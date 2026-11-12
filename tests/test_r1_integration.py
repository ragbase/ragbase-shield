"""R1 integration (owner: integrator): the CLI restore names what it could not restore (CL-31, CL-36).

Synthetic data only. Every name, company and number below is invented and is not from any evaluation corpus.
"""
from __future__ import annotations

import io
import sys

import pytest

from ragbase_shield import cli, service

TEXT = ("Madame Ombeline QUISTRAVEL contre la société VORDANEX SARL, représentée par "
        "M. Théodric PALUSKEVAN.\n")


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    for name in cli._AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    fake_home = tmp_path / "user-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    service.reset()
    yield
    service.reset()


@pytest.fixture
def dossier(tmp_path, capsys):
    folder = tmp_path / "Dossier Quistravel"
    folder.mkdir()
    (folder / "requete.txt").write_text(TEXT, encoding="utf-8")
    assert cli.main(["add", str(folder)]) == 0
    capsys.readouterr()
    return "DOSSIER_1"


def _restore(code: str, text: str, capsys, monkeypatch) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    rc = cli.main(["restore", "--dossier", code, "-"])
    out, err = capsys.readouterr()
    return rc, out, err


def _masked(code: str, capsys, monkeypatch) -> str:
    monkeypatch.setattr(sys, "stdin", io.StringIO(TEXT))
    assert cli.main(["mask", "--dossier", code]) == 0
    return capsys.readouterr()[0]


def test_cli_restore_names_generic_placeholders_with_counts(dossier, capsys, monkeypatch):
    masked = _masked(dossier, capsys, monkeypatch)
    rc, out, err = _restore(dossier, masked + " Voir [SOCIETE], [SOCIETE] et [PERSONNE].", capsys, monkeypatch)
    assert rc == 0 and "QUISTRAVEL" in out
    line = next(ln for ln in err.splitlines() if "Marques génériques" in ln)
    assert "[SOCIETE] x2" in line and "[PERSONNE]" in line and "[PERSONNE] x" not in line


def test_cli_restore_names_shield_ids_without_a_local_name(dossier, capsys, monkeypatch):
    rc, out, err = _restore(dossier, "Pièce DOC_917 et sortie OUTPUT_63, encore DOC_917.", capsys, monkeypatch)
    assert rc == 0
    line = next(ln for ln in err.splitlines() if "Identifiants Shield" in ln)
    # the service lists each Shield id once (placeholders are listed per occurrence)
    assert "DOC_917" in line and "OUTPUT_63" in line and "DOC_917 x" not in line


def test_cli_restore_of_a_clean_text_prints_neither_line(dossier, capsys, monkeypatch):
    masked = _masked(dossier, capsys, monkeypatch)
    rc, out, err = _restore(dossier, masked, capsys, monkeypatch)
    assert rc == 0 and "PALUSKEVAN" in out
    assert "Marques génériques" not in err and "Identifiants Shield" not in err


def test_count_list_keeps_first_seen_order():
    assert cli._count_list(["[ADRESSE]", "DOC_8", "[ADRESSE]", "[ADRESSE]"]) == "[ADRESSE] x3, DOC_8"
    assert cli._count_list(["OUTPUT_2"]) == "OUTPUT_2"
    assert cli._count_list([]) == ""
