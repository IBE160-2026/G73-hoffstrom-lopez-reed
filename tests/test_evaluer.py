"""Evalueringsskriptet (E2-S06, PRD FR10, beslutning 11 og 12).

Baselinen på testperioden regnes på de committede utdragene, gjennom skriptets egne funksjoner, uten ``--test`` og uten
å røre ``metrikker.json``. Alt med modell bruker en syntetisk fixture i ``tmp_path``, med artefakter trent av
``scripts/tren.py``. Ingen test kjører ``--test``, og ingen test predikerer på testperioden med en modell. Den eneste
testen med ekte modell er valideringskjøringen med refit bare på treningsdelen (spec-beslutning 4). Git-vakta før
``--test`` (E2-S10) testes med git byttet ut og med alt som predikerer byttet ut med en funksjon som feiler.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import joblib
import pytest

from app.data import last_utdrag
from app.prediksjon.baseline import BASELINE_FIL
from tests.test_tren import _fixture, _skriv

REPO_ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("evaluer", REPO_ROT / "scripts" / "evaluer.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)
tren = ev.T

METRIKKER = REPO_ROT / "data" / "modell" / "metrikker.json"
UTDRAG = REPO_ROT / "data" / "utdrag"
ARMER = {"baseline", "modell", "ablasjon_uten_f13_f14", "varsle_alle"}


def _les(sti):
    return sti.read_bytes() if sti.is_file() else None


# --- Baselinen på de committede utdragene -----------------------------------------------------


def test_baseline_testperioden_lik_dataregresjonen():
    """464/996 og 343/431 ved begge horisontene (E1-S05), uten modell, uten ``--test`` og uten å skrive."""
    for_ = _les(METRIKKER)
    features = ev.les_features(UTDRAG / "features.csv")
    res = ev.evaluer(last_utdrag(), features, "test", artefakter=None)
    utvalg = {"6": ((433, 733), 0.735944), "24": ((418, 742), 0.74498)}
    for h in ("6", "24"):
        b = res["horisonter"][h]
        assert (b["ovrige_alle"]["baseline"]["treff_30"], b["ovrige_alle"]["baseline"]["n"]) == (464, 996)
        assert (b["passasjer"]["baseline"]["treff_30"], b["passasjer"]["baseline"]["n"]) == (343, 431)
        m = b["ovrige_modellutvalg"]["baseline"]
        assert ((m["treff_30"], m["n"]), b["andel_modellutvalg"]["med_fasit"]) == utvalg[h]
        assert set(b["ovrige_alle"]) == {"baseline", "varsle_alle"}
        assert b["ovrige_alle"]["varsle_alle"]["n"] == 996
        assert b["ovrige_alle"]["baseline"]["varsel"]["f1"] is None
    assert _les(METRIKKER) == for_
    committet = json.loads(for_)["test_bare_baseline"]
    assert {k: v for k, v in committet.items() if k != "kilder"} == res


def test_validering_modellarm_er_holdt_ute():
    """Spec-beslutning 4: refit på trening alene gir nøyaktig andelen fra modellvalget (69,1 % / 59,8 %)."""
    modell_dir = REPO_ROT / "data" / "modell"
    valg = json.loads((modell_dir / "modellvalg.json").read_text(encoding="utf-8"))
    artefakter, _ = ev.last_artefakter(modell_dir, UTDRAG / "features.csv", UTDRAG / "anlop.csv")
    refit = ev.refit_modellvalg(artefakter, valg, UTDRAG / "features.csv", UTDRAG / "anlop.csv")
    res = ev.evaluer(last_utdrag(), ev.les_features(UTDRAG / "features.csv"), "validering", refit)
    for h, forventet in (("6", 0.690632), ("24", 0.597778)):
        v = valg["horisonter"][h]
        assert v["kandidater"][v["valgt"]]["andel_30"] == forventet
        assert res["horisonter"][h]["ovrige_modellutvalg"]["modell"]["andel_30"] == forventet


def test_split_sjekkes_begge_veier(fixture):
    features = ev.les_features(fixture / "features.csv")
    anlop = last_utdrag(fixture / "anlop.csv")
    vid = next(a.voyageid for a in anlop if a.split == "test")
    uten = {k: r for k, r in features.items() if k[0] != vid}
    with pytest.raises(ev.Avvik, match=str(vid)):
        ev.anlop_i_split(anlop, uten, "test")
    vid_va = next(k[0] for k, r in features.items() if r["del"] == "validering")
    feil = {k: (dict(r, **{"del": "test"}) if k[0] == vid_va else r) for k, r in features.items()}
    with pytest.raises(ev.Avvik, match=str(vid_va)):
        ev.anlop_i_split(anlop, feil, "test")


# --- Syntetisk fixture med trente artefakter --------------------------------------------------


@pytest.fixture(scope="module")
def fixture(tmp_path_factory):
    mappe = tmp_path_factory.mktemp("evaluer")
    anlop, features = _fixture()
    # Sørg for minst ett valideringsanløp i ankomstsonen ved kuttet (F6), så delegeringen av F6 testes.
    f6 = next(r["voyageid"] for r in features if r["del"] == "validering" and r["gruppe"] == "Øvrige"
              and r["har_tilstand"] == "1" and r["fart_knop"])
    for r in features:
        if r["voyageid"] == f6:
            r.update(distanse_km="5.000", i_sonen_ved_kutt="1")
    _skriv(mappe, anlop, features)
    # Den committede baseline.json: BaselinePrediktor leser den, og artefaktene må ha samme sha256.
    assert tren.main(["--features", str(mappe / "features.csv"), "--anlop", str(mappe / "anlop.csv"),
                      "--baseline", str(BASELINE_FIL), "--ut-dir", str(mappe / "modell")]) == 0
    return mappe


def _args(mappe, ut, *ekstra, modell_dir=None):
    return [*ekstra, "--features", str(mappe / "features.csv"), "--anlop", str(mappe / "anlop.csv"),
            "--modell-dir", str(modell_dir or mappe / "modell"), "--ut", str(ut)]


@pytest.fixture(scope="module")
def validert(fixture, tmp_path_factory):
    ut = tmp_path_factory.mktemp("ut") / "metrikker.json"
    assert ev.main(_args(fixture, ut)) == 0
    return fixture, ut, json.loads(ut.read_text(encoding="utf-8"))


def _prediksjoner(mappe, h):
    artefakter, _ = ev.last_artefakter(mappe / "modell", mappe / "features.csv", mappe / "anlop.csv")
    features = ev.les_features(mappe / "features.csv")
    anlop = ev.anlop_i_split(last_utdrag(mappe / "anlop.csv"), features, "validering")
    baseline = ev.baseline_prediksjoner(anlop, h)
    modell = ev.modell_prediksjoner(artefakter[h]["modell"], anlop, features, h, baseline)
    return anlop, features, baseline, modell


@pytest.mark.parametrize("h", ev.HORISONTER)
def test_delegering(fixture, h):
    """Passasjer, uten tilstand og F6 = 1 får baselinens prediksjon og ingen varsel; modellutvalget får modellen."""
    anlop, features, baseline, modell = _prediksjoner(fixture, h)
    typer = set()
    for a in anlop:
        rad = features.get((a.voyageid, h))
        p = modell[a.voyageid]
        if ev.i_modellutvalg(a, rad):
            typer.add("modell")
            assert p.forklaring["metode"] == "modell"
            assert isinstance(p.forventet_forsinket, bool)
            assert p.forventet_forsinket == (p.forklaring["predikert_avvik_min"] > 120)
            kalibrert = baseline[a.voyageid].predikert_ankomst
            avvik = (p.predikert_ankomst - kalibrert).total_seconds() / 60
            assert avvik == pytest.approx(p.forklaring["predikert_avvik_min"], abs=1e-6)
        else:
            typer.add("passasjer" if a.gruppe == "Passasjer" else ("f6" if ev.er_f6(rad) else "uten_tilstand"))
            assert p == baseline[a.voyageid]
            assert p.forventet_forsinket is None
    assert typer == {"modell", "passasjer", "f6", "uten_tilstand"}


@pytest.mark.parametrize("h", ev.HORISONTER)
def test_modellutvalget_er_samme_rader_for_modell_og_baseline(fixture, h):
    anlop, features, baseline, modell = _prediksjoner(fixture, h)
    sett = ev.radsett(anlop, features, h)
    utvalg = {a.voyageid for a in sett["ovrige_modellutvalg"]}
    assert utvalg <= {a.voyageid for a in sett["ovrige_alle"]}
    assert utvalg == {v for v, p in modell.items() if p.forklaring["metode"] == "modell"}
    assert set(modell) == set(baseline) == {a.voyageid for a in anlop}


def test_samme_n_for_alle_armer_og_noklene(validert):
    _, _, data = validert
    assert data["testkjoringer"] == 0 and data["testkjoringer_logg"] == []
    assert "test" not in data and "test_bare_baseline" not in data
    for h in ("6", "24"):
        b = data["validering"]["horisonter"][h]
        for navn in ("ovrige_alle", "ovrige_modellutvalg"):
            assert set(b[navn]) == ARMER
            assert len({v["n"] for v in b[navn].values()}) == 1, navn
            assert b[navn]["baseline"]["varsel"]["presisjon"] is None
            assert b[navn]["modell"]["varsel"]["f1"] is not None
        assert set(b["passasjer"]) == {"baseline"}
        o = b["antall"]["ovrige"]
        assert b["ovrige_modellutvalg"]["baseline"]["n"] == o["modellutvalg_med_fasit"]
        assert b["ovrige_alle"]["baseline"]["n"] == o["med_fasit"]
        assert o["modellutvalg"] + o["f6"] == o["med_tilstand"]
        assert b["andel_modellutvalg"] == {"alle_rader": round(o["modellutvalg"] / o["rader"], 6),
                                           "med_fasit": round(o["modellutvalg_med_fasit"] / o["med_fasit"], 6)}


def test_validering_beholder_testblokken_og_er_deterministisk(fixture, tmp_path):
    ut = tmp_path / "metrikker.json"
    test_blokk = {"split": "test", "horisonter": {"6": {"x": 1}}}
    ut.write_text(json.dumps({"test": test_blokk, "testkjoringer": 1,
                              "testkjoringer_logg": [{"nr": 1, "dato": "2026-11-20"}]}), encoding="utf-8")
    assert ev.main(_args(fixture, ut)) == 0
    forste = ut.read_bytes()
    data = json.loads(forste)
    assert data["test"] == test_blokk
    assert data["testkjoringer"] == 1 and data["testkjoringer_logg"] == [{"nr": 1, "dato": "2026-11-20"}]
    assert data["validering"]["split"] == "validering"
    assert ev.main(_args(fixture, ut)) == 0
    assert ut.read_bytes() == forste


HASH_A, HASH_B = "a" * 40, "b" * 40


def test_testkjoring_teller_og_logger_dato_og_commit():
    """Bokføringen for ``--test``, uten å kjøre ``--test``. Loggen har ``{nr, dato, commit}`` (E2-S10)."""
    en = ev.oppdater(None, "test", {"split": "test"}, "2026-11-20", commit=HASH_A)
    assert en["testkjoringer"] == 1
    assert en["testkjoringer_logg"] == [{"nr": 1, "dato": "2026-11-20", "commit": HASH_A}]
    to = ev.oppdater(en, "test", {"split": "test"}, "2026-11-21", ny_testkjoring=True, commit=HASH_B)
    assert to["testkjoringer"] == 2 and [x["dato"] for x in to["testkjoringer_logg"]] == ["2026-11-20", "2026-11-21"]
    assert [x["commit"] for x in to["testkjoringer_logg"]] == [HASH_A, HASH_B]
    with pytest.raises(ev.Avvik, match="--ny-testkjoring"):
        ev.oppdater(to, "test", {"split": "test"}, "2026-11-22", commit=HASH_B)
    va = ev.oppdater(to, "validering", {"split": "validering"})
    assert va["testkjoringer"] == 2 and va["test"] == {"split": "test"}
    assert ev.oppdater(va, "test_bare_baseline", {})["testkjoringer"] == 2
    with pytest.raises(ValueError, match="dato"):
        ev.oppdater(None, "test", {}, commit=HASH_A)
    with pytest.raises(ValueError, match="commit"):
        ev.oppdater(None, "test", {}, "2026-11-20")


# --- Git-vakta før --test (E2-S10, krav 1). Syntetisk: git er byttet ut, og ingenting predikeres. ----------


def _falsk_git(status="", head=HASH_A, upstream=HASH_A, feil=None):
    def git(*args):
        if feil is not None:
            raise feil
        return {("status", "--porcelain"): status, ("rev-parse", "HEAD"): head,
                ("rev-parse", "@{u}"): upstream}[args]
    return git


def test_sjekk_git_gir_full_hash_naar_rent_og_pushet(monkeypatch):
    monkeypatch.setattr(ev, "git", _falsk_git())
    assert ev.sjekk_git() == HASH_A


@pytest.mark.parametrize("git, grunn", [
    (_falsk_git(status=" M scripts/evaluer.py"), "ikke rent"),
    (_falsk_git(status="?? ny_fil.txt"), "ikke rent"),
    (_falsk_git(upstream=HASH_B), "Push"),
    (_falsk_git(feil=FileNotFoundError("git")), "git er ikke tilgjengelig"),
    (_falsk_git(feil=ev.subprocess.CalledProcessError(128, ["git"], stderr="no upstream configured")),
     "no upstream"),
], ids=["endret", "usporet", "ikke_pushet", "uten_git", "uten_upstream"])
def test_test_uten_ren_pushet_git_stopper_for_noe_predikeres(fixture, tmp_path, monkeypatch, capsys, git, grunn):
    """``--test`` stopper med «ingenting er skrevet» før artefakter lastes eller noe predikeres, og fila er urørt."""
    def nekt(*a, **k):
        raise AssertionError("--test gikk forbi git-vakta")

    monkeypatch.setattr(ev, "git", git)
    for navn in ("last_artefakter", "evaluer", "baseline_prediksjoner", "modell_prediksjoner"):
        monkeypatch.setattr(ev, navn, nekt)
    ut = tmp_path / "metrikker.json"
    innhold = json.dumps({"testkjoringer": 0, "testkjoringer_logg": []})
    ut.write_text(innhold, encoding="utf-8")
    assert ev.main(_args(fixture, ut, "--test")) == 2
    assert ut.read_text(encoding="utf-8") == innhold
    err = capsys.readouterr().err
    assert "ingenting er skrevet" in err and grunn in err


def test_test_allerede_kjort_stopper(fixture, tmp_path, monkeypatch, capsys):
    """Med ``testkjoringer ≥ 1`` nektes ``--test`` som før, også når git er rent, og ingenting predikeres."""
    def nekt(*a, **k):
        raise AssertionError("--test predikerte etter en tidligere testkjøring")

    monkeypatch.setattr(ev, "git", _falsk_git())
    monkeypatch.setattr(ev, "evaluer", nekt)
    ut = tmp_path / "metrikker.json"
    innhold = json.dumps({"testkjoringer": 1, "testkjoringer_logg": [{"nr": 1, "dato": "2026-11-20",
                                                                      "commit": HASH_A}]})
    ut.write_text(innhold, encoding="utf-8")
    assert ev.main(_args(fixture, ut, "--test")) == 2
    assert ut.read_text(encoding="utf-8") == innhold
    assert "--ny-testkjoring" in capsys.readouterr().err


def test_vakta_gjelder_bare_test(fixture, tmp_path, monkeypatch):
    """Validering og ``--bare-baseline`` spør ikke git."""
    def nekt(*a, **k):
        raise AssertionError("git kalt utenfor --test")

    monkeypatch.setattr(ev, "git", nekt)
    assert ev.main(_args(fixture, tmp_path / "a.json", "--bare-baseline")) == 0


def test_artefakt_mot_feil_utdrag_stopper_uten_a_skrive(fixture, tmp_path, capsys):
    mappe = tmp_path / "endret"
    shutil.copytree(fixture, mappe)
    with open(mappe / "features.csv", "a", encoding="utf-8") as f:
        f.write("\n")
    ut = tmp_path / "metrikker.json"
    assert ev.main(_args(mappe, ut)) == 2
    assert not ut.exists()
    assert "features_sha256" in capsys.readouterr().err


def test_bare_baseline_laster_ingen_modell(fixture, tmp_path, monkeypatch):
    def nekt(*a, **k):
        raise AssertionError("--bare-baseline lastet en modellartefakt")

    monkeypatch.setattr(joblib, "load", nekt)
    monkeypatch.setattr(ev, "last_artefakter", nekt)
    monkeypatch.setattr(ev.T, "prediker", nekt)
    ut = tmp_path / "metrikker.json"
    assert ev.main(_args(fixture, ut, "--bare-baseline", modell_dir=tmp_path / "finnes_ikke")) == 0
    data = json.loads(ut.read_text(encoding="utf-8"))
    assert data["testkjoringer"] == 0 and "test" not in data
    blokk = data["test_bare_baseline"]
    assert blokk["split"] == "test"
    for b in blokk["horisonter"].values():
        assert set(b["ovrige_alle"]) == set(b["ovrige_modellutvalg"]) == {"baseline", "varsle_alle"}
        assert set(b["passasjer"]) == {"baseline"}
        assert "andel_modellutvalg" in b
