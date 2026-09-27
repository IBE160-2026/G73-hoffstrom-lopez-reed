#!/usr/bin/env python3
"""Fetch voyages arriving at Bergen Havn (NOBGO) from Kystdatahuset's open Voyage API.

Endpoint: GET /api/voyage/between/{fromDate}/{toDate}
Confirmed against the live OpenAPI spec (kystdatahuset.no/ws/swagger/v1/swagger.json)
on 2026-09-27: this endpoint requires no authentication (JWT bearer is only required
for a few admin/upload endpoints, not for voyage or AIS position reads). Dates are UTC
"YYYY-MM-DD HH:MM:SSZ" strings.

Fetched month by month so a multi-year request stays within a few hundred MB in memory
at a time -- a single request for 2024-01-01..2026-03-15 nationwide would be > 1 GB.

Usage:
    python3 pipeline/fetch_voyages.py
    python3 pipeline/fetch_voyages.py --from-date 2024-01-01 --to-date 2026-03-15
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API_BASE = "https://kystdatahuset.no/ws/api/voyage/between"
ARR_LOCODE = "NOBGO"  # Bergen, locationid 2328078
FIELDS = [
    "voyageid",
    "mmsino",
    "shipname",
    "ship_type",
    "ship_group",
    "length",
    "eta",
    "etd",
    "dep_locname",
]


def month_chunks(from_date: date, to_date: date):
    """Yield (start, end) date pairs covering [from_date, to_date) in <=1-month steps."""
    cur = from_date
    while cur < to_date:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        nxt = min(nxt, to_date)
        yield cur, nxt
        cur = nxt


def fetch_chunk(from_dt: str, to_dt: str) -> list[dict]:
    url = f"{API_BASE}/{urllib.parse.quote(from_dt)}/{urllib.parse.quote(to_dt)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.load(resp)
    if not payload.get("success"):
        raise RuntimeError(f"Kystdatahuset API returned success=false: {payload.get('msg')}")
    return payload["data"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-date", default="2024-01-01", help="YYYY-MM-DD, inclusive (UTC)")
    parser.add_argument("--to-date", default="2026-03-15", help="YYYY-MM-DD, exclusive per API (UTC)")
    parser.add_argument("--out", default=None, help="Output CSV path (default: pipeline/data/voyages_bergen_<from>_<to>.csv)")
    args = parser.parse_args()

    from_date = date.fromisoformat(args.from_date)
    to_date = date.fromisoformat(args.to_date)

    out_path = args.out or f"pipeline/data/voyages_bergen_{args.from_date}_{args.to_date}.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    total_nationwide = 0
    total_bergen = 0
    seen_voyage_ids = set()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for chunk_start, chunk_end in month_chunks(from_date, to_date):
            from_dt = f"{chunk_start.isoformat()} 00:00:00Z"
            to_dt = f"{chunk_end.isoformat()} 00:00:00Z"
            print(f"Fetching {from_dt} -> {to_dt} ...", file=sys.stderr)
            try:
                voyages = fetch_chunk(from_dt, to_dt)
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                print(f"  Request failed for this chunk: {exc} -- skipping, logged as a gap.", file=sys.stderr)
                continue

            total_nationwide += len(voyages)
            bergen = [v for v in voyages if v.get("arr_locode") == ARR_LOCODE]
            new = 0
            for v in bergen:
                vid = v.get("voyageid")
                if vid in seen_voyage_ids:
                    continue  # month boundaries can overlap by a few seconds at the edge
                seen_voyage_ids.add(vid)
                writer.writerow({k: v.get(k) for k in FIELDS})
                new += 1
            total_bergen += new
            print(f"  {len(voyages)} nationwide, {new} new Bergen arrivals (running total: {total_bergen})", file=sys.stderr)

    print(f"\nDone. {total_nationwide} voyages nationwide across the full range, "
          f"{total_bergen} unique voyages arriving at {ARR_LOCODE} (Bergen).", file=sys.stderr)
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
