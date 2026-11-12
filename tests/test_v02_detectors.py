"""v0.2 DETECTORS builder (docs/V02_DESIGN.md section 4.4 and the DETECTORS rows of sections 2.2 to 2.5).

Every name, number, handle and company below is invented for these tests. Checksummed identifiers are built in code
(a valid number, then one digit changed). No string of a benchmark or of the Max corpus appears here.
"""
import re

import pytest

from ragbase_shield import config
from ragbase_shield.engine import (
    CODE_RE,
    KINDS,
    PREFIXES,
    UNMASK_RE,
    Entity,
    Masker,
    MemoryStore,
    detect_structured,
    entity_norm,
    escape_codes,
    find_suspects,
    make_code,
)
from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import names as nm
from ragbase_shield.engine.detectors import (
    PUBLIC_HANDLES,
    aba_routing_valid,
    detect_candidates,
    luhn_check_digit,
    shape_template,
    structured_norm,
)
from ragbase_shield.engine.types import SHAPE_KINDS


# ----------------------------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------------------------


def masker(store=None):
    return Masker(store if store is not None else MemoryStore(), use_ner=False)


def mask(text, store=None):
    return masker(store).mask(text)


def spans(text, store=None):
    return [(s.kind, s.value) for s in mask(text, store).spans]


def valid_kinds(text, **kw):
    """(kind, value, detector) of every valid candidate of the structured detectors."""
    return [(c.kind, text[c.start:c.end], c.detector) for c in detect_candidates(text, **kw) if c.valid]


def selected(text):
    return [(s.kind, s.value) for s in detect_structured(text)]


def aba_number(prefix8):
    for d in "0123456789":
        if aba_routing_valid(prefix8 + d):
            return prefix8 + d
    raise AssertionError("no ABA digit")


def siret_pair():
    """(valid SIRET, the same with a wrong last digit)."""
    siren = "73282932" + luhn_check_digit("73282932")
    siret = siren + "0001" + luhn_check_digit(siren + "0001")
    bad = siret[:-1] + str((int(siret[-1]) + 3) % 10)
    return siret, bad


CHAT = (
    "priya kervadec: morning all\n"
    "marc vredenik: morning\n"
    "priya kervadec: can someone ping priya about the deck?\n"
    "marc vredenik: sure, priya's draft is in the folder\n"
)


# ----------------------------------------------------------------------------------------------------------------
# kinds, prefixes, codes
# ----------------------------------------------------------------------------------------------------------------


def test_new_kinds_prefixes_and_codes():
    for kind, fr, en in (("USERNAME", "PSEUDO", "USERNAME"), ("EMPLOYEE_ID", "MATRICULE", "EMPLOYEEID"),
                         ("ACCOUNT_NUMBER", "COMPTE", "ACCOUNT")):
        assert kind in KINDS
        assert PREFIXES[kind] == (fr, en, False)
        assert make_code(kind, 0) == f"{fr}_1" and make_code(kind, 41, "en") == f"{en}_42"
        for code in (f"{fr}_7", f"{en}_123456"):
            assert CODE_RE.fullmatch(code) and UNMASK_RE.fullmatch(code)
            assert escape_codes(f"see {code} here") == f"see {code.replace('_', '-')} here"
    assert SHAPE_KINDS == ("EMPLOYEE_ID", "ACCOUNT_NUMBER")
    assert Entity("PERSON", "Lou Vauquelin", "lou vauquelin", "PERSONNE_A").source == "detected"


def test_new_codes_do_not_look_like_dlp_patterns_and_are_not_detected():
    dlp = [re.compile(r"\d{5,}"), re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
           re.compile(r"\b\d{3} ?\d{3} ?\d{3}\b")]
    codes = [make_code(k, i, loc) for k in ("USERNAME", "EMPLOYEE_ID", "ACCOUNT_NUMBER")
             for loc in ("fr", "en") for i in range(0, 9999, 7)]
    for code in codes:
        assert not any(p.search(code) for p in dlp), code
    assert detect_structured(" ".join(codes)) == []
    m = masker()
    assert m.scan("PSEUDO_1 MATRICULE_2 COMPTE_3 USERNAME_4 EMPLOYEEID_5 ACCOUNT_6") == []
    assert m.mask("Voir MATRICULE_12 et COMPTE_3.").text == "Voir MATRICULE-12 et COMPTE-3."


def test_memory_store_shape_memory():
    s = MemoryStore()
    rev = s.revision
    s.add_shape("EMPLOYEE_ID", "EMP-ddddd")
    s.add_shape("EMPLOYEE_ID", "EMP-ddddd")  # known: ignored
    s.add_shape("PERSON", "EMP-ddddd")  # not a shape kind
    s.add_shape("ACCOUNT_NUMBER", "")  # empty
    s.add_shape("ACCOUNT_NUMBER", "ACC")  # no digit marker
    s.add_shape("ACCOUNT_NUMBER", "AC-dddd-dd")
    assert s.shapes() == [("EMPLOYEE_ID", "EMP-ddddd"), ("ACCOUNT_NUMBER", "AC-dddd-dd")]
    assert s.revision == rev + 2


def test_cli_and_norms_know_the_kinds():
    from ragbase_shield.cli import _KIND_LABELS

    assert {_KIND_LABELS[k] for k in ("USERNAME", "EMPLOYEE_ID", "ACCOUNT_NUMBER")} == {"Pseudos", "Matricules",
                                                                                         "Comptes"}
    assert structured_norm("USERNAME", "@Priya.K") == "priya.k"
    assert structured_norm("EMPLOYEE_ID", "emp-00 123") == "EMP00123"
    assert structured_norm("ACCOUNT_NUMBER", "4471.9920/11") == "4471992011"
    assert entity_norm("EMPLOYEE_ID", "EMP-00123") == entity_norm("EMPLOYEE_ID", "emp 00123")


# ----------------------------------------------------------------------------------------------------------------
# mentions and handles
# ----------------------------------------------------------------------------------------------------------------


def test_slack_mention_masks_the_id_only_and_restores():
    text = "ping <@U024BE7LH> and <@W012A3CDE|lou> please"
    r = mask(text)
    assert r.text == "ping <@PSEUDO_1> and <@PSEUDO_2|lou> please"
    assert [(s.kind, s.value) for s in r.spans] == [("USERNAME", "U024BE7LH"), ("USERNAME", "W012A3CDE")]
    assert masker(MemoryStore()).unmask("x") == "x"


def test_mention_round_trip_one_code_per_id():
    s = MemoryStore()
    m = masker(s)
    r = m.mask("<@U024BE7LH> wrote. Later <@U024BE7LH> again.")
    assert r.text.count("PSEUDO_1") == 2
    assert m.unmask(r.text) == "<@U024BE7LH> wrote. Later <@U024BE7LH> again."


@pytest.mark.parametrize("text,value", [
    ("cc @priya.k on this", "priya.k"),
    ("ask @m_vredenik42 about it.", "m_vredenik42"),
    ("thanks @lou-v.", "lou-v"),
    ("(@brizac2024)", "brizac2024"),
])
def test_handles_are_usernames(text, value):
    assert ("USERNAME", value) in spans(text)


@pytest.mark.parametrize("text", [
    "cc @channel and @here and @everyone and @all",
    "write to lou.vauquelin@exemple-mail.fr today",  # an e-mail is not a handle
    "the domain @acme-exemple.com is parked",  # a domain is not a handle
    "section 4 @ page 12",
    "@2024 is not a handle",
])
def test_public_mentions_emails_domains_are_not_handles(text):
    assert not [k for k, _ in spans(text) if k == "USERNAME"], text


def test_public_handle_list_is_lower_case():
    assert "channel" in PUBLIC_HANDLES and all(h == h.lower() for h in PUBLIC_HANDLES)


def test_handle_of_a_registered_person_resolves_to_the_regex_username():
    s = MemoryStore()
    mask("Priya Kervadec est la responsable.", s)
    r = mask("cc @kervadec et @priya", s)
    assert r.text == "cc @PSEUDO_1 et @PSEUDO_2"


# ----------------------------------------------------------------------------------------------------------------
# labelled identifiers in both languages
# ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,kind,value", [
    ("Employee ID: EMP-00123 joined in May.", "EMPLOYEE_ID", "EMP-00123"),
    ("Emp # 4521 is on leave", "EMPLOYEE_ID", "4521"),
    ("Staff number 88123, badge 00417", "EMPLOYEE_ID", "88123"),
    ("Badge: 00417", "EMPLOYEE_ID", "00417"),
    ("Payroll ID = PR-2024-0088", "EMPLOYEE_ID", "PR-2024-0088"),
    ("Account number: 4471-9920-11 is overdue", "ACCOUNT_NUMBER", "4471-9920-11"),
    ("Acct # 55-887-21", "ACCOUNT_NUMBER", "55-887-21"),
    ("Policy no. PL-2024-0088 renewed", "ACCOUNT_NUMBER", "PL-2024-0088"),
    ("Member ID 77-1234 expired", "ACCOUNT_NUMBER", "77-1234"),
    ("Customer ID: C-44821", "ACCOUNT_NUMBER", "C-44821"),
    ("Username: jdoe42", "USERNAME", "jdoe42"),
    ("Login: lou.vauquelin", "USERNAME", "lou.vauquelin"),
    ("user id = mt_2024", "USERNAME", "mt_2024"),
    ("Matricule : 4521A", "EMPLOYEE_ID", "4521A"),
    ("N° matricule 0047315", "EMPLOYEE_ID", "0047315"),
    ("Numéro de salarié : 88-123", "EMPLOYEE_ID", "88-123"),
    ("N° de compte : 00123456789", "ACCOUNT_NUMBER", "00123456789"),
    ("Compte client 4471-22 à jour", "ACCOUNT_NUMBER", "4471-22"),
    ("N° adhérent : 1234567", "ACCOUNT_NUMBER", "1234567"),
    ("Identifiant de connexion : jdoe42", "USERNAME", "jdoe42"),
    ("Nom d'utilisateur : lou.v", "USERNAME", "lou.v"),
    ("ID: AB-1234", "ID_CODE", "AB-1234"),
])
def test_labelled_ids(text, kind, value):
    assert (kind, value) in spans(text), spans(text)


def test_labelled_id_wins_over_the_generic_reference_kind():
    # "matricule" was a generic labelled reference (ID_CODE) in R1: the staff kind now wins the same span
    assert spans("Matricule : 4521A") == [("EMPLOYEE_ID", "4521A")]
    assert mask("Matricule : 4521A").text == "Matricule : MATRICULE_1"


@pytest.mark.parametrize("text", [
    "Employee ID: 2024",  # a year
    "Account number: 12/03/2024",  # a date
    "Badge: 10h30",  # a time
    "Account 1 250 000",  # a grouped number without a marker
    "Acct # 12 500 €",  # an amount
    "ID: 1234",  # generic label: letters and digits needed
    "ID card number 123",
    "Login : see the attached list",  # a value made of letters only must end its line
    "Employee ID: MATRICULE_1",  # a Shield code
    "the login of the agent",
])
def test_refused_labelled_values(text):
    assert not [k for k, _ in spans(text) if k in ("EMPLOYEE_ID", "ACCOUNT_NUMBER", "USERNAME", "ID_CODE")], text


def test_label_on_the_previous_line_form_layout():
    assert ("EMPLOYEE_ID", "4521A") in spans("Matricule :\n4521A")
    assert ("USERNAME", "jdoe42") in spans("Login:\njdoe42\n")


def test_siret_with_a_wrong_check_digit_and_its_label_on_the_previous_line():
    good, bad = siret_pair()
    text = f"SIRET\n{bad}\nAutre"
    cands = [c for c in detect_candidates(text) if c.kind == "SIRET"]
    assert cands and cands[0].valid and not cands[0].checked
    assert ("SIRET", bad) in spans(text)
    # no label at all: a bad check digit is not masked
    assert not [k for k, _ in spans(f"Total\n{bad}\nAutre") if k == "SIRET"]
    assert ("SIRET", good) in spans(f"n° {good}")


def test_same_id_written_differently_shares_one_code():
    s = MemoryStore()
    assert mask("Staff ID: EMP-00123.", s).text == "Staff ID: MATRICULE_1."
    r = mask("Later: EMP 00123 and emp-00123 and EMP-00123 again.", s)
    assert r.text == "Later: MATRICULE_1 and MATRICULE_1 and MATRICULE_1 again."


# ----------------------------------------------------------------------------------------------------------------
# routing numbers
# ----------------------------------------------------------------------------------------------------------------


def test_aba_routing_checksum():
    n = aba_number("12300456")
    assert aba_routing_valid(n)
    assert not aba_routing_valid(n[:-1] + str((int(n[-1]) + 1) % 10))
    assert not aba_routing_valid("99" + n[2:])  # not a Federal Reserve prefix
    assert not aba_routing_valid(n + "1")


def test_routing_number_needs_a_payment_word_on_the_line():
    n = aba_number("12300456")
    assert ("ACCOUNT_NUMBER", n) in spans(f"Routing number: {n}")
    assert ("ACCOUNT_NUMBER", n) in spans(f"wire to ABA {n}, account 1234")
    assert ("ACCOUNT_NUMBER", n) in spans(f"Routing {n}\nAccount 5566778899")
    bare = f"Le total est de {n} unités."
    assert not [k for k, _ in spans(bare) if k == "ACCOUNT_NUMBER"]
    assert not [sp for sp in find_suspects(bare) if sp.kind == "ACCOUNT_NUMBER"]


# ----------------------------------------------------------------------------------------------------------------
# id shape memory
# ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value,template", [
    ("EMP-00123", "EMP-ddddd"),
    ("emp 00123", "EMP ddddd"),
    ("PR/2024", "PR/dddd"),
    ("A1B2-7788", "AdBd-dddd"),
    ("123456", None),
    ("4521", None),
    ("AB12", None),
    ("EMP-00123-with-a-very-long-tail-00", None),
])
def test_shape_template(value, template):
    assert shape_template(value) == template


def test_shape_memory_masks_unlabelled_ids_of_the_dossier():
    s = MemoryStore()
    r1 = mask("Employee ID: EMP-00123 (Marc Vredenik).", s)
    assert ("EMPLOYEE_ID", "EMP-00123") in [(x.kind, x.value) for x in r1.spans]
    assert s.shapes() == [("EMPLOYEE_ID", "EMP-ddddd")]
    r2 = mask("The other badge holders are EMP-00456 and EMP-00789 today; invoice 00456 stays.", s)
    assert r2.text == "The other badge holders are MATRICULE_2 and MATRICULE_3 today; invoice 00456 stays."
    # a second masker on the same store knows the layout too
    assert masker(s).mask("ref EMP-00999").text == "ref MATRICULE_4"
    assert ("EMPLOYEE_ID", "EMP-00456", "shape") in valid_kinds("x EMP-00456", shapes=s.shapes())
    assert valid_kinds("x EMP-00456") == []


def test_digit_only_values_teach_no_shape():
    s = MemoryStore()
    mask("Matricule : 4521", s)
    assert s.shapes() == []
    assert spans("Le lot 4522 est vendu.", s) == []


def test_shape_memory_needs_a_store_that_keeps_shapes():
    class Bare:
        def __init__(self):
            self._inner = MemoryStore()

        def all(self):
            return self._inner.all()

        def get_by_norm(self, kind, norm):
            return self._inner.get_by_norm(kind, norm)

        def get_by_code(self, code):
            return self._inner.get_by_code(code)

        def add(self, kind, value, norm):
            return self._inner.add(kind, value, norm)

        def is_kept_clear(self, norm):
            return False

    s = Bare()
    assert mask("Staff ID: EMP-00123", s).text == "Staff ID: MATRICULE_1"
    assert mask("then EMP-00456", s).text == "then EMP-00456"


# ----------------------------------------------------------------------------------------------------------------
# tables
# ----------------------------------------------------------------------------------------------------------------


def test_table_columns_of_the_new_kinds():
    t = ("| Employee ID | Name | Account number | Login |\n|---|---|---|---|\n"
         "| EMP-00123 | Lou Vauquelin | 4471-9920-11 | lou.v |\n| 4521 | Marc Vredenik | 55887721 | see below |")
    got = spans(t)
    for item in (("EMPLOYEE_ID", "EMP-00123"), ("EMPLOYEE_ID", "4521"), ("ACCOUNT_NUMBER", "4471-9920-11"),
                 ("ACCOUNT_NUMBER", "55887721"), ("USERNAME", "lou.v")):
        assert item in got, got
    assert ("USERNAME", "see below") not in got and ("USERNAME", "see") not in got
    t2 = "| Matricule | Compte client |\n|---|---|\n| AX-55102 | 00123456789 |"
    assert ("EMPLOYEE_ID", "AX-55102") in spans(t2) and ("ACCOUNT_NUMBER", "00123456789") in spans(t2)


# ----------------------------------------------------------------------------------------------------------------
# language filter of the detector registry
# ----------------------------------------------------------------------------------------------------------------


def test_detect_candidates_language_filter(monkeypatch):
    def fake_en(text):
        for m in re.finditer(r"ZZ\d{4}", text):
            yield det.Candidate(m.start(), m.end(), "ID_CODE", True, 5, "fake_en")

    fake_en.langs = ("en",)

    def fake_any(text):
        for m in re.finditer(r"YY\d{4}", text):
            yield det.Candidate(m.start(), m.end(), "ID_CODE", True, 5, "fake_any")

    monkeypatch.setattr(det, "_en_detectors", lambda: (fake_en, fake_any))
    text = "ZZ1234 YY5678"
    assert {c.detector for c in detect_candidates(text, lang="en")} >= {"fake_en", "fake_any"}
    assert {c.detector for c in detect_candidates(text)} >= {"fake_en", "fake_any"}
    got_fr = {c.detector for c in detect_candidates(text, lang="fr")}
    assert "fake_any" in got_fr and "fake_en" not in got_fr


def test_en_detectors_absent_is_graceful():
    assert isinstance(det._en_detectors(), tuple)
    assert all(callable(f) for f in det.DETECTORS)


# ----------------------------------------------------------------------------------------------------------------
# birth dates with month names of both languages
# ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,value", [
    ("Date of birth: March 14, 1979", "March 14, 1979"),
    ("DOB 14 Mar 1979", "14 Mar 1979"),
    ("born on 2nd April 1980", "2nd April 1980"),
    ("née le 2 avril 1980", "2 avril 1980"),
    ("Né le 1er mars 1979", "1er mars 1979"),
])
def test_birth_dates_in_both_languages(text, value):
    assert ("BIRTHDATE", value) in spans(text)


def test_known_birth_date_is_found_in_its_english_forms():
    s = MemoryStore()
    mask("Née le 14 mars 1979, Madame Hélène Tardivel.", s)
    r = mask("DOB: March 14, 1979 and born 14 March 1979 and 14/03/1979.", s)
    assert r.text == "DOB: NAISSANCE_1 and born NAISSANCE_1 and NAISSANCE_1."
    assert structured_norm("BIRTHDATE", "March 14, 1979") == "1979-03-14" == structured_norm("BIRTHDATE", "14 mars 1979")


def test_reference_followed_by_an_english_month_keeps_the_day_out():
    assert ("CASE_REF", "4521") in spans("réf. 4521 12 march 2026")


# ----------------------------------------------------------------------------------------------------------------
# plates and reference-code guards
# ----------------------------------------------------------------------------------------------------------------


def test_plate_forms():
    assert ("ID_CODE", "AB-123-CD") in spans("Il a garé AB-123-CD devant.")
    assert ("ID_CODE", "AB 123-CD") in spans("Il a garé AB 123-CD devant.")
    assert ("ID_CODE", "AB-123 CD") in spans("Il a garé AB-123 CD devant.")
    assert spans("Il a garé AB 123 CD devant.") == []  # two spaces: needs a vehicle word
    assert ("ID_CODE", "AB 123 CD") in spans("véhicule AB 123 CD")
    got = spans("véhicule AB-123-CD-75 garé")
    assert ("ID_CODE", "AB-123-CD") in got and not any("75" in v for _k, v in got)
    assert spans("Il a garé AB-123-CDE devant.") == []


@pytest.mark.parametrize("text,forbidden", [
    ("Voir le dossier n° 2024. Il est clos.", ["2024", "2024. Il"]),
    ("N/Réf 2024. Nous vous écrivons.", ["2024"]),
    ("Selon le rapport (T4) du trimestre.", ["4", "T4"]),
    ("Un bilan (T12) a été établi.", ["12"]),
])
def test_false_reference_codes_are_refused(text, forbidden):
    got = [v for k, v in spans(text) if k in ("CASE_REF", "ID_CODE")]
    assert not any(v in forbidden for v in got), got


def test_reference_values_still_found_and_a_trailing_year_is_cut():
    assert ("CASE_REF", "4521") in spans("Réf. 4521 2024. Nous vous écrivons.")
    assert ("CASE_REF", "2024-0042") in spans("N/Réf. 2024-0042")
    assert ("ID_CODE", "1234") in spans("Me Lantier (T 1234)")
    assert ("ID_CODE", "1234") in spans("toque 1234")


# ----------------------------------------------------------------------------------------------------------------
# public URLs with a profile path, and a known name in a public URL path
# ----------------------------------------------------------------------------------------------------------------


def test_profile_paths_on_public_hosts_are_masked():
    assert spans("https://www.wikipedia.org/wiki/Droit") == []
    assert spans("voir https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006419288") == []
    assert ("URL", "https://www.wikipedia.org/user/jdoe42") in spans("https://www.wikipedia.org/user/jdoe42 ok")
    assert ("URL", "example.com/in/lou-vauquelin") in spans("see example.com/in/lou-vauquelin now")
    assert ("URL", "https://example.org/@lou.v") in spans("https://example.org/@lou.v")


def test_known_name_inside_a_public_url_path_gets_the_person_code():
    s = MemoryStore()
    mask("Jean Brizac est le gérant.", s)
    r = mask("Voir https://fr.wikipedia.org/wiki/Jean_Brizac et https://www.example.org/people/brizac-jean/bio", s)
    assert r.text == "Voir https://fr.wikipedia.org/wiki/PERSONNE_A et SITE_1"
    assert ("PERSON", "Jean_Brizac") in [(x.kind, x.value) for x in r.spans]


# ----------------------------------------------------------------------------------------------------------------
# casual text: lower-case first names, possessive, "@", comma at a line start
# ----------------------------------------------------------------------------------------------------------------


def test_casual_first_name_variants_in_chat_text():
    s = MemoryStore()
    mask("Priya Kervadec et Marc Vredenik sont les référents.", s)
    r = mask(CHAT, s)
    assert "priya" not in r.text.lower().replace("personne", "") and "vredenik" not in r.text.lower()
    assert r.text.count("PERSONNE_A") == 4 and r.text.count("PERSONNE_B") == 2
    assert "PERSONNE_A's draft" in r.text


def test_casual_variant_outside_chat_needs_a_cue():
    s = MemoryStore()
    mask("Priya Kervadec est la responsable.", s)
    formal = "La réunion est reportée. Le dossier de priya reste ouvert. Priya a répondu."
    r = mask(formal, s)
    assert r.text == "La réunion est reportée. Le dossier de priya reste ouvert. PERSONNE_A a répondu."
    assert mask("Le projet est prêt. Voici priya's notes.", s).text == "Le projet est prêt. Voici PERSONNE_A's notes."
    assert mask("Bonjour.\npriya, peux-tu relire ?", s).text == "Bonjour.\nPERSONNE_A, peux-tu relire ?"


def test_casual_variant_never_guesses_between_two_people_and_skips_common_words():
    s = MemoryStore()
    mask("Priya Kervadec et Priya Vredenik sont présentes. Pierre Brizac aussi.", s)
    r = mask("hello all\nping priya please\npierre de taille livré\n", s)
    first = {s.get_by_norm("PERSON", "priya kervadec").code, s.get_by_norm("PERSON", "priya vredenik").code}
    own = re.search(r"ping (PERSONNE_[A-Z]+) please", r.text)
    assert own and own.group(1) not in first  # masked, restorable, never one of the two Priyas
    assert r.text.endswith("pierre de taille livré\n")
    assert not [v for v in nm.person_variants("Pierre Brizac") if v.need == "casual"]
    assert [v for v in nm.person_variants("Priya Kervadec") if v.need == "casual"][0].case == "any"


def test_lower_case_company_in_chat_text():
    s = MemoryStore()
    mask("La société Zorb SAS a signé.", s)
    assert mask("hi all\nsent it to zorb this morning\nthanks\n", s).text == "hi all\nsent it to SOCIETE_A this morning\nthanks\n"
    assert mask("La facture a été envoyée. Un zorb est un jouet.", s).text == "La facture a été envoyée. Un zorb est un jouet."


def test_casual_text_fallback_rule():
    from ragbase_shield.engine.masker import _casual_text_fallback as casual

    assert casual("hi\nping <@U024BE7LH>")
    assert casual("one line\nanother line\nThird line")
    assert not casual("La Cour. Le Tribunal. Attendu que. Par ces motifs.")
    assert not casual("")


# ----------------------------------------------------------------------------------------------------------------
# comma lists after a plural title; civility of shared surnames
# ----------------------------------------------------------------------------------------------------------------


def test_comma_list_after_a_plural_title():
    t = "Composée de Mmes Vauquelin, Tardivel, Ormesson et Brizac, conseillers, et de M. Lantier, greffier."
    r = mask(t)
    assert r.text == ("Composée de Mmes PERSONNE_A, PERSONNE_B, PERSONNE_C et PERSONNE_D, conseillers, et de "
                      "M. PERSONNE_E, greffier.")
    assert ("PERSON", "Lantier") in spans("Maîtres Ormesson, Brizac, Lantier, avocats au barreau")
    assert ("PERSON", "Kervadec") in spans("MM. Vredenik, Kervadec, Président et Secrétaire")
    got = spans("MM. Vredenik, Kervadec, Président et Secrétaire")
    assert ("PERSON", "Président") not in got and ("PERSON", "Secrétaire") not in got
    got2 = spans("Mes Tardivel, Vauquelin et la société Brivanor SAS")
    assert ("PERSON", "Vauquelin") in got2 and not any(k == "PERSON" and "Brivanor" in v for k, v in got2)


def test_title_civility_and_person_civility(monkeypatch):
    assert nm.title_civility("vu par Mme ", 11) == "F"
    assert nm.title_civility("avec M. ", 8) == "M"
    assert nm.title_civility("Mrs ", 4) == "F" and nm.title_civility("Mr ", 3) == "M"
    assert nm.title_civility("avec Me ", 8) == "" and nm.title_civility("avec ", 5) == ""
    monkeypatch.setattr(nm, "_first_name_sex", lambda: {"jean": "M", "marie": "F"})
    assert nm.person_civility("Jean Kervadec") == "M" and nm.person_civility("Marie-Lou Kervadec") == "F"
    assert nm.person_civility("Kervadec") == "" and nm.person_civility("Lou Kervadec") == ""


def test_shared_surname_resolved_by_civility(monkeypatch):
    monkeypatch.setattr(nm, "_first_name_sex", lambda: {"jean": "M", "helene": "F"})
    s = MemoryStore()
    mask("M. Jean Kervadec est le gérant.", s)
    mask("Mme Hélène Kervadec est la gérante.", s)
    r = mask("Mme Kervadec a signé. M. Kervadec aussi. Kervadec seul est ambigu.", s)
    jean = s.get_by_norm("PERSON", "jean kervadec").code
    marie = s.get_by_norm("PERSON", "helene kervadec").code
    assert jean != marie
    assert r.text.startswith(f"Mme {marie} a signé. M. {jean} aussi. ")
    alone = r.spans[-1]
    assert alone.value == "Kervadec" and r.text.split("aussi. ")[1].split()[0] not in (jean, marie)


def test_shared_surname_without_sex_data_keeps_r1_behaviour(monkeypatch):
    monkeypatch.setattr(nm, "_first_name_sex", lambda: {})
    s = MemoryStore()
    mask("M. Jean Kervadec est le gérant.", s)
    mask("Mme Hélène Kervadec est la gérante.", s)
    r = mask("Mme Kervadec a signé.", s)
    codes = {s.get_by_norm("PERSON", "jean kervadec").code, s.get_by_norm("PERSON", "helene kervadec").code}
    assert r.text.split()[1] not in codes and r.text.split()[1].startswith("PERSONNE_")


# ----------------------------------------------------------------------------------------------------------------
# acronym of a known company inside a hyphenated code
# ----------------------------------------------------------------------------------------------------------------


def test_company_acronym_inside_a_hyphenated_code():
    s = MemoryStore()
    r = mask("La société Brasseries Velanor Quimpertin SAS livre les lots BVQ-1042 et BVQ-1043, pas ABC-1042.", s)
    assert r.text == "La société SOCIETE_A SAS livre les lots SOCIETE_A-1042 et SOCIETE_A-1043, pas ABC-1042."
    assert mask("Lot BVQ-2044 (annexe)", s).text == "Lot SOCIETE_A-2044 (annexe)"
    assert mask("Le sigle BVQ seul, puis BVQ-X-2024.", s).text == "Le sigle SOCIETE_A seul, puis SOCIETE_A-X-2024."


def test_two_companies_with_one_acronym_are_never_guessed():
    s = MemoryStore()
    r = mask("Brasseries Velanor Quimpertin SAS et Bureau Vexin Qualité SARL : lot BVQ-1042.", s)
    assert "BVQ-1042" in r.text


# ----------------------------------------------------------------------------------------------------------------
# legal-form policy switch
# ----------------------------------------------------------------------------------------------------------------


def test_legal_form_switch(monkeypatch):
    text = "Entre la société BRIVANOR LOGISTIQUE SAS et la SARL Kervalen, il est convenu."
    monkeypatch.delenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", raising=False)
    assert not config.mask_legal_form()
    assert mask(text).text == "Entre la société SOCIETE_A SAS et la SARL SOCIETE_B, il est convenu."
    monkeypatch.setenv("RAGBASE_SHIELD_MASK_LEGAL_FORM", "1")
    assert config.mask_legal_form()
    s = MemoryStore()
    m = masker(s)
    r = m.mask(text)
    assert r.text == "Entre la société SOCIETE_A et la SOCIETE_B, il est convenu."
    assert m.unmask(r.text) == text
    assert m.mask("BRIVANOR LOGISTIQUE seule.").text == "SOCIETE_A seule."


# ----------------------------------------------------------------------------------------------------------------
# canary and leaks
# ----------------------------------------------------------------------------------------------------------------


def test_canary_finds_registered_usernames_and_ids():
    s = MemoryStore()
    m = masker(s)
    m.mask("Employee ID: EMP-00123, login lou.vauquelin, account number 4471-9920-11, <@U024BE7LH>.")
    out = "the answer cites EMP 00123, LOU.VAUQUELIN, 4471 9920 11 and U024BE7LH"
    found = {sp.kind for sp in m.scan(out)}
    assert found >= {"EMPLOYEE_ID", "USERNAME", "ACCOUNT_NUMBER"}
    assert m.scan("MATRICULE_1 PSEUDO_1 COMPTE_1 PSEUDO_2") == []


def test_mask_result_holds_no_real_value_in_codes():
    r = mask("Staff ID: EMP-00123, login lou.vauquelin, account number 4471-9920-11, <@U024BE7LH>.")
    for value in ("EMP-00123", "lou.vauquelin", "4471-9920-11", "U024BE7LH"):
        assert value not in r.text
    assert [e.kind for e in r.new_entities] == ["EMPLOYEE_ID", "USERNAME", "ACCOUNT_NUMBER", "USERNAME"]
