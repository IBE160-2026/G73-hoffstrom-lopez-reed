"""Visningshjelperne (E1-S06, E0-S18): norsk tid, avrunding til nærmeste minutt, horisont."""
import datetime as dt

import pytest

from app.visning import (
    horisont_etikett,
    til_oslo_minutt,
    ukedag_dato_klokke,
    ukedag_klokke,
)

UTC = dt.timezone.utc


def test_avrunding_29_sekunder_ned():
    t = dt.datetime(2025, 10, 8, 7, 55, 29, tzinfo=UTC)
    assert ukedag_klokke(t) == "ons 09:55"


def test_avrunding_30_sekunder_opp():
    t = dt.datetime(2025, 10, 8, 7, 55, 30, tzinfo=UTC)
    assert ukedag_klokke(t) == "ons 09:56"


def test_avrunding_29_999_sekunder_ned():
    t = dt.datetime(2025, 10, 8, 7, 55, 29, 999999, tzinfo=UTC)
    assert ukedag_klokke(t) == "ons 09:55"


def test_bergen_energy():
    # 07:55:48 UTC = 09:55:48 norsk tid → «ons 09:56» (E0-S18).
    t = dt.datetime(2025, 10, 8, 7, 55, 48, tzinfo=UTC)
    assert ukedag_klokke(t) == "ons 09:56"


def test_avrunding_over_midnatt_bytter_dag():
    t = dt.datetime(2025, 10, 8, 21, 59, 45, tzinfo=UTC)  # 23:59:45 norsk tid
    assert ukedag_dato_klokke(t) == "tor 09.10 00:00"


@pytest.mark.parametrize(
    "dag, forventet",
    [(6, "man"), (7, "tir"), (8, "ons"), (9, "tor"), (10, "fre"), (11, "lør"), (12, "søn")],
)
def test_ukedager(dag, forventet):
    t = dt.datetime(2025, 10, dag, 10, 0, tzinfo=UTC)
    assert ukedag_klokke(t).split()[0] == forventet


def test_dato_format():
    t = dt.datetime(2025, 10, 8, 6, 0, tzinfo=UTC)
    assert ukedag_dato_klokke(t) == "ons 08.10 08:00"


def test_sommertid_til_vintertid():
    """Oslo går fra +02 til +01 natt til søndag 26.10.2025 (01:00 UTC)."""
    for_ = dt.datetime(2025, 10, 26, 0, 30, tzinfo=UTC)
    etter = dt.datetime(2025, 10, 26, 1, 30, tzinfo=UTC)
    assert til_oslo_minutt(for_).utcoffset() == dt.timedelta(hours=2)
    assert til_oslo_minutt(etter).utcoffset() == dt.timedelta(hours=1)
    assert ukedag_dato_klokke(for_) == "søn 26.10 02:30"
    assert ukedag_dato_klokke(etter) == "søn 26.10 02:30"
    assert ukedag_klokke(dt.datetime(2025, 10, 26, 12, 0, tzinfo=UTC)) == "søn 13:00"


def test_naiv_tid_avvises():
    with pytest.raises(ValueError):
        ukedag_klokke(dt.datetime(2025, 10, 8, 8, 0))


def test_horisont_etiketter():
    assert horisont_etikett(6) == "≤ 6 t"
    assert horisont_etikett(24) == "6–24 t"
    with pytest.raises(ValueError):
        horisont_etikett(12)
