---
title: "Product Brief: AIS-basert ankomstprediksjon (working title)"
status: draft
created: 2026-09-17
updated: 2026-09-17
---

# Product Brief: AIS-basert ankomstprediksjon (working title)

> **Session paused 2026-09-17 (second pause).** Sections below are marked `[DRAFT]` (raw material captured, not yet reviewed/confirmed with the group), `[PARTIAL]` (grounded in research but waiting on a group decision), or `[NOT STARTED]`. See `.memlog.md` for the full trail and the next questions to pick up with.

## Executive Summary

**[DRAFT — raw material from initial brain dump, not yet polished or reviewed]**

A decision-support tool that predicts when ships will actually arrive at port, built on open AIS and voyage data from Kystverket's Kystdatahuset. The raw data only reports each vessel's self-reported planned ETA, so the group derives *actual* arrival time from AIS tracks and builds a dataset of deviations between reported and real arrival. A model is trained on this dataset to estimate arrival time 6 and 24 hours ahead, benchmarked against the vessel's own reported ETA as the reference baseline. A generative AI layer summarizes the output as a daily "disruption brief" for a port operator, including a map and a stated reason for each expected deviation.

## The Problem

**[PARTIAL — anchor port confirmed (Bergen Havn); status-quo cost grounded via research 2026-09-17; still waiting on which operational role is the primary user]**

Confirmed about Bergen Havn (public sources, 2026-09-17 research pass):
- Norway's largest cargo port and largest cruise port, run by Bergen og Omland Havnevesen (BOH). Handles cruise traffic (~300–328 calls/year, ~590,000–631,000 passengers in 2024), offshore/supply vessels as a core segment, plus other cargo. Current total port-call volume could not be confirmed — the only figure found (~27,000–29,000 calls/year) dates to 2006–2011 and should not be used without a fresher source.
- Bergen Havn is a **named, confirmed participant** in Kystverket's "Digital tvilling i havn" (Digital Twin in Harbor) project (NOK 10.5M, 20 Norwegian ports + Kartverket, led by Oslo Havn), whose stated purpose is to streamline vessel arrival and port calls, reducing port time and waiting. This is real, current institutional appetite for this kind of tool — a genuine "why now," not an invented one. It is digital-twin/mapping infrastructure, not itself an ETA-prediction tool, so it is a tailwind, not a competitor.
- **No documentation found** of actual congestion, delay, or berth-scheduling problems specific to Bergen Havn. This must stay a reasoned inference from the general industry pattern below, never stated as a confirmed Bergen Havn pain point.
- **No direct public link found** between Bergen Havn and Kystdatahuset specifically.

General industry pattern (NOT Bergen-specific — applied here by analogy; final prose must keep this framing explicit):
- IMO's Just-In-Time (JIT) Arrival Guide names the exact mechanism this product targets: a vessel's self-reported ETA does not reflect berth, pilot, or tug readiness, so a ship can be perfectly "on time" by its own report and still cause avoidable waiting.
- Documented pattern elsewhere: better port-call coordination is linked to up to ~20% fuel savings per voyage (IMO estimate); one Port of Algeciras case reported a 40% reduction in idle time and 32.9 tonnes CO2 saved per call.
- No industry-wide monetary figure (e.g. "$X per hour of idle berth time") was found. Any such figure used in the brief must be labeled illustrative, not sourced.

Still open: which specific role at Bergen Havn is the primary user (see Who This Serves) — this decides whether the "today" workflow being disrupted is berth planning, pilot/tug dispatch, or something else, and that in turn decides which concrete daily task the AI brief needs to support.

## The Solution

**[DRAFT — raw material from brain dump, not yet polished or confirmed]**

Pipeline: ingest open AIS/voyage data from Kystdatahuset → derive actual arrival events from AIS tracks (the group has not yet fixed the exact detection method, though research below suggests this part is technically standard) → build a labeled dataset of deviation between reported and actual arrival → train a model predicting arrival 6h and 24h out → benchmark against the vessel's own reported ETA → generative AI layer produces a daily disruption brief per port operator, with a map and a stated reason for each predicted deviation.

Delivery form: a website/dashboard, tentatively decided — the group flagged this could still change. Whether it needs a login is explicitly left open (see Scope).

## What Makes This Different

**[PARTIAL — grounded in web research done 2026-09-17, not yet turned into brief prose or confirmed with the group]**

Key research findings to build this section from:
- No vendor found (Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic) publishes an audited, reproducible ETA-accuracy benchmark — claims are marketing copy, not documented methodology. This is itself a legitimate differentiation point: nobody else is being rigorous here either.
- Kystdatahuset is a data source, not a prediction product — Kystverket itself does not appear to run an ETA model on top of it.
- Closest Nordic academic precedent: an NTNU thesis predicting ship turnaround time (AIS + AutoML/TPOT) at Mongstad — cautionary conclusion ("a convoluted task with many hidden variables"), useful as an honest reference point, not a bar to claim beating by a wide margin.
- Deriving "actual arrival" from AIS (port polygon + ~0.5 knot speed threshold) is standard technique, not the hard part of this project — the hard part is the prediction itself.
- Strong feasibility precedent (added 2026-09-17): a Hong Kong study combining AIS trajectories with port-call data via XGBoost reduced ETA mean-absolute-error by **52.98% versus the vessel's own self-reported ETA** — near-identical method to this project's approach, at a different port. This is a citable proof the method works, not a promise this group will match it.

Not yet drafted: an explicit "why would a port operator switch to this" statement per the template's honesty rule (no fabricated moat).

## Who This Serves

**[INCOMPLETE — anchor port is now decided (Bergen Havn), but the specific operational role is not]**

Placeholder: a port operator role at Bergen Havn. Still needs to become concrete — is this a berth planner, a pilot/tug dispatcher, a traffic controller (trafikkleder), or something else? That choice decides what the daily AI brief actually needs to help someone *do*, and what "success" looks like for them day to day. Asked, not yet answered.

## Success Criteria

**[PARTIAL]**

Functional direction agreed: the model predicts arrival 6h and 24h ahead and is measured against the ship's own reported ETA as the baseline reference.

Research recommendation (not yet a group decision): since no external, audited ETA-error benchmark exists in the industry or literature, the group should compute its own baseline — how far off the reported ETA actually is, at 6h and 24h out, using Kystdatahuset data — and set the success criterion as a percentage improvement over that self-computed baseline, rather than citing an external number. Published literature MAE ranges from ~6 minutes (near-port/short-sea) to 2-5 hours (ocean-going, multi-day) depending on horizon, for calibration only. The Hong Kong AIS+XGBoost precedent (52.98% MAE reduction vs. self-reported ETA, see What Makes This Different) is a useful aspirational reference for what "good" looks like with this method — but it is a different port with a different pipeline, so it should not be adopted directly as this group's target number.

## Scope

**[INCOMPLETE — ambition level decided, boundary details still open]**

Decided: the group is going for the ambitious end-to-end version — a live pipeline against fresh Kystdatahuset data, not a bounded historical-data proof. User's words: "vi kjører på."

Still open / flagged but not yet answered:
- **AIS data-quality risk**: AIS has known coverage gaps and noise. Coach's question, asked but not yet answered: does the group have a fallback if live data turns out too messy for the full live-pipeline ambition within 12 weeks, or is the live-pipeline commitment firm regardless? This risk should be named explicitly in the final Scope section, not hidden.
- **Login/auth for v1**: explicitly left undecided by the group ("ikke bestemt"). The course's own evaluation framework (see `docs/kilder/Prosjektforslag...pdf`) asks projects to state a position on "Sikkerhet/innlogging" — this needs a real answer before the brief is finished, even if the answer is "no login in v1, because X."
- IN/OUT boundary list itself (capability-level, not feature list) has not been drafted yet — depends on the above being settled first.

## Vision

**[NOT STARTED]**

Open question, asked but not yet answered: where does this go in 2-3 years if it works — stays a Bergen Havn tool, expands to more Norwegian ports, or generalizes beyond port arrival (e.g. other AIS-driven maritime prediction problems)?

---

## Known constraints (not part of the brief itself, kept here for continuity)

- Course: IBE160 Programmering med KI, Høgskolen i Molde, group G73 (Theodor Gimming Hoffstrøm, Felipe Knudstad-Lopez, Thomas Kvile-Reed).
- This brief is due in 3 days; the full project runs ~12 weeks total and must end in a working prototype.
- Self-defined project — not one of the 8 course-suggested proposals.
- No prior written material existed for this idea before this session.
