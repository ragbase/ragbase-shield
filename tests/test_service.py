"""Service layer (ARCHITECTURE 4.4): model-facing functions return codes and masked text only, local functions
restore, every failure is a code-only ShieldError. Synthetic data only."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from ragbase_shield import documents, service
from ragbase_shield.engine import UNMASK_RE
from ragbase_shield.service import ShieldError

FIXTURES = Path(__file__).parent / "fixtures" / "docs"

ASSIGNATION = (
    "ASSIGNATION DEVANT LE TRIBUNAL JUDICIAIRE DE DOUAI\n\n"
    "Madame Clémence MORVANDIAU, demeurant 14 rue des Glycines, 59300 Valenciennes, "
    "courriel clemence.morvandiau@exemple-morvandiau.fr,\n\n"
    "CONTRE la société LAMBRETTI CONSEIL SAS, représentée par M. Ugo FERRACCI-DAUBEL, président.\n\n"
    "Mme Morvandiau a versé un acompte de 12 400 euros à la société Lambretti Conseil. "
    "Le licenciement est contesté devant le conseil de prud'hommes.\n"
)
SECRETS = ["Clémence MORVANDIAU", "Morvandiau", "MORVANDIAU", "LAMBRETTI CONSEIL", "Lambretti Conseil",
           "FERRACCI-DAUBEL", "14 rue des Glycines", "clemence.morvandiau@exemple-morvandiau.fr"]


@pytest.fixture(autouse=True)
def _fresh_service():
    service.reset()
    yield
    service.reset()


@pytest.fixture
def case(tmp_path):
    folder = tmp_path / "Dossier Morvandiau"
    folder.mkdir()
    (folder / "assignation.txt").write_text(ASSIGNATION, encoding="utf-8")
    (folder / "Courrier Morvandiau.txt").write_text("Madame Morvandiau,\nVotre dossier avance.\n", encoding="utf-8")
    sub = folder / "Pièces Lambretti"
    sub.mkdir()
    (sub / "note.md").write_text("# Note\n\nM. Ferracci-Daubel conteste. Mme Morvandiau maintient.\n",
                                 encoding="utf-8")
    info = service.add_dossier(folder, "Morvandiau c. Lambretti Conseil SAS")
    return {"folder": folder, "code": info["code"], "info": info}


def leaks(output) -> list[str]:
    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    return [s for s in SECRETS if s in text]


def doc_id(code: str, name_part: str) -> str:
    for d in service.list_documents(code):
        if name_part in d["masked_name"]:
            return d["id"]
    raise AssertionError(name_part)


# ---------------------------------------------------------------------------------------------- dossiers

def test_add_dossier_returns_codes_and_counts(case):
    info = case["info"]
    assert info["code"] == "DOSSIER_1"
    assert info["documents"] == 3 and info["unreadable"] == 0
    assert info["counts"].get("PERSON", 0) >= 2 and info["counts"].get("ORG", 0) >= 1
    assert not leaks(info)


def test_list_dossiers_has_no_title_or_folder(case):
    rows = service.list_dossiers()
    assert rows == [{"code": "DOSSIER_1", "documents": 3, "entities": rows[0]["entities"]}]
    assert "Morvandiau" not in json.dumps(rows)
    private = service.list_dossiers(include_private=True)
    assert private[0]["title"] == "Morvandiau c. Lambretti Conseil SAS"
    assert Path(private[0]["folder"]) == case["folder"].resolve()


def test_title_parties_are_registered_when_documents_do_not_name_them(tmp_path):
    folder = tmp_path / "vide"
    folder.mkdir()
    info = service.add_dossier(folder, "Garnier-Vasseur c. Brunelac Ateliers SAS")
    assert info["parties"] == 2
    ents = service.entities(info["code"])
    assert {e["kind"] for e in ents} == {"PERSON", "ORG"}
    assert all(e["source"] == "user" for e in ents)


def test_folder_name_is_parsed_for_parties_only_with_a_separator(tmp_path):
    plain = tmp_path / "Dossier Ferracci-Daubel"
    plain.mkdir()
    info = service.add_dossier(plain)
    assert info["parties"] == 0
    assert service.entities(info["code"]) == []
    sides = tmp_path / "Ferracci-Daubel c. Brivanor Conseil SAS"
    sides.mkdir()
    info = service.add_dossier(sides)
    assert info["parties"] == 2


def test_title_parties_already_found_in_documents_are_not_duplicated(case):
    persons = [e for e in service.entities(case["code"]) if e["kind"] == "PERSON"]
    morvandiau = [e for e in persons if "orvandiau" in e["value"].lower()]
    assert len(morvandiau) == 1


# ---------------------------------------------------------------------------------------------- documents

def test_list_documents_masks_file_and_folder_names(case):
    docs = service.list_documents(case["code"])
    assert [d["id"] for d in docs] == ["DOC_1", "DOC_2", "DOC_3"]
    assert not leaks(docs)
    names = {d["masked_name"] for d in docs}
    assert "assignation.txt" in names
    assert any(re.fullmatch(r"Courrier PERSONNE_[A-Z]+\.txt", n) for n in names)
    note = next(d for d in docs if d["masked_name"] == "note.md")
    assert re.fullmatch(r"Pièces SOCIETE_[A-Z]+/note\.md", note["masked_path"])
    assert {d["kind"] for d in docs} == {"txt", "md"}


def test_read_document_is_masked_and_consistent(case):
    r = service.read_document(case["code"], doc_id(case["code"], "assignation"))
    assert set(r) >= {"id", "text", "next", "total_chars", "needs_ocr", "start", "pages", "warnings"}
    assert r["next"] is None and r["needs_ocr"] is False and r["start"] == 0
    assert not leaks(r)
    text = r["text"]
    assert "TRIBUNAL JUDICIAIRE DE DOUAI" in text  # courts stay in clear
    assert "conseil de prud'hommes" in text
    codes = [m.group() for m in UNMASK_RE.finditer(text)]
    assert any(c.startswith("PERSONNE_") for c in codes) and any(c.startswith("SOCIETE_") for c in codes)
    # the full name and "Mme Morvandiau" share one code
    person = re.search(r"Madame (PERSONNE_[A-Z]+)", text).group(1)
    assert f"Mme {person}" in text


def test_read_document_pages_cover_the_text_and_never_split_a_code(case):
    long_text = "\n".join(ASSIGNATION.replace("12 400", str(1000 + i)) for i in range(6))
    (case["folder"] / "long.txt").write_text(long_text.replace("\n\n", " "), encoding="utf-8")
    did = doc_id(case["code"], "long")
    full = service.read_document(case["code"], did, 0, 50_000)["text"]
    pages, start = [], 0
    while start is not None:
        r = service.read_document(case["code"], did, start, 500)
        assert len(r["text"]) <= 500
        pages.append(r["text"])
        start = r["next"]
    assert "".join(pages) == full and len(pages) >= 2
    cuts, pos = [], 0
    for p in pages[:-1]:
        pos += len(p)
        cuts.append(pos)
    for m in UNMASK_RE.finditer(full):
        assert not any(m.start() < c < m.end() for c in cuts), "a page boundary splits a code"
    beyond = service.read_document(case["code"], did, 10**7)
    assert beyond["text"] == "" and beyond["next"] is None


def test_read_document_bad_arguments_fail_closed(case):
    with pytest.raises(ShieldError) as e:
        service.read_document(case["code"], "DOC_99")
    assert e.value.kind == "unknown_document" and "DOC_99" in str(e.value)
    with pytest.raises(ShieldError) as e:
        service.read_document("Dossier Morvandiau", "DOC_1")
    assert e.value.kind == "invalid_argument" and "Morvandiau" not in str(e.value)
    with pytest.raises(ShieldError) as e:
        service.read_document("DOSSIER_42", "DOC_1")
    assert e.value.kind == "unknown_dossier"
    with pytest.raises(ShieldError):
        service.read_document(case["code"], "../../etc/passwd")


def test_read_document_sees_file_changes(case):
    did = doc_id(case["code"], "assignation")
    first = service.read_document(case["code"], did)["text"]
    path = case["folder"] / "assignation.txt"
    path.write_text(ASSIGNATION + "\nNouvelle pièce : courriel de Mme Morvandiau du 3 mars.\n", encoding="utf-8")
    second = service.read_document(case["code"], did)["text"]
    assert second != first and "Nouvelle pièce" in second and not leaks(second)


def test_scanned_pdf_reports_needs_ocr(case):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(case["folder"] / "scan.pdf", "wb") as fh:
        w.write(fh)
    docs = service.list_documents(case["code"])
    pdf = next(d for d in docs if d["kind"] == "pdf")
    assert pdf["pages"] == 1
    r = service.read_document(case["code"], pdf["id"])
    assert r["needs_ocr"] is True and r["text"] == ""


def test_unreadable_document_error_is_a_code(case):
    (case["folder"] / "broken.docx").write_bytes(b"not a zip at all")
    did = doc_id(case["code"], "broken")
    with pytest.raises(ShieldError) as e:
        service.read_document(case["code"], did)
    assert e.value.kind == "document_unreadable" and "docx_unreadable" in str(e.value)


def test_internal_errors_never_echo_values(case, monkeypatch, caplog):
    def boom(path):
        raise RuntimeError("secret Clémence MORVANDIAU 14 rue des Glycines")

    monkeypatch.setattr(documents, "read_text", boom)
    service.default()._docs.clear()
    with pytest.raises(ShieldError) as e:
        service.read_document(case["code"], "DOC_1")
    assert e.value.kind == "internal"
    assert not leaks(str(e.value)) and "ref " in str(e.value)
    assert not leaks(caplog.text)
    assert e.value.__cause__ is None and e.value.__suppress_context__


def test_vault_error_is_code_only(tmp_path, monkeypatch, case):
    service.reset()
    home = Path(service.default().registry.home)
    service.reset()
    (home / "key").write_bytes(b"0" * 44)
    with pytest.raises(ShieldError) as e:
        service.list_dossiers()
    assert e.value.kind == "vault_error"
    assert str(home) not in str(e.value)


def test_canary_replaces_values_the_masker_missed(case, monkeypatch):
    """Even if the engine lets a registered value through, the output canary replaces it."""
    from ragbase_shield.engine import MaskResult, Masker

    monkeypatch.setattr(Masker, "mask", lambda self, text, **kw: MaskResult(text=text))
    service.default()._docs.clear()
    r = service.read_document(case["code"], doc_id(case["code"], "assignation"))
    assert not [s for s in ("MORVANDIAU", "Morvandiau", "LAMBRETTI", "FERRACCI") if s in r["text"]]


# ---------------------------------------------------------------------------------------------- search

def test_search_with_a_code_finds_every_mention(case):
    text = service.read_document(case["code"], doc_id(case["code"], "assignation"))["text"]
    person = re.search(r"Madame (PERSONNE_[A-Z]+)", text).group(1)
    hits = service.search(case["code"], f"{person} acompte")
    assert hits and not leaks(hits)
    assert hits[0]["document"].startswith("DOC_") and person in hits[0]["snippet"] and "acompte" in hits[0]["snippet"]
    r = service.read_document(case["code"], hits[0]["document"], hits[0]["offset"])
    assert r["text"].startswith(hits[0]["snippet"].lstrip("…").split()[0])


def test_search_plain_words_are_accent_and_case_insensitive(case):
    hits = service.search(case["code"], "LICENCIEMENT conteste")
    assert hits and "licenciement" in hits[0]["snippet"].lower()
    assert service.search(case["code"], "prud hommes") or service.search(case["code"], "prud'hommes")


def test_search_never_confirms_a_guessed_real_name(case):
    for guess in ("Morvandiau", "Lambretti", "Glycines", "FERRACCI"):
        assert service.search(case["code"], guess) == [], guess


def test_search_bad_query(case):
    with pytest.raises(ShieldError):
        service.search(case["code"], "   ")
    with pytest.raises(ShieldError):
        service.search(case["code"], "x" * 600)


# ---------------------------------------------------------------------------------------------- save_draft

def test_save_draft_docx_restores_locally_and_returns_codes_only(case):
    code = case["code"]
    text = service.read_document(code, doc_id(code, "assignation"))["text"]
    person = re.search(r"Madame (PERSONNE_[A-Z]+)", text).group(1)
    org = re.search(r"(SOCIETE_[A-Z]+)", text).group(1)
    r = service.save_draft(code, f"Conclusions {person}", f"# Conclusions\n\n**{person}** contre {org}, et "
                                                          "PERSONNE_ZZ.\n", "docx")
    assert set(r) == {"id", "bytes", "format", "unknown_codes"}
    assert r["id"] == "OUTPUT_1" and r["format"] == "docx" and r["bytes"] > 1000
    assert r["unknown_codes"] == ["PERSONNE_ZZ"]
    out_dir = case["folder"] / "Shield - sorties"
    files = list(out_dir.iterdir())
    assert len(files) == 1 and files[0].suffix == ".docx" and "MORVANDIAU" in files[0].name.upper()
    restored = documents.read_text(files[0]).text
    assert "MORVANDIAU" in restored.upper() and "LAMBRETTI" in restored.upper()
    assert documents.docx_dossier_code(files[0]) == code
    # the output folder is not listed as a document
    assert all("Shield - sorties" not in d["masked_path"] for d in service.list_documents(code))


def test_save_draft_md_and_errors(case):
    r = service.save_draft(case["code"], "note", "Bonjour", "md")
    assert r["format"] == "md" and r["id"].startswith("OUTPUT_")
    with pytest.raises(ShieldError):
        service.save_draft(case["code"], "x", "contenu", "pdf")
    with pytest.raises(ShieldError):
        service.save_draft(case["code"], "x", "   ")


# ---------------------------------------------------------------------------------------------- local API

def test_mask_and_restore_round_trip(case):
    code = case["code"]
    r = service.mask_text("Mme Morvandiau écrit à la société Lambretti Conseil.", code)
    assert not leaks(r["masked"])
    assert r["counts"].get("PERSON") == 1 and r["counts"].get("ORG") == 1
    assert {f["kind"] for f in r["found"]} == {"PERSON", "ORG"} and all("value" not in f for f in r["found"])
    with_values = service.mask_text("Mme Morvandiau", code, include_values=True)
    assert "orvandiau" in with_values["found"][0]["value"].lower()
    back = service.restore_report(r["masked"] + " PERSONNE_ZZ", code)
    assert "MORVANDIAU" in back["text"].upper() and back["unknown_codes"] == ["PERSONNE_ZZ"]
    assert back["restored"] == 2
    assert service.restore_text(r["masked"], code) == back["text"][: -len(" PERSONNE_ZZ")]


def test_mask_without_dossier_uses_a_temporary_store(case):
    r = service.mask_text("M. Ugo FERRACCI-DAUBEL, IBAN FR76 3000 6000 0112 3456 7890 189")
    assert "FERRACCI" not in r["masked"] and "IBAN_1" in r["masked"]
    assert len(service.entities(case["code"])) == case["info"]["entities"]  # nothing persisted


def test_keep_clear_and_register(case):
    code = case["code"]
    reg = service.register(code, "PERSON", "Thibault Mercadier")
    assert reg["code"].startswith("PERSONNE_")
    r = service.mask_text("M. Thibault Mercadier", code)
    assert reg["code"] in r["masked"]
    service.keep_clear(code, reg["code"])
    assert "Mercadier" in service.mask_text("M. Thibault Mercadier", code)["masked"]
    assert [e for e in service.entities(code) if e["code"] == reg["code"]][0]["kept_clear"] is True
    service.keep_clear(code, reg["code"], False)
    assert "Mercadier" not in service.mask_text("M. Thibault Mercadier", code)["masked"]
    with pytest.raises(ShieldError):
        service.keep_clear(code, "PERSONNE_ZZ")
    with pytest.raises(ShieldError):
        service.register(code, "NAME", "x")


def test_registering_a_known_name_reuses_its_code(case):
    """A second code for the same person would make the engine stop masking the shared first name."""
    code = case["code"]
    before = service.entities(code)
    known = next(e for e in before if e["kind"] == "PERSON" and "FERRACCI" in e["value"].upper())
    again = service.register(code, "PERSON", "Ugo Ferracci-Daubel")
    assert again["code"] == known["code"]
    org = next(e for e in before if e["kind"] == "ORG")
    assert service.register(code, "ORG", "Lambretti Conseil SAS")["code"] == org["code"]
    assert len(service.entities(code)) == len(before)


def test_kept_clear_entity_stays_clear_in_documents(case):
    code = case["code"]
    org = next(e for e in service.entities(code) if e["kind"] == "ORG")
    service.keep_clear(code, org["code"])
    text = service.read_document(code, doc_id(code, "assignation"))["text"]
    assert "LAMBRETTI" in text.upper()


def test_mask_file(case, tmp_path):
    p = tmp_path / "Lettre Morvandiau.txt"
    p.write_text("Madame Clémence MORVANDIAU, 14 rue des Glycines, 59300 Valenciennes.", encoding="utf-8")
    r = service.mask_file(p, case["code"])
    assert r["name"] == "Lettre Morvandiau.txt" and "Morvandiau" not in r["masked_name"]
    assert not leaks(r["masked_text"]) and r["needs_ocr"] is False


# ---------------------------------------------------------------------------------------------- canary and hooks support

def test_scan_text_reports_codes_only(case):
    hits = service.scan_text("Peux-tu écrire à Clémence Morvandiau et à LAMBRETTI CONSEIL ?")
    assert {h["kind"] for h in hits} == {"PERSON", "ORG"}
    assert all(h["dossier"] == "DOSSIER_1" and (h["code"] is None or UNMASK_RE.fullmatch(h["code"])) for h in hits)
    assert not leaks(hits)
    assert service.scan_text("Résume le dossier de PERSONNE_A pour SOCIETE_A.") == []
    assert service.scan_text("Aucun nom ici, seulement le Code du travail.") == []


def test_scan_text_ignores_kept_clear_values(case):
    code = case["code"]
    org = next(e for e in service.entities(code) if e["kind"] == "ORG")
    assert service.scan_text("la société Lambretti Conseil")
    service.keep_clear(code, org["code"])
    assert not [h for h in service.scan_text("la société Lambretti Conseil") if h["kind"] == "ORG"]


def test_protect_masks_values_and_keeps_codes(case):
    text, codes = service.protect("Résultat : PERSONNE_A et Mme Clémence MORVANDIAU, LAMBRETTI CONSEIL SAS.")
    assert not leaks(text) and codes
    assert text.startswith("Résultat : PERSONNE_A et Mme PERSONNE_")
    same, none = service.protect("Rien à masquer ici.")
    assert same == "Rien à masquer ici." and none == []


def test_status_is_honest(case):
    s = service.status()
    # "rules+ner:<backend>" when a model is installed (the name of the backend is part of the honest answer)
    assert s["version"] == "0.4.1" and re.fullmatch(r"rules(?:\+ner(?::[\w:.-]+)?)?", s["engine_mode"])
    assert s["ocr"] is False and s["network"] is False and s["dossiers"] == 1 and s["key_storage"] == "file"
    joined = " ".join(s["limits"])
    assert "pseudonymisation" in joined.lower() and "100" not in joined and "OCR" in joined


def test_journal_holds_codes_and_numbers_only(case):
    code = case["code"]
    service.read_document(code, "DOC_1")
    service.search(code, "acompte")
    service.save_draft(code, "Projet", "texte", "md")
    entries = service.journal()
    events = {e["event"] for e in entries}
    assert {"read_document", "search", "save_draft", "add_dossier"} <= events
    assert not leaks(entries)
    assert all(e["dossier"] in (None, code) for e in entries)


def test_remove_dossier(case):
    service.remove_dossier(case["code"])
    assert service.list_dossiers() == []
    with pytest.raises(ShieldError):
        service.list_documents(case["code"])


def test_every_fixture_reads_clean(tmp_path):
    """All engine fixtures: masked reads hold none of the registered parties."""
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    for i, item in enumerate(manifest):
        gold = json.loads((FIXTURES / item["gold"]).read_text(encoding="utf-8"))
        folder = tmp_path / f"f{i}"
        folder.mkdir()
        shutil.copy(FIXTURES / item["doc"], folder / item["doc"])
        code = service.add_dossier(folder, gold["title"])["code"]
        for p in gold["parties"]:
            service.register(code, p["kind"], p["value"])
        text = service.read_document(code, "DOC_1", 0, 50_000)["text"]
        for p in gold["parties"]:
            assert p["value"] not in text, (item["doc"], p["id"])
