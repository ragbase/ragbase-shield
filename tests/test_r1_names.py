"""R1 corrections, NAMES owner (names.py, masker.py, lexicons). One group of tests per failure class of R1_PLAN.md.

Every name, company, number and date below is invented for these tests.
"""
from __future__ import annotations

from ragbase_shield.engine import Masker, MemoryStore, entity_norm
from ragbase_shield.engine import names as nm
from ragbase_shield.engine.masker import code_like_spans, escape_codes


def registered(*items) -> Masker:
    store = MemoryStore()
    for kind, value in items:
        store.add(kind, value, entity_norm(kind, value))
    return Masker(store, use_ner=False)


def fresh() -> Masker:
    return Masker(MemoryStore(), use_ner=False)


def names_of(result, kind=None):
    return [s.value for s in result.spans if s.kind in ((kind,) if kind else ("PERSON", "ORG"))]


# --- CL-01: acronym of a registered company --------------------------------------------------------------------


def test_cl01_acronym_whole_word_and_code_prefix():
    m = registered(("ORG", "Brasseries Velanor Quimpertin"))
    out = m.mask("Le lot BVQ-310, la série BVQ2024 ; BVQ a vendu ; Data room BVQ").text
    assert "BVQ" not in out
    assert out.count("SOCIETE_A") == 4 and "SOCIETE_A-310" in out


def test_cl01_defined_alias_with_alternative_names():
    r = fresh().mask("La société Brasseries Velanor Quimpertin SAS (ci-après « BVQ » ou « la Société »). BVQ a vendu.")
    assert "BVQ" not in r.text and "« la Société »" in r.text
    assert len([e for e in r.new_entities if e.kind == "ORG"]) == 1


def test_cl01_common_acronyms_lower_case_and_api():
    m = registered(("ORG", "Pollen Diffusion Graphique"), ("ORG", "Brasseries Velanor Quimpertin"))
    out = m.mask("le PDG et la TVA ; une bvq ; BVQ").text
    assert out.startswith("le PDG et la TVA ; une bvq ; SOCIETE_")
    assert nm.org_acronyms("Brasseries Velanor Quimpertin SAS") == ["BVQ"]
    assert nm.org_acronyms("Pollen Diffusion Graphique") == []  # "PDG" is a common acronym


def test_cl01_two_companies_with_one_acronym_are_left():
    m = registered(("ORG", "Brasseries Velanor Quimpertin"), ("ORG", "Bureau Vertical Quorum"))
    assert "BVQ a vendu" in m.mask("BVQ a vendu.").text


# --- CL-02: initials of a registered person --------------------------------------------------------------------


def test_cl02_dotted_initials_anywhere():
    m = registered(("PERSON", "Ludovic Pradimont"), ("PERSON", "Anne-Lise Vorgane"))
    out = m.mask("Paraphes : L. P. / A.-L. V.\nRelu par L.P. le matin.").text
    assert out == "Paraphes : PERSONNE_A / PERSONNE_B\nRelu par PERSONNE_A le matin."


def test_cl02_two_letter_group_only_in_an_initials_context():
    m = registered(("PERSON", "Ludovic Pradimont"))
    out = m.mask("Fichier 2025-ABC-0442 LP\n[LP] à revoir\nLP/MD\nLP est un sigle ici.").text
    assert out.count("PERSONNE_A") == 3
    assert "LP est un sigle ici." in out


def test_cl02_three_letter_group_and_common_abbreviations():
    m = registered(("PERSON", "Jean-Luc Pradimont"), ("PERSON", "Ruben Ibarrondo"))
    out = m.mask("Note de JLP. Joindre un RIB et un PV.").text
    assert out == "Note de PERSONNE_A. Joindre un RIB et un PV."  # "RIB" are the initials of no one, "RI" is common


def test_cl02_same_initials_for_two_people_are_left():
    m = registered(("PERSON", "Ludovic Pradimont"), ("PERSON", "Léon Parvatet"))
    out = m.mask("Paraphes : L. P.\nFichier 2025-ABC-0442 LP").text
    assert out == "Paraphes : L. P.\nFichier 2025-ABC-0442 LP"
    assert nm.person_initials("Ludovic Pradimont") == ["LP"]
    assert nm.person_initials("Jean-Luc de Pradimont") == ["JLP", "JLDP"]


# --- CL-03: nickname or diminutive -----------------------------------------------------------------------------


def test_cl03_prefix_diminutive_in_greeting_and_after_a_preposition():
    m = registered(("PERSON", "Stéphanie Lomarec"))
    out = m.mask("Bonjour Steph,\nvoir avec Steph demain ; Steph a appelé.").text
    assert out == "Bonjour PERSONNE_A,\nvoir avec PERSONNE_A demain ; PERSONNE_A a appelé."


def test_cl03_two_owners_or_another_real_first_name_never_take_the_code():
    m = registered(("PERSON", "Stéphanie Lomarec"), ("PERSON", "Stéphanie Brandol"))
    out = m.mask("voir avec Steph demain.").text
    assert "Steph" not in out and "PERSONNE_A" not in out and "PERSONNE_B" not in out
    m = registered(("PERSON", "Christiane Volmerac"))
    assert "Christian a signé" in m.mask("Hier, Christian a signé.").text  # a gender form, not a diminutive


def test_cl03_listed_diminutive_and_registered_people_only():
    m = registered(("PERSON", "Élisabeth Quervanec"))
    assert m.mask("Merci Babette, à demain.").text == "Merci PERSONNE_A, à demain."
    out = fresh().mask("Mme Stéphanie Lomarec signe. Hier, Steph a appelé.").text
    assert "Steph a appelé" in out  # a name found in this text only: no diminutive guess


# --- CL-04: first name alone -----------------------------------------------------------------------------------


def test_cl04a_usual_first_name_of_several_given_names():
    m = registered(("PERSON", "Aurore Maëlle Vellacrin"))
    assert m.mask("Aurore ne va pas bien.").text == "PERSONNE_A ne va pas bien."


def test_cl04b_first_name_of_two_people_gets_its_own_code():
    m = registered(("PERSON", "Lucie Duravel"), ("PERSON", "Lucie Bressant"))
    r = m.mask("Hier, Lucie a confirmé.")
    assert r.text == "Hier, PERSONNE_C a confirmé." and r.new_entities[0].value == "Lucie"
    assert m.mask("Lucie viendra aussi.").text == "PERSONNE_C viendra aussi."
    m = registered(("PERSON", "Lucie Duravel"), ("PERSON", "Lucie M. Duravel"))  # one person split in two codes
    assert m.mask("Hier, Lucie a confirmé.").text == "Hier, PERSONNE_A a confirmé."


def test_cl04c_first_name_after_an_elision():
    m = registered(("PERSON", "Aurore Vellacrin"))
    out = m.mask("Le mail d'Aurore est arrivé ; l'avis d’Aurore aussi ; qu'Aurore signe.").text
    assert "Aurore" not in out and out.count("PERSONNE_A") == 3


def test_cl04d_first_name_that_is_a_common_word():
    m = registered(("PERSON", "Claire Vandorel"))
    out = m.mask("Il faut voir avec Claire demain ; une eau claire.\nClaire viendra.").text
    assert out == "Il faut voir avec PERSONNE_A demain ; une eau claire.\nClaire viendra."  # sentence start: unsure


def test_cl04e_person_known_by_a_first_name_only():
    r = fresh().mask("Son fils Maxence est absent. Hier, Maxence refuse de venir.")
    assert r.text == "Son fils PERSONNE_A est absent. Hier, PERSONNE_A refuse de venir."
    m = registered(("PERSON", "Maxence"))
    assert m.mask("Le dossier de Maxence, puis Maxence a appelé.").text.count("PERSONNE_A") == 1


# --- CL-05: bare common-word surname ---------------------------------------------------------------------------


def test_cl05_surname_comma_first_name_header():
    m = registered(("PERSON", "Agathe Boulanger"))
    assert m.mask("De : Boulanger, Agathe\nObjet : pièces").text == "De : PERSONNE_A\nObjet : pièces"


def test_cl05_party_separator_and_mid_sentence():
    m = registered(("PERSON", "Agathe Boulanger"))
    out = m.mask("Requête Boulanger c/ Brivelor ; hier, Boulanger a écrit.").text
    assert out == "Requête PERSONNE_A c/ Brivelor ; hier, PERSONNE_A a écrit."


def test_cl05_common_noun_stays_clear():
    m = registered(("PERSON", "Agathe Boulanger"))
    text = "Le boulanger du quartier ; le Boulanger du coin.\nREQUETE BOULANGER"
    assert m.mask(text).text == text


def test_cl05_capitals_inside_a_phrase_of_a_mixed_line():
    m = registered(("PERSON", "Agathe Boulanger"), ("PERSON", "Paul Blanc"))
    out = m.mask("la requête de BOULANGER est rejetée\nCouleur : BLANC ;").text
    assert out == "la requête de PERSONNE_A est rejetée\nCouleur : BLANC ;"


# --- CL-06: one-edit typo of a registered name -----------------------------------------------------------------


def test_cl06_typo_gets_the_registered_code():
    m = registered(("PERSON", "Ludovic Pradimont"))
    r = m.mask("La famille Pradimomt est là. M. Pradimon aussi. Pradel non.")
    assert r.text == "La famille PERSONNE_A est là. M. PERSONNE_A aussi. Pradel non."
    assert r.new_entities == []


def test_cl06_typo_of_a_company_word():
    m = registered(("ORG", "Kervalen Industrie"))
    assert m.mask("Le site Kervalin a fermé.").text == "Le site SOCIETE_A a fermé."


def test_cl06_ambiguous_or_short_names_are_not_linked():
    m = registered(("PERSON", "Ludovic Pradimont"), ("PERSON", "Hugo Pradimost"))
    assert "PERSONNE_A" not in m.mask("La famille Pradimomt est là.").text
    assert "PERSONNE_B" not in m.mask("La famille Pradimomt est là.").text
    m = registered(("PERSON", "Ludovic Morel"))
    assert "PERSONNE_A" not in m.mask("Le témoin Morez est absent.").text  # under 6 letters: never a typo


# --- CL-07: compound holding a registered name -----------------------------------------------------------------


def test_cl07_hyphen_compound_with_a_strong_name_is_masked_whole():
    m = registered(("PERSON", "Hervé Lorvain"))
    r = m.mask("Mme Maëla-Lorvain est venue ; Lorvain-Kerbrat aussi ; M. Lorvain.")
    assert r.text == "Mme PERSONNE_B est venue ; PERSONNE_C aussi ; M. PERSONNE_A."
    assert sorted(e.value for e in r.new_entities) == ["Lorvain-Kerbrat", "Maëla-Lorvain"]


def test_cl07_document_words_and_weak_names_are_no_compound():
    m = registered(("PERSON", "Hervé Lorvain"), ("PERSON", "Louise Martin"))
    r = m.mask("Notes-Lorvain-2026 ; la Saint-Martin.")
    assert r.new_entities == [] and "la Saint-Martin." in r.text


def test_cl07_compound_is_one_span():
    m = registered(("ORG", "Velmora Holding"))
    r = m.mask("La marque Kestrane-Velmora progresse.")
    assert "Velmora" not in r.text and "Kestrane" not in r.text
    assert [s.value for s in r.spans] == ["Kestrane-Velmora"]


# --- CL-08: trade names ----------------------------------------------------------------------------------------


def test_cl08_compound_trade_noun():
    r = fresh().mask("la Boulangerie-Pâtisserie Mercadou ouvre.")
    assert r.text == "la Boulangerie-Pâtisserie SOCIETE_A ouvre." and r.new_entities[0].value == "Mercadou"


def test_cl08_new_trade_nouns_and_plurals():
    out = fresh().mask("la Minoterie Bastidou ; la Scierie Rouvelin ; les Brasseries Quimpertin").text
    assert out == "la Minoterie SOCIETE_A ; la Scierie SOCIETE_B ; les Brasseries SOCIETE_C"


def test_cl08_lower_case_and_institutional_words_stay_clear():
    text = "la boulangerie du village ; le Garage Municipal ; le Restaurant Universitaire."
    assert fresh().mask(text).text == text


# --- CL-09: partnership names ----------------------------------------------------------------------------------


def test_cl09_partners_joined_by_et():
    r = fresh().mask("La SCP Varenne et Maudet, avocats associés.")
    assert r.text == "La SCP SOCIETE_A, avocats associés." and r.new_entities[0].value == "Varenne et Maudet"


def test_cl09_partners_joined_by_comma_and_ampersand():
    r = fresh().mask("La SELARL Varenne, Maudet & Corlay plaide.")
    assert r.text == "La SELARL SOCIETE_A plaide."


def test_cl09_stops_at_an_article():
    r = fresh().mask("La SCP Varenne et la société Brivelor.")
    assert r.text == "La SCP SOCIETE_A et la société SOCIETE_B."


# --- CL-15: a registered birth date in another format -----------------------------------------------------------


def test_cl15_numeric_forms_of_a_registered_birth_date():
    m = registered(("BIRTHDATE", "3 mai 2016"))
    out = m.mask("date : 03/05/2016 ; 2016-05-03 ; 3.5.16").text
    assert out == "date : NAISSANCE_1 ; NAISSANCE_1 ; NAISSANCE_1"


def test_cl15_long_form_of_a_registered_numeric_date():
    m = registered(("BIRTHDATE", "01/03/1979"))
    assert m.mask("le 1er mars 1979 et le 1 mars 1979").text == "le NAISSANCE_1 et le NAISSANCE_1"


def test_cl15_other_dates_stay_clear():
    m = registered(("BIRTHDATE", "3 mai 2016"))
    text = "réunion du 04/05/2016 et du 3 juin 2016"
    assert m.mask(text).text == text


# --- CL-17: defined contractual role terms ---------------------------------------------------------------------


def test_cl17_defined_role_with_an_article_is_no_company():
    r = fresh().mask("La société Velmora SAS (ci-après dénommée « le Concessionnaire »). Le Concessionnaire s'engage.")
    assert [e.value for e in r.new_entities] == ["Velmora"]
    assert "« le Concessionnaire »" in r.text and "Le Concessionnaire s'engage." in r.text


def test_cl17_article_before_the_quotes_and_unlisted_terms():
    r = fresh().mask("ci-après dénommée « la Distributrice Agréée » ; le « Bailleur » paie.")
    assert r.new_entities == []


def test_cl17_role_noun_with_a_legal_form_is_still_a_company():
    r = fresh().mask("La société Concessionnaire SAS signe.")
    assert [e.value for e in r.new_entities] == ["Concessionnaire"]


# --- CL-18: common words masked --------------------------------------------------------------------------------


def test_cl18a_canary_keeps_the_case_of_dictionary_words():
    m = registered(("ORG", "Financière Kervalen"))
    assert m.scan("la dette financière nette ; une Financière") == []
    assert [s.value for s in m.scan("le site kervalen ferme")] == ["kervalen"]  # a distinctive name: any case


def test_cl18b_bare_m_is_a_title_only_with_the_name_on_its_line():
    r = fresh().mask("Indice 245 M\n    Horaire mensuel 151,67\nNiveau 310 M Palier haut")
    assert names_of(r, "PERSON") == []
    assert names_of(fresh().mask("M Durandeau a signé."), "PERSON") == ["Durandeau"]


def test_cl18d_generic_business_adjective_is_no_head_word():
    m = registered(("ORG", "Financière Kervalen"))
    assert m.mask("Synthèse Financière ; Kervalen").text == "Synthèse Financière ; SOCIETE_A"
    assert ("financiere",) not in {v.tokens for v in nm.org_variants("Financière Kervalen")}


# --- CL-19: all-capital instrument word read as a first name -----------------------------------------------------


def test_cl19_instrument_acronym_before_a_name():
    r = fresh().mask("Il détient 500 ORANE Talmecourt et des BSA.")
    assert not any("ORANE" in v for v in names_of(r)) and "BSA" in r.text


def test_cl19_capital_first_name_before_a_mixed_case_word():
    r = fresh().mask("La note ANNE Talmecourt est jointe.")
    assert not any("ANNE" in v for v in names_of(r, "PERSON"))


def test_cl19_real_names_still_found():
    assert names_of(fresh().mask("Jean DUPRAT signe."), "PERSON") == ["Jean DUPRAT"]
    assert names_of(fresh().mask("Orane Dulivert signe."), "PERSON") == ["Orane Dulivert"]


# --- CL-20: shared surname, qualifiers, title + first name --------------------------------------------------------


def test_cl20_father_and_son_never_merged():
    m = registered(("PERSON", "Jean-Luc Vellardin"), ("PERSON", "Bastien Vellardin"))
    r = m.mask("M. Vellardin fils et M. Vellardin père ; Vellardin a dit.")
    assert "PERSONNE_A" not in r.text and "PERSONNE_B" not in r.text
    assert sorted(e.value for e in r.new_entities) == ["Vellardin", "Vellardin fils", "Vellardin père"]
    assert nm.split_person("Vellardin fils") == ([], ["Vellardin", "fils"])


def test_cl20_shared_surname_after_a_title_gets_its_own_code():
    m = registered(("PERSON", "Perrine Morvanec"), ("PERSON", "Ghislain Morvanec"))
    out = m.mask("Mme Morvanec est là ; Ghislain Morvanec aussi.").text
    assert out == "Mme PERSONNE_C est là ; PERSONNE_B aussi."


def test_cl20_first_name_never_right_after_a_title():
    m = registered(("PERSON", "Gaspard Brévanne"), ("PERSON", "Anselme Gaspard"))
    assert m.mask("M. Gaspard est venu.").text == "M. PERSONNE_B est venu."
    m = registered(("PERSON", "Bastien Vellardin"))
    assert m.mask("M. Vellardin père et M. Vellardin.").text == "M. PERSONNE_B et M. PERSONNE_A."


# --- CL-21: family-named company -------------------------------------------------------------------------------


def test_cl21_company_context_beats_a_known_surname():
    m = registered(("PERSON", "Jean-Luc Vellardin"))
    out = m.mask("(Groupe Vellardin) ; l'entreprise Vellardin ; M. Vellardin signe.").text
    assert out == "(Groupe SOCIETE_A) ; l'entreprise SOCIETE_A ; M. PERSONNE_A signe."


def test_cl21_leading_words_of_a_long_company_name():
    m = registered(("ORG", "Lumière Froid Services"))
    assert m.mask("Lumière Froid a livré ; Lumière Froid Services aussi.").text == "SOCIETE_A a livré ; SOCIETE_A aussi."


def test_cl21_person_name_holding_a_firm_word():
    r = fresh().mask("La SCP Varenne et Maudet plaide ; Jean Varenne a signé.")
    assert r.text == "La SCP SOCIETE_A plaide ; PERSONNE_A a signé."


# --- CL-22: person rule swallows neighbours ----------------------------------------------------------------------


def test_cl22_role_word_genitive_is_no_person():
    r = fresh().mask("La gérante de LUMIERE FROID SERVICES a signé.")
    assert names_of(r, "PERSON") == [] and names_of(r, "ORG") == ["LUMIERE FROID SERVICES"]


def test_cl22_person_ends_before_de_company():
    r = fresh().mask("Kévin RAMEL de LUMIERE FROID SERVICES a signé.")
    assert names_of(r, "PERSON") == ["Kévin RAMEL"] and names_of(r, "ORG") == ["LUMIERE FROID SERVICES"]
    assert names_of(fresh().mask("Mme Hélène de LA ROCHE signe."), "PERSON") == ["Hélène de LA ROCHE"]


def test_cl22_fund_forms_make_one_company():
    r = fresh().mask("Velmora Coastal Infrastructure Fund II SCSp investit.")
    assert names_of(r, "PERSON") == [] and names_of(r, "ORG") == ["Velmora Coastal Infrastructure Fund II"]


# --- CL-23: one entity split across codes -------------------------------------------------------------------------


def test_cl23_compatible_given_names_link():
    m = registered(("PERSON", "Ombeline Maud Talvez"))
    r = m.mask("Ombeline Talvez signe.")
    assert r.text == "PERSONNE_A signe." and r.new_entities == []


def test_cl23_compound_first_name_is_another_person():
    m = registered(("PERSON", "Jean Ravelin"))
    assert m.mask("Jean-Marc Ravelin signe.").text == "PERSONNE_B signe."


def test_cl23_two_compatible_people_are_not_guessed():
    m = registered(("PERSON", "Ombeline Maud Talvez"), ("PERSON", "Ombeline Iris Talvez"))
    assert m.mask("Ombeline Talvez signe.").text == "PERSONNE_C signe."


# --- CL-29: Shield object ids ----------------------------------------------------------------------------------


def test_cl29_object_ids_are_not_escaped():
    out = fresh().mask("voir DOC_3, DOSSIER_12 et OUTPUT_2.").text
    assert out == "voir DOC_3, DOSSIER_12 et OUTPUT_2."
    assert code_like_spans("DOC_3 DOSSIER_1 OUTPUT_9") == []


def test_cl29_entity_codes_still_escaped():
    assert escape_codes("PERSONNE_A et DOC_4") == "PERSONNE-A et DOC_4"


def test_cl29_masking_a_restored_text_keeps_object_ids():
    m = fresh()
    first = m.mask("M. Florimond KERGALAN, voir DOC_7.")
    again = m.mask(m.unmask(first.text))
    assert again.text == first.text == "M. PERSONNE_A, voir DOC_7."


# --- CL-30: values stored on one line -----------------------------------------------------------------------------


def test_cl30_new_value_has_no_line_break():
    r = fresh().mask("M. Florimond\nKERGALAN a signé.")
    assert [e.value for e in r.new_entities] == ["Florimond KERGALAN"]


def test_cl30_restore_keeps_a_table_row_whole():
    m = fresh()
    r = m.mask("Témoin : M. Florimond\nKERGALAN")
    assert m.unmask("| témoin | PERSONNE_A |") == "| témoin | Florimond KERGALAN |"
    assert "\n" not in r.new_entities[0].value


def test_cl30_tabs_and_spaces_collapsed():
    r = fresh().mask("Mme Ombeline\u00a0 Talvez signe.")
    assert [e.value for e in r.new_entities] == ["Ombeline Talvez"]
