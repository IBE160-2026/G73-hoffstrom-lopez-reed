---
title: "Arkitektur: AIS-basert ankomstprediksjon"
status: aktiv
created: 2026-10-16
updated: 2026-10-16
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
class Prediksjon:
    voyageid: int
    horisont_timer: int                  # 6 eller 24, valgt fra rapportert ETA − naa (PRD FR2)
    predikert_ankomst: datetime          # UTC, tz-aware
    forventet_forsinket: Optional[bool]  # None = prediktoren kan ikke varsle (baseline)
    forklaring: dict                     # input som ble brukt; vises på detaljsiden og mates til AI-laget (E3)

class Prediktor(Protocol):
    navn: str                            # vises i prediktor-stripa, f.eks. "Kalibrert baseline"
    kan_varsle: bool
    def prediker(self, anlop: Sequence["Anlop"], naa: datetime) -> list[Prediksjon]: ...

def velg_prediktor() -> Prediktor:
    """PREDIKTOR=baseline|modell|auto (standard auto: modell hvis artefakt finnes, ellers baseline)."""
```

- `naa` sendes med, slik at horisonten kan velges: ≤ 6 t hvis `eta_reported − naa ≤ 6 t`, ellers 24 t. Kuttpunktet `t_H = eta_reported − H` er da alltid ≤ `naa` (PRD FR9a). Modellen leser tilstanden ved `t_H` fra `tilstand_ved_kutt.csv` og aldri noe nyere. Baselinen bruker bare horisonten til visning.
- *Avvik* og *forsinket* (fasit) regnes i `metrikker.py` mot kalibrert baseline og er aldri en del av `Prediksjon`. Bytter man prediktor, endres derfor ikke fasiten (PRD §3).
- Den samme kontrakttesten (`tests/test_prediktor_kontrakt.py`) kjøres parametrisert mot alle prediktorer. En ny prediktor er ikke ferdig før den består.

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

`voyageid, horisont_timer, t_kutt_utc, lat, lon, distanse_km, fart_knop, kurs_grader, posisjon_alder_min, allerede_ankommet`

Feltene er tomme når posisjon mangler, og raden beholdes. Fila er ~15 600 rader og ~1,5 MB og committes. Det er den eneste AIS-avledede inputen modellen får hos sensor (PRD NFR1).

**Tidssoner:** all lagring og beregning skjer i UTC. `arrival_in_area_utc` mangler tidssonesuffiks i kilden og normaliseres ved innlasting. Visning skjer i `Europe/Oslo` via `zoneinfo`. `tzdata` ligger i `requirements.txt` fordi Windows ikke har tidssonedatabasen.

**`data/modell/`** (E2): `modell_6t.joblib`, `modell_24t.joblib` og `metrikker.json`. Alt committes hvis det er under 10 MB, så sensor slipper å trene.

## 5. Mappestruktur

```
app/
  __init__.py          create_app(), laster data én gang
  data.py              Anlop-dataklasse, last_utdrag(), anlop_i_vindu(naa, timer=24, vis=…)
  metrikker.py         andel_innenfor(…, min=30), presisjon_recall(…)        (A6)
  visning.py           formatering: norsk tid, «+3 t 22 min», horisont-bøtte
  prediksjon/
    __init__.py        Prediksjon, Prediktor, velg_prediktor()                (A5)
    baseline.py        BaselinePrediktor                                      (E1)
    modell.py          ModellPrediktor                                        (E2)
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
| Dataregresjon | utdraget gir 46,6 % / 79,6 % (naiv 12,9 % / 7,4 %) og 1 427/1 566 med fasit på testsplitten | `tests/test_dataregresjon.py` (PRD FR8, NFR3) |
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
