# Essai comparatif : Shield, Hexagone, Tonic, Presidio (octobre et novembre 2026)

Version publique, 11 novembre 2026. Elle remplace la version du 25 octobre 2026, dont le résumé et les tables
sont repris plus bas mot pour mot. Nouveau dans cette version : les lignes Shield 0.4.0
(addendum 4 du protocole, écart D28). Le résumé et les tables d'octobre (Shield 0.3.1) ne changent pas. Protocole
fixé d'avance : [PROTOCOL.md](PROTOCOL.md) v1.0, [PROTOCOL_ADDENDUM_1.md](PROTOCOL_ADDENDUM_1.md) et, pour Shield
0.4.0, [PROTOCOL_ADDENDUM_4.md](PROTOCOL_ADDENDUM_4.md). Écarts au protocole : [DEVIATIONS.md](DEVIATIONS.md) (D1 à
D24 pour octobre, D28 pour Shield 0.4.0, D31 pour la Table 18). Ce document contient seulement des totaux par jeu de
données. Il ne contient aucun chiffre interne de Tonic et aucun détail par document d'un concurrent.

**Ajout du 13 novembre 2026 (écart D31).** La Table 18 donne la précision, le rappel et le F1 par mot de Shield 0.4.0,
Hexagone et Presidio sur REF, FR-PII-Bench, MAPA et Max. C'est une lecture exploratoire, définie après les essais,
pour information : sans test et sans affirmation. Aucun autre chiffre de ce fichier ne change. Détail : section
« Ajout du 13 novembre 2026 », après la Table 17. / **Addition of 13 November 2026 (deviation D31).** Table 18 gives
the word-level precision, recall and F1 of Shield 0.4.0, Hexagone and Presidio on REF, FR-PII-Bench, MAPA and Max. It
is an exploratory reading, defined after the runs, for information: no test and no claim. No other number of this
file changes. Detail: section "Addition of 13 November 2026", after Table 17.

## Mise à jour du 11 novembre 2026 : Shield 0.4.0

**Statut.** Précision : complète pour les deux lignes Shield 0.4.0 (6 jeux de données, 798 documents par ligne, aucun
document en échec). Vitesse et mémoire : mesurées sur REF dans une séance du 11 novembre 2026. Hexagone et Presidio
n'ont pas été relancés. Les fichiers gelés sont intacts (PREREG 685 fichiers sur 685, PREREG_DATA 829 sur 829,
PREREG_V04 10 sur 10).

**À lire avant les chiffres.**

- **Shield 0.4.0 a été construit après que les premiers résultats de cet essai ont été connus. Aucun jeu de données
  n'est « tenu à l'écart » pour Shield 0.4.0. Hexagone 0.3.9 et Presidio 2.2.364 ont été mesurés en octobre 2026 et
  n'ont pas été relancés.**
- C'est une deuxième tentative du même outil : Shield 0.3.1 est la première, Shield 0.4.0 la deuxième. Les règles de
  la mesure ont été fixées avant la mesure (addendum 4, gelé le 11 novembre 2026). Mais l'équipe a changé l'outil
  après avoir vu les premiers résultats. Ces lignes montrent ce que fait la nouvelle version sur ces fichiers. Elles
  ne sont pas une confirmation sur des données jamais vues.
- Les lignes Shield 0.3.1 restent telles que mesurées en octobre. Elles sont affichées à côté des lignes 0.4.0. Elles
  ne sont pas remplacées.
- Hexagone ne peut pas être relancé : sa période d'essai a pris fin le 31 octobre 2026. Les autres outils ont
  peut-être des versions plus récentes. La comparaison est donc : Shield de novembre contre les autres outils
  d'octobre.
- Statut de chaque jeu pour Shield 0.4.0, écrit entre parenthèses après le nom du jeu dans ce résumé (détail :
  Table 11) :
  - REF (pas tenu à l'écart) : écrit par l'équipe Shield ; ses résultats avec la 0.3.1 étaient connus ; pas utilisé
    pour construire la 0.4.0 d'après les traces, sans preuve.
  - FR-PII-Bench (contrôle) et MAPA (contrôle) : jeux de contrôle de régression à chaque étape du travail sur la
    0.4.0.
  - Max (contrôle, avec une correction venue de cet essai) : la 0.4.0 lit un classeur Excel que la 0.3.1 ne lisait
    pas, et ce défaut a été trouvé par cet essai.
  - Judilibre (pas tenu à l'écart pour la 0.4.0) : ses résultats avec la 0.3.1 étaient connus ; un autre tirage de
    la même source a servi de contrôle ; pas utilisé d'après les traces, sans preuve. Il reste tenu à l'écart pour
    les autres outils.
  - Anglais (développement) : il fait partie du jeu de développement de la 0.4.0.
- Machine : la même VM Windows qu'en octobre (profil A : 6 cœurs, 16 Go, sans carte graphique). Ce n'est pas un
  portable. Séance Shield 0.4.0 : 11 novembre 2026.
- Tonic : mesuré en interne, non publié (conditions de Tonic).
- Shield est notre produit (RAGbase). Cet essai est fait par nous.
- « Shield 0.4.0 règles » est le réglage par défaut du produit (ligne S-R4). « Shield 0.4.0 GLiNER » veut dire règles
  plus le modèle GLiNER sur processeur (ligne S-N4).

**Résultat selon la règle fixée d'avance (section 11.3 du protocole ; addendum 4, section 20.9)**

Pour Shield 0.4.0, la seule formulation permise est : « les conditions de la section 11.3 sont remplies » ou « ne sont
pas remplies ». La section 11.3 lie la phrase « Shield bat X » à un jeu tenu à l'écart, et aucun jeu ne l'est pour
Shield 0.4.0.

| Lecture | Contre Hexagone Rapide | Contre Hexagone Précis |
|---|---|---|
| Shield 0.4.0, les deux lignes ensemble (lecture de la Table 3) | **conditions non remplies** | **conditions non remplies** |
| Shield 0.4.0 règles, réglage par défaut du produit (S-R4) | conditions non remplies | conditions non remplies |
| Shield 0.4.0 GLiNER (S-N4) | conditions non remplies | conditions non remplies |
| Rappel, octobre : « Shield 0.3.1 bat ... » | NON | NON |

Raison, la même pour chaque ligne : sur REF (pas tenu à l'écart), Hexagone Rapide et Hexagone Précis laissent moins de
données personnelles lisibles que Shield 0.4.0, avec un écart net. Écarts nets dans le même sens sur MAPA (contrôle)
et sur l'anglais (développement) pour Hexagone Rapide et Précis, et sur FR-PII-Bench (contrôle) pour Hexagone Précis.
Détail : Table 14. Tonic : mesuré en interne, non publié (conditions de Tonic). La vitesse n'entre pas dans cette
règle.

**Chiffres clés** (plus bas = mieux ; VM profil A, pas un portable). REF et Judilibre ne sont pas tenus à l'écart pour
Shield 0.4.0 ; la colonne « Statut » le rappelle pour chaque ligne. Les temps et la mémoire de Shield 0.4.0 viennent
de la séance du 11 novembre 2026 ; les autres valeurs viennent des séances d'octobre.

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

1. **Ce qui change entre Shield 0.3.1 et Shield 0.4.0, mode règles (réglage par défaut).** Sur REF (pas tenu à
   l'écart), FR-PII-Bench (contrôle), MAPA (contrôle) et Judilibre (pas tenu à l'écart pour la 0.4.0), le texte de
   sortie de Shield 0.4.0 règles est identique à celui de Shield 0.3.1 règles (5 documents sur 5, 300 sur 300, 19 sur
   19, 200 sur 200). Chaque compte est donc le même. Sur Max (contrôle, avec une correction venue de cet essai),
   Shield 0.4.0 règles lit le classeur Excel que la 0.3.1 ne pouvait pas lire : 52 données lisibles sur 1 003 au lieu
   de 54, sans écart net. Sans ce classeur (32 documents), les sorties sont identiques. Sur l'anglais (développement) :
   143 sur 1 276 au lieu de 142, sans écart net.
2. **Ce qui change, mode GLiNER.** Sorties identiques sur REF (pas tenu à l'écart), FR-PII-Bench (contrôle), MAPA
   (contrôle) et Judilibre (pas tenu à l'écart pour la 0.4.0). Sur l'anglais (développement), Shield 0.4.0 GLiNER
   laisse plus de données lisibles que Shield 0.3.1 GLiNER : 49 sur 1 276 au lieu de 27, avec un écart net (1,72
   point ; intervalle à 95 % : 1,01 à 2,49). Les 22 éléments en plus sont tous des noms d'organisation. C'est le seul
   écart net entre la 0.4.0 et la 0.3.1, et il est en défaveur de la 0.4.0. Sur Max (contrôle, avec une correction
   venue de cet essai) : 48 sur 1 003 au lieu de 50, sans écart net.
3. **Protection (P1), Shield 0.4.0 contre les autres outils.** Hexagone Rapide laisse moins de données lisibles que
   Shield 0.4.0 règles et GLiNER sur REF (pas tenu à l'écart ; 38 contre 56 et 56 sur 1 015), sur MAPA (contrôle ; 89
   contre 319 et 222 sur 1 615) et sur l'anglais (développement ; 22 contre 143 et 49 sur 1 276). Hexagone Précis
   laisse moins de données lisibles sur REF (1 contre 56 et 56), FR-PII-Bench (contrôle ; 3 contre 36 et 26 sur
   2 105), MAPA (100 contre 319 et 222) et l'anglais (10 contre 143 et 49). Shield 0.4.0 règles et GLiNER laissent
   moins de données lisibles qu'Hexagone Rapide sur FR-PII-Bench (36 et 26 contre 72). Pas d'écart net avec Hexagone
   Rapide ni avec Hexagone Précis sur Max (contrôle, avec une correction venue de cet essai) et sur Judilibre (pas
   tenu à l'écart pour la 0.4.0). Contre Presidio : Shield 0.4.0 règles et GLiNER laissent moins de données lisibles
   sur REF, FR-PII-Bench, Max et Judilibre ; pas d'écart net sur MAPA ; sur l'anglais, Presidio laisse moins de
   données lisibles que Shield 0.4.0 règles (108 contre 143) et Shield 0.4.0 GLiNER en laisse moins que Presidio (49
   contre 108). Ces résultats sont ceux de la 0.3.1, sauf un : sur l'anglais, Hexagone Rapide n'avait pas d'écart net
   avec Shield 0.3.1 GLiNER ; il en a un avec Shield 0.4.0 GLiNER.
4. **Sur-masquage (P2).** Shield 0.4.0 règles et GLiNER changent moins de termes juridiques qu'Hexagone Rapide et
   Précis sur chaque jeu qui en contient, avec un écart net : REF (pas tenu à l'écart ; 15 et 15 contre 65 et 172 sur
   365), MAPA (contrôle ; 0 et 0 contre 579 et 640 sur 1 344), Max (contrôle, avec une correction venue de cet essai ;
   3 et 6 contre 68 et 84 sur 144), Judilibre (pas tenu à l'écart pour la 0.4.0 ; 296 et 1 048 contre 2 264 sur 6 136
   pour Hexagone Rapide ; sous-ensemble de 50 : 88 et 233 contre 637 sur 1 476 pour Hexagone Précis). Contre
   Presidio : moins de termes changés sur REF, MAPA et Max pour les deux lignes, et sur Judilibre pour Shield 0.4.0
   règles (296 contre 911) ; pas d'écart net sur Judilibre pour Shield 0.4.0 GLiNER (1 048 contre 911). Ces comptes
   sont les mêmes que ceux de la 0.3.1.
5. **Le compromis reste le même.** Sur REF (pas tenu à l'écart), Shield 0.4.0 laisse plus de données personnelles
   lisibles qu'Hexagone et change beaucoup moins de termes juridiques.
6. **Documents en échec.** Aucun pour Shield 0.4.0 règles ni GLiNER : 798 documents traités sur 798 dans chaque mode.
   Shield 0.3.1 échouait sur 1 classeur de Max. Hexagone Rapide et Précis : 2 documents de Max chacun, comme en
   octobre.
7. **Vitesse et mémoire (VM profil A, pas un portable ; séance du 11 novembre 2026 ; REF, pas tenu à l'écart).** Un
   fichier REF de 10 pages, médiane de 10 valeurs : Shield 0.4.0 règles 0,59 s (0,50 à 0,69 s) ; Shield 0.4.0 GLiNER
   17,4 s (16,5 à 17,9 s). Valeurs d'octobre, à côté : Shield 0.3.1 règles 0,75 s ; Shield 0.3.1 GLiNER 23 s ;
   Presidio 1,6 s ; Hexagone Rapide 27 s depuis le clic. Nous ne disons pas que la 0.4.0 est plus rapide que la
   0.3.1 : les deux séances ont 16 jours d'écart, la VM a été arrêtée puis redémarrée entre les deux, et la charge de
   fond était plus faible le 11 novembre. Trois résultats d'octobre tiennent encore pour la 0.4.0, mesurée dans une
   autre séance : Shield règles plus rapide qu'Hexagone Rapide, Shield règles plus rapide que Presidio, Presidio plus
   rapide que Shield GLiNER. Mémoire : Shield 0.4.0 règles 74 à 75 Mo sur REF (jusqu'à 217 Mo selon le jeu) ; Shield
   0.4.0 GLiNER 3,8 Go sur REF (jusqu'à 6,5 Go sur Max).
8. **Où vont les données.** Shield 0.4.0 : rien ne sort de la machine (0 tentative de connexion dans les 20 processus
   de la séance, vérifié à chaque essai).
9. **Contrôles.** Un recompte indépendant, avec un compteur écrit à part, donne les mêmes comptes que le correcteur
   gelé pour les deux lignes Shield 0.4.0, élément par élément, et les mêmes résultats pour les 93 comparaisons.
   Aucune correction n'a été faite après avoir vu les scores.
10. **Limites propres à ces lignes.** Une deuxième tentative, sans jeu tenu à l'écart. Novembre contre octobre. Pour
    REF et Judilibre, « pas utilisé » repose sur les traces, sans preuve. Une seule mesure par ligne. 93 comparaisons
    de plus, sans correction pour comparaisons multiples : quelques écarts nets peuvent venir du hasard. La mesure
    porte sur le paquet Python de Shield 0.4.0, pas sur les installateurs de bureau.

## Update of 11 November 2026: Shield 0.4.0 (English)

**Status.** Accuracy: complete for the two Shield 0.4.0 rows (6 data sets, 798 documents per row, no failed document).
Speed and memory: measured on REF in a session of 11 November 2026. Hexagone and Presidio were not run again. The
frozen files are intact (PREREG 685 of 685 files, PREREG_DATA 829 of 829, PREREG_V04 10 of 10).

**Read this before the numbers.**

- **Shield 0.4.0 was built after the first results of this comparison were known. No data set is held-out for Shield
  0.4.0. Hexagone 0.3.9 and Presidio 2.2.364 were measured in October 2026 and were not run again.**
- This is a second attempt by the same tool: Shield 0.3.1 is the first, Shield 0.4.0 the second. The rules of the
  measurement were fixed before the measurement (addendum 4, frozen on 11 November 2026). But the team changed the
  tool after it saw the first results. These rows show what the new version does on these files. They are not a
  confirmation on unseen data.
- The Shield 0.3.1 rows stay as measured in October. They are shown next to the 0.4.0 rows. They are not replaced.
- Hexagone cannot be run again: its trial period ended on 31 October 2026. The other tools may have newer versions.
  So the comparison is: Shield of November against the other tools of October.
- Status of each set for Shield 0.4.0, written in brackets after the set name in this summary (detail: Table 11):
  - REF (not held-out): written by the Shield team; its results with 0.3.1 were known; not used to build 0.4.0
    according to the records, without proof.
  - FR-PII-Bench (gate) and MAPA (gate): regression gates at every step of the work on 0.4.0.
  - Max (gate, with a fix from this study): 0.4.0 reads an Excel workbook that 0.3.1 did not read, and this study
    found that fault.
  - Judilibre (not held-out for 0.4.0): its results with 0.3.1 were known; another draw from the same source was a
    gate; not used according to the records, without proof. It stays held-out for the other tools.
  - English (development): it is part of the development set of 0.4.0.
- Machine: the same Windows VM as in October (profile A: 6 cores, 16 GB, no graphics card). It is not a laptop. Shield
  0.4.0 session: 11 November 2026.
- Tonic: measured internally, not published (Tonic's terms).
- Shield is our product (RAGbase). We ran this test.
- "Shield 0.4.0 rules" is the product default (row S-R4). "Shield 0.4.0 GLiNER" means rules plus the GLiNER model on
  the CPU (row S-N4).

**Result by the rule fixed in advance (protocol section 11.3; addendum 4, section 20.9)**

For Shield 0.4.0 the only wording allowed is: "the conditions of section 11.3 are met" or "are not met". Section 11.3
ties the sentence "Shield beats X" to a held-out set, and no set is held-out for Shield 0.4.0.

| Reading | Against Hexagone Fast | Against Hexagone Precis |
|---|---|---|
| Shield 0.4.0, both rows together (the reading of Table 3) | **conditions not met** | **conditions not met** |
| Shield 0.4.0 rules, the product default (S-R4) | conditions not met | conditions not met |
| Shield 0.4.0 GLiNER (S-N4) | conditions not met | conditions not met |
| For reading, October: "Shield 0.3.1 beats ..." | NO | NO |

Reason, the same for every line: on REF (not held-out), Hexagone Fast and Hexagone Precis leave less personal data
readable than Shield 0.4.0, with a clear difference. Clear differences in the same direction on MAPA (gate) and
English (development) for Hexagone Fast and Precis, and on FR-PII-Bench (gate) for Hexagone Precis. Detail: Table 14.
Tonic: measured internally, not published (Tonic's terms). Speed is not part of this rule.

**Key numbers** (lower is better; VM profile A, not a laptop). REF and Judilibre are not held-out for Shield 0.4.0;
the "Status" column says so for each line. The times and the memory of Shield 0.4.0 come from the session of 11
November 2026; the other values come from the October sessions.

| Tool | Status of REF and Judilibre for this line | Personal data readable, REF | Legal terms changed, REF | Legal terms changed, Judilibre | Median time, one 10-page REF file | Memory, REF |
|---|---|---|---|---|---|---|
| Shield 0.4.0 rules | not held-out (0.3.1 results known) | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 296 of 6,136 (4.8 %); subset of 50: 88 of 1,476 (6.0 %) | 0.59 s (11 November) | 74 to 75 MB |
| Shield 0.4.0 GLiNER | not held-out (0.3.1 results known) | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 1,048 of 6,136 (17.1 %); 50: 233 (15.8 %) | 17.4 s (11 November) | 3.8 GB |
| Shield 0.3.1 rules | REF invented; Judilibre held-out | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 296 of 6,136 (4.8 %); 50: 88 (6.0 %) | 0.75 s (25 October) | 74 MB |
| Shield 0.3.1 GLiNER | REF invented; Judilibre held-out | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 1,048 of 6,136 (17.1 %); 50: 233 (15.8 %) | 23 s (25 October) | 3.7 GB |
| Hexagone Fast | REF new; Judilibre held-out | 38 of 1,015 (3.7 %) | 65 of 365 (17.8 %) | 2,264 of 6,136 (36.9 %); 50: 581 (39.4 %) | 27 s (October) | 1.6 to 1.7 GB |
| Hexagone Precis | REF new; Judilibre held-out | 1 of 1,015 (0.1 %) | 172 of 365 (47.1 %) | subset of 50 only: 637 of 1,476 (43.2 %) | 540 s, that is 9 min (October, partial) | 3.8 to 5.4 GB |
| Presidio | REF new; Judilibre held-out | 249 of 1,015 (24.5 %) | 56 of 365 (15.3 %) | 911 of 6,136 (14.8 %); 50: 234 (15.9 %) | 1.6 s (25 October) | 0.57 GB |
| Tonic (cloud) | | measured internally, not published (Tonic's terms) | | | | |

1. **What changes between Shield 0.3.1 and Shield 0.4.0, rules mode (the product default).** On REF (not held-out),
   FR-PII-Bench (gate), MAPA (gate) and Judilibre (not held-out for 0.4.0), the output text of Shield 0.4.0 rules is
   identical to that of Shield 0.3.1 rules (5 of 5 documents, 300 of 300, 19 of 19, 200 of 200). So every count is the
   same. On Max (gate, with a fix from this study), Shield 0.4.0 rules reads the Excel workbook that 0.3.1 could not
   read: 52 items readable of 1,003 instead of 54, no clear difference. Without that workbook (32 documents) the
   outputs are identical. On English (development): 143 of 1,276 instead of 142, no clear difference.
2. **What changes, GLiNER mode.** Identical outputs on REF (not held-out), FR-PII-Bench (gate), MAPA (gate) and
   Judilibre (not held-out for 0.4.0). On English (development), Shield 0.4.0 GLiNER leaves more data readable than
   Shield 0.3.1 GLiNER: 49 of 1,276 instead of 27, with a clear difference (1.72 points; 95 % interval 1.01 to
   2.49). The 22 more items are all organisation names. It is the only clear difference between 0.4.0 and 0.3.1, and
   it is against 0.4.0. On Max (gate, with a fix from this study): 48 of 1,003 instead of 50, no clear difference.
3. **Protection (P1), Shield 0.4.0 against the other tools.** Hexagone Fast leaves less data readable than Shield
   0.4.0 rules and GLiNER on REF (not held-out; 38 against 56 and 56 of 1,015), on MAPA (gate; 89 against 319 and 222
   of 1,615) and on English (development; 22 against 143 and 49 of 1,276). Hexagone Precis leaves less data readable
   on REF (1 against 56 and 56), FR-PII-Bench (gate; 3 against 36 and 26 of 2,105), MAPA (100 against 319 and 222) and
   English (10 against 143 and 49). Shield 0.4.0 rules and GLiNER leave less data readable than Hexagone Fast on
   FR-PII-Bench (36 and 26 against 72). No clear difference with Hexagone Fast or Hexagone Precis on Max (gate, with a
   fix from this study) and on Judilibre (not held-out for 0.4.0). Against Presidio: Shield 0.4.0 rules and GLiNER
   leave less data readable on REF, FR-PII-Bench, Max and Judilibre; no clear difference on MAPA; on English, Presidio
   leaves less data readable than Shield 0.4.0 rules (108 against 143), and Shield 0.4.0 GLiNER leaves less than
   Presidio (49 against 108). These results are those of 0.3.1, except one: on English, Hexagone Fast had no clear
   difference with Shield 0.3.1 GLiNER; it has one with Shield 0.4.0 GLiNER.
4. **Over-masking (P2).** Shield 0.4.0 rules and GLiNER change fewer legal terms than Hexagone Fast and Precis on
   every set that has them, with a clear difference: REF (not held-out; 15 and 15 against 65 and 172 of 365), MAPA
   (gate; 0 and 0 against 579 and 640 of 1,344), Max (gate, with a fix from this study; 3 and 6 against 68 and 84 of
   144), Judilibre (not held-out for 0.4.0; 296 and 1,048 against 2,264 of 6,136 for Hexagone Fast; subset of 50: 88
   and 233 against 637 of 1,476 for Hexagone Precis). Against Presidio: fewer changed terms on REF, MAPA and Max for
   both rows, and on Judilibre for Shield 0.4.0 rules (296 against 911); no clear difference on Judilibre for Shield
   0.4.0 GLiNER (1,048 against 911). These counts are the same as those of 0.3.1.
5. **The trade-off stays the same.** On REF (not held-out), Shield 0.4.0 leaves more personal data readable than
   Hexagone and changes far fewer legal terms.
6. **Failed documents.** None for Shield 0.4.0 rules or GLiNER: 798 of 798 documents processed in each mode. Shield
   0.3.1 failed on 1 workbook of Max. Hexagone Fast and Precis: 2 Max documents each, as in October.
7. **Speed and memory (VM profile A, not a laptop; session of 11 November 2026; REF, not held-out).** One 10-page REF
   file, median of 10 values: Shield 0.4.0 rules 0.59 s (0.50 to 0.69 s); Shield 0.4.0 GLiNER 17.4 s (16.5 to
   17.9 s). October values, side by side: Shield 0.3.1 rules 0.75 s; Shield 0.3.1 GLiNER 23 s; Presidio 1.6 s;
   Hexagone Fast 27 s from the click. We do not say that 0.4.0 is faster than 0.3.1: the two sessions are 16 days
   apart, the VM was stopped and started between them, and the background load was lower on 11 November. Three October
   results still hold for 0.4.0, measured in another session: Shield rules faster than Hexagone Fast, Shield rules
   faster than Presidio, Presidio faster than Shield GLiNER. Memory: Shield 0.4.0 rules 74 to 75 MB on REF (up to
   217 MB depending on the set); Shield 0.4.0 GLiNER 3.8 GB on REF (up to 6.5 GB on Max).
8. **Where the data goes.** Shield 0.4.0: nothing leaves the machine (0 connection attempts in the 20 processes of the
   session, checked in every run).
9. **Checks.** An independent recount, with a counter written apart, gives the same counts as the frozen scorer for
   the two Shield 0.4.0 rows, item by item, and the same results for the 93 comparisons. No correction was made after
   the scores were seen.
10. **Limits of these rows.** A second attempt, with no held-out set. November against October. For REF and
    Judilibre, "not used" rests on the records, without proof. One run per row. 93 more comparisons, with no
    correction for multiple comparisons: some clear differences can come from chance. The measurement is of the
    Shield 0.4.0 Python package, not of the desktop installers.

---

## Résumé d'octobre 2026 (Shield 0.3.1, sans changement)

**Statut.** Précision : complète (6 jeux de données, tous les outils). Vitesse : partielle. Hexagone Précis n'a fait
que 3 tâches sur 5 dans la séance de vitesse (écart D22). Le profil B (4 cœurs, 8 Go) n'a pas tourné. Les fichiers
gelés sont intacts (PREREG 685 fichiers sur 685, PREREG_DATA 829 sur 829).

**À lire avant les chiffres.**

- Shield est notre produit (RAGbase). Cet essai est fait par nous.
- Machine : une VM Windows dans le cloud (profil A : 6 cœurs, 16 Go, sans carte graphique). Ce n'est pas un
  portable. La VM n'a pas de limite de puissance et a des instructions (AVX-512) que les portables n'ont pas. Sur un
  portable, les temps seraient plus longs. Tous les outils locaux ont tourné sur la même VM.
- Hexagone a été piloté par Claude (un agent d'IA), à la demande de Hadi (écart D1). Claude a utilisé les écrans de
  l'application, une action à la fois, avec les réglages par défaut. Le protocole prévoyait une personne.
- Tonic : mesuré en interne, non publié (conditions de Tonic).
- Statut de chaque jeu pour Shield. « Inventé » : REF, écrit par l'équipe Shield, nouveau pour Shield au moment du
  gel, pas indépendant. « Informé » : FR-PII-Bench, MAPA, Max, anglais ; ces jeux ont servi à construire Shield.
  « Tenu à l'écart » : Judilibre, 200 décisions tirées au sort après le gel, jamais vues par aucun outil.
- « Shield » seul veut dire Shield 0.3.1 en mode règles, le réglage par défaut du produit. « Shield GLiNER » veut dire
  règles plus le modèle GLiNER sur processeur.

**Verdict selon la règle fixée d'avance (section 11.3 du protocole)**

| Affirmation | Résultat | Raison |
|---|---|---|
| Shield bat Hexagone Rapide | **NON** | Sur REF (inventé), Hexagone Rapide laisse moins de données personnelles lisibles, avec un écart net. Écarts nets en sens inverse aussi sur MAPA et l'anglais (informés). |
| Shield bat Hexagone Précis | **NON** | Sur REF (inventé), Hexagone Précis laisse moins de données personnelles lisibles, avec un écart net. Écarts nets en sens inverse aussi sur FR-PII-Bench, MAPA et l'anglais (informés). |
| Shield bat Tonic | **NON** | Mesuré en interne, non publié (conditions de Tonic). |
| Shield plus rapide qu'Hexagone Rapide | **OUI** pour Shield règles | Chaque valeur de Shield (0,66 à 0,87 s) est sous chaque valeur d'Hexagone Rapide (23,1 s ou plus). Shield GLiNER : pas de résultat, les valeurs se chevauchent. |
| Shield plus rapide qu'Hexagone Précis | provisoire | Plus rapide sur chaque valeur, mais la séance de vitesse Précis est incomplète (D22). |

**Chiffres clés** (plus bas = mieux ; VM profil A, pas un portable)

| Outil | Données personnelles lisibles, REF (inventé) | Termes juridiques changés, REF (inventé) | Termes juridiques changés, Judilibre (tenu à l'écart) | Temps médian, un fichier REF de 10 pages | Mémoire, REF |
|---|---|---|---|---|---|
| Shield (règles) | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 296 sur 6 136 (4,8 %) ; sous-ensemble de 50 : 88 sur 1 476 (6,0 %) | 0,75 s | 74 Mo |
| Shield GLiNER | 56 sur 1 015 (5,5 %) | 15 sur 365 (4,1 %) | 1 048 sur 6 136 (17,1 %) ; 50 : 233 (15,8 %) | 23 s | 3,7 Go |
| Hexagone Rapide | 38 sur 1 015 (3,7 %) | 65 sur 365 (17,8 %) | 2 264 sur 6 136 (36,9 %) ; 50 : 581 (39,4 %) | 27 s | 1,6 à 1,7 Go |
| Hexagone Précis | 1 sur 1 015 (0,1 %) | 172 sur 365 (47,1 %) | sous-ensemble de 50 seulement : 637 sur 1 476 (43,2 %) | 540 s, soit 9 min (partiel) | 3,8 à 5,4 Go |
| Presidio | 249 sur 1 015 (24,5 %) | 56 sur 365 (15,3 %) | 911 sur 6 136 (14,8 %) ; 50 : 234 (15,9 %) | 1,6 s | 0,57 Go |
| Tonic (cloud) | mesuré en interne, non publié (conditions de Tonic) | | | | |

1. **Protection (P1).** Sur REF (inventé), Hexagone Rapide et Précis laissent moins de données personnelles lisibles
   que Shield. Shield ne manque aucun nom de personne sur REF. Ses 56 manques sont des sociétés (30), des adresses
   (11), des identifiants (10) et des numéros de dossier (5). Hexagone Précis expose aussi moins que Shield sur
   FR-PII-Bench (3 contre 36 sur 2 105), MAPA (100 contre 319 sur 1 615) et l'anglais (10 contre 142 sur 1 276), tous
   informés. Pas d'écart net sur Max (informé) ni sur le sous-ensemble Judilibre (tenu à l'écart). Hexagone Rapide
   expose moins que Shield sur MAPA (89 contre 319) et l'anglais (22 contre 142). Shield expose moins qu'Hexagone
   Rapide sur FR-PII-Bench (36 contre 72). Pas d'écart net sur Max ni sur Judilibre.
2. **Sur-masquage (P2).** Shield change moins de termes juridiques (juridictions, villes de juridiction, lois, codes,
   articles) qu'Hexagone Rapide et Précis, sur chaque jeu qui en contient (REF, MAPA, Max, Judilibre), avec un écart
   net. MAPA (informé) : 0 sur 1 344 pour Shield, 579 (43,1 %) pour Hexagone Rapide, 640 (47,6 %) pour Hexagone
   Précis. Les 15 changements de Shield sur REF sont des numéros de décision inventés, qu'Hexagone et Presidio
   changent aussi. Sur Judilibre, 257 des 296 changements de Shield sont des villes de juridiction.
3. **Le compromis.** Sur REF, Shield laisse plus de données personnelles lisibles qu'Hexagone. Shield change beaucoup
   moins de termes juridiques. Hexagone masque plus et change beaucoup plus le texte juridique.
4. **Shield GLiNER.** Il aide en anglais (27 contre 142 sur 1 276) et sur MAPA (222 contre 319 sur 1 615), deux jeux
   informés. Sur REF, sa sortie est identique à celle de Shield règles. Sur Judilibre (tenu à l'écart), il change
   1 048 termes juridiques (17,1 %) au lieu de 296 (4,8 %).
5. **Vitesse (VM profil A, pas un portable).** Un fichier REF de 10 pages, médiane de toutes les valeurs : Shield
   0,75 s ; Presidio 1,6 s ; Shield GLiNER 23 s ; Hexagone Rapide 27 s depuis le clic (30 s depuis la marque de
   départ) ; Hexagone Précis 540 s, soit 9 min (8 valeurs, partiel). Pour ce type de machine, Hexagone publie 30 s à
   1 min en Rapide et 3 à 6 min en Précis (estimations). Nous mesurons 23 à 32 s en Rapide et 7,0 à 10,5 min en
   Précis. Démarrage à froid : Shield 0,4 s ; Shield GLiNER 17,4 s ; Presidio 8,2 s ; Hexagone prêt entre 5,4 et
   15,5 s (lu sur des captures d'écran).
6. **Mémoire.** Shield 74 Mo sur REF (jusqu'à 216 Mo selon le jeu). Shield GLiNER 3,7 Go (jusqu'à 6,1 Go). Hexagone
   Rapide 1,6 à 1,7 Go. Hexagone Précis 3,8 à 5,4 Go : l'application plus un modèle de langue local, en hausse d'une
   tâche à l'autre. Presidio 0,57 Go (jusqu'à 0,82 Go).
7. **Où vont les données.** Shield et Presidio : rien ne sort de la machine (0 tentative de connexion, vérifié à
   chaque essai). Hexagone : traitement sur la machine selon sa documentation ; nous n'avons pas observé son trafic,
   ses conditions l'interdisent. Tonic Textual : le texte part dans le cloud de Tonic.
8. **Chiffres publiés par les éditeurs eux-mêmes.** Ils ne sont pas comparables aux nôtres (autres données, autre
   correcteur, autre mode). Tonic : 96,4 % de rappel NER sur PrivacyBench v2.5 avec Textual Graph Synthesis (fiche
   Hugging Face TonicAI/Privacy-Bench, révision a79d9e80, 15 octobre 2026) ; 93,9 % sur PrivacyBench v2 (étiquette
   v2, 22 septembre 2026). Hexagone : 93,7 % de rappel NER et 88,1 % combiné sur PrivacyBench
   (hexagone.ai/fr/research/privacy-bench, octobre 2026). Lus le 23 octobre 2026. Notre essai de Tonic utilise le
   chemin par défaut du SDK, pas Graph Synthesis.
9. **Contrôles.** Deux recomptes indépendants, avec un second correcteur écrit à partir du texte du protocole, ont
   vérifié chaque compte. Les corrections faites après avoir vu les scores sont dans D17 et D24. Exemple : Hexagone
   Rapide sur FR-PII-Bench passe de 68 à 72, à cause de mauvaises paires entre sorties et entrées. Aucune correction
   n'a changé une affirmation ni le verdict.
10. **Ce qui manque.** La séance de vitesse complète d'Hexagone Précis et le profil B (4 cœurs, 8 Go).

## Summary of October 2026 (Shield 0.3.1, unchanged)

**Status.** Accuracy: complete (6 data sets, every tool). Speed: partial. Hexagone Precis did only 3 of 5 tasks in
the speed session (deviation D22). Profile B (4 cores, 8 GB) did not run. The frozen files are intact (PREREG 685 of
685 files, PREREG_DATA 829 of 829).

**Read this before the numbers.**

- Shield is our product (RAGbase). We ran this test.
- Machine: a Windows VM in the cloud (profile A: 6 cores, 16 GB, no graphics card). It is not a laptop. The VM has no
  power cap and has instructions (AVX-512) that laptops do not have. On a laptop the times would be longer. Every local
  tool ran on the same VM.
- Hexagone operated by Claude at Hadi's instruction (D1). Claude used the app's own screens, one action at a time, with
  the default settings. The protocol said a person would operate it.
- Tonic: measured internally, not published (Tonic's terms).
- Status of each set for Shield. "Invented": REF, written by the Shield team, new to Shield at the freeze, not
  independent. "Informed": FR-PII-Bench, MAPA, Max, English; these sets shaped Shield. "Held-out": Judilibre, 200
  decisions drawn after the freeze, never seen by any tool.
- "Shield" alone means Shield 0.3.1 in rules mode, the product default. "Shield GLiNER" means rules plus the GLiNER
  model on the CPU.

**Verdict by the rule fixed in advance (protocol section 11.3)**

| Claim | Result | Reason |
|---|---|---|
| Shield beats Hexagone Fast | **NO** | On REF (invented), Hexagone Fast leaves less personal data readable, with a clear difference. Clear opposite differences also on MAPA and English (informed). |
| Shield beats Hexagone Precis | **NO** | On REF (invented), Hexagone Precis leaves less personal data readable, with a clear difference. Clear opposite differences also on FR-PII-Bench, MAPA and English (informed). |
| Shield beats Tonic | **NO** | Measured internally, not published (Tonic's terms). |
| Shield faster than Hexagone Fast | **YES** for Shield rules | Every Shield value (0.66 to 0.87 s) is below every Hexagone Fast value (23.1 s or more). Shield GLiNER: no claim, the values overlap. |
| Shield faster than Hexagone Precis | provisional | Faster on every value, but the Precis speed session is incomplete (D22). |

**Key numbers** (lower is better; VM profile A, not a laptop)

| Tool | Personal data readable, REF (invented) | Legal terms changed, REF (invented) | Legal terms changed, Judilibre (held-out) | Median time, one 10-page REF file | Memory, REF |
|---|---|---|---|---|---|
| Shield (rules) | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 296 of 6,136 (4.8 %); subset of 50: 88 of 1,476 (6.0 %) | 0.75 s | 74 MB |
| Shield GLiNER | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 1,048 of 6,136 (17.1 %); 50: 233 (15.8 %) | 23 s | 3.7 GB |
| Hexagone Fast | 38 of 1,015 (3.7 %) | 65 of 365 (17.8 %) | 2,264 of 6,136 (36.9 %); 50: 581 (39.4 %) | 27 s | 1.6 to 1.7 GB |
| Hexagone Precis | 1 of 1,015 (0.1 %) | 172 of 365 (47.1 %) | subset of 50 only: 637 of 1,476 (43.2 %) | 540 s, that is 9 min (partial) | 3.8 to 5.4 GB |
| Presidio | 249 of 1,015 (24.5 %) | 56 of 365 (15.3 %) | 911 of 6,136 (14.8 %); 50: 234 (15.9 %) | 1.6 s | 0.57 GB |
| Tonic (cloud) | measured internally, not published (Tonic's terms) | | | | |

1. **Protection (P1).** On REF (invented), Hexagone Fast and Precis leave less personal data readable than Shield.
   Shield misses no person name on REF. Its 56 misses are companies (30), addresses (11), identifiers (10) and case
   numbers (5). Hexagone Precis also exposes less than Shield on FR-PII-Bench (3 against 36 of 2,105), MAPA (100
   against 319 of 1,615) and English (10 against 142 of 1,276), all informed. No clear difference on Max (informed) or
   on the Judilibre subset (held-out). Hexagone Fast exposes less than Shield on MAPA (89 against 319) and English (22
   against 142). Shield exposes less than Hexagone Fast on FR-PII-Bench (36 against 72). No clear difference on Max or
   Judilibre.
2. **Over-masking (P2).** Shield changes fewer legal terms (courts, court cities, laws, codes, articles) than Hexagone
   Fast and Precis on every set that has them (REF, MAPA, Max, Judilibre), with a clear difference. MAPA (informed): 0
   of 1,344 for Shield, 579 (43.1 %) for Hexagone Fast, 640 (47.6 %) for Hexagone Precis. Shield's 15 changes on REF are
   invented precedent numbers, which Hexagone and Presidio also change. On Judilibre, 257 of Shield's 296 changes are court cities.
3. **The trade-off.** On REF, Shield leaves more personal data readable than Hexagone. Shield changes far fewer legal
   terms. Hexagone masks more and changes much more of the legal text.
4. **Shield GLiNER.** It helps on English (27 against 142 of 1,276) and on MAPA (222 against 319 of 1,615), two
   informed sets. On REF its output is identical to Shield rules. On Judilibre (held-out) it changes 1,048 legal terms
   (17.1 %) instead of 296 (4.8 %).
5. **Speed (VM profile A, not a laptop).** One 10-page REF file, median of all values: Shield 0.75 s; Presidio 1.6 s;
   Shield GLiNER 23 s; Hexagone Fast 27 s from the click (30 s from the start mark); Hexagone Precis 540 s, that is
   9 min (8 values, partial). For this kind of machine Hexagone publishes 30 s to 1 min in Fast and 3 to 6 min in
   Precis (estimates). We measure 23 to 32 s in Fast and 7.0 to 10.5 min in Precis. Cold start: Shield 0.4 s; Shield
   GLiNER 17.4 s; Presidio 8.2 s; Hexagone ready between 5.4 and 15.5 s (read from screenshots).
6. **Memory.** Shield 74 MB on REF (up to 216 MB depending on the set). Shield GLiNER 3.7 GB (up to 6.1 GB). Hexagone
   Fast 1.6 to 1.7 GB. Hexagone Precis 3.8 to 5.4 GB: the app plus a local language model, rising task after task.
   Presidio 0.57 GB (up to 0.82 GB).
7. **Where the data goes.** Shield and Presidio: nothing leaves the machine (0 connection attempts, checked in every
   run). Hexagone: processed on the machine according to its documentation; we did not watch its traffic, its terms
   forbid it. Tonic Textual: the text goes to Tonic's cloud.
8. **Numbers the vendors publish themselves.** They are not comparable with ours (other data, other scorer, other
   mode). Tonic: 96.4 % NER recall on PrivacyBench v2.5 with Textual Graph Synthesis (Hugging Face card
   TonicAI/Privacy-Bench, revision a79d9e80, 2026-10-15); 93.9 % on PrivacyBench v2 (tag v2, 2026-09-22). Hexagone:
   93.7 % NER recall and 88.1 % combined on PrivacyBench (hexagone.ai/fr/research/privacy-bench, October 2026). Read on
   2026-10-23. Our Tonic run used the default SDK path, not Graph Synthesis.
9. **Checks.** Two independent re-scores, with a second scorer written from the protocol text, checked every count.
   The corrections made after the scores were seen are in D17 and D24. Example: Hexagone Fast on FR-PII-Bench goes from
   68 to 72, because of wrong output-input pairs. No correction changed a claim or the verdict.
10. **What is missing.** The full Hexagone Precis speed session and profile B (4 cores, 8 GB).

---

## Tables of October 2026 (Shield 0.3.1 and the other tools, unchanged)

Row names: S-R = Shield 0.3.1 rules (product default); S-N = Shield 0.3.1 rules plus GLiNER on the CPU; S-N2 = S-N
with AVX2 only (speed only); H-F = Hexagone 0.3.9 Fast ("Standard"); H-P = Hexagone 0.3.9 Precis ("Analyse
approfondie"); T = Tonic Textual cloud API; P = Presidio 2.2.364. Machine: VM profile A for S-R, S-N, H-F, H-P and P;
T ran from a Mac client to Tonic's cloud (D3). Hexagone operated by Claude at Hadi's instruction (D1).

In every table, the Tonic row says: "mesuré en interne, non publié (conditions de Tonic) / measured internally, not
published (Tonic's terms)".

### Table 1. P1 protection and P2 over-masking (lower is better)

P1 = gold personal data items with one or more identifying words still readable at their place ("strict"), or more
than half of its identifying letters and digits kept ("value"); document properties apart. P2 = must-stay-clear items
(court, court city, article, code, law, legal reference, legal term) with a changed word; body only. In brackets: rate
and 95 % Wilson interval. A failed document counts as fully exposed (rule 8 of the protocol).

| Set (status) | Row | Docs (failed) | P1 exposed, strict | P1 exposed, value | P2 must-stay-clear altered |
|---|---|---|---|---|---|
| REF (invented) | S-R | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF (invented) | S-N | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF (invented) | H-F | 5 (0) | 38 of 1,015 (3.7 %; 2.7 to 5.1) | 9 of 1,015 (0.9 %; 0.5 to 1.7) | 65 of 365 (17.8 %; 14.2 to 22.1) |
| REF (invented) | H-P | 5 (0) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 172 of 365 (47.1 %; 42.1 to 52.2) |
| REF (invented) | T | | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | | |
| REF (invented) | P | 5 (0) | 249 of 1,015 (24.5 %; 22.0 to 27.3) | 185 of 1,015 (18.2 %; 16.0 to 20.7) | 56 of 365 (15.3 %; 12.0 to 19.4) |
| FR-PII-Bench (informed) | S-R | 300 (0) | 36 of 2,105 (1.7 %; 1.2 to 2.4) | 27 of 2,105 (1.3 %; 0.9 to 1.9) | no items |
| FR-PII-Bench (informed) | S-N | 300 (0) | 26 of 2,105 (1.2 %; 0.8 to 1.8) | 18 of 2,105 (0.9 %; 0.5 to 1.3) | no items |
| FR-PII-Bench (informed) | H-F | 300 (0) | 72 of 2,105 (3.4 %; 2.7 to 4.3) | 45 of 2,105 (2.1 %; 1.6 to 2.8) | no items |
| FR-PII-Bench (informed) | H-F, 30 % cut | 300 (34) | 336 of 2,105 (16.0 %; 14.5 to 17.6) | 315 of 2,105 (15.0 %; 13.5 to 16.6) | no items |
| FR-PII-Bench (informed) | H-P | 300 (0) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | no items |
| FR-PII-Bench (informed) | H-P, 30 % cut | 300 (38) | 307 of 2,105 (14.6 %; 13.1 to 16.2) | 307 of 2,105 (14.6 %; 13.1 to 16.2) | no items |
| FR-PII-Bench (informed) | T | | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | | |
| FR-PII-Bench (informed) | P | 300 (0) | 918 of 2,105 (43.6 %; 41.5 to 45.7) | 543 of 2,105 (25.8 %; 24.0 to 27.7) | no items |
| MAPA (informed) | S-R | 19 (0) | 319 of 1,615 (19.8 %; 17.9 to 21.8) | 286 of 1,615 (17.7 %; 15.9 to 19.6) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA (informed) | S-N | 19 (0) | 222 of 1,615 (13.7 %; 12.2 to 15.5) | 189 of 1,615 (11.7 %; 10.2 to 13.4) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA (informed) | H-F | 19 (0) | 89 of 1,615 (5.5 %; 4.5 to 6.7) | 58 of 1,615 (3.6 %; 2.8 to 4.6) | 579 of 1,344 (43.1 %; 40.5 to 45.7) |
| MAPA (informed) | H-P | 19 (0) | 100 of 1,615 (6.2 %; 5.1 to 7.5) | 90 of 1,615 (5.6 %; 4.6 to 6.8) | 640 of 1,344 (47.6 %; 45.0 to 50.3) |
| MAPA (informed) | T | not sent (real court texts, protocol 9.2) | | | |
| MAPA (informed) | P | 19 (0) | 294 of 1,615 (18.2 %; 16.4 to 20.2) | 216 of 1,615 (13.4 %; 11.8 to 15.1) | 242 of 1,344 (18.0 %; 16.0 to 20.2) |
| Max (informed) | S-R | 33 (1) | 54 of 1,003 (5.4 %; 4.1 to 7.0) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max (informed) | S-N | 33 (1) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 43 of 1,003 (4.3 %; 3.2 to 5.7) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max (informed) | H-F | 33 (2) | 67 of 1,003 (6.7 %; 5.3 to 8.4) | 56 of 1,003 (5.6 %; 4.3 to 7.2) | 68 of 144 (47.2 %; 39.2 to 55.3) |
| Max (informed) | H-P | 33 (2) | 38 of 1,003 (3.8 %; 2.8 to 5.2) | 33 of 1,003 (3.3 %; 2.4 to 4.6) | 84 of 144 (58.3 %; 50.2 to 66.1) |
| Max (informed) | T | | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | | |
| Max (informed) | P | 33 (0) | 393 of 1,003 (39.2 %; 36.2 to 42.2) | 315 of 1,003 (31.4 %; 28.6 to 34.3) | 80 of 144 (55.6 %; 47.4 to 63.4) |
| Judilibre (held-out) | S-R | 200 (0) | 6 of 673 (0.9 %; 0.4 to 1.9) | 2 of 673 (0.3 %; 0.1 to 1.1) | 296 of 6,136 (4.8 %; 4.3 to 5.4) |
| Judilibre (held-out) | S-N | 200 (0) | 4 of 673 (0.6 %; 0.2 to 1.5) | 2 of 673 (0.3 %; 0.1 to 1.1) | 1,048 of 6,136 (17.1 %; 16.2 to 18.0) |
| Judilibre (held-out) | H-F | 200 (0) | 11 of 673 (1.6 %; 0.9 to 2.9) | 8 of 673 (1.2 %; 0.6 to 2.3) | 2,264 of 6,136 (36.9 %; 35.7 to 38.1) |
| Judilibre (held-out) | T | not sent (real court texts, protocol 9.2) | | | |
| Judilibre (held-out) | P | 200 (0) | 93 of 673 (13.8 %; 11.4 to 16.6) | 68 of 673 (10.1 %; 8.0 to 12.6) | 911 of 6,136 (14.8 %; 14.0 to 15.8) |
| Judilibre, Precis subset of 50 (held-out) | S-R | 50 (0) | 3 of 194 (1.5 %; 0.5 to 4.4) | 1 of 194 (0.5 %; 0.1 to 2.9) | 88 of 1,476 (6.0 %; 4.9 to 7.3) |
| Judilibre, Precis subset of 50 (held-out) | S-N | 50 (0) | 1 of 194 (0.5 %; 0.1 to 2.9) | 1 of 194 (0.5 %; 0.1 to 2.9) | 233 of 1,476 (15.8 %; 14.0 to 17.7) |
| Judilibre, Precis subset of 50 (held-out) | H-F | 50 (0) | 2 of 194 (1.0 %; 0.3 to 3.7) | 1 of 194 (0.5 %; 0.1 to 2.9) | 581 of 1,476 (39.4 %; 36.9 to 41.9) |
| Judilibre, Precis subset of 50 (held-out) | H-P | 50 (0) | 0 of 194 (0.0 %; 0.0 to 1.9) | 0 of 194 (0.0 %; 0.0 to 1.9) | 637 of 1,476 (43.2 %; 40.7 to 45.7) |
| Judilibre, Precis subset of 50 (held-out) | P | 50 (0) | 32 of 194 (16.5 %; 11.9 to 22.4) | 21 of 194 (10.8 %; 7.2 to 16.0) | 234 of 1,476 (15.9 %; 14.1 to 17.8) |
| English (informed) | S-R | 241 (0) | 142 of 1,276 (11.1 %; 9.5 to 13.0) | 135 of 1,276 (10.6 %; 9.0 to 12.4) | no items |
| English (informed) | S-N | 241 (0) | 27 of 1,276 (2.1 %; 1.5 to 3.1) | 23 of 1,276 (1.8 %; 1.2 to 2.7) | no items |
| English (informed) | H-F | 241 (0) | 22 of 1,276 (1.7 %; 1.1 to 2.6) | 15 of 1,276 (1.2 %; 0.7 to 1.9) | no items |
| English (informed) | H-P | 241 (0) | 10 of 1,276 (0.8 %; 0.4 to 1.4) | 8 of 1,276 (0.6 %; 0.3 to 1.2) | no items |
| English (informed) | T | | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | | |
| English (informed) | P | 241 (0) | 108 of 1,276 (8.5 %; 7.1 to 10.1) | 107 of 1,276 (8.4 %; 7.0 to 10.0) | no items |

Notes on Table 1.

- **Judilibre P1 is indicative only.** Its gold is 673 names of lawyers, judges and clerks found by fixed patterns. The
  parties are already pseudonymised in the source.
- **Precis subset.** Hexagone Precis ran the pre-registered subset of 50 Judilibre decisions (protocol 5.3 and 9.4).
  The other rows were scored again on the same 50, with the same per-document results as in their 200-document runs.
  The 200-document rows stay the Judilibre headline.
- **FR-PII-Bench, Hexagone pairs.** Hexagone masks output file names. Outputs were paired to inputs with the app's own
  mapping export and its processing order (D17, D23, D24). A first pairing by text overlap was wrong for 172 of the
  300 Fast outputs; with the right pairs, H-F goes from 68 to 72 (30 % cut: 333 to 336). For Precis, every pairing
  method gives the same counts.
- **30 % cut.** A sensitivity reading (D11, D12): an output that does not match its input with 30 % text overlap or
  more counts as failed. It is not the primary reading.
- **Failed documents on Max.** S-R and S-N: 1 spreadsheet that Shield 0.3.1 cannot read on the file path. H-F and
  H-P: 2 documents each under the retention rule; for H-P they hold 19 of its 38 exposures. On 3 Max documents, H-P
  showed an "Incomplet" badge; all 3 have a readable output and are scored as normal.
- **MAPA gold.** 8 court-city keep items are in the gold twice. Without them: 1,336 items; S-R and S-N 0, H-F 571
  (42.7 %). One MAPA gold item sits inside another; S-R and S-N count it twice (319 and 222). The table keeps the frozen
  gold. No claim changes.

### Table 2. Claims per set (paired bootstrap over documents)

A claim is allowed only when the whole 95 % interval of the difference is on one side of 0 (2,000 resamples, seed
20261023). A P1 claim needs both the strict and the value reading to agree. "X better" = X exposes less (P1) or alters
fewer must-stay-clear items (P2). "none" = no clear difference. REF has 5 documents from one template, so its
intervals are narrow. Comparisons with Tonic: mesuré en interne, non publié (conditions de Tonic) / measured
internally, not published (Tonic's terms).

| Set (status) | Shield row against | P1, S-R | P1, S-N | P2, S-R | P2, S-N |
|---|---|---|---|---|---|
| REF (invented) | H-F | H-F better | H-F better | S-R better | S-N better |
| REF (invented) | H-P | H-P better | H-P better | S-R better | S-N better |
| REF (invented) | P | S-R better | S-N better | S-R better | S-N better |
| REF (invented) | S-R against S-N | none | | none | |
| FR-PII-Bench (informed) | H-F | S-R better | S-N better | no items | no items |
| FR-PII-Bench (informed) | H-F, 30 % cut | S-R better | S-N better | no items | no items |
| FR-PII-Bench (informed) | H-P | H-P better | H-P better | no items | no items |
| FR-PII-Bench (informed) | H-P, 30 % cut | S-R better | S-N better | no items | no items |
| FR-PII-Bench (informed) | P | S-R better | S-N better | no items | no items |
| FR-PII-Bench (informed) | S-R against S-N | S-N better | | no items | |
| MAPA (informed) | H-F | H-F better | H-F better | S-R better | S-N better |
| MAPA (informed) | H-P | H-P better | H-P better | S-R better | S-N better |
| MAPA (informed) | P | none | none | S-R better | S-N better |
| MAPA (informed) | S-R against S-N | S-N better | | none | |
| Max (informed) | H-F | none | none | S-R better | S-N better |
| Max (informed) | H-P | none | none | S-R better | S-N better |
| Max (informed) | P | S-R better | S-N better | S-R better | S-N better |
| Max (informed) | S-R against S-N | none (readings disagree) | | none | |
| Judilibre (held-out) | H-F | none | none | S-R better | S-N better |
| Judilibre (held-out) | P | S-R better | S-N better | S-R better | none |
| Judilibre (held-out) | S-R against S-N | none | | S-R better | |
| Judilibre, Precis subset of 50 (held-out) | H-F | none | none | S-R better | S-N better |
| Judilibre, Precis subset of 50 (held-out) | H-P | none (the interval touches 0) | none (the interval touches 0) | S-R better | S-N better |
| Judilibre, Precis subset of 50 (held-out) | P | S-R better | S-N better | S-R better | none |
| Judilibre, Precis subset of 50 (held-out) | S-R against S-N | none | | S-R better | |
| English (informed) | H-F | H-F better | none | no items | no items |
| English (informed) | H-P | H-P better | H-P better | no items | no items |
| English (informed) | P | P better | S-N better | no items | no items |
| English (informed) | S-R against S-N | S-N better | | no items | |

### Table 3. Overall claims (protocol section 11.3)

| Claim | Needs | Found | Allowed? |
|---|---|---|---|
| Shield beats Hexagone Fast | a P2 claim on held-out Judilibre; P1 and P2 claims on REF; no opposite claim on any other set | Judilibre P2: Shield better (S-R and S-N). REF P2: Shield better. REF P1: **Hexagone Fast better**. Opposite P1 claims on MAPA (S-R, S-N) and English (S-R). | **No** |
| Shield beats Hexagone Precis | the same (Judilibre for H-P = the pre-registered subset of 50) | Judilibre subset P2: Shield better (S-R 88 and S-N 233 against 637 of 1,476). REF P2: Shield better. REF P1: **Hexagone Precis better**. Opposite P1 claims on FR-PII-Bench (S-R, S-N), MAPA (S-R, S-N) and English (S-R, S-N). Max: P1 none, P2 Shield better. | **No** |
| Shield beats Tonic | P1 and P2 claims on REF; no opposite claim on any other set Tonic ran | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | **No** |
| Reverse, per set | the same rule | Hexagone Fast exposes less than Shield on REF, MAPA and English (against S-R). Hexagone Precis exposes less on REF, FR-PII-Bench, MAPA and English (against S-R and S-N). No clear P1 difference with Hexagone Precis on Max and the Judilibre subset. Shield alters fewer must-stay-clear items than Hexagone Fast and Precis on every set that has them (REF, MAPA, Max, Judilibre). | per set only |
| Shield against Presidio (not a section 11.3 claim) | | S-N: better or no difference on every set, no opposite claim. S-R: better on REF, FR-PII-Bench, Max, Judilibre, and on MAPA P2; Presidio exposes less on English. | reported only |

### Table 4. P1 per label on REF (invented), exposed, strict reading

| Label (items) | S-R | S-N | H-F | H-P | P | T |
|---|---:|---:|---:|---:|---:|---|
| PERSON (580) | 0 | 0 | 0 | 0 | 22 | internal |
| ORG (175) | 30 | 30 | 20 | 0 | 59 | internal |
| ADDRESS (70) | 11 | 11 | 1 | 0 | 60 | internal |
| ID_CODE (50) | 10 | 10 | 0 | 0 | 47 | internal |
| EMAIL (45) | 0 | 0 | 1 | 0 | 0 | internal |
| PHONE (25) | 0 | 0 | 0 | 0 | 1 | internal |
| CASE_REF (20) | 5 | 5 | 16 | 1 | 20 | internal |
| BIRTHDATE (15) | 0 | 0 | 0 | 0 | 15 | internal |
| IBAN (10) | 0 | 0 | 0 | 0 | 0 | internal |
| SIREN (10) | 0 | 0 | 0 | 0 | 10 | internal |
| SIRET (10) | 0 | 0 | 0 | 0 | 10 | internal |
| NIR (5) | 0 | 0 | 0 | 0 | 5 | internal |
| Total (1,015) | 56 | 56 | 38 | 1 | 249 | internal |

"internal" = mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms).

### Table 5. P2 per class (altered, body)

Classes marked * are must-stay-clear (P2). Dates and amounts are reported apart: masking them is a policy choice, not
an error. Judilibre placeholders are reported apart too.

**REF (invented)**

| Class (items) | S-R | S-N | H-F | H-P | P | T |
|---|---:|---:|---:|---:|---:|---|
| article* (145) | 0 | 0 | 0 | 17 | 0 | internal |
| code* (125) | 0 | 0 | 0 | 80 | 0 | internal |
| court* (30) | 0 | 0 | 30 | 30 | 25 | internal |
| court city* (20) | 0 | 0 | 20 | 20 | 16 | internal |
| law* (10) | 0 | 0 | 0 | 10 | 0 | internal |
| legal reference* (15, invented precedent numbers) | 15 | 15 | 15 | 15 | 15 | internal |
| legal term* (20) | 0 | 0 | 0 | 0 | 0 | internal |
| date (245) | 1 | 1 | 245 | 245 | 0 | internal |
| amount (155) | 0 | 0 | 155 | 155 | 0 | internal |

**Judilibre, 200 decisions (held-out)**

| Class (items) | S-R | S-N | H-F | P |
|---|---:|---:|---:|---:|
| article* (2,115) | 15 | 730 | 35 | 41 |
| code* (1,637) | 13 | 14 | 10 | 1 |
| court* (1,284) | 0 | 6 | 1,219 | 240 |
| court city* (854) | 257 | 286 | 851 | 628 |
| law* (246) | 11 | 12 | 149 | 1 |
| placeholder (8,648) | 884 | 4,906 | 7,363 | 4,620 |

**Judilibre, Precis subset of 50 (held-out)**

| Class (items) | S-R | S-N | H-F | H-P | P |
|---|---:|---:|---:|---:|---:|
| article* (502) | 3 | 140 | 4 | 28 | 5 |
| code* (357) | 3 | 3 | 7 | 39 | 0 |
| court* (333) | 0 | 4 | 319 | 325 | 80 |
| court city* (201) | 82 | 85 | 200 | 200 | 148 |
| law* (83) | 0 | 1 | 51 | 45 | 1 |
| placeholder (1,752) | 206 | 1,104 | 1,396 | 1,348 | 969 |

### Table 6. Words changed outside the gold (secondary reading)

Share of the words that are not gold personal data and that the tool changed (dates and amounts included). Lower
means more of the text stays as written.

| Set (status) | S-R | S-N | H-F | H-P | P |
|---|---|---|---|---|---|
| REF (invented), of 22,320 words | 43 (0.2 %) | 43 (0.2 %) | 2,009 (9.0 %) | 3,262 (14.6 %) | 832 (3.7 %) |
| Judilibre, Precis subset of 50 (held-out), of 85,395 words | 3,620 (4.2 %) | 5,698 (6.7 %) | 12,016 (14.1 %) | 14,324 (16.8 %) | 5,458 (6.4 %) |

Tonic: mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms).

### Table 7. Speed on REF (VM profile A, not a laptop)

One task = one 10-page REF file (about 29,383 characters, 20.7 personal data items per page). Values: day 1 (5) plus
one speed session (5), in a fresh process or app session. Shield and Presidio: the task time of their own logs.
Hexagone: two readings, from the click on "Démarrer la synchronisation" and from the operator's start mark, each to the
last output file time. Cold start: Shield and Presidio, process start to the end of a warm-up mask (3 processes);
Hexagone, app launch to the first screenshot of the ready main window, given as a range (3 launches; D21). Only
aggregates are given.

| Row | n | Median (s) | Range (s) | s per page | Cold start (s) |
|---|---:|---:|---|---:|---|
| S-R | 10 | 0.75 | 0.66 to 0.87 | 0.075 | 0.42 to 0.44 |
| S-N | 10 | 23.26 | 20.34 to 28.28 | 2.33 | 17.38 to 17.48 |
| S-N2 (AVX2 only) | 5 | 21.09 | 20.67 to 21.24 | 2.11 | 17.20 to 17.39 |
| P | 10 | 1.59 | 1.58 to 2.12 | 0.16 | 8.18 to 8.24 |
| H-F, from the click | 10 | 26.93 | 23.08 to 31.69 | 2.69 | ready between 6.3 and 15.5 |
| H-F, from the start mark | 10 | 30.10 | 26.66 to 36.94 | 3.01 | same |
| H-P, from the click (partial) | 8 | 540.28 | 417.77 to 632.34 | 54.0 | ready between 5.4 and 13.7 |
| H-P, from the start mark (partial) | 8 | 543.82 | 421.57 to 635.20 | 54.4 | same |
| T | mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms) | | | | |

Speed claims (rule 11.3: every value of one row below every value of the other):

| Pair | Result |
|---|---|
| S-R against H-F | **S-R faster** (0.66 to 0.87 s against 23.08 s or more from the click, 26.66 s or more from the start mark). Final. |
| S-N against H-F | No claim. The values overlap in both readings. |
| S-R and S-N against H-P | Faster on every value we have (H-P 417.77 s or more). **Provisional**: the Precis speed session is partial (3 of 5 tasks, D22). |
| S-R against P | S-R faster. |
| P against S-N | Presidio faster. |
| T | No claim. Tonic times include the network (D3). |

Notes. (a) To the operator's end mark, the medians are 43.33 s (H-F) and 557.16 s (H-P) from the click. (b) The day-1
clicks are Mac times in whole seconds, and the Mac clock was about 1 s behind the VM. So day-1 values "from the click"
can be about 1 s too long. With 1 s less, the H-F median stays 26.93 s and the H-P median is 539.28 s. No claim
changes. (c) Nothing else ran on the VM during a timed task, apart from the output-folder poll, the memory samplers
and one status screenshot (checked in the logs; D20, D24). (d) H-P got faster task after task in the speed session
while its local model process grew in memory. (e) The two cold-start definitions are not the same, so the Shield and
Hexagone cold starts are not a claim.

### Table 8. REF against Hexagone's published speed table

Hexagone's reference file: a 10-page Word document, about 30,000 characters, about 20 personal data items per page
(hexagone.ai/fr/system-requirements, read 2026-10-23). Our REF: 10 pages, 29,383 characters on average, 20.7 items
per page.

| Machine row in Hexagone's table | Mode | Hexagone's table | Measured here (VM profile A) |
|---|---|---|---|
| Windows laptop 2023 or later, 16 GB, 6 cores (= profile A) | Fast | 30 s to 1 min (estimated) | 23.1 to 31.7 s from the click (median 26.9); 26.7 to 36.9 s from the start mark (median 30.1) |
| same | Precis | 3 to 6 min (estimated) | 7.0 to 10.5 min from the click (median 9.0; partial, 8 values), 1.2 to 3.5 times the table |
| Windows laptop 2019, 8 GB, 4 cores (= profile B) | Fast | 1 min 20 s to 1 min 45 s (measured by Hexagone) | not run |
| same | Precis | 6 to 10 min (measured by Hexagone) | not run |

### Table 9. Peak memory (VM profile A)

| Row | REF | Up to, over the sets | How measured |
|---|---|---|---|
| S-R | 74 to 75 MB | 216 MB (FR-PII-Bench) | Windows peak working set of the process, read from outside |
| S-N | 3,721 to 3,771 MB | 6,129 MB (Max) | same |
| S-N2 | 3,700 to 3,825 MB | speed rows only | same |
| P | 565 to 566 MB | 817 MB (MAPA) | same |
| H-F | 1,640 to 1,737 MB | REF only sampled | sum of the app's working sets, once per second (Windows process list) |
| H-P | 3,752 to 5,436 MB together: app 1,687 to 1,755 MB plus a local language-model process 2,120 to 3,760 MB | REF only sampled | same, plus a second sampler for the model process; it rose task after task |
| T | not applicable (Tonic's cloud) | | |

Free memory at session start: about 11.7 to 12.0 GB (Hexagone sessions, app closed); 9.0 GB on the Shield and
Presidio day (Hexagone idle in the background with about 1.6 GB). On profile B (8 GB), S-N on Max (6.1 GB) and H-P (up
to 5.4 GB) may run short of memory. Not run yet.

### Table 10. Where the data goes (P4)

| Row | Where the text is processed | What leaves the machine | How we know |
|---|---|---|---|
| S-R, S-N | on the VM | nothing: 0 outbound connection attempts in 12 per-set runs and 9 speed processes | our own process guard, every run |
| P | on the VM | nothing: 0 attempts in 6 runs and 3 speed processes | the same guard |
| H-F, H-P | on the VM (detection model; in Precis also a local language-model process seen in the Windows process list) | documented: the trial's daily machine check with Hexagone's server; auto-update was on (version 0.3.9 at every check) | Hexagone's documentation and the Windows process list only; we did not watch its traffic (its terms) |
| T | Tonic's cloud (textual.tonic.ai) | every file sent | by design |

---

## Tables for Shield 0.4.0 (protocol addendum 4, deviation D28; added 2026-11-11)

Row names: S-R4 = Shield 0.4.0 rules (the product default); S-N4 = Shield 0.4.0 rules plus GLiNER on the CPU (the same
model files as row S-N). The other row names are those of the October tables. Tables 1 to 10 above are not changed
and get no 0.4.0 row. Machine: VM profile A, not a laptop; Shield 0.4.0 session of 2026-11-11; the other rows are the
October runs. Shield 0.4.0 was built after the first results of this comparison were known; the other tools were measured in October and not run again. No set is held-out for Shield 0.4.0.
Tonic: mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms); the
tables below have no Tonic row.

### Table 11. Status of each set for Shield 0.4.0

"Held-out" is used only when it is proven that neither the set nor a result on it could reach the build. That is
true for no set here.

| Set | Status for Shield 0.4.0 (S-R4 and S-N4) | Short label | Status for Shield 0.3.1 (October) | Status for Hexagone and Presidio |
|---|---|---|---|---|
| REF | written by the Shield team; not independent. Scored with Shield 0.3.1 on 2026-10-25, and the misses per label were known while 0.4.0 was built. No record shows that the 0.4.0 work read the files, the gold, Shield's outputs or its scores. Not proven | not held-out: team-written, 0.3.1 results known; unused by record | invented | new to both |
| FR-PII-Bench | informed, and a regression gate of the 0.4.0 work at every step | gate | informed | not seen, as far as we know |
| MAPA | informed, and a regression gate of the 0.4.0 work at every step | gate | informed | not seen, as far as we know |
| Max | informed; audited at every step; run in full with the finished build; one failure that this study found (an Excel workbook that 0.3.1 could not read) was fixed in 0.4.0 | gate, with a fix from this study | informed | not seen, as far as we know |
| Judilibre | not used by the 0.4.0 work according to every record; not proven. The 0.3.1 results on it were known. Another draw of the same source was a gate at every step, on the same kind of measure | not held-out: 0.3.1 results known, same-source gate; unused by record | held-out | held-out |
| English | informed: part of the development set of the 0.4.0 work | development set (in-sample) | informed | public benchmark; Hexagone publishes numbers on it |

Timeline: first scores of every tool on 2026-10-25. Nine of the ten accepted changes of the 0.4.0 work were committed
after these first scores. The rules for the 0.4.0 rows were frozen on 2026-11-11 at 09:04 UTC, before any Shield 0.4.0 output
on these sets existed through the head-to-head runner. A held-out number for 0.4.0 needs a new draw made after that
freeze; it is not part of this document, and Hexagone could not be run on it.

### Table 12. P1 protection and P2 over-masking with the Shield 0.4.0 rows (lower is better)

Same definitions as Table 1. The status column gives the status of the set for the row of that line. The rows S-R,
S-N, H-F, H-P and P are the October rows of Table 1, printed again for reading.

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

Notes on Table 12.

- **Identical outputs.** On REF, FR-PII-Bench, MAPA and Judilibre the output text of each 0.4.0 row is identical to
  that of the 0.3.1 row of the same mode. On these sets the per-label and per-class counts of S-R4 and S-N4 equal
  those of S-R and S-N in Tables 4 and 5.
- **Max and the workbook.** Shield 0.3.1 failed on one Excel workbook (no output). Shield 0.4.0 reads it. The reader
  fix came from this study. The lines "Max without the workbook" give the same rows on the 32 other documents;
  for every row, the per-document results are those of its 33-document run. H-F and H-P fail the workbook under
  the retention rule, in October as now.
- **FR-PII-Bench, H-F.** The line shows the corrected pairs of October (72 and 45; notes on Table 1).
- **Judilibre P1 is indicative only** (notes on Table 1). The Precis subset: the 50 decisions that H-P ran.
- **English by label.** Exposed organisation names: 104 of 246 for S-R4 (103 for S-R) and 48 of 246 for S-N4 (26
  for S-N). The other labels do not change (given names 35 and 1 of 867, family names 4 and 0 of 97, e-mail
  addresses and phone numbers 0).
- **Secondary reading, words changed outside the gold.** REF: 43 of 22,320 for both 0.4.0 rows, as for 0.3.1. Max
  (33 documents): S-R4 82 of 25,814; S-N4 251 of 25,814, of which 53 in the workbook. English: S-R4 197 of 22,276
  (S-R 198); S-N4 309 (S-N 321).

### Table 13. Claims per set for the Shield 0.4.0 rows (paired bootstrap over documents)

Same rule as Table 2: a claim needs the whole 95 % interval of the difference on one side of 0 (2,000 resamples,
seed 20261023), and a P1 claim needs the strict and the value reading to agree. "X better" = X exposes less (P1) or
alters fewer must-stay-clear items (P2). "none" = no clear difference. Claims in both directions are listed with
the same weight. The last column compares each line with the line of the 0.3.1 rows in Table 2. Comparisons with
Tonic: mesuré en interne, non publié (conditions de Tonic) / measured internally, not published (Tonic's terms).

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

Notes on Table 13.

- **The one line that differs from October.** English, against H-F, row S-N4: 49 against 22 of 1,276; strict
  difference +2.12 points (95 % interval +0.84 to +3.34), value difference +2.04 points (+0.79 to +3.26). For the
  0.3.1 row S-N the interval held 0 (27 against 22). English is a development set of Shield 0.4.0.
- **Max.** A claim in favour of a 0.4.0 row on Max is made only when it holds on the 33 documents and on the 32
  documents without the workbook, because the reader fix came from this study. Every Max claim of this table holds
  in both readings. No claim against a 0.4.0 row exists on Max.
- **FR-PII-Bench, H-F.** The paired test was run with the first pairing of October (68 exposed) and again with the
  corrected pairs (72 exposed): the same claim both times.
- **Judilibre.** A claim on this set reads: "the fresh Judilibre draw (held-out for the other tool; not held-out
  for Shield 0.4.0: 0.3.1 results known, same-source gate; unused by record)".
- **Size of the main differences** (Shield row minus other row, in points, with the 95 % interval). REF P1: S-R4
  and S-N4 against H-F +1.77 (+1.58 to +1.97), against H-P +5.42 (+5.12 to +5.71). REF P2: against H-F -13.70,
  against H-P -43.01 (-44.11 to -42.47). MAPA P1: S-R4 against H-F +14.24 (+9.12 to +19.09), S-N4 against H-F
  +8.24 (+3.86 to +11.99). MAPA P2: against H-F -43.08 (-48.89 to -37.62). Judilibre P2: S-R4 against H-F -32.07
  (-34.48 to -29.78), S-N4 against H-F -19.82 (-23.59 to -16.14). English P1: S-R4 against H-F +9.48 (+7.37 to
  +11.59), S-R4 against H-P +10.42 (+8.19 to +12.67), S-N4 against H-P +3.06 (+1.96 to +4.12).

### Table 14. The section 11.3 reading for Shield 0.4.0 (addendum 4, section 20.9)

Wording: "the conditions of section 11.3 are met (or not met)". No sentence says that Shield 0.4.0 beats a tool.
Speed is not part of this reading. First the overall line, the reading of Table 3: every needed claim must hold
for both Shield rows, and an opposite claim of either row counts.

| Overall line | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) |
|---|---|---|
| Shield 0.4.0 (S-R4 and S-N4 together) | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-F better); S-N4: no P1 claim on REF (H-F better). Opposite claims: S-R4: REF P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: MAPA P1; S-N4: English P1 | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-P better); S-N4: no P1 claim on REF (H-P better). Opposite claims: S-R4: REF P1; S-R4: FR-PII-Bench P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: FR-PII-Bench P1; S-N4: MAPA P1; S-N4: English P1 |
| Shield 0.3.1 (S-R and S-N together), Table 3 of October, cited as written | No | No |

Then the row-level table, an addition of addendum 4. A row-level reading never stands for "Shield 0.4.0"; the
product default is the rules row. Conditions for a row: against H-F, a P2 claim on Judilibre (200), a P1 and a P2
claim on REF, and no opposite claim on any of the six sets; against H-P, the same with the Judilibre Precis subset
of 50. Presidio has no overall reading in section 11.3: per-set claims only.

| Shield row | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) | Against Presidio (per set only) |
|---|---|---|---|
| S-R4, Shield 0.4.0 rules (product default) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N4, Shield 0.4.0 rules + GLiNER | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |
| S-R, Shield 0.3.1 rules (October files, same rule) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N, Shield 0.3.1 rules + GLiNER (the same) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |

The needed claims that hold, for every row: the P2 claim on Judilibre and the P2 claim on REF. The needed claim that
fails, for every row: the P1 claim on REF (Hexagone Fast and Precis expose less). One cell of a 0.4.0 row differs
from the 0.3.1 row of the same mode: S-N4 against H-F has one more opposite claim, P1 on English (a development set
of Shield 0.4.0). Set status for Shield 0.4.0: Table 11. Tonic: mesuré en interne, non publié (conditions de Tonic) /
measured internally, not published (Tonic's terms).

### Table 15. Shield 0.4.0 against Shield 0.3.1, per set and mode

Paired comparison of each 0.4.0 row with the 0.3.1 row of the same mode. Difference = 0.3.1 row minus 0.4.0 row, in
points, with the 95 % interval (above 0: 0.4.0 exposes or alters less). No pooled claim is made: per set and per
measure only. Claims in both directions have the same weight. The 0.3.1 rows ran on 2026-10-25, the 0.4.0 rows on
2026-11-11, both on the VM profile A.

| Mode | Set (status for Shield 0.4.0) | Identical outputs | P1 strict, 0.3.1 to 0.4.0 | P1 strict difference (95 %) | P1 value, 0.3.1 to 0.4.0 | Protection | P2, 0.3.1 to 0.4.0 | Legal-term fidelity | Gold items gained / lost |
|---|---|---|---|---|---|---|---|---|---|
| rules | REF (not held-out: team-written, 0.3.1 results known; unused by record) | 5 of 5 | 56 to 56 of 1,015 | +0.00 (+0.00 to +0.00) | 31 to 31 | identical outputs (5 of 5) | 15 to 15 of 365 | identical outputs (5 of 5) | 0 / 0 |
| rules | FR-PII-Bench (gate) | 300 of 300 | 36 to 36 of 2,105 | +0.00 (+0.00 to +0.00) | 27 to 27 | identical outputs (300 of 300) | no items | no items | 0 / 0 |
| rules | MAPA (gate) | 19 of 19 | 319 to 319 of 1,615 | +0.00 (+0.00 to +0.00) | 286 to 286 | identical outputs (19 of 19) | 0 to 0 of 1,344 | identical outputs (19 of 19) | 0 / 0 |
| rules | Max, 33 documents (gate, with a fix from this study) | 32 of 33 | 54 to 52 of 1,003 | +0.20 (+0.00 to +0.73) | 50 to 48 | no clear change | 3 to 3 of 144 | no clear change | 2 (PERSON 2) / 0 |
| rules | Max without the workbook, 32 documents (gate, with a fix from this study) | 32 of 32 | 52 to 52 of 1,001 | +0.00 (+0.00 to +0.00) | 48 to 48 | identical outputs (32 of 32) | 3 to 3 of 144 | identical outputs (32 of 32) | 0 / 0 |
| rules | Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | 200 of 200 | 6 to 6 of 673 | +0.00 (+0.00 to +0.00) | 2 to 2 | identical outputs (200 of 200) | 296 to 296 of 6,136 | identical outputs (200 of 200) | 0 / 0 |
| rules | English (development set (in-sample)) | 127 of 241 | 142 to 143 of 1,276 | -0.08 (-0.63 to +0.42) | 135 to 136 | no clear change | no items | no items | 4 (ORGANIZATION 4) / 5 (ORGANIZATION 5) |
| rules + GLiNER | REF (not held-out: team-written, 0.3.1 results known; unused by record) | 5 of 5 | 56 to 56 of 1,015 | +0.00 (+0.00 to +0.00) | 31 to 31 | identical outputs (5 of 5) | 15 to 15 of 365 | identical outputs (5 of 5) | 0 / 0 |
| rules + GLiNER | FR-PII-Bench (gate) | 300 of 300 | 26 to 26 of 2,105 | +0.00 (+0.00 to +0.00) | 18 to 18 | identical outputs (300 of 300) | no items | no items | 0 / 0 |
| rules + GLiNER | MAPA (gate) | 19 of 19 | 222 to 222 of 1,615 | +0.00 (+0.00 to +0.00) | 189 to 189 | identical outputs (19 of 19) | 0 to 0 of 1,344 | identical outputs (19 of 19) | 0 / 0 |
| rules + GLiNER | Max, 33 documents (gate, with a fix from this study) | 28 of 33 | 50 to 48 of 1,003 | +0.20 (+0.00 to +0.73) | 43 to 41 | no clear change | 6 to 6 of 144 | no clear change | 2 (PERSON 2) / 0 |
| rules + GLiNER | Max without the workbook, 32 documents (gate, with a fix from this study) | 28 of 32 | 48 to 48 of 1,001 | +0.00 (+0.00 to +0.00) | 41 to 41 | no clear change | 6 to 6 of 144 | no clear change | 0 / 0 |
| rules + GLiNER | Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | 200 of 200 | 4 to 4 of 673 | +0.00 (+0.00 to +0.00) | 2 to 2 | identical outputs (200 of 200) | 1,048 to 1,048 of 6,136 | identical outputs (200 of 200) | 0 / 0 |
| rules + GLiNER | English (development set (in-sample)) | 57 of 241 | 27 to 49 of 1,276 | -1.72 (-2.49 to -1.01) | 23 to 41 | **0.4.0 exposes more** | no items | no items | 0 / 22 (ORGANIZATION 22) |

Notes on Table 15. The one document that changes status is the Max workbook: failed with 0.3.1, read with 0.4.0, in
both modes; its 2 person names are now protected. The frozen rule counts every gold item of a failed document as
exposed, so the 33-document lines charge 0.3.1 with these 2 items; the 32-document lines show the rest. English,
rules + GLiNER: the value reading agrees with the strict reading (difference -1.41 points, 95 % interval -2.17 to
-0.72), so the claim "0.4.0 exposes more" is made. No must-stay-clear item was restored or newly altered on any
set.

### Table 16. Failed documents

| Set | S-R4 | S-N4 | S-R (October) | S-N (October) | H-F (October) | H-P (October) | P (October) |
|---|---:|---:|---:|---:|---:|---:|---:|
| REF (5 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| FR-PII-Bench (300 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MAPA (19 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Max (33 documents) | 0 | 0 | 1 | 1 | 2 | 2 | 0 |
| Judilibre (200 documents) | 0 | 0 | 0 | 0 | 0 | 0 of 50 (subset) | 0 |
| English (241 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Shield 0.4.0: 798 of 798 documents processed in each mode, and no output falls under the retention rule. S-R and
S-N on Max: the workbook (no output). H-F and H-P on Max: 2 documents each under the retention rule (notes on
Table 1). The 30 % cut lines of Table 1 are a sensitivity reading and are not counted here.

### Table 17. Speed and memory of the Shield 0.4.0 session, next to the October values (VM profile A, not a laptop)

One task = one 10-page REF file, as Table 7. Shield 0.4.0: 10 values per row (the 5 REF tasks of the accuracy run
and the 5 tasks of the first speed process), session of 2026-11-11. The other rows are the October rows of Tables 7
and 9. REF is not held-out for Shield 0.4.0 (Table 11).

| Row | Session | n | Median (s) | Range (s) | s per page | Cold start (s) | Peak memory, REF | Peak memory, up to, over the sets |
|---|---|---:|---:|---|---:|---|---|---|
| S-R4, Shield 0.4.0 rules | 2026-11-11 | 10 | 0.585 | 0.498 to 0.694 | 0.0585 | 0.35 to 0.37 | 74 to 75 MB | 217 MB (FR-PII-Bench) |
| S-N4, Shield 0.4.0 rules + GLiNER | 2026-11-11 | 10 | 17.43 | 16.48 to 17.95 | 1.74 | 13.47 to 13.65 | 3,791 to 3,803 MB | 6,498 MB (Max) |
| S-R, Shield 0.3.1 rules | 2026-10-25 | 10 | 0.75 | 0.66 to 0.87 | 0.075 | 0.42 to 0.44 | 74 to 75 MB | 216 MB (FR-PII-Bench) |
| S-N, Shield 0.3.1 rules + GLiNER | 2026-10-25 | 10 | 23.26 | 20.34 to 28.28 | 2.33 | 17.38 to 17.48 | 3,721 to 3,771 MB | 6,129 MB (Max) |
| P, Presidio 2.2.364 | 2026-10-25 | 10 | 1.59 | 1.58 to 2.12 | 0.16 | 8.18 to 8.24 | 565 to 566 MB | 817 MB (MAPA) |
| H-F, from the click | October 2026 | 10 | 26.93 | 23.08 to 31.69 | 2.69 | ready between 6.3 and 15.5 | 1,640 to 1,737 MB | REF only sampled |
| H-F, from the start mark | October 2026 | 10 | 30.10 | 26.66 to 36.94 | 3.01 | same | same | same |
| H-P, from the click (partial) | October 2026 | 8 | 540.28 | 417.77 to 632.34 | 54.0 | ready between 5.4 and 13.7 | 3,752 to 5,436 MB together | REF only sampled |

Speed claims for the 0.4.0 rows (rule 11.3: every value of one row below every value of the other; addendum 4,
section 20.6, for values of different sessions):

| Pair | Result |
|---|---|
| S-R4 against S-N4 (same session) | **S-R4 faster**: 0.50 to 0.69 s against 16.48 to 17.95 s |
| "S-R faster than H-F" (Table 7), read again for S-R4 | **still holds for 0.4.0, measured in another session**: S-R4 0.50 to 0.69 s (2026-11-11) against H-F 23.08 s or more from the click and 26.66 s or more from the start mark (October) |
| "S-R faster than P" (Table 7), read again for S-R4 | **still holds for 0.4.0, measured in another session**: S-R4 0.50 to 0.69 s against P 1.58 to 2.12 s (2026-10-25) |
| "Presidio faster than S-N" (Table 7), read again for S-N4 | **still holds for 0.4.0, measured in another session**: P 1.58 to 2.12 s (2026-10-25) against S-N4 16.48 to 17.95 s (2026-11-11) |
| S-N4 against H-F | No claim. Table 7 has no claim for S-N against H-F, and no new claim in favour of a 0.4.0 row is opened across sessions. Values side by side: S-N4 16.48 to 17.95 s (2026-11-11); H-F 23.08 to 31.69 s from the click, 26.66 to 36.94 s from the start mark (October) |
| S-R4 and S-N4 against H-P | No claim: the Precis speed session of October is partial (3 of 5 tasks, D22) |
| Shield 0.4.0 against Shield 0.3.1 | **No claim**, in either direction. Values side by side only |

Notes. (a) The six machine facts of the VM are the same in both sessions (machine type, processor, cores, memory,
Windows build, power plan). (b) Known differences between the sessions: 16 days apart; the VM was stopped and
started in between and may sit on another host; on 2026-10-25 Hexagone was idle in the background and about 9.0 GB
of memory was free, on 2026-11-11 no Hexagone process ran and about 12.2 GB was free. Less background load helps
the 0.4.0 timings. No control run of 0.3.1 was made in the new session, so a difference of the VM cannot be told
apart from a difference of Shield. (c) The VM was quiet during the 0.4.0 session: no other work ran, and the
processor load before each timed REF process was 4 % or less. (d) Where the data goes: Shield 0.4.0 processed
everything on the VM, with 0 outbound connection attempts in the 20 processes of the session (12 accuracy runs, 6
speed processes, 2 pilot processes), by our own process guard. (e) On Max, S-N4 holds 6.5 GB at its peak; on a
machine with 8 GB this may run short. Profile B and the AVX2-only variant were not run for 0.4.0.

## Ajout du 13 novembre 2026 / Addition of 13 November 2026: word-level precision, recall and F1 (deviation D31)

**Français.** Cette section est ajoutée le 13 novembre 2026, sur décision de Hadi (écart D31). Elle ne change aucun
autre chiffre de ce fichier. La Table 18 donne la précision, le rappel et le F1 par mot de Shield 0.4.0 (règles et
GLiNER), Hexagone 0.3.9 (Rapide et Précis) et Presidio 2.2.364, sur les quatre jeux qui donnent un F1 : REF,
FR-PII-Bench, MAPA et Max.

- Lecture exploratoire, par mot. Elle a été définie après les essais (section 18 du protocole, dans l'addendum 2,
  interne ; addendum 4, section 20.10). Elle est donnée pour information, sans test et sans affirmation. Elle n'entre
  dans aucune règle de lecture (section 11.3).
- Rappel : part des mots à changer que l'outil a changés. Précision : part des mots changés par l'outil qui devaient
  l'être. F1 : moyenne harmonique de la précision et du rappel ; il est haut seulement quand les deux sont hauts.
  Plus haut = mieux pour les trois.
- La précision compte comme une erreur chaque mot changé qui n'est pas sur la liste de référence, termes juridiques
  compris.
- Sur MAPA et Max, la précision est une limite basse : la vraie valeur peut être plus haute.
- Judilibre et l'anglais donnent le rappel seulement, sans F1. Ils ne sont pas dans la Table 18.
- Shield 0.4.0 a été construit après les premiers résultats de cet essai : aucun jeu n'est tenu à l'écart pour lui. La
  colonne « Status » donne le statut du jeu pour chaque ligne. Hexagone et Presidio ont été mesurés en octobre 2026 et
  n'ont pas été relancés.
- Shield 0.3.1 : ses valeurs par mot ne sont pas publiées. La Table 15 montre où la sortie de Shield 0.4.0 est
  identique à celle de Shield 0.3.1.
- Tonic : mesuré en interne, non publié (conditions de Tonic).

**English.** This section was added on 13 November 2026, by Hadi's decision (deviation D31). It changes no other
number of this file. Table 18 gives the word-level precision, recall and F1 of Shield 0.4.0 (rules and GLiNER),
Hexagone 0.3.9 (Fast and Precis) and Presidio 2.2.364, on the four sets that give an F1: REF, FR-PII-Bench, MAPA and
Max.

- An exploratory reading, by word. It was defined after the runs (protocol section 18, in addendum 2, internal;
  addendum 4, section 20.10). It is for information only: no test and no claim. It is not part of any reading rule
  (section 11.3).
- Recall: of the words that must change, the share that the tool changed. Precision: of the words that the tool
  changed, the share that had to change. F1: the harmonic mean of precision and recall; it is high only when both are
  high. Higher is better for all three.
- Precision counts as an error every changed word that is not on the reference list, legal terms included.
- On MAPA and Max, precision is a lower limit: the true value can be higher.
- Judilibre and English give recall only, no F1. They are not in Table 18.
- Shield 0.4.0 was built after the first results of this comparison: no set is held-out for it. The "Status" column
  gives the status of the set for each line. Hexagone and Presidio were measured in October 2026 and were not run
  again.
- Shield 0.3.1: its word-level values are not published. Table 15 shows where the output of Shield 0.4.0 is identical
  to that of Shield 0.3.1.
- Tonic: measured internally, not published (Tonic's terms).

### Table 18. Word-level precision, recall and F1 of the public rows (exploratory, defined after the runs; higher is better; no claim)

In %, per set; no pooling over sets. The status column gives the status of the set for the row of that line. One run
per row. Shield 0.4.0: session of 2026-11-11; the other rows are the October runs.

| Set | Row | Status of the set for this row | Precision | Recall | F1 |
|---|---|---|---:|---:|---:|
| REF | S-R4, Shield 0.4.0 rules | not held-out: team-written, 0.3.1 results known; unused by record | 97.9 | 96.2 | 97.1 |
| REF | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: team-written, 0.3.1 results known; unused by record | 97.9 | 96.2 | 97.1 |
| REF | H-F, Hexagone 0.3.9 Fast | new to every other tool | 50.6 | 97.6 | 66.7 |
| REF | H-P, Hexagone 0.3.9 Precis | new to every other tool | 44.0 | 99.9 | 61.1 |
| REF | P, Presidio 2.2.364 | new to every other tool | 82.5 | 76.1 | 79.2 |
| FR-PII-Bench | S-R4, Shield 0.4.0 rules | gate | 95.0 | 98.9 | 96.9 |
| FR-PII-Bench | S-N4, Shield 0.4.0 rules + GLiNER | gate | 93.6 | 99.1 | 96.2 |
| FR-PII-Bench | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 68.4 | 98.4 | 80.7 |
| FR-PII-Bench | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 67.7 | 99.9 | 80.7 |
| FR-PII-Bench | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 69.2 | 64.1 | 66.5 |
| MAPA | S-R4, Shield 0.4.0 rules | gate | 81.8 (lower limit) | 79.1 | 80.4 |
| MAPA | S-N4, Shield 0.4.0 rules + GLiNER | gate | 77.6 (lower limit) | 87.3 | 82.2 |
| MAPA | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 28.5 (lower limit) | 95.3 | 43.8 |
| MAPA | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 23.8 (lower limit) | 93.9 | 37.9 |
| MAPA | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 51.0 (lower limit) | 84.1 | 63.5 |
| Max, 33 documents | S-R4, Shield 0.4.0 rules | gate, with a fix from this study | 95.9 (lower limit) | 94.7 | 95.3 |
| Max, 33 documents | S-N4, Shield 0.4.0 rules + GLiNER | gate, with a fix from this study | 88.5 (lower limit) | 95.3 | 91.8 |
| Max, 33 documents | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 38.1 (lower limit) | 92.4 | 54.0 |
| Max, 33 documents | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 32.7 (lower limit) | 96.2 | 48.9 |
| Max, 33 documents | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 38.0 (lower limit) | 63.0 | 47.4 |

---

## Method

### Machines

| Profile | Machine | Used for |
|---|---|---|
| A | Google Cloud VM, `n2-custom-12-16384`: 12 vCPU = 6 cores with hyper-threading, 16 GB, Intel Cascade Lake, no GPU, Windows Server 2025 Datacenter, zone europe-west1-b. It matches Hexagone's recommended row (Windows laptop 2023 or later, 16 GB, 6 cores). | every accuracy, speed and memory number of the local tools |
| B | the same VM with 4 cores and 8 GB (Hexagone's measured floor row) | planned for speed and memory; not run |
| Mac client | runs the Tonic SDK and sends the files to Tonic's cloud (D3) | Tonic only |

### Systems and settings

Settings were fixed before any run (protocol section 6). Nobody changed a setting during the runs.

| Row | System and version | Settings |
|---|---|---|
| S-R | RAGbase Shield 0.3.1 (commit `577b423`, wheel hash in `PREREG_DATA.sha256`), rules mode | product defaults; NER off |
| S-N | the same build, rules plus GLiNER on the CPU (model `fastino/gliner2-privacy-filter-PII-multi`, revision `1cb41660`) | product defaults; NER on |
| S-N2 | S-N limited to AVX2 instructions | speed rows only |
| H-F | Hexagone AI Desktop 0.3.9, Fast ("Standard") | every setting as installed; rule "Tout masquer"; replacement by substitutes; no edit in the review pane |
| H-P | Hexagone AI Desktop 0.3.9, Precis ("Analyse approfondie") | the same; Precis was offered on profile A |
| T | Tonic Textual cloud API, SDK `tonic-textual` 3.24.0 | default server, entity types and handling; no Graph Synthesis |
| P | Presidio 2.2.364 (analyzer and replacement packages), spaCy 3.8.16, `fr_core_news_md` 3.8.0 (French), `en_core_web_lg` 3.8.0 (English) | default recognizers, threshold and replacement |

Rows added on 2026-11-11 (addendum 4):

| Row | System and version | Settings |
|---|---|---|
| S-R4 | RAGbase Shield 0.4.0 (commit `fd8662d`, wheel SHA-256 `01404cd3...85b9`, frozen in `PREREG_V04.sha256`), rules mode; installed in a new folder on the same VM, with the dependency versions of the 0.3.1 rows | product defaults; NER off |
| S-N4 | the same build, rules plus GLiNER on the CPU (the same model files as row S-N) | product defaults; NER on |

The 0.4.0 rows ran with the same runner, the same 798 input files, the same readers and the same scorer as the
0.3.1 rows. Hexagone and Presidio were not run again.

Hexagone operated by Claude at Hadi's instruction (D1). Claude used the app's documented flows (folder flow, settings,
CSV and mapping exports) in a Remote Desktop session, one screenshot and one action at a time. No API, no traffic
capture, no reading of app files, models or logs. The same app and settings a person would use.

### Data

Only public benchmark data and invented documents. No client data.

| Set | Status for Shield | Files | Characters | Gold items scored (P1) | Must-stay-clear items (P2) | Source and licence |
|---|---|---:|---:|---:|---:|---|
| REF | invented (written by the Shield team, new to Shield at the freeze, not independent) | 5 (.docx) | 146,917 | 1,015 | 365 | our generator, invented French employment-litigation file, built like Hexagone's reference file; real courts, codes, articles and laws; invented precedent numbers; CC BY 4.0 |
| FR-PII-Bench v0 | informed | 300 (.txt) | 109,433 | 2,105 | 0 | `JaqueBill/fr-pii-bench`, revision `5476b0a`; CC BY 4.0 |
| MAPA, Cour de cassation | informed | 19 (.txt) | 465,252 | 1,615 | 1,344 | MAPA package on Hugging Face, revision `8b147fa`; CC BY 4.0 |
| Max (matters A to G) | informed | 33 (.docx 10, .pdf 20, .xlsx 1, .txt 2) | 173,365 | 1,003 | 144 | our invented matters; CC BY 4.0 |
| Judilibre fresh draw | held-out for every tool | 200 (.txt) | 2,308,427 | 673 (indicative) | 6,136 | `antoinejeannot/jurisprudence`, revision `8019db1`, seed 20261023, drawn and hashed before any tool read it; Licence Ouverte 2.0 |
| English (PrivacyBench v2.5 e-mail bodies) | informed | 241 (.txt) | 133,186 | 1,276 | 0 | 2 of the 21 exports, drawn with seed 20261023; CC BY 4.0 |

The column "Status for Shield" above is the status for Shield 0.3.1. For Shield 0.4.0 no set is held-out: Table 11.

Every tool got the same files, in the same order, as the same folders (one folder per set; Max: one per matter;
English: one per export).

### Scorer and claim rule

- One scorer for every tool: `score_text.py` (laptop-score-1.1), with one reader for inputs and outputs:
  `extract_text.py` (laptop-extract-1.1). It aligns the input text and the output text, then says for each gold item
  whether it is still readable at its place, and for each must-stay-clear item whether it changed. It handles every
  replacement style (codes, fake values, tags, deletion).
- Rule 8: a document fails when the tool reports a failure, writes no output, writes an unreadable output, or keeps
  less than half of the words outside the gold (documents with 20 or more such words). All its gold items then count
  as exposed.
- Claims: `compare_runs.py` 1.1, paired bootstrap over documents, 2,000 resamples, seed 20261023. A claim needs the
  whole 95 % interval on one side of 0. A P1 claim needs the strict and the value reading to agree. Speed: "faster"
  only when the ranges do not overlap.
- Freeze: the protocol, the scorer, the reader, the comparison script, the runners and the built data were hashed
  before any Hexagone, Tonic or Presidio output existed. `PREREG.sha256` v1.1 (685 files, 2026-10-24 13:49Z; SHA-256
  of the file `fc3a0d2d...6f25a`) and `PREREG_DATA.sha256` (829 files, 2026-10-24 13:42Z, before any tool read a fresh
  Judilibre decision; `6fbfa1cf...1eec`). A first freeze (v1.0, 2026-10-23) was replaced by v1.1 after a fairness
  review, before any competitor output (D2). Both freezes checked OK on 2026-10-25.
- Shield 0.4.0 rows (added 2026-11-11): the rules are in `PROTOCOL_ADDENDUM_4.md`, frozen with the 0.4.0 wheel by
  `PREREG_V04.sha256` on 2026-11-11 at 09:04 UTC, before any 0.4.0 output on these sets existed through the
  head-to-head runner. The scores of the two rows were checked by an independent recount with a counter that
  imports nothing from the frozen scripts: same P1 and P2 counts, item by item, and the same 93 comparisons. No
  correction was made after the scores were seen. All three freezes checked OK on 2026-11-11.
- Checks: two independent re-scores with a second scorer written from the protocol text (check 1, D17; check of
  step 2, D24). They read every disagreement item by item. Corrections made after the scores were seen are logged in
  D17 and D24. None changed a claim.

### Sealing (protocol section 13)

Hexagone and Tonic outputs, their exports and every per-document competitor result stay in a sealed folder. Only
aggregate counts leave it, as in this document. No Shield rule, lexicon, test or comment may use a competitor output
or a competitor's per-item result. Sessions that work on Shield's source code or tests do not open the sealed folder.
A search outside the sealed folder for competitor output strings found none (D24). Shield's own outputs are not
sealed.

### Deviations (full text in [DEVIATIONS.md](DEVIATIONS.md))

| Entry | Title |
|---|---|
| D1 | Claude operates Hexagone, at Hadi's instruction |
| D2 | Interim freeze before the protocol review finished; fairness review; re-freeze v1.1; run sheet not frozen |
| D3 | Tonic runs from the Mac with the key file |
| D4 | Fresh Judilibre draw and data addendum |
| D5 | Hexagone first-launch facts not recorded yet (closed by D9) |
| D6 | Wrong hash quotes in two operator reports |
| D7 | Shield working tree changed during the trial (the tested Shield stays the frozen 0.3.1 wheel) |
| D8 | Shield setup on the VM carried Windows patches (closed by D15) |
| D9 | Hexagone first-launch facts recorded |
| D10 | Hexagone masks output file names; name-only pairing rule; operator mechanics |
| D11 | The name rule fails on multi-file tasks; pairing by text overlap for those tasks |
| D12 | The 30 % overlap threshold drops documents the app did process; primary reading without the threshold |
| D13 | Precis input folders are byte-identical copies |
| D14 | Hexagone Precis stopped after REF and FR-PII-Bench: the Remote Desktop session was disconnected |
| D15 | Shield and Presidio runs: setup written before the runs |
| D16 | Scoring step: how the frozen scorer is fed |
| D17 | Check 1: independent re-score; corrections made after the scores were seen |
| D18 | Sealing fixes after the fairness check |
| D19 | Second Hexagone operator session: Precis resumed, late FR-PII-Bench Precis exports, click time log |
| D20 | Hexagone speed session: set-up written before the session |
| D21 | Hexagone cold start: the frame recorder was blocked by the antivirus; ready time read from screenshots |
| D22 | Hexagone Precis speed session stopped after 3 of 5 tasks: the Remote Desktop session was disconnected again |
| D23 | Scoring step 2: how the new Precis rows and the speed session are fed to the scorer |
| D24 | Check of step 2: independent re-score; text corrections made after the scores were seen |
| D25 to D27 | internal additions; they are not part of this document |
| D28 | Rows S-R4 and S-N4: Shield 0.4.0, a build made after the first results, run on profile A; the other tools not run again |
| D31 | Word-level precision, recall and F1 of the public rows on REF, FR-PII-Bench, MAPA and Max published (Table 18; exploratory, defined after the runs, no claim; added 2026-11-13) |

### Limits

| Limit | Effect |
|---|---|
| A VM is not a laptop (protocol 4.2): no power cap or heat limit, AVX-512, no hybrid cores, Windows Server 2025 instead of Windows 11, server memory, one machine | absolute times are VM times and would be longer on a business laptop; the local tools are compared on the same VM; real laptop runs are a next step |
| Lawyers' laptops run Office and a browser at the same time | not simulated |
| Informed sets | only Judilibre is held-out for Shield; REF was written by the Shield team |
| One run per tool and mode | no run-to-run spread for accuracy |
| REF has 5 documents from one template | narrow comparison intervals |
| Judilibre P1 | indicative (673 professional names found by patterns) |
| Retention rule (rule 8) | it catches broken outputs, and it also counts heavy redaction as failure |
| Hexagone operated by Claude (D1) | an AI agent drove the app, not a person; same app and settings |
| Hexagone output names are masked | pairs rebuilt from the app's own exports and processing order (D10 to D12, D17, D24) |
| Hexagone Precis on Judilibre | 50 of the 200 decisions (pre-registered subset) |
| Hexagone speed | Precis session partial (3 of 5); cold start only as ranges; no profile B; auto-update was on (version 0.3.9 at every check) |
| Hexagone traffic | not observed (its terms); "on the machine" is from its documentation |
| Tonic | internal (its terms); default SDK path, not Graph Synthesis; run from a Mac client (D3) |
| Folder condition | tools that keep one pseudonym per person across a folder may gain or lose from cross-document effects; published per-document numbers are not directly comparable |

Limits of the Shield 0.4.0 rows (added 2026-11-11):

| Limit | Effect |
|---|---|
| A second attempt | Shield 0.4.0 was built after the first results. No set is held-out for it. The rows show what the new build does on these files. They are not a confirmation on unseen data |
| November against October | Hexagone and Presidio are the October runs, with the versions of that time. Hexagone cannot be run again (its trial ended). Newer versions could score differently |
| Status by record, not by proof | for REF and for Judilibre, "not used by the 0.4.0 work" rests on the records (work logs, prompts, code scan); there is no technical barrier and no access log |
| Not blind | the 0.4.0 work had already measured the build on the documents of four of these sets with other runners |
| Max and the workbook | the reader fix came from this study; the reading on 32 documents shows Max without it |
| More comparisons | 93 more paired comparisons, with no correction for multiple comparisons; some clear differences can come from chance |
| Speed | another session, 16 days later, on a VM that was stopped and started, with less background load; no control run of 0.3.1; no profile B |
| Rules written with the first results known | the author of addendum 4 knew the October results; the choices this left open are listed in the addendum (section 20.14) |
| The wheel, not the installer | the rows measure the Shield 0.4.0 Python package with the dependency versions of the 0.3.1 rows; the desktop installers carry their own Python and packages and were not measured here |

### Links

- Protocol: [PROTOCOL.md](PROTOCOL.md) v1.0 and [PROTOCOL_ADDENDUM_1.md](PROTOCOL_ADDENDUM_1.md)
- Shield 0.4.0 rows: [PROTOCOL_ADDENDUM_4.md](PROTOCOL_ADDENDUM_4.md) (section 20)
- Earlier public version (25 October 2026): its summary and Tables 1 to 10 are repeated word for word in this file
- Deviations: [DEVIATIONS.md](DEVIATIONS.md)
- Vendor sources: hexagone.ai/fr/system-requirements, hexagone.ai/fr/research/privacy-bench,
  huggingface.co/datasets/TonicAI/Privacy-Bench (all read 2026-10-23)
