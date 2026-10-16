---
title: "Epics og stories"
status: aktiv
created: 2026-10-16
updated: 2026-10-16
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

## E0 — Planlegging (fase 2, 16.–23. okt) · branch `epic/e0-planlegging`

| ID | Story | Leveranse | Status |
|---|---|---|---|
| E0-S01 | PRD | `docs/prd.md` | ✅ |
| E0-S02 | UX-skisser | `docs/ux/dashbord.md` | ✅ |
| E0-S03 | Arkitektur | `docs/arkitektur.md` | ✅ |
| E0-S04 | Epics og stories | `docs/epics.md` | ✅ |
| E0-S05 | Plan, arbeidsflyt og promptlogg oppdatert | `docs/plan.md`, `docs/prompts/` | ✅ |

---

## E1 — Dashbord v1 på kalibrert baseline (fase 3, 24. okt–6. nov) · `epic/e1-dashbord-v1`

**Mål:** en app sensor kan kjøre og vurdere selv om ingenting annet blir ferdig. **Ferdig når:** klone-testen i E1-S16 er under 20 min og UU-sjekklista er utfylt.

### E1-S01 — Prosjektskjelett ☐
**Krav:** NFR1, NFR2, A1 · **Avhenger av:** —
- `app/__init__.py` med `create_app()`. `flask --app app run` svarer 200 på `/`.
- `requirements.txt` (flask, tzdata, pytest), `.env.example` som i arkitektur §7, og `tests/conftest.py` med app-fixture.
- Appen starter uten `.env`.

**Test:** `tests/test_app.py::test_forside_svarer_200`

### E1-S02 — Datautdrag og lagret baseline ☐
**Krav:** NFR1, A4 · **Avhenger av:** E1-S01
- `scripts/lag_utdrag.py` leser `pipeline/data/bergen_eta_avvik.csv` og skriver `data/utdrag/anlop.csv` (kolonnene i arkitektur §4) og `data/baseline.json`.
- Splitt og offset regnes på samme måte som i `derive_arrivals.py`: 6 260/1 566 rader og 44,8/64,2 min.
- Skriptet er deterministisk: to kjøringer gir identiske filer. Den genererte dataen committes i samme commit.

**Test:** `tests/test_lag_utdrag.py`, som kjører skriptet på `tests/fixtures/` og sjekker kolonner, splitt og offset.

### E1-S03 — Datalag ☐
**Krav:** FR2, FR5 · **Avhenger av:** E1-S02
- `last_utdrag()` gir `Anlop`-objekter med tz-aware UTC-tider. Tider uten suffiks tolkes som UTC.
- `anlop_i_vindu(naa, timer=24, vis="alle"|"passasjer"|"ovrige")` gir anløp med rapportert ETA i [naa, naa + 24 t).
- Anløp med `status_in_area ≠ ok` har `faktisk_ankomst = None`.

**Test:** `tests/test_data.py`, med vindusgrenser (inkludert start, ekskludert slutt), filter og manglende fasit.

### E1-S04 — Prediktor-grensesnitt og kalibrert baseline ☐
**Krav:** FR3, A5 · **Avhenger av:** E1-S03
- `Prediksjon`, `Prediktor` og `velg_prediktor()` som i arkitektur §3.
- `BaselinePrediktor`: `predikert = eta − offset[gruppe]`, `forventet_forsinket = None`, `kan_varsle = False`. `forklaring` inneholder gruppe og offset.
- Kontrakttesten er parametrisert, så E2 kan legge til sin prediktor.

**Test:** `tests/test_prediktor_kontrakt.py`, `tests/test_baseline.py` (BERGEN ENERGY: 11:00 → 09:55 norsk tid)

### E1-S05 — Metrikkmodul og dataregresjon ☐
**Krav:** FR8, NFR3, A6 · **Avhenger av:** E1-S04
- `andel_innenfor(prediksjoner, anlop, minutter=30)` regner bare på anløp med fasit.
- På testsplitten av det ekte utdraget gir baselinen **46,6 %** (øvrige) og **79,6 %** (passasjer), og naiv ETA gir **12,9 %** (øvrige), avrundet til én desimal.

**Test:** `tests/test_metrikker.py` (fixture), `tests/test_dataregresjon.py` (ekte utdrag)

### E1-S06 — Hovedskjerm med anløpsliste ☐
**Krav:** FR2, FR3, UX skjerm A · **Avhenger av:** E1-S05
- `GET /` uten parametre viser vinduet fra 08.10.2025 08:00 norsk tid: 15 anløp, sortert etter predikert ankomst, med kolonnene fra skjerm A.
- Prediktor-stripa viser «Kalibrert baseline» og teksten om at baselinen ikke varsler. Varselkolonnen viser «–».
- Tider vises i norsk tid som «ons 09:55». Horisonten er ≤ 6 t, 6–24 t eller «–» når predikert ankomst ligger før «nå».
- Tomt vindu gir meldingen fra UX §5.

**Test:** `tests/test_ruter.py::test_standardvindu`, `::test_tomt_vindu`, `tests/test_visning.py`

### E1-S07 — Tidsvelger for «nå» med validering ☐
**Krav:** FR1, UU5 · **Avhenger av:** E1-S06
- Skjemaet har dato og klokkeslett med synlige `<label>`, og knappen «Oppdater». Skjemaet sendes ikke automatisk.
- Gyldig `naa` i testperioden gir det vinduet. Ugyldig eller utenforliggende verdi gir status 200, feilmelding med `aria-describedby` og `aria-invalid`, og standardvinduet i lista.

**Test:** `tests/test_ruter.py::test_naa_gyldig`, `::test_naa_utenfor_testperiode`, `::test_naa_ugyldig_format`

### E1-S08 — Filter: alle / passasjer / øvrige ☐
**Krav:** FR5 · **Avhenger av:** E1-S07
- Radiogruppe i `<fieldset>` med `<legend>`. `vis=ovrige` på standardvinduet gir 9 rader.
- Filteret beholdes i URL-en og på tvers av andre valg.

**Test:** `tests/test_ruter.py::test_filter_ovrige`

### E1-S09 — Fasit-bryter ☐
**Krav:** FR4, UU3, UX skjerm A2 · **Avhenger av:** E1-S08
- `fasit=1` legger til kolonnene Faktisk og Avvik. Avvik over 120 min viser ▲ + «FORSINKET» + varselfarge.
- I standardvinduet er BERGEN ENERGY, OCEAN RESPONSE og SIEM PEARL merket FORSINKET.
- Anløp uten AIS viser «Fasit mangler (ingen AIS-data)».
- `fasit=0` (standard) viser ingen fasitdata i HTML-en.

**Test:** `tests/test_ruter.py::test_fasit_av_skjuler`, `::test_fasit_merker_forsinket`, `::test_fasit_mangler`

### E1-S10 — Sortering ☐
**Krav:** FR6, UU7 · **Avhenger av:** E1-S09
- Sorteringsknappene ligger i `<th>`, og aktiv kolonne har `aria-sort`.
- `sorter=avvik` virker bare når `fasit=1`. Ellers faller den tilbake til predikert ankomst uten feil.

**Test:** `tests/test_ruter.py::test_sorter_avvik`, `::test_sorter_avvik_uten_fasit`

### E1-S11 — Detaljside for anløp ☐
**Krav:** FR7, UX skjerm C · **Avhenger av:** E1-S10
- `/anlop/<id>` viser skipsdata, tidspunkter i `<dl>` og forklaringen fra `Prediksjon.forklaring`.
- «Tilbake» beholder `naa`, `vis`, `fasit` og `sorter`. Fasit vises bare hvis `fasit=1`.
- Ukjent ID gir 404 med lenke tilbake.

**Test:** `tests/test_ruter.py::test_detalj`, `::test_detalj_404`, `::test_detalj_tilbakelenke`

### E1-S12 — Treffsikkerhetspanel og metodeside ☐
**Krav:** FR8 · **Avhenger av:** E1-S11
- Panelet viser de tre tallene fra E1-S05, regnet med `metrikker.py` (ikke hardkodet), merket «hele testperioden».
- Søylene har tekstverdi, så de ikke bare er grafikk. `/metode` forklarer baseline, ±30 min og testperioden og lenker til beslutning 04/05.

**Test:** `tests/test_ruter.py::test_panel_tall`, `::test_metode`

### E1-S13 — Visuelt design og kontrast ☐
**Krav:** UU1, UX §7 · **Avhenger av:** E1-S06
- `static/style.css` har tokenene fra UX §7, lyst og mørkt tema (`prefers-color-scheme`), fokusring og `tabular-nums`.
- Alle tokenpar i UX §7 har kontrast ≥ 4,5:1 (tekst) og ≥ 3:1 (`--kant`).

**Test:** `tests/test_kontrast.py`, som leser tokenene fra CSS-fila.

### E1-S14 — Responsiv layout ☐
**Krav:** UU6, UX skjerm B · **Avhenger av:** E1-S13
- Under 640 px vises tabellradene som kort med `data-label`, og skjemaet ligger i `<details>`. Ingen horisontal rulling på 360 px eller ved 200 % zoom.

**Test:** manuell, med punkt UU6 i UX §6. `tests/test_uu_struktur.py::test_viewport_og_data_label`

### E1-S15 — UU-gjennomgang ☐
**Krav:** UU2–UU7 · **Avhenger av:** E1-S14
- Hopp-lenke, landemerker, `lang="nb"`, én `h1`, `th scope` og alt-tekst er på plass.
- Den manuelle sjekklista i UX §6 er gjennomført og utfylt med dato og resultat. Funn rettes i denne storyen eller føres opp som nye stories.

**Test:** `tests/test_uu_struktur.py` + utfylt sjekkliste

### E1-S16 — README og klone-test ☐
**Krav:** NFR1 · **Avhenger av:** E1-S15
- README har en «Kom i gang»-seksjon: krav (Python ≥ 3.9), venv, `pip install -r requirements.txt`, `flask --app app run`, `pytest`, og hva man bør se (standardvinduet, 46,6 %).
- Et gruppemedlem som ikke bygde E1 kloner repoet på nytt og følger bare README. Tiden logges i README (mål: < 20 min), og alt som var uklart rettes.

**Test:** klone-test med loggført tid

### E1-S17 — Skjermbilder mot skisse ☐
**Krav:** kriterium 4 · **Avhenger av:** E1-S16
- `docs/ux/skjermbilder/` har skjerm A, A2, B og C fra den kjørende appen (1280 px og 360 px). UX-dokumentet får en seksjon om hva som ble annerledes enn skissen, og hvorfor.

**Test:** manuell. Filene finnes og avvikene er beskrevet.

---

## E2 — Modell bak dashbordet (fase 4, 7.–27. nov) · `epic/e2-modell`

**Mål:** en modell som slår den kalibrerte baselinen, synlig i det samme dashbordet. Klarer den det ikke, skal det vises ærlig. **Ferdig når:** dashbordet viser modellen som standard, og resultatnotatet er skrevet.

### E2-S01 — Featureliste og horisont (beslutning 08) ☐
**Krav:** PRD §7 · **Avhenger av:** E1-S05
- `docs/beslutninger/08-features-og-horisont.md` avgjør tre ting:
  - hvilke features som brukes, og for hver av dem hvorfor den er kjent ved prediksjonstidspunktet
  - hva som skiller 6 t- fra 24 t-prediksjonen når datasettet har én rapportert ETA per seilas
  - om det skal være separate modeller for passasjer og øvrige
- Avvik fra stories E2-S02–S09 som følger av beslutningen, oppdateres her.

**Test:** beslutningen finnes og er gjennomgått av hele gruppa (godkjent i PR).

### E2-S02 — Feature-bygging uten lekkasje ☐
**Krav:** NFR3 · **Avhenger av:** E2-S01
- `app/prediksjon/features.py` bygger features for ett anløp gitt `naa`. Historikkfeatures (for eksempel fartøyets tidligere avvik) bruker bare treningsrader med ETA før `naa`.

**Test:** `tests/test_features.py::test_ingen_lekkasje`. Når en fremtidig rad endres, endres ikke featuren.

### E2-S03 — Treningsskript og første modell ☐
**Krav:** FR9, A7 · **Avhenger av:** E2-S02
- `scripts/tren.py` trener på `split=train` med fast seed og lagrer `data/modell/modell_6t.joblib`. scikit-learn legges i `requirements.txt`.

**Test:** `tests/test_tren.py`. Skriptet kjører på fixturen og gir samme prediksjon to ganger.

### E2-S04 — 24 t-horisont ☐
**Krav:** FR9 · **Avhenger av:** E2-S03
- `modell_24t.joblib` (eller den løsningen beslutning 08 har valgt) lagres. Dashbordet velger modell etter horisont-bøtta.

**Test:** `tests/test_tren.py::test_24t`

### E2-S05 — Evalueringsskript ☐
**Krav:** FR10, NFR3, A6 · **Avhenger av:** E2-S04
- `scripts/evaluer.py` bruker `app/metrikker.py` og skriver `data/modell/metrikker.json`: andel innenfor ±30 min, presisjon og recall på forsinket, MAE og median (som støttetall) per gruppe og horisont, for både modell og baseline.

**Test:** `tests/test_evaluer.py`. Baseline-tallene i `metrikker.json` er lik dataregresjonen fra E1-S05.

### E2-S06 — ModellPrediktor ☐
**Krav:** FR9, A5 · **Avhenger av:** E2-S05
- Implementerer kontrakten, `kan_varsle = True`. `forklaring` inneholder de faktiske featureverdiene.

**Test:** legges til i `tests/test_prediktor_kontrakt.py`

### E2-S07 — Bytt inn i dashbordet ☐
**Krav:** FR3, FR9, UX §5 · **Avhenger av:** E2-S06
- `PREDIKTOR=auto` velger modellen når artefaktet finnes. Prediktor-stripa viser «Modell v1», og varselkolonnen viser ▲ + «VARSEL».
- Mangler artefaktet, faller appen tilbake til baseline med melding.
- *Ingen endring i malene utover stripa og varselkolonnen.* Det er testen på at A5 holdt.

**Test:** `tests/test_ruter.py::test_modell_standard`, `::test_fallback_baseline`

### E2-S08 — Panel: modell mot baseline ☐
**Krav:** FR10 · **Avhenger av:** E2-S07
- Panelet viser modell og baseline side om side, pluss presisjon/recall, lest fra `metrikker.json`. Taper modellen, vises det med samme tydelighet.

**Test:** `tests/test_ruter.py::test_panel_modell_mot_baseline`

### E2-S09 — Resultatnotat ☐
**Krav:** brief Success Criteria · **Avhenger av:** E2-S08
- `docs/resultater.md` gjør rede for modell og baseline på testsplitten, begrensningene (vintervridd test, AIS-hull), og om målene ble nådd. Et negativt resultat rapporteres. README nevner modellen.

**Test:** tallene i notatet er lik `metrikker.json` (sjekkes i PR)

---

## E3 — Generativt AI-lag med testmodus (fase 5, 28. nov–5. des) · `epic/e3-ai-lag`

**Mål:** begrunnelser sensor kan se uten nøkkel. **Ferdig når:** appen kjører med `LLM_MODUS=test` uten nett, og ekte modus er vist og logget minst én gang.

### E3-S01 — Adapter og testmodus ☐
**Krav:** FR13, A8, NFR6 · **Avhenger av:** E2-S06 (eller E1-S04 hvis E2 glipper)
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
- Skjerm C viser begrunnelsen merket «KI-GENERERT» (eller «Testmodus»).

**Test:** `tests/test_ruter.py::test_detalj_begrunnelse`

### E3-S05 — Forstyrrelsesbrief på hovedskjermen ☐
**Krav:** FR12 · **Avhenger av:** E3-S04
- 3–5 setninger øverst på skjerm A, som nevner anløpene med varsel i vinduet.

**Test:** `tests/test_ruter.py::test_brief_nevner_varslede`

### E3-S06 — Opptak av ekte svar for demodager ☐
**Krav:** FR13 · **Avhenger av:** E3-S05
- `scripts/ta_opp_begrunnelser.py` kjører ekte modus for 2–3 demovinduer og lagrer svarene i `data/begrunnelser_opptak.json`. Testmodus viser opptaket når det finnes, så sensor ser ekte output uten nøkkel.

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
| FR3 | E1-S04, E1-S06, E2-S07 |
| FR4 | E1-S09 |
| FR5 | E1-S03, E1-S08 |
| FR6 | E1-S10 |
| FR7 | E1-S11 |
| FR8 | E1-S05, E1-S12 |
| FR9 | E2-S03, E2-S04, E2-S06, E2-S07 |
| FR10 | E2-S05, E2-S08 |
| FR11 | E3-S02, E3-S03, E3-S04 |
| FR12 | E3-S05 |
| FR13 | E3-S01, E3-S06 |
| FR14 | E3-S08 |
| UU1 | E1-S13 |
| UU2–UU7 | E1-S07, E1-S08, E1-S10, E1-S14, E1-S15 |
| NFR1 | E1-S01, E1-S02, E1-S16, E3-S07 |
| NFR2 | alle (test per story) |
| NFR3 | E1-S05, E2-S02, E2-S05 |
| NFR4 | arbeidsreglene øverst |

## Endringslogg

- **2026-10-16** — Første versjon (E0-S04): E0 ferdig, og E1 (17 stories), E2 (9) og E3 (8) planlagt.
