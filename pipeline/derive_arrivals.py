#!/usr/bin/env python3
"""Derive actual arrival from cached AIS tracks and compare to reported ETA.

PRIMARY label (v4, group's correction 2026-09-27 -- replaces the stop-detection rule
as the headline metric): arrival_in_area = the FIRST AIS position inside the ~15 km
port-area circle within the voyage's fetch window. No stop requirement, no gap rule,
no speed threshold of any kind -- a single position is enough. Rationale: the question
a havnevakt actually asks is "when does the ship get here", and zone entry is a clean,
well-defined geometric event that needs only one data point, unlike stop-detection,
which needs a pattern the data often doesn't contain (ISLAND CLIPPER, pilot voyage
2223567: only 29 minutes of continuous coverage in the inner zone total -- below what
either the gap rule or the stability fallback requires). Coverage on this label is
bounded only by voyages with no AIS positions in the window at all (~16% in the
pilot -- see "Known exclusion" below), not by whether a stop pattern happened to be
captured.

SECONDARY label, kept but non-blocking: arrival_at_quay, via the gap rule (v2) then
the position-stability fallback (v3) within a tighter ~1.5 km circle -- reported
wherever it can be derived, but a missing arrival_at_quay no longer affects a voyage's
overall coverage status. The difference (arrival_at_quay - arrival_in_area), when both
exist, is the area-to-berth dwell time -- reported as its own distribution, not
discarded.
  - find_gap_event: last position before a reporting gap of more than
    GAP_THRESHOLD_MINUTES with no positions at all, where the next position after the
    gap is still inside the zone. Valid because positions are fetched per-MMSI, so a
    gap can only mean this vessel went quiet, never "something else entered the zone."
  - find_stability_event (fallback when the gap rule finds nothing): first position
    that stays within STABILITY_MAX_DRIFT_METERS of itself for the following
    STABILITY_WINDOW_MINUTES. Position only -- sog and calc_speed are both untrusted
    for this (see fetch_ais.py's docstring for why sog never reads near-zero here).

Known exclusion, NOT resolved (group's correction: do not assert either explanation as
established) -- roughly 16% of pilot voyages returned zero AIS positions for their
MMSI in the fetch window, and every one of them was foreign-flagged (0 of 67
Norwegian-flag pilot voyages were empty; 16 of 33 foreign-flag were). Two candidate
explanations remain open and unresolved: (a) an access restriction on foreign-vessel
position history in the open/anonymous API tier, or (b) an MMSI mismatch, where
SafeSeaNet/Kystdatahuset's on-file MMSI for a foreign vessel is stale and the lookup
simply fails on the key. The direct test (cross-referencing by IMO via
/api/ship/combined/imo/{imo}) is blocked: that endpoint requires the
"Kystdatahuset_ekstern_alle" role live, despite the OpenAPI spec not flagging JWT on
it. An open substitute (/api/ais_shipreg/statinfo/for-mmsis-time) also returned empty
for the MMSIs tested, which is suggestive but not conclusive either way. Documented as
an open question, not a resolved cause.

Known, documented limitation, NOT fixed: two pilot voyages (VESTERALEN, KONG HARALD --
both Hurtigruten coastal-route ships) were 231 km and 420 km from Bergen throughout
their fetch window -- the multi-day Bergen-Kirkenes route means the window (capped at
the next voyage's ETD) doesn't reach far enough for this route type.

Same-vessel window fix: voyages are grouped by MMSI and sorted by ETA; each voyage's
search window is capped at the *next* voyage's ETD for the same MMSI (if one exists in
this Bergen-arrival dataset), never at a fixed +48h if that next voyage arrives
sooner -- prevents a frequent caller's search from bleeding into its own next port
call. If a search reaches that boundary without finding an event, status is
"avkortet_av_neste_seilas" (truncated by next voyage), counted separately from a
genuine "not_detected". The last voyage per MMSI keeps the natural ETA+48h window.

Reporting is split by ship_group ("Passasjer" vs. everything else) as a proxy for
scheduled/liner vs. non-scheduled traffic: scheduled ferries showed near-zero
deviation from their own reported ETA in the pilot, while non-scheduled traffic had a
long tail of large misses -- pooling the two would hide that tail inside the scheduled
fleet's near-perfect self-reporting. This is a proxy (some "Passasjer" traffic is
cruise, not liner), flagged for refinement later.

Reads pipeline/data/ais_cache/{voyageid}.json (written by fetch_ais.py) and the
voyages CSV (written by fetch_voyages.py). Writes pipeline/data/bergen_eta_avvik.csv.

Usage:
    python3 pipeline/derive_arrivals.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv
    python3 pipeline/derive_arrivals.py --voyages ... --sample 10
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta

VOYAGES_DEFAULT = "pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv"
CACHE_DIR = "pipeline/data/ais_cache"
OUT_DEFAULT = "pipeline/data/bergen_eta_avvik.csv"

PORT_CENTER_LAT = 60.398
PORT_CENTER_LON = 5.321
OUTER_RADIUS_KM = 15.0  # arrival_in_area (primary) -- zone entry, no stop required
INNER_RADIUS_KM = 1.5   # arrival_at_quay (secondary) -- gap rule + stability fallback

GAP_THRESHOLD_MINUTES = 30
STABILITY_WINDOW_MINUTES = 30
STABILITY_MAX_DRIFT_METERS = 50
EDGE_PROXIMITY_HOURS = 3

# Must match fetch_ais.py's fetch window (this only ever narrows the analysis window
# further via the next-voyage cap, never widens it beyond what was fetched).
WINDOW_BEFORE_FALLBACK_HOURS = 24
WINDOW_AFTER_HOURS = 48
ETD_SANITY_CAP_DAYS = 14

# Column indices in each cached AIS row -- verified empirically against the live API
# on 2026-09-27 (see fetch_ais.py docstring).
IDX_TS, IDX_LON, IDX_LAT, IDX_SOG, IDX_CALC = 1, 2, 3, 5, 7


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_naive_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def compute_fetch_window(row: dict) -> tuple[datetime, datetime]:
    """The window fetch_ais.py actually fetched -- unchanged."""
    eta = parse_naive_utc(row["eta"])
    start = None
    etd_raw = row.get("etd")
    if etd_raw:
        try:
            etd = parse_naive_utc(etd_raw)
            if etd < eta and (eta - etd) <= timedelta(days=ETD_SANITY_CAP_DAYS):
                start = etd
        except ValueError:
            pass
    if start is None:
        start = eta - timedelta(hours=WINDOW_BEFORE_FALLBACK_HOURS)
    end = eta + timedelta(hours=WINDOW_AFTER_HOURS)
    return start, end


def find_zone_entry(pts: list, radius_km: float, window_start: datetime, window_end: datetime):
    """Primary rule: first position (chronological) inside radius_km, no other
    condition. pts: full sorted (ts, lat, lon, sog, calc) list, unfiltered by zone."""
    for ts, lat, lon, *_ in pts:
        if not (window_start <= ts <= window_end):
            continue
        if haversine_km(lat, lon, PORT_CENTER_LAT, PORT_CENTER_LON) <= radius_km:
            return ts
    return None


def find_gap_event(pts: list, radius_km: float, window_start: datetime, window_end: datetime):
    """Secondary rule, part 1. Returns (arrival_ts, gap_minutes) or (None, None)."""
    in_window = [p for p in pts if window_start <= p[0] <= window_end]
    for (ts1, lat1, lon1, *_), (ts2, lat2, lon2, *_) in zip(in_window, in_window[1:]):
        d1 = haversine_km(lat1, lon1, PORT_CENTER_LAT, PORT_CENTER_LON)
        d2 = haversine_km(lat2, lon2, PORT_CENTER_LAT, PORT_CENTER_LON)
        if d1 > radius_km or d2 > radius_km:
            continue
        gap_min = (ts2 - ts1).total_seconds() / 60
        if gap_min > GAP_THRESHOLD_MINUTES:
            return ts1, round(gap_min, 1)
    return None, None


def find_stability_event(pts: list, radius_km: float, window_start: datetime, window_end: datetime):
    """Secondary rule, part 2 (fallback). Returns arrival_ts or None."""
    in_zone = [
        p for p in pts
        if window_start <= p[0] <= window_end
        and haversine_km(p[1], p[2], PORT_CENTER_LAT, PORT_CENTER_LON) <= radius_km
    ]
    window = timedelta(minutes=STABILITY_WINDOW_MINUTES)
    for i, (ts_i, lat_i, lon_i, *_rest) in enumerate(in_zone):
        followers = [p for p in in_zone[i:] if p[0] - ts_i <= window]
        if not followers or (followers[-1][0] - ts_i) < window:
            continue
        max_drift_m = max(haversine_km(lat_i, lon_i, p[1], p[2]) * 1000 for p in followers)
        if max_drift_m <= STABILITY_MAX_DRIFT_METERS:
            return ts_i
    return None


def load_sorted_points(positions: list) -> list:
    pts = [
        (parse_naive_utc(row[IDX_TS]), row[IDX_LAT], row[IDX_LON], row[IDX_SOG], row[IDX_CALC])
        for row in positions
    ]
    pts.sort(key=lambda p: p[0])
    return pts


def build_next_etd_by_voyage(voyages: list) -> dict:
    by_mmsi = defaultdict(list)
    for v in voyages:
        by_mmsi[v["mmsino"]].append(v)
    next_etd = {}
    for mmsi, rows in by_mmsi.items():
        rows_sorted = sorted(rows, key=lambda r: parse_naive_utc(r["eta"]))
        for i, v in enumerate(rows_sorted):
            if i + 1 < len(rows_sorted):
                nxt_etd_raw = rows_sorted[i + 1].get("etd")
                next_etd[v["voyageid"]] = parse_naive_utc(nxt_etd_raw) if nxt_etd_raw else None
            else:
                next_etd[v["voyageid"]] = None
    return next_etd


def percentile(sorted_vals: list, p: float) -> float:
    if not sorted_vals:
        return float("nan")
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo, hi = int(math.floor(idx)), int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def baseline_stats(devs: list) -> dict:
    n = len(devs)
    if n == 0:
        return {"n": 0}
    abs_devs = sorted(abs(d) for d in devs)
    signed_sorted = sorted(devs)
    mae = sum(abs_devs) / n
    median_signed = percentile(signed_sorted, 0.5)
    within_30 = sum(1 for d in devs if abs(d) <= 30) / n
    over_2h = sum(1 for d in devs if abs(d) > 120) / n
    return {
        "n": n, "mae": mae, "median_signed": median_signed,
        "within_30min": within_30, "over_2h": over_2h,
        "min": signed_sorted[0], "max": signed_sorted[-1],
    }


TEST_FRACTION = 0.2  # chronological split: last 20% of voyages by ETA is held out


def group_of(row: dict) -> str:
    return "Passasjer" if row["ship_group"] == "Passasjer" else "Non-Passasjer"


DELAY_THRESHOLD_MINUTES = 120  # ">2h" -- the group's chosen definition of a disruption
                               # worth flagging to a havnevakt


def compute_offsets_and_split(output_rows: list) -> tuple:
    """Chronological (by eta_reported) 80/20 split, and offset[ship_group] = median
    dwell_area_to_quay_minutes on TRAIN rows only. Split is chronological, not random
    -- consistent with how this would actually be evaluated once a model exists, and
    avoids leaking the test period's dwell pattern into the offset."""
    by_time = sorted(output_rows, key=lambda r: r["eta_reported"])
    split_idx = int(len(by_time) * (1 - TEST_FRACTION))
    train_rows, test_rows = by_time[:split_idx], by_time[split_idx:]

    offsets = {}
    for group in ("Passasjer", "Non-Passasjer"):
        train_dwell = [
            float(r["dwell_area_to_quay_minutes"]) for r in train_rows
            if group_of(r) == group and r["status_in_area"] == "ok" and r["status_at_quay"] == "ok"
        ]
        offsets[group] = percentile(sorted(train_dwell), 0.5) if train_dwell else None
    return offsets, train_rows, test_rows


def run_calibration_analysis(offsets: dict, train_rows: list, test_rows: list) -> None:
    """Group's correction 2026-09-27: arrival_in_area stays a raw observation (no
    dwell baked into the label). Instead, the REPORTED ETA baseline is calibrated:
        calibrated_baseline = eta_reported - offset[ship_group]
    Naive and calibrated headline stats are both computed on the TEST split only, so
    the comparison in the printed table is apples-to-apples (the earlier "naive"
    numbers reported before this correction were computed on the full pilot batch,
    not held-out data, and mixed an uncalibrated baseline with the evaluation set --
    both fixed here)."""
    for group in ("Passasjer", "Non-Passasjer"):
        n_train = sum(1 for r in train_rows if group_of(r) == group and r["status_in_area"] == "ok" and r["status_at_quay"] == "ok")
        off = offsets.get(group)
        print(
            f"  offset[{group}] = median dwell on TRAIN = "
            f"{'n/a (no train rows with both labels)' if off is None else f'{off:.1f}min'} "
            f"(train n={n_train})",
            file=sys.stderr,
        )

    test_dates = sorted(r["eta_reported"][:10] for r in test_rows)
    print(
        f"\nSplit: {len(train_rows)} train / {len(test_rows)} test "
        f"(chronological, last {TEST_FRACTION:.0%} by ETA: {test_dates[0]} .. {test_dates[-1]}). "
        f"TEST set below is what both tables are evaluated on.\n"
        f"  Method note: a chronological split is the right call to avoid leaking the "
        f"test period's dwell pattern into the offset -- but on this dataset it also means "
        f"the test window sits in one season (see dates above). Generalization claims "
        f"beyond that season are not supported by this split alone.",
        file=sys.stderr,
    )

    print(
        "\nMetric order per group's correction 2026-09-27: MAE is unstable on a "
        "tail-heavy distribution (calibrated/Non-Passasjer showed median -6.6min, "
        "50% within +/-30min, yet MAE 365min -- a few extreme voyages dominate the "
        "mean). +/-30min is now the headline; MAE and median are support stats only.",
        file=sys.stderr,
    )
    print("\n%-24s %6s %11s %11s %10s %10s" % ("group", "n", "+/-30min", "MAE(supp)", "med(supp)", "off>2h"), file=sys.stderr)
    for label, use_calibrated in [("naive", False), ("calibrated", True)]:
        for group in ("ALL", "Passasjer", "Non-Passasjer"):
            rows = [r for r in test_rows if r["status_in_area"] == "ok" and (group == "ALL" or group_of(r) == group)]
            devs = []
            for r in rows:
                raw_dev = float(r["deviation_in_area_minutes"])
                if not use_calibrated:
                    devs.append(raw_dev)
                    continue
                g = group_of(r)
                off = offsets.get(g)
                if off is None:
                    continue  # can't calibrate this row's group -- excluded, not zero-filled
                devs.append(raw_dev + off)
            s = baseline_stats(devs)
            if s["n"]:
                print(
                    "%-24s %6d %10.1f%% %10.1f %10.1f %9.1f%%" % (
                        f"{label}/{group}", s["n"], s["within_30min"] * 100,
                        s["mae"], s["median_signed"], s["over_2h"] * 100,
                    ),
                    file=sys.stderr,
                )
            else:
                print(f"{label}/{group:<10} n=0 (no evaluable rows)", file=sys.stderr)

    print(
        "\nWhy naive and calibrated differ: arrival_in_area fires at zone entry "
        "(~15 km out), which precedes berth arrival by the dwell time (median ~1h, "
        "see area-to-quay dwell section) -- the ship's own reported ETA most likely "
        "targets berth arrival, not zone entry. The naive comparison is therefore "
        "measuring two different physical events and overstates the miss; the "
        "calibrated baseline (eta - train-derived offset) targets the same event "
        "arrival_in_area actually measures.",
        file=sys.stderr,
    )
def label_delay(deviation_calibrated_minutes: float) -> bool:
    """The one ground-truth delay definition, used consistently everywhere:
    er_forsinket = kalibrert_arrival_in_area - rapportert_eta > DELAY_THRESHOLD_MINUTES.
    Signed, not absolute -- this flags LATE arrivals specifically ("forsinket"), not
    early ones. Precision/recall against this flag is a MODEL metric and is deferred
    until a model exists (group's correction 2026-09-27): the reported ETA baseline
    predicts zero deviation by definition, so it never flags anything -- precision/
    recall against a baseline that never predicts positive is degenerate, not a
    result. This function only defines the label; nothing in this script evaluates
    a classifier against it yet."""
    return deviation_calibrated_minutes > DELAY_THRESHOLD_MINUTES


def report_label_agreement(output_rows: list, offsets: dict) -> None:
    """Data-quality cross-check (group's correction 2026-09-27), NOT a result:
    on voyages where both arrival_in_area and arrival_at_quay were derived, how often
    do the two labels agree on er_forsinket? arrival_at_quay needs no calibration (it
    already targets berth arrival), so its own deviation vs. reported ETA is used
    directly. Uses all rows with both labels (not test-restricted) -- this
    characterizes label agreement, not a leakage-sensitive fitted parameter, so the
    full sample is used for a more reliable number. Belongs in the methods/
    limitations section, not the results section."""
    both = [
        r for r in output_rows
        if r["status_in_area"] == "ok" and r["status_at_quay"] == "ok" and offsets.get(group_of(r)) is not None
    ]
    n = len(both)
    print(f"\nLabel agreement check (methods/limitations, not a result) -- n={n} voyages with both labels:", file=sys.stderr)
    if n == 0:
        print("  no rows with both labels available.", file=sys.stderr)
        return
    agree = 0
    for r in both:
        off = offsets[group_of(r)]
        in_area_flag = label_delay(float(r["deviation_in_area_minutes"]) + off)
        at_quay_flag = label_delay(float(r["deviation_at_quay_minutes"]))
        agree += in_area_flag == at_quay_flag
    print(
        f"  arrival_in_area (calibrated) and arrival_at_quay (raw) agree on "
        f"er_forsinket (>{DELAY_THRESHOLD_MINUTES}min late) in {agree}/{n} ({agree/n:.1%}) of cases.",
        file=sys.stderr,
    )


def check_dwell_selection_bias(output_rows: list, voyages: list) -> None:
    """Group's correction 2026-09-27: dwell (and therefore the offset used to
    calibrate the baseline) only exists for voyages where BOTH labels were derived.
    If that subset differs systematically from the rest (e.g. by vessel length or
    type), the offset is biased toward whatever kind of voyage is easier to detect
    at_quay for. Compares length and ship_type between "has dwell" and "in_area ok,
    no at_quay" -- does not adjust anything, just reports whether they look alike."""
    voy_by_id = {v["voyageid"]: v for v in voyages}
    with_dwell, without_dwell = [], []
    for r in output_rows:
        if r["status_in_area"] != "ok":
            continue
        v = voy_by_id.get(r["voyageid"])
        if v is None:
            continue
        (with_dwell if r["status_at_quay"] == "ok" else without_dwell).append(v)

    def length_stats(vs):
        lengths = sorted(float(v["length"]) for v in vs if v.get("length"))
        if not lengths:
            return None
        return {
            "n": len(lengths), "median": percentile(lengths, 0.5),
            "mean": sum(lengths) / len(lengths),
        }

    def type_counts(vs):
        c = defaultdict(int)
        for v in vs:
            c[v.get("ship_type", "?")] += 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1])[:5])

    ls_with, ls_without = length_stats(with_dwell), length_stats(without_dwell)
    print(f"\nDwell-derivation selection-bias check (with dwell n={len(with_dwell)}, without n={len(without_dwell)}):", file=sys.stderr)
    if ls_with and ls_without:
        print(
            f"  length (m): with_dwell median={ls_with['median']:.1f} mean={ls_with['mean']:.1f} | "
            f"without_dwell median={ls_without['median']:.1f} mean={ls_without['mean']:.1f}",
            file=sys.stderr,
        )
    print(f"  top ship_type, with dwell:    {type_counts(with_dwell)}", file=sys.stderr)
    print(f"  top ship_type, without dwell: {type_counts(without_dwell)}", file=sys.stderr)


def summarize_coverage(rows: list, label: str) -> None:
    n_total = len(rows)
    print(f"\n-- {label} (n={n_total}) --", file=sys.stderr)
    for zone_label, status_key in [("arrival_in_area (PRIMARY)", "status_in_area"), ("arrival_at_quay (secondary)", "status_at_quay")]:
        status_counts = defaultdict(int)
        for r in rows:
            status_counts[r[status_key]] += 1
        coverage = status_counts["ok"] / n_total if n_total else 0.0
        line = f"  {zone_label}: ok={status_counts['ok']} ({coverage:.1%})"
        for k in ("avkortet_av_neste_seilas", "not_detected", "empty"):
            if status_counts[k]:
                line += f", {k}={status_counts[k]}"
        print(line, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voyages", default=VOYAGES_DEFAULT)
    parser.add_argument("--out", default=OUT_DEFAULT)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args()

    with open(args.voyages, newline="", encoding="utf-8") as f:
        voyages = list(csv.DictReader(f))

    voyages = [v for v in voyages if os.path.exists(os.path.join(CACHE_DIR, f"{v['voyageid']}.json"))]
    next_etd_map = build_next_etd_by_voyage(voyages)

    fieldnames = [
        "voyageid", "mmsino", "shipname", "ship_group", "eta_reported",
        "window_start", "window_end_used", "truncated_by_next_voyage",
        "arrival_in_area_utc", "deviation_in_area_minutes", "status_in_area",
        "arrival_at_quay_utc", "gap_at_quay_minutes", "deviation_at_quay_minutes", "method_at_quay", "status_at_quay",
        "dwell_area_to_quay_minutes", "near_window_edge",
        "deviation_calibrated_minutes", "er_forsinket",
    ]
    output_rows = []

    for v in voyages:
        voyageid = v["voyageid"]
        eta = parse_naive_utc(v["eta"])
        fetch_start, natural_end = compute_fetch_window(v)
        next_etd = next_etd_map.get(voyageid)
        if next_etd is not None and fetch_start < next_etd < natural_end:
            window_end_used = next_etd
            truncated = True
        else:
            window_end_used = natural_end
            truncated = False

        row_out = {
            "voyageid": voyageid, "mmsino": v["mmsino"], "shipname": v["shipname"],
            "ship_group": v.get("ship_group", ""), "eta_reported": v["eta"],
            "window_start": fetch_start.isoformat(), "window_end_used": window_end_used.isoformat(),
            "truncated_by_next_voyage": truncated,
            "arrival_in_area_utc": "", "deviation_in_area_minutes": "", "status_in_area": "",
            "arrival_at_quay_utc": "", "gap_at_quay_minutes": "", "deviation_at_quay_minutes": "", "method_at_quay": "", "status_at_quay": "",
            "dwell_area_to_quay_minutes": "", "near_window_edge": False,
            "deviation_calibrated_minutes": "", "er_forsinket": "",
        }

        with open(os.path.join(CACHE_DIR, f"{voyageid}.json"), encoding="utf-8") as cf:
            positions = json.load(cf)

        if not positions:
            row_out["status_in_area"] = "empty"
            row_out["status_at_quay"] = "empty"
            output_rows.append(row_out)
            continue

        pts = load_sorted_points(positions)
        near_edge = False

        # Primary: zone entry, no stop condition.
        arrival_in_area = find_zone_entry(pts, OUTER_RADIUS_KM, fetch_start, window_end_used)
        if arrival_in_area is not None:
            row_out["arrival_in_area_utc"] = arrival_in_area.isoformat()
            row_out["deviation_in_area_minutes"] = round((arrival_in_area - eta).total_seconds() / 60, 1)
            row_out["status_in_area"] = "ok"
            if (arrival_in_area - fetch_start) < timedelta(hours=EDGE_PROXIMITY_HOURS) or \
               (window_end_used - arrival_in_area) < timedelta(hours=EDGE_PROXIMITY_HOURS):
                near_edge = True
        else:
            row_out["status_in_area"] = "avkortet_av_neste_seilas" if truncated else "not_detected"

        # Secondary: gap rule, then stability fallback. Non-blocking.
        arrival_at_quay, gap_min = find_gap_event(pts, INNER_RADIUS_KM, fetch_start, window_end_used)
        method = "gap"
        if arrival_at_quay is None:
            arrival_at_quay = find_stability_event(pts, INNER_RADIUS_KM, fetch_start, window_end_used)
            gap_min = ""
            method = "stability"
        if arrival_at_quay is not None:
            row_out["arrival_at_quay_utc"] = arrival_at_quay.isoformat()
            row_out["gap_at_quay_minutes"] = gap_min
            row_out["deviation_at_quay_minutes"] = round((arrival_at_quay - eta).total_seconds() / 60, 1)
            row_out["method_at_quay"] = method
            row_out["status_at_quay"] = "ok"
            if (arrival_at_quay - fetch_start) < timedelta(hours=EDGE_PROXIMITY_HOURS) or \
               (window_end_used - arrival_at_quay) < timedelta(hours=EDGE_PROXIMITY_HOURS):
                near_edge = True
            if arrival_in_area is not None:
                row_out["dwell_area_to_quay_minutes"] = round((arrival_at_quay - arrival_in_area).total_seconds() / 60, 1)
        else:
            row_out["status_at_quay"] = "avkortet_av_neste_seilas" if truncated else "not_detected"

        row_out["near_window_edge"] = near_edge
        output_rows.append(row_out)

    # Offsets/split computed once here (before writing) so the calibrated label and
    # the er_forsinket ground-truth flag can be persisted per row -- ready for the
    # modeling phase, not just printed to console.
    offsets, train_rows, test_rows = compute_offsets_and_split(output_rows)
    for r in output_rows:
        if r["status_in_area"] != "ok":
            continue
        off = offsets.get(group_of(r))
        if off is None:
            continue
        cal_dev = round(float(r["deviation_in_area_minutes"]) + off, 1)
        r["deviation_calibrated_minutes"] = cal_dev
        r["er_forsinket"] = label_delay(cal_dev)

    with open(args.out, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Processed {len(output_rows)} voyages (that had AIS data fetched) -> {args.out}", file=sys.stderr)

    scheduled = [r for r in output_rows if r["ship_group"] == "Passasjer"]
    other = [r for r in output_rows if r["ship_group"] != "Passasjer"]

    summarize_coverage(output_rows, "ALL")
    summarize_coverage(scheduled, "Passasjer (proxy for rutegaende/scheduled)")
    summarize_coverage(other, "Non-Passasjer (proxy for ikke-rutegaende)")

    both = [r for r in output_rows if r["status_in_area"] == "ok" and r["status_at_quay"] == "ok"]
    if both:
        dwell = sorted(float(r["dwell_area_to_quay_minutes"]) for r in both)
        print(
            f"\nArea-to-quay dwell time (n={len(dwell)} voyages with both labels derived) -- PRELIMINARY, "
            f"recompute on full batch before locking:\n"
            f"  median={percentile(dwell, 0.5):.1f}min  Q1={percentile(dwell, 0.25):.1f}min  Q3={percentile(dwell, 0.75):.1f}min  "
            f"min={dwell[0]:.1f}min  max={dwell[-1]:.1f}min",
            file=sys.stderr,
        )
    else:
        print("\nArea-to-quay dwell time: no voyages had both labels derived in this batch.", file=sys.stderr)

    print(
        "\n--- Calibrated baseline (group's correction 2026-09-27): offset = median TRAIN dwell per "
        "ship_group; naive and calibrated both evaluated on the held-out TEST split only. Previously "
        "reported naive numbers on the full pilot batch are superseded -- do not reuse them. ---",
        file=sys.stderr,
    )
    run_calibration_analysis(offsets, train_rows, test_rows)
    report_label_agreement(output_rows, offsets)
    check_dwell_selection_bias(output_rows, voyages)

    n_truncated = sum(1 for r in output_rows if r["truncated_by_next_voyage"])
    print(f"\n{n_truncated}/{len(output_rows)} voyages had their window capped by a next voyage for the same MMSI.", file=sys.stderr)

    if args.sample:
        detected = [r for r in output_rows if r["status_in_area"] == "ok"]
        sample = random.sample(detected, min(args.sample, len(detected)))
        print(f"\n--- Manual spot check: {len(sample)} random voyages ---", file=sys.stderr)
        for r in sample:
            print(
                f"  voyage {r['voyageid']} ({r['shipname']}, {r['ship_group']}): "
                f"ETA={r['eta_reported']} | in_area={r['arrival_in_area_utc']} (dev {r['deviation_in_area_minutes']}min) | "
                f"at_quay={r['arrival_at_quay_utc']} (dev {r['deviation_at_quay_minutes']}min) | "
                f"dwell={r['dwell_area_to_quay_minutes']}min | truncated={r['truncated_by_next_voyage']} edge={r['near_window_edge']}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
