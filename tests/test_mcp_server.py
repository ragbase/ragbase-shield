"""MCP server (ARCHITECTURE 4.5): exactly six tools with annotations, codes-only results, code-only errors,
no tool that unmasks text for the model. Synthetic data only."""
from __future__ import annotations

import asyncio
import os
import re
import sys

import pytest
from mcp import Client, StdioServerParameters

from ragbase_shield import __version__, config, documents, mcp_server, service

TEXT = ("Madame Clémence MORVANDIAU, demeurant 14 rue des Glycines, 59300 Valenciennes, contre la société "
        "LAMBRETTI CONSEIL SAS. Mme Morvandiau réclame un acompte.\n")
SECRETS = ("MORVANDIAU", "Morvandiau", "LAMBRETTI", "Lambretti", "Glycines")
EXPECTED = {
    "shield_list_dossiers": (True, set()),
    "shield_list_documents": (True, {"dossier"}),
    "shield_read_document": (True, {"dossier", "document", "start", "max_chars"}),
    "shield_search": (True, {"dossier", "query"}),
    "shield_save_draft": (False, {"dossier", "title", "content", "format"}),
    "shield_status": (True, set()),
}


@pytest.fixture(autouse=True)
def _fresh():
    service.reset()
    yield
    service.reset()


@pytest.fixture
def dossier(tmp_path):
    folder = tmp_path / "Dossier Morvandiau"
    folder.mkdir()
    (folder / "assignation.txt").write_text(TEXT * 8, encoding="utf-8")
    return {"code": service.add_dossier(folder, "Morvandiau c. Lambretti Conseil SAS")["code"], "folder": folder}


def call(name: str, args: dict | None = None, server=None) -> tuple[bool, str]:
    server = server or mcp_server.build_server()

    async def go():
        async with Client(server) as c:
            r = await c.call_tool(name, args or {})
            return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

    return asyncio.run(go())


def clean(text: str) -> bool:
    return not any(s in text for s in SECRETS)


def test_exactly_six_tools_with_annotations():
    tools = asyncio.run(mcp_server.build_server().list_tools())
    assert {t.name for t in tools} == set(EXPECTED) == set(mcp_server.TOOL_NAMES)
    for t in tools:
        read_only, params = EXPECTED[t.name]
        a = t.annotations
        assert a is not None and a.title
        assert a.read_only_hint is read_only
        assert a.destructive_hint is False and a.open_world_hint is False
        assert set((t.input_schema or {}).get("properties", {})) == params
        assert t.description and len(t.description) > 40
    by_name = {t.name: t for t in tools}
    assert by_name["shield_save_draft"].annotations.idempotent_hint is False
    fmt = by_name["shield_save_draft"].input_schema["properties"]["format"]
    assert set(fmt.get("enum", [])) == {"docx", "md"}


def test_no_tool_unmasks_text_for_the_model():
    tools = asyncio.run(mcp_server.build_server().list_tools())
    for t in tools:
        assert not re.search(r"restore|unmask|reveal|real_value|demask", t.name)
        for p in (t.input_schema or {}).get("properties", {}):
            assert p not in ("text", "masked_text", "codes", "code")


def test_instructions_in_french_and_english():
    s = mcp_server.build_server()
    text = s.instructions
    assert "shield_save_draft" in text and "Shield - sorties" in text
    assert "Ne demandez jamais" in text and "never ask the user for real names" in text
    assert "ne pas coller" in text and "paste raw client text" in text
    assert s.name == "RAGbase Shield"


def test_list_dossiers_without_dossier():
    err, out = call("shield_list_dossiers")
    assert not err and "Aucun dossier" in out


def test_full_workflow_returns_codes_only(dossier):
    code = dossier["code"]
    server = mcp_server.build_server()
    err, out = call("shield_list_dossiers", server=server)
    assert not err and code in out and clean(out)
    err, out = call("shield_list_documents", {"dossier": code}, server)
    assert not err and "DOC_1 | txt" in out and clean(out)
    err, out = call("shield_read_document", {"dossier": code, "document": "DOC_1", "max_chars": 500}, server)
    assert not err and clean(out) and "PERSONNE_" in out
    m = re.search(r"suite : start=(\d+)", out)
    assert m, out[:200]
    err, out2 = call("shield_read_document", {"dossier": code, "document": "DOC_1", "start": int(m.group(1))},
                     server)
    assert not err and clean(out2) and "fin du document" in out2
    person = re.search(r"Madame (PERSONNE_[A-Z]+)", out).group(1)
    err, out = call("shield_search", {"dossier": code, "query": f"{person} acompte"}, server)
    assert not err and "DOC_1" in out and clean(out)
    err, out = call("shield_search", {"dossier": code, "query": "Morvandiau"}, server)
    assert not err and "aucun résultat" in out
    err, out = call("shield_save_draft", {"dossier": code, "title": f"Note {person}",
                                          "content": f"# Note\n\n{person} réclame un acompte."}, server)
    assert not err and re.search(r"Enregistré : OUTPUT_1 \(\d+ Ko, docx\)", out) and "Shield - sorties" in out
    assert clean(out) and str(dossier["folder"]) not in out
    files = list((dossier["folder"] / "Shield - sorties").glob("*.docx"))
    assert len(files) == 1 and "MORVANDIAU" in documents.read_text(files[0]).text.upper()
    err, out = call("shield_status", server=server)
    assert not err and __version__ in out and "OCR" in out and "100" not in out


def test_save_draft_reports_unknown_codes(dossier):
    err, out = call("shield_save_draft", {"dossier": dossier["code"], "title": "x",
                                          "content": "PERSONNE_ZZ et SOCIETE_Q", "format": "md"})
    assert not err and "PERSONNE_ZZ" in out and "SOCIETE_Q" in out


@pytest.mark.parametrize("args", [
    {"dossier": "DOSSIER_77", "document": "DOC_1"},
    {"dossier": "Morvandiau c. Lambretti Conseil SAS", "document": "DOC_1"},
    {"dossier": "DOSSIER_1", "document": "DOC_404"},
    {"dossier": "DOSSIER_1", "document": "/etc/passwd"},
])
def test_errors_are_code_only(dossier, args):
    err, out = call("shield_read_document", args)
    assert err and clean(out) and "Traceback" not in out
    if "Morvandiau" in str(args):
        assert "Morvandiau" not in out


def test_internal_error_is_generic(dossier, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("Clémence MORVANDIAU")

    monkeypatch.setattr(service, "list_documents", boom)
    err, out = call("shield_list_documents", {"dossier": dossier["code"]})
    assert err and clean(out) and "interne" in out


def test_final_canary_on_tool_results(dossier, monkeypatch):
    """A value that slips into a formatted result is still replaced before it leaves the server."""
    monkeypatch.setattr(service, "list_documents", lambda code: [
        {"id": "DOC_1", "kind": "txt", "size": 10, "pages": None, "masked_name": "x.txt",
         "masked_path": "Clémence MORVANDIAU.txt"}])
    err, out = call("shield_list_documents", {"dossier": dossier["code"]})
    assert not err and clean(out)


def test_scanned_pdf_message(dossier):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    with open(dossier["folder"] / "scan.pdf", "wb") as fh:
        w.write(fh)
    err, listing = call("shield_list_documents", {"dossier": dossier["code"]})
    doc = re.search(r"(DOC_\d+) \| pdf", listing).group(1)
    err, out = call("shield_read_document", {"dossier": dossier["code"], "document": doc})
    assert not err and "OCR" in out


def test_stdio_server_in_a_child_process(dossier, tmp_path):
    env = dict(os.environ, RAGBASE_SHIELD_HOME=str(config.home()), RAGBASE_SHIELD_KEYRING="0")
    params = StdioServerParameters(command=sys.executable, args=["-m", "ragbase_shield", "mcp"], env=env)
    errlog = tmp_path / "child-stderr.txt"

    async def go():
        from mcp.client.stdio import stdio_client

        with open(errlog, "w", encoding="utf-8") as fh:
            async with Client(stdio_client(params, errlog=fh)) as c:
                tools = await c.list_tools()
                names = {t.name for t in getattr(tools, "tools", tools)}
                r = await c.call_tool("shield_read_document", {"dossier": dossier["code"], "document": "DOC_1"})
                return names, "\n".join(x.text for x in r.content), c.instructions

    names, text, instructions = asyncio.run(asyncio.wait_for(go(), 120))
    assert names == set(EXPECTED)
    assert clean(errlog.read_text(encoding="utf-8"))
    assert "PERSONNE_" in text and clean(text)
    assert instructions and "shield_save_draft" in instructions
