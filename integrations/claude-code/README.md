# RAGbase Shield plugin for Claude Code and Cowork

The plugin adds three things:

1. **MCP server** ([`plugin/.mcp.json`](plugin/.mcp.json)), the 6 Shield tools:
   `uvx --from ${CLAUDE_PLUGIN_ROOT}/vendor/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield mcp`.
2. **Skill** ([`plugin/skills/ragbase-shield/SKILL.md`](plugin/skills/ragbase-shield/SKILL.md)), French
   and English: list dossiers, read through Shield tools only, never ask for or type real names, work with
   codes, save with `shield_save_draft`, tell the user the restored file is in `Shield - sorties`.
3. **Hooks** ([`plugin/hooks/hooks.json`](plugin/hooks/hooks.json)). Each hook runs
   `uvx --from ${CLAUDE_PLUGIN_ROOT}/vendor/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield hook <event>`
   in exec form: `command` is `uvx` and every other word is one item of `args`, so no shell runs and a plugin
   path with spaces stays one argument.

| Event | Matcher | Command (after the wheel) | Effect |
|---|---|---|---|
| `UserPromptSubmit` | (none: every prompt) | `ragbase-shield hook user-prompt-submit` | blocks a prompt that contains a registered value and names the code to use |
| `PreToolUse` | built-in tools: `Read`, `Grep`, `Glob`, `LS`, `LSP`, `Bash`, `PowerShell`, `Monitor`, `Edit`, `MultiEdit`, `Write`, `NotebookRead`, `NotebookEdit`, `Artifact`, `SendUserFile` (exact list: [`hooks.json`](plugin/hooks/hooks.json)) | `ragbase-shield hook pre-tool-use` | denies direct reads inside a registered dossier folder (and uploads of its files), access to Shield's own data and Desk, and the Shield commands that print real values or change the vault; points to `shield_read_document` |
| `PreToolUse` | `mcp__.*` (other MCP servers; Shield's own tools are skipped) | `ragbase-shield hook pre-tool-use` | denies a file tool of another MCP server (for example `mcp__filesystem__read_file`) on a dossier folder |
| `PostToolUse` | (none: every tool) | `ragbase-shield hook post-tool-use` | replaces a registered value left in a tool result (text or number) with its code; a result too large to check in time is blanked and the session stops |

The marketplace file is at the repo root: [`/.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)
(marketplace `ragbase`, plugin `ragbase-shield`, source `./integrations/claude-code/plugin`).

`claude plugin validate --strict` passes for the marketplace and the plugin (Claude Code 2.1.220 and 2.1.321; on
2.1.321 also with `--profile directory`).

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

The plugin pins the package as Anthropic's plugin directory requires for `uvx`: it ships the wheel of the GitHub
release, [`plugin/vendor/ragbase_shield-0.4.1-py3-none-any.whl`](plugin/vendor/) (same SHA-256 as in the
`SHA256SUMS` file of the release), and runs it with `uvx --from`. A version number alone
(`ragbase-shield==<version>`) is not a pin for the directory.
At each release: put the wheel of the release into `plugin/vendor/` (remove the old one), change the wheel name in
`.mcp.json` and in the 4 hooks of `hooks/hooks.json`, and raise the `version` in `plugin.json`. The tests check
that the wheel, its version and these files agree. The listing icon is
[`plugin/.claude-plugin/icon.png`](plugin/.claude-plugin/icon.png) (512 x 512, drawn by
[`../assets/make_icons.py`](../assets/make_icons.py)). The plugin folder has its own
[`README.md`](plugin/README.md) (the directory listing text).

Needs uv (`uvx`) on the `PATH` seen by Claude Code. The `ragbase-shield` package is in the plugin (the wheel in
`vendor/`); `uvx` installs it and downloads its dependencies from PyPI once. The first prompt after install can
take a few seconds while `uvx` prepares the environment. Each hook has a 60-second timeout; Shield
answers within about 40 seconds and fails closed past that (a very large prompt is blocked, a very large tool
result is blanked). A hook call costs about 0.1 to 0.3 s on a laptop, plus the OS keychain access when the
vault key is in the keychain.

## Local development

The plugin always runs the wheel in `plugin/vendor/`, not a checkout. To try a code change in the plugin, build a
wheel (`uv build --wheel`) and put it in a copy of the plugin folder under the same name; never commit a wheel that
is not the file of the release.

```sh
claude --plugin-dir /path/to/ragbase-shield/integrations/claude-code/plugin
claude plugin validate /path/to/ragbase-shield
claude plugin validate /path/to/ragbase-shield/integrations/claude-code/plugin
```

The second line validates the marketplace, the third line the plugin.

## Notes

- If a hook cannot start (for example `uvx` missing), Claude Code treats it as a non-blocking error and the
  action goes ahead. Claude Code 2.1.295 and later can fail closed with `"onFailure": "block"` on a hook.
  It is not set because older Claude Code versions do not know the field. Run
  `ragbase-shield doctor` to check the install.
- The hooks are a second line of defence. The first is the workflow: connect folders, read through the
  Shield tools, never paste raw client text.
