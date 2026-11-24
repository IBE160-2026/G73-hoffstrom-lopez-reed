"""Testmodus: deterministisk mal-tekst for begrunnelsen (E3-S01, PRD FR13).

Malen bygges bare fra ``PrediksjonsInput`` og ``Prediksjon`` og rører aldri nettet. Den brukes i testmodus og som
tilbakefall i ekte modus.

Opptak av ekte svar (E3-S06): ``scripts/ta_opp_begrunnelser.py`` kjører ekte modus én gang for demovinduet og skriver
de godkjente svarene til ``data/begrunnelser_opptak.json``. I testmodus viser appen et opptak når det finnes og fortsatt
passer (``opptak_for``), ellers malen. Fila leses én gang per prosess og skrives aldri av appen.

På baselinen, og for rader modellen har delegert til baselinen, påstår teksten aldri at et avvik er ventet (FR11).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import threading
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Tuple

from app.begrunnelse.klartekst import DELEGERT_KLARTEKST, brief_innledning, innledning

MERKE_TEST = "Testmodus"
MERKE_FEILET = "Testmodus (ekte kall feilet)"
MERKE_GRENSE = "Testmodus (kallgrensen er nådd)"
MERKE_KI = "KI-GENERERT"
MERKE_APP = "Laget av appen"  # briefen uten varsler eller på baselinen (E3-S05, spec-valg B1)
MERKE_OPPTAK = "Testmodus (opptak av ekte svar)"  # E3-S06, spec-valg O2: vises med datoen for opptaket

VARSEL_GRENSE_MIN = 120  # beslutning 06, A3: varsel når predikert avvik er over 120 min

GRUPPE_TEKST = {"Passasjer": "passasjerskip", "Øvrige": "øvrige (ikke-rutegående) skip"}


def mal(inp, prediksjon) -> str:
    """Mal-teksten for ett anløp (``begrunnelse-v5``): innledningen appen skriver (konklusjonen, og på baseline- og
    varselrader én setning til), så én setning i vanlig språk. Høyst 3 setninger, og den består kontrollen."""
    f = prediksjon.forklaring
    start = innledning(inp, prediksjon)
    if f.get("metode") == "modell":
        if prediksjon.forventet_forsinket is True:
            return f"{start} Det er over varselgrensen på {VARSEL_GRENSE_MIN} min."
        return f"{start} Modellen vurderer anløpet som under varselgrensen på {VARSEL_GRENSE_MIN} min."
    grunn = DELEGERT_KLARTEKST.get(f.get("delegert"))
    if grunn:
        return f"{start} Modellen vurderer ikke anløpet ({grunn})."
    return f"{start} Beregningen kan ikke varsle avvik."


# --- Forstyrrelsesbriefen (E3-S05, PRD FR12) -------------------------------------------------------------------

BRIEF_MAL_SLUTT = "Skipsnavnet i lista åpner forklaringen for hvert anløp."


def brief_mal(valgte, antall_varsler: int) -> str:
    """Mal-briefen med varsler (``brief-v1``, spec-valg B2): innledningen appen skriver, og én fast setning.
    3 setninger, og den består kontrollen."""
    return f"{brief_innledning(valgte, antall_varsler)} {BRIEF_MAL_SLUTT}"


def _antall(n: int, entall: str, flertall: str) -> str:
    return f"{n} {entall if n == 1 else flertall}"


def app_brief(par) -> str:
    """Briefen appen skriver uten varsler, eller når baselinen er aktiv (spec-valg B1). Tre setninger: antall anløp
    i vinduet, hvor mange modellen har vurdert, og hvorfor resten ikke er vurdert (gruppert etter
    ``DELEGERT_KLARTEKST``). Ingen kall, i begge modusene."""
    forklaringer = [p.forklaring for _, p in par]
    modell = sum(1 for f in forklaringer if f.get("metode") == "modell")
    delegert = Counter(f["delegert"] for f in forklaringer if f.get("delegert"))
    forste = f"{len(par)} anløp har rapportert ETA i vinduet."
    if not modell and not delegert:  # baselinen er aktiv
        return (f"{forste} Modellen har ikke vurdert noen av dem, og ingen har varsel. "
                "Tidene bygger bare på vanlig avvik for skipsgruppen, og den beregningen kan ikke varsle.")
    andre = f"Modellen har vurdert {modell} av dem, og ingen har varsel."
    if not delegert:
        return f"{forste} {andre} Alle anløpene er vurdert av modellen."
    rekkefolge = list(DELEGERT_KLARTEKST) + sorted(k for k in delegert if k not in DELEGERT_KLARTEKST)
    grunner = [f"{DELEGERT_KLARTEKST.get(k, 'ukjent grunn')} ({_antall(delegert[k], 'anløp', 'anløp')})"
               for k in rekkefolge if k in delegert]
    liste = grunner[0] if len(grunner) == 1 else f"{', '.join(grunner[:-1])} og {grunner[-1]}"
    if not modell:  # Modell v1 er aktiv, men har delegert alle radene
        return f"{forste} Modellen har ikke vurdert noen av dem, og ingen har varsel. Grunnene er: {liste}."
    resten = sum(delegert.values())
    return f"{forste} {andre} {'Det andre anløpet' if resten == 1 else f'De {resten} andre'} er ikke vurdert: {liste}."


# --- Opptak av ekte svar (E3-S06, PRD FR13) --------------------------------------------------------------------
#
# Hver oppføring har nøkkelen (vindu, seilas eller «brief», prediktor) og lagrer prompt-versjonen, modellstrengen,
# tidspunktet for opptaket og SHA-256 av faktaene som ble sendt. Et opptak brukes bare når nøkkelen, prompt-versjonen
# og faktahashen stemmer. Ellers vises malen. Manglende eller ugyldig fil gir malen og én advarsel per prosess.

logger = logging.getLogger("app.begrunnelse")

OPPTAK_FIL = Path(__file__).resolve().parents[2] / "data" / "begrunnelser_opptak.json"
OPPTAK_FORMAT = 1
BRIEF_NOKKEL = "brief"
_OPPTAK_FELT = ("naa", "anlop", "prediktor", "prompt_versjon", "modell", "tatt_opp", "fakta_sha256", "tekst")

_opptak_laas = threading.Lock()
_opptak: Optional[Dict[tuple, dict]] = None  # None = ikke lest ennå


def fakta_hash(fakta: Mapping[str, str]) -> str:
    """SHA-256 av faktaene som sortert JSON i UTF-8 (``lag_fakta`` / ``lag_brief_fakta``)."""
    tekst = json.dumps(dict(fakta), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()


def opptak_nokkel(naa, anlop, prediktor_navn: str) -> tuple:
    """(vindu, seilas eller «brief», prediktor). ``naa`` er et tidspunkt eller en ISO-streng."""
    return (naa if isinstance(naa, str) else naa.isoformat(), anlop, prediktor_navn)


def _gyldig(oppforing) -> bool:
    if not isinstance(oppforing, dict):
        return False
    if any(not isinstance(oppforing.get(f), str) for f in _OPPTAK_FELT if f != "anlop"):
        return False
    anlop = oppforing.get("anlop")
    return anlop == BRIEF_NOKKEL or (isinstance(anlop, int) and not isinstance(anlop, bool))


def les_opptak(fil: Optional[Path] = None) -> Dict[tuple, dict]:
    """Oppføringene i fila etter nøkkel. Manglende eller ugyldig fil gir {} (``ValueError``/``OSError`` fanges)."""
    data = json.loads(Path(fil or OPPTAK_FIL).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("opptak"), list):
        raise ValueError("opptaksfila mangler lista «opptak»")
    return {opptak_nokkel(o["naa"], o["anlop"], o["prediktor"]): o for o in data["opptak"] if _gyldig(o)}


def _alle_opptak() -> Dict[tuple, dict]:
    global _opptak
    with _opptak_laas:
        if _opptak is None:
            try:
                _opptak = les_opptak()
            except (OSError, ValueError) as feil:
                logger.warning("opptak: ingen opptak brukes (%s)", type(feil).__name__)
                _opptak = {}
        return _opptak


def nullstill_opptak() -> None:
    """Glem fila, så den leses på nytt ved neste oppslag (testene)."""
    global _opptak
    with _opptak_laas:
        _opptak = None


def tatt_opp_dato(tidspunkt: str) -> str:
    """«24.11.2026» (norsk tid) fra ISO-tidspunktet i oppføringen."""
    from app.visning import OSLO

    t = dt.datetime.fromisoformat(tidspunkt)
    if t.tzinfo is not None:
        t = t.astimezone(OSLO)
    return t.strftime("%d.%m.%Y")


def opptak_for(naa, anlop, prediktor_navn: str, fakta: Callable[[], Mapping[str, str]],
               prompt_versjon: str) -> Optional[Tuple[str, str]]:
    """(tekst, dato) for et opptak som fortsatt passer, ellers None.

    Opptaket må ha samme nøkkel, samme prompt-versjon og samme faktahash. ``fakta`` kalles bare når nøkkelen finnes."""
    oppforing = _alle_opptak().get(opptak_nokkel(naa, anlop, prediktor_navn))
    if oppforing is None:
        return None
    if oppforing["prompt_versjon"] != prompt_versjon:
        return None
    if oppforing["fakta_sha256"] != fakta_hash(fakta()):
        return None
    try:
        dato = tatt_opp_dato(oppforing["tatt_opp"])
    except ValueError:
        return None
    return oppforing["tekst"], dato
