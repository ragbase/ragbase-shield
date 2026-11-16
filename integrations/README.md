# RAGbase Shield integrations

Every app integration in this folder runs the **same local stdio MCP server**:

```text
command: uvx
args:    ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl", "ragbase-shield", "mcp"]
```

`uvx` comes with [uv](https://docs.astral.sh/uv/getting-started/installation/). On first use it downloads this
file, the wheel of the GitHub release, and its dependencies from PyPI, then caches them. `ragbase-shield install
<app>` writes a shorter entry (uvx with the arguments `ragbase-shield mcp`): uvx then runs the command installed
with `uv tool install` and the same URL, so the guides install that command first. The server talks to the app over
stdio only: no port, no network.

The browser extension is the exception: it does not run the MCP server. It talks to Shield Desk
(`ragbase-shield desk`) on `http://127.0.0.1:7878` with the per-install token.

## List

| App | Folder | What it is |
|---|---|---|
| Claude Desktop (chat) | [`claude-desktop/`](claude-desktop/) | MCPB desktop extension, `manifest_version` 0.4, `server.type` `"uv"`, 6 tools declared, `build_mcpb.sh` |
| Claude app (Claude tab), Mac and Windows | Not in this repository: [ragbase/ragbase-shield-mac](https://github.com/ragbase/ragbase-shield-mac), [ragbase/ragbase-shield-windows](https://github.com/ragbase/ragbase-shield-windows) | The Claude plugin: engine inside the plugin, 7 tools, skill, no hooks |
| Claude Code | [`claude-code/`](claude-code/) + repo-root [`/.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) | Plugin for Claude Code: MCP server, skill, 3 hooks; runs the release wheel it ships in `plugin/vendor/` |
| ChatGPT desktop (Work, Codex) | [`chatgpt/`](chatgpt/) | Step-by-step guide |
| Codex CLI and IDE | [`codex/`](codex/) | `config.toml.example` |
| ChatGPT and Codex plugin | [`openai-plugin/`](openai-plugin/) + repo-root [`/.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json) | Portable Agent Plugins package: `plugin.json`, `mcp.json` (stdio), skill |
| GitHub Copilot (VS Code) | [`vscode/`](vscode/) | `mcp.json.example`, `vscode:mcp/install` link |
| Microsoft 365 Copilot, Word, Outlook, Copilot app | [`microsoft-copilot/`](microsoft-copilot/) | Guide: Shield Desk, clipboard, browser extension. No native connector, by design |
| claude.ai, chatgpt.com, Copilot web, Gemini | [`browser-extension/`](browser-extension/) | Manifest V3 extension for Chrome and Edge, no build step. Not in the stores yet: load it unpacked |

> **The plugin in [`claude-code/`](claude-code/) is for Claude Code only.** Do not add it in the Claude tab of the
> Claude app: it needs uv, and its hooks can stop every message there. In the Claude app, use the Claude plugin:
> [ragbase/ragbase-shield-mac](https://github.com/ragbase/ragbase-shield-mac) (Mac) or
> [ragbase/ragbase-shield-windows](https://github.com/ragbase/ragbase-shield-windows) (Windows).

Shared files:

- [`assets/make_icons.py`](assets/make_icons.py) draws every icon (stdlib only). Run it from the repo root.
- `tests/test_integrations.py` and `tests/js/background_harness.mjs` check all of the above.

## Local development form

To test a checkout, use one of these.

1. Make the entries written by `ragbase-shield install` use your checkout (not the Claude Code plugin: it runs its
   own wheel). uvx uses an installed tool unless `--isolated` is given.

   ```sh
   uv tool install --editable /path/to/ragbase-shield
   ```

2. Or point one app at the checkout directly:

   ```sh
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
