# E1-S05 metrikker og dataregresjon

## 2026-10-27 kl. 17:01 — Theodor Gimming

### Oppgave
Implementere E1-S05 med to krav fra gruppa:
- Baselinen er den første prediktoren som implementerer S04-kontrakten, og den skal bestå lekkasjetestene uten unntak.
- En regresjonstest skal låse 46,6 % (Øvrige) og 79,6 % (Passasjer) innenfor ±30 min, så en test feiler hvis datalaget eller kontrakten flytter tallene.

### Plan
- Full `bmad-build`-flyt. Specen er [`spec-e1-s05-metrikker-og-dataregresjon.md`](../../_bmad-output/implementation-artifacts/spec-e1-s05-metrikker-og-dataregresjon.md), og epic-konteksten ble laget på nytt først fordi den var utdatert etter S04.
- Før specen ble skrevet, ble tallene reprodusert gjennom kontrakten på det ekte utdraget. Det avdekket at pipelinen hadde rundet avviket. Gruppa valgte alternativ 1: lås 12,8 % og rett dokumentene.
- Etter godkjenning: implementasjon i en subagent, tre reviewere og triage, rettelser og egen mutasjonssjekk med kontrollkjøring. Deretter commit og push.

### Resultat
- **`app/metrikker.py`:** `andel_innenfor()` regner ±30 min inklusivt, på uavrundede tider og bare for anløp med status `ok`. `dekning()` teller anløp per status. Manglende eller doble prediksjoner gir `ValueError`. En AST-sjekk med hviteliste hindrer modulen i å lage egne prediksjoner.
- **`app/prediksjon/naiv.py`:** `NaivPrediktor` er en referanseprediktor i `PREDIKTORER`, og den kan ikke velges med `velg_prediktor`. En ny prediktormodul som ikke er registrert, får kontrakttesten til å feile.
- **`tests/test_dataregresjon.py`** låser eksakte antall ved H = 6 og 24:
  - baseline: 464/996 (46,6 %) og 343/431 (79,6 %)
  - naiv: 127/996 (12,8 %) og 32/431 (7,4 %)
  - dekning: 1 427 av 1 566 anløp har fasit (126 empty, 8 not_detected, 5 avkortet)
- **12,9 → 12,8 %:** rettet i brief, brief.no, PRD, addendum (der ALL også gikk fra 11,2 til 11,1 %), UX, arkitektur og epics. Beslutning 04 har fått en merknad, og `pipeline/derive_arrivals.py` en kommentar. Oppførselen er ikke endret.
- **Review:** ti rettelser. De viktigste var at manglende eller doble prediksjoner ble telt feil, og at en uregistrert prediktor slapp unna kontrakttesten.
- **Mutasjonssjekk:** ni mutanter, alle fanget etter rettelsene. Mutanten der fasit avgjøres av ankomsttid i stedet for status, overlevde første runde. Det var samme hull som i S03.
- **Tester:** 120 grønne.
- **Refleksjonsnotater:** pipeline-avrundingen og testhullet fra S03 som kom igjen.
- **Commit:** `9c7132e`, pushet til origin. Epic-konteksten er laget på nytt, så det punktet er lukket i `issues.md`.

### Åpne punkter
- README nevner bare 46,6 %. 79,6 %, 12,8 % og 7,4 % legges inn i «Kom i gang» i E1-S16.
