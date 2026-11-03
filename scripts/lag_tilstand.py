"""Lag tilstandsutdraget ved kuttpunktene (E2-S03, PRD FR9a og NFR1, beslutning 08, 09 og 11).

Leser AIS-cachen fra ``pipeline/fetch_ais_kutt.py`` (``pipeline/data/ais_kutt_cache/``, bare
lesing) og ``voyageid`` og ``eta_reported`` fra ``data/utdrag/anlop.csv``. Skriver:

- ``data/utdrag/tilstand_ved_kutt.csv``: én rad per anløp og H ∈ {6, 24}, fra siste gyldige
  posisjon i [t_kutt − 24 t, t_kutt], der t_kutt = rapportert ETA − H.
- ``data/utdrag/tilstand_ved_kutt.json``: kilde, antall filer, samlet sha256, dato og
  fordelingen på ``ais_status``.

Lekkasjesikring:
- Scriptet leser ingen ankomstfelt.
- Det filtrerer på tidsstempel på nytt i stedet for å stole på cachen.
- Stemmer kuttpunktet i en cachefil ikke med ETA − H, stopper det uten å skrive noe.

En posisjon er gyldig bare hvis MMSI-en i punktet er lik seilasens MMSI og har 9 sifre (Felipe,
03.11.2026), og bredde/lengde er en reell posisjon (ikke 91/181 eller 0,0).

``ais_status`` er ``ok``, ``ingen_posisjon`` (hentet, men ingen gyldig posisjon i vinduet) eller
``ikke_hentet`` (ingen cachefil). Raden skrives alltid, med tomme tilstandsfelt når statusen
ikke er ``ok``.

Kjøres fra repo-roten når hentingen er ferdig:

    .venv/bin/python scripts/lag_tilstand.py [--cache-dir STI] [--anlop STI] [--ut-dir STI] [--laget ÅÅÅÅ-MM-DD]

Utdataene er byte-identiske for samme input og samme ``--laget``. Oppgi derfor ``--laget`` når
utdraget lages på nytt, ellers endres datoen i metadataene.

``kilde_antall_filer`` og ``kilde_sha256`` gjelder cachefilene for anløpene i ``anlop.csv``.
``kilde_antall_tomme_svar`` teller filer der API-et ga tomt svar (``status: "tom"``). Slike
seilaser blir ``ingen_posisjon``, men kan hentes på nytt med ``fetch_ais_kutt.py --prov-tomme``.
"""
import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import math
import os
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
STANDARD_CACHE = Path("pipeline/data/ais_kutt_cache")
STANDARD_ANLOP = Path("data/utdrag/anlop.csv")
STANDARD_UT_DIR = Path("data/utdrag")

HORISONTER = (6, 24)
TILBAKEBLIKK = dt.timedelta(hours=24)
# Samme referansepunkt og jordradius som pipeline/derive_arrivals.py (kopiert, ikke importert: CLI-script).
PORT_LAT, PORT_LON = 60.398, 5.321
JORDRADIUS_KM = 6371.0
SOG_IKKE_TILGJENGELIG = 102.3
COG_IKKE_TILGJENGELIG = 360.0
KOLONNER = ["voyageid", "horisont_timer", "t_kutt_utc", "ais_status", "lat", "lon",
            "distanse_km", "fart_knop", "kurs_grader", "posisjon_alder_min"]
STATUSER = ("ok", "ingen_posisjon", "ikke_hentet")
# Kolonnene i et Kystdatahuset-punkt (verifisert mot API-et 27.09.2026, se pipeline/fetch_ais.py).
I_MMSI, I_LON, I_LAT, I_COG, I_SOG = 0, 2, 3, 4, 5

# Én kilde for tidsstempeltolking: samme funksjoner som hentingen bruker.
_spec = importlib.util.spec_from_file_location("fetch_ais_kutt", REPO_ROT / "pipeline" / "fetch_ais_kutt.py")
_fak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fak)
tidsstempel = _fak.tidsstempel
filtrer_til_vindu = _fak.filtrer_til_vindu
naive_utc = _fak.naive_utc


class KuttAvvik(Exception):
    """Cachen stemmer ikke med anlop.csv eller kan ikke leses. Ingenting skrives."""


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * JORDRADIUS_KM * math.asin(math.sqrt(a))


def les_anlop(sti):
    """Bare voyageid, mmsino og eta_reported. Ankomstfeltene i fila leses aldri videre."""
    with open(sti, newline="", encoding="utf-8") as f:
        return [{"voyageid": r["voyageid"], "mmsino": r["mmsino"], "eta_reported": r["eta_reported"]}
                for r in csv.DictReader(f)]


def gyldig_mmsi(mmsi):
    """MMSI har 9 sifre. MMSI 0 (63 seilaser i anlop.csv) gir posisjoner fra alle fartøy i verden
    som sender 0 (E2-S03-røyktesten 03.11.2026, beslutning 07)."""
    m = str(mmsi).strip()
    return len(m) == 9 and m.isdigit()


def _tall(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def gyldig_posisjon(punkt, mmsi):
    """Gyldig bare hvis punktet tilhører seilasens fartøy (samme MMSI, 9 sifre) og har en reell posisjon."""
    try:
        if not gyldig_mmsi(mmsi) or str(punkt[I_MMSI]).strip() != str(mmsi).strip():
            return False
        lon, lat = _tall(punkt[I_LON]), _tall(punkt[I_LAT])
    except (IndexError, TypeError):
        return False
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)  # 0,0 er en plassholder, ikke en posisjon


def siste_gyldige(punkter, mmsi):
    """Siste gyldige punkt etter tidsstempel. Ved likt tidsstempel vinner det siste i fila."""
    beste, beste_t = None, None
    for p in punkter:
        t = tidsstempel(p)
        if t is None or not gyldig_posisjon(p, mmsi):
            continue
        if beste_t is None or t >= beste_t:
            beste, beste_t = p, t
    return beste, beste_t


def _felt(punkt, i, ikke_tilgjengelig):
    try:
        v = _tall(punkt[i])
    except IndexError:
        return ""
    if v is None or v >= ikke_tilgjengelig or v < 0:
        return ""
    return f"{v:.1f}"


def tilstandsrad(voyageid, mmsi, h, t_kutt, cache):
    rad = {k: "" for k in KOLONNER}
    rad.update(voyageid=voyageid, horisont_timer=str(h), t_kutt_utc=t_kutt.isoformat() + "Z")
    if cache is None:
        rad["ais_status"] = "ikke_hentet"
        return rad
    v = (cache.get("horisonter") or {}).get(str(h))
    if not isinstance(v, dict) or "t_kutt_utc" not in v or not isinstance(v.get("posisjoner"), list):
        raise KuttAvvik(f"seilas {voyageid}, H={h}: cachefila mangler horisonten eller har feil format")
    if naive_utc(v["t_kutt_utc"]) != t_kutt:
        raise KuttAvvik(f"seilas {voyageid}, H={h}: cachen har t_kutt {v['t_kutt_utc']}, "
                        f"men rapportert ETA − {h} t er {t_kutt.isoformat()}")
    punkter = filtrer_til_vindu(v["posisjoner"], t_kutt - TILBAKEBLIKK, t_kutt)
    p, t = siste_gyldige(punkter, mmsi)
    if p is None:
        rad["ais_status"] = "ingen_posisjon"
        return rad
    lat, lon = float(p[I_LAT]), float(p[I_LON])
    rad.update(ais_status="ok", lat=f"{lat:.6f}", lon=f"{lon:.6f}",
               distanse_km=f"{haversine_km(lat, lon, PORT_LAT, PORT_LON):.3f}",
               fart_knop=_felt(p, I_SOG, SOG_IKKE_TILGJENGELIG),
               kurs_grader=_felt(p, I_COG, COG_IKKE_TILGJENGELIG),
               posisjon_alder_min=f"{(t_kutt - t).total_seconds() / 60:.1f}")
    return rad


def _sha256(sti):
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            h.update(blokk)
    return h.hexdigest()


def bygg(anlop, cache_dir):
    """Returnerer (rader, filhasher, antall tomme svar). Kaster KuttAvvik. Skriver ingenting."""
    rader, hasher, tomme = [], [], 0
    for a in sorted(anlop, key=lambda r: int(r["voyageid"])):
        sti = os.path.join(cache_dir, f"{a['voyageid']}.json")
        cache = None
        if os.path.exists(sti):
            with open(sti, "rb") as f:
                data = f.read()  # én lesing: sjekksummen gjelder nøyaktig innholdet som brukes
            try:
                cache = json.loads(data)
            except ValueError as exc:
                raise KuttAvvik(f"seilas {a['voyageid']}: cachefila kan ikke leses ({exc})") from exc
            if not isinstance(cache, dict):
                raise KuttAvvik(f"seilas {a['voyageid']}: cachefila har feil format")
            hasher.append(f"{a['voyageid']}.json {hashlib.sha256(data).hexdigest()}")
            tomme += cache.get("status") == "tom"
        eta = naive_utc(a["eta_reported"])
        for h in HORISONTER:
            rader.append(tilstandsrad(a["voyageid"], a["mmsino"], h, eta - dt.timedelta(hours=h), cache))
    return rader, hasher, tomme


def _skriv_par(filer):
    """Skriv alle filene til .tmp først, og bytt dem inn først når alle er skrevet.

    Feiler skrivingen, byttes ingenting inn. Et avbrudd mellom de to os.replace-kallene kan ikke
    hindres med to filer, men det oppdages: utdrag_sha256 i metadataene stemmer da ikke med CSV-en.
    """
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


def _visningssti(sti):
    try:
        return Path(sti).resolve().relative_to(REPO_ROT).as_posix()
    except ValueError:
        return Path(sti).name  # aldri en maskinspesifikk sti i en committet fil


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", type=Path, default=STANDARD_CACHE)
    ap.add_argument("--anlop", type=Path, default=STANDARD_ANLOP)
    ap.add_argument("--ut-dir", type=Path, default=STANDARD_UT_DIR)
    ap.add_argument("--laget", default=dt.date.today().isoformat())
    args = ap.parse_args(argv)

    if not args.anlop.is_file():
        sys.exit(f"Fant ikke {args.anlop}. Kjør fra repo-roten.")
    if not args.cache_dir.is_dir():
        sys.exit(f"Fant ikke AIS-cachen {args.cache_dir}. Kjør først: python3 pipeline/fetch_ais_kutt.py")
    try:
        dt.date.fromisoformat(args.laget)
    except ValueError:
        sys.exit(f"--laget må være ÅÅÅÅ-MM-DD, fikk {args.laget!r}")

    try:
        anlop = les_anlop(args.anlop)
        rader, hasher, tomme = bygg(anlop, str(args.cache_dir))
    except KuttAvvik as exc:
        print(f"Stopper, ingenting er skrevet: {exc}", file=sys.stderr)
        return 2

    antall = {str(h): {s: 0 for s in STATUSER} for h in HORISONTER}
    for r in rader:
        antall[r["horisont_timer"]][r["ais_status"]] += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=KOLONNER, lineterminator="\n")
    w.writeheader()
    w.writerows(rader)
    csv_tekst = buf.getvalue()
    meta = {
        "anlop": _visningssti(args.anlop),
        "anlop_sha256": _sha256(args.anlop),
        "kilde": _visningssti(args.cache_dir),
        "kilde_antall_filer": len(hasher),
        "kilde_antall_tomme_svar": tomme,
        "anlop_ugyldig_mmsi": sum(not gyldig_mmsi(a["mmsino"]) for a in anlop),
        "utdrag_sha256": hashlib.sha256(csv_tekst.encode("utf-8")).hexdigest(),
        "kilde_sha256": hashlib.sha256("\n".join(sorted(hasher)).encode("utf-8")).hexdigest(),
        "laget": args.laget,
        "antall_per_horisont": antall,
        "rader": len(rader),
    }
    args.ut_dir.mkdir(parents=True, exist_ok=True)
    _skriv_par([(args.ut_dir / "tilstand_ved_kutt.csv", csv_tekst),
                (args.ut_dir / "tilstand_ved_kutt.json",
                 json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n")])

    for h in HORISONTER:
        a = antall[str(h)]
        print(f"H={h:2}: ok={a['ok']} ingen_posisjon={a['ingen_posisjon']} ikke_hentet={a['ikke_hentet']}")
    if any(antall[str(h)]["ikke_hentet"] for h in HORISONTER):
        print("Advarsel: noen anløp har ingen cachefil (ikke_hentet). Kjører hentingen fortsatt?",
              file=sys.stderr)
    print(f"Skrev {len(rader)} rader til {args.ut_dir / 'tilstand_ved_kutt.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
