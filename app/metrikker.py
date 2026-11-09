"""Metrikkmodulen (arkitektur A6, E1-S05): den eneste kilden til treffandel og dekning.

Treff er ``|faktisk − predikert| ≤ minutter`` (inklusiv), på uavrundede tider. Bare anløp
med fasit (``status_in_area == "ok"``) scores; resten telles av ``dekning()``.
Modulen lager aldri prediksjoner selv; de kommer fra en prediktor via ``lag_input``.

E2-S06 la til støttetallene (MAE og median absolutt feil) og varselmetrikkene (presisjon, recall og F1
mot ``er_forsinket``, beslutning 06), med samme oppslag på ``voyageid`` som ``andel_innenfor``.
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from app.data import Anlop
from app.prediksjon import Prediksjon


class Treffandel(NamedTuple):
    treff: int
    n: int
    andel: float  # treff / n, uavrundet


def har_fasit(a: Anlop) -> bool:
    return a.status_in_area == "ok" and a.faktisk_ankomst is not None


def _par(prediksjoner: Iterable[Prediksjon], anlop: Iterable[Anlop]) -> List[Tuple[Prediksjon, Anlop]]:
    """Prediksjon og anløp parvis for anløpene med fasit, slått opp på ``voyageid``.

    ``ValueError`` (med id) når en prediksjon mangler anløp, når en voyageid er predikert to
    ganger, når et anløp med fasit mangler prediksjon, og når ingen anløp har fasit.
    """
    etter_id: Dict[int, Anlop] = {a.voyageid: a for a in anlop}
    par = []
    sett = set()
    for p in prediksjoner:
        a = etter_id.get(p.voyageid)
        if a is None:
            raise ValueError(f"prediksjon for voyageid {p.voyageid} finnes ikke blant anløpene")
        if p.voyageid in sett:
            raise ValueError(f"voyageid {p.voyageid} er predikert mer enn én gang")
        sett.add(p.voyageid)
        if har_fasit(a):
            par.append((p, a))
    mangler = sorted(v for v, a in etter_id.items() if har_fasit(a) and v not in sett)
    if mangler:
        raise ValueError(f"anløp med fasit mangler prediksjon: voyageid {mangler[:10]}")
    if not par:
        raise ValueError("ingen anløp med fasit å score")
    return par


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
    grense = dt.timedelta(minutes=minutter)
    par = _par(prediksjoner, anlop)
    treff = sum(1 for p, a in par if abs(a.faktisk_ankomst - p.predikert_ankomst) <= grense)
    return Treffandel(treff, len(par), treff / len(par))


class Feilstatistikk(NamedTuple):
    n: int
    mae_min: float  # snitt av |faktisk − predikert| i minutter, uavrundet
    median_min: float  # median av |faktisk − predikert| i minutter, uavrundet


def absolutt_feil(prediksjoner: Iterable[Prediksjon], anlop: Iterable[Anlop]) -> Feilstatistikk:
    """MAE og median absolutt feil i minutter (støttetall, aldri hovedtallet).

    Samme oppslag og samme ``ValueError`` som ``andel_innenfor``. Bare anløp med fasit scores.
    """
    feil = [abs((a.faktisk_ankomst - p.predikert_ankomst).total_seconds()) / 60
            for p, a in _par(prediksjoner, anlop)]
    return Feilstatistikk(len(feil), sum(feil) / len(feil), statistics.median(feil))


class Varselmetrikker(NamedTuple):
    n: int  # anløp med fasit
    forsinket: int  # anløp der er_forsinket er sann
    varsler: int  # anløp med forventet_forsinket = True
    treff: int  # varsel og forsinket
    presisjon: Optional[float]  # None når prediktoren ikke kan varsle
    recall: Optional[float]
    f1: Optional[float]


VARSEL_TERSKEL_MIN = 120.0  # beslutning 06 og PRD A3; endres ikke


def er_forsinket(a: Anlop, kalibrert: Prediksjon, terskel_min: float = VARSEL_TERSKEL_MIN) -> bool:
    """Beslutning 06: signert, faktisk ankomst mer enn ``terskel_min`` etter den kalibrerte baselinen.

    ``kalibrert`` er den kalibrerte baselinens prediksjon for samme anløp. Modulen regner den aldri selv.
    """
    if kalibrert.voyageid != a.voyageid:
        raise ValueError(f"kalibrert prediksjon {kalibrert.voyageid} hører ikke til anløp {a.voyageid}")
    return a.faktisk_ankomst - kalibrert.predikert_ankomst > dt.timedelta(minutes=terskel_min)


def _forsinket(
    kalibrert: Iterable[Prediksjon], anlop: Iterable[Anlop], terskel_min: float
) -> Dict[int, bool]:
    return {a.voyageid: er_forsinket(a, k, terskel_min) for k, a in _par(kalibrert, anlop)}


def _varselmetrikker(par_varsel: List[Tuple[bool, bool]], kan_varsle: bool) -> Varselmetrikker:
    n = len(par_varsel)
    forsinket = sum(1 for _, f in par_varsel if f)
    varsler = sum(1 for v, _ in par_varsel if v)
    treff = sum(1 for v, f in par_varsel if v and f)
    if not kan_varsle:
        return Varselmetrikker(n, forsinket, varsler, treff, None, None, None)
    presisjon = treff / varsler if varsler else 0.0
    recall = treff / forsinket if forsinket else 0.0
    f1 = 2 * presisjon * recall / (presisjon + recall) if presisjon + recall else 0.0
    return Varselmetrikker(n, forsinket, varsler, treff, presisjon, recall, f1)


def varselmetrikker(
    prediksjoner: Iterable[Prediksjon],
    anlop: Iterable[Anlop],
    kalibrert: Iterable[Prediksjon],
    terskel_min: float = VARSEL_TERSKEL_MIN,
) -> Varselmetrikker:
    """Presisjon, recall og F1 for ``forventet_forsinket`` mot ``er_forsinket`` (beslutning 06).

    ``kalibrert`` er den kalibrerte baselinens prediksjoner for de samme anløpene; de definerer
    ``er_forsinket``. Begge sett slås opp som i ``andel_innenfor`` (samme ``ValueError``), og de må
    dekke nøyaktig de samme anløpene med fasit.

    ``forventet_forsinket = None`` betyr at prediktoren ikke varslet for raden (delegert til baselinen)
    og telles som ikke varsel. Er den None for alle rader, kan prediktoren ikke varsle, og presisjon,
    recall og F1 er None (ikke aktuelt), ikke 0. Uten varsler er presisjonen 0,0.
    """
    anlop = list(anlop)
    par = _par(prediksjoner, anlop)
    fasit = _forsinket(kalibrert, anlop, terskel_min)
    kan_varsle = any(p.forventet_forsinket is not None for p, _ in par)
    return _varselmetrikker([(p.forventet_forsinket is True, fasit[a.voyageid]) for p, a in par], kan_varsle)


def varsle_alle(
    anlop: Iterable[Anlop], kalibrert: Iterable[Prediksjon], terskel_min: float = VARSEL_TERSKEL_MIN
) -> Varselmetrikker:
    """Referansen «varsle alle» (PRD FR10) på de samme anløpene: presisjon = grunnraten, recall = 1."""
    fasit = _forsinket(kalibrert, anlop, terskel_min)
    return _varselmetrikker([(True, f) for f in fasit.values()], True)


def dekning(anlop: Iterable[Anlop]) -> Dict[str, int]:
    """Antall anløp per ``status_in_area`` (``ok`` = med fasit)."""
    return dict(Counter(a.status_in_area for a in anlop))
