---
title: 'E2-S05 — Tren 6 t- og 24 t-modell'
type: 'feature'
created: '2026-11-06'
status: 'done'
baseline_commit: '0759f48cad765a6395bd7a180766c6bac9be55c5'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/beslutninger/11-modellvalg-ovrige-og-features.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** E2-S04 has produced `data/utdrag/features.csv` (F1–F16, `del` = trening/validering/test), but there is no model yet. E2-S06 (evaluation) and E2-S07 (ModellPrediktor) need four committed, reproducible artifacts: a main model and an ablation without F13–F14, for each horizon, trained only on Øvrige (decision 11, PRD FR9/FR10).

**Approach:** New `scripts/tren.py`. Per horizon it fits candidate configurations on `trening` with the `fartoy_*_modellvalg` history, scores them on `validering`, and picks one. Then it refits the chosen configuration on `trening` + `validering` with the final `fartoy_*` history, as main model and as ablation, and writes `data/modell/modell_{6,24}t.joblib`, `modell_{6,24}t_uten_f13_f14.joblib` and `data/modell/modellvalg.json`. The test period is never read.

## Boundaries & Constraints

**Always:**
- Training rows: `gruppe == "Øvrige"`, `har_tilstand == "1"`, and ground truth in `anlop.csv` (`status_in_area == "ok"` with `arrival_in_area_utc`). Passasjer rows and rows without state are never fitted on.
- Target: calibrated deviation in minutes, `arrival_in_area − (eta_reported − offset_Øvrige)`, with the offset from `data/baseline.json`. A prediction is `calibrated ETA + predicted deviation`, and alert = predicted deviation > 120 min (PRD FR9, A3). `anlop.csv` is read only to build the target. No arrival field goes into a feature.
- Rows with `del == "test"` are dropped as soon as they are read. They do not reach a fit, a category map, a score, or a printout.
- Features F1–F16 as committed. The ablation drops `avgangshavn`, `avgatt_for_kutt` and `timer_siden_avgang` (F13–F14). F8 and F13 are grouped with `lag_kategorikart`/`grupper_sjeldne` on the rows being fitted (trening for selection, trening + validering for the final fit), and the map is stored in the artifact.
- Model family: scikit-learn `HistGradientBoostingRegressor` with native missing-value support and native categorical features (decision 11, choice 1). Fixed `random_state`. Same input gives byte-identical `modellvalg.json` and identical predictions.
- The ablation uses the configuration chosen for the main model at the same horizon, so the difference between them comes only from the features.
- Each artifact is a dict: `modell`, `features` (ordered), `kategorier` (F8/F13 maps), `horisont`, `variant`, `sklearn_versjon`, `trent_paa` (row counts per `del`), `config`, and the sha256 of `features.csv` and `anlop.csv`.
- `requirements.txt` gets `scikit-learn==1.6.1` (pinned, because a joblib artifact is only guaranteed to load with the same version, and 1.6 is the last series for Python 3.9). The commit message gives the reason (arkitektur A7, line 200).
- Everything E2 commits under `data/` stays below 10 MB (NFR1).

**Never:**
- Read `del == "test"` rows for anything, or touch the test period in any other way. Counting test runs belongs to E2-S06.
- Change `features.csv`, `anlop.csv`, `baseline.json` or `app/prediksjon/*` (the AST rule and the predictor contract are unchanged). Write a `ModellPrediktor` (E2-S07) or an evaluation (E2-S06).
- Tune the 120 min alert threshold.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal | fixture with trening/validering/test rows | 4 artifacts + `modellvalg.json` | N/A |
| Passasjer rows | Passasjer rows with ground truth and state | not in any fit (artifact row counts exclude them) | N/A |
| Test rows changed | test-row features and arrival altered | artifacts' predictions and `modellvalg.json` identical | N/A |
| No state / no ground truth | `har_tilstand = 0` or `status_in_area ≠ ok` | row skipped | N/A |
| Missing F2/F3 | empty `fart_knop`, `kurs_mot_havn` | fitted and predicted (NaN) | N/A |
| Unknown category at predict | new `skipstype` | mapped to `annet` | N/A |
| Inconsistent input | `features.csv` voyageid not in `anlop.csv`, or sha mismatch with `features.json` | nothing written | exit with message |

## Decisions (Felipe, 2026-11-09, at approval)

1. **Selection criterion: share within ±30 min on validation (1A), with a simplicity rule.** Configurations within 1 percentage point of the best share count as equally good, because differences smaller than that are noise with about 700 validation rows. Among those, choose the simplest: fewest iterations (`max_iter`) first, then shallowest trees (`max_leaf_nodes`), then lower MAE. The F1 for alerts is reported but does not decide. The rule, the 1 pp tolerance, and which configurations fell inside it are written to `modellvalg.json`.
2. **Candidates (2B):** `loss` ∈ {absolute_error, squared_error} × `learning_rate` ∈ {0.05, 0.1} × `max_leaf_nodes` ∈ {15, 31}, with `max_iter` = 300 and early stopping off. That is 8 HGB configurations per horizon. The reference "deviation = 0" (the calibrated baseline) is scored on the same validation rows and shown in `modellvalg.json` and the printout. It is never chosen. If no configuration beats it, the selected HGB is still trained, and the loss is reported in E2-S06, not hidden.
3. **The 33 early zone entries and the 3 "impossible" rows stay in training (3A).** The label is the same for model and baseline, and the dataset is not changed.
4. The spec is kept as one, above 1 600 tokens (Felipe).

</frozen-after-approval>

## Code Map

- `data/utdrag/features.csv` / `features.json` -- input. Columns: see the header row. Øvrige rows with state: trening 2 867 / 2 704, validering 710 / 688 (6 h / 24 h). `utdrag_sha256` in the JSON.
- `app/prediksjon/features.py:122-137` -- `lag_kategorikart`, `grupper_sjeldne`, `ANNET`. Reuse them, do not copy them. Import from a script: see `scripts/lag_features.py`.
- `data/baseline.json` -- `offset_minutter["Øvrige"]` = 64.2. Read-only.
- `scripts/lag_features.py` -- house style: `REPO_ROT`, overridable paths, `--laget`, `Inkonsistens` → `sys.exit`, deterministic JSON (`sort_keys`, `indent=2`, `\n`).
- `tests/test_features.py:17-20` -- the pattern for loading a `scripts/` module with `importlib`.
- `tests/test_prediktor_kontrakt.py` (AST rule) -- covers `app/prediksjon/*.py` only. `scripts/tren.py` is outside it, and that is fine.
- `docs/arkitektur.md:45,137,200` -- A7, the `data/modell/` layout, and the rule for adding a dependency.
- `.venv` is Python 3.9.6, and scikit-learn is not installed yet.

## Tasks & Acceptance

**Execution:**
- [x] `requirements.txt` -- add `scikit-learn==1.6.1` and install it in `.venv` -- A7, pinned for joblib.
- [x] `scripts/tren.py` -- loader (join on voyageid, filters, test drop), matrix builder (category maps, ablation columns), selection loop, final refit, writers. CLI `--features`, `--anlop`, `--baseline`, `--ut-dir`, `--seed`. Docstring cites decision 11 and the run command.
- [x] `tests/test_tren.py` -- a synthetic fixture in `tmp_path` (about 200 rows across the three `del` values and both groups). Tests: `test_samme_prediksjon_to_ganger`, `test_ingen_passasjer_i_trening`, `test_ablasjon_uten_f13_f14`, `test_testperioden_paavirker_ikke` (alter test rows → identical output), `test_kategori_ukjent_blir_annet`, `test_manglende_verdier`, `test_inkonsistent_input_skriver_ingenting`. Mutation-check the test drop and the Passasjer filter.
- [x] `data/modell/*` -- run on the real data and commit the artifacts and `modellvalg.json` in a separate commit. `docs/epics.md` E2-S05 → ✅ in that commit.
- [x] `docs/arkitektur.md` §4 -- add `modellvalg.json` to the `data/modell/` line.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then it is green in < 1 min, and `test_dataregresjon.py` and the AST rule are unchanged.
- Given the real data, when `scripts/tren.py` runs twice, then `modellvalg.json` is byte-identical, and each artifact gives identical predictions on the validation rows.
- Given the committed artifacts, then they load with the pinned scikit-learn, and the E2 total under `data/` is below 10 MB.

## Implementation Notes

- 2026-11-09: implemented by a subagent from this spec, with the commits re-authored to Felipe. Training rows after the ground-truth filter: 2 767 / 634 at 6 h and 2 608 / 621 at 24 h. The Code Map figures were counted before that filter.
- Mutation checks by the implementer: removing the Passasjer filter fails `test_ingen_passasjer_i_trening`. Removing the test drop makes the run stop (exit 2). Letting test rows into the fit fails `test_testperioden_paavirker_ikke`.
- Validation result: both horizons chose `absolute_error`, lr 0.05, 15 leaves. Within ±30 min: 62.8 % against 41.5 % for the reference at 6 h, and 56.2 % against 39.6 % at 24 h.
- **Finding for E2-S06 (raised with Felipe):** at 6 h, 947 Øvrige rows with ground truth are already in the zone (F6), and 569 of them are labelled late (median +200 min). They are short local trips from ports inside the 15 km zone (Kleppestø, Ågotnes, Skålevik, Bergen). For them, "first position in the zone" is a point after departure, not an arrival. F6 alone gives a validation F1 of 0.82, so the gain must be read with the F6 split in E2-S06.

## Spec Change Log

- 2026-11-09 (Felipe, after the review): **decision 12**. The model is used only for rows that are outside the arrival zone at the cut (F6 = 0). `treningsrader` skips F6 rows (`utelat_i_sonen=True`; `False` is kept only for comparison). The artifacts and `modellvalg.json` are retrained. `modellvalg.json` gains `utvalg`, `enkelhetsregel_endret_valget` and `standardfeil_beste_andel_pp` per horizon, and `toleranse_merknad`. The tolerance is unchanged (Felipe: it was set before the results, and adjusting it now would be fitting after the fact). The rule did not change the choice at either horizon. The new selection is 15 leaves at 6 h and 31 leaves at 24 h. Rows: 2 190 / 459 at 6 h and 2 119 / 450 at 24 h. Validation within ±30 min: 69.1 % against 56.9 % at 6 h, and 59.8 % against 51.8 % at 24 h. E2 data is 7.5 MB in total. `test_ingen_passasjer_i_trening` now also changes F6 rows, and the mutation that removes the filter is caught. The comparison table is in decision 12.

## Review Triage Log

Three layers ran in parallel on 2026-11-09: Blind Hunter (BH), Edge Case Hunter (ECH) and Verification Gap (VG). The five VG gaps were confirmed by mutation runs.

**patch:**
- VG1: the sign of the target and the direction of the offset are untested. Flipping either passed all 8 tests — medium. **patch**: `test_maal_er_kalibrert_avvik`.
- VG2 / BH: `velg` is only checked for self-consistency. Sorting by MAE first passed — medium. **patch**: `test_velg_toleranse_og_enkelhet`.
- VG3: the `historikk="modellvalg"` branch is untested. Turning it off would leak validation history into the model selection and still pass — medium. **patch**: a `matrise` assertion.
- VG4 / BH: `score` has no value assertions. Changing `<= 60` passed — medium. **patch**: `test_score_kjente_tall`.
- VG5 / BH: nothing checks that the committed artifacts load, match `features.csv`, or stay under 10 MB together with E2 data — medium. **patch**: `test_committede_modeller`.
- BH: the artifacts do not carry the Øvrige offset or the sha of `baseline.json`, so E2-S07 could pair a model with another calibration — medium. **patch**: `offset_ovrige_min` and `baseline_sha256` in each artifact.
- BH: numpy and joblib are not pinned, but pickles depend on them — medium. **patch**: pin `numpy==2.0.2` and `joblib==1.5.3`.

**false:**
- BH: E2-S05 is ✅ while the spec is `in-review` and uncommitted — false as a code defect. The spec is committed with the story when the review ends.
- BH: the simplicity tie-break on `max_iter` never decides — false. Decision 2 fixes `max_iter` = 300, so the tie-break on leaves is the one that bites. `REGEL` states the approved rule exactly.
- BH: `modellvalg.json` has no input checksums — false as a defect. It is deliberate, because the file must stay identical when test rows change (I/O matrix). The checksums are in the artifacts.
- BH: the alert metrics of the reference are 0 — false. "Deviation = 0" never exceeds 120 by construction. The comparison for alerts is "alert everyone" in E2-S06 (FR10).
- ECH: the artifacts are not byte-identical when test rows change — false. The matrix requires identical predictions and `modellvalg.json`, and the sha that changes is the input checksum, by design.
- ECH: more than 254 categories — false. The threshold is 20 rows over about 3 400 Øvrige rows, so there can be at most 170 categories.
- ECH: `gruppe` differs from `ship_group` — false. `lag_features.py` derives `gruppe` from the same `ship_group`.

**reject (low):**
- BH: the 1 pp tolerance is below the sampling noise (n = 634/621, SE ≈ 2 pp), so the simplicity rule never applies (`innenfor_toleranse` = [0]) — not a code defect. The tolerance is Felipe's approved decision 1. Raised with Felipe.
- BH: the Code Map row counts (2 867/710) do not match those trained on (2 767/634) — low. The Code Map counted before the ground-truth filter. The fix is to edit the spec, so it is noted in the Implementation Notes.
- BH: the mutation check is ticked with no evidence — low. Recorded in the Implementation Notes.
- BH / ECH: `_skriv_atomisk` is not all-or-nothing across files — low. It needs an `os.replace` failure mid-swap on a local disk, and the fix needs backup and restore logic.
- BH / ECH: a missing `offset_minutter`, malformed timestamps, missing columns, non-UTF-8 input, a non-object JSON, `inf`, unknown `horisont_timer` or `har_tilstand` values, or duplicate (voyageid, H) pairs give a traceback or are silently skipped — low. All inputs are locked, committed and checked by `test_committet_*`, and each guard would add branches.
- BH / VG: the duplicate-voyageid, unknown-`del` and `split`-mismatch branches are untested — low. The matrix asks only for the two that are tested.
- BH: `arkitektur.md` lists `metrikker.json` (E2-S06) and the key order in the JSON is "24", "6" — low and cosmetic.

## Design Notes

The target is the deviation from the calibrated baseline, not the arrival time. A model that predicts 0 then reproduces the baseline exactly, the alert rule is a plain threshold on the output, and E2-S07 only adds the prediction to `eta_reported − offset`. Selection on `trening` → `validering` with the frozen `*_modellvalg` history, followed by a refit on both with the final history, is what decision 11 (choice 5) and E2-S04 prepared.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `.venv/bin/python scripts/tren.py` -- expected: 4 artifacts and `modellvalg.json` in `data/modell/`, selection table printed
- `du -ch data/utdrag/ais_kutt_dekning.csv data/utdrag/tilstand_ved_kutt.* data/utdrag/features.* data/modell/*` -- expected: < 10 MB
