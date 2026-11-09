"""Modell mot baseline på valideringsdelen, med og uten rader i ankomstsonen ved kuttet (beslutning 12).

Lager tabellen i beslutning 12. Per horisont kjøres samme konfigurasjonssøk som i ``scripts/tren.py``,
fittet på ``trening`` med ``fartoy_*_modellvalg``, og scoret på ``validering``:

- (a) gammel modell (søk på alle rader, også F6), målt på alle valideringsrader
- (b) den samme gamle modellen, målt på valideringsrader utenfor sonen (F6 = 0)
- (c) ny modell (søk bare på rader utenfor sonen), målt på de samme radene som (b)

Baselinen («avvik = 0», kalibrert baseline) og «varsle alle» måles på nøyaktig de samme radene.
Testperioden leses aldri: ``tren.les_features`` kaster testradene. Skriptet skriver ingenting.

    .venv/bin/python scripts/sammenlign_f6.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("tren", REPO_ROT / "scripts" / "tren.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)


def utenfor_sonen(rader):
    return [r for r in rader if r["i_sonen_ved_kutt"] != "1"]


def sok(rader, h):
    """Konfigurasjonssøket fra tren.py for én horisont. Returnerer (modell, kategorier, config)."""
    rader = [r for r in rader if r["horisont_timer"] == str(h)]
    tr = [r for r in rader if r["del"] == "trening"]
    va = [r for r in rader if r["del"] == "validering"]
    kat = T.lag_kategorier(tr, T.FEATURES)
    X_tr, X_va = T.matrise(tr, T.FEATURES, kat, "modellvalg"), T.matrise(va, T.FEATURES, kat, "modellvalg")
    y_tr, y_va = [r["avvik_min"] for r in tr], [r["avvik_min"] for r in va]
    res = []
    for config in T.KANDIDATER:
        m = T.lag_modell(config, T.FEATURES, T.SEED).fit(X_tr, y_tr)
        res.append(dict(T.score(y_va, m.predict(X_va)), config=config, modell=m))
    valgt, _, _ = T.velg(res)
    return res[valgt]["modell"], kat, res[valgt]["config"]


def mal(modell, kat, rader):
    y = [r["avvik_min"] for r in rader]
    pred = modell.predict(T.matrise(rader, T.FEATURES, kat, "modellvalg"))
    return T.score(y, pred), T.score(y, np.zeros(len(y))), T.score(y, np.full(len(y), np.inf))["varsel_f1"]


def main(argv=None):
    with open(REPO_ROT / "data" / "baseline.json", encoding="utf-8") as f:
        offset = json.load(f)["offset_minutter"][T.TRENGRUPPE]
    features = T.les_features((REPO_ROT / "data" / "utdrag" / "features.csv").read_bytes())
    alle = T.treningsrader(features, T.les_csv(REPO_ROT / "data" / "utdrag" / "anlop.csv"), offset,
                           utelat_i_sonen=False)
    print("| H | Variant | n | ±30 min modell | ±30 min baseline | MAE modell | MAE baseline "
          "| F1 modell | F1 baseline | F1 «varsle alle» | Valgt konfigurasjon |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for h in T.HORISONTER:
        va = [r for r in alle if r["horisont_timer"] == str(h) and r["del"] == "validering"]
        gammel, kat_g, c_g = sok(alle, h)
        ny, kat_n, c_n = sok(utenfor_sonen(alle), h)
        for navn, modell, kat, rader, c in (("(a) gammel, alle rader", gammel, kat_g, va, c_g),
                                            ("(b) gammel, uten F6-rader", gammel, kat_g, utenfor_sonen(va), c_g),
                                            ("(c) ny, uten F6-rader", ny, kat_n, utenfor_sonen(va), c_n)):
            m, b, f1_alle = mal(modell, kat, rader)
            print(f"| {h} t | {navn} | {len(rader)} | {m['andel_30']:.1%} | {b['andel_30']:.1%} | {m['mae']:.0f} "
                  f"| {b['mae']:.0f} | {m['varsel_f1']:.2f} | {b['varsel_f1']:.2f} | {f1_alle:.2f} "
                  f"| {c['loss']}, lr {c['learning_rate']}, {c['max_leaf_nodes']} blad |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
