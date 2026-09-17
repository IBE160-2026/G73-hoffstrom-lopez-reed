---
title: "Product Brief: AIS-basert ankomstprediksjon (working title)"
status: draft
created: 2026-09-17
updated: 2026-09-17
---

# Product Brief: AIS-basert ankomstprediksjon (working title)

> **Session paused 2026-09-17.** Sections below are marked `[DRAFT]` (raw material captured, not yet reviewed/confirmed with the group), `[PARTIAL]` (grounded in research but waiting on a group decision), or `[NOT STARTED]`. See `.memlog.md` for the full trail and the next questions to pick up with.

## Executive Summary

**[DRAFT — raw material from initial brain dump, not yet polished or reviewed]**

A decision-support tool that predicts when ships will actually arrive at port, built on open AIS and voyage data from Kystverket's Kystdatahuset. The raw data only reports each vessel's self-reported planned ETA, so the group derives *actual* arrival time from AIS tracks and builds a dataset of deviations between reported and real arrival. A model is trained on this dataset to estimate arrival time 6 and 24 hours ahead, benchmarked against the vessel's own reported ETA as the reference baseline. A generative AI layer summarizes the output as a daily "disruption brief" for a port operator, including a map and a stated reason for each expected deviation.

## The Problem

**[INCOMPLETE — this is the open thread; brain dump went straight to the solution]**

Open questions the group needs to answer before this section can be written:

1. **Who is the port operator, concretely?** A named Norwegian port (Oslo Havn, Bergen Havn, Kristiansund, …) or a generic role? Without a concrete anchor, the pain stays abstract.
2. What does a port operator actually do today when a ship is running hours behind its reported ETA? What does the error cost them concretely (wasted berth time, overtime, rescheduling)?

## The Solution

**[DRAFT — raw material from brain dump, not yet polished or confirmed]**

Pipeline: ingest open AIS/voyage data from Kystdatahuset → derive actual arrival events from AIS tracks (the group has not yet fixed the exact detection method, though research below suggests this part is technically standard) → build a labeled dataset of deviation between reported and actual arrival → train a model predicting arrival 6h and 24h out → benchmark against the vessel's own reported ETA → generative AI layer produces a daily disruption brief per port operator, with a map and a stated reason for each predicted deviation.

Open question: delivery form of the daily brief — a dashboard/website the operator logs into, a generated PDF/email, or something else. This affects whether v1 needs authentication at all.

## What Makes This Different

**[PARTIAL — grounded in web research done 2026-09-17, not yet turned into brief prose or confirmed with the group]**

Key research findings to build this section from:
- No vendor found (Portcast, PortXchange, Awake.AI, Sinay, Windward, MarineTraffic) publishes an audited, reproducible ETA-accuracy benchmark — claims are marketing copy, not documented methodology. This is itself a legitimate differentiation point: nobody else is being rigorous here either.
- Kystdatahuset is a data source, not a prediction product — Kystverket itself does not appear to run an ETA model on top of it.
- Closest Nordic academic precedent: an NTNU thesis predicting ship turnaround time (AIS + AutoML/TPOT) at Mongstad — cautionary conclusion ("a convoluted task with many hidden variables"), useful as an honest reference point, not a bar to claim beating by a wide margin.
- Deriving "actual arrival" from AIS (port polygon + ~0.5 knot speed threshold) is standard technique, not the hard part of this project — the hard part is the prediction itself.

Not yet drafted: an explicit "why would a port operator switch to this" statement per the template's honesty rule (no fabricated moat).

## Who This Serves

**[INCOMPLETE — depends on Problem section open question 1]**

Placeholder: a port operator role at a Norwegian port. Needs to become concrete (who exactly, what are they trying to accomplish day to day, what does success look like for them) once the group has picked a real or realistic anchor port.

## Success Criteria

**[PARTIAL]**

Functional direction agreed: the model predicts arrival 6h and 24h ahead and is measured against the ship's own reported ETA as the baseline reference.

Research recommendation (not yet a group decision): since no external, audited ETA-error benchmark exists in the industry or literature, the group should compute its own baseline — how far off the reported ETA actually is, at 6h and 24h out, using Kystdatahuset data — and set the success criterion as a percentage improvement over that self-computed baseline, rather than citing an external number. Published literature MAE ranges from ~6 minutes (near-port/short-sea) to 2-5 hours (ocean-going, multi-day) depending on horizon, for calibration only.

## Scope

**[INCOMPLETE — pending group decision on ambition level]**

Open question: given ~12 weeks and a 3-person team, and given the project has three heavy parts (data pipeline, prediction model, generative reporting layer), is v1 aimed at an end-to-end pipeline against live/fresh data, or a system proven convincingly on a bounded historical dataset (e.g., one port, one vessel type, one season)? This decision will shape the entire IN/OUT boundary and has not been made yet.

## Vision

**[NOT STARTED]**

---

## Known constraints (not part of the brief itself, kept here for continuity)

- Course: IBE160 Programmering med KI, Høgskolen i Molde, group G73 (Theodor Gimming Hoffstrøm, Felipe Knudstad-Lopez, Thomas Kvile-Reed).
- This brief is due in 3 days; the full project runs ~12 weeks total and must end in a working prototype.
- Self-defined project — not one of the 8 course-suggested proposals.
- No prior written material existed for this idea before this session.
