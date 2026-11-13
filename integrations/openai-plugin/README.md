# RAGbase Shield: portable plugin for ChatGPT and Codex

Agent Plugins 1.0.0 package (the portable format OpenAI recommends), for the ChatGPT desktop app and Codex.

| File | Content |
|---|---|
| [`plugin.json`](plugin.json) | Root manifest with the Agent Plugins schema; OpenAI display data under `extensions.com.openai` |
| [`mcp.json`](mcp.json) | One stdio server: `uvx ragbase-shield mcp`, `cwd` `${PLUGIN_ROOT}` |
| [`skills/ragbase-shield/SKILL.md`](skills/ragbase-shield/SKILL.md) | Safe workflow, French and English (same file as the Claude Code skill; a test keeps them identical) |
| `assets/icon.png` | 512 x 512 icon |

The repo marketplace that lists it is [`/.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json)
(marketplace `ragbase`, source `./integrations/openai-plugin`, policy `AVAILABLE` / `ON_INSTALL`,
category `Productivity`). Install steps: [`../chatgpt/README.md`](../chatgpt/README.md).

Local test without GitHub:

```sh
codex plugin marketplace add /path/to/ragbase-shield
```

Then restart the ChatGPT desktop app and install from the **RAGbase** source in the Plugins Directory.

The package follows the published Agent Plugins schemas (unit tests check it). A local-MCP plugin is "Desktop
only"; public listing of local-MCP plugins is limited to
partners approved by OpenAI. No lifecycle hooks are bundled (plugins with hooks cannot be listed publicly,
and the Shield hook handlers speak the Claude Code format).
