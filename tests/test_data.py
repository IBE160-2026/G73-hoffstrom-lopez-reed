"""Tester for app/data.py (E1-S03): vindusgrenser, filter, tidssoner og manglende fasit."""
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.data import GYLDIGE_VIS, _til_utc, STANDARD_UTDRAG, Anlop, anlop_i_vindu, last_utdrag

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "anlop_mini.csv"
UTC = dt.timezone.utc
NAA = dt.datetime(2025, 10, 8, 6, 0, tzinfo=UTC)


@pytest.fixture
def mini():
    return last_utdrag(FIXTURE)


def ider(anlop):
    return [a.voyageid for a in anlop]


def test_eta_akkurat_naa_er_med(mini):
    assert 1003 in ider(anlop_i_vindu(NAA, anlop=mini))


def test_eta_akkurat_naa_pluss_24_t_er_ute(mini):
    vindu = ider(anlop_i_vindu(NAA, anlop=mini))
    assert 1009 not in vindu
    assert 1008 in vindu  # ett sekund før slutt er med


def test_eta_ett_sekund_for_naa_er_ute(mini):
    assert 1002 not in ider(anlop_i_vindu(NAA, anlop=mini))


def test_filter(mini):
    alle = anlop_i_vindu(NAA, vis="alle", anlop=mini)
    passasjer = anlop_i_vindu(NAA, vis="passasjer", anlop=mini)
    ovrige = anlop_i_vindu(NAA, vis="ovrige", anlop=mini)
    assert ider(alle) == [1003, 1004, 1005, 1006, 1007, 1008]  # sortert på (ETA, voyageid)
    assert ider(passasjer) == [1003, 1004, 1005]
    assert ider(ovrige) == [1006, 1007, 1008]
    assert {a.gruppe for a in ovrige} == {"Øvrige"}
    assert [a.ship_group for a in ovrige] == ["Last", "Slep", "Fisk"]  # rå gruppe beholdes


def test_ukjent_filter_gir_valueerror(mini):
    with pytest.raises(ValueError) as feil:
        anlop_i_vindu(NAA, vis="rutegaende", anlop=mini)
    for verdi in GYLDIGE_VIS:
        assert verdi in str(feil.value)


def test_naiv_naa_gir_valueerror(mini):
    with pytest.raises(ValueError):
        anlop_i_vindu(dt.datetime(2025, 10, 8, 8), anlop=mini)


def test_naa_i_oslotid_gir_samme_vindu_som_utc(mini):
    oslo = dt.datetime(2025, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Oslo"))
    assert anlop_i_vindu(oslo, anlop=mini) == anlop_i_vindu(NAA, anlop=mini)


def test_ankomst_uten_suffiks_tolkes_som_utc(mini):
    anlop = {a.voyageid: a for a in mini}[1005]
    assert anlop.faktisk_ankomst == dt.datetime(2025, 10, 8, 11, 18, 10, tzinfo=UTC)
    assert anlop.faktisk_ankomst.isoformat() == "2025-10-08T11:18:10+00:00"


@pytest.mark.parametrize(
    "voyageid, status",
    [(1004, "empty"), (1006, "not_detected"), (1007, "avkortet_av_neste_seilas")],
)
def test_status_ikke_ok_gir_ingen_fasit(mini, voyageid, status):
    anlop = {a.voyageid: a for a in mini}[voyageid]
    assert anlop.faktisk_ankomst is None
    assert anlop.status_in_area == status


def test_ekte_utdrag_standardvindu():
    alle = last_utdrag()
    assert len(alle) == 7826
    naa = dt.datetime(2025, 10, 8, 8, 0, tzinfo=ZoneInfo("Europe/Oslo"))
    assert len(anlop_i_vindu(naa)) == 15
    assert len(anlop_i_vindu(naa, vis="ovrige")) == 9
    assert len(anlop_i_vindu(naa, vis="passasjer")) == 6


def test_last_utdrag_parses_en_gang():
    assert last_utdrag() is last_utdrag()
    assert last_utdrag(STANDARD_UTDRAG) is last_utdrag(str(STANDARD_UTDRAG))


def test_alle_tider_er_utc():
    for a in last_utdrag():
        assert isinstance(a, Anlop)
        assert a.eta_reported.tzinfo is UTC
        if a.faktisk_ankomst is not None:
            assert a.faktisk_ankomst.tzinfo is UTC


def test_timer_styrer_vindusslutt(mini):
    # timer=6 gir [06:00, 12:00): de to anløpene med ETA akkurat 12:00 er ute (halvåpent vindu).
    assert ider(anlop_i_vindu(NAA, timer=6, anlop=mini)) == [1003, 1004]
    # timer=7 gir [06:00, 13:00): 12:00 er inne, 14:00 er ute.
    assert ider(anlop_i_vindu(NAA, timer=7, anlop=mini)) == [1003, 1004, 1005, 1006]


def test_status_ikke_ok_med_ankomst_gir_ingen_fasit(mini):
    anlop = {a.voyageid: a for a in mini}[1011]
    assert anlop.status_in_area == "not_detected"
    assert anlop.faktisk_ankomst is None


@pytest.mark.parametrize(
    "tekst", ["2025-10-08T06:00:00Z", "2025-10-08T08:00:00+02:00", "2025-10-08T06:00:00"]
)
def test_til_utc_formater(tekst):
    t = _til_utc(tekst)
    assert t == NAA
    assert t.tzinfo is UTC
