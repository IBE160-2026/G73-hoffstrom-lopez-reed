---
title: 'E2-S01 — Gjenstående modellvalg og featureliste'
type: 'chore'
created: '2026-11-03'
status: 'done'
baseline_commit: '4bb69d2db1406962f194033e341ca70bf8c24340'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/docs/beslutninger/08-horisont-kuttes-pa-rapportert-eta.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The PRD §8 questions (one or two models, A1, A2) and the feature list are still open, and E2-S03–S05 cannot be specced without them. The vessel-history feature is also a known leakage trap: computed over the whole dataset, it would carry test-period ground truth into the model.

**Approach:** One new decision document (beslutning 11) records Felipe's choices and the locked feature list. The PRD, epics and architecture are updated to match, PRD first (PRD §1 rule). No code. Approval comes from the whole group in the E2 PR.

## Decisions (Felipe, 2026-11-03)

1. **One model, Øvrige only.** Passasjer keeps the calibrated baseline. For Passasjer rows the model predictor delegates to the baseline, and the row is marked as a baseline prediction.
2. **A1 cannot be verified,** because the dataset has one reported ETA per voyage and no time for when it was reported. It moves from §9 Assumptions to an explicit **limitation** in the PRD and in this decision. It is no longer an assumption to be refuted.
3. **A2 is kept and confirmed:** the model succeeds on alerts if its F1 is higher than the rule that alerts every call (≈ 0.33 on Øvrige). The `[ASSUMPTION]` tag is removed.
4. **The vessel-history feature uses training data only:** train-split rows with `arrival_in_area < t_H` of the row being predicted, never the row itself. Test-period deviations never enter any feature. A named test in E2-S04 proves it (see Tasks).
5. **Departure port and ETD (F13–F14) are kept** (question 1 → A). Whether the departure port was known at `t_H` is recorded as a limitation next to A1. **Ablation:** E2-S05 also trains without F13–F14, and E2-S06/E2-S10 report both results side by side. That measures how much the model rests on fields we cannot verify.
6. **Horizons** (question 2 → A): one model family for Øvrige, trained once per horizon, giving two artifacts (6 h and 24 h).
7. **F1–F16 are locked** as listed below, with three clarifications:
   - **F6 split:** rows where the ship is already in the arrival zone at `t_H` give the model an edge the baseline does not have. E2-S06/E2-S10 report every model-vs-baseline number both with and without those rows.
   - **F7 at zero speed:** `slakk_timer = H − (distanse_km / 1.852) / max(fart_knop, 1.0)`, clipped to [−48, H]. Speed below 1 kn counts as 1 kn. Distance 0 gives `slakk_timer = H`. If SOG is missing or ≥ 102.3 kn (the AIS "not available" value), F2 and F7 are empty. A test in E2-S04 covers speeds 0, 0.3, 1.0, 12, missing and 102.3.
   - **F15 shrinkage target:** the Øvrige mean that F15 is shrunk towards (k = 5) is also computed on training rows only, with arrival < `t_H`. The history test covers it.

## Boundaries & Constraints

**Always:**
- Every feature is computable from information available at `t_H`. That means AIS ≤ `t_H`, static ship data, reported ETA, ETD only when ≤ `t_H`, and training-split history with arrival < `t_H` (FR9a).
- Calendar features are computed from reported ETA in Europe/Oslo time, never from actual arrival.
- The cut point, the 24 h lookback and the baseline for rows without state (decision 08/09) are unchanged.
- A3 (the alert is a > 120 min threshold on predicted deviation) is unchanged.
- PRD changes get a changelog line, and the decision follows the existing format (Kontekst / Alternativer / Valg / Begrunnelse / Konsekvens).

**Never:**
- Touch code, `data/`, `pipeline/` or `pipeline/data/`. The E2-S02 fetch is running.
- Change the locked numbers (46.6 % / 79.6 %, 19.5 %).
- Features from: `arrival_in_area`/`arrival_at_quay`/dwell/status fields, `window_*`/`truncated_by_next_voyage` (they depend on the next voyage), the ETD value when ETD > `t_H`, statistics over the test period, or raw `mmsino`/`shipname` as IDs.

</frozen-after-approval>

## Feature list (locked 2026-11-03, see decision 7)

Only Øvrige rows that have AIS state at `t_H` are fed to the model. Rows without state get the baseline (FR9a).

| # | Feature | Source, known at `t_H` because … |
|---|---|---|
| F1 | `distanse_km` to the port reference point | last AIS ≤ `t_H` (E2-S03) |
| F2 | `fart_knop` (SOG) | last AIS ≤ `t_H` |
| F3 | `kurs_mot_havn` = cos(COG − bearing to port), in [−1, 1] | last AIS ≤ `t_H`. Raw course is circular (359° ≈ 1°) |
| F4 | `posisjon_alder_min` | `t_H` − time of the position |
| F5 | `lat`, `lon` | last AIS ≤ `t_H`. Separates routes, e.g. from the north and from the south |
| F6 | `i_sonen_ved_kutt` (0/1) | from the position (distance ≤ zone radius), **not** from the `allerede_ankommet` label |
| F7 | `slakk_timer`, defined in decision 7 | derived from F1/F2. Positive means it will make the ETA at current speed |
| F8 | `skipstype` (category; rare types grouped as `annet`) | static voyage data |
| F9 | `lengde_m` | static voyage data |
| F10 | ETA time of day, as sin/cos of the hour | reported ETA, Oslo time |
| F11 | ETA weekday | reported ETA, Oslo time |
| F12 | ETA month, as sin/cos | reported ETA. The test is winter-skewed, and training covers two winters |
| F13 | `avgangshavn` (top N in training, others `annet`) | voyage data, a limitation next to A1 (decision 5) |
| F14 | `avgatt_for_kutt` (0/1), and `timer_siden_avgang` only when ETD ≤ `t_H`, otherwise empty | ETD is used only when it is in the past at `t_H` |
| F15 | `fartoy_snittavvik_min`: the vessel's mean calibrated deviation, shrunk towards the Øvrige mean (k = 5) | train rows only, same MMSI, `arrival_in_area < t_H`, not the row itself. The Øvrige mean comes from train rows only as well (decisions 4 and 7) |
| F16 | `fartoy_antall_tidligere` | same source as F15 |

## Code Map

- `docs/prd.md:87-101` -- FR9a/FR9/FR10. FR9 gets "model for Øvrige only, Passasjer delegates to baseline". FR10 gets "Passasjer reported as baseline only". The `[ASSUMPTION]` tags at :97 and :100 are decided: :100 is removed (A2). :97 (A3) stays.
- `docs/prd.md:161-177` -- §8: close three rows and move them to **Lukket**. §9: remove A1 and A2, keep A3. Add a new "Kjente begrensninger" list in §7 with A1 (explicit limitation) and the departure port (decision 5). FR10 gets the F13–F14 ablation and the F6 split as extra reporting requirements.
- `docs/epics.md:237-327` -- E2-S01 ◐ (✅ when approved in the PR). E2-S04 gets the feature list reference and the history test. E2-S05 trains on Øvrige only. E2-S07 delegates Passasjer to the baseline. E2-S10 limitations are worded as "A1 (begrensning)".
- `docs/arkitektur.md:48-96` -- §3 contract: a note that ModellPrediktor delegates Passasjer to BaselinePrediktor, and `forklaring["metode"]` shows which one was used. §4: the new committed extract for static/history features (name decided in E2-S04, < 10 MB together with the state extract, NFR1).
- `pipeline/fetch_voyages.py:44-54` -- `ship_type`, `length`, `etd` and `dep_locname` exist only in the gitignored `pipeline/data/voyages_*.csv`, not in the locked `data/utdrag/anlop.csv`. That is why E2-S04 needs a new committed extract.
- `docs/beslutninger/08-…`, `09-…` -- format to follow. The new file is `docs/beslutninger/11-modellvalg-ovrige-og-features.md`.

## Tasks & Acceptance

**Execution:**
- [x] `docs/beslutninger/11-modellvalg-ovrige-og-features.md` -- decisions 1–7, feature list F1–F16 with the F7 definition, the exclusion list, limitations (A1, departure port), the ablation and the F6 split.
- [x] `docs/prd.md` -- FR9, FR10, §7 limitations, §8 closed, §9 trimmed, changelog line.
- [x] `docs/epics.md` -- E2-S01 ◐, E2-S04/S05/S07/S10 as in the Code Map, changelog line. E2-S04's test list gets `tests/test_features.py::test_fartoyhistorikk_bare_fra_trening`: change every test-period deviation (and the row's own) → identical F15/F16 **and identical shrinkage target** for all rows; change a train row's deviation → only rows with `t_H` after that row's arrival change. It also gets `::test_slakk_ved_lav_fart` (decision 7). E2-S05 adds the ablation model without F13–F14. E2-S06 and E2-S10 add the ablation results and the with/without-F6 split.
- [x] `docs/arkitektur.md` -- §3 delegation note, §4 extract note, changelog line.

**Acceptance Criteria:**
- Given the updated PRD, when §8 and §9 are read, then the three E2-S01 rows are closed, A1 is a limitation rather than an assumption, and A2 has no `[ASSUMPTION]` tag.
- Given beslutning 11, when each feature F1–F16 is checked against the exclusion list, then none depends on data after `t_H` or on the test period.
- Given `git diff --stat`, then only `docs/` and this spec changed, and `pytest` is still green.
- Given the E2 PR, then the whole group has approved beslutning 11 (the story's test from the epics).

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green (documentation-only change)
- `git diff --stat` -- expected: only `docs/` and `_bmad-output/`

## Implementation Notes

- 2026-11-03: implemented directly in the main session. Review ran as three independent subagents. Documentation only, and `pytest` stayed green (198).
- Felipe's three clarifications (ablation, F6 split, F7 at zero speed, the F15 shrinkage target) are in decisions 5–7 and run through the PRD, epics and decision 11.

## Spec Change Log

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG).

- VG: no verification gaps, because the change is documentation only. No code reads these files.
- BH/ECH: decision 11 said `kan_varsle` is true only for model rows, but `kan_varsle` is a predictor attribute (`app/__init__.py:63`). This contradicted E2-S07 — medium. **patch**: the predictor keeps `kan_varsle = True`, and delegated rows get `forventet_forsinket = None` plus `metode = "baseline"` (decision 11, choice 8; arkitektur §3; E2-S07).
- BH/ECH: no route for F8–F16 through the leakage boundary — medium. **patch**: they go through `lag_input` or a sister function, never by file reads in the predictor module. A new field in `PrediksjonsInput` is a contract change in its own PR, approved by Thomas and Felipe (choice 8, arkitektur §3, E2-S07).
- BH: the contract change has no sign-off step — low. **patch**: covered by the same text. Decision 11 itself does not change the contract.
- BH/ECH: the F16 test cannot catch leakage, because only deviations change — medium. **patch**: the test also adds, removes and moves test rows.
- BH/ECH: unspecified parameters (N, the rarity threshold, the zone radius, the clip rationale) — medium. **patch**: ≥ 20 Øvrige rows in the fit data, otherwise `annet`; radius 15 km (decision 03, `OUTER_RADIUS_KM`); the clip rationale is stated; category lists are fitted only on the fit data.
- BH/ECH: COG and position sentinels; distance 0 makes the bearing undefined — medium. **patch**: F3 is empty for COG missing or ≥ 360, speed < 1 kn, or distance 0. Lat 91 / lon 181 is not a valid position. New `test_kurs_ugyldig`.
- BH/ECH: "row without state" is undefined; NaN in F2/F7 has no handling path — medium. **patch**: defined as no valid position in the lookback. Missing speed or course goes to the model with empty fields, and the model family must tolerate NaN or impute on train only.
- ECH: F15 shrinkage target undefined when there are no train rows before `t_H` — medium. **patch**: the target is 0 and F16 is 0, covered by the test.
- ECH: missing or unseen static fields — low, direct fix. **patch**: unknown → `annet`, missing length → empty, missing ETD → F14 empty.
- ECH: ETD boundary "≤" vs "før" — low, direct fix. **patch**: "ved eller før" (≤) everywhere.
- BH: two "in zone" definitions — medium. **patch**: the split uses F6, `allerede_ankommet` is counted as before, and their overlap is reported.
- BH/ECH: size budget stated in two ways — low. **patch**: one budget, everything E2 commits under `data/` < 10 MB, in the PRD, arkitektur and epics.
- BH: F7 uses H instead of the actual time left under the clamp — low. **patch**: H is defined as `eta_reported − t_kutt`, which equals 6/24 today. The formula in Felipe's decision 7 is unchanged.
- BH/ECH: the A1 documentation check is not recorded — medium. **patch**: decision 11 states plainly that the check was not done in this session, and A1 reopens if a report time is found later.
- BH/ECH: stale A3 text in PRD §9 — low. **patch**: "Beholdt uendret i E2-S01".
- BH: the new E2-S05/S06 requirements have no tests — medium. **patch**: test lines added in epics (no Passasjer in training, ablation without F13–F14, `metrikker.json` keys).
- BH: title wording "én modell" vs four artifacts; "kontrollgruppe" unexplained — low. **patch**: "modellfamilie", and the Passasjer wording is reworded.
- ECH: F15 uses calibrated deviation with the offset fitted on all of train, so training-row features would carry later label information — false. The offset is one constant per group, subtracted from every deviation and from the shrinkage target alike, so F15 shifts by a constant and carries no information about later arrivals. Category frequencies over all of train — **patch**: fitted on the fit data only.
