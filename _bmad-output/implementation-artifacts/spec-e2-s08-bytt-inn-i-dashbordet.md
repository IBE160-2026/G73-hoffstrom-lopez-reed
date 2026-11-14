---
title: 'E2-S08 — Bytt inn i dashbordet'
type: 'feature'
created: '2026-11-10'
status: 'done'
baseline_commit: '0b2933910ecb212e4c67194226827340956fd8f7'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/ux/dashbord.md'
  - '{project-root}/docs/beslutninger/12-modellen-bare-utenfor-sonen.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `ModellPrediktor` (E2-S07) exists, but `velg_prediktor` always returns the baseline, so the dashboard can never show the model or an alert (FR3, FR9).

**Approach:** `velg_prediktor` returns `ModellPrediktor` only when the test-period lock allows it (Decision 1), and falls back to the baseline with a message when `ModellPrediktor()` raises. The main screen shows "Modell v1" in the predictor strip and fills the Varsel column from `forventet_forsinket` and `forklaring["delegert"]`. Templates change only in the strip and the Varsel column (the A5 test).

## Boundaries & Constraints

**Always:**
- **Test rows (Felipe, 2026-11-10):** test-period rows are used only for what this spec states explicitly. Anything else, including prediction without ground truth, means stop and ask first. Model accuracy on the test period stays locked until E2-S10. Every route test that renders model rows uses a `STANDARD_NAA` inside the validation part (the last 20 % of `train`, chronological), never the test period.
- **Fallback:** if `ModellPrediktor()` raises `ValueError` (missing or mismatched artifact), `velg_prediktor` returns `BaselinePrediktor`, and the strip says «Modell ikke funnet — viser kalibrert baseline» (UX §5). The app never fails to start because of the model.
- **Alert column:** `True` → ▲ + «VARSEL» (icon + text, never colour alone, UU3). `False` → «–» with screen-reader text «Ingen varsel». `None` → «–» plus the delegation reason as visible text. Baseline rows keep today's text («baselinen varsler ikke»).
- The baseline-only note in the strip («Baselinen kan ikke varsle avvik …») shows only when `kan_varsle` is False. With the model, the strip states the coverage limit (only calls outside the arrival zone with AIS position at the cut; under half of the delayed calls, 57 and 78 of 194).
- Existing route tests that check baseline values (order, times, strip) pin `PREDIKTOR=baseline`; their expectations do not change.
- `pytest` stays green without network and without `pipeline/data/`, in < 1 min.

**Never:**
- Score the model on the test period, show model-vs-truth on test rows, or record model predictions for test rows in tests or by hand.
- Change `PrediksjonsInput`, `ModellPrediktor`, the artifacts, `metrikker.json` or the data layer.
- Add the panel (E2-S09) or the results note (E2-S10).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Auto, before test run | `PREDIKTOR` unset/`auto`, `testkjoringer = 0`, any window | baseline, today's screen | N/A |
| Model, pre-test window | `PREDIKTOR=modell`, `testkjoringer = 0`, window ends on or before the test-period start (training or validation) | strip «Modell v1» + in-sample text (Decision 5), alert column filled | N/A |
| Model, test window, locked | `PREDIKTOR=modell`, `testkjoringer = 0`, window ends after the test-period start (incl. the default 08.10.2025 and a window straddling the boundary) | baseline + lock text in the strip | N/A |
| After test run | `testkjoringer ≥ 1`, `PREDIKTOR` `auto` or `modell`, any window | strip «Modell v1» | N/A |
| Explicit baseline | `PREDIKTOR=baseline` | today's screen, unchanged | N/A |
| Model row with alert | validation window, `forventet_forsinket=True` | ▲ + «VARSEL» | N/A |
| Model row, no alert | `forventet_forsinket=False` | «–», screen reader «Ingen varsel» | N/A |
| Delegated row | `delegert` = `passasjer` / `ingen_tilstand` / `i_sonen_ved_kutt` / `ingen_featurerad` | «–» + reason text (Decision 3) | N/A |
| Missing artifact | `PREDIKTOR=modell`, empty model dir, validation window | baseline + «Modell ikke funnet — viser kalibrert baseline» | `ValueError` caught in `velg_prediktor` |
| Unknown value | `PREDIKTOR=tull` | — | `ValueError`, as today |

## Decisions (Felipe, 2026-11-10, at approval)

1. **Lock gate (1A plus an addition).**
   - Until `data/modell/metrikker.json` has `testkjoringer ≥ 1` (missing file or key counts as 0), `auto` returns the baseline.
   - In the same period, `PREDIKTOR=modell` shows the model only for windows before the test period, in training or validation (see the correction below). A window counts as test period when its end (`naa + 24 h`) is after the earliest reported ETA in the `test` split. A call with no `naa` counts as test period too.
   - Otherwise `PREDIKTOR=modell` falls back to the baseline, and the strip says why: «Modellen vises ikke for testperioden før den ene testkjøringen (E2-S10) — viser kalibrert baseline».
   - After the test run, `auto` and `modell` both pick the model.
   - **Correction (Felipe, 2026-11-10, after review):** Felipe's first wording, «Modellen kan bare vises for vinduer i valideringsperioden», was wrong. Only the test period is locked, and windows in the training part show the model too. The final model is fitted on training + validation (`scripts/tren.py:22`), so both parts are in-sample. A lower bound at the start of validation would protect nothing.
   - A test shows that `PREDIKTOR=modell` gives the baseline and the lock text for the default window, and for a window that straddles the boundary, while `testkjoringer = 0`.
2. **Prediksjonsfeil and `test_fasit_uavhengig_av_prediktor` are deferred (2A)** to E1-S09, after E2-S10. They are recorded in `deferred-work.md`.
3. **Delegation texts (3, with one change):**
   - `passasjer` → «– (rutegående: bare baseline)»
   - `ingen_tilstand` → «– (ingen AIS-tilstand)»
   - `i_sonen_ved_kutt` → «– (allerede i havneområdet)»: «ankomstsone» is the group's internal term.
   - `ingen_featurerad` → «– (ingen modelldata ved kuttet)»
4. The spec is kept as one, above 1 600 tokens. Every commit has `--author "Felipe Knudstad-Lopez <feknu2660@himolde.no>"`, story ID first.
5. **In-sample text (2A, extended):** whenever the model is shown for a window before the test period, the strip says «Modellen er trent på disse anløpene, så treffene ser bedre ut enn de er. Ekte resultater finnes først for testperioden.» This holds for training and validation windows alike. After the test run, the text is not shown for test-period windows.

6. **Two barriers that must each hold on their own (Felipe, 2026-11-11):** the lock in `velg_prediktor` and the test-row guard in `tests/conftest.py` are separate safeguards. Neither may rely on the other. `test_laasen_alene_stopper_modellen_paa_testvindu` replaces the guard with a spy that never runs the real model, and shows that the lock alone gives the baseline for the default (test-period) window. The guard stops `ModellPrediktor.prediker` on test-period rows even if the lock breaks.
7. **Baseline strip wording (Felipe, 2026-11-11):** the baseline strip also says «havneområdet», not «ankomstsonen».

</frozen-after-approval>

## Code Map

- `app/prediksjon/__init__.py` `velg_prediktor` -- today always the baseline. It needs the window (`naa`) for the lock, through an optional argument; `app/__init__.py:26` passes it. This module is the one prediction module allowed to touch `app.data`, so the earliest test-period ETA is read here. Import `ModellPrediktor` lazily inside the function, and catch `ValueError` for the fallback. The docstring is stale (deferred from E2-S07): fix it.
- `app/prediksjon/modell.py` -- `ModellPrediktor()` raises `ValueError` on a missing or mismatched artifact. The artifacts are cached (`lru_cache`), so a call per request is cheap. Do not change.
- `app/__init__.py` `_rader`, `forside`, `PREDIKTOR_BESKRIVELSE` -- add `varsel` and the reason text per row from `Prediksjon`, a description for «Modell v1», and a fallback flag for the strip. Rows are built only from `PrediksjonsInput` + `Prediksjon` (no ground truth).
- `app/templates/forside.html` -- the strip (`kan_varsle` block) and the `Varsel` cell, nothing else. The footnote «"–" i Varsel: baselinen varsler ikke» depends on the predictor.
- `app/static/style.css` -- `--varsel` for ▲ «VARSEL», if not already styled (reuse it; E1-S09 is planned to use the same token).
- `tests/test_ruter.py` -- the baseline expectations stay as they are; pin `PREDIKTOR=baseline` with `monkeypatch`. New tests: `test_modell_i_valideringsvindu`, `test_laas_testperioden` (Decision 1, including the boundary window and `testkjoringer` 0 vs 1 through a patched path or `monkeypatch`, never by editing the real `metrikker.json`), `test_fallback_baseline`, and the alert-column tests on a validation-period `STANDARD_NAA`.
- `tests/test_baseline.py:104` `test_velg_prediktor_gir_baseline` and `tests/test_modellprediktor.py:279` `test_dashbordet_bruker_fortsatt_baselinen` -- they assert that every value gives the baseline. Update them to the decided behaviour.
- `tests/conftest.py` -- the `app`/`client` fixtures. A validation-window client fixture goes here.
- `data/modell/metrikker.json` -- `testkjoringer` is 0 today. Read it only.
- `docs/ux/dashbord.md` §5, `docs/arkitektur.md` §3, `docs/epics.md`, `README.md` -- update the docs and set E2-S08 ✅.

## Tasks & Acceptance

**Execution:**
- [x] `app/prediksjon/__init__.py` -- `velg_prediktor` with the lock gate (Decision 1) and the fallback -- FR9
- [x] `app/__init__.py`, `app/templates/forside.html` -- the strip and the Varsel column per the matrix -- FR3, UU3
- [x] `tests/test_ruter.py`, `tests/conftest.py`, `tests/test_baseline.py`, `tests/test_modellprediktor.py` -- one test per matrix row, model rows only in a validation window -- NFR2
- [x] `docs/ux/dashbord.md`, `docs/arkitektur.md`, `docs/epics.md`, `README.md` -- the new states, E2-S08 ✅, changelog -- traceability

**Acceptance Criteria:**
- Given `PREDIKTOR=baseline`, when `/` opens, then every existing `test_ruter.py` assertion still holds.
- Given any `PREDIKTOR` value, when the test suite runs, then no test renders model rows for a test-period window.
- Given a validation window with the model, when `/` opens, then the template diff against baseline touches only the strip and the Varsel cell.

## Implementation Notes

- `velg_prediktor_med_merknad(verdi, naa)` returns the predictor plus the strip note; `velg_prediktor` wraps it. `VINDU_TIMER` lives in `app.prediksjon` only.
- `tests/conftest.py` has two autouse fixtures: `testkjoringer = 0` from a separate tmp dir, and a guard that fails before `ModellPrediktor.prediker` runs on any input with a reported ETA in the test period (not applied to the contract and model-predictor tests).
- Mutation check (2026-11-11): 25 of 25 mutants killed across the lock, the fallback, `testkjoringer()`, the in-sample text and the Varsel cell.
- The routes test the model only for 15.06.2024 and 15.08.2025 (pre-test windows) and for the empty test window 03.02.2026.

## Spec Change Log

## Review Triage Log

| # | Layer | Finding | Verdict | Evidence | Route |
|---|-------|---------|---------|----------|-------|
| 1 | blind | Lock lets training windows show the model, against «bare valideringsperioden» | intent_gap | Felipe 2026-11-10: his first wording was wrong; both parts are in-sample; only the test period is locked (Decision 1 correction, Decision 5 adds the in-sample text) | resolved by human |
| 2 | blind, edge-case | `testperiode_start()` can raise (no test rows, unreadable extract), giving HTTP 500 | medium | bare `min()` over `last_utdrag()` with no guard; spec says the app never fails because of the model | patch |
| 3 | edge-case, verification-gap | Only `ValueError` from `ModellPrediktor()` is caught; corrupt `.joblib` gives HTTP 500 | medium | `_last_artefakter` raises other types on unpickling/import errors | patch |
| 4 | edge-case | `VINDU_TIMER` defined twice (`app/__init__.py`, `app/prediksjon/__init__.py`) | medium | if they diverge, the lock checks a shorter window than the one rendered, and the model runs on test rows | patch |
| 5 | blind, edge-case | Tests depend on the real `metrikker.json` having `testkjoringer = 0` | medium | six tests change meaning when E2-S10 raises the counter | patch |
| 6 | blind, verification-gap, orchestrator | Nothing in the suite enforces "no model on test rows"; lock tests would predict test rows if the lock broke | medium | the lock tests render the default window with `PREDIKTOR=modell`; a spy that fails before predicting makes the rule a check and the mutation check safe | patch |
| 7 | verification-gap | `testkjoringer()` bool and non-object branches untested | low | pre-verified; `true` would unlock the lock; direct test cases | patch |
| 8 | blind, edge-case | Unknown/missing delegation code renders "Ingen varsel" | low | template `else` branch; direct text change plus a key-set test | patch |
| 9 | blind | Delegated rows give screen readers no "Ingen varsel" context | low | the "–" is `aria-hidden`; only the reason is read; direct fix (UU4) | patch |
| 10 | blind | `docs/epics.md` E2-S08 old bullets contradict the lock | low | "`PREDIKTOR=auto` velger modellen når artefaktet finnes", Prediksjonsfeil still listed | patch |
| 11 | blind | `docs/arkitektur.md` §3 leakage bullet says only `lag_input` touches `app.data` | low | `featurer_ved_kutt` and `testperiode_start` do too | patch |
| 12 | blind | UX §6 UU1 row says `--varsel` is not built | low | `style.css` now defines it | patch |
| 13 | blind | README describes `PREDIKTOR=modell` but the UI can only reach the locked default window | low | no `naa` form yet (E1-S07) | patch |
| 14 | blind | Footnote hardcodes "2 timer" | false | `VARSEL_MIN = 120` and the deviation is relative to calibrated baseline, as the footnote says | reject |
| 15 | blind | Story ✅ while spec is `in-review` | false | the spec is closed in step 5 of the same story | reject |
| 16 | blind | Fallback strip shows baseline text «Varselkolonnen fylles når modellen kommer» next to the note | low | slightly odd, but true; fix adds branching in the strip | reject |
| 17 | blind | `testkjoringer` counter is editable by anyone | low | the lock guards against accidental viewing, not deliberate edits; `evaluer.py` is the only writer | reject |
| 18 | edge-case | `prediker()` errors at request time give HTTP 500 | low | not shown reachable with the committed `features.csv` | reject |
| 19 | edge-case | Naive `naa` raises only on the `modell` path | low | `STANDARD_NAA` is tz-aware; config is code | reject |
| 20 | edge-case | Footnote changes too, beyond strip and Varsel (A5 claim) | false | the footnote explains the Varsel column; Code Map named it | reject |
| 21 | orchestrator (full suite) | The autouse `metrikker.json` fixture wrote into each test's `tmp_path`, so two `test_fetch_ais_kutt.py` tests that expect an empty `tmp_path` failed | medium | the patch agent ran only the files it edited; the full suite gave 2 failed | patch: separate dir from `tmp_path_factory` |
| 22 | mutation check | `except Exception` → `except ValueError` in `i_testperioden` survived | medium | the test raised only `ValueError`; an unreadable extract (`OSError`) would give HTTP 500 | patch: parametrize with `OSError`; 24 of 25 mutants killed; the lock-off mutant was stopped by the test-row guard before the model ran |
| 23 | mutation check | `i_utvalg` without `kan_varsle` survived | low | equivalent while the template checked `kan_varsle` a second time; two places held the same rule | patch (2026-11-11): the in-sample text moved out of the `kan_varsle` branch, so the rule lives only in `app/__init__.py`; the mutant is now killed by `test_i_utvalg_ikke_med_baselinen` |
| 24 | Felipe (2026-11-11) | Lock-off mutants were killed by the guard, not by the lock tests | medium | the lock tests failed on the guard's AssertionError before their own assertions | patch: `test_laasen_alene_stopper_modellen_paa_testvindu` (guard replaced by a spy); the three lock-off mutants are killed by it with the guard out of play; full rerun 25 of 25 killed |

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `git diff --quiet data/` -- expected: no change
