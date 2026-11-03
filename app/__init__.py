"""Flask-appen for ankomstprediksjon i Bergen Havn (arkitektur A1, §5)."""
import datetime as dt

from flask import Flask, current_app, render_template

from app.data import anlop_i_vindu
from app.prediksjon import lag_input, velg_prediktor
from app.visning import OSLO, horisont_etikett, ukedag_dato_klokke, ukedag_klokke

# Standard «nå» (UX §2): ons 08.10.2025 08:00 norsk tid.
STANDARD_NAA = dt.datetime(2025, 10, 8, 8, 0, tzinfo=OSLO)
VINDU_TIMER = 24

# Kort forklaring i prediktor-stripa (UX §2). Ukjent prediktor får bare navnet.
PREDIKTOR_BESKRIVELSE = {
    "Kalibrert baseline": "rapportert ETA justert med median liggetid.",
}


def _rader(naa):
    """Anløp i vinduet med prediksjon, sortert på uavrundet predikert ankomst.

    Radene bygges bare fra ``PrediksjonsInput`` og ``Prediksjon``, så ingen fasit
    (``faktisk_ankomst``, ``status_in_area``) kan havne i malen.
    """
    prediktor = velg_prediktor()
    inputs = [lag_input(a, naa) for a in anlop_i_vindu(naa, timer=VINDU_TIMER)]
    prediksjoner = prediktor.prediker(inputs, naa)
    par = sorted(
        zip(inputs, prediksjoner),
        key=lambda ip: (ip[1].predikert_ankomst, ip[0].eta_reported, ip[0].voyageid),
    )
    rader = [
        {
            "skip": inp.shipname,
            "gruppe": inp.ship_group,
            "rapportert": ukedag_klokke(inp.eta_reported),
            "predikert": ukedag_klokke(p.predikert_ankomst),
            "for_naa": p.predikert_ankomst < naa,
            "horisont": horisont_etikett(inp.horisont_timer),
        }
        for inp, p in par
    ]
    return prediktor, rader


def create_app(config=None):
    """Lag appen. Leser ingen .env. Appen skal starte uten (NFR1, NFR6)."""
    app = Flask(__name__)
    app.config["STANDARD_NAA"] = STANDARD_NAA
    if config:
        app.config.update(config)

    @app.get("/")
    def forside():
        naa = current_app.config["STANDARD_NAA"]
        prediktor, rader = _rader(naa)
        return render_template(
            "forside.html",
            rader=rader,
            prediktor_navn=prediktor.navn,
            prediktor_beskrivelse=PREDIKTOR_BESKRIVELSE.get(prediktor.navn),
            kan_varsle=prediktor.kan_varsle,
            vindu_fra=ukedag_dato_klokke(naa),
            vindu_til=ukedag_dato_klokke(
                naa.astimezone(dt.timezone.utc) + dt.timedelta(hours=VINDU_TIMER)
            ),
        )

    return app
