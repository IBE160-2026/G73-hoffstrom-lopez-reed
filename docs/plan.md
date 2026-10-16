# Plan — G73

> **Dette er et FORSLAG, ikke en vedtatt plan.** Theodor justerer den med resten av gruppa. Milepælene er tidsestimater, ikke løfter, og arbeidsdelingen er en startpunkt-skisse basert på tre naturlige arbeidsstrømmer i prosjektet — ikke en vurdering av hvem som kan hva.

**Sluttfrist:** 15. desember 2026 (oppgitt av gruppa).
**Sist oppdatert:** 16. oktober 2026, etter gruppas gjennomgang av PR #1 (faser lagt om: dashbordet skal finnes tidlig, ikke komme sist).
**Alle datoer under regnes fra 16. oktober 2026** — forrige versjon regnet fra 6. oktober, som allerede var passert.

Se `docs/vurderingskriterier.md` for hvordan Del 1 (70 % av karakteren) og refleksjonsrapporten (30 %) faktisk vurderes.

## Hvorfor fasene snudd om

Forrige versjon av planen satte modellarbeid først og dashbord sist (10.–30. nov, tre uker, etter fem uker med modell). Faglærer var konkret: *"Bygg en første, enkel versjon av dashbordet med baseline-prediksjonene allerede nå."* Begrunnelsen er enkel og alvorlig — **det er appen sensor kjører og karaktersetter**, ikke modellen isolert. Glipper modellarbeidet underveis, skal gruppa likevel ha noe kjørbart å vise fram. Dashbordet bygges derfor på den kalibrerte baselinen først, og modellen byttes inn bak det senere uten at resten av appen må bygges om.

## Milepæler

### Fase 1 — Datapipeline ✅ fullført (17. sep – 28. sep)

- Full AIS-henting fullført for hele perioden (8 094 seilaser, 2024–2026).
- `derive_arrivals.py` kjørt på fullbatchen: 87,1 % dekning, kalibrert baseline, liggetid-fordeling, skjevhetssjekk — alt låst med ekte tall.
- Datasettoppsummering skrevet (`docs/addendum.md`), brief oppdatert med faktiske tall (`docs/brief.md`).
- **Leveranse (levert):** et låst, dokumentert datasett (`pipeline/data/bergen_eta_avvik.csv`) klart for modellarbeid.

### Fase 2 — BMAD (PRD, arkitektur, epics/stories) + UX-skisser (16. okt – 23. okt, ~1 uke)

Ikke lenger et åpent spørsmål — dette er nå en fase, fordi kriterium 1 (30 % av del 1) krever BMAD-dokumenter som faktisk er brukt og oppdatert, ikke bare en brief.

- **PRD** med BMAD, bygget på `docs/brief.md` — kravene briefens suksesskriterier faktisk oversettes til.
- **Arkitektur**: teknologivalg for dashbord og modell, begrunnet og ikke mer komplekse enn appen trenger (kriterium 5).
- **Epics/stories**, spesifikt nok til at hver story blir én branch og én PR (se arbeidsflyt under).
- **UX-skisser**: skjermbeskrivelser/wireframes for dashbordets kjerneskjermbilde — listevisning over anløp, kart, begrunnelsestekst per avvik. Trenger ikke kode; penn-og-papir eller enkle mockups holder, men skal ligge i repoet (`docs/ux/` eller tilsvarende). Universell utforming tas inn fra start: kontrast, tastaturnavigasjon, alt-tekst på kart/ikoner, og at skjermbildet fungerer på minst to skjermstørrelser.
- **Leveranse:** PRD, arkitektur, stories og UX-skisser klare — Fase 3 bygger direkte på dette, ikke designer underveis.

### Fase 3 — Dashbord v1 på kalibrert baseline (24. okt – 6. nov, ~2 uker)

Ingen modell ennå. Dashbordet viser prediksjoner fra den kalibrerte baselinen (`rapportert_eta − offset`, se `docs/beslutninger/04-kalibrert-baseline.md`) mot faktisk ankomst i det låste datasettet — en ekte, om enn enkel, demo av verdien.

- Nettbasert dashbord bygget etter skjermbeskrivelsene fra Fase 2 (v1: ingen innlogging, se `docs/addendum.md` for begrunnelse).
- **Versjonert datautdrag** av det låste datasettet, lite nok til å ligge i repoet eller hentes raskt — ikke den fulle, gitignorede `pipeline/data/`.
- **README oppdatert** slik at sensor kan klone repoet og ha appen kjørende på **under 20 minutter**, uten gruppens egne nøkler eller kontoer (kriterium 6).
- **Leveranse:** en app som faktisk virker — uten modell, men kjørbar og vurderbar i seg selv hvis resten av semesteret glipper.

### Fase 4 — Modell (7. nov – 27. nov, ~3 uker)

Bygges og evalueres som før, men byttes nå inn **bak et dashbord som allerede fungerer** — i stedet for at dashbordet venter på modellen.

- Baseline: kalibrert rapportert-ETA som gulv å slå (allerede etablert i pipelinen).
- Tren prediksjonsmodell(er) for 6t- og 24t-horisont mot `arrival_in_area`.
- Evaluer mot hovedmetrikken (andel innenfor ±30 min) og sekundærmetrikken (presisjon/recall på `er_forsinket`-flagget) — se `docs/brief.md`.
- Iterer på modellvalg og features; vurder om rutegående/ikke-rutegående bør modelleres separat, gitt hvor ulikt de to gruppene oppfører seg.
- Koble modellens prediksjoner inn i dashbordet fra Fase 3, i stedet for den rene baselinen.
- **Leveranse:** en trent modell som slår den kalibrerte baselinen, synlig i det samme dashbordet sensor allerede kan kjøre.

### Fase 5 — Generativt AI-lag (28. nov – 5. des, ~1 uke)

- Daglig forstyrrelsesbrief: begrunnelse per forventet avvik, generert fra modellens faktiske input (skipstype, historisk avvik, tid på døgnet osv.) — ikke fritt oppspinn.
- **Testmodus uten API-nøkkel**, slik at sensor kan se AI-laget i bruk uten gruppens egen språkmodell-tilgang (kriterium 6).
- Kart i dashbordet, hvis tiden tillater — eksplisitt lavest prioritert i denne fasen, ikke en forutsetning for at resten er ferdig.
- **Leveranse:** AI-generert begrunnelse synlig i dashbordet, med en måte sensor kan se den virke uten egne nøkler.

### Fase 6 — Testing, polering, levering (6. des – 15. des, ~1,5 uke)

- Ende-til-ende-testing av hele kjeden (data → modell → AI-lag → dashbord), inkludert automatiske tester av pipelinen (kriterium 3 — finnes ikke ennå).
- Ferdigstill refleksjonsrapporten (se egen seksjon under).
- Buffer for forsinkelser — bevisst satt av, ikke fylt med nye oppgaver.
- Presentasjon/demo-forberedelse hvis kurset krever det.
- **Leveranse:** innlevert prosjekt, 15. desember.

## Refleksjonsrapporten — egen leveranse, løpende (30 % av karakteren)

Ikke en avsluttende oppgave i Fase 6 — den skrives **underveis**, fordi mye av innholdet (utfordringer, hvor KI bommet, hva vi rettet, hvorfor vi endret metode) allerede finnes i `docs/beslutninger/` og `docs/prompts/` mens det er ferskt. Delmål knyttet direkte til fasene over, ikke bare "løpende":

- **Omfang:** 3 000–5 000 ord, individuelle refleksjoner fra Theodor, Felipe og Thomas (ikke én felles tekst).
- **Etter Fase 2 (23. okt):** hver person noterer hvordan BMAD-flyten (PRD/arkitektur/stories) faktisk fungerte — traff kravene, eller måtte de justeres etter at koding startet?
- **Etter Fase 3 (6. nov):** notér hva som var vanskelig med å få et kjørbart v1 opp uten modell — spesielt der KI-forslag måtte rettes eller forkastes.
- **Etter Fase 4 (27. nov):** notér modellarbeidets reelle utfordringer — der dette allerede er godt dekket i `docs/beslutninger/`, er jobben å trekke det inn i egne ord, ikke finne opp noe nytt.
- **Etter Fase 5 (5. des):** notér hvordan AI-laget faktisk oppførte seg — traff begrunnelsene, eller måtte prompting rettes etter at dere så ekte output?
- **6.–12. des:** hvert individuelt utkast skrives ferdig fra de fire notatrundene over.
- **12.–15. des:** siste gjennomlesing, sammen med resten av innleveringen.
- **Leveranse:** tre individuelle refleksjoner, innlevert 15. desember sammen med Del 1.

## Forslag til arbeidsdeling

Delt etter de naturlige arbeidsstrømmene i prosjektet — bytt fritt basert på hvem som faktisk vil/kan hva. Fase 2 (PRD/arkitektur/stories) er i sin natur et gruppearbeid, ikke én persons ansvar — del den opp dere imellom når dere planlegger den konkret.

| Arbeidsstrøm | Forslag | Dekker |
|---|---|---|
| Data & pipeline | Theodor | Datakvalitet, kalibrering, dokumentasjon av beslutninger (fullført, vedlikehold videre) |
| Dashbord & UX | Thomas | UX-skisser (Fase 2), dashbord v1 (Fase 3), generativt AI-lag (Fase 5) |
| Modell | Felipe | Feature-arbeid, trening, evaluering mot suksesskriteriene (Fase 4) |

Fase 3 og 4 krever samarbeid uansett — modellen (Felipe) skal kobles inn i dashbordet (Thomas) uten å bygge det om, og det går lettere hvis grensesnittet mellom dem er avtalt i Fase 2.

## Arbeidsflyt fra nå av

**Branch per story, pull request inn til main.** Ikke flere commits rett på main. Sensor ser etter branches, PR-er og issues som spor på arbeidsflyt — det er en del av kriterium 1 og 7 i `docs/vurderingskriterier.md`.

## Åpne spørsmål til gruppa

- Er det delfrister før 15. desember (presentasjon, statusmøte) som bør inn som egne milepæler?
- Skal rutegående og ikke-rutegående trafikk modelleres som to separate modeller, gitt hvor ulikt de oppfører seg (se `docs/beslutninger/05-andel-innenfor-30-min-fremfor-mae.md`)? Kan avgjøres i Fase 2 sammen med arkitekturvalgene, ikke nødvendigvis nå.
