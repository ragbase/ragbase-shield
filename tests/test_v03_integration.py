"""v0.3 integration (2026-10-21): the four owner parts work together in the Masker pipeline.

rules -> directory -> NER gated -> merge -> resolve with export evidence -> guards -> codes / synthetic.
Every name, company, address and identifier here is invented.
"""
from __future__ import annotations

import os

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as dr
from ragbase_shield.engine import names as nm
from ragbase_shield.engine import ner as nr


class _Backend:
    """A fake NER backend: fixed finds per text (``(text, model label, score)``), the protocol of ``ner.NerBackend``."""

    name = "callable:test"

    def __init__(self, finds, labels=None):
        self.finds = finds
        self.labels = labels or {"company": "ORG", "person": "PERSON", "username": "USERNAME",
                                 "vessel": "ID_CODE", "building": "ID_CODE"}
        self.thresholds = {label: 0.4 for label in self.labels}

    def predict(self, chunks):
        out = []
        for ch in chunks:
            spans = []
            for text, label, score in self.finds:
                i = ch.find(text)
                while i >= 0:
                    spans.append(nr.NerSpan(i, i + len(text), label, score))
                    i = ch.find(text, i + 1)
            out.append(spans)
        return out


def _ner_masker(finds, store=None, **labels):
    st = store if store is not None else MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    m.use_ner = True  # the test environment has no model installed: the fake backend stands in for it
    m._backend = _Backend(finds, labels or None)
    m._backend_tried = True
    return m, st


# ---------------------------------------------------------------------------------------------------------------
# rules go through the shared entry point and the span refinement (S1+S4)
# ---------------------------------------------------------------------------------------------------------------

def test_english_rules_go_through_the_refinement_and_a_domain_of_the_text_names_the_company():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    r = m.mask("Hello from Vrennick (billing@vrennick.test). Vrennick ships Monday.")
    codes = {e.value: e.code for e in st.all()}
    assert "Vrennick" in codes and st.get_by_norm("ORG", "vrennick") is not None
    assert r.text == f"Hello from {codes['Vrennick']} (EMAIL_1). {codes['Vrennick']} ships Monday.", r.text


def test_person_of_company_keeps_the_person_and_the_company_apart():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    r = m.mask("Hi Marguerite, Tobias Quillanmere of Brightholm Logistics LLC called back. Regards, Tobias")
    kinds = {e.value: e.kind for e in st.all()}
    assert kinds.get("Tobias Quillanmere") == "PERSON" and kinds.get("Brightholm Logistics") == "ORG", kinds
    assert "Quillanmere" not in r.text and "Brightholm" not in r.text
    assert " of COMPANY_A LLC" in r.text, r.text


def test_french_rules_keep_the_court_clear_and_mask_the_company_core():
    st = MemoryStore(locale="fr")
    m = Masker(st, locale="fr", use_ner=False)
    r = m.mask("Maître Ombeline Talvez, avocate de la SAS Les Tilleuls, a saisi le Tribunal judiciaire de Nantes.")
    assert r.text == "Maître PERSONNE_A, avocate de la SAS SOCIETE_A, a saisi le Tribunal judiciaire de Nantes.", r.text


def test_cover_policy_covers_the_legal_form_keeps_it_readable_and_stores_the_core(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", "cover")
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", raising=False)
    assert nm.legal_form_policy() == "cover"
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    r = m.mask("Acme Widgets, Inc. signed with Northvale Analytics LLC today.")
    assert r.text == "COMPANY_A, Inc. signed with COMPANY_B LLC today.", r.text
    assert [s.value for s in r.spans] == ["Acme Widgets, Inc.", "Northvale Analytics LLC"]
    assert sorted(e.value for e in st.all()) == ["Acme Widgets", "Northvale Analytics"]
    r2 = m.mask("Acme Widgets called; Northvale Analytics LLC replied.")
    assert r2.text == "COMPANY_A called; COMPANY_B LLC replied.", r2.text
    st2 = MemoryStore(locale="fr")
    m2 = Masker(st2, locale="fr", use_ner=False)
    r3 = m2.mask("La SAS Les Tilleuls et la société Dupraz Frères SARL ont signé.")
    assert r3.text == "La SAS SOCIETE_A et la société SOCIETE_B SARL ont signé.", r3.text
    assert sorted(e.value for e in st2.all()) == ["Dupraz Frères", "Les Tilleuls"]
    assert m2.unmask(r3.text) == "La SAS Les Tilleuls et la société Dupraz Frères SARL ont signé."


def test_default_policy_is_clear_and_unchanged():
    assert nm.legal_form_policy() == "clear"
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    r = m.mask("Acme Widgets, Inc. signed with Northvale Analytics LLC today.")
    assert r.text == "COMPANY_A, Inc. signed with COMPANY_B LLC today.", r.text
    assert [s.value for s in r.spans] == ["Acme Widgets", "Northvale Analytics"]


# ---------------------------------------------------------------------------------------------------------------
# directory -> rules (S3 -> S4): the dossier's domain labels name the companies
# ---------------------------------------------------------------------------------------------------------------

def test_directory_domains_feed_the_company_rules_and_full_names_are_seeded():
    eml = (b"From: Lucasta Fennimore <lucasta.fennimore@wrexholm.example>\r\n"
           b"To: Percival Oddington <p.oddington@wrexholm.example>\r\nSubject: hi\r\n\r\nping\r\n")
    d = dr.build([("eml", eml)], lang="en")
    assert "wrexholm" in d.domains and len(d) == 2
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, directory=d)
    r = m.mask("Wrexholm confirmed; Fennimore and Oddington will attend.")
    codes = {e.value: e.code for e in st.all()}
    assert codes["Lucasta Fennimore"] in r.text and codes["Percival Oddington"] in r.text
    assert "Wrexholm" not in r.text and st.get_by_norm("ORG", "wrexholm") is not None, r.text
    assert m._domains() == ["wrexholm"]


# ---------------------------------------------------------------------------------------------------------------
# gated NER (S7) in the masker: signals decide the store variants; the watch list reaches the result
# ---------------------------------------------------------------------------------------------------------------

def test_unconfirmed_model_find_is_masked_in_place_and_stays_contained():
    m, st = _ner_masker([("Quorvane Tessifer", "company", 0.8)])
    r = m.mask("We met Quorvane Tessifer on Monday.")
    assert r.text == "We met COMPANY_A on Monday." and [(e.value, e.source) for e in st.all()] == [("Quorvane Tessifer", "ner")]
    r2 = m.mask("Later quorvane tessifer wrote, Quorvane alone wrote, and Quorvane Tessifer wrote.")
    # the exact capitalised surface is known; no lower-case and no partial variant until a signal confirms it
    assert r2.text == "Later quorvane tessifer wrote, Quorvane alone wrote, and COMPANY_A wrote.", r2.text


def test_confirmed_model_find_is_a_detected_entity_with_full_variants():
    m, st = _ner_masker([("Ilvane Torquist", "person", 0.8)])
    r = m.mask("Dear Ilvane Torquist, the file is attached.")
    assert r.text == "Dear PERSON_A, the file is attached."
    assert [(e.value, e.source) for e in st.all()] == [("Ilvane Torquist", "detected")]
    r2 = m.mask("Then Torquist alone, and Mr. Torquist, and Ilvane Torquist again.")
    assert r2.text == "Then PERSON_A alone, and Mr. PERSON_A, and PERSON_A again.", r2.text


def test_unconfirmed_person_find_gets_no_surname_variant():
    m, st = _ner_masker([("Ilvane Torquist", "person", 0.8)])
    m.mask("Ilvane Torquist sent the file.")
    assert [(e.value, e.source) for e in st.all()] == [("Ilvane Torquist", "ner")]
    r = m.mask("Then Torquist alone, and ilvane torquist, and Ilvane Torquist again.")
    assert r.text == "Then Torquist alone, and ilvane torquist, and PERSON_A again.", r.text


def test_rules_seeing_the_model_find_lift_the_containment():
    m, st = _ner_masker([("Ilvane Torquist", "person", 0.8)])
    m.mask("Ilvane Torquist sent the file.")
    assert st.all()[0].source == "ner"
    m.mask("Mr. Ilvane Torquist signed.")  # the title rule finds the same name: the entity is upgraded
    r = m.mask("Then Torquist alone.")
    assert r.text == "Then PERSON_A alone.", r.text


def test_model_handle_is_masked_in_its_slot_only():
    m, st = _ner_masker([("ilvane.t", "username", 0.9)])
    r = m.mask("user: ilvane.t\nMessage from Ilvane T about the file.")
    assert r.text.startswith("user: USERNAME_1\n") and "Ilvane T about" in r.text, r.text
    r2 = m.mask("Ilvane T wrote to ilvane.t again; login ilvane.t")
    assert "Ilvane T wrote" in r2.text and r2.text.endswith("login USERNAME_1"), r2.text


def test_watch_list_reaches_the_mask_result_and_nothing_on_it_is_masked():
    m, st = _ner_masker([("Greywell Tower", "building", 0.9)])
    r = m.mask("The lift of Greywell Tower is broken again.")
    assert r.text == "The lift of Greywell Tower is broken again." and st.all() == []
    assert r.watch == [(12, 26, "ID_CODE", "building")]
    assert Masker(MemoryStore(locale="en"), locale="en", use_ner=False).mask("Greywell Tower").watch == []


def test_candidate_signals_survive_the_copy():
    from ragbase_shield.engine.masker import _Cand, _copy

    c = _Cand(0, 5, "ORG", "ner", 1, signals=("cue", "rule"))
    assert _copy(c).signals == ("cue", "rule")


# ---------------------------------------------------------------------------------------------------------------
# synthetic mode (leak fix): the masker reserves new surfaces before it looks for known fake surfaces
# ---------------------------------------------------------------------------------------------------------------

def test_real_name_equal_to_an_earlier_fake_is_masked_and_the_fake_is_redrawn():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, replacement="synthetic")
    m.mask("Mr. Pelorin Oskvarnik signed the lease.")
    first_fake = st.synthetic(st.all()[0].code)
    first = first_fake.split()[0]
    out = m.mask(f"Mr. {first} Kestrelford joined the call.").text
    assert "Kestrelford" not in out and first not in out, out
    assert st.synthetic(st.all()[0].code) != first_fake  # the colliding fake was re-drawn


def test_a_pseudonymised_answer_masked_again_is_unchanged():
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, replacement="synthetic")
    masked = m.mask("Mr. Pelorin Oskvarnik and Ms. Maelle Quillanmere met Brightholm Logistics LLC on site.").text
    assert "Oskvarnik" not in masked and "Quillanmere" not in masked and "Brightholm" not in masked
    answer = "Summary: " + masked + " They will meet again."
    again = m.mask(answer)
    assert again.text == answer, (again.text, answer)
    assert again.spans == []


def test_synthetic_values_fail_closed_when_the_synthesizer_breaks(monkeypatch):
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False, replacement="synthetic")
    masked = m.mask("Mr. Pelorin Oskvarnik signed.").text
    fake = st.synthetic(st.all()[0].code)
    assert fake.split()[-1] in masked

    def boom(self):
        raise RuntimeError("broken")

    monkeypatch.setattr(type(m.synthesizer()), "values", boom)
    assert m._synthetic_values() == {}
    # codes mode on the same store: with no known fake surface, the answer is handled as plain text, never as a
    # real value (the fake is not in the store as a real entity)
    m2 = Masker(st, locale="en", language="en", use_ner=False)
    assert m2._synthetic_values() == {}


# ---------------------------------------------------------------------------------------------------------------
# service: a synthetic dossier registers every document in codes mode before a fake is drawn
# ---------------------------------------------------------------------------------------------------------------

def test_service_scan_registers_a_synthetic_dossier_before_the_first_draw(tmp_path, monkeypatch):
    from ragbase_shield import service as sv

    monkeypatch.setenv("RAGBASE_SHIELD_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("RAGBASE_SHIELD_REPLACEMENT", "synthetic")
    monkeypatch.setenv("RAGBASE_SHIELD_LANGUAGE", "en")
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "off")
    folder = tmp_path / "dossier"
    folder.mkdir()
    (folder / "a.txt").write_text("Mr. Pelorin Oskvarnik signed the lease with Brightholm Logistics LLC.\n", encoding="utf-8")
    (folder / "b.txt").write_text("Ms. Maelle Quillanmere and Mr. Casimir Brannoch reviewed it.\n", encoding="utf-8")
    svc = sv.Service(tmp_path / "home")
    seen = []
    orig = sv.Service._register_pass

    def spy(self, d):
        seen.append(d.code)
        return orig(self, d)

    monkeypatch.setattr(sv.Service, "_register_pass", spy)
    added = svc.add_dossier(folder)
    assert seen == [added["code"]]
    d = svc._dossier(added["code"])
    values = {e.value for e in d.all()}
    assert {"Pelorin Oskvarnik", "Maelle Quillanmere", "Casimir Brannoch"} <= values
    fakes = {d.synthetic(e.code) for e in d.all() if e.kind == "PERSON"}
    real_words = {w.lower() for v in values for w in v.split()}
    assert fakes and all(f and not ({w.lower() for w in f.split()} & real_words) for f in fakes)
    docs = svc.list_documents(added["code"])
    text = "".join(svc.read_document(added["code"], doc["id"], 0)["text"] for doc in docs)
    for w in ("Oskvarnik", "Quillanmere", "Brannoch", "Brightholm"):
        assert w not in text, (w, text)


def test_service_scan_in_codes_mode_runs_no_register_pass(tmp_path, monkeypatch):
    from ragbase_shield import service as sv

    monkeypatch.setenv("RAGBASE_SHIELD_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("RAGBASE_SHIELD_REPLACEMENT", raising=False)
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "off")
    folder = tmp_path / "dossier"
    folder.mkdir()
    (folder / "a.txt").write_text("Mr. Pelorin Oskvarnik signed the lease.\n", encoding="utf-8")
    svc = sv.Service(tmp_path / "home")
    calls = []
    monkeypatch.setattr(sv.Service, "_register_pass", lambda self, d: calls.append(d.code))
    svc.add_dossier(folder)
    assert calls == []


# ---------------------------------------------------------------------------------------------------------------
# the PrivacyBench runner adapter reads the engine's roles (no benchmark data here: invented text)
# ---------------------------------------------------------------------------------------------------------------

def test_runner_adapter_splits_a_person_by_the_engine_roles():
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "evaluation" / "public" / "privacybench" / "run_shield.py"
    if not path.exists():
        pytest.skip("runner not present")
    spec = importlib.util.spec_from_file_location("privacybench_runner_under_test", path)
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    m.mask('Mr. Bartholomew "Bart" Vredenik and Ms. Oddington, Lucasta met.')
    roles = R.name_roles(st, m)
    assert isinstance(roles, R._Roles) and roles.masker is m
    code = {e.value: e.code for e in st.all()}
    text = 'Bartholomew "Bart" Vredenik'
    parts = R.split_person(text, 100, roles, code.get("Bartholomew Vredenik"))
    assert parts == [("NAME_GIVEN", 100, 111), ("NAME_GIVEN", 113, 117), ("NAME_FAMILY", 119, 127)], parts
    # "Last, First": family then given, from the entity's roles, not from the position
    parts2 = R.split_person("Oddington, Lucasta", 0, roles, code.get("Lucasta Oddington"))
    assert parts2 == [("NAME_FAMILY", 0, 9), ("NAME_GIVEN", 11, 18)], parts2
    # without the masker: the positional rule of the baselines
    assert R.split_person("Oddington, Lucasta", 0, R.name_roles(st)) == [("NAME_GIVEN", 0, 9), ("NAME_FAMILY", 11, 18)]
