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
