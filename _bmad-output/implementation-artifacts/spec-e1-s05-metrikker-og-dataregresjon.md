---
title: 'E1-S05 — Metrikkmodul og dataregresjon'
type: 'feature'
created: '2026-10-27'
status: 'done'
baseline_commit: '4895eb144ebc5df7904a2d7dc302b95d4fe92bb6'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-e1-s04-prediktor-og-baseline.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The headline numbers (46,6 % Øvrige, 79,6 % Passasjer within ±30 min on the test period) live in brief, PRD and README, but no test produces them from the app's own code. A change in the data layer or the S04 contract could silently move them, and a sensor would find README and app disagreeing.

**Approach:** Add `app/metrikker.py` that scores `Prediksjon` objects against ground truth, and a regression test on the real extract that produces every number through the S04 contract (`lag_input` → `prediker`), with no shortcut.

**Group requirements (27.10.2026):**
1. The baseline is the first predictor implementing the S04 contract. It must pass the contract's leakage tests like every future predictor, with no exception for being "just" a baseline. The regression numbers must come from that same contract path.
2. A regression test locks 46,6 % (Øvrige) and 79,6 % (Passasjer) within ±30 min on the test period. Any change that moves them fails a test.

**Decision (27.10.2026): naive Øvrige is 12,8 %, not 12,9 %.** `pipeline/derive_arrivals.py:518` rounded deviations to 0,1 min before the ±30 comparison. Voyage 3542899 (+30 min 1 s) was counted as a hit, which gave 12,9 %. On unrounded times it is 127/996 = 12,8 %. The rule from E1-S02 that calculations use unrounded times applies everywhere. Correct 12,9 % → 12,8 % in brief.md, brief.no.md, prd.md, addendum.md, ux/dashbord.md, arkitektur.md and epics.md, with a changelog line where the document has one. Decision 04 and the prompt logs stay as history, with a dated note in decision 04 saying the number was corrected from 12,9 % because the pipeline rounded the deviation before comparing.

## Boundaries & Constraints

**Always:**
- ±30 min is inclusive: `|faktisk − predikert| ≤ 30 min`, on unrounded times (decision 27.10: only display rounds).
- Only calls with ground truth count (`status_in_area == "ok"`). Calls without it are counted by `dekning()`, never scored.
- Every prediction scored, baseline and naive alike, is produced by a predictor in `PREDIKTORER` via `lag_input(a, naa)` with `naa = eta_reported − H` for H ∈ {6, 24}.
- The regression test locks exact counts, not only rounded percentages.
- Python 3.9.

**Never:**
- `metrikker.py` computing a prediction itself (`eta − offset`), importing `app.prediksjon.baseline`, or reading `data/baseline.json`.
- A predictor exempted from, or skipped in, `tests/test_prediktor_kontrakt.py`.
- Route, template or panel changes (E1-S12).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Baseline, Øvrige | real extract, test split, H = 6 and 24 | 464 / 996 → 46,6 % at both horizons | N/A |
| Baseline, Passasjer | same | 343 / 431 → 79,6 % at both horizons | N/A |
| Naive, Passasjer | same | 32 / 431 → 7,4 % | N/A |
| Naive, Øvrige | same | 127 / 996 → 12,8 % (voyage 3542899 at +30 min 1 s is outside) | N/A |
| Coverage | test split | 1 566 calls: ok 1 427, empty 126, not_detected 8, avkortet_av_neste_seilas 5 | N/A |
| Boundary | deviation exactly 30 min / 30 min + 1 s | inside / outside | N/A |
| No ground truth | status ≠ ok | excluded from numerator and denominator | N/A |
| Mismatch | prediction for a voyageid not in calls | — | `ValueError` naming the id |
| Empty | no scorable calls | — | `ValueError`, never 0 % or division error |

</frozen-after-approval>

## Code Map

- `app/prediksjon/__init__.py` -- `lag_input`, `Prediksjon`, `PrediksjonsInput`. Read-only.
- `app/prediksjon/baseline.py` -- `BaselinePrediktor`. Read-only.
- `tests/test_prediktor_kontrakt.py` -- `PREDIKTORER = [BaselinePrediktor]`. Add `NaivPrediktor`; nothing else changes.
- `app/data.py` -- `last_utdrag()`, `Anlop` (`faktisk_ankomst` is `None` unless `status_in_area == "ok"`). Read-only.
- `pipeline/derive_arrivals.py:231` -- original `abs(d) <= 30` (inclusive). Reference only.
- 12,9 % occurs in `docs/brief.md:53`, `docs/brief.no.md:53`, `docs/prd.md:80`, `docs/addendum.md:59`, `docs/ux/dashbord.md:59`, `docs/arkitektur.md:181`, `docs/epics.md` (E1-S05) and `docs/beslutninger/04-kalibrert-baseline.md:29` (history: note only).

## Tasks & Acceptance

**Execution:**
- [x] `app/prediksjon/naiv.py` -- `NaivPrediktor` (navn «Naiv ETA», `kan_varsle = False`, `predikert = eta_reported`, `forklaring` with `metode`, `gruppe`) -- a reference predictor, so the naive number also goes through the contract. Not selectable through `velg_prediktor`.
- [x] `app/metrikker.py` -- `andel_innenfor(prediksjoner, anlop, minutter=30)` returning hits, n and share. `dekning(anlop)` returning counts per status.
- [x] `tests/test_prediktor_kontrakt.py` -- add `NaivPrediktor` to `PREDIKTORER`. Add a test that `BaselinePrediktor` and `NaivPrediktor` are both in it, and an AST check that `metrikker.py` does not import `app.prediksjon.baseline` or reference `baseline.json`.
- [x] `tests/test_metrikker.py` -- fixture-based matrix rows: boundary, no ground truth, mismatch, empty.
- [x] `tests/test_dataregresjon.py` -- real extract: exact counts and rounded percentages for baseline (both horizons) and naive, plus coverage.
- [x] `docs/epics.md` -- E1-S05 → ✅, naive Øvrige 12,8 %, changelog line.
- [x] `docs/brief.md`, `docs/brief.no.md`, `docs/prd.md`, `docs/addendum.md`, `docs/ux/dashbord.md`, `docs/arkitektur.md` -- 12,9 % → 12,8 %, changelog line where the document has one. `docs/beslutninger/04-kalibrert-baseline.md` -- dated note only, the 12,9 % sentence stays.

**Acceptance Criteria:**
- Given the committed extract, when `pytest` runs, then the regression test proves 46,6 % and 79,6 % from predictions made by `BaselinePrediktor` through `lag_input`.
- Given a predictor removed from `PREDIKTORER`, when the suite runs, then a test fails.

## Design Notes

**Why `naa = eta − H`.** Each call is scored as if predicted at its cut point, which is how E2 will evaluate the model per horizon (FR10). The baseline ignores the horizon, so the same number at H = 6 and 24 is itself a check.

**What the regression test can and cannot catch.** Exact counts catch any change to rows, statuses, the split, the boundary (`<` gives 463/996 = 46,5 %) or the offsets beyond rounding. The Passasjer count is flat around its offset: 343/431 at 43,75, 44,75, 44,8 and 46,75 min. A Passasjer offset change of ±1 min is therefore *not* caught here. The exact offset is already locked by `test_baseline.py::test_passasjer_offset_er_uavrundet` and `::test_offset_leses_fra_baseline_json`, so it must not be claimed here. Øvrige moves with ±1 min (462 / 461).

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green (72 existing + new).
- `grep -rn '12,9\|12\.9' docs README.md` -- expected: hits only in `docs/prompts/`, `docs/refleksjon/` and the history sentence plus note in decision 04.
- Mutation check with a control run on unchanged code. The regression test must fail when:
  - `≤` becomes `<`
  - the Øvrige offset changes by 1 min
  - a test-split `ok` row is changed to `empty` in a temp copy of the extract
  - `metrikker.py` computes `eta − offset` itself (AST test)
  - `NaivPrediktor` is removed from `PREDIKTORER`

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). Plus the orchestrator's own mutation check (M).

- BH: a scorable call with no prediction drops out of `n` silently, so a predictor that skips hard calls scores higher. medium, real (only the hard-coded n in the regression test notices). **patch**: `ValueError` naming the id.
- BH + ECH: duplicate predictions for one voyageid are counted twice. medium, real. **patch**: `ValueError` on duplicates.
- BH + ECH (claim) + VG other: `test_alle_kjente_prediktorer_er_med` checks two hard-coded classes, so an unregistered new predictor module escapes the contract, which is exactly what group requirement 1 forbids. medium, real. **patch**: discover predictor classes in `_prediktormoduler()` and compare with `PREDIKTORER`; `naiv.py` added to `test_prediktormoduler_finnes`.
- BH + ECH: the metrics AST import check is a blocklist and misses `velg_prediktor`/`NaivPrediktor` imports. medium, real. **patch**: allowlist (`Anlop`, `Prediksjon`, stdlib). Dynamic `importlib` is rejected as deliberate code, as in S04.
- VG gap: nothing tests that `NaivPrediktor` cannot be chosen via `velg_prediktor`, although epics.md now states it. medium, pre-verified. **patch**: test for `"naiv"` → `ValueError`.
- M: the mutant `har_fasit = faktisk is not None` (status ignored) survives, because the test helper never builds a non-ok call with an arrival time. VG noted the data layer makes it unreachable today. low, but it is the spec's own rule and the S03 lesson. **patch**: test-only.
- BH: `docs/addendum.md` ALL row changed 11.2 → 11.1 % without explanation. low, real. **patch**: extend the note.
- BH: the decision 04 note sits under "Fullbatch-tall (n=7 826)" while 127/996 is the test split. low, real. **patch**: name the population.
- BH: the regression docstring claims README has the numbers; it has only 46,6 %. low, real. **patch**: wording.
- BH: `pipeline/derive_arrivals.py:518` still rounds the column that produced 12,9 %. low, real. **patch**: comment only; behaviour unchanged because the pipeline is locked (E0-S14).
- BH + ECH: `dekning()` counts `ok` while `har_fasit` also requires an arrival time. **false**: the real extract has 0 `ok` rows without an arrival, and the data layer sets the time from the same row.
- BH: FR8 per-group coverage and 91,1 % not computed. **false** for this story: `dekning()` on a group-filtered list gives it; the epics criterion (counts per status) is met. E1-S12 builds the panel.
- BH: `NaivPrediktor.forklaring` lacks `eta_reported`. **false**: the contract requires `metode` and `gruppe` (arkitektur §3, S04).
- BH: horizon parametrisation tells nothing apart. **false**: by design (Design Notes): identical numbers at both horizons are themselves a check.
- BH: the regression test imports `PREDIKTORER` from another test module. low, rejected: it works under the repo's `pytest.ini`, and no breakage was shown.
- BH + ECH: `minutter` negative/NaN not validated. low, rejected: internal parameter, callers pass constants; a guard adds surface.
- ECH: duplicate voyageid among `anlop`. low, rejected: voyageid is unique in the extract; a guard adds complexity.
- ECH: naive `predikert_ankomst` gives a raw `TypeError`. **false**: the contract test asserts every prediction is tz-aware UTC.
- ECH: `NaivPrediktor` never inspects `naa`. **false**: no predictor needs to; `t_kutt` is enforced in `lag_input`.
- ECH: relative/dynamic import of baseline in `metrikker.py`. Relative import is covered by the allowlist patch; dynamic is rejected as deliberate.
