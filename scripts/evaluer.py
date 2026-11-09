"""Modell mot kalibrert baseline på de samme anløpene, per horisont og gruppe (E2-S06, PRD FR10, beslutning 11 og 12).

Hvert anløp i splitten scores ved begge horisontene, ved sitt eget kuttpunkt (``naa = eta_reported − H``, som i
``tests/test_dataregresjon.py``). Bare anløp med fasit scores (``har_fasit``). Alle tall kommer fra ``app/metrikker.py``.

Armene, på de samme radene:
- **baseline:** ``BaselinePrediktor`` via ``lag_input``.
- **modell:** artefaktets prediksjon for Øvrige-rader med tilstand og F6 = 0 (modellutvalget), og baselinen for alle andre
  rader (Passasjer, uten tilstand, F6 = 1), slik ``ModellPrediktor`` (E2-S07) skal delegere. En modellprediksjon er
  ``eta_reported − offset_ovrige_min + predikert avvik``, og varsel er predikert avvik > 120 min. Delegerte rader får
  ``forventet_forsinket = None``.
- **ablasjon_uten_f13_f14:** det samme med ``modell_{H}t_uten_f13_f14``.

Radsettene per horisont: Øvrige, all trafikk (med delegering); Øvrige, modellutvalget; og Passasjer (bare baseline).
F6 og tilstand leses fra ``features.csv`` (regnet fra tilstandsutdraget ved kuttet), aldri fra ankomstfeltene.

Kjøringer:
- standard: valideringsdelen (``del == "validering"`` i ``features.csv``). Skriver blokken ``validering``.
- ``--test``: testperioden. Skriver blokken ``test``, øker ``testkjoringer`` og logger datoen.
- ``--bare-baseline``: bare baselinen på testperioden, uten å laste noen modell og uten å røre ``testkjoringer``.
  Gir baselinecellene og modellandelen til tabellen i briefen. Skriver blokken ``test_bare_baseline``.

Andre blokker i ``metrikker.json`` beholdes. Samme input gir byte-identisk fil (bare testloggen endres ved ``--test``).

    .venv/bin/python scripts/evaluer.py [--test | --bare-baseline] [--features STI] [--anlop STI] [--modell-dir STI] [--ut STI]
"""
import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROT))
from app.data import last_utdrag  # noqa: E402
from app.metrikker import (absolutt_feil, andel_innenfor, har_fasit, varselmetrikker,  # noqa: E402
                           varsle_alle)
from app.prediksjon import Prediksjon, lag_input  # noqa: E402
from app.prediksjon.baseline import BASELINE_FIL, BaselinePrediktor  # noqa: E402

_spec = importlib.util.spec_from_file_location("tren", REPO_ROT / "scripts" / "tren.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

STANDARD = {
    "features": REPO_ROT / "data" / "utdrag" / "features.csv",
    "anlop": REPO_ROT / "data" / "utdrag" / "anlop.csv",
    "modell_dir": REPO_ROT / "data" / "modell",
    "ut": REPO_ROT / "data" / "modell" / "metrikker.json",
}
HORISONTER = (6, 24)
ARMER = {"modell": "hoved", "ablasjon_uten_f13_f14": "uten_f13_f14"}
VARSEL_MIN = T.VARSEL_MIN
TREFF_MIN = T.TREFF_MIN
MERKNAD_VALIDERING = (
    "Artefaktene er trent på trening + validering (E2-S05, endelig fit), og F15–F16 er den endelige historikken. "
    "Modelltallene på valideringsdelen er derfor målt på rader modellen er trent på, ikke på holdt-ut data. "
    "Baselinetallene og antallene påvirkes ikke. Holdt-ut-tallene for modellvalget står i modellvalg.json.")


class Avvik(Exception):
    """Input stemmer ikke (artefakt mot utdrag, split mot split). Ingenting skrives."""


def sha256_fil(sti):
    return hashlib.sha256(Path(sti).read_bytes()).hexdigest()


def les_features(sti):
    """Alle featureradene, også testperioden, som {(voyageid, H): rad}. Bare F1–F16, tilstand, F6 og del."""
    with open(sti, newline="", encoding="utf-8") as f:
        return {(int(r["voyageid"]), int(r["horisont_timer"])): r for r in csv.DictReader(f)}


def anlop_i_split(anlop, features, split):
    """Anløpene i ``split`` (``validering`` eller ``test``), i fast rekkefølge (voyageid)."""
    deler = {}
    for (vid, _), r in features.items():
        if deler.setdefault(vid, r["del"]) != r["del"]:
            raise Avvik(f"seilas {vid} har ulik del i features.csv ved de to horisontene")
    if split == "test":
        ut = [a for a in anlop if a.split == "test"]
        feil = [a.voyageid for a in ut if deler.get(a.voyageid, "test") != "test"]
    elif split == "validering":
        ut = [a for a in anlop if deler.get(a.voyageid) == "validering"]
        feil = [a.voyageid for a in ut if a.split != "train"]
    else:
        raise ValueError(f"ukjent split {split!r}")
    if feil:
        raise Avvik(f"split i features.csv og anlop.csv er uenige for {split}: voyageid {sorted(feil)[:10]}")
    return sorted(ut, key=lambda a: a.voyageid)


def har_tilstand(rad):
    return rad is not None and rad["har_tilstand"] == "1"


def er_f6(rad):
    """F6: i ankomstsonen ved kuttet, regnet fra posisjonen (beslutning 11, valg 7)."""
    return har_tilstand(rad) and rad["i_sonen_ved_kutt"] == "1"


def i_modellutvalg(a, rad):
    """Beslutning 12: Øvrige med tilstand ved kuttet og F6 = 0. Alle andre rader går til baselinen."""
    return a.gruppe == T.TRENGRUPPE and har_tilstand(rad) and not er_f6(rad)


def radsett(anlop, features, h):
    """{navn: [Anlop]} for én horisont. Modellutvalget er et delsett av Øvrige, all trafikk."""
    ovrige = [a for a in anlop if a.gruppe == T.TRENGRUPPE]
    return {
        "ovrige_alle": ovrige,
        "ovrige_modellutvalg": [a for a in ovrige if i_modellutvalg(a, features.get((a.voyageid, h)))],
        "passasjer": [a for a in anlop if a.gruppe == "Passasjer"],
    }


def baseline_prediksjoner(anlop, h):
    """{voyageid: Prediksjon} fra ``BaselinePrediktor``, hvert anløp ved sitt eget kuttpunkt."""
    prediktor = BaselinePrediktor()
    ut = {}
    for a in anlop:
        naa = a.eta_reported - dt.timedelta(hours=h)
        inp = lag_input(a, naa)
        if inp.horisont_timer != h:
            raise Avvik(f"seilas {a.voyageid}: lag_input ga horisont {inp.horisont_timer}, ikke {h}")
        [p] = prediktor.prediker([inp], naa)
        ut[a.voyageid] = p
    return ut


def modell_prediksjoner(artefakt, anlop, features, h, baseline):
    """{voyageid: Prediksjon}: artefaktet for modellutvalget, baselinen (uten varsel) for resten."""
    if artefakt["horisont"] != h:
        raise Avvik(f"artefaktet er for {artefakt['horisont']} t, ikke {h} t")
    utvalg = [a for a in anlop if i_modellutvalg(a, features.get((a.voyageid, h)))]
    avvik = T.prediker(artefakt, [features[(a.voyageid, h)] for a in utvalg]) if utvalg else []
    ut = dict(baseline)
    offset_min = artefakt["offset_ovrige_min"]
    for a, avvik_min in zip(utvalg, avvik):
        b = baseline[a.voyageid]
        avvik_min = float(avvik_min)
        ut[a.voyageid] = Prediksjon(
            voyageid=a.voyageid, horisont_timer=b.horisont_timer,
            predikert_ankomst=b.forklaring["eta_reported"] - dt.timedelta(minutes=offset_min - avvik_min),
            forventet_forsinket=avvik_min > VARSEL_MIN,
            forklaring={"metode": "modell", "variant": artefakt["variant"], "predikert_avvik_min": avvik_min},
        )
    return ut


def _r(x, siffer=6):
    return None if x is None else round(float(x), siffer)


def _varsel(v):
    return {"n": v.n, "forsinket": v.forsinket, "varsler": v.varsler, "treff": v.treff,
            "presisjon": _r(v.presisjon), "recall": _r(v.recall), "f1": _r(v.f1)}


def score_arm(prediksjoner, anlop, kalibrert):
    """Alle tall for én arm på ``anlop``. ``kalibrert`` (baselinen) definerer ``er_forsinket``."""
    p = [prediksjoner[a.voyageid] for a in anlop]
    k = [kalibrert[a.voyageid] for a in anlop]
    treff = andel_innenfor(p, anlop, TREFF_MIN)
    feil = absolutt_feil(p, anlop)
    return {"n": treff.n, "treff_30": treff.treff, "andel_30": _r(treff.andel),
            "mae_min": _r(feil.mae_min, 4), "median_min": _r(feil.median_min, 4),
            "varsel": _varsel(varselmetrikker(p, anlop, k, VARSEL_MIN))}


def _antall(anlop, features, h, sett):
    ovrige, utvalg = sett["ovrige_alle"], sett["ovrige_modellutvalg"]

    def n(rader, fasit=False):
        return sum(1 for a in rader if not fasit or har_fasit(a))

    rad = {a.voyageid: features.get((a.voyageid, h)) for a in anlop}
    tilstand = [a for a in ovrige if har_tilstand(rad[a.voyageid])]
    f6 = [a for a in ovrige if er_f6(rad[a.voyageid])]
    antall = {
        "ovrige": {"rader": n(ovrige), "med_fasit": n(ovrige, True),
                   "med_tilstand": n(tilstand), "med_tilstand_med_fasit": n(tilstand, True),
                   "f6": n(f6), "f6_med_fasit": n(f6, True),
                   "modellutvalg": n(utvalg), "modellutvalg_med_fasit": n(utvalg, True)},
        "passasjer": {"rader": n(sett["passasjer"]), "med_fasit": n(sett["passasjer"], True)},
    }
    o = antall["ovrige"]
    andel = {"alle_rader": _r(o["modellutvalg"] / o["rader"]) if o["rader"] else None,
             "med_fasit": _r(o["modellutvalg_med_fasit"] / o["med_fasit"]) if o["med_fasit"] else None}
    return antall, andel


def evaluer_horisont(anlop, features, h, artefakter=None):
    """Blokken for én horisont. ``artefakter`` = {arm: artefakt}, eller None for bare baseline."""
    sett = radsett(anlop, features, h)
    baseline = baseline_prediksjoner(anlop, h)
    armer = {"baseline": baseline}
    for arm, artefakt in (artefakter or {}).items():
        armer[arm] = modell_prediksjoner(artefakt, anlop, features, h, baseline)
    antall, andel = _antall(anlop, features, h, sett)
    blokk = {"antall": antall, "andel_modellutvalg": andel}
    for navn, rader in sett.items():
        armnavn = ["baseline"] if navn == "passasjer" else list(armer)
        blokk[navn] = {arm: score_arm(armer[arm], rader, baseline) for arm in armnavn}
        if navn != "passasjer":
            k = [baseline[a.voyageid] for a in rader]
            blokk[navn]["varsle_alle"] = _varsel(varsle_alle(rader, k, VARSEL_MIN))
            ns = {v["n"] for arm, v in blokk[navn].items() if arm != "varsle_alle"}
            if len(ns) != 1:
                raise Avvik(f"H={h}, {navn}: armene er scoret på ulikt antall rader {sorted(ns)}")
    return blokk


def last_artefakter(modell_dir, features_sti, anlop_sti):
    """{H: {arm: artefakt}}. Sjekker sha256 mot utdragene og offseten mot baseline.json før noe annet."""
    import joblib

    sha = {"features_sha256": sha256_fil(features_sti), "anlop_sha256": sha256_fil(anlop_sti),
           "baseline_sha256": sha256_fil(BASELINE_FIL)}
    with open(BASELINE_FIL, encoding="utf-8") as f:
        offset = json.load(f)["offset_minutter"][T.TRENGRUPPE]
    ut, filer = {}, {}
    for h in HORISONTER:
        ut[h] = {}
        for arm, variant in ARMER.items():
            sti = Path(modell_dir) / T.filnavn(h, variant)
            if not sti.is_file():
                raise Avvik(f"fant ikke artefaktet {sti}")
            art = joblib.load(sti)
            for k, v in sha.items():
                if art.get(k) != v:
                    raise Avvik(f"{sti.name}: {k} i artefaktet stemmer ikke med de committede filene. "
                                "Artefaktet er trent på andre data; tren på nytt eller sjekk ut riktige filer.")
            if art.get("offset_ovrige_min") != offset:
                raise Avvik(f"{sti.name}: offset_ovrige_min {art.get('offset_ovrige_min')} ≠ baseline.json {offset}")
            if art.get("horisont") != h or art.get("variant") != variant:
                raise Avvik(f"{sti.name}: artefaktet er {art.get('horisont')} t / {art.get('variant')}")
            ut[h][arm] = art
            filer[sti.name] = sha256_fil(sti)
    return ut, dict(sha, artefakter_sha256=filer)


def evaluer(anlop, features, split, artefakter=None):
    """{"split": .., "horisonter": {"6": blokk, "24": blokk}}."""
    rader = anlop_i_split(anlop, features, split)
    return {"split": split, "antall_anlop": len(rader),
            "horisonter": {str(h): evaluer_horisont(rader, features, h, artefakter and artefakter[h])
                           for h in HORISONTER}}


def oppdater(gammel, nokkel, blokk, dato=None):
    """Ny ``metrikker.json`` fra den gamle. Bare ``nokkel`` byttes. ``nokkel == "test"`` øker telleren og logger ``dato``."""
    ny = dict(gammel or {})
    ny.setdefault("testkjoringer", 0)
    ny.setdefault("testkjoringer_logg", [])
    ny["beskrivelse"] = ("Modell mot kalibrert baseline på de samme anløpene (E2-S06, PRD FR10, beslutning 11 og 12). "
                         "Laget med scripts/evaluer.py.")
    ny["treff_min"], ny["varsel_min"] = TREFF_MIN, VARSEL_MIN
    ny[nokkel] = blokk
    if nokkel == "test":
        if dato is None:
            raise ValueError("en testkjøring må ha dato")
        ny["testkjoringer"] = ny["testkjoringer"] + 1
        ny["testkjoringer_logg"] = list(ny["testkjoringer_logg"]) + [{"nr": ny["testkjoringer"], "dato": dato}]
    return ny


def skriv_json(sti, data):
    sti = Path(sti)
    sti.parent.mkdir(parents=True, exist_ok=True)
    tmp = sti.with_name(sti.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, sti)


def _pst(x):
    return "–" if x is None else f"{x:6.1%}"


def _f(x):
    return "–" if x is None else f"{x:.2f}"


def skriv_tabell(resultat, ut=sys.stdout):
    print(f"Split: {resultat['split']} ({resultat['antall_anlop']} anløp)", file=ut)
    for h, blokk in resultat["horisonter"].items():
        o = blokk["antall"]["ovrige"]
        andel = blokk["andel_modellutvalg"]
        print(f"\nH = {h} t. Øvrige: {o['rader']} rader, {o['med_fasit']} med fasit, {o['med_tilstand']} med tilstand, "
              f"{o['f6']} F6, {o['modellutvalg']} i modellutvalget ({o['modellutvalg_med_fasit']} med fasit). "
              f"Modellandel: {_pst(andel['alle_rader'])} av alle, {_pst(andel['med_fasit'])} av dem med fasit.", file=ut)
        print(f"  {'radsett':20} {'arm':22} {'n':>5} {'±30':>7} {'MAE':>7} {'median':>7} {'P':>5} {'R':>5} {'F1':>5}",
              file=ut)
        for navn in ("ovrige_modellutvalg", "ovrige_alle", "passasjer"):
            for arm, v in blokk[navn].items():
                if arm == "varsle_alle":
                    print(f"  {navn:20} {'«varsle alle»':22} {v['n']:5} {'':>7} {'':>7} {'':>7} "
                          f"{_f(v['presisjon']):>5} {_f(v['recall']):>5} {_f(v['f1']):>5}", file=ut)
                    continue
                s = v["varsel"]
                print(f"  {navn:20} {arm:22} {v['n']:5} {_pst(v['andel_30']):>7} {v['mae_min']:7.1f} "
                      f"{v['median_min']:7.1f} {_f(s['presisjon']):>5} {_f(s['recall']):>5} {_f(s['f1']):>5}", file=ut)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    modus = ap.add_mutually_exclusive_group()
    modus.add_argument("--test", action="store_true", help="evaluer testperioden (teller testkjøringen)")
    modus.add_argument("--bare-baseline", action="store_true",
                       help="bare baselinen på testperioden, uten modell og uten å telle en testkjøring")
    for k, v in STANDARD.items():
        ap.add_argument("--" + k.replace("_", "-"), type=Path, default=v)
    args = ap.parse_args(argv)
    for sti in (args.features, args.anlop, BASELINE_FIL):
        if not Path(sti).is_file():
            print(f"Fant ikke {sti}. Kjør fra repo-roten.", file=sys.stderr)
            return 2

    try:
        if args.bare_baseline:
            artefakter = None
            kilder = {"features_sha256": sha256_fil(args.features), "anlop_sha256": sha256_fil(args.anlop),
                      "baseline_sha256": sha256_fil(BASELINE_FIL)}
            split, nokkel = "test", "test_bare_baseline"
        else:
            artefakter, kilder = last_artefakter(args.modell_dir, args.features, args.anlop)
            split, nokkel = ("test", "test") if args.test else ("validering", "validering")
        resultat = evaluer(last_utdrag(args.anlop), les_features(args.features), split, artefakter)
    except Avvik as exc:
        print(f"Stopper, ingenting er skrevet: {exc}", file=sys.stderr)
        return 2

    blokk = dict(resultat, kilder=kilder)
    if nokkel == "validering":
        blokk["merknad"] = MERKNAD_VALIDERING
    gammel = json.loads(args.ut.read_text(encoding="utf-8")) if args.ut.is_file() else None
    dato = dt.date.today().isoformat() if nokkel == "test" else None
    skriv_json(args.ut, oppdater(gammel, nokkel, blokk, dato))
    skriv_tabell(resultat)
    print(f"\nSkrev blokken «{nokkel}» til {args.ut}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
