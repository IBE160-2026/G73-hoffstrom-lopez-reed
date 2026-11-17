"""Tabellene i resultatnotatet (E2-S10), med en syntetisk ``metrikker.json``. Tallene er oppdiktet.

Ekte testtall leses bare i ``tests/test_resultater.py``, og bare fra den committede fila (regelen om testrader).
"""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from conftest import syntetisk_blokk

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("resultattabeller", REPO_ROT / "scripts" / "resultattabeller.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

HASH = "c" * 40


def _med_ablasjon(blokk, treff_minus=10):
    """Legg til ablasjonsarmen (som ``scripts/evaluer.py`` skriver) med færre treff enn modellen."""
    blokk = copy.deepcopy(blokk)
    for h in blokk["horisonter"].values():
        for radsett in ("ovrige_modellutvalg", "ovrige_alle"):
            a = copy.deepcopy(h[radsett]["modell"])
            a["treff_30"] -= treff_minus
            a["andel_30"] = a["treff_30"] / a["n"]
            a["mae_min"] = 61.25
            h[radsett]["ablasjon_uten_f13_f14"] = a
    return blokk


def _data(**test_kw):
    return {"testkjoringer": 1, "testkjoringer_logg": [{"nr": 1, "dato": "2026-11-13", "commit": HASH}],
            "validering": _med_ablasjon(syntetisk_blokk(modell_treff=280)),
            "test": _med_ablasjon(syntetisk_blokk(**test_kw)),
            "test_bare_baseline": syntetisk_blokk()}


def test_alle_tabellene_finnes():
    tabeller = rt.render(_data())
    assert list(tabeller) == list(rt.REKKEFOLGE)
    md = rt.som_markdown(tabeller)
    for navn in rt.REKKEFOLGE:
        assert f"### {rt.OVERSKRIFTER[navn]}\n\n{tabeller[navn]}" in md


def test_hovedtabellen_har_briefens_form():
    linjer = rt.render(_data())["hovedtabell"].splitlines()
    assert linjer[0] == ("| Rad | Testanløp med fasit | Modellandel (av Øvrige-anløp med fasit) | Baseline, ±30 min | "
                         "Modell, ±30 min | Grunnrate forsinket | F1 «varsle alle» | F1 modell |")
    assert linjer[2] == ("| **Modellutvalget** (avgjør bestått/ikke bestått) | 400 / 400 | 66,7 % / 66,7 % | "
                         "62,5 % (250/400) / 65,0 % (260/400) | 75,0 % (300/400) / 80,0 % (320/400) | "
                         "15,0 % (60/400) / 17,5 % (70/400) | 0,26 / 0,30 | 0,60 / 0,58 |")
    assert linjer[3].startswith("| **All Øvrige-trafikk, med delegering** | 600 / 600 | 66,7 % / 66,7 % | "
                                "41,7 % (250/600) / 43,3 % (260/600) | 50,0 % (300/600) / 53,3 % (320/600) | "
                                "20,0 % (120/600) / 23,3 % (140/600) | 0,33 / 0,38 |")
    assert len(linjer) == 4


def test_dom_bestatt():
    dom = rt.render(_data())["dom"].splitlines()[2:]
    assert dom == [
        "| 6 t | Innenfor ±30 min høyere enn baselinen | 75,0 % (300/400) | 62,5 % (250/400) | bestått |",
        "| 6 t | Varsel-F1 høyere enn «varsle alle» | 0,600 | 0,261 | bestått |",
        "| 24 t | Innenfor ±30 min høyere enn baselinen | 80,0 % (320/400) | 65,0 % (260/400) | bestått |",
        "| 24 t | Varsel-F1 høyere enn «varsle alle» | 0,582 | 0,298 | bestått |",
    ]


def test_dom_ikke_bestatt_sies_like_tydelig():
    """Taper modellen, står «ikke bestått» i samme kolonne og form som «bestått»."""
    dom = rt.render(_data(modell_treff=200, modell_varsler=100, modell_varseltreff=5))["dom"]
    assert "| 6 t | Innenfor ±30 min høyere enn baselinen | 50,0 % (200/400) | 62,5 % (250/400) | ikke bestått |" in dom
    assert "| 6 t | Varsel-F1 høyere enn «varsle alle» | 0,062 | 0,261 | ikke bestått |" in dom
    assert "nesten" not in dom and "på nivå" not in dom


def test_likt_er_ikke_bestatt():
    """Kravet er «høyere enn». Like verdier er ikke bestått."""
    dom = rt.render(_data(modell_treff=250))["dom"]
    assert "| 6 t | Innenfor ±30 min høyere enn baselinen | 62,5 % (250/400) | 62,5 % (250/400) | ikke bestått |" in dom


def test_dommen_viser_ulike_verdier_ulikt():
    """Et tap som runder til samme tall, vises med flere desimaler (ingen avrunding gjør et tap til «likt»)."""
    data = _data()
    m = data["test"]["horisonter"]["6"]["ovrige_modellutvalg"]
    m["modell"]["andel_30"], m["baseline"]["andel_30"] = 0.59101, 0.59149
    m["modell"]["varsel"]["f1"], m["varsle_alle"]["f1"] = 0.14412, 0.14449
    dom = rt.render(data)["dom"]
    assert "| 59,10 % (300/400) | 59,15 % (250/400) | ikke bestått |" in dom
    assert "| 0,1441 | 0,1445 | ikke bestått |" in dom


def test_varsle_alle_uten_f1_kan_ikke_avgjores():
    data = _data()
    data["test"]["horisonter"]["24"]["ovrige_modellutvalg"]["varsle_alle"]["f1"] = None
    assert "| 24 t | Varsel-F1 høyere enn «varsle alle» | 0,582 | kan ikke varsle | kan ikke avgjøres |" in (
        rt.render(data)["dom"])


def test_validering_og_test_er_merket_som_ulike_fit():
    tabell = rt.render(_data())["validering_mot_test"]
    assert ("| 6 t | Modellutvalget | Validering (refit på trening alene) | 400 | 70,0 % (280/400) | "
            "62,5 % (250/400) |") in tabell
    assert ("| 6 t | Modellutvalget | Test (endelige artefakter, trent på trening + validering) | 400 | "
            "75,0 % (300/400) | 62,5 % (250/400) |") in tabell
    assert len(tabell.splitlines()) == 2 + 2 * 2 * 2


def test_ablasjonen():
    tabell = rt.render(_data())["ablasjon"]
    assert ("| 6 t | Modellutvalget | 400 | 75,0 % (300/400) | 72,5 % (290/400) | 0,60 | 0,60 | 50,0 | 61,2 |"
            in tabell)  # 61,25 runder ned (binær 61.25 er eksakt, Python runder halv til partall)


def test_stottetall_og_kontrollgruppen():
    tabell = rt.render(_data())["stottetall"]
    assert "| 6 t | Passasjer (kontrollgruppe) | Baseline | 280 | 75,0 % (210/280) | 50,0 | 20,0 |" in tabell
    assert "Systemet (modell + baseline for resten)" in tabell


def test_dekning_og_testkjoringer():
    tabeller = rt.render(_data())
    assert "| 6 t | 700 | 600 | 550 | 100 | 450 | 400 | 60 av 120 | 280 av 300 |" in tabeller["dekning"]
    assert tabeller["dekning"].startswith("Anløp i testperioden: 1000.")
    assert tabeller["testkjoringer"].startswith("Antall testkjøringer: 1.")
    assert f"| 1 | 2026-11-13 | `{HASH}` |" in tabeller["testkjoringer"]


@pytest.mark.parametrize("endring", [
    lambda d: d.update(testkjoringer=0),
    lambda d: d.pop("test"),
    lambda d: d.pop("validering"),
    lambda d: d.pop("testkjoringer"),
], ids=["null_kjoringer", "uten_test", "uten_validering", "uten_teller"])
def test_uten_testkjoring_ingen_tabeller(endring):
    data = _data()
    endring(data)
    with pytest.raises(rt.Mangler):
        rt.render(data)


def test_kommandolinja(tmp_path, capsys):
    sti = tmp_path / "metrikker.json"
    sti.write_text(json.dumps(_data()), encoding="utf-8")
    assert rt.main(["--metrikker", str(sti)]) == 0
    assert capsys.readouterr().out == rt.som_markdown(rt.render(_data()))
    sti.write_text(json.dumps({"testkjoringer": 0}), encoding="utf-8")
    assert rt.main(["--metrikker", str(sti)]) == 2
    assert "ingen testkjøring" in capsys.readouterr().err


@pytest.mark.parametrize("innhold", ["[]", '"tekst"', json.dumps({"testkjoringer": 1, "validering": {}, "test": {}})],
                         ids=["liste", "streng", "mangler_nokler"])
def test_kommandolinja_feil_form_gir_melding(tmp_path, capsys, innhold):
    sti = tmp_path / "metrikker.json"
    sti.write_text(innhold, encoding="utf-8")
    assert rt.main(["--metrikker", str(sti)]) == 2
    assert "Kan ikke lage tabellene" in capsys.readouterr().err
