# RAGbase Shield

**Utilisez Claude sur vos dossiers clients, sans aucune fuite d'informations sensibles.**

Le meilleur moteur de pseudonymisation du marché.

RAGbase Shield 0.4.1 est un outil gratuit et open source (licence Apache-2.0).
Sur votre ordinateur, il remplace les noms et les numéros de vos clients par des codes avant l'envoi à Claude.
Quand Claude répond, Shield remet les vrais noms. Cela se passe aussi sur votre ordinateur.
Le droit reste lisible : les articles, les juridictions, les dates et les montants restent en clair, et Claude peut
travailler.

C'est une **pseudonymisation locale et réversible**.
Ce n'est pas une anonymisation : les faits, les dates et les montants restent lisibles par l'IA.
Rien ne part chez RAGbase. Shield n'envoie aucune statistique d'usage.

English version: [README.md](README.md)

Sommaire :

- [Pour les avocats : l'essentiel](#pour-les-avocats--lessentiel)
- [Installer](#installer)
- [Utiliser au quotidien](#utiliser-au-quotidien)
- [Résultats](#résultats)
- [Les limites (à lire)](#les-limites-à-lire)
- [Le modèle de confidentialité en 5 lignes](#le-modèle-de-confidentialité-en-5-lignes)
- [Pour les développeurs et l'informatique du cabinet](#pour-les-développeurs-et-linformatique-du-cabinet)
- [Liens](#liens)
- [Pour aller plus loin](#pour-aller-plus-loin)

---

## Pour les avocats : l'essentiel

### Ce que fait Shield

Vous écrivez ou vous ouvrez ce texte (exemple inventé) :

```text
M. Thibault Mercadier, domicilié 12 rue des Glycines, 69007 Lyon, conteste son
licenciement par la société Ateliers Brunelac SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° 25/01234).
Contact : t.mercadier@example.org
```

Claude reçoit ce texte :

```text
M. PERSONNE_A, domicilié ADRESSE_1, conteste son
licenciement par la société SOCIETE_A SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° RG_1).
Contact : EMAIL_1
```

C'est la sortie réelle de Shield 0.4.1 sur cet exemple, en mode Rapide (le réglage par défaut).
Notez ce qui reste lisible : la date, le montant, la juridiction.
Claude en a besoin pour travailler.

Dans un même dossier, une personne garde toujours le même code.
« M. Mercadier », « Thibault Mercadier » et « MERCADIER Thibault » deviennent tous PERSONNE_A.

Après « M. », « Mme », « Mlle » ou « Me », Shield masque le nom qui suit, avec ou sans majuscules, dans tous les textes en français.
Dans un texte tapé sans majuscules, comme sur un téléphone ou dans une note rapide, Shield masque aussi les noms avec ou sans civilité, les sociétés écrites avec leur forme juridique, les adresses postales et les champs « nom : » et « prénom : ».
Le réglage RAGBASE_SHIELD_LOWERCASE_NAMES=0 désactive ces règles.

### Les 3 règles à retenir

1. **Connectez un dossier, n'attachez pas le fichier au chat.**
   Un fichier joint au chat part chez le fournisseur d'IA avant que Shield puisse agir.
   Ajoutez le répertoire du dossier dans Shield. L'IA lit ensuite les pièces masquées par Shield.
2. **Ne collez pas de texte brut dans la zone de saisie du chat.**
   Passez d'abord par Shield (page « Masquer » de Shield Desk, ou l'extension de navigateur).
   Pour parler d'une personne dans le chat, écrivez son code (PERSONNE_A), pas son nom.
3. **Un texte déjà envoyé ne peut pas être rappelé.**
   Shield protège seulement ce qui passe par lui.
   Si un nom est parti par erreur, Shield ne peut rien y faire.

### Ce qui part chez le fournisseur d'IA, ce qui reste chez vous

| Part chez le fournisseur d'IA (Anthropic, OpenAI, Microsoft) | Reste sur votre ordinateur |
|---|---|
| Le texte masqué, avec des codes (PERSONNE_A, SOCIETE_A, IBAN_1) | Les vrais noms et les vrais numéros |
| Les faits, les dates (sauf dates de naissance), les montants, le raisonnement juridique | La table de correspondance codes / noms (le « coffre »), chiffrée |
| Les juridictions, les lois, les articles cités | La clé de chiffrement du coffre |
| Le code du dossier (DOSSIER_1) et les noms de fichiers masqués | Le nom réel du dossier et le chemin du répertoire |
| Votre question | Le journal local (événements, codes et nombres seulement) |

Détails : [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md).

### Les codes

| Ce qui est masqué | Code |
|---|---|
| Personne | PERSONNE_A, PERSONNE_B, ... |
| Société | SOCIETE_A, ... |
| Adresse postale | ADRESSE_1, ... |
| E-mail, téléphone | EMAIL_1, TEL_1 |
| IBAN, carte bancaire | IBAN_1, CARTE_1 |
| N° de sécurité sociale (NIR) | NIR_1 |
| SIREN, SIRET, TVA intracommunautaire | SIREN_1, SIRET_1, TVA_1 |
| Références de procédure (RG, pourvoi, Portalis, ECLI) | RG_1 |
| Autres identifiants (ISIN, LEI, passeport, plaque, adresse IP) | IDENT_1 |
| Sites web et adresses URL (sauf sites publics connus) | SITE_1 |
| Date de naissance | NAISSANCE_1 |

Shield ne masque pas : les juridictions, les institutions (Cour de cassation, CNIL, URSSAF...),
les lois, les codes, les articles, les mois et les jours.

---

## Installer

Téléchargements (installateurs, extension Claude Desktop, fichier `SHA256SUMS`) : la page des versions,
https://github.com/ragbase/ragbase-shield/releases/latest. Paquet Python : `ragbase-shield` sur PyPI.

| Votre application ou votre système | Quoi installer | Guide |
|---|---|---|
| Mac (macOS 13 ou plus récent) | `RAGbase-Shield-0.4.1.pkg` : double-clic, installation pour vous seul (prévue sans mot de passe administrateur), sans Terminal. Pas encore signé : macOS vous demande de confirmer la première fois | [docs/INSTALL.md](docs/INSTALL.md), section 0 |
| Windows 10 ou 11 | `RAGbase-Shield-0.4.1-win64.msi` : installation pour l'utilisateur (prévue sans droits administrateur). Pas encore signé : SmartScreen vous demande de confirmer | [docs/INSTALL.md](docs/INSTALL.md), section 0 |
| Claude Desktop | `ragbase-shield-0.4.1.mcpb` : double-clic, puis « Installer » | [docs/INSTALL.md](docs/INSTALL.md), section 2 |
| Claude Code et Cowork | Plugin : `/plugin marketplace add ragbase/ragbase-shield`, puis `/plugin install ragbase-shield@ragbase` | [docs/INSTALL.md](docs/INSTALL.md), section 3 |
| ChatGPT desktop et Codex, GitHub Copilot dans VS Code | `ragbase-shield install chatgpt` (ou `codex`, `vscode`), une fois la commande installée | [docs/INSTALL.md](docs/INSTALL.md), sections 4 et 5 |
| Toute application web (claude.ai, chatgpt.com, Copilot web) | Shield Desk, et l'extension de navigateur pour Chrome et Edge (pas encore dans les boutiques : chargez le dossier `integrations/browser-extension` en mode développeur) | [docs/INSTALL.md](docs/INSTALL.md), sections 6 et 7 |
| Terminal, avec uv ou pip | Shield Desk avec uv, ou le paquet avec pip | ci-dessous |

**Avec uv (une seule commande).** uv est l'outil open source qui télécharge et lance Shield.

Sur Mac : ouvrez l'application Terminal, collez cette ligne, puis appuyez sur Entrée.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sur Windows : ouvrez PowerShell, collez cette ligne, puis appuyez sur Entrée.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fermez la fenêtre, puis ouvrez-en une nouvelle. Lancez ensuite Shield Desk :

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk
```

Votre navigateur s'ouvre sur **http://127.0.0.1:7878**, avec un lien privé qui contient un jeton secret.
C'est une page locale : elle fonctionne seulement sur votre ordinateur.
Pour la rouvrir, relancez la commande ci-dessus ou utilisez le lien affiché dans le Terminal.
L'adresse seule, sans le jeton, affiche « Jeton refusé ».
Laissez la fenêtre du Terminal ouverte : la fermer arrête Shield Desk et l'extension de navigateur.

**Avec pip :** installez le fichier wheel de la version, puis lancez Shield Desk.

```sh
pip install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield desk
```

Le mode Précis (avec modèle IA) est optionnel (voir [docs/NER.md](docs/NER.md)) :

```sh
pip install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
```

Sur Mac, au premier usage, une fenêtre peut demander l'accès au trousseau pour la clé de Shield :
cliquez sur « Toujours autoriser ».

---

## Utiliser au quotidien

### Avec Claude (Claude Desktop, Claude Code, Cowork)

1. Dans Shield Desk, page **Dossiers**, rubrique « Ajouter un dossier » : indiquez le chemin complet du
   répertoire du dossier client, puis cliquez sur « Ajouter et analyser ».
   Shield lui donne un code (DOSSIER_1) et lit les pièces.
   Pour copier le chemin d'un dossier : sur Mac, dans le Finder, clic droit sur le dossier en tenant la touche
   Option, puis « Copier … comme chemin d'accès » ; sous Windows, Maj + clic droit, puis
   « Copier en tant que chemin d'accès ».
2. Cliquez sur « Voir les entités » pour voir la liste des noms détectés. Ajoutez ceux qui manquent avec
   « Ajouter un nom ou un terme », au-dessus de la liste : le client, les parties, un nom de projet.
   Activez l'interrupteur « Garder en clair » pour un nom qui doit rester lisible.
3. Dans Claude, demandez par exemple :
   « Liste mes dossiers Shield. Lis les pièces du DOSSIER_1 et prépare un projet de conclusions.
   Enregistre le projet avec Shield. »
4. Claude ne voit que des codes. Il enregistre le projet avec l'outil Shield.
5. Shield écrit le document, avec les vrais noms, dans le sous-répertoire **« Shield - sorties »**
   du dossier client. Ouvrez-le sur votre ordinateur et relisez-le.

Claude ne peut pas demander à Shield les vrais noms. Seul votre ordinateur les remet.
Les mêmes étapes valent pour ChatGPT desktop, Codex et GitHub Copilot dans VS Code.

### Avec toute autre application, par Shield Desk

Pour claude.ai, chatgpt.com, Microsoft 365 Copilot, Word et Outlook.

1. Ouvrez Shield Desk avec le lien affiché par sa commande (voir Installer), page **Masquer**. Choisissez le
   dossier. Sans dossier, les noms enregistrés deviennent [PERSONNE] ou [SOCIETE] et la restauration est
   impossible.
2. Collez votre texte dans « Texte d'origine » (pas dans le chat), puis cliquez sur « Masquer ».
3. Vérifiez les éléments détectés, puis cliquez sur « Copier le texte masqué ».
4. Collez le texte masqué dans l'application d'IA.
5. Copiez la réponse de l'IA. Dans Shield Desk, page **Restaurer**, collez-la, puis cliquez sur
   « Restaurer les noms ». Shield affiche aussi les « codes inconnus dans ce dossier »
   (par exemple un code inventé par l'IA). Copiez le texte restauré dans votre document.
   Ne le recollez jamais dans le chat : il contient les vrais noms.

Pour les habitués du terminal, la même chose en deux commandes :
`ragbase-shield mask --dossier DOSSIER_1 --clipboard` remplace le contenu du presse-papiers par le texte masqué.
`ragbase-shield restore --dossier DOSSIER_1 --clipboard` remet les vrais noms dans le presse-papiers.

---

## Résultats

Tout masquer est facile, mais Claude ne peut plus travailler. Shield masque les données de vos clients et garde le droit
lisible. Nous avons mesuré Shield face à Hexagone et à Presidio sur quatre benchmarks en français, tous publics.

| | Shield 0.4.1 Rapide | Shield 0.4.1 Précis | Hexagone 0.3.9 Rapide | Hexagone 0.3.9 Précis | Presidio 2.2.364 |
|---|---|---|---|---|---|
| **Score global (F1), plus haut = mieux** | | | | | |
| FR-PII-Bench | **96,9** | 96,2 | 80,7 | 80,7 | 66,5 |
| MAPA | 80,4 | **82,2** | 43,8 | 37,9 | 63,5 |
| REF | **97,1** | **97,1** | 66,7 | 61,1 | 79,2 |
| Max | **95,3** | 91,8 | 54,0 | 48,9 | 47,4 |
| **Termes juridiques modifiés, plus bas = mieux** | | | | | |
| MAPA | **0,0 %** | **0,0 %** | 43,1 % | 47,6 % | 18,0 % |
| REF | **4,1 %** | **4,1 %** | 17,8 % | 47,1 % | 15,3 % |
| Max | **2,1 %** | 4,2 % | 47,2 % | 58,3 % | 55,6 % |
| **Vitesse et mémoire, plus bas = mieux** | | | | | |
| Temps pour un document | **0,61 s** | 17,7 s | 26,93 s | 9 min | 1,59 s |
| Mémoire au pic | **78 à 79 Mo** | 3,7 à 3,8 Go | 1,6 à 1,7 Go | 3,8 à 5,4 Go | 0,57 Go |

Rapide est le mode par défaut. Précis ajoute un modèle d'IA qui tourne sur votre ordinateur. La meilleure valeur de
chaque ligne est en gras.

Méthode et résultats détaillés : [evaluation/laptop/RESULTS_PUBLIC.md](evaluation/laptop/RESULTS_PUBLIC.md) (en anglais).

REF et Max, avec leurs corrigés et une commande qui reproduit les résultats de Shield et de Presidio : [evaluation/datasets](evaluation/datasets).

---

## Les limites (à lire)

- **Pas d'OCR.** Un PDF scanné (une image) ne contient pas de texte. Shield le signale et ne le lit pas.
- **La détection n'est jamais complète.** Un nom que personne n'a enregistré peut passer :
  nom rare, nom étranger, surnom, faute de frappe. Enregistrez les parties de chaque dossier.
  Ce sont elles que Shield masque le plus sûrement. Vérifiez la liste des noms détectés, et relisez le texte masqué
  avant de l'envoyer.
- **Les noms restaurés suivent l'orthographe enregistrée dans le dossier.** « M. Mercadier » peut revenir
  en « M. Thibault Mercadier », et les majuscules peuvent changer. Les identifiants reviennent dans la première
  écriture vue dans le dossier (par exemple « 832 456 719 » pour « 832456719 »). Relisez le document restauré.
- **Les faits peuvent identifier un client**, même sans son nom : une affaire connue, une fonction unique,
  un lieu précis, un montant. Shield ne masque pas les faits. Relisez, et généralisez si besoin.
- **ChatGPT web (chatgpt.com) n'a pas de branchement direct.** Utilisez Shield Desk ou l'extension de navigateur.
- **Microsoft 365 Copilot (Word, Outlook, Teams, application Copilot) : seulement via Shield Desk.**
  Attention : Copilot dans Word ou Outlook lit le document ou l'e-mail ouvert.
  Ouvrez une copie masquée, pas l'original.
- **L'extension de navigateur masque le texte que vous collez ou que vous glissez.** Le texte tapé au clavier
  part tel quel. Un fichier collé ou glissé dans le chat est bloqué ; « Joindre quand même » l'envoie sans masquage.
  Elle n'est pas encore dans les boutiques Chrome et Edge.
- **Les installateurs ne sont pas encore signés.** Le Mac et Windows affichent un avertissement la première fois.
- **Un administrateur peut bloquer Shield** : extensions dans Claude Team ou Enterprise,
  serveurs MCP dans Copilot Business ou Enterprise.
- **Le RGPD continue de s'appliquer.** Pour vous, des données pseudonymisées restent des données personnelles.
  Shield réduit ce que le fournisseur d'IA reçoit. Ce n'est pas une garantie de conformité.

Fiche conformité (CNB, barreau de Paris, avocats aux Conseils, RGPD) : [docs/CONFORMITE.fr.md](docs/CONFORMITE.fr.md)
Questions fréquentes : [docs/FAQ.md](docs/FAQ.md)

---

## Le modèle de confidentialité en 5 lignes

1. Le masquage et la restauration se font sur votre ordinateur. Le fournisseur d'IA reçoit des codes, jamais les
   vrais noms que Shield a détectés ou que vous avez enregistrés.
2. La table codes / noms (le coffre) est chiffrée, une par dossier ; sa clé reste dans le trousseau du système
   (ou dans un fichier lisible par vous seul).
3. Aucun outil ne remet les vrais noms au modèle, et un agent IA ne peut pas changer ce qui est masqué.
4. Aucun appel réseau dans la bibliothèque, aucune télémétrie, aucune vérification de mise à jour. Le seul
   téléchargement, lancé par vous, est le modèle IA optionnel du mode Précis.
5. Des données pseudonymisées restent des données personnelles : Shield réduit ce que voit le fournisseur. C'est
   une pseudonymisation, pas une anonymisation.

Modèle complet : [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md).

---

## Pour les développeurs et l'informatique du cabinet

### Architecture en bref

- **Mode Rapide** (par défaut ; nom technique : règles). Un moteur local de règles, de dictionnaires et de chiffres
  de contrôle détecte les noms et les identifiants, en français et en anglais (la langue est détectée par texte, ou
  fixée avec `RAGBASE_SHIELD_LANGUAGE`).
- **Mode Précis** (optionnel ; nom technique : GLiNER). Un modèle IA de reconnaissance des noms travaille à côté
  des règles. Il pèse environ 1,2 Go, sa licence est Apache-2.0 et il fonctionne hors ligne, sur le processeur.
  Aucun modèle n'est installé par défaut. Pour l'ajouter :

  ```
  pip install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  # ou, avec uv : uv tool install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
  ragbase-shield ner download            # fastino/gliner2-privacy-filter-PII-multi, une fois, dans ~/.ragbase-shield/models
  ragbase-shield ner status              # ou : ragbase-shield doctor
  ```

  Ce que le modèle trouve passe par la même liste blanche et les mêmes garde-fous que les règles ; les hooks et
  le contrôle final ne l'utilisent jamais. `RAGBASE_SHIELD_NER=off` le désactive.
- Remplacement par des codes (`PERSONNE_A`) par défaut, ou par des pseudonymes réalistes (`ragbase-shield set
  DOSSIER_n --replacement synthetic`) : réversible par le coffre, pseudonymisation et non anonymisation.
- Un coffre chiffré par dossier (SQLite + Fernet). La clé est dans le trousseau du système,
  sinon dans un fichier lisible par vous seul (mode 0600).
- Un serveur MCP local (stdio) pour Claude, ChatGPT desktop, Codex et VS Code.
  Ses outils prennent des codes de dossier et de document, jamais du texte brut.
  Aucun outil ne remet les vrais noms au modèle.
- Shield Desk : une page web locale sur 127.0.0.1, avec un jeton par installation.
- Des hooks Claude Code bloquent un prompt qui contient un nom enregistré, et les lectures directes d'un dossier.
- Aucun appel réseau dans le code de la bibliothèque. Aucune télémétrie.

Contrat complet : [ARCHITECTURE.md](ARCHITECTURE.md). Modèle de confidentialité : [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md).

### Ligne de commande

```
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

Avec uv, installez la commande une fois pour toutes, depuis le fichier wheel de la version :

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
```

Ou lancez une commande sans l'installer :

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield doctor
```

Depuis une copie du dépôt : `uv tool install .` (ou `uv tool install --editable .` pour développer).
Les configurations écrites par `install` marchent alors, et `doctor` vérifie que chaque application peut
démarrer Shield.

Depuis le terminal d'un agent IA (Claude Code, Codex), `entities`, `restore` et `export` refusent de
s'exécuter, car ce qu'elles affichent part chez le modèle. `add`, `register`, `keep-clear` et `import` refusent
aussi : un assistant IA ne peut pas changer ce qui est masqué. `list` n'affiche que les codes.
Lancez ces commandes dans votre propre terminal, ou utilisez Shield Desk.

### Applications prises en charge

| Application | Branchement |
|---|---|
| Claude Desktop | Extension en un clic (`.mcpb`) qui lance le serveur MCP local |
| Claude Code et Cowork | Plugin : serveur MCP + skill + hooks |
| ChatGPT desktop et Codex | Serveur MCP local (`~/.codex/config.toml`), là où le MCP local est permis |
| GitHub Copilot (VS Code) | Serveur MCP local (`mcp.json`) |
| Toute autre application (claude.ai, chatgpt.com, Copilot, Word, Outlook) | Shield Desk, presse-papiers, extension de navigateur |

### Vérifier soi-même

- `ragbase-shield doctor` vérifie l'installation, le stockage de la clé et chaque intégration.
- `ragbase-shield verify` place des données inventées, passe par chaque chemin (outils MCP, hooks, Desk)
  et affiche CLEAN ou LEAK.
- Tests : `uv run --extra dev pytest -q`. Données inventées seulement.
- Banc de non-régression : `uv run python bench/run_bench.py` (rappel et précision par type, sur un corpus
  juridique français inventé).
- Scripts d'évaluation : `evaluation/public/` (benchmarks publics ; données téléchargées dans le dossier
  `.bench_data/`, ignoré par git), `evaluation/holdout-en/` (un corpus anglais inventé), `evaluation/laptop/`
  (les scripts et les résultats du benchmark), `evaluation/datasets/` (les benchmarks REF et Max, avec leurs
  corrigés).
- Installateurs de bureau : [packaging/README.md](packaging/README.md).

### Variables d'environnement

| Variable | Effet |
|---|---|
| `RAGBASE_SHIELD_HOME` | Répertoire des données (par défaut `~/.ragbase-shield`, ou `%LOCALAPPDATA%\ragbase-shield` sous Windows) |
| `RAGBASE_SHIELD_LOCALE=en` | Codes en anglais (PERSON_A, COMPANY_A) au lieu de PERSONNE_A, SOCIETE_A |
| `RAGBASE_SHIELD_PORT` | Port de Shield Desk (par défaut 7878) |
| `RAGBASE_SHIELD_KEYRING=0` | Clé dans un fichier 0600 au lieu du trousseau du système |
| `RAGBASE_SHIELD_MASK_TOQUE=0` | Laisse visibles les numéros de toque des avocats (masqués par défaut) |
| `RAGBASE_SHIELD_LOWERCASE_NAMES=0` | Désactive les règles pour les noms en minuscules après une civilité et pour les textes tapés sans majuscules (actives par défaut) |

### Contribuer, sécurité, licence

- Failles de sécurité : [SECURITY.md](SECURITY.md). N'ouvrez pas de ticket public.
- Historique des versions : [CHANGELOG.md](CHANGELOG.md).
- Licence : [Apache-2.0](LICENSE). Attributions : [NOTICE](NOTICE). Benchmarks de `evaluation/datasets` : [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Données de test : inventées seulement. N'envoyez jamais de vraies données de client dans un ticket.

---

## Liens

- Code source : https://github.com/ragbase/ragbase-shield
- Versions (installateurs, `.mcpb`, `SHA256SUMS`) : https://github.com/ragbase/ragbase-shield/releases/latest
- Signaler un problème : https://github.com/ragbase/ragbase-shield/issues
- Page du produit : https://shield.ragbase.ai
- Guide d'installation par application : [docs/INSTALL.md](docs/INSTALL.md). Questions fréquentes : [docs/FAQ.md](docs/FAQ.md).
- Résultats publics : [evaluation/laptop/RESULTS_PUBLIC.md](evaluation/laptop/RESULTS_PUBLIC.md)

---

## Pour aller plus loin

Shield réduit ce que l'IA voit. Il ne remplace pas une IA qui tourne chez vous.
Si votre cabinet veut une IA privée, installée sur ses propres machines, RAGbase en propose une :
https://ragbase.ai
