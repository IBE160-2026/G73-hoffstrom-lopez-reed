"""Kontroll av svaret fra språkmodellen før det vises (E3-S03, PRD FR11 og FR11a).

``kontroller`` gir None når svaret godtas, ellers navnet på den første regelen som brytes. Adapteren logger det
som ``kontroll_<regel>`` og viser testmodus-teksten.

Reglene: ikke tomt (``tom``), høyst 400 tegn (``lengde``), høyst 3 setninger (``setninger``), hvert tall i teksten
finnes i inputen (``tall``), ingen tall skrevet med ord (``tallord``), ingen andre skipsnavn fra utdraget
(``skipsnavn``), ingen årsaksord fra en fast liste (``aarsak``), uten varsel (``forventet_forsinket`` er ikke True)
ingen «forsink» (``forsink``), og retningsord som stemmer med fortegnet på avviket (``retning``, se ``retning``).

Kontrollen er et vern, ikke et bevis. Den fanger oppdiktede tall, andre skip og de vanligste oppdiktede årsakene,
men ikke en feil påstand skrevet med tall og ord som finnes i inputen. Tall skrevet med ord avvises fra en fast liste
(«to timer», «en halvtime», «dobbelt»), men «en» og «ett» kan ikke skilles fra artikkelen og slipper gjennom.
Retningsord fanges bare fra listene under. Den er streng med vilje: et godt svar som
avvises, gir bare testmodus-teksten.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, Mapping, Optional

MAKS_TEGN = 400
MAKS_SETNINGER = 3

# Et fortegn (+, - eller −) teller bare når det ikke står rett etter et ord eller tall («v1», «6–24» har ikke fortegn).
_TALL = re.compile(r"(?:(?<![\w])([+\-\u2212]))?(\d+(?:[.,]\d+)?)")
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

# Tall skrevet med ord (prompten sier at tall skal skrives som i faktaene). «en», «ett» og «én» er ikke med: de kan
# ikke skilles fra artikkelen.
TALLORD = (
    r"to", r"tre", r"fire", r"fem", r"seks", r"sju", r"syv", r"åtte", r"ni", r"ti", r"elleve", r"tolv", r"tretten",
    r"fjorten", r"femten", r"seksten", r"sytten", r"atten", r"nitten", r"tjue\w*", r"tretti\w*", r"førti\w*",
    r"femti\w*", r"seksti\w*", r"sytti\w*", r"åtti\w*", r"nitti\w*", r"hundre\w*", r"tusen\w*", r"null",
    r"halv\w*", r"kvarter\w*", r"dobbel\w*", r"tredobbel\w*", r"et par",
    r"two", r"three", r"four", r"five", r"ten", r"twenty", r"thirty", r"hundred", r"half", r"double", r"twice",
)
_TALLORD = re.compile(r"(?<!\w)(" + "|".join(TALLORD) + r")(?!\w)", re.IGNORECASE)

# Retningsord. «tidligere anløp» (= forrige anløp) er ikke en retning.
SENERE_ORD = (r"senere", r"forsink\w*", r"for sent", r"etter tiden", r"etter planen", r"later", r"delay\w*", r"late")
TIDLIGERE_ORD = (r"tidligere(?!\s+anløp)", r"før tiden", r"for tidlig", r"før planen", r"earlier", r"early", r"ahead")
_SENERE = re.compile(r"(?<!\w)(" + "|".join(SENERE_ORD) + r")(?!\w)", re.IGNORECASE)
_TIDLIGERE = re.compile(r"(?<!\w)(" + "|".join(TIDLIGERE_ORD) + r")(?!\w)", re.IGNORECASE)


def retning(prediksjon) -> Optional[int]:
    """Fortegnet på avviket teksten skal beskrive: +1 senere, −1 tidligere, 0 ingen, None ukjent.

    Modell v1: fortegnet på ``predikert_avvik_min`` (avvik fra kalibrert baseline). Baselinen og rader modellen har
    delegert: predikert ankomst minus rapportert ETA. Det er alltid negativt (rapportert ETA minus offset), så
    «tidligere enn rapportert ETA» godtas og «senere» avvises.
    """
    f = prediksjon.forklaring
    if f.get("metode") == "modell" and f.get("predikert_avvik_min") is not None:
        verdi = round(f["predikert_avvik_min"])
    elif f.get("eta_reported") is not None:
        verdi = round((prediksjon.predikert_ankomst - f["eta_reported"]).total_seconds() / 60)
    else:
        return None
    return (verdi > 0) - (verdi < 0)


def _normaliser(tall: str) -> str:
    """«09» og «9» er samme tall, «64,2» er «64.2», og «64,20» og «9,0» er «64.2» og «9»."""
    heltall, _, desimaler = tall.replace(",", ".").partition(".")
    heltall = heltall.lstrip("0") or "0"
    desimaler = desimaler.rstrip("0")
    return f"{heltall}.{desimaler}" if desimaler else heltall


def tall_i(tekst: str) -> set:
    """Tallene i teksten uten fortegn."""
    return {_normaliser(t) for _, t in _TALL.findall(tekst)}


def _med_fortegn(tekst: str) -> set:
    """{(fortegn, tall)} der fortegnet er «+» eller «-». Et tall uten fortegn regnes som positivt."""
    return {("-" if s in "-\u2212" and s else "+", _normaliser(t)) for s, t in _TALL.findall(tekst)}


def _bare_skrevet_med_fortegn(tekst: str) -> set:
    return {("-" if s in "-\u2212" else "+", _normaliser(t)) for s, t in _TALL.findall(tekst) if s}


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
    retning: Optional[int] = None,
) -> Optional[str]:
    """None når svaret godtas, ellers regelen som brytes. ``skipsnavn`` er standard alle navn i utdraget.

    ``retning`` (+1, −1, 0) er fortegnet på avviket (``retning(prediksjon)``). Med +1 avvises «tidligere»-ord, med −1
    «senere»-ord, og med 0 begge. None hopper over regelen."""
    tekst = (tekst or "").strip()
    if not tekst:
        return "tom"
    if len(tekst) > MAKS_TEGN:
        return "lengde"
    if antall_setninger(tekst) > MAKS_SETNINGER:
        return "setninger"
    input_tekst = "\n".join(f"{k}: {v}" for k, v in fakta.items())
    # Tillatte tall kommer bare fra verdiene, ikke fra etikettene. Et tall uten fortegn må finnes i inputen uansett
    # fortegn; et tall skrevet med fortegn må finnes med samme fortegn («+12» godtas ikke mot «−12»).
    verdier = "\n".join(fakta.values())
    if not tall_i(tekst) <= tall_i(verdier) or not _bare_skrevet_med_fortegn(tekst) <= _med_fortegn(verdier):
        return "tall"
    if _TALLORD.search(tekst):
        return "tallord"
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
    if retning is not None:
        if (retning <= 0 and _SENERE.search(tekst)) or (retning >= 0 and _TIDLIGERE.search(tekst)):
            return "retning"
    return None
