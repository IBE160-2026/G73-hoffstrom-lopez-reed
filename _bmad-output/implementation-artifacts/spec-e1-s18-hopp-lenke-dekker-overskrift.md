---
title: 'E1-S18 — Hopp-lenken dekker overskriften ved fokus'
type: 'bugfix'
created: '2026-11-05'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Finding from the UU check on 2026-11-03 (E1-S16): when the skip link («Hopp til innhold») has focus, it is drawn on top of «ANKOMSTPREDIKSJON» and the first letter of «Anløp», because `.hopp:focus` only moves the absolutely positioned link to `top: 0.5rem`.

**Approach:** On focus, the skip link joins the normal flow at the top of the page (static position, its own space), so the header moves down instead of being covered. It stays the first Tab stop, it is hidden until focused, and its text, target and colours are unchanged. Felipe asked for the short BMAD flow (2026-11-05); the test is manual UU2 in UX §6, and `tests/test_uu_struktur.py` stays green.

</frozen-after-approval>

## Implementation Notes

- `app/static/style.css`: `.hopp:focus` is now `position: static; display: inline-block; margin: 0.5rem 1rem 0`. The link takes its own space at the top on focus and pushes the header down. It is unchanged off focus (absolute, `top: -10rem`).
- `tests/test_uu_struktur.py`: `test_hopplenke_dekker_ikke_overskriften_ved_fokus` guards the chosen CSS. Mutation-checked: putting `top: 0.5rem` back instead of `position: static` fails it.
- Status stays `in-review` and epics shows ◐ until a human has run the manual UU2 check in UX §6. That check is the story's own test. I could not see the focused state myself: the screenshot script captures the page without focus.
- 2026-11-05: Theodor Gimming ran the manual UU2 check against `fix/e1-s18-s19`. The skip link no longer covers «ANKOMSTPREDIKSJON» or «Anløp» on focus, the focus ring is clear, and Enter goes to `#anlopslista`. UX §6 is filled in and E1-S18 is ✅.

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
