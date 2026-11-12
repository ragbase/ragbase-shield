"""v0.4 W0: Windows compatibility, with general changes that hold on every platform.

- Vault: a damaged vault file never keeps an open handle (Windows cannot delete an open file).
- ``service.reset`` also closes the registries the hooks keep open (``verify`` removes its temporary home).
- PreToolUse, shell commands: Git Bash paths on Windows (``C:\\Users\\...``, ``/c/Users/...``), command lines run
  by a nested shell (``bash -c``, ``cmd /c``, ``powershell -Command`` and ``-EncodedCommand``, ``eval``,
  ``Invoke-Expression``), cmd.exe and PowerShell syntax (``cd /d``, ``dir /s``, ``for /r``, the ``^`` and backtick
  escapes, ``-Path:<value>``, ``$env:VAR``), and a ``cd`` that fails (the shell stays where it was).
- The value of an option (``--exclude-dir=<v>``, ``-Path:<v>``, cmd ``/g:<v>``) is checked but is never the path
  argument of a recursive or listing command, so the current folder is still checked; ``cd /d`` is cmd.exe syntax
  only; a shell never loses a folder it may be in (too many folder changes = denied); PowerShell braces inside a
  word stay literal, a script block is checked like a glob of the folder, ``foreach ($x in <command>)`` is read.
- ``file://`` paths written the Windows way.
- Packaging: the package that runs (source tree or installed wheel) holds every data file its code loads.
- File names stored in NFD (a folder copied from a Mac to NTFS) are listed and read.
- Test isolation: no test sees the machine's models or writes into the real Windows profile.

Every name, folder and value below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path

import pytest

import ragbase_shield
from ragbase_shield import cli, hooks, service
from ragbase_shield import vault as V
from ragbase_shield.desk import app as desk_app

TEXT = ("Madame Odile BRASQUELIN contre la société TOUVENOIX LOGISTIQUE SARL, représentée par "
        "M. Basile TOUVENOIX. Courriel : odile.brasquelin@exemple-brasquelin.fr.\n")
SECRETS = ("BRASQUELIN", "Brasquelin", "brasquelin", "TOUVENOIX", "Touvenoix")


@pytest.fixture(autouse=True)
def _fresh():
    service.reset()
    yield
    service.reset()


@pytest.fixture
def place(tmp_path):
    """tmp/Clients/Dossier Exemple (registered) and tmp/projet (an unrelated folder)."""
    folder = tmp_path / "Clients" / "Dossier Exemple"
    folder.mkdir(parents=True)
    (folder / "a.txt").write_text(TEXT, encoding="utf-8")
    service.add_dossier(folder, "Brasquelin c. Touvenoix Logistique")
    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "notes.md").write_text("rien\n", encoding="utf-8")
    autre = tmp_path / "autre"
    autre.mkdir()
    return {"tmp": tmp_path, "clients": folder.parent, "folder": folder, "projet": projet, "autre": autre}


def check(command: str, cwd: Path, powershell: bool = False):
    return hooks.check_command(command, str(cwd), hooks._guard(), powershell=powershell)


def ps_encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


# ------------------------------------------------------------------------------------------ vault and registries

def test_a_damaged_vault_file_leaves_no_open_handle(tmp_path, monkeypatch):
    bad = tmp_path / "abime.db"
    bad.write_bytes(b"ceci n'est pas une base SQLite " * 64)
    opened = []
    real_connect = sqlite3.connect

    def spy(*a, **k):
        conn = real_connect(*a, **k)
        opened.append(conn)
        return conn

    monkeypatch.setattr(V.sqlite3, "connect", spy)
    with pytest.raises(sqlite3.DatabaseError):
        V._connect(bad)
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError):  # closed: the file is free (Windows can delete it)
        opened[0].execute("SELECT 1")
    bad.unlink()
    assert not bad.exists()


def test_service_reset_closes_the_registries_the_hooks_keep(place):
    reg = hooks._registry()
    assert reg.folders() and hooks._REGISTRIES
    service.reset()
    assert hooks._REGISTRIES == {}
    with pytest.raises(sqlite3.ProgrammingError):
        reg._db.conn.execute("SELECT 1")


def test_temp_env_releases_its_home(tmp_path):
    home = tmp_path / "verify-home"
    with cli._temp_env(home):
        folder = tmp_path / "Dossier Temporaire"
        folder.mkdir()
        (folder / "a.txt").write_text(TEXT, encoding="utf-8")
        service.add_dossier(folder)
        assert hooks._registry().folders()
    assert hooks._REGISTRIES == {}
    shutil.rmtree(home)  # Windows: fails while a handle on registry.db is open
    assert not home.exists()


# ------------------------------------------------------------------------------------------ nested shells

@pytest.mark.parametrize("command", [
    'bash -c "cd {clients} && cat */a.txt"',
    "sh -c 'cd {clients}; cat */a.txt'",
    'bash -lc "cd {clients} && grep -rn acompte ."',
    'timeout 10 zsh -c "cd {clients} && ls"',
    'eval "cd {clients}; cat */a.txt"',
    'cmd /c "cd /d {clients} && type *\\a.txt"',
    'cmd.exe /s /c "cd /d {clients} & dir /s /b"',
    'cmd //c "cd /d {tmp} && dir /s /b"',
    'cmd /c "for /r {clients} %f in (*.txt) do type %f"',
    'cmd /c "cd /d {clients} && type Dossier^ Exemple\\a.txt"',
    'powershell -NoProfile -Command "Set-Location \'{clients}\'; Get-Content */a.txt"',
    'pwsh -c "Set-Location {clients}; Get-ChildItem -Recurse"',
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {enc}',
])
def test_a_nested_shell_cannot_reach_a_dossier(place, command):
    enc = ps_encoded(f"Set-Location '{place['clients']}'; Get-ChildItem -Recurse | Get-Content")
    cmd = command.format(clients=place["clients"], tmp=place["tmp"], enc=enc)
    assert check(cmd, place["projet"]) == "DOSSIER_1", cmd


@pytest.mark.parametrize("command", [
    'bash -c "echo bonjour"',
    "sh -c 'ls -la'",
    'cmd /c "dir /b"',
    'cmd //c "dir /s /b"',
    'powershell -NoProfile -Command "Get-ChildItem -Recurse"',
    "powershell -EncodedCommand {enc}",
    'eval "echo $((1 + 1))"',
])
def test_a_harmless_nested_shell_is_allowed(place, command):
    cmd = command.format(enc=ps_encoded("Write-Output 'bonjour'"))
    assert check(cmd, place["projet"]) is None, cmd


def test_powershell_tool_invoke_expression(place):
    cmd = f"iex \"Set-Location '{place['clients']}'; Get-Content */a.txt\""
    assert check(cmd, place["projet"], powershell=True) == "DOSSIER_1"
    assert check("iex \"Write-Output 'bonjour'\"", place["projet"], powershell=True) is None


def test_an_undecodable_encoded_command_is_not_an_error(place):
    assert check("powershell -EncodedCommand %%%pas-du-base64%%%", place["projet"]) is None


# ------------------------------------------------------------------------------------------ cd that fails

@pytest.mark.parametrize("command", [
    "cd /dossier/qui/n-existe/pas ; cat Clients/Dossier\\ Exemple/a.txt",
    "cd /dossier/qui/n-existe/pas || cat 'Clients/Dossier Exemple/a.txt'",
    "cd sous-dossier-absent && cd .. ; head -3 Clients/*/a.txt",
])
def test_a_failed_cd_keeps_the_old_folder(place, command):
    assert check(command, place["tmp"]) == "DOSSIER_1", command


def test_a_cd_to_an_existing_folder_moves(place):
    assert check("cd projet && cat notes.md", place["tmp"]) is None
    assert check("cd /dossier/qui/n-existe/pas ; ls", place["projet"]) is None


# ------------------------------------------------------------------------------------------ cmd.exe and PowerShell

def test_cmd_forms(place):
    assert check(f'cmd /c "cd /d {place["tmp"]} && dir /s /b"', place["projet"]) == "DOSSIER_1"
    assert check(f'cmd /c "cd /d {place["projet"]} && dir /s /b"', place["tmp"]) is None
    assert check(f'cmd /c "pushd {place["clients"]} && more < Dossier^ Exemple\\a.txt"', place["projet"]) == \
        "DOSSIER_1"


def test_powershell_forms(place, monkeypatch):
    clients = place["clients"]
    for cmd in (f"Set-Location '{clients}'; Get-Content Dossier` Exemple/a.txt",
                f"Set-Location -Path:'{clients}'; Get-Content -Path:'Dossier Exemple/a.txt'",
                f"cd '{clients}'; Get-ChildItem -Rec",
                f"cd '{clients}'; gci -r | Select-String acompte",
                f"Set-Location '{clients}'; Copy-Item -Recurse . $env:TEMP"):
        assert check(cmd, place["projet"], powershell=True) == "DOSSIER_1", cmd
    monkeypatch.setenv("SHIELD_W0_CLIENTS", str(clients))
    assert check("Set-Location $env:SHIELD_W0_CLIENTS; gci -r", place["projet"], powershell=True) == "DOSSIER_1"
    assert check("Set-Location ${env:shield_w0_clients}; Get-ChildItem -Recurse", place["projet"],
                 powershell=True) == "DOSSIER_1"
    assert check("Get-ChildItem -Recurse; Write-Output 'fin'", place["projet"], powershell=True) is None


def test_windows_words_quotes_and_escapes():
    ps = hooks._windows_words("Get-Content 'a ''b'' c' \"d `\"e`\" f\" g` h; Write-Output x", ps=True)
    assert ps == [["Get-Content", "a 'b' c", 'd "e" f', "g h"], ["Write-Output", "x"]]
    cm = hooks._windows_words('type "C:\\Dossier A\\x.txt" C:\\b^ c\\y.txt & dir /s', ps=False)
    assert cm == [["type", "C:\\Dossier A\\x.txt", "C:\\b c\\y.txt"], ["dir", "/s"]]


def test_home_and_environment_forms(monkeypatch):
    monkeypatch.setenv("SHIELD_W0_DIR", "/w0/dossiers")
    assert hooks._expand("$env:SHIELD_W0_DIR/a.txt") == "/w0/dossiers/a.txt"
    assert hooks._expand("$ENV:shield_w0_dir/a.txt") == "/w0/dossiers/a.txt"
    home = str(Path.home())
    assert Path(hooks._expand("%USERPROFILE%/Clients")) == Path(home) / "Clients"
    monkeypatch.delenv("HOME", raising=False)  # a hook started without HOME: the shell still knows it
    assert Path(hooks._expand("$HOME/Clients")) == Path(home) / "Clients"


# ------------------------------------------------------------------------------------------ Git Bash on Windows

def test_windows_reading_of_a_bash_command():
    r = hooks._windows_reading
    assert r(r"cd C:\Users\Compte\Clients && cat */a.txt") == "cd C:/Users/Compte/Clients && cat */a.txt"
    assert r(r"cp -r D:\Cabinet\Clients /tmp/copie") == "cp -r D:/Cabinet/Clients /tmp/copie"
    assert r(r"less C:\Users\Compte\Dossier\ Exemple\a.txt") == r"less C:/Users/Compte/Dossier\ Exemple/a.txt"
    assert r("cat /c/Users/Compte/a.txt") == "cat c:/Users/Compte/a.txt"
    assert r("ls /cygdrive/d/Dossiers /mnt/e/x") == "ls d:/Dossiers e:/x"
    for same in (r"find . -name \*.txt", r"echo a\ b", r'printf "x\\y"', "ls ./c/x a/c/x /tmp/x", "cmd /c dir",
                 r"grep \"x\" f"):
        assert r(same) == same, same


def test_bash_commands_with_windows_paths_are_denied_on_windows(place, monkeypatch):
    monkeypatch.setattr(hooks, "_WINDOWS", True)

    def win(p: Path) -> str:  # the path as a Windows user types it (backslashes)
        return str(p).replace("/", "\\")

    for cmd in (f"cd {win(place['clients'])} && cat */a.txt",
                f"cp -r {win(place['clients'])} /tmp/copie",
                f"cd {win(place['tmp'])} ; less Clients/Dossier\\ Exemple/a.txt",
                f"cd {win(place['tmp'])}\\Clients && cat < 'Dossier Exemple/a.txt'"):
        assert check(cmd, place["projet"]) == "DOSSIER_1", cmd
    for cmd in ("git status", "ls /", f"grep -r TODO {win(place['projet'])}", r"find . -name \*.md"):
        assert check(cmd, place["projet"]) is None, cmd


def test_hook_output_for_a_windows_command_holds_no_value(place, monkeypatch):
    import io
    import json

    monkeypatch.setattr(hooks, "_WINDOWS", True)
    cmd = f"cd {str(place['clients']).replace('/', chr(92))} && cat */a.txt"
    out, err = io.StringIO(), io.StringIO()
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(place["projet"])}
    rc = hooks.main("pre-tool-use", io.StringIO(json.dumps(payload)), out, err)
    text = out.getvalue() + err.getvalue()
    assert rc == 2 and json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert not any(s in text for s in SECRETS) and str(place["folder"]) not in text


def test_file_uri_written_the_windows_way():
    u = hooks._uri_path
    assert u("file://C:\\Users\\Compte\\a.txt") == "C:\\Users\\Compte\\a.txt"
    assert u("file:///C:\\Users\\Compte\\a.txt") == "C:\\Users\\Compte\\a.txt"
    assert u("file:///C:/Users/Compte/a%20b.txt") == "C:/Users/Compte/a b.txt"
    assert u("file://C%3A/Users/Compte/a.txt") == "C:/Users/Compte/a.txt"
    assert u("file:///Users/compte/a.txt") == "/Users/compte/a.txt"
    assert u("file://serveur/partage/a.txt") == "/partage/a.txt"


# ------------------------------------------------------------------------------------------ packaging, file names

def test_the_package_that_runs_holds_every_data_file_its_code_loads():
    pkg = Path(ragbase_shield.__file__).resolve().parent
    lexdir = pkg / "engine" / "lexicon"
    needed: set[str] = set()
    for py in (pkg / "engine").rglob("*.py"):
        needed |= set(re.findall(r'\b(?:_folded_set|read_lines|read_sections)\("([a-z0-9_]+\.txt)"',
                                 py.read_text(encoding="utf-8")))
    assert len(needed) >= 10
    missing = sorted(n for n in needed if not (lexdir / n).is_file())
    assert not missing, missing
    static = Path(desk_app.STATIC_DIR)
    html = (static / "index.html").read_text(encoding="utf-8")
    for ref in re.findall(r'(?:src|href)="/static/([^"]+)"', html):
        assert (static / ref).is_file(), ref


def test_a_file_named_in_nfd_is_listed_and_read(tmp_path):
    folder = tmp_path / "Dossier Exemple"
    folder.mkdir()
    name = unicodedata.normalize("NFD", "Pièce élève.txt")  # as copied from a Mac
    (folder / name).write_text(TEXT, encoding="utf-8")
    code = service.add_dossier(folder)["code"]
    docs = service.list_documents(code)
    assert len(docs) == 1
    got = service.read_document(code, docs[0]["id"])
    assert "PERSONNE_" in got["text"] and not any(s in got["text"] for s in SECRETS)


def test_tests_never_see_the_machine_models_or_the_real_profile(tmp_path):
    assert "RAGBASE_SHIELD_MODELS_DIR" not in os.environ
    for var in ("APPDATA", "LOCALAPPDATA", "RAGBASE_SHIELD_HOME"):
        assert Path(os.environ[var]).is_relative_to(tmp_path), var
    if os.name == "nt":  # the Claude Desktop settings a test may write are in the temporary profile
        assert cli.claude_desktop_config_path().is_relative_to(tmp_path)


def test_privacybench_runner_reads_files_in_the_same_order_on_every_os():
    """The runner sorted Path objects: a WindowsPath sorts case-insensitively, so the units of an export came in
    another order on Windows (other codes, another store state). ``ordered`` sorts case-sensitively, part by part."""
    import importlib.util
    from pathlib import PurePosixPath, PureWindowsPath

    path = Path(__file__).resolve().parents[1] / "evaluation" / "public" / "privacybench" / "run_shield.py"
    if not path.exists():
        pytest.skip("runner not present")
    spec = importlib.util.spec_from_file_location("privacybench_runner_w0", path)
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    names = ["drive/Zeta_Plan.pdf", "drive/alpha_notes.docx", "drive/Beta-Report.csv", "drive/beta/x.pdf", "D1/a.json",
             "d0/b.json"]
    posix = [str(p) for p in sorted(PurePosixPath(n) for n in names)]
    for cls in (PurePosixPath, PureWindowsPath):
        assert [p.as_posix() for p in R.ordered(cls(n) for n in names)] == posix, cls.__name__
    assert [p.as_posix() for p in sorted(PureWindowsPath(n) for n in names)] != posix  # the old Windows order


# ------------------------------------------------------------------------------------------ option values (try 2)

@pytest.mark.parametrize("command, where", [
    ("grep -r --exclude-dir=./none MOT", "clients"),
    ("grep -r --exclude=/none MOT", "tmp"),
    ("rg --type-add=x:./y MOT", "tmp"),
    ("ls --ignore=./zz", "clients"),
    ("ls --hide=/zz", "clients"),
    ("rg --glob=!./x MOT", "tmp"),
    ("grep -rl MOT --exclude=./x", "clients"),
    ("ls -la --color=always --hide=/zz", "clients"),
    ("find -name=./x", "tmp"),
    ('cmd /c "dir /s /b /a:-d"', "clients"),
    ('cmd /c "findstr /s /g:C:\\x\\list.txt motif"', "clients"),
    ('powershell -c "gci -r -Exclude:./zz"', "clients"),
    ('pwsh -NoProfile -Command "Get-ChildItem -Recurse -Filter:*.txt"', "clients"),
])
def test_an_option_value_is_never_the_path_argument(place, command, where):
    """A recursive or listing command with no positional path reads the current folder: the folder is checked
    whatever the options hold (the hook of try 1 read ``--x=./y`` as the path argument and let these through)."""
    assert check(command, place[where]) == "DOSSIER_1", command
    assert check(command, place["projet"]) is None, command


@pytest.mark.parametrize("command", [
    "Get-ChildItem -Recurse -Exclude:./zz",
    "gci -r -Filter:*.txt",
    "ls -Recurse -Exclude:C:\\zz",
    "Get-ChildItem -Recurse -Exclude:'\\\\srv\\share\\zz'",
    "Get-ChildItem -Path:. -Recurse",
])
def test_powershell_option_values_are_never_the_path_argument(place, command):
    assert check(command, place["clients"], powershell=True) == "DOSSIER_1", command
    assert check(command, place["projet"], powershell=True) is None, command


def test_windows_spellings_of_an_option_value(place, monkeypatch):
    """Backslashes, a drive letter and a UNC name in an option value: still not the path argument."""
    monkeypatch.setattr(hooks, "_WINDOWS", True)
    for cmd, where in (("grep -r --exclude-dir=.\\none MOT", "clients"),
                       ("rg --type-add=x:C:\\y MOT", "tmp"),
                       ("ls --hide=\\\\srv\\share\\zz", "clients"),
                       ("ls --hide=//srv/share/zz", "clients"),
                       ("ls --hide=D:/zz", "clients")):
        assert check(cmd, place[where]) == "DOSSIER_1", cmd
        assert check(cmd, place["projet"]) is None, cmd
    assert hooks._norm("\\\\srv\\share\\Clients") == hooks._norm("//srv/share/Clients")


def test_an_option_value_inside_a_dossier_is_denied(place):
    """The value is checked like a path (one more denial than HEAD, never one less)."""
    assert check(f'some-tool --input="{place["folder"]}/a.txt"', place["projet"]) == "DOSSIER_1"
    assert check(f"some-tool --input={place['projet']}/notes.md", place["projet"]) is None
    assert check(f'cmd /c "findstr /s /g:{place["folder"]}\\a.txt motif"', place["projet"]) == "DOSSIER_1"
    assert check("Select-String -Path:'Clients/Dossier Exemple/a.txt' -Pattern x", place["tmp"],
                 powershell=True) == "DOSSIER_1"


def test_a_file_filter_in_an_option_is_not_a_place(place):
    """``--include=*.txt`` filters names; it names no folder, so a command on another folder stays allowed. The
    folder is written as a Bash user writes it (forward slashes: a bare ``C:\\x`` loses its backslashes in Bash)."""
    projet = place["projet"].as_posix()
    for cmd in (f"grep -r --include=*.txt MOT {projet}", f"rg --type-add=x:*.y MOT {projet}",
                f"grep -rn --exclude=none MOT {projet}", f"find {projet} -name=x"):
        assert check(cmd, place["tmp"]) is None, cmd
    assert check("grep -r --include=*.txt MOT", place["tmp"]) == "DOSSIER_1"
    assert check(f"grep -r --include=*.txt MOT {place['clients'].as_posix()}", place["projet"]) == "DOSSIER_1"


def test_cmd_switch_with_a_quoted_value_is_a_switch():
    words = hooks._windows_words('findstr /c:"a b" /s x', ps=False)
    assert words == [["findstr", "/c:a b", "/s", "x"]]
    assert hooks._CMD_SWITCH.match("/c:a b") and hooks._CMD_SWITCH.match("/s") and hooks._CMD_SWITCH.match("/a:-d")
    assert not hooks._CMD_SWITCH.match("/srv/share/x") and not hooks._CMD_SWITCH.match("/tmp")


# ------------------------------------------------------------------------------------------ the X1 gaps (try 2)

def test_cd_d_is_cmd_syntax_only(place):
    """``cd /d <folder>`` fails in bash and zsh (the shell stays where it was); only cmd.exe moves."""
    tail = 'cat "Clients/Dossier Exemple/a.txt"'
    assert check(f"cd /d {place['autre']} ; {tail}", place["tmp"]) == "DOSSIER_1"
    assert check(f"cd /d {place['autre']} && {tail}", place["tmp"]) == "DOSSIER_1"
    assert check(f"Set-Location /d {place['autre']} ; gc 'Clients/Dossier Exemple/a.txt'", place["tmp"],
                 powershell=True) == "DOSSIER_1"
    inner = 'type "Clients\\Dossier Exemple\\a.txt"'
    assert check(f"cmd /c 'cd /d {place['autre']} && {inner}'", place["tmp"]) is None
    assert check(f"cmd /c 'cd /d {place['tmp']}\\no\\such && {inner}'", place["tmp"]) == "DOSSIER_1"


def test_cmd_without_d_keeps_the_drive(place):
    """cmd.exe ``cd`` without ``/d`` never changes the drive: a cd to another drive leaves the shell in place."""
    other_drive = "D:" + str(place["autre"]).replace("\\", "/")[2:] if os.name == "nt" else None
    if other_drive is None:
        pytest.skip("drive letters exist on Windows only")
    inner = 'type "Clients\\Dossier Exemple\\a.txt"'
    assert check(f"cmd /c 'cd {other_drive} && {inner}'", place["tmp"]) == "DOSSIER_1"


def test_cmd_cd_takes_the_rest_of_the_line(place):
    """cmd.exe: ``cd C:\\Dossier Exemple`` moves into the folder with the space (no quotes needed)."""
    spaced = place["tmp"] / "Dossier Exemple Bis"
    spaced.mkdir()
    (spaced / "a.txt").write_text("rien\n", encoding="utf-8")
    assert check(f'cmd /c "cd /d {spaced} && type a.txt"', place["projet"]) is None
    assert check(f'cmd /c "cd /d {place["clients"]} && type *\\a.txt"', place["projet"]) == "DOSSIER_1"


def test_a_shell_never_loses_a_folder_it_may_be_in(place):
    tail = 'cat "Clients/Dossier Exemple/a.txt"'
    many_abs = " ; ".join(f"cd /n{i}" for i in range(1, 13))
    assert check(f"{many_abs} ; {tail}", place["tmp"]) == "DOSSIER_1"  # the start folder is kept
    four_rel = " ; ".join(f"cd n{i}" for i in range(1, 5))
    assert check(f"{four_rel} ; {tail}", place["tmp"]) == "DOSSIER_1"  # 16 possible folders, all checked
    five_rel = " ; ".join(f"cd n{i}" for i in range(1, 6))
    assert check(f"{five_rel} ; {tail}", place["tmp"]) == "SHELL"  # past the limit: denied, not guessed
    assert check(f"{five_rel} ; ls", place["projet"]) == "SHELL"  # also when nothing could be reached
    assert "complexe" in hooks._deny_reason("SHELL") and "too complex" in hooks._deny_reason("SHELL")


def test_a_too_complex_command_is_denied_without_any_value(place):
    import io
    import json

    five_rel = " ; ".join(f"cd n{i}" for i in range(1, 6))
    payload = {"tool_name": "Bash", "tool_input": {"command": f"{five_rel} ; cat a.txt"}, "cwd": str(place["tmp"])}
    out, err = io.StringIO(), io.StringIO()
    rc = hooks.main("pre-tool-use", io.StringIO(json.dumps(payload)), out, err)
    text = out.getvalue() + err.getvalue()
    assert rc == 2 and json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "complexe" in text and not any(s in text for s in SECRETS) and str(place["folder"]) not in text


def test_powershell_braces_inside_a_word_stay_literal(place):
    assert check("gc Clients/{Dossier` Exemple}/a.txt", place["tmp"], powershell=True) == "DOSSIER_1"
    assert check("gc ./Clients/{Dossier Exemple}/a.txt", place["tmp"], powershell=True) == "DOSSIER_1"
    assert hooks._windows_words("gc a{b}c; & { cd x; ls }", ps=True) == [["gc", "a{b}c"], ["{"], ["cd", "x"],
                                                                         ["ls"]]


def test_powershell_script_blocks_and_foreach(place):
    clients = place["clients"]
    for cmd in ("foreach ($f in gci -r) { gc $f }",
                "gci -r | % { gc $_ }",
                "& { Set-Location Clients; gc */a.txt }"):
        assert check(cmd, place["tmp"], powershell=True) == "DOSSIER_1", cmd
    assert check(f"foreach ($f in gci -r '{clients}') {{ gc $f }}", place["projet"], powershell=True) == "DOSSIER_1"
    assert check(f"foreach ($f in Get-ChildItem '{clients}') {{ $f.Name }}", place["projet"],
                 powershell=True) == "DOSSIER_1"
    assert check("foreach ($f in gci) { $f.Name }", place["projet"], powershell=True) is None
    assert check("gci | % { $_.Name }", place["projet"], powershell=True) is None
