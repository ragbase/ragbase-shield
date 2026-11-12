# RAGbase Shield (plugin for Claude Code and Cowork)

Version 0.4.0. Free and open source (Apache-2.0). Publisher: RAGbase, Paris.
English version below.

## Français

RAGbase Shield fait une **pseudonymisation locale et réversible** des dossiers clients. Sur votre ordinateur, il
remplace les noms, adresses, IBAN, e-mails et numéros de vos clients par des codes (PERSONNE_A, SOCIETE_B, IBAN_1).
Claude travaille avec ces codes. Les vrais noms reviennent seulement sur votre ordinateur, dans le document final.
Ce n'est pas une anonymisation : les faits, les dates et les montants restent lisibles par l'IA.

Ce que le plugin ajoute :

- **Un serveur MCP local** (`uvx ragbase-shield==0.4.0 mcp`) avec six outils : lister les dossiers, lister les
  pièces, lire une pièce masquée, chercher dans un dossier, enregistrer le projet final, statut de Shield.
- **Une compétence (skill)** qui explique à Claude la procédure sûre : lire par les outils Shield, garder les codes,
  enregistrer avec `shield_save_draft`.
- **Des hooks** (Claude Code et Cowork) que vous installez pour protéger vos dossiers :
  - un message qui contient une valeur enregistrée d'un dossier est bloqué, et Shield indique le code à utiliser ;
  - une lecture directe d'un dossier enregistré (Read, Grep, Bash, un outil de fichiers d'un autre serveur MCP) est
    refusée, et Claude est renvoyé vers `shield_read_document` ;
  - une valeur enregistrée qui reste dans le résultat d'un outil est remplacée par son code.

Ce que le plugin exécute et envoie :

- `uvx` télécharge le paquet `ragbase-shield` 0.4.0 et ses dépendances depuis PyPI, une fois, au premier lancement.
- Le serveur MCP et les hooks tournent sur votre ordinateur. Ils n'envoient rien à RAGbase et aucune statistique
  d'usage. La table des codes (le coffre) est chiffrée et reste sur votre ordinateur.
- Le texte masqué part chez Anthropic, comme tout message de la conversation avec Claude.
- Le modèle NER optionnel se télécharge seulement si vous lancez vous-même `ragbase-shield ner download`.

Exemples de demandes :

1. « Liste mes dossiers Shield, puis résume les pièces du dossier DOSSIER_1. »
2. « Dans DOSSIER_2, cherche les échéances de paiement et fais-en un tableau. »
3. « Rédige une mise en demeure adressée à PERSONNE_A à partir des pièces de DOSSIER_1, puis enregistre-la avec
   shield_save_draft. »

Pour commencer : installez uv, enregistrez un dossier avec Shield Desk (`uvx ragbase-shield==0.4.0 desk`) ou avec
`uvx ragbase-shield==0.4.0 add <dossier> --title "Titre"`, puis lancez Claude Code. Pour tester sans vos données :
`uvx ragbase-shield==0.4.0 verify` vérifie chaque chemin avec des données inventées et répond CLEAN ou LEAK.

Limites : la détection n'est pas complète, relisez le texte masqué dans les cas sensibles. Dans le comparatif public
du 11 novembre 2026, Hexagone laisse moins de données personnelles lisibles que Shield 0.4.0 sur certains jeux de
test. Les chiffres, avec leur jeu, leur mode et leur statut : https://shield.ragbase.ai/resultats/. Le texte que vous
tapez ou joignez directement dans une autre application d'IA n'est pas protégé.

## English

RAGbase Shield does **local, reversible pseudonymisation** of client files. On your computer, it replaces your
clients' names, addresses, IBANs, e-mails and numbers with codes (PERSON_A, COMPANY_B, IBAN_1 in the English
locale; PERSONNE_A, SOCIETE_B in the default French locale). Claude works with these codes. The real names come back
only on your computer, in the final document. This is not anonymisation: facts, dates and amounts stay readable by
the AI.

What the plugin adds:

- **A local MCP server** (`uvx ragbase-shield==0.4.0 mcp`) with six tools: list dossiers, list documents, read a
  masked document, search a dossier, save the final draft, Shield status.
- **A skill** that tells Claude the safe workflow: read through the Shield tools, keep the codes, save with
  `shield_save_draft`.
- **Hooks** (Claude Code and Cowork) that you install to protect your dossiers:
  - a prompt that contains a registered value of a dossier is blocked, and Shield gives the code to use;
  - a direct read of a registered dossier (Read, Grep, Bash, a file tool of another MCP server) is denied, and
    Claude is sent to `shield_read_document`;
  - a registered value left in a tool result is replaced with its code.

What the plugin runs and sends:

- `uvx` downloads the `ragbase-shield` 0.4.0 package and its dependencies from PyPI, once, at the first start.
- The MCP server and the hooks run on your computer. They send nothing to RAGbase and no usage statistics. The code
  table (the vault) is encrypted and stays on your computer.
- The masked text goes to Anthropic, like every message of the conversation with Claude.
- The optional NER model downloads only if you run `ragbase-shield ner download` yourself.

Example prompts:

1. "List my Shield dossiers, then summarise the documents of DOSSIER_1."
2. "In DOSSIER_2, find the payment deadlines and put them in a table."
3. "Draft a formal notice for PERSON_A from the documents of DOSSIER_1, then save it with shield_save_draft."

To start: install uv, register a folder with Shield Desk (`uvx ragbase-shield==0.4.0 desk`) or with
`uvx ragbase-shield==0.4.0 add <folder> --title "Title"`, then start Claude Code. To test without your data:
`uvx ragbase-shield==0.4.0 verify` checks every path with invented data and answers CLEAN or LEAK.

Limits: detection is not complete, so review the masked text in sensitive cases. In the public comparison of
11 November 2026, Hexagone leaves less personal data readable than Shield 0.4.0 on some test sets. The numbers, with
their set, mode and status: https://shield.ragbase.ai/en/results/. Text that you type or attach directly in another
AI app is not protected.

Source code, install guide and support: https://github.com/ragbase/ragbase-shield (issues for questions).
Privacy policy: https://shield.ragbase.ai/en/privacy/
