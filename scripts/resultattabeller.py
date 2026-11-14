"""Tabellene i resultatnotatet (E2-S10), rendret fra ``data/modell/metrikker.json``.

Hvert tall i tabellene i ``docs/resultater.md`` kommer herfra. Modulen regner ingenting fra utdrag eller prediksjoner,
den former bare verdiene i fila. ``tests/test_resultater.py::test_notat_lik_metrikker`` sjekker at notatet har
tabellene ordrett.

Tabellene:
- ``testkjoringer``: antall testkjøringer, med dato og commit fra loggen.
- ``hovedtabell``: modellutvalget og all Øvrige-trafikk side om side, per horisont (samme form som i briefen).
- ``dom``: bestått/ikke bestått per horisont, på modellutvalget, med kriteriene fra briefen.
- ``validering_mot_test``: validering (refit på trening) og test (de endelige artefaktene) side om side.
- ``ablasjon``: modellen mot ablasjonen uten F13–F14 på testperioden.
- ``stottetall``: MAE og median (støttetall, aldri hovedtall), også for Passasjer (kontrollgruppe, bare baseline).
- ``dekning``: antall anløp, fasit, AIS-tilstand ved kuttet, F6 og modellutvalget på testperioden.

Dommen sammenligner de uavrundede verdiene. Tallene i dommen vises med så mange desimaler som trengs for at to ulike
verdier aldri ser like ut.

    .venv/bin/python scripts/resultattabeller.py [--metrikker STI]
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
METRIKKER = REPO_ROT / "data" / "modell" / "metrikker.json"
HORISONTER = ("6", "24")
RADSETT = {"ovrige_modellutvalg": "Modellutvalget", "ovrige_alle": "All Øvrige-trafikk, med delegering"}
KAN_IKKE_VARSLE = "kan ikke varsle"
REKKEFOLGE = ("testkjoringer", "hovedtabell", "dom", "validering_mot_test", "ablasjon", "stottetall", "dekning")
OVERSKRIFTER = {
    "testkjoringer": "Testkjøringer",
    "hovedtabell": "Modellutvalget og all Øvrige-trafikk (testperioden)",
    "dom": "Dom per horisont (modellutvalget)",
    "validering_mot_test": "Validering mot test",
    "ablasjon": "Ablasjon uten F13–F14 (testperioden)",
    "stottetall": "Støttetall: MAE og median (testperioden)",
    "dekning": "Dekning ved kuttet (testperioden)",
}


class Mangler(Exception):
    """``metrikker.json`` har ingen testkjøring eller mangler en blokk notatet trenger."""


# --- Formatering -------------------------------------------------------------------------------------------------


def _komma(tekst):
    return tekst.replace(".", ",")


def pst(x, desimaler=1):
    """0.590723 → «59,1 %»."""
    return _komma(f"{x * 100:.{desimaler}f}") + " %"


def brok(teller, nevner):
    return f"{teller}/{nevner}"


def andel(x, teller, nevner, desimaler=1):
    return f"{pst(x, desimaler)} ({brok(teller, nevner)})"


def f1(x, desimaler=2):
    return KAN_IKKE_VARSLE if x is None else _komma(f"{x:.{desimaler}f}")


def minutter(x):
    return _komma(f"{x:.1f}")


def _skilles(a, b, fmt, start):
    """Antall desimaler (fra ``start``, høyst 6) som får ``fmt`` til å vise ulike verdier ulikt."""
    d = start
    while a != b and d < 6 and fmt(a, d) == fmt(b, d):
        d += 1
    return d


def tabell(hode, rader):
    linjer = ["| " + " | ".join(hode) + " |", "|" + "---|" * len(hode)]
    linjer += ["| " + " | ".join(str(c) for c in rad) + " |" for rad in rader]
    return "\n".join(linjer)


def _per_h(blokk, f):
    """«a / b» for 6 t og 24 t."""
    return " / ".join(f(blokk["horisonter"][h]) for h in HORISONTER)


# --- Tabellene ---------------------------------------------------------------------------------------------------


def tabell_testkjoringer(data):
    logg = data.get("testkjoringer_logg") or []
    rader = [[x["nr"], x["dato"], f"`{x.get('commit', 'mangler')}`"] for x in logg]
    return (f"Antall testkjøringer: {data['testkjoringer']}.\n\n"
            + tabell(["Nr.", "Dato", "Commit (full hash)"], rader))


def tabell_hoved(test):
    def rad(navn, radsett, merknad):
        def arm(h, a):
            return h[radsett][a]
        return [
            f"**{navn}**{merknad}",
            _per_h(test, lambda h: str(arm(h, "baseline")["n"])),
            _per_h(test, lambda h: pst(h["andel_modellutvalg"]["med_fasit"])),
            _per_h(test, lambda h: andel(arm(h, "baseline")["andel_30"], arm(h, "baseline")["treff_30"],
                                         arm(h, "baseline")["n"])),
            _per_h(test, lambda h: andel(arm(h, "modell")["andel_30"], arm(h, "modell")["treff_30"],
                                         arm(h, "modell")["n"])),
            _per_h(test, lambda h: andel(arm(h, "varsle_alle")["presisjon"], arm(h, "varsle_alle")["forsinket"],
                                         arm(h, "varsle_alle")["n"])),
            _per_h(test, lambda h: f1(arm(h, "varsle_alle")["f1"])),
            _per_h(test, lambda h: f1(arm(h, "modell")["varsel"]["f1"])),
        ]
    hode = ["Rad", "Testanløp med fasit", "Modellandel (av Øvrige-anløp med fasit)", "Baseline, ±30 min",
            "Modell, ±30 min", "Grunnrate forsinket", "F1 «varsle alle»", "F1 modell"]
    return tabell(hode, [rad("Modellutvalget", "ovrige_modellutvalg", " (avgjør bestått/ikke bestått)"),
                         rad("All Øvrige-trafikk, med delegering", "ovrige_alle", "")])


def dom_horisont(h):
    """[(krav, modell, referanse, dom)] for én horisont på modellutvalget. Uavrundede verdier avgjør."""
    m, b, alle = (h["ovrige_modellutvalg"][a] for a in ("modell", "baseline", "varsle_alle"))
    d = _skilles(m["andel_30"], b["andel_30"], pst, 1)
    treff = ("Innenfor ±30 min høyere enn baselinen",
             andel(m["andel_30"], m["treff_30"], m["n"], d), andel(b["andel_30"], b["treff_30"], b["n"], d),
             "bestått" if m["andel_30"] > b["andel_30"] else "ikke bestått")
    fm, fa = m["varsel"]["f1"], alle["f1"]
    if fa is None:
        dom_f1 = "kan ikke avgjøres"
    else:
        dom_f1 = "bestått" if fm is not None and fm > fa else "ikke bestått"
    d = _skilles(fm, fa, f1, 3) if fm is not None and fa is not None else 3
    varsel = ("Varsel-F1 høyere enn «varsle alle»", f1(fm, d), f1(fa, d), dom_f1)
    return [treff, varsel]


def tabell_dom(test):
    rader = [[f"{h} t", *rad] for h in HORISONTER for rad in dom_horisont(test["horisonter"][h])]
    return tabell(["Horisont", "Krav (briefen)", "Modell", "Referanse", "Dom"], rader)


def tabell_validering_mot_test(validering, test):
    perioder = (("Validering (refit på trening alene)", validering),
                ("Test (endelige artefakter, trent på trening + validering)", test))
    rader = []
    for h in HORISONTER:
        for radsett, navn in RADSETT.items():
            for periode, blokk in perioder:
                s = blokk["horisonter"][h][radsett]
                m, b, alle = s["modell"], s["baseline"], s["varsle_alle"]
                rader.append([f"{h} t", navn, periode, m["n"], andel(m["andel_30"], m["treff_30"], m["n"]),
                              andel(b["andel_30"], b["treff_30"], b["n"]), f1(m["varsel"]["f1"]), f1(alle["f1"])])
    return tabell(["Horisont", "Radsett", "Periode og fit", "n", "Modell, ±30 min", "Baseline, ±30 min",
                   "F1 modell", "F1 «varsle alle»"], rader)


def tabell_ablasjon(test):
    rader = []
    for h in HORISONTER:
        for radsett, navn in RADSETT.items():
            s = test["horisonter"][h][radsett]
            m, a = s["modell"], s["ablasjon_uten_f13_f14"]
            rader.append([f"{h} t", navn, m["n"], andel(m["andel_30"], m["treff_30"], m["n"]),
                          andel(a["andel_30"], a["treff_30"], a["n"]), f1(m["varsel"]["f1"]),
                          f1(a["varsel"]["f1"]), minutter(m["mae_min"]), minutter(a["mae_min"])])
    return tabell(["Horisont", "Radsett", "n", "Modell, ±30 min", "Uten F13–F14, ±30 min", "F1 modell",
                   "F1 uten F13–F14", "MAE modell (min)", "MAE uten F13–F14 (min)"], rader)


def tabell_stottetall(test):
    armer = (("ovrige_modellutvalg", "Modellutvalget", "modell", "Modell"),
             ("ovrige_modellutvalg", "Modellutvalget", "baseline", "Baseline"),
             ("ovrige_alle", "All Øvrige-trafikk", "modell", "Systemet (modell + baseline for resten)"),
             ("ovrige_alle", "All Øvrige-trafikk", "baseline", "Baseline"),
             ("passasjer", "Passasjer (kontrollgruppe)", "baseline", "Baseline"))
    rader = []
    for h in HORISONTER:
        for radsett, navn, arm, armnavn in armer:
            v = test["horisonter"][h][radsett][arm]
            rader.append([f"{h} t", navn, armnavn, v["n"], andel(v["andel_30"], v["treff_30"], v["n"]),
                          minutter(v["mae_min"]), minutter(v["median_min"])])
    return tabell(["Horisont", "Radsett", "Arm", "n", "±30 min", "MAE (min)", "Median absolutt feil (min)"], rader)


def tabell_dekning(test):
    rader = []
    for h in HORISONTER:
        hb = test["horisonter"][h]
        o, p = hb["antall"]["ovrige"], hb["antall"]["passasjer"]
        f_alle = hb["ovrige_alle"]["varsle_alle"]["forsinket"]
        f_utvalg = hb["ovrige_modellutvalg"]["varsle_alle"]["forsinket"]
        rader.append([f"{h} t", o["rader"], o["med_fasit"], o["med_tilstand"], o["f6"], o["modellutvalg"],
                      o["modellutvalg_med_fasit"], f"{f_utvalg} av {f_alle}", f"{p['med_fasit']} av {p['rader']}"])
    return (f"Anløp i testperioden: {test['antall_anlop']}.\n\n"
            + tabell(["Horisont", "Øvrige-anløp", "Med fasit", "Med AIS-tilstand ved kuttet",
                      "I sonen ved kuttet (F6)", "Modellutvalget", "Modellutvalget med fasit",
                      "Forsinkede i modellutvalget, av alle forsinkede Øvrige", "Passasjer med fasit"], rader))


def render(data):
    """{navn: markdown} for alle tabellene. Krever en testkjøring og blokkene ``test`` og ``validering``."""
    if not isinstance(data.get("testkjoringer"), int) or data["testkjoringer"] < 1 or "test" not in data:
        raise Mangler("metrikker.json har ingen testkjøring (testkjoringer < 1 eller ingen test-blokk)")
    if "validering" not in data:
        raise Mangler("metrikker.json mangler blokken validering")
    test, validering = data["test"], data["validering"]
    return {
        "testkjoringer": tabell_testkjoringer(data),
        "hovedtabell": tabell_hoved(test),
        "dom": tabell_dom(test),
        "validering_mot_test": tabell_validering_mot_test(validering, test),
        "ablasjon": tabell_ablasjon(test),
        "stottetall": tabell_stottetall(test),
        "dekning": tabell_dekning(test),
    }


def som_markdown(tabeller):
    return "\n\n".join(f"### {OVERSKRIFTER[navn]}\n\n{tabeller[navn]}" for navn in REKKEFOLGE) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrikker", type=Path, default=METRIKKER)
    args = ap.parse_args(argv)
    try:
        tabeller = render(json.loads(args.metrikker.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, Mangler) as exc:
        print(f"Kan ikke lage tabellene: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(som_markdown(tabeller))
    return 0


if __name__ == "__main__":
    sys.exit(main())
