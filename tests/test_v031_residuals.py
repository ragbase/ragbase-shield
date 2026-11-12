"""v0.3.1 synthetic mode: the two leak classes the integrator's leak check still found after the SYNTH fixes.

1. A particle word that ends a name is a given name or a nickname, never a particle. A person stored with a cut
   value that ends with a quoted nickname which is also a particle word (the shape 'Firstname "Del') kept that word
   in its fake, so every mention of the nickname alone was written unchanged. A particle always comes before another
   name word ("van" in "Ysolde van Quorrow").
2. A number of two or more digits of a real name is never written again: a company fake keeps the numbers of the
   real name ("317 Quorrow" drawn as "317 ..."), so the masker's leak guard fails closed (the code).

Every name and number below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import re

from ragbase_shield.engine import Masker, MemoryStore, Synthesizer
from ragbase_shield.engine import masker as mk
from ragbase_shield.engine import synthetic as sy
from ragbase_shield.engine.masker import entity_norm
from ragbase_shield.engine.normalize import fold_word

SEED = b"v031-particle-test-seed-0123456789abcdef"
CUT = 'Delphinia "Del'
PLAIN = "Ysolde van Quorrow"


def _words(s: str) -> set[str]:
    return {fold_word(r) for r in re.findall(r"[^\W\d_]+", s)}


def _store():
    st = MemoryStore(locale="en")
    a = st.add("PERSON", CUT, entity_norm("PERSON", CUT))
    b = st.add("PERSON", PLAIN, entity_norm("PERSON", PLAIN))
    return st, a, b


def test_a_particle_that_ends_the_mention_is_not_a_fixed_word():
    assert sy.mention_word_fixed("PERSON", "Del", "Del", 0, CUT) is False
    assert sy.unchanged_mention_word("PERSON", "Del", "Del", CUT) is True
    # a particle followed by a name word stays a particle
    assert sy.mention_word_fixed("PERSON", "van", PLAIN, 7, PLAIN) is True
    assert sy.unchanged_mention_word("PERSON", PLAIN, "Corentin van Abberley", PLAIN) is False


def test_the_fake_of_a_value_that_ends_with_a_particle_word_replaces_it():
    st, a, b = _store()
    s = Synthesizer(SEED, "en", st)
    fa, fb = s.value_for(a), s.value_for(b)
    assert "del" not in _words(fa)
    assert "van" in _words(fb) and not ({"ysolde", "quorrow"} & _words(fb))
    for need in ("", "dir", "first"):
        out = s.render(a, fa, "Del", need)
        assert fold_word(out) != "del" and "del" not in _words(out), (need, out)


def test_the_masker_never_writes_the_nickname_back():
    st, _a, _b = _store()
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    for text in ("Thanks Del, see you on Monday.\n", "Best,\nDel\n", f"{PLAIN} signed the memo.\n"):
        out = m.mask(text).text
        assert not re.search(r"\bDel\b", out), out
        assert "Ysolde" not in out and "Quorrow" not in out, out


def test_codes_mode_is_unchanged():
    st, a, _b = _store()
    m = Masker(st, locale="en", use_ner=False)
    out = m.mask("Thanks Del, see you on Monday.\n").text
    assert not re.search(r"\bDel\b", out), out


def test_a_number_of_the_real_company_name_is_never_written_again():
    st = MemoryStore(locale="en")
    value = "317 Quorrow"
    ent = st.add("ORG", value, entity_norm("ORG", value))
    assert mk._synthetic_leaks(ent, "317 Brindlemoor")
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    for text in ("The 317 Quorrow team signed off.\n", "Ask 317 Quorrow for the file.\n"):
        out = m.mask(text).text
        assert "317" not in out and "Quorrow" not in out, out


def test_the_number_guard_compares_whole_digit_runs():
    st = MemoryStore(locale="en")
    value = "Quorrow Freight"
    ent = st.add("ORG", value, entity_norm("ORG", value))
    # a number the real name does not hold is no leak (the guard compares whole digit runs)
    assert not mk._synthetic_leaks(ent, "Brindlemoor Haulage 12")
    assert mk._synthetic_leaks(st.add("ORG", "Quorrow 12 Haulage", entity_norm("ORG", "Quorrow 12 Haulage")),
                               "Brindlemoor 12 Carters")
    assert not mk._synthetic_leaks(ent, "Brindlemoor Haulage 125")
