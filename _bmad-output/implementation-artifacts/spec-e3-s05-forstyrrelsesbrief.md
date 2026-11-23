---
title: 'E3-S05 — Disruption brief at the top of the main screen'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_commit: 'fb6d17a9d4270e38170c38be644010c41adf4f3e'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-e3-s01-s04-begrunnelse-via-openrouter.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** FR12 is unbuilt. The harbour watch opens screen A and has to scan 15 rows to find the calls to distrust. There is no short summary of the window.

**Approach:** A brief of 3–5 sentences at the top of screen A about at most 3 alerted calls, sorted by predicted deviation. It goes through the same adapter as the justification (test mode default, check, cache, cap, fallback), and the page never waits for it (FR11a), the same way as screen C.

## Spec choices B1–B3 (Theodor, 2026-11-19)

- **B1 — No alerts, or the baseline is active: the app writes the brief, no call.** It gives the number of calls in the window, how many the model assessed, and why the rest are not assessed (grouped by `DELEGERT_KLARTEKST`), in 3 sentences, labelled «Laget av appen». This applies in both modes and is server-rendered, so there is no fetch, no cache entry and no count against the cap.
- **B2 — With alerts, the app writes the opening verbatim (as in `begrunnelse-v5/v6`).** It gives the number of alerts, and for each included call the name, the time into the harbour area and the deviation from the usual for the ship group. The model adds the reasons from the facts, up to 5 sentences in total. The test-mode template is the opening plus one fixed sentence, 3–5 sentences.
- **B3 — Size:** the full spec is kept (about 2,100 tokens), with one commit for E3-S05.

## Boundaries & Constraints

**Always:**
- **Same adapter and rules as E3-S01–S04:** `hent_brief` and `cachet_brief` in `app/begrunnelse/`. Input only from `PrediksjonsInput` + `Prediksjon` for the window. No ground truth, MMSI or voyage ID. Config only in `konfig.py`. The key is never logged.
- **Selection:** calls with `forventet_forsinket is True`, sorted by `forklaring["predikert_avvik_min"]` descending (ties: voyageid), at most 3. If there are more than 3, the brief says how many alerts there are in total.
- **FR11a, as on screen C:** `GET /` makes no call. A cached brief is server-rendered. Otherwise an `aria-live="polite"` region shows «Henter oversikt …» and `POST /brief` fetches `{tekst, merke}`, always 200. `<noscript>` shows the template text labelled «Testmodus». `begrunnelse.js` is generalised to find both regions, not copied.
- **FR11b:** cache key (`naa`, predictor name), with the same success/failure lifetimes (S5). The brief shares the per-process cap `LLM_MAKS_KALL` with the justifications.
- **Check:** `kontroller` with limits as parameters: brief 3–5 sentences (reject < 3 and > 5) and ≤ 700 characters. Every other rule as today (numbers, other ship names, cause words, concepts, `retning` = 0 so «senere»/«tidligere» are allowed only where the facts contain them, `metode`). The answer must start with the app-written opening verbatim.
- **Prompt:** a separate versioned file `app/begrunnelse/prompt_brief.md`, version `brief-v1`, in the same style as `begrunnelse-v6`.
- **Tests:** test mode or fake transport, sockets blocked. Model rows only at `VALIDERING_NAA` (test-row rule; subagents are told this). The epics test names `test_brief_nevner_varslede` and `test_brief_uten_varsler` are used.

**Never:**
- A real call, reading `.env` or printing the key. A smoke call only when Theodor asks.
- Changing the list, the panel, the predictor strip or screen C beyond moving the shared JS.
- Recordings (E3-S06), README (E3-S07), the outside-reader check (manual, an open item), merging anything.

## I/O & Edge-Case Matrix

| Scenario | State | Shown | Logged |
|---|---|---|---|
| Test mode | default | template brief, «Testmodus» | nothing |
| Real, 1–3 alerts | key, valid answer | answer, «KI-GENERERT» | nothing |
| Real, > 3 alerts | 5 alerts | the top 3 by deviation, and «5 anløp har varsel» | nothing |
| Cache hit | same (`naa`, predictor) | server-rendered, 0 new calls | nothing |
| Failure / check fails / no key / cap | as in E3-S04 | template, «Testmodus (ekte kall feilet)» or «(kallgrensen er nådd)» | reason code with `naa` and predictor |
| No alerts, or baseline (B1) | either mode | app brief, «Laget av appen», server-rendered | nothing, 0 calls |
| 0 calls in the window | empty window | no brief section | nothing |
| No JS | no cached brief | `<noscript>` template, «Testmodus» | nothing |

</frozen-after-approval>

## Code Map

- `app/begrunnelse/__init__.py` -- `cachet`, `hent_begrunnelse`, `_cache`, `_kall`, `_laas`, `_fra_cache`, `_ekte`. Add `cachet_brief`/`hent_brief` alongside, and factor out the shared cache/cap path instead of duplicating it. Keep the key shape for the justifications.
- `app/begrunnelse/input.py` -- `lag_fakta`. Reuse it per included call. The brief facts get a window header (from–to, number of calls, number assessed by the model, number of alerts) and per-call fields with a numbered prefix.
- `app/begrunnelse/kontroll.py:113` -- `kontroller`, `MAKS_TEGN`, `MAKS_SETNINGER`, `antall_setninger`. Add `maks_tegn`, `min_setninger`, `maks_setninger` parameters with today's defaults.
- `app/begrunnelse/openrouter_klient.py:35-46` -- `_prompt`/`bygg_prompt` read only `prompt.md`. Add a file parameter (default `prompt.md`). Check that `MAKS_TOKENS` = 300 covers 700 characters.
- `app/begrunnelse/testmodus.py`, `klartekst.py` -- `mal`, `innledning`, `varighet`, `DELEGERT_KLARTEKST`. Add the brief template and opening here.
- `app/__init__.py:27-54,103-122` -- `_rader` (already has the pairs, `prediktor`, `naa`) and `forside`. Pass `cachet_brief` to the template. Add `POST /brief`.
- `app/templates/forside.html:5` -- the brief section goes first in `innhold`, before the predictor strip, and only when `rader` is non-empty.
- `app/static/begrunnelse.js` -- generalise to every `[data-ki-url]` region. Screen C keeps working (`anlop.html` data attributes).
- `tests/conftest.py:21-60` -- the test-row guard and the AI guards. Do not change them.
- `docs/ux/dashbord.md` §2, §5, §6; `docs/arkitektur.md:157`; `docs/epics.md:397-402` -- the brief in the sketch notes, states, UU rows (aria-live and no-JS for the brief, plus the outside-reader check as ☐), the `hent_brief` signature, and ✅ in the commit.

## Tasks & Acceptance

**Execution:**
- [x] `app/begrunnelse/kontroll.py`, `openrouter_klient.py` -- limit and prompt-file parameters with unchanged defaults
- [x] `app/begrunnelse/klartekst.py`, `testmodus.py`, `input.py` -- selection, B2 opening, test-mode template, B1 app brief, brief facts
- [x] `app/begrunnelse/prompt_brief.md`, `__init__.py` -- `brief-v1`, `cachet_brief`, `hent_brief`, shared cache/cap
- [x] `app/__init__.py`, `forside.html`, `begrunnelse.js` -- section, `POST /brief`, generalised JS
- [x] `tests/test_begrunnelse.py`, `tests/test_ruter.py` -- every matrix row, selection and sorting, > 3 alerts, the 3/5-sentence and 700-character limits, the shared cap, screen C unchanged, key-leak test
- [x] `docs/…` -- as in the Code Map, and `docs/beslutninger/13` gets a line on the brief cost

**Acceptance Criteria:**
- Given test mode and no network, when `pytest` runs, then everything is green and no socket is opened.
- Given a fake transport that sleeps 30 s, when `GET /` is requested, then it answers 200 in < 1 s with «Henter oversikt …».
- Given a window with no alerts, or `PREDIKTOR=baseline`, in real mode with a fake transport, when `GET /` and `POST /brief` are requested, then the transport is not called and the brief is labelled «Laget av appen».
- Given the validation window with Modell v1, then the brief names the alerted calls in deviation order and no other ship.
- Given screen C, when it is opened after the JS change, then all E3-S04 route tests are still green.

## Implementation Notes

- The shared cache/cap path is factored into `_hent_med_cache` and `_kall_og_kontroller`, and the justification keeps its cache key. Screen C's data attributes were renamed to `data-ki-url`/`data-ki-mal` for the shared JS, and the four screen C test assertions were updated to match (attribute names only).
- Mutation check (orchestrator, after the review patches, 2026-11-23): `BRIEF_MAKS_TEGN` 699/701, `BRIEF_MIN_SETNINGER` 2/4, `BRIEF_MAKS_SETNINGER` 4/6, `BRIEF_MAKS_ANLOP` 2/4 and the sort direction. All 9 mutants turned a test red. The implementer's own run (11 mutants, including the tie-break and the lower sentence limit) was also all red.
- Review patches: ship initials («G. M.», «LT.») no longer end a sentence (`_SETNINGSSLUTT`), the all-delegated wording in `app_brief`, the prompt rule on model-assessed calls, the JS source test, the `kontroll.py` docstring, and `begrunnelse.js` plus both POST routes in `docs/arkitektur.md`. Suite: 781 passed.
- After the smoke call (Theodor, 2026-11-23, `brief-v2` and `begrunnelse-v7`):
  - With 3 alerts, `brief-v1` went over 700 characters. The model may now add 1–2 sentences after the opening (`input.brief_setninger_igjen`: about 200 characters per sentence, at least 1 and at most 2), and the check rejects more than that. This gives 2 with 1 alert and 1 with 3 alerts. The 700-character limit is unchanged.
  - «Rekker fram til rapportert ETA» is sent only when the ship is heading toward the harbour (`kurs_mot_havn` > 0) in the shared `lag_fakta`. This applies to both the brief and screen C.
  - Mutation check: 8 mutants, all red.
- `brief-v3` (Theodor, 2026-11-23, after the `brief-v2` smoke call, where the model wrote one sentence per ship although the facts allowed 1):
  - With 2–3 alerts, the model may add one short sentence per ship, and the check allows the opening plus that many, never over 5 in total.
  - For each of those ships only ship, distance, direction and speed are sent.
  - With 1 alert nothing changes (1–2 sentences by length). The 700-character limit is unchanged.
  - Mutation check: 11 mutants, all red.
- `brief-v4`/`begrunnelse-v8` (Theodor, 2026-11-23): distance, speed and direction are written in the past tense, at the last position, with its time when the facts have it. With 2–3 alerts, «Siste AIS-posisjon» is also sent per ship. The new check rule `presens` rejects «er … km», «går med … knop» and «er på vei» for both the brief and screen C. Mutation check: 5 mutants, all red.
- Finding #1 (deferred: `begrunnelse.js` only checked as source text) is now covered: `tests/test_begrunnelse_js.py` runs the script in Node against a fake DOM (`tests/js/begrunnelse_harness.js`). It covers the failure branch (network error, HTTP 500, invalid text, invalid label) and the success branch for screen C and the brief, and it is skipped when `node` is missing. Mutation check: 10 mutants in the JS, all red (2026-11-23).

## Review Triage Log

Pass 1 (2026-11-23). Layers: blind-hunter (BH), edge-case-hunter (EC), verification-gap (VG).

| # | Finding | Verdict | Evidence | Route |
|---|---|---|---|---|
| 1 | VG: `begrunnelse.js` is never executed by a test, only its source text | low | No JS harness in the repo (same as E3-S04 #3). The brief's aria-live and no-JS rows in UX §6 are ☐. | defer |
| 2 | VG: `test_begrunnelse_js_finnes_og_bruker_post` asserts `begrunnelse-svar`, which is now only in a comment | low | Confirmed in the diff. Direct test correction. | patch |
| 3 | EC: ship names with initials («G. M. DANNEVIG», «LT. PETE MAVERICK MITCHELL») count as extra sentences in the brief opening | medium | Both names are in the extract (717 names checked). `_SETNINGSSLUTT` splits after «G.». The template breaks its 3-sentence contract, and model replies fail `setninger`. | patch |
| 4 | EC/BH: `POST /brief` can 500 if `_par` or the fallback `testbrief` raises | false | Both run in `GET /` first (`_par`, `brief_mal`), so a failure there already breaks the page before the JS ever posts. Same as E3-S04 #20. | reject |
| 5 | EC: `GET /` 500s if `cachet_brief`/`testbrief` raises | maybe-false | No input shown that makes them raise; alerted rows always carry `predikert_avvik_min` (`modell.py:113`). A guard would add a branch. | reject |
| 6 | EC: `POST /brief` on an empty window returns a «0 anløp» text | low | The section and the JS are not rendered for an empty window, so only a hand-made POST reaches it. | reject |
| 7 | EC/BH: `app_brief` infers «baseline active» from row data | false | Under Modell v1 every row has `metode == "modell"` or `delegert` (`modell.py`). Only the baseline produces neither. | reject |
| 8 | EC/BH: all rows delegated gives «Modellen har vurdert 0 av dem … De N andre» | low | Real: a window with only passenger or in-zone calls. Direct text correction. | patch |
| 9 | EC: «Alle anløpene er vurdert» when some rows are neither model nor delegated | false | Same as #7: that mix does not occur under Modell v1. | reject |
| 10 | EC: `predikert_avvik_min` missing or None on an alerted row | false | `forventet_forsinket is True` is only set by `ModellPrediktor`, which always writes the key (`modell.py:113`). | reject |
| 11 | EC/BH: the brief cache key does not cover `par` | false | `STANDARD_NAA` is fixed per app, and the extract and model are read-only per process. Same as E3-S04 #7. | reject |
| 12 | EC/BH: `retning=0` rejects «tidligere» or allows it globally | low | This is the frozen rule (directions only as they appear in the facts), the same as for the justification. | reject (spec rule) |
| 13 | BH: the prompt says 600 characters and the check 700 | false | Deliberate margin, as in `begrunnelse-v4` (prompt 300, check 400). | reject |
| 14 | BH: E3-S05 is ✅ in `docs/epics.md` while manual checks are open | low | Same practice as E3-S04 (✅ with UU rows ☐). The open checks are in `issues.md`. | reject |
| 15 | BH: `MAKS_TOKENS` = 300 may truncate the brief | maybe-false | A truncated reply is caught as `avkortet` by the client and logged. Only the smoke call shows whether 300 is enough. | reject (smoke call settles it) |
| 16 | BH: the prompt refers to «Metode», but the keys are «Anløp N – Metode» | low | Confirmed. Direct prompt wording fix (`brief-v1`, never smoke-called). | patch |
| 17 | BH: dead or redundant code (`_antall` with the same forms, unreachable branches in `_brief_linje`, `testbrief` called twice) | low | Cosmetic, no harm to users. | reject |
| 18 | BH: the JS 20 s timeout is not tuned for the brief | false | The server call times out at `LLM_TIMEOUT_S` = 8 s, well inside 20 s. | reject |
| 19 | BH: arkitektur does not list `begrunnelse.js` or `POST /brief` | low | Confirmed. Direct doc fix. | patch |
| 20 | BH: the UX §2 sketch is not redrawn | low | The note says so explicitly. Redrawing is cosmetic. | reject |
| 21 | BH: the `kontroll.py` docstring is badly reflowed, and `lengde` reads «400 tegn» only | low | Confirmed. Direct docstring fix. | patch |

## Verification

**Commands:**
- `.venv/bin/python -m pytest -q` -- expected: all green, no network

**Mutation check:** the 3/5 sentence limits, 700 vs 701 characters, the top-3 cut-off and the sort direction. Each mutant must turn a test red.

**Manual checks:**
- In the preview (`LLM_MODUS=ekte` for Preview): the brief on the standard window, keyboard and VoiceOver, and a blocked `POST /brief`. The outside-reader check is an open item for the group.
