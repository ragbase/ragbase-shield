"""Desktop installers (packaging/): the safety rules a lawyer's machine depends on, checked without building.

Covers the two review findings of 2026-10-27 that were left open in desk/ (1b: the service processes put the
current folder on sys.path; 2: ``service uninstall --purge-data`` could delete a custom data folder that holds
client files), plus static checks of what ships: home-domain package, no network tool in the install scripts,
hashed locks and pins, isolated launchers, no em or en dash, and the install guide's one-click section.
Nothing here builds a package, opens the network or touches launchd or the real HOME.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ragbase_shield import cli
from ragbase_shield.desk import service_manager as sm

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packaging"
TEXT_SUFFIXES = {".md", ".sh", ".py", ".xml", ".html", ".plist", ".json", ".in", ".txt", ".lock", ".entitlements"}


@pytest.fixture
def user_home(tmp_path, monkeypatch):
    """A temporary account home, and no launchd call: uninstall must never reach the real login item."""
    h = tmp_path / "userhome"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))  # Windows: Path.home() reads USERPROFILE, not HOME
    for name in ("CLAUDECODE", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED", "RAGBASE_SHIELD_AGENT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sm, "launchd_bootout", lambda runner=None: True)
    monkeypatch.setattr(sm, "delete_run_key", lambda: False)
    return h


# ------------------------------------------------------------------------------------------ finding 1b


def test_service_processes_keep_the_current_folder_out_of_sys_path():
    flags = sm.safe_flags()
    assert flags[:2] == ["-E", "-s"]
    if sys.version_info >= (3, 11):
        assert "-P" in flags
    assert sm.service_args()[:len(flags)] == flags
    child = sm.desk_child_command(7979)
    assert child[1:1 + len(flags)] == flags and child[-4:] == ["desk", "--service", "--port", "7979"]


def test_windows_launcher_is_isolated(monkeypatch):
    monkeypatch.setattr(sm, "is_windows", lambda: True)
    assert sm.launcher_args()[:1] == ["-I"]


@pytest.mark.skipif(sys.version_info < (3, 11), reason="-P exists from Python 3.11 (the installers ship 3.12)")
def test_planted_module_in_the_current_folder_does_not_run(tmp_path):
    work = tmp_path / "project"
    work.mkdir()
    marker = tmp_path / "planted-ran"
    (work / "json.py").write_text(f"open({str(marker)!r}, 'w').close()\nraise SystemExit(7)\n", encoding="utf-8")
    r = subprocess.run([sys.executable, *sm.safe_flags(), "-m", "json.tool"], input="{}", cwd=work,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "{}"
    assert not marker.exists()


# ------------------------------------------------------------------------------------------ finding 2


def _shield_files(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "desk_token").write_text("A" * 43 + "\n")
    (folder / "registry.db").write_bytes(b"")
    (folder / "registry.db-wal").write_bytes(b"")
    (folder / "vaults").mkdir(exist_ok=True)


def test_purge_keeps_a_custom_folder_that_holds_client_files(user_home, capsys):
    h = sm.home()  # conftest: a custom RAGBASE_SHIELD_HOME
    _shield_files(h)
    client = h / "Conclusions Mercadier.docx"
    client.write_bytes(b"client file")
    assert not sm.purge_allowed(h)
    r = sm.uninstall(purge_data=True)
    assert r == {"home": str(h), "purged": False, "refused": True}
    assert client.read_bytes() == b"client file" and (h / "desk_token").exists()
    # The CLI says so and does not advise deleting that folder.
    assert cli.main(["service", "uninstall", "--purge-data"]) == 0
    out = capsys.readouterr().out
    assert "rien n'y est supprimé" in out and "supprimez ce dossier" not in out
    assert client.exists()


def test_purge_deletes_a_custom_folder_with_shield_files_only(user_home):
    h = sm.home()
    _shield_files(h)
    assert sm.purge_allowed(h)
    r = sm.uninstall(purge_data=True)
    assert r["purged"] and not r["refused"] and not h.exists()


def test_purge_never_deletes_the_account_home(user_home, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_HOME", str(user_home))
    assert not sm.purge_allowed(user_home)
    monkeypatch.delenv("RAGBASE_SHIELD_HOME")
    assert not sm.purge_allowed(user_home)
    assert not sm.purge_allowed(Path(user_home.anchor))


def test_shield_names_match_the_macos_uninstaller():
    text = (PKG / "macos" / "uninstall.sh").read_text(encoding="utf-8")
    body = text.split("only_shield_files() {", 1)[1].split("\n}", 1)[0]
    names = set()
    for line in re.findall(r"^[ \t]+([^\s(|][^)\n]*)\) ;;$", body, re.M):
        names.update(n for n in line.split("|") if n != "registry.db-*")
    assert names and names <= sm.SHIELD_DATA_NAMES, names - sm.SHIELD_DATA_NAMES


# ------------------------------------------------------------------------------------------ what ships


def _packaging_text_files():
    return sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and (p.suffix in TEXT_SUFFIXES or p.parent.name == "scripts"))


def test_packaging_text_has_no_em_or_en_dash():
    files = _packaging_text_files() + [ROOT / "docs" / "INSTALL.md"]
    assert len(files) > 20
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert "—" not in text and "–" not in text, p.relative_to(ROOT)


def test_package_installs_in_the_home_domain_only():
    xml = (PKG / "macos" / "Distribution.xml").read_text(encoding="utf-8")
    assert 'enable_currentUserHome="true"' in xml
    assert 'enable_localSystem="false"' in xml and 'enable_anywhere="false"' in xml
    build = (PKG / "macos" / "build.sh").read_text(encoding="utf-8")
    assert 's/ auth="root"/ auth="none"/' in build  # no administrator password asked by Installer


@pytest.mark.parametrize("name", ["scripts/preinstall", "scripts/postinstall", "uninstall.sh"])
def test_install_scripts_make_no_network_call(name):
    text = (PKG / "macos" / name).read_text(encoding="utf-8")
    for word in ("curl", "wget", "http://", "https://", "pip install", "uv pip", "uv tool"):
        assert word not in text, f"{name}: {word!r}"
    for line in re.findall(r'"\$(?:PY|APP/runtime/bin/python3\.12)" -\S[^\n]*', text):
        assert line.split('" ', 1)[1].startswith("-E -s -P "), f"{name}: {line}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell scripts")
@pytest.mark.parametrize("name", ["scripts/preinstall", "scripts/postinstall", "uninstall.sh", "build.sh",
                                  "build_pkg.sh", "test_payload.sh", "compare_pkgs.sh", "sign_and_notarize_TODO.sh"])
def test_shell_scripts_parse(name):
    path = PKG / "macos" / name
    assert path.is_file(), name
    assert subprocess.run(["/bin/sh", "-n", str(path)], capture_output=True, timeout=30).returncode == 0, name


def test_launchers_run_python_in_isolated_mode():
    text = (PKG / "common" / "build_payload.py").read_text(encoding="utf-8")
    mac = text.split('MAC_LAUNCHER = """', 1)[1].split('"""', 1)[0]
    win = text.split("WIN_LAUNCHER = ", 1)[1].split("\n\n", 1)[0]
    assert re.search(r'exec "\$DIR/runtime/bin/python\{pyver\}" -I -X utf8 -m ragbase_shield "\$@"', mac)
    assert "python.exe\\\" -I -X utf8 -m ragbase_shield %*" in win


def test_every_download_is_pinned_by_sha256():
    pins = json.loads((PKG / "common" / "pins.json").read_text(encoding="utf-8"))
    targets = pins["python"]["targets"]
    assert set(targets) == {"macos-x86_64", "macos-arm64", "windows-x64"}
    for t in targets.values():
        assert re.fullmatch(r"[0-9a-f]{64}", t["sha256"]) and t["file"].endswith(".tar.gz")
    for lock in [*pins["wheels"]["locks"].values(), pins["build_tools"]["build_constraints"]]:
        text = (PKG / "common" / lock).read_text(encoding="utf-8")
        reqs = re.findall(r"^([A-Za-z0-9_.\-\[\]]+)==\S+((?:\s*\\\n\s+--hash=sha256:[0-9a-f]{64})+)", text, re.M)
        names = re.findall(r"^[A-Za-z0-9_.\-\[\]]+==", text, re.M)
        assert reqs and len(reqs) == len(names), lock  # every pin carries at least one hash


def test_no_gpl_tray_library():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "tray-mac" in pyproject and "tray-win" in pyproject
    for lock in (PKG / "common").glob("requirements-*.lock"):
        assert not re.search(r"^pystray==", lock.read_text(encoding="utf-8"), re.M), lock.name  # LGPL-3.0


def test_signing_is_a_todo_and_never_faked():
    script = (PKG / "macos" / "sign_and_notarize_TODO.sh").read_text(encoding="utf-8")
    assert "exit 2" in script and "notarytool" in script and "productsign" in script
    assert (PKG / "macos" / "TODO_SIGNING.md").is_file()


# ------------------------------------------------------------------------------------------ docs


def test_install_guide_has_the_one_click_section_in_both_languages():
    text = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
    fr, en = text.split("## Part 2. English", 1)
    assert "### 0. Installer en un clic" in fr and "### 0 bis. Autre méthode" in fr
    assert "### 0. One-click install" in en and "### 0b. Other way" in en
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
    wheel = f"https://github.com/ragbase/ragbase-shield/releases/download/v{version}/ragbase_shield-{version}-py3-none-any.whl"
    for part in (fr, en):
        assert "RAGbase-Shield-<version>.pkg" in part and "RAGbase-Shield-<version>-win64.msi" in part
        # The uv way runs the wheel of the release of this version (the 0 bis / 0b section).
        assert f"uvx --from {wheel} ragbase-shield desk" in part
        # No placeholder for a screenshot that does not exist (a public guide must not look unfinished).
        assert "à venir" not in part and "to come" not in part
    assert fr.index("### 0. Installer en un clic") < fr.index("### 0 bis. Autre méthode")


def test_packaging_readme_says_built_and_unsigned():
    text = (PKG / "README.md").read_text(encoding="utf-8")
    assert "built, unsigned" in text.lower() and "sign_and_notarize_TODO.sh" in text and "sign_TODO.ps1" in text
