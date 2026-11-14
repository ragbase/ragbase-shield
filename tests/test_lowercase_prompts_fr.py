"""v0.4.1, round 2: prompts that lawyers type in lower case, beyond a civility and a first name.

E: a postal address typed in lower case ("12 rue des glycines, 69007 lyon"). 0.4.0 masks the same address with
capitals; with no capital it stayed readable. The guards: a street type that is also an ordinary word needs a home
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
    ("m. nona hakim, domicilié 12 rue des glycines, 69007 lyon, conteste son licenciement",
     ["12 rue des glycines, 69007 lyon"], "m. PERSONNE_A, domicilié ADRESSE_1, conteste son licenciement"),
    ("il habite au 5 avenue victor hugo 75016 paris",
     ["5 avenue victor hugo 75016 paris"], "il habite au ADRESSE_1"),
    ("monsieur azzouni hadi habite 12 rue de la paix 75002 paris",
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
    "M. Hakim, domicilié 12 rue des Glycines, 69007 Lyon, conteste son licenciement.",
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
        # 0.4.0: an address with no capital stays readable; one capitalised part may keep its 0.4.0 mask
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
