---
title: 'E2-S10 — Resultatnotat'
type: 'feature'
created: '2026-11-13'
status: 'done'
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
- [x] **Gate:** pytest green, `git status --porcelain` empty, push, HEAD = `@{u}`. Log the output in Implementation Notes. **Then stop at the checkpoint (Decision 6).**

**The run (once):** `.venv/bin/python scripts/evaluer.py --test`. Save the console output in Implementation Notes.

**After the run** (commit B):
- [x] `data/modell/metrikker.json` -- as written by the run, untouched.
- [x] `docs/resultater.md` -- the rendered tables, plus text covering every item in Requirement 4 and the epics list. The verdict uses the verbatim criteria.
- [x] `README.md`, `docs/epics.md` (E2-S10 ✅, E2 done), the brief cells (Decision 2), and the screenshots (Decision 3).

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
- After review (2026-11-13): `sjekk_git` runs `git fetch --quiet` before reading `@{u}`; `--test` refuses unless `--features/--anlop/--modell-dir/--ut` equal the `STANDARD` paths; the successful `--test` path is tested with git, `last_artefakter` and `evaluer` replaced (commit in log and `test.kilder`); the main-table row reads «(avgjør bestått/ikke bestått)»; the table CLI also catches `KeyError/TypeError/AttributeError`; `test_resultater.py` has a post-run test for acceptance criterion 3 (panel test view, `auto` → `ModellPrediktor`, no prediction).
- Gate output is recorded in the hand-off report and goes into these notes in commit B (writing it here before the run would dirty the tree).
- Gate output (pytest, clean tree, HEAD = `@{u}`) and the run's console output are written here in commit B. Writing them before the run would dirty the tree and block the guard. Pre-run code was reviewed (triage log below); the note in commit B is reviewed after the run.

**Checkpoint (Decision 6), shown to Felipe before the run on 2026-11-13. He answered "Ja, start testkjøringen":**
- Commit: `8920acb92cda52c9ed03992cb404def7d03f9fdc`, authored by Felipe.
- `.venv/bin/pytest -q`: 441 passed, 3 skipped (the skipped tests in `tests/test_resultater.py`), 28 s.
- `git status --porcelain`: empty. After `git fetch`, HEAD and `@{u}` (`origin/epic/e2-modell`) were both `8920acb…`, and `sjekk_git()` returned the same hash.
- Criteria: verbatim in this spec, committed before the run. The script check against `docs/brief.md` lines 46–71 was True.
- Command: `.venv/bin/python scripts/evaluer.py --test`

**Console output of the one test run (2026-11-13):**

```
Split: test (1566 anløp)

H = 6 t. Øvrige: 1119 rader, 996 med fasit, 1012 med tilstand, 200 F6, 812 i modellutvalget (733 med fasit). Modellandel:  72.6% av alle,  73.6% av dem med fasit.
  radsett              arm                        n     ±30     MAE  median     P     R    F1
  ovrige_modellutvalg  baseline                 733   59.1%    91.9    21.5     –     –     –
  ovrige_modellutvalg  modell                   733   68.5%    75.9    14.7  0.58  0.39  0.46
  ovrige_modellutvalg  ablasjon_uten_f13_f14    733   66.0%    84.0    15.8  1.00  0.18  0.30
  ovrige_modellutvalg  «varsle alle»            733                          0.08  1.00  0.14
  ovrige_alle          baseline                 996   46.6%   135.8    34.3     –     –     –
  ovrige_alle          modell                   996   53.5%   124.0    26.5  0.58  0.11  0.19
  ovrige_alle          ablasjon_uten_f13_f14    996   51.7%   130.0    27.7  1.00  0.05  0.10
  ovrige_alle          «varsle alle»            996                          0.19  1.00  0.33
  passasjer            baseline                 431   79.6%    22.5     5.7     –     –     –

H = 24 t. Øvrige: 1119 rader, 996 med fasit, 1011 med tilstand, 191 F6, 820 i modellutvalget (742 med fasit). Modellandel:  73.3% av alle,  74.5% av dem med fasit.
  radsett              arm                        n     ±30     MAE  median     P     R    F1
  ovrige_modellutvalg  baseline                 742   56.3%   102.4    23.4     –     –     –
  ovrige_modellutvalg  modell                   742   57.1%    96.4    23.6  0.75  0.31  0.44
  ovrige_modellutvalg  ablasjon_uten_f13_f14    742   53.8%   102.4    26.2  0.39  0.19  0.26
  ovrige_modellutvalg  «varsle alle»            742                          0.11  1.00  0.19
  ovrige_alle          baseline                 996   46.6%   135.8    34.3     –     –     –
  ovrige_alle          modell                   996   47.2%   131.3    34.2  0.75  0.12  0.21
  ovrige_alle          ablasjon_uten_f13_f14    996   44.7%   135.8    35.7  0.39  0.08  0.13
  ovrige_alle          «varsle alle»            996                          0.19  1.00  0.33
  passasjer            baseline                 431   79.6%    22.5     5.7     –     –     –

Skrev blokken «test» til /Users/theodorhoffstrom/G73-hoffstrom-lopez-reed/data/modell/metrikker.json
```

The log is `testkjoringer_logg = [{"nr": 1, "dato": "2026-11-13", "commit": "8920acb92cda52c9ed03992cb404def7d03f9fdc"}]`, and the same commit is in `test.kilder.commit`.

**After the run:**
- `tests/test_resultater.py`: all three previously skipped tests passed once `docs/resultater.md` existed. Before that, `test_notat_lik_metrikker` failed with `FileNotFoundError`, as expected.
- **McNemar add-on** (`scripts/mcnemar.py`, approved by Felipe as 1A after Claude stopped and asked under the test-row rule). It ran once and checked that the locked files were unchanged since `8920acb` and that the totals equalled `metrikker.json`. Output:

  ```
| Horisont | n | Begge riktige | Bare modell | Bare baseline | Ingen | Uenige par | p (eksakt) |
|---|---|---|---|---|---|---|---|
| 6 t | 733 | 379 | 123 | 54 | 177 | 177 | < 0,000001 |
| 24 t | 742 | 365 | 59 | 53 | 265 | 112 | 0,6368 |

Skrev /Users/theodorhoffstrom/G73-hoffstrom-lopez-reed/data/modell/mcnemar.json
  ```

  The first version rounded p to 6 decimals, which stored 6 h as `0.0`. It was fixed to 6 significant digits, and p was recomputed from the stored cross-table without reading the test rows again.
- **F13–F14 vs A1:** Felipe's wording "(A1)" was corrected, with his approval, to "the limitation next to A1 in decision 11".
- **Commit order (Felipe):**
  - `a30ddd7`: results, note and reflection notes
  - `c6f1dbd`: merge of `origin/main` (PR #6, E1-S18/S19), with conflicts in `app/__init__.py`, `docs/epics.md`, `docs/prd.md` and `docs/ux/dashbord.md` resolved as Felipe approved
  - a last commit: brief cells, README, epics, screenshots and this spec
- **Locked-file check** (`git diff --stat 8920acb HEAD -- data/modell/*.joblib data/modell/modellvalg.json data/utdrag/features.csv scripts/tren.py scripts/evaluer.py app/prediksjon`): empty after `a30ddd7`, after `c6f1dbd`, and before the last commit. None of PR #6's files are on the locked list.
- **UU6 regression after the merge:** the screenshot script found 649 px at 640 px. The cause was «Spesialfartøy» (PR #6) together with the model's alert texts. It was fixed with a soft hyphen (Felipe, A) and the test `test_spesialfartoy_myk_bindestrek_uten_synlige`. It is now 640 px, and the screenshots were retaken with the model.

## Spec Change Log

## Review Triage Log

| # | Layer | Finding | Verdict | Evidence | Route |
|---|-------|---------|---------|----------|-------|
| 1 | verification-gap, blind | The successful `main --test` path is untested, so `commit` could be missing from `test.kilder` without any test failing | medium | pre-verified: deleting `kilder = dict(kilder, commit=commit)` leaves the suite green, and `test_resultater` is skipped until the run | patch |
| 2 | verification-gap, blind, edge-case | "Validation does not ask git" is tested only for `--bare-baseline` | low | `test_vakta_gjelder_bare_test` runs only `--bare-baseline`; direct one-line fix | patch |
| 3 | blind, edge-case | `--test` accepts path arguments outside the repo or to ignored files, so the commit would not describe the scored inputs | medium | `STANDARD` paths are overridable through `argparse`, and `git status --porcelain` does not see ignored or external files | patch |
| 4 | blind | HEAD = `@{u}` uses a local ref that can be stale | low | nothing fetches before the comparison; Requirement 1 says "pushed" | patch |
| 5 | blind, edge-case | The main table prints «(bestått/ikke bestått)» literally | low | `tabell_hoved` copies the brief's row label; it reads as an unfilled cell in a results note | patch |
| 6 | blind, edge-case | `resultattabeller.main` gives a traceback on a missing nested key or a non-dict file | low | `except` covers only `OSError, ValueError, Mangler`; direct fix | patch |
| 7 | blind | No test checks that the real file gives the test view and the model after the run (AC 3) | medium | the real-file tests now all use `valideringsvisning` (Decision 1) | patch: skipped-until-run test without prediction |
| 8 | verification-gap | The note must land in the same commit as `metrikker.json`, or `test_notat_lik_metrikker` goes red | false | already the plan: commit B holds both | reject |
| 9 | blind | Guard runs before the "already run" check, and `"sjekk"` is a placeholder | low | both orders refuse with exit 2 and nothing written; only the message order differs | reject |
| 10 | blind | `dom_horisont` does not assert that the model and baseline `n` are equal | false | `evaluer.py` scores both arms on identical subset rows (S06 matrix "Subset identity", tested there) | reject |
| 11 | blind, edge-case | `_skilles` stops at 6 decimals, and a win rounded to a tie becomes "ikke bestått" | false | `evaluer._r` stores 6 decimals; with equal `n` ≈ 733, two shares differ by ≥ 1/733 | reject |
| 12 | blind | `test_notat_lik_metrikker` checks tables, not headings or prose numbers | low | the spec requires tables verbatim; prose is checked in the PR (epics E2-S10 Test) | reject |
| 13 | blind, edge-case | `render` does not check log length or `kilder.commit` against the log | low | `test_testkjoringen_har_full_commit` checks it on the real file; a guard adds branches for an unreachable state | reject |
| 14 | blind | The module loader is duplicated in two test files | low | harmless duplication | reject |
| 15 | edge-case | Inputs could change between `sjekk_git()` and the reads | low | needs a concurrent edit during the one supervised run | reject |
| 16 | edge-case | The AC names `logg[0]`, while the test checks `logg[-1]` | false | with one run (`--ny-testkjoring` forbidden) they are the same entry | reject |
| 17 | post-run: blind, edge-case, verification-gap | The p-value test uses `abs=1e-6`, so the `0.0` bug would pass | medium | the 6 h p is 2.3e-07, below the tolerance | patch: `rel=1e-5`, plus a `(123, 54)` case |
| 18 | post-run: blind | The note's opening says "nothing rerun" while McNemar re-read the test rows | medium | contradiction inside `docs/resultater.md` | patch: opening names the one approved re-read |
| 19 | post-run: blind | "Feil funnet etter kjøringen: Ingen" omits the p rounding bug and UU6 | medium | both are in the reflection notes, not in the note | patch |
| 20 | post-run: blind | Nothing stops a second McNemar run, which would read test rows again | medium | `main` always recomputes | patch: refuse when `mcnemar.json` exists; `--bare-tabell` reads only the JSON |
| 21 | post-run: blind, edge-case | "The same code" overstates it, because `_treff` re-implements the ±30 rule | low | semantics match `andel_innenfor` (`<=`, timedelta), and totals are checked | patch: wording narrowed in the docstring and the note |
| 22 | post-run: blind, edge-case | `sjekk_uendret` ignores untracked files | low | `git diff` does not see untracked files | patch: plus `git status --porcelain --untracked-files=all` |
| 23 | post-run: edge-case | Missing log commit, missing git or bad JSON gives a traceback | low | direct `except` and guard | patch |
| 24 | post-run: verification-gap | No test reaches `sjekk_uendret` or the totals check | medium | pre-verified | defer (`deferred-work.md`); the script now refuses to run again |
| 25 | post-run: blind | The briefs show the 24 h pass without its caveats | medium | changelog said only "pass at both horizons" | patch: six voyages, p = 0.64, ablation |
| 26 | post-run: blind | The UU6 row contradicts itself about 1920 px | low | old sentence left in the same cell | patch |
| 27 | post-run: blind | Summer/winter split is loose (both periods include September) | low | validation ends 13.09.2025, test starts 14.09.2025 | patch: exact dates |
| 28 | post-run: blind | No effect size or CI, and no correction for two horizons | low | omission not stated | patch: stated as left out |
| 29 | post-run: blind, verification-gap | Soft-hyphen constants at the bottom of the test file, and the hyphen not checked in the HTML | low | direct | patch |
| 30 | post-run: blind | `mcnemar.json` lacks the analysis date and that p was recomputed | low | recorded in the note and the spec; editing committed data by hand again adds risk | reject |
| 31 | post-run: edge-case | `app/__init__.py` is not on the locked list and changed in the merge | false | McNemar ran before the merge, when `app/__init__.py` equalled `8920acb` | reject |

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- all green, < 1 min, both before and after the run
- `git diff --stat <run-commit> HEAD -- data/modell/*.joblib data/modell/modellvalg.json data/utdrag/features.csv scripts/tren.py scripts/evaluer.py app/prediksjon` -- empty
- `.venv/bin/python -c "import json;print(json.load(open('data/modell/metrikker.json'))['testkjoringer'])"` -- `1`
