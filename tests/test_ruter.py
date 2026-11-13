"""Hovedskjermen `GET /` (E1-S06, UX §2 skjerm A, §5 tomt vindu; E2-S08 modellen i dashbordet).

Testene for baselineverdiene låser ``PREDIKTOR=baseline`` (autouse-fixturen under). Modellrader rendres bare
for ``VALIDERING_NAA`` i valideringsdelen, aldri for et vindu i testperioden (regelen om testrader, E2-S08).
"""
import dataclasses
import datetime as dt
import json
import re

import pytest
from conftest import VALIDERING_NAA, anlopslista, parse_html, syntetisk_blokk

import app.prediksjon as prediksjon
import app.prediksjon.modell as modellmodul
from app import DELEGERT_TEKST, STANDARD_NAA, create_app
from app.data import anlop_i_vindu
from app.prediksjon import MERKNAD_IKKE_FUNNET, MERKNAD_LAAST, lag_input, velg_prediktor
from app.prediksjon.baseline import BaselinePrediktor
from app.prediksjon.modell import ModellPrediktor
from app.visning import OSLO, ukedag_dato_klokke, ukedag_klokke

KOLONNER = ["Skip", "Gruppe", "Rapportert", "Predikert", "Horisont", "Varsel"]
HJELPETEKST = "predikert før valgt tidspunkt"
TOM_MELDING = "Ingen anløp med rapportert ETA i dette vinduet. Prøv et annet tidspunkt."


@pytest.fixture(autouse=True)
def _baseline(monkeypatch):
    """Baselineforventningene gjelder ``PREDIKTOR=baseline``. Modelltestene setter verdien selv."""
    monkeypatch.setenv("PREDIKTOR", "baseline")


def _ren(t):
    return re.sub(r"\s+", " ", t).strip()


def _rader(dokument):
    """Rader som {kolonne: celle-node}."""
    tbody = anlopslista(dokument).finn_alle("tbody")[0]
    rader = []
    for tr in tbody.finn_alle("tr"):
        tder = tr.finn_alle("td")
        rader.append({td.attrs["data-label"]: td for td in tder})
    return rader


def test_standardvindu(dokument):
    h2 = _ren(anlopslista(dokument).finn_alle("h2")[0].tekst())
    assert h2 == "15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)"

    ths = [_ren(th.tekst()) for th in anlopslista(dokument).finn_alle("th")]
    assert ths == KOLONNER

    rader = _rader(dokument)
    assert len(rader) == 15
    skip = [_ren(r["Skip"].tekst()) for r in rader]
    assert skip[0] == "ROTTERDAM"
    assert skip[-1] == "MSC POESIA"

    etter_navn = {_ren(r["Skip"].tekst()): r for r in rader}
    # Avrunding til nærmeste minutt: 09:55:48 → 09:56 (E0-S18).
    be = etter_navn["BERGEN ENERGY"]
    assert _ren(be["Predikert"].tekst()) == "ons 09:56"
    assert _ren(be["Rapportert"].tekst()) == "ons 11:00"
    assert _ren(be["Gruppe"].tekst()) == "Tank"
    # Horisont fra rapportert ETA − nå.
    assert _ren(be["Horisont"].tekst()) == "≤ 6 t"
    assert _ren(etter_navn["THUN EVOLVE"]["Horisont"].tekst()) == "6–24 t"


def test_sortert_etter_uavrundet_predikert(dokument):
    """Rekkefølgen er predikert ankomst, ikke rapportert ETA.

    NORDNORGE (rapportert 14:45) kommer etter BERGEN TANK (rapportert 15:00),
    fordi Passasjer har mindre offset.
    """
    skip = [_ren(r["Skip"].tekst()) for r in _rader(dokument)]
    assert skip == [
        "ROTTERDAM", "EINARSON", "TROLLFJORD", "BERGEN ENERGY", "VASCO DA GAMA",
        "ELEKTRON", "STAVANGERFJORD", "OCEAN RESPONSE", "ELDJARN", "THUN EVOLVE",
        "BERGEN TANK", "NORDNORGE", "G O SARS", "SIEM PEARL", "MSC POESIA",
    ]


def test_predikert_for_naa_merkes(dokument):
    merket = []
    for r in _rader(dokument):
        celle = r["Predikert"]
        tekst = _ren(celle.tekst())
        if HJELPETEKST in tekst:
            assert "*" in tekst
            merket.append(_ren(r["Skip"].tekst()))
        else:
            assert "*" not in tekst
    assert merket == ["ROTTERDAM", "EINARSON"]
    rader = {_ren(r["Skip"].tekst()): r for r in _rader(dokument)}
    assert _ren(rader["ROTTERDAM"]["Predikert"].tekst()).startswith("ons 07:15*")
    assert _ren(rader["EINARSON"]["Predikert"].tekst()).startswith("ons 07:56*")


def test_varselkolonnen_forklarer_seg(dokument):
    """Synlig «–», og en tekst skjermlesere får (UU4, FR3)."""
    for r in _rader(dokument):
        celle = r["Varsel"]
        synlige = [c for c in celle.iter() if c.attrs.get("aria-hidden") == "true"]
        assert [_ren(c.tekst()) for c in synlige] == ["–"]
        lest = _ren(celle.skjermlesertekst())
        assert "baselinen varsler ikke" in lest


def test_prediktor_stripa(dokument):
    stripe = [s for s in dokument.finn_alle("section")
              if "prediktor" in s.attrs.get("class", "").split()][0]
    tekst = _ren(stripe.tekst())
    assert "Kalibrert baseline" in tekst
    assert "Baselinen kan ikke varsle avvik. Varselkolonnen fylles når modellen kommer." in tekst
    assert "I testperioden var det under halvparten av de forsinkede anløpene." in tekst
    assert "rapportert ETA justert med median liggetid" in tekst
    # «ankomstsone» er gruppens interne begrep; på skjermen står «havneområdet» (E2-S08, beslutning 3).
    assert "utenfor havneområdet med AIS-posisjon ved kuttet" in tekst
    assert "ankomstsone" not in tekst


def test_norsk_tid_staar_paa_skjermen(dokument):
    assert "(norsk tid)" in _ren(dokument.tekst())


def test_tomt_vindu(tomt_dokument):
    h2 = _ren(anlopslista(tomt_dokument).finn_alle("h2")[0].tekst())
    assert h2 == "0 anløp · tir 03.02 08:00 – ons 04.02 08:00 (norsk tid)"
    assert TOM_MELDING in _ren(tomt_dokument.tekst())
    assert anlopslista(tomt_dokument).finn_alle("table") == []


def test_vindu_over_sommertid():
    """Vinduet krysser overgangen til vintertid natt til 26.10.2025: 24 t etter
    lør 08:00 (+02) er søn 07:00 (+01)."""
    naa = dt.datetime(2025, 10, 25, 8, 0, tzinfo=STANDARD_NAA.tzinfo)
    klient = create_app({"TESTING": True, "STANDARD_NAA": naa}).test_client()
    svar = klient.get("/")
    assert svar.status_code == 200
    dokument = parse_html(svar.get_data(as_text=True))
    h2 = _ren(anlopslista(dokument).finn_alle("h2")[0].tekst())
    assert h2.endswith("søn 26.10 07:00 (norsk tid)")
    antall = len(anlop_i_vindu(naa))
    assert h2.startswith(f"{antall} anløp")
    tbody = anlopslista(dokument).finn_alle("tbody")
    assert len(tbody[0].finn_alle("tr") if tbody else []) == antall


def test_ingen_fasit_i_html(client):
    """Ingen faktisk ankomst lekker ut (fasit av, FR4)."""
    html = client.get("/").get_data(as_text=True)
    for ord_ in ("faktisk_ankomst", "status_in_area", "Faktisk", "fasit"):
        assert ord_ not in html

    anlop = anlop_i_vindu(STANDARD_NAA)
    fasit = [a.faktisk_ankomst for a in anlop if a.faktisk_ankomst is not None]
    assert len(fasit) == 15
    for t in fasit:
        assert t.isoformat() not in html
        assert t.astimezone(STANDARD_NAA.tzinfo).isoformat() not in html
        assert t.astimezone(STANDARD_NAA.tzinfo).strftime("%H:%M:%S") not in html
        assert ukedag_dato_klokke(t) not in html

    # Hver «ukedag HH:MM» i HTML-en er en rapportert eller predikert tid. Da kan en
    # fasit-tid bare stå der hvis den tilfeldigvis er lik en av dem.
    lovlige = {ukedag_klokke(a.eta_reported) for a in anlop} | _predikerte_tider()
    vist = set(re.findall(r"(?:man|tir|ons|tor|fre|lør|søn) \d\d:\d\d", html))
    assert vist <= lovlige
    lekker = {ukedag_klokke(t) for t in fasit} - lovlige
    assert lekker, "testen må ha fasit-tider som skiller seg fra de viste"
    assert not (vist & lekker)


def _predikerte_tider():
    anlop = anlop_i_vindu(STANDARD_NAA)
    p = velg_prediktor().prediker([lag_input(a, STANDARD_NAA) for a in anlop], STANDARD_NAA)
    return {ukedag_klokke(x.predikert_ankomst) for x in p}


def test_standard_naa_er_oslo_0800():
    assert STANDARD_NAA.utcoffset() == dt.timedelta(hours=2)
    assert (STANDARD_NAA.year, STANDARD_NAA.month, STANDARD_NAA.day, STANDARD_NAA.hour) == (
        2025, 10, 8, 8)


# ---------------------------------------------------------------------------
# E2-S08: modellen i dashbordet. Modellrader bare i valideringsvinduet.

I_UTVALG = ("Modellen er trent på disse anløpene, så treffene ser bedre ut enn de er. "
            "Ekte resultater finnes først for testperioden.")
TRENING_NAA = dt.datetime(2024, 6, 15, 8, 0, tzinfo=OSLO)
MODELL_STRIPE = "Modellen varsler bare for anløp utenfor havneområdet med AIS-posisjon ved kuttet."
BASELINE_STRIPE = "Baselinen kan ikke varsle avvik. Varselkolonnen fylles når modellen kommer."


def _side(naa):
    svar = create_app({"TESTING": True, "STANDARD_NAA": naa}).test_client().get("/")
    assert svar.status_code == 200
    return parse_html(svar.get_data(as_text=True))


def _synlig(celle):
    """Synlig tekst: uten ``visually-hidden``."""
    def tekst(n):
        if "visually-hidden" in n.attrs.get("class", "").split():
            return ""
        return "".join(c if isinstance(c, str) else tekst(c) for c in n.children)
    return _ren(tekst(celle))


def _stripe(dokument):
    return _ren([s for s in dokument.finn_alle("section")
                 if "prediktor" in s.attrs.get("class", "").split()][0].tekst())


def _testkjoringer(monkeypatch, tmp_path, antall):
    sti = tmp_path / "metrikker.json"
    sti.write_text(json.dumps({"testkjoringer": antall}), encoding="utf-8")
    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", sti)


def _valideringsprediksjoner():
    """Modellens prediksjoner for valideringsvinduet, per skipsnavn (bare valideringsrader)."""
    naa = VALIDERING_NAA
    assert naa.astimezone(dt.timezone.utc) + dt.timedelta(hours=24) <= prediksjon.testperiode_start()
    inputs = [lag_input(a, naa) for a in anlop_i_vindu(naa)]
    return {i.shipname: p for i, p in zip(inputs, ModellPrediktor().prediker(inputs, naa))}


def test_valideringsvinduet_er_foer_testperioden():
    assert prediksjon.testperiode_start() == dt.datetime(2025, 9, 14, 3, 15, tzinfo=dt.timezone.utc)
    assert VALIDERING_NAA + dt.timedelta(hours=24) < prediksjon.testperiode_start()
    assert all(a.split == "train" for a in anlop_i_vindu(VALIDERING_NAA))


def test_auto_foer_testkjoringen_gir_baseline(monkeypatch):
    monkeypatch.setenv("PREDIKTOR", "auto")
    stripe = _stripe(_side(VALIDERING_NAA))
    assert "Kalibrert baseline" in stripe
    assert BASELINE_STRIPE in stripe
    assert MERKNAD_LAAST not in stripe and MERKNAD_IKKE_FUNNET not in stripe


def test_modell_i_valideringsvindu(monkeypatch):
    monkeypatch.setenv("PREDIKTOR", "modell")
    dokument = _side(VALIDERING_NAA)
    stripe = _stripe(dokument)
    assert "Modell v1" in stripe
    assert MODELL_STRIPE in stripe
    assert "57 av 194 ved 6 t og 78 av 194 ved 24 t" in stripe
    assert BASELINE_STRIPE not in stripe
    assert MERKNAD_LAAST not in stripe and MERKNAD_IKKE_FUNNET not in stripe

    pred = _valideringsprediksjoner()
    rader = {_ren(r["Skip"].tekst()): r for r in _rader(dokument)}
    assert set(rader) == set(pred)
    for skip, r in rader.items():
        assert _ren(r["Predikert"].tekst()).startswith(ukedag_klokke(pred[skip].predikert_ankomst))
    # Sortert på modellens uavrundede predikerte ankomst.
    skip = [_ren(r["Skip"].tekst()) for r in _rader(dokument)]
    assert skip == sorted(skip, key=lambda s: pred[s].predikert_ankomst)


def test_varselkolonnen_med_modellen(monkeypatch):
    """▲ + «VARSEL» (ikon og tekst, UU3), «–» med skjermlesertekst, og synlig grunn for delegerte rader."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    dokument = _side(VALIDERING_NAA)
    pred = _valideringsprediksjoner()
    grunner = {
        "passasjer": "– (rutegående: bare baseline)",
        "ingen_tilstand": "– (ingen AIS-tilstand)",
        "i_sonen_ved_kutt": "– (allerede i havneområdet)",
    }
    sett = set()
    for r in _rader(dokument):
        p = pred[_ren(r["Skip"].tekst())]
        celle = r["Varsel"]
        synlig, lest = _synlig(celle), _ren(celle.skjermlesertekst())
        skjult = [_ren(c.tekst()) for c in celle.iter() if c.attrs.get("aria-hidden") == "true"]
        if p.forventet_forsinket is True:
            assert synlig == "▲ VARSEL"
            assert skjult == ["▲"]
            assert lest == "VARSEL"
            assert "varsel-merke" in celle.finn_alle("span")[0].attrs["class"]
            sett.add("varsel")
        elif p.forventet_forsinket is False:
            assert skjult == ["–"]
            assert lest == "Ingen varsel"
            sett.add("ingen")
        else:
            assert synlig == grunner[p.forklaring["delegert"]]
            assert skjult == ["–"]
            assert lest == "Ingen varsel: " + grunner[p.forklaring["delegert"]][2:]
            sett.add(p.forklaring["delegert"])
        assert "baselinen varsler ikke" not in lest
    assert sett == {"varsel", "ingen", "passasjer", "ingen_tilstand", "i_sonen_ved_kutt"}
    liste = anlopslista(dokument)
    fotnote = _ren(liste.finn_alle("p")[-1].tekst())  # panelet (E2-S09) står etter lista
    assert "▲ VARSEL" in fotnote and "baselinen varsler ikke" not in fotnote


def test_varsel_ingen_featurerad(monkeypatch):
    """Uten featurerad ved kuttet står «– (ingen modelldata ved kuttet)»."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    pred = _valideringsprediksjoner()
    maal = next(s for s, p in pred.items() if p.forklaring.get("metode") == "modell")
    ekte = modellmodul.featurer_ved_kutt
    monkeypatch.setattr(modellmodul, "featurer_ved_kutt",
                        lambda inp: None if inp.shipname == maal else ekte(inp))
    rader = {_ren(r["Skip"].tekst()): r for r in _rader(_side(VALIDERING_NAA))}
    assert _synlig(rader[maal]["Varsel"]) == "– (ingen modelldata ved kuttet)"


def test_varsel_ukjent_delegering(monkeypatch):
    """En delegert rad uten kjent kode får «– (ingen modellvurdering)», ikke «Ingen varsel»."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    ekte = ModellPrediktor.prediker

    def uten_kode(self, inputs, naa):
        return [dataclasses.replace(p, forventet_forsinket=None, forklaring={"metode": "kalibrert_baseline"})
                for p in ekte(self, inputs, naa)]

    monkeypatch.setattr(ModellPrediktor, "prediker", uten_kode)
    for r in _rader(_side(VALIDERING_NAA)):
        assert _synlig(r["Varsel"]) == "– (ingen modellvurdering)"
        assert _ren(r["Varsel"].skjermlesertekst()) == "Ingen varsel: (ingen modellvurdering)"


def test_delegert_tekst_dekker_kodene():
    """Nøklene i ``DELEGERT_TEKST`` er nøyaktig kodene ``ModellPrediktor`` kan gi (``app/prediksjon/modell.py``)."""
    import inspect

    kilde = inspect.getsource(modellmodul)
    koder = set(re.findall(r'grunn = "([a-z_]+)"', kilde))
    assert koder == {"passasjer", "ingen_tilstand", "i_sonen_ved_kutt", "ingen_featurerad"}
    assert set(DELEGERT_TEKST) == koder


def test_modell_endrer_bare_stripa_og_varselcellen(monkeypatch):
    """A5: samme kolonner, anløp og celler som baselinen, utenom Predikert (tiden), Varsel og stripa."""
    base = _side(VALIDERING_NAA)
    monkeypatch.setenv("PREDIKTOR", "modell")
    modell = _side(VALIDERING_NAA)
    assert [_ren(th.tekst()) for th in anlopslista(base).finn_alle("th")] == [
        _ren(th.tekst()) for th in anlopslista(modell).finn_alle("th")]
    assert _ren(anlopslista(base).finn_alle("h2")[0].tekst()) == _ren(anlopslista(modell).finn_alle("h2")[0].tekst())
    assert _ren(base.finn_alle("h1")[0].tekst()) == _ren(modell.finn_alle("h1")[0].tekst())

    def celler(d):
        return {_ren(r["Skip"].tekst()): {k: _ren(v.tekst()) for k, v in r.items()
                                          if k in ("Skip", "Gruppe", "Rapportert", "Horisont")}
                for r in _rader(d)}

    assert celler(base) == celler(modell)


def test_laasen_alene_stopper_modellen_paa_testvindu(monkeypatch):
    """Låsen og vakten mot testrader er to sperrer som skal holde hver for seg (E2-S08, beslutning 6).

    Vakten fra ``conftest.py`` er her byttet ut med en spion som aldri kjører den ekte modellen. Testen viser at
    låsen alene gir baselinen for standardvinduet (testperioden): ``ModellPrediktor`` blir verken valgt eller kalt.
    Bryter låsen, feiler testen uten at modellen har predikert noe på testradene.
    """
    kall = []

    def spion(self, inputs, naa):
        kall.append(len(inputs))
        raise AssertionError("ModellPrediktor.prediker kalt for et testvindu: låsen holdt ikke")

    monkeypatch.setattr(ModellPrediktor, "prediker", spion)
    monkeypatch.setenv("PREDIKTOR", "modell")
    assert prediksjon.testkjoringer() == 0
    prediktor, merknad = prediksjon.velg_prediktor_med_merknad(naa=STANDARD_NAA)
    assert isinstance(prediktor, BaselinePrediktor) and merknad == MERKNAD_LAAST
    svar = create_app({"TESTING": True, "STANDARD_NAA": STANDARD_NAA}).test_client().get("/")
    assert svar.status_code == 200
    assert kall == []
    assert MERKNAD_LAAST in _stripe(parse_html(svar.get_data(as_text=True)))


def test_laas_testperioden_standardvindu(monkeypatch):
    """Før testkjøringen gir ``PREDIKTOR=modell`` baselinen og låseteksten i standardvinduet."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    assert prediksjon.testkjoringer() == 0
    dokument = _side(STANDARD_NAA)
    stripe = _stripe(dokument)
    assert "Kalibrert baseline" in stripe and "Modell v1" not in stripe
    assert MERKNAD_LAAST in stripe
    assert BASELINE_STRIPE in stripe
    for r in _rader(dokument):
        assert "baselinen varsler ikke" in _ren(r["Varsel"].skjermlesertekst())


def test_laas_testperioden_vindu_over_grensen(monkeypatch):
    """Et vindu som starter i valideringsdelen og slutter i testperioden, er låst."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    naa = dt.datetime(2025, 9, 13, 8, 0, tzinfo=OSLO)
    assert naa < prediksjon.testperiode_start() < naa + dt.timedelta(hours=24)
    stripe = _stripe(_side(naa))
    assert "Kalibrert baseline" in stripe
    assert MERKNAD_LAAST in stripe


def test_laas_grensen_er_vinduets_slutt(monkeypatch):
    start = prediksjon.testperiode_start()
    paa_grensen = start - dt.timedelta(hours=24)
    assert isinstance(velg_prediktor("modell", paa_grensen), ModellPrediktor)
    assert isinstance(velg_prediktor("modell", paa_grensen + dt.timedelta(seconds=1)), BaselinePrediktor)
    assert isinstance(velg_prediktor("modell", None), BaselinePrediktor)
    assert prediksjon.velg_prediktor_med_merknad("modell", None)[1] == MERKNAD_LAAST
    for verdi in ("auto", "baseline"):
        assert isinstance(velg_prediktor(verdi, paa_grensen), BaselinePrediktor)


@pytest.mark.parametrize("innhold", [None, "{}", '{"testkjoringer": 0}', "ikke json",
                                     '{"testkjoringer": true}', "[]"])
def test_laas_uten_testkjoring(monkeypatch, tmp_path, innhold):
    """Manglende fil eller nøkkel teller som 0 testkjøringer."""
    sti = tmp_path / "metrikker.json"
    if innhold is not None:
        sti.write_text(innhold, encoding="utf-8")
    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", sti)
    assert prediksjon.testkjoringer() == 0
    assert isinstance(velg_prediktor("auto", VALIDERING_NAA), BaselinePrediktor)
    assert isinstance(velg_prediktor("modell", STANDARD_NAA), BaselinePrediktor)


@pytest.mark.parametrize("verdi", ["auto", "modell"])
def test_etter_testkjoringen_gir_modellen(monkeypatch, tmp_path, verdi):
    """Etter testkjøringen velges modellen for alle vinduer. Bare valget sjekkes for testvinduet; modellrader
    rendres bare i valideringsvinduet."""
    _testkjoringer(monkeypatch, tmp_path, 1)
    for naa in (None, STANDARD_NAA, VALIDERING_NAA):
        prediktor, merknad = prediksjon.velg_prediktor_med_merknad(verdi, naa)
        assert isinstance(prediktor, ModellPrediktor) and merknad is None
    monkeypatch.setenv("PREDIKTOR", verdi)
    stripe = _stripe(_side(VALIDERING_NAA))
    assert "Modell v1" in stripe and MODELL_STRIPE in stripe


def test_eksplisitt_baseline_etter_testkjoringen(monkeypatch, tmp_path):
    _testkjoringer(monkeypatch, tmp_path, 1)
    assert isinstance(velg_prediktor("baseline", VALIDERING_NAA), BaselinePrediktor)
    stripe = _stripe(_side(VALIDERING_NAA))
    assert "Kalibrert baseline" in stripe and BASELINE_STRIPE in stripe


def test_fallback_baseline(monkeypatch, tmp_path):
    """Tom modellmappe: baselinen og «Modell ikke funnet — viser kalibrert baseline» (UX §5)."""
    monkeypatch.setattr(prediksjon, "MODELL_DIR", tmp_path)
    monkeypatch.setenv("PREDIKTOR", "modell")
    prediktor, merknad = prediksjon.velg_prediktor_med_merknad(naa=VALIDERING_NAA)
    assert isinstance(prediktor, BaselinePrediktor) and merknad == MERKNAD_IKKE_FUNNET
    dokument = _side(VALIDERING_NAA)
    stripe = _stripe(dokument)
    assert "Kalibrert baseline" in stripe
    assert "Modell ikke funnet — viser kalibrert baseline" in stripe
    assert BASELINE_STRIPE in stripe
    for r in _rader(dokument):
        assert "baselinen varsler ikke" in _ren(r["Varsel"].skjermlesertekst())


def test_fallback_baseline_etter_testkjoringen(monkeypatch, tmp_path):
    _testkjoringer(monkeypatch, tmp_path, 1)
    tom = tmp_path / "tom"
    tom.mkdir()
    monkeypatch.setattr(prediksjon, "MODELL_DIR", tom)
    for verdi in ("auto", "modell"):
        prediktor, merknad = prediksjon.velg_prediktor_med_merknad(verdi, STANDARD_NAA)
        assert isinstance(prediktor, BaselinePrediktor) and merknad == MERKNAD_IKKE_FUNNET


def test_ukjent_prediktor_gir_valueerror(monkeypatch):
    monkeypatch.setenv("PREDIKTOR", "tull")
    with pytest.raises(ValueError):
        velg_prediktor(naa=VALIDERING_NAA)


@pytest.mark.parametrize("naa", [TRENING_NAA, VALIDERING_NAA], ids=["trening", "validering"])
def test_modell_foer_testperioden_sier_i_utvalg(monkeypatch, naa):
    """Beslutning 1 (rettelse) og 5: trening- og valideringsvinduer viser modellen med teksten om at den er trent
    på anløpene."""
    monkeypatch.setenv("PREDIKTOR", "modell")
    assert all(a.split == "train" for a in anlop_i_vindu(naa))
    stripe = _stripe(_side(naa))
    assert "Modell v1" in stripe and I_UTVALG in stripe


def test_i_utvalg_ikke_med_baselinen(monkeypatch):
    stripe = _stripe(_side(VALIDERING_NAA))
    assert "Kalibrert baseline" in stripe and I_UTVALG not in stripe


def test_i_utvalg_ikke_for_testvindu_etter_testkjoringen(monkeypatch, tmp_path):
    """Etter testkjøringen vises ikke teksten for testvinduer. Bare stripa sjekkes; modellen kjøres ikke på
    testradene (vinduet er tomt, TOMT_NAA i testperioden)."""
    from conftest import TOMT_NAA

    _testkjoringer(monkeypatch, tmp_path, 1)
    monkeypatch.setenv("PREDIKTOR", "modell")
    assert anlop_i_vindu(TOMT_NAA) == []
    stripe = _stripe(_side(TOMT_NAA))
    assert "Modell v1" in stripe and I_UTVALG not in stripe


@pytest.mark.parametrize("feil", [ValueError("min() arg is an empty sequence"), OSError("utdraget kan ikke leses")])
def test_testperiode_start_feiler_gir_laast(monkeypatch, feil):
    """Kan ikke testperiodens start leses (ingen testrader, eller uleselig utdrag), er vinduet låst, og siden svarer
    likevel 200."""
    def feiler():
        raise feil

    monkeypatch.setattr(prediksjon, "testperiode_start", feiler)
    assert prediksjon.i_testperioden(VALIDERING_NAA) is True
    monkeypatch.setenv("PREDIKTOR", "modell")
    stripe = _stripe(_side(VALIDERING_NAA))
    assert "Kalibrert baseline" in stripe and MERKNAD_LAAST in stripe


def test_fallback_korrupt_artefakt(monkeypatch, tmp_path):
    """Et korrupt ``.joblib`` gir baselinen og «Modell ikke funnet», ikke HTTP 500."""
    for h in (6, 24):
        (tmp_path / f"modell_{h}t.joblib").write_bytes(b"ikke en joblib-fil")
    monkeypatch.setattr(prediksjon, "MODELL_DIR", tmp_path)
    monkeypatch.setenv("PREDIKTOR", "modell")
    prediktor, merknad = prediksjon.velg_prediktor_med_merknad(naa=VALIDERING_NAA)
    assert isinstance(prediktor, BaselinePrediktor) and merknad == MERKNAD_IKKE_FUNNET
    assert MERKNAD_IKKE_FUNNET in _stripe(_side(VALIDERING_NAA))


def test_vakta_stopper_modellen_paa_testrader():
    """Autouse-vakta i conftest stopper modellen før den kjøres på en testrad."""
    anlop = anlop_i_vindu(STANDARD_NAA)
    with pytest.raises(AssertionError, match="testrad"):
        ModellPrediktor().prediker([lag_input(anlop[0], STANDARD_NAA)], STANDARD_NAA)


# ---------------------------------------------------------------------------
# E2-S09: panelet «modell mot baseline». Det leser bare metrikker.json. Visningen etter testkjøringen testes bare
# med syntetiske filer i tmp_path (regelen om testrader). PREDIKTOR=baseline (autouse over) gjelder også her.

# Den ekte fila leses gjennom ``valideringsvisning`` (conftest, E2-S10 beslutning 1A), så testene er like før og etter
# testkjøringen.


def _metrikker(monkeypatch, sti):
    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", sti)


def _syntetisk(monkeypatch, tmp_path, data):
    sti = tmp_path / "metrikker.json"
    sti.write_text(json.dumps(data), encoding="utf-8")
    _metrikker(monkeypatch, sti)


def _panel(dokument):
    return [n for n in dokument.iter() if n.attrs.get("id") == "treffsikkerhet"][0]


def _forside():
    svar = create_app({"TESTING": True}).test_client().get("/")
    assert svar.status_code == 200
    return parse_html(svar.get_data(as_text=True))


def _pst(x):
    return f"{x * 100:.1f}".replace(".", ",") + " %"


def _brok(a, b):
    return f"{a}/{b}"


def _forventet_varsel(v):
    if v["presisjon"] is None:
        return ["kan ikke varsle"] * 3
    return [f"{_pst(v['presisjon'])} ({_brok(v['treff'], v['varsler'])})",
            f"{_pst(v['recall'])} ({_brok(v['treff'], v['forsinket'])})",
            f"{v['f1']:.2f}".replace(".", ",")]


def _forventet_tabell(radsett, armer):
    """{mål: [celletekst per arm]} regnet rett fra fila, uavhengig av app/panel.py."""
    rader = {"Innenfor ±30 min": [], "Presisjon": [], "Recall": [], "F1": []}
    for arm in armer:
        if arm == "varsle_alle":
            v = radsett[arm]
            rader["Innenfor ±30 min"].append("ikke aktuelt")
        else:
            a = radsett[arm]
            v = a["varsel"]
            rader["Innenfor ±30 min"].append(f"{_pst(a['andel_30'])} ({_brok(a['treff_30'], a['n'])})")
        for maal, tekst in zip(("Presisjon", "Recall", "F1"), _forventet_varsel(v)):
            rader[maal].append(tekst)
    return rader


def _tabell(table):
    """{mål: [celletekst]} som skjermleseren får den (– er skjult, «ikke aktuelt» leses)."""
    ut = {}
    for tr in table.finn_alle("tbody")[0].finn_alle("tr"):
        th = tr.finn_alle("th")[0]
        ut[_ren(th.tekst())] = [_ren(td.skjermlesertekst()).replace("\u00a0", " ") for td in tr.finn_alle("td")]
    return ut


def _pst_og_f1_i_blokk(blokk):
    """Alle andeler (som «x,y %») og F1-verdier (som «0,xx») en blokk har, lest rett fra fila."""
    tekster = set()

    def gaa(d):
        if isinstance(d, dict):
            for k, x in d.items():
                if isinstance(x, float) and k in ("andel_30", "presisjon", "recall", "med_fasit", "alle_rader"):
                    tekster.add(_pst(x))
                elif isinstance(x, float) and k == "f1":
                    tekster.add(f"{x:.2f}".replace(".", ","))
                gaa(x)
    gaa(blokk)
    return tekster


def _alle_tall_i_blokk(blokk):
    """Alle andeler og brøker en blokk kan gi på skjermen, som visningstekst."""
    tall = set()

    def gaa(d):
        if isinstance(d, dict):
            if "andel_30" in d:
                tall.add(_brok(d["treff_30"], d["n"]))
            if "presisjon" in d and d["presisjon"] is not None:
                tall.update({_brok(d["treff"], d["varsler"]), _brok(d["treff"], d["forsinket"])})
            for v in d.values():
                gaa(v)
    gaa(blokk)
    return tall


def _forventet_differanse(a, b, skala, desimaler, enhet, subjekt="modellen"):
    """Forventet differanselinje for den ekte fila (ingen grensetilfeller der: ingen er like eller runder til 0)."""
    d = (a - b) * skala
    assert d != 0 and round(abs(d), desimaler) != 0
    tegn, ord_ = ("+", f"{subjekt} bedre") if d > 0 else ("−", f"{subjekt} dårligere")
    return f"{tegn}{abs(d):.{desimaler}f}".replace(".", ",") + f"{enhet} ({ord_})"


def test_panel_modell_mot_baseline(monkeypatch, valideringsvisning):
    """Med den ekte metrikker.json sett før testkjøringen (beslutning 1A i E2-S10): valideringsblokken, og hvert tall
    i panelet er filas verdi etter avrunding."""
    data = json.loads(valideringsvisning.read_text(encoding="utf-8"))
    assert data["testkjoringer"] == 0 and "test" not in data
    _metrikker(monkeypatch, valideringsvisning)
    panel = _panel(_forside())
    tekst = _ren(panel.tekst()).replace("\u00a0", " ")
    v = data["validering"]

    assert "Validering (mai–sep 2025) — utviklingstall, ikke testresultat" in tekst
    assert f"{v['antall_anlop']:,}".replace(",", " ") + " anløp i perioden" in tekst
    assert "Tall mangler" not in tekst
    assert panel.finn_alle("ul") == [] and " bestått (" not in tekst  # ingen dom før testkjøringen

    h3 = [_ren(n.tekst()) for n in panel.finn_alle("h3")]
    assert h3 == ["Horisont 6 t", "Horisont 24 t"]
    tabeller = panel.finn_alle("table")
    assert len(tabeller) == 6
    grupper = [n for n in panel.iter() if "panel-gruppe" in n.attrs.get("class", "").split()]
    assert len(grupper) == 6 and all(len(g.finn_alle("table")) == 1 for g in grupper)
    # Faste ankre fra den ekte fila: modellen vinner ±30 min på modellutvalget, og systemet (modell + baseline for
    # resten) taper F1 mot «varsle alle» på all Øvrige-trafikk ved 6 t. Den raden sier «systemet», aldri «modellen».
    assert "Modell − baseline, innenfor ±30 min: +12,2 pp (modellen bedre)" in tekst
    assert "Systemet − «varsle alle», varsel-F1: −0,35 (systemet dårligere)" in tekst
    assert "Modell − «varsle alle», varsel-F1: −0,35" not in tekst
    for i, h in enumerate(("6", "24")):
        hv = v["horisonter"][h]
        o, p = hv["antall"]["ovrige"], hv["antall"]["passasjer"]
        assert f"Med fasit: Øvrige {o['med_fasit']} av {o['rader']}, Passasjer {p['med_fasit']} av {p['rader']}." in tekst
        assert (f"Modellandel av Øvrige med fasit: {_pst(hv['andel_modellutvalg']['med_fasit'])} "
                f"({_brok(o['modellutvalg_med_fasit'], o['med_fasit'])})") in tekst
        forventet = [
            ("Øvrige, modellutvalget", _forventet_tabell(hv["ovrige_modellutvalg"], ["modell", "baseline", "varsle_alle"])),
            ("Øvrige, alle (resten får baseline)", _forventet_tabell(hv["ovrige_alle"], ["modell", "baseline", "varsle_alle"])),
            ("Passasjer (rutegående, bare baseline)", _forventet_tabell(hv["passasjer"], ["baseline"])),
        ]
        for table, (caption, rader) in zip(tabeller[3 * i:3 * i + 3], forventet):
            assert _ren(table.finn_alle("caption")[0].tekst()) == caption
            assert _tabell(table) == rader
        # Differanselinjene står i gruppens egen blokk, med fortegn og ord fra den uavrundede differansen.
        for gruppe, radsett in zip(grupper[3 * i:3 * i + 3], ("ovrige_modellutvalg", "ovrige_alle", "passasjer")):
            linjer = [_ren(p_.tekst()).replace("\u00a0", " ") for p_ in gruppe.finn_alle("p")]
            if radsett == "passasjer":
                assert linjer == []
                continue
            m, b, alle = (hv[radsett][k] for k in ("modell", "baseline", "varsle_alle"))
            arm, subjekt = ("Systemet", "systemet") if radsett == "ovrige_alle" else ("Modell", "modellen")
            forventet_linjer = [
                f"{arm} − baseline, innenfor ±30 min: "
                + _forventet_differanse(m["andel_30"], b["andel_30"], 100, 1, " pp", subjekt),
                f"{arm} − «varsle alle», varsel-F1: "
                + _forventet_differanse(m["varsel"]["f1"], alle["f1"], 1, 2, "", subjekt),
            ]
            if radsett == "ovrige_alle":
                forventet_linjer.append(
                    "De fleste forsinkelsene i all trafikk er turer inne i havneområdet, der modellen ikke brukes og "
                    "baselinen ikke kan varsle. Modellutvalget er raden som viser modellen.")
            assert linjer == forventet_linjer
            kolonner = [_ren(th.tekst()) for th in gruppe.finn_alle("thead")[0].finn_alle("th")]
            assert kolonner == ["Mål", arm, "Baseline", "«Varsle alle»"]

    # Ingen verdi fra test_bare_baseline (eller ablasjonen) som ikke også står i valideringsblokken.
    vist = _alle_tall_i_blokk({k: x for k, x in v["horisonter"].items()})
    fremmede = _alle_tall_i_blokk(data["test_bare_baseline"]) - vist
    assert fremmede and not any(re.search(rf"\b{re.escape(b)}\b", tekst) for b in fremmede)
    fremmede_tall = _pst_og_f1_i_blokk(data["test_bare_baseline"]) - _pst_og_f1_i_blokk(v)
    assert fremmede_tall
    for t in fremmede_tall:
        assert not re.search(rf"(?<![\d,+−<]){re.escape(t)}(?!\d)", tekst), f"{t} fra test_bare_baseline i panelet"
    for h in ("6", "24"):
        for radsett in ("ovrige_modellutvalg", "ovrige_alle"):
            abl = v["horisonter"][h][radsett]["ablasjon_uten_f13_f14"]
            assert f"({_brok(abl['treff_30'], abl['n'])})" not in tekst


def test_panel_baseline_kan_ikke_varsle(monkeypatch, valideringsvisning):
    _metrikker(monkeypatch, valideringsvisning)
    for table in _panel(_forside()).finn_alle("table"):
        rader = _tabell(table)
        kolonner = [_ren(th.tekst()) for th in table.finn_alle("thead")[0].finn_alle("th")]
        b = kolonner.index("Baseline") - 1
        assert [rader[m][b] for m in ("Presisjon", "Recall", "F1")] == ["kan ikke varsle"] * 3
        assert all("0,0" not in rader[m][b] for m in rader)


def test_panel_etter_testkjoringen(monkeypatch, tmp_path):
    _syntetisk(monkeypatch, tmp_path, {"testkjoringer": 1, "validering": syntetisk_blokk(modell_treff=301),
                                       "test": syntetisk_blokk()})
    panel = _panel(_forside())
    tekst = _ren(panel.tekst()).replace("\u00a0", " ")
    assert "Testperioden (14.09.2025–15.03.2026)" in tekst
    assert "Validering" not in tekst and "301/400" not in tekst
    assert "avgjøres først på testperioden" not in tekst
    dommer = [_ren(li.tekst()).replace("\u00a0", " ") for li in panel.finn_alle("li")]
    assert dommer == [  # én dom per horisont, på modellutvalget; 24 t har egne tall
        "Innenfor ±30 min: bestått (modell 75,0 %, baseline 62,5 %)",
        "Varsel-F1: bestått (modell 0,600, «varsle alle» 0,261)",
        "Innenfor ±30 min: bestått (modell 80,0 %, baseline 65,0 %)",
        "Varsel-F1: bestått (modell 0,582, «varsle alle» 0,298)",
    ]


def test_panel_foer_testkjoringen_sier_at_dommen_venter(monkeypatch, tmp_path):
    """Før testkjøringen: ingen dom, og panelet sier at bestått/ikke bestått avgjøres på testperioden (beslutning 1)."""
    _syntetisk(monkeypatch, tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk()})
    panel = _panel(_forside())
    tekst = _ren(panel.tekst()).replace("\u00a0", " ")
    assert "Bestått eller ikke bestått avgjøres først på testperioden (E2-S10)." in tekst
    assert panel.finn_alle("li") == []


def test_panel_horisontene_viser_egne_tall(monkeypatch, tmp_path):
    _syntetisk(monkeypatch, tmp_path, {"testkjoringer": 0, "validering": syntetisk_blokk()})
    tabeller = _panel(_forside()).finn_alle("table")
    assert _tabell(tabeller[0])["Innenfor ±30 min"][:2] == ["75,0 % (300/400)", "62,5 % (250/400)"]
    assert _tabell(tabeller[3])["Innenfor ±30 min"][:2] == ["80,0 % (320/400)", "65,0 % (260/400)"]


def test_panel_modellen_taper_like_tydelig(monkeypatch, tmp_path):
    _syntetisk(monkeypatch, tmp_path, {"testkjoringer": 1, "test": syntetisk_blokk(modell_treff=230)})
    panel = _panel(_forside())
    tekst = _ren(panel.tekst()).replace("\u00a0", " ")
    assert "Modell − baseline, innenfor ±30 min: −5,0 pp (modellen dårligere)" in tekst
    assert "Innenfor ±30 min: ikke bestått (modell 57,5 %, baseline 62,5 %)" in tekst
    # Samme visuelle vekt: modell- og baselinecellene har samme klasse, uthevingen er den samme.
    for table in panel.finn_alle("table"):
        for tr in table.finn_alle("tbody")[0].finn_alle("tr"):
            klasser = {td.attrs.get("class") for td in tr.finn_alle("td")}
            assert klasser == {"verdi"}
            assert not any(n.tag in ("strong", "b", "em") for td in tr.finn_alle("td") for n in td.iter())


@pytest.mark.parametrize("innhold", [None, "ikke json", '{"testkjoringer": 0}', '{"testkjoringer": 1}',
                                     '{"testkjoringer": 1, "test_bare_baseline": {"antall_anlop": 1}}'],
                         ids=["ingen-fil", "ikke-json", "ingen-validering", "ingen-test", "bare-baseline"])
def test_panel_tall_mangler(monkeypatch, tmp_path, innhold):
    sti = tmp_path / "metrikker.json"
    if innhold is not None:
        sti.write_text(innhold, encoding="utf-8")
    _metrikker(monkeypatch, sti)
    panel = _panel(_forside())
    tekst = _ren(panel.tekst())
    assert "Tall mangler" in tekst
    assert panel.finn_alle("table") == []
    assert ("Testperioden" if innhold and '"testkjoringer": 1' in innhold else "Validering") in tekst


def test_panel_endrer_ikke_lista_og_stripa(monkeypatch, valideringsvisning):
    """Lista og prediktor-stripa er like med og uten tall i panelet (E2-S08-visningen er urørt)."""
    def deler(dokument):
        stripe = [s for s in dokument.finn_alle("section") if "prediktor" in s.attrs.get("class", "").split()][0]
        liste = [n for n in dokument.iter() if n.attrs.get("id") == "anlopslista"][0]
        return _ren(stripe.tekst()), _ren(liste.tekst()), [_ren(th.tekst()) for th in liste.finn_alle("th")]

    uten = deler(_forside())
    _metrikker(monkeypatch, valideringsvisning)
    med = _forside()
    assert deler(med) == uten
    assert deler(med)[2] == KOLONNER
    # Panelet står etter lista i HTML, så mobil (< 640 px) viser lista først (beslutning 2A).
    ider = [n.attrs.get("id") for n in med.iter() if n.attrs.get("id") in ("anlopslista", "treffsikkerhet")]
    assert ider == ["anlopslista", "treffsikkerhet"]


def test_panel_uu_struktur(monkeypatch, valideringsvisning):
    """Overskrifter uten hopp, th med scope, caption per tabell, og ingen farge alene (UU3, UU7)."""
    _metrikker(monkeypatch, valideringsvisning)
    dokument = _forside()
    nivaaer = [int(n.tag[1]) for n in dokument.iter() if len(n.tag) == 2 and n.tag[0] == "h" and n.tag[1] in "123456"]
    for forrige, neste in zip(nivaaer, nivaaer[1:]):
        assert neste <= forrige + 1
    panel = _panel(dokument)
    assert panel.tag == "section" and panel.attrs.get("aria-labelledby") == "panel-tittel"
    assert panel.finn_alle("img") == [] and panel.finn_alle("svg") == []  # verdiene står som tekst
    for table in panel.finn_alle("table"):
        captions = table.finn_alle("caption")
        assert len(captions) == 1 and _ren(captions[0].tekst())
        for th in table.finn_alle("th"):
            assert th.attrs.get("scope") in ("col", "row")
            assert _ren(th.tekst()), "tom overskriftscelle"
        for td in table.finn_alle("td"):
            assert _ren(td.skjermlesertekst()), "verdicelle uten tekst"
            assert "style" not in td.attrs
