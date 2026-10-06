# Tilbakemelding på product brief

| | |
|---|---|
| **Gruppe** | G73 – G73-hoffstrom-lopez-reed |
| **Product brief** | `docs/brief.no.md` (commit `ad2ffca`, frontmatter `updated: 2026-09-27`). Den norske versjonen av briefen. Den gjeldende engelske `docs/brief.md` har fått egen tilbakemelding i `docs/tilbakemelding-product-brief.md`. |
| **Tilbakemelding fra** | Faglærer i IBE160 (utarbeidet med KI-støtte) |
| **Dato** | 2026-10-06 |

## Samlet vurdering

- **Bør revideres før dere går videre.** Rett punktene markert «Endre» før dere lager PRD og arkitektur.

`docs/brief.no.md` er en eldre norsk oversettelse av `docs/brief.md`, ikke en alternativ idé. Produktet, brukeren og avgrensningen er de samme. Den engelske versjonen ble oppdatert 28. september med resultater fra fullbatchen, men den norske ble ikke oppdatert. Derfor mangler den norske versjonen nå det som gjør den engelske sterk. Det gjelder de målbare suksesskriteriene, avgrensningen til ikke-rutegående trafikk, risikoene og «Data inn / Data ut». I tillegg beskriver den «Digital tvilling i havn» som om prosjektet pågår. Selve ideen vurderes likt i begge versjonene. Vurderingen «Bør revideres» skyldes at denne fila ikke kan brukes som grunnlag for PRD slik den står nå. README lenker til begge versjonene. Bestem derfor hvilken brief som gjelder, og oppdater, merk eller fjern den andre (se kriterium 1 og 7).

**Det som er bra:**

1. Den norske versjonen har samme konkrete bruker og situasjon som den engelske. Brukeren er havnevakta ved Bergen Havns Maritime Operations Center, med scenarioet «skipet melder ETA 08:00, neste fartøy skal til samme kai 14:00». Det gjør en norsk brief lett å forstå for både gruppen og sensor.
2. Scope er tydelig delt i «INN» og «UT». Begrunnelsen for at v1 ikke har innlogging er god: Dataene er åpne (NLOD), appen behandler ingen personopplysninger og har én rolle. Rollebasert tilgang, flere havner og API er bevisst utsatt.

**De viktigste endringene:**

1. Bestem én gjeldende brief. Enten oppdaterer dere den norske versjonen slik at den blir lik `docs/brief.md`, eller så fjerner dere den eller merker den tydelig som utdatert. Gjør det samme med lenken i README. I dag finnes det to versjoner med ulike suksesskriterier. Da er det uklart hvilke krav PRD og stories skal spores tilbake til.
2. Suksesskriteriene i denne versjonen er de gamle. Her står det «prosentvis forbedring over den selvberegnede baselinen» målt på MAE, uten noe tall å slå. Den engelske versjonen bruker andel innenfor ±30 minutter som hovedmetrikk og presisjon/recall på `er_forsinket` som sekundærmetrikk. Den har også konkrete tall: 46,6 % innenfor ±30 min og 24,3 % som bommer med over 2 timer, for ikke-rutegående trafikk. Kriteriene i den norske versjonen kan ikke brukes som testtilfeller.
3. Rett opp utdaterte fakta og lukk de åpne punktene. Den norske teksten sier at Bergen Havn «allerede er en navngitt deltaker» i «Digital tvilling i havn». Den engelske versjonen har rettet dette: Prosjektet ble avsluttet i november 2024. Ta også stilling til de to åpne punktene øverst i fila (tittel og språk), og fjern pausemerknaden fra 21. september.

## Vanskelighetsgrad og gjennomførbarhet

### Vurdert vanskelighetsgrad

- **Vanskelig**

**Sammenlignbart med:** 4) KI-støttet MRP II, delmodul 4.1 Prognoser og Demand Management (vanskelig). Prosjektet ligner prognosemodulen fordi det skal lage prediksjoner fra historiske data. Det krever metodevalg, håndtering av avvik og evaluering mot en baseline. I tillegg skal dere selv utlede fasiten fra rå AIS-spor, lage et generativt AI-lag og bygge et kartbasert dashbord. Vurderingen er den samme som for `docs/brief.md`, fordi begge versjonene beskriver det samme produktet.

**Begrunnelse:**

| Faktor | Nivå (lav / middels / høy) | Kommentar |
|---|---|---|
| Domenelogikk – hvor mange og hvor kompliserte regler og beregninger må stemme? | Høy | Faktisk ankomst skal utledes med havneområde-polygon og fartsterskel. Deretter skal dere bygge et merket avviksdatasett og predikere ankomst 6 og 24 timer frem. Denne versjonen beskriver ikke kalibreringen per trafikktype. Den er nødvendig for at baselinen skal bli rettferdig. |
| Datamodell – antall entiteter og relasjoner mellom dem | Middels | Datamodellen har seilas, fartøy (MMSI), AIS-posisjon, utledet ankomst, prediksjon og daglig brief. Denne versjonen mangler oversikten «Data inn / Data ut» som den engelske har. |
| Brukere, roller og innlogging | Lav | Det er bevisst ingen innlogging i v1, og begrunnelsen er god. Dere bruker eventuelt én delt HTTP Basic Auth hvis demoen skal ligge på nett. |
| KI-funksjonalitet i appen, f.eks. kall til språkmodell, prompts i koden og håndtering av usikre svar | Høy | Appen har både en maskinlæringsmodell og et generativt lag som skal begrunne hvert forventet avvik. Briefen sier ikke hvordan dere hindrer at språkmodellen finner på årsaker som modellen ikke bygger på. |
| Integrasjoner og eksterne tjenester, f.eks. API-er, betaling og e-post | Middels | Integrasjonene er Kystdatahuset, BarentsWatch som reserve og en språkmodell som ikke er valgt. Hentingen fra Kystdatahuset er allerede bygget i `pipeline/`. |
| Sanntid, samtidighet eller flere brukere som påvirker hverandre | Middels | V1 bygger på historiske data, men «live pipeline» står som uttalt ambisjon. Nivået er lavt hvis live-delen holdes helt utenfor v1. |
| Filhåndtering, f.eks. opplasting, PDF-lesing og eksport | Lav | Appen har ingen opplasting. Mellomfilene blir store, men pipelinen cacher dem. |
| Sikkerhet og personvern | Lav | Dataene er åpne, og appen behandler ingen personopplysninger. Begrunnelsen står i Scope og i addendumet. |

**Hva vanskelighetsgraden betyr for dere:**

- _Vanskelig:_ Et vanskelig prosjekt gir større mulighet for toppkarakter, men også større risiko. Definer en minimal versjon som sikkert kan bli ferdig. Den kan være et dashbord som viser predikerte ankomster mot rapportert ETA for en valgt dag i testperioden, med én modell og én horisont. Legg 24-timershorisonten, kartet og den generative briefen i tydelige trinn etterpå hvis tiden blir knapp. Denne versjonen sier «~12 uker», mens `docs/brief.md` sier «~10 uker» og `docs/plan.md` regner med omtrent 11 uker. Bli enige om én tidsramme.

### Gjennomførbarhet med BMAD og Claude Code

Dere skal planlegge med BMAD (product brief → PRD → arkitektur → epics og stories) og implementere med Claude Code. Vurderingen under tar hensyn til at det må være tid til hele denne flyten, og til testing, retting og README til slutt.

| Spørsmål | Vurdering (OK / risiko / stor risiko) | Kommentar |
|---|---|---|
| **Tid og omfang** – kan v1 realistisk bli ferdig og stabil i løpet av semesteret, med tid til flere iterasjoner? | Risiko | Datapipelinen er allerede ferdig. Men modellen, AI-laget, kartet og dashbordet skal bygges etter hverandre i løpet av omtrent åtte uker. Denne versjonen mangler i tillegg risikoavsnittet der dere selv peker på den stramme tidsrammen. |
| **BMAD-flyten** – er briefen konkret nok til at PRD, arkitektur og stories kan lages uten store hull, og blir det overkommelig mange stories? | Stor risiko | PRD bygd på denne versjonen ville fått gamle mål og mangle avgrensningen til ikke-rutegående trafikk. Lag PRD fra den gjeldende briefen, og sørg for at det bare finnes én. |
| **Egnet for Claude Code** – bruker løsningen en vanlig, godt dokumentert teknologistakk som Claude Code håndterer godt, eller krever den nisjeteknologi, spesialmaskinvare eller mye manuell konfigurasjon? | OK | Python, vanlige ML-biblioteker og et webdashbord er godt dokumentert. Pipelinen bruker bare standardbiblioteket. |
| **Kontroll på KI-ens arbeid** – kan gruppen selv avgjøre om koden gjør det riktige? Krever domenet kunnskap gruppen ikke har, f.eks. avanserte beregninger eller fagregler, så er det vanskelig å kvalitetssikre. | OK | Beslutningsloggen i `docs/beslutninger/` viser at dere kontrollerer resultatene, for eksempel med kalibrert baseline og skjevhetssjekk. Disse kontrollene er bare beskrevet i den engelske briefen. |
| **Testbarhet** – finnes det tydelige regler og forventede resultater som tester kan skrives mot? | Risiko | Ankomstreglene kan testes med små, konstruerte AIS-spor med kjent fasit. Suksesskriteriet i denne versjonen har likevel ikke noe konkret mål å teste mot. Det finnes ingen automatiske tester ennå. |
| **Kjørbar for sensor** – kan appen kjøres lokalt etter README, uten gruppens nøkler, betalte kontoer eller egen infrastruktur? | Stor risiko | Data i `pipeline/data/` er gitignored, en full henting tar timer, og AI-laget krever en nøkkel. Uten et versjonert datautdrag og en testmodus får ikke sensor kjørt appen innen rimelig tid. |
| **Avhengigheter og kostnader** – krever løsningen betalte API-er, f.eks. språkmodeller, og finnes det en plan for kostnad, testmodus eller mock-data? | Risiko | Kildedataene er gratis. Dere har ikke valgt språkmodell for den daglige briefen, og det finnes ingen plan for kostnad eller testmodus. |

**Konklusjon om gjennomførbarhet:**

- **Gjennomførbart med justert omfang.** Se forslagene under.

**Forslag til justering av omfang eller vanskelighetsgrad:**

1. Flytt «live pipeline» helt ut av v1, slik at v1 bare bygger på det låste historiske datasettet. Dashbordet kan «spille av» en valgt dag i testperioden. I denne versjonen står live-data både som ambisjon under «Løsningen» og som «UT» i Scope. Gjør det entydig.
2. Start med én horisont, for eksempel 6 timer, og én modell. La det generative laget begrunne avvik bare ut fra modellens input, for eksempel skipstype, historisk avvik og tid på døgnet. Vis disse opplysningene ved siden av teksten.

## Hvorfor product brief er viktig for mappen

Product brief er utgangspunktet for PRD, arkitektur, stories og til slutt koden. Del 1 av mappen vurderes blant annet på om sensor kan følge en sporbar vei fra plan til ferdig app. Den vurderes også på om appen gjør det dere har beskrevet, om den er testet, om den er godt designet, og om den kan kjøres etter README. Et uklart, for stort eller for lite brief gjør alt dette vanskeligere senere. Det er mye enklere å rette nå enn sent i semesteret.

## 1. Gjennomgang av briefens deler

| Del av brief | Status | Kommentar |
|---|---|---|
| Executive Summary – er det klart hva appen er, og hvilket problem den løser? | Juster | Det er tydelig hva verktøyet gjør og for hvem. Teksten sier at Bergen Havn «allerede er en navngitt deltaker» i «Digital tvilling i havn». Den engelske versjonen har rettet dette: Prosjektet ble avsluttet i november 2024. |
| Problemet – er problemet konkret, med reelle situasjoner og brukere? | Juster | Scenarioet er konkret, og dere er ærlige om at smerten er en slutning fra bransjemønsteret. Avsnittet om «Precision on scale» mangler. Det skiller offentlige kaier fra private terminaler og gjør pilotens omfang tydelig. |
| Løsningen – beskriver løsningen brukeropplevelsen, ikke bare teknologi? | Juster | Det meste av teksten handler om pipelinen og modellen. Beskriv hva havnevakta ser og gjør i dashbordet en vanlig morgen. Teksten er lik den engelske, så rett begge hvis dere beholder to versjoner. |
| Hva gjør dette annerledes – er vurderingen ærlig og realistisk? | OK | Dere er ærlige om at det ikke finnes noen teknisk vollgrav. Teksten bygger på både konkurrenter og forskning. Den engelske versjonen har i tillegg kildelenker. |
| Hvem dette tjener – er primærbrukerne tydelige, og vet vi hva de trenger? | OK | Primær- og sekundærbruker er tydelige, og det står eksplisitt hvem som ikke er brukere i v1. |
| Suksesskriterier – kan kriteriene faktisk sjekkes eller testes? | Endre | Målet er en uspesifisert «prosentvis forbedring» av MAE. Det er nettopp den metrikken dere senere fant ut at er ustabil på denne fordelingen. Erstatt kriteriene med de gjeldende: andel innenfor ±30 min, presisjon/recall på `er_forsinket`, avgrensning til ikke-rutegående trafikk og konkrete tall å slå. |
| Scope – er det klart hva som er med i første versjon, og hva som ikke er det? | Juster | Delingen i «INN» og «UT» er tydelig. Rammen «~12 uker» stemmer ikke med `docs/brief.md` (~10 uker) eller `docs/plan.md` (~11 uker). Live-data står både som ambisjon og som «UT». |
| Visjon – henger visjonen sammen med resten uten å blåse opp omfanget? | OK | Flere havner, API og liggetid er tydelig plassert etter semesteret. |

## 2. Utgangspunkt for del 1 av mappen

Punktene følger kriteriene i sensorveiledningen for del 1. Vektene i parentes viser hvor mye hvert kriterium teller i del 1.

| Kriterium i del 1 | Hva briefen bør legge til rette for | Status | Kommentar |
|---|---|---|---|
| **1. Prosess og KI-styring** (30 %) | Brief som er presis nok til at PRD og stories kan bygges direkte på den, slik at krav kan spores fra brief til kode. | Endre | Krav må kunne spores fra én brief. Med to versjoner som har ulike mål, blir det uklart for sensor hvilken plan koden skal måles mot. Det at briefen har utviklet seg, er derimot godt prosessmateriale. Vis det i git-historikken og beslutningsloggen, ikke som to filer som lever side om side. |
| **2. Funksjonalitet og omfang** (20 %) | Realistisk omfang for gruppen og semesteret: en tydelig kjerneflyt som kan bli ferdig og stabil, og nok innhold til å vise reell funksjonalitet. | Juster | Briefen har rikelig med innhold. Pass på at dashbordet blir ferdig og stabilt, siden det er det sensor ser, og ikke bare modellen. Tidsrammen må være lik i alle dokumentene. |
| **3. Kvalitetssikring og testing** (15 %) | Suksesskriterier og funksjoner som er konkrete nok til å bli testtilfeller. | Endre | Det gamle MAE-kriteriet uten mål kan ikke bli et testtilfelle. Kriteriene i `docs/brief.md` kan det. |
| **4. Design og brukeropplevelse** (10 %) | Tydelige brukere og brukssituasjoner som designet kan bygges rundt, gjerne med de viktigste skjermbildene eller flytene skissert. | Juster | Brukeren er tydelig, men dashbordet er lite beskrevet. Skissér skjermbildet for den daglige briefen, med liste, kart og begrunnelse, i et UX-steg. |
| **5. Kodekvalitet og arkitektur** (10 %) | Teknologivalg som er begrunnet og ikke mer komplekse enn appen trenger. | OK | Valgene er enkle: standardbiblioteket, CSV og caching. Velg dashbordteknologi som er like enkel. |
| **6. README og kjørbarhet** (10 %) | Løsning som andre kan kjøre lokalt uten betalte kontoer, og uten tilgang til gruppens egne tjenester og nøkler. | Endre | Appen kan ikke kjøres raskt uten data og nøkkel. Legg ved et lite datautdrag og en lagret modell, og lag en testmodus for AI-laget. README lenker i dag til begge briefene uten å si hvilken som gjelder. |
| **7. Ryddighet i repoet** (5 %) | En plan for hvor hemmeligheter, testdata og dokumentasjon skal ligge. | Juster | Strukturen i `docs/` og `pipeline/` er god. En utdatert kopi av briefen ved siden av den gjeldende er en «gammel versjon» av den typen sensor ser etter. Fila viser også til `.memlog.md`, som ligger under `_bmad-output/`. Rydd slik at det er tydelig hva som gjelder. |

## 3. Neste steg for gruppen

1. Bestem at `docs/brief.md` er gjeldende brief. Fjern deretter `docs/brief.no.md`, eller merk den øverst som «utdatert oversettelse – se docs/brief.md». Oppdater lenken i README. Velger dere heller en norsk brief, må alle endringene fra 28. september oversettes.
2. Ta tittel, språk og spørsmålet om live-data inn i den gjeldende briefen. Fjern pausemerknaden, og bli enige om én tidsramme.
3. Lag deretter PRD, arkitektur og epics/stories med BMAD, bygd på den gjeldende briefen. De bør også dekke hvordan sensor kjører appen med et versjonert datautdrag og en testmodus for AI-laget.

Oppdater product brief i repoet når dere har gjort endringene, slik at historikken viser hvordan planen utviklet seg. Det er en del av prosessen sensor ser etter.
