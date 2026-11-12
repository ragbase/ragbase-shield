"""Regression tests for the review of 2026-10-16 (leak hunt, French recall, install UX, correctness).

One test (or a small group) per finding. Synthetic data only: every name, company and number is invented.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import sys
import threading
import time
import types
import unicodedata
from pathlib import Path

import pytest

from ragbase_shield import cli, config, documents, hooks, service
from ragbase_shield import vault as V
from ragbase_shield.engine import Masker, MemoryStore, entity_norm, make_code
from ragbase_shield.engine.types import CODE_RE, CodeRangeError
from ragbase_shield.service import ShieldError

DOC = (
    "CONCLUSIONS POUR Madame Maëlle KERVADEC\n\n"
    "Madame Maëlle KERVADEC, née le 14 mars 1981, demeurant 12 rue des Tanneurs, 35000 Rennes,\n"
    "courriel maelle.kervadec@exemple-mail.fr, tél. 06 12 34 56 78.\n"
    "Contre la société VELTRANE INDUSTRIES SAS, SIREN 388 684 722, représentée par M. Octave LOUBRIAT.\n"
    "Mme Kervadec a été licenciée le 3 janvier 2026. M. Paul MARTIN, témoin, confirme les faits.\n"
)
SECRETS = ("Kervadec", "KERVADEC", "kervadec", "Veltrane", "VELTRANE", "veltrane", "Loubriat", "LOUBRIAT",
           "Atlantide", "atlantide", "Tanneurs", "388684722", "388 684 722", "0612345678", "06 12 34 56 78")


def leaks(output) -> list[str]:
    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    return [s for s in SECRETS if s in text]


def registered(*items) -> Masker:
    store = MemoryStore()
    for kind, value in items:
        store.add(kind, value, entity_norm(kind, value))
    return Masker(store, use_ner=False)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    for name in cli._AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    service.reset()
    yield
    service.reset()


@pytest.fixture
def case(tmp_path):
    folder = tmp_path / "dossiers" / "client-a"
    folder.mkdir(parents=True)
    (folder / "conclusions.txt").write_text(DOC, encoding="utf-8")
    code = service.add_dossier(folder, "Kervadec c. Veltrane Industries SAS")["code"]
    service.register(code, "ORG", "Atlantide")
    return {"folder": folder, "code": code, "tmp": tmp_path}


def run_cli(argv, capsys, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    return rc, out, err


def hook(event: str, payload) -> tuple[int, dict | None, str]:
    out, err = io.StringIO(), io.StringIO()
    rc = hooks.main(event, io.StringIO(json.dumps(payload)), out, err)
    text = out.getvalue()
    return rc, (json.loads(text) if text.strip() else None), text + err.getvalue()


# ============================================================================================ critical

def test_vault_changing_commands_are_refused_in_an_agent_shell(case, capsys, monkeypatch, tmp_path):
    """A model (or a prompt injection in a document) can never switch masking off from its shell."""
    code = case["code"]
    before = service.read_document(code, "DOC_1")["text"]
    monkeypatch.setenv("CLAUDECODE", "1")
    other = tmp_path / "autre"
    other.mkdir()
    for argv in (["keep-clear", code, "PERSONNE_A"], ["register", code, "--person", "Octave LOUBRIAT"],
                 ["add", str(other)], ["import", str(tmp_path / "x.shield")],
                 ["export", code, str(tmp_path / "y.shield")]):
        rc, out, err = run_cli(argv, capsys)
        assert rc == 3, argv
        assert not leaks(out + err)
    assert not (tmp_path / "y.shield").exists()
    service.reset()
    after = service.read_document(code, "DOC_1")["text"]
    assert after == before and not leaks(after)
    for command in (f"ragbase-shield keep-clear {code} PERSONNE_A", f"ragbase-shield register {code} --person X",
                    f"uvx ragbase-shield add {other}", "ragbase-shield import x.shield",
                    f"python -m ragbase_shield keep-clear {code} PERSONNE_A"):
        rc, data, _ = hook("pre-tool-use", {"tool_name": "Bash", "tool_input": {"command": command},
                                            "cwd": str(tmp_path)})
        assert rc == 2 and data["hookSpecificOutput"]["permissionDecision"] == "deny", command


FILE_NAMES = ["Kervadec-c-Veltrane.txt", "Conclusions-KERVADEC.txt", "Notes-Kervadec-2026.txt", "VELTRANE-Kbis.txt",
              "LOUBRIAT-Octave-attestation.txt", "Kervadec2026.txt", "2026Kervadec.txt", "MaelleKervadec.txt",
              "kervadec's notes.txt", "Atlantide-note.txt", "veltrane.txt", "Kervadec_c_Veltrane.txt"]


def test_masked_file_names_hold_no_registered_value(case):
    for name in FILE_NAMES:
        (case["folder"] / name).write_text("x", encoding="utf-8")
    rows = service.list_documents(case["code"])
    assert len(rows) == len(FILE_NAMES) + 1
    for r in rows:
        assert not leaks(r["masked_name"]) and not leaks(r["masked_path"]), r["masked_name"]
    names = {r["masked_name"] for r in rows}
    assert "PERSONNE_A-c-SOCIETE_A.txt" in names and "Conclusions-PERSONNE_A.txt" in names


def test_mask_text_without_a_dossier_still_hides_registered_values(case):
    text = "le projet Atlantide de veltrane ; Kervadec relance MARTIN ; contact maelle.kervadec@exemple-mail.fr"
    res = service.mask_text(text)
    assert not leaks(res["masked"]), res["masked"]
    assert "[SOCIETE]" in res["masked"] and "[PERSONNE]" in res["masked"]
    assert res["canary"] >= 3 and sum(res["counts"].values()) >= 4
    with_dossier = service.mask_text(text, case["code"])["masked"]
    assert "SOCIETE_B" in with_dossier and "PERSONNE_A" in with_dossier and not leaks(with_dossier)
    f = case["tmp"] / "Kervadec.txt"
    f.write_text(text, encoding="utf-8")
    item = service.mask_file(f)
    assert not leaks(item["masked_text"]) and not leaks(item["masked_name"])


@pytest.mark.parametrize("text", ["la SCI DU PARC", "la SARL DE LA GARE", "Bailleur : SCI DES LILAS",
                                  "LA SOCIÉTÉ DES TROIS CHÊNES", "GIE DU RHÔNE", "La SCI DU 12 RUE PASTEUR",
                                  "SAS DU", "SCI ET", "SARL DE", "la SCI D'ARMOR"])
def test_company_particles_never_crash(text):
    out = Masker(MemoryStore(), use_ner=False).mask(text).text
    assert out


def test_sci_du_parc_masks_the_particle_with_the_name():
    assert Masker(MemoryStore(), use_ner=False).mask("la SCI DU PARC").text == "la SCI SOCIETE_A"


def test_random_company_forms_never_crash():
    rnd = random.Random(1016)
    pieces = ["SAS", "SCI", "SARL", "GIE", "SELARL", "DU", "DE", "LA", "LES", "DES", "ET", "&", "M.", "Mme",
              "PARC", "GARE", "Lilas", "la", "société", "12", "RUE", "Maître", "D'", "AARPI", "–", ","]
    m = Masker(MemoryStore(), use_ner=False)
    for _ in range(3000):
        text = " ".join(rnd.choice(pieces) for _ in range(rnd.randint(1, 6)))
        m.mask(text)


def test_add_dossier_rolls_back_when_the_scan_fails(tmp_path, monkeypatch):
    folder = tmp_path / "f"
    folder.mkdir()
    (folder / "a.txt").write_text(DOC, encoding="utf-8")
    svc = service.default()

    def boom(d):
        raise RuntimeError("scan failed")

    monkeypatch.setattr(svc, "_scan", boom)
    with pytest.raises(ShieldError):
        svc.add_dossier(folder)
    assert svc.list_dossiers() == []


class _RacyKeyring:
    """Fake OS keychain: both callers read "no key", then both write (the second one 0.2 s later)."""

    def __init__(self):
        self.store: dict = {}
        self.lock = threading.Lock()
        self.sets = 0
        self.barrier = threading.Barrier(2)

    def get_password(self, service_name, user):
        value = self.store.get((service_name, user))
        if value is None and self.sets == 0:
            try:
                self.barrier.wait(timeout=1)
            except threading.BrokenBarrierError:
                pass
        return value

    def set_password(self, service_name, user, password):
        with self.lock:
            self.sets += 1
            n = self.sets
        if n == 2:
            time.sleep(0.2)
        self.store[(service_name, user)] = password


@pytest.mark.parametrize("registry_exists", [False, True])
def test_first_start_race_on_the_keychain_keeps_one_key(tmp_path, monkeypatch, registry_exists):
    fake = _RacyKeyring()
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=fake.get_password,
                                                                      set_password=fake.set_password))
    monkeypatch.setenv("RAGBASE_SHIELD_KEYRING", "1")
    home = tmp_path / "home"
    home.mkdir()
    if registry_exists:  # e.g. created by an earlier "doctor" run, without a key yet
        db = V._Db(home / "registry.db")
        db.schema(V._REGISTRY_SCHEMA)
        db.close()
    out: dict = {}

    def open_registry(name):
        try:
            out[name] = V.Registry(home)
        except Exception as exc:  # noqa: BLE001
            out[name] = exc

    threads = [threading.Thread(target=open_registry, args=(n,)) for n in ("desk", "mcp")]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(isinstance(r, V.Registry) for r in out.values()), out
    folder = tmp_path / "dossier"
    folder.mkdir()
    d = out["desk"].add_dossier(folder, "Dupont c. ACME SAS")
    d.register("PERSON", "Jean Dupont")
    for r in out.values():
        r.close()
    with V.Registry(home) as again:  # the next start opens the vault: the key was never lost
        assert [x.code for x in again.list()] == ["DOSSIER_1"]


# ============================================================================================ major: service

def test_search_never_confirms_a_guessed_name(case):
    code = case["code"]
    (case["folder"] / "attestation.txt").write_text(
        "Attestation de M. Octave LOUBRIAT pour Mme Maëlle KERVADEC, ancienne collègue.\n", encoding="utf-8")
    service.scan_dossier(code)
    p = next(m.group() for m in re.finditer(r"PERSONNE_[A-Z]+", service.read_document(code, "DOC_1")["text"]))
    results = {}
    for guess in ("Octave LOUBRIAT", "Octave LEBRUN", "Jean MARTIN"):
        results[guess] = [(r["document"], r["snippet"]) for r in service.search(code, f"{p} et M. {guess}")]
        assert not leaks(results[guess])
    assert results["Octave LOUBRIAT"] == results["Octave LEBRUN"] == results["Jean MARTIN"]
    assert service.search(code, "LOUBRIAT") == []


def test_a_damaged_vault_makes_every_model_facing_check_fail_closed(case, tmp_path):
    other = tmp_path / "b"
    other.mkdir()
    (other / "n.txt").write_text("Rien de client ici.\n", encoding="utf-8")
    code_b = service.add_dossier(other)["code"]
    d = service.default().registry.get(case["code"])
    vault_file = d._db.path
    service.reset()
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(vault_file) + suffix)
        if p.exists():
            p.write_bytes(b"\0" * 4096)
    for call in (lambda: service.scan_text("Écris à Maëlle KERVADEC"), lambda: service.protect("Mme Kervadec"),
                 lambda: service.default().guard_output("Mme Kervadec"),
                 lambda: service.read_document(code_b, "DOC_1")):
        with pytest.raises(ShieldError) as e:
            call()
        assert e.value.kind == "vault_error" and not leaks(str(e.value))
    service.reset()
    rc, data, text = hook("user-prompt-submit", {"prompt": "Écris à Maëlle KERVADEC"})
    assert rc == 2 and data["decision"] == "block" and not leaks(text)
    rc, data, text = hook("post-tool-use", {"tool_name": "Bash", "tool_response": {"stdout": "Mme Kervadec, 12 rue"}})
    assert data["continue"] is False and not leaks(text)
    assert service.list_dossiers()[0].get("error") == "vault_unreadable"  # display only: still listed


def test_masked_upload_names_never_hold_a_value(case, tmp_path):
    for name in ("veltrane.txt", "Atlantide-note.txt", "kervadec's notes.txt", "MaelleKervadec.txt", "Kervadec.txt"):
        f = tmp_path / "upload.txt"
        f.write_text("Bonjour.", encoding="utf-8")
        for d in (None, case["code"]):
            item = service.mask_file(f, d, name=name)
            assert not leaks(item["masked_name"]), (name, d, item["masked_name"])
            assert item["masked_name"].endswith(".txt")


def test_masked_upload_name_falls_back_to_a_neutral_name(case, tmp_path, monkeypatch):
    f = tmp_path / "u.txt"
    f.write_text("Bonjour.", encoding="utf-8")
    svc = service.default()
    monkeypatch.setattr(svc, "_has_registered", lambda text: True)  # the canary still sees something
    assert svc.mask_file(f, case["code"], name="Kervadec.txt")["masked_name"] == "document.txt"


def test_title_party_that_the_documents_found_as_a_company_is_not_a_person(tmp_path):
    folder = tmp_path / "Mercadier"
    folder.mkdir()
    (folder / "lettre.txt").write_text("La société Ateliers Brunelac SAS a écrit à M. Paul Mercadier.\n",
                                       encoding="utf-8")
    code = service.add_dossier(folder, "Mercadier c. Ateliers Brunelac")["code"]
    ents = service.entities(code)
    brunelac = [e for e in ents if "brunelac" in e["value"].lower()]
    assert [e["kind"] for e in brunelac] == ["ORG"], ents


def test_one_word_title_party_is_the_known_company(tmp_path):
    folder = tmp_path / "Kerdalis c. Vellarine"
    folder.mkdir()
    (folder / "a.txt").write_text("La société KERDALIS INDUSTRIES SAS contre la société VELLARINE DISTRIBUTION SAS, "
                                  "à l'enseigne « VELLARINE ».\n", encoding="utf-8")
    info = service.add_dossier(folder)
    assert info["parties"] == 0
    assert all(e["kind"] == "ORG" for e in service.entities(info["code"]) if "ell" in e["value"].lower()
               or "erd" in e["value"].lower())


def test_a_typed_title_for_a_registered_folder_is_kept_and_parsed(case):
    info = service.add_dossier(case["folder"], "Kervadec c. Brivalto Négoce SAS")
    assert info["existing"] and info["title_updated"] and info["parties"] == 1
    rows = service.list_dossiers(include_private=True)
    assert rows[0]["title"] == "Kervadec c. Brivalto Négoce SAS"
    assert any("Brivalto" in e["value"] for e in service.entities(case["code"]))


def test_document_too_large_is_refused_with_a_code(case, monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCUMENT_CHARS", 100)
    service.reset()
    with pytest.raises(ShieldError) as e:
        service.read_document(case["code"], "DOC_1")
    assert e.value.kind == "document_too_large" and "DOC_1" in str(e.value)


def test_nfd_text_is_masked_like_nfc(case):
    nfd = unicodedata.normalize("NFD", "Mme Maëlle KERVADEC et Mme Gaëlle Dénécé, à Rennes.")
    out = service.mask_text(nfd, case["code"])["masked"]
    assert "PERSONNE_A" in out and "Gaëlle" not in out and "Dénécé" not in out
    out = Masker(MemoryStore(), use_ner=False).mask(unicodedata.normalize("NFD", "Mme Hélène Lefèvre ... Me José Ibáñez"))
    assert out.text == "Mme PERSONNE_A ... Me PERSONNE_B"


# ============================================================================================ major: hooks

def test_post_tool_use_masks_number_leaves(case):
    resp = {"siren": 388684722, "tel": 612345678, "f": 388684722.0, "ok": True, "n": 3, "none": None}
    rc, data, text = hook("post-tool-use", {"tool_name": "mcp__other__crm", "tool_response": resp})
    new = data["hookSpecificOutput"]["updatedToolOutput"]
    assert new["siren"].startswith("SIREN_") and new["tel"].startswith("TEL_") and new["f"].startswith("SIREN_")
    assert new["ok"] is True and new["n"] == 3 and new["none"] is None
    assert not leaks(text)


def test_fail_closed_blanks_every_string_and_number(case, monkeypatch):
    monkeypatch.setattr(service, "default", lambda: (_ for _ in ()).throw(RuntimeError("Kervadec")))
    resp = {"stdout": "KERVADEC", "stderr": "388684722", "numLines": 612345678, "isImage": False,
            "Kervadec": "x", "items": [{"type": "text", "text": "Mme Kervadec"}]}
    rc, data, text = hook("post-tool-use", {"tool_name": "Bash", "tool_response": resp})
    new = data["hookSpecificOutput"]["updatedToolOutput"]
    assert data["continue"] is False and not leaks(text)
    assert new["stdout"] == new["stderr"] == hooks._REMOVED and new["numLines"] == 0 and new["isImage"] is False
    assert set(new) == {"stdout", "stderr", "numLines", "isImage", "champ_1", "items"}  # a key may be a value
    assert new["items"] == [{"type": hooks._REMOVED, "text": hooks._REMOVED}]


def test_shield_tools_are_not_scanned_twice_and_other_mcp_tools_are(case):
    resp = [{"type": "text", "text": "Mme Kervadec"}]
    assert hook("post-tool-use", {"tool_name": "mcp__ragbase-shield__shield_read_document",
                                  "tool_response": resp})[1] is None
    rc, data, text = hook("post-tool-use", {"tool_name": "mcp__ragbase-shield-evil__shield_read_document",
                                            "tool_response": resp})
    assert data and not leaks(text)


def test_hook_budgets_fail_closed(case, monkeypatch):
    monkeypatch.setattr(hooks, "MAX_PROMPT_CHARS", 50)
    monkeypatch.setattr(hooks, "MAX_RESULT_CHARS", 50)
    rc, data, text = hook("user-prompt-submit", {"prompt": "Bonjour " * 20})
    assert rc == 2 and data["decision"] == "block" and "trop long" in data["reason"]
    rc, data, text = hook("post-tool-use", {"tool_name": "Bash", "tool_response": {"stdout": "Mme Kervadec " * 20}})
    assert data["continue"] is False and not leaks(text)
    monkeypatch.setattr(hooks, "MAX_RESULT_CHARS", 10 ** 7)
    monkeypatch.setattr(hooks, "TIME_BUDGET_S", -1.0)
    rc, data, text = hook("post-tool-use", {"tool_name": "Bash", "tool_response": {"stdout": "Mme Kervadec"}})
    assert data["continue"] is False and not leaks(text)


@pytest.mark.parametrize("tool,ti", [
    ("Monitor", {"command": "tail -f {doc}"}),
    ("LSP", {"operation": "hover", "file_path": "{doc}", "line": 1}),
    ("LSP", {"uri": "file://{doc}"}),
    ("Artifact", {"file_path": "{doc}"}),
    ("Artifact", {"files": {"index.html": "{doc}"}}),
    ("SendUserFile", {"files": ["{doc}"]}),
    ("mcp__filesystem__read_file", {"path": "{doc}"}),
    ("mcp__filesystem__list_directory", {"path": "{parent}"}),
    ("mcp__filesystem__search_files", {"path": "{grand}", "pattern": "*.txt"}),
])
def test_pre_tool_use_covers_more_tools(case, tool, ti):
    places = {"{doc}": str(case["folder"] / "conclusions.txt"), "{parent}": str(case["folder"].parent),
              "{grand}": str(case["folder"].parent.parent)}

    def fill_in(v):  # on the values, not on the JSON text: a Windows path holds backslashes
        if isinstance(v, str):
            for k, p in places.items():
                v = v.replace(k, p)
            return v
        if isinstance(v, dict):
            return {k: fill_in(x) for k, x in v.items()}
        return [fill_in(x) for x in v] if isinstance(v, list) else v

    fill = fill_in(ti)
    rc, data, text = hook("pre-tool-use", {"tool_name": tool, "tool_input": fill, "cwd": "/"})
    assert rc == 2 and data["hookSpecificOutput"]["permissionDecision"] == "deny", (tool, ti)


def test_pre_tool_use_leaves_unrelated_tools_alone(case, tmp_path):
    for tool, ti in (("mcp__ragbase-shield__shield_read_document", {"dossier": "DOSSIER_1", "document": "DOC_1"}),
                     ("mcp__filesystem__read_file", {"path": str(tmp_path / "ailleurs.txt")}),
                     ("mcp__web__search", {"query": "jurisprudence prud'hommes / 2026"}),
                     ("SendUserFile", {"files": [str(tmp_path / "rapport.pdf")]})):
        rc, data, _ = hook("pre-tool-use", {"tool_name": tool, "tool_input": ti, "cwd": "/"})
        assert rc == 0 and data is None, tool


def test_hooks_exit_early_when_nothing_is_registered(monkeypatch):
    called = []
    monkeypatch.setattr(hooks, "_service", lambda: called.append(1))
    assert hooks.handle("user-prompt-submit", {"prompt": "Bonjour Maëlle"}).exit_code == 0
    assert hooks.handle("post-tool-use", {"tool_name": "Bash", "tool_response": {"stdout": "x"}}).output is None
    assert called == []


def test_pre_tool_use_does_not_load_the_engine(case):
    import subprocess

    code = ("import json, sys, io; from ragbase_shield import hooks; "
            "hooks.main('pre-tool-use', io.StringIO(json.dumps({'tool_name': 'Read', 'tool_input': "
            "{'file_path': '/etc/hosts'}})), io.StringIO(), io.StringIO()); "
            "print('ragbase_shield.engine.masker' in sys.modules)")
    env = dict(os.environ, RAGBASE_SHIELD_HOME=str(config.home()), RAGBASE_SHIELD_KEYRING="0")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    assert p.stdout.strip() == "False", p.stderr


# ============================================================================================ major: engine

@pytest.mark.parametrize("text", ["Kervadec's file", "KERVADEC’s notes", "Veltrane's offer", "KervadecMaelle",
                                  "OctaveLoubriat", "VeltraneIndustries", "@mkervadec a posté", "Kervadec2026",
                                  "Atlantide-note", "Mme Maëlle KERVA-\nDEC signe", "VELTRA-\nNE INDUSTRIES",
                                  "M. LOUB-\nRIAT", "Conclusions-KERVADEC"])
def test_glued_and_broken_forms_are_masked_and_seen_by_the_canary(text):
    m = registered(("PERSON", "Maëlle KERVADEC"), ("ORG", "VELTRANE INDUSTRIES SAS"), ("PERSON", "Octave LOUBRIAT"),
                   ("ORG", "Atlantide"))
    assert m.scan(text), text
    if text != "Conclusions-KERVADEC":  # a capitalised word glued before stays a compound name (the canary sees it)
        assert not leaks(m.mask(text).text), (text, m.mask(text).text)


def test_glued_codes_stay_readable_for_restore():
    m = registered(("PERSON", "Maëlle Kervadec"))
    for text in ("Kervadec2026.pdf", "2026Kervadec", "MmeKervadec"):
        masked = m.mask(text).text
        assert "PERSONNE_A" in masked and "Maëlle Kervadec" in m.unmask(masked), (text, masked)


def test_tribunal_de_commerce_roll_numbers_and_pourvoi_without_dot():
    m = Masker(MemoryStore(), use_ner=False)
    for text in ("RG : 2024J00817", "RG n° 2024J00817", "TC Lyon RG 2024J00817", "(RG n° 2024R00312)",
                 "Affaire liée : RG 2023F01234", "voir 2023L04567", "pourvoi n°21-12345"):
        out = m.mask(text).text
        assert "RG_" in out and not re.search(r"\d{5}", out), (text, out)


def test_siren_inside_an_euid():
    assert Masker(MemoryStore(), use_ner=False).mask("EUID : FR6901.832456719").text == "EUID : FR6901.SIREN_1"


def test_short_forms_with_particles_share_the_code():
    m = registered(("PERSON", "Jean-Baptiste Le Goff"), ("PERSON", "François-Xavier d'Orgeval"),
                   ("PERSON", "Hélène DE LA ROCHÈRE-VASSEUR"))
    out = m.mask("M. Le Goff ; M. d'Orgeval ; F.-X. d'Orgeval ; Me DE LA ROCHÈRE-VASSEUR (T 1187) ; "
                 "Me Rochère-Vasseur").text
    assert out.count("PERSONNE_A") == 1 and out.count("PERSONNE_B") == 2 and out.count("PERSONNE_C") == 2, out
    assert len([e for e in m.store.all() if e.kind == "PERSON"]) == 3


def test_surname_seen_first_then_the_full_name_keeps_one_code(case):
    m = Masker(MemoryStore(), use_ner=False)
    assert m.mask("M. Ouardi écrit.").text == "M. PERSONNE_A écrit."
    assert m.mask("Mehdi Ouardi signe. M. Ouardi aussi.").text == "PERSONNE_A signe. M. PERSONNE_A aussi."
    assert [e.value for e in m.store.all()] == ["Mehdi Ouardi"]  # the value was upgraded
    # the same with the encrypted vault
    d = service.default().registry.get(case["code"])
    vm = Masker(d, use_ner=False)
    first = vm.mask("M. Quellerin est absent.").text
    code = re.search(r"PERSONNE_[A-Z]+", first).group()
    assert vm.mask("Bastien Quellerin confirme.").text == f"{code} confirme."
    assert d.get_by_code(code).value == "Bastien Quellerin"


def test_firms_joined_by_ampersand():
    m = Masker(MemoryStore(), use_ner=False)
    for text in ("CASTAGNÈDE & LHOMME – SELAS d'avocats", "CASTAGNÈDE & LHOMME, SELAS", "CASTAGNÈDE & LHOMME (SELAS)",
                 "PERNAUD & VALETTE, société d'exercice libéral à responsabilité limitée",
                 "AARPI MOREL & ROUX AVOCATS"):
        out = Masker(MemoryStore(), use_ner=False).mask(text).text
        assert out.startswith(("SOCIETE_A", "AARPI SOCIETE_A")) and "&" not in out, (text, out)
    out = m.mask("SELARL PERNAUD & VALETTE\nPERNAUD & VALETTE\nConstat").text
    assert out == "SELARL SOCIETE_A\nSOCIETE_A\nConstat"
    known = registered(("PERSON", "Pierre-Alain Castagnède"), ("PERSON", "Inès Lhomme"))
    assert known.mask("CASTAGNÈDE & LHOMME – SELAS d'avocats").text.startswith("SOCIETE_A")


def test_a_new_name_broken_by_a_line_break():
    out = Masker(MemoryStore(), use_ner=False).mask("M. Jean\nMOREL-DUVAL a signé.").text
    assert out == "M. PERSONNE_A a signé."
    # a signature (first name, then a company on the next line) is not joined
    out = Masker(MemoryStore(), use_ner=False).mask("Cordialement,\nJean-Pierre\nBrivanor Logistique - 01 99 00 31 87")
    assert "Brivanor" not in out.text
    assert not [e for e in out.new_entities if e.kind == "PERSON" and "Brivanor" in e.value]


@pytest.mark.parametrize("text,expected", [
    ("Maître Hélène de La Rochère‑Vasseur", "Maître PERSONNE_A"),
    ("M. Ber­trand Fré­miot", "M. PERSONNE_A"),
    ("Me Pierre‐Alain Castagnède", "Me PERSONNE_A"),
])
def test_unicode_hyphens_and_soft_hyphens(text, expected):
    assert Masker(MemoryStore(), use_ner=False).mask(text).text == expected


def test_m_dot_stays_a_title_for_a_first_name_starting_with_m():
    m = registered(("PERSON", "Mehdi Ouardi"))
    assert m.mask("pour le volet salarial de M. Ouardi").text == "pour le volet salarial de M. PERSONNE_A"
    out = m.mask("Attestation de M. Mehdi Ouardi. M. Ouardi a signé.").text
    assert out == "Attestation de M. PERSONNE_A. M. PERSONNE_A a signé."
    assert m.unmask(out) == "Attestation de M. Mehdi Ouardi. M. Mehdi Ouardi a signé."


def test_escape_matches_what_restore_reads():
    m = Masker(MemoryStore(), use_ner=False)
    text = ("Contact : jean.dupont@exemple-client.fr. Variables : USER_EMAIL_1, CFG_PERSONNE_A, PERSONNE_Ab, "
            "TEL_1er, SITE_1_old, PERSONNE_A1.")
    masked = m.mask(text).text
    restored = m.unmask(masked)
    # every code-like word of the real text was escaped, so restore never writes a client value into it
    assert restored.count("jean.dupont@exemple-client.fr") == 1 and "@" not in restored.split(".", 1)[1][30:]
    for escaped in ("USER_EMAIL-1", "CFG_PERSONNE-A", "PERSONNE-Ab", "TEL-1er", "SITE-1_old", "PERSONNE-A1"):
        assert escaped in masked and escaped in restored, escaped


def test_restore_reads_mangled_codes_and_reports_near_misses():
    m = registered(("PERSON", "Paul Rivière"))
    text, unknown = m.unmask_report("PERSONNE\\_A, PERSONNE_​A, PERSONNE＿A et personne_a.")
    assert text.count("Paul Rivière") == 3 and "personne_a" in unknown


def test_code_ranges_are_the_same_everywhere():
    assert CODE_RE.fullmatch("PERSONNE_AAAA") and CODE_RE.fullmatch("EMAIL_999999") and CODE_RE.fullmatch("DOSSIER_10000")
    store = MemoryStore()
    store._counts["EMAIL"] = 10_000
    store._counts["PERSON"] = 18_278
    m = Masker(store, use_ner=False)
    masked = m.mask("Écrire à a.b@exemple-mail.fr et à Mme Lucie Trivelon.").text
    assert "EMAIL_10001" in masked and "PERSONNE_AAAA" in masked
    restored, unknown = m.unmask_report(masked)
    assert "a.b@exemple-mail.fr" in restored and "Lucie Trivelon" in restored and not unknown
    with pytest.raises(CodeRangeError):
        make_code("PERSON", 26 + 26 ** 2 + 26 ** 3 + 26 ** 4)
    assert documents._DOSSIER_CODE_RE.match("DOSSIER_123456")


def test_masker_construction_never_loads_a_ner_model(monkeypatch):
    from ragbase_shield.engine import masker as mk

    loads = []
    monkeypatch.setattr(mk, "ner_installed", lambda model="auto": True)
    monkeypatch.setattr(mk.nr, "load_backend", lambda *a, **k: loads.append(1))  # v0.2: engine/ner.py backends
    m = Masker(MemoryStore())
    assert m.mode.startswith("rules+ner") and loads == []
    Masker(MemoryStore(), use_ner=False).scan("Mme Lucie Trivelon")
    assert loads == []


# ============================================================================================ minor: engine

@pytest.mark.parametrize("text,leak", [
    ("Nom, prénoms : FRÉMIOT Bertrand, Louis, Marie\n", "Louis"),
    ("Code de vérification : Hk7Rq2LmWz", "Hk7Rq2LmWz"),
    ("R.C.S. Lyon - Numéro de gestion 2017 B 04512", "04512"),
    ("Me Durand (Toque 1187)", "1187"),
    ("Les fonds peuvent être virés sur fr76 3000 6000 0112 3456 7890 189", "0112"),
    ("NIR 2 81 07 69 123 045 / 48", "045"),
    ("Le gérant, né en 1968, a signé.", "1968"),
    ("permis n° 120569300123", "120569300123"),
    ("dont le siège social est à Francheville (69340), 31 bis, chemin de la Garenne", "Francheville"),
    ("Présents : Claire Fontaine, Pierre Lenoir et Rose Marchand.", "Fontaine"),
    ("Avis client signé « Martine G. »", "Martine"),
    ("Signé : J. Morel", "Morel"),
    ("Bonjour Corinne,\nmerci.", "Corinne"),
    ("floqué au nom de TRANSPORTS GRAVELOTTE", "GRAVELOTTE"),
    ("le Garage Gravelotte et la Pharmacie Rouvière", "Rouvière"),
    ("L'association Les Amis du Vieux Bron a écrit.", "Bron"),
    ("Kerdalis (ci-après « Kerdalis ») livre.", "Kerdalis"),
])
def test_more_values_are_found_without_registration(text, leak):
    out = Masker(MemoryStore(), use_ner=False).mask(text).text
    assert leak not in out, (text, out)


@pytest.mark.parametrize("text", [
    "titulaire d'un office à la résidence de Lyon",
    "Jurisprudences Perruche, Blanco, Nicolo, Jacques Vabre et Manoukian.",
    "le Tribunal de commerce de Lyon et la Cour de cassation",
    "Hôtel de Ville",
])
def test_public_wording_stays_in_clear(text):
    assert Masker(MemoryStore(), use_ner=False).mask(text).text == text


def test_toque_numbers_can_stay_visible(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_MASK_TOQUE", "0")
    assert Masker(MemoryStore(), use_ner=False).mask("(Toque 1187)").text == "(Toque 1187)"


def test_registered_trade_name_matches_without_the_trade_noun():
    m = registered(("PERSON", "Martine Gauthier"), ("ORG", "TRANSPORTS GRAVELOTTE"))
    assert m.mask("Avis client signé « Martine G. » ; Gravelotte facture.").text == \
        "Avis client signé « PERSONNE_A » ; SOCIETE_A facture."


# ============================================================================================ vault

def test_vault_entity_creation_is_not_quadratic(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "off")  # the vault is measured, not an optional model
    folder = tmp_path / "liste"
    folder.mkdir()
    lines = [f"{i}. Mme Lucie Nomtest{i:04d}x, e-mail p{i}@client-exemple.fr" for i in range(400)]
    (folder / "liste.txt").write_text("Liste\n" + "\n".join(lines) + "\n", encoding="utf-8")
    t = time.time()
    info = service.add_dossier(folder)
    assert info["entities"] >= 800 and time.time() - t < 20


def test_snapshot_sees_entities_added_by_another_connection(case):
    d1 = service.default().registry.get(case["code"])
    n = len(d1.all())
    d1.journal("read_document", chars=1)  # a journal write must not force a full decrypt
    snap = d1._snap
    assert d1.all() and d1._snap is snap
    with V.Registry(config.home()) as other:
        other.get(case["code"]).register("PERSON", "Lucie Trivelon")
    assert len(d1.all()) == n + 1 and any(e.value == "Lucie Trivelon" for e in d1.all())


def test_upgrade_keeps_a_kept_clear_choice(case):
    d = service.default().registry.get(case["code"])
    ent = d.register("PERSON", "Quellerin")
    d.keep_clear(ent.code)
    new = d.upgrade(ent.code, "Bastien Quellerin", entity_norm("PERSON", "Bastien Quellerin"))
    assert new.code == ent.code and new.value == "Bastien Quellerin" and d.is_kept_clear(new.norm)


def test_two_registries_created_at_once_both_open(tmp_path):
    home = tmp_path / "fresh"
    out = []

    def go():
        try:
            out.append(V.Registry(home))
        except Exception as exc:  # noqa: BLE001
            out.append(exc)

    threads = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(isinstance(r, V.Registry) for r in out), out
    for r in out:
        r.close()


def test_get_document_finds_a_file_stored_in_nfd(case, monkeypatch):
    nfc = "Pièce élève.txt"
    (case["folder"] / nfc).write_text("x", encoding="utf-8")
    d = service.default().registry.get(case["code"])
    ref = next(r for r in d.documents() if r.rel == nfc)
    real_is_file = Path.is_file

    def is_file(self):  # a file system that keeps the NFD name: the NFC path does not exist
        return False if self.name == nfc else real_is_file(self)

    on_disk = case["folder"] / unicodedata.normalize("NFD", nfc)
    if not on_disk.exists():  # NTFS and ext4 keep names as written (the NFD name is another file); APFS: same file
        on_disk.write_text("x", encoding="utf-8")
    monkeypatch.setattr(Path, "is_file", is_file)
    monkeypatch.setattr(d, "_scan_folder", lambda: {nfc: (on_disk, 1)})
    monkeypatch.setattr(V, "_inside", lambda p, root: True)
    got = d.get_document(ref.id)
    assert got is not None and got.path == on_disk


def test_windows_data_folder_is_local_and_moved_once(tmp_path, monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_HOME", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    roaming, local = tmp_path / "Roaming", tmp_path / "Local"
    (roaming / "ragbase-shield").mkdir(parents=True)
    (roaming / "ragbase-shield" / "registry.db").write_bytes(b"x")
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    home = config.home()
    assert home == local / "ragbase-shield" and (home / "registry.db").exists()
    assert not (roaming / "ragbase-shield").exists()


# ============================================================================================ CLI, Desk, docs

def test_mask_summary_separates_codes_and_mentions(case, capsys, monkeypatch):
    text = "Les Ateliers Brunelac SAS écrivent. ATELIERS BRUNELAC répond. M. Mercadier aussi."
    rc, out, err = run_cli(["mask", "--dossier", case["code"], "-"], capsys, text, monkeypatch)
    assert rc == 0 and re.search(r"\d+ code\(s\), \d+ remplacement\(s\) \((?:Sociétés|Personnes) \d", err), err


def test_doctor_checks_that_the_configured_command_starts(capsys, tmp_path, monkeypatch):
    fake_home = tmp_path / "user"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))  # Windows: the home and the Claude Desktop folder
    monkeypatch.setenv("APPDATA", str(fake_home / "AppData" / "Roaming"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))
    path = cli.claude_desktop_config_path()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mcpServers": {"ragbase-shield": {"command": "/opt/uv/bin/uvx",
                                                                  "args": ["ragbase-shield", "mcp"]}}}),
                    encoding="utf-8")
    seen = []

    def fake_run(cmd, timeout=180):
        seen.append(cmd)
        return 2, "error: ragbase-shield was not found in the package registry"

    monkeypatch.setattr(cli, "_run_cmd", fake_run)
    rc, out, _ = run_cli(["doctor"], capsys)
    assert rc == 1 and "FAIL  Claude Desktop : démarrage du serveur" in out and "uv tool install" in out
    assert seen == [["/opt/uv/bin/uvx", "--offline", "ragbase-shield", "--version"]]
    monkeypatch.setattr(cli, "_run_cmd", lambda cmd, timeout=180: (0, "ragbase-shield 0.3.1"))
    rc, out, _ = run_cli(["doctor"], capsys)
    assert "OK    Claude Desktop : démarrage du serveur" in out
    assert re.search(r"OK    mcp : \d+\.\d+", out)  # a real version, not "installé"


def test_doctor_reads_claude_config_dir(capsys, tmp_path, monkeypatch):
    cfg = tmp_path / "cc"
    cfg.mkdir()
    (cfg / "settings.json").write_text(json.dumps({"enabledPlugins": {"ragbase-shield@ragbase": True}}),
                                       encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    monkeypatch.setenv("HOME", str(tmp_path / "nobody"))
    rc, out, _ = run_cli(["doctor"], capsys)
    assert "OK    Claude Code : configuré" in out


def test_codex_install_without_tomllib_never_adds_a_second_table(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    path = cli.codex_config_path()
    path.parent.mkdir(parents=True)
    path.write_text('[mcp_servers]\nragbase-shield = { command = "old", args = [] }\n', encoding="utf-8")
    monkeypatch.setattr(cli, "_toml_load", lambda text: None)  # Python 3.10: no tomllib
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/opt/uv/bin/uvx" if name == "uvx" else None)
    before = path.read_text(encoding="utf-8")
    rc, out, err = run_cli(["install", "codex"], capsys)
    assert rc == 1 and path.read_text(encoding="utf-8") == before


def test_install_claude_code_without_a_checkout_says_no_hooks(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_repo_root", lambda: None)
    monkeypatch.delenv("RAGBASE_SHIELD_MARKETPLACE", raising=False)
    rc, out, _ = run_cli(["install", "claude-code", "--dry-run"], capsys)
    assert rc == 0 and "SANS les hooks" in out


def test_pypdf_warnings_are_silenced():
    import logging

    assert logging.getLogger("pypdf").getEffectiveLevel() >= logging.ERROR


def test_desk_page_never_says_no_dossier_when_the_list_was_not_read():
    js = (Path(service.__file__).parent / "desk" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'if (state.conn !== "ok")' in js and "dos_locked" in js
    assert "function dedupeJournal" in js and "lastDossier()" in js
    assert "ragbase-shield desk »" not in js.replace("uvx ragbase-shield desk »", "")


def test_extension_handles_drop_html_files_and_beforeinput():
    js = (Path(__file__).resolve().parents[1] / "integrations" / "browser-extension" / "content.js").read_text(
        encoding="utf-8")
    for needle in ("addEventListener('drop'", "addEventListener('beforeinput'", "function htmlToText",
                   "blockFiles(", "'FILE'"):
        assert needle in js, needle
    assert "if (!text) return; // images or files only" not in js
