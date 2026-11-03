"""Tester for scripts/lag_utdrag.py (E1-S02) og det committede utdraget i data/."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import lag_utdrag

REPO_ROT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROT / "tests" / "fixtures" / "pipeline_mini.csv"
KOLONNER = [
    "voyageid", "mmsino", "shipname", "ship_group",
    "eta_reported", "arrival_in_area_utc", "status_in_area", "split",
]


def kjor(kilde, ut_dir, laget="2026-10-22"):
    return lag_utdrag.main(["--kilde", str(kilde), "--ut-dir", str(ut_dir), "--laget", laget])


def les_csv(sti):
    with open(sti, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def les_json(sti):
    with open(sti, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def utdrag(tmp_path):
    assert kjor(FIXTURE, tmp_path) == 0
    return tmp_path


def test_kolonner_og_rekkefolge(utdrag):
    with open(utdrag / "utdrag" / "anlop.csv", encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    assert header == KOLONNER
    rader = les_csv(utdrag / "utdrag" / "anlop.csv")
    # Sortert kronologisk på eta_reported, verdier uendret fra kilden.
    assert [r["voyageid"] for r in rader] == [str(1001 + i) for i in range(10)]
    assert rader[0]["eta_reported"] == "2025-01-01T01:00:00+00:00"
    assert rader[0]["arrival_in_area_utc"] == "2025-01-01T00:50:00"
    assert rader[7]["shipname"] == "TEST ÅTTE"


def test_splitt_8_2(utdrag):
    rader = les_csv(utdrag / "utdrag" / "anlop.csv")
    assert [r["split"] for r in rader] == ["train"] * 8 + ["test"] * 2
    assert {r["voyageid"] for r in rader if r["split"] == "test"} == {"1009", "1010"}


def test_baseline_offset_og_metadata(utdrag):
    baseline = les_json(utdrag / "baseline.json")
    # Passasjer train ok/ok: 10, 20, 40 -> 20 (1004 utelatt: status_in_area).
    # Øvrige train ok/ok: 30, 50, 60 -> 50 (1008 utelatt: status_at_quay). Test-rader (1000) teller ikke.
    assert baseline["offset_minutter"] == {"Passasjer": 20.0, "Øvrige": 50.0}
    assert baseline["test_fra_utc"] == "2025-01-01T09:00:00Z"
    assert baseline["kilde"] == "tests/fixtures/pipeline_mini.csv"
    assert baseline["kilde_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert baseline["laget"] == "2026-10-22"
    tekst = (utdrag / "baseline.json").read_text(encoding="utf-8")
    assert "Øvrige" in tekst and tekst.endswith("}\n")


def test_percentile_interpolerer_som_pipelinen():
    assert lag_utdrag.percentile([10.0, 20.0, 40.0, 45.0], 0.5) == 30.0
    assert lag_utdrag.percentile([7.0], 0.5) == 7.0


def test_gruppe_uten_train_rader_gir_null(tmp_path):
    tekst = FIXTURE.read_text(encoding="utf-8").replace(",Passasjer,", ",Last,")
    kilde = tmp_path / "uten_passasjer.csv"
    kilde.write_text(tekst, encoding="utf-8")
    assert kjor(kilde, tmp_path / "ut") == 0
    baseline = les_json(tmp_path / "ut" / "baseline.json")
    assert baseline["offset_minutter"]["Passasjer"] is None
    assert '"Passasjer": null' in (tmp_path / "ut" / "baseline.json").read_text(encoding="utf-8")


def test_deterministisk(tmp_path):
    assert kjor(FIXTURE, tmp_path / "a") == 0
    assert kjor(FIXTURE, tmp_path / "b") == 0
    for navn in ("utdrag/anlop.csv", "baseline.json"):
        assert (tmp_path / "a" / navn).read_bytes() == (tmp_path / "b" / navn).read_bytes()
    assert b"\r\n" not in (tmp_path / "a" / "utdrag" / "anlop.csv").read_bytes()


def test_manglende_kilde_feiler_uten_filer(tmp_path):
    mangler = tmp_path / "finnes_ikke.csv"
    ut = tmp_path / "ut"
    res = subprocess.run(
        [sys.executable, str(REPO_ROT / "scripts" / "lag_utdrag.py"),
         "--kilde", str(mangler), "--ut-dir", str(ut)],
        capture_output=True, text=True,
    )
    assert res.returncode != 0
    assert str(mangler) in res.stderr
    assert "derive_arrivals.py" in res.stderr
    assert not ut.exists()


def test_committet_utdrag_og_baseline():
    """Akseptanse: det committede data/ gir 6 260/1 566 og 44,8/64,2 uten pipeline/data/."""
    rader = les_csv(REPO_ROT / "data" / "utdrag" / "anlop.csv")
    assert list(rader[0].keys()) == KOLONNER
    assert len(rader) == 7826
    assert sum(r["split"] == "train" for r in rader) == 6260
    assert sum(r["split"] == "test" for r in rader) == 1566
    baseline = les_json(REPO_ROT / "data" / "baseline.json")
    assert round(baseline["offset_minutter"]["Passasjer"], 1) == 44.8
    assert round(baseline["offset_minutter"]["Øvrige"], 1) == 64.2
    assert baseline["test_fra_utc"] == "2025-09-14T03:15:00Z"
    forste_test = next(r for r in rader if r["split"] == "test")
    assert forste_test["eta_reported"] == "2025-09-14T03:15:00+00:00"


def test_samme_splitt_og_offset_som_pipelinen(tmp_path):
    """7 rader gir 7 * 0.8 = 5.6 -> 5 train / 2 test (round/ceil ville gitt 6); låser trunkeringen mot derive_arrivals.py."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "derive_arrivals", REPO_ROT / "pipeline" / "derive_arrivals.py")
    derive_arrivals = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(derive_arrivals)

    linjer = FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True)
    kilde = tmp_path / "sju_rader.csv"
    kilde.write_text("".join(linjer[:8]), encoding="utf-8")  # header + 7 rader
    with open(kilde, encoding="utf-8", newline="") as f:
        rader = list(csv.DictReader(f))
    assert len(rader) == 7

    p_offset, p_train, p_test = derive_arrivals.compute_offsets_and_split(rader)
    v_offset, v_train, v_test = lag_utdrag.splitt_og_offset(rader)

    assert len(v_train) == 5 and len(v_test) == 2
    assert [r["voyageid"] for r in v_train] == [r["voyageid"] for r in p_train]
    assert [r["voyageid"] for r in v_test] == [r["voyageid"] for r in p_test]
    assert v_offset == {"Passasjer": p_offset["Passasjer"], "Øvrige": p_offset["Non-Passasjer"]}
