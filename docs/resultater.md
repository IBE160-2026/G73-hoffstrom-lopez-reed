# Resultatnotat: modell mot kalibrert baseline (E2-S10)

Testperioden (14.09.2025–15.03.2026) er kjørt én gang, 13.11.2026, med `scripts/evaluer.py --test` på commit `8920acb92cda52c9ed03992cb404def7d03f9fdc`. Før kjøringen var modellen, konfigurasjonen, valgreglene og suksesskriteriene låst. Kriteriene ble kopiert ordrett fra `docs/brief.md` inn i specen (`_bmad-output/implementation-artifacts/spec-e2-s10-resultatnotat.md`) og committet før tallene var kjent. Ingenting i modellen, konfigurasjonen, valgreglene eller kriteriene er endret etter kjøringen, og testkjøringen er ikke gjort på nytt. Testradene er lest én gang til, for McNemar-tilleggsanalysen, med de samme låste artefaktene (se under), og det endrer ikke dommen. Alle tall i tabellene under er hentet fra `data/modell/metrikker.json` og `data/modell/mcnemar.json`, og `tests/test_resultater.py` og `tests/test_mcnemar.py` sjekker at tabellene er ordrett like filene.

## Oppsummering

- **Dommen: bestått ved begge horisonter**, slik kriteriene i briefen sier. På modellutvalget har modellen høyere andel innenfor ±30 min enn den kalibrerte baselinen og høyere varsel-F1 enn «varsle alle», både ved 6 t og 24 t.
- **6 t er en klar forbedring.** Modellen treffer innenfor ±30 min på 68,5 % mot baselinens 59,1 % (+9,4 prosentpoeng, 502 mot 433 av 733 anløp). McNemars test (tilleggsanalyse, se under) gir p ≈ 2,3 · 10⁻⁷.
- **24 t er formelt bestått, men forskjellen er seks anløp, og den hviler på data vi ikke kan verifisere.** Modellen treffer 57,1 % mot baselinens 56,3 % (424 mot 418 av 742). McNemars test gir p = 0,64, så forskjellen kan ikke skilles fra tilfeldig variasjon.
- **Bestått ved 24 t avhenger av avgangshavn og ETD (F13–F14).** Ablasjonen uten dem treffer 53,8 % mot baselinens 56,3 %, og ville altså **ikke bestått**. F13–F14 er de to featurene vi ikke kan verifisere (avgangshavn og ETD, begrensningen ved siden av A1 i beslutning 11): de kommer fra en seilaspost som kan være satt sammen i etterkant.
- **Varsel-F1 falt fra validering til test**, fra 0,58 til 0,46 (6 t) og fra 0,60 til 0,44 (24 t). Testperioden er høst og vinter (14.09.2025–15.03.2026), mens valideringen var mai–13.09.2025.
- **For all Øvrige-trafikk er systemet dårligere enn «varsle alle» på varsel.** Systemet (modellen der den brukes, baselinen ellers) har F1 0,19 og 0,21 mot 0,33. Det er ikke kriteriet, men det er prisen for at varselet bare kan nå under halvparten av de forsinkede anløpene (se begrensningene).

## Kriteriene

Kriteriene står ordrett i specen. Kort: bestått/ikke bestått avgjøres på **modellutvalget** (Øvrige-anløp med AIS-posisjon ved kuttet som er utenfor ankomstsonen, beslutning 12). Modellen må ha (1) høyere andel innenfor ±30 min enn den kalibrerte baselinen på de samme anløpene, og (2) høyere varsel-F1 enn regelen «varsle alle» på de samme anløpene. Dommen sammenligner de uavrundede verdiene.

### Testkjøringer

Antall testkjøringer: 1.

| Nr. | Dato | Commit (full hash) |
|---|---|---|
| 1 | 2026-11-13 | `8920acb92cda52c9ed03992cb404def7d03f9fdc` |

### Dom per horisont (modellutvalget)

| Horisont | Krav (briefen) | Modell | Referanse | Dom |
|---|---|---|---|---|
| 6 t | Innenfor ±30 min høyere enn baselinen | 68,5 % (502/733) | 59,1 % (433/733) | bestått |
| 6 t | Varsel-F1 høyere enn «varsle alle» | 0,463 | 0,144 | bestått |
| 24 t | Innenfor ±30 min høyere enn baselinen | 57,1 % (424/742) | 56,3 % (418/742) | bestått |
| 24 t | Varsel-F1 høyere enn «varsle alle» | 0,436 | 0,190 | bestått |

## Modellutvalget og all Øvrige-trafikk

Tabellen har samme form som i briefen. Raden for modellutvalget avgjør dommen. Raden for all Øvrige-trafikk viser systemet: modellen for anløpene i modellutvalget og baselinen for resten (Passasjer er ikke med). Modellandelen er andelen av Øvrige-anløp med fasit som modellen faktisk brukes på.

| Rad | Testanløp med fasit | Modellandel (av Øvrige-anløp med fasit) | Baseline, ±30 min | Modell, ±30 min | Grunnrate forsinket | F1 «varsle alle» | F1 modell |
|---|---|---|---|---|---|---|---|
| **Modellutvalget** (avgjør bestått/ikke bestått) | 733 / 742 | 73,6 % / 74,5 % | 59,1 % (433/733) / 56,3 % (418/742) | 68,5 % (502/733) / 57,1 % (424/742) | 7,8 % (57/733) / 10,5 % (78/742) | 0,14 / 0,19 | 0,46 / 0,44 |
| **All Øvrige-trafikk, med delegering** | 996 / 996 | 73,6 % / 74,5 % | 46,6 % (464/996) / 46,6 % (464/996) | 53,5 % (533/996) / 47,2 % (470/996) | 19,5 % (194/996) / 19,5 % (194/996) | 0,33 / 0,33 | 0,19 / 0,21 |

## Tilleggsanalyse: McNemars test for ±30 min

**Regnet etter testkjøringen, og endrer ikke dommen.** Modell og baseline er målt på de samme anløpene, så forskjellen i treffandel kan testes parvis. McNemar trenger antall uenige par: anløp der bare modellen eller bare baselinen treffer. `metrikker.json` har bare summene. Testradene ble derfor lest på nytt med `scripts/mcnemar.py` (godkjent av Felipe 13.11.2026), med de samme committede artefaktene og den samme prediksjonskoden som testkjøringen (funksjonene i `scripts/evaluer.py`). Treffregelen per anløp (|faktisk − predikert| ≤ 30 min) er skrevet i skriptet, lik den i `app/metrikker.py`. Skriptet sjekket først at de låste filene var uendret siden kjøringens commit, og etterpå at summene ble nøyaktig de samme som i `metrikker.json`. Bare krysstabellen og p-verdien er lagret (`data/modell/mcnemar.json`), ikke prediksjoner per anløp. p-verdien er den eksakte tosidige binomialtesten på de uenige parene. Det er ikke regnet effektstørrelse eller konfidensintervall for den parvise forskjellen, og p-verdiene er ikke korrigert for at to horisonter er testet. Skriptet stopper nå hvis `mcnemar.json` finnes, så analysen ikke kan gjøres på nytt ved et uhell.

| Horisont | n | Begge riktige | Bare modell | Bare baseline | Ingen | Uenige par | p (eksakt) |
|---|---|---|---|---|---|---|---|
| 6 t | 733 | 379 | 123 | 54 | 177 | 177 | 2,3e-07 |
| 24 t | 742 | 365 | 59 | 53 | 265 | 112 | 0,6368 |

- **6 t:** 123 anløp der bare modellen treffer, mot 54 der bare baselinen gjør det. Forskjellen er klar.
- **24 t:** 59 mot 53 av 112 uenige par. Det er nesten like mange hver vei, og p = 0,64. Modellen og baselinen bommer på ulike anløp, men like ofte.
- For all Øvrige-trafikk er de uenige parene de samme, fordi resten av anløpene får baselinens prediksjon i begge armene.

## Validering mot test

Valideringstallene og testtallene kommer fra ulike tilpasninger (E2-S06, beslutning 4). Validering er modellen tilpasset på nytt bare på treningsdelen, slik den var ved modellvalget. Test er de endelige artefaktene, trent på trening og validering samlet.

| Horisont | Radsett | Periode og fit | n | Modell, ±30 min | Baseline, ±30 min | F1 modell | F1 «varsle alle» |
|---|---|---|---|---|---|---|---|
| 6 t | Modellutvalget | Validering (refit på trening alene) | 459 | 69,1 % (317/459) | 56,9 % (261/459) | 0,58 | 0,19 |
| 6 t | Modellutvalget | Test (endelige artefakter, trent på trening + validering) | 733 | 68,5 % (502/733) | 59,1 % (433/733) | 0,46 | 0,14 |
| 6 t | All Øvrige-trafikk, med delegering | Validering (refit på trening alene) | 659 | 48,6 % (320/659) | 40,1 % (264/659) | 0,17 | 0,51 |
| 6 t | All Øvrige-trafikk, med delegering | Test (endelige artefakter, trent på trening + validering) | 996 | 53,5 % (533/996) | 46,6 % (464/996) | 0,19 | 0,33 |
| 24 t | Modellutvalget | Validering (refit på trening alene) | 450 | 59,8 % (269/450) | 51,8 % (233/450) | 0,60 | 0,28 |
| 24 t | Modellutvalget | Test (endelige artefakter, trent på trening + validering) | 742 | 57,1 % (424/742) | 56,3 % (418/742) | 0,44 | 0,19 |
| 24 t | All Øvrige-trafikk, med delegering | Validering (refit på trening alene) | 659 | 45,5 % (300/659) | 40,1 % (264/659) | 0,24 | 0,51 |
| 24 t | All Øvrige-trafikk, med delegering | Test (endelige artefakter, trent på trening + validering) | 996 | 47,2 % (470/996) | 46,6 % (464/996) | 0,21 | 0,33 |

- Andelen innenfor ±30 min holdt seg på modellutvalget (69,1 → 68,5 % ved 6 t, 59,8 → 57,1 % ved 24 t). Baselinen var derimot høyere i test (56,9 → 59,1 % og 51,8 → 56,3 %). Ved 24 t krympet derfor marginen fra 8 til under 1 prosentpoeng.
- Varsel-F1 falt fra 0,58 til 0,46 (6 t) og fra 0,60 til 0,44 (24 t). Grunnraten for forsinkede i modellutvalget er også lavere i test (7,8 % og 10,5 %), så «varsle alle» falt fra 0,19 til 0,14 og fra 0,28 til 0,19.
- Vi har ikke undersøkt om fallet skyldes sesong, at grunnraten er lavere, eller noe annet. Testperioden er høst og vinter (14.09.2025–15.03.2026), og valideringen var mai–13.09.2025.

## Ablasjon uten F13–F14

Ablasjonen er den samme modellen trent uten avgangshavn og ETD (F13–F14, beslutning 11). Den viser hvor mye resultatet hviler på disse to feltene.

| Horisont | Radsett | n | Modell, ±30 min | Uten F13–F14, ±30 min | F1 modell | F1 uten F13–F14 | MAE modell (min) | MAE uten F13–F14 (min) |
|---|---|---|---|---|---|---|---|---|
| 6 t | Modellutvalget | 733 | 68,5 % (502/733) | 66,0 % (484/733) | 0,46 | 0,30 | 75,9 | 84,0 |
| 6 t | All Øvrige-trafikk, med delegering | 996 | 53,5 % (533/996) | 51,7 % (515/996) | 0,19 | 0,10 | 124,0 | 130,0 |
| 24 t | Modellutvalget | 742 | 57,1 % (424/742) | 53,8 % (399/742) | 0,44 | 0,26 | 96,4 | 102,4 |
| 24 t | All Øvrige-trafikk, med delegering | 996 | 47,2 % (470/996) | 44,7 % (445/996) | 0,21 | 0,13 | 131,3 | 135,8 |

- Ablasjonen er dårligere enn hovedmodellen på alle mål ved begge horisonter.
- **Ved 24 t ville ablasjonen ikke bestått kriteriet for ±30 min**: 53,8 % mot baselinens 56,3 %. Ved 6 t ville den bestått (66,0 % mot 59,1 %).
- Bestått ved 24 t hviler altså på F13–F14, som vi ikke kan verifisere.

## Støttetall

MAE og median absolutt feil er støttetall, aldri hovedtall (briefen). Passasjer er kontrollgruppe og får bare baselinen.

| Horisont | Radsett | Arm | n | ±30 min | MAE (min) | Median absolutt feil (min) |
|---|---|---|---|---|---|---|
| 6 t | Modellutvalget | Modell | 733 | 68,5 % (502/733) | 75,9 | 14,7 |
| 6 t | Modellutvalget | Baseline | 733 | 59,1 % (433/733) | 91,9 | 21,5 |
| 6 t | All Øvrige-trafikk | Systemet (modell + baseline for resten) | 996 | 53,5 % (533/996) | 124,0 | 26,5 |
| 6 t | All Øvrige-trafikk | Baseline | 996 | 46,6 % (464/996) | 135,8 | 34,3 |
| 6 t | Passasjer (kontrollgruppe) | Baseline | 431 | 79,6 % (343/431) | 22,5 | 5,7 |
| 24 t | Modellutvalget | Modell | 742 | 57,1 % (424/742) | 96,4 | 23,6 |
| 24 t | Modellutvalget | Baseline | 742 | 56,3 % (418/742) | 102,4 | 23,4 |
| 24 t | All Øvrige-trafikk | Systemet (modell + baseline for resten) | 996 | 47,2 % (470/996) | 131,3 | 34,2 |
| 24 t | All Øvrige-trafikk | Baseline | 996 | 46,6 % (464/996) | 135,8 | 34,3 |
| 24 t | Passasjer (kontrollgruppe) | Baseline | 431 | 79,6 % (343/431) | 22,5 | 5,7 |

## Dekning ved kuttet

Anløp i testperioden: 1566.

| Horisont | Øvrige-anløp | Med fasit | Med AIS-tilstand ved kuttet | I sonen ved kuttet (F6) | Modellutvalget | Modellutvalget med fasit | Forsinkede i modellutvalget, av alle forsinkede Øvrige | Passasjer med fasit |
|---|---|---|---|---|---|---|---|---|
| 6 t | 1119 | 996 | 1012 | 200 | 812 | 733 | 57 av 194 | 431 av 447 |
| 24 t | 1119 | 996 | 1011 | 191 | 820 | 742 | 78 av 194 | 431 av 447 |

- Av 1 119 Øvrige-anløp i testperioden har 1 012 (6 t) og 1 011 (24 t) en gyldig AIS-posisjon i døgnet før kuttet. Dekningsfila fra hentingen (`data/utdrag/ais_kutt_dekning.csv`) teller 1 013 og 1 012. Forskjellen er posisjoner med AIS-verdiene for «ikke tilgjengelig», som ikke regnes som gyldige (beslutning 11).
- Hentingen hadde ingen manglende dager i testperioden.

## Begrensninger

- **Varselet kan nå under halvparten av de forsinkede anløpene, uansett hvor god modellen er.** Av 194 forsinkede Øvrige-anløp i testperioden ligger bare 57 (6 t) og 78 (24 t) i modellutvalget. Resten er turer inne i ankomstsonen ved kuttet (F6) eller anløp uten AIS-posisjon ved kuttet. De får baselinen, som ikke kan varsle. Derfor er systemets F1 for all Øvrige-trafikk lavere enn «varsle alle».
- **Etiketten for turer inne i havneområdet.** For anløp som allerede er i ankomstsonen ved kuttet (F6), måler etiketten (soneinngang) ikke en ankomst (beslutning 03). Disse anløpene er tatt ut av modellutvalget og gis baselinen (beslutning 12). Det er grunnen til at bestått/ikke bestått avgjøres på modellutvalget, og til at varselbarrieren ble lavere enn opprinnelig. Barrieren ble flyttet etter at valideringstallene var kjent (E2-S05, beslutning 12), men før testkjøringen.
- **Testperioden er vinterhalvåret** (14.09.2025–15.03.2026, høst og vinter). Resultatet sier ingenting om sommeren. Valideringen (mai–13.09.2025) var for det meste sommer, og F1 falt fra validering til test.
- **AIS-hull.** Anløp uten gyldig posisjon i døgnet før kuttet får baselinen (107 og 108 Øvrige-anløp ved 6 t og 24 t). Modellen er bare målt der den har AIS.
- **A1: rapportert ETA ved `t_H`.** Datasettet har én rapportert ETA per seilas og ingen tidsstempel for når den ble meldt. Er den oppdatert etter `t_H`, har både modell og baseline fått mer informasjon enn vakta hadde. Det kan ikke verifiseres i dataene (beslutning 11).
- **Avgangshavn og ETD (F13–F14).** De kommer fra en seilaspost som kan være satt sammen i etterkant, og kan ikke verifiseres. ETD brukes bare når den ligger før `t_H`. Bestått ved 24 t avhenger av disse feltene (ablasjonen over).
- **Én testperiode, én kjøring.** Det er ikke regnet konfidensintervaller for andelene eller effektstørrelse for den parvise forskjellen. McNemar-testen er en tilleggsanalyse regnet etter kjøringen, uten korreksjon for to horisonter.

## Ble målene nådd?

- **Hovedmålet (±30 min på modellutvalget):** ja, ved begge horisonter. Ved 6 t er forbedringen klar. Ved 24 t er den seks anløp, kan ikke skilles fra tilfeldig variasjon (p = 0,64), og forsvinner uten F13–F14.
- **Varsel (F1 over «varsle alle» på modellutvalget):** ja, ved begge horisonter (0,46 mot 0,14 og 0,44 mot 0,19). For all Øvrige-trafikk er systemet dårligere enn «varsle alle» (0,19 og 0,21 mot 0,33).
- **Datakvalitet:** AIS-dekningen ved kuttet er logget (over og i `data/utdrag/ais_kutt_dekning.csv`).
- **Produkt (den daglige briefen for havnevakta):** avgjøres ikke av denne kjøringen. Det hører til E3.

## Feil funnet etter kjøringen

- **I testkjøringen (`scripts/evaluer.py --test`):** ingen.
- **I tilleggsanalysen:** første versjon av `scripts/mcnemar.py` avrundet p-verdien til 6 desimaler, og 6 t ble lagret som `0.0`. Den ble rettet til 6 gjeldende siffer, og p ble regnet på nytt fra den lagrede krysstabellen, uten nytt gjennomløp av testradene. Krysstabellen ble ikke endret. Testen sjekker nå p-verdien med relativ toleranse.
- **I dashbordet, etter sammenslåingen med `main` (PR #6):** siden rullet horisontalt ved 640 px (200 % zoom, UU6), fordi visningsnavnet «Spesialfartøy» og modellens varseltekster sammen gjorde tabellen for bred. Det er rettet med en myk bindestrek i visningsnavnet. Feilen påvirket ingen tall.

## Reproduksjon

Testkjøringen skal ikke gjøres på nytt (`--ny-testkjoring` er ikke brukt). Tabellene lages fra de committede filene med `.venv/bin/python scripts/resultattabeller.py`, og McNemar-tabellen med `.venv/bin/python scripts/mcnemar.py --bare-tabell` fra `data/modell/mcnemar.json`. Ingen av dem leser testradene.
