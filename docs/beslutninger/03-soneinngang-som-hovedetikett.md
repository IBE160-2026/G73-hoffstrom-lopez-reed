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

v4 er den endelige løsningen: spørsmålet en havnevakt faktisk stiller er "når kommer skipet", og soneinngang er en ren geometrisk hendelse som bare krever ett datapunkt — i motsetning til stoppdeteksjon, som krever et mønster datagrunnlaget ofte ikke inneholder. Dette løftet dekningen betydelig: fra gap-regelens nivå (målt som `arrival_at_quay` på fullbatchen: 64,0 %, n=7 826) til 87,1 % (`arrival_in_area`, samme utvalg). Dekningen er nå i hovedsak begrenset av skip uten AIS-data i det hele tatt (935 av 7 826, 11,9 %), ikke av om et stoppmønster tilfeldigvis ble fanget.

Gap-regelen beholdes som sekundær etikett (`arrival_at_quay`) fordi differansen mellom soneinngang og faktisk kai — liggetiden fra havneområde til kai — er et nyttig tall i seg selv, og ble grunnlaget for kalibreringen (beslutning 04).

## Konsekvens

Datasettet har to etiketter per seilas: én med høy dekning og upresis definisjon (soneinngang), én med lav dekning og mer presis definisjon (kai-ankomst). Modellen trenes mot soneinngang; kai-ankomst brukes til kalibrering og som kryssjekk i metodedelen, ikke som fasit i seg selv.

## Kjent begrensning: soneinngang lenge før ETA (06.11.2026)

Etiketten er *første* AIS-posisjon innenfor sonen. Et skip som passerer gjennom sonen tidlig og går ut igjen, får derfor en ankomst som er for tidlig. Kontrollen etter full henting (E2-S04, `scripts/sjekk_avstand_og_etikett.py`) viser:

- **33 av 6 815 anløp med fasit (0,48 %)** har soneinngang mer enn 24 t før rapportert ETA (median 35 t, maks 296 t). De samler seg ikke på én skipstype. De er spredt på 14 typer, og offshore og forsyning står for 6 av de 33 (18,2 %), mot 15,8 % av alle anløp med fasit. Den største enkelttypen er forskningsfartøy, med 6.
- **Tre anløp er fysisk umulige** ut fra posisjonen ved kuttet. Alle er trolig etikettfeil der en tidligere passering ble fanget:
  - HALTBAKK STAR (2233024): 315 km unna ved `t_6`, soneinngang 2 613 min før kalibrert ETA.
  - NORDKAPP (2444262): 1 458 km unna ved `t_6`, 10 087 min før.
  - STAVANGERFJORD (2835191): 347 km unna ved `t_6`, 1 444 min før.
- **Testdelen.** Ingen av de tre umulige ligger i testdelen. Av de 33 tidlige ligger 6 i testdelen:
  - HALTBAKK STAR (3353948), et annet anløp enn det umulige, 89 t før ETA
  - EINARSON, 26 t
  - PELAGIA HORDAFOR, 61 t
  - RO CHIEF, 177 t
  - VISION OF THE FJORDS, 25 t
  - ROBAS, 27 t

  De 6 er 0,4 % av testperioden, og de kan gjøre evalueringen litt strengere for modell og baseline likt.
- **Datasettet endres ikke.** Det er låst, og etiketten er den samme for modell og baseline. Begrensningen nevnes i resultatnotatet.

## Kjent begrensning: trafikk som allerede er i sonen ved kuttet (09.11.2026)

For anløp som allerede er i ankomstsonen ved kuttet, måler etiketten ikke en ankomst. Det gjelder lokale turer fra havner inne i 15-km-sonen, som Kleppestø, Ågotnes, Skålevik og Bergen. «Første posisjon i sonen» blir da et punkt etter avgang, ikke en ankomst.
- Ved `t_6` er 947 Øvrige-anløp med fasit allerede i sonen (F6), og 569 av dem er merket sene.
- F6 alene gir F1 0,82 for varsel på valideringsdelen.
- Datasettet endres ikke. Modellen brukes bare for anløp som er utenfor sonen ved kuttet ([beslutning 12](12-modellen-bare-utenfor-sonen.md)).
