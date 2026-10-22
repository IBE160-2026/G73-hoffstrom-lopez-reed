- source_spec: `_bmad-output/implementation-artifacts/spec-e1-s01-prosjektskjelett.md`
  summary: Move inline comments in `.env.example` to their own lines before any story starts loading `.env`.
  evidence: maybe-false — copied verbatim from architecture §7; some loaders keep `  # …` in the value. Settle by loading the file with whatever loader the first config-reading story (E1-S04 `PREDIKTOR`) chooses.
