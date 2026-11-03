"""Kalibrert baseline (beslutning 04, E1-S04): ``predikert = rapportert ETA − offset[gruppe]``.

Offsetene leses én gang fra ``data/baseline.json``, uavrundet. Baselinen varsler aldri.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence

from app.prediksjon import Prediksjon, PrediksjonsInput

BASELINE_FIL = Path(__file__).resolve().parents[2] / "data" / "baseline.json"


@lru_cache(maxsize=None)
def _offsets(sti: Path = BASELINE_FIL) -> Dict[str, float]:
    with open(sti, encoding="utf-8") as f:
        return dict(json.load(f)["offset_minutter"])


class BaselinePrediktor:
    navn = "Kalibrert baseline"
    kan_varsle = False

    def __init__(self) -> None:
        self.offset_minutter = dict(_offsets())

    def prediker(
        self, inputs: Sequence[PrediksjonsInput], naa: dt.datetime
    ) -> List[Prediksjon]:
        ut = []
        for inp in inputs:
            if not isinstance(inp, PrediksjonsInput):
                raise TypeError(
                    "prediker() tar PrediksjonsInput fra lag_input(), "
                    f"ikke {type(inp).__name__}"
                )
            offset = self.offset_minutter[inp.gruppe]
            ut.append(
                Prediksjon(
                    voyageid=inp.voyageid,
                    horisont_timer=inp.horisont_timer,
                    predikert_ankomst=inp.eta_reported - dt.timedelta(minutes=offset),
                    forventet_forsinket=None,
                    forklaring={
                        "metode": "kalibrert_baseline",
                        "gruppe": inp.gruppe,
                        "offset_minutter": offset,
                        "eta_reported": inp.eta_reported,
                    },
                )
            )
        return ut
