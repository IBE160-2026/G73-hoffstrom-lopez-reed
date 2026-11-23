"""Testmodus: deterministisk mal-tekst for begrunnelsen (E3-S01, PRD FR13).

Malen bygges bare fra ``PrediksjonsInput`` og ``Prediksjon`` og rører aldri nettet. Den brukes i testmodus og som
tilbakefall i ekte modus. Opptak av ekte svar for demovinduene kommer i E3-S06.

På baselinen, og for rader modellen har delegert til baselinen, påstår teksten aldri at et avvik er ventet (FR11).
"""
from __future__ import annotations

from collections import Counter

from app.begrunnelse.klartekst import DELEGERT_KLARTEKST, brief_innledning, innledning

MERKE_TEST = "Testmodus"
MERKE_FEILET = "Testmodus (ekte kall feilet)"
MERKE_GRENSE = "Testmodus (kallgrensen er nådd)"
MERKE_KI = "KI-GENERERT"
MERKE_APP = "Laget av appen"  # briefen uten varsler eller på baselinen (E3-S05, spec-valg B1)

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
