---
title: "Product Brief: AIS-basert ankomstprediksjon (working title)"
status: draft
created: 2026-09-17
updated: 2026-09-28
---

# Product Brief: AIS-basert ankomstprediksjon (working title)

## Executive Summary

For the havnevakt in Bergen Havn's Maritime Operations Center, we are building a decision-support tool that predicts when a ship will actually arrive — not just what it reported — so quay allocation can be planned against a number worth trusting instead of a self-reported ETA. Today, the havnevakt assigns quay space continuously based on vessel-reported ETAs, with no reliable way to know in advance which reports to trust and which will be hours off. The gap matters now because the underlying problem already has institutional attention in Norway: Bergen Havn was a named participant in Kystverket's Oslo Havn-led "Digital tvilling i havn" initiative (NOK 10.5M, ~20 Norwegian ports, concluded November 2024), whose goal was streamlining vessel arrivals and reducing port waiting time. That project built digital-twin and mapping infrastructure, not an operational ETA-prediction tool, and the problem it aimed at hasn't been picked up again since it concluded — this project builds the prediction layer nobody has since provided, using the same open AIS data Kystverket already publishes through Kystdatahuset.

## The Problem

Bergen Havn runs berth allocation through the havnevakt (duty officer) in its Maritime Operations Center — a shift-staffed role that continuously assigns quay space based on vessels' self-reported ETAs. The job, in one concrete scenario: a ship reports ETA 08:00; the next vessel is due at the same quay at 14:00; does the first ship actually arrive at 08:00, or 11:30 — and does anything need reassigning right now?

Reported ETAs are known industry-wide to diverge from actual arrival, because they don't reflect berth, pilot, or tug readiness — IMO's Just-In-Time Arrival Guide names this exact mechanism: a vessel can be perfectly "on time" by its own report and still cause avoidable waiting or a scramble to reassign a quay. No public documentation confirms this specific pain at Bergen Havn — that stays a reasoned inference from the general industry pattern, not a claimed fact. The port did commit real money to the adjacent problem in the past ("Digital tvilling i havn," concluded Nov 2024, see Executive Summary) — evidence the institution has treated today's ETA information as insufficient to plan against before, not evidence of an active initiative today.

**Precision on scale:** Bergen Havn is frequently described as Norway's largest cargo port and largest cruise port by tonnage — but the bulk of that cargo tonnage moves over privately operated terminals, not the public quays the havnevakt actually disposes of. The pain this brief describes applies to the public-quay traffic under the havnevakt's own authority, which is a real but narrower slice of the port's total tonnage figures. This distinction matters for scoping the pilot and should not be blurred by citing the port's overall size as if it were all addressable.

## The Solution

A decision-support tool that predicts when a ship will actually arrive at Bergen Havn — 6 and 24 hours ahead — built on open AIS and voyage data from Kystverket's Kystdatahuset. Because the raw data only carries each vessel's self-reported ETA, the pipeline first derives actual arrival events from AIS tracks (a standard technique: a port-area polygon combined with a stopped-speed threshold) to build a labeled dataset of the deviation between reported and real arrival. A model trained on that dataset produces the 6h/24h predictions, benchmarked against the vessel's own reported ETA — the reference every prediction has to beat. A generative AI layer turns each day's predictions into a short daily brief for the havnevakt: a map plus a stated reason for each expected deviation, so the operator sees not just a number but why it is likely wrong.

v1 ships as a web dashboard, open without login (see Scope). The group's stated ambition is a live pipeline against fresh Kystdatahuset data, with a tested contingency plan if live data proves too gappy within the course timeline (full plan in the addendum).

## What Makes This Different

No AIS-ETA vendor found in the market — Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic — publishes an audited, reproducible accuracy benchmark; their claims are marketing copy, not documented methodology. That is itself a legitimate differentiator: this project measures itself, in public, against the one honest baseline available — the vessel's own reported ETA. Kystdatahuset is a data source, not a prediction product, so no existing tool sits on top of exactly this data today.

The closest Nordic academic precedent, an NTNU thesis on AIS-based turnaround-time prediction at Mongstad ([ntnuopen.ntnu.no/handle/11250/2780189](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2780189)), reached a cautionary conclusion ("a convoluted task with many hidden variables") — an honest reference point, not a bar this project claims to clear easily. A closer methodological precedent exists outside Norway: a Hong Kong study combining AIS trajectories with port-call data via XGBoost ([ScienceDirect, S1474034625009036](https://www.sciencedirect.com/science/article/pii/S1474034625009036)) cut ETA error by 52.98% against the vessel's own reported ETA, using a near-identical approach at a different port — real evidence the method works, not a promise this group will match that number.

Honestly: there is no technical moat here. The advantage is being first to point this exact method at Bergen Havn's exact ETA-accuracy problem, and being transparent about the resulting number instead of asserting one.

## Who This Serves

**Primary: the havnevakt in Bergen Havn's Maritime Operations Center** (public 24/7 contact: havnevakt@bergenhavn.no) — a shift-based role that continuously assigns quay space. Success for them: fewer last-minute quay reassignments, and a trustworthy answer to "will this ship actually be here when it says it will."

**Secondary: havnekaptein / driftsleder** — tactical planning over weeks rather than single port calls, using the same predictions rolled up into patterns and capacity views.

**Explicitly not a v1 user:** shipping companies, ship agents, cargo owners. Widening the audience to them is a deliberate later-stage decision (see Vision), not an oversight.

## Success Criteria

**Functional — metric structure.** Real pipeline work building the ground-truth dataset (deriving actual arrival from AIS tracks, see addendum) showed the deviation distribution is tail-heavy: most calls land close to their reported ETA, a minority miss by hours, and a single error metric that averages across both groups misleads. Mean absolute error is unstable on this shape — it can look dramatically worse than the typical case actually is, because a handful of extreme voyages dominate the mean. The metric structure is therefore:
- **Primary: share of predictions within ±30 minutes of actual arrival.** The number a havnevakt would actually trust or not.
- **Secondary: precision and recall on flagging arrivals that deviate more than 2 hours** ("er_forsinket") — a disruption-detection framing, evaluated once a trained model exists (the reported ETA alone predicts zero deviation by definition, so it cannot meaningfully be scored against this flag).
- **Support stats only, never the headline:** MAE and median absolute error, reported for transparency but not used as the pass/fail criterion.

The reported-ETA baseline itself is scored the same way, calibrated per vessel-traffic type (scheduled/liner vs. other) rather than compared naively — see the addendum's method notes on why zone-entry-based ground truth needs this calibration to be comparable to ETA at all. The Hong Kong precedent (52.98% MAE reduction vs. self-reported ETA) remains a useful aspirational reference for what "good" looks like with this method, not a number to adopt directly.

**Data quality.** AIS coverage is logged as an explicit metric; voyages where actual arrival cannot be derived are dropped and counted, not silently interpolated (full contingency plan and coverage numbers in the addendum).

**Product.** The havnevakt can read a daily brief and understand, without asking anyone, which of tomorrow's expected arrivals to distrust and why.

## Data In / Data Ut

**Data inn:**
- Seilasdata fra Kystdatahusets åpne API (rapportert ETA/ETD, skipsnavn, MMSI, skipstype/-gruppe, lengde, avgangs-/ankomststed) for anløp til Bergen Havn (NOBGO).
- AIS-posisjonsdata (breddegrad, lengdegrad, fart, kurs, tidsstempel) per fartøy fra samme kilde, hentet per MMSI for et tidsvindu rundt hvert anløp.
- BarentsWatch Live AIS som dokumentert reserveløsning dersom Kystdatahuset-arkivet viser seg utilstrekkelig (se addendum).

**Data ut:**
- Predikert ankomsttid (6t og 24t horisont, når modellen er trent) per fartøy, målt mot skipets egen rapporterte ETA.
- Et signert forsinkelsesflagg (er_forsinket) for anløp som avviker vesentlig fra kalibrert forventet ankomst.
- En daglig AI-generert forstyrrelsesbrief til havnevakten: kart og begrunnelse per forventet avvik.
- Dekningsgrad- og datakvalitetsmetrikker som følger med hver kjøring, ikke skjules.

## Risks

- **AIS-dekning under fortøyning.** Rå AIS-data viste seg å ha reelle rapporteringshull nettopp når skip ligger stille ved kai — et sentralt funn i utviklingen av selve datagrunnlaget, ikke en teoretisk bekymring. Håndtert med en egen kontinuitetsplan (addendum), men gjenstår som en systematisk begrensning i datagrunnlaget.
- **Ukjent dekning for utenlandskflaggede skip.** En vesentlig andel anløp fra utenlandskflaggede fartøy mangler AIS-posisjonsdata i den åpne API-tilgangen. Årsaken er uavklart (tilgangsbegrensning vs. utdatert MMSI-registrering) — se addendum. Utgjør en skjevhet i datagrunnlaget mot norskflagget trafikk inntil avklart.
- **Halefordelt avvik gjør enkle mål misvisende.** Se Success Criteria — MAE og gjennomsnitt kan gi et misvisende bilde av modellens faktiske nytteverdi for havnevakten.
- **Kalibreringsskjevhet.** Baseline-kalibreringen (offset mellom sonepassering og faktisk kaitid) er estimert på et utvalg som systematisk overrepresenterer større, mer rutepregede fartøy, fordi det er de skipstypene der begge etikettene lettest lar seg utlede. Dokumentert, ikke korrigert.
- **Stram tidsramme.** 10 uker til et fungerende produkt er en bevisst ambisiøs ramme for en tre-personers gruppe, gitt at prosjektet har tre tunge delkomponenter (datapipeline, prediksjonsmodell, generativt rapporteringslag). Se Scope for hva som er bevisst utsatt.
- **Ingen teknisk moat.** Se What Makes This Different — fortrinnet er utførelse og transparens, ikke en forsvarbar teknisk barriere.

## Scope

**IN — v1 (this course, ~10 weeks):**
1. Historical AIS/voyage ingestion from Kystdatahuset for a verified data window at Bergen Havn.
2. Derivation of actual-arrival events from AIS tracks, with a logged per-day coverage metric.
3. A trained model predicting arrival 6h and 24h ahead, benchmarked against reported ETA.
4. A web dashboard showing the daily brief: predicted arrivals, a map, and a stated reason per expected deviation, generated by an AI summarization layer.
5. Open access, no login — source data is open (NLOD), no personal data is processed, and v1 has a single user role. If the demo must be reachable remotely, a single shared HTTP Basic Auth stands in front of it (not user accounts). Full rationale in the addendum.

**OUT — deliberately deferred, not rejected:**
1. Real-time/live data as the primary source — the group is committed to attempting it, with a tested fallback to BarentsWatch Live AIS if the Kystdatahuset archive proves too gappy (addendum: contingency plan).
2. Additional ports beyond Bergen Havn.
3. Prediction exposed as an API for other consumers.
4. Time-in-port and departure prediction, and berth-capacity-linked reallocation suggestions.
5. Role-based access control (havnevakt vs. havnekaptein vs. read-only) — deferred because it only matters once this extends past a single pilot.
6. Any external-facing consumer (shipping companies, agents, cargo owners).

## Vision

In three years, Norwegian ports plan quay use against a shared, data-driven arrival estimate — not against a number the ship self-reported a day in advance. The path there: this semester, one port and historical data prove the method against the vessel's own reported ETA. Within a year, the same pipeline runs in real time across 3-5 ports and the prediction is exposed as an API. Within two to three years, it extends from arrival to time-in-port and departure, connects to berth capacity so the system suggests reallocation instead of only flagging a deviation, and the same estimate is shared with terminal and transporter so the whole chain plans against one number instead of each link guessing separately.

---

## Known constraints (not part of the brief itself, kept here for continuity)

- Course: IBE160 Programmering med KI, Høgskolen i Molde, group G73 (Theodor Gimming Hoffstrøm, Felipe Knudstad-Lopez, Thomas Kvile-Reed).
- Self-defined project — not one of the 8 course-suggested proposals.
- Technical/implementation depth (AIS data-quality contingency plan, security design detail, roadmap detail) lives in `addendum.md`.
