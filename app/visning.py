"""Visningshjelpere for hovedskjermen (E1-S06, UX §2, E0-S18).

Alt her gjelder bare visning. Tider vises i Europe/Oslo, avrundet til nærmeste minutt.
Beregninger (±30 min, avvik, sortering) bruker alltid de uavrundede tidene.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")

# Norske ukedagsforkortelser uten locale (mandag = 0, som ``weekday()``).
UKEDAGER = ("man", "tir", "ons", "tor", "fre", "lør", "søn")

HORISONT_ETIKETT = {6: "≤ 6 t", 24: "6–24 t"}


def til_oslo_minutt(t: dt.datetime) -> dt.datetime:
    """Tz-aware tid til Europe/Oslo, avrundet til nærmeste minutt (:30 sekunder runder opp)."""
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("tiden må ha tidssone (tz-aware datetime)")
    utc = t.astimezone(dt.timezone.utc)
    avrundet = (utc + dt.timedelta(seconds=30)).replace(second=0, microsecond=0)
    return avrundet.astimezone(OSLO)


def ukedag_klokke(t: dt.datetime) -> str:
    """«ons 09:56»."""
    o = til_oslo_minutt(t)
    return f"{UKEDAGER[o.weekday()]} {o:%H:%M}"


def ukedag_dato_klokke(t: dt.datetime) -> str:
    """«ons 08.10 08:00»."""
    o = til_oslo_minutt(t)
    return f"{UKEDAGER[o.weekday()]} {o:%d.%m %H:%M}"


def horisont_etikett(horisont_timer: int) -> str:
    """«≤ 6 t» eller «6–24 t» fra ``PrediksjonsInput.horisont_timer``."""
    try:
        return HORISONT_ETIKETT[horisont_timer]
    except KeyError:
        raise ValueError(f"ukjent horisont: {horisont_timer!r}") from None
