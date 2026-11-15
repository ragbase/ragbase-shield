# Security policy

RAGbase Shield protects client data. We treat any path that lets a real value reach a model as a serious bug.

**En français :** pour signaler une faille, n'ouvrez pas de ticket public. Utilisez le signalement privé
décrit ci-dessous. N'envoyez jamais de vraies données de client : utilisez des données inventées.

## Supported versions

| Version | Security fixes |
|---|---|
| 0.4.x | Yes |

## How to report a vulnerability

- Use GitHub private vulnerability reporting on the RAGbase Shield repository
  (Security tab > "Report a vulnerability"): https://github.com/ragbase/ragbase-shield/security/advisories/new
- Do not open a public issue, pull request or discussion for a vulnerability.
- Use synthetic data only. Never include real client names, documents, vault files or keys.
- Include: the Shield version (`ragbase-shield doctor`), your OS, the app (Claude Desktop, Claude Code, ChatGPT
  desktop, Codex, VS Code, Desk, browser extension), the steps, and what leaked (kind and code, not the value).

We aim to acknowledge a report within 7 days, and to agree a disclosure date with you once a fix is ready.
We credit reporters in the CHANGELOG unless they ask us not to.

## What counts as a vulnerability

Report it privately if you find any of these:

- A vault value (real name or identifier) in an MCP tool result, a tool error, a hook output, a log line or the journal.
- A way for a model to obtain real values from Shield (Shield has no unmask tool by design).
- A tool that returns raw text when the engine, the vault or a document reader fails (Shield must fail closed).
- A raw dossier title, folder path or real file name shown to a model.
- Shield Desk reachable from another host, from a page without the token, or through a Host header other than
  `127.0.0.1:<port>` or `localhost:<port>`.
- A CORS bypass on the Desk API (CORS is allowed only for `chrome-extension://*` and `moz-extension://*` with a
  valid token).
- The browser extension writing restored real values into the provider's page.
- Real values readable from vault files without the key, or a key file not limited to its owner (mode 0600).
- A network call from library code.
- Codes derived from the value (for example a hash), or a restore that maps a code to the wrong value.
- `ragbase-shield verify` printing CLEAN while a path leaks.

## Not a vulnerability (but please tell us in a normal issue, with synthetic data)

- A name or identifier the detector misses. Detection is never complete. Send a synthetic example.
- Facts, dates or amounts that identify a client. Shield does not mask facts by design.

## Out of scope

- Text the user types, pastes or attaches directly into an AI app. It reaches the provider before Shield runs.
- Malware, or another person with access to the user's unlocked session.
- The AI provider's retention and use of masked text.
- Weaknesses in a third-party app (Claude, ChatGPT, Copilot, VS Code, a browser).

## Security design in short

- Mask before the model. No MCP tool takes raw client text as input; tools take dossier and document codes and
  read files locally.
- No vault value in any tool output, error, hook output or log line. An automated leak test runs every MCP tool and
  hook on every fixture.
- Vault: one SQLite file per dossier, real values encrypted with Fernet (`cryptography`). The key is in the OS
  keychain (`keyring`), or in a 0600 file when no keychain exists. Dossier titles and folder paths are encrypted.
- Desk: 127.0.0.1 only, Host header check, per-install token (`<home>/desk_token`, mode 0600).
- MCP server: stdio only.
- No telemetry. `opentelemetry-api` is installed as a dependency of the `mcp` SDK, but Shield installs no
  OpenTelemetry SDK or exporter and configures none.
- No GPL or AGPL dependency. The runtime dependencies declare MIT, MIT-0, MIT-CMU, BSD, Apache-2.0 or PSF
  licences. The lxml binary wheels bundle GNU libiconv (LGPL-2.1), as lxml's own licence notice states. Desktop
  installers: [packaging/README.md](packaging/README.md), section "Licences of what ships".

Full model: [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md). Contract: [ARCHITECTURE.md](ARCHITECTURE.md).

## Hardening tips for firms

- Turn on full-disk encryption (FileVault on macOS, BitLocker on Windows).
- Lock the screen when you leave the computer.
- Keep Shield up to date: run the newer `.pkg` or `.msi`. With uv, first paste the uv line for your computer (Mac
  or Windows) from the [README](README.md#install), section Install. If uv is already on your computer, paste this
  line anyway: it updates uv. Then run
  `uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl`.
- Do not share `desk_token`, vault files or exports. Send an export passphrase through a separate channel.
- Run `ragbase-shield verify` after each update and keep the CLEAN result with your AI usage records.
