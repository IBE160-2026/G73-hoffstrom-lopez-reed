"""AI-laget: begrunnelse per anløp bak en adapter med testmodus som standard (arkitektur A8, E3-S01–S04).

Rutene kaller bare ``cachet`` og ``hent_begrunnelse`` herfra, aldri leverandøren direkte.

- **Testmodus** (``LLM_MODUS=test``, standard): deterministisk mal-tekst merket «Testmodus». Ingen nett.
- **Ekte modus** (``LLM_MODUS=ekte``): ett kall til OpenRouter per (seilas, prediktor), og svaret kontrolleres før
  det vises. Alle feil gir mal-teksten merket «Testmodus (ekte kall feilet)», og siden svarer alltid 200.

Adapteren tar ``PrediksjonsInput`` + ``Prediksjon``, aldri et ``Anlop``, så fasit ikke kan nå språkmodellen.

**Cache og kallgrense (PRD FR11b slik den er endret, spec-valg S5–S6).** Cachen ligger i minnet per prosess.
Et godkjent svar beholdes så lenge prosessen lever. En feil (kallfeil, tidsavbrudd, 402, mislykket kontroll) beholdes
bare i ``LLM_FEIL_TTL_S`` sekunder, og neste besøk etter det gjør et nytt forsøk, som teller mot grensen. Grensen er
høyst ``LLM_MAKS_KALL`` forsøk per prosess, talt under en lås. På Vercel er hver funksjonsinstans en egen prosess, så
grensen gjelder per instans. Totalen stoppes av bruksgrensen på nøkkelen hos OpenRouter (HTTP 402), ikke av appen.
Manglende nøkkel gjør ingen kall og teller ingenting.

Feil logges som en årsakskode med seilas og prediktor, aldri med nøkkelen.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from app.begrunnelse import konfig
from app.begrunnelse.testmodus import MERKE_FEILET, MERKE_GRENSE, MERKE_KI, MERKE_TEST, mal
from app.prediksjon import Prediksjon, PrediksjonsInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Begrunnelse:
    tekst: str
    merke: str  # «KI-GENERERT», «Testmodus», «Testmodus (ekte kall feilet)» eller «Testmodus (kallgrensen er nådd)»

    def som_dict(self) -> dict:
        return {"tekst": self.tekst, "merke": self.merke}


# Tilstand per prosess. Testene nullstiller den (``nullstill``) og bytter ut klokke og transport.
_laas = threading.Lock()
_cache: Dict[Tuple[int, str], Tuple[Begrunnelse, Optional[float]]] = {}  # → (svar, utløper; None = aldri)
_kall = 0
klokke: Callable[[], float] = time.monotonic
transport = None  # None = urllib mot OpenRouter (``openrouter_klient``). Testene setter en falsk transport.


def nullstill() -> None:
    """Tøm cachen og telleren (testene)."""
    global _kall
    with _laas:
        _cache.clear()
        _kall = 0


def antall_kall() -> int:
    """Ekte forsøk gjort i denne prosessen."""
    return _kall


def _sjekk(inp, prediksjon) -> None:
    if not isinstance(inp, PrediksjonsInput):
        raise TypeError(f"AI-laget tar PrediksjonsInput, ikke {type(inp).__name__}")
    if not isinstance(prediksjon, Prediksjon):
        raise TypeError(f"AI-laget tar Prediksjon, ikke {type(prediksjon).__name__}")
    if prediksjon.voyageid != inp.voyageid:
        raise ValueError("prediksjonen hører til en annen seilas enn inputen")


def testtekst(inp, prediksjon, merke: str = MERKE_TEST) -> Begrunnelse:
    """Mal-teksten med et testmodus-merke."""
    return Begrunnelse(mal(inp, prediksjon), merke)


def _logg(kode: str, inp, prediktor_navn: str) -> None:
    logger.warning("begrunnelse: %s voyageid=%s prediktor=%s", kode, inp.voyageid, prediktor_navn)


def _fra_cache(nokkel) -> Optional[Begrunnelse]:
    """Gyldig svar fra cachen, eller None. Kalleren holder låsen. En feil utløper ved ``klokke() >= utløper``."""
    treff = _cache.get(nokkel)
    if treff is None:
        return None
    svar, utloper = treff
    if utloper is not None and klokke() >= utloper:
        del _cache[nokkel]
        return None
    return svar


def cachet(inp, prediksjon, prediktor_navn: str) -> Optional[Begrunnelse]:
    """Det siden kan vise uten å vente: mal-teksten i testmodus, et cachet svar i ekte modus, ellers None.

    Gjør aldri et kall og teller ingenting. Med None viser siden «Henter forklaring …» og henter svaret med POST.
    """
    _sjekk(inp, prediksjon)
    if konfig.modus() == "test":
        return testtekst(inp, prediksjon)
    with _laas:
        return _fra_cache((inp.voyageid, prediktor_navn))


def _ekte(inp, prediksjon, api_nokkel: str) -> Tuple[Optional[str], Optional[str]]:
    """Ett ekte kall med kontroll. Gir (tekst, None) eller (None, årsakskode)."""
    from app.begrunnelse import openrouter_klient
    from app.begrunnelse.input import lag_fakta
    from app.begrunnelse.klartekst import konklusjon
    from app.begrunnelse.kontroll import kontroller, retning

    fakta = lag_fakta(inp, prediksjon)
    system, bruker = openrouter_klient.bygg_prompt(fakta)
    try:
        tekst = openrouter_klient.kall(
            system, bruker, modell=konfig.modellstreng(), nokkel=api_nokkel,
            timeout=konfig.timeout_s(), transport=transport, resonnering=konfig.resonnering(),
        )
    except openrouter_klient.KlientFeil as feil:
        return None, feil.kode
    regel = kontroller(tekst, fakta, forventet_forsinket=prediksjon.forventet_forsinket, retning=retning(prediksjon),
                       konklusjon=konklusjon(inp, prediksjon))
    if regel:
        return None, f"kontroll_{regel}"
    return tekst.strip(), None


def hent_begrunnelse(inp, prediksjon, prediktor_navn: str) -> Begrunnelse:
    """Begrunnelsen for ett anløp. Kaster aldri for feil hos leverandøren eller i svaret: alt gir testmodus-tekst."""
    global _kall
    _sjekk(inp, prediksjon)
    if konfig.modus() == "test":
        return testtekst(inp, prediksjon)
    nokkel = (inp.voyageid, prediktor_navn)
    with _laas:
        svar = _fra_cache(nokkel)
    if svar is not None:
        return svar
    api_nokkel = konfig.api_nokkel()
    if api_nokkel is None:
        _logg("mangler_nokkel", inp, prediktor_navn)
        return testtekst(inp, prediksjon, MERKE_FEILET)
    with _laas:
        svar = _fra_cache(nokkel)  # en annen forespørsel kan ha blitt ferdig i mellomtiden
        if svar is not None:
            return svar
        if _kall >= konfig.maks_kall():
            _logg("kallgrense", inp, prediktor_navn)
            return testtekst(inp, prediksjon, MERKE_GRENSE)
        _kall += 1
    try:
        tekst, kode = _ekte(inp, prediksjon, api_nokkel)
    except Exception as feil:  # uventet feil: aldri HTTP 500, og meldingen logges ikke (den kan inneholde hva som helst)
        tekst, kode = None, f"uventet_{type(feil).__name__}"
    if tekst is not None:
        svar, utloper = Begrunnelse(tekst, MERKE_KI), None
    else:
        _logg(kode, inp, prediktor_navn)
        svar, utloper = testtekst(inp, prediksjon, MERKE_FEILET), klokke() + konfig.feil_ttl_s()
    with _laas:
        _cache[nokkel] = (svar, utloper)
    return svar
