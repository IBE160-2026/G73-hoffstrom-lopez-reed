# Status — AIS-basert ankomstprediksjon

For Felipe og Thomas. Dere har ikke sett noe av dette arbeidet ennå — dette er en overlevering, ikke en detaljert logg. Full produktbrief: [`docs/brief.md`](brief.md). Full teknisk begrunnelse: [`docs/addendum.md`](addendum.md) og [`docs/beslutninger/`](beslutninger/).

## Hvor vi står

Vi har hentet og prosessert et komplett datasett: **8 094 seilaser** som ankommer Bergen Havn, jan. 2024–mars 2026, fra Kystverkets åpne Kystdatahuset-API. For hver seilas har vi forsøkt å utlede når skipet *faktisk* ankom (ikke bare hva det selv rapporterte som ETA), basert på rå AIS-posisjoner.

To ting datasettet gir oss:

1. **Dekning: 87,1 %.** For 87,1 % av seilasene kan vi fastslå faktisk ankomsttidspunkt (`arrival_in_area` — første AIS-posisjon innenfor en ~15 km sone rundt havna). De resterende ~13 % mangler AIS-data helt, se "Hva er åpent".
2. **Kalibrert baseline.** Skipets egen rapporterte ETA er ikke direkte sammenlignbar med ankomsttidspunktet vi utleder (de måler litt ulike ting — se `docs/beslutninger/04-kalibrert-baseline.md`). Justert for det treffer den rapporterte ETA-en, for **ikke-rutegående trafikk** (frakt, offshore, osv. — ikke ferger):
   - **46,6 %** av ankomstene innenfor ±30 minutter
   - **24,3 %** av ankomstene bommer med over 2 timer, selv etter justering

   Det siste tallet er det viktigste: **det er den halen modellen skal angripe.** Rutegående trafikk (ferger) er nesten løst allerede — 79,6 % innenfor ±30 min uten noen modell i det hele tatt — og holdes derfor utenfor hovedresultatet som kontrollgruppe, ikke som del av målet.

## Hva er bestemt og ligger fast

Alle metodevalg er logget som egne beslutninger med kontekst, alternativer og begrunnelse — les dem hvis noe virker rart, ikke bare stol på tallet:

- [`01-henting-per-mmsi.md`](beslutninger/01-henting-per-mmsi.md) — hvordan AIS-data hentes
- [`02-hentevindu-trimmet-av-neste-seilas.md`](beslutninger/02-hentevindu-trimmet-av-neste-seilas.md) — tidsvinduet per seilas
- [`03-soneinngang-som-hovedetikett.md`](beslutninger/03-soneinngang-som-hovedetikett.md) — hva "ankomst" faktisk betyr i dataene
- [`04-kalibrert-baseline.md`](beslutninger/04-kalibrert-baseline.md) — hvorfor ETA-en må justeres for å sammenlignes
- [`05-andel-innenfor-30-min-fremfor-mae.md`](beslutninger/05-andel-innenfor-30-min-fremfor-mae.md) — hvorfor ±30 min er hovedtallet, ikke MAE
- [`06-signert-forsinkelsesflagg.md`](beslutninger/06-signert-forsinkelsesflagg.md) — hvordan "forsinket" er definert
- [`07-manglende-ais-utenlandske-skip.md`](beslutninger/07-manglende-ais-utenlandske-skip.md) — se under

## Hva er åpent

- **De ~13 % uten AIS-data.** Rammer nesten bare utenlandskflaggede skip. To mulige forklaringer (tilgangsbegrensning vs. utdatert MMSI-registrering) — ingen er bekreftet, se beslutning 07. Ikke noe å fikse nå, bare vær klar over at ikke-rutegående trafikk systematisk er underrepresentert i datasettet av en grunn vi ikke fullt forstår.
- **Skjevhet i kalibreringen.** Offset-tallet (44,8 min rutegående / 64,2 min ikke-rutegående) er beregnet på et utvalg som overrepresenterer større, mer rutepregede skip — det er de typene der vi klarer å utlede kaitidspunkt i tillegg til soneinngang. Dokumentert, ikke korrigert.
- **Vintervridd testsett.** Splitten som brukes til evaluering er kronologisk (riktig valg for å unngå lekkasje), men det betyr testperioden er sep. 2025–mars 2026 — i hovedsak vinterhalvår. Ikke trekk konklusjoner om sommertrafikk fra disse tallene.

## Neste steg — 6. oktober

Modellarbeidet starter. To ting bør være avklart i gruppa *før* det:

1. **Featureliste.** Hva skal modellen faktisk trene på utover historisk avvik (værdata? sesong? skipstype/-lengde? tid på døgnet?). Ikke bestemt ennå.
2. **Arbeidsdeling.** Det ligger et forslag i [`docs/plan.md`](plan.md) — det er kun et forslag, juster det dere tre imellom.

Målet modellen skal slå står i `docs/brief.md` under Success Criteria: 46,6 % innenfor ±30 min og bedre presisjon/recall på 24,3%-halen, målt på ikke-rutegående trafikk.

## Kjøre pipelinen fra bunn (hvis cachen mistes)

`pipeline/data/` er gitignored — hele datasettet må regenereres om noen sletter det lokalt. Kun Python standardbibliotek trengs, ingen `pip install`. Full forklaring i [`README.md`](../README.md), kort versjon:

```
python3 pipeline/fetch_voyages.py --from-date 2024-01-01 --to-date 2026-03-15
python3 pipeline/fetch_ais.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv
python3 pipeline/derive_arrivals.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv
```

Steg 2 tar flere timer (offentlig API, ~8 000 kall med pause mellom hvert) — kjør det med `caffeinate -i` foran på Mac, ellers kan maskinen sove og henge tilkoblingen underveis. Alt caches per seilas, så et avbrutt kjør plukkes opp igjen uten å starte på nytt.
