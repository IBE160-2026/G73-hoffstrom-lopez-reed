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
    fakta = lag_fakta(inp, p)
    assert fakta["Skip"] == inp.shipname
    assert fakta["Rapportert ETA (norsk tid)"] == ukedag_dato_klokke(inp.eta_reported)
    assert fakta["Predikert ankomst (norsk tid)"] == ukedag_dato_klokke(p.predikert_ankomst)
    assert fakta["Metode"] == "Kalibrert baseline"
    assert fakta["Varsel"] == "ingen (baselinen kan ikke varsle)"
    assert any(k.startswith("Fast forskyvning") for k in fakta)


def test_input_modell_har_avvik_og_featurer(monkeypatch):
    from app.begrunnelse.input import lag_fakta

    inp, p = modellpar(monkeypatch, True)
    fakta = lag_fakta(inp, p)
    assert fakta["Metode"] == "Modell v1"
    assert fakta["Varsel"].startswith("ja")
    assert fakta["Predikert avvik fra kalibrert baseline (min)"] == f"{p.forklaring['predikert_avvik_min']:.0f}"
    assert "Distanse til havna (km)" in fakta
    inp, p = modellpar(monkeypatch, None)
    fakta = lag_fakta(inp, p)
    assert "Hvorfor Modell v1 ikke vurderer anløpet" in fakta
    assert fakta["Varsel"].startswith("ingen")


# --- E3-S03: ekte klient (bare med falsk transport), prompt og kontroll -----------------------------------------

import urllib.error  # noqa: E402

from app.begrunnelse import openrouter_klient  # noqa: E402
from app.begrunnelse.kontroll import antall_setninger, kontroller  # noqa: E402
from app.begrunnelse.testmodus import MERKE_GRENSE, MERKE_KI  # noqa: E402


def godt_svar(inp, p):
    """Et svar som består kontrollen: bare tall og navn fra inputen, ingen årsaksord."""
    from app.begrunnelse.input import lag_fakta

    fakta = lag_fakta(inp, p)
    return (f"{inp.shipname} har rapportert ETA {fakta['Rapportert ETA (norsk tid)']}. "
            f"Prediksjonen er kalibrert baseline med forskyvning på "
            f"{fakta['Fast forskyvning: median tid fra sonegrense til kai for gruppen (min)']} min.")


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
    assert "begrunnelse-v2" in tekst
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
    fakta = {"Offset (min)": "64,2", "Fart (knop)": "9"}
    assert kontroller("Offset 64,20 min og fart 9,0 knop.", fakta, forventet_forsinket=True, skipsnavn=[]) is None
    assert kontroller("Offset 64,21 min.", fakta, forventet_forsinket=True, skipsnavn=[]) == "tall"


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

    for inp, p in [baselinepar()[:2], modellpar(monkeypatch, True), modellpar(monkeypatch, False),
                   modellpar(monkeypatch, None)]:
        from app.begrunnelse.kontroll import retning

        assert kontroller(begrunnelse.testtekst(inp, p).tekst, lag_fakta(inp, p),
                          forventet_forsinket=p.forventet_forsinket, retning=retning(p)) is None


def test_mislykket_kontroll_logges(monkeypatch, caplog):
    ekte(monkeypatch)
    inp, p, _ = baselinepar()
    sett_transport(monkeypatch, FalskTransport("Været gjør at skipet kommer sent."))
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
    ("Skipet kommer senere enn baseline.", 1, None),
    ("Skipet kommer tidligere enn baseline.", 1, "retning"),
    ("Skipet kommer før tiden.", 1, "retning"),
    ("Skipet kommer tidligere enn baseline.", -1, None),
    ("Skipet kommer senere enn baseline.", -1, "retning"),
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
    ekte(monkeypatch)
    sett_transport(monkeypatch, FalskTransport("Prediksjonen er tidligere enn rapportert ETA. Baselinen er senere."))
    inp, p, _ = baselinepar()
    with caplog.at_level(logging.WARNING, logger="app.begrunnelse"):
        svar = hent_begrunnelse(inp, p, BASELINE)
    assert svar.merke != MERKE_KI
    assert "kontroll_retning" in caplog.text


def test_resonnering_er_av_som_standard(monkeypatch):
    """Røykkallet 18.11.2026: med modellens standard gikk alle 300 tokens til resonnering, og svaret var tomt."""
    ekte(monkeypatch)
    t = FalskTransport("Prediksjonen er kalibrert baseline.")
    sett_transport(monkeypatch, t)
    inp, p, _ = baselinepar()
    hent_begrunnelse(inp, p, BASELINE)
    assert t.kall[0]["body"]["reasoning"] == {"effort": "none"}
    assert t.kall[0]["body"]["max_tokens"] == 300


@pytest.mark.parametrize("verdi, forventet", [("low", {"effort": "low"}), ("tull", {"effort": "none"}), ("", None)])
def test_resonnering_fra_miljoet(monkeypatch, verdi, forventet):
    ekte(monkeypatch)
    monkeypatch.setenv("LLM_RESONNERING", verdi)
    t = FalskTransport("Prediksjonen er kalibrert baseline.")
    sett_transport(monkeypatch, t)
    inp, p, _ = baselinepar()
    hent_begrunnelse(inp, p, BASELINE)
    assert t.kall[0]["body"].get("reasoning") == forventet
