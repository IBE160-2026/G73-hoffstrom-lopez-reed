---
title: 'E1-S02 — Datautdrag og lagret baseline'
type: 'feature'
created: '2026-10-22'
status: 'done'
baseline_commit: '35ce55dae7322a1ab14a2803f3b79e4f8ad6f031'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/docs/arkitektur.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The full dataset lives in the gitignored `pipeline/data/` and takes hours to regenerate, so the examiner cannot run the app from a clone (NFR1). The calibrated baseline's split and offsets exist only as console output of `derive_arrivals.py`.

**Approach:** Add `scripts/lag_utdrag.py`, which reads `pipeline/data/bergen_eta_avvik.csv` and writes a committed extract `data/utdrag/anlop.csv` (architecture §4 columns plus `split`) and `data/baseline.json` (offsets per group, test start, source path and sha256, date made). Split and offsets are computed exactly as in `derive_arrivals.py`, giving 6 260/1 566 rows and 44,8/64,2 min on the real data. Generated files are committed in the same commit as the script.

## Boundaries & Constraints

**Always:** stdlib only (csv, json, hashlib, argparse); Python 3.9. Same split rule as `compute_offsets_and_split`: stable sort by `eta_reported` string, `split_idx = int(n * 0.8)`. Same offset rule: median (`percentile(…, 0.5)` semantics) of `dwell_area_to_quay_minutes` over TRAIN rows with `status_in_area == "ok"` and `status_at_quay == "ok"`, grouped Passasjer vs. all others ("Øvrige"). Deterministic: same input + same `--laget` → byte-identical outputs. Paths overridable by CLI args so tests run on fixtures.

**Never:** modify `pipeline/` or `pipeline/data/`; compute deviation or `er_forsinket` in the extract (computed in the app, architecture §4); normalise timestamps (that is E1-S03's loader); round the stored offsets (rounding could flip a ±30 min classification and break the E1-S05 regression numbers).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real data | `pipeline/data/bergen_eta_avvik.csv` (7 826 rows) | 7 826 rows; 6 260 `train` / 1 566 `test`; offsets round to 44,8 / 64,2; `test_fra_utc` = `2025-09-14T03:15:00Z` | N/A |
| Fixture | `tests/fixtures/pipeline_mini.csv` (10 rows, hand-made) | 8 train / 2 test, offsets equal hand-computed medians | N/A |
| Group with no qualifying train rows | fixture variant | offset is `null` in JSON | no crash |
| Source missing | wrong `--kilde` path | exit non-zero with message naming the path and the pipeline command | no partial output files |
| Run twice | same input, same `--laget` | identical bytes | N/A |

</frozen-after-approval>

## Code Map

- `pipeline/derive_arrivals.py:240-267` -- `TEST_FRACTION`, `group_of`, `compute_offsets_and_split`: the rule to replicate (do not import: the module is a CLI script with heavy top-level docs; replicate the ~15 lines and cite the source).
- `pipeline/derive_arrivals.py:209-220` -- `percentile` (linear interpolation); replicate exactly.
- `pipeline/data/bergen_eta_avvik.csv` -- source; `eta_reported` has `+00:00`, `arrival_in_area_utc` has no suffix. Keep values verbatim.
- `docs/arkitektur.md` §4 -- extract columns and `baseline.json` shape. Group keys in JSON: `"Passasjer"`, `"Øvrige"` (`ensure_ascii=False`).
- `tests/conftest.py` -- existing fixtures; no change needed.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/lag_utdrag.py` -- CLI `--kilde`, `--ut-dir` (default `data/`), `--laget` (default today, ISO date) -- writes `utdrag/anlop.csv` (rows in split-sort order, `\n` line endings) and `baseline.json` (sorted keys, indent 2, trailing newline); prints counts and offsets.
- [x] `tests/fixtures/pipeline_mini.csv` -- 10 hand-made rows across both groups with known dwell values, plus one group-less-train variant built inside the test.
- [x] `tests/test_lag_utdrag.py` -- columns, 8/2 split, offsets, `null` offset, determinism, missing-source exit code.
- [x] `data/utdrag/anlop.csv`, `data/baseline.json` -- generated from the real source and committed.
- [x] `docs/epics.md` -- E1-S02 → ✅.

**Acceptance Criteria:**
- Given the committed `data/`, when a test reads `baseline.json` and `anlop.csv`, then it finds 6 260/1 566 rows and offsets 44,8/64,2 (rounded) without needing `pipeline/data/`.
- Given a fresh clone, when `pytest` runs, then no test needs network or `pipeline/data/`.

## Design Notes

`laget` breaks byte-identity across days, so determinism is defined for a fixed `--laget`; the test passes one explicitly. Offsets are stored unrounded (e.g. `44.75`), displayed rounded.

## Verification

**Commands:**
- `.venv/bin/python scripts/lag_utdrag.py` -- expected: prints 6260 train / 1566 test, offsets 44.8 / 64.2
- `.venv/bin/pytest -q` -- expected: all green, < 1 min

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). Diff excluded the 702 kB generated `data/utdrag/anlop.csv` (covered by `test_committet_utdrag_og_baseline`).

- VG gap: split truncation `int(n*0.8)` not pinned (fixture n=10 gives exactly 8.0) — medium, pre-verified; same root as BH "no parity test with pipeline". **patch**: parity test vs. `derive_arrivals.compute_offsets_and_split` on a 9-row variant.
- BH/ECH: "no half files" comment, CSV written before JSON — low, real (comment overstates). **patch**: reword comment; atomic temp-file writes rejected (guard for disk-full/permission failures never seen in practice).
- BH/ECH/VG: `data/` untracked so clean-clone test fails — false: staged in the story commit per spec task list; review ran before commit.
- BH: `laget` defaults to today, breaking cross-day byte identity — false: Design Notes define determinism for a fixed `--laget`.
- BH/ECH/VG: stored offset 44.75, not 44.8 — false as a defect: Boundaries say "never round stored offsets"; display rounding belongs to E1-S04/S11.
- BH/ECH: bad input (missing column, empty dwell, BOM, non-UTF-8, header-only, `Z` suffix, mixed ETA formats, bad `--laget`, `--ut-dir` is a file) gives tracebacks — low, rejected: the only input is our own pipeline output (all ETAs `+00:00`, verified on 7 826 rows); fixes add guards for unseen states.
- BH: string sort with ties untested — low, rejected: identical to pipeline (stable sort); the real boundary row has a unique ETA.
- BH: no check that `kilde_sha256` is well-formed — low, rejected: fixture test asserts the exact sha.
- BH: no record of the command that produced `data/` — false: module docstring has the command; `baseline.json` stores source sha and `laget`.
- Parity test tightened by the orchestrator from 9 to 7 rows after the implementer noted `round(7.2) == int(7.2)`: 7 × 0.8 = 5.6 separates truncation from both `round` and `ceil`.
