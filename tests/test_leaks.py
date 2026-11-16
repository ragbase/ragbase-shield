"""Leak gate (ARCHITECTURE section 5): for every synthetic fixture, register a dossier on a temp copy, run every
MCP tool and every hook, and assert that no vault value appears in any model-facing output.

The checker here is independent of Shield's own canary: plain string search for every vault value, every
registered party, every gold mention and the dossier title (exact, upper case, folded multi-word forms, and
digits-only forms of numbers)."""
from __future__ import annotations

import asyncio
import io
import json
import re
import shutil
import unicodedata
from pathlib import Path

import pytest
from mcp import Client

from ragbase_shield import hooks, mcp_server, service
from ragbase_shield.engine.types import NEVER_SPREAD_KINDS

FIXTURES = Path(__file__).parent / "fixtures" / "docs"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("’", "'"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.sub("[\u2010\u2011\u2013]", "-", s).split())


def _digits(s: str) -> str:
    return re.sub(r"[\s.\-/]", "", s).lower()


class Leaks:
    def __init__(self, values, birth_places=()):
        self.values = sorted({" ".join(v.split()) for v in values if v and len(v.strip()) >= 3}, key=len, reverse=True)
        # 0.4.4 (birth place fix): a place of birth is a town. It must never show in a birth context ("née le
        # NAISSANCE_1 à Lyon"), but the same town elsewhere is legal text that stays ("avocat au barreau de Lyon",
        # a keep of the gold file): it is checked in its birth context only.
        self.birth = [re.compile(r"(?i)\b(?:né(?:e|s|es)?|naissance)\b[^.\n]{0,60}?(?<![\w-])"
                                 + re.escape(" ".join(v.split())) + r"(?![\w-])")
                      for v in birth_places if v and v.strip()]

    def find(self, output) -> list[str]:
        text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        folded, compact = " " + _fold(text) + " ", _digits(text)
        found = []
        for v in self.values:
            for form in {v, v.upper()}:
                if re.search(r"(?<![\w-])" + re.escape(form) + r"(?![\w-])", text):
                    found.append(v)
                    break
            else:
                f = _fold(v)
                if " " in f and re.search(r"(?<![a-z0-9-])" + re.escape(f) + r"(?![a-z0-9-])", folded):
                    found.append(v)
                elif sum(c.isdigit() for c in v) >= 6 and _digits(v) in compact:
                    found.append(v)
        found += [rx.pattern for rx in self.birth if rx.search(text)]
        return found


@pytest.fixture(autouse=True)
def _fresh():
    service.reset()
    yield
    service.reset()


def _setup(tmp_path: Path, item: dict):
    gold = json.loads((FIXTURES / item["gold"]).read_text(encoding="utf-8"))
    folder = tmp_path / "dossier"
    folder.mkdir()
    shutil.copy(FIXTURES / item["doc"], folder / item["doc"])
    code = service.add_dossier(folder, gold["title"])["code"]
    for p in gold["parties"]:
        service.register(code, p["kind"], p["value"])
    d = service.default().registry.get(code)
    values = [e.value for e in d.all() if e.kind not in NEVER_SPREAD_KINDS] + [p["value"] for p in gold["parties"]]
    values += [m["text"] for m in gold["mentions"]] + [gold["title"]]
    return folder, code, gold, Leaks(values, [e.value for e in d.all() if e.kind in NEVER_SPREAD_KINDS])


def _calls(server, calls: list[tuple[str, dict]]) -> list[tuple[str, bool, str]]:
    async def go():
        out = []
        async with Client(server) as c:
            for name, args in calls:
                r = await c.call_tool(name, args)
                out.append((name, bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)))
        return out

    return asyncio.run(go())


def _hook(event: str, payload: dict) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    rc = hooks.main(event, io.StringIO(json.dumps(payload)), out, err)
    return rc, out.getvalue() + "\n" + err.getvalue()


def test_mcp_server_lists_exactly_six_annotated_tools():
    tools = asyncio.run(mcp_server.build_server().list_tools())
    assert sorted(t.name for t in tools) == sorted(mcp_server.TOOL_NAMES)
    assert len(tools) == 6
    for t in tools:
        assert t.annotations is not None and t.annotations.read_only_hint is (t.name != "shield_save_draft")
        assert t.annotations.destructive_hint is False


@pytest.mark.parametrize("item", MANIFEST, ids=[m["doc"] for m in MANIFEST])
def test_no_vault_value_in_any_mcp_output(tmp_path, item):
    folder, code, gold, leaks = _setup(tmp_path, item)
    server = mcp_server.build_server()
    first = _calls(server, [("shield_list_dossiers", {}), ("shield_list_documents", {"dossier": code}),
                            ("shield_status", {})])
    outputs = list(first)
    start, pages = 0, 0
    while start is not None and pages < 100:
        [(name, err, text)] = _calls(server, [("shield_read_document",
                                               {"dossier": code, "document": "DOC_1", "start": start,
                                                "max_chars": 700})])
        assert not err, text
        outputs.append((f"{name}@{start}", err, text))
        m = re.search(r"suite : start=(\d+)\]", text)
        start = int(m.group(1)) if m else None
        pages += 1
    masked = "\n".join(t for n, _e, t in outputs if n.startswith("shield_read_document"))
    codes = sorted(set(re.findall(r"\b(?:PERSONNE|SOCIETE|EMAIL|IBAN|SIREN|ADRESSE)_[A-Z0-9]+\b", masked)))
    queries = codes[:3] + ["le", "société", "article"]
    queries += [p["value"] for p in gold["parties"]] + [p["value"].split()[-1] for p in gold["parties"]]
    calls = [("shield_search", {"dossier": code, "query": q}) for q in queries]
    calls += [("shield_save_draft", {"dossier": code, "title": f"Projet {codes[0] if codes else ''}",
                                     "content": "# Projet\n\n" + " ".join(codes), "format": "docx"}),
              ("shield_save_draft", {"dossier": code, "title": "Note", "content": "Texte " + " ".join(codes),
                                     "format": "md"}),
              ("shield_read_document", {"dossier": code, "document": "DOC_404"}),
              ("shield_read_document", {"dossier": gold["title"], "document": "DOC_1"}),
              ("shield_list_documents", {"dossier": "DOSSIER_999"})]
    outputs += _calls(server, calls)
    bad = [(name, leaks.find(text)) for name, _e, text in outputs if leaks.find(text)]
    assert not bad, bad
    assert any(c.startswith("PERSONNE_") or c.startswith("SOCIETE_") for c in codes)


@pytest.mark.parametrize("item", MANIFEST, ids=[m["doc"] for m in MANIFEST])
def test_no_vault_value_in_any_hook_output(tmp_path, item):
    folder, code, gold, leaks = _setup(tmp_path, item)
    raw = (FIXTURES / item["doc"]).read_text(encoding="utf-8")
    results = []
    for p in gold["parties"]:
        rc, out = _hook("user-prompt-submit", {"hook_event_name": "UserPromptSubmit",
                                               "prompt": f"Prépare une lettre pour {p['value']}, merci."})
        assert rc == 2, (p["id"], out)
        results.append(("user-prompt-submit", out))
    rc, out = _hook("user-prompt-submit", {"prompt": "Résume DOC_1 de " + code})
    assert rc == 0 and not out.strip()
    target = str(folder / item["doc"])
    for tool, ti in (("Read", {"file_path": target}), ("Grep", {"pattern": "a", "path": str(folder)}),
                     ("Glob", {"pattern": "**/*", "path": str(folder)}), ("Bash", {"command": f"cat '{target}'"}),
                     ("Bash", {"command": f"cd '{folder.parent}' && grep -rn societe ."})):
        rc, out = _hook("pre-tool-use", {"tool_name": tool, "tool_input": ti, "cwd": str(tmp_path)})
        assert rc == 2 and '"deny"' in out, (tool, ti)
        results.append((f"pre-tool-use {tool}", out))
    for tool, resp in (("Bash", {"stdout": raw, "stderr": "", "interrupted": False, "isImage": False}),
                       ("Read", {"type": "text", "file": {"filePath": "/x.txt", "content": raw, "numLines": 1,
                                                          "startLine": 1, "totalLines": 1}}),
                       ("mcp__other__fetch", [{"type": "text", "text": raw}]),
                       ("WebFetch", raw)):
        rc, out = _hook("post-tool-use", {"tool_name": tool, "tool_input": {}, "tool_response": resp})
        assert rc == 0 and "updatedToolOutput" in out, tool
        results.append((f"post-tool-use {tool}", out))
    bad = [(name, leaks.find(out)) for name, out in results if leaks.find(out)]
    assert not bad, bad


def test_journal_and_logs_hold_no_value(tmp_path, caplog):
    caplog.set_level("DEBUG")
    item = MANIFEST[0]
    folder, code, gold, leaks = _setup(tmp_path, item)
    _calls(mcp_server.build_server(), [("shield_read_document", {"dossier": code, "document": "DOC_1"}),
                                       ("shield_search", {"dossier": code, "query": "société"}),
                                       ("shield_read_document", {"dossier": gold["title"], "document": "x"})])
    _hook("user-prompt-submit", {"prompt": gold["parties"][0]["value"]})
    assert not leaks.find(service.journal())
    assert not leaks.find(caplog.text)


# File names of registered parties: joined with hyphens, glued to digits, CamelCase, with an English
# possessive (review of 2026-10-16). None may reach the model, through the MCP server or the hooks.
HARD_FILE_NAMES = ["{s}-c-{o}.txt", "Conclusions-{S}.txt", "Notes-{s}-2026.txt", "{O}-Kbis.txt", "{S}2026.txt",
                   "2026{s}.txt", "{f}{s}.txt", "{l}'s notes.txt", "{s} - attestation.txt", "{s}_c_{o}.txt",
                   "{ol}.txt", "{o}-note.txt"]


def test_no_party_name_in_masked_file_names(tmp_path):
    item = MANIFEST[0]
    folder, code, gold, leaks = _setup(tmp_path, item)
    person = next(p["value"] for p in gold["parties"] if p["kind"] == "PERSON")
    org = next(p["value"] for p in gold["parties"] if p["kind"] == "ORG")
    first, surname = person.split()[0], person.split()[-1]
    org_head = org.split()[0]
    fill = {"s": surname, "S": surname.upper(), "o": org_head, "O": org_head.upper(), "f": first,
            "l": surname.lower(), "ol": org_head.lower()}
    for pattern in HARD_FILE_NAMES:
        (folder / pattern.format(**fill)).write_text("x", encoding="utf-8")
    [(_n, err, text)] = _calls(mcp_server.build_server(), [("shield_list_documents", {"dossier": code})])
    assert not err
    folded = _fold(text)
    for word in {surname, org_head, first}:
        assert _fold(word) not in folded, (word, text)
    rc, out = _hook("post-tool-use", {"tool_name": "Glob", "tool_input": {},
                                      "tool_response": {"filenames": [str(p) for p in folder.iterdir()]}})
    assert rc == 0 and _fold(surname) not in _fold(out.split('"updatedToolOutput"', 1)[-1].split("additionalContext")[0])


def test_the_checker_sees_a_birth_place_in_its_birth_context_only():
    """0.4.4 (birth place fix): the checker flags a place of birth in a birth context, never the same town in a
    court or a bar name (invented text)."""
    leaks = Leaks([], ["Lyon"])
    assert leaks.find("Madame PERSONNE_A, née le NAISSANCE_1 à Lyon, demeurant ADRESSE_1")
    assert leaks.find("Lieu de naissance : Lyon")
    assert not leaks.find("Madame PERSONNE_A, née le NAISSANCE_1 à LIEU_1.\nAvocat au barreau de Lyon.")
    assert not leaks.find("Il ne travaille plus à Lyon. Le conseil de prud'hommes de Lyon est saisi.")
