"""Tester for metrikkmodulen (E1-S05): grensen, fasit, mismatch og tomt grunnlag."""
import datetime as dt

import pytest

from app.data import Anlop
from app.metrikker import (Feilstatistikk, Treffandel, Varselmetrikker, absolutt_feil, andel_innenfor,
                           dekning, er_forsinket, varselmetrikker, varsle_alle)
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


def prediksjon(voyageid, predikert, varsel=None):
    return Prediksjon(voyageid, 6, predikert, varsel, {"metode": "test", "gruppe": "Øvrige"})


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


# --- E2-S06: støttetall og varsel ------------------------------------------------------

MIN = dt.timedelta(minutes=1)


def test_absolutt_feil_mae_og_median():
    p = [prediksjon(1, FAKTISK + 10 * MIN), prediksjon(2, FAKTISK - 20 * MIN),
         prediksjon(3, FAKTISK + 90 * MIN), prediksjon(4, FAKTISK)]
    r = absolutt_feil(p, [anlop(1), anlop(2), anlop(3), anlop(4, status="empty")])
    assert r == Feilstatistikk(3, 40.0, 20.0)


def test_absolutt_feil_uavrundet_og_partall_median():
    p = [prediksjon(1, FAKTISK + dt.timedelta(seconds=30)), prediksjon(2, FAKTISK + 3 * MIN)]
    assert absolutt_feil(p, [anlop(1), anlop(2)]) == Feilstatistikk(2, 1.75, 1.75)


@pytest.mark.parametrize("prediksjoner, anlopene, tekst", [
    ([prediksjon(4242, FAKTISK), prediksjon(4242, FAKTISK)], [anlop(4242)], "4242"),
    ([prediksjon(1, FAKTISK)], [anlop(1), anlop(4242)], "4242"),
    ([prediksjon(4242, FAKTISK)], [anlop(1)], "4242"),
    ([], [anlop(1, status="empty")], "ingen anløp med fasit"),
])
def test_absolutt_feil_samme_kontrakt_som_andel(prediksjoner, anlopene, tekst):
    with pytest.raises(ValueError, match=tekst):
        absolutt_feil(prediksjoner, anlopene)


def test_er_forsinket_er_signert_og_streng():
    """Beslutning 06: bare senere enn kalibrert baseline, og strengt over 120 min."""
    kal = FAKTISK - 120 * MIN
    assert not er_forsinket(anlop(1), prediksjon(1, kal))
    assert er_forsinket(anlop(1), prediksjon(1, kal - dt.timedelta(seconds=1)))
    assert not er_forsinket(anlop(1), prediksjon(1, FAKTISK + 300 * MIN))  # tidlig er ikke forsinket
    with pytest.raises(ValueError):
        er_forsinket(anlop(1), prediksjon(2, kal))


def _kalibrert(forsinket):
    """Kalibrerte prediksjoner: anløp i ``forsinket`` kom 3 t etter baselinen, resten på minuttet."""
    return [prediksjon(v, FAKTISK - (180 * MIN if v in forsinket else dt.timedelta(0))) for v in range(1, 6)]


def test_varselmetrikker_presisjon_recall_f1():
    anlopene = [anlop(v) for v in range(1, 6)]
    kal = _kalibrert({1, 2})
    p = [prediksjon(1, FAKTISK, True), prediksjon(2, FAKTISK, False), prediksjon(3, FAKTISK, True),
         prediksjon(4, FAKTISK, None), prediksjon(5, FAKTISK, False)]
    r = varselmetrikker(p, anlopene, kal)
    assert r == Varselmetrikker(5, 2, 2, 1, 0.5, 0.5, 0.5)


def test_baseline_kan_ikke_varsle_gir_none():
    anlopene = [anlop(v) for v in range(1, 6)]
    kal = _kalibrert({1})
    r = varselmetrikker(kal, anlopene, kal)
    assert (r.presisjon, r.recall, r.f1) == (None, None, None)
    assert (r.n, r.forsinket, r.varsler) == (5, 1, 0)


def test_ingen_varsler_gir_null_presisjon():
    anlopene = [anlop(v) for v in range(1, 6)]
    p = [prediksjon(v, FAKTISK, False) for v in range(1, 6)]
    assert varselmetrikker(p, anlopene, _kalibrert({1})) == Varselmetrikker(5, 1, 0, 0, 0.0, 0.0, 0.0)


def test_varsle_alle_er_grunnraten():
    anlopene = [anlop(v) for v in range(1, 6)] + [anlop(9, status="empty")]
    kal = _kalibrert({1}) + [prediksjon(9, FAKTISK)]
    r = varsle_alle(anlopene, kal)
    assert (r.n, r.forsinket, r.varsler, r.treff) == (5, 1, 5, 1)
    assert r.presisjon == pytest.approx(0.2) and r.recall == 1.0
    assert r.f1 == pytest.approx(2 * 0.2 / 1.2)


def test_varsel_kalibrert_ma_dekke_samme_anlop():
    anlopene = [anlop(v) for v in range(1, 6)]
    p = [prediksjon(v, FAKTISK, False) for v in range(1, 6)]
    with pytest.raises(ValueError, match="5"):
        varselmetrikker(p, anlopene, _kalibrert(set())[:4])
