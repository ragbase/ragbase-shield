# RAGbase Shield (plugin for Claude Code)

Version 0.4.4. Free and open source (Apache-2.0). Publisher: RAGbase, Paris.
English version below.

## Français

> **Pour Claude Code seulement.** N'ajoutez pas ce plugin dans l'onglet Claude de l'application Claude : il a besoin
> de uv, et ses hooks peuvent y bloquer chaque message. Dans l'application Claude, utilisez le plugin Claude :
> [ragbase/ragbase-shield-mac](https://github.com/ragbase/ragbase-shield-mac) (Mac) ou
> [ragbase/ragbase-shield-windows](https://github.com/ragbase/ragbase-shield-windows) (Windows).

RAGbase Shield fait une **pseudonymisation locale et réversible** des dossiers clients. Sur votre ordinateur, il
remplace les noms, adresses, IBAN, e-mails et numéros de vos clients par des codes (PERSONNE_A, SOCIETE_B, IBAN_1).
Claude travaille avec ces codes. Les vrais noms reviennent seulement sur votre ordinateur, dans le document final.
Ce n'est pas une anonymisation : les faits, les dates et les montants restent lisibles par l'IA.

Ce que le plugin ajoute :

- **Un serveur MCP local** (`ragbase-shield mcp`) avec six outils : lister les dossiers, lister les
  pièces, lire une pièce masquée, chercher dans un dossier, enregistrer le projet final, statut de Shield.
- **Une compétence (skill)** qui explique à Claude la procédure sûre : lire par les outils Shield, garder les codes,
  enregistrer avec `shield_save_draft`.
- **Des hooks** (Claude Code) que vous installez pour protéger vos dossiers :
  - un message qui contient une valeur enregistrée d'un dossier est bloqué, et Shield indique le code à utiliser ;
  - une lecture directe d'un dossier enregistré (Read, Grep, Bash, un outil de fichiers d'un autre serveur MCP) est
    refusée, et Claude est renvoyé vers `shield_read_document` ;
  - une valeur enregistrée qui reste dans le résultat d'un outil est remplacée par son code.

Ce que le plugin exécute et envoie :

- Le plugin contient le paquet `ragbase-shield` 0.4.4, dans le fichier
  `vendor/ragbase_shield-0.4.4-py3-none-any.whl`. C'est le fichier de la version 0.4.4 publiée sur GitHub. Son
  SHA-256 est celui du fichier `SHA256SUMS` de cette version :
  `b70d309802890ef5e7da817e9f5c86171eb9ec461441950fd5e3c4287b8f6e9a`.
- Le serveur MCP et les quatre hooks lancent ce fichier, et rien d'autre :
  `uvx --from ${CLAUDE_PLUGIN_ROOT}/vendor/ragbase_shield-0.4.4-py3-none-any.whl ragbase-shield mcp`
  (ou `hook user-prompt-submit`, `hook pre-tool-use`, `hook post-tool-use` à la place de `mcp`).
- Au premier lancement, `uvx` installe ce fichier et télécharge ses dépendances depuis PyPI, une fois.
- Le serveur MCP et les hooks tournent sur votre ordinateur. Ils n'envoient rien à RAGbase et aucune statistique
  d'usage. La table des codes (le coffre) est chiffrée et reste sur votre ordinateur.
- Le texte masqué part chez Anthropic, comme tout message de la conversation avec Claude.
- Le modèle IA optionnel du mode Précis (nom technique : GLiNER) se télécharge seulement si vous lancez vous-même
  `ragbase-shield ner download`.

Ce que renvoie chaque hook (code source : `src/ragbase_shield/hooks.py` du dépôt) :

- `UserPromptSubmit` : rien (code de sortie 0), et le message part. Si le message contient une valeur enregistrée :
  `"decision": "block"` avec `suppressOriginalPrompt: true` et le code de sortie 2.
- `PreToolUse` (les deux entrées) : rien (code de sortie 0), et les règles d'autorisation habituelles de Claude Code
  s'appliquent. Pour un accès direct à un dossier enregistré, aux données de Shield ou à Shield Desk, ou pour une
  commande Shield qui affiche des valeurs réelles ou modifie le coffre : `permissionDecision: "deny"` avec une raison
  et le code de sortie 2. Ce hook ne renvoie jamais `allow`, `ask` ou `approve` et ne modifie jamais l'entrée d'un
  outil (pas de `updatedInput`).
- `PostToolUse` : rien (code de sortie 0). Si le résultat d'un outil contient une valeur enregistrée :
  `updatedToolOutput` (et `updatedMCPToolOutput` pour un outil MCP), le même résultat avec les codes à la place des
  valeurs, et un message (`additionalContext`, `systemMessage`).
- Si Shield échoue, ou si la vérification ne peut pas finir à temps, le hook bloque le message, refuse l'appel, ou
  vide le résultat et arrête la session (`"continue": false`).

Exemples de demandes :

1. « Liste mes dossiers Shield, puis résume les pièces du dossier DOSSIER_1. »
2. « Dans DOSSIER_2, cherche les échéances de paiement et fais-en un tableau. »
3. « Rédige une mise en demeure adressée à PERSONNE_A à partir des pièces de DOSSIER_1, puis enregistre-la avec
   shield_save_draft. »

Installation dans Claude Code (version 2.1.275 ou plus récente) :
`/plugin install ragbase-shield --marketplace ragbase/ragbase-shield`. Avec une version plus ancienne :
`/plugin marketplace add ragbase/ragbase-shield`, puis `/plugin install ragbase-shield@ragbase`.

Pour commencer : installez uv, l'outil open source qui télécharge et lance Shield.

Sur Mac : ouvrez l'application Terminal, collez cette ligne, puis appuyez sur Entrée.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sur Windows : ouvrez PowerShell, collez cette ligne, puis appuyez sur Entrée.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Si uv est déjà installé sur votre ordinateur, collez quand même cette ligne : elle met uv à jour.

Fermez la fenêtre, puis ouvrez-en une nouvelle. Installez ensuite la commande `ragbase-shield`, depuis le fichier
de la version 0.4.4 publiée sur GitHub :

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl
```

Enregistrez un dossier avec Shield Desk (`ragbase-shield desk`) ou avec
`ragbase-shield add <dossier> --title "Titre"`, puis lancez Claude Code. Pour tester sans vos données :
`ragbase-shield verify` vérifie chaque chemin avec des données inventées et répond CLEAN ou LEAK.

Limites : la détection n'est pas complète, relisez le texte masqué dans les cas sensibles. Le texte que vous tapez ou
joignez directement dans une autre application d'IA n'est pas protégé. Les résultats mesurés :
https://shield.ragbase.ai/resultats/.

## English

> **For Claude Code only.** Do not add this plugin in the Claude tab of the Claude app: it needs uv, and its hooks
> can stop every message there. In the Claude app, use the Claude plugin:
> [ragbase/ragbase-shield-mac](https://github.com/ragbase/ragbase-shield-mac) (Mac) or
> [ragbase/ragbase-shield-windows](https://github.com/ragbase/ragbase-shield-windows) (Windows).

RAGbase Shield does **local, reversible pseudonymisation** of client files. On your computer, it replaces your
clients' names, addresses, IBANs, e-mails and numbers with codes (PERSON_A, COMPANY_B, IBAN_1 in the English
locale; PERSONNE_A, SOCIETE_B in the default French locale). Claude works with these codes. The real names come back
only on your computer, in the final document. This is not anonymisation: facts, dates and amounts stay readable by
the AI.

What the plugin adds:

- **A local MCP server** (`ragbase-shield mcp`) with six tools: list dossiers, list documents, read a
  masked document, search a dossier, save the final draft, Shield status.
- **A skill** that tells Claude the safe workflow: read through the Shield tools, keep the codes, save with
  `shield_save_draft`.
- **Hooks** (Claude Code) that you install to protect your dossiers:
  - a prompt that contains a registered value of a dossier is blocked, and Shield gives the code to use;
  - a direct read of a registered dossier (Read, Grep, Bash, a file tool of another MCP server) is denied, and
    Claude is sent to `shield_read_document`;
  - a registered value left in a tool result is replaced with its code.

What the plugin runs and sends:

- The plugin holds the `ragbase-shield` 0.4.4 package, in the file
  `vendor/ragbase_shield-0.4.4-py3-none-any.whl`. It is the wheel of the GitHub release 0.4.4. Its SHA-256 is the
  one in the `SHA256SUMS` file of that release:
  `b70d309802890ef5e7da817e9f5c86171eb9ec461441950fd5e3c4287b8f6e9a`.
- The MCP server and the four hooks run this file and nothing else:
  `uvx --from ${CLAUDE_PLUGIN_ROOT}/vendor/ragbase_shield-0.4.4-py3-none-any.whl ragbase-shield mcp`
  (or `hook user-prompt-submit`, `hook pre-tool-use`, `hook post-tool-use` in place of `mcp`).
- At the first start, `uvx` installs this file and downloads its dependencies from PyPI, once.
- The MCP server and the hooks run on your computer. They send nothing to RAGbase and no usage statistics. The code
  table (the vault) is encrypted and stays on your computer.
- The masked text goes to Anthropic, like every message of the conversation with Claude.
- The optional AI model of Precise mode (technical name: GLiNER) downloads only if you run
  `ragbase-shield ner download` yourself.

What each hook returns (source code: `src/ragbase_shield/hooks.py` in the repository):

- `UserPromptSubmit`: nothing (exit code 0), and the prompt goes on. If the prompt holds a registered value:
  `"decision": "block"` with `suppressOriginalPrompt: true` and exit code 2.
- `PreToolUse` (both entries): nothing (exit code 0), and the normal Claude Code permission rules apply. For a direct
  access to a registered dossier folder, to Shield's own data or to Shield Desk, or for a Shield command that prints
  real values or changes the vault: `permissionDecision: "deny"` with a reason and exit code 2. This hook never
  returns `allow`, `ask` or `approve` and never changes a tool input (no `updatedInput`).
- `PostToolUse`: nothing (exit code 0). If a tool result holds a registered value: `updatedToolOutput` (and
  `updatedMCPToolOutput` for an MCP tool), the same result with codes in place of the values, and a message
  (`additionalContext`, `systemMessage`).
- If Shield fails, or the check cannot finish in time, the hook blocks the prompt, denies the call, or blanks the
  result and stops the session (`"continue": false`).

Example prompts:

1. "List my Shield dossiers, then summarise the documents of DOSSIER_1."
2. "In DOSSIER_2, find the payment deadlines and put them in a table."
3. "Draft a formal notice for PERSON_A from the documents of DOSSIER_1, then save it with shield_save_draft."

Install in Claude Code (version 2.1.275 or later):
`/plugin install ragbase-shield --marketplace ragbase/ragbase-shield`. With an older version:
`/plugin marketplace add ragbase/ragbase-shield`, then `/plugin install ragbase-shield@ragbase`.

To start: install uv, the open-source tool that downloads and runs Shield.

On a Mac: open the Terminal app, paste this line, press Enter.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows: open PowerShell, paste this line, press Enter.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If uv is already on your computer, paste this line anyway: it updates uv.

Close the window and open a new one. Then install the `ragbase-shield` command, from the file of the 0.4.4 release
on GitHub:

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl
```

Register a folder with Shield Desk (`ragbase-shield desk`) or with
`ragbase-shield add <folder> --title "Title"`, then start Claude Code. To test without your data:
`ragbase-shield verify` checks every path with invented data and answers CLEAN or LEAK.

Limits: detection is not complete, so review the masked text in sensitive cases. Text that you type or attach
directly in another AI app is not protected. The measured results: https://shield.ragbase.ai/en/results/.

Source code, install guide and support: https://github.com/ragbase/ragbase-shield (issues for questions).
Privacy policy: https://shield.ragbase.ai/en/privacy/
