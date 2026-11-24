"""AI-laget: begrunnelse per anløp bak en adapter med testmodus som standard (arkitektur A8, E3-S01–S04).

Rutene kaller bare ``cachet``, ``hent_begrunnelse``, ``cachet_brief`` og ``hent_brief`` herfra, aldri leverandøren
direkte. Briefen (E3-S05) går gjennom samme cache, kallgrense og kontroll som begrunnelsen.

- **Testmodus** (``LLM_MODUS=test``, standard): et opptak av et ekte svar merket «Testmodus (opptak av ekte svar)»
  når det finnes og fortsatt passer (E3-S06), ellers deterministisk mal-tekst merket «Testmodus». Ingen nett.
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
from app.begrunnelse.testmodus import (BRIEF_NOKKEL, MERKE_APP, MERKE_FEILET, MERKE_GRENSE, MERKE_KI, MERKE_OPPTAK,
                                       MERKE_TEST, mal, nullstill_opptak, opptak_for)
from app.prediksjon import Prediksjon, PrediksjonsInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Begrunnelse:
    tekst: str
    # «KI-GENERERT», «Testmodus», «Testmodus (ekte kall feilet)», «Testmodus (kallgrensen er nådd)»,
    # «Laget av appen» (briefen, B1) eller «Testmodus (opptak av ekte svar)» (E3-S06)
    merke: str
    tatt_opp: Optional[str] = None  # «24.11.2026» for et opptak (E3-S06, merket «Testmodus (opptak av ekte svar)»)

    def som_dict(self) -> dict:
        svar = {"tekst": self.tekst, "merke": self.merke}
        if self.tatt_opp is not None:
            svar["tatt_opp"] = self.tatt_opp
        return svar


# Tilstand per prosess. Testene nullstiller den (``nullstill``) og bytter ut klokke og transport.
_laas = threading.Lock()
# Nøkkel: (seilas, prediktor) for begrunnelsen, («brief», nå, prediktor) for briefen → (svar, utløper; None = aldri)
_cache: Dict[tuple, Tuple[Begrunnelse, Optional[float]]] = {}
_kall = 0
klokke: Callable[[], float] = time.monotonic
transport = None  # None = urllib mot OpenRouter (``openrouter_klient``). Testene setter en falsk transport.


def nullstill() -> None:
    """Tøm cachen og telleren, og glem opptaksfila (testene)."""
    global _kall
    with _laas:
        _cache.clear()
        _kall = 0
    nullstill_opptak()


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


def _fra_opptak(naa, anlop, prediktor_navn, fakta, prompt_fil) -> Optional[Begrunnelse]:
    """Et opptak som fortsatt passer (E3-S06), ellers None. Kaster aldri: en feil gir malen."""
    from app.begrunnelse.openrouter_klient import prompt_versjon

    try:
        treff = opptak_for(naa, anlop, prediktor_navn, fakta, prompt_versjon(prompt_fil))
    except Exception as feil:  # opptaket er en pynt: aldri HTTP 500 for det
        logger.warning("opptak: oppslaget feilet (%s)", type(feil).__name__)
        return None
    if treff is None:
        return None
    tekst, dato = treff
    return Begrunnelse(tekst, MERKE_OPPTAK, dato)


def testtekst(inp, prediksjon, merke: str = MERKE_TEST, naa=None, prediktor_navn: Optional[str] = None) -> Begrunnelse:
    """Mal-teksten med et testmodus-merke. Med merket «Testmodus», ``naa`` og ``prediktor_navn`` vises heller et
    opptak av et ekte svar når det finnes og fortsatt passer (E3-S06). Tilbakefallsmerkene gir alltid malen."""
    if merke == MERKE_TEST and naa is not None and prediktor_navn is not None:
        from app.begrunnelse.input import lag_fakta
        from app.begrunnelse.openrouter_klient import PROMPT_FIL

        opptak = _fra_opptak(naa, inp.voyageid, prediktor_navn, lambda: lag_fakta(inp, prediksjon), PROMPT_FIL)
        if opptak is not None:
            return opptak
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


def cachet(inp, prediksjon, prediktor_navn: str, naa=None) -> Optional[Begrunnelse]:
    """Det siden kan vise uten å vente: opptaket eller mal-teksten i testmodus, et cachet svar i ekte modus, ellers
    None.

    Gjør aldri et kall og teller ingenting. Med None viser siden «Henter forklaring …» og henter svaret med POST.
    """
    _sjekk(inp, prediksjon)
    if konfig.modus() == "test":
        return testtekst(inp, prediksjon, naa=naa, prediktor_navn=prediktor_navn)
    with _laas:
        return _fra_cache((inp.voyageid, prediktor_navn))


def _ekte(inp, prediksjon, api_nokkel: str) -> Tuple[Optional[str], Optional[str]]:
    """Ett ekte kall med kontroll. Gir (tekst, None) eller (None, årsakskode)."""
    from app.begrunnelse.input import lag_fakta
    from app.begrunnelse.klartekst import er_modellvurdert, innledning
    from app.begrunnelse.kontroll import retning

    return _kall_og_kontroller(
        lag_fakta(inp, prediksjon), api_nokkel, forventet_forsinket=prediksjon.forventet_forsinket,
        retning=retning(prediksjon), konklusjon=innledning(inp, prediksjon), modellrad=er_modellvurdert(prediksjon))


def _kall_og_kontroller(fakta, api_nokkel: str, prompt_fil=None, **regler) -> Tuple[Optional[str], Optional[str]]:
    """Ett ekte kall med kontroll, felles for begrunnelsen og briefen. ``regler`` går til ``kontroller``."""
    from app.begrunnelse import openrouter_klient
    from app.begrunnelse.kontroll import kontroller

    system, bruker = openrouter_klient.bygg_prompt(fakta, prompt_fil or openrouter_klient.PROMPT_FIL)
    try:
        tekst = openrouter_klient.kall(
            system, bruker, modell=konfig.modellstreng(), nokkel=api_nokkel,
            timeout=konfig.timeout_s(), transport=transport, resonnering=konfig.resonnering(),
        )
    except openrouter_klient.KlientFeil as feil:
        return None, feil.kode
    regel = kontroller(tekst, fakta, **regler)
    if regel:
        return None, f"kontroll_{regel}"
    return tekst.strip(), None


def _hent_med_cache(nokkel, ekte_kall: Callable[[str], Tuple[Optional[str], Optional[str]]],
                    reserve: Callable[[str], Begrunnelse], logg: Callable[[str], None]) -> Begrunnelse:
    """Den felles veien i ekte modus for begrunnelsen og briefen: cache, nøkkel, kallgrense, ett kall, kontroll og
    tilbakefall. ``reserve(merke)`` gir mal-teksten med et merke. Kaster aldri for feil hos leverandøren."""
    global _kall
    with _laas:
        svar = _fra_cache(nokkel)
    if svar is not None:
        return svar
    api_nokkel = konfig.api_nokkel()
    if api_nokkel is None:
        logg("mangler_nokkel")
        return reserve(MERKE_FEILET)
    with _laas:
        svar = _fra_cache(nokkel)  # en annen forespørsel kan ha blitt ferdig i mellomtiden
        if svar is not None:
            return svar
        if _kall >= konfig.maks_kall():
            logg("kallgrense")
            return reserve(MERKE_GRENSE)
        _kall += 1
    try:
        tekst, kode = ekte_kall(api_nokkel)
    except Exception as feil:  # uventet feil: aldri HTTP 500, og meldingen logges ikke (den kan inneholde hva som helst)
        tekst, kode = None, f"uventet_{type(feil).__name__}"
    if tekst is not None:
        svar, utloper = Begrunnelse(tekst, MERKE_KI), None
    else:
        logg(kode)
        svar, utloper = reserve(MERKE_FEILET), klokke() + konfig.feil_ttl_s()
    with _laas:
        _cache[nokkel] = (svar, utloper)
    return svar


def hent_begrunnelse(inp, prediksjon, prediktor_navn: str, naa=None) -> Begrunnelse:
    """Begrunnelsen for ett anløp. Kaster aldri for feil hos leverandøren eller i svaret: alt gir testmodus-tekst.
    Opptak (E3-S06) brukes bare i testmodus, aldri i ekte modus."""
    _sjekk(inp, prediksjon)
    if konfig.modus() == "test":
        return testtekst(inp, prediksjon, naa=naa, prediktor_navn=prediktor_navn)
    return _hent_med_cache(
        (inp.voyageid, prediktor_navn),
        lambda api_nokkel: _ekte(inp, prediksjon, api_nokkel),
        lambda merke: testtekst(inp, prediksjon, merke),
        lambda kode: _logg(kode, inp, prediktor_navn),
    )


# --- Forstyrrelsesbriefen (E3-S05, PRD FR12) -------------------------------------------------------------------
#
# Samme adapter og regler som begrunnelsen. Uten varsler, eller når baselinen er aktiv, skriver appen briefen selv
# (spec-valg B1): ingen kall, ingen cache og ingenting som teller mot grensen. Med varsler skriver appen innledningen
# (B2), og i ekte modus legger modellen til grunnene. Cachenøkkelen er («brief», nå, prediktor), og briefen deler
# kallgrensen ``LLM_MAKS_KALL`` med begrunnelsene.


def _sjekk_par(par) -> list:
    par = list(par)
    for inp, prediksjon in par:
        _sjekk(inp, prediksjon)
    return par


def _brief_nokkel(naa, prediktor_navn: str):
    return ("brief", naa.isoformat(), prediktor_navn)


def _logg_brief(kode: str, naa, prediktor_navn: str) -> None:
    logger.warning("brief: %s naa=%s prediktor=%s", kode, naa.isoformat(), prediktor_navn)


def testbrief(par, merke: str = MERKE_TEST, naa=None, prediktor_navn: Optional[str] = None) -> Begrunnelse:
    """Briefen uten kall: appens egen brief uten varsler (merket «Laget av appen»), ellers mal-briefen med ``merke``.
    Med merket «Testmodus», ``naa`` og ``prediktor_navn`` vises heller et opptak når det finnes og fortsatt passer
    (E3-S06). Appens egen brief tas aldri opp."""
    from app.begrunnelse.klartekst import velg_varslede
    from app.begrunnelse.testmodus import app_brief, brief_mal

    par = _sjekk_par(par)
    valgte, antall = velg_varslede(par)
    if not antall:
        return Begrunnelse(app_brief(par), MERKE_APP)
    if merke == MERKE_TEST and naa is not None and prediktor_navn is not None:
        from app.begrunnelse.input import lag_brief_fakta
        from app.begrunnelse.openrouter_klient import PROMPT_BRIEF_FIL

        opptak = _fra_opptak(naa, BRIEF_NOKKEL, prediktor_navn,
                             lambda: lag_brief_fakta(par, naa, valgte, antall), PROMPT_BRIEF_FIL)
        if opptak is not None:
            return opptak
    return Begrunnelse(brief_mal(valgte, antall), merke)


def cachet_brief(par, naa, prediktor_navn: str) -> Optional[Begrunnelse]:
    """Det skjerm A kan vise uten å vente: appens egen brief (B1), mal-briefen i testmodus, et cachet svar i ekte
    modus, ellers None. Gjør aldri et kall. Med None viser siden «Henter oversikt …» og henter briefen med POST."""
    par = _sjekk_par(par)
    if konfig.modus() == "test":
        return testbrief(par, naa=naa, prediktor_navn=prediktor_navn)
    svar = testbrief(par)
    if svar.merke == MERKE_APP:
        return svar
    with _laas:
        return _fra_cache(_brief_nokkel(naa, prediktor_navn))


def hent_brief(par, naa, prediktor_navn: str) -> Begrunnelse:
    """Briefen for vinduet. ``par`` er (``PrediksjonsInput``, ``Prediksjon``) for alle anløp i vinduet.
    Kaster aldri for feil hos leverandøren eller i svaret: alt gir testmodus-tekst."""
    par = _sjekk_par(par)
    if konfig.modus() == "test":
        return testbrief(par, naa=naa, prediktor_navn=prediktor_navn)
    svar = testbrief(par)
    if svar.merke == MERKE_APP:
        return svar

    def ekte_kall(api_nokkel):
        from app.begrunnelse import openrouter_klient
        from app.begrunnelse.input import brief_setninger_igjen, lag_brief_fakta
        from app.begrunnelse.klartekst import brief_innledning, velg_varslede
        from app.begrunnelse.kontroll import BRIEF_MAKS_TEGN, BRIEF_MIN_SETNINGER, antall_setninger

        valgte, antall = velg_varslede(par)
        start = brief_innledning(valgte, antall)
        # Høyst innledningen pluss setningene modellen får legge til (``brief-v3``), og innenfor 3–5 (spec).
        return _kall_og_kontroller(
            lag_brief_fakta(par, naa, valgte, antall), api_nokkel, openrouter_klient.PROMPT_BRIEF_FIL,
            forventet_forsinket=True, retning=0, konklusjon=start, modellrad=True,
            maks_tegn=BRIEF_MAKS_TEGN, min_setninger=BRIEF_MIN_SETNINGER,
            maks_setninger=antall_setninger(start) + brief_setninger_igjen(start, len(valgte)))

    return _hent_med_cache(
        _brief_nokkel(naa, prediktor_navn),
        ekte_kall,
        lambda merke: testbrief(par, merke),
        lambda kode: _logg_brief(kode, naa, prediktor_navn),
    )
