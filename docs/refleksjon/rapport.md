# Refleksjonsrapport - Programmering med KI

> **Status: under arbeid (E0-S20, opprettet 17.11.2026).** Strukturen følger kursmalen (`reflection-report-template.md`). Tekst i hakeparentes er malens hjelpetekst og er ikke skrevet ennå. Svarene på faglærers to refleksjonsspørsmål fra tilbakemeldingen på PRD-en ([`docs/tilbakemelding-prd.md`](../tilbakemelding-prd.md) kapittel 7) står i 3.1. De er **utkast** skrevet med KI (Claude), bygd bare på det som er dokumentert i [`notater.md`](notater.md), [`docs/beslutninger/`](../beslutninger/), [`docs/resultater.md`](../resultater.md) og sesjonsloggene i `.logs/`. Gruppa må lese dem, rette dem og skrive dem om med egne ord før innlevering. De individuelle refleksjonene i 7.4 skriver hver av oss selv.

## 1. Gruppeinformasjon

**Gruppenavn:** G73 – G73-hoffstrom-lopez-reed

**Gruppemedlemmer:**
- Theodor Gimming - [Student-ID/E-post]
- Felipe Knudstad-Lopez - [Student-ID/E-post]
- Thomas Kvile-Reed - [Student-ID/E-post]

**Dato:** [DD.MM.ÅÅÅÅ]

---

## 2. Utviklingsprosessen

### 2.1 Oversikt over prosjektet
[Kort beskrivelse av hva dere har utviklet. Hva var hovedmålet med applikasjonen?]

### 2.2 Arbeidsmetodikk
[Beskriv hvordan dere organiserte arbeidet]
- Hvordan fordelte dere oppgaver?
- Hvilke verktøy brukte dere for samarbeid og hvordan det fungerte? (f.eks. Git, og Teams)
- Hvordan brukte dere KI-verktøy i prosessen?

### 2.3 Teknologi og verktøy
[Liste over de viktigste teknologiene og verktøyene dere brukte]
- Frontend: [f.eks. NextJS, HTML/CSS]
- Backend: [f.eks. Python/FastAPI]
- Database: [f.eks. Supabase, MongoDB, PostgreSQL]
- KI-verktøy: [f.eks. Claude Code, Gemini CLI, GPT-5 Codex]
- Andre verktøy: [f.eks. VS Code, BMAD etc]

### 2.4 Utviklingsfaser
[Beskriv de ulike fasene i utviklingen]

**Fase 1: Planlegging**
- [Hva gjorde dere i denne fasen?]
- [Hvordan brukte dere KI her? Husk å lagre promptene deres! Inkluder ALLE stegene dere gjorde.]

**Fase 2: Utvikling**
- [Hva gjorde dere i denne fasen?]
- [Hvordan brukte dere KI her? Husk å lagre promptene deres! Inkluder ALLE stegene dere gjorde.]

---

## 3. Utfordringer og løsninger

### 3.1 Tekniske utfordringer

**Utfordring 1: Å hindre lekkasje i prediksjonen (FR9a)** — *UTKAST, svar på refleksjonsspørsmål 1: «Hvordan sjekket dere at FR9a faktisk hindrer lekkasje, og hva fant dere i KI-forslagene som måtte rettes?»*

- **Problem:** En prediksjon med horisont H skal bare bruke det vakta kunne vite H timer før ankomst. Hvis kuttet hadde vært forankret i faktisk ankomst, ville fasiten selv bestemt hvilke data modellen fikk se. Vi valgte derfor å kutte ved rapportert ETA − H (beslutning 08, PRD FR9a), og kravet ble at prediksjonen skal være uendret når alle AIS-punkter etter kuttet fjernes, og når faktisk ankomst endres.
- **Løsning, slik vi sjekket det:**
  - **Tester som låser hvert ledd i kjeden**, ikke bare sluttresultatet:
    - Hentingen henter aldri etter ETA − 6 t (`test_ingenting_etter_eta_minus_6t`, `85021b9`), og punkter etter kuttet filtreres bort på tidsstemplet i svaret (`test_filtrerer_bort_punkter_etter_kutt`, `14b21e3`).
    - Tilstandsutdraget har en egen lekkasjetest (`test_ingen_lekkasje`, `901f5c3`). Historikkfeaturene og ETD skal ikke bruke noe etter kuttet (`test_historikk_uten_lekkasje`, `test_etd_etter_kutt_brukes_ikke`).
    - Prediktorkontrakten gir ingen vei til fasit, og endret fasit gir identiske prediksjoner (`test_input_har_ingen_vei_til_fasit`, `test_endret_fasit_gir_identiske_prediksjoner`). En AST-sjekk stopper prediktormoduler som prøver å lese utdraget direkte (`5db2e45`, E1-S04).
  - **Mutasjonssjekk med kontrollkjøring.** For hver lekkasjetest endret vi koden slik at den lekker, og sjekket at testen ble rød. Vi kjørte også testen på uendret kode, for å se at den var grønn der.
  - **En lås og en vakt for testperioden** (E2-S08): appen viser ikke modellen på testvinduer før den ene testkjøringen, og en egen vakt i testene stopper modellen før den kjører på en testrad.
- **KI sin rolle, det vi måtte rette** (alle står i `notater.md` med dato):
  - **En test som bare fantes i teksten** (22.10). Filtreringen på tidsstempel var spesifisert med egen test i E2-S02 (`94330e9`), og Claude skrev i en oppsummering at FR9a krever filtrering «med egen test». Testen fantes ikke. Vi fant det fordi vi ba om bevis for at testen feiler når filteret fjernes. Den første versjonen av uttrekket kalte seg selv, og de første mutantene traff feil linje. Det ble avslørt av kontrollkjøringen på uendret kode, ikke av mutantene (`14b21e3`).
  - **«Verified against live API» uten at det var sjekket.** Hentekoden fra september (`ad2ffca`) sa i docstringen at tidene var verifisert. I virkeligheten forskjøv API-et vinduet med +1 t om vinteren og +2 t om sommeren. Uten filtrering på tidsstemplet ville modellen fått data fra etter kuttet (beslutning 09, `94330e9`).
  - **Arkitekturen motsa sin egen nye regel** (E1-S04). Lekkasjeregelen forbød prediktormoduler å lese `data/utdrag/`, men samme seksjon sa at modellen skulle lese tilstanden derfra. Ingen av de tre reviewerne så det. Claude fant det under triagen (`5db2e45`).
  - **En mutant som ikke kompilerte, så ut som en fanget mutant** (E1-S04). Pytest ga «errors», ikke «failed». Først da mutanten ble skrevet riktig, feilet fire lekkasjetester slik de skulle.
  - **Valideringstall målt på rader modellen hadde sett** (E2-S06). Claude skrev specen slik at valideringen brukte de endelige artefaktene, som er trent på trening og validering. Implementeringsagenten meldte det selv. Rettet med en modell som trenes på nytt bare på treningsdelen (`d36964c`, `78a6a02`).
  - **Testrader brukt utover det som var avtalt** (E2-S07). Implementeringsagenten kjørte modellen på testradene for å sjekke at artefaktene var uendret. Den leste ikke fasiten, men formålet var ikke tillatt. Etter det står regelen «testrader bare til det som er avtalt, ellers stopp og spør» i alle senere stories (`8e1f01f`).
- **Det vi ikke kan sjekke:** om rapportert ETA er slik den var kjent ved kuttet (A1), og om avgangshavn og ETD (F13–F14) er satt sammen i etterkant (beslutning 11). Begge står som kjente begrensninger i resultatnotatet.

**Utfordring 2: Resultat eller støy?** — *UTKAST, svar på refleksjonsspørsmål 2: «Hvis modellen bare slår baselinen med et par prosentpoeng, hvordan avgjør dere om det er et resultat eller støy, og hva skal stå i rapporten?»*

- **Problem:** Kriteriet vi låste før testkjøringen, var at modellen skulle ha *høyere* andel innenfor ±30 min enn baselinen på modellutvalget. Det hadde ingen margin, så 0,1 prosentpoeng ville også telt. Testkjøringen 13.11 (`8920acb`, `a30ddd7`) ga 68,5 % mot 59,1 % ved 6 t og 57,1 % mot 56,3 % ved 24 t. Ved 24 t var forskjellen seks anløp av 742, og formelt bestått.
- **Løsning:**
  - **Først en tilleggsanalyse.** Samme dag ba Felipe om McNemars test. Den trengte svar per anløp, og `metrikker.json` hadde bare summene. Claude stoppet og spurte før testradene ble lest på nytt. Felipe godkjente ett eget gjennomløp med de låste artefaktene, og bare krysstabellen og p-verdien ble lagret. Resultatet var p ≈ 2,3 · 10⁻⁷ ved 6 t og p = 0,64 ved 24 t (`a30ddd7`).
  - **Så faglærers tilbakemelding.** Tilbakemeldingen på PRD-en (`2fbc096`) foreslo en margin på 3 prosentpoeng og et 95 % konfidensintervall (bootstrap over anløp), og «ikke påvist» når forskjellen er mindre. Den lå på `main` fra 12.11, dagen før testkjøringen, men ble lest etter den. Gruppa bestemte å følge den (E2-S11, 17.11). Intervallene ble regnet fra krysstabellen som allerede var lagret, uten å lese testradene på nytt. Resultatet var +9,4 pp [6,0; 12,8] ved 6 t, som er bestått, og +0,8 pp [−2,0; 3,6] ved 24 t, som er ikke påvist.
  - **Hva som står i rapporten:** den nye dommen først, og den opprinnelige rett under. Vi sier rett ut at kriteriet ble endret etter testkjøringen, og at endringen gikk i strengere retning: den gjorde resultatet svakere, ikke sterkere. Ved 24 t står også ablasjonen uten F13–F14 (53,8 % mot 56,3 %), som viser at det lille som var, hvilte på felt vi ikke kan verifisere.
- **KI sin rolle:**
  - KI-en foreslo ikke selv en margin da kriteriet ble skrevet. Det var faglærer som så hullet.
  - Det som fungerte, var regelen om å stoppe og spørre før testrader brukes til noe nytt (fra E2-S07). Den gjorde at McNemar-gjennomløpet ble godkjent og dokumentert før det skjedde, ikke forklart etterpå.
  - Ved første lagring ble p-verdien ved 6 t avrundet til `0.0`, fordi skriptet runder til 6 desimaler. Den ble regnet på nytt fra krysstabellen.
- **Lærdom (utkast):** Margin og rapporteringsregel må låses *før* den første testkjøringen. «Høyere» er ikke et kriterium når forskjellen kan være seks anløp. Når et kriterium likevel endres etterpå, må begge dommene stå, sammen med hvilken vei endringen gikk.

### 3.2 Samarbeidsutfordringer
[Utfordringer knyttet til teamarbeid og kommunikasjon]
- [Beskriv utfordringer og hvordan dere løste dem]

### 3.3 KI-spesifikke utfordringer
[Problemer spesifikt knyttet til bruk av KI]
- [f.eks. Feil kode fra KI, misforståelser, inkonsistent kvalitet]
- [Hvordan håndterte dere disse?]

---

## 4. Kritisk vurdering av KI sin påvirkning

### 4.1 Fordeler med KI-assistanse
[Reflekter over de positive aspektene]

**Effektivitet og produktivitet:**
- [Hvordan påvirket KI arbeidshastigheten?]
- [Eksempler på oppgaver som gikk raskere]

**Læring og forståelse:**
- [Hva lærte dere ved å bruke KI?]
- [Bidro KI til bedre forståelse av konsepter?]

**Kvalitet på koden:**
- [Hvordan påvirket KI kodekvaliteten?]
- [Eksempler på forbedringer KI foreslo]

### 4.2 Begrensninger og ulemper
[Reflekter over de negative aspektene]

**Kvalitet og pålitelighet:**
- [Eksempler på feil eller dårlige løsninger fra KI]
- [Hvordan oppdaget og håndterte dere disse?]

**Avhengighet og forståelse:**
- [Ble dere for avhengige av KI?]
- [Var det tilfeller hvor KI hindret læring?]

**Kreativitet og problemløsning:**
- [Påvirket KI deres egen kreativitet?]
- [Eksempler på situasjoner hvor KI begrenset kreativ tenkning]

### 4.3 Sammenligning: Med og uten KI
[Reflekter over hvordan prosjektet ville vært uten KI]
- Hva ville vært annerledes?
- Hvilke deler av prosjektet ville vært vanskeligere/lettere?
- Ville sluttresultatet vært bedre eller dårligere?

### 4.4 Samlet vurdering
[Konklusjon: Hvordan påvirket KI sluttresultatet totalt sett?]
- Var KI en netto positiv eller negativ faktor?
- Hva var den viktigste lærdommen om å bruke KI i utviklingsprosessen?

---

## 5. Etiske implikasjoner

### 5.1 Ansvar og eierskap
- Hvem er ansvarlig for koden når KI har bidratt?
- Hvordan sikrer man kvalitet når KI genererer kode?
- Diskuter spørsmål om opphavsrett og intellektuell eiendom

### 5.2 Transparens
- Bør det være transparent at KI er brukt?
- Hvordan dokumenterer man KI sin bidrag?
- Hva er konsekvensene av å ikke være åpen om KI-bruk?

### 5.3 Påvirkning på læring og kompetanse
- Hvordan påvirker KI-avhengighet fremtidig kompetanse?
- Hvilke ferdigheter risikerer man å ikke utvikle?
- Balanse mellom effektivitet og læring

### 5.4 Arbeidsmarkedet
- Hvordan kan utbredt KI-bruk påvirke fremtidige jobber i IT?
- Hvilke roller vil bli viktigere/mindre viktige?
- Deres refleksjoner om fremtidig karriere i en KI-drevet verden

### 5.5 Datasikkerhet og personvern
- Hvilke data delte dere med KI-verktøy?
- Potensielle risikoer ved å dele kode og data med KI
- Hvordan skal man tenke på sikkerhet når man bruker KI?

---

## 6. Teknologiske implikasjoner

### 6.1 Kodekvalitet og vedlikehold
- Hvordan påvirker KI-generert kode langsiktig vedlikehold?
- Er KI-kode like forståelig som menneskeskrevet kode?
- Utfordringer med å debugge KI-generert kode

### 6.2 Standarder og beste praksis
- Følger KI alltid beste praksis og industristandarder?
- Eksempler på hvor KI foreslo utdaterte eller dårlige løsninger
- Viktigheten av å validere KI sine forslag

### 6.3 Fremtidig utvikling
- Hvordan tror dere KI vil påvirke programvareutvikling fremover?
- Hvilke ferdigheter blir viktigere for utviklere?
- Deres anbefalinger for hvordan man bør bruke KI i utviklingsprosesser

---

## 7. Konklusjon og læring

### 7.1 Viktigste lærdommer
[Liste de 3-5 viktigste tingene dere lærte gjennom prosjektet]
1. [Lærdom 1]
2. [Lærdom 2]
3. [Lærdom 3]

### 7.2 Hva ville dere gjort annerledes?
[Reflekter over hva dere ville endret hvis dere skulle startet på nytt]
- [Tekniske valg]
- [Bruk av KI]
- [Samarbeid og organisering]

### 7.3 Anbefalinger
[Deres anbefalinger til andre studenter som skal bruke KI i utvikling]
- [Råd om effektiv bruk av KI]
- [Fallgruver å unngå]
- [Beste praksis dere oppdaget]

### 7.4 Personlig refleksjon (individuelt)

**Theodor Gimming:**
[Personlig refleksjon over egen læring og utvikling]

**Felipe Knudstad-Lopez:**
[Personlig refleksjon over egen læring og utvikling]

**Thomas Kvile-Reed:**
[Personlig refleksjon over egen læring og utvikling]

---

## 8. Vedlegg (valgfritt)

- Skjermbilder av applikasjonen
- Lenke til GitHub repository
- Annen relevant dokumentasjon

---

**Ordantall:** [Ca. antall ord]

**Forventet lengde:** 3000-5000 ord (avhengig av gruppestørrelse og prosjektets kompleksitet)
