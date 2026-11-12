"""v0.4 S0: synthetic-mode leak classes C, D and K, and the clean-room audit's written forms.

C: the local part of a fake e-mail kept a part of the real one (a short given name, an initial).
D: a fake was one edit (or the same sound) away from the real value ("Wandrell" for a real "Vandrell").
K: a fake identifier kept the real letter code ("QXT-..." stayed "QXT-...").
Audit: evaluation/audit/audit_bench.py finds digit identifiers written in quoted groups or with any separator, and
the other written forms of the v0.3.1 gold-audit break test (camelCase, escapes, entities, joined literals, look-alike
letters, base64, hex, digests, three-letter names, five-digit ids, files outside the old paths, allow laundering).

Every name, number, address and code below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

from ragbase_shield.engine import Masker, MemoryStore, Synthesizer
from ragbase_shield.engine import synthetic as sy
from ragbase_shield.engine.masker import entity_norm
from ragbase_shield.engine.normalize import fold_word

SEED = b"v04-s0-synthetic-test-seed-0123456789abcdef"
ROOT = Path(__file__).resolve().parents[1]


def _synth(*entities: tuple[str, str], seed: bytes = SEED):
    st = MemoryStore(locale="en")
    ents = [st.add(k, v, entity_norm(k, v)) for k, v in entities]
    return Synthesizer(seed, "en", st), st, ents


def _parts(s: str) -> set[str]:
    return {fold_word(r) for r in re.findall(r"[^\W\d_]+", s)}


# ------------------------------------------------------------------------------------------ class C: e-mail local part

def test_linked_local_part_is_built_from_the_fake_person_never_from_the_real_one():
    s, st, (p, m) = _synth(("PERSON", "Tavish Marvelle"), ("EMAIL", "t.marvelle@brenwick-optics.test"))
    fake = s.value_for(p)
    local = s.value_for(m).partition("@")[0]
    first, last = sy._ascii(fake.split()[0]), sy._ascii(fake.split()[-1])
    assert local == f"{first[:1]}.{last}"
    assert not (_parts(local) & _parts("t.marvelle")), local  # not even the initial "t"


def test_short_form_and_joined_initial_of_the_local_part_read_as_the_fake_given_name():
    s, st, (p, m1, m2) = _synth(("PERSON", "Dovrena Quillsby"), ("EMAIL", "dov.quillsby@brenwick-optics.test"),
                                ("EMAIL", "dquillsby@brenwick-optics.test"))
    fake = s.value_for(p)
    first, last = sy._ascii(fake.split()[0]), sy._ascii(fake.split()[-1])
    assert s.value_for(m1).partition("@")[0] == f"{first}.{last}"  # "dov" (first letters) -> the whole fake name
    assert s.value_for(m2).partition("@")[0] == f"{first[:1]}{last}"  # "d" + surname, joined
    for m in (m1, m2):
        assert not (_parts(s.value_for(m).partition("@")[0]) & {"dov", "d", "quillsby", "dquillsby", "dovrena"})


def test_unlinked_local_part_is_neutral_and_keeps_no_real_part_or_initial():
    # two people share the surname: the local part names neither for sure, a neutral one is built
    s, st, (a, b, m) = _synth(("PERSON", "Tavish Marvelle"), ("PERSON", "Elsabet Marvelle"),
                              ("EMAIL", "t.marvelle@brenwick-optics.test"))
    for seed in (SEED, b"another-seed-for-the-neutral-local-part-000", b"third-seed-neutral-local-part-xyz-00000"):
        s2, _st, (_a, _b, m2) = _synth(("PERSON", "Tavish Marvelle"), ("PERSON", "Elsabet Marvelle"),
                                       ("EMAIL", "t.marvelle@brenwick-optics.test"), seed=seed)
        local = s2.value_for(m2).partition("@")[0]
        assert re.fullmatch(r"[a-z]\.[a-z]+", local), local
        assert not (_parts(local) & {"t", "marvelle", "tavish", "elsabet"}), local


def test_collision_rule_and_render_canary_refuse_a_kept_local_part():
    s, st, (p, m) = _synth(("PERSON", "Tavish Marvelle"), ("EMAIL", "t.marvelle@brenwick-optics.test"))
    idx = s._index()
    assert s._collides(m, "t.zorbin@larkfell.example", idx) == "the fake e-mail keeps a part of the real local part"
    assert s._collides(m, "q.zorbin@larkfell.example", idx) is None
    with pytest.raises(sy.SyntheticLeak) as ei:
        s.render(m, "t.zorbin@larkfell.example", "t.marvelle@brenwick-optics.test")
    assert m.code in str(ei.value) and "marvelle" not in str(ei.value).lower()


def test_a_stale_local_part_follows_the_fake_person():
    s, st, (p, m) = _synth(("PERSON", "Tavish Marvelle"), ("EMAIL", "t.marvelle@brenwick-optics.test"))
    s.value_for(p)
    s.value_for(m)
    # a stored fake from an older build that kept the real initial is no longer usable: it is drawn again
    st.set_synthetic(m.code, "t.zorbin@larkfell.example")
    new = s.value_for(m)
    assert new != "t.zorbin@larkfell.example" and not new.startswith("t.")


# ------------------------------------------------------------------------------------------ class D: one edit, same sound

@pytest.mark.parametrize("a, b, expected", [
    ("vandrell", "wandrell", True), ("vandrell", "vandrel", True), ("vandrell", "avndrell", True),
    ("vandrell", "vandrella", True), ("vandrell", "wandrels", False), ("vandrell", "vandrell", False),
])
def test_one_edit_counts_the_first_letter_too(a, b, expected):
    assert sy._one_edit(a, b) is expected
    assert bool(sy._del_keys(a) & sy._del_keys(b)) is (expected or a == b)


def test_sound_key_reads_spellings_of_the_same_sound_alike():
    assert sy._sound("Korvath") == sy._sound("Corvath")
    assert sy._sound("Brynde") == sy._sound("Brinde")
    assert sy._sound("Phelsar") == sy._sound("Felsar")
    assert sy._sound("Korvath") != sy._sound("Morvath") and sy._sound("abc") == ""


def test_a_fake_name_word_one_edit_or_same_sound_from_a_real_word_is_refused():
    s, st, (a, b) = _synth(("PERSON", "Osric Vandrell"), ("PERSON", "Ilse Felsar"))
    idx = s._index()
    assert s._collides(a, "Brisk Wandrell", idx) == "a fake name word is one edit from a real word"
    assert s._collides(b, "Maud Phelsar", idx) == "a fake name word sounds like a real word"  # two edits away
    assert s._collides(a, "Brisk Tolvenard", idx) is None


def test_drawn_fakes_are_never_one_edit_or_same_sound_from_the_real_words():
    for i in range(25):
        seed = f"s0-one-edit-seed-{i:03d}-0123456789abcdef".encode()
        s, st, ents = _synth(("PERSON", "Osric Vandrell"), ("PERSON", "Ilse Corvath"),
                             ("PHONE", "+1 (802) 555-0166"), seed=seed)
        real = {"osric", "vandrell", "ilse", "corvath"}
        for e in ents:
            fake = s.value_for(e)
            assert not sy._one_edit(sy._core(fake), sy._core(e.value)), (e.value, fake)
            for w in _parts(fake):
                assert not any(sy._one_edit(w, r) for r in real if len(r) >= 5), (w, fake)
                assert not (len(w) >= 4 and sy._sound(w) in {sy._sound(r) for r in real}), (w, fake)
        assert s.failed_closed == Counter()


def test_the_one_edit_rule_is_exact_two_edits_away_is_not_refused():
    # "redwald" and "trewald" share a key of _del_keys ("rewald") but are two edits apart: not a near word
    assert sy._del_keys("redwald") & sy._del_keys("trewald") and not sy._one_edit("redwald", "trewald")
    s, st, (a,) = _synth(("PERSON", "Ottar Trewald"))
    idx = s._index()
    assert s._near_real_word({"redwald"}, idx) is None
    assert s._near_real_word({"trewalt"}, idx) == "is one edit from a real word"


def test_large_dossier_of_mails_never_fails_closed_on_near_words():
    # many invented people and mails whose words share endings with the fake pools ("-wood", "-field"): the near
    # rule on host words is checked against the mail's own words, so the draw never runs out
    syl_a = ("Bran", "Kest", "Fin", "Ostro", "Quil", "Tre", "Vau", "Win", "Zor", "Mer", "Dov", "Pel")
    syl_b = ("wick", "bury", "wood", "garec", "brook", "halde", "moor", "field", "nick", "sley", "venor", "aske")
    items = []
    for i, (a, b) in enumerate((a, b) for a in syl_a for b in syl_b):
        items += [("PERSON", f"{a}rik {a}{b}"), ("EMAIL", f"{a.lower()[0]}.{a.lower()}{b}@x{i}.test")]
    s, st, ents = _synth(*items)
    for e in ents:
        fake = s.value_for(e)
        if e.kind == "EMAIL":
            assert not (_parts(fake.partition("@")[0]) & _parts(e.value.partition("@")[0])), (e.value, fake)
    assert s.failed_closed == Counter()


def test_a_phone_one_digit_from_the_real_one_is_refused():
    s, st, (ph,) = _synth(("PHONE", "+1 (802) 555-0166"))
    idx = s._index()
    assert s._collides(ph, "+1 (802) 555-0167", idx) == "the fake is one edit from the real value"
    assert s._collides(ph, "+1 (716) 555-0120", idx) is None
    with pytest.raises(sy.SyntheticLeak):
        s.render(ph, "+1 (802) 555-0167", "+1 (802) 555-0166")


# ------------------------------------------------------------------------------------------ class K: identifier codes

def test_identifier_letter_code_gets_a_fake_code_consistent_in_the_dossier():
    s, st, (a, b, c) = _synth(("EMPLOYEE_ID", "QXT-48213"), ("EMPLOYEE_ID", "QXT-70562"),
                              ("ACCOUNT_NUMBER", "zwv-3195-77"))
    fa, fb, fc = (s.value_for(e) for e in (a, b, c))
    assert re.fullmatch(r"[A-Z]{3}-\d{5}", fa) and re.fullmatch(r"[A-Z]{3}-\d{5}", fb), (fa, fb)
    assert fa[:3] == fb[:3]  # one real code, one fake code
    assert all(x != y for x, y in zip(fa[:3], "QXT"))  # no real letter at its place
    assert re.fullmatch(r"[a-z]{3}-\d{4}-\d\d", fc) and all(x != y for x, y in zip(fc[:3], "zwv")), fc
    assert s.failed_closed == Counter()


def test_public_labels_stay_and_a_kept_code_is_refused():
    s, st, (rg, ecli, ident, user) = _synth(("CASE_REF", "RG 24/01234"),
                                            ("CASE_REF", "ECLI:FR:CCASS:2024:SO00123"),
                                            ("ID_CODE", "QXT-48213"), ("USERNAME", "tavi42"))
    assert s.value_for(rg).startswith("RG ") and s.value_for(ecli).startswith("ECLI:")
    assert "tavi" not in s.value_for(user).lower()
    idx = s._index()
    assert s._collides(ident, "QXT-11111", idx) == "the fake keeps a letter code of the real value"
    assert s._collides(ident, "JAB-11111", idx) is None
    with pytest.raises(sy.SyntheticLeak):
        s.render(ident, "QXT-11111", "QXT-48213")


# ------------------------------------------------------------------------------------------ masker, end to end

def test_masker_synthetic_output_keeps_no_local_part_code_or_near_word():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    t = ("Ms. Dovrena Quillsby (dov.quillsby@brenwick-optics.test, Employee ID: QXT-48213) wrote to Mr. Osric "
         "Vandrell. Mr. Tavish Marvelle (t.marvelle@brenwick-optics.test) called +1 (802) 555-0166. "
         "Employee ID: QXT-70562.")
    out = m.mask(t).text
    real = {"dovrena", "quillsby", "dov", "qxt", "osric", "vandrell", "tavish", "marvelle", "brenwick"}
    words = _parts(out)
    assert not (words & real), out
    assert not any(sy._one_edit(w, r) for w in words for r in real if len(r) >= 5 and len(w) >= 4), out
    assert "t." not in re.findall(r"\b\w\.(?=\w+@)", out)
    assert m.unmask(out) == t


# ------------------------------------------------------------------------------------------ audit_bench written forms

@pytest.fixture(scope="module")
def ab():
    sys.path.insert(0, str(ROOT / "evaluation" / "audit"))
    try:
        import audit_bench  # noqa: PLC0415 - evaluation tool, standard library only
    finally:
        sys.path.pop(0)
    return audit_bench


def _gold(ab, items):
    gs = ab.GoldSet()
    for raw, label, how in items:
        gs.add_any(raw, "PrivacyBench", label, how)
    return gs


def _hits(ab, gs, text, allow=None, new_allow=frozenset()):
    ix = ab._Index(gs, {})
    hits: dict = {}
    for v in ab.variants(text):
        ab.line_hits(v, ix, allow or {}, set(new_allow), Counter(), hits)
    return {(k[0], g.masked if g else None, note) for k, (g, note) in hits.items()}


def test_audit_reads_digit_groups_across_any_separator(ab):
    assert "2085550163" in set(ab.loose_windows(ab.fold('("208", "555", "0163")'), 40))
    assert "4178623051" in set(ab.loose_windows(ab.fold("[417] [862] [3051]"), 40))
    assert not set(ab.loose_windows(ab.fold("Emp # 4521"), 40))  # every part holds a digit
    # a decimal comma ends the run: "613,57" is one number
    assert set(ab.loose_windows(ab.fold("4 802 613,57 euros"), 40)) == {"4802", "4802613", "802613"}
    gs = _gold(ab, [("+1-208-555-0163", "PHONE_NUMBER", "phone")])
    assert ("ident", "1~15", "") in _hits(ab, gs, '# groups ("208", "555", "0163") of a phone')


@pytest.mark.parametrize("line", [
    "tavishMarvelle = 1",                      # camelCase
    'X = "Marv\\u0065lle"',                     # Python escape
    "Name: Marv&#101;lle",                     # HTML entity
    'Y = "Marv" + "elle"',                     # joined literals
    "Мarvelle",                           # Cyrillic capital Em in a Latin word
    "Marv%65lle",                              # URL escape
])
def test_audit_reads_the_decoded_forms_of_a_line(ab, line):
    gs = _gold(ab, [("Marvelle", "NAME_FAMILY", "words")])
    assert ("words", "M~8", "") in _hits(ab, gs, line), line


def test_audit_reads_base64_hex_and_digests_of_a_value(ab):
    mail = "t.marvelle@brenwick-optics.test"
    gs = _gold(ab, [(mail, "EMAIL_ADDRESS", "email")])
    assert any(k == "ident" for k, _m, _n in _hits(ab, gs, "# " + base64.b64encode(mail.encode()).decode()))
    assert any(k == "ident" for k, _m, _n in _hits(ab, gs, "# " + mail.encode().hex()))
    for h in (hashlib.sha256, hashlib.sha1, hashlib.md5):
        assert ("hash", "t~31", "") in _hits(ab, gs, "# " + h(mail.encode()).hexdigest())
    assert ("hash", "t~31", "") in _hits(ab, gs, "# " + hashlib.sha256(mail.upper().lower().encode()).hexdigest())


def test_audit_short_names_and_five_digit_ids(ab):
    gs = _gold(ab, [("Qyv", "NAME_GIVEN", "words"), ("48026", "EMPLOYEE_ID", "ident"), ("51320", "LOCATION_ADDRESS",
                                                                                         "address")])
    assert ("short", "Q~3", "") in _hits(ab, gs, '# "Qyv" is a name')
    assert not _hits(ab, gs, "# qyv in lower case, QYV in capitals")
    assert ("ident", "4~5", "") in _hits(ab, gs, "# employee 48026")
    assert not _hits(ab, gs, "# postcode 51320")  # a five-digit postcode is not distinctive
    assert not _hits(ab, gs, "# not 480261 nor 1480 26")
    assert ("short", "Q~3", "") not in _hits(ab, gs, '# "Qyv" is a name', allow={("qyv",): "test"})


def test_audit_flags_an_allow_entry_added_with_the_value_it_hides(ab):
    gs = _gold(ab, [("Marvelle", "NAME_FAMILY", "words")])
    key = ("marvelle",)
    assert not _hits(ab, gs, "Contact Marvelle.", allow={key: "old entry"})
    got = _hits(ab, gs, "Contact Marvelle.", allow={key: "new entry"}, new_allow={key})
    assert ("words", "M~8", "allow-added") in got


def test_audit_scope_covers_root_files_and_the_scoreboard_not_the_runners(ab):
    for rel in ("SECURITY.md", "pyproject.toml", "bench/run_bench.py", "evaluation/SCOREBOARD.md", "docs/a.svg",
                ".claude-plugin/marketplace.json", "src/ragbase_shield/engine/synthetic.py"):
        assert ab.in_repo_scope(rel), rel
    for rel in ("evaluation/public/privacybench/RESULTS.md", "evaluation/audit/allow.txt", ".bench_data/x.json",
                "src/ragbase_shield/__pycache__/x.pyc"):
        assert not ab.in_repo_scope(rel), rel


def test_audit_reads_office_xml_and_skips_binary(ab, tmp_path):
    import zipfile
    doc = tmp_path / "invented.docx"
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", "<w:document><w:p><w:r><w:t>Marv</w:t></w:r><w:r><w:t>elle</w:t></w:r>"
                                        "</w:p></w:document>")
    png = tmp_path / "icon.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n\0\0\0")
    unread: list = []
    assert ab._read(doc, unread) == ["Marvelle"]
    assert ab._read(png, unread) is None and len(unread) == 1
