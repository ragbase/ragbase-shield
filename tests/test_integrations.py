"""Static checks for every app integration (owner: integrations). Synthetic data only, no network."""
from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
INTEG = ROOT / "integrations"
EXT = INTEG / "browser-extension"
TOOLS = {
    "shield_list_dossiers",
    "shield_list_documents",
    "shield_read_document",
    "shield_search",
    "shield_save_draft",
    "shield_status",
}
HOOK_EVENTS = {"user-prompt-submit", "pre-tool-use", "post-tool-use"}
PROVIDER_SITES = [
    "https://chatgpt.com/*",
    "https://claude.ai/*",
    "https://copilot.microsoft.com/*",
    "https://m365.cloud.microsoft/*",
    "https://gemini.google.com/*",
]
SERVER_ARGS = ["ragbase-shield", "mcp"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", data[16:24])


# ---- every JSON file parses ------------------------------------------------------------------
def _json_files():
    files = list(INTEG.rglob("*.json")) + list(INTEG.rglob("*.json.example"))
    files += [ROOT / ".claude-plugin" / "marketplace.json", ROOT / ".agents" / "plugins" / "marketplace.json"]
    return sorted(set(files))


@pytest.mark.parametrize("path", _json_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_json_parses(path):
    assert isinstance(load(path), dict)


def test_versions_match_pyproject():
    v = project_version()
    assert load(INTEG / "claude-desktop" / "manifest.json")["version"] == v
    assert load(INTEG / "claude-code" / "plugin" / ".claude-plugin" / "plugin.json")["version"] == v
    assert load(INTEG / "openai-plugin" / "plugin.json")["version"] == v
    assert load(EXT / "manifest.json")["version"] == v


# ---- Claude Desktop (MCPB) -------------------------------------------------------------------
MCPB_TOP_KEYS = {
    "$schema", "dxt_version", "manifest_version", "name", "display_name", "version", "description",
    "long_description", "author", "repository", "homepage", "documentation", "support", "icon", "icons",
    "screenshots", "localization", "server", "tools", "tools_generated", "prompts", "prompts_generated",
    "keywords", "license", "privacy_policies", "compatibility", "user_config", "_meta",
}


def test_mcpb_manifest():
    m = load(INTEG / "claude-desktop" / "manifest.json")
    assert set(m) <= MCPB_TOP_KEYS, set(m) - MCPB_TOP_KEYS  # the v0.4 schema rejects unknown keys
    for key in ("name", "version", "description", "author", "server"):
        assert m[key]
    assert m["manifest_version"] == "0.4"  # first version with server.type "uv"
    assert m["name"] == "ragbase-shield"
    assert m["display_name"] == "RAGbase Shield"
    assert m["author"]["name"] == "RAGbase"
    assert m["license"] == "Apache-2.0"
    server = m["server"]
    assert set(server) == {"type", "entry_point", "mcp_config"}
    assert server["type"] == "uv"
    assert server["entry_point"] == "src/server.py"
    assert server["mcp_config"]["command"] == "uv"
    assert "${__dirname}" in server["mcp_config"]["args"]
    assert {t["name"] for t in m["tools"]} == TOOLS
    assert all(set(t) <= {"name", "description"} and t["description"] for t in m["tools"])
    assert m["tools_generated"] is False
    assert set(m["compatibility"]["platforms"]) == {"darwin", "win32"}
    assert set(m["compatibility"]) <= {"claude_desktop", "platforms", "runtimes"}
    icon = INTEG / "claude-desktop" / m["icon"]
    assert png_size(icon) == (512, 512)


def test_mcpb_launcher_and_build_script():
    launcher = (INTEG / "claude-desktop" / "server.py").read_text(encoding="utf-8")
    assert '"mcp"' in launcher and "ragbase_shield.cli" in launcher
    assert "print(" not in launcher  # stdout is the MCP channel
    script = (INTEG / "claude-desktop" / "build_mcpb.sh").read_text(encoding="utf-8")
    assert "@anthropic-ai/mcpb pack" in script and "@anthropic-ai/mcpb validate" in script
    assert "$ROOT/dist" in script
    assert "dist/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


# ---- Claude Code / Cowork plugin ---------------------------------------------------------------
PLUGIN = INTEG / "claude-code" / "plugin"


def plugin_pin() -> str:
    """The exact package the Claude plugin runs with uvx: raise it with the project version at each release."""
    return f"ragbase-shield=={project_version()}"


def test_claude_marketplace():
    mk = load(ROOT / ".claude-plugin" / "marketplace.json")
    assert mk["name"] == "ragbase"
    assert mk["owner"]["name"]
    [entry] = mk["plugins"]
    assert entry["name"] == "ragbase-shield"
    assert entry["source"] == "./integrations/claude-code/plugin"
    assert (ROOT / entry["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_claude_plugin_manifest_and_mcp():
    p = load(PLUGIN / ".claude-plugin" / "plugin.json")
    assert p["name"] == "ragbase-shield"
    assert p["license"] == "Apache-2.0"
    mcp = load(PLUGIN / ".mcp.json")["mcpServers"]["ragbase-shield"]
    # The plugin pins the package (Anthropic's plugin directory blocks an unpinned uvx launcher).
    assert mcp["command"] == "uvx" and mcp["args"] == [plugin_pin(), "mcp"]
    assert p["version"] == project_version()
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    assert len(re.sub(r"```.*?```", " ", readme, flags=re.S).split()) >= 40  # directory listing text


def test_claude_hooks():
    hooks = load(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"UserPromptSubmit", "PreToolUse", "PostToolUse"}
    expected = {
        "UserPromptSubmit": "user-prompt-submit",
        "PreToolUse": "pre-tool-use",
        "PostToolUse": "post-tool-use",
    }
    for event, sub in expected.items():
        for group in hooks[event]:
            [handler] = group["hooks"]
            assert handler["type"] == "command"
            assert handler["command"] == f"uvx {plugin_pin()} hook {sub}"
            assert handler["timeout"] >= 60
        assert sub in HOOK_EVENTS
    assert len(hooks["UserPromptSubmit"]) == 1 and len(hooks["PostToolUse"]) == 1
    builtin, mcp = hooks["PreToolUse"]
    assert builtin["matcher"] == ("Read|Grep|Glob|LS|LSP|Bash|PowerShell|Monitor|Edit|MultiEdit|Write|NotebookRead|"
                                  "NotebookEdit|Artifact|SendUserFile")
    assert mcp["matcher"] == "mcp__.*"  # file tools of other MCP servers (Shield's own tools are skipped)
    from ragbase_shield import hooks as shield_hooks
    handled = shield_hooks._FILE_TOOLS | shield_hooks._TREE_TOOLS | shield_hooks._SHELL_TOOLS | shield_hooks._UPLOAD_TOOLS
    assert set(builtin["matcher"].split("|")) == handled
    assert "matcher" not in hooks["UserPromptSubmit"][0]  # this event has no matcher
    assert "matcher" not in hooks["PostToolUse"][0]  # mask leftovers in every tool result


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md needs YAML frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_skill_content_and_copies():
    claude = PLUGIN / "skills" / "ragbase-shield" / "SKILL.md"
    openai = INTEG / "openai-plugin" / "skills" / "ragbase-shield" / "SKILL.md"
    text = claude.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert fm["name"] == "ragbase-shield"
    assert len(fm["description"]) > 40
    for tool in TOOLS:
        assert tool in text
    assert "Shield - sorties" in text
    assert "## Français" in text and "## English" in text
    assert openai.read_text(encoding="utf-8") == text, "keep both SKILL.md copies identical"


def test_output_dir_name_matches_config():
    from ragbase_shield import config

    assert config.OUTPUT_DIR_NAME == "Shield - sorties"


# ---- ChatGPT desktop / Codex ---------------------------------------------------------------------
@pytest.mark.skipif(tomllib is None, reason="tomllib needs Python 3.11+")
def test_codex_config_example():
    data = tomllib.loads((INTEG / "codex" / "config.toml.example").read_text(encoding="utf-8"))
    server = data["mcp_servers"]["ragbase-shield"]
    assert server["command"] == "uvx"
    assert server["args"] == SERVER_ARGS
    assert server["default_tools_approval_mode"] in {"auto", "prompt", "writes", "approve"}


def test_openai_portable_plugin():
    base = INTEG / "openai-plugin"
    p = load(base / "plugin.json")
    assert p["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert re.fullmatch(r"(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", p["name"])
    allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
               "keywords", "extensions"}
    assert set(p) <= allowed
    ui = p["extensions"]["com.openai"]["interface"]
    for key in ("composerIcon", "logo"):
        assert ui[key].startswith("./") and (base / ui[key]).is_file()
    mcp = load(base / "mcp.json")
    assert mcp["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    server = mcp["mcpServers"]["ragbase-shield"]
    assert set(server) <= {"type", "command", "args", "env", "cwd"}
    assert server["type"] == "stdio" and server["command"] == "uvx" and server["args"] == SERVER_ARGS
    assert server["cwd"].startswith("${PLUGIN_ROOT}")
    assert not set(server.get("env", {})) & {"PLUGIN_ROOT", "PLUGIN_DATA"}


def test_openai_repo_marketplace():
    mk = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert mk["name"] and mk["interface"]["displayName"]
    for entry in mk["plugins"]:
        assert entry["policy"]["installation"] in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
        assert entry["policy"]["authentication"] in {"ON_INSTALL", "ON_FIRST_USE"}
        assert entry["category"]
        path = entry["source"]["path"]
        assert path.startswith("./") and ".." not in path
        assert (ROOT / path / "plugin.json").is_file()


# ---- VS Code / Copilot -------------------------------------------------------------------------
def test_vscode_example_and_install_link():
    server = load(INTEG / "vscode" / "mcp.json.example")["servers"]["ragbase-shield"]
    assert server == {"type": "stdio", "command": "uvx", "args": SERVER_ARGS}
    payload = json.dumps({"name": "ragbase-shield", **server}, separators=(",", ":"))
    link = "vscode:mcp/install?" + urllib.parse.quote(payload, safe="")
    readme = (INTEG / "vscode" / "README.md").read_text(encoding="utf-8")
    assert link in readme
    decoded = json.loads(urllib.parse.unquote(link.split("?", 1)[1]))
    assert decoded["command"] == "uvx" and decoded["args"] == SERVER_ARGS
    assert "MCP servers in Copilot" in readme


# ---- Browser extension ---------------------------------------------------------------------------
def test_extension_manifest_is_minimal():
    m = load(EXT / "manifest.json")
    assert m["manifest_version"] == 3
    assert sorted(m["permissions"]) == ["sidePanel", "storage"]
    assert m["host_permissions"] == ["http://127.0.0.1/*"]
    assert "optional_permissions" not in m and "optional_host_permissions" not in m
    [cs] = m["content_scripts"]
    assert cs["matches"] == PROVIDER_SITES
    assert cs["js"] == ["content.js"]
    assert m["background"] == {"service_worker": "background.js"}
    for rel in [m["side_panel"]["default_path"], m["options_ui"]["page"], "background.js", "content.js",
                *m["icons"].values(), *m["action"]["default_icon"].values()]:
        assert (EXT / rel).is_file(), rel
    for size, rel in m["icons"].items():
        assert png_size(EXT / rel) == (int(size), int(size))
    csp = m["content_security_policy"]["extension_pages"]
    assert "script-src 'self'" in csp and "unsafe" not in csp


def _locale_keys(lang: str) -> dict:
    return load(EXT / "_locales" / lang / "messages.json")


def test_extension_locales_complete():
    fr, en = _locale_keys("fr"), _locale_keys("en")
    assert set(fr) == set(en)
    for key in fr:
        assert set(fr[key].get("placeholders", {})) == set(en[key].get("placeholders", {})), key
    used = set()
    manifest_text = (EXT / "manifest.json").read_text(encoding="utf-8")
    used |= set(re.findall(r"__MSG_(\w+)__", manifest_text))
    for path in list(EXT.glob("*.js")) + list(EXT.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        used |= set(re.findall(r"\bt\('(\w+)'", text))
        used |= set(re.findall(r"getMessage\('(\w+)'", text))
        used |= set(re.findall(r"data-i18n(?:-placeholder|-title)?=\"(\w+)\"", text))
        for pair in re.findall(r"\['(err\w+)', '(err\w+)'\]", text):  # content.js ERRORS table
            used |= set(pair)
    missing = used - set(fr)
    assert not missing, missing
    assert "texte masqué" in fr["badgeMasked"]["message"]
    assert fr["errDeskDown"]["message"] == "Shield Desk n'est pas lancé"


def test_extension_never_restores_into_provider_pages():
    content = (EXT / "content.js").read_text(encoding="utf-8")
    for forbidden in ("/api/restore", "shield:restore", "shield:dossiers", "/api/dossiers", "fetch("):
        assert forbidden not in content, forbidden
    assert "e.isTrusted" in content  # page scripts cannot drive the masking oracle
    background = (EXT / "background.js").read_text(encoding="utf-8")
    assert "CONTENT_ALLOWED = new Set(['shield:mask', 'shield:openOptions'])" in background


def test_extension_talks_only_to_localhost():
    for path in list(EXT.glob("*.js")) + list(EXT.glob("*.html")) + list(EXT.glob("*.css")):
        text = path.read_text(encoding="utf-8")
        for url in re.findall(r"(?:https?|wss?)://[^\s'\"`)]+", text):
            assert url.startswith("http://127.0.0.1"), f"{path.name}: {url}"
        assert "<script src=\"http" not in text
        assert "eval(" not in text and "new Function" not in text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_extension_background_router_with_node():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "js" / "background_harness.mjs"), str(EXT / "background.js")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip().startswith("OK ")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_extension_scripts_parse_with_node():
    for path in EXT.glob("*.js"):
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f"{path.name}: {result.stderr}"


# ---- docs ---------------------------------------------------------------------------------------
def test_integrations_readme_lists_everything():
    text = (INTEG / "README.md").read_text(encoding="utf-8")
    for name in ("claude-desktop", "claude-code", "codex", "openai-plugin", "chatgpt", "vscode",
                 "microsoft-copilot", "browser-extension"):
        assert f"{name}/" in text, name
        assert (INTEG / name).is_dir()
    for folder in ("chatgpt", "microsoft-copilot", "vscode", "browser-extension", "claude-desktop", "claude-code"):
        assert (INTEG / folder / "README.md").is_file(), folder


def test_no_absolute_user_paths_in_integrations():
    for path in INTEG.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md", ".toml", ".example", ".js", ".sh", ".py", ".html"}:
            text = path.read_text(encoding="utf-8")
            assert "/Users/" not in text and "C:\\Users\\" not in text, path


# ---- MCP server cross-check (runs once the mcp module exists) -------------------------------------
def test_manifest_tools_match_mcp_server():
    import asyncio

    try:
        from ragbase_shield import mcp_server
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        pytest.skip("ragbase_shield.mcp_server not built yet")
    servers = [v for v in vars(mcp_server).values() if isinstance(v, MCPServer)]
    if not servers:
        factory = getattr(mcp_server, "build_server", None) or getattr(mcp_server, "create_server", None)
        if factory is None:
            pytest.skip("no MCPServer instance or factory found in ragbase_shield.mcp_server")
        servers = [factory()]
    tools = asyncio.run(servers[0].list_tools())
    names = {t.name for t in tools}
    manifest = {t["name"] for t in load(INTEG / "claude-desktop" / "manifest.json")["tools"]}
    assert names == manifest == TOOLS
