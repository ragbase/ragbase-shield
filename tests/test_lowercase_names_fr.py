"""v0.4.1: names typed in lower case in French text.

Lawyers type prompts fast, often with no capital: "M. zadou mila", "mme claire dufresne conteste". The rules of
this version find a name with no capital from what stands around it: a civility before it (A), a first name of
the lexicon at its start (B), a company cue and a legal form around it (C); one person keeps one code whatever
the letter case (D). The guards matter as much: a determiner, a role, a verb or an ordinary word
is never masked, and capitalised text gives the 0.4.0 output. ``RAGBASE_SHIELD_LOWERCASE_NAMES=0`` turns the rules
off. Invented data only: every name, company and sentence below is made up for these tests."""
from __future__ import annotations

import pytest

from ragbase_shield import config
from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import lexicon as lx
from ragbase_shield.engine import names as nm
from ragbase_shield.engine import ner as nr
from ragbase_shield.engine.normalize import fold_word

SWITCH = "RAGBASE_SHIELD_LOWERCASE_NAMES"

# Four typed lines: a civility or a person noun, then a name with no capital. (text, the names masked, the masked
# text)
TYPED_LINES = [
    ("M. zadou mila, domicilié 12 rue des Glycines, 69007 Lyon, conteste son licenciement par la société "
     "Ateliers Brunelac SAS",
     ["zadou mila", "Ateliers Brunelac"],
     "M. PERSONNE_A, domicilié ADRESSE_1, conteste son licenciement par la société SOCIETE_A SAS"),
    ("M. nelba samir, domicilié 12 rue des Glycines, 69007 Lyon, conteste son licenciement",
     ["nelba samir"],
     "M. PERSONNE_A, domicilié ADRESSE_1, conteste son licenciement"),
    ("mme claire dufresne conteste son licenciement.",
     ["claire dufresne"],
     "mme PERSONNE_A conteste son licenciement."),
    ("bonjour, mon client jean dupont a été licencié par la société durand sas.",
     ["jean dupont", "durand"],
     "bonjour, mon client PERSONNE_A a été licencié par la société SOCIETE_A sas."),
]

# A: a civility, then a name in lower case. (text, the names masked, in text order)
CIVILITY = [
    ("m. kervadec conteste la sanction.", ["kervadec"]),
    ("Mme pradimont a quitté l'entreprise en mars.", ["pradimont"]),
    ("mlle ouardi demande un rappel de salaire.", ["ouardi"]),
    ("monsieur talvez refuse de payer la pension.", ["talvez"]),
    ("madame varenne souhaite divorcer.", ["varenne"]),
    ("Monsieur julien maudet a signé le bail hier.", ["julien maudet"]),
    ("Madame nadia brivanor travaille à temps partiel.", ["nadia brivanor"]),
    ("maître karim ben salah représente madame de la tour.", ["karim ben salah", "de la tour"]),
    ("Me gravelotte plaide demain matin.", ["gravelotte"]),
    ("j'ai écrit à Me pernaud hier soir.", ["pernaud"]),
    ("mme anne-sophie velanor a saisi le conseil.", ["anne-sophie velanor"]),
    ("m. jean pierre quimpertin, gérant, a signé.", ["jean pierre quimpertin"]),
    ("contre m. thomas kerdalis et mme emma kerdalis.", ["thomas kerdalis", "emma kerdalis"]),
    ("mm. vellin et talvez ont signé.", ["vellin", "talvez"]),
    ("bonjour, je représente mme d'arvignac dans ce dossier.", ["d'arvignac"]),
    ("monsieur van der kesselt est le bailleur.", ["van der kesselt"]),
    ("mme rose kervadec a contesté la rupture.", ["rose kervadec"]),
    ("m. petit conteste son licenciement.", ["petit"]),
    ("le cabinet de maître pradimont suit le dossier.", ["pradimont"]),
    ("le rendez-vous est fixé avec mme ouardi", ["ouardi"]),
    ("mme marie talvez a déposé plainte.", ["marie talvez"]),
    ("m. zadou Mila conteste la décision.", ["zadou Mila"]),
    ("mme veuve pradimont a renoncé à la succession.", ["pradimont"]),
    ("mme nadia kervadec épouse maudet demande le divorce.", ["nadia kervadec", "maudet"]),
    ("mme fatoumata quimpertin est salariée depuis 2019.", ["fatoumata quimpertin"]),
    ("m. kervadec jean a signé le bail.", ["kervadec jean"]),
    ("mr vellin a appelé ce matin.", ["vellin"]),
    ("MM. vellin et talvez ont signé le protocole.", ["vellin", "talvez"]),
]

# B: a first name of the lexicon in lower case, then a word that no French list knows.
FIRST_NAME = [
    ("ma cliente sophie martin-leroy, née le 3 mai 1980, travaille chez dupont conseil sarl.",
     ["sophie martin-leroy", "dupont conseil"]),
    ("nadia kervadec conteste son licenciement.", ["nadia kervadec"]),
    ("je défends paul pradimont devant le conseil de prud'hommes.", ["paul pradimont"]),
    ("le bail a été signé par camille ouardi.", ["camille ouardi"]),
    ("julien talvez, né le 2 février 1988, est salarié depuis 2015.", ["julien talvez"]),
    ("jean pierre maudet a démissionné.", ["jean pierre maudet"]),
    ("anne-sophie brivanor réclame des heures supplémentaires.", ["anne-sophie brivanor"]),
    ("mon voisin lucas gravelotte refuse de couper sa haie.", ["lucas gravelotte"]),
    ("karim ben salah est mon client.", ["karim ben salah"]),
    ("le salarié mehdi pernaud a été convoqué.", ["mehdi pernaud"]),
    ("thomas valette et emma valette sont séparés.", ["thomas valette", "emma valette"]),
    ("pierre lervignac conteste la décision.", ["pierre lervignac"]),
    ("jean martin a écrit au bailleur.", ["jean martin"]),
    ("l'employeur est représenté par me julien morvanti.", ["julien morvanti"]),  # the first name, not "me"
    ("copie à lucas maudet et à camille velanor.", ["lucas maudet", "camille velanor"]),
    ("léa pradimont conteste son avertissement.", ["léa pradimont"]),
]

# C: a company name in lower case with a legal form in any letter case.
COMPANY = [
    ("la société durand sas a licencié mon client.", ["durand"]),
    ("l'entreprise kerdalis sarl refuse de payer.", ["kerdalis"]),
    ("le cabinet morvanti selarl représente la partie adverse.", ["morvanti"]),
    ("la banque velanor sas a refusé le prêt.", ["velanor"]),
    ("mon client travaille chez quimpertin transports sarl.", ["quimpertin transports"]),
    ("la sarl vellin conseil a résilié le contrat.", ["vellin conseil"]),
    ("la SCI talvez loue un local.", ["talvez"]),
    ("le groupe varenne sasu emploie dix salariés.", ["varenne"]),
    ("la société durand et fils sarl est en redressement.", ["durand et fils"]),
    ("il a été licencié par brivanor logistique sarl en mars.", ["brivanor logistique"]),
    ("le capital de pernaud sas est de 10 000 euros.", ["pernaud"]),
    ("contrat entre kervadec sarl et maudet sas.", ["kervadec", "maudet"]),
    ("la sarl ouardi et fils a été créée en 2010.", ["ouardi et fils"]),
    ("la sarl Pradimont a résilié le contrat.", ["Pradimont"]),  # a lower-case form before a capitalised name
    ("la société Kerdalis EURL a fait appel.", ["Kerdalis"]),  # capitals: the 0.4.0 span, unchanged
]

# A capitalised first name, then a word in lower case that no list knows: the word may be a job, an adverb or a
# legal word as well as a surname, so the capitalised rules read the line alone (the same output with the rules off).
KEYBOARD_UNKNOWN_WORD = [
    "Mme Claire dufresne conteste son licenciement.",
    "M. Thibault mercadier a signé le bail hier.",
    "Monsieur Paul vernaton, salarié depuis 2015, conteste la sanction.",
    "Je représente Mme Sophie kerdalis.",
    "Me Karim talvez plaide demain matin.",
    "Bonjour, mon client Jean dupont a été licencié.",
    "Je pense que Paul pradimont conteste la décision.",
    "Le bail est au nom de ma cliente Emma velanor.",
    "M. Zadou mila, domicilié 12 rue des Glycines, 69007 Lyon, conteste son licenciement.",
    "M. Kervadec julien conteste la sanction.",
    "M. Benoit velkor conteste son avertissement.",
    "Mme Martin zorvaine convoquée ne s'est pas présentée.",
    "M. Xavier brivanec a supprimé le site.",
]

POSITIVE = [(t, names) for t, names, _out in TYPED_LINES] + CIVILITY + FIRST_NAME + COMPANY

# A word in lower case after a capitalised name is no surname: the mask is the 0.4.0 mask. (text, the names masked)
AFTER_A_NAME = [
    ("M. Martin susvisé a formé un pourvoi.", ["Martin"]),
    ("M. Thomas précité a répondu aux conclusions.", ["Thomas"]),
    ("M. Bernard fils conteste la donation.", ["Bernard"]),
    ("Mme Martin seule assume la charge des enfants.", ["Martin"]),
    ("M. Laurent également conteste la décision.", ["Laurent"]),
    ("M. Vincent junior a signé le protocole.", ["Vincent"]),
    ("M. Simon cohéritier conteste le partage.", ["Simon"]),
    ("Je représente M. Martin aujourd'hui.", ["Martin"]),
    ("Il a écrit à M. Robert notaire à Lyon.", ["Robert"]),
    ("M. Henri demeurant à Paris conteste.", ["Henri"]),
    ("M. Martin lui-même a signé.", ["Martin"]),
    ("Mme Thomas titulaire", ["Thomas"]),
    ("Contre M. Laurent derechef.", ["Laurent"]),
    ("Le tribunal a déclaré M. Martin démissionnaire.", ["Martin"]),
    ("Le juge a nommé Mme Bernard cogérante.", ["Bernard"]),
    ("Le tribunal déclare M. Thomas velkor.", ["Thomas"]),  # a word no list knows after a verb with an attribute
    ("M. Thomas xyz a répondu.", ["Thomas"]),               # three letters: an abbreviation, no surname
    ("M. Martin contsete la décision.", ["Martin"]),        # a typing error before a determiner
    ("Me Dupont plaide demain.", ["Dupont"]),
    ("Le tribunal a jugé Paul forclos en sa demande.", []),
    ("On a élu Julie cheffe de projet.", []),
]

# The guards: nothing of these sentences is a person or a company.
NEGATIVE = [
    # a determiner, a role or punctuation after a civility
    "M. le président a ouvert l'audience.",
    "Mme la juge a renvoyé l'affaire.",
    "monsieur le maire a signé l'arrêté.",
    "Me, je vous écris au sujet du dossier.",
    "madame, monsieur, veuillez trouver ci-joint la convocation.",
    "monsieur le proviseur a exclu l'élève.",
    "madame la rectrice a rejeté le recours.",
    "monsieur le doyen a convoqué le conseil.",
    "bonjour maître, voici les pièces.",
    "cher monsieur, je fais suite à notre échange.",
    # "me" the pronoun, "Me" at the start of a sentence before a verb
    "il me semble que sa demande est fondée.",
    "me dupont plaide demain.",
    "Me semble correct sur ce point.",
    "Me résumer ce jugement en dix lignes.",
    "Me rédiger une mise en demeure.",
    "Me peaufiner ce courrier avant envoi.",
    "Me confirmez-vous la date du rendez-vous ?",
    "Me référant à votre courrier, je vous informe de ma décision.",
    "merci de me rappeler demain matin.",
    # a civility used alone for a party, then a verb or a state
    "madame demande une prestation compensatoire.",
    "monsieur verse une pension de 300 euros.",
    "madame travaille à temps partiel depuis 2019.",
    "madame travaille a temps partiel depuis 2019.",
    "monsieur conteste le montant, madame réclame la garde.",
    "mme perçoit le rsa et m. refuse de payer.",
    "madame seule assume la charge des enfants.",
    "monsieur absent à l'audience.",
    "m. totalement opposé à la vente.",
    "monsieur acquiesce au jugement.",
    "madame priorise ses enfants et monsieur fiabilise ses revenus.",
    "madame porte plainte contre son voisin.",
    "monsieur chauffeur routier, madame sans emploi.",
    "M. xxx demeurant à xxx, né le xx/xx/xxxx.",
    "monsieur et madame sont séparés depuis 2019.",
    "il doit poser 12 m. de clôture.",
    # a civility word used as a common noun
    "ce monsieur prétend que le bail est nul.",
    "un monsieur âgé est venu au cabinet.",
    "le maître d'ouvrage conteste la réception.",
    "il est employé comme maître nageur à la piscine.",
    "maître d'apprentissage depuis dix ans, il forme les jeunes.",
    "le professeur principal a convoqué les parents.",
    "le docteur traitant a prescrit un arrêt.",
    "le dr traitant refuse de communiquer le dossier.",
    "docteur honoris causa de l'université.",
    "mes clients contestent la décision.",
    "Mes clients contestent la décision.",
    "pr info, le client a appelé ce matin.",
    # a first name that is also a common word
    "pierre angulaire du dossier, ce contrat est nul.",
    "elle porte une robe rose bonbon.",
    "le juste prix du bien est discuté.",
    "la marguerite est fanée.",
    "il porte un jean délavé.",
    "un mur en pierre sèche sépare les terrains.",
    "il marie sa fille en juin.",
    "le droit romain connaissait cette règle.",
    "une aurore boréale a été observée.",
    "max 3 jours de délai.",
    "il habite rue jean jaurès à lyon.",
    "ma fille marine est en cm2.",
    "il me marie demain avec sa cousine.",
    "john called me about the file",
    # legal forms that are also words, companies with no name
    "sa demande est fondée.",
    "la sas est en liquidation.",
    "il a créé une sarl en 2020.",
    "le sas d'entrée est fermé.",
    "la sarl familiale bénéficie d'un régime fiscal.",
    "la scp notariale a reçu l'acte.",
    "la société mère détient 80 % du capital.",
    "le cabinet conseille la société depuis 2015.",
    "elle travaille chez elle le lundi.",
    "les statuts de la sarl sont clairs.",
    "il passe par le sas de sécurité.",
    "la sarl locataire ne paie plus.",
    # verbs, dates, amounts, courts, codes, articles and laws
    "en mai, au plus tard, la somme sera versée.",
    "le conseil de prud'hommes de lyon a jugé le 3 mars 2025.",
    "article l. 1232-1 du code du travail.",
    "le tribunal judiciaire de paris a condamné la société.",
    "la loi pinel s'applique au logement.",
    "le salarié a été licencié pour faute grave.",
    "il conteste son licenciement pour motif économique.",
    "le bailleur réclame trois mois de loyer.",
    "pouvez-vous me résumer cet arrêt ?",
    "bonjour claude, peux-tu relire ce texte ?",
]

# Correctly capitalised text: the output with the rules on must equal the output with the rules off (0.4.0).
CAPITALISED = [
    "M. Thibault Mercadier conteste son licenciement par la société Ateliers Brunelac SAS.",
    "Mme Claire Dufresne, née le 3 mai 1980 à Lyon, demeurant 12 rue des Glycines, 69007 Lyon, a saisi le conseil.",
    "Maître Karim Ben Salah représente Madame de La Tour devant le tribunal judiciaire de Nanterre.",
    "Me Dupont plaide demain devant la cour d'appel de Versailles.",
    "Le conseil de prud'hommes de Lyon a jugé le 3 mars 2025 (article L. 1232-1 du code du travail).",
    "M. le Président, Mme la Juge, je vous prie d'agréer l'expression de ma considération distinguée.",
    "Madame demande une prestation compensatoire et Monsieur s'y oppose.",
    "La société Kerdalis SARL, représentée par son gérant M. Julien Maudet, a résilié le contrat.",
    "La SCI Les Tilleuls loue un local commercial à la SAS Brivanor Logistique.",
    "Jean Dupont et Sophie Martin-Leroy sont mariés depuis 2010.",
    "DUPONT Jean-Pierre, né le 4 mars 1975 à Paris, est gérant de la SARL Velanor.",
    "Cher Maître, je fais suite à notre entretien téléphonique.",
    "Les époux Talvez ont acquis le bien en 2015.",
    "M. Pradimont soutient que la clause est abusive ; Mme Varenne le conteste.",
    "Pierre angulaire du dossier, le contrat de bail a été signé en 2019.",
    "Me résumer ce jugement en dix lignes, puis me proposer trois arguments.",
    "M. Martin susvisé a formé un pourvoi en cassation.",
    "Mme Petit demeurant à Lyon est représentée par Me Bernard avocat au barreau de Lyon.",
    "M. Durand ès qualités de liquidateur de la société Brivanor.",
    "Madame Rose Kervadec veuve Talvez a renoncé à la succession.",
    "Le gérant, M. Thomas Kerdalis, et son épouse, Mme Emma Kerdalis, sont cautions solidaires.",
    "Marie a déposé plainte ; Paul nie les faits.",
    "MM. Vellin et Talvez ont signé le protocole.",
    "Par ces motifs, condamne la société Morvanti à payer à M. Kervadec la somme de 8 000 euros.",
]


def _masker(**kw) -> Masker:
    return Masker(MemoryStore(), use_ner=False, **kw)


def _names(text: str, masker: Masker | None = None, **kw) -> list[str]:
    """The person and company mentions masked in ``text``, in text order."""
    r = (masker or _masker()).mask(text, **kw)
    return [s.value for s in r.spans if s.kind in ("PERSON", "ORG")]


@pytest.fixture(autouse=True)
def _default_switch(monkeypatch):
    monkeypatch.delenv(SWITCH, raising=False)


# ---------------------------------------------------------------------------
# The typed lines and the four rules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,names,masked", TYPED_LINES)
def test_typed_lines_are_masked(text, names, masked):
    m = _masker()
    r = m.mask(text)
    assert r.text == masked
    assert [s.value for s in r.spans if s.kind in ("PERSON", "ORG")] == names
    assert m.unmask(r.text) == text


@pytest.mark.parametrize("text,names,masked", TYPED_LINES)
@pytest.mark.parametrize("chat", [None, True, False])
def test_typed_lines_with_and_without_the_chat_flag(text, names, masked, chat):
    assert _masker().mask(text, chat=chat).text == masked


@pytest.mark.parametrize("text,names", POSITIVE)
def test_lower_case_names_are_masked(text, names):
    m = _masker()
    r = m.mask(text)
    assert [s.value for s in r.spans if s.kind in ("PERSON", "ORG")] == names
    for name in names:
        assert name not in r.text
    assert m.unmask(r.text) == text  # restore gives back the text as typed


def test_there_are_enough_positive_cases():
    assert len(POSITIVE) >= 40 and len({t for t, _ in POSITIVE}) == len(POSITIVE)


@pytest.mark.parametrize("text,names", CIVILITY + FIRST_NAME)
def test_people_get_person_codes(text, names):
    r = _masker().mask(text)
    people = [s for s in r.spans if s.value in names and s.kind == "PERSON"]
    assert len(people) >= 1


@pytest.mark.parametrize("text,names", [c for c in COMPANY if c[1]])
def test_companies_get_company_codes_and_keep_the_legal_form(text, names):
    r = _masker().mask(text)
    assert [s.kind for s in r.spans if s.value in names] == ["ORG"] * len(names)
    low = r.text.lower()
    assert any(form in low.split() or form + "." in low.split()
               for form in ("sas", "sarl", "selarl", "sci", "sasu", "eurl"))


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", NEGATIVE)
def test_ordinary_words_are_not_masked(text):
    assert _names(text) == []


def test_there_are_enough_negative_cases():
    assert len(NEGATIVE) >= 40 and len(set(NEGATIVE)) == len(NEGATIVE)


@pytest.mark.parametrize("text,kept", [
    ("m. samir conteste son licenciement.", "conteste son licenciement."),
    ("mme dufresne a été licenciée le 3 mars.", "a été licenciée le"),
    ("m. kervadec, né le 4 mars 1975, est gérant.", "est gérant."),
    ("madame ouardi et monsieur talvez sont associés.", "sont associés."),
    ("mme pradimont travaille comme infirmière à lyon.", "travaille comme infirmière à lyon."),
    ("monsieur mila doit 4 000 euros à la banque.", "doit 4 000 euros à la banque."),
])
def test_a_name_stops_at_a_verb(text, kept):
    r = _masker().mask(text)
    assert kept in r.text and "PERSONNE_A" in r.text


def test_lower_case_me_and_sa_are_never_a_civility_or_a_legal_form():
    assert _names("il me dupont semble") == []
    assert _names("me kervadec plaide demain.") == []
    assert _names("la société durand sa a licencié mon client.") == []  # lower-case "sa" is the possessive
    assert _names("la société durand SA a licencié mon client.") == ["durand"]  # in capitals it is the form
    for word in ("la", "en", "au", "sa", "me"):
        assert _names(f"mme {word} conteste.") == []


def test_the_words_around_decide_between_a_verb_and_a_name():
    # a verb form or an ordinary word right after the civility is no name, whatever stands around it
    assert _names("madame porte plainte contre son voisin.") == []
    assert _names("j'ai écrit à mme porte hier.") == []
    assert _names("mme porte conteste le congé.") == []
    # a first name that is also a verb form
    assert _names("mme marie talvez conteste.") == ["marie talvez"]
    assert _names("il marie sa fille à un notaire.") == []


def test_dates_amounts_and_references_keep_their_own_kind():
    r = _masker().mask("mme claire dufresne, née le 3 mai 1980, réclame 12 500 euros (rg 21/01234) "
                       "selon l'article l. 1232-1 du code du travail.")
    assert [(s.kind, s.value) for s in r.spans if s.kind in ("PERSON", "ORG")] == [("PERSON", "claire dufresne")]
    assert "12 500 euros" in r.text and "du code du travail" in r.text and "article l. 1232-1" in r.text
    assert "3 mai 1980" not in r.text  # the birth date detector of 0.4.0


# ---------------------------------------------------------------------------
# Capitalised text: the 0.4.0 output, byte for byte
# ---------------------------------------------------------------------------


def _outputs(texts: list[str]) -> list[str]:
    return [_masker().mask(t).text for t in texts]


def test_capitalised_text_is_the_same_with_the_rules_on_and_off(monkeypatch):
    assert len(CAPITALISED) >= 20
    monkeypatch.setenv(SWITCH, "0")
    off = _outputs(CAPITALISED)
    monkeypatch.setenv(SWITCH, "1")
    on = _outputs(CAPITALISED)
    assert on == off


def test_capitalised_dossier_is_the_same_with_the_rules_on_and_off(monkeypatch):
    """One dossier, the capitalised sentences in a row: same codes, same store."""
    def run() -> tuple[list[str], list[tuple[str, str, str]]]:
        m = _masker()
        out = [m.mask(t).text for t in CAPITALISED]
        return out, [(e.code, e.kind, e.value) for e in m.store.all()]

    monkeypatch.setenv(SWITCH, "0")
    off = run()
    monkeypatch.setenv(SWITCH, "1")
    assert run() == off


def test_capitalised_names_keep_their_0_4_0_spans():
    r = _masker().mask("M. Thibault Mercadier conteste. Mme Claire Dufresne et Jean Dupont aussi.")
    assert r.text == "M. PERSONNE_A conteste. Mme PERSONNE_B et PERSONNE_C aussi."


@pytest.mark.parametrize("text,names", AFTER_A_NAME)
def test_a_word_after_a_capitalised_name_is_no_surname(monkeypatch, text, names):
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text).text
    monkeypatch.setenv(SWITCH, "1")
    r = _masker().mask(text)
    assert r.text == off
    assert [s.value for s in r.spans if s.kind in ("PERSON", "ORG")] == names


@pytest.mark.parametrize("text", KEYBOARD_UNKNOWN_WORD)
def test_a_capitalised_first_name_and_an_unknown_word_keep_the_capitalised_reading(monkeypatch, text):
    on = _masker().mask(text)
    monkeypatch.setenv(SWITCH, "0")
    off = _masker().mask(text)
    assert on.text == off.text


# ---------------------------------------------------------------------------
# D: one code whatever the letter case, and restore
# ---------------------------------------------------------------------------


def test_one_person_one_code_across_letter_cases():
    m = _masker()
    assert m.mask("M. nelba samir conteste son licenciement.").text == "M. PERSONNE_A conteste son licenciement."
    assert m.mask("Nelba Samir a saisi le conseil.").text == "PERSONNE_A a saisi le conseil."
    assert m.mask("M. Samir a raison.").text == "M. PERSONNE_A a raison."
    assert m.mask("m. samir est venu hier.").text == "m. PERSONNE_A est venu hier."
    assert m.mask("NELBA SAMIR a signé.").text == "PERSONNE_A a signé."
    assert [e.code for e in m.store.all() if e.kind == "PERSON"] == ["PERSONNE_A"]


def test_one_person_one_code_in_one_text():
    r = _masker().mask("M. zadou mila conteste. M. Mila a raison. zadou mila est parti.")
    assert r.text == "M. PERSONNE_A conteste. M. PERSONNE_A a raison. PERSONNE_A est parti."


def test_surname_alone_keeps_the_code_in_both_cases():
    m = _masker()
    assert m.mask("mme claire dufresne conteste.").text == "mme PERSONNE_A conteste."
    assert m.mask("Mme Dufresne a raison.").text == "Mme PERSONNE_A a raison."
    assert m.mask("mme dufresne est venue.").text == "mme PERSONNE_A est venue."
    assert m.mask("Claire Dufresne a signé.").text == "PERSONNE_A a signé."


def test_a_capitalised_name_first_then_lower_case():
    m = _masker()
    assert m.mask("Thibault Mercadier a signé.").text == "PERSONNE_A a signé."
    assert m.mask("m. mercadier conteste.").text == "m. PERSONNE_A conteste."
    assert m.mask("thibault mercadier est venu.").text == "PERSONNE_A est venu."
    assert len(m.store.all()) == 1


def test_one_company_one_code_across_letter_cases():
    m = _masker()
    assert m.mask("la société durand sas a licencié mon client.").text == \
        "la société SOCIETE_A sas a licencié mon client."
    assert m.mask("Durand SAS conteste.").text == "SOCIETE_A SAS conteste."
    assert m.mask("La société Durand a répondu.").text == "La société SOCIETE_A a répondu."
    assert [e.code for e in m.store.all()] == ["SOCIETE_A"]


def test_two_people_keep_two_codes():
    r = _masker().mask("mme nadia kervadec et m. julien maudet sont associés.")
    assert r.text == "mme PERSONNE_A et m. PERSONNE_B sont associés."


def test_the_link_of_a_lower_case_person_is_for_lower_case_values_only():
    """0.4.0 gives "M. Nelba Samir" and "M. Samir" two codes (the lexicon reads "Samir" as the first name); with
    capitals this stays."""
    m = _masker()
    assert m.mask("M. Nelba Samir conteste son licenciement.").text == "M. PERSONNE_A conteste son licenciement."
    assert m.mask("M. Samir a raison.").text == "M. PERSONNE_B a raison."


@pytest.mark.parametrize("text", [t for t, _n in POSITIVE])
def test_restore_gives_back_the_text_as_typed(text):
    m = _masker()
    assert m.unmask(m.mask(text).text) == text


def test_restore_writes_the_first_spelling_of_the_dossier():
    m = _masker()
    first = m.mask("M. nelba samir conteste.")
    assert m.unmask(first.text) == "M. nelba samir conteste."
    later = m.mask("Nelba Samir a saisi le conseil.")
    assert m.unmask(later.text) == "nelba samir a saisi le conseil."  # one code, one stored spelling (as in 0.4.0)


# ---------------------------------------------------------------------------
# The switch, the modes, the language
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "OFF"])
def test_the_switch_gives_the_0_4_0_detection(monkeypatch, value):
    monkeypatch.setenv(SWITCH, value)
    assert nm.lowercase_names() is False and config.lowercase_names() is False
    assert _masker().mask(TYPED_LINES[0][0]).text == \
        "M. zadou mila, domicilié ADRESSE_1, conteste son licenciement par la société SOCIETE_A SAS"
    assert _masker().mask(TYPED_LINES[2][0]).text == TYPED_LINES[2][0]
    assert _masker().mask(TYPED_LINES[3][0]).text == TYPED_LINES[3][0]
    for text, names in CIVILITY + FIRST_NAME + COMPANY:
        # rules off: the 0.4.0 behaviour (the capitalised rules alone)
        assert _names(text) == [n for n in names if n == "Kerdalis"]


@pytest.mark.parametrize("value", ["1", "true", "", "yes"])
def test_the_switch_is_on_by_default(monkeypatch, value):
    monkeypatch.setenv(SWITCH, value)
    assert nm.lowercase_names() is True and config.lowercase_names() is True
    assert _masker().mask(TYPED_LINES[2][0]).text == TYPED_LINES[2][2]


def test_the_switch_is_read_at_each_call(monkeypatch):
    m = _masker()
    monkeypatch.setenv(SWITCH, "0")
    assert m.mask("mme claire dufresne conteste.").text == "mme claire dufresne conteste."
    monkeypatch.setenv(SWITCH, "1")
    assert m.mask("mme claire dufresne conteste.").text == "mme PERSONNE_A conteste."


def test_the_switch_also_turns_the_link_off(monkeypatch):
    m = _masker()
    assert m.mask("M. nelba samir conteste.").text == "M. PERSONNE_A conteste."
    monkeypatch.setenv(SWITCH, "0")
    assert m.mask("M. Samir a raison.").text == "M. PERSONNE_B a raison."  # the 0.4.0 link


class _Backend:
    """A fake model with fixed finds (surface, model label, score), wherever the surface occurs in a chunk."""

    name = "callable:lowercase"

    def __init__(self, finds=()):
        self.finds = list(finds)
        self.labels = {"company": "ORG", "person": "PERSON"}
        self.thresholds = {label: 0.4 for label in self.labels}

    def predict(self, chunks):
        out = []
        for ch in chunks:
            spans = []
            for surface, label, score in self.finds:
                i = ch.find(surface)
                while i >= 0:
                    spans.append(nr.NerSpan(i, i + len(surface), label, score))
                    i = ch.find(surface, i + 1)
            out.append(spans)
        return out


def _model_masker(finds=()) -> Masker:
    m = Masker(MemoryStore(), use_ner=False)
    m.use_ner = True  # no model in the test environment: the fake backend stands in for it
    m._backend = _Backend(finds)
    m._backend_tried = True
    return m


@pytest.mark.parametrize("text,names,masked", TYPED_LINES)
def test_model_mode_masks_the_typed_lines(text, names, masked):
    m = _model_masker()
    r = m.mask(text)
    assert m.mode.startswith("rules+ner") and r.text == masked


@pytest.mark.parametrize("text,names", CIVILITY[:10] + FIRST_NAME[:6] + COMPANY[:6])
def test_model_mode_keeps_the_lower_case_names(text, names):
    assert _names(text, _model_masker()) == names


def test_model_mode_and_a_model_find_on_the_same_name():
    m = _model_masker([("claire dufresne", "person", 0.9)])
    assert m.mask("mme claire dufresne conteste son licenciement.").text == "mme PERSONNE_A conteste son licenciement."


def test_plugged_recogniser_mode():
    m = Masker(MemoryStore(), ner=lambda text: [])
    assert m.mode == "rules+ner"
    assert m.mask(TYPED_LINES[3][0]).text == TYPED_LINES[3][2]


def test_english_output_does_not_depend_on_the_switch(monkeypatch):
    text = "Please ask mrs claire dufresne of durand sas to send the signed lease before the hearing on monday."
    monkeypatch.setenv(SWITCH, "0")
    off = Masker(MemoryStore(), use_ner=False, language="en").mask(text).text
    monkeypatch.setenv(SWITCH, "1")
    assert Masker(MemoryStore(), use_ner=False, language="en").mask(text).text == off


# ---------------------------------------------------------------------------
# The rules of names.py and the word lists
# ---------------------------------------------------------------------------


def _spans(text: str) -> list[tuple[str, str, str]]:
    return [(text[s.start:s.end], s.kind, s.rule) for s in nm.detect_names(text, lang="fr")]


def test_rule_names_and_priorities_are_those_of_the_capitalised_rules():
    text = "mme claire dufresne et jean dupont travaillent pour la société durand sas."
    by_rule = {s.rule: (text[s.start:s.end], s.kind, s.priority) for s in nm.detect_names(text, lang="fr")}
    assert by_rule["title"] == ("claire dufresne", "PERSON", 5)
    assert by_rule["first_name"] == ("jean dupont", "PERSON", 4)
    assert by_rule["legal_form"] == ("durand", "ORG", 6)


def test_no_span_without_a_lower_case_name_word(monkeypatch):
    """With capitals only the lower-case rules add nothing: the rule spans are those of 0.4.0."""
    text = "M. Thibault Mercadier et Jean Dupont travaillent pour la société Durand SAS."
    monkeypatch.setenv(SWITCH, "0")
    off = _spans(text)
    monkeypatch.setenv(SWITCH, "1")
    assert _spans(text) == off
    assert ("Thibault Mercadier", "PERSON", "title") in off and ("Jean Dupont", "PERSON", "first_name") in off


@pytest.mark.parametrize("form", ["conteste", "contestait", "contestent", "contesté", "licenciée", "plaide",
                                   "représente", "travaille", "perçoit", "reçoivent", "prend", "comprennent",
                                   "écrit", "produisent", "connaît", "vient", "tiennent", "met", "rend", "part",
                                   "ouvre", "vit", "conclut", "résout", "craint", "joint", "acquiert", "prévoit",
                                   "mangeons", "exigeait", "emploie", "paie", "appelle", "rejette", "achète",
                                   "finit", "finissent", "saisit", "agit", "choisi", "enverra", "acquiesce"])
def test_verb_forms_are_read_from_the_infinitives(form):
    assert lx.verb_form(fold_word(form)) == "form"


@pytest.mark.parametrize("form", ["a", "ont", "est", "sont", "était", "sera", "aura", "fait", "peut", "veut",
                                   "doit", "sait", "faut", "va"])
def test_auxiliary_forms(form):
    assert lx.verb_form(fold_word(form)) == "aux"


@pytest.mark.parametrize("word", ["contester", "plaider", "finir", "prendre", "recevoir", "écrire", "résumer"])
def test_infinitives(word):
    assert lx.verb_form(fold_word(word)) == "inf"


@pytest.mark.parametrize("word", ["dupont", "dufresne", "samir", "mila", "zadou", "mercadier", "durand", "martin",
                                   "karim", "sophie", "jean", "kervadec", "pradimont", "talvez", "garnier",
                                   "velmaire", "vincent", "laurent", "talvent", "brivanez"])
def test_names_are_no_verb_forms(word):
    assert lx.verb_form(word) == ""


def test_the_verb_file_has_every_section_and_no_misplaced_infinitive():
    v = lx.verbs()
    assert len(v["er"]) > 2000 and len(v["ir"]) > 150 and len(v["forms"]) > 5000 and len(v["auxiliaries"]) > 200
    assert all(w.endswith("er") for w in v["er"]) and all(w.endswith("ir") for w in v["ir"])
    sections = lx.read_sections("verbs_fr.txt")
    models = [line.partition(":")[0].strip() for line in sections["models"]]
    assert len(models) == len(set(models)) >= 30
    for model in models:
        assert sections.get(model), f"model {model} has no verb"


def test_the_word_file_has_its_sections():
    words = lx.lowercase_words()
    assert set(words) == {"function", "persons", "states", "words"}
    assert all(len(v) > 50 for v in words.values())
    assert "angulaire" in words["words"] and "bonbon" in words["words"]
    assert "seule" in words["states"] and "voisin" in words["persons"] and "quant" in words["function"]


@pytest.mark.parametrize("word,kind", [
    ("dupont", "oov"), ("karim", "first"), ("claire", "amb"), ("pierre", "amb"), ("marie", "amb"),
    ("petit", "common"), ("conteste", "verb"), ("angulaire", "plain"), ("président", "no"), ("le", "no"),
    ("seule", "no"), ("voisin", "no"), ("apparemment", "no"), ("martin-leroy", "first"), ("indexation", "plain"),
    ("susvisé", "verb"), ("lyon", "plain"), ("juridique", "plain"), ("contestait", "verb"),
    ("cohéritier", "no"), ("cogérante", "no"), ("démissionnaire", "no"), ("forclos", "no"), ("bis", "no"),
])
def test_word_classes(word, kind):
    w = nm._words(word)[0]
    assert nm._lc_kind(w) == kind


def test_the_lists_of_0_4_0_do_not_change():
    """Version 0.4.1 adds two files and reads them from the new rules only."""
    assert "conteste" not in lx.stopwords() and "angulaire" not in lx.common_words()
    assert "bonbon" not in nm._lists()[2] and "zadou" not in nm._lists()[4]
