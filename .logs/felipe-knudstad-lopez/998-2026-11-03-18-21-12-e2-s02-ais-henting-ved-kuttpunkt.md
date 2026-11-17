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

## 2026-11-05 kl. 14:22 — Felipe Knudstad-Lopez

### Oppgave
Fullkjøringen stoppet 03.11 kl. 19:42 etter 2 185 av 7 826 seilaser. Grunnen var ikke nedetid, men ti 42P01-feil på rad for dagstabellen `ais_20240730`. Felipe ba om to rettelser i `fetch_ais_kutt.py`, med tester. Den første: en manglende dagstabell skal ikke telle mot stoppregelen. Den andre: vinduet skal deles rundt den manglende dagen, slik at bare den dagen går tapt, og delvinduene må være lange nok med tanke på funn B. De manglende dagene skulle føres inn i dekningsloggen. Deretter skulle 42P01-seilasene kjøres på nytt, det skulle committes med Felipe som forfatter og pushes, og fullkjøringen skulle startes igjen. Hendelsen skulle også inn i refleksjonsnotatene.

### Plan
- Sjekke påstanden mot `ais_kutt_logg.csv`. Det stemte: de ti siste feilene var 42P01 for `ais_20240730`, og i tillegg var det én fra piloten for `ais_20241028`.
- Seks prøvekall mot API-et rundt 30.07.2024 for å finne ut hvordan dagstabellen velges.
- Rette koden og legge til tester, med mutasjonssjekk av stoppregelen.
- Kjøre de 11 seilasene på nytt, committe, pushe og starte fullkjøringen igjen.

### Resultat
- **Prøvekall:** API-et velger dagstabeller etter datoen i forespørselen. [28.07 00:00, 29.07 23:59] gir data fram til 29.07 23:59:58 UTC. [31.07 00:00, 01.08 06:00] gir data fra 31.07 02:00 UTC. Et vindu som starter 30.07 22:00 eller 23:00, feiler.
- **Rettelse:**
  - Ny feiltype `ManglerDag`, som leser dagen fra meldingen. Den teller ikke mot stoppregelen og nullstiller den heller ikke.
  - Funksjonene `hent_med_hull` og `del_rundt_dag` deler vinduet rundt dagen. Venstre del slutter 23:59 dagen før, og høyre del starter 00:00 dagen etter. Hver del forlenges utover til minst 25 t, men aldri inn i en annen kjent manglende dag.
  - Er vinduet delt, fjernes duplikater. Uten deling er svaret uendret.
  - Cachen får feltet `manglende_dager`. `ais_kutt_dekning.csv` får kolonnene `med_manglende_dag` og `manglende_dager`. Det tapte intervallet regnes som hele dagen pluss 2 t inn i dagen etter.
- **Tester:** 10 nye, og alle 249 i repoet er grønne. Mutasjonssjekket: de to testene for stoppregelen feiler når rettelsen fjernes.
- **Ny kjøring av 42P01-seilasene:** alle 11 ble hentet, 9 `ok` og 2 `tom`, uten feil. Ingen punkter ligger på den manglende dagen. 2496687 har 0 punkter ved t_6, fordi hele tilbakeblikket ligger i hullet. Det er et ekte tap.
- **Commits:** `0a85cd4` (rettelsen) og `cf6a8eb` (refleksjonsnotat), begge med Felipe som forfatter. `0a85cd4` er pushet.
- **Fullkjøring:** startet igjen 05.11 kl. 14:17 med `nohup caffeinate -i .venv/bin/python pipeline/fetch_ais_kutt.py >> pipeline/data/ais_kutt_kjoring.log 2>&1 &`. 5 630 seilaser gjenstår. Etter 4 min er status `[50/5630] ok=45 tom=5 feil=0`, og estimatet er rundt 7,4 t. Mange seilaser rundt 30.07 blir delt som de skal.
- **Prosess:** endringen ble gjort direkte, ikke gjennom hele bmad-build-ruta. Kvalitetssikringen var tester, mutasjonssjekk og kjøring mot ekte API.

**Review av `0a85cd4` (samme dag, etter omstarten):**
- **Gjennomføring:** BMAD-reviewen ble kjørt med fire reviewere: Blind Hunter, Edge Case Hunter, Verification Gap og Acceptance Auditor. Funnene ble sjekket mot cachen uten å skrive noe. `fetch_ais_kutt.py` ble ikke rørt, og kjøringen gikk hele tiden.
- **Hva sjekken viste:**
  - 28 delte seilaser, alle med én manglende dag.
  - 0 feil siden omstarten.
  - 0 duplikater fra API-et i 200 seilaser.
  - Ingen funn krever ny henting.
- **B1, egen status for permanente hull:** utsatt av Felipe og ført i `_bmad-output/implementation-artifacts/deferred-work.md`.
- **B2, rettet i `1cee190` (E2-S03):**
  - `lag_tilstand.py` gir status `manglende_dag` når kuttpunktet ligger i hullet og bare har en posisjon fra før. Slike rader går til baselinen.
  - 4 nye tester, og alle 253 er grønne. Mutasjonssjekken fanger alle fire mutasjonene. Første versjon av grensetesten lot `<=` i slutten av hullet slippe gjennom, og den er strammet inn.
  - Mot den ekte cachen fikk 8 kuttpunkter `manglende_dag`.
- **Seks rettelser i `fetch_ais_kutt.py`:** ført inn i story-fila (`spec-e2-s02-…`, «Review Findings»). De tas når kjøringen er ferdig. Story-statusen er satt til `in-progress`.
- **Beslutning 09:** et tillegg forklarer hvorfor en manglende dag koster 26 t (`9ecf360`). Høyre del kan tidligst starte kl. 00:00 dagen etter, og med forskyvningen på +2 t kommer første punkt kl. 02:00 UTC. Om vinteren er tapet trolig 25 t.
- **Rettelse av commitmeldingen:** `0a85cd4` sier «10 nye tester», men det er 9 testfunksjoner. Commiten er pushet og blir ikke endret.

### Åpne punkter
- Sjekk kjøreloggen i kveld og i morgen tidlig (`tail pipeline/data/ais_kutt_kjoring.log`). Har den stoppet, kjør samme kommando igjen.
- Når fullkjøringen er ferdig: les `med_manglende_dag` og `manglende_dager` i dekningstabellen, og vurder om hullene skal føres som kjent begrensning i beslutning 09.
- Når fullkjøringen er ferdig: ta de seks review-rettelsene i `fetch_ais_kutt.py` (story-fila, «Review Findings»), og kjør `lag_tilstand.py` på nytt.
