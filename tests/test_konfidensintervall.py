"""Konfidensintervallene og den nye dommen (E2-S11). Leser bare committede JSON-filer, aldri testradene."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("konfidensintervall", REPO_ROT / "scripts" / "konfidensintervall.py")
ki = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ki)


def test_analytisk_ki_kjent_verdi():
    # b = 123, c = 54, n = 733: d = 69/733, SE = √(177 − 69²/733) / 733
    d, lo, hi = ki.analytisk_ki(123, 54, 733)
    assert d == pytest.approx(69 / 733)
    se = ((177 - 69 ** 2 / 733) ** 0.5) / 733
    assert (lo, hi) == pytest.approx((d - ki.Z * se, d + ki.Z * se))


def test_ingen_uenige_gir_null_bredde():
    d, lo, hi = ki.analytisk_ki(0, 0, 100)
    assert d == lo == hi == 0
    tab = {"n": 100, "begge": 60, "bare_modell": 0, "bare_baseline": 0, "ingen": 40}
    assert np.all(ki.bootstrap_treff(tab, np.random.default_rng(0), trekk=200) == 0)


@pytest.mark.parametrize("nedre, dom", [
    (0.060, "bestått"),
    (0.030001, "bestått"),       # rett over marginen
    (0.030, "ikke påvist"),      # lik marginen er ikke over (gruppa, 17.11.2026)
    (0.029999, "ikke påvist"),   # rett under
    (-0.020, "ikke påvist"),
])
def test_dom_grenser(nedre, dom):
    assert ki.dom_treff(nedre) == dom


def test_samme_regel_som_panelet():
    from app.panel import dom_treff
    for nedre in (0.060, 0.030001, 0.030, 0.029999, -0.020):
        assert ki.dom_treff(nedre) == dom_treff(nedre, ki.MARGIN)


def test_f1_varsle_alle():
    # 57 forsinkede av 733: TP = 57, FP = 676, FN = 0 → 2·57 / (2·57 + 676)
    assert float(ki.f1(np.array(57), np.array(676), np.array(0))) == pytest.approx(114 / 790)
    assert float(ki.f1(np.array(0), np.array(0), np.array(0))) == 0.0


def test_forveksling_fra_varseltall():
    fv = ki.forveksling({"treff": 22, "varsler": 38, "forsinket": 57, "n": 733})
    assert fv == {"tp": 22, "fp": 16, "fn": 35, "tn": 660}


def test_committet_fil_lik_ny_beregning():
    """Fast seed: en ny beregning fra de committede filene gir nøyaktig den committede fila."""
    if not ki.UT.is_file():
        pytest.skip("konfidensintervall.json er ikke laget ennå")
    ny = ki.beregn(json.loads(ki.MCNEMAR.read_text(encoding="utf-8")), json.loads(ki.METRIKKER.read_text(encoding="utf-8")))
    assert json.loads(json.dumps(ny, ensure_ascii=False)) == json.loads(ki.UT.read_text(encoding="utf-8"))


def test_committet_f1_lik_metrikker():
    """Forvekslingsmatrisen gir F1-verdiene i metrikker.json, så intervallet bygger på de samme tallene."""
    if not ki.UT.is_file():
        pytest.skip("konfidensintervall.json er ikke laget ennå")
    data = json.loads(ki.UT.read_text(encoding="utf-8"))
    for v in data["horisonter"].values():
        fv = v["varsel_f1"]["forveksling"]
        assert float(ki.f1(np.array(fv["tp"]), np.array(fv["fp"]), np.array(fv["fn"]))) == pytest.approx(
            v["varsel_f1"]["modell"], abs=1e-6)


def test_tabellen_i_notatet():
    if not ki.UT.is_file():
        pytest.skip("konfidensintervall.json er ikke laget ennå")
    assert ki.tabell(json.loads(ki.UT.read_text(encoding="utf-8"))) in (
        REPO_ROT / "docs" / "resultater.md").read_text(encoding="utf-8")


def test_dommen_bruker_bootstrap_ikke_analytisk(monkeypatch):
    """Dommen i fila følger nedre grense fra bootstrap. Et analytisk intervall langt over marginen endrer den ikke
    (mutasjonssjekken, E2-S11)."""
    monkeypatch.setattr(ki, "analytisk_ki", lambda b, c, n: (0.0, 0.9, 0.95))
    tab = {"n": 200, "begge": 80, "bare_modell": 20, "bare_baseline": 20, "ingen": 80}
    varsel = {"treff": 5, "varsler": 10, "forsinket": 20, "n": 200, "f1": 1 / 3}
    blokk = {"modell": {"varsel": varsel}, "varsle_alle": {"f1": 40 / 220}}
    data = ki.beregn({"testkjoring_commit": "x", "horisonter": {h: tab for h in ki.HORISONTER}},
                     {"test": {"horisonter": {h: {ki.RADSETT: blokk} for h in ki.HORISONTER}}})
    for v in data["horisonter"].values():
        assert v["treff_30"]["analytisk"][0] == 0.9
        assert v["treff_30"]["bootstrap"][0] < ki.MARGIN
        assert v["treff_30"]["dom"] == "ikke påvist"
