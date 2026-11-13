# RAGbase Shield in the ChatGPT desktop app and Codex

The ChatGPT desktop app (Work and Codex), the Codex CLI and the Codex IDE extension share one
configuration file, `~/.codex/config.toml`, and can all run **local (stdio) MCP servers**. RAGbase Shield
plugs in there: the model reads your dossier documents masked and never sees the real names.

The screen labels below follow OpenAI's documentation (learn.chatgpt.com, October 2026). They can change.

## What works and what does not

| Surface | Works with Shield? |
|---|---|
| ChatGPT desktop app (macOS, Windows, Linux), local **Work** threads and **Codex** | Yes, local MCP server |
| Codex CLI, Codex IDE extension (VS Code, Cursor...) | Yes, same `config.toml` |
| **ChatGPT web (chatgpt.com)** | **No.** It does not read local configuration and only uses remote MCP servers through plugins. Shield has no remote server, by design: a remote server would see the text. On the web, use Shield Desk or the browser extension ([`../browser-extension/`](../browser-extension/)). |
| ChatGPT mobile apps | No |
| Work threads that run in the cloud ("Work Cloud") | Not reliably: local MCP servers may not be available in cloud containers. Use local threads. |

Plans: OpenAI includes ChatGPT Work and Codex in the Free, Go, Plus, Pro, Business, Edu and Enterprise
plans. On Business, Edu and Enterprise, workspace admins can restrict MCP servers through managed
configuration; ask your admin if the server does not appear.

## Before you start

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (it provides `uvx`).
2. Register a dossier folder: Shield Desk (`uvx ragbase-shield desk`) or `uvx ragbase-shield add <folder>`.

## Add the server: pick one way

**A. From the terminal (simplest)**

```sh
uvx ragbase-shield install chatgpt --dry-run   # shows the change
uvx ragbase-shield install chatgpt             # writes [mcp_servers.ragbase-shield] into ~/.codex/config.toml
```

**B. In the ChatGPT desktop app**

1. Open **Settings**, then **MCP servers**.
2. Click **Add server**.
3. Name: `ragbase-shield`. Type: **STDIO**. Command: `uvx`. Arguments: `ragbase-shield mcp`.
4. Save, then click **Restart**.

**C. By hand**

Copy the table from [`../codex/config.toml.example`](../codex/config.toml.example) into
`~/.codex/config.toml` (Windows: `%USERPROFILE%\.codex\config.toml`), then restart the app.

```toml
[mcp_servers.ragbase-shield]
command = "uvx"
args = ["ragbase-shield", "mcp"]
startup_timeout_sec = 60
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

`default_tools_approval_mode = "writes"`: the read-only Shield tools run without a prompt;
`shield_save_draft` (it writes a file) asks first.

Codex CLI alternative: `codex mcp add ragbase-shield -- uvx ragbase-shield mcp`.

## Check and use

1. In the composer, type `/mcp`: `ragbase-shield` must be listed.
2. Start a **Work** thread (toggle above the composer) or a **Codex** chat, on your computer.
3. Ask: "List my RAGbase Shield dossiers, read DOSSIER_1 and draft a summary, then save it with
   shield_save_draft."
4. Open the restored file in the `Shield - sorties` folder of your dossier.

Rules: work with codes (`PERSONNE_A`), never type real names in the chat, never attach or paste raw client
files. The hooks that block real names in prompts exist only in Claude Code.

## Optional: install as a plugin (adds the safe-workflow skill)

The repository also ships a portable plugin ([`../openai-plugin/`](../openai-plugin/): `plugin.json`,
`mcp.json` with the same stdio server, and the skill) and a repo marketplace at
[`/.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json).

```sh
codex plugin marketplace add ragbase/ragbase-shield
```

Then restart the ChatGPT desktop app, open the **Plugins Directory**, choose the **RAGbase** source and
install **RAGbase Shield**. Use either the plugin
or the `config.toml` entry, not both, so the tools are not listed twice.

## If the server does not start

- "uvx not found": use the full path in `command`: `~/.local/bin/uvx` (macOS, Linux) or
  `%USERPROFILE%\.local\bin\uvx.exe` (Windows).
- First start is slow: `uvx` downloads the package once. `startup_timeout_sec = 60` covers it.
- Run `uvx ragbase-shield doctor`.

Local development (server from a checkout instead of PyPI):

```toml
[mcp_servers.ragbase-shield]
command = "uv"
args = ["run", "--directory", "/path/to/ragbase-shield", "ragbase-shield", "mcp"]
startup_timeout_sec = 60
```
