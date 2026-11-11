"""Panelet «modell mot baseline» som ren funksjon (E2-S09, FR10): ``app.panel.lag_panel``.

Visningen etter testkjøringen testes bare med syntetiske filer i ``tmp_path`` (regelen om testrader).
Rutetestene står i ``tests/test_ruter.py``.
"""
import json
from pathlib import Path

import pytest
from conftest import syntetisk_blokk

from app.panel import KAN_IKKE_VARSLE, PERIODE_TEST, PERIODE_VALIDERING, lag_panel

EKTE = Path(__file__).resolve().parent.parent / "data" / "modell" / "metrikker.json"


def _fil(tmp_path, data):
    sti = tmp_path / "metrikker.json"
    sti.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return sti


def _celler(panel, h=0, gruppe=0):
    g = panel["horisonter"][h]["grupper"][gruppe]
    return {r["maal"]: [c["tekst"] for c in r["celler"]] for r in g["rader"]}


def test_ekte_fil_gir_valideringsblokken():
    data = json.loads(EKTE.read_text(encoding="utf-8"))
    assert data["testkjoringer"] == 0  # ellers er dette en annen test
    panel = lag_panel(EKTE)
    assert not panel["mangler"] and not panel["etter_test"]
    assert panel["periode"] == PERIODE_VALIDERING
    v = data["validering"]
    assert panel["antall_anlop"] == f"{v['antall_anlop']:,}".replace(",", "\u00a0")
    for h, horisont in zip(("6", "24"), panel["horisonter"]):
        m = v["horisonter"][h]["ovrige_modellutvalg"]["modell"]
        assert horisont["grupper"][0]["rader"][0]["celler"][0]["tekst"] == (
            f"{m['andel_30'] * 100:.1f}".replace(".", ",") + f"\u00a0% ({m['treff_30']}/{m['n']})")
        assert all(g["dom"] is None for g in horisont["grupper"])


def test_tall_og_antall_formateres(tmp_path):
    sti = _fil(tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk(antall_anlop=1566)})
    panel = lag_panel(sti)
    assert panel["antall_anlop"] == "1\u00a0566"
    c = _celler(panel)
    assert c["Innenfor ±30 min"] == ["75,0\u00a0% (300/400)", "62,5\u00a0% (250/400)", "–"]
    assert c["Presisjon"] == ["75,0\u00a0% (30/40)", KAN_IKKE_VARSLE, "15,0\u00a0% (60/400)"]
    assert c["Recall"] == ["50,0\u00a0% (30/60)", KAN_IKKE_VARSLE, "100,0\u00a0% (60/60)"]
    assert c["F1"] == ["0,60", KAN_IKKE_VARSLE, "0,26"]
    h = panel["horisonter"][0]
    assert h["fasit_ovrige"] == "600 av 700" and h["fasit_passasjer"] == "280 av 300"
    assert h["modellandel"] == "66,7\u00a0% (400/600)"
    assert h["grupper"][0]["differanse"] == "+12,5 pp (modellen bedre)"
    assert h["grupper"][0]["differanse_f1"] == "+0,34 (modellen bedre)"
    assert h["grupper"][2]["differanse"] is None and h["grupper"][2]["differanse_f1"] is None


def test_horisontene_viser_egne_tall(tmp_path):
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk()}))
    seks, tjuefire = (_celler(panel, h=i) for i in (0, 1))
    assert seks["Innenfor ±30 min"][:2] == ["75,0\u00a0% (300/400)", "62,5\u00a0% (250/400)"]
    assert tjuefire["Innenfor ±30 min"][:2] == ["80,0\u00a0% (320/400)", "65,0\u00a0% (260/400)"]
    assert seks["Recall"][0] == "50,0\u00a0% (30/60)" and tjuefire["Recall"][0] == "45,7\u00a0% (32/70)"
    assert _celler(panel, h=0, gruppe=2)["Innenfor ±30 min"] == ["75,0\u00a0% (210/280)"]
    assert _celler(panel, h=1, gruppe=2)["Innenfor ±30 min"] == ["71,4\u00a0% (200/280)"]
    assert [h["etikett"] for h in panel["horisonter"]] == ["6 t", "24 t"]


def test_null_er_kan_ikke_varsle_aldri_null(tmp_path):
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk()}))
    passasjer = _celler(panel, gruppe=2)
    assert passasjer["Presisjon"] == passasjer["Recall"] == passasjer["F1"] == [KAN_IKKE_VARSLE]
    assert all(c[1] == KAN_IKKE_VARSLE for k, c in _celler(panel).items() if k != "Innenfor ±30 min")


def test_modell_med_null_varsler_er_ikke_kan_ikke_varsle(tmp_path):
    """0 varsler gir presisjon 0,0 fra metrikkmodulen, ikke null. Andelen 0/0 er ikke definert, så cellen sier
    «ingen varsler (0/0)», verken «0,0 %» eller «kan ikke varsle»."""
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0,
                                      "validering": syntetisk_blokk(modell_varsler=0, modell_varseltreff=0)}))
    c = _celler(panel)
    assert c["Presisjon"][0] == "ingen varsler (0/0)"
    assert c["Recall"][0] == "0,0\u00a0% (0/60)"
    assert c["F1"][0] == "0,00"
    assert KAN_IKKE_VARSLE not in c["Presisjon"][0] + c["Recall"][0] + c["F1"][0]


def test_ingen_forsinkede_er_ikke_0_prosent(tmp_path):
    blokk = syntetisk_blokk()
    alle = blokk["horisonter"]["6"]["ovrige_modellutvalg"]["varsle_alle"]
    alle.update(forsinket=0, treff=0, recall=0.0)
    c = _celler(lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": blokk})))
    assert c["Recall"][2] == "ingen forsinkede (0/0)"


def test_foer_testkjoringen_vises_aldri_test_eller_test_bare_baseline(tmp_path):
    data = {"testkjoringer": 0, "validering": syntetisk_blokk(modell_treff=301),
            "test": syntetisk_blokk(modell_treff=399), "test_bare_baseline": syntetisk_blokk(baseline_treff=111)}
    panel = lag_panel(_fil(tmp_path, data))
    assert panel["periode"] == PERIODE_VALIDERING
    tekst = json.dumps(panel, ensure_ascii=False)
    assert "301/400" in tekst
    assert "399/400" not in tekst and "111/400" not in tekst


def test_etter_testkjoringen_test_med_dom(tmp_path):
    data = {"testkjoringer": 1, "validering": syntetisk_blokk(modell_treff=301), "test": syntetisk_blokk()}
    panel = lag_panel(_fil(tmp_path, data))
    assert panel["etter_test"] and panel["periode"] == PERIODE_TEST
    assert "301/400" not in json.dumps(panel, ensure_ascii=False)
    assert [h["grupper"][0]["dom"] for h in panel["horisonter"]] == [
        ["Innenfor ±30 min: bestått (modell 75,0\u00a0%, baseline 62,5\u00a0%)",
         "Varsel-F1: bestått (modell 0,600, «varsle alle» 0,261)"],
        ["Innenfor ±30 min: bestått (modell 80,0\u00a0%, baseline 65,0\u00a0%)",
         "Varsel-F1: bestått (modell 0,582, «varsle alle» 0,298)"],
    ]
    for h in panel["horisonter"]:
        modellutvalg, alle, passasjer = h["grupper"]
        assert alle["dom"] is None and passasjer["dom"] is None  # dommen avgjøres på modellutvalget


def test_modellen_taper(tmp_path):
    data = {"testkjoringer": 1, "test": syntetisk_blokk(modell_treff=230, modell_varsler=100, modell_varseltreff=5)}
    g = lag_panel(_fil(tmp_path, data))["horisonter"][0]["grupper"][0]
    assert g["differanse"] == "−5,0 pp (modellen dårligere)"
    assert g["dom"][0].startswith("Innenfor ±30 min: ikke bestått")
    assert g["dom"][1].startswith("Varsel-F1: ikke bestått")


def test_dom_kriteriene_er_uavhengige(tmp_path):
    """±30 min og varsel-F1 avgjøres hver for seg: det ene kan bestå mens det andre ikke gjør det."""
    treff_feil = lag_panel(_fil(tmp_path, {"testkjoringer": 1, "test": syntetisk_blokk(modell_treff=200)}))
    assert treff_feil["horisonter"][0]["grupper"][0]["dom"] == [
        "Innenfor ±30 min: ikke bestått (modell 50,0\u00a0%, baseline 62,5\u00a0%)",
        "Varsel-F1: bestått (modell 0,600, «varsle alle» 0,261)",
    ]
    f1_feil = lag_panel(_fil(tmp_path, {"testkjoringer": 1,
                                        "test": syntetisk_blokk(modell_varsler=100, modell_varseltreff=5)}))
    assert f1_feil["horisonter"][0]["grupper"][0]["dom"] == [
        "Innenfor ±30 min: bestått (modell 75,0\u00a0%, baseline 62,5\u00a0%)",
        "Varsel-F1: ikke bestått (modell 0,062, «varsle alle» 0,261)",
    ]


def test_f1_dom_uten_varsle_alle_kan_ikke_avgjores(tmp_path):
    blokk = syntetisk_blokk()
    blokk["horisonter"]["6"]["ovrige_modellutvalg"]["varsle_alle"]["f1"] = None
    g = lag_panel(_fil(tmp_path, {"testkjoringer": 1, "test": blokk}))["horisonter"][0]["grupper"][0]
    assert g["dom"][1] == "Varsel-F1: kan ikke avgjøres (modell 0,600, «varsle alle» kan ikke varsle)"
    assert g["differanse_f1"] == "kan ikke sammenlignes"


def test_f1_differanse_uten_modell_f1_kan_ikke_sammenlignes(tmp_path):
    """Er modellens F1 ``null`` (og «varsle alle» har en verdi), sier F1-linja «kan ikke sammenlignes». Panelet
    faller ikke til «Tall mangler» (mutasjonssjekken, E2-S09)."""
    blokk = syntetisk_blokk()
    blokk["horisonter"]["6"]["ovrige_modellutvalg"]["modell"]["varsel"]["f1"] = None
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": blokk}))
    assert panel["mangler"] is False
    assert panel["horisonter"][0]["grupper"][0]["differanse_f1"] == "kan ikke sammenlignes"


def test_lik_f1_er_ikke_bestatt(tmp_path):
    """Varsel-F1 består bare når modellen er strengt bedre enn «varsle alle» (FR10). Lik F1 er «ikke bestått»."""
    blokk = syntetisk_blokk()
    utvalg = blokk["horisonter"]["6"]["ovrige_modellutvalg"]
    utvalg["modell"]["varsel"]["f1"] = utvalg["varsle_alle"]["f1"]
    g = lag_panel(_fil(tmp_path, {"testkjoringer": 1, "test": blokk}))["horisonter"][0]["grupper"][0]
    assert g["dom"][1].startswith("Varsel-F1: ikke bestått")
    assert g["differanse_f1"] == "±0,00 (likt)"


def test_differanse_ord_folger_uavrundet_fortegn(tmp_path):
    """Runder differansen til 0,0, står det «<0,1 pp» med riktig ord, aldri «likt» ved siden av «bestått»."""
    blokk = syntetisk_blokk()
    utvalg = blokk["horisonter"]["6"]["ovrige_modellutvalg"]
    utvalg["modell"]["andel_30"] = utvalg["baseline"]["andel_30"] + 0.0004
    utvalg["modell"]["varsel"]["f1"] = utvalg["varsle_alle"]["f1"] - 0.004
    g = lag_panel(_fil(tmp_path, {"testkjoringer": 1, "test": blokk}))["horisonter"][0]["grupper"][0]
    assert g["differanse"] == "<0,1 pp (modellen bedre)"
    assert g["dom"][0].startswith("Innenfor ±30 min: bestått")
    assert g["differanse_f1"] == "<0,01 (modellen dårligere)"
    assert g["dom"][1].startswith("Varsel-F1: ikke bestått")


def test_modellen_taper_paa_f1_mot_varsle_alle(tmp_path):
    g = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk(
        modell_varsler=100, modell_varseltreff=5)}))["horisonter"][0]["grupper"][0]
    assert g["differanse_f1"] == "−0,20 (modellen dårligere)"


@pytest.mark.parametrize("verdi", [float("nan"), float("inf"), float("-inf")])
def test_ikke_endelige_tall_gir_tall_mangler(tmp_path, verdi):
    blokk = syntetisk_blokk()
    blokk["horisonter"]["24"]["ovrige_alle"]["baseline"]["andel_30"] = verdi
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": blokk}))
    assert panel["mangler"] is True
    assert "nan" not in json.dumps(panel).lower() and "inf" not in json.dumps(panel).lower()


def test_likt_er_ikke_bestatt(tmp_path):
    data = {"testkjoringer": 1, "test": syntetisk_blokk(modell_treff=250)}
    g = lag_panel(_fil(tmp_path, data))["horisonter"][0]["grupper"][0]
    assert g["differanse"] == "±0,0 pp (likt)"
    assert g["dom"][0].startswith("Innenfor ±30 min: ikke bestått")


def test_ablasjonen_vises_ikke(tmp_path):
    blokk = syntetisk_blokk()
    for h in blokk["horisonter"].values():
        h["ovrige_modellutvalg"]["ablasjon_uten_f13_f14"] = dict(h["ovrige_modellutvalg"]["modell"], treff_30=123)
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": blokk}))
    assert "123/" not in json.dumps(panel, ensure_ascii=False)
    assert [g["kolonner"] for g in panel["horisonter"][0]["grupper"]][0] == ["Modell", "Baseline", "«Varsle alle»"]


def _uten_nokkel(blokk, *sti):
    d = blokk
    for k in sti[:-1]:
        d = d[k]
    del d[sti[-1]]
    return blokk


@pytest.mark.parametrize("innhold", [
    None,
    "ikke json",
    "[]",
    {"testkjoringer": 0},
    {"testkjoringer": 0, "test_bare_baseline": syntetisk_blokk()},
    {"testkjoringer": 1, "validering": syntetisk_blokk()},
    {"testkjoringer": 0, "validering": _uten_nokkel(syntetisk_blokk(), "horisonter", "24")},
    {"testkjoringer": 0, "validering": _uten_nokkel(syntetisk_blokk(), "horisonter", "6", "ovrige_modellutvalg",
                                                    "modell")},
    {"testkjoringer": 0, "validering": dict(syntetisk_blokk(), antall_anlop="mange")},
], ids=["ingen-fil", "ikke-json", "liste", "ingen-blokk", "bare-test-bare-baseline", "test-mangler",
        "horisont-mangler", "arm-mangler", "feil-type"])
def test_tall_mangler(tmp_path, innhold):
    sti = tmp_path / "metrikker.json"
    if innhold is not None:
        _fil(tmp_path, innhold)
    panel = lag_panel(sti)
    assert panel["mangler"] is True
    assert panel["horisonter"] == [] and panel["antall_anlop"] is None


def test_leser_metrikker_fil_fra_prediksjon(monkeypatch, tmp_path):
    """Panelet bruker ``app.prediksjon.METRIKKER_FIL`` (samme sti som låsen), ikke en egen kopi."""
    import app.prediksjon as prediksjon

    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", _fil(tmp_path, {"testkjoringer": 0,
                                                                     "validering": syntetisk_blokk()}))
    assert lag_panel()["mangler"] is False


def test_all_ovrige_trafikk_er_systemet_ikke_modellen(tmp_path):
    """Raden for all Øvrige-trafikk viser modellen pluss baselinen for resten, så den sier «systemet» (Felipe,
    11.11.2026), og forklarer hvorfor. Modellutvalget sier fortsatt «modellen»."""
    panel = lag_panel(_fil(tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk()}))
    for h in panel["horisonter"]:
        utvalg, alle, passasjer = h["grupper"]
        assert utvalg["kolonner"][0] == "Modell" and utvalg["forklaring"] is None
        assert "modellen" in utvalg["differanse"] and "systemet" not in utvalg["differanse"]
        assert alle["kolonner"][0] == "Systemet"
        assert "systemet" in alle["differanse"] and "modellen" not in alle["differanse"]
        assert "systemet" in alle["differanse_f1"] and "modellen" not in alle["differanse_f1"]
        assert alle["forklaring"].startswith("De fleste forsinkelsene i all trafikk er turer inne i havneområdet")
        assert "Modellutvalget er raden som viser modellen." in alle["forklaring"]
        assert passasjer["forklaring"] is None
