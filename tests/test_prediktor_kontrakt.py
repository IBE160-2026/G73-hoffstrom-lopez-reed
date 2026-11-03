"""Kontrakttest for alle prediktorer (arkitektur §3, E1-S04).

En ny prediktor legges i ``PREDIKTORER`` og er ikke ferdig før den består alt her,
inkludert lekkasjetestene: input har ingen fasit, fasit kan ikke endre en prediksjon,
og kuttpunktet ligger aldri etter «nå».
"""
import ast
import dataclasses
import datetime as dt
import importlib
import inspect
from pathlib import Path

import pytest

from app.data import Anlop, anlop_i_vindu, last_utdrag
from app.prediksjon import Prediksjon, PrediksjonsInput, lag_input
from app.prediksjon.baseline import BaselinePrediktor
from app.prediksjon.naiv import NaivPrediktor

UTC = dt.timezone.utc
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "anlop_mini.csv"
PREDIKSJON_DIR = Path(__file__).resolve().parent.parent / "app" / "prediksjon"
METRIKKER = Path(__file__).resolve().parent.parent / "app" / "metrikker.py"
NAA = dt.datetime(2025, 10, 8, 6, 0, tzinfo=UTC)  # 08:00 norsk tid, standardvinduet
TEST_FRA = dt.datetime(2025, 9, 14, 3, 15, tzinfo=UTC)

FASITFELT = {"faktisk_ankomst", "status_in_area", "split"}
INPUTFELT = (
    "voyageid", "mmsino", "shipname", "ship_group", "gruppe",
    "eta_reported", "horisont_timer", "t_kutt",
)

# E2-S07 legger til ModellPrediktor her.
PREDIKTORER = [BaselinePrediktor, NaivPrediktor]


@pytest.fixture(params=PREDIKTORER, ids=lambda k: k.__name__)
def prediktor(request):
    return request.param()


@pytest.fixture
def mini():
    return last_utdrag(FIXTURE)


@pytest.fixture(scope="module")
def ekte():
    return last_utdrag()


# --- Input-verdien ---------------------------------------------------------------


def test_input_har_bare_kjente_felt():
    assert tuple(f.name for f in dataclasses.fields(PrediksjonsInput)) == INPUTFELT


def test_input_har_ingen_vei_til_fasit(mini):
    for a in mini:
        inp = lag_input(a, NAA)
        offentlig = {n for n in dir(inp) if not n.startswith("_")}
        assert not offentlig & FASITFELT
        for f in dataclasses.fields(inp):
            assert not isinstance(getattr(inp, f.name), Anlop)
        assert not any(isinstance(v, Anlop) for v in vars(inp).values())


def test_input_er_frossen(mini):
    inp = lag_input(mini[0], NAA)
    with pytest.raises(dataclasses.FrozenInstanceError):
        inp.eta_reported = NAA  # type: ignore[misc]


class _JukserFaktisk:
    navn = "Jukser (faktisk ankomst)"
    kan_varsle = False

    def prediker(self, inputs, naa):
        return [
            Prediksjon(i.voyageid, i.horisont_timer, i.faktisk_ankomst, None, {})
            for i in inputs
        ]


class _JukserStatus:
    navn = "Jukser (status)"
    kan_varsle = False

    def prediker(self, inputs, naa):
        return [
            Prediksjon(i.voyageid, i.horisont_timer, i.eta_reported,
                       i.status_in_area != "ok", {})
            for i in inputs
        ]


@pytest.mark.parametrize("jukser", [_JukserFaktisk, _JukserStatus])
def test_juksende_prediktor_far_attributeerror(jukser, mini):
    inputs = [lag_input(a, NAA) for a in anlop_i_vindu(NAA, anlop=mini)]
    with pytest.raises(AttributeError):
        jukser().prediker(inputs, NAA)


# --- Alle prediktorer --------------------------------------------------------------


def test_navn_og_kan_varsle(prediktor):
    assert isinstance(prediktor.navn, str) and prediktor.navn
    assert isinstance(prediktor.kan_varsle, bool)


def test_prediksjon_folger_kontrakten(prediktor, ekte):
    inputs = [lag_input(a, NAA) for a in anlop_i_vindu(NAA, anlop=ekte)]
    assert inputs
    prediksjoner = prediktor.prediker(inputs, NAA)
    assert [p.voyageid for p in prediksjoner] == [i.voyageid for i in inputs]
    for inp, p in zip(inputs, prediksjoner):
        assert isinstance(p, Prediksjon)
        assert p.horisont_timer == inp.horisont_timer in (6, 24)
        assert p.predikert_ankomst.utcoffset() == dt.timedelta(0)
        assert isinstance(p.forklaring, dict)
        assert {"metode", "gruppe"} <= p.forklaring.keys()
        if not prediktor.kan_varsle:
            assert p.forventet_forsinket is None


def test_tar_ikke_anlop_direkte(prediktor, mini):
    with pytest.raises(TypeError):
        prediktor.prediker(list(anlop_i_vindu(NAA, anlop=mini)), NAA)


def _endre_fasit(a: Anlop) -> Anlop:
    if a.faktisk_ankomst is None:
        return dataclasses.replace(
            a, faktisk_ankomst=a.eta_reported + dt.timedelta(hours=7), status_in_area="ok"
        )
    return dataclasses.replace(
        a, faktisk_ankomst=a.faktisk_ankomst - dt.timedelta(hours=5), status_in_area="empty"
    )


def test_endret_fasit_gir_identiske_prediksjoner(prediktor, mini, ekte):
    for naa, kilde in ((NAA, mini), (NAA, ekte)):
        anlop = anlop_i_vindu(naa, anlop=kilde)
        endret = [_endre_fasit(a) for a in anlop]
        assert [a.faktisk_ankomst for a in endret] != [a.faktisk_ankomst for a in anlop]
        for a, b in zip(anlop, endret):
            assert lag_input(a, naa) == lag_input(b, naa)
        foer = prediktor.prediker([lag_input(a, naa) for a in anlop], naa)
        etter = prediktor.prediker([lag_input(a, naa) for a in endret], naa)
        assert foer == etter


# --- Kuttpunktet (flyttet fra E2-S07) ---------------------------------------------


def _spredte_naa(ekte, antall=20):
    slutt = max(a.eta_reported for a in ekte if a.split == "test")
    steg = (slutt - TEST_FRA) / antall
    return [TEST_FRA + steg * i for i in range(antall)]


def test_kutt_ikke_etter_naa(ekte):
    """``t_kutt ≤ nå`` for hvert anløp i testperioden, ved 20 spredte «nå».

    Bruker alle anløp i testsplitten, ikke bare 24 t-vinduet, så klemmen mot «nå»
    også testes for anløp lenger fram enn 24 t (E1-S06 valg B).
    """
    test = [a for a in ekte if a.split == "test"]
    for naa in _spredte_naa(ekte):
        for a in test:
            inp = lag_input(a, naa)
            assert inp.t_kutt <= naa, (a.voyageid, naa)
            assert inp.t_kutt <= inp.eta_reported - dt.timedelta(hours=inp.horisont_timer)


# --- Kildekoden --------------------------------------------------------------------


def _prediktormoduler():
    grense = PREDIKSJON_DIR / "__init__.py"
    return sorted(p for p in PREDIKSJON_DIR.rglob("*.py") if p != grense)


def _forbudte_referanser(kilde: str):
    feil = []
    for node in ast.walk(ast.parse(kilde)):
        if isinstance(node, ast.Import):
            feil += [a.name for a in node.names if a.name == "app.data"
                     or a.name.startswith("app.data.")]
        elif isinstance(node, ast.ImportFrom):
            modul = node.module or ""
            navn = [a.name for a in node.names]
            if modul == "app.data" or modul.startswith("app.data."):
                feil.append(modul)
            elif modul == "app" and "data" in navn:
                feil.append("from app import data")
            elif node.level >= 2 and (modul == "data" or modul.startswith("data.")
                                      or (not modul and "data" in navn)):
                feil.append("relativ import av app.data")
        tekst = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            tekst = node.value
        elif isinstance(node, ast.Name):
            tekst = node.id
        elif isinstance(node, ast.Attribute):
            tekst = node.attr
        elif isinstance(node, ast.alias):
            tekst = node.name
        if tekst and "utdrag" in tekst.lower():
            feil.append(f"refererer utdrag: {tekst!r}")
    return feil


def test_prediktormoduler_finnes():
    assert {"baseline.py", "naiv.py"} <= {p.name for p in _prediktormoduler()}


def _prediktorklasser():
    """Alle klasser med ``prediker`` definert i en prediktormodul."""
    rot = PREDIKSJON_DIR.parent.parent
    funnet = set()
    for sti in _prediktormoduler():
        modulnavn = ".".join(sti.relative_to(rot).with_suffix("").parts)
        modul = importlib.import_module(modulnavn)
        for _, klasse in inspect.getmembers(modul, inspect.isclass):
            if klasse.__module__ == modul.__name__ and callable(getattr(klasse, "prediker", None)):
                funnet.add(klasse)
    return funnet


def test_alle_prediktorer_er_i_kontrakten():
    """Ingen prediktor slipper unna kontrakten (E1-S05, gruppekrav 1).

    Hver klasse med ``prediker`` i ``app/prediksjon/`` må stå i ``PREDIKTORER``, og
    omvendt. En ny modul (f.eks. E2s ``modell.py``) som ikke legges til, feiler her.
    """
    assert _prediktorklasser() == set(PREDIKTORER)
    assert {BaselinePrediktor, NaivPrediktor} <= set(PREDIKTORER)


@pytest.mark.parametrize(
    "sti", _prediktormoduler(), ids=lambda p: str(p.relative_to(PREDIKSJON_DIR))
)
def test_prediktormodul_leser_ikke_datalaget(sti):
    assert _forbudte_referanser(sti.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("kilde", [
    "import app.data",
    "from app.data import Anlop",
    "from app import data",
    "from ..data import last_utdrag",
    "from .. import data",
    "p = 'data/utdrag/anlop.csv'",
    "last_utdrag()",
])
def test_ast_sjekken_fanger_juks(kilde):
    assert _forbudte_referanser(kilde)


# --- Metrikkmodulen (E1-S05) ---------------------------------------------------------


# Det eneste metrikker.py får importere fra app: typene den scorer.
METRIKK_TILLATT = {("app.data", "Anlop"), ("app.prediksjon", "Prediksjon")}


def _metrikk_brudd(kilde: str):
    """``metrikker.py`` scorer prediksjoner; den lager dem aldri selv.

    Importer: standardbiblioteket, ``Anlop`` fra ``app.data`` og ``Prediksjon`` fra
    ``app.prediksjon``. Alt annet fra ``app`` (prediktorer, ``velg_prediktor``) og
    relative importer er forbudt. Forbudt er også referanse til ``baseline.json`` og
    navn som viser at den regner ``eta − offset`` selv (``offset``, ``eta_reported``).
    """
    feil = []
    for node in ast.walk(ast.parse(kilde)):
        if isinstance(node, ast.Import):
            feil += [a.name for a in node.names
                     if a.name == "app" or a.name.startswith("app.")]
        elif isinstance(node, ast.ImportFrom):
            modul = node.module or ""
            if node.level:
                feil.append(f"relativ import: {modul!r}")
            elif modul == "app" or modul.startswith("app."):
                feil += [f"from {modul} import {a.name}" for a in node.names
                         if (modul, a.name) not in METRIKK_TILLATT]
        tekst = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            tekst = node.value
        elif isinstance(node, ast.Name):
            tekst = node.id
        elif isinstance(node, ast.Attribute):
            tekst = node.attr
        elif isinstance(node, ast.arg):
            tekst = node.arg
        if tekst:
            liten = tekst.lower()
            if "baseline.json" in liten:
                feil.append(f"refererer baseline.json: {tekst!r}")
            if "offset" in liten or liten == "eta_reported":
                feil.append(f"regner prediksjon selv: {tekst!r}")
    return feil


def test_metrikker_lager_ikke_prediksjoner():
    assert _metrikk_brudd(METRIKKER.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("kilde", [
    "import app.prediksjon.baseline",
    "from app.prediksjon.baseline import BaselinePrediktor",
    "from app.prediksjon import baseline",
    "from app.prediksjon import velg_prediktor",
    "from app.prediksjon.naiv import NaivPrediktor",
    "from app.prediksjon import Prediksjon, lag_input",
    "import app.prediksjon",
    "from .prediksjon import Prediksjon",
    "p = 'data/baseline.json'",
    "x = a.eta_reported - dt.timedelta(minutes=64.2)",
    "x = OFFSET_MINUTTER['Øvrige']",
])
def test_metrikk_ast_sjekken_fanger_juks(kilde):
    assert _metrikk_brudd(kilde)


def test_metrikk_ast_sjekken_tillater_typene():
    assert _metrikk_brudd(
        "import datetime as dt\nfrom collections import Counter\n"
        "from app.data import Anlop\nfrom app.prediksjon import Prediksjon\n"
    ) == []
