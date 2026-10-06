# Tilbakemelding på product brief

| | |
|---|---|
| **Gruppe** | G73 – G73-hoffstrom-lopez-reed |
| **Product brief** | `docs/brief.md` (commit `c1fe8c3`), lest sammen med `docs/addendum.md`. Den norske oversettelsen `docs/brief.no.md` (commit `ad2ffca`) er eldre og mangler endringene fra 28. september. |
| **Tilbakemelding fra** | Faglærer i IBE160 (utarbeidet med KI-støtte) |
| **Dato** | 2026-10-06 |

## Samlet vurdering

- **Godt utgangspunkt med justeringer.** Gruppen kan gå videre og innarbeide punktene under.

**Det som er bra:**

1. Briefen har en svært konkret bruker og situasjon: havnevakta ved Bergen Havns Maritime Operations Center, med scenarioet «skipet melder ETA 08:00, neste fartøy skal til samme kai 14:00 – kommer det første faktisk 08:00 eller 11:30?». Det gjør det lett å forstå hva produktet skal hjelpe med.
2. Suksesskriteriene er målbare og ærlige. Dere har beregnet en kalibrert baseline på ekte data (46,6 % innenfor ±30 minutter og 24,3 % som bommer med over 2 timer for ikke-rutegående trafikk), valgt hovedmetrikk med begrunnelse, og lovet å rapportere et negativt resultat i stedet for å omdefinere suksess. Beslutningsloggen i `docs/beslutninger/` og reserveplanen i fem nivåer er godt prosessmateriale.

**De viktigste endringene:**

1. Planlegg hvordan sensor kan kjøre appen. Datasettet ligger i `pipeline/data/`, som er gitignored, og AIS-hentingen tar «flere timer» med ca. 8 000 API-kall. Sensor må kunne starte dashbordet uten å hente alt på nytt, for eksempel med et lite, versjonert utdrag av datasettet og en lagret modell. Det generative AI-laget for den daglige briefen trenger også en testmodus uten deres API-nøkkel.
2. Gi applikasjonen mer plass i planen. I `docs/plan.md` får dashbordet og AI-laget bare ca. tre uker (10.–30. november), etter fem uker med modellarbeid. Del 1 vurderer appen sensor kan kjøre, inkludert design og brukeropplevelse. Lag en enkel versjon av dashbordet tidlig (gjerne med baseline-prediksjonene), og forbedre den parallelt med modellen.
3. Hold én gjeldende brief. `docs/brief.md` (engelsk) og `docs/brief.no.md` (norsk) er nå ulike – den norske mangler blant annet avgrensningen til ikke-rutegående trafikk og tallene som skal slås. Bestem hvilken som gjelder, og oppdater eller fjern den andre. Ta også stilling til de to åpne punktene øverst i den norske versjonen (tittel og språk).

## Vanskelighetsgrad og gjennomførbarhet

### Vurdert vanskelighetsgrad

- **Vanskelig**

**Sammenlignbart med:** 4) KI-støttet MRP II, delmodul 4.1 Prognoser og Demand Management (vanskelig). Som prognosemodulen handler prosjektet om å lage prediksjoner fra historiske data, med metodevalg, avvikshåndtering og evaluering mot en baseline. I tillegg kommer egen utledning av fasit fra rå AIS-spor, et generativt AI-lag og et kartbasert dashbord.

**Begrunnelse:**

| Faktor | Nivå (lav / middels / høy) | Kommentar |
|---|---|---|
| Domenelogikk – hvor mange og hvor kompliserte regler og beregninger må stemme? | Høy | Utledning av faktisk ankomst (sone og fartsterskel), kalibrering per trafikktype, kronologisk splitt, prediksjon på 6t/24t og evaluering med presisjon/recall. Alt må være metodisk riktig. |
| Datamodell – antall entiteter og relasjoner mellom dem | Middels | Seilas, fartøy (MMSI), AIS-posisjon, utledet ankomst, prediksjon og daglig brief. Lagres i dag som CSV-filer. |
| Brukere, roller og innlogging | Lav | Bevisst ingen innlogging i v1, med god begrunnelse (åpne data, én rolle). |
| KI-funksjonalitet i appen, f.eks. kall til språkmodell, prompts i koden og håndtering av usikre svar | Høy | En maskinlæringsmodell pluss et generativt lag som skal begrunne hvert forventet avvik. Begrunnelsene må bygge på modellens faktiske input, ellers kan KI-en finne på årsaker. |
| Integrasjoner og eksterne tjenester, f.eks. API-er, betaling og e-post | Middels | Kystdatahuset og eventuelt BarentsWatch, pluss en språkmodell. Hentingen er allerede bygget og kjørt. |
| Sanntid, samtidighet eller flere brukere som påvirker hverandre | Middels | Historiske data i v1, men «live pipeline» er uttalt ambisjon. Lav hvis live-delen holdes utenfor. |
| Filhåndtering, f.eks. opplasting, PDF-lesing og eksport | Lav | Ingen opplasting. Store mellomfiler, men håndtert med caching. |
| Sikkerhet og personvern | Lav | Åpne data (NLOD) og ingen personopplysninger. BarentsWatch-nøkler skal ligge i miljøvariabler – godt beskrevet. |

**Hva vanskelighetsgraden betyr for dere:**

- _Vanskelig:_ Et vanskelig prosjekt gir større mulighet for toppkarakter, men også større risiko. Definer en minimal versjon som sikkert kan bli ferdig: et dashbord som viser predikerte ankomster mot rapportert ETA for en valgt dag i testperioden, med én modell og én horisont. Legg 24t-horisont, kart og generativ brief i tydelige trinn etterpå hvis tiden blir knapp.

### Gjennomførbarhet med BMAD og Claude Code

Dere skal planlegge med BMAD (product brief → PRD → arkitektur → epics og stories) og implementere med Claude Code. Vurderingen under tar hensyn til at det må være tid til hele denne flyten, og til testing, retting og README til slutt.

| Spørsmål | Vurdering (OK / risiko / stor risiko) | Kommentar |
|---|---|---|
| **Tid og omfang** – kan v1 realistisk bli ferdig og stabil i løpet av semesteret, med tid til flere iterasjoner? | Risiko | Datapipelinen er allerede ferdig, noe som er et stort forsprang. Risikoen ligger i at modell, AI-lag, kart og dashbord skal bli ferdig etter hverandre på ca. åtte uker. |
| **BMAD-flyten** – er briefen konkret nok til at PRD, arkitektur og stories kan lages uten store hull, og blir det overkommelig mange stories? | Risiko | Briefen er svært konkret om data og metrikk, men PRD, arkitektur og epics er ikke laget ennå, og planen går rett fra pipeline til modell. Lag PRD og stories for dashbordet og AI-laget før dere bygger dem, så sporbarheten fra plan til kode blir tydelig. |
| **Egnet for Claude Code** – bruker løsningen en vanlig, godt dokumentert teknologistakk som Claude Code håndterer godt, eller krever den nisjeteknologi, spesialmaskinvare eller mye manuell konfigurasjon? | OK | Python, vanlige ML-biblioteker og et webdashbord er godt dokumentert. Pipelinen bruker bare standardbiblioteket. |
| **Kontroll på KI-ens arbeid** – kan gruppen selv avgjøre om koden gjør det riktige? Krever domenet kunnskap gruppen ikke har, f.eks. avanserte beregninger eller fagregler, så er det vanskelig å kvalitetssikre. | OK | Dere har vist at dere kontrollerer resultatene: kalibrering, skjevhetssjekk, enighet mellom to uavhengige etiketter (97,0 %) og dokumenterte metodevalg. Fortsett slik med modellen. |
| **Testbarhet** – finnes det tydelige regler og forventede resultater som tester kan skrives mot? | OK | Ankomstregler, kalibrering og metrikker kan testes med små, konstruerte AIS-spor med kjent fasit. Legg inn automatiske tester for pipelinen – det finnes ingen ennå. |
| **Kjørbar for sensor** – kan appen kjøres lokalt etter README, uten gruppens nøkler, betalte kontoer eller egen infrastruktur? | Stor risiko | README beskriver pipelinen godt, men full henting tar timer, data er gitignored, og AI-laget krever nøkkel. Uten et versjonert utdrag og testmodus får ikke sensor kjørt appen innenfor rimelig tid. |
| **Avhengigheter og kostnader** – krever løsningen betalte API-er, f.eks. språkmodeller, og finnes det en plan for kostnad, testmodus eller mock-data? | Risiko | Kildedataene er gratis. Språkmodell for den daglige briefen er ikke valgt, og det finnes ingen plan for kostnad eller testmodus. |

**Konklusjon om gjennomførbarhet:**

- **Gjennomførbart med justert omfang.** Se forslagene under.

**Forslag til justering av omfang eller vanskelighetsgrad:**

1. Flytt «live pipeline» helt ut av v1, slik at v1 bare bygger på det låste historiske datasettet. Dashbordet kan «spille av» en valgt dag i testperioden. Det er nok til å vise verdien for havnevakta.
2. Start med én horisont (for eksempel 6t) og én modell. La det generative AI-laget lage begrunnelser bare ut fra modellens input (skipstype, historisk avvik, tid på døgnet osv.), og vis disse ved siden av teksten slik at havnevakta – og sensor – kan se at begrunnelsen stemmer.

## Hvorfor product brief er viktig for mappen

Product brief er utgangspunktet for PRD, arkitektur, stories og til slutt koden. Del 1 av mappen vurderes blant annet på om sensor kan følge en sporbar vei fra plan til ferdig app. Den vurderes også på om appen gjør det dere har beskrevet, om den er testet, om den er godt designet, og om den kan kjøres etter README. Et uklart, for stort eller for lite brief gjør alt dette vanskeligere senere. Det er mye enklere å rette nå enn sent i semesteret.

## 1. Gjennomgang av briefens deler

| Del av brief | Status | Kommentar |
|---|---|---|
| Executive Summary – er det klart hva appen er, og hvilket problem den løser? | OK | Tydelig hva verktøyet gjør, for hvem, og hvorfor det er aktuelt nå (koblingen til «Digital tvilling i havn»). |
| The Problem – er problemet konkret, med reelle situasjoner og brukere? | OK | Konkret scenario og ærlig om at smerten ved Bergen Havn er en slutning fra bransjemønsteret, ikke bekreftet. |
| The Solution – beskriver løsningen brukeropplevelsen, ikke bare teknologi? | Juster | Mye handler om pipeline og modell. Beskriv tydeligere hva havnevakta ser og gjør i dashbordet en vanlig morgen – det er grunnlaget for UX-arbeidet. |
| What Makes This Different – er vurderingen ærlig og realistisk? | OK | Ærlig om at det ikke finnes en teknisk vollgrav, og godt forankret i konkurrenter og forskning. |
| Who This Serves – er primærbrukerne tydelige, og vet vi hva de trenger? | OK | Primær- og sekundærbruker er tydelige, og det er eksplisitt hvem som ikke er v1-brukere. |
| Success Criteria – kan kriteriene faktisk sjekkes eller testes? | OK | Målbare tall å slå, med begrunnet metrikk. Produktkriteriet om den daglige briefen kan gjøres litt mer konkret, for eksempel hva briefen minst skal inneholde. |
| Scope – er det klart hva som er med i første versjon, og hva som ikke er det? | Juster | Tydelig «INN» og «UT». Live-data står både som ambisjon i løsningen og som «UT» i Scope – gjør det entydig. Rammen «~12 uker» bør stemme med `plan.md`. |
| Vision – henger visjonen sammen med resten uten å blåse opp omfanget? | OK | Flere havner, API og liggetid er tydelig plassert etter semesteret. |

## 2. Utgangspunkt for del 1 av mappen

Punktene følger kriteriene i sensorveiledningen for del 1. Vektene i parentes viser hvor mye hvert kriterium teller i del 1.

| Kriterium i del 1 | Hva briefen bør legge til rette for | Status | Kommentar |
|---|---|---|---|
| **1. Prosess og KI-styring** (30 %) | Brief som er presis nok til at PRD og stories kan bygges direkte på den, slik at krav kan spores fra brief til kode. | Juster | Brief, beslutningslogg og commits viser en sporbar prosess. Det som mangler, er PRD, arkitektur og epics/stories. Lag dem før modell- og dashbordarbeidet, og lagre gjerne KI-øktene. |
| **2. Funksjonalitet og omfang** (20 %) | Realistisk omfang for gruppen og semesteret: en tydelig kjerneflyt som kan bli ferdig og stabil, og nok innhold til å vise reell funksjonalitet. | Juster | Rikelig innhold. Pass på at det sensor ser – dashbordet – blir ferdig og stabilt, ikke bare modellen. |
| **3. Kvalitetssikring og testing** (15 %) | Suksesskriterier og funksjoner som er konkrete nok til å bli testtilfeller. | OK | Svært gode, målbare kriterier og dokumentert kontroll av data. Legg til automatiske tester for pipeline og modell-evaluering. |
| **4. Design og brukeropplevelse** (10 %) | Tydelige brukere og brukssituasjoner som designet kan bygges rundt, gjerne med de viktigste skjermbildene eller flytene skissert. | Juster | Brukeren er tydelig, men dashbordet er lite beskrevet. Skissér skjermbildet for den daglige briefen (liste, kart og begrunnelse) i et UX-steg. |
| **5. Kodekvalitet og arkitektur** (10 %) | Teknologivalg som er begrunnet og ikke mer komplekse enn appen trenger. | OK | Enkle valg (standardbibliotek, CSV, caching) med god begrunnelse. Velg dashbordteknologi like enkelt. |
| **6. README og kjørbarhet** (10 %) | Løsning som andre kan kjøre lokalt uten betalte kontoer, og uten tilgang til gruppens egne tjenester og nøkler. | Endre | README er god for pipelinen, men appen kan ikke kjøres raskt uten data og nøkkel. Legg ved et lite datautdrag og en lagret modell, og lag testmodus for AI-laget. |
| **7. Ryddighet i repoet** (5 %) | En plan for hvor hemmeligheter, testdata og dokumentasjon skal ligge. | Juster | God struktur i `docs/` og `pipeline/`, og nøkler er planlagt i miljøvariabler. Rydd i dupliserte briefer, og vurder om kopiene av kursmateriale i `docs/kilder/` hører hjemme i et offentlig repo. |

## 3. Neste steg for gruppen

1. Gjør `docs/brief.md` til gjeldende brief (eller oppdater den norske), og ta tittel og live-data-spørsmålet inn i briefen.
2. Lag PRD, arkitektur og epics/stories med BMAD som dekker modell, AI-lag og dashbord – inkludert hvordan sensor kjører appen med et versjonert datautdrag og testmodus.
3. Bygg en første, enkel versjon av dashbordet med baseline-prediksjonene allerede nå, slik at design og README kan forbedres i flere runder parallelt med modellarbeidet.

Oppdater product brief i repoet når dere har gjort endringene, slik at historikken viser hvordan planen utviklet seg. Det er en del av prosessen sensor ser etter.
