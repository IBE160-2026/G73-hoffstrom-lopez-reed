"""Kontroll av svaret fra språkmodellen før det vises (E3-S03, PRD FR11 og FR11a).

``kontroller`` gir None når svaret godtas, ellers navnet på den første regelen som brytes. Adapteren logger det
som ``kontroll_<regel>`` og viser testmodus-teksten.

Reglene: ikke tomt (``tom``), høyst 400 tegn (``lengde``), høyst 3 setninger (``setninger``), hvert tall i teksten
finnes i inputen (``tall``), ingen andre skipsnavn fra utdraget (``skipsnavn``), ingen årsaksord fra en fast liste
(``aarsak``), og uten varsel (``forventet_forsinket`` er ikke True) ingen «forsink» (``forsink``).

Kontrollen er et vern, ikke et bevis. Den fanger oppdiktede tall, andre skip og de vanligste oppdiktede årsakene,
men ikke en feil påstand skrevet med tall og ord som finnes i inputen. Den er streng med vilje: et godt svar som
avvises, gir bare testmodus-teksten.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, Mapping, Optional

MAKS_TEGN = 400
MAKS_SETNINGER = 3

_TALL = re.compile(r"\d+(?:[.,]\d+)?")
_SETNINGSSLUTT = re.compile(r"(?<=[.!?…])\s+")

# Årsaker prompten forbyr. Hele ord (med vanlige bøyninger), så «vindu» og «motorvei» ikke gir falske treff for
# «vind», men «motoren» og «motorfeil» gjør det.
AARSAKSORD = (
    r"vær(et|varsel|forhold\w*)?", r"uvær\w*", r"storm\w*", r"vind(en|kast\w*|styrke)?", r"kuling\w*", r"tåke\w*",
    r"bølge\w*", r"sjøgang\w*", r"is(en|forhold\w*)?", r"streik\w*", r"motor(en|feil\w*|problem\w*|stopp\w*|havari\w*)?",
    r"maskin(en|feil\w*|problem\w*|skade\w*)?", r"mannskap\w*", r"havari\w*", r"ulykke\w*", r"teknisk\w*",
    r"kø(en)?", r"los(en|bestilling\w*)?", r"weather", r"storm", r"strike\w*", r"engine\w*", r"crew\w*",
)
_AARSAK = re.compile(r"(?<!\w)(" + "|".join(AARSAKSORD) + r")(?!\w)", re.IGNORECASE)
_FORSINK = re.compile(r"forsink", re.IGNORECASE)


def _normaliser(tall: str) -> str:
    """«09» og «9» er samme tall, og «64,2» er «64.2»."""
    heltall, _, desimaler = tall.replace(",", ".").partition(".")
    heltall = heltall.lstrip("0") or "0"
    return f"{heltall}.{desimaler}" if desimaler else heltall


def tall_i(tekst: str) -> set:
    return {_normaliser(t) for t in _TALL.findall(tekst)}


def antall_setninger(tekst: str) -> int:
    return len([s for s in _SETNINGSSLUTT.split(tekst.strip()) if s.strip()])


@lru_cache(maxsize=1)
def _alle_skipsnavn() -> tuple:
    from app.data import last_utdrag

    return tuple(sorted({a.shipname for a in last_utdrag() if a.shipname.strip()}, key=len, reverse=True))


@lru_cache(maxsize=4)
def _navnemonster(navn: tuple):
    if not navn:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(n) for n in navn) + r")(?!\w)", re.IGNORECASE)


def kontroller(
    tekst: Optional[str],
    fakta: Mapping[str, str],
    *,
    forventet_forsinket: Optional[bool],
    skipsnavn: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """None når svaret godtas, ellers regelen som brytes. ``skipsnavn`` er standard alle navn i utdraget."""
    tekst = (tekst or "").strip()
    if not tekst:
        return "tom"
    if len(tekst) > MAKS_TEGN:
        return "lengde"
    if antall_setninger(tekst) > MAKS_SETNINGER:
        return "setninger"
    input_tekst = "\n".join(f"{k}: {v}" for k, v in fakta.items())
    if not tall_i(tekst) <= tall_i(input_tekst):
        return "tall"
    # Et navn som også står i inputen (eget skip, avgangshavn …), er lov. Mønsteret prøver lengste navn først, så
    # «SIEM PEARL» ikke gir treff på et annet skip som bare heter «PEARL».
    monster = _navnemonster(tuple(sorted(set(skipsnavn), key=len, reverse=True)) if skipsnavn is not None
                            else _alle_skipsnavn())
    if monster is not None:
        for m in monster.finditer(tekst):
            if not re.search(r"(?<!\w)" + re.escape(m.group(0)) + r"(?!\w)", input_tekst, re.IGNORECASE):
                return "skipsnavn"
    if _AARSAK.search(tekst):
        return "aarsak"
    if forventet_forsinket is not True and _FORSINK.search(tekst):
        return "forsink"
    return None
