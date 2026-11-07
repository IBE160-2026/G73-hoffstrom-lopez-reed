# Seilasene uten AIS skyldes hentingen, ikke flagg eller MMSI, og de hentes ikke på nytt

**Korrigert 22.10.2026.** Første versjon av denne beslutningen (28.09.2026) forklarte de manglende AIS-dataene med at skipene var utenlandske. Den antok enten at den åpne API-tilgangen begrenser historikk for utenlandske fartøy, eller at registrert MMSI er utdatert. Den forklaringen holder ikke, se under. Den opprinnelige teksten finnes i git-historikken (`git log -p -- docs/beslutninger/07-manglende-ais-utenlandske-skip.md`).

## Kontekst

935 av 7 826 seilaser (11,9 %) ga null AIS-posisjoner i hentevinduet i fullbatch-hentingen (`status_in_area = empty`). De mangler derfor fasit. Det er hovedgrunnen til at dekningen er 87,1 % og ikke høyere.

## Hva vi vet nå

- **Skjevheten mot utenlandske skip er ekte.** Målt på MMSI-prefiks for hele datasettet er 83 % av `empty`-seilasene utenlandske, mot 33 % av seilasene med fasit. Første versjon hadde bare målt dette på pilotutvalget.
- **Men dataene finnes, og de er tilgjengelige.** I stikkprøven fra beslutning 09 (`pipeline/sjekk_ais_dekning_kutt.py --oppfolging`, 22.10.2026) har 7 av 10 tilfeldige `empty`-seilaser fra testperioden posisjoner i sitt *opprinnelige* hentevindu i dag. Alle 7 har punkter innenfor 15 km fra Bergen, altså selve ankomsten. 5 av de 7 er utenlandske.
  - **Tilgangsbegrensning er motbevist** for disse. Det er samme anonyme tilgang som før.
  - **Utdatert MMSI er motbevist** for disse. Det er samme MMSI som før.
  - De 3 som fortsatt er tomme, er alle utenlandske. For dem kan en MMSI-feil fortsatt være forklaringen.
- **Hvorfor den opprinnelige hentingen ga tomme svar, vet vi ikke.** Kandidatene er at API-et ga midlertidig tomme svar under nattehentingen (som ble avbrutt og startet på nytt 27.–28.09), eller at arkivet er fylt på i ettertid. Ingen av dem er undersøkt. At utenlandske skip er overrepresentert, tyder på at kilden for deres posisjoner oppfører seg annerledes, men det er ikke bekreftet.

## Alternativer vurdert

- **Hente `empty`-seilasene på nytt nå.** Stikkprøven tyder på at rundt to tredeler kan berges, altså opptil ~600 seilaser.
- **Beholde det låste datasettet og føre dekningen som en kjent underestimering.** Valgt.

## Valg

**Vi henter ikke på nytt.** Datasettet ble låst 28.09.2026, og dekningen på 87,1 % føres som en **kjent underestimering**: den reelle dekningen i Kystdatahuset er høyere. Ny henting av `empty`-seilasene er **videre arbeid**.

## Begrunnelse

46,6 % og alle tall nedstrøms bygger på det låste datasettet: kalibreringen (beslutning 04), splitten, utdraget i `data/` (E1-S02), regresjonstestene (PRD FR8), brief, PRD, epics og beslutning 08–09. En ny henting midt i oktober ville ugyldiggjort hele den kjeden én uke før dashbordet skal stå på dem. Den ville også gitt et nytt datasett med en annen fordeling av skip (flere utenlandske og flere ikke-rutegående), som måtte kalibreres og dokumenteres på nytt. Et kjent, dokumentert hull er bedre enn et datasett i bevegelse.

## Konsekvens

- **Dekningen på 87,1 % er en underestimering.** Det står der tallet brukes (brief, addendum, status). Hullet rammer mest utenlandske og ikke-rutegående skip. Det betyr at Øvrige er underrepresentert i evalueringen, og at baselinetallene er målt på et utvalg som heller mot norske, mer rutepregede skip.
- **Ved ny henting senere må `fetch_ais.py` rettes først.** Det gjelder ny API-adresse og vindu som forskyves (beslutning 09, funn A–C). Resultatet skal behandles som et nytt datasett med egen låsing og egne tall, ikke som en stille oppdatering av det gamle.
- **Beslutning 08 og 09:** AIS ved kuttpunktene (E2-S02) er en ny, separat henting av tilstanden før ankomst, ikke av fasiten. Den berøres ikke av dette valget. Skip som mangler fasit i dag, er fortsatt uten fasit og tas ikke med i evalueringen.

## Oppdatert 03.11.2026: 63 av de tomme seilasene har MMSI 0

Røyktesten i E2-S03 fant at **63 av de 935 tomme seilasene (6,7 %) har MMSI 0** i seilasdataene fra SafeSeaNet. Ingen av dem har fasit. Alle 63 er `empty`: 59 Øvrige i trening, 3 Passasjer i trening og 1 Øvrige i test.

**Det forklarer en del av de tomme svarene.** MMSI 0 er ikke et ekte fartøy. Når API-et blir spurt om MMSI 0, svarer det i dag med posisjoner fra alle fartøy i verden som sender 0. Røyktesten fikk «siste posisjoner» 7 000–17 000 km fra Bergen. Disse seilasene kan aldri få en fasit fra AIS, uansett hvordan de hentes. De er et hull i SafeSeaNet-dataene, ikke i hentingen.

**Det forklarer ikke resten.**
- **872 av de 935 (93 %) har en gyldig MMSI med 9 sifre** og er fortsatt uforklart. Stikkprøven fra beslutning 09 (7 av 10 har data i dag) gjelder dem.
- **Skjevheten mot utenlandske skip står.** Tallet på 83 % over regnet MMSI 0 som utenlandsk, fordi den ikke har norsk prefiks (257–259). Uten de 63 er andelen 81,4 % (710 av 872), mot 33,2 % blant seilasene med fasit.
- **Det sier ingenting om hvorfor den opprinnelige hentingen ga tomme svar** for skip som har data i dag.

**Konsekvens:** dekningen på 87,1 % og 46,6 % er uendret. Datasettet er fortsatt låst. Tilstandsutdraget i E2-S03 regner en posisjon som gyldig bare hvis MMSI-en i punktet er lik seilasens MMSI og har 9 sifre, så MMSI 0-seilasene blir `ingen_posisjon` (Felipe, 03.11.2026). Ved en eventuell ny henting (videre arbeid) bør seilaser med MMSI 0 tas ut før kallet, ikke etterpå.

