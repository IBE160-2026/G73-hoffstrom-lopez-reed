# Skjermbilder av dashbordet

Skjermbilder av den kjørende appen, ved siden av skissene i [`../dashbord.md`](../dashbord.md).

| Fil | Viser | Bredde |
|---|---|---|
| `hovedskjerm-desktop.png` | Skjerm A, standardvinduet (ons 08.10.2025 08:00) | 1280 px |
| `hovedskjerm-mobil.png` | Skjerm B, samme vindu som kort | 360 px |

## Slik lages de

```bash
.venv/bin/python scripts/ta_skjermbilder.py
```

Skriptet starter appen på en ledig lokal port og åpner `/` i headless Chrome, inne i en `<iframe>` med nøyaktig bredde på en innpakningsside fra samme opprinnelse. Først måler det `scrollWidth` og `scrollHeight` på 360, 640, 1280 og 1920 px. Er siden bredere enn vinduet på noen av dem, stopper skriptet med feilkode og sier hvor bred den er. Deretter tar det bilder på 1280 og 360 px, med høyden fra målingen, og skriver de to PNG-filene hit. Kjør det når alle tester er grønne, se over bildene og commit dem.

**Hvorfor 640 px.** 200 % zoom i et vindu på 1280 px gir 640 CSS-piksler å legge ut siden på. Målingen på 640 px er derfor den samme sjekken som 200 % zoom på desktop (UU6).

**Krever Google Chrome eller Chromium.** Chrome står ikke i `requirements.txt` og trengs ikke for noe annet. Skriptet bruker standardstien på macOS (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`). Andre steder oppgis stien slik:

```bash
.venv/bin/python scripts/ta_skjermbilder.py --chrome /usr/bin/google-chrome
# eller
CHROME=/usr/bin/chromium .venv/bin/python scripts/ta_skjermbilder.py
```

Finner skriptet ikke Chrome, stopper det med en melding om hvordan stien oppgis.

**Ikke en del av testene.** `pytest` importerer aldri skriptet og trenger verken Chrome eller nett. Sensor kjører testene på en ren maskin.

**Mobilbildet.** Headless Chrome lager ikke vinduer smalere enn 500 px. Mobilbildet tas derfor med iframen på 360 px i et vindu på 500 px, og bildet beskjæres til 360 px etterpå med ren stdlib. Bildet viser altså ikke selv om siden ruller horisontalt. Det er målingen over som sjekker det.
