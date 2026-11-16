"""Engine: structured detectors with check digits. All numbers are generated or textbook examples."""
import pytest

from ragbase_shield.engine import detect_structured, find_suspects
from ragbase_shield.engine.detectors import (
    iban_check_digits,
    iban_valid,
    isin_valid,
    lei_valid,
    luhn_check_digit,
    luhn_valid,
    nir_key,
    nir_valid,
    siren_valid,
    siret_valid,
    structured_norm,
    url_is_public,
    vat_fr_key,
    vat_fr_valid,
)


def found(text):
    return [(s.kind, s.value) for s in detect_structured(text)]


def kinds(text):
    return [s.kind for s in detect_structured(text)]


def suspects(text):
    return [(s.kind, s.value) for s in find_suspects(text)]


def make_siren(body="73282932"):
    return body + luhn_check_digit(body)


def bad_digit(num):
    """Same number with the last digit changed (so the check fails)."""
    return num[:-1] + str((int(num[-1]) + 1) % 10)


# --- check digit helpers -------------------------------------------------------------------------


def test_luhn():
    assert luhn_valid("4970101234567893")
    assert not luhn_valid("4970101234567890")
    assert not luhn_valid("")
    assert not luhn_valid("12a4")


def test_siren_siret_validators():
    siren = make_siren()
    assert siren_valid(siren) and not siren_valid(bad_digit(siren))
    nic = "0001"
    siret = siren + nic + luhn_check_digit(siren + nic)
    assert siret_valid(siret) and not siret_valid(bad_digit(siret))


def test_siret_la_poste_exception():
    # La Poste establishments: sum of digits is a multiple of 5, Luhn does not apply.
    s = next("356000000" + f"{n:05d}" for n in range(1, 100000)
             if sum(map(int, "356000000" + f"{n:05d}")) % 5 == 0 and not luhn_valid("356000000" + f"{n:05d}"))
    assert siret_valid(s)
    assert not siret_valid("356000000" + "00002")


def test_nir_key_and_corsica():
    body = "1800375112005"
    assert nir_valid(body + f"{nir_key(body):02d}")
    assert not nir_valid(body + f"{(nir_key(body) % 97) + 1:02d}")
    for corsica in ("175042A004087", "282112B033012"):
        assert nir_valid(corsica + f"{nir_key(corsica):02d}")
    assert nir_key("175042A004087") != nir_key("175042B004087")


def test_nir_rejects_impossible_month():
    body = "1801575112005"  # month 15 does not exist
    assert not nir_valid(body + f"{nir_key(body):02d}")


def test_iban_validator_all_countries():
    for iban in ("FR7630006000011234567890189", "DE89370400440532013000", "GB82WEST12345698765432",
                 "BE68539007547034", "NL91ABNA0417164300", "CH9300762011623852957"):
        assert iban_valid(iban), iban
    assert not iban_valid("FR7630006000011234567890188")
    assert not iban_valid("FR763000600001123456789018")  # wrong length for FR
    bban = "30006000011234567890189"
    assert iban_check_digits("FR", bban) == "76"


def test_vat_fr_key():
    siren = make_siren()
    key = vat_fr_key(siren)
    assert vat_fr_valid(f"FR{key:02d}{siren}")
    assert vat_fr_valid(f"FR {key:02d} {siren[:3]} {siren[3:6]} {siren[6:]}")
    assert not vat_fr_valid(f"FR{(key + 1) % 97:02d}{siren}")


def test_isin_and_lei():
    assert isin_valid("US0378331005")
    assert not isin_valid("US0378331006")
    body = "969500ABCDEFGHJK12"
    n = int("".join(str(int(c, 36)) for c in body + "00"))
    lei = body + f"{98 - n % 97:02d}"
    assert lei_valid(lei)
    assert not lei_valid(lei[:-1] + str((int(lei[-1]) + 1) % 10))


# --- detection in text ---------------------------------------------------------------------------


def test_email():
    assert found("Écrire à jp.delacourt@brivanor-exemple.fr.") == [("EMAIL", "jp.delacourt@brivanor-exemple.fr")]
    assert found("contact : <s.o'neil+test@cabinet-exemple.co.uk>") == [("EMAIL", "s.o'neil+test@cabinet-exemple.co.uk")]


@pytest.mark.parametrize("phone", [
    "01 99 00 12 34", "01.99.00.12.34", "01-99-00-12-34", "0199001234", "+33 1 99 00 12 34",
    "+33 (0)1 99 00 12 34", "+33199001234", "0033 6 39 98 12 34", "06 39 98 12 34",
])
def test_phone_french_formats(phone):
    assert found(f"Tél. : {phone}, merci") == [("PHONE", phone)]


def test_phone_international_and_not_amounts():
    assert found("Mobile UK +44 20 7946 0958.") == [("PHONE", "+44 20 7946 0958")]
    assert kinds("La somme de 1 234 567,89 euros et 12 345 678 euros.") == []
    assert kinds("Le 12/03/2024 à 14:30.") == []


def test_phone_norm_links_spellings():
    assert structured_norm("PHONE", "+33 6 39 98 12 34") == structured_norm("PHONE", "06.39.98.12.34") == "0639981234"


@pytest.mark.parametrize("iban", [
    "FR76 3000 6000 0112 3456 7890 189", "FR7630006000011234567890189", "DE89 3704 0044 0532 0130 00",
    "GB82 WEST 1234 5698 7654 32", "BE68 5390 0754 7034",
])
def test_iban_in_text(iban):
    assert found(f"Virement sur le compte {iban}, BIC AGRIFRPP.") == [("IBAN", iban)]


def test_iban_wrong_check_is_suspect_not_checksum_valid():
    # detect_structured lists check-digit-valid values only; since R1 (CL-11) the masker still masks this
    # IBAN-shaped value (tests/test_r1_detectors.py), and it stays on the review list.
    t = "IBAN FR76 3000 6000 0112 3456 7890 188"
    assert found(t) == []
    assert suspects(t) == [("IBAN", "FR76 3000 6000 0112 3456 7890 188")]


def test_iban_not_extended_into_next_word():
    t = "IBAN FR76 3000 6000 0112 3456 7890 189 BIC BNPAFRPP"
    assert found(t) == [("IBAN", "FR76 3000 6000 0112 3456 7890 189")]


def test_nir_spaced_and_compact():
    body = "1800375112005"
    nir = body + f"{nir_key(body):02d}"
    spaced = f"{nir[0]} {nir[1:3]} {nir[3:5]} {nir[5:7]} {nir[7:10]} {nir[10:13]} {nir[13:]}"
    assert found(f"NIR : {spaced}") == [("NIR", spaced)]
    assert found(f"n° SS {nir}.") == [("NIR", nir)]
    corsica = "175042A004087"
    c = corsica + f"{nir_key(corsica):02d}"
    cs = f"{c[0]} {c[1:3]} {c[3:5]} {c[5:7]} {c[7:10]} {c[10:13]} {c[13:]}"
    assert found(f"né en Corse : {cs}") == [("NIR", cs)]


def test_nir_wrong_key_is_suspect():
    body = "2900769383045"
    wrong = body + f"{(nir_key(body) % 97) + 1:02d}"
    assert found(f"NIR {wrong}") == []
    assert suspects(f"NIR {wrong}") == [("NIR", wrong)]


def test_siren_and_siret_in_text():
    siren = make_siren()
    sp = f"{siren[:3]} {siren[3:6]} {siren[6:]}"
    assert found(f"RCS Lyon {sp}") == [("SIREN", sp)]
    assert found(f"RCS Lyon B {siren}") == [("SIREN", siren)]
    nic = "0002"
    siret = siren + nic + luhn_check_digit(siren + nic)
    for form in (siret, f"{sp} {siret[9:]}", f"{sp} {siret[9:12]} {siret[12:]}"):
        assert found(f"SIRET : {form}.") == [("SIRET", form)], form


def test_siren_wrong_luhn_not_checksum_valid_and_amounts_ignored():
    # detect_structured lists check-digit-valid values only; since R1 (CL-11) a labelled wrong-key SIREN is
    # masked all the same (tests/test_r1_detectors.py), and it stays on the review list.
    siren = make_siren()
    wrong = bad_digit(siren)
    assert found(f"SIREN {wrong}") == []
    assert suspects(f"SIREN {wrong}") == [("SIREN", wrong)]
    sp = f"{siren[:3]} {siren[3:6]} {siren[6:]}"
    assert found(f"un capital de {sp} euros") == []
    assert found(f"montant : {sp} €") == []
    assert found(f"soit {sp},00 EUR") == []
    assert suspects(f"la référence 123456789 du colis") == []  # no keyword: not flagged


def test_vat_in_text():
    siren = make_siren()
    vat = f"FR{vat_fr_key(siren):02d}{siren}"
    assert found(f"TVA intracommunautaire : {vat}") == [("VAT", vat)]
    spaced = f"FR {vat[2:4]} {siren[:3]} {siren[3:6]} {siren[6:]}"
    assert found(f"N° TVA {spaced}") == [("VAT", spaced)]
    bad = f"FR{(vat_fr_key(siren) + 1) % 97:02d}{siren}"
    assert found(f"TVA {bad}") == []
    assert suspects(f"TVA {bad}") == [("VAT", bad)]


@pytest.mark.parametrize("card", ["4970 1012 3456 7893", "4970-1012-3456-7893", "4970101234567893", "3782 822463 10005"])
def test_card(card):
    assert found(f"Carte n° {card} exp. 09/28") == [("CARD", card)]


def test_card_wrong_luhn():
    assert found("Carte 4970 1012 3456 7890") == []
    assert suspects("Carte 4970 1012 3456 7890") == [("CARD", "4970 1012 3456 7890")]


@pytest.mark.parametrize("text,value", [
    ("RG n° 23/01234", "23/01234"),
    ("N° RG 21/00123", "21/00123"),
    ("R.G. : 22/04567", "22/04567"),
    ("répertoire général n° 2023/01234", "2023/01234"),
    ("Cass. soc., 8 mars 2023, n° 21-12.345", "21-12.345"),
    ("sur le pourvoi n° Q 21-12.345", "Q 21-12.345"),
    ("N° Portalis DBVX-V-B7H-OPQR", "DBVX-V-B7H-OPQR"),
    ("N° Portalis 352J-W-B7I-C3XXF", "352J-W-B7I-C3XXF"),
    ("décision ECLI:FR:CCASS:2021:SO00123.", "ECLI:FR:CCASS:2021:SO00123"),
    ("jugement du tribunal, affaire n° 2023/1234", "2023/1234"),
    ("requête n° 2301234 enregistrée au greffe", "2301234"),
    ("Nos réf. : SL/2023/0456", "SL/2023/0456"),
])
def test_case_refs(text, value):
    assert found(text) == [("CASE_REF", value)]


def test_docket_needs_court_context_and_skips_laws():
    assert found("la facture n° 2023/1234 du fournisseur") == []
    assert found("le règlement (UE) n° 2016/679 relatif aux données") == []
    assert found("le pourvoi 21-12.345") == [("CASE_REF", "21-12.345")]
    assert found("la version 21-12.345 du logiciel") == []


def test_id_codes():
    assert found("ISIN US0378331005") == [("ID_CODE", "US0378331005")]
    assert found("ISIN US0378331006") == []
    assert found("véhicule AB-123-CD") == [("ID_CODE", "AB-123-CD")]
    assert found("le véhicule immatriculé AB 123 CD") == [("ID_CODE", "AB 123 CD")]
    assert found("le code AB 123 CD du produit") == []
    assert found("serveur 192.0.2.44 et 2001:db8:85a3::8a2e:370:7334") == [
        ("ID_CODE", "192.0.2.44"), ("ID_CODE", "2001:db8:85a3::8a2e:370:7334")]
    assert found("l'article 1.2.3.4 du contrat") == []
    assert found("passeport n° 19AB52817") == [("ID_CODE", "19AB52817")]
    assert found("la commande 19AB52817") == []


def test_urls_and_public_whitelist():
    assert found("voir https://www.brivanor-exemple.fr/equipe.") == [("URL", "https://www.brivanor-exemple.fr/equipe")]
    assert found("site www.brivanor-exemple.fr ou brivanor-exemple.com/contact") == [
        ("URL", "www.brivanor-exemple.fr"), ("URL", "brivanor-exemple.com/contact")]
    for public in ("https://www.legifrance.gouv.fr/codes/id/LEGIARTI000006901174", "www.cnil.fr",
                   "https://eur-lex.europa.eu/eli/reg/2016/679/oj", "https://fr.wikipedia.org/wiki/Cour_de_cassation",
                   "www.service-public.fr", "https://www.courdecassation.fr/decision/123"):
        assert found(f"source : {public}") == [], public
        assert url_is_public(public)
    assert found("M.Dupont et S.A.S. et art.Fr") == []


@pytest.mark.parametrize("text,value", [
    ("né le 12 mars 1980 à Lyon", "12 mars 1980"),
    ("née le 12/03/1980", "12/03/1980"),
    ("né(e) le 1er janvier 1975", "1er janvier 1975"),
    ("Date de naissance : 05/06/1977", "05/06/1977"),
    ("Date et lieu de naissance : Le 11 février 1962 à Lyon", "11 février 1962"),
    ("née à Mâcon (71), le 3 mai 1975", "3 mai 1975"),
    ("Mme Durand, née VASSEUR le 3 mai 1975", "3 mai 1975"),
    ("MONSIEUR DUPONT, NÉ LE 3 MARS 1970", "3 MARS 1970"),
    ("DATE DE NAISSANCE : 12/03/1980", "12/03/1980"),
])
def test_birthdate(text, value):
    assert [f for f in found(text) if f[0] != "BIRTHPLACE"] == [("BIRTHDATE", value)]


@pytest.mark.parametrize("text,place", [
    ("né le 12 mars 1980 à Lyon", "Lyon"),
    ("Date et lieu de naissance : Le 11 février 1962 à Lyon", "Lyon"),
    ("née à Mâcon (71), le 3 mai 1975", "Mâcon"),
    ("Monsieur Jean Kerbrat, né en 1958 à Saint-Brieuc", "Saint-Brieuc"),
    ("Lieu de naissance : Quimperlé", "Quimperlé"),
    ("born on 4 March 1970 in Leeds", "Leeds"),
])
def test_birthplace(text, place):
    """Plugin round 2: the town next to a birth date or a birth word is masked (LIEU_n)."""
    assert ("BIRTHPLACE", place) in found(text)


def test_town_without_birth_is_clear():
    assert not [f for f in found("signé à Angers le 3 mars 2020 ; demeurant à Lyon ; né le 3 mars 1980 à l'hôpital")
                if f[0] == "BIRTHPLACE"]


def test_dates_without_birth_context_are_clear():
    assert found("Par jugement du 12 mars 1980, le tribunal a statué ; il ne le 12 mars") == []
    assert found("la décision ne sera rendue que le 12 mars 2025") == []


@pytest.mark.parametrize("text,value", [
    ("demeurant 12 bis, rue des Lilas, 69003 Lyon,", "12 bis, rue des Lilas, 69003 Lyon"),
    ("situé 3 rue de la Paix 75002 PARIS.", "3 rue de la Paix 75002 PARIS"),
    ("au 18 avenue Félix Faure - 69003 Lyon", "18 avenue Félix Faure - 69003 Lyon"),
    ("12-14 bd du Général Leclerc, 92200 Neuilly-sur-Seine", "12-14 bd du Général Leclerc, 92200 Neuilly-sur-Seine"),
    ("BP 4521 - 69003 LYON CEDEX 03.", "BP 4521 - 69003 LYON CEDEX 03"),
    ("CS 70001, 75008 Paris", "CS 70001, 75008 Paris"),
    ("lieu-dit Les Granges, 71250 Cluny", "lieu-dit Les Granges, 71250 Cluny"),
    ("7 impasse des Glycines\nBâtiment C\n69100 Villeurbanne", "7 impasse des Glycines\nBâtiment C\n69100 Villeurbanne"),
    ("12 avenue des Champs, 75008 Paris Cedex 08.", "12 avenue des Champs, 75008 Paris Cedex 08"),
    ("Demeurant 12 rue des Lilas\r\n69003 LYON\r\n", "12 rue des Lilas\r\n69003 LYON"),
    ("DEMEURANT 3 RUE DE LA PAIX 75002 PARIS,", "3 RUE DE LA PAIX 75002 PARIS"),
])
def test_addresses(text, value):
    assert found(text) == [("ADDRESS", value)]


def test_address_false_positives():
    for t in ("mettre en place une procédure", "au cours de la procédure", "la Cour d'appel, pôle 6, ch. 5",
              "à la place de Pierre Martin", "chemin de fer", "les 3 cours de droit"):
        assert kinds(t) == [], t


def test_structured_norms():
    assert structured_norm("IBAN", "FR76 3000 6000 0112 3456 7890 189") == "FR7630006000011234567890189"
    assert structured_norm("URL", "https://www.Exemple.fr/") == "exemple.fr"
    assert structured_norm("BIRTHDATE", "12 mars 1980") == structured_norm("BIRTHDATE", "12/03/1980") == "1980-03-12"
    assert structured_norm("ID_CODE", "AB-123-CD") == structured_norm("ID_CODE", "ab 123 cd")
