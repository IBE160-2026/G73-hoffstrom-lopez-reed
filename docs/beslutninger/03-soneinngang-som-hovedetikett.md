# Gap-regel, deretter soneinngang som hovedetikett

## Kontekst

Kystdatahuset oppgir kun rapportert ETA — ikke faktisk ankomsttid. Vi må utlede faktisk ankomst fra rå AIS-spor. Dette kravet gikk gjennom tre versjoner før det stabiliserte seg.

## Alternativer vurdert

- **v1 — fartsterskel:** ankomst = første punkt innenfor havnesonen med fart under 0,5 knop i minst 10 sammenhengende minutter.
- **v2 — gap-regel:** ankomst = siste posisjon innenfor sonen før et opphold i rapportering på over 30 minutter, der posisjonen etter oppholdet fortsatt er innenfor sonen. Ingen fartsterskel.
- **v3 — posisjonsstabilitet som fallback:** når gap-regelen ikke finner noe, prøv i stedet første punkt som ikke beveger seg mer enn 50 meter på 30 minutter (kun posisjon, ingen fartskomponent).
- **v4 — soneinngang:** ankomst = første AIS-posisjon innenfor en ca. 15 km havnesone. Ingen stoppkrav i det hele tatt.

## Valg

Soneinngang (v4) som hovedetikett. Gap-regelen (v2, med v3 som fallback) beholdes som sekundær, ikke-blokkerende etikett (`arrival_at_quay`).

## Begrunnelse

v1 feilet fullstendig (0 % treff): AIS-rapportert fart (`sog`) går aldri under ca. 0,6 knop noe sted nær kai i datagrunnlaget — skip slutter rett og slett å sende AIS mens de ligger fortøyd, i stedet for å rapportere nær-null fart. Konkret bekreftet med ett lasteskip som hadde 22,3 timer sammenhengende AIS-stillhet ved kai.

v2 løste det ved å bruke stillheten selv som signal, og er gyldig nettopp fordi henting skjer per MMSI (beslutning 01) — et opphold kan da bare bety at dette skipet gikk stille. Dekningen ble vesentlig bedre, men fortsatt begrenset: skip som rapporterer jevnlig hele tiden ved kai (ikke går stille) blir ikke fanget. v3 ble lagt til for disse tilfellene, men bidro i praksis nesten ingenting — de fleste slike anløp manglet rett og slett 30 sammenhengende minutters nærdekning å teste stabilitet mot.

v4 er den endelige løsningen: spørsmålet en havnevakt faktisk stiller er "når kommer skipet", og soneinngang er en ren geometrisk hendelse som bare krever ett datapunkt — i motsetning til stoppdeteksjon, som krever et mønster datagrunnlaget ofte ikke inneholder. Dette løftet dekningen betydelig (fra gap-regelens nivå til vesentlig høyere — TBD, fylles inn når fullbatch er kjørt), og dekningen er nå i hovedsak begrenset av skip uten AIS-data i det hele tatt, ikke av om et stoppmønster tilfeldigvis ble fanget.

Gap-regelen beholdes som sekundær etikett (`arrival_at_quay`) fordi differansen mellom soneinngang og faktisk kai — liggetiden fra havneområde til kai — er et nyttig tall i seg selv, og ble grunnlaget for kalibreringen (beslutning 04).

## Konsekvens

Datasettet har to etiketter per seilas: én med høy dekning og upresis definisjon (soneinngang), én med lav dekning og mer presis definisjon (kai-ankomst). Modellen trenes mot soneinngang; kai-ankomst brukes til kalibrering og som kryssjekk i metodedelen, ikke som fasit i seg selv.
