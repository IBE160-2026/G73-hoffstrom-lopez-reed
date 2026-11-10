"""Kodingen av F1–F16 til modellens input-matrise (E2-S05, flyttet hit i E2-S07).

Én definisjon av modellarmen: ``scripts/tren.py`` (trening og modellvalg), ``scripts/evaluer.py`` (via ``tren``)
og ``ModellPrediktor`` bruker alle ``matrise`` herfra. Ren funksjon: modulen leser ingen filer og importerer ikke
datalaget (AST-regelen i ``tests/test_prediktor_kontrakt.py`` gjelder også her).
"""
import numpy as np

from app.prediksjon import features as F

FEATURES = [
    "distanse_km", "fart_knop", "kurs_mot_havn", "posisjon_alder_min", "lat", "lon",   # F1–F5
    "i_sonen_ved_kutt", "slakk_timer",                                                 # F6–F7
    "skipstype", "lengde_m",                                                           # F8–F9
    "eta_time_sin", "eta_time_cos", "eta_ukedag", "eta_maned_sin", "eta_maned_cos",    # F10–F12
    "avgangshavn", "avgatt_for_kutt", "timer_siden_avgang",                            # F13–F14
    "fartoy_snittavvik_min", "fartoy_antall_tidligere",                                # F15–F16
]
KATEGORISKE = ("skipstype", "avgangshavn")                                             # F8, F13
HISTORIKK = ("fartoy_snittavvik_min", "fartoy_antall_tidligere")                       # F15–F16


def tall(s):
    """Tom streng og None blir NaN (HistGradientBoosting håndterer manglende verdier)."""
    return float("nan") if s is None or s == "" else float(s)


def matrise(rader, features, kategorier, historikk="endelig"):
    """X som float-matrise. Kategorier kodes som indeks i kartet; ukjent og manglende blir ``annet``.
    ``historikk="modellvalg"`` henter F15–F16 fra ``fartoy_*_modellvalg``."""
    kode = {k: {v: i for i, v in enumerate(liste)} for k, liste in kategorier.items()}
    X = np.empty((len(rader), len(features)), dtype=float)
    for i, r in enumerate(rader):
        for j, f in enumerate(features):
            if f in kode:
                X[i, j] = kode[f][F.grupper_sjeldne(r.get(f), frozenset(kode[f]))]
            elif f in HISTORIKK and historikk == "modellvalg":
                X[i, j] = tall(r[f + "_modellvalg"])
            else:
                X[i, j] = tall(r.get(f))
    return X
