"""Testmodus: deterministisk mal-tekst for begrunnelsen (E3-S01, PRD FR13).

Malen bygges bare fra ``PrediksjonsInput`` og ``Prediksjon`` og rører aldri nettet. Den brukes i testmodus og som
tilbakefall i ekte modus. Opptak av ekte svar for demovinduene kommer i E3-S06.

På baselinen, og for rader modellen har delegert til baselinen, påstår teksten aldri at et avvik er ventet (FR11).
"""
from __future__ import annotations

from app.begrunnelse.klartekst import DELEGERT_KLARTEKST, konklusjon
from app.visning import tall

MERKE_TEST = "Testmodus"
MERKE_FEILET = "Testmodus (ekte kall feilet)"
MERKE_GRENSE = "Testmodus (kallgrensen er nådd)"
MERKE_KI = "KI-GENERERT"

VARSEL_GRENSE_MIN = 120  # beslutning 06, A3: varsel når predikert avvik er over 120 min

GRUPPE_TEKST = {"Passasjer": "passasjerskip", "Øvrige": "øvrige (ikke-rutegående) skip"}


def mal(inp, prediksjon) -> str:
    """Mal-teksten for ett anløp (``begrunnelse-v4``): konklusjonen i forhold til rapportert ETA, så én setning i
    vanlig språk. Samme form og grenser som et ekte svar, og den består kontrollen."""
    f = prediksjon.forklaring
    start = konklusjon(inp, prediksjon)
    if f.get("metode") == "modell":
        avvik = round(f["predikert_avvik_min"])
        if prediksjon.forventet_forsinket is True:
            return (f"{start} Modellen venter {tall(abs(avvik), 0)} min mer enn vanlig for skipsgruppen, "
                    f"over varselgrensen på {VARSEL_GRENSE_MIN} min.")
        return f"{start} Modellen vurderer anløpet som under varselgrensen på {VARSEL_GRENSE_MIN} min."
    grunn = DELEGERT_KLARTEKST.get(f.get("delegert"))
    if grunn:
        return f"{start} Modellen vurderer ikke anløpet ({grunn}), så tiden bygger på vanlig avvik for skipsgruppen."
    return f"{start} Tiden bygger på vanlig avvik for skipsgruppen, og beregningen kan ikke varsle."
