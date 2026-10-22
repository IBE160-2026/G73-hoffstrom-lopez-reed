# Prediksjonshorisonten defineres av kutt i AIS-sporet ved rapportert ETA − H

## Kontekst

Briefen lover prediksjon 6 og 24 timer før ankomst. Datasettet har én rapportert ETA per seilas, så ETA-en alene skiller ikke en 6 t-prediksjon fra en 24 t-prediksjon. Dette sto som åpent spørsmål i PRD §7 og story E2-S01.

## Alternativer vurdert

- **Samme input for begge horisontene.** Da er «6 t» og «24 t» bare navn, og ingenting skiller dem i dataene.
- **Kutt ved faktisk ankomst − H.** Forkastet. Prediksjonstidspunktet ville da avhenge av fasiten. Modellen ville fått vite *når* skipet kom fram, og det er nettopp det den skal predikere. Det ville gitt lekkasje.
- **Kutt ved rapportert ETA − H.** Valgt.

## Valg

For hver seilas og horisont H ∈ {6 t, 24 t} er **prediksjonstidspunktet `t_H = rapportert_eta − H`**. Modellens input er fartøyets tilstand ved `t_H`, regnet fra den siste AIS-posisjonen *ved eller før* `t_H`:

- posisjon (bredde- og lengdegrad)
- gjenstående distanse til Bergen havn (storsirkel til referansepunktet for ankomstsonen fra beslutning 03)
- fart over grunn
- kurs over grunn
- alder på posisjonen (`t_H` − tidspunkt for posisjonen), slik at modellen vet hvor fersk tilstanden er

**Baselinen er den samme for begge horisontene:** `rapportert_eta − offset[gruppe]` (beslutning 04). Rapportert ETA er kjent ved begge tidspunktene, så baselinen har ikke mer å bruke ved 6 t enn ved 24 t.

**Lekkasjeregel (ufravikelig):** ingen input til modellen kan avhenge av `arrival_in_area`, `arrival_at_quay` eller andre data etter `t_H`. Kuttet skjer på *rapportert* ETA, aldri på faktisk ankomst. Dette er også krav i PRD-en og testes i E2-S03.

## Begrunnelse

Å kutte på rapportert ETA etterligner vaktsituasjonen. Havnevakta vet hva skipet har meldt og ser hvor det er nå. Hen vet ikke når det faktisk kommer. En modell som får vite mer enn vakta kunne visst, gir et tall som ser bra ut i evalueringen og er verdiløst i drift.

Kuttet lager også et reelt skille mellom horisontene: 24 t før er skipet ofte fortsatt i forrige havn eller langt ute, og 6 t før er det som regel underveis. Hvor mye det skillet er verdt, viser evalueringen.

## Konsekvens

**Dagens AIS-cache dekker ikke kuttpunktene.** Hentevinduet (beslutning 02) starter ved seilasens ETD, eller ETA − 24 t som reserve, og er laget for å finne *ankomst*, ikke tilstand mange timer før. Målt 16.10.2026 på `pipeline/data/ais_cache/`:

| Utvalg | n | Posisjon ≤ 1 t før `t_6` | Posisjon ≤ 1 t før `t_24` |
|---|---|---|---|
| Test, øvrige | 1 119 | 30,8 % | 7,3 % |
| Test, passasjer | 447 | 26,0 % | 8,7 % |
| Trening, øvrige | 4 358 | 28,8 % | 6,2 % |
| Alle | 7 826 | 32,6 % | 9,2 % |

Det trengs derfor en egen, målrettet AIS-henting rundt hvert kuttpunkt (story E2-S02). Den henter et lite vindu [`t_H` − 3 t, `t_H`] per seilas og horisont, så ingen posisjoner etter `t_H` noen gang lastes ned for dette formålet.

**Noen seilaser vil fortsatt mangle posisjon ved `t_H`.** Typisk gjelder det skip utenfor norsk AIS-dekning 24 t før, og utenlandsflaggede skip (beslutning 07). De predikeres da med baselinen og merkes «ingen AIS-tilstand ved prediksjonstidspunktet». De fjernes ikke fra evalueringen. Modellen og baselinen evalueres på *nøyaktig samme* rader, og dekningen ved hvert kutt rapporteres som eget tall.

**Antakelse som ikke kan verifiseres i dataene:** Kystdatahuset gir én ETA per seilas. Vi vet ikke om det er ETA-en slik den var meldt ved `t_H`, eller en senere oppdatert verdi. Er den oppdatert nærmere ankomst, får både modell og baseline litt mer informasjon enn vakta hadde ved `t_24`. Det er en kjent begrensning, ikke en lekkasje vi selv har laget. Den rapporteres i resultatnotatet (E2-S10).

**I avspillingen i dashbordet** velges horisonten fra `rapportert_eta − nå` (≤ 6 t gir 6 t-modellen, ellers 24 t-modellen), ikke fra predikert ankomst. Da er `t_H ≤ nå` for hver rad, og avspillingen bruker aldri AIS-data vakta ikke kunne hatt (PRD FR2). Dette ble fanget i BMAD-valideringen av PRD-en samme dag.

**Skip som har ankommet før `t_H`** (1,6 % ved 6 t, 0,4 % ved 24 t) beholdes. Ankomsten er da kjent informasjon ved prediksjonstidspunktet, ikke en lekkasje. De telles likevel og rapporteres separat, så de ikke stille løfter treffsikkerheten.

Om passasjer og øvrige skal ha separate modeller, er fortsatt åpent og avgjøres i E2-S01.

**Oppdatert 22.10.2026:** Vinduet [`t_H` − 3 t, `t_H`] over er erstattet av [`t_H` − 24 t, `t_H`]. Stikkprøven i [beslutning 09](09-ais-dekning-ved-kuttpunktene.md) viste at skip som ligger i ro, har glisne AIS-punkter, og at API-et forskyver vinduet som det blir bedt om. Valget i denne beslutningen, kutt ved rapportert ETA − H, står.
