"""Engine: Masker.mask / unmask / scan, keep-clear, escaping, codes, NER hook, speed. Synthetic data only."""
import re
import time
from pathlib import Path

import pytest

from ragbase_shield.engine import (
    CODE_RE,
    KINDS,
    UNMASK_RE,
    Entity,
    Masker,
    MaskResult,
    MemoryStore,
    Span,
    detect_structured,
    entity_norm,
    escape_codes,
    make_code,
    normalize,
)
from ragbase_shield.engine.detectors import luhn_check_digit, nir_key

DOCS = Path(__file__).parent / "fixtures" / "docs"

SAMPLE = (
    "Entre la société BRIVANOR LOGISTIQUE SAS, représentée par Monsieur Jean-Pierre DELACOURT, "
    "et Madame Hélène VASSEUR-GARNIER, née le 3 mai 1975, demeurant 4 allée des Peupliers, 71000 Mâcon, "
    "tél. 06 39 98 12 34, h.vasseur@exemple-mail.fr, IBAN FR76 3000 6000 0112 3456 7890 189. "
    "Le Tribunal judiciaire de Lyon et l'URSSAF ; article L1234-9 du Code du travail."
)


def codes_in(text):
    return {m.group() for m in UNMASK_RE.finditer(text)}


def new_masker(**kw):
    kw.setdefault("use_ner", False)
    return Masker(MemoryStore(), **kw)


# --- mask --------------------------------------------------------------------------------------------


def test_mask_basic_and_result_types():
    m = new_masker()
    r = m.mask(SAMPLE)
    assert isinstance(r, MaskResult)
    assert r.text == (
        "Entre la société SOCIETE_A SAS, représentée par Monsieur PERSONNE_A, "
        "et Madame PERSONNE_B, née le NAISSANCE_1, demeurant ADRESSE_1, "
        "tél. TEL_1, EMAIL_1, IBAN IBAN_1. "
        "Le Tribunal judiciaire de Lyon et l'URSSAF ; article L1234-9 du Code du travail."
    )
    assert all(isinstance(s, Span) and SAMPLE[s.start:s.end] == s.value for s in r.spans)
    assert {e.code for e in r.new_entities} == codes_in(r.text)
    assert all(isinstance(e, Entity) and e.norm for e in r.new_entities)


def test_mask_empty_and_plain_text():
    m = new_masker()
    assert m.mask("").text == ""
    plain = "Le contrat est conclu pour une durée de deux ans."
    r = m.mask(plain)
    assert r.text == plain and r.spans == [] and r.new_entities == []


def test_codes_are_stable_across_calls_and_new_entities_only_once():
    m = new_masker()
    r1 = m.mask("M. Jean-Pierre DELACOURT, IBAN FR76 3000 6000 0112 3456 7890 189.")
    r2 = m.mask("Plus tard, DELACOURT a écrit. IBAN : FR7630006000011234567890189.")
    assert r1.text == "M. PERSONNE_A, IBAN IBAN_1."
    assert r2.text == "Plus tard, PERSONNE_A a écrit. IBAN : IBAN_1."
    assert len(r1.new_entities) == 2 and r2.new_entities == []


def test_one_code_per_person_with_variants():
    m = new_masker()
    r = m.mask("Jean-Pierre DELACOURT signe. DELACOURT Jean-Pierre paraphe. M. Delacourt et J.-P. Delacourt.")
    assert codes_in(r.text) == {"PERSONNE_A"}


def test_structured_beats_names():
    m = new_masker()
    r = m.mask("Le site www.paul-martin-exemple.fr et l'adresse 12 rue Paul Martin, 69003 Lyon.")
    assert r.text == "Le site SITE_1 et l'adresse ADRESSE_1."


def test_escape_real_text_that_looks_like_a_code():
    m = new_masker()
    r = m.mask("Le fichier PERSONNE_A et la cote EMAIL_1, DOSSIER_3 ; M. Paul Rivière.")
    assert r.text == "Le fichier PERSONNE-A et la cote EMAIL-1, DOSSIER_3 ; M. PERSONNE_A."
    assert m.unmask(r.text) == "Le fichier PERSONNE-A et la cote EMAIL-1, DOSSIER_3 ; M. Paul Rivière."
    assert escape_codes("SOCIETE_B et RG_12") == "SOCIETE-B et RG-12"


def test_whitelist_and_keep_courts_clear():
    m = new_masker()
    text = ("Le Conseil de prud'hommes de Boulogne-Billancourt, la Cour d'appel de Versailles, le Conseil d'État, "
            "la CNIL, l'AMF, l'ACPR, France Travail, le Code civil, l'article L1234-9 et le RGPD.")
    assert m.mask(text).text == text


# --- keep clear ------------------------------------------------------------------------------------


def test_keep_clear_by_entity_norm():
    store = MemoryStore()
    m = Masker(store, use_ner=False)
    r = m.mask("M. Paul Rivière et Mme Agnès Tissandier.")
    riviere = next(e for e in r.new_entities if "Rivi" in e.value)
    store.keep_clear(riviere.norm)
    assert m.mask("M. Paul Rivière et Mme Agnès Tissandier. Rivière confirme.").text == \
        "M. Paul Rivière et Mme PERSONNE_B. Rivière confirme."


def test_keep_clear_by_term_before_detection():
    store = MemoryStore()
    store.keep_clear(normalize("Brivanor"))
    m = Masker(store, use_ner=False)
    r = m.mask("La société Brivanor SAS et M. Paul Rivière.")
    assert r.text == "La société Brivanor SAS et M. PERSONNE_A."
    assert all(e.kind != "ORG" for e in r.new_entities)


# --- unmask ----------------------------------------------------------------------------------------


def test_unmask_round_trip_and_punctuation():
    m = new_masker()
    r = m.mask(SAMPLE)
    assert m.unmask(r.text) == SAMPLE
    answer = "**PERSONNE_A** (TEL_1), PERSONNE_B's file; « SOCIETE_A » et _IBAN_1_."
    assert m.unmask(answer) == ("**Jean-Pierre DELACOURT** (06 39 98 12 34), Hélène VASSEUR-GARNIER's file; "
                                "« BRIVANOR LOGISTIQUE » et _FR76 3000 6000 0112 3456 7890 189_.")


def test_unmask_report_lists_unknown_and_invented_codes():
    m = new_masker()
    m.mask("M. Paul Rivière.")
    text, unknown = m.unmask_report("PERSONNE_A et PERSONNE_Q puis SIRET_7, PERSONNE_Q encore, DOSSIER_2.")
    assert text == "Paul Rivière et PERSONNE_Q puis SIRET_7, PERSONNE_Q encore, DOSSIER_2."
    assert unknown == ["PERSONNE_Q", "SIRET_7"]


def test_unmask_exact_codes_only():
    m = new_masker()
    m.mask("M. Paul Rivière.")
    for loose in ("PERSONNE A", "personne_a", "PERSONNE-A", "XPERSONNE_A", "PERSONNE_AB"):
        assert m.unmask(loose) == loose
    # A code glued to digits is still a code: the masker writes "PERSONNE_A2026" for "Rivière2026".
    assert m.unmask("PERSONNE_A1") == "Paul Rivière1"


def test_unmask_does_not_double_legal_form_or_title():
    store = MemoryStore()
    store.add("ORG", "ACME SAS", entity_norm("ORG", "ACME SAS"))
    store.add("PERSON", "Maître Sophie Lervignac", entity_norm("PERSON", "Maître Sophie Lervignac"))
    m = Masker(store, use_ner=False)
    assert m.unmask("SOCIETE_A SAS et la société SOCIETE_A") == "ACME SAS et la société ACME SAS"
    assert m.unmask("Maître PERSONNE_A et PERSONNE_A") == "Maître Sophie Lervignac et Maître Sophie Lervignac"


def test_english_locale_codes():
    store = MemoryStore(locale="en")
    m = Masker(store, locale="en", use_ner=False)
    r = m.mask("M. Paul Rivière, IBAN FR76 3000 6000 0112 3456 7890 189, NIR 1 80 03 75 112 005 %02d"
               % nir_key("1800375112005"))
    assert "PERSON_A" in r.text and "IBAN_1" in r.text and "SSN_1" in r.text
    assert m.unmask(r.text).startswith("M. Paul Rivière")


# --- registered entities with a store that keeps its own norms ---------------------------------------


class PlainNormStore(MemoryStore):
    """Like the vault: register() normalises with plain normalize(), not with entity_norm()."""

    def register(self, kind, value):
        return self.add(kind, value, normalize(value))


def test_registered_values_found_whatever_norm_the_store_used():
    store = PlainNormStore()
    store.register("PERSON", "DUPONT Jean-Pierre")
    store.register("IBAN", "FR76 3000 6000 0112 3456 7890 189")
    store.register("ORG", "ACME SAS")
    m = Masker(store, use_ner=False)
    r = m.mask("Jean-Pierre Dupont paie depuis FR7630006000011234567890189 pour la société Acme.")
    assert r.text == "PERSONNE_A paie depuis IBAN_1 pour la société SOCIETE_A."
    assert r.new_entities == []


def test_custom_term_of_any_kind_is_masked():
    store = MemoryStore()
    store.add("ORG", "Projet Hermine", entity_norm("ORG", "Projet Hermine"))
    store.add("ORG", "Kervalonix", entity_norm("ORG", "Kervalonix"))
    store.add("ID_CODE", "DOS-77-AB", entity_norm("ID_CODE", "DOS-77-AB"))
    m = Masker(store, use_ner=False)
    assert m.mask("Le Projet Hermine, réf DOS-77-AB, avec kervalonix.").text == "Le SOCIETE_A, réf IDENT_1, avec SOCIETE_B."
    # every word of "projet hermine" is a common word or a first name: lower case is not matched
    assert m.mask("un projet hermine").text == "un projet hermine"


# --- scan (canary) -------------------------------------------------------------------------------------


def test_scan_known_values_variants_line_breaks_and_ocr():
    m = new_masker()
    m.mask(SAMPLE)
    leaked = "Réponse : Jean-Pierre\nDelacourt, VASSEUR-GARNIER, Delac0urt, tél. O6 39 98 I2 34, PERSONNE_A."
    spans = m.scan(leaked)
    values = [s.value for s in spans]
    assert "Jean-Pierre\nDelacourt" in values
    assert "VASSEUR-GARNIER" in values
    assert "Delac0urt" in values
    assert "O6 39 98 I2 34" in values
    assert all("PERSONNE_A" not in v for v in values)
    assert all(s.source in ("dictionary", "regex") for s in spans)


def test_scan_valid_identifiers_without_store():
    m = new_masker()
    spans = m.scan("Écrire à x.y@exemple-mail.fr, IBAN FR76 3000 6000 0112 3456 7890 189, ou IBAN FR76 3000 6000 0112 3456 7890 188.")
    assert [(s.kind, s.source) for s in spans] == [("EMAIL", "regex"), ("IBAN", "regex")]


def test_scan_masked_text_is_clean():
    m = new_masker()
    r = m.mask(SAMPLE)
    assert [s for s in m.scan(r.text) if s.source == "dictionary"] == []


# --- codes and DLP ---------------------------------------------------------------------------------------

DLP_PATTERNS = [
    re.compile(r"\d{5,}"),  # long digit runs (cards, NIR, SIREN, phone numbers)
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),  # credit card (Purview-like)
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),  # IBAN
    re.compile(r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b"),  # French NIR
    re.compile(r"\b0[1-9](?:[ .-]?\d{2}){4}\b"),  # French phone
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # US SSN
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),  # e-mail
    re.compile(r"\b\d{3} ?\d{3} ?\d{3}\b"),  # SIREN
    re.compile(r"\bFR[0-9A-Z]{2}\d{9}\b"),  # French VAT
    re.compile(r"https?://|www\."),  # URL
]


def _all_codes():
    for kind in KINDS:
        for locale in ("fr", "en"):
            limit = 18278 if kind in ("PERSON", "ORG") else 9999
            for i in range(limit):
                yield make_code(kind, i, locale)


def test_codes_do_not_look_like_dlp_patterns():
    codes = list(_all_codes())
    assert len(codes) > 300_000
    for code in codes:
        assert CODE_RE.fullmatch(code), code
        for pat in DLP_PATTERNS:
            assert not pat.search(code), (code, pat.pattern)
    blob = " ".join(codes[::7])
    assert detect_structured(blob) == []


def test_codes_survive_masking_unchanged_by_detectors():
    m = new_masker()
    text = "PERSONNE_A SOCIETE_B IBAN_12 TEL_3 RG_4"
    assert all(s.source == "regex" for s in m.scan(text)) and m.scan(text) == []


# --- optional NER -----------------------------------------------------------------------------------------


def test_rules_mode_by_default_without_spacy(monkeypatch, tmp_path):
    from ragbase_shield.engine import ner

    # no GLiNER model on this "machine" either (a machine may hold one in its Hugging Face cache)
    monkeypatch.setattr(ner, "_cache_roots", lambda: [tmp_path / "no-models"])
    m = Masker(MemoryStore())
    try:
        import spacy  # noqa: F401
    except ImportError:
        assert m.mode == "rules" and not m.use_ner


def test_ner_hook_is_filtered_and_never_overrides_structured():
    text = "Témoin : Kofi Ansah. Contact : kofi@exemple-mail.fr. Cour de cassation. Le Bureau."

    def fake_ner(t):
        out = []
        for word, kind in (("Kofi Ansah", "PERSON"), ("kofi@exemple-mail.fr", "PERSON"),
                           ("Cour de cassation", "ORG"), ("Bureau", "ORG")):
            i = t.index(word)
            out.append((i, i + len(word), kind))
        return out

    m = Masker(MemoryStore(), ner=fake_ner)
    assert m.mode == "rules+ner"
    r = m.mask(text)
    assert r.text == "Témoin : PERSONNE_A. Contact : EMAIL_1. Cour de cassation. Le Bureau."


def test_ner_failure_falls_back_to_rules():
    def broken(_t):
        raise RuntimeError("model crashed")

    m = Masker(MemoryStore(), ner=broken)
    assert m.mask("M. Paul Rivière.").text == "M. PERSONNE_A."


# --- corpus-level checks ----------------------------------------------------------------------------------


def _fixture_texts():
    return sorted(DOCS.glob("*.txt"))


@pytest.mark.parametrize("path", _fixture_texts(), ids=lambda p: p.stem)
def test_no_gold_value_left_in_masked_fixture(path):
    import json

    gold = json.loads(path.with_suffix("").with_suffix(".gold.json").read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    m = new_masker()
    masked = m.mask(text).text
    clear_texts = " ".join(c["text"] for c in gold["keep_clear"]).lower()
    for mention in gold["mentions"]:
        value = mention["text"]
        if value.lower() in clear_texts:
            continue
        assert not re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", masked), (mention["kind"], value)
    for item in gold["keep_clear"]:
        assert item["text"] in masked, item["text"]
    assert m.unmask(masked).count("_") <= text.count("_")


def test_speed_300k_characters_rules_mode():
    blob = "\n\n".join(p.read_text(encoding="utf-8") for p in _fixture_texts())
    text = (blob * (300_000 // len(blob) + 1))[:300_000]
    m = new_masker()
    m.mask(text[:5000])  # warm the lexicons
    t0 = time.perf_counter()
    r = m.mask(text)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0, f"{elapsed:.2f}s"
    t0 = time.perf_counter()
    m.unmask(r.text)
    m.scan(text[:100_000])
    assert time.perf_counter() - t0 < 3.0


def test_generated_identifiers_are_masked_in_bulk():
    m = new_masker()
    parts = []
    for i in range(50):
        body = f"{(i * 7919) % 10**8 + 10**8:09d}"[:8]
        siren = body + luhn_check_digit(body)
        parts.append(f"RCS Lyon {siren[:3]} {siren[3:6]} {siren[6:]} ;")
    text = "\n".join(parts)
    r = m.mask(text)
    assert not re.search(r"\d{3} \d{3} \d{3}", r.text)
    assert len({e.code for e in r.new_entities}) == 50


# --- masking text that already holds codes ---------------------------------------------------------------


def test_code_like_text_is_never_analysed():
    m = new_masker()
    out = m.mask("Le dossier SOCIETE_B SAS et PERSONNE_C Durand ; M. Paul Rivière.").text
    assert out == "Le dossier SOCIETE-B SAS et PERSONNE-C Durand ; M. PERSONNE_A."


def test_keep_known_codes_allows_masking_an_answer_again():
    m = new_masker()
    first = m.mask("M. Paul Rivière et la société Brivanor SAS.").text
    assert first == "M. PERSONNE_A et la société SOCIETE_A SAS."
    answer = first + " Ajouter Mme Agnès Tissandier et SOCIETE_Z."
    again = m.mask(answer, keep_known_codes=True)
    assert again.text == "M. PERSONNE_A et la société SOCIETE_A SAS. Ajouter Mme PERSONNE_B et SOCIETE-Z."
    assert m.unmask(again.text) == "M. Paul Rivière et la société Brivanor SAS. Ajouter Mme Agnès Tissandier et SOCIETE-Z."
    # default: every code-like string is escaped, known or not
    assert m.mask(first).text == "M. PERSONNE-A et la société SOCIETE-A SAS."
