# De 16 % uten AIS som åpent spørsmål

## Kontekst

En andel av seilasene i pilotutvalget ga null AIS-posisjoner i hele hentevinduet, til tross for korrekt MMSI og gyldig tidsvindu. Mønsteret var ikke tilfeldig: alle de berørte seilasene gjaldt utenlandskflaggede skip, mens ingen norskflaggede seilaser i utvalget manglet data.

## Alternativer vurdert

- **Hypotese A — tilgangsbegrensning:** den åpne/anonyme tilgangen til Kystdatahuset-APIet begrenser posisjonshistorikk for utenlandske fartøy.
- **Hypotese B — MMSI-mismatch:** Kystdatahuset/SafeSeaNets registrerte MMSI for et utenlandsk skip kan være utdatert, slik at oppslaget feiler på nøkkelen, ikke på tilgangen.
- **Test av hypotese B:** kryssoppslag via IMO-nummer (`/api/ship/combined/imo/{imo}`) for å se om AIS-registeret oppgir en annen MMSI enn den seilasdataene bruker.

## Valg

Dokumentere som et åpent, uavklart spørsmål. Ingen av hypotesene legges til grunn i videre arbeid.

## Begrunnelse

Den direkte testen (IMO-oppslag) er blokkert: endepunktet krever rollen `Kystdatahuset_ekstern_alle` i praksis, til tross for at APIets egen spesifikasjon ikke oppgir autentiseringskrav på det endepunktet. Et alternativt, åpent endepunkt (`ais_shipreg/statinfo`) ga samme tomme resultat for de testede MMSI-ene — det er antydende, men skiller ikke mellom hypotese A og B. Uten en innlogget rolle med tilstrekkelige rettigheter er det ikke mulig å avgjøre saken nå. Å likevel hevde én forklaring ville vært en påstand uten dekning.

## Konsekvens

Dekningstallet for ikke-rutegående/utenlandsk trafikk vil være lavere enn det ellers ville vært, av en årsak vi ikke fullt ut forstår. Dette står som en dokumentert begrensning i briefens risikoseksjon. Dersom gruppen på et senere tidspunkt får tilgang til en konto med høyere rolle, er testen beskrevet over klar til å kjøres direkte.
