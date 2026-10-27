"""Ta skjermbilder av hovedskjermen med headless Chrome (E1-S06).

Ikke en del av testene: ``pytest`` importerer aldri denne fila, og Chrome står ikke i
``requirements.txt``. Se ``docs/ux/skjermbilder/README.md``.

Bruk:
    .venv/bin/python scripts/ta_skjermbilder.py [--chrome STI]

Chrome finnes via ``--chrome``, miljøvariabelen ``CHROME`` eller standardstien på macOS.

Siden vises i en ``<iframe>`` med nøyaktig bredde på en innpakningsside fra samme
opprinnelse. Først måles ``scrollWidth``/``scrollHeight`` på 360, 640 (= 1280 px ved
200 % zoom), 1280 og 1920 px, og skriptet stopper med feil hvis siden er bredere enn
vinduet. Så tas bilder på 1280 og 360 px med høyden fra målingen. Headless Chrome lager
aldri et vindu smalere enn 500 px, så smale bilder beskjæres etterpå (ren stdlib-PNG).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import struct
import threading
import zlib
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from werkzeug.serving import make_server  # noqa: E402  (følger med Flask)

from app import create_app  # noqa: E402

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UT = ROT / "docs" / "ux" / "skjermbilder"

MAALE_BREDDER = (360, 640, 1280, 1920)  # 640 = 1280 px ved 200 % zoom
BILDER = [("hovedskjerm-desktop.png", 1280), ("hovedskjerm-mobil.png", 360)]
CHROME_MIN_BREDDE = 500


def finn_chrome(arg: str | None) -> str:
    kandidat = arg or os.environ.get("CHROME") or MAC_CHROME
    sti = shutil.which(kandidat) or (kandidat if Path(kandidat).is_file() else None)
    if not sti:
        sys.exit(
            f"Fant ikke Chrome på «{kandidat}».\n"
            "Oppgi stien med --chrome STI eller miljøvariabelen CHROME, for eksempel\n"
            "  CHROME=/usr/bin/google-chrome .venv/bin/python scripts/ta_skjermbilder.py"
        )
    return sti


def _kjor_chrome(chrome: str, args: list, timeout: int = 60) -> str:
    with tempfile.TemporaryDirectory() as profil:
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
             "--no-default-browser-check", f"--user-data-dir={profil}",
             "--force-device-scale-factor=1", *args],
            capture_output=True, text=True, timeout=timeout,
        )
    if r.returncode != 0:
        sys.exit(f"Chrome feilet (kode {r.returncode}):\n{r.stderr}")
    return r.stdout


def maal(chrome: str, base: str, bredde: int) -> tuple:
    """(scrollWidth, scrollHeight) for siden i en iframe på ``bredde`` px."""
    dom = _kjor_chrome(chrome, [
        f"--window-size={max(bredde, CHROME_MIN_BREDDE)},1000",
        "--virtual-time-budget=5000", "--dump-dom",
        f"{base}{RAMME}?bredde={bredde}&hoyde=100&maal=1",
    ])
    m = re.search(r'id="maaling">(\d+)x(\d+)<', dom)
    if not m:
        sys.exit(f"fant ingen måling for {bredde} px i DOM-en fra Chrome")
    return int(m.group(1)), int(m.group(2))


def ta_bilde(chrome: str, base: str, fil: Path, bredde: int, hoyde: int) -> None:
    if fil.exists():
        fil.unlink()  # et gammelt bilde skal ikke kunne bestå sjekken under
    vindu = max(bredde, CHROME_MIN_BREDDE)
    _kjor_chrome(chrome, [
        f"--window-size={vindu},{hoyde}", "--virtual-time-budget=5000",
        f"--screenshot={fil}", f"{base}{RAMME}?bredde={bredde}&hoyde={hoyde}",
    ])
    if not fil.is_file():
        sys.exit(f"Chrome skrev ikke {fil}")
    if vindu != bredde:
        _png_beskjaer(fil, bredde)


RAMME = "/_skjermbilde-ramme"
RAMME_HTML = """<!doctype html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#fff">
<iframe id="side" src="/" width="{bredde}" height="{hoyde}" style="border:0;display:block"></iframe>
<p id="maaling"></p>
{skript}
</body></html>"""
MAALE_SKRIPT = """<script>
document.getElementById("side").addEventListener("load", function () {
  var d = this.contentDocument.documentElement;
  document.getElementById("maaling").textContent = d.scrollWidth + "x" + d.scrollHeight;
});
</script>"""


def med_ramme(app):
    """WSGI-innpakning: serverer rammesiden fra samme opprinnelse som appen."""
    from urllib.parse import parse_qs

    def wsgi(environ, start_response):
        if environ.get("PATH_INFO") != RAMME:
            return app(environ, start_response)
        q = parse_qs(environ.get("QUERY_STRING", ""))
        html = RAMME_HTML.format(
            bredde=int(q["bredde"][0]), hoyde=int(q["hoyde"][0]),
            skript=MAALE_SKRIPT if "maal" in q else "",
        ).encode("utf-8")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [html]

    return wsgi


def _png_les(fil: Path):
    """Les en 8-bits, ikke-interlacet RGB/RGBA-PNG til (bredde, høyde, kanaler, rader)."""
    data = fil.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "ikke en PNG"
    pos, idat = 8, b""
    while pos < len(data):
        lengde, typ = struct.unpack(">I4s", data[pos:pos + 8])
        innhold = data[pos + 8:pos + 8 + lengde]
        if typ == b"IHDR":
            bredde, hoyde, dybde, farge, _, _, interlace = struct.unpack(">IIBBBBB", innhold)
            if dybde != 8 or farge not in (2, 6) or interlace:
                sys.exit(f"uventet PNG-format i {fil} (dybde {dybde}, farge {farge})")
        elif typ == b"IDAT":
            idat += innhold
        pos += 12 + lengde
    kanaler = 3 if farge == 2 else 4
    raa = zlib.decompress(idat)
    stride = bredde * kanaler
    rader, forrige = [], bytearray(stride)
    for y in range(hoyde):
        start = y * (stride + 1)
        filter_, rad = raa[start], bytearray(raa[start + 1:start + 1 + stride])
        for i in range(stride):
            a = rad[i - kanaler] if i >= kanaler else 0
            b = forrige[i]
            if filter_ == 1:
                rad[i] = (rad[i] + a) & 0xFF
            elif filter_ == 2:
                rad[i] = (rad[i] + b) & 0xFF
            elif filter_ == 3:
                rad[i] = (rad[i] + ((a + b) >> 1)) & 0xFF
            elif filter_ == 4:
                c = forrige[i - kanaler] if i >= kanaler else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                rad[i] = (rad[i] + pred) & 0xFF
        rader.append(rad)
        forrige = rad
    return bredde, hoyde, kanaler, farge, rader


def _png_beskjaer(fil: Path, ny_bredde: int) -> None:
    """Behold de ``ny_bredde`` pikslene lengst til venstre."""
    bredde, hoyde, kanaler, farge, rader = _png_les(fil)
    raa = b"".join(b"\x00" + bytes(r[:ny_bredde * kanaler]) for r in rader)

    def chunk(typ: bytes, innhold: bytes) -> bytes:
        return (struct.pack(">I", len(innhold)) + typ + innhold
                + struct.pack(">I", zlib.crc32(typ + innhold) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", ny_bredde, hoyde, 8, farge, 0, 0, 0)
    fil.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                    + chunk(b"IDAT", zlib.compress(raa, 9)) + chunk(b"IEND", b""))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--chrome", help="sti til Chrome/Chromium")
    args = p.parse_args()
    chrome = finn_chrome(args.chrome)

    server = make_server("127.0.0.1", 0, med_ramme(create_app()))  # port 0 = ledig port
    traad = threading.Thread(target=server.serve_forever, daemon=True)
    traad.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        hoyder = {}
        for bredde in MAALE_BREDDER:
            sw, sh = maal(chrome, base, bredde)
            print(f"{bredde:>5} px: scrollWidth {sw}, scrollHeight {sh}")
            if sw > bredde:
                sys.exit(f"Horisontal rulling på {bredde} px: siden er {sw} px bred.")
            hoyder[bredde] = sh
        UT.mkdir(parents=True, exist_ok=True)
        for navn, bredde in BILDER:
            fil = UT / navn
            ta_bilde(chrome, base, fil, bredde, hoyder[bredde])
            print(f"skrev {fil.relative_to(ROT)} ({bredde} × {hoyder[bredde]})")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
