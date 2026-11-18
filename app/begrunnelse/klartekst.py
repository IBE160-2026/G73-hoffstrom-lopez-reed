"""Konklusjonen i forhold til rapportert ETA, regnet ut i appen (E3-S03, ``begrunnelse-v4``).

Modellen skal ikke regne selv. ``konklusjon`` gir den første setningen ordrett, og kontrollen sjekker at svaret starter
med den. ``retning`` gir fortegnet setningen beskriver.

- **Modell v1:** predikert ankomst minus rapportert ETA.
- **Baselinen og rader modellen har delegert:** det faktiske fortegnet på forskyvningen for skipsgruppen
  (``predikert = rapportert ETA − offset``). En positiv offset gir «tidligere», en negativ gir «senere». Regelen
  antar ikke at offset er positiv.

Modulen avhenger bare av ``app.visning``, så både ``input`` og ``testmodus`` kan bruke den.
"""
from __future__ import annotations

from typing import Optional

from app.visning import til_oslo_minutt, ukedag_klokke

# Rader modellen ikke vurderer, i vanlig språk (uten «baseline»).
DELEGERT_KLARTEKST = {
    "passasjer": "rutegående skip vurderes ikke av modellen",
    "ingen_tilstand": "ingen AIS-posisjon å vurdere",
    "i_sonen_ved_kutt": "skipet var allerede i havneområdet",
    "ingen_featurerad": "ingen modelldata for anløpet",
}


def avvik_mot_eta_min(prediksjon) -> Optional[int]:
    """Predikert ankomst minus rapportert ETA i hele minutter. None uten ETA.

    Størrelsen regnes fra tidene slik de vises (avrundet til minutt), så tallet alltid stemmer med «17:44 mot 16:30».
    Fortegnet for baselinen og delegerte rader kommer fra forskyvningen (``−offset_minutter``)."""
    f = prediksjon.forklaring
    if f.get("eta_reported") is None:
        return None
    vist = round((til_oslo_minutt(prediksjon.predikert_ankomst) - til_oslo_minutt(f["eta_reported"]))
                 .total_seconds() / 60)
    if f.get("metode") != "modell" and f.get("offset_minutter") is not None:
        offset = f["offset_minutter"]
        fortegn = (offset < 0) - (offset > 0)
        return fortegn * abs(vist)
    return vist


def retning(prediksjon) -> Optional[int]:
    """+1 senere enn rapportert ETA, −1 tidligere, 0 omtrent likt, None ukjent."""
    avvik = avvik_mot_eta_min(prediksjon)
    if avvik is None:
        return None
    return (avvik > 0) - (avvik < 0)


def varighet(minutter: int) -> str:
    """«74 min» under 90 min, ellers «2 t 18 min» eller «3 t». Alltid positivt: fortegnet står i ordet."""
    m = abs(minutter)
    if m < 90:
        return f"{m} min"
    timer, rest = divmod(m, 60)
    return f"{timer} t {rest} min" if rest else f"{timer} t"


def _tidspar(prediksjon, eta) -> str:
    """«17:44 mot 16:30», med ukedag når de to tidene er på ulike dager."""
    pred, rapp = til_oslo_minutt(prediksjon.predikert_ankomst), til_oslo_minutt(eta)
    if pred.date() == rapp.date():
        return f"{pred:%H:%M} mot {rapp:%H:%M}"
    return f"{ukedag_klokke(prediksjon.predikert_ankomst)} mot {ukedag_klokke(eta)}"


def konklusjon(inp, prediksjon) -> str:
    """Første setning, f.eks. «Ventes 74 min senere enn rapportert ETA (17:44 mot 16:30).»"""
    avvik = avvik_mot_eta_min(prediksjon)
    tider = _tidspar(prediksjon, inp.eta_reported)
    if avvik is None or avvik == 0:
        return f"Ventes omtrent ved rapportert ETA ({tider})."
    ord_ = "senere" if avvik > 0 else "tidligere"
    return f"Ventes {varighet(avvik)} {ord_} enn rapportert ETA ({tider})."
