"""95 % konfidensintervall for parret differanse, modell mot baseline på modellutvalget (E2-S11).

Etter faglærers tilbakemelding på PRD-en (``docs/tilbakemelding-prd.md`` punkt 4.1, 12.11.2026) lykkes modellen på
±30 min hvis forskjellen modell − baseline (punktestimatet) er minst 3,0 prosentpoeng. Forskjellen rapporteres med
95 % KI, men intervallet avgjør ikke dommen. Er forskjellen under 3,0, er resultatet «ikke påvist». Kriteriet ble endret etter testkjøringen, i strengere retning.

Skriptet leser **ikke** testradene. Alt regnes fra filer som allerede er committet:

- ``data/modell/mcnemar.json``: krysstabellen per anløp (begge, bare modell, bare baseline, ingen). Å trekke anløp
  med tilbakelegging er det samme som å trekke fra de fire feltene med sannsynlighet felt/n (multinomial), fordi
  differansen bare avhenger av hvilket felt hvert anløp ligger i.
- ``data/modell/metrikker.json``, ``test``-blokken: varseltallene (treff, varsler, forsinket, n) for modellen. De
  gir hele forvekslingsmatrisen (TP, FP, FN, TN). F1 for «varsle alle» avhenger bare av antall forsinkede i det
  samme trekket, så også F1-differansen er parret. F1 har ingen margin (faglærer foreslo ingen). Intervallet
  rapporteres, men endrer ikke F1-dommen.

Bootstrap: fast seed, 10 000 trekk, persentilintervall (2,5 og 97,5). Analytisk intervall ved siden av:
differanse ± 1,96 · SE, der SE = √((b + c) − (b − c)² / n) / n for parrede andeler (b = bare modell,
c = bare baseline).

    .venv/bin/python scripts/konfidensintervall.py            # regn og skriv data/modell/konfidensintervall.json
    .venv/bin/python scripts/konfidensintervall.py --bare-tabell
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROT = Path(__file__).resolve().parent.parent
MCNEMAR = REPO_ROT / "data" / "modell" / "mcnemar.json"
METRIKKER = REPO_ROT / "data" / "modell" / "metrikker.json"
UT = REPO_ROT / "data" / "modell" / "konfidensintervall.json"
RADSETT = "ovrige_modellutvalg"
HORISONTER = ("6", "24")
SEED = 160
TREKK = 10_000
MARGIN = 0.03
Z = 1.959963984540054
MERKNAD = ("Regnet 17.11.2026, etter testkjøringen, fra krysstabellen i mcnemar.json og varseltallene i "
           "metrikker.json. Testradene er ikke lest. Kriteriet (forskjellen minst 3 prosentpoeng; KI rapporteres, men "
           "avgjør ikke dommen) kom fra faglærers tilbakemelding på PRD-en (12.11.2026) og ble tatt inn etter testkjøringen, "
           "i strengere retning.")


def analytisk_ki(b, c, n):
    """Parret differanse (b − c) / n med Wald-intervall for avhengige andeler."""
    d = (b - c) / n
    se = math.sqrt((b + c) - (b - c) ** 2 / n) / n
    return d, d - Z * se, d + Z * se


def bootstrap_treff(tab, rng, trekk=TREKK):
    """Differanser (bare modell − bare baseline) / n for ``trekk`` multinomiale trekk av n anløp."""
    n = tab["n"]
    felt = np.array([tab["begge"], tab["bare_modell"], tab["bare_baseline"], tab["ingen"]])
    t = rng.multinomial(n, felt / n, size=trekk)
    return (t[:, 1] - t[:, 2]) / n


def f1(tp, fp, fn):
    """F1 = 2TP / (2TP + FP + FN). Ingen treff gir 0."""
    nevner = 2 * tp + fp + fn
    return np.where(nevner > 0, 2 * tp / np.maximum(nevner, 1), 0.0)


def forveksling(varsel):
    tp = varsel["treff"]
    fp = varsel["varsler"] - tp
    fn = varsel["forsinket"] - tp
    return {"tp": tp, "fp": fp, "fn": fn, "tn": varsel["n"] - tp - fp - fn}


def bootstrap_f1(fv, rng, trekk=TREKK):
    """F1 modell − F1 «varsle alle» for ``trekk`` multinomiale trekk av anløpene i forvekslingsmatrisen.
    «Varsle alle» har TP = antall forsinkede (tp + fn) og FP = resten."""
    n = fv["tp"] + fv["fp"] + fv["fn"] + fv["tn"]
    felt = np.array([fv["tp"], fv["fp"], fv["fn"], fv["tn"]])
    t = rng.multinomial(n, felt / n, size=trekk)
    tp, fp, fn = t[:, 0], t[:, 1], t[:, 2]
    forsinket = tp + fn
    return f1(tp, fp, fn) - f1(forsinket, n - forsinket, np.zeros_like(forsinket))


def _ki(verdier):
    lo, hi = np.percentile(verdier, [2.5, 97.5])
    return float(lo), float(hi)


def _r(x):
    return round(float(x), 6)


def dom_treff(differanse_antall, n, margin=MARGIN):
    """Bestått hvis forskjellen (punktestimatet) er minst marginen: (bare modell − bare baseline) / n ≥ margin.
    Ellers «ikke påvist». Intervallet er ikke med. Sammenligningen gjøres på heltall (100 · differanse ≥ 3 · n), så
    nøyaktig 3,0 pp alltid gir bestått, uansett avrunding i flyttall. Samme regel som ``app.panel.dom_treff``."""
    return "bestått" if 100 * differanse_antall >= round(margin * 100, 6) * n else "ikke påvist"


def beregn(mcnemar, metrikker):
    rng = np.random.default_rng(SEED)
    ut = {}
    for h in HORISONTER:
        tab = mcnemar["horisonter"][h]
        blokk = metrikker["test"]["horisonter"][h][RADSETT]
        d, a_lo, a_hi = analytisk_ki(tab["bare_modell"], tab["bare_baseline"], tab["n"])
        b_lo, b_hi = _ki(bootstrap_treff(tab, rng))
        fv = forveksling(blokk["modell"]["varsel"])
        f1_m, f1_a = blokk["modell"]["varsel"]["f1"], blokk["varsle_alle"]["f1"]
        f_lo, f_hi = _ki(bootstrap_f1(fv, rng))
        ut[h] = {
            "n": tab["n"],
            "treff_30": {"differanse": _r(d), "bootstrap": [_r(b_lo), _r(b_hi)], "analytisk": [_r(a_lo), _r(a_hi)],
                         "dom": dom_treff(tab["bare_modell"] - tab["bare_baseline"], tab["n"])},
            "varsel_f1": {"modell": f1_m, "varsle_alle": f1_a, "differanse": _r(f1_m - f1_a),
                          "bootstrap": [_r(f_lo), _r(f_hi)], "forveksling": fv},
        }
    return {"merknad": MERKNAD, "radsett": RADSETT, "seed": SEED, "trekk": TREKK, "margin": MARGIN,
            "intervall": "95 % persentil (bootstrap over anløp); analytisk: Wald for parrede andeler",
            "testkjoring_commit": mcnemar["testkjoring_commit"], "horisonter": ut}


def _pp(x):
    return f"{x * 100:+.1f}".replace(".", ",").replace("-", "−")


def _iv(par, pp=True):
    f = (lambda v: _pp(v).lstrip("+")) if pp else (lambda v: f"{v:.2f}".replace(".", ",").replace("-", "−"))
    return f"[{f(par[0])}; {f(par[1])}]"


def tabell(data):
    """Markdown-tabellene til resultatnotatet: ny dom på ±30 min, og F1-intervallet."""
    linjer = ["| Horisont | n | Modell − baseline, ±30 min (pp) | 95 % KI, bootstrap | 95 % KI, analytisk | Krav (punktestimat) | Dom |",
              "|---|---|---|---|---|---|---|"]
    for h in HORISONTER:
        v = data["horisonter"][h]["treff_30"]
        linjer.append(f"| {h} t | {data['horisonter'][h]['n']} | {_pp(v['differanse'])} | {_iv(v['bootstrap'])} | "
                      f"{_iv(v['analytisk'])} | minst +3,0 pp | {v['dom']} |")
    linjer += ["", "| Horisont | F1 modell | F1 «varsle alle» | Differanse | 95 % KI, bootstrap |", "|---|---|---|---|---|"]
    for h in HORISONTER:
        v = data["horisonter"][h]["varsel_f1"]
        f = lambda x: f"{x:.3f}".replace(".", ",")
        linjer.append(f"| {h} t | {f(v['modell'])} | {f(v['varsle_alle'])} | "
                      f"{('+' if v['differanse'] >= 0 else '−') + f(abs(v['differanse']))} | {_iv(v['bootstrap'], pp=False)} |")
    return "\n".join(linjer)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--bare-tabell"]:
        print(tabell(json.loads(UT.read_text(encoding="utf-8"))))
        return 0
    if argv:
        print("Bruk: scripts/konfidensintervall.py [--bare-tabell]", file=sys.stderr)
        return 2
    data = beregn(json.loads(MCNEMAR.read_text(encoding="utf-8")), json.loads(METRIKKER.read_text(encoding="utf-8")))
    UT.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(tabell(data))
    print(f"\nSkrev {UT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
