# E1-S16 README og forhåndssjekk

## 2026-10-27 kl. 17:35 (oppdatert 17:39) — Theodor Gimming

### Oppgave
Skrive «Kom i gang» i README og deretter gjøre en tørrkjøring: klone repoet til en ny, tom mappe utenfor prosjektet, lage et nytt virtuelt miljø og følge README ordrett fra første til siste kommando, uten noe fra den eksisterende mappa. Alt som feiler eller er uklart, skal rettes og logges. Dette er en forhåndssjekk, ikke klone-testen. Den ekte gjøres av Felipe eller Thomas på egen maskin 28.10 og logges under deres navn.

Oppfølging samme dag:
- Bytt standardporten til 8000. AirPlay svarer 403 på port 5000 på macOS, og målet er å fjerne fella, ikke forklare den.
- Kjør tørrkjøringen på nytt fra en tom mappe.
- Åpne PR for E1 til main uten å merge. PR-beskrivelsen skal si at kontraktendringen må godkjennes av begge eierne, og at klone-testen kjøres mot main etter merge.

### Plan
- README del 1 committes og pushes (`384d5be`), slik at tørrkjøringen kloner fra GitHub og ikke fra mappa lokalt.
- Tørrkjøring i scratchpaden. Rent skall (`env -i`, bare systemets `PATH`), systemets Python 3.9.6, og kommandoene i README én for én.
- Rette funnene, pushe og kjøre på nytt fra en ny, tom mappe uten pip-cache.

### Resultat
**Forhåndssjekk 1 (17:31, maskinen her: macOS, Python 3.9.6):**

| # | Steg | Funn | Tiltak |
|---|---|---|---|
| 1 | `git clone …` | **Blokkerer.** Klonen gir `main`, der verken `app/`, `requirements.txt` eller «Kom i gang» finnes. Hele E1 ligger bare på `epic/e1-dashbord-v1`. | Ikke rettet. Krever at E1 merges til main (delvis PR, som arbeidsreglene åpner for). Tørrkjøringen fortsatte med `-b epic/e1-dashbord-v1` som eneste avvik fra README. |
| 2 | `pip install` | Advarsel om gammel pip (21.2.4). Ufarlig, men kan se ut som en feil. | README sier at advarselen er ufarlig. |
| 3 | `pytest` | 179 grønne. | — |
| 4 | `pytest tests/test_dataregresjon.py -v` | Testnavnene viste «Øvrige» som `\xd8vrige`, så tallene var vanskelige å lese. | Lesbare id-er (`baseline-ovrige-464-996-46,6-6t`). |
| 5 | `flask --app app run` | Appen svarer på 127.0.0.1:5000. **`localhost:5000` gir 403 fra AirPlay** (`Server: AirTunes`), fordi `localhost` blir `::1`. Rådet i README («port opptatt») var feil. | README forklarer det som faktisk skjer. Logget i refleksjonsnotatene. |
| 6 | Hva du skal se | Overskrift «15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)», 15 rader, «Kalibrert baseline» og forklaringen. Stemmer med README. | — |

Tid: 24 s (med pip-cache, så ikke representativt).

**Forhåndssjekk 2 (etter rettelsene, `4af9dc7`):** ny tom mappe, `--no-cache-dir`. 179 grønne, 10/10 i dataregresjonen og 200 på 127.0.0.1. Tid: 14 s. Fortsatt på E1-branchen, se funn 1.

**Port 8000 (`cf697a8`):**
- README starter med `flask --app app run --port 8000`.
- Sjekket på forhånd: `127.0.0.1:8000` og `localhost:8000` svarer begge 200.
- Når porten er opptatt, sier Flask «Address already in use». README gjengir nå den meldingen, i stedet for AirPlay-advarselen.

**Forhåndssjekk 3 (etter portbyttet):**
- Ny tom mappe, uten pip-cache. Startkommandoen ble lest rett fra README.
- 179 grønne, og 10/10 i dataregresjonen.
- `127.0.0.1:8000` og `localhost:8000` svarer begge 200, med overskriften «15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)».
- 14 s fra tom mappe til side.

**PR #4** (https://github.com/IBE160-2026/G73-hoffstrom-lopez-reed/pull/4) er åpnet fra `epic/e1-dashbord-v1` til main og ikke merget. Beskrivelsen sier at kontraktendringen i arkitektur §3 må godkjennes av begge eierne (Thomas og Felipe), og at klone-testen kjøres mot main etter merge, ikke mot branchen.

**Commits:** `384d5be` (README del 1), `4af9dc7` (rettelser) og `cf697a8` (port 8000), alle pushet. E1-S16 står som ◐.

### Åpne punkter
- PR #4 må godkjennes, med kontraktendringen av både Thomas og Felipe, og merges før klone-testen. Ellers finner den som følger README ingen app på main.
- Klone-testen (E1-S16) kjøres av Felipe eller Thomas på egen maskin 28.10, logges i `.logs/<deres navn>/`, og tiden føres i README.
- UU-sjekklista i UX §6 fylles ut i E1-S16, med manuell tastatur- og VoiceOver-sjekk.
