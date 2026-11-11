---
title: 'E2-S09 — Panel: modell mot baseline'
type: 'feature'
created: '2026-11-11'
status: 'done'
baseline_commit: '35d81b3e24baae141ce773b23698c184e2c1f343'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/ux/dashbord.md'
  - '{project-root}/docs/prd.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `data/modell/metrikker.json` (E2-S06) holds model and baseline numbers side by side, but nothing on screen shows them. FR10 asks for a panel with model vs. calibrated baseline per horizon, with precision, recall and F1 against the "alert everyone" reference, where a losing model is shown just as clearly as a winning one.

**Approach:** A panel on the main screen that only reads `metrikker.json` and computes nothing from extracts or predictions. Before the test run it shows the validation block, and after it the `test` block (Decision 1). For each horizon (6 t, 24 t) it shows these rows:
- Øvrige, model subset: model and baseline
- all Øvrige with delegation: model and baseline
- Passasjer: baseline only

Each row has ±30 min share with counts, and alert precision, recall and F1 next to "varsle alle". It also shows the model share of Øvrige calls.

## Boundaries & Constraints

**Always:**
- **Test rows (Felipe, 2026-11-10):** test-period rows are used only for what this spec states. Anything else means stop and ask first. The panel and its tests never compute model numbers on test rows. The model's test numbers exist only after E2-S10 writes them. Tests for the post-test-run view use a synthetic `metrikker.json` in `tmp_path`, never real test numbers.
- The panel reads `metrikker.json` only. Every number shown is a value from the file, rounded for display only. Shares are shown as % with one decimal and the count (`317/459`).
- `null` (baseline cannot alert) is shown as «kan ikke varsle», never as 0.
- The period label is always visible: which split the numbers come from, and how many calls have ground truth.
- Equal clarity: model and baseline use the same visual weight. Bars, where used, carry their value as text (UU, as E1-S12 plans). Colour is never the only carrier.
- The ablation (`ablasjon_uten_f13_f14`) is not shown in the panel. It belongs to the results note (E2-S10).
- Missing or unreadable `metrikker.json`, or a missing block: the panel says «Tall mangler» and the page still answers 200.

**Never:**
- Change `metrikker.json`, `scripts/evaluer.py`, the predictors, or the lock in `velg_prediktor`.
- Run `scripts/evaluer.py --test` or add model numbers for the test period by any route.
- Show `test_bare_baseline` next to validation model numbers. Mixing periods in one table is forbidden.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Before test run | real file, `testkjoringer = 0` | validation block, label «Validering (mai–sep 2025) — utviklingstall, ikke testresultat», no verdict | N/A |
| After test run | synthetic file, `testkjoringer = 1` with a `test` block | `test` block, period label «testperioden», bestått/ikke bestått per horizon on the model subset | N/A |
| Model wins | model `andel_30` > baseline | both values, same weight, difference in pp | N/A |
| Model loses | synthetic, model `andel_30` < baseline | both values, same weight, negative difference shown just as clearly | N/A |
| Baseline alert | `presisjon`/`recall`/`f1` = `null` | «kan ikke varsle» | N/A |
| Missing file/block | no file, or no `validering`/`test` key | «Tall mangler», page 200 | caught, no 500 |

## Decisions (Felipe, 2026-11-11, at approval)

1. **Validation now, test after E2-S10 (1A).**
   - Before the test run (`testkjoringer < 1`, the same `testkjoringer()` as the lock), the panel shows the `validering` block, labelled «Validering (mai–sep 2025) — utviklingstall, ikke testresultat».
   - The validation view shows the numbers and the model − baseline difference, with no bestått/ikke bestått verdict.
   - After the test run it shows the `test` block. The verdict per horizon is decided on the model subset (FR10): ±30 min share, model > baseline; alert F1, model > `varsle_alle`. A loss is shown with the same weight as a win.
2. **Main screen, right column (2A)**, where UX §2 places «Treffsikkerhet». On mobile (< 640 px) the panel comes after the list. The E1-S12 panel stays a KAN.
3. **Choices approved:** no ablation in the panel (E2-S10), Passasjer as one baseline-only row, `null` as «kan ikke varsle», and `test_bare_baseline` never next to validation model numbers.
4. Every commit has `--author "Felipe Knudstad-Lopez <feknu2660@himolde.no>"`, story ID first.

5. **«Systemet» on the all-Øvrige row (Felipe, 2026-11-11, before commit):** the all-Øvrige group shows the model plus the baseline for the calls the model is not used on. Its column header is «Systemet», and its difference lines say «systemet bedre/dårligere», never «modellen». Under the row it says: «De fleste forsinkelsene i all trafikk er turer inne i havneområdet, der modellen ikke brukes og baselinen ikke kan varsle. Modellutvalget er raden som viser modellen.» Tests: `test_all_ovrige_trafikk_er_systemet_ikke_modellen` and `test_panel_modell_mot_baseline`.

</frozen-after-approval>

## Code Map

- `data/modell/metrikker.json` -- keys `testkjoringer`, `validering`, `test_bare_baseline`, `treff_min`, `varsel_min`. Under `<split>.horisonter.{6,24}`: `ovrige_modellutvalg` / `ovrige_alle` with `modell`, `baseline`, `ablasjon_uten_f13_f14` (`andel_30`, `treff_30`, `n`, `varsel{presisjon,recall,f1,...}`), plus `varsle_alle`; `passasjer.baseline`; `andel_modellutvalg.med_fasit`; `antall`. `evaluer.py` writes the `test` block with the same shape (check `scripts/evaluer.py` `oppdater`).
- `app/prediksjon/__init__.py` `METRIKKER_FIL`, `testkjoringer()` -- reuse them for the path and the test-run state; do not duplicate.
- `app/__init__.py` `forside` -- passes the panel data to the template. The panel's read and shaping go into a new pure module (`app/panel.py`), not into the route.
- `app/templates/forside.html`, `app/static/style.css` -- add the panel. The table and the strip are unchanged.
- `tests/conftest.py` -- the autouse `testkjoringer = 0` and the test-row guard stay. The panel tests patch `METRIKKER_FIL` to synthetic files.
- `tests/test_ruter.py` -- `test_panel_modell_mot_baseline` (epics), and one test per matrix row.
- `docs/ux/dashbord.md` §2 and §5, `docs/epics.md` -- the panel layout, its states, E2-S09 ✅, changelog.

## Tasks & Acceptance

**Execution:**
- [x] `app/panel.py` -- read and shape `metrikker.json` per the matrix, without computing anything -- FR10
- [x] `app/__init__.py`, `app/templates/forside.html`, `app/static/style.css` -- render the panel -- FR10, UU
- [x] `tests/test_ruter.py`, `tests/test_panel.py` -- one test per matrix row; every displayed number is traced back to the file -- NFR2
- [x] `docs/ux/dashbord.md`, `docs/epics.md` -- layout, states, ✅, changelog

**Acceptance Criteria:**
- Given the real `metrikker.json`, when `/` opens, then every number in the panel equals the file's value after rounding, and no value from `test_bare_baseline` appears.
- Given the panel, when the table of calls is compared with E2-S08, then the table and the strip are unchanged.

## Implementation Notes

- `app/panel.py` `lag_panel()` only reads `metrikker.json` (path and `testkjoringer()` from `app.prediksjon`) and never raises. The route passes `panel=lag_panel()`.
- Comparison wording comes from the raw sign (`_sammenlign`); «<0,1 pp»/«<0,01» when it rounds to zero. Empty denominators show «ingen varsler (0/0)» / «ingen forsinkede (0/0)». Non-finite numbers give «Tall mangler».
- List lookups in the route and UU tests are scoped to `#anlopslista`; `test_panel_uu_struktur` checks the panel rendered from the real file.
- Mutation check: 25 of 26 killed; the survivor is equivalent. After Decision 5: 27 of 28 (two new mutants for «systemet»), the same equivalent survivor.
- Screenshots (2026-11-11, `scripts/ta_skjermbilder.py` functions, output to the scratchpad, not committed): `scrollWidth` equals the viewport at 360, 640, 1024, 1280 and 1920 px, so no horizontal scrolling. At 1024 px the list column is narrower and the «predikert før valgt tidspunkt» hint wraps to three lines. The panel is much taller than the list (page height 2 802 px at 1 280 px).

## Spec Change Log

## Review Triage Log

| # | Layer | Finding | Verdict | Evidence | Route |
|---|-------|---------|---------|----------|-------|
| 1 | verification-gap | The two verdicts are never tested on a split case | medium | pre-verified: coupling `f1_ok` to `treff_ok` left 72 tests green | patch |
| 2 | blind, edge-case, orchestrator | Difference wording uses the rounded value, the verdict the unrounded one, so «likt» can sit next to «bestått» | medium | `_differanse` rounds before choosing the word; `_dom` compares raw | patch |
| 3 | blind | A loss on F1 against «varsle alle» has no summary line, while a ±30 min win does | medium | real validation, Øvrige alle: model F1 below «varsle alle» at both horizons; only table cells show it; FR10 equal clarity | patch |
| 4 | edge-case | F1 verdict text can show two equal 2-decimal numbers next to «bestått» | low | `_f1` rounds to 2 decimals; direct fix | patch |
| 5 | blind | `varsle_alle.f1 = null` gives «ikke bestått» as if the model lost | low | `f1_ok` is False when either is None; direct fix | patch |
| 6 | blind | 0 alerts shown as «0,0 % (0/0)» | low | `app/metrikker.py:126` writes 0.0 for 0/0; the screen should say there were no alerts | patch |
| 7 | edge-case | NaN/Infinity in the file shows «nan %» | low | `json.loads` accepts NaN; direct guard in the formatters | patch |
| 8 | blind | Route test checks only `abs(d) pp` somewhere | low | sign, wording and table not checked; «bedre»/«dårligere» swap passes | patch |
| 9 | blind, edge-case | `test_bare_baseline` leak check covers only fractions | low | percentages and F1 not checked | patch |
| 10 | blind, edge-case | Synthetic block uses the same dict for both horizons | low | a horizon swap is not caught | patch |
| 11 | edge-case, orchestrator | Existing list and UU tests look up `th`/`table`/`tbody` document-wide, and pass only because the autouse stub gives «Tall mangler» | medium | the UU structure checks never see the panel's tables | patch: scope list lookups to `#anlopslista`, and run the UU structure checks on the panel with the real file |
| 12 | blind | `overflow-wrap: anywhere` can break numbers mid-fraction | low | 24rem column with three value columns; direct CSS fix | patch |
| 13 | blind | UX §2 still has the old «Treffsikkerhet» bullet next to the new one | low | two panels described | patch |
| 14 | blind | Epics Test line lists only `test_panel_modell_mot_baseline` | low | new tests not named | patch |
| 15 | blind | Footnote does not explain «pp» | low | direct text | patch |
| 16 | blind, edge-case | File read twice per request (`testkjoringer` then the numbers) | low | a rewrite between the reads is not realistic outside E2-S10; the fix needs a new parse-once API | reject |
| 17 | blind | Period labels hard-coded | false | Decision 1 gives the validation label verbatim; the test dates are UX §2's | reject |
| 18 | blind, edge-case | «Tall mangler» hides the ground-truth count | false | there is nothing to count when the block is missing | reject |
| 19 | edge-case | Huge integer share raises `OverflowError` | low | not producible by `evaluer.py` | reject |
| 20 | edge-case | Grid starts at 1024 px, not 640 px | false | UX §2 defines desktop as ≥ 1024 px; Decision 2 only fixes < 640 px | reject |
| 21 | blind | `data-arm` attribute unused | low | harmless | reject |
| 22 | blind | Spec unticked while epics says ✅ | false | the spec is closed in step 5 | reject |
| 23 | mutation check | Model F1 `null` with «varsle alle» set gave «Tall mangler» instead of «kan ikke sammenlignes» untested | low | mutant 19 survived | patch: `test_f1_differanse_uten_modell_f1_kan_ikke_sammenlignes` |
| 24 | mutation check | The before-test sentence «Bestått eller ikke bestått avgjøres først på testperioden» untested | low | mutant 24 survived | patch: `test_panel_foer_testkjoringen_sier_at_dommen_venter`, plus absence after the test run |
| 25 | mutation check | F1 verdict `>` vs `>=` not caught: no fixture has equal F1 | medium | survived on three reruns; the first run reported it killed, which could not be reproduced | patch: `test_lik_f1_er_ikke_bestatt` |
| 26 | mutation check | Wording `d > 0` vs `d >= 0` | false | equivalent: `d == 0` returns «likt» before the word is chosen | reject |

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green, < 1 min
- `git diff --quiet data/` -- expected: no change
