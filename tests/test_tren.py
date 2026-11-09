"""Treningen av 6 t- og 24 t-modellen (E2-S05, beslutning 11, PRD FR9/FR10).

Bare en syntetisk fixture i tmp_path. Ingen test trenger pipeline/data/, nett eller de committede artefaktene.
"""
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import math
import random
from pathlib import Path

import joblib
import numpy as np
import pytest

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("lag_features", REPO_ROT / "scripts" / "lag_features.py")
lf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lf)
_spec = importlib.util.spec_from_file_location("tren", REPO_ROT / "scripts" / "tren.py")
tren = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tren)

OFFSET = {"Passasjer": 44.75, "Øvrige": 64.2}
START = dt.datetime(2024, 1, 1, 6, 0)


def _fixture(n=100, seed=1):
    """n anløp (to horisonter hver): 60 % trening, 20 % validering, 20 % test; hvert femte er Passasjer.
    Hvert tiende Øvrige-anløp mangler tilstand eller fasit. Avviket avhenger av slakk og skipstype."""
    rng = random.Random(seed)
    anlop, features = [], []
    for i in range(n):
        vid = str(1000 + i)
        eta = START + dt.timedelta(hours=7 * i)
        del_ = "trening" if i < 0.6 * n else ("validering" if i < 0.8 * n else "test")
        gruppe = "Passasjer" if i % 5 == 0 else "Øvrige"
        skipstype = "Tanker" if i % 17 == 3 else "General Cargo Ship"
        fasit = i % 10 != 7
        km = rng.uniform(0, 400)
        fart = rng.uniform(0, 15)
        avvik = 3 * max(0.0, km / 1.852 / max(fart, 1.0) - 6) + (40 if skipstype == "Tanker" else 0) + rng.gauss(0, 10)
        ank = eta - dt.timedelta(minutes=OFFSET[gruppe]) + dt.timedelta(minutes=avvik)
        anlop.append({"voyageid": vid, "mmsino": str(257000000 + i % 7), "shipname": "X",
                      "ship_group": "Passasjer" if gruppe == "Passasjer" else "Last",
                      "eta_reported": eta.isoformat() + "+00:00",
                      "arrival_in_area_utc": ank.isoformat() if fasit else "",
                      "status_in_area": "ok" if fasit else "empty",
                      "split": "test" if del_ == "test" else "train"})
        for h in (6, 24):
            tilstand = i % 10 != 4
            rad = {k: "" for k in lf.KOLONNER}
            rad.update({"voyageid": vid, "horisont_timer": str(h),
                        "t_kutt_utc": (eta - dt.timedelta(hours=h)).isoformat() + "Z",
                        "gruppe": gruppe, "del": del_, "har_tilstand": str(int(tilstand)),
                        "skipstype": skipstype, "lengde_m": "90.50", "eta_time_sin": "0.5", "eta_time_cos": "0.5",
                        "eta_ukedag": str(eta.weekday()), "eta_maned_sin": "0.0", "eta_maned_cos": "1.0",
                        "avgangshavn": "Ågotnes" if i % 2 else "Mongstad", "avgatt_for_kutt": "1",
                        "timer_siden_avgang": "3.000", "fartoy_snittavvik_min": "10.00",
                        "fartoy_antall_tidligere": "2", "fartoy_snittavvik_min_modellvalg": "5.00",
                        "fartoy_antall_tidligere_modellvalg": "1"})
            if tilstand:
                mangler_fart = i % 9 == 2
                rad.update({"distanse_km": f"{km:.3f}", "fart_knop": "" if mangler_fart else f"{fart:.1f}",
                            "kurs_mot_havn": "" if mangler_fart else "0.9", "posisjon_alder_min": "1.0",
                            "lat": "60.5", "lon": "5.0", "i_sonen_ved_kutt": str(int(km <= 15)),
                            "slakk_timer": "" if mangler_fart else f"{h - km / 1.852 / max(fart, 1.0):.3f}"})
            features.append(rad)
    return anlop, features


def _skriv(mappe, anlop, features):
    mappe.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=lf.KOLONNER, lineterminator="\n")
    w.writeheader()
    w.writerows(features)
    tekst = buf.getvalue()
    (mappe / "features.csv").write_text(tekst, encoding="utf-8")
    (mappe / "features.json").write_text(json.dumps(
        {"utdrag_sha256": hashlib.sha256(tekst.encode("utf-8")).hexdigest()}), encoding="utf-8")
    with open(mappe / "anlop.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(anlop[0]))
        w.writeheader()
        w.writerows(anlop)
    (mappe / "baseline.json").write_text(json.dumps({"offset_minutter": OFFSET}), encoding="utf-8")


def _kjor(mappe, ut="modell"):
    return tren.main(["--features", str(mappe / "features.csv"), "--anlop", str(mappe / "anlop.csv"),
                      "--baseline", str(mappe / "baseline.json"), "--ut-dir", str(mappe / ut)])


def _artefakter(ut):
    return {p.name: joblib.load(p) for p in sorted(ut.glob("*.joblib"))}


def _valideringsrader(features, h):
    return [r for r in features if r["del"] == "validering" and r["horisont_timer"] == str(h)]


def _samme(features, ut_a, ut_b):
    assert (ut_a / "modellvalg.json").read_bytes() == (ut_b / "modellvalg.json").read_bytes()
    a, b = _artefakter(ut_a), _artefakter(ut_b)
    assert sorted(a) == sorted(b) == ["modell_24t.joblib", "modell_24t_uten_f13_f14.joblib",
                                      "modell_6t.joblib", "modell_6t_uten_f13_f14.joblib"]
    for navn in a:
        rr = _valideringsrader(features, a[navn]["horisont"])
        assert np.array_equal(tren.prediker(a[navn], rr), tren.prediker(b[navn], rr)), navn
        assert a[navn]["trent_paa"] == b[navn]["trent_paa"]


@pytest.fixture(scope="module")
def kjort(tmp_path_factory):
    mappe = tmp_path_factory.mktemp("tren")
    anlop, features = _fixture()
    _skriv(mappe, anlop, features)
    assert _kjor(mappe) == 0
    return mappe, anlop, features


def _forventet_antall(anlop, features, h):
    a = {r["voyageid"]: r for r in anlop}
    n = {"trening": 0, "validering": 0}
    for r in features:
        if (r["horisont_timer"] == str(h) and r["del"] in n and r["gruppe"] == "Øvrige"
                and r["har_tilstand"] == "1" and a[r["voyageid"]]["status_in_area"] == "ok"):
            n[r["del"]] += 1
    return n


def test_samme_prediksjon_to_ganger(kjort):
    mappe, _, features = kjort
    assert _kjor(mappe, "modell_igjen") == 0
    _samme(features, mappe / "modell", mappe / "modell_igjen")
    art = _artefakter(mappe / "modell")["modell_6t.joblib"]
    for k in ("modell", "features", "kategorier", "horisont", "variant", "sklearn_versjon", "trent_paa",
              "config", "features_sha256", "anlop_sha256"):
        assert k in art
    assert art["features_sha256"] == hashlib.sha256((mappe / "features.csv").read_bytes()).hexdigest()
    valg = json.loads((mappe / "modell" / "modellvalg.json").read_text(encoding="utf-8"))
    for h in ("6", "24"):
        v = valg["horisonter"][h]
        assert len(v["kandidater"]) == 8 and "referanse_avvik_0" in v
        assert v["valgt"] in v["innenfor_toleranse"]
        assert v["kandidater"][v["valgt"]]["config"] == v["valgt_config"]


def test_ingen_passasjer_i_trening(kjort, tmp_path):
    mappe, anlop, features = kjort
    for navn, art in _artefakter(mappe / "modell").items():
        assert art["trent_paa"] == _forventet_antall(anlop, features, art["horisont"]), navn
    # Passasjer-rader og Øvrige-rader uten tilstand eller fasit endres kraftig: ingenting endres.
    uten_fasit = {a["voyageid"] for a in anlop if a["status_in_area"] != "ok"}
    endret_f = [dict(r, distanse_km="999.000", skipstype="Tanker", fart_knop="0.1")
                if r["gruppe"] == "Passasjer" or r["har_tilstand"] != "1" or r["voyageid"] in uten_fasit else r
                for r in features]
    endret_a = [dict(a, arrival_in_area_utc="2030-01-01T00:00:00") if a["ship_group"] == "Passasjer" else a
                for a in anlop]
    _skriv(tmp_path, endret_a, endret_f)
    assert _kjor(tmp_path) == 0
    _samme(features, mappe / "modell", tmp_path / "modell")


def test_ablasjon_uten_f13_f14(kjort):
    mappe, _, _ = kjort
    art = _artefakter(mappe / "modell")
    for h in (6, 24):
        hoved, abl = art[f"modell_{h}t.joblib"], art[f"modell_{h}t_uten_f13_f14.joblib"]
        assert set(hoved["features"]) - set(abl["features"]) == {"avgangshavn", "avgatt_for_kutt", "timer_siden_avgang"}
        assert abl["modell"].n_features_in_ == len(abl["features"]) == len(hoved["features"]) - 3
        assert "avgangshavn" not in abl["kategorier"] and "skipstype" in abl["kategorier"]
        assert abl["config"] == hoved["config"] and abl["variant"] == "uten_f13_f14" and hoved["variant"] == "hoved"


def test_testperioden_paavirker_ikke(kjort, tmp_path):
    mappe, anlop, features = kjort
    rng = random.Random(7)
    test_ider = {r["voyageid"] for r in features if r["del"] == "test"}
    endret_f = [dict(r, distanse_km=f"{rng.uniform(0, 900):.3f}", skipstype=rng.choice(["Ny", "Tanker", ""]),
                     avgangshavn="Ny havn", fartoy_snittavvik_min="999.00", fartoy_snittavvik_min_modellvalg="-999.00",
                     har_tilstand="1") if r["del"] == "test" else r for r in features]
    endret_a = [dict(a, arrival_in_area_utc="2030-01-01T00:00:00", status_in_area="ok")
                if a["voyageid"] in test_ider else a for a in anlop]
    # 25 nye testrader av den sjeldne typen ville gjort «Tanker» til egen kategori om de ble talt.
    for i in range(25):
        endret_f.append(dict(endret_f[-1], voyageid=str(9000 + i), skipstype="Tanker"))
        endret_a.append(dict(endret_a[-1], voyageid=str(9000 + i)))
    _skriv(tmp_path, endret_a, endret_f)
    assert _kjor(tmp_path) == 0
    _samme(features, mappe / "modell", tmp_path / "modell")


def test_kategori_ukjent_blir_annet(kjort):
    mappe, _, features = kjort
    art = _artefakter(mappe / "modell")["modell_6t.joblib"]
    assert "Tanker" not in art["kategorier"]["skipstype"]          # under 20 rader i fitdataene
    assert "annet" in art["kategorier"]["skipstype"]
    rad = _valideringsrader(features, 6)[1]
    varianter = [dict(rad, skipstype=v) for v in ("Helt ny type", "", "annet", "Tanker")]
    X = tren.matrise(varianter, art["features"], art["kategorier"])
    j = art["features"].index("skipstype")
    assert set(X[:, j]) == {art["kategorier"]["skipstype"].index("annet")}
    p = tren.prediker(art, varianter)
    assert np.all(p == p[0])


def test_manglende_verdier(kjort):
    mappe, anlop, features = kjort
    assert any(r["fart_knop"] == "" and r["har_tilstand"] == "1" and r["del"] == "trening" and r["gruppe"] == "Øvrige"
               for r in features)
    for art in _artefakter(mappe / "modell").values():
        rad = dict(_valideringsrader(features, art["horisont"])[1], fart_knop="", kurs_mot_havn="", slakk_timer="",
                   avgatt_for_kutt="", timer_siden_avgang="", lengde_m="")
        X = tren.matrise([rad], art["features"], art["kategorier"])
        assert math.isnan(X[0, art["features"].index("fart_knop")])
        assert np.isfinite(tren.prediker(art, [rad])).all()


@pytest.mark.parametrize("feil", ["ukjent_voyageid", "sha"])
def test_inkonsistent_input_skriver_ingenting(tmp_path, feil):
    anlop, features = _fixture(n=30)
    if feil == "ukjent_voyageid":
        features[0] = dict(features[0], voyageid="424242")
    _skriv(tmp_path, anlop, features)
    if feil == "sha":
        (tmp_path / "features.json").write_text(json.dumps({"utdrag_sha256": "0" * 64}), encoding="utf-8")
    assert _kjor(tmp_path) == 2
    assert not (tmp_path / "modell").exists()
