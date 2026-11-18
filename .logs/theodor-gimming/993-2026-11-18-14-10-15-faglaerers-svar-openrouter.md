# Faglærers svar: technology.md og OpenRouter-nøkkel

## 2026-11-18 kl. 14:10 — Theodor Gimming

### Oppgave
Følge opp faglærers svar på de to spørsmålene fra 17.11: (a) kurset deler ut en OpenRouter-nøkkel med bruksgrense, god nok til å teste appen, og (b) `technology.md` var en rest som ikke skal brukes. Fjerne fila, gjøre klar en lokal `.env` for nøkkelen og levere gjennom en liten PR. Nøkkelen skal aldri inn i chat, logger, kode eller git, og Claude skal ikke lese eller teste den før Theodor sier fra.

### Plan
- Gren `chore/e0-s22-technology-og-env`, story-ID E0-S22 (sjekket ledig i `docs/epics.md` og `git log --all`).
- Fjerne `technology.md`, lage `.env` med bare `OPENROUTER_API_KEY=`, oppdatere `.env.example`, kjøre suiten, PR og merge.

### Resultat
- `90e939c`: `_bmad-output/planning-artifacts/architecture/technology.md` er fjernet. Den tomme mappa forsvant med den. Commit-meldingen viser til faglærers svar.
- `0a66c14`: `.env.example` har fått `OPENROUTER_API_KEY=<din-nøkkel-her>` med en kommentar om at nøkkelen bare står i `.env`. E0-S22 står i tabellen og endringsloggen i `docs/epics.md`.
- `.env` er laget i rotmappa med bare linjen `OPENROUTER_API_KEY=` (uten verdi). `git check-ignore -v .env` gir `.gitignore:42`, `git status` viser den ikke, og `git ls-files` har ingen `.env`.
- Suiten: 498 passed. Repoet har ingen CI, så suiten ble kjørt lokalt.
- PR #10 er åpnet. Punktene om `technology.md` og om nøkler i `issues.md` er lukket.
- Nøkkelen er ikke lagt inn, lest eller testet.

### Åpne punkter
- E3 må avgjøre leverandøren. Arkitekturen (`docs/arkitektur.md`), `.env.example` og E3-S03 i `docs/epics.md` sier Anthropic (`ANTHROPIC_API_KEY`, `anthropic_klient.py`), mens kursnøkkelen er til OpenRouter.
- Theodor legger nøkkelen inn i `.env` selv. Den er ikke testet før han sier fra.
