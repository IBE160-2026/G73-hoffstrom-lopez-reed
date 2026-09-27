# G73 — Gimnaldo og Lipe

Gruppeprosjekt i **IBE160 Programmering med KI** ved Høgskolen i Molde, høsten 2026 (15 studiepoeng).

Repoet inneholder gruppens applikasjon og dokumentasjon av utvikling, testing og kvalitetssikring med KI.

## Medlemmer

- Theodor Gimming Hoffstrøm
- Felipe Knudstad-Lopez
- Thomas Kvile-Reed

## Om prosjektet

Et AIS-basert beslutningsstøtteverktøy som predikerer når skip faktisk ankommer Bergen Havn — ikke bare når de selv rapporterer at de kommer. Kjernelabelen (`arrival_in_area`, soneinngang i havneområdet) måles mot hvert enkelt fartøys egen rapporterte ETA og skal etter hvert danne grunnlaget for prediksjoner på 6- og 24-timers horisont, rettet mot havnevakta ved Bergen Havns Maritime Operations Center.

Full produktbrief ligger i [`docs/brief.md`](docs/brief.md) (norsk versjon: [`docs/brief.no.md`](docs/brief.no.md)), med utdypende teknisk grunnlag i [`docs/addendum.md`](docs/addendum.md). Beslutninger tatt underveis i datapipelinen er logget enkeltvis i [`docs/beslutninger/`](docs/beslutninger/).

## Datakilder

- **Kystverkets Kystdatahuset Open API** (`https://kystdatahuset.no/ws/api/...`) — hovedkilden.
  - Seilasdata: `GET /api/voyage/between/{fromDate}/{toDate}`
  - AIS-posisjoner: `POST /api/ais/positions/for-mmsis-time`
  - Begge er åpne, uten innlogging — verifisert direkte mot det kjørende APIet i dette prosjektet.
- **BarentsWatch Live AIS** — dokumentert reserveløsning hvis Kystdatahuset-arkivet viser seg utilstrekkelig. Se reserveplanen i [`docs/addendum.md`](docs/addendum.md).

## Kjøre pipelinen

Alle skript er i `pipeline/` og bruker kun Python standardbibliotek — ingen `pip install` nødvendig.

**1. Hent seilaser som ankommer Bergen (NOBGO)**

```
python3 pipeline/fetch_voyages.py --from-date 2024-01-01 --to-date 2026-03-15
```

Henter måned for måned (holder minnebruket nede over et flerårig spenn) og skriver én CSV med alle unike Bergen-ankomster i perioden til `pipeline/data/voyages_bergen_<from>_<to>.csv`.

**2. Hent AIS-posisjoner per seilas**

```
python3 pipeline/fetch_ais.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv
```

Hvert fartøys posisjoner hentes i et vindu rundt egen ETA (fra seilasens etd, eller ETA−24t som reserve, til ETA+48t — trimmet av neste seilas' ETD for samme MMSI der det finnes). Ett resultat cachet per seilas i `pipeline/data/ais_cache/{voyageid}.json`, så et nytt kjør aldri henter en allerede cachet seilas på nytt. Dekning logges fortløpende til `pipeline/data/ais_coverage.csv`. Bruk `--limit N` for å kun kjøre en pilotbatch.

Dette er et offentlig API — skriptet holder en liten pause mellom hvert kall og prøver på nytt ved feil, i stedet for å presse på.

**3. Utled ankomsttidspunkt og avvik**

```
python3 pipeline/derive_arrivals.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv
```

Leser de cachede AIS-sporene og utleder to etiketter per seilas: `arrival_in_area` (hovedetikett — soneinngang, ingen fartsterskel) og `arrival_at_quay` (sekundær, mer presis men lavere dekning). Beregner en kalibrert baseline (rapportert ETA justert med medianliggetid fra havneområde til kai, estimert kun på treningsdata) og forsinkelsesflagget `er_forsinket`. Full kolonneliste finnes i `fieldnames` i skriptet; resultatet skrives til `pipeline/data/bergen_eta_avvik.csv`. Legg til `--sample N` for en manuell stikkprøve mot konsollen.

## Hvor data havner

Alt hentet og utledet data havner i `pipeline/data/` — **gitignored**, aldri committet. Mappen er fullt ut regenererbar ved å kjøre de tre stegene over på nytt, og kan bli flere gigabyte ved full historikk. Ikke forsøk å legge den til i git.
