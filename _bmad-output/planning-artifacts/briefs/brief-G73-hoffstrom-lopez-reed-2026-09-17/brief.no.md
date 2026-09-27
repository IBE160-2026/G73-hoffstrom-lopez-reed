---
title: "Produktbrief: AIS-basert ankomstprediksjon (arbeidstittel)"
status: draft
created: 2026-09-17
updated: 2026-09-27
---

# Produktbrief: AIS-basert ankomstprediksjon (arbeidstittel)

> **Økt satt på pause 2026-09-21.** Alle 7 seksjoner under er ferdig med innhold — ingenting her er halvveis. To beslutninger er fortsatt åpne, spurt om men ikke besvart ennå:
> 1. **Tittel** — fortsatt en arbeidstittel. Har dere et produktnavn, eller skal den stå slik til finalize?
> 2. **Språk** — dette utkastet var opprinnelig på engelsk (etter prosjektkonfigens `document_output_language` og eksempelbriefen i `docs/kilder/`). Denne filen er den norske versjonen, laget som en egen fil ved siden av den engelske.
>
> Se `.memlog.md` for hele beslutningsloggen.

## Executive Summary

For havnevakta ved Bergen Havns Maritime Operations Center bygger vi et beslutningsstøtteverktøy som predikerer når et skip faktisk vil ankomme — ikke bare hva det har rapportert — slik at kaidisponering kan planlegges mot et tall som er verdt å stole på, i stedet for en selvrapportert ETA. I dag disponerer havnevakta kaiplass fortløpende basert på skipenes rapporterte ETA-er, uten noen pålitelig måte å vite på forhånd hvilke rapporter som kan stoles på og hvilke som vil vise seg å være timevis feil. Gapet er relevant nå fordi Bergen Havn — Norges største godshavn og største cruisehavn — allerede er en navngitt deltaker i Kystverkets 10,5 millioner kroner store initiativ "Digital tvilling i havn", hvis uttalte mål er å strømlinjeforme skipsanløp og redusere ventetid i havn. Dette prosjektet bygger prediksjonslaget som det initiativet ennå ikke leverer, ved bruk av de samme åpne AIS-dataene Kystverket allerede publiserer gjennom Kystdatahuset.

## Problemet

Bergen Havn styrer kaidisponering gjennom havnevakta (vaktoffiseren) i sitt Maritime Operations Center — en skiftbasert rolle som fortløpende tildeler kaiplass basert på skipenes selvrapporterte ETA-er. Jobben, i ett konkret scenario: et skip melder ETA 08:00; neste fartøy skal til samme kai 14:00; kommer det første skipet faktisk 08:00, eller 11:30 — og må noe omdisponeres akkurat nå?

Rapporterte ETA-er er kjent bransje-bredt for å avvike fra faktisk ankomst, fordi de ikke gjenspeiler kai-, los- eller slepebåtberedskap — IMOs Just-In-Time Arrival Guide navngir akkurat denne mekanismen: et skip kan være helt "i rute" etter sin egen melding og likevel forårsake unødvendig venting eller en hastig omdisponering av kai. Ingen offentlig dokumentasjon bekrefter denne konkrete smerten ved Bergen Havn spesifikt — det forblir en resonnert slutning fra det generelle bransjemønsteret, ikke en påstått fakta. Men havna har allerede forpliktet reelle midler til det tilstøtende problemet: den er navngitt deltaker i Kystverkets prosjekt "Digital tvilling i havn", hvis uttalte formål er å strømlinjeforme skipsanløp og redusere havnetid — et bevis på at institusjonen allerede anser dagens ETA-informasjon som utilstrekkelig å planlegge mot.

## Løsningen

Et beslutningsstøtteverktøy som predikerer når et skip faktisk vil ankomme Bergen Havn — 6 og 24 timer i forkant — bygget på åpne AIS- og seilasdata fra Kystverkets Kystdatahuset. Siden rådataene bare inneholder hvert skips selvrapporterte ETA, utleder pipelinen først faktiske ankomsthendelser fra AIS-sporene (en standardteknikk: en havneområde-polygon kombinert med en fartsterskel for stopp) for å bygge et merket datasett over avviket mellom rapportert og reell ankomst. En modell trent på dette datasettet produserer 6t/24t-prediksjonene, målt mot skipets egen rapporterte ETA — referansen hver prediksjon må slå. Et generativt AI-lag gjør hver dags prediksjoner om til en kort daglig brief for havnevakta: et kart pluss en begrunnelse for hvert forventede avvik, slik at operatøren ser ikke bare et tall, men hvorfor det trolig er feil.

v1 leveres som et nettbasert dashbord, åpent uten innlogging (se Scope). Gruppens uttalte ambisjon er en live pipeline mot ferske Kystdatahuset-data, med en utprøvd reserveplan hvis live-data viser seg for hullete innenfor kursets tidsramme (full plan i tillegget).

## Hva gjør dette annerledes

Ingen AIS-ETA-leverandør funnet i markedet — Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic — publiserer en revidert, reproduserbar nøyaktighetsbenchmark; påstandene deres er markedsføringstekst, ikke dokumentert metodikk. Det er i seg selv en legitim differensiator: dette prosjektet måler seg selv, offentlig, mot den ene ærlige baseline som finnes — skipets egen rapporterte ETA. Kystdatahuset er en datakilde, ikke et prediksjonsprodukt, så det finnes ikke noe eksisterende verktøy bygget på akkurat disse dataene i dag.

Den nærmeste nordiske akademiske presedensen, en NTNU-masteroppgave om AIS-basert prediksjon av liggetid ved Mongstad, kom til en forsiktig konklusjon ("a convoluted task with many hidden variables") — et ærlig referansepunkt, ikke en list dette prosjektet påstår å klare enkelt. En nærmere metodisk presedens finnes utenfor Norge: en Hong Kong-studie som kombinerte AIS-spor med anløpsdata via XGBoost kuttet ETA-feilen med 52,98 % mot skipets egen rapporterte ETA, med en nesten identisk tilnærming ved en annen havn — reelt bevis på at metoden virker, ikke et løfte om at denne gruppen vil matche det tallet.

Ærlig sagt: det finnes ingen teknisk moat her. Fortrinnet er å være først til å rette akkurat denne metoden mot Bergen Havns konkrete ETA-nøyaktighetsproblem, og å være transparent om tallet som kommer ut, i stedet for å påstå ett.

## Hvem dette tjener

**Primær: havnevakta i Bergen Havns Maritime Operations Center** (offentlig døgnkontakt: havnevakt@bergenhavn.no) — en skiftbasert rolle som fortløpende tildeler kaiplass. Suksess for dem: færre siste-liten-omdisponeringer av kai, og et pålitelig svar på "kommer dette skipet faktisk når det sier det skal."

**Sekundær: havnekaptein / driftsleder** — taktisk planlegging over uker fremfor enkeltanløp, med de samme prediksjonene aggregert til mønstre og kapasitetsoversikter.

**Eksplisitt ikke en v1-bruker:** rederier, skipsagenter, vareeiere. Å utvide brukergruppen til dem er en bevisst senere beslutning (se Visjon), ikke en forglemmelse.

## Suksesskriterier

**Funksjonelt.** Modellen predikerer ankomst 6t og 24t i forkant for skip som anløper Bergen Havn, målt mot skipets egen rapporterte ETA som baseline den må slå. Siden ingen ekstern, revidert bransjebenchmark finnes (se Hva gjør dette annerledes), skal gruppen beregne sin egen rapportert-ETA-feil-baseline direkte fra Kystdatahuset-data og sette målet som en prosentvis forbedring over den selvberegnede baselinen. Hong Kong-presedensen (52,98 % MAE-reduksjon mot selvrapportert ETA) er et nyttig ambisjonsreferansepunkt for hva "bra" ser ut som med denne metoden — ikke et tall å adoptere direkte, siden det kommer fra en annen havn og en annen pipeline.

**Datakvalitet.** Daglig AIS-dekning logges som en eksplisitt metrikk; seilaser der faktisk ankomst ikke kan utledes droppes og telles, ikke stille interpolert (full reserveplan i tillegget).

**Produkt.** Havnevakta kan lese en daglig brief og forstå, uten å spørre noen, hvilke av morgendagens forventede ankomster de bør mistro, og hvorfor.

## Scope

**INN — v1 (dette kurset, ~12 uker):**
1. Historisk AIS-/seilasinnhenting fra Kystdatahuset for et verifisert datavindu ved Bergen Havn.
2. Utledning av faktiske ankomsthendelser fra AIS-spor, med en logget daglig dekningsmetrikk.
3. En trent modell som predikerer ankomst 6t og 24t i forkant, målt mot rapportert ETA.
4. Et nettbasert dashbord som viser den daglige briefen: predikerte ankomster, et kart, og en begrunnelse per forventet avvik, generert av et AI-oppsummeringslag.
5. Åpen tilgang, ingen innlogging — kildedata er åpne (NLOD), ingen personopplysninger behandles, og v1 har én brukerrolle. Må demoen være tilgjengelig eksternt, står én delt HTTP Basic Auth foran (ikke brukerkontoer). Full begrunnelse i tillegget.

**UT — bevisst utsatt, ikke avvist:**
1. Sanntids-/live-data som primærkilde — gruppen er forpliktet til å forsøke det, med en utprøvd reserveløsning til BarentsWatch Live AIS hvis Kystdatahuset-arkivet viser seg for hullete (tillegg: reserveplan).
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
