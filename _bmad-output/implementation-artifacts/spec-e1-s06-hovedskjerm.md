---
title: 'E1-S06 — Hovedskjerm med anløpsliste'
type: 'feature'
created: '2026-10-27'
status: 'done'
baseline_commit: '2843422eb9706cd3957c5cef17d12015a228f844'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/docs/ux/dashbord.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `GET /` is a placeholder. Sensor cannot see a single prediction.

**Approach:** Render screen A (`docs/ux/dashbord.md` §2) for the default window with server-side HTML: header, prediktor-stripa, the call table sorted by predicted arrival, and the footnote. Below 640 px the same table becomes cards (screen B). Predictions come from `velg_prediktor()` through `lag_input`.

**Group requirements (27.10.2026):**
1. Build to the wireframes. Every deviation is justified and logged in the UX changelog.
2. The UU minimum moved into S06 gets automated tests wherever possible: `lang`, landmarks, heading hierarchy, alt text, and that all interactive elements are keyboard-reachable. The colour tokens used in CSS must equal the UX §7 table, whose contrast is already calculated.
3. The varsel column is empty on purpose in v1, and the screen says why (UX §1, §2, FR3).
4. When S06 is done, screenshots of the default window at desktop width and below 640 px go into `docs/ux/skjermbilder/`, for README in S16.
5. **Clarification at approval (27.10.2026):** the screenshots are taken by a separate script outside the test suite. `pytest` must never need Chrome or anything else not in `requirements.txt`, because sensor runs the tests on a clean machine. The script is documented in `docs/ux/`, not in README's run-the-tests step.

**Decided earlier:** window on reported ETA in [nå, nå + 24 t) (E0-S18); times shown rounded to the nearest minute, display only (E0-S18).

## Boundaries & Constraints

**Always:**
- Default «nå» = 08.10.2025 08:00 Europe/Oslo. All shown times are Europe/Oslo, and the page says so.
- Columns: Skip, Gruppe, Rapportert, Predikert, Horisont, Varsel. Format «ons 09:56». Horizon «≤ 6 t» / «6–24 t» from `PrediksjonsInput.horisont_timer`.
- Rows are sorted by unrounded predicted arrival, ties by reported ETA, then voyageid. A predicted time before «nå» gets `*` plus the text «predikert før valgt tidspunkt».
- Varsel cell: visible «–», with a text alternative for screen readers saying the baseline does not warn. Prediktor-stripa shows the predictor's `navn` and, when `kan_varsle` is false, the UX §2 text that the baseline cannot warn and the column fills when the model comes.
- UU minimum from epics E1-S06: light-theme tokens (UX §7), skip link first, a visible 3 px `--aksent` focus ring, `lang="nb"`, one `h1` with no skipped heading levels, `<table>` with `<th scope="col">`, `header` and `main` landmarks, viewport meta, and `data-label` cards below 640 px with no horizontal scroll at 360 px.
- No JavaScript. No new dependencies.

**Never:**
- Form, filter, fasit columns, sort buttons, detail links or panel. These are S07–S12 (KAN), and leaving them out is not a deviation.
- Ground truth in the HTML (`faktisk_ankomst`, `status_in_area`).
- Dark theme (S13).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | `GET /` | 200, 15 rows, first ROTTERDAM, last MSC POESIA, header «15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)» | N/A |
| Rounding | BERGEN ENERGY 09:55:48 | «ons 09:56» | N/A |
| Before «nå» | ROTTERDAM 07:15:15, EINARSON 07:55:48 | `*` and help text on those two rows only | N/A |
| Horizon | BERGEN ENERGY / THUN EVOLVE | «≤ 6 t» / «6–24 t» | N/A |
| Empty window | test config sets «nå» to a period with no calls | 200, «0 anløp …», UX §5 message, no table | N/A |
| No ground truth leak | default window | none of the ground-truth arrival times appear in the HTML | N/A |

</frozen-after-approval>

## Code Map

- `app/__init__.py` -- `create_app(config)`, placeholder `/`. Replace the route and keep the factory. Add config `STANDARD_NAA` (tz-aware) so tests can render an empty window without S07's query parameter.
- `app/data.py` -- `anlop_i_vindu(naa)`. Read-only.
- `app/prediksjon/__init__.py` -- `lag_input`, `velg_prediktor`. Read-only.
- `tests/conftest.py` -- `app`/`client` fixtures. Reuse.
- `docs/ux/dashbord.md` §2 (screen A), §3 (B), §5 (empty window), §7 (tokens table, focus ring).

## Tasks & Acceptance

**Execution:**
- [ ] `app/visning.py` -- Oslo time, rounded to the nearest minute, «ons 09:56» and «ons 08.10 08:00» (Norwegian weekday abbreviations without locale), and the horizon label.
- [ ] `app/templates/base.html`, `app/templates/forside.html` -- screen A as above.
- [ ] `app/static/style.css` -- `:root` tokens copied from UX §7 (light), focus ring, `.visually-hidden`, card layout below 640 px.
- [ ] `app/__init__.py` -- route `/` builds the window, predicts, sorts and renders.
- [ ] `tests/test_ruter.py` -- `test_standardvindu`, `test_tomt_vindu`, ground-truth leak.
- [ ] `tests/test_visning.py` -- rounding at :29/:30 seconds, weekday names, DST (Oslo +02 → +01 on 26.10.2025), horizon labels.
- [ ] `tests/test_uu_struktur.py` (stdlib `html.parser`) -- `lang="nb"`, one `h1` and no skipped levels, `header`/`main`, skip link first with a working target, every `th` with `scope`, every `td` with `data-label`, viewport meta, every `img` with `alt`, meaningful `svg` with title/aria-label. Keyboard: interactive elements are native (`a[href]`, `button`, `input`), no positive or `-1` `tabindex` on them, no `onclick` handlers.
- [ ] `tests/test_kontrast.py` -- parse the UX §7 table and the `:root` block in `style.css`. Every token used in CSS equals the UX value. Recompute WCAG contrast for the pairs used (≥ 4,5:1 text, ≥ 3:1 `--kant`).
- [ ] `docs/ux/dashbord.md` -- correct the sketch times to nearest-minute rounding (EINARSON 07:56, ELEKTRON 10:26, OCEAN RESPONSE 12:41, ELDJARN 12:56, SIEM PEARL 15:26, also in A2), add a changelog line for each deviation, and set the UU1/UU4/UU7 checklist rows' test column to the new tests.
- [ ] `scripts/ta_skjermbilder.py` -- standalone script (not under `tests/`, never imported by tests). It starts the app on a free local port, runs headless Chrome (`--headless --screenshot --window-size`), and writes `docs/ux/skjermbilder/hovedskjerm-desktop.png` (1280 px) and `hovedskjerm-mobil.png` (360 px). Path to Chrome via an argument or env var with the macOS default, and a clear error if it is missing. Run it after all tests are green and commit the PNGs.
- [ ] `docs/ux/skjermbilder/README.md` -- how to run the script, what it needs (Chrome, not in requirements.txt), and that it is not part of `pytest`.
- [ ] `docs/epics.md` -- E1-S06 → ✅, changelog line.

**Acceptance Criteria:**
- Given a sensor following README, when they open `/`, then they see 15 calls with predicted arrival in Norwegian time and a stated reason why the varsel column is empty.
- Given a 360 px wide viewport, when the page renders, then rows show as cards and the screenshot shows no horizontal scroll.

## Design Notes

**Sketch deviations already known.** E0-S18 changed only BERGEN ENERGY to 09:56. Every Øvrige row has a 64,2 min offset (:48 seconds) and rounds up, so five more sketch times are wrong. Screen B's form-in-`<details>` has no form to hold in S06, which is not a deviation.

**What cannot be automated.** Contrast as rendered and tab order as experienced need a human. The no-scroll-at-360 px check is covered by the mobile screenshot and the UX §6 checklist in S16.

## Verification

**Commands:**
- `.venv/bin/pytest -q` -- expected: all green (120 existing + new).
- Mutation check with a control run on unchanged code. The tests must fail when:
  - the times are truncated instead of rounded
  - the sort uses reported ETA
  - `scope` is dropped from one `th`
  - one `--tekst` hex differs from UX §7
  - the skip link is moved after the table
  - the varsel text alternative is removed
  - `faktisk_ankomst` is rendered

**Manual checks:**
- Tab through the page at 1280 px: skip link first, focus visible. Inspect both screenshots.

## Review Triage Log

Three layers: Blind Hunter (BH), Edge Case Hunter (ECH), Verification Gap (VG). The orchestrator's own mutation check (16 mutants, all caught) ran before review.

- ECH (claim): the 360 px image is cropped to the leftmost 360 px with scrolling off, so horizontal overflow is cut away by construction, and the screenshot cannot prove the AC "no horizontal scroll". high: the evidence for UU6 was invalid. **patch**: the script measures scrollWidth/scrollHeight at 360, 640 (= 1280 px at 200 % zoom), 1280 and 1920, fails on overflow, and sizes the images from the measured height. BH + ECH: fixed heights could cut the page silently. Fixed by the same patch.
- BH: `display:block` on the mobile table drops table semantics in Safari/VoiceOver, so UX §3's "skjermlesere ser fortsatt en tabell" is false on mobile. medium. **patch**: explicit ARIA table roles, a test, and a UX changelog line.
- VG gap + BH: no route test crosses the DST change; a wall-clock `naa + 24 h` would label the window one hour wrong. medium, pre-verified. **patch**: `test_vindu_over_sommertid`.
- VG gap + BH: the predictor description in the strip is untested and is keyed on the display name. low, pre-verified. **patch**: assert the text.
- ECH: a stale PNG could pass the `is_file()` check; Chrome's stderr is discarded. low, direct. **patch**.
- BH: the mobile header row is hidden with only part of the visually-hidden pattern. low, direct. **patch**.
- BH: the skip-link test does not check that the target is the list. low, direct. **patch**.
- BH + ECH: token regexes disagree on hyphens, which would break in E1-S13. low, one-character fix. **patch**.
- BH: the «Mer ›» changelog bullet is unclear. low. **patch**.
- BH + VG other + ECH (claim): the varsel cell and footnote text are hard-coded to the baseline. **false** for this story: `velg_prediktor()` can only return the baseline in E1, and E2-S08 owns the varsel column ("Malene endres ikke utover stripa, varselkolonnen …").
- BH: `tabular-nums` missing. **false**: moved to E1-S13 (KAN) in E0-S17.
- BH: E1-S06 marked ✅ while manual UU checks are open. **false**: the checklist is filled in E1-S16 (E0-S17). The 200 % zoom check is now automated through the 640 px measurement. The keyboard walk-through still needs a human.
- BH: the review diff omits the spec and notater. **false**: by design; notater has today's entries.
- ECH: a predictor returning fewer or reordered predictions would mis-pair rows in `zip`. **false**: the contract test asserts order and length for every predictor in `PREDIKTORER`.
- ECH: an invalid `PREDIKTOR` gives 500 per request, not at startup. low, rejected: it adds startup behaviour, and E2-S08 owns fallback.
- ECH: a naive or string `STANDARD_NAA` gives 500. low, rejected: test-only config.
- ECH: a prediction seconds before «nå» shows «08:00*». low, rejected: consistent with E0-S18 (only display rounds) and rare.
- ECH: PNG parser guards (missing IHDR, `assert` under `-O`, filter bytes). low, rejected: the input is Chrome's own output, and the guards add surface.
- ECH + BH: contrast-test parsing (no trailing semicolon, several `:root` blocks, `fill`/`stroke`, IndexError on a one-number row, empty heading list). Rejected: loud failures, or E1-S13's concern when the dark theme adds a second block.
