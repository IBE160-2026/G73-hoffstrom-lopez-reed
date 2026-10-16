# Plan — G73

> **Dette er et FORSLAG, ikke en vedtatt plan.** Theodor justerer den med resten av gruppa. Milepælene er tidsestimater, ikke løfter, og arbeidsdelingen er en startpunkt-skisse basert på tre naturlige arbeidsstrømmer i prosjektet — ikke en vurdering av hvem som kan hva.

**Sluttfrist:** 15. desember 2026 (oppgitt av gruppa).
**Sist oppdatert:** 16. oktober 2026, etter faglærers tilbakemelding på product brief (se `docs/tilbakemelding-product-brief.md`).
**Modellarbeid startet:** 6. oktober 2026 (fast, avtalt).

Omtrent 11 uker fra briefen ble ferdigstilt (27. sep) til frist — se `docs/vurderingskriterier.md` for hvordan Del 1 (70 % av karakteren) og refleksjonsrapporten (30 %) faktisk vurderes.

## Milepæler

### Fase 1 — Datapipeline ✅ fullført (17. sep – 28. sep)

- Full AIS-henting fullført for hele perioden (8 094 seilaser, 2024–2026).
- `derive_arrivals.py` kjørt på fullbatchen: 87,1 % dekning, kalibrert baseline, liggetid-fordeling, skjevhetssjekk — alt låst med ekte tall.
- Datasettoppsummering skrevet (`docs/addendum.md`), brief oppdatert med faktiske tall (`docs/brief.md`).
- **Leveranse (levert):** et låst, dokumentert datasett (`pipeline/data/bergen_eta_avvik.csv`) klart for modellarbeid.

### Fase 2 — Modell + UX-skisser, parallelt (6. okt – 9. nov, ~5 uker)

To spor som går samtidig, ikke etter hverandre — UX skal **ikke** vente til dashbordet skal bygges.

**Modell-sporet:**
- Baseline: kalibrert rapportert-ETA som gulv å slå (allerede etablert i pipelinen).
- Tren første prediksjonsmodell(er) for 6t- og 24t-horisont mot `arrival_in_area`.
- Evaluer mot hovedmetrikken (andel innenfor ±30 min) og sekundærmetrikken (presisjon/recall på `er_forsinket`-flagget) — se `docs/brief.md`.
- Iterer på modellvalg og features; vurder om rutegående/ikke-rutegående bør modelleres separat, gitt hvor ulikt de to gruppene oppfører seg.
- **Leveranse:** en trent modell som slår den kalibrerte baselinen, med resultater rapportert etter strukturen i Success Criteria.

**UX-sporet (nytt, starter nå — kriterium 4 i `docs/vurderingskriterier.md`):**
- Skisser/wireframes eller skjermbeskrivelser for dashbordets kjerneskjermbilde: listevisning over anløp, kart, begrunnelsestekst per avvik. Trenger ikke kode — penn-og-papir eller enkle mockups holder, men de skal ligge i repoet (`docs/ux/` eller tilsvarende).
- Universell utforming tas inn i kravene fra start, ikke ettermontert: kontrast, tastaturnavigasjon, alt-tekst på kart/ikoner, og at skjermbildet fungerer på minst to skjermstørrelser (bærbar + mindre skjerm).
- **Leveranse:** skjermbeskrivelser klare *før* Fase 3 starter, slik at dashbordbyggingen har noe konkret å bygge mot i stedet for å designe underveis.

### Fase 3 — Rapporteringslag og grensesnitt, bygget fra UX-skissene (10. nov – 30. nov, ~3 uker)

- Generativt AI-lag: daglig forstyrrelsesbrief med kart og begrunnelse per forventet avvik.
- Nettbasert dashbord (v1: ingen innlogging, se `docs/addendum.md` for begrunnelse), bygget etter skjermbeskrivelsene fra Fase 2 — ikke design-fra-bunn-mens-vi-koder.
- Kobling mellom modellens output og dashbordet.
- **Leveranse:** en fungerende ende-til-ende demo en havnevakt kan bla gjennom, og som sensor kan kjøre lokalt (se kriterium 6 i `docs/vurderingskriterier.md` — versjonert datautdrag og testmodus for AI-laget må være på plass her, ikke i Fase 4).

### Fase 4 — Testing, polering, levering (1. des – 15. des, ~2 uker)

- Ende-til-ende-testing av hele kjeden (data → modell → rapport → dashbord), inkludert automatiske tester av pipelinen (kriterium 3 — finnes ikke ennå).
- Ferdigstill refleksjonsrapporten (se egen seksjon under — skal være i hovedsak skrevet innen denne fasen starter, ikke påbegynt her).
- Buffer for forsinkelser — dette er bevisst satt av, ikke fylt med nye oppgaver.
- Presentasjon/demo-forberedelse hvis kurset krever det.
- **Leveranse:** innlevert prosjekt, 15. desember.

## Refleksjonsrapporten — egen leveranse, løpende (30 % av karakteren)

Ikke en avsluttende oppgave i Fase 4 — den skrives **underveis**, fordi mye av innholdet (utfordringer, hvor KI bommet, hva vi rettet, hvorfor vi endret metode) allerede finnes i `docs/beslutninger/` og `docs/prompts/` mens det er ferskt. Å vente til desember betyr å rekonstruere ting vi allerede har skrevet ned én gang.

- **Omfang:** 3 000–5 000 ord, individuelle refleksjoner fra Theodor, Felipe og Thomas (ikke én felles tekst).
- **Nå – 9. nov (gjennom Fase 2):** hver person fører egne løpende notater — hva var vanskelig, hvor tok KI feil, hva måtte rettes manuelt. `docs/beslutninger/` og `docs/prompts/` er kilden, ikke noe å finne opp i etterkant.
- **10. nov – 30. nov (gjennom Fase 3):** samme praksis videreføres for AI-lag- og dashbordarbeidet.
- **1. des – 10. des:** hvert individuelt utkast skrives ferdig fra notatene.
- **10. des – 15. des:** siste gjennomlesing, sammen med resten av innleveringen.
- **Leveranse:** tre individuelle refleksjoner, innlevert 15. desember sammen med Del 1.

## Forslag til arbeidsdeling

Delt etter de naturlige arbeidsstrømmene i prosjektet — bytt fritt basert på hvem som faktisk vil/kan hva. Alle tre bør ha vært innom datapipelinen, siden modellarbeidet bygger direkte på den, og alle tre skriver sin egen refleksjon uavhengig av hvem som gjør hva teknisk.

| Arbeidsstrøm | Forslag | Dekker |
|---|---|---|
| Data & pipeline | Theodor | Datakvalitet, kalibrering, dokumentasjon av beslutninger (fullført, vedlikehold videre) |
| Modell | Felipe | Feature-arbeid, trening, evaluering mot suksesskriteriene |
| UX & grensesnitt | Thomas | Skjermbeskrivelser/wireframes (Fase 2), dashbord og generativt AI-lag (Fase 3) |

I fase 2 og 3 er det naturlig at alle tre bidrar på tvers — spesielt evaluering (fase 2) og integrasjon (fase 3) krever samarbeid mellom data-, modell- og grensesnittarbeidet.

## Arbeidsflyt fra nå av

**Branch per story, pull request inn til main.** Ikke flere commits rett på main. Sensor ser etter branches, PR-er og issues som spor på arbeidsflyt — det er en del av kriterium 1 og 7 i `docs/vurderingskriterier.md`.

## Åpne spørsmål til gruppa

- **PRD, arkitektur og epics/stories med BMAD** — faglærers tilbakemelding peker på dette som det største hullet i sporbarheten (kriterium 1, 30 % vekt): briefen er konkret, men ingenting er bygget på den ennå. Ikke lagt inn som egen fase her fordi det er en beslutning om *når* og *hvor mye* som bør tas med hele gruppa — men det bør trolig skje tidlig i Fase 2, ikke underveis i Fase 3.
- Er det delfrister før 15. desember (presentasjon, statusmøte) som bør inn som egne milepæler?
- Skal rutegående og ikke-rutegående trafikk modelleres som to separate modeller, gitt hvor ulikt de oppfører seg (se `docs/beslutninger/05-andel-innenfor-30-min-fremfor-mae.md`)?
