"""Prediktor-kontrakten (arkitektur §3, A5; E1-S04).

Prediktorer får aldri et ``Anlop``. De får en ``PrediksjonsInput``: en frossen verdi med
bare det som er kjent ved prediksjonstidspunktet (identitet, gruppe, rapportert ETA,
horisont og kuttpunkt). Den har ingen felt eller referanse som fører til fasiten
(``faktisk_ankomst``, ``status_in_area``, ``split``). ``lag_input`` er den eneste
koden i prediksjonslaget som rører datalaget.
"""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Protocol, Sequence

if TYPE_CHECKING:
    from app.data import Anlop

HORISONT_KORT = 6
HORISONT_LANG = 24
GYLDIGE_PREDIKTOR = ("auto", "baseline", "modell")


@dataclass(frozen=True)
class PrediksjonsInput:
    """Det en prediktor får vite om ett anløp. Ingen fasit, ingen vei til fasit."""

    voyageid: int
    mmsino: int
    shipname: str
    ship_group: str  # rå gruppe fra kilden (Tank, Last, Passasjer, …)
    gruppe: str  # «Passasjer» eller «Øvrige»
    eta_reported: dt.datetime  # rapportert ETA, UTC
    horisont_timer: int  # 6 eller 24, fra rapportert ETA − naa (PRD FR2)
    t_kutt: dt.datetime  # min(eta_reported − H, naa), UTC (FR9a)


@dataclass(frozen=True)
class Prediksjon:
    voyageid: int
    horisont_timer: int  # 6 eller 24, valgt fra rapportert ETA − naa (PRD FR2)
    predikert_ankomst: dt.datetime  # UTC, tz-aware
    forventet_forsinket: Optional[bool]  # None = prediktoren kan ikke varsle (baseline)
    forklaring: dict  # input som ble brukt; vises på detaljsiden og mates til AI-laget (E3)


class Prediktor(Protocol):
    navn: str  # vises i prediktor-stripa, f.eks. «Kalibrert baseline»
    kan_varsle: bool

    def prediker(
        self, inputs: Sequence[PrediksjonsInput], naa: dt.datetime
    ) -> List[Prediksjon]: ...


def _til_utc(t: dt.datetime, navn: str) -> dt.datetime:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"{navn} må ha tidssone (tz-aware datetime)")
    return t.astimezone(dt.timezone.utc)


def lag_input(anlop: "Anlop", naa: dt.datetime) -> PrediksjonsInput:
    """Bygg prediktorens input fra et anløp. Den eneste grensen mot ``app.data``.

    Horisont: 6 t hvis ``eta − naa ≤ 6 t``, ellers 24 t. Kuttpunkt:
    ``min(eta − H, naa)``, så det aldri ligger etter «nå».
    """
    naa = _til_utc(naa, "naa")
    eta = _til_utc(anlop.eta_reported, "eta_reported")
    horisont = HORISONT_KORT if eta - naa <= dt.timedelta(hours=HORISONT_KORT) else HORISONT_LANG
    t_kutt = min(eta - dt.timedelta(hours=horisont), naa)
    return PrediksjonsInput(
        voyageid=anlop.voyageid,
        mmsino=anlop.mmsino,
        shipname=anlop.shipname,
        ship_group=anlop.ship_group,
        gruppe=anlop.gruppe,
        eta_reported=eta,
        horisont_timer=horisont,
        t_kutt=t_kutt,
    )


def velg_prediktor(verdi: Optional[str] = None) -> Prediktor:
    """Velg prediktor fra ``PREDIKTOR`` (``auto`` | ``baseline`` | ``modell``).

    Standard er ``auto``: modell hvis artefakt finnes, ellers baseline. I E1 finnes
    ingen modellartefakt, så alle tre gir baselinen. Ukjent verdi gir ``ValueError``.
    """
    if verdi is None:
        verdi = os.environ.get("PREDIKTOR", "")
    verdi = verdi.strip().lower() or "auto"
    if verdi not in GYLDIGE_PREDIKTOR:
        raise ValueError(
            f"ukjent PREDIKTOR={verdi!r}; gyldige verdier er {', '.join(GYLDIGE_PREDIKTOR)}"
        )
    from app.prediksjon.baseline import BaselinePrediktor

    # E2-S07/E2-S08: «modell» og «auto» velger ModellPrediktor når artefaktet finnes.
    return BaselinePrediktor()
