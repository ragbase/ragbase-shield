"""Round 10 (engine 0.4.4): the dossier stays ready between starts (A), very long documents (B), the start handshake
(C1), four Windows message fixes (F1 to F4) and the version (D). Invented text and synthetic files only: no real
person, no client data. A "new process" is a new Service object on the same data folder (service.reset())."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from mcp import Client

import synth_pdf
from ragbase_shield import __version__, claude_tab, documents, kept, service, vault

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
NAMES = ("Ysaline", "Corbaz", "Kerbrat", "Aurélien", "Brévanne", "Odilon", "Quillardet", "Valmoray", "Ternesse",
         "Ferracci", "Daubel", "Maëlle", "Kervadec")
SENTENCE = "le bon de livraison signé au dépôt de Lorient"
ENGLISH = re.compile(r"\b(the|masked|error|internal|unknown|vault|reading|kept|cache)\b", re.I)


# ============================================================================================ helpers

def make_folder(root: Path) -> Path:
    """A small client folder: texts, a note, an e-mail, a web page, a short PDF (ruled tables), a sub-folder that names
    opposing parties, and a file name with a person's name."""
    f = root / "cabinet" / "Dossier Valmoray c. Ternesse"
    (f / "Ferracci c. Daubel").mkdir(parents=True)
    (f / "note de synthese.txt").write_text(
        f"Note fictive. Mme {synth_pdf.PERSON_EARLY} a signé {SENTENCE} le 3 mars 2026. M. Odilon Quillardet, "
        "gérant de la société Brévanne Logistique SAS, conteste la facture. IBAN FR76 3000 6000 0112 3456 7890 189.\n"
        * 6, encoding="utf-8")
    (f / "courrier Maëlle Kervadec.md").write_text(
        "# Courrier fictif\n\nMadame Maëlle Kervadec écrit au cabinet au sujet de la livraison du 4 avril 2026. "
        "Elle cite le contrat de transport et l'article 4 du code civil.\n", encoding="utf-8")
    (f / "echange.eml").write_text(
        "From: Ysaline Corbaz <y.corbaz@exemple-fictif.fr>\nTo: Cabinet <contact@cabinet-exemple.fr>\n"
        "Subject: Livraison\nContent-Type: text/plain; charset=utf-8\n\nBonjour, je vous joins la facture de "
        "M. Odilon Quillardet. Bien à vous, Ysaline Corbaz\n", encoding="utf-8")
    (f / "Ferracci c. Daubel" / "page.html").write_text(
        "<html><body><p>Audience fictive : M. Ferracci contre Mme Daubel, renvoi au 12 mai 2026. Le bon de "
        "livraison est produit.</p></body></html>", encoding="utf-8")
    synth_pdf.make_long_pdf(f / "registre.pdf", 3)
    return f


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    saved_env = dict(os.environ)
    saved_picker = claude_tab.PICKER
    service.reset()
    claude_tab.lock_settings(tmp_path / "shield-data")
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 20.0)
    monkeypatch.setattr(claude_tab, "STATUS_WAIT_SECONDS", 0.3)
    yield tmp_path / "shield-data"
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


def _wait(code: str, timeout: float = 60.0) -> None:
    assert service.default().wait_reading(code, timeout), "the reading did not end"


class Reads:
    """Counts every reading of a file of the lawyer (document reader and PDF page count); ``fail`` makes them fail."""

    def __init__(self, monkeypatch, fail: bool = False):
        self.calls = 0
        self.fail = fail
        real_read, real_pages = documents.read_text, service.Service._pdf_pages

        def read(path, **kw):
            self.calls += 1
            if self.fail:
                raise AssertionError("a file of the lawyer was read")
            return real_read(path, **kw)

        def pages(svc, path, m, z):
            key = (str(path), m, z)
            if key not in svc._pages:
                self.calls += 1
                if self.fail:
                    raise AssertionError("a PDF of the lawyer was opened")
            return real_pages(svc, path, m, z)

        monkeypatch.setattr(documents, "read_text", read)
        monkeypatch.setattr(service.Service, "_pdf_pages", pages)


def answers(server, code: str) -> dict:
    """Every answer of the A4 list: the documents, the full read of every document, three searches, a saved draft
    (md) and the status."""
    out = {}
    _, out["list"] = call(server, "shield_list_documents", {"dossier": code})
    for doc in sorted(set(re.findall(r"^(DOC_[0-9]+) \|", out["list"], re.M))):
        start, parts = 0, []
        while start is not None:
            err, text = call(server, "shield_read_document", {"dossier": code, "document": doc, "start": start,
                                                              "max_chars": 500})
            parts.append(text)
            m = re.search(r"suite : start=([0-9]+)\]", text)
            start = int(m.group(1)) if m and not err else None
        out[f"read {doc}"] = "\n".join(parts)
    for q in ("livraison", "PERSONNE_A", "bon de livraison", "facture contestée"):
        _, out[f"search {q}"] = call(server, "shield_search", {"dossier": code, "query": q})
    _, saved = call(server, "shield_save_draft", {"dossier": code, "title": "Note PERSONNE_A",
                                                  "content": "# Note\n\nPERSONNE_A et SOCIETE_A, DOC_2.", "format": "md"})
    out["save"] = re.sub(r"OUTPUT_[0-9]+", "OUTPUT_n", saved)
    _, out["status"] = call(server, "shield_status")
    return out


def protect(folder: Path) -> tuple[object, str, str]:
    claude_tab.PICKER = lambda title, timeout: str(folder)
    server = claude_tab.build_server()
    err, text = call(server, "shield_protect_folder")
    assert not err, text
    code = re.search(r"DOSSIER_[0-9]+", text).group(0)
    _wait(code)
    return server, code, text


def first_reading(tmp_path) -> tuple[Path, str, dict]:
    folder = make_folder(tmp_path)
    server, code, _ = protect(folder)
    return folder, code, answers(server, code)


def new_process() -> None:
    service.reset()


def kept_files(data: Path) -> list[Path]:
    return sorted(p for p in (data / "kept").rglob("*") if p.is_file())


# ============================================================================================ A: kept sets

def test_unchanged_files_give_a_ready_dossier_with_zero_reads_and_identical_answers(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    assert "Kervadec" not in before["list"] and "PERSONNE_" in before["read DOC_1"] + before["read DOC_2"]
    assert any(p.name.startswith("m-") for p in kept_files(plugin))
    new_process()
    reads = Reads(monkeypatch, fail=True)  # A4: zero reads of the lawyer's files
    claude_tab.PICKER = lambda title, timeout: str(folder)
    server = claude_tab.build_server()
    t0 = time.monotonic()
    err, text = call(server, "shield_protect_folder")
    assert time.monotonic() - t0 < 5.0
    assert not err and f"Ce dossier était déjà protégé : {code}. Il est prêt." in text, text
    assert "Shield lit" not in text and "relu" not in text
    after = answers(server, code)
    assert reads.calls == 0
    for key in before:
        assert after[key] == before[key], key
    assert service.default().pending_readings() == {}


def test_a_first_call_with_no_protect_also_uses_the_kept_set(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    new_process()
    reads = Reads(monkeypatch, fail=True)
    server = claude_tab.build_server()
    _, text = call(server, "shield_list_documents", {"dossier": code})
    assert text == before["list"] and reads.calls == 0


def _second_start_reads(monkeypatch, code: str) -> int:
    """New process: whether the kept set is used (0) or the dossier is read again (number of file reads)."""
    new_process()
    reads = Reads(monkeypatch)
    svc = service.default()
    ready = svc._kset_ready(code)
    if not ready:
        svc.start_reading(code)
        _wait(code)
    svc.list_documents(code)
    return 0 if ready else max(1, reads.calls)


def _set_files(data: Path, code: str) -> tuple[list[Path], list[Path]]:
    files = sorted((data / "kept" / code).iterdir())
    return [p for p in files if p.name.startswith("m-")], [p for p in files if not p.name.startswith("m-")]


CHANGES = {
    "mtime": lambda f, data, code: os.utime(f / "echange.eml", ns=(1_700_000_000_000_000_000,) * 2),
    "size": lambda f, data, code: (f / "echange.eml").open("a", encoding="utf-8").write("Post-scriptum fictif.\n"),
    "file_added": lambda f, data, code: (f / "ajout.txt").write_text("Mme Ondine Valcrest écrit.\n", encoding="utf-8"),
    "file_removed": lambda f, data, code: (f / "echange.eml").unlink(),
    "lexicon": lambda f, data, code: service.default().register(code, "PERSON", "Ondine Valcrest"),
    "keep_clear": lambda f, data, code: service.default().keep_clear(code, "PERSONNE_A", True),
    "setting": lambda f, data, code: service.default().set_dossier_setting(code, "language", "fr"),
    "entry_corrupted": lambda f, data, code: _flip(_set_files(data, code)[1][0]),
    "entry_missing": lambda f, data, code: _set_files(data, code)[1][0].unlink(),
    "manifest_cut": lambda f, data, code: _cut(_set_files(data, code)[0][0]),
    "other_dossier": lambda f, data, code: _other_dossier(f),
}


def _flip(p: Path) -> None:
    b = bytearray(p.read_bytes())
    b[len(b) // 2] ^= 0x01
    p.write_bytes(bytes(b))


def _cut(p: Path) -> None:
    p.write_bytes(p.read_bytes()[: len(p.read_bytes()) // 2])


def _other_dossier(f: Path) -> None:
    other = f.parent / "Dossier Ondine"
    other.mkdir()
    (other / "a.txt").write_text("Mme Ondine Valcrest et M. Corentin Faubeau.\n", encoding="utf-8")
    service.default().add_dossier(other)


@pytest.mark.parametrize("cause", sorted(CHANGES))
def test_each_cause_alone_gives_a_full_reading(plugin, tmp_path, monkeypatch, cause):
    folder, code, before = first_reading(tmp_path)
    CHANGES[cause](folder, plugin, code)
    assert _second_start_reads(monkeypatch, code) > 0, cause
    # the kept set is replaced at the end of the new reading, and the next start uses it
    assert _second_start_reads(monkeypatch, code) == 0, cause


def test_engine_version_or_rules_fingerprint_changed_gives_a_full_reading(plugin, tmp_path, monkeypatch):
    folder, code, _ = first_reading(tmp_path)
    with monkeypatch.context() as m:
        m.setattr(service, "__version__", "9.9.9")
        assert _second_start_reads(m, code) > 0
    new_process()
    assert not service.default()._kset_ready(code)  # the set of "9.9.9" is not used by 0.4.4
    _second_start_reads(monkeypatch, code)
    with monkeypatch.context() as m:
        m.setattr(kept, "RULES_REVISION", kept.RULES_REVISION + "-changed")
        assert _second_start_reads(m, code) > 0
    assert kept.rules_fingerprint() != ""


def test_a_manifest_of_another_dossier_id_is_not_used(plugin, tmp_path, monkeypatch):
    folder, code, _ = first_reading(tmp_path)
    new_process()
    svc = service.default()
    d = svc.registry.get(code)
    man, payloads = svc._kset_store().load(d)
    man = {k: v for k, v in man.items() if k not in ("entries", "gen", "format")}
    man["dossier"] = "0" * 32
    assert svc._kset_store().write(d, man, payloads)
    assert _second_start_reads(monkeypatch, code) > 0
    # a set of another dossier (other key) copied in: does not decrypt, counts as absent
    other = tmp_path / "autre"
    other.mkdir()
    (other / "b.txt").write_text("Texte fictif.\n", encoding="utf-8")
    service.default().protect_folder(other)
    _wait("DOSSIER_2")
    for p in (plugin / "kept" / code).iterdir():
        p.unlink()
    for p in (plugin / "kept" / "DOSSIER_2").iterdir():
        shutil.copy(p, plugin / "kept" / code / p.name)
    assert _second_start_reads(monkeypatch, code) > 0


def test_a_document_that_failed_for_a_cause_that_can_pass_is_never_kept(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    real = documents.read_text

    def locked(path, **kw):
        if Path(path).name == "echange.eml":
            raise documents.ReadLocked()
        return real(path, **kw)

    with monkeypatch.context() as m:
        m.setattr(documents, "read_text", locked)
        server, code, text = protect(folder)
        assert "1 illisible(s)" in text
    assert not (plugin / "kept" / code).exists() or not _set_files(plugin, code)[0]
    assert _second_start_reads(monkeypatch, code) > 0  # read again; now the file opens: kept
    assert _second_start_reads(monkeypatch, code) == 0


def test_a_too_long_reading_is_never_kept(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    real = documents.read_text

    def slow(path, **kw):
        if Path(path).suffix == ".pdf":
            raise documents.ReadTooLong()
        return real(path, **kw)

    with monkeypatch.context() as m:
        m.setattr(documents, "read_text", slow)
        _, code, text = protect(folder)
        assert "1 non lu(s) car trop long(s)" in text
    assert not (plugin / "kept" / code).exists() or not _set_files(plugin, code)[0]


def test_two_server_processes_share_one_data_folder(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    service.reset()
    env = dict(os.environ, PYTHONPATH=str(SRC), RAGBASE_SHIELD_KEYRING="0")
    script = ("import sys\nfrom pathlib import Path\nfrom ragbase_shield import claude_tab, service, documents\n"
              "def boom(*a, **k):\n    raise SystemExit('read')\n"
              "documents.read_text = boom\n"
              f"claude_tab.lock_settings(Path({str(plugin)!r}))\n"
              "svc = service.default()\n"
              f"print(svc._kset_ready({code!r}), len(svc.list_documents({code!r})))\n")
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env, timeout=120)
    assert out.stdout.strip() == "True 5", out.stdout + out.stderr[-2000:]


def test_a_reader_gets_a_whole_set_while_another_process_replaces_it(plugin, tmp_path):
    folder, code, _ = first_reading(tmp_path)
    svc = service.default()
    d = svc.registry.get(code)
    store_a, store_b = kept.KeptStore(plugin), kept.KeptStore(plugin)
    man, _payloads = store_a.load(d)
    base = {k: v for k, v in man.items() if k not in ("entries", "gen", "format")}

    def version(tag: str) -> tuple[dict, dict]:
        payloads = {f"DOC_{i}": kept.pack({"tag": tag}, {"masked": tag * 2000}) for i in range(1, 6)}
        return dict(base, summary={"tag": tag}), payloads

    stop = threading.Event()
    errors: list = []

    def writer(store, tag):
        while not stop.is_set():
            m, p = version(tag)
            store.write(d, m, p)

    def reader():
        seen = 0
        while not stop.is_set():
            got = kept.KeptStore(plugin).load(d)
            if got is None:
                continue
            m, payloads = got
            if "tag" not in (m.get("summary") or {}):
                continue  # the set of the first reading, before the writers
            tags = {kept.unpack(p)[0].get("tag") for p in payloads.values()}
            if tags != {m["summary"]["tag"]}:
                errors.append(tags)
            seen += 1
        errors.append(("seen", seen))

    threads = [threading.Thread(target=writer, args=(store_a, "X")), threading.Thread(target=writer, args=(store_b, "Y")),
               threading.Thread(target=reader)]
    for t in threads:
        t.start()
    time.sleep(2.0)
    stop.set()
    for t in threads:
        t.join(10)
    mixes = [e for e in errors if not (isinstance(e, tuple) and e[0] == "seen")]
    seen = [e[1] for e in errors if isinstance(e, tuple) and e[0] == "seen"]
    assert not mixes and seen and seen[0] > 0


def test_a_kill_between_the_entries_and_the_manifest_gives_a_full_reading(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    real_write = kept.KeptStore._write_file

    def killed(self, folder_, name, data):
        if name.startswith("m-"):
            raise KeyboardInterrupt("killed")  # the process stops: entries on disk, no manifest
        return real_write(self, folder_, name, data)

    with monkeypatch.context() as m:
        m.setattr(kept.KeptStore, "_write_file", killed)
        with pytest.raises(KeyboardInterrupt):
            svc = service.default()
            code = svc.protect_folder(folder)["code"]
            job = svc._reads[code]
            job.finished.wait(60)
            d = svc.registry.get(code)
            kept.KeptStore(plugin).write(d, {"dossier": d.uuid}, {"DOC_1": kept.pack({}, {"masked": "x"})})
    code = "DOSSIER_1"
    orphans = [p for p in (plugin / "kept" / code).iterdir() if not p.name.startswith("m-")]
    assert orphans and not _set_files(plugin, code)[0]
    assert _second_start_reads(monkeypatch, code) > 0
    monkeypatch.setattr(kept, "ORPHAN_SECONDS", 0.0)
    service.default().clean_kept()
    assert not set(orphans) & set((plugin / "kept" / code).iterdir())  # the orphans are deleted at a start


def test_a_rename_that_fails_as_on_windows(plugin, tmp_path, monkeypatch):
    real = os.replace
    fails = {"n": 2}

    def flaky(src, dst):
        if fails["n"] > 0:
            fails["n"] -= 1
            e = PermissionError(13, "held by another process")
            e.winerror = 32
            raise e
        return real(src, dst)

    monkeypatch.setattr(kept, "REPLACE_WAIT", 0.01)
    monkeypatch.setattr(kept.os, "replace", flaky)
    folder, code, _ = first_reading(tmp_path)
    assert _set_files(plugin, code)[0]  # written after two failed tries
    fails["n"] = 10 ** 6  # always held: the write gives up, the reading does not fail
    (folder / "nouveau.txt").write_text("Texte fictif.\n", encoding="utf-8")
    new_process()
    svc = service.default()
    svc.start_reading(code)
    _wait(code)
    assert svc.reading_state(code) is None and len(svc.list_documents(code)) == 6
    assert not _set_files(plugin, code)[0]
    monkeypatch.setattr(kept.os, "replace", real)
    assert _second_start_reads(monkeypatch, code) > 0  # simply read again at the next start


def test_names_on_disk_are_codes_and_random_ids_only(plugin, tmp_path):
    folder, code, _ = first_reading(tmp_path)
    files = kept_files(plugin)
    assert files
    for p in files:
        rel = p.relative_to(plugin / "kept").as_posix()
        assert re.fullmatch(r"DOSSIER_[0-9]+/(m-[0-9]{20}-[0-9a-f]{8}|[0-9a-f]{8}\.[0-9]+)\.bin", rel), rel
        for word in NAMES + ("note", "synthese", "courrier", "echange", "registre", "page", "Valmoray"):
            assert word.lower() not in rel.lower()
        assert len(str(p)) - len(str(plugin)) < 60  # short paths (Windows data folder)


def test_kept_bytes_hold_no_plain_text(plugin, tmp_path):
    first_reading(tmp_path)
    blobs = b"".join(p.read_bytes() for p in kept_files(plugin))
    for needle in (SENTENCE, "Quillardet", "Corbaz", synth_pdf.PERSON_EARLY, "livraison", "PERSONNE_A", "DOC_1"):
        for enc in ("utf-8", "utf-16-le", "latin-1"):
            try:
                b = needle.encode(enc)
            except UnicodeEncodeError:
                continue
            assert b not in blobs, needle


def test_the_last_check_still_runs_on_kept_text(plugin, tmp_path, monkeypatch):
    folder, code, before = first_reading(tmp_path)
    svc = service.default()
    d = svc.registry.get(code)
    ent = next(e for e in d.all() if e.kind == "PERSON" and "Quillardet" in e.value)
    store = svc._kset_store()
    man, payloads = store.load(d)
    doc = next(k for k in payloads)
    meta, texts = kept.unpack(payloads[doc])
    planted = f"Témoin fictif : {ent.value}. " + texts["masked"]
    texts = dict(texts, masked=planted, masked0=planted)
    payloads[doc] = kept.pack(meta, texts)
    store.write(d, {k: v for k, v in man.items() if k not in ("entries", "gen", "format")}, payloads)
    new_process()
    reads = Reads(monkeypatch, fail=True)
    server = claude_tab.build_server()
    err, text = call(server, "shield_read_document", {"dossier": code, "document": doc, "max_chars": 500})
    assert not err and reads.calls == 0
    assert "Quillardet" not in text and f"Témoin fictif : {ent.code}." in text
    # exactly as a fresh text holding the same value
    assert service.default().guard_parts([f"Témoin fictif : {ent.value}."], code) == [f"Témoin fictif : {ent.code}."]


def test_search_on_the_kept_shadow_equals_search_on_the_text(tmp_path):
    """The search text of a kept entry gives byte for byte the results of the original text."""
    svc = service.Service(tmp_path / "data")
    try:
        f = make_folder(tmp_path)
        code = svc.add_dossier(f)["code"]
        d = svc.registry.get(code)
        queries = ["livraison", "bon de livraison", "facture", "Corbaz", "PERSONNE_A", "gérant société", "2026",
                   "article 4", "transport", "SOCIETE_A facture", "Ysaline", "mars"]
        fresh = {q: svc.search(code, q) for q in queries}
        for ref in d.documents():
            key = (code, ref.id)
            e = svc._docs[key]
            shadow = service._search_shadow(e.raw, e.alignment)
            if e.alignment is not None:
                assert shadow is not None and len(shadow) == len(e.raw)
                for word in ("Corbaz", "Quillardet", "Kervadec"):
                    assert word not in shadow
            svc._docs[key] = service._CachedDoc(
                mtime_ns=e.mtime_ns, size=e.size, version=e.version, raw=None, masked=e.masked,
                alignment=e.alignment, needs_ocr=e.needs_ocr, pages=e.pages, warnings=e.warnings, masked0=e.masked0,
                align0=e.align0, epoch=e.epoch, shadow=shadow)
        for q in queries:
            assert svc.search(code, q) == fresh[q], q
    finally:
        svc.close()


def test_shadow_keeps_word_limits():
    for ch in "aé9ŒßŁ":
        assert service._shadow_char(ch) == "x"
    for ch in " \n\u00a0\u200b\u0301":
        assert service._shadow_char(ch) == ch
    for ch in "'-.,&\u03b1":
        assert service._shadow_char(ch) == "*"  # never a letter or a digit: the same word limits


def test_removed_dossier_loses_its_kept_set_and_clean_at_start(plugin, tmp_path):
    folder, code, _ = first_reading(tmp_path)
    assert (plugin / "kept" / code).exists()
    service.default().remove_dossier(code)
    assert not (plugin / "kept" / code).exists()
    ghost = plugin / "kept" / "DOSSIER_77"
    ghost.mkdir(parents=True)
    (ghost / "m-00000000000000000001-abcdef01.bin").write_bytes(b"x")
    assert service.default().clean_kept() == ["DOSSIER_77"] and not ghost.exists()


def test_kept_dossier_says_ready_in_plain_french(plugin, tmp_path):
    folder, code, _ = first_reading(tmp_path)
    new_process()
    server, code2, text = protect(folder)
    assert code2 == code
    assert not ENGLISH.search(text) and "—" not in text
    _, status = call(server, "shield_status")
    assert f"{code} est prêt : 5 document(s) trouvé(s), 5 lu(s)." in status


# ============================================================================================ B: long documents

def test_limits_are_six_million():
    assert service.MAX_DOCUMENT_CHARS == 6_000_000 and service.MAX_MASK_CHARS == 6_000_000


def test_a_text_over_the_old_limit_is_read(tmp_path):
    p = tmp_path / "long.txt"
    p.write_text(("Ligne fictive de registre numéro 0001 pour le dépôt de Lorient.\n" * 52_000), encoding="utf-8")
    assert len(p.read_text(encoding="utf-8")) > 3_000_000
    res = documents.read_text(p, max_chars=service.MAX_DOCUMENT_CHARS)
    assert len(res.text) > 3_000_000
    with pytest.raises(documents.ReadTooLarge):
        documents.read_text(p, max_chars=3_000_000)


def test_document_budget_grows_with_pages():
    b = documents.document_budget
    assert b(None) == b(0) == b(300) == 180.0 and b(301) == 180.5 and b(800) == 430.0 and b(2300) == 1180.0
    assert b(10_000) == 1800.0


def test_a_long_pdf_gets_its_page_budget(tmp_path, monkeypatch):
    path = synth_pdf.make_long_pdf(tmp_path / "long.pdf", 3)
    monkeypatch.setattr(documents, "PDF_PLUMBER_MAX_PAGES", 0)
    def clock_from(start=0.0):
        seen = []

        def clock():  # the start, then 400 s later at every look
            seen.append(1)
            return start if len(seen) == 1 else start + 400.0
        return clock

    monkeypatch.setattr(documents, "_pdf_page_count", lambda p: 3)
    with pytest.raises(documents.ReadTooLong):
        documents.read_text(path, clock=clock_from())  # 3 pages: 180 s
    monkeypatch.setattr(documents, "_pdf_page_count", lambda p: 1500)  # 780 s
    assert documents.read_text(path, clock=clock_from()).pages == 3
    with pytest.raises(documents.ReadTooLong):
        documents.read_text(path, clock=clock_from(), budget=180.0)  # a budget given by the caller wins


def test_the_stuck_rule_follows_the_budget_of_the_document():
    job = service._Reading("DOSSIER_1", "x")
    job.state = "reading"
    job.step(documents.document_budget(1500))
    assert not job.stuck(job.step_started + 700) and job.stuck(job.step_started + 780 + 61)
    job.step()
    assert job.stuck(job.step_started + 241)
    assert service._mask_budget(6_000_000) == 480.0 and service._mask_budget(10, 900.0) == 900.0


def test_progress_sets_the_budget_of_a_long_pdf(tmp_path, monkeypatch):
    f = tmp_path / "d"
    f.mkdir()
    (f / "grand.pdf").write_bytes(b"%PDF-1.4 fictif")
    seen = {}
    gate = threading.Event()

    def fake(path, progress=None, **kw):
        progress(0, 1000)
        seen["budget"] = svc._reads["DOSSIER_1"].budget
        gate.wait(5)
        return documents.ReadResult("Texte fictif du registre.", pages=1000)

    monkeypatch.setattr(documents, "read_text", fake)
    svc = service.Service(tmp_path / "data")
    try:
        svc.protect_folder(f)
        time.sleep(0.5)
        gate.set()
        assert svc.wait_reading("DOSSIER_1", 20)
        assert seen["budget"] == documents.document_budget(1000) == 530.0
    finally:
        svc.close()


def test_too_large_answer_says_what_to_do():
    text = claude_tab.ERRORS["document_too_large"]
    assert "trop long pour Shield" in text and "deux fichiers" in text and "shield_protect_folder" in text
    assert not ENGLISH.search(text) and "—" not in text


# ============================================================================================ C1: start handshake

def test_readings_start_again_after_the_answer_to_initialize(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(claude_tab, "_RESUMED", False)
    monkeypatch.setattr(service, "resume_readings", lambda: calls.append("resume") or [])
    monkeypatch.setattr(service, "clean_kept", lambda: calls.append("clean") or [])

    class FakeServer:
        def run(self, transport):
            time.sleep(0.2)
            calls.append("run")

    monkeypatch.setattr(claude_tab, "build_server", lambda: FakeServer())
    monkeypatch.setattr(claude_tab, "RESUME_AFTER_SECONDS", 0.5)
    monkeypatch.setattr(claude_tab, "lock_settings", lambda *a, **k: tmp_path)
    claude_tab.main([])
    assert calls[0] == "run"  # nothing started before the server answers
    deadline = time.monotonic() + 5
    while "resume" not in calls and time.monotonic() < deadline:
        time.sleep(0.05)
    assert calls[1:3] == ["resume", "clean"]
    assert not claude_tab.start_resume()  # once per process


def test_the_initialized_notification_starts_the_readings(monkeypatch, plugin):
    started = []
    monkeypatch.setattr(claude_tab, "start_resume", lambda: started.append(1) or True)
    server = claude_tab.build_server()
    entry = server._lowlevel_server.get_notification_handler("notifications/initialized")
    assert entry is not None
    asyncio.run(entry.handler(None, None))
    assert started == [1]


# ============================================================================================ F1 to F4

def _saving_dossier(tmp_path, folder_name="Dossier Faubeau"):
    f = tmp_path / folder_name
    f.mkdir(parents=True)
    (f / "a.txt").write_text("Mme Ondine Valcrest écrit au cabinet.\n", encoding="utf-8")
    svc = service.Service(tmp_path / "data")
    code = svc.add_dossier(f)["code"]
    return svc, code, f


@pytest.mark.parametrize("make", [lambda: PermissionError(13, "refused"), lambda: _winerror5()])
def test_f1_a_blocked_save_gives_its_own_kind(tmp_path, monkeypatch, make):
    svc, code, _ = _saving_dossier(tmp_path)
    try:
        def boom(*a, **k):
            raise make()

        monkeypatch.setattr(documents, "_write_atomic", boom)
        with pytest.raises(service.ShieldError) as exc:
            svc.save_draft(code, "Projet", "Texte PERSONNE_A.", "md")
        assert exc.value.kind == "write_blocked"
        monkeypatch.setattr(documents, "_write_atomic", lambda *a, **k: (_ for _ in ()).throw(OSError(28, "full")))
        with pytest.raises(service.ShieldError) as exc:
            svc.save_draft(code, "Projet", "Texte PERSONNE_A.", "md")
        assert exc.value.kind == "write_failed"  # any other error: the same path and text as before
    finally:
        svc.close()


def _winerror5() -> OSError:
    e = OSError(13, "access denied")
    e.winerror = 5
    return e


def test_f1_texts_per_system():
    win, mac = claude_tab.write_blocked_text("win32"), claude_tab.write_blocked_text("darwin")
    assert win.startswith("Windows a empêché Shield") and "« shield.exe »" in win and "Rien n'a été envoyé" in win
    assert "Autoriser une application via un dispositif d'accès contrôlé aux dossiers" in win
    assert mac.startswith("macOS a empêché Shield") and "Fichiers et dossiers" in mac
    for t in (win, mac):
        assert "—" not in t and not ENGLISH.search(t)
    exc = service.ShieldError("x", "write_blocked")
    assert claude_tab._msg(exc) == claude_tab.write_blocked_text()


def test_f2_long_paths_are_counted_and_said(plugin, tmp_path, monkeypatch):
    f = tmp_path / "c" / "Dossier Long"
    (f / ("s" * 40)).mkdir(parents=True)
    (f / "court1.txt").write_text("Texte fictif un.\n", encoding="utf-8")
    (f / "court2.txt").write_text("Texte fictif deux.\n", encoding="utf-8")
    (f / "court3.md").write_text("Texte fictif trois.\n", encoding="utf-8")
    (f / ("l" * 60 + ".txt")).write_text("Texte fictif long.\n", encoding="utf-8")
    (f / ("m" * 70 + ".txt")).write_text("Texte fictif plus long.\n", encoding="utf-8")
    (f / ("s" * 40) / "dans.txt").write_text("Texte fictif dedans.\n", encoding="utf-8")
    limit = len(str(f)) + 30  # like Windows with long paths off: these paths do not open
    monkeypatch.setattr(vault, "WINDOWS_MAX_PATH", limit)
    monkeypatch.setattr(documents, "windows_paths", lambda platform=None: True)
    real_stat, real_scandir = Path.stat, os.scandir

    def stat(self, *a, **k):
        if str(self).startswith(str(f)) and len(str(self)) > limit:
            raise FileNotFoundError(2, "path too long", str(self))
        return real_stat(self, *a, **k)

    def scandir(path="."):
        if str(path).startswith(str(f)) and len(str(path)) > limit:
            raise FileNotFoundError(3, "path too long", str(path))
        return real_scandir(path)

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(os, "scandir", scandir)
    claude_tab._check_size(f)  # never fails on such a path
    server, code, text = protect(f)
    line = ("3 document(s) ou sous-dossier(s) n'ont pas pu être lus : leur chemin est trop long pour Windows (plus de "
            "259 caractères). Raccourcissez le nom des dossiers ou des fichiers, puis rappelez shield_protect_folder.")
    assert "3 document(s) trouvé(s), 3 lu(s). " + line in text, text
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    assert line in listing and "l" * 60 not in listing
    _, status = call(server, "shield_status")
    assert line in status
    assert not (plugin / "kept" / code).exists() or not _set_files(plugin, code)[0]  # never kept


def test_f2_another_failure_counts_as_unreadable(tmp_path, monkeypatch):
    f = tmp_path / "Dossier"
    (f / "sous").mkdir(parents=True)
    (f / "a.txt").write_text("Texte fictif.\n", encoding="utf-8")
    (f / "sous" / "b.txt").write_text("Texte fictif.\n", encoding="utf-8")
    real_scandir = os.scandir
    monkeypatch.setattr(os, "scandir", lambda p=".": (_ for _ in ()).throw(PermissionError(13, "no", str(p)))
                        if str(p).endswith("sous") else real_scandir(p))
    svc = service.Service(tmp_path / "data")
    try:
        code = svc.protect_folder(f)["code"]
        assert svc.wait_reading(code, 20)
        s = svc.reading_summary(code)
        assert s["documents"] == 2 and s["unreadable"] == 1 and s["skipped_long"] == 0
        assert claude_tab.summary_line(s) == "2 document(s) trouvé(s), 1 lu(s), 1 illisible(s)."
    finally:
        svc.close()


def test_f3_output_name_fits_windows(tmp_path):
    folder = tmp_path / ("d" * max(1, 200 - len(str(tmp_path)) - 1))
    folder.mkdir()
    title = "Conclusions récapitulatives en réponse pour PERSONNE_A contre SOCIETE_A devant le tribunal judiciaire"
    name = documents.fit_output_name(folder, documents.safe_filename(title, "docx"), platform="win32")
    assert name.endswith(".docx") and len(str(folder / name)) <= 255 - 5
    assert documents.fit_output_name(folder, "court.docx", platform="win32") == "court.docx"
    assert documents.fit_output_name(folder, documents.safe_filename(title, "docx"), platform="darwin") == \
        documents.safe_filename(title, "docx")  # elsewhere: unchanged
    deep = tmp_path / ("e" * max(1, 245 - len(str(tmp_path)) - 1))
    deep.mkdir()
    with pytest.raises(documents.DocumentError) as exc:
        documents.fit_output_name(deep, documents.safe_filename(title, "md"), platform="win32")
    assert str(exc.value) == documents.OUTPUT_PATH_TOO_LONG


def test_f3_two_saves_with_a_long_title_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "windows_paths", lambda platform=None: True)
    name = "f" * max(1, 190 - len(str(tmp_path)) - len("/data"))
    svc, code, f = _saving_dossier(tmp_path, name)
    try:
        title = "Conclusions récapitulatives en réponse pour PERSONNE_A contre SOCIETE_A devant le tribunal judiciaire"
        ids = [svc.save_draft(code, title, "Texte fictif.", "md")["id"] for _ in range(2)]
        outs = sorted((f / "Shield - sorties").iterdir())
        assert len(ids) == 2 and len(outs) == 2 and outs[0].name != outs[1].name
        assert all(len(str(p)) <= 255 and p.suffix == ".md" for p in outs)
    finally:
        svc.close()
    deep = "g" * max(1, 236 - len(str(tmp_path)) - 1)
    svc, code, f = _saving_dossier(tmp_path, deep)
    try:
        with pytest.raises(service.ShieldError) as exc:
            svc.save_draft(code, "Projet", "Texte.", "md")
        assert exc.value.kind == "output_path_too_long"
        text = claude_tab._msg(exc.value)
        assert text == ("Le chemin du dossier client est trop long pour que Windows y enregistre le fichier. "
                        "Raccourcissez le nom des dossiers, puis redemandez l'enregistrement.")
    finally:
        svc.close()


def test_f4_open_refusal_causes():
    e32 = PermissionError(13, "sharing")
    e32.winerror = 32
    e33 = OSError(13, "lock")
    e33.winerror = 33
    assert documents.open_refusal(e32) == documents.open_refusal(e33) == documents.READ_LOCKED
    assert documents.open_refusal(PermissionError(13, "no")) == documents.READ_DENIED
    wrapped = ValueError("reader")
    wrapped.__cause__ = e32
    assert documents.open_refusal(wrapped) == documents.READ_LOCKED
    assert documents.open_refusal(ValueError("broken")) is None


def test_f4_a_locked_file_is_named_in_the_list_and_explained(plugin, tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    real = documents.read_text
    sharing = PermissionError(13, "sharing violation")
    sharing.winerror = 32

    def held(path, **kw):
        if Path(path).name == "echange.eml":
            raise sharing  # what the e-mail reader meets when Word or Outlook holds the file
        return real(path, **kw)

    monkeypatch.setattr(documents, "_read_eml", lambda p: (_ for _ in ()).throw(sharing))
    server, code, text = protect(folder)
    assert "5 document(s) trouvé(s), 4 lu(s), 1 illisible(s)." in text
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    lines = [l for l in listing.splitlines() if "(non lu : ouvert dans un autre programme)" in l]
    assert len(lines) == 1 and "e-mail" in lines[0]
    doc = lines[0].split(" |")[0]
    err, answer = call(server, "shield_read_document", {"dossier": code, "document": doc})
    assert err and answer == ("Ce document est ouvert dans un autre programme qui le bloque (par exemple Word ou "
                              "Excel). Fermez-le, puis rappelez shield_protect_folder.")
    # closed: protect again reads it
    monkeypatch.setattr(documents, "_read_eml", documents.__dict__["_read_eml"].__wrapped__
                        if hasattr(documents._read_eml, "__wrapped__") else _real_read_eml)
    _, again = call(server, "shield_protect_folder")
    _wait(code)
    _, status = call(server, "shield_status")
    assert f"{code} est prêt : 5 document(s) trouvé(s), 5 lu(s)." in status, status


_real_read_eml = documents._read_eml


def test_f4_an_unreadable_document_is_marked_not_read(plugin, tmp_path):
    folder = make_folder(tmp_path)
    (folder / "abime.pdf").write_bytes(b"%PDF-1.4 rien de lisible")
    server, code, text = protect(folder)
    _, listing = call(server, "shield_list_documents", {"dossier": code})
    assert sum(1 for l in listing.splitlines() if l.endswith(" | (non lu)")) == 1
    assert "(non lu : ouvert" not in listing


# ============================================================================================ D: version

def test_version_is_0_4_4():
    assert __version__ == "0.4.4"
    sys.path.insert(0, str(HERE.parent / "packaging" / "claude_plugin"))
    try:
        import shield_boot
    finally:
        sys.path.pop(0)
    assert shield_boot.VERSION == "0.4.4"
    assert "0.4.4" in kept.rules_fingerprint() or kept.rules_fingerprint()  # the version is part of it


def test_status_shows_the_version(plugin):
    _, text = call(claude_tab.build_server(), "shield_status")
    assert text.startswith("RAGbase Shield 0.4.4 fonctionne sur cet ordinateur")


def test_an_old_0_4_3_cache_folder_breaks_nothing(tmp_path, monkeypatch):
    sys.path.insert(0, str(HERE.parent / "packaging" / "claude_plugin"))
    try:
        import shield_boot as boot
    finally:
        sys.path.pop(0)
    eng = tmp_path / "plugin" / "engine"
    eng.mkdir(parents=True)
    (eng / boot.ID_FILE).write_text("abc123abc123\n", encoding="ascii")
    local = tmp_path / "local"
    monkeypatch.setattr(boot, "local_app_data", lambda: str(local))
    old = local / "RAGbase Shield" / "engine" / "0.4.3-abc123abc123"
    old.mkdir(parents=True)
    (old / boot.MARKER).write_text("RAGbase Shield 0.4.3: 1 entries\n", encoding="ascii")
    new = boot.cache_dir(str(eng))
    assert Path(new).name.startswith("0.4.4-") and Path(new) != old and not boot.is_complete(new)
