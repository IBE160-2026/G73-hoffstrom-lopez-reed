"""AI-laget: begrunnelse per anløp (E3-S01–S04, spec-e3-s01-s04-begrunnelse-via-openrouter).

Ingen test gjør et ekte kall: ``conftest._ai_vakter`` fjerner nøkkelen, setter testmodus og sperrer socketer.
Ekte modus testes bare med en falsk transport og den falske nøkkelen ``sk-or-TEST-IKKE-EKTE``.
Baselinerader tas fra standardvinduet. Modellrader bare fra ``VALIDERING_NAA`` (regelen om testrader).
"""
import logging
import urllib.request

import pytest
from conftest import NettSperret

import app.begrunnelse as begrunnelse
from app import STANDARD_NAA
from app.begrunnelse import Begrunnelse, cachet, hent_begrunnelse, konfig
from app.begrunnelse.testmodus import MERKE_FEILET, MERKE_TEST
from app.data import anlop_i_vindu
from app.prediksjon import lag_input
from app.prediksjon.baseline import BaselinePrediktor

FALSK_NOKKEL = "sk-or-TEST-IKKE-EKTE"
BASELINE = "Kalibrert baseline"


def baselinepar(naa=STANDARD_NAA, indeks=0):
    """(input, prediksjon, anløp) for et anløp i vinduet, med baselinen."""
    anlop = anlop_i_vindu(naa)[indeks]
    inp = lag_input(anlop, naa)
    return inp, BaselinePrediktor().prediker([inp], naa)[0], anlop


def ekte(monkeypatch, nokkel=FALSK_NOKKEL):
    monkeypatch.setenv("LLM_MODUS", "ekte")
    if nokkel:
        monkeypatch.setenv("OPENROUTER_API_KEY", nokkel)


# --- E3-S01: adapter og testmodus ------------------------------------------------------------------------------

def test_nett_er_sperret_i_testene():
    with pytest.raises(NettSperret):
        urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=1)


def test_testmodus_uten_nett():
    inp, p, _ = baselinepar()
    svar = hent_begrunnelse(inp, p, BASELINE)
    assert isinstance(svar, Begrunnelse)
    assert svar.merke == MERKE_TEST
    assert inp.shipname in svar.tekst
    assert begrunnelse.antall_kall() == 0
    # Deterministisk, og siden kan vise den uten å vente.
    assert hent_begrunnelse(inp, p, BASELINE) == svar == cachet(inp, p, BASELINE)


def test_testmodus_er_standard(monkeypatch):
    monkeypatch.delenv("LLM_MODUS")
    assert konfig.modus() == "test"
    monkeypatch.setenv("LLM_MODUS", "noe-annet")
    assert konfig.modus() == "test"
    monkeypatch.setenv("LLM_MODUS", " EKTE ")
    assert konfig.modus() == "ekte"


def test_konfig_standardverdier():
    assert konfig.modellstreng() == "deepseek/deepseek-v4.1-flash-1017:floor"
    assert konfig.maks_kall() == 20
    assert konfig.feil_ttl_s() == 300
    assert konfig.timeout_s() == 8
    assert konfig.api_nokkel() is None


def test_konfig_fra_miljoet(monkeypatch):
    monkeypatch.setenv("LLM_MODELL", "leverandor/modell")
    monkeypatch.setenv("LLM_ROUTING", "nitro")
    assert konfig.modellstreng() == "leverandor/modell:nitro"
    monkeypatch.setenv("LLM_ROUTING", "")
    assert konfig.modellstreng() == "leverandor/modell"
    monkeypatch.setenv("LLM_MAKS_KALL", "tull")
    assert konfig.maks_kall() == 20
    monkeypatch.setenv("LLM_MAKS_KALL", "3")
    assert konfig.maks_kall() == 3
    monkeypatch.setenv("LLM_FEIL_TTL_S", "-1")
    assert konfig.feil_ttl_s() == 300


def test_mangler_nokkel_gir_ingen_kall(monkeypatch, caplog):
    ekte(monkeypatch, nokkel=None)

    def transport(*a, **k):
        raise AssertionError("ingen nøkkel skal gi ingen kall")

    monkeypatch.setattr(begrunnelse, "transport", transport)
    inp, p, _ = baselinepar()
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar.merke == MERKE_FEILET
    assert svar.tekst == begrunnelse.testtekst(inp, p).tekst
    assert begrunnelse.antall_kall() == 0
    assert "mangler_nokkel" in caplog.text and str(inp.voyageid) in caplog.text
    assert cachet(inp, p, BASELINE) is None  # ikke cachet: nøkkelen kan komme med en ny prosess


def test_adapteren_tar_ikke_anlop():
    inp, p, anlop = baselinepar()
    with pytest.raises(TypeError):
        hent_begrunnelse(anlop, p, BASELINE)
    with pytest.raises(TypeError):
        cachet(anlop, p, BASELINE)
