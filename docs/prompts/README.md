# Prompt- og KI-øktlogg

Sensorveiledningen for del 1 krever lagrede prompts og KI-økter koblet til konkrete endringer. Dette er stedet.

## Hva vi fant ut

Claude Code lagrer full, tidsstemplet lokal økthistorikk per prosjekt (`~/.claude/projects/<prosjekt>/<session-id>.jsonl`). For dette repoet går den tilbake til 17. september — hele arbeidet med product brief og datapipeline er altså allerede lagret lokalt, inkludert hver faktiske prompt vi skrev (skilt fra systemtekst, verktøyresultater og bakgrunnsvarsler via feltet `promptSource: "typed"` i loggen). Filene for september (`2026-09-17.md` til `2026-09-28.md`) er rekonstruert direkte derfra — ikke fra hukommelse.

Denne JSONL-fila ligger kun lokalt (ikke i git) og er maskinens egen Claude Code-historikk, ikke noe prosjektet eier eller kan dele direkte. Format-filene her er destillatet som faktisk hører hjemme i repoet.

## Format

Én fil per arbeidsøkt, navngitt `YYYY-MM-DD.md` (flere økter samme dag: `YYYY-MM-DD-2.md` osv.). Hver fil har fire deler:

```markdown
# Arbeidsøkt: YYYY-MM-DD

## Hva vi ba om
[Prompter i kronologisk rekkefølge, med tidsstempel og mest mulig ordrett —
dette ER det sensorveiledningen ber om, ikke et sammendrag av det.]

## Hva ble endret
[Kort, faktisk oppsummering: hvilke filer, hvilke beslutninger, hvilke
funn. Noen setninger, ikke en gjenfortelling av hele samtalen.]

## Commits
[hash — commit-melding, med tidspunkt]
```

## Fra nå av

Logg økten når den er ferdig (eller ved et naturlig pausepunkt), ikke i etterkant av flere dagers arbeid — det er nettopp det som gikk tapt for deler av september og måtte rekonstrueres. Alle tre bør logge sine egne økter, ikke bare den som skriver i dette repoet til vanlig.
