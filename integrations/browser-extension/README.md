# RAGbase Shield browser extension (Chrome and Edge, Manifest V3)

Masks client text **when you paste or drop it** into an AI chat, before the page sees it, and restores the real
names **only in the extension's side panel**. It works with Shield Desk running on your computer.

Sites: `chatgpt.com`, `claude.ai`, `copilot.microsoft.com`, `m365.cloud.microsoft`, `gemini.google.com`.

The extension is not in the Chrome Web Store or Edge Add-ons yet: load it unpacked (see below). After you
paste, check that the prompt box shows codes before you send.

## How it works

1. You paste into the prompt box (textarea, input or rich editor).
2. `content.js` stops the paste before the page gets it and sends the text to `background.js`.
3. `background.js` calls `POST http://127.0.0.1:<port>/api/mask` with the header `X-Shield-Token`.
4. `content.js` inserts the **masked** text and shows a small badge:
   "RAGbase Shield: texte masqué (n éléments)".
5. If Shield Desk is not reachable (or the token is missing or wrong), **nothing is pasted**. A panel says
   "Shield Desk n'est pas lancé" with two buttons: "Coller quand même (non masqué)" and "Annuler".
6. To read an answer with the real names: click the extension icon to open the **side panel**, choose
   the dossier, paste the answer, click **Restaurer les noms**, then **Copier**. The restored text stays in
   the side panel. The extension never writes it into the provider page.

Privacy rules in the code:

- `content.js` can only ask for `shield:mask` and `shield:openOptions`. `background.js` refuses
  `shield:restore`, `shield:dossiers` and `shield:status` from provider pages (checked by sender URL).
- Only trusted (real user) paste events are handled, so a page script cannot use the extension to probe
  the vault.
- The only network peer is `http://127.0.0.1`. No external libraries, no telemetry, no remote code.
- The token, port, on/off switch and dossier code live in `chrome.storage.local` in this browser.

Permissions: `storage`, `sidePanel`, host permission `http://127.0.0.1/*` only. The five chat sites are
covered by the content script `matches` (the install warning is the same as with host permissions, and
the extension gets no other access to those sites).

Not covered: text you **type** goes out as typed. A file pasted or dropped on the page is stopped, and
"Attach anyway" sends it unmasked. Use Shield Desk (**Fichiers** page) for files.

## Install (unpacked, developer mode)

1. Start Shield Desk with uv. uv is the open-source tool that downloads and runs Shield.

   On a Mac: open the Terminal app, paste this line, press Enter.

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   On Windows: open PowerShell, paste this line, press Enter.

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   If uv is already on your computer, paste this line anyway: it updates uv.

   Close the window and open a new one. Then install the `ragbase-shield` command once, from the wheel of the
   release, and start Shield Desk:

   ```sh
   uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
   ragbase-shield desk
   ```

   To start Shield Desk without installing the command:
   `uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk`.
   Copy the token that Shield Desk shows (it is stored in the `desk_token` file of the Shield data folder).
2. Chrome: open `chrome://extensions`. Edge: open `edge://extensions`.
3. Turn on **Developer mode**, click **Load unpacked**, choose this `browser-extension` folder.
4. The options page opens. Paste the token, click **Tester la connexion**, choose the dossier.
5. Paste client text into one of the five sites: the masked text appears with the badge.

## Files

| File | Role |
|---|---|
| `manifest.json` | Manifest V3; default locale `fr` |
| `background.js` | Service worker: the only code that calls the Desk API |
| `content.js` | Paste interception, masked insertion, badge, blocked-paste panel (closed shadow DOM) |
| `options.html`, `options.js` | Token, port, on/off, dossier |
| `sidepanel.html`, `sidepanel.js` | Restore names, copy |
| `common.js`, `ui.css` | Shared page helpers and style (light and dark) |
| `_locales/fr`, `_locales/en` | All user-facing strings |
| `icons/` | 16, 32, 48, 128 px, drawn by [`../assets/make_icons.py`](../assets/make_icons.py) |

To package for the stores: zip the contents of this folder (no build step).
