---
title: "Product Brief: AIS-basert ankomstprediksjon (working title)"
status: draft
created: 2026-09-17
updated: 2026-09-17
---

# Product Brief: AIS-basert ankomstprediksjon (working title)

## Executive Summary

For the havnevakt in Bergen Havn's Maritime Operations Center, we are building a decision-support tool that predicts when a ship will actually arrive — not just what it reported — so quay allocation can be planned against a number worth trusting instead of a self-reported ETA. Today, the havnevakt assigns quay space continuously based on vessel-reported ETAs, with no reliable way to know in advance which reports to trust and which will be hours off. The gap matters now because Bergen Havn — Norway's largest cargo port and largest cruise port — is already a named participant in Kystverket's NOK 10.5M "Digital tvilling i havn" initiative, whose explicit goal is streamlining vessel arrivals and reducing port waiting time. This project builds the prediction layer that initiative does not yet provide, using the same open AIS data Kystverket already publishes through Kystdatahuset.

## The Problem

Bergen Havn runs berth allocation through the havnevakt (duty officer) in its Maritime Operations Center — a shift-staffed role that continuously assigns quay space based on vessels' self-reported ETAs. The job, in one concrete scenario: a ship reports ETA 08:00; the next vessel is due at the same quay at 14:00; does the first ship actually arrive at 08:00, or 11:30 — and does anything need reassigning right now?

Reported ETAs are known industry-wide to diverge from actual arrival, because they don't reflect berth, pilot, or tug readiness — IMO's Just-In-Time Arrival Guide names this exact mechanism: a vessel can be perfectly "on time" by its own report and still cause avoidable waiting or a scramble to reassign a quay. No public documentation confirms this specific pain at Bergen Havn — that stays a reasoned inference from the general industry pattern, not a claimed fact. But the port has already committed real money to the adjacent problem: it is a named participant in Kystverket's "Digital tvilling i havn" project, whose stated purpose is to streamline vessel arrivals and reduce port time — evidence the institution already treats today's ETA information as insufficient to plan against.

## The Solution

A decision-support tool that predicts when a ship will actually arrive at Bergen Havn — 6 and 24 hours ahead — built on open AIS and voyage data from Kystverket's Kystdatahuset. Because the raw data only carries each vessel's self-reported ETA, the pipeline first derives actual arrival events from AIS tracks (a standard technique: a port-area polygon combined with a stopped-speed threshold) to build a labeled dataset of the deviation between reported and real arrival. A model trained on that dataset produces the 6h/24h predictions, benchmarked against the vessel's own reported ETA — the reference every prediction has to beat. A generative AI layer turns each day's predictions into a short daily brief for the havnevakt: a map plus a stated reason for each expected deviation, so the operator sees not just a number but why it is likely wrong.

v1 ships as a web dashboard, open without login (see Scope). The group's stated ambition is a live pipeline against fresh Kystdatahuset data, with a tested contingency plan if live data proves too gappy within the course timeline (full plan in the addendum).

## What Makes This Different

No AIS-ETA vendor found in the market — Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic — publishes an audited, reproducible accuracy benchmark; their claims are marketing copy, not documented methodology. That is itself a legitimate differentiator: this project measures itself, in public, against the one honest baseline available — the vessel's own reported ETA. Kystdatahuset is a data source, not a prediction product, so no existing tool sits on top of exactly this data today.

The closest Nordic academic precedent, an NTNU thesis on AIS-based turnaround-time prediction at Mongstad, reached a cautionary conclusion ("a convoluted task with many hidden variables") — an honest reference point, not a bar this project claims to clear easily. A closer methodological precedent exists outside Norway: a Hong Kong study combining AIS trajectories with port-call data via XGBoost cut ETA error by 52.98% against the vessel's own reported ETA, using a near-identical approach at a different port — real evidence the method works, not a promise this group will match that number.

Honestly: there is no technical moat here. The advantage is being first to point this exact method at Bergen Havn's exact ETA-accuracy problem, and being transparent about the resulting number instead of asserting one.

## Who This Serves

**Primary: the havnevakt in Bergen Havn's Maritime Operations Center** (public 24/7 contact: havnevakt@bergenhavn.no) — a shift-based role that continuously assigns quay space. Success for them: fewer last-minute quay reassignments, and a trustworthy answer to "will this ship actually be here when it says it will."

**Secondary: havnekaptein / driftsleder** — tactical planning over weeks rather than single port calls, using the same predictions rolled up into patterns and capacity views.

**Explicitly not a v1 user:** shipping companies, ship agents, cargo owners. Widening the audience to them is a deliberate later-stage decision (see Vision), not an oversight.

## Success Criteria

**Functional.** The model predicts arrival 6h and 24h ahead for vessels calling at Bergen Havn, scored against that vessel's own reported ETA as the baseline it has to beat. Since no external, audited industry benchmark exists (see What Makes This Different), the group will compute its own reported-ETA error baseline directly from Kystdatahuset data and set the target as a percentage improvement over that self-computed baseline. The Hong Kong precedent (52.98% MAE reduction vs. self-reported ETA) is a useful aspirational reference for what "good" looks like with this method — not a number to adopt directly, since it comes from a different port and pipeline.

**Data quality.** Daily AIS coverage is logged as an explicit metric; voyages where actual arrival cannot be derived are dropped and counted, not silently interpolated (full contingency plan in the addendum).

**Product.** The havnevakt can read a daily brief and understand, without asking anyone, which of tomorrow's expected arrivals to distrust and why.

## Scope

**IN — v1 (this course, ~12 weeks):**
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
