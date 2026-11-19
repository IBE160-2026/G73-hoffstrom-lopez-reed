---
title: 'E3-S05 — Disruption brief at the top of the main screen'
type: 'feature'
created: '2026-11-19'
status: 'draft'
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
- [ ] `app/begrunnelse/kontroll.py`, `openrouter_klient.py` -- limit and prompt-file parameters with unchanged defaults
- [ ] `app/begrunnelse/klartekst.py`, `testmodus.py`, `input.py` -- selection, B2 opening, test-mode template, B1 app brief, brief facts
- [ ] `app/begrunnelse/prompt_brief.md`, `__init__.py` -- `brief-v1`, `cachet_brief`, `hent_brief`, shared cache/cap
- [ ] `app/__init__.py`, `forside.html`, `begrunnelse.js` -- section, `POST /brief`, generalised JS
- [ ] `tests/test_begrunnelse.py`, `tests/test_ruter.py` -- every matrix row, selection and sorting, > 3 alerts, the 3/5-sentence and 700-character limits, the shared cap, screen C unchanged, key-leak test
- [ ] `docs/…` -- as in the Code Map, and `docs/beslutninger/13` gets a line on the brief cost

**Acceptance Criteria:**
- Given test mode and no network, when `pytest` runs, then everything is green and no socket is opened.
- Given a fake transport that sleeps 30 s, when `GET /` is requested, then it answers 200 in < 1 s with «Henter oversikt …».
- Given a window with no alerts, or `PREDIKTOR=baseline`, in real mode with a fake transport, when `GET /` and `POST /brief` are requested, then the transport is not called and the brief is labelled «Laget av appen».
- Given the validation window with Modell v1, then the brief names the alerted calls in deviation order and no other ship.
- Given screen C, when it is opened after the JS change, then all E3-S04 route tests are still green.

## Verification

**Commands:**
- `.venv/bin/python -m pytest -q` -- expected: all green, no network

**Mutation check:** the 3/5 sentence limits, 700 vs 701 characters, the top-3 cut-off and the sort direction. Each mutant must turn a test red.

**Manual checks:**
- In the preview (`LLM_MODUS=ekte` for Preview): the brief on the standard window, keyboard and VoiceOver, and a blocked `POST /brief`. The outside-reader check is an open item for the group.
