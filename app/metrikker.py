"""Metrikkmodulen (arkitektur A6, E1-S05): den eneste kilden til treffandel og dekning.

Treff er ``|faktisk − predikert| ≤ minutter`` (inklusiv), på uavrundede tider. Bare anløp
med fasit (``status_in_area == "ok"``) scores; resten telles av ``dekning()``.
Modulen lager aldri prediksjoner selv; de kommer fra en prediktor via ``lag_input``.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Dict, Iterable, NamedTuple

from app.data import Anlop
from app.prediksjon import Prediksjon


class Treffandel(NamedTuple):
    treff: int
    n: int
    andel: float  # treff / n, uavrundet


def har_fasit(a: Anlop) -> bool:
    return a.status_in_area == "ok" and a.faktisk_ankomst is not None


def andel_innenfor(
    prediksjoner: Iterable[Prediksjon], anlop: Iterable[Anlop], minutter: float = 30
) -> Treffandel:
    """Andel prediksjoner innenfor ±``minutter`` av faktisk ankomst.

    Hver prediksjon slås opp på ``voyageid`` i ``anlop``. ``ValueError`` (med id) når en
    prediksjon mangler anløp, når en voyageid er predikert to ganger, eller når et anløp
    med fasit mangler prediksjon (ellers kunne en prediktor hoppe over vanskelige anløp).
    Anløp uten fasit hoppes over (verken teller eller nevner). Ingen scorbare anløp gir
    ``ValueError``, aldri 0 %.
    """
    etter_id: Dict[int, Anlop] = {a.voyageid: a for a in anlop}
    grense = dt.timedelta(minutes=minutter)
    treff = n = 0
    sett = set()
    for p in prediksjoner:
        a = etter_id.get(p.voyageid)
        if a is None:
            raise ValueError(f"prediksjon for voyageid {p.voyageid} finnes ikke blant anløpene")
        if p.voyageid in sett:
            raise ValueError(f"voyageid {p.voyageid} er predikert mer enn én gang")
        sett.add(p.voyageid)
        if not har_fasit(a):
            continue
        n += 1
        if abs(a.faktisk_ankomst - p.predikert_ankomst) <= grense:
            treff += 1
    mangler = sorted(v for v, a in etter_id.items() if har_fasit(a) and v not in sett)
    if mangler:
        raise ValueError(f"anløp med fasit mangler prediksjon: voyageid {mangler[:10]}")
    if n == 0:
        raise ValueError("ingen anløp med fasit å score")
    return Treffandel(treff, n, treff / n)


def dekning(anlop: Iterable[Anlop]) -> Dict[str, int]:
    """Antall anløp per ``status_in_area`` (``ok`` = med fasit)."""
    return dict(Counter(a.status_in_area for a in anlop))
