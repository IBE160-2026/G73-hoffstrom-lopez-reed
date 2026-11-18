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

Prisene endres (DeepSeeks eget endepunkt endrer pris etter tid på døgnet), så overslaget sjekkes på nytt før levering. **Risiko:** bruker modellen output-tokens på resonnering, kan svaret bli tomt eller kuttet ved `max_tokens`. Kontrollen gir da tilbakefallet (`kontroll_tom` eller `avkortet`), og røykkallet viser om det skjer.

## Begrunnelse

Nøkkelen med hard bruksgrense er det eneste som faktisk setter et tak på forbruket når appen kjører på flere instanser. Adapteren gjør leverandøren byttbar (A8), så valget koster lite å endre: modellen og routingen er miljøvariabler, og klienten er én fil.
