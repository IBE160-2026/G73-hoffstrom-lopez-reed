# E1-S18 og E1-S19: hopp-lenke og «Spesialfartøy»

## 2026-11-05 kl. 15:00 — Felipe Knudstad-Lopez

### Oppgave
Mens E2-hentingen kjører, skulle KAN-storyene E1-S18 (hopp-lenken dekker overskriften ved fokus) og E1-S19 (norsk visningsnavn for «Auxiliary») tas på en egen branch, `fix/e1-s18-s19`, fra `main`. `pipeline/`, `data/` og alt som har med E2 å gjøre, skulle ikke røres. Kortversjonen av BMAD-flyten skulle brukes, og det skulle åpnes en PR inn til `main`.

### Plan
- Bestillingen hadde bare plassholderen «[navn dere velger]». Felipe valgte «Spesialfartøy».
- Arbeidet ble gjort i en egen git-worktree (`../G73-fix-e1-s18-s19`), så filene i hovedmappa, der hentingen kjører, ikke ble byttet.
- BMAD-build gikk oneshot-ruta, med én spec per story og én reviewer (Blind Hunter).

### Resultat
- **E1-S18:** `.hopp:focus` er `position: static`, så lenka skyver overskriften ned ved fokus i stedet for å dekke den. Det finnes en vakttest i `test_uu_struktur.py`, og den er mutasjonssjekket. Storyen står som ◐ i epics til UU2 er sjekket manuelt. Jeg har ikke sett fokustilstanden selv.
- **E1-S19:** `gruppe_visning()` i `app/visning.py` er tatt i bruk i `_rader`. Testene `test_gruppe_visning` og `test_ingen_rad_viser_auxiliary` er mutasjonssjekket. PRD-ordlista og A2-skissen er oppdatert, og storyen er ✅. Dataregresjonen, `data/` og `pipeline/` er uendret.
- **Review:** 9 funn, og 6 av dem er rettet:
  - skjermbildene er tatt på nytt, og UU6-målingen gir ingen rulling på 360, 640, 1280 eller 1920 px
  - endringslogg i PRD og UX
  - merknad i UU2-raden
  - specene er avsluttet
  - opprydding i testene
  Funnene om `:focus-visible` og den ujevne skissekanten er forkastet.
- **Tester og PR:** alle 182 tester er grønne på branchen. Commiten er `58bae80` med Felipe som forfatter og er pushet. PR: https://github.com/IBE160-2026/G73-hoffstrom-lopez-reed/pull/6

### Åpne punkter
- E1-S18: UU2 i UX §6 må sjekkes manuelt (Tab på forsiden: hopp-lenken skal synes uten å dekke overskriften). Fyll ut raden, og sett E1-S18 til ✅.
- PR #6 må gjennomgås og merges inn i `main`.
- Worktreen `../G73-fix-e1-s18-s19` kan fjernes med `git worktree remove` når PR-en er merget.
