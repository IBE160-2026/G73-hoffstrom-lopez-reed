"""Målrettet AIS-henting ved kuttpunktene (E2-S02, PRD FR9a, beslutning 08/09).

Ingen test bruker nett: hentefunksjonen erstattes av en falsk som returnerer et
konstruert API-svar.
"""
import csv
import importlib.util
import io
import json
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import pytest

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_ais_kutt", REPO_ROT / "pipeline" / "fetch_ais_kutt.py")
fak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fak)

ETA = "2026-02-26T12:00:00+00:00"
ETA_DT = datetime(2026, 2, 26, 12, 0)
T6, T24 = ETA_DT - timedelta(hours=6), ETA_DT - timedelta(hours=24)


@pytest.fixture(autouse=True)
def ingen_sovn(monkeypatch):
    """Pausene mellom delkall skal ikke gjøre testene trege. Tester som teller pausene,
    patcher time.sleep selv."""
    monkeypatch.setattr(fak.time, "sleep", lambda s: None)


def punkt(t):
    # Samme kolonnerekkefølge som API-et: mmsi, tid, lon, lat, cog, sog, …
    return [257000000, t.isoformat() if isinstance(t, datetime) else t, 5.3, 60.4, 90.0, 10.0, 1, 10.0, 10, 50, 90, 0]


def rad(**over):
    r = {"voyageid": "100", "mmsino": "257000000", "ship_group": "Last", "eta_reported": ETA, "split": "test"}
    r.update(over)
    return r


def skriv_kilde(tmp_path, rader, ekstra=("arrival_in_area_utc", "status_in_area")):
    sti = tmp_path / "anlop.csv"
    felt = list(fak.FELTER) + list(ekstra)
    with open(sti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felt)
        w.writeheader()
        for r in rader:
            w.writerow({**{k: "" for k in ekstra}, **r})
    return sti


def alle_tider_i_cache(cache_fil):
    c = json.loads(Path(cache_fil).read_text(encoding="utf-8"))
    return {h: [fak.tidsstempel(p) for p in v["posisjoner"]] for h, v in c["horisonter"].items()}


class FalskHent:
    def __init__(self, svar=None, feil=False):
        self.svar, self.feil, self.kall = svar or [], feil, []

    def __call__(self, mmsi, start, slutt):
        self.kall.append((mmsi, start, slutt))
        if self.feil:
            raise fak.HenteFeil("nede")
        return list(self.svar)


# Et svar slik API-et faktisk oppfører seg: forskjøvet +1 t og med punkter helt fram til ETA.
SVAR = [punkt(ETA_DT + timedelta(minutes=m)) for m in range(-72 * 60, 18 * 60 + 61, 30)] + [
    punkt(T6), punkt(T6 + timedelta(seconds=1)), punkt(T24), punkt(T24 + timedelta(seconds=1)),
    punkt(T24 - timedelta(hours=24)), punkt(T24 - timedelta(hours=24, seconds=1)),
]


def test_vindu_fra_rapportert_eta():
    """Forespørsel og kuttpunkter avhenger bare av rapportert ETA, ikke av faktisk ankomst."""
    assert fak.foresporselsvindu(ETA_DT) == (ETA_DT - timedelta(hours=72), ETA_DT + timedelta(hours=18))
    assert fak.kuttpunkter(ETA_DT) == {6: T6, 24: T24}
    hent_a, hent_b = FalskHent(SVAR), FalskHent(SVAR)
    a = fak.bygg_cache(rad(arrival_in_area_utc="2026-02-26T11:00:00"), hent_a("x", *fak.foresporselsvindu(ETA_DT)))
    b = fak.bygg_cache(rad(arrival_in_area_utc="2026-02-28T03:00:00"), hent_b("x", *fak.foresporselsvindu(ETA_DT)))
    a.pop("hentet_utc"), b.pop("hentet_utc")
    assert a == b


def test_leser_ikke_ankomstfelt(tmp_path):
    sti = skriv_kilde(tmp_path, [rad(arrival_in_area_utc="2026-02-26T11:00:00", status_in_area="ok")])
    lest = fak.les_anlop(sti)
    assert set(lest[0]) == set(fak.FELTER)
    # Uten ankomstkolonnene i fila virker skriptet like godt.
    (tmp_path / "uten").mkdir()
    sti2 = skriv_kilde(tmp_path / "uten", [rad()], ekstra=())
    assert fak.les_anlop(sti2) == [rad()]


def test_filtrerer_bort_punkter_etter_kutt(tmp_path):
    """Et svar med punkter etter t_H gir ingen slike i cachen, og grensene er inklusive."""
    fak.behandle(rad(), str(tmp_path), FalskHent(SVAR))
    tider = alle_tider_i_cache(tmp_path / "100.json")
    for h, t_kutt in ((6, T6), (24, T24)):
        assert tider[str(h)], h
        assert max(tider[str(h)]) == t_kutt
        assert min(tider[str(h)]) == t_kutt - timedelta(hours=24)
        assert all(t_kutt - timedelta(hours=24) <= t <= t_kutt for t in tider[str(h)])


def test_ingenting_etter_eta_minus_6t(tmp_path, monkeypatch):
    """Hardt tak (Felipe 03.11.2026): ingen punkter etter ETA − 6 t når disk, selv om
    vindusfilteret per horisont skulle svikte. Mutasjonssjekket: testen feiler når taket
    i kutt_ved_tak fjernes."""
    monkeypatch.setattr(fak, "filtrer_til_vindu", lambda svar, fra, til: list(svar))
    try:
        fak.behandle(rad(), str(tmp_path), FalskHent(SVAR))
    except RuntimeError:
        pytest.fail("taket slapp gjennom punkter etter ETA − 6 t")
    raa = (tmp_path / "100.json").read_text(encoding="utf-8")
    tider = [t for ts in alle_tider_i_cache(tmp_path / "100.json").values() for t in ts]
    assert tider and max(tider) == T6
    assert (T6 + timedelta(seconds=1)).isoformat() not in raa
    c = json.loads(raa)
    assert c["kastet_etter_tak"] == sum(1 for p in SVAR if fak.tidsstempel(p) > T6)


def test_uleselige_tidsstempler_kastes(tmp_path):
    svar = [punkt("tull"), [1], punkt(T6 + timedelta(hours=1, minutes=-59)), punkt("2026-02-26T05:00:00Z"),
            punkt("2026-02-26T07:30:00+02:00")]  # = 05:30 UTC
    fak.behandle(rad(), str(tmp_path), FalskHent(svar))
    assert alle_tider_i_cache(tmp_path / "100.json")["6"] == [datetime(2026, 2, 26, 5, 0), datetime(2026, 2, 26, 5, 30)]


def test_hopper_over_cachet(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad(), rad(voyageid="101")])
    cache = tmp_path / "cache"
    argv = ["--kilde", str(kilde), "--cache-dir", str(cache), "--logg", str(tmp_path / "l.csv"),
            "--dekning", str(tmp_path / "d.csv"), "--pause", "0"]
    h1 = FalskHent(SVAR)
    assert fak.main(argv, hent=h1) == 0
    assert len(h1.kall) == 2
    h2 = FalskHent(SVAR)
    assert fak.main(argv, hent=h2) == 0
    assert h2.kall == []


def test_feil_gir_ingen_cache(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i)) for i in range(12)])
    cache = tmp_path / "cache"
    argv = ["--kilde", str(kilde), "--cache-dir", str(cache), "--logg", str(tmp_path / "l.csv"),
            "--dekning", str(tmp_path / "d.csv"), "--pause", "0"]
    h = FalskHent(feil=True)
    assert fak.main(argv, hent=h) == 2           # stopper etter 10 feil på rad
    assert len(h.kall) == fak.MAKS_FEIL_PA_RAD
    assert list(cache.iterdir()) == []
    logg = list(csv.DictReader(open(tmp_path / "l.csv", encoding="utf-8")))
    assert all(r["status"].startswith("feil") for r in logg)
    h2 = FalskHent(SVAR)                          # neste kjøring prøver alle igjen
    assert fak.main(argv, hent=h2) == 0 and len(h2.kall) == 12


def test_tomt_svar(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad()])
    cache = tmp_path / "cache"
    argv = ["--kilde", str(kilde), "--cache-dir", str(cache), "--logg", str(tmp_path / "l.csv"),
            "--dekning", str(tmp_path / "d.csv"), "--pause", "0"]
    fak.main(argv, hent=FalskHent([]))
    c = json.loads((cache / "100.json").read_text(encoding="utf-8"))
    assert c["status"] == "tom" and c["horisonter"]["6"]["posisjoner"] == []
    assert fak.main(argv, hent=(h := FalskHent(SVAR))) == 0 and h.kall == []
    assert fak.main(argv + ["--prov-tomme"], hent=(h := FalskHent(SVAR))) == 0 and len(h.kall) == 1


def test_ingen_tmp_fil_ved_avbrudd(tmp_path, monkeypatch):
    def krasj(*a, **k):
        raise KeyboardInterrupt
    monkeypatch.setattr(fak.json, "dump", krasj)
    with pytest.raises(KeyboardInterrupt):
        fak.skriv_atomisk(str(tmp_path / "100.json"), {"a": 1})
    assert list(tmp_path.iterdir()) == []         # verken 100.json eller 100.json.tmp


def test_dekningstabell(tmp_path):
    rader = [rad(voyageid="1"), rad(voyageid="2", ship_group="Passasjer", split="train"),
             rad(voyageid="3"), rad(voyageid="4")]
    cache = str(tmp_path)
    fak.behandle(rader[0], cache, FalskHent(SVAR))                          # posisjon rett ved kutt
    fak.behandle(rader[1], cache, FalskHent([punkt(T6 - timedelta(hours=5)),
                                             punkt(T24 - timedelta(hours=5))]))  # bare gammel posisjon
    fak.behandle(rader[2], cache, FalskHent([]))                            # tom; rad 4 er ikke hentet
    tab = {(r["horisont_timer"], r["gruppe"], r["split"]): r for r in fak.dekning(rader, cache)}
    assert len(tab) == 4
    o = tab[(6, "Øvrige", "test")]
    assert (o["n"], o["hentet"], o["med_posisjon_24t"], o["med_posisjon_1t"]) == (3, 2, 1, 1)
    assert o["andel_med_posisjon_24t"] == "0.500"
    p = tab[(24, "Passasjer", "train")]
    assert (p["n"], p["hentet"], p["med_posisjon_24t"], p["med_posisjon_1t"]) == (1, 1, 1, 0)
    fak.skriv_dekning(list(tab.values()), str(tmp_path / "d.csv"))
    assert len(list(csv.DictReader(open(tmp_path / "d.csv", encoding="utf-8")))) == 4


def argv_for(tmp_path, kilde, *ekstra):
    return ["--kilde", str(kilde), "--cache-dir", str(tmp_path / "cache"), "--logg", str(tmp_path / "l.csv"),
            "--dekning", str(tmp_path / "d.csv"), "--pause", "0", *ekstra]


class FalskRespons(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_hent_posisjoner_kropp_og_gjentak(monkeypatch):
    kall, sovn = [], []
    svar = iter([OSError("timeout"), b'{"success": false, "msg": "x"}', b'[]',
                 b'{"success": true, "data": [[1, "2026-02-26T05:00:00"]]}'])

    def urlopen(req, timeout):
        kall.append(req)
        x = next(svar)
        if isinstance(x, Exception):
            raise x
        return FalskRespons(x)
    monkeypatch.setattr(fak.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fak.time, "sleep", sovn.append)
    start, slutt = fak.foresporselsvindu(ETA_DT)
    assert fak.hent_posisjoner("257000000", start, slutt) == [[1, "2026-02-26T05:00:00"]]
    assert json.loads(kall[0].data) == {"mmsiIds": [257000000], "start": "202602231200", "end": "202602270600"}
    assert kall[0].full_url == fak.API_URL and kall[0].get_method() == "POST"
    assert sovn == list(fak.BACKOFF_SEK)


def test_hent_posisjoner_gir_opp(monkeypatch):
    def urlopen(req, timeout):
        raise urllib.error.URLError("nede")
    monkeypatch.setattr(fak.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fak.time, "sleep", lambda s: None)
    with pytest.raises(fak.HenteFeil):
        fak.hent_posisjoner("1", ETA_DT, ETA_DT)


def test_hent_posisjoner_4xx_uten_gjentak(monkeypatch):
    kall = []

    def urlopen(req, timeout):
        kall.append(1)
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, None)
    monkeypatch.setattr(fak.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fak.time, "sleep", lambda s: None)
    with pytest.raises(fak.HenteFeil):
        fak.hent_posisjoner("1", ETA_DT, ETA_DT)
    assert len(kall) == 1


def test_bare_uleselige_tidsstempler_er_feil(tmp_path):
    with pytest.raises(fak.HenteFeil):
        fak.behandle(rad(), str(tmp_path), FalskHent([punkt("26.02.2026 05:00")]))
    assert list(tmp_path.iterdir()) == []


def test_feil_pa_rad_nullstilles(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i), mmsino=str(i)) for i in range(19)])

    def hent(mmsi, start, slutt):
        if mmsi != "9":
            raise fak.HenteFeil("nede")
        return list(SVAR)
    assert fak.main(argv_for(tmp_path, kilde), hent=hent) == 0
    assert [f.name for f in (tmp_path / "cache").iterdir()] == ["9.json"]


def test_utvalg_er_deterministisk_og_hopper_over_cachet(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i)) for i in range(6)])
    h = FalskHent(SVAR)
    (tmp_path / "cache").mkdir()
    fak.behandle(rad(voyageid="0"), str(tmp_path / "cache"), h)  # allerede cachet før piloten
    h1, h2 = FalskHent(SVAR), FalskHent(SVAR)
    fak.main(argv_for(tmp_path, kilde, "--utvalg", "2", "--seed", "2"), hent=h1)
    valgt = sorted(f.name for f in (tmp_path / "cache").iterdir())
    assert len(h1.kall) == 2 and len(valgt) == 3 and "0.json" in valgt
    for f in (tmp_path / "cache").iterdir():
        if f.name != "0.json":
            f.unlink()
    fak.main(argv_for(tmp_path, kilde, "--utvalg", "2", "--seed", "2"), hent=h2)
    assert sorted(f.name for f in (tmp_path / "cache").iterdir()) == valgt


def test_avbrudd_skriver_dekning_og_kan_fortsette(tmp_path):
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i), mmsino=str(i)) for i in range(3)])

    def hent(mmsi, start, slutt):
        if mmsi == "1":
            raise KeyboardInterrupt
        return list(SVAR)
    assert fak.main(argv_for(tmp_path, kilde), hent=hent) == 130
    assert [f.name for f in (tmp_path / "cache").iterdir()] == ["0.json"]
    assert (tmp_path / "d.csv").exists()
    h = FalskHent(SVAR)
    assert fak.main(argv_for(tmp_path, kilde), hent=h) == 0 and len(h.kall) == 2


def test_tom_kilde(tmp_path):
    kilde = skriv_kilde(tmp_path, [])
    assert fak.main(argv_for(tmp_path, kilde), hent=FalskHent()) == 0
    assert (tmp_path / "d.csv").read_text(encoding="utf-8").strip() == ",".join(fak.DEKNING_KOLONNER)


def test_manglende_dagstabell_uten_gjentak(monkeypatch):
    """Sett i piloten: success=false med 42P01 «does not exist» kommer igjen hver gang."""
    kall = []

    def urlopen(req, timeout):
        kall.append(1)
        return FalskRespons(json.dumps({"success": False, "msg": '42P01: relation "ais202410.ais_20241028" '
                                        'does not exist\n\nPOSITION: 978'}).encode())
    monkeypatch.setattr(fak.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fak.time, "sleep", lambda s: None)
    with pytest.raises(fak.HenteFeil, match="mangler hos API-et"):
        fak.hent_posisjoner("1", ETA_DT, ETA_DT)
    assert len(kall) == 1


# --- Manglende dagstabell (42P01): stoppregel og deling av vinduet (05.11.2026) ---

class FalskArkiv:
    """Etterligner API-et slik prøvekallene 05.11.2026 viste: dagstabellene velges etter
    datoen i forespørselen, og et vindu som rører en manglende dag, feiler med 42P01.
    Returnerer ett punkt per time i [start, slutt], uten forskyvning."""

    def __init__(self, mangler=()):
        self.mangler, self.kall = set(mangler), []

    def __call__(self, mmsi, start, slutt):
        self.kall.append((start, slutt))
        d = start.date()
        while d <= slutt.date():
            if d in self.mangler:
                raise fak.ManglerDag(f'mangler hos API-et: 42P01: relation "ais{d:%Y%m}.ais_{d:%Y%m%d}" '
                                     'does not exist', d)
            d += timedelta(days=1)
        t, ut = start.replace(minute=0), []
        while t <= slutt:
            if t >= start:
                ut.append(punkt(t))
            t += timedelta(hours=1)
        return ut


def test_delt_manglende_dag_teller_ikke_mot_stoppregelen(tmp_path):
    """Hentingen 03.11.2026 stoppet etter ti 42P01 på rad for samme dag. Med lesbar dag
    deles vinduet nå, og alle seilasene hentes."""
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i), mmsino=str(i), eta_reported="2024-07-31T10:30:00+00:00")
                                   for i in range(25)])
    assert fak.main(argv_for(tmp_path, kilde), hent=FalskArkiv({datetime(2024, 7, 30).date()})) == 0
    assert len(list((tmp_path / "cache").iterdir())) == 25
    logg = list(csv.DictReader(open(tmp_path / "l.csv", encoding="utf-8")))
    assert [r["status"] for r in logg] == ["ok"] * 25


def test_manglende_dag_som_ikke_kan_deles_teller_mot_stoppregelen(tmp_path):
    """Review 05.11.2026: et systematisk API-brudd med «does not exist» uten lesbar dag
    skal stoppe kjøringen som vanlig nedetid, ikke gå gjennom alle seilasene."""
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i), mmsino=str(i)) for i in range(30)])
    kall = []

    def hent(mmsi, start, slutt):
        kall.append(mmsi)
        raise fak.ManglerDag("mangler hos API-et: 42P01", None)
    assert fak.main(argv_for(tmp_path, kilde), hent=hent) == 2
    assert len(kall) == fak.MAKS_FEIL_PA_RAD
    logg = list(csv.DictReader(open(tmp_path / "l.csv", encoding="utf-8")))
    assert all(r["status"].startswith("feil: mangler hos API-et") for r in logg)


def test_delt_seilas_nullstiller_stoppregelen(tmp_path):
    """En seilas som hentes etter deling, er en suksess: annenhver ekte feil stopper ikke."""
    kilde = skriv_kilde(tmp_path, [rad(voyageid=str(i), mmsino=str(i), eta_reported="2024-07-31T10:30:00+00:00")
                                   for i in range(30)])
    arkiv = FalskArkiv({datetime(2024, 7, 30).date()})

    def hent(mmsi, start, slutt):
        if int(mmsi) % 2:
            return arkiv(mmsi, start, slutt)
        raise fak.HenteFeil("nede")
    assert fak.main(argv_for(tmp_path, kilde), hent=hent) == 0
    assert len(list((tmp_path / "cache").iterdir())) == 15


def test_manglende_dag_leses_fra_meldingen(monkeypatch):
    def urlopen(req, timeout):
        return FalskRespons(json.dumps({"success": False, "msg": '42P01: relation "ais202407.ais_20240730" '
                                        'does not exist\n\nPOSITION: 978'}).encode())
    monkeypatch.setattr(fak.urllib.request, "urlopen", urlopen)
    with pytest.raises(fak.ManglerDag) as e:
        fak.hent_posisjoner("1", ETA_DT, ETA_DT)
    assert e.value.dag == datetime(2024, 7, 30).date() and e.value.varig
    assert fak.manglende_dag("noe annet") is None


def test_delvinduer_unngar_dagen_og_er_lange_nok():
    dag = datetime(2024, 7, 30).date()
    # Seilas 2501661 fra kjøringen 03.11: ETA 31.07 10:30 → [28.07 10:30, 01.08 04:30].
    start, slutt = datetime(2024, 7, 28, 10, 30), datetime(2024, 8, 1, 4, 30)
    v, h = fak.del_rundt_dag(start, slutt, dag)
    assert v == (start, datetime(2024, 7, 29, 23, 59))
    assert h[0] == datetime(2024, 7, 31, 0, 0) and h[1] >= slutt
    for s, e in (v, h):
        assert e - s >= fak.MIN_DELVINDU
        assert not (s.date() <= dag <= e.date())
    # Kort rest på hver side forlenges utover, ikke innover.
    v, h = fak.del_rundt_dag(datetime(2024, 7, 29, 20), datetime(2024, 7, 31, 3), dag)
    assert v == (datetime(2024, 7, 28, 22, 59), datetime(2024, 7, 29, 23, 59))
    assert h == (datetime(2024, 7, 31, 0, 0), datetime(2024, 8, 1, 1, 0))
    # Manglende dag helt i starten eller slutten gir bare én del.
    assert len(fak.del_rundt_dag(datetime(2024, 7, 30, 5), datetime(2024, 8, 2), dag)) == 1
    assert len(fak.del_rundt_dag(datetime(2024, 7, 27), datetime(2024, 7, 30, 5), dag)) == 1


def test_bare_den_manglende_dagen_gar_tapt(tmp_path):
    dag = datetime(2024, 7, 30).date()
    arkiv = FalskArkiv({dag})
    r = rad(voyageid="2501661", eta_reported="2024-07-31T10:30:00+00:00")
    loggrad = fak.behandle(r, str(tmp_path), arkiv)
    assert loggrad[-1] == "ok"
    assert len(arkiv.kall) == 3  # hele vinduet, så de to delene
    c = json.loads((tmp_path / "2501661.json").read_text(encoding="utf-8"))
    assert c["manglende_dager"] == ["2024-07-30"]
    tider = sorted(fak.tidsstempel(p) for ps in c["horisonter"].values() for p in ps["posisjoner"])
    assert not any(t.date() == dag for t in tider)
    # t_24 = 30.07 10:30 ligger i hullet, men 29.07 har posisjoner; t_6 = 31.07 04:30 har 31.07.
    assert max(fak.tidsstempel(p) for p in c["horisonter"]["24"]["posisjoner"]) == datetime(2024, 7, 29, 23, 0)
    assert max(fak.tidsstempel(p) for p in c["horisonter"]["6"]["posisjoner"]) == datetime(2024, 7, 31, 4, 0)


def test_to_manglende_dager_og_ingen_duplikater(tmp_path):
    """Delvinduene overlapper ikke, så sammenslåingen trenger ingen dedup."""
    mangler = {datetime(2024, 7, 29).date(), datetime(2024, 7, 31).date()}
    arkiv = FalskArkiv(mangler)
    punkter, dager = fak.hent_med_hull(arkiv, "1", datetime(2024, 7, 28, 6), datetime(2024, 8, 2, 6))
    assert dager == sorted(mangler)
    tider = [fak.tidsstempel(p) for p in punkter]
    assert len(tider) == len(set(tider))
    assert not any(t.date() in mangler for t in tider)
    # Dagen mellom de to hullene (30.07) og dagene utenfor er med.
    for d in (28, 30, 1, 2):
        assert any(t.day == d for t in tider), d


def test_uten_hull_er_svaret_uendret():
    """Uten manglende dag går det ett kall, og svaret brukes som det er (ingen dedup)."""
    h = FalskHent(SVAR + SVAR[:3])
    punkter, dager = fak.hent_med_hull(h, "1", *fak.foresporselsvindu(ETA_DT))
    assert dager == [] and len(h.kall) == 1 and len(punkter) == len(SVAR) + 3


def test_dekning_teller_manglende_dag_i_tilbakeblikket(tmp_path):
    dag = datetime(2024, 7, 30).date()
    rader = [rad(voyageid="1", eta_reported="2024-07-31T10:30:00+00:00"),   # t_24 i hullet
             rad(voyageid="2", eta_reported="2024-08-02T12:00:00+00:00")]  # hullet er i vinduet, før begge tilbakeblikk
    fak.behandle(rader[0], str(tmp_path), FalskArkiv({dag}))
    fak.behandle(rader[1], str(tmp_path), FalskArkiv({dag}))
    tab = {r["horisont_timer"]: r for r in fak.dekning(rader, str(tmp_path))}
    assert tab[24]["med_manglende_dag"] == 1 and tab[24]["manglende_dager"] == "2024-07-30"
    # t_6 = 31.07 04:30, tilbakeblikk fra 30.07 04:30: rører også hullet.
    assert tab[6]["med_manglende_dag"] == 1
    c2 = json.loads((tmp_path / "2.json").read_text(encoding="utf-8"))
    assert c2["manglende_dager"] == ["2024-07-30"]  # vinduet starter 30.07 12:00, tilbakeblikket 31.07 12:00


def test_manglende_dag_som_ikke_kan_deles_gir_feil():
    """Kan vinduet ikke deles, blir det en vanlig HenteFeil som teller mot stoppregelen."""
    def hent(mmsi, s, e):
        raise fak.ManglerDag("x", datetime(2020, 1, 1).date())  # dag utenfor vinduet
    with pytest.raises(fak.HenteFeil, match="utenfor") as e:
        fak.hent_med_hull(hent, "1", ETA_DT, ETA_DT + timedelta(days=1))
    assert not isinstance(e.value, fak.ManglerDag)


# --- Rettelser fra review av 0a85cd4 (05.11.2026), lagt inn 06.11.2026 ---

def test_samme_dag_etter_deling_gir_opp():
    """Vern mot evig deling: kommer samme dag igjen etter delingen, gis det opp."""
    dag = datetime(2024, 7, 30).date()
    kall = []

    def hent(mmsi, s, e):
        kall.append((s, e))
        raise fak.ManglerDag("mangler hos API-et: 42P01", dag)
    with pytest.raises(fak.HenteFeil, match="kom igjen etter deling") as e:
        fak.hent_med_hull(hent, "1", datetime(2024, 7, 28, 10, 30), datetime(2024, 8, 1, 4, 30))
    assert not isinstance(e.value, fak.ManglerDag)
    assert len(kall) == 2  # hele vinduet, så første delvindu, som gir samme dag igjen


def test_maks_delinger(monkeypatch):
    """Vern mot evig deling: etter MAKS_DELINGER delinger gis det opp."""
    monkeypatch.setattr(fak, "MAKS_DELINGER", 2)
    mangler = {datetime(2024, 7, d).date() for d in (2, 4, 6)}
    arkiv = FalskArkiv(mangler)
    with pytest.raises(fak.HenteFeil, match="mer enn 2 delinger"):
        fak.hent_med_hull(arkiv, "1", datetime(2024, 7, 1, 6), datetime(2024, 7, 8, 6))
    # Hele, 01.07 (ok), 03.07–08.07 (deles ved 4.), 03.07 (ok), 05.07–08.07 (6. = tredje deling).
    assert len(arkiv.kall) == 5
    monkeypatch.setattr(fak, "MAKS_DELINGER", 3)
    _, dager = fak.hent_med_hull(FalskArkiv(mangler), "1", datetime(2024, 7, 1, 6), datetime(2024, 7, 8, 6))
    assert dager == sorted(mangler)


def test_pause_mellom_delkall(monkeypatch, tmp_path):
    sovn = []
    monkeypatch.setattr(fak.time, "sleep", sovn.append)
    r = rad(voyageid="2501661", eta_reported="2024-07-31T10:30:00+00:00")
    fak.behandle(r, str(tmp_path), FalskArkiv({datetime(2024, 7, 30).date()}), pause=1.0)
    assert sovn == [1.0, 1.0]  # to delkall etter delingen
    sovn.clear()
    fak.behandle(rad(voyageid="9"), str(tmp_path), FalskHent(SVAR), pause=1.0)
    assert sovn == []  # udelt seilas: pausen tas i main, som før


def test_delt_seilas_beholder_svaret_som_det_er():
    """Ingen dedup: en delt seilas behandler API-ets rader likt med en udelt."""
    arkiv = FalskArkiv({datetime(2024, 7, 30).date()})

    def hent(mmsi, s, e):
        ut = arkiv(mmsi, s, e)
        return ut + ut[-1:]  # én dublett i hvert svar
    start, slutt = datetime(2024, 7, 28, 10, 30), datetime(2024, 8, 1, 4, 30)
    punkter, _ = fak.hent_med_hull(hent, "1", start, slutt)
    tider = [fak.tidsstempel(p) for p in punkter]
    assert len(tider) - len(set(tider)) == 2


def test_delt_svar_klippes_til_foresporselen():
    """Delvinduer forlenget utover gir ikke punkter utenfor [start, slutt + forskyvning]."""
    mangler = {datetime(2024, 7, 29).date(), datetime(2024, 7, 31).date()}
    arkiv = FalskArkiv(mangler)
    start, slutt = datetime(2024, 7, 28, 10, 30), datetime(2024, 8, 1, 4, 30)
    punkter, _ = fak.hent_med_hull(arkiv, "1", start, slutt)
    # Forlengelsen hentet faktisk punkter utenfor vinduet på begge sider ...
    assert min(s for s, _ in arkiv.kall) < start and max(e for _, e in arkiv.kall) > slutt + fak.API_FORSKYVNING_MAKS
    # ... men de er klippet bort.
    tider = [fak.tidsstempel(p) for p in punkter]
    assert min(tider) >= start and max(tider) <= slutt + fak.API_FORSKYVNING_MAKS
    assert min(tider) == datetime(2024, 7, 28, 11) and max(tider) == datetime(2024, 8, 1, 6)


def test_tapt_intervall_slutter_2t_inn_i_dagen_etter(tmp_path):
    """Høyre delvindu starter 00:00 i forespørselsklokka, og API-et forskyver inntil +2 t.
    Et tilbakeblikk som starter 31.07 før 02:00, rører derfor hullet etter 30.07."""
    dag = datetime(2024, 7, 30).date()
    assert fak.tapt_intervall(dag) == (datetime(2024, 7, 30), datetime(2024, 7, 31, 2))
    for eta, forventet in (("2024-08-02T01:59:00+00:00", 1),   # fra_24 = 31.07 01:59
                           ("2024-08-02T02:00:00+00:00", 0)):  # fra_24 = 31.07 02:00
        r = rad(voyageid=eta[11:13] + eta[14:16], eta_reported=eta)
        fak.behandle(r, str(tmp_path), FalskArkiv({dag}))
        tab = {x["horisont_timer"]: x for x in fak.dekning([r], str(tmp_path))}
        assert tab[24]["med_manglende_dag"] == forventet, eta
        assert tab[6]["med_manglende_dag"] == 0


def test_dekning_pa_cache_uten_manglende_dager(tmp_path):
    """Cachefiler fra før 05.11.2026 har ikke feltet manglende_dager."""
    r = rad(voyageid="7")
    innhold = fak.bygg_cache(r, list(SVAR))
    assert "manglende_dager" not in innhold
    fak.skriv_atomisk(fak.cache_sti(str(tmp_path), "7"), innhold)
    tab = fak.dekning([r], str(tmp_path))
    assert [(x["hentet"], x["med_posisjon_24t"], x["med_manglende_dag"], x["manglende_dager"]) for x in tab] \
        == [(1, 1, 0, "")] * 2
