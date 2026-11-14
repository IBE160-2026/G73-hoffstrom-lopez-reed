"""Modellprediktoren (E2-S07, PRD FR9, beslutning 11 og 12).

Modellen gjelder bare Øvrige-anløp med AIS-tilstand ved kuttet som er utenfor ankomstsonen (F6 = 0). For dem er

    predikert_ankomst = eta_reported − offset_ovrige_min + predikert avvik
    forventet_forsinket = predikert avvik > 120 min

med ``modell_{H}t.joblib`` og offseten fra artefaktet. Alle andre rader delegeres til ``BaselinePrediktor``
(``forventet_forsinket = None``, ``forklaring["delegert"]`` sier hvorfor), slik modellarmen i ``scripts/evaluer.py``
gjør. F1–F16 kommer gjennom grensen (``featurer_ved_kutt`` i ``__init__.py``). Modulen leser ingen datafiler utenom artefaktene selv.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence

from app.prediksjon import Prediksjon, PrediksjonsInput, features_sha256, featurer_ved_kutt
from app.prediksjon.baseline import BaselinePrediktor
from app.prediksjon.koding import FEATURES, matrise

MODELL_DIR = Path(__file__).resolve().parents[2] / "data" / "modell"
HORISONTER = (6, 24)
MODELLGRUPPE = "Øvrige"
VARSEL_MIN = 120.0  # samme terskel som er_forsinket (beslutning 06, PRD A3)


@lru_cache(maxsize=None)
def _last_artefakter(modell_dir: Path) -> Dict[int, dict]:
    import joblib

    ut = {}
    for h in HORISONTER:
        sti = Path(modell_dir) / f"modell_{h}t.joblib"
        if not sti.is_file():
            raise ValueError(f"fant ikke modellartefaktet {sti}")
        ut[h] = joblib.load(sti)
    return ut


def _sjekk(art: dict, h: int, sha: str, offset: float) -> None:
    navn = f"modell_{h}t.joblib"
    if art.get("horisont") != h or art.get("variant") != "hoved":
        raise ValueError(f"{navn}: artefaktet er {art.get('horisont')} t / {art.get('variant')}, ikke {h} t / hoved")
    if art.get("features_sha256") != sha:
        raise ValueError(f"{navn}: features_sha256 i artefaktet stemmer ikke med featurefila grensen gir "
                         "(artefaktet er trent på andre data)")
    if art.get("offset_ovrige_min") != offset:
        raise ValueError(f"{navn}: offset_ovrige_min {art.get('offset_ovrige_min')} ≠ baseline.json {offset}")
    if art.get("historikk", "endelig") != "endelig":
        raise ValueError(f"{navn}: historikk {art.get('historikk')!r} i artefaktet, ikke 'endelig'")
    if list(art.get("features", [])) != FEATURES:
        raise ValueError(f"{navn}: featurelista i artefaktet er ikke den grensen gir")


class ModellPrediktor:
    navn = "Modell v1"
    kan_varsle = True

    def __init__(self, modell_dir: Path = MODELL_DIR) -> None:
        self._baseline = BaselinePrediktor()
        offset = self._baseline.offset_minutter[MODELLGRUPPE]
        sha = features_sha256()
        self._artefakter = _last_artefakter(Path(modell_dir))
        for h, art in self._artefakter.items():
            _sjekk(art, h, sha, offset)

    def prediker(
        self, inputs: Sequence[PrediksjonsInput], naa: dt.datetime
    ) -> List[Prediksjon]:
        for inp in inputs:
            if not isinstance(inp, PrediksjonsInput):
                raise TypeError(
                    "prediker() tar PrediksjonsInput fra lag_input(), "
                    f"ikke {type(inp).__name__}"
                )
        ut: List[Prediksjon] = list(self._baseline.prediker(inputs, naa))
        per_h: Dict[int, list] = {}
        for i, inp in enumerate(inputs):
            featurer = None if inp.gruppe != MODELLGRUPPE else featurer_ved_kutt(inp)
            if inp.gruppe != MODELLGRUPPE:
                grunn = "passasjer"  # gruppe er «Passasjer» eller «Øvrige» (beslutning 11)
            elif featurer is None:
                grunn = "ingen_featurerad"
            elif featurer["i_sonen_ved_kutt"] is None:  # F6 er definert nøyaktig når tilstanden finnes
                grunn = "ingen_tilstand"
            elif featurer["i_sonen_ved_kutt"] == 1:
                grunn = "i_sonen_ved_kutt"
            else:
                per_h.setdefault(inp.horisont_timer, []).append((i, inp, featurer))
                continue
            b = ut[i]
            ut[i] = Prediksjon(b.voyageid, b.horisont_timer, b.predikert_ankomst, None,
                               dict(b.forklaring, delegert=grunn))
        for h, rader in per_h.items():
            art = self._artefakter[h]
            avvik = art["modell"].predict(matrise([f for _, _, f in rader], art["features"], art["kategorier"]))
            offset_min = art["offset_ovrige_min"]
            for (i, inp, featurer), avvik_min in zip(rader, avvik):
                avvik_min = float(avvik_min)
                ut[i] = Prediksjon(
                    voyageid=inp.voyageid,
                    horisont_timer=inp.horisont_timer,
                    # Samme uttrykk som modellarmen i scripts/evaluer.py, så tidene er bit-like.
                    predikert_ankomst=inp.eta_reported - dt.timedelta(minutes=offset_min - avvik_min),
                    forventet_forsinket=avvik_min > VARSEL_MIN,
                    forklaring={
                        "metode": "modell",
                        "gruppe": inp.gruppe,
                        "variant": art["variant"],
                        "horisont": h,
                        "predikert_avvik_min": avvik_min,
                        "offset_ovrige_min": offset_min,
                        "eta_reported": inp.eta_reported,
                        "featurer": {k: featurer[k] for k in art["features"]},
                    },
                )
        return ut
