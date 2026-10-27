"""Naiv ETA (E1-S05): ``predikert = rapportert ETA``. Referanseprediktor, varsler aldri.

Finnes så naiv-tallet i regresjonstesten går gjennom samme kontrakt som baselinen
(``lag_input`` → ``prediker``). Kan ikke velges med ``velg_prediktor``.
"""
from __future__ import annotations

import datetime as dt
from typing import List, Sequence

from app.prediksjon import Prediksjon, PrediksjonsInput


class NaivPrediktor:
    navn = "Naiv ETA"
    kan_varsle = False

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
            ut.append(
                Prediksjon(
                    voyageid=inp.voyageid,
                    horisont_timer=inp.horisont_timer,
                    predikert_ankomst=inp.eta_reported,
                    forventet_forsinket=None,
                    forklaring={"metode": "naiv_eta", "gruppe": inp.gruppe},
                )
            )
        return ut
