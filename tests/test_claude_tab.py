"""Plugin mode for the Claude tab (ragbase_shield.claude_tab): locked settings, key store with no fallback, the
shield_protect_folder tool (no path through Claude, counts only, wide folders refused) and French-only texts.
Invented text only: no real person, no client data."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import pytest
from mcp import Client

from ragbase_shield import claude_tab, config, service, vault

FOLDER_NAME = "Dossier Ferrandou c. Brisquet"
FILE_NAME = "Conclusions Ferrandou.txt"
TEXT = ("Monsieur Aurélien FERRANDOU, demeurant 9 impasse des Mésanges, 49100 Angers, contre la société "
        "BRISQUET MENUISERIE SARL (SIREN 732 829 320). M. Ferrandou réclame le solde de 7 300 euros. "
        "IBAN FR76 3000 6000 0112 3456 7890 189.\n")
BIRTH = "Monsieur Aurélien FERRANDOU, né le 14 février 1972 à Angers, gérant.\n"
SECRETS = ("FERRANDOU", "Ferrandou", "BRISQUET", "Brisquet", "Mésanges", "Aurélien", "732 829 320",
           "FR76 3000", FOLDER_NAME, "Angers")
#: English words that must not appear in a French text of the plugin.
ENGLISH = re.compile(r"\b(the|masked|dossier code|document code|error|internal|unknown|vault|registered|"
                     r"pinned|search for|words or|file title|start offset)\b", re.I)


@pytest.fixture(autouse=True)
def _plugin_mode(tmp_path):
    saved_env = dict(os.environ)
    saved_picker = claude_tab.PICKER
    service.reset()
    claude_tab.lock_settings(tmp_path / "shield-data")
    yield
    service.reset()
    vault.KEY_STORE = None
    claude_tab.PICKER = saved_picker
    os.environ.clear()
    os.environ.update(saved_env)


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "cabinet" / FOLDER_NAME
    f.mkdir(parents=True)
    (f / FILE_NAME).write_text(TEXT * 4 + BIRTH, encoding="utf-8")
    (f / "releve.txt").write_text("Relevé : virement de M. Aurélien Ferrandou, 4 000 euros, le 2 mai 2026.\n",
                                  encoding="utf-8")
    return f


def pick(path):
    claude_tab.PICKER = lambda title, timeout: str(path)


def call(server, name: str, args: dict | None = None) -> tuple[bool, str]:
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(name, args or {})
            return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

    return asyncio.run(go())


def clean(text: str, folder: Path | None = None) -> bool:
    bad = list(SECRETS) + ([str(folder), folder.name, str(folder.parent)] if folder else [])
    return not any(s in text for s in bad)


# ------------------------------------------------------------------------------------------ tools and texts

def test_seven_tools_in_french_and_protect_takes_no_argument():
    server = claude_tab.build_server()
    tools = asyncio.run(server.list_tools())
    assert [t.name for t in tools] == list(claude_tab.TOOL_NAMES)
    by_name = {t.name: t for t in tools}
    protect = by_name["shield_protect_folder"]
    assert not (protect.input_schema.get("properties") or {}), "the folder must never be a tool argument"
    for t in tools:
        text = " | ".join([t.description or "", t.title or ""] + [
            str(p.get("description", "")) for p in (t.input_schema.get("properties") or {}).values()])
        assert not ENGLISH.search(text), (t.name, text)
        assert re.search(r"[éèàùç]|dossier|document", text), t.name
    assert not ENGLISH.search(claude_tab.INSTRUCTIONS)
    for texts in (claude_tab.REFUSALS, claude_tab.PICK_MESSAGES, claude_tab.ERRORS):
        for v in texts.values():
            assert not ENGLISH.search(v), v


def test_bad_arguments_get_a_french_answer():
    server = claude_tab.build_server()
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_1", "start": -5})
    assert err and text == claude_tab.ERRORS["invalid_argument"]
    err, text = call(server, "shield_unmask", {"text": "x"})
    assert err and text == claude_tab.ERRORS["invalid_argument"]


def test_no_tool_removes_exports_or_unmasks():
    names = set(claude_tab.TOOL_NAMES)
    assert not any(w in n for n in names for w in ("remove", "delete", "export", "unmask", "restore", "entities",
                                                    "register", "keep_clear", "vault"))


# ------------------------------------------------------------------------------------------ shield_protect_folder

def test_protect_folder_answers_code_and_counts_only(folder):
    pick(folder)
    server = claude_tab.build_server()
    err, text = call(server, "shield_protect_folder")
    assert not err, text
    assert "DOSSIER_1" in text and "maintenant protégé" in text
    assert "2 document(s) trouvé(s), 2 lu(s)" in text
    assert re.search(r"\d+ personne\(s\)", text) and "société(s)" in text
    assert clean(text, folder), text
    assert FILE_NAME not in text and "releve" not in text
    assert server._shield_scope.pinned == "DOSSIER_1"


def test_second_call_on_same_folder_gives_same_code(folder):
    pick(folder)
    server = claude_tab.build_server()
    _, first = call(server, "shield_protect_folder")
    _, second = call(server, "shield_protect_folder")
    assert "DOSSIER_1" in first and "DOSSIER_1" in second
    assert "déjà protégé" in second and clean(second, folder)
    assert [r["code"] for r in service.list_dossiers()] == ["DOSSIER_1"]


def test_cancelled_window_says_so_in_french():
    def cancelled(title, timeout):
        assert title == claude_tab.PICK_TITLE and "choisissez le dossier" in title
        raise claude_tab.PickCancelled()

    claude_tab.PICKER = cancelled
    err, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert not err and "la fenêtre a été fermée" in text and "Rien n'a été protégé" in text
    assert service.list_dossiers() == []


def test_window_that_cannot_open_says_so():
    def broken(title, timeout):
        raise claude_tab.PickFailed("failed")

    claude_tab.PICKER = broken
    _, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert text == claude_tab.PICK_MESSAGES["failed"]


@pytest.mark.parametrize("where", ["home", "root", "parent_of_home", "documents", "downloads", "desktop", "system",
                                   "shield_data", "claude_data"])
def test_wide_and_private_folders_are_refused(where, tmp_path):
    home = claude_tab.user_home()
    target = {
        "home": home,
        "root": Path(Path.cwd().anchor),
        "parent_of_home": home.parent,
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "desktop": home / "Desktop",
        "system": Path("C:/Windows") if sys.platform == "win32" else Path("/usr/bin"),
        "shield_data": config.home(),
        "claude_data": home / ".claude",
    }[where]
    if not target.is_dir():
        pytest.skip(f"no {where} folder on this computer")
    with pytest.raises(claude_tab.FolderRefused):
        claude_tab.check_folder(target)
    pick(target)
    err, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert not err and "Rien n'a été protégé" in text
    assert str(target) not in text and service.list_dossiers() == []


def test_folder_holding_the_shield_data_is_refused(tmp_path):
    with pytest.raises(claude_tab.FolderRefused) as e:
        claude_tab.check_folder(tmp_path)  # holds shield-data (the scratch data folder of this test)
    assert e.value.kind == "app_data"


def test_too_many_files_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_tab, "MAX_FOLDER_FILES", 5)
    big = tmp_path / "archive"
    big.mkdir()
    for i in range(6):
        (big / f"note{i}.txt").write_text("x", encoding="utf-8")
    with pytest.raises(claude_tab.FolderRefused) as e:
        claude_tab.check_folder(big)
    assert e.value.kind == "too_big"


def test_missing_folder_is_refused(tmp_path):
    pick(tmp_path / "nowhere")
    _, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert text == claude_tab.REFUSALS["missing"]


# ------------------------------------------------------------------------------------------ the other tools leak nothing

def test_every_answer_holds_codes_only(folder):
    pick(folder)
    server = claude_tab.build_server()
    answers = [call(server, "shield_protect_folder")[1]]
    answers.append(call(server, "shield_list_dossiers")[1])
    err, docs = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert not err and "DOC_1" in docs and "PERSONNE_" in docs  # the party name in the file name became a code
    answers.append(docs)
    for doc in ("DOC_1", "DOC_2"):
        err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": doc})
        assert not err and "PERSONNE_" in text
        answers.append(text)
    for query in ("Ferrandou", "solde", "PERSONNE_A", "Mésanges"):
        answers.append(call(server, "shield_search", {"dossier": "DOSSIER_1", "query": query})[1])
    answers.append(call(server, "shield_status")[1])
    err, saved = call(server, "shield_save_draft", {"dossier": "DOSSIER_1", "title": "Note PERSONNE_A",
                                                    "content": "# Note\nPERSONNE_A réclame le solde.", "format": "md"})
    assert not err and "OUTPUT_" in saved
    answers.append(saved)
    for a in answers:
        assert clean(a, folder), a
        assert not ENGLISH.search(a), a
    outputs = folder / config.OUTPUT_DIR_NAME
    restored = next(outputs.iterdir()).read_text(encoding="utf-8")
    assert "Ferrandou" in restored.title() or "FERRANDOU" in restored  # real names back on the computer only


def test_errors_are_french_and_hold_no_value(folder):
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_99"})
    assert err and text == claude_tab.ERRORS["unknown_document"]
    err, text = call(server, "shield_list_documents", {"dossier": "DOSSIER_7"})
    assert err and "DOSSIER_1" in text and "shield_protect_folder" in text and not ENGLISH.search(text)


def test_switching_dossier_goes_through_the_window(folder, tmp_path):
    other = tmp_path / "cabinet" / "Dossier 2026-014"
    other.mkdir()
    (other / "note.txt").write_text("Madame Odile GARANCIER réclame 900 euros.\n", encoding="utf-8")
    server = claude_tab.build_server()
    pick(folder)
    call(server, "shield_protect_folder")
    pick(other)
    _, text = call(server, "shield_protect_folder")
    assert "DOSSIER_2" in text and server._shield_scope.pinned == "DOSSIER_2"
    err, _ = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert err
    pick(folder)
    _, text = call(server, "shield_protect_folder")
    assert "DOSSIER_1" in text and "déjà protégé" in text and server._shield_scope.pinned == "DOSSIER_1"


# ------------------------------------------------------------------------------------------ locked settings and key

def test_environment_cannot_move_or_weaken_shield(tmp_path, monkeypatch):
    elsewhere = tmp_path / "attacker-home"
    for name, value in (("RAGBASE_SHIELD_HOME", str(elsewhere)), ("RAGBASE_SHIELD_MULTI_DOSSIER", "1"),
                        ("RAGBASE_SHIELD_DOSSIER", "DOSSIER_9"), ("RAGBASE_SHIELD_KEYRING", "1"),
                        ("RAGBASE_SHIELD_LOWERCASE_NAMES", "0"), ("ragbase_shield_ner", "on"),
                        ("RAGBASE_SHIELD_MODELS_DIR", str(elsewhere)), ("HF_HOME", str(elsewhere))):
        monkeypatch.setenv(name, value)
    data = tmp_path / "shield-data"
    home = claude_tab.lock_settings(data)
    assert home == data.resolve() and config.home() == data.resolve()
    assert not elsewhere.exists()
    env_upper = {k.upper(): v for k, v in os.environ.items()}
    for name in ("RAGBASE_SHIELD_MULTI_DOSSIER", "RAGBASE_SHIELD_DOSSIER", "RAGBASE_SHIELD_LOWERCASE_NAMES",
                 "RAGBASE_SHIELD_MODELS_DIR", "HF_HOME"):
        assert name not in env_upper
    assert env_upper["RAGBASE_SHIELD_NER"] == "off" and env_upper["RAGBASE_SHIELD_KEYRING"] == "0"
    assert isinstance(vault.KEY_STORE, claude_tab.FileKeyStore)
    assert claude_tab.build_server()._shield_scope.pinned is None  # RAGBASE_SHIELD_DOSSIER was ignored


def test_fixed_places_come_from_the_system(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "fake"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "fake"))
    home = claude_tab.plugin_home()
    assert str(tmp_path) not in str(home)
    assert home.name in (claude_tab.APP_DIR_NAME, "ragbase-shield-plugin")
    assert claude_tab.plugin_home() != Path(config.home())


def test_windows_vault_is_in_the_profile_not_in_appdata(monkeypatch, tmp_path):
    """Windows: the packaged Claude app can redirect writes under AppData to a folder that Windows deletes with the
    app. The vault goes to <profile>\\RAGbase Shield; the profile comes from the shell, never from a variable."""
    profile, local = tmp_path / "profile", tmp_path / "profile" / "AppData" / "Local"
    folders = {claude_tab._FOLDERID["Profile"]: profile, claude_tab._FOLDERID["LocalAppData"]: local}
    monkeypatch.setattr(claude_tab, "_known_folder", lambda guid: folders.get(guid))
    monkeypatch.setattr(claude_tab.sys, "platform", "win32")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "planted-profile"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "planted-local"))
    home = claude_tab.plugin_home()
    assert home == profile / "RAGbase Shield"
    assert "AppData" not in home.parts and "planted" not in str(home)
    folders.clear()  # the shell gives no answer: an error, never %USERPROFILE%
    with pytest.raises(OSError):
        claude_tab.plugin_home()


def test_status_names_the_vault_place_without_a_path(folder, tmp_path):
    assert "dossier personnel Windows" in claude_tab.data_place_fr("win32")
    assert "Bibliothèque" in claude_tab.data_place_fr("darwin")
    for platform in ("win32", "darwin", "linux"):
        text = claude_tab.data_place_fr(platform)
        assert "\\" not in text and "/" not in text and "AppData" not in text
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    err, text = call(server, "shield_status")
    assert not err and claude_tab.data_place_fr() in text
    assert clean(text, folder) and str(tmp_path) not in text and not ENGLISH.search(text)


def test_key_store_failure_is_an_error_not_a_file(folder, tmp_path):
    class Broken:
        source = "broken"

        def get(self):
            raise OSError("no keychain")

        def put(self, key):
            raise OSError("no keychain")

    data = tmp_path / "data-2"
    claude_tab.lock_settings(data, key_store=Broken())
    pick(folder)
    err, text = call(claude_tab.build_server(), "shield_protect_folder")
    assert err and text == claude_tab.ERRORS["vault_error"]
    assert not (data / "key").exists() and not (data / "test-key").exists()


def test_wrong_key_does_not_open_the_vault(folder, tmp_path):
    pick(folder)
    call(claude_tab.build_server(), "shield_protect_folder")
    service.reset()

    class Other:
        source = "other"

        def get(self):
            from cryptography.fernet import Fernet

            return Fernet.generate_key()

        def put(self, key):
            raise AssertionError("must not create a key for an existing vault")

    vault.KEY_STORE = Other()
    err, text = call(claude_tab.build_server(), "shield_list_dossiers")
    assert text.count("coffre illisible") == 1 or (err and text == claude_tab.ERRORS["vault_error"])


def test_mac_keychain_store_keeps_the_key_off_the_command_line(monkeypatch):
    seen = []

    class R:
        def __init__(self, rc, out=b""):
            self.returncode, self.stdout, self.stderr = rc, out, b""

    store_value = {}

    def fake_run(cmd, input=None, capture_output=None, timeout=None, env=None):
        seen.append((list(cmd), input, env))
        if cmd[1] == "find-generic-password":
            return R(0, store_value["k"] + b"\n") if "k" in store_value else R(44)
        if cmd[1] == "-i":
            store_value["k"] = input.split(b" -w ")[1].split()[0]
            return R(0)
        return R(1)

    monkeypatch.setattr(claude_tab.subprocess, "run", fake_run)
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    store = claude_tab.MacKeychainStore()
    assert store.get() is None
    store.put(key)
    assert store.get() == key
    for cmd, stdin, env in seen:
        assert cmd[0] == "/usr/bin/security" and env == {"PATH": "/usr/bin:/bin"}
        assert not any(key.decode() in part for part in cmd)
    assert any(stdin and key in stdin for _cmd, stdin, _env in seen)


def test_test_switches_are_command_line_only():
    assert claude_tab._parse([]) == (None, None)
    with pytest.raises(SystemExit):
        claude_tab._parse(["--test-pick", "/x"])  # a test answer needs a scratch data folder
    with pytest.raises(SystemExit):
        claude_tab._parse(["--home", "/x"])
    data, picked = claude_tab._parse(["--test-data", "/d", "--test-pick", "/p"])
    assert data == Path("/d") and picked == "/p"


# ------------------------------------------------------------------------------------------ round 2 (review findings)

def test_birthplace_is_a_code(folder):
    """Review finding: "né le <date> à Angers" sent the town in clear."""
    pick(folder)
    server = claude_tab.build_server()
    _, text = call(server, "shield_protect_folder")
    assert "lieu(x) de naissance" in text
    err, doc = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_1"})
    if "NAISSANCE_" not in doc:
        err, doc = call(server, "shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_2"})
    assert not err and re.search(r"né le NAISSANCE_\d+ à LIEU_\d+", doc), doc
    _, hits = call(server, "shield_search", {"dossier": "DOSSIER_1", "query": "gérant"})
    assert "LIEU_" in hits and clean(doc, folder) and clean(hits, folder), hits


@pytest.mark.parametrize("sentence, place", [
    ("Madame Odile Garancier, née le 03/04/1975 à Saint-Étienne (Loire), comptable.", "Saint-Étienne"),
    ("Monsieur Paul Ferrandou, né à La Rochelle le 2 juin 1980.", "La Rochelle"),
    ("Date et lieu de naissance : 7 avril 1990 à Boulogne-Billancourt", "Boulogne-Billancourt"),
    ("Lieu de naissance : Quimperlé", "Quimperlé"),
    ("Madame Anne Brisquet, née Garancier le 5 mai 1969 à Aix-en-Provence.", "Aix-en-Provence"),
])
def test_birthplace_forms(sentence, place):
    from ragbase_shield.engine import Masker, MemoryStore

    out = Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False).mask(sentence).text
    assert place not in out and "LIEU_" in out, out


def test_a_town_without_birth_stays_clear():
    from ragbase_shield.engine import Masker, MemoryStore

    out = Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False).mask(
        "Le contrat a été signé à Angers le 3 mars 2020.").text
    assert "Angers" in out and "LIEU_" not in out


def test_sub_folder_and_unknown_file_names_never_reach_claude(folder):
    """Review finding: sub-folder names and file names with a name the detection did not know were sent as is."""
    (folder / "Martin-Pradel c. Boisgontier").mkdir()
    (folder / "Martin-Pradel c. Boisgontier" / "conclusions.txt").write_text("Conclusions.\n", encoding="utf-8")
    (folder / "Succession Quillivic").mkdir()
    (folder / "Succession Quillivic" / "acte.txt").write_text("Acte.\n", encoding="utf-8")
    (folder / "Notes Kerbrat 2026.txt").write_text("Rendez-vous.\n", encoding="utf-8")
    (folder / "Jean-Yves Tanguerel - attestation.txt").write_text("Attestation.\n", encoding="utf-8")
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    err, docs = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert not err
    for name in ("Martin", "Pradel", "Boisgontier", "Quillivic", "Kerbrat", "Jean-Yves", "Tanguerel", "Succession"):
        assert name not in docs, (name, docs)
    assert "sous-dossier 1 / conclusions.txt" in docs and "sous-dossier 2 / acte.txt" in docs, docs
    assert "Notes … 2026.txt" in docs and "attestation.txt" in docs, docs
    _, again = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert again == docs  # stable labels
    # the parties of a sub-folder name became codes of the dossier: same code in every document
    ents = {e["value"] for e in service.entities("DOSSIER_1")}
    assert {"Martin-Pradel", "Boisgontier"} <= ents, ents


def test_safe_file_name_rules():
    f = claude_tab.safe_file_name
    assert f("Notes Quillivic 2026.txt") == "Notes … 2026.txt"
    assert f("PERSONNE_A - attestation.docx") == "PERSONNE_A - attestation.docx"
    assert f("Martin-Pradel c. Boisgontier") == "… c. …"
    assert f("Conclusions récapitulatives v2.pdf") == "Conclusions récapitulatives v2.pdf"
    assert f("Courrier de Pierre.pdf") == "Courrier de ….pdf"
    assert f("relance [PERSONNE] 12-03.txt") == "relance [PERSONNE] 12-03.txt"


def test_parent_of_a_protected_dossier_is_refused(folder):
    """Review finding: a parent folder became one dossier holding several client dossiers."""
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    pick(folder.parent)
    _, text = call(server, "shield_protect_folder")
    assert text == claude_tab.REFUSALS["holds_dossier"]
    assert [r["code"] for r in service.list_dossiers()] == ["DOSSIER_1"]


def test_sub_folder_of_a_protected_dossier_gives_the_same_code(folder):
    sub = folder / "Pièces"
    sub.mkdir()
    (sub / "piece.txt").write_text("Monsieur Aurélien FERRANDOU signe.\n", encoding="utf-8")
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    pick(sub)
    server2 = claude_tab.build_server()
    _, text = call(server2, "shield_protect_folder")
    assert "fait partie de DOSSIER_1" in text and clean(text, sub), text
    assert server2._shield_scope.pinned == "DOSSIER_1"
    assert [r["code"] for r in service.list_dossiers()] == ["DOSSIER_1"]


# ------------------------------------------------------------------ Windows: SYSTEMROOT before asyncio (round 3)

def test_systemroot_is_filled_on_windows_when_missing():
    env = {"PATH": r"C:\Windows\System32"}
    assert claude_tab.fill_systemroot(env, windows=True, windows_dir=lambda: r"C:\Windows") is True
    assert env["SYSTEMROOT"] == r"C:\Windows"


def test_systemroot_is_kept_when_present_or_not_windows():
    env = {"SYSTEMROOT": r"D:\Win"}
    assert claude_tab.fill_systemroot(env, windows=True, windows_dir=lambda: r"C:\Windows") is False
    assert env["SYSTEMROOT"] == r"D:\Win"
    env = {}
    assert claude_tab.fill_systemroot(env, windows=False, windows_dir=lambda: "/x") is False and env == {}
    env = {}  # the system call failed: nothing is invented
    assert claude_tab.fill_systemroot(env, windows=True, windows_dir=lambda: "") is False and env == {}


def test_systemroot_fix_runs_before_asyncio_is_imported():
    """The fix must run at import time, before the MCP framework imports asyncio (WinError 10106 otherwise)."""
    src = Path(claude_tab.__file__).read_text(encoding="utf-8")
    call = src.index("\nfill_systemroot()")
    head = src[:call]
    imports = re.findall(r"^(?:import|from) ([\w.]+)", head, re.M)  # top-level imports before the fix
    assert imports and not any(m.split(".")[0] in ("asyncio", "mcp", "anyio") or m == "." for m in imports)


# ------------------------------------------------------------------ round 7: the Windows folder window, two extras

class FakeWin:
    """Stands for the user32 calls: windows = {handle: (process id, title)}."""

    def __init__(self, windows=None):
        self.windows = dict(windows or {})
        self.front: list = []
        self.closed: list = []
        self.on_close = None
        self.broken: set = set()  # windows that go away during the look
        self.refuse: set = set()  # windows that bring_front fails on

    def top_windows(self):
        return list(self.windows)

    def process_of(self, h):
        if h in self.broken:
            raise OSError("window went away")
        return self.windows[h][0]

    def title_of(self, h):
        return self.windows[h][1]

    def bring_front(self, h):
        self.front.append(h)
        if h in self.refuse:
            raise OSError("refused")

    def close(self, h):
        self.closed.append(h)
        if self.on_close:
            self.on_close(h)


class FakeThread:
    """A window thread that never ends by itself; it ends when ``stop`` is set."""

    def __init__(self, ends_after_joins=None):
        self.joins: list = []
        self.ends_after_joins = ends_after_joins
        self.stopped = False

    def is_alive(self):
        if self.ends_after_joins is not None and len(self.joins) >= self.ends_after_joins:
            return False
        return not self.stopped

    def join(self, timeout=None):
        self.joins.append(timeout)


class FakeClock:
    def __init__(self, thread, step=0.2):
        self.now, self.thread, self.step = 100.0, thread, step

    def __call__(self):
        self.now += self.step if self.thread.joins else 0.0
        return self.now


ME = os.getpid()
TITLE = claude_tab.PICK_TITLE


def test_own_windows_are_this_process_and_this_title_only():
    win = FakeWin({1: (ME, TITLE), 2: (ME + 1, TITLE), 3: (ME, "RAGbase Shield"), 4: (ME, TITLE), 5: (ME, TITLE)})
    win.broken.add(5)  # gone during the look: skipped, no error
    assert claude_tab._own_windows(TITLE, win) == [1, 4]

    class NoAnswer(FakeWin):
        def top_windows(self):
            raise OSError("EnumWindows")

    assert claude_tab._own_windows(TITLE, NoAnswer()) == []


def test_each_new_window_is_put_in_front_once_and_errors_stay_inside(monkeypatch):
    win = FakeWin({7: (ME + 1, TITLE)})  # another program's window with the same title is never touched
    thread = FakeThread(ends_after_joins=6)

    def join(timeout=None):
        thread.joins.append(timeout)
        if len(thread.joins) == 2:
            win.windows.update({8: (ME, TITLE), 9: (ME, TITLE)})
            win.refuse.add(9)  # bring_front fails on this one: the loop goes on, and it is not tried again

    thread.join = join
    claude_tab._watch_pick(thread, TITLE, 60.0, win, clock=FakeClock(thread))
    assert sorted(win.front) == [8, 9] and win.closed == [] and len(thread.joins) == 6
    assert all(t <= claude_tab.PICK_POLL for t in thread.joins)


def test_time_limit_closes_shields_own_window_then_waits(monkeypatch):
    win = FakeWin({11: (ME, TITLE), 12: (ME + 1, TITLE), 13: (ME, "RAGbase Shield")})
    thread = FakeThread()
    with pytest.raises(claude_tab.PickFailed) as exc:
        claude_tab._watch_pick(thread, TITLE, 1.0, win, clock=FakeClock(thread))
    assert exc.value.kind == "timeout"
    assert win.closed == [11]  # only Shield's own folder window, never Claude's or another program's
    assert thread.joins[-1] == claude_tab.PICK_CLOSE_WAIT
    assert claude_tab.PICK_TIMEOUT == 290.0


def _window_thread_fakes():
    import threading

    win = FakeWin()
    closed = threading.Event()
    calls: list = []

    def dialog(title, button):
        calls.append((title, button))
        win.windows[21] = (ME, title)
        closed.wait(10)
        win.windows.pop(21, None)
        return None  # WM_CLOSE closes the window as "Cancel"

    win.on_close = lambda h: closed.set()
    return win, dialog, calls


def test_time_limit_with_a_real_window_thread(monkeypatch):
    monkeypatch.setattr(claude_tab, "_PICK_THREAD", None)
    monkeypatch.setattr(claude_tab, "PICK_POLL", 0.01)
    win, dialog, calls = _window_thread_fakes()
    with pytest.raises(claude_tab.PickFailed) as exc:
        claude_tab._pick_windows(TITLE, 0.3, win=win, dialog=dialog)
    assert exc.value.kind == "timeout" and win.closed == [21] and win.front == [21]
    assert not claude_tab._PICK_THREAD.is_alive()  # the window is gone before the answer
    assert calls == [(TITLE, claude_tab.PICK_BUTTON)]
    # the next call opens a new window and the lawyer's choice comes back
    assert claude_tab._pick_windows(TITLE, 5.0, win=FakeWin(), dialog=lambda t, b: r"C:\Cabinet\Client A") == \
        r"C:\Cabinet\Client A"


def test_window_answers_cancel_and_failure(monkeypatch):
    monkeypatch.setattr(claude_tab, "_PICK_THREAD", None)
    with pytest.raises(claude_tab.PickCancelled):
        claude_tab._pick_windows(TITLE, 5.0, win=FakeWin(), dialog=lambda t, b: None)

    def broken(t, b):
        raise OSError("Show")

    with pytest.raises(claude_tab.PickFailed) as exc:
        claude_tab._pick_windows(TITLE, 5.0, win=FakeWin(), dialog=broken)
    assert exc.value.kind == "failed"


def test_a_window_that_did_not_close_blocks_a_second_one(monkeypatch):
    stuck = FakeThread()
    monkeypatch.setattr(claude_tab, "_PICK_THREAD", stuck)
    win = FakeWin({31: (ME, TITLE)})
    opened: list = []
    with pytest.raises(claude_tab.PickFailed) as exc:
        claude_tab._pick_windows(TITLE, 5.0, win=win, dialog=lambda t, b: opened.append(t))
    assert exc.value.kind == "failed" and opened == [] and win.closed == [31]
    stuck.stopped = True  # it closed after all: the next call opens a window
    assert claude_tab._pick_windows(TITLE, 5.0, win=FakeWin(), dialog=lambda t, b: "C:\\Dossier") == "C:\\Dossier"


class FakeUser32:
    def __init__(self, front=0, front_thread=0, fail_focus=False):
        self.log: list = []
        self.front, self.front_thread, self.fail_focus = front, front_thread, fail_focus

    def SetWindowPos(self, *a):
        self.log.append(("SetWindowPos",) + a)
        return 1

    def GetForegroundWindow(self):
        return self.front

    def GetWindowThreadProcessId(self, h, out):
        assert out is None
        return self.front_thread

    def AttachThreadInput(self, me, other, attach):
        self.log.append(("AttachThreadInput", me, other, attach))
        return 1

    def SetForegroundWindow(self, h):
        self.log.append(("SetForegroundWindow", h))
        if self.fail_focus:
            raise OSError("focus")
        return 1

    def PostMessageW(self, *a):
        self.log.append(("PostMessageW",) + a)
        return 1

    def GetSystemMetrics(self, i):
        return (1920, 1080)[i]

    def CreateWindowExW(self, *a):
        self.log.append(("CreateWindowExW",) + a)
        return 777


def _win_with(user32, me=50):
    w = object.__new__(claude_tab._Win32)
    w.user32 = user32

    class K:
        @staticmethod
        def GetCurrentThreadId():
            return me

    w.kernel32 = K
    return w


def test_focus_shares_input_for_one_call_and_always_detaches():
    u = FakeUser32(front=900, front_thread=60, fail_focus=True)
    with pytest.raises(OSError):
        _win_with(u).bring_front(41)
    assert u.log[0] == ("SetWindowPos", 41, -1, 0, 0, 0, 0, 0x1 | 0x2 | 0x40)  # HWND_TOPMOST, no size/move, shown
    assert u.log[1:] == [("AttachThreadInput", 50, 60, True), ("SetForegroundWindow", 41),
                         ("AttachThreadInput", 50, 60, False)]
    for front, thread in ((0, 0), (900, 50)):  # nothing in front, or our own thread in front: no attach at all
        u = FakeUser32(front=front, front_thread=thread)
        _win_with(u).bring_front(42)
        assert [e[0] for e in u.log] == ["SetWindowPos", "SetForegroundWindow"]


def test_owner_is_an_invisible_window_of_shield_and_close_is_wm_close():
    u = FakeUser32()
    w = _win_with(u)
    assert w.make_owner() == 777
    _name, ex, cls, title, style, x, y, cx, cy, parent, *_rest = u.log[0]
    assert (ex, cls, title, style) == (0x80 | 0x8, "STATIC", "RAGbase Shield", 0x80000000)  # no WS_VISIBLE
    assert (x, y, cx, cy, parent) == (960, 540, 0, 0, None)
    w.close(43)
    assert u.log[-1] == ("PostMessageW", 43, 0x0010, 0, 0)
    src = Path(claude_tab.__file__).read_text(encoding="utf-8")
    dialog_src = src[src.index("def _pick_windows_dialog"):src.index("def _pick_windows(")]
    assert "GetForegroundWindow" not in dialog_src and "owner = win.make_owner()" in dialog_src
    assert "win.destroy(owner)" in dialog_src[dialog_src.index("finally:"):]


def _make_xlsx(path: Path) -> None:
    import zipfile

    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                    'package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
        zf.writestr("_rels/.rels", f'<?xml version="1.0"?><Relationships {rel}><Relationship Id="rId1" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                    'Target="xl/workbook.xml"/></Relationships>')
        zf.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook {ns} xmlns:r="http://schemas.openxmlformats.'
                    'org/officeDocument/2006/relationships"><sheets><sheet name="Frais" sheetId="1" r:id="rId1"/>'
                    "</sheets></workbook>")
        zf.writestr("xl/_rels/workbook.xml.rels", f'<?xml version="1.0"?><Relationships {rel}><Relationship '
                    'Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                    'Target="worksheets/sheet1.xml"/></Relationships>')
        zf.writestr("xl/worksheets/sheet1.xml", f'<?xml version="1.0"?><worksheet {ns}><sheetData><row r="1">'
                    '<c r="A1" t="inlineStr"><is><t>Frais de greffe</t></is></c><c r="B1"><v>45</v></c></row>'
                    "</sheetData></worksheet>")


def test_excel_files_are_named_excel_in_the_document_list(folder):
    _make_xlsx(folder / "frais.xlsx")
    pick(folder)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    err, docs = call(server, "shield_list_documents", {"dossier": "DOSSIER_1"})
    assert not err and "| Excel |" in docs and "xlsx |" not in docs, docs
    assert claude_tab.TYPE_WORDS["xlsx"] == "Excel"


def test_unknown_argument_writes_one_french_sentence(capsys):
    for argv in (["--home", "/x"], ["--test-data", "/d", "--bogus"]):
        with pytest.raises(SystemExit) as exc:
            claude_tab._parse(argv)
        assert exc.value.code == 2
        out = capsys.readouterr()
        assert out.out == "" and out.err == "RAGbase Shield ne peut pas démarrer : réinstallez le plugin.\n"
    with pytest.raises(SystemExit) as exc:
        claude_tab.main(["--plugin-root"])  # stops before anything starts
    assert exc.value.code == 2 and "réinstallez le plugin" in capsys.readouterr().err
