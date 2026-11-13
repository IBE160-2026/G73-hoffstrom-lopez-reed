"""Resultatnotatet ``docs/resultater.md`` mot den committede ``data/modell/metrikker.json`` (E2-S10).

Testene leser bare ``test``-blokken i fila, som den ene ``scripts/evaluer.py --test``-kjøringen skrev. Ingen modell
kjøres her. Før testkjøringen (``testkjoringer == 0``) hoppes de over.
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROT = Path(__file__).resolve().parent.parent
METRIKKER = REPO_ROT / "data" / "modell" / "metrikker.json"
NOTAT = REPO_ROT / "docs" / "resultater.md"
_spec = importlib.util.spec_from_file_location("resultattabeller", REPO_ROT / "scripts" / "resultattabeller.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


def _data():
    data = json.loads(METRIKKER.read_text(encoding="utf-8"))
    if data.get("testkjoringer", 0) < 1:
        pytest.skip("testperioden er ikke kjørt ennå (testkjoringer == 0)")
    return data


def test_notat_lik_metrikker():
    """Hver tabell i notatet er lik renderingen fra metrikker.json, ordrett."""
    tabeller = rt.render(_data())
    notat = NOTAT.read_text(encoding="utf-8")
    for navn in rt.REKKEFOLGE:
        assert tabeller[navn] in notat, f"tabellen «{navn}» i docs/resultater.md er ikke lik metrikker.json"


def test_testkjoringen_har_full_commit():
    data = _data()
    logg = data["testkjoringer_logg"]
    assert len(logg) == data["testkjoringer"]
    commit = logg[-1]["commit"]
    assert len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
    assert data["test"]["kilder"]["commit"] == commit


def test_etter_testkjoringen_viser_appen_modellen(monkeypatch):
    """Akseptkriterium 3: den ekte fila gir testvisningen i panelet, og ``auto`` velger modellen i standardvinduet.
    Ingen prediksjon og ingen rendering av ``/``."""
    _data()
    import app.prediksjon as prediksjon
    from app import STANDARD_NAA
    from app.panel import PERIODE_TEST, lag_panel
    from app.prediksjon.modell import ModellPrediktor

    panel = lag_panel(METRIKKER)
    assert panel["etter_test"] and panel["periode"] == PERIODE_TEST and not panel["mangler"]
    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", METRIKKER)
    assert isinstance(prediksjon.velg_prediktor("auto", STANDARD_NAA), ModellPrediktor)
