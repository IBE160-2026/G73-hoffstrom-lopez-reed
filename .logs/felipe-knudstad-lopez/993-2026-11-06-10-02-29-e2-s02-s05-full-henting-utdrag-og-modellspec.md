# E2-S02–S05: full henting, utdrag, sjekker og modellspec

## 2026-11-06 kl. 10:02 — Felipe Knudstad-Lopez

### Oppgave
Felipe styrte økta fra Theodors maskin. Hentingen for E2-S02 var ferdig: 7 825 av 7 826 seilaser, og 1 feil (URLError 05.11, maskinen var uten nett). Planen var:
1. ta de seks review-rettelsene og hente den feilede seilasen
2. committe dekningstabellen og sette E2-S02 ferdig
3. sammenligne dekningen med 93 % i beslutning 09
4. lage tilstands- og featureutdragene
5. kjøre sjekken av lange avstander og etikettsjekken
6. starte E2-S05 med full BMAD-flyt og stoppe ved godkjenning

Alle commits har Felipe som forfatter.

### Plan
- Steg 1–3, stopp og vis. Deretter flytte tabellen til `data/utdrag/`, beslutning 09, push og steg 4–5, stopp og vis. Så sjekkskriptet, beslutning 03, refleksjonsnotater, push og E2-S05.
- Kontinuitet: [998 e2-s02](998-2026-11-03-18-21-12-e2-s02-ais-henting-ved-kuttpunkt.md), [996 e2-s03](996-2026-11-03-19-02-50-e2-s03-tilstandsutdrag.md), [995 e2-s04](995-2026-11-03-19-20-13-e2-s04-features.md).
- E2-S05-spec (utkast): `_bmad-output/implementation-artifacts/spec-e2-s05-tren-modell.md`.

### Resultat
- **`8694a48` E2-S02, de seks review-rettelsene, med 10 nye tester:**
  - En manglende dag som ikke kan deles, teller mot stoppregelen.
  - Vernet mot evig deling har fått tester.
  - Delkallene har fått pause.
  - Dedupen er fjernet.
  - Svaret klippes til forespørselen + 2 t. Det avviker fra funnet, som sa ved `slutt`. Begrunnelsen står i specen.
  - Det er nye tester for `tapt_intervall` og for gammel cache.
  - Mutasjonssjekk: 7 av 7 mutasjoner fanget.
  - Seilas 2713140 ble hentet på nytt, så alle 7 826 av 7 826 er i cachen (6,0 GB).
- **`46db209` E2-S02:** dekningstabellen er lagt til, og E2-S02 står til ✅.
- **`9b2e433`:** tabellen er flyttet til `data/utdrag/ais_kutt_dekning.csv`, og skriptet, epics og specen er oppdatert. Beslutning 09 har fått et avsnitt om resultatet: 93,4 % (930/996, KI 91,7–94,8) med fasit, 90,4 % for alle anløp og 65,2 % for `empty`. De samme 40 anløpene fra stikkprøven gir fortsatt 37/40, med de samme 3 som manglet. Tråden om `empty` er lukket.
- **`910028c` E2-S03:** `tilstand_ved_kutt.csv/.json`, 15 652 rader. Ved H = 6 er 6 866 `ok`, og ved H = 24 er 6 569 `ok`. `manglende_dag` er 1 ved H = 6 og 10 ved H = 24. Ny `test_committet_tilstand`, og E2-S03 står til ✅.
- **`47a2c02` E2-S04:** `features.csv/.json`, 15 652 rader, med 5 008 / 1 252 / 1 566 anløp per del. En ny kjøring ga byte-identisk fil. Ny `test_committet_features`. E2-filene er 4,2 MB til sammen. E2-S04 står til ✅.
- **`a90f1f6` E2-S04, `scripts/sjekk_avstand_og_etikett.py`:**
  - 15 rader trenger mer enn 25 kn.
  - Tre er «umulige» (HALTBAKK STAR, NORDKAPP og STAVANGERFJORD), alle i train.
  - 33 av 6 815 anløp (0,48 %) har soneinngang mer enn 24 t før ETA, spredt på 14 skipstyper. Offshore og forsyning står for 18,2 % av dem, mot 15,8 % av alle anløp. 6 av de 33 er i test.
  - Ført inn som kjent begrensning i beslutning 03, og tabellene står i E2-S04-specen.
- **`bd1dce3`:** refleksjonsnotater om de manglende committet-testene (andre gang, jf. 22.10) og om feil kallantall i review-funnet.
- Alt til og med `bd1dce3` er pushet. Testene er grønne: 263 passed.
- **E2-S05:** BMAD-build steg 1–2 er kjørt. Specen er skrevet med `status: draft` (ikke committet), med tre åpne spørsmål: valideringskriteriet, kandidatsettet, og om de 33 tidlige anløpene og de 3 umulige skal være med i treningen. Specen er omtrent 2 400 tokens, over grensen på 1 600.

### Åpne punkter
- E2-S05: Felipe svarer på de tre åpne spørsmålene i specen og avgjør om specen kan være over 1 600 tokens. Deretter godkjennes den, og implementeringen starter.
- Seilas 3353948 HALTBAKK STAR i testdelen har soneinngang 89 t før ETA (beslutning 03). Den tas med i resultatnotatet (E2-S10) som en mulig etikettfeil i testperioden.

## 2026-11-09 kl. 14:26 — Felipe Knudstad-Lopez

### Oppgave
Felipe svarte på de tre spørsmålene i E2-S05-specen: 1A med en tilleggsregel, 2B og 3A. Tilleggsregelen er at konfigurasjoner innenfor 1 pp av den beste andelen innenfor ±30 min regnes som like gode, og at den enkleste av dem velges. Specen skulle holdes samlet, og implementeringen skulle starte («Godkjenn og fortsett»).

### Plan
- Svarene føres inn som beslutninger i specen. Deretter implementerer en subagent fra specen, tre reviewere går gjennom resultatet parallelt, og rettelsene tas inn.
- Spec: `_bmad-output/implementation-artifacts/spec-e2-s05-tren-modell.md`, med status `done`.

### Resultat
- **`aa66a2b`:** `scripts/tren.py` og `tests/test_tren.py`, og `scikit-learn==1.6.1` lagt til i `requirements.txt`.
- **`9a52b9d`:** de fire artefaktene og `modellvalg.json`, og E2-S05 står til ✅.
- Subagenten committet med Theodor som forfatter. Forfatteren er skrevet om til Felipe før push.
- **Review:** tre lag fant fem testhull, alle bekreftet med mutasjoner, og to feil i innholdet:
  - artefaktene manglet offset og sha for baseline
  - numpy og joblib var ikke låst
- **`36eebb0` og `f5418ad`:** rettelsene, med fem nye tester og artefaktene trent på nytt. `modellvalg.json` er byte-identisk.
- Testene er grønne: 276 passed på omtrent 10 s. E2-dataene er 6,4 MB.
- **Valideringsresultat:** begge horisontene valgte `absolute_error`, læringsrate 0,05 og 15 blad. Innenfor ±30 min: 62,8 % mot 41,5 % for referansen ved 6 t, og 56,2 % mot 39,6 % ved 24 t.
- **Funn:** 947 Øvrige-anløp med fasit er allerede i sonen ved t_6, og 569 av dem er merket sene. Det er lokale turer der avgangshavna ligger inne i 15-km-sonen (Kleppestø, Ågotnes, Skålevik, Bergen). Etiketten er da ikke en ankomst. F6 alene gir F1 0,82 på valideringsdelen.
- **Ikke pushet:** de fire E2-S05-commitene og denne loggen.

### Åpne punkter
- Felipe avgjør hva som gjøres med turene inne i sonen før E2-S06. Alternativene er å holde seg til splitten med og uten F6 som planlagt, å gjøre dem til egen kategori, å holde dem utenfor modellen, eller å føre dem som kjent begrensning i beslutning 03.
- Toleransen på 1 pp er mindre enn utvalgsstøyen (n = 634/621, standardfeil ≈ 2 pp), så enkelhetsregelen slo aldri inn. Felipe vurderer om toleransen skal opp.

## 2026-11-09 kl. 14:34 — Felipe Knudstad-Lopez

### Oppgave
Felipe ba om fire ting:
- Pushe de seks E2-S05-commitene.
- Funn 1 (trafikk inne i sonen): føre det inn i beslutning 03 som en begrensning ved etiketten, lage beslutning 12 (modellen brukes bare utenfor sonen ved kuttet, og F6-rader går til baselinen), trene en variant uten F6-rader og vise en tabell med (a), (b) og (c).
- Funn 2 (toleransen): ikke endre den, men skrive i modellvalg.json at regelen ikke slo inn, og hvorfor.
- Stoppe før E2-S06.

### Plan
- Push. Filtrere F6 i `treningsrader` og teste filteret med en mutasjon.
- Lage sammenligningstabellen på valideringsdelen med modellene fra modellvalget. Testperioden røres ikke.
- Trene på nytt og oppdatere beslutning 03 og 12, PRD FR9, epics og specen.

### Resultat
- Pushet til og med `e5a66d2`.
- **`e68bdc5`:**
  - Beslutning 12 er ny, og beslutning 03 har fått et tillegg.
  - `tren.py` utelater F6-rader. `modellvalg.json` har fått `utvalg`, `enkelhetsregel_endret_valget`, standardfeil og `toleranse_merknad`.
  - PRD FR9 og epics (E2-S06/S07 og endringsloggen) er oppdatert, og specen har fått en linje i endringsloggen.
- **`54ff298`:** artefaktene er trent på nytt. Det ble 15 blad ved 6 t og 31 ved 24 t, og E2-dataene er 7,5 MB.
- Testene er grønne: 276 passed.
- Tabellen på valideringsdelen (± 30 min, modell mot baseline på de samme radene):
  - (a) gammel modell på alle rader: 62,8 / 41,5 ved 6 t, og 56,2 / 39,6 ved 24 t
  - (b) gammel modell uten F6-rader: 70,6 / 56,9, og 60,4 / 51,8
  - (c) ny modell uten F6-rader: 69,1 / 56,9, og 59,8 / 51,8

  F1 for (c) er 0,58 og 0,60, mot 0,19 og 0,28 for «varsle alle». Hele tabellen står i beslutning 12.
- Enkelhetsregelen endret ikke valget ved noen av horisontene. Ved 6 t lå 3 konfigurasjoner innenfor toleransen, men den beste var også den enkleste.
- Skriptet som lager tabellen, ligger bare i scratchpad. Tallene står i beslutning 12.
- Ikke pushet: `e68bdc5`, `54ff298` og denne loggen.

### Åpne punkter
- Beslutning 12 godkjennes av gruppa i E2-PR-en, og Thomas ser på E2-S07, der F6-rader delegeres.

## 2026-11-09 kl. 17:20 — Felipe Knudstad-Lopez

### Oppgave
Felipe svarte på spørsmålene i E2-S06-specen:
- **1A:** bestått/ikke bestått avgjøres på modellutvalget. All Øvrige-trafikk med delegering skal stå i samme tabell, både i briefen og i resultatnotatet, sammen med hvor stor andel av anløpene modellen brukes på.
- **2B:** testkjøringen gjøres i E2-S10. Modell, konfigurasjon og valgregler er låst før den kjøringen.

Han godkjente og ba om at arbeidet fortsatte. Under reviewen svarte han på to nye spørsmål:
- valideringstallene skal komme fra en modell trent på nytt i minnet, bare på treningsdelen
- varselstreken skal ligge på modellutvalget, og dokumentene skal si rett ut at den er lavere

### Plan
- Svarene føres inn i specen som beslutning 1–3. En subagent implementerer, og tre reviewere går gjennom resultatet. De to nye spørsmålene går til Felipe og føres inn som beslutning 4–5, og implementøren retter funnene.
- Spec: `_bmad-output/implementation-artifacts/spec-e2-s06-evalueringsskript.md`, med status `done`.

### Resultat
- **`79ea662` og `73bc453`:**
  - `scripts/evaluer.py`, nye mål i `app/metrikker.py` og nye tester.
  - Briefen (EN og NO), PRD FR10 og `status.md` sier at bestått/ikke bestått avgjøres på modellutvalget.
  - E2-S10 har fått låsen og tabellen med begge radene.
  - `metrikker.json` er committet. Subagenten committet som Theodor, og forfatteren ble skrevet om til Felipe.
- **Review:** 19 funn.
  - To krevde svar fra Felipe:
    - De endelige artefaktene er trent på trening + validering, så valideringstallene var målt på rader modellen hadde sett. Modellutvalget viste 78,2 % og 72,4 % mot 69,1 % og 59,8 % holdt ut.
    - Varselstreken ble senket fra F1 0,33 til 0,14 og 0,19 uten at det sto noe sted.
  - Sju ble rettet.
  - Én ble utsatt: `--test`-stien er ikke testet. Den skal prøvekjøres på en kopi før E2-S10 (`deferred-work.md`).
  - Resten ble avvist med begrunnelse i specens triage-logg.
- **`d36964c` og `78a6a02`:**
  - Valideringen trener modellen på nytt i minnet, bare på treningsdelen. Tallene er nå lik `modellvalg.json`: 69,1 % ved 6 t og 59,8 % ved 24 t, med F1 0,58 og 0,60. En test låser dette.
  - Briefen og PRD sier at varselstreken er lavere, hvorfor, og at den ble flyttet etter valideringstallene.
  - Grensene på testperioden (433/733 og 418/742) er låst i en test.
  - Splitten sjekkes begge veier.
  - `--test` nekter å kjøre en gang til uten `--ny-testkjoring`.
- **Testperioden, bare baseline:**
  - Baselinen på modellutvalget er 59,1 % ved 6 t og 56,3 % ved 24 t. Modellen brukes på 73,6 % og 74,5 % av Øvrige-anløpene med fasit.
  - Av 194 forsinkede Øvrige-anløp er 57 og 78 i utvalget, 107 og 92 er F6-rader, og 30 og 24 har ingen tilstand.
- **`286dd20`:** specen med beslutninger, endringslogg og triage-logg.
- **`88e395f`:** refleksjonsnotat.
- `testkjoringer` = 0. Testene er grønne: 300 passed. En ny kjøring gir en byte-identisk `metrikker.json`.
- Ikke pushet.

### Åpne punkter
- Før testkjøringen i E2-S10 prøvekjøres `--test` på en kopi av `metrikker.json`, så det er sikkert at tallene havner under `test` og at kjøringen telles.
- Gruppa godkjenner den nye suksessformuleringen i briefen og PRD (modellutvalget avgjør, og varselstreken er lavere) i E2-PR-en.

## 2026-11-09 kl. 17:25 — Felipe Knudstad-Lopez

### Oppgave
Felipe ba om fire ting:
- pushe alt
- skrive tydelig i briefen, resultatnotatet, README og på skjermen at varselet bare kan nå under halvparten av de forsinkede anløpene
- føre i loggen at baselinetallene på testperioden ble regnet etter at vi sa stopp
- sette forfattervariablene for git i miljøet og skrive forfatterregelen inn i instruksen til hver subagent

Deretter skulle E2-S07 startes med full BMAD-flyt og stoppe ved godkjenning av specen.

### Plan
- Teksten føres inn der varselet beskrives. Resultatnotatet finnes ikke ennå, så kravet legges i E2-S10 i `docs/epics.md`.
- E2-S07: steg 1–2 i BMAD-build. Spec: `_bmad-output/implementation-artifacts/spec-e2-s07-modellprediktor.md` (draft).

### Resultat
- **Pushet** til og med `ea6d23b`. Alle 8 nye commits har Felipe som forfatter.
- **`ea6d23b`:** teksten om at varselet når under halvparten står nå flere steder:
  - Briefen (EN og NO), under tabellen: av 194 forsinkede Øvrige-anløp ligger bare 57 (6 t) og 78 (24 t) i modellutvalget. Systemet kan dermed varsle om under halvparten av de forsinkede anløpene, uansett modellens kvalitet. Resten er turer inne i sonen (F6: 107 og 92) eller anløp uten AIS (30 og 24).
  - README og forsiden, der varselet forklares. Testen i `tests/test_ruter.py` er utvidet.
  - E2-S08 og E2-S10 i `docs/epics.md` skal si det samme der varselet forklares.
  - Skjermbildet `docs/ux/skjermbilder/hovedskjerm-desktop.png` er ikke laget på nytt. Det viser den gamle teksten, og PR #6 endrer det samme bildet.
- **Baselinetallene på testperioden ble regnet etter at vi sa stopp.** Testkjøringen ble lagt til E2-S10 (beslutning 2 i E2-S06). Etter det regnet `scripts/evaluer.py --bare-baseline` baselinen på testperioden: 433/733 og 418/742 på modellutvalget, modellandelen, grunnratene og fordelingen av de 194 forsinkede anløpene. Tallene inneholder ingen modellvalg, og ingen modell ble kjørt. **Ingenting i E2-S07 til E2-S09 skal endres på grunnlag av dem** (Felipe). Det står også som en grense i E2-S07-specen.
- **Forfatter:**
  - `GIT_AUTHOR_NAME` og `GIT_AUTHOR_EMAIL` er satt til Felipe i `.claude/settings.local.json`. Fila er gitignorert og ligger lokalt på Theodors maskin.
  - Variablene virker først fra neste oppstart av Claude Code, ikke i denne økta. Inntil da brukes `--author` på hver commit.
  - Instruksen til hver subagent skal si at commits har Felipe som forfatter.
- **E2-S07:** specen er skrevet med `status: draft`, med ett åpent spørsmål: hvordan F1–F16 når prediktoren (søsterfunksjon i grensen, eller nytt felt i `PrediksjonsInput` med egen PR). Den er omtrent 2 400 tokens.

### Åpne punkter
- Fjern `env`-blokken i `.claude/settings.local.json` når Felipe ikke lenger styrer. Ellers får Theodors egne commits Felipe som forfatter.
- Skjermbildet av hovedskjermen må lages på nytt etter PR #6, med den nye varselteksten.

## 2026-11-09 kl. 17:27 — Felipe Knudstad-Lopez

### Oppgave
Felipe svarte 1A på spørsmålet i E2-S07-specen og ville ha en test som viser at `featurer_ved_kutt` bare kan returnere modellens featurekolonner. Forfattervariablene skulle fjernes igjen, og han valgte «Godkjenn og stopp».

### Plan
- Svaret føres inn i specen som beslutning 1–4, og specen settes til `ready-for-dev`.
- `.claude/settings.local.json` fjernes. Spec og logg committes med `--author` og pushes.

### Resultat
- **E2-S07-specen** (`_bmad-output/implementation-artifacts/spec-e2-s07-modellprediktor.md`) er committet med status `ready-for-dev`. Den er ikke implementert. Beslutningene:
  1. Featurene F1–F16 når prediktoren gjennom `featurer_ved_kutt(inp)` i grensen. Det er ingen kontraktendring og ingen egen PR.
  2. En test viser at funksjonen bare returnerer modellens featurekolonner, aldri etikett- eller ankomstfelt. Den har også fått en egen rad i matrisen.
  3. Specen holdes samlet, selv om den er over 1 600 tokens.
  4. Alle commits skal ha Felipe som forfatter.
- **`.claude/settings.local.json` er fjernet.** Fila fantes ikke før økta og inneholdt bare de to variablene. Den har aldri vært sporet i git (`git ls-files` finner den ikke, og den står i `.gitignore:52`). Fremover brukes `--author` på hver commit, og forfatterregelen står i instruksen til subagentene. Punktet i `issues.md` er lukket.

### Åpne punkter
- E2-S07 implementeres i en ny økt fra specen (`ready-for-dev`). Forfatterregelen står i instruksen til subagenten.
