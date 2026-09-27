# Hentevindu utvidet, og trimmet av neste seilas' ETD

## Kontekst

Vi trenger et tidsvindu rundt hvert anløps rapporterte ETA å hente AIS-posisjoner innenfor. Vinduet må være bredt nok til å fange opp reelle avvik, men ikke så bredt at det plukker opp feil hendelse.

## Alternativer vurdert

- **Fast vindu ETA ± 12 timer.** Første forsøk.
- **Bredere, asymmetrisk vindu**: start = seilasens egen ETD (med et fornuftstak på 14 dager, ellers ETA − 24 timer), slutt = ETA + 48 timer.
- **Vindu trimmet av neste seilas.** Samme som over, men sluttidspunktet kappes ved neste kjente seilas' ETD for samme MMSI, dersom det finnes.

## Valg

Asymmetrisk vindu (ETD/ETA−24t til ETA+48t), trimmet av neste seilas' ETD for samme skip når det finnes.

## Begrunnelse

Et fast ±12-timersvindu dropper systematisk nettopp de anløpene som bommer mest på egen ETA — det er ikke tilfeldig datatap, det er skjevt datatap som trekker hovedfunnet mot null. Den brede varianten løser det, men skaper et nytt problem for skip med hyppige anløp (ferger): et vidt vindu rundt én seilas kan strekke seg inn i *neste* seilas for samme skip, og gap-regelen plukker da opp feil ankomst — observert direkte som avvik på nær 48 timer, rett ved den gamle vinduskanten. Løsningen er å gruppere seilaser per MMSI, sortere kronologisk, og kutte hvert vindu ved neste seilas' ETD.

Når søket når den grensen uten å finne en hendelse, merkes raden `avkortet_av_neste_seilas` — ikke som "ikke oppdaget". Et skip som ankommer etter neste seilas' ETD er nettopp et ekstremavvik vi vil fange, og å la det forsvinne stille ville skjevt resultatet i feil retning (mot at skip ser mer presise ut enn de er).

## Konsekvens

Vinduslogikken må dupliseres identisk i både hentesteget (`fetch_ais.py`) og utledningssteget (`derive_arrivals.py`), siden sistnevnte må vite nøyaktig hvilket vindu som faktisk ble hentet. `avkortet_av_neste_seilas` er en egen statuskategori i output, atskilt fra `not_detected`, og må telles og rapporteres separat.
