# Henting per MMSI fremfor bbox-skanning

## Kontekst

AIS-posisjoner kan hentes fra Kystdatahuset på to måter: `within-bbox-time` (alle skip innenfor et geografisk område og tidsvindu) eller `for-mmsis-time` (posisjoner for spesifikke skip, identifisert ved MMSI). Vi trengte en metode for å hente sporingsdata for hvert anløp i seilasdatasettet.

## Alternativer vurdert

- **Bbox-skanning** (`within-bbox-time`): henter alle skip innenfor en bounding box rundt havneområdet, uavhengig av hvilket skip vi faktisk er interessert i.
- **Per-MMSI-henting** (`for-mmsis-time`): henter posisjoner kun for det spesifikke skipet vi ser på, avgrenset til et tidsvindu rundt anløpet.

## Valg

Per-MMSI-henting.

## Begrunnelse

Bbox-skanning drar inn hvert skip som befinner seg i området, ikke bare det vi sporer — det gir langt mer data enn nødvendig og krever ekstra filtrering i etterkant. Viktigere: per-MMSI-henting er en forutsetning for gap-regelen (se beslutning 03) og vindu-trimmingen mot neste seilas (se beslutning 02). Når vi henter posisjoner for ett bestemt skip over et definert tidsrom, kan et opphold i rapporteringen bare bety at *dette skipet* har gått stille — ikke at det har forlatt et geografisk søkeområde som et annet skip så entret. Den logiske garantien bbox-skanning ikke gir.

## Konsekvens

All videre henting (`fetch_ais.py`) er bygget rundt én seilas + ett MMSI + ett tidsvindu om gangen. Dette gjør pipelinen tregere per anløp enn en bulk-bbox-henting ville vært, men gjør at gap-basert ankomstdeteksjon faktisk er gyldig å bruke.
