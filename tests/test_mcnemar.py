"""McNemar-tilleggsanalysen (E2-S10). Bare rene funksjoner og syntetiske tall, ingen testrader."""
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("mcnemar", REPO_ROT / "scripts" / "mcnemar.py")
mc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mc)


@pytest.mark.parametrize("b, c, p", [
    (6, 0, 0.03125),                 # 2 · 0,5^6
    (0, 6, 0.03125),                 # symmetrisk
    (10, 5, 2 * 4944 / 2 ** 15),     # 2 · Σ C(15, 0..5) / 2^15
    (5, 5, 1.0),                     # likt gir 1 (kappet)
    (0, 0, 1.0),                     # ingen uenige par
    (1, 0, 1.0),                     # 2 · 0,5 = 1
])
def test_p_eksakt(b, c, p):
    assert mc.p_mcnemar_eksakt(b, c) == pytest.approx(p)


def test_krysstabell():
    m = [True, True, False, False, True]
    b = [True, False, True, False, True]
    assert mc.krysstabell(m, b) == {"begge": 2, "bare_modell": 1, "bare_baseline": 1, "ingen": 1}
    with pytest.raises(ValueError):
        mc.krysstabell([True], [True, False])


def test_krever_en_testkjoring():
    for data in ({"testkjoringer": 0}, {"testkjoringer": 2, "test": {}}, {"testkjoringer": 1}):
        with pytest.raises(mc.Avvik):
            mc.beregn(data)


def test_tabell_fra_fil():
    data = {"horisonter": {h: {"n": 10, "begge": 4, "bare_modell": 3, "bare_baseline": 1, "ingen": 2, "uenige": 4,
                                "p_verdi": 0.625} for h in ("6", "24")}}
    t = mc.tabell(data)
    assert "| 6 t | 10 | 4 | 3 | 1 | 2 | 4 | 0,6250 |" in t and "| 24 t |" in t


def test_committet_mcnemar_i_notatet():
    """Etter tilleggsanalysen: tabellen i notatet er lik renderingen fra mcnemar.json, og summene stemmer med
    testblokken i metrikker.json."""
    sti = REPO_ROT / "data" / "modell" / "mcnemar.json"
    if not sti.is_file():
        pytest.skip("mcnemar.json er ikke laget ennå")
    data = json.loads(sti.read_text(encoding="utf-8"))
    metrikker = json.loads((REPO_ROT / "data" / "modell" / "metrikker.json").read_text(encoding="utf-8"))
    assert data["testkjoring_commit"] == metrikker["testkjoringer_logg"][-1]["commit"]
    for h, v in data["horisonter"].items():
        s = metrikker["test"]["horisonter"][h][mc.RADSETT]
        assert v["begge"] + v["bare_modell"] == s["modell"]["treff_30"]
        assert v["begge"] + v["bare_baseline"] == s["baseline"]["treff_30"]
        assert v["n"] == s["modell"]["n"]
        assert v["p_verdi"] == pytest.approx(mc.p_mcnemar_eksakt(v["bare_modell"], v["bare_baseline"]), abs=1e-6)
    assert mc.tabell(data) in (REPO_ROT / "docs" / "resultater.md").read_text(encoding="utf-8")
