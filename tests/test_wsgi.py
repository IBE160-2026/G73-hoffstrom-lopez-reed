"""Inngangspunktet for produksjon (E0-S21, arkitektur §11).

- ``wsgi.app`` er appen fra ``create_app()`` uten konfigurasjon, og ``pyproject.toml`` peker Vercel dit.
- Appen skriver ingenting til disk når den svarer, også når modellartefaktene lastes (Vercel har et
  skrivebeskyttet filsystem). Modellen kjøres bare på valideringsvinduet (regelen om testrader).
"""
import builtins
import importlib
import io
import os
import pathlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from conftest import VALIDERING_NAA

from app import create_app

REPO_ROT = Path(__file__).resolve().parent.parent


def test_pyproject_peker_paa_wsgi_app():
    tekst = (REPO_ROT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^\[tool\.vercel\]\s*\nentrypoint = "wsgi:app"\s*$', tekst, re.M)
    assert not re.search(r"^\[project\]", tekst, re.M)  # avhengighetene skal komme fra requirements.txt


def test_python_versjonen_er_312():
    """numpy 2.0.2 har ingen hjul for 3.13, så Vercel må bruke 3.12 (arkitektur §11)."""
    assert (REPO_ROT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"


def test_wsgi_app_er_create_app_uten_konfigurasjon():
    import wsgi

    wsgi = importlib.reload(wsgi)
    ref = create_app()
    assert wsgi.app.name == ref.name
    assert wsgi.app.config["STANDARD_NAA"] == ref.config["STANDARD_NAA"]
    assert not wsgi.app.config["TESTING"]
    assert sorted(r.rule for r in wsgi.app.url_map.iter_rules()) == sorted(r.rule for r in ref.url_map.iter_rules())
    svar = wsgi.app.test_client().get("/")
    assert svar.status_code == 200 and "anløp" in svar.get_data(as_text=True)


@pytest.fixture
def ingen_skriving(monkeypatch):
    """Alt som skriver til disk, feiler. Lesing er lov.

    ``sys.dont_write_bytecode`` slås på fordi pytest selv skriver om og cacher moduler som heter ``*_test.py`` når de
    importeres (scipys ``_page_trend_test.py`` importeres når modellen pakkes ut). Det er pytest, ikke appen. I
    produksjon lar Python være å skrive bytekode der det ikke går, uten feil, og Vercel kompilerer den på forhånd."""
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    def nekt(*_a, **_k):
        raise AssertionError("appen prøvde å skrive til disk")

    ekte_open = builtins.open

    def vaktet_open(fil, mode="r", *a, **k):
        if any(t in mode for t in "wax+"):
            nekt()
        return ekte_open(fil, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", vaktet_open)
    monkeypatch.setattr(io, "open", vaktet_open)
    for navn in ("write_text", "write_bytes", "mkdir", "touch", "unlink", "rename", "replace"):
        monkeypatch.setattr(pathlib.Path, navn, nekt)
    for modul, navn in ((os, "mkdir"), (os, "makedirs"), (os, "remove"), (os, "rename"), (os, "replace"),
                        (shutil, "copy"), (shutil, "copyfile"), (shutil, "move"), (tempfile, "mkstemp"),
                        (tempfile, "mkdtemp"), (tempfile, "NamedTemporaryFile"), (tempfile, "TemporaryDirectory")):
        monkeypatch.setattr(modul, navn, nekt)


def test_skriver_ikke_til_disk(ingen_skriving, monkeypatch):
    """Forsiden, stilarket og en ukjent side gir svar uten skriving, både med baselinen og med modellen."""
    import wsgi

    klient = wsgi.app.test_client()
    assert klient.get("/").status_code == 200
    assert klient.get("/static/style.css").status_code == 200
    assert klient.get("/finnes-ikke").status_code == 404

    import app.prediksjon as prediksjon
    from app.prediksjon import modell

    monkeypatch.setenv("PREDIKTOR", "modell")
    modell._last_artefakter.cache_clear()  # artefaktene lastes på nytt under vakten
    svar = create_app({"STANDARD_NAA": VALIDERING_NAA}).test_client().get("/")
    assert svar.status_code == 200
    tekst = svar.get_data(as_text=True)
    assert "Modell v1" in tekst, tekst[tekst.find("prediktor"):][:400]
    assert prediksjon.MODELL_DIR.is_dir()


def test_vakten_fanger_skriving(tmp_path, ingen_skriving):
    """Kontroll: vakten stopper faktisk en skriving, så en grønn test over betyr noe."""
    with pytest.raises(AssertionError, match="skrive til disk"):
        open(tmp_path / "x.txt", "w")
    with pytest.raises(AssertionError, match="skrive til disk"):
        (tmp_path / "y.txt").write_text("y")
