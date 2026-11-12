"""Build the synthetic French legal corpus used by the engine tests and the bench.

Every person, company, address and number in these documents is invented. Identifiers with a
check digit (SIREN, SIRET, NIR, IBAN, VAT, card, LEI, ISIN) are generated here so that they are
valid, from a fixed seed. Phone numbers use the ARCEP ranges reserved for fiction.

Markup in the templates:

- ``[[KIND:id|text]]``: a mention that must be masked. ``id`` groups the mentions of one entity.
- ``((text))``: text that must stay in clear (courts, institutions, laws, ordinary words).

Run ``python tests/fixtures/build_fixtures.py`` to rewrite ``tests/fixtures/docs/``. The output is
committed; the tests check that it is up to date.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from ragbase_shield.engine.detectors import (  # noqa: E402
    iban_check_digits,
    luhn_check_digit,
    nir_key,
    vat_fr_key,
)

OUT = HERE / "docs"
RNG = random.Random(20261016)


# ---------------------------------------------------------------------------
# Valid synthetic identifiers
# ---------------------------------------------------------------------------


def _digits(n: int) -> str:
    return "".join(RNG.choice("0123456789") for _ in range(n))


def make_siren() -> str:
    body = str(RNG.randint(1, 9)) + _digits(7)
    return body + luhn_check_digit(body)


def make_siret(siren: str) -> str:
    nic = "000" + _digits(1)
    return siren + nic + luhn_check_digit(siren + nic)


def make_vat(siren: str) -> str:
    return f"FR{vat_fr_key(siren):02d}{siren}"


def rib_key(bank: str, branch: str, account: str) -> str:
    table = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "12345678912345678923456789")
    b, g, a = (int(x.translate(table)) for x in (bank, branch, account))
    return f"{97 - (89 * b + 15 * g + 3 * a) % 97:02d}"


def make_iban_fr() -> str:
    bank, branch, account = _digits(5), _digits(5), _digits(11)
    bban = bank + branch + account + rib_key(bank, branch, account)
    return "FR" + iban_check_digits("FR", bban) + bban


def make_iban_de() -> str:
    bban = _digits(8) + _digits(10)
    return "DE" + iban_check_digits("DE", bban) + bban


def make_nir(sex: str, yy: str, mm: str, dept: str, commune: str, order: str) -> str:
    body = sex + yy + mm + dept + commune + order
    return body + f"{nir_key(body):02d}"


def make_card(prefix: str = "4970") -> str:
    body = prefix + _digits(15 - len(prefix))
    return body + luhn_check_digit(body)


def make_lei() -> str:
    alnum = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    body = "969500" + "".join(RNG.choice(alnum) for _ in range(12))
    n = int("".join(str(int(c, 36)) for c in body + "00"))
    return body + f"{98 - n % 97:02d}"


def make_isin() -> str:
    body = "FR0014" + _digits(5)
    expanded = "".join(str(int(c, 36)) for c in body)
    return body + luhn_check_digit(expanded)


def group(s: str, size: int = 4) -> str:
    return " ".join(s[i:i + size] for i in range(0, len(s), size))


def siren_sp(s: str) -> str:
    return f"{s[:3]} {s[3:6]} {s[6:9]}"


def siret_sp(s: str) -> str:
    return f"{s[:3]} {s[3:6]} {s[6:9]} {s[9:]}"


def nir_sp(s: str) -> str:
    return f"{s[0]} {s[1:3]} {s[3:5]} {s[5:7]} {s[7:10]} {s[10:13]} {s[13:]}"


def make_luhn_amount() -> str:
    while True:
        body = str(RNG.randint(1, 9)) + _digits(7)
        cand = body + luhn_check_digit(body)
        if cand[0] != "0":
            return f"{cand[:3]} {cand[3:6]} {cand[6:]}"


IDS: dict[str, str] = {}
for _org in ("brivanor", "quantorive", "kervalon", "tilleuls"):
    IDS[f"{_org}_siren"] = make_siren()
    IDS[f"{_org}_siret"] = make_siret(IDS[f"{_org}_siren"])
    IDS[f"{_org}_vat"] = make_vat(IDS[f"{_org}_siren"])
    IDS[f"{_org}_siren_sp"] = siren_sp(IDS[f"{_org}_siren"])
    IDS[f"{_org}_siret_sp"] = siret_sp(IDS[f"{_org}_siret"])
IDS["vasseur_iban"] = make_iban_fr()
IDS["vasseur_iban_sp"] = group(IDS["vasseur_iban"])
IDS["ravel_iban"] = make_iban_fr()
IDS["ravel_iban_sp"] = group(IDS["ravel_iban"])
IDS["tilleuls_iban"] = make_iban_fr()
IDS["tilleuls_iban_sp"] = group(IDS["tilleuls_iban"])
IDS["de_iban_sp"] = group(make_iban_de())
IDS["ravel_nir"] = make_nir("1", "88", "09", "69", "266", "123")
IDS["ravel_nir_sp"] = nir_sp(IDS["ravel_nir"])
IDS["haddad_nir"] = make_nir("2", "90", "07", "69", "383", "045")
IDS["santoni_nir"] = make_nir("1", "75", "04", "2A", "004", "087")
IDS["santoni_nir_sp"] = nir_sp(IDS["santoni_nir"])
IDS["card"] = group(make_card())
IDS["quantorive_lei"] = make_lei()
IDS["quantorive_isin"] = make_isin()
IDS["capital_amount"] = make_luhn_amount()
IDS["torvane_siren"] = make_siren()  # generated last: the identifiers above keep their values


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

DOCS: list[dict] = []

DOCS.append({
    "name": "01_assignation",
    "type": "assignation",
    "title": "Brivanor Logistique SAS c. Vasseur-Garnier",
    "parties": [
        {"id": "o_brivanor", "kind": "ORG", "value": "Brivanor Logistique SAS"},
        {"id": "p_vasseur", "kind": "PERSON", "value": "Hélène Vasseur-Garnier"},
        {"id": "p_delacourt", "kind": "PERSON", "value": "Jean-Pierre Delacourt"},
    ],
    "text": """ASSIGNATION DEVANT LE ((TRIBUNAL JUDICIAIRE DE LYON))

L'AN DEUX MILLE VINGT-SIX ET LE DOUZE MARS

À LA REQUÊTE DE :

La société [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] SAS, société par actions simplifiée au capital de 150 000 euros, immatriculée au ((RCS)) de Lyon sous le numéro [[SIREN:s1|{brivanor_siren_sp}]], dont le siège social est situé [[ADDRESS:a1|18 rue Victor Lagrange, 69007 Lyon]], représentée par son Président en exercice, Monsieur [[PERSON:p_delacourt|Jean-Pierre DELACOURT]], domicilié en cette qualité audit siège,

Ayant pour avocat Maître [[PERSON:p_lervignac|Sophie LERVIGNAC]], avocat au ((barreau de Lyon)), [[ORG:o_lervignac|LERVIGNAC AVOCATS]] SELARL, [[ADDRESS:a2|5 place Bellecour, 69002 Lyon]], tél. [[PHONE:t1|04 65 71 20 14]], courriel [[EMAIL:e1|s.lervignac@lervignac-avocats.fr]],

J'ai, [[PERSON:p_marchal|Étienne Marchal]], commissaire de justice associé, soussigné,

DONNÉ ASSIGNATION À :

Madame [[PERSON:p_vasseur|Hélène VASSEUR-GARNIER]], née le [[BIRTHDATE:b1|3 mai 1975]] à Mâcon (71), de nationalité française, demeurant [[ADDRESS:a3|4 allée des Peupliers, 71000 Mâcon]],

D'AVOIR À COMPARAÎTRE devant le ((Tribunal judiciaire de Lyon)), audience d'orientation du jeudi 4 juin 2026 à 9 heures.

EXPOSÉ DES FAITS

Par contrat du 2 février 2024, la société [[ORG:o_brivanor|Brivanor Logistique]] a confié à Mme [[PERSON:p_vasseur|Vasseur-Garnier]] une mission de conseil en organisation de ses entrepôts. Un acompte de 24 500 euros a été versé le 9 février 2024 sur le compte [[IBAN:i1|{vasseur_iban_sp}]] désigné par la défenderesse.

Aucune prestation n'a été exécutée. Malgré une mise en demeure du 15 novembre 2025, Mme [[PERSON:p_vasseur|VASSEUR-GARNIER]] n'a pas restitué l'acompte.

DISCUSSION

Sur le fondement des ((articles 1217 et 1231-1 du Code civil)), la société [[ORG:o_brivanor|Brivanor]] est fondée à solliciter la résolution du contrat et la restitution des sommes versées.

PAR CES MOTIFS

Il est demandé au ((Tribunal judiciaire de Lyon)) de :
- prononcer la résolution du contrat du 2 février 2024 ;
- condamner Mme [[PERSON:p_vasseur|Hélène Vasseur-Garnier]] à payer à la société [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] la somme de 24 500 euros ;
- la condamner au paiement de 3 000 euros au titre de l'((article 700 du Code de procédure civile)).

Sous toutes réserves.

Pièces communiquées :
1. Contrat du 2 février 2024
2. Mise en demeure du 15 novembre 2025
3. Extrait Kbis de la société [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] (SIRET [[SIRET:s2|{brivanor_siret_sp}]])
""",
})

DOCS.append({
    "name": "02_conclusions_appel",
    "type": "conclusions",
    "title": "Benali c. Quantorive SA",
    "parties": [
        {"id": "p_benali", "kind": "PERSON", "value": "Karim Benali"},
        {"id": "o_quantorive", "kind": "ORG", "value": "Quantorive SA"},
    ],
    "text": """((COUR D'APPEL DE LYON))
((Chambre sociale)) A

RG n° [[CASE_REF:r1|24/03187]] - N° Portalis [[CASE_REF:r2|DBVX-V-B7I-PQ3R]]

CONCLUSIONS D'APPELANT N° 2

POUR :

Monsieur [[PERSON:p_benali|Karim BENALI]], né le [[BIRTHDATE:b1|17/11/1984]] à Vénissieux (69), demeurant [[ADDRESS:a1|27 rue Paul Bert, 69003 Lyon]],

Appelant, ayant pour avocat Maître [[PERSON:p_morvillier|Gaëtan MORVILLIER]], avocat au ((barreau de Lyon)), [[EMAIL:e1|contact@morvillier-avocat.fr]]

CONTRE :

La société [[ORG:o_quantorive|QUANTORIVE]] SA, au capital de (({capital_amount} euros)), immatriculée au ((RCS)) de Lyon sous le n° [[SIREN:s1|{quantorive_siren_sp}]], prise en la personne de ses représentants légaux,

Intimée, ayant pour avocat Maître [[PERSON:p_lervignac|Sophie LERVIGNAC]], avocat au ((barreau de Lyon))

PLAISE À LA COUR

I. FAITS ET PROCÉDURE

M. [[PERSON:p_benali|Benali]] a été engagé par la société [[ORG:o_quantorive|Quantorive]] le 3 janvier 2017 en qualité de responsable logistique, moyennant un salaire brut mensuel de 3 412,50 euros.

Le 12 septembre 2022, [[PERSON:p_benali|BENALI]] a été convoqué à un entretien préalable. Il a été licencié pour faute grave par lettre du 4 octobre 2022.

Par jugement du 7 mars 2024, le ((conseil de prud'hommes de Lyon)) a débouté M. [[PERSON:p_benali|Karim Benali]] de l'ensemble de ses demandes. Il a interjeté appel le 2 avril 2024.

II. DISCUSSION

Selon une jurisprudence constante, la faute grave est celle qui rend impossible le maintien du salarié dans l'entreprise (cf. ((Cass. soc.)), 14 février 2024, pourvoi n° [[CASE_REF:r3|22-18.734]] ; [[CASE_REF:r4|ECLI:FR:CCASS:2024:SO00187]]).

En l'espèce, la société [[ORG:o_quantorive|QUANTORIVE]] ne rapporte pas la preuve des griefs. Le licenciement est dépourvu de ((cause réelle et sérieuse)) au sens de l'((article L1235-3 du Code du travail)).

M. [[PERSON:p_benali|Benali]] est resté inscrit à ((France Travail)) jusqu'au mois de mai 2023.

PAR CES MOTIFS

Infirmer le jugement ; condamner la société [[ORG:o_quantorive|Quantorive]] à payer à M. [[PERSON:p_benali|BENALI]] la somme de 41 000 euros à titre de dommages et intérêts.

Fait à Lyon, le 30 septembre 2026
Maître [[PERSON:p_morvillier|Gaëtan MORVILLIER]]
""",
})

DOCS.append({
    "name": "03_contrat_travail",
    "type": "contrat",
    "title": "Kervalon Conseil - contrat Ravel",
    "parties": [
        {"id": "o_kervalon", "kind": "ORG", "value": "Kervalon Conseil SARL"},
        {"id": "p_ravel", "kind": "PERSON", "value": "Thomas Ravel"},
    ],
    "text": """CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE

ENTRE LES SOUSSIGNÉS :

La société [[ORG:o_kervalon|KERVALON CONSEIL]] SARL, au capital de 20 000 euros, dont le siège social est situé [[ADDRESS:a1|9 cours Lafayette, 69006 Lyon]], immatriculée au ((RCS)) de Lyon sous le numéro [[SIREN:s1|{kervalon_siren_sp}]], SIRET [[SIRET:s2|{kervalon_siret}]], numéro de TVA intracommunautaire [[VAT:v1|{kervalon_vat}]], représentée par Madame [[PERSON:p_fontanel|Claire FONTANEL]], en sa qualité de gérante,

Ci-après dénommée « la Société »,

ET

Monsieur [[PERSON:p_ravel|Thomas RAVEL]], né le [[BIRTHDATE:b1|14/09/1988]] à Villeurbanne (69), de nationalité française, numéro de sécurité sociale [[NIR:n1|{ravel_nir_sp}]], demeurant [[ADDRESS:a2|112 avenue Félix Faure, 69003 Lyon]], téléphone [[PHONE:t1|06 39 98 27 51]], adresse électronique [[EMAIL:e1|thomas.ravel@exemple-mail.fr]],

Ci-après dénommé « le Salarié »,

IL A ÉTÉ CONVENU CE QUI SUIT :

Article 1 - Engagement

La Société engage le Salarié à compter du 1er décembre 2026, sous réserve des résultats de la visite d'information et de prévention. Le présent contrat est régi par la ((convention collective nationale)) des bureaux d'études techniques, dite ((Syntec)).

Article 2 - Fonctions

M. [[PERSON:p_ravel|Ravel]] exercera les fonctions de consultant senior, statut cadre. Il sera placé sous l'autorité de Mme [[PERSON:p_fontanel|Fontanel]].

Article 3 - Période d'essai

Le contrat ne deviendra définitif qu'à l'issue d'une période d'essai de quatre mois, conformément à l'((article L1221-19 du Code du travail)).

Article 4 - Rémunération

Le Salarié percevra une rémunération annuelle brute de 52 000 euros, versée en douze mensualités sur le compte [[IBAN:i1|{ravel_iban_sp}]] ouvert au nom de M. [[PERSON:p_ravel|Thomas Ravel]] à la Banque [[ORG:o_arvoria|Arvoria]].

Article 5 - Durée du travail

La durée du travail est fixée selon une convention de forfait en jours de 218 jours par an.

Fait à Lyon, le 6 novembre 2026, en deux exemplaires.

Pour la Société, [[PERSON:p_fontanel|Claire Fontanel]], gérante          Le Salarié, [[PERSON:p_ravel|Thomas Ravel]]
((Lu et approuvé))
""",
})

DOCS.append({
    "name": "04_jugement_cph",
    "type": "jugement",
    "title": "Haddad c. Brivanor Logistique SAS",
    "parties": [
        {"id": "p_haddad", "kind": "PERSON", "value": "Nadia Haddad"},
        {"id": "o_brivanor", "kind": "ORG", "value": "Brivanor Logistique SAS"},
    ],
    "text": """((CONSEIL DE PRUD'HOMMES DE LYON))
((Section Commerce))

RG N° [[CASE_REF:r1|23/01456]] - N° Portalis [[CASE_REF:r2|35L7-X-B7H-CQ4M]]

JUGEMENT DU 18 SEPTEMBRE 2026

Composition du bureau de jugement lors des débats et du délibéré :
M. [[PERSON:p_vannier|Rodolphe VANNIER]], Président, conseiller employeur
Mme [[PERSON:p_tissandier|Agnès TISSANDIER]], conseiller salarié
Assistés de Mme [[PERSON:p_bourdaret|Inès BOURDARET]], greffière

ENTRE :

Madame [[PERSON:p_haddad|Nadia HADDAD]], née le [[BIRTHDATE:b1|22 juillet 1990]] à Lyon, demeurant [[ADDRESS:a1|7 impasse des Glycines, 69100 Villeurbanne]]
Représentée par Maître [[PERSON:p_morvillier|Gaëtan MORVILLIER]], avocat au ((barreau de Lyon))
DEMANDERESSE

ET :

SAS [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]], SIRET [[SIRET:s1|{brivanor_siret}]], [[ADDRESS:a2|18 rue Victor Lagrange, 69007 Lyon]]
Représentée par Maître [[PERSON:p_lervignac|Sophie LERVIGNAC]], avocat au ((barreau de Lyon))
DÉFENDERESSE

EXPOSÉ DU LITIGE

Mme [[PERSON:p_haddad|HADDAD]] a été engagée par la société [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] à compter du 6 mars 2019 en qualité de préparatrice de commandes. Elle a fait l'objet d'un licenciement pour inaptitude le 14 février 2023.

Elle soutient que l'employeur a manqué à son obligation de reclassement. La société [[ORG:o_brivanor|Brivanor]] conclut au rejet des demandes.

MOTIFS DE LA DÉCISION

((Attendu que)) l'employeur ne justifie d'aucune recherche de reclassement au sein du groupe ; qu'il convient de dire le licenciement sans ((cause réelle et sérieuse)) ;

Que Mme [[PERSON:p_haddad|Nadia Haddad]] justifie de son inscription à ((France Travail)) et de la perception d'indemnités versées par ((Pôle emploi)) puis par l'((Unédic)) ;

PAR CES MOTIFS

Le Conseil, statuant publiquement, par jugement contradictoire et en premier ressort :

DIT le licenciement de Mme [[PERSON:p_haddad|Nadia HADDAD]] dépourvu de cause réelle et sérieuse ;
CONDAMNE la SAS [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] à lui payer la somme de 18 600 euros en application de l'((article L1235-3 du Code du travail)) ;
ORDONNE le remboursement par l'employeur à ((France Travail)) des indemnités de chômage versées dans la limite de trois mois ;
CONDAMNE la défenderesse aux dépens.

La Greffière                                  Le Président
[[PERSON:p_bourdaret|I. BOURDARET]]                                  [[PERSON:p_vannier|R. VANNIER]]
""",
})

DOCS.append({
    "name": "05_echange_emails",
    "type": "emails",
    "title": "Haddad c. Brivanor - correspondance client",
    "parties": [
        {"id": "o_brivanor", "kind": "ORG", "value": "Brivanor Logistique SAS"},
        {"id": "p_delacourt", "kind": "PERSON", "value": "Jean-Pierre Delacourt"},
        {"id": "p_haddad", "kind": "PERSON", "value": "Nadia Haddad"},
    ],
    "text": """De : [[PERSON:p_lervignac|Sophie Lervignac]] <[[EMAIL:e1|s.lervignac@lervignac-avocats.fr]]>
Envoyé : lundi 21 septembre 2026 18:42
À : [[PERSON:p_delacourt|Jean-Pierre Delacourt]] <[[EMAIL:e2|jp.delacourt@brivanor-logistique.fr]]>
Objet : Dossier [[PERSON:p_haddad|Haddad]] c/ [[ORG:o_brivanor|Brivanor]] - jugement du 18 septembre

Bonjour [[PERSON:p_delacourt|Jean-Pierre]],

Le ((conseil de prud'hommes de Lyon)) a rendu son jugement dans l'affaire RG [[CASE_REF:r1|23/01456]]. La société est condamnée à verser 18 600 euros à Mme [[PERSON:p_haddad|Haddad]].

Nous avons un mois pour interjeter appel devant la ((cour d'appel de Lyon)). Le texte de l'((article L1235-3)) est disponible sur ((https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000035644154)).

Nos réf. : [[CASE_REF:r2|SL/2023/0456]]

Bien cordialement,
[[PERSON:p_lervignac|Sophie Lervignac]]
Avocate associée
[[ORG:o_lervignac|LERVIGNAC AVOCATS]] - [[ADDRESS:a1|5 place Bellecour, 69002 Lyon]]
Tél. : [[PHONE:t1|04 65 71 20 14]] - Mob. : [[PHONE:t2|+33 6 39 98 45 12]]
[[URL:u1|www.lervignac-avocats.fr]]

-----

De : [[PERSON:p_delacourt|Jean-Pierre Delacourt]] <[[EMAIL:e2|jp.delacourt@brivanor-logistique.fr]]>
Envoyé : mardi 22 septembre 2026 08:15
À : [[PERSON:p_lervignac|Sophie Lervignac]] <[[EMAIL:e1|s.lervignac@lervignac-avocats.fr]]>
Cc : [[PERSON:p_belkacem|Yasmine Belkacem]] <[[EMAIL:e3|y.belkacem@brivanor-logistique.fr]]>

Bonjour Maître,

Merci. Nous souhaitons faire appel. [[PERSON:p_belkacem|Yasmine]], notre DRH, vous transmettra le dossier de Mme [[PERSON:p_haddad|Haddad]] et l'historique de ses arrêts.

Pour régler votre provision, vous pouvez débiter la carte de l'entreprise n° [[CARD:c1|{card}]] (expiration 09/28). Notre portail fournisseur a enregistré votre dernière connexion depuis l'adresse IP [[ID_CODE:ip1|192.0.2.44]].

Cordialement,
[[PERSON:p_delacourt|Jean-Pierre]]
[[ORG:o_brivanor|Brivanor Logistique]] - [[PHONE:t3|01 99 00 31 87]]
""",
})

DOCS.append({
    "name": "06_extrait_kbis",
    "type": "kbis",
    "title": "Quantorive SA",
    "parties": [
        {"id": "o_quantorive", "kind": "ORG", "value": "Quantorive SA"},
        {"id": "p_ferrandou", "kind": "PERSON", "value": "Lucien Ferrandou"},
        {"id": "p_belkacem", "kind": "PERSON", "value": "Yasmine Belkacem"},
    ],
    "text": """((Greffe du Tribunal de commerce de Lyon))

EXTRAIT D'IMMATRICULATION PRINCIPALE AU ((REGISTRE DU COMMERCE ET DES SOCIÉTÉS))
à jour au 3 octobre 2026

IDENTIFICATION DE LA PERSONNE MORALE

Immatriculation au RCS, numéro : [[SIREN:s1|{quantorive_siren_sp}]] R.C.S. Lyon
Date d'immatriculation : 14/03/2011
Dénomination ou raison sociale : [[ORG:o_quantorive|QUANTORIVE]]
Forme juridique : Société anonyme à conseil d'administration
Capital social : 1 250 000,00 Euros
Adresse du siège : [[ADDRESS:a1|27 avenue Jean Jaurès, 69007 Lyon]]
Activités principales : conseil en organisation logistique et transport
Numéro de TVA intracommunautaire : [[VAT:v1|{quantorive_vat}]]
Identifiant LEI : [[ID_CODE:l1|{quantorive_lei}]]
Code ISIN des actions : [[ID_CODE:l2|{quantorive_isin}]]

GESTION, DIRECTION, ADMINISTRATION, CONTRÔLE, ASSOCIÉS OU MEMBRES

Président du conseil d'administration
Nom, prénoms : [[PERSON:p_ferrandou|FERRANDOU Lucien Marcel]]
Date et lieu de naissance : Le [[BIRTHDATE:b1|11 février 1962]] à Clermont-Ferrand (63)
Nationalité : Française
Domicile personnel : [[ADDRESS:a2|9 chemin des Vignes, 69890 La Tour-de-Salvagny]]

Directeur général
Nom, prénoms : [[PERSON:p_belkacem|BELKACEM Yasmine]]
Date et lieu de naissance : Le [[BIRTHDATE:b2|2 août 1979]] à Saint-Étienne (42)
Nationalité : Française
Domicile personnel : [[ADDRESS:a3|31 boulevard des Belges, 69006 Lyon]]

Commissaire aux comptes titulaire
Dénomination : [[ORG:o_auditia|AUDITIA RHÔNE]]
Forme juridique : Société par actions simplifiée

RENSEIGNEMENTS RELATIFS À L'ACTIVITÉ ET À L'ÉTABLISSEMENT PRINCIPAL

Adresse de l'établissement : [[ADDRESS:a1|27 avenue Jean Jaurès, 69007 Lyon]]
SIRET : [[SIRET:s2|{quantorive_siret_sp}]]
Origine du fonds : Création
Mode d'exploitation : Exploitation directe

Le Greffier
""",
})

DOCS.append({
    "name": "07_pv_assemblee",
    "type": "pv_ag",
    "title": "SCI Les Tilleuls de Saône",
    "parties": [
        {"id": "o_tilleuls", "kind": "ORG", "value": "SCI Les Tilleuls de Saône"},
        {"id": "p_quere", "kind": "PERSON", "value": "Mathilde Quéré-Lansac"},
        {"id": "p_martin", "kind": "PERSON", "value": "Louise Martin"},
        {"id": "p_blanc", "kind": "PERSON", "value": "Paul Blanc"},
    ],
    "text": """SCI [[ORG:o_tilleuls|LES TILLEULS DE SAÔNE]]
Société civile immobilière au capital de 1 000 euros
Siège social : [[ADDRESS:a1|3 quai des Marans, 71000 Mâcon]]
[[SIREN:s1|{tilleuls_siren_sp}]] ((RCS)) Mâcon

PROCÈS-VERBAL DE L'ASSEMBLÉE GÉNÉRALE EXTRAORDINAIRE DU 18 JUIN 2026

L'an deux mille vingt-six, le dix-huit juin, à quatorze heures, les associés de la société civile immobilière [[ORG:o_tilleuls|Les Tilleuls de Saône]] se sont réunis au siège social, sur convocation de la gérante, Mme [[PERSON:p_quere|Mathilde QUÉRÉ-LANSAC]].

Sont présents :
- Mme [[PERSON:p_quere|Mathilde QUÉRÉ-LANSAC]], titulaire de 500 parts ;
- Mme [[PERSON:p_martin|Louise MARTIN]], titulaire de 300 parts ;
- M. [[PERSON:p_blanc|Paul BLANC]], titulaire de 200 parts.

Mme [[PERSON:p_quere|Quéré-Lansac]] préside la séance. M. [[PERSON:p_blanc|Blanc]] est désigné secrétaire. L'assemblée réunit la totalité des parts et peut valablement délibérer, la date ayant été fixée d'un commun accord ((le 11 novembre, jour de la Saint-Martin)).

PREMIÈRE RÉSOLUTION - Agrément d'une cession de parts

L'assemblée agrée la cession de 100 parts par Mme [[PERSON:p_martin|Martin]] au profit de la société [[ORG:o_kervalon|KERVALON CONSEIL]] SARL, moyennant le prix de 45 000 euros payable par virement sur le compte de la SCI [[IBAN:i1|{tilleuls_iban_sp}]].
Cette résolution est adoptée à l'unanimité.

DEUXIÈME RÉSOLUTION - Véhicule de la société

L'assemblée autorise la gérante à céder le véhicule utilitaire immatriculé [[ID_CODE:p1|GH-482-KT]]. Aucun ((chèque en blanc)) ne sera remis à l'acquéreur.
Cette résolution est adoptée à l'unanimité.

TROISIÈME RÉSOLUTION - Pouvoirs

Tous pouvoirs sont donnés au porteur d'une copie du présent procès-verbal pour accomplir les formalités auprès du ((greffe du Tribunal de commerce de Mâcon)).

La présidente de séance                    Le secrétaire
M. [[PERSON:p_quere|QUÉRÉ-LANSAC]]                           [[PERSON:p_blanc|P. BLANC]]
""",
})

DOCS.append({
    "name": "08_mise_en_demeure",
    "type": "lettre",
    "title": "SCI Les Tilleuls de Saône c. de Montclar",
    "parties": [
        {"id": "o_tilleuls", "kind": "ORG", "value": "SCI Les Tilleuls de Saône"},
        {"id": "p_montclar", "kind": "PERSON", "value": "Arnaud de Montclar"},
    ],
    "text": """[[ORG:o_lervignac|LERVIGNAC AVOCATS]] SELARL
[[ADDRESS:a1|5 place Bellecour, 69002 Lyon]]
Tél. [[PHONE:t1|04 65 71 20 14]]

LETTRE RECOMMANDÉE AVEC ACCUSÉ DE RÉCEPTION

Monsieur [[PERSON:p_montclar|Arnaud de MONTCLAR]]
[[ADDRESS:a2|Résidence Les Charmilles, Bât. C
21 boulevard des Belges
69006 LYON]]

Lyon, le 6 octobre 2026

Nos réf. : [[CASE_REF:r1|SL/MDM/2026-0117]]
Objet : Mise en demeure - loyers impayés

Monsieur,

Nous intervenons en qualité de conseil de la SCI [[ORG:o_tilleuls|LES TILLEULS DE SAÔNE]], bailleresse des locaux commerciaux situés [[ADDRESS:a3|14 rue Gambetta, 71000 Mâcon]], que vous occupez en vertu d'un bail commercial du 1er avril 2019.

À ce jour, vous restez redevable de la somme de 18 732,40 euros au titre des loyers et charges des mois de janvier à septembre 2026.

Nous vous mettons en demeure de régler cette somme sous huit jours par virement sur le compte [[IBAN:i1|{tilleuls_iban_sp}]] ouvert à la Banque [[ORG:o_arvoria|Arvoria]].

À défaut, notre cliente fera délivrer un commandement visant la clause résolutoire, conformément à l'((article L. 145-41 du Code de commerce)), et saisira le juge des référés du ((Tribunal judiciaire de Mâcon)).

Nous vous prions d'agréer, Monsieur [[PERSON:p_montclar|de Montclar]], l'expression de nos salutations distinguées.

Maître [[PERSON:p_lervignac|Sophie LERVIGNAC]]

Copie : Mme [[PERSON:p_quere|Mathilde Quéré-Lansac]], gérante
""",
})

DOCS.append({
    "name": "09_constat_internet",
    "type": "constat",
    "title": "Brivanor Logistique SAS c. Vasseur-Garnier - constat",
    "parties": [
        {"id": "o_brivanor", "kind": "ORG", "value": "Brivanor Logistique SAS"},
        {"id": "p_vasseur", "kind": "PERSON", "value": "Hélène Vasseur-Garnier"},
    ],
    "text": """PROCÈS-VERBAL DE CONSTAT SUR INTERNET

L'an deux mille vingt-six et le vingt-trois septembre,

À la demande de la société [[ORG:o_brivanor|BRIVANOR LOGISTIQUE]] SAS, [[SIREN:s1|{brivanor_siren}]] ((RCS)) Lyon,

Je, [[PERSON:p_marchal|Étienne MARCHAL]], commissaire de justice, certifie avoir procédé aux constatations suivantes depuis mon poste de travail relié à internet (adresse IP publique [[ID_CODE:ip1|198.51.100.23]], adresse IPv6 [[ID_CODE:ip2|2001:db8:85a3::8a2e:370:7334]]).

1. Je me rends sur le site [[URL:u1|https://www.brivanor-logistique.fr/equipe]] et constate que la page présente Mme [[PERSON:p_vasseur|Hélène Vasseur-Garnier]] comme « consultante associée ».

2. Je consulte le profil professionnel accessible à l'adresse [[URL:u2|https://www.reseau-pro.example/in/helene-vasseur-garnier]] ; il mentionne une collaboration avec [[URL:u3|quantorive-conseil.fr]].

3. Je consulte la fiche publique de l'entreprise sur ((https://annuaire-entreprises.data.gouv.fr)) et le texte de l'((article L. 441-10 du Code de commerce)) sur ((www.legifrance.gouv.fr)).

4. Un courriel du 2 septembre 2026, que me présente le requérant, demande le règlement d'une facture sur le compte allemand [[IBAN:i1|{de_iban_sp}]].

5. Le témoin, M. [[PERSON:p_santoni|Pierre-Antoine SANTONI]], né le [[BIRTHDATE:b1|8 avril 1975]] à Ajaccio, numéro de sécurité sociale [[NIR:n1|{santoni_nir_sp}]], présente une pièce d'identité : passeport n° [[ID_CODE:id1|19AB52817]].

Mes constatations étant terminées, j'ai dressé le présent procès-verbal.

[[PERSON:p_marchal|É. MARCHAL]]
""",
})


DOCS.append({
    "name": "10_formes_difficiles",
    "type": "note",
    "title": "Morvezen c. Torvane Industries SAS",
    "parties": [
        {"id": "p_morvezen", "kind": "PERSON", "value": "Ysaline Morvezen"},
        {"id": "o_torvane", "kind": "ORG", "value": "Torvane Industries SAS"},
        {"id": "p_ouardi", "kind": "PERSON", "value": "Mehdi Ouardi"},
    ],
    # Hard forms found by the review of 2026-10-16: English possessive, glued words, a social handle, a word
    # broken by a hyphen at a line end (PDF text), Unicode hyphens and soft hyphens, firms joined by "&" with
    # their legal form after a dash or a comma, a tribunal de commerce roll number and a SIREN inside an EUID.
    "text": """NOTE DE SYNTHÈSE – DOSSIER [[PERSON:p_morvezen|MORVEZEN]] C. [[ORG:o_torvane|TORVANE]]

[[ORG:o_cast|CASTAGNÈDE & LHOMME]] – SELAS d'avocats
Dossier suivi par Me [[PERSON:p_rochere|Hélène de La Rochère‑Vasseur]] (Toque [[ID_CODE:tq|1187]]).

Cliente : Mme [[PERSON:p_morvezen|Ysaline MORVEZEN]]. Adversaire : la société [[ORG:o_torvane|TORVANE INDUSTRIES]] SAS, numéro unique d'identification européen (EUID) FR6901.[[SIREN:s1|{torvane_siren}]], affaire enregistrée au ((Tribunal de commerce de Lyon)) sous le RG n° [[CASE_REF:rg1|2024J00817]].

1. Résumé en anglais pour le correspondant : [[PERSON:p_morvezen|Morvezen]]'s claim against [[ORG:o_torvane|Torvane]]'s subsidiary is not time-barred.

2. Les fichiers reçus portent des noms collés : [[PERSON:p_morvezen|Morvezen]]2026.pdf, [[ORG:o_torvane|Torvane]]-note.docx et [[PERSON:p_morvezen|YsalineMorvezen]].txt.

3. Le compte Instagram @[[PERSON:p_morvezen|ymorvezen]] a publié une photo du camion floqué au nom de TRANSPORTS [[ORG:o_grav|GRAVELOTTE]] ; le Garage [[ORG:o_grav|Gravelotte]] le confirme.

4. Le représentant de la société, M. [[PERSON:p_quellec|Bastien Quel-
lec]], a confirmé la réunion avec la SCI [[ORG:o_parc|DU PARC]], bailleresse des locaux.

5. Extrait Kbis du gérant :
Nom, prénoms : [[PERSON:p_fremiot|FRÉMIOT Bertrand, Louis, Marie]]
Le gérant, M. [[PERSON:p_fremiot|Ber­trand Fré­miot]], n'a pas répondu.

6. Attestation de M. [[PERSON:p_ouardi|Mehdi Ouardi]]. M. [[PERSON:p_ouardi|Ouardi]] a signé le constat dressé par l'étude [[ORG:o_pernaud|PERNAUD & VALETTE]], société d'exercice libéral à responsabilité limitée.

7. Selon la ((jurisprudence Jacques Vabre)), le droit de l'Union prime sur la loi postérieure.

Bonjour [[PERSON:p_corinne|Corinne]],
merci pour votre relecture.

Signé : [[PERSON:p_morel|J. Morel]]
""",
})


# ---------------------------------------------------------------------------
# Markup parser
# ---------------------------------------------------------------------------

_MARK_RE = re.compile(r"\[\[(?P<kind>[A-Z_]+):(?P<id>[\w]+)\|(?P<text>.*?)\]\]|\(\((?P<clear>.*?)\)\)", re.S)
CHECKSUM_KINDS = {"IBAN", "NIR", "SIREN", "SIRET", "VAT", "CARD"}
CHECKSUM_IDS = {"l1", "l2"}  # LEI and ISIN in the Kbis


def render(template: str) -> tuple[str, list[dict], list[dict]]:
    """Return (plain text, mentions, keep_clear) from a template with markup."""
    source = template.format_map(IDS)
    out: list[str] = []
    mentions: list[dict] = []
    clear: list[dict] = []
    pos = 0
    length = 0
    for m in _MARK_RE.finditer(source):
        chunk = source[pos:m.start()]
        out.append(chunk)
        length += len(chunk)
        if m.group("kind"):
            text = m.group("text")
            mentions.append({"id": m.group("id"), "kind": m.group("kind"), "text": text,
                             "start": length, "end": length + len(text)})
        else:
            text = m.group("clear")
            clear.append({"text": text, "start": length, "end": length + len(text)})
        out.append(text)
        length += len(text)
        pos = m.end()
    out.append(source[pos:])
    return "".join(out), mentions, clear


def build() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    manifest = []
    for doc in DOCS:
        text, mentions, clear = render(doc["text"])
        for mt in mentions:
            assert text[mt["start"]:mt["end"]] == mt["text"]
            mt["checksum"] = mt["kind"] in CHECKSUM_KINDS or (mt["kind"] == "ID_CODE" and mt["id"] in CHECKSUM_IDS)
        gold = {
            "doc": doc["name"] + ".txt",
            "type": doc["type"],
            "title": doc["title"],
            "parties": doc["parties"],
            "mentions": mentions,
            "keep_clear": clear,
        }
        tp = OUT / (doc["name"] + ".txt")
        gp = OUT / (doc["name"] + ".gold.json")
        tp.write_text(text, encoding="utf-8")
        gp.write_text(json.dumps(gold, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written += [tp, gp]
        manifest.append({"doc": tp.name, "gold": gp.name, "type": doc["type"]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return written


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(HERE.parents[1]))
