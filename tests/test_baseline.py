"""Tester for kalibrert baseline og velg_prediktor (E1-S04)."""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.data import Anlop, anlop_i_vindu, last_utdrag
from app.prediksjon import GYLDIGE_PREDIKTOR, lag_input, velg_prediktor
from app.prediksjon.baseline import BASELINE_FIL, BaselinePrediktor

UTC = dt.timezone.utc
OSLO = ZoneInfo("Europe/Oslo")
NAA = dt.datetime(2025, 10, 8, 6, 0, tzinfo=UTC)  # 08:00 norsk tid


def anlop(eta, ship_group="Last", voyageid=1):
    return Anlop(
        voyageid=voyageid, mmsino=257000000 + voyageid, shipname="TEST",
        ship_group=ship_group, eta_reported=eta, faktisk_ankomst=None,
        status_in_area="empty", split="test",
    )


def prediker_en(a, naa=NAA):
    inp = lag_input(a, naa)
    [p] = BaselinePrediktor().prediker([inp], naa)
    return inp, p


def test_bergen_energy():
    [a] = [a for a in anlop_i_vindu(NAA) if a.shipname == "BERGEN ENERGY"]
    assert a.ship_group == "Tank"
    assert a.eta_reported == dt.datetime(2025, 10, 8, 9, 0, tzinfo=UTC)
    inp, p = prediker_en(a)
    assert p.predikert_ankomst == dt.datetime(2025, 10, 8, 7, 55, 48, tzinfo=UTC)
    assert p.predikert_ankomst.astimezone(OSLO).time() == dt.time(9, 55, 48)
    assert p.horisont_timer == 6
    assert p.forventet_forsinket is None
    assert p.forklaring["gruppe"] == "Øvrige"
    assert p.forklaring["offset_minutter"] == 64.2
    assert p.forklaring["metode"] == "kalibrert_baseline"


def test_passasjer_offset_er_uavrundet():
    eta = dt.datetime(2025, 10, 8, 12, 0, tzinfo=UTC)
    _, p = prediker_en(anlop(eta, "Passasjer"))
    assert p.predikert_ankomst == eta - dt.timedelta(minutes=44.75)
    assert p.predikert_ankomst == dt.datetime(2025, 10, 8, 11, 15, 15, tzinfo=UTC)
    assert p.forklaring["offset_minutter"] == 44.75


def test_offset_leses_fra_baseline_json():
    lagret = json.loads(Path(BASELINE_FIL).read_text(encoding="utf-8"))["offset_minutter"]
    assert BaselinePrediktor().offset_minutter == lagret


def test_baselinen_varsler_aldri():
    b = BaselinePrediktor()
    assert b.navn == "Kalibrert baseline"
    assert b.kan_varsle is False
    naa = dt.datetime(2025, 10, 1, tzinfo=UTC)
    inputs = [lag_input(a, naa) for a in anlop_i_vindu(naa, timer=24 * 7)]
    assert inputs
    assert all(p.forventet_forsinket is None for p in b.prediker(inputs, naa))


@pytest.mark.parametrize("delta, horisont", [
    (dt.timedelta(hours=6), 6),
    (dt.timedelta(hours=6, seconds=1), 24),
    (dt.timedelta(0), 6),
    (dt.timedelta(hours=23, minutes=59), 24),
])
def test_horisontgrense(delta, horisont):
    inp, p = prediker_en(anlop(NAA + delta))
    assert inp.horisont_timer == p.horisont_timer == horisont
    assert inp.t_kutt == NAA + delta - dt.timedelta(hours=horisont)


def test_eta_mer_enn_24_t_fram_kuttes_ved_naa():
    inp, p = prediker_en(anlop(NAA + dt.timedelta(hours=30)))
    assert inp.horisont_timer == p.horisont_timer == 24
    assert inp.t_kutt == NAA


def test_naa_i_annen_tidssone_gir_samme_input():
    a = anlop(NAA + dt.timedelta(hours=3))
    assert lag_input(a, NAA.astimezone(OSLO)) == lag_input(a, NAA)
    assert lag_input(a, NAA.astimezone(OSLO)).t_kutt.utcoffset() == dt.timedelta(0)


def test_naiv_naa_gir_valueerror():
    with pytest.raises(ValueError):
        lag_input(anlop(NAA), dt.datetime(2025, 10, 8, 8))


def test_naiv_eta_gir_valueerror():
    with pytest.raises(ValueError):
        lag_input(anlop(dt.datetime(2025, 10, 8, 9)), NAA)


@pytest.mark.parametrize("verdi", [None, "", "  ", "auto", "baseline", " Baseline ", "modell"])
def test_velg_prediktor_gir_baseline(monkeypatch, verdi):
    if verdi is None:
        monkeypatch.delenv("PREDIKTOR", raising=False)
    else:
        monkeypatch.setenv("PREDIKTOR", verdi)
    assert isinstance(velg_prediktor(), BaselinePrediktor)


def test_naiv_kan_ikke_velges(monkeypatch):
    """``NaivPrediktor`` er bare referanse i regresjonen (E1-S05), ikke et valg."""
    with pytest.raises(ValueError):
        velg_prediktor("naiv")
    monkeypatch.setenv("PREDIKTOR", "naiv")
    with pytest.raises(ValueError):
        velg_prediktor()


def test_velg_prediktor_ukjent_verdi(monkeypatch):
    monkeypatch.setenv("PREDIKTOR", "tull")
    with pytest.raises(ValueError) as feil:
        velg_prediktor()
    assert "tull" in str(feil.value)
    for verdi in GYLDIGE_PREDIKTOR:
        assert verdi in str(feil.value)


def test_velg_prediktor_ukjent_verdi_direkte():
    with pytest.raises(ValueError):
        velg_prediktor("tull")


def test_mini_fixture_far_riktig_gruppeoffset():
    mini = last_utdrag(Path(__file__).resolve().parent / "fixtures" / "anlop_mini.csv")
    inputs = [lag_input(a, NAA) for a in anlop_i_vindu(NAA, anlop=mini)]
    assert inputs
    for inp, p in zip(inputs, BaselinePrediktor().prediker(inputs, NAA)):
        venter = 44.75 if inp.gruppe == "Passasjer" else 64.2
        assert inp.eta_reported - p.predikert_ankomst == dt.timedelta(minutes=venter)
