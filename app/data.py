"""Datalaget: leser det committede utdraget til typede anløp (E1-S03, arkitektur §4–§5).

Alle tider er tz-aware UTC. En tid uten tidssonesuffiks tolkes som UTC, samme regel
som ``scripts/lag_utdrag.py:til_utc_z``.
"""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

REPO_ROT = Path(__file__).resolve().parent.parent
STANDARD_UTDRAG = REPO_ROT / "data" / "utdrag" / "anlop.csv"
VIS_GRUPPE = {"alle": None, "passasjer": "Passasjer", "ovrige": "Øvrige"}
GYLDIGE_VIS = tuple(VIS_GRUPPE)


@dataclass(frozen=True)
class Anlop:
    voyageid: int
    mmsino: int
    shipname: str
    ship_group: str  # rå gruppe fra kilden (Tank, Last, Passasjer, …)
    eta_reported: dt.datetime  # rapportert ETA, UTC
    faktisk_ankomst: Optional[dt.datetime]  # UTC; None når status_in_area ≠ ok
    status_in_area: str
    split: str

    @property
    def gruppe(self) -> str:
        """«Passasjer» eller «Øvrige» (ordlisten)."""
        return "Passasjer" if self.ship_group == "Passasjer" else "Øvrige"


def _til_utc(tekst: str) -> dt.datetime:
    """ISO-tid til tz-aware UTC. Uten suffiks tolkes som UTC (Python 3.9 tåler ikke ``Z``)."""
    tekst = tekst.strip()
    if tekst.endswith("Z"):
        tekst = tekst[:-1] + "+00:00"
    t = dt.datetime.fromisoformat(tekst)
    if t.tzinfo is None:
        return t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def _fra_rad(rad: dict) -> Anlop:
    status = rad["status_in_area"]
    ankomst = rad["arrival_in_area_utc"]
    return Anlop(
        voyageid=int(rad["voyageid"]),
        mmsino=int(rad["mmsino"]),
        shipname=rad["shipname"],
        ship_group=rad["ship_group"],
        eta_reported=_til_utc(rad["eta_reported"]),
        faktisk_ankomst=_til_utc(ankomst) if status == "ok" and ankomst else None,
        status_in_area=status,
        split=rad["split"],
    )


@lru_cache(maxsize=None)
def _last(sti: Path) -> tuple[Anlop, ...]:
    with open(sti, encoding="utf-8", newline="") as f:
        return tuple(_fra_rad(rad) for rad in csv.DictReader(f))


def last_utdrag(sti=STANDARD_UTDRAG) -> tuple[Anlop, ...]:
    """Les utdraget. Parses én gang per sti; senere kall gir samme objekt."""
    return _last(Path(sti).resolve())


def anlop_i_vindu(
    naa: dt.datetime,
    timer: int = 24,
    vis: str = "alle",
    anlop: Optional[Iterable[Anlop]] = None,
) -> list[Anlop]:
    """Anløp med rapportert ETA i [naa, naa + timer), sortert på (ETA, voyageid).

    ``naa`` må være tz-aware. ``vis`` er ``alle``, ``passasjer`` eller ``ovrige``.
    ``anlop`` er standard hele utdraget.
    """
    if naa.tzinfo is None or naa.utcoffset() is None:
        raise ValueError("naa må ha tidssone (tz-aware datetime)")
    if vis not in GYLDIGE_VIS:
        raise ValueError(f"ukjent vis={vis!r}; gyldige verdier er {', '.join(GYLDIGE_VIS)}")
    if anlop is None:
        anlop = last_utdrag()

    start = naa.astimezone(dt.timezone.utc)
    slutt = start + dt.timedelta(hours=timer)
    gruppe = VIS_GRUPPE[vis]
    treff = [
        a for a in anlop
        if start <= a.eta_reported < slutt and (gruppe is None or a.gruppe == gruppe)
    ]
    return sorted(treff, key=lambda a: (a.eta_reported, a.voyageid))
