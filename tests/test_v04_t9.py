"""v0.4 T9 (English, NER mode only): the model-only finds the dossier does not support are not masked.

OM10 a company of one common word, G3 a reference code read as a login, an account or a staff number (or, with a
digit, as a name), G4 a person of one common word; the same for a one-word mention of a longer name that only the
model found. Evidence keeps the mask: a rule reading, a context cue, an e-mail domain, an owner word before a code,
an entity of the store, a name of the directory. Rules mode and French text never change. Invented data only: every
name, company, code and sentence below is made up for these tests."""
from __future__ import annotations

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import ner as nr

# formal text that writes "granite" in lower case in mid-sentence: the dossier makes it a common word
FORMAL = ("The survey team logged the granite samples, the granite ledger and the granite blocks for the "
          "west wing, then sent the granite report to the board.")
# filler of ordinary sentences, long enough to put two sightings of a name in two model chunks
FILLER = " ".join(["The weekly review covered the schedule, the open tasks and the next steps for the team."] * 16)


class _Backend:
    """A fake model: fixed finds (surface, model label, score) wherever the surface occurs in a chunk."""

    name = "callable:t9"

    def __init__(self, finds):
        self.finds = list(finds)
        self.labels = {"company": "ORG", "person": "PERSON", "username": "USERNAME",
                       "account_number": "ACCOUNT_NUMBER", "employee_id": "EMPLOYEE_ID"}
        self.thresholds = {label: 0.4 for label in self.labels}

    def predict(self, chunks):
        out = []
        for ch in chunks:
            spans = []
            for surface, label, score in self.finds:
                i = ch.find(surface)
                while i >= 0:
                    spans.append(nr.NerSpan(i, i + len(surface), label, score))
                    i = ch.find(surface, i + 1)
            out.append(spans)
        return out


def _masker(finds, store=None, locale="en"):
    st = store if store is not None else MemoryStore(locale=locale)
    if locale == "en":
        m = Masker(st, locale="en", language="en", use_ner=False)
    else:
        m = Masker(st, locale=locale, use_ner=False)
    m.use_ner = True  # no model in the test environment: the fake backend stands in for it
    m._backend = _Backend(finds)
    m._backend_tried = True
    return m, st


def _no_t9(m):
    """The same masker without T9 (to show that a test checks T9 and not an earlier guard)."""
    m._t9_gate = lambda text, cands: cands
    m._t9_drop_reason = lambda text, d: ""
    return m


# ---------------------------------------------------------------------------------------------------------------
# OM10: a company of one common word
# ---------------------------------------------------------------------------------------------------------------

def test_one_common_word_company_of_the_model_alone_is_not_masked():
    text = "The numbers came from Forecast this morning for a second look."
    m, st = _masker([("Forecast", "company", 0.9)])
    assert "Forecast" in m.mask(text).text
    assert st.get_by_norm("ORG", "forecast") is None
    m0, _st0 = _masker([("Forecast", "company", 0.9)])
    assert "Forecast" not in _no_t9(m0).mask(text).text


def test_an_email_domain_of_the_text_keeps_the_same_word_masked():
    m, _st = _masker([("Forecast", "company", 0.9)])
    r = m.mask("The numbers came from Forecast this morning (contact: ops@forecast.example).")
    assert "from Forecast" not in r.text, r.text


def test_a_distinctive_one_word_company_of_the_model_stays_masked():
    m, _st = _masker([("Vellquist", "company", 0.9)])
    r = m.mask("The numbers came from Vellquist this morning for a second look.")
    assert "Vellquist" not in r.text, r.text


def test_a_word_the_dossier_writes_in_lower_case_is_common_for_the_gate():
    m, _st = _masker([("Granite", "company", 0.9)])
    m.mask(FORMAL)
    assert "Granite" in m.mask("The files came from Granite on Friday.").text


def test_an_entity_made_before_the_evidence_loses_its_mentions_later():
    m, _st = _masker([("Granite", "company", 0.9)])
    first = m.mask("The files came from Granite on Friday.")
    assert "Granite" not in first.text  # no evidence yet: the model find is kept (the gate needs evidence to drop)
    m.mask(FORMAL)
    again = m.mask("The files came from Granite on Friday.")
    assert "Granite" in again.text, again.text


def test_user_entity_is_never_refused():
    st = MemoryStore(locale="en")
    st.add("ORG", "Forecast", "forecast", source="user")
    m, _st = _masker([("Forecast", "company", 0.9)], store=st)
    r = m.mask("The numbers came from Forecast this morning for a second look.")
    assert "Forecast" not in r.text, r.text


# ---------------------------------------------------------------------------------------------------------------
# one-word mentions of a longer name of the model alone
# ---------------------------------------------------------------------------------------------------------------

def test_common_word_alone_of_a_model_company_is_not_masked_its_whole_name_stays():
    finds = [("Granite Vellquist", "company", 0.95)]
    text = "Granite Vellquist signed the lease. " + FILLER + " Granite Vellquist paid. Then Granite called."
    m, _st = _masker(finds)
    m.mask(FORMAL)
    r = m.mask(text)
    assert "Granite Vellquist" not in r.text and "Then Granite called" in r.text, r.text
    m0, _st0 = _masker(finds)
    _no_t9(m0).mask(FORMAL)
    assert "Then Granite called" not in m0.mask(text).text


def test_mention_that_only_two_model_companies_own_is_not_masked():
    finds = [("Granite Hall", "company", 0.95), ("Granite Works", "company", 0.95)]
    text = ("Granite Hall and Granite Works met. " + FILLER + " Granite Hall paid, Granite Works too. "
            "Then Granite left early.")
    m, _st = _masker(finds)
    m.mask(FORMAL)
    r = m.mask(text)
    assert "Then Granite left" in r.text and "Granite Hall" not in r.text, r.text


# ---------------------------------------------------------------------------------------------------------------
# G4: one common word as a person
# ---------------------------------------------------------------------------------------------------------------

def test_one_common_word_person_of_the_model_alone_is_not_masked():
    m, _st = _masker([("Granite", "person", 0.9)])
    m.mask(FORMAL)
    assert "Granite" in m.mask("I spoke with Granite yesterday.").text


def test_a_greeting_keeps_the_person_for_the_whole_session():
    m, _st = _masker([("Granite", "person", 0.9)])
    m.mask(FORMAL)
    assert "Granite" not in m.mask("Thanks, Granite").text
    assert "Granite" not in m.mask("I spoke with Granite yesterday.").text


# ---------------------------------------------------------------------------------------------------------------
# G3: reference codes
# ---------------------------------------------------------------------------------------------------------------

def test_reference_code_of_the_model_alone_is_not_an_account_or_a_login():
    finds = [("QX-TRV-71", "account_number", 0.9), ("KLM-PLN-4", "username", 0.9)]
    text = "Ticket ref QX-TRV-71 was filed under plan KLM-PLN-4 yesterday."
    m, _st = _masker(finds)
    r = m.mask(text)
    assert "QX-TRV-71" in r.text and "KLM-PLN-4" in r.text, r.text
    m0, _st0 = _masker(finds)
    r0 = _no_t9(m0).mask(text)
    assert "QX-TRV-71" not in r0.text and "KLM-PLN-4" not in r0.text, r0.text


def test_an_owner_word_keeps_the_code_masked_for_the_whole_session():
    m, _st = _masker([("QX-TRV-71", "employee_id", 0.9)])
    assert "QX-TRV-71" not in m.mask("Please update the badge QX-TRV-71 before Monday.").text
    assert "QX-TRV-71" not in m.mask("Ticket ref QX-TRV-71 was filed yesterday.").text


def test_a_code_with_a_digit_read_as_a_company_is_not_masked():
    m, _st = _masker([("QX-TRV-71", "company", 0.9)])
    assert "QX-TRV-71" in m.mask("The numbers came from QX-TRV-71 this morning.").text


def test_digit_only_account_number_stays_masked():
    m, _st = _masker([("4418-2290-77", "account_number", 0.9)])
    r = m.mask("Ticket reference: 4418-2290-77 for the transfer.")
    assert "4418-2290-77" not in r.text, r.text


# ---------------------------------------------------------------------------------------------------------------
# scope: NER mode, English only, fail closed
# ---------------------------------------------------------------------------------------------------------------

def test_rules_mode_keeps_no_t9_state():
    m = Masker(MemoryStore(locale="en"), locale="en", language="en", use_ner=False)
    m.mask("Vellquist Holdings LLC signed. The numbers came from Forecast this morning.")
    assert m._t9_model == {} and m._t9_made == set() and m._t9_minted == set()


def test_french_text_is_not_gated():
    m, _st = _masker([("Forecast", "company", 0.9)], locale="fr")
    m.mask("Le dossier est parti chez Forecast ce matin pour relecture.")
    assert m._t9_model == {}


def test_a_failure_of_the_gate_keeps_the_model_find(monkeypatch):
    m, _st = _masker([("Forecast", "company", 0.9)])

    def boom(*_a, **_k):
        raise RuntimeError("t9 test")

    monkeypatch.setattr(m, "_t9_refuted", boom)
    r = m.mask("The numbers came from Forecast this morning for a second look.")
    assert "Forecast" not in r.text, r.text
