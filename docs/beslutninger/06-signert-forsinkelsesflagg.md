# Signert forsinkelsesflagg fremfor absoluttavvik

## Kontekst

Produktet skal flagge anløp med vesentlig avvik for havnevakten. Vi trenger en binær "verdt å flagge"-etikett, og en plan for når/hvordan den skal evalueres.

## Alternativer vurdert

- **Absoluttavvik:** flagg alle anløp der `|avvik| > 120 min`, uavhengig av retning.
- **Signert avvik (kun forsinkelse):** flagg kun anløp der skipet ankommer *senere* enn kalibrert baseline med mer enn 120 minutter.
- For evaluering: beregne presisjon/recall mot flagget allerede nå, eller vente til en modell finnes.

## Valg

Signert flagg: `er_forsinket = (kalibrert arrival_in_area − rapportert_eta) > 120 min`. Presisjon og recall mot dette flagget beregnes **ikke** før en faktisk prediksjonsmodell finnes (fra 6. oktober).

## Begrunnelse

Å ankomme vesentlig *tidligere* enn ventet er en annen operativ situasjon for en havnevakt enn å ankomme vesentlig *senere* — et samlet "avvik > 2 timer i hvilken som helst retning"-flagg ville visket ut det skillet. "Forsinket" skal bety forsinket.

Presisjon/recall er en modellmetrikk og gir ikke mening før det finnes en modell å evaluere: rapportert ETA predikerer per definisjon null avvik og kan derfor aldri "flagge" noe selv — en presisjon/recall-beregning mot en baseline som aldri predikerer positivt er degenerert, ikke et resultat. Dette ble først forsøkt løst ved å kryssvalidere hovedetiketten (kalibrert `arrival_in_area`) mot sekundæretiketten (`arrival_at_quay`) som en slags stand-in-fasit, men det ble korrigert: da måler tallet både selve klassifiseringen og uenigheten mellom to ulike etikettdefinisjoner samtidig, og er umulig å tolke rent.

Kryssjekken beholdes likevel, men omplassert: hvor ofte de to etikettene er enige om forsinkelsesflagget rapporteres som et **datakvalitetstall i metodedelen**, ikke som modellytelse — og med et eksplisitt forbehold om at utvalget der begge etiketter finnes er skjevt (se addendum), så enigheten kan være lavere på de vanskelige tilfellene som ikke er representert der.

## Konsekvens

`er_forsinket` og `deviation_calibrated_minutes` er lagret som egne kolonner i output-datasettet, klare til bruk som modellmål fra 6. oktober. Ingen presisjon/recall-tall rapporteres før da. Enighetsprosenten mellom de to etikettene inngår i briefens metode-/begrensningsdel, ikke i resultatdelen.

**Fullbatch-tall (n=5 010 med begge etiketter, låst 2026-09-28):** de to etikettene er enige om `er_forsinket`-flagget i 97,0 % av tilfellene (4 859/5 010) — men dette utvalget er skjevt mot større, mer rutepregede fartøy (se beslutning 07-tilstøtende funn i addendum), så enighetstallet sier mest om de enkle tilfellene.
