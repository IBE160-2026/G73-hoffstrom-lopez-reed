# E2-S02 AIS-henting ved kuttpunktene

## 2026-11-03 kl. 18:21 — Felipe Knudstad-Lopez

Felipe styrte økta. Den ble kjørt med Claude Code på Theodors maskin, der git står som Theodor Gimming. Commitene i økta har derfor `--author` satt til Felipe.

### Oppgave
Starte E2 (modellen) på branchen `epic/e2-modell` fra `main`, med én commit per story som i E1. E2-S01 og E2-S02 skulle få full BMAD-flyt, etter at beslutning 08 og 09 var lest. E2-S02, den målrettede AIS-hentingen rundt kuttpunktene, var prioritert. Den skulle specces, godkjennes og startes i kveld, så den kunne kjøre over natta.

Felipes krav:
- filtrering på tidsstemplet i svaret (`filtrer_til_vindu`)
- cache per seilas, så hentingen kan avbrytes og fortsette
- pause mellom kall og nye forsøk ved feil
- pilot på 50 seilaser med estimat før fullkjøringen
- det låste datasettet og 46,6 % røres ikke

### Plan
- Les beslutning 08 og 09, E2 i `docs/epics.md`, FR9a i PRD-en og den låste `pipeline/fetch_ais.py`.
- Lag branchen `epic/e2-modell` fra `main`.
- BMAD-build:
  - epic-kontekst: [`_bmad-output/implementation-artifacts/epic-2-context.md`](../../_bmad-output/implementation-artifacts/epic-2-context.md)
  - spec: [`_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md`](../../_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md)
  - deretter Felipes godkjenning, implementering, tre uavhengige gjennomganger (Blind Hunter, Edge Case Hunter, Verification Gap), pilot, commit og push, og fullkjøring
- Felipe godkjente specen med fire presiseringer (står i specen under «Decisions»):
  1. Hardt tak: ingen punkter etter ETA − 6 t i cachen, med en test som er mutasjonssjekket.
  2. Kode og tester committes etter piloten, og dekningstabellen committes separat.
  3. Commitene får `--author` Felipe.
  4. Fullkjøringen startes med `caffeinate -i`.
- E2-S01 ble ikke startet. Den er en beslutning som hele gruppa må godkjenne i PR-en, og de åpne valgene der påvirker ikke hentevinduet.

### Resultat
**Ny kode:**
- `pipeline/fetch_ais_kutt.py`:
  - **Forespørsel:** ett kall per seilas for [ETA − 72 t, ETA + 18 t] mot `kystdatahuset.kystverket.no`.
  - **Filtrering:** først et hardt tak ved ETA − 6 t, så `filtrer_til_vindu` til [`t_H` − 24 t, `t_H`] for H ∈ {6, 24}.
  - **Cache:** én fil per seilas i `pipeline/data/ais_kutt_cache/`, skrevet atomisk.
  - **Pause og nye forsøk:** 1 s pause, og 3 nye forsøk med 5/15/45 s backoff. Ved 4xx og ved en manglende dagstabell hos API-et gis det opp med en gang. Skriptet stopper etter 10 feil på rad.
  - **Logg og dekning:** kall logges i `ais_kutt_logg.csv`, og dekningen per horisont, gruppe og splitt skrives til `ais_kutt_dekning.csv`.
  - **Leser bare** `voyageid, mmsino, ship_group, eta_reported, split` fra `data/utdrag/anlop.csv`.
- `tests/test_fetch_ais_kutt.py`: 19 tester uten nett. Hele suiten har 198 grønne tester på 0,8 s, og `test_dataregresjon.py` er uendret og grønn.
- Mutasjonssjekk, gjort for hånd: hver mutasjon ble lagt inn, testene kjørt, og fila satt tilbake. Alle ble fanget:

  | Mutasjon | Testen som feilet |
  |---|---|
  | Taket fjernet | `test_ingenting_etter_eta_minus_6t` |
  | Taket flyttet til ETA | `test_ingenting_etter_eta_minus_6t` |
  | Vindusfilteret slipper alt | `test_filtrerer_bort_punkter_etter_kutt` og `test_dekningstabell` |
  | Forespørselsvinduet forskjøvet | `test_vindu_fra_rapportert_eta` |
  | Telleren for feil på rad nullstilles ikke | `test_feil_pa_rad_nullstilles` |

- Gjennomgangen ga 13 rettelser. De viktigste:
  - feiltyper som ellers kunne stoppet hele nattkjøringen
  - tester for selve API-kallet og for `--utvalg`
  - uleselige tidsstempler, som nå telles for seg
  - en eksplisitt sjekk i stedet for `assert`

  Én ting er utsatt til `deferred-work.md`: å oppdage avkortede svar. Hele triagen står i specen.

**Pilot, 03.11.2026** (`--utvalg 50 --seed 2`):
- 49 hentet (41 med posisjoner, 8 tomme) og 1 feil, på 4,3 min.
- Median 2,7 s per kall, og 724 kB per seilas i cachen.
- Estimat for de 7 777 som gjenstår: rundt 8 t og 5,6 GB. Felipe så estimatet og ga klarsignal.
- Funn: API-et svarer `42P01: relation "ais202410.ais_20241028" does not exist` for seilas 2690405. En dagstabell mangler hos Kystdatahuset, så slike feil prøves ikke på nytt.
- Dekning i piloten (n er for lite til å konkludere): Øvrige har posisjon i 24-timersvinduet for 68 % (23 av 34) ved begge horisontene.

**Låst datasett:** `pipeline/data/` er bekreftet gitignorert (`.gitignore:55`), og ingen filer derfra er sporet. Hentingen skriver bare til nye filer der. `data/`, `ais_cache/`, `bergen_eta_avvik.csv` og `fetch_ais.py` er ikke rørt.

**Git:** E2-S02-commiten `85021b9` (forfatter Felipe Knudstad-Lopez) er pushet til `origin/epic/e2-modell`. `docs/epics.md` viser E2-S02 som ◐ til dekningstabellen er committet.

**Fullkjøring:** startes etter denne loggen, frakoblet fra økta:

```sh
nohup caffeinate -i python3 pipeline/fetch_ais_kutt.py > pipeline/data/ais_kutt_kjoring.log 2>&1 &
tail -f pipeline/data/ais_kutt_kjoring.log      # fremdrift
ls pipeline/data/ais_kutt_cache | wc -l         # ferdige av 7 826
pkill -f fetch_ais_kutt.py                      # avbryt rent
```

Fortsett ved å kjøre den første kommandoen på nytt. Seilaser som ligger i cachen, hoppes over.

### Åpne punkter
- Fullkjøringen av E2-S02 går over natta. Sjekk loggen. Hvis den stoppet etter 10 feil på rad, kjør samme kommando igjen.
- Dekningstabellen (`pipeline/data/ais_kutt_dekning.csv`) føres inn i specen og i loggen og committes separat. E2-S02 settes til ✅ i `docs/epics.md`.
- Sammenlign dekningen ved `t_24` for Øvrige/test med ≈ 93 % i beslutning 09, regnet bare på seilaser som hadde AIS i den opprinnelige hentingen. Er den langt lavere, må det undersøkes før E2-S03.
- Tell seilasene som feilet med `mangler hos API-et` (manglende dagstabeller), og vurder om de skal føres som kjent hull.
- E2-S01 (én eller to modeller, A1, A2) er ikke startet. Den må godkjennes av hele gruppa i PR-en før E2-S04.
