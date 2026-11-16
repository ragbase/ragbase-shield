"""Round 9 (engine 0.4.3): long PDF files read fast, with a time budget and flat memory (B), and a dossier read in
the background with a progress count (A). Invented text and synthetic files only: no real person, no client data.

The slow test with the 800-page file runs only with RAGBASE_SHIELD_SLOW_TESTS=1 (kept out of the default run)."""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from mcp import Client

import synth_pdf
from ragbase_shield import __version__, claude_tab, documents, service, vault
from ragbase_shield.documents import DocumentError, ReadTooLong, read_text

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
GRAND = "grand livre.pdf"
LATE_NAME = "Kerbrat-Lussac"
GRAND_TEXT = ("Registre des livraisons fictif. Le 3 mars 2026, M. Aurélien Kerbrat-Lussac signe le bon de "
              "livraison au dépôt.\n") * 40
NOTE_TEXT = "Note interne fictive : le rendez-vous avec M. Kerbrat-Lussac est fixé au 12 avril 2026.\n"
ENGLISH = re.compile(r"\b(the|masked|error|internal|unknown|vault|reading|progress|waiting|pending)\b", re.I)


# ============================================================================================ B: PDF reading

def _plumber_text(path: Path) -> str:
    """The 0.4.2 reading of a PDF (pdfplumber, page by page), for the byte-for-byte check."""
    import pdfplumber

    texts = []
    with pdfplumber.open(str(path), password="") as pdf:
        for page in pdf.pages:
            texts.append(documents.pdf_page_text(page).strip("\n"))
    return documents._clean_text("\n\n".join(t for t in texts if t.strip()))


def test_constants_are_one_place():
    assert documents.PDF_PLUMBER_MAX_PAGES == 40
    assert documents.DOCUMENT_TIME_BUDGET == 180.0
    assert documents.PDF_PLUMBER_SECONDS == 20.0


def test_short_pdf_is_read_exactly_as_before(tmp_path):
    path = synth_pdf.make_long_pdf(tmp_path / "court.pdf", 3)
    res = read_text(path)
    assert res.text == _plumber_text(path)
    assert " | " in res.text  # the ruled-table cells of the pdfplumber reading
    assert res.pages == 3 and not res.warnings


def test_long_pdf_is_read_with_pypdf_from_the_first_page(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 3)
    used = []
    real_plumber, real_pypdf = documents._read_pdf_plumber, documents._read_pdf_pypdf
    monkeypatch.setattr(documents, "_read_pdf_plumber", lambda *a, **k: used.append("plumber") or real_plumber(*a, **k))
    monkeypatch.setattr(documents, "_read_pdf_pypdf", lambda *a, **k: used.append("pypdf") or real_pypdf(*a, **k))
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 2)
    res = read_text(path)
    assert used == ["pypdf"]
    assert res.pages == 3 and synth_pdf.PERSON_EARLY in res.text and " | " not in res.text
    used.clear()
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 3)  # exactly at the limit: pdfplumber
    read_text(path)
    assert used == ["plumber"]


def test_progress_counts_pages(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 3)
    for limit in (40, 0):  # pdfplumber, then pypdf
        monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", limit)
        seen = []
        read_text(path, progress=lambda done, total: seen.append((done, total)))
        assert seen == [(0, 3), (1, 3), (2, 3), (3, 3)]


class FakeClock:
    """A clock that moves ``step`` seconds at every reading."""

    def __init__(self, step: float):
        self.t = 0.0
        self.step = step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def test_time_budget_stops_a_long_reading_between_pages(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 3)
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 0)
    with pytest.raises(ReadTooLong) as exc:
        read_text(path, clock=FakeClock(100.0))
    assert str(exc.value) == documents.READ_TOO_LONG and isinstance(exc.value, DocumentError)
    # a budget that is not passed: the same file is read in full
    assert read_text(path, clock=FakeClock(1.0)).pages == 3


def test_budget_on_the_pdfplumber_path_too(tmp_path):
    path = synth_pdf.make_long_pdf(tmp_path / "court.pdf", 3)
    with pytest.raises(ReadTooLong):
        read_text(path, budget=0.0, clock=FakeClock(1.0))


def test_slow_pdfplumber_falls_back_to_pypdf_for_the_whole_file(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "court.pdf", 3)
    seen = []
    res = read_text(path, progress=lambda d, t: seen.append(d), clock=FakeClock(15.0))
    assert res.text == documents._clean_text(documents._read_pdf_pypdf(path)[0])
    assert res.pages == 3
    assert seen[:2] == [0, 1] and seen[-4:] == [0, 1, 2, 3]  # pdfplumber stopped after page 1, pypdf from page 1


def test_pdf_pages_are_freed_while_reading(tmp_path, monkeypatch):
    """B3: no page keeps its decoded content (pypdf) or its objects (pdfplumber) after it is read."""
    import pdfplumber.page
    import pypdf

    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 4)
    readers = []
    real_reader = pypdf.PdfReader

    def spy(*a, **k):
        r = real_reader(*a, **k)
        readers.append(r)
        return r

    monkeypatch.setattr(pypdf, "PdfReader", spy)
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 0)
    read_text(path)
    reader = readers[-1]
    for page in reader.pages:
        assert page["/Contents"].get_object().decoded_self is None
    closed = []
    real_close = pdfplumber.page.Page.close
    monkeypatch.setattr(pdfplumber.page.Page, "close", lambda self: closed.append(1) or real_close(self))
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 40)
    after_page = []
    read_text(path, progress=lambda done, total: after_page.append(len(closed)))
    assert after_page == [0, 1, 2, 3, 4]  # each page is freed as soon as its text is read


def test_pdf_reader_errors_keep_their_codes(tmp_path):
    bad = tmp_path / "abime.pdf"
    bad.write_bytes(b"%PDF-1.4 rien")
    with pytest.raises(DocumentError) as exc:
        read_text(bad)
    assert str(exc.value) == "pdf_unreadable"


def test_synthetic_pdf_has_the_shape_of_the_slow_file():
    raw = synth_pdf._page_stream(1, 800)
    assert raw.count(b" Tj") == 556 and raw.count(b" re") >= 160


# ============================================================================================ A: background reading

class SlowRead:
    """Fake ``documents.read_text``: the file ``grand livre.pdf`` is a long PDF whose reading waits for ``release``
    (page 120 of 846 meanwhile); the other files are read for real."""

    def __init__(self, real, too_long: bool = False):
        self.real = real
        self.release = threading.Event()
        self.calls = 0
        self.too_long = too_long

    def __call__(self, path, *, progress=None, budget=None, clock=time.monotonic, max_chars=None):
        if Path(path).name == GRAND:
            self.calls += 1
            if progress:
                progress(0, 846)
            while not self.release.wait(0.02):
                if progress:
                    progress(120, 846)
            if self.too_long:
                raise ReadTooLong()
            return documents.ReadResult(GRAND_TEXT, pages=846)
        return self.real(path, progress=progress, budget=budget, clock=clock, max_chars=max_chars)


@pytest.fixture
def slow(monkeypatch):
    fake = SlowRead(documents.read_text)
    monkeypatch.setattr(documents, "read_text", fake)
    yield fake
    fake.release.set()


@pytest.fixture
def dossier(tmp_path):
    f = tmp_path / "cabinet" / "Dossier Brévanne"
    f.mkdir(parents=True)
    (f / GRAND).write_bytes(b"%PDF-1.4 fictif")
    (f / "note.txt").write_text(NOTE_TEXT, encoding="utf-8")
    return f


@pytest.fixture
def svc(tmp_path):
    s = service.Service(tmp_path / "data")
    yield s
    s.close()


def _wait(s, code, timeout=20.0):
    assert s.wait_reading(code, timeout), "the reading did not end"


def test_service_reads_in_the_background_and_refuses_content_meanwhile(svc, dossier, slow):
    r = svc.protect_folder(dossier)
    code = r["code"]
    assert code == "DOSSIER_1" and not r["existing"]
    deadline = time.monotonic() + 5
    while (svc.reading_state(code) or {}).get("page") != 120 and time.monotonic() < deadline:
        time.sleep(0.02)
    st = svc.reading_state(code)
    assert st["state"] == "reading" and st["total"] == 2 and st["page"] == 120 and st["pages"] == 846
    for call in (lambda: svc.list_documents(code), lambda: svc.read_document(code, "DOC_1"),
                 lambda: svc.search(code, "livraison"), lambda: svc.save_draft(code, "Projet", "Texte"),
                 lambda: svc.document_folders(code)):
        with pytest.raises(service.ShieldError) as exc:
            call()
        assert exc.value.kind == "dossier_reading" and exc.value.dossier == code
    assert svc._mark_path(code).exists()
    slow.release.set()
    _wait(svc, code)
    assert svc.reading_state(code) is None and not svc._mark_path(code).exists()
    summary = svc.reading_summary(code)
    assert summary["documents"] == 2 and summary["unreadable"] == 0 and summary["too_long"] == 0
    docs = svc.list_documents(code)
    assert len(docs) == 2
    note = next(d for d in docs if d["kind"] == "txt")
    text = svc.read_document(code, note["id"])["text"]
    # the name was found in the long document, read last: it is hidden in the note too
    assert LATE_NAME not in text and "Kerbrat" not in text
    assert slow.calls == 1  # read once: the masking used the text read before


def test_status_and_dossier_list_answer_while_a_masking_holds_the_service(svc, dossier, slow):
    code = svc.protect_folder(dossier)["code"]
    held = threading.Event()
    done = threading.Event()

    def hold():
        with svc._lock:
            held.set()
            done.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    held.wait(2)
    try:
        t0 = time.monotonic()
        st = svc.status()
        rows = svc.list_dossiers()
        state = svc.reading_state(code)
        states = svc.readings()
        assert time.monotonic() - t0 < 1.0
        assert st["version"] == "0.4.3" and rows[0]["reading"]["state"] in ("reading", "waiting")
        assert state is not None and states[0]["code"] == code
        with pytest.raises(service.ShieldError):
            svc.list_documents(code)  # the refusal does not wait for the lock either
        assert time.monotonic() - t0 < 1.5
    finally:
        done.set()
        t.join()
        slow.release.set()
    _wait(svc, code)


def test_a_stop_in_the_middle_leaves_the_dossier_not_ready_then_reading_starts_again(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    deadline = time.monotonic() + 5
    while (first.reading_state(code) or {}).get("page") != 120 and time.monotonic() < deadline:
        time.sleep(0.02)
    first.close()  # the server stops in the middle of the long document
    assert (home / service.READING_DIR_NAME / f"{code}.pending").exists()
    second = service.Service(home)
    try:
        assert second.pending_readings() == {code: second.registry.get(code).uuid}
        assert second.reading_state(code)["state"] == "pending"
        with pytest.raises(service.ShieldError) as exc:
            second.read_document(code, "DOC_1")  # a half-read dossier is never readable; this call restarts it
        assert exc.value.kind == "dossier_reading"
        assert second.reading_state(code)["state"] in ("waiting", "reading")
        slow.release.set()
        _wait(second, code)
        assert second.reading_state(code) is None and len(second.list_documents(code)) == 2
    finally:
        second.close()


def test_resume_at_start_reads_the_unfinished_dossiers(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    first.close()
    slow.release.set()
    second = service.Service(home)
    try:
        assert second.resume_readings() == [code]
        assert second.resume_readings() == []  # already going on: no second reading
        _wait(second, code)
        assert second.pending_readings() == {}
    finally:
        second.close()


def test_a_second_request_for_the_same_folder_joins_the_reading(svc, dossier, slow):
    a = svc.protect_folder(dossier)
    b = svc.protect_folder(dossier)
    assert a["code"] == b["code"] and b["already_reading"] and b["existing"]
    assert sum(1 for t in threading.enumerate() if t.name.startswith("shield-reading-")) == 1
    slow.release.set()
    _wait(svc, a["code"])


def test_one_reading_at_a_time(svc, dossier, slow, tmp_path):
    other = tmp_path / "cabinet" / "Dossier Quillardet"
    other.mkdir()
    (other / "lettre.txt").write_text("Lettre fictive de Mme Odile Quillardet, 3 rue des Lilas, 44000 Nantes.\n",
                                      encoding="utf-8")
    a = svc.protect_folder(dossier)["code"]
    deadline = time.monotonic() + 5
    while (svc.reading_state(a) or {}).get("state") != "reading" and time.monotonic() < deadline:
        time.sleep(0.02)
    b = svc.protect_folder(other)["code"]
    time.sleep(0.2)
    assert svc.reading_state(b)["state"] == "waiting"
    slow.release.set()
    _wait(svc, a)
    _wait(svc, b)
    assert svc.reading_state(a) is None and svc.reading_state(b) is None


def test_a_document_over_its_budget_is_counted_and_listed_as_not_read(svc, dossier, monkeypatch):
    fake = SlowRead(documents.read_text, too_long=True)
    fake.release.set()
    monkeypatch.setattr(documents, "read_text", fake)
    code = svc.protect_folder(dossier)["code"]
    _wait(svc, code)
    summary = svc.reading_summary(code)
    assert summary["too_long"] == 1 and summary["unreadable"] == 0 and summary["documents"] == 2
    docs = {d["kind"]: d for d in svc.list_documents(code)}
    assert docs["pdf"]["not_read"] == "too_long" and docs["txt"]["not_read"] is None
    with pytest.raises(service.ShieldError) as exc:
        svc.read_document(code, docs["pdf"]["id"])
    assert exc.value.kind == "document_too_long"
    assert svc.search(code, "rendez-vous")  # the other documents are searched; the long one is skipped
    assert fake.calls == 1  # never read again while the file is the same


def test_remove_dossier_clears_the_mark(svc, dossier, slow):
    code = svc.protect_folder(dossier)["code"]
    slow.release.set()
    _wait(svc, code)
    svc._write_mark(code, "x")
    svc.remove_dossier(code)
    assert not svc._mark_path(code).exists()


def test_a_removed_dossier_is_not_read_again(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    first.close()
    second = service.Service(home)
    try:
        second.registry.remove(code)
        slow.release.set()
        second.resume_readings()
        _wait(second, code)
        assert second.pending_readings() == {} and second.reading_state(code) is None
    finally:
        second.close()


def test_after_a_restart_a_long_pdf_is_read_again_in_the_background(tmp_path, dossier, slow, monkeypatch):
    """A ready dossier, a new process (empty cache): the first call does not read an 846-page PDF inside the tool
    call; it starts a background reading (no mark: the dossier stays ready on disk) and answers the progress."""
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    slow.release.set()
    _wait(first, code)
    first.close()
    slow.release.clear()
    monkeypatch.setattr(service.Service, "_pdf_pages", lambda self, path, m, z: 846 if path.name == GRAND else 1)
    second = service.Service(home)
    try:
        with pytest.raises(service.ShieldError) as exc:
            second.list_documents(code)
        assert exc.value.kind == "dossier_reading"
        assert second.pending_readings() == {}  # no mark: a stop now would leave the dossier ready
        slow.release.set()
        _wait(second, code)
        assert len(second.list_documents(code)) == 2  # once per process: no second background reading
        assert slow.calls == 2
    finally:
        second.close()


def test_a_ready_dossier_of_small_files_answers_at_once_after_a_restart(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    slow.release.set()
    _wait(first, code)
    first.close()
    second = service.Service(home)
    try:
        assert len(second.list_documents(code)) == 2  # the fake PDF has no page count: nothing to read first
    finally:
        second.close()


def test_a_reading_that_keeps_failing_stops_being_started_again(svc, dossier, slow, monkeypatch):
    slow.release.set()
    monkeypatch.setattr(service.Service, "_build_directory", lambda self, d: 1 / 0)
    code = svc.protect_folder(dossier)["code"]
    for _ in range(service.MAX_READING_FAILURES + 2):
        _wait(svc, code)
        with pytest.raises(service.ShieldError):
            svc.list_documents(code)
    _wait(svc, code)
    state = svc.reading_state(code)
    assert state["state"] == "failed" and state["gave_up"]
    assert svc.resume_readings() == []
    assert "Redémarrez l'application Claude" in claude_tab.reading_sentence(state)
    assert svc._mark_path(code).exists()  # still never readable


# ============================================================================================ A: the plugin tools

@pytest.fixture
def plugin(tmp_path, monkeypatch):
    saved_env = dict(os.environ)
    saved_picker = claude_tab.PICKER
    service.reset()
    claude_tab.lock_settings(tmp_path / "shield-data")
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 0.3)
    monkeypatch.setattr(claude_tab, "STATUS_WAIT_SECONDS", 0.3)
    yield
    service.reset()
    vault.KEY_STORE = None
    claude_tab.PICKER = saved_picker
    os.environ.clear()
    os.environ.update(saved_env)


def call(server, name: str, args: dict | None = None) -> tuple[bool, str]:
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(name, args or {})
            return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

    return asyncio.run(go())


def _no_secret(text: str, folder: Path) -> bool:
    return not any(s in text for s in ("Kerbrat", "Aurélien", "Brévanne", GRAND, "grand livre", "note", str(folder)))


def test_protect_answers_fast_with_the_progress_then_status_says_ready(plugin, dossier, slow):
    claude_tab.PICKER = lambda title, timeout: str(dossier)
    server = claude_tab.build_server()
    t0 = time.monotonic()
    err, text = call(server, "shield_protect_folder")
    assert time.monotonic() - t0 < 10.0
    assert not err, text
    assert "Le dossier choisi est maintenant protégé : DOSSIER_1." in text
    assert "Shield lit les documents de DOSSIER_1 sur cet ordinateur : 0 lu(s) sur 2 (document en cours : " \
           "page 120 sur 846)." in text
    assert "Les vrais noms restent sur cet ordinateur." in text and "shield_status" in text
    assert _no_secret(text, dossier) and not ENGLISH.search(text) and "—" not in text
    assert server._shield_scope.pinned == "DOSSIER_1"
    # A2: no list, no content, no name while the dossier is read
    for name, args in (("shield_list_documents", {"dossier": "DOSSIER_1"}),
                       ("shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_1"}),
                       ("shield_search", {"dossier": "DOSSIER_1", "query": "livraison"}),
                       ("shield_save_draft", {"dossier": "DOSSIER_1", "title": "Projet", "content": "Texte"})):
        err, text = call(server, name, args)
        assert not err, (name, text)
        assert "page 120 sur 846" in text and "Aucun document n'est montré" in text, (name, text)
        assert "DOC_" not in text and _no_secret(text, dossier), (name, text)
    t0 = time.monotonic()
    err, text = call(server, "shield_status")
    assert time.monotonic() - t0 < 1.0 and not err
    assert "RAGbase Shield 0.4.3" in text and "lu(s) sur 2" in text and "Ne faites rien d'autre" in text
    _, text = call(server, "shield_list_dossiers")
    assert "DOSSIER_1 : pas encore prêt." in text
    assert not list((service.default().registry.home / "vaults").parent.glob("**/*.pdf"))  # nothing copied
    slow.release.set()
    _wait(service.default(), "DOSSIER_1")
    _, text = call(server, "shield_status")
    assert "DOSSIER_1 est prêt : 2 document(s) trouvé(s), 2 lu(s)." in text and _no_secret(text, dossier)
    err, text = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert not err and "DOC_1" in text and "DOC_2" in text and "Kerbrat" not in text and "Brévanne" not in text
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_2"})
    assert not err and "rendez-vous" in text and "Kerbrat" not in text


def test_small_folder_answers_as_before(plugin, dossier, monkeypatch):
    fake = SlowRead(documents.read_text)
    fake.release.set()
    monkeypatch.setattr(documents, "read_text", fake)
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 8.0)
    claude_tab.PICKER = lambda title, timeout: str(dossier)
    err, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert not err
    assert "Le dossier choisi est maintenant protégé : DOSSIER_1." in text
    assert "2 document(s) trouvé(s), 2 lu(s)." in text and "Suite : shield_list_documents avec DOSSIER_1." in text
    assert "lit les documents" not in text


def test_protect_again_while_reading_and_too_long_answers(plugin, dossier, slow, monkeypatch):
    claude_tab.PICKER = lambda title, timeout: str(dossier)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    _, text = call(server, "shield_protect_folder")
    assert "Ce dossier est déjà protégé : DOSSIER_1. Sa lecture continue." in text
    slow.release.set()
    _wait(service.default(), "DOSSIER_1")
    # the same folder later, with a long document over its budget: counted and listed as not read
    fake = SlowRead(documents.read_text, too_long=True)
    fake.release.set()
    monkeypatch.setattr(documents, "read_text", fake)
    (dossier / GRAND).write_bytes(b"%PDF-1.4 fictif, version 2")
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 8.0)
    _, text = call(server, "shield_protect_folder")
    assert "Ce dossier était déjà protégé : DOSSIER_1. Shield l'a relu." in text
    assert "2 document(s) trouvé(s), 1 lu(s), 1 non lu(s) car trop long(s)." in text
    _, text = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert "non lu (trop long)" in text
    pdf_id = next(line.split(" |")[0] for line in text.splitlines() if "non lu (trop long)" in line)
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": pdf_id})
    assert err and "trop long pour Shield" in text


def test_tool_texts_tell_about_the_background_reading(plugin):
    server = claude_tab.build_server()

    async def tools():
        async with Client(server) as c:
            return {t.name: t.description for t in (await c.list_tools()).tools}

    desc = asyncio.run(tools())
    assert "arrière-plan" in desc["shield_protect_folder"] and "arrière-plan" in desc["shield_status"]
    assert "7. Shield lit un grand dossier en arrière-plan." in claude_tab.INSTRUCTIONS


def test_version_is_0_4_3():
    assert __version__ == "0.4.3"
    sys.path.insert(0, str(HERE.parent / "packaging" / "claude_plugin"))
    try:
        import shield_boot
    finally:
        sys.path.pop(0)
    assert shield_boot.VERSION == "0.4.3"


def test_reading_sentences_are_plain_french():
    states = [
        {"code": "DOSSIER_2", "state": "waiting", "total": None},
        {"code": "DOSSIER_2", "state": "reading", "total": 27, "done": 12, "page": 120, "pages": 846},
        {"code": "DOSSIER_2", "state": "reading", "total": 27, "done": 3, "page": 0, "pages": 0},
        {"code": "DOSSIER_2", "state": "masking", "total": 27, "masked": 5},
        {"code": "DOSSIER_2", "state": "failed", "total": 27},
        {"code": "DOSSIER_2", "state": "pending", "total": None},
    ]
    for st in states:
        text = claude_tab.reading_answer(st)
        assert "DOSSIER_2" in text and not ENGLISH.search(text) and "—" not in text
    assert "12 lu(s) sur 27 (document en cours : page 120 sur 846)." in claude_tab.reading_sentence(states[1])
    assert "3 lu(s) sur 27." in claude_tab.reading_sentence(states[2])
    assert "5 sur 27 terminé(s)" in claude_tab.reading_sentence(states[3])


# ============================================================================================ slow: the 800-page file

SLOW = os.environ.get("RAGBASE_SHIELD_SLOW_TESTS", "").strip() == "1"

_MEASURE = r"""
import json, os, resource, sys, time
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from ragbase_shield import documents, service
folder, home = Path(sys.argv[2]), Path(sys.argv[3])
os.environ["RAGBASE_SHIELD_HOME"] = str(home)
os.environ["RAGBASE_SHIELD_KEYRING"] = "0"
os.environ["RAGBASE_SHIELD_NER"] = "off"
t = time.monotonic()
res = documents.read_text(folder / "Grand livre des livraisons.pdf")
read_s = time.monotonic() - t
peak_read = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
s = service.Service(home)
t = time.monotonic()
code = s.protect_folder(folder)["code"]
ok = s.wait_reading(code, 600)
total_s = time.monotonic() - t
sm = s.reading_summary(code) or {}
docs = s.list_documents(code)
pdf = next(d for d in docs if d["kind"] == "pdf")
first = s.read_document(code, pdf["id"])["text"]
s.close()
scale = 1 if sys.platform == "darwin" else 1024
print(json.dumps({"read_s": read_s, "pages": res.pages, "chars": len(res), "peak_read_mb": peak_read * scale / 2**20,
                  "dossier_s": total_s, "ok": ok, "summary": {k: sm.get(k) for k in ("documents", "unreadable",
                  "too_long", "read_seconds", "seconds")}, "first": first[:3000]}))
"""


@pytest.mark.skipif(not SLOW, reason="slow: set RAGBASE_SHIELD_SLOW_TESTS=1 (800-page PDF, minutes)")
def test_800_page_dossier_is_read_in_time_with_flat_memory(tmp_path):
    folder = synth_pdf.make_dossier(tmp_path / "Dossier Brévanne", 800)
    script = tmp_path / "measure.py"
    script.write_text(_MEASURE, encoding="utf-8")
    out = subprocess.run([sys.executable, str(script), str(SRC), str(folder), str(tmp_path / "data")],
                         capture_output=True, text=True, timeout=900)
    assert out.returncode == 0, out.stderr[-2000:]
    m = json.loads(out.stdout.strip().splitlines()[-1])
    print({k: v for k, v in m.items() if k != "first"})
    assert m["pages"] == 800 and m["chars"] > 1_500_000
    assert m["read_s"] <= 120, m
    assert m["peak_read_mb"] < 700, m
    assert m["ok"] and m["dossier_s"] <= 300, m
    assert m["summary"]["documents"] == 27 and m["summary"]["too_long"] == 0
    assert synth_pdf.PERSON_EARLY not in m["first"] and "Corbaz" not in m["first"]
