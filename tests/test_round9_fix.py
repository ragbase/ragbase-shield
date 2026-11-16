"""Round 9 fixes (engine 0.4.3), one test or more for each finding of the two reviews. Invented text and synthetic
files only: no real person, no client data."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import synth_pdf
from ragbase_shield import claude_tab, documents, service
from ragbase_shield.documents import ReadTooLarge, ReadTooLong, read_text
from ragbase_shield.engine import parse_parties
from test_round9 import (GRAND, LATE_NAME, NOTE_TEXT, FakeClock, SlowRead, _wait, call, dossier, plugin,  # noqa: F401
                         slow, svc)


def _until(cond, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not cond() and time.monotonic() < deadline:
        time.sleep(0.02)
    return cond()


def _reading_threads() -> int:
    return sum(1 for t in threading.enumerate() if t.name.startswith("shield-reading-") and t.is_alive())


def _content_calls(s, code):
    return (lambda: s.list_documents(code), lambda: s.read_document(code, "DOC_2"),
            lambda: s.search(code, "rendez-vous"), lambda: s.save_draft(code, "Projet", "Texte"),
            lambda: s.document_folders(code))


# ============================================================ finding 1: two processes (two conversations), one folder

def test_another_service_never_reads_a_dossier_that_one_service_is_reading(tmp_path, dossier, slow):
    home = tmp_path / "data"
    other = service.Service(home)  # the second conversation started first: it has seen no mark yet
    first = service.Service(home)
    try:
        assert other.pending_readings() == {}
        code = first.protect_folder(dossier)["code"]
        assert _until(lambda: (first.reading_state(code) or {}).get("page") == 120)
        info = first._mark_info(code)
        assert info["owner"] == first._token and info["pid"] == os.getpid()
        st = other.reading_state(code)
        assert st["state"] == "pending" and st["elsewhere"]
        for c in _content_calls(other, code):
            with pytest.raises(service.ShieldError) as exc:
                c()
            assert exc.value.kind == "dossier_reading"
        assert other.resume_readings() == []  # no second reading of the same dossier
        assert other.protect_folder(dossier)["already_reading"]
        assert _reading_threads() == 1 and slow.calls == 1
        assert "Shield lit les documents de DOSSIER_1 sur cet ordinateur." in claude_tab.reading_answer(st)
        threading.Timer(0.3, slow.release.set).start()
        assert other.wait_reading(code, 20.0)  # waits for the other service's mark
        _wait(first, code)
        assert other.reading_state(code) is None
        note = next(d for d in other.list_documents(code) if d["kind"] == "txt")
        text = other.read_document(code, note["id"])["text"]
        assert LATE_NAME not in text and "Kerbrat" not in text
    finally:
        slow.release.set()
        first.close()
        other.close()


def test_a_stale_mark_of_another_service_is_read_again(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    other = service.Service(home)
    try:
        code = first.protect_folder(dossier)["code"]
        assert _until(lambda: (first.reading_state(code) or {}).get("page") == 120)
        old = time.time() - service.MARK_STALE_SECONDS - 30
        os.utime(first._mark_path(code), (old, old))  # untouched for 90 s: its owner hangs or is gone
        assert not other.reading_state(code).get("elsewhere")
        assert other.resume_readings() == [code]
    finally:
        slow.release.set()
        first.close()
        other.close()


def test_a_mark_whose_process_is_gone_is_free_at_once(tmp_path, dossier, slow):
    home = tmp_path / "data"
    first = service.Service(home)
    code = first.protect_folder(dossier)["code"]
    uuid = first.registry.get(code).uuid
    first.close()
    assert first._mark_path(code).stat().st_mtime < 1  # a closed service frees its marks at once
    out = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
    dead = int(out.stdout.strip())
    assert not service._pid_alive(dead) and service._pid_alive(os.getpid())
    path = home / service.READING_DIR_NAME / f"{code}.pending"
    other = service.Service(home)
    try:
        path.write_text(f"{uuid} {os.getpid()} someone-else\n", encoding="ascii")  # fresh, alive: another reader
        assert other._foreign(other._mark_info(code)) and other.resume_readings() == []
        path.write_text(f"{uuid} {dead} someone-else\n", encoding="ascii")  # fresh, but its process is gone
        assert not other._foreign(other._mark_info(code))
        slow.release.set()
        assert other.resume_readings() == [code]
        _wait(other, code)
        assert other.reading_state(code) is None and not path.exists()
    finally:
        other.close()


def test_the_reading_service_keeps_its_mark_fresh(svc, dossier, slow, monkeypatch):
    monkeypatch.setattr(service, "MARK_TOUCH_SECONDS", 0.05)
    code = svc.protect_folder(dossier)["code"]
    path = svc._mark_path(code)
    old = time.time() - 100
    os.utime(path, (old, old))
    assert _until(lambda: path.stat().st_mtime > time.time() - 5)
    slow.release.set()
    _wait(svc, code)


# ============================================================ finding 2: party names that end in "al"

@pytest.mark.parametrize("title,expected", [
    ("Valcourt c. Brenneval", [("PERSON", "Valcourt"), ("PERSON", "Brenneval")]),
    ("Martin c. Duval", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Martin c. Maréchal", [("PERSON", "Martin"), ("PERSON", "Maréchal")]),
    ("Dupont c. Laval", [("PERSON", "Dupont"), ("PERSON", "Laval")]),
    ("Bernard c. Percival", [("PERSON", "Bernard"), ("PERSON", "Percival")]),
    ("Martin c. Pascal", [("PERSON", "Martin"), ("PERSON", "Pascal")]),
    ("Martin c. Duval et autres", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Martin c. Duval et al.", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Martin c. Duval et al", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Martin c. Duval, consorts", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Martin c. Duval & cts", [("PERSON", "Martin"), ("PERSON", "Duval")]),
    ("Dupont et autres c. SNCF", [("PERSON", "Dupont"), ("ORG", "SNCF")]),
])
def test_title_parties_keep_their_last_letters(title, expected):
    assert parse_parties(title) == expected


def test_a_sub_folder_party_ending_in_al_is_hidden(svc, tmp_path):
    folder = tmp_path / "cabinet" / "Dossier Ormes"
    sub = folder / "Valcourt c. Brenneval"
    sub.mkdir(parents=True)
    (sub / "courrier.txt").write_text("Valcourt écrit à Brenneval le 3 mars 2026 au sujet du loyer.\n", encoding="utf-8")
    code = svc.protect_folder(folder)["code"]
    _wait(svc, code)
    text = svc.read_document(code, "DOC_1")["text"]
    assert "Brenneval" not in text and "Valcourt" not in text


# ============================================================ finding 3: the mark cannot be written

def test_a_new_dossier_is_never_registered_without_its_mark(svc, dossier, monkeypatch):
    def locked(self, code, uuid):
        raise PermissionError("held by another program")

    monkeypatch.setattr(service.Service, "_write_mark", locked)
    with pytest.raises(service.ShieldError):
        svc.protect_folder(dossier)
    assert svc.registry.folders() == {} and svc.pending_readings() == {}


def test_the_mark_is_written_again_when_a_program_holds_it_for_a_moment(svc, dossier, slow, monkeypatch):
    real = os.replace
    tries = []

    def flaky(src, dst, *a, **k):
        if str(dst).endswith(service._READING_SUFFIX) and len(tries) < 2:
            tries.append(dst)
            raise PermissionError("held for a moment")
        return real(src, dst, *a, **k)

    monkeypatch.setattr(service.os, "replace", flaky)
    code = svc.protect_folder(dossier)["code"]
    assert len(tries) == 2 and svc._mark_path(code).exists()
    assert not list(svc._mark_path(code).parent.glob("*.tmp"))
    slow.release.set()
    _wait(svc, code)


def test_a_reading_blocks_its_dossier_even_when_its_mark_cannot_be_written(svc, dossier, slow, monkeypatch):
    slow.release.set()
    code = svc.protect_folder(dossier)["code"]
    _wait(svc, code)
    slow.release.clear()

    def locked(self, code, uuid):
        raise PermissionError("held by another program")

    monkeypatch.setattr(service.Service, "_write_mark", locked)
    (dossier / GRAND).write_bytes(b"%PDF-1.4 fictif, version 2")
    svc.start_reading(code)
    assert not svc._mark_path(code).exists()
    for c in _content_calls(svc, code):
        with pytest.raises(service.ShieldError) as exc:
            c()
        assert exc.value.kind == "dossier_reading"
    slow.release.set()
    _wait(svc, code)
    assert len(svc.list_documents(code)) == 2


# ============================================================ finding 4: one page or one document that never ends

def test_the_budget_stops_a_reading_inside_one_heavy_page(tmp_path):
    path = synth_pdf.make_vector_pdf(tmp_path / "plan.pdf", 20_000, pages=1, heavy_page=1)
    seen = []
    with pytest.raises(ReadTooLong):
        documents._read_pdf_pypdf(path, progress=lambda d, t: seen.append(d), deadline=5.0, clock=FakeClock(1.0))
    assert seen == [0]  # stopped inside page 1, not after it
    text = documents._read_pdf_pypdf(path, deadline=1e9, clock=FakeClock(1.0))[0]
    assert "Plan fictif du lot 3" in text
    with pytest.raises(ReadTooLong):  # the public reader too (a one-page plan goes to pypdf)
        read_text(path, budget=3.0, clock=FakeClock(1.0))


class Hang:
    """Fake ``documents.read_text``: the long PDF stops at one page and never ends until ``release``."""

    def __init__(self, real):
        self.real = real
        self.release = threading.Event()

    def __call__(self, path, *, progress=None, budget=None, clock=time.monotonic, max_chars=None):
        if Path(path).name == GRAND:
            if progress:
                progress(57, 300)
            self.release.wait(30)
            return documents.ReadResult("Registre fictif.", pages=300)
        return self.real(path, progress=progress, budget=budget, clock=clock, max_chars=max_chars)


def test_a_reading_stuck_inside_one_document_gives_up_and_frees_the_others(svc, dossier, tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENT_TIME_BUDGET", 0.2)
    monkeypatch.setattr(service, "STUCK_MARGIN_SECONDS", 0.2)
    fake = Hang(documents.read_text)
    monkeypatch.setattr(documents, "read_text", fake)
    other = tmp_path / "cabinet" / "Dossier Quillardet"
    other.mkdir()
    (other / "lettre.txt").write_text("Lettre fictive de Mme Odile Quillardet.\n", encoding="utf-8")
    try:
        a = svc.protect_folder(dossier)["code"]
        b = svc.protect_folder(other)["code"]
        assert _until(lambda: (svc.reading_state(a) or {}).get("stuck"))
        st = svc.reading_state(a)
        assert st["state"] == "failed" and st["gave_up"]
        assert "Redémarrez l'application Claude" in claude_tab.reading_sentence(st)
        assert "appelez de nouveau shield_status" not in claude_tab.reading_answer(st)
        t0 = time.monotonic()
        assert svc.wait_reading(a, 5.0) is False and time.monotonic() - t0 < 1.0
        _wait(svc, b, 10.0)  # the stuck reading no longer holds the other dossier back
        assert svc.reading_state(b) is None
        with pytest.raises(service.ShieldError):
            svc.list_documents(a)  # still never readable
    finally:
        fake.release.set()
        monkeypatch.setattr(service, "STUCK_MARGIN_SECONDS", 600.0)  # the rest of the reading is not stuck
    _wait(svc, a, 20.0)


# ============================================================ finding 5: the same codes as the 0.4.2 one-step reading

_EQ_TEXTS = (
    "Le témoin Kerbrat-Lussac a confirmé la date. Aurélien a rappelé le cabinet le lendemain.",
    "Selon M. Kerbrat-Lussac, la livraison était incomplète. Copie à Mme Corbaz-Thévenet.",
    "Réunion avec le gérant de Brévanne Logistique SAS. Kerbrat-Lussac était absent.",
    "Note interne : appeler Aurélien Kerbrat au sujet du bon de livraison.",
    "Le conseil de Lestrade conteste la facture. Morvan maintient sa demande.",
)


def _eq_folder(root: Path) -> Path:
    folder = root / "Morvan c. Lestrade"
    sub = folder / "Valcourt c. Brenneval"
    sub.mkdir(parents=True)
    for i in range(8):
        (folder / f"note {i + 1:02d}.txt").write_text(_EQ_TEXTS[i % len(_EQ_TEXTS)] + f" Pièce {i + 1}.\n",
                                                      encoding="utf-8")
    (sub / "courrier Valcourt.txt").write_text("Valcourt écrit à Brenneval le 3 mars 2026 au sujet du loyer.\n",
                                               encoding="utf-8")
    (folder / "mail.eml").write_text(
        "From: Cabinet <contact@cabinet-exemple.fr>\nTo: Ysaline Corbaz-Thevenet <ysaline.corbaz@exemple.fr>\n"
        "Subject: Point\nContent-Type: text/plain; charset=utf-8\n\nBonjour Mme Corbaz-Thévenet, voici le point avec "
        "Kerbrat-Lussac.\n", encoding="utf-8")
    synth_pdf.make_long_pdf(folder / "Grand livre.pdf", 4)
    return folder


def _read_all(s, code) -> dict:
    out = {"__list__": [(d["id"], d["masked_path"]) for d in s.list_documents(code)]}
    for doc, _name in out["__list__"]:
        parts, start = [], 0
        while True:
            r = s.read_document(code, doc, start, service.MAX_READ_CHARS)
            parts.append(r["text"])
            if r["next"] is None:
                break
            start = r["next"]
        out[doc] = "".join(parts)
    return out


def test_background_reading_gives_the_texts_of_the_0_4_2_one_step_reading(tmp_path):
    folder = _eq_folder(tmp_path / "cabinet")
    old = service.Service(tmp_path / "old")
    new = service.Service(tmp_path / "new")
    try:
        r = old.add_dossier(folder)  # what 0.4.2 shield_protect_folder did, in one tool call
        if old.register_folder_parties(r["code"]):
            old.scan_dossier(r["code"])
        before = _read_all(old, r["code"])
        code = new.protect_folder(folder)["code"]
        _wait(new, code, 120.0)
        after = _read_all(new, code)
    finally:
        old.close()
        new.close()
    assert before == after
    blob = repr(after)
    for name in ("Kerbrat", "Aurélien", "Corbaz", "Brévanne", "Valcourt", "Brenneval", "Morvan", "Lestrade"):
        assert name not in blob, name


# ============================================================ finding 6: a text over the size limit

def test_a_text_over_the_size_limit_gets_one_true_answer(plugin, tmp_path, monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCUMENT_CHARS", 5_000)
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 8.0)
    folder = tmp_path / "cabinet" / "Dossier Quillardet"
    folder.mkdir(parents=True)
    (folder / "export.txt").write_text("Ligne fictive du registre des livraisons du dépôt.\n" * 200, encoding="utf-8")
    (folder / "note.txt").write_text(NOTE_TEXT, encoding="utf-8")
    claude_tab.PICKER = lambda title, timeout: str(folder)
    server = claude_tab.build_server()
    _, text = call(server, "shield_protect_folder")
    assert "2 document(s) trouvé(s), 1 lu(s), 1 non lu(s) car trop long(s)." in text and "illisible" not in text
    _, text = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    lines = [line for line in text.splitlines() if "non lu (trop long)" in line]
    assert len(lines) == 1
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": lines[0].split(" |")[0]})
    assert err and text == claude_tab.ERRORS["document_too_large"] and "trois minutes" not in text


def test_a_pdf_over_the_size_limit_stops_early_and_a_smaller_one_reads_the_same(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 6)
    full = read_text(path)
    for limit in (40, 0):  # pdfplumber, then pypdf
        monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", limit)
        seen = []
        with pytest.raises(ReadTooLarge) as exc:
            read_text(path, max_chars=3_000, progress=lambda d, t: seen.append(d))
        assert str(exc.value) == documents.READ_TOO_LARGE and max(seen) < 6
        assert read_text(path, max_chars=10 ** 7) == read_text(path)
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 40)
    assert read_text(path, max_chars=len(full)) == full  # exactly at the limit: read


def test_service_counts_a_document_over_the_size_limit_as_too_long(svc, tmp_path, monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCUMENT_CHARS", 5_000)
    folder = tmp_path / "cabinet" / "Dossier Ormes"
    folder.mkdir(parents=True)
    (folder / "export.txt").write_text("Ligne fictive du registre.\n" * 400, encoding="utf-8")
    code = svc.protect_folder(folder)["code"]
    _wait(svc, code)
    sm = svc.reading_summary(code)
    assert sm["too_long"] == 1 and sm["unreadable"] == 0
    assert svc.list_documents(code)[0]["not_read"] == "too_large"
    with pytest.raises(service.ShieldError) as exc:
        svc.read_document(code, "DOC_1")
    assert exc.value.kind == "document_too_large"


# ============================================================ finding 7: Claude cannot wait, so shield_status waits

def test_status_waits_for_the_end_of_the_reading(plugin, dossier, slow, monkeypatch):
    monkeypatch.setattr(claude_tab, "STATUS_WAIT_SECONDS", 10.0)
    claude_tab.PICKER = lambda title, timeout: str(dossier)
    server = claude_tab.build_server()
    _, text = call(server, "shield_protect_folder")
    assert "puis appelez de nouveau shield_status" in text
    threading.Timer(0.5, slow.release.set).start()
    t0 = time.monotonic()
    _, text = call(server, "shield_status")
    dt = time.monotonic() - t0
    assert 0.3 < dt < 9.0, dt
    assert "DOSSIER_1 est prêt" in text and "appelez de nouveau" not in text


def test_a_reading_shield_gave_up_on_asks_no_new_call(plugin, dossier, slow, monkeypatch):
    monkeypatch.setattr(claude_tab, "STATUS_WAIT_SECONDS", 5.0)
    slow.release.set()
    monkeypatch.setattr(service.Service, "_build_directory", lambda self, d: 1 / 0)
    claude_tab.PICKER = lambda title, timeout: str(dossier)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    for _ in range(service.MAX_READING_FAILURES + 1):
        t0 = time.monotonic()
        _, text = call(server, "shield_status")
        assert time.monotonic() - t0 < 4.0
    assert "Redémarrez l'application Claude" in text and "appelez de nouveau" not in text
    err, text = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert not err and "Redémarrez l'application Claude" in text and "appelez" not in text


def test_no_text_asks_claude_to_wait_some_seconds():
    for st in ({"code": "DOSSIER_2", "state": "reading", "total": 27, "done": 3},
               {"code": "DOSSIER_2", "state": "pending", "total": None}):
        text = claude_tab.reading_answer(st)
        assert "Dites à l'avocat où en est la lecture, puis appelez de nouveau shield_status." in text
        assert "attendez" not in text
    assert "attendez quelques secondes" not in claude_tab.INSTRUCTIONS
    assert "jusqu'à 15 secondes" in claude_tab.INSTRUCTIONS


# ============================================================ finding 9: a ready dossier never waits for another masking

def test_a_ready_dossier_answers_while_another_dossier_is_masked(svc, tmp_path, monkeypatch):
    ready = tmp_path / "cabinet" / "Dossier Ormes"
    ready.mkdir(parents=True)
    (ready / "note.txt").write_text(NOTE_TEXT, encoding="utf-8")
    c = svc.protect_folder(ready)["code"]
    _wait(svc, c)
    busy = tmp_path / "cabinet" / "Dossier Quillardet"
    busy.mkdir()
    (busy / "lettre.txt").write_text("Lettre fictive de Mme Odile Quillardet.\n", encoding="utf-8")
    entered, gate = threading.Event(), threading.Event()
    real = service.Service._doc_make

    def slow_make(self, d, ref, st, raw, m):
        if "Quillardet" in str(ref.path):
            entered.set()
            gate.wait(10)
        return real(self, d, ref, st, raw, m)

    monkeypatch.setattr(service.Service, "_doc_make", slow_make)
    try:
        a = svc.protect_folder(busy)["code"]
        assert entered.wait(5)
        t0 = time.monotonic()
        text = svc.read_document(c, "DOC_1")["text"]
        assert len(svc.list_documents(c)) == 1 and svc.search(c, "rendez-vous")
        assert time.monotonic() - t0 < 1.0
        assert "rendez-vous" in text and "Kerbrat" not in text
    finally:
        gate.set()
    _wait(svc, a)


# ============================================================ finding 10: one heavy page in a short PDF

def test_a_short_pdf_with_a_heavy_page_is_read_with_pypdf(tmp_path, monkeypatch):
    heavy = synth_pdf.make_vector_pdf(tmp_path / "plan.pdf", 15_000)
    light = synth_pdf.make_vector_pdf(tmp_path / "plan leger.pdf", 300)
    assert documents._pdf_heavy(heavy) and not documents._pdf_heavy(light)
    used = []
    real_plumber, real_pypdf = documents._read_pdf_plumber, documents._read_pdf_pypdf
    monkeypatch.setattr(documents, "_read_pdf_plumber", lambda *a, **k: used.append("plumber") or real_plumber(*a, **k))
    monkeypatch.setattr(documents, "_read_pdf_pypdf", lambda *a, **k: used.append("pypdf") or real_pypdf(*a, **k))
    res = read_text(heavy)
    assert used == ["pypdf"] and res.pages == 3 and "Plan fictif du lot 3" in res.text
    used.clear()
    read_text(light)
    assert used == ["plumber"]
