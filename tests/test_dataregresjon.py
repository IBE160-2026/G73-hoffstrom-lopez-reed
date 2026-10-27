"""Dataregresjon på det committede utdraget (E1-S05).

Låser overskriftstallene i brief og PRD (README får tallene i E1-S16): kalibrert baseline 46,6 % (Øvrige) og
79,6 % (Passasjer) innenfor ±30 min i testperioden, naiv ETA 12,8 % / 7,4 %, og dekningen.
Hvert tall lages gjennom S04-kontrakten: ``lag_input(a, naa)`` med ``naa = eta − H``, så
``prediker`` på en prediktor fra ``PREDIKTORER``. Eksakte antall, ikke bare prosent.

Hva testen ikke fanger: Passasjer-tallet er flatt rundt offseten (343/431 ved 43,75–46,75
min). Offseten er låst i ``test_baseline.py``, ikke her.
"""
import datetime as dt

import pytest

from app.data import last_utdrag
from app.metrikker import andel_innenfor, dekning
from app.prediksjon import lag_input
from app.prediksjon.baseline import BaselinePrediktor
from app.prediksjon.naiv import NaivPrediktor

from tests.test_prediktor_kontrakt import PREDIKTORER

HORISONTER = (6, 24)


@pytest.fixture(scope="module")
def test_split():
    return [a for a in last_utdrag() if a.split == "test"]


def _prediker_ved_kutt(prediktor, anlop, horisont):
    """Hvert anløp predikeres ved sitt eget kuttpunkt: ``naa = eta − H``."""
    ut = []
    for a in anlop:
        naa = a.eta_reported - dt.timedelta(hours=horisont)
        inp = lag_input(a, naa)
        assert inp.horisont_timer == horisont
        ut += prediktor.prediker([inp], naa)
    return ut


def _score(prediktorklasse, test_split, gruppe, horisont):
    assert prediktorklasse in PREDIKTORER  # bare kontraktstestede prediktorer scores
    anlop = [a for a in test_split if a.gruppe == gruppe]
    return andel_innenfor(_prediker_ved_kutt(prediktorklasse(), anlop, horisont), anlop)


@pytest.mark.parametrize("horisont", HORISONTER)
@pytest.mark.parametrize("prediktor, gruppe, treff, n, prosent", [
    (BaselinePrediktor, "Øvrige", 464, 996, "46,6"),
    (BaselinePrediktor, "Passasjer", 343, 431, "79,6"),
    (NaivPrediktor, "Øvrige", 127, 996, "12,8"),
    (NaivPrediktor, "Passasjer", 32, 431, "7,4"),
])
def test_treffandel_innenfor_30_min(test_split, prediktor, gruppe, treff, n, prosent, horisont):
    r = _score(prediktor, test_split, gruppe, horisont)
    assert (r.treff, r.n) == (treff, n)
    assert f"{r.andel * 100:.1f}".replace(".", ",") == prosent


def test_naiv_ovrige_bruker_uavrundet_avvik(test_split):
    """Seilas 3542899 er +30 min 1 s: utenfor. Pipelinen avrundet og fikk 12,9 %."""
    [a] = [a for a in test_split if a.voyageid == 3542899]
    avvik = a.faktisk_ankomst - a.eta_reported
    assert abs(avvik) == dt.timedelta(minutes=30, seconds=1)
    assert andel_innenfor(_prediker_ved_kutt(NaivPrediktor(), [a], 6), [a]).treff == 0


def test_dekning_testperioden(test_split):
    assert len(test_split) == 1566
    assert dekning(test_split) == {
        "ok": 1427, "empty": 126, "not_detected": 8, "avkortet_av_neste_seilas": 5,
    }
