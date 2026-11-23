"""Kjører ``app/static/begrunnelse.js`` i Node mot en falsk DOM (E3-S05, review-funn 1, utsatt i ``deferred-work.md``).

Før dette ble skriptet bare sjekket som kildetekst. Testen kjører feilgrenen og den vellykkede grenen for både skjerm C
og briefen. Node trengs ikke for å kjøre appen, så testen hoppes over når ``node`` ikke finnes.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node finnes ikke")


@pytest.fixture(scope="module")
def resultat():
    ut = subprocess.run([NODE, str(ROT / "tests" / "js" / "begrunnelse_harness.js"),
                         str(ROT / "app" / "static" / "begrunnelse.js")],
                        capture_output=True, text=True, timeout=30, check=True)
    return json.loads(ut.stdout)


def _region(resultat, navn, i=0):
    return [(c["klasse"], c["tekst"]) for c in resultat[navn]["regioner"][i]]


@pytest.mark.parametrize("navn, klasse, mal", [
    ("skjerm_c_feiler", "begrunnelse-tekst", "MAL C"),
    ("brief_feiler", "brief-tekst", "MAL A"),
    ("http_500", "begrunnelse-tekst", "MAL C"),
    ("ugyldig_svar", "brief-tekst", "MAL A"),
    ("ugyldig_merke", "begrunnelse-tekst", "MAL C"),
])
def test_feilet_henting_viser_mal_merket_feilet(resultat, navn, klasse, mal):
    """«Henter …» byttes ut med «Testmodus (ekte kall feilet)» og mal-teksten fra ``data-ki-mal``."""
    assert _region(resultat, navn) == [("ki-merke", "Testmodus (ekte kall feilet)"), (klasse, mal)]


def test_vellykket_henting_viser_svaret(resultat):
    assert _region(resultat, "skjerm_c_ok") == [("ki-merke", "KI-GENERERT"), ("begrunnelse-tekst", "SVAR C")]
    assert resultat["skjerm_c_ok"]["kall"] == [{"url": "/anlop/1/begrunnelse", "method": "POST"}]


def test_alle_regioner_hentes(resultat):
    """Skjerm A og C bruker samme skript. Hver ``[data-ki-url]``-region får sitt eget kall og sin egen klasse."""
    assert [k["url"] for k in resultat["begge_ok"]["kall"]] == ["/brief", "/anlop/1/begrunnelse"]
    assert _region(resultat, "begge_ok", 0) == [("ki-merke", "KI-GENERERT"), ("brief-tekst", "SVAR /brief")]
    assert _region(resultat, "begge_ok", 1) == [("ki-merke", "KI-GENERERT"),
                                                ("begrunnelse-tekst", "SVAR /anlop/1/begrunnelse")]
