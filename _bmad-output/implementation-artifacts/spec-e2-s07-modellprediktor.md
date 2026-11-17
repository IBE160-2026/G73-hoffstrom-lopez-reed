---
title: 'E2-S07 — ModellPrediktor'
type: 'feature'
created: '2026-11-09'
status: 'done'
baseline_commit: '5898ff601b502a3eb9620c700714c9910e3fb335'
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
- [x] `app/prediksjon/` -- move the feature encoding out of `scripts/tren.py` into a pure function; `tren.py` imports it. `tests/test_tren.py::test_committede_modeller` stays green, and the artifacts are not rewritten.
- [x] `app/prediksjon/__init__.py` -- `featurer_ved_kutt(inp)` (Decision 1), with the `t_kutt` equality rule and the features-file sha.
- [x] `app/prediksjon/modell.py` -- `ModellPrediktor` (`navn = "Modell v1"`, `kan_varsle = True`), artifacts loaded once, delegation, the artifact check.
- [x] `tests/test_prediktor_kontrakt.py` -- add `ModellPrediktor` to `PREDIKTORER`.
- [x] `tests/test_modellprediktor.py` -- one test per matrix row (including the boundary-output test, Decision 2), the equivalence with `evaluer.modell_prediksjoner` on validation rows, and that a row's prediction does not change when another row's features or ground truth change.
- [x] `docs/arkitektur.md` §3, `docs/epics.md` -- the chosen feature path, E2-S07 ✅ and a changelog line.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then it is green in < 1 min, and the AST rule and `test_dataregresjon.py` are unchanged.
- Given the validation rows at their cut, when `ModellPrediktor` and `evaluer.modell_prediksjoner` predict them, then every `predikert_ankomst` and alert is identical.
- Given the default dashboard (`PREDIKTOR` unset), when it is opened, then it still shows the baseline (the swap is E2-S08).

## Implementation Notes

- The encoding lives in a new pure module `app/prediksjon/koding.py` (`FEATURES`, `KATEGORISKE`, `HISTORIKK`, `tall`, `matrise`), so `features.py` stays stdlib-only. `scripts/tren.py` imports and re-exports these names, so `tren.matrise`/`tren.FEATURES` (used by `evaluer.py`, `sammenlign_f6.py` and `test_tren.py`) are unchanged. Retraining into a scratch directory gave a byte-identical `modellvalg.json` and identical predictions for all four artifacts.
- `featurer_ved_kutt` returns typed values (float, category string, or None for an empty cell). `matrise` encodes them exactly as the CSV strings (`""`/None → NaN or `annet`).
- The boundary does not hand over `har_tilstand` (it is not an artifact feature). `ModellPrediktor` reads "no state" as F6 = None. `test_tilstand_er_lik_definert_f6` shows `har_tilstand == 1` ⇔ F6 is defined for every row of `features.csv`, so this matches `evaluer.har_tilstand`.
- `ModellPrediktor(modell_dir=MODELL_DIR)` takes an optional directory (used by the mismatch test). It also checks horizon, variant and that the artifact's feature list equals the boundary's.
- Delegated rows keep the baseline's `forklaring` (`metode: "kalibrert_baseline"`) plus `delegert`. Model rows carry `gruppe` too, which the contract test requires.

## Spec Change Log

## Review Triage Log

| # | Layer | Finding | Verdict | Evidence | Route |
|---|-------|---------|---------|----------|-------|
| 1 | verification-gap | No test sends a mixed 6 h/24 h batch with model rows; `self._artefakter[min(per_h)]` mutation survives | medium | pre-verified by mutation (17/17 green) | patch |
| 2 | verification-gap, blind | Horizon/variant and feature-list checks in `_sjekk` untested | medium | pre-verified by deleting both checks (17/17 green) | patch |
| 3 | edge-case, verification-gap | Artifact `historikk` key ignored; `evaluer` honours it | low | committed artifacts lack the key, but a `modellvalg` artifact would load silently and diverge from `evaluer` | patch |
| 4 | edge-case, blind | Missing artifact raises `FileNotFoundError`, not `ValueError`, so an E2-S08 fallback on `ValueError` misses it | medium | `_last_artefakter` raises `FileNotFoundError` | patch |
| 5 | blind | `test_modellrad` hardcodes offset 64.2 | low | recalibrating `baseline.json` breaks the test for an unrelated reason; direct fix | patch |
| 6 | blind | `passasjer`/`ingen_tilstand` delegation tested only at H = 6 | low | parametrize lists only h=6 for them; direct fix | patch |
| 7 | blind | `test_prediktormoduler_finnes` does not assert `modell.py`, `koding.py` are scanned by the AST rule | low | asserts only `{baseline.py, naiv.py}`; direct fix | patch |
| 8 | blind | Isolation test does not assert the changed row's prediction moved | low | only `featurer` compared; one assertion | patch |
| 9 | blind | `arkitektur.md` §5 `__init__.py` line omits `featurer_ved_kutt`, `features_sha256` | low | stale tree line; direct correction | patch |
| 10 | blind | `velg_prediktor` docstring says no model artifact exists | low | stale, but spec forbids touching `velg_prediktor` here | defer (E2-S08) |
| 11 | edge-case | Generator input is exhausted by the type loop | low | contract is `Sequence`; all callers pass lists; `BaselinePrediktor` has the same shape | reject |
| 12 | edge-case | Hand-built naive `t_kutt` silently delegates | low | only `lag_input` builds inputs and it normalises to UTC | reject |
| 13 | edge-case | Duplicate `(voyageid, H)` in `features.csv` | low | not reachable with the committed, validated extract | reject |
| 14 | edge-case | Artifact without `modell`/`kategorier` key fails at predict time | low | committed artifacts have both; needs extra guards | reject |
| 15 | blind | `epics.md` story body says "merkes med metoden" | false | delegated rows do carry `metode` (`kalibrert_baseline`) plus `delegert` | reject |
| 16 | blind | Narrower artifact check than `evaluer.last_artefakter` | false | spec sets the check to `features_sha256` + offset; the predictor reads neither `anlop.csv` nor anything else `baseline_sha256` guards beyond the offset, which is compared by value | reject |
| 17 | blind | Served feature values never checked against raw CSV | false | `test_lik_modellarmen_i_evaluer` compares with `evaluer`, which encodes the raw strings; a parsing bug changes predictions | reject |
| 18 | blind | Non-Øvrige groups all labelled `passasjer` | false | `BaselinePrediktor.prediker` runs first and raises `KeyError` on an unknown group | reject |
| 19 | blind | Contract test does not check alert type for `kan_varsle = True` | low | model returns `bool` by construction; contract change is out of proportion | reject |
| 20 | blind | Equivalence test does not assert horizon | false | `evaluer.baseline_prediksjoner` raises on a horizon mismatch | reject |
| 21 | blind | Retrain claim and `--author` not evidenced in diff | low | process claims; the fix would edit this spec | reject |
| 22 | blind | F15–F16 leakage checked only by column name | false | pre-existing E2-S04 guarantee, tested in `tests/test_features.py` | reject |
| 23 | blind | Unbounded caches, shared mutable artifact dicts | low | nothing mutates them; fix adds complexity | reject |
| 24 | mutation check | `avvik_min > VARSEL_MIN` → `>= VARSEL_MIN + 1` survived: no validation row predicts 120–121 min | medium | 1 of 17 mutants survived | patch: `test_varselterskelen_er_strengt_over_120` with a stub model; rerun 18/18 killed |

## Design Notes

The model arm in `evaluer.py` was written first, from the artifact, so that E2-S07 has a fixed reference. The equivalence test is what keeps "the model arm" to one definition. It runs on validation rows, so no model accuracy on the test period is looked at before the single test run in E2-S10.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `.venv/bin/pytest -q tests/test_prediktor_kontrakt.py tests/test_modellprediktor.py` -- expected: `ModellPrediktor` passes every contract test
- `git diff --quiet data/` -- expected: no change to the artifacts or extracts
