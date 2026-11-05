"""Tilstandsutdraget ved kuttpunktene (E2-S03, PRD FR9a, beslutning 08, 09 og 11).

Alle tester bygger en liten AIS-cache og en anlop.csv i tmp_path. Ingen trenger nett eller
pipeline/data/.
"""
import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("lag_tilstand", REPO_ROT / "scripts" / "lag_tilstand.py")
lt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lt)

ETA = datetime(2026, 2, 26, 12, 0)
T = {6: ETA - timedelta(hours=6), 24: ETA - timedelta(hours=24)}


MMSI = 257000000


def punkt(t, lat=60.40, lon=5.32, cog=90.0, sog=10.0, mmsi=MMSI):
    return [mmsi, t.isoformat() if isinstance(t, datetime) else t, lon, lat, cog, sog, 1, 10.0, 10, 50, 90, 0]


def cachefil(d, voyageid, pos6, pos24, status="ok", t_kutt=None):
    t_kutt = t_kutt or T
    c = {"voyageid": voyageid, "status": status, "horisonter": {
        str(h): {"t_kutt_utc": t_kutt[h].isoformat(), "fra_utc": (t_kutt[h] - timedelta(hours=24)).isoformat(),
                 "posisjoner": p} for h, p in ((6, pos6), (24, pos24))}}
    (d / f"{voyageid}.json").write_text(json.dumps(c), encoding="utf-8")


def anlop(d, rader, ankomst="2026-02-26T11:40:00", mmsi=None):
    sti = d / "anlop.csv"
    with open(sti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["voyageid", "mmsino", "shipname", "ship_group", "eta_reported",
                                          "arrival_in_area_utc", "status_in_area", "split"])
        w.writeheader()
        for v in rader:
            w.writerow({"voyageid": v, "mmsino": str((mmsi or {}).get(v, MMSI)), "shipname": "X", "ship_group": "Last",
                        "eta_reported": ETA.isoformat() + "+00:00", "arrival_in_area_utc": ankomst,
                        "status_in_area": "ok", "split": "test"})
    return sti


def kjør(tmp_path, cache, kilde, navn="ut"):
    ut = tmp_path / navn
    kode = lt.main(["--cache-dir", str(cache), "--anlop", str(kilde), "--ut-dir", str(ut), "--laget", "2026-11-04"])
    return kode, ut


def les(ut):
    with open(ut / "tilstand_ved_kutt.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def oppsett(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    p6 = [punkt(T[6] - timedelta(hours=3), lat=60.9), punkt(T[6] - timedelta(minutes=30), lat=60.5, lon=5.10, sog=8.2, cog=170.0)]
    p24 = [punkt(T[24] - timedelta(hours=5), lat=61.2, sog=0.1)]
    cachefil(cache, "100", p6, p24)
    return cache, p6, p24


def test_normal_rad(tmp_path):
    cache, _, _ = oppsett(tmp_path)
    kode, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100"]))
    assert kode == 0
    r6, r24 = les(ut)
    assert list(r6) == lt.KOLONNER and "allerede_ankommet" not in r6
    assert (r6["horisont_timer"], r6["t_kutt_utc"], r6["ais_status"]) == ("6", "2026-02-26T06:00:00Z", "ok")
    assert (r6["lat"], r6["lon"], r6["fart_knop"], r6["kurs_grader"], r6["posisjon_alder_min"]) == (
        "60.500000", "5.100000", "8.2", "170.0", "30.0")
    assert abs(float(r6["distanse_km"]) - lt.haversine_km(60.5, 5.10, lt.PORT_LAT, lt.PORT_LON)) < 1e-3
    assert r24["lon"] == "5.320000"
    assert (r24["lat"], r24["fart_knop"], r24["posisjon_alder_min"]) == ("61.200000", "0.1", "300.0")


def test_ingen_lekkasje(tmp_path):
    """Punkter etter t_kutt lagt inn eller flyttet, og faktisk ankomst endret → byte-identisk utdrag."""
    cache, p6, p24 = oppsett(tmp_path)
    _, ut_a = kjør(tmp_path, cache, anlop(tmp_path, ["100"]), "a")
    fasit = (ut_a / "tilstand_ved_kutt.csv").read_bytes()

    etter = [punkt(T[6] + timedelta(seconds=1), lat=60.398), punkt(ETA + timedelta(hours=1), lat=60.398, sog=0.0)]
    cachefil(cache, "100", p6 + etter, p24 + [punkt(T[24] + timedelta(seconds=1), lat=60.0)])
    _, ut_b = kjør(tmp_path, cache, anlop(tmp_path, ["100"]), "b")
    assert (ut_b / "tilstand_ved_kutt.csv").read_bytes() == fasit

    _, ut_c = kjør(tmp_path, cache, anlop(tmp_path, ["100"], ankomst="2026-02-27T09:00:00"), "c")
    assert (ut_c / "tilstand_ved_kutt.csv").read_bytes() == fasit

    # Punktene etter kuttet flyttes til et annet tidspunkt etter kuttet, eller fjernes igjen.
    flyttet = [punkt(T[6] + timedelta(hours=3), lat=60.398), punkt(ETA + timedelta(hours=5), lat=60.1)]
    cachefil(cache, "100", p6 + flyttet, p24)
    _, ut_d = kjør(tmp_path, cache, anlop(tmp_path, ["100"]), "d")
    assert (ut_d / "tilstand_ved_kutt.csv").read_bytes() == fasit
    cachefil(cache, "100", p6, p24)
    _, ut_e = kjør(tmp_path, cache, anlop(tmp_path, ["100"]), "e")
    assert (ut_e / "tilstand_ved_kutt.csv").read_bytes() == fasit


def test_vindusgrensene_er_inklusive(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    cachefil(cache, "100", [punkt(T[6], lat=60.6)], [punkt(T[24] - timedelta(hours=24), lat=60.7)])
    _, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100"]))
    r6, r24 = les(ut)
    assert (r6["ais_status"], r6["lat"], r6["posisjon_alder_min"]) == ("ok", "60.600000", "0.0")
    assert (r24["ais_status"], r24["lat"], r24["posisjon_alder_min"]) == ("ok", "60.700000", "1440.0")


def test_flyttet_siste_punkt(tmp_path):
    """Flyttes siste punkt til etter kuttet, brukes det forrige, og ingen felt kommer fra det flyttede."""
    cache, p6, p24 = oppsett(tmp_path)
    flyttet = [p6[0], punkt(T[6] + timedelta(minutes=10), lat=60.5, sog=8.2, cog=170.0)]
    cachefil(cache, "100", flyttet, p24)
    _, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100"]))
    r6 = les(ut)[0]
    assert (r6["lat"], r6["posisjon_alder_min"]) == ("60.900000", "180.0")


def test_mangler_posisjon(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    cachefil(cache, "100", [], [], status="tom")
    cachefil(cache, "101", [punkt(T[6] - timedelta(hours=25))], [])  # bare utenfor vinduet
    kode, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100", "101", "102"]))
    assert kode == 0
    rader = les(ut)
    assert len(rader) == 6
    assert [r["ais_status"] for r in rader] == ["ingen_posisjon"] * 4 + ["ikke_hentet"] * 2
    for r in rader:
        assert all(r[k] == "" for k in ("lat", "lon", "distanse_km", "fart_knop", "kurs_grader", "posisjon_alder_min"))
    meta = json.loads((ut / "tilstand_ved_kutt.json").read_text(encoding="utf-8"))
    assert meta["antall_per_horisont"]["6"] == {"ok": 0, "ingen_posisjon": 2, "manglende_dag": 0, "ikke_hentet": 1}
    assert meta["kilde_antall_filer"] == 2 and meta["rader"] == 6
    assert meta["kilde_antall_tomme_svar"] == 1
    assert meta["utdrag_sha256"] == hashlib.sha256((ut / "tilstand_ved_kutt.csv").read_bytes()).hexdigest()
    assert not meta["kilde"].startswith("/") and not meta["anlop"].startswith("/")


def test_sentinelverdier(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    p6 = [punkt(T[6] - timedelta(hours=2), lat=60.7), punkt(T[6] - timedelta(hours=1), lat=91.0, lon=181.0),
          punkt(T[6] - timedelta(minutes=30), lat=0.0, lon=0.0)]
    p24 = [punkt(T[24] - timedelta(hours=1), sog=102.3, cog=360.0)]
    cachefil(cache, "100", p6, p24)
    _, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100"]))
    r6, r24 = les(ut)
    assert (r6["lat"], r6["posisjon_alder_min"]) == ("60.700000", "120.0")   # ugyldig siste punkt hoppes over
    assert (r24["ais_status"], r24["fart_knop"], r24["kurs_grader"]) == ("ok", "", "")
    assert r24["lat"] == "60.400000"


def test_siste_gyldige_punkt_ved_likt_tidsstempel():
    t = T[6] - timedelta(minutes=5)
    p, _ = lt.siste_gyldige([punkt(t, lat=60.1), punkt(t, lat=60.2), punkt(t - timedelta(minutes=1), lat=60.3)], MMSI)
    assert p[3] == 60.2


def test_kuttavvik_stopper(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    feil = {6: T[6] + timedelta(hours=1), 24: T[24]}
    cachefil(cache, "100", [], [], t_kutt=feil)
    kode, ut = kjør(tmp_path, cache, anlop(tmp_path, ["100"]))
    assert kode == 2
    assert not ut.exists() or list(ut.iterdir()) == []


def test_deterministisk(tmp_path):
    cache, _, _ = oppsett(tmp_path)
    cachefil(cache, "99", [punkt(T[6] - timedelta(hours=1))], [])
    kilde = anlop(tmp_path, ["100", "99"])
    _, a = kjør(tmp_path, cache, kilde, "a")
    _, b = kjør(tmp_path, cache, kilde, "b")
    for navn in ("tilstand_ved_kutt.csv", "tilstand_ved_kutt.json"):
        assert (a / navn).read_bytes() == (b / navn).read_bytes()
    assert [r["voyageid"] for r in les(a)] == ["99", "99", "100", "100"]   # numerisk sortering
    assert b"\r\n" not in (a / "tilstand_ved_kutt.csv").read_bytes()


def test_leser_ikke_ankomstfelt(tmp_path):
    rader = lt.les_anlop(anlop(tmp_path, ["100"]))
    assert rader == [{"voyageid": "100", "mmsino": "257000000", "eta_reported": "2026-02-26T12:00:00+00:00"}]


def test_sjekksum_folger_kilden(tmp_path):
    cache, p6, p24 = oppsett(tmp_path)
    kilde = anlop(tmp_path, ["100"])
    _, a = kjør(tmp_path, cache, kilde, "a")
    cachefil(cache, "100", p6[:1], p24)
    _, b = kjør(tmp_path, cache, kilde, "b")
    ja, jb = (json.loads((d / "tilstand_ved_kutt.json").read_text(encoding="utf-8")) for d in (a, b))
    assert ja["kilde_sha256"] != jb["kilde_sha256"]


def test_mangler_cache_mappe(tmp_path):
    import pytest
    with pytest.raises(SystemExit) as e:
        lt.main(["--cache-dir", str(tmp_path / "finnes_ikke"), "--anlop", str(anlop(tmp_path, ["1"])),
                 "--ut-dir", str(tmp_path / "ut")])
    assert "fetch_ais_kutt.py" in str(e.value)
    assert not (tmp_path / "finnes_ikke").exists()


def test_odelagt_eller_ufullstendig_cache_stopper(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    kilde = anlop(tmp_path, ["100"])
    (cache / "100.json").write_text('{"status": "ok", "horisonter": {"6"', encoding="utf-8")
    kode, ut = kjør(tmp_path, cache, kilde)
    assert kode == 2 and not ut.exists()
    (cache / "100.json").write_text(json.dumps({"status": "ok", "horisonter": {"24": {}}}), encoding="utf-8")
    kode, ut = kjør(tmp_path, cache, kilde)
    assert kode == 2 and not ut.exists()


def test_ingen_halv_skriving(tmp_path):
    """Feiler skrivingen av den andre fila, byttes ingen av dem inn, og ingen .tmp blir liggende.
    (Et avbrudd mellom de to os.replace-kallene kan ikke hindres med to filer. Det oppdages med
    utdrag_sha256 i metadataene.)"""
    import pytest
    cache, _, _ = oppsett(tmp_path)
    ut = tmp_path / "ut"
    ut.mkdir()
    (ut / "tilstand_ved_kutt.csv").write_text("gammel", encoding="utf-8")
    (ut / "tilstand_ved_kutt.json.tmp").mkdir()          # gjør at skrivingen av JSON feiler
    with pytest.raises(OSError):
        lt.main(["--cache-dir", str(cache), "--anlop", str(anlop(tmp_path, ["100"])), "--ut-dir", str(ut),
                 "--laget", "2026-11-04"])
    assert (ut / "tilstand_ved_kutt.csv").read_text(encoding="utf-8") == "gammel"
    assert not (ut / "tilstand_ved_kutt.csv.tmp").exists()


def test_mmsi_maa_stemme_og_ha_9_sifre(tmp_path):
    """MMSI 0 gir posisjoner fra alle fartøy i verden som sender 0 (røyktesten 03.11.2026).
    Et punkt teller bare hvis MMSI-en er seilasens egen og har 9 sifre."""
    cache = tmp_path / "cache"
    cache.mkdir()
    verden = [punkt(T[6] - timedelta(hours=1), lat=-31.57, lon=-55.59, mmsi=0)]
    cachefil(cache, "100", verden, verden)
    fremmed = [punkt(T[6] - timedelta(hours=2), lat=60.6), punkt(T[6] - timedelta(hours=1), lat=-31.57, mmsi=211000000)]
    cachefil(cache, "101", fremmed, [])
    cachefil(cache, "102", [punkt(T[6] - timedelta(hours=1), mmsi="257000000")], [])   # streng-MMSI i punktet
    kilde = anlop(tmp_path, ["100", "101", "102"], mmsi={"100": 0})
    _, ut = kjør(tmp_path, cache, kilde)
    rader = les(ut)
    assert [r["ais_status"] for r in rader if r["voyageid"] == "100"] == ["ingen_posisjon", "ingen_posisjon"]
    r101 = next(r for r in rader if r["voyageid"] == "101" and r["horisont_timer"] == "6")
    assert (r101["ais_status"], r101["lat"]) == ("ok", "60.600000")     # fremmed MMSI hoppes over
    assert next(r for r in rader if r["voyageid"] == "102")["ais_status"] == "ok"
    meta = json.loads((ut / "tilstand_ved_kutt.json").read_text(encoding="utf-8"))
    assert meta["anlop_ugyldig_mmsi"] == 1
    assert not lt.gyldig_mmsi("0") and not lt.gyldig_mmsi("25700000") and not lt.gyldig_mmsi("2570000001")
    assert lt.gyldig_mmsi("257000000") and lt.gyldig_mmsi(257000000)


# --- Kuttpunkt i en manglende dagstabell (Felipe 05.11.2026, beslutning 09) ---
# Hentingen deler vinduet rundt en dag som mangler hos API-et. Ligger t_kutt i det tapte
# intervallet [dag 00:00, dagen etter 02:00), er en posisjon fra før hullet ikke en ekte alder.

HULL_ETA = datetime(2024, 7, 31, 10, 30)              # som seilas 2501661 fra kjøringen 03.11
HULL_T = {6: HULL_ETA - timedelta(hours=6), 24: HULL_ETA - timedelta(hours=24)}  # 31.07 04:30, 30.07 10:30


def hullcache(d, voyageid, pos6, pos24, manglende=("2024-07-30",), t_kutt=HULL_T):
    cachefil(d, voyageid, pos6, pos24, t_kutt=t_kutt)
    sti = d / f"{voyageid}.json"
    c = json.loads(sti.read_text(encoding="utf-8"))
    if manglende is not None:
        c["manglende_dager"] = list(manglende)
    sti.write_text(json.dumps(c), encoding="utf-8")


def hull_anlop(d, rader):
    sti = d / "anlop.csv"
    with open(sti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["voyageid", "mmsino", "eta_reported"])
        w.writeheader()
        for v in rader:
            w.writerow({"voyageid": v, "mmsino": str(MMSI), "eta_reported": HULL_ETA.isoformat() + "+00:00"})
    return sti


def test_kutt_i_manglende_dag_far_egen_status(tmp_path):
    """t_24 = 30.07 10:30 ligger i hullet. Siste posisjon er fra 29.07 23:00: ikke ok, men manglende_dag.
    Mutasjonssjekket: testen feiler når sjekken i tilstandsrad fjernes."""
    cache = tmp_path / "cache"
    cache.mkdir()
    for_hullet = punkt(datetime(2024, 7, 29, 23, 0))
    hullcache(cache, "100", [for_hullet, punkt(datetime(2024, 7, 31, 4, 0))], [for_hullet])
    kode, ut = kjør(tmp_path, cache, hull_anlop(tmp_path, ["100"]))
    assert kode == 0
    r6, r24 = les(ut)
    assert r24["ais_status"] == "manglende_dag"
    assert all(r24[k] == "" for k in ("lat", "lon", "distanse_km", "fart_knop", "kurs_grader", "posisjon_alder_min"))
    # t_6 = 31.07 04:30 ligger etter hullet (det slutter 31.07 02:00) og har en fersk posisjon.
    assert (r6["ais_status"], r6["posisjon_alder_min"]) == ("ok", "30.0")
    meta = json.loads((ut / "tilstand_ved_kutt.json").read_text(encoding="utf-8"))
    assert meta["antall_per_horisont"]["24"]["manglende_dag"] == 1


def test_hullgrensene(tmp_path):
    """Hullet er [30.07 00:00, 31.07 02:00). Kutt like før og ved slutten er ikke i hullet. En posisjon
    fra innenfor hullet (vinterforskyvning +1 t gir data fra 01:00) er ekte og gir ok. Uten posisjon
    i det hele tatt blir et kutt i hullet manglende_dag, ikke ingen_posisjon."""
    hull = lt.tapt_intervall(datetime(2024, 7, 30).date())
    assert hull == (datetime(2024, 7, 30), datetime(2024, 7, 31, 2, 0))
    cache = tmp_path / "cache"
    cache.mkdir()
    tilfeller = {
        "1": ({6: datetime(2024, 7, 29, 23, 59), 24: datetime(2024, 7, 30, 0, 0)}, "ok", "manglende_dag"),
        # Kutt nøyaktig ved slutten av hullet (31.07 02:00) er utenfor det: posisjonen fra 29.07 er
        # da eldre enn tilbakeblikket, så statusen blir ingen_posisjon, ikke manglende_dag.
        "2": ({6: datetime(2024, 7, 31, 2, 0), 24: datetime(2024, 7, 31, 1, 59)}, "ingen_posisjon", "manglende_dag"),
    }
    for v, (tk, _, _) in tilfeller.items():
        p = punkt(datetime(2024, 7, 29, 23, 30) if v == "1" else datetime(2024, 7, 31, 1, 0) - timedelta(hours=25))
        hullcache(cache, v, [p], [p], t_kutt=tk)
    rad = lambda v, h, tk: lt.tilstandsrad(v, MMSI, h, tk[h], json.loads((cache / f"{v}.json").read_text()))  # noqa: E731
    for v, (tk, s6, s24) in tilfeller.items():
        assert (rad(v, 6, tk)["ais_status"], rad(v, 24, tk)["ais_status"]) == (s6, s24), v
    # Posisjon inne i hullet, 31.07 01:00, ved kutt 31.07 01:30: ekte, ok.
    tk = {6: datetime(2024, 7, 31, 1, 30), 24: datetime(2024, 7, 30, 1, 30)}
    hullcache(cache, "3", [punkt(datetime(2024, 7, 31, 1, 0))], [], t_kutt=tk)
    assert rad("3", 6, tk)["ais_status"] == "ok" and rad("3", 6, tk)["posisjon_alder_min"] == "30.0"
    assert rad("3", 24, tk)["ais_status"] == "manglende_dag"   # ingen posisjon, kutt i hullet


def test_gammel_cache_uten_manglende_dager(tmp_path):
    """Cachefiler fra før 05.11.2026 har ikke feltet. De oppfører seg som før."""
    cache = tmp_path / "cache"
    cache.mkdir()
    hullcache(cache, "100", [], [punkt(datetime(2024, 7, 29, 23, 0))], manglende=None)
    _, ut = kjør(tmp_path, cache, hull_anlop(tmp_path, ["100"]))
    assert [r["ais_status"] for r in les(ut)] == ["ingen_posisjon", "ok"]
