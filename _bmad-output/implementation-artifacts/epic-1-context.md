# Epic 1 Context: Dashbord v1 på kalibrert baseline

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->
<!-- Sources: docs/epics.md, docs/prd.md, docs/arkitektur.md, docs/ux/dashbord.md (the project keeps its planning docs in docs/, not in _bmad-output/planning-artifacts). Compiled 2026-10-27. -->

## Goal

Deliver a runnable, server-rendered Flask dashboard that replays the locked historical dataset of Bergen port calls: for a simulated «nå», it lists every anløp with reported ETA in the next 24 hours together with a prediction from the calibrated baseline (rapportert ETA minus a per-group median offset). This is the deliverable that cannot slip: the examiner clones the repo and grades the running app, so it must work in under 20 minutes from the README with no keys, no network beyond `pip install` and no gitignored pipeline data. E1 is done when the clone test (E1-S16) is under 20 min and the UU checklist is filled in. Phase 3 ends 6 Nov, so stories are split into **MÅ** (must ship) and **KAN** (only if time allows, still in E1). The model (E2) and AI layer (E3) later plug in behind the same predictor interface without rebuilding the views.

## Stories

MÅ, in order (S01–S04 done):
- E1-S01: Prosjektskjelett ✅
- E1-S02: Datautdrag og lagret baseline ✅
- E1-S03: Datalag ✅
- E1-S04: Prediktor-grensesnitt og kalibrert baseline ✅
- E1-S05: Metrikkmodul og dataregresjon
- E1-S06: Hovedskjerm med anløpsliste (includes UU minimum)
- E1-S16: README og klone-test

KAN, in this order:
- E1-S07: Tidsvelger for «nå» med validering
- E1-S13: Visuelt design og kontrast (rest: dark theme, `--varsel`/`--ok`, tabular-nums)
- E1-S08: Filter alle/passasjer/øvrige
- E1-S09: Fasit-bryter
- E1-S11: Detaljside for anløp
- E1-S12: Treffsikkerhetspanel og metodeside
- E1-S10: Sortering
- E1-S15: UU-gjennomgang (rest: KAN screens, VoiceOver)
- E1-S14: Responsiv layout (rest: form in `<details>`, KAN screens)
- E1-S17: Skjermbilder mot skisse

## Requirements & Constraints

- App starts and all tests run with no `.env`, no network and no `pipeline/data/`. `pytest` under one minute; `GET /` under 1 s locally for the default window.
- One story = one commit, story ID first in the message; status in `docs/epics.md` set to ✅ in the same commit, with a passing named test. If behaviour deviates from PRD/UX, update that doc in the same commit with a changelog line.
- Honest numbers: dashboard and evaluation share one metrics function. Regression figures on the test split (one decimal): baseline Øvrige 46,6 %, Passasjer 79,6 % within ±30 min; naive ETA 12,8 % / 7,4 %; 1 427 of 1 566 with fasit (126 `empty`, 8 `not_detected`, 5 `avkortet_av_neste_seilas`). Metrics count only calls with fasit.
- Avvik and FORSINKET (> 120 min, signed) are always computed against the calibrated baseline, never the active predictor, and never live in `Prediksjon`. The baseline never warns: varsel column shows «–» with a readable explanation.
- Window selects on **reported** ETA in the half-open [nå, nå + 24 t), sorted by predicted arrival (decided for v1; predicted-arrival selection is revisited in E2-S08). Horizon bucket (≤ 6 t / 6–24 t) is computed from reported ETA − nå. Predicted arrival before «nå» gets the help text «predikert før valgt tidspunkt».
- Times display in Norwegian time **rounded to nearest minute** (display only; ±30 min, avvik and all calculations use unrounded times). BERGEN ENERGY 09:55:48 → «ons 09:56».
- UU minimum is MÅ (in E1-S06), not KAN: UU1 contrast (light-theme tokens, ≥ 4,5:1 text, ≥ 3:1 borders), UU2 keyboard (skip link first, logical Tab order, 3 px `--aksent` focus ring, never bare `outline: none`), UU4 text alternatives (meaningful icons labelled, decorative `aria-hidden`), UU6 (viewport meta, cards with `data-label` under 640 px, no horizontal scroll at 360/1280 px or 200 % zoom), UU7 (`lang="nb"`, one `h1`, real `<table>` with `th scope="col"`, `header`/`main` landmarks). UU5 form labels apply once forms exist (S07/S08). UU3: FORSINKET uses icon + text, not colour alone.
- Domain vocabulary is Norwegian and fixed (anløp, rapportert ETA, faktisk ankomst, Passasjer/Øvrige, avvik, varsel, horisont, «nå», testperioden); use the same names in code, UI and tests.
- Secrets only in gitignored `.env`; `.env.example` has no real keys.

## Technical Decisions

- Python ≥ 3.9 + Flask 3, Jinja, server-rendered HTML. No database (CSV in memory), no JS framework, no build step, one CSS file with tokens. Deps: `flask>=3,<4`, `tzdata`, `pytest`; any new dependency is justified in its story's commit.
- **Predictor contract (A5), input-based:** dashboard reaches predictors only via `lag_input(anlop, naa) -> PrediksjonsInput`. `PrediksjonsInput` (frozen: voyageid, mmsino, shipname, ship_group, gruppe, eta_reported, horisont_timer, t_kutt) has no path to `faktisk_ankomst`, `status_in_area` or `split`. `prediker(inputs: Sequence[PrediksjonsInput], naa)` returns `list[Prediksjon]` and raises `TypeError` for anything else; there is no variant taking `Anlop`. `lag_input` sets horizon (6 t if eta − nå ≤ 6 t, else 24 t) and `t_kutt = min(eta − H, naa)`. Only `app/prediksjon/__init__.py` may import `app.data`; an AST test enforces this for predictor modules. `Prediksjon.predikert_ankomst` is UTC, tz-aware, full precision. `velg_prediktor()` reads `PREDIKTOR=baseline|modell|auto` (unknown → `ValueError`; in E1 all resolve to baseline). Contract changes need a separate PR approved by both owners.
- Parametrised contract test runs against every predictor: no fasit in input, changed fasit gives identical predictions, `t_kutt ≤ naa`, no data-layer reads.
- Data: UTC internally, `Europe/Oslo` for display via `zoneinfo`. Committed `data/utdrag/anlop.csv` and `data/baseline.json` (offsets 44,8 Passasjer / 64,2 Øvrige min, test start 2025-09-14T03:15Z, source sha256). Avvik/forsinket are computed in-app, never stored.
- Metrics (A6): `app/metrikker.py` is the single source for `andel_innenfor(...)` and `dekning()`, reused later by `scripts/evaluer.py`.
- Routes: `GET /` (`naa`, `vis`, `fasit`, `sorter` in URL), `GET /anlop/<voyageid>` (404 with back link), `GET /metode`. Invalid parameters give 200 with a form error and the default window, never 400.
- Tests: Flask test client for routes, `html.parser` for UU structure, contrast computed from `static/style.css` tokens.

## UX & Interaction Patterns

- Main screen order: skip link → header with `h1` → GET form (submit only via «Oppdater», never auto-submit) → always-visible predictor strip («Kalibrert baseline», says it cannot warn) → list → accuracy panel labelled «hele testperioden».
- Default «nå» is 08.10.2025 08:00 Norwegian time: 15 anløp; `vis=ovrige` gives 9. Columns: skip, gruppe, rapportert, predikert, horisont, varsel. Ship name links to detail page.
- Empty window: «Ingen anløp med rapportert ETA i dette vinduet. Prøv et annet tidspunkt.»
- Under 640 px the same table restyles into cards via CSS (`data-label`).
- Colour tokens (light + dark) and target contrast ratios are fixed in the UX doc; light theme is default, dark via `prefers-color-scheme` (KAN).

## Cross-Story Dependencies

- MÅ chain: S04 → S05 and S04 → S06; S16 needs S05 and S06. Run a first clone test right after S06 and repeat at the end.
- KAN chain: S06 → S07 → S08 → S09 → S10 → S11 → S12; S13 depends on S06, S14 on S13, S15 on S14, S17 on S16.
- S16 fills the UU checklist for everything built and marks unbuilt screens «ikke bygd (KAN)»; README points to 46,6 % from the S05 regression (in the panel only if S12 is built).
- E2 adds `ModellPrediktor` behind the S04 contract (state at `t_kutt` passes through `lag_input` or a sibling in `__init__.py`), reuses S05 metrics, and revisits window selection in E2-S08.
