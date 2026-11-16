"""Engine 0.4.4: the birth place fix (L1 to L6).

Since plugin round 2 the engine masks the place of birth (kind BIRTHPLACE, code LIEU_n). In 0.4.2 and 0.4.3 that
value then SPREAD like a name: every other « Lyon » of the dossier became LIEU_1, also in « cour d'appel de Lyon »,
« tribunal judiciaire de Lyon » or « Fait à Lyon ». The fix: ONE rule in ``engine.types`` (the kind BIRTHPLACE is
never spreadable). A place of birth is masked only where the text says it is one (the birth contexts of round 2);
its value is never searched for anywhere else; restore still puts the real town back.

Every name, town of birth, address and number here is invented for these tests."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from ragbase_shield import claude_tab, kept, service, vault
from ragbase_shield.engine import Masker, MemoryStore, entity_norm
from ragbase_shield.engine import types as engine_types
from ragbase_shield.engine.types import is_weak_value, spreadable

TOWNS = ["Lyon", "Paris", "Valence", "Aix-en-Provence", "Saint-Étienne"]

DOC_A = ("Monsieur Thibault Mercadier, né le 3 mars 1980 à Lyon (Rhône), de nationalité française, demeurant "
         "12 rue des Glycines, 69007 Lyon.")
DOC_B = ("Il conteste son licenciement devant le conseil de prud'hommes de Lyon (RG n° 25/01234). La cour d'appel de "
         "Lyon a déjà jugé, le 5 mai 2021, que l'article L. 1232-1 du code du travail s'applique. Fait à Lyon, le "
         "2 novembre 2026. Le tribunal judiciaire de Lyon est compétent. Le siège de la société Ateliers Brunelac "
         "SAS est à Lyon.")
B_CLEAR = ["conseil de prud'hommes de Lyon", "La cour d'appel de Lyon a déjà jugé", "Fait à Lyon, le 2 novembre 2026",
           "Le tribunal judiciaire de Lyon est compétent", "est à Lyon."]


def _de(town: str) -> str:
    return "d'" + town if town[0] in "AEIOUÉ" else "de " + town


def _forms(town: str) -> list[str]:
    de = _de(town)
    return [f"Le tribunal judiciaire {de} est saisi.", f"Le tribunal de commerce {de} a statué.",
            f"Le conseil de prud'hommes {de} a jugé.", f"La cour d'appel {de} a confirmé.",
            f"Le tribunal administratif {de} a annulé.", f"Fait à {town}, le 2 novembre 2026.",
            f"notaire à {town}, le 5 mai 2021.", f"Il a été soigné au centre hospitalier {de}."]


def _masker(store=None) -> Masker:
    return Masker(store if store is not None else MemoryStore(), locale="fr", language="auto", use_ner=False,
                  replacement="codes")


def _folder(root: Path, name: str, files: dict[str, str]) -> Path:
    f = root / "cabinet" / name
    f.mkdir(parents=True)
    for fname, text in files.items():
        (f / fname).write_text(text, encoding="utf-8")
    return f


# ============================================================ the rule (engine.types)

def test_the_one_rule_birthplace_is_never_spreadable():
    spreads = engine_types.spreads
    assert engine_types.NEVER_SPREAD_KINDS == frozenset({"BIRTHPLACE"})
    assert not spreads("BIRTHPLACE", "Aix-en-Provence")
    assert spreads("ADDRESS", "12 rue des Glycines, 69007 Lyon") and spreads("PERSON", "Thibault Mercadier")
    assert not spreads("ID_CODE", "4") and is_weak_value("4")  # the weak rule of 0.4.3 is part of the same rule
    store = MemoryStore()
    ents = [store.add("BIRTHPLACE", "Lyon", entity_norm("BIRTHPLACE", "Lyon")),
            store.add("PERSON", "Thibault Mercadier", entity_norm("PERSON", "Thibault Mercadier")),
            store.add("ID_CODE", "13", "13")]
    assert [e.value for e in spreadable(ents)] == ["Thibault Mercadier"]


# ============================================================ the probe, at the Masker level

def test_the_probe_second_document_keeps_every_town_in_clear():
    m = _masker()
    a = m.mask(DOC_A).text
    assert re.fullmatch(r"Monsieur PERSONNE_A, né le NAISSANCE_1 à LIEU_1 \(Rhône\), de nationalité française, "
                        r"demeurant ADRESSE_1\.", a), a
    b = m.mask(DOC_B).text
    assert "LIEU" not in b, b
    for part in B_CLEAR:
        assert part in b, (part, b)
    assert "Brunelac" not in b and "25/01234" not in b  # the company and the case number are still masked


def test_the_probe_same_document_masked_twice():
    """The reading masks every document twice (first and last pass): the second pass must not spread the town."""
    m = _masker()
    text = DOC_A + " " + DOC_B
    first = m.mask(text).text
    second = m.mask(text).text
    assert first == second, (first, second)
    assert second.count("LIEU_1") == 1 and "né le NAISSANCE_1 à LIEU_1 (Rhône)" in second
    for part in B_CLEAR:
        assert part in second, (part, second)


@pytest.mark.parametrize("town", TOWNS)
def test_courts_notaries_hospitals_and_fait_a_stay_in_clear(town):
    m = _masker()
    birth = m.mask(f"Mme Odile Ferrandon, née le 4 avril 1975 à {town}, demeurant 3 place du Marché, 26000 "
                   "Valence.").text
    assert "née le NAISSANCE_1 à LIEU_1," in birth and town not in birth.replace("26000 Valence", ""), birth
    for form in _forms(town):
        out = m.mask(form).text
        assert out == form, (form, out)
    joined = " ".join(_forms(town))
    assert m.mask(joined).text == joined


@pytest.mark.parametrize("town", TOWNS)
@pytest.mark.parametrize("ctx", ["Il est né à {X}.", "Elle est née à {X}.", "Lieu de naissance : {X}",
                                 "Il est né le 3 mars 1980 à {X}."])
def test_the_birth_contexts_are_still_masked(town, ctx):
    m = _masker()
    m.mask(f"Mme Odile Ferrandon, née le 4 avril 1975 à {town}.")  # the town is already in the store
    out = m.mask("M. Paul Ravenel. " + ctx.format(X=town)).text
    assert "LIEU_1" in out and town not in out, out


def test_the_last_check_of_the_masker_never_finds_a_birth_place():
    m = _masker()
    m.mask(DOC_A)
    assert not [sp for sp in m.scan("La cour d'appel de Lyon a jugé. Fait à Lyon.") if sp.kind == "BIRTHPLACE"]


def test_restore_gives_the_real_town_back():
    m = _masker()
    m.mask(DOC_A)
    assert m.unmask("Né à LIEU_1, il saisit le conseil de prud'hommes de Lyon.") == \
        "Né à Lyon, il saisit le conseil de prud'hommes de Lyon."


def test_an_address_and_names_are_masked_as_before():
    """L5: the address rule still masks the town of an address; a town inside a company or a person's name is
    masked with that name."""
    m = _masker()
    m.mask(DOC_A)
    out = m.mask("Il demeure 12 rue des Glycines, 69007 Lyon. La société Lyon Ascenseurs Brunelac SAS "
                 "a signé.").text
    assert "ADRESSE_1" in out and "Glycines" not in out and "Ascenseurs" not in out, out


# ============================================================ the service: a dossier of two invented files

FILES = {
    "identite.txt": DOC_A + "\n",
    "conclusions.txt": DOC_B + "\n",
}


def _scan(root: Path, files=FILES) -> tuple[str, dict[str, str]]:
    code = service.add_dossier(_folder(root, "Mercadier c. Brunelac", files))["code"]
    service.scan_dossier(code)
    docs = {d["masked_name"]: d["id"] for d in service.list_documents(code)}
    return code, docs


def test_service_read_search_and_draft(tmp_path):
    code, docs = _scan(tmp_path)
    assert set(docs) == {"identite.txt", "conclusions.txt"}
    a = service.read_document(code, docs["identite.txt"])["text"]
    b = service.read_document(code, docs["conclusions.txt"])["text"]
    assert "né le NAISSANCE_1 à LIEU_1 (Rhône)" in a and "Lyon" not in a, a
    assert "LIEU" not in b, b
    for part in B_CLEAR:
        assert part in b, (part, b)
    hits = service.search(code, "Lyon")
    assert hits and all(h["document"] == docs["conclusions.txt"] for h in hits), hits
    assert any("cour d'appel de Lyon" in h["snippet"] for h in hits), hits
    r = service.save_draft_report(code, "Note", "Le conseil de prud'hommes de Lyon est saisi. Le salarié est né "
                                                "à LIEU_1.", "md")
    out_dir = tmp_path / "cabinet" / "Mercadier c. Brunelac" / "Shield - sorties"
    saved = [p.read_text(encoding="utf-8") for p in out_dir.iterdir()]
    assert len(saved) == 1 and r["unknown_codes"] == []
    assert "Le conseil de prud'hommes de Lyon est saisi. Le salarié est né à Lyon." in saved[0], saved[0]
    counts = {e["kind"]: e["value"] for e in service.entities(code)}
    assert counts.get("BIRTHPLACE") == "Lyon"  # still counted (the protect answer reads these counts)


def test_the_last_check_on_an_answer_leaves_the_court(tmp_path):
    code, _docs = _scan(tmp_path)
    other = service.add_dossier(_folder(tmp_path, "Autre", {"a.txt": "Note fictive.\n"}))["code"]
    text = "La cour d'appel de Lyon a jugé. Fait à Lyon. Le tribunal judiciaire de Lyon est compétent."
    s = service.default()
    for primary in (code, other, None):
        assert s.guard_output(text, primary) == text
        assert s.guard_parts([text, "Le siège est à Lyon."], primary) == [text, "Le siège est à Lyon."]
    assert not service.has_registered(text)


def test_another_dossier_keeps_its_courts_in_clear(tmp_path):
    _scan(tmp_path)
    code2, docs2 = _scan(tmp_path / "deux", {"jugement.txt": "Jugement fictif du tribunal judiciaire de Lyon. "
                                                             "Fait à Lyon, le 4 juin 2025.\n"})
    text = service.read_document(code2, docs2["jugement.txt"])["text"]
    assert text.strip() == "Jugement fictif du tribunal judiciaire de Lyon. Fait à Lyon, le 4 juin 2025.", text
    assert not any(e["kind"] == "BIRTHPLACE" for e in service.entities(code2))


def test_an_old_vault_with_a_birth_place_gives_the_new_behaviour(tmp_path):
    """L4: a vault of 0.4.2 / 0.4.3 already holds BIRTHPLACE values (here put in through ``register``, as an old
    reading did). A reading with the fixed engine needs no manual step."""
    f = _folder(tmp_path, "Ancien", {"conclusions.txt": DOC_B + "\n"})
    code = service.add_dossier(f)["code"]
    service.register(code, "BIRTHPLACE", "Lyon")
    other = service.add_dossier(_folder(tmp_path, "Autre", {"a.txt": "Né à Valence.\n"}))["code"]
    service.register(other, "BIRTHPLACE", "Valence")
    service.scan_dossier(code)
    doc = service.list_documents(code)[0]["id"]
    text = service.read_document(code, doc)["text"]
    assert "LIEU" not in text and "[LIEU]" not in text, text
    for part in B_CLEAR:
        assert part in text, (part, text)
    assert service.default().guard_output("Le tribunal judiciaire de Valence.", code) == \
        "Le tribunal judiciaire de Valence."


def test_no_kept_set_made_before_the_fix_is_used(tmp_path, plugin_env, monkeypatch):
    """L4: the rules fingerprint of the kept set changed, so a set written by the 0.4.4 engine before this fix
    (``0.4.4-r2``, courts as LIEU_1) is never used: the next start reads the dossier again, with no manual step."""
    assert kept.RULES_REVISION not in ("0.4.4-r1", "0.4.4-r2")
    claude_tab.lock_settings(tmp_path / "data")
    f = _folder(tmp_path, "Mercadier c. Brunelac", FILES)
    claude_tab.PICKER = lambda title, timeout: str(f)

    def conclusions() -> str:
        code = service.list_dossiers()[0]["code"]
        assert service.default().wait_reading(code, 30.0)
        doc = next(d["id"] for d in service.list_documents(code) if d["masked_name"] == "conclusions.txt")
        return service.read_document(code, doc)["text"]

    with monkeypatch.context() as m:  # the engine before the fix: the town spreads, the old revision
        m.setattr(engine_types, "NEVER_SPREAD_KINDS", frozenset())
        m.setattr(kept, "RULES_REVISION", "0.4.4-r2")
        service.default().protect_folder(f)
        assert "cour d'appel de LIEU_1" in conclusions()
        assert list((tmp_path / "data" / "kept").rglob("m-*.bin"))  # a kept set was written
    service.reset()  # a new start of the app, with the fixed engine
    assert not service.default()._kset_ready(service.list_dossiers()[0]["code"])
    service.default().protect_folder(f)
    text = conclusions()
    assert "LIEU" not in text, text
    for part in B_CLEAR:
        assert part in text, (part, text)


def test_the_last_check_still_masks_a_birth_context(tmp_path):
    """L1 in the last check: a structured find in a birth context is the detector reading its context, not a
    spread: it still gets the dossier's code."""
    code, _docs = _scan(tmp_path)
    out = service.default().guard_output("Il est né le 3 mars 1980 à Lyon. La cour d'appel de Lyon a jugé.", code)
    assert out.startswith("Il est né le ") and " à LIEU_1." in out and "La cour d'appel de Lyon a jugé." in out, out


# ============================================================ the plugin: the protect answer still counts it

@pytest.fixture
def plugin_env(monkeypatch):
    saved_env = dict(os.environ)
    saved_picker = claude_tab.PICKER
    monkeypatch.setattr(claude_tab, "PROTECT_ANSWER_SECONDS", 30.0)
    monkeypatch.setattr(claude_tab, "STATUS_WAIT_SECONDS", 30.0)
    yield
    service.reset()
    vault.KEY_STORE = None
    claude_tab.PICKER = saved_picker
    os.environ.clear()
    os.environ.update(saved_env)


def test_the_plugin_counts_the_birth_place_and_shows_the_courts(tmp_path, plugin_env):
    import asyncio

    from mcp import Client

    def call(server, name, args=None):
        async def go():
            async with Client(server) as c:
                r = await c.call_tool(name, args or {})
                return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

        return asyncio.run(go())

    claude_tab.lock_settings(tmp_path / "data")
    f = _folder(tmp_path, "Mercadier c. Brunelac", FILES)
    claude_tab.PICKER = lambda title, timeout: str(f)
    server = claude_tab.build_server()
    err, first = call(server, "shield_protect_folder")
    code = server._shield_scope.pinned
    assert not err and service.wait_reading(code, 30.0)
    err, status = call(server, "shield_status")
    assert not err and "1 lieu(x) de naissance" in status, status
    err, listing = call(server, "shield_list_documents", {"dossier": code})
    doc = next(line.split(" | ")[0] for line in listing.splitlines() if "conclusions.txt" in line)
    err, text = call(server, "shield_read_document", {"dossier": code, "document": doc})
    assert not err and "LIEU" not in text, text
    for part in B_CLEAR:
        assert part in text, (part, text)
    err, found = call(server, "shield_search", {"dossier": code, "query": "Lyon"})
    assert not err and "cour d'appel de Lyon" in found and "LIEU" not in found, found
