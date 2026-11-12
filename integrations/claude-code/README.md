# RAGbase Shield plugin for Claude Code and Cowork

The plugin adds three things:

1. **MCP server** ([`plugin/.mcp.json`](plugin/.mcp.json)): `uvx ragbase-shield==0.4.0 mcp`, the 6 Shield tools.
2. **Skill** ([`plugin/skills/ragbase-shield/SKILL.md`](plugin/skills/ragbase-shield/SKILL.md)), French
   and English: list dossiers, read through Shield tools only, never ask for or type real names, work with
   codes, save with `shield_save_draft`, tell the user the restored file is in `Shield - sorties`.
3. **Hooks** ([`plugin/hooks/hooks.json`](plugin/hooks/hooks.json)):

| Event | Matcher | Command | Effect |
|---|---|---|---|
| `UserPromptSubmit` | (none: every prompt) | `uvx ragbase-shield==0.4.0 hook user-prompt-submit` | blocks a prompt that contains a registered value and names the code to use |
| `PreToolUse` | built-in tools: `Read`, `Grep`, `Glob`, `LS`, `LSP`, `Bash`, `PowerShell`, `Monitor`, `Edit`, `MultiEdit`, `Write`, `NotebookRead`, `NotebookEdit`, `Artifact`, `SendUserFile` (exact list: [`hooks.json`](plugin/hooks/hooks.json)) | `uvx ragbase-shield==0.4.0 hook pre-tool-use` | denies direct reads inside a registered dossier folder (and uploads of its files), access to Shield's own data and Desk, and the Shield commands that print real values or change the vault; points to `shield_read_document` |
| `PreToolUse` | `mcp__.*` (other MCP servers; Shield's own tools are skipped) | `uvx ragbase-shield==0.4.0 hook pre-tool-use` | denies a file tool of another MCP server (for example `mcp__filesystem__read_file`) on a dossier folder |
| `PostToolUse` | (none: every tool) | `uvx ragbase-shield==0.4.0 hook post-tool-use` | replaces a registered value left in a tool result (text or number) with its code; a result too large to check in time is blanked and the session stops |

The marketplace file is at the repo root: [`/.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)
(marketplace `ragbase`, plugin `ragbase-shield`, source `./integrations/claude-code/plugin`).

Status: `claude plugin validate` **passes** for the marketplace and the plugin (Claude Code 2.1.220).
**Not installed end to end** yet.

## Install

In Claude Code:

```text
/plugin marketplace add ragbase/ragbase-shield
/plugin install ragbase-shield@ragbase
```

Then run `/reload-plugins` or restart Claude Code.

In the Claude app (Cowork): **Customize > Plugins > Add > Add marketplace**, enter `ragbase/ragbase-shield`,
then add **RAGbase Shield**. The MCP server is marked "Runs in each session": it runs on your computer, in
Claude Code and in Cowork sessions on your computer, not in plain chat. For plain chat in Claude Desktop,
use the `.mcpb` extension ([`../claude-desktop/`](../claude-desktop/)).

The plugin pins the package version (`ragbase-shield==0.4.0`), as Anthropic's plugin directory requires for
`uvx`. At each release, raise the pin in `.mcp.json` and `hooks/hooks.json` and the `version` in `plugin.json`
together. The plugin folder has its own [`README.md`](plugin/README.md) (the directory listing text).

Needs uv (`uvx`) on the `PATH` seen by Claude Code, and the `ragbase-shield` package (`uvx` fetches it from PyPI; from a copy of the repository,
`uv tool install .` once, and `uvx` then uses that install). The first prompt after
install can take a few seconds: `uvx` prepares the package once. Each hook has a 60-second timeout; Shield
answers within about 40 seconds and fails closed past that (a very large prompt is blocked, a very large tool
result is blanked). A hook call costs about 0.1 to 0.3 s on a laptop, plus the OS keychain access when the
vault key is in the keychain.

## Local development

```sh
uv tool install --editable /path/to/ragbase-shield   # every "uvx ragbase-shield ..." now uses the checkout
claude --plugin-dir /path/to/ragbase-shield/integrations/claude-code/plugin
claude plugin validate /path/to/ragbase-shield                       # marketplace
claude plugin validate /path/to/ragbase-shield/integrations/claude-code/plugin
```

## Notes

- If a hook cannot start (for example `uvx` missing), Claude Code treats it as a non-blocking error and the
  action goes ahead. Claude Code 2.1.295 and later can fail closed with `"onFailure": "block"` on a hook.
  It is not set because older Claude Code versions do not know the field. Run
  `ragbase-shield doctor` to check the install.
- The hooks are a second line of defence. The first is the workflow: connect folders, read through the
  Shield tools, never paste raw client text.
