"""R1 corrections, owner SERVICE (internal correction plan R1): search oracle (CL-25), cross-dossier
canary placeholders (CL-26), dossier scoping of the MCP server (CL-27), unsupported files (CL-28), report of what
a saved draft could not restore (CL-31, CL-36) and short forms of registered names in labels (CL-01, CL-02,
CL-05). Every name, number and acronym here is invented for these tests."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest
from mcp import Client

from ragbase_shield import documents, mcp_server, service
from ragbase_shield.service import ShieldError


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_MULTI_DOSSIER", raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_DOSSIER", raising=False)
    service.reset()
    yield
    service.reset()


def _dossier(tmp_path: Path, name: str, files: dict[str, str], people=(), orgs=()) -> str:
    folder = tmp_path / name
    folder.mkdir()
    for fname, text in files.items():
        (folder / fname).write_text(text, encoding="utf-8")
    code = service.add_dossier(folder)["code"]
    for p in people:
        service.register(code, "PERSON", p)
    for o in orgs:
        service.register(code, "ORG", o)
    return code


def _code_of(code: str, value: str) -> str:
    return next(e["code"] for e in service.entities(code) if e["value"] == value)


def call(name: str, args: dict | None = None, server=None) -> tuple[bool, str]:
    server = server or mcp_server.build_server()

    async def go():
        async with Client(server) as c:
            r = await c.call_tool(name, args or {})
            return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

    return asyncio.run(go())


@pytest.fixture
def two(tmp_path):
    """Dossier "other" (registered first) holds the names; dossier "mine" holds a note that cites some of them."""
    other = _dossier(tmp_path, "autre", {"acte.txt": "Acte de cession.\n"},
                     people=["Oswin Brakevald", "Rozenn Tonnelier"], orgs=["Financière Tarvellec"])
    mine = _dossier(tmp_path, "client", {"note.txt": "Compte rendu.\n"}, people=["Isaure Wardec"])
    return {"other": other, "mine": mine, "folder": tmp_path / "client"}


# ------------------------------------------------------------------------------------- CL-26 canary codes

def test_cl26_value_of_another_dossier_gets_a_restorable_code_of_this_dossier(two):
    out = service.default().guard_output("Le dossier Brakevald est clos.", two["mine"])
    assert "Brakevald" not in out and "[PERSONNE]" not in out
    code = re.search(r"PERSONNE_[A-Z]+", out).group()
    assert service.default().registry.get(two["mine"]).get_by_code(code) is not None
    assert service.restore_text(out, two["mine"]) == "Le dossier Brakevald est clos."
    assert not any(e["value"] == "Brakevald" for e in service.entities(two["other"]))  # nothing added there


def test_cl26_common_words_of_another_dossier_stay_in_this_dossier_text(two):
    text = "La dette financière nette baisse. Rozenn a appelé. Le tonnelier aussi."
    assert service.default().guard_output(text, two["mine"]) == text


def test_cl26_without_a_dossier_the_canary_still_uses_placeholders(two):
    out = service.default().guard_output("Le dossier Brakevald est clos.")
    assert "Brakevald" not in out and "[PERSONNE]" in out
    masked = service.mask_text("Courrier pour Oswin Brakevald.")["masked"]
    assert "Brakevald" not in masked


def test_cl26_mask_text_for_a_dossier_restores_the_other_dossier_value(two):
    r = service.mask_text("Rendez-vous avec Brakevald demain.", two["mine"])
    assert "Brakevald" not in r["masked"] and "[PERSONNE]" not in r["masked"]
    assert service.restore_text(r["masked"], two["mine"]) == "Rendez-vous avec Brakevald demain."


def test_cl26_mcp_tool_result_keeps_this_dossier_common_words(two):
    (two["folder"] / "suivi.txt").write_text("La dette financière nette baisse.\n", encoding="utf-8")
    docs = service.list_documents(two["mine"])
    doc = next(d["id"] for d in docs if d["masked_name"] == "suivi.txt")
    err, out = call("shield_read_document", {"dossier": two["mine"], "document": doc})
    assert not err and "dette financière nette" in out and "[SOCIETE]" not in out


def test_cl26_name_of_another_dossier_in_a_file_name_gets_a_code_of_this_dossier(two):
    (two["folder"] / "Courrier Tarvellec.txt").write_text("Bonjour.\n", encoding="utf-8")
    names = [d["masked_name"] for d in service.list_documents(two["mine"])]
    hit = next(n for n in names if n.startswith("Courrier "))
    assert "Tarvellec" not in hit and re.fullmatch(r"Courrier SOCIETE_[A-Z]+\.txt", hit), names


# ------------------------------------------------------------------------------------- CL-25 search oracle

@pytest.fixture
def cited(two):
    (two["folder"] / "rapport.txt").write_text(
        "Le rapport annuel cite Brakevald deux fois.\nLa dette financière nette baisse.\n", encoding="utf-8")
    service.scan_dossier(two["mine"])
    return two


def test_cl25_search_never_confirms_a_name_the_canary_hid(cited):
    assert service.search(cited["mine"], "Brakevald") == []
    # the hidden word adds nothing: same hits, same order, same snippets as the plain word alone
    assert service.search(cited["mine"], "cite Brakevald") == service.search(cited["mine"], "cite") != []


def test_cl25_search_still_finds_plain_words_and_codes(cited):
    hits = service.search(cited["mine"], "rapport annuel")
    assert hits and all("Brakevald" not in h["snippet"] for h in hits)
    code = re.search(r"PERSONNE_[A-Z]+", hits[0]["snippet"]).group()
    by_code = service.search(cited["mine"], code)
    assert by_code and code in by_code[0]["snippet"]
    assert service.search(cited["mine"], "financière")  # visible in clear: a normal hit


def test_cl25_a_value_registered_later_in_another_dossier_is_hidden_from_search(cited):
    assert service.search(cited["mine"], "annuel")  # the document is now in the cache
    service.register(cited["other"], "PERSON", "Ulrik Annuelsen")  # unrelated: nothing changes
    service.register(cited["other"], "ORG", "Rapportiq Velmar")
    assert service.search(cited["mine"], "Rapportiq") == []
    page = service.read_document(cited["mine"], next(d["id"] for d in service.list_documents(cited["mine"])
                                                      if d["masked_name"] == "rapport.txt"))["text"]
    assert "Brakevald" not in page


def test_cl25_offsets_of_search_and_read_line_up(cited):
    docs = {d["masked_name"]: d["id"] for d in service.list_documents(cited["mine"])}
    hit = service.search(cited["mine"], "dette")[0]
    page = service.read_document(cited["mine"], docs["rapport.txt"], start=hit["offset"], max_chars=500)["text"]
    assert "dette" in page


def test_cl25_a_damaged_vault_still_fails_closed_after_the_document_guard(cited):
    vault_file = service.default().registry.get(cited["other"])._db.path
    service.reset()
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(vault_file) + suffix)
        if p.exists():
            p.write_bytes(b"\0" * 4096)
    doc = next(d.id for d in service.default().registry.get(cited["mine"]).documents() if d.name == "rapport.txt")
    for fn in (lambda: service.read_document(cited["mine"], doc), lambda: service.search(cited["mine"], "dette")):
        with pytest.raises(ShieldError) as exc:
            fn()
        assert exc.value.kind == "vault_error" and "Brakevald" not in str(exc.value)


# ------------------------------------------------------------------------------------- CL-27 dossier scope

def test_cl27_a_server_is_pinned_to_the_first_dossier_it_opens(two):
    server = mcp_server.build_server()
    err, _ = call("shield_list_documents", {"dossier": two["mine"]}, server)
    assert not err
    err, out = call("shield_list_documents", {"dossier": two["other"]}, server)
    assert err and two["mine"] in out and "dossier_scope" in out
    assert "Brakevald" not in out
    err, out = call("shield_search", {"dossier": two["other"], "query": "acte"}, server)
    assert err and "dossier_scope" in out
    err, out = call("shield_save_draft", {"dossier": two["other"], "title": "x", "content": "y"}, server)
    assert err and "dossier_scope" in out
    assert not (Path(service.list_dossiers(include_private=True)[0]["folder"]) / "Shield - sorties").exists()


def test_cl27_list_dossiers_after_pinning_shows_one_row(two):
    server = mcp_server.build_server()
    err, out = call("shield_list_dossiers", {}, server)
    assert not err and two["mine"] in out and two["other"] in out and "premier dossier" in out
    call("shield_read_document", {"dossier": two["mine"], "document": "DOC_1"}, server)
    err, out = call("shield_list_dossiers", {}, server)
    assert not err and two["mine"] in out and two["other"] not in out and "1 dossier(s)" in out


def test_cl27_opt_out_and_fixed_dossier(two, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_MULTI_DOSSIER", "1")
    server = mcp_server.build_server()
    assert not call("shield_list_documents", {"dossier": two["mine"]}, server)[0]
    assert not call("shield_list_documents", {"dossier": two["other"]}, server)[0]
    monkeypatch.delenv("RAGBASE_SHIELD_MULTI_DOSSIER")
    monkeypatch.setenv("RAGBASE_SHIELD_DOSSIER", two["other"])
    server = mcp_server.build_server()
    err, out = call("shield_list_documents", {"dossier": two["mine"]}, server)
    assert err and two["other"] in out


def test_cl27_unknown_dossier_does_not_pin_and_a_new_server_starts_free(two):
    server = mcp_server.build_server()
    assert call("shield_list_documents", {"dossier": "DOSSIER_77"}, server)[0]
    assert not call("shield_list_documents", {"dossier": two["other"]}, server)[0]
    assert call("shield_list_documents", {"dossier": two["mine"]}, server)[0]
    assert not call("shield_list_documents", {"dossier": two["mine"]}, mcp_server.build_server())[0]
    assert service.list_documents(two["other"]) and service.list_documents(two["mine"])  # the service is free


# ------------------------------------------------------------------------------------- CL-28 unsupported

@pytest.fixture
def sheets(tmp_path):
    code = _dossier(tmp_path, "tableurs", {"note.txt": "Mme Isaure Wardec écrit.\n"}, people=["Isaure Wardec"])
    folder = tmp_path / "tableurs"
    # v0.4 (T8): .xlsx is read since T8; a slide deck stands for the unsupported file
    (folder / "Budget Wardec 2025.pptx").write_bytes(b"PK\x03\x04 not a real deck")
    (folder / "plan.png").write_bytes(b"\x89PNG")
    (folder / "Thumbs.db").write_bytes(b"x")
    return code


def test_cl28_unsupported_files_are_listed_with_a_masked_name(sheets):
    docs = service.list_documents(sheets)
    kinds = {d["masked_name"]: d["kind"] for d in docs}
    sheet = next(n for n in kinds if n.endswith(".pptx"))
    assert kinds[sheet] == "unsupported" and kinds["plan.png"] == "unsupported" and kinds["note.txt"] == "txt"
    assert "Wardec" not in sheet and "PERSONNE_A" in sheet
    assert not any("Thumbs" in n for n in kinds)
    assert service.list_dossiers()[0]["documents"] == 1  # only readable documents are counted


def test_cl28_reading_an_unsupported_file_gives_a_code_only_error(sheets):
    doc = next(d["id"] for d in service.list_documents(sheets) if d["masked_name"].endswith(".pptx"))
    with pytest.raises(ShieldError) as exc:
        service.read_document(sheets, doc)
    assert exc.value.kind == "unsupported_format" and doc in str(exc.value) and "Wardec" not in str(exc.value)
    err, out = call("shield_read_document", {"dossier": sheets, "document": doc})
    assert err and "unsupported_format" in out and "Wardec" not in out


def test_cl28_mcp_listing_explains_unsupported_files_and_search_skips_them(sheets):
    err, out = call("shield_list_documents", {"dossier": sheets})
    assert not err and "| unsupported |" in out and "ne peut pas" in out and "Wardec" not in out
    assert all(h["document"] != "DOC_2" for h in service.search(sheets, "budget"))


# ------------------------------------------------------------------------------------- CL-31 / CL-36 report

@pytest.fixture
def drafted(tmp_path):
    return _dossier(tmp_path, "brouillons", {"Pièce Kestrevon.txt": "Mme Isaure Wardec écrit.\n"},
                    people=["Isaure Wardec"])


def test_cl31_save_draft_report_lists_placeholders_and_mcp_asks_for_a_rewrite(drafted):
    r = service.save_draft_report(drafted, "Note", "[SOCIETE] a vendu à [SOCIETE] puis [PERSONNE] a signé.", "md")
    assert r["placeholders"].count("[SOCIETE]") == 2 and r["placeholders"].count("[PERSONNE]") == 1
    err, out = call("shield_save_draft", {"dossier": drafted, "title": "Note", "content": "[SOCIETE] et [SOCIETE]"})
    assert not err and "[SOCIETE] ×2" in out and "enregistrez à nouveau" in out


def test_cl31_clean_draft_reports_nothing_and_save_draft_keeps_its_shape(drafted):
    a = _code_of(drafted, "Isaure Wardec")
    r = service.save_draft_report(drafted, "Note", f"{a} a signé.", "md")
    assert r["placeholders"] == [] and r["shield_ids"] == [] and r["unknown_codes"] == []
    assert set(service.save_draft(drafted, "Note", f"{a} a signé.", "md")) == {"id", "bytes", "format",
                                                                                "unknown_codes"}
    err, out = call("shield_save_draft", {"dossier": drafted, "title": "Note", "content": f"{a} a signé."})
    assert not err and "Attention" not in out and "Identifiants Shield" not in out


def test_cl31_restore_report_lists_placeholders(drafted):
    a = _code_of(drafted, "Isaure Wardec")
    r = service.restore_report(f"{a} et [SOCIETE] et DOC_404", drafted)
    assert "Wardec" in r["text"] and r["placeholders"] == ["[SOCIETE]"] and r["shield_ids"] == ["DOC_404"]


def test_cl36_id_labels_are_local_and_only_for_this_dossier(drafted):
    svc = service.default()
    d = svc.registry.get(drafted)
    labels = svc._id_labels(d, f"Voir DOC_1, {drafted}, DOSSIER_99 et DOC_404.")
    assert labels == {"DOC_1": "Pièce Kestrevon.txt", drafted: d.title}
    out_id = service.save_draft(drafted, "Synthèse", "Texte.", "md")["id"]
    assert svc._id_labels(d, f"suite de {out_id}") == {out_id: "Synthèse.md"}


def test_cl36_save_draft_passes_labels_to_restore_and_returns_no_label(drafted, monkeypatch):
    seen = {}
    real = service._restore_for_output()

    def spy(text, masker, *, id_labels=None, **kw):
        seen.setdefault("labels", []).append(dict(id_labels or {}))
        if real is not None:
            return real(text, masker, id_labels=id_labels, **kw)
        from types import SimpleNamespace

        out, unknown = masker.unmask_report(text)
        return SimpleNamespace(text=out, unknown_codes=unknown, placeholders=[], shield_ids=[], restored=0)

    monkeypatch.setattr(service, "_restore_for_output", lambda: spy)
    err, out = call("shield_save_draft", {"dossier": drafted, "title": "Synthèse DOC_1",
                                          "content": "Selon DOC_1, voir aussi DOC_404.", "format": "md"})
    assert not err and "Kestrevon" not in out
    assert any(lab.get("DOC_1") == "Pièce Kestrevon.txt" for lab in seen["labels"])
    if real is not None:  # the RESTORE correction is installed: the local file names the piece
        saved = next((Path(service.list_dossiers(include_private=True)[0]["folder"]) / "Shield - sorties")
                     .glob("*.md"))
        text = documents.read_text(saved).text
        assert "Pièce Kestrevon.txt" in text and "DOC_1" not in text and "DOC_404" in out


def test_cl36_restore_report_names_own_ids_and_reports_the_others(drafted, tmp_path):
    other = _dossier(tmp_path, "tiers", {"x.txt": "x\n"})
    r = service.restore_report(f"Voir DOC_1, DOC_404 et {other}.", drafted)
    assert "DOC_404" in r["shield_ids"] and other in r["shield_ids"]
    if service._restore_for_output() is not None:  # the RESTORE correction is installed
        assert "Pièce Kestrevon.txt" in r["text"] and "DOC_1" not in r["shield_ids"]
    else:
        assert "DOC_1" in r["shield_ids"]


# ------------------------------------------------------------------------------------- labels CL-01 CL-02 CL-05

@pytest.fixture
def labelled(tmp_path):
    code = _dossier(tmp_path, "etiquettes", {"note.txt": "Note interne.\n"},
                    people=["Isaure Rozenn Wardec", "Gwenola Serrurier"], orgs=["Brasserie Xavaron Quellec"])
    return {"code": code, "folder": tmp_path / "etiquettes"}


def _masked_names(code: str) -> dict[str, str]:
    return {d["masked_path"]: d["kind"] for d in service.list_documents(code)}


def test_cl01_company_acronym_in_file_and_folder_names(labelled):
    sub = labelled["folder"] / "Data room BXQ"
    sub.mkdir()
    (sub / "BXQ-310 fiche.txt").write_text("x", encoding="utf-8")
    (labelled["folder"] / "CDI signé.txt").write_text("x", encoding="utf-8")
    org = _code_of(labelled["code"], "Brasserie Xavaron Quellec")
    names = _masked_names(labelled["code"])
    assert f"Data room {org}/{org}-310 fiche.txt" in names, names
    assert "CDI signé.txt" in names
    svc = service.default()
    d = svc.registry.get(labelled["code"])
    assert svc._label_pass("notes bxq", d) == "notes bxq"  # the service rule needs capitals
    assert svc._label_pass("Rapport BXQ2024", d) == f"Rapport {org}2024"


def test_cl02_person_initials_in_file_names(labelled):
    for name in ("Note I.R.W. 2025.txt", "Synthèse IRW.txt", "Statuts S.A..txt"):
        (labelled["folder"] / name).write_text("x", encoding="utf-8")
    person = _code_of(labelled["code"], "Isaure Rozenn Wardec")
    names = _masked_names(labelled["code"])
    assert any(re.fullmatch(rf"Note {person}\.? 2025\.txt", n) for n in names), names
    assert f"Synthèse {person}.txt" in names and "Statuts S.A..txt" in names, names


def test_cl02_shared_initials_are_never_guessed(tmp_path):
    code = _dossier(tmp_path, "homonymes", {"note.txt": "x\n"},
                    people=["Isaure Rozenn Wardec", "Ilwen Ravaud Wolquin"])
    svc = service.default()
    d = svc.registry.get(code)
    # the label pass of the service (the engine's own masking of the label is tested by the NAMES owner)
    assert svc._label_pass("Synthèse IRW", d) == "Synthèse IRW"
    assert svc._label_pass("Note I.R.W.", d).startswith("Note [PERSONNE]")  # dotted: a person, but which one


def test_cl05_capitalised_common_word_surname_in_file_names(labelled):
    (labelled["folder"] / "Bulletins Serrurier 2024.txt").write_text("x", encoding="utf-8")
    (labelled["folder"] / "devis serrurier.txt").write_text("x", encoding="utf-8")
    person = _code_of(labelled["code"], "Gwenola Serrurier")
    names = _masked_names(labelled["code"])
    assert f"Bulletins {person} 2024.txt" in names and "devis serrurier.txt" in names, names


def test_cl05_ambiguous_common_word_surname_stays(tmp_path):
    code = _dossier(tmp_path, "ambigu", {"note.txt": "x\n"},
                    people=["Gwenola Serrurier", "Ilwen Serrurier", "Gwenola Basile", "Basile Kestrevon"])
    svc = service.default()
    d = svc.registry.get(code)
    # the label rule of the service (two owners of the surname; a surname that is another person's first name)
    assert svc._label_pass("Bulletins Serrurier", d) == "Bulletins Serrurier"
    assert svc._label_pass("Note Basile", d) == "Note Basile"
    # and the last canary never gives such a word the code of one of its owners
    owners = {_code_of(code, "Gwenola Basile"), _code_of(code, "Basile Kestrevon")}
    out = svc.guard_output("Note Basile", code)
    assert not any(c in out for c in owners), out
