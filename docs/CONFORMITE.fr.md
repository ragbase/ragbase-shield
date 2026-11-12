# Fiche conformité : RAGbase Shield

**En bref.** RAGbase Shield fait une **pseudonymisation locale et réversible** : sur votre ordinateur, il
remplace les noms et les identifiants par des codes avant l'envoi à l'IA, puis remet les vrais noms sur votre
ordinateur. Ce n'est pas une anonymisation : les faits, les dates et les montants restent lisibles.
Shield réduit ce que le fournisseur d'IA reçoit. Il ne remplace ni votre jugement, ni la relecture humaine.

| Texte | Ce que dit le texte | Ce que fait Shield | Ce qui reste à votre charge |
|---|---|---|---|
| **RGPD, art. 4(5)** (texte officiel) | La pseudonymisation empêche d'attribuer les données à une personne sans informations supplémentaires, conservées séparément et protégées. | La table codes / noms (le coffre) reste sur votre poste, chiffrée. La clé est dans le trousseau du système. | Les données pseudonymisées restent des données personnelles (considérant 26). Le RGPD s'applique : registre, base légale, information. |
| **CEPD, lignes directrices 01/2025 sur la pseudonymisation** (version soumise à consultation, adoptée le 16/01/2025 ; version finale non vérifiée) | La pseudonymisation aide à respecter les art. 5, 25 et 32. Les données restent personnelles. Le secret qui permet de réidentifier doit être protégé. | Codes attribués dans l'ordre (PERSONNE_A, PERSONNE_B), jamais calculés à partir du nom. Coffre et clé séparés du texte envoyé. | Votre analyse de risque. |
| **CNB, guide pratique « Utilisation des systèmes d'intelligence artificielle générative » (2024), p. 31** (d'après notre veille du 16/10/2026 ; page non relue pour cette fiche) | Pseudonymiser avant l'IA : noms remplacés par des initiales ou des chaînes aléatoires, adresses ramenées à la ville, vigilance sur les recoupements (montants, noms de projets). | Noms et sociétés remplacés par des codes. Adresse entière masquée (ADRESSE_1). Vous pouvez ajouter un nom de projet ou tout autre terme au dossier. | Les recoupements par les faits et les montants. |
| **CNB, grille de lecture IA, v1.2 (1re édition, juin 2025)** (titre et version vérifiés ; contenu d'après notre veille) | Une promesse de non-réutilisation d'un éditeur ne se vérifie pas. Seule une anonymisation complète préalable ou une IA locale supprime le risque. | Réduit ce que le fournisseur reçoit. Code ouvert, contrôle par `ragbase-shield verify`. | Le risque n'est pas supprimé : les faits partent. Pour le supprimer, il faut une IA locale. |
| **CNB, guide « Déontologie et IA » (adopté les 12 et 13 mars 2026)** | Pas encore lu (accès réservé) : cette fiche ne le résume pas. | | |
| **Barreau de Paris, modèle de charte IA (juillet 2026), art. 4 et 10** (texte du modèle lu le 16/10/2026 ; date du 21/07/2026 d'après notre veille) | Art. 4, hypothèse 2 : outil en ligne permis après validation ou garanties suffisantes, sans donnée confidentielle ou sensible, avec vérification humaine systématique. Art. 10 : garanties de sécurité, dont chiffrement et journalisation. | Code ouvert que votre référent peut auditer. Tout reste local. Coffre chiffré. Journal local : événements, codes et nombres, jamais un vrai nom. | Shield masque l'identité, pas le secret : un fait couvert par le secret reste confidentiel après masquage. La validation de l'outil d'IA et la relecture restent à vous. |
| **Collège de déontologie des avocats au Conseil d'État et à la Cour de cassation, Recommandation n° 2026-01 du 2 avril 2026** (texte lu le 16/10/2026) | Hors IA « fermée », ne pas transmettre d'éléments non anonymisés : noms des clients, toute information qui permet de les identifier, éléments de procédure. Recourir, le cas échéant, à la pseudonymisation et à l'anonymisation. Une question juridique posée abstraitement ne méconnaît pas le secret. | Masque noms, sociétés, identifiants et références de procédure (RG, pourvoi, ECLI) avant l'envoi. | Un texte pseudonymisé n'est pas anonyme. Retirez les faits qui identifient. Préférez la question abstraite quand c'est possible. |

**À surveiller (non vérifié) :** Conseil d'État, 13 février 2026, n° 498628 ; CEPD, projet de lignes
directrices 02/2026 sur l'anonymisation.

**Ce que Shield vous permet de montrer :**

- le journal local (`ragbase-shield journal`) : quoi, quand, combien, sans vrais noms ;
- le contrôle `ragbase-shield verify` : il place des données inventées et affiche CLEAN ou LEAK pour chaque chemin ;
- la liste des noms détectés par dossier, revue avant l'envoi ;
- le code source ouvert (licence Apache-2.0). Shield n'envoie rien à RAGbase.

**Les 3 règles à donner à l'équipe :** connectez un dossier, n'attachez pas le fichier au chat ;
ne collez pas de texte brut dans le chat ; un texte déjà envoyé ne peut pas être rappelé.

*Cette fiche n'est pas un avis juridique. Elle décrit un outil. Le respect du secret professionnel et du RGPD
reste de la responsabilité de l'avocat et du cabinet.*

Sources : [RGPD](https://eur-lex.europa.eu/eli/reg/2016/679/oj) ·
[CEPD, lignes directrices](https://www.edpb.europa.eu/our-work-tools/our-documents/publication-type/guidelines_en) ·
[CNB, guide 2024](https://cnb.avocat.fr/medias/cnb-guidepratique-utilisation-systemes-iag-2024-68f7b1d86e4570.98487114.pdf) ·
[CNB, grille 2025](https://cnb.avocat.fr/medias/cnb-grille-lecture-intelligence-aartificielle-2025-68f775b81ba5b2.65545272.pdf) ·
[CNB, Déontologie et IA](https://cnb.avocat.fr/actualite/le-cnb-adopte-un-guide-sur-la-deontologie-et-l-intelligence-artificielle) ·
[Barreau de Paris, modèle de charte](https://www.avocatparis.org/sites/bdp/files/2026-07/Mod%C3%A8le%20charte%20IA.docx) ·
[Recommandation 2026-01](https://www.ordre-avocats-cassation.fr/sites/default/files/Recommandation%20n%C2%B02026-01%20-%20L'intelligence%20artificielle.pdf).
