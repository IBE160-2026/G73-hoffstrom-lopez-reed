"""Tren 6 t- og 24 t-modellen for Øvrige, med ablasjon uten F13–F14 (E2-S05, beslutning 11, PRD FR9/FR10, arkitektur A7).

Målet er kalibrert avvik i minutter, ``arrival_in_area − (eta_reported − offset_Øvrige)``. En prediksjon er
kalibrert ETA + predikert avvik, og varsel er predikert avvik > 120 min (PRD FR9, A3). Modellen som
predikerer 0, er altså nøyaktig den kalibrerte baselinen.

Leser (bare lesing):
- ``data/utdrag/features.csv`` og ``features.json`` (F1–F16, ``del``). Rader med ``del == "test"`` kastes
  idet de leses: de når aldri et fit, et kategorikart, en score eller en utskrift.
- ``data/utdrag/anlop.csv``: bare til å bygge målet. Ingen ankomstfelt går inn i en feature.
- ``data/baseline.json``: offseten for Øvrige.

Utvalget er Øvrige-rader med tilstand og fasit som er **utenfor ankomstsonen ved kuttet** (F6 = 0,
beslutning 12). For trafikk som allerede er i sonen ved kuttet, måler etiketten ikke en ankomst
(beslutning 03). Slike rader går til baselinen, som rader uten tilstand.

Per horisont:
1. Modellvalg: 8 konfigurasjoner av ``HistGradientBoostingRegressor`` fittes på ``trening`` med
   ``fartoy_*_modellvalg`` og scores på ``validering``. Valgkriteriet er andel innenfor ±30 min, med
   1 prosentpoengs toleranse og enkelhetsregel (færrest ``max_iter``, så færrest ``max_leaf_nodes``,
   så lavest MAE). Referansen «avvik = 0» (kalibrert baseline) vises, men velges aldri.
2. Endelig fit: valgt konfigurasjon på ``trening`` + ``validering`` med endelig ``fartoy_*``, både som
   hovedmodell og som ablasjon uten ``avgangshavn``, ``avgatt_for_kutt`` og ``timer_siden_avgang``.

Skriver ``data/modell/modell_{6,24}t.joblib``, ``modell_{6,24}t_uten_f13_f14.joblib`` og ``modellvalg.json``.

    .venv/bin/python scripts/tren.py [--features STI] [--anlop STI] [--baseline STI] [--ut-dir STI] [--seed N]

Samme input gir byte-identisk ``modellvalg.json`` og identiske prediksjoner.
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

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

REPO_ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROT))
from app.prediksjon import features as F  # noqa: E402
from app.prediksjon.koding import FEATURES, HISTORIKK, KATEGORISKE, matrise  # noqa: E402,F401

STANDARD = {
    "features": Path("data/utdrag/features.csv"),
    "anlop": Path("data/utdrag/anlop.csv"),
    "baseline": Path("data/baseline.json"),
    "ut_dir": Path("data/modell"),
}
HORISONTER = (6, 24)
SEED = 20261109
TRENGRUPPE = "Øvrige"
TREFF_MIN = 30.0
VARSEL_MIN = 120.0             # PRD A3: terskelen tunes ikke
TOLERANSE_PP = 1.0             # beslutning 1 (Felipe, 09.11.2026)

# FEATURES, KATEGORISKE, HISTORIKK og matrise står i app/prediksjon/koding.py (E2-S07): én definisjon av modellarmen.
ABLASJON_UT = ("avgangshavn", "avgatt_for_kutt", "timer_siden_avgang")                 # F13–F14
FEATURES_UTEN_F13_F14 = [f for f in FEATURES if f not in ABLASJON_UT]

KANDIDATER = [
    {"loss": loss, "learning_rate": lr, "max_leaf_nodes": blad, "max_iter": 300}
    for loss in ("absolute_error", "squared_error")
    for lr in (0.05, 0.1)
    for blad in (15, 31)
]
UTVALG = ("Øvrige-rader med AIS-tilstand og fasit som er utenfor ankomstsonen ved kuttet (F6 = 0). "
          "F6-rader går til baselinen, som rader uten tilstand (beslutning 12).")
REGEL = ("Høyest andel innenfor ±30 min på validering. Konfigurasjoner innenfor 1 prosentpoeng av beste "
         "andel regnes som like gode; blant dem velges færrest max_iter, så færrest max_leaf_nodes, så lavest "
         "MAE. F1 for varsel rapporteres, men avgjør ikke. Referansen «avvik = 0» velges aldri.")


class Inkonsistens(Exception):
    pass


def naive_utc(s):
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d.astimezone(dt.timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def les_features(innhold):
    """Featureradene uten testperioden. Testrader kastes her, før noe annet ser dem."""
    return [r for r in csv.DictReader(io.StringIO(innhold.decode("utf-8"))) if r["del"] != "test"]


def les_csv(sti):
    with open(sti, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def treningsrader(features, anlop, offset, utelat_i_sonen=True):
    """Øvrige-rader med tilstand og fasit, utenfor sonen ved kuttet (beslutning 12), med målet
    ``avvik_min`` lagt til. ``utelat_i_sonen=False`` gir utvalget fra før beslutning 12, bare til
    sammenligning. Kaster Inkonsistens."""
    idx = {}
    for a in anlop:
        if a["voyageid"] in idx:
            raise Inkonsistens(f"duplikat voyageid {a['voyageid']} i anlop.csv")
        idx[a["voyageid"]] = a
    ut = []
    for r in features:
        if r["del"] not in ("trening", "validering"):
            raise Inkonsistens(f"ukjent del {r['del']!r} for seilas {r['voyageid']}")
        a = idx.get(r["voyageid"])
        if a is None:
            raise Inkonsistens(f"seilas {r['voyageid']} i features.csv finnes ikke i anlop.csv")
        if a["split"] != "train":
            raise Inkonsistens(f"seilas {r['voyageid']} er {r['del']} i features.csv, men {a['split']} i anlop.csv")
        if r["gruppe"] != TRENGRUPPE or r["har_tilstand"] != "1":
            continue
        if utelat_i_sonen and r["i_sonen_ved_kutt"] == "1":
            continue  # beslutning 12: F6-rader går til baselinen
        if a["status_in_area"] != "ok" or not a["arrival_in_area_utc"]:
            continue
        kalibrert_eta = naive_utc(a["eta_reported"]) - dt.timedelta(minutes=offset)
        avvik = (naive_utc(a["arrival_in_area_utc"]) - kalibrert_eta).total_seconds() / 60
        ut.append(dict(r, avvik_min=avvik))
    return ut


def lag_kategorier(rader, features):
    """F8/F13-kartene, fittet på radene som fittes (beslutning 11). Koden er indeksen i lista."""
    return {k: sorted(F.lag_kategorikart(r[k] for r in rader) | {F.ANNET}) for k in KATEGORISKE if k in features}


def lag_modell(config, features, seed):
    return HistGradientBoostingRegressor(
        **config, early_stopping=False, random_state=seed,
        categorical_features=[f in KATEGORISKE for f in features])


def prediker(artefakt, rader):
    """Predikert kalibrert avvik i minutter for featurerader (dict med kolonnene fra features.csv)."""
    return artefakt["modell"].predict(matrise(rader, artefakt["features"], artefakt["kategorier"]))


def score(y, pred):
    y, pred = np.asarray(y, dtype=float), np.asarray(pred, dtype=float)
    feil = np.abs(pred - y)
    faktisk, varsel = y > VARSEL_MIN, pred > VARSEL_MIN
    tp = int(np.sum(faktisk & varsel))
    pres = tp / int(np.sum(varsel)) if np.any(varsel) else 0.0
    rec = tp / int(np.sum(faktisk)) if np.any(faktisk) else 0.0
    f1 = 2 * pres * rec / (pres + rec) if pres + rec else 0.0
    return {"andel_30": round(float(np.mean(feil <= TREFF_MIN)), 6), "mae": round(float(np.mean(feil)), 4),
            "varsel_presisjon": round(pres, 6), "varsel_recall": round(rec, 6), "varsel_f1": round(f1, 6)}


def velg(resultater):
    """Beslutning 1: innenfor 1 pp av beste andel, så enkleste. Returnerer (indeks, beste, innenfor)."""
    beste = max(r["andel_30"] for r in resultater)
    innenfor = [i for i, r in enumerate(resultater) if (beste - r["andel_30"]) * 100 <= TOLERANSE_PP + 1e-9]
    valgt = min(innenfor, key=lambda i: (resultater[i]["config"]["max_iter"],
                                         resultater[i]["config"]["max_leaf_nodes"], resultater[i]["mae"], i))
    return valgt, beste, innenfor


def tren_horisont(rader, h, seed):
    """Modellvalg og endelig fit for én horisont. Returnerer (valgrapport, {variant: artefakt uten sha})."""
    rader = [r for r in rader if r["horisont_timer"] == str(h)]
    tr = [r for r in rader if r["del"] == "trening"]
    va = [r for r in rader if r["del"] == "validering"]
    if not tr or not va:
        raise Inkonsistens(f"H={h}: trenger både trenings- og valideringsrader (fikk {len(tr)} og {len(va)})")
    kat = lag_kategorier(tr, FEATURES)
    X_tr, X_va = matrise(tr, FEATURES, kat, "modellvalg"), matrise(va, FEATURES, kat, "modellvalg")
    y_tr, y_va = [r["avvik_min"] for r in tr], [r["avvik_min"] for r in va]
    resultater = []
    for config in KANDIDATER:
        m = lag_modell(config, FEATURES, seed).fit(X_tr, y_tr)
        resultater.append(dict(score(y_va, m.predict(X_va)), config=config))
    valgt, beste, innenfor = velg(resultater)
    config = resultater[valgt]["config"]
    std_feil_pp = round(100 * float(np.sqrt(beste * (1 - beste) / len(va))), 2)
    rapport = {
        "enkelhetsregel_endret_valget": valgt != max(range(len(resultater)),
                                                     key=lambda i: (resultater[i]["andel_30"], -i)),
        "standardfeil_beste_andel_pp": std_feil_pp,
        "antall": {"trening": len(tr), "validering": len(va)},
        "kandidater": resultater,
        "referanse_avvik_0": score(y_va, np.zeros(len(va))),
        "beste_andel_30": beste,
        "innenfor_toleranse": innenfor,
        "valgt": valgt,
        "valgt_config": config,
    }
    alle = tr + va
    y = [r["avvik_min"] for r in alle]
    artefakter = {}
    for variant, features in (("hoved", FEATURES), ("uten_f13_f14", FEATURES_UTEN_F13_F14)):
        kat = lag_kategorier(alle, features)
        modell = lag_modell(config, features, seed).fit(matrise(alle, features, kat), y)
        artefakter[variant] = {
            "modell": modell, "features": list(features), "kategorier": kat, "horisont": h,
            "variant": variant, "sklearn_versjon": sklearn.__version__,
            "trent_paa": {"trening": len(tr), "validering": len(va)}, "config": dict(config, random_state=seed),
            "maal": "kalibrert avvik i minutter: arrival_in_area − (eta_reported − offset_Øvrige)",
            "utvalg": UTVALG,
        }
    return rapport, artefakter


def toleranse_merknad(valg):
    """Beslutning 1 og Felipe 09.11.2026: toleransen justeres ikke i etterkant, men det skal stå om regelen slo inn."""
    slo_inn = [h for h, v in valg.items() if v["enkelhetsregel_endret_valget"]]
    se = ", ".join(f"{v['standardfeil_beste_andel_pp']} pp ved {h} t" for h, v in sorted(valg.items(), key=lambda x: int(x[0])))
    if slo_inn:
        return f"Enkelhetsregelen endret valget ved {', '.join(sorted(slo_inn, key=int))} t."
    flere = ", ".join(f"{len(v['innenfor_toleranse'])} ved {h} t" for h, v in sorted(valg.items(), key=lambda x: int(x[0])))
    return (f"Enkelhetsregelen endret ikke valget ved noen horisont: den valgte konfigurasjonen har også høyest "
            f"andel innenfor ±30 min. Antall konfigurasjoner innenfor {TOLERANSE_PP:g} prosentpoeng av den beste: "
            f"{flere}, og den beste var der også den enkleste. "
            f"Toleransen er mindre enn utvalgsstøyen (standardfeil for beste andel: "
            f"{se}). Den ble satt før resultatene forelå (Felipe, 09.11.2026), og den justeres ikke i etterkant, "
            "fordi det ville vært tilpasning til resultatet.")


def filnavn(h, variant):
    return f"modell_{h}t.joblib" if variant == "hoved" else f"modell_{h}t_{variant}.joblib"


def _skriv_atomisk(filer):
    """[(sti, skrivefunksjon(tmp_sti))]. Alle skrives til .tmp først, så flyttes de på plass."""
    tmp = [(Path(str(sti) + ".tmp"), sti, fn) for sti, fn in filer]
    try:
        for t, _, fn in tmp:
            fn(t)
        for t, sti, _ in tmp:
            os.replace(t, sti)
    except BaseException:
        for t, _, _ in tmp:
            if t.exists():
                t.unlink()
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in STANDARD.items():
        ap.add_argument("--" + k.replace("_", "-"), type=Path, default=v)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    meta_sti = args.features.with_suffix(".json")
    for sti in (args.features, meta_sti, args.anlop, args.baseline):
        if not sti.is_file():
            sys.exit(f"Fant ikke {sti}. Kjør fra repo-roten etter scripts/lag_features.py.")

    innhold = args.features.read_bytes()
    anlop_bytes = args.anlop.read_bytes()
    meta = json.loads(meta_sti.read_text(encoding="utf-8"))
    with open(args.baseline, encoding="utf-8") as f:
        offset = json.load(f)["offset_minutter"].get(TRENGRUPPE)
    try:
        if _sha256_bytes(innhold) != meta.get("utdrag_sha256"):
            raise Inkonsistens(f"sha256 for {args.features} stemmer ikke med {meta_sti}")
        if offset is None:
            raise Inkonsistens(f"baseline.json mangler offset for {TRENGRUPPE}")
        rader = treningsrader(les_features(innhold), les_csv(args.anlop), offset)
        valg, artefakter = {}, {}
        for h in HORISONTER:
            valg[str(h)], artefakter[h] = tren_horisont(rader, h, args.seed)
    except Inkonsistens as exc:
        print(f"Stopper, ingenting er skrevet: {exc}", file=sys.stderr)
        return 2

    sha = {"features_sha256": _sha256_bytes(innhold), "anlop_sha256": _sha256_bytes(anlop_bytes),
           "baseline_sha256": _sha256_bytes(args.baseline.read_bytes()), "offset_ovrige_min": offset}
    rapport = {
        "beslutning": "docs/beslutninger/11-modellvalg-ovrige-og-features.md",
        "regel": REGEL, "toleranse_pp": TOLERANSE_PP, "treff_min": TREFF_MIN, "varsel_min": VARSEL_MIN,
        "seed": args.seed, "sklearn_versjon": sklearn.__version__, "offset_ovrige_min": offset,
        "features": FEATURES, "features_uten_f13_f14": FEATURES_UTEN_F13_F14,
        "kandidater": KANDIDATER, "horisonter": valg, "utvalg": UTVALG,
        "toleranse_merknad": toleranse_merknad(valg),
    }
    tekst = json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def _joblib(art):
        return lambda t: joblib.dump(dict(art, **sha), t)

    def _tekst(t):
        t.write_text(tekst, encoding="utf-8")

    args.ut_dir.mkdir(parents=True, exist_ok=True)
    filer = [(args.ut_dir / filnavn(h, v), _joblib(a)) for h in HORISONTER for v, a in artefakter[h].items()]
    _skriv_atomisk(filer + [(args.ut_dir / "modellvalg.json", _tekst)])

    for h in HORISONTER:
        v = valg[str(h)]
        print(f"H={h} t: trening {v['antall']['trening']}, validering {v['antall']['validering']}")
        print(f"  {'#':>2} {'loss':15} {'lr':>5} {'blad':>4} {'±30':>7} {'MAE':>8} {'F1':>6}")
        ref = v["referanse_avvik_0"]
        print(f"  {'-':>2} {'avvik = 0':15} {'':>5} {'':>4} {ref['andel_30']:7.1%} {ref['mae']:8.1f} {ref['varsel_f1']:6.3f}")
        for i, r in enumerate(v["kandidater"]):
            c = r["config"]
            merke = " <- valgt" if i == v["valgt"] else (" (innenfor 1 pp)" if i in v["innenfor_toleranse"] else "")
            print(f"  {i:>2} {c['loss']:15} {c['learning_rate']:5} {c['max_leaf_nodes']:4} "
                  f"{r['andel_30']:7.1%} {r['mae']:8.1f} {r['varsel_f1']:6.3f}{merke}")
    print(f"Skrev {len(filer)} artefakter og modellvalg.json til {args.ut_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
