---
title: 'E2-S10 — Resultatnotat'
type: 'feature'
created: '2026-11-13'
status: 'in-progress'
baseline_commit: '503454cbe1f36d08781ad0748fab169033727f90'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/brief.md'
  - '{project-root}/docs/beslutninger/11-modellvalg-ovrige-og-features.md'
  - '{project-root}/docs/beslutninger/12-modellen-bare-utenfor-sonen.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The model and the evaluation are finished (E2-S05–S09), but the test period has never been scored with the model. The brief's table still says "filled in E2-S10", and there is no results note. Epic E2 is done only when the dashboard shows the model by default and `docs/resultater.md` is written.

**Approach:** Lock everything first. Then run `scripts/evaluer.py --test` exactly once, on a pushed, clean commit whose full hash is written into `metrikker.json`. Write `docs/resultater.md` from the numbers that run produced, with nothing tuned and nothing rerun. The run itself sets `testkjoringer = 1`, and that makes the dashboard show the model by default (E2-S08).

## Requirements (Felipe, 2026-11-13, at story start)

1. **Gate before the test run:** all tests green (`.venv/bin/pytest -q`), the working tree clean, and everything pushed (HEAD equals `@{u}`). `metrikker.json` records the full hash of the commit the test run builds on.
2. **Success criteria are copied verbatim** from the brief into this spec before the run (section below). That documents what counted as passing before the numbers were known.
3. **The test run is made once.** Afterwards nothing changes in the model, the configuration, the selection rules or the criteria. If an error is found, it is reported in the results note next to the numbers, not fixed and rerun.
4. **The results note shows:**
   - the model subset and all Øvrige traffic side by side
   - validation and test side by side
   - the ablation without F13–F14
   - the limitations:
     - fewer than half of the delays can be alerted
     - the label for trips inside the port area (F6, decision 03)
     - the test period is the winter half-year (14.09.2025–15.03.2026)

Also from `docs/epics.md` E2-S10: the number of test runs, coverage at the cut, AIS gaps, A1 (reported ETA at `t_H`), departure port and ETD, whether the goals were met, a negative result reported as such, and a README mention of the model.

## Success Criteria (verbatim from `docs/brief.md`, blob `6f3d90d7cc801798862ceb377f07b25f25739952`, at commit `503454cbe1f36d08781ad0748fab169033727f90`)

The Norwegian version `docs/brief.no.md` is pinned at the same commit, blob `c9e4dfe982c7a99a4b44d5a4bee83faa9f6c1cfe`. Pass/fail is read from the text below. It is not reinterpreted after the run.

**Functional — metric structure.** Real pipeline work building the ground-truth dataset (deriving actual arrival from AIS tracks on the full 8,094-voyage, 27-month dataset — see addendum) showed the deviation distribution is tail-heavy: most calls land close to their reported ETA, a minority miss by hours, and a single error metric that averages across both groups misleads. Mean absolute error is unstable on this shape — it can look dramatically worse than the typical case actually is, because a handful of extreme voyages dominate the mean. The metric structure is therefore:
- **Primary: share of predictions within ±30 minutes of actual arrival.** The number a havnevakt would actually trust or not.
- **Secondary: precision and recall on flagging arrivals that deviate more than 2 hours** ("er_forsinket") — a disruption-detection framing, evaluated once a trained model exists (the reported ETA alone predicts zero deviation by definition, so it cannot meaningfully be scored against this flag).
- **Support stats only, never the headline:** MAE and median absolute error, reported for transparency but not used as the pass/fail criterion.

**Scoped to non-scheduled traffic alone.** The headline result is reported on non-scheduled (ikke-rutegående) traffic only, with scheduled/liner traffic (Passasjer) kept as a control group, not pooled into the main number. Reason, confirmed on the full dataset: the calibrated baseline already puts scheduled traffic at 79.6% within ±30 minutes, up from a naive 7.4% — that traffic is close to solved by a constant offset alone. Training and reporting against the pooled dataset would let a model largely learn to recognize which voyages are ferries rather than learn to predict genuine arrival uncertainty, and the headline number would be inflated by the easy half of the fleet. Non-scheduled traffic is where the real problem — and the product's value — actually lives.

**The number to beat:** on all non-scheduled traffic, the calibrated reported-ETA baseline reaches **46.6% within ±30 minutes** (up from a naive 12.8%), and **19.5% of arrivals still arrive more than 2 hours later than it** even after calibration (signed delay — exactly what the `er_forsinket` flag measures) — calibration corrects the typical case, not the disruptive tail (MAE for this group barely moves, 155→136 minutes). Since decision 12 the model is used only on non-scheduled voyages that have an AIS position at the cut and are outside the arrival zone (the **model subset**); every other voyage is delegated to the baseline. Model and baseline are therefore always compared on the same voyages, and **pass/fail is decided on the model subset**. 46.6% stays as the baseline for all non-scheduled traffic; **the number the model must beat is the calibrated baseline on the model subset: 59.1% within ±30 minutes at 6 h and 56.3% at 24 h.** On flagging, the model must reach a higher F1 than the "flag everyone" rule on the model subset (the baseline cannot flag anything by construction). **This alert bar is lower than before:** on the test period the delayed base rate in the model subset is 7.8% (57/733) at 6 h and 10.5% (78/742) at 24 h, which gives "flag everyone" F1 ≈ 0.14 and 0.19, against 19.5% (194/996) and F1 ≈ 0.33 on all non-scheduled traffic. The reason is that most delayed non-scheduled voyages fall outside the model subset — 137 of 194 (70.6%) at 6 h and 116 of 194 (59.8%) at 24 h — and they are mostly voyages already inside the arrival zone at the cut (F6), whose label does not measure an arrival (decision 03); they go to the baseline, which cannot flag. The bar was moved after the validation results were known (E2-S05, decision 12), and the alert numbers for all non-scheduled traffic stand in the same table below. If the model does not clear one or both bars, that is reported as a result, not omitted — an honest negative finding is more useful here than a quiet redefinition of success after the fact.

Both rows are reported side by side, per horizon (6 h / 24 h), on the test period:

| Row | Test voyages with ground truth | Model share (of non-scheduled voyages with ground truth) | Baseline, ±30 min | Model, ±30 min | Delayed base rate | "Flag everyone" F1 | Model F1 |
|---|---|---|---|---|---|---|---|
| **Model subset** (pass/fail) | 733 / 742 | 73.6% / 74.5% | 59.1% (433/733) / 56.3% (418/742) | filled in E2-S10 | 7.8% (57/733) / 10.5% (78/742) | 0.14 / 0.19 | filled in E2-S10 |
| **All non-scheduled traffic, with delegation** | 996 / 996 | 73.6% / 74.5% | 46.6% (464/996) / 46.6% (464/996) | filled in E2-S10 | 19.5% (194/996) / 19.5% (194/996) | 0.33 / 0.33 | filled in E2-S10 |

The model share is the share of non-scheduled test voyages with ground truth that the model is actually used on; the rest get the baseline in the model column too. The baseline cells come from a baseline-only run (`scripts/evaluer.py --bare-baseline`, `data/modell/metrikker.json`), which does not use the model.

**The alert can reach fewer than half of the delayed voyages, however good the model is.** Of the 194 delayed non-scheduled voyages in the test period, only 57 (6 h) and 78 (24 h) are in the model subset. The rest are trips inside the arrival zone at the cut (F6: 107 and 92) or voyages with no AIS position at the cut (30 and 24). They get the baseline, which cannot alert. The alert columns in the table above therefore apply only to the model subset, and the F1 for all traffic shows what that costs.

The reported-ETA baseline itself is scored the same way, calibrated per vessel-traffic type (scheduled/liner vs. other) rather than compared naively — see the addendum's method notes on why zone-entry-based ground truth needs this calibration to be comparable to ETA at all. The Hong Kong precedent (52.98% MAE reduction vs. self-reported ETA) remains a useful aspirational reference for what "good" looks like with this method, not a number to adopt directly.

**Data quality.** AIS coverage is logged as an explicit metric; voyages where actual arrival cannot be derived are dropped and counted, not silently interpolated (full contingency plan and coverage numbers in the addendum).

**Product.** The havnevakt can read a daily brief and understand, without asking anyone, which of tomorrow's expected arrivals to distrust and why.

## Boundaries & Constraints

**Always:**
- **Test rows:** model predictions on test rows are made only by the single `evaluer.py --test` run. Every later use (note, panel, tests) reads the `test` block from `metrikker.json`. Anything beyond this and Decision 3 requires stopping and asking Felipe.
- The guard and the hash live in `evaluer.py` and run before anything is predicted. `--test` stops with "ingenting er skrevet" if the tree is dirty, HEAD ≠ `@{u}`, or git is unavailable. The run stores `commit` (full `git rev-parse HEAD`) in its `testkjoringer_logg` entry and in `test.kilder`.
- Every number in the note's tables is rendered from `metrikker.json` by one function. A test checks that the committed note contains those tables verbatim.
- Validation and test are labelled as different fits (S06 Decision 4): validation uses refits on train only, and test uses the committed final artifacts.

**Never:**
- `--ny-testkjoring`, a second `--test`, or `--test` inside pytest.
- After the run, any change to `data/modell/*.joblib`, `modellvalg.json`, `features.csv`, `scripts/tren.py`, `scripts/evaluer.py`, `app/prediksjon/`, the 120 min / ±30 min thresholds, or the success criteria.
- Rounding or wording that turns a loss into "almost" or "on par". The verdict uses the brief's comparisons on the raw values.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Gate passes | clean, pushed, `testkjoringer = 0` | `test` block written, `testkjoringer = 1`, log `{nr, dato, commit}` | N/A |
| Dirty tree / not pushed / no git | any | nothing predicted, nothing written | exit 2 with reason |
| Already run | `testkjoringer ≥ 1` | refused, as today | exit 2 |
| Model loses | test numbers | "ikke bestått" stated with the same weight as a pass | N/A |
| Error found after the run | any | reported in the note with the numbers, nothing rerun | N/A |

## Decisions (Felipe, 2026-11-13, at approval)

1. **Real-file tests pinned to a validation view (1A).** Before the run, the tests that assume `testkjoringer == 0` in the real `metrikker.json` read a view built from the real file, with `testkjoringer` set to 0 and `test` removed. The tests are then green both before and after the run, and no test changes after it.
2. **Brief cells filled in (2A).** After the run, only the cells marked "filled in E2-S10" in `docs/brief.md` and `docs/brief.no.md` are filled, with a dated changelog line. The criteria text stays untouched.
3. **Test rows after the run (3A).** These uses are allowed:
   - `auto` shows the model on test windows, as E2-S08 designed
   - one manual look at the standard window
   - the screenshots in `docs/ux/skjermbilder/` may be retaken, so README shows the model. That changes no numbers.
4. **A run that fails while predicting (4A).** Stop and ask Felipe. No rerun without approval, and the note reports it either way.
5. **The spec length is approved as it is** (~4 100 tokens, ~1 600 of them the verbatim criteria).
6. **Checkpoint before the run (Felipe).** When everything is implemented and the tests are green, stop and show Felipe a checklist:
   - the commit hash
   - a clean working tree
   - pushed (HEAD = `@{u}`)
   - the criteria in the spec
   - the exact command

   `evaluer.py --test` starts only when Felipe says yes.
7. Every commit has `--author "Felipe Knudstad-Lopez <feknu2660@himolde.no>"`, story ID first. The session is logged under Felipe in `.logs/`.

</frozen-after-approval>

## Code Map

- `scripts/evaluer.py` -- `main` (lines ~356–404): the `--test` path calls `oppdater(gammel, "test", {}, "sjekk", …)` as a pre-check before predicting. The git guard goes next to it. `oppdater` (~299) builds the log entry, so add `commit` there. `skriv_tabell` prints the console table. Do not touch the scoring.
- `data/modell/metrikker.json` -- `testkjoringer = 0`, `testkjoringer_logg = []`, the `validering` block and `test_bare_baseline` (brief baseline cells: 433/733, 418/742, 464/996). `oppdater` replaces only the `test` key.
- `tests/test_evaluer.py` -- `oppdater` tests at ~179–198 (log shape `{nr, dato}` → add `commit`). Never runs `--test` on real data.
- `tests/conftest.py` -- the autouse `testkjoringer = 0` stub and the guard against model use on test rows stay unchanged.
- `tests/test_panel.py:28`, `tests/test_ruter.py:650,726,805,816` -- real-file tests that assume 0 runs (Decision 1).
- `app/panel.py` -- shows the `test` block and the verdict automatically once `testkjoringer ≥ 1`. No change needed.
- `app/prediksjon/__init__.py:196` -- the lock. Unchanged: `testkjoringer ≥ 1` makes `auto` pick the model.
- `data/utdrag/ais_kutt_dekning.csv`, `metrikker.json` `antall` -- coverage at the cut. Take the note's numbers from `metrikker.json`.
- `docs/brief.md` / `docs/brief.no.md` lines 44–71 -- the criteria and the table (Decision 2).
- `README.md:81–83` -- the model paragraph, written for "before the test run".
- `docs/epics.md` E2-S10, and the E2 "Ferdig når" line -- ✅ and changelog.

## Tasks & Acceptance

**Before the run** (commit A, `E2-S10: …`):
- [x] `scripts/evaluer.py` -- git guard (clean, HEAD = `@{u}`) before predicting, plus `commit` in the log entry and in `test.kilder`. Git is called through a function the tests can replace. -- Requirement 1
- [x] `tests/test_evaluer.py` -- dirty, unpushed and no-git cases are refused with nothing written; the log has `commit`. Synthetic only. -- matrix
- [x] `scripts/resultattabeller.py` + `tests/test_resultattabeller.py` -- render the note's tables from `metrikker.json` (synthetic fixture). The tables:
  - model subset vs. all Øvrige
  - validation vs. test
  - ablation
  - coverage
  - verdict per horizon

  `tests/test_resultater.py::test_notat_lik_metrikker` is skipped while `testkjoringer == 0`. -- Requirement 4
- [x] `tests/test_panel.py`, `tests/test_ruter.py` -- the real-file tests read the validation view (Decision 1).
- [ ] **Gate:** pytest green, `git status --porcelain` empty, push, HEAD = `@{u}`. Log the output in Implementation Notes. **Then stop at the checkpoint (Decision 6).**

**The run (once):** `.venv/bin/python scripts/evaluer.py --test`. Save the console output in Implementation Notes.

**After the run** (commit B):
- [ ] `data/modell/metrikker.json` -- as written by the run, untouched.
- [ ] `docs/resultater.md` -- the rendered tables, plus text covering every item in Requirement 4 and the epics list. The verdict uses the verbatim criteria.
- [ ] `README.md`, `docs/epics.md` (E2-S10 ✅, E2 done), the brief cells (Decision 2), and the screenshots (Decision 3).

**Acceptance Criteria:**
- Given commit B, when `git log` is read, then the hash in `metrikker.json` `testkjoringer_logg[0].commit` is an ancestor of B, and no file in the "Never" list differs between that hash and B.
- Given `docs/resultater.md`, when `test_notat_lik_metrikker` runs, then every table equals the render from `metrikker.json`.
- Given `PREDIKTOR` unset after the run, when `/` opens on the standard window, then the strip shows «Modell v1» and the panel shows the test block with its verdict.

## Implementation Notes

**Before the run (commit A, 2026-11-13):**
- `scripts/evaluer.py`: `git(*args)` (replaceable in tests) and `sjekk_git()` run first in the `--test` path, before artifacts are loaded or anything is predicted. Dirty tree (untracked files included), HEAD ≠ `@{u}`, no upstream or no git → `Avvik` → "Stopper, ingenting er skrevet: …", exit 2. `oppdater(..., commit=)` requires `commit` for `test` and logs `{nr, dato, commit}`; `test.kilder.commit` is the same full hash. Scoring untouched.
- `tests/test_evaluer.py`: refusal cases (modified, untracked, not pushed, no git, no upstream) and "already run" call `main(["--test", …])` on the synthetic fixture with `git` and every predicting function replaced by one that fails, so nothing is predicted; the file is byte-identical afterwards. No test reaches the scoring under `--test`. Validation and `--bare-baseline` never call git.
- `scripts/resultattabeller.py`: `render(data)` → 7 markdown tables (testkjøringer, hovedtabell in the brief's shape, dom, validering mot test, ablasjon, støttetall incl. Passasjer control, dekning). Refuses (`Mangler`) without a test run. The verdict compares raw values with strict `>`; shown decimals grow until unequal values look unequal. CLI prints the tables for pasting into `docs/resultater.md`.
- `tests/test_resultattabeller.py` (synthetic), `tests/test_resultater.py` (real file; both tests skip while `testkjoringer == 0`; also checks the log commit is a full hash equal to `test.kilder.commit`).
- Decision 1A: `valideringsvisning` fixture in `tests/conftest.py` (real file, `testkjoringer = 0`, empty log, no `test`). Used by `test_panel.py::test_ekte_fil_gir_valideringsblokken` and the four real-file panel tests in `test_ruter.py`.
- Shape check (not committed): `render` on the real file with `test` set to a copy of `validering` reproduces the panel's validation numbers (69,1 % / 59,8 %). No test rows were touched.
- Gate output is recorded in the hand-off report and goes into these notes in commit B (writing it here before the run would dirty the tree).

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- all green, < 1 min, both before and after the run
- `git diff --stat <run-commit> HEAD -- data/modell/*.joblib data/modell/modellvalg.json data/utdrag/features.csv scripts/tren.py scripts/evaluer.py app/prediksjon` -- empty
- `.venv/bin/python -c "import json;print(json.load(open('data/modell/metrikker.json'))['testkjoringer'])"` -- `1`
