---
title: "Product Brief: AIS-basert ankomstprediksjon (working title)"
status: draft
created: 2026-09-17
updated: 2026-10-16
---

# Product Brief: AIS-basert ankomstprediksjon (working title)

## Executive Summary

For the havnevakt in Bergen Havn's Maritime Operations Center, we are building a decision-support tool that predicts when a ship will actually arrive — not just what it reported — so quay allocation can be planned against a number worth trusting instead of a self-reported ETA. Today, the havnevakt assigns quay space continuously based on vessel-reported ETAs, with no reliable way to know in advance which reports to trust and which will be hours off. The gap matters now because the underlying problem already has institutional attention in Norway: Bergen Havn was a named participant in Kystverket's Oslo Havn-led "Digital tvilling i havn" initiative (NOK 10.5M, ~20 Norwegian ports, concluded November 2024), whose goal was streamlining vessel arrivals and reducing port waiting time. That project built digital-twin and mapping infrastructure, not an operational ETA-prediction tool, and the problem it aimed at hasn't been picked up again since it concluded — this project builds the prediction layer nobody has since provided, using the same open AIS data Kystverket already publishes through Kystdatahuset.

## The Problem

Bergen Havn runs berth allocation through the havnevakt (duty officer) in its Maritime Operations Center — a shift-staffed role that continuously assigns quay space based on vessels' self-reported ETAs. The job, in one concrete scenario: a ship reports ETA 08:00; the next vessel is due at the same quay at 14:00; does the first ship actually arrive at 08:00, or 11:30 — and does anything need reassigning right now?

Reported ETAs are known industry-wide to diverge from actual arrival, because they don't reflect berth, pilot, or tug readiness — IMO's Just-In-Time Arrival Guide names this exact mechanism: a vessel can be perfectly "on time" by its own report and still cause avoidable waiting or a scramble to reassign a quay. No public documentation confirms this specific pain at Bergen Havn — that stays a reasoned inference from the general industry pattern, not a claimed fact. The port did commit real money to the adjacent problem in the past ("Digital tvilling i havn," concluded Nov 2024, see Executive Summary) — evidence the institution has treated today's ETA information as insufficient to plan against before, not evidence of an active initiative today.

**Precision on scale:** Bergen Havn is frequently described as Norway's largest cargo port and largest cruise port by tonnage — but the bulk of that cargo tonnage moves over privately operated terminals, not the public quays the havnevakt actually disposes of. The pain this brief describes applies to the public-quay traffic under the havnevakt's own authority, which is a real but narrower slice of the port's total tonnage figures. This distinction matters for scoping the pilot and should not be blurred by citing the port's overall size as if it were all addressable.

## The Solution

A decision-support tool that predicts when a ship will actually arrive at Bergen Havn — 6 and 24 hours ahead — built on open AIS and voyage data from Kystverket's Kystdatahuset. Because the raw data only carries each vessel's self-reported ETA, the pipeline derives actual arrival events from AIS tracks (zone entry into the port area, calibrated per vessel-traffic type — see addendum) to build a labeled dataset of the deviation between reported and real arrival. A model trained on that dataset produces the 6h/24h predictions, benchmarked against the vessel's own reported ETA — the reference every prediction has to beat. A generative AI layer turns each day's predictions into a short daily brief for the havnevakt: a map plus a stated reason for each expected deviation, so the operator sees not just a number but why it is likely wrong.

v1 builds entirely on the locked historical dataset (8,094 voyages, Jan 2024–Mar 2026 — see addendum), not a live feed: the dashboard lets the havnevakt "replay" a chosen day or period from that dataset and see the model's predictions against what actually happened. Open without login (see Scope).

## What Makes This Different

No AIS-ETA vendor found in the market — Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic — publishes an audited, reproducible accuracy benchmark; their claims are marketing copy, not documented methodology. That is itself a legitimate differentiator: this project measures itself, in public, against the one honest baseline available — the vessel's own reported ETA. Kystdatahuset is a data source, not a prediction product, so no existing tool sits on top of exactly this data today.

The closest Nordic academic precedent, an NTNU thesis on AIS-based turnaround-time prediction at Mongstad ([ntnuopen.ntnu.no/handle/11250/2780189](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2780189)), reached a cautionary conclusion ("a convoluted task with many hidden variables") — an honest reference point, not a bar this project claims to clear easily. A closer methodological precedent exists outside Norway: a Hong Kong study combining AIS trajectories with port-call data via XGBoost ([ScienceDirect, S1474034625009036](https://www.sciencedirect.com/science/article/pii/S1474034625009036)) cut ETA error by 52.98% against the vessel's own reported ETA, using a near-identical approach at a different port — real evidence the method works, not a promise this group will match that number.

Honestly: there is no technical moat here. The advantage is being first to point this exact method at Bergen Havn's exact ETA-accuracy problem, and being transparent about the resulting number instead of asserting one.

## Who This Serves

**Primary: the havnevakt in Bergen Havn's Maritime Operations Center** (public 24/7 contact: havnevakt@bergenhavn.no) — a shift-based role that continuously assigns quay space. Success for them: fewer last-minute quay reassignments, and a trustworthy answer to "will this ship actually be here when it says it will."

**Secondary: havnekaptein / driftsleder** — tactical planning over weeks rather than single port calls, using the same predictions rolled up into patterns and capacity views.

**Explicitly not a v1 user:** shipping companies, ship agents, cargo owners. Widening the audience to them is a deliberate later-stage decision (see Vision), not an oversight.

## Success Criteria

**Functional — metric structure.** Real pipeline work building the ground-truth dataset (deriving actual arrival from AIS tracks on the full 8,094-voyage, 27-month dataset — see addendum) showed the deviation distribution is tail-heavy: most calls land close to their reported ETA, a minority miss by hours, and a single error metric that averages across both groups misleads. Mean absolute error is unstable on this shape — it can look dramatically worse than the typical case actually is, because a handful of extreme voyages dominate the mean. The metric structure is therefore:
- **Primary: share of predictions within ±30 minutes of actual arrival.** The number a havnevakt would actually trust or not.
- **Secondary: precision and recall on flagging arrivals that deviate more than 2 hours** ("er_forsinket") — a disruption-detection framing, evaluated once a trained model exists (the reported ETA alone predicts zero deviation by definition, so it cannot meaningfully be scored against this flag).
- **Support stats only, never the headline:** MAE and median absolute error, reported for transparency but not used as the pass/fail criterion.

**Scoped to non-scheduled traffic alone.** The headline result is reported on non-scheduled (ikke-rutegående) traffic only, with scheduled/liner traffic (Passasjer) kept as a control group, not pooled into the main number. Reason, confirmed on the full dataset: the calibrated baseline already puts scheduled traffic at 79.6% within ±30 minutes, up from a naive 7.4% — that traffic is close to solved by a constant offset alone. Training and reporting against the pooled dataset would let a model largely learn to recognize which voyages are ferries rather than learn to predict genuine arrival uncertainty, and the headline number would be inflated by the easy half of the fleet. Non-scheduled traffic is where the real problem — and the product's value — actually lives.

**The number to beat:** on non-scheduled traffic, the calibrated reported-ETA baseline reaches **46.6% within ±30 minutes** (up from a naive 12.9%), and **24.3% of arrivals still miss by more than 2 hours** even after calibration — calibration corrects the typical case, not the disruptive tail (MAE for this group barely moves, 155→136 minutes). The model's target is to beat both numbers: a higher ±30-minute share, and a materially better precision/recall on flagging that ~24% disruption tail than the baseline can offer (the baseline cannot flag anything by construction). If the model does not clear one or both bars, that is reported as a result, not omitted — an honest negative finding is more useful here than a quiet redefinition of success after the fact.

The reported-ETA baseline itself is scored the same way, calibrated per vessel-traffic type (scheduled/liner vs. other) rather than compared naively — see the addendum's method notes on why zone-entry-based ground truth needs this calibration to be comparable to ETA at all. The Hong Kong precedent (52.98% MAE reduction vs. self-reported ETA) remains a useful aspirational reference for what "good" looks like with this method, not a number to adopt directly.

**Data quality.** AIS coverage is logged as an explicit metric; voyages where actual arrival cannot be derived are dropped and counted, not silently interpolated (full contingency plan and coverage numbers in the addendum).

**Product.** The havnevakt can read a daily brief and understand, without asking anyone, which of tomorrow's expected arrivals to distrust and why.

## Data In / Data Out

**Data in:**
- Voyage data from Kystdatahuset's open API (reported ETA/ETD, ship name, MMSI, ship type/group, length, departure/arrival location) for calls at Bergen Havn (NOBGO).
- AIS position data (latitude, longitude, speed, course, timestamp) per vessel from the same source, fetched per MMSI for a time window around each call.
- BarentsWatch Live AIS as a documented contingency source if the Kystdatahuset archive proves insufficient (see addendum).

**Data out:**
- Predicted arrival time (6h and 24h horizon, once the model is trained) per vessel, measured against that vessel's own reported ETA.
- A signed delay flag (er_forsinket) for calls that deviate materially from the calibrated expected arrival.
- A daily AI-generated disruption brief for the havnevakt: map and reasoning per expected deviation.
- Coverage and data-quality metrics shipped with every run, not hidden.

## Risks

- **AIS coverage during mooring.** Raw AIS data turned out to have real reporting gaps precisely when ships lie still at berth — a central finding in building the ground-truth dataset itself, not a theoretical concern. Handled with its own contingency plan (addendum), but remains a systematic limitation in the dataset.
- **Unknown coverage for foreign-flagged vessels.** A significant share of foreign-flagged vessel calls lack AIS position data in the open API access. The cause is unresolved (access restriction vs. outdated MMSI registration) — see addendum. Constitutes a bias in the dataset against Norwegian-flagged traffic until resolved.
- **Tail-heavy deviation makes simple metrics misleading.** See Success Criteria — MAE and the mean can give a misleading picture of the model's actual usefulness to the havnevakt.
- **Calibration bias.** The baseline calibration (offset between zone entry and actual berth time) is estimated on a sample that systematically overrepresents larger, more schedule-pattern vessels, because those are the ship types where both labels are most easily derived. Documented, not corrected.
- **Tight timeline.** 11 weeks to a working product is a deliberately ambitious scope for a three-person group, given the project has three heavy sub-components (data pipeline, prediction model, generative reporting layer). See Scope for what is deliberately deferred.
- **No technical moat.** See What Makes This Different — the advantage is execution and transparency, not a defensible technical barrier.

## Scope

**IN — v1 (this course, ~11 weeks — matches `docs/plan.md`'s Sept 27 – Dec 15 timeline):**
1. Historical AIS/voyage ingestion from Kystdatahuset — locked: 8,094 voyages, Bergen Havn, Jan 2024–Mar 2026 (see addendum).
2. Derivation of actual-arrival events from AIS tracks, with a logged coverage metric (87.1% achieved).
3. A trained model predicting arrival 6h and 24h ahead on the locked dataset, benchmarked against reported ETA.
4. A web dashboard that replays a chosen day or period from the locked dataset: predicted arrivals, a map, and a stated reason per expected deviation, generated by an AI summarization layer.
5. Open access, no login — source data is open (NLOD), no personal data is processed, and v1 has a single user role. If the demo must be reachable remotely, a single shared HTTP Basic Auth stands in front of it (not user accounts). Full rationale in the addendum.

**OUT — deliberately deferred, not rejected:**
1. Real-time/live data as a source for v1 — deferred entirely; v1 runs on the locked historical dataset only, not a live feed. BarentsWatch Live AIS was kept as a documented contingency in case historical coverage proved insufficient (addendum) but was never triggered — 87.1% coverage was achieved from the Kystdatahuset archive alone.
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
