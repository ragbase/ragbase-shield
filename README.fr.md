# RAGbase Shield

**Utilisez Claude, ChatGPT et Copilot sur vos dossiers, en masquant les noms de vos clients avant l'envoi.**

RAGbase Shield 0.4.0 est un outil gratuit et open source (licence Apache-2.0).
Sur votre ordinateur, il remplace les noms et les numéros de vos clients par des codes avant l'envoi à l'IA.
Quand l'IA répond, Shield remet les vrais noms. Cela se passe aussi sur votre ordinateur.

C'est une **pseudonymisation locale et réversible**.
Ce n'est pas une anonymisation : les faits, les dates et les montants restent lisibles par l'IA.
Rien ne part chez RAGbase. Shield n'envoie aucune statistique d'usage.

English version: [README.md](README.md)

Sommaire :

- [Pour les avocats : l'essentiel](#pour-les-avocats--lessentiel)
- [Installer](#installer)
- [Utiliser au quotidien](#utiliser-au-quotidien)
- [Résultats : essai comparatif public du 11 novembre 2026](#résultats--essai-comparatif-public-du-11-novembre-2026)
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

L'IA reçoit ce texte :

```text
M. PERSONNE_A, domicilié ADRESSE_1, conteste son
licenciement par la société SOCIETE_A SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° RG_1).
Contact : EMAIL_1
```

C'est la sortie réelle du moteur 0.4.0 (mode règles, le réglage par défaut) sur cet exemple. Un test la vérifie.
Notez ce qui reste lisible : la date, le montant, la juridiction.
L'IA en a besoin pour travailler.

Dans un même dossier, une personne garde toujours le même code.
« M. Mercadier », « Thibault Mercadier » et « MERCADIER Thibault » deviennent tous PERSONNE_A.

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
| Mac (macOS 13 ou plus récent) | `RAGbase-Shield-0.4.0.pkg` : double-clic, installation pour vous seul (prévue sans mot de passe administrateur), sans Terminal. Pas encore signé : macOS vous demande de confirmer la première fois | [docs/INSTALL.md](docs/INSTALL.md), section 0 |
| Windows 10 ou 11 | `RAGbase-Shield-0.4.0-win64.msi` : installation pour l'utilisateur (prévue sans droits administrateur). Pas encore signé : SmartScreen vous demande de confirmer | [docs/INSTALL.md](docs/INSTALL.md), section 0 |
| Claude Desktop | `ragbase-shield-0.4.0.mcpb` : double-clic, puis « Installer » | [docs/INSTALL.md](docs/INSTALL.md), section 2 |
| Claude Code et Cowork | Plugin : `/plugin marketplace add ragbase/ragbase-shield`, puis `/plugin install ragbase-shield@ragbase` | [docs/INSTALL.md](docs/INSTALL.md), section 3 |
| ChatGPT desktop et Codex, GitHub Copilot dans VS Code | `uvx ragbase-shield install chatgpt` (ou `codex`, `vscode`) | [docs/INSTALL.md](docs/INSTALL.md), sections 4 et 5 |
| Toute application web (claude.ai, chatgpt.com, Copilot web) | Shield Desk, et l'extension de navigateur pour Chrome et Edge (pas encore dans les boutiques : chargez le dossier `integrations/browser-extension` en mode développeur) | [docs/INSTALL.md](docs/INSTALL.md), sections 6 et 7 |
| Terminal, avec uv ou pip | `uvx ragbase-shield desk`, ou `pip install ragbase-shield` | ci-dessous |

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
uvx ragbase-shield desk
```

Votre navigateur s'ouvre sur **http://127.0.0.1:7878**, avec un lien privé qui contient un jeton secret.
C'est une page locale : elle fonctionne seulement sur votre ordinateur.
Pour la rouvrir, relancez la commande ci-dessus ou utilisez le lien affiché dans le Terminal.
L'adresse seule, sans le jeton, affiche « Jeton refusé ».
Laissez la fenêtre du Terminal ouverte : la fermer arrête Shield Desk et l'extension de navigateur.

**Avec pip :** `pip install ragbase-shield`, puis `ragbase-shield desk`. Le modèle optionnel de reconnaissance des
noms : `pip install "ragbase-shield[ner]"` (voir [docs/NER.md](docs/NER.md)).

Sur Mac, au premier usage, une fenêtre peut demander l'accès au trousseau pour la clé de Shield :
cliquez sur « Toujours autoriser ».

---

## Utiliser au quotidien

### Avec Claude Desktop, Claude Code, ChatGPT desktop ou Copilot dans VS Code

1. Dans Shield Desk, page **Dossiers**, rubrique « Ajouter un dossier » : indiquez le chemin complet du
   répertoire du dossier client, puis cliquez sur « Ajouter et analyser ».
   Shield lui donne un code (DOSSIER_1) et lit les pièces.
   Pour copier le chemin d'un dossier : sur Mac, dans le Finder, clic droit sur le dossier en tenant la touche
   Option, puis « Copier … comme chemin d'accès » ; sous Windows, Maj + clic droit, puis
   « Copier en tant que chemin d'accès ».
2. Cliquez sur « Voir les entités » pour voir la liste des noms détectés. Ajoutez ceux qui manquent avec
   « Ajouter un nom ou un terme », au-dessus de la liste : le client, les parties, un nom de projet.
   Activez l'interrupteur « Garder en clair » pour un nom qui doit rester lisible.
3. Dans l'application d'IA, demandez par exemple :
   « Liste mes dossiers Shield. Lis les pièces du DOSSIER_1 et prépare un projet de conclusions.
   Enregistre le projet avec Shield. »
4. L'IA ne voit que des codes. Elle enregistre le projet avec l'outil Shield.
5. Shield écrit le document, avec les vrais noms, dans le sous-répertoire **« Shield - sorties »**
   du dossier client. Ouvrez-le sur votre ordinateur et relisez-le.

L'IA ne peut pas demander à Shield les vrais noms. Seul votre ordinateur les remet.

### Avec n'importe quelle application (Word, Outlook, Copilot, claude.ai, chatgpt.com)

1. Ouvrez Shield Desk avec le lien affiché par `uvx ragbase-shield desk`, page **Masquer**. Choisissez le
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

## Résultats : essai comparatif public du 11 novembre 2026

Fichier complet, avec chaque jeu de données, chaque mode, chaque statut, la méthode et les limites :
[evaluation/laptop/RESULTS_PUBLIC.md](evaluation/laptop/RESULTS_PUBLIC.md) (en français d'abord, puis en anglais).
Protocole fixé d'avance : [PROTOCOL.md](evaluation/laptop/PROTOCOL.md) et ses addenda, dans le même dossier.

À lire avant les chiffres :

- **Shield 0.4.0 a été construit après que les premiers résultats de cet essai ont été connus. Aucun jeu de
  données n'est « tenu à l'écart » pour Shield 0.4.0. Hexagone 0.3.9 et Presidio 2.2.364 ont été mesurés en
  octobre 2026 et n'ont pas été relancés.** La comparaison est donc : Shield de novembre contre les autres outils
  d'octobre.
- Shield est notre produit (RAGbase). Cet essai est fait par nous.
- Statut de chaque jeu pour Shield 0.4.0 : REF (pas tenu à l'écart : écrit par l'équipe Shield, résultats de la
  0.3.1 connus), FR-PII-Bench et MAPA (contrôle), Max (contrôle, avec une correction venue de cet essai),
  Judilibre (pas tenu à l'écart pour la 0.4.0), anglais (développement).
- Machine : une VM Windows (6 cœurs, 16 Go, sans carte graphique). Ce n'est pas un portable.
- « Shield 0.4.0 règles » est le réglage par défaut du produit. « Shield 0.4.0 GLiNER » veut dire règles plus le
  modèle GLiNER sur processeur.
- Tonic : mesuré en interne, non publié (conditions de Tonic).

**Résultat selon la règle fixée d'avance** (section 11.3 du protocole ; addendum 4, section 20.9). Pour Shield
0.4.0, la seule formulation permise est : « les conditions de la section 11.3 sont remplies » ou « ne sont pas
remplies ».

| Lecture | Contre Hexagone Rapide | Contre Hexagone Précis |
|---|---|---|
| Shield 0.4.0, les deux lignes ensemble (lecture de la Table 3) | **conditions non remplies** | **conditions non remplies** |
| Shield 0.4.0 règles, réglage par défaut du produit (S-R4) | conditions non remplies | conditions non remplies |
| Shield 0.4.0 GLiNER (S-N4) | conditions non remplies | conditions non remplies |
| Pour mémoire : Shield 0.3.1, octobre (Table 3) | conditions non remplies | conditions non remplies |

Raison, la même pour chaque ligne : sur REF (pas tenu à l'écart), Hexagone Rapide et Hexagone Précis laissent moins de
données personnelles lisibles que Shield 0.4.0, avec un écart net. Écarts nets dans le même sens sur MAPA (contrôle)
et sur l'anglais (développement) pour Hexagone Rapide et Précis, et sur FR-PII-Bench (contrôle) pour Hexagone Précis.
Détail : Table 14. Tonic : mesuré en interne, non publié (conditions de Tonic). La vitesse n'entre pas dans cette
règle.

**Chiffres clés** (plus bas = mieux ; VM, pas un portable). La colonne « Statut » rappelle le statut de REF et de
Judilibre pour chaque ligne.

| Outil | Statut de REF et de Judilibre pour cette ligne | Données personnelles lisibles, REF | Termes juridiques changés, REF | Termes juridiques changés, Judilibre | Temps médian, un fichier REF de 10 pages | Mémoire, REF |
|---|---|---|---|---|---|---|
| Shield 0.4.0 règles | pas tenus à l'écart (résultats de la 0.3.1 connus) | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 296 sur 6 136 (4,8 %) ; sous-ensemble de 50 : 88 sur 1 476 (6,0 %) | 0,59 s (11 novembre) | 74 à 75 Mo |
| Shield 0.4.0 GLiNER | pas tenus à l'écart (résultats de la 0.3.1 connus) | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 1 048 sur 6 136 (17,1 %) ; 50 : 233 (15,8 %) | 17,4 s (11 novembre) | 3,8 Go |
| Shield 0.3.1 règles | REF inventé ; Judilibre tenu à l'écart | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 296 sur 6 136 (4,8 %) ; 50 : 88 (6,0 %) | 0,75 s (25 octobre) | 74 Mo |
| Shield 0.3.1 GLiNER | REF inventé ; Judilibre tenu à l'écart | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 1 048 sur 6 136 (17,1 %) ; 50 : 233 (15,8 %) | 23 s (25 octobre) | 3,7 Go |
| Hexagone Rapide | REF nouveau ; Judilibre tenu à l'écart | 38 sur 1 015 (3,7 %) | 65 sur 365 (17,8 %) | 2 264 sur 6 136 (36,9 %) ; 50 : 581 (39,4 %) | 27 s (octobre) | 1,6 à 1,7 Go |
| Hexagone Précis | REF nouveau ; Judilibre tenu à l'écart | 1 sur 1 015 (0,1 %) | 172 sur 365 (47,1 %) | sous-ensemble de 50 seulement : 637 sur 1 476 (43,2 %) | 540 s, soit 9 min (octobre, partiel) | 3,8 à 5,4 Go |
| Presidio | REF nouveau ; Judilibre tenu à l'écart | 249 sur 1 015 (24,5 %) | 56 sur 365 (15,3 %) | 911 sur 6 136 (14,8 %) ; 50 : 234 (15,9 %) | 1,6 s (25 octobre) | 0,57 Go |
| Tonic (cloud) | | mesuré en interne, non publié (conditions de Tonic) | | | | |

En bref (les résultats de la Table 13, dans les deux sens) :

- **Le compromis.** Sur REF (pas tenu à l'écart), Shield 0.4.0 laisse plus de données personnelles lisibles
  qu'Hexagone, et il change beaucoup moins de termes juridiques (juridictions, lois, codes, articles).
- **Données personnelles lisibles (P1), là où Hexagone en laisse moins.** Hexagone Rapide et Hexagone Précis :
  sur REF (pas tenu à l'écart), MAPA (contrôle) et l'anglais (développement). Hexagone Précis aussi sur
  FR-PII-Bench (contrôle).
- **Données personnelles lisibles (P1), là où Shield 0.4.0 en laisse moins.** Contre Hexagone Rapide sur
  FR-PII-Bench (contrôle). Contre Presidio sur REF, FR-PII-Bench, Max et Judilibre. Sur l'anglais, Presidio en
  laisse moins que Shield 0.4.0 règles, et Shield 0.4.0 GLiNER en laisse moins que Presidio.
- **Pas d'écart net (P1).** Avec Hexagone Rapide et Hexagone Précis sur Max (contrôle, avec une correction venue
  de cet essai) et sur Judilibre (pas tenu à l'écart pour la 0.4.0). Avec Presidio sur MAPA.
- **Termes juridiques changés (P2).** Les deux lignes Shield 0.4.0 changent moins de termes juridiques
  qu'Hexagone Rapide et Précis sur chaque jeu qui en contient. Contre Presidio : moins sur REF, MAPA et Max pour
  les deux lignes, et sur Judilibre pour la ligne règles ; pas d'écart net sur Judilibre pour la ligne GLiNER.
- **Shield 0.4.0 contre 0.3.1.** En mode règles, le texte de sortie est identique sur REF, FR-PII-Bench, MAPA et
  Judilibre. En mode GLiNER, sur l'anglais (développement), Shield 0.4.0 laisse plus de noms d'organisation
  lisibles que la 0.3.1 : un écart net en défaveur de la 0.4.0.
- **Vitesse.** Nous ne disons pas que la 0.4.0 est plus rapide que la 0.3.1 : les deux séances ont 16 jours
  d'écart, sur la même VM.

<details>
<summary>Chaque jeu, P1 et P2, les deux lignes Shield 0.4.0 (Tables 12, 13, 14 et 16 du fichier public, en anglais, telles qu'elles y sont imprimées)</summary>

P1 = données personnelles du corrigé encore lisibles (plus bas = mieux). P2 = termes juridiques qui doivent rester
en clair et qui ont été changés (plus bas = mieux). Entre parenthèses : taux et intervalle de Wilson à 95 %. Les
lignes d'octobre sont imprimées de nouveau pour la lecture.

**Table 12. P1 protection and P2 over-masking with the Shield 0.4.0 rows**

| Set | Row | Status of the set for this row | Docs (failed) | P1 exposed, strict | P1 exposed, value | P2 must-stay-clear altered |
|---|---|---|---|---|---|---|
| REF | S-R4, Shield 0.4.0 rules | not held-out: team-written, 0.3.1 results known; unused by record | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: team-written, 0.3.1 results known; unused by record | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-R, Shield 0.3.1 rules | invented | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-N, Shield 0.3.1 rules + GLiNER | invented | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | H-F, Hexagone 0.3.9 Fast | new to every other tool | 5 (0) | 38 of 1,015 (3.7 %; 2.7 to 5.1) | 9 of 1,015 (0.9 %; 0.5 to 1.7) | 65 of 365 (17.8 %; 14.2 to 22.1) |
| REF | H-P, Hexagone 0.3.9 Precis | new to every other tool | 5 (0) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 172 of 365 (47.1 %; 42.1 to 52.2) |
| REF | P, Presidio 2.2.364 | new to every other tool | 5 (0) | 249 of 1,015 (24.5 %; 22.0 to 27.3) | 185 of 1,015 (18.2 %; 16.0 to 20.7) | 56 of 365 (15.3 %; 12.0 to 19.4) |
| FR-PII-Bench | S-R4, Shield 0.4.0 rules | gate | 300 (0) | 36 of 2,105 (1.7 %; 1.2 to 2.4) | 27 of 2,105 (1.3 %; 0.9 to 1.9) | no items |
| FR-PII-Bench | S-N4, Shield 0.4.0 rules + GLiNER | gate | 300 (0) | 26 of 2,105 (1.2 %; 0.8 to 1.8) | 18 of 2,105 (0.9 %; 0.5 to 1.3) | no items |
| FR-PII-Bench | S-R, Shield 0.3.1 rules | informed | 300 (0) | 36 of 2,105 (1.7 %; 1.2 to 2.4) | 27 of 2,105 (1.3 %; 0.9 to 1.9) | no items |
| FR-PII-Bench | S-N, Shield 0.3.1 rules + GLiNER | informed | 300 (0) | 26 of 2,105 (1.2 %; 0.8 to 1.8) | 18 of 2,105 (0.9 %; 0.5 to 1.3) | no items |
| FR-PII-Bench | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 300 (0) | 72 of 2,105 (3.4 %; 2.7 to 4.3) | 45 of 2,105 (2.1 %; 1.6 to 2.8) | no items |
| FR-PII-Bench | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 300 (0) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | no items |
| FR-PII-Bench | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 300 (0) | 918 of 2,105 (43.6 %; 41.5 to 45.7) | 543 of 2,105 (25.8 %; 24.0 to 27.7) | no items |
| MAPA | S-R4, Shield 0.4.0 rules | gate | 19 (0) | 319 of 1,615 (19.8 %; 17.9 to 21.8) | 286 of 1,615 (17.7 %; 15.9 to 19.6) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-N4, Shield 0.4.0 rules + GLiNER | gate | 19 (0) | 222 of 1,615 (13.7 %; 12.2 to 15.5) | 189 of 1,615 (11.7 %; 10.2 to 13.4) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-R, Shield 0.3.1 rules | informed | 19 (0) | 319 of 1,615 (19.8 %; 17.9 to 21.8) | 286 of 1,615 (17.7 %; 15.9 to 19.6) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-N, Shield 0.3.1 rules + GLiNER | informed | 19 (0) | 222 of 1,615 (13.7 %; 12.2 to 15.5) | 189 of 1,615 (11.7 %; 10.2 to 13.4) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 19 (0) | 89 of 1,615 (5.5 %; 4.5 to 6.7) | 58 of 1,615 (3.6 %; 2.8 to 4.6) | 579 of 1,344 (43.1 %; 40.5 to 45.7) |
| MAPA | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 19 (0) | 100 of 1,615 (6.2 %; 5.1 to 7.5) | 90 of 1,615 (5.6 %; 4.6 to 6.8) | 640 of 1,344 (47.6 %; 45.0 to 50.3) |
| MAPA | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 19 (0) | 294 of 1,615 (18.2 %; 16.4 to 20.2) | 216 of 1,615 (13.4 %; 11.8 to 15.1) | 242 of 1,344 (18.0 %; 16.0 to 20.2) |
| Max, 33 documents | S-R4, Shield 0.4.0 rules | gate, with a fix from this study | 33 (0) | 52 of 1,003 (5.2 %; 4.0 to 6.7) | 48 of 1,003 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max, 33 documents | S-N4, Shield 0.4.0 rules + GLiNER | gate, with a fix from this study | 33 (0) | 48 of 1,003 (4.8 %; 3.6 to 6.3) | 41 of 1,003 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max, 33 documents | S-R, Shield 0.3.1 rules | informed | 33 (1) | 54 of 1,003 (5.4 %; 4.1 to 7.0) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max, 33 documents | S-N, Shield 0.3.1 rules + GLiNER | informed | 33 (1) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 43 of 1,003 (4.3 %; 3.2 to 5.7) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max, 33 documents | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 33 (2) | 67 of 1,003 (6.7 %; 5.3 to 8.4) | 56 of 1,003 (5.6 %; 4.3 to 7.2) | 68 of 144 (47.2 %; 39.2 to 55.3) |
| Max, 33 documents | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 33 (2) | 38 of 1,003 (3.8 %; 2.8 to 5.2) | 33 of 1,003 (3.3 %; 2.4 to 4.6) | 84 of 144 (58.3 %; 50.2 to 66.1) |
| Max, 33 documents | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 33 (0) | 393 of 1,003 (39.2 %; 36.2 to 42.2) | 315 of 1,003 (31.4 %; 28.6 to 34.3) | 80 of 144 (55.6 %; 47.4 to 63.4) |
| Max without the workbook, 32 documents | S-R4, Shield 0.4.0 rules | gate, with a fix from this study | 32 (0) | 52 of 1,001 (5.2 %; 4.0 to 6.7) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max without the workbook, 32 documents | S-N4, Shield 0.4.0 rules + GLiNER | gate, with a fix from this study | 32 (0) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 41 of 1,001 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max without the workbook, 32 documents | S-R, Shield 0.3.1 rules | informed | 32 (0) | 52 of 1,001 (5.2 %; 4.0 to 6.7) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max without the workbook, 32 documents | S-N, Shield 0.3.1 rules + GLiNER | informed | 32 (0) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 41 of 1,001 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max without the workbook, 32 documents | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 32 (1) | 65 of 1,001 (6.5 %; 5.1 to 8.2) | 54 of 1,001 (5.4 %; 4.2 to 7.0) | 68 of 144 (47.2 %; 39.2 to 55.3) |
| Max without the workbook, 32 documents | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 32 (1) | 36 of 1,001 (3.6 %; 2.6 to 4.9) | 31 of 1,001 (3.1 %; 2.2 to 4.4) | 84 of 144 (58.3 %; 50.2 to 66.1) |
| Max without the workbook, 32 documents | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 32 (0) | 392 of 1,001 (39.2 %; 36.2 to 42.2) | 314 of 1,001 (31.4 %; 28.6 to 34.3) | 80 of 144 (55.6 %; 47.4 to 63.4) |
| Judilibre, 200 decisions | S-R4, Shield 0.4.0 rules | not held-out: 0.3.1 results known, same-source gate; unused by record | 200 (0) | 6 of 673 (0.9 %; 0.4 to 1.9) | 2 of 673 (0.3 %; 0.1 to 1.1) | 296 of 6,136 (4.8 %; 4.3 to 5.4) |
| Judilibre, 200 decisions | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: 0.3.1 results known, same-source gate; unused by record | 200 (0) | 4 of 673 (0.6 %; 0.2 to 1.5) | 2 of 673 (0.3 %; 0.1 to 1.1) | 1,048 of 6,136 (17.1 %; 16.2 to 18.0) |
| Judilibre, 200 decisions | S-R, Shield 0.3.1 rules | held-out | 200 (0) | 6 of 673 (0.9 %; 0.4 to 1.9) | 2 of 673 (0.3 %; 0.1 to 1.1) | 296 of 6,136 (4.8 %; 4.3 to 5.4) |
| Judilibre, 200 decisions | S-N, Shield 0.3.1 rules + GLiNER | held-out | 200 (0) | 4 of 673 (0.6 %; 0.2 to 1.5) | 2 of 673 (0.3 %; 0.1 to 1.1) | 1,048 of 6,136 (17.1 %; 16.2 to 18.0) |
| Judilibre, 200 decisions | H-F, Hexagone 0.3.9 Fast | held-out | 200 (0) | 11 of 673 (1.6 %; 0.9 to 2.9) | 8 of 673 (1.2 %; 0.6 to 2.3) | 2,264 of 6,136 (36.9 %; 35.7 to 38.1) |
| Judilibre, 200 decisions | P, Presidio 2.2.364 | held-out | 200 (0) | 93 of 673 (13.8 %; 11.4 to 16.6) | 68 of 673 (10.1 %; 8.0 to 12.6) | 911 of 6,136 (14.8 %; 14.0 to 15.8) |
| Judilibre, Precis subset of 50 | S-R4, Shield 0.4.0 rules | not held-out: 0.3.1 results known, same-source gate; unused by record | 50 (0) | 3 of 194 (1.5 %; 0.5 to 4.4) | 1 of 194 (0.5 %; 0.1 to 2.9) | 88 of 1,476 (6.0 %; 4.9 to 7.3) |
| Judilibre, Precis subset of 50 | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: 0.3.1 results known, same-source gate; unused by record | 50 (0) | 1 of 194 (0.5 %; 0.1 to 2.9) | 1 of 194 (0.5 %; 0.1 to 2.9) | 233 of 1,476 (15.8 %; 14.0 to 17.7) |
| Judilibre, Precis subset of 50 | S-R, Shield 0.3.1 rules | held-out | 50 (0) | 3 of 194 (1.5 %; 0.5 to 4.4) | 1 of 194 (0.5 %; 0.1 to 2.9) | 88 of 1,476 (6.0 %; 4.9 to 7.3) |
| Judilibre, Precis subset of 50 | S-N, Shield 0.3.1 rules + GLiNER | held-out | 50 (0) | 1 of 194 (0.5 %; 0.1 to 2.9) | 1 of 194 (0.5 %; 0.1 to 2.9) | 233 of 1,476 (15.8 %; 14.0 to 17.7) |
| Judilibre, Precis subset of 50 | H-F, Hexagone 0.3.9 Fast | held-out | 50 (0) | 2 of 194 (1.0 %; 0.3 to 3.7) | 1 of 194 (0.5 %; 0.1 to 2.9) | 581 of 1,476 (39.4 %; 36.9 to 41.9) |
| Judilibre, Precis subset of 50 | H-P, Hexagone 0.3.9 Precis | held-out | 50 (0) | 0 of 194 (0.0 %; 0.0 to 1.9) | 0 of 194 (0.0 %; 0.0 to 1.9) | 637 of 1,476 (43.2 %; 40.7 to 45.7) |
| Judilibre, Precis subset of 50 | P, Presidio 2.2.364 | held-out | 50 (0) | 32 of 194 (16.5 %; 11.9 to 22.4) | 21 of 194 (10.8 %; 7.2 to 16.0) | 234 of 1,476 (15.9 %; 14.1 to 17.8) |
| English | S-R4, Shield 0.4.0 rules | development set (in-sample) | 241 (0) | 143 of 1,276 (11.2 %; 9.6 to 13.1) | 136 of 1,276 (10.7 %; 9.1 to 12.5) | no items |
| English | S-N4, Shield 0.4.0 rules + GLiNER | development set (in-sample) | 241 (0) | 49 of 1,276 (3.8 %; 2.9 to 5.0) | 41 of 1,276 (3.2 %; 2.4 to 4.3) | no items |
| English | S-R, Shield 0.3.1 rules | informed | 241 (0) | 142 of 1,276 (11.1 %; 9.5 to 13.0) | 135 of 1,276 (10.6 %; 9.0 to 12.4) | no items |
| English | S-N, Shield 0.3.1 rules + GLiNER | informed | 241 (0) | 27 of 1,276 (2.1 %; 1.5 to 3.1) | 23 of 1,276 (1.8 %; 1.2 to 2.7) | no items |
| English | H-F, Hexagone 0.3.9 Fast | public benchmark; Hexagone publishes numbers on it | 241 (0) | 22 of 1,276 (1.7 %; 1.1 to 2.6) | 15 of 1,276 (1.2 %; 0.7 to 1.9) | no items |
| English | H-P, Hexagone 0.3.9 Precis | public benchmark; Hexagone publishes numbers on it | 241 (0) | 10 of 1,276 (0.8 %; 0.4 to 1.4) | 8 of 1,276 (0.6 %; 0.3 to 1.2) | no items |
| English | P, Presidio 2.2.364 | public benchmark; Hexagone publishes numbers on it | 241 (0) | 108 of 1,276 (8.5 %; 7.1 to 10.1) | 107 of 1,276 (8.4 %; 7.0 to 10.0) | no items |

**Table 13. Claims per set for the Shield 0.4.0 rows** (paired bootstrap over documents; a claim needs the whole
95 % interval on one side of 0; "none" = no clear difference; claims in both directions have the same weight)

| Set (status for Shield 0.4.0) | Shield 0.4.0 row against | P1, S-R4 | P1, S-N4 | P2, S-R4 | P2, S-N4 | Different from the 0.3.1 rows? |
|---|---|---|---|---|---|---|
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | H-F | H-F better | H-F better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | H-P | H-P better | H-P better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | S-R4 against S-N4 | none | | none | | no |
| FR-PII-Bench (gate) | H-F | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | H-F, 30 % cut (sensitivity reading) | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | H-P | H-P better | H-P better | no items | no items | no |
| FR-PII-Bench (gate) | H-P, 30 % cut (sensitivity reading) | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | P | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | S-R4 against S-N4 | S-N4 better | | no items | | no |
| MAPA (gate) | H-F | H-F better | H-F better | S-R4 better | S-N4 better | no |
| MAPA (gate) | H-P | H-P better | H-P better | S-R4 better | S-N4 better | no |
| MAPA (gate) | P | none | none | S-R4 better | S-N4 better | no |
| MAPA (gate) | S-R4 against S-N4 | S-N4 better | | none | | no |
| Max, 33 documents (gate, with a fix from this study) | H-F | none | none | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | H-P | none | none | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | S-R4 against S-N4 | none (readings disagree) | | none | | no |
| Max without the workbook, 32 documents (gate, with a fix from this study) | H-F | none | none | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Max without the workbook, 32 documents (gate, with a fix from this study) | H-P | none | none | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Max without the workbook, 32 documents (gate, with a fix from this study) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-F | none | none | S-R4 better | S-N4 better | no |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | none | no |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | S-R4 against S-N4 | none | | S-R4 better | | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-F | none | none | S-R4 better | S-N4 better | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-P | none (the interval touches 0) | none (the interval touches 0) | S-R4 better | S-N4 better | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | none | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | S-R4 against S-N4 | none | | S-R4 better | | no |
| English (development set (in-sample)) | H-F | H-F better | H-F better | no items | no items | yes, P1 for S-N4: "none" for the 0.3.1 row |
| English (development set (in-sample)) | H-P | H-P better | H-P better | no items | no items | no |
| English (development set (in-sample)) | P | P better | S-N4 better | no items | no items | no |
| English (development set (in-sample)) | S-R4 against S-N4 | S-N4 better | | no items | | no |

**Table 14. The section 11.3 reading for Shield 0.4.0**

| Overall line | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) |
|---|---|---|
| Shield 0.4.0 (S-R4 and S-N4 together) | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-F better); S-N4: no P1 claim on REF (H-F better). Opposite claims: S-R4: REF P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: MAPA P1; S-N4: English P1 | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-P better); S-N4: no P1 claim on REF (H-P better). Opposite claims: S-R4: REF P1; S-R4: FR-PII-Bench P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: FR-PII-Bench P1; S-N4: MAPA P1; S-N4: English P1 |
| Shield 0.3.1 (S-R and S-N together), Table 3 of October, cited as written | No | No |

| Shield row | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) | Against Presidio (per set only) |
|---|---|---|---|
| S-R4, Shield 0.4.0 rules (product default) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N4, Shield 0.4.0 rules + GLiNER | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |
| S-R, Shield 0.3.1 rules (October files, same rule) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N, Shield 0.3.1 rules + GLiNER (the same) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |

**Table 16. Failed documents**

| Set | S-R4 | S-N4 | S-R (October) | S-N (October) | H-F (October) | H-P (October) | P (October) |
|---|---:|---:|---:|---:|---:|---:|---:|
| REF (5 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| FR-PII-Bench (300 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MAPA (19 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Max (33 documents) | 0 | 0 | 1 | 1 | 2 | 2 | 0 |
| Judilibre (200 documents) | 0 | 0 | 0 | 0 | 0 | 0 of 50 (subset) | 0 |
| English (241 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

</details>

---

## Les limites (à lire)

- **Pas d'OCR.** Un PDF scanné (une image) ne contient pas de texte. Shield le signale et ne le lit pas.
- **La détection n'est jamais complète.** Un nom que personne n'a enregistré peut passer :
  nom rare, nom étranger, surnom, faute de frappe. Enregistrez les parties de chaque dossier.
  Ce sont elles que Shield masque le plus sûrement.
- **Dans l'essai comparatif public, Hexagone laisse moins de données personnelles lisibles sur certains jeux**
  (REF, MAPA et l'anglais ; Hexagone Précis aussi sur FR-PII-Bench). Shield change moins de termes juridiques.
  Lisez les résultats ci-dessus avec leur statut : aucun jeu n'est tenu à l'écart pour Shield 0.4.0.
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
   téléchargement, lancé par vous, est le modèle optionnel de reconnaissance des noms.
5. Des données pseudonymisées restent des données personnelles : Shield réduit ce que voit le fournisseur. C'est
   une pseudonymisation, pas une anonymisation.

Modèle complet : [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md).

---

## Pour les développeurs et l'informatique du cabinet

### Architecture en bref

- Un moteur local (règles, dictionnaires, chiffres de contrôle) détecte les noms et les identifiants, en français
  et en anglais (la langue est détectée par texte, ou fixée avec `RAGBASE_SHIELD_LANGUAGE`).
  Un modèle de reconnaissance des noms (NER) est optionnel ; aucun n'est installé par défaut. Pour en ajouter un
  (environ 1,2 Go, Apache-2.0, fonctionne hors ligne, processeur seul) :

  ```
  pip install "ragbase-shield[ner]"      # ou : uv pip install "ragbase-shield[ner]"
  ragbase-shield ner download            # fastino/gliner2-privacy-filter-PII-multi, une fois, dans ~/.ragbase-shield/models
  ragbase-shield ner status              # ou : ragbase-shield doctor
  ```

  Les trouvailles du modèle passent par la même liste blanche et les mêmes garde-fous que les règles ; les hooks et
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
ragbase-shield set <DOSSIER_n> --replacement codes|synthetic [--language auto|fr|en]  # per-dossier settings (v0.2)
ragbase-shield ner status | download [--model fastino|urchade|all] [--dir DIR] [--dry-run] [--force]  # optional NER model (v0.2)
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

Avec uv, préfixez par `uvx` (`uvx ragbase-shield doctor`),
ou installez la commande une fois pour toutes : `uv tool install ragbase-shield`.
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
- Banc d'essai : `uv run python bench/run_bench.py` (rappel et précision par type, sur un corpus juridique
  inventé, écrit en même temps que les règles ; c'est un garde-fou de non-régression, pas une mesure de
  précision sur de vrais dossiers).
- Scripts d'évaluation : `evaluation/public/` (benchmarks publics ; données téléchargées dans le dossier
  `.bench_data/`, ignoré par git), `evaluation/holdout-en/` (un corpus anglais inventé), `evaluation/laptop/`
  (le correcteur et les scripts gelés de l'essai comparatif public).
- Installateurs de bureau : [packaging/README.md](packaging/README.md).

### Variables d'environnement

| Variable | Effet |
|---|---|
| `RAGBASE_SHIELD_HOME` | Répertoire des données (par défaut `~/.ragbase-shield`, ou `%LOCALAPPDATA%\ragbase-shield` sous Windows) |
| `RAGBASE_SHIELD_LOCALE=en` | Codes en anglais (PERSON_A, COMPANY_A) au lieu de PERSONNE_A, SOCIETE_A |
| `RAGBASE_SHIELD_PORT` | Port de Shield Desk (par défaut 7878) |
| `RAGBASE_SHIELD_KEYRING=0` | Clé dans un fichier 0600 au lieu du trousseau du système |
| `RAGBASE_SHIELD_MASK_TOQUE=0` | Laisse visibles les numéros de toque des avocats (masqués par défaut) |

### Contribuer, sécurité, licence

- Failles de sécurité : [SECURITY.md](SECURITY.md). N'ouvrez pas de ticket public.
- Historique des versions : [CHANGELOG.md](CHANGELOG.md).
- Licence : [Apache-2.0](LICENSE). Attributions : [NOTICE](NOTICE).
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
