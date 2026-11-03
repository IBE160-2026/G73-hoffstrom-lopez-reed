"""Tester for metrikkmodulen (E1-S05): grensen, fasit, mismatch og tomt grunnlag."""
import datetime as dt

import pytest

from app.data import Anlop
from app.metrikker import Treffandel, andel_innenfor, dekning
from app.prediksjon import Prediksjon

UTC = dt.timezone.utc
FAKTISK = dt.datetime(2025, 10, 8, 12, 0, tzinfo=UTC)


def anlop(voyageid, status="ok", faktisk=FAKTISK):
    return Anlop(
        voyageid=voyageid, mmsino=257000000 + voyageid, shipname="TEST",
        ship_group="Last", eta_reported=FAKTISK + dt.timedelta(hours=1),
        faktisk_ankomst=faktisk if status == "ok" else None,
        status_in_area=status, split="test",
    )


def prediksjon(voyageid, predikert):
    return Prediksjon(voyageid, 6, predikert, None, {"metode": "test", "gruppe": "Øvrige"})


@pytest.mark.parametrize("avvik, treff", [
    (dt.timedelta(minutes=30), 1),
    (-dt.timedelta(minutes=30), 1),
    (dt.timedelta(minutes=30, seconds=1), 0),
    (-dt.timedelta(minutes=30, seconds=1), 0),
    (dt.timedelta(minutes=29, seconds=59, microseconds=999999), 1),
])
def test_grensen_er_inklusiv_og_uavrundet(avvik, treff):
    r = andel_innenfor([prediksjon(1, FAKTISK + avvik)], [anlop(1)])
    assert r == Treffandel(treff, 1, float(treff))


def test_annen_grense():
    p = [prediksjon(1, FAKTISK + dt.timedelta(minutes=45))]
    assert andel_innenfor(p, [anlop(1)], minutter=60).treff == 1
    assert andel_innenfor(p, [anlop(1)]).treff == 0


@pytest.mark.parametrize("status", ["empty", "not_detected", "avkortet_av_neste_seilas"])
def test_uten_fasit_er_utenfor_teller_og_nevner(status):
    anlopene = [anlop(1), anlop(2, status=status), anlop(3)]
    p = [
        prediksjon(1, FAKTISK),
        prediksjon(2, FAKTISK),  # ville vært treff om det ble scoret
        prediksjon(3, FAKTISK + dt.timedelta(hours=2)),
    ]
    assert andel_innenfor(p, anlopene) == Treffandel(1, 2, 0.5)


def test_ikke_ok_med_faktisk_ankomst_scores_ikke():
    """Status avgjør, ikke om faktisk ankomst tilfeldigvis er fylt ut."""
    uten = Anlop(2, 2, "X", "Last", FAKTISK, FAKTISK, "empty", "test")
    p = [prediksjon(1, FAKTISK + dt.timedelta(hours=2)), prediksjon(2, FAKTISK)]
    assert andel_innenfor(p, [anlop(1), uten]) == Treffandel(0, 1, 0.0)


def test_samme_voyageid_to_ganger_gir_valueerror():
    with pytest.raises(ValueError, match="4242"):
        andel_innenfor([prediksjon(4242, FAKTISK), prediksjon(4242, FAKTISK)], [anlop(4242)])


def test_anlop_med_fasit_uten_prediksjon_gir_valueerror():
    with pytest.raises(ValueError, match="4242"):
        andel_innenfor([prediksjon(1, FAKTISK)], [anlop(1), anlop(4242)])


def test_ok_uten_faktisk_ankomst_scores_ikke():
    a = Anlop(1, 1, "X", "Last", FAKTISK, None, "ok", "test")
    with pytest.raises(ValueError):
        andel_innenfor([prediksjon(1, FAKTISK)], [a])


def test_prediksjon_uten_anlop_gir_valueerror_med_id():
    with pytest.raises(ValueError, match="4242"):
        andel_innenfor([prediksjon(1, FAKTISK), prediksjon(4242, FAKTISK)], [anlop(1)])


@pytest.mark.parametrize("prediksjoner, anlopene", [
    ([], []),
    ([], [anlop(1, status="empty")]),
    ([prediksjon(1, FAKTISK)], [anlop(1, status="empty")]),
])
def test_tomt_grunnlag_gir_valueerror(prediksjoner, anlopene):
    with pytest.raises(ValueError, match="ingen anløp med fasit"):
        andel_innenfor(prediksjoner, anlopene)


def test_dekning_teller_per_status():
    anlopene = [anlop(1), anlop(2), anlop(3, status="empty"), anlop(4, status="not_detected")]
    assert dekning(anlopene) == {"ok": 2, "empty": 1, "not_detected": 1}
    assert dekning([]) == {}
