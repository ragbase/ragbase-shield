"""Shield Desk server (ARCHITECTURE.md sections 4.7 and 6), driven with starlette.testclient.

Checks: the token file, the token on every /api route, the Host check (DNS rebinding, other ports), the
Origin check and CORS (extension origins only, only with a valid token), security headers, body limits,
every endpoint on a temporary dossier made of synthetic files, the mask/restore round trip, file uploads
(masking, no path traversal, temp files removed), French JSON errors without stack traces or values, the
journal (codes and counts only), serve() (127.0.0.1 only, token never printed to an agent) and the CLI.

Synthetic data only: every name below is invented.
"""
from __future__ import annotations

import io
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from ragbase_shield import cli, config, service
from ragbase_shield.desk import app as desk

PORT = 7878
BASE = f"http://127.0.0.1:{PORT}"
TOKEN = "desk-test-token-" + "a1b2c3d4" * 4
H = {"X-Shield-Token": TOKEN}
EXT = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
MOZ = "moz-extension://0b3c3d4e-1111-4a5b-9c8d-123456789abc"


def iban_fr(bban: str) -> str:
    """A French IBAN with valid ISO 13616 check digits (computed, not copied)."""
    digits = "".join(str(int(c, 36)) for c in bban + "FR00")
    return f"FR{98 - int(digits) % 97:02d}{bban}"


IBAN = iban_fr("30004000031234567890143")
LAWYER = "Hélène Morvandiau-Lescaut"
CLIENT = "Quentin Ferracci-Daubel"
COMPANY = "Brivanor Conseil"
EMAIL = "q.ferracci@brivanor-conseil.fr"
TITLE = "Ferracci-Daubel c. Brivanor Conseil SAS"
TEXT = (f"Maître {LAWYER}, avocate de M. {CLIENT},\n"
        f"contre la société {COMPANY} SAS. Courriel : {EMAIL}\n"
        f"IBAN {IBAN}. Tribunal judiciaire de Paris, Code du travail article L1234-9.\n")
REAL = (LAWYER, "Morvandiau", CLIENT, "Ferracci", COMPANY, "Brivanor", EMAIL, IBAN)


def leaked(payload) -> list[str]:
    """Real values present in a payload (JSON-serialised, case-insensitive)."""
    blob = json.dumps(payload, ensure_ascii=False).lower() if not isinstance(payload, str) else payload.lower()
    return [v for v in REAL if v.lower() in blob]


@pytest.fixture(autouse=True)
def _fresh_service(monkeypatch):
    for name in cli._AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    service.reset()
    yield
    service.reset()


@pytest.fixture
def client():
    app = desk.create_app(port=PORT, token=TOKEN)
    with TestClient(app, base_url=BASE) as c:
        yield c


@pytest.fixture
def folder(tmp_path) -> Path:
    from docx import Document

    f = tmp_path / "Dossier Ferracci-Daubel"
    f.mkdir()
    (f / "assignation.txt").write_text(TEXT, encoding="utf-8")
    (f / "notes.md").write_text(f"# Notes\n\nRendez-vous avec M. {CLIENT} le 3 mars.\n", encoding="utf-8")
    doc = Document()
    doc.add_paragraph(f"Courrier de Maître {LAWYER} à la société {COMPANY} SAS.")
    doc.save(str(f / "courrier.docx"))
    return f


@pytest.fixture
def dossier(client, folder) -> str:
    r = client.post("/api/dossiers", json={"folder": str(folder), "title": TITLE}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()["code"]


# ---------------------------------------------------------------------------------------------- token file

def test_token_file_is_created_0600_and_reused():
    path = config.home() / "desk_token"
    assert not path.exists()
    t1 = desk.load_or_create_token()
    assert path.is_file() and len(t1) >= 32
    if not sys.platform.startswith("win"):
        assert path.stat().st_mode & 0o777 == 0o600
    assert desk.load_or_create_token() == t1
    desk.create_app(port=PORT)  # token=None reads the same file
    assert path.read_text(encoding="ascii").strip() == t1


def test_damaged_token_file_is_replaced():
    path = config.home() / "desk_token"
    path.write_text("short", encoding="ascii")
    os.chmod(path, 0o600)
    t = desk.load_or_create_token()
    assert t != "short" and len(t) >= 32 and path.read_text(encoding="ascii").strip() == t


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_token_readable_by_others_is_rotated():
    t1 = desk.load_or_create_token()
    path = config.home() / "desk_token"
    os.chmod(path, 0o644)
    t2 = desk.load_or_create_token()
    assert t2 != t1 and path.stat().st_mode & 0o777 == 0o600


def test_create_app_refuses_a_weak_token_or_port():
    with pytest.raises(ValueError):
        desk.create_app(port=PORT, token="short")
    with pytest.raises(ValueError):
        desk.create_app(port=0, token=TOKEN)
    app = desk.create_app(port=PORT, token=TOKEN)
    assert TOKEN not in repr(app.user_middleware)


def test_token_is_required_on_every_api_route(client):
    for method, path in (("GET", "/api/status"), ("GET", "/api/dossiers"), ("POST", "/api/dossiers"),
                         ("DELETE", "/api/dossiers/DOSSIER_1"), ("GET", "/api/dossiers/DOSSIER_1/entities"),
                         ("POST", "/api/dossiers/DOSSIER_1/keep-clear"), ("POST", "/api/dossiers/DOSSIER_1/scan"),
                         ("POST", "/api/mask"), ("POST", "/api/restore"), ("POST", "/api/files"),
                         ("GET", "/api/journal"), ("GET", "/api/nothing-here")):
        r = client.request(method, path)
        assert r.status_code == 401, (method, path, r.status_code)
        assert r.json()["error"].startswith("Le jeton est manquant ou invalide")
        r = client.request(method, path, headers={"X-Shield-Token": "wrong-" + TOKEN})
        assert r.status_code == 403, (method, path, r.status_code)


def test_token_in_the_query_string_is_not_accepted_by_the_api(client):
    assert client.get(f"/api/status?t={TOKEN}").status_code == 401
    r = client.get("/api/status", headers=H)
    assert r.status_code == 200 and r.json()["version"]
    assert TOKEN not in r.text


def test_page_and_static_files_load_without_the_token(client):
    r = client.get(f"/?t={TOKEN}")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "/static/app.js" in r.text and TOKEN not in r.text
    assert client.get("/").status_code == 200  # a reload after the page removed ?t=
    r = client.get("/static/app.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert client.get("/static/style.css").status_code == 200


# ---------------------------------------------------------------------------------------------- host

@pytest.mark.parametrize("host", ["evil.example", "evil.example:7878", "shield.attacker.test:7878",
                                  "127.0.0.1", "127.0.0.1:9999", "localhost:80", "[::1]:7878", "0.0.0.0:7878",
                                  "127.0.0.1:7878.evil.example", ""])
def test_foreign_host_is_rejected_everywhere(client, host):
    for path in ("/", "/static/app.js", "/api/status", "/api/dossiers"):
        r = client.get(path, headers={**H, "Host": host})
        assert r.status_code == 403, (host, path)
        assert r.json()["code"] == "bad_host"


def test_localhost_host_is_accepted(client):
    assert client.get("/api/status", headers={**H, "Host": "localhost:7878"}).status_code == 200
    assert client.get("/api/status", headers={**H, "Host": "LOCALHOST:7878"}).status_code == 200


# ---------------------------------------------------------------------------------------------- origin and CORS

def test_web_origin_is_refused_even_with_the_token(client):
    for origin in ("https://evil.example", "null", "http://127.0.0.1:3000", "https://chatgpt.com",
                   "chrome-extension://", "chrome-extension://abc/x"):
        r = client.get("/api/status", headers={**H, "Origin": origin})
        assert r.status_code == 403, origin
        assert "access-control-allow-origin" not in r.headers
    r = client.post("/api/mask", json={"text": TEXT}, headers={**H, "Origin": "https://evil.example"})
    assert r.status_code == 403 and "access-control-allow-origin" not in r.headers
    assert not leaked(r.json())


def test_cross_site_fetch_metadata_is_refused(client):
    r = client.get("/api/status", headers={**H, "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


def test_preflight_for_extensions_only(client):
    for origin in (EXT, MOZ):
        r = client.options("/api/mask", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                 "Access-Control-Request-Headers": "content-type,x-shield-token"})
        assert r.status_code == 204, origin
        assert r.headers["access-control-allow-origin"] == origin
        assert "X-Shield-Token" in r.headers["access-control-allow-headers"]
        assert "access-control-allow-credentials" not in r.headers
    r = client.options("/api/mask", headers={"Origin": EXT, "Access-Control-Request-Method": "POST",
                                             "Access-Control-Request-Private-Network": "true"})
    assert r.headers["access-control-allow-private-network"] == "true"
    for origin in ("https://evil.example", "http://127.0.0.1:3000", "null"):
        r = client.options("/api/mask", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert r.status_code == 403
        assert "access-control-allow-origin" not in r.headers


def test_cors_header_only_with_a_valid_token(client):
    r = client.get("/api/status", headers={**H, "Origin": EXT})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == EXT
    assert "Origin" in r.headers["vary"]
    r = client.get("/api/status", headers={"Origin": EXT})
    assert r.status_code == 401 and "access-control-allow-origin" not in r.headers
    r = client.get("/api/status", headers={"Origin": EXT, "X-Shield-Token": "bad-" + TOKEN})
    assert r.status_code == 403 and "access-control-allow-origin" not in r.headers
    # the Desk page itself: same origin, no CORS header needed
    r = client.get("/api/status", headers={**H, "Origin": BASE})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


# ---------------------------------------------------------------------------------------------- headers

def test_security_headers(client):
    for path, headers in (("/", {}), ("/static/app.js", {}), ("/api/status", H), ("/api/nothing", H)):
        r = client.get(path, headers=headers)
        csp = r.headers["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp, path
        assert "script-src 'self'" in csp and "unsafe-inline" not in csp
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
    assert client.get("/api/status", headers=H).headers["cache-control"] == "no-store"


def test_websocket_is_refused(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/status", headers=H):
            pass


def test_static_folder_cannot_be_escaped(client):
    for path in ("/static/%2e%2e/app.py", "/static/..%2fapp.py", "/static/../app.py", "/static/%2e%2e/__init__.py"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert "def create_app" not in r.text and "import" not in r.text


# ---------------------------------------------------------------------------------------------- errors

def test_errors_are_french_json(client):
    r = client.get("/nothing-here")
    assert r.status_code == 404 and r.json() == {"error": "Adresse inconnue sur Shield Desk.", "code": "not_found"}
    r = client.get("/api/mask", headers=H)
    assert r.status_code == 405 and r.json()["code"] == "method_not_allowed"
    r = client.post("/api/mask", content=b"{not json", headers={**H, "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["error"] == "Corps JSON invalide."
    r = client.post("/api/mask", content=b"[1, 2]", headers={**H, "Content-Type": "application/json"})
    assert r.status_code == 400
    r = client.post("/api/mask", data={"text": "x"}, headers=H)
    assert r.status_code == 415
    r = client.post("/api/mask", json={"text": 12}, headers=H)
    assert r.status_code == 400 and "text" in r.json()["error"]
    r = client.post("/api/mask", json={}, headers=H)
    assert r.status_code == 400 and r.json()["code"] == "missing_field"
    r = client.post("/api/mask", json={"text": "x", "dossier": "Ferracci"}, headers=H)
    assert r.status_code == 400 and r.json()["code"] == "invalid_dossier"
    r = client.post("/api/mask", json={"text": "x", "dossier": "DOSSIER_42"}, headers=H)
    assert r.status_code == 404 and r.json()["code"] == "unknown_dossier"
    for resp in (r,):
        assert "Traceback" not in resp.text


def test_internal_error_has_no_stack_trace_and_no_value(client, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError(f"secret {CLIENT} {IBAN}")

    monkeypatch.setattr(service, "mask_text", boom)
    r = client.post("/api/mask", json={"text": TEXT}, headers=H)
    assert r.status_code == 500 and r.json()["code"] == "internal"
    assert r.json()["error"].startswith("Erreur interne de Shield Desk")
    assert "Traceback" not in r.text and not leaked(r.text) and "RuntimeError" not in r.text
    assert not leaked(caplog.text)


def test_shield_error_maps_to_status(client, monkeypatch):
    def broken(*a, **k):
        raise service.ShieldError("Coffre RAGbase Shield illisible ou clé absente (vault error, ref 1).",
                                  "vault_error")

    monkeypatch.setattr(service, "list_dossiers", broken)
    r = client.get("/api/dossiers", headers=H)
    assert r.status_code == 500 and r.json()["code"] == "vault_error"


# ---------------------------------------------------------------------------------------------- body limits

def test_json_body_limit(client, monkeypatch):
    monkeypatch.setattr(desk, "MAX_JSON_BYTES", 2000)
    r = client.post("/api/mask", json={"text": "a" * 5000}, headers=H)
    assert r.status_code == 413 and r.json()["code"] == "too_large"

    def chunks():  # no Content-Length: the counting receive must stop it
        yield b'{"text": "'
        for _ in range(10):
            yield b"b" * 500
        yield b'"}'

    r = client.post("/api/mask", content=chunks(), headers={**H, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_bad_content_length(client):
    r = client.post("/api/mask", content=b"{}", headers={**H, "Content-Type": "application/json",
                                                         "Content-Length": "-1"})
    assert r.status_code in (400, 413)


# ---------------------------------------------------------------------------------------------- dossiers

def test_status(client):
    r = client.get("/api/status", headers=H)
    st = r.json()
    assert st["version"] and st["network"] is False and st["limits"]


def test_dossier_add_list_entities_register_keep_clear_scan_remove(client, folder):
    r = client.post("/api/dossiers", json={"folder": str(folder), "title": TITLE}, headers=H)
    assert r.status_code == 201
    created = r.json()
    assert created["code"] == "DOSSIER_1" and created["documents"] == 3 and created["entities"] >= 4
    assert created["title"] == TITLE and Path(created["folder"]) == folder.resolve()

    rows = client.get("/api/dossiers", headers=H).json()
    assert [d["code"] for d in rows] == ["DOSSIER_1"]
    assert rows[0]["title"] == TITLE and rows[0]["documents"] == 3

    ents = client.get("/api/dossiers/DOSSIER_1/entities", headers=H).json()
    values = {e["value"] for e in ents}
    assert {LAWYER, CLIENT, EMAIL, IBAN} <= values
    assert all(set(e) >= {"code", "kind", "value", "kept_clear"} for e in ents)

    r = client.post("/api/dossiers/DOSSIER_1/entities", json={"kind": "PERSON", "value": "Capucine Lombardi-Vasseur"},
                    headers=H)
    assert r.status_code == 201 and r.json()["code"].startswith("PERSONNE_")
    new_code = r.json()["code"]
    masked = client.post("/api/mask", json={"text": "Réunion avec Capucine Lombardi-Vasseur.", "dossier": "DOSSIER_1"},
                         headers=H).json()["masked"]
    assert new_code in masked and "Lombardi" not in masked
    assert client.post("/api/dossiers/DOSSIER_1/entities", json={"kind": "PLANET", "value": "x"},
                       headers=H).status_code == 400
    assert client.post("/api/dossiers/DOSSIER_1/entities", json={"kind": "PERSON", "value": "  "},
                       headers=H).status_code == 400

    org = next(e["code"] for e in ents if e["kind"] == "ORG")
    r = client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"code": org, "value": True}, headers=H)
    assert r.status_code == 200 and r.json() == {"ok": True}
    ents = client.get("/api/dossiers/DOSSIER_1/entities", headers=H).json()
    assert next(e for e in ents if e["code"] == org)["kept_clear"] is True
    masked = client.post("/api/mask", json={"text": TEXT, "dossier": "DOSSIER_1"}, headers=H).json()["masked"]
    assert COMPANY in masked and CLIENT not in masked
    assert client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"code": org, "value": False},
                       headers=H).status_code == 200
    assert client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"code": org, "value": "yes"},
                       headers=H).status_code == 400
    assert client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"code": "PERSONNE_ZZ"},
                       headers=H).status_code == 400
    assert client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"term": "Paris"}, headers=H).status_code == 200

    r = client.post("/api/dossiers/DOSSIER_1/scan", headers=H)
    assert r.status_code == 200
    scan = r.json()
    assert scan["code"] == "DOSSIER_1" and scan["documents"] == 3 and scan["counts"]["PERSON"] >= 2
    assert not leaked(scan)

    assert client.delete("/api/dossiers/DOSSIER_1", headers=H).json() == {"ok": True}
    assert client.get("/api/dossiers", headers=H).json() == []
    r = client.get("/api/dossiers/DOSSIER_1/entities", headers=H)
    assert r.status_code == 404 and r.json()["code"] == "unknown_dossier"
    assert client.delete("/api/dossiers/DOSSIER_1", headers=H).status_code == 404
    assert client.delete("/api/dossiers/not-a-code", headers=H).status_code == 400


def test_add_dossier_checks_the_folder(client, tmp_path, folder):
    some_file = folder / "assignation.txt"
    cases = {
        "": "missing_field",
        "relative/path": "invalid_folder",
        str(tmp_path / "does-not-exist"): "folder_not_found",
        str(some_file): "not_a_folder",
        Path.home().anchor: "folder_too_wide",  # the root: "/" on Mac and Linux, the drive "C:\\" on Windows
        str(Path.home()): "folder_too_wide",
        str(config.home()): "folder_too_wide",
        str(config.home() / "vaults"): "folder_too_wide",
    }
    (config.home() / "vaults").mkdir(exist_ok=True)
    for raw, code in cases.items():
        r = client.post("/api/dossiers", json={"folder": raw}, headers=H)
        assert r.status_code == 400, raw
        assert r.json()["code"] == code, (raw, r.json())
        assert raw == "" or raw not in r.json()["error"]  # the message never repeats the path
    assert client.post("/api/dossiers", json={"folder": 12}, headers=H).status_code == 400
    assert client.post("/api/dossiers", json={"folder": str(folder), "title": "x" * 500},
                       headers=H).status_code == 400
    # a quoted path (copied from Windows Explorer) is accepted
    r = client.post("/api/dossiers", json={"folder": f'"{folder}"'}, headers=H)
    assert r.status_code == 201 and r.json()["code"] == "DOSSIER_1"
    assert client.get("/api/dossiers", headers=H).json()[0]["title"] == folder.name


# ---------------------------------------------------------------------------------------------- mask / restore

def test_mask_and_restore_round_trip(client, dossier):
    r = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H)
    assert r.status_code == 200
    res = r.json()
    assert not leaked(res["masked"])
    assert "Tribunal judiciaire de Paris" in res["masked"] and "L1234-9" in res["masked"]
    codes = {f["code"] for f in res["found"]}
    assert {f["kind"] for f in res["found"]} >= {"PERSON", "ORG", "EMAIL", "IBAN"}
    assert all(c in res["masked"] for c in codes)
    assert {f["value"] for f in res["found"]} >= {LAWYER, CLIENT}  # the Desk page shows values for review
    assert res["counts"]["PERSON"] == 2

    answer = res["masked"] + "\nVoir aussi PERSONNE_ZZ."
    r = client.post("/api/restore", json={"text": answer, "dossier": dossier}, headers=H)
    assert r.status_code == 200
    back = r.json()
    assert back["text"] == TEXT + "\nVoir aussi PERSONNE_ZZ."
    assert back["unknown_codes"] == ["PERSONNE_ZZ"] and back["restored"] == len(codes)

    # the same dossier gives the same codes on every call
    again = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H).json()
    assert again["masked"] == res["masked"]


def test_mask_without_dossier_uses_a_temporary_store(client):
    r = client.post("/api/mask", json={"text": TEXT}, headers=H)
    assert r.status_code == 200
    res = r.json()
    assert not leaked(res["masked"]) and "PERSONNE_A" in res["masked"]
    assert client.get("/api/dossiers", headers=H).json() == []


def test_extension_gets_least_privilege(client, dossier, tmp_path):
    """An extension origin may read the status and the dossier codes and titles, mask and restore; nothing else."""
    xh = {**H, "Origin": EXT}
    rows = client.get("/api/dossiers", headers=xh).json()
    assert rows and all("folder" not in r for r in rows) and all("title" in r for r in rows)
    assert all("folder" in r for r in client.get("/api/dossiers", headers=H).json())  # the Desk page still has it
    for method, path, kw in (("get", f"/api/dossiers/{dossier}/entities", {}),
                             ("post", f"/api/dossiers/{dossier}/entities", {"json": {"kind": "PERSON", "value": "X Y"}}),
                             ("post", f"/api/dossiers/{dossier}/keep-clear", {"json": {"code": "PERSONNE_A"}}),
                             ("post", f"/api/dossiers/{dossier}/scan", {}),
                             ("get", "/api/journal", {}),
                             ("post", "/api/dossiers", {"json": {"folder": str(tmp_path)}}),
                             ("delete", f"/api/dossiers/{dossier}", {})):
        r = getattr(client, method)(path, headers=xh, **kw)
        assert r.status_code == 403 and r.json()["code"] == "extension_forbidden", (method, path)
        assert not leaked(r.json())
    r = client.post("/api/files", files={"files": ("a.txt", TEXT.encode(), "text/plain")}, headers=xh)
    assert r.status_code == 403
    assert client.get("/api/status", headers=xh).status_code == 200
    assert client.post("/api/restore", json={"text": "PERSONNE_A", "dossier": dossier}, headers=xh).status_code == 200
    assert client.get(f"/api/dossiers/{dossier}/entities", headers=H).status_code == 200  # the page keeps it


def test_mask_from_an_extension_returns_no_value(client, dossier):
    r = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers={**H, "Origin": EXT})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == EXT
    res = r.json()
    assert res["found"] and all("value" not in f for f in res["found"])
    assert not leaked(res)
    r = client.post("/api/mask", json={"text": TEXT}, headers={**H, "Origin": MOZ})
    assert r.status_code == 200 and not leaked(r.json())


def test_restore_needs_a_dossier(client, dossier):
    r = client.post("/api/restore", json={"text": "PERSONNE_A"}, headers=H)
    assert r.status_code == 400 and r.json()["code"] == "missing_dossier"
    r = client.post("/api/restore", json={"text": "PERSONNE_A", "dossier": ""}, headers=H)
    assert r.status_code == 400
    r = client.post("/api/restore", json={"dossier": dossier}, headers=H)
    assert r.status_code == 400


# ---------------------------------------------------------------------------------------------- files

def _upload_root() -> Path:
    return config.home() / desk.UPLOAD_DIR


def test_files_upload_masks_each_file(client, dossier, folder):
    files = [
        ("files", (f"{CLIENT} - assignation.txt", TEXT.encode("utf-8"), "text/plain")),
        ("files", ("courrier.docx", (folder / "courrier.docx").read_bytes(),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("vide.md", b"", "text/markdown")),
    ]
    r = client.post("/api/files", files=files, data={"dossier": dossier}, headers=H)
    assert r.status_code == 200, r.text
    items = r.json()
    assert [i["name"] for i in items] == [f"{CLIENT} - assignation.txt", "courrier.docx", "vide.md"]
    assert all("error" not in i for i in items)
    shown = [{"masked_name": i["masked_name"], "masked_text": i["masked_text"]} for i in items]
    assert not leaked(shown)
    assert items[0]["masked_name"].endswith(" - assignation.txt") and "PERSONNE_" in items[0]["masked_name"]
    assert "Tribunal judiciaire de Paris" in items[0]["masked_text"]
    assert "PERSONNE_A" in items[1]["masked_text"] and "SOCIETE_A" in items[1]["masked_text"]
    assert items[2]["masked_text"] == ""
    # same codes as the dossier
    masked = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H).json()["masked"]
    assert items[0]["masked_text"] == masked.rstrip("\n")
    assert not any(_upload_root().iterdir())  # temp files are gone


def test_files_without_dossier(client):
    r = client.post("/api/files", files={"files": ("a.txt", TEXT.encode(), "text/plain")}, headers=H)
    assert r.status_code == 200
    item = r.json()[0]
    assert not leaked(item["masked_text"]) and "PERSONNE_A" in item["masked_text"]


def test_files_upload_has_no_path_traversal(client, tmp_path):
    root = _upload_root()
    names = ["../../outside.txt", "..\\..\\win-outside.txt", "/etc/passwd.txt", "sub/dir/inner.md", "..", "  "]
    files = [("files", (n, TEXT.encode(), "text/plain")) for n in names]
    r = client.post("/api/files", files=files, headers=H)
    assert r.status_code == 200
    items = r.json()
    assert [i["name"] for i in items] == ["outside.txt", "win-outside.txt", "passwd.txt", "inner.md",
                                          "document", "document"]
    assert [bool(i.get("error")) for i in items] == [False, False, False, False, True, True]
    for p in (root.parent / "outside.txt", root.parent.parent / "outside.txt", tmp_path / "outside.txt",
              config.home() / "win-outside.txt"):
        assert not p.exists()
    assert not any(root.iterdir())


def test_files_errors_per_item_and_limits(client, monkeypatch):
    files = [("files", ("tool.exe", b"MZ\x00\x00", "application/octet-stream")),
             ("files", ("broken.docx", b"this is not a zip", "application/octet-stream")),
             ("files", ("big.txt", b"x" * 300, "text/plain")),
             ("files", ("ok.txt", b"Bonjour.", "text/plain"))]
    monkeypatch.setattr(desk, "MAX_FILE_BYTES", 200)
    r = client.post("/api/files", files=files, headers=H)
    assert r.status_code == 200
    items = r.json()
    assert items[0]["error"].startswith("Format non pris en charge")
    assert items[1]["error"].startswith("Fichier illisible")
    assert items[2]["error"].startswith("Fichier trop volumineux")
    assert "error" not in items[3] and items[3]["masked_text"] == "Bonjour."
    assert "Traceback" not in r.text

    many = [("files", (f"f{i}.txt", b"x", "text/plain")) for i in range(desk.MAX_FILES_PER_REQUEST + 1)]
    r = client.post("/api/files", files=many, headers=H)
    assert r.status_code == 400 and r.json()["code"] == "bad_upload"

    monkeypatch.setattr(desk, "MAX_UPLOAD_BYTES", 1000)
    r = client.post("/api/files", files={"files": ("a.txt", b"y" * 5000, "text/plain")}, headers=H)
    assert r.status_code == 413 and "25 Mo" in r.json()["error"]


def test_files_request_checks(client):
    assert client.post("/api/files", json={"files": []}, headers=H).status_code == 415
    r = client.post("/api/files", files={"other": ("a.txt", b"x", "text/plain")}, headers=H)
    assert r.status_code == 400 and r.json()["code"] == "no_files"
    r = client.post("/api/files", files={"files": ("a.txt", b"x", "text/plain")}, data={"dossier": "DOSSIER_9"},
                    headers=H)
    assert r.status_code == 404 and r.json()["code"] == "unknown_dossier"
    r = client.post("/api/files", files={"files": ("a.txt", b"x", "text/plain")}, data={"dossier": "../x"},
                    headers=H)
    assert r.status_code == 400


# ---------------------------------------------------------------------------------------------- journal

def test_journal_has_codes_and_counts_only(client, dossier, folder):
    client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H)
    client.post("/api/mask", json={"text": TEXT}, headers=H)
    masked = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H).json()["masked"]
    client.post("/api/restore", json={"text": masked, "dossier": dossier}, headers=H)
    client.post("/api/dossiers/DOSSIER_1/entities", json={"kind": "PERSON", "value": "Capucine Lombardi-Vasseur"},
                headers=H)
    client.post("/api/dossiers/DOSSIER_1/keep-clear", json={"term": "Brivanor"}, headers=H)
    client.post("/api/files", files={"files": (f"{CLIENT}.txt", TEXT.encode(), "text/plain")},
                data={"dossier": dossier}, headers=H)
    client.post("/api/dossiers/DOSSIER_1/scan", headers=H)

    r = client.get("/api/journal", headers=H)
    assert r.status_code == 200
    rows = r.json()
    events = {row["event"] for row in rows}
    assert {"dossier_added", "add_dossier", "mask", "restore", "register", "keep_clear", "files", "scan"} <= events
    assert all(set(row) == {"time", "event", "dossier", "counts"} for row in rows)
    blob = json.dumps(rows, ensure_ascii=False)
    assert not leaked(blob)
    for private in (TITLE, str(folder), folder.name, "Lombardi", "Capucine", TOKEN):
        assert private not in blob

    only = client.get(f"/api/journal?dossier={dossier}&limit=3", headers=H).json()
    assert len(only) == 3 and all(row["dossier"] == dossier for row in only)
    assert client.get("/api/journal?dossier=Ferracci", headers=H).status_code == 400
    assert client.get("/api/journal?limit=0", headers=H).status_code == 400
    assert client.get("/api/journal?limit=abc", headers=H).status_code == 400

    client.delete(f"/api/dossiers/{dossier}", headers=H)
    rows = client.get("/api/journal", headers=H).json()
    assert any(row["event"] == "dossier_removed" for row in rows)


# ---------------------------------------------------------------------------------------------- verify paths

def test_verify_style_checks(client, dossier):
    """The checks `ragbase-shield verify` runs against create_app()."""
    assert client.get("/api/dossiers").status_code in (401, 403)
    assert client.get("/api/dossiers", headers={**H, "Host": "evil.example"}).status_code == 403
    r = client.options("/api/mask", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin", "") not in ("*", "https://evil.example")
    r = client.post("/api/mask", json={"text": TEXT, "dossier": dossier}, headers=H)
    assert not leaked(r.json()["masked"])


def test_cli_verify_desk_paths_are_clean(capsys):
    rc = cli.main(["verify"])
    out = capsys.readouterr().out
    desk_lines = [line for line in out.splitlines() if "desk" in line.lower()]
    assert desk_lines and all("CLEAN" in line for line in desk_lines), desk_lines
    assert rc == 0, out


# ---------------------------------------------------------------------------------------------- serve

class _FakeServer:
    instances: list = []

    def __init__(self, cfg):
        self.config = cfg
        self.started = False
        self.sockets = None
        _FakeServer.instances.append(self)

    def run(self, sockets=None):
        self.sockets = sockets
        self.bound = [s.getsockname() for s in sockets]
        self.started = True
        time.sleep(0.05)


@pytest.fixture
def fake_uvicorn(monkeypatch):
    import uvicorn

    _FakeServer.instances = []
    monkeypatch.setattr(uvicorn, "Server", _FakeServer)
    opened: list[str] = []
    event = threading.Event()

    def fake_open(url, new=0):
        opened.append(url)
        event.set()
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", fake_open)
    return opened, event


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_serve_binds_127_0_0_1_only_and_opens_the_browser_with_the_token(fake_uvicorn, capsys):
    opened, event = fake_uvicorn
    port = _free_port()
    assert desk.serve(port=port, open_browser=True, show_token=True) == 0
    server = _FakeServer.instances[-1]
    assert server.bound == [("127.0.0.1", port)]
    cfg = server.config
    assert cfg.host == "127.0.0.1" and cfg.access_log is False and cfg.server_header is False
    assert cfg.proxy_headers is False
    assert event.wait(5)
    token = (config.home() / "desk_token").read_text(encoding="ascii").strip()
    assert opened == [f"http://127.0.0.1:{port}/?t={token}"]
    out = capsys.readouterr().out
    assert f"http://127.0.0.1:{port}/?t={token}" in out


def test_serve_never_prints_the_token_for_an_agent(fake_uvicorn, capsys):
    opened, _event = fake_uvicorn
    port = _free_port()
    assert desk.serve(port=port, open_browser=False, show_token=False) == 0
    token = (config.home() / "desk_token").read_text(encoding="ascii").strip()
    out, err = capsys.readouterr()
    assert token not in out + err and "?t=" not in out + err
    assert f"http://127.0.0.1:{port}/" in out
    time.sleep(0.1)
    assert opened == []


def test_serve_reports_a_busy_port(fake_uvicorn, capsys):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        assert desk.serve(port=port, open_browser=False) == 1
        err = capsys.readouterr().err
        # the user's own terminal: the link that works, with the token (a second launch is not a dead end)
        token = (config.home() / "desk_token").read_text(encoding="ascii").strip()
        assert f"déjà lancé sur le port {port}" in err and f"?t={token}" in err
        assert desk.serve(port=port, open_browser=False, show_token=False) == 1
        err = capsys.readouterr().err
        assert f"Le port {port} est déjà utilisé" in err and token not in err and "?t=" not in err
    assert desk.serve(port=70000, open_browser=False) == 2


def test_serve_cleans_stale_upload_folders(fake_uvicorn):
    root = config.home() / desk.UPLOAD_DIR
    root.mkdir(parents=True, exist_ok=True)
    old = root / "upload-old"
    old.mkdir()
    (old / "upload-1.txt").write_text("x", encoding="utf-8")
    past = time.time() - 7200
    os.utime(old, (past, past))
    fresh = root / "upload-fresh"
    fresh.mkdir()
    desk.serve(port=_free_port(), open_browser=False, show_token=False)
    assert not old.exists() and fresh.exists()


# ---------------------------------------------------------------------------------------------- cli

def test_cli_desk_calls_the_real_serve(monkeypatch, capsys):
    seen = {}

    def fake_serve(port=7878, open_browser=True, show_token=True):
        seen.update(port=port, open_browser=open_browser, show_token=show_token)
        return 0

    monkeypatch.setattr(desk, "serve", fake_serve)
    assert cli.main(["desk", "--port", "7999", "--no-browser"]) == 0
    assert seen == {"port": 7999, "open_browser": False, "show_token": True}
    monkeypatch.setenv("CLAUDECODE", "1")
    assert cli.main(["desk"]) == 0
    assert seen == {"port": config.DESK_PORT, "open_browser": False, "show_token": False}


def test_cli_desk_missing_module_even_after_import(monkeypatch, capsys):
    import ragbase_shield.desk.app  # noqa: F401 - the package attribute now exists

    monkeypatch.setitem(sys.modules, "ragbase_shield.desk.app", None)
    assert cli.main(["desk", "--no-browser"]) == 2
    assert "Shield Desk" in capsys.readouterr().err
