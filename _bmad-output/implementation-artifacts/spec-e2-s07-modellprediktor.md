---
title: 'E2-S07 — ModellPrediktor'
type: 'feature'
created: '2026-11-09'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/beslutninger/12-modellen-bare-utenfor-sonen.md'
  - '{project-root}/docs/arkitektur.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The trained models (E2-S05) and the evaluation (E2-S06) exist, but nothing in the app can use them: there is no predictor behind the E1-S04 contract that predicts with the artifact (FR9). E2-S08 needs one to swap into the dashboard.

**Approach:** New `ModellPrediktor` in `app/prediksjon/modell.py` with `kan_varsle = True`. It predicts Øvrige voyages in the model subset (state at the cut and F6 = 0, decision 12) with `modell_{H}t.joblib` and delegates every other row to `BaselinePrediktor`, exactly as the model arm in `scripts/evaluer.py` does. F1–F16 reach it through the prediction boundary in `app/prediksjon/__init__.py`, never by reading files in the predictor module.

## Boundaries & Constraints

**Always:**
- **Contract:** passes every test in `tests/test_prediktor_kontrakt.py` after being added to `PREDIKTORER`, including the leakage tests and the AST rule. `ModellPrediktor()` takes no required arguments and loads the committed artifacts.
- **Model rows:** `predikert_ankomst = eta_reported − offset_ovrige_min + predicted deviation`, with the offset from the artifact. `forventet_forsinket = predicted deviation > 120` (the same threshold as `er_forsinket`, decision 06). `forklaring` has `metode: "modell"`, `variant`, `horisont`, `predikert_avvik_min` and the feature values used.
- **Delegated rows** (Passasjer, no state, F6 = 1, or no feature row valid at `t_kutt`): the baseline's `Prediksjon`, with `forventet_forsinket = None` and `forklaring["delegert"]` naming the reason (`passasjer`, `ingen_tilstand`, `i_sonen_ved_kutt`, `ingen_featurerad`).
- **Time:** a feature row is only used when its `t_kutt_utc` equals the input's `t_kutt`. When `lag_input` clamps the cut to `naa` (ETA more than 24 h ahead), the committed row is from after `naa`, so the row is delegated.
- **What the boundary hands over:** only the artifact's feature columns. Never `del`, `gruppe` from the file, `t_kutt_utc` beyond the equality check, the `_modellvalg` history, or anything from `anlop.csv` beyond what `lag_input` already gives.
- **One definition of the model arm:** the feature encoding (`matrise`) moves to `app/prediksjon/` and `scripts/tren.py` imports it from there. The committed artifacts and `modellvalg.json` are unchanged.
- **Equivalence:** on the validation rows at the cut (`naa = eta − H`), `ModellPrediktor` gives the same `predikert_ankomst` and `forventet_forsinket` as `evaluer.modell_prediksjoner` with the final artifacts.
- **Artifact check:** `features_sha256` in each artifact must equal the sha of the features file the boundary serves, and `offset_ovrige_min` must equal `baseline.json`. Otherwise `ModellPrediktor()` raises, so E2-S08 can fall back to the baseline.

**Never:**
- Score `ModellPrediktor` against ground truth on the test period, in tests or by hand, or print or aggregate its accuracy there. Running it on test-period rows is allowed only for the contract, leakage and determinism checks, which never read the ground truth for scoring. Nothing is changed on the basis of the baseline-only test numbers from E2-S06 (Felipe, 2026-11-09).
- Change `velg_prediktor`, the templates or the dashboard (E2-S08). Use the ablation artifacts in the app.
- Retrain or change the artifacts, `features.csv`, `metrikker.json` or `modellvalg.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Model row | Øvrige, state, F6 = 0, `t_kutt = eta − H` | model prediction, alert True/False, `metode: "modell"` | N/A |
| Passasjer | any | baseline, `forventet_forsinket` None, `delegert: "passasjer"` | N/A |
| No state | Øvrige, `har_tilstand = 0` | baseline, `delegert: "ingen_tilstand"` | N/A |
| In zone | Øvrige, F6 = 1 | baseline, `delegert: "i_sonen_ved_kutt"` | N/A |
| Cut clamped | ETA − naa > 24 h | baseline, `delegert: "ingen_featurerad"` | N/A |
| Unknown voyage | voyage not in `features.csv` (e.g. the mini fixture) | baseline, `delegert: "ingen_featurerad"` | N/A |
| Mixed batch | model and delegated rows | output order equals input order, one `Prediksjon` per input | N/A |
| Boundary output | any voyage and horizon | `featurer_ved_kutt` returns only the artifact's feature columns (or None), never `del`, `gruppe`, `t_kutt_utc`, `_modellvalg` columns, `voyageid`, or any label or arrival field (`faktisk_ankomst`, `arrival_*`, `status_in_area`, `split`, `avvik*`, `er_forsinket`) | N/A |
| Artifact mismatch | sha or offset differs | — | `ModellPrediktor()` raises `ValueError` with the reason |

## Decisions (Felipe, 2026-11-09, at approval)

1. **F1–F16 reach the predictor through a sister function in the boundary (1A), with no contract change.** `app/prediksjon/__init__.py` gets `featurer_ved_kutt(inp)`. It looks up the voyage and horizon in `features.csv` and returns a frozen mapping of only the artifact's feature columns, and only when the row's cut equals `inp.t_kutt`; otherwise None. `ModellPrediktor` calls it. `PrediksjonsInput`, `INPUTFELT` and the dashboard's call to `lag_input` are unchanged, so no separate contract PR is needed.
2. **A test shows that `featurer_ved_kutt` can only return the model's feature columns, never label or arrival fields** (the "Boundary output" matrix row). It checks the returned keys against the artifact's `features` list for every row in `features.csv`, and that none of the forbidden names appear.
3. The spec is kept as one, above 1 600 tokens.
4. Every commit has `--author "Felipe Knudstad-Lopez <feknu2660@himolde.no>"`, story ID first in the message.

</frozen-after-approval>

## Code Map

- `app/prediksjon/__init__.py` -- `PrediksjonsInput` (8 fields, locked by `INPUTFELT` in the contract test), `lag_input` (H from `eta − naa`, `t_kutt = min(eta − H, naa)`), `velg_prediktor` (do not change). The only prediction module allowed to touch the data layer and the string `utdrag`.
- `app/prediksjon/baseline.py` -- `BaselinePrediktor`: the delegation target. It reads `data/baseline.json`.
- `app/prediksjon/features.py` -- pure feature functions (`grupper_sjeldne`, `ANNET`). The encoding goes here, or into a new pure module.
- `scripts/tren.py:151` `matrise`, `:173` `prediker`, `KATEGORISKE`, `HISTORIKK`, `TRENGRUPPE` -- the encoding to move. The final artifacts use `historikk="endelig"` (the `fartoy_*` columns).
- `scripts/evaluer.py` `modell_prediksjoner`, `i_modellutvalg`, `har_tilstand`, `er_f6`, `last_artefakter` -- the model arm and the sha/offset check to match. Load it with `importlib` in the test.
- `data/modell/modell_{6,24}t.joblib` -- keys `modell`, `features`, `kategorier`, `horisont`, `variant`, `offset_ovrige_min`, `features_sha256`, `config`.
- `data/utdrag/features.csv` -- `voyageid`, `horisont_timer`, `t_kutt_utc`, `har_tilstand`, `i_sonen_ved_kutt`, the feature columns.
- `tests/test_prediktor_kontrakt.py` -- `PREDIKTORER` (add `ModellPrediktor`), `INPUTFELT`, `_forbudte_referanser` (AST rule), `test_alle_prediktorer_er_i_kontrakten`.
- `app/__init__.py:20-40` -- the dashboard calls `lag_input` then `prediker`. Not changed here.
- `docs/arkitektur.md` §3 (line 91) -- update with how the features reach the model, and the delegation reasons.

## Tasks & Acceptance

**Execution:**
- [ ] `app/prediksjon/` -- move the feature encoding out of `scripts/tren.py` into a pure function; `tren.py` imports it. `tests/test_tren.py::test_committede_modeller` stays green, and the artifacts are not rewritten.
- [ ] `app/prediksjon/__init__.py` -- `featurer_ved_kutt(inp)` (Decision 1), with the `t_kutt` equality rule and the features-file sha.
- [ ] `app/prediksjon/modell.py` -- `ModellPrediktor` (`navn = "Modell v1"`, `kan_varsle = True`), artifacts loaded once, delegation, the artifact check.
- [ ] `tests/test_prediktor_kontrakt.py` -- add `ModellPrediktor` to `PREDIKTORER`.
- [ ] `tests/test_modellprediktor.py` -- one test per matrix row (including the boundary-output test, Decision 2), the equivalence with `evaluer.modell_prediksjoner` on validation rows, and that a row's prediction does not change when another row's features or ground truth change.
- [ ] `docs/arkitektur.md` §3, `docs/epics.md` -- the chosen feature path, E2-S07 ✅ and a changelog line.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then it is green in < 1 min, and the AST rule and `test_dataregresjon.py` are unchanged.
- Given the validation rows at their cut, when `ModellPrediktor` and `evaluer.modell_prediksjoner` predict them, then every `predikert_ankomst` and alert is identical.
- Given the default dashboard (`PREDIKTOR` unset), when it is opened, then it still shows the baseline (the swap is E2-S08).

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

The model arm in `evaluer.py` was written first, from the artifact, so that E2-S07 has a fixed reference. The equivalence test is what keeps "the model arm" to one definition. It runs on validation rows, so no model accuracy on the test period is looked at before the single test run in E2-S10.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `.venv/bin/pytest -q tests/test_prediktor_kontrakt.py tests/test_modellprediktor.py` -- expected: `ModellPrediktor` passes every contract test
- `git diff --quiet data/` -- expected: no change to the artifacts or extracts
