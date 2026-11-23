"""Flask-appen for ankomstprediksjon i Bergen Havn (arkitektur A1, §5)."""
import datetime as dt
import logging

from flask import Flask, abort, current_app, jsonify, render_template

from app import begrunnelse
from app.begrunnelse.testmodus import GRUPPE_TEKST, MERKE_FEILET, VARSEL_GRENSE_MIN
from app.data import anlop_i_vindu
from app.panel import lag_panel
from app.prediksjon import VINDU_TIMER, i_testperioden, lag_input, velg_prediktor_med_merknad
from app.visning import (DELEGERT_TEKST, OSLO, gruppe_visning, horisont_etikett, tall, ukedag_dato_klokke,
                         ukedag_klokke)

# Standard «nå» (UX §2): ons 08.10.2025 08:00 norsk tid.
STANDARD_NAA = dt.datetime(2025, 10, 8, 8, 0, tzinfo=OSLO)

# Kort forklaring i prediktor-stripa (UX §2). Ukjent prediktor får bare navnet.
PREDIKTOR_BESKRIVELSE = {
    "Kalibrert baseline": "rapportert ETA justert med median liggetid.",
    "Modell v1": "6 t / 24 t, rapportert ETA justert med modellens predikerte avvik. "
                 "Anløp modellen ikke dekker, får kalibrert baseline.",
}



def _par(naa):
    """(prediktor, merknad, par): (``PrediksjonsInput``, ``Prediksjon``) for anløpene i vinduet, sortert på
    uavrundet predikert ankomst. Lista og briefen (E3-S05) bygges fra de samme parene."""
    prediktor, merknad = velg_prediktor_med_merknad(naa=naa)
    inputs = [lag_input(a, naa) for a in anlop_i_vindu(naa, timer=VINDU_TIMER)]
    prediksjoner = prediktor.prediker(inputs, naa)
    par = sorted(
        zip(inputs, prediksjoner),
        key=lambda ip: (ip[1].predikert_ankomst, ip[0].eta_reported, ip[0].voyageid),
    )
    return prediktor, merknad, par


def _rader(naa, par_i_vindu=None):
    """Anløp i vinduet med prediksjon, sortert på uavrundet predikert ankomst.

    Radene bygges bare fra ``PrediksjonsInput`` og ``Prediksjon``, så ingen fasit
    (``faktisk_ankomst``, ``status_in_area``) kan havne i malen.
    """
    prediktor, merknad, par = par_i_vindu or _par(naa)
    rader = [
        {
            "voyageid": inp.voyageid,
            "skip": inp.shipname,
            "gruppe": gruppe_visning(inp.ship_group),
            "rapportert": ukedag_klokke(inp.eta_reported),
            "predikert": ukedag_klokke(p.predikert_ankomst),
            "for_naa": p.predikert_ankomst < naa,
            "horisont": horisont_etikett(inp.horisont_timer),
            "varsel": p.forventet_forsinket,
            "varsel_grunn": DELEGERT_TEKST.get(p.forklaring.get("delegert")),
        }
        for inp, p in par
    ]
    return prediktor, merknad, rader


def _ett_anlop(voyageid, naa):
    """(prediktor, input, prediksjon) for seilasen i vinduet, eller None. Anløpet blir aldri med videre: rutene og
    AI-laget får bare ``PrediksjonsInput`` og ``Prediksjon``."""
    for a in anlop_i_vindu(naa, timer=VINDU_TIMER):
        if a.voyageid == voyageid:
            prediktor, _ = velg_prediktor_med_merknad(naa=naa)
            inp = lag_input(a, naa)
            return prediktor, inp, prediktor.prediker([inp], naa)[0]
    return None


def _minutter(verdi, desimaler=0, fortegn=False):
    """«64,2», «+152» eller «−12» (ekte minustegn), samme format som inputen til AI-laget."""
    tekst = tall(verdi, desimaler)
    return f"+{tekst}" if fortegn and not tekst.startswith("\u2212") and tekst != "0" else tekst


def metode_tekst(inp, p):
    """«Slik ble prediksjonen laget» på skjerm C (FR7), per gruppe og metode."""
    f = p.forklaring
    if f.get("metode") == "modell":
        offset = _minutter(f["offset_ovrige_min"], 1)
        return [
            f"Modell v1 ({horisont_etikett(inp.horisont_timer)}): kalibrert baseline (rapportert ETA − {offset} min) "
            f"justert med modellens predikerte avvik på {_minutter(f['predikert_avvik_min'], fortegn=True)} min.",
            f"Modellen varsler når predikert avvik er over {VARSEL_GRENSE_MIN} min.",
        ]
    linjer = []
    if f.get("offset_minutter") is not None:
        offset = _minutter(f["offset_minutter"], 1)
        linjer += [f"Kalibrert baseline: rapportert ETA − {offset} min.",
                   f"{offset} min er median tid fra sonegrense til kai for "
                   f"{GRUPPE_TEKST.get(f.get('gruppe'), 'gruppen')} i treningsdata."]
    grunn = DELEGERT_TEKST.get(f.get("delegert"))
    if grunn:
        linjer.append(f"Modell v1 vurderer ikke dette anløpet ({grunn}), så det får kalibrert baseline.")
    return linjer


def create_app(config=None):
    """Lag appen. Leser ingen .env. Appen skal starte uten (NFR1, NFR6)."""
    app = Flask(__name__)
    app.config["STANDARD_NAA"] = STANDARD_NAA
    if config:
        app.config.update(config)

    @app.get("/")
    def forside():
        naa = current_app.config["STANDARD_NAA"]
        prediktor, merknad, par = _par(naa)
        _, _, rader = _rader(naa, (prediktor, merknad, par))
        return render_template(
            "forside.html",
            rader=rader,
            # E3-S05 (FR12, FR11a): briefen vises med en gang når den finnes uten kall (appens egen brief, testmodus
            # eller cache). Ellers står «Henter oversikt …», og nettleseren henter den med POST /brief.
            brief=begrunnelse.cachet_brief(par, naa, prediktor.navn) if par else None,
            brief_mal=begrunnelse.testbrief(par).tekst if par else None,
            prediktor_navn=prediktor.navn,
            prediktor_beskrivelse=PREDIKTOR_BESKRIVELSE.get(prediktor.navn),
            kan_varsle=prediktor.kan_varsle,
            prediktor_merknad=merknad,
            # Beslutning 5: modellen vist for et vindu før testperioden er trent på de anløpene.
            i_utvalg=prediktor.kan_varsle and not i_testperioden(naa),
            vindu_fra=ukedag_dato_klokke(naa),
            vindu_til=ukedag_dato_klokke(
                naa.astimezone(dt.timezone.utc) + dt.timedelta(hours=VINDU_TIMER)
            ),
            # E2-S09: modell mot baseline, lest fra metrikker.json. Uavhengig av vinduet og prediktoren.
            panel=lag_panel(),
        )

    @app.get("/anlop/<int:voyageid>")
    def anlop(voyageid):
        """Skjerm C (UX §4, FR7, FR11). Rendres uten å kalle språkmodellen (FR11a): et cachet svar vises med en
        gang, ellers står «Henter forklaring …» og nettleseren henter svaret med POST."""
        naa = current_app.config["STANDARD_NAA"]
        treff = _ett_anlop(voyageid, naa)
        if treff is None:
            return render_template("anlop.html", ukjent=True, voyageid=voyageid), 404
        prediktor, inp, p = treff
        return render_template(
            "anlop.html",
            ukjent=False,
            inp=inp,
            gruppe=gruppe_visning(inp.ship_group),
            rapportert=ukedag_dato_klokke(inp.eta_reported),
            predikert=ukedag_dato_klokke(p.predikert_ankomst),
            horisont=horisont_etikett(inp.horisont_timer),
            kuttpunkt=ukedag_dato_klokke(inp.t_kutt),
            kan_varsle=prediktor.kan_varsle,
            varsel=p.forventet_forsinket,
            varsel_grunn=DELEGERT_TEKST.get(p.forklaring.get("delegert")),
            metode=metode_tekst(inp, p),
            prediktor_navn=prediktor.navn,
            begrunnelse=begrunnelse.cachet(inp, p, prediktor.navn),
            mal=begrunnelse.testtekst(inp, p).tekst,
        )

    @app.post("/anlop/<int:voyageid>/begrunnelse")
    def begrunnelse_json(voyageid):
        """Begrunnelsen som JSON ``{tekst, merke}``. Alltid 200 for en kjent seilas, også når kallet feiler.
        POST, så søkeroboter ikke utløser betalte kall."""
        treff = _ett_anlop(voyageid, current_app.config["STANDARD_NAA"])
        if treff is None:
            abort(404)
        prediktor, inp, p = treff
        try:
            svar = begrunnelse.hent_begrunnelse(inp, p, prediktor.navn)
        except Exception as feil:  # aldri HTTP 500 for begrunnelsen; meldingen logges ikke
            logging.getLogger("app.begrunnelse").warning(
                "begrunnelse: uventet_%s voyageid=%s prediktor=%s", type(feil).__name__, voyageid, prediktor.navn)
            svar = begrunnelse.testtekst(inp, p, MERKE_FEILET)
        return jsonify(svar.som_dict())

    @app.post("/brief")
    def brief_json():
        """Briefen for vinduet som JSON ``{tekst, merke}``. Alltid 200, også når kallet feiler (E3-S05, FR11a).
        POST, så søkeroboter ikke utløser betalte kall."""
        naa = current_app.config["STANDARD_NAA"]
        prediktor, _, par = _par(naa)
        try:
            svar = begrunnelse.hent_brief(par, naa, prediktor.navn)
        except Exception as feil:  # aldri HTTP 500 for briefen; meldingen logges ikke
            logging.getLogger("app.begrunnelse").warning(
                "brief: uventet_%s naa=%s prediktor=%s", type(feil).__name__, naa.isoformat(), prediktor.navn)
            svar = begrunnelse.testbrief(par, MERKE_FEILET)
        return jsonify(svar.som_dict())

    return app
