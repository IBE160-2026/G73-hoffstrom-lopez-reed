---
title: 'E1-S04 — Prediktor-grensesnitt og kalibrert baseline'
type: 'feature'
created: '2026-10-22'
status: 'done'
baseline_commit: '038f260db52e54c83463eed20417bee90051fc94'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/docs/arkitektur.md'
  - '{project-root}/docs/beslutninger/08-horisont-kuttes-pa-rapportert-eta.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The predictor contract in architecture §3 hands predictors `Anlop` objects, which carry `faktisk_ankomst` and `status_in_area`. Leakage is only *forbidden*. Any future model could read the ground truth by accident, and nothing would fail.

**Approach:** Make leakage impossible by construction. Predictors receive only a `PrediksjonsInput`: a frozen value holding what is known at prediction time (identity, group, reported ETA, horizon, cut time). It has no field and no reference that leads to ground truth. A single boundary function builds inputs from `Anlop`, and it is the only prediction code allowed to touch the data layer. On top of that: `Prediksjon`, the `Prediktor` protocol, `velg_prediktor()`, and `BaselinePrediktor` (`predikert = eta − offset[gruppe]`, never warns). A parametrised contract test runs against every predictor and proves that ground truth cannot change a prediction.

**Group requirements (22.10.2026):**
1. Leakage must be impossible per construction, not just forbidden: no actual arrival, no ground-truth status, no AIS after the cut. A test must prove it.
2. The contract must not lock the dashboard to selecting calls by reported ETA. Whether S06 selects on reported or predicted arrival is an open decision for E1-S06 (Design Notes).

## Boundaries & Constraints

**Always:**
- `PrediksjonsInput` fields: `voyageid, mmsino, shipname, ship_group, gruppe, eta_reported, horisont_timer, t_kutt`.
- Horizon from reported ETA: 6 if `eta − naa ≤ 6 t`, else 24 (PRD FR2).
- `t_kutt = min(eta − H, naa)`. Under today's selection this equals `eta − H` (FR9a). It never exceeds `naa` under any selection.
- Offsets are read from `data/baseline.json`, unrounded. `predikert_ankomst` is tz-aware UTC at full precision. Display rounding is E1-S06's call.
- `forklaring` contains `metode`, `gruppe`, `offset_minutter`.
- Python 3.9.

**Never:**
- A field, property or method on the input that exposes `faktisk_ankomst`, `status_in_area`, `split`, or the `Anlop` object.
- A predictor module (`app/prediksjon/*.py` except the boundary) importing `app.data`, or reading `data/utdrag/`.
- Deviation or `er_forsinket` inside a predictor (they belong to `metrikker.py`, against the baseline).
- Route or template changes (E1-S06).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| BERGEN ENERGY | Tank, ETA 09:00Z, `naa` 06:00Z | `predikert` 07:55:48Z (09:55:48 Oslo); H = 6; `forventet_forsinket is None` | N/A |
| Passasjer offset | ETA 12:00Z | `predikert` = 12:00 − 44.75 min | N/A |
| Horizon edge | `eta − naa` = 6 t exactly / 6 t + 1 s | H = 6 / H = 24 | N/A |
| ETA > 24 t ahead | `eta − naa` = 30 t | H = 24, `t_kutt == naa` (not after) | N/A |
| Cheating predictor | reads `inp.faktisk_ankomst` / `inp.status_in_area` | — | `AttributeError` |
| Ground truth altered | same calls, `faktisk_ankomst`/status changed via `dataclasses.replace` | every predictor returns identical predictions | N/A |
| `PREDIKTOR` | unset / `auto` / `baseline` / `modell` / `tull` | baseline / baseline / baseline / baseline (no model artifact in E1) / `ValueError` naming valid values | fail at selection |

</frozen-after-approval>

## Code Map

- `app/data.py` -- `Anlop`, `anlop_i_vindu`. Read-only for this story. The boundary imports `Anlop` from here.
- `data/baseline.json` -- `offset_minutter` {"Passasjer": 44.75, "Øvrige": 64.2}.
- `docs/arkitektur.md` §3 -- the contract text and its changelog. Changing it requires a changelog line and both owners' approval in the PR.
- `docs/epics.md` E1-S04 / E2-S07 -- `test_kutt_ikke_etter_naa` moves into this story's contract test.

## Tasks & Acceptance

**Execution:**
- [x] `app/prediksjon/__init__.py` -- `PrediksjonsInput`, `Prediksjon` (as §3), `Prediktor` Protocol (`navn`, `kan_varsle`, `prediker(inputs: Sequence[PrediksjonsInput], naa) -> list[Prediksjon]`), `lag_input(anlop, naa)` (the only `app.data` boundary), `velg_prediktor()`.
- [x] `app/prediksjon/baseline.py` -- `BaselinePrediktor` (navn «Kalibrert baseline», `kan_varsle = False`). Offsets are loaded once from `data/baseline.json`.
- [x] `tests/test_prediktor_kontrakt.py` -- parametrised over a `PREDIKTORER` list. It covers:
  - the input has no ground-truth field
  - a cheating predictor gets `AttributeError`
  - predictions are identical under altered ground truth
  - `t_kutt ≤ naa` for every input built from the real extract at 20 spread `naa` values in the test period
  - an AST check that predictor modules do not import `app.data` or reference `utdrag`
- [x] `tests/test_baseline.py` -- BERGEN ENERGY, Passasjer offset, horizon edges, `velg_prediktor` matrix.
- [x] `docs/arkitektur.md` -- §3 updated to the input-based contract, plus a changelog line. `docs/epics.md` -- E1-S04 → ✅, and `test_kutt_ikke_etter_naa` is noted as moved from E2-S07.

**Acceptance Criteria:**
- Given any future predictor added to `PREDIKTORER`, when the contract test runs, then it must pass the same leakage tests before it counts as done.
- Given the route code of E1-S06, then it can only reach a predictor through `lag_input`. There is no overload that accepts `Anlop`.

## Design Notes

**What "impossible by construction" means here.** Python cannot stop deliberate code from opening a file. The guarantee therefore has two parts:
- **The interface:** a predictor has no path to ground truth.
- **A failing test:** an accidental import or file read is caught.

Together they rule out cheating by mistake, which is what the group asked for.

**Why `t_kutt = min(eta − H, naa)`.** Today this is identical to FR9a. It also keeps the contract safe if S06 ever asks for predictions on calls more than 24 t ahead. In that case the cut is clamped to «nå», and no future AIS can be read. If option B below is chosen, FR9a needs that sentence added.

**Open decision for E1-S06: what the 24 t window selects on.** This is not decided in this story. The contract supports both options.
- **A — Reported ETA in [nå, nå + 24 t) (today, PRD FR2).**
  - Pros: simple and stable. Every row has a defined 6/24 t horizon. The numbers 15 / 6 / 9 are already pinned.
  - Cons: once the model exists, a ship reported 25 t out but predicted 20 t out is not shown. A ship whose reported ETA has passed but is predicted late also drops out. Those are exactly the delays the havnevakt cares about.
- **B — Predicted arrival in [nå, nå + 24 t).**
  - How: predict a wider candidate set, for example reported ETA in [nå − X, nå + 24 t + Y), then filter on prediction.
  - Pros: shows what the havnevakt actually needs.
  - Cons: rows beyond 24 t have no trained horizon. They would use the cut at «nå» with a baseline fallback, or need a third horizon. The window count depends on the active predictor, so 15 / 9 change when the model is swapped in. X and Y must be chosen and justified. PRD FR2, UX §2 and tests in S06/S08 change.
- **Recommendation:** decide in S06 with the group. A keeps v1 simple. B is the better product once the model warns. Choosing A now and B in E2-S08 is possible because the contract does not change.

**Display note for S06.** BERGEN ENERGY is 09:55:48 Oslo time. UX shows «09:55» (truncated). Rounding to the nearest minute gives 09:56. S06 must choose and test one rule.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green (31 existing + new), < 1 min.
- Mutation check with a control run on unchanged code: the leakage tests must fail when `PrediksjonsInput` gains a `faktisk_ankomst` field, when `BaselinePrediktor` reads ground truth via `app.data`, and when `t_kutt` drops the `min(…, naa)`.

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). Plus one finding from triage itself (T).

- T: §3 still says the model reads `tilstand_ved_kutt.csv`, which lives in `data/utdrag/` — the folder this same diff forbids predictor modules to read. The doc contradicts itself and would send E2-S07 into a failing AST check. medium, real. **patch**: state must come through the boundary, exact shape decided in E2-S07.
- BH + ECH (claim) + VG other: §3 says "umulig per konstruksjon" without the limit; the AST lint misses `importlib`/attribute access. medium (overclaim in a graded document), real. **patch**: one sentence on the limit (mistakes, not intent), as in Design Notes. Detecting dynamic imports is rejected: it guards deliberate code, which the intent explicitly excludes.
- VG gap + BH + ECH: `forklaring` documented as "minst metode, gruppe, offset_minutter" for every predictor, test checks only `metode`; `offset_minutter` is baseline-only. medium, pre-verified. **patch**: doc says `metode` + `gruppe` for all, `offset_minutter` for baseline; contract test asserts `metode` + `gruppe`.
- BH: §3 shows `velg_prediktor()` without `verdi`; the `TypeError` rule required by the contract test is undocumented. low, real, doc-only. **patch**.
- BH + ECH: naive `eta_reported` is silently read as host-local time in `lag_input`, while a naive `naa` raises. low (data layer always gives tz-aware), direct fix reusing `_til_utc`. **patch** + test.
- ECH + VG other: whitespace-only `PREDIKTOR` raises instead of falling back to `auto`; normalisation untested (VG filed as defer). low, real, one-line reorder. **patch** + parametrised cases (absorbs the VG defer).
- BH + ECH: `offset_minutter` dict shared through `lru_cache` across instances. low, real, one-token fix. **patch** (`dict(...)`).
- BH + ECH: AST check globs only top level of `app/prediksjon/`. low, real, one-word fix. **patch** (`rglob`).
- ECH: `test_mini_fixture_far_riktig_gruppeoffset` passes vacuously on an empty window. low, real. **patch** (`assert inputs`).
- BH + ECH: unknown `gruppe` gives bare `KeyError`. **false**: `Anlop.gruppe` is a property mapping `ship_group` to Passasjer/Øvrige, so no other key is reachable; a loud KeyError on an edited JSON is correct.
- ECH: `baseline.json` missing/malformed raises at construction. **false**: loud failure on a committed file is correct behaviour.
- ECH: hashing `Prediksjon` raises `TypeError` (dict field). **false** for this story: nothing hashes it, and the `dict` field is pre-existing contract text.
- BH: `__init__.py` excluded from AST check. **false**: it is the boundary and the only module allowed to touch `app.data`, by spec.
- BH: `PREDIKTOR=modell` silently returns baseline. **false**: frozen matrix specifies exactly this for E1; E2-S08 owns the fallback message.
- BH: `forklaring` holds a raw `datetime`, not JSON-serialisable for E3. **false**: no consumer serialises it; E3-S02 builds its own input. Rejected without change.
- BH: `_endre_fasit` never changes `split`; no `_JukserSplit`. **false**: `test_input_har_bare_kjente_felt` and the `FASITFELT` check already prove `split` is unreachable.
- BH: fasit-change test is partly circular. **false**: by design; documents the input-level guarantee, the AST test covers the other path.
- BH: `TEST_FRA` hard-coded instead of read from `baseline.json`. low, rejected: drift only shifts the sample period, the assertion stays valid.
- BH: behaviour for past ETA unspecified. **false**: the spec rule `eta − naa ≤ 6 t → 6` covers negative deltas; `t_kutt ≤ naa` holds and is tested.
- BH: E1-S04 marked ✅ before PR approval. **false**: project rule sets ✅ in the story commit; PR approval is the merge gate.
- BH: moving `test_kutt_ikke_etter_naa` weakens E2-S07; ECH (claim): AIS-after-cut not proven for E2. Real but E2's: no AIS exists in E1, and the input has no AIS field. **defer** to E2-S03/S07 (covered by the T patch above and `deferred-work.md`).
- ECH: `max()` on empty test split / empty mini window in `test_tar_ikke_anlop_direkte`. **false**: both fail loudly, never pass vacuously.
- BH: spec untracked; no notater entry. **false**: spec is committed with the story; triage found one AI error (T), logged in `docs/refleksjon/notater.md`.
