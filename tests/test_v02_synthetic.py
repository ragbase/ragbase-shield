"""v0.2 synthetic replacement mode (owner SYNTH; design docs/V02_DESIGN.md section 4.5).

Every name, number and address below is invented for these tests (none comes from a benchmark).
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import pytest

from ragbase_shield import cli, config, service
from ragbase_shield import vault as V
from ragbase_shield.engine import Masker, MemoryStore, Synthesizer, shift_date_text
from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import synthetic as sy
from ragbase_shield.engine.masker import entity_norm
from ragbase_shield.engine.normalize import fold_word
from ragbase_shield.restore_utils import restore_for_output

SEED = b"0123456789abcdef0123456789abcdef"
FIXTURES = Path(__file__).parent / "fixtures" / "docs"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

TEXT = ("Madame Clémence MORVANDIAU, née le 14 mars 1979, demeurant 14 rue des Glycines, 59300 Valenciennes, "
        "courriel clemence.morvandiau@exemple-morvandiau.fr, tél. 06 12 34 56 78,\n"
        "CONTRE la société LAMBRETTI CONSEIL SAS (SIREN 552 100 554), représentée par M. Ugo FERRACCI-DAUBEL.\n"
        "Mme Morvandiau a écrit à Lambretti Conseil. C. Morvandiau et son conseil Me Ferracci-Daubel. "
        "IBAN FR76 3000 6000 0112 3456 7890 189. Dossier PERSONNE_A. Née le 14/03/1979 à Lille.\n")
SECRETS = ("Morvandiau", "MORVANDIAU", "Clémence", "Lambretti", "LAMBRETTI", "Ferracci", "FERRACCI", "Daubel",
           "exemple-morvandiau", "06 12 34 56 78", "552 100 554", "Glycines", "3000 6000 0112", "14 mars 1979",
           "14/03/1979")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def leaks(text: str, secrets=SECRETS) -> list[str]:
    low = _fold(text)
    return [s for s in secrets if _fold(s) in low]


def _store(*entities: tuple[str, str]) -> tuple[MemoryStore, list]:
    st = MemoryStore()
    ents = [st.add(k, v, entity_norm(k, v)) for k, v in entities]
    return st, ents


def _synth(*entities: tuple[str, str], lang: str = "fr", **kw):
    st, ents = _store(*entities)
    return Synthesizer(SEED, lang, st, **kw), st, ents


# ------------------------------------------------------------------------------------------ generator

def test_same_seed_same_store_gives_the_same_value():
    s1, st1, e1 = _synth(("PERSON", "Gontran Velquier"), ("ORG", "Brunsvald Optique SAS"))
    s2, st2, e2 = _synth(("PERSON", "Gontran Velquier"), ("ORG", "Brunsvald Optique SAS"))
    assert [s1.value_for(e) for e in e1] == [s2.value_for(e) for e in e2]
    st3, e3 = _store(("PERSON", "Gontran Velquier"), ("ORG", "Brunsvald Optique SAS"))
    other = Synthesizer(b"f" * 32, "fr", st3)
    assert other.value_for(e3[0]) != s1.value_for(e1[0])  # another seed: another pseudonym


def test_value_is_kept_once_given_and_differs_from_every_real_value():
    s, st, ents = _synth(("PERSON", "Gontran Velquier"), ("PERSON", "Marthe Velquier"), ("PERSON", "Odile Prat"))
    first = s.value_for(ents[0])
    assert s.value_for(ents[0]) == first and st.synthetic(ents[0].code) == first
    fakes = [s.value_for(e) for e in ents]
    assert len(set(fakes)) == 3
    real_words = {fold_word(w) for e in ents for w in e.value.split()}
    for f in fakes:
        assert not real_words & {fold_word(w) for w in f.split()}
        assert fold_word(f) not in {e.norm for e in ents}


def test_shared_real_surname_gives_one_fake_surname_and_sex_is_kept():
    s, st, ents = _synth(("PERSON", "Gontran Velquier"), ("PERSON", "Marthe Velquier"), ("PERSON", "Sabine Prat"))
    f0, f1, f2 = (s.value_for(e) for e in ents)
    assert f0.split()[-1] == f1.split()[-1] and f0.split()[0] != f1.split()[0]
    assert f2.split()[-1] != f0.split()[-1]
    lists = sy.synthetic_lists("fr")
    assert f1.split()[0] in lists["first_f"] and f2.split()[0] in lists["first_f"]   # Marthe, Sabine: F
    assert f0.split()[0] in lists["first_m"]                                           # Gontran: M


def test_person_shape_is_kept_compound_first_name_particles_initials_and_case():
    s, st, ents = _synth(("PERSON", "Jean-Pierre DUPONTEL"), ("PERSON", "Hélène de La Rochère-Vasseur"),
                         ("PERSON", "Martine G."))
    f0, f1, f2 = (s.value_for(e) for e in ents)
    assert re.fullmatch(r"[^\W\d_]+-[^\W\d_]+ [A-ZÀ-Ý]+", f0), f0
    assert f1.startswith("Hélène ") is False and " de La " in f1 and "-" in f1.split()[-1]
    assert re.fullmatch(r"[^\W\d_]+ [A-Z]\.", f2), f2


def test_company_keeps_generic_words_and_legal_form():
    s, st, ents = _synth(("ORG", "Brasseries Velanor de Quimpertin SAS"), ("ORG", "Garage du Centre"),
                         ("ORG", "société Brunsvald Avocats"))
    f0, f1, f2 = (s.value_for(e) for e in ents)
    assert f0.startswith("Brasseries ") and f0.endswith(" SAS") and " de " in f0 and "Velanor" not in f0
    assert f1.startswith("Garage du ") and f1 != "Garage du Centre"
    assert f2.startswith("société ") and f2.endswith(" Avocats") and "Brunsvald" not in f2


def test_email_links_to_the_fake_person_and_company_and_uses_a_reserved_domain():
    s, st, ents = _synth(("PERSON", "Gontran Velquier"), ("ORG", "Brunsvald Optique SAS"),
                         ("EMAIL", "g.velquier@brunsvald-optique.fr"), ("EMAIL", "contact@gmail.com"))
    person, org = s.value_for(ents[0]), s.value_for(ents[1])
    mail = s.value_for(ents[2])
    local, _, host = mail.partition("@")
    assert host.endswith("." + sy.SYNTHETIC_TLD) and "brunsvald" not in host and "velquier" not in mail
    # v0.4 S0 (class C): the real initial "g." is never kept: the fake person's initial and surname
    assert local == f"{sy._ascii(person.split()[0])[:1]}.{sy._ascii(person.split()[-1])}" and local[:1] != "g"
    assert sy._ascii(org.split()[0]) in host
    other = s.value_for(ents[3])
    assert other.endswith("." + sy.SYNTHETIC_TLD) and "gmail" not in other


@pytest.mark.parametrize("real, pattern", [
    ("06 12 34 56 78", r"06 39 98 \d\d \d\d"),
    ("01 42 68 53 00", r"01 99 00 \d\d \d\d"),
    ("+33 6 12 34 56 78", r"\+33 6 39 98 \d\d \d\d"),
    ("+1 (415) 555-2671", r"\+1 \([2-9]\d\d\) 555-01\d\d"),
    ("07700 123456", r"07700 900\d\d\d"),
    ("+44 20 7123 4567", r"\+44 20 7946 0\d\d\d"),
])
def test_phones_use_fiction_ranges_and_keep_separators(real, pattern):
    s, st, ents = _synth(("PHONE", real))
    fake = s.value_for(ents[0])
    assert re.fullmatch(pattern, fake), fake
    assert det.structured_norm("PHONE", fake) != det.structured_norm("PHONE", real)


def test_identifiers_are_valid_shape_preserving_and_different():
    s, st, ents = _synth(("IBAN", "FR76 3000 6000 0112 3456 7890 189"), ("SIREN", "552 100 554"),
                         ("SIRET", "552 100 554 00013"), ("VAT", "FR 40 303 265 045"),
                         ("CARD", "4970 1012 3456 7890"), ("NIR", "1 85 03 75 112 034 42"), ("NIR", "123-45-6789"),
                         ("CASE_REF", "RG 24/01234"), ("ID_CODE", "AB-123-CD"))
    fakes = [s.value_for(e) for e in ents]
    iban, siren, siret, vat, card, nir, ssn, rg, ident = fakes
    assert det.iban_valid(iban) and iban.startswith("FR76 0000 0") and len(iban) == len(ents[0].value)
    assert det.siren_valid(siren) and re.fullmatch(r"\d{3} \d{3} \d{3}", siren)
    assert det.siret_valid(siret) and re.fullmatch(r"\d{3} \d{3} \d{3} \d{5}", siret)
    assert det.vat_fr_valid(vat) and vat.startswith("FR ")
    assert det.luhn_valid(card.replace(" ", "")) and card.startswith("4242 42")
    assert det.nir_valid(nir) and re.fullmatch(r"\d \d\d \d\d \d\d \d{3} \d{3} \d\d", nir)
    assert ssn.startswith("987-65-432")
    assert rg.startswith("RG ") and re.fullmatch(r"RG \d\d/\d{5}", rg) and rg != "RG 24/01234"
    # v0.4 S0 (class K): the public label "RG" stays, the letter code "AB" of an identifier gets a fake code
    assert re.fullmatch(r"[A-Z]{2}-\d{3}-[A-Z]{2}", ident) and ident[0] != "A" and ident[1] != "B"
    assert "CD" not in ident
    for e, f in zip(ents, fakes):
        assert re.sub(r"\W", "", f) != re.sub(r"\W", "", e.value)
    assert s.collisions["NIR"] == 2 and s.collisions["SIREN"] == 1


def test_birth_dates_shift_30_to_400_days_in_the_same_form():
    s, st, ents = _synth(("BIRTHDATE", "14 mars 1979"), ("BIRTHDATE", "07/11/1985"), ("BIRTHDATE", "1981-06-02"),
                         ("BIRTHDATE", "1er mars 1990"), ("BIRTHDATE", "March 14, 1975"))
    from datetime import date
    for e in ents:
        f = s.value_for(e)
        d0 = date.fromisoformat(det.structured_norm("BIRTHDATE", e.value))
        d1 = date.fromisoformat(det.structured_norm("BIRTHDATE", f))
        assert 30 <= abs((d1 - d0).days) <= 400, (e.value, f)
    assert re.fullmatch(r"\d{1,2} [a-zéû]+ \d{4}", s.value_for(ents[0]))
    assert re.fullmatch(r"\d\d/\d\d/\d{4}", s.value_for(ents[1]))
    assert re.fullmatch(r"\d{4}-\d\d-\d\d", s.value_for(ents[2]))
    assert re.fullmatch(r"[A-Z][a-z]+ \d{1,2}, \d{4}", s.value_for(ents[4]))
    assert shift_date_text("le 31 janv. 2001", 40) == "le 12 mars 2001"
    assert shift_date_text("02.01.99", 40) == "11.02.99"
    assert shift_date_text("rien ici", 40) is None


def test_address_is_a_street_from_the_list_with_a_postcode_and_town():
    s, st, ents = _synth(("ADDRESS", "14 rue des Glycines, 59300 Valenciennes"), ("ADDRESS", "3 allée des Peupliers"))
    a, b = (s.value_for(e) for e in ents)
    assert re.fullmatch(r"\d{1,3} .+, \d{5} .+", a) and "Glycines" not in a and "Valenciennes" not in a
    assert re.fullmatch(r"\d{1,3} \D+", b) and "Peupliers" not in b


def test_url_keeps_scheme_and_path_length_with_a_reserved_domain():
    s, st, ents = _synth(("ORG", "Brunsvald Optique SAS"), ("URL", "https://www.brunsvald-optique.fr/contact/42"))
    org = s.value_for(ents[0])
    url = s.value_for(ents[1])
    assert url.startswith("https://www.") and url.split("/")[2].endswith("." + sy.SYNTHETIC_TLD)
    assert sy._ascii(org.split()[0]) in url and "brunsvald" not in url
    assert len(url.split("/")[3]) == len("contact") and re.fullmatch(r"\d\d", url.split("/")[4])


def test_fake_values_never_hold_a_whitelist_or_dictionary_surname():
    lists = sy.synthetic_lists("fr")
    import ragbase_shield.engine.names as nm
    assert all(not nm._lexicon_word(fold_word(w)) for w in lists["last"])
    assert lists["first_f"] and lists["first_m"] and lists["org"] and lists["streets"] and lists["towns"]
    en = sy.synthetic_lists("en")
    assert en["last"] and en["towns"] and any("," in t for _c, t in en["towns"])


# ------------------------------------------------------------------------------------------ render / restore

def test_render_each_variant_and_restore_it():
    s, st, ents = _synth(("PERSON", "Jean-Pierre Dupontel"), ("ORG", "Brasseries Velanor de Quimpertin SAS"))
    p, o = ents
    fp, fo = s.value_for(p), s.value_for(o)
    cases = ["Dupontel", "DUPONTEL", "J.-P. Dupontel", "Jean-Pierre", "Dupontel, Jean-Pierre", "JPD", "J. P.",
             "Jean-Pierre DUPONTEL", "Dupomtel", "Dupontel's"]
    for surf in cases:
        r = s.render(p, fp, surf)
        assert "dupontel" not in _fold(r) and "jean" not in _fold(r), (surf, r)
        back = s.restore(p, fp, r)
        assert _fold(back).replace("dupomtel", "dupontel") == _fold(surf).replace("dupomtel", "dupontel"), (surf, r, back)
    for surf in ["BVQ", "Brasseries Velanor", "société Brasseries Velanor de Quimpertin", "BVQ-310", "Velanor"]:
        r = s.render(o, fo, surf)
        assert "velanor" not in _fold(r) and "quimpertin" not in _fold(r), (surf, r)
        assert s.restore(o, fo, r) == surf, (surf, r)
    assert s.render(p, fp, "DUPONTEL").isupper() and s.render(p, fp, "Dupontel")[1:].islower()


def test_render_of_other_kinds_lays_the_fake_over_the_text_form():
    s, st, ents = _synth(("PHONE", "06 12 34 56 78"), ("BIRTHDATE", "14 mars 1979"), ("IBAN", "FR7630006000011234567890189"))
    ph, bd, ib = ents
    fph, fbd, fib = (s.value_for(e) for e in ents)
    assert re.fullmatch(r"06\.39\.98\.\d\d\.\d\d", s.render(ph, fph, "06.12.34.56.78"))
    assert s.restore(ph, fph, s.render(ph, fph, "06.12.34.56.78")) == "06.12.34.56.78"
    other = s.render(bd, fbd, "14/03/1979")
    assert re.fullmatch(r"\d\d/\d\d/\d{4}", other) and other != "14/03/1979"
    assert s.restore(bd, fbd, other) == "14/03/1979"
    spaced = s.render(ib, fib, "FR76 3000 6000 0112 3456 7890 189")
    assert spaced.count(" ") == 6 and det.iban_valid(spaced)


# ------------------------------------------------------------------------------------------ masker

def test_masker_synthetic_mode_round_trip_and_mode():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    assert m.mode == "rules+synthetic"
    r = m.mask(TEXT)
    assert r.mode == "synthetic" and len(r.codes) == len(r.spans) == len(r.replacements) and r.spans
    assert not leaks(r.text), leaks(r.text)
    assert "PERSONNE_" not in r.text and "PERSONNE-A" in r.text  # code-like real text still escaped
    back, unknown = m.unmask_report(r.text)
    assert back == TEXT.replace("PERSONNE_A", "PERSONNE-A") and unknown == []
    # the same fake identity across mentions: surname alone, initial + surname, upper case
    fake_surname = st.synthetic("PERSONNE_A").split()[-1]
    assert r.text.count(fake_surname.upper()) >= 1 and f"Mme {fake_surname.title()}" in r.text


def test_masking_a_synthetic_answer_again_is_idempotent_in_synthetic_mode_and_gives_codes_in_codes_mode():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    masked = m.mask(TEXT).text
    answer = masked.replace("CONTRE", "Contre") + "\nMerci, " + st.synthetic("PERSONNE_B").split()[-1] + ".\n"
    assert m.mask(answer).text == answer
    assert len(st.all()) == len({e.code for e in st.all()}) and not any("Merci" in e.value for e in st.all())
    codes = Masker(st, use_ner=False).mask(answer)
    assert codes.mode == "codes" and "PERSONNE_A" in codes.text and "PERSONNE_B" in codes.text
    assert not leaks(codes.text) and not [w for w in st.synthetic("PERSONNE_A").split() if w in codes.text]


def test_unmask_handles_partial_upper_possessive_and_reports_altered_names():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    m.mask("Madame Clémence MORVANDIAU et M. Ugo FERRACCI-DAUBEL se sont rencontrés.")
    fake_a, fake_b = st.synthetic("PERSONNE_A"), st.synthetic("PERSONNE_B")
    first_a, sur_a = fake_a.split()[0], fake_a.split()[-1]
    altered = sur_a.title()[:-1] + ("z" if sur_a.lower().endswith("x") else "x")  # one edit away, never equal
    answer = (f"{sur_a.upper()} a écrit. {first_a} signe. Le dossier de {sur_a.title()}'s. "
              f"{fake_b.split()[-1].title()} répond. Et Monsieur {altered} aussi.")
    back, unknown = m.unmask_report(answer)
    assert "MORVANDIAU a écrit" in back and "Clémence signe" in back and "Morvandiau's" in back
    assert "Ferracci-Daubel répond" in back and unknown == []
    assert m.synthetic_altered(answer) == 1
    rep = restore_for_output(answer, m)
    assert rep.restored_synthetic == 4 and rep.unmatched_synthetic == 1 and rep.restored == 4
    assert rep.public()["unmatched_synthetic"] == 1 and "MORVANDIAU" not in repr(rep.public())


def test_restore_for_output_applies_the_form_fixes_to_synthetic_mentions():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    m.mask("Madame Agathe Ivernel-Soubise, salariée.")
    fake = st.synthetic("PERSONNE_A")
    rep = restore_for_output(f"Le contrat de {fake.split()[-1]} est joint.", m)
    assert rep.text == "Le contrat d'Ivernel-Soubise est joint." and rep.fixes["elision"] == 1


def test_rendering_that_would_leak_falls_back_to_the_code(monkeypatch):
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    monkeypatch.setattr(Synthesizer, "render", lambda self, ent, fake, surface, need="", vtoks=(): surface)
    r = m.mask("Madame Clémence MORVANDIAU écrit.")
    assert "PERSONNE_A" in r.text and not leaks(r.text)
    monkeypatch.setattr(Synthesizer, "render", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = m.mask("Madame Clémence MORVANDIAU écrit encore.")
    assert "PERSONNE_A" in r.text and not leaks(r.text)


def test_canary_and_codes_mode_are_unchanged_by_synthetic_values():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    out = m.mask(TEXT).text
    assert [sp.kind for sp in m.scan(out) if sp.source == "dictionary"] == []  # no real value left
    assert {sp.kind for sp in m.scan(TEXT) if sp.source == "dictionary"} >= {"PERSON", "ORG"}
    plain = Masker(st, use_ner=False).mask(TEXT)
    assert plain.mode == "codes" and "PERSONNE_A" in plain.text and not leaks(plain.text)


def test_upgraded_entity_keeps_its_fake_surname():
    st = MemoryStore()
    m = Masker(st, use_ner=False, replacement="synthetic")
    a = m.mask("M. Ouardi a signé.").text
    sur = st.synthetic("PERSONNE_A")
    b = m.mask("M. Mehdi Ouardi a signé. M. Ouardi aussi.").text
    assert st.all()[0].value == "Mehdi Ouardi" and st.synthetic("PERSONNE_A").endswith(" " + sur)
    assert b.count(sur) == 2 and a == f"M. {sur} a signé."
    assert m.unmask(b) == "M. Mehdi Ouardi a signé. M. Ouardi aussi."


@pytest.mark.parametrize("item", MANIFEST, ids=[m["doc"] for m in MANIFEST])
def test_no_gold_mention_in_any_synthetic_fixture(item):
    gold = json.loads((FIXTURES / item["gold"]).read_text(encoding="utf-8"))
    text = (FIXTURES / item["doc"]).read_text(encoding="utf-8")
    st = MemoryStore()
    for p in gold["parties"]:
        st.add(p["kind"], p["value"], entity_norm(p["kind"], p["value"]))
    m = Masker(st, use_ner=False, replacement="synthetic")
    out = m.mask(text).text
    low = _fold(out)
    words = set()
    for p in gold["parties"]:
        words |= {fold_word(w) for w in re.findall(r"[^\W\d_]{4,}", p["value"])}
    import ragbase_shield.engine.names as nm
    bad = [w for w in words if not nm._lexicon_word(w) and w not in nm.ORG_GENERIC and w not in nm.LEGAL_FORMS
           and re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low)]
    assert not bad, bad
    for mention in gold["mentions"]:
        if mention["checksum"]:
            assert re.sub(r"\W", "", mention["text"]) not in re.sub(r"\W", "", out)
    for kept in gold["keep_clear"]:
        assert _fold(kept["text"]) in low, kept["text"]
    # a name split over two lines is replaced whole, in codes mode too: same line count as the codes output
    assert m.unmask(out).count("\n") == Masker(st, use_ner=False).mask(text).text.count("\n")


# ------------------------------------------------------------------------------------------ vault

@pytest.fixture
def reg(tmp_path):
    r = V.Registry(tmp_path / "home")
    yield r
    r.close()


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "dossier"
    f.mkdir()
    (f / "note.txt").write_text("x", encoding="utf-8")
    return f


def test_vault_stores_synthetic_values_encrypted_and_unique(reg, folder):
    d = reg.add_dossier(folder, "Velquier c. Brunsvald")
    a = d.register("PERSON", "Gontran Velquier")
    b = d.register("PERSON", "Marthe Prat")
    assert d.synthetic(a.code) is None
    d.set_synthetic(a.code, "Firmin Ysembart")
    assert d.synthetic(a.code) == "Firmin Ysembart" and d.get_by_synthetic_norm("firmin ysembart").code == a.code
    with pytest.raises(V.VaultError):
        d.set_synthetic(b.code, "FIRMIN YSEMBART")  # taken (case and accents aside)
    d.set_synthetic(a.code, "Firmin Vaudrel")  # replaced
    assert d.get_by_synthetic_norm("firmin ysembart") is None and d.synthetic(a.code) == "Firmin Vaudrel"
    with pytest.raises(V.VaultError):
        d.set_synthetic("PERSONNE_ZZ", "x")
    raw = (reg.vaults_dir / f"{d.uuid}.db").read_bytes()
    assert b"Vaudrel" not in raw and b"Ysembart" not in raw and b"Velquier" not in raw
    assert len(d.synthetic_seed()) == 32 and d.synthetic_seed() == d.synthetic_seed()
    other = reg.add_dossier(folder.parent / "dossier2" if (folder.parent / "dossier2").mkdir() is None else folder)
    assert other.synthetic_seed() != d.synthetic_seed()
    assert d.entity_source(d.add("PERSON", "Odile Prat", "odile prat", source="ner").code) == "ner"
    assert d.add("PERSON", "Odile Prat", "odile prat").source == "ner"


def test_vault_shapes_and_settings(reg, folder):
    d = reg.add_dossier(folder)
    d.add_shape("EMPLOYEE_ID", "EMP-ddddd")
    d.add_shape("EMPLOYEE_ID", "EMP-ddddd")
    assert d.shapes() == [("EMPLOYEE_ID", "EMP-ddddd")]
    with pytest.raises(ValueError):
        d.add_shape("PLANET", "x")
    assert d.setting("replacement") is None and d.settings() == {}
    d.set_setting("replacement", "synthetic")
    d.set_setting("language", "en")
    assert d.settings() == {"language": "en", "replacement": "synthetic"}
    d.set_setting("replacement", None)
    assert d.setting("replacement") is None
    with pytest.raises(ValueError):
        d.set_setting("replacement", "maybe")
    with pytest.raises(ValueError):
        d.setting("colour")


def test_schema_1_vault_is_migrated_in_place(tmp_path):
    """A vault written by v0.1 (no synthetic columns, no shapes table) opens, migrates and keeps its data."""
    import sqlite3

    home = tmp_path / "home"
    folder = tmp_path / "d"
    folder.mkdir()
    r = V.Registry(home)
    d = r.add_dossier(folder, "Ancien")
    d.register("PERSON", "Gontran Velquier")
    path = r.vaults_dir / f"{d.uuid}.db"
    r.close()
    con = sqlite3.connect(str(path))  # rebuild the v0.1 layout by hand
    con.executescript("""
        CREATE TABLE entities_v1(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL, idx INTEGER NOT NULL, code TEXT NOT NULL UNIQUE,
          norm_mac BLOB NOT NULL, norm_enc BLOB NOT NULL, value_enc BLOB NOT NULL,
          source TEXT NOT NULL, created REAL NOT NULL,
          UNIQUE(kind, norm_mac), UNIQUE(kind, idx));
        INSERT INTO entities_v1 SELECT id, kind, idx, code, norm_mac, norm_enc, value_enc, source, created
          FROM entities;
        DROP TABLE entities;
        ALTER TABLE entities_v1 RENAME TO entities;
        DROP TABLE shapes;
        UPDATE meta SET v='1' WHERE k='schema';
    """)
    con.close()
    con = sqlite3.connect(str(path))
    assert "synth_enc" not in {r_[1] for r_ in con.execute("PRAGMA table_info(entities)")}
    con.close()
    r = V.Registry(home)
    d = r.get("DOSSIER_1")
    assert d._db.query("SELECT v FROM meta WHERE k='schema'") == [("2",)]
    assert [e.value for e in d.all()] == ["Gontran Velquier"] and d.synthetic("PERSONNE_A") is None
    d.set_synthetic("PERSONNE_A", "Firmin Ysembart")
    d.add_shape("ACCOUNT_NUMBER", "ACC-dddddd")
    r.close()
    r = V.Registry(home)
    d = r.get("DOSSIER_1")
    assert d.synthetic("PERSONNE_A") == "Firmin Ysembart" and d.shapes() == [("ACCOUNT_NUMBER", "ACC-dddddd")]
    r.close()


def test_export_version_2_round_trip_and_version_1_import(reg, folder, tmp_path):
    d = reg.add_dossier(folder, "Velquier c. Brunsvald")
    a = d.register("PERSON", "Gontran Velquier")
    d.set_synthetic(a.code, "Firmin Ysembart")
    d.add_shape("EMPLOYEE_ID", "EMP-ddddd")
    d.set_setting("replacement", "synthetic")
    export = d.export(tmp_path / "h.shield", "phrase de passe longue")
    assert b"Ysembart" not in export.read_bytes()
    r2 = V.Registry(tmp_path / "h2")
    imp = r2.import_(export, "phrase de passe longue")
    assert imp.synthetic("PERSONNE_A") == "Firmin Ysembart" and imp.shapes() == [("EMPLOYEE_ID", "EMP-ddddd")]
    assert imp.settings() == {"replacement": "synthetic"}
    assert imp.get_by_synthetic_norm("firmin ysembart").value == "Gontran Velquier"
    r2.close()
    good1 = {"format": V._EXPORT_FORMAT, "version": 1, "title": "t", "folder": "", "locale": "fr",
             "entities": [{"kind": "PERSON", "idx": 0, "code": "PERSONNE_A", "value": "v", "norm": "v",
                           "source": "user"}],
             "counters": {"PERSON": 1}, "clear": [], "documents": []}
    V._validate_payload(good1)
    good2 = dict(good1, version=2, shapes=[{"kind": "EMPLOYEE_ID", "template": "EMP-ddddd"}],
                 settings={"replacement": "codes"},
                 entities=[dict(good1["entities"][0], synthetic="Firmin Ysembart", source="ner")])
    V._validate_payload(good2)
    for mutate in (lambda p: p["entities"][0].update(synthetic=""),
                   lambda p: p.update(settings={"replacement": "maybe"}),
                   lambda p: p.update(shapes=[{"kind": "PLANET", "template": "x"}]),
                   lambda p: p.update(version=3)):
        bad = json.loads(json.dumps(good2))
        mutate(bad)
        with pytest.raises((ValueError, KeyError, TypeError)):
            V._validate_payload(bad)
    bad = json.loads(json.dumps(good1))
    bad["entities"][0]["synthetic"] = "x"  # a version-1 file never carries synthetic values
    with pytest.raises(ValueError):
        V._validate_payload(bad)


# ------------------------------------------------------------------------------------------ service, CLI, Desk

@pytest.fixture(autouse=True)
def _fresh_service(monkeypatch):
    for name in cli._AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_REPLACEMENT", raising=False)
    service.reset()
    yield
    service.reset()


@pytest.fixture
def case(tmp_path):
    folder = tmp_path / "Dossier Morvandiau"
    folder.mkdir()
    (folder / "assignation.txt").write_text(TEXT, encoding="utf-8")
    info = service.add_dossier(folder, "Morvandiau c. Lambretti Conseil SAS")
    return {"folder": folder, "code": info["code"]}


def test_service_mask_text_synthetic_round_trip_and_found(case):
    code = case["code"]
    r = service.mask_text(TEXT, code, include_values=True, replacement="synthetic")
    assert r["mode"] == "synthetic" and not leaks(r["masked"]) and "PERSONNE_" not in r["masked"]
    kinds = {f["kind"] for f in r["found"]}
    assert {"PERSON", "ORG", "EMAIL", "PHONE", "IBAN", "SIREN"} <= kinds
    assert all(f["synthetic"] and f["value"] for f in r["found"])
    back = service.restore_report(r["masked"] + " PERSONNE_ZZ", code)
    assert back["text"] == TEXT.replace("PERSONNE_A", "PERSONNE-A") + " PERSONNE_ZZ"
    assert back["unknown_codes"] == ["PERSONNE_ZZ"] and back["restored_synthetic"] == back["restored"] > 5
    assert back["unmatched_synthetic"] == 0
    ents = service.entities(code)
    assert all("synthetic" in e for e in ents) and any(e["synthetic"] for e in ents)
    plain = service.mask_text(TEXT, code)
    assert plain["mode"] == "codes" and "PERSONNE_A" in plain["masked"]
    with pytest.raises(service.ShieldError):
        service.mask_text(TEXT, code, replacement="maybe")


def test_service_dossier_setting_and_env_default(case, monkeypatch):
    code = case["code"]
    assert service.status()["replacement"] == "codes"
    assert service.set_dossier_setting(code, "replacement", "synthetic") == {"replacement": "synthetic"}
    assert service.list_dossiers(include_private=True)[0]["replacement"] == "synthetic"
    r = service.mask_text(TEXT, code)
    assert r["mode"] == "synthetic" and not leaks(r["masked"])
    page = service.read_document(code, "DOC_1")
    assert not leaks(page["text"]) and "PERSONNE_" not in page["text"]
    hits = service.search(code, "Dossier")
    assert hits and not leaks(json.dumps(hits, ensure_ascii=False))
    assert service.set_dossier_setting(code, "replacement", None) == {}
    assert service.mask_text(TEXT, code)["mode"] == "codes"
    monkeypatch.setenv("RAGBASE_SHIELD_REPLACEMENT", "synthetic")
    assert service.status()["replacement"] == "synthetic"
    assert service.mask_text("M. Ugo FERRACCI-DAUBEL")["mode"] == "synthetic"
    assert service.mask_text(TEXT, code, replacement="codes")["mode"] == "codes"
    with pytest.raises(service.ShieldError):
        service.set_dossier_setting(code, "colour", "blue")


def test_hooks_and_canary_stay_in_codes_mode(case):
    code = case["code"]
    service.set_dossier_setting(code, "replacement", "synthetic")
    masked, added = service.protect("Lettre pour Clémence Morvandiau et Lambretti Conseil.")
    assert "PERSONNE_A" in masked and not leaks(masked) and "PERSONNE_A" in added
    assert service.default().guard_output("Clémence Morvandiau") in ("[PERSONNE]", "PERSONNE_A")
    assert all(h["code"] for h in service.scan_text("Mme Morvandiau"))


def test_cli_mask_mode_set_and_agent_refusal(case, capsys, monkeypatch):
    code = case["code"]
    monkeypatch.setattr(sys, "stdin", io.StringIO(TEXT))
    rc = cli.main(["mask", "--dossier", code, "--mode", "synthetic"])
    out, err = capsys.readouterr()
    assert rc == 0 and not leaks(out) and "PERSONNE_" not in out and "synthétique" in err
    monkeypatch.setattr(sys, "stdin", io.StringIO(out))
    rc = cli.main(["restore", "--dossier", code, "-"])
    out2, err2 = capsys.readouterr()
    assert rc == 0 and "MORVANDIAU" in out2 and "pseudonyme(s) synthétique(s)" in err2
    monkeypatch.setattr(sys, "stdin", io.StringIO("M. Ugo FERRACCI-DAUBEL"))
    rc = cli.main(["mask", "--synthetic"])
    out, err = capsys.readouterr()
    assert rc == 0 and "FERRACCI" not in out and "sans --dossier" in err
    rc = cli.main(["set", code, "--replacement", "synthetic"])
    out, err = capsys.readouterr()
    assert rc == 0 and "remplacement = synthetic" in out and "pseudonymisation" in out
    assert service.list_dossiers(include_private=True)[0]["replacement"] == "synthetic"
    rc = cli.main(["set", code, "--replacement", "default", "--language", "en"])
    out, err = capsys.readouterr()
    assert rc == 0 and "langue = en" in out and "remplacement" not in out
    rc = cli.main(["set", code])
    assert rc == 2
    capsys.readouterr()
    monkeypatch.setenv("CLAUDECODE", "1")
    rc = cli.main(["set", code, "--replacement", "synthetic"])
    out, err = capsys.readouterr()
    assert rc == 3 and "modifie le coffre" in err
    assert service.list_dossiers(include_private=True)[0]["replacement"] == "codes"


def test_desk_mask_accepts_replacement_and_restore_reports_synthetic(case):
    from starlette.testclient import TestClient
    from ragbase_shield.desk import app as desk

    token = "desk-test-token-" + "a1b2c3d4" * 4
    h = {"X-Shield-Token": token}
    with TestClient(desk.create_app(port=7878, token=token), base_url="http://127.0.0.1:7878") as client:
        r = client.post("/api/mask", json={"text": TEXT, "dossier": case["code"], "replacement": "synthetic"},
                        headers=h)
        assert r.status_code == 200 and r.json()["mode"] == "synthetic" and not leaks(r.json()["masked"])
        assert all(f.get("synthetic") for f in r.json()["found"])
        r2 = client.post("/api/restore", json={"text": r.json()["masked"], "dossier": case["code"]}, headers=h)
        assert r2.status_code == 200 and "MORVANDIAU" in r2.json()["text"] and r2.json()["restored_synthetic"] > 5
        assert r2.json()["unmatched_synthetic"] == 0
        bad = client.post("/api/mask", json={"text": TEXT, "replacement": "maybe"}, headers=h)
        assert bad.status_code == 400
        st = client.get("/api/status", headers=h).json()
        assert st["replacement"] == "codes" and st["replacements"] == ["codes", "synthetic"]


def test_verify_covers_the_synthetic_mode(capsys):
    counts = cli.run_verify(lambda s, p, d: print(s, p, d))
    out = capsys.readouterr().out
    assert counts["LEAK"] == 0 and counts["ERROR"] == 0
    assert "CLEAN cli mask --mode synthetic" in out and "CLEAN restauration (mode synthétique)" in out


def test_leak_gate_in_synthetic_mode_over_every_fixture(tmp_path):
    for item in MANIFEST:
        gold = json.loads((FIXTURES / item["gold"]).read_text(encoding="utf-8"))
        folder = tmp_path / item["doc"].split(".")[0]
        folder.mkdir()
        shutil.copy(FIXTURES / item["doc"], folder / item["doc"])
        code = service.add_dossier(folder, gold["title"])["code"]
        for p in gold["parties"]:
            service.register(code, p["kind"], p["value"])
        service.set_dossier_setting(code, "replacement", "synthetic")
        page = service.read_document(code, "DOC_1", max_chars=50000)["text"]
        import ragbase_shield.engine.names as nm
        secrets = [p["value"] for p in gold["parties"]] + [mm["text"] for mm in gold["mentions"] if mm["checksum"]]
        secrets += [p["value"].split()[-1] for p in gold["parties"]
                    if p["kind"] == "PERSON" and not nm._lexicon_word(fold_word(p["value"].split()[-1]))]
        low = _fold(page)
        found = [s for s in secrets if len(s) >= 5
                 and re.search(r"(?<![a-z])" + re.escape(_fold(s)) + r"(?![a-z])", low)]
        assert not found, (item["doc"], found)
        st = service.status()
        assert not [s for s in secrets if len(s) >= 5 and _fold(s) in _fold(json.dumps(st, ensure_ascii=False))]
        service.reset()
