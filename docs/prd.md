---
title: "PRD: AIS-basert ankomstprediksjon"
status: aktiv
created: 2026-10-16
updated: 2026-10-16
bygger_på: docs/brief.md
---

# PRD — AIS-basert ankomstprediksjon

**Bygger på:** [`docs/brief.md`](brief.md) (problem, bruker, suksesskriterier). **Brukes av:** [`docs/arkitektur.md`](arkitektur.md), [`docs/ux/dashbord.md`](ux/dashbord.md), [`docs/epics.md`](epics.md).

Dette er et levende dokument. Når et krav endres under bygging, endres det her først, deretter i stories. Hver endring får en linje i endringsloggen nederst.

## 1. Mål

Havnevakta skal kunne se hvilke anløp de neste 24 timene det er grunn til å mistro, og hvorfor. v1 er en *avspilling* av det låste historiske datasettet, ikke et live-verktøy (se brief, Scope).

**Leveranser, i prioritert rekkefølge:**

| # | Leveranse | Fase | Epic | Hvis den glipper |
|---|---|---|---|---|
| 1 | **Dashbord v1 på kalibrert baseline**: det sensor kjører | 3 (24. okt–6. nov) | E1 | Prosjektet har ikke noe kjørbart. Kan ikke glippe. |
| 2 | Modell byttet inn bak samme dashbord | 4 (7.–27. nov) | E2 | Dashbord v1 står fortsatt, og negativt resultat rapporteres ærlig |
| 3 | Generativt AI-lag med testmodus | 5 (28. nov–5. des) | E3 | Dashbord med modell står fortsatt |

Hver leveranse skal kunne leveres alene. Det er et designkrav, ikke bare et håp: dashbordet kjenner bare et prediktor-grensesnitt (se arkitektur, §3), ikke selve modellen.

## 2. Bruker og bruksituasjon

**Havnevakta** (primær, se brief) ved vaktstart: *"Hvilke anløp de neste 24 timene kan jeg ikke stole på?"* Hen sitter ved en arbeidsstasjon (desktop først) og må kunne bruke verktøyet med tastatur alene.

**Sensor** (sekundær, men avgjørende for v1): kloner repoet, starter appen, spiller av en dag og ser at tallene stemmer med briefen. Alt i §5 (kjørbarhet) er skrevet for sensor.

## 3. Funksjonelle krav

ID-ene brukes i stories (`docs/epics.md`) og i tester. **Fase 3** = må være ferdig i dashbord v1.

### Dashbord v1: kalibrert baseline (E1)

- **FR1 — Simulert «nå».** Brukeren velger dato og klokkeslett (norsk tid) som «nå». Valget er begrenset til testperioden (14.09.2025–15.03.2026), fordi prediksjoner på treningsdata er misvisende. Standard er 08.10.2025 kl. 08:00. Ugyldig eller utenforliggende tid gir en feilmelding knyttet til feltet, ikke en krasj.
- **FR2 — Anløpsliste.** Viser alle anløp med rapportert ETA i vinduet [«nå», «nå» + 24 t], kronologisk etter predikert ankomst. Per rad: skipsnavn, skipsgruppe, rutegående/ikke-rutegående, rapportert ETA, predikert ankomst, horisont (≤ 6 t / 6–24 t) og varsel.
- **FR3 — Kilde alltid synlig.** Skjermen viser alltid hvilken prediktor som står bak tallene («Kalibrert baseline» eller «Modell vX»). Baselinen varsler aldri forsinkelse; varselkolonnen viser da «–» med en forklaring, ikke et tomt felt.
- **FR4 — Fasit.** En bryter («Vis faktisk ankomst») legger til faktisk ankomst (`arrival_in_area`), avvik i minutter og et forsinket-merke (> 2 t, se beslutning 06). Bryteren er av som standard, slik vakta ville sett det. Anløp uten AIS-data viser «Fasit mangler», ikke blankt.
- **FR5 — Filter.** Vis alle, kun ikke-rutegående eller kun rutegående. Standard: alle.
- **FR6 — Sortering.** Bytt mellom predikert ankomst (standard) og størst avvik. Størst avvik er bare tilgjengelig når fasit vises.
- **FR7 — Detaljvisning.** Hvert anløp har en egen side: skipsdata, alle tidspunkt, og en forklaring av hvordan prediksjonen ble laget (v1: «rapportert ETA − 64 min, median liggetid for ikke-rutegående i treningsdata»).
- **FR8 — Treffsikkerhet.** Et panel viser andel innenfor ±30 min for hele testperioden: ikke-rutegående som hovedtall, rutegående som kontroll, naiv ETA til sammenligning. For baseline skal tallene være 46,6 % / 79,6 % / 12,9 % (brief, beslutning 04).

### Modell (E2)

- **FR9 — Modellprediksjon.** Modellen leverer predikert ankomst og et forsinket-varsel per anløp gjennom samme grensesnitt som baselinen. Dashbordet bytter kilde uten endringer i visningskoden.
- **FR10 — Modell mot baseline.** Treffsikkerhetspanelet viser modell og kalibrert baseline side om side, pluss presisjon/recall på forsinket-varselet. Taper modellen på ett eller begge mål, vises det like tydelig.

### Generativt AI-lag (E3)

- **FR11 — Begrunnelse per anløp.** Detaljsiden viser en kort tekst om hvorfor avviket er ventet, generert *kun* fra modellens faktiske input og output. Teksten er merket «KI-generert».
- **FR12 — Forstyrrelsesbrief.** Øverst på hovedskjermen står 3–5 setninger om vinduet: hvilke anløp vakta bør følge med på, og hvorfor.
- **FR13 — Testmodus.** Uten API-nøkkel kjører AI-laget i testmodus. Det er standard. Testmodus viser lagrede ekte svar for demodagene og ellers en deterministisk mal, tydelig merket.
- **FR14 — Kart (valgfritt).** Kart over anløpene i vinduet. Lavest prioritet i hele prosjektet og kan droppes.

## 4. Universell utforming (krav fra start)

Mål: WCAG 2.1 nivå AA for de kravene som gjelder appen. Hvert punkt har en test eller en manuell sjekk i [`docs/ux/dashbord.md` §6](ux/dashbord.md#6-sjekkliste-for-universell-utforming).

- **UU1 — Kontrast.** Tekst ≥ 4,5:1, store tekster og UI-grenser ≥ 3:1, i både lyst og mørkt tema. Testes automatisk mot fargetokenene.
- **UU2 — Tastatur.** Alt kan nås og brukes med Tab, Shift+Tab, Enter og Space i logisk rekkefølge. Synlig fokusmarkering. «Hopp til innhold»-lenke først på siden.
- **UU3 — Ikke bare farge.** Varsel og forsinket-merke har både ikon og tekst. Fargen forsterker, men bærer ikke informasjonen alene.
- **UU4 — Alt-tekst.** Alle ikoner som bærer mening har tekstalternativ. Rene pynteikoner har `alt=""` eller `aria-hidden`. Kart (FR14) får en tekstlig ekvivalent: lista selv.
- **UU5 — Skjemaetiketter.** Hvert felt har en synlig `<label>`. Feilmeldinger er koblet til feltet (`aria-describedby`) og sier hva som er feil og hva som er gyldig.
- **UU6 — Skjermstørrelser.** Brukbar fra 360 px til 1920 px bredde uten horisontal rulling, og ved 200 % zoom. Under 640 px vises anløp som kort i stedet for tabell.
- **UU7 — Semantikk.** `lang="nb"`, én `h1`, ekte `<table>` med `<th scope>`, `aria-sort` på sorterbar kolonne, landemerker (`header`, `main`, `nav`).

## 5. Ikke-funksjonelle krav

- **NFR1 — Kjørbarhet (kriterium 6).** Sensor skal kunne klone repoet og ha appen kjørende på **under 20 minutter** ved å følge README, uten gruppas nøkler eller kontoer og uten nett utover `pip install`. Dette forutsetter:
  - **Versjonert datautdrag** i `data/utdrag/`, ikke den gitignorede `pipeline/data/`.
  - **Lagret baseline** (`data/baseline.json`: offset per gruppe, splittidspunkt, kildefilens sjekksum), slik at ingenting må regnes ut på nytt ved oppstart.
  - **`.env.example`** med alle variabler og *ingen* ekte nøkler. Appen starter uten `.env`.
  - Fra E2: **lagret modellartefakt**, så sensor ikke må trene.
  - Fra E3: **testmodus som standard** (FR13).
  - Verifisert med en *klone-test*: et gruppemedlem som ikke bygde oppsettet følger README på en ren maskin. Tiden loggføres.
- **NFR2 — Testbarhet (kriterium 3).** Hver story har akseptansekriterier som kan sjekkes og en navngitt test, automatisk der det går og ellers et manuelt sjekkpunkt. `pytest` kjører uten nett og uten `pipeline/data/` på under ett minutt.
- **NFR3 — Ærlige tall.** Dashbord og evalueringsskript bruker *samme* metrikkfunksjon. Alle tall regnes på testsplitten. Baseline-tallene i FR8 er en regresjonstest: endrer de seg, er noe galt.
- **NFR4 — Sporbarhet (kriterium 1).** Én story = én commit, med story-ID først i commit-meldingen (`E1-S03: …`). Én branch og én PR per epic. PR-beskrivelsen lister storyene.
- **NFR5 — Enkelhet (kriterium 5).** Ingen database, ingen JS-rammeverk, ingen byggesteg. Begrunnet i arkitekturen.
- **NFR6 — Hemmeligheter (kriterium 7).** Nøkler bare i `.env`, som er gitignored. Ingen nøkkel trengs for å kjøre eller teste.

## 6. Utenfor v1

Som i briefens Scope/OUT: live-data, flere havner, API for andre, innlogging og roller. I tillegg: redigering av data, eksport, varsler (e-post/push) og historikk over valgte «nå»-tidspunkt.

## 7. Åpne spørsmål

| Spørsmål | Avgjøres i | Eier |
|---|---|---|
| Hvilke features finnes faktisk *på prediksjonstidspunktet*? Hva skiller 6 t fra 24 t når datasettet bare har én rapportert ETA per seilas? | E2-S01 (blir beslutning 08) | Felipe |
| Én modell, eller separate for rutegående/ikke-rutegående? | E2-S01 | Felipe |
| Hvilken språkmodell-leverandør skal brukes i ekte modus? Arkitekturen antar Anthropic, men adapteren gjør byttet billig. | E3-S03 | Thomas |

## Endringslogg

- **2026-10-16** — Første versjon (E0-S01). Designvalg fra UX-runden: simulert «nå» + 24 t-vindu, desktop først, kronologisk liste med avvik markert, Python/Flask.
