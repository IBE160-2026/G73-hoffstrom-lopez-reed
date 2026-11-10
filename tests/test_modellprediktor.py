"""ModellPrediktor og grensen ``featurer_ved_kutt`` (E2-S07, PRD FR9, beslutning 11 og 12).

Alle eksempelrader er fra valideringsdelen. Ingen test sammenligner en modellprediksjon med fasit, og ingen test
predikerer på testperioden med modellen utenom kontrakttestene (``tests/test_prediktor_kontrakt.py``), som aldri
scorer. Ekvivalensen med modellarmen i ``scripts/evaluer.py`` sjekkes på valideringsradene ved kuttet.
"""
import csv
import dataclasses
import datetime as dt
import importlib.util
from pathlib import Path

import joblib
import pytest

import app.prediksjon.modell as modellmodul
from app.data import last_utdrag
from app.prediksjon import PrediksjonsInput, featurer_ved_kutt, lag_input, velg_prediktor
from app.prediksjon.baseline import BaselinePrediktor
from app.prediksjon.modell import ModellPrediktor

REPO_ROT = Path(__file__).resolve().parent.parent
FEATURES_CSV = REPO_ROT / "data" / "utdrag" / "features.csv"
MODELL_DIR = REPO_ROT / "data" / "modell"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "anlop_mini.csv"

_spec = importlib.util.spec_from_file_location("evaluer", REPO_ROT / "scripts" / "evaluer.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

FORBUDT = {"del", "gruppe", "t_kutt_utc", "voyageid", "horisont_timer", "har_tilstand", "faktisk_ankomst",
           "status_in_area", "split", "er_forsinket"}


@pytest.fixture(scope="module")
def prediktor():
    return ModellPrediktor()


@pytest.fixture(scope="module")
def features():
    return ev.les_features(FEATURES_CSV)


@pytest.fixture(scope="module")
def validering(features):
    return ev.anlop_i_split(last_utdrag(), features, "validering")


def _finn(validering, features, h, betingelse):
    for a in validering:
        rad = features.get((a.voyageid, h))
        if betingelse(a, rad):
            return a
    raise AssertionError("fant ingen eksempelrad")


def _ved_kutt(a, h):
    naa = a.eta_reported - dt.timedelta(hours=h)
    return lag_input(a, naa), naa


def _modellrad(a, rad):
    return ev.i_modellutvalg(a, rad)


# --- Matrisen ----------------------------------------------------------------------------------


@pytest.mark.parametrize("h", [6, 24])
def test_modellrad(prediktor, validering, features, h):
    a = _finn(validering, features, h, _modellrad)
    inp, naa = _ved_kutt(a, h)
    [p] = prediktor.prediker([inp], naa)
    f = p.forklaring
    assert f["metode"] == "modell" and f["variant"] == "hoved" and f["horisont"] == h
    assert f["gruppe"] == "Øvrige" and "delegert" not in f
    assert p.forventet_forsinket is (f["predikert_avvik_min"] > 120)
    offset = BaselinePrediktor().offset_minutter["Øvrige"]
    venter = inp.eta_reported - dt.timedelta(minutes=offset) + dt.timedelta(minutes=f["predikert_avvik_min"])
    assert abs((p.predikert_ankomst - venter).total_seconds()) < 1e-3
    assert f["featurer"] == dict(featurer_ved_kutt(inp))
    assert f["featurer"]["i_sonen_ved_kutt"] == 0


@pytest.mark.parametrize("navn, h, betingelse", [
    ("passasjer", 6, lambda a, r: a.gruppe == "Passasjer"),
    ("passasjer", 24, lambda a, r: a.gruppe == "Passasjer"),
    ("ingen_tilstand", 6, lambda a, r: a.gruppe == "Øvrige" and r is not None and r["har_tilstand"] == "0"),
    ("ingen_tilstand", 24, lambda a, r: a.gruppe == "Øvrige" and r is not None and r["har_tilstand"] == "0"),
    ("i_sonen_ved_kutt", 6, lambda a, r: a.gruppe == "Øvrige" and ev.er_f6(r)),
    ("i_sonen_ved_kutt", 24, lambda a, r: a.gruppe == "Øvrige" and ev.er_f6(r)),
])
def test_delegerte_rader(prediktor, validering, features, navn, h, betingelse):
    a = _finn(validering, features, h, betingelse)
    inp, naa = _ved_kutt(a, h)
    [p] = prediktor.prediker([inp], naa)
    [b] = BaselinePrediktor().prediker([inp], naa)
    assert p.forventet_forsinket is None
    assert p.forklaring["delegert"] == navn
    assert p.predikert_ankomst == b.predikert_ankomst
    assert {k: v for k, v in p.forklaring.items() if k != "delegert"} == b.forklaring


class _FastAvvik:
    """Stub-modell som predikerer samme avvik for alle rader."""

    def __init__(self, avvik):
        self.avvik = avvik

    def predict(self, X):
        return [self.avvik] * len(X)


@pytest.mark.parametrize("avvik, varsel", [(120.0, False), (120.001, True), (-30.0, False)])
def test_varselterskelen_er_strengt_over_120(validering, features, avvik, varsel):
    """Varsel er predikert avvik > 120 min (beslutning 06), ikke ≥. Stub-modell, så ingen rad trenger å ligge på grensen."""
    p = ModellPrediktor()
    p._artefakter = {h: dict(art, modell=_FastAvvik(avvik)) for h, art in p._artefakter.items()}
    a = _finn(validering, features, 6, _modellrad)
    inp, naa = _ved_kutt(a, 6)
    [ut] = p.prediker([inp], naa)
    assert ut.forklaring["predikert_avvik_min"] == avvik
    assert ut.forventet_forsinket is varsel


def test_klemt_kutt_delegeres(prediktor, validering, features):
    """ETA mer enn 24 t fram: ``t_kutt = naa`` ≠ radens kutt, så den committede raden (fra etter «nå») brukes ikke."""
    a = _finn(validering, features, 24, _modellrad)
    naa = a.eta_reported - dt.timedelta(hours=30)
    inp = lag_input(a, naa)
    assert inp.horisont_timer == 24 and inp.t_kutt == naa
    assert featurer_ved_kutt(inp) is None
    [p] = prediktor.prediker([inp], naa)
    assert p.forklaring["delegert"] == "ingen_featurerad" and p.forventet_forsinket is None


def test_ukjent_seilas_delegeres(prediktor):
    naa = dt.datetime(2025, 10, 7, 6, 0, tzinfo=dt.timezone.utc)
    inputs = [lag_input(a, naa) for a in last_utdrag(FIXTURE)]
    for inp, p in zip(inputs, prediktor.prediker(inputs, naa)):
        venter = "passasjer" if inp.gruppe == "Passasjer" else "ingen_featurerad"
        assert p.forklaring["delegert"] == venter and p.forventet_forsinket is None


def test_blandet_batch_beholder_rekkefolgen(prediktor, validering):
    ovrige = [a for a in validering if a.gruppe == "Øvrige"][:40]
    passasjer = [a for a in validering if a.gruppe == "Passasjer"][:20]
    blandet = [x for par in zip(ovrige[::2], ovrige[1::2], passasjer) for x in par]
    inputs = [lag_input(a, a.eta_reported - dt.timedelta(hours=6)) for a in blandet]
    naa = max(i.t_kutt for i in inputs)
    ut = prediktor.prediker(inputs, naa)
    assert [p.voyageid for p in ut] == [i.voyageid for i in inputs]
    metoder = {p.forklaring["metode"] for p in ut}
    assert metoder == {"modell", "kalibrert_baseline"}
    for inp, p in zip(inputs, ut):
        assert p == prediktor.prediker([inp], naa)[0]


def test_blandet_batch_med_begge_horisontene(prediktor, validering, features):
    """Modellrader ved 6 t og 24 t flettet i ett kall: hver rad bruker artefaktet for sin egen horisont."""
    seks = [a for a in validering if _modellrad(a, features.get((a.voyageid, 6)))][:10]
    tjuefire = [a for a in validering if _modellrad(a, features.get((a.voyageid, 24)))][:10]
    inputs = [_ved_kutt(a, h)[0] for par in zip(seks, tjuefire) for a, h in zip(par, (6, 24))]
    naa = max(i.t_kutt for i in inputs)
    ut = prediktor.prediker(inputs, naa)
    assert [p.forklaring["horisont"] for p in ut] == [6, 24] * 10
    for inp, p in zip(inputs, ut):
        [enkelt] = prediktor.prediker([inp], naa)
        assert p == enkelt and p.forklaring["metode"] == "modell"
        assert p.forklaring["horisont"] == inp.horisont_timer == enkelt.forklaring["horisont"]


def test_grensen_gir_bare_modellens_featurekolonner():
    """Spec-beslutning 2: for hver rad i features.csv er nøklene nøyaktig artefaktets features, aldri fasit eller ankomst."""
    art = joblib.load(MODELL_DIR / "modell_6t.joblib")
    with open(FEATURES_CSV, newline="", encoding="utf-8") as f:
        rader = list(csv.DictReader(f))
    for r in rader:
        t_kutt = dt.datetime.fromisoformat(r["t_kutt_utc"].replace("Z", "+00:00"))
        inp = PrediksjonsInput(int(r["voyageid"]), 0, "", "", "Øvrige", t_kutt, int(r["horisont_timer"]), t_kutt)
        ut = featurer_ved_kutt(inp)
        assert list(ut) == art["features"]
        for k in ut:
            assert k not in FORBUDT and not k.endswith("_modellvalg")
            assert not k.startswith(("arrival", "avvik"))
        with pytest.raises(TypeError):
            ut["distanse_km"] = 0  # frossen
        assert featurer_ved_kutt(dataclasses.replace(inp, t_kutt=t_kutt - dt.timedelta(minutes=1))) is None
    with pytest.raises(TypeError):
        featurer_ved_kutt(last_utdrag(FIXTURE)[0])


def test_tilstand_er_lik_definert_f6():
    """Prediktoren ser ikke ``har_tilstand``; den leser fravær av tilstand som F6 = None. Det holder for hver rad."""
    with open(FEATURES_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            assert (r["har_tilstand"] == "1") == (r["i_sonen_ved_kutt"] != ""), r["voyageid"]


@pytest.mark.parametrize("felt, verdi, melding", [
    ("features_sha256", "0" * 64, "features_sha256"),
    ("offset_ovrige_min", 60.0, "offset_ovrige_min"),
    ("horisont", 6, "artefaktet er 6 t"),
    ("variant", "uten_f13_f14", "uten_f13_f14"),
    ("features", "omvendt", "featurelista"),
    ("features", "kortere", "featurelista"),
    ("historikk", "modellvalg", "historikk"),
])
def test_artefakt_som_ikke_stemmer_gir_valueerror(tmp_path, felt, verdi, melding):
    for h in (6, 24):
        art = joblib.load(MODELL_DIR / f"modell_{h}t.joblib")
        if h == 24:
            if verdi == "omvendt":
                verdi = art["features"][::-1]
            elif verdi == "kortere":
                verdi = art["features"][:-1]
            art[felt] = verdi
        joblib.dump(art, tmp_path / f"modell_{h}t.joblib")
    with pytest.raises(ValueError, match=melding):
        ModellPrediktor(tmp_path)


def test_manglende_artefakt_gir_valueerror(tmp_path):
    joblib.dump(joblib.load(MODELL_DIR / "modell_6t.joblib"), tmp_path / "modell_6t.joblib")
    with pytest.raises(ValueError, match="fant ikke modellartefaktet"):
        ModellPrediktor(tmp_path)


# --- Ekvivalens og uavhengighet ----------------------------------------------------------------


@pytest.mark.parametrize("h", [6, 24])
def test_lik_modellarmen_i_evaluer(prediktor, validering, features, h):
    """Valideringsradene ved kuttet: samme tid og varsel som ``evaluer.modell_prediksjoner`` med de endelige artefaktene."""
    artefakter, _ = ev.last_artefakter(MODELL_DIR, FEATURES_CSV, REPO_ROT / "data" / "utdrag" / "anlop.csv")
    baseline = ev.baseline_prediksjoner(validering, h)
    ref = ev.modell_prediksjoner(artefakter[h]["modell"], validering, features, h, baseline)
    inputs = [_ved_kutt(a, h)[0] for a in validering]
    ut = prediktor.prediker(inputs, max(i.t_kutt for i in inputs))
    assert len(ut) == len(ref)
    n_modell = 0
    for p in ut:
        r = ref[p.voyageid]
        assert p.predikert_ankomst == r.predikert_ankomst, p.voyageid
        assert p.forventet_forsinket == r.forventet_forsinket, p.voyageid
        assert (p.forklaring["metode"] == "modell") == (r.forklaring["metode"] == "modell")
        n_modell += p.forklaring["metode"] == "modell"
    assert n_modell > 400


def test_en_rad_paavirkes_ikke_av_en_annen(prediktor, validering, features, monkeypatch):
    rader = [a for a in validering if _modellrad(a, features.get((a.voyageid, 6)))][:2]
    a, b = rader
    naa = max(a.eta_reported, b.eta_reported) - dt.timedelta(hours=6)
    inputs = [_ved_kutt(a, 6)[0], _ved_kutt(b, 6)[0]]
    foer = prediktor.prediker(inputs, naa)

    ekte = modellmodul.featurer_ved_kutt

    def endret(inp):
        f = ekte(inp)
        if inp.voyageid == b.voyageid:
            return dict(f, distanse_km=f["distanse_km"] + 300.0, slakk_timer=-48.0, lengde_m=10.0)
        return f

    monkeypatch.setattr(modellmodul, "featurer_ved_kutt", endret)
    etter = prediktor.prediker(inputs, naa)
    assert etter[0] == foer[0]
    assert etter[1].forklaring["featurer"] != foer[1].forklaring["featurer"]
    assert etter[1].forklaring["predikert_avvik_min"] != foer[1].forklaring["predikert_avvik_min"]
    monkeypatch.undo()

    ny_fasit = dataclasses.replace(b, faktisk_ankomst=b.eta_reported + dt.timedelta(hours=9), status_in_area="ok")
    igjen = prediktor.prediker([_ved_kutt(a, 6)[0], _ved_kutt(ny_fasit, 6)[0]], naa)
    assert igjen == foer


def test_dashbordet_bruker_fortsatt_baselinen(monkeypatch):
    """Byttet er E2-S08: ``PREDIKTOR`` uten verdi gir fortsatt baselinen."""
    monkeypatch.delenv("PREDIKTOR", raising=False)
    assert isinstance(velg_prediktor(), BaselinePrediktor)
