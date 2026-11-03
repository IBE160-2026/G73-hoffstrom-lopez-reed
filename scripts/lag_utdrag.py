"""Lag datautdrag og lagret baseline fra pipeline-output (E1-S02, arkitektur §4, A4).

Leser ``pipeline/data/bergen_eta_avvik.csv`` og skriver:

- ``<ut-dir>/utdrag/anlop.csv``: alle rader, bare kolonnene appen trenger, pluss ``split``.
- ``<ut-dir>/baseline.json``: offset per gruppe, start på testperioden, kilde og sha256.

Splitt og offset regnes nøyaktig som i ``pipeline/derive_arrivals.py``
(``percentile``, ``group_of`` og ``compute_offsets_and_split``). Logikken er kopiert,
ikke importert, fordi den modulen er et CLI-skript. Bare standardbiblioteket brukes.

Kjøres fra repo-roten:

    .venv/bin/python scripts/lag_utdrag.py [--kilde STI] [--ut-dir STI] [--laget ÅÅÅÅ-MM-DD]
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import sys
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
STANDARD_KILDE = Path("pipeline/data/bergen_eta_avvik.csv")
STANDARD_UT_DIR = Path("data")

KOLONNER = [
    "voyageid",
    "mmsino",
    "shipname",
    "ship_group",
    "eta_reported",
    "arrival_in_area_utc",
    "status_in_area",
    "split",
]

# Fra pipeline/derive_arrivals.py: TEST_FRACTION
TEST_ANDEL = 0.2
GRUPPER = ("Passasjer", "Øvrige")


def percentile(sorted_vals, p):
    """Kopi av ``percentile`` i pipeline/derive_arrivals.py (lineær interpolasjon)."""
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


def gruppe(rad):
    """Som ``group_of`` i derive_arrivals.py, men med navnet «Øvrige» for ikke-passasjer."""
    return "Passasjer" if rad["ship_group"] == "Passasjer" else "Øvrige"


def splitt_og_offset(rader):
    """Som ``compute_offsets_and_split`` i derive_arrivals.py.

    Stabil sortering på ``eta_reported`` som streng, ``split_idx = int(n * 0.8)``,
    offset = median av ``dwell_area_to_quay_minutes`` på train-rader der både
    ``status_in_area`` og ``status_at_quay`` er ``ok``. Gruppe uten slike rader gir None.
    """
    etter_tid = sorted(rader, key=lambda r: r["eta_reported"])
    split_idx = int(len(etter_tid) * (1 - TEST_ANDEL))
    train, test = etter_tid[:split_idx], etter_tid[split_idx:]

    offset = {}
    for g in GRUPPER:
        opphold = [
            float(r["dwell_area_to_quay_minutes"])
            for r in train
            if gruppe(r) == g and r["status_in_area"] == "ok" and r["status_at_quay"] == "ok"
        ]
        offset[g] = percentile(sorted(opphold), 0.5) if opphold else None
    return offset, train, test


def til_utc_z(tidspunkt):
    """``2025-09-14T03:15:00+00:00`` -> ``2025-09-14T03:15:00Z``. Uten suffiks tolkes som UTC."""
    t = dt.datetime.fromisoformat(tidspunkt)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def vis_sti(sti):
    """Kildesti som lagres i baseline.json: relativ til repo-roten når mulig."""
    absolutt = sti.resolve()
    try:
        return absolutt.relative_to(REPO_ROT).as_posix()
    except ValueError:
        return absolutt.as_posix()


def lag_utdrag(kilde, ut_dir, laget):
    """Les kilden, og skriv anlop.csv og baseline.json. Returnerer baseline-dikten."""
    innhold = kilde.read_bytes()
    sha = hashlib.sha256(innhold).hexdigest()
    rader = list(csv.DictReader(io.StringIO(innhold.decode("utf-8"), newline="")))

    offset, train, test = splitt_og_offset(rader)

    csv_buf = io.StringIO()
    skriver = csv.writer(csv_buf, lineterminator="\n")
    skriver.writerow(KOLONNER)
    for split, del_rader in (("train", train), ("test", test)):
        for r in del_rader:
            skriver.writerow([r[k] for k in KOLONNER[:-1]] + [split])

    baseline = {
        "offset_minutter": offset,
        "test_fra_utc": til_utc_z(test[0]["eta_reported"]) if test else None,
        "kilde": vis_sti(kilde),
        "kilde_sha256": sha,
        "laget": laget,
    }
    json_tekst = json.dumps(baseline, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    # Alt er regnet ut før noe skrives, så en feil i utregningen gir ingen filer.
    (ut_dir / "utdrag").mkdir(parents=True, exist_ok=True)
    with open(ut_dir / "utdrag" / "anlop.csv", "w", encoding="utf-8", newline="") as f:
        f.write(csv_buf.getvalue())
    with open(ut_dir / "baseline.json", "w", encoding="utf-8", newline="") as f:
        f.write(json_tekst)
    return baseline, len(train), len(test)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kilde", type=Path, default=REPO_ROT / STANDARD_KILDE,
                        help="pipeline-CSV (standard: %(default)s)")
    parser.add_argument("--ut-dir", type=Path, default=REPO_ROT / STANDARD_UT_DIR,
                        help="mappe for utdrag/anlop.csv og baseline.json (standard: %(default)s)")
    parser.add_argument("--laget", default=dt.date.today().isoformat(),
                        help="dato som lagres i baseline.json (standard: i dag)")
    args = parser.parse_args(argv)

    if not args.kilde.is_file():
        print(
            f"Fant ikke kilden {args.kilde}.\n"
            "Lag den med pipelinen (python pipeline/fetch_voyages.py, "
            "pipeline/fetch_ais.py og så pipeline/derive_arrivals.py), eller oppgi --kilde.",
            file=sys.stderr,
        )
        return 1

    baseline, n_train, n_test = lag_utdrag(args.kilde, args.ut_dir, args.laget)
    off = baseline["offset_minutter"]

    def fmt(v):
        return "–" if v is None else f"{v:.1f}"

    print(f"Skrev {args.ut_dir / 'utdrag' / 'anlop.csv'} og {args.ut_dir / 'baseline.json'}")
    print(f"{n_train} train / {n_test} test (test fra {baseline['test_fra_utc']})")
    print(f"Offset: Passasjer {fmt(off['Passasjer'])} min / Øvrige {fmt(off['Øvrige'])} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
