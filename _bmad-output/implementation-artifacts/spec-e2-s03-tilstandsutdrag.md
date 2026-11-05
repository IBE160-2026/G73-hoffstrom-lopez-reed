---
title: 'E2-S03 — Tilstandsutdrag og lekkasjetest'
type: 'feature'
created: '2026-11-03'
status: 'done'
baseline_commit: 'b64123da896eda598161b8733c9313b0cea805db'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/docs/beslutninger/11-modellvalg-ovrige-og-features.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The model needs the vessel's state at `t_H` as a small committed file the examiner can use without the 5.6 GB AIS cache (NFR1). Building it must not let any data after `t_H`, or the actual arrival, reach a state field (FR9a).

**Approach:** `scripts/lag_tilstand.py` reads the E2-S02 cache (`pipeline/data/ais_kutt_cache/`, read-only) and `voyageid, eta_reported` from `data/utdrag/anlop.csv`. It writes `data/utdrag/tilstand_ved_kutt.csv` with one row per voyage and H ∈ {6, 24}, taken from the last valid position in [`t_H` − 24 h, `t_H`]. It re-filters on timestamps itself instead of trusting the cache. Code and tests are committed now. The extract is generated and committed separately once the overnight fetch is done (same pattern as E2-S02).

## Decisions (Felipe, 2026-11-03, at approval)

1. **Checksum** (question 1 → A): a new `data/utdrag/tilstand_ved_kutt.json` holds the source path, file count, combined sha256 (the sha256 of the sorted per-file sha256s), creation date (`--laget`) and per-H × `ais_status` counts. `data/baseline.json` is not touched.
2. **`allerede_ankommet`** (question 2 → A): dropped from the extract. The script never reads an arrival field, and the leakage test covers the whole row.
4. **MMSI rule** (Felipe, 2026-11-03, after the smoke run): a position is valid only if the point's MMSI equals the voyage's MMSI and has 9 digits. That extends "valid position" in Boundaries, and the reader now also keeps `mmsino` (not an arrival field). The 63 MMSI 0 voyages become `ingen_posisjon`, and `anlop_ugyldig_mmsi` is counted in the metadata. Recorded in decision 07 and the reflection notes.
3. **One definition of "already in the arrival zone at the cut"** across the whole E2 report: F6, from the position at `t_kutt` (distance ≤ 15 km). E2-S06 splits with and without F6 rows, and the counts it reports are F6 counts. There is no separate count based on actual arrival. PRD FR9a/FR10, decision 11 (choice 7), arkitektur §4 and epics E2-S06 are updated to match.

## Boundaries & Constraints

**Always:**
- Stdlib only, Python 3.9. Run from the repo root. Paths can be overridden for tests.
- `t_kutt = eta_reported − H`, computed from `anlop.csv`. The script stops with an error if a cache file's `t_kutt_utc` disagrees with it.
- Defence in depth: a point counts only if its timestamp is in [`t_kutt` − 24 h, `t_kutt`]. The window filter from `pipeline/fetch_ais_kutt.py` (`filtrer_til_vindu`, `tidsstempel`) is applied again here.
- **Valid position:** lat in [−90, 90] and lon in [−180, 180], so lat 91 / lon 181 are not valid. The row is built from the last valid point. If several points share the last timestamp, the last one in the file wins.
- **Sentinels:** SOG ≥ 102.3 gives an empty `fart_knop`, and COG ≥ 360 gives an empty `kurs_grader`. The position is still used.
- **Fields:** `distanse_km` is the haversine distance (R = 6371) to (60.398, 5.321), the same as `derive_arrivals.py`. `posisjon_alder_min` = (`t_kutt` − point time) in minutes.
- **`ais_status` column:**
  - `ok` — a valid position exists
  - `ingen_posisjon` — the voyage was fetched but has no valid position in the window
  - `ikke_hentet` — there is no cache file (the fetch failed, or the API is missing the day table)
  
  The row is always written, with empty state fields when the status is not `ok`.
- **Output is deterministic:** sorted by (voyageid, horisont_timer), `\n` line endings, fixed formatting (lat/lon 6 decimals, km 3, knots and degrees 1, minutes 1). Same input gives byte-identical output.
- **Run summary:** counts per H × ais_status are printed, and so is a warning when `ikke_hentet` > 0.

**Never:**
- Write anything under `pipeline/` or `pipeline/data/`. Change `data/utdrag/anlop.csv`, the locked dataset, or the 46.6 % regression.
- Read `arrival_in_area_utc`, `status_in_area` or any other arrival field from `anlop.csv`. The reader keeps only `voyageid, eta_reported`.
- Network calls. Features (F3 speed rule, F6, F7 and so on) belong to E2-S04.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal | cache with points in the window | last point → lat, lon, km, sog, cog, age. `ais_status=ok` | N/A |
| Point after cut | point at `t_kutt` + 1 s injected into the cache | identical row | N/A |
| Point moved | the last point moved to after `t_kutt` | the previous point is used, and no field depends on the moved one | N/A |
| Arrival changed | other `arrival_in_area_utc` in `anlop.csv` | byte-identical output | N/A |
| Empty | `status: "tom"` or an empty list | row kept, state fields empty, `ingen_posisjon` | N/A |
| No cache | file missing | row kept, empty, `ikke_hentet` | warning printed |
| Sentinels | lat 91, or SOG 102.3 / COG 360 | invalid point skipped; speed or course empty | N/A |
| Cut mismatch | `t_kutt_utc` in the cache ≠ ETA − H | — | exits non-zero and writes no file |

</frozen-after-approval>

## Code Map

- `pipeline/fetch_ais_kutt.py` -- cache format: `{"status": "ok"|"tom", "horisonter": {"6"|"24": {"t_kutt_utc", "fra_utc", "posisjoner": [[mmsi, tid, lon, lat, cog, sog, ...], ...]}}}`. Reuse `tidsstempel` and `filtrer_til_vindu` by loading the module with `importlib`. Importing has no side effects, and this keeps one source of truth for timestamp parsing. Do not edit the module (the fetch is running).
- `scripts/lag_utdrag.py` -- house style for `scripts/`: argparse with overridable paths, `REPO_ROT`, error message with a non-zero exit, no partial output files.
- `pipeline/derive_arrivals.py:89-110` -- `PORT_CENTER_LAT/LON`, `haversine_km` (R = 6371). Copy, do not import (it is a CLI script).
- `tests/test_fetch_ais_kutt.py` -- pattern for `importlib` loading and API-shaped points (`punkt()`).
- `docs/arkitektur.md` §4 -- extract columns: add `ais_status`, remove `allerede_ankommet`, and add the metadata file.
- `docs/prd.md` FR9a (the bullet "Anløp der skipet allerede har ankommet før `t_H` …") and FR10; `docs/beslutninger/11-…` choice 7; `docs/epics.md` E2-S06 ("antall `allerede_ankommet`") -- these change to the single F6 definition (decision 3).

## Tasks & Acceptance

**Execution:**
- [x] `scripts/lag_tilstand.py` -- CLI `--cache-dir`, `--anlop`, `--ut`, `--laget` -- builds and writes the extract and `tilstand_ved_kutt.json`.
- [x] `tests/test_tilstand.py` -- `test_ingen_lekkasje` (injected or moved points after `t_kutt`, and changed arrival → byte-identical output), `test_mangler_posisjon` (empty and missing cache), `test_sentinelverdier`, `test_siste_gyldige_punkt` (ties and invalid last point), `test_kuttavvik_stopper`, `test_deterministisk`, `test_leser_ikke_ankomstfelt`. All use fixtures in `tmp_path` and need no `pipeline/data/`. Mutation-check the re-filter and the arrival-independence.
- [x] `docs/arkitektur.md` §4, `docs/epics.md` E2-S03/E2-S06, `docs/prd.md` FR9a/FR10 and changelog, `docs/beslutninger/11-…` choice 7 (marked updated 03.11) -- columns, metadata file, and the single F6 definition (decisions 1–3). E2-S03 → ◐.
- [ ] **After the fetch** (separate commit): run against the full cache and commit `data/utdrag/tilstand_ved_kutt.csv` and `tilstand_ved_kutt.json`. Add `test_committet_tilstand` (15 652 rows, columns, every `ok` row has `posisjon_alder_min` in [0, 1440]). E2-S03 → ✅.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then all tests are green in < 1 min, and `test_dataregresjon.py` is unchanged.
- Given the full cache, when the script runs twice, then the outputs are byte-identical and under 2 MB.
- Given `git status` after any run, then nothing under `pipeline/` has changed.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green
- `git status --porcelain pipeline/` -- expected: empty

## Implementation Notes

- 2026-11-03: implemented directly in the main session. Review ran as three independent subagents. 14 tests, 212 in the full suite.
- **Mutation checks** (applied by hand and restored), all caught:

  | Mutation | Failing test |
  |---|---|
  | Re-filter removed | `test_ingen_lekkasje`, `test_flyttet_siste_punkt`, `test_mangler_posisjon` |
  | Window extended to after the cut | `test_ingen_lekkasje`, `test_flyttet_siste_punkt` |
  | Window made exclusive at the cut | `test_vindusgrensene_er_inklusive` |
  | Arrival used as ETA | 10 tests |
  | Ties: first one wins | `test_siste_gyldige_punkt_ved_likt_tidsstempel` |
  | Every position valid; 0,0 accepted; speed sentinel removed | `test_sentinelverdier` |
  | Cut check removed | `test_kuttavvik_stopper` |
  | lon written from lat | `test_normal_rad` |

- **Smoke run on the partial cache** (600 files, read-only, output to the scratchpad, nothing committed):
  - 15 652 rows. Of the fetched voyages, 490/600 are `ok` at 6 h and 455/600 at 24 h.
  - Median distance 87 km (6 h) and 182 km (24 h). Median position age 0.1 min.
  - The column order is confirmed on real API points.
- **Finding from the smoke run: MMSI 0.** 6 voyages (rows) sit 7 000–17 000 km from Bergen. All have `mmsino = 0`, and the API then returns points from every vessel worldwide that sends MMSI 0. There are 63 such voyages in `anlop.csv`, and all are `status_in_area = empty`, so they have no ground truth and the 46.6 % is unaffected. Felipe chose the MMSI rule (decision 4). After it, the maximum distance is 645 km at 24 h. `test_mmsi_maa_stemme_og_ha_9_sifre` is mutation-checked: removing the MMSI equality or the 9-digit requirement is caught.
- **2026-11-05: new `ais_status` `manglende_dag`** (Felipe, after the code review of E2-S02's fix `0a85cd4`, decision 09 addendum).
  - A cut point inside the lost interval of a missing day table (`fetch_ais_kutt.tapt_intervall`: [day 00:00, next day 02:00)) gets `manglende_dag`, unless there is a valid position from inside the hole. It does not get `ok` with a position from the day before. Rows that are not `ok` go to the baseline (`har_tilstand=0` in `lag_features.py`).
  - Tests: `test_kutt_i_manglende_dag_far_egen_status`, `test_hullgrensene`, `test_gammel_cache_uten_manglende_dager`, and in `test_features.py` `test_manglende_dag_gar_til_baselinen`.
  - Mutation-checked: removing the check, ignoring in-hole positions, and moving either interval bound are all caught. The first boundary test let `<=` at the end survive, and it was tightened.
  - Real cache 05.11 (partial, read-only, output in the scratchpad): 8 cut points get `manglende_dag` (1 at 6 h, 7 at 24 h), which matches the review's count.

## Spec Change Log

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG).

- VG: `lon` is never asserted — medium, pre-verified. **patch**: a distinct fixture lon, asserted for both horizons. Mutation confirmed.
- ECH/BH: corrupt or incomplete cache JSON (missing horizon or keys) gives a traceback instead of a clean stop — low, direct fix. **patch**: `KuttAvvik` names the file, nothing is written, test added.
- ECH: the fetch can replace a file between `json.load` and the hash — low, direct fix. **patch**: read once, then hash and parse the same bytes.
- ECH: lat 0 / lon 0 placeholder accepted — low, direct fix. **patch**: not a valid position, test added.
- ECH/BH: CSV and JSON written one after the other — low. **patch**: both written to `.tmp` before either is replaced, plus `utdrag_sha256` in the metadata so a mismatch between the two replace calls is detectable. The test covers a failure in the write phase.
- BH: `tom` answers are mixed into `ingen_posisjon` — medium. The three statuses are frozen (Felipe), so no new status. **patch**: `kilde_antall_tomme_svar` in the metadata and the docstring.
- BH: arkitektur says an `ok` row is complete, but speed and course can be empty — low. **patch**: doc text, plus a note that E2-S04 must handle it.
- BH: the leakage test wording differs between PRD and epics, and the "moved" and "removed" cases were not tested — medium. **patch**: both cases are in `test_ingen_lekkasje`, and the epics wording now matches PRD FR9a.
- BH: no test at the exact window edges — medium. **patch**: `test_vindusgrensene_er_inklusive`, mutation confirmed.
- BH: hard-coded column indices, with tests sharing the same assumption — medium. **patch**: named constants `I_LON/I_LAT/I_COG/I_SOG`, and the smoke run on real cached API points confirmed the order (lat ≈ 60, lon ≈ 5, speed and course plausible).
- BH: no checksum for `anlop.csv`; absolute paths could be committed — low, direct fix. **patch**: `anlop`, `anlop_sha256`, and paths relative to the repo (otherwise just the file name).
- BH/ECH: `kilde_antall_filer` means matched files only — low. **patch**: documented.
- BH/ECH: `--laget` defaults to today — false as a defect. Determinism is defined for a fixed `--laget`, as in E1-S02. Documented in the docstring.
- BH: stale F6 wording in decision 11 — low. **patch**.
- BH: test file-handle leak — low. **patch**: `with`.
- ECH: empty, non-numeric or duplicate voyageids, and unparseable ETAs — false. All 7 826 rows of the locked `anlop.csv` were checked in E2-S02: digit ids, 0 duplicates, every ETA parses.
- ECH: empty `anlop.csv` writes a header-only extract — low, rejected. The source is the locked file, which has 7 826 rows.
