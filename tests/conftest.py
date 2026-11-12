"""Test isolation: temp data dir, file key (never the OS keychain), no outbound network."""
import os
import socket

import pytest


@pytest.fixture(autouse=True)
def _shield_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_HOME", str(tmp_path / "shield-home"))
    monkeypatch.setenv("RAGBASE_SHIELD_KEYRING", "0")
    # The models of the machine are not part of a test: a run with RAGBASE_SHIELD_MODELS_DIR set behaves like one
    # with the models in the default data folder (moved above). Tests that need a model ask for it (real_models).
    monkeypatch.delenv("RAGBASE_SHIELD_MODELS_DIR", raising=False)
    # Windows: the per-user folders (Claude Desktop settings, the default data folder) are temporary too, so no
    # test can write into the real profile of the user who runs the tests.
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata-roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata-local"))
    yield


_real_connect = socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host in ("127.0.0.1", "localhost", "::1"):
        return _real_connect(self, address)
    if self.family == getattr(socket, "AF_UNIX", None):
        return _real_connect(self, address)
    raise RuntimeError(f"RAGbase Shield tests must not open network connections (tried {address!r})")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    yield
