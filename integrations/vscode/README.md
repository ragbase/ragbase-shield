# RAGbase Shield in GitHub Copilot (VS Code)

Copilot Chat in agent mode can use the RAGbase Shield tools through a local MCP server (stdio). The server
runs on your computer; Copilot only receives masked text (codes such as `PERSONNE_A`).

The config files follow the official VS Code documentation.

## Before you start

- Install uv (it provides `uvx`). uv is the open-source tool that downloads and runs Shield.

  On a Mac: open the Terminal app, paste this line, press Enter.

  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

  On Windows: open PowerShell, paste this line, press Enter.

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  If uv is already on your computer, paste this line anyway: it updates uv.

  Close the window and open a new one.
- Register at least one dossier folder: `ragbase-shield add <folder>` or Shield Desk. The `ragbase-shield`
  command comes from the wheel of the release:
  `uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl`.
- **Copilot Business and Copilot Enterprise:** an organization or enterprise owner must turn on the
  **"MCP servers in Copilot"** policy in the GitHub Copilot policy settings. It is off by default for
  these plans, and Copilot will not start MCP servers until it is on. (GitHub announced a new global default
  for unconfigured Copilot features from 22 October 2026: check with your admin which value applies.)
  Copilot Free, Pro and Pro+ users do not need an admin.

## Option 1: one-click install

Open this link (VS Code must be installed). VS Code asks you to confirm, then adds the server to your
user profile:

```
vscode:mcp/install?%7B%22name%22%3A%22ragbase-shield%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22https%3A%2F%2Fgithub.com%2Fragbase%2Fragbase-shield%2Freleases%2Fdownload%2Fv0.4.4%2Fragbase_shield-0.4.4-py3-none-any.whl%22%2C%22ragbase-shield%22%2C%22mcp%22%5D%7D
```

VS Code Insiders:

```
vscode-insiders:mcp/install?%7B%22name%22%3A%22ragbase-shield%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22https%3A%2F%2Fgithub.com%2Fragbase%2Fragbase-shield%2Freleases%2Fdownload%2Fv0.4.4%2Fragbase_shield-0.4.4-py3-none-any.whl%22%2C%22ragbase-shield%22%2C%22mcp%22%5D%7D
```

The link is `vscode:mcp/install?` followed by the URL-encoded JSON of the server
(`encodeURIComponent(JSON.stringify(config))`), here (uvx runs the wheel of the release):

```json
{"name":"ragbase-shield","type":"stdio","command":"uvx","args":["--from","https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl","ragbase-shield","mcp"]}
```

GitHub pages do not open `vscode:` links. For a README button, use the web redirect that many MCP
READMEs use (it opens VS Code with the same configuration):

```
https://insiders.vscode.dev/redirect/mcp/install?name=ragbase-shield&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22https%3A%2F%2Fgithub.com%2Fragbase%2Fragbase-shield%2Freleases%2Fdownload%2Fv0.4.4%2Fragbase_shield-0.4.4-py3-none-any.whl%22%2C%22ragbase-shield%22%2C%22mcp%22%5D%7D
```

Command line alternative:

```bash
code --add-mcp '{"name":"ragbase-shield","type":"stdio","command":"uvx","args":["--from","https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl","ragbase-shield","mcp"]}'
```

## Option 2: `ragbase-shield install vscode`

The Shield CLI writes the server into your VS Code user `mcp.json`. Use `--dry-run` to see the change first.

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl
ragbase-shield install vscode --dry-run
ragbase-shield install vscode
```

## Option 3: by hand

Current VS Code docs prefer two portable places and call the older ones "deprecated, kept for compatibility":

- the workspace file `.mcp.json` at the project root, or `$COPILOT_HOME/mcp-config.json`
  (`~/.copilot/mcp-config.json`) for every project, with a top-level `"mcpServers"` key:

  ```json
  {"mcpServers": {"ragbase-shield": {"type": "stdio", "command": "uvx", "args": ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl", "ragbase-shield", "mcp"]}}}
  ```

- the older `.vscode/mcp.json` and the user-profile `mcp.json` (top-level `"servers"`) still work today.
  `ragbase-shield install vscode` writes the user-profile file.

- For all your projects: run **MCP: Open User Configuration** from the Command Palette and add the
  `ragbase-shield` entry from [`mcp.json.example`](mcp.json.example) under `"servers"`.
- For one project only: copy [`mcp.json.example`](mcp.json.example) to `.vscode/mcp.json` in that project.

VS Code shows a trust dialog the first time the server starts. Accept it for `ragbase-shield`.

Local development (run from a checkout of the repository instead of the wheel of the release):

```json
{
  "servers": {
    "ragbase-shield": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ragbase-shield", "ragbase-shield", "mcp"]
    }
  }
}
```

## Use it

1. Open Copilot Chat and choose **Agent** mode.
2. Click the tools icon and check that the `ragbase-shield` tools are enabled.
3. Ask: "List my RAGbase Shield dossiers, read DOSSIER_1 and draft a summary, then save it with
   shield_save_draft."
4. Open the restored file in the `Shield - sorties` folder of your dossier.

Rules: work with codes, never type real names in the chat, never attach or paste raw client files.
Copilot hooks are not used: the Claude Code hooks (block real names in prompts) do not exist in VS Code.
