"""Ta opp ekte svar for demovinduet (E3-S06, PRD FR13).

Kjører ekte modus én gang for demovinduet gjennom den vanlige adapteren (``hent_begrunnelse``, ``hent_brief``), så
hvert svar har bestått ``kontroller``. Bare svar merket «KI-GENERERT» skrives til ``data/begrunnelser_opptak.json``.
Et avvist eller feilet svar utelates (appen viser malen for det anløpet) og står i oppsummeringen med årsakskoden.
Appens egen brief uten varsler eller på baselinen (spec-valg B1) gjør ingen kall og tas ikke opp.

Bare 08.10.2025 08:00 (``STANDARD_NAA``) tas opp (spec-valg O1). Vinduet ligger i testperioden: opptaket er bare
til visning (spec-valg O3), og ingen fasit sendes eller leses.

Bruk:
    .venv/bin/python scripts/ta_opp_begrunnelser.py           # bare planen, ingen kall
    LLM_MODUS=ekte OPENROUTER_API_KEY=… .venv/bin/python scripts/ta_opp_begrunnelser.py --kjor

Uten ``--kjor`` skrives bare planen (vindu, antall kall), og ingen modell kjøres. Med ``--kjor`` kreves
``LLM_MODUS=ekte`` og ``OPENROUTER_API_KEY`` i miljøet. Skriptet leser ingen ``.env``, og nøkkelen skrives aldri ut
eller til fila. Kallgrensen ``LLM_MAKS_KALL`` heves bare for skriptets egen prosess.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

import app.begrunnelse as begrunnelse  # noqa: E402
from app import STANDARD_NAA, _par  # noqa: E402
import app.begrunnelse.testmodus as testmodus  # noqa: E402
from app.begrunnelse import konfig, openrouter_klient  # noqa: E402
from app.begrunnelse.testmodus import (BRIEF_NOKKEL, MERKE_APP, MERKE_KI, OPPTAK_FORMAT, fakta_hash,  # noqa: E402
                                       les_opptak, opptak_nokkel)
from app.data import anlop_i_vindu  # noqa: E402
from app.prediksjon import VINDU_TIMER, velg_prediktor_med_merknad  # noqa: E402
from app.visning import OSLO, ukedag_dato_klokke  # noqa: E402

DEMOVINDUER = (STANDARD_NAA,)  # spec-valg O1: bare 08.10.2025 08:00
MERKNAD = ("Opptak av ekte svar for demovinduet (E3-S06). Laget av scripts/ta_opp_begrunnelser.py, lest av appen "
           "i testmodus. Ikke rediger for hånd.")


class Stopp(Exception):
    """Skriptet kan ikke kjøre (mangler ekte modus eller nøkkel). Meldingen inneholder aldri nøkkelen."""


def _versjoner() -> dict:
    return {"begrunnelse": openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_FIL),
            "brief": openrouter_klient.prompt_versjon(openrouter_klient.PROMPT_BRIEF_FIL)}


def _plan_for(naa) -> dict:
    """Antall kall for vinduet uten å kjøre noen modell: én begrunnelse per anløp og høyst én brief."""
    prediktor, _ = velg_prediktor_med_merknad(naa=naa)
    antall = len(anlop_i_vindu(naa, timer=VINDU_TIMER))
    return {"naa": naa, "prediktor": prediktor.navn, "anlop": antall, "maks_kall": antall + (1 if antall else 0)}


def _les_fil(fil: Path) -> list:
    """Oppføringene i fila som de står, eller [] når fila mangler eller er ugyldig."""
    try:
        data = json.loads(Path(fil).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    opptak = data.get("opptak") if isinstance(data, dict) else None
    return opptak if isinstance(opptak, list) else []


def advarsler(fil: Path) -> list:
    """Oppføringer i fila som appen ikke vil bruke fordi prompt-versjonen er endret (da vises malen)."""
    versjoner = _versjoner()
    try:
        oppforinger = les_opptak(fil).values()
    except (OSError, ValueError):
        return []
    ut = []
    for o in oppforinger:
        dagens = versjoner["brief" if o["anlop"] == BRIEF_NOKKEL else "begrunnelse"]
        if o["prompt_versjon"] != dagens:
            ut.append(f"Advarsel: opptaket for {o['anlop']} ({o['naa']}) har {o['prompt_versjon']}, men prompten er "
                      f"{dagens}. Appen viser malen for det til det tas opp på nytt.")
    return ut


def _fil(fil) -> Path:
    """``fil`` eller ``testmodus.OPPTAK_FIL``, slått opp ved kallet (ikke ved import)."""
    return Path(fil) if fil is not None else Path(testmodus.OPPTAK_FIL)


def plan(vinduer=DEMOVINDUER, fil=None, skriv=print) -> int:
    """Skriver planen og gir høyst antall kall. Gjør ingen kall og kjører ingen modell."""
    fil = _fil(fil)
    versjoner = _versjoner()
    skriv("Plan for opptak (ingen kall uten --kjor):")
    totalt = 0
    for naa in vinduer:
        p = _plan_for(naa)
        totalt += p["maks_kall"]
        skriv(f"  Vindu {ukedag_dato_klokke(naa)}: {p['anlop']} anløp, prediktor {p['prediktor']}. "
              f"{p['anlop']} begrunnelser og høyst 1 brief (ingen kall for briefen uten varsler, B1).")
    skriv(f"  Høyst {totalt} kall i alt. Prompt: {versjoner['begrunnelse']}, {versjoner['brief']}. "
          f"Modell: {konfig.modellstreng()}.")
    skriv(f"  Fil: {fil} ({len(_les_fil(fil))} oppføringer nå).")
    for linje in advarsler(fil):
        skriv(f"  {linje}")
    return totalt


class _Koder(logging.Handler):
    """Samler årsakskodene adapteren logger (``begrunnelse: <kode> …`` / ``brief: <kode> …``)."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.koder = []

    def emit(self, record):
        if isinstance(record.args, tuple) and record.args and str(record.msg).startswith(("begrunnelse:", "brief:")):
            self.koder.append(str(record.args[0]))


def _oppforing(naa, anlop, prediktor_navn, versjon, fakta, tekst, skip=None) -> dict:
    o = {"naa": naa.isoformat(), "anlop": anlop, "prediktor": prediktor_navn, "prompt_versjon": versjon,
         "modell": konfig.modellstreng(), "tatt_opp": dt.datetime.now(OSLO).isoformat(timespec="seconds"),
         "fakta_sha256": fakta_hash(fakta), "tekst": tekst}
    if skip is not None:
        o["skip"] = skip
    return o


def _skriv_atomisk(fil: Path, tekst: str) -> None:
    """Skriv til en midlertidig fil ved siden av og bytt den inn med ``os.replace``, så et avbrudd aldri gir en
    halv fil."""
    import tempfile

    fil.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{fil.name}.", suffix=".tmp", dir=fil.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as ut:
            ut.write(tekst)
        os.replace(tmp, fil)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def kjor(vinduer=DEMOVINDUER, fil=None, skriv=print) -> dict:
    """Ta opp svarene og skriv fila. Gir oppsummeringen ``{tatt_opp, avvist, b1, kall}``."""
    fil = _fil(fil)
    from app.begrunnelse.input import lag_brief_fakta, lag_fakta
    from app.begrunnelse.klartekst import velg_varslede

    if konfig.modus() != "ekte":
        raise Stopp("--kjor krever LLM_MODUS=ekte i miljøet.")
    if konfig.api_nokkel() is None:
        raise Stopp(f"--kjor krever {konfig.NOKKEL_VARIABEL} i miljøet. Skriptet leser ikke .env.")
    versjoner = _versjoner()
    gammel_grense = os.environ.get("LLM_MAKS_KALL")
    os.environ["LLM_MAKS_KALL"] = str(sum(_plan_for(naa)["maks_kall"] for naa in vinduer))  # bare denne prosessen
    koder = _Koder()
    logging.getLogger("app.begrunnelse").addHandler(koder)
    nye, avvist, b1 = [], [], []

    def utfall(svar, hva):
        if svar.merke == MERKE_KI:
            return True
        kode = koder.koder[-1] if koder.koder else svar.merke
        avvist.append({"hva": hva, "kode": kode})
        return False

    try:
        for naa in vinduer:
            prediktor, _, par = _par(naa)
            for inp, p in par:
                koder.koder.clear()
                svar = begrunnelse.hent_begrunnelse(inp, p, prediktor.navn)
                if utfall(svar, f"{inp.shipname} ({inp.voyageid})"):
                    nye.append(_oppforing(naa, inp.voyageid, prediktor.navn, versjoner["begrunnelse"],
                                          lag_fakta(inp, p), svar.tekst, inp.shipname))
            if not par:
                continue
            if begrunnelse.testbrief(par).merke == MERKE_APP:
                b1.append(naa.isoformat())
                continue
            koder.koder.clear()
            svar = begrunnelse.hent_brief(par, naa, prediktor.navn)
            if utfall(svar, f"brief ({naa.isoformat()})"):
                valgte, antall = velg_varslede(par)
                nye.append(_oppforing(naa, BRIEF_NOKKEL, prediktor.navn, versjoner["brief"],
                                      lag_brief_fakta(par, naa, valgte, antall), svar.tekst))
    finally:
        logging.getLogger("app.begrunnelse").removeHandler(koder)
        if gammel_grense is None:
            os.environ.pop("LLM_MAKS_KALL", None)
        else:
            os.environ["LLM_MAKS_KALL"] = gammel_grense

    # Et nytt godkjent svar erstatter det gamle med samme nøkkel. Gamle opptak uten nytt svar (kallet feilet eller
    # ble avvist) beholdes, og det samme gjør andre vinduer. Oppføringer uten form (ikke dict, ``naa`` ikke tekst)
    # droppes, så sorteringen ikke feiler etter de betalte kallene.
    def nokkel(o):
        return opptak_nokkel(o["naa"], o.get("anlop"), o.get("prediktor"))

    nye_nokler = {nokkel(o) for o in nye}
    beholdt = [o for o in _les_fil(fil)
               if isinstance(o, dict) and isinstance(o.get("naa"), str) and nokkel(o) not in nye_nokler]
    alle = sorted(beholdt + nye, key=lambda o: (o["naa"], str(o.get("anlop")), str(o.get("prediktor"))))
    _skriv_atomisk(fil, json.dumps({"format": OPPTAK_FORMAT, "merknad": MERKNAD, "opptak": alle},
                                   ensure_ascii=False, indent=2) + "\n")

    oppsummering = {"tatt_opp": len(nye), "avvist": avvist, "b1": b1, "kall": begrunnelse.antall_kall()}
    skriv(f"Tatt opp: {len(nye)} svar til {fil}. Ekte kall: {oppsummering['kall']}.")
    for a in avvist:
        skriv(f"  Utelatt: {a['hva']}: {a['kode']} (appen viser malen)")
    for naa in b1:
        skriv(f"  Briefen for {naa} tas ikke opp: appen skriver den selv (B1), ingen kall.")
    return oppsummering


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ta opp ekte svar for demovinduet (E3-S06).")
    parser.add_argument("--kjor", action="store_true", help="gjør de ekte kallene (krever LLM_MODUS=ekte og nøkkel)")
    parser.add_argument("--fil", type=Path, default=None, help="opptaksfila (standard data/begrunnelser_opptak.json)")
    args = parser.parse_args(argv)
    if not args.kjor:
        plan(fil=args.fil)
        return 0
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    try:
        kjor(fil=args.fil)
    except Stopp as feil:
        print(f"Stopp: {feil}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
