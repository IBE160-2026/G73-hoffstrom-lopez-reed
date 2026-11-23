"""AI-laget: begrunnelse per anløp (E3-S01–S04, spec-e3-s01-s04-begrunnelse-via-openrouter).

Ingen test gjør et ekte kall: ``conftest._ai_vakter`` fjerner nøkkelen, setter testmodus og sperrer socketer.
Ekte modus testes bare med en falsk transport og den falske nøkkelen ``sk-or-TEST-IKKE-EKTE``.
Baselinerader tas fra standardvinduet. Modellrader bare fra ``VALIDERING_NAA`` (regelen om testrader).
"""
import json
import logging
import urllib.request

import pytest
from conftest import FalskTransport, NettSperret

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
    from app.begrunnelse.klartekst import innledning
    assert svar.tekst.startswith(innledning(inp, p))
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
    monkeypatch.setenv("LLM_MAKS_KALL", "inf")
    assert konfig.maks_kall() == 20
    monkeypatch.setenv("LLM_MAKS_KALL", "nan")
    assert konfig.maks_kall() == 20
    monkeypatch.setenv("LLM_FEIL_TTL_S", "-1")
    assert konfig.feil_ttl_s() == 300
    monkeypatch.setenv("LLM_FEIL_TTL_S", "inf")
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


# --- E3-S02: input bygd fra modellens faktiske data -------------------------------------------------------------

FASITFELT = ("faktisk_ankomst", "status_in_area", "split")


def modellpar(monkeypatch, varsel=None):
    """(input, prediksjon) fra ``ModellPrediktor`` i valideringsvinduet. ``varsel`` = True/False velger en rad med
    eller uten varsel, None en delegert rad."""
    from conftest import VALIDERING_NAA

    from app.prediksjon import MODELL_DIR
    from app.prediksjon.modell import ModellPrediktor

    inputs = [lag_input(a, VALIDERING_NAA) for a in anlop_i_vindu(VALIDERING_NAA)]
    par = list(zip(inputs, ModellPrediktor(MODELL_DIR).prediker(inputs, VALIDERING_NAA)))
    for inp, p in par:
        if p.forventet_forsinket is varsel:
            return inp, p
    raise AssertionError(f"ingen rad med forventet_forsinket={varsel!r} i valideringsvinduet")


def test_input_uten_fasit(monkeypatch):
    from app.begrunnelse.input import lag_fakta

    for inp, p in [baselinepar()[:2], modellpar(monkeypatch, True), modellpar(monkeypatch, None)]:
        fakta = lag_fakta(inp, p)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in fakta.items())
        tekst = "\n".join(f"{k}: {v}" for k, v in fakta.items())
        assert str(inp.mmsino) not in tekst
        assert str(inp.voyageid) not in tekst
        for felt in FASITFELT:
            assert felt not in tekst.lower()
    # Fasiten for anløpet finnes i datalaget, men når aldri inputen.
    inp, p, anlop = baselinepar()
    assert anlop.faktisk_ankomst is not None
    from app.visning import ukedag_dato_klokke
    assert ukedag_dato_klokke(anlop.faktisk_ankomst) not in "\n".join(lag_fakta(inp, p).values())
    with pytest.raises(TypeError):
        lag_fakta(anlop, p)


def test_input_baseline_har_tider_som_paa_skjermen():
    from app.begrunnelse.input import lag_fakta
    from app.visning import ukedag_dato_klokke

    inp, p, _ = baselinepar()
    from app.begrunnelse.klartekst import innledning

    fakta = lag_fakta(inp, p)
    assert list(fakta)[0] == "Innledning (skriv ordrett først)"
    assert fakta["Innledning (skriv ordrett først)"] == innledning(inp, p)
    assert fakta["Skip"] == inp.shipname
    assert fakta["Rapportert ETA"] == ukedag_dato_klokke(inp.eta_reported)
    assert fakta["Ventet ankomst"] == ukedag_dato_klokke(p.predikert_ankomst)
    assert fakta["Metode"] == "vanlig avvik for denne skipsgruppen"
    assert fakta["Varsel"] == "ingen (beregningen bygger bare på vanlig avvik for skipsgruppen og kan ikke varsle)"
    assert fakta["Vanlig avvik for skipsgruppen"] == "45 min før rapportert ETA"  # Passasjer, offset 44,75


def test_input_modell_har_avvik_og_featurer(monkeypatch):
    from app.begrunnelse.input import lag_fakta

    inp, p = modellpar(monkeypatch, True)
    fakta = lag_fakta(inp, p)
    assert fakta["Metode"] == "modellvurdering av skipets posisjon, fart og tidligere anløp"
    assert fakta["Varsel"].startswith("ja, over varselgrensen")
    assert fakta["Modellens vurdering"] == (
        f"{abs(p.forklaring['predikert_avvik_min']):.0f} min senere enn vanlig for skipsgruppen")
    assert fakta["Vanlig avvik for skipsgruppen"] == "64 min før rapportert ETA"
    assert fakta["Avstand til havna"].endswith(" km")
    inp, p = modellpar(monkeypatch, None)
    fakta = lag_fakta(inp, p)
    assert "Hvorfor modellen ikke vurderer anløpet" in fakta
    assert fakta["Varsel"].startswith("ingen")


# --- E3-S03: ekte klient (bare med falsk transport), prompt og kontroll -----------------------------------------

import urllib.error  # noqa: E402

from app.begrunnelse import openrouter_klient  # noqa: E402
from app.begrunnelse.kontroll import antall_setninger, kontroller  # noqa: E402
from app.begrunnelse.testmodus import MERKE_GRENSE, MERKE_KI  # noqa: E402


def godt_svar(inp, p):
    """Et svar som består kontrollen: innledningen først, så én setning uten nye tall, navn eller forbudte ord."""
    from app.begrunnelse.klartekst import innledning

    return f"{innledning(inp, p)} Beregningen kan ikke varsle avvik."


def sett_transport(monkeypatch, transport):
    monkeypatch.setattr(begrunnelse, "transport", transport)
    return transport


def test_ekte_med_mock(monkeypatch):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(godt_svar(inp, p)))
    svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar == Begrunnelse(godt_svar(inp, p), MERKE_KI)
    assert len(t.kall) == 1 and begrunnelse.antall_kall() == 1
    k = t.kall[0]
    assert k["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert k["headers"]["Authorization"] == f"Bearer {FALSK_NOKKEL}"
    assert k["body"]["model"] == "deepseek/deepseek-v4.1-flash-1017:floor"
    assert k["body"]["max_tokens"] == 300
    assert k["timeout"] == 8
    system, bruker = k["body"]["messages"][0]["content"], k["body"]["messages"][1]["content"]
    assert "Ikke finn på årsaker" in system
    assert f"- Skip: {inp.shipname}" in bruker
    assert str(inp.mmsino) not in json.dumps(k["body"])


def test_prompt_er_versjonert():
    tekst = openrouter_klient.PROMPT_FIL.read_text(encoding="utf-8")
    assert "begrunnelse-v8" in tekst
    assert "utenom slik de står i innledningen eller faktaene" in tekst
    system, bruker = openrouter_klient.bygg_prompt({"Skip": "X"})
    assert "<!--" not in system + bruker and "{fakta}" not in bruker
    assert "- Skip: X" in bruker


@pytest.mark.parametrize("feil, kode", [
    (TimeoutError("timed out"), "timeout"),
    (urllib.error.URLError(TimeoutError("timed out")), "timeout"),
    (urllib.error.URLError("Name or service not known"), "nett"),
    (ConnectionResetError(), "nett"),
    (500, "http_500"),
    (503, "http_503"),
    (429, "http_429"),
    (401, "http_401"),
    (402, "kvote_402"),
    (b"ikke json", "svar_format"),
    (b'{"choices": []}', "svar_format"),
    (b'{"error": {"code": 400, "message": "x"}}', "svar_format"),
])
def test_fallback_ved_feil(monkeypatch, caplog, feil, kode):
    ekte(monkeypatch)
    sett_transport(monkeypatch, FalskTransport(feil))
    inp, p, _ = baselinepar()
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar.merke == MERKE_FEILET
    assert svar.tekst == begrunnelse.testtekst(inp, p).tekst
    assert f"begrunnelse: {kode} voyageid={inp.voyageid} prediktor={BASELINE}" in caplog.text
    assert FALSK_NOKKEL not in caplog.text


def test_avkortet_svar_avvises(monkeypatch, caplog):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    sett_transport(monkeypatch, FalskTransport(godt_svar(inp, p), finish_reason="length"))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_FEILET
    assert "avkortet" in caplog.text


def test_uventet_feil_gir_testmodus(monkeypatch, caplog):
    ekte(monkeypatch)
    sett_transport(monkeypatch, FalskTransport(RuntimeError(f"hemmelig {FALSK_NOKKEL}")))
    inp, p, _ = baselinepar()
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_FEILET
    assert "uventet_RuntimeError" in caplog.text and FALSK_NOKKEL not in caplog.text


def test_urllib_transport_mapper_feil(monkeypatch):
    """Standardtransporten med en sperret urlopen: HTTP-feil gir statuskoden, nettfeil gir ``nett``."""
    def http_feil(req, timeout):
        assert req.get_header("Authorization") == f"Bearer {FALSK_NOKKEL}"
        raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", http_feil)
    with pytest.raises(openrouter_klient.KlientFeil) as e:
        openrouter_klient.kall("s", "b", modell="m", nokkel=FALSK_NOKKEL, timeout=1)
    assert e.value.kode == "kvote_402" and FALSK_NOKKEL not in str(e.value) and e.value.__cause__ is None

    def nettfeil(req, timeout):
        raise urllib.error.URLError("ingen rute")

    monkeypatch.setattr(urllib.request, "urlopen", nettfeil)
    with pytest.raises(openrouter_klient.KlientFeil) as e:
        openrouter_klient.kall("s", "b", modell="m", nokkel=FALSK_NOKKEL, timeout=1)
    assert e.value.kode == "nett" and FALSK_NOKKEL not in repr(e.value)


def test_nokkelen_lekker_ikke(monkeypatch, caplog):
    """Den falske nøkkelen står aldri i logg, svar eller unntakstekst, uansett utfall."""
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    tekster = []
    with caplog.at_level(logging.DEBUG):
        for i, utfall in enumerate([godt_svar(inp, p), 401, 402, TimeoutError("timed out"), "tull 99999."]):
            sett_transport(monkeypatch, FalskTransport(utfall))
            svar = hent_begrunnelse(inp, p, f"P{i}")
            tekster.append(json.dumps(svar.som_dict()))
            try:
                openrouter_klient.kall("s", "b", modell="m", nokkel=FALSK_NOKKEL, timeout=1,
                                       transport=FalskTransport(utfall))
            except openrouter_klient.KlientFeil as feil:
                tekster += [str(feil), repr(feil), str(feil.__cause__ or ""), str(feil.__context__ or "")]
    assert FALSK_NOKKEL not in caplog.text
    assert all(FALSK_NOKKEL not in t for t in tekster)


# Cache og kallgrense (FR11b slik den er endret, spec-valg S5–S6) ------------------------------------------------

class Klokke:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_cache_gir_null_nye_kall(monkeypatch):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(godt_svar(inp, p)))
    klokke = Klokke()
    monkeypatch.setattr(begrunnelse, "klokke", klokke)
    forste = hent_begrunnelse(inp, p, BASELINE)
    klokke.t += 10 ** 9  # et godkjent svar utløper aldri
    assert hent_begrunnelse(inp, p, BASELINE) == forste == cachet(inp, p, BASELINE)
    assert len(t.kall) == 1
    # Ny prediktor er en ny nøkkel.
    hent_begrunnelse(inp, p, "Modell v1")
    assert len(t.kall) == 2


@pytest.mark.parametrize("utfall", [500, "tull 99999.", TimeoutError()])
def test_feil_caches_i_300_s(monkeypatch, utfall):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(utfall))
    klokke = Klokke(1000.0)
    monkeypatch.setattr(begrunnelse, "klokke", klokke)
    assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_FEILET
    klokke.t = 1299.0
    assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_FEILET
    assert cachet(inp, p, BASELINE).merke == MERKE_FEILET
    assert len(t.kall) == 1
    klokke.t = 1300.0
    assert cachet(inp, p, BASELINE) is None
    t.svar = godt_svar(inp, p)
    assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_KI
    assert len(t.kall) == 2 and begrunnelse.antall_kall() == 2


def test_feil_ttl_fra_miljoet(monkeypatch):
    ekte(monkeypatch)
    monkeypatch.setenv("LLM_FEIL_TTL_S", "5")
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(500))
    klokke = Klokke(0.0)
    monkeypatch.setattr(begrunnelse, "klokke", klokke)
    hent_begrunnelse(inp, p, BASELINE)
    klokke.t = 4.9
    hent_begrunnelse(inp, p, BASELINE)
    klokke.t = 5.0
    hent_begrunnelse(inp, p, BASELINE)
    assert len(t.kall) == 2


def test_kallgrense_20(monkeypatch, caplog):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(godt_svar(inp, p)))
    for i in range(20):
        assert hent_begrunnelse(inp, p, f"P{i}").merke == MERKE_KI
    assert len(t.kall) == 20
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, "P20")
    assert svar == Begrunnelse(begrunnelse.testtekst(inp, p).tekst, MERKE_GRENSE)
    assert len(t.kall) == 20 and begrunnelse.antall_kall() == 20
    assert "kallgrense" in caplog.text
    # Cachede svar vises fortsatt over grensen.
    assert hent_begrunnelse(inp, p, "P0").merke == MERKE_KI


def test_feil_teller_mot_grensen(monkeypatch):
    ekte(monkeypatch)
    monkeypatch.setenv("LLM_MAKS_KALL", "2")
    inp, p, _ = baselinepar()
    t = sett_transport(monkeypatch, FalskTransport(500))
    klokke = Klokke(0.0)
    monkeypatch.setattr(begrunnelse, "klokke", klokke)
    hent_begrunnelse(inp, p, BASELINE)
    klokke.t = 300.0
    hent_begrunnelse(inp, p, BASELINE)
    klokke.t = 600.0
    t.svar = godt_svar(inp, p)
    assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_GRENSE
    assert len(t.kall) == 2


# Kontrollen ---------------------------------------------------------------------------------------------------

FAKTA = {"Skip": "BERGEN ENERGY", "Rapportert ETA (norsk tid)": "ons 08.10 11:00", "Horisont": "≤ 6 t",
         "Predikert avvik fra kalibrert baseline (min)": "152", "Avgangshavn": "ÅGOTNES"}
NAVN = ["BERGEN ENERGY", "BERGEN TANK", "SIEM PEARL", "PEARL", "ÅGOTNES"]


def k(tekst, varsel=True, fakta=FAKTA):
    return kontroller(tekst, fakta, forventet_forsinket=varsel, skipsnavn=NAVN)


def test_kontroll_godtar_et_godt_svar():
    assert k("BERGEN ENERGY har ETA ons 08.10 11:00. Modellen venter 152 min forsinkelse fra ÅGOTNES.") is None


@pytest.mark.parametrize("tekst", ["", "   \n ", None])
def test_kontroll_tom(tekst):
    assert k(tekst) == "tom"


def test_kontroll_lengde_400_mot_401():
    assert k("a" * 399 + ".") is None
    assert k("a" * 400 + ".") == "lengde"
    assert k("  " + "a" * 399 + ".  ") is None  # blanktegn rundt telles ikke


def test_kontroll_setninger_3_mot_4():
    assert k("Alfa. Beta. Gamma.") is None
    assert k("Alfa. Beta. Gamma. Delta.") == "setninger"
    assert k("Alfa! Beta? Gamma … Delta") == "setninger"
    assert antall_setninger("Uten punktum") == 1
    assert antall_setninger("Avvik på 64,2 min. Neste.") == 2


def test_tall_finnes_i_input():
    assert k("Avviket er 152 min.") is None
    assert k("Avviket er 153 min.") == "tall"
    assert k("ETA er 11:00 og 11:01.") == "tall"
    assert k("ETA er kl 11.00.") is None  # «11.00» blir 11 når nullene i desimalene tas bort, og 11 står i inputen
    assert k("ETA er kl 11.30.") == "tall"
    assert k("Horisonten er 6 t.") is None
    assert k("Avviket er 152,5 min.") == "tall"


def test_tall_med_fortegn_maa_ha_samme_fortegn():
    fakta = {"Avvik (min)": "\u221212", "Horisont": "≤ 6 t", "Modell": "Modell v1"}
    assert kontroller("Avviket er \u221212 min.", fakta, forventet_forsinket=True, skipsnavn=[]) is None
    assert kontroller("Avviket er -12 min.", fakta, forventet_forsinket=True, skipsnavn=[]) is None
    assert kontroller("Avviket er 12 min.", fakta, forventet_forsinket=True, skipsnavn=[]) is None  # uten fortegn
    assert kontroller("Avviket er +12 min.", fakta, forventet_forsinket=True, skipsnavn=[]) == "tall"
    # Et tall uten fortegn i inputen regnes som positivt.
    assert k("Avviket er +152 min.") is None
    assert k("Avviket er \u2212152 min.") == "tall"
    # Bindestrek og tankestrek mellom tall er ikke fortegn.
    assert kontroller("Modell v1 og 6–24 t.", {"a": "Modell v1", "b": "6–24 t"}, forventet_forsinket=True,
                      skipsnavn=[]) is None


def test_tillatte_tall_bare_fra_verdiene():
    fakta = {"Kurs mot havna (1 = rett mot, \u22121 = rett bort)": "0,87"}
    assert kontroller("Kursen er 0,87.", fakta, forventet_forsinket=True, skipsnavn=[]) is None
    assert kontroller("Kursen er 1.", fakta, forventet_forsinket=True, skipsnavn=[]) == "tall"
    assert kontroller("Kursen er \u22121.", fakta, forventet_forsinket=True, skipsnavn=[]) == "tall"


def test_desimaler_uten_etterfolgende_nuller():
    fakta = {"Avvik (min)": "64,2", "Fart (knop)": "9"}
    assert kontroller("Avvik 64,20 min og fart 9,0 knop.", fakta, forventet_forsinket=True, skipsnavn=[]) is None
    assert kontroller("Avvik 64,21 min.", fakta, forventet_forsinket=True, skipsnavn=[]) == "tall"


def test_kontroll_andre_skipsnavn():
    assert k("BERGEN TANK kommer også.") == "skipsnavn"
    assert k("Bergen Tank kommer også.") == "skipsnavn"
    assert k("SIEM PEARL er nær.") == "skipsnavn"
    assert k("Skipet kom fra Ågotnes.") is None  # står i inputen
    assert k("Bergen Energy er nær.") is None
    fakta = dict(FAKTA, Skip="SIEM PEARL")
    assert kontroller("SIEM PEARL er nær.", fakta, forventet_forsinket=True, skipsnavn=NAVN) is None


def test_kontroll_standard_skipsnavn_fra_utdraget():
    inp, p, _ = baselinepar()
    fakta = {"Skip": inp.shipname}
    annen = next(a.shipname for a in anlop_i_vindu(STANDARD_NAA) if a.shipname != inp.shipname)
    assert kontroller(f"{inp.shipname} er nær.", fakta, forventet_forsinket=None) is None
    assert kontroller(f"{annen} er nær.", fakta, forventet_forsinket=None) == "skipsnavn"


@pytest.mark.parametrize("tekst", ["Været er dårlig.", "Det er streik i havna.", "Motoren har feil.",
                                   "Mannskapet er sent ute.", "Kraftig vind.", "Tett tåke ved innseilingen.",
                                   "Engine trouble."])
def test_kontroll_aarsaksord(tekst):
    assert k(tekst) == "aarsak"


@pytest.mark.parametrize("tekst", ["Vinduet er 24 timer.", "Skipet går mot havna.", "Det er vist i lista."])
def test_kontroll_aarsaksord_ingen_falske_treff(tekst):
    assert kontroller(tekst, {"x": "24"}, forventet_forsinket=True, skipsnavn=[]) is None


def test_kontroll_forsink_bare_med_varsel():
    assert k("Anløpet blir forsinket.", varsel=True) is None
    assert k("Anløpet blir forsinket.", varsel=False) == "forsink"
    assert k("Ingen forsinkelse ventet.", varsel=None) == "forsink"


def test_mal_teksten_bestaar_kontrollen(monkeypatch):
    """Testmodus-malen holder de samme grensene som et ekte svar, også uten varsel (ingen «forsink»)."""
    from app.begrunnelse.input import lag_fakta

    from app.begrunnelse.klartekst import er_modellvurdert, innledning
    from app.begrunnelse.kontroll import retning

    typer = set()
    for inp, p in alle_rader():
        typer.add("modell_varsel" if p.forventet_forsinket else "modell" if p.forventet_forsinket is False
                  else p.forklaring.get("delegert") or "baseline")
        tekst = begrunnelse.testtekst(inp, p).tekst
        assert tekst.startswith(innledning(inp, p))
        assert antall_setninger(tekst) <= 3, tekst
        assert kontroller(tekst, lag_fakta(inp, p), forventet_forsinket=p.forventet_forsinket, retning=retning(p),
                          konklusjon=innledning(inp, p), modellrad=er_modellvurdert(p)) is None, tekst
    assert {"modell_varsel", "modell", "baseline", "passasjer"} <= typer


def test_mislykket_kontroll_logges(monkeypatch, caplog):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    from app.begrunnelse.klartekst import innledning
    sett_transport(monkeypatch, FalskTransport(f"{innledning(inp, p)} Været gjør at skipet kommer sent."))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_FEILET
    assert "kontroll_aarsak" in caplog.text


def test_tall_viser_aldri_minus_null():
    from app.visning import tall

    assert tall(-0.4, 0) == "0"
    assert tall(-0.04, 1) == "0,0"
    assert tall(-12.4, 0) == "\u221212"
    assert tall(64.25, 1) in ("64,2", "64,3")
    assert tall(152.0, 0) == "152"


def test_modell_id_bare_i_konfig():
    """Modell-ID-en står bare i ``konfig.py`` (beslutning 13), og URL-en bare i klienten."""
    from pathlib import Path

    rot = Path(__file__).resolve().parent.parent / "app"
    for fil in rot.rglob("*"):
        if fil.suffix not in {".py", ".md", ".html", ".js", ".css"}:
            continue
        tekst = fil.read_text(encoding="utf-8")
        if fil.name != "konfig.py":
            assert "deepseek" not in tekst, fil
        if fil.name != "openrouter_klient.py":
            assert "openrouter.ai" not in tekst, fil


# ---------- Etter røykkallet 18.11.2026: tall med ord, retningsord, resonnering og overskrift ----------

@pytest.mark.parametrize("tekst", ["Skipet er to timer bak.", "Avviket er en halvtime.", "Det er dobbelt så lenge.",
                                   "Tre av fire anløp.", "Hundre minutter.", "Two hours late."])
def test_kontroll_tall_skrevet_med_ord(tekst):
    assert kontroller(tekst, {"a": "x"}, forventet_forsinket=True, skipsnavn=[]) == "tallord"


@pytest.mark.parametrize("tekst", ["Prediksjonen bygger på farten.", "Torsdag kom skipet.", "Tonnasjen er stor.",
                                   "Fartøyet har en lang historikk."])
def test_kontroll_tallord_ingen_falske_treff(tekst):
    assert kontroller(tekst, {"a": "x"}, forventet_forsinket=True, skipsnavn=[]) is None


@pytest.mark.parametrize("tekst, retning, regel", [
    ("Skipet kommer senere enn rapportert ETA.", 1, None),
    ("Skipet kommer tidligere enn rapportert ETA.", 1, "retning"),
    ("Skipet kommer før tiden.", 1, "retning"),
    ("Skipet kommer tidligere enn rapportert ETA.", -1, None),
    ("Skipet kommer senere enn rapportert ETA.", -1, "retning"),
    ("Skipet er etter planen.", -1, "retning"),
    ("Skipet kommer senere.", 0, "retning"),
    ("Skipet kommer tidligere.", 0, "retning"),
    ("Det kommer i rute.", 0, None),
    ("Skipet kommer senere.", None, None),  # ukjent retning: regelen hoppes over
    ("Fartøyet har 50 tidligere anløp.", 1, None),  # «tidligere anløp» er ikke en retning
])
def test_kontroll_retningsord_mot_fortegnet(tekst, retning, regel):
    fakta = {"a": "50"}
    assert kontroller(tekst, fakta, forventet_forsinket=True, skipsnavn=[], retning=retning) == regel


def test_retning_fra_prediksjonen(monkeypatch):
    from app.begrunnelse.kontroll import retning

    inp, p, _ = baselinepar()
    assert retning(p) == -1  # baselinen: rapportert ETA minus offset, alltid tidligere
    _, med_varsel = modellpar(monkeypatch, True)
    assert retning(med_varsel) == 1
    _, delegert = modellpar(monkeypatch, None)
    assert retning(delegert) == -1


def test_adapteren_avviser_feil_retning(monkeypatch, caplog):
    from app.begrunnelse.klartekst import innledning

    ekte(monkeypatch)
    inp, p, _ = baselinepar()  # baselinen i standardvinduet: før rapportert ETA
    sett_transport(monkeypatch, FalskTransport(f"{innledning(inp, p)} Skipet kommer likevel senere enn vanlig."))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar.merke != MERKE_KI
    assert "kontroll_retning" in caplog.text


def test_resonnering_er_av_som_standard(monkeypatch):
    """Røykkallet 18.11.2026: med modellens standard gikk alle 300 tokens til resonnering, og svaret var tomt."""
    ekte(monkeypatch)
    t = FalskTransport("Tiden bygger på vanlig avvik for skipsgruppen.")
    sett_transport(monkeypatch, t)
    inp, p, _ = baselinepar()
    hent_begrunnelse(inp, p, BASELINE)
    assert t.kall[0]["body"]["reasoning"] == {"effort": "none"}
    assert t.kall[0]["body"]["max_tokens"] == 300


@pytest.mark.parametrize("verdi, forventet", [("low", {"effort": "low"}), ("tull", {"effort": "none"}), ("", None)])
def test_resonnering_fra_miljoet(monkeypatch, verdi, forventet):
    ekte(monkeypatch)
    monkeypatch.setenv("LLM_RESONNERING", verdi)
    t = FalskTransport("Tiden bygger på vanlig avvik for skipsgruppen.")
    sett_transport(monkeypatch, t)
    inp, p, _ = baselinepar()
    hent_begrunnelse(inp, p, BASELINE)
    assert t.kall[0]["body"].get("reasoning") == forventet


def _baselineprediksjon(offset):
    import datetime as dt

    from app.prediksjon import Prediksjon

    eta = dt.datetime(2025, 8, 15, 6, 0, tzinfo=dt.timezone.utc)
    return Prediksjon(voyageid=1, horisont_timer=6, predikert_ankomst=eta - dt.timedelta(minutes=offset),
                      forventet_forsinket=None,
                      forklaring={"metode": "kalibrert_baseline", "gruppe": "Øvrige", "offset_minutter": offset,
                                  "eta_reported": eta})


@pytest.mark.parametrize("offset, forventet", [(64.2, -1), (44.75, -1), (-30.0, 1), (0.0, 0)])
def test_retning_baseline_foelger_fortegnet_paa_forskyvningen(offset, forventet):
    """Retningen for baselinen kommer fra det faktiske fortegnet på forskyvningen, ikke fra en antakelse om at den er
    positiv. En negativ forskyvning gir «senere» (predikert = rapportert ETA − offset)."""
    from app.begrunnelse.kontroll import retning

    assert retning(_baselineprediksjon(offset)) == forventet


def test_negativ_forskyvning_godtar_senere_og_avviser_tidligere():
    from app.begrunnelse.kontroll import retning

    r = retning(_baselineprediksjon(-30.0))
    fakta = {"Fast forskyvning (min)": "\u221230,0"}
    assert kontroller("Prediksjonen er senere enn rapportert ETA.", fakta, forventet_forsinket=None, skipsnavn=[],
                      retning=r) is None
    assert kontroller("Prediksjonen er tidligere enn rapportert ETA.", fakta, forventet_forsinket=None, skipsnavn=[],
                      retning=r) == "retning"


def test_dagens_forskyvninger_er_positive():
    """Per 18.11.2026 er begge forskyvningene positive, så baselinen er tidligere enn rapportert ETA for begge gruppene.
    Testen feiler hvis det endres, så noen ser på retningen og teksten i malen («rapportert ETA minus …») på nytt."""
    import json
    from pathlib import Path

    offsets = json.loads((Path(__file__).resolve().parent.parent / "data" / "baseline.json").read_text())["offset_minutter"]
    assert offsets == {"Passasjer": 44.75, "Øvrige": 64.2}


# ---------- begrunnelse-v4: konklusjon, klartekst, begrep og den utvidede retningsregelen ----------

import datetime as dt  # noqa: E402

from app.begrunnelse import klartekst  # noqa: E402
from app.begrunnelse.input import _rekker_fram, _retning_mot_havna, lag_fakta  # noqa: E402
from app.begrunnelse.kontroll import _BEGREP  # noqa: E402
from app.prediksjon import Prediksjon, PrediksjonsInput  # noqa: E402
from app.visning import ukedag_dato_klokke  # noqa: E402

ETA = dt.datetime(2025, 8, 15, 14, 30, tzinfo=dt.timezone.utc)  # fre 15.08 16:30 norsk tid


def alle_rader():
    """Alle modellrader (varsel, uten varsel, delegert) i valideringsvinduet og alle baselinerader i standardvinduet."""
    from conftest import VALIDERING_NAA

    from app.prediksjon import MODELL_DIR
    from app.prediksjon.modell import ModellPrediktor

    ut = []
    inputs = [lag_input(a, VALIDERING_NAA) for a in anlop_i_vindu(VALIDERING_NAA)]
    ut += list(zip(inputs, ModellPrediktor(MODELL_DIR).prediker(inputs, VALIDERING_NAA)))
    inputs = [lag_input(a, STANDARD_NAA) for a in anlop_i_vindu(STANDARD_NAA)]
    ut += list(zip(inputs, BaselinePrediktor().prediker(inputs, STANDARD_NAA)))
    return ut


def syntetisk_inp(eta=ETA, h=6, t_kutt=None):
    return PrediksjonsInput(voyageid=1, mmsino=2, shipname="TESTSKIP", ship_group="Last", gruppe="Øvrige",
                            eta_reported=eta, horisont_timer=h, t_kutt=t_kutt or eta - dt.timedelta(hours=h))


def modellprediksjon(avvik_mot_eta_min, eta=ETA, featurer=None, predikert_avvik=10.0):
    return Prediksjon(voyageid=1, horisont_timer=6, predikert_ankomst=eta + dt.timedelta(minutes=avvik_mot_eta_min),
                      forventet_forsinket=predikert_avvik > 120,
                      forklaring={"metode": "modell", "gruppe": "Øvrige", "predikert_avvik_min": predikert_avvik,
                                  "offset_ovrige_min": 64.2, "eta_reported": eta, "featurer": featurer or {}})


def baselineprediksjon(offset, eta=ETA):
    return Prediksjon(voyageid=1, horisont_timer=6, predikert_ankomst=eta - dt.timedelta(minutes=offset),
                      forventet_forsinket=None,
                      forklaring={"metode": "kalibrert_baseline", "gruppe": "Øvrige", "offset_minutter": offset,
                                  "eta_reported": eta})


@pytest.mark.parametrize("p, forventet", [
    (modellprediksjon(74), "Ventes inn i havneområdet kl. 17:44, 74 min etter rapportert ETA (16:30)."),
    (modellprediksjon(-138), "Ventes inn i havneområdet kl. 14:12, 2 t 18 min før rapportert ETA (16:30)."),
    (baselineprediksjon(64.2), "Ventes inn i havneområdet kl. 15:26, 64 min før rapportert ETA (16:30)."),
    (baselineprediksjon(-30.0), "Ventes inn i havneområdet kl. 17:00, 30 min etter rapportert ETA (16:30)."),  # fortegn fra offset
    (modellprediksjon(0), "Ventes inn i havneområdet kl. 16:30, omtrent ved rapportert ETA (16:30)."),
    (baselineprediksjon(0.0), "Ventes inn i havneområdet kl. 16:30, omtrent ved rapportert ETA (16:30)."),
])
def test_konklusjon(p, forventet):
    assert klartekst.konklusjon(syntetisk_inp(), p) == forventet


def test_konklusjon_ulike_datoer_har_ukedag():
    eta = dt.datetime(2025, 8, 15, 21, 30, tzinfo=dt.timezone.utc)  # fre 23:30 norsk tid
    p = modellprediksjon(74, eta=eta)
    assert klartekst.konklusjon(syntetisk_inp(eta=eta), p) == (
        "Ventes inn i havneområdet lør kl. 00:44, 74 min etter rapportert ETA (fre 23:30).")
    p = modellprediksjon(-74, eta=dt.datetime(2025, 8, 15, 22, 30, tzinfo=dt.timezone.utc))  # lør 00:30
    assert klartekst.konklusjon(syntetisk_inp(eta=p.forklaring["eta_reported"]), p) == (
        "Ventes inn i havneområdet fre kl. 23:16, 74 min før rapportert ETA (lør 00:30).")


@pytest.mark.parametrize("minutter, tekst", [(89, "89 min"), (90, "1 t 30 min"), (120, "2 t"), (-138, "2 t 18 min"),
                                             (0, "0 min")])
def test_varighet(minutter, tekst):
    assert klartekst.varighet(minutter) == tekst


def test_retning_er_fortegnet_paa_konklusjonen():
    assert klartekst.retning(modellprediksjon(74)) == 1
    assert klartekst.retning(modellprediksjon(-74)) == -1
    assert klartekst.retning(modellprediksjon(0)) == 0
    assert klartekst.retning(baselineprediksjon(64.2)) == -1
    assert klartekst.retning(baselineprediksjon(-30.0)) == 1
    from app.begrunnelse import kontroll
    assert kontroll.retning is klartekst.retning


KONKL = "Ventes 74 min senere enn rapportert ETA (17:44 mot 16:30)."
KFAKTA = {"Konklusjon (første setning, ordrett)": KONKL}


def kk(tekst, fakta=KFAKTA, retning=1):
    return kontroller(tekst, fakta, forventet_forsinket=True, skipsnavn=[], retning=retning, konklusjon=KONKL)


def test_kontroll_konklusjon():
    assert kk(f"{KONKL} Skipet går sakte.") is None
    assert kk(KONKL) is None
    assert kk(f"Ventes  74 min senere\nenn rapportert ETA (17:44 mot 16:30). Skipet går sakte.") is None  # blanktegn
    assert kk("Skipet går sakte.") == "konklusjon"  # mangler
    assert kk("Ventes 75 min senere enn rapportert ETA (17:44 mot 16:30). Skipet går sakte.") == "konklusjon"
    assert kk("Ventes 74 min senere enn rapportert ETA. Skipet går sakte.") == "konklusjon"  # endret
    assert kk(f"Skipet går sakte. {KONKL}") == "konklusjon"  # ikke først
    assert kk("") == "tom"  # «tom» kommer før «konklusjon»
    # Uten konklusjon hoppes regelen over.
    assert kontroller("Skipet går sakte.", {}, forventet_forsinket=True, skipsnavn=[]) is None


@pytest.mark.parametrize("ord_", ["kalibrert", "Kalibrerte", "baseline", "Baselinen", "slakk", "slakken",
                                  "treningsdata", "treningsdataene", "kuttet", "kuttpunktet", "kutt", "alder på",
                                  "posisjonsalderen", "offset", "forskyvning", "forskyvningen", "feature",
                                  "featurene", "cos"])
def test_kontroll_begrep(ord_):
    assert kk(f"{KONKL} Det skyldes {ord_} her.") == "begrep"


@pytest.mark.parametrize("tekst", ["Skipet går mot havna.", "Kalibrering er ikke nevnt.", "Det er kosmetisk.",
                                   "Cosinus er ikke med.", "Alderen er ukjent.", "Skipet er på vei."])
def test_kontroll_begrep_ingen_falske_treff(tekst):
    assert kk(f"{KONKL} {tekst}") is None


def test_kontroll_begrep_treffer_ogsaa_kutter():
    """``kutt\\w*`` treffer også «kutter» (båttypen). Det er en kjent falsk positiv: et slikt svar gir mal-teksten."""
    assert _BEGREP.search("En kutter") is not None
    assert kk(f"{KONKL} Skipet er en kutter.") == "begrep"


def test_retning_tillatt_gjennom_fakta():
    """Et retningsord mot fortegnet godtas bare når samme retning står i en faktaverdi."""
    konkl = "Ventes 64 min tidligere enn rapportert ETA (15:26 mot 16:30)."
    tekst = f"{konkl} Skipet har tidligere kommet senere enn vanlig."
    med = {"Konklusjon (første setning, ordrett)": konkl,
           "Skipets tidligere anløp": "anløp, i snitt omtrent mange min senere enn vanlig for skipsgruppen"}
    uten = {"Konklusjon (første setning, ordrett)": konkl}
    assert kontroller(tekst, med, forventet_forsinket=None, skipsnavn=[], retning=-1, konklusjon=konkl) is None
    assert kontroller(tekst, uten, forventet_forsinket=None, skipsnavn=[], retning=-1, konklusjon=konkl) == "retning"
    # «senere» bare i en etikett teller ikke.
    etikett = {"Konklusjon (første setning, ordrett)": konkl, "Senere": "x"}
    assert kontroller(tekst, etikett, forventet_forsinket=None, skipsnavn=[], retning=-1,
                      konklusjon=konkl) == "retning"


@pytest.mark.parametrize("cos, tekst", [(0.3, "på vei mot havna"), (1e-9, "på vei mot havna"),
                                        (-0.3, "på vei bort fra havna"), (-1e-9, "på vei bort fra havna"),
                                        (0.0, "på tvers av retningen til havna")])
def test_retning_mot_havna_tersklene(cos, tekst):
    assert _retning_mot_havna(cos) == tekst


@pytest.mark.parametrize("slakk, h, tekst", [
    (2.0, 6.0, "ja, ca. 2 timer før rapportert ETA"),
    (2.5, 6.0, "ja, ca. 3 timer før rapportert ETA"),  # halve rundes opp
    (1.2, 6.0, "ja, ca. 1 time før rapportert ETA"),
    (0.49, 6.0, "ja, under 1 time før rapportert ETA"),
    (0.0, 6.0, "ja, under 1 time før rapportert ETA"),
    (-3.5, 6.0, "nei, ca. 4 timer etter rapportert ETA"),
    (-0.2, 6.0, "nei, under 1 time etter rapportert ETA"),
    (-48.0, 24.0, "nei, minst 48 timer etter rapportert ETA"),
    (6.0, 6.0, None),  # distanse 0: slakk = h_eff
])
def test_rekker_fram(slakk, h, tekst):
    assert _rekker_fram(slakk, h) == tekst


REKKER = "Rekker fram til rapportert ETA med farten ved siste posisjon"


def _featurer(**over):
    f = {"distanse_km": 40.0, "fart_knop": 10.0, "kurs_mot_havn": 0.9, "posisjon_alder_min": 25.0,
         "slakk_timer": 3.8, "avgangshavn": "annet", "avgatt_for_kutt": None, "timer_siden_avgang": None,
         "fartoy_antall_tidligere": 0, "fartoy_snittavvik_min": None}
    f.update(over)
    return f


def test_lag_fakta_tilstand_i_klartekst():
    inp = syntetisk_inp()
    fakta = lag_fakta(inp, modellprediksjon(74, featurer=_featurer()))
    assert fakta["Siste AIS-posisjon"] == ukedag_dato_klokke(inp.t_kutt - dt.timedelta(minutes=25))
    assert fakta["Avstand til havna"] == "40 km"
    assert fakta["Fart"] == "10,0 knop"
    assert fakta["Retning"] == "på vei mot havna"
    assert fakta[REKKER] == "ja, ca. 4 timer før rapportert ETA"
    assert "Skipets tidligere anløp" not in fakta  # n = 0
    assert "Avgang" not in fakta  # avgangshavn «annet»


def test_lag_fakta_rekker_fram_utelates():
    # Under 1 knop: ingen «rekker fram», og farten er «nesten stille».
    fakta = lag_fakta(syntetisk_inp(), modellprediksjon(74, featurer=_featurer(fart_knop=0.4, slakk_timer=-48.0)))
    assert fakta["Fart"] == "nesten stille (under 1 knop)"
    assert REKKER not in fakta
    # Distanse 0: slakk = h_eff (6 t), ingen seilingstid å regne på.
    fakta = lag_fakta(syntetisk_inp(), modellprediksjon(74, featurer=_featurer(distanse_km=0.0, slakk_timer=6.0)))
    assert REKKER not in fakta
    # Klippet ved −48.
    fakta = lag_fakta(syntetisk_inp(h=24), modellprediksjon(74, featurer=_featurer(slakk_timer=-48.0)))
    assert fakta[REKKER] == "nei, minst 48 timer etter rapportert ETA"
    fakta = lag_fakta(syntetisk_inp(), modellprediksjon(74, featurer=_featurer(slakk_timer=-2.5)))
    assert fakta[REKKER] == "nei, ca. 3 timer etter rapportert ETA"


def test_lag_fakta_uten_tidligere_anlop_selv_med_snitt():
    """Uten tidligere anløp (F16 = 0) er F15 snittet for Øvrige (``Historikk.fartoy``), ikke skipets eget. Det skal
    ikke sendes som skipets historikk."""
    fakta = lag_fakta(syntetisk_inp(), modellprediksjon(74, featurer=_featurer(
        fartoy_antall_tidligere=0, fartoy_snittavvik_min=23.0)))
    assert "Skipets tidligere anløp" not in fakta


def test_lag_fakta_tidligere_anlop_og_avgang():
    fakta = lag_fakta(syntetisk_inp(), modellprediksjon(74, featurer=_featurer(
        fartoy_antall_tidligere=12.0, fartoy_snittavvik_min=-31.0, avgangshavn="ÅGOTNES", avgatt_for_kutt=1.0,
        timer_siden_avgang=2.5)))
    assert fakta["Skipets tidligere anløp"] == "12 anløp, i snitt omtrent 31 min tidligere enn vanlig for skipsgruppen"
    tid = ukedag_dato_klokke(syntetisk_inp().t_kutt)
    assert fakta["Avgang"] == f"avgang fra ÅGOTNES var registrert ca. 3 timer før {tid}"


def test_lag_fakta_uten_interne_begreper_og_kurstall():
    """Ingen forbudte ord og ingen kursverdi i faktaene, for alle modell-, delegerte og baselinerader i
    valideringsvinduet og alle baselinerader i standardvinduet."""
    from app.visning import tall

    sett = set()
    for inp, p in alle_rader():
        fakta = lag_fakta(inp, p)
        tekst = "\n".join(f"{k}: {v}" for k, v in fakta.items())
        assert not _BEGREP.search(tekst), (inp.voyageid, _BEGREP.search(tekst))
        assert "kurs" not in tekst.lower()
        kurs = (p.forklaring.get("featurer") or {}).get("kurs_mot_havn")
        if kurs is not None:
            assert tall(kurs, 2) not in tekst and tall(kurs, 1) not in fakta.get("Retning", "")
            sett.add("kurs")
        sett.add(p.forklaring.get("delegert") or p.forklaring["metode"])
    assert {"kurs", "modell", "kalibrert_baseline", "passasjer"} <= sett


# ---------- begrunnelse-v5: innledning, «kl.»/«ca.», metoderegelen, setninger igjen og avgang som registrert ----------

def varselprediksjon(predikert_avvik, avvik_mot_eta_min=74):
    """En modellrad med varsel, også med negativt predikert avvik (bare mulig syntetisk)."""
    p = modellprediksjon(avvik_mot_eta_min, predikert_avvik=predikert_avvik)
    return Prediksjon(p.voyageid, p.horisont_timer, p.predikert_ankomst, True, p.forklaring)


def delegertprediksjon(offset=64.2, grunn="ingen_tilstand"):
    p = baselineprediksjon(offset)
    return Prediksjon(p.voyageid, p.horisont_timer, p.predikert_ankomst, None, dict(p.forklaring, delegert=grunn))


K74 = "Ventes inn i havneområdet kl. 17:44, 74 min etter rapportert ETA (16:30)."
K64 = "Ventes inn i havneområdet kl. 15:26, 64 min før rapportert ETA (16:30)."


@pytest.mark.parametrize("p, forventet", [
    (varselprediksjon(138.4), f"{K74} Det er 2 t 18 min senere enn vanlig for skipsgruppen."),
    (varselprediksjon(-138.0), f"{K74} Det er 2 t 18 min tidligere enn vanlig for skipsgruppen."),
    (varselprediksjon(121.0), f"{K74} Det er 2 t 1 min senere enn vanlig for skipsgruppen."),
    (modellprediksjon(74, predikert_avvik=10.0), K74),  # modell uten varsel: bare konklusjonen
    (delegertprediksjon(), f"{K64} Det er vanlig for denne skipsgruppen."),
    (baselineprediksjon(64.2), f"{K64} Det er vanlig for denne skipsgruppen."),
])
def test_innledning_per_radtype(p, forventet):
    assert klartekst.innledning(syntetisk_inp(), p) == forventet


def test_er_modellvurdert():
    assert klartekst.er_modellvurdert(modellprediksjon(74)) is True
    assert klartekst.er_modellvurdert(varselprediksjon(150.0)) is True
    assert klartekst.er_modellvurdert(delegertprediksjon()) is False
    assert klartekst.er_modellvurdert(baselineprediksjon(64.2)) is False


@pytest.mark.parametrize("tekst, antall", [
    (K74, 1),
    ("Det er kl. 17:44.", 1),
    ("Kl. 17:44 kommer det. Neste setning.", 2),
    ("Det er ca. 5 min igjen. Neste setning.", 2),
    ("Ca. 5 min igjen.", 1),
    ("Skipet går sakte. Det er langt unna. Det rekker ikke fram.", 3),
    ("Første. Andre.", 2),
])
def test_kl_og_ca_avslutter_ikke_setningen(tekst, antall):
    assert antall_setninger(tekst) == antall


def test_innledningen_har_riktig_antall_setninger():
    for p, forventet in [(varselprediksjon(138.0), 2), (modellprediksjon(74), 1), (baselineprediksjon(64.2), 2),
                         (delegertprediksjon(), 2)]:
        assert antall_setninger(klartekst.innledning(syntetisk_inp(), p)) == forventet


METODE_TEKSTER = [
    "Tiden bygger på vanlig avvik for skipsgruppen.",
    "Det er vanlig avvik for denne skipsgruppen.",
    "Anslaget baserer seg på det vanlige avviket.",
    "Tiden hviler på vanlig avvik.",
    "Det bygger på det vanlige avviket.",
]


@pytest.mark.parametrize("tekst", METODE_TEKSTER)
def test_metoderegelen_avviser_paa_modellrad(tekst):
    assert kontroller(tekst, {}, forventet_forsinket=True, skipsnavn=[], modellrad=True) == "metode"


@pytest.mark.parametrize("tekst", METODE_TEKSTER)
def test_metoderegelen_godtar_paa_baseline_og_delegert(tekst):
    assert kontroller(tekst, {}, forventet_forsinket=None, skipsnavn=[], modellrad=False) is None
    assert kontroller(tekst, {}, forventet_forsinket=None, skipsnavn=[]) is None  # standard er False


def test_metoderegelen_utloses_ikke_av_varselsetningen():
    innl = klartekst.innledning(syntetisk_inp(), varselprediksjon(138.0))
    fakta = lag_fakta(syntetisk_inp(), varselprediksjon(138.0))
    tekst = f"{innl} Det er over varselgrensen på 120 min."
    assert kontroller(tekst, fakta, forventet_forsinket=True, skipsnavn=[], retning=1, konklusjon=innl,
                      modellrad=True) is None
    assert kontroller("Det er 138 min senere enn vanlig for skipsgruppen.", {"a": "138"}, forventet_forsinket=True,
                      skipsnavn=[], modellrad=True) is None


SETNINGER_IGJEN = "Setninger du kan legge til"


@pytest.mark.parametrize("p, igjen", [(varselprediksjon(138.0), "1"), (modellprediksjon(74), "2"),
                                      (baselineprediksjon(64.2), "1"), (delegertprediksjon(), "1")])
def test_setninger_du_kan_legge_til(p, igjen):
    fakta = lag_fakta(syntetisk_inp(), p)
    assert list(fakta)[:2] == ["Innledning (skriv ordrett først)", SETNINGER_IGJEN]
    assert fakta[SETNINGER_IGJEN] == igjen


def test_setninger_du_kan_legge_til_paa_ekte_rader():
    for inp, p in alle_rader():
        forventet = "2" if klartekst.er_modellvurdert(p) and p.forventet_forsinket is not True else "1"
        assert lag_fakta(inp, p)[SETNINGER_IGJEN] == forventet, inp.voyageid


@pytest.mark.parametrize("over, forventet", [
    ({"avgatt_for_kutt": 1.0, "timer_siden_avgang": 2.5}, "avgang fra ÅGOTNES var registrert ca. 3 timer før {tid}"),
    ({"avgatt_for_kutt": 1.0, "timer_siden_avgang": 41.96}, "avgang fra ÅGOTNES var registrert ca. 42 timer før {tid}"),
    ({"avgatt_for_kutt": 1.0, "timer_siden_avgang": 1.0}, "avgang fra ÅGOTNES var registrert ca. 1 time før {tid}"),
    ({"avgatt_for_kutt": 1.0, "timer_siden_avgang": 0.3}, "avgang fra ÅGOTNES var registrert under 1 time før {tid}"),
    ({"avgatt_for_kutt": 1.0, "timer_siden_avgang": None}, "avgang fra ÅGOTNES var registrert per {tid}"),
    ({"avgatt_for_kutt": 0.0, "timer_siden_avgang": None}, "avgang fra ÅGOTNES var ikke registrert per {tid}"),
])
def test_avgang_som_registrert_informasjon(over, forventet):
    inp = syntetisk_inp()
    fakta = lag_fakta(inp, modellprediksjon(74, featurer=_featurer(avgangshavn="ÅGOTNES", **over)))
    assert fakta["Avgang"] == forventet.format(tid=ukedag_dato_klokke(inp.t_kutt))


def test_avgang_aldri_som_sikkert_faktum():
    """Beslutning 11: F13–F14 kunne ikke verifiseres, så ingen faktaverdi sier at skipet «hadde gått»."""
    sett = 0
    for inp, p in alle_rader():
        for v in lag_fakta(inp, p).values():
            assert "hadde gått" not in v and "hadde ikke gått" not in v
            sett += v.startswith("avgang fra ")
    assert sett > 0  # avgangsfeltet finnes på minst én ekte rad


# ---------- v5: koblingen i adapteren (mutasjonssjekken 18.11 fant at den ikke var testet) ----------

def test_adapteren_avviser_vanlig_avvik_som_forklaring_paa_modellrad(monkeypatch, caplog):
    """Adapteren må sende ``modellrad`` til kontrollen. Ellers slipper «Tiden bygger på vanlig avvik for
    skipsgruppen» gjennom på en rad Modell v1 har vurdert (ISLAND CLIPPER i røykkall 3)."""
    from app.begrunnelse.klartekst import innledning

    ekte(monkeypatch)
    inp, p = modellpar(monkeypatch, False)
    sett_transport(monkeypatch, FalskTransport(f"{innledning(inp, p)} Tiden bygger på vanlig avvik for skipsgruppen."))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, "Modell v1")
    assert svar.merke == MERKE_FEILET
    assert "kontroll_metode" in caplog.text


def test_adapteren_krever_hele_innledningen(monkeypatch, caplog):
    """Adapteren må sende hele innledningen, ikke bare konklusjonen. På en baselinerad mangler svaret her
    «Det er vanlig for denne skipsgruppen.», så det skal avvises."""
    from app.begrunnelse.klartekst import konklusjon

    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    sett_transport(monkeypatch, FalskTransport(f"{konklusjon(inp, p)} Beregningen kan ikke varsle avvik."))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar.merke == MERKE_FEILET
    assert "kontroll_konklusjon" in caplog.text


# ---------- begrunnelse-v6: timer avrundet til hele tall, «ca.» slik det står i faktaene ----------

def test_kontrollen_med_hele_timer_fra_faktaene():
    """Faktaene sier «ca. 42 timer». Svaret kan bruke «ca.» uten at setningen deles, og tallet godtas. Et
    desimaltall modellen har regnet ut selv (41,7), avvises."""
    inp = syntetisk_inp()
    p = modellprediksjon(74, featurer=_featurer(avgangshavn="ÅGOTNES", avgatt_for_kutt=1.0,
                                                 timer_siden_avgang=41.7))
    fakta = lag_fakta(inp, p)
    assert fakta["Avgang"].startswith("avgang fra ÅGOTNES var registrert ca. 42 timer før ")
    assert "omtrent 41,7" not in " ".join(fakta.values())

    def sjekk(tillegg):
        return kontroller(f"{K74} {tillegg}", fakta, forventet_forsinket=False, skipsnavn=[],
                          retning=klartekst.retning(p), konklusjon=K74, modellrad=True)

    assert sjekk("Avgang fra Ågotnes var registrert ca. 42 timer før. Skipet rekker ca. 4 timer før.") is None
    assert antall_setninger(f"{K74} Avgang var registrert ca. 42 timer før. Skipet er 40 km unna.") == 3
    assert sjekk("Avgang fra Ågotnes var registrert 41,7 timer før.") == "tall"


# --- E3-S05: forstyrrelsesbriefen (spec-e3-s05-forstyrrelsesbrief) ---------------------------------------------
# Syntetiske prediksjoner for utvalg, sortering og grenser. Ekte modellrader bare fra VALIDERING_NAA (regelen om
# testrader). Ekte modus bare med falsk transport.

from app.begrunnelse import cachet_brief, hent_brief  # noqa: E402
from app.begrunnelse.input import lag_brief_fakta  # noqa: E402
from app.begrunnelse.klartekst import brief_innledning, velg_varslede  # noqa: E402
from app.begrunnelse.kontroll import BRIEF_MAKS_SETNINGER, BRIEF_MAKS_TEGN, BRIEF_MIN_SETNINGER  # noqa: E402
from app.begrunnelse.testmodus import BRIEF_MAL_SLUTT, MERKE_APP, app_brief, brief_mal  # noqa: E402

MODELL = "Modell v1"
NAA_SYNT = dt.datetime(2025, 8, 15, 8, 0, tzinfo=dt.timezone.utc)


ID0 = 3_000_000  # seilas-ID-ene er store, så de ikke finnes som deltall i tider og navn


def navn(n):
    """«SKIP L» for n = 11: skipsnavn uten tall, så tallkontrollen ikke slår til før navnekontrollen."""
    return f"SKIP {chr(ord('A') + n)}"


def syntetisk_par(n, avvik, navn_=None, varsel=None, delegert=None, featurer=None):
    """(input, prediksjon) med Modell v1-form. ``varsel`` None gir ``avvik > 120``. ``delegert`` gir en delegert rad.
    Seilas-ID er ``ID0 + n``, og skipet heter ``navn(n)``."""
    voyageid = ID0 + n
    inp = PrediksjonsInput(voyageid=voyageid, mmsino=900000000 + n, shipname=navn_ or navn(n),
                           ship_group="Last", gruppe="Øvrige", eta_reported=ETA, horisont_timer=6,
                           t_kutt=ETA - dt.timedelta(hours=6))
    if delegert:
        return inp, Prediksjon(voyageid=voyageid, horisont_timer=6, predikert_ankomst=ETA - dt.timedelta(minutes=64),
                               forventet_forsinket=None,
                               forklaring={"metode": "kalibrert_baseline", "gruppe": "Øvrige", "offset_minutter": 64.2,
                                           "eta_reported": ETA, "delegert": delegert})
    return inp, Prediksjon(voyageid=voyageid, horisont_timer=6,
                           predikert_ankomst=ETA + dt.timedelta(minutes=avvik - 64),
                           forventet_forsinket=(avvik > 120) if varsel is None else varsel,
                           forklaring={"metode": "modell", "gruppe": "Øvrige", "predikert_avvik_min": float(avvik),
                                       "offset_ovrige_min": 64.2, "eta_reported": ETA, "featurer": featurer or {}})


def fem_varsler():
    """5 varsler, 1 uten varsel og 1 delegert. Rekkefølgen er blandet med vilje."""
    return [syntetisk_par(15, 150), syntetisk_par(11, 300), syntetisk_par(12, 130), syntetisk_par(13, 250),
            syntetisk_par(14, 250), syntetisk_par(16, 30), syntetisk_par(17, 0, delegert="passasjer")]


def kb(tekst, fakta, konklusjon=None):
    """Kontrollen med briefens regler."""
    return kontroller(tekst, fakta, forventet_forsinket=True, retning=0, konklusjon=konklusjon, modellrad=True,
                      maks_tegn=BRIEF_MAKS_TEGN, min_setninger=BRIEF_MIN_SETNINGER,
                      maks_setninger=BRIEF_MAKS_SETNINGER, skipsnavn=[])


def test_brief_velger_varslede_sortert_etter_avvik():
    valgte, antall = velg_varslede(fem_varsler())
    assert antall == 5
    # Synkende avvik, likt avvik (250) gir lavest seilas-ID først, og høyst 3.
    assert [p.voyageid - ID0 for _, p in valgte] == [11, 13, 14]
    assert all(p.forventet_forsinket is True for _, p in valgte)


def test_brief_tar_bare_forventet_forsinket_true():
    par = [syntetisk_par(1, 500, varsel=False), syntetisk_par(2, 0, delegert="ingen_tilstand"), syntetisk_par(3, 121)]
    valgte, antall = velg_varslede(par)
    assert antall == 1 and [p.voyageid - ID0 for _, p in valgte] == [3]


@pytest.mark.parametrize("n", [1, 2, 3])
def test_brief_med_tre_eller_faerre_varsler(n):
    par = [syntetisk_par(i, 200 + i) for i in range(1, n + 1)]
    valgte, antall = velg_varslede(par)
    assert len(valgte) == antall == n
    start = brief_innledning(valgte, antall)
    assert start.startswith(f"{n} anløp har varsel. ") and "størst avvik" not in start


def test_brief_over_tre_varsler_sier_hvor_mange():
    valgte, antall = velg_varslede(fem_varsler())
    start = brief_innledning(valgte, antall)
    assert start.startswith("5 anløp har varsel, og her er de 3 med størst avvik. ")
    assert [n for n in (navn(11), navn(13), navn(14), navn(12), navn(15)) if n in start] == [
        navn(11), navn(13), navn(14)]
    assert start.index(navn(11)) < start.index(navn(13)) < start.index(navn(14))
    assert f"{navn(11)} ventes inn i havneområdet fre kl. 20:26, 5 t senere enn vanlig for skipsgruppen;" in start
    assert antall_setninger(start) == 2


def test_brief_mal_er_3_setninger_og_bestaar_kontrollen():
    par = fem_varsler()
    valgte, antall = velg_varslede(par)
    tekst = brief_mal(valgte, antall)
    assert tekst == f"{brief_innledning(valgte, antall)} {BRIEF_MAL_SLUTT}"
    assert antall_setninger(tekst) == 3 and len(tekst) <= BRIEF_MAKS_TEGN
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    assert kb(tekst, fakta, brief_innledning(valgte, antall)) is None


def test_brief_kontroll_setninger_3_til_5():
    fakta = {"Innledning": "Anløpet har varsel."}
    tre = "Anløpet har varsel. Det er sent. Det er alt."
    assert kb(tre, fakta) is None
    assert kb("Anløpet har varsel. Det er sent.", fakta) == "setninger"  # 2 < 3
    assert kb(tre + " Mer. Enda mer.", fakta) is None  # 5
    assert kb(tre + " Mer. Enda mer. For mye.", fakta) == "setninger"  # 6 > 5


def test_brief_kontroll_lengde_700_mot_701():
    fakta = {"Innledning": "Anløpet har varsel."}
    start = "Anløpet har varsel. Det er sent. "
    tekst = start + "a" * (700 - len(start) - 1) + "."
    assert len(tekst) == 700 and kb(tekst, fakta) is None
    assert kb(tekst[:-1] + "a.", fakta) == "lengde"


def test_kontroll_standardgrensene_er_uendret():
    """Begrunnelsen beholder 400 tegn og høyst 3 setninger, uten nedre grense ut over at teksten ikke er tom."""
    fakta = {"Skip": "X"}
    assert kontroller("Én setning.", fakta, forventet_forsinket=None, skipsnavn=[]) is None
    assert kontroller("Ja. Nei. Kanskje. Aldri.", fakta, forventet_forsinket=None, skipsnavn=[]) == "setninger"
    assert kontroller("a" * 401, fakta, forventet_forsinket=None, skipsnavn=[]) == "lengde"


def test_brief_kontroll_andre_skip_og_konklusjon():
    par = fem_varsler()
    valgte, antall = velg_varslede(par)
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    start = brief_innledning(valgte, antall)
    regler = dict(forventet_forsinket=True, retning=0, konklusjon=start, modellrad=True, maks_tegn=BRIEF_MAKS_TEGN,
                  min_setninger=BRIEF_MIN_SETNINGER, maks_setninger=BRIEF_MAKS_SETNINGER,
                  skipsnavn=[navn(i) for i in range(11, 18)])
    assert kontroller(f"{start} {navn(11)} er sent ute.", fakta, **regler) is None
    assert kontroller(f"{start} {navn(15)} er også sent ute.", fakta, **regler) == "skipsnavn"  # ikke tatt med
    assert kontroller(f"Oversikt. {start} Mer.", fakta, **regler) == "konklusjon"
    assert kontroller(f"{start} Det kommer tidligere.", fakta, **regler) == "retning"


def test_brief_fakta_bare_modellens_data_og_valgte_skip():
    par = fem_varsler()
    valgte, antall = velg_varslede(par)
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    assert fakta["Anløp i vinduet"] == "7" and fakta["Vurdert av modellen"] == "6"
    assert fakta["Anløp med varsel"] == "5"
    assert fakta["Vindu"] == "fre 15.08 10:00 – lør 16.08 10:00"
    assert fakta["Setninger du kan legge til"] == "3"  # 3 anløp i briefen: én setning per skip (brief-v3)
    assert [fakta[f"Anløp {i} – Skip"] for i in (1, 2, 3)] == [navn(11), navn(13), navn(14)]
    assert "Anløp 4 – Skip" not in fakta
    tekst = json.dumps(fakta, ensure_ascii=False)
    for inp, _ in par:
        assert str(inp.mmsino) not in tekst
    for inp, p in par:
        assert str(p.voyageid) not in tekst
    for annet in (navn(12), navn(15), navn(16), navn(17)):
        assert annet not in tekst
    assert not any(f in tekst for f in FASITFELT)
    assert not any(k.endswith("Innledning (skriv ordrett først)") and k != "Innledning (skriv ordrett først)"
                   for k in fakta)


def test_app_brief_paa_baselinen():
    inp, p, _ = baselinepar()
    par = [(inp, p)] * 3
    tekst = app_brief(par)
    assert tekst == ("3 anløp har rapportert ETA i vinduet. Modellen har ikke vurdert noen av dem, og ingen har "
                     "varsel. Tidene bygger bare på vanlig avvik for skipsgruppen, og den beregningen kan ikke varsle.")
    assert antall_setninger(tekst) == 3


def test_app_brief_med_modellen_uten_varsler():
    par = [syntetisk_par(1, 30), syntetisk_par(2, -10), syntetisk_par(3, 0, delegert="passasjer"),
           syntetisk_par(4, 0, delegert="passasjer"), syntetisk_par(5, 0, delegert="i_sonen_ved_kutt")]
    tekst = app_brief(par)
    assert tekst == ("5 anløp har rapportert ETA i vinduet. Modellen har vurdert 2 av dem, og ingen har varsel. "
                     "De 3 andre er ikke vurdert: rutegående skip vurderes ikke av modellen (2 anløp) og skipet var "
                     "allerede i havneområdet (1 anløp).")
    assert antall_setninger(tekst) == 3
    assert app_brief(par[:2]).endswith("Alle anløpene er vurdert av modellen.")
    assert "Det andre anløpet er ikke vurdert: ingen AIS-posisjon å vurdere (1 anløp)." in app_brief(
        [syntetisk_par(1, 30), syntetisk_par(2, 0, delegert="ingen_tilstand")])


def test_hent_brief_testmodus():
    par = fem_varsler()
    svar = hent_brief(par, NAA_SYNT, MODELL)
    valgte, antall = velg_varslede(par)
    assert svar == Begrunnelse(brief_mal(valgte, antall), MERKE_TEST) == cachet_brief(par, NAA_SYNT, MODELL)
    assert begrunnelse.antall_kall() == 0


@pytest.mark.parametrize("modus", ["test", "ekte"])
def test_brief_uten_varsler_er_laget_av_appen_uten_kall(monkeypatch, modus):
    if modus == "ekte":
        ekte(monkeypatch)
    t = sett_transport(monkeypatch, FalskTransport("skal ikke brukes"))
    for par in ([syntetisk_par(1, 30), syntetisk_par(2, 0, delegert="passasjer")], [baselinepar()[:2]]):
        assert cachet_brief(par, NAA_SYNT, MODELL) == hent_brief(par, NAA_SYNT, MODELL) == Begrunnelse(
            app_brief(par), MERKE_APP)
    assert t.kall == [] and begrunnelse.antall_kall() == 0 and begrunnelse._cache == {}


def godt_brief_svar(par):
    valgte, antall = velg_varslede(par)
    return f"{brief_innledning(valgte, antall)} Modellen venter at alle tre kommer senere enn vanlig, så følg med på dem."


def test_brief_ekte_med_mock_og_cache(monkeypatch):
    ekte(monkeypatch)
    par = fem_varsler()
    svaret = godt_brief_svar(par).replace("alle tre", "alle")
    t = sett_transport(monkeypatch, FalskTransport(svaret))
    assert cachet_brief(par, NAA_SYNT, MODELL) is None
    svar = hent_brief(par, NAA_SYNT, MODELL)
    assert svar == Begrunnelse(svaret, MERKE_KI)
    assert len(t.kall) == 1
    body = t.kall[0]["body"]
    system, bruker = body["messages"][0]["content"], body["messages"][1]["content"]
    assert "oversikt til havnevakta" in system and "Skriv oversikten." in bruker
    assert f"- Anløp 1 – Skip: {navn(11)}" in bruker and navn(15) not in bruker
    assert body["max_tokens"] == 300
    # Cachetreff: server-rendret, 0 nye kall. Nytt «nå» eller ny prediktor er en ny nøkkel.
    assert cachet_brief(par, NAA_SYNT, MODELL) == svar == hent_brief(par, NAA_SYNT, MODELL)
    assert len(t.kall) == 1
    hent_brief(par, NAA_SYNT + dt.timedelta(hours=1), MODELL)
    hent_brief(par, NAA_SYNT, "Annen prediktor")
    assert len(t.kall) == 3


@pytest.mark.parametrize("utfall, kode", [
    (500, "http_500"), (402, "kvote_402"), (TimeoutError(), "timeout"), ("", "kontroll_tom"),
    ("{start}", "kontroll_setninger"),  # bare innledningen: 2 setninger, under nedre grense på 3
    ("{start} En. To. Tre. Fire.", "kontroll_setninger"),  # 6 setninger, over øvre grense på 5
    ("{start} " + "x" * 700 + ".", "kontroll_lengde"),
    ("{start} Været er dårlig. Det er alt.", "kontroll_aarsak"),
    ("Oversikt. {start} Det er alt.", "kontroll_konklusjon"),
])
def test_brief_feil_gir_mal_og_logges(monkeypatch, caplog, utfall, kode):
    ekte(monkeypatch)
    par = [syntetisk_par(1, 200, navn_="ALFA")]  # én varsel: innledningen er 2 setninger
    valgte, antall = velg_varslede(par)
    start = brief_innledning(valgte, antall)
    if isinstance(utfall, str):
        utfall = utfall.replace("{start}", start)
    sett_transport(monkeypatch, FalskTransport(utfall))
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_brief(par, NAA_SYNT, MODELL)
    assert svar == Begrunnelse(brief_mal(valgte, antall), MERKE_FEILET)
    assert f"brief: {kode} naa={NAA_SYNT.isoformat()} prediktor={MODELL}" in caplog.text
    assert cachet_brief(par, NAA_SYNT, MODELL) == svar  # feilen er cachet i 300 s


def test_brief_uten_nokkel(monkeypatch, caplog):
    ekte(monkeypatch, nokkel=None)
    par = fem_varsler()
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_FEILET
    assert begrunnelse.antall_kall() == 0 and "brief: mangler_nokkel" in caplog.text


def test_brief_deler_kallgrensen_med_begrunnelsene(monkeypatch, caplog):
    ekte(monkeypatch)
    monkeypatch.setenv("LLM_MAKS_KALL", "2")
    inp, p, _ = baselinepar()
    par = fem_varsler()
    t = sett_transport(monkeypatch, FalskTransport(godt_svar(inp, p)))
    assert hent_begrunnelse(inp, p, BASELINE).merke == MERKE_KI
    t.svar = godt_brief_svar(par).replace("alle tre", "alle")
    assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_KI
    assert begrunnelse.antall_kall() == 2
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        assert hent_brief(par, NAA_SYNT, "Annen prediktor") == begrunnelse.testbrief(par, MERKE_GRENSE)
        assert hent_begrunnelse(inp, p, "Annen prediktor").merke == MERKE_GRENSE
    assert "brief: kallgrense" in caplog.text and len(t.kall) == 2
    # Cachede svar vises fortsatt over grensen.
    assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_KI


def test_brief_nokkelen_lekker_ikke(monkeypatch, caplog):
    ekte(monkeypatch)
    par = fem_varsler()
    tekster = []
    with caplog.at_level(logging.DEBUG):
        for i, utfall in enumerate([godt_brief_svar(par), 401, 402, TimeoutError("timed out"), "tull 99999."]):
            sett_transport(monkeypatch, FalskTransport(utfall))
            tekster.append(json.dumps(hent_brief(par, NAA_SYNT, f"P{i}").som_dict()))
    assert FALSK_NOKKEL not in caplog.text and all(FALSK_NOKKEL not in t for t in tekster)


def test_brief_adapteren_tar_ikke_anlop():
    inp, p, anlop = baselinepar()
    with pytest.raises(TypeError):
        hent_brief([(anlop, p)], NAA_SYNT, BASELINE)
    with pytest.raises(TypeError):
        cachet_brief([(anlop, p)], NAA_SYNT, BASELINE)


def test_prompt_brief_er_versjonert():
    tekst = openrouter_klient.PROMPT_BRIEF_FIL.read_text(encoding="utf-8")
    assert "brief-v4" in tekst
    system, bruker = openrouter_klient.bygg_prompt({"Skip": "X"}, openrouter_klient.PROMPT_BRIEF_FIL)
    assert "Ikke finn på årsaker" in system and "- Skip: X" in bruker and "brief-v4" not in system + bruker
    # Standardfila er uendret.
    assert openrouter_klient.bygg_prompt({"Skip": "X"})[0] != system


def test_brief_i_valideringsvinduet_med_modellen():
    """Modell v1 i valideringsvinduet: varslene i avviksrekkefølge, ingen andre skip, og malen består kontrollen."""
    from conftest import VALIDERING_NAA

    from app.prediksjon import MODELL_DIR
    from app.prediksjon.modell import ModellPrediktor

    inputs = [lag_input(a, VALIDERING_NAA) for a in anlop_i_vindu(VALIDERING_NAA)]
    par = list(zip(inputs, ModellPrediktor(MODELL_DIR).prediker(inputs, VALIDERING_NAA)))
    valgte, antall = velg_varslede(par)
    forventet = sorted([(inp, p) for inp, p in par if p.forventet_forsinket is True],
                       key=lambda ip: -ip[1].forklaring["predikert_avvik_min"])
    assert antall >= 2 and [i.shipname for i, _ in valgte] == [i.shipname for i, _ in forventet][:3]
    tekst = begrunnelse.testbrief(par).tekst
    fakta = lag_brief_fakta(par, VALIDERING_NAA, valgte, antall)
    assert kontroller(tekst, fakta, forventet_forsinket=True, retning=0, konklusjon=brief_innledning(valgte, antall),
                      modellrad=True, maks_tegn=BRIEF_MAKS_TEGN, min_setninger=BRIEF_MIN_SETNINGER,
                      maks_setninger=BRIEF_MAKS_SETNINGER) is None
    andre = {i.shipname for i, _ in par} - {i.shipname for i, _ in valgte}
    assert not any(n in tekst or n in json.dumps(fakta, ensure_ascii=False) for n in andre)


# Initialer i skipsnavn deler ikke setninger (gjennomgang av E3-S05) --------------------------------------------

@pytest.mark.parametrize("tekst, antall", [
    ("G. M. DANNEVIG ventes inn. Det er sent.", 2),
    ("LT. PETE MAVERICK MITCHELL ventes inn. Det er sent.", 2),
    ("Det er kl. 17:44. Det er ca. 6 timer igjen.", 2),
    ("Det er sent. Det er alt.", 2),
])
def test_initialer_avslutter_ikke_setningen(tekst, antall):
    assert antall_setninger(tekst) == antall


def test_brief_med_initialer_i_skipsnavnet():
    par = [syntetisk_par(1, 200, navn_="G. M. DANNEVIG"), syntetisk_par(2, 150, navn_="LT. PETE MAVERICK MITCHELL")]
    valgte, antall = velg_varslede(par)
    start = brief_innledning(valgte, antall)
    assert antall_setninger(start) == 2
    assert antall_setninger(brief_mal(valgte, antall)) == 3
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    assert fakta["Setninger du kan legge til"] == "2"
    navn_i_utdraget = ["G. M. DANNEVIG", "LT. PETE MAVERICK MITCHELL", "ANNET SKIP"]
    regler = dict(forventet_forsinket=True, retning=0, konklusjon=start, modellrad=True, maks_tegn=BRIEF_MAKS_TEGN,
                  min_setninger=BRIEF_MIN_SETNINGER, maks_setninger=BRIEF_MAKS_SETNINGER, skipsnavn=navn_i_utdraget)
    assert kontroller(brief_mal(valgte, antall), fakta, **regler) is None
    assert kontroller(f"{start} G. M. DANNEVIG kommer senere enn vanlig. Følg med på det.", fakta, **regler) is None


def test_app_brief_alle_rader_delegert():
    par = [syntetisk_par(1, 0, delegert="passasjer"), syntetisk_par(2, 0, delegert="passasjer"),
           syntetisk_par(3, 0, delegert="ingen_tilstand")]
    tekst = app_brief(par)
    assert tekst == ("3 anløp har rapportert ETA i vinduet. Modellen har ikke vurdert noen av dem, og ingen har "
                     "varsel. Grunnene er: rutegående skip vurderes ikke av modellen (2 anløp) og ingen AIS-posisjon "
                     "å vurdere (1 anløp).")
    assert antall_setninger(tekst) == 3 and "andre" not in tekst and "vurdert 0" not in tekst


# ---------- brief-v2 og begrunnelse-v7: setninger etter innledningens lengde, «rekker fram» bare mot havna ----------

from app.begrunnelse.input import BRIEF_MAKS_TILLEGG, brief_setninger_igjen  # noqa: E402


@pytest.mark.parametrize("antall_skip, forventet", [(1, 2), (2, 2), (3, 3)])
def test_brief_setninger_igjen_etter_innledningen(antall_skip, forventet):
    """1 varsel gir 2 setninger etter lengden (brief-v2). 2–3 varsler gir én per skip (brief-v3)."""
    par = [syntetisk_par(i, 300 - 10 * i, navn_=f"SKIP MED LANGT NAVN {i}") for i in range(1, antall_skip + 1)]
    valgte, antall = velg_varslede(par)
    start = brief_innledning(valgte, antall)
    assert brief_setninger_igjen(start, len(valgte)) == forventet
    assert lag_brief_fakta(par, NAA_SYNT, valgte, antall)["Setninger du kan legge til"] == str(forventet)


def test_brief_setninger_igjen_grensene():
    assert brief_setninger_igjen("Kort. Start.") == BRIEF_MAKS_TILLEGG == 2
    assert brief_setninger_igjen("x" * 690) == 1  # alltid minst 1, så briefen når 3 setninger
    assert brief_setninger_igjen("En. To. Tre. Fire.") == 1  # aldri over 5 til sammen
    assert brief_setninger_igjen("En. To.", 3) == 3  # én per skip
    assert brief_setninger_igjen("En. To. Tre.", 3) == 2  # men aldri over 5 til sammen
    assert brief_setninger_igjen("x" * 690, 2) == 2  # med flere skip styrer antallet, ikke lengden


def test_brief_kontrollen_godtar_ikke_flere_setninger_enn_lovet(monkeypatch):
    ekte(monkeypatch)
    par = fem_varsler()  # 3 anløp i briefen: modellen får legge til 3 setninger, én per skip
    valgte, antall = velg_varslede(par)
    start = brief_innledning(valgte, antall)
    t = FalskTransport(f"{start} Den første er nær. Den andre er nær. Den tredje er nær. Følg med.")
    monkeypatch.setattr(begrunnelse, "transport", t)
    assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_FEILET
    begrunnelse.nullstill()
    t.svar = f"{start} Den første er nær. Den andre er nær. Den tredje er nær."
    assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_KI
    begrunnelse.nullstill()
    par1 = par[:1] + [ip for ip in par if ip[1].forventet_forsinket is not True]  # 1 varsel: høyst 2 setninger
    valgte1, antall1 = velg_varslede(par1)
    assert antall1 == 1
    start1 = brief_innledning(valgte1, antall1)
    t.svar = f"{start1} Den er nær. Den er rask. Følg med."
    assert hent_brief(par1, NAA_SYNT, MODELL).merke == MERKE_FEILET


@pytest.mark.parametrize("kurs, med", [(0.9, True), (1e-9, True), (0.0, False), (-0.3, False), (None, False)])
def test_rekker_fram_bare_paa_vei_mot_havna(kurs, med):
    """«Rekker fram» er regnet bare ut fra avstand og fart. På vei bort fra havna (eller på tvers) leses det som en
    selvmotsigelse, så feltet sendes ikke (begrunnelse-v7, brief-v2). Gjelder begrunnelsen og briefen."""
    p = modellprediksjon(74, featurer=_featurer(kurs_mot_havn=kurs, slakk_timer=3.8))
    fakta = lag_fakta(syntetisk_inp(), p)
    assert (REKKER in fakta) is med



@pytest.mark.parametrize("antall_skip", [2, 3])
def test_brief_fakta_med_flere_skip_bare_avstand_retning_og_fart(antall_skip):
    """Med 2–3 varsler sendes bare skip, avstand, retning og fart per skip (brief-v3), så setningene blir korte."""
    par = [syntetisk_par(i, 300 - 10 * i, featurer=_featurer(avgangshavn="ÅGOTNES", avgatt_for_kutt=1.0,
                                                             timer_siden_avgang=2.0, fartoy_antall_tidligere=5.0,
                                                             fartoy_snittavvik_min=20.0))
           for i in range(1, antall_skip + 1)]
    valgte, antall = velg_varslede(par)
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    for nr in range(1, antall_skip + 1):
        felt = {k.split(" – ", 1)[1] for k in fakta if k.startswith(f"Anløp {nr} – ")}
        assert felt == {"Skip", "Siste AIS-posisjon", "Avstand til havna", "Retning", "Fart"}, felt


def test_brief_fakta_med_ett_skip_er_som_foer():
    par = [syntetisk_par(1, 200, featurer=_featurer(avgangshavn="ÅGOTNES", avgatt_for_kutt=1.0,
                                                    timer_siden_avgang=2.0))]
    valgte, antall = velg_varslede(par)
    fakta = lag_brief_fakta(par, NAA_SYNT, valgte, antall)
    for felt in ("Konklusjon", "Avgang", "Avstand til havna", "Retning", "Fart", REKKER):
        assert f"Anløp 1 – {felt}" in fakta, felt


# ---------- begrunnelse-v8 og brief-v4: avstand, fart og retning i fortid, ved siste posisjon ----------

@pytest.mark.parametrize("setning", [
    "NYKSUND er 212 km fra havna.",
    "Skipet ligger 40 km unna.",
    "Skipet er nå 16 km fra havna.",
    "BERGEN LNG går med 8,1 knop.",
    "Skipet går 10 kn mot havna.",
    "Skipet er på vei mot havna.",
    "Det er på vei bort fra havna.",
])
def test_kontrollen_avviser_presens_om_posisjonen(setning):
    fakta = {"Skip": "NYKSUND", "Avstand til havna": "212 km", "Fart": "8,1 knop", "Retning": "på vei mot havna"}
    assert kontroller(setning.replace("NYKSUND", "Skipet").replace("BERGEN LNG", "Skipet")
                      .replace("40", "212").replace("16", "212").replace("10 kn", "8,1 kn"),
                      fakta, forventet_forsinket=False, skipsnavn=[]) == "presens"


@pytest.mark.parametrize("setning", [
    "Skipet var 212 km fra havna med 8,1 knop og på vei mot havna ved siste posisjon.",
    "Ved siste posisjon var det på vei mot havna.",
    "Det er 212 km igjen etter siste posisjon, sier faktaene.",  # «er 212 km» uten «fra havna» er også presens
])
def test_kontrollen_godtar_fortid_om_posisjonen(setning):
    fakta = {"Avstand til havna": "212 km", "Fart": "8,1 knop", "Retning": "på vei mot havna"}
    regel = kontroller(setning, fakta, forventet_forsinket=False, skipsnavn=[])
    if "er 212 km" in setning:
        assert regel == "presens"
    else:
        assert regel is None


def test_brief_med_presens_gir_mal(monkeypatch):
    ekte(monkeypatch)
    par = fem_varsler()
    valgte, antall = velg_varslede(par)
    start = brief_innledning(valgte, antall)
    t = FalskTransport(f"{start} Den første er på vei mot havna. Den andre var nær. Den tredje var nær.")
    monkeypatch.setattr(begrunnelse, "transport", t)
    assert hent_brief(par, NAA_SYNT, MODELL).merke == MERKE_FEILET
