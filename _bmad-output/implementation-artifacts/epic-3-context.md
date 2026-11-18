# Epic 3 Context: Generativt AI-lag med testmodus

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->
<!-- Sources: docs/epics.md, docs/prd.md, docs/arkitektur.md, docs/ux/dashbord.md, docs/beslutninger/11–12, plus provider facts decided 2026-11-18 (to be recorded as decision 13). The project keeps its planning docs in docs/, not in _bmad-output/planning-artifacts. Compiled 2026-11-18. -->

## Goal

Add a generative AI layer that writes a short per-call justification on the detail page and a disruption brief at the top of the main screen, so the examiner can see the explanations without an API key. Test mode is the default. It shows recorded real answers for the demo windows and otherwise a deterministic template, and it never touches the network. Real mode calls an LLM through an adapter and falls back to test mode on any problem. Done when the app runs with `LLM_MODUS=test` offline, and real mode has been shown and logged at least once. Phase 5, 28 Nov–5 Dec, on branch `epic/e3-ai-lag`.

## Stories

- E3-S01: Adapter and test mode
- E3-S02: Input built from the model's actual data
- E3-S03: Real client and versioned prompt
- E3-S04: Justification on the detail page
- E3-S05: Disruption brief on the main screen
- E3-S06: Recording real answers for demo days
- E3-S07: README for the AI layer
- E3-S08: Map (optional)

## Requirements & Constraints

- **Mock-fallback, never fail hard.** A missing key, failed call or rejected answer never gives HTTP 500, an empty page, or a page without the call list. The page always answers 200. Real mode without a key is not an error: the app starts and shows test mode.
- **Never wait on the LLM.** `GET /` and the detail page load in under 1 s whether the call finishes, fails or never answers. If the answer is not ready, test-mode text is shown. How to avoid waiting (background call, precompute, other) is an E3 design choice. On Vercel, keep in mind that work started after the response is sent may not survive.
- **Validate every answer before showing it.** Fall back to test-mode text labelled «Testmodus (ekte kall feilet)» when: the call fails (network, HTTP, invalid key), the answer is empty or whitespace, it breaks the length limit, or it contains a number or ship name that is not in the input. Log the reason, call and predictor, never the key.
- **Length limits.** Justification: at most 3 sentences and ≤ 400 characters. Brief: 3–5 sentences (reject over 5).
- **Input is the model's own data only.** Build input only from `Prediksjon.forklaring` and `Anlop` fields. Ground truth (actual arrival, delay facts) is never sent, since the harbour watch does not know it. On the baseline, the text describes group, horizon and the group's historical spread, and never claims a deviation is expected. Rows delegated to the baseline (`forklaring["delegert"]`: `passasjer`, `ingen_tilstand`, `i_sonen_ved_kutt`, `ingen_featurerad`) follow the same rule.
- **Brief content.** Covers at most 3 alerted calls, sorted by predicted deviation. With no alerts, or with the baseline active, it says so plainly. A manual check is required: someone outside the group reads the brief for the default window and names, unaided, which calls to watch and why. The result is logged in `docs/ux/dashbord.md` §6.
- **Cost: cache and call cap.** At most one real call per (call, predictor) for justifications and per («nå», predictor) for the brief. Answers, including failed validations, are cached in memory, so repeat visits make no new calls. At most 20 real calls per app lifetime (`LLM_MAKS_KALL`). Over the cap, show test-mode text labelled «Testmodus (kallgrensen er nådd)».
- **Budget backstop.** The OpenRouter key from the lecturer has a hard total limit of USD 20. Because the per-session cap is per Vercel instance (see below), the total number of calls across instances is not bounded by `LLM_MAKS_KALL` alone. Keep real-mode use deliberate.
- **Test mode.** Shows recorded real answers for the demo windows 08.10.2025 08:00 and 17.09.2025 08:00 when they exist, otherwise a deterministic template. Both are clearly labelled. README names the demo windows.
- **Secrets.** Keys only in the local `.env` (gitignored) and in Vercel env vars. No key is needed to run or test. Agents must never open, print or commit `.env`.
- **Tests.** `pytest` runs with no network and no `pipeline/data/`. AI tests use test mode or a mocked client, with network calls blocked. One story = one commit, story ID first. Logs go in `.logs/<bruker>/`, and the first real prompt and answer are logged there.

## Technical Decisions

- **Adapter with test mode as default (A8).** `app/begrunnelse/__init__.py` exposes `hent_begrunnelse(prediksjon, anlop)` and `hent_brief(vindu)` and picks the mode from `LLM_MODUS` (`test` | `ekte`, default `test`). `testmodus.py` holds recording lookup and the deterministic template. The prompt is versioned in `app/begrunnelse/prompt.md`. Routes never call the provider directly.
- **Provider (decided 2026-11-18, decision 13; overrides the Anthropic wording in A8, the architecture's config section and E3-S03).** Real mode uses OpenRouter with the key in `OPENROUTER_API_KEY`. The model is chosen by the lecturer: `deepseek/deepseek-v4.1-flash-1017`, with price-floor routing (cheapest provider). `LLM_MODELL` should default to that ID. E3-S03 must update the planned `anthropic_klient.py` name, the `ANTHROPIC_API_KEY` and `claude-haiku-5-5` lines in `.env.example`, and the planned `anthropic` dependency. Any new dependency is justified in that story's commit message. `.env.example` already contains `OPENROUTER_API_KEY`.
- **Vercel (production).** Serverless with a read-only filesystem. The LLM cache lives only in process memory, never on disk, so the cache and the call cap apply per function instance. `OPENROUTER_API_KEY` is set in Vercel env for Production and Preview. Recorded answers (`data/begrunnelser_opptak.json`) are made locally by `scripts/ta_opp_begrunnelser.py` and committed. The app never writes them.
- **Prediction contract (A5) is unchanged.** `Prediksjon.forklaring` (at least `metode` and `gruppe`; the baseline adds `offset_minutter`; delegated rows carry `delegert`) is the AI layer's only view of the prediction. `ModellPrediktor` ("Modell v1") alerts when predicted deviation > 120 min and predicts only Øvrige with AIS state outside the arrival zone at the cut point.

## UX & Interaction Patterns

- Detail page (screen C): a section "Hvorfor avvik er ventet" with the text labelled «KI-GENERERT» in real mode or «Testmodus» in test mode. Recorded answers show that they are recordings.
- Main screen (screen A): the brief sits at the top, above the list.
- Fallback labels are exact: «Testmodus», «Testmodus (ekte kall feilet)», «Testmodus (kallgrensen er nådd)». Labels are text, never colour alone. The rest of the page renders as before in every AI state.

## Cross-Story Dependencies

S01 → S02 → S03 → S04 → S05 → S06 → S07, strictly in order. S01 builds on E2-S07 (`ModellPrediktor`), or on E1-S04 if E2 slips. S06 needs the real client (S03) and a valid key. S07 repeats the E1-S16 clone test with the AI layer. S08 (map, FR14) is only started if S01–S07 are done before 3 Dec, and its scope is settled first.
