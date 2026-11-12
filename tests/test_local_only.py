"""Local only: library code holds no network client, and the test run blocks outbound sockets."""
from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

import ragbase_shield

# The code of the package that runs (a source tree or an installed wheel).
SRC = Path(ragbase_shield.__file__).resolve().parent

# Modules that open outbound connections. None of them may be imported by library code.
NETWORK_MODULES = {"urllib", "http", "requests", "httpx", "httpx2", "aiohttp", "smtplib", "ftplib",
                   "poplib", "imaplib", "telnetlib", "xmlrpc", "websocket", "websockets"}
# socket is allowed only to bind the Desk port (desk/app.py) and to check that it is free (cli.py doctor).
SOCKET_ALLOWED = {"cli.py", "app.py"}
# The background service asks the local Desk for its status (packaging/DESIGN.md section 4): http.client is
# allowed in desk/loopback.py only, whose host is the constant 127.0.0.1 (checked below).
LOOPBACK_CLIENT = "loopback.py"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def _calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}


@pytest.mark.parametrize("path", sorted(SRC.rglob("*.py")), ids=lambda p: str(p.relative_to(SRC)))
def test_library_has_no_network_client(path):
    allowed = {"http"} if path.name == LOOPBACK_CLIENT and path.parent.name == "desk" else set()
    assert not ((_imports(path) - allowed) & NETWORK_MODULES), f"{path.name} imports a network client"
    if "socket" in _imports(path):
        assert path.name in SOCKET_ALLOWED, f"{path.name} imports socket"
        assert not ({"connect", "connect_ex", "create_connection", "sendto"} & _calls(path))


def test_cli_socket_use_is_local_only():
    text = (SRC / "cli.py").read_text(encoding="utf-8")
    for call in ("create_connection", "sendto", "getaddrinfo"):
        assert f"socket.{call}" not in text


def test_outbound_sockets_are_blocked_during_tests():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="must not open network connections"):
            s.connect(("192.0.2.1", 443))  # TEST-NET-1: never routed
    finally:
        s.close()


def test_loopback_client_targets_127_0_0_1_only():
    text = (SRC / "desk" / LOOPBACK_CLIENT).read_text(encoding="utf-8")
    assert 'LOOPBACK = "127.0.0.1"' in text
    assert text.count("HTTPConnection(") == 1 and "HTTPConnection(LOOPBACK," in text
    assert "HTTPSConnection" not in text and "getaddrinfo" not in text and "socket" not in _imports(SRC / "desk" /
                                                                                                    LOOPBACK_CLIENT)
