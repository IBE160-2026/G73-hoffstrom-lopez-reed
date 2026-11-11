"""Flask-appen for ankomstprediksjon i Bergen Havn (arkitektur A1, §5)."""
import datetime as dt

from flask import Flask, current_app, render_template

from app.data import anlop_i_vindu
from app.prediksjon import VINDU_TIMER, i_testperioden, lag_input, velg_prediktor_med_merknad
from app.visning import OSLO, horisont_etikett, ukedag_dato_klokke, ukedag_klokke

# Standard «nå» (UX §2): ons 08.10.2025 08:00 norsk tid.
STANDARD_NAA = dt.datetime(2025, 10, 8, 8, 0, tzinfo=OSLO)

# Kort forklaring i prediktor-stripa (UX §2). Ukjent prediktor får bare navnet.
PREDIKTOR_BESKRIVELSE = {
    "Kalibrert baseline": "rapportert ETA justert med median liggetid.",
    "Modell v1": "6 t / 24 t, rapportert ETA justert med modellens predikerte avvik. "
                 "Anløp modellen ikke dekker, får kalibrert baseline.",
}

# Synlig grunn i Varsel når modellen har delegert raden til baselinen (beslutning 3 i E2-S08-specen).
# «ankomstsone» er gruppens interne ord; på skjermen står «havneområdet».
DELEGERT_TEKST = {
    "passasjer": "rutegående: bare baseline",
    "ingen_tilstand": "ingen AIS-tilstand",
    "i_sonen_ved_kutt": "allerede i havneområdet",
    "ingen_featurerad": "ingen modelldata ved kuttet",
}


def _rader(naa):
    """Anløp i vinduet med prediksjon, sortert på uavrundet predikert ankomst.

    Radene bygges bare fra ``PrediksjonsInput`` og ``Prediksjon``, så ingen fasit
    (``faktisk_ankomst``, ``status_in_area``) kan havne i malen.
    """
    prediktor, merknad = velg_prediktor_med_merknad(naa=naa)
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
            "varsel": p.forventet_forsinket,
            "varsel_grunn": DELEGERT_TEKST.get(p.forklaring.get("delegert")),
        }
        for inp, p in par
    ]
    return prediktor, merknad, rader


def create_app(config=None):
    """Lag appen. Leser ingen .env. Appen skal starte uten (NFR1, NFR6)."""
    app = Flask(__name__)
    app.config["STANDARD_NAA"] = STANDARD_NAA
    if config:
        app.config.update(config)

    @app.get("/")
    def forside():
        naa = current_app.config["STANDARD_NAA"]
        prediktor, merknad, rader = _rader(naa)
        return render_template(
            "forside.html",
            rader=rader,
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
        )

    return app
