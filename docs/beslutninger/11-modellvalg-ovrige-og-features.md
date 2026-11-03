# Én modellfamilie for Øvrige, og featurelista F1–F16

## Kontekst

Beslutning 08 avgjorde horisonten. Etter den sto tre spørsmål åpne i PRD §8 og E2-S01: én eller to modeller (Passasjer/Øvrige), om rapportert ETA er kjent ved `t_24` (A1), og om suksesskriteriet for varsel holder (A2). E2-S03–S05 trenger dessuten en fast featureliste før de kan specces.

Historisk avvik per fartøy er en kjent lekkasjefelle. Regnes det på hele datasettet, får modellen fasiten fra testperioden.

Felipe avgjorde spørsmålene 03.11.2026 (spec: `_bmad-output/implementation-artifacts/spec-e2-s01-modellvalg.md`).

## Alternativer vurdert

- **Én modell for begge gruppene.** Forkastet. Passasjer er rutegående og treffer 79,6 % innenfor ±30 min uten modell (FR8). Det er Øvrige som har halen på 19,5 %, og det er den modellen skal angripe. En felles modell ville brukt kapasitet på en gruppe som allerede er løst.
- **To modeller, én per gruppe.** Forkastet av samme grunn. En Passasjer-modell har lite å vinne, og den gir én artefakt til å trene, teste og forklare.
- **Én modell, bare for Øvrige.** Valgt.
- **Én modell med H som feature.** Forkastet. Inputen er ulik i art ved de to horisontene: ved 24 t ligger skipet ofte i forrige havn, og ved 6 t er det underveis (beslutning 08).

## Valg

1. **Én modellfamilie, bare for Øvrige, trent én gang per horisont.** Det gir to artefakter, `modell_6t` og `modell_24t`.
   - **Passasjer** beholder den kalibrerte baselinen. Modellprediktoren delegerer Passasjer-rader til baselinen, og `forklaring["metode"]` viser hvilken som ble brukt.
   - **Øvrige uten AIS-tilstand** ved `t_H` får også baselinen (FR9a). «Uten tilstand» betyr ingen gyldig posisjon i [`t_H` − 24 t, `t_H`]. Posisjoner med bredde 91 eller lengde 181 (AIS-verdiene for «ikke tilgjengelig») regnes ikke som gyldige. En rad med gyldig posisjon, men uten fart eller kurs, går til modellen med tomme felt. Modellfamilien må derfor tåle manglende verdier, enten selv (for eksempel `HistGradientBoostingRegressor`) eller med en imputering som bare fittes på treningsdata (E2-S05).
2. **A1 kan ikke verifiseres, og føres som en eksplisitt begrensning, ikke som en antakelse.** Datasettet har én rapportert ETA per seilas og ingen tidsstempel for når den ble meldt. **Grunnlag:** seilas-endepunktet i Kystdatahuset (`/api/voyage/between/{fra}/{til}`), som datasettet er hentet fra, returnerer tidsfeltene `eta` og `etd` per seilas. Det har ikke noe felt for når ETA-en ble meldt eller sist oppdatert. Felipe opplyste at dette ble sjekket mot det kjørende API-et 10.09.2026. Det stemmer med feltlista i `pipeline/fetch_voyages.py` (`FIELDS`), der `eta` er det eneste ETA-feltet. Det er dermed ikke mulig å avgjøre i dataene hvilken ETA vakta så ved `t_H`, og sjekken PRD §8 planla er lukket med dette.
3. **A2 beholdes, og A3 står uendret**: varselet er fortsatt en terskel på predikert avvik (> 120 min). **A2:** Modellen lykkes på varsel hvis F1 er høyere enn regelen som varsler alle anløp. Referansen er presisjon 19,5 %, recall 100 % og F1 ≈ 0,33 for Øvrige i testperioden.
4. **Featurelista F1–F16 er låst** (tabellen under).
5. **Fartøyhistorikken (F15–F16) regnes bare på treningsdata.** Den bruker bare treningsrader med samme MMSI og `arrival_in_area < t_H` for raden som predikeres, og aldri raden selv. Snittet for Øvrige som F15 trekkes mot, regnes også bare på treningsrader med ankomst før `t_H`. Avvik fra testperioden går aldri inn i noen feature, og testrader telles aldri i F16.
   - **Valideringsradene får historikk bare fra treningsdelen, frosset ved grensen, slik testradene får** (oppdatert 03.11.2026, E2-S04, Felipe). Ellers ville valideringen fått ferskere historikk enn testen, og modellvalget sett bedre ut enn testen viser. Den endelige treningen bruker historikk fra trening og validering samlet. Featurefila har derfor F15–F16 i to varianter: `*_modellvalg` og endelig.
   - **Ingen treningsrader før `t_H`:** finnes det ingen Øvrige-treningsrader med ankomst før `t_H` (de tidligste radene), er snittet det trekkes mot 0. Fartøyet uten historikk får F15 = det snittet og F16 = 0.
   - Avviket i F15 er kalibrert med offseten fra `baseline.json`, som er fittet på hele treningsdelen. Det er en konstant forskyvning av alle verdier, både fartøyets snitt og snittet det trekkes mot. Den bærer derfor ingen informasjon om senere ankomster og er ikke en lekkasje.
6. **Avgangshavn og ETD (F13–F14) beholdes** med en begrensning ved siden av A1, og det trenes en **ablasjon** uten dem.
7. **Rader der skipet allerede er i ankomstsonen ved `t_H`** (F6 sann) rapporteres for seg: alle tall for modell mot baseline oppgis både med og uten disse radene. Splitten bruker F6, som er regnet fra posisjonen. **Oppdatert 03.11.2026 (E2-S03, Felipe):** F6 er den eneste definisjonen av «allerede i ankomstsonen ved kuttet» i hele E2-rapporten, både for splitten og for antallet. Et flagg regnet fra faktisk ankomst brukes ikke, og `allerede_ankommet` er tatt ut av tilstandsutdraget.
8. **Kontrakten i arkitektur §3 endres ikke av denne beslutningen.** Delegeringen skjer inne i `ModellPrediktor`, og `forklaring` har allerede `metode`. Prediktoren beholder `kan_varsle = True`. Rader som delegeres til baselinen, får `forventet_forsinket = None` og `forklaring["metode"] = "baseline"`.
   - **Hvordan F1–F16 når prediktoren, avgjøres i E2-S07.** Både tilstand, statiske felt og ferdigregnet historikk skal gå gjennom `lag_input` eller en søsterfunksjon i `__init__.py`, aldri ved at prediktormodulen leser `data/utdrag/` selv. AST-testen gjelder uendret. F15–F16 er ferdig aggregerte tall regnet i E2-S04 og gir ingen vei til `faktisk_ankomst` for raden selv.
   - Må `PrediksjonsInput` få nye felt, er det en kontraktendring. Den tas da i en egen PR som Thomas (dashbord) og Felipe (modell) begge godkjenner (arkitektur §3), og eieren av AI-laget (E3) ser også på den, fordi `forklaring` mates dit.

### Featurelista

Bare rader for Øvrige som har AIS-tilstand ved `t_H`, går til modellen.

| # | Feature | Kilde, og hvorfor den er kjent ved `t_H` |
|---|---|---|
| F1 | `distanse_km` til referansepunktet for havna | siste AIS ≤ `t_H` (E2-S03) |
| F2 | `fart_knop` (fart over grunn) | siste AIS ≤ `t_H` |
| F3 | `kurs_mot_havn` = cos(kurs over grunn − peiling til havna), i [−1, 1]. Tom når kursen mangler eller er ≥ 360 (AIS «ikke tilgjengelig»), når farten er under 1 knop (kursen er da støy), og når distansen er 0 | siste AIS ≤ `t_H`. Rå kurs er sirkulær (359° ≈ 1°). |
| F4 | `posisjon_alder_min` | `t_H` − tidspunktet for posisjonen |
| F5 | `lat`, `lon` | siste AIS ≤ `t_H`. Skiller rutene fra nord og sør. |
| F6 | `i_sonen_ved_kutt` (0/1) | regnet fra posisjonen (distanse ≤ 15 km, samme radius som ankomstsonen i beslutning 03 og `OUTER_RADIUS_KM` i `derive_arrivals.py`), **ikke** fra et flagg regnet fra faktisk ankomst |
| F7 | `slakk_timer` (definert under) | utledet av F1 og F2 |
| F8 | `skipstype` (kategori). Typer med færre enn 20 Øvrige-rader i dataene modellen fittes på, slås sammen til `annet`, og det samme gjelder manglende og ukjente typer | statiske seilasdata |
| F9 | `lengde_m`, tom hvis den mangler | statiske seilasdata |
| F10 | tid på døgnet for ETA, som sin/cos av timen | rapportert ETA i norsk tid |
| F11 | ukedag for ETA | rapportert ETA i norsk tid |
| F12 | måned for ETA, som sin/cos | rapportert ETA. Testen er vintervridd, og treningen dekker to vintre. |
| F13 | `avgangshavn`. Havner med færre enn 20 Øvrige-rader i dataene modellen fittes på, slås sammen til `annet`, og det samme gjelder manglende og ukjente havner | seilasdata, se begrensningene |
| F14 | `avgatt_for_kutt` (0/1), og `timer_siden_avgang` bare når ETD ≤ `t_H`, ellers tom. Mangler ETD, er begge tomme | ETD brukes bare når den ligger ved eller før `t_H` |
| F15 | `fartoy_snittavvik_min`: fartøyets snitt av kalibrert avvik, `(n · snitt + 5 · snitt_Øvrige) / (n + 5)` | se valg 5 |
| F16 | `fartoy_antall_tidligere` | se valg 5 |

Tersklene for F8 og F13 og alle kategorilister fittes på dataene modellen trenes på. Ved modellvalget er det treningsdelen uten valideringsdelen, og testperioden brukes aldri.

**F7 ved fart null eller nær null.**
- Formelen er `slakk_timer = H − (distanse_km / 1,852) / max(fart_knop, 1,0)`, klippet til [−48, H].
- H betyr her tiden fra kuttet til rapportert ETA, `eta_reported − t_kutt` i timer. Med dagens utvalg er det nøyaktig 6 eller 24. Om klemmen mot «nå» i arkitektur §3 noen gang slår inn, blir F7 likevel riktig.
- Klippingen til [−48, H] hindrer at skip langt unna i ro gir ekstreme verdier (for eksempel −246 t for 500 km ved 1 knop). Under −48 t er skipet uansett langt fra å rekke ETA-en.
- Fart under 1 knop regnes som 1 knop, så et skip som ligger stille ikke gir uendelig slakk.
- Distanse 0 gir `slakk_timer = H`.
- Mangler farten, eller er den ≥ 102,3 knop (AIS-verdien for «ikke tilgjengelig»), blir F2 og F7 tomme.

Positiv slakk betyr at skipet rekker ETA-en med farten det har nå.

**Med vilje utelatt:**
- `arrival_in_area`, `arrival_at_quay`, dwell- og statusfelt for samme seilas. De er fasit.
- `window_start`, `window_end_used` og `truncated_by_next_voyage`. De avhenger av neste seilas, som ligger i framtida.
- ETD-verdien når ETD > `t_H`.
- Statistikk regnet over testperioden.
- Rå `mmsino` og `shipname` som ID-er. Fartøyet er dekket av F15–F16, og rå ID-er gir overtilpasning.
- Et flagg for «allerede ankommet» regnet fra faktisk ankomst. Det er utledet av fasiten, og F6 tar samme signal fra posisjonen (valg 7).

## Begrunnelse

**Én modellfamilie for Øvrige** retter innsatsen mot problemet: halen som baselinen ikke klarer. Passasjer vises fortsatt med baselinen, som i E1, så dashbordet og sammenligningen med E1 er uendret for den gruppen.

**Featurelista** etterligner det vakta ser ved `t_H`: hvor skipet er, hvor fort og hvilken vei det går, hva slags skip det er, når det har meldt seg, og hvordan dette fartøyet pleier å treffe. Alt kan regnes fra data før kuttet.

**Ablasjonen og F6-splitten** gjør tallene ærlige på to punkter vi ikke kan lukke helt:
- Avgangshavna kan være satt i etterkant. Ablasjonen viser hvor mye modellen hviler på den.
- Et skip som allerede er i sonen, er nesten fasit. Modellen ser det, men baselinen gjør det ikke. Splitten viser om forspranget kommer derfra.

## Konsekvens

- **PRD:** FR9 og FR10 er oppdatert. A1 og avgangshavna er ført under kjente begrensninger i §7. §8 er lukket for E2-S01, og A1 og A2 er tatt ut av §9. A3 står uendret.
- **E2-S04:** `app/prediksjon/features.py` bygger F1–F16. Skipstype, lengde, ETD og avgangshavn finnes bare i den gitignorerte seilasfila i `pipeline/data/`, og den låste `data/utdrag/anlop.csv` skal ikke endres. E2-S04 skriver derfor F1–F16 til en committet `data/utdrag/features.csv`, uten rå ETD (oppdatert 03.11.2026: det finnes ikke noe eget rått utdrag). Alt E2 committer under `data/` skal til sammen være under 10 MB (NFR1).
  - `tests/test_features.py::test_fartoyhistorikk_bare_fra_trening`:
    - Endres alle avvik i testperioden og radens eget, er F15, F16 og snittet det trekkes mot, identiske for alle rader.
    - Legges testrader til, fjernes de eller flyttes de i tid, er F16 identisk.
    - Endres avviket til én treningsrad, endres bare rader med `t_H` etter den radens ankomst.
    - Uten treningsrader før `t_H` er snittet det trekkes mot 0, og F16 er 0.
  - `tests/test_features.py::test_slakk_ved_lav_fart`: fart 0, 0,3, 1,0 og 12 knop, manglende fart og 102,3 knop. I tillegg `::test_kurs_ugyldig` (kurs 360, manglende kurs, fart < 1 knop og distanse 0 gir tom F3).
- **Størrelse (NFR1):** alt E2 committer under `data/`, det vil si begge utdragene, fire modellartefakter og `metrikker.json`, skal til sammen være under 10 MB.
- **E2-S05:** per horisont trenes hovedmodellen og en ablasjon uten F13–F14, bare på Øvrige. Det gir fire artefakter. Testen viser at ingen Passasjer-rader er med i treningen, og at ablasjonen ikke har F13–F14.
- **E2-S06 og E2-S10:** modell mot baseline rapporteres for begge modellene og både med og uten F6-rader. Passasjer rapporteres bare som baseline. Testen for E2-S06 sjekker at `metrikker.json` har nøklene for ablasjonen og for uten F6, og at Passasjer bare har baseline.
- **E2-S07:** `ModellPrediktor` (`kan_varsle = True`) delegerer Passasjer og rader uten tilstand til `BaselinePrediktor`. Delegerte rader får `forventet_forsinket = None` og `forklaring["metode"] = "baseline"` (valg 8).

**Begrensninger som rapporteres i resultatnotatet (E2-S10):**
- **A1.** Vi vet ikke om ETA-en er slik den var meldt ved `t_H`, eller en senere oppdatering. Både modell og baseline kan da ha fått litt mer informasjon enn vakta hadde.
- **Avgangshavn og ETD.** De kommer fra en seilaspost som kan være satt sammen i etterkant. ETD brukes bare når den ligger før `t_H`, og avgangshavna måles med ablasjonen.
