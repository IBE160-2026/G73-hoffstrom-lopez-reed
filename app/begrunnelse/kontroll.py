"""Kontroll av svaret fra språkmodellen før det vises (E3-S03, PRD FR11 og FR11a).

``kontroller`` gir None når svaret godtas, ellers navnet på den første regelen som brytes. Adapteren logger det
som ``kontroll_<regel>`` og viser testmodus-teksten.

Reglene:

- ikke tomt (``tom``);
- lengde (``lengde``): høyst 400 tegn for begrunnelsen, høyst 700 tegn for briefen (E3-S05);
- setninger (``setninger``): 1–3 setninger for begrunnelsen, 3–5 setninger for briefen;
- hvert tall i teksten finnes i inputen (``tall``), og ingen tall er skrevet med ord (``tallord``);
- ingen andre skipsnavn fra utdraget (``skipsnavn``) og ingen årsaksord fra en fast liste (``aarsak``);
- uten varsel (``forventet_forsinket`` er ikke True) ingen «forsink» (``forsink``);
- retningsord som stemmer med fortegnet på avviket (``retning``, se ``retning``).

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

from app.begrunnelse.klartekst import retning as _klartekst_retning

MAKS_TEGN = 400
MAKS_SETNINGER = 3
# Briefen (E3-S05, PRD FR12): 3–5 setninger og høyst 700 tegn.
BRIEF_MAKS_TEGN = 700
BRIEF_MIN_SETNINGER = 3
BRIEF_MAKS_SETNINGER = 5

# Et fortegn (+, - eller −) teller bare når det ikke står rett etter et ord eller tall («v1», «6–24» har ikke fortegn).
_TALL = re.compile(r"(?:(?<![\w])([+\-\u2212]))?(\d+(?:[.,]\d+)?)")
# «kl.» og «ca.» avslutter ikke en setning (konklusjonen bruker «kl. 17:44»). Det gjør heller ikke punktum etter et
# frittstående ord på 1–2 store bokstaver: initialer i skipsnavn («G. M. DANNEVIG», «LT. PETE MAVERICK MITCHELL»).
_SETNINGSSLUTT = re.compile(r"(?<![Kk]l\.)(?<![Cc]a\.)(?<!(?<!\w)[A-ZÆØÅ]\.)(?<!(?<!\w)[A-ZÆØÅ]{2}\.)(?<=[.!?…])\s+")

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
# Interne begreper som ikke skal stå i teksten til havnevakta (``begrunnelse-v4``).
BEGREPER = (r"kalibrert\w*", r"baseline\w*", r"slakk\w*", r"treningsdata\w*", r"kutt\w*", r"kuttpunkt\w*",
            r"alder på", r"posisjonsalder\w*", r"offset\w*", r"forskyvning\w*", r"featur\w*", r"cos")
_BEGREP = re.compile(r"(?<!\w)(" + "|".join(BEGREPER) + r")(?!\w)", re.IGNORECASE)
# På rader Modell v1 har vurdert, er «vanlig avvik for skipsgruppen» ikke forklaringen (``metode``).
_VANLIG_SOM_METODE = re.compile(
    r"(bygger|baserer|hviler)\s+(seg\s+)?på\s+(det\s+)?vanlig\w*\s+avvik|vanlig\w*\s+avvik\s+for\s+(denne\s+)?skipsgruppen",
    re.IGNORECASE)
# Avstand, fart og retning gjelder siste AIS-posisjon, ikke nå (``begrunnelse-v8``, ``brief-v4``). Presens om dem
# avvises (``presens``): «er 212 km fra havna», «ligger 40 km unna», «går med 13,7 knop», «er på vei mot havna».
_PRESENS = re.compile(
    r"(?<!\w)(er|ligger)\s+(nå\s+)?(omtrent\s+|ca\.\s+)?\d[\d,]*\s*km(?!\w)"
    r"|(?<!\w)(går|seiler|holder)\s+(nå\s+)?(med\s+|i\s+)?\d[\d,]*\s*(knop|kn)(?!\w)"
    r"|(?<!\w)er\s+(nå\s+)?på\s+vei\s+(mot|bort)",
    re.IGNORECASE)
_TIDLIGERE = re.compile(r"(?<!\w)(" + "|".join(TIDLIGERE_ORD) + r")(?!\w)", re.IGNORECASE)


retning = _klartekst_retning  # fortegnet på konklusjonen (``klartekst.retning``)


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
    konklusjon: Optional[str] = None,
    modellrad: bool = False,
    maks_tegn: int = MAKS_TEGN,
    min_setninger: int = 1,
    maks_setninger: int = MAKS_SETNINGER,
) -> Optional[str]:
    """None når svaret godtas, ellers regelen som brytes. ``skipsnavn`` er standard alle navn i utdraget.

    ``retning`` (+1, −1, 0) er fortegnet på konklusjonen (``retning(prediksjon)``). Et retningsord godtas når det
    stemmer med fortegnet, eller når samme retning står i et faktafelt (for eksempel «senere enn vanlig» om skipets
    tidligere anløp). Med 0 og ingen retning i faktaene avvises begge. None hopper over regelen.

    ``konklusjon`` er innledningen appen har skrevet (``klartekst.innledning``: konklusjonen, og på baseline- og
    varselrader én setning til). Svaret må starte med den ordrett (``konklusjon``).

    ``modellrad`` er True når Modell v1 har vurdert raden selv. Da avvises «vanlig avvik for skipsgruppen» som
    forklaring (``metode``), fordi det er baselinens metode, ikke modellens.

    ``maks_tegn``, ``min_setninger`` og ``maks_setninger`` er grensene for lengden. Standard er begrunnelsens
    (høyst 400 tegn og 3 setninger). Briefen (E3-S05) bruker 700 tegn og 3–5 setninger."""
    tekst = (tekst or "").strip()
    if not tekst:
        return "tom"
    if konklusjon is not None and not re.sub(r"\s+", " ", tekst).startswith(re.sub(r"\s+", " ", konklusjon.strip())):
        return "konklusjon"
    if len(tekst) > maks_tegn:
        return "lengde"
    if not min_setninger <= antall_setninger(tekst) <= maks_setninger:
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
    if _BEGREP.search(tekst):
        return "begrep"
    if _PRESENS.search(tekst):
        return "presens"
    if modellrad and _VANLIG_SOM_METODE.search(tekst):
        return "metode"
    if _AARSAK.search(tekst):
        return "aarsak"
    if forventet_forsinket is not True and _FORSINK.search(tekst):
        return "forsink"
    if retning is not None:
        senere_lov = retning > 0 or bool(_SENERE.search(verdier))
        tidligere_lov = retning < 0 or bool(_TIDLIGERE.search(verdier))
        if (not senere_lov and _SENERE.search(tekst)) or (not tidligere_lov and _TIDLIGERE.search(tekst)):
            return "retning"
    return None
