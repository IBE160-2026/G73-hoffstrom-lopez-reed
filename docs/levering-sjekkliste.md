# Sjekkliste før levering 15.12.2026

Laget 24.11.2026 (E0-S23) fra `main` (`3fbe4cd`), med PR #13 og PR #14 åpne. Sjekklista er vår egen oppsummering av hva sensorveiledningen for del 1 og rapportmalen ber om, og den kopierer ikke kursmaterialet (det ligger lokalt, se `.gitignore` og E0-S09). Den bygger videre på [`vurderingskriterier.md`](vurderingskriterier.md), som er skrevet tidligere i prosjektet.

**Status:** ✅ ferdig · ◐ delvis · ☐ mangler. Status er satt ut fra det som ligger i repoet 24.11, ikke ut fra det som er planlagt.

## 1. Del 1 — app og prosess (70 %)

Sensor kloner repoet ved fristen, følger README, kjører appen og testene, leser historikken og prosessdokumentene og stikkprøver koden. Vektene i parentes.

### 1.1 Prosess og KI-styring (30 %)

| Krav (med egne ord) | Status | Hvor i repoet |
|---|---|---|
| Planleggingsdokumenter som faktisk er brukt og oppdatert, ikke bare generert én gang | ✅ | `docs/brief.md`, `docs/prd.md`, `docs/arkitektur.md`, `docs/epics.md`, `docs/ux/dashbord.md`. Alle har endringslogg med datoer helt fram til 24.11. |
| Kode kan spores til krav og stories, og avvik fra planen er forklart | ✅ | Commit-meldingene starter med story-ID. Specene ligger i `_bmad-output/implementation-artifacts/`, og avvikene står i endringsloggene og i spec-valgene (for eksempel O1 i E3-S06). |
| Jevn historikk med små commits og beskrivende meldinger | ◐ | 223 commits på `main`: 11 i september, 49 i oktober og 163 i november. Det er tyngst i november. Unngå én stor commit rett før fristen. |
| Arbeidsflyt med greiner, PR-er og issues | ◐ | 14 PR-er og én gren per epic eller story. **Ingen PR har en godkjent review (Approve)**, og PR #5, #11 og #12 ble merget uten review. GitHub Issues er ikke brukt, men åpne punkter står i `.logs/*/issues.md`. |
| Sporbar KI-bruk: lagrede prompts og økter, og eksempler på at vi rettet eller avviste KI | ✅ | `docs/prompts/` (fram til 27.10), `.logs/` (28 filer), `docs/refleksjon/notater.md` (38 daterte KI-feil med commits), og triage-loggene i specene. |
| Begrunnede beslutninger om teknologi og arkitektur | ✅ | `docs/beslutninger/` (13 beslutninger), og A1–A8 i arkitekturen. |
| Historikken viser at hele gruppa har jobbet over tid | ◐ | `git shortlog`: Theodor 144, Felipe 70 og Thomas 1. Ujevn fordeling er ikke grunnlag for trekk i seg selv, men Thomas' bidrag (UU-sjekk, merge av PR #11) bør synes i loggene og i rapporten. |

### 1.2 Funksjonalitet og omfang (20 %)

| Krav | Status | Hvor |
|---|---|---|
| Kjerneflytene fra brief og README virker fra start til slutt | ✅ | Skjerm A (liste, panel og brief) og skjerm C (detalj og begrunnelse). Produksjon: <https://g73-hoffstrom-lopez-reed.vercel.app>. |
| Omfanget står i forhold til ambisjonen: modell, integrasjon og ikke-trivielle regler | ✅ | Modell v1 (E2), AI-laget via OpenRouter (E3), lekkasjevern (FR9a) og testperiodelås. |
| Stabil ved feil input og gjentatt bruk | ◐ | Ukjent seilas gir 404, og AI-laget gir aldri 500 (FR11a). Det finnes ingen tidsvelger (E1-S07), så ingen input å validere ennå. |
| Det som er utelatt eller endret, er beskrevet og begrunnet | ◐ | MÅ/KAN er avgrenset i `epics.md`, men 10 KAN-stories i E1 står som ☐ (S07–S15, S17). Noe av S11 og S12 er levert gjennom E3-S04 og E2-S09, men story-statusen sier det ikke. Det bør ryddes opp i før levering (se 2.3). |

### 1.3 Kvalitetssikring og testing (15 %)

| Krav | Status | Hvor |
|---|---|---|
| Automatiske tester som kjøres slik README sier, og som tester meningsfull logikk | ✅ | `pytest`: 812 på `main` og 841 med PR #14. Dataregresjon, lekkasje, kontrakt, ruter, UU-struktur, kontrast og AI-laget med falsk transport, og JS i Node. |
| Dokumenterte manuelle tester der automatiske ikke passer | ◐ | UU-sjekklista i UX §6. Lesersjekken av briefen (FR12) er ☐. |
| Spor av kodegjennomgang og retting av KI-kode | ◐ | Triage-loggene i specene (tre reviewer-lag), mutasjonssjekker og `notater.md`. **Ingen review-kommentarer fra gruppa på GitHub.** |
| Feilhåndtering, inputvalidering og ingen hemmeligheter i kode | ✅ | Tilbakefall i AI-laget, kontrollen av LLM-svar, nøkkelen bare i miljøet, og `.env` er aldri committet (sjekket med `git log --all -- .env`). |

### 1.4 Design og brukeropplevelse (10 %)

| Krav | Status | Hvor |
|---|---|---|
| Helhetlig visuelt uttrykk | ◐ | Fargetokener i UX §7 og `style.css`. Mørkt tema (E1-S13) er ikke bygd. |
| Tydelig navigasjon, tilbakemeldinger og tomtilstander | ✅ | UX §5 (tilstandstabellen), merkene i AI-laget og «Henter …» i `aria-live`. |
| Grunnleggende UU: kontrast, tastatur, alt-tekst og etiketter | ✅ | `test_kontrast.py`, `test_uu_struktur.py`, og manuelle sjekker 03.11, 19.11 og 23.11 (UX §6). |
| Tilpasset skjermstørrelser | ✅ | Kort under 640 px, og målt ved 360, 640, 1280 og 1920 px (UX §6, UU6). |
| Spor av designarbeid | ✅ | ASCII-skisser i UX §2–§4 og skjermbilder i `docs/ux/skjermbilder/`. Skjermbilder mot skisse for alle skjermer (E1-S17) er ☐. |

### 1.5 Kodekvalitet og arkitektur (10 %)

| Krav | Status | Hvor |
|---|---|---|
| Mappestrukturen følger arkitekturen | ✅ | Arkitektur §10 mot `app/`, `scripts/`, `tests/` og `pipeline/`. |
| Lesbar kode, lite død kode og lite duplisering | ◐ | Ikke gjennomgått samlet. Review-funn er avvist som kosmetiske flere steder (for eksempel E3-S05 #17). Én opprydningsrunde før levering. |
| Konsekvent stil, gjerne med linter eller formatterer | ☐ | Ingen linter- eller formatter-konfigurasjon i repoet (ingen `ruff`, `pyproject.toml` eller `pre-commit`). |
| Konfigurasjon og avhengigheter håndteres fornuftig | ✅ | `requirements.txt`, `.env.example`, all LLM-konfigurasjon i `konfig.py`, og `vercel.json`. |

### 1.6 README og kjørbarhet (10 %)

| Krav | Status | Hvor |
|---|---|---|
| Hva appen gjør og for hvem, med skjermbilde | ✅ | README «Om prosjektet» og skjermbilde av hovedskjermen. |
| Forutsetninger med versjon | ✅ | Python 3.9 eller nyere, og git. |
| Steg-for-steg-kommandoer som kan kopieres | ✅ | «Kom i gang». Klone-testen 03.11 tok ca. 4 min. |
| Miljøvariabler med eksempelfil | ◐ | `.env.example` finnes, men README forklarer ikke AI-laget, `LLM_MODUS`, testmodus mot ekte modus eller demovinduet. Det er **E3-S07**. |
| Hvordan testene kjøres | ✅ | `pytest` og regresjonstesten. |
| Oversikt over mappestrukturen og lenker til prosessdokumentene | ◐ | Lenker til brief, addendum og beslutninger finnes. Lenker til PRD, arkitektur, epics, UX, `.logs/` og `notater.md`, og en kort mappeoversikt, mangler. |
| README stemmer med koden | ◐ | Bra for E1 og E2. AI-laget (E3) mangler, og klone-testen må kjøres på nytt (E3-S07). Medlemslista sier «Theodor Gimming Hoffstrøm», mens rapporten og loggene sier «Theodor Gimming». Velg én form. |

### 1.7 Ryddighet i repoet (5 %)

| Krav | Status | Hvor |
|---|---|---|
| Tydelig skille mellom kode og dokumentasjon | ✅ | `app/`, `docs/`, `tests/`, `scripts/` og `pipeline/`. |
| `.gitignore` holder ute miljø, cache og byggefiler | ✅ | `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env` og `pipeline/data/`. |
| Ingen hemmeligheter i repoet eller historikken | ✅ | Sjekket 24.11. Bør sjekkes en gang til rett før fristen. |
| Ingen løse filer i rotmappen | ✅ | Roten har bare filer som brukes (`wsgi.py`, `vercel.json`, `pytest.ini`, `CLAUDE.md`). `.gitignore` har et Next.js-avsnitt fra malen som ikke brukes. Det er ufarlig, men kan ryddes. |

### Varseltegn sensor ser etter, og hvordan vi står

- **Mye kode rett før fristen:** risiko hvis E3-S07, opprydding og rapport kommer i én stor commit 14.–15.12. Lever i små PR-er.
- **Planer som ikke stemmer med appen:** 10 KAN-stories står som ☐, og deler av S11 og S12 er faktisk levert. Det må ryddes i `epics.md`.
- **README-kommandoer som ikke virker:** klone-testen må gjentas med AI-laget (E3-S07).
- **Generell KI-dokumentasjon:** lav risiko, fordi `notater.md` og specene knytter feilene til commits.

## 2. Det som gjenstår i E3

| # | Hva | Avhenger av | Status |
|---|---|---|---|
| 1 | **PR #13** (logg og notat etter PR #12) får Approve og merges | Felipe eller Thomas | ☐ |
| 2 | **PR #14** (E3-S06) får Approve, og gruppa godtar PRD-endringen (FR13, bare 08.10) | Felipe eller Thomas | ☐ |
| 3 | **Felipe bekrefter** at opptaket kan bruke testradene for 08.10 bare til visning (spec-valg O3) | Felipe | ☐ |
| 4 | **Opptaket:** `scripts/ta_opp_begrunnelser.py --kjor` (høyst 16 kall), commit `data/begrunnelser_opptak.json`, kostnad i beslutning 13, og sjekk av merket i forhåndsvisningen | 2 og 3 | ☐ |
| 5 | **E3-S07:** README for AI-laget (testmodus som standard, ekte modus med `.env`, demovinduet) og ny klone-test, kjørt av en annen enn den som skrev README | 4 | ☐ |
| 6 | **FR12, lesersjekken:** en person utenfor gruppa leser briefen for standardvinduet. Resultatet føres i UX §6 | Kan gjøres når som helst, helst etter 4 | ☐ |
| 7 | **Lukking av E3:** kostnadsoverslaget i beslutning 13 sjekkes mot OpenRouters priser, og det avgjøres om Preview skal tilbake til `LLM_MODUS=test` | 5 | ☐ |
| 8 | **Kommentarer på PR #11 og PR #12:** Thomas og Felipe skriver hva de sjekket før merge (begge ble merget uten review) | — | ☐ |
| 9 | E3-S08 Kart (valgfri): bare hvis 1–7 er ferdige før 3.12. Foreslås droppet | — | foreslått droppet |

**Merk:** PR #13 og PR #14 legger begge til linjer nederst i `.logs/theodor-gimming/issues.md`. Den som merger sist, må løse en liten konflikt. Denne PR-en rører ikke `issues.md`.

## 3. Refleksjonsrapporten (30 %)

`docs/refleksjon/rapport.md` følger kursmalen. I dag har den ca. 1 700 ord, og nesten alt er de to utkastene i 3.1. Målet i malen er 3 000–5 000 ord.

### Hva agenten kan hjelpe med

Agenten kan lage **utkast bygd bare på det som står i repoet**, med commits og datoer. Hvert utkast merkes som utkast, og gruppa skriver det om med egne ord, slik det allerede står øverst i rapporten.

- **2.1–2.4 Oversikt, metodikk, teknologi og faser:** faktagrunnlag fra brief, PRD, arkitektur, plan, PR-lista og `.logs/`.
- **3.1 Tekniske utfordringer:** utkastene finnes. Agenten kan foreslå en tredje utfordring, AI-laget (prompt v1–v8, kontrollen og røykkallene), fra beslutning 13 og loggene.
- **3.3 KI-spesifikke utfordringer og 4.2 Begrensninger:** et utvalg av de 38 KI-feilene i `notater.md`, gruppert etter type.
- **4.1 Fordeler:** konkrete eksempler (review-lagene, mutasjonssjekkene, tempoet i E3).
- **5.5 Datasikkerhet og personvern:** hva som ble sendt til OpenRouter (ingen fasit, MMSI eller seilas-ID) og hvordan nøkkelen ble håndtert.
- **6.1–6.2:** eksempler fra specene og triage-loggene.
- **8. Vedlegg:** skjermbilder, repolenke og lenker til dokumentene.
- **Sjekk av rapporten mot repoet:** at tall, datoer og commits i rapporten stemmer.

### Hva hver av oss må skrive selv

- **Student-ID eller e-post** for alle tre i kapittel 1, og **datoen**.
- **7.4 Personlig refleksjon:** hver skriver sin egen, uten agent. Råstoff: egne notater, egne økter i `.logs/<navn>/` og planen for refleksjonsrundene i `docs/plan.md`.
- **Omskrivingen av utkastene i 3.1** og alle andre KI-utkast, med egne ord.
- **Vurderingene og meningene:** 3.2 (samarbeid), 4.3–4.4 (med og uten KI, og samlet vurdering), 5.1–5.4 (ansvar, transparens, læring og arbeidsmarked), 6.3 og 7.1–7.3. Agenten kan liste fakta, men kan ikke mene noe på våre vegne.
- **Ordantallet** til slutt.

## 4. Forslag til fordeling og datoer

Det er et forslag, og gruppa avgjør. Plan.md har E3 fram til 5.12 og polering og levering 6.–15.12.

| Dato | Theodor | Felipe | Thomas |
|---|---|---|---|
| **25.–27.11** | Klargjør S07-utkastet (README). Ber agenten om faktautkast til 2.1–2.4 | Bekrefter O3 (punkt 3). Reviewer og godkjenner PR #13 og #14 | Kommenterer PR #11. Reviewer PR #14 hvis Felipe ikke rekker det |
| **28.11–1.12** | Kjører opptaket (punkt 4). E3-S07 i PR | Kommenterer PR #12. Skriver 3.1 utfordring 2 om med egne ord (modell og statistikk) | Kjører klone-testen for E3-S07 og fører tiden i README |
| **2.–5.12** | Lukker E3 (punkt 7). Rydder i `epics.md` (KAN-status, levert i S11 og S12) | Skriver 3.1 utfordring 1 om med egne ord | Finner en leser utenfor gruppa til FR12 (punkt 6). Skriver 3.2 |
| **6.–10.12** | README-lenker og mappeoversikt. Opprydding i koden (død kode, kanskje `ruff`) | 4.1–4.4 og 6.1–6.3 sammen med de andre | 5.1–5.5 sammen med de andre |
| **11.–12.12** | 7.4 egen refleksjon | 7.4 egen refleksjon | 7.4 egen refleksjon |
| **13.12** | Hele gruppa: les rapporten samlet, fyll inn student-ID og dato, tell ord, og skriv 7.1–7.3 sammen | ← | ← |
| **14.12** | Siste klone-test mot `main`, sjekk for hemmeligheter, og alle PR-er merget med Approve | Reviewer de siste PR-ene | Reviewer de siste PR-ene |
| **15.12** | **Levering.** Ingen nye commits etter fristen (sensor ser bort fra dem) | ← | ← |

Hvert punkt leveres i en egen liten PR med Approve fra en annen i gruppa, så historikken viser jevn innsats og ekte review fram til fristen.
