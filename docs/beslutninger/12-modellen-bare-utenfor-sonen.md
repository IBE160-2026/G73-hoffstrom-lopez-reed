# Modellen brukes bare for anløp som er utenfor ankomstsonen ved kuttet

## Kontekst

Etter treningen i E2-S05 (09.11.2026) var gevinsten på valideringsdelen større enn ventet. F1 for varsel var 0,86 ved 6 t, mot 0,49 for «varsle alle» på de samme radene. Gevinsten kom i hovedsak fra rader som allerede er i ankomstsonen ved kuttet (F6).
- Ved `t_6` var 947 Øvrige-anløp med fasit allerede i sonen.
- 569 av dem er merket sene.
- F6 alene gir F1 0,82.

Dette er lokal trafikk fra havner inne i 15-km-sonen, som Kleppestø, Ågotnes, Skålevik og Bergen. For disse anløpene måler etiketten ikke en ankomst (beslutning 03, tillegg 09.11.2026). Det er altså en begrensning ved etiketten, ikke et modellresultat.

## Alternativer vurdert

- **Bare rapportere med og uten F6-rader, som planlagt i beslutning 11 (valg 7).** Forkastet. Modellen ville da ha lært mønsteret i etiketten, og hovedtallet ville vært blåst opp av trafikk vakta ikke trenger hjelp med.
- **Egen kategori for trafikk inne i sonen.** Forkastet. Etiketten er ikke en ankomst for disse radene, så det finnes ingen fasit å trene eller evaluere mot.
- **Modellen brukes bare utenfor sonen ved kuttet.** Valgt.

## Valg

- Modellen trenes, velges og evalueres bare på Øvrige-rader med AIS-tilstand og fasit, der F6 er usann ved kuttet.
- Rader der F6 er sann, går til baselinen, på samme måte som rader uten tilstand. `ModellPrediktor` (E2-S07) delegerer dem og viser metoden i `forklaring`.
- F6 er regnet fra posisjonen ved kuttet (beslutning 11). Delegeringen bruker altså bare data fra før `t_H`.
- F6 står fortsatt i featurelista, så artefaktenes input er uendret. I treningsdataene er den nå alltid 0.

## Begrunnelse

Havnevaktens problem er skip som kommer utenfra. Et skip som allerede ligger i sonen ved kuttet, er ikke et ankomstspørsmål, og etiketten kan ikke si noe meningsfullt om det.

## Grunnlag (valideringsdelen, 09.11.2026)

Testperioden er ikke rørt. Modellene er fra modellvalget, trent bare på trening. Modell og baseline er målt på nøyaktig de samme radene, med Øvrige, AIS-tilstand og fasit.

| H | Variant | n | ±30 min, modell | ±30 min, baseline | MAE modell | MAE baseline | F1 modell | F1 «varsle alle» |
|---|---|---|---|---|---|---|---|---|
| 6 t | (a) gammel modell, alle rader | 634 | 62,8 % | 41,5 % | 96 | 154 | 0,86 | 0,49 |
| 6 t | (b) gammel modell, uten F6-rader | 459 | 70,6 % | 56,9 % | 80 | 101 | 0,67 | 0,19 |
| 6 t | (c) ny modell, uten F6-rader | 459 | 69,1 % | 56,9 % | 82 | 101 | 0,58 | 0,19 |
| 24 t | (a) gammel modell, alle rader | 621 | 56,2 % | 39,6 % | 116 | 161 | 0,81 | 0,51 |
| 24 t | (b) gammel modell, uten F6-rader | 450 | 60,4 % | 51,8 % | 103 | 121 | 0,67 | 0,28 |
| 24 t | (c) ny modell, uten F6-rader | 450 | 59,8 % | 51,8 % | 107 | 121 | 0,60 | 0,28 |

Baselinen varsler aldri, så F1 for baselinen er 0. Referansen for varsel er «varsle alle» (FR10).

## Konsekvens

- **PRD FR9:** prediktoren delegerer også F6-rader til baselinen.
- **E2-S05:** `scripts/tren.py` utelater F6-rader. Artefaktene og `modellvalg.json` er trent på nytt, og `modellvalg.json` har feltet `utvalg`.
- **E2-S06:** hovedtallene for modell mot baseline gjelder anløp utenfor sonen ved kuttet. Antall F6-rader rapporteres. Totalen for alle rader, med F6-rader som baseline, rapporteres i tillegg (FR10: samme anløp).
- **E2-S07:** `ModellPrediktor` delegerer F6-rader til baselinen.
- **Beslutning 03:** begrensningen ved etiketten står der (tillegg 09.11.2026).
