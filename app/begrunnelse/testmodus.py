"""Testmodus: deterministisk mal-tekst for begrunnelsen (E3-S01, PRD FR13).

Malen bygges bare fra ``PrediksjonsInput`` og ``Prediksjon`` og rører aldri nettet. Den brukes i testmodus og som
tilbakefall i ekte modus. Opptak av ekte svar for demovinduene kommer i E3-S06.

På baselinen, og for rader modellen har delegert til baselinen, påstår teksten aldri at et avvik er ventet (FR11).
"""
from __future__ import annotations

from app.visning import DELEGERT_TEKST, horisont_etikett, tall, ukedag_dato_klokke

MERKE_TEST = "Testmodus"
MERKE_FEILET = "Testmodus (ekte kall feilet)"
MERKE_GRENSE = "Testmodus (kallgrensen er nådd)"
MERKE_KI = "KI-GENERERT"

VARSEL_GRENSE_MIN = 120  # beslutning 06, A3: varsel når predikert avvik er over 120 min

GRUPPE_TEKST = {"Passasjer": "passasjerskip", "Øvrige": "øvrige (ikke-rutegående) skip"}


def _baseline_setning(prediksjon) -> str:
    f = prediksjon.forklaring
    offset = f.get("offset_minutter")
    gruppe = GRUPPE_TEKST.get(f.get("gruppe"), "gruppen")
    if offset is None:
        return "Prediksjonen er kalibrert baseline."
    return (f"Prediksjonen er kalibrert baseline: rapportert ETA minus {tall(offset, 1)} min, "
            f"som er median tid fra sonegrense til kai for {gruppe}.")


def mal(inp, prediksjon) -> str:
    """Mal-teksten for ett anløp. Høyst 3 setninger og under 400 tegn (samme grense som ekte svar)."""
    f = prediksjon.forklaring
    horisont = horisont_etikett(inp.horisont_timer)
    if f.get("metode") == "modell":
        avvik = f["predikert_avvik_min"]
        pred = ukedag_dato_klokke(prediksjon.predikert_ankomst)
        if prediksjon.forventet_forsinket is True:
            return (f"Modell v1 ({horisont}) venter at {inp.shipname} kommer {tall(avvik, 0)} min senere enn "
                    f"kalibrert baseline, over varselgrensen på {VARSEL_GRENSE_MIN} min. "
                    f"Predikert ankomst er {pred}, mot rapportert ETA {ukedag_dato_klokke(inp.eta_reported)}.")
        return (f"Modell v1 ({horisont}) predikerer {tall(avvik, 0)} min avvik fra kalibrert baseline for "
                f"{inp.shipname}, under varselgrensen på {VARSEL_GRENSE_MIN} min. Predikert ankomst er {pred}.")
    grunn = DELEGERT_TEKST.get(f.get("delegert"))
    if grunn:
        start = f"Modell v1 vurderer ikke {inp.shipname} ({grunn}), og det er ikke varslet avvik."
    else:
        start = (f"{inp.shipname} har rapportert ETA {ukedag_dato_klokke(inp.eta_reported)} og horisont "
                 f"{horisont}. Baselinen kan ikke varsle avvik.")
    return f"{start} {_baseline_setning(prediksjon)}"
