# E3-S01–S04: begrunnelse via OpenRouter

## 2026-11-18 kl. 14:59 — Theodor Gimming

### Oppgave
Implementere specen for E3-S01–S04 (begrunnelse per anløp via OpenRouter, uten å vente på språkmodellen), med specen som eneste sannhetskilde. Én commit per story.

### Plan
- Spec: [`spec-e3-s01-s04-begrunnelse-via-openrouter.md`](../../_bmad-output/implementation-artifacts/spec-e3-s01-s04-begrunnelse-via-openrouter.md), kontekst: `epic-3-context.md` og `docs/ux/dashbord.md`.
- S01 adapter/konfig/testmodus + vakter i conftest + PRD FR11b, S02 `lag_fakta`, S03 klient/prompt/kontroll + beslutning 13 og arkitektur, S04 skjerm C + JSON-endepunkt + UX §6.

### Resultat
- `c19c67e` E3-S01: `app/begrunnelse/{konfig,testmodus,__init__}.py`. Cache per (voyageid, prediktor): et godkjent svar beholdes så lenge prosessen lever, en feil i 300 s. Kallgrense på 20 forsøk per prosess, under en lås. Autouse-vakt i `tests/conftest.py` (ingen nøkkel, testmodus, socketer sperret, tom cache). FR11b i PRD er endret (S5–S6).
- `1398aca` E3-S02: `input.py` (`lag_fakta`). Bare `PrediksjonsInput` + `Prediksjon`, ingen MMSI, seilas-ID eller fasit.
- `84c0d41` E3-S03: `openrouter_klient.py` (urllib, transporten kan byttes ut, `max_tokens` 300, årsakskoder), `prompt.md` (`begrunnelse-v1`) og `kontroll.py`. Nye `docs/beslutninger/13-openrouter-og-modell.md`. Rettet: A8, §5, §7, §9 og §11 i arkitekturen, og `.env.example` (Anthropic er fjernet). Leverandørspørsmålet i PRD §8 er lukket.
- `64e5831` E3-S04: `GET /anlop/<id>` (skjerm C, 404 for ukjent seilas) og `POST /anlop/<id>/begrunnelse` (alltid 200 med `{tekst, merke}`). Også `aria-live`, `<noscript>`, `begrunnelse.js`, skipsnavnet som lenke på skjerm A og UX §4–§6.
- Suiten: 575 passed (ca. 30 s), uten nett. `grep deepseek|openrouter.ai app/` gir bare `konfig.py` og URL-konstanten i klienten.
- Mutasjonssjekk: 14 av 14 mutanter ble fanget (kallgrense 19/21 og `>`, TTL 299/301 og `>`, et godkjent svar som utløper, 400/401 tegn, 3/4 setninger, max_tokens, GET som kaller språkmodellen), og en kontrollkjøring uten endring overlever. Feil fra KI fanget underveis: første kjøring av mutasjonene ga gamle `.pyc` (`sys.pycache_prefix` er satt, og mtime ble lik innenfor samme sekund). Kjørt på nytt med `PYTHONDONTWRITEBYTECODE=1` og tømt cache.
- Ingen ekte kall er gjort, og `.env` er ikke lest.

### Åpne punkter
- Røykkall i ekte modus på skjerm C, bare når Theodor ber om det. Prompt og svar logges her, uten nøkkelen (E3-S03).
- Manuell UU-sjekk av skjerm C (tastatur, aria-live med VoiceOver, uten JS), som står med ☐ i UX §6.
- Kostnadsoverslaget i beslutning 13 sjekkes mot OpenRouters priser før levering.
- PR for `epic/e3-ai-lag` merges ikke før gruppa har sett den og forhåndsvisningen på Vercel.
