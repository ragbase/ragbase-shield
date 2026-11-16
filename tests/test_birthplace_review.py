"""Engine 0.4.4: the birth place fix, review fixes (second pass).

1. (high) A town inside a known name spread into the courts, like the place of birth before the fix. A title party
   that is a public body ("Mercadier c. Métropole de Lyon") was stored as a person, and its town then gave
   « cour d'appel PERSONNE_B », « Fait à PERSONNE_B », also in another dossier. A company whose name holds a town
   ("SAS Lyon Ascenseurs") gave « cour d'appel de SOCIETE_A »: the dictionary pass of the masker kept the courts,
   but the last check (``Masker.scan``) did not, and « Fait à Lyon », « Ville : Lyon » were masked by both.
2. (medium) Birth contexts that 0.4.2 and 0.4.3 masked only through the spread: the detector reads them now.
3. (medium, F0) A weak identifier (3 to 5 digits) is masked again right after an identifier word.

Every name, town of birth, number and title here is invented for these tests."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from ragbase_shield import claude_tab, kept, service, vault
from ragbase_shield.engine import Masker, MemoryStore, entity_norm, parse_parties
from ragbase_shield.engine import names as nm

COURTS = ("Le conseil de prud'hommes de Lyon. La cour d'appel de Lyon. Fait à Lyon. Ville : Lyon. "
          "Le tribunal judiciaire de Paris a jugé. La cour d'appel de Paris. Fait à Paris. "
          "Le tribunal judiciaire de Valence. Fait à Valence.")
TEXT = "M. Thibault Mercadier conteste. " + COURTS


def _masker(store=None) -> Masker:
    return Masker(store if store is not None else MemoryStore(), locale="fr", language="auto", use_ner=False,
                  replacement="codes")


def _folder(root: Path, name: str, files: dict[str, str]) -> Path:
    f = root / "cabinet" / name
    f.mkdir(parents=True)
    for fname, text in files.items():
        p = f / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return f


def _read_all(code: str) -> dict[str, str]:
    return {d["masked_name"]: service.read_document(code, d["id"])["text"].strip()
            for d in service.list_documents(code)}


# ============================================================ 1. title parties: public bodies are no parties

@pytest.mark.parametrize("title", ["Mercadier c. Métropole de Lyon", "Mercadier c. Ville de Paris",
                                   "Mercadier c. Pôle emploi Paris", "Mercadier c. Mairie de Valence",
                                   "Mercadier c. Centre hospitalier de Valence", "Mercadier c. CPAM du Rhône",
                                   "Mercadier c. URSSAF Rhône-Alpes", "Mercadier c. France Travail",
                                   "Mercadier c. l'État"])
def test_a_public_body_of_the_title_is_no_party(title):
    assert parse_parties(title) == [("PERSON", "Mercadier")], parse_parties(title)


def test_people_and_companies_of_a_title_are_still_parties():
    assert parse_parties("Mercadier c. SAS Lyon Ascenseurs") == [("PERSON", "Mercadier"),
                                                                  ("ORG", "SAS Lyon Ascenseurs")]
    assert parse_parties("Ravenel c. Lyon Ascenseurs") == [("PERSON", "Ravenel"), ("ORG", "Lyon Ascenseurs")]
    assert parse_parties("Mercadier c. Florence Martin") == [("PERSON", "Mercadier"), ("PERSON", "Florence Martin")]
    assert parse_parties("Mercadier c. Nancy Durand") == [("PERSON", "Mercadier"), ("PERSON", "Nancy Durand")]
    assert nm.is_public_body("Métropole de Lyon") and not nm.is_public_body("Ateliers Brunelac SAS")
    # one word that is also a town may be a surname: still a party (its town stays in clear in the courts)
    assert parse_parties("Dupont c. Laval") == [("PERSON", "Dupont"), ("PERSON", "Laval")]


@pytest.mark.parametrize("title", ["Mercadier c. Métropole de Lyon", "Mercadier c. Ville de Paris",
                                   "Mercadier c. Pôle emploi Paris", "Mercadier c. Mairie de Valence",
                                   "Mercadier c. SAS Lyon Ascenseurs", "Mercadier c. Paris"])
def test_the_title_keeps_every_court_and_town_in_clear(tmp_path, title):
    code = service.add_dossier(_folder(tmp_path, title, {"a.txt": TEXT + "\n"}))["code"]
    service.scan_dossier(code)
    text = _read_all(code)["a.txt"]
    assert text == "M. PERSONNE_A conteste. " + COURTS, text


def test_another_dossier_gets_no_town_of_a_title(tmp_path):
    for title in ("Mercadier c. Métropole de Lyon", "Mercadier c. SAS Lyon Ascenseurs"):
        code = service.add_dossier(_folder(tmp_path / title[-4:], title, {"a.txt": TEXT + "\n"}))["code"]
        service.scan_dossier(code)
    f2 = _folder(tmp_path, "Durand c. Brunelac", {"b.txt": "Mme Odile Durand conteste. La cour d'appel de Lyon a "
                                                         "jugé. Le tribunal judiciaire de Paris. Fait à Valence.\n"})
    c2 = service.add_dossier(f2)["code"]
    service.scan_dossier(c2)
    text = _read_all(c2)["b.txt"]
    assert text == ("Mme PERSONNE_A conteste. La cour d'appel de Lyon a jugé. Le tribunal judiciaire de Paris. "
                    "Fait à Valence."), text
    assert {e["value"] for e in service.entities(c2)} == {"Odile Durand", "Brunelac"}
    answer = "La cour d'appel de Lyon. Le tribunal judiciaire de Paris. Fait à Lyon."
    assert service.default().guard_output(answer, c2) == answer


# ============================================================ 1. a town inside a known name (any source)

@pytest.mark.parametrize("kind,value", [("ORG", "SAS Lyon Ascenseurs"), ("ORG", "Lyon Ascenseurs"),
                                        ("PERSON", "Métropole de Lyon"), ("PERSON", "Pôle emploi Paris")])
def test_the_masker_and_its_last_check_leave_the_town_of_a_name(kind, value):
    """``Métropole de Lyon`` stored as a PERSON is what a vault of 0.4.1 to 0.4.3 may hold (old title party)."""
    store = MemoryStore()
    store.add(kind, value, entity_norm(kind, value))
    m = _masker(store)
    assert m.mask(COURTS).text == COURTS
    assert m.scan(COURTS) == []


def test_a_company_found_in_a_document_keeps_the_courts_in_every_document(tmp_path):
    f = _folder(tmp_path, "Dossier Ravenel", {
        "a.txt": "La société Lyon Ascenseurs SAS a licencié M. Paul Ravenel. Le conseil de prud'hommes de Lyon. "
                 "La cour d'appel de Lyon. Fait à Lyon. Ville : Lyon.\n",
        "b.txt": "Le tribunal judiciaire de Lyon. Fait à Lyon le 3 mai.\nLyon, le 4 juin 2025.\n"})
    code = service.add_dossier(f)["code"]
    service.scan_dossier(code)
    docs = _read_all(code)
    assert docs["a.txt"] == ("La société SOCIETE_A SAS a licencié M. PERSONNE_A. Le conseil de prud'hommes de Lyon. "
                             "La cour d'appel de Lyon. Fait à Lyon. Ville : Lyon."), docs["a.txt"]
    assert docs["b.txt"] == "Le tribunal judiciaire de Lyon. Fait à Lyon le 3 mai.\nLyon, le 4 juin 2025.", docs
    assert service.default().guard_output("La cour d'appel de Lyon. Fait à Lyon.", code) == \
        "La cour d'appel de Lyon. Fait à Lyon."
    # the company itself is still masked, whole and by its own name
    assert service.default().guard_output("Lyon Ascenseurs a signé.", code) == "SOCIETE_A a signé."


def test_a_person_whose_surname_is_a_town_is_still_masked():
    m = _masker()
    m.mask("M. Paul Valence, salarié, conteste.")
    out = m.mask("M. Valence a signé. Paul Valence est présent. Le tribunal judiciaire de Valence. Fait à Valence.")
    assert out.text == ("M. PERSONNE_A a signé. PERSONNE_A est présent. Le tribunal judiciaire de Valence. "
                        "Fait à Valence."), out.text


@pytest.fixture
def plugin_env():
    saved_env = dict(os.environ)
    saved_picker = claude_tab.PICKER
    yield
    service.reset()
    vault.KEY_STORE = None
    claude_tab.PICKER = saved_picker
    os.environ.clear()
    os.environ.update(saved_env)


def test_the_plugin_folder_labels_and_sub_folder_party(tmp_path, plugin_env):
    """Plugin flow (protect_folder) with a sub-folder « Ravenel c. Lyon Ascenseurs »: the folder « Lyon - pièces »
    and « Ville : Lyon » stay in clear; the company is masked."""
    claude_tab.lock_settings(tmp_path / "data")
    f = _folder(tmp_path, "Mercadier c. Brunelac", {
        "a.txt": "M. Thibault Mercadier conteste. La cour d'appel de Lyon a jugé. Fait à Lyon. Ville : Lyon.\n",
        "Lyon - pièces/attestation Lyon.txt": "Fait à Lyon.\n",
        "Ravenel c. Lyon Ascenseurs/note.txt": "Note. Lyon, le 4 juin 2025. Lyon Ascenseurs a écrit.\n"})
    s = service.default()
    s.protect_folder(f)
    code = s.list_dossiers()[0]["code"]
    assert s.wait_reading(code, 60)
    out = {x.get("masked_path"): s.read_document(code, x["id"])["text"].strip() for x in s.list_documents(code)}
    assert out["a.txt"] == "M. PERSONNE_A conteste. La cour d'appel de Lyon a jugé. Fait à Lyon. Ville : Lyon.", out
    assert out["Lyon - pièces/attestation Lyon.txt"] == "Fait à Lyon.", out
    note = next(v for k, v in out.items() if k.endswith("/note.txt"))
    assert note == "Note. Lyon, le 4 juin 2025. SOCIETE_A a écrit.", out
    assert any(k.endswith("c. SOCIETE_A/note.txt") for k in out), out
    assert s.guard_output("La cour d'appel de Lyon. LYON.", code) == "La cour d'appel de Lyon. LYON."


def test_kept_sets_before_the_review_are_not_used():
    assert kept.RULES_REVISION not in ("0.4.4-r1", "0.4.4-r2", "0.4.4-r3")


# ============================================================ 2. wider birth contexts (detector, not spread)

BIRTH_FORMS = [
    "Date et lieu de naissance : 03/03/1980, {T}", "Date et lieu de naissance : 03/03/1980 - {T}",
    "Naissance : {T}, 3 mars 1980", "Ville de naissance : {T}", "Lieu et date de naissance : {T}, le 3 mars 1980",
    "M. Paul Ravenel est originaire de {T}, où il est né.", "M. Paul Ravenel, né le 3 mars 1980 dans la ville de {T}.",
    "Date of birth: 3 March 1980, {T}", "DOB: 03/03/1980 POB: {T}", "M. Paul Ravenel a vu le jour à {T}.",
    "| Nom | Né le | À |\n|---|---|---|\n| Ravenel | 03/03/1980 | {T} |", "Sa naissance à {T} en 1980.",
]


@pytest.mark.parametrize("town", ["Lyon", "Aix-en-Provence", "Le Havre", "La Rochelle", "L'Isle-Adam",
                                  "Saint-Étienne"])
@pytest.mark.parametrize("form", BIRTH_FORMS)
def test_more_birth_contexts_are_masked_alone(town, form):
    out = _masker().mask(form.replace("{T}", town)).text
    assert "LIEU_1" in out and town not in out, out


def test_a_town_in_lower_case_after_ne_a_is_masked_when_the_list_knows_it():
    for txt in ("M. Paul Ravenel, né à lyon.", "M. Paul Ravenel, né le 3 mars 1980 à lyon."):
        out = _masker().mask(txt).text
        assert "LIEU_1" in out and "lyon" not in out, out


def test_the_place_after_any_birth_date_of_a_table():
    m = _masker()
    m.mask("Mme Lise Ravenel, née le 12/03/1950 à Brest.")
    out = m.mask("## Arbre familial\n\n| Nom | Naissance |\n|---|---|\n| Lise Ravenel | 12/03/1950 à Crest |\n").text
    assert "NAISSANCE_1 à LIEU_2" in out and "Crest" not in out, out


@pytest.mark.parametrize("txt", ["Elle a donné naissance à Lucie en 2010.", "Il est originaire de Lyon.",
                                 "Le 03/03/1980 à Lyon, la société a signé.", "Né le 3 mars 1980, Paul Ravenel a signé.",
                                 "La cour d'appel de Lyon a jugé. Fait à Lyon, le 2 novembre 2026.",
                                 "| Nom | Ville |\n|---|---|\n| Ravenel | Lyon |",
                                 "Nom de naissance : Durand\nPrénom : Odile"])
def test_no_birth_place_outside_a_birth_context(txt):
    out = _masker().mask(txt).text
    assert "LIEU" not in out, out


def test_the_wider_contexts_never_spread():
    m = _masker()
    m.mask("Date et lieu de naissance : 03/03/1980, Lyon")
    out = m.mask("La cour d'appel de Lyon a jugé. Fait à Lyon.").text
    assert out == "La cour d'appel de Lyon a jugé. Fait à Lyon.", out


# ============================================================ 3. weak identifiers after an identifier word

def test_a_weak_identifier_is_masked_after_an_identifier_word():
    m = _masker()
    m.mask("Matricule : 45821. M. Paul Ravenel.")
    out = m.mask("Le salarié n° 45821 a été licencié. Il a perçu 45821 euros. L'article n° 45821. "
                 "Matricule 45821.").text
    assert out == ("Le salarié n° MATRICULE_1 a été licencié. Il a perçu 45821 euros. L'article n° 45821. "
                   "Matricule MATRICULE_1."), out


def test_a_weak_toque_never_spreads_to_an_article():
    m = _masker()
    m.mask("Me Claire Ferrandon, toque n° 1234.")
    out = m.mask("L'article 1234 du code civil. Montant : 1234 euros. Pièce n° 1234. Vu la note (T. 4).").text
    assert out == "L'article 1234 du code civil. Montant : 1234 euros. Pièce n° 1234. Vu la note (T. 4).", out
    assert re.search(r"IDENT_1", m.mask("Toque n° 1234.").text)
