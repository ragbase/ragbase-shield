# Installer RAGbase Shield / Install RAGbase Shield

Partie 1 en français. [Part 2 in English](#part-2-english).

---

## Partie 1. Français

Sommaire :

0. [Installer en un clic](#0-installer-en-un-clic) (autre méthode :
   [uv et le Terminal](#0-bis-autre-méthode--uv-et-shield-desk-terminal))
1. [Ajouter un dossier client](#1-ajouter-un-dossier-client)
2. [Claude Desktop (un clic)](#2-claude-desktop-un-clic)
3. [Claude Code et Cowork (plugin)](#3-claude-code-et-cowork-plugin)
4. [ChatGPT desktop et Codex](#4-chatgpt-desktop-et-codex)
5. [GitHub Copilot dans VS Code](#5-github-copilot-dans-vs-code)
6. [Microsoft 365 Copilot, Word, Outlook, application Copilot](#6-microsoft-365-copilot-word-outlook-application-copilot)
7. [Toute application web (claude.ai, chatgpt.com, Copilot web)](#7-toute-application-web-claudeai-chatgptcom-copilot-web)
8. [Vérifier que tout fonctionne](#8-vérifier-que-tout-fonctionne)
9. [Mettre à jour, désinstaller](#9-mettre-à-jour-désinstaller)

Avant de commencer, retenez trois règles :

- Connectez un dossier, n'attachez pas le fichier au chat.
- Ne collez pas de texte brut dans le chat. Passez par Shield.
- Un texte déjà envoyé ne peut pas être rappelé.

### 0. Installer en un clic

L'installateur met RAGbase Shield sur votre ordinateur sans Terminal. Il est prévu sans mot de passe
administrateur : tout va dans votre dossier personnel. Il installe :

- Shield, avec sa propre copie de Python : aucun autre logiciel n'est nécessaire ;
- Shield Desk, qui tourne en arrière-plan et démarre à chaque ouverture de session ;
- une icône en forme de bouclier : dans la barre des menus sur Mac, dans la zone de notification sous Windows.

Après l'installation, Shield n'utilise plus Internet, sauf si vous téléchargez vous-même le modèle IA du mode
Précis (section 10). Shield n'envoie aucune statistique d'utilisation.

> **Fichiers non signés.** RAGbase ne signe pas encore les fichiers d'installation. Au premier
> lancement, le Mac et Windows affichent donc un avertissement. Les étapes ci-dessous expliquent comment
> continuer. Téléchargez les fichiers seulement sur la page des versions du dépôt :
> https://github.com/ragbase/ragbase-shield/releases/latest. Comparez l'empreinte SHA-256 du fichier avec le fichier `SHA256SUMS` de la même page
> avant de l'ouvrir.

#### Mac : le fichier .pkg

Il faut macOS 13 ou plus récent. Le même fichier sert aux Mac Intel et aux Mac Apple (puce M).

1. Téléchargez `RAGbase-Shield-<version>.pkg` sur la page des versions du dépôt.
2. Double-cliquez sur le fichier. macOS indique qu'il n'a pas pu vérifier le fichier et ne l'ouvre pas, car il
   n'est pas signé. Cliquez sur « Terminé ». Ne cliquez pas sur « Placer dans la corbeille ».

3. Ouvrez le menu Pomme > Réglages Système > Confidentialité et sécurité. Faites défiler jusqu'à « Sécurité ».
   Près du message sur `RAGbase-Shield`, cliquez sur « Ouvrir quand même ». Ce bouton reste disponible environ
   une heure après l'étape 2. macOS demande de confirmer : cliquez de nouveau sur « Ouvrir quand même », puis
   saisissez le mot de passe de votre Mac (ou utilisez Touch ID).

4. Le programme d'installation s'ouvre. Cliquez sur « Continuer », acceptez la licence, puis cliquez sur
   « Installer ». Si une question porte sur l'emplacement, choisissez « Installer pour moi uniquement ».
   Le programme ne doit pas demander de mot de passe administrateur : s'il en demande un, arrêtez et
   prévenez RAGbase.

5. Cliquez sur « Fermer ». Quelques secondes plus tard, l'icône bouclier apparaît dans la barre des menus,
   en haut à droite. macOS peut signaler un nouvel élément d'arrière-plan « RAGbase Shield » : c'est normal.

6. Cliquez sur l'icône, puis sur « Ouvrir Shield Desk ». La page Shield Desk s'ouvre dans votre navigateur.
   Ajoutez votre premier dossier (section 1).
7. Au premier accès au coffre, macOS demande l'accès au trousseau pour « RAGbase Shield » : cliquez sur
   « Toujours autoriser ». macOS peut aussi demander l'accès à Documents, Bureau ou Téléchargements :
   cliquez sur « Autoriser », sinon Shield ne peut pas lire les dossiers que vous connectez.

Pas d'icône ? Sur un MacBook avec encoche, une barre des menus pleine peut la cacher : déplacez ou retirez
une autre icône (touche Cmd enfoncée, glissez-la). Sinon, fermez votre session, puis rouvrez-la.

#### Windows : le fichier .msi

Il faut Windows 10 ou 11 (64 bits). Une carte graphique n'est pas nécessaire. Sur un PC Windows ARM
(Snapdragon), Shield fonctionne en émulation, un peu plus lentement.

1. Téléchargez `RAGbase-Shield-<version>-win64.msi` sur la page des versions du dépôt (un fichier `.msi`
   envoyé en pièce jointe est bloqué par Outlook et Gmail). Le navigateur peut avertir que ce fichier
   « n'est pas couramment téléchargé » : gardez-le (Edge : « ... », « Conserver », puis « Afficher plus »
   et « Conserver quand même »).
2. Double-cliquez sur le fichier. Windows affiche « Windows a protégé votre ordinateur » et « Microsoft
   Defender SmartScreen a empêché le démarrage d'une application non reconnue », car le fichier n'est pas
   signé. Cliquez sur « Informations complémentaires » : la fenêtre montre « Application :
   RAGbase-Shield-<version>-win64.msi » et « Éditeur : Éditeur inconnu ». Cliquez sur « Exécuter quand même ».
   Pour cet avertissement, Windows envoie l'empreinte et l'adresse de téléchargement du fichier à Microsoft :
   c'est Windows (SmartScreen), pas Shield.
   Si Windows affiche ensuite « Ouvrir un fichier - Avertissement de sécurité », cliquez sur « Exécuter ».
   Si le bouton « Exécuter quand même » n'apparaît pas : sur certains PC Windows 11, le Contrôle intelligent des
   applications (Smart App Control) est actif et bloque les installateurs non signés, sans bouton pour continuer.
   Utilisez alors la méthode avec uv (section 0 bis) ou attendez l'installateur signé. Ne désactivez pas cette
   protection. Dans un cabinet, une règle du service informatique peut aussi bloquer le fichier : contactez-le.

3. L'installation se fait pour votre compte seulement. Elle est prévue sans mot de passe administrateur.
   Une petite fenêtre de progression s'affiche, puis se ferme toute seule (moins d'une
   minute). Windows 11 peut ensuite signaler que RAGbase Shield a été ajouté aux applications de
   démarrage : c'est normal.

4. L'icône bouclier apparaît dans la zone de notification, près de l'horloge. Si vous ne la voyez pas,
   cliquez sur la petite flèche (^) qui montre les icônes cachées. Pour la garder toujours visible :
   Paramètres > Personnalisation > Barre des tâches > Autres icônes de la barre d'état système, puis
   activez RAGbase Shield.

5. Clic droit sur l'icône, puis « Ouvrir Shield Desk ». Ajoutez votre premier dossier (section 1).

#### Le menu de l'icône

| Élément du menu | Ce qu'il fait |
|---|---|
| Shield Desk : en marche, port 7878, ... | Montre l'état de Shield Desk : port, version, mode (« règles » = mode Rapide ; « règles + NER » = mode Précis). Sous Windows : « Statut... ». |
| Ouvrir Shield Desk | Ouvre la page Shield Desk dans votre navigateur, avec le lien privé. |
| Dossiers | Mac : la liste de vos dossiers ; un clic ouvre le dossier dans le Finder. Windows : « Dossiers (Shield Desk) » ouvre la page Dossiers. |
| Dossier de données Shield | Ouvre le dossier des coffres et de la clé. |
| Redémarrer | Redémarre Shield Desk. |
| Lancer à l'ouverture de session | Coché : Shield démarre à chaque ouverture de session. |
| Ouvrir le journal | Ouvre le dossier des journaux, pour le support. Les journaux ne contiennent ni noms ni jeton. |
| Désinstaller... | Retire Shield de l'ordinateur. Vos dossiers et vos coffres restent. |
| Quitter | Arrête Shield Desk jusqu'à la prochaine ouverture de session. L'extension de navigateur ne répond plus. |

#### Après l'installation : vos applications

| Application | À faire |
|---|---|
| Shield Desk et l'extension de navigateur | Rien : Shield Desk tourne toujours, sans fenêtre de terminal. Pour l'extension, collez le jeton dans ses options (section 7). |
| Claude Desktop | Installez le fichier `.mcpb` (section 2). |
| Claude Code et Cowork (plugin) | Le plugin a encore besoin de uv : installez uv (section 0 bis, première commande), puis suivez la section 3. |
| ChatGPT desktop, Codex, VS Code | Une commande dans le Terminal (ci-dessous). Ces applications utilisent ensuite le Shield installé, sans uv. |

Sur Mac (remplacez `codex` par `chatgpt` ou `vscode` selon l'application) :

```sh
"$HOME/Library/Application Support/RAGbase Shield/bin/ragbase-shield" install codex
```

Sous Windows (PowerShell) :

```powershell
& "$env:LOCALAPPDATA\Programs\RAGbase Shield\bin\ragbase-shield.cmd" install codex
```

Les autres commandes `ragbase-shield ...` de ce guide marchent aussi avec ce chemin.

#### Mettre à jour, désinstaller

**Mettre à jour :** téléchargez le nouveau fichier `.pkg` ou `.msi`, puis lancez-le comme la première fois.
Vos dossiers, vos coffres et vos réglages restent. Sous Windows, fermez d'abord Claude Desktop, ChatGPT,
Codex et VS Code : ils utilisent les fichiers de Shield. Sinon Windows termine le remplacement au prochain
redémarrage (il ne redémarre pas tout seul et ne vous le demande pas).

**Désinstaller :** icône Shield > « Désinstaller... ». Sous Windows, Paramètres > Applications > RAGbase
Shield > Désinstaller marche aussi ; fermez d'abord les mêmes applications que pour une mise à jour. Vos dossiers et vos coffres restent dans `~/.ragbase-shield` (Windows :
`%LOCALAPPDATA%\ragbase-shield`) ; pour tout effacer, voir la section 9. Retirez aussi Shield de vos
applications (section 9) : leurs réglages pointent encore vers le Shield désinstallé.

Sur Mac, le service informatique peut aussi lancer
`"$HOME/Library/Application Support/RAGbase Shield/uninstall.sh"`. Avec `--purge-data`, ce script efface
aussi les coffres et la clé : c'est irréversible.

Bon à savoir :

- Après « Quitter », Shield revient à la prochaine ouverture de session. Pour le relancer tout de suite,
  fermez votre session, puis rouvrez-la. Sous Windows, menu Démarrer > RAGbase Shield le relance aussi.
- Si l'icône affiche « port 7878 occupé par un autre programme », un autre logiciel utilise ce port.
  Prévenez RAGbase.
- Le mode Précis (section 10) n'est pas encore disponible avec l'installateur en un clic.
- Relancer le même fichier `.msi` ne réinstalle rien : Shield redémarre, c'est tout. Pour réparer une
  installation abîmée, désinstallez, puis réinstallez.
- Pas d'icône une minute après l'installation ? Menu Démarrer > RAGbase Shield. Toujours rien : une règle du
  cabinet bloque les programmes du dossier utilisateur (AppLocker, Smart App Control) ; contactez votre
  service informatique (fiche `packaging/windows/IT_SHEET.md`).
- Message « Cette installation est interdite par la stratégie système » (code 1625) : la règle « Interdire les
  installations par utilisateur » est active ; service informatique.
- L'icône ne revient pas à l'ouverture de session ? Gestionnaire des tâches > Applications de démarrage >
  RAGbase Shield doit être « Activé ». Si une règle du cabinet ignore cette liste, le service informatique
  crée une tâche planifiée (fiche IT).
- Vous utilisiez déjà Shield avec uv ? Vos dossiers et vos coffres sont repris (même dossier de données).
  Relancez `install` pour chaque application (tableau ci-dessus) : sinon Claude Desktop, Codex ou VS Code
  continuent d'utiliser l'ancien Shield lancé par `uvx`. La commande `ragbase-shield` de uv ne désigne pas
  le Shield installé : `uv tool uninstall ragbase-shield` si vous l'aviez installée.

### 0 bis. Autre méthode : uv et Shield Desk (Terminal)

Cette méthode passe par le Terminal. Elle sert aux habitués du Terminal, au plugin Claude Code (section 3)
et au mode Précis (section 10).

uv est l'outil open source qui télécharge et lance Shield. Il s'installe en une commande.

**Mac.** Ouvrez l'application Terminal (Applications > Utilitaires). Collez cette ligne, puis Entrée :

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows.** Ouvrez PowerShell (menu Démarrer, tapez « PowerShell »). Collez cette ligne, puis Entrée :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Si uv est déjà installé sur votre ordinateur, collez quand même cette ligne : elle met uv à jour.

Fermez la fenêtre, puis ouvrez-en une nouvelle.

> **Depuis une copie du dépôt (développement).** Dans le dossier du dépôt, tapez une seule fois
> `uv tool install .` : les commandes `ragbase-shield` de ce guide utilisent alors cette copie.
> `ragbase-shield doctor` le vérifie.

Installez la commande `ragbase-shield` une fois, depuis le fichier wheel de la version, puis lancez Shield Desk :

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield desk
```

Le navigateur s'ouvre sur **http://127.0.0.1:7878**, avec un lien privé qui contient un jeton secret.
Cette page est locale : elle n'existe que sur votre ordinateur.
Pour la rouvrir, relancez `ragbase-shield desk` ou utilisez le lien affiché dans le terminal : l'adresse seule, sans
le jeton, affiche « Jeton refusé ». Si Shield Desk tourne déjà, la commande affiche de nouveau le lien.
Laissez la fenêtre du terminal ouverte. Pour arrêter Shield Desk, fermez-la (ou Ctrl+C) : l'extension de
navigateur s'arrête aussi.

Pour lancer Shield Desk sans installer la commande :

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk
```


### 1. Ajouter un dossier client

Toutes les applications ont besoin de cette étape. Elle se fait sur votre ordinateur, pas dans le chat.

**Avec Shield Desk.** Page **Dossiers**, rubrique « Ajouter un dossier » : indiquez le chemin complet du
répertoire, puis cliquez sur « Ajouter et analyser ». Shield lui donne un code (DOSSIER_1) et lit les pièces.
Cliquez sur « Voir les entités » pour voir les noms détectés. Ajoutez ceux qui manquent avec
« Ajouter un nom ou un terme », au-dessus de la liste (client, parties, nom de projet). Activez l'interrupteur
« Garder en clair » pour un nom qui doit rester lisible.

Copier le chemin d'un dossier : sur Mac, dans le Finder, clic droit sur le dossier en tenant la touche Option,
puis « Copier … comme chemin d'accès ». Sous Windows, Maj + clic droit sur le dossier, puis
« Copier en tant que chemin d'accès ».

**Avec le terminal**, dans votre propre terminal (pas dans celui d'un assistant IA : `add`, `register` et
`entities` y refusent de s'exécuter). Ces commandes demandent la commande `ragbase-shield` : installez-la une
fois (section 0 bis).

```sh
ragbase-shield add "/chemin/vers/le/dossier" --title "Mercadier c. Ateliers Brunelac"
ragbase-shield entities DOSSIER_1
ragbase-shield register DOSSIER_1 --person "Thibault Mercadier"
ragbase-shield register DOSSIER_1 --org "Ateliers Brunelac"
```

Le titre et le chemin restent sur votre ordinateur. L'IA ne voit que DOSSIER_1.

### 2. Claude Desktop (un clic)

1. Faites l'étape 0 (ou 0 bis) si ce n'est pas déjà fait : Shield Desk sert à ajouter vos dossiers.
   Téléchargez `ragbase-shield-0.4.1.mcpb` sur la page des versions du dépôt :
   https://github.com/ragbase/ragbase-shield/releases/latest.
2. Double-cliquez sur le fichier. Claude Desktop s'ouvre et affiche l'extension. Cliquez sur « Installer ».
   Autre méthode : dans Claude Desktop, Réglages > Extensions, glissez le fichier dans la fenêtre.
3. Ouvrez une nouvelle conversation et demandez : « Quel est le statut de Shield ? ».
   Claude doit utiliser l'outil `shield_status`.

Autre méthode, depuis le terminal (la ligne `--dry-run` montre ce qui sera modifié, sans rien écrire) :

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install claude-desktop --dry-run
ragbase-shield install claude-desktop
```

Bon à savoir :

- Au premier lancement, Claude Desktop télécharge lui-même Python et les composants de l'extension : il
  faut une connexion Internet cette fois-là. Si Claude affiche une erreur qui parle de uv, installez uv
  (section 0 bis), puis relancez Claude Desktop.
- Sur Mac, au premier usage, une fenêtre peut demander l'accès au trousseau pour la clé de RAGbase Shield
  (l'extension tourne avec un autre programme que Shield Desk) : cliquez sur « Toujours autoriser ».
  Si vous refusez, les outils Shield répondent « coffre illisible » : rien n'est montré à Claude.
- Dans Claude Team ou Enterprise, un administrateur peut bloquer les extensions.
- N'attachez pas les pièces au chat. Demandez à Claude de les lire avec Shield.

### 3. Claude Code et Cowork (plugin)

Le plugin installe trois choses : le serveur MCP de Shield, une compétence (skill) qui apprend à Claude
la bonne méthode, et des hooks qui bloquent les erreurs :

- un prompt qui contient un nom enregistré est bloqué. Claude Code vous dit quel code utiliser ;
- la lecture directe d'un fichier d'un dossier enregistré est refusée. Claude passe par Shield ;
- un nom enregistré qui reste dans un résultat d'outil est masqué.

**Méthode plugin (dans Claude Code), recommandée :**

```text
/plugin marketplace add ragbase/ragbase-shield
/plugin install ragbase-shield@ragbase
```

Depuis une copie du dépôt : `/plugin marketplace add /chemin/vers/ragbase-shield`.

**Cowork.** Dans l'application Claude : Customize > Plugins > Add > Add marketplace. Saisissez
`ragbase/ragbase-shield` (ou le chemin d'une copie du dépôt), puis installez RAGbase Shield. Les libellés de
l'écran peuvent changer.

**Méthode terminal :**

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install claude-code --dry-run
ragbase-shield install claude-code
```

Attention : lancée depuis une copie du projet (ou avec `RAGBASE_SHIELD_MARKETPLACE=<dossier du projet>`), cette
commande installe le plugin complet. Sinon, elle installe le **serveur MCP seul, sans les hooks ni la
compétence** : rien ne bloque alors un vrai nom tapé dans Claude Code. La commande l'affiche. Préférez la
méthode plugin.

Bon à savoir : un serveur MCP local fourni par un plugin ne fonctionne pas dans le chat de Claude Desktop.
Pour le chat, utilisez l'extension `.mcpb` (section 2).

### 4. ChatGPT desktop et Codex

**Méthode simple (terminal) :**

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install chatgpt --dry-run
ragbase-shield install chatgpt
ragbase-shield install codex
```

Ces commandes ajoutent Shield dans `~/.codex/config.toml` : la ligne `install chatgpt` pour ChatGPT desktop, la
ligne `install codex` pour Codex.

**Méthode manuelle (Codex).** Ajoutez ce bloc dans `~/.codex/config.toml`
(sous Windows : `%USERPROFILE%\.codex\config.toml`), puis relancez l'application.
Version commentée : [integrations/codex/config.toml.example](../integrations/codex/config.toml.example).

```toml
[mcp_servers.ragbase-shield]
command = "uvx"
args = ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl", "ragbase-shield", "mcp"]
startup_timeout_sec = 60
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

Le premier démarrage télécharge Shield : c'est pourquoi le délai est de 60 secondes.
Avec `"writes"`, les outils de lecture tournent sans question ; l'enregistrement d'un projet
(`shield_save_draft`) vous demande d'abord votre accord.

**Méthode manuelle (ChatGPT desktop).** Settings > MCP servers > Add server.
Nom : `ragbase-shield`. Type : STDIO. Commande : `uvx`. Arguments : le bloc ci-dessous.
Enregistrez, puis cliquez sur Restart.

```text
--from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield mcp
```

Bon à savoir :

- Shield fonctionne dans les conversations Work locales (qui tournent sur cet ordinateur) et dans Codex.
  Les conversations Work hébergées (dans le cloud) ne voient pas Shield.
- Offres Business, Edu et Enterprise : un administrateur peut limiter les serveurs MCP. S'il n'apparaît pas,
  demandez à votre administrateur.
- Les libellés de l'écran peuvent changer.
- ChatGPT web (chatgpt.com) n'a pas de branchement direct. Utilisez Shield Desk ou l'extension (section 7).

### 5. GitHub Copilot dans VS Code

**Méthode simple (terminal) :**

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install vscode --dry-run
ragbase-shield install vscode
```

**Méthode un clic.** Depuis l'ordinateur où VS Code est installé, cliquez sur
[Installer RAGbase Shield dans VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=ragbase-shield&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22https%3A%2F%2Fgithub.com%2Fragbase%2Fragbase-shield%2Freleases%2Fdownload%2Fv0.4.1%2Fragbase_shield-0.4.1-py3-none-any.whl%22%2C%22ragbase-shield%22%2C%22mcp%22%5D%7D).

**Méthode manuelle.** VS Code lit de préférence le fichier `.mcp.json` à la racine du projet, ou
`~/.copilot/mcp-config.json` pour tous vos projets (clé `"mcpServers"` au lieu de `"servers"`, même contenu).
Les anciens emplacements marchent encore : `.vscode/mcp.json` dans le projet, ou le `mcp.json` de votre profil
(c'est là que `ragbase-shield install vscode` écrit) :

```json
{
  "servers": {
    "ragbase-shield": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl", "ragbase-shield", "mcp"]
    }
  }
}
```

Au premier démarrage, VS Code demande si vous faites confiance au serveur : acceptez pour `ragbase-shield`.
Ouvrez Copilot Chat en mode Agent. Les outils `shield_*` apparaissent dans la liste des outils.
Les hooks qui bloquent les vrais noms existent seulement dans Claude Code : dans VS Code, écrivez les codes vous-même.
Détails : [integrations/vscode/README.md](../integrations/vscode/README.md).

Bon à savoir : dans Copilot Business et Copilot Enterprise, la règle « serveurs MCP dans Copilot » est
désactivée par défaut. Un administrateur de l'organisation doit l'activer.

### 6. Microsoft 365 Copilot, Word, Outlook, application Copilot

Il n'y a pas de branchement direct. Un connecteur distant pour Microsoft 365 verrait le texte en
clair, donc nous n'en construisons pas. Utilisez Shield Desk et le presse-papiers.

**Pour une question ou un passage de texte :**

1. Ouvrez Shield Desk (icône Shield > « Ouvrir Shield Desk », ou la commande de la section 0 bis), page
   **Masquer**. Choisissez le dossier.
2. Copiez le texte depuis Word ou Outlook. Collez-le dans « Texte d'origine » (pas dans Copilot),
   puis cliquez sur « Masquer ».
3. Vérifiez les éléments détectés, puis cliquez sur « Copier le texte masqué ».
4. Collez le texte masqué dans Copilot.
5. Copiez la réponse de Copilot. Dans Shield Desk, page **Restaurer**, collez-la, cliquez sur
   « Restaurer les noms », puis sur « Copier le texte restauré ». Collez-le dans votre document ou votre
   e-mail. Ne le recollez jamais dans Copilot : il contient les vrais noms.

**Pour un document entier dans Word :**

1. Dans Shield Desk, page **Fichiers**, déposez le document (« Déposez vos fichiers ici »).
   Cliquez sur « Télécharger (.txt) » pour récupérer la copie masquée.
2. Ouvrez la copie masquée dans Word (ou collez son texte dans un nouveau document). Utilisez Copilot sur
   cette copie seulement.
3. Restaurez le résultat dans Shield Desk, page **Restaurer**.

**Attention :** Copilot dans Word ou dans Outlook lit le document ou l'e-mail ouvert.
N'appelez jamais Copilot sur l'original. Ouvrez la copie masquée.

**Raccourci terminal** (le presse-papiers est remplacé directement ; il faut la commande `ragbase-shield`,
section 0 bis). Avant de coller dans Copilot :

```sh
ragbase-shield mask --dossier DOSSIER_1 --clipboard
```

Après avoir copié la réponse :

```sh
ragbase-shield restore --dossier DOSSIER_1 --clipboard
```

### 7. Toute application web (claude.ai, chatgpt.com, Copilot web)

**Shield Desk** fonctionne avec tous les sites : masquez, copiez, collez, puis restaurez (comme en section 6).

**L'extension de navigateur** (Chrome, Edge) masque le texte au moment où vous le collez sur chatgpt.com,
claude.ai, copilot.microsoft.com, m365.cloud.microsoft et gemini.google.com. Elle passe par Shield Desk sur votre ordinateur.
Les vrais noms ne reviennent que dans le panneau latéral de l'extension, jamais dans la page du site.

- À l'installation, l'extension ouvre sa page d'options. Dans Shield Desk, panneau « Extension navigateur »,
  cliquez sur « Copier le jeton », puis collez-le dans les options de l'extension. Ne collez jamais ce jeton
  dans un chat.
- Shield Desk doit être lancé. Si Desk est fermé, ne collez rien : lancez Desk d'abord.
- L'extension masque le texte collé. Le texte tapé au clavier part tel quel.
- L'extension n'est pas encore dans le Chrome Web Store ni dans Edge Add-ons. En attendant, utilisez Shield Desk.
  Un informaticien peut charger le répertoire `integrations/browser-extension` en mode développeur. Après un
  collage, vérifiez que la zone de saisie montre des codes avant d'envoyer.

### 8. Vérifier que tout fonctionne

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield doctor
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield verify
```

La ligne `doctor` vérifie l'installation, le stockage de la clé et chaque intégration. La ligne `verify` place des
données inventées, teste chaque chemin et affiche CLEAN ou LEAK.

CLEAN veut dire qu'aucune donnée inventée n'a fui par les chemins testés.
LEAK veut dire qu'un chemin a laissé passer une donnée : n'utilisez pas Shield, et signalez-le
(voir [SECURITY.md](../SECURITY.md)).

### 9. Mettre à jour, désinstaller

**Mettre à jour :** avec l'installateur en un clic (section 0), lancez le nouveau fichier `.pkg` ou `.msi`.
Avec uv, cette commande installe la version 0.4.1 ou remplace celle que vous avez. Relancez ensuite Shield Desk
et vos applications.

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
```

Mode Précis : relancez plutôt la commande du mode Précis (section 10).

**Désinstaller Shield installé en un clic :** icône Shield > « Désinstaller... » (détails en section 0).

**Retirer une intégration :**

- Claude Desktop : Réglages > Extensions > RAGbase Shield > désinstaller.
- Claude Code : `/plugin uninstall ragbase-shield@ragbase`.
- ChatGPT desktop, Codex : supprimez le bloc `[mcp_servers.ragbase-shield]` de `~/.codex/config.toml`.
- VS Code : supprimez l'entrée `ragbase-shield` de `mcp.json`.

**Supprimer les données :** supprimez le répertoire `~/.ragbase-shield` (ou `%LOCALAPPDATA%\ragbase-shield`
sous Windows).
Attention : ce répertoire contient les coffres. Sans eux, plus personne ne peut remettre les vrais noms dans
une ancienne réponse. Faites d'abord un export si vous en avez besoin (`ragbase-shield export`).
La clé peut aussi rester dans le trousseau du système : supprimez l'entrée `ragbase-shield` (compte `vault-key`)
si vous le souhaitez.

**Détails techniques par application** (pour l'informatique du cabinet) :
[Claude Desktop](../integrations/claude-desktop/README.md) ·
[Claude Code et Cowork](../integrations/claude-code/README.md) ·
[ChatGPT desktop et Codex](../integrations/chatgpt/README.md) ·
[VS Code](../integrations/vscode/README.md) ·
[Microsoft 365 Copilot](../integrations/microsoft-copilot/README.md) ·
[Extension de navigateur](../integrations/browser-extension/README.md) ·
[Vue d'ensemble](../integrations/README.md)

---

### 10. Option : le mode Précis (avec modèle IA)

Par défaut, Shield est en mode Rapide : il travaille avec ses règles et ses dictionnaires (français et anglais).
Le mode Précis ajoute un modèle IA local (nom technique : GLiNER). Ce modèle trouve en plus les noms sans titre ni
prénom connu, les sociétés sans forme juridique, les pseudonymes et les matricules.
Il tourne sur le processeur, hors ligne, et pèse environ 1,2 Go. Il s'installe avec uv (section 0 bis) :
l'installateur en un clic ne le prend pas encore en charge.

```sh
uv tool install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
ragbase-shield ner download
ragbase-shield ner status
```

`ner download` télécharge le modèle une fois, dans `~/.ragbase-shield/models`. `ner status` (ou
`ragbase-shield doctor`) affiche l'état du mode Précis.

`RAGBASE_SHIELD_NER=off` le désactive ; `RAGBASE_SHIELD_NER_MODEL=urchade` choisit l'autre modèle
(`ragbase-shield ner download --model urchade`). Les hooks et le contrôle final n'utilisent jamais le modèle.

## Part 2. English

Three rules first:

- Connect a folder. Do not attach the file to the chat.
- Do not paste raw text into the chat. Go through Shield.
- Text already sent cannot be recalled.

### 0. One-click install

The installer puts RAGbase Shield on your computer without the Terminal. It is designed to need no administrator
password: everything goes into your own user folder. It installs:

- Shield, with its own copy of Python (nothing else to install);
- Shield Desk, which runs in the background and starts at each login;
- a shield icon: in the menu bar on a Mac, in the notification area on Windows.

After the install, Shield does not use the Internet, except when you download the AI model of Precise mode
yourself (section 10). Shield sends no usage statistics.

> **Unsigned files.** RAGbase does not sign the installer files yet, so macOS and Windows show a
> warning the first time. The steps below show how to continue. Download the files only from the releases page
> of the repository: https://github.com/ragbase/ragbase-shield/releases/latest. Compare the file's SHA-256 fingerprint with the `SHA256SUMS`
> file of the same page before you open the file.

**Mac: `RAGbase-Shield-<version>.pkg`** (macOS 13 or later; one file for Intel and Apple Silicon Macs)

1. Download the file and double-click it. macOS says that it could not verify the file and does not open it,
   because it is not signed. Click "Done". Do not click "Move to Trash".

2. Open the Apple menu > System Settings > Privacy & Security. Scroll down to "Security". Next to the message
   about `RAGbase-Shield`, click "Open Anyway". This button stays for about one hour after step 1. macOS asks you
   to confirm: click "Open Anyway" again, then enter your Mac password (or use Touch ID).

3. In Installer, click Continue, agree to the licence, then click Install. If Installer asks where, choose
   "Install for me only". Installer must not ask for an administrator password: if it does, stop and tell
   RAGbase.

4. Click Close. A few seconds later the shield icon appears in the menu bar. macOS may report a new
   background item "RAGbase Shield": this is normal.

5. Click the icon, then "Open Shield Desk". Add your first folder (section 1).
6. On the first vault access, macOS asks for keychain access for "RAGbase Shield": click "Always Allow".
   If macOS asks for access to Documents, Desktop or Downloads, click "Allow". Otherwise Shield cannot read
   the folders you connect.

No icon? On a MacBook with a notch, a full menu bar can hide it: move or remove another icon (hold Cmd and
drag it). Otherwise log out and log in again.

**Windows: `RAGbase-Shield-<version>-win64.msi`** (Windows 10 or 11, 64-bit; no graphics card needed)

On a Windows ARM PC (Snapdragon), Shield runs in emulation, a little slower.

1. Download the file from the releases page of the repository (an `.msi` sent as an attachment is blocked by Outlook
   and Gmail). The browser may warn that the file "isn't commonly downloaded": keep it (Edge: "...",
   "Keep", then "Show more" and "Keep anyway"). Double-click it. SmartScreen shows "Windows protected
   your PC" and "Microsoft Defender SmartScreen prevented an unrecognized app from starting" because the
   file is not signed. Click "More info": the window shows "App: RAGbase-Shield-<version>-win64.msi" and
   "Publisher: Unknown publisher". Click "Run anyway". For this warning Windows sends the file's fingerprint
   and download address to Microsoft: that is Windows (SmartScreen), not Shield. If Windows then shows
   "Open File - Security Warning", click "Run". If the "Run anyway" button is missing: on some Windows 11 PCs,
   Smart App Control is on and blocks unsigned installers, with no button to continue. Then use the uv method
   (section 0b) or wait for the signed installer. Do not turn this protection off. In a firm, an IT rule can also
   block the file: ask your IT team.

2. The install is for your account only. It is designed to need no administrator password. A small progress
   window opens, then closes by itself (under a minute). Windows 11 may then report that RAGbase Shield was
   added to the startup apps: this is normal.

3. The shield icon appears in the notification area, near the clock (or under the ^ arrow of hidden icons).
   To keep it always visible: Settings > Personalization > Taskbar > Other system tray icons, then turn on
   RAGbase Shield. Right-click it, then click "Open Shield Desk".

**The icon menu:** a status line (port, version, mode: "rules" is Fast mode, "rules + NER" is Precise mode;
"Status..." on Windows), Open Shield Desk, Dossiers
(Mac: your folders, each opens in the Finder; Windows: the Dossiers page), Shield data folder, Restart, Start
at login (check mark), Open the log (it holds no names and no token), Uninstall... (your dossiers and vaults
stay), Quit (Shield Desk stops until the next login, and the browser extension stops answering).

**Your apps after the install:**

| App | What to do |
|---|---|
| Shield Desk and the browser extension | Nothing: Desk always runs, with no terminal window. Paste the token in the extension options (section 7). |
| Claude Desktop | Install the `.mcpb` (section 2). |
| Claude Code and Cowork (plugin) | The plugin still needs uv: install uv (section 0b, first command), then follow section 3. |
| ChatGPT desktop, Codex, VS Code | One Terminal command with the installed Shield (below). The apps then use the installed Shield, without uv. |

On a Mac (replace `codex` with `chatgpt` or `vscode`):

```sh
"$HOME/Library/Application Support/RAGbase Shield/bin/ragbase-shield" install codex
```

On Windows (PowerShell):

```powershell
& "$env:LOCALAPPDATA\Programs\RAGbase Shield\bin\ragbase-shield.cmd" install codex
```

The other `ragbase-shield ...` commands of this guide also work with that path.

**Update:** run the newer `.pkg` or `.msi` like the first time. Your dossiers, vaults and settings stay. On
Windows, close Claude Desktop, ChatGPT, Codex and VS Code first: they use Shield's files. Otherwise Windows
finishes the replacement at the next reboot (it does not reboot by itself and does not ask).
**Uninstall:** Shield icon > "Uninstall..." (on Windows, Settings > Apps > RAGbase Shield > Uninstall also
works; close the same apps first, as for an update). Your dossiers and vaults stay in `~/.ragbase-shield` (Windows: `%LOCALAPPDATA%\ragbase-shield`); to
erase everything, see section 9. Also remove Shield from your apps (section 9): their settings still point at
the removed Shield. On a Mac, IT can also run `"$HOME/Library/Application Support/RAGbase Shield/uninstall.sh"`;
with `--purge-data` it also erases the vaults and the key, which cannot be undone.
After "Quit", Shield comes back at the next login (on Windows, Start menu > RAGbase Shield also starts it
again). Precise mode (section 10) is not available with the
one-click installer yet.
Running the same `.msi` again installs nothing: Shield restarts, that is all; to repair a damaged install,
uninstall, then install again. No icon one minute after the install? Start menu > RAGbase Shield. Still
nothing: a firm policy blocks programs in the user folder (AppLocker, Smart App Control); ask your IT team
(`packaging/windows/IT_SHEET.md`). The message "The system administrator has set policies to prevent this
installation" (code 1625) means the policy "Prohibit user installs" is on: IT team. The icon does not come
back at login? Task Manager > Startup apps > RAGbase Shield must be "Enabled"; when a firm policy ignores that
list, IT creates a scheduled task (IT sheet). Did you use Shield with uv before? Your dossiers and vaults are
kept (same data folder). Run `install` again for each app (table above), or Claude Desktop, Codex and VS Code
keep using the old Shield started by `uvx`; the `ragbase-shield` command of uv is not the installed Shield:
`uv tool uninstall ragbase-shield` if you had installed it.

### 0b. Other way: uv and Shield Desk (Terminal)

For Terminal users, the Claude Code plugin (section 3) and Precise mode (section 10). Install uv (one command),
then install the `ragbase-shield` command and start Shield Desk.

macOS (Terminal):

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If uv is already on your computer, paste this line anyway: it updates uv.

Open a new terminal window.

> **From a copy of the repository (development).** In the repository folder, type once `uv tool install .`:
> the `ragbase-shield` commands of this guide then use that copy. `ragbase-shield doctor` checks it.

Then install the `ragbase-shield` command once, from the wheel of the release, and start Shield Desk:

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield desk
```

The browser opens **http://127.0.0.1:7878** with a private link that holds a per-install token.
To open it again, run `ragbase-shield desk` again or use the link shown in the terminal: the address alone shows
"Token refused". If Desk already runs, the command prints the link again. Keep the terminal open: closing it
stops Desk and the browser extension.

To start Shield Desk without installing the command:

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield desk
```

### 1. Add a case folder

Shield Desk, page **Dossiers** (EN labels: Matters): add the folder, click "Show entities" to review the
detected names, add missing ones ("Add a name or a term", above the list), turn on the "Keep in clear" switch.
To copy a folder path: Mac Finder, hold Option and right-click, "Copy ... as Pathname"; Windows, Shift +
right-click, "Copy as path". Or from your own terminal (not an AI agent's: `add`, `register` and `entities`
refuse to run there; these commands need the `ragbase-shield` command, section 0b):

```sh
ragbase-shield add "/path/to/case/folder" --title "Mercadier c. Ateliers Brunelac"
ragbase-shield entities DOSSIER_1
ragbase-shield register DOSSIER_1 --person "Thibault Mercadier"
```

The title and path stay local. Models only see DOSSIER_1.

### 2. Claude Desktop (one click)

1. Do step 0 (or 0b) first: you add your folders in Shield Desk. Download `ragbase-shield-0.4.1.mcpb` from the
   releases page of the repository: https://github.com/ragbase/ragbase-shield/releases/latest.
2. Double-click it and click "Install" (or drag it into Settings > Extensions).
3. In a new chat, ask "What is the Shield status?". Claude should call `shield_status`.

Terminal alternative, with the command of section 0b: `ragbase-shield install claude-desktop [--dry-run]`.
On first start, Claude Desktop downloads Python and the extension's parts itself: it needs the Internet
that one time. If Claude reports an error about uv, install uv (section 0b) and restart Claude Desktop.
On a Mac, the first use may ask for keychain access for the RAGbase Shield key (the extension runs another
program than Shield Desk): click "Always Allow". If you deny it, the Shield tools answer "vault unreadable" and
show nothing to Claude.
Claude Team and Enterprise admins can block extensions.

### 3. Claude Code and Cowork (plugin)

The plugin ships the MCP server, a skill (work with codes, never ask for real names, save with
`shield_save_draft`) and hooks (`UserPromptSubmit` blocks registered values and names the code to use,
`PreToolUse` denies direct reads in dossier folders, `PostToolUse` masks registered values left in tool results).

In Claude Code (recommended):

```text
/plugin marketplace add ragbase/ragbase-shield
/plugin install ragbase-shield@ragbase
```

From a copy of the repository: `/plugin marketplace add /path/to/ragbase-shield`.
Cowork: Customize > Plugins > Add > Add marketplace, enter `ragbase/ragbase-shield` (or the path of a copy of the
repository), then install RAGbase Shield.

Terminal, with the command of section 0b: `ragbase-shield install claude-code [--dry-run]`. Run from a copy of
the project (or with
`RAGBASE_SHIELD_MARKETPLACE=<project folder>`) it installs the full plugin; otherwise it installs the **MCP
server only, without the hooks and the skill** (nothing then blocks a real name typed in Claude Code). It says
so. Prefer the plugin method.
A local MCP server shipped in a plugin does not run in Claude Desktop chat; use the `.mcpb` there.

### 4. ChatGPT desktop and Codex

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install chatgpt --dry-run
ragbase-shield install chatgpt
ragbase-shield install codex
```

The `--dry-run` line shows the change and writes nothing. The `install chatgpt` line is for ChatGPT desktop, the
`install codex` line for Codex. Both write the `[mcp_servers.ragbase-shield]` table into `~/.codex/config.toml`
(Windows: `%USERPROFILE%\.codex\config.toml`). By hand, add this table; it runs the wheel of the release.
Annotated version: [integrations/codex/config.toml.example](../integrations/codex/config.toml.example).

```toml
[mcp_servers.ragbase-shield]
command = "uvx"
args = ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl", "ragbase-shield", "mcp"]
startup_timeout_sec = 60
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

ChatGPT desktop manual setup: Settings > MCP servers > Add server; name `ragbase-shield`, type STDIO,
command `uvx`, arguments: the block below. Save, then Restart.

```text
--from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield mcp
```

Business, Edu and Enterprise admins can restrict MCP servers. It works in local Work threads (running on this
computer) and in Codex; hosted (cloud) Work threads do not see Shield.
UI labels can change.
ChatGPT web is not supported natively: use Shield Desk or the browser extension.

### 5. GitHub Copilot in VS Code

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
ragbase-shield install vscode --dry-run
ragbase-shield install vscode
```

One click: [Install RAGbase Shield in VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=ragbase-shield&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22https%3A%2F%2Fgithub.com%2Fragbase%2Fragbase-shield%2Freleases%2Fdownload%2Fv0.4.1%2Fragbase_shield-0.4.1-py3-none-any.whl%22%2C%22ragbase-shield%22%2C%22mcp%22%5D%7D).

Manual: VS Code now prefers `.mcp.json` at the project root, or `~/.copilot/mcp-config.json` for all projects
(top-level key `"mcpServers"` instead of `"servers"`, same entry). The older places still work: `.vscode/mcp.json`
in the project, or your user profile `mcp.json` (where `ragbase-shield install vscode` writes):

```json
{
  "servers": {
    "ragbase-shield": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl", "ragbase-shield", "mcp"]
    }
  }
}
```

Accept the trust dialog the first time the server starts. Use Copilot Chat in Agent mode.
The name-blocking hooks exist only in Claude Code; in VS Code, type codes yourself.
Copilot Business and Enterprise: the "MCP servers in Copilot" policy is off by default; an organisation
admin must turn it on. Details: [integrations/vscode/README.md](../integrations/vscode/README.md).

### 6. Microsoft 365 Copilot, Word, Outlook, the Copilot app

No native connection: a remote MCP server for Microsoft 365 would see the clear text.
Use Shield Desk and the clipboard: **Masquer** (mask, copy) → paste into Copilot → copy the answer →
**Restaurer** (restore, copy) → paste into your document, never back into Copilot. For a whole Word document, drop it on the **Fichiers** page,
click "Download (.txt)", open the masked copy in Word, and use Copilot on that copy only.
**Copilot in Word and Outlook reads the open document or email. Never run it on the original.**

Terminal shortcut (with the `ragbase-shield` command, section 0b). Before pasting into Copilot:

```sh
ragbase-shield mask --dossier DOSSIER_1 --clipboard
```

After copying the answer:

```sh
ragbase-shield restore --dossier DOSSIER_1 --clipboard
```

### 7. Any web app (claude.ai, chatgpt.com, Copilot web)

Shield Desk works with every site. The browser extension (Manifest V3, Chrome and Edge) masks pasted text on
chatgpt.com, claude.ai, copilot.microsoft.com, m365.cloud.microsoft and gemini.google.com through the local Desk API (with the
token). Restore happens only in the extension side panel, never in the provider's page.
On install, the extension opens its options page: in Shield Desk, panel "Extension navigateur" (Browser
extension), click "Copy the token" and paste it there. Never paste the token into a chat. Desk must be running.
Typed text is not masked. The extension is not in the Chrome Web Store or Edge Add-ons yet: until then use Shield
Desk, or load `integrations/browser-extension` unpacked (developer mode). After you paste, check that the chat box
shows codes before you send.

### 8. Check

```sh
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield doctor
uvx --from https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl ragbase-shield verify
```

The `doctor` line checks the install, the key storage and each app integration. The `verify` line prints CLEAN or
LEAK per path. If `verify` prints LEAK, stop using Shield and report it privately ([SECURITY.md](../SECURITY.md)).

### 9. Update and uninstall

Update: with the one-click installer (section 0), run the newer `.pkg` or `.msi`. With uv, this command installs
version 0.4.1 or replaces the one you have; then restart Shield Desk and your apps:

```sh
uv tool install https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl
```

Precise mode: run the Precise command again instead (section 10).

Uninstall the one-click install: Shield icon > "Uninstall..." (details in section 0).
Remove integrations: Claude Desktop Settings > Extensions; `/plugin uninstall ragbase-shield@ragbase`;
delete `[mcp_servers.ragbase-shield]` from `~/.codex/config.toml`; delete the `ragbase-shield` entry in `mcp.json`.
Delete data: remove `~/.ragbase-shield` (or `%LOCALAPPDATA%\ragbase-shield` on Windows). This deletes the vaults: old answers can
no longer be restored. Export first if needed. The key may remain in the OS keychain (service `ragbase-shield`,
user `vault-key`); delete that entry if you wish.

Technical details per app:
[Claude Desktop](../integrations/claude-desktop/README.md) ·
[Claude Code and Cowork](../integrations/claude-code/README.md) ·
[ChatGPT desktop and Codex](../integrations/chatgpt/README.md) ·
[VS Code](../integrations/vscode/README.md) ·
[Microsoft 365 Copilot](../integrations/microsoft-copilot/README.md) ·
[Browser extension](../integrations/browser-extension/README.md) ·
[Overview](../integrations/README.md)

### 10. Optional: Precise mode (with AI model)

By default Shield is in Fast mode: it works with its rules and dictionaries (French and English). Precise mode adds
a local AI model (technical name: GLiNER). The model also finds the names without a title or a known first name, the
companies without a legal form, the usernames and the employee ids.
It runs on the CPU, offline, and takes about 1.2 GB. You install it with uv (section 0b): the one-click
installer does not support it yet.

```sh
uv tool install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/ragbase_shield-0.4.1-py3-none-any.whl"
ragbase-shield ner download
ragbase-shield ner status
```

`ner download` downloads the model once, into `~/.ragbase-shield/models`. `ner status` (or `ragbase-shield doctor`)
shows the state of Precise mode.

`RAGBASE_SHIELD_NER=off` turns it off; `RAGBASE_SHIELD_NER_MODEL=urchade` picks the other model
(`ragbase-shield ner download --model urchade`). The hooks and the final check never use the model.
