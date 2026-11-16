"""Background service of the desktop installers (packaging/DESIGN.md section 10): login item, supervisor,
token rules, install.json, server_command and doctor. Runs in the dev venv: no payload, no launchd, no
registry (the launchctl runner is mocked; the Windows-only parts are skipped elsewhere)."""
from __future__ import annotations

import http.server
import json
import os
import plistlib
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from ragbase_shield import __version__, cli
from ragbase_shield.desk import service_manager as sm
from ragbase_shield.desk import tray

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _not_agent(monkeypatch):
    for name in ("CLAUDECODE", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED", "RAGBASE_SHIELD_AGENT"):
        monkeypatch.delenv(name, raising=False)


def _home() -> Path:
    from ragbase_shield import config

    return config.home()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Runner:
    """Records launchctl calls; "print" answers not loaded until a bootstrap succeeded."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.loaded = False

    def __call__(self, cmd):
        self.calls.append([str(c) for c in cmd])
        verb = cmd[1] if len(cmd) > 1 else ""
        rc = 0
        if verb == "print":
            rc = 0 if self.loaded else 113
        elif verb == "bootstrap":
            self.loaded = True
        elif verb == "bootout":
            self.loaded = False
        return subprocess.CompletedProcess(cmd, rc, "", "")


# ------------------------------------------------------------------------------------------ plist


def test_plist_matches_reference_file():
    exe = "/Users/NAME/Library/Application Support/RAGbase Shield/RAGbase Shield.app/Contents/MacOS/RAGbase Shield"
    data = sm.render_plist([exe, *sm.service_args()], {}, Path("/Users/NAME/.ragbase-shield/logs"))
    ref = plistlib.loads((ROOT / "packaging" / "macos" / "ai.ragbase.shield.plist").read_bytes())
    if sys.version_info < (3, 11):  # no -P before Python 3.11 (the installers ship 3.12)
        ref["ProgramArguments"].remove("-P")
    assert plistlib.loads(data) == ref
    d = plistlib.loads(data)
    assert d["Label"] == "ai.ragbase.shield"
    assert d["KeepAlive"] == {"SuccessfulExit": False}
    assert d["ProgramArguments"][-4:] == ["-m", "ragbase_shield", "service", "run"]
    assert d["EnvironmentVariables"]["RAGBASE_SHIELD_SERVICE"] == "1"


@pytest.mark.skipif(sys.platform != "darwin", reason="LaunchAgent: macOS only")
def test_login_item_written_under_home_and_bootstrapped(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "userhome"))
    monkeypatch.setenv("RAGBASE_SHIELD_PORT", "7979")
    runner = _Runner()
    exe = tmp_path / "exe"
    exe.write_text("")
    assert sm.enable_login_item(exe, runner=runner) == "launchagent"
    path = tmp_path / "userhome" / "Library" / "LaunchAgents" / "ai.ragbase.shield.plist"
    assert path.is_file() and sm.launch_agent_path() == path
    d = plistlib.loads(path.read_bytes())
    assert d["ProgramArguments"][0] == str(exe)
    assert d["EnvironmentVariables"]["RAGBASE_SHIELD_PORT"] == "7979"
    assert d["EnvironmentVariables"]["RAGBASE_SHIELD_HOME"] == str(_home())
    assert d["StandardErrorPath"].startswith(str(_home()))
    assert any(c[1] == "bootstrap" for c in runner.calls)
    assert sm.login_item_enabled()
    sm.disable_login_item()
    assert not path.exists() and not sm.login_item_enabled()


# ------------------------------------------------------------------------------------------ install.json, token


def test_install_json_holds_no_secret_and_no_dossier(tmp_path):
    h = _home()
    (h / "desk_token").write_text("A" * 43 + "\n")
    path = sm.write_install_json(None, Path(sys.executable), "none", h)
    text = path.read_text()
    data = json.loads(text)
    assert data["version"] == __version__ and data["login_item"] == "none"
    assert "A" * 43 not in text
    assert set(data) == {"version", "app_dir", "python", "launcher", "launcher_args", "service_exe", "platform",
                         "machine", "login_item", "installed_at"}
    if os.name == "posix":
        assert (path.stat().st_mode & 0o077) == 0


def test_read_token_reads_only_and_rejects_bad_files():
    h = _home()
    tok = h / "desk_token"
    assert sm.read_token(h) is None and not tok.exists()  # never creates it
    tok.write_bytes(b"short\n")
    assert sm.read_token(h) is None
    tok.write_bytes(b"has space " + b"x" * 40 + b"\n")
    assert sm.read_token(h) is None
    good = "Ab_-" * 10
    tok.write_bytes(good.encode() + b"\nsecond line\n")
    assert sm.read_token(h) == good
    assert tok.read_bytes().startswith(good.encode())  # unchanged


def test_log_filter_masks_token_like_runs(tmp_path):
    lg = sm.setup_logging(_home())
    secret = "Zq" * 20
    lg.info("value %s", secret)
    for hd in lg.handlers:
        hd.flush()
    text = (_home() / "logs" / "service.log").read_text()
    assert secret not in text and "[filtre]" in text
    for hd in list(lg.handlers):  # leave no handler on the shared logger for the next test
        lg.removeHandler(hd)
        hd.close()


# ------------------------------------------------------------------------------------------ supervisor


class _FakeChild:
    def __init__(self):
        self.rc = None
        self.pid = 999999
        self.terminated = False

    def poll(self):
        return self.rc

    def terminate(self):
        self.terminated = True
        self.rc = -15

    def wait(self, timeout=None):
        return self.rc

    def kill(self):
        self.rc = -9


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _sup(answers, clock, spawned):
    def prober(_port, _token):
        return answers[0]

    def spawn(_port, _home):
        c = _FakeChild()
        spawned.append(c)
        return c

    return sm.Supervisor(_home(), 7979, spawn=spawn, prober=prober, clock=clock)


def test_supervisor_backoff_and_give_up():
    clock, spawned = _Clock(), []
    answers = [("refused", None)]
    sup = _sup(answers, clock, spawned)
    sup.tick()
    assert len(spawned) == 1 and sup.state == sm.STARTING
    assert (_home() / "desk.pid").read_text().strip() == "999999"
    delays = []
    for i in range(sm.MAX_EXITS):
        spawned[-1].rc = 1
        sup.tick()  # exit noticed
        if sup.state == sm.GAVE_UP:
            break
        before = len(spawned)
        sup.tick()
        assert len(spawned) == before  # waits for the backoff
        delay = sup._next_action - clock.t
        delays.append(delay)
        clock.t += delay
        sup.tick()
        assert len(spawned) == before + 1
    assert delays == [2.0, 5.0, 15.0, 60.0]
    assert sup.state == sm.GAVE_UP and len(spawned) == sm.MAX_EXITS
    assert not (_home() / "desk.pid").exists()
    sup.request("retry")
    sup.tick()
    assert sup.state == sm.STARTING and len(spawned) == sm.MAX_EXITS + 1


def test_supervisor_ready_then_commands():
    clock, spawned = _Clock(), []
    answers = [("refused", None)]
    sup = _sup(answers, clock, spawned)
    sup.tick()
    answers[0] = ("ok", {"version": __version__, "engine_mode": "rules"})
    sup.tick()
    assert sup.state == sm.RUNNING and sup.snapshot()["engine_mode"] == "rules"
    sm.write_command("restart", _home())
    answers[0] = ("refused", None)
    sup.tick()
    assert spawned[0].terminated and len(spawned) == 2 and sup.state == sm.STARTING
    assert not (_home() / "service.cmd").exists()
    sm.write_command("stop", _home())
    sup.tick()
    assert spawned[1].terminated and sup.stopped.is_set()


def test_supervisor_probe_states():
    clock, spawned = _Clock(), []
    answers = [("ok", {"version": "0.0.9"})]
    sup = _sup(answers, clock, spawned)
    sup.tick()
    assert sup.state == sm.ELSEWHERE and not spawned  # a Desk started from a terminal: no second one
    answers[0] = ("busy", 403)
    clock.t += sm.POLL_STATUS
    sup.tick()
    assert sup.state == sm.PORT_BUSY and not spawned
    clock.t += 1
    sup.tick()
    assert not spawned  # retries every 60 s only
    answers[0] = ("refused", None)
    clock.t += sm.PORT_BUSY_RETRY
    sup.tick()
    assert len(spawned) == 1


def test_probe_against_loopback_servers():
    port = _free_port()
    assert sm.probe(port, None)[0] == "refused"

    class H(http.server.BaseHTTPRequestHandler):
        status = 200

        def do_GET(self):  # noqa: N802
            body = json.dumps({"version": "x", "tok": self.headers.get("X-Shield-Token")}).encode()
            self.send_response(H.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        st, data = sm.probe(srv.server_address[1], "T" * 40)
        assert st == "ok" and data["tok"] == "T" * 40
        H.status = 403
        assert sm.probe(srv.server_address[1], None) == ("busy", 403)
    finally:
        srv.shutdown()


@pytest.mark.skipif(sys.platform == "win32", reason="ps command line check")
def test_stale_desk_pid_is_cleaned(tmp_path):
    sleeper = [sys.executable, "-c", "import time; time.sleep(60)"]
    other = subprocess.Popen(sleeper + ["ragbase_shield", "desk"])  # not a Desk child: must survive
    orphan = subprocess.Popen(sleeper + ["-m", "ragbase_shield", "desk", "--service"])  # looks like one
    try:
        (_home() / "desk.pid").write_text(f"{other.pid}\n")
        assert sm.kill_stale_desk(_home()) is False
        assert other.poll() is None and not (_home() / "desk.pid").exists()
        (_home() / "desk.pid").write_text(f"{orphan.pid}\n")
        assert sm.kill_stale_desk(_home()) is True
        assert orphan.wait(timeout=10) is not None
    finally:
        for p in (other, orphan):
            if p.poll() is None:
                p.kill()
            p.wait()


# ------------------------------------------------------------------------------------------ real child


def test_service_run_serves_desk_and_never_logs_the_token(monkeypatch):
    port = _free_port()
    monkeypatch.setenv("RAGBASE_SHIELD_PORT", str(port))
    h = _home()
    env = dict(os.environ)
    proc = subprocess.Popen([sys.executable, "-m", "ragbase_shield", "service", "run", "--no-tray",
                             "--for-seconds", "40"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 35
        st = None
        while time.monotonic() < deadline:
            st, info = sm.probe(port, sm.read_token(h))
            if st == "ok":
                break
            time.sleep(0.3)
        assert st == "ok", "Desk did not answer"
        assert info["version"] == __version__
        assert sm.probe(port, None) == ("busy", 401)  # no token header: refused by the Desk
        assert (h / "service.pid").exists() and (h / "desk.pid").exists()
        ok, lines = sm.status_lines()
        assert ok and any("actif" in line for line in lines)
        assert sm.stop(wait=15)
        proc.wait(timeout=20)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        sm.kill_stale_desk(h)
    out, err = proc.communicate()
    token = (h / "desk_token").read_text().strip()
    assert token
    for f in (h / "logs").iterdir():
        assert token not in f.read_text(errors="replace")
    assert token.encode() not in out + err
    assert not (h / "desk.pid").exists()


def test_desk_service_flag_hides_token_and_browser(monkeypatch):
    import importlib

    desk_app = importlib.import_module("ragbase_shield.desk.app")
    seen = {}

    def fake_serve(port, open_browser, show_token):
        seen.update(port=port, open_browser=open_browser, show_token=show_token)
        return 0

    monkeypatch.setattr(desk_app, "serve", fake_serve)
    assert cli.main(["desk", "--service", "--port", "7990"]) == 0
    assert seen == {"port": 7990, "open_browser": False, "show_token": False}


# ------------------------------------------------------------------------------------------ cli surfaces


def _fake_install(tmp_path) -> Path:
    launcher = tmp_path / "app" / "bin" / "ragbase-shield"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(f"#!/bin/sh\nexec {sys.executable} -m ragbase_shield \"$@\"\n")
    launcher.chmod(0o755)
    data = {"version": __version__, "app_dir": str(tmp_path / "app"), "launcher": str(launcher),
            "launcher_args": [], "login_item": "none"}
    (_home() / "install.json").write_text(json.dumps(data))
    return launcher


@pytest.mark.skipif(sys.platform == "win32", reason="sh launcher")
def test_server_command_prefers_installed_launcher(tmp_path):
    launcher = _fake_install(tmp_path)
    assert cli.server_command() == (str(launcher), ["mcp"])
    (_home() / "install.json").unlink()
    assert cli.server_command()[0] != str(launcher)


@pytest.mark.skipif(sys.platform == "win32", reason="sh launcher")
def test_doctor_shows_installer_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_PORT", str(_free_port()))
    _fake_install(tmp_path)
    labels = {label: (status, detail) for status, label, detail in cli.doctor_checks()}
    assert labels["Installateur"][0] == "OK"
    assert labels["Service Shield Desk"][0] == "WARN"  # nothing listens on that port
    assert labels["uv / uvx"][0] in ("OK", "INFO")


def test_service_install_refused_in_agent_shell(monkeypatch, capsys):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert cli.main(["service", "install", "--no-start", "--no-login-item"]) == 3
    assert not (_home() / "install.json").exists()
    assert cli.main(["service", "status"]) in (0, 1)  # status stays allowed


def test_service_install_without_login_item(tmp_path, monkeypatch, capsys):
    # uninstall boots out the launchd job and deletes ~/Library/LaunchAgents/ai.ragbase.shield.plist: keep
    # both away from the real account (a real install on this Mac must survive the test suite).
    monkeypatch.setenv("HOME", str(tmp_path / "userhome"))
    calls = []
    monkeypatch.setattr(sm, "launchd_bootout", lambda runner=None: calls.append("bootout") or True)
    assert cli.main(["service", "install", "--no-start", "--no-login-item", "--quiet"]) == 0
    data = json.loads((_home() / "install.json").read_text())
    assert data["login_item"] == "none" and data["version"] == __version__
    assert cli.main(["service", "uninstall", "--quiet"]) == 0
    assert not (_home() / "install.json").exists()


# ------------------------------------------------------------------------------------------ tray strings


def test_tray_strings_have_no_dashes_and_match():
    for lang, table in tray.STRINGS.items():
        assert set(table) == set(tray.STRINGS["fr"]), lang
        for s in table.values():
            assert "\u2014" not in s and "\u2013" not in s


def test_status_text(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_UI", "fr")
    snap = {"state": sm.RUNNING, "port": 7878, "version": "0.4.4", "engine_mode": "rules+ner:fastino"}
    assert tray.status_text(snap) == "Shield Desk : en marche, port 7878, v0.4.4, règles + NER"
    assert tray.status_text({"state": sm.PORT_BUSY, "port": 7878}) == \
        "Shield Desk : port 7878 occupé par un autre programme"
    monkeypatch.setenv("RAGBASE_SHIELD_UI", "en")
    assert tray.status_text({"state": sm.GAVE_UP, "port": 7878}) == "Shield Desk: stopped, see the log"


def test_app_dir_only_for_an_installer_folder(tmp_path, monkeypatch):
    for name, expected in (("payload-x86_64", False), ("RAGbase Shield", True)):
        rt = tmp_path / name / "runtime"
        rt.mkdir(parents=True)
        (tmp_path / name / "VERSION").write_text(__version__)
        monkeypatch.setattr(sys, "base_prefix", str(rt))
        assert (sm.app_dir() == (tmp_path / name).resolve()) is expected
