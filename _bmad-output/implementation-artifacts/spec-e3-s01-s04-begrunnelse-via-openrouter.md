---
title: 'E3-S01–S04 — Begrunnelse per anløp via OpenRouter, uten å vente på språkmodellen'
type: 'feature'
created: '2026-11-18'
status: 'in-progress'
baseline_commit: 'cfb460912a21edd5f8033a70ddd296f3364db1a9'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/docs/ux/dashbord.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The app has no AI layer. FR11 (a short justification per call), FR11a (the page never waits on the LLM) and FR11b (cache and call cap) are unbuilt. The plan still says Anthropic, but the lecturer has provided an OpenRouter key (USD 20 hard limit) and chosen the model.

**Approach:** An adapter `app/begrunnelse/` with test mode as the default (A8). It builds the input only from numbers the app already has, calls OpenRouter in real mode, checks every answer, and falls back to labelled test-mode text on any problem. The page renders without the justification and fetches it afterwards. `docs/beslutninger/13-openrouter-og-modell.md` records the provider, model and routing for the whole project.

## Spec choices S1–S7 (Theodor, 2026-11-18)

S1–S7 are this spec's own choices. They are not the project decisions in `docs/beslutninger/`. Project-wide decisions are referred to as `docs/beslutninger/NN`.

- **S1 — Screen C is built here, minimal:** `/anlop/<voyageid>` with ship data, times in a `<dl>`, «Slik ble prediksjonen laget» (the FR7 template per group), the section «Hvorfor avvik er ventet» with the justification, a back link to the list, and 404 with a back link for an unknown ID. It uses `STANDARD_NAA` and has no `naa`/fasit query yet. The ship name on the main screen links to it. This also delivers the core of E1-S11.
- **S2 — Routing is the `:floor` suffix:** the model string is `deepseek/deepseek-v4.1-flash-1017:floor`, built in `konfig.py` from `LLM_MODELL` + `LLM_ROUTING`. Flex endpoints may be used, and capacity errors go to the fallback.
- **S3 — Production:** the code defaults to `LLM_MODUS=test`. Theodor sets `LLM_MODUS=ekte` in Vercel after the smoke call. Claude changes no Vercel settings.
- **S4 — Size:** the full spec is kept (about 2,700 tokens), with one commit per story S01–S04.
- **S5 — Cache lifetime:** a successful (checked) answer is cached for the life of the process. Every failure (call error, timeout, 402, failed check) is cached for only `LLM_FEIL_TTL_S` = 300 s. After that, the next visit makes a new attempt, which counts against the cap. A temporary timeout therefore does not give test mode for the rest of the instance's life. A missing key makes no call and counts nothing.
- **S6 — Deliberate deviation from FR11b, recorded in the PRD:** FR11b says «høyst 20 ekte kall per økt (appens levetid)» and «En demo koster dermed høyst 20 kall». On Vercel every function instance is its own process with its own memory, and there can be several at once and new ones over time. The cap is therefore per process (per instance), not per demo or overall. A shared counter would need external storage (a database or KV), which the app does not have and which architecture §11 rules out on disk. The total spend is stopped by the USD 20 limit on the key at OpenRouter, not by the app. When the limit is reached, OpenRouter answers 402, and the app shows «Testmodus (ekte kall feilet)» and logs `kvote_402`. Failures that are cached for 5 min instead of «for the app's lifetime» are also a deviation from FR11b, and they are recorded in the same update.
- **S7 — Accessibility on screen C:** when the justification arrives, it is announced through an `aria-live="polite"` region (the region exists in the HTML from the start, and only its content changes). The whole page can be used with the keyboard only: back link, ship-name link from the list, visible focus and no focus trap. The page works without JavaScript. A cached answer is server-rendered as usual. Otherwise `<noscript>` shows the test-mode template text labelled «Testmodus». Screen C is added to the UU checklist in `docs/ux/dashbord.md` §6 (UU2 keyboard, UU-aria-live, no-JS), and the manual run is an open item.

## Boundaries & Constraints

**Always:**
- **`docs/beslutninger/13`:** OpenRouter, model `deepseek/deepseek-v4.1-flash-1017`, price-floor routing, chosen on the lecturer's recommendation (2026-11-18). Only numbers and public ship data are sent: ship name, ship group, times, horizon, method, offset or predicted deviation, alert state, delegation reason and the model's feature values. No personal data, no MMSI, no ground truth.
- **Config in one place:** model ID, routing, mode, call cap, failure cache time and timeout are read only in `app/begrunnelse/konfig.py` (`LLM_MODUS`=`test`, `LLM_MODELL`, `LLM_ROUTING`=`floor`, `LLM_MAKS_KALL`=`20`, `LLM_FEIL_TTL_S`=`300`, `LLM_TIMEOUT_S`=`8`). The model string sent to OpenRouter is built there and nowhere else.
- **FR11a:** the page that shows the justification renders without calling the LLM. A cached answer is rendered server-side, so a cache hit is visible in < 1 s. Otherwise the page shows «Henter forklaring …» in an `aria-live="polite"` region and fetches it with `POST /anlop/<voyageid>/begrunnelse` (JSON). Error, timeout, missing key, exhausted quota (HTTP 402) or a failed check → mock text labelled «Testmodus (ekte kall feilet)». The endpoint always answers 200 with `{tekst, merke}`.
- **Answer check (before showing):** non-empty; ≤ 3 sentences and ≤ 400 characters; every number in the text occurs in the input; no other ship name from the extract; no cause words from a fixed list (weather, strike, engine, crew, …). When there is no alert (`forventet_forsinket` is not `True`), the text must not contain `forsink`. The prompt forbids inventing causes. The check is a guard, not proof, and the spec says so.
- **FR11b (as amended, S5–S6):** in-memory cache per (voyageid, predictor name). Success is kept for the life of the process, and failures for `LLM_FEIL_TTL_S` (300 s). At most `LLM_MAKS_KALL` real calls per process, counted per attempt and guarded by a lock. Over the cap → «Testmodus (kallgrensen er nådd)». On Vercel the cache and the cap are per function instance. The total is stopped by the key's USD 20 limit (402). That is written in FR11b, architecture §11 and `docs/beslutninger/13`.
- **Secrets:** the key is read from `OPENROUTER_API_KEY` in `os.environ`, never from a file. It is never written to a log, an exception message, a response or a template. Failures are logged as a reason code with voyageid and predictor only.
- **Tests:** an autouse fixture removes `OPENROUTER_API_KEY`, sets `LLM_MODUS=test` and blocks sockets. The real client is tested only with an injected fake transport and the fake key `sk-or-TEST-IKKE-EKTE`. No test makes a real call. Model rows in route tests use `VALIDERING_NAA` (test-row rule).
- No new dependency: HTTP goes through `urllib.request`.

**Never:**
- Make a real call, read `.env` or print the key, except one manual smoke call when Theodor asks for it.
- Send ground truth (`faktisk_ankomst`, `status_in_area`, `split`) or let the adapter take an `Anlop`. It takes `PrediksjonsInput` + `Prediksjon`.
- Merge the PR before the group has seen it and the Vercel preview (Theodor, 2026-11-18).
- Build the brief (E3-S05), the recordings (E3-S06) or the README section (E3-S07). Write to disk at runtime.

## I/O & Edge-Case Matrix

| Scenario | State | Shown | Logged |
|---|---|---|---|
| Test mode (default) | `LLM_MODUS=test` | template text, «Testmodus» | nothing |
| Real, OK | key, valid answer | answer, «KI-GENERERT» | nothing |
| Real, cache hit | success cached for (voyageid, predictor) | same text, server-rendered, 0 new calls | nothing |
| Failure, < 300 s ago | failure cached | «Testmodus (ekte kall feilet)», 0 new calls | nothing new |
| Failure, ≥ 300 s ago | failure expired | new attempt (counts against the cap) | as the outcome |
| No key | `ekte`, no key | template, «Testmodus (ekte kall feilet)», no call, not counted | `mangler_nokkel` |
| Timeout / network / 5xx / 429 / 401 | — | same | `timeout` / `nett` / `http_<kode>` |
| Quota exhausted (USD 20 used) | HTTP 402 | same | `kvote_402` (tell the lecturer) |
| Check fails | too long, unknown number or name, cause word | same, cached for 300 s | `kontroll_<regel>` |
| Over the cap | 20 attempts done in this process | template, «Testmodus (kallgrensen er nådd)» | `kallgrense` |
| No JavaScript | no cached answer | `<noscript>` template, «Testmodus» | nothing |

</frozen-after-approval>

## Code Map

- `app/prediksjon/__init__.py:38-58` -- `PrediksjonsInput` (no ground truth) and `Prediksjon.forklaring`. The AI layer's only input. Do not change.
- `app/prediksjon/baseline.py:48`, `app/prediksjon/modell.py:108` -- `forklaring` keys: `metode`, `gruppe`, `offset_minutter` | `predikert_avvik_min`, `horisont`, `featurer`, `delegert`.
- `app/__init__.py:31-84` -- `_rader`, `create_app`, `DELEGERT_TEKST`. Reuse `velg_prediktor_med_merknad`, `lag_input`, `anlop_i_vindu` for the new routes. `create_app` reads no `.env` and keeps it that way.
- `app/visning.py` -- `ukedag_klokke`, `til_oslo_minutt`. Times in the prompt use the same format as on screen, so the number check matches.
- `app/templates/forside.html:44` -- the ship-name cell, which becomes a link to screen C (S1).
- `tests/conftest.py` -- `VALIDERING_NAA`, `TESTRADER_TILLATT`, the autouse guards. Add the AI guards next to them.
- `docs/arkitektur.md:46,185-187,207,232` -- A8, the config block, dependencies, §11. Change Anthropic to OpenRouter.
- `docs/epics.md:368-394` -- E3-S01–S04. Change the S03 text (`anthropic_klient.py` → `openrouter_klient.py`) and mark them ✅ in each story's commit.

## Tasks & Acceptance

**Execution:**
- [ ] `app/begrunnelse/konfig.py`, `testmodus.py`, `__init__.py` -- config, template text, `hent_begrunnelse(inp, prediksjon, prediktor_navn)` and `cachet(...)`, cache and cap -- E3-S01
- [ ] `tests/conftest.py` -- autouse: no key, test mode, sockets blocked, cache reset -- E3-S01
- [ ] `app/begrunnelse/input.py` -- `lag_fakta(inp, prediksjon)` → dict with Norwegian labels and screen-formatted values -- E3-S02
- [ ] `app/begrunnelse/prompt.md`, `openrouter_klient.py`, `kontroll.py` -- versioned prompt, client with injectable transport, `max_tokens` 300, error → reason code, answer check -- E3-S03
- [ ] `docs/prd.md` -- FR11b and its test: the cap is per process (per Vercel instance), failures are cached for 300 s, the total is stopped by the key's USD 20 limit (402), and a changelog line -- E3-S01
- [ ] `docs/beslutninger/13-openrouter-og-modell.md`, `docs/arkitektur.md`, `.env.example` -- `docs/beslutninger/13` with the cost estimate and the FR11b deviation, A8 and §11, remove `ANTHROPIC_API_KEY` and `claude-haiku-5-5`, add `LLM_FEIL_TTL_S` -- E3-S03
- [ ] `app/__init__.py`, `app/templates/anlop.html`, `app/static/begrunnelse.js`, `forside.html` -- screen C (S1), the JSON endpoint, `aria-live` and `<noscript>` (S7) -- E3-S04
- [ ] `docs/ux/dashbord.md` §6 -- screen C rows in the UU checklist (keyboard, aria-live, no-JS), marked ☐ until the manual run -- E3-S04
- [ ] `tests/test_begrunnelse.py`, `tests/test_ruter.py` -- every row in the matrix (with an injected clock for the 300 s), the aria-live region and `<noscript>` in the HTML of screen C, key-leak test (fake key absent from caplog, response and exception text), input without ground truth, cache gives 0 new calls, cap at 20, model rows only at `VALIDERING_NAA` -- S01–S04

**Acceptance Criteria:**
- Given `LLM_MODUS=test` and no network, when `pytest` runs, then all tests pass in < 1 min and no socket is opened.
- Given a fake transport that sleeps 30 s, when screen C is requested, then the page answers 200 in < 1 s and contains «Henter forklaring …».
- Given an answer cached for (voyageid, predictor), when screen C is requested again, then the text is in the HTML and the transport is not called.
- Given `grep -rn "deepseek" app/`, then the model ID occurs only in `konfig.py`.
- Given a failure cached at time t, when the same call is requested at t + 299 s, then no call is made. At t + 300 s one new call is made.
- Given screen C with no cached answer, then the HTML has the aria-live region with «Henter forklaring …» and a `<noscript>` with the template text and «Testmodus», and every link can be reached with Tab.

## Design Notes

**Cost estimate** (OpenRouter's public price list, 2026-11-18, per 1M tokens). The cheapest endpoint for the model costs USD 0.036 input and 0.50 output. The most expensive one costs 0.60 and 2.40. One call is about 700 input tokens and at most 300 output tokens (`max_tokens`). That is about USD 0.00018 per call at the floor price, so USD 20 covers about 110,000 calls. Even at the most expensive endpoint it is about USD 0.0011, or about 17,500 calls. A demo with the cap of 20 costs under USD 0.01. Prices change (DeepSeek's own endpoint changes price by time of day), so the estimate is checked again before delivery. Risk: if the model spends output tokens on reasoning, the answer may be empty. The check then gives the fallback, and the smoke call shows whether this happens.

**Why POST and no background thread:** on Vercel, work after the response may be stopped. The call runs inside its own request, which the browser starts after the page is shown. POST keeps crawlers from triggering paid calls.

## Verification

**Commands:**
- `.venv/bin/python -m pytest -q` -- expected: all green, no network
- `grep -rn "deepseek\|openrouter.ai" app/ | grep -v konfig.py` -- expected: only the client's URL constant

- Mutation check (as in E2): the cap (`LLM_MAKS_KALL` off by one: 19/21 must turn a test red), the failure cache time (299/300/301 s, and a success that must never expire), and the length check (3 vs. 4 sentences, 400 vs. 401 characters). Each mutant must turn at least one test red, or a test is added.

**Manual checks:**
- Only when Theodor asks: one smoke call on screen C in real mode. Prompt and answer are logged in `.logs/theodor-gimming/` (E3-S03), without the key.
