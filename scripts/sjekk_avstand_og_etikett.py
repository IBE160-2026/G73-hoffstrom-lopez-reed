"""To kontroller av datasettet etter full henting (E2-S04, beslutning 03 og 11). Endrer ingenting.

1. Lange avstander ved kuttet. Nødvendig fart er rett linje fra posisjonen ved t_kutt til havna,
   delt på H. Rader som trenger mer enn 25 kn, klassifiseres slik:
   - «sen > 120»: fasiten er mer enn 120 min etter kalibrert ETA (beholdes)
   - «i rute»: fasiten er ikke sen (undersøkes)
   - «umulig»: mer enn 45 kn, eller soneinngang før t_kutt med mer enn 15 km igjen (undersøkes)
   - «uten fasit»: beholdes og telles
   Grunnraten for «sen» blant radene som trenger 25 kn eller mindre, skrives ut til sammenligning.
2. Etikettsjekk (beslutning 03): anløp med fasit der soneinngangen er mer enn 24 t før rapportert
   ETA, fordelt på skipstype og sammenlignet med skipstypens andel av alle anløp med fasit.

Leser bare committede filer: data/utdrag/anlop.csv, data/utdrag/features.csv og data/baseline.json.
Ankomstfeltene leses her med vilje: dette er en kontroll av etiketten, ikke en del av modellen.

    .venv/bin/python scripts/sjekk_avstand_og_etikett.py
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

KM_PER_NM = 1.852
REALISTISK_KN = 25.0
UMULIG_KN = 45.0
SEN_MIN = 120.0
SONE_KM = 15.0
TIDLIG = timedelta(hours=24)
OFFSHORE = {"Anchor Handling Tug Supply", "Platform Supply Ship", "Offshore Tug/Supply Ship",
            "Offshore Support Vessel"}


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def gruppe(a):
    return "Passasjer" if a["ship_group"] == "Passasjer" else "Øvrige"


def har_fasit(a):
    return a["status_in_area"] == "ok" and bool(a["arrival_in_area_utc"])


def lange_avstander(anlop, feat, offset):
    klasser, grunn, tilfeller = defaultdict(Counter), defaultdict(lambda: [0, 0]), []
    for r in feat:
        if r["har_tilstand"] != "1":
            continue
        a = anlop[r["voyageid"]]
        h, d = int(r["horisont_timer"]), float(r["distanse_km"])
        kn = d / KM_PER_NM / h
        avvik = None
        if har_fasit(a):
            ank = utc(a["arrival_in_area_utc"])
            avvik = (ank - (utc(a["eta_reported"]) - timedelta(minutes=offset[gruppe(a)]))).total_seconds() / 60
        if kn <= REALISTISK_KN:
            if avvik is not None:
                grunn[(h, gruppe(a))][0] += 1
                grunn[(h, gruppe(a))][1] += avvik > SEN_MIN
            continue
        if avvik is None:
            klasse = "uten fasit"
        elif kn > UMULIG_KN or (utc(a["arrival_in_area_utc"]) < utc(r["t_kutt_utc"]) and d > SONE_KM):
            klasse = "umulig"
        else:
            klasse = "sen > 120" if avvik > SEN_MIN else "i rute"
        k = klasser[(h, gruppe(a))]
        k["> 25 kn"] += 1
        k["> 45 kn"] += kn > UMULIG_KN
        k["med fasit"] += avvik is not None
        k[klasse] += 1
        tilfeller.append({"H": h, "gruppe": gruppe(a), "split": a["split"], "voyageid": r["voyageid"],
                          "navn": a["shipname"], "skipstype": r["skipstype"], "km": round(d),
                          "kn": round(kn, 1), "klasse": klasse,
                          "avvik_min": None if avvik is None else round(avvik)})
    return klasser, grunn, tilfeller


def etikettsjekk(anlop, skipstype):
    med = [a for a in anlop.values() if har_fasit(a)]
    tidlig = [a for a in med if utc(a["arrival_in_area_utc"]) < utc(a["eta_reported"]) - TIDLIG]
    return med, tidlig


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anlop", type=Path, default=Path("data/utdrag/anlop.csv"))
    ap.add_argument("--features", type=Path, default=Path("data/utdrag/features.csv"))
    ap.add_argument("--baseline", type=Path, default=Path("data/baseline.json"))
    args = ap.parse_args(argv)

    with open(args.anlop, newline="", encoding="utf-8") as f:
        anlop = {r["voyageid"]: r for r in csv.DictReader(f)}
    with open(args.features, newline="", encoding="utf-8") as f:
        feat = list(csv.DictReader(f))
    with open(args.baseline, encoding="utf-8") as f:
        offset = json.load(f)["offset_minutter"]
    skipstype = {r["voyageid"]: r["skipstype"] for r in feat}

    print("1. Lange avstander ved kuttet (rett linje til havna / H)")
    klasser, grunn, tilfeller = lange_avstander(anlop, feat, offset)
    kol = ["> 25 kn", "> 45 kn", "med fasit", "sen > 120", "i rute", "umulig", "uten fasit"]
    print("| H | Gruppe | " + " | ".join(kol) + " |")
    for h in (6, 24):
        for g in ("Øvrige", "Passasjer"):
            k = klasser.get((h, g), Counter())
            print(f"| {h} | {g} | " + " | ".join(str(k[c]) for c in kol) + " |")
    print("\nGrunnrate, sen > 120 min blant rader som trenger ≤ 25 kn, med fasit:")
    for h in (6, 24):
        for g in ("Øvrige", "Passasjer"):
            n, s = grunn[(h, g)]
            print(f"  H = {h:<2} {g:<10} {s}/{n} = {100 * s / n:.1f} %" if n else f"  H = {h} {g}: ingen")
    print("\nAlle rader over 25 kn:")
    for t in tilfeller:
        print("  " + ", ".join(f"{k}={v}" for k, v in t.items()))

    print("\n2. Etikettsjekk: soneinngang mer enn 24 t før rapportert ETA")
    med, tidlig = etikettsjekk(anlop, skipstype)
    print(f"{len(tidlig)} av {len(med)} anløp med fasit ({100 * len(tidlig) / len(med):.2f} %). "
          f"Per gruppe: {dict(Counter(gruppe(a) for a in tidlig))}. Per split: {dict(Counter(a['split'] for a in tidlig))}.")
    alle, ti = Counter(skipstype[a["voyageid"]] for a in med), Counter(skipstype[a["voyageid"]] for a in tidlig)
    print("| Skipstype | Tidlige | Andel av de tidlige | Andel av typen | Typens andel av alle med fasit |")
    for t, n in ti.most_common():
        print(f"| {t} | {n} | {100 * n / len(tidlig):.1f} % | {100 * n / alle[t]:.1f} % | {100 * alle[t] / len(med):.1f} % |")
    o, oa = sum(ti[t] for t in OFFSHORE), sum(alle[t] for t in OFFSHORE)
    print(f"Offshore og forsyning: {o} av {len(tidlig)} ({100 * o / len(tidlig):.1f} %), "
          f"mot {100 * oa / len(med):.1f} % av alle med fasit.")
    timer = sorted((utc(a["eta_reported"]) - utc(a["arrival_in_area_utc"])).total_seconds() / 3600 for a in tidlig)
    if timer:
        print(f"Timer før ETA: median {timer[len(timer) // 2]:.0f}, maks {timer[-1]:.0f}.")
    print("I testdelen:")
    for a in sorted(tidlig, key=lambda a: a["voyageid"]):
        if a["split"] == "test":
            t = (utc(a["eta_reported"]) - utc(a["arrival_in_area_utc"])).total_seconds() / 3600
            print(f"  {a['voyageid']} {a['shipname']} ({skipstype[a['voyageid']]}), {t:.0f} t før ETA")


if __name__ == "__main__":
    main()
