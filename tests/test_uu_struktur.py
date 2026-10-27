"""UU-minimum for hovedskjermen, sjekket på HTML-strukturen (E1-S06, UU2/UU4/UU6/UU7).

Bare stdlib (``html.parser`` via ``conftest.parse_html``). Kontrast og tabulatorrekkefølge
slik den oppleves, må sjekkes manuelt (UX §6).
"""
import pytest

INTERAKTIVE = {"a", "button", "input", "select", "textarea", "summary"}
NATIVE = {"button", "input", "select", "textarea", "summary"}


@pytest.fixture(params=["standard", "tomt"])
def side(request, dokument, tomt_dokument):
    return dokument if request.param == "standard" else tomt_dokument


def test_lang_nb(side):
    html = side.finn_alle("html")
    assert len(html) == 1
    assert html[0].attrs.get("lang") == "nb"


def test_viewport_meta(side):
    metas = [m for m in side.finn_alle("meta") if m.attrs.get("name") == "viewport"]
    assert len(metas) == 1
    assert "width=device-width" in metas[0].attrs.get("content", "")


def test_en_h1_og_ingen_hoppede_nivaaer(side):
    nivaaer = [int(n.tag[1]) for n in side.iter()
               if len(n.tag) == 2 and n.tag[0] == "h" and n.tag[1] in "123456"]
    assert nivaaer.count(1) == 1
    assert nivaaer[0] == 1
    for forrige, neste in zip(nivaaer, nivaaer[1:]):
        assert neste <= forrige + 1, f"overskriftsnivå hopper fra h{forrige} til h{neste}"


def test_landemerker(side):
    assert len(side.finn_alle("header")) == 1
    mains = side.finn_alle("main")
    assert len(mains) == 1


def test_hopplenke_er_forst_og_virker(side):
    body = side.finn_alle("body")[0]
    interaktive = [n for n in body.iter() if n.tag in INTERAKTIVE]
    forste = interaktive[0]
    assert forste.tag == "a"
    href = forste.attrs.get("href", "")
    assert href.startswith("#") and len(href) > 1
    maal = [n for n in side.iter() if n.attrs.get("id") == href[1:]]
    assert len(maal) == 1
    assert href == "#anlopslista"
    assert maal[0].tag == "section"
    # Målet ligger i main, og hopp-lenka ligger før header.
    n = maal[0]
    while n is not None and n.tag != "main":
        n = n.parent
    assert n is not None, "hopp-lenkas mål skal ligge i main"
    elementer = [c for c in body.children if not isinstance(c, str)]
    assert elementer[0] is forste


def test_tabell_th_har_scope(dokument):
    tabeller = dokument.finn_alle("table")
    assert len(tabeller) == 1
    ths = tabeller[0].finn_alle("th")
    assert len(ths) == 6
    for th in ths:
        assert th.attrs.get("scope") in ("col", "row")


def test_tabellen_har_eksplisitte_roller(dokument):
    """display: block under 640 px fjerner tabellsemantikken i Safari, så rollene står i HTML."""
    assert dokument.finn_alle("table")[0].attrs.get("role") == "table"
    assert all(td.attrs.get("role") == "cell" for td in dokument.finn_alle("td"))
    assert all(th.attrs.get("role") == "columnheader" for th in dokument.finn_alle("th"))


def test_hver_td_har_data_label(dokument):
    tder = dokument.finn_alle("td")
    assert len(tder) == 15 * 6
    kolonner = [th.tekst().strip() for th in dokument.finn_alle("th")]
    for td in tder:
        assert td.attrs.get("data-label") in kolonner


def test_bilder_har_alt(side):
    for img in side.finn_alle("img"):
        assert "alt" in img.attrs


def test_svg_med_mening_har_tekstalternativ(side):
    for svg in side.finn_alle("svg"):
        if svg.attrs.get("aria-hidden") == "true":
            continue
        har_tittel = any(c.tag == "title" for c in svg.iter() if c is not svg)
        assert har_tittel or svg.attrs.get("aria-label") or svg.attrs.get("aria-labelledby")


def test_interaktive_elementer_kan_naas_med_tastatur(side):
    for n in side.iter():
        assert not any(k.startswith("on") for k in n.attrs), f"{n.tag} har JS-handler"
        if n.tag == "a":
            assert n.attrs.get("href"), "lenke uten href kan ikke nås med Tab"
        if n.tag in INTERAKTIVE:
            tabindex = n.attrs.get("tabindex")
            assert tabindex is None or tabindex == "0", f"{n.tag} har tabindex={tabindex}"
        elif "tabindex" in n.attrs and n.attrs["tabindex"] != "-1":
            pytest.fail(f"{n.tag} er gjort fokuserbar med tabindex; bruk et native element")
        # Ingen falske knapper: role=button/link bare på native elementer.
        if n.attrs.get("role") in ("button", "link"):
            assert n.tag in INTERAKTIVE


def test_ingen_javascript(side):
    assert side.finn_alle("script") == []


def test_dekorative_tegn_er_skjult(dokument):
    """Prediktor-merket ■ er pynt (UU4)."""
    merker = [n for n in dokument.iter() if n.tekst().strip() == "■" and n.tag == "span"]
    assert merker
    for m in merker:
        assert m.attrs.get("aria-hidden") == "true"
