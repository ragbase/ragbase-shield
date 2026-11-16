"""Round 10, second pass (engine 0.4.4): the fixes of the review, and the cheaper re-check of a kept set when only
another dossier changed. Invented text and synthetic files only: no real person, no client data. A "new process" is
a new Service object on the same data folder (service.reset())."""
from __future__ import annotations

import errno
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

from ragbase_shield import claude_tab, documents, kept, service
from test_round10 import (Reads, _set_files, _wait, answers, call, first_reading, make_folder, new_process,  # noqa: F401
                          plugin, protect)

NOT_ROOT = pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                              reason="chmod 000 refuses the open only for a normal user on macOS or Linux")


def _manifests(data: Path, code: str) -> list[Path]:
    folder = data / "kept" / code
    return sorted(folder.glob("m-*.bin")) if folder.exists() else []


def _start(monkeypatch, code: str) -> tuple[bool, int]:
    """New process: (kept set used at once, number of file reads until the dossier is ready)."""
    new_process()
    reads = Reads(monkeypatch)
    svc = service.default()
    ready = svc._kset_ready(code)
    if not ready:
        svc.start_reading(code)
        _wait(code)
    svc.list_documents(code)
    return ready, reads.calls


def _list_line(listing: str, needle: str) -> str:
    return next(l for l in listing.splitlines() if needle in l)


def _docx(path: Path) -> None:
    import docx as _d

    doc = _d.Document()
    doc.add_paragraph("Contrat fictif entre Mme Ysaline Corbaz et la société Brévanne Logistique SAS.")
    doc.save(str(path))


# ============================================================================== findings 1 and 5: an error that passes

def test_io_failure_rule():
    assert documents.io_failure(OSError(errno.EIO, "Input/output error"))
    assert documents.io_failure(TimeoutError(errno.ETIMEDOUT, "timed out"))
    assert documents.io_failure(MemoryError())
    wrapped = ValueError("reader")
    wrapped.__cause__ = OSError(errno.EIO, "io")
    assert documents.io_failure(wrapped)
    assert not documents.io_failure(ValueError("broken zip"))
    assert not documents.io_failure(KeyError("word/document.xml"))


def test_read_text_gives_read_io_for_a_system_error(tmp_path, monkeypatch):
    p = tmp_path / "note.txt"
    p.write_text("Texte fictif.\n", encoding="utf-8")
    monkeypatch.setattr(documents, "_read_plain", lambda path: (_ for _ in ()).throw(OSError(errno.ETIMEDOUT, "x")))
    with pytest.raises(documents.ReadIO) as exc:
        documents.read_text(p)
    assert str(exc.value) == documents.READ_IO
    with pytest.raises(documents.ReadIO) as exc:  # missing for a moment: the old code, but it can pass
        documents.read_text(tmp_path / "parti.txt")
    assert str(exc.value) == "file_not_found"
    bad = tmp_path / "abime.docx"
    bad.write_bytes(b"PK\x03\x04 broken")
    with pytest.raises(documents.DocumentError) as exc:  # a broken file stays a content error
        documents.read_text(bad)
    assert str(exc.value) == "docx_unreadable" and not isinstance(exc.value, documents.ReadIO)


def test_a_passing_io_error_is_not_kept_and_the_file_is_read_again(plugin, tmp_path, monkeypatch):
    """A cloud file that is not on the computer (OneDrive Files On-Demand, iCloud) gives ETIMEDOUT offline; then it
    comes back unchanged (same mtime and size)."""
    folder = make_folder(tmp_path)
    real = documents._read_plain
    state = {"fail": True}

    def offline(path):
        if Path(path).name == "note de synthese.txt" and state["fail"]:
            raise OSError(errno.ETIMEDOUT, "Operation timed out")
        return real(path)

    monkeypatch.setattr(documents, "_read_plain", offline)
    server, code, text = protect(folder)
    assert "5 document(s) trouvé(s), 4 lu(s), 1 illisible(s)." in text
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    line = _list_line(listing, "note de synthese.txt")
    assert line.endswith(" | (non lu)")
    doc = line.split(" |")[0]
    assert not _manifests(plugin, code)  # A2 (e): never kept
    err, answer = call(server, "shield_read_document", {"dossier": code, "document": doc})
    assert err and answer == claude_tab.ERRORS["document_unavailable"]
    assert "abîmé" not in answer
    # the file is back: the same conversation reads it at the next call
    state["fail"] = False
    err, answer = call(server, "shield_read_document", {"dossier": code, "document": doc})
    assert not err and "PERSONNE_" in answer and "Quillardet" not in answer
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    assert "(non lu)" not in listing
    # a new conversation reads the whole dossier again (nothing was kept), then keeps it
    ready, reads = _start(monkeypatch, code)
    assert not ready and reads > 0
    assert service.default().reading_summary(code)["unreadable"] == 0
    ready, reads = _start(monkeypatch, code)
    assert ready and reads == 0


def test_protect_again_reads_a_file_that_came_back(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    real = documents._read_eml
    state = {"fail": True}

    def offline(path):
        if state["fail"]:
            raise OSError(errno.EIO, "Input/output error")
        return real(path)

    monkeypatch.setattr(documents, "_read_eml", offline)
    server, code, text = protect(folder)
    assert "1 illisible(s)" in text
    state["fail"] = False
    new_process()
    server, code2, text = protect(folder)
    assert code2 == code and "Il est prêt" not in text
    assert "5 document(s) trouvé(s), 5 lu(s)." in text, text


def test_a_content_error_is_still_kept(plugin, tmp_path, monkeypatch):
    """A broken file stays "unreadable" while it is the same: the dossier is kept, the list says « (non lu) »."""
    folder = make_folder(tmp_path)
    (folder / "abime.pdf").write_bytes(b"%PDF-1.4 rien de lisible")
    server, code, text = protect(folder)
    assert "1 illisible(s)" in text and _manifests(plugin, code)
    new_process()
    reads = Reads(monkeypatch, fail=True)
    server, code2, text = protect(folder)
    assert "Il est prêt" in text and reads.calls == 0
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    assert _list_line(listing, "abime.pdf").endswith(" | (non lu)")


# ============================================================================== finding 4: a refused or locked Word file

@NOT_ROOT
def test_a_refused_docx_reaches_the_refusal_rule(tmp_path):
    p = tmp_path / "contrat.docx"
    _docx(p)
    os.chmod(p, 0)
    try:
        with pytest.raises(documents.ReadDenied):
            documents.read_text(p)
    finally:
        os.chmod(p, 0o644)
    assert "Ysaline" in documents.read_text(p)


def _sharing_open(target: str):
    real = open

    def fake(file, *a, **kw):
        if str(file).endswith(target):
            exc = PermissionError(13, "The process cannot access the file because it is being used by another process")
            exc.winerror = 32
            raise exc
        return real(file, *a, **kw)

    return fake


def test_a_locked_docx_is_said_locked(tmp_path, monkeypatch):
    p = tmp_path / "contrat.docx"
    _docx(p)
    monkeypatch.setattr(documents, "open", _sharing_open("contrat.docx"), raising=False)
    with pytest.raises(documents.ReadLocked):
        documents.read_text(p)


def test_a_locked_docx_is_marked_never_kept_and_read_once_closed(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    _docx(folder / "contrat Corbaz.docx")
    with monkeypatch.context() as m:
        m.setattr(documents, "open", _sharing_open("contrat Corbaz.docx"), raising=False)
        server, code, text = protect(folder)
        assert "6 document(s) trouvé(s), 5 lu(s), 1 illisible(s)." in text
        _, listing = call(server, "shield_list_documents", {"dossier": code})
        line = _list_line(listing, ".docx")
        assert line.endswith(" | (non lu : ouvert dans un autre programme)") and "Corbaz" not in line
        err, answer = call(server, "shield_read_document", {"dossier": code, "document": line.split(" |")[0]})
        assert err and answer == claude_tab.ERRORS["document_locked"]
        assert not _manifests(plugin, code)
    # Word is closed: a new conversation reads the dossier again, then keeps it
    ready, reads = _start(monkeypatch, code)
    assert not ready and reads > 0
    assert service.default().reading_summary(code)["unreadable"] == 0
    ready, reads = _start(monkeypatch, code)
    assert ready and reads == 0


@NOT_ROOT
def test_a_refused_docx_is_never_kept(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    _docx(folder / "contrat Corbaz.docx")
    os.chmod(folder / "contrat Corbaz.docx", 0)
    try:
        server, code, text = protect(folder)
        assert "1 illisible(s)" in text and not _manifests(plugin, code)
    finally:
        os.chmod(folder / "contrat Corbaz.docx", 0o644)
    new_process()
    server, code, text = protect(folder)
    assert "6 document(s) trouvé(s), 6 lu(s)." in text and "Il est prêt" not in text
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    assert "non lu" not in listing


# ============================================================================== finding 2: evidence

def test_evidence_from_outside_the_documents_gives_a_full_reading(plugin, tmp_path, monkeypatch):
    folder, code, _ = first_reading(tmp_path)
    new_process()
    svc = service.default()
    d = svc.registry.get(code)
    erev, rev = d._counter("erev"), d.revision
    fp = kept.lexicon_fingerprint(d)
    svc.mask_text("Mme Ysaline Corbaz a écrit à M. Odilon Quillardet au sujet de Maëlle.", code)  # Desk, command line
    assert d._counter("erev") > erev and d.revision == rev  # evidence only: the entities are the same
    assert kept.lexicon_fingerprint(d) != fp
    ready, reads = _start(monkeypatch, code)
    assert not ready and reads > 0
    ready, reads = _start(monkeypatch, code)
    assert ready and reads == 0


def test_the_answers_of_a_kept_dossier_leave_it_ready(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    new_process()
    reads = Reads(monkeypatch, fail=True)
    server, _, text = protect(folder)
    assert "Il est prêt" in text
    erev = service.default().registry.get(code)._counter("erev")
    after = answers(server, code)
    assert after == before and reads.calls == 0
    assert service.default().registry.get(code)._counter("erev") == erev
    ready, reads = _start(monkeypatch, code)
    assert ready and reads == 0


def test_evidence_of_another_dossier_does_not_change_the_guard(plugin, tmp_path, monkeypatch):
    folder, code, _ = first_reading(tmp_path)
    other = tmp_path / "Dossier Ondine"
    other.mkdir()
    (other / "a.txt").write_text("Mme Ondine Valcrest et M. Corentin Faubeau signent.\n", encoding="utf-8")
    code2 = service.default().protect_folder(other)["code"]
    _wait(code2)
    _start(monkeypatch, code)  # A is kept again with B in the guard
    svc = service.default()
    b = svc.registry.get(code2)
    guard = kept.guard_fingerprint(svc._open_dossiers())
    erev = b._counter("erev")
    svc.mask_text("Mme Ondine Valcrest a écrit à M. Corentin Faubeau.", code2)
    assert b._counter("erev") > erev
    assert kept.guard_fingerprint(svc._open_dossiers()) == guard
    ready, reads = _start(monkeypatch, code)
    assert ready and reads == 0


# ============================================================================== finding 3: the client folder is gone

def test_the_kept_copy_is_deleted_when_the_client_folder_is_gone(plugin, tmp_path):
    folder, code, _ = first_reading(tmp_path)
    other = tmp_path / "Dossier Ondine"
    other.mkdir()
    (other / "a.txt").write_text("Mme Ondine Valcrest signe.\n", encoding="utf-8")
    code2 = service.default().protect_folder(other)["code"]
    _wait(code2)
    assert _manifests(plugin, code) and _manifests(plugin, code2)
    shutil.rmtree(folder)  # end of the matter: the firm deletes the client folder
    new_process()
    assert service.default().clean_kept() == [code]
    assert not (plugin / "kept" / code).exists()
    assert _manifests(plugin, code2)  # the other dossier keeps its set
    assert code in [x["code"] for x in service.default().list_dossiers()]  # the dossier itself stays (names only)
    assert service.default().clean_kept() == []


# ============================================================================== the cheaper re-check (not_done of pass 1)

def _other_dossier(tmp_path: Path, text: str) -> str:
    other = tmp_path / "Dossier Ondine"
    other.mkdir()
    (other / "a.txt").write_text(text, encoding="utf-8")
    code2 = service.default().protect_folder(other)["code"]
    _wait(code2)
    return code2


def test_another_dossier_added_needs_no_reading(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    _other_dossier(tmp_path, "Mme Ondine Valcrest et M. Corentin Faubeau signent.\n")
    new_process()
    assert not service.default()._kset_ready(code)  # the values of the dossiers changed: not at once
    reads = Reads(monkeypatch, fail=True)
    server, _, text = protect(folder)
    assert f"Ce dossier était déjà protégé : {code}. Il est prêt." in text, text
    after = answers(server, code)
    assert reads.calls == 0
    for key in before:
        if key != "status":  # the status lists the new dossier too
            assert after[key] == before[key], key
    # written again with the new fingerprints: the next start is ready at once
    new_process()
    assert service.default()._kset_ready(code)


def test_another_dossier_whose_name_is_in_the_texts_gives_a_full_reading(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    assert "Lorient" in "".join(v for k, v in before.items() if k.startswith("read"))
    code2 = _other_dossier(tmp_path, "M. Yannick Lorient, témoin fictif.\n")
    service.default().register(code2, "PERSON", "Lorient")
    new_process()
    reads = Reads(monkeypatch)
    server, _, text = protect(folder)
    assert "Il est prêt" not in text and reads.calls > 0
    after = answers(server, code)
    assert "Lorient" not in "".join(v for k, v in after.items() if k.startswith("read"))
    new_process()
    assert service.default()._kset_ready(code)


def test_the_recheck_refuses_a_kept_text_the_last_check_now_changes(plugin, tmp_path, monkeypatch):
    """All or nothing: one document whose last check gives another text sends the WHOLE dossier to a full reading."""
    folder, code, _ = first_reading(tmp_path)
    _other_dossier(tmp_path, "Mme Ondine Valcrest signe.\n")
    new_process()
    svc = service.default()
    real = svc._guard_full
    calls = {"n": 0}

    def guard(text, primary=None):
        calls["n"] += 1
        out = real(text, primary)
        return (out[0] + " ", out[1], out[2]) if calls["n"] == 2 else out

    monkeypatch.setattr(svc, "_guard_full", guard)
    reads = Reads(monkeypatch)
    svc.start_reading(code)
    _wait(code)
    assert reads.calls > 0 and not svc.reading_kept(code)


def test_a_kill_during_the_recheck_leaves_the_mark(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    _other_dossier(tmp_path, "Mme Ondine Valcrest signe.\n")
    new_process()
    svc = service.default()

    def boom(*a, **kw):
        raise service._Stopped()  # the server stops in the middle of the re-check

    monkeypatch.setattr(svc, "_guard_full", boom)
    svc.start_reading(code)
    svc.wait_reading(code, 20)
    assert svc._mark_info(code) is not None  # the mark stays: the next start does the work again
    new_process()
    reads = Reads(monkeypatch, fail=True)
    svc = service.default()
    svc.start_reading(code)
    _wait(code)
    assert svc.reading_kept(code) and reads.calls == 0 and svc._mark_info(code) is None
