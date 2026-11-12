"""v0.3.1 synthetic mode: the two leak causes of RESULTS_V03 section 6 (owner SYNTH).

Cause A: a nickname or short form of a known person was written unchanged ("Reggie" of a real "Reginald ...").
Cause B: a short fake form (the "E." of a fake "Veronica E.") was looked for in source text and hid real values.

Every name, number and address below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import re

import pytest

from ragbase_shield.engine import Masker, MemoryStore, Synthesizer
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import masker as mk
from ragbase_shield.engine import synthetic as sy
from ragbase_shield.engine.masker import entity_norm
from ragbase_shield.engine.normalize import fold_word

SEED = b"v031-synthetic-test-seed-0123456789abcdef"
_RUN = re.compile(r"[^\W\d_]+")


def _store(*entities: tuple[str, str]):
    st = MemoryStore(locale="en")
    return st, [st.add(k, v, entity_norm(k, v)) for k, v in entities]


def _words(s: str) -> set[str]:
    return {fold_word(r) for r in _RUN.findall(s)}


def _first(fake: str) -> str:
    return fake.split()[0]


# ------------------------------------------------------------------------------------------ cause A: renderer

def test_nickname_of_a_table_is_written_as_the_fake_first_given_name():
    st, (a,) = _store(("PERSON", "Reginald Quillmore"))
    s = Synthesizer(SEED, "en", st)
    fake = s.value_for(a)
    for surface, need in (("Reggie", "dir"), ("Reggie", ""), ("Reg", "first"), ("REGGIE", "")):
        out = s.render(a, fake, surface, need)
        assert fold_word(out) == fold_word(_first(fake)), (surface, out)
        assert "reg" not in fold_word(out)
    assert s.render(a, fake, "Reggie Quillmore", "joined") == fake  # nickname + family name
    assert s.render(a, fake, "Quillmore, Reggie", "comma") == f"{fake.split()[1]}, {_first(fake)}"


def test_a_word_that_maps_to_nothing_is_the_given_name_for_a_given_form_else_the_code():
    st, (a,) = _store(("PERSON", "Reginald Quillmore"))
    s = Synthesizer(SEED, "en", st)
    fake = s.value_for(a)
    # "Tobo" is in no table: linked by the masker as a given-name form, it is the fake's first given name
    assert s.render(a, fake, "Tobo", "dir") == _first(fake)
    # linked any other way, it is never copied: the leak check fails closed (the masker writes the code)
    with pytest.raises(sy.SyntheticLeak) as ei:
        s.render(a, fake, "Tobo", "")
    assert a.code in str(ei.value) and "tobo" not in str(ei.value).lower()


def test_directory_nicknames_are_read_by_the_renderer_and_never_used_as_fakes():
    st, (a, b) = _store(("PERSON", "Reginald Quillmore"), ("PERSON", "Hester Vaudrelle"))
    s = Synthesizer(SEED, "en", st)
    s.use_nicknames(lambda value: ("tobo",) if value == "Reginald Quillmore" else ())
    fa, fb = s.value_for(a), s.value_for(b)
    assert s.render(a, fa, "Tobo", "") == _first(fa)
    # no fake ever uses a nickname of a real given name: the tables' forms and the declared ones
    banned = {"tobo", "reg", "reggie"}
    assert not (_words(fa) | _words(fb)) & banned
    idx = s._index()
    assert {"tobo", "reg", "reggie"} <= idx.real_nicks


def test_a_fake_that_uses_a_real_nickname_is_redrawn():
    st, (a, b) = _store(("PERSON", "Hester Vaudrelle"), ("PERSON", "Reginald Quillmore"))
    s = Synthesizer(SEED, "en", st)
    s.value_for(a)
    st.set_synthetic(a.code, "Reggie Ellingworth")  # a stale fake that writes a nickname of the real Reginald
    reasons = dict(s.collisions_with_store())
    assert "nickname" in reasons.get(a.code, "")
    assert "reggie" not in _words(s.value_for(a))


def test_leak_guard_flags_any_unchanged_mention_word_whatever_its_length():
    st, (a, o) = _store(("PERSON", "Reginald Quillmore"), ("ORG", "Ostrevane Mercantile PLC"))
    s = Synthesizer(SEED, "en", st)
    fa, fo = s.value_for(a), s.value_for(o)
    assert s._leaks(a, fa, "Reg", "Reg") is not None          # 3 letters, not a word of the stored value
    assert s._leaks(a, fa, "Bo", "Bo") is not None            # 2 letters
    assert s._leaks(a, fa, "Dr Reggie", "Dr " + _first(fa)) is None   # a title stays
    assert s._leaks(a, fa, "Quillmore's", fa.split()[1] + "'s") is None  # the "s" of a possessive stays
    assert s._leaks(o, fo, "Ostrevane PLC", s.render(o, fo, "Ostrevane PLC")) is None  # the legal form stays
    # the masker's own canary, independent of the renderer
    assert mk._synthetic_leaks(a, "Reggie", "Reggie")
    assert mk._synthetic_leaks(a, "Thanks Reggie", "Thanks Reggie")
    assert not mk._synthetic_leaks(a, _first(fa), "Reggie")
    assert not mk._synthetic_leaks(o, fo, "Ostrevane Mercantile PLC")
    assert not mk._synthetic_leaks(a, "Regg")  # without the mention: the v0.3 rule only (4+ letters)


def test_initials_of_the_mention_are_compared_at_their_place():
    st, (a,) = _store(("PERSON", "Branwick Ostrogarec"))
    s = Synthesizer(SEED, "en", st)
    fake = s.value_for(a)
    out = s.render(a, fake, "B. O.")
    assert out != "B. O." and out[0] != "B" and out[3] != "O"
    assert not sy.unchanged_mention_word("PERSON", "B. O.", "I. B.", "Branwick Ostrogarec")
    assert sy.unchanged_mention_word("PERSON", "B. O.", "B. K.", "Branwick Ostrogarec")


def test_a_capitalised_particle_that_opens_a_name_is_a_given_name():
    st, (a, b) = _store(("PERSON", "Al Quillmore"), ("PERSON", "Maelle de Kestbury"))
    s = Synthesizer(SEED, "en", st)
    fa, fb = s.value_for(a), s.value_for(b)
    assert "al" not in _words(fa) and len(fa.split()) == 2  # replaced, word count kept
    assert " de " in fb  # a particle inside a name stays
    assert s.render(b, fb, "De Kestbury").startswith("De ")  # the value holds it as a particle: fixed
    assert s._leaks(a, fa, "Al", "Al") is not None  # a rendering that copied "Al" is caught
    assert mk._synthetic_leaks(a, "Al " + fa.split()[1], "Al Quillmore")


# ------------------------------------------------------------------------------------------ cause A: masker

def _directory_masker():
    d = D.Directory(persons=[D.Person("Reginald Quillmore", ("reginald",), ("quillmore",), ("tobo",))])
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, directory=d, replacement="codes")
    return m, st


def test_masker_writes_the_fake_first_name_for_a_directory_nickname():
    m, st = _directory_masker()
    docs = ["From: Reginald Quillmore\nThe memo is ready.", "Thanks Tobo, see you at noon."]
    for t in docs:  # pass 1: the export is registered in codes mode (as the runner and the service do)
        m.mask(t)
    m.replacement = "synthetic"
    out = [m.mask(t) for t in docs]
    fake = st.synthetic("PERSON_A")
    assert "Tobo" not in out[1].text and out[1].text == f"Thanks {_first(fake)}, see you at noon."
    assert out[1].codes == ["PERSON_A"]
    assert m.unmask(out[0].text) == docs[0]


# ------------------------------------------------------------------------------------------ cause B

def test_fake_initials_only_where_the_real_value_has_one_and_never_a_dossier_initial():
    people = ["Mirabeth T.", "C. Quillmore", "D. Quillmore", "Hester Vaudrelle", "Corwin Ostrevane", "J. P. Kestrelby"]
    st, ents = _store(*[("PERSON", p) for p in people])
    s = Synthesizer(SEED, "en", st)
    dossier = {fold_word(r) for p in people for r in _RUN.findall(p) if len(r) == 1}
    fakes = {e.value: s.value_for(e) for e in ents}
    seen: list[str] = []
    for real, fake in fakes.items():
        ones = [fold_word(r) for r in _RUN.findall(fake) if len(r) == 1]
        assert len(ones) == len([r for r in _RUN.findall(real) if len(r) == 1]), (real, fake)
        assert not set(ones) & dossier, (real, fake)
        seen.extend(ones)
    assert len(seen) == len(set(seen))  # free letters were left: no two fakes share an initial


def test_a_stale_fake_initial_that_is_a_dossier_initial_is_redrawn():
    st, (a, c) = _store(("PERSON", "Mirabeth T."), ("PERSON", "C. Quillmore"))
    s = Synthesizer(SEED, "en", st)
    s.value_for(a)
    st.set_synthetic(a.code, "Veronica C.")
    assert "initial" in dict(s.collisions_with_store()).get(a.code, "")
    assert not {"c", "t"} & {fold_word(r) for r in _RUN.findall(s.value_for(a)) if len(r) == 1}


def _fake_in_store(real: str, fake: str):
    """A codes-mode masker over a store that holds one real person and a fake value of the same shape."""
    st, (e,) = _store(("PERSON", real))
    st.set_synthetic(e.code, fake)
    m = Masker(st, locale="en", language="en", use_ner=False, replacement="codes")
    assert m._synthetic_values()[e.code][1] == fake  # the fake is safe against the store: it stays
    return m, st


def test_one_letter_and_initial_only_fake_forms_are_never_hits_when_masking():
    m, st = _fake_in_store("Mirabeth T. Tavener", "Veronica E. Lansdowne")
    text = "Table: E. Quillmore | V. E. L. | Veronica Lansdowne"
    masking = [text[s:e] for s, e, _ent, _f in m._synthetic_hits(text, masking=True)]
    restore = [text[s:e] for s, e, _ent, _f in m._synthetic_hits(text)]
    assert "E" not in masking and "E." not in masking and "V. E. L." not in masking
    assert "Veronica Lansdowne" in masking
    assert "V. E. L." in restore  # the restore path keeps every form


def test_no_synthetic_lookup_on_a_source_document():
    m, st = _fake_in_store("Mirabeth Tavener", "Veronica Lansdowne")
    text = "Lansdowne Row is closed on Fridays."  # a source text that happens to hold a fake word
    # codes mode, a source document: the fake surname is left alone (v0.3 replaced it by PERSON_A)
    assert "PERSON_A" not in m.mask(text).text
    # a model answer masked again (keep_known_codes=True): the known fake surface becomes its code
    assert "PERSON_A" in m.mask(text, keep_known_codes=True).text
    # an answer that writes a whole fake value is recognised without the flag
    assert m.mask("Veronica Lansdowne may call. Lansdowne agreed.").text.count("PERSON_A") == 2


def test_a_hit_never_removes_a_longer_real_candidate(monkeypatch):
    m, st = _fake_in_store("Mirabeth Tavener", "Veronica Lansdowne")
    text = "Mr. Corwin Ostrevane signed. Veronica Lansdowne agreed."
    planted = text.index("Corwin")

    def hits(self, t, values=None, *, masking=False):  # a stale short hit inside the real name
        out = [(planted, planted + 6, st.get_by_code("PERSON_A"), "Veronica Lansdowne")]
        v = t.index("Veronica")
        return out + [(v, v + 18, st.get_by_code("PERSON_A"), "Veronica Lansdowne")]

    monkeypatch.setattr(Masker, "_synthetic_hits", hits)
    out = m.mask(text, keep_known_codes=True).text
    assert "Ostrevane" not in out and "Corwin" not in out
    assert "PERSON_A agreed" in out  # the whole fake, alone, is still a known fake surface


def test_codes_mode_of_a_source_document_does_not_depend_on_the_fake_values():
    text = "Mr. Corwin Ostrevane met E. Quillmore and Ms. Hester Vaudrelle at Ostrevane Mercantile PLC."
    st1, st2 = MemoryStore(locale="en"), MemoryStore(locale="en")
    plain = Masker(st1, locale="en", language="en", use_ner=False).mask(text).text
    m2 = Masker(st2, locale="en", language="en", use_ner=False, replacement="synthetic")
    m2.mask("Ms. Mirabeth Tavener signed. Mr. Quentin E. Hollowell agreed.")
    assert any(st2.synthetic(e.code) for e in st2.all())
    codes = Masker(st2, locale="en", language="en", use_ner=False).mask(text).text
    # the same masking; only the code letters differ (the second store already holds two people)
    assert re.sub(r"_[A-Z]+\b", "_X", codes) == re.sub(r"_[A-Z]+\b", "_X", plain)


def test_synthetic_mode_masks_a_table_of_initials_next_to_a_fake_initial():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, replacement="codes")
    rows = ["Ms. Mirabeth T. joined.",
            "Name | Role\nC. Quillmore | Auditor\nD. Quillmore | Clerk\nMr. Corwin Quillmore"]
    for t in rows:
        m.mask(t)
    m.replacement = "synthetic"
    outs = [m.mask(t).text for t in rows]
    assert "Quillmore" not in outs[1] and "Mirabeth" not in outs[0]
    for e in st.all():
        fake = st.synthetic(e.code) or ""
        assert not {"c", "d", "t"} & {fold_word(r) for r in _RUN.findall(fake) if len(r) == 1}, (e.value, fake)
