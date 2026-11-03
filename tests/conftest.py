import datetime as dt
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import pytest

from app import create_app

# Et vindu i testperioden uten anløp (pause i dataene 01.02–06.02.2026).
TOMT_NAA = dt.datetime(2026, 2, 3, 8, 0, tzinfo=ZoneInfo("Europe/Oslo"))


@pytest.fixture
def app():
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


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
