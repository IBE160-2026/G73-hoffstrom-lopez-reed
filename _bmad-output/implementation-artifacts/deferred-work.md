- source_spec: `_bmad-output/implementation-artifacts/spec-e1-s01-prosjektskjelett.md`
  summary: Move inline comments in `.env.example` to their own lines before any story starts loading `.env`.
  evidence: maybe-false — copied verbatim from architecture §7; some loaders keep `  # …` in the value. Settle by loading the file with whatever loader the first config-reading story (E1-S04 `PREDIKTOR`) chooses.
- source_spec: `_bmad-output/implementation-artifacts/spec-e1-s04-prediktor-og-baseline.md`
  summary: E2-S07 must show that ModellPrediktor reads no AIS state newer than `t_kutt`, with the state delivered through the prediction boundary rather than read from `data/utdrag/` by the predictor module.
  evidence: E1-S04's contract test proves `t_kutt ≤ naa` and that the input carries no ground truth, but in E1 there is no AIS state to leak; the AST rule now forbids predictor modules from reading `data/utdrag/tilstand_ved_kutt.csv`, so E2 must route state through the boundary and test it there.

- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md`
  summary: Detect truncated Kystdatahuset answers in `fetch_ais_kutt.py`, which are currently cached as `ok`.
  evidence: maybe-false, medium if true. Decision 09 saw truncation only on windows < 1 day ending just after midnight, and E2-S02 requests 90 h. To settle it, re-fetch a sample of `ok` voyages with a shifted window and compare the point counts in [t_H − 24 h, t_H].

## Deferred from: code review of spec-e2-s02-ais-henting-ved-kuttpunkt.md (2026-11-05)

- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md`
  summary: Give permanent data holes their own status in `fetch_ais_kutt.py`, for example a cache status `mangler` together with a `--prov-*` flag.
  evidence: Today a `ManglerDag` that cannot be split leaves the voyage uncached. It is then retried on every run and counted like a downtime failure in `ais_kutt_dekning.csv`. A voyage with a hole is cached as `ok` and is never refetched, even if Kystdatahuset adds the table later. Affects 0 voyages so far (05.11). Deferred by Felipe 2026-11-05.
- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md`
  summary: Record the sub-windows, the number of calls and the missing days in `ais_kutt_logg.csv`.
  evidence: The call log shows only the original window and status `ok` for split voyages. The missing days are in the cache (`manglende_dager`) and in `ais_kutt_dekning.csv`. Changing the columns would break a log CSV that is already half-written by the running fetch.
- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s06-evalueringsskript.md`
  summary: The `--test` path of `scripts/evaluer.py` (argument mapping and model arm on the test split) is never exercised by a test.
  evidence: Medium if true, unverified. Settle with a dry run on a copy of `metrikker.json` before the single test run in E2-S10, or a pytest on the synthetic fixture if the group allows it.
- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s07-modellprediktor.md`
  summary: The `velg_prediktor` docstring in `app/prediksjon/__init__.py` still says no model artifact exists; update it when E2-S08 wires `ModellPrediktor` into `velg_prediktor`.
  evidence: E2-S07 review finding 10; E2-S07 was not allowed to change `velg_prediktor`.
