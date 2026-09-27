# Plan — G73

> **Dette er et FORSLAG, ikke en vedtatt plan.** Theodor justerer den med resten av gruppa. Milepælene er tidsestimater, ikke løfter, og arbeidsdelingen er en startpunkt-skisse basert på tre naturlige arbeidsstrømmer i prosjektet — ikke en vurdering av hvem som kan hva.

**Sluttfrist:** 15. desember 2026 (oppgitt av gruppa).
**I dag:** 27. september 2026.
**Modellarbeid starter:** 6. oktober 2026 (fast, avtalt).

Det gir omtrent 11 uker fra i dag til frist, hvorav de første ~1,5 ukene er datapipeline-sluttføring (allerede godt i gang) og resten fordeler seg på modell, rapporteringslag og polering.

## Milepæler

### Fase 1 — Datapipeline ferdigstilt (27. sep – 5. okt)

- Full AIS-henting fullført for hele perioden (kjører i skrivende stund).
- `derive_arrivals.py` kjørt på nytt på fullbatchen: dekningstall, kalibrert baseline, liggetid-fordeling, skjevhetssjekk — alt låst med ekte tall (ikke pilotestimater).
- Datasettoppsummering skrevet (se `docs/addendum.md`).
- Brief, addendum og beslutningslogg oppdatert til å reflektere fullbatch-tallene der pilottall i dag står som TBD.
- **Leveranse:** et låst, dokumentert datasett (`pipeline/data/bergen_eta_avvik.csv`) klart for modellarbeid.

### Fase 2 — Modell (6. okt – 9. nov, ~5 uker)

- Baseline: kalibrert rapportert-ETA som gulv å slå (allerede etablert i pipelinen).
- Tren første prediksjonsmodell(er) for 6t- og 24t-horisont mot `arrival_in_area`.
- Evaluer mot hovedmetrikken (andel innenfor ±30 min) og sekundærmetrikken (presisjon/recall på `er_forsinket`-flagget) — se `docs/brief.md`.
- Iterer på modellvalg og features; vurder om rutegående/ikke-rutegående bør modelleres separat, gitt hvor ulikt de to gruppene oppfører seg.
- **Leveranse:** en trent modell som slår den kalibrerte baselinen, med resultater rapportert etter strukturen i Success Criteria.

### Fase 3 — Rapporteringslag og grensesnitt (10. nov – 30. nov, ~3 uker)

- Generativt AI-lag: daglig forstyrrelsesbrief med kart og begrunnelse per forventet avvik.
- Nettbasert dashbord (v1: ingen innlogging, se `docs/addendum.md` for begrunnelse).
- Kobling mellom modellens output og dashbordet.
- **Leveranse:** en fungerende ende-til-ende demo en havnevakt kan bla gjennom.

### Fase 4 — Testing, polering, levering (1. des – 15. des, ~2 uker)

- Ende-til-ende-testing av hele kjeden (data → modell → rapport → dashbord).
- Skriv sluttrapport / kursleveranse.
- Buffer for forsinkelser — dette er bevisst satt av, ikke fylt med nye oppgaver.
- Presentasjon/demo-forberedelse hvis kurset krever det.
- **Leveranse:** innlevert prosjekt, 15. desember.

## Forslag til arbeidsdeling

Delt etter de tre naturlige arbeidsstrømmene i prosjektet — bytt fritt basert på hvem som faktisk vil/kan hva. Alle tre bør ha vært innom datapipelinen før fase 2 starter, siden modellarbeidet bygger direkte på den.

| Arbeidsstrøm | Forslag | Dekker |
|---|---|---|
| Data & pipeline | Theodor | Sluttføre fullbatch-kjøring, datakvalitet, kalibrering, dokumentasjon av beslutninger |
| Modell | Felipe | Feature-arbeid, trening, evaluering mot suksesskriteriene |
| Rapportering & grensesnitt | Thomas | Generativt AI-lag, dashbord, integrasjon mot modellens output |

I fase 2 og 3 er det naturlig at alle tre bidrar på tvers — spesielt evaluering (fase 2) og integrasjon (fase 3) krever samarbeid mellom data-, modell- og grensesnittarbeidet.

## Åpne spørsmål til gruppa

- Er det delfrister før 15. desember (presentasjon, statusmøte) som bør inn som egne milepæler?
- Er 10-ukers-rammen i briefen (Scope) fortsatt riktig gitt at sluttfristen faktisk gir ~11 uker fra i dag?
- Skal rutegående og ikke-rutegående trafikk modelleres som to separate modeller, gitt hvor ulikt de oppfører seg (se `docs/beslutninger/05-andel-innenfor-30-min-fremfor-mae.md`)?
