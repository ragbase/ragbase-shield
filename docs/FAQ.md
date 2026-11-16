# Questions fréquentes / FAQ

Partie 1 en français, pour les avocats. [Part 2 in English](#part-2-english-developers-and-it), for developers and IT.

---

## Partie 1. Français

### Shield envoie-t-il mes données à RAGbase ?

Non. Shield tourne sur votre ordinateur. Il n'envoie rien à RAGbase et n'envoie aucune statistique d'usage.

### Est-ce de l'anonymisation ?

Non. C'est une pseudonymisation locale et réversible. Les noms deviennent des codes, mais les faits, les dates
et les montants restent lisibles. Vous gardez la table qui permet de remettre les vrais noms.

### Le RGPD s'applique-t-il encore ?

Oui. Pour vous, qui détenez la table de correspondance, les données pseudonymisées restent des données
personnelles (RGPD, art. 4(5) et considérant 26). Shield est une mesure de protection. Il ne vous dispense pas
de vos obligations. Voir la [fiche conformité](CONFORMITE.fr.md).

### Que voit exactement l'IA ?

Le texte masqué (PERSONNE_A, SOCIETE_A, ADRESSE_1...), les faits, les dates, les montants, les juridictions et
les articles de loi. Elle voit le dossier sous un code (DOSSIER_1) et les noms de fichiers masqués.
Elle ne voit ni les vrais noms, ni le coffre, ni la clé. Détails : [modèle de confidentialité](PRIVACY_MODEL.md).

### Puis-je joindre un fichier au chat ?

Non. Un fichier joint part chez le fournisseur d'IA avant que Shield puisse agir.
Connectez le dossier dans Shield, puis demandez à l'IA de lire les pièces avec Shield.

### J'ai collé un texte avec un vrai nom dans le chat. Que faire ?

Shield ne peut pas rappeler un texte déjà envoyé. Vous pouvez supprimer la conversation dans l'application
d'IA ; la durée de conservation dépend alors des conditions du fournisseur. Enregistrez ce nom dans le dossier
(page Dossiers de Shield Desk) : il sera masqué la prochaine fois. Dans Claude Code, le hook bloque un prompt
qui contient un nom enregistré.

### Comment parler d'une personne dans le chat ?

Écrivez son code : « Rédige une mise en demeure adressée à PERSONNE_B ». La liste des codes du dossier est dans
Shield Desk, page Dossiers (ou `ragbase-shield entities DOSSIER_1`).

### Shield trouve-t-il tous les noms ?

Non. La détection n'est jamais complète. Shield trouve les numéros à clé de contrôle (SIREN, SIRET, NIR, IBAN,
TVA, carte), les e-mails, les téléphones, les adresses, les références de procédure, les noms précédés d'un
titre (M., Mme, Me, Maître) ou d'un prénom courant, et les sociétés qui ont une forme juridique (SAS, SARL...). Après « M. », « Mme », « Mlle » ou « Me », Shield masque le nom qui suit, avec ou sans majuscules, dans tous les textes en français. Dans un texte tapé sans majuscules, comme sur un téléphone ou dans une note rapide, Shield masque aussi les noms avec ou sans civilité, les sociétés écrites avec leur forme juridique, les adresses postales et les champs « nom : » et « prénom : ». Le réglage RAGBASE_SHIELD_LOWERCASE_NAMES=0 désactive ces règles. Un nom rare, étranger ou mal orthographié
peut passer. Enregistrez les parties de chaque dossier : ce sont elles que Shield masque le plus sûrement.
Vérifiez la liste des noms détectés, et relisez le texte masqué avant de l'envoyer.
Les résultats du benchmark sont dans
[evaluation/laptop/RESULTS_PUBLIC.md](../evaluation/laptop/RESULTS_PUBLIC.md).

### Un nom ne doit pas être masqué (un expert judiciaire, une autorité). Que faire ?

Dans Shield Desk, page Dossiers, cliquez sur « Voir les entités », puis activez l'interrupteur
« Garder en clair » de ce nom. En terminal (le vôtre, pas celui d'un assistant IA, qui refuse cette commande) :
`ragbase-shield keep-clear DOSSIER_1 PERSONNE_C`.

Les numéros de toque des avocats sont masqués par défaut. Pour les laisser visibles, lancez Shield avec
`RAGBASE_SHIELD_MASK_TOQUE=0`.

### Et si l'IA invente un code qui n'existe pas ?

À la restauration, Shield vous signale les codes qu'il ne connaît pas, et les codes mal recopiés qu'il ne remplace
pas (par exemple « personne_a » en minuscules). Vérifiez-les avant d'utiliser le texte. Un code écrit
« PERSONNE\_A » (échappement Markdown) est bien restauré.

### Pourquoi un nom restauré n'a-t-il pas exactement l'orthographe du document ?

Shield remet la valeur enregistrée dans le dossier, dans la première écriture vue : « M. Mercadier » peut revenir
en « M. Thibault Mercadier », un SIREN écrit « 832456719 » peut revenir en « 832 456 719 ». Relisez toujours
le document restauré.

### J'ai masqué un texte sans choisir de dossier. Que se passe-t-il ?

Les noms détectés reçoivent des codes temporaires, et les noms enregistrés dans vos dossiers deviennent
[PERSONNE] ou [SOCIETE]. La restauration n'est pas possible. Choisissez toujours le dossier du client.

### Les PDF scannés sont-ils pris en charge ?

Pas dans cette version : il n'y a pas d'OCR. Shield vous dit qu'un PDF n'a pas de texte et ne le lit pas.
Formats lus : PDF avec texte, DOCX, XLSX, TXT, MD, EML, HTML. Formats écrits : DOCX et MD.

### Où sont stockés les vrais noms ?

Dans un coffre chiffré, un par dossier, sur votre ordinateur (`~/.ragbase-shield`, ou
`%LOCALAPPDATA%\ragbase-shield` sous Windows : jamais le profil itinérant, souvent copié sur un serveur).
La clé est dans le trousseau du système.

### Je perds mon ordinateur. Que se passe-t-il ?

Les coffres sont chiffrés. Sans la clé, ils sont illisibles. Chiffrez aussi le disque (FileVault sur Mac,
BitLocker sous Windows). Sans le coffre, plus personne ne peut remettre les vrais noms dans une ancienne réponse :
faites des exports si vous en avez besoin.

### Comment transmettre un dossier à un collègue ?

`ragbase-shield export DOSSIER_1 dossier.shield` crée un fichier chiffré par une phrase secrète.
Votre collègue lance `ragbase-shield import dossier.shield`. Donnez-lui la phrase secrète par un autre canal.

### Shield fonctionne-t-il avec ChatGPT web, Copilot ou Word ?

Oui, par Shield Desk (masquer, copier, coller, restaurer) ou par l'extension de navigateur pour les sites web.
Il n'y a pas de branchement direct pour ChatGPT web ni pour Microsoft 365 Copilot.
Attention : Copilot dans Word ou Outlook lit le document ou l'e-mail ouvert. Ouvrez une copie masquée.
Voir [INSTALL.md](INSTALL.md).

### Notre cabinet utilise un outil de prévention des fuites (DLP). Est-ce compatible ?

Les codes de Shield sont courts et n'ont pas la forme des données qu'un DLP recherche :
IBAN_1 n'a pas la forme d'un IBAN. Un texte masqué ne devrait donc pas déclencher ces règles.
Faites un essai avec votre outil.

### Combien coûte Shield ?

Rien. Shield est gratuit et open source (licence Apache-2.0). Vous payez seulement votre abonnement d'IA.

### Shield fonctionne-t-il sans Internet ?

Shield, oui : il ne fait aucun appel réseau. L'IA, non : elle tourne chez le fournisseur.
Pour une IA qui tourne chez vous, voir [Pour aller plus loin](../README.fr.md#pour-aller-plus-loin).

---

## Part 2. English (developers and IT)

### Why is there no unmask tool for the model?

Any tool that returns real names to the model sends them to the provider. Restore happens only locally:
Shield Desk, the CLI, the browser extension side panel, or a file written by `shield_save_draft`
(which returns only "saved OUTPUT_n" and a size).

### Why don't MCP tools accept raw text?

If the model can pass raw text to a tool, the provider already has that text. Shield tools take dossier codes and
document codes and read files on disk. `shield_search` accepts a query that may contain codes; Shield maps them back
locally.

### Why codes and not fake names?

Codes are exact and reversible, and they cannot be mistaken for a real person. A fake name can collide with a real
name in the same document, and restore becomes ambiguous.

### Why not hash the values?

A hash of a name can be reversed by a dictionary or frequency attack. Codes are allocated sequentially per dossier
and mean nothing outside the vault.

### What happens on an error?

Shield fails closed. Tools return an error with codes only, never the raw text.

### Is there telemetry or any network call?

No. The library makes no network calls; tests block outbound sockets. The Desk listens on 127.0.0.1 only, checks the
Host header and needs a per-install token. With uv, the install downloads Shield from the release page on GitHub
and its libraries from PyPI; once the command is installed (`uv tool install`), nothing else goes out.

### Can I turn on Precise mode (the AI model)?

Yes, it is optional. Fast mode (technical name: rules) is the default. Precise mode adds a local AI model for name
recognition (technical name: GLiNER; about 1.2 GB, Apache-2.0). Install the `ner` extra, then run
`ragbase-shield ner download`: this is the only download, and you start it yourself. The model then runs offline, on
the CPU, and the engine uses it automatically. What the model finds goes through the same whitelist as the rules and
never overrides the structured detectors. The Mac and Windows installers do not include the model yet. Details:
[NER.md](NER.md).

### What does Shield mask in text typed without capitals?

After "M.", "Mme", "Mlle" or "Me", Shield masks the name that follows, with or without capitals, in every French text.
In text typed without capitals, as on a phone or in a quick note, Shield also masks names with or without a title, companies written with their legal form, postal addresses and the fields "nom :" and "prénom :".
The setting RAGBASE_SHIELD_LOWERCASE_NAMES=0 turns these rules off.

### How do I get English code labels?

Set `RAGBASE_SHIELD_LOCALE=en`: PERSON_A, COMPANY_A, ADDRESS_1, CASEREF_1, SSN_1.

### Where is the data, and how do I change the folder or the port?

`RAGBASE_SHIELD_HOME` sets the data folder (default `~/.ragbase-shield`; on Windows `%LOCALAPPDATA%\ragbase-shield`,
never the roaming profile: SQLite in WAL mode is not safe on a network share). `RAGBASE_SHIELD_PORT` sets the Desk
port (default 7878).
`RAGBASE_SHIELD_KEYRING=0` keeps the key in a 0600 file instead of the OS keychain.
`RAGBASE_SHIELD_MASK_TOQUE=0` keeps lawyers' toque numbers visible.

### uv prints "Failed to patch the install name of the dynamic library". Is it a problem?

No. uv prints it on macOS the first time it downloads a managed Python. Shield works. Shield needs Python 3.10 or
later, and uv picks one for you. To pin a version:
`uvx --python 3.12 --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl ragbase-shield desk`.

### Why are some commands refused in Claude Code or Codex?

What a command prints in an AI agent's shell goes to the model. `entities`, `restore` and `export` refuse
there (they would show real values), and `add`, `register`, `keep-clear` and `import` refuse too (a model, or
a prompt injection inside a client document, must never change what is masked). `list` shows codes only. The
Claude Code hook also denies these commands before they run.

### How do I check an install?

`ragbase-shield doctor` checks the install, key storage and integrations. `ragbase-shield verify` plants synthetic
data, runs every path (MCP tools, hooks, Desk API) and prints CLEAN or LEAK per path.

### Copilot Business or Enterprise does not show the tools.

The "MCP servers in Copilot" policy is off by default for organisations. An admin must turn it on.

### Claude Team or Enterprise does not allow the extension.

Admins can block desktop extensions. Ask your admin, or use Shield Desk.

### How do I report a security problem?

Privately, as described in [SECURITY.md](../SECURITY.md). Use synthetic data only in reports.
