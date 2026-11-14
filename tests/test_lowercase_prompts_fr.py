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
    ("12 rue victor hugo paris", ["12 rue victor hugo paris"]),
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
    ("le locataire du 12 rue des lilas proteste.", ["12 rue des lilas"]),
    ("le 12 rue de la porte dorée appartient à mon client", ["12 rue de la porte dorée"]),
    ("il habite 12 rue de la vieille forge", ["12 rue de la vieille forge"]),
    # a capital on the street name or on the town only
    ("il habite 12 rue des Glycines, 69007 lyon", ["12 rue des Glycines, 69007 lyon"]),
    ("il habite 12 rue des glycines, 69007 Lyon", ["12 rue des glycines, 69007 Lyon"]),
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
    ("mr Vellin a appelé hier", ["Vellin"]),
    ("dr Roquevert a signé le certificat", ["Roquevert"]),
    ("mlle Kerdalis demande des dommages", ["Kerdalis"]),
    ("je représente m. Kelmadi", ["Kelmadi"]),
    ("bonjour, m. Brivault a reçu un avertissement", ["Brivault"]),
    ("m. Le Bihannec conteste", ["Le Bihannec"]),
    ("mme De Roquevert a signé", ["De Roquevert"]),
    ("m. Yanis Kervadec a signé le bail", ["Yanis Kervadec"]),
    ("mm. Vellin et Talvez contestent", ["Vellin", "Talvez"]),
    ("mme Pradimont et m. Talvez divorcent", ["Pradimont", "Talvez"]),
    ("voir m. Kervadec, mme Talvez et dr Vellin", ["Kervadec", "Talvez", "Vellin"]),
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
    for low, cap in (("mm. ", "MM. "), ("m. ", "M. "), ("mme ", "Mme "), ("mlle ", "Mlle "), ("mr ", "Mr "), ("dr ", "Dr ")):
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
    "Benoit velkor conteste son avertissement.",
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
    ("M. Zadou mila conteste son licenciement.", ["Zadou mila"]),
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
    ("contre martin sas", ["martin"], "contre SOCIETE_A sas"),
    ("une facture de laurent sas", ["laurent"], "une facture de SOCIETE_A sas"),
    ("mon client travaille chez julien sarl", ["julien"], "mon client travaille chez SOCIETE_A sarl"),
    ("la société jean kervadec sas a fermé", ["jean kervadec"], "la société SOCIETE_A sas a fermé"),
    ("l'agence zorvane sarl a été condamnée", ["zorvane"], "l'agence SOCIETE_A sarl a été condamnée"),
    ("mon employeur brivault eurl ne me paie plus", ["brivault"], "mon employeur SOCIETE_A eurl ne me paie plus"),
    ("litige avec transports belmadi sarl", ["belmadi"], "litige avec transports SOCIETE_A sarl"),
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
    ("thomas leroy et emma leroy divorcent", ["thomas leroy", "emma leroy"]),
    ("ma cliente emma blanc et son mari lucas blanc divorcent", ["emma blanc", "lucas blanc"]),
    ("l'employeur de ma cliente est philippe marchand", ["philippe marchand"]),
    ("je défends lucas meunier", ["lucas meunier"]),
    ("le dossier oppose paul chevalier à lucas berger", ["paul chevalier", "lucas berger"]),
    ("julie fontaine, salariée depuis 2015, conteste la sanction", ["julie fontaine"]),
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
    "rdv client sam aprem",
    "mon client conteste",
    "mon client principal conteste",
    "le salarié protégé conteste",
    "ma cliente rose de colère a quitté la salle",
    "les époux kervadec contestent",
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
    ("m. cousin conteste son licenciement", ["cousin"]),
    ("mme voisin a signé le bail", ["voisin"]),
    ("je représente mme neveu", ["neveu"]),
    ("m. paul marques a signé le bail", ["paul marques"]),
    ("m. karim carre a été licencié", ["karim carre"]),
    ("mme julie cousin conteste", ["julie cousin"]),
    ("m. ly conteste son licenciement", ["ly"]),
    ("je représente mme ly", ["ly"]),
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
    ("nom : zadou", "nom : PERSONNE_A"),
    ("nom : zadou, prénom : mila", "nom : PERSONNE_A, prénom : PERSONNE_B"),
    ("nom : zadou\nprénom : mila\nné le 3 mars 1980", "nom : PERSONNE_A\nprénom : PERSONNE_B\nné le NAISSANCE_1"),
    ("nom de naissance : kervadec", "nom de naissance : PERSONNE_A"),
    ("prénoms : mila nadia", "prénoms : PERSONNE_A"),
    ("client : kervadec jean, né le 3 mars 1980 à lyon", "client : PERSONNE_A, né le NAISSANCE_1 à lyon"),
    ("client : jean kervadec", "client : PERSONNE_A"),
]

NO_FIELD_VALUE = [
    "nom : à compléter",
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
    ("dossier m. samir / kerval sas", "dossier m. PERSONNE_A / SOCIETE_A sas"),
    ("contre : kerval sas", "contre : SOCIETE_A sas"),
    ("défendeur : brivanor sarl", "défendeur : SOCIETE_A sarl"),
    # names of four or five words, hyphenated initials, a name particle in a compound
    ("madame nelba thi zadou demande un titre de séjour", "madame PERSONNE_A demande un titre de séjour"),
    ("mme maria del carmen kervadec talvez conteste", "mme PERSONNE_A conteste"),
    ("m. jose antonio brivault da costa a été blessé", "m. PERSONNE_A a été blessé"),
    ("m. j-p kervadec a été mis à pied", "m. PERSONNE_A a été mis à pied"),
    ("mme ben-ahmed conteste", "mme PERSONNE_A conteste"),
    ("mme léa du bois a signé", "mme PERSONNE_A a signé"),
    # spellings of a civility typed in lower case
    ("melle vellin demande des dommages", "melle PERSONNE_A demande des dommages"),
    ("mdme kervadec a signé", "mdme PERSONNE_A a signé"),
    ("mrs vellin a signé", "mrs PERSONNE_A a signé"),
    # a legal form in full words, a digit and a join word in a company name, a surname-like word after a noun
    ("la société par actions simplifiée kerval", "la société par actions simplifiée SOCIETE_A"),
    ("la société à responsabilité limitée belmadi a fermé", "la société à responsabilité limitée SOCIETE_A a fermé"),
    ("la société civile immobilière zorvane", "la société civile immobilière SOCIETE_A"),
    ("la société k2 conseil sas a rompu le contrat", "la société SOCIETE_A sas a rompu le contrat"),
    ("la société kerval et compagnie sarl a fermé", "la société SOCIETE_A sarl a fermé"),
    ("la société kerval & co sas a fermé", "la société SOCIETE_A sas a fermé"),
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
