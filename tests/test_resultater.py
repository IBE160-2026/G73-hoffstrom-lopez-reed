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
