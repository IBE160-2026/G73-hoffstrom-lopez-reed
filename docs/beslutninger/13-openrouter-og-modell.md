# OpenRouter og DeepSeek V4.1 Flash for AI-laget

## Kontekst

A8 i arkitekturen sier at AI-laget (E3) ligger bak en adapter med testmodus som standard, og at ekte modus bruker Anthropic API (`anthropic`-pakken). Faglærer har siden delt ut en OpenRouter-nøkkel med en hard bruksgrense på USD 20 til testing (E0-S22), og anbefalt modell 18.11.2026. PRD §8 hadde leverandøren som åpent spørsmål.

På Vercel er hver funksjonsinstans en egen prosess med eget minne (arkitektur §11). Cachen og kallgrensen i FR11b kan derfor bare gjelde per instans, så appen alene kan ikke garantere et øvre tak på antall kall.

Spec: `_bmad-output/implementation-artifacts/spec-e3-s01-s04-begrunnelse-via-openrouter.md` (Theodor Gimming, 18.11.2026).

## Alternativer vurdert

- **Anthropic API, som planlagt i A8.** Forkastet. Gruppa har ingen Anthropic-nøkkel med bruksgrense, og kursnøkkelen er til OpenRouter.
- **OpenRouter med `anthropic`- eller `openai`-pakken.** Forkastet. Det er én POST med JSON, og `urllib.request` fra standardbiblioteket holder. Ingen ny avhengighet å begrunne, låse eller ta med til Vercel.
- **OpenRouter med standard routing.** Forkastet. OpenRouter fordeler da på pris og oppetid, og prisen per kall varierer mer.
- **OpenRouter med `urllib`, modellen faglærer anbefalte, og prisgulv-routing.** Valgt.

## Valg

1. **Leverandør:** OpenRouter (`https://openrouter.ai/api/v1/chat/completions`). Nøkkelen leses fra `OPENROUTER_API_KEY` i miljøet, aldri fra fil, og skrives aldri til logg, unntak, svar eller mal.
2. **Modell:** `deepseek/deepseek-v4.1-flash-1017`, valgt på faglærers anbefaling (18.11.2026). Standardverdien for `LLM_MODELL`.
3. **Routing:** prisgulv (`LLM_ROUTING=floor`). Modellstrengen som sendes, er `deepseek/deepseek-v4.1-flash-1017:floor`, og den bygges bare i `app/begrunnelse/konfig.py`. Flex-endepunkter kan brukes, og kapasitetsfeil går til tilbakefallet.
4. **Hva som sendes:** bare tall og offentlige skipsdata: skipsnavn, skipsgruppe, tider, horisont, metode, offset eller predikert avvik, varseltilstand, grunnen til delegering og et utvalg av modellens featureverdier (`app/begrunnelse/input.py`). Ingen persondata, ingen MMSI og ingen fasit (`faktisk_ankomst`, `status_in_area`, `split`).
5. **Svaret kontrolleres** før det vises (`app/begrunnelse/kontroll.py`), og `max_tokens` er 300. Alle feil gir mal-teksten merket «Testmodus (ekte kall feilet)».
6. **Kostnadsvern (avvik fra FR11b, ført i PRD-en 18.11.2026):** cachen og grensen på 20 forsøk (`LLM_MAKS_KALL`) gjelder per prosess, altså per Vercel-instans, og ikke per demo. En felles teller ville krevd ekstern lagring (database eller KV), som appen ikke har. Det totale forbruket stoppes av bruksgrensen på USD 20 på nøkkelen. Når den er nådd, svarer OpenRouter med HTTP 402, og appen viser «Testmodus (ekte kall feilet)» og logger `kvote_402`. Da må faglærer få beskjed. Feil caches i 300 s (`LLM_FEIL_TTL_S`), ikke i hele levetiden, så et midlertidig tidsavbrudd ikke gir testmodus resten av instansens levetid.
7. **Produksjon:** koden har `LLM_MODUS=test` som standard. Theodor setter `LLM_MODUS=ekte` i Vercel etter røykkallet. Claude endrer ingen innstillinger i Vercel.

## Kostnadsoverslag

OpenRouters offentlige prisliste, 18.11.2026, per million tokens. Det billigste endepunktet for modellen koster USD 0,036 for input og 0,50 for output. Det dyreste koster 0,60 og 2,40.

- Ett kall er omtrent 700 input-tokens og høyst 300 output-tokens (`max_tokens`).
- Med prisgulv blir det omtrent USD 0,00018 per kall, så USD 20 dekker omtrent 110 000 kall.
- Selv på det dyreste endepunktet er det omtrent USD 0,0011 per kall, eller omtrent 17 500 kall.
- En demo med grensen på 20 kall koster under USD 0,01.

Prisene endres (DeepSeeks eget endepunkt endrer pris etter tid på døgnet), så overslaget sjekkes på nytt før levering.

- **Forstyrrelsesbriefen (E3-S05):** ett kall per («nå», prediktor), bare når vinduet har varsler. Faktaene for høyst 3 anløp gir omtrent 1 500–2 500 input-tokens og høyst 300 output-tokens (700 tegn er om lag 200–250 tokens), altså under USD 0,0003 per kall med prisgulv. Briefen deler grensen `LLM_MAKS_KALL` med begrunnelsene. Uten varsler, eller på baseline, skriver appen briefen selv og gjør ingen kall. Ikke prøvd med et ekte kall ennå.

### Røykkallet 18.11.2026

Det ble gjort 3 kall, lokalt med `LLM_MODUS=ekte`, mot valideringsvinduet 15.08.2025 08:00. Det var ett kall av hver: modell med varsel, modell uten varsel og baseline. Alle gikk til Wafer (billigste endepunkt) og svarte HTTP 200.

- **Ingen tekst.** Alle tre brukte alle 300 output-tokens på resonnering (`reasoning_tokens` = 300, `finish_reason` = `length`, `content` = null). Kontrollen ga tilbakefallet (`avkortet`), som den skulle. Ingen feil tekst ble vist.
- **Årsak:** modellen har resonnering på som standard med innsats `high` (`reasoning.default_effort` i OpenRouters modelliste), og resonneringstokens teller mot `max_tokens`. Resonneringen er ikke påbudt (`mandatory` = false), og `none` er støttet.
- **Målt kostnad:** 494–690 input-tokens og 300 output-tokens. Det kostet USD 0,000161–0,000175 per kall, og alle tre til sammen USD 0,000504. Det stemmer med overslaget over.
- **Retting:** klienten sender `reasoning: {"effort": "none"}` (`LLM_RESONNERING`, standard `none`). `max_tokens` er beholdt på 300, fordi et svar på høyst 400 tegn er godt under 200 tokens. Grensen var ikke for lav for svaret. Den ble brukt opp av resonneringen. Rettingen er ikke prøvd med et ekte kall ennå.

### Røykkall 3, 18.11.2026 (`begrunnelse-v4`)

Det ble gjort 3 kall, med de samme tilfellene og `reasoning.effort = none`. Alle tre ble godtatt, med 230, 200 og 114 tegn. De brukte 674–856 input-tokens og 40–81 output-tokens, uten resonneringstokens. Til sammen kostet de USD 0,000154, altså om lag USD 0,00003–0,00007 per kall. For alle tre røykkallene er summen USD 0,000907.

### Røykkall 4, 18.11.2026 (`begrunnelse-v5`)

Det ble gjort 3 kall med de samme tilfellene. Alle tre ble godtatt, med 243, 228 og 109 tegn og høyst 3 setninger. De brukte 834–1027 input-tokens og 41–90 output-tokens, uten resonnering. Til sammen kostet de USD 0,000176. For alle fire røykkallene er summen USD 0,001083.

### Røykkall 5, 19.11.2026 (`begrunnelse-v6`)

Timer i faktaene (om skipet rekker fram, og avgang) er avrundet til hele tall, halve opp. De skrives «ca. 42 timer», «ca. 1 time» og «under 1 time» i stedet for «omtrent 42,0 timer». Prompten tillater nå «ca.» slik det står i faktaene. Kontrollen er uendret: «ca.» deler ikke setninger, og et desimaltall modellen regner ut selv, avvises av tallregelen (test `test_kontrollen_med_hele_timer_fra_faktaene`). Det ble gjort 3 kall med de samme tilfellene, lokalt med `LLM_MODUS=ekte` bare for kjøringen. Alle gikk til Particle AI og stoppet av seg selv, uten resonnering. Alle tre ble godtatt, med 243, 228 og 109 tegn, og tekstene var de samme som i røykkall 4. De brukte 838–1028 input-tokens og 41–90 output-tokens. Til sammen kostet de USD 0,000139, altså USD 0,000035–0,000053 per kall. For alle fem røykkallene er summen USD 0,001222. Faktaene for de to modellradene hadde «ca. 6 timer» og «ca. 16 timer», men ingen av svarene brukte timetallet, så «ca.» i et svar er bare dekket av testen.

**Risiko som er igjen:** kontrollen avviser nå tall skrevet med ord og retningsord som ikke stemmer med fortegnet på avviket. Den fanger likevel ikke «en» og «ett» som tall, eller en feil påstand skrevet med ord og tall som finnes i inputen.

## Begrunnelse

Nøkkelen med hard bruksgrense er det eneste som faktisk setter et tak på forbruket når appen kjører på flere instanser. Adapteren gjør leverandøren byttbar (A8), så valget koster lite å endre: modellen og routingen er miljøvariabler, og klienten er én fil.
