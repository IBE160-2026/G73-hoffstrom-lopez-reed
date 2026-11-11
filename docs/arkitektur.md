---
title: "Arkitektur: AIS-basert ankomstprediksjon"
status: aktiv
created: 2026-10-16
updated: 2026-10-27
bygger_på: docs/prd.md
---

# Arkitektur

**Bygger på:** [`docs/prd.md`](prd.md) (særlig NFR1–NFR6) og [`docs/ux/dashbord.md`](ux/dashbord.md). **Brukes av:** [`docs/epics.md`](epics.md).

Målet er færrest mulig bevegelige deler som likevel lar modellen (E2) og AI-laget (E3) byttes inn uten at dashbordet (E1) bygges om. Arkitekturbeslutningene har ID-er (A1–A8), så stories og commits kan vise til dem.

## 1. Oversikt

```
 pipeline/ (fase 1, ferdig)          scripts/lag_utdrag.py (E1-S02)        app/ (Flask)
 ┌──────────────────────────┐        ┌──────────────────────────┐        ┌──────────────────────────────┐
 │ fetch_voyages.py         │        │ leser full CSV           │        │ data.py      laster utdrag   │
 │ fetch_ais.py             │──CSV──▶│ skriver:                 │──git──▶│ prediksjon/  Prediktor ◀─┐   │
 │ derive_arrivals.py       │        │  data/utdrag/anlop.csv   │        │   baseline.py   (E1)     │   │
 │ → pipeline/data/  (git-  │        │  data/baseline.json      │        │   modell.py     (E2)     │   │
 │   ignored, timer å lage) │        └──────────────────────────┘        │ metrikker.py ── samme ───┼─▶ scripts/evaluer.py (E2)
 └──────────────────────────┘                                            │ begrunnelse/ (E3)        │   │
                                                                         │   test | ekte (adapter)  │   │
                                                                         │ templates/ + static/     │   │
                                                                         └──────────────────────────────┘
                                                                                  ▲ HTTP GET, server-rendret HTML
                                                                               nettleser (ingen JS påkrevd)
```

Sensor trenger bare det som er i git: `app/`, `data/`, `requirements.txt` og README. `pipeline/` beholdes som dokumentasjon av hvordan dataene ble laget.

## 2. Teknologivalg

| ID | Valg | Alternativer vurdert | Begrunnelse |
|---|---|---|---|
| **A1** | **Python ≥ 3.9 + Flask 3, Jinja-maler, server-rendret HTML** | Streamlit; Next.js + Python-API | Ett språk i hele repoet, og pipeline og modell er allerede Python. Med server-rendret HTML styrer vi semantikk, fokus og kontrast fullt ut (UU1–UU7). Det har vi ikke i Streamlit. Next.js ville gitt to språk, to servere og Node-oppsett for sensor: mer enn appen trenger (kriterium 5). Python 3.9 fordi det er det macOS leverer, og det er laveste versjon Flask 3 støtter. |
| **A2** | **Ingen database. CSV lastes i minnet ved oppstart.** | SQLite | ~7 800 rader og ~1 MB. Et filter i Python er raskt nok, og ingen migrering må til. |
| **A3** | **Ingen JS-rammeverk og intet byggesteg.** Én CSS-fil med tokens. | React/HTMX/Tailwind | Skjemaer og lenker dekker all interaksjon (UX §2). Tilstanden ligger i URL-en, og alt kan testes med Flask-testklienten uten nettleser. |
| **A4** | **Versjonert datautdrag + lagret baseline i `data/`** | La sensor kjøre pipelinen | Pipelinen tar timer og trenger nett (NFR1). Utdraget er deterministisk laget fra pipeline-output, og sjekksummen til kilden lagres. |
| **A5** | **Prediktor-grensesnitt (§3) som eneste kobling mellom dashbord og modell** | Dashbordet leser modellens output-CSV direkte | Gjør at E2 kan byttes inn uten endringer i visningskoden (PRD §1), og at Thomas og Felipe kan jobbe parallelt mot en avtalt kontrakt. |
| **A6** | **Én metrikkmodul brukt av både dashbord og evalueringsskript** | Egen utregning i notebook | NFR3: tallet på skjermen og tallet i rapporten *kan ikke* bli ulike. |
| **A7** | **scikit-learn for modellen, lagret med joblib i `data/modell/`** (endelig valg i E2-S01) | XGBoost, LightGBM | scikit-learn har gradient boosting innebygd, og hjul for alle plattformer gjør installasjonen triviell for sensor. XGBoost vurderes bare hvis E2-S01 viser at det trengs. |
| **A8** | **LLM bak adapter med testmodus som standard.** Ekte modus: Anthropic API (`anthropic`-pakken). | Kalle API direkte fra ruten | Sensor har ingen nøkkel (FR13). Adapteren gjør leverandøren byttbar og testene nettfrie. |

## 3. Prediktor-grensesnittet (A5)

Dette er kontrakten mellom dashbordet (Thomas) og modellen (Felipe). Endres den, skal det skje i en egen PR som begge godkjenner, og endringen skal stå i endringsloggen her.

```python
# app/prediksjon/__init__.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence

@dataclass(frozen=True)
class PrediksjonsInput:                  # det eneste en prediktor får se
    voyageid: int
    mmsino: int
    shipname: str
    ship_group: str                      # rå gruppe fra kilden
    gruppe: str                          # «Passasjer» eller «Øvrige»
    eta_reported: datetime               # UTC
    horisont_timer: int                  # 6 eller 24
    t_kutt: datetime                     # min(eta_reported − H, naa), UTC

@dataclass(frozen=True)
class Prediksjon:
    voyageid: int
    horisont_timer: int                  # 6 eller 24, valgt fra rapportert ETA − naa (PRD FR2)
    predikert_ankomst: datetime          # UTC, tz-aware, full presisjon (avrunding er visning)
    forventet_forsinket: Optional[bool]  # None = prediktoren kan ikke varsle (baseline)
    forklaring: dict                     # minst metode og gruppe (baselinen har også offset_minutter); vises på detaljsiden og mates til AI-laget (E3)

class Prediktor(Protocol):
    navn: str                            # vises i prediktor-stripa, f.eks. "Kalibrert baseline"
    kan_varsle: bool
    def prediker(self, inputs: Sequence[PrediksjonsInput], naa: datetime) -> list[Prediksjon]: ...

def lag_input(anlop: "Anlop", naa: datetime) -> PrediksjonsInput:
    """Eneste grense mellom datalaget og prediktorene."""

def velg_prediktor(verdi: Optional[str] = None, naa: Optional[datetime] = None) -> Prediktor:
    """PREDIKTOR=baseline|modell|auto (standard auto). verdi=None leser miljøvariabelen PREDIKTOR. Ukjent verdi gir ValueError.
    Før testkjøringen (testkjoringer = 0 i data/modell/metrikker.json) gir auto baselinen, og modell gir ModellPrediktor
    bare når vinduet [naa, naa + 24 t) slutter senest ved testperiodens første rapporterte ETA (uten naa: låst).
    Etter testkjøringen gir auto og modell ModellPrediktor. Gir ModellPrediktor() ValueError, blir det baselinen.
    velg_prediktor_med_merknad gir i tillegg merknaden til prediktor-stripa (låst testperiode / modell ikke funnet)."""
```

- **Lekkasje er umulig per konstruksjon, ikke bare forbudt.** Prediktorer får aldri et `Anlop`. `PrediksjonsInput` har ingen felt, egenskap eller referanse som fører til `faktisk_ankomst`, `status_in_area` eller `split`, så en prediktor som prøver å lese dem, får `AttributeError`. `lag_input()` er den eneste koden i `app/prediksjon/` som rører anløpene i `app.data`. To søsterfunksjoner i `__init__.py` leser også data: `featurer_ved_kutt` leser `data/utdrag/features.csv` og gir bare modellens featurekolonner, og `testperiode_start` (E2-S08, låsen i `velg_prediktor`) leser `app.data` og gir bare ett tidspunkt ut, testperiodens første rapporterte ETA. Ingen prediktormodul (alt unntatt `__init__.py`) får importere `app.data` eller lese `data/utdrag/`. Det sjekkes med en AST-test. Garantien gjelder feil som skjer ved et uhell, ikke bevisst kode (for eksempel dynamisk `importlib`): grensesnittet gir ingen vei til fasiten, og en utilsiktet import eller fillesing får testen til å feile. Ruten (E1-S06) når en prediktor bare via `lag_input`, og det finnes ingen variant av `prediker` som tar `Anlop`.
- Horisonten velges i `lag_input`: 6 t hvis `eta_reported − naa ≤ 6 t`, ellers 24 t. Kuttpunktet er `t_kutt = min(eta_reported − H, naa)`. Med dagens utvalg (rapportert ETA i [nå, nå + 24 t)) er det det samme som `eta_reported − H` (PRD FR9a). Klemmen mot `naa` gjør at kontrakten også holder hvis E1-S06 ber om prediksjoner for anløp mer enn 24 t fram: kuttet ligger da aldri etter «nå». F1–F16 ved kuttet (tilstand, statiske felt og ferdigregnet fartøyhistorikk) når modellen gjennom søsterfunksjonen `featurer_ved_kutt(inp)` i `__init__.py` (E2-S07), uten nye felt i `PrediksjonsInput`. Den slår opp anløpet og horisonten i `data/utdrag/features.csv` og gir en frossen mapping med bare artefaktets featurekolonner, og bare når radens `t_kutt_utc` er lik `inp.t_kutt`. Ellers gir den None, for eksempel når kuttet er klemt mot `naa`: den committede raden er da fra etter «nå». `del`, `gruppe`, `har_tilstand`, `_modellvalg`-historikken og alle ankomstfelt går aldri ut. Prediktormodulen leser ingen utdrag selv. `features_sha256()` gir sjekksummen for fila, og `ModellPrediktor()` gir `ValueError` hvis den eller `offset_ovrige_min` ikke stemmer med artefaktet og `baseline.json`. Kodingen til modellens matrise (`matrise`) står i `app/prediksjon/koding.py` og brukes også av `scripts/tren.py`, så modellarmen har én definisjon. Baselinen bruker bare horisonten til visning. `ModellPrediktor` (`navn = "Modell v1"`, `kan_varsle = True`) predikerer bare Øvrige med tilstand og F6 = 0 ved kuttet (beslutning 11 og 12): `predikert_ankomst = eta_reported − offset_ovrige_min + predikert avvik`, og varsel er predikert avvik > 120 min. Alle andre rader får baselinens `Prediksjon` med `forventet_forsinket = None` og `forklaring["delegert"]` lik `passasjer`, `ingen_tilstand`, `i_sonen_ved_kutt` eller `ingen_featurerad` (`metode` er da baselinens, `kalibrert_baseline`). Uten tilstand er F6 tom, og det er slik prediktoren ser at tilstanden mangler. Det endrer ikke kontrakten.
- `prediker` skal gi `TypeError` for alt som ikke er `PrediksjonsInput`. Kontrakttesten krever det.
- Om 24 t-vinduet velger på rapportert eller predikert ankomst, er et åpent valg for E1-S06. Kontrakten støtter begge.
- *Avvik* og *forsinket* (fasit) regnes i `metrikker.py` mot kalibrert baseline og er aldri en del av `Prediksjon`. Bytter man prediktor, endres derfor ikke fasiten (PRD §3).
- Den samme kontrakttesten (`tests/test_prediktor_kontrakt.py`) kjøres parametrisert mot alle prediktorer i `PREDIKTORER`. Den sjekker at input ikke har fasit, at endret fasit gir identiske prediksjoner, at `t_kutt ≤ naa` (`test_kutt_ikke_etter_naa`), og at prediktormodulene ikke leser datalaget. En ny prediktor er ikke ferdig før den består.

## 4. Data

**`data/utdrag/anlop.csv`** (A4) — alle 7 826 rader fra `pipeline/data/bergen_eta_avvik.csv`, med bare de kolonnene appen og modellen trenger:

`voyageid, mmsino, shipname, ship_group, eta_reported, arrival_in_area_utc, status_in_area, split`

- `split` er `train` eller `test`, fra den samme kronologiske 80/20-splitten som i beslutning 04 (6 260 / 1 566 rader, testperioden starter 2025-09-14T03:15Z).
- Avvik og `er_forsinket` regnes ut i appen fra baselinen. De lagres ikke, for da kunne de drifte fra hverandre.
- Valideringsdelen for modellvalg (de siste 20 % av `train`, kronologisk, PRD NFR3) avledes i `scripts/` og lagres ikke som egen verdi. Offset regnes fortsatt på hele `train` (beslutning 04), så baselinetallene ikke endres.
- Ventet størrelse er ~700 kB, og fila committes.

**`data/baseline.json`**

```json
{
  "offset_minutter": {"Passasjer": 44.8, "Øvrige": 64.2},
  "test_fra_utc": "2025-09-14T03:15:00Z",
  "kilde": "pipeline/data/bergen_eta_avvik.csv",
  "kilde_sha256": "…",
  "laget": "2026-10-xx"
}
```

**`data/utdrag/tilstand_ved_kutt.csv`** (E2-S03) — én rad per anløp og horisont, regnet med `scripts/lag_tilstand.py` fra AIS hentet av `pipeline/fetch_ais_kutt.py` (vindu [`t_H` − 24 t, `t_H`], filtrert på tidsstemplet i svaret, beslutning 09; beslutning 08):

`voyageid, horisont_timer, t_kutt_utc, ais_status, lat, lon, distanse_km, fart_knop, kurs_grader, posisjon_alder_min`

`ais_status` er `ok`, `ingen_posisjon` (hentet, men ingen gyldig posisjon i vinduet), `manglende_dag` (kuttpunktet ligger i en dag som mangler hos Kystdatahuset, og det finnes ingen gyldig posisjon fra etter at hullet begynte, beslutning 09) eller `ikke_hentet` (ingen cachefil). Alt som ikke er `ok`, går til baselinen (beslutning 11). Når statusen ikke er `ok`, er alle tilstandsfeltene tomme, og raden beholdes. En posisjon er gyldig bare hvis MMSI-en i punktet er lik seilasens MMSI og har 9 sifre (63 seilaser har MMSI 0, beslutning 07), og bredde/lengde er en reell posisjon. Også med `ok` kan `fart_knop` og `kurs_grader` være tomme: verdiene for «ikke tilgjengelig» (fart ≥ 102,3, kurs ≥ 360) og negative verdier skrives ikke. E2-S04 må tåle det. Fila er ~15 600 rader og ~1,5 MB og committes. Det er den eneste AIS-avledede inputen modellen får hos sensor (PRD NFR1). Scriptet leser ingen ankomstfelt, og utdraget har ikke noe flagg regnet fra faktisk ankomst: «allerede i sonen» er F6 i beslutning 11, regnet fra posisjonen.

**`data/utdrag/tilstand_ved_kutt.json`** (E2-S03) — metadata for utdraget:

- sti og sha256 for `anlop.csv`
- kildemappe, antall cachefiler for anløpene i `anlop.csv` og samlet sha256 (sha256 av de sorterte per-fil-sjekksummene)
- antall tomme API-svar (`status: "tom"`, kan hentes på nytt med `--prov-tomme`)
- sha256 for CSV-en, dato (`--laget`, oppgis ved regenerering) og antall per horisont og `ais_status` `data/baseline.json` er en del av det låste datasettet og røres ikke.

**`data/utdrag/features.csv`** (E2-S04) — F1–F16 fra beslutning 11 per anløp og horisont, med `gruppe`, `del` (`trening`/`validering`/`test`) og `har_tilstand`. Lages med `scripts/lag_features.py` fra `anlop.csv`, tilstandsutdraget, `baseline.json` og seilasfila i `pipeline/data/`, som bare leses. Skipstype, lengde, ETD og avgangshavn finnes bare i den gitignorerte seilasfila, så featurefila er det sensor får. Det finnes ikke noe eget utdrag med rå statiske felt (Felipe, 03.11.2026): **rå ETD committes aldri**, bare de avledede F14-feltene. Kategoriene står rå, og sjeldne verdier grupperes i E2-S05 på fitdataene. `features.json` har sjekksummene for input og antall per del og horisont. F15–F16 står i to varianter. `fartoy_*` er til endelig trening og test, med historikk fra hele treningsdelen. `fartoy_*_modellvalg` er til modellvalg, med historikk bare fra treningsdelen uten validering, frosset ved grensen (beslutning 11). Fila var ~2,6 MB i røyktesten 03.11 og committes. Den genereres etter tilstandsutdraget. Alt E2 committer under `data/` skal til sammen være under 10 MB (PRD NFR1): utdragene med metadata (`tilstand_ved_kutt.*`, `features.*`), fire modellartefakter og `metrikker.json`. `test_committet_features` sjekker summen.

**Tidssoner:** all lagring og beregning skjer i UTC. `arrival_in_area_utc` mangler tidssonesuffiks i kilden og normaliseres ved innlasting. Visning skjer i `Europe/Oslo` via `zoneinfo`. `tzdata` ligger i `requirements.txt` fordi Windows ikke har tidssonedatabasen.

**`data/modell/`** (E2): `modell_6t.joblib` og `modell_24t.joblib` (bare Øvrige), ablasjonene uten F13–F14 ved siden av (`modell_{6,24}t_uten_f13_f14.joblib`), `modellvalg.json` (kandidatene, valgregelen og valget per horisont, laget av `scripts/tren.py` i E2-S05) og `metrikker.json`. Alt committes innenfor den samlede grensen på 10 MB, så sensor slipper å trene.

## 5. Mappestruktur

```
app/
  __init__.py          create_app(), laster data én gang
  data.py              Anlop-dataklasse, last_utdrag(), anlop_i_vindu(naa, timer=24, vis=…)
  metrikker.py         andel_innenfor(…, min=30), presisjon_recall(…)        (A6)
  visning.py           formatering: norsk tid, «+3 t 22 min», horisont-bøtte
  prediksjon/
    __init__.py        PrediksjonsInput, Prediksjon, Prediktor, lag_input(), velg_prediktor()  (A5),
                       featurer_ved_kutt(), features_sha256()                 (E2)
    baseline.py        BaselinePrediktor                                      (E1)
    modell.py          ModellPrediktor                                        (E2)
    koding.py          matrise(): F1–F16 til modellens input, delt med scripts/tren.py (E2)
  begrunnelse/                                                                (E3)
    __init__.py        hent_begrunnelse(), hent_brief() — velger modus
    testmodus.py       opptak + deterministisk mal
    anthropic_klient.py
    prompt.md          versjonert prompt
  templates/  base.html, dashbord.html, anlop.html, metode.html, _feil.html
  static/     style.css
data/         utdrag/anlop.csv, baseline.json, modell/ (E2), begrunnelser_opptak.json (E3)
scripts/      lag_utdrag.py (E1), lag_tilstand.py + tren.py + evaluer.py (E2), ta_opp_begrunnelser.py (E3)
tests/        fixtures/anlop_mini.csv + én testfil per modul
pipeline/     + fetch_ais_kutt.py (E2-S02); øvrige uendret
.env.example  requirements.txt  README.md
```

## 6. Ruter

| Rute | Parametre | Svar |
|---|---|---|
| `GET /` | `naa` (ISO, norsk tid), `vis` (`alle`/`passasjer`/`ovrige`), `fasit` (`0`/`1`), `sorter` (`predikert`/`avvik`) | Skjerm A. Ugyldige parametre gir 200 med feilmelding i skjemaet (UX §5), ikke 400. |
| `GET /anlop/<voyageid>` | samme som over, så «Tilbake» virker | Skjerm C, eller 404 med lenke tilbake |
| `GET /metode` | — | Statisk forklaring av baseline, metrikk og testperiode |

## 7. Konfigurasjon (`.env.example`)

```
# Alt er valgfritt. Appen starter og alle tester kjører uten .env.
PREDIKTOR=auto            # baseline | modell | auto
LLM_MODUS=test            # test | ekte  — test krever ingen nøkkel
ANTHROPIC_API_KEY=        # bare for LLM_MODUS=ekte. Aldri committ en ekte nøkkel.
LLM_MODELL=claude-haiku-5-5
```

## 8. Teststrategi (NFR2)

| Nivå | Hva | Hvor |
|---|---|---|
| Enhet | datalag, baseline, metrikker, formatering | `tests/test_*.py` mot `tests/fixtures/anlop_mini.csv` (håndlagde rader med kjente svar) |
| Kontrakt | alle prediktorer mot §3, inkludert `t_H ≤ naa` | `tests/test_prediktor_kontrakt.py` (parametrisert) |
| Lekkasje | tilstand og features er uendret når AIS etter `t_H` eller faktisk ankomst endres | `tests/test_tilstand.py`, `tests/test_features.py` (PRD FR9a) |
| Dataregresjon | utdraget gir 46,6 % / 79,6 % (naiv 12,8 % / 7,4 %) og 1 427/1 566 med fasit på testsplitten | `tests/test_dataregresjon.py` (PRD FR8, NFR3) |
| Rute | statuskoder, rader, feilmeldinger, at URL-tilstanden bevares | Flask-testklient |
| UU-struktur | `lang`, `label for`, `th scope`, `aria-sort`, alt-tekst, én `h1` | `tests/test_uu_struktur.py` med `html.parser` fra standardbiblioteket |
| Kontrast | tokenpar fra `style.css` ≥ 4,5:1 / 3:1 | `tests/test_kontrast.py` |
| Manuell | tastatur, skjermleser, skjermstørrelser, klone-test | sjekklister i `docs/ux/dashbord.md` §6 og i E1-S15 |

`pytest` skal kjøre uten nett og uten `pipeline/data/`. AI-testene bruker bare testmodus eller en mock av klienten.

## 9. Avhengigheter

`requirements.txt`: `flask>=3,<4`, `tzdata`, `pytest`. E2 legger til `scikit-learn`, og E3 legger til `anthropic`. Hver ny avhengighet begrunnes i commit-meldingen til storyen som legger den til.

## Endringslogg

- **2026-10-16** — Første versjon (E0-S03). A1–A8 og prediktor-kontrakten.
- **2026-10-16** — Etter PRD-validering og beslutning 08 (E0-S07):
  - `Prediksjon.horisont_timer` er lagt til, og horisonten velges fra rapportert ETA − naa.
  - Nye filer: `tilstand_ved_kutt.csv` og `fetch_ais_kutt.py`.
  - Det står nå eksplisitt at fasiten regnes utenfor prediktoren.
  - Valideringsdel er lagt til, og teststrategien har fått en egen rad for lekkasje.
- **2026-10-22** — Etter beslutning 09: tilstandsvinduet er 24 t, og posisjoner filtreres på tidsstemplet i svaret.
- **2026-10-27** — E1-S04: prediktor-kontrakten er input-basert. `prediker` tar `PrediksjonsInput` (bygd av `lag_input`) i stedet for `Anlop`, så prediktorer ikke kan nå fasiten. `t_kutt = min(eta − H, naa)`. Kontrakttesten dekker lekkasje, og `test_kutt_ikke_etter_naa` er flyttet hit fra E2-S07. Krever godkjenning fra begge eiere i PR-en.
- **2026-10-27** — E1-S05: naiv ETA for Øvrige i dataregresjonen er 12,8 %, ikke 12,9 %, fordi avviket nå sammenlignes uavrundet. `app/metrikker.py` scorer prediksjoner fra prediktorer i `PREDIKTORER` og lager aldri egne.
- **2026-11-03** — Godkjenningen av kontraktendringen fra E1-S04, slik den faktisk skjedde. Den kom ikke i en egen PR, men i PR #4 (hele E1), som ble merget 03.11 kl. 15:57 UTC.
  - **Felipe** (modell) kommenterte PR #4 kl. 15:57 UTC, før merge: «Godt over og godkjenner mergen». Han ga ingen formell review.
  - **Thomas** (dashbord) godkjente ikke før merge. Han bekreftet i etterkant, 03.11, at han godkjenner kontraktendringen. Bekreftelsen kom gjennom Theodor og står ikke på PR #4.
- **2026-11-03** — E2-S01, beslutning 11: `ModellPrediktor` gjelder bare Øvrige og delegerer Passasjer og rader uten tilstand til baselinen (§3). §4 har fått et nytt utdrag med statiske seilasfelt og ablasjonsmodellene, og en presisering om at `allerede_ankommet` ikke er modellinput.
- **2026-11-03** — E2-S03: tilstandsutdraget har fått `ais_status` og en egen metadatafil (`tilstand_ved_kutt.json`), og `allerede_ankommet` er tatt ut (§4).
- **2026-11-03** — E2-S04: det planlagte utdraget med rå statiske seilasfelt er erstattet av `features.csv` med F1–F16, uten rå ETD (§4).
- **2026-11-05** — E2-S03: ny `ais_status` `manglende_dag` for kuttpunkter i en manglende dagstabell (beslutning 09, Felipe) (§4).
- **2026-11-10** — E2-S07: F1–F16 når `ModellPrediktor` gjennom søsterfunksjonen `featurer_ved_kutt` i `__init__.py`, uten kontraktendring. Delegerte rader har `forklaring["delegert"]`, og kodingen står i `app/prediksjon/koding.py` (§3, §5).
- **2026-11-10** — E2-S08: `velg_prediktor` har fått `naa` og velger `ModellPrediktor` bak låsen for testperioden (til E2-S10) og med tilbakefall til baselinen når artefaktet mangler (§3). Testperiodens første ETA leses i `app/prediksjon/__init__.py`, som er grensen mot `app.data`.
