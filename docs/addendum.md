# Addendum: AIS-basert ankomstprediksjon

Supporting depth captured during the product-brief conversation that belongs in a downstream document (PRD / architecture / solution design), not in the 1-2 page executive brief. Nothing here is audit/override information — see `.memlog.md` for that.

## AIS data-quality contingency plan (5 levels)

Contributed by the group 2026-09-17, in response to the coaching question about a fallback if Kystdatahuset's live/archive data turns out too gappy for the ambitious end-to-end pipeline.

| Nivå | Situasjon | Tiltak |
|---|---|---|
| 0 | Forventet | Velg pilotperiode i verifisert vindu. Okt 2025 – mars 2026 svarer; april 2026 og framover er tomt. |
| 1 | Enkelte dager mangler | Dropp de seilasene, ikke havnen. Logg dekningsgrad per dag som datakvalitetsmetrikk. |
| 2 | AIS finnes, men fasit kan ikke utledes | Bruk `time-in-port`-intervallet som svakere fasit. Flagg raden som lavere kvalitet. |
| 3 | Arkivet utilgjengelig | BarentsWatch Live AIS, 14 dagers rullende vindu, egen logging via cron. |
| 4 | Siste utvei | Syntetisk datasett fra fordelinger observert i den delen av arkivet som virker. Kun for å vise at modell og grensesnitt fungerer, tydelig merket. |

**Anbefaling:** sett opp nivå 3 (BarentsWatch Live AIS + cron-logging) i uke 1 uansett — lav kostnad (en ettermiddag), kjører selvstendig, gir 8 ukers egne data som backup hvis arkivet svikter.

**Beslutningspunkt uke 2:** hvis fasit (faktisk ankomst) kan utledes for under 70% av seilasene i pilotmåneden, gå til nivå 3 som primærkilde fremfor Kystdatahuset-arkivet.

**Rapporteringsverdi:** nivå-1-håndtering (droppe enkeltseilaser, logge dekningsgrad) gir naturlig stoff til et datakvalitetskapittel i sluttrapporten — leses som grundighet, ikke svakhet.

Note (not yet independently verified by research — this is the group's own finding from testing the API/archive directly): the claim that Kystdatahuset's archive responds for Oct 2025–Mar 2026 but is empty from Apr 2026 onward should be re-checked close to project start, since it may reflect a temporary indexing lag rather than a permanent gap.

## Security / access design

- v1: no user accounts, no login. Rationale for the brief: source data is open (NLOD), no personal data is processed, and v1 has exactly one user role — authentication would not test any product hypothesis, it would spend time that should go to the model.
- If the demo instance needs to be reachable outside a local run: one shared HTTP Basic Auth in front, not user accounts.
- If the BarentsWatch Live AIS fallback (contingency level 3) is activated: its client id/secret must live in environment variables and GitHub Secrets, never committed to the repo.
- v2 (explicitly out of scope for this brief): role-based access — havnevakt (operational, write/act), havnekaptein (tactical, read + planning tools), read-only viewer — because berth allocation is operationally sensitive once this moves beyond a single-port pilot.

## Roadmap detail behind the Vision section

- **v1 (this semester):** one port (Bergen Havn), historical data, prediction benchmarked against the vessel's own reported ETA.
- **Year 1:** real-time, 3-5 ports, prediction exposed as an API.
- **Years 2-3:** extend from arrival prediction to time-in-port and departure; connect to berth capacity so the system *suggests* reallocation rather than only flagging deviation; the same estimate shared with terminal and transporter so the whole chain plans against one number.

## Sources supplied by the group

- Bergen Havn contact / Maritime Operations Center: https://www.bergenhavn.no/en/contact (independently verified 2026-09-17 via WebFetch: confirms "Maritime Operations center", email havnevakt@bergenhavn.no, phone +47 55 56 89 50, VHF channel 12)
- Kystdatahuset Open API: https://kystdatahuset.no/ws/swagger/index.html
- BarentsWatch Live AIS API: https://developer.barentswatch.no/docs/AIS/live-ais-api/
