"""v0.3 synthetic mode: collision rules, re-draw and fail-closed canaries (owner SYNTH-LEAK; PLAN section 5).

Every name, number and address below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import re

import pytest

from ragbase_shield.engine import Masker, MemoryStore, Synthesizer
from ragbase_shield.engine import synthetic as sy
from ragbase_shield.engine.masker import entity_norm
from ragbase_shield.engine.normalize import fold_word, normalize

SEED = b"v03-synthetic-leak-test-seed-0123456789abcdef"

# invented syllables: the large-dossier test builds hundreds of surnames from them
_SYL_A = ("Bran", "Kest", "Fin", "Ostro", "Quil", "Tre", "Vau", "Win", "Hal", "Mer")
_SYL_B = ("wick", "bury", "wood", "garec", "brook", "halde", "moor", "field", "nick", "sley")


def _words(s: str) -> set[str]:
    return {fold_word(r) for r in re.findall(r"[^\W\d_]+", s) if len(r) >= 2}


def _store(*entities: tuple[str, str], locale: str = "en") -> tuple[MemoryStore, list]:
    st = MemoryStore(locale=locale)
    ents = [st.add(k, v, entity_norm(k, v)) for k, v in entities]
    return st, ents


def _synth(*entities: tuple[str, str], lang: str = "en", **kw):
    st, ents = _store(*entities, locale=lang)
    return Synthesizer(SEED, lang, st, **kw), st, ents


def _add(st: MemoryStore, kind: str, value: str):
    return st.add(kind, value, entity_norm(kind, value))


def _initials(value: str) -> str:
    return "".join(fold_word(r)[:1] for r in re.findall(r"[^\W\d_]+", value))


# ------------------------------------------------------------------------------------------ re-draw on collision

def test_fake_drawn_before_a_colliding_real_name_is_redrawn():
    s, st, (a,) = _synth(("PERSON", "Pelorin Oskvarnik"))
    fake1 = s.value_for(a)
    first1 = fake1.split()[0]
    assert s.collisions_with_store() == []
    b = _add(st, "PERSON", f"{first1} Quillanmere")  # the real person seen later carries the fake first name
    found = s.collisions_with_store()
    assert [c for c, _r in found] == [a.code] and "a word of a real value" in found[0][1]
    fake2 = s.value_for(a)
    assert fake2 != fake1 and fold_word(first1) not in _words(fake2)
    assert st.synthetic(a.code) == fake2 and s.redrawn["PERSON"] == 1
    assert s.collisions_with_store() == [] and s.value_for(a) == fake2
    fb = s.value_for(b)
    assert not (_words(fb) & (_words(a.value) | _words(b.value) | _words(fake2)))


def test_fake_never_reuses_a_word_of_a_real_value_of_any_kind():
    s, st, (a,) = _synth(("PERSON", "Pelorin Oskvarnik"))
    first1 = s.value_for(a).split()[0]
    # the same person in a dossier where that word is a real handle and the local part of a real e-mail
    s2, st2, ents = _synth(("USERNAME", first1.lower()),
                           ("EMAIL", f"{first1.lower()}.fennimore@brightholm-logistics.test"),
                           ("PERSON", "Pelorin Oskvarnik"))
    fake = s2.value_for(ents[2])
    assert fold_word(first1) not in _words(fake) and fake.split()[0] != first1
    real_words = _words(ents[0].value) | _words(ents[1].value) | _words(ents[2].value)
    assert not (_words(fake) & real_words)
    # a fake e-mail or web address never reuses a word of a real party either
    s3, st3, e3 = _synth(("PERSON", "Pelorin Oskvarnik"), ("ORG", "Brightholm Logistics LLC"),
                         ("EMAIL", "p.oskvarnik@brightholm-logistics.test"),
                         ("URL", "https://www.brightholm-logistics.test/team/pelorin"))
    for e in e3[2:]:
        f = s3.value_for(e)
        assert not ({w for w in _words(f) if len(w) >= 4} & _words("Pelorin Oskvarnik Brightholm Logistics")), f


def test_redraw_collisions_api_and_shared_surname_survive():
    s, st, (a, b, c) = _synth(("PERSON", "Pelorin Oskvarnik"), ("PERSON", "Maelle Oskvarnik"),
                              ("PERSON", "Casimir Wintergale"))
    fa, fb, fc = (s.value_for(e) for e in (a, b, c))
    assert fa.split()[-1] == fb.split()[-1] != fc.split()[-1]
    # two real people seen later: one carries the shared fake surname, one the fake first name of the third
    _add(st, "PERSON", f"Ludivine {fa.split()[-1]}")
    _add(st, "PERSON", f"{fc.split()[0]} Brannoch")
    codes = sorted(code for code, _r in s.collisions_with_store())
    assert codes == sorted([a.code, b.code, c.code])
    assert s.redraw_collisions() == 3 and s.collisions_with_store() == []
    ga, gb, gc = (s.value_for(e) for e in (a, b, c))
    assert ga != fa and gb != fb and gc != fc
    assert ga.split()[-1] == gb.split()[-1] != fa.split()[-1]  # the two sharers still share one fake surname
    assert fold_word(fc.split()[0]) not in _words(gc)
    real_words = set()
    for e in st.all():
        real_words |= _words(e.value)
    for g in (ga, gb, gc):
        assert not (_words(g) & real_words)


def test_values_lists_every_fake_after_the_redraws():
    s, st, (a, b, m) = _synth(("PERSON", "Pelorin Oskvarnik"), ("PERSON", "Casimir Wintergale"),
                              ("EMAIL", "p.oskvarnik@brightholm-logistics.test"))
    fa, fb, fm1 = (s.value_for(e) for e in (a, b, m))
    assert s.values() == {a.code: fa, b.code: fb, m.code: fm1}
    _add(st, "PERSON", f"{fb.split()[0]} Brannoch")  # a real person seen later carries b's fake first name
    assert st.synthetic(b.code) == fb  # the raw store row is stale until the Synthesizer is asked again
    vals = s.values()
    assert set(vals) == {a.code, b.code, m.code} and vals[a.code] == fa
    assert vals[b.code] != fb and fold_word(fb.split()[0]) not in _words(vals[b.code])
    assert vals[b.code] == st.synthetic(b.code) and s.collisions_with_store() == []
    assert Synthesizer(SEED, "en", MemoryStore(locale="en")).values() == {}


def test_reserve_keeps_fakes_away_from_detected_surfaces():
    s, st, (a,) = _synth(("PERSON", "Pelorin Oskvarnik"))
    fake0 = s.value_for(a)
    s.reserve([f"{fake0.split()[0]} Brannoch", "", 3])  # a surface the caller saw but did not register
    assert [code for code, _r in s.collisions_with_store()] == [a.code]
    fake1 = s.value_for(a)
    assert fake1 != fake0 and fold_word(fake0.split()[0]) not in _words(fake1)
    s.reserve([])
    assert s.value_for(a) == fake1


def test_linked_email_follows_the_redraw_of_its_person():
    s, st, (a, m) = _synth(("PERSON", "Pelorin Oskvarnik"), ("EMAIL", "p.oskvarnik@brightholm-logistics.test"))
    fa, mail1 = s.value_for(a), s.value_for(m)
    assert sy._ascii(fa.split()[-1]) in mail1.partition("@")[0]
    _add(st, "PERSON", f"Ludivine {fa.split()[-1]}")  # the fake surname becomes a real surname
    ga = s.value_for(a)
    assert ga.split()[-1] != fa.split()[-1]
    mail2 = s.value_for(m)
    assert mail2 != mail1 and sy._ascii(ga.split()[-1]) in mail2.partition("@")[0]
    assert sy._ascii(fa.split()[-1]) not in mail2


# ------------------------------------------------------------------------------------------ fail closed

def test_value_for_fails_closed_when_no_safe_value_exists(monkeypatch):
    s, st, (a,) = _synth(("PERSON", "Pelorin Oskvarnik"))
    monkeypatch.setattr(sy.Synthesizer, "_generate", lambda self, ent, rng, draw: ent.value)
    monkeypatch.setattr(sy.Synthesizer, "_fallback", lambda self, ent, draw: ent.value)
    with pytest.raises(sy.SyntheticCollision) as ei:
        s.value_for(a)
    msg = str(ei.value)
    assert a.code in msg and "oskvarnik" not in msg.lower() and "pelorin" not in msg.lower()
    assert st.synthetic(a.code) is None and s.failed_closed["PERSON"] == 1
    assert issubclass(sy.SyntheticCollision, sy.SyntheticError) and issubclass(sy.SyntheticError, RuntimeError)
    # through the masker: the code is written, nothing real stays
    st2 = MemoryStore(locale="en")
    m = Masker(st2, locale="en", use_ner=False, replacement="synthetic")
    out = m.mask("Mr. Pelorin Oskvarnik signed the lease.").text
    assert "Oskvarnik" not in out and "Pelorin" not in out and st2.all()[0].code in out


def test_fallback_value_is_checked_too(monkeypatch):
    s, st, (a, b) = _synth(("PERSON", "Pelorin Oskvarnik"), ("PERSON", "Casimir Wintergale"))
    fb = s.value_for(b)
    monkeypatch.setattr(sy.Synthesizer, "_generate", lambda self, ent, rng, draw: None)
    monkeypatch.setattr(sy.Synthesizer, "_fallback", lambda self, ent, draw: fb)  # equals another fake
    with pytest.raises(sy.SyntheticCollision) as ei:
        s.value_for(a)
    assert "another fake" in str(ei.value) and fb not in str(ei.value)


def test_render_fails_closed_when_the_rendering_still_shows_the_real_text(monkeypatch):
    s, st, (a, ph, bd) = _synth(("PERSON", "Pelorin Oskvarnik"), ("PHONE", "+1 (802) 555-0181"),
                                ("BIRTHDATE", "March 14, 1975"))
    fake = s.value_for(a)
    monkeypatch.setattr(sy.Synthesizer, "_render_name",
                        lambda self, src, dst, surface, need, reverse=False: surface)
    for surf in ("Oskvarnik", "P. O.", "OSKVARNIK", "Oskvarnik, Pelorin", "Oskvarnic", "pelorin"):
        with pytest.raises(sy.SyntheticLeak) as ei:
            s.render(a, fake, surf)
        assert "oskvarnik" not in str(ei.value).lower() and a.code in str(ei.value)
    assert s.failed_closed["PERSON"] == 6
    monkeypatch.setattr(sy.Synthesizer, "_render_other", lambda self, ent, src, dst, surface, reverse=False: surface)
    for e, surf in ((ph, "802-555-0181"), (bd, "14/03/1975")):
        with pytest.raises(sy.SyntheticLeak):
            s.render(e, s.value_for(e), surf)
    # through the masker: the code is written, nothing real stays
    st2 = MemoryStore(locale="en")
    m = Masker(st2, locale="en", use_ner=False, replacement="synthetic")
    out = m.mask("Mr. Pelorin Oskvarnik signed; call +1 (802) 555-0181.").text
    assert "Oskvarnik" not in out and "555-0181" not in out and len([c for c in st2.all()]) == 2


def test_render_of_an_unchanged_generic_word_is_not_a_leak(monkeypatch):
    s, st, (o,) = _synth(("ORG", "Garage du Centre"), lang="fr")
    fake = s.value_for(o)
    assert fake.startswith("Garage du ") and fake != "Garage du Centre"
    assert s.render(o, fake, "Garage") == "Garage"  # a generic word of the name, written unchanged: no secret
    assert s.render(o, fake, "Centre") != "Centre"  # the distinctive word is replaced
    # a rendering that would keep the distinctive word trips the canary; the generic word alone still passes
    monkeypatch.setattr(sy.Synthesizer, "_render_name", lambda self, src, dst, surface, need, reverse=False: surface)
    with pytest.raises(sy.SyntheticLeak):
        s.render(o, fake, "Centre")
    assert s.render(o, fake, "Garage") == "Garage"


# ------------------------------------------------------------------------------------------ shape rules

def test_initials_always_differ_and_word_count_is_kept():
    people = [f"{a}{b.lower()} {c}{d.lower()}" for a, b in zip(_SYL_A, _SYL_B)
              for c, d in zip(_SYL_A[::-1], _SYL_B[::-1])][:40]
    people += ["Oskvarnik", "J. P. Wintergale", "Maelle de Kestbury", "Dr Alder Finchmere Jr.", "T. Vaudrelin-Orel"]
    s, st, ents = _synth(*[("PERSON", p) for p in people])
    for e in ents:
        fake = s.value_for(e)
        assert len(re.findall(r"[^\W\d_]+", fake)) == len(re.findall(r"[^\W\d_]+", e.value)), (e.value, fake)
        real_runs = re.findall(r"[^\W\d_]+", e.value)
        fake_runs = re.findall(r"[^\W\d_]+", fake)
        for r, f in zip(real_runs, fake_runs):
            if fold_word(r) != fold_word(f):
                assert fold_word(r)[:1] != fold_word(f)[:1], (e.value, fake)
        if " " in e.value:
            ini = ". ".join(_initials(e.value).upper()) + "."
            assert s.render(e, fake, ini) != ini
    assert "de Kestbury" not in s.value_for(ents[42]) and " de " in s.value_for(ents[42])
    assert s.value_for(ents[43]).startswith("Dr ") and s.value_for(ents[43]).endswith(" Jr.")


def test_fallback_keeps_the_shape_when_every_pool_is_exhausted(monkeypatch):
    s, st, (a, o) = _synth(("PERSON", "Pelorin Oskvarnik"), ("ORG", "Brightholm Logistics LLC"))
    monkeypatch.setattr(sy.Synthesizer, "_pick_word", staticmethod(lambda pools, rng, draw, used, avoid_initial="": None))
    fa, fo = s.value_for(a), s.value_for(o)
    assert len(fa.split()) == 2 and fa[0] != "P" and fa.split()[1][0] != "O" and fa.istitle()
    assert re.fullmatch(r"[A-Z][a-z]{4,7} [A-Z][a-z]{4,7}", fa), fa
    assert fo.endswith(" LLC") and len(fo.split()) == 3 and not ({"brightholm", "logistics"} & _words(fo))
    assert fa.lower() != "pelorin oskvarnik" and s.failed_closed == {}


def test_large_dossier_exhausts_the_pools_without_gibberish_or_collisions():
    lists = sy.synthetic_lists("en")
    firsts = lists["first_f"] + lists["first_m"]  # every name of the fake pool is a real name of this dossier
    surnames = [f"{a}{b.lower()}{c.lower()}" for a in _SYL_A for b in _SYL_B for c in ("ton", "ham", "ley")]
    people = [f"{firsts[i % len(firsts)]} {surnames[i]}" for i in range(260)]
    s, st, ents = _synth(*[("PERSON", p) for p in people])
    real_words = set()
    for e in ents:
        real_words |= _words(e.value)
    fakes = [s.value_for(e) for e in ents]
    assert len({normalize(f) for f in fakes}) == len(fakes)  # every fake distinct
    for e, f in zip(ents, fakes):
        assert len(f.split()) == 2, (e.value, f)
        assert not (_words(f) & real_words), (e.value, f)
        assert fold_word(e.value)[:1] != fold_word(f)[:1]
        assert all(len(w) <= 14 for w in f.split()), f
    assert s.failed_closed == {} and s.collisions_with_store() == []
    # the first names of the pool are all real here, so the fakes come from the public extension list
    assert sum(1 for f in fakes if fold_word(f.split()[0]) in {fold_word(x) for x in firsts}) == 0


def test_fake_name_word_never_holds_a_real_word_and_agrees_with_the_masker_canary():
    from ragbase_shield.engine import masker as mk

    s, st, (o, p) = _synth(("ORG", "Ostro & Vale Roasting"), ("PERSON", "Pelorin Oskvarnik"))
    idx = s._index()
    assert s._collides(o, "Summit & Sandpiper Springvale", idx) == "a fake name word holds a real word"
    assert s._collides(p, "Pelorinault Brannoch", idx) == "a fake name word holds a real word"
    assert s._collides(o, "Summit & Sandpiper Clearbrook", idx) is None
    with pytest.raises(sy.SyntheticLeak):
        s.render(o, "Summit & Sandpiper Springvale", "Vale Roasting")
    # every fake the Synthesizer gives passes the masker's own leak check (no code written for a good fake)
    names = [("ORG", "Ostro & Vale Roasting"), ("ORG", "Kest Finwood Partners LLP"), ("PERSON", "Pelorin Oskvarnik"),
             ("PERSON", "Maelle Vaudrelin-Orel"), ("PERSON", "Dr Alder Finchmere Jr."), ("ORG", "Brightholm Logistics LLC")]
    s2, st2, ents = _synth(*names)
    for e in ents:
        fake = s2.value_for(e)
        assert not mk._synthetic_leaks(e, fake), (e.value, fake)
        assert not mk._synthetic_leaks(e, s2.render(e, fake, e.value)), (e.value, fake)


def test_fake_initials_never_read_as_a_group_of_a_real_value():
    s, st, (a, p, o) = _synth(("ADDRESS", "48 Quenby Ridge Road, Maplewick, OH 43215"),
                              ("PERSON", "Pelorin Oskvarnik"), ("ORG", "Brightholm Logistics LLC"))
    idx = s._index()
    # "OH", the state code of a real address: the masker would read a fake "O. H." there and drop the address
    assert s._collides(p, "Olivia Hesketh", idx) == "the initials of the fake read as a part of a real value"
    assert s._collides(p, "Olivia Tarrow", idx) is None
    assert s._collides(o, "Oakridge Halvern LLC", idx) == "the initials of the fake read as a part of a real value"
    assert s._collides(o, "Oakridge Tarrow LLC", idx) is None
    for e in (p, o):
        fake = s.value_for(e)
        assert not (s._name_groups(e.kind, fake) & idx.real_groups), fake
    assert s.failed_closed == {}


def test_short_fake_id_never_equals_a_group_of_a_real_value():
    s, st, (ph, code, ref) = _synth(("PHONE", "+1 (802) 555-0166"), ("ID_CODE", "208"), ("CASE_REF", "RG 24/0931"))
    idx = s._index()
    assert s._collides(code, "802", idx) == "equals a part of a real value"  # the area code of a real phone
    assert s._collides(code, "0166", idx) is not None and s._collides(code, "803", idx) is None
    assert s._collides(code, "0931", idx) is not None  # a group of a real reference
    fake = s.value_for(code)
    assert fake not in ("802", "555", "0166", "208") and len(fake) == 3
    s.reserve(["Badge 5826"])  # a detected surface the caller did not register: its groups count too
    assert s._collides(code, "5826", s._index()) is not None
    # a fake phone keeps its own shape: the shared "555" group of the fiction range is not a collision by itself
    assert s.value_for(ph) != ph.value and s.failed_closed == {}


# ------------------------------------------------------------------------------------------ addresses, e-mails, web

def test_fake_address_never_keeps_a_real_street_or_town():
    s, st, (fr, en) = _synth(("ADDRESS", "7 rue des Capucines, 44000 Nantes"),
                             ("ADDRESS", "48 Quenby Ridge Road, Maplewick, OH 43215"))
    idx = s._index()
    assert s._collides(fr, "19 rue des Capucines, 31000 Toulouse", idx) == "a word of the fake is a word of a real value"
    assert s._collides(fr, "3 rue Tarrow, 31000 Toulouse", idx) is None  # "rue" is a street type, not a secret
    assert s._collides(en, "12 Quenby Ridge Lane, Wenmoor, OH 43001", idx) is not None
    assert s._collides(en, "12 Tarrow Road, Maplewick, OH 43001", idx) is not None  # the town is a real word too
    assert s._collides(en, "12 Tarrow Road, Wenmoor, OH 43001", idx) is None  # "Road" is generic
    for e in (fr, en):
        f = s.value_for(e)
        assert not ({w for w in _words(f) if len(w) >= 4} & {"capucines", "nantes", "quenby", "ridge", "maplewick"}), f
    # the render canary: a fake that still carries the real street is refused, the code is written instead
    with pytest.raises(sy.SyntheticLeak) as ei:
        s.render(fr, "19 rue des Capucines, 31000 Toulouse", "7 rue des Capucines")
    assert "capucines" not in str(ei.value).lower() and fr.code in str(ei.value)


def test_address_draw_moves_on_when_the_pool_gives_the_real_street(monkeypatch):
    orig = sy.Synthesizer._address
    calls = {"n": 0}

    def addr(self, value, rng):
        calls["n"] += 1
        return "19 rue des Capucines, 31000 Toulouse" if calls["n"] <= 2 else orig(self, value, rng)

    monkeypatch.setattr(sy.Synthesizer, "_address", addr)
    s, st, (a,) = _synth(("ADDRESS", "7 rue des Capucines, 44000 Nantes"), lang="fr")
    fake = s.value_for(a)
    assert calls["n"] >= 3 and not ({"capucines", "nantes"} & _words(fake)), fake
    assert s.failed_closed == {}
    # through the masker, with the same forced pool: nothing of the real address stays in the synthetic text
    calls["n"] = 0
    st2 = MemoryStore(locale="fr")
    st2._synthetic_seed = SEED
    m = Masker(st2, locale="fr", use_ner=False, replacement="synthetic")
    out = m.mask("Mme Perrine Vaudrelin, demeurant 7 rue des Capucines, 44000 Nantes, a écrit au bailleur.").text
    assert not ({"capucines", "nantes", "vaudrelin", "perrine"} & _words(out)), out
    assert calls["n"] >= 3


def test_fake_email_and_web_address_never_keep_a_real_word():
    s, st, (m, u) = _synth(("EMAIL", "quenby.ridge@maplewick-clinic.test"),
                           ("URL", "https://www.maplewick-clinic.test/team"))
    idx = s._index()
    assert s._collides(m, "ivo.maplewick@tarrow.example", idx) is not None
    assert s._collides(m, "ivo.tarrow@wenmoor.example", idx) is None
    assert s._collides(u, "https://www.maplewick.example/abcd", idx) is not None
    assert s._collides(u, "https://www.tarrow.example/abcd", idx) is None
    for e in (m, u):
        f = s.value_for(e)
        assert not ({w for w in _words(f) if len(w) >= 4} & {"quenby", "ridge", "maplewick", "clinic"}), f
        assert f.endswith(".example") or ".example/" in f


# ------------------------------------------------------------------------------------------ masker, end to end

def test_masker_synthetic_output_never_shows_a_real_value_after_late_arrivals():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    t1 = "Mr. Pelorin Oskvarnik and Ms. Maelle Quillanmere met Brightholm Logistics LLC."
    out1 = m.mask(t1).text
    assert not (_words(out1) & {"pelorin", "oskvarnik", "maelle", "quillanmere", "brightholm"})
    code_a = st.all()[0].code
    fake_first = st.synthetic(code_a).split()[0]
    # a real person who carries that fake first name as a surname is registered later (service.register, or
    # the scan of the whole dossier before the first fake is written: PLAN section 5, item 1)
    _add(st, "PERSON", f"Casimir {fake_first}")
    synth = m.synthesizer()
    assert [c for c, _r in synth.collisions_with_store()] == [code_a]
    assert synth.redraw_collisions() == 1 and synth.collisions_with_store() == []  # the masker hook
    assert st.synthetic(code_a).split()[0] != fake_first
    t3 = t1 + f" Then Casimir {fake_first} joined."
    out3 = m.mask(t3).text
    assert fold_word(fake_first) not in _words(out3) and "casimir" not in _words(out3)
    assert not (_words(out3) & {"pelorin", "oskvarnik", "maelle", "quillanmere", "brightholm"})
    assert m.unmask(out3) == t3


def test_english_title_name_is_detected_in_codes_mode():
    st = MemoryStore(locale="en")
    out = Masker(st, locale="en", use_ner=False).mask("Mr. Raphael Kestrelford joined the call.").text
    assert "Kestrelford" not in out and "Raphael" not in out


def test_masker_real_name_equal_to_an_earlier_fake_is_still_masked():
    """v0.3 integration (PLAN section 5, item 2): the masker reserves the new surfaces of a text before it looks
    for known fake surfaces, so a fake drawn earlier that equals a real name seen later is re-drawn, and the real
    name is masked (it was an xfail of the SYNTH owner: the Synthesizer alone cannot see a dropped candidate)."""
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    m.mask("Mr. Pelorin Oskvarnik signed the lease.")
    first = st.synthetic(st.all()[0].code).split()[0]
    out = m.mask(f"Mr. {first} Kestrelford joined the call.").text
    assert "Kestrelford" not in out and first not in out


def test_export_registered_before_the_first_draw_shows_no_real_value(monkeypatch):
    """PLAN section 5, item 1, at the engine level: when every value of the export is registered (codes mode)
    before the first fake is drawn, the collision rules see the whole dossier and nothing real stays in clear,
    even when the pool keeps offering a real name of the export as a fake."""
    texts = [
        "Mr. Pelorin Oskvarnik and Ms. Maelle Quillanmere met Brightholm Logistics LLC on site.",
        "Mr. Casimir Brannoch (casimir.brannoch@brightholm-logistics.test) called +1 (802) 555-0181 twice.",
        "Then Ms. Ludivine Wintergale and Mr. Oskvarnik signed; cc Brannoch and Quillanmere.",
        "Note from T. Oskvarnik: the Wintergale file goes to Casimir.",
    ]  # titles: rules mode (no NER) needs a cue for a bare English name; this test is about the draw order
    real_words = {"pelorin", "oskvarnik", "maelle", "quillanmere", "brightholm", "casimir", "brannoch",
                  "ludivine", "wintergale"}
    # the pool offers a real surname of the export as the first candidate of every draw
    orig = sy.Synthesizer._pick_word
    calls = {"n": 0}

    def pick(pools, rng, draw, used, avoid_initial=""):
        calls["n"] += 1
        return "Wintergale" if calls["n"] % 3 == 1 and "wintergale" not in draw.hard else orig(pools, rng, draw, used, avoid_initial)

    monkeypatch.setattr(sy.Synthesizer, "_pick_word", staticmethod(pick))
    st = MemoryStore(locale="en")
    st._synthetic_seed = SEED
    for t in texts:  # pass 1: register, codes mode, nothing drawn
        Masker(st, locale="en", use_ner=False, replacement="codes").mask(t)
    assert all(st.synthetic(e.code) is None for e in st.all())
    m = Masker(st, locale="en", use_ner=False, replacement="synthetic")
    outs = [m.mask(t) for t in texts]  # pass 2: the store holds the whole export, the fakes are drawn now
    for r in outs:
        assert not (_words(r.text) & real_words), r.text
        assert not any(re.fullmatch(r"[A-Z]+_[A-Z0-9]+", rep or "") for rep in r.replacements), r.replacements
    synth = m.synthesizer()
    assert synth.collisions_with_store() == [] and synth.failed_closed == {}
    for e in st.all():
        if e.kind in ("PERSON", "ORG"):
            assert not (_words(st.synthetic(e.code)) & real_words), (e.kind, st.synthetic(e.code))
    assert m.unmask(outs[0].text) == texts[0]
