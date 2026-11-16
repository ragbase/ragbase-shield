# RAGbase Shield

<!-- mcp-name: io.github.ragbase/ragbase-shield -->

**Use Claude on your client files, without leaking any sensitive information.**

The best pseudonymisation engine on the market.

RAGbase Shield 0.4.1 is a free, open-source tool (Apache-2.0).
On your own computer, it replaces your clients' names and numbers with codes before the text goes to Claude.
When Claude answers, Shield puts the real names back, also on your computer.
The law stays readable: articles, courts, dates and amounts stay in clear, so Claude can do the work.

This is **local, reversible pseudonymisation**.
It is not anonymisation: facts, dates and amounts stay readable by the AI.
Nothing goes to RAGbase. Shield sends no usage statistics.

**Do you use the Claude app on a Mac or a PC?** Add the Claude plugin, with nothing else to install: see [Install](#install).

Version française (la version de référence pour les cabinets français) : [README.fr.md](https://github.com/ragbase/ragbase-shield/blob/main/README.fr.md)

Contents:

- [For lawyers: the essentials](#for-lawyers-the-essentials)
- [Install](#install)
- [Daily use](#daily-use)
- [Results](#results)
- [Limits (please read)](#limits-please-read)
- [Privacy model in 5 lines](#privacy-model-in-5-lines)
- [For developers and IT](#for-developers-and-it)
- [Links](#links)
- [Going further](#going-further)

---

## For lawyers: the essentials

### What Shield does

You write or open this text (invented example):

```text
M. Thibault Mercadier, domicilié 12 rue des Glycines, 69007 Lyon, conteste son
licenciement par la société Ateliers Brunelac SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° 25/01234).
Contact : t.mercadier@example.org
```

Claude receives this text:

```text
M. PERSONNE_A, domicilié ADRESSE_1, conteste son
licenciement par la société SOCIETE_A SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° RG_1).
Contact : EMAIL_1
```

This is the real output of Shield 0.4.1 on this example, in Fast mode (the default).
Note what stays readable: the date, the amount, the court. Claude needs them to do the work.
Shield is built for French legal documents first. It also works on English text.
With `RAGBASE_SHIELD_LOCALE=en`, codes use English labels (PERSON_A, COMPANY_A, ADDRESS_1).

Inside one dossier, a person always keeps the same code.
"M. Mercadier", "Thibault Mercadier" and "MERCADIER Thibault" all become PERSONNE_A.

After "M.", "Mme", "Mlle" or "Me", Shield masks the name that follows, with or without capitals, in every French text.
In text typed without capitals, as on a phone or in a quick note, Shield also masks names with or without a title, companies written with their legal form, postal addresses and the fields "nom :" and "prénom :".
The setting RAGBASE_SHIELD_LOWERCASE_NAMES=0 turns these rules off.

### Three rules to remember

1. **Connect a folder. Do not attach the file to the chat.**
   A file attached to a chat reaches the AI provider before Shield can act.
   Add the case folder to Shield. The AI then reads the documents through Shield, masked.
2. **Do not paste raw text into the chat box.**
   Go through Shield first (the "Masquer" page in Shield Desk, or the browser extension).
   To talk about a person in the chat, write their code (PERSONNE_A), not their name.
3. **Text already sent cannot be recalled.**
   Shield protects only what goes through it. If a name was sent by mistake, Shield cannot undo it.

### What reaches the AI provider, what stays with you

| Reaches the AI provider (Anthropic, OpenAI, Microsoft) | Stays on your computer |
|---|---|
| Masked text with codes (PERSONNE_A, SOCIETE_A, IBAN_1) | Real names and real numbers |
| Facts, dates (except dates of birth), amounts, legal reasoning | The code-to-name table (the "vault"), encrypted |
| Courts, laws and articles cited | The vault encryption key |
| The dossier code (DOSSIER_1) and masked file names | The real dossier name and folder path |
| Your question | The local journal (events, codes and counts only) |

Details: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/PRIVACY_MODEL.md).

### Codes

| What is masked | Code (French labels, default) |
|---|---|
| Person | PERSONNE_A, PERSONNE_B, ... |
| Company | SOCIETE_A, ... |
| Postal address | ADRESSE_1, ... |
| Email, phone | EMAIL_1, TEL_1 |
| IBAN, payment card | IBAN_1, CARTE_1 |
| French social security number (NIR) | NIR_1 |
| SIREN, SIRET, EU VAT number | SIREN_1, SIRET_1, TVA_1 |
| Case references (RG, pourvoi, Portalis, ECLI) | RG_1 |
| Other identifiers (ISIN, LEI, passport, licence plate, IP address) | IDENT_1 |
| Websites and URLs (except well-known public sites) | SITE_1 |
| Date of birth | NAISSANCE_1 |

Shield does not mask courts, institutions (Cour de cassation, CNIL, URSSAF...), laws, codes,
articles, months and days.

---

## Install

**The simplest way, in the Claude app on a Mac or a PC: the Claude plugin.** It carries the whole Shield engine:
nothing else to install (no uv, no Python, no Terminal, no installer). In the Claude app, on the **Claude** tab (not
the Code tab), open **Customize > Plugins > Add > Add marketplace > Add from a repository**.
Type `ragbase/ragbase-shield-mac` (Mac) or `ragbase/ragbase-shield-windows` (Windows) and click **Sync**.
Then, in the **Discover** tab, click **Add** next to "RAGbase Shield (Mac)" or "RAGbase Shield (Windows)".
Or use the button for your system on [shield.ragbase.ai](https://shield.ragbase.ai).
Use and limits: [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md#the-claude-plugin-claude-app-mac-and-windows).

Downloads (installers, Claude Desktop extension, `SHA256SUMS`): the releases page,
https://github.com/ragbase/ragbase-shield/releases/latest. Python package: the wheel of the release (commands below).

| Your app or system | What to install | Guide |
|---|---|---|
| Claude app on a Mac or a PC (Claude tab) | The Claude plugin, nothing else to install: add `ragbase/ragbase-shield-mac` or `ragbase/ragbase-shield-windows` (steps above) | [Mac plugin](https://github.com/ragbase/ragbase-shield-mac), [Windows plugin](https://github.com/ragbase/ragbase-shield-windows), [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md#the-claude-plugin-claude-app-mac-and-windows) |
| Mac (macOS 13 or later) | `RAGbase-Shield-0.4.1.pkg`: double-click, installs for you only (designed to need no administrator password), no Terminal. Not signed yet: macOS asks you to confirm the first time | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), section 0 |
| Windows 10 or 11 | `RAGbase-Shield-0.4.1-win64.msi`: per-user install (designed to need no administrator rights). Not signed yet: SmartScreen asks you to confirm | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), section 0 |
| Claude Desktop, other way (`.mcpb` extension) | `ragbase-shield-0.4.1.mcpb`: double-click, then "Install". In the Claude app, the Claude plugin (first row) is simpler | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), section 2 |
| Claude Code | Plugin: `/plugin marketplace add ragbase/ragbase-shield`, then `/plugin install ragbase-shield@ragbase`. Not for the Claude tab of the Claude app: it needs uv, and its hooks can stop every message there. Use the Claude plugin there | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), section 3 |
| ChatGPT desktop and Codex, GitHub Copilot in VS Code | `ragbase-shield install chatgpt` (or `codex`, `vscode`), once the command is installed with uv (commands below) | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), sections 4 and 5 |
| Any web app (claude.ai, chatgpt.com, Copilot web) | Shield Desk, and the browser extension for Chrome and Edge (not in the stores yet: load the folder `integrations/browser-extension` in developer mode) | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md), sections 6 and 7 |
| Terminal, with uv or pip | Shield Desk with uv, or the package with pip | below |

**With uv.** uv is the open-source tool that downloads and runs Shield.

On a Mac: open the Terminal app, paste this line, press Enter.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows: open PowerShell, paste this line, press Enter.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If uv is already on your computer, paste this line anyway: it updates uv.

Close the window and open a new one. Then install the `ragbase-shield` command once, from the wheel of the release,
and start Shield Desk:

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield desk
```

Your browser opens **http://127.0.0.1:7878** with a private link that holds a secret token.
This is a local page: it works only on your computer.
To open it again, run `ragbase-shield desk` again or use the link shown in the Terminal.
The address alone, without the token, shows "Token refused".
Keep the Terminal window open: closing it stops Shield Desk and the browser extension.

To start Shield Desk without installing the command:

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk
```

**With pip:** install the wheel of the release, then start Shield Desk.

```sh
pip install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield desk
```

Precise mode (with AI model) is optional (see [docs/NER.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/NER.md)). With uv:

```sh
uv tool install --python 3.12 "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
```

On a Mac with an Intel processor, use this line:

```sh
uv tool install --python 3.12 --with "numpy<2" --with "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
```

With pip:

```sh
pip install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
```

On a Mac with an Intel processor, use this line:

```sh
pip install "numpy<2" "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
```

On a Mac, the first use may ask for keychain access for the Shield key: click "Always Allow".

---

## Daily use

### With the Claude plugin (Claude app)

1. In a conversation, write: "Protège un dossier avec Shield" (or "Protect a folder with Shield"). A RAGbase Shield
   window opens on top of Claude: click in it and choose the folder of one client (2,000 files or 2 GB at most).
   Shield reads and masks the whole folder on your computer: a large folder takes some minutes. Claude only gets a
   code, for example `DOSSIER_1`.
2. Ask for your work, for example: "Draft a formal notice". Claude reads the documents with the codes.
3. Write: "Save the final document with Shield". Shield puts the real names back on your computer, in the
   "Shield - sorties" folder of the client folder.

Text you type in the conversation, and a file you drop directly into it, are not masked by the plugin.

### With Claude Desktop and Claude Code

1. In Shield Desk, on the **Dossiers** page, under "Ajouter un dossier" (Add a folder), type the full path of
   the client's case folder, then click "Ajouter et analyser" (Add and scan).
   Shield gives it a code (DOSSIER_1) and reads the documents. The Desk has an EN toggle for English labels
   (tabs: Matters, Mask, Restore, Files, Log).
   To copy a folder path: on a Mac, in the Finder, hold Option and right-click the folder, then
   "Copy ... as Pathname"; on Windows, Shift + right-click, then "Copy as path".
2. Click "Voir les entités" (Show entities) to see the detected names. Add the missing ones with "Add a name or
   a term", above the list: the client, the parties, a project name. Turn on the "Keep in clear" switch for a
   name that must stay readable.
3. In Claude, ask for example:
   "List my Shield dossiers. Read the documents of DOSSIER_1 and draft submissions. Save the draft with Shield."
4. Claude sees only codes. It saves the draft with the Shield tool.
5. Shield writes the document, with the real names, into the **"Shield - sorties"** subfolder
   of the case folder. Open it on your computer and review it.

Claude cannot ask Shield for the real names. Only your computer puts them back.
The same steps work in ChatGPT desktop, Codex and GitHub Copilot in VS Code.

### With any other app, through Shield Desk

For claude.ai, chatgpt.com, Microsoft 365 Copilot, Word and Outlook.

1. Open Shield Desk with the link that its command shows (see Install), page **Masquer** (Mask). Choose the
   dossier. Without a dossier, registered names become [PERSONNE] or [SOCIETE] and restore is not possible.
2. Paste your text into the original-text box (not into the chat), then click "Masquer" (Mask).
3. Check the detected items, then click "Copier le texte masqué" (Copy masked text).
4. Paste the masked text into the AI app.
5. Copy the AI's answer. In Shield Desk, page **Restaurer** (Restore), paste it and click
   "Restaurer les noms" (Restore names). Shield also lists codes it does not know in this dossier
   (for example a code the AI invented). Copy the restored text into your document.
   Never paste it back into the chat: it contains the real names.

From a terminal, the same in two commands:
`ragbase-shield mask --dossier DOSSIER_1 --clipboard` replaces the clipboard with the masked text.
`ragbase-shield restore --dossier DOSSIER_1 --clipboard` puts the real names back into the clipboard.

---

## Results

Masking everything is easy, but then Claude cannot do the work. Shield masks your clients' data and keeps the law
readable. We measured Shield against Hexagone and Presidio on four French benchmarks, all public.

| | Shield 0.4.1 Fast | Shield 0.4.1 Precise | Hexagone 0.3.9 Fast | Hexagone 0.3.9 Precis | Presidio 2.2.364 |
|---|---|---|---|---|---|
| **Overall score (F1), higher is better** | | | | | |
| FR-PII-Bench | **96.9** | 96.2 | 80.7 | 80.7 | 66.5 |
| MAPA | 80.4 | **82.2** | 43.8 | 37.9 | 63.5 |
| REF | **97.1** | **97.1** | 66.7 | 61.1 | 79.2 |
| Max | **95.3** | 91.8 | 54.0 | 48.9 | 47.4 |
| **Legal terms changed, lower is better** | | | | | |
| MAPA | **0.0 %** | **0.0 %** | 43.1 % | 47.6 % | 18.0 % |
| REF | **4.1 %** | **4.1 %** | 17.8 % | 47.1 % | 15.3 % |
| Max | **2.1 %** | 4.2 % | 47.2 % | 58.3 % | 55.6 % |
| **Speed and memory, lower is better** | | | | | |
| Time for one document | **0.61 s** | 17.7 s | 26.93 s | 9 min | 1.59 s |
| Peak memory | **78 to 79 MB** | 3.7 to 3.8 GB | 1.6 to 1.7 GB | 3.8 to 5.4 GB | 0.57 GB |

Fast is the default mode. Precise adds an AI model that runs on your computer. The best value of each row is in bold.

Method and detailed results: [evaluation/laptop/RESULTS_PUBLIC.md](https://github.com/ragbase/ragbase-shield/blob/main/evaluation/laptop/RESULTS_PUBLIC.md).

REF and Max, with their answer keys and one command that reproduces the Shield and Presidio results: [evaluation/datasets](https://github.com/ragbase/ragbase-shield/tree/main/evaluation/datasets).

---

## Limits (please read)

- **The Claude plugin masks only the folder chosen in its window.** Text you type, or a file you drop directly
  into the conversation, is sent as it is. 2,000 files or 2 GB at most per folder.
- **No OCR.** A scanned PDF (an image) has no text. Shield says so and does not read it.
- **Detection is never complete.** A name nobody registered can slip through:
  a rare name, a foreign name, a nickname, a typo. Register the parties of each dossier.
  Those are the names Shield masks most reliably. Check the list of detected names, and read the masked text
  before you send it.
- **Restored names use the spelling stored in the dossier.** "M. Mercadier" can come back as
  "M. Thibault Mercadier", and capital letters can change. Identifiers come back in the first spelling seen in
  the dossier (for example "832 456 719" for "832456719"). Re-read the restored document.
- **Facts can still identify a client**, even without a name: a well-known case, a unique job title,
  a precise place, an amount. Shield does not mask facts. Review, and generalise when needed.
- **ChatGPT web (chatgpt.com) has no native connection.** Use Shield Desk or the browser extension.
- **Microsoft 365 Copilot (Word, Outlook, Teams, the Copilot app): through Shield Desk only.**
  Warning: Copilot in Word or Outlook reads the open document or email. Open a masked copy, not the original.
- **The browser extension masks text you paste or drop.** Text you type goes out as typed. A file pasted or
  dropped into the chat is blocked; "Attach anyway" sends it unmasked. It is not in the Chrome or Edge stores yet.
- **The installers are not signed yet.** macOS and Windows show a warning the first time.
- **An administrator can block Shield**: extensions in Claude Team or Enterprise,
  MCP servers in Copilot Business or Enterprise.
- **The GDPR still applies.** For you, pseudonymised data are still personal data. Shield reduces what the AI
  provider receives. It is not a conformity guarantee.

French compliance sheet (CNB, Paris bar, avocats aux Conseils, GDPR): [docs/CONFORMITE.fr.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/CONFORMITE.fr.md)
FAQ: [docs/FAQ.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/FAQ.md)

---

## Privacy model in 5 lines

1. Masking and restoring run on your computer. The AI provider receives codes, never the real names that Shield
   detected or that you registered.
2. The code-to-name table (the vault) is encrypted, one per dossier; its key stays in the OS keychain (or a file
   only you can read).
3. No tool gives real names to the model, and an AI agent cannot change what is masked.
4. No network call in the library, no telemetry, no update check. The only download, which you start yourself, is
   the optional AI model of Precise mode.
5. Pseudonymised data are still personal data: Shield reduces what the provider sees. It is pseudonymisation,
   not anonymisation.

Full model: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/PRIVACY_MODEL.md).

---

## For developers and IT

### Architecture in short

- **Fast mode** (the default; technical name: rules). A local engine of rules, dictionaries and check digits finds
  names and identifiers, in French and in English (the language is detected per text, or pinned with
  `RAGBASE_SHIELD_LANGUAGE`).
- **Precise mode** (optional; technical name: GLiNER). An AI model for name recognition works next to the rules.
  It takes about 1.2 GB, has an Apache-2.0 licence and runs offline, on the CPU. No model is installed by default.
  To add it with pip:

  ```sh
  pip install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  ```

  On a Mac with an Intel processor, use this line:

  ```sh
  pip install "numpy<2" "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  ```

  or with uv:

  ```sh
  uv tool install --python 3.12 "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  ```

  On a Mac with an Intel processor, use this line:

  ```sh
  uv tool install --python 3.12 --with "numpy<2" --with "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  ```

  Then download the model once (fastino/gliner2-privacy-filter-PII-multi, into `~/.ragbase-shield/models`) and check
  it (`ragbase-shield doctor` checks it too):

  ```sh
  ragbase-shield ner download
  ragbase-shield ner status
  ```

  What the model finds passes the same whitelist and precision guards as the rules; the hooks and the canary never
  use it. `RAGBASE_SHIELD_NER=off` turns it off.
- Replacement by codes (`PERSONNE_A`) by default, or by realistic pseudonyms (`ragbase-shield set DOSSIER_n
  --replacement synthetic`): reversible through the vault, pseudonymisation, not anonymisation.
- One encrypted vault per dossier (SQLite + Fernet). The key lives in the OS keychain,
  or in a file only you can read (mode 0600).
- A local MCP server (stdio) for Claude, ChatGPT desktop, Codex and VS Code.
  Its tools take dossier and document codes, never raw text. No tool gives real names to the model.
- Shield Desk: a local web page on 127.0.0.1, with a per-install token.
- Claude Code hooks block a prompt that contains a registered name, and direct reads of a dossier folder.
- No network calls in library code. No telemetry.

Full contract: [ARCHITECTURE.md](https://github.com/ragbase/ragbase-shield/blob/main/ARCHITECTURE.md). Privacy model: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/PRIVACY_MODEL.md).

### Command line

```text
ragbase-shield add <folder> [--title TEXT]           # register a dossier folder, prints DOSSIER_n, scans it
ragbase-shield list                                  # dossiers (real titles: local terminal)
ragbase-shield entities <DOSSIER_n>                  # detected and registered entities
ragbase-shield register <DOSSIER_n> --person NAME | --org NAME | --kind KIND VALUE
ragbase-shield keep-clear <DOSSIER_n> <CODE> [--off]
ragbase-shield mask [--dossier D] [--clipboard] [--mode codes|synthetic] [FILE|-]   # prints masked text, or replaces the clipboard
ragbase-shield set <DOSSIER_n> --replacement codes|synthetic [--language auto|fr|en]  # per-dossier settings
ragbase-shield ner status | download [--model fastino|urchade|all] [--dir DIR] [--dry-run] [--force]  # optional NER model
ragbase-shield restore --dossier D [--clipboard] [FILE|-]     # prints restored text, or replaces the clipboard
ragbase-shield desk [--port 7878] [--no-browser]
ragbase-shield mcp                                   # stdio MCP server (used by every app integration)
ragbase-shield hook <user-prompt-submit|pre-tool-use|post-tool-use>   # Claude Code hooks, JSON stdin/stdout
ragbase-shield install <claude-desktop|claude-code|chatgpt|codex|vscode> [--dry-run]
ragbase-shield doctor                                # checks install, key storage, each app integration
ragbase-shield verify                                # plants synthetic data, runs every path, prints CLEAN or LEAK
ragbase-shield export <DOSSIER_n> <FILE> / import <FILE>      # encrypted vault handoff (passphrase prompt)
ragbase-shield journal [DOSSIER_n]
```

With uv, install the command once, from the wheel of the release:

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
```

Or run one command without installing it:

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield doctor
```

From a copy of the repository: `uv tool install .` (or `uv tool install --editable .` to develop).
The configs written by `install` then work, and `doctor` checks that each app can start Shield.

From an AI agent's terminal (Claude Code, Codex), `entities`, `restore` and `export` refuse to run, because
what they print reaches the model. `add`, `register`, `keep-clear` and `import` refuse too: an AI assistant
cannot change what is masked. `list` shows codes only. Run these commands in your own terminal, or use
Shield Desk.

### Supported apps

| App | How Shield plugs in |
|---|---|
| Claude app (Claude tab), Mac and Windows | The Claude plugin: engine inside the plugin, local MCP server with 7 tools, skill, no hooks |
| Claude Desktop, other way (`.mcpb` extension) | One-click extension (`.mcpb`) that runs the local MCP server |
| Claude Code | Plugin: MCP server + skill + hooks |
| ChatGPT desktop and Codex | Local MCP server (`~/.codex/config.toml`), where local MCP is allowed |
| GitHub Copilot (VS Code) | Local MCP server (`mcp.json`) |
| Any other app (claude.ai, chatgpt.com, Copilot, Word, Outlook) | Shield Desk, clipboard, browser extension |

### Check it yourself

- `ragbase-shield doctor` checks the install, key storage and each app integration.
- `ragbase-shield verify` plants invented data, runs every path (MCP tools, hooks, Desk) and prints CLEAN or LEAK.
- Tests: `uv run --extra dev pytest -q`. Synthetic data only.
- Regression bench: `uv run python bench/run_bench.py` (recall and precision per kind, on an invented French legal
  corpus).
- Benchmark runners: `evaluation/public/` (public benchmarks; data downloaded into the git-ignored
  `.bench_data/`), `evaluation/holdout-en/` (an invented English corpus), `evaluation/laptop/` (the benchmark
  scripts and results), `evaluation/datasets/` (the REF and Max benchmarks, with their answer keys).
- Desktop installers: [packaging/README.md](https://github.com/ragbase/ragbase-shield/blob/main/packaging/README.md).

### Environment variables

| Variable | Effect |
|---|---|
| `RAGBASE_SHIELD_HOME` | Data folder (default `~/.ragbase-shield`, or `%LOCALAPPDATA%\ragbase-shield` on Windows) |
| `RAGBASE_SHIELD_LOCALE=en` | English code labels (PERSON_A, COMPANY_A) instead of PERSONNE_A, SOCIETE_A |
| `RAGBASE_SHIELD_PORT` | Shield Desk port (default 7878) |
| `RAGBASE_SHIELD_KEYRING=0` | Key in a 0600 file instead of the OS keychain |
| `RAGBASE_SHIELD_MASK_TOQUE=0` | Keeps lawyers' "toque" numbers visible (masked by default) |
| `RAGBASE_SHIELD_LOWERCASE_NAMES=0` | Turns off the rules for names in lower case after a title and for text typed without capitals (on by default) |

### Contributing, security, licence

- Security issues: [SECURITY.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.1/SECURITY.md). Do not open a public issue.
- Release history: [CHANGELOG.md](https://github.com/ragbase/ragbase-shield/blob/main/CHANGELOG.md).
- Licence: [Apache-2.0](https://github.com/ragbase/ragbase-shield/blob/v0.4.1/LICENSE). Attributions: [NOTICE](https://github.com/ragbase/ragbase-shield/blob/v0.4.1/NOTICE). Benchmark sets in `evaluation/datasets`: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Test data: invented only. Never put real client data in an issue.

---

## Links

- Source code: https://github.com/ragbase/ragbase-shield
- Releases (installers, `.mcpb`, `SHA256SUMS`): https://github.com/ragbase/ragbase-shield/releases/latest
- Issues: https://github.com/ragbase/ragbase-shield/issues
- Product page: https://shield.ragbase.ai
- Install guide per app: [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/INSTALL.md). FAQ: [docs/FAQ.md](https://github.com/ragbase/ragbase-shield/blob/main/docs/FAQ.md).
- Public results: [evaluation/laptop/RESULTS_PUBLIC.md](https://github.com/ragbase/ragbase-shield/blob/main/evaluation/laptop/RESULTS_PUBLIC.md)

---

## Going further

Shield reduces what the AI sees. It does not replace an AI that runs on your own machines.
If your firm wants a private AI installed on its own hardware, RAGbase offers one:
https://ragbase.ai
