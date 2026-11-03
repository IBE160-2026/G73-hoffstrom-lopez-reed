- source_spec: `_bmad-output/implementation-artifacts/spec-e1-s01-prosjektskjelett.md`
  summary: Move inline comments in `.env.example` to their own lines before any story starts loading `.env`.
  evidence: maybe-false — copied verbatim from architecture §7; some loaders keep `  # …` in the value. Settle by loading the file with whatever loader the first config-reading story (E1-S04 `PREDIKTOR`) chooses.
- source_spec: `_bmad-output/implementation-artifacts/spec-e1-s04-prediktor-og-baseline.md`
  summary: E2-S07 must show that ModellPrediktor reads no AIS state newer than `t_kutt`, with the state delivered through the prediction boundary rather than read from `data/utdrag/` by the predictor module.
  evidence: E1-S04's contract test proves `t_kutt ≤ naa` and that the input carries no ground truth, but in E1 there is no AIS state to leak; the AST rule now forbids predictor modules from reading `data/utdrag/tilstand_ved_kutt.csv`, so E2 must route state through the boundary and test it there.

- source_spec: `_bmad-output/implementation-artifacts/spec-e2-s02-ais-henting-ved-kuttpunkt.md`
  summary: Detect truncated Kystdatahuset answers in `fetch_ais_kutt.py`, which are currently cached as `ok`.
  evidence: maybe-false, medium if true. Decision 09 saw truncation only on windows < 1 day ending just after midnight, and E2-S02 requests 90 h. To settle it, re-fetch a sample of `ok` voyages with a shifted window and compare the point counts in [t_H − 24 h, t_H].
