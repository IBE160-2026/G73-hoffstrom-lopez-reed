# E2-S09: Panel modell mot baseline

## 2026-11-11 kl. 23:26 — Felipe Knudstad-Lopez

### Oppgave
Felipe ba om å bytte «ankomstsonen» med «havneområdet» i README og lukke punktet, og så E2-S09 med full BMAD-flyt, med stopp ved godkjenning av specen og før commit. Før commit ba han om «systemet» på raden for all Øvrige-trafikk, og om skjermbilder ved 1280, 1024 og 360 px.

### Plan
- README-rettelsen ble committet og pushet først.
- bmad-build fra [specen](../../_bmad-output/implementation-artifacts/spec-e2-s09-panel-modell-mot-baseline.md). Felipe svarte 1A (validering nå, test etter E2-S10) og 2A (høyre kolonne), og godkjente valgene som var tatt.
- Implementering i en subagent, review med tre lag, rettelser, hele suiten og mutasjonssjekk.
- Endringen til «systemet», og skjermbilder med funksjonene i `scripts/ta_skjermbilder.py`. Bildene ble skrevet til scratchpad, så de committede bildene ble ikke overskrevet.

### Resultat
- **`35d81b3`:** README sier «inne i havneområdet». Punktet i `issues.md` er lukket.
- **`8ab7de1`:** `app/panel.py` og panelet på hovedskjermen.
  - Før testkjøringen viser panelet valideringstallene, uten dom. Etter testkjøringen viser det `test`-blokken med bestått/ikke bestått per horisont.
  - Raden for all Øvrige-trafikk sier «Systemet», med forklaringen om turene inne i havneområdet.
  - `test_bare_baseline` og ablasjonen vises aldri.
- **Verifisering:** 411 tester er grønne, og `data/` og låsen er uendret.
  - Review: 22 funn. 15 er rettet og 7 avvist.
  - Mutasjonssjekk: 27 av 28 fanget, og den siste er ekvivalent. Mutasjonssjekken fant tre hull etter reviewen, og ett «fanget»-resultat i første kjøring kunne ikke gjenskapes. Begge deler står i `docs/refleksjon/notater.md`.
- **Skjermbilder:** `scrollWidth` er lik vindusbredden ved 360, 640, 1024, 1280 og 1920 px, så det er ingen sidelengs rulling, og ingenting blir skjøvet ut av bildet.
  - Ved 1024 px blir lista smalere, og hjelpeteksten «predikert før valgt tidspunkt» brytes over tre linjer.
  - Panelet er mye høyere enn lista: siden er 2 802 px høy ved 1280 px, og under lista står det tomt.

### Åpne punkter
- Ved 1024 px presser panelet anløpslista, så hjelpeteksten i Predikert brytes over tre linjer. Vurder om panelet skal stå under lista opp til 1280 px.
- Panelet er omtrent tre ganger så høyt som lista ved desktop. Vurder å slå sammen horisontene eller legge dem i faner eller detaljer.
- Ingen manuell UU-sjekk (200 % zoom, skjermleser) av panelet ennå. UX §6 har ingen rader for panelet.
