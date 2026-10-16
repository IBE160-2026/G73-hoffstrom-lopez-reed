---
title: "Produktbrief: AIS-basert ankomstprediksjon (arbeidstittel)"
status: draft
created: 2026-09-17
updated: 2026-10-16
---

# Produktbrief: AIS-basert ankomstprediksjon (arbeidstittel)

## Executive Summary

For havnevakta ved Bergen Havns Maritime Operations Center bygger vi et beslutningsstøtteverktøy som predikerer når et skip faktisk vil ankomme — ikke bare hva det har rapportert — slik at kaidisponering kan planlegges mot et tall som er verdt å stole på, i stedet for en selvrapportert ETA. I dag disponerer havnevakta kaiplass fortløpende basert på skipenes rapporterte ETA-er, uten noen pålitelig måte å vite på forhånd hvilke rapporter som kan stoles på og hvilke som vil vise seg å være timevis feil. Gapet er relevant nå fordi det underliggende problemet allerede har hatt institusjonell oppmerksomhet i Norge: Bergen Havn var navngitt deltaker i Kystverkets Oslo Havn-ledede initiativ "Digital tvilling i havn" (10,5 MNOK, ca. 20 norske havner, avsluttet november 2024), hvis mål var å strømlinjeforme skipsanløp og redusere ventetid i havn. Det prosjektet bygget digital tvilling- og kartinfrastruktur, ikke et operativt ETA-prediksjonsverktøy, og problemet det siktet mot er ikke tatt opp igjen siden det ble avsluttet — dette prosjektet bygger prediksjonslaget ingen har levert siden, ved bruk av de samme åpne AIS-dataene Kystverket allerede publiserer gjennom Kystdatahuset.

## Problemet

Bergen Havn styrer kaidisponering gjennom havnevakta (vaktoffiseren) i sitt Maritime Operations Center — en skiftbasert rolle som fortløpende tildeler kaiplass basert på skipenes selvrapporterte ETA-er. Jobben, i ett konkret scenario: et skip melder ETA 08:00; neste fartøy skal til samme kai 14:00; kommer det første skipet faktisk 08:00, eller 11:30 — og må noe omdisponeres akkurat nå?

Rapporterte ETA-er er kjent bransje-bredt for å avvike fra faktisk ankomst, fordi de ikke gjenspeiler kai-, los- eller slepebåtberedskap — IMOs Just-In-Time Arrival Guide navngir akkurat denne mekanismen: et skip kan være helt "i rute" etter sin egen melding og likevel forårsake unødvendig venting eller en hastig omdisponering av kai. Ingen offentlig dokumentasjon bekrefter denne konkrete smerten ved Bergen Havn spesifikt — det forblir en resonnert slutning fra det generelle bransjemønsteret, ikke en påstått fakta. Havna forpliktet reelle midler til det tilstøtende problemet i fortid ("Digital tvilling i havn", avsluttet nov. 2024, se Executive Summary) — et bevis på at institusjonen *har* ansett dagens ETA-informasjon som utilstrekkelig å planlegge mot, ikke bevis på et aktivt initiativ i dag.

**Presisjon på størrelse:** Bergen Havn omtales ofte som Norges største godshavn og største cruisehavn, målt i tonnasje — men mesteparten av den godstonnasjen går over privat drevne terminaler, ikke de offentlige kaiene havnevakta faktisk disponerer. Smerten denne briefen beskriver gjelder trafikken over de offentlige kaiene under havnevaktas egen myndighet, som er en reell, men smalere andel av havnas totale tonnasjetall. Dette skillet er viktig for å avgrense piloten riktig, og bør ikke viskes ut ved å sitere havnas totale størrelse som om alt var adresserbart.

## Løsningen

Et beslutningsstøtteverktøy som predikerer når et skip faktisk vil ankomme Bergen Havn — 6 og 24 timer i forkant — bygget på åpne AIS- og seilasdata fra Kystverkets Kystdatahuset. Siden rådataene bare inneholder hvert skips selvrapporterte ETA, utleder pipelinen faktiske ankomsthendelser fra AIS-sporene (soneinngang i havneområdet, kalibrert per fartøystype — se tillegget) for å bygge et merket datasett over avviket mellom rapportert og reell ankomst. En modell trent på dette datasettet produserer 6t/24t-prediksjonene, målt mot skipets egen rapporterte ETA — referansen hver prediksjon må slå. Et generativt AI-lag gjør hver dags prediksjoner om til en kort daglig brief for havnevakta: et kart pluss en begrunnelse for hvert forventede avvik, slik at operatøren ser ikke bare et tall, men hvorfor det trolig er feil.

v1 bygger utelukkende på det låste historiske datasettet (8 094 seilaser, jan. 2024–mars 2026 — se tillegget), ikke en direktestrøm: dashbordet lar havnevakta "spille av" en valgt dag eller periode fra det datasettet og se modellens prediksjoner mot hva som faktisk skjedde. Åpent uten innlogging (se Scope).

## Hva gjør dette annerledes

Ingen AIS-ETA-leverandør funnet i markedet — Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic — publiserer en revidert, reproduserbar nøyaktighetsbenchmark; påstandene deres er markedsføringstekst, ikke dokumentert metodikk. Det er i seg selv en legitim differensiator: dette prosjektet måler seg selv, offentlig, mot den ene ærlige baseline som finnes — skipets egen rapporterte ETA. Kystdatahuset er en datakilde, ikke et prediksjonsprodukt, så det finnes ikke noe eksisterende verktøy bygget på akkurat disse dataene i dag.

Den nærmeste nordiske akademiske presedensen, en NTNU-masteroppgave om AIS-basert prediksjon av liggetid ved Mongstad ([ntnuopen.ntnu.no/handle/11250/2780189](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2780189)), kom til en forsiktig konklusjon ("a convoluted task with many hidden variables") — et ærlig referansepunkt, ikke en list dette prosjektet påstår å klare enkelt. En nærmere metodisk presedens finnes utenfor Norge: en Hong Kong-studie ([ScienceDirect, S1474034625009036](https://www.sciencedirect.com/science/article/pii/S1474034625009036)) som kombinerte AIS-spor med anløpsdata via XGBoost kuttet ETA-feilen med 52,98 % mot skipets egen rapporterte ETA, med en nesten identisk tilnærming ved en annen havn — reelt bevis på at metoden virker, ikke et løfte om at denne gruppen vil matche det tallet.

Ærlig sagt: det finnes ingen teknisk moat her. Fortrinnet er å være først til å rette akkurat denne metoden mot Bergen Havns konkrete ETA-nøyaktighetsproblem, og å være transparent om tallet som kommer ut, i stedet for å påstå ett.

## Hvem dette tjener

**Primær: havnevakta i Bergen Havns Maritime Operations Center** (offentlig døgnkontakt: havnevakt@bergenhavn.no) — en skiftbasert rolle som fortløpende tildeler kaiplass. Suksess for dem: færre siste-liten-omdisponeringer av kai, og et pålitelig svar på "kommer dette skipet faktisk når det sier det skal."

**Sekundær: havnekaptein / driftsleder** — taktisk planlegging over uker fremfor enkeltanløp, med de samme prediksjonene aggregert til mønstre og kapasitetsoversikter.

**Eksplisitt ikke en v1-bruker:** rederier, skipsagenter, vareeiere. Å utvide brukergruppen til dem er en bevisst senere beslutning (se Visjon), ikke en forglemmelse.

## Suksesskriterier

**Funksjonelt — metrikkstruktur.** Reelt pipelinearbeid med å bygge fasit-datasettet (utlede faktisk ankomst fra AIS-spor, på det fulle 8 094-seilas, 27-måneders datasettet — se tillegget) viste at avviksfordelingen er halefordelt: de fleste anløp lander nær rapportert ETA, et mindretall bommer med timer, og ett enkelt feilmål som gjennomsnitter over begge gruppene villeder. Gjennomsnittlig absolutt avvik (MAE) er ustabilt på denne formen — det kan se dramatisk verre ut enn det typiske tilfellet faktisk er, fordi et fåtall ekstreme seilaser dominerer gjennomsnittet. Metrikkstrukturen er derfor:
- **Hovedmål: andel prediksjoner innenfor ±30 minutter av faktisk ankomst.** Tallet en havnevakt faktisk ville stolt på eller ikke.
- **Sekundærmål: presisjon og recall på å flagge anløp som avviker med mer enn 2 timer** ("er_forsinket") — en forstyrrelsesdeteksjons-ramme, evaluert når en trent modell finnes (rapportert ETA alene predikerer null avvik per definisjon, og kan derfor ikke meningsfullt skåres mot dette flagget).
- **Kun støttetall, aldri hovedtallet:** MAE og median absolutt avvik, rapportert for åpenhet, ikke brukt som bestå/ikke bestå-kriterium.

**Avgrenset til ikke-rutegående trafikk alene.** Hovedresultatet rapporteres kun på ikke-rutegående trafikk, med rutegående trafikk (Passasjer) beholdt som kontrollgruppe, ikke slått sammen med hovedtallet. Begrunnelse, bekreftet på hele datasettet: den kalibrerte baselinen plasserer allerede rutegående trafikk på 79,6 % innenfor ±30 minutter, opp fra en naiv 7,4 % — den trafikken er nær løst av en konstant forskyvning alene. Å trene og rapportere mot det samlede datasettet ville latt en modell i stor grad lære å gjenkjenne hvilke anløp som er ferger fremfor å lære reell ankomstusikkerhet, og hovedtallet ville blitt kunstig høyt av den enkle halvparten av flåten. Ikke-rutegående trafikk er der det reelle problemet — og produktets verdi — faktisk ligger.

**Tallet som skal slås:** på ikke-rutegående trafikk når den kalibrerte rapportert-ETA-baselinen **46,6 % innenfor ±30 minutter** (opp fra en naiv 12,9 %), og **24,3 % av anløpene bommer fortsatt med over 2 timer** selv etter kalibrering — kalibrering retter opp det typiske tilfellet, ikke den forstyrrende halen (MAE for denne gruppen beveger seg knapt, 155→136 minutter). Modellens mål er å slå begge tallene: en høyere ±30-minutters-andel, og en vesentlig bedre presisjon/recall på å flagge den ~24 %-forstyrrelseshalen enn baselinen kan tilby (baselinen kan per konstruksjon ikke flagge noe). Hvis modellen ikke klarer én eller begge barrierene, rapporteres det som et resultat, ikke utelates — et ærlig negativt funn er mer nyttig her enn en stille omdefinering av suksess i etterkant.

Rapportert-ETA-baselinen selv skåres på samme måte, kalibrert per fartøystrafikktype (rutegående/annen) fremfor sammenlignet naivt — se tilleggets metodenotater om hvorfor soneinngang-basert fasit trenger denne kalibreringen for i det hele tatt å være sammenlignbar med ETA. Hong Kong-presedensen (52,98 % MAE-reduksjon mot selvrapportert ETA) forblir et nyttig ambisjonsreferansepunkt for hva "bra" ser ut som med denne metoden, ikke et tall å adoptere direkte.

**Datakvalitet.** AIS-dekning logges som en eksplisitt metrikk; seilaser der faktisk ankomst ikke kan utledes droppes og telles, ikke stille interpolert (full reserveplan og dekningstall i tillegget).

**Produkt.** Havnevakta kan lese en daglig brief og forstå, uten å spørre noen, hvilke av morgendagens forventede ankomster de bør mistro, og hvorfor.

## Data Inn / Data Ut

**Data inn:**
- Seilasdata fra Kystdatahusets åpne API (rapportert ETA/ETD, skipsnavn, MMSI, skipstype/-gruppe, lengde, avgangs-/ankomststed) for anløp til Bergen Havn (NOBGO).
- AIS-posisjonsdata (breddegrad, lengdegrad, fart, kurs, tidsstempel) per fartøy fra samme kilde, hentet per MMSI for et tidsvindu rundt hvert anløp.
- BarentsWatch Live AIS som dokumentert reserveløsning dersom Kystdatahuset-arkivet viser seg utilstrekkelig (se tillegget) — ikke utløst (se Scope).

**Data ut:**
- Predikert ankomsttid (6t og 24t horisont, når modellen er trent) per fartøy, målt mot skipets egen rapporterte ETA.
- Et signert forsinkelsesflagg (er_forsinket) for anløp som avviker vesentlig fra kalibrert forventet ankomst.
- En daglig AI-generert forstyrrelsesbrief til havnevakten: kart og begrunnelse per forventet avvik.
- Dekningsgrad- og datakvalitetsmetrikker som følger med hver kjøring, ikke skjules.

## Risiko

- **AIS-dekning under fortøyning.** Rå AIS-data viste seg å ha reelle rapporteringshull nettopp når skip ligger stille ved kai — et sentralt funn i utviklingen av selve datagrunnlaget, ikke en teoretisk bekymring. Håndtert med en egen kontinuitetsplan (tillegget), men gjenstår som en systematisk begrensning i datagrunnlaget.
- **Ukjent dekning for utenlandskflaggede skip.** En vesentlig andel anløp fra utenlandskflaggede fartøy mangler AIS-posisjonsdata i den åpne API-tilgangen. Årsaken er uavklart (tilgangsbegrensning vs. utdatert MMSI-registrering) — se tillegget. Utgjør en skjevhet i datagrunnlaget mot norskflagget trafikk inntil avklart.
- **Halefordelt avvik gjør enkle mål misvisende.** Se Suksesskriterier — MAE og gjennomsnitt kan gi et misvisende bilde av modellens faktiske nytteverdi for havnevakten.
- **Kalibreringsskjevhet.** Baseline-kalibreringen (offset mellom sonepassering og faktisk kaitid) er estimert på et utvalg som systematisk overrepresenterer større, mer rutepregede fartøy, fordi det er de skipstypene der begge etikettene lettest lar seg utlede. Dokumentert, ikke korrigert.
- **Stram tidsramme.** 11 uker til et fungerende produkt er en bevisst ambisiøs ramme for en tre-personers gruppe, gitt at prosjektet har tre tunge delkomponenter (datapipeline, prediksjonsmodell, generativt rapporteringslag). Se Scope for hva som er bevisst utsatt.
- **Ingen teknisk moat.** Se Hva gjør dette annerledes — fortrinnet er utførelse og transparens, ikke en forsvarbar teknisk barriere.

## Scope

**INN — v1 (dette kurset, ~11 uker — stemmer med `docs/plan.md`s tidslinje 27. sep.–15. des.):**
1. Historisk AIS-/seilasinnhenting fra Kystdatahuset — låst: 8 094 seilaser, Bergen Havn, jan. 2024–mars 2026 (se tillegget).
2. Utledning av faktiske ankomsthendelser fra AIS-spor, med en logget dekningsmetrikk (87,1 % oppnådd).
3. En trent modell som predikerer ankomst 6t og 24t i forkant på det låste datasettet, målt mot rapportert ETA.
4. Et nettbasert dashbord som spiller av en valgt dag eller periode fra det låste datasettet: predikerte ankomster, et kart, og en begrunnelse per forventet avvik, generert av et AI-oppsummeringslag.
5. Åpen tilgang, ingen innlogging — kildedata er åpne (NLOD), ingen personopplysninger behandles, og v1 har én brukerrolle. Må demoen være tilgjengelig eksternt, står én delt HTTP Basic Auth foran (ikke brukerkontoer). Full begrunnelse i tillegget.

**UT — bevisst utsatt, ikke avvist:**
1. Sanntids-/live-data som kilde for v1 — utsatt helt; v1 kjører kun på det låste historiske datasettet, ikke en direktestrøm. BarentsWatch Live AIS ble beholdt som en dokumentert reserveløsning i tilfelle historisk dekning viste seg utilstrekkelig (tillegget), men ble aldri utløst — 87,1 % dekning ble oppnådd fra Kystdatahuset-arkivet alene.
2. Flere havner utover Bergen Havn.
3. Prediksjon eksponert som et API for andre konsumenter.
4. Prediksjon av liggetid og avgang, og forslag til omdisponering koblet til kaikapasitet.
5. Rollebasert tilgangskontroll (havnevakt vs. havnekaptein vs. lesetilgang) — utsatt fordi det først blir relevant når dette utvides utover én pilot.
6. Enhver eksternt vendt konsument (rederier, agenter, vareeiere).

## Visjon

Om tre år planlegger norske havner kaibruk mot et felles, datadrevet ankomstanslag — ikke mot et tall skipet selv meldte inn et døgn i forveien. Veien dit: dette semesteret beviser én havn og historiske data metoden mot skipets egen rapporterte ETA. Innen ett år kjører den samme pipelinen i sanntid på tvers av 3–5 havner, og prediksjonen eksponeres som et API. Innen to til tre år utvides den fra ankomst til liggetid og avgang, kobles på kaikapasitet slik at systemet foreslår omdisponering i stedet for bare å flagge et avvik, og det samme anslaget deles med terminal og transportør slik at hele kjeden planlegger mot ett tall i stedet for at hvert ledd gjetter hver for seg.

---

## Kjente rammer (ikke del av selve briefen, beholdt her for kontinuitet)

- Kurs: IBE160 Programmering med KI, Høgskolen i Molde, gruppe G73 (Theodor Gimming Hoffstrøm, Felipe Knudstad-Lopez, Thomas Kvile-Reed).
- Selvdefinert prosjekt — ikke ett av de 8 kursforslagene.
- Teknisk/implementasjonsdybde (AIS-datakvalitets-reserveplan, sikkerhetsdesign-detaljer, veikart-detaljer) ligger i `addendum.md`.
