# Kursmateriale fjernes fra arbeidstreet, men blir liggende i git-historikken

## Kontekst

`docs/kilder/` inneholdt kopier av kursmateriale: BMAD-malen for product brief, et eksempel på en brief og prosjektforslaget for emnet. Faglærer spurte i tilbakemeldingen på product brief om slike kopier hører hjemme i et offentlig repo (`docs/tilbakemelding-product-brief.md`, kriterium 7). Repoet er offentlig. Filene kom inn i commit `0615845` («Legg til BMAD og kursmateriale»).

## Alternativer vurdert

- **La filene ligge.** Forkastet. Faglærer pekte på dem, og vi bruker dem ikke lenger.
- **Fjerne dem fra arbeidstreet og gitignorere mappen.** Valgt. Filene forsvinner fra `main` og kan ikke committes på nytt ved et uhell. Lokale kopier beholdes.
- **Skrive om historikken** (`git filter-repo` eller tilsvarende) og force-pushe. Forkastet, se under.

## Valg

Filene er fjernet fra git og lagt i `.gitignore` (E0-S09, 22.10.2026). **De finnes fortsatt i historikken fra `0615845`, og vi lar dem bevisst ligge der.**

## Begrunnelse

Dette er en avveining mellom opprydding og sporbarhet, og vi velger sporbarhet:

- **Commit-hashene er sporbarhetskjeden.** Promptloggene (`docs/prompts/`), beslutningene og epics-tabellen viser til konkrete commits. En omskriving endrer hashen på hver commit etter `0615845`, altså nesten hele prosjektet. Dermed blir alle disse referansene ugyldige. Sporbarhet er det tyngst vektede vurderingskriteriet (kriterium 1, `docs/vurderingskriterier.md`).
- **Repoet er et GitHub Classroom-repo.** Force-push kan forstyrre kursets oppsett og alle gruppemedlemmenes lokale kloner.
- **Gevinsten er liten.** Filene er kursmateriale som allerede er delt med alle studentene, ikke hemmeligheter eller personopplysninger. Faglærers poeng var at de ikke hører hjemme i repoet. Det er oppfylt når de ikke ligger i arbeidstreet.

## Konsekvens

Den som blar i historikken, finner filene i alle commits fra `0615845` og fram til E0-S09 (`git log --oneline --grep E0-S09`). Var det en hemmelighet, ville vi ha valgt motsatt: rotert nøkkelen og skrevet om historikken. Den grensen er bevisst. Kursmateriale veier ikke opp for en brutt sporbarhetskjede, mens en lekket nøkkel ville gjort det.
