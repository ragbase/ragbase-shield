"""v0.3, owner S1+S4 (spans and organisations): PDF table cells, quoted nicknames with token roles, the legal-form
span policy, company span edges, companies named by an e-mail domain, declared acronyms, same-surface propagation.
Every name, company, domain and number here is invented."""
from __future__ import annotations

from pathlib import Path

import pytest

from ragbase_shield import documents as D
from ragbase_shield.engine import Masker, MemoryStore, entity_norm
from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import locale as lc
from ragbase_shield.engine import names as nm
from ragbase_shield.engine.detectors import IntervalSet


# --- helpers ----------------------------------------------------------------------------------------------


def spans_of(text, lang="en", **kw):
    return [(text[s.start:s.end], s.kind, s.rule) for s in nm.detect_names(text, lang=lang, **kw)]


def orgs_of(text, lang="en", **kw):
    return [(v, r) for v, k, r in spans_of(text, lang, **kw) if k == "ORG"]


def masked(text, lang="en", store=None):
    store = store or MemoryStore(locale=lang)
    r = Masker(store, locale=lang, language=lang, use_ner=False).mask(text)
    return r, store


@pytest.fixture
def wired(monkeypatch):
    """The masker's English rules go through the refinement pass, as ``nm.detect_names(text, lang, protected)``
    does (the integrator's one-line change in ``Masker._detect``); idempotent when that change is in place."""
    from ragbase_shield.engine import masker as mk

    orig = lc.detect_names_en

    def refined(text, b=None):
        return nm.refine_rule_spans(text, orig(text, b), "en")

    monkeypatch.setattr(mk.lc, "detect_names_en", refined)
    yield


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf_rows(path: Path, rows: list[list[tuple[str, int]]]) -> Path:
    """A one-page PDF whose rows hold (text, x) cells at explicit positions (Helvetica 11pt)."""
    ops = ["BT", "/F1 11 Tf"]
    y = 720
    for row in rows:
        for text, x in row:
            ops.append(f"1 0 0 1 {x} {y} Tm ({_pdf_escape(text)}) Tj")
        y -= 16
    ops.append("ET")
    stream = "\n".join(ops).encode("cp1252")
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        5: b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for i in sorted(objects):
        offsets[i] = len(out)
        out += b"%d 0 obj\n" % i + objects[i] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        out += b"%010d 00000 n \n" % offsets[i]
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref
    path.write_bytes(bytes(out))
    return path


# --- 1. PDF table cells -----------------------------------------------------------------------------------


def test_pdf_cell_gap_rule():
    a = {"text": "Rowan", "x0": 72.0, "x1": 100.0}          # 5.6 pt per character
    near = {"text": "Pellstone", "x0": 104.0, "x1": 152.0}  # one space of 4 pt: the same cell
    far = {"text": "Keldrin", "x0": 140.0, "x1": 180.0}     # 40 pt: a table column
    assert not D.pdf_cell_gap(a, near)
    assert D.pdf_cell_gap(a, far)
    assert D.pdf_word_separator(a, near) == " "
    assert D.pdf_word_separator(a, far) == D.PDF_CELL_SEPARATOR
    assert D.pdf_cell_gap(a, far, factor=10.0) is False  # a wider factor keeps them together


def test_pdf_reader_writes_cell_separators_and_the_rules_stop_at_them(tmp_path):
    pytest.importorskip("pdfplumber")
    pdf = make_pdf_rows(tmp_path / "liste.pdf", [
        [("Employee", 72), ("Company", 300)],
        [("Rowan Pellstone", 72), ("Keldrin Analytics Inc", 300)],
        [("Signed in Lyon by the parties.", 72)],
    ])
    res = D.read_text(pdf)
    assert "Rowan Pellstone | Keldrin Analytics Inc" in res.text
    assert "Signed in Lyon by the parties." in res.text  # a normal sentence keeps single spaces
    r, _ = masked(res.text)
    kinds = {(s.value, s.kind) for s in r.spans}
    assert ("Rowan Pellstone", "PERSON") in kinds
    assert any(v.startswith("Keldrin Analytics") and k == "ORG" for v, k in kinds)
    assert not any("Pellstone | Keldrin" in v for v, _ in kinds)


def test_pdf_page_text_is_the_shared_function(tmp_path):
    pdfplumber = pytest.importorskip("pdfplumber")
    pdf = make_pdf_rows(tmp_path / "t.pdf", [[("Alpha", 72), ("Beta", 400)], [("Gamma delta", 72)]])
    with pdfplumber.open(str(pdf)) as doc:
        page = doc.pages[0]
        lines = D.pdf_page_lines(page, return_chars=True)
        assert [[w["text"] for w in line] for line in lines] == [["Alpha", "Beta"], ["Gamma", "delta"]]
        assert all("chars" in w for line in lines for w in line)
        assert D.pdf_page_text(page) == "Alpha | Beta\nGamma delta"


def test_pdf_reader_still_fails_closed_and_reports_scans(tmp_path):
    pytest.importorskip("pdfplumber")
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"%PDF-1.4\nnot a pdf at all")
    with pytest.raises(D.DocumentError) as exc:
        D.read_text(bad)
    assert "pdf" in str(exc.value) and "x.pdf" not in str(exc.value)


# --- 2. quoted nicknames and token roles ---------------------------------------------------------------------


@pytest.mark.parametrize("value,firsts,nicks,surname", [
    ('Bartholomew "Bart" Quenlow', ["Bartholomew"], ["Bart"], ["Quenlow"]),
    ("Leopold (Leo) Varlock", ["Leopold"], ["Leo"], ["Varlock"]),
    ("Josephine 'Josie' Pellstone", ["Josephine"], ["Josie"], ["Pellstone"]),
    ("Josephine Pellstone", ["Josephine"], [], ["Pellstone"]),
    ('"Bart"', [], [], ["Bart"]),  # a quoted word alone is not a nickname structure
    ("Lucie d'Orvane", ["Lucie"], [], ["d'", "Orvane"]),  # an elision is not a quote
])
def test_split_person_sets_the_nickname_aside(value, firsts, nicks, surname):
    assert nm.split_person(value) == (firsts, surname)
    assert nm.person_nicknames(value) == nicks


def test_nickname_does_not_change_the_person_key():
    assert nm.person_norm('Bartholomew "Bart" Quenlow') == nm.person_norm("Bartholomew Quenlow")
    assert entity_norm("PERSON", "Leopold (Leo) Varlock") == "leopold varlock"


def test_person_token_roles_come_from_the_split_not_the_position():
    v = 'Dr. Bartholomew "Bart" Quenlow Jr'
    roles = [(v[s:e], r) for s, e, r in nm.person_token_roles(v)]
    assert roles == [("Dr.", "title"), ("Bartholomew", "given"), ("Bart", "nick"), ("Quenlow", "family"), ("Jr", "family")]
    v2 = "QUENLOW Bartholomew"
    assert [(v2[s:e], r) for s, e, r in nm.person_token_roles(v2)] == [("QUENLOW", "family"), ("Bartholomew", "given")]
    # a person known by one word: a lexicon first name is a given name, another word a family name
    assert [r for _s, _e, r in nm.person_token_roles("Josephine")] == ["given"]
    assert [r for _s, _e, r in nm.person_token_roles("Quenlow")] == ["family"]
    assert nm.split_person("Josephine") == ([], ["Josephine"])  # the engine's own split is unchanged


def test_surface_roles_read_the_entity_and_fall_back_to_the_position():
    ent = "Leopold (Leo) Varlock"
    assert [(r) for _s, _e, r in nm.surface_roles("Varlock, Leo", ent)] == ["family", "nick"]
    assert [(r) for _s, _e, r in nm.surface_roles("Varlock", ent)] == ["family"]
    assert [(r) for _s, _e, r in nm.surface_roles("Leo", ent)] == ["nick"]
    assert [(r) for _s, _e, r in nm.surface_roles('Leopold "Leo" Varlock')] == ["given", "nick", "family"]
    assert [(r) for _s, _e, r in nm.surface_roles("Leopold Varlock")] == ["given", "family"]
    # a diminutive of the usual first name counts as a nickname of that person
    assert [(r) for _s, _e, r in nm.surface_roles("Leopoldo Varlock", "Leopoldo Varlock")] == ["given", "family"]


def test_nickname_variants_link_the_mentions_to_one_person(wired):
    text = ('Alexander "Sasha" Quenlow signed the lease. Sasha Quenlow will move in on Monday. '
            'Quenlow, Sasha is listed as the tenant. Thanks, Sasha.')
    r, store = masked(text)
    values = [s.value for s in r.spans if s.kind == "PERSON"]
    assert 'Alexander "Sasha" Quenlow' in values and "Sasha Quenlow" in values and "Quenlow, Sasha" in values
    assert "Sasha" in values
    assert "Sasha" not in r.text and "Quenlow" not in r.text
    # the nickname + surname forms are variants of the declared person ("Sasha Quenlow", "Quenlow, Sasha",
    # "Sasha" alone); the rule spans of these mentions are kept, so no mention is ever lost. Today the masker
    # lets a rule candidate win over the variant and mints its own code: linking the codes of one person is the
    # kind and directory steps' job (S2, S3), which read ``person_nicknames`` and these variants.
    variants = {v.tokens for v in nm.person_variants('Alexander "Sasha" Quenlow')}
    assert ("sasha", "quenlow") in variants and ("quenlow", "sasha") in variants and ("sasha",) in variants
    assert r.text.count("PERSON_A") >= 1
    back = Masker(store, locale="en", language="en", use_ner=False).unmask(r.text)
    assert "PERSON_" not in back and back.count("Quenlow") == 3 and back.endswith("Thanks, Sasha.")


def test_rule_spans_of_nickname_mentions_are_kept_by_the_refinement():
    text = 'Alexander "Sasha" Quenlow signed. Sasha Quenlow will move in. Quenlow, Sasha is the tenant.'
    out = nm.refine_rule_spans(text, lc.detect_names_en(text), "en")
    persons = sorted(text[s.start:s.end] for s in out if s.kind == "PERSON")
    assert "Sasha Quenlow" in persons and "Quenlow, Sasha" in persons


@pytest.mark.parametrize("value,firsts,surname", [
    ("Quenlow, Chidera", ["Chidera"], ["Quenlow"]),   # neither word in the lexicon: the comma decides
    ("PELLSTONE, Rowan", ["Rowan"], ["PELLSTONE"]),
    ("Pellstone, R.", ["R."], ["Pellstone"]),
    ("de Varlock, Marc", ["Marc"], ["de", "Varlock"]),
    ("Pellstone, Jr", [], ["Pellstone", "Jr"]),        # a generational qualifier after the comma is no first name
    ("Rowan Pellstone", ["Rowan"], ["Pellstone"]),      # no comma: the usual order
])
def test_comma_order_puts_the_surname_before_the_comma(value, firsts, surname):
    assert nm.split_person(value) == (firsts, surname)


def test_comma_order_gives_one_key_and_the_family_role():
    assert nm.person_norm("Quenlow, Chidera") == nm.person_norm("Chidera Quenlow")
    v = "Quenlow, Chidera"
    assert [(v[s:e], r) for s, e, r in nm.person_token_roles(v)] == [("Quenlow", "family"), ("Chidera", "given")]
    assert [r for _s, _e, r in nm.surface_roles("Chidera", "Quenlow, Chidera")] == ["given"]


def test_bracketed_surname_is_not_a_nickname():
    assert nm.split_person("Sam (Pellstone)") == (["Sam"], ["Pellstone"])
    assert nm.person_nicknames("Sam (Pellstone)") == []
    assert [r for _s, _e, r in nm.surface_roles("Sam (Pellstone)")] == ["given", "family"]
    # a quoted last word after a full name is a nickname
    assert nm.person_nicknames('Josephine Pellstone ("Josie")') == ["Josie"]
    assert nm.split_person('Josephine Pellstone ("Josie")') == (["Josephine"], ["Pellstone"])


def test_words_after_the_first_names_stay_in_the_surname():
    # the engine's split is unchanged here: a capitalised word that is not a lexicon first name joins the
    # surname (a middle-name reading was measured worse: merged table rows make three-word surfaces)
    assert nm.split_person("Hannah Chidera Quenlow") == (["Hannah"], ["Chidera", "Quenlow"])
    assert nm.split_person("Marie Van Pellstone") == (["Marie"], ["Van", "Pellstone"])
    assert nm.split_person("Jean Pellstone VARLOCK") == (["Jean", "Pellstone"], ["VARLOCK"])  # case decides


def test_extension_stops_at_a_person_in_a_merged_table_row():
    text = "From: ops@keldrin.example\n\nKeldrin Research Kate Pellstone 2026 approved"
    found = [text[s.start:s.end] for s in nm.detect_names(text, lang="en") if s.kind == "ORG"]
    assert "Keldrin Research" in found
    assert not any("Kate" in v for v in found)


def test_extension_over_a_business_unit_noun():
    text = "From: ops@keldrin.example\n\nKeldrin Oncology presented the data. The Keldrin Footwear line ships in May."
    found = [(text[s.start:s.end]) for s in nm.detect_names(text, lang="en") if s.kind == "ORG"]
    assert "Keldrin Oncology" in found and "Keldrin Footwear" in found
    text2 = "From: ops@keldrin.example\n\nKeldrin Oncology\nPresented the data."
    assert "Keldrin Oncology" in [text2[s.start:s.end] for s in nm.detect_names(text2, lang="en")]
    assert not any("\n" in text2[s.start:s.end] for s in nm.detect_names(text2, lang="en"))


# --- 3. the legal-form span policy -----------------------------------------------------------------------------


def test_legal_form_policy_values(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", raising=False)
    assert nm.legal_form_policy() == "clear"
    monkeypatch.setenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", "cover")
    assert nm.legal_form_policy() == "cover"
    monkeypatch.setenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", "1")
    assert nm.legal_form_policy() == "mask"


def test_span_covers_the_legal_form_in_both_languages(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", raising=False)
    en = "The lease is signed by Keldrin Analytics Inc. and by Vorlane Pellstone Company on Monday."
    assert ("Keldrin Analytics", "legal_form") in orgs_of(en)
    monkeypatch.setenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", "cover")
    found = orgs_of(en)
    assert ("Keldrin Analytics Inc.", "legal_form") in found
    assert ("Vorlane Pellstone Company", "legal_form") in found
    fr = "La société ARDOVALE SAS et la SCI Les Tilleuls ont signé."
    found_fr = orgs_of(fr, "fr")
    assert ("ARDOVALE SAS", "legal_form") in found_fr
    assert ("SCI Les Tilleuls", "legal_form") in found_fr


def test_cover_policy_masks_restores_and_keeps_one_entity(monkeypatch, wired):
    monkeypatch.setenv("RAGBASE_SHIELD_LEGAL_FORM_SPAN", "cover")
    text = "Invoice from Keldrin Analytics Inc. The Keldrin Analytics team will call. Keldrin's revenue grew."
    r, store = masked(text)
    orgs = [e for e in store.all() if e.kind == "ORG"]
    # one entity; its value is the full span today, the core once the masker renders ``org_form_parts``
    assert len(orgs) == 1 and orgs[0].value in ("Keldrin Analytics Inc.", "Keldrin Analytics")
    assert [s.value for s in r.spans if s.kind == "ORG"][0] == "Keldrin Analytics Inc."
    assert "Keldrin" not in r.text
    back = Masker(store, locale="en", language="en", use_ner=False).unmask(r.text)
    # the full mention restores exactly; a partial mention restores with the stored form until the masker stores
    # the core under this policy (org_form_parts: lead + code + trail in the text, the core as the value)
    assert "COMPANY_" not in back and back.startswith("Invoice from Keldrin Analytics Inc. The Keldrin Analytics")


def test_form_helpers():
    text = "Supplier: Keldrin Analytics, Inc. and Vorlane Pty Ltd for the year."
    s = text.index("Keldrin")
    e = s + len("Keldrin Analytics")
    assert text[e:nm.legal_form_after(text, e, "en")] == ", Inc."
    s2 = text.index("Vorlane")
    assert text[s2 + len("Vorlane"):nm.legal_form_after(text, s2 + len("Vorlane"), "en")] == " Pty Ltd"
    assert nm.legal_form_after("Keldrin Analytics\nInc.", len("Keldrin Analytics"), "en") is None  # a line break
    assert nm.legal_form_after("Keldrin Analytics | Inc.", len("Keldrin Analytics"), "en") is None  # a cell
    fr = "la SCI Les Tilleuls"
    assert nm.legal_form_before(fr, fr.index("Les"), "fr") == fr.index("SCI")
    assert nm.org_form_parts("Keldrin Analytics, Inc.", "en") == ("", "Keldrin Analytics", ", Inc.")
    assert nm.org_form_parts("SCI Les Tilleuls", "fr") == ("SCI ", "Les Tilleuls", "")
    assert nm.org_form_parts("Keldrin", "en") == ("", "Keldrin", "")
    assert nm.org_form_parts("Inc.", "en") == ("", "Inc.", "")
    assert nm.org_core("Keldrin Analytics Corporation") == "Keldrin Analytics"
    assert nm.org_norm("Vorlane Incorporated") == "vorlane"


# --- 4. companies named by an e-mail domain --------------------------------------------------------------------


def test_email_domains_helper():
    text = "Write to rowan@Keldrin-Analytics.com, cc josie@keldrin-analytics.com and a friend at gmail.com."
    assert det.email_domains(text) == ["keldrin-analytics.com"]


@pytest.mark.parametrize("domain,expected", [
    ("mail.keldrin-analytics.co.uk", [(("keldrin", "analytics"), True), (("keldrinanalytics",), True), (("keldrin",), False)]),
    ("quenlowlabs.com", [(("quenlow", "labs"), True), (("quenlowlabs",), True), (("quenlow",), False)]),
    ("ardovale.io", [(("ardovale",), True)]),
    ("delta.example", [(("delta",), False)]),  # a vocabulary word: needs a cue in the text
    ("gmail.com", []),
    ("outlook.fr", []),
    ("ab.com", []),
    # a bare label, as the dossier directory keeps it
    ("keldrin-analytics", [(("keldrin", "analytics"), True), (("keldrinanalytics",), True), (("keldrin",), False)]),
    ("ardovale", [(("ardovale",), True)]),
    ("gmail", []),
    ("com", []),
])
def test_org_candidates_from_domain(domain, expected):
    assert nm.org_candidates_from_domain(domain, "en") == expected


def test_domain_names_the_company_in_the_text(wired):
    text = ("From: rowan@keldrin-analytics.com\n\nHi team, Keldrin Analytics will host the review. "
            "Please send the deck to Keldrin by Friday. The keldrin folder is on the drive.")
    found = orgs_of(text)
    assert ("Keldrin Analytics", "domain") in found
    assert not any(v == "Keldrin" for v, _ in found)  # the head word alone needs a company cue
    assert not any(v == "keldrin" for v, _ in found)  # lower case: never a domain match
    text2 = text.replace("to Keldrin by Friday", "to Keldrin's CFO by Friday") + " Keldrin again."
    found2 = [(v, r) for v, r in orgs_of(text2) if v == "Keldrin"]
    assert ("Keldrin", "domain") in found2  # "Keldrin's CFO": a cue
    assert ("Keldrin", "same_surface") in found2  # and the same word elsewhere follows
    r, store = masked(text2)
    assert "Keldrin" not in r.text
    assert len({e.code for e in store.all() if e.kind == "ORG"}) == 1


def test_dictionary_word_domain_needs_a_company_cue():
    text = ("Contact: ops@delta.example\n\nDelta shipped the parts. We joined Delta last year. "
            "The delta between the two runs is small. Delta's revenue grew.")
    found = [v for v, r in orgs_of(text) if r == "domain"]
    assert "Delta" in found  # "joined Delta", "Delta's revenue": cues
    hits = [s for s in nm.detect_names(text, lang="en") if s.rule == "domain"]
    assert len(hits) == 2  # not the bare "Delta shipped", not "the delta"


def test_domain_match_yields_to_a_person_title_and_to_person_spans():
    text = "From: info@pellstone.example\n\nMr Pellstone and Josephine Pellstone met the Pellstone board."
    found = nm.detect_names(text, lang="en")
    domain_hits = [text[s.start:s.end] for s in found if s.rule == "domain"]
    assert domain_hits == ["Pellstone"]
    only = [s for s in found if s.rule == "domain"][0]
    assert text[only.end:only.end + 6] == " board"


def test_domains_of_the_dossier_can_be_passed_in():
    text = "Ardovale sent the invoice. Please call Ardovale tomorrow."
    assert not orgs_of(text)
    assert [v for v, r in orgs_of(text, domains=["billing.ardovale.io"]) if r == "domain"] == ["Ardovale", "Ardovale"]
    # the directory keeps the label only ("ardovale"): accepted as the domain name
    assert [v for v, r in orgs_of(text, domains=["ardovale"]) if r == "domain"] == ["Ardovale", "Ardovale"]


# --- 5. declared acronyms and aliases --------------------------------------------------------------------------


def test_declared_acronym_is_the_company_here_and_later(wired):
    text = ("Keldrin Vorlane Technologies Inc (KVT) supplies the parts. KVT invoices monthly, and the KVT "
            "warehouse is in Lyon. Mr KVT is not a person here.")
    found = nm.detect_names(text, lang="en")
    acros = [(text[s.start:s.end], s.priority) for s in found if s.rule == "acronym"]
    assert acros == [("KVT", 5), ("KVT", 4), ("KVT", 4)]
    r, store = masked(text)
    assert "KVT" not in r.text.replace("Mr KVT", "")
    assert len({e.code for e in store.all() if e.kind == "ORG"}) == 1


def test_declared_quoted_alias_and_prefix_acronym():
    text = 'Ardovale Capital Partners ("Ardovale") and Quenlow Corporation (QUENLOW) are the parties.'
    found = [(text[s.start:s.end], s.rule) for s in nm.detect_names(text, lang="en") if s.kind == "ORG"]
    assert ("Ardovale", "acronym") in found
    assert ("QUENLOW", "acronym") in found


@pytest.mark.parametrize("text", [
    "Ardovale Capital Partners (LLC) hired a clerk.",      # a legal form in brackets
    "Ardovale Capital Partners (CEO) hired a clerk.",      # a common acronym
    "Ardovale Capital Partners (Section) hired a clerk.",  # not an abbreviation of the name
    "Ardovale Capital Partners (ACP Group) hired a clerk.",
])
def test_no_alias_without_an_abbreviation(text):
    assert not [s for s in nm.detect_names(text, lang="en") if s.rule == "acronym"]


def test_french_declared_alias_after_a_legal_form():
    text = "La société ARDOVALE SAS (ci-après « ARDOVALE ») a signé. ARDOVALE conteste."
    found = nm.detect_names(text, lang="fr")
    assert [(text[s.start:s.end], s.rule) for s in found if s.rule == "acronym"] == [("ARDOVALE", "acronym")] * 2
    assert any(text[s.start:s.end] == "ARDOVALE" and s.start > text.index("conteste") - 10 for s in found)
    # the French party-definition rule (no legal form before the bracket) is untouched
    text2 = "La société ARDOVALE (ci-après « ARDOVALE ») a signé."
    assert any(text2[s.start:s.end] == "ARDOVALE" and s.rule == "party_definition"
               for s in nm.detect_names(text2, lang="fr"))


# --- 6. company span edges --------------------------------------------------------------------------------------


def test_extension_over_head_words_and_its_stops():
    text = "She joined Vorlane Capital Partners in May."
    assert ("Vorlane Capital Partners", "trigger") in orgs_of(text) or ("Vorlane Capital Partners", "suffix") in orgs_of(text)
    text2 = "She joined Vorlane Commercial Banking in May and Vorlane, Capital later."
    found = orgs_of(text2)
    assert any(v == "Vorlane Commercial Banking" for v, _ in found)
    assert not any(v.startswith("Vorlane, Capital") for v, _ in found)
    text3 = "She joined Vorlane\nCapital Partners in May."
    assert not any(v.startswith("Vorlane Capital") or "\n" in v for v, _ in orgs_of(text3))
    text4 = "She joined Vorlane | Capital Partners in May."
    assert not any("|" in v for v, _ in orgs_of(text4))


def test_extension_never_enters_a_protected_term():
    text = "From: ops@vorlane.example\n\nVorlane Commercial Banking opened a branch. Vorlane Commercial Banking, again."
    found = [(text[s.start:s.end], s.rule) for s in nm.detect_names(text, lang="en") if s.kind == "ORG"]
    assert found.count(("Vorlane Commercial Banking", "domain")) == 2  # the domain span extended over the head word
    protected = IntervalSet()
    protected.add(text.index("Banking"), text.index("Banking") + 7)  # the caller protects the head word
    out = nm.refine_rule_spans(text, lc.detect_names_en(text), "en", protected=protected)
    assert [text[s.start:s.end] for s in out if s.rule == "domain"][0] == "Vorlane"


# --- 7. same-surface propagation ------------------------------------------------------------------------------


def test_same_surface_propagation_of_a_multi_word_company():
    text = ("Keldrin Vorlane Inc delivered the report. We thank Keldrin Vorlane for the report. "
            "Keldrin Vorlane\nis on line two. Mr Keldrin Vorlane is not a firm. Keldrin vorlane is not it.")
    found = nm.detect_names(text, lang="en")
    same = [(text[s.start:s.end], s.priority) for s in found if s.rule == "same_surface"]
    assert same == [("Keldrin Vorlane", 4)] * 2
    assert not any(s.rule == "same_surface" and text[s.start - 3:s.start] == "Mr " for s in found)


def test_same_surface_needs_evidence_for_dictionary_words():
    text = "General Services Inc paid. General Services again. Nothing else."
    found = [(text[s.start:s.end], s.rule) for s in nm.detect_names(text, lang="en") if s.kind == "ORG"]
    assert ("General Services", "same_surface") in found  # a legal form is strong evidence
    text2 = "They met the Northern Lights team. Northern Lights again."
    assert not [s for s in nm.detect_names(text2, lang="en") if s.rule == "same_surface"]


# --- 8. the refinement pass as a whole -------------------------------------------------------------------------


def test_refine_keeps_other_kinds_and_dedupes():
    text = "Josephine Pellstone of Keldrin Analytics Inc met Keldrin Analytics Inc again."
    raw = lc.detect_names_en(text)
    out = nm.refine_rule_spans(text, raw + raw, "en")
    persons = [s for s in out if s.kind == "PERSON"]
    assert [text[s.start:s.end] for s in persons] == ["Josephine Pellstone"]
    keys = [(s.start, s.end, s.kind) for s in out]
    assert len(keys) == len(set(keys))


def test_refine_accepts_the_masker_intervals():
    text = "Report by Keldrin Analytics Inc (KAI) for the board."
    protected = IntervalSet()
    protected.add(text.index("(KAI)") + 1, text.index("(KAI)") + 4)  # the caller protects the alias
    out = nm.refine_rule_spans(text, lc.detect_names_en(text), "en", protected=protected)
    assert not [s for s in out if s.rule == "acronym"]


def test_strong_org_rules_and_detect_names_dispatch():
    assert {"legal_form", "domain", "acronym"} <= nm.STRONG_ORG_RULES
    fr = "La société ARDOVALE SAS a signé."
    assert ("ARDOVALE", "ORG", "legal_form") in spans_of(fr, "fr")
    en = "Keldrin Analytics Inc signed."
    assert ("Keldrin Analytics", "ORG", "legal_form") in spans_of(en, "en")
    assert nm.detect_names(en) == nm.detect_names(en, lang="fr")  # the default stays the French rules


def test_refinement_adds_nothing_to_plain_french_prose():
    text = ("Le tribunal judiciaire de Lyon a condamné la société ARDOVALE SAS. Monsieur Jean Pellstone, "
            "salarié, a été entendu. L'article 1240 du code civil s'applique.")
    raw = nm._detect_names_fr(text)
    out = nm.refine_rule_spans(text, raw, "fr")
    assert {(s.start, s.end, s.kind) for s in out} == {(s.start, s.end, s.kind) for s in raw}
