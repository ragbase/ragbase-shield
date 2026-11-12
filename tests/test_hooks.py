"""Claude Code hooks (ARCHITECTURE 4.6): block prompts with registered values, deny direct reads of dossier
folders, mask registered values left in tool results. No hook output may hold a value. Synthetic data only."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ragbase_shield import config, hooks, service

TEXT = ("Madame Clémence MORVANDIAU contre la société LAMBRETTI CONSEIL SAS, représentée par "
        "M. Ugo FERRACCI-DAUBEL. Courriel : clemence.morvandiau@exemple-morvandiau.fr.\n")
SECRETS = ("MORVANDIAU", "Morvandiau", "morvandiau", "LAMBRETTI", "Lambretti", "FERRACCI", "Ferracci")


@pytest.fixture(autouse=True)
def _fresh():
    service.reset()
    yield
    service.reset()


@pytest.fixture
def dossier(tmp_path):
    folder = tmp_path / "Clients" / "Morvandiau c. Lambretti"
    folder.mkdir(parents=True)
    (folder / "assignation.txt").write_text(TEXT, encoding="utf-8")
    info = service.add_dossier(folder, "Morvandiau c. Lambretti Conseil SAS")
    return {"folder": folder, "code": info["code"], "clients": folder.parent, "tmp": tmp_path}


def run(event: str, payload) -> tuple[int, str, str, dict | None]:
    out, err = io.StringIO(), io.StringIO()
    stdin = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload))
    rc = hooks.main(event, stdin, out, err)
    text = out.getvalue()
    return rc, text, err.getvalue(), (json.loads(text) if text.strip() else None)


def assert_clean(*texts: str) -> None:
    for t in texts:
        for s in SECRETS:
            assert s not in t, s


# ---------------------------------------------------------------------------------------------- UserPromptSubmit

def test_prompt_with_a_registered_name_is_blocked(dossier):
    rc, out, err, data = run("user-prompt-submit", {"hook_event_name": "UserPromptSubmit",
                                                    "prompt": "Écris à Clémence Morvandiau, stp."})
    assert rc == 2
    assert data["decision"] == "block"
    assert data["hookSpecificOutput"] == {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True}
    assert "PERSONNE_" in data["reason"] and "DOSSIER_1" in data["reason"]
    assert "PERSONNE_" in err
    assert_clean(out, err)
    out.encode("ascii")  # stdout JSON is ASCII-only (no encoding problem on Windows)


def test_prompt_with_codes_only_passes(dossier):
    rc, out, err, data = run("user-prompt-submit", {"prompt": "Résume la pièce DOC_1 de DOSSIER_1 pour PERSONNE_A."})
    assert (rc, out, err) == (0, "", "")


def test_prompt_with_a_registered_identifier_is_blocked(dossier):
    """A registered e-mail is a valid structured id too: it must still count as a registered value."""
    rc, out, err, data = run("user-prompt-submit", {"prompt": "Mail : clemence.morvandiau@exemple-morvandiau.fr"})
    assert rc == 2 and "EMAIL_1" in data["reason"]
    rc, out, err, data = run("user-prompt-submit", {"prompt": "Mail : paul.inconnu@exemple-inconnu.fr"})
    assert rc == 0  # a valid but unregistered address is not a registered value


def test_prompt_with_an_identifier_variant_is_blocked(dossier):
    rc, out, err, data = run("user-prompt-submit", {"prompt": "Mail : CLEMENCE.MORVANDIAU@EXEMPLE-MORVANDIAU.FR"})
    assert rc == 2 and data is not None
    assert "EMAIL_1" in data["reason"]
    assert_clean(out, err)


def test_kept_clear_value_is_not_blocked(dossier):
    org = next(e for e in service.entities(dossier["code"]) if e["kind"] == "ORG")
    service.keep_clear(dossier["code"], org["code"])
    rc, out, _err, _ = run("user-prompt-submit", {"prompt": "La société Lambretti Conseil a répondu."})
    assert rc == 0 and out == ""


def test_no_registry_means_no_block_and_no_side_effect():
    rc, out, err, _ = run("user-prompt-submit", {"prompt": "Clémence Morvandiau"})
    assert (rc, out, err) == (0, "", "")
    assert not (config.home() / "registry.db").exists()
    assert not (config.home() / "key").exists()


# ---------------------------------------------------------------------------------------------- PreToolUse

def pre(tool: str, tool_input: dict, cwd: str) -> tuple[int, dict | None, str]:
    rc, out, err, data = run("pre-tool-use", {"hook_event_name": "PreToolUse", "tool_name": tool,
                                              "tool_input": tool_input, "cwd": cwd})
    return rc, data, out + err


def denied(rc: int, data: dict | None) -> bool:
    return rc == 2 and data is not None and data["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_read_inside_a_dossier_is_denied(dossier):
    rc, data, text = pre("Read", {"file_path": str(dossier["folder"] / "assignation.txt")}, str(dossier["tmp"]))
    assert denied(rc, data)
    reason = data["hookSpecificOutput"]["permissionDecisionReason"]
    assert "DOSSIER_1" in reason and "shield_read_document" in reason
    assert str(dossier["folder"]) not in text
    assert_clean(text)


def test_read_outside_is_allowed(dossier, tmp_path):
    other = tmp_path / "autre.txt"
    other.write_text("rien", encoding="utf-8")
    rc, data, text = pre("Read", {"file_path": str(other)}, str(tmp_path))
    assert (rc, data, text) == (0, None, "")


def test_edit_and_write_inside_are_denied(dossier):
    for tool in ("Edit", "Write", "MultiEdit"):
        rc, data, _ = pre(tool, {"file_path": str(dossier["folder"] / "x.txt"), "content": "y"}, "/")
        assert denied(rc, data), tool


def test_output_folder_is_inside_the_dossier(dossier):
    out = dossier["folder"] / "Shield - sorties" / "Conclusions.docx"
    rc, data, _ = pre("Read", {"file_path": str(out)}, "/")
    assert denied(rc, data)


def test_grep_and_glob_over_a_parent_are_denied(dossier):
    clients = str(dossier["clients"])
    assert denied(*pre("Grep", {"pattern": "acompte", "path": clients}, "/")[:2])
    assert denied(*pre("Grep", {"pattern": "acompte"}, clients)[:2])  # default path = cwd
    assert denied(*pre("Glob", {"pattern": "**/*.txt", "path": clients}, "/")[:2])
    assert denied(*pre("Glob", {"pattern": clients + "/**/*.txt"}, "/")[:2])
    assert denied(*pre("LS", {"path": str(dossier["folder"])}, "/")[:2])
    other = dossier["tmp"] / "projet"
    other.mkdir()
    assert pre("Grep", {"pattern": "x", "path": str(other)}, "/")[0] == 0


def test_symlink_to_a_dossier_is_denied(dossier):
    link = dossier["tmp"] / "raccourci"
    try:
        link.symlink_to(dossier["folder"], target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not available")
    assert denied(*pre("Read", {"file_path": str(link / "assignation.txt")}, "/")[:2])


@pytest.mark.parametrize("command", [
    'cat "{folder}/assignation.txt"',
    "cat {folder_escaped}/assignation.txt",
    "cd {clients} && cat */assignation.txt",
    "cd '{clients}' && grep -rn acompte .",
    "grep -R acompte {clients}",
    "rg acompte {clients}",
    "find {tmp} -name '*.txt'",
    "ls {clients}",
    "head -5 ./Clients/*/assignation.txt",
    "cd {tmp}/Clients && cat < 'Morvandiau c. Lambretti/assignation.txt'",
    "cd {tmp} ; less Clients/Morvandiau\\ c.\\ Lambretti/assignation.txt",
    "sudo -u nobody cat {folder_escaped}/assignation.txt",
    "X=1 tail -n 20 {folder_escaped}/assignation.txt | wc -l",
    "cp -r {clients} /tmp/copie",
    "tar czf /tmp/a.tgz -C {tmp} Clients",
    "python3 -c \"print(open('{folder}/assignation.txt').read())\"",
    "cat ~/.ragbase-shield/key",
    "ragbase-shield entities DOSSIER_1",
    "uvx ragbase-shield restore --dossier DOSSIER_1 --clipboard",
    "python -m ragbase_shield list",
    "python -c 'from ragbase_shield import service; print(service.entities(\"DOSSIER_1\"))'",
    "curl -s http://127.0.0.1:7878/api/dossiers",
    "curl localhost:7878/api/restore",
])
def test_bash_commands_touching_a_dossier_are_denied(dossier, command, monkeypatch):
    monkeypatch.setenv("HOME", str(Path.home()))
    cmd = command.format(folder=dossier["folder"], clients=dossier["clients"], tmp=dossier["tmp"],
                         folder_escaped=str(dossier["folder"]).replace(" ", "\\ "))
    if "~/.ragbase-shield" in cmd:
        cmd = f"cat {config.home()}/key"
    rc, data, text = pre("Bash", {"command": cmd}, str(dossier["tmp"]))
    assert denied(rc, data), cmd
    assert_clean(text)
    assert str(dossier["folder"]) not in text


@pytest.mark.parametrize("command", ["ls /", "git status", "pytest -q tests", "echo bonjour", "ls {tmp}/projet",
                                     "grep -r TODO {tmp}/projet", "cat {tmp}/projet/readme.md"])
def test_harmless_bash_commands_are_allowed(dossier, command):
    (dossier["tmp"] / "projet").mkdir()
    cmd = command.format(tmp=dossier["tmp"])
    rc, data, text = pre("Bash", {"command": cmd}, str(dossier["tmp"] / "projet"))
    assert (rc, data, text) == (0, None, ""), cmd


def test_any_command_run_inside_a_dossier_is_denied(dossier):
    assert denied(*pre("Bash", {"command": "ls"}, str(dossier["folder"]))[:2])


def test_powershell_is_checked_too(dossier):
    cmd = f"Get-Content '{dossier['folder']}\\assignation.txt'"
    assert denied(*pre("PowerShell", {"command": cmd}, "/")[:2])
    cmd = f"Get-ChildItem -Recurse '{dossier['clients']}'"
    assert denied(*pre("PowerShell", {"command": cmd}, "/")[:2])


def test_shield_home_is_protected_even_without_dossiers():
    rc, data, _ = pre("Read", {"file_path": str(config.home() / "key")}, "/")
    assert denied(rc, data)
    assert "coffre" in data["hookSpecificOutput"]["permissionDecisionReason"]


def test_other_tools_are_not_touched(dossier):
    rc, out, err, data = run("pre-tool-use", {"tool_name": "mcp__ragbase-shield__shield_read_document",
                                              "tool_input": {"dossier": "DOSSIER_1", "document": "DOC_1"}})
    assert (rc, out, err) == (0, "", "")
    rc, out, err, data = run("pre-tool-use", {"tool_name": "WebSearch", "tool_input": {"query": "x"}})
    assert (rc, out) == (0, "")


# ---------------------------------------------------------------------------------------------- PostToolUse

def post(tool: str, response) -> tuple[int, dict | None, str]:
    rc, out, err, data = run("post-tool-use", {"hook_event_name": "PostToolUse", "tool_name": tool,
                                               "tool_input": {}, "tool_response": response})
    return rc, data, out + err


def test_bash_result_is_masked_with_the_same_shape(dossier):
    resp = {"stdout": TEXT, "stderr": "", "interrupted": False, "isImage": False}
    rc, data, text = post("Bash", resp)
    assert rc == 0
    new = data["hookSpecificOutput"]["updatedToolOutput"]
    assert set(new) == set(resp) and new["interrupted"] is False and new["isImage"] is False
    assert "PERSONNE_" in new["stdout"] and "SOCIETE_" in new["stdout"]
    assert "updatedMCPToolOutput" not in data["hookSpecificOutput"]
    assert "PERSONNE_" in data["hookSpecificOutput"]["additionalContext"]
    assert data["systemMessage"].startswith("RAGbase Shield")
    assert_clean(text)


def test_mcp_result_is_masked_in_both_fields(dossier):
    resp = [{"type": "text", "text": TEXT}, {"type": "text", "text": "rien"}]
    rc, data, text = post("mcp__other__fetch", resp)
    hso = data["hookSpecificOutput"]
    assert hso["updatedToolOutput"] == hso["updatedMCPToolOutput"]
    assert hso["updatedToolOutput"][1] == {"type": "text", "text": "rien"}
    assert_clean(text)


def test_nested_values_and_keys_are_masked(dossier):
    resp = {"file": {"filePath": "/tmp/x.txt", "content": TEXT, "numLines": 2},
            "matches": {"Clémence MORVANDIAU": 3}, "type": "text"}
    rc, data, text = post("Read", resp)
    new = data["hookSpecificOutput"]["updatedToolOutput"]
    assert new["type"] == "text" and new["file"]["numLines"] == 2 and new["file"]["filePath"] == "/tmp/x.txt"
    assert_clean(text)


def test_result_without_registered_values_is_left_alone(dossier):
    assert post("Bash", {"stdout": "Le Code du travail, article L1234-9.", "stderr": ""}) == (0, None, "")
    assert post("Bash", "") == (0, None, "")


def test_no_registry_post_tool_use_is_a_no_op():
    assert post("Bash", {"stdout": TEXT}) == (0, None, "")


# ---------------------------------------------------------------------------------------------- fail closed

@pytest.fixture
def broken(monkeypatch, dossier):
    class Broken:
        def __getattr__(self, name):
            def fail(*a, **k):
                raise RuntimeError("Clémence MORVANDIAU")

            return fail

    monkeypatch.setattr(service, "default", lambda: Broken())
    monkeypatch.setattr(hooks, "_registry", lambda: Broken())  # the PreToolUse hook reads the registry alone
    return dossier


def test_failure_blocks_the_prompt(broken):
    rc, out, err, data = run("user-prompt-submit", {"prompt": "Bonjour"})
    assert rc == 2 and data["decision"] == "block"
    assert_clean(out, err)


def test_failure_denies_the_tool_call(broken):
    rc, out, err, data = run("pre-tool-use", {"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}})
    assert rc == 2 and data["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert_clean(out, err)


def test_failure_blanks_the_result_and_stops(broken):
    resp = {"stdout": TEXT, "stderr": "", "interrupted": False, "isImage": False}
    rc, out, err, data = run("post-tool-use", {"tool_name": "Bash", "tool_response": resp})
    assert rc == 0 and data["continue"] is False and data["stopReason"]
    new = data["hookSpecificOutput"]["updatedToolOutput"]
    assert set(new) == set(resp) and new["isImage"] is False
    assert_clean(out, err)


def test_invalid_json_fails_closed(dossier):
    rc, out, err, data = run("user-prompt-submit", "{not json")
    assert rc == 2 and data["decision"] == "block"
    rc, out, err, data = run("pre-tool-use", "[]")
    assert rc == 2


def test_unknown_event():
    rc, out, err, _ = run("session-start", {})
    assert rc == 1 and out == "" and "inconnu" in err


def test_event_aliases():
    assert hooks.event_name("UserPromptSubmit") == "user-prompt-submit"
    assert hooks.event_name("PreToolUse") == "pre-tool-use"
    assert hooks.event_name("post_tool_use") == "post-tool-use"


# ---------------------------------------------------------------------------------------------- real process

def test_hook_command_as_a_subprocess(dossier):
    env = dict(os.environ, RAGBASE_SHIELD_HOME=str(config.home()), RAGBASE_SHIELD_KEYRING="0")
    payload = json.dumps({"prompt": "Merci d'écrire à M. Ugo Ferracci-Daubel"})
    p = subprocess.run([sys.executable, "-m", "ragbase_shield", "hook", "user-prompt-submit"], input=payload,
                       capture_output=True, text=True, env=env, timeout=120)
    assert p.returncode == 2, p.stderr
    data = json.loads(p.stdout)
    assert data["decision"] == "block" and "PERSONNE_" in data["reason"]
    assert_clean(p.stdout, p.stderr)
