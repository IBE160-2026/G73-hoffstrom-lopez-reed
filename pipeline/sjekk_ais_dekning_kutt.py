#!/usr/bin/env python3
"""Stikkprøve: finnes AIS-posisjoner ved kuttpunktene t_H = rapportert ETA - H?

Grunnlag for beslutning 09. Dagens cache (fetch_ais.py) starter hentevinduet ved
seilasens ETD, så den sier ingenting om hvor skipet var ved t_24 når ETD er senere
enn t_24. Dette skriptet spør Kystdatahuset direkte om vinduet [t_H - 3 t, t_H] for et
lite, tilfeldig (fast seed) utvalg av testperiodens Øvrige-anløp, og om det samme for
en kontrollgruppe uten AIS i det hele tatt (status_in_area = empty, beslutning 07).

Bevisst lite: ~90 kall med pause mellom hvert. Dette er IKKE E2-S02-hentingen.

To funn fra 2026-10-22 som skriptet tar hensyn til:
- APIet har flyttet til kystdatahuset.kystverket.no (gammel adresse gir 301, og
  urllib følger ikke 301 på POST).
- APIet returnerer posisjoner for vinduet forskjøvet +1 t (vinter) / +2 t (sommer)
  i forhold til start/end i forespørselen, mens tidsstemplene i svaret er UTC.
  Vi ber derfor om [t_H - 5 t, t_H] og filtrerer på tidsstempelet selv, så ingen
  posisjon etter t_H brukes.

    python3 pipeline/sjekk_ais_dekning_kutt.py --n 40 --n-empty 10
    python3 pipeline/sjekk_ais_dekning_kutt.py --oppfolging

--oppfolging leser stikkprøven og spør (1) for anløp uten posisjon ved t_24: hvor var
skipet sist sett i [t_24 - 24 t, t_24]? og (2) for empty-kontrollen: finnes det i dag
posisjoner i seilasens opprinnelige hentevindu fra fetch_ais.py?
"""
import argparse
import csv
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import fetch_ais  # noqa: E402
from fetch_ais import fetch_positions, to_kdh_time  # noqa: E402

fetch_ais.API_URL = "https://kystdatahuset.kystverket.no/ws/api/ais/positions/for-mmsis-time"

AVVIK = "pipeline/data/bergen_eta_avvik.csv"
SEILASER = "pipeline/data/voyages_bergen_2024-01-01_2026-03-15.csv"
UT = "pipeline/data/ais_dekning_kutt_stikkprove.json"
PORT_LAT, PORT_LON = 60.398, 5.321  # samme referansepunkt som derive_arrivals.py
VINDU_TIMER = 3
PAUSE_SEK = 1.0


def km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def hent_filtrert(mmsi, fra, til):
    """[fra, til] i UTC, korrigert for forskyvningen: be om 2 t ekstra før, filtrer selv."""
    svar = fetch_positions(mmsi, to_kdh_time(fra - timedelta(hours=2)), to_kdh_time(til))
    time.sleep(PAUSE_SEK)
    return [p for p in svar if fra <= datetime.fromisoformat(p[1]) <= til]


def oppfolging():
    stikk = json.load(open(UT, encoding="utf-8"))
    avvik = {r["voyageid"]: r for r in csv.DictReader(open(AVVIK, encoding="utf-8"))}
    seilas = {r["voyageid"]: r for r in csv.DictReader(open(SEILASER, encoding="utf-8"))}
    ut = []
    for x in stikk:
        r = avvik[x["voyageid"]]
        mmsi = int(r["mmsino"])
        eta = datetime.fromisoformat(r["eta_reported"]).replace(tzinfo=None)
        if x["gruppe"] == "ok" and x["horisont"] == 24 and not x["antall"]:
            kutt = eta - timedelta(hours=24)
            pos = hent_filtrert(mmsi, kutt - timedelta(hours=24), kutt)
            rad = {"voyageid": x["voyageid"], "sporsmal": "sist_sett_for_t24", "dep_locname": x["dep_locname"],
                   "antall": len(pos)}
            if pos:
                siste = max(pos, key=lambda p: p[1])
                rad.update(timer_for_kutt=round((kutt - datetime.fromisoformat(siste[1])).total_seconds() / 3600, 1),
                           km_til_bergen=round(km(siste[3], siste[2], PORT_LAT, PORT_LON), 1), sog=siste[5])
            ut.append(rad)
        elif x["gruppe"] == "empty":
            fra, til = fetch_ais.compute_window(seilas[x["voyageid"]])
            pos = hent_filtrert(mmsi, fra, til)
            naer = [p for p in pos if km(p[3], p[2], PORT_LAT, PORT_LON) <= 15.0]
            ut.append({"voyageid": x["voyageid"], "sporsmal": "empty_opprinnelig_vindu",
                       "antall": len(pos), "innenfor_15_km": len(naer)})
        else:
            continue
        print(json.dumps(ut[-1], ensure_ascii=False), flush=True)
    with open(UT.replace(".json", "_oppfolging.json"), "w", encoding="utf-8") as f:
        json.dump(ut, f, ensure_ascii=False, indent=1)


def main():
    if "--oppfolging" in sys.argv:
        return oppfolging()
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--n-empty", type=int, default=10)
    ap.add_argument("--seed", type=int, default=9)
    args = ap.parse_args()

    rader = list(csv.DictReader(open(AVVIK, encoding="utf-8")))
    seilas = {r["voyageid"]: r for r in csv.DictReader(open(SEILASER, encoding="utf-8"))}
    rader.sort(key=lambda r: r["eta_reported"])
    test = [r for r in rader[int(len(rader) * 0.8):] if r["ship_group"] != "Passasjer"]
    rng = random.Random(args.seed)
    utvalg = rng.sample([r for r in test if r["status_in_area"] == "ok"], args.n)
    kontroll = rng.sample([r for r in test if r["status_in_area"] == "empty"], args.n_empty)

    resultat = []
    for gruppe, rs, horisonter in (("ok", utvalg, (24, 6)), ("empty", kontroll, (24,))):
        for r in rs:
            eta = datetime.fromisoformat(r["eta_reported"]).replace(tzinfo=None)
            etd_raw = seilas[r["voyageid"]]["etd"]
            for h in horisonter:
                kutt = eta - timedelta(hours=h)
                svar = fetch_positions(int(r["mmsino"]), to_kdh_time(kutt - timedelta(hours=VINDU_TIMER + 2)),
                                       to_kdh_time(kutt))
                fra = kutt - timedelta(hours=VINDU_TIMER)
                pos = [p for p in svar if fra <= datetime.fromisoformat(p[1]) <= kutt]
                time.sleep(PAUSE_SEK)
                rad = {"voyageid": r["voyageid"], "gruppe": gruppe, "horisont": h,
                       "ship_group": r["ship_group"], "dep_locname": seilas[r["voyageid"]]["dep_locname"],
                       "etd_for_kutt": bool(etd_raw) and datetime.fromisoformat(etd_raw).replace(tzinfo=None) <= kutt,
                       "antall": len(pos), "etter_kutt_i_svar": len(svar) - len([p for p in svar if datetime.fromisoformat(p[1]) <= kutt])}
                if pos:
                    siste = max(pos, key=lambda p: p[1])
                    rad.update(siste_utc=siste[1], km_til_bergen=round(km(siste[3], siste[2], PORT_LAT, PORT_LON), 1),
                               lat=siste[3], lon=siste[2], sog=siste[5])
                resultat.append(rad)
                print(json.dumps(rad, ensure_ascii=False), flush=True)

    with open(UT, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=1)

    for gruppe in ("ok", "empty"):
        for h in (24, 6):
            rs = [x for x in resultat if x["gruppe"] == gruppe and x["horisont"] == h]
            if not rs:
                continue
            med = [x for x in rs if x["antall"]]
            avst = sorted(x["km_til_bergen"] for x in med)
            print(f"{gruppe:5} H={h:2}: {len(med)}/{len(rs)} med posisjon i [t_H-3t, t_H]"
                  + (f", median avstand {avst[len(avst)//2]} km, maks {avst[-1]} km" if avst else ""))


if __name__ == "__main__":
    main()
