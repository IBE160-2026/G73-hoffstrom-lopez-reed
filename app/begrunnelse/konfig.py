"""All konfigurasjon for AI-laget, lest på ett sted (E3-S01, beslutning 13).

Verdiene leses fra miljøet ved hvert oppslag, så testene kan sette dem med ``monkeypatch``. Ingenting her leser
``.env``. Nøkkelen leses bare fra ``os.environ`` og skal aldri skrives til logg, unntak, svar eller mal.

Modellstrengen som sendes til OpenRouter, bygges bare her (``modellstreng``): ``LLM_MODELL`` + ``:`` + ``LLM_ROUTING``.
Med ``LLM_ROUTING=floor`` velger OpenRouter den billigste leverandøren av modellen (spec-valg S2).
"""
from __future__ import annotations

import math
import os

STANDARD_MODUS = "test"
GYLDIGE_MODUS = ("test", "ekte")
STANDARD_MODELL = "deepseek/deepseek-v4.1-flash-1017"
STANDARD_ROUTING = "floor"
STANDARD_MAKS_KALL = 20
STANDARD_FEIL_TTL_S = 300.0
STANDARD_TIMEOUT_S = 8.0
NOKKEL_VARIABEL = "OPENROUTER_API_KEY"


def _tekst(navn: str, standard: str) -> str:
    return os.environ.get(navn, "").strip() or standard


def _tall(navn: str, standard: float, minst: float) -> float:
    """Tall fra miljøet. Tomt, ugyldig, ikke endelig (inf, nan) eller under ``minst`` gir standardverdien, så appen alltid starter."""
    try:
        verdi = float(os.environ.get(navn, "").strip())
    except ValueError:
        return standard
    return verdi if math.isfinite(verdi) and verdi >= minst else standard


def modus() -> str:
    """``test`` (standard) eller ``ekte``. Ukjent verdi gir ``test``: testmodus krever ingen nøkkel og ingen nett."""
    verdi = _tekst("LLM_MODUS", STANDARD_MODUS).lower()
    return verdi if verdi in GYLDIGE_MODUS else STANDARD_MODUS


def modellstreng() -> str:
    """Modellstrengen til OpenRouter, f.eks. ``deepseek/deepseek-v4.1-flash-1017:floor``."""
    modell = _tekst("LLM_MODELL", STANDARD_MODELL)
    routing = os.environ.get("LLM_ROUTING")
    routing = STANDARD_ROUTING if routing is None else routing.strip()
    return f"{modell}:{routing}" if routing and ":" not in modell else modell


def maks_kall() -> int:
    """Høyst så mange ekte kall per prosess (PRD FR11b, spec-valg S6: per Vercel-instans)."""
    return int(_tall("LLM_MAKS_KALL", STANDARD_MAKS_KALL, 0))


def feil_ttl_s() -> float:
    """Hvor lenge et mislykket kall eller en mislykket kontroll caches (spec-valg S5)."""
    return _tall("LLM_FEIL_TTL_S", STANDARD_FEIL_TTL_S, 0)


def timeout_s() -> float:
    return _tall("LLM_TIMEOUT_S", STANDARD_TIMEOUT_S, 0.1)


def api_nokkel():
    """Nøkkelen fra ``OPENROUTER_API_KEY``, eller None. Aldri fra fil."""
    return os.environ.get(NOKKEL_VARIABEL, "").strip() or None
