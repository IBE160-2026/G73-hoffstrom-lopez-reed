---
title: 'E1-S03 — Datalag'
type: 'feature'
created: '2026-10-22'
status: 'done'
baseline_commit: '68a9f76426c37d375d1d1cd59985c7a95269a17a'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/docs/arkitektur.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The committed extract `data/utdrag/anlop.csv` (E1-S02) is plain text with mixed timestamp formats. The predictor (E1-S04), metrics (E1-S05) and views (E1-S06+) need typed port calls with correct UTC times and a single, tested definition of "calls in the next 24 hours from «nå»".

**Approach:** Add `app/data.py` with a frozen dataclass `Anlop`, `last_utdrag()` and `anlop_i_vindu(naa, timer=24, vis="alle")`, as in `docs/epics.md` E1-S03 and architecture §5. Times are tz-aware UTC; a timestamp without suffix is read as UTC. The window is half-open on reported ETA: [naa, naa + timer). Calls with `status_in_area` ≠ `ok` get `faktisk_ankomst = None`. Tests in `tests/test_data.py` on a hand-made fixture, plus a check that the real extract gives the 15 / 9 calls the later stories rely on.

## Boundaries & Constraints

**Always:** stdlib + existing deps only; Python 3.9 (`datetime.fromisoformat` does not accept `Z`). Group naming as in the glossary: `Passasjer` when `ship_group == "Passasjer"`, otherwise `Øvrige`; `vis` values `alle` / `passasjer` / `ovrige`. Keep the raw `ship_group` (Tank, Last, …): the list shows it. Data is read once and cached; tests can pass their own path or list.

**Never:** sort by predicted arrival (that is E1-S06, which owns the predictor); compute deviation or `er_forsinket` (E1-S05/S09); load the extract from `pipeline/data/`; wire data into `create_app()` or routes (E1-S06); accept a naive `naa` silently.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ETA exactly at `naa` | fixture row with `eta == naa` | included | N/A |
| ETA exactly at `naa + 24 t` | fixture row | excluded | N/A |
| ETA one second before `naa` | fixture row | excluded | N/A |
| Filter | `vis="passasjer"` / `"ovrige"` / `"alle"` | only that group / all | N/A |
| Unknown filter | `vis="rutegaende"` | — | `ValueError` naming valid values |
| Naive `naa` | `datetime(2025,10,8,8)` | — | `ValueError` |
| `naa` in Oslo time | `08:00+02:00` | same window as `06:00Z` | N/A |
| Arrival without suffix | `2025-10-08T11:18:10` | `2025-10-08T11:18:10+00:00` | N/A |
| Status not `ok` | `empty`, `not_detected`, `avkortet_av_neste_seilas` | `faktisk_ankomst is None`, status kept | N/A |
| Real extract, default window | `naa` = 08.10.2025 08:00 Oslo | 15 calls; 9 with `vis="ovrige"`; 7 826 rows loaded | N/A |

</frozen-after-approval>

## Code Map

- `data/utdrag/anlop.csv` -- source; columns `voyageid, mmsino, shipname, ship_group, eta_reported, arrival_in_area_utc, status_in_area, split`. `eta_reported` always ends `+00:00`; `arrival_in_area_utc` is 19 chars without suffix when status is `ok`, empty otherwise (verified on all 7 826 rows).
- `scripts/lag_utdrag.py:til_utc_z` -- existing "no suffix = UTC" rule; same semantics, do not import a script into `app/`.
- `tests/conftest.py` -- `app`/`client` fixtures; add nothing app-related here.
- `tests/fixtures/` -- add `anlop_mini.csv` (architecture §8 names it) in the extract format.
- `pytest.ini` -- `pythonpath = .`, so `from app.data import …` works.

## Tasks & Acceptance

**Execution:**
- [x] `app/data.py` -- `Anlop` (frozen dataclass: `voyageid:int, mmsino:int, shipname:str, ship_group:str, eta_reported:datetime, faktisk_ankomst:Optional[datetime], status_in_area:str, split:str`, property `gruppe`), `GYLDIGE_VIS`, `STANDARD_UTDRAG` path, `last_utdrag(sti=STANDARD_UTDRAG) -> tuple[Anlop, ...]` (cached per path), `anlop_i_vindu(naa, timer=24, vis="alle", anlop=None) -> list[Anlop]` sorted by `(eta_reported, voyageid)`.
- [x] `tests/fixtures/anlop_mini.csv` -- ~10 rows covering both groups, all four statuses, and ETAs at, just before and exactly 24 h after a chosen `naa`.
- [x] `tests/test_data.py` -- one test per matrix row.
- [x] `docs/epics.md` -- E1-S03 → ✅.

**Acceptance Criteria:**
- Given the committed extract, when `last_utdrag()` is called twice, then the file is parsed once (same object returned).
- Given any loaded `Anlop`, then `eta_reported.tzinfo` and (when present) `faktisk_ankomst.tzinfo` are UTC.

## Design Notes

`anlop=None` keeps the epics signature while letting tests and later stories pass a list. The default window number (15 / 9) is asserted here because E1-S06 and E1-S08 depend on it; if the data layer disagrees, it should fail now, not in a route test.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green (12 existing + new), < 1 min

## Implementation Notes (post-review)

- Review patch for `timer`: the orchestrator's requested expectation ("timer=6 → 12:00 in") contradicted the half-open window in this spec. The implementer flagged it instead of bending the code. The final test asserts both `timer=6 → [1003, 1004]` (12:00 out) and `timer=7 → [1003, 1004, 1005, 1006]`.
- Mutation check (with a control run on unchanged code): the suite fails when `timer` is hard-coded to 24 h (1 failing), when the end bound is closed `<=` (4 failing), and when ground truth comes from the arrival field instead of status (1 failing).

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG).

- VG gap + BH: `timer` never tested off-default; a hard-coded 24 h passes all tests — medium, pre-verified. **patch**: `test_timer_styrer_vindusslutt` (timer=6).
- VG other + BH: no fixture row separates "status ≠ ok" from "arrival empty"; a regression to `if ankomst` passes — medium, real (spec rule is status-based). **patch**: fixture row with non-ok status and filled arrival.
- BH: `GYLDIGE_VIS` and the inline group dict can drift; a new value silently filters as "alle" — low, real, trivial fix. **patch**: single mapping, `GYLDIGE_VIS` derived.
- BH + VG other: `Z` and non-zero offset branches of `_til_utc` never run — low, real, test-only fix. **patch**: parametrised test.
- BH: real-data test misses `passasjer` = 6 — low, real, one line. **patch**.
- Orchestrator: fixture `ship_group` "Fiske" does not exist in real data ("Fisk") — low, cosmetic. **patch**.
- BH/ECH: `ok` with empty arrival loads silently as None; should raise — low, rejected: 0 of 7 826 rows (verified at planning); fix adds a guard for an unseen state.
- BH/ECH: malformed rows give context-free `KeyError`/`ValueError`; BOM; lowercase `z`; whitespace/casing in `ship_group`; odd fractional seconds — low, rejected: the only input is our own generated extract (format verified); guards add branches.
- BH/ECH: `timer` ≤ 0 returns empty instead of raising — low, rejected: no caller passes it; routes fix `timer` (E1-S06).
- BH/ECH: `lru_cache` never reloads when the file changes — low, rejected: the extract changes only by commit; restart is the normal reload (docstring says "parses én gang").
- BH: story marked ✅ before review; spec untracked — false: ✅ and spec land in the story commit after review, per epics rules.
- BH: `tzinfo is UTC` relies on CPython internals — false: `_til_utc` always sets `dt.timezone.utc` itself (`replace`/`astimezone`), so identity is guaranteed by our code.
