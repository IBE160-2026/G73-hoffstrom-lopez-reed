---
title: "Epics og stories"
status: aktiv
created: 2026-10-16
updated: 2026-10-27
bygger_på: docs/prd.md, docs/arkitektur.md, docs/ux/dashbord.md
---

# Epics og stories

**Bygger på:** [`docs/prd.md`](prd.md) (FR/UU/NFR), [`docs/arkitektur.md`](arkitektur.md) (A1–A8) og [`docs/ux/dashbord.md`](ux/dashbord.md) (skjerm A–C).

## Arbeidsregler

- **Én branch per epic:** `epic/e1-dashbord-v1`, `epic/e2-modell`, `epic/e3-ai-lag`. Én PR inn til main per epic. Store epics kan få delvise PR-er underveis, for eksempel etter E1-S06, så main alltid har noe som kjører.
- **Én commit per story.** Story-ID står først i commit-meldingen:
  ```
  E1-S04: Legg til prediktor-grensesnitt og kalibrert baseline
  ```
  Da finner sensor (og vi) koden til en story med `git log --oneline --grep 'E1-S04'`.
- **Ferdig betyr:** akseptansekriteriene er oppfylt, testen er skrevet og `pytest` er grønn, og statusen under er satt til ✅ *i samme commit*. Avviker oppførselen fra PRD- eller UX-dokumentet, oppdateres det dokumentet i samme commit, med en linje i endringsloggen.
- **Ny eller endret story underveis** legges til her med neste ledige nummer. Nummer gjenbrukes aldri, og forkastede stories markeres ✗ med begrunnelse.
- PR-beskrivelsen lister storyene og lenker til promptloggen for øktene (`docs/prompts/`).

Status: ☐ ikke startet · ◐ pågår · ✅ ferdig · ✗ forkastet

---

## E0 — Planlegging (fase 2, 16.–23. okt) · branch `epic/e0-planlegging` (merget i PR #2), oppfølging på `epic/e0-oppfolging`

| ID | Story | Leveranse | Status |
|---|---|---|---|
| E0-S01 | PRD | `docs/prd.md` | ✅ |
| E0-S02 | UX-skisser | `docs/ux/dashbord.md` | ✅ |
| E0-S03 | Arkitektur | `docs/arkitektur.md` | ✅ |
| E0-S04 | Epics og stories | `docs/epics.md` | ✅ |
| E0-S05 | Plan, arbeidsflyt og promptlogg oppdatert | `docs/plan.md`, `docs/prompts/` | ✅ |
| E0-S06 | BMAD-validering av PRD, og PRD oppdatert med funnene | `_bmad-output/planning-artifacts/prds/…/validation-report.md`, `docs/prd.md` | ✅ |
| E0-S07 | Beslutning 08 (horisont ved rapportert ETA − H) og nedstrøms dokumenter oppdatert | `docs/beslutninger/08-…`, `docs/epics.md`, `docs/arkitektur.md`, `docs/ux/dashbord.md` | ✅ |
| E0-S08 | Halen rettet fra 24,3 % (absolutt) til 19,5 % (signert forsinket) i alle levende dokumenter | `docs/brief.md`, `docs/brief.no.md`, `docs/status.md`, `docs/addendum.md`, `docs/prd.md` | ✅ |
| E0-S09 | Kursmateriale (`docs/kilder/`) fjernet fra arbeidstreet; beslutning 10 om hvorfor historikken ikke skrives om | `.gitignore`, `docs/beslutninger/10-…` | ✅ |
| E0-S10 | Beslutning 09: AIS-dekning ved kuttpunktene avklart før modellfasen, PRD oppdatert | `docs/beslutninger/09-…`, `pipeline/sjekk_ais_dekning_kutt.py`, `docs/prd.md` | ✅ |
| E0-S11 | Promptlogg 22.10 med vurdering av BMAD-dev-flyten (beholdes for ikke-trivielle stories) | `docs/prompts/2026-10-22.md` | ✅ |
| E0-S12 | Tidsstempelfilteret for AIS-svar trukket ut som funksjon, med test som er vist å feile når filteret fjernes eller svekkes | `pipeline/sjekk_ais_dekning_kutt.py`, `tests/test_ais_filter.py` | ✅ |
| E0-S13 | Beslutning 07 korrigert (flagg/MMSI motbevist, ingen ny henting, 87,1 % som kjent underestimering), brief/status/addendum/PRD/UX fulgt opp | `docs/beslutninger/07-…`, `docs/prd.md` | ✅ |
| E0-S14 | Hentestegene i pipelinen merket som låst: `main()` stopper med forklaring, README og status oppdatert | `pipeline/fetch_ais.py`, `pipeline/fetch_voyages.py`, `README.md` | ✅ |
| E0-S15 | Refleksjonsnotater opprettet: KI-feil fanget logges samme dag (første oppføringer 22.10) | `docs/refleksjon/notater.md` | ✅ |
| E0-S16 | Løpende sesjonslogg: fast ID for alle loggcommits. `docs/prompts/` til og med 27.10, deretter faglærers format i `.logs/<bruker>/` (CLAUDE.md) | `docs/prompts/`, `.logs/` | ◐ løpende |
| E0-S17 | Omfangssjekk for E1: MÅ/KAN, UU-minimum lagt inn i MÅ, avhengigheter koblet om | `docs/epics.md` | ✅ |
| E0-S18 | To avgjørelser før E1-S06: vinduet velger på rapportert ETA i v1, og tider vises avrundet til nærmeste minutt (bare visning) | `docs/epics.md`, `docs/ux/dashbord.md` | ✅ |

---

## E1 — Dashbord v1 på kalibrert baseline (fase 3, 24. okt–6. nov) · `epic/e1-dashbord-v1`

**Mål:** en app sensor kan kjøre og vurdere selv om ingenting annet blir ferdig. **Ferdig når:** klone-testen i E1-S16 er under 20 min og UU-sjekklista er utfylt.

**Omfang (E0-S17, 27.10):** fase 3 slutter 6. nov.
- **MÅ** er det som trengs for at sensor kan klone repoet, følge README og se et fungerende dashbord med baseline-prediksjoner på under 20 min, med universell utforming på det som vises.
- **KAN** tas i rekkefølgen under hvis tiden strekker til. KAN-storyene er ikke flyttet ut av E1.

| | Stories, i rekkefølge |
|---|---|
| **MÅ** | E1-S04 ✅ → E1-S05 ✅ → E1-S06 ✅ → E1-S16. Første klone-test kjøres rett etter S06, og den gjentas til slutt. |
| **KAN** | E1-S07 → E1-S13 → E1-S08 → E1-S09 → E1-S11 → E1-S12 → E1-S10 → E1-S15 → E1-S14 → E1-S17 |

UU1–UU7 er ikke KAN. Minimumskravene står som akseptansekriterier i E1-S06 (det MÅ viser), og UU-sjekklista fylles ut i E1-S16. Det som gjenstår av E1-S13, E1-S14 og E1-S15, gjelder skjermer og temaer som bygges i KAN-storyene.

### E1-S01 — Prosjektskjelett ✅ · MÅ
**Krav:** NFR1, NFR2, A1 · **Avhenger av:** —
- `app/__init__.py` med `create_app()`. `flask --app app run` svarer 200 på `/`.
- `requirements.txt` (flask, tzdata, pytest), `.env.example` som i arkitektur §7, og `tests/conftest.py` med app-fixture.
- Appen starter uten `.env`.

**Test:** `tests/test_app.py::test_forside_svarer_200`

### E1-S02 — Datautdrag og lagret baseline ✅ · MÅ
**Krav:** NFR1, A4 · **Avhenger av:** E1-S01
- `scripts/lag_utdrag.py` leser `pipeline/data/bergen_eta_avvik.csv` og skriver `data/utdrag/anlop.csv` (kolonnene i arkitektur §4) og `data/baseline.json`.
- Splitt og offset regnes på samme måte som i `derive_arrivals.py`: 6 260/1 566 rader og 44,8/64,2 min.
- Skriptet er deterministisk: to kjøringer gir identiske filer. Den genererte dataen committes i samme commit.

**Test:** `tests/test_lag_utdrag.py`, som kjører skriptet på `tests/fixtures/` og sjekker kolonner, splitt og offset.

### E1-S03 — Datalag ✅ · MÅ
**Krav:** FR2, FR5 · **Avhenger av:** E1-S02
- `last_utdrag()` gir `Anlop`-objekter med tz-aware UTC-tider. Tider uten suffiks tolkes som UTC.
- `anlop_i_vindu(naa, timer=24, vis="alle"|"passasjer"|"ovrige")` gir anløp med rapportert ETA i [naa, naa + 24 t).
- Anløp med `status_in_area ≠ ok` har `faktisk_ankomst = None`.

**Test:** `tests/test_data.py`, med vindusgrenser (inkludert start, ekskludert slutt), filter og manglende fasit.

### E1-S04 — Prediktor-grensesnitt og kalibrert baseline ✅ · MÅ
**Krav:** FR3, A5 · **Avhenger av:** E1-S03
- `Prediksjon`, `Prediktor` og `velg_prediktor()` som i arkitektur §3.
- `BaselinePrediktor`: `predikert = eta − offset[gruppe]`, `forventet_forsinket = None`, `kan_varsle = False`. `forklaring` inneholder gruppe og offset.
- Kontrakttesten er parametrisert, så E2 kan legge til sin prediktor.
- Prediktorer får `PrediksjonsInput` fra `lag_input(anlop, naa)`, aldri `Anlop`, så de ikke kan lese fasiten. `t_kutt = min(eta − H, naa)`.
- `test_kutt_ikke_etter_naa` er flyttet hit fra E2-S07.

**Test:** `tests/test_prediktor_kontrakt.py`, `tests/test_baseline.py` (BERGEN ENERGY: 11:00 → 09:55 norsk tid)

### E1-S05 — Metrikkmodul og dataregresjon ✅ · MÅ
**Krav:** FR8, NFR3, A6 · **Avhenger av:** E1-S04
- `andel_innenfor(prediksjoner, anlop, minutter=30)` regner bare på anløp med fasit.
- På testsplitten av det ekte utdraget gir baselinen **46,6 %** (Øvrige) og **79,6 %** (Passasjer). Naiv ETA gir **12,8 %** (Øvrige) og **7,4 %** (Passasjer). Alt avrundes til én desimal.
- `dekning()` gir antall per status. Testperioden har 1 427 av 1 566 med fasit: 126 `empty`, 8 `not_detected` og 5 `avkortet_av_neste_seilas`.
- Alle tallene lages gjennom S04-kontrakten (`lag_input(a, eta − H)` → `prediker`, H = 6 og 24). Naiv ETA er en egen referanseprediktor, `NaivPrediktor`, som står i `PREDIKTORER` og består kontrakttesten. Den kan ikke velges med `velg_prediktor`.
- ±30 min er inklusiv og regnes på uavrundede tider. Regresjonstesten låser eksakte antall (464/996, 343/431, 127/996, 32/431).

**Test:** `tests/test_metrikker.py` (fixture), `tests/test_dataregresjon.py` (ekte utdrag)

### E1-S06 — Hovedskjerm med anløpsliste ✅ · MÅ
**Krav:** FR2, FR3, UX skjerm A, UU1/UU2/UU4/UU6/UU7 (minimum) · **Avhenger av:** E1-S04
- `GET /` uten parametre viser vinduet fra 08.10.2025 08:00 norsk tid: 15 anløp, sortert etter predikert ankomst, med kolonnene fra skjerm A.
- Prediktor-stripa viser «Kalibrert baseline» og teksten om at baselinen ikke varsler. Varselkolonnen viser «–».
- **Vinduet velger på rapportert ETA i [nå, nå + 24 t)** (alternativ A i S04-specen, avgjort 27.10). Om predikert ankomst skal brukes, vurderes når modellen byttes inn (E2-S08).
- Tider vises i norsk tid, **avrundet til nærmeste minutt** (avgjort 27.10). BERGEN ENERGY (09:55:48) vises som «ons 09:56». Avrundingen gjelder bare visningen: ±30 min, avvik og alle beregninger bruker uavrundede tider. Testen dekker et tidspunkt med sekunder ≥ 30 og et med < 30.
- Horisonten regnes fra **rapportert ETA − nå**: ≤ 6 t eller 6–24 t (PRD FR2). Predikert ankomst før «nå» får hjelpeteksten «predikert før valgt tidspunkt».
- Tomt vindu gir meldingen fra UX §5.
- **UU-minimum (E0-S17):**
  - **UU1 kontrast:** `static/style.css` har tokenene for lyst tema fra UX §7 (`--bakgrunn`, `--flate`, `--tekst`, `--dempet`, `--aksent`, `--kant`). Alle par som brukes, har ≥ 4,5:1 for tekst og ≥ 3:1 for kant.
  - **UU2 tastatur:** «Hopp til innhold» er første element. Alle lenker og knapper kan nås med Tab i logisk rekkefølge, og fokusringen er 3 px `--aksent` (aldri `outline: none` uten erstatning).
  - **UU4 alt-tekst:** ikoner med mening har tekstalternativ, og pynteikoner har `aria-hidden`. Varselkolonnens «–» har en forklaring som kan leses (FR3).
  - **UU6 skjermstørrelser:** `<meta name="viewport">`. Under 640 px vises radene som kort med `data-label`. Ingen horisontal rulling på 360 px, 1280 px eller ved 200 % zoom.
  - **UU7 semantikk:** `lang="nb"`, én `h1`, ekte `<table>` med `<th scope="col">`, og landemerkene `header` og `main`.
  - **UU5 skjemaetiketter** gjelder ikke S06, siden MÅ ikke har noe skjema. Kravet står allerede i E1-S07 og E1-S08 for når de bygges.

**Test:** `tests/test_ruter.py::test_standardvindu`, `::test_tomt_vindu`, `tests/test_visning.py`, `tests/test_kontrast.py` (tokenene fra `style.css`), `tests/test_uu_struktur.py` (hopp-lenke, `lang`, én `h1`, `th scope`, landemerker, viewport, `data-label`), og manuell sjekk av 360 px / 200 % zoom og tastaturrekkefølge

### E1-S07 — Tidsvelger for «nå» med validering ☐ · KAN
**Krav:** FR1, UU5 · **Avhenger av:** E1-S06
- Skjemaet har dato og klokkeslett med synlige `<label>`, og knappen «Oppdater». Skjemaet sendes ikke automatisk.
- Gyldig `naa` i testperioden gir det vinduet. Ugyldig eller utenforliggende verdi gir status 200, feilmelding med `aria-describedby` og `aria-invalid`, og standardvinduet i lista.

**Test:** `tests/test_ruter.py::test_naa_gyldig`, `::test_naa_utenfor_testperiode`, `::test_naa_ugyldig_format`

### E1-S08 — Filter: alle / passasjer / øvrige ☐ · KAN
**Krav:** FR5 · **Avhenger av:** E1-S07
- Radiogruppe i `<fieldset>` med `<legend>`. `vis=ovrige` på standardvinduet gir 9 rader.
- Filteret beholdes i URL-en og på tvers av andre valg.

**Test:** `tests/test_ruter.py::test_filter_ovrige`

### E1-S09 — Fasit-bryter ☐ · KAN
**Krav:** FR4, UU3, UX skjerm A2 · **Avhenger av:** E1-S08
- `fasit=1` legger til kolonnene Faktisk og Avvik. Avvik = faktisk − **kalibrert baseline** (ordliste, PRD §3), aldri mot den aktive prediktoren. Avvik over 120 min viser ▲ + «FORSINKET» + varselfarge.
- I standardvinduet er BERGEN ENERGY, OCEAN RESPONSE og SIEM PEARL merket FORSINKET.
- Anløp uten fasit viser årsaken: tre ulike tekster for `empty`, `not_detected` og `avkortet_av_neste_seilas` (PRD FR4).
- `fasit=0` (standard) viser ingen fasitdata i HTML-en.

**Test:** `tests/test_ruter.py::test_fasit_av_skjuler`, `::test_fasit_merker_forsinket`, `::test_fasit_mangler_tre_aarsaker`

### E1-S10 — Sortering ☐ · KAN
**Krav:** FR6, UU7 · **Avhenger av:** E1-S09
- Sorteringsknappene ligger i `<th>`, og aktiv kolonne har `aria-sort`.
- `sorter=avvik` sorterer synkende (mest forsinket først) og virker bare når `fasit=1`. Ellers faller den tilbake til predikert ankomst uten feil.

**Test:** `tests/test_ruter.py::test_sorter_avvik`, `::test_sorter_avvik_uten_fasit`

### E1-S11 — Detaljside for anløp ☐ · KAN
**Krav:** FR7, UX skjerm C · **Avhenger av:** E1-S10
- `/anlop/<id>` viser skipsdata, tidspunkter i `<dl>` og forklaringen fra `Prediksjon.forklaring`, med malen per gruppe fra PRD FR7 (44,8 eller 64,2 min).
- «Tilbake» beholder `naa`, `vis`, `fasit` og `sorter`. Fasit vises bare hvis `fasit=1`.
- Ukjent ID gir 404 med lenke tilbake.

**Test:** `tests/test_ruter.py::test_detalj`, `::test_detalj_404`, `::test_detalj_tilbakelenke`

### E1-S12 — Treffsikkerhetspanel og metodeside ☐ · KAN
**Krav:** FR8 · **Avhenger av:** E1-S11
- Panelet viser de fire tallene og dekningen fra E1-S05, regnet med `metrikker.py` (ikke hardkodet) og merket «hele testperioden».
- Søylene har tekstverdi, så de ikke bare er grafikk. `/metode` forklarer baseline, ±30 min og testperioden, viser dekning per status og MAE/median som støttetall, har forklaringssetningen fra beslutning 04 og lenker til beslutning 04/05.

**Test:** `tests/test_ruter.py::test_panel_tall`, `::test_metode`

### E1-S13 — Visuelt design og kontrast ☐ · KAN
**Krav:** UU1, UX §7 · **Avhenger av:** E1-S06
- Lyst tema, fokusring og kontrasttest for tekst/kant er flyttet til E1-S06 (MÅ). Her gjenstår mørkt tema, `--varsel`/`--ok` og `tabular-nums`.
- `static/style.css` har tokenene fra UX §7, lyst og mørkt tema (`prefers-color-scheme`), fokusring og `tabular-nums`.
- Alle tokenpar i UX §7 har kontrast ≥ 4,5:1 (tekst) og ≥ 3:1 (`--kant`).

**Test:** `tests/test_kontrast.py`, som leser tokenene fra CSS-fila.

### E1-S14 — Responsiv layout ☐ · KAN
**Krav:** UU6, UX skjerm B · **Avhenger av:** E1-S13
- Kortvisning under 640 px for hovedlista er flyttet til E1-S06 (MÅ). Her gjenstår skjemaet i `<details>` og responsivitet for skjermene fra KAN-storyene.
- Under 640 px vises tabellradene som kort med `data-label`, og skjemaet ligger i `<details>`. Ingen horisontal rulling på 360 px eller ved 200 % zoom.

**Test:** manuell, med punkt UU6 i UX §6. `tests/test_uu_struktur.py::test_viewport_og_data_label`

### E1-S15 — UU-gjennomgang ☐ · KAN
**Krav:** UU2–UU7 · **Avhenger av:** E1-S14
- Minimumskravene for det MÅ viser, ligger i E1-S06, og sjekklista fylles ut i E1-S16. Her gjenstår gjennomgangen av skjermene fra KAN-storyene og skjermleser-sjekken (VoiceOver).
- Hopp-lenke, landemerker, `lang="nb"`, én `h1`, `th scope` og alt-tekst er på plass.
- Den manuelle sjekklista i UX §6 er gjennomført og utfylt med dato og resultat. Funn rettes i denne storyen eller føres opp som nye stories.

**Test:** `tests/test_uu_struktur.py` + utfylt sjekkliste

### E1-S16 — README og klone-test ☐ · MÅ
**Krav:** NFR1, UX §6 · **Avhenger av:** E1-S05, E1-S06
- README har en «Kom i gang»-seksjon: krav (Python ≥ 3.9), venv, `pip install -r requirements.txt`, `flask --app app run`, `pytest`, og hva man bør se: standardvinduet med 15 anløp, og 46,6 % fra dataregresjonen i E1-S05 (i panelet hvis E1-S12 er bygd).
- Et gruppemedlem som ikke bygde E1 kloner repoet på nytt og følger bare README. Tiden logges i README (mål: < 20 min), og alt som var uklart rettes.

- UU-sjekklista i UX §6 fylles ut med dato og resultat for alt som er bygd. Rader for skjermer som ikke er bygd, merkes «ikke bygd (KAN)». Med dette står «Ferdig når» for E1 uendret.

**Test:** klone-test med loggført tid, og utfylt sjekkliste

### E1-S17 — Skjermbilder mot skisse ☐ · KAN
**Krav:** kriterium 4 · **Avhenger av:** E1-S16
- `docs/ux/skjermbilder/` har skjerm A, A2, B og C fra den kjørende appen (1280 px og 360 px). UX-dokumentet får en seksjon om hva som ble annerledes enn skissen, og hvorfor.

**Test:** manuell. Filene finnes og avvikene er beskrevet.

---

## E2 — Modell bak dashbordet (fase 4, 7.–27. nov) · `epic/e2-modell`

**Mål:** en modell som slår den kalibrerte baselinen, synlig i det samme dashbordet. Klarer den det ikke, skal det vises ærlig. **Ferdig når:** dashbordet viser modellen som standard, og resultatnotatet er skrevet.

**Grunnlag:** [beslutning 08](beslutninger/08-horisont-kuttes-pa-rapportert-eta.md). Kuttpunktet er `t_H = rapportert ETA − H`, aldri faktisk ankomst (PRD FR9a). Dagens AIS-cache har posisjon ved kuttpunktet for bare 31 % (6 t) og 7 % (24 t) av Øvrige i testperioden. Derfor kommer det en egen henting (S02) før noe trenes.

### E2-S01 — Gjenstående modellvalg ◐
**Krav:** PRD §8, §9 · **Avhenger av:** E1-S05
- Horisonten er avgjort i beslutning 08 (16.10.2026).
- Gjenstår, og legges til i beslutning 08 eller en ny beslutning:
  - én eller to modeller (Passasjer/Øvrige)
  - om rapportert ETA er kjent ved `t_24` (A1). Sjekk Kystdatahuset-dokumentasjonen og rådata.
  - bekreftelse av suksesskriteriet for varsel (A2)
- Endres A2 eller A3, oppdateres PRD FR9/FR10 først.

**Test:** beslutningen er gjennomgått av hele gruppa (godkjent i PR).

### E2-S02 — Målrettet AIS-henting ved kuttpunktene ☐
**Krav:** FR9a · **Avhenger av:** E2-S01
- `pipeline/fetch_ais_kutt.py` henter AIS for [`t_H` − 24 t, `t_H`] per anløp og H ∈ {6, 24}, med samme caching og pausing som `fetch_ais.py` (beslutning 09).
- Ny API-adresse (`kystdatahuset.kystverket.no`). Det bes om et vindu med minst én dags margin på hver side, og posisjonene filtreres på tidsstemplet i svaret, siden API-et forskyver vinduet +1/+2 t og kan kutte ved midnatt (beslutning 09, funn B–C).
- Vinduet regnes bare fra rapportert ETA. Skriptet leser ikke `arrival_in_area`.
- Dekning per horisont, gruppe og splitt logges i `pipeline/data/ais_kutt_dekning.csv`.

**Test:** `tests/test_fetch_ais_kutt.py::test_vindu_fra_rapportert_eta` (vinduet endres ikke når faktisk ankomst endres), `::test_filtrerer_bort_punkter_etter_kutt` (et svar med punkter etter `t_H` gir ingen slike i cachen) og en loggført dekningstabell.

### E2-S03 — Tilstandsutdrag og lekkasjetest ☐
**Krav:** FR9a, NFR1 · **Avhenger av:** E2-S02
- `scripts/lag_tilstand.py` skriver `data/utdrag/tilstand_ved_kutt.csv`: én rad per anløp og H, med posisjon, gjenstående distanse, fart, kurs, alder på posisjon og flagget `allerede_ankommet`. Fila committes, og kildens sjekksum legges i `data/baseline.json`.
- Mangler posisjon i [`t_H` − 24 t, `t_H`], blir feltene tomme, og raden beholdes.

**Test:** `tests/test_tilstand.py::test_ingen_lekkasje` (punkter etter `t_H` fjernet eller flyttet, faktisk ankomst endret → identisk rad) og `::test_mangler_posisjon`

### E2-S04 — Features og valideringssplitt ☐
**Krav:** FR9a, NFR3 · **Avhenger av:** E2-S03
- `app/prediksjon/features.py` slår sammen tilstand og historikk. Historikken (for eksempel fartøyets tidligere avvik) kommer bare fra treningsanløp med faktisk ankomst før `t_H`.
- Valideringsdelen er de siste 20 % av treningsdataene, kronologisk, og testperioden røres ikke.

**Test:** `tests/test_features.py::test_historikk_uten_lekkasje`, `::test_valideringssplitt_kronologisk`

### E2-S05 — Tren 6 t- og 24 t-modell ☐
**Krav:** FR9, A7 · **Avhenger av:** E2-S04
- `scripts/tren.py` trener én modell per horisont med fast seed. Modellvalget gjøres på valideringsdelen.
- Resultatet lagres i `data/modell/modell_6t.joblib` og `modell_24t.joblib`, og scikit-learn legges i `requirements.txt`.

**Test:** `tests/test_tren.py`. Kjøring på fixturen gir samme prediksjon to ganger.

### E2-S06 — Evalueringsskript ☐
**Krav:** FR10, NFR3, A6 · **Avhenger av:** E2-S05
- `scripts/evaluer.py` bruker `app/metrikker.py` og skriver `data/modell/metrikker.json`, med følgende per horisont og gruppe, for modell og baseline på samme anløp:
  - andel innenfor ±30 min
  - presisjon, recall og F1 på varsel, mot «varsle alle»
  - MAE og median
  - dekning av tilstand
  - antall `allerede_ankommet`
- Skriptet teller kjøringer mot testperioden (`--test`) og lagrer antallet.

**Test:** `tests/test_evaluer.py`. Baselinetallene er lik dataregresjonen fra E1-S05.

### E2-S07 — ModellPrediktor ☐
**Krav:** FR9, A5 · **Avhenger av:** E2-S06
- Implementerer kontrakten, med `kan_varsle = True`. Horisonten velges fra `rapportert ETA − nå` (PRD FR2).
- Varselet er `predikert − kalibrert baseline > 120 min`. Uten tilstand brukes baselinen, merket.

**Test:** legges til i `PREDIKTORER` i `tests/test_prediktor_kontrakt.py` og må bestå alle kontrakt- og lekkasjetestene der. `::test_kutt_ikke_etter_naa` (`t_H ≤ nå` for alle rader i en avspilling) ble flyttet til E1-S04 og gjelder allerede.

### E2-S08 — Bytt inn i dashbordet ☐
**Krav:** FR3, FR4, FR9, UX §5 · **Avhenger av:** E2-S07
- `PREDIKTOR=auto` velger modellen når artefaktet finnes. Prediktor-stripa viser «Modell v1», varselkolonnen viser ▲ + «VARSEL», og med fasit på kommer kolonnen Prediksjonsfeil.
- Mangler artefaktet, faller appen tilbake til baseline med melding.
- Malene endres ikke utover stripa, varselkolonnen og prediksjonsfeil. Det er testen på at A5 holdt.

**Test:** `tests/test_ruter.py::test_modell_standard`, `::test_fallback_baseline`, og `::test_fasit_uavhengig_av_prediktor` (avvik og FORSINKET er like med `PREDIKTOR=baseline` og `PREDIKTOR=modell`)

### E2-S09 — Panel: modell mot baseline ☐
**Krav:** FR10 · **Avhenger av:** E2-S08
- Panelet viser modell og baseline side om side per horisont, pluss presisjon, recall og F1 mot referansen, lest fra `metrikker.json`. Taper modellen, vises det med samme tydelighet.

**Test:** `tests/test_ruter.py::test_panel_modell_mot_baseline`

### E2-S10 — Resultatnotat ☐
**Krav:** brief Success Criteria, NFR3 · **Avhenger av:** E2-S09
- `docs/resultater.md` dekker:
  - modell og baseline på testperioden per horisont
  - antall testkjøringer
  - dekning ved kutt
  - begrensningene: vintervridd test, AIS-hull og A1
  - om målene ble nådd
- Et negativt resultat rapporteres. README nevner modellen.

**Test:** tallene i notatet er lik `metrikker.json` (sjekkes i PR).

---

## E3 — Generativt AI-lag med testmodus (fase 5, 28. nov–5. des) · `epic/e3-ai-lag`

**Mål:** begrunnelser sensor kan se uten nøkkel. **Ferdig når:** appen kjører med `LLM_MODUS=test` uten nett, og ekte modus er vist og logget minst én gang.

### E3-S01 — Adapter og testmodus ☐
**Krav:** FR13, A8, NFR6 · **Avhenger av:** E2-S07 (eller E1-S04 hvis E2 glipper)
- `hent_begrunnelse(prediksjon, anlop)` og `hent_brief(vindu)`. `LLM_MODUS=test` er standard og gir en deterministisk mal-tekst merket «Testmodus».
- Ingen nettkall i testmodus.

**Test:** `tests/test_begrunnelse.py::test_testmodus_uten_nett` (nettkall blokkert i testen)

### E3-S02 — Input bygd fra modellens faktiske data ☐
**Krav:** FR11 · **Avhenger av:** E3-S01
- Input til AI-laget bygges bare fra `Prediksjon.forklaring` og `Anlop`. Fasit sendes aldri med, siden vakta ikke kjenner den.

**Test:** `tests/test_begrunnelse.py::test_input_uten_fasit`

### E3-S03 — Ekte klient og versjonert prompt ☐
**Krav:** FR11, A8 · **Avhenger av:** E3-S02
- `anthropic_klient.py` leser `ANTHROPIC_API_KEY` og `LLM_MODELL`, og prompten ligger i `app/begrunnelse/prompt.md`.
- Ved tidsavbrudd eller feil faller den tilbake til testmodus med merket fra UX §5.
- Den første ekte prompten og et svar logges i `docs/prompts/`.

**Test:** `tests/test_begrunnelse.py::test_ekte_med_mock`, `::test_fallback_ved_feil`

### E3-S04 — Begrunnelse på detaljsiden ☐
**Krav:** FR11 · **Avhenger av:** E3-S03
- Skjerm C viser begrunnelsen merket «KI-GENERERT» (eller «Testmodus»): høyst 3 setninger og ≤ 400 tegn (PRD FR11).
- Alle tall og skipsnavn i teksten finnes i inputen. På baseline påstår teksten aldri at et avvik er ventet.

**Test:** `tests/test_ruter.py::test_detalj_begrunnelse`, `tests/test_begrunnelse.py::test_tall_finnes_i_input`

### E3-S05 — Forstyrrelsesbrief på hovedskjermen ☐
**Krav:** FR12 · **Avhenger av:** E3-S04
- 3–5 setninger øverst på skjerm A om høyst 3 varslede anløp, sortert etter predikert avvik. Uten varsler, eller på baseline, sier briefen det rett ut (PRD FR12).
- Manuell sjekk: en person utenfor gruppa leser briefen for standardvinduet. Resultatet logges i `docs/ux/dashbord.md` §6.

**Test:** `tests/test_ruter.py::test_brief_nevner_varslede`, `::test_brief_uten_varsler`, og den manuelle sjekken

### E3-S06 — Opptak av ekte svar for demodager ☐
**Krav:** FR13 · **Avhenger av:** E3-S05
- `scripts/ta_opp_begrunnelser.py` kjører ekte modus for demovinduene 08.10.2025 08:00 og 17.09.2025 08:00 og lagrer svarene i `data/begrunnelser_opptak.json`. Testmodus viser opptaket når det finnes, så sensor ser ekte output uten nøkkel.

**Test:** `tests/test_begrunnelse.py::test_testmodus_bruker_opptak`

### E3-S07 — README for AI-laget ☐
**Krav:** NFR1 · **Avhenger av:** E3-S06
- README forklarer testmodus (standard) og ekte modus (`.env`), og hva sensor ser i hvert av dem.

**Test:** klone-testen fra E1-S16 gjentas med AI-laget.

### E3-S08 — Kart (valgfri) ☐
**Krav:** FR14, UU4 · **Avhenger av:** E3-S07
- Bare hvis E3-S01–S07 er ferdige før 3. des. Utdraget har ingen posisjoner, så omfanget avklares først.
- Kartet har en tekstlig ekvivalent og alt-tekst.

**Test:** avklares når storyen startes

---

## Sporbarhet: krav → stories

| Krav | Stories |
|---|---|
| FR1 | E1-S07 |
| FR2 | E1-S03, E1-S06 |
| FR3 | E1-S04, E1-S06, E2-S08 |
| FR4 | E1-S09, E2-S08 |
| FR5 | E1-S03, E1-S08 |
| FR6 | E1-S10 |
| FR7 | E1-S11 |
| FR8 | E1-S05, E1-S12 |
| FR9a | E2-S02, E2-S03, E2-S04, E2-S07 |
| FR9 | E2-S05, E2-S07, E2-S08 |
| FR10 | E2-S06, E2-S09, E2-S10 |
| FR11 | E3-S02, E3-S03, E3-S04 |
| FR12 | E3-S05 |
| FR13 | E3-S01, E3-S06 |
| FR14 | E3-S08 |
| UU1 | E1-S06, E1-S13 |
| UU2–UU7 | E1-S06, E1-S07, E1-S08, E1-S10, E1-S14, E1-S15, E1-S16 |
| NFR1 | E1-S01, E1-S02, E1-S16, E2-S03, E3-S07 |
| NFR2 | alle (test per story) |
| NFR3 | E1-S05, E2-S04, E2-S06, E2-S10 |
| NFR4 | arbeidsreglene øverst |
| NFR5 | E1-S01 (A1–A3) |
| NFR6 | E1-S01, E3-S01, E3-S03 |

## Endringslogg

- **2026-10-16** — Første versjon (E0-S04): E0 ferdig, og E1 (17 stories), E2 (9) og E3 (8) planlagt.
- **2026-10-16** — Etter PRD-validering og beslutning 08 (E0-S07):
  - E2 er skrevet om til 10 stories. Det er nye stories for AIS-henting ved kuttpunkt (S02), tilstandsutdrag med lekkasjetest (S03) og valideringssplitt (S04). E2 var ikke startet, så nummereringen er lagt om nå, før merge.
  - E1-S05/S06/S09/S10/S11/S12 og E3-S04/S05/S06 er tilpasset PRD-oppdateringen.
- **2026-10-22** — E0-S08–S10 lagt til som oppfølging etter merge av PR #2: halen rettet til 19,5 %, kursmateriale ut av repoet, og AIS-dekning ved kuttpunktene avklares (beslutning 09) før E2-S02.
- **2026-10-22** — E0-S10, beslutning 09: E2-S02 og E2-S03 bruker 24 t tilbakeblikk og filtrerer på tidsstemplet i svaret. Ny test i E2-S02 for at ingen punkter etter `t_H` slipper gjennom.
- **2026-10-27** — E1-S04: prediktorene får `PrediksjonsInput` i stedet for `Anlop` (arkitektur §3). `test_kutt_ikke_etter_naa` er flyttet fra E2-S07 til E1-S04.
- **2026-10-27** — E0-S17, omfangssjekk for E1 med 10 dager igjen av fase 3:
  - MÅ er S04–S06 og S16, og resten er KAN. KAN-storyene står fortsatt i E1.
  - UU-minimum (UU1, UU2, UU4, UU6, UU7) er flyttet inn i S06, og sjekklista inn i S16, så «Ferdig når» står uendret. Restene av S13, S14 og S15 er KAN.
  - S06 avhenger nå av S04, og S16 av S05 og S06.
  - E0-S16 er en fast ID for løpende sesjonslogg.
- **2026-10-27** — E0-S18: E1-S06 har fått to avgjørelser. Vinduet velger på rapportert ETA (A), og predikert ankomst vurderes i E2-S08. Tider vises avrundet til nærmeste minutt, men beregningene er uavrundet.
- **2026-10-27** — E1-S05: naiv ETA for Øvrige er 12,8 % (127/996), ikke 12,9 %. Pipelinen avrundet avviket til 0,1 min før ±30-sammenligningen, så seilas 3542899 (+30 min 1 s) ble telt som treff. `NaivPrediktor` er lagt til som referanseprediktor i kontrakttesten.
- **2026-10-27** — E1-S06: hovedskjermen viser standardvinduet (15 anløp) med UU-minimum og kort under 640 px. Testene er `test_ruter.py`, `test_visning.py`, `test_uu_struktur.py` og `test_kontrast.py`. Skjermbilder ligger i `docs/ux/skjermbilder/` og lages med `scripts/ta_skjermbilder.py` utenfor `pytest`. Avvikene fra skissene står i UX-endringsloggen.
