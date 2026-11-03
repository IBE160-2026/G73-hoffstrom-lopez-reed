#!/usr/bin/env python3
"""Målrettet AIS-henting ved kuttpunktene t_H = rapportert ETA − H, H ∈ {6, 24} (E2-S02).

Grunnlag: beslutning 08 (kuttet ligger på rapportert ETA, aldri på faktisk ankomst) og
beslutning 09 (tilbakeblikk [t_H − 24 t, t_H], ny API-adresse, og API-et forskyver
vinduet +1/+2 t og kan kutte korte svar ved midnatt).

Slik virker skriptet:
- Det leser bare voyageid, mmsino, ship_group, eta_reported og split fra
  data/utdrag/anlop.csv. Ankomstfeltene leses aldri, og vinduet regnes bare fra
  rapportert ETA.
- Det gjør ett kall per seilas for [ETA − 72 t, ETA + 18 t]. Det dekker begge
  tilbakeblikkene med minst én dags margin og er alltid lengre enn ett døgn.
- Det har et hardt tak: punkter etter ETA − 6 t (det seneste kuttpunktet) kastes før
  noe skrives, uansett hva API-et returnerer (Felipe, 03.11.2026). Deretter filtreres
  svaret på sine egne UTC-tidsstempler til [t_H − 24 t, t_H] per horisont.
- Det cacher én fil per seilas i pipeline/data/ais_kutt_cache/ og skriver den atomisk,
  så et avbrudd ikke etterlater halve filer. Cachede seilaser hentes aldri på nytt.
  Feilede seilaser caches ikke og prøves igjen ved neste kjøring. Tomme svar caches
  med status «tom», og --prov-tomme henter dem på nytt.
- Det tar 1 s pause etter hvert kall og prøver opptil 3 ganger på nytt (5/15/45 s)
  ved feil. Feiler 10 seilaser på rad, stopper det.
- Hvert kall logges i pipeline/data/ais_kutt_logg.csv. Dekningen per horisont, gruppe
  og splitt skrives til pipeline/data/ais_kutt_dekning.csv etter hver kjøring.

Det låste datasettet (data/, pipeline/data/ais_cache/, bergen_eta_avvik.csv) røres ikke.

    caffeinate -i python3 pipeline/fetch_ais_kutt.py --utvalg 50 --seed 2   # pilot
    caffeinate -i python3 pipeline/fetch_ais_kutt.py                        # resten
    python3 pipeline/fetch_ais_kutt.py --bare-dekning                       # bare tabellen

Ctrl-C eller `kill` (SIGTERM) stopper skriptet rent. Kjør samme kommando igjen for å
fortsette der det slapp.
"""
import argparse
import csv
import http.client
import json
import os
import random
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API_URL = "https://kystdatahuset.kystverket.no/ws/api/ais/positions/for-mmsis-time"
KILDE = "data/utdrag/anlop.csv"
CACHE_DIR = "pipeline/data/ais_kutt_cache"
LOGG = "pipeline/data/ais_kutt_logg.csv"
DEKNING = "pipeline/data/ais_kutt_dekning.csv"

FELTER = ("voyageid", "mmsino", "ship_group", "eta_reported", "split")
HORISONTER = (6, 24)
TILBAKEBLIKK = timedelta(hours=24)
FORESPORSEL_FOR = timedelta(hours=72)    # t_24 − 24 t − 24 t margin
FORESPORSEL_ETTER = timedelta(hours=18)  # t_6 + 24 t margin
PAUSE_SEK = 1.0
BACKOFF_SEK = (5, 15, 45)
MAKS_FEIL_PA_RAD = 10

LOGG_KOLONNER = ["tid_utc", "voyageid", "mmsino", "eta_reported", "foresporsel_start",
                 "foresporsel_slutt", "antall_i_svar", "kastet_etter_tak", "antall_6t",
                 "antall_24t", "sekunder", "status"]


DEKNING_KOLONNER = ["horisont_timer", "gruppe", "split", "n", "hentet", "med_posisjon_24t",
                    "andel_med_posisjon_24t", "med_posisjon_1t", "andel_med_posisjon_1t"]


class HenteFeil(Exception):
    def __init__(self, melding, varig=False):
        super().__init__(melding)
        self.varig = varig


def naive_utc(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


_TID = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:?\d\d)?$")


def tidsstempel(punkt):
    """UTC-tidsstempelet i et API-punkt (kolonne 1), naivt. None hvis det ikke kan leses."""
    try:
        m = _TID.match(str(punkt[1]).strip())
        if not m:
            return None
        dt = datetime.fromisoformat(m.group(1))
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    if m.group(2):
        dt += timedelta(seconds=float(m.group(2)))
    off = m.group(3)
    if off and off != "Z":
        sign = 1 if off[0] == "+" else -1
        dt -= sign * timedelta(hours=int(off[1:3]), minutes=int(off[-2:]))
    return dt


def les_anlop(sti):
    """Bare FELTER beholdes. Ankomstfeltene finnes i fila, men leses aldri videre."""
    with open(sti, newline="", encoding="utf-8") as f:
        return [{k: r[k] for k in FELTER} for r in csv.DictReader(f)]


def gruppe(rad):
    return "Passasjer" if rad["ship_group"] == "Passasjer" else "Øvrige"


def kuttpunkter(eta):
    return {h: eta - timedelta(hours=h) for h in HORISONTER}


def foresporselsvindu(eta):
    return eta - FORESPORSEL_FOR, eta + FORESPORSEL_ETTER


def tak(eta):
    """Seneste tillatte tidsstempel i cachen: det seneste kuttpunktet, ETA − 6 t."""
    return eta - timedelta(hours=min(HORISONTER))


def kutt_ved_tak(svar, eta):
    """Hardt tak: kast alt etter ETA − 6 t og alt uten lesbart tidsstempel."""
    grense = tak(eta)
    return [p for p in svar if (t := tidsstempel(p)) is not None and t <= grense]


def filtrer_til_vindu(svar, fra, til):
    """Behold bare posisjoner med tidsstempel i [fra, til] (UTC, naive).

    Kystdatahuset returnerer et vindu forskjøvet +1/+2 t i forhold til forespørselen
    (beslutning 09, funn B), så svaret kan inneholde punkter etter kuttpunktet.
    """
    return [p for p in svar if (t := tidsstempel(p)) is not None and fra <= t <= til]


def bygg_cache(rad, svar):
    eta = naive_utc(rad["eta_reported"])
    uleselige = sum(1 for p in svar if tidsstempel(p) is None)
    if svar and uleselige == len(svar):
        # Nytt tidsformat fra API-et? Da skal seilasen ikke caches som «ok» uten punkter.
        raise HenteFeil(f"ingen lesbare tidsstempler i {len(svar)} punkter, f.eks. {svar[0][:2]!r}")
    under_tak = kutt_ved_tak(svar, eta)
    horisonter = {}
    for h, t_kutt in kuttpunkter(eta).items():
        pos = filtrer_til_vindu(under_tak, t_kutt - TILBAKEBLIKK, t_kutt)
        horisonter[str(h)] = {"t_kutt_utc": t_kutt.isoformat(),
                              "fra_utc": (t_kutt - TILBAKEBLIKK).isoformat(),
                              "posisjoner": pos}
    grense = tak(eta)
    if any(tidsstempel(p) > grense for v in horisonter.values() for p in v["posisjoner"]):
        raise RuntimeError("punkt etter ETA − 6 t på vei til cachen")  # skal aldri skje
    start, slutt = foresporselsvindu(eta)
    return {"voyageid": rad["voyageid"], "mmsino": rad["mmsino"],
            "eta_reported": rad["eta_reported"],
            "foresporsel": [start.isoformat(), slutt.isoformat()],
            "hentet_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
            "status": "ok" if svar else "tom",
            "antall_i_svar": len(svar), "uleselige": uleselige,
            "kastet_etter_tak": len(svar) - uleselige - len(under_tak),
            "horisonter": horisonter}


def hent_posisjoner(mmsi, start, slutt):
    body = json.dumps({"mmsiIds": [int(mmsi)], "start": start.strftime("%Y%m%d%H%M"),
                       "end": slutt.strftime("%Y%m%d%H%M")}).encode("utf-8")
    siste = None
    for forsok in range(len(BACKOFF_SEK) + 1):
        if forsok:
            time.sleep(BACKOFF_SEK[forsok - 1])
        req = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.load(resp)
            if not isinstance(payload, dict):
                raise HenteFeil(f"uventet svar: {type(payload).__name__}")
            if not payload.get("success"):
                msg = str(payload.get("msg"))
                if "does not exist" in msg:
                    # Dagstabellen mangler hos Kystdatahuset (sett i piloten 03.11.2026: 42P01,
                    # «relation "ais202410.ais_20241028" does not exist»). Nytt forsøk hjelper ikke.
                    raise HenteFeil(f"mangler hos API-et: {msg.splitlines()[0]}", varig=True)
                raise HenteFeil(f"success=false: {msg}")
            data = payload.get("data") or []
            if not isinstance(data, list):
                raise HenteFeil(f"uventet data: {type(data).__name__}")
            return data
        except urllib.error.HTTPError as exc:
            siste = exc
            if 400 <= exc.code < 500 and exc.code != 429:
                break  # feil i forespørselen, nytt forsøk hjelper ikke
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError, HenteFeil) as exc:
            siste = exc
            if getattr(exc, "varig", False):
                raise
    raise HenteFeil(f"{type(siste).__name__}: {siste}")


def skriv_atomisk(sti, obj):
    tmp = sti + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, sti)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def cache_sti(cache_dir, voyageid):
    return os.path.join(cache_dir, f"{voyageid}.json")


def les_cache(cache_dir, voyageid):
    try:
        with open(cache_sti(cache_dir, voyageid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def behandle(rad, cache_dir, hent=hent_posisjoner):
    """Hent, filtrer og cache én seilas. Returnerer en loggrad. Kaster HenteFeil."""
    eta = naive_utc(rad["eta_reported"])
    start, slutt = foresporselsvindu(eta)
    t0 = time.time()
    svar = hent(rad["mmsino"], start, slutt)
    innhold = bygg_cache(rad, svar)
    skriv_atomisk(cache_sti(cache_dir, rad["voyageid"]), innhold)
    return [innhold["hentet_utc"], rad["voyageid"], rad["mmsino"], rad["eta_reported"],
            start.isoformat(), slutt.isoformat(), len(svar), innhold["kastet_etter_tak"],
            len(innhold["horisonter"]["6"]["posisjoner"]),
            len(innhold["horisonter"]["24"]["posisjoner"]),
            round(time.time() - t0, 2), innhold["status"]]


def dekning(anlop, cache_dir):
    tall = {}
    for rad in anlop:
        c = les_cache(cache_dir, rad["voyageid"])
        for h in HORISONTER:
            n = tall.setdefault((h, gruppe(rad), rad["split"]), [0, 0, 0, 0])
            n[0] += 1
            if c is None:
                continue
            n[1] += 1
            v = c["horisonter"][str(h)]
            if v["posisjoner"]:
                n[2] += 1
                siste = max(tidsstempel(p) for p in v["posisjoner"])
                if naive_utc(v["t_kutt_utc"]) - siste <= timedelta(hours=1):
                    n[3] += 1
    rader = []
    for (h, g, s) in sorted(tall, key=lambda k: (k[0], k[1] != "Øvrige", k[2] != "test")):
        n, hentet, med, med1 = tall[(h, g, s)]
        andel = lambda x: f"{x / hentet:.3f}" if hentet else ""  # noqa: E731
        rader.append({"horisont_timer": h, "gruppe": g, "split": s, "n": n, "hentet": hentet,
                      "med_posisjon_24t": med, "andel_med_posisjon_24t": andel(med),
                      "med_posisjon_1t": med1, "andel_med_posisjon_1t": andel(med1)})
    return rader


def skriv_dekning(rader, sti):
    tmp = sti + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DEKNING_KOLONNER, lineterminator="\n")
        w.writeheader()
        w.writerows(rader)
    os.replace(tmp, sti)


def _sigterm(signum, frame):
    raise KeyboardInterrupt


def main(argv=None, hent=hent_posisjoner):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kilde", default=KILDE)
    ap.add_argument("--cache-dir", default=CACHE_DIR)
    ap.add_argument("--logg", default=LOGG)
    ap.add_argument("--dekning", default=DEKNING)
    ap.add_argument("--utvalg", type=int, default=None, help="tilfeldig pilot på N ikke-cachede seilaser")
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--prov-tomme", action="store_true", help="hent seilaser med status «tom» på nytt")
    ap.add_argument("--pause", type=float, default=PAUSE_SEK)
    ap.add_argument("--bare-dekning", action="store_true")
    args = ap.parse_args(argv)
    signal.signal(signal.SIGTERM, _sigterm)

    anlop = les_anlop(args.kilde)
    os.makedirs(args.cache_dir, exist_ok=True)

    def trengs(rad):
        c = les_cache(args.cache_dir, rad["voyageid"])
        return c is None or (args.prov_tomme and c.get("status") == "tom")

    ko = [] if args.bare_dekning else [r for r in anlop if trengs(r)]
    if args.utvalg is not None:
        ko = random.Random(args.seed).sample(ko, min(args.utvalg, len(ko)))
    print(f"{len(anlop)} anløp, {len(ko)} skal hentes nå.", file=sys.stderr, flush=True)

    ny_logg = not os.path.exists(args.logg)
    loggf = open(args.logg, "a", newline="", encoding="utf-8")
    logg = csv.writer(loggf)
    if ny_logg:
        logg.writerow(LOGG_KOLONNER)

    ok = tom = feil = pa_rad = 0
    t0 = time.time()
    avbrutt = stoppet = False
    try:
        for i, rad in enumerate(ko, 1):
            try:
                loggrad = behandle(rad, args.cache_dir, hent)
                pa_rad = 0
                ok += loggrad[-1] == "ok"
                tom += loggrad[-1] == "tom"
            except HenteFeil as exc:
                feil += 1
                pa_rad += 1
                eta = naive_utc(rad["eta_reported"])
                s, e = foresporselsvindu(eta)
                loggrad = [datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
                           rad["voyageid"], rad["mmsino"], rad["eta_reported"], s.isoformat(),
                           e.isoformat(), 0, 0, 0, 0, "", f"feil: {exc}"]
                print(f"  {rad['voyageid']} FEIL: {exc}", file=sys.stderr, flush=True)
            logg.writerow(loggrad)
            loggf.flush()
            if i % 25 == 0 or i == len(ko):
                gatt = time.time() - t0
                rest = (len(ko) - i) * gatt / i
                print(f"  [{i}/{len(ko)}] ok={ok} tom={tom} feil={feil} "
                      f"{gatt / 60:.1f} min brukt, ca. {rest / 3600:.1f} t ({rest / 60:.0f} min) igjen",
                      file=sys.stderr, flush=True)
            if pa_rad >= MAKS_FEIL_PA_RAD:
                stoppet = True
                print(f"\nStopper: {MAKS_FEIL_PA_RAD} seilaser på rad feilet. API-et er trolig nede. "
                      "Kjør samme kommando igjen senere for å fortsette.", file=sys.stderr)
                break
            time.sleep(args.pause)
    except KeyboardInterrupt:
        avbrutt = True
        print("\nAvbrutt. Ferdige seilaser ligger i cachen. Kjør samme kommando for å fortsette.",
              file=sys.stderr)
    finally:
        loggf.close()

    rader = dekning(anlop, args.cache_dir)
    skriv_dekning(rader, args.dekning)

    gatt = time.time() - t0
    filer = [f for f in os.listdir(args.cache_dir) if f.endswith(".json")]
    byte = sum(os.path.getsize(os.path.join(args.cache_dir, f)) for f in filer)
    hentet = ok + tom
    gjenstar = sum(1 for r in anlop if les_cache(args.cache_dir, r["voyageid"]) is None)
    print(f"\nFerdig: {hentet} hentet (ok={ok}, tom={tom}), {feil} feil, {gatt / 60:.1f} min.",
          file=sys.stderr)
    if hentet:
        per = gatt / (hentet + feil)
        print(f"  {per:.2f} s per seilas inkl. pause, {byte / len(filer) / 1e3:.0f} kB per seilas i cachen.\n"
              f"  Cache nå: {byte / 1e6:.1f} MB i {len(filer)} filer. Gjenstår: {gjenstar} seilaser.\n"
              f"  Estimat for resten: ca. {gjenstar * per / 3600:.1f} t og "
              f"{gjenstar * byte / len(filer) / 1e6:.0f} MB "
              f"(totalt ca. {len(anlop) * byte / len(filer) / 1e6:.0f} MB).", file=sys.stderr)
    print(f"Dekning: {args.dekning}\nLogg: {args.logg}", file=sys.stderr)
    if avbrutt:
        return 130
    return 2 if stoppet else 0


if __name__ == "__main__":
    sys.exit(main())
