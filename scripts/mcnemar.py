"""McNemars test for ±30 min på testperioden, modell mot baseline på modellutvalget (E2-S10, tilleggsanalyse).

Tilleggsanalyse regnet etter den ene testkjøringen (Felipe, 13.11.2026). Den endrer ikke dommen, som er avgjort
av kriteriene i briefen på tallene i ``data/modell/metrikker.json``. McNemar trenger antall uenige par (anløp der
bare én av armene treffer), og ``metrikker.json`` har bare summene. Testradene leses derfor på nytt, med:

- de samme committede artefaktene og den samme prediksjonskoden som testkjøringen (funksjonene i ``scripts/evaluer.py``).
  Treffregelen per anløp (``_treff``: |faktisk − predikert| ≤ 30 min) er skrevet her, likt ``app.metrikker.andel_innenfor``,
  og summene sjekkes mot ``metrikker.json``
- en sjekk først om de låste filene er uendret siden kjøringens commit (``testkjoringer_logg[-1].commit``)
- en sjekk etterpå om summene er nøyaktig lik ``test``-blokken. Er de ikke det, skrives ingenting.

Bare krysstabellen (begge riktige, bare modell, bare baseline, ingen) og p-verdien lagres, i
``data/modell/mcnemar.json``. Prediksjoner per anløp lagres ikke. p-verdien er den eksakte tosidige
binomialtesten på de uenige parene (p = 0,5).

    .venv/bin/python scripts/mcnemar.py
"""
import datetime as dt
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("evaluer", REPO_ROT / "scripts" / "evaluer.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

UT = REPO_ROT / "data" / "modell" / "mcnemar.json"
RADSETT = "ovrige_modellutvalg"
LAASTE_STIER = (":(glob)data/modell/*.joblib", "data/modell/modellvalg.json", "data/utdrag", "data/baseline.json", "scripts/evaluer.py", "scripts/tren.py",
                "app/prediksjon", "app/metrikker.py", "app/data.py")
MERKNAD = ("Tilleggsanalyse regnet etter testkjøringen. Endrer ikke dommen. Testradene er lest på nytt med de samme "
           "artefaktene og den samme koden som testkjøringen, fordi metrikker.json bare har summene. Bare "
           "krysstabellen og p-verdien er lagret.")


class Avvik(Exception):
    """Gjennomløpet stemmer ikke med testkjøringen. Ingenting skrives."""


def p_mcnemar_eksakt(bare_modell, bare_baseline):
    """Eksakt tosidig McNemar: binomialtest av min(b, c) blant b + c uenige par, p = 0,5. Ingen uenige par gir 1."""
    n = bare_modell + bare_baseline
    if n == 0:
        return 1.0
    k = min(bare_modell, bare_baseline)
    hale = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * hale)


def krysstabell(treff_modell, treff_baseline):
    """{begge, bare_modell, bare_baseline, ingen} fra to like lange lister med True/False per anløp."""
    if len(treff_modell) != len(treff_baseline):
        raise ValueError("armene har ulikt antall anløp")
    par = list(zip(treff_modell, treff_baseline))
    return {"begge": sum(m and b for m, b in par), "bare_modell": sum(m and not b for m, b in par),
            "bare_baseline": sum(b and not m for m, b in par), "ingen": sum(not m and not b for m, b in par)}


def _treff(prediksjoner, anlop):
    grense = dt.timedelta(minutes=ev.TREFF_MIN)
    return [abs(a.faktisk_ankomst - prediksjoner[a.voyageid].predikert_ankomst) <= grense for a in anlop]


def sjekk_uendret(commit):
    """De låste filene er like i arbeidstreet og i kjøringens commit (``git diff --quiet``), og det finnes ingen
    ikke-sporede filer under dem (``git status --porcelain``)."""
    try:
        r = subprocess.run(["git", "diff", "--quiet", commit, "--", *LAASTE_STIER], cwd=REPO_ROT)
        ukjente = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", *LAASTE_STIER],
                                 cwd=REPO_ROT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Avvik(f"git er ikke tilgjengelig ({exc})") from exc
    if r.returncode != 0 or ukjente:
        raise Avvik(f"de låste filene er endret siden testkjøringens commit {commit}")


def beregn(metrikker):
    if metrikker.get("testkjoringer") != 1 or "test" not in metrikker:
        raise Avvik("krever nøyaktig én testkjøring i metrikker.json")
    logg = metrikker.get("testkjoringer_logg") or []
    if not logg or "commit" not in logg[-1]:
        raise Avvik("testkjoringer_logg mangler commit")
    commit = logg[-1]["commit"]
    sjekk_uendret(commit)
    artefakter, _ = ev.last_artefakter(ev.STANDARD["modell_dir"], ev.STANDARD["features"], ev.STANDARD["anlop"])
    features = ev.les_features(ev.STANDARD["features"])
    anlop = ev.anlop_i_split(ev.last_utdrag(ev.STANDARD["anlop"]), features, "test")
    ut = {}
    for h in ev.HORISONTER:
        utvalg = [a for a in ev.radsett(anlop, features, h)[RADSETT] if ev.har_fasit(a)]
        baseline = ev.baseline_prediksjoner(anlop, h)
        modell = ev.modell_prediksjoner(artefakter[h]["modell"], anlop, features, h, baseline)
        tab = krysstabell(_treff(modell, utvalg), _treff(baseline, utvalg))
        fasit = metrikker["test"]["horisonter"][str(h)][RADSETT]
        sjekk = {"modell": (tab["begge"] + tab["bare_modell"], fasit["modell"]["treff_30"]),
                 "baseline": (tab["begge"] + tab["bare_baseline"], fasit["baseline"]["treff_30"]),
                 "n": (sum(tab.values()), fasit["modell"]["n"])}
        ulike = {k: v for k, v in sjekk.items() if v[0] != v[1]}
        if ulike:
            raise Avvik(f"H={h}: gjennomløpet gir andre summer enn testkjøringen (nytt, metrikker.json): {ulike}")
        ut[str(h)] = dict(tab, n=sum(tab.values()), uenige=tab["bare_modell"] + tab["bare_baseline"],
                          p_verdi=float(f"{p_mcnemar_eksakt(tab['bare_modell'], tab['bare_baseline']):.6g}"))
    return {"merknad": MERKNAD, "radsett": RADSETT, "testkjoring_commit": commit, "test": "eksakt tosidig",
            "horisonter": ut}


def _p(x):
    return f"{x:.1e}".replace(".", ",") if x < 1e-4 else f"{x:.4f}".replace(".", ",")


def tabell(data):
    """Markdown-tabellen til resultatnotatet."""
    linjer = ["| Horisont | n | Begge riktige | Bare modell | Bare baseline | Ingen | Uenige par | p (eksakt) |",
              "|---|---|---|---|---|---|---|---|"]
    for h in ("6", "24"):
        v = data["horisonter"][h]
        linjer.append(f"| {h} t | {v['n']} | {v['begge']} | {v['bare_modell']} | {v['bare_baseline']} | "
                      f"{v['ingen']} | {v['uenige']} | {_p(v['p_verdi'])} |")
    return "\n".join(linjer)


def main(argv=None):
    """Uten argumenter: analysen, én gang. Finnes ``mcnemar.json``, stopper den (testradene leses ikke på nytt).
    ``--bare-tabell``: skriv tabellen fra ``mcnemar.json`` uten å lese testradene."""
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--bare-tabell"]:
        print(tabell(json.loads(UT.read_text(encoding="utf-8"))))
        return 0
    if argv:
        print("Bruk: scripts/mcnemar.py [--bare-tabell]", file=sys.stderr)
        return 2
    if UT.exists():
        print(f"Stopper, ingenting er skrevet: {UT} finnes. Analysen er gjort én gang (E2-S10), og en ny kjøring "
              "ville lest testradene på nytt. Bruk --bare-tabell for å skrive tabellen.", file=sys.stderr)
        return 2
    try:
        data = beregn(json.loads(ev.STANDARD["ut"].read_text(encoding="utf-8")))
    except (Avvik, ev.Avvik, OSError, ValueError) as exc:
        print(f"Stopper, ingenting er skrevet: {exc}", file=sys.stderr)
        return 2
    ev.skriv_json(UT, data)
    print(tabell(data))
    print(f"\nSkrev {UT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
