"""Featurene F1–F16 og valideringssplitten (E2-S04, beslutning 11, PRD FR9a).

Bare fixtures i minnet eller i tmp_path. Ingen test trenger pipeline/data/ eller nett.
"""
import copy
import csv
import importlib.util
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.prediksjon import features as F

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("lag_features", REPO_ROT / "scripts" / "lag_features.py")
lf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lf)

OFFSET = {"Passasjer": 44.75, "Øvrige": 64.2}
A, B = "257000001", "257000002"


def anlop(vid, eta, split, mmsi=A, ankomst_min=None, gruppe="Last", status="ok"):
    """ankomst_min: faktisk ankomst i minutter etter (ETA − offset), altså kalibrert avvik."""
    eta_dt = datetime.fromisoformat(eta)
    off = OFFSET["Passasjer" if gruppe == "Passasjer" else "Øvrige"]
    ank = "" if ankomst_min is None else (eta_dt - timedelta(minutes=off) + timedelta(minutes=ankomst_min)).isoformat()
    return {"voyageid": str(vid), "mmsino": mmsi, "shipname": "X", "ship_group": gruppe,
            "eta_reported": eta_dt.isoformat() + "+00:00", "arrival_in_area_utc": ank,
            "status_in_area": status if ank else "empty", "split": split}


def tilstand_for(anlop_rader, km="50.000", fart="12.0", kurs="180.0", status="ok"):
    rader = []
    for a in anlop_rader:
        eta = lf.naive_utc(a["eta_reported"])
        for h in (6, 24):
            ok = status == "ok"
            rader.append({"voyageid": a["voyageid"], "horisont_timer": str(h),
                          "t_kutt_utc": (eta - timedelta(hours=h)).isoformat() + "Z", "ais_status": status,
                          "lat": "60.800000" if ok else "", "lon": "5.300000" if ok else "",
                          "distanse_km": km if ok else "", "fart_knop": fart if ok else "",
                          "kurs_grader": kurs if ok else "", "posisjon_alder_min": "10.0" if ok else ""})
    return rader


def seilaser_for(anlop_rader, etd_timer_for_eta=30):
    return [{"voyageid": a["voyageid"], "ship_type": "General Cargo Ship", "length": "90.5",
             "etd": (lf.naive_utc(a["eta_reported"]) - timedelta(hours=etd_timer_for_eta)).isoformat() + "+00:00",
             "dep_locname": "Ågotnes"} for a in anlop_rader]


def bygg(anlop_rader, **kw):
    return lf.bygg(anlop_rader, tilstand_for(anlop_rader, **kw), seilaser_for(anlop_rader), OFFSET)


def hist(rader):
    """(voyageid, H) → (F15, F16)."""
    return {(r["voyageid"], r["horisont_timer"]): (r["fartoy_snittavvik_min"], r["fartoy_antall_tidligere"]) for r in rader}


def grunnsett():
    return [
        anlop(1, "2024-01-10T12:00:00", "train", ankomst_min=100),
        anlop(2, "2024-02-10T12:00:00", "train", ankomst_min=-20),
        anlop(3, "2024-03-10T12:00:00", "train", mmsi=B, ankomst_min=100),
        anlop(4, "2024-04-10T12:00:00", "train", ankomst_min=300),
        anlop(5, "2024-05-10T12:00:00", "train", ankomst_min=10),
        anlop(10, "2025-10-10T12:00:00", "test", ankomst_min=500),
        anlop(11, "2025-11-10T12:00:00", "test", ankomst_min=-300),
    ]


# ---------- F15–F16 ----------

def test_fartoyhistorikk_bare_fra_trening():
    """Endres avvik i testperioden og radens eget, eller legges testrader til, fjernes eller flyttes,
    er F15, F16 og snittet det trekkes mot, identiske for alle rader."""
    rader = grunnsett()
    fasit = hist(bygg(rader))

    endret = copy.deepcopy(rader)
    for a in endret:
        if a["split"] == "test":
            eta = lf.naive_utc(a["eta_reported"])
            a["arrival_in_area_utc"] = (eta + timedelta(hours=40)).isoformat()
    assert hist(bygg(endret)) == fasit

    flere = copy.deepcopy(rader) + [anlop(12, "2025-10-20T12:00:00", "test", ankomst_min=900),
                                    anlop(13, "2025-09-01T12:00:00", "test", mmsi=B, ankomst_min=-900)]
    h = hist(bygg(flere))
    assert {k: v for k, v in h.items() if k[0] not in ("12", "13")} == fasit

    flyttet = [a for a in copy.deepcopy(rader) if a["voyageid"] != "11"]
    flyttet.append(anlop(11, "2026-01-02T12:00:00", "test", ankomst_min=-300))
    h = hist(bygg(flyttet))
    assert {k: v for k, v in h.items() if k[0] != "11"} == {k: v for k, v in fasit.items() if k[0] != "11"}

    # Snittet det trekkes mot, regnes bare på treningsrader.
    def maal(rs):
        return [lf.bygg_historikk(rs, OFFSET).maal(lf.naive_utc(a["eta_reported"]), a["voyageid"]) for a in rader]
    assert maal(endret) == maal(rader) == maal(flere)


def test_endret_treningsrad_paavirker_bare_senere_rader():
    rader = grunnsett()
    fasit = hist(bygg(rader))
    endret = copy.deepcopy(rader)
    endret[1]["arrival_in_area_utc"] = (lf.naive_utc(endret[1]["arrival_in_area_utc"]) + timedelta(minutes=77)).isoformat()
    ny_ank = lf.naive_utc(endret[1]["arrival_in_area_utc"])
    h = hist(bygg(endret))
    for a in rader:
        for hh in (6, 24):
            t_kutt = lf.naive_utc(a["eta_reported"]) - timedelta(hours=hh)
            samme = h[(a["voyageid"], str(hh))] == fasit[(a["voyageid"], str(hh))]
            if t_kutt <= min(ny_ank, lf.naive_utc(rader[1]["arrival_in_area_utc"])):
                assert samme, (a["voyageid"], hh)
    assert any(h[k] != fasit[k] for k in h)


def test_historikk_uten_lekkasje():
    """Radens egen ankomst er aldri med, heller ikke når den ligger før radens eget kutt."""
    a = anlop(1, "2024-01-10T12:00:00", "train", ankomst_min=-2000)   # ankom ~33 t før kalibrert ETA
    t24 = lf.naive_utc(a["eta_reported"]) - timedelta(hours=24)
    assert lf.naive_utc(a["arrival_in_area_utc"]) < t24
    r = {x["horisont_timer"]: x for x in bygg([a])}
    assert (r["24"]["fartoy_snittavvik_min"], r["24"]["fartoy_antall_tidligere"]) == ("0.00", "0")


def test_uten_historikk_og_mmsi_0():
    rader = grunnsett() + [anlop(20, "2024-06-10T12:00:00", "train", mmsi="0", ankomst_min=999),
                           anlop(21, "2024-06-11T12:00:00", "train", mmsi="0", ankomst_min=50)]
    r = {(x["voyageid"], x["horisont_timer"]): x for x in bygg(rader)}
    forste = r[("1", "24")]
    assert (forste["fartoy_snittavvik_min"], forste["fartoy_antall_tidligere"]) == ("0.00", "0")
    null = r[("21", "6")]
    assert null["fartoy_antall_tidligere"] == "0"
    h = lf.bygg_historikk(rader, OFFSET)
    t = lf.naive_utc("2024-06-11T06:00:00")
    assert float(null["fartoy_snittavvik_min"]) == pytest.approx(h.maal(t, "21"), abs=0.01)
    # MMSI 0 bidrar heller ikke til snittet det trekkes mot.
    assert h.maal(t, "21") == pytest.approx((100 - 20 + 100 + 300 + 10) / 5)


def test_krymping_mot_snittet():
    rader = grunnsett()
    r = {(x["voyageid"], x["horisont_timer"]): x for x in bygg(rader)}
    x = r[("4", "24")]                                  # fartøy A har 1 og 2 før (snitt 40)
    maal = (100 - 20 + 100) / 3                         # 60: ulikt fartøyets snitt, så k synes
    assert x["fartoy_antall_tidligere"] == "2"
    assert float(x["fartoy_snittavvik_min"]) == pytest.approx((100 - 20 + 5 * maal) / 7, abs=0.01)


# ---------- Valideringssplitt ----------

def test_valideringssplitt_kronologisk():
    rader = [anlop(i, f"2024-01-{i:02d}T12:00:00", "train", ankomst_min=0) for i in (7, 3, 9, 1, 5, 2, 8, 4, 6, 10)]
    rader += [anlop(99, "2025-12-01T12:00:00", "test", ankomst_min=0)]
    d = F.valideringssplitt(rader)
    assert {v for v, x in d.items() if x == "validering"} == {"9", "10"}
    assert d["99"] == "test" and sum(x == "trening" for x in d.values()) == 8
    sju = F.valideringssplitt(rader[:7])                # 7 * 0.8 = 5.6 → 5 / 2, som E1-S02
    assert sorted(sju.values()).count("validering") == 2


# ---------- F1–F14 ----------

@pytest.mark.parametrize("fart, ventet", [
    (0.0, 6 - 50 / 1.852),          # under 1 kn regnes som 1 kn → klippes ikke (−21 t)
    (0.3, 6 - 50 / 1.852),
    (1.0, 6 - 50 / 1.852),
    (12.0, 6 - 50 / 1.852 / 12),
    (None, None),
])
def test_slakk_ved_lav_fart(fart, ventet):
    v = F.slakk_timer(50.0, fart, 6.0)
    assert (v is None) if ventet is None else v == pytest.approx(ventet)


def test_slakk_klipping_og_null_distanse():
    assert F.slakk_timer(500.0, 0.0, 24.0) == -48.0
    assert F.slakk_timer(0.0, 0.0, 6.0) == 6.0
    assert F.slakk_timer(1.0, 30.0, 6.0) <= 6.0
    # Fart 102,3 er allerede tom i tilstandsfila (E2-S03), så F7 blir tom.
    r = bygg([anlop(1, "2024-01-10T12:00:00", "train")], fart="")
    assert all(x["slakk_timer"] == "" and x["fart_knop"] == "" for x in r)


def test_kurs_ugyldig():
    assert F.kurs_mot_havn(60.8, 5.3, 360.0, 12.0, 50.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, None, 12.0, 50.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, 180.0, 0.5, 50.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, 180.0, None, 50.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, 180.0, 12.0, 0.0) is None
    # Rett sør fra 60,8 N mot Bergen (60,4 N, omtrent samme lengdegrad) gir nær 1, rett nord nær −1.
    assert F.kurs_mot_havn(60.8, 5.321, 180.0, 12.0, 44.0) == pytest.approx(1.0, abs=1e-3)
    assert F.kurs_mot_havn(60.8, 5.321, 0.0, 12.0, 44.0) == pytest.approx(-1.0, abs=1e-3)


def test_etd_etter_kutt_brukes_ikke():
    a = anlop(1, "2024-01-10T12:00:00", "train")
    t = tilstand_for([a])
    s1, s2 = seilaser_for([a], etd_timer_for_eta=3), seilaser_for([a], etd_timer_for_eta=1)   # begge etter t_6
    r1, r2 = lf.bygg([a], t, s1, OFFSET), lf.bygg([a], t, s2, OFFSET)
    assert r1 == r2
    assert {x["horisont_timer"]: (x["avgatt_for_kutt"], x["timer_siden_avgang"]) for x in r1} == {"6": ("0", ""), "24": ("0", "")}
    r3 = lf.bygg([a], t, seilaser_for([a], etd_timer_for_eta=30), OFFSET)
    assert {x["horisont_timer"]: (x["avgatt_for_kutt"], x["timer_siden_avgang"]) for x in r3} == {"6": ("1", "24.000"), "24": ("1", "6.000")}
    r4 = lf.bygg([a], t, [{**s1[0], "etd": ""}], OFFSET)
    assert all(x["avgatt_for_kutt"] == "" and x["timer_siden_avgang"] == "" for x in r4)


def test_kalender_oslo_sommertid():
    """Sommertid 2025 starter 30.03 kl. 01:00 UTC. ETA 00:30 UTC = 01:30 norsk, 01:30 UTC = 03:30 norsk."""
    for utc, lokal_time in (("2025-03-30T00:30:00", 1.5), ("2025-03-30T01:30:00", 3.5), ("2025-07-01T12:00:00", 14.0)):
        k = F.kalender(datetime.fromisoformat(utc))
        assert k["eta_time_sin"] == pytest.approx(math.sin(2 * math.pi * lokal_time / 24))
        assert k["eta_time_cos"] == pytest.approx(math.cos(2 * math.pi * lokal_time / 24))
    nyttar = F.kalender(datetime.fromisoformat("2025-12-31T23:30:00"))   # 00:30 1. januar norsk tid
    assert (nyttar["eta_maned_sin"], nyttar["eta_maned_cos"], nyttar["eta_ukedag"]) == (pytest.approx(0.0), pytest.approx(1.0), 3)


def test_grupper_sjeldne():
    kart = F.lag_kategorikart(["A"] * 20 + ["B"] * 19 + ["", None])
    assert kart == frozenset({"A"})
    assert [F.grupper_sjeldne(v, kart) for v in ("A", "B", "", None, "Ny")] == ["A", "annet", "annet", "annet", "annet"]


def test_f6_fra_posisjon():
    assert (F.i_sonen(15.0), F.i_sonen(15.001), F.i_sonen(None)) == (1, 0, None)
    a = anlop(1, "2024-01-10T12:00:00", "train", ankomst_min=0)
    b = anlop(1, "2024-01-10T12:00:00", "train", ankomst_min=-3000)     # «ankom» lenge før kuttet
    assert [x["i_sonen_ved_kutt"] for x in bygg([a], km="14.000")] == [x["i_sonen_ved_kutt"] for x in bygg([b], km="14.000")] == ["1", "1"]


def test_rad_uten_tilstand():
    r = bygg([anlop(1, "2024-01-10T12:00:00", "train")], status="ingen_posisjon")
    for x in r:
        assert x["har_tilstand"] == "0"
        assert all(x[k] == "" for k in ("distanse_km", "fart_knop", "kurs_mot_havn", "posisjon_alder_min",
                                        "lat", "lon", "i_sonen_ved_kutt", "slakk_timer"))
        assert x["skipstype"] == "General Cargo Ship" and x["eta_ukedag"] != ""


def test_inkonsistent_tilstand_stopper():
    a = anlop(1, "2024-01-10T12:00:00", "train")
    t = tilstand_for([a])
    t[0]["t_kutt_utc"] = "2024-01-10T07:00:00Z"
    with pytest.raises(lf.Inkonsistens):
        lf.bygg([a], t, seilaser_for([a]), OFFSET)
    with pytest.raises(lf.Inkonsistens):
        lf.bygg([a], t[1:], seilaser_for([a]), OFFSET)
    ekte = tilstand_for([a])
    with pytest.raises(lf.Inkonsistens):                                  # ekstra rad for ukjent seilas
        lf.bygg([a], ekte + [{**ekte[0], "voyageid": "999"}], seilaser_for([a]), OFFSET)
    with pytest.raises(lf.Inkonsistens):                                  # duplikat i tilstandsfila
        lf.bygg([a], ekte + [ekte[0]], seilaser_for([a]), OFFSET)
    with pytest.raises(lf.Inkonsistens):                                  # duplikat i seilasfila
        lf.bygg([a], ekte, seilaser_for([a]) * 2, OFFSET)
    with pytest.raises(lf.Inkonsistens):                                  # offset mangler
        lf.bygg([a], ekte, seilaser_for([a]), {"Passasjer": 44.75, "Øvrige": None})


# ---------- Hele scriptet ----------

def _skriv(sti, rader):
    with open(sti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rader[0]))
        w.writeheader()
        w.writerows(rader)


def test_deterministisk_og_uten_ra_etd(tmp_path):
    rader = grunnsett()
    _skriv(tmp_path / "anlop.csv", rader)
    _skriv(tmp_path / "tilstand.csv", tilstand_for(rader))
    _skriv(tmp_path / "seilaser.csv", seilaser_for(rader))
    (tmp_path / "baseline.json").write_text(json.dumps({"offset_minutter": OFFSET}), encoding="utf-8")
    argv = ["--anlop", str(tmp_path / "anlop.csv"), "--tilstand", str(tmp_path / "tilstand.csv"),
            "--seilaser", str(tmp_path / "seilaser.csv"), "--baseline", str(tmp_path / "baseline.json"),
            "--laget", "2026-11-04"]
    assert lf.main(argv + ["--ut-dir", str(tmp_path / "a")]) == 0
    assert lf.main(argv + ["--ut-dir", str(tmp_path / "b")]) == 0
    for navn in ("features.csv", "features.json"):
        assert (tmp_path / "a" / navn).read_bytes() == (tmp_path / "b" / navn).read_bytes()
    tekst = (tmp_path / "a" / "features.csv").read_text(encoding="utf-8")
    assert "etd" not in tekst.splitlines()[0] and "+00:00" not in tekst      # rå ETD skrives aldri ut
    assert tekst.splitlines()[0].split(",") == lf.KOLONNER
    meta = json.loads((tmp_path / "a" / "features.json").read_text(encoding="utf-8"))
    assert meta["rader"] == 14 and not any(v["sti"].startswith("/") for v in meta["kilder"].values())
    per_h = lambda n: {h: {"med_tilstand": n, "uten_tilstand": 0} for h in ("6", "24")}   # noqa: E731
    assert meta["antall"] == {"trening": per_h(4), "validering": per_h(1), "test": per_h(2)}
    assert meta["anlop_uten_seilasrad"] == 0 and set(meta["kode_sha256"]) == {"features.py", "lag_features.py"}
    import hashlib
    assert meta["utdrag_sha256"] == hashlib.sha256((tmp_path / "a" / "features.csv").read_bytes()).hexdigest()
    # Ingen ETD-verdi fra fixturen finnes i utdataene, uansett format.
    for r in seilaser_for(rader):
        etd = lf.naive_utc(r["etd"])
        for form in (etd.isoformat(), etd.isoformat() + "Z", etd.strftime("%Y-%m-%d %H:%M"), etd.strftime("%Y%m%d%H%M")):
            assert form not in tekst, form


def test_main_stopper_uten_aa_skrive(tmp_path):
    rader = grunnsett()
    t = tilstand_for(rader)
    t[0]["t_kutt_utc"] = "2000-01-01T00:00:00Z"
    _skriv(tmp_path / "anlop.csv", rader)
    _skriv(tmp_path / "tilstand.csv", t)
    _skriv(tmp_path / "seilaser.csv", seilaser_for(rader))
    (tmp_path / "baseline.json").write_text(json.dumps({"offset_minutter": OFFSET}), encoding="utf-8")
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "features.csv").write_text("gammel", encoding="utf-8")
    kode = lf.main(["--anlop", str(tmp_path / "anlop.csv"), "--tilstand", str(tmp_path / "tilstand.csv"),
                    "--seilaser", str(tmp_path / "seilaser.csv"), "--baseline", str(tmp_path / "baseline.json"),
                    "--ut-dir", str(ut), "--laget", "2026-11-04"])
    assert kode == 2
    assert sorted(p.name for p in ut.iterdir()) == ["features.csv"]
    assert (ut / "features.csv").read_text(encoding="utf-8") == "gammel"


def test_uten_seilasrad():
    a = anlop(1, "2024-01-10T12:00:00", "train")
    for x in lf.bygg([a], tilstand_for([a]), [], OFFSET):
        assert all(x[k] == "" for k in ("skipstype", "lengde_m", "avgangshavn", "avgatt_for_kutt", "timer_siden_avgang"))


def test_etd_plassholder_og_for_gammel():
    eta = datetime(2024, 12, 3, 13)
    assert F.gyldig_etd(datetime(1, 1, 1), eta) is None
    assert F.gyldig_etd(eta - timedelta(days=14, seconds=1), eta) is None
    assert F.gyldig_etd(eta - timedelta(days=14), eta) == eta - timedelta(days=14)
    a = anlop(1, "2024-12-03T13:00:00", "train")
    s = [{**seilaser_for([a])[0], "etd": "0001-01-01T00:00:00"}]
    for x in lf.bygg([a], tilstand_for([a]), s, OFFSET):
        assert (x["avgatt_for_kutt"], x["timer_siden_avgang"]) == ("", "")


def test_ugyldig_fart_og_nan():
    nan = float("nan")
    assert F.slakk_timer(50.0, 102.3, 6.0) is None and F.slakk_timer(50.0, nan, 6.0) is None
    assert F.slakk_timer(nan, 12.0, 6.0) is None and F.slakk_timer(50.0, -1.0, 6.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, 180.0, nan, 50.0) is None
    assert F.kurs_mot_havn(60.8, 5.3, 180.0, 102.3, 50.0) is None
    assert F.i_sonen(nan) is None


def test_egen_ankomst_endrer_ikke_egen_historikk():
    """Endres en treningsrads egen ankomst, er radens egne F15/F16 uendret (de bruker bare andre rader)."""
    rader = grunnsett()
    fasit = hist(bygg(rader))
    for i, a in enumerate(rader):
        if a["split"] != "train":
            continue
        endret = copy.deepcopy(rader)
        endret[i]["arrival_in_area_utc"] = (lf.naive_utc(a["eta_reported"]) - timedelta(hours=30)).isoformat()
        h = hist(bygg(endret))
        for hh in ("6", "24"):
            assert h[(a["voyageid"], hh)] == fasit[(a["voyageid"], hh)], (a["voyageid"], hh)


def _valideringssett():
    """10 treningsanløp for samme fartøy: 8 trening og 2 validering (siste 20 %), og 1 test."""
    rader = [anlop(i, f"2024-0{1 + i // 4}-{1 + (i % 4) * 7:02d}T12:00:00", "train", ankomst_min=10 * i) for i in range(10)]
    return rader + [anlop(50, "2025-10-01T12:00:00", "test", ankomst_min=0)]


def test_valideringshistorikk_frosset_ved_grensen():
    """Modellvalg-variantene er upåvirket av valideringsdelens ankomster. Den endelige varianten bruker dem."""
    rader = _valideringssett()
    d = F.valideringssplitt(rader)
    validering = [a["voyageid"] for a in rader if d[a["voyageid"]] == "validering"]
    assert len(validering) == 2
    mv = lambda rs: {(x["voyageid"], x["horisont_timer"]): (x["fartoy_snittavvik_min_modellvalg"],  # noqa: E731
                                                            x["fartoy_antall_tidligere_modellvalg"]) for x in bygg(rs)}
    fasit_mv, fasit_endelig = mv(rader), hist(bygg(rader))
    endret = copy.deepcopy(rader)
    for a in endret:
        if a["voyageid"] in validering:
            a["arrival_in_area_utc"] = (lf.naive_utc(a["eta_reported"]) - timedelta(hours=40)).isoformat()
    assert mv(endret) == fasit_mv
    assert hist(bygg(endret)) != fasit_endelig                       # den endelige bruker valideringsdelen
    # Den siste valideringsraden ser 8 treningsanløp i modellvalg, men 9 (også den første valideringsraden) i endelig.
    r = {(x["voyageid"], x["horisont_timer"]): x for x in bygg(rader)}
    siste = (validering[-1], "6")
    assert (r[siste]["fartoy_antall_tidligere_modellvalg"], r[siste]["fartoy_antall_tidligere"]) == ("8", "9")
    # Testraden: modellvalg ser 8, endelig ser alle 10.
    assert (r[("50", "6")]["fartoy_antall_tidligere_modellvalg"], r[("50", "6")]["fartoy_antall_tidligere"]) == ("8", "10")
