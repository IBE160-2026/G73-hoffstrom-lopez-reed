# Epic 1 Context: Dashbord v1 på kalibrert baseline

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->
<!-- Sources: docs/epics.md, docs/prd.md, docs/arkitektur.md, docs/ux/dashbord.md (the project keeps its planning docs in docs/, not in _bmad-output/planning-artifacts). -->

## Goal

Deliver a runnable, server-rendered web dashboard that replays the locked historical dataset of Bergen port calls and shows, for a simulated "now", every call with reported ETA in the next 24 hours together with a prediction from the calibrated baseline (reported ETA minus a per-group median offset). This is the one deliverable that cannot slip: the examiner clones the repo and grades the running app. It must be runnable in under 20 minutes from README, without network beyond `pip install`, keys or the gitignored pipeline data. The model (E2) and AI layer (E3) later plug in behind the same predictor interface without rebuilding the views.

## Stories

- E1-S01: Prosjektskjelett
- E1-S02: Datautdrag og lagret baseline
- E1-S03: Datalag
- E1-S04: Prediktor-grensesnitt og kalibrert baseline
- E1-S05: Metrikkmodul og dataregresjon
- E1-S06: Hovedskjerm med anløpsliste
- E1-S07: Tidsvelger for «nå» med validering
- E1-S08: Filter alle/passasjer/øvrige
- E1-S09: Fasit-bryter
- E1-S10: Sortering
- E1-S11: Detaljside for anløp
- E1-S12: Treffsikkerhetspanel og metodeside
- E1-S13: Visuelt design og kontrast
- E1-S14: Responsiv layout
- E1-S15: UU-gjennomgang
- E1-S16: README og klone-test
- E1-S17: Skjermbilder mot skisse

## Requirements & Constraints

- App starts and all tests run with no `.env`, no network and no `pipeline/data/`. `pytest` under one minute; `GET /` under 1 s locally.
- Every story has checkable acceptance criteria and a named test. One story = one commit, story ID first in the commit message; status in `docs/epics.md` set to ✅ in the same commit. If behaviour deviates from PRD/UX, that doc is updated in the same commit with a changelog line.
- Secrets only in `.env` (gitignored); `.env.example` lists all variables with no real keys.
- Honest numbers: dashboard and evaluation share one metrics function. Baseline regression figures on the test split: Øvrige 46,6 % within ±30 min (naive 12,9 %), Passasjer 79,6 % (naive 7,4 %); coverage 1 427 of 1 566.
- Deviation (avvik) and FORSINKET (> 120 min, signed) are always computed against the calibrated baseline, never the active predictor. The baseline never issues a warning.
- Domain vocabulary is Norwegian and fixed (anløp, rapportert ETA, faktisk ankomst, Passasjer/Øvrige, avvik, varsel, horisont, «nå», testperioden). Use the same names in code, UI and tests.
- Accessibility (WCAG 2.1 AA) from the start: visible labels, keyboard-only use, not colour alone, `lang="nb"`, one `h1`, real tables with `th scope`, 360–1920 px without horizontal scroll.

## Technical Decisions

- Python ≥ 3.9 + Flask 3, Jinja templates, server-rendered HTML. No database (CSV loaded into memory at startup), no JS framework, no build step, one CSS file with tokens.
- Dependencies: `flask>=3,<4`, `tzdata`, `pytest`. New dependencies are justified in the commit message of the story that adds them.
- Layout: `app/` (`__init__.py` with `create_app()`, `data.py`, `metrikker.py`, `visning.py`, `prediksjon/`), `data/` (committed extract `utdrag/anlop.csv` + `baseline.json`), `scripts/`, `tests/` (`fixtures/anlop_mini.csv`, one test file per module).
- Predictor contract (`app/prediksjon/__init__.py`): frozen dataclass `Prediksjon(voyageid, horisont_timer, predikert_ankomst, forventet_forsinket, forklaring)`; `Prediktor` protocol with `navn`, `kan_varsle`, `prediker(anlop, naa)`; `velg_prediktor()` driven by `PREDIKTOR=baseline|modell|auto`. A parametrised contract test runs against every predictor.
- Data: UTC everywhere internally; `arrival_in_area_utc` has no suffix in the source and is normalised to UTC on load; display in `Europe/Oslo`. Extract columns: `voyageid, mmsino, shipname, ship_group, eta_reported, arrival_in_area_utc, status_in_area, split`. Train/test is a chronological 80/20 split (6 260 / 1 566; test starts 2025-09-14T03:15Z). Offsets 44,8 (Passasjer) / 64,2 (Øvrige) min. `baseline.json` stores offsets, test start, source path, source sha256, date made.
- Config (`.env.example`): `PREDIKTOR=auto`, `LLM_MODUS=test`, `ANTHROPIC_API_KEY=`, `LLM_MODELL=claude-haiku-5-5`.
- State lives in the URL (`naa`, `vis`, `fasit`, `sorter`); invalid parameters give 200 with a form error, never 400.

## UX & Interaction Patterns

- Main screen: header + form (date, time, filter radio group, fasit checkbox, "Oppdater" button — never auto-submit) → predictor strip (always visible) → call list sorted by predicted arrival → accuracy panel for the whole test period. Default "now" is 08.10.2025 08:00 Norwegian time (15 calls).
- Detail page `/anlop/<id>` with `<dl>` timestamps and the prediction explanation; "Tilbake" keeps the query.
- Under 640 px the same table restyles into cards via CSS (`data-label`).
- Colour tokens with light/dark themes are defined in the UX doc; contrast is tested from `style.css`.

## Cross-Story Dependencies

- Stories are a linear chain S01 → S12; S13 depends on S06; S14–S17 follow in order.
- E2 adds its predictor behind the S04 contract and reuses the S05 metrics module; E3's adapter depends on S04 if E2 slips.
