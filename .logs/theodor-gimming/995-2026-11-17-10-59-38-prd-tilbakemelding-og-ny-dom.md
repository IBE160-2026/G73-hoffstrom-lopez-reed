# PRD-tilbakemelding og ny dom

## 2026-11-17 kl. 10:59 — Theodor Gimming

### Oppgave
Følge opp faglærers tilbakemelding på PRD-en (`docs/tilbakemelding-prd.md`, `2fbc096`, 12.11). Den lå på `main` dagen før testkjøringen, men ble lest etter den. Gruppa har bestemt å følge faglærer på suksesskriteriet: ±30 min er bestått bare når nedre grense i 95 % KI er over marginen på 3 pp, ellers «ikke påvist». Resten av tilbakemeldingen skal inn i PRD-en, og refleksjonsrapporten skal opprettes med utkast til svar på faglærers to spørsmål. Alt gjøres på `epic/e2-modell` (PR #5), som deretter gjøres klar for review.

### Plan
- Regne konfidensintervallene fra krysstabellen i `mcnemar.json` (bootstrap, seed 160, 10 000 trekk, og analytisk ved siden av), uten å lese testradene. Stoppe hvis tallene avviker vesentlig fra forventet.
- Ny dom først i resultatnotatet, den opprinnelige rett under. FR10 og begge briefene oppdateres, med en linje i endringsloggene.
- Dashbordet leser `konfidensintervall.json` og avgjør dommen med samme regel. Tester og mutasjonssjekk. README, status og UX rettes, og skjermbildene tas på nytt.
- PRD: FR11a og FR11b (mock-fallback, siden venter aldri, cache, høyst 20 kall), UJ-1 og UJ-2, testbare FR5–FR7 og FR14, ordliste, FR9 før FR9a, A1 inline.
- `docs/refleksjon/rapport.md` etter kursmalen, med utkast i 3.1.
- `technology.md` røres ikke.

### Resultat
- **Intervaller** (`data/modell/konfidensintervall.json`, `scripts/konfidensintervall.py`):
  - 6 t: +9,4 pp, bootstrap [6,0; 12,8], analytisk [5,9; 12,9]. **Bestått.**
  - 24 t: +0,8 pp, [−2,0; 3,6] med begge metodene. **Ikke påvist.**
  - Tallene stemte med det som var forventet.
  - Varsel-F1 trengte ikke testradene, fordi `metrikker.json` har hele forvekslingsmatrisen. Intervallene er +0,32 [0,19; 0,44] og +0,25 [0,12; 0,36]. Det er informasjon, uten margin.
- **Grensen:** første melding sa «over», og neste sa «minst». Theodor valgte **over** (> 3,0 pp) på spørsmål.
- **Commits:**
  - `7f69bd2` E2-S11: kriteriet, notatet, briefene, FR10, panelet, README, status, UX §2/§5, skjermbildene og tester.
    - Mutasjonssjekken med kontrollkjøring fanget 13 av 13 mutanter. Det skjedde etter én ny test for en skriptmutant som hadde overlevd, og den er ført i `notater.md`.
    - Skjermbildene viser ingen rulling ved 360, 640, 1280 eller 1920 px.
  - `b040653` E0-S19: resten av PRD-tilbakemeldingen.
    - FR11a ble endret etter beskjed: siden venter aldri på kallet og lastes på under 1 s. Hvordan, avgjøres i E3-arkitekturen.
    - Kravet om tidsavbrudd på 10 s er fjernet, og grensen på 20 kall er godkjent av gruppa.
  - `53524d3` E0-S20: `docs/refleksjon/rapport.md` med utkast, merket UTKAST, i 3.1.
- **Tester:** 487 grønne.
- **Lukket punkt:** E2-S07-punktet fra 27.10 er lukket. Tilstanden ved kuttet går gjennom grensen (`featurer_ved_kutt`, `79d3f17`).

### Åpne punkter
- Felipe og Thomas må lese `docs/resultater.md` og godkjenne den nye dommen før PR #5 merges.
- Refleksjonsrapporten: utkastene i 3.1 må skrives om med egne ord. Resten av malen, student-ID-ene og de individuelle refleksjonene i 7.4 står tomme.
- E3-arkitekturen må avgjøre hvordan siden unngår å vente på språkmodellkallet (FR11a).
- PRD 4.5 og kapittel 5 er ikke gjort: FR8 bør vise til `data/baseline.json` i stedet for å gjenta tallene, og filnavnene i FR8, NFR1 og NFR2 hører hjemme i arkitekturen.

## 2026-11-17 kl. 11:31 — Theodor Gimming

### Oppgave
Rette regelen slik at den er nøyaktig faglærers (tilbakemelding 4.1). Modellen lykkes på ±30 min hvis forskjellen (punktestimatet) er minst 3,0 pp. 95 % KI rapporteres, men er ikke en del av dommen. Theodor hadde skrevet at nedre grense i intervallet også skulle telle, og hadde brukt «over» og «minst» om hverandre. Grensetesten skal vise at nøyaktig 3,0 gir bestått, og notatet skal si at den strengere varianten gir samme dom.

### Plan
- Regelen i skriptet og panelet: punktestimatet ≥ marginen, sammenlignet på heltall (treff og n), så nøyaktig 3,0 pp alltid er bestått.
- Tester for grensen, også flyttallsfella (59/100 − 56/100), for at KI ikke avgjør dommen, og ny mutasjonssjekk.
- Rette notatet, FR10, begge briefene, README, status, UX og epics. Føre rettelsen inn i notater.md og i utkastet i rapporten.

### Resultat
- `94f032d` E2-S11: regelen er rettet overalt, og endringsloggene har en linje om rettelsen. Dommen er uendret: bestått ved 6 t (+9,4 pp) og ikke påvist ved 24 t (+0,8 pp). Notatet har setningen om at den strengere varianten gir samme dom (nedre grense 6,0 og −2,0).
- Panelet sjekker også at `andel_30` stemmer med `treff_30 / n`, siden dommen nå regnes på antall treff.
- Mutasjonssjekken med kontrollkjøring fanget 14 av 16. De to som overlever, er ekvivalente flyttallsvarianter (`antall/n` og den lagrede differansen avrundet til 6 desimaler). Varianten med rå andeler fanges av flyttallstesten.
- 492 tester grønne. Skjermbildene er tatt på nytt, uten rulling.
- `notater.md` har en ny oppføring: regelen ble formulert strengere enn faglærer skrev, og ble rettet etter at den var implementert.

### Åpne punkter
- Uendret fra seksjonen over: Felipe og Thomas må godkjenne den nye dommen før merge. Punktet står allerede i `issues.md`.
