"""Prediktor-kontrakten (arkitektur §3, A5; E1-S04).

Prediktorer får aldri et ``Anlop``. De får en ``PrediksjonsInput``: en frossen verdi med
bare det som er kjent ved prediksjonstidspunktet (identitet, gruppe, rapportert ETA,
horisont og kuttpunkt). Den har ingen felt eller referanse som fører til fasiten
(``faktisk_ankomst``, ``status_in_area``, ``split``). ``lag_input`` er den eneste
koden i prediksjonslaget som rører datalaget.

Featurene F1–F16 ved kuttet når modellen gjennom søsterfunksjonen ``featurer_ved_kutt`` (E2-S07,
beslutning 1A i specen). Den leser ``data/utdrag/features.csv`` og gir bare modellens featurekolonner.

``velg_prediktor`` (E2-S08) velger mellom baseline og ``ModellPrediktor``. Låsen for testperioden trenger
testperiodens første rapporterte ETA, og den leses her, fordi denne modulen er grensen mot ``app.data``.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

if TYPE_CHECKING:
    from app.data import Anlop

HORISONT_KORT = 6
HORISONT_LANG = 24
GYLDIGE_PREDIKTOR = ("auto", "baseline", "modell")
FEATURES_FIL = Path(__file__).resolve().parents[2] / "data" / "utdrag" / "features.csv"


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


def _featureverdi(kolonne: str, verdi: str, kategoriske: Sequence[str]):
    """Tom celle blir None. Kategoriene (F8, F13) står som tekst, alt annet som float."""
    if verdi == "":
        return None
    return verdi if kolonne in kategoriske else float(verdi)


@lru_cache(maxsize=None)
def _featurefil(sti: Path = FEATURES_FIL) -> Tuple[str, Dict[Tuple[int, int], Tuple[dt.datetime, Mapping]]]:
    """(sha256, {(voyageid, H): (t_kutt, featurer)}). Lest én gang. Bare modellens featurekolonner beholdes;
    ``del``, ``gruppe``, ``har_tilstand``, ``_modellvalg``-historikken og alt annet kastes her."""
    from app.prediksjon.koding import FEATURES, KATEGORISKE

    innhold = Path(sti).read_bytes()
    rader = {}
    for r in csv.DictReader(io.StringIO(innhold.decode("utf-8"))):
        t_kutt = _til_utc(dt.datetime.fromisoformat(r["t_kutt_utc"].replace("Z", "+00:00")), "t_kutt_utc")
        featurer = MappingProxyType({k: _featureverdi(k, r[k], KATEGORISKE) for k in FEATURES})
        rader[(int(r["voyageid"]), int(r["horisont_timer"]))] = (t_kutt, featurer)
    return hashlib.sha256(innhold).hexdigest(), rader


def features_sha256() -> str:
    """sha256 for featurefila ``featurer_ved_kutt`` svarer fra. ``ModellPrediktor`` sjekker den mot artefaktet."""
    return _featurefil()[0]


def featurer_ved_kutt(inp: PrediksjonsInput) -> Optional[Mapping]:
    """F1–F16 for anløpet og horisonten, som en frossen mapping med bare modellens featurekolonner.

    Gir None hvis det ikke finnes en featurerad, eller hvis radens kuttpunkt ikke er lik ``inp.t_kutt``
    (for eksempel når ``lag_input`` har klemt kuttet mot «nå»: den committede raden er da fra etter «nå»).
    Uten AIS-tilstand ved kuttet er F1–F7 None (også F6). Ingen fasit eller ankomstfelt går ut herfra.
    """
    if not isinstance(inp, PrediksjonsInput):
        raise TypeError(f"featurer_ved_kutt() tar PrediksjonsInput, ikke {type(inp).__name__}")
    treff = _featurefil()[1].get((inp.voyageid, inp.horisont_timer))
    if treff is None or treff[0] != inp.t_kutt:
        return None
    return treff[1]


# Låsen i velg_prediktor (E2-S08, beslutning 1 i specen).
METRIKKER_FIL = Path(__file__).resolve().parents[2] / "data" / "modell" / "metrikker.json"
MODELL_DIR = Path(__file__).resolve().parents[2] / "data" / "modell"
VINDU_TIMER = 24  # dashbordets vindu [naa, naa + 24 t)
MERKNAD_LAAST = ("Modellen vises ikke for testperioden før den ene testkjøringen (E2-S10) "
                 "— viser kalibrert baseline")
MERKNAD_IKKE_FUNNET = "Modell ikke funnet — viser kalibrert baseline"


def testkjoringer(sti: Optional[Path] = None) -> int:
    """``testkjoringer`` i ``metrikker.json``. Mangler fila eller nøkkelen, eller kan den ikke leses, er svaret 0
    (låst)."""
    sti = METRIKKER_FIL if sti is None else sti
    try:
        verdi = json.loads(Path(sti).read_text(encoding="utf-8")).get("testkjoringer", 0)
    except (OSError, ValueError, AttributeError):
        return 0
    return verdi if isinstance(verdi, int) and not isinstance(verdi, bool) else 0


@lru_cache(maxsize=None)
def testperiode_start() -> dt.datetime:
    """Tidligste rapporterte ETA i ``test``-delen (UTC). Bare låsen bruker den; ingen fasit går ut herfra."""
    from app.data import last_utdrag

    return min(a.eta_reported for a in last_utdrag() if a.split == "test").astimezone(dt.timezone.utc)


def i_testperioden(naa: Optional[dt.datetime]) -> bool:
    """Vinduet regnes som testperiode når slutten (``naa + 24 t``) er etter testperiodens første ETA.
    Uten ``naa``, eller hvis testperiodens start ikke kan leses, regnes det også som testperiode."""
    if naa is None:
        return True
    slutt = _til_utc(naa, "naa") + dt.timedelta(hours=VINDU_TIMER)
    try:
        return slutt > testperiode_start()
    except Exception:  # ingen testrader eller uleselig utdrag: låst, aldri HTTP 500
        return True


def velg_prediktor_med_merknad(
    verdi: Optional[str] = None, naa: Optional[dt.datetime] = None
) -> Tuple[Prediktor, Optional[str]]:
    """Som ``velg_prediktor``, men gir også en merknad til prediktor-stripa når modellen var valgt og
    appen viser baselinen i stedet (låst testperiode eller manglende artefakt). Ellers er merknaden None."""
    if verdi is None:
        verdi = os.environ.get("PREDIKTOR", "")
    verdi = verdi.strip().lower() or "auto"
    if verdi not in GYLDIGE_PREDIKTOR:
        raise ValueError(
            f"ukjent PREDIKTOR={verdi!r}; gyldige verdier er {', '.join(GYLDIGE_PREDIKTOR)}"
        )
    from app.prediksjon.baseline import BaselinePrediktor

    if verdi == "baseline":
        return BaselinePrediktor(), None
    if testkjoringer() < 1:
        if verdi == "auto":
            return BaselinePrediktor(), None
        if i_testperioden(naa):
            return BaselinePrediktor(), MERKNAD_LAAST
    from app.prediksjon.modell import ModellPrediktor

    try:
        return ModellPrediktor(MODELL_DIR), None
    except Exception:  # manglende, avvikende eller korrupt artefakt: appen skal alltid starte
        return BaselinePrediktor(), MERKNAD_IKKE_FUNNET


def velg_prediktor(verdi: Optional[str] = None, naa: Optional[dt.datetime] = None) -> Prediktor:
    """Velg prediktor fra ``PREDIKTOR`` (``auto`` | ``baseline`` | ``modell``). Ukjent verdi gir ``ValueError``.

    - ``baseline`` gir alltid ``BaselinePrediktor``.
    - Før testkjøringen (``testkjoringer`` i ``data/modell/metrikker.json`` er 0, eller fila mangler) gir ``auto``
      baselinen. ``modell`` gir ``ModellPrediktor`` bare når vinduet ``[naa, naa + 24 t)`` slutter senest ved
      testperiodens første rapporterte ETA. Ellers, og uten ``naa``, gir den baselinen (låst testperiode).
    - Etter testkjøringen gir både ``auto`` og ``modell`` ``ModellPrediktor``.
    - Feiler ``ModellPrediktor()`` (artefakt mangler, stemmer ikke eller er korrupt), faller valget tilbake til
      baselinen, så appen alltid starter.

    Merknaden til prediktor-stripa får man fra ``velg_prediktor_med_merknad``.
    """
    return velg_prediktor_med_merknad(verdi, naa)[0]
