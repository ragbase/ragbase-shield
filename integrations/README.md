# RAGbase Shield integrations

Every app integration runs the **same local stdio MCP server**:

```text
command: uvx
args:    ["ragbase-shield", "mcp"]
```

`uvx` comes with [uv](https://docs.astral.sh/uv/getting-started/installation/). It downloads the
`ragbase-shield` package from PyPI on first use and caches it. The server talks to the app over stdio only:
no port, no network.

The browser extension is the exception: it does not run the MCP server. It talks to Shield Desk
(`ragbase-shield desk`) on `http://127.0.0.1:7878` with the per-install token.

## List and status

"Tested" means what was actually run on 2026-10-16. Nothing here was tested on Windows yet.

| App | Folder | What it is | Status |
|---|---|---|---|
| Claude Desktop (chat) | [`claude-desktop/`](claude-desktop/) | MCPB desktop extension, `manifest_version` 0.4, `server.type` `"uv"`, 6 tools declared, `build_mcpb.sh` | **Built and validated**: official CLI `@anthropic-ai/mcpb` 2.1.2 `validate` and `pack` pass (283 KB bundle, 34 files). `build_mcpb.sh --smoke` starts the bundled server with `uv run` and gets the 6 manifest tools. **Not installed** in Claude Desktop yet. |
| Claude Code and Cowork | [`claude-code/`](claude-code/) + repo-root [`/.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) | Plugin: MCP server, skill, 3 hooks | **Validated**: `claude plugin validate` passes for the marketplace and the plugin (Claude Code 2.1.220). **Not installed end to end** (needs the PyPI package with the `mcp` and `hook` commands). |
| ChatGPT desktop (Work, Codex) | [`chatgpt/`](chatgpt/) | Step-by-step guide | **Not tested.** Written from the official docs. |
| Codex CLI and IDE | [`codex/`](codex/) | `config.toml.example` | TOML parses (unit test). **Not tested** in Codex. |
| ChatGPT and Codex plugin | [`openai-plugin/`](openai-plugin/) + repo-root [`/.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json) | Portable Agent Plugins package: `plugin.json`, `mcp.json` (stdio), skill | Checked against the Agent Plugins 1.0.0 schemas (unit tests). **Not tested** in ChatGPT or Codex. |
| GitHub Copilot (VS Code) | [`vscode/`](vscode/) | `mcp.json.example`, one-click `vscode:mcp/install` link | Link encoding unit-tested. **Not tested** in VS Code. |
| Microsoft 365 Copilot, Word, Outlook, Copilot app | [`microsoft-copilot/`](microsoft-copilot/) | Guide: Shield Desk, clipboard, browser extension | Documentation only. No native connector, by design. |
| claude.ai, chatgpt.com, Copilot web, Gemini | [`browser-extension/`](browser-extension/) | Manifest V3 extension for Chrome and Edge, no build step | **Partly tested**: service worker router unit-tested in Node (17 checks); paste masking, badge, blocked paste ("Coller quand même", "Annuler") tested in Chromium with a mocked `chrome` API; options and side panel rendered with mocks. **Not yet loaded** as an extension against a live Shield Desk or the five real sites. |

Shared files:

- [`assets/make_icons.py`](assets/make_icons.py) draws every icon (stdlib only). Run it from the repo root.
- `tests/test_integrations.py` and `tests/js/background_harness.mjs` check all of the above.

## Local development form

Before the package is on PyPI, or to test a checkout, use one of these:

```sh
# 1. Make every "uvx ragbase-shield ..." (MCP server and Claude Code hooks) use your checkout.
#    uvx uses an installed tool unless --isolated is given.
uv tool install --editable /path/to/ragbase-shield

# 2. Or point one app at the checkout directly:
uv run --directory /path/to/ragbase-shield ragbase-shield mcp
```

For form 2 the app config becomes `command: "uv"`, `args: ["run", "--directory", "/path/to/ragbase-shield",
"ragbase-shield", "mcp"]`. Each folder's README shows it for that app.

## Known limits (all apps)

- Shield protects what goes **through Shield** (dossier documents read with the Shield tools, text pasted
  through the extension or Desk). Text typed or pasted into a chat without Shield, and files attached to
  a chat, reach the provider before Shield can act.
- Desktop apps started from the Dock or Start menu may not see `uvx` on their `PATH`. If an app says it
  cannot start `uvx`, use the full path: `~/.local/bin/uvx` (macOS, Linux) or
  `%USERPROFILE%\.local\bin\uvx.exe` (Windows).
- Pseudonymisation is reversible and detection is never complete. Review masked text in sensitive cases.
