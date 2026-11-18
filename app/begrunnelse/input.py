"""Input til språkmodellen, bygd bare fra modellens egne data (E3-S02, PRD FR11, beslutning 13).

``lag_fakta`` tar ``PrediksjonsInput`` + ``Prediksjon`` og gir en ordnet dict med norske etiketter og verdier
formatert som på skjermen (tider i norsk tid, avrundet til minutt). Tallkontrollen (``kontroll.py``) sjekker
tallene i svaret mot nøyaktig disse verdiene.

Det som sendes: skipsnavn, skipsgruppe, tider, horisont, metode, offset eller predikert avvik, varseltilstand,
grunnen til delegering og modellens featureverdier. Det som aldri sendes: MMSI, seilas-ID og fasit
(``faktisk_ankomst``, ``status_in_area``, ``split``), som verken ``PrediksjonsInput`` eller ``Prediksjon`` har.
"""
from __future__ import annotations

from typing import Dict

from app.begrunnelse.testmodus import VARSEL_GRENSE_MIN
from app.prediksjon import Prediksjon, PrediksjonsInput
from app.visning import DELEGERT_TEKST, gruppe_visning, horisont_etikett, tall, ukedag_dato_klokke

# Featurene som sendes, med etikett og antall desimaler. Sykliske koder (sin/cos for time og måned), ukedag,
# posisjon og F6 sendes ikke: de er uleselige som tall, eller står allerede i inputen (F6 er alltid 0 for rader
# modellen vurderer, beslutning 12).
FEATURE_ETIKETT = {
    "distanse_km": ("Distanse til havna (km)", 0),
    "fart_knop": ("Fart over grunn (knop)", 1),
    "kurs_mot_havn": ("Kurs mot havna (1 = rett mot, −1 = rett bort)", 2),
    "posisjon_alder_min": ("Alder på siste AIS-posisjon (min)", 0),
    "slakk_timer": ("Slakk mot rapportert ETA med farten nå (timer)", 1),
    "skipstype": ("Skipstype", None),
    "lengde_m": ("Lengde (m)", 0),
    "avgangshavn": ("Avgangshavn", None),
    "avgatt_for_kutt": ("Avgått før kuttet", None),
    "timer_siden_avgang": ("Timer siden avgang", 1),
    "fartoy_snittavvik_min": ("Fartøyets historiske snittavvik (min)", 0),
    "fartoy_antall_tidligere": ("Fartøyets tidligere anløp i treningsdata", 0),
}

METODE_NAVN = {"kalibrert_baseline": "Kalibrert baseline", "modell": "Modell v1"}


def _feature(navn: str, verdi) -> str:
    _, desimaler = FEATURE_ETIKETT[navn]
    if navn == "avgatt_for_kutt":
        return "ja" if verdi else "nei"
    if desimaler is None:
        return str(verdi)
    return tall(float(verdi), desimaler)


def _varsel(prediksjon: Prediksjon) -> str:
    f = prediksjon.forklaring
    if f.get("delegert"):
        return "ingen (modellen vurderer ikke anløpet)"
    if f.get("metode") != "modell":
        return "ingen (baselinen kan ikke varsle)"
    if prediksjon.forventet_forsinket is True:
        return f"ja, predikert avvik over {VARSEL_GRENSE_MIN} min"
    return f"nei, predikert avvik ikke over {VARSEL_GRENSE_MIN} min"


def lag_fakta(inp: PrediksjonsInput, prediksjon: Prediksjon) -> Dict[str, str]:
    """Faktaene om ett anløp som sendes til språkmodellen. Bare tekst, ferdig formatert."""
    if not isinstance(inp, PrediksjonsInput):
        raise TypeError(f"lag_fakta() tar PrediksjonsInput, ikke {type(inp).__name__}")
    if not isinstance(prediksjon, Prediksjon):
        raise TypeError(f"lag_fakta() tar Prediksjon, ikke {type(prediksjon).__name__}")
    if prediksjon.voyageid != inp.voyageid:
        raise ValueError("prediksjonen hører til en annen seilas enn inputen")
    f = prediksjon.forklaring
    fakta = {
        "Skip": inp.shipname,
        "Skipsgruppe": gruppe_visning(inp.ship_group).replace("­", ""),
        "Gruppe": inp.gruppe,
        "Rapportert ETA (norsk tid)": ukedag_dato_klokke(inp.eta_reported),
        "Predikert ankomst (norsk tid)": ukedag_dato_klokke(prediksjon.predikert_ankomst),
        "Horisont": horisont_etikett(inp.horisont_timer),
        "Kuttpunkt for dataene (norsk tid)": ukedag_dato_klokke(inp.t_kutt),
        "Metode": METODE_NAVN.get(f.get("metode"), str(f.get("metode"))),
    }
    if f.get("metode") == "modell":
        fakta["Predikert avvik fra kalibrert baseline (min)"] = tall(f["predikert_avvik_min"], 0)
        fakta["Kalibrert baseline for øvrige: rapportert ETA minus (min)"] = tall(f["offset_ovrige_min"], 1)
        fakta["Varselgrense (min)"] = str(VARSEL_GRENSE_MIN)
    elif f.get("offset_minutter") is not None:
        fakta["Fast forskyvning: median tid fra sonegrense til kai for gruppen (min)"] = tall(
            f["offset_minutter"], 1)
    fakta["Varsel"] = _varsel(prediksjon)
    if f.get("delegert"):
        fakta["Hvorfor Modell v1 ikke vurderer anløpet"] = DELEGERT_TEKST.get(f["delegert"], f["delegert"])
    for navn, verdi in (f.get("featurer") or {}).items():
        if navn in FEATURE_ETIKETT and verdi is not None:
            fakta[FEATURE_ETIKETT[navn][0]] = _feature(navn, verdi)
    return fakta
