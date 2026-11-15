# RAGbase Shield with Microsoft 365 Copilot, Word, Outlook and the Copilot app

There is no native Copilot connector, by design. This folder is a guide.

## Why there is no connector

Microsoft 365 Copilot connects to tools through **remote** servers (declarative agents, remote MCP
servers, Graph connectors) that run in the cloud. Such a server would receive the clear text before
masking it. That breaks the Shield rule: real data is masked on your computer, before any model sees it.
So Shield uses three local paths instead.

## 1. Shield Desk (any Copilot: web, app, Teams, Word, Outlook)

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

It opens a local page on `http://127.0.0.1:7878`. To start Shield Desk without installing the command:
`uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk`.

1. **Masquer**: choose the dossier, paste the client text, check the detected entities, click copy.
2. Paste the masked text into Copilot. Copilot sees codes such as `PERSONNE_A`, `SOCIETE_B`, `IBAN_1`.
3. Copy Copilot's answer.
4. **Restaurer**: same dossier, paste the answer, copy the text with the real names.
5. Paste it into your Word document or email. Never paste it back into Copilot.

For a whole document: drop the file on the **Fichiers** page, download the **masked copy**, and use
Copilot on that copy only.

**Copilot in Word and Outlook reads the whole open document or email. Never run it on the original
client document: open the masked copy instead.**

## 2. Clipboard commands (fastest in Word and Outlook)

These commands need the `ragbase-shield` command that section 1 installs.

This command replaces the clipboard with the masked text:

```sh
ragbase-shield mask --dossier DOSSIER_1 --clipboard
```

This command replaces the clipboard with the restored text:

```sh
ragbase-shield restore --dossier DOSSIER_1 --clipboard
```

Copy, run the mask command, paste into Copilot. Copy the answer, run the restore command, paste into
your document. You can bind the two commands to keyboard shortcuts (macOS Shortcuts app; on Windows, a
desktop shortcut with a shortcut key).

## 3. Browser extension (Copilot on the web)

The RAGbase Shield extension for Chrome and Edge masks text pasted into `copilot.microsoft.com` and
`m365.cloud.microsoft` through Shield Desk, and restores names only in its side panel. See
[`../browser-extension/`](../browser-extension/). It does not act inside the Word, Outlook or Teams
desktop apps: use the clipboard commands there.

## Planned: a Word add-in

An Office.js add-in served as static HTTPS files, with all masking and restoring inside the add-in (no
server sees the text).

## Rules

- Mask before Copilot: text typed or pasted directly into Copilot has already left your computer.
- Use one dossier per client so codes stay stable and restore works.
- This is pseudonymisation (reversible), not anonymisation. Detection is never complete: check the masked
  text before you send it in sensitive cases.
