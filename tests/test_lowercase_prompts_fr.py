"""v0.4.1, round 2: prompts that lawyers type in lower case, beyond a civility and a first name.

E: a postal address typed in lower case ("12 rue des glycines, 69007 lyon") has the mask of the same address with
capitals. The guards: a street type that is also an ordinary word needs a home
cue or a postcode ("3 cours de droit", "1 place de parking" stay readable), the name stops at the verb of the
sentence, and text with capitals keeps its 0.4.0 reading. ``RAGBASE_SHIELD_LOWERCASE_NAMES=0`` turns the rule off.
Invented data only: every name, street and sentence below is made up for these tests."""
from __future__ import annotations

import pytest

from ragbase_shield.engine import Masker, MemoryStore

SWITCH = "RAGBASE_SHIELD_LOWERCASE_NAMES"


def _masker() -> Masker:
    return Masker(MemoryStore(), use_ner=False)


def _spans(text: str, kind: str, masker: Masker | None = None) -> list[str]:
    r = (masker or _masker()).mask(text)
    return [s.value for s in r.spans if s.kind == kind]


@pytest.fixture(autouse=True)
def _default_switch(monkeypatch):
    monkeypatch.delenv(SWITCH, raising=False)


# ---------------------------------------------------------------------------
# E: an address typed in lower case
# ---------------------------------------------------------------------------

# (text, the addresses masked, the masked text)
ADDRESS_LINES = [
    ("m. nelba samir, domicilié 12 rue des glycines, 69007 lyon, conteste son licenciement",
     ["12 rue des glycines, 69007 lyon"], "m. PERSONNE_A, domicilié ADRESSE_1, conteste son licenciement"),
    ("il habite au 5 avenue victor hugo 75016 paris",
     ["5 avenue victor hugo 75016 paris"], "il habite au ADRESSE_1"),
    ("monsieur kervadec yanis habite 12 rue de la paix 75002 paris",
     ["12 rue de la paix 75002 paris"], "monsieur PERSONNE_A habite ADRESSE_1"),
]

# (text, the addresses masked)
ADDRESS = [
    ("elle habite 14 impasse du moulin à nantes", ["14 impasse du moulin"]),
    ("mon client demeure 3 bis avenue jean jaurès, 31000 toulouse", ["3 bis avenue jean jaurès, 31000 toulouse"]),
    ("siège social : 27 boulevard de la république 13001 marseille",
     ["27 boulevard de la république 13001 marseille"]),
    ("il réside 9 quai des brumes 44000 nantes depuis 2019", ["9 quai des brumes 44000 nantes"]),
    ("domicilié 6 rue saint honoré 75001 paris", ["6 rue saint honoré 75001 paris"]),
    ("elle habite 2 allée des cerisiers, 33000 bordeaux, et travaille à pessac",
     ["2 allée des cerisiers, 33000 bordeaux"]),
    ("au 15 rue du général leclerc 94000 créteil", ["15 rue du général leclerc 94000 créteil"]),
    ("j'habite 21 rue de la grande armée 75017 paris", ["21 rue de la grande armée 75017 paris"]),
    ("il habite 12 rue notre dame des champs 75006 paris", ["12 rue notre dame des champs 75006 paris"]),
    ("domicilié 12 rue du 8 mai 1945, 92100 boulogne billancourt, il conteste",
     ["12 rue du 8 mai 1945, 92100 boulogne billancourt"]),
    ("il habite 7 rue des lilas 17000 la rochelle", ["7 rue des lilas 17000 la rochelle"]),
    ("il demeure 8 rue du château 78100 saint germain en laye", ["8 rue du château 78100 saint germain en laye"]),
    ("siège : 4 boulevard des belges 76600 le havre cedex 2", ["4 boulevard des belges 76600 le havre cedex 2"]),
    ("elle demeure 30 cours lafayette 69003 lyon 3e", ["30 cours lafayette 69003 lyon 3e"]),
    ("domiciliée 8 allée des cerisiers bâtiment c 69100 villeurbanne",
     ["8 allée des cerisiers bâtiment c 69100 villeurbanne"]),
    ("12 rue des lilas porte 4, 69003 lyon", ["12 rue des lilas porte 4, 69003 lyon"]),
    # a street type that is also an ordinary word: a home cue before the number, or a postcode after the name
    ("j'habite 3 place carnot 13100 aix en provence", ["3 place carnot 13100 aix en provence"]),
    ("elle demeure 7 chemin des vignes à lyon", ["7 chemin des vignes"]),
    ("adresse : 4 chemin des vignes 84000 avignon", ["4 chemin des vignes 84000 avignon"]),
    ("il habite 18 route de lyon, 38200 vienne", ["18 route de lyon, 38200 vienne"]),
    ("domicilié 5 place bellecour, 69002 lyon", ["5 place bellecour, 69002 lyon"]),
    # the name stops at the verb of the sentence, at a function word, at a complement
    ("il habite 12 rue des glycines conteste son licenciement", ["12 rue des glycines"]),
    ("il habite 12 rue des lilas depuis 2010 et travaille", ["12 rue des lilas"]),
    ("il habite 12 rue des lilas et il conteste son licenciement", ["12 rue des lilas"]),
    ("il habite 12 rue des lilas appartement 4 et conteste son licenciement", ["12 rue des lilas appartement 4"]),
    ("il habite 12 rue de la vieille forge", ["12 rue de la vieille forge"]),
    # a capital on the street name or on the town only
]

# No address: a number and a street type that is an ordinary word here, a street with no number, an amount.
NO_ADDRESS = [
    "il a vu 3 cours de droit civil cette année",
    "il loue 1 place de parking au sous-sol",
    "le salarié a suivi 2 cours du soir",
    "la clause 4 voie de recours est claire",
    "il a pris 2 route nationale",
    "elle occupe 1 villa de vacances",
    "il y a 3 passage de relais",
    "article 5 voie d'exécution",
    "la rue est barrée depuis lundi",
    "le dossier est dans une impasse totale",
    "il réclame 12 000 euros et 3 mois de préavis",
    "il doit 15000 euros à son employeur",
    "le quai est fermé et la rue aussi",
    "il conteste son licenciement du 3 mars 2025",
]

# Capitalised addresses and sentences: the same output with the rule on and off.
ADDRESS_CAPITALISED = [
    "M. Samir, domicilié 12 rue des Glycines, 69007 Lyon, conteste son licenciement.",
    "Il habite au 5 avenue Victor Hugo 75016 Paris.",
    "Madame Vellin demeure 3 bis avenue Jean Jaurès, 31000 Toulouse.",
    "Le siège social est situé 27 boulevard de la République, 13001 Marseille.",
    "Elle habite 14 impasse du Moulin à Nantes depuis 2019.",
    "Domicilié 5 place Bellecour, 69002 Lyon, il conteste.",
    "Il habite 12 rue des Lilas et conteste son licenciement.",
    "Le 12 rue des Lilas appartient à la SCI Talvez.",
    "Il habite 8 rue du Château, 78100 Saint-Germain-en-Laye.",
    "Siège : 4 boulevard des Belges, 76600 Le Havre Cedex 2.",
    "Il suit 3 cours de droit civil et loue 1 place de parking.",
    "Le conseil de prud'hommes de Lyon a jugé le 3 mars 2025.",
]


@pytest.mark.parametrize("text,addresses,masked", ADDRESS_LINES)
def test_address_lines_of_the_report(text, addresses, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert [s.value for s in r.spans if s.kind == "ADDRESS"] == addresses
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text,addresses", [(t, a) for t, a, _ in ADDRESS_LINES] + ADDRESS)
def test_a_lower_case_address_is_masked(text, addresses):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind == "ADDRESS"] == addresses
    for a in addresses:
        assert a not in r.text
    assert m.unmask(r.text) == text  # restore gives back the text as typed


@pytest.mark.parametrize("text", NO_ADDRESS)
def test_ordinary_words_are_no_address(text):
    r = _masker().mask(text)
    assert [s.value for s in r.spans if s.kind == "ADDRESS"] == []
    assert r.text == text


def test_there_are_enough_address_cases():
    assert len(ADDRESS) >= 25 and len(NO_ADDRESS) >= 10
    assert len({t for t, _ in ADDRESS}) == len(ADDRESS)


@pytest.mark.parametrize("text", ADDRESS_CAPITALISED)
def test_capitalised_addresses_are_the_same_with_the_rule_on_and_off(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text
    assert [(s.start, s.end, s.kind) for s in on.spans] == [(s.start, s.end, s.kind) for s in off.spans]


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_the_switch_turns_the_address_rule_off(monkeypatch, value):
    monkeypatch.setenv(SWITCH, value)
    for text, _addresses in [(t, a) for t, a, _ in ADDRESS_LINES] + ADDRESS:
        got = _spans(text, "ADDRESS")
        # rules off: the 0.4.0 behaviour (a capitalised part may keep its mask)
        assert all(any(c.isupper() for c in a) for a in got), (text, got)


def test_one_address_one_code_across_letter_cases():
    m = _masker()
    a = m.mask("Il habite 12 rue des Glycines, 69007 Lyon.").text
    b = m.mask("il habite 12 rue des glycines, 69007 lyon").text
    assert a == "Il habite ADRESSE_1." and b == "il habite ADRESSE_1"


def test_the_address_and_the_name_of_one_line():
    m = _masker()
    r = m.mask("mme claire dufresne habite 9 quai des brumes 44000 nantes et conteste son licenciement.")
    assert r.text == "mme PERSONNE_A habite ADRESSE_1 et conteste son licenciement."


# ---------------------------------------------------------------------------
# K1: a civility typed in lower case and a name with its capitals
# ---------------------------------------------------------------------------

# "m." and "mme" in lower case are a title as "M." and "Mme" are: "m. Kervadec conteste".
# (text, the names masked)
LOWER_CIVILITY = [
    ("m. Kervadec conteste son licenciement", ["Kervadec"]),
    ("mme Pradimont a signé le bail", ["Pradimont"]),
    ("m. TALVEZ conteste son licenciement", ["TALVEZ"]),
    ("mme PRADIMONT conteste son licenciement", ["PRADIMONT"]),
    ("mlle Kerdalis demande des dommages", ["Kerdalis"]),
    ("je représente m. Kelmadi", ["Kelmadi"]),
    ("bonjour, m. Talvenec a reçu un avertissement", ["Talvenec"]),
    ("m. Le Bihannec conteste", ["Le Bihannec"]),
    ("mme De Roquevert a signé", ["De Roquevert"]),
    ("m. Yanis Kervadec a signé le bail", ["Yanis Kervadec"]),
    ("mm. Vellin et Talvez contestent", ["Vellin", "Talvez"]),
    ("mme Pradimont et m. Talvez divorcent", ["Pradimont", "Talvez"]),
    ("voir m. Kervadec, mme Talvez et mlle Vellin", ["Kervadec", "Talvez", "Vellin"]),
]

# No name: a unit after a number, an office, the pronoun "me", a noun after the civility.
LOWER_CIVILITY_NO_NAME = [
    "le mur mesure 12 m. Il est trop haut",
    "la haie fait 3 m. Kervadec le sait",
    "m. le Président a ouvert l'audience",
    "mme la Juge a tranché",
    "il me dit que Paris est loin",
    "m. Demande de renvoi",
]


@pytest.mark.parametrize("text,names", LOWER_CIVILITY)
def test_a_lower_case_civility_and_a_capitalised_name(text, names):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind == "PERSON"] == names
    for name in names:
        assert name not in r.text
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text,names", LOWER_CIVILITY)
def test_a_lower_case_civility_reads_the_name_as_the_capitalised_civility_does(text, names):
    # "m. Kervadec" gives the spans of "M. Kervadec"
    caps = text
    for low, cap in (("mm. ", "MM. "), ("m. ", "M. "), ("mme ", "Mme "), ("mlle ", "Mlle ")):
        caps = caps.replace(low, cap)
    assert _spans(caps, "PERSON") == names


@pytest.mark.parametrize("text", LOWER_CIVILITY_NO_NAME)
def test_a_lower_case_civility_is_no_proof_of_a_name(text):
    assert _masker().mask(text).text == text


def test_a_known_person_after_a_lower_case_civility():
    m = _masker()
    first = m.mask("Monsieur Yanis Kervadec a signé le bail.")
    assert first.text == "Monsieur PERSONNE_A a signé le bail."
    assert m.mask("m. Kervadec conteste le congé").text == "m. PERSONNE_A conteste le congé"
    assert m.mask("m. kervadec conteste le congé").text == "m. PERSONNE_A conteste le congé"


@pytest.mark.parametrize("value", ["0", "off"])
def test_the_switch_turns_the_lower_case_civility_off(monkeypatch, value):
    monkeypatch.setenv(SWITCH, value)
    for text, _names in LOWER_CIVILITY:
        if "Yanis" not in text:  # 0.4.0 masks a first name and a surname with their capitals
            assert _spans(text, "PERSON") == [], text


# ---------------------------------------------------------------------------
# Precision: legal text and notes keep their reading
# ---------------------------------------------------------------------------

# The same output with the rules on and off. A civility is no proof of a name: after "à" the words that follow it
# are the object of the verb; "le" or "la" and a word after it is an office; "Me" before an infinitive is the
# pronoun; "le docteur" and "un professeur" are common nouns. A note word and a legal form are no company. A word
# in lower case that no list knows after a capitalised first name may be a job or an adverb.
ORDINARY_TEXT = [
    # an object after "à" and a civility with no name
    "Le tribunal a accordé à Madame la jouissance du logement.",
    "le bailleur a remis à monsieur le trousseau de clés.",
    "le juge a accordé à madame des délais de paiement.",
    "cela cause à monsieur du souci.",
    "on a reproché à madame de la négligence.",
    "L'acte attribue à Monsieur le mobilier du salon.",
    "le greffe a notifié à madame des écritures tardives.",
    "il a laissé à monsieur du temps pour répondre.",
    # an office after a civility and an article
    "monsieur le jex a statué hier.",
    "madame la proc a requis six mois.",
    "m. le major a pris la plainte.",
    "mme la jaf a entendu les enfants.",
    "madame la duchesse a vendu le domaine.",
    "m. le bihannec conteste son avertissement.",
    # the pronoun "me" before an infinitive, a fixed phrase
    "Me transcrire ce jugement en anglais.",
    "Me relire ce contrat avant midi.",
    "Me traduire la clause 4.",
    "Me dire si le délai est expiré.",
    "le mouvement Me too a dix ans.",
    # "docteur" and "professeur" as common nouns, short words after a civility
    "Le docteur référent a rendu son rapport.",
    "le professeur émérite a signé la consultation.",
    "un docteur urgentiste a examiné la victime.",
    "Condamne Monsieur et Madame in solidum à payer la somme.",
    "bonjour madame pb sur le bail svp",
    "bonjour monsieur rdv demain à 9h",
    # a note word and a legal form
    "compta sci à refaire avant lundi.",
    "récap sarl à envoyer demain.",
    "docs sasu reçus ce matin.",
    "immat eurl en attente.",
    "ago sarl prévue le 3 mai.",
    "pv sas signé hier.",
    # things, days
    "une bouteille d'huile d'olive extra vierge.",
    "rdv cliente sam aprem.",
    # a capitalised first name and a word in lower case that no list knows
    "M. Benoit velkor conteste son avertissement.",
    "Mme Martin zorvaine convoquée ne s'est pas présentée.",
    "M. Xavier brivanec a supprimé le site.",
]

# What still holds a name next to these guards. (text, the names masked)
SUPPORTED_NAMES = [
    ("madame de la tour conteste le congé", ["de la tour"]),
    ("mme de la tour a signé le bail", ["de la tour"]),
    ("mme de la tour ne conteste pas le congé", ["de la tour"]),
    ("je représente mme d'arvignac dans ce dossier", ["d'arvignac"]),
    ("contre monsieur du roquevert", ["du roquevert"]),
    ("le docteur karim kervadec a examiné mon client", ["karim kervadec"]),
    ("Me kervadec plaide demain", ["kervadec"]),
    ("m. roy conteste son licenciement", ["roy"]),
    ("kerdalis sarl conteste la créance.", ["kerdalis"]),
    ("kerdalis sarl et talvez sas sont en litige", ["kerdalis", "talvez"]),
    ("kerdalis sarl licencie trois salariés", ["kerdalis"]),
]


@pytest.mark.parametrize("text", ORDINARY_TEXT)
def test_ordinary_text_is_the_same_with_the_rules_on_and_off(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text
    assert [(s.start, s.end, s.kind) for s in on.spans] == [(s.start, s.end, s.kind) for s in off.spans]


@pytest.mark.parametrize("text,names", SUPPORTED_NAMES)
def test_names_with_support_are_masked(text, names):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind in ("PERSON", "ORG")] == names
    assert m.unmask(r.text) == text


def test_there_are_enough_precision_cases():
    assert len(ORDINARY_TEXT) >= 35 and len(set(ORDINARY_TEXT)) == len(ORDINARY_TEXT)


# ---------------------------------------------------------------------------
# K10, K7: a legal form closes a company name; it is never a surname
# ---------------------------------------------------------------------------

# A company named with a first name, and a company after a noun that is no company cue. The legal form stays
# readable, the nouns before the name too. (text, the company names masked, the masked text)
COMPANY_WITH_FORM = [
    ("la société julien sarl refuse de payer", ["julien"], "la société SOCIETE_A sarl refuse de payer"),
    ("le garage julien sarl a fermé", ["julien"], "le garage SOCIETE_A sarl a fermé"),
    ("les établissements bernard sas ont licencié trois salariés", ["bernard"],
     "les établissements SOCIETE_A sas ont licencié trois salariés"),
    ("contre gabin sas", ["gabin"], "contre SOCIETE_A sas"),
    ("le devis de vincent sas", ["vincent"], "le devis de SOCIETE_A sas"),
    ("ma cliente a travaillé chez damien sarl", ["damien"], "ma cliente a travaillé chez SOCIETE_A sarl"),
    ("la société jean kervadec sas a fermé", ["jean kervadec"], "la société SOCIETE_A sas a fermé"),
    ("l'agence zorvane sarl a été condamnée", ["zorvane"], "l'agence SOCIETE_A sarl a été condamnée"),
    ("mon employeur talvenec eurl ne me paie plus", ["talvenec"], "mon employeur SOCIETE_A eurl ne me paie plus"),
    ("litige avec transports zelmadec sarl", ["zelmadec"], "litige avec transports SOCIETE_A sarl"),
    ("la boulangerie marie sarl a fermé", ["marie"], "la boulangerie SOCIETE_A sarl a fermé"),
    ("le dossier kervadec sarl avance", ["kervadec"], "le dossier SOCIETE_A sarl avance"),
    ("la clinique talvez sas a licencié une infirmière", ["talvez"],
     "la clinique SOCIETE_A sas a licencié une infirmière"),
    ("boulangerie patisserie talvez sarl ne paie pas les heures", ["talvez"],
     "boulangerie patisserie SOCIETE_A sarl ne paie pas les heures"),
]

# No company: a legal form with no name before it, an adjective, a common word, a form that is also a word.
NO_COMPANY = [
    "le contrat de travail sarl",
    "la petite sarl a fermé",
    "le grand sas est fermé",
    "il est gérant de sarl depuis 2019",
    "les statuts de la sarl sont clairs",
    "le fonds de commerce sarl",
    "le bail commercial sarl",
    "un prêt personnel sarl",
    "la sarl familiale a fermé",
    "julien sarl à relancer",
    "le garage petit sarl a fermé",
]


@pytest.mark.parametrize("text,names,masked", COMPANY_WITH_FORM)
def test_a_legal_form_closes_a_company_name(text, names, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert [s.value for s in r.spans if s.kind == "ORG"] == names
    assert [s.value for s in r.spans if s.kind == "PERSON"] == []  # a legal form is never a surname
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_COMPANY)
def test_a_legal_form_alone_is_no_company(text):
    assert _masker().mask(text).text == text


def test_a_person_before_a_legal_form_word_keeps_the_person_code():
    r = _masker().mask("mon client julien talvez dirige une sarl")
    assert r.text == "mon client PERSONNE_A dirige une sarl"


def test_one_company_one_code_with_a_first_name_as_its_name():
    m = _masker()
    assert m.mask("Julien SARL a écrit hier.").text == "SOCIETE_A SARL a écrit hier."
    assert m.mask("le garage julien sarl refuse de rembourser").text == "le garage SOCIETE_A sarl refuse de rembourser"
    assert m.mask("julien sarl a répondu").text == "SOCIETE_A sarl a répondu"
    assert [(e.code, e.kind) for e in m.store.all()] == [("SOCIETE_A", "ORG")]


def test_restore_adds_no_legal_form():
    m = _masker()
    first = m.mask("le garage julien sarl refuse de rembourser")
    assert m.unmask(first.text) == "le garage julien sarl refuse de rembourser"
    later = m.mask("la société Julien a répondu")
    assert later.text == "la société SOCIETE_A a répondu"
    assert m.unmask(later.text) == "la société julien a répondu"  # one code, one stored spelling


# ---------------------------------------------------------------------------
# Names with no civility: a surname that is a common word, the surname first, a first name after a person noun
# ---------------------------------------------------------------------------

# A first name of the lexicon, then a surname that is also a common word, where a name stands: at the start of
# the clause or after a person noun, a preposition or a verb, and before a verb, "et" or the end of the clause.
COMMON_WORD_SURNAME = [
    ("mon client paul petit a été licencié", ["paul petit"]),
    ("paul mercier conteste son licenciement", ["paul mercier"]),
    ("hugo leroy et clara leroy se séparent", ["hugo leroy", "clara leroy"]),
    ("ma cliente emma blanc et son mari lucas blanc divorcent", ["emma blanc", "lucas blanc"]),
    ("le bailleur de mon client est sylvain marchand", ["sylvain marchand"]),
    ("je défends lucas meunier", ["lucas meunier"]),
    ("le dossier oppose paul chevalier à lucas berger", ["paul chevalier", "lucas berger"]),
    ("je soussigné paul mercier, né le 3 mai 1980 à nantes, atteste avoir vu les faits", ["paul mercier"]),
]

# The surname first: a word that no list knows, then a first name of the lexicon.
SURNAME_FIRST = [
    ("zadou mila conteste son licenciement", ["zadou mila"]),
    ("mon client s'appelle nelba samir", ["nelba samir"]),
    ("Mon client s'appelle zadou mila.", ["zadou mila"]),
    ("nelba samir et zadou mila sont associés", ["nelba samir", "zadou mila"]),
    ("je défends kervadec yanis contre son employeur", ["kervadec yanis"]),
    ("le bail est au nom de talvez nadia", ["talvez nadia"]),
]

# A noun that names a person, then one first name of the lexicon.
LONE_FIRST_NAME = [
    ("mon client kevin a été licencié hier", ["kevin"]),
    ("ma fille emma", ["emma"]),
    ("notre salarié lucas et son collègue yanis contestent", ["lucas", "yanis"]),
    ("mon avocat martin a plaidé", ["martin"]),
    ("les enfants emma et lucas vivent chez madame.", ["emma", "lucas"]),
    ("mes clients paul et virginie sont mariés", ["paul", "virginie"]),
    ("ses fils adam et noé ont hérité", ["adam", "noé"]),
]

# No name: the words after the first name read as ordinary words, or nothing holds a name.
NO_NAME_WITHOUT_CIVILITY = [
    "lucas roux de colère a quitté la salle",
    "emma petit à petit a repris le travail",
    "paul blanc de peur n'a rien dit",
    "paul seul conteste la décision",
    "paul aussi conteste",
    "paul conteste",
    "paul et emma contestent",
    "bonjour paul",
    "merci paul pour le dossier",
    "voir lucas demain",
    "appeler julie avant midi",
    "whatsapp emma hier",
    "point dossier sam aprem, 15h",
    "mon client conteste",
    "mon client principal conteste",
    "le salarié protégé conteste",
    "ma cliente rose de colère a quitté la salle",
    "les époux kervadec contestent",
    "les salariés protégés contestent",
    "les témoins clés ont disparu",
    "les parties paul et marie",
]


@pytest.mark.parametrize("text,names", COMMON_WORD_SURNAME + SURNAME_FIRST + LONE_FIRST_NAME)
def test_a_name_with_no_civility_is_masked(text, names):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind == "PERSON"] == names
    for name in names:
        assert name not in r.text
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_NAME_WITHOUT_CIVILITY)
def test_no_name_without_what_holds_one(text):
    assert _masker().mask(text).text == text


def test_surname_first_then_the_usual_order_keep_one_code():
    m = _masker()
    assert m.mask("zadou mila conteste son licenciement").text == "PERSONNE_A conteste son licenciement"
    assert m.mask("m. zadou a écrit hier").text == "m. PERSONNE_A a écrit hier"
    assert [e.code for e in m.store.all() if e.kind == "PERSON"] == ["PERSONNE_A"]


# ---------------------------------------------------------------------------
# After a civility: a surname with a French particle after a first name, a surname that is an ordinary word
# ---------------------------------------------------------------------------

# (text, the names masked)
PARTICLE_AFTER_FIRST_NAME = [
    ("mme sophie de roquevert demande le divorce", ["sophie de roquevert"]),
    ("m. paul le bihannec a été licencié", ["paul le bihannec"]),
    ("mme nadia de la roche a hérité d'un appartement", ["nadia de la roche"]),
    ("mme sophie du kervadec a vendu la maison", ["sophie du kervadec"]),
    ("mme claire d'arvignac a signé", ["claire d'arvignac"]),
    ("m. pierre de roquevert conteste", ["pierre de roquevert"]),
    ("m. yanis le bihannec et mme nadia de roquevert divorcent", ["yanis le bihannec", "nadia de roquevert"]),
]

ORDINARY_WORD_SURNAME = [
    ("m. paul marques a signé le bail", ["paul marques"]),
    ("m. karim carre a été licencié", ["karim carre"]),
    ("mme julie cousin conteste", ["julie cousin"]),
    ("m. roi conteste son licenciement", ["roi"]),
]

# The words after the first name are no surname: only the first name is masked. (text, the names masked)
NOT_A_SURNAME = [
    ("m. paul de retour conteste", ["paul"]),
    ("m. paul du coup conteste", ["paul"]),
    ("mme julie de la part de son employeur a reçu une lettre", ["julie"]),
    ("m. paul de garde a signé", ["paul"]),
    ("m. paul le premier a signé", ["paul"]),
    ("mme sophie des fois conteste", ["sophie"]),
    ("mme julie seule assume la charge", ["julie"]),
    ("m. paul ensuite a signé", ["paul"]),
    ("m. paul absent a été remplacé", ["paul"]),
    ("mme sophie demande le divorce", ["sophie"]),
    ("m. paul conteste et refuse", ["paul"]),
    ("madame gérante conteste", []),
    ("monsieur chauffeur routier conteste", []),
    ("madame infirmière, monsieur ouvrier", []),
    ("voir madame pb", []),
    ("bien que monsieur ait refusé de signer", []),
]


@pytest.mark.parametrize("text,names", PARTICLE_AFTER_FIRST_NAME + ORDINARY_WORD_SURNAME)
def test_surnames_after_a_civility(text, names):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind == "PERSON"] == names
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text,names", NOT_A_SURNAME)
def test_ordinary_words_after_a_first_name_are_no_surname(text, names):
    r = _masker().mask(text)
    assert [s.value for s in r.spans if s.kind == "PERSON"] == names


# ---------------------------------------------------------------------------
# Form fields, a legal form before the name, a company cue with no legal form
# ---------------------------------------------------------------------------

# (text, the masked text)
FIELDS = [
    ("nom : zadou, prénom : mila", "nom : PERSONNE_A, prénom : PERSONNE_B"),
    ("nom : zadou\nprénom : mila\nné le 3 mars 1980", "nom : PERSONNE_A\nprénom : PERSONNE_B\nné le NAISSANCE_1"),
    ("prénoms : mila nadia", "prénoms : PERSONNE_A"),
    ("client : kervadec jean, né le 3 mars 1980 à lyon", "client : PERSONNE_A, né le NAISSANCE_1 à lyon"),
    ("client : jean kervadec", "client : PERSONNE_A"),
]

NO_FIELD_VALUE = [
    "nom : à compléter",
    "nom : zadou",
    "nom de naissance : kervadec",
    "nom : inconnu",
    "prénom : non renseigné",
    "nom : voir ci-dessus",
    "nom du fichier : contrat",
    "le nom : zadou",
]

# (text, the masked text)
FORM_BEFORE_NAME = [
    ("samir nelba c/ sas brivanor", "PERSONNE_A c/ sas SOCIETE_A"),
    ("contre: sarl les jardins de provence, représentée par son gérant pierre durand",
     "contre: sarl SOCIETE_A, représentée par son gérant PERSONNE_A"),
    ("nelba samir et zadou mila sont associés de la sci les tilleuls",
     "PERSONNE_A et PERSONNE_B sont associés de la sci SOCIETE_A"),
    ("la sci les tilleuls a acheté l'immeuble", "la sci SOCIETE_A a acheté l'immeuble"),
    ("c/ sas brivanor", "c/ sas SOCIETE_A"),
    ("le cabinet kervadec & associés représente la partie adverse", "le cabinet SOCIETE_A représente la partie adverse"),
    ("le cabinet kervadec talvez et associés plaide", "le cabinet SOCIETE_A plaide"),
    ("la société julien a licencié mon client", "la société SOCIETE_A a licencié mon client"),
]

NO_COMPANY_NAME = [
    "la sarl les a licenciés",
    "la sci le sait",
    "il a géré la sas les mois suivants",
    "la sarl la plus rentable",
    "la société civile a été dissoute",
    "la société mère a licencié",
    "la société leader a annoncé",
    "le groupe électrogène est en panne",
    "la société marie a fermé",
    "le sas est fermé",
]


@pytest.mark.parametrize("text,masked", FIELDS + FORM_BEFORE_NAME)
def test_fields_and_companies_in_lower_case(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_FIELD_VALUE + NO_COMPANY_NAME)
def test_no_field_value_and_no_company_name(text):
    assert _masker().mask(text).text == text


def test_capitalised_fields_keep_their_reading(monkeypatch):
    for text in ("Nom : Zadou, Prénom : Mila", "Nom : Zadou\nPrénom : Mila", "Client : Kervadec Jean, né le 3 mars 1980"):
        on = _masker().mask(text).text
        monkeypatch.setenv(SWITCH, "0")
        off = _masker().mask(text).text
        monkeypatch.delenv(SWITCH)
        assert on == off


# ---------------------------------------------------------------------------
# Captions, long names, spellings of civilities and of legal forms
# ---------------------------------------------------------------------------

# (text, the masked text)
MORE_SHAPES = [
    # a case caption with bare surnames
    ("kervadec c/ talvez", "PERSONNE_A c/ PERSONNE_B"),
    ("affaire kervadec c/ talvez", "affaire PERSONNE_A c/ PERSONNE_B"),
    ("dossier martin c/ kervadec, audience le 3 mars", "dossier PERSONNE_A c/ PERSONNE_B, audience le 3 mars"),
    ("dossier martin contre kervadec", "dossier PERSONNE_A contre PERSONNE_B"),
    ("kervadec c/ talvez et brivanor sarl", "PERSONNE_A c/ PERSONNE_B et SOCIETE_A sarl"),
    ("dossier m. samir / kerdalis sas", "dossier m. PERSONNE_A / SOCIETE_A sas"),
    ("contre : kerdalis sas", "contre : SOCIETE_A sas"),
    ("défendeur : brivanor sarl", "défendeur : SOCIETE_A sarl"),
    # names of four or five words, hyphenated initials, a name particle in a compound
    ("madame nelba thi zadou demande un titre de séjour", "madame PERSONNE_A demande un titre de séjour"),
    ("mme maria del carmen kervadec talvez conteste", "mme PERSONNE_A conteste"),
    ("m. jose antonio talvenec da costa a été blessé", "m. PERSONNE_A a été blessé"),
    ("m. j-p kervadec a été mis à pied", "m. PERSONNE_A a été mis à pied"),
    ("mme ben-youssef refuse la sanction", "mme PERSONNE_A refuse la sanction"),
    ("mme léa du bois a signé", "mme PERSONNE_A a signé"),
    # spellings of a civility typed in lower case
    ("melle vellin demande des dommages", "melle PERSONNE_A demande des dommages"),
    ("mdme kervadec a signé", "mdme PERSONNE_A a signé"),
    ("mrs vellin a signé", "mrs PERSONNE_A a signé"),
    # a legal form in full words, a digit and a join word in a company name, a surname-like word after a noun
    ("la société par actions simplifiée kerdalis", "la société par actions simplifiée SOCIETE_A"),
    ("la société à responsabilité limitée zelmadec a fermé", "la société à responsabilité limitée SOCIETE_A a fermé"),
    ("la société civile immobilière zorvane", "la société civile immobilière SOCIETE_A"),
    ("la société k2 conseil sas a rompu le contrat", "la société SOCIETE_A sas a rompu le contrat"),
    ("la société kerdalis et compagnie sarl a fermé", "la société SOCIETE_A sarl a fermé"),
    ("la société kerdalis & co sas a fermé", "la société SOCIETE_A sas a fermé"),
    ("le garage lenoir sarl a fermé", "le garage SOCIETE_A sarl a fermé"),
]

NO_MORE_SHAPES = [
    "appel c/ jugement",
    "recours c/ décision du préfet",
    "tva c/ urssaf",
    "appel contre jugement",
    "plainte contre x",
    "contre toute attente",
    "kervadec contre son employeur",
    "note : zorbla sarl",
    "objet : sas zorblax",
    "la société civile immobilière a été dissoute",
    "la société anonyme de droit français",
    "la société civile professionnelle d'avocats",
    "il se mêle de tout",
    "le t2 sas",
    "Melle Vellin demande des dommages",
    "Kervadec c/ Talvez",
]

# A name of more than three words needs its verb or the end of the clause. (text, the names masked)
LONG_NAME_LIMITS = [
    ("mme sophie kervadec talvez hier matin", ["sophie kervadec talvez"]),
    ("m. paul kervadec talvez brivanor zorvane velkor conteste", ["paul kervadec talvez"]),
]


@pytest.mark.parametrize("text,masked", MORE_SHAPES)
def test_more_shapes_of_names_in_lower_case(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_MORE_SHAPES)
def test_these_shapes_hold_no_name(text):
    assert _masker().mask(text).text == text


@pytest.mark.parametrize("text,names", LONG_NAME_LIMITS)
def test_a_long_name_needs_its_verb(text, names):
    assert _spans(text, "PERSON") == names


# ---------------------------------------------------------------------------
# Short surnames, "aït" names, surnames that are also words, more legal forms
# ---------------------------------------------------------------------------

# (text, the masked text)
HELD_NAMES = [
    ("m. ait ouardi conteste son expulsion", "m. PERSONNE_A conteste son expulsion"),
    ("mme ait zelmoune, salariée depuis 2015, a été licenciée", "mme PERSONNE_A, salariée depuis 2015, a été licenciée"),
    ("m. paul ait ouardi a signé le bail", "m. PERSONNE_A a signé le bail"),
    ("karim ait ouardi conteste", "PERSONNE_A conteste"),
    ("m. paul ly a signé le bail", "m. PERSONNE_A a signé le bail"),
    ("paul ly conteste son licenciement", "PERSONNE_A conteste son licenciement"),
    ("mon client paul ly a été licencié", "mon client PERSONNE_A a été licencié"),
    ("paul porte conteste son licenciement", "PERSONNE_A conteste son licenciement"),
    ("mon client paul comte a été licencié", "mon client PERSONNE_A a été licencié"),
    ("paul de roquevert conteste", "PERSONNE_A conteste"),
    ("mon client paul de roquevert a été licencié", "mon client PERSONNE_A a été licencié"),
    ("m. said conteste la rupture", "m. PERSONNE_A conteste la rupture"),
    ("la société zorvane EARL a été assignée", "la société SOCIETE_A EARL a été assignée"),
    ("la société kerdalis earl a été assignée", "la société SOCIETE_A earl a été assignée"),
    ("mon client a un litige avec brivanor gaec", "mon client a un litige avec SOCIETE_A gaec"),
]

NOT_HELD = [
    "bien que monsieur ait refusé de signer",
    "que madame ait raison ou non",
    "paul porte plainte contre son voisin",
    "paul place son argent",
    "paul bois beaucoup",
    "julie place souvent ses économies",
    "paul de retour conteste",
    "le petit paul de roquevert",
]


@pytest.mark.parametrize("text,masked", HELD_NAMES)
def test_names_that_their_verb_or_their_place_holds(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NOT_HELD)
def test_words_that_nothing_holds_as_a_name(text):
    assert _masker().mask(text).text == text


@pytest.mark.parametrize("text", ["EARL Zorvane a été assignée.", "La société Zorvane EARL a été assignée.",
                                  "Le GAEC Brivanor a contesté la créance."])
def test_capitalised_companies_with_these_forms_keep_their_reading(monkeypatch, text):
    on = _masker().mask(text).text
    monkeypatch.setenv(SWITCH, "0")
    assert _masker().mask(text).text == on


# ---------------------------------------------------------------------------
# More ordinary text: notes, legal prose and chat lines with the words that the rules look at
# ---------------------------------------------------------------------------

MORE_ORDINARY_TEXT = [
    # a first name and ordinary words
    "lucas grand et fort a porté plainte",
    "julie court vers la sortie",
    "il faut que paul vienne demain",
    "paul noir de monde hier soir",
    "emma de son côté conteste",
    "lucas de retour a signé",
    "julie du coup refuse",
    "paul de garde ce soir",
    "paul et virginie sont mariés",
    "jean qui rit et jean qui pleure",
    "rose et bleu sont ses couleurs",
    "marie toi avec lui",
    "olivier et laurier sont des arbres",
    "merci julie pour ton retour",
    "cc paul pour info",
    "objet : relance paul",
    # an application or a channel and a first name
    "linkedin emma a répondu hier",
    "whatsapp paul a écrit ce matin",
    "teams lucas à 14h",
    "gmail emma ne répond pas",
    "attn paul",
    "feedback paul",
    "brief emma à 10h",
    "todo lucas",
    "staff paul a validé",
    # a person noun and an ordinary word
    "le salarié lambda conteste",
    "ma cliente victoire a obtenu gain de cause",
    "notre client prudence oblige a refusé",
    "le bailleur social a refusé le dossier",
    "le témoin clé a disparu",
    "la victime mineure a été entendue",
    "son employeur actuel refuse",
    "le client final a payé",
    "le client roi a toujours raison",
    "mon voisin porte plainte contre moi",
    "ma fille place son argent",
    "mon client marque une pause",
    "la salariée rose de honte a quitté la salle",
    "le salarié pierre angulaire du projet a démissionné",
    "mon client loup solitaire refuse",
    "ma cliente fleur bleue y croit",
    "mon client de bonne foi conteste",
    "mon client conteste son licenciement pour faute grave",
    "le salarié protégé a été licencié sans autorisation",
    "mon client principal a résilié le contrat",
    "la partie adverse conteste",
    "mon cousin germain a hérité de la maison",
    "ma cousine germaine conteste le partage",
    "mon frère jumeau a signé",
    "son fils aîné a hérité",
    "sa fille cadette conteste",
    "mon oncle paternel a légué",
    "le témoin oculaire a confirmé",
    "mon ami fidèle a témoigné",
    "un salarié modèle a été licencié",
    "mon voisin bruyant refuse",
    "mon client innocent a été relaxé",
    "ma cliente victime a porté plainte",
    # a company cue or a legal form and ordinary words
    "la banque centrale a baissé son taux directeur",
    "le syndicat sud a appelé à la grève",
    "l'entreprise lambda a répondu",
    "le groupe mère et filiales a consolidé",
    "l'association loi 1901 a été dissoute",
    "la société civile immobilière a vendu",
    "la société mère détient 80 % du capital de sa filiale",
    "la société leader du marché a annoncé",
    "le groupe électrogène est en panne",
    "la sarl a été créée en 2019",
    "la sci familiale détient l'immeuble",
    "une sas au capital de 1000 euros",
    "il a créé sa sasu en mars",
    "les statuts de la sas prévoient une clause",
    "la holding détient la sarl et la sci",
    "il est associé de la sci depuis 2015",
    # fields, captions
    "nom : néant",
    "nom : idem",
    "nom : sans objet",
    "prénom : à vérifier",
    "nom : voir kbis",
    "contre toute attente le juge a refusé",
    "appel contre le jugement du 3 mars",
    "le recours contre la décision est recevable",
    "pour ou contre la clause",
    # a civility and no name
    "bonjour maître, voici le dossier",
    "bonjour madame, monsieur,",
    "madame, monsieur, veuillez trouver ci-joint",
    "madame le maire a signé l'arrêté",
    "monsieur le préfet a refusé",
    "maître d'ouvrage et maître d'œuvre sont en litige",
    "le maître nageur a été licencié",
    "ce monsieur conteste la facture",
    "une dame âgée a chuté",
    "le docteur a refusé le certificat",
    "m. de son côté conteste",
    "mme de retour de congé a été licenciée",
    "monsieur de passage à paris a signé",
    "madame de nationalité française conteste",
    "monsieur du fait de son âge refuse",
    "mme des fois conteste",
    "m. le sait bien",
    "mme la voit souvent",
    "m. en a parlé",
    "mme y tient",
    "m. a signé hier",
    "mme est venue ce matin",
    "dr a prescrit un arrêt",
    "m. et mme contestent",
    "mm. les juges ont statué",
    "mr le directeur a répondu",
    "mlle est mineure",
    # numbers and street words
    "il habite en banlieue depuis 2010",
    "elle suit 3 cours du soir par semaine",
    "le 12 mai 2023 à paris",
]

# (text, the masked text)
SURNAME_THEN_TWO_GIVEN_NAMES = [
    ("nelba thi zadou a été licenciée", "PERSONNE_A a été licenciée"),
    ("mon client nelba thi zadou conteste", "mon client PERSONNE_A conteste"),
]


@pytest.mark.parametrize("text", MORE_ORDINARY_TEXT)
def test_more_ordinary_text_is_the_same_with_the_rules_on_and_off(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text


@pytest.mark.parametrize("text,masked", SURNAME_THEN_TWO_GIVEN_NAMES)
def test_a_surname_then_two_given_names(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


# ---------------------------------------------------------------------------
# E, more shapes: a street with no number, the town on the next line, a town with its postcode in brackets
# ---------------------------------------------------------------------------

# (text, the addresses masked)
MORE_ADDRESSES = [
    ("il habite rue des glycines à lyon", ["rue des glycines"]),
    ("elle demeure avenue victor hugo, 75016 paris", ["avenue victor hugo, 75016 paris"]),
    ("domicilié impasse du moulin 44000 nantes", ["impasse du moulin 44000 nantes"]),
    ("12 rue des glycines\n69007 lyon", ["12 rue des glycines\n69007 lyon"]),
    ("il habite au 12, rue des glycines à lyon (69007)", ["12, rue des glycines", "lyon (69007)"]),
    ("né à lyon le 3 mars 1980, demeurant à villeurbanne (69100)", ["villeurbanne (69100)"]),
    ("il vit à saint germain en laye (78100) depuis 2010", ["saint germain en laye (78100)"]),
]

NO_MORE_ADDRESSES = [
    "la rue des glycines est barrée",
    "dans la rue principale",
    "en pleine rue commerçante",
    "il habite rue",
    "une impasse totale",
    "le chiffre (75000) est faux",
    "voir article l. 1234 (69007)",
]


@pytest.mark.parametrize("text,addresses", MORE_ADDRESSES)
def test_more_address_shapes_in_lower_case(text, addresses):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind == "ADDRESS"] == addresses
    # an address on two lines is restored on one line, as with capitals
    assert m.unmask(r.text).split() == text.split()
    if not any("\n" in a for a in addresses):
        assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_MORE_ADDRESSES)
def test_these_lines_hold_no_address(text):
    assert _masker().mask(text).text == text


@pytest.mark.parametrize("text", ["Il habite rue des Glycines à Lyon.", "Demeurant à Villeurbanne (69100).",
                                  "12 rue des Glycines\n69007 Lyon", "La rue des Glycines est barrée."])
def test_capitalised_addresses_of_these_shapes_keep_their_reading(monkeypatch, text):
    on = _masker().mask(text).text
    monkeypatch.setenv(SWITCH, "0")
    assert _masker().mask(text).text == on


# A third batch: names of laws and cases, verbs after a person noun, fields and labels with no name, company words
# with no name, home words with no address.
ORDINARY_TEXT_3 = [
    "thomas court et saute",
    "lucas petit garçon de dix ans",
    "emma blanche de peur n'a rien dit",
    "paul content de lui a signé",
    "julie fort contente a remercié",
    "louis vit à paris depuis 2010",
    "le prénom paul est courant en france",
    "hugo est un prénom courant",
    "le mois de mai a été chaud",
    "en avril ne te découvre pas d'un fil",
    "m. mai a signé",
    "la loi pinel a été prorogée",
    "le dispositif pinel plus",
    "le barème macron s'applique",
    "l'arrêt blanco de 1873",
    "la jurisprudence perruche",
    "le code napoléon",
    "la loi alur protège les locataires",
    "le rapport lambert a été remis",
    "l'amendement est adopté",
    "le client est roi",
    "mon client est parti hier",
    "mon client paie ses dettes",
    "ma cliente porte plainte",
    "ma cliente marche avec une canne",
    "mon voisin loue son garage",
    "le salarié marque son désaccord",
    "l'employeur place le salarié en chômage partiel",
    "le locataire rose de colère a claqué la porte",
    "le bailleur jean de lui-même a résilié",
    "les enfants jouent dans la cour",
    "les parents contestent la décision",
    "les époux ont signé la convention",
    "les associés votent la dissolution",
    "les salariés grévistes ont été remplacés",
    "mes clients souhaitent transiger",
    "ses fils héritent de la maison",
    "nom du client à compléter",
    "nom de la société : à définir",
    "prénom du gérant inconnu",
    "nom : tenu secret",
    "prénom : nc",
    "nom et prénom : voir pièce 3",
    "client : collectivité locale",
    "client : professionnel du bâtiment",
    "employeur : fonction publique territoriale",
    "adversaire : inconnu à ce jour",
    "contre : x",
    "c/ assurance maladie",
    "recours c/ tiers responsable",
    "action c/ garant",
    "pourvoi c/ arrêt de la cour d'appel",
    "le cabinet médical a fermé",
    "le cabinet comptable et associés",
    "la société civile et commerciale",
    "la banque postale a refusé le prêt",
    "la compagnie aérienne a annulé le vol",
    "l'association sportive a été dissoute",
    "l'entreprise individuelle a été radiée",
    "la sarl unipersonnelle a été créée",
    "la sci de famille possède deux biens",
    "la sas simplifiée unipersonnelle",
    "une sarl de famille soumise à l'ir",
    "il a monté sa sasu tout seul",
    "le garage est fermé le lundi",
    "l'agence immobilière facture ses honoraires au vendeur",
    "la clinique vétérinaire a facturé",
    "mon employeur actuel ne paie plus",
    "le dossier médical a été transmis",
    "le dossier pénal est vide",
    "la procédure collective est ouverte",
    "il habite chez ses parents",
    "elle habite en face du tribunal",
    "il habite au rez-de-chaussée",
    "j'habite au 3e étage sans ascenseur",
    "il demeure introuvable",
    "elle demeure responsable du sinistre",
    "situé au cœur de la ville",
    "domicilié fiscalement en france",
    "adresse inconnue à ce jour",
    "adresse : voir kbis",
    "au 1er janvier 2024",
    "3 allée et venues",
    "2 quai et 1 voie",
    "il a pris l avenue en sens interdit",
    "la résidence principale est insaisissable",
    "sa résidence habituelle est en france",
    "le lotissement est achevé",
    "un chemin de servitude traverse le terrain",
    "une place de stationnement est louée 80 euros",
    "né à lyon (rhône)",
    "né en 1980 (44 ans)",
    "loyer de 850 euros (charges comprises)",
    "la cour (chambre sociale) a jugé",
]


@pytest.mark.parametrize("text", ORDINARY_TEXT_3)
def test_a_third_batch_of_ordinary_text(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text


# ---------------------------------------------------------------------------
# Names that a dot, a bracket or a comma cuts in two clauses
# ---------------------------------------------------------------------------

# (text, the masked text)
ACROSS_CLAUSES = [
    ("m. k. kervadec conteste", "m. PERSONNE_A conteste"),
    ("mme a. talvez a signé", "mme PERSONNE_A a signé"),
    ("m. j.p. kervadec a été mis à pied", "m. PERSONNE_A a été mis à pied"),
    ("m. j. p. kervadec conteste", "m. PERSONNE_A conteste"),
    ("mme vellin ep. kervadec conteste", "mme PERSONNE_A ep. PERSONNE_B conteste"),
    ("la société kerdalis (sas) refuse", "la société SOCIETE_A (sas) refuse"),
    ("kerdalis, sas au capital de 1000 euros", "SOCIETE_A, sas au capital de 1000 euros"),
    ("la société kerdalis s.a.s. a été condamnée", "la société SOCIETE_A s.a.s. a été condamnée"),
    ("la société zelmadec s.a.r.l. doit payer", "la société SOCIETE_A s.a.r.l. doit payer"),
]

NOT_ACROSS_CLAUSES = [
    "voir m. k. demain",
    "tout ce que madame a. le juge a tranché",
    "il a tort. kervadec conteste",
    "le salarié (cdi) conteste",
    "son employeur, sas au capital de 1000 euros, refuse",
    "une entreprise familiale, sarl au capital de 5000 euros",
    "la clause (sas) est nulle",
    "il est gérant (sarl) depuis 2019",
]


@pytest.mark.parametrize("text,masked", ACROSS_CLAUSES)
def test_names_across_two_clauses(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NOT_ACROSS_CLAUSES)
def test_no_name_across_two_clauses(text):
    assert _masker().mask(text).text == text


@pytest.mark.parametrize("text", ["M. K. Kervadec conteste.", "La société Kerdalis (SAS) refuse.",
                                  "Kerdalis, SAS au capital de 1000 euros.", "La société Kerdalis S.A.S. a été condamnée."])
def test_capitalised_names_across_two_clauses_keep_their_reading(monkeypatch, text):
    on = _masker().mask(text).text
    monkeypatch.setenv(SWITCH, "0")
    assert _masker().mask(text).text == on


# ---------------------------------------------------------------------------
# Two tiers: text with its capitals keeps its reading; text typed without capitals takes the other rules
# ---------------------------------------------------------------------------

# Sentences with correct capitals: a full-word civility stands alone before a verb, a participle, an adjective;
# a street word after a year; a label with an ordinary value; a legal form in capitals and an adjective. The
# output is the output with the rules off.
CORRECT_CAPITALS = [
    "Sur la demande de Madame présentée le 4 avril 2024, le juge a statué.",
    "Le contrat de Monsieur signé le 2 janvier 2020 est à durée indéterminée.",
    "Monsieur quitta la maison familiale en juin 2020.",
    "Madame refusa de signer le protocole.",
    "J'ai vu Monsieur pousser la porte du local.",
    "Madame polonaise travaille en France depuis 2015.",
    "Maître verrier reconnu, il a ouvert son atelier.",
    "Maîtres d'ouvrage : M. et Mme Kervadec.",
    "Le docteur référent a rendu son rapport.",
    "En 2023 impasse des discussions salariales.",
    "Lot 7 allée de boxes, lot 8 grenier.",
    "Nom : douteux, Prénom : incomplet",
    "La SCI familiale détient l'immeuble.",
    "Révision de Dr civil le jeudi.",
    "J'ai parlé avec Monsieur des délais.",
    "Mme accepta de venir et M. resta dehors.",
    "M. Benoit velkor conteste son avertissement.",
    "k. primes\nl. astreintes\nm. horaires\nn. frais de route",
]

# Text typed without capitals, or with the capitals of a phone keyboard (the first letter of the sentence, a
# first name). (text, the masked text)
TYPED_WITHOUT_CAPITALS = [
    ("La sarl zorvane conteste le congé.", "La sarl SOCIETE_A conteste le congé."),
    ("L'employeur brivanor sas n'a proposé aucun poste.", "L'employeur SOCIETE_A sas n'a proposé aucun poste."),
    ("Yanis kervadec a été mis à pied.", "PERSONNE_A a été mis à pied."),
    ("Mon client paul petit a été licencié.", "Mon client PERSONNE_A a été licencié."),
    ("Bonjour. Brivanor sas m'a licencié hier.", "Bonjour. SOCIETE_A sas m'a licencié hier."),
    ("mon client travaille chez Kerdalis sasu", "mon client travaille chez SOCIETE_A sasu"),
    ("le 3 mars 2022 m. kervadec a signé la rupture", "le 3 mars 2022 m. PERSONNE_A a signé la rupture"),
    ("Monsieur julien kervadec a signé le bail hier.", "Monsieur PERSONNE_A a signé le bail hier."),
]

# One person, one code, and an exact restore when two people of one text have the same surname and one first name
# has the capital of a keyboard.
SAME_SURNAME = [
    "Yanis kervadec et son épouse nadia kervadec ont acheté en indivision",
    "Mme Nadia kervadec et son mari yanis kervadec divorcent",
    "Yanis kervadec conteste. son frère lucas kervadec aussi.",
    "mon client Yanis kervadec et sa sœur emma kervadec héritent de la maison",
]


@pytest.mark.parametrize("text", CORRECT_CAPITALS)
def test_text_with_its_capitals_keeps_its_reading(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text


@pytest.mark.parametrize("text,masked", TYPED_WITHOUT_CAPITALS)
def test_text_typed_without_capitals(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", SAME_SURNAME)
def test_two_people_with_one_surname_keep_two_codes_and_an_exact_restore(text):
    m = _masker()
    r = m.mask(text)
    assert "PERSONNE_A" in r.text and "PERSONNE_B" in r.text and "kervadec" not in r.text
    assert m.unmask(r.text) == text


# Round 3: company shapes, the other surname, fields after a list mark. (text, the masked text)
MORE_TYPED_SHAPES = [
    ("ma cliente la sarl boulangerie zorvane conteste le congé", "ma cliente la sarl SOCIETE_A conteste le congé"),
    ("Employeur : transports kerdalis sarl. Salarié : m. kervadec.",
     "Employeur : transports SOCIETE_A sarl. Salarié : m. PERSONNE_A."),
    ("la selarl kervadec et talvenec représente le bailleur", "la selarl SOCIETE_A représente le bailleur"),
    ("mme nadia kervadec née dos zelmoune demande la liquidation", "mme PERSONNE_A née PERSONNE_B demande la liquidation"),
    ("madame kervadec, née talvenec, a renoncé à la succession",
     "madame PERSONNE_A, née PERSONNE_B, a renoncé à la succession"),
    ("madame kervadec (née talvenec) demande le divorce", "madame PERSONNE_A (née PERSONNE_B) demande le divorce"),
    ("- nom : kervadec\n- prénom : nadia", "- nom : PERSONNE_A\n- prénom : PERSONNE_B"),
    ("le 3 mars 2022 m. kervadec a signé la rupture conventionnelle",
     "le 3 mars 2022 m. PERSONNE_A a signé la rupture conventionnelle"),
]

NO_TYPED_SHAPES = [
    "nom : douteux, prénom : incomplet",
    "m. tns, aucune fiche de paie.",
    "la sarl boulangerie a fermé",
    "le mur fait 12 m. il est trop haut",
    "depuis l'arrêt jacques vabre, le juge écarte la loi contraire au traité.",
    "monsieur quitta la maison familiale en juin",
    "madame refusa de signer",
    "le dossier de monsieur avance bien.",
    "sur le licenciement de madame notifié le 3 mars",
    "j'ai vu monsieur pousser la porte du local.",
    "révision de dr civil le jeudi.",
    "habits : jean blanc, chemise rayée.",
    "la sarl croate a détaché huit maçons.",
    "madame hélas n'a gardé aucun courrier.",
    "mme lusophone ne parle pas le français.",
]


@pytest.mark.parametrize("text,masked", MORE_TYPED_SHAPES)
def test_more_shapes_typed_without_capitals(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", NO_TYPED_SHAPES)
def test_typed_text_with_no_name(text):
    assert _masker().mask(text).text == text


# A town, a month or an acronym with a capital does not show that a sentence has its capitals: a phone keyboard
# writes them. (text, the masked text)
TYPED_WITH_A_PLACE_OR_AN_ACRONYM = [
    ("mon client paul petit a écrit à Lyon", "mon client PERSONNE_A a écrit à Lyon"),
    ("Mon client paul petit travaille à Paris depuis Mars 2020 en CDI",
     "Mon client PERSONNE_A travaille à Paris depuis Mars 2020 en CDI"),
    ("ma cliente nadia kervadec a saisi le CPH de Nanterre", "ma cliente PERSONNE_A a saisi le CPH de Nanterre"),
    ("zadou mila conteste son licenciement devant le CPH de Lyon",
     "PERSONNE_A conteste son licenciement devant le CPH de Lyon"),
    ("la société brivanor sas a son siège à Marseille, en France",
     "la société SOCIETE_A sas a son siège à Marseille, en France"),
]

# A capital on another word is a capital of correct text: the sentence takes the rules of tier A only.
OTHER_CAPITALS = [
    "mon client paul petit a écrit au Tribunal",
    "mon client paul petit a lu le Code du travail",
    "Madame polonaise travaille en France depuis 2015.",
    "La SCI familiale détient le bien à Ajaccio.",
    "Le salarié a signé un CDI à Lyon le 3 Mars.",
    "Monsieur quitta Paris en Mai 2021.",
]


@pytest.mark.parametrize("text,masked", TYPED_WITH_A_PLACE_OR_AN_ACRONYM)
def test_a_place_or_an_acronym_keeps_the_sentence_typed(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text", OTHER_CAPITALS)
def test_another_capital_is_correct_text(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    assert _masker().mask(text).text == on.text


# ---------------------------------------------------------------------------
# Last guards: units, the pronoun "Me" after a colon, headings, captions, fields, street words, person nouns
# ---------------------------------------------------------------------------

LAST_GUARDS = [
    # "Me" after a colon, a quote, a bracket or a list mark is the pronoun
    "Il écrit : « Me réservant le droit d'agir, je maintiens ma demande. »",
    "Réponse : « Me soustrayant à cet ordre, je n'ai commis aucune faute. »",
    "- Me rappeler le délai d'appel",
    # "m." and "mm." as units of length
    "Le prix est de 40 euros le m. linéaire, pose comprise.",
    "le volume en m. cubes figure au devis.",
    "tolérance de 3 mm. linéaires sur le plan.",
    # a heading word and a legal form
    "Acomptes sarl : 1 500 euros TTC.",
    "Avantages eurl : régime fiscal du gérant.",
    "il faut régler les acomptes sarl et sci avant lundi.",
    "frais sas et sarl refacturés au client.",
    # acronyms and role nouns around "c/" and "contre"
    "asl c/ syndic, charges contestées.",
    "cfdt c/ direction, audience le 9.",
    "copro contre proprio, comme toujours.",
    # field values that are placeholders or ordinary words
    "nom : null",
    "prénom : tbd",
    "nom : dito",
    "nom : énigme, à chercher",
    # a street word used as an ordinary word; a count after a comma
    "il demeure 1 impasse complète dans les pourparlers.",
    "il habite 1 rue plus bas, même secteur.",
    "boutique 3 rue commerçante, 20000 visiteurs par mois.",
    "zone 3 quai nord, 12000 colis en retard.",
    # legal roles, states and job nouns after a civility
    "M. emphytéote acquitte la redevance annuelle.",
    "Le Tribunal relève que Mme usufruitière ne produit aucune pièce.",
    "monsieur carreleur, exposé au bruit pendant quinze ans.",
    "madame fleuriste, vente du fonds prévue en mars.",
    "situation : monsieur couvreur et madame coiffeuse.",
    "m. grutier intérimaire depuis deux ans.",
    "mme hispanophone ne lit pas l'arabe.",
    "m. réticent refuse la médiation.",
    "il est maître horloger, garantie des vices cachés.",
    "maître artificier, agrément préfectoral retiré.",
    # verbs after a civility
    "monsieur tergiverse, comme d'habitude.",
    "madame tergiverse et refuse de signer.",
    "m. bougonne à chaque audience.",
]

# A noun of a trade that is also a usual surname stays a name; real addresses, captions and fields stay masked.
# (text, the masked text)
STILL_NAMES = [
    ("m. boulanger conteste son licenciement", "m. PERSONNE_A conteste son licenciement"),
    ("mme meunier a signé le bail", "mme PERSONNE_A a signé le bail"),
    ("m. garnier conteste la sanction", "m. PERSONNE_A conteste la sanction"),
    ("représenté par m. kervadec", "représenté par m. PERSONNE_A"),
    ("Me kervadec plaide demain", "Me PERSONNE_A plaide demain"),
    ("kervadec c/ talvenec", "PERSONNE_A c/ PERSONNE_B"),
    ("dossier martin c/ kervadec", "dossier PERSONNE_A c/ PERSONNE_B"),
    ("nom : zadou, prénom : mila", "nom : PERSONNE_A, prénom : PERSONNE_B"),
    ("il habite 12 rue des glycines, 69007 lyon", "il habite ADRESSE_1"),
    ("elle demeure 7 chemin des vignes à lyon", "elle demeure ADRESSE_1 à lyon"),
    ("Bonjour. Brivanor sas m'a licencié hier.", "Bonjour. SOCIETE_A sas m'a licencié hier."),
    ("mon client travaille chez Kerdalis sasu", "mon client travaille chez SOCIETE_A sasu"),
    ("kerdalis sarl et talvez sas sont en litige", "SOCIETE_A sarl et SOCIETE_B sas sont en litige"),
]


@pytest.mark.parametrize("text", LAST_GUARDS)
def test_the_last_guards(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    assert _masker().mask(text).text == on.text


@pytest.mark.parametrize("text,masked", STILL_NAMES)
def test_names_stay_masked_next_to_the_last_guards(text, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert m.unmask(r.text) == text


def test_job_nouns_that_are_surnames_are_left_out_of_the_job_list():
    from ragbase_shield.engine import lexicon as lx
    from ragbase_shield.engine import names as nm
    persons = nm._lc_sets()["persons"]
    assert "soudeur" in persons and "cariste" in persons
    for word in ("boulanger", "meunier", "berger", "boucher", "marchand", "mercier", "charpentier", "pelletier"):
        assert word not in persons
    assert len(lx.lowercase_words()["jobs"]) > 200
