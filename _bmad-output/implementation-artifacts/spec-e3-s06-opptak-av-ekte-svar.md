---
title: 'E3-S06 — Recorded real answers for the demo windows'
type: 'feature'
created: '2026-11-24'
status: 'done'
baseline_commit: '3fbe4cd4374c5f4b3751bcf9ed0527badb28c7c4'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-e3-s05-forstyrrelsesbrief.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** FR13 says test mode shows recorded real answers for the demo windows, but test mode today only has the deterministic template (`testmodus.mal`, `brief_mal`). The examiner, who has no key, never sees what the language model actually writes.

**Approach:** A local script, `scripts/ta_opp_begrunnelser.py`, runs real mode once for the demo window through the existing adapter (check, fallback) and writes the accepted answers to `data/begrunnelser_opptak.json`, which is committed. In test mode the app shows a recording when one exists and still matches the input. Otherwise it shows the template, as today.

## Spec choices O1–O3 (Theodor, 2026-11-24)

- **O1 — Only 08.10.2025 08:00 is recorded.** The app only renders `STANDARD_NAA`; the time picker (E1-S07) is not built, so 17.09 cannot be shown. FR13, `docs/epics.md` (E3-S06) and the PRD change log are amended to say so. The PR states that the group must accept the PRD change in its review.
- **O2 — Label:** «Testmodus (opptak av ekte svar)», with the recording date shown with it (e.g. «tatt opp 24.11.2026»).
- **O3 — Limited use of test rows (display, not evaluation).** The recording run makes `ModellPrediktor` predict the 08.10 window, which lies in the test period. This is allowed only for display: no ground truth is sent or read, no locked file (model artefacts, `metrikker.json`, `resultater.md`) is changed, and production already shows Modell v1 for 08.10 since E2-S10. Felipe confirms before the recording run. Code and tests are built now; `--kjor` is not run. Tests and subagents still use model rows only at `VALIDERING_NAA`.

## Boundaries & Constraints

**Always:**
- **Same adapter.** The script calls `hent_begrunnelse` and `hent_brief`, so every recorded answer has passed `kontroller`. Only answers labelled «KI-GENERERT» are recorded. A rejected or failed answer is left out (the template is shown for that call) and reported by the script.
- **Freshness.** Each entry stores the prompt version (`begrunnelse-vN` / `brief-vN`, read from the prompt file's `**Versjon:**` line), the model string, the recording time and a SHA-256 of the facts sent (`lag_fakta` / `lag_brief_fakta`). The app uses an entry only when the key (window, voyage or «brief», predictor) and the facts hash match. A changed prompt version or changed facts → template. The script prints a warning in that case instead of failing.
- **Reading only.** The app reads the file once per process and never writes it (read-only disk on Vercel, arkitektur §11). A missing or invalid file → template, no error, status 200.
- **Script guards.** Without `--kjor` the script only prints the plan (windows, number of calls). With `--kjor` it requires `LLM_MODUS=ekte` and `OPENROUTER_API_KEY`, raises the cap for its own process only (`LLM_MAKS_KALL`), and never prints or writes the key. The B1 app brief (no alerts / baseline) makes no call and is not recorded.
- **Tests.** Test mode or a fake transport, sockets blocked. Model rows only at `VALIDERING_NAA` with a hand-built recording file (`tmp_path`); the test-row rule is passed to every subagent. The epics test name `test_testmodus_bruker_opptak` is used.

**Never:**
- Running the script with `--kjor`, reading `.env`, or printing the key. The recording run is a separate step that Theodor starts after Felipe has confirmed (O3), logged in `.logs/` with cost (decision 13).
- Recording 17.09.2025 (O1).
- Using a recording in real mode (real mode keeps its own cache and fallback), changing the check rules, the prompts, the list, the panel or the JS.
- A time picker or a `?naa=` parameter (E1-S07), the README (E3-S07), merging anything.

## I/O & Edge-Case Matrix

| Scenario | State | Shown | Logged |
|---|---|---|---|
| Test mode, recording matches | 08.10, file has the call | recorded text, «Testmodus (opptak av ekte svar)» + date | nothing |
| Test mode, no entry | call missing in file | template, «Testmodus» | nothing |
| Test mode, facts or prompt changed | hash/version differs | template, «Testmodus» | nothing |
| File missing or invalid JSON | — | template, «Testmodus», 200 | one warning per process |
| Brief, alerts, recording matches | 08.10 | recorded brief, recording label | nothing |
| Brief, no alerts / baseline | B1 | app brief, «Laget av appen» | nothing |
| Real mode | key set | as today (recordings not used) | as today |
| Script without `--kjor` | — | plan only, 0 calls | — |
| Script, answer rejected | `kontroll_*` | entry left out, listed in the summary | reason code |

</frozen-after-approval>

## Code Map

- `app/begrunnelse/__init__.py` -- `cachet`, `hent_begrunnelse`, `testtekst`, `cachet_brief`, `hent_brief`, `testbrief`. In test mode, `testtekst`/`testbrief` (with `merke == MERKE_TEST` only) first ask the recording lookup. The failure labels (`MERKE_FEILET`, `MERKE_GRENSE`) keep the template. Signatures unchanged except a `naa` argument where the lookup needs it (`cachet`/`hent_begrunnelse` get `naa` from the routes).
- `app/begrunnelse/testmodus.py` -- add `MERKE_OPPTAK` and the lookup (`opptak_for(...)`), file path `OPPTAK_FIL = data/begrunnelser_opptak.json`, read once (module-level cache, reset in `nullstill`).
- `app/begrunnelse/input.py:121,183` -- `lag_fakta`, `lag_brief_fakta`: hash their output (sorted JSON, UTF-8). Do not change them.
- `app/begrunnelse/openrouter_klient.py:24-46` -- `PROMPT_FIL`, `PROMPT_BRIEF_FIL`, `_prompt`: add a small `prompt_versjon(fil)`.
- `app/__init__.py:110-190` -- pass `naa` to `cachet`/`hent_begrunnelse`. No other route change.
- `scripts/ta_opp_begrunnelser.py` -- new. Uses `create_app`'s helpers (`_par`) per window, so the script and the app build the same pairs.
- `tests/conftest.py` -- do not change the guards. Point `OPPTAK_FIL` at a missing file by default (autouse), so no test depends on the real recording.
- `docs/prd.md:148` (FR13) and the PRD change log, `docs/arkitektur.md:160,170,248`, `docs/ux/dashbord.md` §4/§5, `docs/epics.md:406-410` and its change log -- only 08.10 (O1), the label (O2), the lookup rule, the limited test-row use (O3), and ✅. The cost line in `docs/beslutninger/13-*` comes after the run.

## Tasks & Acceptance

**Execution:**
- [x] `app/begrunnelse/openrouter_klient.py`, `testmodus.py` -- prompt version, facts hash, lookup, label
- [x] `app/begrunnelse/__init__.py`, `app/__init__.py` -- use the lookup in test mode; pass `naa`
- [x] `scripts/ta_opp_begrunnelser.py` -- plan mode, `--kjor`, summary (recorded / rejected / B1)
- [x] `tests/conftest.py`, `tests/test_begrunnelse.py`, `tests/test_ruter.py`, `tests/test_opptak_skript.py` -- every matrix row, `test_testmodus_bruker_opptak`, the script with a fake transport (plan mode makes 0 calls, rejected answer left out, key never in the file)
- [x] `docs/…` -- as in the Code Map

**Acceptance Criteria:**
- Given no `data/begrunnelser_opptak.json`, when `pytest` runs, then everything is green with no socket opened, and the pages look as today.
- Given a recording file made by the script with a fake transport at `VALIDERING_NAA`, when screen C and screen A are opened in test mode, then the recorded texts are server-rendered with the recording label.
- Given the same file and a changed prompt version, then the template is shown.

## Implementation Notes

- Built by the implementation subagent (2026-11-24): `prompt_versjon`, `fakta_hash`, `opptak_for`, `MERKE_OPPTAK` with the date (`Begrunnelse.tatt_opp`), test-mode lookup in `testtekst`/`testbrief`, `naa` from the routes, and the script with plan mode and `--kjor`. The templates `anlop.html` and `forside.html` got one line each to show the date (O2). They were not in the Code Map. Suite: 839 passed.
- The plan only warns about an old prompt version, not about changed facts. Checking the facts would mean running Modell v1 on 08.10, and plan mode runs no model (O3). With `--kjor` the facts are hashed again anyway.
- `--kjor` was not run. `data/begrunnelser_opptak.json` does not exist until Felipe has confirmed (O3) and Theodor has run the script.

## Review Triage Log

Pass 1 (2026-11-24). Layers: blind-hunter (BH), edge-case-hunter (EC), verification-gap (VG: no gaps, 2 other findings).

| # | Finding | Verdict | Evidence | Route |
|---|---|---|---|---|
| 1 | BH/EC: non-dict entries in the existing file crash `sorted` after the paid calls | low | The filter keeps non-dicts, and `o.get` raises. Only reached with a hand-edited file. A direct fix. | patch |
| 2 | EC: a re-run with failed calls drops working recordings for the window | medium | `beholdt` drops every entry for the run window, and `nye` only has KI answers. | patch |
| 3 | BH/EC: in-place `write_text`, so a crash leaves a truncated file | low | Confirmed. Temp file + `os.replace` is a direct fix. | patch |
| 4 | EC: the script's `OPPTAK_FIL` default is bound at import, before the conftest patch | low | `from … import OPPTAK_FIL` copies the real path. No test calls without `fil` today, but the fix is direct. | patch |
| 5 | BH: four tests hard-code `begrunnelse-v8`/`brief-v4` | low | Every prompt bump breaks unrelated tests. A direct substitution. | patch |
| 6 | BH/EC/VG: two `**Test:**` lines under E3-S06 in epics.md | low | Confirmed in the diff. | patch |
| 7 | BH/EC: UX §4 shows an example date as real, and the FR11a label list omits the new label | low | Confirmed. | patch |
| 8 | BH: the JSON docstrings and the `Begrunnelse.merke` comment are out of date | low | `tatt_opp` is undocumented, and the comment omits «Laget av appen» and the new label. | patch |
| 9 | BH: E3-S06 marked ✅ before the recording exists | low | Same practice as E3-S05 (✅ with manual and follow-up steps open). The run is a separate step under O3 and goes into `issues.md`. | reject |
| 10 | BH: follow-ups are not in `issues.md` | false | The session log at the end of this build writes them (CLAUDE.md, `sesjonslogg`). | reject |
| 11 | BH: no guard that the script records under Modell v1 | low | `auto` gives Modell v1 after E2-S10, as in production, and the plan prints the predictor. A guard adds a branch. | reject |
| 12 | BH: recordings are not run through `kontroller` again when loaded | low | Every recording passed the check when it was taken. A rule change shows up as an old prompt version in practice. Adding it is a new branch. | reject |
| 13 | BH: the error code is read from the log format | low | A dev-only summary. It falls back to the label, never wrong data. | reject |
| 14 | BH: voyage ids sort as text, and `skip` is undocumented | low | Cosmetic order inside the JSON. `skip` is an extra readable field that the app ignores. | reject |
| 15 | VG/EC: the plan does not warn when the facts have changed | low | The facts can only be checked by running the model on 08.10, which plan mode must not do (O3). Noted in Implementation Notes. | reject |
| 16 | EC: several windows that share a voyageid reuse cached text | false | `DEMOVINDUER` has exactly one window (O1). | reject |
| 17 | EC: `format` in the file is never checked | low | Only format 1 exists. A guard adds a branch for a format that does not exist. | reject |
| 18 | EC: the prompt is edited without a version bump | low | Project practice is a version bump for every prompt change (v1–v8). | reject |
| 19 | EC: a missing `**Versjon:**` line gives log spam | false | Both prompt files have the line, and the script test pins it. | reject |
| 20 | EC: `testtekst`/`testbrief` also got `prediktor_navn` | false | The lookup needs it, since the key includes the predictor. That matches the Code Map's intent. | reject |

## Verification

**Commands:**
- `.venv/bin/python -m pytest -q` -- expected: all green, no network
- `.venv/bin/python scripts/ta_opp_begrunnelser.py` -- expected: the plan, 0 calls

**Mutation check:** the hash comparison, the prompt-version comparison and the «only KI-GENERERT is recorded» filter. Each mutant must turn a test red.

**Manual checks:**
- After Theodor's recording run: clone without `.env`, open `/` and one alerted call in test mode, and see the recording label.
