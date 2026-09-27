#!/usr/bin/env python3
"""Fetch AIS positions per voyage from Kystdatahuset, with disk caching.

Endpoint: POST /api/ais/positions/for-mmsis-time
Body: {"mmsiIds": [<mmsi>], "start": "<yyyyMMddHHmm>", "end": "<yyyyMMddHHmm>"}
No authentication required (verified against live API + OpenAPI spec, 2026-09-27).
Deliberately NOT using within-bbox-time: bbox scanning pulls in every ship in the area,
not just the one we asked for -- far more data than needed for a per-voyage lookup.

Fetch window (revised 2026-09-27, group's correction): a fixed ETA+/-12h window
systematically drops voyages that miss their own ETA by more than 12h -- exactly the
high-deviation cases the whole project is built to catch. That is biased data loss,
not random loss, and it would pull the headline result toward zero. Window is now:
    start = this voyage's own etd (departure from its origin port), sanity-capped
             at 14 days before eta; falls back to eta-24h if etd is missing, later
             than eta, or further back than the cap
    end   = eta + 48h
See derive_arrivals.py for the "how much of this window are we actually using"
edge-proximity check the group asked for.

Response rows are untyped arrays (the OpenAPI spec does not name the columns). Column
order was verified empirically against the live API on 2026-09-27, not assumed:
    0 mmsi          6 message_nr (AIS msg type: 1 or 3, both Class A position reports)
    1 date_time_utc 7 calc_speed  (derived from position deltas -- see note below)
    2 longitude     8 sec_prevpoint (exact match to elapsed seconds between rows -- verified)
    3 latitude      9 dist_prevpoint (metres since previous point)
    4 cog (course)  10 true_heading (compass degrees)
    5 sog (speed, knots, transponder-reported) 11 rot (rate of turn)
Correction (2026-09-27): field 11 was first assumed to be nav_status; a broader sample
showed values from -731 to 720, which rules that out (nav_status is 0-15 per spec) and
fits rot instead (large-magnitude values cluster on close-in points, consistent with a
vessel maneuvering to berth). nav_status does not appear to be present in this response
at all -- this endpoint returns 12 of PosMsg's 14 declared fields, dropping 'source' and
'nav_status'. This matches KDataAPI3.Models.GeoAisDB.PosMsg's field set, reordered for
the array serialization.

Field 5 (sog) vs field 7 (calc_speed): tested against the 100-voyage pilot batch, the
transponder-reported sog never drops below 0.5 kn anywhere within 1.5 km of the port
centre (0 of 13,449 close-range points) -- it has a noise floor that never reaches true
zero while moored. calc_speed does (1,004 of the same 13,449 points). derive_arrivals.py
uses calc_speed for exactly this reason.

minSpeed is intentionally omitted from the request (not set to any value) -- we need
low/zero-speed points to detect arrival, and the field defaults to no filtering.

Caches one JSON file per voyage under pipeline/data/ais_cache/{voyageid}.json so a
re-run never re-fetches a voyage that's already on disk. Logs per-voyage coverage
(rows received, window used, or why not) to pipeline/data/ais_coverage.csv -- this is
the coverage metric for the brief's data-quality section, not something to hide.

This is a public API: a REQUEST_DELAY_SECONDS pause sits between calls, and failed
calls retry with backoff before being logged as a gap.

Usage:
    python3 pipeline/fetch_ais.py --voyages pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv --limit 100
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

API_URL = "https://kystdatahuset.no/ws/api/ais/positions/for-mmsis-time"
WINDOW_BEFORE_FALLBACK_HOURS = 24
WINDOW_AFTER_HOURS = 48
ETD_SANITY_CAP_DAYS = 14
REQUEST_DELAY_SECONDS = 0.3
CACHE_DIR = "pipeline/data/ais_cache"
COVERAGE_PATH = "pipeline/data/ais_coverage.csv"


def to_kdh_time(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")


def parse_naive_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def compute_window(row: dict) -> tuple[datetime, datetime]:
    """Shared window logic -- derive_arrivals.py recomputes this identically so the
    edge-proximity check compares against the exact window that was actually fetched."""
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


def fetch_positions(mmsi: int, start: str, end: str, retries: int = 2) -> list:
    body = json.dumps({"mmsiIds": [mmsi], "start": start, "end": end}).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.load(resp)
            if not payload.get("success"):
                raise RuntimeError(f"API returned success=false: {payload.get('msg')}")
            return payload.get("data") or []
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voyages", required=True, help="CSV produced by fetch_voyages.py")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N voyages not already cached (for a pilot batch)")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)

    with open(args.voyages, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    coverage_exists = os.path.exists(COVERAGE_PATH)
    coverage_f = open(COVERAGE_PATH, "a", newline="", encoding="utf-8")
    coverage_writer = csv.writer(coverage_f)
    if not coverage_exists:
        coverage_writer.writerow(["voyageid", "mmsino", "eta", "window_start", "window_end", "num_positions", "status"])

    already_cached = 0
    fetched_ok = 0
    fetched_empty = 0
    fetched_error = 0
    processed_this_run = 0

    t0 = time.time()

    for row in rows:
        if args.limit is not None and processed_this_run >= args.limit:
            break

        voyageid = row["voyageid"]
        mmsi = int(row["mmsino"])
        cache_path = os.path.join(CACHE_DIR, f"{voyageid}.json")

        if os.path.exists(cache_path):
            already_cached += 1
            continue

        window_start, window_end = compute_window(row)
        start = to_kdh_time(window_start)
        end = to_kdh_time(window_end)

        try:
            positions = fetch_positions(mmsi, start, end)
            with open(cache_path, "w", encoding="utf-8") as cf:
                json.dump(positions, cf)
            status = "ok" if positions else "empty"
            if positions:
                fetched_ok += 1
            else:
                fetched_empty += 1
            coverage_writer.writerow([voyageid, mmsi, row["eta"], window_start.isoformat(), window_end.isoformat(), len(positions), status])
        except Exception as exc:  # noqa: BLE001 -- log and keep going, one bad voyage shouldn't kill the run
            fetched_error += 1
            coverage_writer.writerow([voyageid, mmsi, row["eta"], window_start.isoformat(), window_end.isoformat(), 0, f"error: {exc}"])
            print(f"  voyage {voyageid} FAILED: {exc}", file=sys.stderr)

        coverage_f.flush()
        processed_this_run += 1
        if processed_this_run % 25 == 0:
            elapsed = time.time() - t0
            print(f"  [{processed_this_run} fetched this run] cached_prior={already_cached} ok={fetched_ok} empty={fetched_empty} error={fetched_error} elapsed={elapsed:.0f}s", file=sys.stderr)

        time.sleep(REQUEST_DELAY_SECONDS)

    coverage_f.close()
    elapsed = time.time() - t0
    cache_bytes = sum(
        os.path.getsize(os.path.join(CACHE_DIR, fn))
        for fn in os.listdir(CACHE_DIR) if fn.endswith(".json")
    )
    print(
        f"\nDone. This run: {processed_this_run} voyages fetched in {elapsed:.1f}s "
        f"({elapsed/processed_this_run:.2f}s/voyage average).\n"
        f"  already cached (skipped): {already_cached}\n"
        f"  ok (has positions): {fetched_ok}\n"
        f"  empty (fetched, zero AIS positions in window): {fetched_empty}\n"
        f"  error: {fetched_error}\n"
        f"Cache dir size so far: {cache_bytes/1e6:.1f} MB across "
        f"{len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])} cached voyages.",
        file=sys.stderr,
    )
    print(f"Coverage log: {COVERAGE_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
