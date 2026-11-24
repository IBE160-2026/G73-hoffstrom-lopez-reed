# Sjekkliste før levering

## 2026-11-24 kl. 23:03 — Theodor Gimming

### Oppgave
Theodor ba om en sjekkliste for det som gjenstår før levering 15.12. Den skulle ha med:
- hvert krav fra sensorveiledningen (del 1) og rapportmalen, med status og hvor det er dekket;
- det som gjenstår i E3;
- hva agenten kan hjelpe med i rapporten, og hva hver må skrive selv;
- et forslag til fordeling og datoer.

Kursmaterialet skulle ikke kopieres inn. Arbeidet skulle gjøres på en egen gren fra `main`, med push og PR, uten merge og uten å endre `issues.md`.

### Plan
- Lese kildene lokalt: sensorveiledningen (PDF i `~/Downloads`), rapportmalen, `docs/refleksjon/rapport.md` og `notater.md`, `issues.md` og `epics.md`.
- Sjekke repoet mot hvert kriterium: README, `.gitignore`, `.env` i historikken, commits per måned og per person, PR-er med review-status, linter og ☐-stories.
- Skrive `docs/levering-sjekkliste.md` med egne ord, med lenke til den eldre [`docs/vurderingskriterier.md`](../../docs/vurderingskriterier.md).

### Resultat
- Grenen `docs/levering-sjekkliste` er laget fra `main` (`3fbe4cd`). Commit `1b4f3d7` (E0-S23, også ført i E0-tabellen i `epics.md`).
- Det som ble funnet 24.11, og som står i sjekklista:
  - Ingen PR har en godkjent review, og PR #5, #11 og #12 ble merget uten.
  - `git shortlog`: Theodor 144, Felipe 70 og Thomas 1.
  - Ingen linter eller formatter.
  - README mangler AI-laget (E3-S07) og lenker til PRD, arkitektur, epics og logger.
  - 10 KAN-stories i E1 står som ☐, men deler av S11 og S12 er levert.
  - Rapporten har ca. 1 700 ord, mot 3 000–5 000 i malen. Student-ID, dato og 7.4 mangler.
  - `.env` er aldri committet.
- `issues.md` er ikke endret, slik Theodor ba om, så det ikke blir flere konflikter med PR #13 og PR #14. De nye åpne punktene står bare her.
- Kursmaterialet er ikke kopiert inn. Sjekklista oppsummerer med egne ord.

### Åpne punkter
- Gruppa går gjennom forslaget til fordeling og datoer i `docs/levering-sjekkliste.md` §4 og blir enige om det. Når PR #13 og PR #14 er merget, føres de avtalte punktene inn i `issues.md`.
- Rydde i `docs/epics.md`: status for KAN-storyene, og hva av E1-S11 og E1-S12 som er levert gjennom E3-S04 og E2-S09.
- README: lenker til PRD, arkitektur, epics, UX, `.logs/` og `notater.md`, en kort mappeoversikt, og én form av Theodors navn (README sier «Theodor Gimming Hoffstrøm»).
- Vurdere en linter eller formatter (for eksempel `ruff`) og én opprydningsrunde i koden før levering.
