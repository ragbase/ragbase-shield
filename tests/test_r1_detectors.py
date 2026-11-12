"""R1 corrections, DETECTORS owner (R1_PLAN.md classes CL-07, CL-10 to CL-16 and the ``table_cells`` interface).

Every name, number and place below is invented for these tests. Identifier values are built in code (a valid
number, then one digit changed) so no real identifier appears.
"""
import pytest

from ragbase_shield.engine import Masker, MemoryStore, detect_structured, find_suspects
from ragbase_shield.engine.detectors import (
    detect_candidates,
    iban_check_digits,
    imo_valid,
    luhn_check_digit,
    structured_norm,
    table_cells,
)


def mask(text):
    return Masker(MemoryStore(), use_ner=False).mask(text)


def spans(text):
    return [(s.kind, s.value) for s in mask(text).spans]


def masked_values(text):
    return [s.value for s in mask(text).spans]


def wrong_last_digit(num):
    return num[:-1] + str((int(num[-1]) + 3) % 10)


def fr_iban(bban):
    return "FR" + iban_check_digits("FR", bban) + bban


def grouped(s):
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def siren_from(body):
    return body + luhn_check_digit(body)


def siret_from(siren, nic="0004"):
    return siren + nic + luhn_check_digit(siren + nic)


# --- table_cells (interface for NAMES) ------------------------------------------------------------------------


def test_table_cells_markdown_table_gives_header_labels():
    t = "| Prénom | Date de naissance |\n|---|---|\n| Ysolde | 04/11/2011 |\n| Aldwin | 19/02/2014 |"
    cells = table_cells(t)
    assert [(t[s:e], lab) for s, e, lab in cells] == [
        ("Ysolde", "prenom"), ("04/11/2011", "date de naissance"),
        ("Aldwin", "prenom"), ("19/02/2014", "date de naissance")]


def test_table_cells_docx_rows_without_outer_pipes_and_empty_cells():
    t = "Salarié | Matricule | Équipe\nVasquerin | 70413 | \nFerlavoux |  | Quart B"
    got = [(t[s:e], lab) for s, e, lab in table_cells(t)]
    assert got == [("Vasquerin", "salarie"), ("70413", "matricule"), ("Ferlavoux", "salarie"), ("Quart B", "equipe")]


def test_table_cells_block_ends_at_a_line_without_pipes():
    t = "A | B\n1 | 2\nTexte libre.\nC | D\n3 | 4"
    got = [(t[s:e], lab) for s, e, lab in table_cells(t)]
    assert got == [("1", "a"), ("2", "b"), ("3", "c"), ("4", "d")]
    assert table_cells("une phrase | avec une barre") == []
    assert table_cells("pas de tableau") == []


# --- CL-11: identifier shape with a wrong check digit ---------------------------------------------------------


def test_iban_with_wrong_check_digit_is_masked_and_still_reported():
    good = fr_iban("2004101005" + "0500013M02606")
    bad = wrong_last_digit(good)
    t = f"Coordonnées bancaires : {grouped(bad)} (Banque Talvoreen)"
    assert grouped(bad) in masked_values(t)
    assert all(s.kind != "IBAN" for s in detect_structured(t))  # its check digit fails
    assert [s.kind for s in find_suspects(t)] == ["IBAN"]


def test_iban_wrong_check_not_masked_when_not_iban_shaped():
    # exact length but mostly letters: a reference, not an IBAN with a typo
    t = "code FR12 ABCD EFGH IJKL MNOP QRST U12"
    assert "IBAN" not in [k for k, _ in spans(t)]
    # lower case look-alike with a wrong checksum stays ordinary text
    good = fr_iban("1027807777" + "0002345678904")
    assert spans("voir " + wrong_last_digit(good).lower()) == []


def test_iban_wrong_length_is_not_masked():
    good = fr_iban("3004700055" + "0001112223344")
    short = good[:-1]
    assert "IBAN" not in [k for k, _ in spans(f"compte {short} ouvert")]


def test_siret_with_wrong_key_masked_only_with_a_label_on_the_line():
    siret = siret_from(siren_from("41852963"))
    bad = wrong_last_digit(siret)
    sp = f"{bad[:3]} {bad[3:6]} {bad[6:9]} {bad[9:]}"
    assert ("SIRET", sp) in spans(f"Établissement employeur – SIRET : {sp}")
    assert spans(f"bordereau {sp} du transporteur") == []
    # the label must be on the same line
    assert spans(f"SIRET :\nbordereau {sp}") == []


def test_siren_with_wrong_luhn_and_rcs_label_is_one_span():
    siren = siren_from("63917420")
    bad = wrong_last_digit(siren)
    t = f"immatriculée au RCS de Vauclerval sous le n° {bad[:3]} {bad[3:6]} {bad[6:]}"
    assert ("SIREN", f"{bad[:3]} {bad[3:6]} {bad[6:]}") in spans(t)
    # a valid SIREN followed by a wrong NIC stays one SIRET span, never "SIREN + digits"
    siret_bad = wrong_last_digit(siret_from(siren))
    t2 = f"SIRET {siret_bad}"
    assert spans(t2) == [("SIRET", siret_bad)]


def test_siret_column_of_a_table():
    good = siret_from(siren_from("52074186"), "0019")
    bad = wrong_last_digit(good)
    t = f"Société | SIRET\nTalvoreen Marine | {good}\nBrumaskel Outillage | {bad}"
    vals = masked_values(t)
    assert good in vals and bad in vals


# --- CL-12: court roll numbers with a section letter and no "n°" -------------------------------------------------


@pytest.mark.parametrize("text,value", [
    ("Affaire enrôlée sous la référence G 25/07391 devant la section", "G 25/07391"),
    ("N° RG H 24/01277", "H 24/01277"),
    ("RG K 23/40518 – audience du 3 mars", "K 23/40518"),
])
def test_section_letter_roll_numbers(text, value):
    assert ("CASE_REF", value) in spans(text)


def test_section_roll_number_loose_shapes_need_court_context():
    assert spans("le conseil de prud'hommes, dossier enrôlé W24/06613") == [("CASE_REF", "W24/06613")]
    assert spans("prix unitaire W24/06613 hors taxes") == []
    assert spans("une pente de 12/45678 et un ratio 24/100") == []


def test_bare_roll_number_needs_a_court_word_on_the_line():
    assert ("CASE_REF", "25/03318") in spans("Conseil de prud'hommes de Vauclerval, affaire 25/03318")
    assert spans("le coefficient 25/03318 du barème") == []


# --- CL-13: labelled references without a check digit ----------------------------------------------------------


@pytest.mark.parametrize("text,kind,value", [
    ("Matricule : Q-70413", "EMPLOYEE_ID", "Q-70413"),  # v0.2: own kind
    ("procédure n° 2025-0917 ouverte", "CASE_REF", "2025-0917"),
    ("contrat de prêt n° 00731942 signé", "ID_CODE", "00731942"),
    ("N/Réf. : QTV/2025/0418", "CASE_REF", "QTV/2025/0418"),
    ("Numéro allocataire : 8801764", "ID_CODE", "8801764"),
    ("compte cotisant URSSAF n° 117 000 6093 1846", "ID_CODE", "117 000 6093 1846"),
    ("titre de perception n° 2025-77-1093", "ID_CODE", "2025-77-1093"),
    ("enquête préliminaire n° 25/00981/PQ", "CASE_REF", "25/00981/PQ"),
])
def test_labelled_references(text, kind, value):
    assert (kind, value) in spans(text)


@pytest.mark.parametrize("text", [
    "article 1231-6 du code civil",
    "référence à la loi n° 2015-990 du 6 août 2015",
    "la procédure prévue par le décret n° 2019-1333",
    "dossier du 12/03/2024",
    "contrat de 2024",
    "Référence : 12 500 € HT",
    "le dossier comprend 1250 pages",
    "le contrat de travail à durée indéterminée",
])
def test_labelled_references_leave_laws_dates_amounts_and_prose(text):
    assert [k for k, _ in spans(text) if k in ("ID_CODE", "CASE_REF")] == []


def test_form_label_with_the_value_on_the_next_line():
    assert ("ID_CODE", "AX-55102") in spans("Identifiant :\nAX-55102")


def test_toque_with_a_space_between_letter_and_number():
    assert ("ID_CODE", "R 0712") in spans("Me Ferlavoux, avocat, toque : R 0712")
    assert ("ID_CODE", "B 33") in spans("Toque n° B 33")
    assert spans("une toque de cuisinier") == []


def test_bic_with_a_branch_code_is_masked_bank_code_alone_stays(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_BIC", raising=False)
    assert ("ID_CODE", "QTVAFRPPK17") in spans("BIC : QTVAFRPPK17")
    assert spans("BIC QTVAFRPP") == []
    assert spans("BIC QTVAFRPPXXX") == []  # "XXX" is the head office: the bank, not a branch
    monkeypatch.setenv("RAGBASE_SHIELD_MASK_BIC", "all")
    assert ("ID_CODE", "QTVAFRPP") in spans("BIC QTVAFRPP")
    monkeypatch.setenv("RAGBASE_SHIELD_MASK_BIC", "0")
    assert spans("BIC : QTVAFRPPK17") == []


def test_bic_right_after_an_iban_without_its_own_label(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_BIC", raising=False)
    iban = fr_iban("1951904125" + "0007770118355")
    t = f"IBAN {iban} / ZRWBFRP1M04"
    vals = masked_values(t)
    assert iban in vals and "ZRWBFRP1M04" in vals
    # an upper-case word right after the IBAN, with no separator and no digit, is not taken as a BIC
    assert masked_values(f"IBAN {iban} QTVAFRPPKZW") == [iban]
    # the country part of a BIC must be a country code
    assert masked_values(f"IBAN {iban} / QTVAQQP1M04") == [iban]


def test_mifir_national_client_identifier():
    assert ("ID_CODE", "BE19881023YSOLDVASQU") in spans("Identifiant MiFIR : BE19881023YSOLDVASQU")
    assert ("ID_CODE", "LU20011207ALDWIFERL#") in spans("CONCAT LU20011207ALDWIFERL#")
    assert spans("code BE19881399YSOLDVASQU") == []  # month 13 is not a date


def test_postal_tracking_number_needs_a_mail_context():
    assert ("ID_CODE", "2C 418 773 0952 6") in spans("envoyé en lettre recommandée, suivi 2C 418 773 0952 6")
    assert ("ID_CODE", "RQ 417 552 908 FR") in spans("Colis international RQ 417 552 908 FR")
    assert spans("code produit RQ417552908FR") == []


def test_labelled_reference_in_a_table_column():
    t = "Nom | Matricule | Service\nVasquerin | 0070413 | Atelier\nFerlavoux | 0070588 | Quai"
    vals = masked_values(t)
    assert "0070413" in vals and "0070588" in vals
    assert "Atelier" not in vals and "Quai" not in vals


# --- CL-14: cadastral parcels ------------------------------------------------------------------------------------


def test_cadastre_section_with_numbers():
    assert ("ID_CODE", "QX n° 118 et 119") in spans("un terrain cadastré section QX n° 118 et 119")
    assert ("ID_CODE", "B 2207") in spans("la parcelle figurant au cadastre section B 2207")


def test_cadastre_items_after_a_parcel_word():
    assert ("ID_CODE", "YB 41 et YB 42") in spans("les parcelles YB 41 et YB 42 sont grevées d'une servitude")
    assert ("ID_CODE", "WT 7") in spans("cadastrée WT 7, d'une contenance de 12 a")


def test_cadastre_leaves_court_sections_roads_and_plain_sections():
    assert spans("section Encadrement du conseil") == []
    assert [k for k, _ in spans("la parcelle longe la RD 917 sur 200 mètres")] == []
    assert spans("voir la section B 4 du rapport") == []


# --- CL-15: dates of birth in digits ----------------------------------------------------------------------------


@pytest.mark.parametrize("text,value", [
    ("Né(e) le : 17/08/1983", "17/08/1983"),
    ("NÉE LE : 02.11.1990", "02.11.1990"),
    ("Date of birth: 1979-06-21", "1979-06-21"),
    ("DOB 1979-06-21", "1979-06-21"),
])
def test_birth_labels(text, value):
    assert ("BIRTHDATE", value) in spans(text)


def test_birth_dates_in_a_table_column_and_in_a_key_value_row():
    t = "| Enfant | Né le | Classe |\n|---|---|---|\n| Ysolde | 04/11/2011 | CM2 |\n| Aldwin | 19/02/2014 | CE1 |"
    vals = masked_values(t)
    assert "04/11/2011" in vals and "19/02/2014" in vals
    assert ("BIRTHDATE", "30/09/1987") in spans("Date de naissance | 30/09/1987")


def test_event_dates_stay_clear():
    assert spans("signé le : 17/08/1983") == []
    t = "| Échéance | Montant |\n|---|---|\n| 04/11/2025 | 300 € |"
    assert [k for k, _ in spans(t)] == []
    assert structured_norm("BIRTHDATE", "1979-06-21") == structured_norm("BIRTHDATE", "21/06/1979")


# --- CL-16: address parts --------------------------------------------------------------------------------------


def test_zone_name_with_a_regional_article_is_taken_whole():
    assert spans("Siège : ZA de Pen ar Velin, 29870 Kergolven") == [
        ("ADDRESS", "ZA de Pen ar Velin, 29870 Kergolven")]
    assert spans("lieu-dit Mas del Quindrel, 34190 Brissac-sur-Orb") == [
        ("ADDRESS", "lieu-dit Mas del Quindrel, 34190 Brissac-sur-Orb")]


def test_adjective_before_the_street_type():
    assert spans("domiciliée 7 Grande Rue, 38990 Saint-Ovrel") == [("ADDRESS", "7 Grande Rue, 38990 Saint-Ovrel")]
    assert spans("au 15 Vieille Route de Talvoreen") == [("ADDRESS", "15 Vieille Route de Talvoreen")]
    assert spans("dans une petite rue calme") == []


def test_two_column_letter_header_keeps_each_town_with_its_street():
    t = ("Monsieur Vasquerin                 Société Brumaskel\n"
         "17 rue des Quindrelles             12 avenue Ferlavoux\n"
         "62480 Vauclerval                   59870 Morgwenig")
    vals = masked_values(t)
    assert "17 rue des Quindrelles" in vals and "12 avenue Ferlavoux" in vals
    assert "62480 Vauclerval" in vals and "59870 Morgwenig" in vals


def test_postcode_and_town_after_an_address_code():
    store = MemoryStore()
    m = Masker(store, use_ner=False)
    first = m.mask("demeurant 4 impasse des Quindrelles")
    code = first.text.split()[-1]
    assert code.startswith("ADRESSE_")
    again = m.mask(f"{code}, 62480 Vauclerval", keep_known_codes=True)
    assert "Vauclerval" not in again.text and code in again.text


def test_uk_and_canadian_addresses():
    assert spans("Office: 14 Quarry Lane, Bristol BS7 4QX") == [("ADDRESS", "14 Quarry Lane, Bristol BS7 4QX")]
    assert spans("Bureau : 88 Maple Crescent, Halifax (Nova Scotia) B3K 2T9") == [
        ("ADDRESS", "88 Maple Crescent, Halifax (Nova Scotia) B3K 2T9")]
    assert spans("Kelvanne, ON K7L 3N6") == [("ADDRESS", "Kelvanne, ON K7L 3N6")]


def test_town_alone_stays_clear():
    assert spans("Elle habite à Vauclerval depuis 2019.") == []
    assert spans("Rendez-vous à Bristol la semaine prochaine.") == []


# --- CL-07: vessel names --------------------------------------------------------------------------------------


def test_vessel_with_a_distinctive_name_masks_the_name_only():
    r = mask("la vedette Brumaskel-Varn a été saisie au port")
    assert [(s.kind, s.value) for s in r.spans] == [("ID_CODE", "Brumaskel-Varn")]
    assert r.text.startswith("la vedette IDENT_")
    assert ("ID_CODE", "Ystrelle") in spans("le voilier « Ystrelle » de M. Vasquerin")


def test_vessel_with_an_ordinary_word_name_masks_word_and_trigger_together():
    # the ordinary word alone never becomes a dictionary entry
    assert spans("le chalutier Espérance est désarmé") == [("ID_CODE", "chalutier Espérance")]
    assert spans("Le navire est arrivé au port.") == []
    assert spans("le bateau de pêche du père") == []


def test_vessel_column_and_imo_number():
    t = "Navire | Année\nMorgwenig | 1998\nTalvoreen II | 2004"
    vals = masked_values(t)
    assert "Morgwenig" in vals and "Talvoreen II" in vals
    imo = "947013" + str(sum(int(c) * w for c, w in zip("947013", range(7, 1, -1))) % 10)
    assert imo_valid(imo)
    assert ("ID_CODE", imo) in spans(f"IMO {imo}")


# --- CL-10: schools, crèches and care homes ---------------------------------------------------------------------


def test_school_with_a_distinctive_name_keeps_the_establishment_word():
    r = mask("Ysolde est scolarisée au groupe scolaire Les Quindrelles depuis 2021.")
    assert ("ORG", "Les Quindrelles") in [(s.kind, s.value) for s in r.spans]
    assert "groupe scolaire SOCIETE_" in r.text
    assert ("ORG", "Saint-Ferlavoux") in spans("inscrit au collège Saint-Ferlavoux")
    assert ("ORG", "Morgwenig") in spans("la micro-crèche Morgwenig")


def test_school_named_with_ordinary_words_is_masked_as_one_phrase():
    assert spans("Elle va à l'école du Moulin chaque matin.") == [("ID_CODE", "école du Moulin")]


def test_public_institutions_and_ordinary_uses_stay_clear():
    for t in ("diplômé de l'École nationale de la magistrature", "le collège Cadres du comité",
              "au lycée de Vauclerval", "l'école de la République", "le collège des salariés",
              "École : oui"):
        assert [k for k, _ in spans(t) if k in ("ORG", "ID_CODE")] == [], t


def test_school_column_of_a_table():
    t = "| Enfant | École |\n|---|---|\n| Ysolde | Les Quindrelles |\n| Aldwin | Ferlavoux-Haut |"
    vals = masked_values(t)
    assert "Les Quindrelles" in vals and "Ferlavoux-Haut" in vals


def test_detect_candidates_marks_unchecked_identifiers():
    good = fr_iban("2004101005" + "0500013M02606")
    bad = wrong_last_digit(good)
    c = [c for c in detect_candidates(f"IBAN {bad}") if c.kind == "IBAN"]
    assert c and c[0].valid and not c[0].checked
    c = [c for c in detect_candidates(f"IBAN {good}") if c.kind == "IBAN"]
    assert c and c[0].valid and c[0].checked


# --- precision guards added with the rules above ------------------------------------------------------------------


def test_prose_around_labels_stays_clear():
    for t in ("La procédure de licenciement a été engagée le 12/03/2024 par lettre recommandée.",
              "Le PV de constat du 12/05/2023 a été dressé.",
              "La retraite à taux plein est acquise à 67 ans.",
              "Son contrat de 2019 a été renouvelé ; dossier de 2021 classé.",
              "Matricule : à compléter"):
        assert [k for k, _ in spans(t) if k in ("ID_CODE", "CASE_REF")] == [], t


def test_childminder_is_not_a_school_and_left_cells_are_labels_only_in_key_value_rows():
    assert [k for k, _ in spans("L'assistante maternelle Ysolde Ferlavoux garde les enfants.")
            if k in ("ORG", "ID_CODE")] == []
    t = "| Contrat | Montant | Échéance |\n|---|---|---|\n| Prêt immobilier | 25000 | 03/05/2016 |"
    assert [k for k, _ in spans(t)] == []
    t2 = "| Ne pas remplir | Date |\n|---|---|\n| X | 03/05/2016 |"
    assert [k for k, _ in spans(t2)] == []
    assert ("EMPLOYEE_ID", "AX-55102") in spans("Fiche | Agent\nMatricule : | AX-55102")
    assert ("EMPLOYEE_ID", "AX-55102") in spans("Matricule | AX-55102\nService | Quai")


def test_codes_are_never_read_as_reference_values():
    assert [k for k, _ in spans("dossier IDENT_12 et procédure RG_3") if k in ("ID_CODE", "CASE_REF")] == []
