---
title: "PRD: AIS-basert ankomstprediksjon"
status: aktiv
created: 2026-10-16
updated: 2026-10-16
bygger_på: docs/brief.md
validert: _bmad-output/planning-artifacts/prds/prd-G73-hoffstrom-lopez-reed-2026-10-16/validation-report.md
---

# PRD — AIS-basert ankomstprediksjon

**Bygger på:** [`docs/brief.md`](brief.md) (problem, bruker, suksesskriterier) og beslutningene i [`docs/beslutninger/`](beslutninger/). **Brukes av:** [`docs/arkitektur.md`](arkitektur.md), [`docs/ux/dashbord.md`](ux/dashbord.md) og [`docs/epics.md`](epics.md). **Validert** med BMAD `bmad-prd` (validate) 16.10.2026. Rapporten ligger i `_bmad-output/planning-artifacts/prds/prd-G73-hoffstrom-lopez-reed-2026-10-16/`.

Dette er et levende dokument. Når et krav endres under bygging, endres det her først, deretter i stories. Hver endring får en linje i endringsloggen nederst. Antakelser som ikke er bekreftet, er merket `[ASSUMPTION]` og samlet i §9.

## 1. Mål

Havnevakta skal kunne se hvilke anløp de neste 24 timene det er grunn til å mistro, og hvorfor. v1 er en *avspilling* av det låste historiske datasettet, ikke et live-verktøy (se brief, Scope). Utdraget har 7 826 anløp. Det er de 8 094 seilasene som ble hentet, minus de som falt bort i utledningen (se `docs/addendum.md`).

**Leveranser, i prioritert rekkefølge:**

| # | Leveranse | Fase | Epic | Hvis den glipper |
|---|---|---|---|---|
| 1 | **Dashbord v1 på kalibrert baseline**: det sensor kjører | 3 (24. okt–6. nov) | E1 | Prosjektet har ikke noe kjørbart. Kan ikke glippe. |
| 2 | Modell byttet inn bak samme dashbord | 4 (7.–27. nov) | E2 | Dashbord v1 står fortsatt, og negativt resultat rapporteres ærlig |
| 3 | Generativt AI-lag med testmodus | 5 (28. nov–5. des) | E3 | Dashbord med modell står fortsatt |

Hver leveranse skal kunne leveres alene. Det er et designkrav, ikke bare et håp: dashbordet kjenner bare et prediktor-grensesnitt (se arkitektur, §3), ikke selve modellen.

**Hva v1 alene gir, og hva det ikke gir:** v1 viser en kalibrert forventet ankomst per anløp, og lar vakta og sensor spille av fasiten og se hvor ofte den treffer. v1 kan *ikke* si hvilke anløp vakta bør mistro. Baselinen er en fast forskyvning per gruppe og varsler aldri (FR3). Mistro-signalet kommer først med modellen i E2. Klarer ikke modellen å slå baselinen, er det svaret prosjektet gir, og det skal stå like tydelig.

## 2. Bruker og bruksituasjon

**Havnevakta** (primær, se brief) ved vaktstart: *«Hvilke anløp de neste 24 timene kan jeg ikke stole på?»* Hen sitter ved en arbeidsstasjon (desktop først) og må kunne bruke verktøyet med tastatur alene.

**Sensor** (sekundær, men avgjørende for v1): kloner repoet, starter appen, spiller av en dag og ser at tallene stemmer med briefen. Alt i §5 (kjørbarhet) er skrevet for sensor.

## 3. Ordliste

Hvert begrep har ett navn. Navnene brukes likt i PRD, UX, arkitektur, stories og UI.

| Begrep | Betydning |
|---|---|
| **Anløp** | Én seilas til Bergen Havn, altså én rad i datautdraget (`voyageid`) |
| **Rapportert ETA** | `eta_reported`: ankomsttiden skipet selv har meldt. Én verdi per anløp. |
| **Faktisk ankomst** | `arrival_in_area`: første AIS-posisjon innenfor ankomstsonen, ~15 km fra kai (beslutning 03). Ikke ankomst ved kai. |
| **Passasjer / Øvrige** | Skipsgruppe. *Passasjer* er `ship_group = Passasjer` og brukes som proxy for rutegående trafikk, selv om gruppen også har cruiseskip. *Øvrige* er alle andre grupper (Last, Tank, Slep, Auxiliary, Fisk). Hovedtallet gjelder Øvrige. |
| **Kalibrert baseline** | `rapportert ETA − offset[gruppe]`, der offset er median tid fra ankomstsonen til kai i treningsdata: 44,8 min for Passasjer og 64,2 min for Øvrige (beslutning 04) |
| **Avvik** | `faktisk ankomst − kalibrert baseline`, i minutter. Positivt betyr senere enn forventet. Regnes *alltid* mot kalibrert baseline, uansett hvilken prediktor som vises. |
| **Forsinket** | Fasitetiketten `avvik > 120 min` (signert, beslutning 06). Den er uavhengig av prediktoren. |
| **Prediksjonsfeil** | `faktisk ankomst − predikert ankomst` for den aktive prediktoren |
| **Varsel** | Prediktorens påstand om at et anløp blir forsinket (`forventet_forsinket`). Baselinen gir aldri varsel. |
| **Horisont (H)** | 6 t eller 24 t. Hvor lang tid før rapportert ETA prediksjonen lages. |
| **Kuttpunkt (`t_H`)** | `rapportert ETA − H`: det siste tidspunktet en prediksjon med horisont H kan bruke data fra (FR9a) |
| **«Nå»** | Det simulerte tidspunktet brukeren spiller av fra (FR1) |
| **Testperioden** | De siste 20 % av anløpene etter rapportert ETA: 1 566 anløp, 14.09.2025–15.03.2026 |

## 4. Funksjonelle krav

ID-ene brukes i stories (`docs/epics.md`) og i tester.

### Dashbord v1: kalibrert baseline (E1)

- **FR1 — Simulert «nå».** Brukeren velger dato og klokkeslett (norsk tid) som «nå». Valget er begrenset til testperioden, fordi prediksjoner på treningsdata er misvisende. Standard er 08.10.2025 kl. 08:00. Ugyldig eller utenforliggende tid gir en feilmelding knyttet til feltet, ikke en krasj.
- **FR2 — Anløpsliste.** Viser alle anløp med rapportert ETA i det halvåpne vinduet [«nå», «nå» + 24 t), kronologisk etter predikert ankomst.
  - Per rad: skipsnavn, skipsgruppe, rapportert ETA, predikert ankomst, horisont og varsel.
  - **Horisonten regnes fra rapportert ETA, ikke fra predikert ankomst:** ≤ 6 t hvis `rapportert ETA − nå ≤ 6 t`, ellers 6–24 t. Dermed er kuttpunktet `t_H ≤ nå` for hver rad (FR9a), og avspillingen bruker aldri data fra etter «nå».
  - Predikert ankomst kan ligge før «nå». Raden vises da som vanlig, med hjelpeteksten «predikert før valgt tidspunkt».
- **FR3 — Kilde alltid synlig.** Skjermen viser alltid hvilken prediktor som står bak tallene («Kalibrert baseline» eller «Modell vX»). Baselinen varsler aldri forsinkelse. Varselkolonnen viser da «–» med en forklaring, ikke et tomt felt.
- **FR4 — Fasit.** En bryter («Vis faktisk ankomst») legger til faktisk ankomst, avvik og FORSINKET-merket (ordliste). Med en modell aktiv kommer også prediksjonsfeil. Bryteren er av som standard, slik vakta ville sett det.
  - Avvik og FORSINKET endrer seg ikke når prediktoren byttes. Det testes.
  - Anløp uten fasit viser årsaken, ikke blankt:
    - `empty` → «Fasit mangler (ingen AIS-data hentet)»
    - `not_detected` → «Fasit mangler (ankomst ikke funnet i AIS-sporet)»
    - `avkortet_av_neste_seilas` → «Fasit mangler (avkortet av neste seilas, trolig stort avvik)» (beslutning 02)
- **FR5 — Filter.** Vis alle, kun Øvrige eller kun Passasjer. Standard: alle.
- **FR6 — Sortering.** Bytt mellom predikert ankomst (standard) og avvik, synkende, så de mest forsinkede kommer først. Avvik er bare tilgjengelig når fasit vises.
- **FR7 — Detaljvisning.** Hvert anløp har en egen side: skipsdata, alle tidspunkt, og en forklaring av hvordan prediksjonen ble laget. For baselinen er forklaringen en mal per gruppe: «rapportert ETA − {offset} min (median tid fra ankomstsonen til kai for {gruppe} i treningsdata)».
- **FR8 — Treffsikkerhet og datakvalitet.** Et panel og en metodeside (`/metode`) viser tall for hele testperioden, regnet med samme metrikkfunksjon som evalueringen (NFR3):
  - **Andel innenfor ±30 min** (hovedmetrikken), med både naiv ETA og kalibrert baseline per gruppe. For baseline skal tallene være **Øvrige 46,6 %** (naiv 12,9 %) og **Passasjer 79,6 %** (naiv 7,4 %) (`docs/beslutninger/04-kalibrert-baseline.md`).
  - **Dekning:** antall anløp med fasit av totalt per gruppe og antall per status (`ok`, `empty`, `not_detected`, `avkortet_av_neste_seilas`). Testperioden: 1 427 av 1 566 (91,1 %).
  - **Støttetall** (bare på `/metode`, aldri som hovedtall): MAE og median absolutt avvik.
  - `/metode` har setningen som beslutning 04 krever: forskjellen mellom naiv og kalibrert baseline skyldes at de måler to ulike fysiske hendelser, ikke at kalibrert er en bedre modell.

### Modell (E2)

- **FR9a — Informasjonskutt (lekkasjekrav).** For horisont H ∈ {6 t, 24 t} er kuttpunktet **`t_H = rapportert ETA − H`** (`docs/beslutninger/08-horisont-kuttes-pa-rapportert-eta.md`).
  - **Kuttet forankres i rapportert ETA og aldri i faktisk ankomst.** Et kutt ved faktisk ankomst ville latt fasiten bestemme hvilke data modellen ser.
  - Modellens input er fartøyets tilstand ved `t_H`, regnet fra siste AIS-posisjon ved eller før `t_H`: posisjon, gjenstående distanse til ankomstsonen, fart, kurs og alder på posisjonen. I tillegg kommer historiske features fra anløp med faktisk ankomst før `t_H`, og bare fra treningsdata.
  - **Test:** prediksjonen er uendret når alle AIS-punkter etter `t_H` fjernes eller flyttes, og når faktisk ankomst endres.
  - Tilstanden hentes fra siste posisjon i [`t_H` − 24 t, `t_H`] (beslutning 09). Kystdatahuset forskyver vinduet og kan kutte svar ved midnatt, så posisjonene filtreres på tidsstemplet i svaret, aldri på vinduet det ble bedt om. Filtreringen testes.
  - Anløp uten AIS-posisjon i [`t_H` − 24 t, `t_H`] får baselinens prediksjon og merket «ingen AIS-tilstand ved prediksjonstidspunktet». De tas ikke ut av evalueringen.
  - Anløp der skipet allerede har ankommet før `t_H` beholdes, siden vakta ville sett det. De telles og rapporteres separat (1,6 % ved 6 t, 0,4 % ved 24 t).
  - `[NOTE FOR PM]` Ved 6 t bruker dashbordet et spor som kan være opptil 6 t eldre enn «nå». Å kutte ved «nå» ville gitt ferskere data, men da ville input i drift ikke ligne input i trening. Gruppa velger konsistens framfor ferskhet.
- **FR9 — Modellprediksjon.** Modellen leverer predikert ankomst og varsel per anløp og horisont gjennom samme grensesnitt som baselinen. Dashbordet bytter kilde uten endringer i visningskoden.
  - Hvilken horisont som brukes for en rad, bestemmes av bøtta i FR2.
  - Varsel = `predikert ankomst − kalibrert baseline > 120 min`, altså samme terskel og retning som fasitetiketten. `[ASSUMPTION]`
- **FR10 — Modell mot baseline.** Panelet og `metrikker.json` viser modell og kalibrert baseline side om side, **per horisont og per gruppe**, på nøyaktig samme anløp. Det betyr at tallet for «ingen AIS-tilstand» regnes med som baseline-prediksjoner, og at et tall bare for rader med tilstand rapporteres i tillegg.
  - **±30 min:** modellen lykkes hvis den har høyere andel innenfor ±30 min enn baselinen på Øvrige, separat for hver horisont.
  - **Varsel:** grunnraten er **19,5 %** forsinket blant Øvrige i testperioden (signert, n = 996 med fasit). Briefen, statusnotatet og addendumet bruker det samme tallet (rettet 22.10.2026). Baselinen kan ikke varsle, så referansen er regelen «varsle alle»: presisjon 19,5 %, recall 100 %, F1 ≈ 0,33. Modellen lykkes på varsel hvis F1 er høyere enn referansen. `[ASSUMPTION]`
  - Presisjon, recall og F1 vises alltid sammen, og et tap vises like tydelig som en seier.

### Generativt AI-lag (E3)

- **FR11 — Begrunnelse per anløp.** Detaljsiden viser høyst 3 setninger (≤ 400 tegn) om hvorfor avviket er ventet, merket «KI-generert».
  - Teksten bygges bare fra `Prediksjon.forklaring` og anløpsdata. Fasit sendes aldri med.
  - **Test:** alle tall og skipsnavn i teksten finnes i inputen.
  - På baseline (hvis E2 glipper) beskriver teksten gruppe, horisont og den historiske spredningen for gruppen. Den påstår aldri at et avvik er ventet.
- **FR12 — Forstyrrelsesbrief.** Øverst på hovedskjermen står 3–5 setninger om vinduet.
  - Utvalget er anløpene med varsel, sortert etter predikert avvik, høyst 3.
  - Er det ingen varsler, eller er baselinen aktiv, sier briefen det rett ut.
  - **Manuell sjekk (briefens produktkriterium):** en person utenfor gruppa leser briefen for standardvinduet og nevner, uten hjelp, hvilke anløp som bør følges og hvorfor. Resultatet logges.
- **FR13 — Testmodus.** Uten API-nøkkel kjører AI-laget i testmodus. Det er standard. Testmodus viser lagrede ekte svar for demovinduene **08.10.2025 08:00** og **17.09.2025 08:00**, og ellers en deterministisk mal. Begge er tydelig merket. README nevner demovinduene.
- **FR14 — Kart (valgfritt).** Kart over anløpene i vinduet, med posisjon ved kuttpunktet fra tilstandsutdraget (NFR1). Lavest prioritet i hele prosjektet og kan droppes (se §6).

## 5. Universell utforming (krav fra start)

Mål: WCAG 2.1 nivå AA for de kravene som gjelder appen. Hvert punkt har en test eller en manuell sjekk i [`docs/ux/dashbord.md` §6](ux/dashbord.md#6-sjekkliste-for-universell-utforming).

- **UU1 — Kontrast.** Tekst ≥ 4,5:1, store tekster og UI-grenser ≥ 3:1, i både lyst og mørkt tema. Testes automatisk mot fargetokenene.
- **UU2 — Tastatur.** Alt kan nås og brukes med Tab, Shift+Tab, Enter og Space i logisk rekkefølge. Synlig fokusmarkering. «Hopp til innhold»-lenke først på siden.
- **UU3 — Ikke bare farge.** Varsel og FORSINKET har både ikon og tekst. Fargen forsterker, men bærer ikke informasjonen alene.
- **UU4 — Alt-tekst.** Alle ikoner som bærer mening har tekstalternativ. Rene pynteikoner har `alt=""` eller `aria-hidden`. Kart (FR14) får en tekstlig ekvivalent: lista selv.
- **UU5 — Skjemaetiketter.** Hvert felt har en synlig `<label>`. Feilmeldinger er koblet til feltet (`aria-describedby`) og sier hva som er feil og hva som er gyldig.
- **UU6 — Skjermstørrelser.** Brukbar fra 360 px til 1920 px bredde uten horisontal rulling, og ved 200 % zoom. Under 640 px vises anløp som kort i stedet for tabell.
- **UU7 — Semantikk.** `lang="nb"`, én `h1`, ekte `<table>` med `<th scope>`, `aria-sort` på sorterbar kolonne, landemerker (`header`, `main`, `nav`).

## 6. Ikke-funksjonelle krav

Kriterienumrene viser til [`docs/vurderingskriterier.md`](vurderingskriterier.md).

- **NFR1 — Kjørbarhet (kriterium 6).** Sensor skal kunne klone repoet og ha appen kjørende på **under 20 minutter** ved å følge README, uten gruppas nøkler eller kontoer og uten nett utover `pip install`. Dette forutsetter:
  - **Versjonert datautdrag** i `data/utdrag/`, ikke den gitignorede `pipeline/data/`.
  - **Lagret baseline** (`data/baseline.json`: offset per gruppe, splittidspunkt, kildefilens sjekksum), slik at ingenting må regnes ut på nytt ved oppstart.
  - **`.env.example`** med alle variabler og *ingen* ekte nøkler. Appen starter uten `.env`.
  - Fra E2: **versjonert tilstandsutdrag** (`data/utdrag/tilstand_ved_kutt.csv`, én rad per anløp og horisont, regnet etter FR9a, med kildens sjekksum) og **lagret modellartefakt**. Sensor trenger verken AIS-cachen eller å trene. Grense: under 10 MB til sammen.
  - Fra E3: **testmodus som standard** (FR13).
  - Verifisert med en *klone-test*: et gruppemedlem som ikke bygde oppsettet følger README på en ren maskin. Tiden loggføres.
- **NFR2 — Testbarhet (kriterium 3).** Hver story har akseptansekriterier som kan sjekkes og en navngitt test, automatisk der det går og ellers et manuelt sjekkpunkt. `pytest` kjører uten nett og uten `pipeline/data/` på under ett minutt. `GET /` svarer på under 1 s lokalt for standardvinduet.
- **NFR3 — Ærlige tall.**
  - Dashbord og evalueringsskript bruker *samme* metrikkfunksjon.
  - **Modellvalg, features og tuning skjer bare på en valideringsdel:** de siste 20 % av treningsdataene, kronologisk.
  - **Testperioden brukes bare til tallene som rapporteres.** Antall kjøringer mot testperioden logges i `metrikker.json` og i resultatnotatet.
  - Baselinetallene i FR8 er en regresjonstest. Endrer de seg, er noe galt.
- **NFR4 — Sporbarhet (kriterium 1).** Én story = én commit, med story-ID først i commit-meldingen (`E1-S03: …`). Én branch og én PR per epic. PR-beskrivelsen lister storyene og lenker til promptloggen for øktene (`docs/prompts/`).
- **NFR5 — Enkelhet (kriterium 5).** Ingen database, ingen JS-rammeverk, ingen byggesteg. Begrunnet i arkitekturen (A1–A3).
- **NFR6 — Hemmeligheter (kriterium 7).** Nøkler bare i `.env`, som er gitignored. Ingen nøkkel trengs for å kjøre eller teste.

## 7. Utenfor v1, og avvik fra briefen

Som i briefens Scope/OUT: live-data, flere havner, API for andre, innlogging og roller. Ny henting av seilasene uten AIS i det låste datasettet er også utenfor v1 (beslutning 07). I tillegg: redigering av data, eksport, varsler (e-post/push) og historikk over valgte «nå»-tidspunkt.

**Bevisste avvik fra briefen** (briefen oppdateres så kjeden stemmer, se §8):

- **Kart** (brief Scope IN 4) er nedprioritert til valgfritt (FR14). Det er det minst testbare elementet og det minst nødvendige for vaktas spørsmål, og posisjonsdata finnes først med tilstandsutdraget i E2.
- **Dagsbrief** (brief Solution) er gjort om til en brief for 24 t-vinduet fra valgt «nå» (FR12). Det tilsvarer det samme for vakta.
- **Avspilling av en «periode»** (brief Solution) er avgrenset til ett 24 t-vindu om gangen. Det er det vakta faktisk ser på.
- **Havnekaptein/driftsleder** (brief, sekundærbruker) får ingen egne visninger i v1.
- **HTTP Basic Auth** (brief Scope IN 5) er ikke nødvendig, siden appen kjøres lokalt.

## 8. Åpne spørsmål

| Spørsmål | Avgjøres i | Eier |
|---|---|---|
| Én modell, eller separate for Passasjer og Øvrige? | E2-S01 | Felipe |
| Er rapportert ETA verdien slik den var ved `t_24`, eller en senere oppdatering? Sjekk Kystdatahuset-dokumentasjonen og rådata (A1 i §9). | E2-S01 | Theodor |
| Bekreft suksesskriteriet for varsel (F1 mot «varsle alle», A2 i §9) før første modell trenes | E2-S01 | Felipe |
| Før opp avvikene i §7 i brief.md og brief.no.md. (Halen er rettet til 19,5 % signert 22.10.2026, E0-S08.) | før fase 3 | Theodor |
| Hvilken språkmodell-leverandør skal brukes i ekte modus? Arkitekturen antar Anthropic, men adapteren gjør byttet billig. | E3-S03 | Thomas |

**Lukket:** *Hva skiller 6 t fra 24 t?* Kuttpunktet ved rapportert ETA − H (FR9a, beslutning 08, 16.10.2026). *Er skipene utenfor AIS-rekkevidde 24 t før, så 24 t-horisonten må droppes?* Nei. ≈ 93 % har posisjon med 24 t tilbakeblikk, og de fleste ligger i en norsk havn (beslutning 09, 22.10.2026). *Skal `empty`-seilasene hentes på nytt?* Nei. Datasettet er låst, og 46,6 % og alle tall nedstrøms bygger på det. 87,1 % dekning føres som en kjent underestimering, og ny henting er videre arbeid (beslutning 07, korrigert 22.10.2026).

## 9. Antakelser

- **A1** (FR9a, FR10): rapportert ETA er kjent ved `t_24`. Datasettet har én ETA per anløp og ingen tidsstempel for når den ble meldt. Er den oppdatert senere, får både modell og baseline litt mer informasjon enn vakta hadde. Det rapporteres som begrensning hvis det ikke kan avkreftes.
- **A2** (FR10): suksess på varsel = F1 høyere enn «varsle alle» (≈ 0,33 på Øvrige).
- **A3** (FR9): varselet er en terskel på predikert avvik (> 120 min), ikke en egen klassifikator. Kan endres i E2-S01, men da endres FR9 først.

## Endringslogg

- **2026-10-16** — Første versjon (E0-S01). Designvalg fra UX-runden: simulert «nå» + 24 t-vindu, desktop først, kronologisk liste med avvik markert, Python/Flask.
- **2026-10-16** — Oppdatert etter BMAD-validering (E0-S06; karakter *Poor*, 1 critical og 10 high). Endringer:
  - Nytt FR9a: informasjonskutt ved rapportert ETA − H, gruppas beslutning, beslutning 08.
  - Horisont-bøtta regnes fra rapportert ETA.
  - Avvik og FORSINKET regnes alltid mot kalibrert baseline.
  - Fasit mangler skilles på tre årsaker.
  - FR8 har fått dekning, naiv baseline for Passasjer og støttetall.
  - FR10 har fått suksesskriterier per horisont og grunnraten 19,5 %.
  - NFR3 har fått valideringssplitt, og NFR1 har fått tilstandsutdrag.
  - FR11–FR13 er gjort testbare.
  - Nye seksjoner: ordliste (§3), avvik fra briefen (§7) og antakelser (§9).
- **2026-10-22** — E0-S08: halen er 19,5 % (signert forsinket, `er_forsinket`) i alle levende dokumenter. Det absolutte tallet er fjernet fra FR10, og det åpne spørsmålet i §8 er snevret inn til avvikene i §7.
- **2026-10-22** — E0-S10, beslutning 09: 24 t-horisonten beholdes. FR9a har fått tilbakeblikk på 24 t og krav om at posisjoner filtreres på tidsstemplet i svaret, siden API-et forskyver og kutter vinduer. Nytt åpent spørsmål om ny henting av `empty`-seilasene.
- **2026-10-22** — E0-S13, beslutning 07 korrigert: gruppespørsmålet om ny henting er besvart med nei, og ny henting er ført under §7. Teksten for `empty` i FR4 er endret til «ingen AIS-data hentet», siden dataene finnes i Kystdatahuset.
