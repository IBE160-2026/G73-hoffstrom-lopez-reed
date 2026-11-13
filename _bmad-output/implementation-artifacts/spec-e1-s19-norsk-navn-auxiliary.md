---
title: 'E1-S19 — Norsk visningsnavn for gruppen «Auxiliary»'
type: 'feature'
created: '2026-11-05'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Finding from the UU check on 2026-11-03 (E1-S16), not a UU requirement: the dashboard shows the group name «Auxiliary» (for example G O SARS), an English word among Norwegian group names. It applies to 524 voyages in `data/utdrag/anlop.csv`.

**Approach:** The dashboard shows «Spesialfartøy» instead (Felipe chose the name on 2026-11-05). Only the display changes: `ship_group` in the extract, the checksums and `tests/test_dataregresjon.py` stay untouched, and the Passasjer/Øvrige grouping is unaffected. The PRD glossary and the UX screen A2 sketch use the same name. A test shows that no row displays «Auxiliary». Short BMAD flow (Felipe, 2026-11-05). Nothing in `pipeline/`, `data/` or E2 is touched.

</frozen-after-approval>

## Implementation Notes

- `app/visning.py`: `GRUPPE_VISNINGSNAVN = {"Auxiliary": "Spesialfartøy"}` and `gruppe_visning()`. Unknown groups are shown as in the source.
- `app/__init__.py`: `_rader` uses `gruppe_visning(inp.ship_group)`. `PrediksjonsInput.ship_group`, `Anlop.gruppe` (Passasjer/Øvrige) and the data are unchanged.
- `docs/prd.md` glossary and the `docs/ux/dashbord.md` A2 sketch use «Spesialfartøy». The A2 Gruppe column is 3 characters wider.
- Tests: `test_gruppe_visning` and `test_ingen_rad_viser_auxiliary` (mutation-checked: dropping `gruppe_visning` in `_rader` fails it). `tests/test_dataregresjon.py`, `data/` and `pipeline/` are untouched.
- 2026-11-05: the group approved the name «Spesialfartøy». Theodor Gimming confirmed in the manual check that G O SARS is shown as «Spesialfartøy».

## Review Triage Log

One reviewer (Blind Hunter, short BMAD flow) reviewed E1-S18 and E1-S19 together on 2026-11-05.
- Screenshots in `docs/ux/skjermbilder/` still showed «Auxiliary» — medium, **patch**: reran `scripts/ta_skjermbilder.py`. The overflow measurement passes at 360, 640, 1280 and 1920 px, with the longer name and the skip link in the flow.
- UX doc and PRD changed without a changelog line, and the PRD's description of the group had no source — low, **patch**: changelog lines added. The description now cites the most common vessels in the group.
- UU2 row in UX §6 did not say a fix exists — low, **patch**: added a note that the fix waits for a manual UU2 check.
- Spec files were still `in-progress` with empty notes — low, **patch**: this finalization.
- The E1-S18 test checks CSS text, not behaviour, and its imports were local — low, **patch**: the docstring now says it guards the chosen solution. Imports moved to module level, and the regex tolerates whitespace. Tab order is covered by `test_hopplenke_er_forst_og_virker`.
- The «no row shows Auxiliary» test covers only the default window — low, **patch** (docstring): every row, including the mobile cards, is built by `_rader`, so the default window is enough.
- `:focus` instead of `:focus-visible`; `z-index`/`left` unused when static — rejected (low). The link is hidden off-screen until focused, so a mouse click on it is not a realistic path. The leftovers do no harm.
- The A2 sketch has a ragged right edge — rejected (low): it was there before this change (byte widths differ because of multi-byte characters), and the sketch has no frame.
