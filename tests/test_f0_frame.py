"""F0 (engine 0.4.3): Shield never masks its own answer.

The owner's data folder held an older dossier in which a short number ("4") was a registered identifier. The last
check of every answer replaced that "4" everywhere: "DOSSIER_4" became "DOSSIER_[IDENT]" and the counts became
codes, so Shield refused its own dossier code. Four layers, each tested here:

- L1: an answer is built from parts; only the parts that come from documents or from a person go through the last
  check (``mcp_server.Content``). Shield's own words, codes and counts never do.
- L2: a hit of the last check that touches a Shield code, DOC_n, DOSSIER_n, OUTPUT_n or a placeholder is dropped.
- L3: a weak value (fewer than 3 characters, or digits only and fewer than 6 of them) is never spread: not searched
  for in other places, not used by the last check, never made into an entity of another dossier.
- L4: the toque rule no longer stores "(T. 4)", "(T 13)" (a tome, a table) as an identifier.

Every name, number and folder here is invented for these tests."""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import pytest
from mcp import Client

from ragbase_shield import claude_tab, mcp_server, service, vault
from ragbase_shield.engine import Masker, MemoryStore, entity_norm
from ragbase_shield.engine import detectors as det
from ragbase_shield.engine.types import is_weak_value, spreadable

WEAK_VALUES = [("ID_CODE", "4"), ("ID_CODE", "13"), ("ID_CODE", "5"), ("ID_CODE", "20"), ("ID_CODE", "35"),
               ("PERSON", "Suite")]
CODE_VALUES = [("PERSON", "A"), ("ID_CODE", "1"), ("ORG", "DOSSIER")]

# Dossier B: five documents full of short numbers (the owner's dossier had a code DOSSIER_4 and counts of 5 and 20)
B_FILES = {
    "note 4.txt": "Note fictive : M. Odilon Quillardet a signé le 13 mars 2026. Voir l'article 4 du code civil et "
                  "la pièce 5.\n",
    "lettre 13.txt": "Lettre fictive à Mme Ysaline Corvanec, 20 rue des Lilas, 35000 Rennes. Délai de 35 jours.\n",
    "pièce 5.txt": "Pièce 5 fictive : relevé de 20 lignes, total de 35 euros, payé le 4 avril 2026.\n",
    "compte rendu.txt": "Compte rendu fictif du 4 mai 2026 : 13 personnes présentes, vote à 20 voix contre 5.\n",
    "annexe 20.txt": "Annexe 20 fictive. Tableau 4 sur 35, ligne 13.\n",
}
PLACEHOLDER_RE = re.compile(r"\[[A-ZÀ-Ý_]{2,}\]")


def call(server, name: str, args: dict | None = None) -> tuple[bool, str]:
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(name, args or {})
            return bool(r.is_error), "\n".join(getattr(x, "text", "") for x in r.content)

    return asyncio.run(go())


def _folder(root: Path, name: str, files: dict[str, str]) -> Path:
    f = root / "cabinet" / name
    f.mkdir(parents=True)
    for fname, text in files.items():
        (f / fname).write_text(text, encoding="utf-8")
    return f


def _register(code: str, values) -> None:
    for kind, value in values:
        service.register(code, kind, value)


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


def _plugin_answers(server, code: str, docs: int) -> list[tuple[bool, str]]:
    """Every tool of the plugin, for dossier ``code`` (the protect call comes first, in the caller)."""
    calls = [("shield_list_dossiers", None), ("shield_status", None),
             ("shield_list_documents", {"dossier": code})]
    calls += [("shield_read_document", {"dossier": code, "document": f"DOC_{i}"}) for i in range(1, docs + 1)]
    calls += [("shield_search", {"dossier": code, "query": "fictive"}),
              ("shield_search", {"dossier": code, "query": "35"}),
              ("shield_save_draft", {"dossier": code, "title": "Projet 4",
                                     "content": "Texte pour PERSONNE_A, pièce 5 et DOC_1, 20 lignes."}),
              ("shield_read_document", {"dossier": code, "document": "DOC_99"})]
    return [call(server, name, args) for name, args in calls]


def _plugin_run(root: Path, values, *, other_first: bool = True, fillers: int = 2) -> list[tuple[bool, str]]:
    """Dossier A (with ``values``) and ``fillers`` empty dossiers, then dossier B protected through the plugin.
    With ``other_first=False``, B is protected first and A comes after it."""
    claude_tab.lock_settings(root / "data")
    b = _folder(root, "Dossier Nouveau", B_FILES)

    def make_others():
        a = _folder(root, "Dossier Ancien", {"ancien.txt": "Courrier ancien fictif.\n"})
        _register(service.add_dossier(a)["code"], values)
        for i in range(fillers):
            service.add_dossier(_folder(root, f"Dossier Vide {i}", {"vide.txt": "Rien.\n"}))

    if other_first:
        make_others()
    claude_tab.PICKER = lambda title, timeout: str(b)
    server = claude_tab.build_server()
    first = call(server, "shield_protect_folder")
    code = server._shield_scope.pinned
    assert service.wait_reading(code, 30.0)
    if not other_first:
        make_others()
    return [first] + _plugin_answers(server, code, len(B_FILES))


# ============================================================ (1) the owner's case, through the plugin

def test_weak_values_of_another_dossier_change_no_answer_of_the_plugin(tmp_path, plugin_env):
    with_values = _plugin_run(tmp_path / "owner", WEAK_VALUES)
    empty = _plugin_run(tmp_path / "empty", [])
    assert with_values == empty  # byte for byte, every answer of the seven tools
    protect = with_values[0][1]
    assert "Le dossier choisi est maintenant protégé : DOSSIER_4." in protect
    assert "5 document(s) trouvé(s), 5 lu(s)." in protect
    assert "Suite : shield_list_documents avec DOSSIER_4." in protect
    texts = [t for _err, t in with_values]
    for t in texts:
        assert "IDENT" not in t and not PLACEHOLDER_RE.search(t), t
    for t in texts:
        if t.startswith("[DOSSIER_4 / DOC_"):  # the head of a read answer is Shield's own "[...]"
            assert "[" not in t.split("]", 1)[1], t
        else:
            assert "[" not in t, t
    joined = "\n".join(texts)
    assert "Voir l'article 4 du code civil et la pièce 5." in joined
    assert "13 personnes présentes, vote à 20 voix contre 5." in joined
    assert " | lettre 13.txt" in joined and " | note 4.txt" in joined
    assert "Quillardet" not in joined and "Corvanec" not in joined


def test_the_weak_values_stay_in_the_old_vault(tmp_path, plugin_env):
    _plugin_run(tmp_path / "owner", WEAK_VALUES, fillers=0)
    assert {(e["kind"], e["value"]) for e in service.entities("DOSSIER_1")} == set(WEAK_VALUES)
    assert not any(e["value"] in {"4", "13", "5", "20", "35", "Suite"} for e in service.entities("DOSSIER_2"))


# ============================================================ (2) Shield's own codes

def test_values_shaped_like_parts_of_codes_never_change_a_code(tmp_path, plugin_env):
    with_values = _plugin_run(tmp_path / "codes", CODE_VALUES, other_first=False, fillers=0)
    empty = _plugin_run(tmp_path / "empty", [], other_first=False, fillers=0)
    assert with_values == empty
    joined = "\n".join(t for _e, t in with_values)
    for token in ("DOSSIER_1", "DOC_1", "PERSONNE_A", "OUTPUT_1"):
        assert token in joined, token
    assert "IDENT" not in joined and not PLACEHOLDER_RE.search(joined)
    read = next(t for _e, t in with_values if t.startswith("[DOSSIER_1 / DOC_") and "Lettre fictive" in t)
    assert "Mme PERSONNE_A, ADRESSE_1." in read  # a document text keeps its codes too


def test_the_last_check_never_changes_a_shield_code_even_for_a_strong_value(tmp_path):
    other = _folder(tmp_path, "Autre", {"a.txt": "Acte fictif.\n"})
    mine = _folder(tmp_path, "Client", {"b.txt": "Note fictive.\n"})
    code_o = service.add_dossier(other)["code"]
    code_m = service.add_dossier(mine)["code"]
    _register(code_o, [("ORG", "DOSSIER"), ("PERSON", "PERSONNE"), ("ORG", "OUTPUT"), ("ORG", "IDENT")])
    text = "Voir DOSSIER_2, DOC_1, PERSONNE_A, IDENT_3, OUTPUT_1 et [PERSONNE], [IDENT]."
    assert service.default().guard_output(text, code_m) == text
    assert service.default().guard_output(text) == text
    # a real name of the other dossier next to a code is still replaced
    _register(code_o, [("PERSON", "Oswin Brakevald")])
    out = service.default().guard_output("DOC_1 cite Oswin Brakevald.", code_m)
    assert out.startswith("DOC_1 cite PERSONNE_") and "Brakevald" not in out


def test_l2_alone_keeps_dossier_codes_when_the_weak_rule_is_off(tmp_path, monkeypatch):
    """L2 holds on its own: with the weak-value rule switched off, "4" of another dossier still never touches
    DOSSIER_4, DOC_4 or OUTPUT_4 (it is still replaced in the prose: that is the L3 job)."""
    import ragbase_shield.engine.masker as masker_mod

    monkeypatch.setattr(masker_mod, "spreadable", lambda ents: list(ents))
    monkeypatch.setattr(service, "is_weak_value", lambda value: False)
    other = _folder(tmp_path, "Autre", {"a.txt": "Acte fictif.\n"})
    code_o = service.add_dossier(other)["code"]
    for i in range(3):
        service.add_dossier(_folder(tmp_path, f"Vide {i}", {"v.txt": "Rien.\n"}))
    _register(code_o, [("ID_CODE", "4")])
    out = service.default().guard_output("DOSSIER_4 : DOC_4, OUTPUT_4, 4 pièces.", "DOSSIER_4")
    assert out.startswith("DOSSIER_4 : DOC_4, OUTPUT_4, ") and not out.endswith(" 4 pièces."), out


def test_the_cause_with_the_three_layers_off_gives_the_owners_text(tmp_path, monkeypatch):
    """The cause, proven: with L2 and L3 switched off, a "4" registered in another dossier turns Shield's own
    "DOSSIER_4" into "DOSSIER_[IDENT]" (the text the owner saw), and into a new code of the dossier with one."""
    import ragbase_shield.engine.masker as masker_mod

    other = _folder(tmp_path, "Autre", {"a.txt": "Acte fictif.\n"})
    code_o = service.add_dossier(other)["code"]
    for i in range(3):
        service.add_dossier(_folder(tmp_path, f"Vide {i}", {"v.txt": "Rien.\n"}))
    _register(code_o, [("ID_CODE", "4")])
    text = "Le dossier choisi est maintenant protégé : DOSSIER_4."
    assert service.default().guard_output(text) == text  # 0.4.3
    monkeypatch.setattr(masker_mod, "spreadable", lambda ents: list(ents))
    monkeypatch.setattr(service, "is_weak_value", lambda value: False)
    monkeypatch.setattr(service, "shield_token_spans", lambda text: [])
    service.default()._rule_maskers.clear()
    assert service.default().guard_output(text) == "Le dossier choisi est maintenant protégé : DOSSIER_[IDENT]."
    minted = service.default().guard_output(text, "DOSSIER_4")
    assert re.fullmatch(r"Le dossier choisi est maintenant protégé : DOSSIER_IDENT_\d+\.", minted), minted


# ============================================================ (3) a weak value is masked at its place, never spread

def test_a_weak_value_is_masked_where_found_and_not_in_the_other_documents(tmp_path):
    f = _folder(tmp_path, "Client", {
        "a lettre.txt": "Me Lucie Vernat, avocat, toque 4.\n",
        "b note.txt": "Voir l'article 4 du code civil, le 13 mars 2026.\n",
    })
    code = service.add_dossier(f)["code"]
    _register(code, [("ID_CODE", "13")])  # a weak value already in the vault
    service.scan_dossier(code)
    docs = {d["masked_name"]: d["id"] for d in service.list_documents(code)}
    a = service.read_document(code, docs["a lettre.txt"])["text"]
    b = service.read_document(code, docs["b note.txt"])["text"]
    assert re.fullmatch(r"Me PERSONNE_A, avocat, toque IDENT_\d\.\n?", a), a
    assert b.strip() == "Voir l'article 4 du code civil, le 13 mars 2026."
    assert any(e["value"] == "4" and e["kind"] == "ID_CODE" for e in service.entities(code))


def test_the_masker_never_searches_for_a_weak_value():
    store = MemoryStore(locale="fr")
    for kind, value in (("ID_CODE", "4"), ("PERSON", "Li"), ("ORG", "3M"), ("ID_CODE", "35000"),
                        ("PERSON", "Odilon Quillardet"), ("ID_CODE", "AB-4512-77")):
        store.add(kind, value, entity_norm(kind, value))
    m = Masker(store, locale="fr", use_ner=False)
    text = "Voir l'article 4, la page 35000 et le 3M du dossier AB-4512-77 de M. Odilon Quillardet."
    masked = m.mask(text).text
    assert "article 4," in masked and "35000" in masked and " 3M " in masked
    assert "Quillardet" not in masked and "AB-4512-77" not in masked
    found = {sp.value for sp in m.scan(text)}
    assert "4" not in found and "35000" not in found and "3M" not in found
    assert "AB-4512-77" in found


@pytest.mark.parametrize("value,weak", [
    ("4", True), ("13", True), ("35000", True), ("12 345", True), ("1.2.3", True), ("A", True), ("Li", True),
    ("3M", True), ("J.-B.", True), ("123456", False), ("Suite", False), ("DOS", False), ("AB4", False),
    ("4 bis", False), ("Odilon", False), ("", True),
])
def test_the_weak_rule(value, weak):
    assert is_weak_value(value) is weak


def test_spreadable_is_the_one_list_the_masker_and_the_last_check_read():
    import inspect

    import ragbase_shield.engine.masker as masker_mod

    assert "spreadable(ents)" in inspect.getsource(masker_mod.Masker._lexicon)
    ents = [MemoryStore().add("ID_CODE", "4", "4"), MemoryStore().add("PERSON", "Odilon Prat", "odilon prat")]
    assert [e.value for e in spreadable(ents)] == ["Odilon Prat"]


def test_a_weak_value_is_never_made_into_an_entity_of_another_dossier(tmp_path):
    code = service.add_dossier(_folder(tmp_path, "Client", {"b.txt": "Note.\n"}))["code"]
    d = service.default().registry.get(code)
    assert service.default()._mint(d, "ID_CODE", "4") is None
    assert service.default()._mint(d, "PERSON", "Li") is None
    assert service.default()._mint(d, "PERSON", "Oswin Brakevald") is not None


# ============================================================ (4) the MCP server of Claude Desktop, Cowork...

def _mcp_run(root: Path, values, monkeypatch) -> list[tuple[bool, str]]:
    monkeypatch.setenv("RAGBASE_SHIELD_HOME", str(root / "data"))
    monkeypatch.delenv("RAGBASE_SHIELD_MULTI_DOSSIER", raising=False)
    monkeypatch.delenv("RAGBASE_SHIELD_DOSSIER", raising=False)
    service.reset()
    a = _folder(root, "Dossier Ancien", {"ancien.txt": "Courrier ancien fictif.\n"})
    _register(service.add_dossier(a)["code"], values)
    for i in range(2):
        service.add_dossier(_folder(root, f"Dossier Vide {i}", {"vide.txt": "Rien.\n"}))
    code = service.add_dossier(_folder(root, "Dossier Nouveau", B_FILES))["code"]
    assert code == "DOSSIER_4"
    service.scan_dossier(code)
    server = mcp_server.build_server()
    calls = [("shield_list_documents", {"dossier": code})]
    calls += [("shield_read_document", {"dossier": code, "document": f"DOC_{i}"}) for i in range(1, 6)]
    calls += [("shield_search", {"dossier": code, "query": "fictive"}),
              ("shield_save_draft", {"dossier": code, "title": "Projet 4",
                                     "content": "Texte pour PERSONNE_A, pièce 5 et [IDENT], DOC_1."}),
              ("shield_list_dossiers", None), ("shield_status", None)]
    out = [call(server, name, args) for name, args in calls]
    service.reset()
    return out


def test_weak_values_of_another_dossier_change_no_answer_of_the_mcp_server(tmp_path, monkeypatch):
    with_values = _mcp_run(tmp_path / "owner", WEAK_VALUES + CODE_VALUES, monkeypatch)
    empty = _mcp_run(tmp_path / "empty", [], monkeypatch)
    assert with_values == empty
    joined = "\n".join(t for _e, t in with_values)
    assert "DOSSIER_4 : 5 document(s)." in joined and "Voir l'article 4 du code civil" in joined
    assert "IDENT_" not in joined and "Quillardet" not in joined


# ============================================================ (5) the canary still works

def test_a_name_of_another_dossier_in_a_search_result_is_still_replaced(tmp_path, plugin_env):
    claude_tab.lock_settings(tmp_path / "data")
    a = _folder(tmp_path, "Dossier Ancien", {"ancien.txt": "Courrier ancien fictif.\n"})
    _register(service.add_dossier(a)["code"], [("PERSON", "Oswin Brakevald")] + WEAK_VALUES)
    b = _folder(tmp_path, "Dossier Nouveau", {"note.txt": "Note fictive : le rapport cite Brakevald 4 fois.\n"})
    claude_tab.PICKER = lambda title, timeout: str(b)
    server = claude_tab.build_server()
    call(server, "shield_protect_folder")
    assert service.wait_reading("DOSSIER_2", 30.0)
    err, text = call(server, "shield_search", {"dossier": "DOSSIER_2", "query": "rapport"})
    assert not err and "Brakevald" not in text and "DOSSIER_2 : 1 résultat(s)." in text
    assert re.search(r"le rapport cite PERSONNE_[A-Z]+ 4 fois\.", text), text
    err, text = call(server, "shield_read_document", {"dossier": "DOSSIER_2", "document": "DOC_1"})
    assert not err and "Brakevald" not in text and " 4 fois." in text


def test_content_parts_are_checked_and_the_frame_is_not(tmp_path):
    other = _folder(tmp_path, "Autre", {"a.txt": "Acte fictif.\n"})
    _register(service.add_dossier(other)["code"], [("PERSON", "Oswin Brakevald"), ("PERSON", "Suite")])
    mine = service.add_dossier(_folder(tmp_path, "Client", {"b.txt": "Note.\n"}))["code"]
    out = mcp_server._answer(["Suite : Brakevald | ", mcp_server.Content("Brakevald a écrit.")], mine)
    assert out.startswith("Suite : Brakevald | PERSONNE_") and out.endswith(" a écrit.")


# ============================================================ L4: the source of the short identifiers

@pytest.mark.parametrize("text", ["Voir Dalloz (T. 4), p. 35.", "Rapport annexe (T 13).", "Tableau (T. 2, ligne 20)",
                                  "(T4)", "( T 35 )", "(T. 1234, p. 3)"])
def test_a_tome_or_table_number_is_not_a_toque(text):
    got = [text[c.start:c.end] for c in det.detect_candidates(text, lang="fr") if c.valid and c.kind == "ID_CODE"]
    assert got == [], got
    m = Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False)
    assert m.mask(text).text == text and not m.store.all()


@pytest.mark.parametrize("text,value", [("Me Lantier (T 1234)", "1234"), ("Me Lantier (T. P 485)", "P 485"),
                                        ("toque 1234", "1234"), ("Toque n° B 33", "B 33")])
def test_real_toques_are_still_found(text, value):
    got = [text[c.start:c.end] for c in det.detect_candidates(text, lang="fr") if c.valid and c.kind == "ID_CODE"]
    assert value in got, got
