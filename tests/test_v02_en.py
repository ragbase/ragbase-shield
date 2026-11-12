"""v0.2 LOCALE-EN: language detection, the English lexicon bundle, the English name rules, the English
protected intervals and the US/UK structured detectors. Every name, number and address is invented."""
import re
import time

import pytest

from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import locale as lc
from ragbase_shield.engine.detectors import detect_structured
from ragbase_shield.engine.normalize import fold, tokens


# --- helpers ----------------------------------------------------------------------------------------------


def names(text):
    return [(text[s.start:s.end], s.kind) for s in lc.detect_names_en(text)]


def rules(text):
    return {(text[s.start:s.end], s.rule) for s in lc.detect_names_en(text)}


def persons(text):
    return [v for v, k in names(text) if k == "PERSON"]


def orgs(text):
    return [v for v, k in names(text) if k == "ORG"]


def found(text):
    return [(s.kind, s.value) for s in detect_structured(text, det.detect_candidates_en(text))]


def protected(text):
    f = fold(text)
    iv = lc.protected_intervals_en(text, f, tokens(f.text))
    return [text[s:e] for s, e in zip(iv._starts, iv._ends)]


@pytest.fixture(scope="module")
def en():
    return lc.bundle("en")


# --- language detection ------------------------------------------------------------------------------------


EN_TEXTS = [
    "Hi Priya, please send the invoice to Marcus by Friday. Thanks for your help with the report.",
    "The tenant shall pay the rent on the first day of each month, and the landlord shall maintain the premises.",
    "We are pleased to offer you the position of Senior Analyst. Your start date will be confirmed by email.",
    "can you check the deploy? it failed again and the logs are empty, I think the token expired",
    "Please find attached the signed agreement. Let me know if you have any questions about the terms.",
    "The board approved the budget for next year, with a focus on the new platform and the hiring plan.",
    "Our team met the client at their office to review the contract and the payment schedule.",
    "If you need anything else from us before the meeting, just let me know and we will sort it out.",
    "She said that the report was late because the data from the vendor had not been delivered yet.",
    "Thanks again for your time today. We will follow up with the proposal by the end of the week.",
    "The court held that the employer had not breached the agreement when it terminated the contract.",
    "I have reviewed the file and I think we should settle. The other side will not go to trial.",
    "Dear Mr. Thurlowe, we are writing to confirm that your application has been received by our office.",
    "Monday: standup at nine, then the review with the design team and the call with the vendor.",
    "The invoice is overdue by thirty days. Please remit payment to the account listed below.",
    "Notes from the call: they want a demo next week, and they asked about pricing for two hundred seats.",
    "You should have received the package yesterday. If not, please contact the carrier with the tracking number.",
    "Here is the summary of the changes we discussed, with the open questions listed at the end.",
    "The new policy applies to all employees from the first of the month, as explained in the memo.",
    "Could you share the slides before the meeting so that everyone has time to read them?",
]
FR_TEXTS = [
    "Bonjour Madame, veuillez trouver ci-joint le contrat de travail signé par le salarié. Cordialement.",
    "La cour d'appel a confirmé le jugement et condamné la société aux dépens de la procédure.",
    "Le locataire s'engage à payer le loyer le premier de chaque mois et à entretenir les lieux loués.",
    "Nous avons le plaisir de vous proposer le poste d'analyste. La date de début sera confirmée par courriel.",
    "peux-tu vérifier le déploiement ? il a encore échoué et les journaux sont vides, je pense que le jeton a expiré",
    "Merci de trouver ci-joint l'accord signé. N'hésitez pas si vous avez des questions sur les conditions.",
    "Le conseil a approuvé le budget de l'année prochaine, avec une priorité sur la nouvelle plateforme.",
    "Notre équipe s'est rendue sur place pour revoir le contrat et l'échéancier de paiement.",
    "Si vous avez besoin d'autre chose avant la réunion, dites-le moi et nous nous en occuperons.",
    "Elle a dit que le rapport était en retard parce que les données du fournisseur n'étaient pas arrivées.",
    "Le tribunal a jugé que l'employeur n'avait pas violé l'accord en mettant fin au contrat.",
    "J'ai relu le dossier et je pense que nous devrions transiger. La partie adverse n'ira pas au procès.",
    "Monsieur, nous vous confirmons que votre demande a bien été reçue par nos services.",
    "Lundi : point à neuf heures, puis la revue avec l'équipe design et la réunion de l'après-midi.",
    "La facture est en retard de trente jours. Merci de régler le montant sur le compte indiqué ci-dessous.",
    "Notes de l'appel : ils veulent une démonstration la semaine prochaine et demandent les tarifs.",
    "Vous auriez dû recevoir le colis hier. Sinon, contactez le transporteur avec le numéro de suivi.",
    "Voici le résumé des changements dont nous avons discuté, avec les questions ouvertes à la fin.",
    "La nouvelle politique s'applique à tous les salariés à compter du premier du mois, comme indiqué.",
    "Pourriez-vous partager les diapositives avant la réunion pour que chacun ait le temps de les lire ?",
]


@pytest.mark.parametrize("text", EN_TEXTS)
def test_detect_language_en(text):
    assert lc.detect_language(text) == "en"
    assert lc.detect_language(text, default="en") == "en"


@pytest.mark.parametrize("text", FR_TEXTS)
def test_detect_language_fr(text):
    assert lc.detect_language(text) == "fr"
    assert lc.detect_language(text, default="en") == "fr"


def test_detect_language_short_and_empty_take_default():
    assert lc.detect_language("Hi Priya") == "fr"
    assert lc.detect_language("Hi Priya", default="en") == "en"
    assert lc.detect_language("") == "fr"
    assert lc.detect_language("12 34 56 78 90 ++ --", default="en") == "en"


def test_detect_language_mixed_takes_the_dominant_one():
    mixed = "La direction a envoyé the invoice and the contract to the team for review before the meeting with the board."
    assert lc.detect_language(mixed) == "en"
    mixed_fr = "The client a envoyé la facture et le contrat à l'équipe pour relecture avant la réunion avec le conseil."
    assert lc.detect_language(mixed_fr, default="en") == "fr"


def test_detect_language_is_deterministic():
    text = EN_TEXTS[0] + "\n" + FR_TEXTS[0]
    assert len({lc.detect_language(text) for _ in range(20)}) == 1


def test_casual_text():
    assert lc.casual_text("hey can you ping marcus\nsure, on it\nthanks")
    assert lc.casual_text("<@U024ABCDE> can you check this?")
    assert lc.casual_text("Reminder @channel the review moved to 3pm")
    assert not lc.casual_text("Dear Sir,\nPlease find attached the signed agreement.\nRegards")
    assert not lc.casual_text("")
    assert not lc.casual_text("Re: invoice\nRe: contract\nRe: meeting")


def test_language_setting(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_LANGUAGE", raising=False)
    assert lc.language_setting() == "auto"
    monkeypatch.setenv("RAGBASE_SHIELD_LANGUAGE", "EN")
    assert lc.language_setting() == "en"
    monkeypatch.setenv("RAGBASE_SHIELD_LANGUAGE", "fr")
    assert lc.language_setting() == "fr"
    monkeypatch.setenv("RAGBASE_SHIELD_LANGUAGE", "anything")
    assert lc.language_setting() == "auto"


# --- bundles -------------------------------------------------------------------------------------------------


def test_en_files_and_sections_exist():
    for name, sections in lc.EN_FILES.items():
        secs = lc.read_sections(name)
        for sec in sections:
            assert secs.get(sec), f"{name} has no entries in [{sec}]"


def test_bundle_en_sizes(en):
    assert len(en.all_first_names) > 5000
    assert len(en.first_names) > 4500
    assert len(en.stopwords) > 300
    assert len(en.vocab) > 1500
    assert len(en.places) > 400
    assert len(en.whitelist_phrases) > 250
    assert len(en.legal_terms) > 400
    assert en.legal_forms["inc"] == "strong" and en.legal_forms["co"] == "weak" and en.legal_forms["co."] == "strong"
    assert ("limited", "liability", "company") in en.legal_forms_spelled


def test_bundle_en_first_names_sex_and_nicknames(en):
    assert en.first_name_sex["priya"] == "F"
    assert en.first_name_sex["marcus"] == "M"
    assert lc.first_name_sex("Priya", en) == "F"
    assert lc.first_name_sex("Marcus-Lee", en) == "M"
    assert lc.first_name_sex("Xyzzyq", en) == "U"
    assert "bill" in en.nicknames["william"] and "peggy" in en.nicknames["margaret"]


@pytest.mark.parametrize("name,strong", [
    ("priya", True), ("jennifer", True), ("marcus", True), ("olivia", True), ("kofi", True),
    ("mark", False), ("will", False), ("grace", False), ("hope", False), ("april", False), ("virginia", False),
    ("summer", False), ("bill", False), ("chase", False), ("dean", False),
])
def test_strong_and_ambiguous_first_names(en, name, strong):
    assert name in en.all_first_names
    assert (name in en.first_names) is strong
    assert lc.is_first_name(name.capitalize(), en) is strong
    assert lc.is_first_name(name.capitalize(), en, strong=False)


def test_bundle_isolation_between_languages(en):
    fr = lc.bundle("fr")
    # "Avec" is a French stop word and a fine name word in English; "Which" the reverse.
    assert lc.is_name_word("Avec", en) and not lc.is_name_word("Avec", fr)
    assert lc.is_name_word("Which", fr) and not lc.is_name_word("Which", en)
    assert "pat" in en.vocab and "pat" not in fr.stopwords
    assert fr.lang == "fr" and en.lang == "en"
    assert fr.first_names and "jean" in fr.first_names and "jean" not in en.first_names  # a word in English


def test_bundle_is_cached():
    assert lc.bundle("en") is lc.bundle("EN") is lc.bundle("en-US")
    assert lc.bundle("fr") is lc.bundle("anything-else")


# --- predicates -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("word,expected", [
    ("Inc.", "strong"), ("Inc", "strong"), ("INC", "strong"), ("LLC", "strong"), ("Ltd", "strong"),
    ("Limited", "strong"), ("Corp.", "strong"), ("Co.", "strong"), ("Co", None), ("CO", "weak"),
    ("co", None), ("L.P.", "strong"), ("LP", "weak"), ("lp", None), ("S.A.", "strong"), ("SA", "weak"),
    ("Company", "weak"), ("GmbH", "strong"), ("PLC", "strong"), ("plc", None), ("Street", None),
])
def test_legal_form(en, word, expected):
    assert lc.legal_form(word, en) == expected


@pytest.mark.parametrize("word,person,org", [
    ("Thurlowe", True, True), ("Northvale", True, True), ("Street", False, True), ("Team", False, True),
    ("The", False, False), ("Monday", False, False), ("Mr", False, False), ("Inc", False, False),
    ("Partners", False, True), ("Brown", True, True), ("Boston", True, True), ("Priya", True, True),
    ("IT", False, True), ("HR", False, True), ("Attorney", False, True), ("Review", False, True),
    ("General", False, True), ("First", False, True), ("Which", False, False),
    ("O'Brien", True, True), ("Hale-Whitlaw", True, True), ("x", False, False), ("thurlowe", False, False),
])
def test_is_name_word(en, word, person, org):
    assert lc.is_name_word(word, en) is person
    assert lc.is_name_word(word, en, kind="ORG") is org


def test_is_name_word_flags(en):
    assert lc.is_name_word("Brown", en) and not lc.is_name_word("Brown", en, allow_common=False)
    assert lc.is_name_word("Boston", en) and not lc.is_name_word("Boston", en, allow_place=False)


@pytest.mark.parametrize("word,expected", [
    ("Northvale", True), ("Brightwater", True), ("Thurlowe", True), ("Brown", False), ("Boston", False),
    ("Priya", False), ("Group", False), ("Review", False), ("IBM", False), ("Co", False), ("Li", False),
])
def test_is_distinctive(en, word, expected):
    assert lc.is_distinctive(word, en) is expected


def test_small_predicates(en):
    assert lc.is_place("Boston", en) and lc.is_place("TX", en) and not lc.is_place("Northvale", en)
    assert lc.is_acronym("IBM", en) and lc.is_acronym("Nasdaq", en) and lc.is_acronym("Q3", en)
    assert not lc.is_acronym("Priya", en) and not lc.is_acronym("Northvale", en)
    assert lc.is_title("Mr", en) and lc.is_title("Judge", en) and not lc.is_title("Priya", en)
    assert lc.is_vocab_word("Review", en) and lc.is_vocab_word("The", en) and not lc.is_vocab_word("Northvale", en)
    assert lc.is_stopword("the", en) and not lc.is_stopword("Priya", en)
    assert lc.dictionary_word("review", "en") and lc.dictionary_word("priya", "en")
    assert not lc.dictionary_word("northvale", "en")
    assert lc.dictionary_word("societe", "fr") and not lc.dictionary_word("kervadec", "fr")


# --- English person rules -------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,name", [
    ("Mr. Thurlowe signed the lease.", "Thurlowe"),
    ("Dr. Priya Ravikar will attend.", "Priya Ravikar"),
    ("Ms Hale-Whitlaw objected.", "Hale-Whitlaw"),
    ("Dear Mrs. O'Brien, thank you.", "O'Brien"),
    ("Prof Kofi Ansomah presented.", "Kofi Ansomah"),
    ("Judge Thurlowe ruled.", "Thurlowe"),
    ("Senator Lee spoke.", "Lee"),
    ("Mr. J. P. Morgan-Cortez Jr. replied.", "J. P. Morgan-Cortez Jr."),
    ("MR. THURLOWE SIGNED.", "THURLOWE"),
])
def test_titles(text, name):
    assert (name, "PERSON") in names(text)


@pytest.mark.parametrize("text,name", [
    ("Marcus Lee sent the deck.", "Marcus Lee"),
    ("Please thank Jennifer Obiekwe for the report.", "Jennifer Obiekwe"),
    ("Priya K. Thurlowe joined.", "Priya K. Thurlowe"),
    ("Kofi Ansomah, Aisha Mohammed and Wei Zhang attended.", "Aisha Mohammed"),
    ("Hiroshi Takemura and Olu Adebanjo agreed.", "Olu Adebanjo"),
    ("Priya van der Hoeven called.", "Priya van der Hoeven"),
    ("Marcus Lee III attended.", "Marcus Lee III"),
    ("Grace Okwuosa signed.", "Grace Okwuosa"),
    ("We met Virginia Woolf in Virginia.", "Virginia Woolf"),
    ("Paris Hilton stayed in Paris.", "Paris Hilton"),
    ("Contact Mark Ellis today.", "Mark Ellis"),
    ("Thanks to Will Smith for the help.", "Will Smith"),
    ("From: Marcus Lee <marcus.lee@example.com>", "Marcus Lee"),
    ("PRIYA THURLOWE\nSenior Analyst", "PRIYA THURLOWE"),
])
def test_first_name_surname(text, name):
    assert (name, "PERSON") in names(text)


@pytest.mark.parametrize("text", [
    "Grace Period applies to the invoice.",
    "Mark Review the draft before Friday.",
    "Will Smith arrive before noon?",          # ambiguous first name + common surname at a sentence start
    "Hope Street is closed.",
    "Chase Bank called.",
    "The Finance Team met the Legal Department on Monday.",
    "Happy Monday everyone, the Sales Update is attached.",
    "PRIYA Thurlowe",                           # not the English name order (an acronym before a name)
    "Lake Mary and Fort Worth are places.",
    "Rose Garden tickets are on sale.",
    "Summer Sale starts Friday.",
])
def test_no_person_on_common_words(text):
    assert persons(text) == []


def test_ambiguous_first_name_with_common_surname_mid_sentence():
    assert "Will Smith" in persons("I saw Will Smith yesterday.")
    assert "Mark Brown" in persons("We spoke to Mark Brown about it.")


@pytest.mark.parametrize("text,name", [
    ("Thurlowe, Priya", "Thurlowe, Priya"),
    ("Obiekwe, Jennifer K.", "Obiekwe, Jennifer K."),
    ("Attendees: Thurlowe, Priya; Obiekwe, Marcus", "Obiekwe, Marcus"),
])
def test_surname_first(text, name):
    assert (name, "PERSON") in names(text)


@pytest.mark.parametrize("text", [
    "Boston, Massachusetts",
    "Thanks, Priya",             # the greeting rule takes "Priya", never "Thanks, Priya"
    "Question, Priya",
    "Monday, Marcus",
    "Thurlowe, Priya Ravikar",     # two people in a list, not "Last, First"
])
def test_surname_first_guards(text):
    assert not any("," in v for v in persons(text))


@pytest.mark.parametrize("text,expected", [
    ("Hi Priya, can you send the deck?", ["Priya"]),
    ("Hello Marcus Lee,", ["Marcus Lee"]),
    ("Dear Mr. Thurlowe,", ["Thurlowe"]),
    ("Thanks Marcus", ["Marcus"]),
    ("Thank you Priya!", ["Priya"]),
    ("Hi Priya and Marcus,", ["Priya", "Marcus"]),
    ("Hi Priya, Marcus, Jennifer", ["Priya", "Marcus", "Jennifer"]),
    ("Hi April,", ["April"]),
    ("Hi Summer, how are you?", ["Summer"]),
    ("cc Lee", ["Lee"]),
    ("Good morning Priya", ["Priya"]),
])
def test_greetings(text, expected):
    assert persons(text) == expected


@pytest.mark.parametrize("text", [
    "Hi Team,", "Hello World", "Dear Customer,", "Dear Sir or Madam,", "Thanks Again", "Best Western",
    "Hi there,", "Thank You", "Hi all,", "Hi May 5 meeting",
])
def test_greetings_guards(text):
    assert persons(text) == []


@pytest.mark.parametrize("text,name", [
    ("Thanks,\nPriya Thurlowe\nSenior Analyst", "Priya Thurlowe"),
    ("Best regards,\nMarcus", "Marcus"),
    ("Kind regards\nP. Ravikar", "P. Ravikar"),
    ("Cheers,\nJennifer Obiekwe | Northvale", "Jennifer Obiekwe"),
    ("Thanks again,\n\nMarcus Lee", "Marcus Lee"),
])
def test_signoffs(text, name):
    assert (name, "PERSON") in names(text)
    assert ("Senior Analyst", "PERSON") not in names(text)


def test_signoff_guards():
    assert persons("Thanks,\nThe Northvale Team") == []
    assert persons("Best,\nSales Department") == []


@pytest.mark.parametrize("text,expected", [
    ("[10:32] Priya: can you check the deploy?", ["Priya"]),
    ("10:33 AM Marcus Lee: done", ["Marcus Lee"]),
    ("Priya: yes\nMarcus: no", ["Priya", "Marcus"]),
    ("> Jennifer Obiekwe: please review", ["Jennifer Obiekwe"]),
])
def test_speaker_labels(text, expected):
    assert persons(text) == expected


@pytest.mark.parametrize("text", ["Sales Update: nothing new", "Note: see below", "Subject: Re: contract",
                                  "Mark: fixed", "marcus: sure"])
def test_speaker_guards(text):
    assert ("speaker" not in {r for _, r in rules(text)})


@pytest.mark.parametrize("text,name", [
    ("Our manager Jane Doe reports to the board.", "Jane Doe"),
    ("my colleague Priya will join", "Priya"),
    ("attorney Mark Ellis filed it", "Mark Ellis"),
    ("the tenant Marcus Lee paid", "Marcus Lee"),
    ("nurse Grace confirmed", "Grace"),
])
def test_roles(text, name):
    assert (name, "PERSON") in names(text)


def test_role_guards():
    assert persons("the manager will decide") == []
    assert persons("the client Review Board met") == []


def test_possessive_first_name_and_bare_first_names():
    assert ("Priya", "possessive_first") in rules("Priya's laptop broke.")
    assert persons("Jennifer sent it. Olivia approved. Update Priya on this.") == ["Jennifer", "Olivia", "Priya"]
    assert persons("Grant access to Dawn.") == []            # ambiguous names alone stay in clear
    assert persons("Priya Update is attached") == []         # a capitalised word after it: not a person
    assert ("Priya", "first_alone") in rules("ping Priya about it")


# --- English company rules ------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,name", [
    ("Northvale Analytics Inc. filed.", "Northvale Analytics"),
    ("The contract with Brightwater Capital Partners, LLC ends.", "Brightwater Capital Partners"),
    ("Lakeshore Medical Center Inc. went public.", "Lakeshore Medical Center"),
    ("General Motors LLC and The Harrowgate Toy Company reported.", "General Motors"),
    ("Ben & Jerry's Homemade Inc. reported.", "Ben & Jerry's Homemade"),
    ("Kestrel Logistics Ltd paid.", "Kestrel Logistics"),
    ("Northvale Co. and Brightwater Limited Liability Company merged.", "Brightwater"),
    ("Hale & Whitlaw P.C. advised.", "Hale & Whitlaw"),
    ("Orion Robotics GmbH expanded.", "Orion Robotics"),
])
def test_legal_forms_after_name(text, name):
    assert (name, "ORG") in names(text)


def test_legal_form_guards():
    assert orgs("The Company shall pay.") == []
    assert orgs("the company Inc") == []
    assert orgs("Terms and Conditions Co") == []


@pytest.mark.parametrize("text,name", [
    ("Brightwater Capital Partners hired her.", "Brightwater Capital Partners"),
    ("Hope Analytics shipped it.", "Hope Analytics"),
    ("Chase Bank called.", "Chase Bank"),
    ("Boston Consulting Group advised.", "Boston Consulting Group"),
    ("Kestrel Logistics delivered.", "Kestrel Logistics"),
    ("Northvale Software and Services", "Northvale Software and Services"),
    ("Ellis & Partners filed.", "Ellis & Partners"),
    ("ORION ROBOTICS SYSTEMS", "ORION ROBOTICS SYSTEMS"),
])
def test_suffix_companies(text, name):
    assert (name, "ORG") in names(text)


@pytest.mark.parametrize("text", [
    "The Finance Team met the Legal Department.",
    "Global Services are listed.",
    "Capital Partners is a generic phrase.",
    "Sales Group update",
    "Attorney Mark Ellis of Ellis & Partners filed.",   # the suffix rule never crosses "of"
])
def test_suffix_guards(text):
    assert all(v not in ("Finance Team", "Global Services", "Capital Partners", "Sales Group",
                         "Mark Ellis of Ellis & Partners") for v in orgs(text))


@pytest.mark.parametrize("text,name", [
    ("Baker & McKenzie advised.", "Baker & McKenzie"),
    ("Smith, Jones & Rowe LLP advised.", "Smith, Jones & Rowe"),
    ("Johnson & Johnson reported.", "Johnson & Johnson"),
    ("Hale & Whitlaw Partners filed.", "Hale & Whitlaw Partners"),
])
def test_partnerships(text, name):
    assert (name, "ORG") in names(text)


def test_partnership_guards():
    assert orgs("Tom & Jerry are cartoons.") == []
    assert orgs("Research & Development costs rose.") == []
    assert orgs("Terms & Conditions apply.") == []


@pytest.mark.parametrize("text,name", [
    ("She works at Northvale.", "Northvale"),
    ("He joined Brightwater last year.", "Brightwater"),
    ("Our client Lakeshore Medical signed.", "Lakeshore Medical"),
    ("the vendor Kestrel Logistics", "Kestrel Logistics"),
    ("at Family Depot", "Family Depot"),
])
def test_triggers(text, name):
    assert (name, "ORG") in names(text)


@pytest.mark.parametrize("text", [
    "we met at Lunch at Home at Boston", "at Priya's desk", "she joined Monday", "at Noon", "client Review",
    "at Lakeshore Medical Center Inc.",   # the legal form rule takes it; the trigger rule stays out
])
def test_trigger_guards(text):
    assert all(v not in ("Lunch", "Home", "Boston", "Priya", "Monday", "Noon", "Review") for v in orgs(text))


@pytest.mark.parametrize("text,name", [
    ("Bank of America and the University of Northvale sued.", "Bank of America"),
    ("Bank of America and the University of Northvale sued.", "University of Northvale"),
    ("the Church of England replied", "Church of England"),
    ("First National Bank of Kestrel", "First National Bank of Kestrel"),
])
def test_org_of(text, name):
    assert (name, "ORG") in names(text)


def test_org_of_guards():
    assert orgs("the bank of the river") == []
    assert orgs("School of Thought") == []


def test_possessive_companies():
    assert ("Northvale", "ORG") in names("Northvale's Q3 results slipped.")
    assert ("Brightwater", "ORG") in names("Brightwater's CEO resigned.")
    assert orgs("Priya's team won.") == []
    assert orgs("Brown's revenue") == []


def test_dedupe_keeps_longest_and_highest_priority():
    spans = lc.detect_names_en("Hi Priya, can you send the deck?")
    assert [(s.rule, s.priority) for s in spans if s.start == 3] == [("greeting", 3)]
    text = "Brightwater Capital Partners hired her."
    assert [t for t in orgs(text)] == ["Brightwater Capital Partners"]


def test_rule_spans_are_rulespans_and_in_range():
    from ragbase_shield.engine.names import RuleSpan

    text = "Hi Priya, Marcus Lee at Northvale Analytics Inc. says Mr. Thurlowe's report is late.\nBest,\nJennifer"
    for s in lc.detect_names_en(text):
        assert isinstance(s, RuleSpan)
        assert 0 <= s.start < s.end <= len(text)
        assert s.kind in ("PERSON", "ORG") and s.priority >= 2 and s.rule


# --- protected intervals --------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,phrase", [
    ("The Securities and Exchange Commission fined them.", "Securities and Exchange Commission"),
    ("Filed in the United States District Court for the Northern District of California.",
     "United States District Court for the Northern District of California"),
    ("The Court of Appeals for the Ninth Circuit reversed.", "Court of Appeals for the Ninth Circuit"),
    ("Under the Clean Air Act of 1970 and Section 230.", "Clean Air Act of 1970"),
    ("Under the Clean Air Act of 1970 and Section 230.", "Section 230"),
    ("Cook County sued.", "Cook County"),
    ("The Department of Labor and the Office of the Attorney General replied.", "Department of Labor"),
    ("The Department of Labor and the Office of the Attorney General replied.", "Office of the Attorney General"),
    ("See Rule 12(b)(6) and Title VII.", "Rule 12(b)(6)"),
    ("HM Revenue & Customs wrote.", "HM Revenue & Customs"),
    ("the Employment Tribunal in Leeds", "Employment Tribunal"),
    ("per the General Data Protection Regulation", "General Data Protection Regulation"),
])
def test_protected_intervals_en(text, phrase):
    assert any(phrase in p for p in protected(text))


def test_protected_intervals_leave_names_alone():
    text = "Priya Thurlowe of Northvale Analytics Inc. met Marcus Lee."
    assert protected(text) == []


def test_whitelist_matcher_en_has_phrases():
    assert len(lc.whitelist_matcher_en()) > 250


# --- masker regexes -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("before,ok", [
    ("Mr. ", True), ("Dr ", True), ("Judge ", True), ("JUDGE ", True), ("Professor ", True), ("Ms ", True),
    ("the ", False), ("Mister ", True), ("Mr.", False), ("Summer ", False),
])
def test_title_before_re_en(before, ok):
    assert bool(lc.title_before_re("en").search(before)) is ok


@pytest.mark.parametrize("before,ok", [
    ("Hi ", True), ("Hi, ", True), ("Dear ", True), ("Thanks all, ", True), ("Best,\n", True),
    ("Kind regards,\n", True), ("Cheers\n", True), ("Talk soon,\n", True), ("cc ", True),
    ("the ", False), ("Best ", False), ("regards", False),
])
def test_salute_before_re_en(before, ok):
    assert bool(lc.salute_before_re("en").search(before)) is ok


def test_fr_regexes_are_the_v01_ones():
    from ragbase_shield.engine import masker

    assert lc.title_before_re("fr") is masker._TITLE_BEFORE_RE
    assert lc.salute_before_re("fr") is masker._SALUTE_BEFORE_RE


# --- US and UK detectors --------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,value", [
    ("Call me at (415) 555-0134 tomorrow.", "(415) 555-0134"),
    ("Office 415-555-0134 x204.", "415-555-0134 x204"),
    ("fax 802.555.0193", "802.555.0193"),
    ("cell: 4155550177", "4155550177"),
    ("Tel 802 555 0147", "802 555 0147"),
    ("UK office 020 7946 0958.", "020 7946 0958"),
    ("mobile 07700 900123", "07700 900123"),
    ("0161 496 0000 is the switchboard", "0161 496 0000"),
    ("+44 (0)20 7946 0958 too", "+44 (0)20 7946 0958"),
    ("ring 01onal".replace("onal", "632 960123"), "01632 960123"),
])
def test_phone_en(text, value):
    assert ("PHONE", value) in found(text)


@pytest.mark.parametrize("text", [
    "ref 2024-10-18 and order 8025550181 is not a phone",    # bare digits without a label
    "amount 1234567890",
    "version 415.555",
    "the year 2024 and 1999",
    "ticket 115-555-0134",   # area code cannot start with 1
])
def test_phone_en_guards(text):
    assert all(k != "PHONE" for k, _ in found(text))


def test_ssn_validators():
    assert det.ssn_valid("123-45-6789") and det.ssn_valid("123456789")
    for bad in ("000-12-3456", "666-12-3456", "912-12-3456", "123-00-6789", "123-45-0000", "12345678"):
        assert not det.ssn_valid(bad), bad
    assert det.itin_valid("912-70-1234") and det.itin_valid("999-88-1234")
    assert not det.itin_valid("912-45-1234") and not det.itin_valid("123-70-1234")


@pytest.mark.parametrize("text,kind,value", [
    ("SSN: 123-45-6789", "NIR", "123-45-6789"),
    ("ssn 123 45 6789", "NIR", "123 45 6789"),
    ("Social Security number 123456789", "NIR", "123456789"),
    ("ITIN 912-70-1234", "ID_CODE", "912-70-1234"),
    ("taxpayer id 912701234", "ID_CODE", "912701234"),
])
def test_ssn_and_itin(text, kind, value):
    assert (kind, value) in found(text)


@pytest.mark.parametrize("text", [
    "bad 000-12-3456 and 666-12-3456 and 987-00-1234 and 987-65-0000",
    "order 123456789 without a label",
    "date 2024-10-18",
])
def test_ssn_guards(text):
    assert all(k not in ("NIR",) for k, _ in found(text))


def test_nino():
    assert det.nino_valid("AB 12 34 56 C") and det.nino_valid("AB123456C")
    for bad in ("QQ 12 34 56 C", "BG 12 34 56 A", "AB 12 34 56 E", "AO 12 34 56 A", "AB 12 34 5 C"):
        assert not det.nino_valid(bad), bad
    assert ("ID_CODE", "AB 12 34 56 C") in found("NI: AB 12 34 56 C")
    assert ("ID_CODE", "AB123456C") in found("National Insurance no AB123456C")
    assert ("ID_CODE", "AB123456C") not in found("part AB123456C ordered")   # compact form needs a label
    assert all(v != "QQ 12 34 56 C" for _, v in found("QQ 12 34 56 C"))


@pytest.mark.parametrize("text,value", [
    ("Ship to 742 Evergreen Terrace, Springfield, IL 62704.", "742 Evergreen Terrace, Springfield, IL 62704"),
    ("Office: 1600 Amphitheatre Parkway Mountain View, CA 94043.", "1600 Amphitheatre Parkway Mountain View, CA 94043"),
    ("Mail: 1 Northvale Way, Suite 400\nBoston, MA 02110\nUSA", "1 Northvale Way, Suite 400\nBoston, MA 02110"),
    ("350 5th Avenue, New York, NY 10118", "350 5th Avenue, New York, NY 10118"),
    ("12 W 42nd Street, Apt 3B, New York, New York 10036", "12 W 42nd Street, Apt 3B, New York, New York 10036"),
    ("PO Box 1234, Austin, TX 78701", "PO Box 1234, Austin, TX 78701"),
    ("P.O. Box 99", "P.O. Box 99"),
    ("Springfield, IL 62704", "Springfield, IL 62704"),
    ("She lives at 2023 Spring Road, Dallas, TX 75201.", "2023 Spring Road, Dallas, TX 75201"),
    ("4400 Kestrel Blvd NE, Albuquerque, NM 87110-1234", "4400 Kestrel Blvd NE, Albuquerque, NM 87110-1234"),
    ("9 Elm St.\nIL 62704", "9 Elm St.\nIL 62704"),
    ("221B Baker Street, London NW1 6XE", "221B Baker Street, London NW1 6XE"),
])
def test_address_en(text, value):
    assert ("ADDRESS", value) in found(text)


@pytest.mark.parametrize("text", [
    "zip 62704 alone",
    "5 Street alone",
    "In 2023 Spring Road budgets rose",   # a year-like number without a tail or a label
    "the court filed 12 motions",
])
def test_address_en_guards(text):
    cands = [c for f in det.DETECTORS_EN for c in f(text)]
    assert all(c.kind != "ADDRESS" for c in cands)


def test_detectors_en_carry_lang_and_registry_helper():
    assert all(getattr(f, "langs", None) == ("en",) for f in det.DETECTORS_EN)
    text = "SSN 123-45-6789 at 742 Evergreen Terrace, Springfield, IL 62704, IBAN FR76 3000 6000 0112 3456 7890 189"
    plain = {(c.kind, c.detector) for c in det.detect_candidates(text, lang="fr")}
    withen = {(c.kind, c.detector) for c in det.detect_candidates_en(text)}
    every = {(c.kind, c.detector) for c in det.detect_candidates(text)}
    assert ("NIR", "ssn") in withen and ("NIR", "ssn") in every and ("NIR", "ssn") not in plain
    assert ("IBAN", "iban") in plain and ("IBAN", "iban") in withen


def test_structured_norm_of_en_kinds():
    assert det.structured_norm("NIR", "123-45-6789") == "123456789"
    assert det.structured_norm("PHONE", "(415) 555-0134") == "4155550134"
    assert det.structured_norm("ADDRESS", "742 Evergreen Terrace,\nSpringfield, IL 62704") == \
        "742 evergreen terrace springfield il 62704"


# --- no benchmark surface, no network, speed -------------------------------------------------------------------


def test_lexicon_files_hold_no_real_values():
    # the English lexicons are word lists: no e-mail, phone, IBAN or SSN shaped entry slipped in
    for name in lc.EN_FILES:
        for sec, entries in lc.read_sections(name).items():
            for e in entries:
                assert "@" not in e and not re.search(r"\d{3}[\- ]\d{2}[\- ]\d{4}", e), (name, sec, e)


def test_speed_rules_en():
    text = ("Hi Priya, Marcus Lee at Northvale Analytics Inc. says Mr. Thurlowe's report is late. "
            "Please call (415) 555-0134 or write to 742 Evergreen Terrace, Springfield, IL 62704. "
            "Brightwater Capital Partners and Baker & McKenzie advised Johnson & Johnson.\nBest,\nJennifer\n") * 400
    lc.detect_names_en("warm up")
    t0 = time.perf_counter()
    lc.detect_names_en(text)
    det.detect_candidates_en(text)
    f = fold(text)
    lc.protected_intervals_en(text, f, tokens(f.text))
    dt = time.perf_counter() - t0
    assert len(text) / dt > 20_000, f"{len(text) / dt:.0f} chars/s"
