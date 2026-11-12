"""Tests for ragbase_shield.vault. Synthetic data only (invented names)."""
from __future__ import annotations

import os
import stat
import sys
import threading
import types
from pathlib import Path

import pytest

from ragbase_shield import config
from ragbase_shield import vault as V
from ragbase_shield.engine.types import CODE_RE, Entity
from ragbase_shield.vault import DocRef, Registry, UnknownDossier, VaultError

PERSON = "Hélène Garnier-Vasseur"
PERSON2 = "Jules Morvandiau"
PERSON3 = "Capucine Delaroche-Ybert"
COMPANY = "Lambretti Conseil SAS"
EMAIL = "jules.morvandiau@exemple-fictif.fr"
TITLE = "Garnier-Vasseur c. Lambretti Conseil"
PASS = "phrase de passe fictive 2026"


@pytest.fixture
def folder(tmp_path) -> Path:
    f = tmp_path / "Clients" / "Affaire Garnier-Vasseur"
    f.mkdir(parents=True)
    return f


@pytest.fixture
def reg():
    r = Registry()
    yield r
    r.close()


def _all_bytes(root: Path) -> bytes:
    data = b""
    for p in sorted(root.rglob("*")):
        if p.is_file():
            data += p.read_bytes()
    return data


def _variants(value: str) -> list[bytes]:
    return [value.encode("utf-8"), value.encode("utf-16-le"), value.lower().encode("utf-8")]


# --------------------------------------------------------------------------- registry basics

def test_add_list_get_dossiers(reg, folder, tmp_path):
    other = tmp_path / "Autre"
    other.mkdir()
    d1 = reg.add_dossier(folder, title=TITLE)
    d2 = reg.add_dossier(other)
    assert (d1.code, d2.code) == ("DOSSIER_1", "DOSSIER_2")
    assert d1.title == TITLE and d1.folder == folder.resolve()
    assert d2.title == "Autre"
    assert reg.add_dossier(folder) is d1  # same folder: same dossier
    assert [d.code for d in reg.list()] == ["DOSSIER_1", "DOSSIER_2"]
    assert reg.get("dossier_1") is d1 and reg.get(" DOSSIER_2 ") is d2
    assert TITLE not in repr(d1) and str(folder) not in repr(d1)
    assert repr(d1) == "Dossier(DOSSIER_1)"
    assert d1.locale == "fr"


def test_unknown_dossier_and_bad_folder_messages_hold_no_real_value(reg, folder, tmp_path):
    reg.add_dossier(folder, title=TITLE)
    with pytest.raises(UnknownDossier) as exc:
        reg.get("DOSSIER_99")
    assert isinstance(exc.value, KeyError)
    assert str(exc.value).startswith("DOSSIER_99")
    with pytest.raises(UnknownDossier):
        reg.get("Garnier")
    missing = tmp_path / "Dossier Morvandiau inexistant"
    with pytest.raises(VaultError) as exc2:
        reg.add_dossier(missing)
    assert "Morvandiau" not in str(exc2.value)
    a_file = tmp_path / "Morvandiau.txt"
    a_file.write_text("x")
    with pytest.raises(VaultError) as exc3:
        reg.add_dossier(a_file)
    assert "Morvandiau" not in str(exc3.value)


def test_registry_files_are_private(reg, folder):
    reg.add_dossier(folder)
    home = config.home()
    if os.name == "posix":
        assert stat.S_IMODE((home / "key").stat().st_mode) == 0o600
        assert stat.S_IMODE((home / "registry.db").stat().st_mode) == 0o600
        for p in (home / "vaults").iterdir():
            assert stat.S_IMODE(p.stat().st_mode) & 0o077 == 0
        assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert reg.key_source == "file"


# --------------------------------------------------------------------------- codes

def test_code_allocation_order_and_stability(reg, folder):
    d = reg.add_dossier(folder)
    a = d.add("PERSON", PERSON, V.normalize(PERSON))
    b = d.add("PERSON", PERSON2, V.normalize(PERSON2))
    s = d.add("ORG", COMPANY, V.normalize(COMPANY))
    e1 = d.add("EMAIL", EMAIL, EMAIL)
    c = d.add("PERSON", PERSON3, V.normalize(PERSON3))
    e2 = d.add("EMAIL", "h.garnier@exemple-fictif.fr", "h.garnier@exemple-fictif.fr")
    assert [x.code for x in (a, b, s, e1, c, e2)] == [
        "PERSONNE_A", "PERSONNE_B", "SOCIETE_A", "EMAIL_1", "PERSONNE_C", "EMAIL_2"]
    assert d.add("PERSON", "HELENE garnier-vasseur", V.normalize(PERSON)) == a  # same norm, same code
    assert d.get_by_code("SOCIETE_A") == s
    assert d.get_by_norm("PERSON", V.normalize(PERSON2)) == b
    assert d.get_by_norm("ORG", V.normalize(PERSON2)) is None
    assert [x.code for x in d.all()] == ["PERSONNE_A", "PERSONNE_B", "SOCIETE_A", "EMAIL_1", "PERSONNE_C", "EMAIL_2"]
    assert all(isinstance(x, Entity) for x in d.all())
    reg.close()

    reg2 = Registry()
    d2 = reg2.get("DOSSIER_1")
    assert d2.get_by_code("PERSONNE_A").value == PERSON
    assert d2.add("PERSON", "Ondine Prat-Kerhoas", "ondine prat-kerhoas").code == "PERSONNE_D"
    assert d2.add("EMAIL", "o.prat@exemple-fictif.fr", "o.prat@exemple-fictif.fr").code == "EMAIL_3"
    reg2.close()


def test_letter_codes_continue_after_z(reg, folder):
    d = reg.add_dossier(folder)
    codes = [d.add("PERSON", f"Personne Fictive {i}", f"personne fictive {i}").code for i in range(28)]
    assert codes[0] == "PERSONNE_A" and codes[25] == "PERSONNE_Z"
    assert codes[26] == "PERSONNE_AA" and codes[27] == "PERSONNE_AB"
    assert all(CODE_RE.fullmatch(c) for c in codes)


def test_locale_is_fixed_per_dossier(folder, tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_LOCALE", "en")
    r = Registry()
    d = r.add_dossier(folder)
    assert d.locale == "en"
    assert d.add("PERSON", PERSON, V.normalize(PERSON)).code == "PERSON_A"
    assert d.add("ORG", COMPANY, V.normalize(COMPANY)).code == "COMPANY_A"
    r.close()
    monkeypatch.setenv("RAGBASE_SHIELD_LOCALE", "fr")
    r2 = Registry()
    d2 = r2.get("DOSSIER_1")
    assert d2.locale == "en"
    assert d2.add("PERSON", PERSON2, V.normalize(PERSON2)).code == "PERSON_B"
    other = tmp_path / "fr"
    other.mkdir()
    assert r2.add_dossier(other).add("PERSON", PERSON, V.normalize(PERSON)).code == "PERSONNE_A"
    r2.close()


def test_add_validates_input(reg, folder):
    d = reg.add_dossier(folder)
    with pytest.raises(ValueError):
        d.add("NOT_A_KIND", "x", "x")
    with pytest.raises(ValueError):
        d.add("PERSON", "  ", "x")
    with pytest.raises(ValueError):
        d.add("PERSON", "x", "")


# --------------------------------------------------------------------------- register / keep clear

def test_register_normalises_case_accents_spaces(reg, folder):
    d = reg.add_dossier(folder)
    a = d.register("PERSON", "  Hélène   GARNIER-VASSEUR ")
    assert a.code == "PERSONNE_A"
    assert a.value == "Hélène GARNIER-VASSEUR"
    assert a.norm == "helene garnier-vasseur"
    assert d.register("PERSON", "helene garnier-vasseur").code == "PERSONNE_A"
    assert d.register("PERSON", "HÉLÈNE Garnier-Vasseur").code == "PERSONNE_A"
    assert d.register("ORG", COMPANY).code == "SOCIETE_A"
    assert d.entity_source("PERSONNE_A") == "user"
    assert d.add("PERSON", PERSON2, V.normalize(PERSON2)).code == "PERSONNE_B"
    assert d.entity_source("PERSONNE_B") == "detected"
    with pytest.raises(ValueError):
        d.register("PERSON", "   ")
    with pytest.raises(ValueError):
        d.register("ALIEN", "x")


def test_local_normalizer():
    assert V._local_normalize("  Ægir   Œuvre  L’Étoile ") == "aegir oeuvre l'etoile"
    assert V._local_normalize("ÇA VA") == "ca va"


def test_keep_clear_by_code_and_by_term_persists(reg, folder):
    d = reg.add_dossier(folder)
    a = d.register("PERSON", PERSON)
    assert not d.is_kept_clear(a.norm)
    d.keep_clear("PERSONNE_A")
    assert d.is_kept_clear(a.norm)
    d.keep_clear("Tribunal de Commerce de Saint-Fictif")
    assert d.is_kept_clear("tribunal de commerce de saint-fictif")
    with pytest.raises(VaultError) as exc:
        d.keep_clear("PERSONNE_Z")
    assert "PERSONNE_Z" in str(exc.value)
    reg.close()
    r2 = Registry()
    d2 = r2.get("DOSSIER_1")
    assert d2.is_kept_clear(a.norm)
    assert d2.is_kept_clear("tribunal de commerce de saint-fictif")
    assert sorted(d2.kept_clear_terms()) == ["helene garnier-vasseur", "tribunal de commerce de saint-fictif"]
    d2.keep_clear("PERSONNE_A", False)
    assert not d2.is_kept_clear(a.norm)
    r2.close()


# --------------------------------------------------------------------------- encryption at rest

def test_real_values_norms_titles_and_paths_are_encrypted_at_rest(reg, folder):
    (folder / "Conclusions Garnier-Vasseur.docx").write_bytes(b"x")
    d = reg.add_dossier(folder, title=TITLE)
    d.register("PERSON", PERSON)
    d.register("ORG", COMPANY)
    d.add("EMAIL", EMAIL, EMAIL)
    d.keep_clear("Ville de Bourg-Fictif-sur-Loire")
    assert len(d.documents()) == 1
    d.register_output(folder / "Shield - sorties" / "Note Morvandiau.docx")
    d.journal("mask", persons=2)
    reg.close()

    data = _all_bytes(config.home())
    assert data  # the files exist
    secrets = [PERSON, V.normalize(PERSON), COMPANY, V.normalize(COMPANY), EMAIL, TITLE,
               "bourg-fictif-sur-loire", "Conclusions Garnier-Vasseur", "Note Morvandiau",
               str(folder), folder.name, "Garnier", "Lambretti", "Morvandiau"]
    for secret in secrets:
        for variant in _variants(secret):
            assert variant not in data, f"found in clear: {secret!r}"
    assert b"PERSONNE_A" in data  # codes are not secret


# --------------------------------------------------------------------------- persistence

def test_persistence_across_registry_instances(reg, folder):
    (folder / "a.txt").write_text("x")
    d = reg.add_dossier(folder, title=TITLE)
    d.register("PERSON", PERSON)
    d.register("ORG", COMPANY)
    ids = [x.id for x in d.documents()]
    d.journal("scan", documents=1)
    reg.close()
    r2 = Registry()
    d2 = r2.get("DOSSIER_1")
    assert d2.title == TITLE and d2.folder == folder.resolve()
    assert [(e.code, e.value) for e in d2.all()] == [("PERSONNE_A", PERSON), ("SOCIETE_A", COMPANY)]
    assert [x.id for x in d2.documents()] == ids
    assert d2.journal_entries()[0]["event"] == "scan"
    r2.close()


def test_two_registries_share_state_like_two_processes(folder):
    r1, r2 = Registry(), Registry()
    d1 = r1.add_dossier(folder)
    d2 = r2.get("DOSSIER_1")
    a = d1.add("PERSON", PERSON, V.normalize(PERSON))
    b = d2.add("PERSON", PERSON2, V.normalize(PERSON2))  # sees A, allocates B
    assert (a.code, b.code) == ("PERSONNE_A", "PERSONNE_B")
    assert d1.add("PERSON", PERSON2, V.normalize(PERSON2)).code == "PERSONNE_B"  # cache refreshed
    assert d1.get_by_code("PERSONNE_B").value == PERSON2
    d2.keep_clear("PERSONNE_A")
    assert d1.is_kept_clear(a.norm)
    r1.close()
    r2.close()


def test_concurrent_adds_from_threads(reg, folder):
    d = reg.add_dossier(folder)
    names = [f"Personne Fictive {i}" for i in range(60)]
    results: list[Entity] = []
    lock = threading.Lock()

    def worker(chunk):
        for n in chunk:
            e = d.add("PERSON", n, n.lower())
            with lock:
                results.append(e)

    # every thread adds every name, in different orders
    threads = [threading.Thread(target=worker, args=(names[i::1] if i % 2 else names[::-1],)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = {e.norm: e.code for e in d.all()}
    assert len(codes) == 60 and len(set(codes.values())) == 60
    assert all(codes[e.norm] == e.code for e in results)


# --------------------------------------------------------------------------- documents

def _tree(folder: Path) -> None:
    (folder / "sub" / "deeper").mkdir(parents=True)
    (folder / ".git").mkdir()
    (folder / "Shield - sorties").mkdir()
    for rel in ("b.docx", "a.pdf", "e.eml", "f.html", "g.htm", "sub/c.txt", "sub/deeper/d.md",
                ".cache.txt", ".git/config.txt", "~$b.docx", "~WRL0001.tmp", "tableau.pptx",
                "Shield - sorties/sortie.docx", "brouillon.docx~"):
        (folder / rel).write_bytes(b"synthetic")


def test_documents_listing_skips_hidden_temp_output(reg, folder):
    _tree(folder)
    d = reg.add_dossier(folder)
    docs = d.documents()
    assert [x.rel for x in docs] == ["a.pdf", "b.docx", "e.eml", "f.html", "g.htm", "sub/c.txt", "sub/deeper/d.md"]
    assert [x.id for x in docs] == [f"DOC_{i}" for i in range(1, 8)]
    first = docs[0]
    assert isinstance(first, DocRef)
    assert first.path == folder.resolve() / "a.pdf" and first.name == "a.pdf"
    assert first.kind == "pdf" and first.size == len(b"synthetic")
    assert {x.kind for x in docs} == {"pdf", "docx", "eml", "html", "txt", "md"}
    assert "a.pdf" not in repr(first)


def test_documents_ignore_symlinks_leaving_the_folder(reg, folder, tmp_path):
    outside = tmp_path / "hors-dossier.txt"
    outside.write_text("x")
    (folder / "vrai.txt").write_text("x")
    try:  # Windows: a symlink needs the privilege (administrator or developer mode); without it, nothing to test
        (folder / "lien.txt").symlink_to(outside)
        (folder / "lien-interne.txt").symlink_to(folder / "vrai.txt")
    except OSError:
        pytest.skip("this account cannot create symlinks")
    d = reg.add_dossier(folder)
    assert sorted(x.rel for x in d.documents()) == ["lien-interne.txt", "vrai.txt"]


def test_document_ids_are_stable_and_never_reused(reg, folder):
    _tree(folder)
    d = reg.add_dossier(folder)
    before = {x.rel: x.id for x in d.documents()}
    assert {x.rel: x.id for x in d.documents()} == before
    reg.close()

    r2 = Registry()
    d2 = r2.get("DOSSIER_1")
    assert {x.rel: x.id for x in d2.documents()} == before
    (folder / "a.pdf").unlink()
    (folder / "0-nouveau.txt").write_text("x")
    after = {x.rel: x.id for x in d2.documents()}
    assert "a.pdf" not in after
    assert after["0-nouveau.txt"] == "DOC_8"  # next number, DOC_1 is not reused
    assert all(after[k] == v for k, v in before.items() if k != "a.pdf")
    assert d2.get_document("DOC_8").rel == "0-nouveau.txt"
    assert d2.get_document("doc_2").rel == "b.docx"
    assert d2.get_document("DOC_1") is None  # deleted file
    assert d2.get_document("DOC_999") is None
    assert d2.get_document("../../etc/passwd") is None
    r2.close()


def test_output_dir_created_on_demand_and_outputs(reg, folder):
    d = reg.add_dossier(folder)
    out = folder / config.OUTPUT_DIR_NAME
    assert not out.exists()
    assert d.output_dir() == folder.resolve() / config.OUTPUT_DIR_NAME
    assert out.is_dir()
    (out / "x.docx").write_bytes(b"x")
    assert d.documents() == []
    o1 = d.register_output(out / "x.docx")
    o2 = d.register_output(out / "y.md")
    assert (o1, o2) == ("OUTPUT_1", "OUTPUT_2")
    assert d.get_output("OUTPUT_1") == out / "x.docx"
    assert d.get_output("OUTPUT_9") is None and d.get_output("x") is None


def test_dossier_for_path(reg, folder, tmp_path):
    d = reg.add_dossier(folder)
    inner = folder / "sub"
    inner.mkdir()
    d_inner = reg.add_dossier(inner)
    assert reg.dossier_for_path(folder / "a.txt") is d
    assert reg.dossier_for_path(inner / "b.txt") is d_inner
    assert reg.dossier_for_path(tmp_path / "ailleurs.txt") is None


# --------------------------------------------------------------------------- journal

def test_journal_accepts_codes_and_numbers_only(reg, folder):
    d = reg.add_dossier(folder)
    d.register("PERSON", PERSON)
    d.journal("read_document", document="DOC_3", entities=4, ratio=0.5, ok=True,
              codes=["PERSONNE_A", "SOCIETE_B"], kinds={"PERSON": 2, "EMAIL": 1}, fmt="docx")
    entry = d.journal_entries()[0]
    assert entry["event"] == "read_document" and entry["dossier"] == "DOSSIER_1"
    assert entry["counts"]["document"] == "DOC_3" and entry["counts"]["kinds"] == {"PERSON": 2, "EMAIL": 1}
    assert "T" in entry["time"]

    bad_calls = [
        dict(name=PERSON),
        dict(note="client fictif"),
        dict(number_as_text="732829320"),
        dict(codes=["PERSONNE_A", PERSON]),
        dict(kinds={PERSON: 1}),
        dict(nested=[["PERSONNE_A"]]),
        dict(obj=object()),
        dict(value=float("nan")),
    ]
    for kwargs in bad_calls:
        with pytest.raises(ValueError) as exc:
            d.journal("mask", **kwargs)
        assert "Garnier" not in str(exc.value) and "732829320" not in str(exc.value)
    with pytest.raises(ValueError):
        d.journal("Garnier-Vasseur", n=1)
    with pytest.raises(ValueError):
        d.journal("mask", **{"Garnier": 1})
    assert len(d.journal_entries()) == 1
    reg.close()
    assert b"client fictif" not in _all_bytes(config.home())


def test_registry_journal_merges_dossier_events(reg, folder, tmp_path):
    d = reg.add_dossier(folder)
    other = tmp_path / "o"
    other.mkdir()
    d_other = reg.add_dossier(other)
    d.journal("mask", entities=3)
    d_other.journal("restore", restored=1)
    events = [(e["event"], e["dossier"]) for e in reg.journal_entries("DOSSIER_1")]
    assert events == [("mask", "DOSSIER_1"), ("dossier_added", "DOSSIER_1")]
    all_events = {(e["event"], e["dossier"]) for e in reg.journal_entries()}
    assert ("restore", "DOSSIER_2") in all_events and ("dossier_added", "DOSSIER_2") in all_events
    with pytest.raises(ValueError):
        reg.journal("x", dossier="Garnier")


# --------------------------------------------------------------------------- export / import

def _populated(reg, folder):
    (folder / "a.txt").write_text("x")
    (folder / "b.txt").write_text("x")
    d = reg.add_dossier(folder, title=TITLE)
    d.register("PERSON", PERSON)
    d.register("PERSON", PERSON2)
    d.add("PERSON", PERSON3, V.normalize(PERSON3))
    d.register("ORG", COMPANY)
    d.keep_clear("PERSONNE_B")
    d.keep_clear("Cour d'appel de Fictiville")
    d.documents()
    return d


def test_export_import_round_trip(reg, folder, tmp_path):
    d = _populated(reg, folder)
    export = d.export(tmp_path / "handoff.shield", PASS)
    raw = export.read_bytes()
    for secret in (PERSON, PERSON2, COMPANY, TITLE, "fictiville", str(folder)):
        for variant in _variants(secret):
            assert variant not in raw
    if os.name == "posix":
        assert stat.S_IMODE(export.stat().st_mode) == 0o600
    assert d.journal_entries()[0]["event"] == "export"

    colleague_folder = tmp_path / "copie-collegue"
    colleague_folder.mkdir()
    (colleague_folder / "a.txt").write_text("x")
    (colleague_folder / "b.txt").write_text("x")
    (colleague_folder / "c.txt").write_text("x")
    r2 = Registry(tmp_path / "colleague-home")  # other home: other master key
    assert (tmp_path / "colleague-home" / "key").read_bytes() != (config.home() / "key").read_bytes()
    imp = r2.import_(export, PASS, folder=colleague_folder)
    assert imp.code == "DOSSIER_1" and imp.title == TITLE and imp.locale == "fr"
    assert imp.folder == colleague_folder.resolve()
    assert [(e.code, e.kind, e.value, e.norm) for e in imp.all()] == \
        [(e.code, e.kind, e.value, e.norm) for e in d.all()]
    assert imp.is_kept_clear(V.normalize(PERSON2)) and imp.is_kept_clear("cour d'appel de fictiville")
    assert not imp.is_kept_clear(V.normalize(PERSON))
    assert imp.entity_source("PERSONNE_C") == "detected" and imp.entity_source("PERSONNE_A") == "user"
    docs = {x.rel: x.id for x in imp.documents()}
    assert docs == {"a.txt": "DOC_1", "b.txt": "DOC_2", "c.txt": "DOC_3"}
    assert imp.add("PERSON", "Ondine Prat-Kerhoas", "ondine prat-kerhoas").code == "PERSONNE_D"
    assert imp.register("ORG", "Fictiva Holding SARL").code == "SOCIETE_B"
    assert ("dossier_imported", "DOSSIER_1") in {(e["event"], e["dossier"]) for e in r2.journal_entries()}
    r2.close()


def test_import_default_folder(reg, folder, tmp_path):
    d = _populated(reg, folder)
    export = d.export(tmp_path / "h.shield", PASS)
    # same computer, original folder already registered: goes to <home>/imported/
    imp = reg.import_(export, PASS)
    assert imp.code == "DOSSIER_2"
    assert imp.folder.parent == config.home() / V.IMPORTED_DIR_NAME
    assert imp.get_by_code("PERSONNE_A").value == PERSON
    # other computer where the original folder exists and is free: uses it
    r2 = Registry(tmp_path / "h2")
    imp2 = r2.import_(export, PASS, title="Copie")
    assert imp2.folder == folder.resolve() and imp2.title == "Copie"
    with pytest.raises(VaultError):
        r2.import_(export, PASS, folder=folder)  # already registered there
    r2.close()


def test_import_wrong_passphrase_fails(reg, folder, tmp_path):
    d = _populated(reg, folder)
    export = d.export(tmp_path / "h.shield", PASS)
    r2 = Registry(tmp_path / "h2")
    with pytest.raises(VaultError) as exc:
        r2.import_(export, "mauvaise phrase de passe")
    assert "Garnier" not in str(exc.value)
    assert r2.list() == []
    r2.close()


def test_import_rejects_tampered_or_foreign_files(reg, folder, tmp_path):
    d = _populated(reg, folder)
    export = d.export(tmp_path / "h.shield", PASS)
    raw = bytearray(export.read_bytes())
    raw[-10] ^= 0x01
    tampered = tmp_path / "t.shield"
    tampered.write_bytes(bytes(raw))
    foreign = tmp_path / "f.shield"
    foreign.write_bytes(b"not an export")
    bad_header = tmp_path / "b.shield"
    bad_header.write_bytes(V._EXPORT_MAGIC + b'{"kdf":"scrypt","n":2,"r":8,"p":1,"salt":"AA=="}\nxx\n')
    r2 = Registry(tmp_path / "h2")
    for path in (tampered, foreign, bad_header, tmp_path / "absent.shield"):
        with pytest.raises(VaultError):
            r2.import_(path, PASS)
    assert r2.list() == []
    r2.close()


def test_export_needs_a_real_passphrase(reg, folder, tmp_path):
    d = reg.add_dossier(folder)
    with pytest.raises(ValueError):
        d.export(tmp_path / "x.shield", "court")
    assert not (tmp_path / "x.shield").exists()


def test_import_payload_validation():
    good = {"format": V._EXPORT_FORMAT, "version": 1, "title": "t", "folder": "", "locale": "fr",
            "entities": [{"kind": "PERSON", "idx": 0, "code": "PERSONNE_A", "value": "v", "norm": "v",
                          "source": "user"}],
            "counters": {"PERSON": 1}, "clear": [], "documents": [{"id": 1, "rel": "a/b.txt"}]}
    V._validate_payload(good)
    for mutate in (
        lambda p: p["entities"][0].update(code="PERSONNE_B"),        # code does not match index
        lambda p: p["entities"][0].update(kind="ALIEN"),
        lambda p: p["documents"][0].update(rel="../../secret.txt"),  # traversal
        lambda p: p["documents"][0].update(rel="/etc/passwd"),
        lambda p: p.update(counters={"PERSON": 0}),                 # counter would reuse a code
        lambda p: p.update(locale="de"),
    ):
        bad = {**good, "entities": [dict(good["entities"][0])], "documents": [dict(good["documents"][0])]}
        mutate(bad)
        with pytest.raises((ValueError, KeyError, TypeError)):
            V._validate_payload(bad)


# --------------------------------------------------------------------------- remove

def test_remove_dossier(reg, folder, tmp_path):
    (folder / "a.txt").write_text("contenu")
    d = reg.add_dossier(folder, title=TITLE)
    d.register("PERSON", PERSON)
    vault_file = config.home() / "vaults" / f"{d.uuid}.db"
    assert vault_file.exists()
    reg.remove("DOSSIER_1")
    assert not vault_file.exists()
    assert not list((config.home() / "vaults").iterdir())
    with pytest.raises(UnknownDossier):
        reg.get("DOSSIER_1")
    assert reg.list() == []
    assert (folder / "a.txt").read_text() == "contenu"  # documents untouched
    assert ("dossier_removed", "DOSSIER_1") in {(e["event"], e["dossier"]) for e in reg.journal_entries()}
    assert reg.add_dossier(folder).code == "DOSSIER_2"  # numbers are not reused
    with pytest.raises(UnknownDossier):
        reg.remove("DOSSIER_1")


def test_removed_in_other_process_is_noticed(folder):
    r1, r2 = Registry(), Registry()
    r1.add_dossier(folder)
    assert r2.get("DOSSIER_1")
    r1.remove("DOSSIER_1")
    with pytest.raises(UnknownDossier):
        r2.get("DOSSIER_1")
    assert r2.list() == []
    r1.close()
    r2.close()


# --------------------------------------------------------------------------- keys

def test_wrong_key_fails_closed(reg, folder):
    d = reg.add_dossier(folder)
    d.register("PERSON", PERSON)
    reg.close()
    from cryptography.fernet import Fernet

    (config.home() / "key").write_bytes(Fernet.generate_key())
    with pytest.raises(VaultError) as exc:
        Registry()
    assert "Garnier" not in str(exc.value)


def test_missing_key_fails_closed_without_new_key(reg, folder):
    reg.add_dossier(folder)
    reg.close()
    (config.home() / "key").unlink()
    with pytest.raises(VaultError):
        Registry()
    assert not (config.home() / "key").exists()


class _FakeKeyring(types.ModuleType):
    def __init__(self, fail: bool = False):
        super().__init__("keyring")
        self.store: dict = {}
        self.fail = fail

    def get_password(self, service, user):
        if self.fail:
            raise RuntimeError("no keychain")
        return self.store.get((service, user))

    def set_password(self, service, user, password):
        if self.fail:
            raise RuntimeError("no keychain")
        self.store[(service, user)] = password


def test_keyring_is_used_when_enabled(folder, monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setitem(sys.modules, "keyring", fake)
    monkeypatch.setenv("RAGBASE_SHIELD_KEYRING", "1")
    r = Registry()
    assert r.key_source == "keyring"
    assert ("ragbase-shield", "vault-key") in fake.store
    assert not (config.home() / "key").exists()
    r.add_dossier(folder).register("PERSON", PERSON)
    r.close()
    r2 = Registry()
    assert r2.get("DOSSIER_1").get_by_code("PERSONNE_A").value == PERSON
    r2.close()

    # keychain gone later: fail closed, do not create a new key file that would hide the data
    fake.fail = True
    with pytest.raises(VaultError):
        Registry()
    assert not (config.home() / "key").exists()
    fake.fail = False
    r3 = Registry()
    assert r3.get("DOSSIER_1").get_by_code("PERSONNE_A").value == PERSON
    r3.close()


def test_keyring_failure_falls_back_to_key_file(folder, monkeypatch):
    monkeypatch.setitem(sys.modules, "keyring", _FakeKeyring(fail=True))
    monkeypatch.setenv("RAGBASE_SHIELD_KEYRING", "1")
    r = Registry()
    assert r.key_source == "file"
    assert (config.home() / "key").exists()
    r.add_dossier(folder).register("PERSON", PERSON)
    r.close()
    r2 = Registry()
    assert r2.get("DOSSIER_1").get_by_code("PERSONNE_A").value == PERSON
    r2.close()


def test_keyring_off_never_touches_keyring(folder, monkeypatch):
    class Boom(types.ModuleType):
        def __getattr__(self, name):
            raise AssertionError("keyring must not be used when RAGBASE_SHIELD_KEYRING=0")

    monkeypatch.setitem(sys.modules, "keyring", Boom("keyring"))
    r = Registry()
    assert r.key_source == "file"
    r.close()


# --------------------------------------------------------------------------- engine integration

def test_dossier_works_as_engine_entity_store(reg, folder):
    d = reg.add_dossier(folder)
    for method in ("all", "get_by_norm", "get_by_code", "add", "is_kept_clear"):
        assert callable(getattr(d, method))
    masker_mod = pytest.importorskip("ragbase_shield.engine.masker")
    d.register("PERSON", PERSON)
    masker = masker_mod.Masker(d, locale=d.locale, use_ner=False)
    res = masker.mask(f"Le dossier de {PERSON} est prêt.")
    assert PERSON not in res.text and "PERSONNE_A" in res.text
    assert masker.unmask(res.text) == f"Le dossier de {PERSON} est prêt."


# --------------------------------------------------------------------------- robustness

def test_same_folder_from_many_threads_gives_one_dossier(reg, folder):
    results = []

    def worker():
        results.append(reg.add_dossier(folder).code)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert set(results) == {"DOSSIER_1"}
    assert len(reg.list()) == 1


def test_folders_and_path_lookup_do_not_need_the_vault(reg, folder, tmp_path):
    d = reg.add_dossier(folder)
    (folder / "a.txt").write_text("x")
    assert reg.folders() == {"DOSSIER_1": folder.resolve()}
    assert reg.dossier_code_for_path(folder / "a.txt") == "DOSSIER_1"
    assert reg.dossier_code_for_path(tmp_path) is None
    reg.close()
    # damaged vault file: the registry still knows the folder (hooks keep blocking reads), and the
    # dossier can still be removed
    vault_file = config.home() / "vaults" / f"{d.uuid}.db"
    vault_file.write_bytes(b"garbage, not sqlite" * 100)
    r2 = Registry()
    assert r2.dossier_code_for_path(folder / "a.txt") == "DOSSIER_1"
    with pytest.raises(VaultError) as exc:
        r2.get("DOSSIER_1")
    assert str(folder) not in str(exc.value)
    r2.remove("DOSSIER_1")
    assert r2.folders() == {} and not vault_file.exists()
    r2.close()
