"""Tidsstempelfilteret for AIS-svar (beslutning 09, funn B–C; PRD FR9a).

Kystdatahuset gir punkter fra et vindu forskjøvet +1/+2 t, så et svar på
[t_H − 3 t, t_H] inneholder punkter etter t_H. Filteret må fjerne dem.
"""
import importlib.util
from datetime import datetime
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "sjekk_ais_dekning_kutt", REPO_ROT / "pipeline" / "sjekk_ais_dekning_kutt.py")
sjekk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sjekk)


def punkt(tid):
    # Samme kolonnerekkefølge som API-et: mmsi, tid, lon, lat, cog, sog, …
    return [257000000, tid, 5.3, 60.4, 90.0, 10.0, 1, 10.0, 10, 50, 90, 0]


def test_filtrerer_bort_punkter_etter_kutt():
    kutt = datetime(2026, 2, 26, 3, 40)
    fra = datetime(2026, 2, 26, 0, 40)
    # Slik et ekte svar ser ut: vinduet forskjøvet +1 t, altså punkter fram til kutt + 1 t.
    svar = [punkt(t) for t in (
        "2026-02-26T00:39:59",   # før vinduet
        "2026-02-26T00:40:00",   # på startgrensen
        "2026-02-26T02:15:00",
        "2026-02-26T03:40:00",   # på kuttet: tillatt
        "2026-02-26T03:40:01",   # ett sekund etter kuttet: lekkasje
        "2026-02-26T04:39:50",
    )]
    beholdt = [p[1] for p in sjekk.filtrer_til_vindu(svar, fra, kutt)]
    assert beholdt == ["2026-02-26T00:40:00", "2026-02-26T02:15:00", "2026-02-26T03:40:00"]
    assert all(datetime.fromisoformat(t) <= kutt for t in beholdt)
