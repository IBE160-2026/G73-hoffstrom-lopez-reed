import datetime as dt
import json
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import pytest

from app import create_app

# Et vindu i testperioden uten anløp (pause i dataene 01.02–06.02.2026).
TOMT_NAA = dt.datetime(2026, 2, 3, 8, 0, tzinfo=ZoneInfo("Europe/Oslo"))

# Et vindu i valideringsdelen (siste 20 % av train, kronologisk), langt før testperioden (14.09.2025).
# Modellrader rendres bare her (E2-S08, regelen om testrader). Vinduet har både varsel, ikke varsel og alle
# delegeringsgrunnene unntatt ``ingen_featurerad``.
VALIDERING_NAA = dt.datetime(2025, 8, 15, 8, 0, tzinfo=ZoneInfo("Europe/Oslo"))


# Kontrakttestene og modellprediktortestene får kjøre modellen på testrader (E2-S07). Ingen andre.
TESTRADER_TILLATT = {"test_prediktor_kontrakt", "test_modellprediktor"}


@pytest.fixture(autouse=True)
def _ingen_testkjoring(monkeypatch, tmp_path_factory):
    """Testene avhenger ikke av den ekte ``metrikker.json``: ``testkjoringer = 0`` med mindre testen overstyrer."""
    import app.prediksjon as prediksjon

    sti = tmp_path_factory.mktemp("metrikker_laast") / "metrikker.json"  # egen mappe: tmp_path til testen er urørt
    sti.write_text(json.dumps({"testkjoringer": 0}), encoding="utf-8")
    monkeypatch.setattr(prediksjon, "METRIKKER_FIL", sti)


@pytest.fixture(autouse=True)
def _ingen_modell_paa_testrader(request, monkeypatch):
    """Håndhever regelen om testrader (E2-S08): ``ModellPrediktor.prediker`` feiler FØR den kjøres hvis en input har
    rapportert ETA ved eller etter testperiodens start."""
    if request.module.__name__.rsplit(".", 1)[-1] in TESTRADER_TILLATT:
        return
    import app.prediksjon as prediksjon
    from app.prediksjon.modell import ModellPrediktor

    ekte = ModellPrediktor.prediker

    def vaktet(self, inputs, naa):
        start = prediksjon.testperiode_start()
        for inp in inputs:
            if getattr(inp, "eta_reported", None) is not None and inp.eta_reported >= start:
                raise AssertionError(f"modellen kjørt på en testrad (voyageid {inp.voyageid}) utenfor kontrakttestene")
        return ekte(self, inputs, naa)

    monkeypatch.setattr(ModellPrediktor, "prediker", vaktet)


@pytest.fixture
def app():
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def validering_client():
    return create_app({"TESTING": True, "STANDARD_NAA": VALIDERING_NAA}).test_client()


@pytest.fixture
def tomt_client():
    return create_app({"TESTING": True, "STANDARD_NAA": TOMT_NAA}).test_client()


# ---------------------------------------------------------------------------
# Liten HTML-parser for strukturtestene (bare stdlib, ingen nye avhengigheter).

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []  # Node eller str

    def iter(self):
        """Alle etterkommere (dokumentrekkefølge), inkludert seg selv."""
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def finn_alle(self, tag):
        return [n for n in self.iter() if n.tag == tag]

    def tekst(self):
        deler = []
        for c in self.children:
            deler.append(c if isinstance(c, str) else c.tekst())
        return "".join(deler)

    def skjermlesertekst(self):
        """Tekst en skjermleser får: uten ``aria-hidden="true"``."""
        deler = []
        for c in self.children:
            if isinstance(c, str):
                deler.append(c)
            elif c.attrs.get("aria-hidden") != "true":
                deler.append(c.skjermlesertekst())
        return "".join(deler)


class _Bygger(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rot = Node("#dokument", {})
        self.aktiv = self.rot

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.aktiv)
        self.aktiv.children.append(node)
        if tag not in VOID:
            self.aktiv = node

    def handle_startendtag(self, tag, attrs):
        self.aktiv.children.append(Node(tag, attrs, self.aktiv))

    def handle_endtag(self, tag):
        n = self.aktiv
        while n is not self.rot and n.tag != tag:
            n = n.parent
        if n is not self.rot:
            self.aktiv = n.parent

    def handle_data(self, data):
        self.aktiv.children.append(data)


def parse_html(html: str) -> Node:
    b = _Bygger()
    b.feed(html)
    b.close()
    return b.rot


def anlopslista(dokument: Node) -> Node:
    """Seksjonen ``#anlopslista`` (lista med anløp). Tabelloppslag for lista avgrenses hit, så panelets tabeller
    (E2-S09) ikke blandes inn."""
    return [n for n in dokument.iter() if n.attrs.get("id") == "anlopslista"][0]


@pytest.fixture
def dokument(client):
    svar = client.get("/")
    assert svar.status_code == 200
    return parse_html(svar.get_data(as_text=True))


@pytest.fixture
def tomt_dokument(tomt_client):
    svar = tomt_client.get("/")
    assert svar.status_code == 200
    return parse_html(svar.get_data(as_text=True))


# ---------------------------------------------------------------------------
# Syntetisk ``metrikker.json`` for panelet (E2-S09). Tallene er oppdiktet. Visningen etter testkjøringen testes
# bare med slike filer i ``tmp_path``, aldri med ekte testtall (regelen om testrader).

def _syntetisk_arm(andel_30, treff_30, n, varsel):
    return {"andel_30": andel_30, "treff_30": treff_30, "n": n, "mae_min": 50.0, "median_min": 20.0,
            "varsel": varsel}


def _syntetisk_varsel(n, forsinket, varsler, treff):
    if varsler is None:  # kan ikke varsle
        return {"n": n, "forsinket": forsinket, "varsler": 0, "treff": 0,
                "presisjon": None, "recall": None, "f1": None}
    p = treff / varsler if varsler else 0.0
    r = treff / forsinket if forsinket else 0.0
    return {"n": n, "forsinket": forsinket, "varsler": varsler, "treff": treff, "presisjon": p, "recall": r,
            "f1": 2 * p * r / (p + r) if p + r else 0.0}


def syntetisk_blokk(modell_treff=300, baseline_treff=250, modell_varsler=40, modell_varseltreff=30, n=400,
                    forsinket=60, antall_anlop=1000):
    """Én split-blokk med samme form som ``scripts/evaluer.py`` skriver (uten ablasjon, som panelet ikke viser).

    Argumentene gjelder 6 t. 24 t får andre tall (+20 modelltreff, +10 baselinetreff, +10 forsinkede og +2
    varseltreff), så testene kan se at hver horisont viser sine egne tall."""
    def radsett(n_, forsinket_, m_treff, b_treff, v_treff):
        return {
            "modell": _syntetisk_arm(m_treff / n_, m_treff, n_,
                                     _syntetisk_varsel(n_, forsinket_, modell_varsler, v_treff)),
            "baseline": _syntetisk_arm(b_treff / n_, b_treff, n_,
                                       _syntetisk_varsel(n_, forsinket_, None, None)),
            "varsle_alle": _syntetisk_varsel(n_, forsinket_, n_, forsinket_),
        }

    def horisont(m_treff, b_treff, forsinket_, v_treff, passasjer_treff):
        return {
            "andel_modellutvalg": {"alle_rader": n / 700, "med_fasit": n / 600},
            "antall": {"ovrige": {"rader": 700, "med_fasit": 600, "med_tilstand": 550, "f6": 100,
                                  "f6_med_fasit": 90, "modellutvalg": 450, "modellutvalg_med_fasit": n,
                                  "med_tilstand_med_fasit": 500},
                       "passasjer": {"rader": 300, "med_fasit": 280}},
            "ovrige_modellutvalg": radsett(n, forsinket_, m_treff, b_treff, v_treff),
            "ovrige_alle": radsett(600, forsinket_ * 2, m_treff, b_treff, v_treff),
            "passasjer": {"baseline": _syntetisk_arm(passasjer_treff / 280, passasjer_treff, 280,
                                                     _syntetisk_varsel(280, 3, None, None))},
        }

    v24 = modell_varseltreff + 2 if modell_varsler >= modell_varseltreff + 2 else modell_varseltreff
    return {"split": "syntetisk", "antall_anlop": antall_anlop, "horisonter": {
        "6": horisont(modell_treff, baseline_treff, forsinket, modell_varseltreff, 210),
        "24": horisont(modell_treff + 20, baseline_treff + 10, forsinket + 10, v24, 200),
    }}
