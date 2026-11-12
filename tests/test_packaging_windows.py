"""Windows installer (packaging/windows/): the rules the per-user .msi depends on, checked without Windows.

The .msi itself is built and tested on a Windows machine (packaging/windows/build.sh, build_msi.ps1,
test_install.ps1; packaging/README.md). Here: the WiX source (per-user scope, MajorUpgrade, custom actions that run
our own runtime with -E -s -P -X utf8 from a working folder outside the app folder), the generated components (HKCU
KeyPath, RemoveFolder, *.pyc clean-up), the staging of the MSI version and ProductCode, uninstall.cmd, the signing
TODO, and the Windows fixes in desk/ (loopback probe, tray, PID check). No network, no registry.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ragbase_shield.desk import loopback
from ragbase_shield.desk import service_manager as sm
from ragbase_shield.desk import tray

ROOT = Path(__file__).resolve().parents[1]
WIN = ROOT / "packaging" / "windows"
PINS = json.loads((ROOT / "packaging" / "common" / "pins.json").read_text(encoding="utf-8"))
NS = {"w": "http://wixtoolset.org/schemas/v4/wxs"}
FLAGS = "-E -s -P -X utf8 -m ragbase_shield"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_win_{name}", WIN / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ------------------------------------------------------------------------------------------ Package.wxs


def _package() -> ET.Element:
    return ET.parse(WIN / "Package.wxs").getroot()


def test_package_is_per_user_with_major_upgrade():
    pkg = _package().find("w:Package", NS)
    assert pkg is not None and pkg.get("Scope") == "perUser"
    assert pkg.get("ProductCode") == "$(var.ProductCode)" and pkg.get("UpgradeCode") == "$(var.UpgradeCode)"
    mu = pkg.find("w:MajorUpgrade", NS)
    assert mu is not None and mu.get("Schedule") == "afterInstallInitialize" and "récente" in mu.get("DowngradeErrorMessage")
    props = {p.get("Id"): p.get("Value") for p in pkg.findall("w:Property", NS)}
    assert props["ARPNOMODIFY"] == "1" and props["ARPNOREPAIR"] == "1"
    assert props["MSIRESTARTMANAGERCONTROL"] == "Disable"  # Restart Manager would "Quit" the tray
    std = {s.get("Id") for s in pkg.findall("w:StandardDirectory", NS)}
    assert std == {"LocalAppDataFolder", "ProgramMenuFolder"}  # nothing per machine
    progs = pkg.find("w:StandardDirectory[@Id='LocalAppDataFolder']/w:Directory", NS)
    assert progs.get("Name") == "Programs" and progs.find("w:Directory", NS).get("Name") == "RAGbase Shield"


def test_package_never_reboots_and_never_asks_for_one():
    """A file in use (an AI app runs the MCP server from runtime\\) made a /qn install or removal reboot the
    machine at once, and the Settings > Apps flow ask for a reboot (review 2026-11-03)."""
    pkg = _package().find("w:Package", NS)
    props = {p.get("Id"): p.get("Value") for p in pkg.findall("w:Property", NS)}
    assert props["REBOOT"] == "ReallySuppress"


def test_every_msiexec_call_of_the_vm_tests_and_the_it_sheet_passes_norestart():
    """With /qn and a file in use, msiexec reboots the machine unless /norestart (or REBOOT=ReallySuppress) is
    given: the VM is also the Hexagone trial machine, so every call carries the flag whatever the package."""
    ti = (WIN / "test_install.ps1").read_text(encoding="utf-8")
    assert ti.count("msiexec.exe") == 1  # one helper (Run-Msi); every call goes through it
    helper = ti.split("function Run-Msi", 1)[1].split("\n}", 1)[0]
    assert "msiexec.exe" in helper and '"/norestart"' in helper
    tb = (WIN / "test_basic_user.ps1").read_text(encoding="utf-8")
    calls = [ln for ln in tb.splitlines() if "msiexec.exe" in ln]
    assert len(calls) == 2 and all("/norestart" in ln for ln in calls), calls
    sheet = (WIN / "IT_SHEET.md").read_text(encoding="utf-8")
    silent = [ln for ln in sheet.splitlines() if ln.startswith("msiexec /i") or ln.startswith("msiexec /x")]
    assert len(silent) == 2 and all("/norestart" in ln for ln in silent), silent
    assert "3010" in sheet and "REBOOT=ReallySuppress" in sheet
    assert "/norestart" in (WIN / "uninstall.cmd").read_text(encoding="ascii")
    # W8b.2: a removal with python.exe in use returned 0 on the VM (files in use moved to C:\Config.Msi for the
    # next reboot), not 3010; the check accepts both, and the IT sheet names both
    w8b2 = [ln for ln in ti.splitlines() if 'Check "W8b.2"' in ln]
    assert len(w8b2) == 1 and "($rc -eq 0 -or $rc -eq 3010)" in w8b2[0], w8b2
    assert "returns 0 or 3010" in sheet


def test_vm_test_counters_are_never_shadowed():
    """PowerShell variable names are case-insensitive and a script-level assignment reaches $script: scope: a local
    "$pending = @()" in W8b turned the counter $script:Pending into an array, so the RESULT line died with "The
    '++' operator works only on numbers" after every check had passed (final build run of 2026-11-03)."""
    ti = (WIN / "test_install.ps1").read_text(encoding="utf-8")
    counters = {m.group(1).lower() for m in re.finditer(r"\$script:(\w+)\+\+", ti)}
    assert counters == {"pass", "fail", "pending"}, counters
    for name in counters:
        bad = [ln.strip() for ln in ti.splitlines() if re.search(rf"^\s*\${name}\s*=", ln, re.IGNORECASE)]
        assert not bad, bad
    assert 'Log "RESULT: $($script:Pass) passed, $($script:Fail) failed, $($script:Pending) pending"' in ti


def test_package_text_fits_code_page_1252():
    pkg = _package().find("w:Package", NS)
    assert pkg.get("Codepage") == "1252" and pkg.get("Language") == "1036"
    (WIN / "Package.wxs").read_text(encoding="utf-8").encode("cp1252")  # every character fits the MSI code page


def test_custom_actions_run_our_runtime_isolated_outside_the_app_folder():
    pkg = _package().find("w:Package", NS)
    cas = {c.get("Id"): c for c in pkg.findall("w:CustomAction", NS)}
    assert set(cas) == {"ShieldRegister", "ShieldStart", "ShieldStop", "ShieldStopEarly", "ShieldUnregister"}
    want = {"ShieldRegister": "service install --no-start", "ShieldStart": "service start",
            "ShieldStop": "service stop --quiet", "ShieldStopEarly": "service stop --quiet",
            "ShieldUnregister": "service uninstall --quiet --purge-extras"}
    for cid, ca in cas.items():
        cmd = ca.get("ExeCommand")
        assert cmd == f'"[INSTALLFOLDER]runtime\\RAGbase Shield.exe" {FLAGS} {want[cid]}', cid
        assert ca.get("Directory") == "LocalAppDataFolder", cid  # never a working folder inside <app>
        for word in ("powershell", "cmd.exe", "http", "pip", "uv "):
            assert word not in cmd.lower(), (cid, word)
    for cid in ("ShieldRegister", "ShieldStop", "ShieldUnregister"):
        assert cas[cid].get("Execute") == "deferred" and cas[cid].get("Impersonate") == "yes"
        assert cas[cid].get("Return") == "ignore"
    assert cas["ShieldStart"].get("Return") == "asyncNoWait"
    seq = {c.get("Action"): c for c in pkg.find("w:InstallExecuteSequence", NS)}
    assert seq["ShieldUnregister"].get("Condition") == 'REMOVE="ALL" AND NOT UPGRADINGPRODUCTCODE'
    assert seq["ShieldUnregister"].get("Before") == "RemoveFiles" and seq["ShieldStop"].get("Before") == "ShieldUnregister"
    assert seq["ShieldRegister"].get("After") == "InstallFiles" and seq["ShieldStart"].get("After") == "InstallFinalize"


def test_shortcut_and_run_key_use_the_service_flags():
    pkg = _package().find("w:Package", NS)
    sc = pkg.find(".//w:Shortcut", NS)
    assert sc.get("Target") == "[INSTALLFOLDER]runtime\\RAGbase Shield.exe"
    assert sc.get("Arguments") == f"{FLAGS} service start" and sc.get("WorkingDirectory") == "LocalAppDataFolder"
    kp = pkg.find(".//w:Component[@Id='StartMenuShortcut']/w:RegistryValue", NS)
    assert kp.get("Root") == "HKCU" and kp.get("KeyPath") == "yes"
    # The Run key written by "service install" carries the same flags as the custom actions.
    assert " ".join(sm.service_args()) == f"{FLAGS} service run"
    exe = Path(r"C:\Users\x\AppData\Local\Programs\RAGbase Shield\runtime\RAGbase Shield.exe")
    assert sm.run_key_command(exe).endswith(f'RAGbase Shield.exe" {FLAGS} service run')


# ------------------------------------------------------------------------------------------ gen_components.py


def _fake_payload(root: Path) -> Path:
    p = root / "payload"
    (p / "runtime" / "Lib" / "site-packages" / "pkg").mkdir(parents=True)
    (p / "runtime" / "RAGbase Shield.exe").write_bytes(b"MZ")
    (p / "runtime" / "python.exe").write_bytes(b"MZ")
    (p / "runtime" / "Lib" / "os.py").write_text("x = 1\n")
    (p / "runtime" / "Lib" / "site-packages" / "pkg" / "__init__.py").write_text("")
    (p / "runtime" / "Lib" / "site-packages" / "pkg" / "data.bin").write_bytes(b"\0")
    (p / "icons").mkdir()
    (p / "icons" / "shield.ico").write_bytes(b"\0")
    (p / "VERSION").write_text("0.3.1\n")
    return p


def test_components_are_per_user_shaped_and_clean_bytecode(tmp_path):
    gen = _load("gen_components")
    payload = _fake_payload(tmp_path)
    text = gen.generate(payload)
    assert text == gen.generate(payload)  # same tree, same file
    root = ET.fromstring(text)
    comps = root.findall(".//w:Component", NS)
    folders = {"."} | {d.relative_to(payload).as_posix() for d in payload.rglob("*") if d.is_dir()}
    assert len(comps) == len(folders)
    for c in comps:
        kp = [r for r in c.findall("w:RegistryValue", NS) if r.get("KeyPath") == "yes"]
        assert len(kp) == 1 and kp[0].get("Root") == "HKCU" and kp[0].get("Key") == gen.REG_KEY  # ICE38
        assert any(rf.get("On") == "uninstall" and rf.get("Directory") is None for rf in c.findall("w:RemoveFolder", NS))  # ICE64
        assert uuid.UUID(c.get("Guid").strip("{}"))
    files = root.findall(".//w:File", NS)
    assert len(files) == sum(1 for f in payload.rglob("*") if f.is_file())
    # Every folder with .py files gets a __pycache__ child whose *.pyc go at uninstall and update.
    pyc = root.findall(".//w:RemoveFile", NS)
    assert len(pyc) == 2 and all(r.get("Name") == "*.pyc" and r.get("On") == "both" for r in pyc)
    caches = [d for d in root.iter("{%s}Directory" % NS["w"]) if d.get("Name") == "__pycache__"]
    assert len(caches) == 2
    top = [c for c in comps if c.get("Directory") == "INSTALLFOLDER"][0]
    assert top.find("w:RemoveRegistryKey", NS).get("Key") == "Software\\RAGbase\\Shield"
    assert any(rf.get("Directory") == "ProgramsFolder" for rf in top.findall("w:RemoveFolder", NS))
    # Component GUIDs: uuid5 of the folder under the pinned namespace (stable across versions).
    ns = uuid.UUID(PINS["windows"]["shield_ns"])
    assert top.get("Guid") == "{" + str(uuid.uuid5(ns, "component:.")).upper() + "}"


def test_components_refuse_names_the_msi_cannot_hold(tmp_path):
    gen = _load("gen_components")
    payload = _fake_payload(tmp_path)
    (payload / "runtime" / "Lib" / "café.py").write_text("")
    with pytest.raises(SystemExit):
        gen.generate(payload)


# ------------------------------------------------------------------------------------------ stage_payload.py


def test_product_code_rule_is_the_pinned_one():
    st = _load("stage_payload")
    ns = uuid.UUID(PINS["windows"]["shield_ns"])
    assert st.product_code("0.3.1") == "{" + str(uuid.uuid5(ns, "ragbase-shield-win64-0.3.1")).upper() + "}"
    assert st.product_code("0.3.1") != st.product_code("0.3.2")
    assert st.msi_version_ok("0.4.0") and st.msi_version_ok("255.255.65535")
    for bad in ("0.4.0.1", "0.4", "256.0.0", "0.4.0rc1", ""):
        assert not st.msi_version_ok(bad), bad


def test_stage_sets_the_installed_product_code_everywhere(tmp_path):
    st = _load("stage_payload")
    payload = _fake_payload(tmp_path)
    (payload / "install_info.json").write_text(json.dumps({"version": "0.3.1", "target": "windows-x64",
                                                           "product_code": "{OLD}"}))
    shutil.copy2(WIN / "uninstall.cmd", payload / "uninstall.cmd")
    staged = tmp_path / "stage"
    v = st.stage(payload, staged, "0.3.2")
    code = st.product_code("0.3.2")
    info = json.loads((staged / "install_info.json").read_text())
    assert info["product_code"] == code and info["msi_version"] == "0.3.2"
    assert info["upgrade_code"] == "{" + PINS["windows"]["upgrade_code"] + "}"
    assert v["ProductCode"] == code and v["Version"] == "0.3.2" and v["UpgradeCode"] == info["upgrade_code"]
    unc = (staged / "uninstall.cmd").read_bytes().decode("ascii")
    assert f"msiexec.exe /x {code} /norestart %*" in unc and "__PRODUCT_CODE__" not in unc
    manifest = json.loads((staged / "MANIFEST.json").read_text())
    assert manifest["files"]["uninstall.cmd"] == __import__("hashlib").sha256(unc.encode()).hexdigest()
    assert json.loads(Path(str(staged) + ".msi_vars.json").read_text())["ShortcutGuid"] == st.shortcut_guid()
    assert (payload / "install_info.json").read_text().count("{OLD}") == 1  # the payload itself is not changed


def test_uninstall_cmd_leaves_the_app_folder_and_keeps_the_data():
    raw = (WIN / "uninstall.cmd").read_bytes()
    text = raw.decode("ascii")
    assert raw.count(b"\r\n") == raw.count(b"\n")  # CRLF only
    assert 'cd /d "%SystemRoot%"' in text and "msiexec.exe /x __PRODUCT_CODE__ /norestart %*" in text
    for line in text.splitlines():
        if line.lower().startswith("rem "):
            assert not set(line) & set("<>|&"), line  # no redirection or pipe hidden in a comment


# ------------------------------------------------------------------------------------------ build scripts, signing


def test_vm_scripts_hold_no_forbidden_word():
    deny = re.compile(r"C:[\\/]+shield([\\/\"' ;]|$)|"
                      r"restart-computer|stop-computer|shutdown|logoff|tsdiscon|tscon|rwinsta|lockworkstation", re.I | re.M)
    for name in ("build_msi.ps1", "test_install.ps1", "net_sampler.ps1", "mcp_probe.py", "Package.wxs", "sign_TODO.ps1"):
        assert not deny.search((WIN / name).read_text(encoding="utf-8")), name


def test_windows_signing_is_a_todo_and_never_faked():
    script = (WIN / "sign_TODO.ps1").read_text(encoding="utf-8")
    head = script.split("$Root =", 1)[0]
    assert "exit 2" in head and "TODO: certificate not configured" in head  # before anything is signed
    assert "signtool" in script and "/tr" in script and "verify /pa" in script
    doc = (WIN / "TODO_SIGNING.md").read_text(encoding="utf-8")
    assert "signtool sign /fd SHA256" in doc and "Trusted Signing" in doc


def test_windows_texts_have_no_em_or_en_dash():
    files = [p for p in WIN.iterdir() if p.is_file() and p.suffix in (".ps1", ".wxs", ".cmd", ".sh", ".py", ".md")]
    assert len(files) >= 12
    for p in files:
        text = p.read_bytes().decode("utf-8")
        assert "\u2014" not in text and "\u2013" not in text, p.name


# ------------------------------------------------------------------------------------------ desk/ fixes found on the VM


def test_loopback_connect_timeout_means_nothing_listens(monkeypatch):
    """Windows answers a closed loopback port after about 2 s of SYN retries: the 2 s probe timed out and the
    service took the free port for a busy one (VM, 2026-10-27)."""
    def slow_connect(self):
        raise TimeoutError("timed out")

    monkeypatch.setattr(loopback.http.client.HTTPConnection, "connect", slow_connect)
    assert loopback.get_json(7979, "/api/status", None, 2.0) == ("refused", None)


def test_loopback_closed_port_is_refused():
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    assert loopback.get_json(port, "/api/status", None, 2.0)[0] == "refused"


def test_windows_pid_check_needs_a_program_of_this_runtime(monkeypatch):
    monkeypatch.setattr(sm, "is_windows", lambda: True)
    here = Path(sys.executable).resolve().parent
    monkeypatch.setattr(sm, "_win_image_path", lambda pid: str(here / "python.exe"))
    assert sm._pid_is_shield(1234, "desk")
    monkeypatch.setattr(sm, "_win_image_path", lambda pid: r"C:\Program Files\Other\python.exe")
    assert not sm._pid_is_shield(1234, "desk")  # a recycled PID of another python
    monkeypatch.setattr(sm, "_win_image_path", lambda pid: "")
    assert not sm._pid_is_shield(1234, "desk")


class _FakeSysTray:
    QUIT = "QUIT"
    FIRST_ID = 1023

    def __init__(self, icon, hover_text, menu_options=None, on_quit=None, default_menu_index=None):
        self.hover = hover_text
        self.on_quit = on_quit
        opts = list(menu_options or ()) + [("Quit", None, self.QUIT)]
        self._menu_options = [o + (self.FIRST_ID + i,) for i, o in enumerate(opts)]
        self._menu_actions_by_id = {o[3]: o[2] for o in self._menu_options}
        self._notify_id = object()
        self.refreshed = 0
        self.executed: list[int] = []

    def _refresh_icon(self):
        self.refreshed += 1

    def _execute_menu_option(self, id):  # noqa: A002
        self.executed.append(id)


def test_windows_tray_fixes(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_UI", "fr")
    answers = []
    cls = tray._shield_systray_class(_FakeSysTray, lambda: answers.pop(0))
    t = cls(None, "Shield Desk : démarrage", (("Ouvrir Shield Desk", None, lambda s: None),))
    label, _icon, action, qid = t._menu_options[-1]
    assert label == "Quitter" and action == _FakeSysTray.QUIT  # the library's English "Quit", relabelled
    answers.extend([False, True])
    t._execute_menu_option(qid)
    assert t.executed == []  # Annuler: nothing stops
    t._execute_menu_option(qid)
    assert t.executed == [qid]
    t._execute_menu_option(_FakeSysTray.FIRST_ID)
    assert t.executed[-1] == _FakeSysTray.FIRST_ID  # other items: no dialog
    t._restart(None, None, 0, 0)
    assert t._notify_id is None and t.refreshed == 1  # TaskbarCreated: the icon is ADDED again


def test_windows_session_id_is_unknown_elsewhere():
    if sys.platform != "win32":
        assert tray.windows_session_id() is None


def test_tray_uninstall_runs_msiexec_outside_the_app_folder(monkeypatch, tmp_path):
    app = tmp_path / "RAGbase Shield"
    app.mkdir()
    calls = []
    monkeypatch.setattr(tray.subprocess, "Popen", lambda argv, **kw: calls.append((argv, kw)))
    monkeypatch.setattr(sm, "uninstall", lambda **kw: calls.append(("sm.uninstall", kw)))
    monkeypatch.setattr(tray.sys, "platform", "win32")
    monkeypatch.setenv("SystemRoot", r"C:\Windows")

    class _Sup:
        home = tmp_path / "home"

    ctl = tray.Controller(_Sup(), app)  # type: ignore[arg-type]
    code = "{9CDD5182-5007-5279-827A-0AB8663A576B}"
    (app / "install_info.json").write_text(json.dumps({"product_code": code}))
    ctl.uninstall()
    assert calls[-1][0] == ["msiexec", "/x", code] and calls[-1][1]["cwd"] == r"C:\Windows"
    (app / "install_info.json").write_text(json.dumps({"product_code": "/i evil.msi"}))
    ctl.uninstall()
    assert calls[-1][0] == "sm.uninstall"  # never an argument that is not a ProductCode


def test_verify_temp_env_closes_the_hook_registries(tmp_path):
    """Windows cannot delete an open registry.db: "verify" ended in "Erreur interne (PermissionError)" without its
    result line on the installed Shield (VM, 2026-10-27; patch W1 of the Windows set-up report)."""
    from ragbase_shield import cli, hooks

    closed = []

    class _Reg:
        def close(self):
            closed.append(1)

    with cli._temp_env(tmp_path / "home"):
        hooks._REGISTRIES["x"] = _Reg()
    assert closed == [1] and hooks._REGISTRIES == {}


# ------------------------------------------------------------------------------------------ review 2026-11-03 (privacy and security lens)


def test_installed_service_is_stopped_before_install_validate():
    """InstallValidate lists every process that holds a file to replace or remove, and it runs before any deferred
    action: the running supervisor and Desk were listed on each update and removal of the first build (a "files in
    use" dialog with a window). ShieldStopEarly stops the installed service first; never on a first install."""
    pkg = _package().find("w:Package", NS)
    seq = {c.get("Action"): c for c in pkg.find("w:InstallExecuteSequence", NS)}
    early = seq["ShieldStopEarly"]
    assert early.get("Before") == "InstallValidate"
    assert early.get("Condition") == "Installed OR WIX_UPGRADE_DETECTED"
    ca = {c.get("Id"): c for c in pkg.findall("w:CustomAction", NS)}["ShieldStopEarly"]
    assert ca.get("Execute") == "immediate" and ca.get("Return") == "ignore" and ca.get("Impersonate") is None
    order = [c.get("Action") for c in pkg.find("w:InstallExecuteSequence", NS)]
    assert order.index("ShieldStopEarly") < order.index("ShieldStop")
    ps = (WIN / "test_install.ps1").read_text(encoding="utf-8")
    assert "function Shield-FilesInUse" in ps and ps.count("Shield-FilesInUse (") >= 2  # update and removal logs


def test_run_key_command_quotes_the_program_path():
    """An unquoted path with spaces in a Run value is the classic planted-program hole (C:\\Program.exe)."""
    exe = Path(r"C:\Users\Jean Dupont\AppData\Local\Programs\RAGbase Shield\runtime\RAGbase Shield.exe")
    cmd = sm.run_key_command(exe)
    assert cmd == f'"{exe}" -E -s -P -X utf8 -m ragbase_shield service run' and cmd.count('"') == 2
    assert sm.safe_flags() == ["-E", "-s", "-P"]  # = -I on Python 3.11+: no PYTHON* variable, user site or current folder
    assert sm.launcher_args.__doc__ and "-I" in sm.launcher_args.__doc__


def test_vm_test_scripts_never_put_the_token_in_a_string():
    """The VM tests read the Desk token to call the Desk (header only); no printed or logged string may carry it."""
    for name in ("test_install.ps1", "test_basic_user.ps1"):
        text = (WIN / name).read_text(encoding="utf-8")
        assert "X-Shield-Token" in text
        for ln in text.splitlines():
            for literal in re.findall(r'"((?:[^"`]|`.)*)"', ln):  # every double-quoted PowerShell string
                assert not re.search(r"\$(tok|tokenSeen)\b", literal), (name, ln.strip())
            assert "Write-Output $tok" not in ln and "Log $tok" not in ln


def test_package_holds_no_url_but_the_about_link():
    """No network at install or start: the only URL in the package is the Settings > Apps 'about' link, a registry
    string that nothing fetches."""
    text = (WIN / "Package.wxs").read_text(encoding="utf-8")
    urls = [u for u in re.findall(r'https?://[^\s"<]+', text) if not u.startswith("http://wixtoolset.org/schemas/")]
    assert urls == ["https://ragbase.ai"]  # the XML namespace is an identifier, not an address
    assert 'Id="ARPURLINFOABOUT" Value="https://ragbase.ai"' in text


def test_it_sheet_and_install_guide_cover_the_review_cases():
    sheet = (WIN / "IT_SHEET.md").read_text(encoding="utf-8")
    assert "ShieldStopEarly" in sheet and "same name" in sheet  # the files-in-use box and its name match
    assert "HKCU" in sheet and "%WINDIR%\\Installer" in sheet  # what Windows Installer writes, and where
    guide = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
    fr, en = guide.split("## Part 2. English", 1)
    for part, phrases in ((fr, ("Éditeur inconnu", "Conserver quand même", "fermez d'abord Claude Desktop",
                                "uv tool uninstall ragbase-shield", "Applications de démarrage")),
                          (en, ("Unknown publisher", "Keep anyway", "close Claude Desktop, ChatGPT",
                                "uv tool uninstall ragbase-shield", "Startup apps"))):
        for phrase in phrases:
            assert phrase in part, phrase
