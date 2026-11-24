"""Ekte klient mot OpenRouter (E3-S03, beslutning 13). Bare standardbiblioteket (``urllib.request``).

``kall`` sender én chat-forespørsel og gir svarteksten, eller kaster ``KlientFeil`` med en årsakskode:
``timeout``, ``nett``, ``kvote_402`` (bruksgrensen på nøkkelen er nådd), ``http_<kode>``, ``svar_format`` eller
``avkortet``. Nøkkelen står bare i ``Authorization``-headeren og havner aldri i en feilmelding.

Transporten kan byttes (``transport=``), så testene aldri går mot nettet. Den tar
``(url, headers, body, timeout)`` og gir ``(status, body)``.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Tuple

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# 300 dekker også briefen: høyst 700 tegn norsk tekst er om lag 200–250 tokens uten resonnering (E3-S05).
MAKS_TOKENS = 300
TEMPERATUR = 0.2
PROMPT_FIL = Path(__file__).with_name("prompt.md")
PROMPT_BRIEF_FIL = Path(__file__).with_name("prompt_brief.md")  # forstyrrelsesbriefen (E3-S05)


class KlientFeil(Exception):
    """Kallet feilet. ``kode`` er årsakskoden som logges. Meldingen er bare koden."""

    def __init__(self, kode: str):
        super().__init__(kode)
        self.kode = kode


@lru_cache(maxsize=None)
def _prompt(fil: Path = PROMPT_FIL) -> Tuple[str, str]:
    """Markørene står alene på en linje. Teksten før ``<!-- SYSTEM -->`` er dokumentasjon og sendes ikke."""
    tekst = Path(fil).read_text(encoding="utf-8")
    _, system, bruker = re.split(r"^<!-- (?:SYSTEM|BRUKER) -->$", tekst, flags=re.MULTILINE)
    return system.strip(), bruker.strip()


@lru_cache(maxsize=None)
def prompt_versjon(fil: Path = PROMPT_FIL) -> str:
    """Versjonen i prompt-fila, f.eks. ``begrunnelse-v8`` eller ``brief-v4``, fra linja ``**Versjon:** `…```.
    Opptakene (E3-S06) lagrer den, og et opptak med en annen versjon brukes ikke."""
    treff = re.search(r"^\*\*Versjon:\*\*\s*`([^`]+)`", Path(fil).read_text(encoding="utf-8"), flags=re.MULTILINE)
    if treff is None:
        raise ValueError(f"fant ingen **Versjon:**-linje i {Path(fil).name}")
    return treff.group(1)


def bygg_prompt(fakta: Mapping[str, str], fil: Path = PROMPT_FIL) -> Tuple[str, str]:
    """(systemmelding, brukermelding) fra prompt-fila (standard ``prompt.md``, briefen ``prompt_brief.md``) og
    faktaene."""
    system, bruker = _prompt(fil)
    linjer = "\n".join(f"- {k}: {v}" for k, v in fakta.items())
    return system, bruker.replace("{fakta}", linjer)


def urllib_transport(url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> Tuple[int, bytes]:
    """POST med ``urllib.request``. HTTP-feil gir statuskoden, og feilkroppen leses ikke."""
    forespørsel = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(forespørsel, timeout=timeout) as svar:
            return svar.status, svar.read()
    except urllib.error.HTTPError as feil:
        return feil.code, b""


def kall(system: str, bruker: str, *, modell: str, nokkel: str, timeout: float, transport=None,
         resonnering=None) -> str:
    """Ett kall til OpenRouter. Gir svarteksten (kan være tom; kontrollen avviser den).

    ``resonnering`` er ``reasoning.effort`` (``konfig.resonnering()``). None sender ingen ``reasoning``. Resonneringstokens
    teller mot ``max_tokens`` (røykkallet 18.11.2026: med modellens standard gikk alle 300 til resonnering)."""
    forespørsel = {
        "model": modell,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": bruker}],
        "max_tokens": MAKS_TOKENS,
        "temperature": TEMPERATUR,
    }
    if resonnering:
        forespørsel["reasoning"] = {"effort": resonnering}
    body = json.dumps(forespørsel).encode("utf-8")
    headers = {"Authorization": f"Bearer {nokkel}", "Content-Type": "application/json"}
    try:
        status, data = (transport or urllib_transport)(OPENROUTER_URL, headers, body, timeout)
    except TimeoutError:  # socket.timeout er et alias for TimeoutError
        raise KlientFeil("timeout") from None
    except urllib.error.URLError as feil:
        raise KlientFeil("timeout" if isinstance(feil.reason, TimeoutError) else "nett") from None
    except OSError:
        raise KlientFeil("nett") from None
    if status == 402:
        raise KlientFeil("kvote_402")
    if status != 200:
        raise KlientFeil(f"http_{status}")
    try:
        svar = json.loads(data.decode("utf-8"))
        valg = svar["choices"][0]
        tekst = valg["message"]["content"]
        avkortet = valg.get("finish_reason") == "length"  # kuttet ved max_tokens: kan stoppe midt i en setning
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise KlientFeil("svar_format") from None
    if tekst is None:
        tekst = ""
    if not isinstance(tekst, str):
        raise KlientFeil("svar_format")
    if avkortet:
        raise KlientFeil("avkortet")
    return tekst
