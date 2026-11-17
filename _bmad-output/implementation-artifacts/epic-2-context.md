# Epic 2 Context: Modell bak dashbordet

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->
<!-- Sources: docs/epics.md, docs/prd.md, docs/arkitektur.md, docs/beslutninger/08–09 (the project keeps its planning docs in docs/, not in _bmad-output/planning-artifacts). Compiled 2026-11-03. -->

## Goal

Put a model behind the existing dashboard that tries to beat the calibrated baseline (reported ETA minus a per-group median offset), at two horizons, 6 h and 24 h before reported ETA. If the model does not beat the baseline, the dashboard and the results note say so plainly. Done when the dashboard shows the model by default and `docs/resultater.md` is written. Before anything is trained, a targeted AIS fetch around each cut point is needed. The locked AIS cache has a position near the cut point for only ~31 % (6 h) / ~7 % (24 h) of non-passenger test calls, because its windows start at ETD.

## Stories

- E2-S01: Remaining model choices (one or two models, A1, A2)
- E2-S02: Targeted AIS fetch at the cut points
- E2-S03: State extract and leakage test
- E2-S04: Features and validation split
- E2-S05: Train 6 h and 24 h models
- E2-S06: Evaluation script
- E2-S07: ModellPrediktor
- E2-S08: Swap into the dashboard
- E2-S09: Panel: model vs. baseline
- E2-S10: Results note

## Requirements & Constraints

- **Cut point (non-negotiable):** `t_H = reported ETA − H`, H ∈ {6, 24}. It is never derived from actual arrival (`arrival_in_area`, `arrival_at_quay`). No model input may depend on data after `t_H`. Tests must show predictions unchanged when AIS points after `t_H` are removed or moved, and when actual arrival changes.
- **State lookback:** the last AIS position in [`t_H` − 24 h, `t_H`]. Calls with no position keep their row, get the baseline prediction, and are flagged "no AIS state at prediction time". Calls already arrived before `t_H` are kept and counted separately.
- **Locked dataset:** the dataset (`data/utdrag/anlop.csv`, `data/baseline.json`, `pipeline/data/bergen_eta_avvik.csv`, `pipeline/data/ais_cache/`) and its regression numbers (46.6 % / 79.6 % within ±30 min) must not change. New data goes to new files.
- **Honest numbers:** model selection, features and tuning use only a validation split, the last 20 % of training data in chronological order. The test period is used only for reported numbers, and test runs are counted. Dashboard and evaluation share one metric function.
- **Success:** a higher share within ±30 min than the baseline on Øvrige, per horizon. Alert F1 higher than "alert everyone" (≈ 0.33, base rate 19.5 %).
- **Examiner runs from a clone:** `pytest` must pass with no network and no `pipeline/data/`, in under 1 min. Only the committed state extract and the model artifact ship (< 10 MB together).
- One story = one commit, story ID first in the message. One branch (`epic/e2-modell`) and one PR per epic.

## Technical Decisions

- **Kystdatahuset API:** `POST https://kystdatahuset.kystverket.no/ws/api/ais/positions/for-mmsis-time`, body `{"mmsiIds":[mmsi],"start":"yyyyMMddHHmm","end":"yyyyMMddHHmm"}`, no auth. The old host answers 301, and urllib does not follow 301 on POST. The response window is shifted +1 h (winter) / +2 h (summer) from the requested one, and short windows that end just after midnight can be truncated at 23:59:59. Always request at least one day of margin on each side and filter on the response timestamp (`row[1]`, UTC). Row columns: 0 mmsi, 1 time UTC, 2 lon, 3 lat, 4 cog, 5 sog, 7 calc_speed.
- Pipeline scripts use only the stdlib and live in `pipeline/`. Their output in `pipeline/data/` is gitignored. `pipeline/fetch_ais.py` is locked and exits on purpose, so it must not be edited.
- The port reference point is (60.398, 5.321), the same as `derive_arrivals.py`. Groups are `Passasjer` vs. `Øvrige` (everything else). Split comes from `data/utdrag/anlop.csv`.
- State extract `data/utdrag/tilstand_ved_kutt.csv` (E2-S03) has the columns `voyageid, horisont_timer, t_kutt_utc, lat, lon, distanse_km, fart_knop, kurs_grader, posisjon_alder_min, allerede_ankommet`. It is committed, with the source checksum in `baseline.json`.
- The predictor contract is from E1-S04. ModellPrediktor must get AIS state through the prediction boundary and must not read `data/utdrag/` itself. An AST rule enforces this.

## Cross-Story Dependencies

S02 → S03 → S04 → S05 → S06 → S07 → S08 → S09 → S10, strictly in order. S01's open choices (one or two models, A1, A2) affect S04 and later, not the fetch window in S02.
