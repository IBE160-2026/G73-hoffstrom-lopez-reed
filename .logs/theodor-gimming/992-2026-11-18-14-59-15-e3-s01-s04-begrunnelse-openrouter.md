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

## 2026-11-18 kl. 15:09 — Theodor Gimming (review og mutasjonssjekk)

### Oppgave
Fullføre bmad-build-flyten for E3-S01–S04: kontrollere implementeringen mot diffen, kjøre review med tre lag, rette funnene, mutasjonssjekke grensene og åpne PR. Ikke merge før gruppa har sett PR-en og forhåndsvisningen, og ikke gjøre røykkallet før Theodor ber om det.

### Plan
- Kontrollere oppgavene og matrisen mot diffen fra `cfb4609`.
- Review med tre lag (blind-hunter, edge-case-hunter og verification-gap), triage i specen og rettinger gjennom implementeringsagenten.
- Mutasjonssjekk med `PYTHONDONTWRITEBYTECODE=1`, så PR mot `main`.

### Resultat
- Hver rad i matrisen har en test som kjører. Modellnavnet står bare i `konfig.py`.
- **Review:** 26 funn. 13 er rettet, 2 er utsatt (`deferred-work.md`: JS-en er bare sjekket som kildetekst, og `reasoning`-parameteren er ukjent til røykkallet), og 11 er forkastet med begrunnelse. Alt står i Review Triage Log i specen.
  - Viktigst: tallkontrollen så ikke fortegn («+12» ble godtatt mot «−12»), og tallene i etikettene var tillatt.
  - Også rettet: «−0», `inf` i konfigurasjonen, etterfølgende nuller, en myk bindestrek som ikke synes i kildekoden, testhull for varselgrenene og fortegnet på skjerm C, tidsmåling uten oppvarming, og epic-konteksten og testreferansene i `docs/epics.md`.
- **Rettingene er committet per story:** `f7f265d` (S01), `49bab53` (S02), `f530965` (S03), `3a642e1` (S04) og `e8f20b6` (specen er ferdig).
- **Mutasjonssjekk (Claude, etter reviewen):** alle 14 mutanter ble fanget, og kontrollkjøringen var grønn. Mutantene var kallgrensen satt til 19 og 21 og `>=` byttet til `>`, cache-tiden satt til 299 og 301 og `>=` byttet til `>`, et godkjent svar som utløper, 401 og 399 tegn og `>` byttet til `>=`, 4 og 2 setninger, fortegnskontrollen fjernet, og tall i etikettene tillatt igjen.
- **Suiten:** 584 passed, uten nett.
- **KI-feil** er ført i `docs/refleksjon/notater.md` (`1d9c48e`): de gamle `.pyc`-filene i mutasjonssjekken, tallkontrollen uten fortegn, og «han» om Theodor.
- Ingen ekte kall er gjort, og verdien i `.env` er ikke lest.

### Åpne punkter
- Overskriften «Hvorfor avvik er ventet» står også over baselinerader og rader uten varsel (review-funn 26). Den kommer fra UX §4 og S1, så Theodor og gruppa må avgjøre om den skal endres.
- Kontrollen fanger ikke retningsord («senere», «tidligere») eller tall skrevet med ord. Det må følges med på i røykkallet.
