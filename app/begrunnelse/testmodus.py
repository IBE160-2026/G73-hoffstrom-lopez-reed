"""Testmodus: deterministisk mal-tekst for begrunnelsen (E3-S01, PRD FR13).

Malen bygges bare fra ``PrediksjonsInput`` og ``Prediksjon`` og rører aldri nettet. Den brukes i testmodus og som
tilbakefall i ekte modus. Opptak av ekte svar for demovinduene kommer i E3-S06.

På baselinen, og for rader modellen har delegert til baselinen, påstår teksten aldri at et avvik er ventet (FR11).
"""
from __future__ import annotations

from app.begrunnelse.klartekst import DELEGERT_KLARTEKST, innledning

MERKE_TEST = "Testmodus"
MERKE_FEILET = "Testmodus (ekte kall feilet)"
MERKE_GRENSE = "Testmodus (kallgrensen er nådd)"
MERKE_KI = "KI-GENERERT"

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
