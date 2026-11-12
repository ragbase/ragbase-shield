"""v0.4 T4 (PLAN_V04 2.3, OM4 / OM9 / O1): the forms of a company named by an e-mail domain. Invented data only.

- a run of capitalised words whose letters, joined, spell an e-mail domain label ("Grelmont Quay" for
  grelmontquay.example), also with a spelled legal form for its short form ("Ostrel Company" for ostrelco);
- ampersand initials of a short label ("V&K" for vk.example), never a business abbreviation ("R&D");
- a camel-case word that is the label ("tZorvel"), in any text;
- the label or its squeezed run in lower case in chat text only (or with a legal form after it), never a dictionary
  word or a first name, never inside an address, a host, a path or a file name;
- a person of the dossier named like a domain stays a person;
- the words of a known address or host written as prose are not that address (the company rules read them);
- side effects kept small: no place-name head variant for a domain-form company, no common-word head variant for a
  company seen only in lower case, no initials in hyphenated codes for either;
- English only: a French text keeps the old rules.
"""
from __future__ import annotations

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import masker as M
from ragbase_shield.engine import names as nm

LABELS = ["grelmontquay", "ostrelco", "vk", "rd", "tzorvel", "orchard", "olivia", "pacificquay", "meadowvane"]


def _rules(text: str, domains=LABELS) -> list[tuple[str, str, str]]:
    return [(r.kind, text[r.start:r.end], r.rule) for r in nm.detect_names(text, lang="en", domains=domains)]


def _forms(text: str, domains=LABELS) -> list[str]:
    return [s for k, s, r in _rules(text, domains) if k == "ORG" and r in ("domain_form", "domain")]


def _eml(frm: str, to: str, body: str = "Noted.") -> tuple:
    return ("eml", f"From: {frm}\nTo: {to}\nSubject: note\n\n{body}\n".encode())


def _directory(extra: tuple = ()) -> D.Directory:
    items = [
        _eml("Wenna Brask <wenna.brask@ploverin.example>", "Teodor Vashmere <teodor.vashmere@grelmontquay.example>"),
        _eml("Teodor Vashmere <teodor.vashmere@grelmontquay.example>", "Ilsa Morrow <ilsa.morrow@grelmontquay.example>"),
        _eml("Pell Doran <pell.doran@vk.example>", "Wenna Brask <wenna.brask@ploverin.example>"),
        _eml("Sabe Lund <sabe.lund@tzorvel.example>", "Wenna Brask <wenna.brask@ploverin.example>"),
        _eml("Odra Venmoss <odra.venmoss@pacificquay.example>", "Wenna Brask <wenna.brask@ploverin.example>"),
        _eml("Ari Venn <ari.venn@meadowvane.example>", "Wenna Brask <wenna.brask@ploverin.example>"),
    ] + list(extra)
    return D.build(items, lang="en")


def _masker(directory=None) -> Masker:
    return Masker(MemoryStore(locale="en"), locale="en", use_ner=False,
                  directory=directory if directory is not None else _directory())


def _spans(m: Masker, texts: list[str], target: str) -> list[tuple[str, str]]:
    for t in texts:
        m.mask(t)
    r = m.mask(target)
    return [(s.kind, target[s.start:s.end]) for s in r.spans]


# --- squeezed runs of capitalised words -----------------------------------------------------------------------

@pytest.mark.parametrize("text,surface", [
    ("Lena from Grelmont Quay sent the draft.", "Grelmont Quay"),
    ("The Grelmont Quay's team will call.", "Grelmont Quay"),
    ("We met Ostrel Company in March.", "Ostrel Company"),
    ("Invoice from Ostrel Co for the audit.", "Ostrel Co"),
    ("Our former colleague went ex-Grelmont Quay last year.", "Grelmont Quay"),
])
def test_squeezed_run_spells_the_label(text, surface):
    assert surface in _forms(text)


def test_possessive_form_that_spells_the_label():
    assert _forms("Supplies from Varnell's depot arrived.", domains=["varnells"]) == ["Varnell's"]
    assert _forms("Supplies from Varnell's depot arrived.", domains=["varnell"]) == ["Varnell"]
    assert _forms("Supplies from Varnell's Depot arrived.", domains=["varnellsdepot"]) == ["Varnell's Depot"]


def test_squeezed_run_needs_the_whole_label():
    assert _forms("Grelmont alone and Quay alone are not it.") == []
    assert _forms("Lena from Grelmont Quay sent it.", domains=["grelmontquays"]) == []


def test_squeezed_run_never_after_a_title():
    assert "Grelmont Quay" not in _forms("Dear Mr. Grelmont Quay, thank you.")


def test_squeezed_run_needs_five_letters():
    assert _forms("A note from Ab Cd today.", domains=["abcd"]) == []


# --- ampersand initials ---------------------------------------------------------------------------------------

def test_ampersand_initials_spell_a_short_label():
    assert _forms("Offer from V&K for the role. V & K is hiring.") == ["V&K", "V & K"]


def test_business_ampersand_abbreviations_are_never_a_company():
    assert _forms("The R&D budget and the M&A review.", domains=["rd", "ma"]) == []


def test_ampersand_initials_need_the_label():
    assert _forms("Offer from Q&Z for the role.") == []


# --- camel case -----------------------------------------------------------------------------------------------

def test_camel_case_label_in_any_text():
    assert _forms("We renewed the tZorvel contract.") == ["tZorvel"]


# --- lower case in chat ---------------------------------------------------------------------------------------

def test_lower_case_label_and_run_in_chat():
    text = "hey team, the grelmontquay deck is late. talk to grelmont quay tomorrow"
    assert _forms(text) == ["grelmontquay", "grelmont quay"]


def test_lower_case_label_outside_chat_needs_a_legal_form():
    assert _forms("The renewal with tzorvel was signed.") == []
    assert _forms("The renewal with tzorvel LLC was signed.") == ["tzorvel"]


def test_lower_case_dictionary_word_or_first_name_label_is_not_taken():
    assert _forms("ok the orchard plan is fine, ask olivia") == []


@pytest.mark.parametrize("text", [
    "send it to jo@grelmontquay.example asap",
    "see www.grelmontquay.example for the deck",
    "the file grelmontquay.pdf is in the folder",
    "posted in #grelmontquay-ops just now",
    "path is /shared/grelmontquay/q3 ok",
])
def test_lower_case_label_never_inside_an_address_host_path_or_handle(text):
    assert _forms(text) == []


# --- the masker: persons, prose addresses, side effects ------------------------------------------------------

def test_squeezed_run_is_masked_as_the_company():
    m = _masker()
    assert ("ORG", "Grelmont Quay") in _spans(m, [], "Lena from Grelmont Quay sent the draft.")


def test_a_dossier_person_named_like_a_domain_stays_a_person():
    d = _directory((_eml("Dorian Hale <dorian@dorianhale.example>", "Wenna Brask <wenna.brask@ploverin.example>"),
                    _eml("Dorian Hale <dorian@dorianhale.example>", "Ilsa Morrow <ilsa.morrow@grelmontquay.example>")))
    m = _masker(d)
    got = _spans(m, [], "Thanks to Dorian Hale for the review.")
    assert ("PERSON", "Dorian Hale") in got
    assert not [s for k, s in got if k == "ORG"]


def test_words_of_a_known_host_written_as_prose_are_the_company():
    d = _directory((_eml("Lumo Rask <lumo@hexlo.ai>", "Wenna Brask <wenna.brask@ploverin.example>"),))
    m = _masker(d)
    got = _spans(m, ["Visit hexlo.ai for the deck."], "Contact: Lumo Rask, CEO, Hexlo AI.")
    assert not [s for k, s in got if k == "URL"]
    assert ("ORG", "Hexlo") in got


def test_words_of_a_known_address_written_as_prose_are_not_the_address():
    m = _masker()
    texts = ["Best,\nNell\nIntake Desk, Quillmar Co\nintake.desk@quillmar.co"]
    got = _spans(m, texts, "Thanks,\nNell\nIntake Desk, Quillmar Co")
    assert not [s for k, s in got if k == "EMAIL"]
    assert ("ORG", "Quillmar") in got
    real = m.mask("Write to intake.desk@quillmar.co today.")
    assert any(s.kind == "EMAIL" for s in real.spans)


def test_written_as_words():
    assert M._written_as_words("Intake Desk, Quillmar Co", "EMAIL")
    assert not M._written_as_words("intake.desk@quillmar.co", "EMAIL")
    assert M._written_as_words("Hexlo AI", "URL")
    assert not M._written_as_words("hexlo.ai", "URL")
    assert not M._written_as_words("Hexlo AI", "PERSON")


def test_place_head_word_of_a_domain_form_company_is_the_place():
    m = _masker()
    got = _spans(m, ["Our partner Pacific Quay signed."], "We sailed the Pacific coast; Pacific Quay paid.")
    assert ("ORG", "Pacific Quay") in got
    assert ("ORG", "Pacific") not in got


def test_common_head_word_of_a_lower_case_company_is_a_word():
    m = _masker()
    got = _spans(m, ["ok so meadow vane wants the logs"], "Meadow paths open in May.")
    assert not [s for k, s in got if k == "ORG"]


def test_domain_form_company_gives_no_initials_in_codes():
    m = _masker()
    got = _spans(m, ["Lena from Grelmont Quay sent the draft."], "Schematic GQ-2041-B is approved.")
    assert ("ORG", "GQ") not in got


def test_domain_label_min_len():
    assert nm._domain_label("vk.example") == ""
    assert nm._domain_label("vk.example", min_len=2) == "vk"
    assert nm._domain_label("vk", min_len=2) == "vk"


# --- English only ---------------------------------------------------------------------------------------------

def test_french_text_keeps_the_old_rules():
    assert nm.domain_form_spans("Rendez-vous chez Grelmont Quay demain.", LABELS, "fr") == []
    got = [(k, r) for k, _s, r in [(r.kind, "", r.rule) for r in nm.detect_names(
        "Rendez-vous chez Grelmont Quay demain.", lang="fr", domains=LABELS)]]
    assert ("ORG", "domain_form") not in got


def test_french_masker_keeps_prose_address_matches():
    # the v0.3 reading stays in French: the words of a known address are still that address (no T4 change)
    m = Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False)
    m.mask("Écrire à contact.cabinet@vorelmar.fr pour le dossier.")
    t = "Merci, Contact Cabinet, Vorelmar Fr"
    assert [(s.kind, t[s.start:s.end]) for s in m.mask(t).spans] == [("EMAIL", "Contact Cabinet, Vorelmar Fr")]
