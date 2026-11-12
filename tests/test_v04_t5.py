"""v0.4 T5 (PLAN_V04 2.3, FM1 / FM4 / FM5 / FM7 / FM9 / FM10): the precision core of the English rules. Invented
data only (invented people, companies, places and sentences).

- FM4 (rules): a legal form in capitals stops being a legal form when it is the prefix of a code ("LTD-78Q4"), a US
  state code after a place ("Vennick Reach, CO 81099", "Vennick Reach CO/UT"), or one code of a list of capital
  codes ("HRM, LTD and payroll"); a line-opening participle sits outside the name before a legal form
  ("Drafted for Quorvel Inc.");
- the dossier knowledge: how the formal text writes each word in mid-sentence (lower case: a common word), the
  acronyms it declares in brackets, which rule found each name; chat text gives no word evidence;
- FM1: a "First Noun" person only the first-name rules saw, whose last word is a common word or holds a digit;
- FM4 (dossier): a company found only before a legal form in capitals that a lower-case word follows, all of whose
  words are common words ("Lantern LTD bundle");
- FM5: a one-word company found only by a trigger word, whose word is a common word;
- FM7: a lower-case one-word mention that is a common word;
- FM9: an acronym variant of a company that no text of the dossier declares;
- FM10: a name of one or two words that is a place, unless a person cue or the directory says otherwise;
- fail closed: without the dossier knowledge (a new masker), the masks stay; English only.
"""
from __future__ import annotations

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import names as nm


def _orgs(text: str, lang: str = "en") -> list[tuple[str, str]]:
    return [(text[r.start:r.end], r.rule) for r in nm.detect_names(text, lang=lang) if r.kind == "ORG"]


def _masker(directory=None, language: str = "auto") -> Masker:
    if directory is None:
        return Masker(MemoryStore(locale="en"), locale="en", use_ner=False, language=language)
    return Masker(MemoryStore(locale="en"), locale="en", use_ner=False, language=language, directory=directory)


def _masked(m: Masker, texts: list[str], target: str) -> list[str]:
    """Surfaces masked in ``target`` after the dossier ``texts`` (two passes, as a dossier scan then a mask)."""
    for _ in range(2):
        for t in texts:
            m.mask(t)
    r = m.mask(target)
    return [target[s.start:s.end] for s in r.spans]


# Formal text that writes a few words in lower case in mid-sentence (the dossier's own evidence of common words).
LOWER = [
    "The weekly roster was posted on time, and the roster review found no gap in the monthly roster totals.",
    "Our committee kept the roster open, so the roster owners can check each roster entry before the audit.",
    "Each pass has a voucher and the voucher rules apply, so every voucher keeps its own code for the whole year.",
    "Guests pick a lantern size; the lantern colour is billed apart, and a lantern upgrade is rare.",
]


# --- FM4 in the English rules ----------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Ship the crates to Dock 9, Vennick Reach, CO 81099 by Friday.",
    "Granite Bay Library | Vennick Reach, CO | north yard | autumn opening",
    "Our drivers cover Vennick Reach CO/UT on the same route each week.",
])
def test_state_code_is_no_legal_form(text):
    assert not any(s.startswith("Vennick") for s, _ in _orgs(text))


def test_state_code_keeps_real_forms():
    assert ("Vennick", "legal_form") in _orgs("We signed with Vennick Co. last week.")
    assert ("Ostrabel", "legal_form") in _orgs("Ostrabel LLC agreed to the terms.")


def test_code_prefix_is_no_legal_form():
    text = "Serials on file: KP-77Q4, VN, LTD-78Q4 and MR-79Q4 are listed below."
    assert not any(s == "VN" for s, _ in _orgs(text))


@pytest.mark.parametrize("text", [
    "The night report lists one total across HRM, LTD and payroll feeds.",
    "Weekend desk | HRM, LTD, PAYX and the holiday roster | done",
])
def test_list_of_capital_codes_is_not_a_company(text):
    assert not any("HRM" in s for s, _ in _orgs(text))


def test_list_rule_keeps_a_company_before_a_comma_form():
    assert any(s == "Velltry" for s, _ in _orgs("Velltry, LTD, which signed last year, sent the file."))


def test_participle_opens_no_company_name():
    orgs = _orgs("Drafted for Quorvel Inc., Dock Office.")
    assert ("Quorvel", "legal_form") in orgs
    assert not any(s.startswith("Drafted") for s, _ in orgs)


def test_rules_unchanged_in_french():
    """The FM4 readings are English only: the French rules keep their own reading of the same text."""
    place = "Nos chauffeurs couvrent Vennick Reach CO/UT chaque semaine."
    codes = "Le rapport de nuit donne un total pour HRM, LTD et la paie."
    assert any(s == "Vennick Reach" for s, _ in _orgs(place, "fr"))
    assert any(s == "HRM" for s, _ in _orgs(codes, "fr"))
    assert not any("Vennick" in s for s, _ in _orgs(place))
    assert not any("HRM" in s for s, _ in _orgs(codes))


# --- the dossier knowledge ----------------------------------------------------------------------------------------

def test_mid_sentence_evidence_counts_formal_text_once():
    m = _masker()
    for _ in range(3):
        for t in LOWER:
            m.mask(t)
    assert m._t5_mid["roster"][0] == 6
    assert m._t5_mid["voucher"][0] == 3


def test_chat_text_gives_no_word_evidence():
    m = _masker()
    m.mask("<@U01> ok so roster and roster and roster again, the roster is fine")
    assert "roster" not in m._t5_mid


def test_declared_acronyms_are_noted():
    m = _masker()
    m.mask("Harrow Vale Systems (HVS) will ship the order next week.")
    assert "HVS" in m._t5_declared


def test_french_text_gives_no_knowledge():
    m = _masker(language="fr")
    m.mask("Le planning est clos, et le planning a été revu par le comité de la société Harrow Vale (HVS).")
    assert not m._t5_mid and not m._t5_declared and not m._t5_prov


# --- FM1: "First Noun" persons ----------------------------------------------------------------------------------

def test_first_noun_with_a_common_last_word_is_not_a_person():
    m = _masker()
    assert "Mabel Roster" not in _masked(m, LOWER, "The Mabel Roster memo went to the board today.")


def test_first_noun_with_a_digit_last_word_is_not_a_person():
    m = _masker()
    assert "Mabel K9R" not in _masked(m, [], "Order the Mabel K9R units before the season.")


def test_first_noun_with_a_person_cue_stays_a_person():
    m = _masker()
    out = _masked(m, LOWER + ["Dear Mabel Roster,\n\nThe file is attached.\n"],
                  "The Mabel Roster memo went to the board today.")
    assert "Mabel Roster" in out


def test_first_noun_without_evidence_stays_masked():
    m = _masker()
    assert "Mabel Roster" in _masked(m, [], "The Mabel Roster memo went to the board today.")


def test_directory_person_stays_a_person():
    d = D.build([("eml", b"From: Mabel Roster <mabel.roster@ploverin.example>\nTo: Ari Venn <ari.venn@vane.example>\n"
                         b"Subject: note\n\nNoted.\n")], lang="en")
    m = _masker(directory=d)
    assert "Mabel Roster" in _masked(m, LOWER, "The Mabel Roster memo went to the board today.")


# --- FM4 with the dossier evidence --------------------------------------------------------------------------------

def test_product_code_of_common_words_is_not_a_company():
    m = _masker()
    assert "Lantern" not in _masked(m, LOWER, "Lantern LTD bundle | yearly fee, yearly cap | open")


def test_product_code_without_evidence_stays_masked():
    m = _masker()
    assert "Lantern" in _masked(m, [], "Lantern LTD bundle | yearly fee, yearly cap | open")


def test_company_before_a_capital_form_and_a_lower_case_word_stays():
    m = _masker()
    assert "Ostrabel" in _masked(m, LOWER, "Ostrabel LTD agreed to the terms last week.")


# --- FM5: trigger word on a common word -------------------------------------------------------------------------

def test_trigger_on_a_common_word_is_not_a_company():
    m = _masker()
    assert "Voucher" not in _masked(m, LOWER, "The crew at Voucher checked the new totals.")


def test_trigger_without_evidence_stays_masked():
    m = _masker()
    assert "Voucher" in _masked(m, [], "The crew at Voucher checked the new totals.")


# --- FM7: lower-case common word ----------------------------------------------------------------------------------

def test_lower_case_common_word_of_a_name_is_not_masked():
    m = _masker()
    texts = LOWER + ["Mr. Kestrel Roster signed the lease on Monday."]
    out = _masked(m, texts, "Please send the roster to Roster before Friday.")
    assert "roster" not in out
    assert "Roster" in out


def test_lower_case_word_without_evidence_stays_masked():
    m = _masker()
    out = _masked(m, ["Mr. Kestrel Roster signed the lease on Monday."], "Please send the roster to Roster today.")
    assert "roster" in out


# --- FM9: undeclared acronym variants ---------------------------------------------------------------------------

def test_undeclared_acronym_is_not_masked():
    m = _masker()
    out = _masked(m, ["Harrow Vale Systems LLC sent the quote."], "HVS will ship the order next week.")
    assert "HVS" not in out


def test_declared_acronym_stays_masked():
    m = _masker()
    texts = ["Harrow Vale Systems LLC sent the quote.", "Harrow Vale Systems (HVS) confirmed the date."]
    assert "HVS" in _masked(m, texts, "HVS will ship the order next week.")


# --- FM10: places --------------------------------------------------------------------------------------------------

def test_place_first_name_alone_is_not_the_person():
    m = _masker()
    texts = ["The Savannah Pell memo was sent to the board.", "Our team met the board on Monday."]
    out = _masked(m, texts, "The board said Savannah will host the spring launch.")
    assert "Savannah" not in out


def test_place_head_word_alone_is_not_the_company():
    m = _masker()
    texts = ["We hired Spokane Ridge Partners for the audit."]
    out = _masked(m, texts, "The team flew to Spokane on Monday for the audit.")
    assert "Spokane" not in out
    assert "Spokane Ridge Partners" in _masked(m, texts, "We paid Spokane Ridge Partners in full.")


def test_place_head_word_of_a_strong_company_stays():
    m = _masker()
    texts = ["Spokane Ridge LLC sent the invoice."]
    assert "Spokane" in _masked(m, texts, "The team flew to Spokane on Monday for the audit.")


def test_place_name_with_a_greeting_stays_a_person():
    m = _masker()
    assert "Savannah" in _masked(m, ["Hi Savannah,\n\nThe file is ready.\n"], "Hi Savannah,\n\nThanks again.\n")


def test_first_noun_that_opens_with_the_company_label_is_the_company():
    d = D.build([("eml", b"From: Ari Venn <ari.venn@mabel.example>\nTo: Odra Venmoss <odra.venmoss@mabel.example>\n"
                         b"Subject: note\n\nNoted.\n"),
                 ("eml", b"From: Odra Venmoss <odra.venmoss@mabel.example>\nTo: Pell Doran <pell.doran@mabel.example>\n"
                         b"Subject: note\n\nNoted.\n")], lang="en")
    m = _masker(directory=d)
    target = "Please send the Mabel Logistics notes to the board."
    for _ in range(2):
        m.mask(target)
    r = m.mask(target)
    assert [(s.kind, target[s.start:s.end]) for s in r.spans if "Mabel" in target[s.start:s.end]] == \
        [("ORG", "Mabel Logistics")]
