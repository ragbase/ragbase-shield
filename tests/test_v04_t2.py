"""v0.4 T2 (PLAN_V04 2.3, CRITIC 4): chat names, quoted nicknames, greeting and sign-off slots. Invented data only.

- K1: a lower-case directory first name or nickname in chat needs no cue when it is a three-letter form that is no
  common word; a form that is a common word is refused when the words around it read it as a function word, a
  noun or a verb; chat abbreviations and words the export shows as a company never pass (``Masker._chat_form_ok``);
- K3: a nickname between single quotes or brackets inside a name stays in the name; a person span never cuts
  through a pair of quotes (``locale._runs``, ``locale._quote_trim``);
- K7: capitalised short forms, diminutives and common-word first names of a correspondent in a greeting, sign-off
  or "goes by" slot (``Masker._name_slot``, ``Masker._dir_slot_ok``, the "dir_slot" forms of ``_dir_refs``);
- English only: a French text keeps the old rules.
"""
from __future__ import annotations

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import locale as lc
from ragbase_shield.engine import masker as M
from ragbase_shield.engine import synthetic as S

DOMAIN = "quillmere.example"


def _user(first: str, last: str, display: str = "", domain: str = DOMAIN) -> dict:
    handle = f"{first}.{last}".lower()
    return {"name": handle, "real_name": f"{first} {last}",
            "profile": {"display_name": display or first, "first_name": first, "last_name": last,
                        "email": f"{handle}@{domain}"}}


USERS = [
    _user("Lisette", "Merriwen"),
    _user("Kestrella", "Varnholt", display="Kes"),
    _user("Hopewell", "Wrexley", display="Hope"),
    _user("Willoughby", "Corwin", display="Will"),
    _user("Teverell", "Brandquist", display="Tev", domain="tev.example"),
    _user("Ezri", "Vantorre", display="Ez"),
    _user("Williamina", "Tressider", display="Williamina"),
]


@pytest.fixture(scope="module")
def directory() -> D.Directory:
    return D.build([("slack_users", USERS)], lang="auto")


def _masked(directory, texts: list[str], target: str) -> list[str]:
    """Surfaces of the PERSON spans of ``target`` after a pass over ``texts`` (the dossier) and ``target``."""
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False, directory=directory)
    for t in texts + [target]:
        m.mask(t)
    r = m.mask(target)
    return [target[s.start:s.end] for s in r.spans if s.kind == "PERSON"]


# --- K1: lower-case directory forms in chat ------------------------------------------------------------------

def test_k1_short_directory_form_in_chat_needs_no_cue(directory):
    t = "ok so kes already pushed the draft, can you check it"
    assert "kes" in _masked(directory, [], t)


def test_k1_common_word_form_as_a_name_is_masked(directory):
    t = "yeah hope said the draft goes out friday"
    assert "hope" in _masked(directory, [], t)


@pytest.mark.parametrize("t", [
    "i hope the draft goes out friday",          # subject pronoun before: a verb
    "the hope is that it ships friday lol",       # determiner before: a noun
    "ok will do, sending it now",                 # a stop word: never a name alone
    "hope the client signs it this week",         # clause start, object after: a verb
])
def test_k1_function_noun_or_verb_reading_is_refused(directory, t):
    masked = [w.lower() for w in _masked(directory, [], t)]
    assert "hope" not in masked and "will" not in masked


def test_k1_company_evidence_wins_without_a_cue(directory):
    # "tev" is also the domain label of the correspondents' addresses: company evidence wins, a cue still decides
    assert "tev" not in _masked(directory, [], "ok tev pushed the fix to the shared drive")
    assert "tev" in _masked(directory, [], "thanks tev, that works")


def test_k1_chat_abbreviation_is_never_a_name(directory):
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False, directory=directory)
    m._lang = "en"
    t = "lol sure, send it over"
    assert not m._chat_form_ok(t, 3, "lol", False, "")


def test_k1_needs_chat_like_text(directory):
    t = "Status Report\nThe draft from kes was reviewed.\nNext Steps\nSign-off pending."
    assert "kes" not in _masked(directory, [], t)


def test_k1_french_text_keeps_the_cue_rule(directory):
    t = "bon on verra avec kes demain pour le dossier du client, la réunion est confirmée"
    assert "kes" not in _masked(directory, [], t)


# --- K3: quoted nicknames ------------------------------------------------------------------------------------

@pytest.mark.parametrize("t,full", [
    ("Owner: Ottilie 'Otti' Brannoch, Director - Operations", "Ottilie 'Otti' Brannoch"),
    ("Owner: Ottilie ‘Otti’ Brannoch, Director - Operations", "Ottilie ‘Otti’ Brannoch"),
    ("Owner: Cornelius (Neil) Quenby, Director - Operations", "Cornelius (Neil) Quenby"),
])
def test_k3_single_quoted_or_bracketed_nickname_stays_in_the_name(t, full):
    spans = [(t[x.start:x.end], x.kind) for x in lc.detect_names_en(t)]
    assert (full, "PERSON") in spans
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False)
    r = m.mask(t)
    assert full in [t[s.start:s.end] for s in r.spans]
    roles = dict((w.strip("'‘’()"), role) for w, role in m.person_roles(full))
    assert roles.get("Otti", roles.get("Neil")) == "nick"


@pytest.mark.parametrize("t", [
    'Approver | Ottilie "Otti" | Director, Operations',
    'Prepared for: Ottilie\n"Otti" Brannoch - Director',
    'D2 | Internal backfill | Octavia "Neil W." | Named shortlist',
])
def test_k3_a_person_span_never_cuts_through_a_quote_pair(t):
    store = MemoryStore(locale="en")
    m = Masker(store, locale="en", use_ner=False)
    r = m.mask(t)
    for e in store.all():
        if e.kind == "PERSON":
            assert e.value.count('"') % 2 == 0, e.value
    assert any(("Otti" in t[s.start:s.end]) or ("Neil" in t[s.start:s.end]) for s in r.spans)


def test_k3_word_after_the_nickname_must_be_a_name_word():
    t = "Lead: Ottilie 'Otti' Logistics Lead"
    spans = [t[x.start:x.end] for x in lc.detect_names_en(t)]
    assert not any("Logistics" in s for s in spans)


@pytest.mark.parametrize("t", ["Project 'Atlas' Review is due on Monday.", "Sam (Finance) said the report is late."])
def test_k3_quoted_common_words_are_not_joined(t):
    spans = [t[x.start:x.end] for x in lc.detect_names_en(t)]
    assert not any(("Atlas" in s and "Project" in s) or ("Finance" in s) for s in spans)


# --- K7: greeting, sign-off and "goes by" slots --------------------------------------------------------------

@pytest.mark.parametrize("t", [
    "Thanks for the notes, all good on my side.\n\nLis",
    "Agreed on every point.\n\n—Lis",
    "Lis,\n\nThe revised schedule is attached.",
    "Hi Cosima and Lis,\n\nPlease review the attached schedule.",
    "Cosima and Lis,\n\nPlease review the attached schedule.",
    "Looks right to me.\n\nLis\n\nLisette Merriwen\nOperations",
])
def test_k7_short_form_in_a_slot(directory, t):
    assert "Lis" in _masked(directory, [], t)


@pytest.mark.parametrize("t", [
    "The Lis Road site is closed on Monday.",
    "We met near the river. Lis water levels rose, and the LIS index fell.",
])
def test_k7_short_form_outside_a_slot_is_not_masked(directory, t):
    assert "Lis" not in _masked(directory, [], t)
    assert "LIS" not in _masked(directory, [], t)


def test_k7_two_letter_name_and_common_word_diminutive_in_slots(directory):
    assert "Ez" in _masked(directory, [], "Ez,\n\nThe schedule moved to Thursday.")
    assert "Hope" in _masked(directory, [], "Signed copies go out at four.\n\nHope")
    assert "Ez" not in _masked(directory, [], "The Ez pass lane is open on weekends.")


def test_k7_goes_by_after_the_full_name(directory):
    t = "Owner | Hopewell Wrexley (Hope) | Partner Manager"
    assert "Hope" in _masked(directory, [], t)


def test_capitalised_function_word_before_a_directory_name(directory):
    assert "Kes" in _masked(directory, [], "When Kes asked why the margin was tight, we explained it.")
    assert "Kes" not in _masked(directory, [], "The Kes fund closed its second round in May.")
    # a common word outside a slot keeps the old rule (no cue: not masked)
    assert "Hope" not in _masked(directory, [], "When Hope asked why the margin was tight, we explained it.")


def test_k7_french_text_keeps_the_old_rules(directory):
    t = "Merci pour le dossier, la réunion de demain est confirmée au cabinet.\n\nLis"
    assert "Lis" not in _masked(directory, [], t)


def test_slot_forms_are_owned_apart_and_rendered_as_given_names():
    assert "dir_slot" not in M._FIRST_NEEDS
    assert "dir_slot" in S._GIVEN_NEEDS
