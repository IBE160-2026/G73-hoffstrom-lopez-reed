"""Input til språkmodellen, bygd bare fra modellens egne data (E3-S02, PRD FR11, beslutning 13).

``lag_fakta`` tar ``PrediksjonsInput`` + ``Prediksjon`` og gir en ordnet dict med norske etiketter og verdier
formatert som på skjermen (tider i norsk tid, avrundet til minutt). Tallkontrollen (``kontroll.py``) sjekker
tallene i svaret mot nøyaktig disse verdiene.

Det som sendes (``begrunnelse-v4``): konklusjonen i forhold til rapportert ETA (regnet ut i appen), skipsnavn,
skipsgruppe, tider, metode, vanlig avvik for skipsgruppen, modellens vurdering, varseltilstand, grunnen til delegering,
og tilstanden ved siste posisjon i vanlig språk: avstand, fart, retning mot eller bort fra havna, om skipet rekker fram,
avgang og skipets tidligere anløp. Interne begreper (kalibrert baseline, slakk, treningsdata, kuttpunkt, alder på
posisjonen, kurs som tall) sendes ikke. Det som aldri sendes: MMSI, seilas-ID og fasit
(``faktisk_ankomst``, ``status_in_area``, ``split``), som verken ``PrediksjonsInput`` eller ``Prediksjon`` har.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Dict, Optional

from app.begrunnelse.klartekst import DELEGERT_KLARTEKST, brief_innledning, innledning
from app.begrunnelse.kontroll import BRIEF_MAKS_SETNINGER, MAKS_SETNINGER, antall_setninger
from app.begrunnelse.testmodus import VARSEL_GRENSE_MIN
from app.prediksjon import VINDU_TIMER, Prediksjon, PrediksjonsInput
from app.prediksjon.features import MIN_FART_KN, SLAKK_MIN_TIMER
from app.visning import gruppe_visning, tall, ukedag_dato_klokke

def _retning_mot_havna(kurs_cos: float) -> str:
    """F3 er cos(kurs − peiling til havna): over 0 betyr at avstanden minker (farten har en komponent mot havna),
    under 0 at den øker, og 0 at skipet går på tvers. Tersklene følger av definisjonen i ``features.kurs_mot_havn``."""
    if kurs_cos > 0:
        return "på vei mot havna"
    if kurs_cos < 0:
        return "på vei bort fra havna"
    return "på tvers av retningen til havna"


def _ca_timer(timer: float) -> str:
    """Timer avrundet til hele tall (halve opp): «ca. 42 timer», «ca. 1 time», og «under 1 time» under en halv."""
    hele = math.floor(timer + 0.5)
    if hele == 0:
        return "under 1 time"
    return f"ca. {hele} time" if hele == 1 else f"ca. {hele} timer"


def _rekker_fram(slakk: float, h_eff: float) -> Optional[str]:
    """F7 er (rapportert ETA − kuttet) minus seilingstiden med farten da, klippet til [−48, h_eff] timer."""
    if slakk >= h_eff:  # distanse 0: ingen seilingstid å regne på
        return None
    if slakk <= SLAKK_MIN_TIMER:
        return "nei, minst 48 timer etter rapportert ETA"
    if slakk >= 0:
        return f"ja, {_ca_timer(slakk)} før rapportert ETA"
    return f"nei, {_ca_timer(-slakk)} etter rapportert ETA"


def _vanlig(offset: float) -> str:
    """«64 min før rapportert ETA», med det faktiske fortegnet på forskyvningen."""
    if round(offset) == 0:
        return "omtrent ved rapportert ETA"
    return f"{tall(abs(offset), 0)} min {'før' if offset > 0 else 'etter'} rapportert ETA"


def _sammenlignet_med_vanlig(avvik: float) -> str:
    if round(avvik) == 0:
        return "omtrent som vanlig for skipsgruppen"
    return f"{tall(abs(avvik), 0)} min {'senere' if avvik > 0 else 'tidligere'} enn vanlig for skipsgruppen"


def _varsel(prediksjon: Prediksjon) -> str:
    f = prediksjon.forklaring
    if f.get("delegert"):
        return "ingen (modellen vurderer ikke anløpet)"
    if f.get("metode") != "modell":
        return "ingen (beregningen bygger bare på vanlig avvik for skipsgruppen og kan ikke varsle)"
    # Uten retningsord: et «senere» her ville gjort «senere» lovlig i svaret på alle modellrader (kontroll ``retning``).
    if prediksjon.forventet_forsinket is True:
        return f"ja, over varselgrensen på {VARSEL_GRENSE_MIN} min mer enn vanlig for skipsgruppen"
    return f"nei, under varselgrensen på {VARSEL_GRENSE_MIN} min mer enn vanlig for skipsgruppen"


def _tilstand(inp: PrediksjonsInput, featurer: dict) -> Dict[str, str]:
    """Posisjon, fart, retning og om skipet rekker fram, i vanlig språk. Ingen kursverdi eller slakk som tall."""
    ut: Dict[str, str] = {}
    alder = featurer.get("posisjon_alder_min")
    if alder is not None:
        ut["Siste AIS-posisjon"] = ukedag_dato_klokke(inp.t_kutt - dt.timedelta(minutes=alder))
    if featurer.get("distanse_km") is not None:
        ut["Avstand til havna"] = f"{tall(featurer['distanse_km'], 0)} km"
    fart = featurer.get("fart_knop")
    if fart is not None:
        ut["Fart"] = "nesten stille (under 1 knop)" if fart < MIN_FART_KN else f"{tall(fart, 1)} knop"
    if featurer.get("kurs_mot_havn") is not None:
        ut["Retning"] = _retning_mot_havna(featurer["kurs_mot_havn"])
    if featurer.get("slakk_timer") is not None and fart is not None and fart >= MIN_FART_KN:
        h_eff = (inp.eta_reported - inp.t_kutt).total_seconds() / 3600
        rekker = _rekker_fram(featurer["slakk_timer"], h_eff)
        if rekker:
            ut["Rekker fram til rapportert ETA med farten ved siste posisjon"] = rekker
    havn = featurer.get("avgangshavn")
    # F13–F14 er rapportert avgangshavn og ETD. De kunne ikke verifiseres historisk (beslutning 11), så de sendes som
    # registrert informasjon, ikke som et sikkert faktum. F14 er regnet ved kuttet, som vises som et tidspunkt.
    tidspunkt = ukedag_dato_klokke(inp.t_kutt)
    if featurer.get("avgatt_for_kutt") is not None and havn and havn != "annet":
        if featurer["avgatt_for_kutt"]:
            timer = featurer.get("timer_siden_avgang")
            ut["Avgang"] = (f"avgang fra {havn} var registrert {_ca_timer(timer)} før {tidspunkt}"
                            if timer is not None else f"avgang fra {havn} var registrert per {tidspunkt}")
        else:
            ut["Avgang"] = f"avgang fra {havn} var ikke registrert per {tidspunkt}"
    n = featurer.get("fartoy_antall_tidligere")
    snitt = featurer.get("fartoy_snittavvik_min")
    if n and snitt is not None:
        ut["Skipets tidligere anløp"] = (f"{tall(n, 0)} anløp, i snitt omtrent "
                                         f"{_sammenlignet_med_vanlig(snitt)}")
    return ut


def lag_fakta(inp: PrediksjonsInput, prediksjon: Prediksjon) -> Dict[str, str]:
    """Faktaene om ett anløp som sendes til språkmodellen, i vanlig språk (``begrunnelse-v4``).

    Konklusjonen i forhold til rapportert ETA er regnet ut her (``klartekst.konklusjon``), så modellen ikke regner
    selv. Interne begreper (kalibrert baseline, slakk, treningsdata, kuttpunkt, alder på posisjonen, kurs som tall)
    er oversatt før de sendes."""
    if not isinstance(inp, PrediksjonsInput):
        raise TypeError(f"lag_fakta() tar PrediksjonsInput, ikke {type(inp).__name__}")
    if not isinstance(prediksjon, Prediksjon):
        raise TypeError(f"lag_fakta() tar Prediksjon, ikke {type(prediksjon).__name__}")
    if prediksjon.voyageid != inp.voyageid:
        raise ValueError("prediksjonen hører til en annen seilas enn inputen")
    f = prediksjon.forklaring
    fakta = {
        "Innledning (skriv ordrett først)": innledning(inp, prediksjon),
        "Setninger du kan legge til": str(max(MAKS_SETNINGER - antall_setninger(innledning(inp, prediksjon)), 0)),
        "Skip": inp.shipname,
        "Skipsgruppe": gruppe_visning(inp.ship_group).replace("\u00ad", ""),
        "Rapportert ETA": ukedag_dato_klokke(inp.eta_reported),
        "Ventet ankomst": ukedag_dato_klokke(prediksjon.predikert_ankomst),
    }
    if f.get("metode") == "modell":
        fakta["Metode"] = "modellvurdering av skipets posisjon, fart og tidligere anløp"
        fakta["Vanlig avvik for skipsgruppen"] = _vanlig(f["offset_ovrige_min"])
        fakta["Modellens vurdering"] = _sammenlignet_med_vanlig(f["predikert_avvik_min"])
    else:
        fakta["Metode"] = "vanlig avvik for denne skipsgruppen"
        if f.get("offset_minutter") is not None:
            fakta["Vanlig avvik for skipsgruppen"] = _vanlig(f["offset_minutter"])
    fakta["Varsel"] = _varsel(prediksjon)
    if f.get("delegert"):
        fakta["Hvorfor modellen ikke vurderer anløpet"] = DELEGERT_KLARTEKST.get(f["delegert"], "ukjent grunn")
    fakta.update(_tilstand(inp, f.get("featurer") or {}))
    return fakta


# Feltene fra ``lag_fakta`` som ikke gjelder briefen (briefen har sin egen innledning og sitt eget antall setninger).
_BARE_BEGRUNNELSE = ("Innledning (skriv ordrett først)", "Setninger du kan legge til")


def lag_brief_fakta(par, naa: dt.datetime, valgte, antall_varsler: int) -> Dict[str, str]:
    """Faktaene til briefen (``brief-v1``, E3-S05): et hode for vinduet og ``lag_fakta`` for hvert anløp som er tatt
    med, med nummerert prefiks («Anløp 1 – Skip»). ``par`` er alle (``PrediksjonsInput``, ``Prediksjon``) i vinduet,
    og ``valgte`` er de varslede anløpene briefen tar med (``klartekst.velg_varslede``). Ingen fasit, MMSI eller
    seilas-ID, og ingen andre skip enn de som er tatt med."""
    for inp, p in par:
        if not isinstance(inp, PrediksjonsInput) or not isinstance(p, Prediksjon):
            raise TypeError("lag_brief_fakta() tar par av PrediksjonsInput og Prediksjon")
    start = brief_innledning(valgte, antall_varsler)
    slutt = naa.astimezone(dt.timezone.utc) + dt.timedelta(hours=VINDU_TIMER)
    fakta = {
        "Innledning (skriv ordrett først)": start,
        "Setninger du kan legge til": str(max(BRIEF_MAKS_SETNINGER - antall_setninger(start), 0)),
        "Vindu": f"{ukedag_dato_klokke(naa)} – {ukedag_dato_klokke(slutt)}",
        "Anløp i vinduet": str(len(par)),
        "Vurdert av modellen": str(sum(1 for _, p in par if p.forklaring.get("metode") == "modell")),
        "Anløp med varsel": str(antall_varsler),
    }
    for nr, (inp, p) in enumerate(valgte, 1):
        fakta[f"Anløp {nr} – Konklusjon"] = innledning(inp, p)
        for k, v in lag_fakta(inp, p).items():
            if k not in _BARE_BEGRUNNELSE:
                fakta[f"Anløp {nr} – {k}"] = v
    return fakta
