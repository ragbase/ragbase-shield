"""v0.4 T3 (PLAN_V04 2.3, CRITIC 4): company evidence beats a person reading. Invented data only.

- OM1, firm names: "Name & Co." and "Name and Company" are company names in the English rules (the connector and
  the word belong to the name), never across a lower-case word, never "and Company Secretary" (an office);
- OM1, company mailbox: the directory makes no person from an address whose local part spells the label of a
  shared company domain; the display name (and its last word) is registered as the company, so it stays masked;
- OM2, one-word company label that is also a person's name: decided per mention (company cues against person
  cues), and by the export's own majority when the mention has no cue;
- fail closed: a person reading that company evidence beats becomes the company; it is never dropped;
- English only: a French text keeps the old rules.
"""
from __future__ import annotations

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import locale as lc
from ragbase_shield.engine import masker as M
from ragbase_shield.engine import names as nm

FIRM = "ploverin.example"


def _eml(frm: str, to: str, body: str = "Noted.") -> tuple:
    return ("eml", f"From: {frm}\nTo: {to}\nSubject: note\n\n{body}\n".encode())


def _rules(text: str) -> list[tuple[str, str, str]]:
    return [(r.kind, text[r.start:r.end], r.rule) for r in nm.detect_names(text, lang="en")]


def _masker(directory) -> Masker:
    return Masker(MemoryStore(locale="en"), locale="en", use_ner=False, directory=directory)


def _spans(m: Masker, texts: list[str], target: str) -> list[tuple[str, str]]:
    """(kind, surface) of the spans of ``target`` after a pass over ``texts`` (the dossier) and ``target``."""
    for t in texts + [target]:
        m.mask(t)
    r = m.mask(target)
    return [(s.kind, target[s.start:s.end]) for s in r.spans]


# --- OM1: firm names with "& Co." or "and Company" -----------------------------------------------------------

@pytest.mark.parametrize("text,surface", [
    ("Our counsel Tharvel & Company signed the deal.", "Tharvel & Company"),
    ("Contract with Quessard and Company, Inc. was renewed.", "Quessard and Company"),
    ("Signed by Ombrevane & Co. yesterday.", "Ombrevane & Co."),
    ("Brokerage services by Ilvane Corsetti & Co., Inc. are listed.", "Ilvane Corsetti & Co."),
])
def test_firm_name_with_connector_form(text, surface):
    assert ("ORG", surface, "legal_form") in _rules(text)


def test_firm_name_never_crosses_a_lower_case_word():
    text = "Attendees were Wenna Brask and Teodor Vashmere for Ilvane Corsetti and Company, and others."
    orgs = [s for k, s, _r in _rules(text) if k == "ORG"]
    assert orgs == ["Ilvane Corsetti and Company"]


def test_company_office_is_not_a_firm_name():
    text = "Wenna Brask and Company Secretary Teodor Vashmere met."
    assert not [s for k, s, _r in _rules(text) if k == "ORG"]


def test_lower_case_company_is_not_a_firm_word():
    assert not [s for k, s, _r in _rules("Tharvel and company left early.") if k == "ORG"]


def test_org_core_drops_the_english_connector_before_the_form():
    assert nm.org_core("Quessard and Company") == "Quessard"
    assert nm.org_core("Ombrevane & Co.").rstrip(" &") == "Ombrevane"
    assert nm.org_core("Tharvel and Quessard") == "Tharvel and Quessard"  # a name with "and" inside keeps it


# --- OM1: company mailbox ----------------------------------------------------------------------------------

def _mailbox_items(extra_local: tuple[str, ...] = ("wenna.brask", "teodor.vashmere")) -> list:
    items = [_eml("Corin Ploverin <corin.ploverin@corinploverin.example>", "Wenna Brask <wenna.brask@corinploverin.example>")]
    for local in extra_local:
        first, last = local.split(".")
        items.append(_eml(f"{first.title()} {last.title()} <{local}@corinploverin.example>",
                          "Wenna Brask <wenna.brask@corinploverin.example>"))
    return items


def test_company_mailbox_is_no_person():
    d = D.build(_mailbox_items(), lang="en")
    assert [p.value for p in d.persons] == ["Wenna Brask", "Teodor Vashmere"]
    assert d.orgs == ["Corin Ploverin", "Ploverin"]
    assert not d.lookup("Ploverin")


def test_personal_domain_keeps_its_person():
    # one address at the domain: a personal domain, not a company mailbox
    d = D.build([_eml("Corin Ploverin <corin.ploverin@corinploverin.example>", "Wenna Brask <wenna.brask@other.example>")],
                lang="en")
    assert "Corin Ploverin" in [p.value for p in d.persons]
    assert d.orgs == []


def test_first_name_equal_to_the_label_stays_a_person():
    items = [_eml(f"{n.title()} Brask <{n}.brask@{FIRM}>", f"Corvel Thimbrask <corvel.thimbrask@{FIRM}>")
             for n in ("ploverin", "wenna", "teodor")]
    d = D.build(items, lang="en")
    assert "Ploverin Brask" in [p.value for p in d.persons]
    assert d.orgs == []


def test_directory_round_trip_keeps_orgs():
    d = D.build(_mailbox_items(), lang="en")
    back = D.Directory.from_dict(d.to_dict())
    assert back.orgs == d.orgs
    assert "orgs" not in D.Directory([D.Person("Wenna Brask", ("wenna",), ("brask",))]).to_dict()


def test_seed_registers_the_mailbox_name_as_a_company():
    d = D.build(_mailbox_items(), lang="en")
    store = MemoryStore(locale="en")
    d.seed(store)
    kinds = {(e.kind, e.value) for e in store.all()}
    assert ("ORG", "Corin Ploverin") in kinds and ("ORG", "Ploverin") in kinds
    assert ("PERSON", "Corin Ploverin") not in kinds


def test_company_mailbox_name_stays_masked():
    # fail closed: without its person the name must still be masked (as the company)
    d = D.build(_mailbox_items(), lang="en")
    m = _masker(d)
    texts = ["I have copied Corin Ploverin on this thread.", "The Ploverin team agreed.", "Corin Ploverin expects it."]
    for t in texts:
        m.mask(t)
    for t in texts:
        out = m.mask(t).text
        assert "Ploverin" not in out, out


def test_company_mailbox_name_keeps_its_declared_initials_masked():
    dom = "quorinploverin.example"
    d = D.build([_eml(f"Quorin Ploverin <quorin.ploverin@{dom}>", f"Wenna Brask <wenna.brask@{dom}>"),
                 _eml(f"Teodor Vashmere <teodor.vashmere@{dom}>", f"Wenna Brask <wenna.brask@{dom}>")], lang="en")
    assert d.orgs[:1] == ["Quorin Ploverin"]
    m = _masker(d)
    t = "Feedback | Quorin Ploverin (QP), Territory Manager, North"
    m.mask(t)
    r = m.mask(t)
    assert ("ORG", "QP") in [(s.kind, t[s.start:s.end]) for s in r.spans]


# --- OM2: one-word company label that is also a first name --------------------------------------------------

# the label is a first name of the English lexicon, so the e-mail domain rule needs a company cue for it
LABEL_PERSON = {"value": "Adelina Corsetti", "given": ["adelina"], "family": ["corsetti"],
                "emails": ["adelina.corsetti@adelina.example"]}


@pytest.fixture()
def label_dir() -> D.Directory:
    assert "adelina" in lc.bundle("en").all_first_names
    return D.Directory.from_dict({"persons": [LABEL_PERSON], "domains": {"adelina": 40}})


def _kind_of(spans: list[tuple[str, str]], word: str) -> set[str]:
    return {k for k, s in spans if s == word}


@pytest.mark.parametrize("text", [
    "She moved from Adelina to a startup last year.",
    "The Adelina team will review the draft.",
    "Adelina's revenue grew in the second quarter.",
    "ADELINA CONFIDENTIAL",
    "region,account\nNorth,Adelina",
])
def test_label_with_company_cue_is_the_company(label_dir, text):
    word = "ADELINA" if "ADELINA" in text else "Adelina"
    assert _kind_of(_spans(_masker(label_dir), [], text), word) == {"ORG"}


@pytest.mark.parametrize("text", [
    "Hi Adelina, the deck is ready.",
    "Adelina Corsetti signed it.",
    "Best,\n\nAdelina",
])
def test_label_with_person_cue_stays_the_person(label_dir, text):
    spans = _spans(_masker(label_dir), [], text)
    assert spans and all(k == "PERSON" for k, s in spans if "Adelina" in s)


def test_label_in_a_row_with_its_family_name_stays_the_person(label_dir):
    text = "first,last,role\nAdelina,Corsetti,Director"
    assert _kind_of(_spans(_masker(label_dir), [], text), "Adelina") == {"PERSON"}


def test_label_without_cue_follows_the_export_majority(label_dir):
    dossier = ["We buy from Adelina every month.", "The Adelina team called.", "ADELINA PRICING", "Prices at Adelina rose."]
    target = "Adelina expects the order next week."
    assert _kind_of(_spans(_masker(label_dir), dossier * 2, target), "Adelina") == {"ORG"}
    # with no company cue anywhere in the export, the person reading stays
    assert _kind_of(_spans(_masker(label_dir), [], target), "Adelina") <= {"PERSON"}


# --- fail closed: company evidence relabels, never drops ---------------------------------------------------

def test_first_last_with_company_evidence_stays_masked():
    # "Adelina Vashmere" reads as a person, but the export shows it as a company (its squeezed e-mail domain
    # label): the span becomes the company; v0.3 dropped it and left the name in clear
    d = D.Directory.from_dict({"persons": [], "domains": {"adelinavashmere": 30}})
    m = _masker(d)
    t = "Adelina Vashmere expects the filing by Friday."
    m.mask(t)
    r = m.mask(t)
    assert [(s.kind, t[s.start:s.end]) for s in r.spans] == [("ORG", "Adelina Vashmere")]


# --- org_head: a dossier first name that opens a company name ----------------------------------------------

def test_dossier_first_name_is_no_company_head_word():
    d = D.Directory.from_dict({"persons": [{"value": "Ilvane Corsetti", "given": ["ilvane"], "family": ["corsetti"]}],
                               "domains": {}})
    m = _masker(d)
    m.mask("Brokerage services by Ilvane Tharvel & Co. are listed.")
    ev = m._evidence()
    assert (ev.get("ilvane") or {}).get("org_head", 0) == 0
    assert (ev.get("ilvane tharvel") or {}).get("org", 0) >= 1


def test_dossier_first_name_before_a_company_word_stays_a_head_word():
    d = D.Directory.from_dict({"persons": [{"value": "Ilvane Corsetti", "given": ["ilvane"], "family": ["corsetti"]}],
                               "domains": {}})
    m = _masker(d)
    m.mask("Freight is handled by Ilvane Logistics Inc. this year.")
    assert (m._evidence().get("ilvane") or {}).get("org_head", 0) >= 1


# --- English only --------------------------------------------------------------------------------------------

def test_french_text_never_runs_the_label_rule(label_dir, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("English rule ran on French text")

    monkeypatch.setattr(M.Masker, "_label_mentions_en", boom)
    m = Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False, directory=label_dir)
    m.mask("Bonjour, la société Adelina a signé le contrat avec Maître Corsetti hier à Lyon.")



# --- vault evidence fields ---------------------------------------------------------------------------------

def test_vault_accepts_label_cue_evidence():
    from ragbase_shield import vault as V

    assert "label_org" in V._EVIDENCE_FIELDS and "label_person" in V._EVIDENCE_FIELDS
