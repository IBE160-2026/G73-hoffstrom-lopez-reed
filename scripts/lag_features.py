"""Lag featurefila F1–F16 per anløp og horisont (E2-S04, beslutning 11, PRD FR9a og NFR1).

Leser (bare lesing):
- ``data/utdrag/anlop.csv``: ETA, MMSI, gruppe og split. Faktisk ankomst brukes **bare** til å bygge
  fartøyhistorikken fra treningsrader (F15–F16), aldri til en rads egne features.
- ``data/utdrag/tilstand_ved_kutt.csv``: tilstanden ved kuttet (E2-S03).
- ``pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv``: skipstype, lengde, ETD og avgangshavn.
  Fila er gitignorert, så featurefila er det sensor får (NFR1). Rå ETD skrives aldri ut.
- ``data/baseline.json``: offset per gruppe til kalibrert avvik. Offseten er fittet på hele
  treningsdelen, men den er én konstant per gruppe. Både fartøyets snitt og snittet det trekkes mot
  forskyves like mye, så den bærer ingen informasjon om senere ankomster (beslutning 11, valg 5).

Skriver ``data/utdrag/features.csv`` og ``features.json`` (sjekksummer for input og antall).
Sjeldne kategorier grupperes ikke her: det fittes i E2-S05 på dataene modellen trenes på.

F15–F16 skrives i to varianter:
- ``fartoy_*``: **endelig** trening og test. Historikken kommer fra hele train-splitten (trening og
  validering) med ankomst før kuttet.
- ``fartoy_*_modellvalg``: **modellvalg** på valideringsdelen. Historikken kommer bare fra
  treningsdelen, så valideringsradene får historikk frosset ved grensen, slik testradene får.

    .venv/bin/python scripts/lag_features.py [--anlop STI] [--tilstand STI] [--seilaser STI] [--baseline STI] [--ut-dir STI] [--laget ÅÅÅÅ-MM-DD]

Utdataene er byte-identiske for samme input og samme ``--laget``.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROT))
from app.prediksjon import features as F  # noqa: E402

STANDARD = {
    "anlop": Path("data/utdrag/anlop.csv"),
    "tilstand": Path("data/utdrag/tilstand_ved_kutt.csv"),
    "seilaser": Path("pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv"),
    "baseline": Path("data/baseline.json"),
    "ut_dir": Path("data/utdrag"),
}
HORISONTER = (6, 24)
KOLONNER = [
    "voyageid", "horisont_timer", "t_kutt_utc", "gruppe", "del", "har_tilstand",
    "distanse_km", "fart_knop", "kurs_mot_havn", "posisjon_alder_min", "lat", "lon",   # F1–F5
    "i_sonen_ved_kutt", "slakk_timer",                                                 # F6–F7
    "skipstype", "lengde_m",                                                           # F8–F9
    "eta_time_sin", "eta_time_cos", "eta_ukedag", "eta_maned_sin", "eta_maned_cos",    # F10–F12
    "avgangshavn", "avgatt_for_kutt", "timer_siden_avgang",                            # F13–F14
    "fartoy_snittavvik_min", "fartoy_antall_tidligere",                                # F15–F16, endelig
    "fartoy_snittavvik_min_modellvalg", "fartoy_antall_tidligere_modellvalg",          # F15–F16, modellvalg
]


class Inkonsistens(Exception):
    pass


def naive_utc(s):
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d.astimezone(dt.timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def _tall(s):
    if s is None or s == "":
        return None
    return float(s)


def _fmt(v, des):
    return "" if v is None else f"{v:.{des}f}"


def les_csv(sti):
    with open(sti, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def gruppe(ship_group):
    return "Passasjer" if ship_group == "Passasjer" else "Øvrige"


def bygg_historikk(anlop, offset, bare=None):
    """Historikkrader bare fra train-splitten, med fasit (status_in_area = ok).

    ``bare`` er et sett med voyageid-er. Er det gitt, brukes bare de radene. For modellvalget er
    det treningsdelen uten validering, så valideringsradene får historikk frosset ved grensen,
    slik testradene får (Felipe, 03.11.2026).
    """
    rader = []
    for a in anlop:
        if bare is not None and a["voyageid"] not in bare:
            continue
        if a["split"] != "train" or a["status_in_area"] != "ok" or not a["arrival_in_area_utc"]:
            continue
        g = gruppe(a["ship_group"])
        ank = naive_utc(a["arrival_in_area_utc"])
        kalibrert_eta = naive_utc(a["eta_reported"]) - dt.timedelta(minutes=offset[g])
        rader.append(F.Historikkrad(voyageid=a["voyageid"], mmsino=a["mmsino"], ovrige=(g == "Øvrige"),
                                    ankomst=ank, avvik_min=(ank - kalibrert_eta).total_seconds() / 60))
    return F.Historikk(rader)


def featurerad(a, h, tilstand, seilas, historikk, del_, historikk_modellvalg=None):
    eta = naive_utc(a["eta_reported"])
    t_kutt = naive_utc(tilstand["t_kutt_utc"])
    if t_kutt != eta - dt.timedelta(hours=h):
        raise Inkonsistens(f"seilas {a['voyageid']}, H={h}: t_kutt i tilstandsfila stemmer ikke med ETA − {h} t")
    h_eff = (eta - t_kutt).total_seconds() / 3600
    ok = tilstand["ais_status"] == "ok"
    km, fart = (_tall(tilstand["distanse_km"]), _tall(tilstand["fart_knop"])) if ok else (None, None)
    lat, lon = (_tall(tilstand["lat"]), _tall(tilstand["lon"])) if ok else (None, None)
    kurs = _tall(tilstand["kurs_grader"]) if ok else None
    alder = _tall(tilstand["posisjon_alder_min"]) if ok else None
    etd = F.gyldig_etd(naive_utc(seilas["etd"]) if seilas and seilas.get("etd") else None, eta)
    avgatt, timer = F.avgang(etd, t_kutt)
    kal = F.kalender(eta)
    f15, f16 = historikk.fartoy(a["mmsino"], t_kutt, a["voyageid"])
    mv15, mv16 = (historikk_modellvalg or historikk).fartoy(a["mmsino"], t_kutt, a["voyageid"])
    return {
        "voyageid": a["voyageid"], "horisont_timer": str(h), "t_kutt_utc": t_kutt.isoformat() + "Z",
        "gruppe": gruppe(a["ship_group"]), "del": del_, "har_tilstand": str(int(ok)),
        "distanse_km": _fmt(km, 3), "fart_knop": _fmt(fart, 1),
        "kurs_mot_havn": _fmt(F.kurs_mot_havn(lat, lon, kurs, fart, km), 6),
        "posisjon_alder_min": _fmt(alder, 1), "lat": _fmt(lat, 6), "lon": _fmt(lon, 6),
        "i_sonen_ved_kutt": "" if F.i_sonen(km) is None else str(F.i_sonen(km)),
        "slakk_timer": _fmt(F.slakk_timer(km, fart, h_eff), 3),
        "skipstype": (seilas or {}).get("ship_type") or "",
        "lengde_m": _fmt(F.lengde((seilas or {}).get("length")), 2),
        "eta_time_sin": _fmt(kal["eta_time_sin"], 6), "eta_time_cos": _fmt(kal["eta_time_cos"], 6),
        "eta_ukedag": str(kal["eta_ukedag"]),
        "eta_maned_sin": _fmt(kal["eta_maned_sin"], 6), "eta_maned_cos": _fmt(kal["eta_maned_cos"], 6),
        "avgangshavn": (seilas or {}).get("dep_locname") or "",
        "avgatt_for_kutt": "" if avgatt is None else str(avgatt), "timer_siden_avgang": _fmt(timer, 3),
        "fartoy_snittavvik_min": _fmt(f15, 2), "fartoy_antall_tidligere": str(f16),
        "fartoy_snittavvik_min_modellvalg": _fmt(mv15, 2), "fartoy_antall_tidligere_modellvalg": str(mv16),
    }


def _unik(rader, nokkel, navn):
    idx = {}
    for r in rader:
        k = nokkel(r)
        if k in idx:
            raise Inkonsistens(f"duplikat {k} i {navn}")
        idx[k] = r
    return idx


def bygg(anlop, tilstand, seilaser, offset):
    """Returnerer featureradene. Kaster Inkonsistens. Skriver ingenting."""
    for g in ("Passasjer", "Øvrige"):
        if offset.get(g) is None:
            raise Inkonsistens(f"baseline.json mangler offset for {g}")
    _unik(anlop, lambda r: r["voyageid"], "anlop.csv")
    t_idx = _unik(tilstand, lambda r: (r["voyageid"], r["horisont_timer"]), "tilstandsfila")
    s_idx = _unik(seilaser, lambda r: r["voyageid"], "seilasfila")
    deler = F.valideringssplitt(anlop)
    historikk = bygg_historikk(anlop, offset)                       # endelig: trening + validering
    historikk_mv = bygg_historikk(anlop, offset, {v for v, d in deler.items() if d == "trening"})
    rader = []
    for a in sorted(anlop, key=lambda r: int(r["voyageid"])):
        for h in HORISONTER:
            t = t_idx.get((a["voyageid"], str(h)))
            if t is None:
                raise Inkonsistens(f"seilas {a['voyageid']}, H={h} mangler i tilstandsfila")
            rader.append(featurerad(a, h, t, s_idx.get(a["voyageid"]), historikk, deler[a["voyageid"]], historikk_mv))
    if len(t_idx) != len(rader):
        raise Inkonsistens(f"tilstandsfila har {len(t_idx)} rader, men anlop.csv gir {len(rader)}")
    return rader


def _sha256(sti):
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            h.update(blokk)
    return h.hexdigest()


def _visningssti(sti):
    try:
        return Path(sti).resolve().relative_to(REPO_ROT).as_posix()
    except ValueError:
        return Path(sti).name


def _skriv_par(filer):
    tmp = [(str(sti) + ".tmp", sti) for sti, _ in filer]
    try:
        for (t, _), (_, tekst) in zip(tmp, filer):
            with open(t, "w", encoding="utf-8", newline="") as f:
                f.write(tekst)
        for t, sti in tmp:
            os.replace(t, sti)
    except BaseException:
        for t, _ in tmp:
            if os.path.exists(t):
                os.remove(t)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in STANDARD.items():
        ap.add_argument("--" + k.replace("_", "-"), type=Path, default=v)
    ap.add_argument("--laget", default=dt.date.today().isoformat())
    args = ap.parse_args(argv)
    for k in ("anlop", "tilstand", "seilaser", "baseline"):
        if not getattr(args, k).is_file():
            sys.exit(f"Fant ikke {getattr(args, k)}. Kjør fra repo-roten"
                     + (" etter scripts/lag_tilstand.py." if k == "tilstand" else "."))
    try:
        dt.date.fromisoformat(args.laget)
    except ValueError:
        sys.exit(f"--laget må være ÅÅÅÅ-MM-DD, fikk {args.laget!r}")

    with open(args.baseline, encoding="utf-8") as f:
        offset = json.load(f)["offset_minutter"]
    try:
        rader = bygg(les_csv(args.anlop), les_csv(args.tilstand), les_csv(args.seilaser), offset)
    except Inkonsistens as exc:
        print(f"Stopper, ingenting er skrevet: {exc}", file=sys.stderr)
        return 2

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=KOLONNER, lineterminator="\n")
    w.writeheader()
    w.writerows(rader)
    tekst = buf.getvalue()
    antall = {}
    for r in rader:
        n = antall.setdefault(r["del"], {}).setdefault(r["horisont_timer"], {"med_tilstand": 0, "uten_tilstand": 0})
        n["med_tilstand" if r["har_tilstand"] == "1" else "uten_tilstand"] += 1
    anlop_rader = les_csv(args.anlop)
    seilas_ider = {r["voyageid"] for r in les_csv(args.seilaser)}
    meta = {"laget": args.laget, "rader": len(rader), "antall": antall,
            "anlop_uten_seilasrad": sum(a["voyageid"] not in seilas_ider for a in anlop_rader),
            "kode_sha256": {p.name: _sha256(p) for p in (REPO_ROT / "app" / "prediksjon" / "features.py",
                                                       Path(__file__).resolve())},
            "parametre": {"SHRINK_K": F.SHRINK_K, "SLAKK_MIN_TIMER": F.SLAKK_MIN_TIMER, "MIN_FART_KN": F.MIN_FART_KN,
                          "SONE_KM": F.SONE_KM, "ETD_MAKS_FOR_ETA_DOGN": F.ETD_MAKS_FOR_ETA.days,
                          "TRENINGSANDEL": F.TRENINGSANDEL},
            "utdrag_sha256": hashlib.sha256(tekst.encode("utf-8")).hexdigest(),
            "kilder": {k: {"sti": _visningssti(getattr(args, k)), "sha256": _sha256(getattr(args, k))}
                       for k in ("anlop", "tilstand", "seilaser", "baseline")}}
    args.ut_dir.mkdir(parents=True, exist_ok=True)
    _skriv_par([(args.ut_dir / "features.csv", tekst),
                (args.ut_dir / "features.json", json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n")])
    for d in ("trening", "validering", "test"):
        print(f"{d:10}: " + ", ".join(f"H={h}: {antall.get(d, {}).get(h)}" for h in ("6", "24")))
    print(f"Skrev {len(rader)} rader til {args.ut_dir / 'features.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
