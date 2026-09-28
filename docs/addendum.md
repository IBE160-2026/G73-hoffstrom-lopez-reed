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

## Dataset Summary — full batch, locked 2026-09-28

Pipeline work is stopped here per the group's decision (2026-09-27: "vi starter modellen 6. oktober uansett dekningstall"). These are the real, final numbers from the complete fetch — not pilot estimates. Full method detail (arrival-rule evolution, calibration, metric structure) is in `docs/beslutninger/`.

- **Period:** 2024-01-01 to 2026-03-15 (27 months), voyages arriving at Bergen (NOBGO) only.
- **Voyages:** 8,094 total. AIS fetch attempted for all; **7,826 successfully cached**. The remaining 268 are permanent gaps confirmed by retry — specific date partitions missing from Kystdatahuset's own database (`relation ... does not exist`), not a transient or our-side issue. Note: the week-1 assumption that the archive only responds for Oct 2025–Mar 2026 (contingency plan, level 0 above) turned out to be overly pessimistic — data was retrievable across the full 27-month range, with these specific date exceptions.
- **Coverage, arrival_in_area (PRIMARY label):** **87.1%** overall (n=7,826) — comfortably above the group's 70% threshold from the contingency plan; the BarentsWatch fallback was not needed.
  - Scheduled/liner (Passasjer proxy): 94.3%
  - Non-scheduled: 84.0%
- **Coverage, arrival_at_quay (secondary label):** 64.0% overall (89.9% Passasjer / 52.9% Non-Passasjer) — lower as expected, since it needs a gap/stability pattern the AIS data doesn't always contain.
- **Area-to-quay dwell time:** median 56.7min (Q1 42.9, Q3 69.7). One extreme outlier at 5,911min (~4.1 days) — not yet investigated; could be a genuine long anchoring wait or a data artifact. Flagged for the modeling phase, not resolved here.
- **Calibrated baseline offset** (median TRAIN dwell per ship_group): Passasjer 44.8min, Non-Passasjer 64.2min (train n=1,700 / 2,228).
- **Train/test split:** 6,260 / 1,566, chronological. Test period: 2025-09-14 to 2026-03-15 — a fall/winter window; generalization claims beyond that season aren't supported by this split alone.
- **Calibrated baseline performance** (TEST split, n=1,427 evaluable):

  | Group | n | naive ±30min | calibrated ±30min | calibrated off>2h |
  |---|---|---|---|---|
  | ALL | 1,427 | 11.2% | **56.6%** | 17.5% |
  | Passasjer | 431 | 7.4% | **79.6%** | 1.9% |
  | Non-Passasjer | 996 | 12.9% | **46.6%** | 24.3% |

  Calibration fixes the systematic bias (median goes from roughly -50min to near zero) but barely moves MAE for Non-Passasjer (126→102 min overall, still driven by the tail) — a constant offset corrects the typical case, not the extreme one. The off>2h rate is nearly unchanged by calibration (as it should be: shifting everything by a constant doesn't change how many cross a fixed threshold by much) — **this ~17-24% disruption rate is the real target the model needs to move**, not the ±30min headline alone.
- **Label agreement** (arrival_in_area calibrated vs. arrival_at_quay raw, on the >2h flag): 97.0% (n=5,010) — the two independently-derived labels agree on which voyages are genuine disruptions almost all the time, on the subset where both exist.
- **Selection-bias check, confirmed at full scale:** vessels where both labels were derivable are substantially larger (median 119.9m vs. 74.6m) and skew toward Passenger/Ro-Ro, Passenger/Cruise, and Ro-Ro Cargo; vessels without a derivable at_quay skew toward General Cargo, Bunkering/LNG Tankers, and offshore-supply types. The calibration offset is therefore likely biased toward larger, more schedule-pattern vessels — a real limitation of the offset, not fixed here (see `docs/beslutninger/04-kalibrert-baseline.md`).
- **Window-truncation fix in effect:** 1,492 of 7,826 voyages (19.1%) had their AIS search window capped by the next voyage for the same MMSI (the frequent-caller/ferry correction) — confirms this was a real, non-trivial problem at full scale, not a pilot-only artifact.

**What this leaves for the model (starting 6. oktober):** the calibrated baseline already places over half of all arrivals within 30 minutes, and about 80% for scheduled traffic. The model's job is concentrated on the harder ~15-20% — non-scheduled traffic in particular, where MAE barely improves under calibration alone — and specifically on getting the >2h disruption flag right, since that's the case the baseline structurally cannot help with (a constant offset cannot predict which specific voyages will be extreme outliers).

## Sources supplied by the group

- Bergen Havn contact / Maritime Operations Center: https://www.bergenhavn.no/en/contact (independently verified 2026-09-17 via WebFetch: confirms "Maritime Operations center", email havnevakt@bergenhavn.no, phone +47 55 56 89 50, VHF channel 12)
- Kystdatahuset Open API: https://kystdatahuset.no/ws/swagger/index.html
- BarentsWatch Live AIS API: https://developer.barentswatch.no/docs/AIS/live-ais-api/
