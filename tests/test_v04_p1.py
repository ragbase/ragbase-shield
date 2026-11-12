"""v0.4 P1 (policy option, OFF by default): the public tool or vendor of the English whitelist that is the
dossier's own company (the label of its main e-mail domain) is masked when the option is on. Default off: every
vendor stays readable, as before. Only that one label, for that one dossier: every other vendor stays
protected, a dossier without a clear main domain changes nothing, French text never changes. Invented data only:
every person, company, address and sentence below is made up for these tests; the vendor words are entries of the
product's own list (``en_whitelist.txt``, section [vendors])."""
from __future__ import annotations

import pytest

from ragbase_shield import config
from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import locale as lc
from ragbase_shield.engine.normalize import fold, tokens

OWN = "trello"      # the invented dossier's own company: a vendor of the list, used as its mail domain label
OTHER = "jira"      # another vendor of the list, mentioned in the texts, never the own company
NOT_VENDOR = "ploverin"  # an invented company label that is no vendor


def _eml(frm: str, to: str, body: str = "Noted.") -> tuple:
    return ("eml", f"From: {frm}\nTo: {to}\nSubject: note\n\n{body}\n".encode())


def _directory(own: str = OWN, own_count: int = 4, other_count: int = 1) -> D.Directory:
    """A directory built from invented e-mails: ``own_count`` internal mails of the company ``own`` (two addresses
    at its domain each) and ``other_count`` internal mails of an invented second company (two addresses each)."""
    people = ["Ilsa Morrow", "Teodor Vashmere", "Odra Venmoss", "Sabe Lund", "Pell Doran", "Ari Venn"]
    items = []
    for k in range(own_count):
        a, b = people[k % len(people)], people[(k + 1) % len(people)]
        items.append(_eml(f"{a} <{a.lower().replace(' ', '.')}{k}@{own}.example>",
                          f"{b} <{b.lower().replace(' ', '.')}{k}@{own}.example>"))
    for k in range(other_count):
        items.append(_eml(f"Wenna Brask <wenna.brask{k}@meadowvane.example>",
                          f"Corin Haldane <corin.haldane{k}@meadowvane.example>"))
    return D.build(items, lang="en")


def _masker(directory, option=None, lang: str = "en") -> Masker:
    if lang == "en":
        return Masker(MemoryStore(locale="en"), locale="en", language="en", use_ner=False, directory=directory,
                      own_company_vendor=option)
    return Masker(MemoryStore(locale="fr"), locale="fr", language="fr", use_ner=False, directory=directory,
                  own_company_vendor=option)


TEXT = ("Hi Wenna, Trello will review the renewal with Ilsa Morrow on Thursday, and the tickets stay in Jira "
        "until then.\nBest,\nTeodor")
TEXT2 = "The board of Trello approved the plan; please share the Jira export with Odra."


def _orgs(m: Masker) -> set[str]:
    return {e.value.lower() for e in m.store.all() if e.kind == "ORG"}


# --- setting ----------------------------------------------------------------------------------------------------


def test_setting_default_off(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", raising=False)
    assert lc.own_company_vendor_setting() is False
    assert config.own_company_vendor() is False
    for v in ("1", "true", "YES", " on "):
        monkeypatch.setenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", v)
        assert lc.own_company_vendor_setting() is True and config.own_company_vendor() is True
    for v in ("0", "no", "", "off", "maybe"):
        monkeypatch.setenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", v)
        assert lc.own_company_vendor_setting() is False


# --- lexicon ----------------------------------------------------------------------------------------------------


def test_vendors_section_belongs_to_the_whitelist():
    assert "vendors" in lc.EN_FILES["en_whitelist.txt"]
    en = lc.bundle("en")
    assert en.vendor_phrases and en.vendor_phrases <= set(en.whitelist_phrases)
    assert OWN in en.vendor_phrases and OTHER in en.vendor_phrases
    assert NOT_VENDOR not in en.vendor_phrases
    # the courts, bodies and statutes of the whitelist are not vendors
    assert set(en.whitelist_phrases) - en.vendor_phrases
    assert lc.bundle("fr").vendor_phrases == frozenset()


def test_protected_intervals_release_one_phrase():
    text = "We moved the board to Trello and the files to Jira; the Employment Tribunal asked for both."
    f = fold(text)
    ft = tokens(f.text)
    s_own, s_other, s_body = text.index("Trello"), text.index("Jira"), text.index("Employment")
    whole = lc.protected_intervals_en(text, f, ft)
    assert whole.overlaps(s_own, s_own + 6) and whole.overlaps(s_other, s_other + 4)
    assert whole.overlaps(s_body, s_body + 19)
    part = lc.protected_intervals_en(text, f, ft, release={OWN})
    assert not part.overlaps(s_own, s_own + 6)
    assert part.overlaps(s_other, s_other + 4) and part.overlaps(s_body, s_body + 19)
    # an empty release is the whole protection
    assert lc.protected_intervals_en(text, f, ft, release=()).overlaps(s_own, s_own + 6)


# --- main e-mail domain of the dossier ------------------------------------------------------------------------


def test_main_domain_label_is_the_clear_top_count():
    assert _masker(_directory())._main_domain_label() == OWN
    assert _masker(D.Directory([], {OWN: 3, NOT_VENDOR: 3}))._main_domain_label() == ""   # a tie: no main company
    assert _masker(D.Directory([], {OWN: 2, NOT_VENDOR: 5}))._main_domain_label() == NOT_VENDOR
    assert _masker(None)._main_domain_label() == ""
    assert _masker(D.Directory([], {}))._main_domain_label() == ""


# --- default: nothing changes ---------------------------------------------------------------------------------


def test_default_keeps_the_vendor_readable(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", raising=False)
    for option in (None, False):
        m = _masker(_directory(), option)
        assert m._vendor_release() == frozenset()
        out = m.mask(TEXT).text
        assert "Trello" in out and "Jira" in out
        assert "Ilsa Morrow" not in out  # the person is masked as always
        assert OWN not in _orgs(m)


# --- option on: the own company is masked, every other vendor stays readable -----------------------------------


def test_option_masks_the_own_company_vendor_only():
    m = _masker(_directory(), True)
    assert m._vendor_release() == frozenset({OWN})
    out = m.mask(TEXT).text
    assert "Trello" not in out and "Jira" in out
    assert OWN in _orgs(m) and OTHER not in _orgs(m)
    # the next text of the same dossier: the known company is masked again, the other vendor stays
    out2 = m.mask(TEXT2).text
    assert "Trello" not in out2 and "Jira" in out2


def test_option_from_the_environment(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", "1")
    m = _masker(_directory(), None)
    assert m._vendor_release() == frozenset({OWN})
    assert "Trello" not in m.mask(TEXT).text
    monkeypatch.setenv("RAGBASE_SHIELD_OWN_COMPANY_VENDOR", "0")
    m2 = _masker(_directory(), None)
    assert m2._vendor_release() == frozenset()
    assert "Trello" in m2.mask(TEXT).text


def test_option_needs_a_clear_main_domain_that_is_a_vendor():
    # the vendor is a correspondent's domain, not the main one
    m = _masker(_directory(own_count=1, other_count=3), True)
    assert m._vendor_release() == frozenset() and "Trello" in m.mask(TEXT).text
    # a tie at the top
    m = _masker(D.Directory([], {OWN: 2, "meadowvane": 2}), True)
    assert m._vendor_release() == frozenset() and "Trello" in m.mask(TEXT).text
    # the main domain is a company that is no vendor: nothing released, the list stays protected
    m = _masker(D.Directory([], {NOT_VENDOR: 6, OWN: 1}), True)
    assert m._vendor_release() == frozenset() and "Trello" in m.mask(TEXT).text
    # no directory at all
    m = _masker(None, True)
    assert m._vendor_release() == frozenset() and "Trello" in m.mask(TEXT).text


def test_option_releases_one_label_not_the_vendor_list():
    # a second vendor at a lower address count is still protected: only the main domain's label is released
    d = D.Directory([], {OWN: 5, OTHER: 2})
    m = _masker(d, True)
    assert m._vendor_release() == frozenset({OWN})
    out = m.mask(TEXT).text
    assert "Trello" not in out and "Jira" in out


def test_release_follows_the_directory():
    m = _masker(_directory(), True)
    assert m._vendor_release() == frozenset({OWN})
    m._directory_arg = D.Directory([], {NOT_VENDOR: 4})
    m._dir_cache = (None, None)
    assert m._vendor_release() == frozenset()


# --- French text never changes --------------------------------------------------------------------------------


@pytest.mark.parametrize("option", [False, True])
def test_french_text_is_the_same_with_and_without_the_option(option):
    text = ("Bonjour Wenna, Trello examinera le renouvellement avec Ilsa Morrow jeudi, et les tickets restent "
            "dans Jira jusque-là.\nCordialement,\nTeodor")
    ref = _masker(_directory(), False, lang="fr").mask(text).text
    out = _masker(_directory(), option, lang="fr").mask(text).text
    assert out == ref
