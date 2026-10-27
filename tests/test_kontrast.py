"""Fargetokens og kontrast (E1-S06, UU1, UX §7).

Tokenene i ``:root`` i ``app/static/style.css`` skal være like verdiene i UX §7 (lyst
tema), og kontrasten regnes på nytt etter WCAG 2.x for parene stilarket faktisk bruker.
"""
import re
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
STIL = ROT / "app" / "static" / "style.css"
UX = ROT / "docs" / "ux" / "dashbord.md"

BAKGRUNNER = ("--bakgrunn", "--flate")


def _ux_tokens():
    """{token: (lys hex, kontrast mot bakgrunn, kontrast mot flate | None)} fra UX §7."""
    tekst = UX.read_text(encoding="utf-8")
    seksjon = tekst.split("## 7. Visuelt språk", 1)[1].split("\n## ", 1)[0]
    tokens = {}
    for linje in seksjon.splitlines():
        m = re.match(r"\|\s*`(--[a-z-]+)`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|\s*([^|]*)\|", linje)
        if not m:
            continue
        navn, hex_, kontrast = m.groups()
        tall = re.findall(r"\d+,\d+", kontrast)
        tokens[navn] = (hex_.upper(), [float(t.replace(",", ".")) for t in tall])
    return tokens


def _css():
    return STIL.read_text(encoding="utf-8")


def _css_uten_kommentarer():
    return re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)


def _root_tokens():
    css = _css_uten_kommentarer()
    blokk = re.search(r":root\s*\{([^}]*)\}", css).group(1)
    return {n: v.upper() for n, v in re.findall(r"(--[a-z-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", blokk)}


def _luminans(hex_):
    def kanal(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * kanal(r) + 0.7152 * kanal(g) + 0.0722 * kanal(b)


def kontrast(a, b):
    la, lb = sorted((_luminans(a), _luminans(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _bruk(egenskap_moenster):
    """Tokens brukt i deklarasjoner der egenskapen matcher mønsteret."""
    css = _css_uten_kommentarer()
    brukt = set()
    for egenskap, verdi in re.findall(r"([a-z-]+)\s*:\s*([^;{}]+);", css):
        if re.fullmatch(egenskap_moenster, egenskap):
            brukt |= set(re.findall(r"var\((--[a-z-]+)\)", verdi))
    return brukt


def test_ux_tabellen_kan_leses():
    ux = _ux_tokens()
    assert set(ux) >= {"--bakgrunn", "--flate", "--tekst", "--dempet", "--aksent", "--kant"}


def test_root_tokens_er_like_ux():
    ux = _ux_tokens()
    root = _root_tokens()
    assert root, "fant ingen tokens i :root"
    for navn, verdi in root.items():
        assert navn in ux, f"{navn} står ikke i UX §7"
        assert verdi == ux[navn][0], f"{navn} er {verdi} i CSS, men {ux[navn][0]} i UX §7"


def test_alle_brukte_tokens_er_definert():
    css = _css_uten_kommentarer()
    brukt = set(re.findall(r"var\((--[a-z-]+)\)", css))
    assert brukt <= set(_root_tokens())


def test_ingen_harde_farger_utenfor_root():
    css = _css_uten_kommentarer()
    utenfor = re.sub(r":root\s*\{[^}]*\}", "", css)
    assert not re.findall(r"#[0-9A-Fa-f]{3,8}\b", utenfor)


@pytest.mark.parametrize("bakgrunn", BAKGRUNNER)
def test_tekstfarger_har_minst_4_5(bakgrunn):
    root = _root_tokens()
    tekstfarger = _bruk(r"color") - set(BAKGRUNNER)
    assert "--tekst" in tekstfarger
    for t in tekstfarger:
        k = kontrast(root[t], root[bakgrunn])
        assert k >= 4.5, f"{t} mot {bakgrunn}: {k:.2f}:1"


@pytest.mark.parametrize("bakgrunn", BAKGRUNNER)
def test_kant_og_fokusring_har_minst_3(bakgrunn):
    root = _root_tokens()
    kanter = _bruk(r"border(-[a-z]+)?|outline(-color)?")
    assert {"--kant", "--aksent"} <= kanter
    for t in kanter:
        k = kontrast(root[t], root[bakgrunn])
        assert k >= 3.0, f"{t} mot {bakgrunn}: {k:.2f}:1"


def test_bakgrunner_er_bakgrunnstokens():
    assert _bruk(r"background(-color)?") <= set(BAKGRUNNER)


def test_utregnet_kontrast_stemmer_med_ux_tabellen():
    ux = _ux_tokens()
    for navn, (hex_, tall) in ux.items():
        if not tall:
            continue
        mot_bakgrunn = kontrast(hex_, ux["--bakgrunn"][0])
        mot_flate = kontrast(hex_, ux["--flate"][0])
        assert abs(mot_bakgrunn - tall[0]) < 0.06, f"{navn}: {mot_bakgrunn:.2f} ≠ {tall[0]}"
        assert abs(mot_flate - tall[1]) < 0.06, f"{navn}: {mot_flate:.2f} ≠ {tall[1]}"


def test_fokusring_er_3px_aksent():
    css = _css_uten_kommentarer()
    assert re.search(r":focus-visible\s*\{[^}]*outline:\s*3px solid var\(--aksent\)", css)
    assert not re.search(r"outline\s*:\s*(none|0)\s*;", css)
