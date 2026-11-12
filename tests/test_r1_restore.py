"""R1 corrections, owner RESTORE (classes CL-30 to CL-36 of R1_PLAN.md).

Every name, title and file name below is invented for these tests.
"""
from __future__ import annotations

import docx
import pytest

from ragbase_shield import documents as D
from ragbase_shield.engine.masker import Masker, entity_norm
from ragbase_shield.engine.types import MemoryStore
from ragbase_shield.restore_utils import (FIX_KEYS, RestoreReport, find_placeholders, find_shield_ids,
                                          restore_for_output)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _setup(*entities: tuple[str, str]):
    store = MemoryStore()
    codes = [store.add(kind, value, entity_norm(kind, value)).code for kind, value in entities]
    return Masker(store, use_ner=False), codes


def _restore(text: str, *entities: tuple[str, str], **kw) -> RestoreReport:
    m, _codes = _setup(*entities)
    return restore_for_output(text, m, **kw)


# --------------------------------------------------------------------------------- contract

def test_report_matches_unmask_report_when_nothing_to_fix():
    m, (a, b) = _setup(("PERSON", "Gontran Velquier"), ("ORG", "Brunsvald Optique"))
    text = f"Accord entre {a} et {b} ; code inconnu PERSONNE_Q ; casse fausse personne_a."
    rep = restore_for_output(text, m)
    plain, unknown = m.unmask_report(text)
    assert rep.text == plain
    assert rep.unknown_codes == unknown == ["PERSONNE_Q", "personne_a"]
    assert rep.restored == 2
    assert set(rep.fixes) == set(FIX_KEYS) and not any(rep.fixes.values())


def test_public_report_holds_no_value_and_repr_hides_text():
    rep = _restore("voir PERSONNE_A et DOC_3 [SOCIETE]", ("PERSON", "Gontran Velquier"),
                   id_labels={"DOC_3": "Bail Velquier signé.pdf"})
    pub = rep.public()
    flat = repr(pub)
    assert "Velquier" not in flat and "Bail" not in flat
    assert pub["ids_replaced"] == ["DOC_3"] and pub["placeholders"] == ["[SOCIETE]"]
    assert "Velquier" not in repr(rep)


def test_empty_text():
    m, _ = _setup(("PERSON", "Gontran Velquier"))
    rep = restore_for_output("", m)
    assert rep.text == "" and rep.restored == 0 and rep.placeholders == [] and rep.shield_ids == []


# --------------------------------------------------------------------------------- CL-30 line breaks

def test_line_break_in_value_keeps_table_row_whole():
    rep = _restore("| Rôle | Nom |\n|---|---|\n| témoin | PERSONNE_A |\n| expert | autre |",
                   ("PERSON", "Ombrine\nVELASTRE"))
    lines = rep.text.split("\n")
    assert lines[2] == "| témoin | Ombrine VELASTRE |"
    assert len(lines) == 4
    assert rep.fixes["line_break"] == 1


def test_line_break_in_value_inside_a_paragraph_becomes_a_space(tmp_path):
    rep = _restore("Le rapport de PERSONNE_A est daté.", ("PERSON", "Sixtine \n  PELLEMONT"))
    assert rep.text == "Le rapport de Sixtine PELLEMONT est daté."
    out = D.write_docx(tmp_path / "x.docx", rep.text, "DOSSIER_1")
    assert "Sixtine PELLEMONT" in docx.Document(str(out)).paragraphs[0].text


def test_hyphen_at_line_end_inside_value():
    rep = _restore("A : PERSONNE_A. B : SOCIETE_A.", ("PERSON", "Aldric POMEREUX-\nLAVAUR"),
                   ("ORG", "Distille-\nries Varnoult"))
    assert "Aldric POMEREUX-LAVAUR" in rep.text      # capital after the break: a compound name
    assert "Distilleries Varnoult" in rep.text       # lower case after the break: one word cut in two
    assert rep.fixes["line_break"] == 2


def test_docx_writer_joins_a_table_row_split_by_a_line_break(tmp_path):
    md = "| Nom | Rôle |\n|---|---|\n| Eudoxie\nGARVADEC | partie |\n| autre | témoin |\n"
    out = D.write_docx(tmp_path / "t.docx", md, "DOSSIER_1")
    rows = [[c.text for c in r.cells] for r in docx.Document(str(out)).tables[0].rows]
    assert rows == [["Nom", "Rôle"], ["Eudoxie GARVADEC", "partie"], ["autre", "témoin"]]


def test_docx_writer_does_not_join_a_paragraph_after_an_open_row(tmp_path):
    md = "| Nom | Rôle |\n|---|---|\n| autre | témoin\nUn paragraphe qui suit.\n"
    doc = docx.Document(str(D.write_docx(tmp_path / "t.docx", md, "DOSSIER_1")))
    assert len(doc.tables[0].rows) == 2
    assert any(p.text == "Un paragraphe qui suit." for p in doc.paragraphs)


# --------------------------------------------------------------------------------- CL-31 placeholders

def test_placeholders_are_listed_per_occurrence():
    rep = _restore("La société [SOCIETE] et [SOCIETE] avec PERSONNE_A.", ("PERSON", "Gontran Velquier"))
    assert rep.placeholders == ["[SOCIETE]", "[SOCIETE]"]
    assert rep.public()["placeholders"] == ["[SOCIETE]", "[SOCIETE]"]


def test_placeholders_in_english_and_markdown_escaped():
    assert find_placeholders(r"signed by \[PERSON\] at [ADDRESS] for [COMPANY]") == \
        ["[PERSON]", "[ADDRESS]", "[COMPANY]"]


def test_no_placeholder_and_other_brackets_ignored():
    rep = _restore("Voir [annexe 2] et [NOTE] puis PERSONNE_A.", ("PERSON", "Gontran Velquier"))
    assert rep.placeholders == []


# --------------------------------------------------------------------------------- CL-32 elision

def test_de_becomes_d_before_a_vowel():
    rep = _restore("Le courrier de PERSONNE_A et le rapport de SOCIETE_A.",
                   ("PERSON", "Isaure Quarnevic"), ("ORG", "Ostréa Velmont"))
    assert rep.text == "Le courrier d'Isaure Quarnevic et le rapport d'Ostréa Velmont."
    assert rep.fixes["elision"] == 2


def test_elision_keeps_case_and_the_text_apostrophe():
    rep = _restore("De PERSONNE_A. QUE PERSONNE_A. l’avis de PERSONNE_A ; puisque PERSONNE_A",
                   ("PERSON", "Isaure Quarnevic"))
    assert rep.text == ("D’Isaure Quarnevic. QU’Isaure Quarnevic. l’avis d’Isaure Quarnevic ; "
                        "puisqu’Isaure Quarnevic")


def test_d_becomes_de_before_a_consonant():
    rep = _restore("Le dossier d'PERSONNE_A et qu’**PERSONNE_A** signe.", ("PERSON", "Barnabé Quesnoir"))
    assert rep.text == "Le dossier de Barnabé Quesnoir et que **Barnabé Quesnoir** signe."
    assert rep.fixes["elision"] == 2


def test_no_elision_before_h_y_vowel_or_other_kinds():
    rep = _restore("de PERSONNE_A, de PERSONNE_B, de PERSONNE_C, de EMAIL_1, Unde PERSONNE_C",
                   ("PERSON", "Hermance Dolbreuil"), ("PERSON", "Yannig Rostagne"), ("PERSON", "Yvain Rostagne"),
                   ("EMAIL", "isaure@exemple.test"))
    assert rep.text == ("de Hermance Dolbreuil, de Yannig Rostagne, d'Yvain Rostagne, de isaure@exemple.test, "
                        "Unde Yvain Rostagne")


# --------------------------------------------------------------------------------- CL-33 name form

def test_surname_first_value_restores_in_natural_order():
    rep = _restore("Monsieur PERSONNE_A,\nVotre dossier.", ("PERSON", "QUILLEBRECQ Anatole"))
    assert rep.text.startswith("Monsieur Anatole QUILLEBRECQ,")
    assert rep.fixes["name_order"] == 1


def test_capitals_value_gets_first_name_case_only_when_clear():
    rep = _restore("Pour PERSONNE_A et PERSONNE_B.", ("PERSON", "ANATOLE QUILLEBRECQ"),
                   ("PERSON", "GONTRAN AMBROISE"))
    assert rep.text == "Pour Anatole QUILLEBRECQ et GONTRAN AMBROISE."  # two first names: order unknown


def test_natural_order_values_unchanged():
    rep = _restore("PERSONNE_A, PERSONNE_B, M. PERSONNE_C", ("PERSON", "Anatole Quillebrecq"),
                   ("PERSON", "QUILLEBRECQ"), ("PERSON", "VELMONTAIS Zorvic"))
    assert rep.text == "Anatole Quillebrecq, QUILLEBRECQ, M. VELMONTAIS Zorvic"  # unknown first name: no guess
    assert rep.fixes["name_order"] == 0


def test_birth_name_marker_restores_the_surname_only():
    rep = _restore("Mme PERSONNE_A, née PERSONNE_B ; nom de naissance : PERSONNE_B",
                   ("PERSON", "Philomène Garvadec"), ("PERSON", "Philomène Trabolec"))
    assert rep.text == "Mme Philomène Garvadec, née Trabolec ; nom de naissance : Trabolec"
    assert rep.fixes["birth_name"] == 2


def test_first_name_written_before_the_code_is_not_doubled():
    rep = _restore("Bonjour Philomène PERSONNE_A,\nla Société SOCIETE_A et le Groupe SOCIETE_B ; Velmont SOCIETE_C",
                   ("PERSON", "Philomène Garvadec"), ("ORG", "Société Brunsvald"), ("ORG", "Groupe Ostral"),
                   ("ORG", "Velmont Ingénierie"))
    assert rep.text == ("Bonjour Philomène Garvadec,\nla Société Brunsvald et le Groupe Ostral ; "
                        "Velmont Velmont Ingénierie")  # a distinctive word is never dropped for a company
    assert rep.fixes["doubled_word"] == 3


def test_legal_form_written_before_the_code_is_not_doubled():
    rep = _restore("la SAS SOCIETE_A ; la sas SOCIETE_A ; de SOCIETE_A SAS", ("ORG", "Ostréa Velmont SAS"))
    assert rep.text == "la SAS Ostréa Velmont ; la sas Ostréa Velmont SAS ; d'Ostréa Velmont SAS"


# --------------------------------------------------------------------------------- CL-34 numbered lists

def _displayed_numbers(doc) -> list[tuple[str, str]]:
    """(number Word shows, paragraph text) for each numbered paragraph: start of its numbering instance + rank."""
    numbering = doc.part.numbering_part.element
    seen: dict[int, int] = {}
    out = []
    for par in doc.paragraphs:
        ppr = par._p.pPr
        if ppr is None or ppr.numPr is None or ppr.numPr.numId is None:
            continue
        nid = ppr.numPr.numId.val
        num = numbering.num_having_numId(nid)
        so = num.find(f"{W}lvlOverride/{W}startOverride")
        start = int(so.get(f"{W}val")) if so is not None else 1
        rank = seen.get(nid, 0)
        seen[nid] = rank + 1
        abstract = next(a for a in numbering.iterchildren(f"{W}abstractNum")
                        if a.get(f"{W}abstractNumId") == str(num.abstractNumId.val))
        level_text = abstract.find(f"{W}lvl/{W}lvlText").get(f"{W}val")
        out.append((level_text.replace("%1", str(start + rank)), par.text))
    return out


def test_two_lists_both_restart_at_one(tmp_path):
    md = "1. pièce une\n2. pièce deux\n\nTexte entre les listes.\n\n1. demande une\n2. demande deux\n"
    doc = docx.Document(str(D.write_docx(tmp_path / "l.docx", md, "DOSSIER_1")))
    assert _displayed_numbers(doc) == [("1.", "pièce une"), ("2.", "pièce deux"),
                                       ("1.", "demande une"), ("2.", "demande deux")]
    assert all(p.style.name == "List Number" for p in doc.paragraphs if p.text.startswith(("pièce", "demande")))


def test_written_numbers_are_kept(tmp_path):
    md = "15. quinzième point\n16. seizième point\n\n1. premier\n2. deuxième\n5. cinquième\n"
    doc = docx.Document(str(D.write_docx(tmp_path / "l.docx", md, "DOSSIER_1")))
    assert [n for n, _t in _displayed_numbers(doc)] == ["15.", "16.", "1.", "2.", "5."]


def test_parenthesis_lists_and_decimal_headings(tmp_path):
    md = "1) option une\n2) option deux\n\n4.1 Calendrier\n4.2 Budget\n"
    doc = docx.Document(str(D.write_docx(tmp_path / "l.docx", md, "DOSSIER_1")))
    assert _displayed_numbers(doc) == [("1)", "option une"), ("2)", "option deux")]
    assert any(p.text == "4.1 Calendrier\n4.2 Budget" for p in doc.paragraphs)


def test_nested_list_restarts_under_each_parent(tmp_path):
    md = "1. parent un\n   1. enfant a\n   2. enfant b\n2. parent deux\n   1. enfant c\n"
    doc = docx.Document(str(D.write_docx(tmp_path / "l.docx", md, "DOSSIER_1")))
    assert [n for n, _t in _displayed_numbers(doc)] == ["1.", "1.", "2.", "2.", "1."]


# --------------------------------------------------------------------------------- CL-35 file names

def test_long_file_name_cut_at_a_word_boundary_with_extension():
    title = " ".join(["Conclusions récapitulatives Quarnevic"] * 8)
    name = D.safe_filename(title, "docx")
    stem = name[:-len(".docx")]
    assert name.endswith(".docx") and len(stem) <= D.MAX_STEM_CHARS
    assert title.startswith(stem) and title[len(stem)] == " "


def test_cut_file_name_drops_a_dangling_function_word():
    title = "Note " + "a" * 108 + " sur la demande de"   # the cut lands after "sur la"
    stem = D.safe_filename(title, "md")[:-3]
    assert not stem.endswith((" sur", " la", " de")) and stem.endswith("a")
    assert D.trim_dangling("Mémoire en réponse de l’") == "Mémoire en réponse"
    assert D.trim_dangling("Lettre à") == "Lettre"


def test_short_file_name_unchanged_and_byte_limit_respected():
    assert D.safe_filename("Lettre à la partie adverse", "docx") == "Lettre à la partie adverse.docx"
    title = " ".join(["éèêéèê"] * 30)
    stem = D.safe_filename(title, "md")[:-3]
    assert len(stem.encode("utf-8")) <= D.MAX_STEM_BYTES and title.startswith(stem)
    assert title[len(stem)] == " "


def test_title_cut_before_a_restored_value_never_inside_it():
    m, (a,) = _setup(("ORG", "Velquier Brunsvald Optique Industrielle de Précision"))
    title = "Projet de lettre de mise en demeure adressée au conseil de la partie adverse dans " \
            f"le dossier {a}"
    rep = restore_for_output(title, m, max_chars=D.MAX_STEM_CHARS)
    assert rep.truncated and len(rep.text) <= D.MAX_STEM_CHARS
    assert "Velquier" not in rep.text and rep.text.endswith("dossier")
    short = restore_for_output(f"Note {a}", m, max_chars=D.MAX_STEM_CHARS)
    assert short.text == "Note Velquier Brunsvald Optique Industrielle de Précision" and not short.truncated


# --------------------------------------------------------------------------------- CL-36 Shield ids

def test_shield_ids_replaced_by_local_labels():
    rep = _restore("Voir DOC_2 du DOSSIER_4 et la note OUTPUT_3 ; aussi DOC\\_2.", ("PERSON", "Gontran Velquier"),
                   id_labels={"DOC_2": "Avenant Ostral.pdf", "DOSSIER_4": "Velquier c. Ostral",
                              "OUTPUT_3": "Note interne.docx"})
    assert rep.text == ("Voir Avenant Ostral.pdf du Velquier c. Ostral et la note Note interne.docx ; "
                        "aussi Avenant Ostral.pdf.")
    assert rep.ids_replaced == ["DOC_2", "DOSSIER_4", "OUTPUT_3", "DOC_2"] and rep.shield_ids == []


def test_unknown_shield_id_stays_and_is_reported():
    rep = _restore("Voir DOC_2 et DOC_9.", ("PERSON", "Gontran Velquier"), id_labels={"DOC_2": "Pièce une.pdf"})
    assert rep.text == "Voir Pièce une.pdf et DOC_9."
    assert rep.shield_ids == ["DOC_9"]


def test_without_labels_every_id_is_reported_and_kept():
    rep = _restore("DOSSIER_1, DOC_12 et OUTPUT_7 ; PERSONNE_A ; MYDOC_3 et DOC_4b restent du texte.",
                   ("PERSON", "Gontran Velquier"))
    assert rep.shield_ids == ["DOSSIER_1", "DOC_12", "OUTPUT_7"]
    assert "DOSSIER_1, DOC_12 et OUTPUT_7" in rep.text and rep.ids_replaced == []
    assert find_shield_ids("DOC_2 DOC＿5") == ["DOC_2", "DOC_5"]
    bad = _restore("Voir DOC_2.", ("PERSON", "Gontran Velquier"), id_labels={"FICHIER_2": "x", "DOC_2": "  "})
    assert bad.text == "Voir DOC_2." and bad.shield_ids == ["DOC_2"]


@pytest.mark.parametrize("kind", ["PERSON", "ORG"])
def test_elision_not_applied_to_a_word_glued_to_the_previous_value(kind):
    value = "Isaure Quarnevic" if kind == "PERSON" else "Ostréa Velmont"
    code = "PERSONNE_A" if kind == "PERSON" else "SOCIETE_A"
    rep = _restore(f"{code}de {code}", (kind, value))
    assert rep.text == f"{value}de {value}"
