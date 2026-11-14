"""Command line (ARCHITECTURE section 8): every command, agent-shell protection, install with backups and
--dry-run, doctor, verify, clipboard backends. Synthetic data only; HOME is redirected for app configs."""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

from ragbase_shield import cli, clipboard, config, service

ROOT = Path(__file__).resolve().parents[1]
TEXT = ("Madame Clémence MORVANDIAU contre la société LAMBRETTI CONSEIL SAS, représentée par "
        "M. Ugo FERRACCI-DAUBEL.\n")


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    for name in cli._AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    fake_home = tmp_path / "user-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("APPDATA", str(fake_home / "AppData"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_MARKETPLACE", raising=False)
    service.reset()
    yield
    service.reset()


@pytest.fixture
def which(monkeypatch):
    found = {"uvx": "/opt/uv/bin/uvx"}
    monkeypatch.setattr(cli.shutil, "which", lambda name: found.get(name))
    return found


@pytest.fixture
def dossier(tmp_path):
    folder = tmp_path / "Dossier Morvandiau"
    folder.mkdir()
    (folder / "assignation.txt").write_text(TEXT, encoding="utf-8")
    return folder


def run(argv: list[str], capsys, stdin: str | None = None, monkeypatch=None) -> tuple[int, str, str]:
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    return rc, out, err


# ---------------------------------------------------------------------------------------------- contract

def test_parser_has_every_command_of_section_8():
    arch = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    block = arch.split("## 8. CLI contract", 1)[1].split("```", 2)[1]
    names = set(re.findall(r"(?:^|/ )\s*(?:ragbase-shield )?([a-z][a-z-]+) [<\[A-Z-]|^ragbase-shield ([a-z-]+)\s",
                           block, re.M))
    commands = {a or b for a, b in names} | set(re.findall(r"^ragbase-shield ([a-z-]+)", block, re.M))
    commands |= {"import"} if "import <FILE>" in block else set()
    sub = next(a for a in cli.build_parser()._actions if a.dest == "command")
    assert commands <= set(sub.choices), commands - set(sub.choices)
    assert set(sub.choices) >= {"add", "list", "entities", "register", "keep-clear", "mask", "restore", "desk",
                                "mcp", "hook", "install", "doctor", "verify", "export", "import", "journal",
                                "set"}  # v0.2: "set" (SYNTH); other builders add their own subcommands
    install = sub.choices["install"]
    app = next(a for a in install._actions if a.dest == "app")
    assert set(app.choices) == {"claude-desktop", "claude-code", "chatgpt", "codex", "vscode"}


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0 and "0.4.1" in capsys.readouterr().out


def test_python_dash_m_works():
    p = subprocess.run([sys.executable, "-m", "ragbase_shield", "--version"], capture_output=True, text=True,
                       timeout=60)
    assert p.returncode == 0 and "ragbase-shield 0.4.1" in p.stdout


# ---------------------------------------------------------------------------------------------- dossier commands

def test_add_list_entities_register_keep_clear(dossier, capsys):
    rc, out, err = run(["add", str(dossier), "--title", "Morvandiau c. Lambretti Conseil SAS"], capsys)
    assert rc == 0 and out.strip() == "DOSSIER_1" and "document(s)" in err
    assert "MORVANDIAU" not in out + err
    rc, out, _ = run(["list"], capsys)
    assert rc == 0 and out.startswith("DOSSIER_1") and "Morvandiau c. Lambretti Conseil SAS" in out
    rc, out, _ = run(["entities", "DOSSIER_1"], capsys)
    assert rc == 0 and re.search(r"PERSONNE_A\tPERSON\t.*MORVANDIAU", out)
    rc, out, _ = run(["register", "DOSSIER_1", "--person", "Thibault Mercadier"], capsys)
    assert rc == 0 and re.fullmatch(r"PERSONNE_[A-Z]+\n", out)
    code = out.strip()
    rc, out, _ = run(["register", "DOSSIER_1", "--kind", "EMAIL", "t.mercadier@exemple-cabinet.fr"], capsys)
    assert rc == 0 and out.strip() == "EMAIL_1"
    rc, out, _ = run(["register", "DOSSIER_1", "--org", "Ateliers Brunelac"], capsys)
    assert rc == 0 and out.startswith("SOCIETE_")
    rc, out, _ = run(["keep-clear", "DOSSIER_1", code], capsys)
    assert rc == 0 and "gardé en clair" in out
    rc, out, _ = run(["entities", "DOSSIER_1"], capsys)
    assert "gardé en clair" in out
    rc, out, _ = run(["keep-clear", "DOSSIER_1", code, "--off"], capsys)
    assert rc == 0 and "masqué de nouveau" in out
    rc, out, err = run(["register", "DOSSIER_1", "--kind", "NAME", "x"], capsys)
    assert rc == 1 and "Erreur" in err


def test_register_needs_one_option(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["register", "DOSSIER_1"])
    assert e.value.code == 2


def test_unknown_dossier_is_a_clean_error(capsys):
    rc, out, err = run(["entities", "DOSSIER_9"], capsys)
    assert rc == 1 and "inconnu" in err and "Traceback" not in err


def test_agent_shell_protection(dossier, capsys, monkeypatch):
    run(["add", str(dossier), "--title", "Morvandiau c. Lambretti Conseil SAS"], capsys)
    monkeypatch.setenv("CLAUDECODE", "1")
    rc, out, err = run(["entities", "DOSSIER_1"], capsys)
    assert rc == 3 and "MORVANDIAU" not in out + err
    rc, out, err = run(["restore", "--dossier", "DOSSIER_1", "-"], capsys, "PERSONNE_A", monkeypatch)
    assert rc == 3 and "MORVANDIAU" not in out + err
    rc, out, err = run(["list"], capsys)
    assert rc == 0 and "DOSSIER_1" in out and "Morvandiau" not in out + err and "Codes seulement" in err
    rc, out, err = run(["mask", "--dossier", "DOSSIER_1", "-"], capsys, TEXT, monkeypatch)
    assert rc == 0 and "MORVANDIAU" not in out  # masking stays allowed: its output is masked


# ---------------------------------------------------------------------------------------------- mask / restore

def test_mask_and_restore_stdin(dossier, capsys, monkeypatch):
    run(["add", str(dossier)], capsys)
    rc, out, err = run(["mask", "--dossier", "DOSSIER_1"], capsys, TEXT, monkeypatch)
    assert rc == 0 and "PERSONNE_" in out and "MORVANDIAU" not in out and "remplacement(s)" in err
    rc, out2, err = run(["restore", "--dossier", "DOSSIER_1", "-"], capsys, out + " PERSONNE_ZZ", monkeypatch)
    assert rc == 0 and "MORVANDIAU" in out2 and "PERSONNE_ZZ" in err


def test_mask_without_dossier_warns(capsys, monkeypatch):
    rc, out, err = run(["mask"], capsys, "M. Ugo FERRACCI-DAUBEL", monkeypatch)
    assert rc == 0 and "FERRACCI" not in out and "restauration ne sera pas possible" in err


def test_mask_file_formats(dossier, capsys, tmp_path):
    import docx

    run(["add", str(dossier)], capsys)
    p = tmp_path / "piece.docx"
    d = docx.Document()
    d.add_paragraph("Madame Clémence MORVANDIAU et la société LAMBRETTI CONSEIL SAS.")
    d.save(str(p))
    rc, out, _ = run(["mask", "--dossier", "DOSSIER_1", str(p)], capsys)
    assert rc == 0 and "SOCIETE_" in out and "LAMBRETTI" not in out
    rc, out, err = run(["mask", str(tmp_path / "absent.txt")], capsys)
    assert rc == 2 and "introuvable" in err
    binf = tmp_path / "x.bin"
    binf.write_bytes(b"\x00\x01\x02" * 100)
    rc, out, err = run(["mask", str(binf)], capsys)
    assert rc == 2


def test_clipboard_round_trip(dossier, capsys, monkeypatch):
    run(["add", str(dossier)], capsys)
    board = {"text": TEXT}
    monkeypatch.setattr(clipboard, "paste", lambda: board["text"])
    monkeypatch.setattr(clipboard, "copy", lambda t: board.__setitem__("text", t))
    rc, out, err = run(["mask", "--dossier", "DOSSIER_1", "--clipboard"], capsys)
    assert rc == 0 and out == "" and "presse-papiers" in err
    assert "PERSONNE_" in board["text"] and "MORVANDIAU" not in board["text"]
    rc, out, err = run(["restore", "--dossier", "DOSSIER_1", "--clipboard"], capsys)
    assert rc == 0 and out == "" and "MORVANDIAU" in board["text"]


def test_clipboard_error_is_reported(capsys, monkeypatch):
    def fail():
        raise clipboard.ClipboardError("Presse-papiers indisponible")

    monkeypatch.setattr(clipboard, "paste", fail)
    rc, out, err = run(["mask", "--clipboard"], capsys)
    assert rc == 1 and "indisponible" in err


# ---------------------------------------------------------------------------------------------- clipboard backends

@pytest.mark.parametrize("platform,tools,env,copy_cmd,paste_cmd", [
    ("darwin", {"pbcopy", "pbpaste"}, {}, ["pbcopy"], ["pbpaste"]),
    ("linux", {"wl-copy", "wl-paste", "xclip"}, {"WAYLAND_DISPLAY": "wayland-0"}, ["wl-copy"],
     ["wl-paste", "--no-newline"]),
    ("linux", {"xclip"}, {}, ["xclip", "-selection", "clipboard", "-in"], ["xclip", "-selection", "clipboard", "-out"]),
    ("linux", {"xsel"}, {}, ["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"]),
])
def test_clipboard_backends(monkeypatch, platform, tools, env, copy_cmd, paste_cmd):
    calls = []
    monkeypatch.setattr(clipboard.sys, "platform", platform)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(clipboard.shutil, "which", lambda n: f"/usr/bin/{n}" if n in tools else None)

    def fake_run(cmd, input=None, **kw):
        calls.append((cmd, input))
        return types.SimpleNamespace(returncode=0, stdout="héllo".encode("utf-8"))

    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)
    clipboard.copy("Clémence")
    assert calls[-1] == (copy_cmd, "Clémence".encode("utf-8"))
    assert clipboard.paste() == "héllo" and calls[-1][0] == paste_cmd


def test_clipboard_windows_uses_powershell(monkeypatch):
    calls = []
    monkeypatch.setattr(clipboard.sys, "platform", "win32")
    monkeypatch.setattr(clipboard.shutil, "which", lambda n: "C:/ps/powershell.exe" if n == "powershell" else None)
    monkeypatch.setattr(clipboard.subprocess, "run", lambda cmd, input=None, **kw: (
        calls.append(cmd), types.SimpleNamespace(returncode=0, stdout=b"\xef\xbb\xbfa\r\nb"))[1])
    clipboard.copy("x")
    assert "Set-Clipboard" in calls[-1][-1] and "-NoProfile" in calls[-1]
    assert clipboard.paste() == "a\nb" and "Get-Clipboard" in calls[-1][-1]


def test_clipboard_missing_tool(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "linux")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(clipboard.shutil, "which", lambda n: None)
    with pytest.raises(clipboard.ClipboardError) as e:
        clipboard.copy("secret Morvandiau")
    assert "xclip" in str(e.value) and "Morvandiau" not in str(e.value)


def test_clipboard_command_failure_hides_the_text(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(clipboard.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=1, stdout=b"Morvandiau"))
    with pytest.raises(clipboard.ClipboardError) as e:
        clipboard.paste()
    assert "Morvandiau" not in str(e.value)


# ---------------------------------------------------------------------------------------------- install

def test_install_claude_desktop(capsys, which):
    path = cli.claude_desktop_config_path()
    rc, out, _ = run(["install", "claude-desktop", "--dry-run"], capsys)
    assert rc == 0 and "dry-run" in out and not path.exists()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}), encoding="utf-8")
    rc, out, _ = run(["install", "claude-desktop"], capsys)
    assert rc == 0 and "sauvegarde" in out
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["theme"] == "dark" and data["mcpServers"]["other"] == {"command": "x"}
    assert data["mcpServers"]["ragbase-shield"] == {"command": "/opt/uv/bin/uvx", "args": ["ragbase-shield", "mcp"]}
    backups = list(path.parent.glob("claude_desktop_config.json.bak-*"))
    assert len(backups) == 1 and "ragbase-shield" not in backups[0].read_text(encoding="utf-8")
    rc, out, _ = run(["install", "claude-desktop"], capsys)
    assert rc == 0 and "déjà configuré" in out
    assert len(list(path.parent.glob("*.bak-*"))) == 1


def test_install_refuses_a_file_it_cannot_parse(capsys, which):
    path = cli.claude_desktop_config_path()
    path.parent.mkdir(parents=True)
    path.write_text('{"mcpServers": {}, // commentaire\n}', encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    rc, out, err = run(["install", "claude-desktop"], capsys)
    assert rc == 1 and "rien n'a été modifié" in err and path.read_text(encoding="utf-8") == before


def test_install_vscode(capsys, which):
    path = cli.vscode_mcp_path()
    rc, out, _ = run(["install", "vscode"], capsys)
    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"servers": {"ragbase-shield": {"type": "stdio", "command": "/opt/uv/bin/uvx",
                                                   "args": ["ragbase-shield", "mcp"]}}}


def test_install_without_uvx_uses_the_installed_command(capsys, which):
    which.pop("uvx")
    which["ragbase-shield"] = "/opt/tools/bin/ragbase-shield"
    run(["install", "vscode"], capsys)
    data = json.loads(cli.vscode_mcp_path().read_text(encoding="utf-8"))
    assert data["servers"]["ragbase-shield"]["command"] == "/opt/tools/bin/ragbase-shield"
    assert data["servers"]["ragbase-shield"]["args"] == ["mcp"]


def test_install_codex_appends_and_replaces(capsys, which):
    tomllib = pytest.importorskip("tomllib")
    path = cli.codex_config_path()
    path.parent.mkdir(parents=True)
    path.write_text('model = "o4"\n\n[mcp_servers.other]\ncommand = "x"\n', encoding="utf-8")
    rc, out, _ = run(["install", "codex", "--dry-run"], capsys)
    assert rc == 0 and "[mcp_servers.ragbase-shield]" in out
    assert "ragbase-shield" not in path.read_text(encoding="utf-8")
    rc, out, _ = run(["install", "chatgpt"], capsys)
    assert rc == 0 and "ChatGPT" in out
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["model"] == "o4" and data["mcp_servers"]["other"] == {"command": "x"}
    entry = data["mcp_servers"]["ragbase-shield"]
    assert entry["command"] == "/opt/uv/bin/uvx" and entry["args"] == ["ragbase-shield", "mcp"]
    assert entry["default_tools_approval_mode"] == "writes" and entry["startup_timeout_sec"] == 60
    # an old entry is replaced, other tables are kept
    text = path.read_text(encoding="utf-8").replace("/opt/uv/bin/uvx", "/old/uvx")
    path.write_text(text + '\n[mcp_servers.ragbase-shield.env]\nA = "1"\n\n[profiles.x]\nmodel = "y"\n',
                    encoding="utf-8")
    rc, out, _ = run(["install", "codex"], capsys)
    assert rc == 0
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["mcp_servers"]["ragbase-shield"]["command"] == "/opt/uv/bin/uvx"
    assert "env" not in data["mcp_servers"]["ragbase-shield"] and data["profiles"]["x"] == {"model": "y"}
    assert data["mcp_servers"]["other"] == {"command": "x"}
    assert len(list(path.parent.glob("config.toml.bak-*"))) >= 2


def test_install_codex_refuses_invalid_toml(capsys, which):
    pytest.importorskip("tomllib")
    path = cli.codex_config_path()
    path.parent.mkdir(parents=True)
    path.write_text("[broken\n", encoding="utf-8")
    rc, out, err = run(["install", "codex"], capsys)
    assert rc == 1 and path.read_text(encoding="utf-8") == "[broken\n"


def test_install_claude_code_plugin_from_the_repo(capsys, which, monkeypatch):
    if Path(cli.__file__).resolve() == (ROOT / "src" / "ragbase_shield" / "cli.py").resolve():
        assert cli._repo_root() == ROOT  # Shield runs from this checkout: it finds the plugin marketplace
    else:  # Shield runs from an installed wheel (no checkout around it): the tests' checkout is the repo
        if not (ROOT / ".claude-plugin" / "marketplace.json").is_file():
            pytest.skip("the test tree has no .claude-plugin folder")
        monkeypatch.setattr(cli, "_repo_root", lambda: ROOT)
    which["claude"] = "/opt/claude/bin/claude"
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: (
        calls.append(cmd), types.SimpleNamespace(returncode=0, stdout="ok", stderr=""))[1])
    rc, out, _ = run(["install", "claude-code", "--dry-run"], capsys)
    assert rc == 0 and calls == [] and "plugin install ragbase-shield@ragbase" in out
    rc, out, _ = run(["install", "claude-code"], capsys)
    assert rc == 0
    assert calls == [["/opt/claude/bin/claude", "plugin", "marketplace", "add", str(ROOT)],
                     ["/opt/claude/bin/claude", "plugin", "install", "ragbase-shield@ragbase", "--scope", "user"]]


def test_install_claude_code_mcp_only_and_missing_cli(capsys, which, monkeypatch):
    monkeypatch.setattr(cli, "_repo_root", lambda: None)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=1 if cmd[1:3] == ["mcp", "get"] else 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc, out, err = run(["install", "claude-code"], capsys)
    assert rc == 1 and "claude mcp add --scope user ragbase-shield -- /opt/uv/bin/uvx ragbase-shield mcp" in err
    assert calls == []
    which["claude"] = "/opt/claude/bin/claude"
    rc, out, err = run(["install", "claude-code"], capsys)
    assert rc == 0 and "hooks" in out
    assert calls[-1] == ["/opt/claude/bin/claude", "mcp", "add", "--scope", "user", "ragbase-shield", "--",
                         "/opt/uv/bin/uvx", "ragbase-shield", "mcp"]


# ---------------------------------------------------------------------------------------------- doctor / verify

def test_doctor(capsys, dossier):
    run(["add", str(dossier)], capsys)
    rc, out, err = run(["doctor"], capsys)
    assert rc == 0, out
    assert "Clé du coffre : fichier 0600" in out and "Coffre : 1 dossier(s)" in out
    assert "Claude Desktop" in out and "VS Code" in out and "ChatGPT desktop / Codex" in out
    assert "MORVANDIAU" not in out and str(dossier) not in out
    assert "FAIL" not in out


def test_doctor_flags_open_permissions(capsys, dossier):
    if os.name != "posix":
        pytest.skip("POSIX permissions")
    run(["add", str(dossier)], capsys)
    token = config.home() / "desk_token"
    token.write_text("x", encoding="utf-8")
    os.chmod(token, 0o644)
    rc, out, _ = run(["doctor"], capsys)
    assert rc == 1 and re.search(r"FAIL\s+Jeton Shield Desk : droits 644", out)


def test_doctor_reports_a_wrong_key(capsys, dossier):
    run(["add", str(dossier)], capsys)
    service.reset()
    (config.home() / "key").write_bytes(b"A" * 43 + b"=")
    rc, out, _ = run(["doctor"], capsys)
    assert rc == 1 and "FAIL  Coffre" in out


def test_verify_is_clean_and_leaves_the_real_home_alone(capsys):
    home_before = os.environ["RAGBASE_SHIELD_HOME"]
    rc, out, err = run(["verify"], capsys)
    assert rc == 0, out
    assert "LEAK" not in out and "Résultat : CLEAN" in out
    for path in ("mcp shield_read_document", "mcp stdio", "hook user-prompt-submit", "hook pre-tool-use Read",
                 "hook post-tool-use Bash", "journal", "logs"):
        assert path in out, path
    assert os.environ["RAGBASE_SHIELD_HOME"] == home_before
    assert not (config.home() / "registry.db").exists()


def test_verify_detects_a_leak(capsys, monkeypatch):
    """If a tool returned a real value, verify must say LEAK and exit non-zero."""
    import functools

    from ragbase_shield import mcp_server

    real = mcp_server.shield_list_documents

    @functools.wraps(real)
    def leaky(dossier):
        return real(dossier) + "\nClémence Morvandiau"

    monkeypatch.setattr(mcp_server, "shield_list_documents", leaky)
    monkeypatch.setattr(mcp_server, "_TOOLS", tuple((leaky if f is real else f, t, h)
                                                     for f, t, h in mcp_server._TOOLS))
    monkeypatch.setattr(cli, "_verify_stdio", lambda *a: ("SKIP", "mcp stdio", "test"))
    monkeypatch.setattr(service.Service, "guard_output", lambda self, text: text)
    rc, out, _ = run(["verify"], capsys)
    assert rc == 1 and "LEAK   mcp shield_list_documents" in out and "Résultat : LEAK" in out


def test_leak_checker():
    c = cli.LeakChecker(["Clémence MORVANDIAU", "Blanc", "FR76 1756 9003 4240 7182 3509 645", "Martin"])
    assert c.find("Mme CLÉMENCE MORVANDIAU") and c.find("iban FR7617569003424071823509645")
    assert not c.find("chèque en blanc") and not c.find("PERSONNE_A et SOCIETE_B")


# ---------------------------------------------------------------------------------------------- other commands

def test_hook_command(capsys, monkeypatch, dossier):
    run(["add", str(dossier), "--title", "Morvandiau c. Lambretti Conseil SAS"], capsys)
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(dossier / "assignation.txt")}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    rc = cli.main(["hook", "pre-tool-use"])
    out, err = capsys.readouterr()
    assert rc == 2 and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_export_import_and_journal(capsys, monkeypatch, dossier, tmp_path):
    run(["add", str(dossier), "--title", "Morvandiau c. Lambretti Conseil SAS"], capsys)
    answers = iter(["phrase-de-passe-longue", "phrase-de-passe-longue"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))
    target = tmp_path / "handoff.shield"
    rc, out, err = run(["export", "DOSSIER_1", str(target)], capsys)
    assert rc == 0 and target.exists() and b"MORVANDIAU" not in target.read_bytes()
    other = tmp_path / "colleague"
    other.mkdir()
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "phrase-de-passe-longue")
    rc, out, err = run(["import", str(target), "--folder", str(other)], capsys)
    assert rc == 0 and out.strip() == "DOSSIER_2"
    rc, out, err = run(["journal"], capsys)
    assert rc == 0 and "dossier_imported" in out and "MORVANDIAU" not in out
    rc, out, err = run(["journal", "DOSSIER_1"], capsys)
    assert rc == 0 and "export" in out


def test_export_rejects_a_short_passphrase(capsys, monkeypatch, dossier, tmp_path):
    run(["add", str(dossier)], capsys)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "court")
    rc, out, err = run(["export", "DOSSIER_1", str(tmp_path / "x")], capsys)
    assert rc == 2 and not (tmp_path / "x").exists()


def test_desk_missing_module(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "ragbase_shield.desk.app", None)
    rc, out, err = run(["desk", "--no-browser"], capsys)
    assert rc == 2 and "Shield Desk" in err


def test_desk_calls_serve_with_supported_arguments(capsys, monkeypatch):
    seen = {}
    fake = types.ModuleType("ragbase_shield.desk.app")

    def serve(port, open_browser):
        seen.update(port=port, open_browser=open_browser)

    fake.serve = serve
    monkeypatch.setitem(sys.modules, "ragbase_shield.desk.app", fake)
    import ragbase_shield.desk as desk_pkg

    monkeypatch.setattr(desk_pkg, "app", fake, raising=False)
    rc, out, err = run(["desk", "--port", "7999", "--no-browser"], capsys)
    assert rc == 0 and seen == {"port": 7999, "open_browser": False}
    monkeypatch.setenv("CLAUDECODE", "1")

    def serve2(port=7878, open_browser=True, show_token=True):
        seen.update(port=port, open_browser=open_browser, show_token=show_token)

    fake.serve = serve2
    rc, out, err = run(["desk"], capsys)
    assert rc == 0 and seen["open_browser"] is False and seen["show_token"] is False
