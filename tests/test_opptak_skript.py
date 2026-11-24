"""Opptaksskriptet (E3-S06): ``scripts/ta_opp_begrunnelser.py``.

Ingen test kjører skriptet mot nettet: ``conftest._ai_vakter`` sperrer socketer, og ekte modus testes bare med en falsk
transport og den falske nøkkelen ``sk-or-TEST-IKKE-EKTE``. Modellrader bare fra ``VALIDERING_NAA`` (regelen om
testrader). Planmodus kjører ingen modell, så den kan vise standardvinduet.
"""
import json
import os

import pytest
from conftest import VALIDERING_NAA, FalskTransport, OpptakTransport, last_opptaksskript

import app.begrunnelse as begrunnelse
import app.begrunnelse.testmodus as testmodus
from app import _par
from app.begrunnelse import openrouter_klient
from app.begrunnelse.input import lag_brief_fakta, lag_fakta
from app.begrunnelse.klartekst import brief_innledning, innledning, velg_varslede
from app.begrunnelse.testmodus import MERKE_KI, MERKE_OPPTAK, MERKE_TEST, brief_mal, fakta_hash, mal

FALSK_NOKKEL = "sk-or-TEST-IKKE-EKTE"
skript = last_opptaksskript()


@pytest.fixture
def modell(monkeypatch):
    monkeypatch.setenv("PREDIKTOR", "modell")


def _ekte(monkeypatch, transport):
    monkeypatch.setenv("LLM_MODUS", "ekte")
    monkeypatch.setenv("OPENROUTER_API_KEY", FALSK_NOKKEL)
    monkeypatch.setattr(begrunnelse, "transport", transport)
    return transport


def _transport(par, avvis=()):
    tekster = {innledning(inp, p): mal(inp, p) for inp, p in par}
    valgte, antall = velg_varslede(par)
    if antall:
        tekster[brief_innledning(valgte, antall)] = brief_mal(valgte, antall)
    return OpptakTransport(tekster, avvis)


def test_plan_gjor_ingen_kall(monkeypatch, tmp_path, capsys):
    """Uten --kjor: bare planen, 0 kall, og ingen modell kjøres (heller ikke for standardvinduet)."""
    from app.prediksjon.modell import ModellPrediktor

    def ingen_modell(*a, **k):
        raise AssertionError("planen kjørte modellen")

    monkeypatch.setattr(ModellPrediktor, "prediker", ingen_modell)
    t = _ekte(monkeypatch, FalskTransport("skal ikke brukes"))
    monkeypatch.setenv("PREDIKTOR", "modell")
    assert skript.main(["--fil", str(tmp_path / "opptak.json")]) == 0
    ut = capsys.readouterr().out
    assert "ons 08.10 08:00: 15 anløp" in ut and "Høyst 16 kall i alt" in ut
    assert openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_FIL) in ut
    assert openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_BRIEF_FIL) in ut
    assert t.kall == [] and begrunnelse.antall_kall() == 0
    assert not (tmp_path / "opptak.json").exists()
    assert FALSK_NOKKEL not in ut


def test_plan_advarer_om_utdatert_prompt(tmp_path, capsys):
    sti = tmp_path / "opptak.json"
    sti.write_text(json.dumps({"opptak": [{
        "naa": "2025-10-08T08:00:00+02:00", "anlop": 1, "prediktor": "Modell v1", "prompt_versjon": "gammel-v0",
        "modell": "m", "tatt_opp": "2026-11-24T10:00:00+01:00", "fakta_sha256": "0", "tekst": "x"}]}),
        encoding="utf-8")
    skript.plan(fil=sti)
    ut = capsys.readouterr().out
    assert "Advarsel" in ut and "gammel-v0" in ut and openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_FIL) in ut


@pytest.mark.parametrize("modus, nokkel", [("test", FALSK_NOKKEL), ("ekte", None)])
def test_kjor_krever_ekte_modus_og_nokkel(monkeypatch, tmp_path, capsys, modus, nokkel):
    t = FalskTransport("skal ikke brukes")
    monkeypatch.setattr(begrunnelse, "transport", t)
    monkeypatch.setenv("LLM_MODUS", modus)
    if nokkel:
        monkeypatch.setenv("OPENROUTER_API_KEY", nokkel)
    assert skript.main(["--kjor", "--fil", str(tmp_path / "opptak.json")]) == 2
    feil = capsys.readouterr().err
    assert "Stopp" in feil and FALSK_NOKKEL not in feil
    assert t.kall == [] and not (tmp_path / "opptak.json").exists()


def test_kjor_tar_opp_godkjente_svar(monkeypatch, tmp_path, modell, capsys):
    _, _, par = _par(VALIDERING_NAA)
    avvist_inp, avvist_p = next((inp, p) for inp, p in par if p.forventet_forsinket is False)
    t = _ekte(monkeypatch, _transport(par, avvis={innledning(avvist_inp, avvist_p)}))
    sti = tmp_path / "opptak.json"
    monkeypatch.setenv("LLM_MAKS_KALL", "3")  # skriptet hever grensen bare for seg selv
    oppsummering = skript.kjor([VALIDERING_NAA], sti)
    assert os.environ["LLM_MAKS_KALL"] == "3"

    assert len(t.kall) == len(par) + 1 == oppsummering["kall"]
    assert oppsummering["avvist"] == [{"hva": f"{avvist_inp.shipname} ({avvist_inp.voyageid})",
                                       "kode": "kontroll_konklusjon"}]
    assert oppsummering["tatt_opp"] == len(par) and oppsummering["b1"] == []

    tekst = sti.read_text(encoding="utf-8")
    assert FALSK_NOKKEL not in tekst and "Authorization" not in tekst
    data = json.loads(tekst)
    oppforinger = {o["anlop"]: o for o in data["opptak"]}
    assert set(oppforinger) == {inp.voyageid for inp, _ in par if inp.voyageid != avvist_inp.voyageid} | {"brief"}
    for inp, p in par:
        if inp.voyageid == avvist_inp.voyageid:
            continue
        o = oppforinger[inp.voyageid]
        assert o["tekst"] == mal(inp, p) and o["fakta_sha256"] == fakta_hash(lag_fakta(inp, p))
        assert o["naa"] == VALIDERING_NAA.isoformat() and o["prediktor"] == "Modell v1"
        assert o["prompt_versjon"] == openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_FIL) and o["modell"] == "deepseek/deepseek-v4.1-flash-1017:floor"
    valgte, antall = velg_varslede(par)
    assert oppforinger["brief"]["fakta_sha256"] == fakta_hash(lag_brief_fakta(par, VALIDERING_NAA, valgte, antall))
    assert oppforinger["brief"]["prompt_versjon"] == openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_BRIEF_FIL)
    ut = capsys.readouterr().out
    assert "Utelatt" in ut and "kontroll_konklusjon" in ut and FALSK_NOKKEL not in ut

    # Fila virker i testmodus: opptaket for de godkjente, malen for det avviste.
    monkeypatch.setenv("LLM_MODUS", "test")
    monkeypatch.setattr(testmodus, "OPPTAK_FIL", sti)
    begrunnelse.nullstill()
    for inp, p in par:
        svar = begrunnelse.hent_begrunnelse(inp, p, "Modell v1", naa=VALIDERING_NAA)
        assert svar.merke == (MERKE_TEST if inp.voyageid == avvist_inp.voyageid else MERKE_OPPTAK)
    assert begrunnelse.hent_brief(par, VALIDERING_NAA, "Modell v1").merke == MERKE_OPPTAK


def test_bare_ki_generert_tas_opp(monkeypatch, tmp_path, modell):
    """Alle kall feiler (HTTP 500): ingen oppføringer, og alle står i oppsummeringen."""
    _, _, par = _par(VALIDERING_NAA)
    _ekte(monkeypatch, FalskTransport(500))
    sti = tmp_path / "opptak.json"
    oppsummering = skript.kjor([VALIDERING_NAA], sti)
    assert json.loads(sti.read_text(encoding="utf-8"))["opptak"] == []
    assert oppsummering["tatt_opp"] == 0
    assert len(oppsummering["avvist"]) == len(par) + 1
    assert {a["kode"] for a in oppsummering["avvist"]} == {"http_500"}


def test_kjor_uten_varsler_tar_ikke_opp_briefen(monkeypatch, tmp_path):
    """B1: med baselinen skriver appen briefen selv. Ingen kall for den, og den tas ikke opp."""
    monkeypatch.setenv("PREDIKTOR", "baseline")
    _, _, par = _par(VALIDERING_NAA)
    t = _ekte(monkeypatch, _transport(par))
    oppsummering = skript.kjor([VALIDERING_NAA], tmp_path / "opptak.json")
    assert len(t.kall) == len(par) and oppsummering["b1"] == [VALIDERING_NAA.isoformat()]
    oppforinger = json.loads((tmp_path / "opptak.json").read_text(encoding="utf-8"))["opptak"]
    assert "brief" not in {o["anlop"] for o in oppforinger}
    assert {o["prediktor"] for o in oppforinger} == {"Kalibrert baseline"}


def test_kjor_beholder_andre_vinduer(monkeypatch, tmp_path, modell):
    sti = tmp_path / "opptak.json"
    annen = {"naa": "2025-09-17T08:00:00+02:00", "anlop": 7, "prediktor": "Modell v1", "prompt_versjon": "x",
             "modell": "m", "tatt_opp": "2026-11-24T10:00:00+01:00", "fakta_sha256": "0", "tekst": "x"}
    _, _, par = _par(VALIDERING_NAA)
    erstattes = dict(annen, naa=VALIDERING_NAA.isoformat(), anlop=par[0][0].voyageid)
    uten_nytt = dict(annen, naa=VALIDERING_NAA.isoformat(), anlop=8)
    ugyldige = [3, "x", {"naa": 5, "anlop": 1}, {"anlop": 2}]
    sti.write_text(json.dumps({"format": 1, "opptak": [annen, erstattes, uten_nytt, *ugyldige]}), encoding="utf-8")
    _ekte(monkeypatch, _transport(par))
    skript.kjor([VALIDERING_NAA], sti)
    oppforinger = json.loads(sti.read_text(encoding="utf-8"))["opptak"]
    assert annen in oppforinger and uten_nytt in oppforinger and erstattes not in oppforinger
    assert len(oppforinger) == len(par) + 1 + 2  # nye (begrunnelser + brief) + to beholdt, ugyldige droppet
    assert [p.name for p in tmp_path.iterdir()] == ["opptak.json"]  # ingen midlertidig fil igjen


def test_feilet_ny_kjoring_beholder_gamle_opptak(monkeypatch, tmp_path, modell):
    """En ny kjøring der kallene feiler (402), sletter ikke de gode opptakene for vinduet."""
    sti = tmp_path / "ny" / "opptak.json"  # mappa lages
    _, _, par = _par(VALIDERING_NAA)
    _ekte(monkeypatch, _transport(par))
    skript.kjor([VALIDERING_NAA], sti)
    for_ = json.loads(sti.read_text(encoding="utf-8"))["opptak"]
    begrunnelse.nullstill()
    _ekte(monkeypatch, FalskTransport(402))
    oppsummering = skript.kjor([VALIDERING_NAA], sti)
    assert oppsummering["tatt_opp"] == 0 and {a["kode"] for a in oppsummering["avvist"]} == {"kvote_402"}
    assert json.loads(sti.read_text(encoding="utf-8"))["opptak"] == for_


def test_standardfila_slaas_opp_ved_kallet(monkeypatch, tmp_path, modell):
    """Uten ``fil`` brukes ``testmodus.OPPTAK_FIL`` slik den er ved kallet (conftest peker den bort fra data/)."""
    sti = tmp_path / "standard.json"
    monkeypatch.setattr(testmodus, "OPPTAK_FIL", sti)
    _, _, par = _par(VALIDERING_NAA)
    _ekte(monkeypatch, _transport(par))
    skript.kjor([VALIDERING_NAA])
    assert len(json.loads(sti.read_text(encoding="utf-8"))["opptak"]) == len(par) + 1


def test_prompt_versjon_i_skriptet_er_den_samme_som_appen_sjekker():
    assert skript._versjoner() == {"begrunnelse": openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_FIL),
                                   "brief": openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_BRIEF_FIL)}
    assert MERKE_KI == "KI-GENERERT"
