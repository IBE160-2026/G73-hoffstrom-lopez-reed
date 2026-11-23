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


def _tider(prediksjon, eta):
    """(«kl. 17:44», «16:30»), med ukedag på begge når de er på ulike dager («lør kl. 00:44», «fre 23:30»)."""
    pred, rapp = til_oslo_minutt(prediksjon.predikert_ankomst), til_oslo_minutt(eta)
    if pred.date() == rapp.date():
        return f"kl. {pred:%H:%M}", f"{rapp:%H:%M}"
    dag_p, klokke_p = ukedag_klokke(prediksjon.predikert_ankomst).split(" ")
    return f"{dag_p} kl. {klokke_p}", ukedag_klokke(eta)


def konklusjon(inp, prediksjon) -> str:
    """Første setning. Tiden gjelder havneområdet, ikke kai (beslutning 03), f.eks.
    «Ventes inn i havneområdet kl. 17:44, 74 min etter rapportert ETA (16:30).»"""
    avvik = avvik_mot_eta_min(prediksjon)
    pred, rapp = _tider(prediksjon, inp.eta_reported)
    if avvik is None or avvik == 0:
        return f"Ventes inn i havneområdet {pred}, omtrent ved rapportert ETA ({rapp})."
    ord_ = "etter" if avvik > 0 else "før"
    return f"Ventes inn i havneområdet {pred}, {varighet(avvik)} {ord_} rapportert ETA ({rapp})."


def er_modellvurdert(prediksjon) -> bool:
    """Modell v1 har vurdert raden selv (ikke delegert til baselinen)."""
    return prediksjon.forklaring.get("metode") == "modell"


def innledning(inp, prediksjon) -> str:
    """Setningene appen skriver, og som svaret må starte med ordrett.

    - Alle rader: konklusjonen.
    - Baselinen og delegerte rader: «Det er vanlig for denne skipsgruppen.»
    - Varselrader: avviket fra det som er vanlig for skipsgruppen, som er det som gir varselet,
      f.eks. «Det er 138 min senere enn vanlig for skipsgruppen.»
    """
    deler = [konklusjon(inp, prediksjon)]
    f = prediksjon.forklaring
    if not er_modellvurdert(prediksjon):
        deler.append("Det er vanlig for denne skipsgruppen.")
    elif prediksjon.forventet_forsinket is True and f.get("predikert_avvik_min") is not None:
        avvik = round(f["predikert_avvik_min"])
        ord_ = "senere" if avvik > 0 else "tidligere"
        deler.append(f"Det er {varighet(avvik)} {ord_} enn vanlig for skipsgruppen.")
    return " ".join(deler)


# --- Forstyrrelsesbriefen (E3-S05, PRD FR12) -------------------------------------------------------------------

BRIEF_MAKS_ANLOP = 3  # briefen tar med høyst så mange varslede anløp


def velg_varslede(par):
    """(valgte, antall_varsler) for briefen. ``par`` er (``PrediksjonsInput``, ``Prediksjon``) for vinduet.

    Bare anløp med ``forventet_forsinket is True``, sortert etter ``forklaring["predikert_avvik_min"]`` synkende
    (likt avvik: lavest seilas-ID først), og høyst ``BRIEF_MAKS_ANLOP``. ``antall_varsler`` er alle varslene."""
    varslede = [(inp, p) for inp, p in par if p.forventet_forsinket is True]
    varslede.sort(key=lambda ip: (-ip[1].forklaring.get("predikert_avvik_min", 0.0), ip[1].voyageid))
    return varslede[:BRIEF_MAKS_ANLOP], len(varslede)


def _brief_linje(inp, prediksjon) -> str:
    """«ODIN VIKING ventes inn i havneområdet fre kl. 12:31, 3 t 25 min senere enn vanlig for skipsgruppen»."""
    avvik = round(prediksjon.forklaring.get("predikert_avvik_min", 0.0))
    dag, klokkeslett = ukedag_klokke(prediksjon.predikert_ankomst).split(" ")
    if avvik == 0:
        sammenlignet = "omtrent som vanlig for skipsgruppen"
    else:
        sammenlignet = f"{varighet(avvik)} {'senere' if avvik > 0 else 'tidligere'} enn vanlig for skipsgruppen"
    return f"{inp.shipname} ventes inn i havneområdet {dag} kl. {klokkeslett}, {sammenlignet}"


def brief_innledning(valgte, antall_varsler: int) -> str:
    """Innledningen appen skriver i briefen (spec-valg B2), og som svaret må starte med ordrett. To setninger:
    antall varsler, og så navn, tid inn i havneområdet og avvik fra det vanlige for hvert anløp som er tatt med."""
    if antall_varsler > len(valgte):
        forste = f"{antall_varsler} anløp har varsel, og her er de {len(valgte)} med størst avvik."
    else:
        forste = f"{antall_varsler} anløp har varsel."
    return f"{forste} {'; '.join(_brief_linje(inp, p) for inp, p in valgte)}."
