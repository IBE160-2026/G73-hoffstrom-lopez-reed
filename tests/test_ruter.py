"""Hovedskjermen `GET /` (E1-S06, UX §2 skjerm A, §5 tomt vindu)."""
import datetime as dt
import re

from conftest import parse_html

from app import STANDARD_NAA, create_app
from app.data import anlop_i_vindu
from app.prediksjon import lag_input, velg_prediktor
from app.visning import ukedag_dato_klokke, ukedag_klokke

KOLONNER = ["Skip", "Gruppe", "Rapportert", "Predikert", "Horisont", "Varsel"]
HJELPETEKST = "predikert før valgt tidspunkt"
TOM_MELDING = "Ingen anløp med rapportert ETA i dette vinduet. Prøv et annet tidspunkt."


def _ren(t):
    return re.sub(r"\s+", " ", t).strip()


def _rader(dokument):
    """Rader som {kolonne: celle-node}."""
    tbody = dokument.finn_alle("tbody")[0]
    rader = []
    for tr in tbody.finn_alle("tr"):
        tder = tr.finn_alle("td")
        rader.append({td.attrs["data-label"]: td for td in tder})
    return rader


def test_standardvindu(dokument):
    h2 = _ren(dokument.finn_alle("h2")[0].tekst())
    assert h2 == "15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)"

    ths = [_ren(th.tekst()) for th in dokument.finn_alle("th")]
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
    assert "rapportert ETA justert med median liggetid" in tekst


def test_norsk_tid_staar_paa_skjermen(dokument):
    assert "(norsk tid)" in _ren(dokument.tekst())


def test_tomt_vindu(tomt_dokument):
    h2 = _ren(tomt_dokument.finn_alle("h2")[0].tekst())
    assert h2 == "0 anløp · tir 03.02 08:00 – ons 04.02 08:00 (norsk tid)"
    assert TOM_MELDING in _ren(tomt_dokument.tekst())
    assert tomt_dokument.finn_alle("table") == []


def test_vindu_over_sommertid():
    """Vinduet krysser overgangen til vintertid natt til 26.10.2025: 24 t etter
    lør 08:00 (+02) er søn 07:00 (+01)."""
    naa = dt.datetime(2025, 10, 25, 8, 0, tzinfo=STANDARD_NAA.tzinfo)
    klient = create_app({"TESTING": True, "STANDARD_NAA": naa}).test_client()
    svar = klient.get("/")
    assert svar.status_code == 200
    dokument = parse_html(svar.get_data(as_text=True))
    h2 = _ren(dokument.finn_alle("h2")[0].tekst())
    assert h2.endswith("søn 26.10 07:00 (norsk tid)")
    antall = len(anlop_i_vindu(naa))
    assert h2.startswith(f"{antall} anløp")
    tbody = dokument.finn_alle("tbody")
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
