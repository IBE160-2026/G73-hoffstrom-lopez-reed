# E3-S01–S04: begrunnelse via OpenRouter

## 2026-11-18 kl. 14:59 — Theodor Gimming

### Oppgave
Implementere specen for E3-S01–S04 (begrunnelse per anløp via OpenRouter, uten å vente på språkmodellen), med specen som eneste sannhetskilde. Én commit per story.

### Plan
- Spec: [`spec-e3-s01-s04-begrunnelse-via-openrouter.md`](../../_bmad-output/implementation-artifacts/spec-e3-s01-s04-begrunnelse-via-openrouter.md), kontekst: `epic-3-context.md` og `docs/ux/dashbord.md`.
- S01 adapter/konfig/testmodus + vakter i conftest + PRD FR11b, S02 `lag_fakta`, S03 klient/prompt/kontroll + beslutning 13 og arkitektur, S04 skjerm C + JSON-endepunkt + UX §6.

### Resultat
- `c19c67e` E3-S01: `app/begrunnelse/{konfig,testmodus,__init__}.py`. Cache per (voyageid, prediktor): et godkjent svar beholdes så lenge prosessen lever, en feil i 300 s. Kallgrense på 20 forsøk per prosess, under en lås. Autouse-vakt i `tests/conftest.py` (ingen nøkkel, testmodus, socketer sperret, tom cache). FR11b i PRD er endret (S5–S6).
- `1398aca` E3-S02: `input.py` (`lag_fakta`). Bare `PrediksjonsInput` + `Prediksjon`, ingen MMSI, seilas-ID eller fasit.
- `84c0d41` E3-S03: `openrouter_klient.py` (urllib, transporten kan byttes ut, `max_tokens` 300, årsakskoder), `prompt.md` (`begrunnelse-v1`) og `kontroll.py`. Nye `docs/beslutninger/13-openrouter-og-modell.md`. Rettet: A8, §5, §7, §9 og §11 i arkitekturen, og `.env.example` (Anthropic er fjernet). Leverandørspørsmålet i PRD §8 er lukket.
- `64e5831` E3-S04: `GET /anlop/<id>` (skjerm C, 404 for ukjent seilas) og `POST /anlop/<id>/begrunnelse` (alltid 200 med `{tekst, merke}`). Også `aria-live`, `<noscript>`, `begrunnelse.js`, skipsnavnet som lenke på skjerm A og UX §4–§6.
- Suiten: 575 passed (ca. 30 s), uten nett. `grep deepseek|openrouter.ai app/` gir bare `konfig.py` og URL-konstanten i klienten.
- Mutasjonssjekk: 14 av 14 mutanter ble fanget (kallgrense 19/21 og `>`, TTL 299/301 og `>`, et godkjent svar som utløper, 400/401 tegn, 3/4 setninger, max_tokens, GET som kaller språkmodellen), og en kontrollkjøring uten endring overlever. Feil fra KI fanget underveis: første kjøring av mutasjonene ga gamle `.pyc` (`sys.pycache_prefix` er satt, og mtime ble lik innenfor samme sekund). Kjørt på nytt med `PYTHONDONTWRITEBYTECODE=1` og tømt cache.
- Ingen ekte kall er gjort, og `.env` er ikke lest.

### Åpne punkter
- Røykkall i ekte modus på skjerm C, bare når Theodor ber om det. Prompt og svar logges her, uten nøkkelen (E3-S03).
- Manuell UU-sjekk av skjerm C (tastatur, aria-live med VoiceOver, uten JS), som står med ☐ i UX §6.
- Kostnadsoverslaget i beslutning 13 sjekkes mot OpenRouters priser før levering.
- PR for `epic/e3-ai-lag` merges ikke før gruppa har sett den og forhåndsvisningen på Vercel.

## 2026-11-18 kl. 15:09 — Theodor Gimming (review og mutasjonssjekk)

### Oppgave
Fullføre bmad-build-flyten for E3-S01–S04: kontrollere implementeringen mot diffen, kjøre review med tre lag, rette funnene, mutasjonssjekke grensene og åpne PR. Ikke merge før gruppa har sett PR-en og forhåndsvisningen, og ikke gjøre røykkallet før Theodor ber om det.

### Plan
- Kontrollere oppgavene og matrisen mot diffen fra `cfb4609`.
- Review med tre lag (blind-hunter, edge-case-hunter og verification-gap), triage i specen og rettinger gjennom implementeringsagenten.
- Mutasjonssjekk med `PYTHONDONTWRITEBYTECODE=1`, så PR mot `main`.

### Resultat
- Hver rad i matrisen har en test som kjører. Modellnavnet står bare i `konfig.py`.
- **Review:** 26 funn. 13 er rettet, 2 er utsatt (`deferred-work.md`: JS-en er bare sjekket som kildetekst, og `reasoning`-parameteren er ukjent til røykkallet), og 11 er forkastet med begrunnelse. Alt står i Review Triage Log i specen.
  - Viktigst: tallkontrollen så ikke fortegn («+12» ble godtatt mot «−12»), og tallene i etikettene var tillatt.
  - Også rettet: «−0», `inf` i konfigurasjonen, etterfølgende nuller, en myk bindestrek som ikke synes i kildekoden, testhull for varselgrenene og fortegnet på skjerm C, tidsmåling uten oppvarming, og epic-konteksten og testreferansene i `docs/epics.md`.
- **Rettingene er committet per story:** `f7f265d` (S01), `49bab53` (S02), `f530965` (S03), `3a642e1` (S04) og `e8f20b6` (specen er ferdig).
- **Mutasjonssjekk (Claude, etter reviewen):** alle 14 mutanter ble fanget, og kontrollkjøringen var grønn. Mutantene var kallgrensen satt til 19 og 21 og `>=` byttet til `>`, cache-tiden satt til 299 og 301 og `>=` byttet til `>`, et godkjent svar som utløper, 401 og 399 tegn og `>` byttet til `>=`, 4 og 2 setninger, fortegnskontrollen fjernet, og tall i etikettene tillatt igjen.
- **Suiten:** 584 passed, uten nett.
- **KI-feil** er ført i `docs/refleksjon/notater.md` (`1d9c48e`): de gamle `.pyc`-filene i mutasjonssjekken, tallkontrollen uten fortegn, og «han» om Theodor.
- Ingen ekte kall er gjort, og verdien i `.env` er ikke lest.

### Åpne punkter
- Overskriften «Hvorfor avvik er ventet» står også over baselinerader og rader uten varsel (review-funn 26). Den kommer fra UX §4 og S1, så Theodor og gruppa må avgjøre om den skal endres.
- Kontrollen fanger ikke retningsord («senere», «tidligere») eller tall skrevet med ord. Det må følges med på i røykkallet.

## 2026-11-18 kl. 15:41 — Theodor Gimming (røykkall og rettinger)

### Oppgave
Gjøre røykkallet lokalt med nøkkelen i `.env` og `LLM_MODUS=ekte` bare for kjøringen: høyst 3 kall, ett av hver (modell med varsel, modell uten varsel, baseline). Deretter skulle overskriften på skjerm C bare si «Hvorfor avvik er ventet» ved varsel, kontrollen skulle sjekke retningsord og tall skrevet med ord, og token-grensen skulle justeres om nødvendig. Push, men ikke merge.

### Plan
- Et skript i scratchpad la nøkkelen inn i miljøet til prosessen uten å skrive den ut, satte `LLM_MAKS_KALL=3`, og tok vare på `usage` gjennom en transport som pakket inn den ekte klienten (`usage.include`).
- Modellradene ble hentet fra valideringsvinduet 15.08.2025 08:00, som i testene, så testperioden ikke ble brukt.

### Resultat
**Røykkallet** (3 kall, Wafer, HTTP 200, prompt `begrunnelse-v1`):

| Tilfelle | Skip | Input-tokens | Output (resonnering) | Kostnad (USD) | Kuttet | Tekst | Kontroll |
|---|---|---|---|---|---|---|---|
| Modell med varsel (+138 min) | BERGEN ENERGY | 689 | 300 (300) | 0,000175 | ja (`length`) | ingen (null) | `tom`, vist som `avkortet` |
| Modell uten varsel (−10 min) | ISLAND CLIPPER | 690 (256 fra cache) | 300 (300) | 0,000168 | ja | ingen | `tom`, vist som `avkortet` |
| Baseline | NORMAND SIGMA | 494 (256 fra cache) | 300 (300) | 0,000161 | ja | ingen | `tom`, vist som `avkortet` |

Til sammen kostet det USD 0,000504. Alle tre viste «Testmodus (ekte kall feilet)». Nøkkelen ble ikke skrevet ut, og skriptet stoppet hvis den havnet i utskriften. Fakta for kallet med varsel (BERGEN ENERGY): Tank, ETA fre 15.08 16:30, predikert fre 15.08 17:44, horisont 6–24 t, avvik 138 min, varsel ja, 221 km, 6,7 kn, slakk 6,2 t, historisk snittavvik 131 min over 183 anløp.

**Årsak:** modellen resonnerer som standard med innsats `high` (OpenRouters modelliste: `default_effort` er high og `mandatory` er false, og `none` er støttet). Resonneringen teller mot `max_tokens`.

**Rettinger** (`5b2f820` E3-S03 og `2351d45` E3-S04):
- Klienten sender `reasoning: {"effort": "none"}` (`LLM_RESONNERING`, standard `none`). `max_tokens` er beholdt på 300: grensen var ikke for lav for svaret, den ble brukt opp av resonneringen.
- Kontrollen avviser tall skrevet med ord (`tallord`) og retningsord som ikke stemmer med fortegnet på avviket (`retning`):
  - modell: fortegnet på `predikert_avvik_min`
  - baseline og delegerte rader: alltid tidligere enn rapportert ETA
  - «tidligere anløp» er unntatt
- Prompten er nå `begrunnelse-v2`.
- Overskriften er «Hvorfor avvik er ventet» bare ved varsel, ellers «Om prediksjonen», og UX §4 er oppdatert.
- Beslutning 13 har fått de målte tallene, og `notater.md` har fått en oppføring.

**Kontroll:** suiten er grønn med 615 tester. Mutasjonssjekken av de nye reglene fanget 14 av 14 mutanter, og kontrollkjøringen var grønn. Mutantene: tallregelen fjernet, «to» fjernet, «halv» fjernet, retningsregelen fjernet, retning 0 som slipper gjennom senere eller tidligere, listene byttet om, unntaket for «tidligere anløp» fjernet, baselinen med feil fortegn, adapteren uten retning, resonnering satt til high eller ikke sendt, og overskriften i to varianter.

### Åpne punkter
- Rettingen (`reasoning.effort = none`) er ikke prøvd mot et ekte kall. Det trengs ett nytt røykkall når Theodor godkjenner det.
- `LLM_MODUS=ekte` i Vercel venter til det røykkallet har gitt tekst.

## 2026-11-18 kl. 15:46 — Theodor Gimming (røykkall 2 og fortegnet på forskyvningen)

### Oppgave
Rette kontrollen, så retningen for baselinen følger det faktiske fortegnet på forskyvningen for skipsgruppen. Føre «en»/«ett» som kjent begrensning i specen. Kjøre røykkallet på nytt med de samme 3 tilfellene, lokalt og med `LLM_MODUS=ekte` bare for kjøringen. Ingenting skulle settes i Vercel. Push, men ikke merge.

### Plan
- Sjekke fortegnene i `data/baseline.json`, rette `retning()`, legge til tester og mutanter, og committe.
- Kjøre samme røykskript som sist (scratchpad, 3 kall, `usage.include`).

### Resultat
- **Forskyvningene i dag:** Passasjer 44,75 og Øvrige 64,2 min. Begge er positive.
- **`35725ed` (E3-S03):** `retning()` bruker `−offset_minutter` for baselinen og delegerte rader. Uten offset faller den tilbake til tidene. Prompten er `begrunnelse-v3`, uten «alltid tidligere».
  - Nye tester: negativ forskyvning, forskyvning 0, og `test_dagens_forskyvninger_er_positive` (blir rød hvis `baseline.json` endres).
  - Begge mutantene ble fanget («antar alltid tidligere» og snudd fortegn). Suiten er grønn med 621 tester.
  - Specen har fått den kjente begrensningen med «en», «ett» og «én».
- **Røykkall 2** (3 kall, Wafer, `reasoning.effort = none`, ingen resonneringstokens, `finish_reason` = `stop` for alle):

| Tilfelle | Godtatt? | Tegn | Input / output | Kostnad (USD) |
|---|---|---|---|---|
| Modell med varsel, BERGEN ENERGY (+138) | ja, KI-GENERERT | 400 | 787 / 143 | 0,0000998 |
| Modell uten varsel, ISLAND CLIPPER (−10) | nei, `kontroll_lengde`, vist som «Testmodus (ekte kall feilet)» | 402 | 788 / 148 | 0,0000924 |
| Baseline, NORMAND SIGMA | ja, KI-GENERERT | 244 | 592 / 91 | 0,0000568 |

  - Til sammen kostet det USD 0,000249. For begge røykkallene er summen USD 0,000753.
  - Den første ekte prompten (`begrunnelse-v3`) og det første godtatte svaret, for BERGEN ENERGY:
    - Fakta: Tank, ETA fre 15.08 16:30, predikert fre 15.08 17:44, 6–24 t, avvik 138 min, varselgrense 120, varsel ja, 221 km, 6,7 kn, kurs −0,85, slakk 6,2 t, snittavvik 131 min over 183 anløp.
    - Svar: «BERGEN ENERGY er predikert til ankomst fre 15.08 17:44, mens rapportert ETA er fre 15.08 16:30, et avvik på 138 min fra kalibrert baseline og over varselgrensen på 120 min. Prediksjonen bygger på 221 km distanse til havna, fart over grunn på 6,7 knop, kurs mot havna på −0,85 og slakk mot rapportert ETA på 6,2 timer. Fartøyets historiske snittavvik er 131 min fra 183 tidligere anløp i treningsdata.»
  - Alle tallene i de to godtatte svarene står i faktaene, og ingen årsaker er diktet opp.
- Nøkkelen ble ikke skrevet ut, og ingenting ble satt i Vercel.

### Åpne punkter
- Modellen skriver opp mot grensen (400 og 402 tegn), så en del svar faller tilbake på lengden. Et forslag er å be om høyst 300 tegn i prompten, slik at det blir margin mot kontrollen på 400. Det er ikke gjort, og Theodor avgjør.
- `LLM_MODUS=ekte` i Vercel settes av Theodor, når Theodor vil.

## 2026-11-18 kl. 16:01 — Theodor Gimming (begrunnelse-v4 og røykkall 3)

### Oppgave
Lage `begrunnelse-v4`:
- Konklusjonen i forhold til rapportert ETA skal stå først og regnes ut i appen.
- Ingen interne begreper. Kurs og slakk oversettes med terskler fra definisjonene, og baselinen beskrives som «vanlig avvik for skipsgruppen».
- 1–2 grunner fra faktaene.
- Prompten ber om høyst 300 tegn, og kontrollen beholder 400.
- Kontroll, tester og mutanter skal oppdateres.

Deretter skulle de samme 3 røykkallene kjøres. Push, men ikke merge.

### Plan
- Lese definisjonene av F3 (cos(kurs − peiling)), F7 (rapportert ETA − kuttpunkt minus seilingstiden, klippet ved −48) og F15/F16 (avvik mot baselinen, trukket mot snittet for Øvrige med k = 5).
- Ny `klartekst.py` (konklusjon og retning), skrive om `lag_fakta`, malen, kontrollen (`konklusjon`, `begrep` og bredere `retning`) og prompten.
- Implementeringsagenten oppdaterte testene.

### Resultat
- **`bb19734` (E3-S03):**
  - Retning: F3 over 0 gir «på vei mot havna» og under 0 «på vei bort fra havna».
  - Rekker fram: F7 som «ja/nei, omtrent X timer før/etter rapportert ETA». Den utelates ved distanse 0 og under 1 knop.
  - Siste AIS-posisjon er kuttpunktet minus alderen.
  - Historikken utelates ved n = 0, fordi F15 da er snittet for Øvrige og ikke skipets eget.
- **Feilen jeg laget:** jeg ødela markøren `<!-- SYSTEM -->` i `prompt.md`, så ekte modus ville feilet på hvert kall. Agenten fant det gjennom 38 røde tester, og det er rettet. Se `notater.md`.
- **Suiten:** 679 tester er grønne.
- **Mutasjonssjekk:** alle 22 mutanter ble fanget, og kontrollkjøringen var grønn. Én overlevde først (historikk ved n = 0), og det ble lagt til en test for den.
- **Røykkall 3** (Wafer, ingen resonnering, alle stoppet av seg selv, alle godtatt, til sammen USD 0,000154):
  1. BERGEN ENERGY (230 tegn): «Ventes 74 min senere enn rapportert ETA (17:44 mot 16:30). Skipet var på vei bort fra havna ved siste posisjon, og hadde ikke gått fra Ågotnes. Skipets tidligere anløp er i snitt omtrent 131 min senere enn vanlig for skipsgruppen.»
  2. ISLAND CLIPPER (200 tegn): «Ventes 74 min tidligere enn rapportert ETA (18:16 mot 19:30). Skipet er på vei mot havna og rekker fram til rapportert ETA med farten ved siste posisjon. Tiden bygger på vanlig avvik for skipsgruppen.»
  3. NORMAND SIGMA (114 tegn): «Ventes 64 min tidligere enn rapportert ETA (06:56 mot 08:00). Tiden bygger på vanlig avvik for denne skipsgruppen.»

### Åpne punkter
- ISLAND CLIPPER er en modellrad, men svaret sier «Tiden bygger på vanlig avvik for skipsgruppen». Det er misvisende. Prompten ba om den setningen bare når faktaene ikke gir noen grunn. Kontrollen kan avvise setningen på modellrader. Theodor avgjør.
- Konklusjonen «Ventes 64 min tidligere enn rapportert ETA» på baselinerader kan leses som at skipet er tidlig. I virkeligheten er predikert tid inngang i havneområdet, og den ligger vanligvis rundt 64 min før ETA til kai (beslutning 03 og 04). Gruppa bør vurdere ordlyden.
