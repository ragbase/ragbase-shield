# RAGbase Shield for Claude Desktop (desktop extension, .mcpb)

A one-click desktop extension that runs the RAGbase Shield MCP server on your computer. Claude reads
your dossier documents **masked** through 6 tools and never sees the real names.

## Install (users)

1. Download `ragbase-shield-<version>.mcpb` from the GitHub Releases page:
   https://github.com/ragbase/ragbase-shield/releases/latest
   (The Claude directory no longer accepts `.mcpb` files, so Releases is the distribution channel.)
2. Install it in one of these ways:
   - double-click the file;
   - drag it into the Claude Desktop window;
   - **Settings > Extensions > Advanced settings > Install Extension…** and choose the file.
3. Review the details and confirm.
4. Register a dossier folder once: open Shield Desk (`uvx ragbase-shield desk`) or run
   `uvx ragbase-shield add <folder>`.
5. In a chat, ask: "List my RAGbase Shield dossiers, read DOSSIER_1 and draft a summary, then save it."
   The restored file appears in the `Shield - sorties` folder of the dossier.

The extension uses `server.type: "uv"`: Claude Desktop installs Python and the dependencies itself with
uv, on first start. No separate Python install is needed.

Team and Enterprise: an admin can allow or block desktop extensions for the organization.

**macOS keychain prompt.** By default the vault key is stored in the macOS keychain by the
first program that opens the vault (usually Shield Desk, run by `uvx`). The extension's server runs another
Python program (the uv environment inside the extension folder), and macOS keychain access rules are per
program. Expect a dialog that asks to let the extension use the "ragbase-shield" keychain item: click
**Always Allow**. If you click Deny, the vault stays closed and every Shield tool answers "vault unreadable"
(fail closed: nothing reaches Claude).
Two ways around it: open the vault with the extension first (ask Claude for `shield_status` before you start
Shield Desk), or use the 0600 key file for every program (`RAGBASE_SHIELD_KEYRING=0` in the environment of
Shield Desk and of the extension, before the first start).

Do not attach client files to the chat and do not paste raw client text: that content reaches the provider
before Shield can act. Connect the folder in Shield Desk instead.

## Tools declared in the manifest

| Tool | What it returns |
|---|---|
| `shield_list_dossiers` | dossier codes and counts, never real titles |
| `shield_list_documents` | coded ids (DOC_n) and masked file names |
| `shield_read_document` | masked text, with paging |
| `shield_search` | masked snippets |
| `shield_save_draft` | "saved OUTPUT_n (x KB)": the restored file is written locally |
| `shield_status` | version, engine mode, limits |

## Build (maintainers)

```sh
integrations/claude-desktop/build_mcpb.sh            # assemble, uv lock, validate, pack
integrations/claude-desktop/build_mcpb.sh --smoke    # also start the server once and compare its tools
integrations/claude-desktop/build_mcpb.sh --no-lock  # offline build, no uv.lock
```

Output: `dist/ragbase-shield-<version>.mcpb` (`dist/` is gitignored).

What the script does:

1. Copies `src/ragbase_shield` to `<bundle>/src/ragbase_shield` and [`server.py`](server.py) to
   `<bundle>/src/server.py` (a launcher that runs the same server as `ragbase-shield mcp`).
2. Writes `manifest.json` (version taken from `pyproject.toml`) and a dependencies-only `pyproject.toml`
   (`[tool.uv] package = false`), plus `.mcpbignore`.
3. Runs `uv lock` so every install resolves the same versions.
4. Runs `npx -y @anthropic-ai/mcpb validate` then `npx -y @anthropic-ai/mcpb pack`.

Needs bash, Python 3.11+ (or the repo `.venv`), Node.js for `npx`, and uv. To test the bundle by hand:
`uv run --directory dist/mcpb-build/ragbase-shield src/server.py` (stdio, waits for an MCP client).

Before a release: install the `.mcpb` on a clean macOS and a clean Windows machine and run the
`ragbase-shield verify` paths. If the uv runtime fails on a platform, the fallback is a self-contained
binary (`server.type: "binary"`).

## Files

- [`manifest.json`](manifest.json): MCPB manifest, `manifest_version` 0.4 (the first version with `uv`).
- [`server.py`](server.py): launcher copied into the bundle.
- [`build_mcpb.sh`](build_mcpb.sh): build script.
- `icon.png`: 512 x 512, drawn by [`../assets/make_icons.py`](../assets/make_icons.py).
