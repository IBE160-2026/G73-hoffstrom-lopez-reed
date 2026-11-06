---
title: 'E2-S02 — Målrettet AIS-henting ved kuttpunktene'
type: 'feature'
created: '2026-11-03'
status: 'in-progress'
baseline_commit: 'f867bf48b3be6c140b02b1177cb910e9166469cb'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/docs/beslutninger/09-ais-dekning-ved-kuttpunktene.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The locked AIS cache rarely has a position at `t_H = reported ETA − H` (7 % at 24 h, 31 % at 6 h for Øvrige/test), so no state can be built for the model. Kystdatahuset also shifts requested windows by +1/+2 h and can truncate them at midnight, so a naive fetch leaks points after `t_H`.

**Approach:** New `pipeline/fetch_ais_kutt.py`. It makes one API call per voyage with ≥ 1 day margin around both horizon windows, filters the response on its own UTC timestamps (`filtrer_til_vindu`) into [`t_H` − 24 h, `t_H`] for H ∈ {6, 24}, and caches only the filtered points, one file per voyage. It is resumable, paced, and retries failed calls. A 50-voyage pilot measures time and disk use, and the full run waits for Felipe's go.

## Decisions (Felipe, 2026-11-03, at approval)

1. **Hard ceiling ETA − 6 h.** The request window [ETA − 72 h, ETA + 18 h] stands, but the cache must never contain a point later than the latest cut point, `t_6` = ETA − 6 h. Such points are close to the ground truth and are dropped before writing, whatever the API returns. This is a separate guard on top of the per-horizon filter, and a test proves it. The test is shown to fail when the guard is removed (mutation check).
2. **Commits:** code and tests are committed after the pilot, as the E2-S02 commit. The coverage table is committed separately when the full run is done.
3. **Commit author:** commits in this session use `--author` with Felipe Knudstad-Lopez and the e-mail he provides.
4. **Full run:** started with `caffeinate -i`, after Felipe has seen the pilot estimate. Felipe gets the commands to follow progress, to stop, and to resume.

## Boundaries & Constraints

**Always:**
- The window is computed only from `eta_reported`. The input reader keeps `voyageid, mmsino, ship_group, eta_reported, split` from `data/utdrag/anlop.csv` and drops every other column.
- Every point written to cache has a timestamp in [`t_H` − 24 h, `t_H`], inclusive.
- Request window: [`eta` − 72 h, `eta` + 18 h], that is 24 h before `t_24`'s lookback start and 24 h after `t_6`. It always spans more than one day, which avoids the midnight truncation (finding B).
- Stdlib only. Python 3.9.
- Host: `https://kystdatahuset.kystverket.no/ws/api/ais/positions/for-mmsis-time`.
- 1.0 s pause after each call. On URLError, HTTP error, timeout, invalid JSON or `success=false`: retry up to 3 times with 5 / 15 / 45 s backoff. After 10 voyages in a row fail, stop with a clear message.
- Cache files are written atomically (temp file + `os.replace`). A voyage with a cache file is never fetched again. A failed voyage gets no cache file and is retried on the next run. An empty answer is cached with `status: "tom"`, and `--prov-tomme` re-fetches those.
- Every call is appended to `pipeline/data/ais_kutt_logg.csv`. Coverage per horizon × group × split is written to `pipeline/data/ais_kutt_dekning.csv` after every run, from the cache alone. Columns: n, fetched, with a position in the 24 h lookback, with a position ≤ 1 h before `t_H`, and shares.
- `--utvalg N --seed S` runs a random pilot. Afterwards the script prints elapsed time, s/voyage, cache bytes per voyage, and an estimate of time and disk use for the remaining voyages.

**Never:**
- Write to `data/`, `pipeline/data/ais_cache/`, `pipeline/data/bergen_eta_avvik.csv`, the other existing `pipeline/data/*` files, or `pipeline/fetch_ais.py`. Only these new paths may be written: `pipeline/data/ais_kutt_cache/`, `ais_kutt_logg.csv` and `ais_kutt_dekning.csv`.
- Read `arrival_in_area_utc`, `status_in_area` or any other arrival field. Network access in tests. Starting the full run before Felipe has seen the pilot estimate.
- Building the state extract. That is E2-S03.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal | voyage, answer shifted +1 h | cache has `"6"` and `"24"` lists, every timestamp in [`t_H` − 24 h, `t_H`] | N/A |
| Point after cut | answer has `t_6` + 1 s | not in `"6"` list (may be in neither) | N/A |
| Actual arrival changed | same row, other `arrival_in_area_utc` | identical request window and cut points | N/A |
| Already cached | cache file exists | no API call | N/A |
| Empty answer | `data: []` | cached `status: "tom"`, counted as without position | `--prov-tomme` re-fetches |
| API failure | 3 retries fail | no cache file, `feil` row in log | retried next run. 10 in a row → stop |
| Interrupted | Ctrl-C / kill | no partial cache file | rerun continues |

</frozen-after-approval>

## Code Map

- `pipeline/sjekk_ais_dekning_kutt.py:62` -- `filtrer_til_vindu(svar, fra, til)`, tested by `tests/test_ais_filter.py`. Copy the function into the new script (the source imports locked `fetch_ais` and patches its global). Keep the name and semantics. Parse timestamps robustly: strip a tz suffix and fractional seconds.
- `pipeline/fetch_ais.py` -- locked: `main()` exits. Reuse only its ideas: `to_kdh_time` format `%Y%m%d%H%M`, the POST body shape and the cache/log layout. Do not import it.
- `data/utdrag/anlop.csv` -- 7 826 rows (train 6 260 / test 1 566). `eta_reported` has `+00:00`. Make it naive UTC.
- API row columns: 0 mmsi, 1 UTC time `YYYY-MM-DDTHH:MM:SS`, 2 lon, 3 lat, 4 cog, 5 sog, 7 calc_speed.
- `tests/test_ais_filter.py` -- pattern for loading a `pipeline/` script with `importlib` in tests.

## Tasks & Acceptance

**Execution:**
- [x] `pipeline/fetch_ais_kutt.py` -- CLI `--utvalg`, `--seed`, `--prov-tomme`, `--kilde`, `--cache-dir`, `--pause` -- the fetcher above. Docstring cites decisions 08/09, the run commands and `caffeinate -i`.
- [x] `tests/test_fetch_ais_kutt.py` -- `test_vindu_fra_rapportert_eta`, `test_filtrerer_bort_punkter_etter_kutt` (fake fetch through the cache-writing path, checks the file on disk), `test_leser_ikke_ankomstfelt`, `test_hopper_over_cachet`, `test_feil_gir_ingen_cache`, `test_tomt_svar`, `test_ingenting_etter_eta_minus_6t` (mutation-checked), `test_dekningstabell`. All tests use `tmp_path` and a monkeypatched fetch, with no network.
- [ ] Pilot (done 2026-11-03, see Implementation Notes); full run waiting for Felipe's go: `--utvalg 50 --seed 2`, then report time, disk use and estimate to Felipe. After his go: full run in the background with `caffeinate -i`.
- [ ] `docs/epics.md` -- E2-S02 → ◐ in the code commit, then → ✅ in the separate coverage commit after the full run. The coverage table goes in the session log and in the Implementation Notes.

**Acceptance Criteria:**
- Given the full test suite, when `pytest` runs without network and without `pipeline/data/`, then it is green, `test_dataregresjon.py` is unchanged and still passes, and the run takes < 1 min.
- Given a finished run, when `ais_kutt_dekning.csv` is read, then it has 2 horizons × 2 groups × 2 splits, and the 24 h lookback coverage at `t_24` for Øvrige/test is in the range decision 09 predicts (≈ 93 % ± 8 pp). If it is not, investigate before E2-S03.
- Given `git status` after the run, then no tracked file changed except the story's own files.

## Design Notes

One call per voyage, not one per horizon, halves the calls (~7 826). The two lookbacks overlap, so the call covers both with margin. All voyages are fetched, including the 935 `empty` ones: choosing voyages would mean reading arrival fields, and E2-S03 needs one row per voyage and horizon anyway.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `caffeinate -i python3 pipeline/fetch_ais_kutt.py --utvalg 50 --seed 2` -- expected: 50 voyages processed, estimate printed
- `git status --porcelain` -- expected: only the new script, test and spec

## Implementation Notes

- 2026-11-03: implemented directly in the main session, which already held the full context. Review ran as three independent subagents.
- Mutation checks were run by hand: each mutation was applied, the tests were run, and the file was restored. Each mutation is caught: removing the cap or moving it to ETA fails `test_ingenting_etter_eta_minus_6t`. Letting the window filter pass everything fails `test_filtrerer_bort_punkter_etter_kutt` and `test_dekningstabell`. Shifting the request window fails `test_vindu_fra_rapportert_eta`. Removing the failure-streak reset fails `test_feil_pa_rad_nullstilles`.
- **Pilot, 2026-11-03** (`--utvalg 50 --seed 2`): 49 fetched (41 ok, 8 empty) and 1 failure, in 4.3 min. A call takes 2.7 s at the median (max 4.2 s), and an answer has 12 600 points at the median (max 43 000). The cache is 724 kB per voyage, 35 MB in total. Estimate for the remaining 7 777: about 8 h at ~3.8 s per voyage (the script's own figure of 11.3 h includes the failed voyage's 65 s backoff), and about 5.6 GB of disk.
- **Pilot finding:** the API answers `success=false`, `42P01: relation "ais202410.ais_20241028" does not exist` for voyage 2690405, because a day table is missing on the server side. Such failures now fail fast and are not retried (`varig=True`, `test_manglende_dagstabell_uten_gjentak`). They stay uncached and are logged as `feil: mangler hos API-et`, and the full run reports how many there are.
- Pilot coverage, too small to conclude from: within 24 h lookback, Øvrige 68 % (23/34) at both horizons and Passasjer 100 % / 93 %. Decision 09's ≈ 93 % counted only voyages with AIS in the original fetch. The pilot includes 8 empty answers, so the shares are not comparable until the full run.

## Spec Change Log

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). They ran in parallel with the pilot. No finding touched the filtering semantics, so the pilot cache stays valid.

- VG: `hent_posisjoner` untested (body, format, retries) — medium, pre-verified. **patch**: `test_hent_posisjoner_kropp_og_gjentak`, `_gir_opp`, `_4xx_uten_gjentak`.
- VG: the failure streak reset is not pinned — medium, pre-verified (mutation confirmed: removing `pa_rad = 0` passed every test). **patch**: `test_feil_pa_rad_nullstilles`.
- VG: `--utvalg`/`--seed` untested — medium, pre-verified. **patch**: `test_utvalg_er_deterministisk_og_hopper_over_cachet`.
- VG: the SIGTERM/Ctrl-C path through `main` is untested — low, but the test is cheap. **patch**: `test_avbrudd_skriver_dekning_og_kan_fortsette`.
- BH/ECH: non-dict payload, non-list `data`, and `http.client.HTTPException` escape the retry and crash the run — medium. **patch**: they are mapped to `HenteFeil`.
- BH: 4xx is retried with full backoff, so 10 bad requests in a row cost about 11 min — low. **patch**: fail fast on 4xx except 429.
- BH/ECH/VG: unreadable timestamps were counted as `kastet_etter_tak`, and a format change would cache everything as `ok` with no points — medium. **patch**: separate `uleselige` count, and an all-unreadable answer raises `HenteFeil`, so nothing is cached and it is retried later. The pilot shows a single format, `YYYY-MM-DDTHH:MM:SS`.
- ECH: a regex-valid but impossible date raises `ValueError`, and dict points raise `KeyError` — low, direct fix. **patch**: both caught in `tidsstempel`, so the point is dropped.
- BH: the safety check is an `assert`, which `python -O` removes — low, direct fix. **patch**: explicit `RuntimeError`.
- BH/ECH/VG: `skriv_atomisk` leaves `.tmp` behind, and the test name claimed otherwise — low, direct fix. **patch**: the tmp file is removed on any exception, and the test asserts an empty directory.
- ECH/VG: `skriv_dekning` raised `IndexError` on an empty source — low, direct fix. **patch**: fixed `DEKNING_KOLONNER`, plus `test_tom_kilde`.
- BH: a truncated answer is cached as `ok` and never refetched — maybe-false. Decision 09 saw truncation only on short windows (< 1 day) ending just after midnight, and ours are 90 h. A silent ship and a truncated answer cannot be told apart without the raw answer. **defer**.
- BH: `status` follows the raw answer, not what survives the cap — false as a defect: `tom` marks "API gave nothing" so that `--prov-tomme` can retry it. A ship with points only after ETA − 6 t has no state, and a retry would not change that.
- BH: the request runs to ETA + 18 h — rejected: this is the window Felipe approved (decision 1). The cap guarantees nothing after ETA − 6 h is stored.
- BH: no schema/parameter version in the cache — low, rejected: there is one writer and one format, and E2-S03 reads `t_kutt_utc`/`fra_utc` from each file.
- BH/ECH: `int(mmsi)` or `naive_utc(eta)` crash on bad rows; duplicate voyageids — false: all 7 826 rows checked: MMSIs are digits, ETAs parse, 0 duplicate ids.
- ECH: voyageid path traversal — false: every id is digits only.
- BH: unstable sort of the coverage rows — false: split ∈ {train, test} only.
- ECH: odd-shaped cache JSON raises `KeyError` in `dekning` — false: the only writer is `bygg_cache`.
- BH: relative default paths; pilot not stratified — low, rejected. Run from the repo root as documented, like the other pipeline scripts. 50 random draws over a 25 % Passasjer share is enough for a time and disk estimate.
- ECH: interrupt during the post-loop block; log row missing if killed between cache write and log write; negative `--utvalg`; space-separated timestamps — low/false, rejected. The cache is the source of truth, the log is informative, and the pilot shows the `T` format.

### Review Findings (code review of 0a85cd4, 2026-11-05)

Four layers (Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor) reviewed the missing-day-table fix. All findings below were checked against the live cache, read-only, on 2026-11-05. 28 voyages had been split, all of them on a single day (30.07 or 28.10). There were 0 failures since the restart. API duplicate rows: 0 in 200 unsplit voyages (1.79 M points). **None of the findings requires re-fetching cached voyages.** Felipe decided: B1 deferred, B2 fixed now. The six patches below wait until the running full fetch finishes, because `fetch_ais_kutt.py` must not change during the run.

- [x] [Review][Decision] Permanent data holes have no status of their own — deferred (Felipe 2026-11-05). See deferred-work.md.
  - A voyage that cannot be split is never cached, so it is retried on every run and looks like downtime in the coverage table. This happens when the day is unreadable, the day lies outside the window, or `MAKS_DELINGER` is hit.
  - The opposite case: a voyage with a hole is cached as `ok` and is never refetched, even if Kystdatahuset later adds the table.
  - Affects cached voyages: no. 0 such failures so far.
- [x] [Review][Decision] `lag_tilstand.py` ignored `manglende_dager` — fixed (Felipe 2026-11-05, E2-S03 commit).
  - Cut points inside the lost interval got `ais_status=ok`, with a position from before the hole and an artificially high age.
  - They now get `manglende_dag` and go to the baseline. The fix is mutation-checked.
  - Affects cached voyages: yes, 8 cut points in 28 voyages. Solved downstream, with no re-fetch.
- [x] [Review][Patch] Stop-rule exemption is too broad. Any "does not exist" message becomes `ManglerDag`, even with no readable day, so a systematic API break would never stop the run. Exempt only a `ManglerDag` with a readable day. Count unsplittable re-raises (repeat day, outside window, `MAKS_DELINGER`) as ordinary failures. [pipeline/fetch_ais_kutt.py: hent_posisjoner, hent_med_hull, main] — medium. Cached voyages: not affected.
- [x] [Review][Patch] No test covers the guards against endless splitting: the same day returning after a split, and `MAKS_DELINGER`. Add a stub that always raises the same day: it must raise after one split, with exactly 3 calls. [tests/test_fetch_ais_kutt.py] — medium. Cached voyages: not affected.
- [x] [Review][Patch] No 1 s pause between the sub-calls of a split voyage. They run as 3 or more back-to-back calls. [pipeline/fetch_ais_kutt.py: hent_med_hull] — low. Cached voyages: not affected (only load on the API).
- [x] [Review][Patch] The dedup in `hent_med_hull` is effectively dead code. Sub-windows cannot overlap by construction, and the API sends no duplicates. It also makes split and unsplit voyages behave differently. Remove it. [pipeline/fetch_ais_kutt.py: hent_med_hull] — low. Cached voyages: not affected (0 duplicates).
- [x] [Review][Patch] The windows are extended outward, so `antall_i_svar` and `kastet_etter_tak` count points outside the original request window. Clip the merged answer to `[start, slutt]` before `bygg_cache`. [pipeline/fetch_ais_kutt.py: hent_med_hull/behandle] — low. Cached voyages: metadata in the 28 split files only. Horizon positions are unaffected.
- [x] [Review][Patch] Two tests are missing. One should pin the +2 h end of `tapt_intervall` in the coverage count, with a lookback starting 31.07 00:00–02:00. The other should run `dekning` on an old-format cache with no `manglende_dager`. [tests/test_fetch_ais_kutt.py] — low. Cached voyages: not affected.
- [x] [Review][Defer] The call log still shows the original window. It does not record the sub-windows, the number of calls or the missing days. [pipeline/fetch_ais_kutt.py: behandle, LOGG_KOLONNER] — deferred: changing columns in a CSV that is already half-written during a run. The days are in the cache and in `ais_kutt_dekning.csv`.

**The six patches, done 2026-11-06 after the full run (Felipe):**
- Stop rule: `hent_med_hull` turns every missing day it cannot split into an ordinary `HenteFeil`, so it counts toward the stop rule. A missing day with a readable day is split and fetched, so it never reaches `main`, and the exemption in `main` is gone. Tests: `test_manglende_dag_som_ikke_kan_deles_teller_mot_stoppregelen`, `test_delt_manglende_dag_teller_ikke_mot_stoppregelen` and `test_delt_seilas_nullstiller_stoppregelen`. The two old tests that pinned the broad exemption were replaced.
- Guards: `test_samme_dag_etter_deling_gir_opp` and `test_maks_delinger`. The finding said "exactly 3 calls", but the right number is 2: the first sub-window already returns the same day, and the code gives up there.
- Pause: `hent_med_hull` sleeps `pause` (default `PAUSE_SEK`, `--pause` from `main`) before each sub-call. Test: `test_pause_mellom_delkall`.
- Dedup removed. Test: `test_delt_seilas_beholder_svaret_som_det_er`.
- Clipping: the merged answer is clipped to `[start, slutt + API_FORSKYVNING_MAKS]`, not `[start, slutt]` as the finding says. An unsplit voyage gets the request window shifted by up to +2 h, so clipping at `slutt` would make split and unsplit voyages count differently. Points with an unreadable timestamp are kept so `uleselige` still counts them. Test: `test_delt_svar_klippes_til_foresporselen`.
- Missing tests: `test_tapt_intervall_slutter_2t_inn_i_dagen_etter` (lookback start 31.07 01:59 counts, 02:00 does not) and `test_dekning_pa_cache_uten_manglende_dager`.
- Mutation check by hand, 7 mutations, all caught. They were: the old exemption, no same-day guard, no pause, dedup back in, no clipping, `API_FORSKYVNING_MAKS = 0`, and `c["manglende_dager"]` without a default.
- The 28 cached split voyages were not refetched. The clipping only changes the metadata, and the horizon positions are unchanged (see the finding).

**Rejected:**
- The lost interval should start 2 h before midnight — false. A probe that ends at 23:59 returns data up to 23:59:58 UTC of the day before.
- The middle part between two missing days can be shorter than 25 h — low. It needs two missing days at most 1 day apart, which has not happened. The fix would add complexity.
- All sub-windows inside holes are cached as `tom` — low. It would need about 4 missing days within one 90 h window.
- The outward extension can reach a missing day outside the original window — low. This has not been observed, and the coverage counts are still correct because they test overlap with the lookback.
- Commit message says "10 nye tester", but there are 9 — low. The commit is pushed, so this is noted in the session log instead.
- "Only the missing day is lost", but the real loss is 26 h — rejected as a code finding, because the fix is documentation. It is now recorded in decision 09 (addendum 2026-11-05).
