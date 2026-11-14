---
title: 'E2-S06 — Evalueringsskript'
type: 'feature'
created: '2026-11-09'
status: 'done'
baseline_commit: 'ec1d420b6f3f7a03f84d3acddb06faaa03d44cb6'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '{project-root}/docs/beslutninger/12-modellen-bare-utenfor-sonen.md'
  - '{project-root}/docs/beslutninger/11-modellvalg-ovrige-og-features.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** E2-S05 produced the models, but there is no evaluation yet that puts model and baseline side by side on the same voyages (PRD FR10). The brief's number to beat (46.6 % within ±30 min) is computed on all Øvrige traffic. Since decision 12 the model applies only to voyages that are outside the arrival zone at the cut, so comparing the model on its subset with 46.6 % on all traffic would compare different rows.

**Approach:** New `scripts/evaluer.py`. It scores model and calibrated baseline per horizon and group on exactly the same voyages, using `app/metrikker.py` as the only metric source, and writes `data/modell/metrikker.json`. The baseline is reported both on all Øvrige traffic (the brief's 46.6 %) and on the model's subset. The brief's success criterion (EN and NO) and PRD FR10 are updated so that model and baseline are compared on the same rows.

## Boundaries & Constraints

**Always:**
- **Rows evaluated** per horizon H ∈ {6, 24}: every voyage in the evaluated split, with each voyage scored at both horizons (`naa = eta_reported − H`, as in `tests/test_dataregresjon.py`). Only voyages with ground truth are scored (`har_fasit`).
- **Arms on the same rows:**
  - Baseline: `BaselinePrediktor` via `lag_input`.
  - Model: the artifact's prediction for Øvrige rows with state and F6 = 0, and the baseline for every other row (Passasjer, no state, F6 = 1), as E2-S07 will delegate (decisions 11 and 12). A model prediction is `eta_reported − offset_ovrige_min + predicted deviation`. Alert = predicted deviation > 120 min. Delegated rows get `forventet_forsinket = None`.
  - Ablation: the same, with `modell_{H}t_uten_f13_f14`.
- **Row sets reported per H:**
  - **Øvrige, all traffic:** baseline (must reproduce 464 / 996 = 46.6 % on test), model arm and ablation arm.
  - **Øvrige, model subset** (state and F6 = 0): baseline, model and ablation on exactly those rows.
  - **Passasjer:** baseline only.
  - Counts: rows with ground truth, rows with state, F6 rows (from the state extract, never from arrival fields), rows in the model subset.
  - **Model share:** the share of Øvrige voyages the model is actually used on (rows in the model subset / all Øvrige rows), both among all rows in the split and among rows with ground truth, so it is clear what the model-subset numbers apply to.
- **Metrics per arm** (all from `app/metrikker.py`):
  - share within ±30 min (`andel_innenfor`, unchanged)
  - MAE and median absolute error, in minutes
  - alert precision, recall and F1 against `er_forsinket` (signed > 120 min against the calibrated baseline, decision 06), next to the "alert everyone" reference on the same rows
  - New functions go into `app/metrikker.py` with tests. Existing behaviour and `test_dataregresjon.py` are unchanged.
- **Splits:**
  - The default run evaluates `validering` (the last 20 % of train, chronological).
  - `--test` evaluates the test period, increments `testkjoringer` in `metrikker.json` and records the date of each test run.
  - The validation and test numbers sit under separate keys, and a validation run never erases test numbers.
- **The model reads** features through `scripts/tren.py`'s `matrise`/`prediker` and the committed `features.csv`. It never reads arrival fields.
- **The brief** (`docs/brief.md`, `docs/brief.no.md`), **PRD FR10** and `docs/status.md` line 43:
  - the success criterion compares model and baseline on the same rows, and the pass/fail is decided on the model subset (Decision 1)
  - one table, not context or a footnote, with two rows: **model subset** and **all Øvrige traffic with delegation**. Columns: number of test voyages with ground truth, model share of Øvrige voyages, baseline ±30 min, model ±30 min. The baseline cells and the model share are filled with test-period numbers from the baseline-only run (46.6 % for all traffic). The model cells say they are filled in E2-S10.
  - 46.6 % stays as the all-traffic baseline, and the baseline on the model subset is named as the number the model must beat
  - the old wording is kept in a dated changelog line
- `metrikker.json` is deterministic: the same input gives identical numbers. Only the test-run log changes on a test run.

**Never:**
- Change or write the artifacts, `features.csv`, `anlop.csv` or `baseline.json`. The only training allowed is the in-memory refit for the validation run (Decision 4); it is never saved. Write `ModellPrediktor` (E2-S07) or touch the dashboard (E2-S08/S09).
- Tune anything on the test period. Run `--test` inside pytest.
- Change the 120 min threshold or the definition of `er_forsinket`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Validation run | default | `metrikker.json` `validering` block written, `testkjoringer` unchanged | N/A |
| Test run | `--test` | `test` block written, `testkjoringer` + 1, date logged | N/A |
| Baseline on test | real data | Øvrige all-traffic baseline 464/996, Passasjer 343/431 | N/A |
| Delegated row | Passasjer / no state / F6 = 1 | model arm = baseline prediction, `forventet_forsinket` None | N/A |
| Baseline alerts | baseline arm | precision/recall/F1 reported as not applicable (`null`), "alert everyone" shown | N/A |
| Model share | any run | `andel_modellutvalg` = subset rows / all Øvrige rows, for all rows and for rows with ground truth | N/A |
| Subset identity | any run | model and baseline subset rows have identical voyageid sets | N/A |
| Artifact mismatch | artifact `features_sha256` ≠ committed `features.csv` | nothing written | exit with message |

## Decisions (Felipe, 2026-11-09, at approval)

1. **Pass/fail is decided on the model subset (1A).** The model is judged where it is used (decision 12). The numbers for all Øvrige traffic with delegation (B) stand in the same table as the model subset, both in the brief and in the results note, not as context or a footnote. The model share of Øvrige voyages is stated next to them, so it is clear what the model-subset number applies to.
2. **No test run in this story (2B).** E2-S06 commits only validation numbers, and the script is finished and tested here. The single test run is made in E2-S10. Model, configuration and selection rules are locked before that run and nothing is changed afterwards. If anything is changed anyway, it is stated in the results note. This is written into E2-S10 in `docs/epics.md`.
   - Baseline-only numbers on the test period (the 464/996 regression, the subset baseline and the model share for the brief table) do not use the model and are allowed. No model or ablation prediction is computed on the test period in this story, in code, tests or by hand.
3. The spec is kept as one, above 1 600 tokens (Felipe).
4. **Validation numbers are held out (review, 2026-11-09).** The final artifacts are fit on train + validation, so scoring them on validation is in-sample. For the validation run, `evaluer.py` refits the configuration chosen in E2-S05 (read from the artifact's `config`, which must equal `modellvalg.json` `valgt_config`) in memory, on the train rows only, with categories fitted on those rows and the `fartoy_*_modellvalg` history, exactly as `tren.tren_horisont` did at selection. It predicts validation with the same `modellvalg` history. The ablation arm is refit the same way with `FEATURES_UTEN_F13_F14`. Nothing is saved. The model arm's ±30 share on the validation subset must then equal the chosen candidate's `andel_30` in `modellvalg.json` (69.1 % and 59.8 %), and a test asserts it. The test run (E2-S10) uses the committed final artifacts, as before.
5. **The alert bar is on the model subset, and the docs say so outright (review, 2026-11-09).** Pass/fail on alerts is F1 above "alert everyone" on the model subset, like ±30. The brief (EN/NO) and PRD FR10 state, next to the criterion and in the changelog:
   - the bar is lower than before: on the test period the base rate in the model subset is 7.8 % (6 h) and 10.5 % (24 h), which gives F1 ≈ 0.14 and 0.19, against 19.5 % and F1 ≈ 0.33 on all Øvrige traffic
   - why: most of the delayed Øvrige voyages (60–75 %) are F6 rows inside the arrival zone, whose label does not measure an arrival (decision 03), and they go to the baseline, which cannot alert
   - that the bar was moved after the validation results were known (E2-S05, decision 12)
   - the alert numbers for all Øvrige traffic with delegation stand in the same table as the model subset

</frozen-after-approval>

## Code Map

- `app/metrikker.py` -- `har_fasit`, `andel_innenfor(prediksjoner, anlop, minutter)` (raises on missing or duplicate predictions) and `dekning`. Add MAE/median and alert-metric functions here with the same lookup-by-voyageid contract.
- `app/prediksjon/__init__.py` -- `lag_input(anlop, naa)`, `Prediksjon`, `PrediksjonsInput`. `app/prediksjon/baseline.py` -- `BaselinePrediktor` (offset from `baseline.json`).
- `app/data.py` -- `last_utdrag()`, `Anlop` (`gruppe`, `faktisk_ankomst`, `split`). The validation split comes from `features.csv` `del` (or `features.valideringssplitt`).
- `tests/test_dataregresjon.py:31-59` -- the harness that scores at the cut point (`naa = eta − H`), and the locked numbers 464/996 and 343/431.
- `scripts/tren.py` -- `matrise`, `prediker`, `HISTORIKK` (the final `fartoy_*` history is the default). Load it with `importlib` as `scripts/sammenlign_f6.py` does. Artifact keys: `offset_ovrige_min`, `features_sha256`, `utvalg`.
- `data/utdrag/features.csv` -- `har_tilstand`, `i_sonen_ved_kutt` (F6), `del`.
- `docs/brief.md:53`, `docs/brief.no.md:53`, `docs/prd.md` FR10 (lines 100–107), `docs/status.md:43` -- the success-criterion text to update.
- `docs/beslutninger/06-signert-forsinkelsesflagg.md` -- the definition of `er_forsinket`.

## Tasks & Acceptance

**Execution:**
- [x] `app/metrikker.py` -- add the absolute-error statistics and the alert metrics (with "alert everyone"). Unit tests in `tests/test_metrikker.py`.
- [x] `scripts/evaluer.py` -- build the arms and the row sets, score them, and write `metrikker.json` (`validering` / `test`, `testkjoringer`, the test-run log, and the input sha256s). `--test` flag. The artifact sha check comes first.
- [x] `tests/test_evaluer.py`:
  - the baseline on the real test split reproduces 464/996 and 343/431 through the script's functions, with no `--test` and no counter change
  - the matrix rows on a small fixture: delegation, subset identity, the counter, a validation run that keeps the test block, and artifact mismatch
  - `metrikker.json` has the ablation keys and the subset keys, and Passasjer has only the baseline
- [x] `scripts/evaluer.py` -- a `--bare-baseline` mode (or a function used by the test) that scores only the baseline on the test period, without loading the model and without touching `testkjoringer`. It gives the brief table's baseline cells and the model share, printed and written to `metrikker.json` under `test_bare_baseline`. A test shows that this mode never loads a model artifact.
- [x] `scripts/evaluer.py` -- the in-memory train-only refit for the validation run (Decision 4). The `merknad` about in-sample numbers goes away; the block says instead that the validation model arms are a train-only refit of the chosen configuration.
- [x] `data/modell/metrikker.json` -- run on validation and commit (separately). No test run (Decision 2).
- [x] `docs/brief.md`, `docs/brief.no.md`, `docs/prd.md` FR10, `docs/status.md` -- update the success criterion as above, with a changelog line.
- [x] `docs/epics.md` -- E2-S06 ✅ in the commit that commits `metrikker.json`. E2-S10 gets: the lock before the test run (Decision 2), and the results note's table with the model subset and all Øvrige traffic with delegation side by side, with the model share. Changelog line.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then it is green in < 1 min, and `test_dataregresjon.py` and the AST rule are unchanged.
- Given a validation run, when `metrikker.json` is read, then every model-vs-baseline pair has the same `n`, and the subset rows are a subset of the all-traffic rows.
- Given two validation runs on the same input, then `metrikker.json` is byte-identical.

## Implementation Notes

- Commits: `79ea662` (script, metrics, tests, docs), `73bc453` (first `metrikker.json`), `d36964c` (review fixes, Decisions 4–5), `78a6a02` (`metrikker.json` with held-out validation arms). No `--test` run; `testkjoringer` = 0.
- Validation, model subset, model arm: 69.1 % (6 h) and 59.8 % (24 h) within ±30 min, equal to the chosen candidates in `modellvalg.json`; ablation 68.0 % and 56.7 %.
- Test period, baseline only: model subset 433/733 and 418/742; model share 73.6 % and 74.5 % of Øvrige voyages with ground truth. Of the 194 delayed Øvrige voyages, 57 / 78 are in the subset, 107 / 92 are F6 rows and 30 / 24 have no state (6 h / 24 h).
- Tests: 300 passed (about 17 s). Two validation runs give a byte-identical `metrikker.json`.

## Spec Change Log

- **2026-11-09, review iteration 1.** Triggering findings: triage rows 1–3 (in-sample validation numbers, the lower alert bar not stated). Felipe answered at the review: refit in memory on train only for validation (Decision 4), and keep the alert bar on the model subset but state it outright (Decision 5). Amended inside the frozen block with Felipe's answers: Never-list (in-memory refit allowed), Decisions 4–5, two tasks. Known-bad state avoided: model numbers on validation read as held out when they are in-sample, and a lowered alert bar presented without saying so. The code was not reverted and re-derived: the fixes are applied on top of the first implementation by the same implementer, since the rest of it passed review. KEEP: the arm/row-set structure, `_par` in `app/metrikker.py`, the sha/offset check first, `--bare-baseline` with no model load, byte-identical reruns, Passasjer baseline only.

## Review Triage Log

Iteration 1 (2026-11-09). Layers: blind hunter (BH), edge-case hunter (EC), verification gap (VG).

| # | Source | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|---|
| 1 | BH, impl report | Validation model/ablation numbers are in-sample (final artifacts are fit on train + validation) | high | intent_gap | `metrikker.json` validation subset: model 78.2 % / 72.4 % against held-out 69.1 % / 59.8 % in `modellvalg.json`. The frozen block says to evaluate with the artifacts and never retrain, so the fix needs Felipe. |
| 2 | BH | The alert bar moved from "alert everyone" on all Øvrige (F1 0.33) to the model subset (0.14 / 0.19), after validation results were known, and the changelog does not say so | high | intent_gap | Test base rate 57/733 and 78/742 on the subset against 194/996 overall. Follows from Decision 1, but the brief's own rule requires it to be stated and justified. |
| 3 | BH | 60–75 % of delayed Øvrige voyages are outside the model subset, and no doc says so | medium | intent_gap | Same numbers as #2. Grouped with #2 for the decision; the wording follows from it. |
| 4 | VG, BH | The subset thresholds 433/733, 418/742 and the model share are not pinned by a test on real data | medium | patch | `test_baseline_testperioden_lik_dataregresjonen` asserts only `ovrige_alle` and `passasjer`. |
| 5 | BH | The brief table has no alert columns, and "model share" does not say it is among voyages with ground truth | medium | patch | FR10: precision, recall and F1 are always shown together. |
| 6 | BH | FR10 still asks for "a number only for rows with state", which the script does not score | low | patch | `evaluer.py` has only `ovrige_alle`, `ovrige_modellutvalg`, `passasjer`. |
| 7 | BH | E2-S10 still lists "numbers with and without rows in the arrival zone", which FR10 removed | low | patch | `docs/epics.md` E2-S10. |
| 8 | BH, EC | `anlop_i_split` checks split agreement in one direction only | low | patch | A `del=test` feature row with a non-test `anlop` split is silently dropped. |
| 9 | BH, EC | `--test` can run a second time without refusal | medium | patch | `oppdater` increments without checking; Decision 2's lock is only procedure. |
| 10 | BH | Spec untracked, and E2-S06 ✅ set before the review | low | patch | Process; fixed when the spec is committed with the final commit. |
| 11 | VG, BH | `main --test` mapping and the test-split model path are never exercised | medium (unverified) | defer | The frozen block forbids running `--test` in pytest. |
| 12 | EC | Empty row set raises an uncaught ValueError | low | reject | No split has an empty row set; loud failure is acceptable. |
| 13 | EC | `varsle_alle` gives recall 0 when no voyage is late, against its docstring | low | patch | Docstring correction. |
| 14 | EC | NaN/inf prediction not guarded | low | reject | HGB does not produce NaN on finite input; a failure would be loud. |
| 15 | EC | Duplicate feature rows overwrite silently | low | reject | `features.csv` uniqueness is tested in E2-S04. |
| 16 | EC | Corrupt `metrikker.json` gives a traceback | low | reject | A loud failure, and the file is committed. |
| 17 | EC | `er_forsinket` on a voyage without ground truth gives a TypeError | low | reject | Callers filter on `har_fasit` first. |
| 18 | EC | Horizon mismatch between predictions and the calibrated baseline is not checked | false | reject | Both arms are built for the same H in `evaluer_horisont`. |
| 19 | EC | `kan_varsle` computed only over scored pairs | low | reject | No arm sets alerts only on rows without ground truth. |

## Design Notes

E2-S07 does not exist yet, so the model arm is built in the script from the artifact, with the same delegation E2-S07 must implement. E2-S07's test should then show that `ModellPrediktor` gives the same predictions as `evaluer.py` on the validation rows. That keeps a single definition of "the model arm".

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `.venv/bin/python scripts/evaluer.py` -- expected: `metrikker.json` `validering` block, with a table printed
- `.venv/bin/python scripts/evaluer.py && git diff --quiet data/modell/metrikker.json` -- expected: no change on rerun
