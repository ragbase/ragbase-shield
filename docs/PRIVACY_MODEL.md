# Modèle de confidentialité / Privacy model

RAGbase Shield 0.4.1. Partie 1 en français, pour les avocats et le DPO.
Part 2 in English, for developers and IT.

---

## Partie 1. En français

### En une phrase

Shield remplace les noms et les numéros par des codes sur votre ordinateur.
Le fournisseur d'IA reçoit le texte masqué : des codes à la place des noms que Shield détecte ou que vous
enregistrez.
C'est une pseudonymisation locale et réversible, pas une anonymisation.

### Le trajet d'un texte

```text
 Votre ordinateur                                   Fournisseur d'IA
 ----------------                                   ----------------
 Pièces du dossier ──► Shield masque ──► texte avec codes ──►  Claude, ChatGPT, Copilot
                         ▲                                      │
                         │ coffre chiffré                       │ réponse avec codes
                         ▼ (codes ⇄ vrais noms)                 │
 Document final ◄── Shield restaure ◄──────────────────────────┘
 (vrais noms, dans « Shield - sorties », ou dans Shield Desk)
```

### Ce qui part, ce qui reste

| Part chez le fournisseur d'IA | Reste sur votre ordinateur |
|---|---|
| Le texte masqué : PERSONNE_A, SOCIETE_A, ADRESSE_1, IBAN_1... | Les vrais noms, adresses, numéros |
| Les faits, les dates (sauf dates de naissance), les montants | Le coffre : la table codes / vrais noms, chiffrée |
| Les juridictions, institutions, lois et articles | La clé du coffre |
| Le code du dossier (DOSSIER_1), les codes des pièces (DOC_1) et les noms de fichiers masqués | Le nom réel du dossier, le chemin du répertoire |
| Votre question et les consignes que vous donnez | Le journal local (événements, codes, nombres) |

### Où sont vos données

- **Le coffre** : un fichier par dossier, dans `~/.ragbase-shield` (Mac, Linux)
  ou `%LOCALAPPDATA%\ragbase-shield` (Windows, jamais le profil itinérant). Les vrais noms y sont chiffrés.
- **La clé** : dans le trousseau du système (Trousseau d'accès sur Mac, Gestionnaire d'identification sous Windows).
  S'il n'y a pas de trousseau, dans un fichier lisible par vous seul.
- **Les documents restaurés** : dans le sous-répertoire « Shield - sorties » du dossier client.
- **Le journal** : des noms d'événements, des codes et des nombres. Jamais un vrai nom.
- **Chez RAGbase** : rien. Shield n'envoie rien à RAGbase et n'envoie aucune statistique.

### Les 3 règles

1. Connectez un dossier, n'attachez pas le fichier au chat.
2. Ne collez pas de texte brut dans le chat. Passez par Shield Desk, la commande `mask` ou l'extension.
3. Un texte déjà envoyé ne peut pas être rappelé.

### Ce que Shield ne fait pas

- Il ne masque pas les faits. Un fait peut suffire à reconnaître un client.
- Il ne trouve pas tous les noms. Les noms enregistrés dans le dossier sont les mieux protégés. Vérifiez la liste
  des noms détectés, et relisez le texte masqué avant de l'envoyer.
- Il ne lit pas les PDF scannés (pas d'OCR dans cette version).
- Il ne protège pas un texte que vous tapez ou collez directement dans le chat.
- Il ne protège pas un ordinateur infecté par un logiciel malveillant.

### Le RGPD continue de s'appliquer

L'article 4(5) du RGPD définit la pseudonymisation : les données ne peuvent plus être attribuées
à une personne sans informations supplémentaires, conservées séparément et protégées.
Avec Shield, ces informations supplémentaires sont le coffre et sa clé. Ils restent sur votre ordinateur.

Pour vous, qui détenez le coffre, les données restent des données personnelles.
Le CEPD le rappelle dans ses lignes directrices 01/2025 sur la pseudonymisation.
Vos obligations RGPD continuent donc de s'appliquer. Shield est une mesure de protection.
Il ne vous en dispense pas. Voir la [fiche conformité](CONFORMITE.fr.md).

---

## Part 2. In English (developers and IT)

### The rules no module may break

These come from [ARCHITECTURE.md](../ARCHITECTURE.md) section 2.

1. **Mask before the model.** Real data must be masked before it enters a conversation.
   Text the user types or pastes into a chat has already reached the provider. Shield cannot recall it.
2. **No real value ever goes to a model.** No MCP tool result, error message, log line or hook output
   contains a vault value. Codes only.
3. **No unmask tool for the model.** Restoring names happens only locally: in Shield Desk, in the CLI,
   in the browser extension's own popup or side panel (never in the provider's page), or by writing a file
   to disk. `shield_save_draft` returns only "saved" and a coded file id.
4. **Fail closed.** If the engine, the vault or a document reader fails, the tool returns an error with
   codes only, never the raw text.
5. **Local only.** No telemetry, no network calls. The Desk binds to 127.0.0.1, checks the Host header and
   requires a random per-install token. The MCP server uses stdio.
6. **Honest wording.** Pseudonymisation (reversible), not anonymisation. Detection is never complete.
7. **Dossier names are client data.** Models see a dossier only by its code (DOSSIER_1).
   Document file names are shown masked.

### What a model can see

| Surface | The model receives |
|---|---|
| `shield_list_dossiers` | Dossier codes and counts |
| `shield_list_documents` | Document codes (DOC_n), masked file names, kind, size, pages |
| `shield_read_document` | Masked text, and the next offset |
| `shield_search` | Masked snippets. The query may contain codes; Shield maps them back locally to search |
| `shield_save_draft` | "saved OUTPUT_n (x KB)". The real-name file is written to disk, never returned |
| `shield_status` | Version, engine mode, honest limits |
| Claude Code hooks | A block message that names the CODE to use, never the value |

No MCP tool takes raw client text from the model as input.
Tools take dossier codes and document codes, and read the files locally.

### Data flow per surface

- **MCP (Claude Desktop, Claude Code, Cowork, ChatGPT desktop, Codex, VS Code):** the app starts
  `ragbase-shield mcp` over stdio. Files are read on disk, masked, and only the masked text is returned.
- **Claude Code hooks:** `UserPromptSubmit` blocks a prompt that contains a registered value of any dossier
  and names the code to use. `PreToolUse` denies `Read`, `Grep`, `Glob` and `Bash cat` inside a registered
  dossier folder and points to `shield_read_document`. `PostToolUse` replaces any registered value left in a
  tool result with its masked version.
- **Shield Desk:** a local page for the user. It may show real values, because it never talks to a model.
- **CLI:** `mask` and `restore` read a file, stdin or the clipboard, and print or replace the clipboard.
- **Browser extension:** masks pasted text through the Desk API (with the token) before the page gets it.
  Restore happens only in the extension's side panel, never in the provider's page.

### Storage

| Item | Where | Protection |
|---|---|---|
| Home | `$RAGBASE_SHIELD_HOME`, else `~/.ragbase-shield`, else `%LOCALAPPDATA%\ragbase-shield` (Windows) | Folder mode 0700 |
| Dossier registry | `<home>/registry.db` | Folder paths and titles encrypted with the master key; one random data key per dossier, wrapped by the master key |
| Vault, one per dossier | `<home>/vaults/<uuid>.db` (SQLite) | Real values, normalised forms and document paths encrypted with Fernet (`cryptography`); lookups use an HMAC, never the name in clear |
| Master key | OS keychain through `keyring` (service `ragbase-shield`, user `vault-key`); fallback `<home>/key` | Fallback file mode 0600; `RAGBASE_SHIELD_KEYRING=0` forces the file; a missing or wrong key fails closed |
| Export for a colleague | The file you choose | scrypt (passphrase) + Fernet, mode 0600; no journal inside |
| Desk token | `<home>/desk_token` | Mode 0600 |
| Journal | Local | Event names, codes and counts only |
| Restored outputs | `<dossier folder>/Shield - sorties` | Your file system; the only DOCX metadata is the custom property `RAGbaseShieldDossier` (the dossier code) |

### Codes

- Allocated sequentially per dossier: PERSONNE_A, PERSONNE_B, ..., IBAN_1, IBAN_2.
  Stable across calls and restarts. Each dossier starts again at A and 1.
- Never derived from a hash of the value. A hash would allow frequency and dictionary attacks.
- Real text that already looks like a code is escaped, so it is never confused with a code. The escape uses
  the same patterns as restore ("USER_EMAIL_1", "PERSONNE_Ab", "TEL_1er" are escaped too), so restore never
  writes a client value into real text.
- Restore uses exact codes, also glued to punctuation or digits ("PERSONNE_A2026"), Markdown-escaped
  ("PERSONNE\_A") or with a hidden character. It reports codes it cannot match, including codes the model
  invented, and near misses it leaves as they are ("personne_a").
- Ranges: letter codes up to four letters (PERSONNE_ZZZZ), number codes up to six digits (EMAIL_999999).
  Past that, Shield refuses to allocate a code instead of writing one that restore could not read.

### Shield Desk security

- Binds to 127.0.0.1 only (default port 7878).
- Rejects any request whose Host header is not `127.0.0.1:<port>` or `localhost:<port>` (403).
- Every `/api/*` route needs the token in the `X-Shield-Token` header (`?t=<token>` only for the first page load).
- CORS is allowed only for `chrome-extension://*` and `moz-extension://*` origins, and only with a valid token.
- Least privilege for the browser extension: an extension origin may call `GET /api/status`, `GET /api/dossiers`
  (codes, titles and counts, never folder paths), `POST /api/mask` (codes and kinds, never values) and
  `POST /api/restore` (shown in the extension side panel only). Every other route answers 403 to it.

### Threat model

In scope (Shield is designed to stop these):

- A vault value reaching the AI provider through a Shield tool, a hook, an error or a log.
- A model obtaining real names from Shield (there is no unmask tool), or confirming a guessed name (search
  matches a phrase that holds codes against the masked text only).
- A model, or a prompt injection inside a client document, changing what is masked: in an agent shell the CLI
  refuses `keep-clear`, `register`, `add` and `import`, and the Claude Code hook denies them.
- A damaged vault silently weakening the checks: every model-facing check fails closed when one registered
  dossier cannot be opened.
- Another website or another computer on the network reading the Desk API.
- Someone with a copy of the vault files but without the key reading real values.
- Code guessing through hashes (codes are sequential, not hashed).

Out of scope (Shield cannot stop these):

- Text the user types, pastes or attaches directly in the AI app.
- Facts, dates and amounts that identify a client without a name.
- Names that the detector misses and nobody registered.
- Malware or another person with access to the user's open session.
- The AI provider's own retention and use of the masked text. Read your provider's terms.

### Residual risks to tell users

- Shield can miss a name that nobody registered. Register the parties of each dossier, check the list of detected
  names, and read the masked text before you send it.
- Cross-references (a project name, an amount, a date, a place) can re-identify. The user can register
  extra terms per dossier, and mark terms "Keep in clear".
- The masked text is still confidential work product. Masking does not make it public.
