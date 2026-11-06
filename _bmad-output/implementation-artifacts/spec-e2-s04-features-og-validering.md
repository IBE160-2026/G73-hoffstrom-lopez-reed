---
title: 'E2-S04 — Features og valideringssplitt'
type: 'feature'
created: '2026-11-03'
status: 'done'
baseline_commit: '75502748b81b06ee77baeb1946452351ac998b1f'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/docs/beslutninger/11-modellvalg-ovrige-og-features.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** E2-S05 needs F1–F16 (decision 11) for every voyage and horizon, plus a chronological validation split, built without leakage. The examiner must get them without `pipeline/data/` (NFR1). Static voyage fields (ship type, length, ETD, departure port) exist only in the gitignored voyages file.

**Approach:**
- `app/prediksjon/features.py` holds pure feature functions. They read no files, and the existing AST rule applies to the module.
- `scripts/lag_features.py` joins `anlop.csv`, `tilstand_ved_kutt.csv` and the voyages file (read-only). It writes a committed `data/utdrag/features.csv`: one row per voyage × H, with F1–F16 and a `del` column (`trening`/`validering`/`test`).
- Code and tests are committed now. The extract follows once E2-S03's extract exists (after the fetch).

## Decisions (Felipe, 2026-11-03, at approval)

1. **Committed data** (question 1 → A): only `data/utdrag/features.csv` (+ `features.json`), with the derived F8–F14. There is no raw static extract, and raw ETD is never committed. Arkitektur §4 is updated.
2. **Long-distance check thresholds** (question 2): realistic speed 25 kn, physically impossible 45 kn (or arrival before `t_kutt` while > 15 km away). Classes: late (> 120 min, kept) / on time (investigate) / impossible (investigate) / no ground truth (kept, counted). It runs on the full data after the fetch. Nothing is removed in this story.
3. **Label check after the fetch** (HALTBAKK STAR): count voyages whose zone entry (`arrival_in_area`) is more than 24 h before the reported ETA, split by ship type. If they concentrate on offshore and supply vessels, that is a limitation of the label choice in decision 03, and it is written into decision 03. The dataset is not changed.

4. **Validation history** (Felipe, after review): validation rows get F15–F16 only from the `trening` part, frozen at the boundary, as test rows are. The final training uses history from trening + validering together. `features.csv` carries both: `fartoy_*_modellvalg` for model selection and `fartoy_*` for the final fit and test.
5. **ETD sanity:** an ETD more than 14 days before ETA counts as missing (approved).

## Boundaries & Constraints

**Always:**
- **Leakage (FR9a, decision 11):**
  - Every feature for a row uses only information available at its `t_kutt`.
  - F15 and F16, including the shrinkage target, come from **train-split** rows with valid MMSI and `arrival_in_area < t_kutt`, never the row itself.
  - The deviation used is the calibrated one: arrival − (ETA − `offset[gruppe]` from `baseline.json`).
  - With no history, the target is 0 and F16 = 0.
- **Definitions** follow decision 11 exactly:
  - F3 is empty when course is missing, speed is missing or < 1 kn, or distance is 0.
  - F6 means distance ≤ 15 km.
  - F7 = H_eff − (km / 1.852) / max(speed, 1), with H_eff = (ETA − `t_kutt`) in hours, clipped to [−48, H_eff]. It is empty when speed is empty, and distance 0 gives H_eff.
  - F10–F12 come from reported ETA in Europe/Oslo time.
  - F14: `avgatt_for_kutt` = 1 if ETD ≤ `t_kutt`, 0 if ETD > `t_kutt`, empty if ETD is missing. `timer_siden_avgang` is filled only when ETD ≤ `t_kutt`.
- **Raw categories** are stored: `skipstype` and `avgangshavn` as in the source. `grupper_sjeldne(verdier, terskel=20)` (≥ 20 Øvrige rows in the fit data, otherwise `annet`) is a tested function for E2-S05 to fit on its fit data only.
- **Validation split:** stable sort of train rows by `eta_reported`. `int(n_train × 0.8)` → `trening`, the rest → `validering`. Test rows stay `test` and are never used to build any feature.
- **Rows without state** (`ais_status ≠ ok`) are kept with empty F1–F7 and `har_tilstand = 0`.
- Deterministic output, stdlib only in the script, Python 3.9. Everything E2 commits under `data/` stays < 10 MB.

**Never:**
- Write to `pipeline/` or `pipeline/data/`.
- Change `anlop.csv`, `baseline.json` or the 46.6 % regression.
- Commit the raw ETD value.
- Let `features.py` import `app.data` or read files.
- Fit anything on the test period.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| History leakage | change every test-period arrival and the row's own; add, remove or move test rows | identical F15/F16 and target for all rows | N/A |
| Later train row | change one train row's arrival deviation | only rows with `t_kutt` after that row's arrival change | N/A |
| No history | first voyage of a vessel, or no train row before `t_kutt` | F15 = target (0 if none), F16 = 0 | N/A |
| ETD after cut | change an ETD that is > `t_kutt` | identical features | N/A |
| Low speed | speed 0, 0.3, 1.0, 12, missing, 102.3 (already empty from E2-S03) | F7 per formula, or empty | N/A |
| Bad course | course 360 or missing, speed < 1, distance 0 | F3 empty | N/A |
| DST | ETA either side of the Oslo DST switch | F10 uses local hour | N/A |
| MMSI 0 | `mmsino = 0` | no history, F16 = 0 | N/A |

</frozen-after-approval>

## Long distances at the cut — first check (Felipe, 03.11)

Run on the partial cache, read-only (605 voyages with state at 6 h and 556 at 24 h, built with the scratchpad extract and joined to `anlop.csv` and `baseline.json`):

| H | Needs > 25 kn | > 30 kn | With ground truth | Late > 120 min | On time | Impossible |
|---|---|---|---|---|---|---|
| 6 h | 3 | 2 | 1 | 0 | 1 | 1 |
| 24 h | 0 | 0 | 0 | — | — | — |

- **The only case with ground truth:** 2233024 HALTBAKK STAR (platform supply ship, train).
  - It is 315 km away at `t_6` and needs 28 kn. Ground truth says it arrived 2 613 min *before* the calibrated ETA, that is 01.02 08:22, before the cut.
  - Voyage: Stavanger 30.01 → ETA Bergen 03.02. The most likely reading is that it passed through the 15 km zone early and went back out to the field, so the label (first zone entry, decision 03) caught the wrong pass.
  - **Possible label error in the locked dataset, not a position error.** It is recorded, and the dataset is not changed.
- Base rate for comparison: among rows needing ≤ 25 kn, with ground truth, 9.9 % are late (6 h) and 9.5 % (24 h). These are partial data across both groups.
- The sample is far too small to conclude. The check is rerun on the full data (task below), and the numbers replace this table.

## Code Map

- `docs/beslutninger/11-modellvalg-ovrige-og-features.md` -- the definitions of F1–F16, with edge rules. They are the source of truth.
- `scripts/lag_tilstand.py` -- the state extract format (`ais_status`, empty fields), `haversine_km`, `naive_utc`, `gyldig_mmsi`. Reuse via `importlib` (as E2-S03 does with the fetcher) rather than copying.
- `scripts/lag_utdrag.py` -- the split rule (stable sort by the `eta_reported` string, `int(n × 0.8)`), and house style.
- `tests/test_prediktor_kontrakt.py:182-247` (`_prediktormoduler`, `test_prediktormodul_leser_ikke_datalaget`) -- the AST rule, which covers every `app/prediksjon/*.py` except `__init__.py`. `features.py` must pass it: no `app.data` import, no `data/utdrag` or `baseline.json` strings.
- `pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv` -- 8 094 rows, columns `voyageid, mmsino, shipname, ship_type, ship_group, length, eta, etd, dep_locname`. **Read-only.** A superset of the `anlop.csv` voyageids.
- `data/baseline.json` -- `offset_minutter` (Passasjer 44.75, Øvrige 64.2). Read-only.

## Tasks & Acceptance

**Execution:**
- [x] `app/prediksjon/features.py` -- pure functions for F1–F16, the `Historikk` class (`maal`, `fartoy`), `gyldig_etd`, `lag_kategorikart`/`grupper_sjeldne`, `valideringssplitt`.
- [x] `scripts/lag_features.py` -- CLI with overridable paths and `--laget`. Writes `features.csv` and `features.json` (input sha256s, counts per `del` × H × `har_tilstand`).
- [x] `tests/test_features.py` -- `test_fartoyhistorikk_bare_fra_trening` (matrix rows 1–3, MMSI 0), `test_historikk_uten_lekkasje`, `test_valideringssplitt_kronologisk`, `test_slakk_ved_lav_fart`, `test_kurs_ugyldig`, `test_etd_etter_kutt_brukes_ikke`, `test_kalender_oslo_sommertid`, `test_grupper_sjeldne`, `test_f6_fra_posisjon`, `test_deterministisk`. Fixtures only. Mutation-check the history filter (train-only, `< t_kutt`, excluding itself) and the ETD rule.
- [x] `docs/arkitektur.md` §4, `docs/epics.md` E2-S04 -- the extract as decided in question 1. E2-S04 → ◐.
- [x] **After E2-S03's extract** (separate commit, extract done 2026-11-06; the two checks follow in their own commit the same day): generate and commit `features.csv`/`.json`, add `test_committet_features` (rows, `del` counts, and the E2 `data/` total < 10 MB), rerun the long-distance check (25/45 kn) and replace the table above with the full numbers, and run the label check (decision 3) and record the result in decision 03 if it is concentrated on offshore and supply. E2-S04 → ✅.

**Acceptance Criteria:**
- Given no `pipeline/data/`, when `pytest` runs, then everything is green in < 1 min, the AST rule passes for `features.py`, and `test_dataregresjon.py` is unchanged.
- Given the generated extract, then it has 15 652 rows, the `trening`/`validering`/`test` counts are 5 008/1 252/1 566 voyages × 2, and its size keeps the E2 `data/` total < 10 MB.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green
- `git status --porcelain pipeline/` -- expected: empty

## Implementation Notes

- 2026-11-03: implemented directly in the main session. Review ran as three independent subagents. 25 tests in `test_features.py`, 239 in the full suite. The AST rule passes for `features.py`: it first caught the word "utdrag" in the module docstring, which was then reworded.
- **Mutation checks**, all caught (each applied and restored):

  | Mutation | Failing test |
  |---|---|
  | Test rows in history | `test_fartoyhistorikk_bare_fra_trening` |
  | No time limit | 3 tests |
  | Own row not excluded | `test_historikk_uten_lekkasje`, `test_egen_ankomst_endrer_ikke_egen_historikk` |
  | ETD after the cut used | `test_etd_etter_kutt_brukes_ikke` |
  | MMSI filter removed | `test_uten_historikk_og_mmsi_0` |
  | k = 0, 1 or 50 | `test_krymping_mot_snittet` |
  | No speed floor in F7 | `test_slakk_ved_lav_fart` |
  | Calendar in UTC | `test_kalender_oslo_sommertid` |
  | Validation = first 20 % | `test_valideringssplitt_kronologisk` |
  | ETD sanity, 102.3 guard, duplicate check or length check removed | caught |

  k = 0 survived the first fixture, because the vessel mean happened to equal the target. The fixture was changed so they differ.
- **Smoke run** (scratchpad, partial state, the voyages file read-only):
  - 15 652 rows, with 5 008 / 1 252 / 1 566 per H, and 2.4 MB.
  - F7 ranges over [−48, H], with median 0.75 h at 6 h.
  - At 6 h, 45 % have not yet departed.
  - F16 has median 14, and 19 % of rows have no history.
- **ETD sanity:** an ETD more than 14 days before ETA counts as missing, the same cap as `fetch_ais.py` (decision 02). It affects 18 of 7 826 rows, including 2 with the placeholder 0001-01-01. All 7 826 voyages have a row in the voyages file, and there are 0 duplicate voyageids.
- **Full extract, 2026-11-06** (`--laget 2026-11-06`): 15 652 rows, 3.1 MB. Voyages per `del`: trening 5 008, validering 1 252, test 1 566. With state at H = 6 / 24: trening 4 271 / 4 029, validering 1 143 / 1 093, test 1 452 / 1 447. A second run gives a byte-identical file. The E2 files under `data/utdrag/` total 4.2 MB, under the 10 MB budget. `test_committet_features` checks sha256, rows, `del` counts and the budget.

## Spec Change Log

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG).

- ECH: ETD placeholder 0001-01-01 (2 real rows) gives `timer_siden_avgang` ≈ 17.7 M h — high. **patch**: `gyldig_etd`, where ETD more than 14 days before ETA counts as missing (18 rows), with a test and a mutation check.
- BH/ECH: validation rows' F15/F16 use other validation rows' arrivals, while test rows see only train-split history frozen at the split. Validation is fresher than test, so model selection may look optimistic — medium. **intent_gap**, resolved by Felipe (decision 4): two variants, with `*_modellvalg` frozen at the boundary. Covered by `test_valideringshistorikk_frosset_ved_grensen`, and the mutation (model selection using the final history) is caught. In the smoke run, 1 687 of 2 504 validation rows differ between the variants, and 0 training rows do.
- VG: the extra-tilstand-row guard is not exercised — medium. **patch**: test, mutation confirmed.
- VG/BH: a voyage without a row in the voyages file is not exercised and not counted — medium. **patch**: `test_uten_seilasrad`, plus `anlop_uten_seilasrad` in the metadata (0 on real data).
- VG/BH: `meta["antall"]` and `utdrag_sha256` are not asserted — medium. **patch**: exact assertion.
- BH/ECH: duplicates in tilstand, voyages or anlop collapse silently; a null offset raises `TypeError` — medium. **patch**: `Inkonsistens` for each, tested, duplicate check mutation-confirmed.
- BH/ECH: NaN, or 102.3 called directly, passes F3/F7/F6 — low, direct fix. **patch**: `_gyldig_fart` and `_endelig`, tested.
- BH: the `main` stop path is untested — medium. **patch**: `test_main_stopper_uten_aa_skrive`, which checks exit 2 and that the old file is untouched.
- BH: the raw-ETD check is weak — low. **patch**: none of the fixture ETDs appears in 4 formats.
- BH: the test does not change a train row's own arrival — medium. **patch**: `test_egen_ankomst_endrer_ikke_egen_historikk`.
- BH: no code identification in `features.json` — low. **patch**: `kode_sha256` and `parametre`.
- BH/VG: epics named the wrong test for 102.3; the spec named a nonexistent `fartoyhistorikk()` — low. **patch**: docs.
- BH: the size was stated before the file existed; nothing enforced the budget — low. **patch**: wording, plus `test_committet_features` checks the total (post-fetch task).
- BH: the baseline offset is fitted on all of train — false. It is one constant per group, so F15 and its target shift by the same amount (decision 11, choice 5, also in the script docstring).
- BH: ETD may be an actual departure time — false as a new finding. It is already a recorded limitation (PRD §7, decision 11), measured by the F13–F14 ablation.
- BH: missing and rare categories share `annet` — false. Decision 11 locks it.
- BH: no code for the post-fetch checks — rejected. They are post-fetch tasks in the spec and epics.
- BH/ECH: `_skriv_par` is not atomic across the two `os.replace` calls — low, same as E2-S03. It is detectable through `utdrag_sha256`.
- ECH: an unexpected `split` value or a non-numeric voyageid — false. The locked `anlop.csv` has only train/test and digit ids.
