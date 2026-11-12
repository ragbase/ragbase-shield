"""v0.3 steps S2+S3 (owner "resolution and directory"): the dossier directory (``engine/directory.py``), the kind
and role decisions from export-level evidence (``Masker._resolve``, ``_evidence_pass``, ``_tally``), the slot rule
of login names and identifiers, the "Last, First" order, the lower-case first names and nicknames of known people
in chat, the vault's evidence and directory tables and the service's directory build. Every name, address, handle
and company below is invented for these tests."""
import json
from pathlib import Path

import pytest

from ragbase_shield import service
from ragbase_shield import vault as V
from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import directory as D
from ragbase_shield.engine import masker as M
from ragbase_shield.engine.masker import entity_norm

# --- invented material ---------------------------------------------------------------------------------------

EML = (
    b"From: Berniece Vaskelund <berniece.vaskelund@brightwater.example>\r\n"
    b"To: \"Brennholt, Octavia\" <octavia.brennholt@brightwater.example>, Rupert Haldane <rupe.haldane@gmail.com>\r\n"
    b"Cc: Grant Pellerin <grant.pellerin@northvale.example>, ops@northvale.example\r\n"
    b"Subject: Deck\r\n\r\n"
    b"Hi Octavia,\r\n\r\nLoop in Constantine \"Kit\" Varlamov and Marguerite Delacour (goes by Daisy).\r\n\r\n"
    b"Thanks,\r\nBerniece Vaskelund\r\nHead of Operations | Brightwater\r\n"
)
USERS = [
    {"name": "octavia.brennholt", "real_name": "Octavia Brennholt",
     "profile": {"display_name": "Tavi", "first_name": "Octavia", "last_name": "Brennholt",
                 "email": "octavia.brennholt@brightwater.example"}},
    {"name": "wilhelmina.os", "real_name": "Wilhelmina Okoro-Sand",
     "profile": {"display_name": "Billie", "email": "wilhelmina.os@brightwater.example"}},
    {"name": "deploy-bot", "real_name": "Deploy Bot", "is_bot": True, "profile": {}},
]
DOCX_CORE = (b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
             b'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Sterling Abernathy</dc:creator>'
             b'<cp:lastModifiedBy>Octavia Brennholt</cp:lastModifiedBy></cp:coreProperties>')


def docx_bytes(core: bytes = DOCX_CORE) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("docProps/core.xml", core)
        zf.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


@pytest.fixture(scope="module")
def directory() -> D.Directory:
    return D.build([("eml", EML), ("slack_users", USERS), ("docx", docx_bytes()),
                    ("text", "Best regards,\nGrant Pellerin\nAnalyst\n")], lang="en")


def person(d: D.Directory, value: str) -> D.Person:
    for p in d.persons:
        if p.value == value:
            return p
    raise AssertionError([p.value for p in d.persons])


def masked(text: str, directory=None, store=None, **kw):
    store = store or MemoryStore(locale="en")
    m = Masker(store, locale="en", language="en", use_ner=False, directory=directory, **kw)
    return m.mask(text), m, store


# --- 1. building the directory ----------------------------------------------------------------------------------


def test_build_reads_headers_slack_users_authors_and_signatures(directory):
    values = [p.value for p in directory.persons]
    assert "Berniece Vaskelund" in values and "Octavia Brennholt" in values and "Rupert Haldane" in values
    assert "Grant Pellerin" in values and "Sterling Abernathy" in values and "Wilhelmina Okoro-Sand" in values
    assert "Deploy Bot" not in values and not any("ops" == p.value.lower() for p in directory.persons)
    bernie = person(directory, "Berniece Vaskelund")
    assert bernie.given == ("berniece",) and bernie.family == ("vaskelund",)
    assert "header" in bernie.sources and "signature" in bernie.sources
    assert bernie.emails == ("berniece.vaskelund@brightwater.example",) and "berniece.vaskelund" in bernie.handles
    octavia = person(directory, "Octavia Brennholt")  # "Brennholt, Octavia" in the header, merged by e-mail
    assert octavia.given == ("octavia",) and octavia.family == ("brennholt",) and "tavi" in octavia.nicknames
    assert set(octavia.sources) >= {"header", "slack", "docx"}
    billie = person(directory, "Wilhelmina Okoro-Sand")
    assert billie.family == ("okoro", "sand") and "billie" in billie.nicknames
    assert directory.domains == {"brightwater": 4, "northvale": 2}  # gmail is a public host


def test_local_part_and_display_name_give_nicknames(directory):
    rupert = person(directory, "Rupert Haldane")
    assert "rupe" in rupert.nicknames and "rupe.haldane" in rupert.handles
    assert directory.lookup("rupe") == [D.Match(rupert, "nick")]


def test_declared_nicknames_in_the_text(directory):
    kit = person(directory, "Constantine Varlamov")  # Constantine "Kit" Varlamov: the quotes declare it
    assert "kit" in kit.nicknames and "declared" in kit.sources
    daisy = person(directory, "Marguerite Delacour")  # (goes by Daisy)
    assert "daisy" in daisy.nicknames
    d = D.build([("text", "Ping Marguerite Delacour (Daisy) about it. Agreed (Final) Pellerin is wrong.")], lang="en")
    assert [p.value for p in d.persons] == ["Marguerite Delacour"]  # the verb is not part of the name; no vocab nick
    # an affiliation or a role in brackets is not a nickname, and neither is a bare third capitalised word; the
    # "aka" inside a surname is not a declaring keyword ("Haldane" is not, "Nakagawa" holds one)
    d = D.build([("text", "Rupert Nakagawa (Brightwater controller) signed with Rupert Nakagawa (Brightwater) and "
                          "Rupert Nakagawa Brightwater. Supplier: Rupert Nakagawa, Brightwater Logistics.")], lang="en")
    assert not [n for p in d.persons for n in p.nicknames], d.persons
    d = D.build([("text", "Rupert Nakagawa (Rupe) wrote; Rupert Nakagawa, who goes by Rupe, nicknamed Rupe by all.")], lang="en")
    assert [(p.value, p.nicknames) for p in d.persons] == [("Rupert Nakagawa", ("rupe",))]


def test_lookup_forms(directory):
    octavia = person(directory, "Octavia Brennholt")
    for surface in ("Octavia Brennholt", "Brennholt Octavia", "Brennholt, Octavia", "O. Brennholt", "Brennholt, Tavi"):
        assert [m.person for m in directory.lookup(surface)] == [octavia], surface
    assert directory.lookup("tavi") == [D.Match(octavia, "nick")]
    assert directory.lookup("Brennholt") == [D.Match(octavia, "family")]
    assert directory.lookup("@octavia.brennholt") == [D.Match(octavia, "handle")]
    assert directory.lookup("octavia.brennholt@brightwater.example") == [D.Match(octavia, "email")]
    billie = person(directory, "Wilhelmina Okoro-Sand")
    assert directory.lookup("Okoro-Sand") == [D.Match(billie, "family")]
    assert directory.lookup("Wilhelmina Okoro-Sand")[0].person == billie
    assert directory.lookup("Nobody") == [] and directory.lookup("") == []
    assert directory.roles("brennholt") == {"family"} and directory.roles("octavia") == {"given"}
    assert directory.is_org_label("Northvale") and directory.is_org_label("BRIGHTWATER") and not directory.is_org_label("gmail")


def test_person_roles_from_the_directory(directory):
    assert directory.person_roles("Brennholt, Octavia") == [("Brennholt", "family"), ("Octavia", "given")]
    assert directory.person_roles("Brennholt, Tavi") == [("Brennholt", "family"), ("Tavi", "nick")]
    assert directory.person_roles("Dr. Octavia Brennholt") == [("Dr", "title"), ("Octavia", "given"), ("Brennholt", "family")]
    assert directory.person_roles("Wilhelmina Okoro-Sand") == [("Wilhelmina", "given"), ("Okoro-Sand", "family")]
    assert directory.person_roles("O. Brennholt") == [("O", "initial"), ("Brennholt", "family")]
    # an unknown name: positional, "Last, First" by the comma
    assert directory.person_roles("Unknown Person") == [("Unknown", "given"), ("Person", "family")]
    assert directory.person_roles("Person, Unknown") == [("Person", "family"), ("Unknown", "given")]


def test_split_name_orders_and_local_part():
    assert D.split_name("Octavia Brennholt") == (["octavia"], ["brennholt"])
    assert D.split_name("Brennholt, Octavia Maud") == (["octavia", "maud"], ["brennholt"])
    assert D.split_name("BRENNHOLT Octavia") == (["octavia"], ["brennholt"])
    assert D.split_name("Okoro-Sand Wilhelmina") == (["wilhelmina"], ["okoro", "sand"])
    assert D.split_name("Mr. Rupert de la Haldane") == (["rupert"], ["de", "la", "haldane"])
    assert D.split_name("Octavia Maud Brennholt", local_part="octavia.brennholt") == (["octavia", "maud"], ["brennholt"])
    assert D.split_name("") == ([], []) and D.split_name("octavia.brennholt") == ([], [])


def test_domain_label():
    assert D.domain_label("jane@mail.northvale.example") == "northvale"
    assert D.domain_label("northvale.co.uk") == "northvale"
    assert D.domain_label("someone@gmail.com") == "" and D.domain_label("x@outlook.fr") == ""
    assert D.domain_label("nodomain") == "" and D.domain_label("") == ""


def test_dict_round_trip_and_bad_input(directory):
    data = json.loads(json.dumps(directory.to_dict()))
    back = D.Directory.from_dict(data)
    assert back == directory and len(back) == len(directory)
    assert D.Directory.from_dict(None) == D.Directory() and not D.Directory.from_dict({"persons": "x"})
    weird = D.Directory.from_dict({"persons": [{"value": ""}, {"nope": 1}, {"value": "Ok Name", "given": ["ok"], "family": ["name"]}],
                                   "domains": {"a": "x", "b": 2}})
    assert [p.value for p in weird.persons] == ["Ok Name"] and weird.domains == {"b": 2}


def test_build_skips_unreadable_items(tmp_path):
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"not a zip")
    d = D.build([bad, tmp_path / "missing.eml", ("slack_users", b"{not json"), ("eml", b"garbage"),
                 ("text", "Thanks,\nOctavia Brennholt\n")], lang="en")
    assert [p.value for p in d.persons] == ["Octavia Brennholt"]


def test_seed_registers_full_names_once(directory):
    store = MemoryStore(locale="en")
    added = directory.seed(store)
    codes = {e.code for e in added}
    assert len(codes) == len([p for p in directory.persons if p.full])
    assert all(e.kind == "PERSON" for e in store.all())
    again = directory.seed(store)
    assert {e.code for e in again} == codes and len(store.all()) == len(codes)


# --- 2. the masker with a directory ------------------------------------------------------------------------------


def test_lower_case_first_names_and_nicknames_in_chat(directory):
    chat = ("hey bernie, can you ping tavi about the deck?\nbillie said rupe is out, ask grant too\n"
            "ok thanks bernie\n")
    r, m, store = masked(chat, directory)
    code = {e.value: e.code for e in store.all()}
    bernie, tavi = code["Berniece Vaskelund"], code["Octavia Brennholt"]
    billie, rupe, grant = code["Wilhelmina Okoro-Sand"], code["Rupert Haldane"], code["Grant Pellerin"]
    assert r.text == (f"hey {bernie}, can you ping {tavi} about the deck?\n{billie} said {rupe} is out, ask {grant} too\n"
                      f"ok thanks {bernie}\n"), r.text
    # a common-word first name needs a cue: "grant" as a verb stays in clear
    r2, _m, _s = masked("we will grant the extension tomorrow\nthen ask grant for the file\n", directory)
    assert r2.text == f"we will grant the extension tomorrow\nthen ask {grant} for the file\n", r2.text
    # formal prose: a lower-case first name alone is not the person
    r3, _m, s3 = masked("The bernie of the matter is the deck. Bernie signed it.", directory)
    bernie3 = {e.value: e.code for e in s3.all()}["Berniece Vaskelund"]
    assert r3.text == f"The bernie of the matter is the deck. {bernie3} signed it.", r3.text


def test_nickname_with_family_name_and_sentence_ends(directory):
    r, _m, store = masked("Tavi Brennholt signed. Brennholt, Tavi is the tenant. Thanks, Tavi. Brennholt will come.", directory)
    tavi = {e.value: e.code for e in store.all()}["Octavia Brennholt"]
    assert r.text == f"{tavi} signed. {tavi} is the tenant. Thanks, {tavi}. {tavi} will come.", r.text
    r2, _m, s2 = masked("I asked Bernie. Vaskelund answered.", directory)
    bernie = {e.value: e.code for e in s2.all()}["Berniece Vaskelund"]
    assert r2.text == f"I asked {bernie}. {bernie} answered.", r2.text  # two mentions, never one span over the dot


def test_last_first_order_keys_to_one_entity_and_gives_roles():
    assert entity_norm("PERSON", "Vaskelund, Berniece") == entity_norm("PERSON", "Berniece Vaskelund")
    assert M._comma_order("M., Jean") == "M., Jean" and M._comma_order("Haldane, Jr.") == "Haldane, Jr."
    r, m, store = masked("Attendees: Vaskelund, Berniece; Pellerin, Grant.\nBerniece Vaskelund opened. Grant Pellerin closed.")
    assert len([e for e in store.all() if e.kind == "PERSON"]) == 2
    assert r.text == "Attendees: PERSON_A; PERSON_B.\nPERSON_A opened. PERSON_B closed."
    assert m.person_roles("Vaskelund, Berniece") == [("Vaskelund", "family"), ("Berniece", "given")]
    assert m.person_roles("Berniece Vaskelund") == [("Berniece", "given"), ("Vaskelund", "family")]
    assert m.person_roles("Vaskelund") == [("Vaskelund", "family")]
    assert m.person_roles("Berniece") == [("Berniece", "given")]
    assert m.person_roles("Somebody") == [("Somebody", "given")]  # unknown: the default of the adapters
    roles = m.name_roles()
    assert roles["vaskelund"] == {"family"} and roles["berniece"] == {"given"} and roles["grant"] == {"given"}


def test_last_first_guard_drops_an_interjection(directory):
    r, _m, store = masked("Perfect, Bernie. Agreed, Tavi. Vaskelund, Bernie is in.", directory)
    code = {e.value: e.code for e in store.all()}
    bernie, tavi = code["Berniece Vaskelund"], code["Octavia Brennholt"]
    assert r.text == f"Perfect, {bernie}. Agreed, {tavi}. {bernie} is in.", r.text
    assert not [e.value for e in store.all() if "Perfect" in e.value or "Agreed" in e.value]


def test_username_and_id_entities_match_only_in_their_slot():
    store = MemoryStore(locale="en")
    store.add("USERNAME", "octavia", "octavia")
    store.add("EMPLOYEE_ID", "BW-4471", "BW4471")
    text = ("@octavia can you look? Octavia is on it, octavia too.\nUsername: octavia\n"
            "Badge BW-4471 was issued; the badge bw-4471 is active.")
    r, m, _s = masked(text, store=store)
    assert r.text == ("@USERNAME_1 can you look? PERSON_A is on it, octavia too.\nUsername: USERNAME_1\n"
                      "Badge EMPLOYEEID_1 was issued; the badge EMPLOYEEID_1 is active."), r.text
    # the canary (lenient) still finds the registered login name anywhere
    assert [s.value for s in m.scan("hello octavia")] == ["octavia"]
    store2 = MemoryStore(locale="en")
    store2.add("USERNAME", "tavi_b", "tavi_b")
    assert [(s.value, s.kind) for s in Masker(store2, locale="en", language="en", use_ner=False).scan("ask tavi_b")] \
        == [("tavi_b", "USERNAME")]
    assert M._in_slot("id: x9", 4, 6, "USERNAME") and M._in_slot("user x9", 5, 7, "USERNAME")  # a digit inside
    assert not M._in_slot("hello world", 6, 11, "USERNAME")


def test_person_rule_with_a_cue_beats_a_company_head_word_and_a_company_rule_beats_a_surname():
    store = MemoryStore(locale="en")
    store.add("ORG", "Sterling Freight", entity_norm("ORG", "Sterling Freight"))
    r, _m, s = masked("Hi Sterling,\n\nSterling Freight ships Monday. Regards,\nSterling", store=store)
    assert r.text == "Hi PERSON_A,\n\nCOMPANY_A ships Monday. Regards,\nPERSON_A", r.text
    store2 = MemoryStore(locale="en")
    store2.add("PERSON", "Haldane", "haldane")
    r2, _m, _s = masked("Haldane Logistics, Inc. and Mr. Haldane met at Haldane Logistics.", store=store2)
    assert r2.text == "COMPANY_A, Inc. and Mr. PERSON_A met at COMPANY_A.", r2.text


def test_bare_first_name_with_company_evidence_is_the_company():
    store = MemoryStore(locale="en")
    m = Masker(store, locale="en", language="en", use_ner=False)
    m.mask("Sterling Freight, Inc. signed. Sterling Abernathy will call Sterling Freight tomorrow.")
    r = m.mask("Sterling confirmed the slots. Hi Sterling, send the Sterling contract. Sterling's team is ready.")
    codes = {e.value: e.code for e in store.all()}
    org, per = codes["Sterling Freight"], codes["Sterling Abernathy"]
    assert r.text == f"{org} confirmed the slots. Hi {per}, send the {org} contract. {per}'s team is ready.", r.text
    assert m._kind_scores("sterling")[1] >= 1 and m._kind_scores("abernathy")[0] >= 1


def test_joined_mentions_give_no_roles_and_a_known_full_name_is_cut_out_of_a_longer_span(directory):
    # a PDF row read as one line: the full name, then the "goes by" cell, then the next column
    r, m, store = masked("Berniece Vaskelund Bernie Supply Chain Brightwater\nBrightwater, Octavia Brennholt Tavi", directory)
    code = {e.value: e.code for e in store.all()}
    bernie, tavi = code["Berniece Vaskelund"], code["Octavia Brennholt"]
    # v0.3 integration: the e-mail domain labels of the directory feed the company rules (S4), so the distinctive
    # label "Brightwater" of the correspondents' domain is the company of the dossier and is masked
    bw = code["Brightwater"]
    assert r.text == f"{bernie} {bernie} Supply Chain {bw}\n{bw}, {tavi} {tavi}", r.text
    assert not [e.value for e in store.all() if e.value.startswith("Berniece Vaskelund ")]
    # the same nickname after another capitalised word is part of that phrase, as before ("Northvale" itself is a
    # domain label of the directory: a company of the dossier since the v0.3 integration)
    r2, _m, s2 = masked("Northvale Tavi reviewed it.", directory)
    nv = {e.value: e.code for e in s2.all()}["Northvale"]
    assert r2.text == f"{nv} Tavi reviewed it.", r2.text
    # a rule span over a first name and a nickname is masked as one span but gives no token roles
    store2 = MemoryStore(locale="en")
    store2.add("PERSON", "Berniece Bernie", entity_norm("PERSON", "Berniece Bernie"))
    m2 = Masker(store2, locale="en", language="en", use_ner=False, directory=directory)
    assert m2.person_roles("Bernie") == [("Bernie", "nick")] and m2.person_roles("Berniece") == [("Berniece", "given")]
    assert "family" not in m2.name_roles().get("bernie", set())
    assert not m2._plausible_full_name("Berniece Bernie") and m2._plausible_full_name("Vaskelund, Berniece")


def test_first_name_before_a_company_head_word_is_the_first_name_alone(directory):
    # a PDF row: the "name" cell holds the first name, the next cell the company (Northvale is a domain label)
    r, _m, store = masked("Controller\nOctavia Northvale\nterms and conditions\nNorthvale Logistics, Inc. supplies.", directory)
    import re as _re
    assert _re.match(r"Controller\nPERSON_[A-Z]+ COMPANY_A\nterms and conditions\nCOMPANY_A, Inc\. supplies\.", r.text), r.text
    assert not [e.value for e in store.all() if e.kind == "PERSON" and "Northvale" in e.value]
    assert [e.value for e in store.all() if e.kind == "ORG"] == ["Northvale Logistics"]


def test_possessive_on_a_company_head_word_stays_the_company():
    store = MemoryStore(locale="en")
    m = Masker(store, locale="en", language="en", use_ner=False)
    m.mask("Northvale Logistics, Inc. signed the deal with Northvale Logistics.")
    r = m.mask("Northvale's ops team is ready; call Northvale's office.")
    org = {e.value: e.code for e in store.all()}["Northvale Logistics"]
    assert r.text == f"{org}'s ops team is ready; call {org}'s office.", r.text
    assert [e.kind for e in store.all()] == ["ORG"]


def test_weak_company_rule_over_known_people_is_a_list_of_people(directory):
    r, _m, store = masked("Berniece & Octavia, please review the draft at Northvale.", directory)
    code = {e.value: e.code for e in store.all()}
    assert r.text.startswith(f"{code['Berniece Vaskelund']} & {code['Octavia Brennholt']}, please review")
    assert not [e for e in store.all() if e.kind == "ORG" and "berniece" in e.norm]


def test_evidence_lives_in_the_store_when_it_keeps_it(tmp_path):
    folder = tmp_path / "Dossier Brennholt"
    folder.mkdir()
    reg = V.Registry(tmp_path / "home")
    try:
        d = reg.add_dossier(folder, "Brennholt matter")
        rev = d.revision
        d.add_evidence({"octavia": {"given": 2, "zzz": 5}, "": {"org": 1}, "x" * 300: {"org": 1}})
        assert d.evidence() == {"octavia": {"given": 2}} and d.revision == rev
        d.add_evidence({"octavia": {"given": 1, "person_cue": 1}})
        assert d.evidence() == {"octavia": {"given": 3, "person_cue": 1}}
        m = Masker(d, locale="fr", language="en", use_ner=False)
        m.mask("Octavia Brennholt met Grant Pellerin at Sterling Freight, Inc. yesterday.")
        ev = d.evidence()
        assert ev["brennholt"]["family"] >= 1 and ev["sterling freight"]["org"] >= 1 and ev["pellerin"]["family"] >= 1
        data = D.build([("text", "Thanks,\nOctavia Brennholt\n")], lang="en").to_dict()
        d.set_directory(data)
        assert d.directory() is d.directory() and d.directory()["persons"][0]["value"] == "Octavia Brennholt"
        m2 = Masker(d, locale="fr", language="en", use_ner=False)
        assert m2.directory is not None and m2.directory.persons[0].value == "Octavia Brennholt"
        r = m2.mask("ping octavia please\nthanks\n")
        assert "PERSONNE_" in r.text and "octavia" not in r.text
        assert d.entity_source(d.get_by_norm("PERSON", entity_norm("PERSON", "Octavia Brennholt")).code) == "detected"
        d.set_directory(None)
        assert d.directory() is None
        with pytest.raises(ValueError):
            d.set_directory("nope")
    finally:
        reg.close()


def test_export_carries_evidence_and_directory(tmp_path):
    folder = tmp_path / "Dossier X"
    folder.mkdir()
    reg = V.Registry(tmp_path / "home")
    try:
        d = reg.add_dossier(folder, "X matter")
        d.add_evidence({"brennholt": {"family": 2}})
        d.set_directory(D.build([("text", "Regards,\nOctavia Brennholt\n")], lang="en").to_dict())
        d.add("PERSON", "Octavia Brennholt", entity_norm("PERSON", "Octavia Brennholt"), source="directory")
        assert d.entity_source("PERSONNE_A") == "directory"
        out = d.export(tmp_path / "x.shield", "une phrase secrète assez longue")
        raw = out.read_bytes()
        assert b"Brennholt" not in raw and b"brennholt" not in raw
        reg2 = V.Registry(tmp_path / "home2")
        try:
            copy = tmp_path / "copy"
            copy.mkdir()
            imp = reg2.import_(out, "une phrase secrète assez longue", folder=copy)
            assert imp.evidence() == {"brennholt": {"family": 2}}
            assert imp.directory()["persons"][0]["value"] == "Octavia Brennholt"
            assert imp.entity_source("PERSONNE_A") == "directory"
        finally:
            reg2.close()
    finally:
        reg.close()


def test_import_rejects_bad_evidence_and_directory():
    base = {"format": V._EXPORT_FORMAT, "version": 2, "code": "DOSSIER_1", "title": "t", "folder": "", "locale": "fr",
            "entities": [], "counters": {}, "clear": [], "documents": []}
    V._validate_payload(dict(base, evidence={"a": {"org": 1}}, directory={"persons": [{"value": "A B"}]}))
    for bad in ({"evidence": {"a": {"zzz": 1}}}, {"evidence": {"a": {"org": -1}}}, {"evidence": ["x"]},
                {"directory": "x"}, {"directory": {"persons": [{"value": ""}]}}, {"directory": {"persons": "x"}}):
        with pytest.raises(ValueError):
            V._validate_payload(dict(base, **bad))


# --- 3. the service --------------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_service():
    service.reset()
    yield
    service.reset()


def test_service_builds_and_seeds_the_directory_on_add_and_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_LOCALE", "en")
    folder = tmp_path / "Brightwater matter"
    (folder / "slack").mkdir(parents=True)
    (folder / "mail.eml").write_bytes(EML)
    (folder / "slack" / "users.json").write_text(json.dumps(USERS), encoding="utf-8")
    (folder / "chat.txt").write_text("hey bernie, tavi said rupe is out today\nok thanks bernie\n", encoding="utf-8")
    info = service.add_dossier(folder, "Brightwater matter")
    assert info["directory"] >= 5 and info["documents"] == 2
    ents = service.entities(info["code"])
    by_value = {e["value"]: e for e in ents}
    assert by_value["Berniece Vaskelund"]["source"] == "directory"
    assert by_value["Octavia Brennholt"]["source"] == "directory"
    assert "Deploy Bot" not in by_value
    chat = [x for x in service.list_documents(info["code"]) if x["kind"] == "txt"][0]
    text = service.read_document(info["code"], chat["id"])["text"]
    assert "bernie" not in text and "tavi" not in text and "rupe" not in text, text
    assert text.count("PERSON_") == 4
    out = service.mask_text("ping tavi and bernie", info["code"])
    assert out["masked"] == f"ping {by_value['Octavia Brennholt']['code']} and {by_value['Berniece Vaskelund']['code']}"
    # a new e-mail: the next scan adds its correspondent to the directory and the store
    (folder / "mail2.eml").write_bytes(b"From: Lucasta Fennimore <lucasta.fennimore@brightwater.example>\r\n"
                                       b"To: x@brightwater.example\r\nSubject: hi\r\n\r\nping me\r\n")
    service.scan_dossier(info["code"])
    assert "Lucasta Fennimore" in {e["value"] for e in service.entities(info["code"])}
    summary = json.dumps(service.list_dossiers())
    assert "Vaskelund" not in summary and "Brennholt" not in summary


def test_service_directory_failure_never_blocks_the_scan(tmp_path, monkeypatch):
    folder = tmp_path / "Dossier Z"
    folder.mkdir()
    (folder / "note.txt").write_text("Madame Octavia Brennholt est convoquée.\n", encoding="utf-8")

    def boom(*_a, **_k):
        raise RuntimeError("no directory today")

    monkeypatch.setattr(D, "build", boom)
    info = service.add_dossier(folder, "Z")
    assert info["directory"] == 0 and info["documents"] == 1
    assert any(e["value"] == "Octavia Brennholt" for e in service.entities(info["code"]))


# --- 4. French behaviour stays ---------------------------------------------------------------------------------


def test_french_companies_and_people_keep_their_kinds():
    store = MemoryStore()
    m = Masker(store, use_ner=False)
    text = ("La société BRENNHOLT INDUSTRIES SAS, représentée par Monsieur Rupert HALDANE, et la SAS VARLAMOV PEINTURE, "
            "domiciliée à Lyon. M. HALDANE signe. Le salarié VARLAMOV conteste. La SAS VARLAMOV PEINTURE, domiciliée à Lyon, paie.")
    r = m.mask(text)
    kinds = {s.value: s.kind for s in r.spans}
    assert kinds["BRENNHOLT INDUSTRIES"] == "ORG" and kinds["VARLAMOV PEINTURE"] == "ORG"
    assert kinds["Rupert HALDANE"] == "PERSON" and kinds["HALDANE"] == "PERSON" and kinds["VARLAMOV"] == "PERSON"
    r2 = m.mask(text)
    assert r2.text == r.text  # the evidence of the first pass changes no kind on the second
