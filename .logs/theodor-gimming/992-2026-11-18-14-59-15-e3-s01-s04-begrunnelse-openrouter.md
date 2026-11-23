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

## 2026-11-18 kl. 16:12 — Theodor Gimming (begrunnelse-v5 og røykkall 4)

### Oppgave
Fire endringer:
1. Konklusjonen skal si at tiden gjelder havneområdet, ikke kai. Baselinerader får i tillegg «Det er vanlig for denne skipsgruppen.»
2. Varselrader får avviket fra det vanlige for skipsgruppen, regnet ut i appen.
3. «Vanlig avvik for skipsgruppen» skal avvises som forklaring på modellrader.
4. Avgangshavn og ETD skal formuleres som registrert informasjon (beslutning 11).

Deretter skulle kontroll, tester og mutanter oppdateres, de 3 røykkallene kjøres, og grenen pushes uten merge.

### Plan
- `klartekst.innledning`: setningene appen skriver, som svaret må starte med ordrett.
- Ny kontrollregel `metode` (med `modellrad`).
- «kl.» og «ca.» skal ikke telles som setningsslutt.
- Faktafeltet «Setninger du kan legge til», og prompten `begrunnelse-v5`.
- Implementeringsagenten oppdaterte testene.

### Resultat
- **`aeff198` (E3-S03).** Suiten er grønn med 716 tester.
- **Mutasjonssjekk:** alle 16 mutanter ble fanget, og kontrollkjøringen var grønn. To overlevde først: adapteren sendte ikke `modellrad`, eller bare konklusjonen. Det fikk to tester gjennom adapteren, og står i `notater.md`.
- **Røykkall 4** (Wafer, ingen resonnering, alle godtatt, til sammen USD 0,000176):
  1. BERGEN ENERGY (243 tegn): «Ventes inn i havneområdet kl. 17:44, 74 min etter rapportert ETA (16:30). Det er 2 t 18 min senere enn vanlig for skipsgruppen. Skipet var på vei bort fra havna ved siste posisjon, og avgang fra Ågotnes var ikke registrert per tor 14.08 16:30.»
  2. ISLAND CLIPPER (228 tegn): «Ventes inn i havneområdet kl. 18:16, 74 min før rapportert ETA (19:30). Skipet er på vei mot havna og rekker fram til rapportert ETA med farten ved siste posisjon. Avgang fra Mongstadbase var ikke registrert per tor 14.08 19:30.»
  3. NORMAND SIGMA (109 tegn): «Ventes inn i havneområdet kl. 06:56, 64 min før rapportert ETA (08:00). Det er vanlig for denne skipsgruppen.»

### Åpne punkter
- Avvik på 90 min eller mer vises som timer og minutter («2 t 18 min»). Theodor brukte «138 min» som eksempel, så formatet bør avklares.

## 2026-11-18 kl. 16:15 — Theodor Gimming (avslutning 18.11)

### Oppgave
Avslutte dagen uten å merge PR #11:
- «2 t 18 min» beholdes.
- De åpne punktene skal stå i `issues.md`: UU-sjekk av skjerm C i forhåndsvisningen, at gruppa ser gjennom PR-en og merger, og `LLM_MODUS=ekte` i Vercel etter merge og før sensur.
- Loggen skal avsluttes, committes og pushes, og arbeidstreet og suiten skal sjekkes.

### Plan
- Oppdatere `issues.md`, skrive denne seksjonen, committe, pushe og kontrollere tilstanden.

### Resultat
- **Formatet:** «2 t 18 min» beholdes, og punktet er lukket.
- **Åpne punkter oppdatert i `issues.md`:**
  - UU-sjekken av skjerm C skal gjøres i forhåndsvisningen, også med en henting som feiler.
  - Gruppa ser gjennom PR #11 og merger.
  - `LLM_MODUS=ekte` settes i Vercel etter merge og før sensur.
- **Dagen samlet (18.11):**
  - E0-S22: `technology.md` er fjernet, og `.env` er satt opp (PR #10, merget).
  - E3-S01–S04 er bygd etter bmad-build: spec med valgene S1–S7, review med tre lag (26 funn) og mutasjonssjekker.
  - Fire runder røykkall har gitt prompten `begrunnelse-v5`. Alle tre testtilfellene godkjennes nå. De fire rundene kostet til sammen USD 0,0011.
  - PR #11 er åpen og ikke merget.
- **KI-feil** er ført i `notater.md`: gamle `.pyc`-filer, tallkontrollen uten fortegn, pronomen, resonneringen som brukte opp token-grensen, den ødelagte markøren i prompten, og koblingen i adapteren som ikke var testet.
- Arbeidstreet og suiten er sjekket etter commit og push. Se sluttoppsummeringen.

### Åpne punkter
- Står i `issues.md`: UU-sjekk av skjerm C, gjennomgang og merge av PR #11, `LLM_MODUS=ekte` i Vercel, sjekk av kostnadsoverslaget før levering, og refleksjonsrapporten.

## 2026-11-19 kl. 15:30 — Theodor Gimming (UU-sjekk av skjerm C og begrunnelse-v6)

### Oppgave
- Lage stegene for en manuell UU-sjekk av skjerm C i forhåndsvisningen av PR #11, også med en henting som feiler.
- Krysse av resultatet i UX §6.
- Avrunde timer i faktaene til hele tall («ca. 42 timer» i stedet for «omtrent 42,0 timer»).
- Pushe til PR #11 uten å merge.

### Plan
- Sjekket at PR #11 og Vercel-forhåndsvisningen var oppdatert (`3c5a1b8`, Vercel SUCCESS). Fant OCEAN RESPONSE (3386826, med varsel) og EINARSON (3390320, uten varsel) i standardvinduet.
- Fant at en henting bare skjer i ekte modus, fordi testmodus skriver mal-teksten rett inn på siden. «Offline etter lasting» virker ikke, fordi hentingen er ferdig før du rekker det. Theodor brukte derfor Network request blocking (`*/begrunnelse`).
- Prompten forbød «ca.» utenom innledningen. Theodor valgte v6, som tillater «ca.» slik det står i faktaene, og «under 1 time» / «ca. 1 time» for 0 og 1.

### Resultat
- **UU-sjekken** ble gjort av Theodor 19.11 i forhåndsvisningen, i ekte modus. `LLM_MODUS=ekte` er satt for Preview i Vercel, ikke for Production. Alle seks stegene besto: modus, tastatur, VoiceOver/aria-live, uten JavaScript, blokkert henting («Testmodus (ekte kall feilet)», uten feilmelding) og overskriftene. Radene for skjerm C i UX §6 er krysset av (`4f73a14`, E3-S04).
- **`02f4372` (E3-S03), begrunnelse-v6:** `_ca_timer` i `app/begrunnelse/input.py` runder av halve opp. Det gjelder «Rekker fram» og «Avgang». Prompten tillater «ca.» slik det står i faktaene. Kontrollkoden er uendret, fordi «ca.» allerede ikke deler setninger og tallregelen avviser 41,7. Det er dekket av en ny test. Beslutning 13 har fått et avsnitt om v6.
- **Suiten:** 724 tester grønne (716 + 8).

### Åpne punkter
- Det er ikke gjort et røykkall med `begrunnelse-v6`. Det gjøres bare når Theodor godkjenner det.
- Med `LLM_MODUS=ekte` for Preview gjør alle forhåndsvisninger, også for andre grener, betalte kall. Avgjør om Preview skal settes tilbake til `test` etter gjennomgangen.

## 2026-11-19 kl. 15:34 — Theodor Gimming (røykkall 5 og Preview i ekte modus)

### Oppgave
Kjøre røykkallet med `begrunnelse-v6` med de samme 3 tilfellene, lokalt og med `LLM_MODUS=ekte` bare for kjøringen. Theodor ville se tekstene, om kontrollen godtok dem, og kostnaden. Avgjørelsen om Preview skulle føres inn, og grenen pushes uten merge.

### Plan
- Kjørte et engangsskript fra scratchpad, ikke i repoet. Det kaller `hent_begrunnelse` én gang per tilfelle, fanger rått svar og `usage`, og stopper hvis nøkkelen havner i utskriften.
- Modellradene kom fra valideringsvinduet 15.08.2025 08:00, som før. Det var BERGEN ENERGY (varsel), ISLAND CLIPPER (uten varsel) og NORMAND SIGMA (baseline).

### Resultat
- **Røykkall 5** (Particle AI, `finish_reason` = `stop`, ingen resonneringstokens). Alle tre ble godtatt (KI-GENERERT), og ingen kontrollregel slo inn. Til sammen kostet de USD 0,000139.
  1. BERGEN ENERGY (243 tegn, 1028/90 tokens, USD 0,0000533): «Ventes inn i havneområdet kl. 17:44, 74 min etter rapportert ETA (16:30). Det er 2 t 18 min senere enn vanlig for skipsgruppen. Skipet var på vei bort fra havna ved siste posisjon, og avgang fra Ågotnes var ikke registrert per tor 14.08 16:30.»
  2. ISLAND CLIPPER (228 tegn, 1008/81 tokens, USD 0,0000505): «Ventes inn i havneområdet kl. 18:16, 74 min før rapportert ETA (19:30). Skipet er på vei mot havna og rekker fram til rapportert ETA med farten ved siste posisjon. Avgang fra Mongstadbase var ikke registrert per tor 14.08 19:30.»
  3. NORMAND SIGMA (109 tegn, 838/41 tokens, USD 0,0000354): «Ventes inn i havneområdet kl. 06:56, 64 min før rapportert ETA (08:00). Det er vanlig for denne skipsgruppen.»
- Tekstene var de samme som i røykkall 4. Faktaene hadde «ca. 6 timer» og «ca. 16 timer», men ingen av svarene brukte timetallet. Derfor er «ca.» i et svar bare dekket av testen. Det er ført i beslutning 13 (røykkall 5). Summen for alle fem røykkallene er USD 0,001222.
- **Preview:** Theodor avgjorde at Preview beholder `LLM_MODUS=ekte` til E3 er ferdig. Punktet er lukket, og det er lagt inn et nytt punkt om å vurdere det igjen etter S07.

### Åpne punkter
- Vurder på nytt om Preview skal beholde `LLM_MODUS=ekte` når E3 er ferdig (står i `issues.md`).
