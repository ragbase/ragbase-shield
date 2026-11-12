"""Engine: person and company rules, variants, dossier titles, whitelist protection. Invented names only."""
import pytest

from ragbase_shield.engine import Masker, MemoryStore, detect_names, entity_norm, parse_parties, person_norm, split_person
from ragbase_shield.engine.names import org_core, org_norm, org_variants, person_variants
from ragbase_shield.engine.normalize import fold, tokens
from ragbase_shield.engine.names import protected_intervals


def masked_names(text):
    """Names masked by a fresh masker (rules only): list of (kind, surface)."""
    r = Masker(MemoryStore(), use_ner=False).mask(text)
    return [(s.kind, s.value) for s in r.spans if s.kind in ("PERSON", "ORG")]


def registered(*items):
    store = MemoryStore()
    for kind, value in items:
        store.add(kind, value, entity_norm(kind, value))
    return Masker(store, use_ner=False)


# --- rules ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("text,name", [
    ("M. Jean-Pierre DELACOURT a signé.", "Jean-Pierre DELACOURT"),
    ("Mme Hélène Vasseur-Garnier est présente.", "Hélène Vasseur-Garnier"),
    ("Maître Sophie LERVIGNAC plaide.", "Sophie LERVIGNAC"),
    ("Me Gaëtan Morvillier plaide.", "Gaëtan Morvillier"),
    ("Monsieur de La Villemarqué est absent.", "de La Villemarqué"),
    ("Docteur Alain Prévost témoigne.", "Alain Prévost"),
    ("Mlle Inès d'Aubrac signe.", "Inès d'Aubrac"),
    ("Me N'Dongo et M. O'Brien.", "N'Dongo"),
    ("Mme Le Goff est gérante.", "Le Goff"),
    ("M. J.-P. Delacourt signe.", "J.-P. Delacourt"),
    ("monsieur Ravel a été reçu.", "Ravel"),
    ("M.Durand a signé.", "Durand"),
])
def test_titles(text, name):
    assert ("PERSON", name) in masked_names(text)


def test_title_keeps_title_in_clear():
    r = Masker(MemoryStore(), use_ner=False).mask("Madame Hélène VASSEUR et Maître Paul Rivière.")
    assert r.text == "Madame PERSONNE_A et Maître PERSONNE_B."


@pytest.mark.parametrize("text,name", [
    ("Thomas Ravel a été engagé le 1er mars.", "Thomas Ravel"),
    ("Le témoin Karim BENALI confirme.", "Karim BENALI"),
    ("Attendu que Pierre Martin conteste.", "Pierre Martin"),
    ("DUPONT Jean-Pierre, né le 3 mars 1970.", "DUPONT Jean-Pierre"),
    ("Nom, prénoms : FERRANDOU Lucien Marcel", "FERRANDOU Lucien Marcel"),
    ("Jean de La Fontaine est cité.", "Jean de La Fontaine"),
])
def test_first_name_rules(text, name):
    assert ("PERSON", name) in masked_names(text)


@pytest.mark.parametrize("text,name", [
    ("le salarié DURAND a été licencié", "DURAND"),
    ("les époux LECLERC demeurant", "LECLERC"),
    ("Mme Durand née VASSEUR", "VASSEUR"),
    ("Kofi ABRANTIE, demeurant à Paris", "Kofi ABRANTIE"),
    ("la dame Coulon et le sieur Bertin", "Coulon"),
])
def test_role_rules(text, name):
    assert ("PERSON", name) in masked_names(text)


def test_plural_titles():
    names = masked_names("Mmes Garnier et Perrin, MM. Rivière et Faure.")
    assert {n for _, n in names} == {"Garnier", "Perrin", "Rivière", "Faure"}


@pytest.mark.parametrize("text,name", [
    ("La société BRIVANOR LOGISTIQUE SAS, au capital", "BRIVANOR LOGISTIQUE"),
    ("Kervalon Conseil SARL et Optiveo SA ont signé.", "Kervalon Conseil"),
    ("la SAS Brivanor a conclu", "Brivanor"),
    ("la SCI Les Tilleuls de Saône, représentée", "Les Tilleuls de Saône"),
    ("la SCI LES TILLEULS DE SAÔNE, bailleresse", "LES TILLEULS DE SAÔNE"),
    ("la SCI du Moulin Vert", "Moulin Vert"),
    ("la société « Optiveo » est", "Optiveo"),
    ("le groupe Arkéane a racheté", "Arkéane"),
    ("La SARL Ferrandou & Fils livre.", "Ferrandou & Fils"),
    ("Nexalia S.A.S. et Kriva GmbH fusionnent.", "Nexalia"),
    ("Le cabinet d'avocats Morel Associés plaide.", "Morel Associés"),
    ("LERVIGNAC AVOCATS - 5 place Bellecour", "LERVIGNAC AVOCATS"),
    ("Dénomination ou raison sociale : QUANTORIVE", "QUANTORIVE"),
])
def test_company_rules(text, name):
    assert ("ORG", name) in masked_names(text)


def test_company_legal_form_stays_in_clear():
    r = Masker(MemoryStore(), use_ner=False).mask("Brivanor Logistique SAS et la SARL Kervalon.")
    assert r.text == "SOCIETE_A SAS et la SARL SOCIETE_B."


def test_et_does_not_join_two_companies():
    names = masked_names("La SCI Les Tilleuls de Saône et Kervalon Conseil SARL signent.")
    assert ("ORG", "Les Tilleuls de Saône") in names and ("ORG", "Kervalon Conseil") in names


@pytest.mark.parametrize("text", [
    "Attendu que la Cour de cassation a jugé.",
    "Monsieur le Président, Madame la Présidente, Mesdames et Messieurs,",
    "Le Conseil de prud'hommes de Lyon, section Commerce.",
    "Me voici. M. le Maire de Lyon. Sur sa demande. SUR SA DEMANDE.",
    "La Société s'engage à respecter le RGPD.",
    "France Travail, l'URSSAF, la CNIL et la Banque de France.",
    "Pierre qui roule n'amasse pas mousse. Rose et Blanche sont des couleurs.",
    "PAR CES MOTIFS, Déboute la demanderesse. DIT n'y avoir lieu.",
    "Lors de l'Assemblée Générale Ordinaire, l'AG a approuvé les comptes.",
    "Le Groupe de travail et la société civile se réunissent.",
    "La Directrice des Ressources Humaines et le Directeur Général Délégué.",
    "Saint-Étienne, Aix-en-Provence et Boulogne-Billancourt.",
    "Rendez-vous le Mardi 4 Mars à 10 heures. Fait à Paris, le 3 juin.",
])
def test_no_false_names(text):
    assert masked_names(text) == []


def test_court_city_stays_clear_but_party_city_name_is_not_confused():
    r = Masker(MemoryStore(), use_ner=False).mask(
        "Le Tribunal judiciaire de Lyon et la Cour d'appel d'Aix-en-Provence. Mme Nadia Haddad, née à Lyon, demeurant à Lyon.")
    assert "Tribunal judiciaire de Lyon" in r.text and "Cour d'appel d'Aix-en-Provence" in r.text
    assert "née à Lyon" in r.text and "demeurant à Lyon" in r.text
    assert "Haddad" not in r.text


def test_protected_intervals_cover_court_city_and_articles():
    text = "Conseil de prud'hommes de Boulogne-Billancourt ; articles L1234-9 et R. 1455-6 ; loi n° 78-17."
    f = fold(text)
    prot = protected_intervals(text, f, tokens(f.text))
    for part in ("Boulogne-Billancourt", "L1234-9", "R. 1455-6", "78-17"):
        i = text.index(part)
        assert prot.overlaps(i, i + len(part)), part


# --- splitting, norms, variants --------------------------------------------------------------------


@pytest.mark.parametrize("value,firsts,surname", [
    ("Jean-Pierre Dupont", ["Jean-Pierre"], ["Dupont"]),
    ("DUPONT Jean-Pierre", ["Jean-Pierre"], ["DUPONT"]),
    ("Jean-Pierre DE LA FONTAINE", ["Jean-Pierre"], ["DE", "LA", "FONTAINE"]),
    ("Dupont Jean-Pierre", ["Jean-Pierre"], ["Dupont"]),
    ("M. Paul Blanc", ["Paul"], ["Blanc"]),
    ("Arnaud de Montclar", ["Arnaud"], ["de", "Montclar"]),
    ("J.-P. Dupont", ["J.-P."], ["Dupont"]),
    ("Dupont", [], ["Dupont"]),
])
def test_split_person(value, firsts, surname):
    assert split_person(value) == (firsts, surname)


def test_person_norm_is_order_case_and_hyphen_free():
    assert person_norm("DUPONT Jean-Pierre") == person_norm("Jean-Pierre Dupont") == person_norm("M. Jean-Pierre DUPONT") \
        == person_norm("Jean Pierre DUPONT") == "jean pierre dupont"


def test_org_core_and_norm():
    assert org_core("ACME SAS") == "ACME"
    assert org_core("la société BRIVANOR LOGISTIQUE SAS") == "BRIVANOR LOGISTIQUE"
    assert org_norm("S.A.S. Optiveo") == org_norm("Optiveo SA") == "optiveo"


def test_variants_flags():
    v = {(x.tokens, x.need) for x in person_variants("Louise Martin")}
    assert (("martin",), "title") in v  # "Martin" is a first name: needs a title alone
    v = {(x.tokens, x.need) for x in person_variants("Hélène Vasseur-Garnier")}
    assert (("vasseur", "garnier"), "") in v
    v = {(x.tokens, x.need) for x in org_variants("Horizon SARL")}
    assert (("horizon",), "org") in v  # common word: needs "société"/a legal form or upper case


# --- variants in text (registered names) -------------------------------------------------------------


def test_registered_person_variants():
    m = registered(("PERSON", "Jean-Pierre Dupont"))
    text = ("Jean-Pierre Dupont, DUPONT Jean-Pierre, J.-P. Dupont, JP Dupont, J. Dupont, M. Dupont, "
            "Maître Dupont, DUPONT, dupont.\nJean-Pierre\nDupont, Jean Pierre DUPONT")
    out = m.mask(text).text
    assert "Dupont" not in out and "DUPONT" not in out and "dupont" not in out
    assert out.count("PERSONNE_A") == 11


def test_surname_that_is_a_word_needs_title_or_first_name():
    m = registered(("PERSON", "Paul Blanc"))
    out = m.mask("M. Blanc et Paul BLANC signent ; un chèque en blanc ; BLANC ; le Mont Blanc.").text
    assert out == "M. PERSONNE_A et PERSONNE_A signent ; un chèque en blanc ; BLANC ; le Mont Blanc."


def test_surname_that_is_a_first_name_needs_title_unless_upper_case():
    m = registered(("PERSON", "Louise Martin"))
    out = m.mask("Mme Martin, MARTIN, Martin est absent et la Saint-Martin.").text
    assert out == "Mme PERSONNE_A, PERSONNE_A, Martin est absent et la Saint-Martin."


def test_registered_surname_not_matched_inside_compound_name():
    m = registered(("PERSON", "Jean-Pierre Dupont"))
    out = m.mask("M. Dupont et Mme Dupont-Morvanti.").text
    assert out.startswith("M. PERSONNE_A et Mme ")
    assert "PERSONNE_A-" not in out


def test_registered_company_variants():
    m = registered(("ORG", "ACME SAS"))
    out = m.mask("ACME SAS, ACME, la société Acme, la SAS ACME, Acme.").text
    assert "ACME" not in out and "Acme" not in out


def test_company_with_common_word_name():
    m = registered(("ORG", "Horizon SARL"))
    out = m.mask("La société Horizon et HORIZON signent ; un horizon lointain ; Horizon SARL.").text
    # the registered value "Horizon SARL" is matched whole, so restore gives it back exactly
    assert out == "La société SOCIETE_A et SOCIETE_A signent ; un horizon lointain ; SOCIETE_A."


def test_first_name_alone_in_greeting_and_signature():
    m = registered(("PERSON", "Jean-Pierre Delacourt"))
    out = m.mask("Bonjour Jean-Pierre,\nmerci.\nCordialement,\nJean-Pierre").text
    assert out == "Bonjour PERSONNE_A,\nmerci.\nCordialement,\nPERSONNE_A"


def test_first_name_alone_skipped_when_two_people_share_it():
    # R1 (CL-04b): never guess which of the two, but never leave the first name in clear either: it gets its own code
    m = registered(("PERSON", "Yasmine Belkacem"), ("PERSON", "Yasmine Durand"))
    out = m.mask("Yasmine, notre DRH, viendra.").text
    assert "Yasmine" not in out and "PERSONNE_A" not in out and "PERSONNE_B" not in out


def test_known_person_found_by_rules_links_variants_in_same_text():
    r = Masker(MemoryStore(), use_ner=False).mask("M. Jean-Pierre DELACOURT signe. DELACOURT confirme. J.-P. Delacourt paraphe.")
    assert r.text == "M. PERSONNE_A signe. PERSONNE_A confirme. PERSONNE_A paraphe."
    assert len(r.new_entities) == 1


def test_surname_before_full_name_gets_the_same_code():
    r = Masker(MemoryStore(), use_ner=False).mask("M. Delacourt écrit. Plus loin : Jean-Pierre Delacourt, président.")
    assert r.text == "M. PERSONNE_A écrit. Plus loin : PERSONNE_A, président."


# --- dossier titles ---------------------------------------------------------------------------------


@pytest.mark.parametrize("title,expected", [
    ("Dupont c. ACME SAS", [("PERSON", "Dupont"), ("ORG", "ACME SAS")]),
    ("ACME SAS contre Jean-Pierre Dupont", [("ORG", "ACME SAS"), ("PERSON", "Jean-Pierre Dupont")]),
    ("Brivanor Logistique v. Kervalon Conseil", [("ORG", "Brivanor Logistique"), ("ORG", "Kervalon Conseil")]),
    ("M. et Mme Martin c. SCI Les Tilleuls", [("PERSON", "Martin"), ("ORG", "SCI Les Tilleuls")]),
    ("Haddad c. Brivanor Logistique SAS et autres", [("PERSON", "Haddad"), ("ORG", "Brivanor Logistique SAS")]),
    ("Société Optiveo c. M. Paul Blanc et Mme Louise Martin",
     [("ORG", "Optiveo"), ("PERSON", "Paul Blanc"), ("PERSON", "Louise Martin")]),
    ("DUPONT / ACME", [("PERSON", "DUPONT"), ("ORG", "ACME")]),
    ("Martin et Fils SARL c. Durand", [("ORG", "Martin et Fils SARL"), ("PERSON", "Durand")]),
])
def test_parse_parties(title, expected):
    assert parse_parties(title) == expected


def test_parse_parties_empty():
    assert parse_parties("") == []
    assert parse_parties("   ") == []


@pytest.mark.parametrize("title,expected", [
    ("Dossier Ferracci-Daubel", [("PERSON", "Ferracci-Daubel")]),
    ("Haddad c. Brivanor - correspondance client", [("PERSON", "Haddad"), ("PERSON", "Brivanor")]),
    ("Kervalon Conseil - contrat Ravel", [("ORG", "Kervalon Conseil")]),
    ("Haddad c. Brivanor (appel)", [("PERSON", "Haddad"), ("PERSON", "Brivanor")]),
    ("2026-04 : Haddad c. Brivanor", [("PERSON", "Haddad"), ("PERSON", "Brivanor")]),
    ("Affaire Dupont c. ACME SAS", [("PERSON", "Dupont"), ("ORG", "ACME SAS")]),
    ("la société Optiveo c. M. Blanc", [("ORG", "Optiveo"), ("PERSON", "Blanc")]),
    ("Optiveo SAS en liquidation c. Durand", [("ORG", "Optiveo SAS"), ("PERSON", "Durand")]),
    ("dossiers clients", []),
    ("Dossier Haddad c/ Brivanor - jugement du 18 septembre", [("PERSON", "Haddad"), ("PERSON", "Brivanor")]),
])
def test_parse_parties_drops_title_descriptions(title, expected):
    assert parse_parties(title) == expected


def test_has_party_separator():
    from ragbase_shield.engine import has_party_separator
    assert has_party_separator("Dupont c. ACME SAS")
    assert has_party_separator("ACME contre Durand")
    assert not has_party_separator("Dossier Ferracci-Daubel")
    assert not has_party_separator("Vasseur-Garnier")


def test_detect_names_returns_rule_spans():
    spans = detect_names("Mme Nadia HADDAD et la société BRIVANOR SAS")
    assert {("PERSON", "Nadia HADDAD"), ("ORG", "BRIVANOR")} <= {(s.kind, "Mme Nadia HADDAD et la société BRIVANOR SAS"[s.start:s.end]) for s in spans}


def test_signature_columns_are_two_people():
    store = MemoryStore()
    text = ("Mme Mathilde QUÉRÉ-LANSAC et M. Paul BLANC signent.\n"
            "M. QUÉRÉ-LANSAC                    P. BLANC\nSigné :\tM. Jean DURAND\tMme Louise MARTIN")
    out = Masker(store, use_ner=False).mask(text).text
    assert all("   " not in e.value and "\t" not in e.value for e in store.all())
    for word in ("QUÉRÉ", "BLANC", "DURAND", "MARTIN"):
        assert word not in out
    assert len([e for e in store.all() if e.kind == "PERSON"]) == 4
