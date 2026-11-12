"""v0.2 NER layer: backends, chunking, offsets, merge rules and precision guards (owner: NER builder).

Invented data only. The real-model tests run when a GLiNER model is cached (RAGBASE_SHIELD_MODELS_DIR or the
default models directory) and the ``ner`` extra is installed; otherwise they are skipped, never failed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import merge as mg
from ragbase_shield.engine import ner
from ragbase_shield.engine import names as nm
from ragbase_shield.engine.normalize import fold, tokens

LEX = Path(ner.__file__).resolve().parent / "lexicon"  # the package that runs (source tree or installed wheel)


# ---------------------------------------------------------------------------
# Helpers: fake backends
# ---------------------------------------------------------------------------


def _spans_for(chunk: str, wanted: list[tuple[str, str, float]]) -> list[tuple[int, int, str, float]]:
    """Every occurrence of each wanted text inside the chunk, as (start, end, label, score)."""
    out = []
    for text, label, score in wanted:
        i = chunk.find(text)
        while i != -1:
            out.append((i, i + len(text), label, score))
            i = chunk.find(text, i + 1)
    return out


def fake_backend(wanted: list[tuple[str, str, float]], labels=None, name="fake", thresholds=None, calls=None):
    labels = labels or ner.KIND_FASTINO

    def fn(chunks):
        if calls is not None:
            calls.append(list(chunks))
        return [_spans_for(c, wanted) for c in chunks]

    return ner.CallableBackend(fn, labels, name=name, thresholds=thresholds)


def _span(text: str, needle: str, kind: str, label: str = "person", score: float = 0.9, nth: int = 0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(needle, i + 1)
    return (i, i + len(needle), kind, label, score)


def _kept(text, spans, **kw):
    return {text[m.start:m.end]: m.kind for m in mg.guard_ner_spans(text, spans, **kw)}


# ---------------------------------------------------------------------------
# Settings, status, graceful absence
# ---------------------------------------------------------------------------


def test_settings_defaults(monkeypatch):
    for k in ("RAGBASE_SHIELD_NER", "RAGBASE_SHIELD_NER_MODEL", "RAGBASE_SHIELD_NER_MAX_CHARS",
              "RAGBASE_SHIELD_NER_THREADS"):
        monkeypatch.delenv(k, raising=False)
    assert ner.ner_setting() == "auto"
    assert ner.ner_model_setting() == "auto"
    assert ner.ner_max_chars() == 200_000
    assert ner.ner_threads() == 0  # 0 = the library default (physical cores), measured fastest
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "OFF")
    assert ner.ner_setting() == "off"
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "1")
    assert ner.ner_setting() == "on"
    monkeypatch.setenv("RAGBASE_SHIELD_NER_MODEL", "urchade")
    assert ner.ner_model_setting() == "urchade"
    monkeypatch.setenv("RAGBASE_SHIELD_NER_MODEL", "weird")
    assert ner.ner_model_setting() == "auto"
    monkeypatch.setenv("RAGBASE_SHIELD_NER_MAX_CHARS", "500")
    assert ner.ner_max_chars() == 500
    monkeypatch.setenv("RAGBASE_SHIELD_NER_THREADS", "3")
    assert ner.ner_threads() == 3


def test_models_dir_env_and_default(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_MODELS_DIR", str(tmp_path / "m"))
    assert ner.models_dir() == tmp_path / "m"
    monkeypatch.delenv("RAGBASE_SHIELD_MODELS_DIR", raising=False)
    assert ner.models_dir().name == "models"  # under RAGBASE_SHIELD_HOME (set by conftest)


def test_absent_model_is_graceful(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_MODELS_DIR", str(tmp_path / "empty"))
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "nohub"))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setattr(ner, "_spacy_model_name", lambda: None)
    assert ner.snapshot_dir(ner.MODELS["fastino"]) is None
    assert ner.resolve_model("auto") is None
    assert ner.resolve_model("fastino") is None
    assert ner.ner_installed() is False
    assert ner.load_backend("auto") is None
    assert ner.ner_available("urchade") is False
    st = ner.status()
    assert st["mode"] == "rules" and st["backend"] is None
    assert st["models"]["fastino"]["cached"] is False
    lines = ner.status_lines("fr")
    assert lines[0][0] == "INFO" and "ner download" in lines[0][2]
    assert "torch" not in sys.modules or True  # the check never loads torch; see test below


def test_installed_check_never_imports_torch(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_MODELS_DIR", str(tmp_path / "empty"))
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "nohub"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    before = set(sys.modules)
    ner.ner_installed("fastino")
    ner.status("fastino")
    assert not ({"torch", "gliner", "gliner2", "transformers"} & (set(sys.modules) - before))


def test_off_setting_disables_everything(monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_NER", "off")
    assert ner.ner_installed() is False
    assert ner.load_backend() is None
    assert ner.status()["mode"] == "rules"
    assert ner.status_lines("en")[0][2].startswith("disabled")


def test_snapshot_dir_finds_hub_layout_and_plain_folder(tmp_path):
    spec = ner.MODELS["fastino"]
    root = tmp_path / "models"
    snap = root / "models--fastino--gliner2-privacy-filter-PII-multi" / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    assert ner.snapshot_dir(spec, roots=[root]) is None  # no weights yet
    (snap / "config.json").write_text("{}", encoding="utf-8")
    (snap / "model.safetensors").write_bytes(b"\0")
    assert ner.snapshot_dir(spec, roots=[root]) == snap
    refs = root / "models--fastino--gliner2-privacy-filter-PII-multi" / "refs"
    refs.mkdir()
    (refs / "main").write_text("abc123\n", encoding="utf-8")
    assert ner.snapshot_dir(spec, roots=[root]) == snap
    plain = tmp_path / "plain" / "gliner2-privacy-filter-PII-multi"
    plain.mkdir(parents=True)
    (plain / "config.json").write_text("{}", encoding="utf-8")
    (plain / "model.safetensors").write_bytes(b"\0")
    assert ner.snapshot_dir(spec, roots=[tmp_path / "plain"]) == plain


def test_download_dry_run_makes_no_network_call(tmp_path, capsys):
    out = ner.download_model("all", models_dir_path=tmp_path / "dl", dry_run=True)
    assert out == []
    text = capsys.readouterr().out
    assert "fastino/gliner2-privacy-filter-PII-multi" in text and "urchade/gliner_multi_pii-v1" in text
    assert "Apache-2.0" in text
    with pytest.raises(ValueError):
        ner.download_model("nope", models_dir_path=tmp_path, dry_run=True)


def test_label_maps_cover_the_design_kinds():
    kinds = set(ner.KIND_FASTINO.values())
    assert {"PERSON", "ORG", "EMAIL", "PHONE", "ADDRESS", "BIRTHDATE", "USERNAME", "EMPLOYEE_ID",
            "ACCOUNT_NUMBER", "ID_CODE"} == kinds
    assert set(ner.KIND_URCHADE.values()) == kinds
    for ignored in ("city", "country", "postal_code", "card_number", "iban", "document_date"):
        assert ignored not in ner.KIND_FASTINO


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _check_chunks(text, max_chars):
    pieces = ner.chunk_text(text, max_chars)
    assert "".join(c for _o, c in pieces) == text
    pos = 0
    for off, chunk in pieces:
        assert off == pos and text[off:off + len(chunk)] == chunk
        assert 0 < len(chunk) <= max_chars
        pos += len(chunk)
    return pieces


def test_chunk_prefers_blank_line_then_line_then_sentence_then_space():
    para = "Première phrase de test. Deuxième phrase de test ! Troisième ?\n"
    text = (para * 3) + "\n" + (para * 3)
    pieces = _check_chunks(text, 220)
    assert all(c.endswith("\n") for _o, c in pieces[:-1])
    one_line = "Mot " * 200
    pieces = _check_chunks(one_line, 100)
    assert all(c.endswith(" ") for _o, c in pieces[:-1])
    sentences = "Phrase une. " * 40
    pieces = _check_chunks(sentences.strip(), 100)
    assert all(c.endswith(". ") for _o, c in pieces[:-1])


def test_chunk_hard_cut_without_any_separator_and_small_inputs():
    text = "x" * 3005
    pieces = _check_chunks(text, 1000)
    assert [len(c) for _o, c in pieces] == [1000, 1000, 1000, 5]
    assert ner.chunk_text("", 100) == []
    assert ner.chunk_text("court", 100) == [(0, "court")]
    with pytest.raises(ValueError):
        ner.chunk_text("abc", 4)


def test_chunk_cut_stays_in_the_last_two_thirds():
    text = "a\n" + "b" * 200 + " " + "c" * 50
    pieces = _check_chunks(text, 120)
    assert len(pieces[0][1]) > 40  # the newline at offset 1 is too early to be used


# ---------------------------------------------------------------------------
# run_ner: offsets, exact match, thresholds, label map, cache
# ---------------------------------------------------------------------------


def test_run_ner_maps_offsets_across_chunks_and_sorts():
    text = ("Bonjour. " * 30) + "Rendez-vous avec Clotilde Berrivan demain.\n\n" + ("Suite. " * 30) \
           + "Contact : Kalvenor Industrie.\n"
    backend = fake_backend([("Clotilde Berrivan", "person", 0.9), ("Kalvenor Industrie", "organization", 0.8)])
    spans = ner.run_ner(text, backend, max_chars=200, cache=None)
    assert [(text[s:e], k, lab, sc) for s, e, k, lab, sc in spans] == [
        ("Clotilde Berrivan", "PERSON", "person", 0.9), ("Kalvenor Industrie", "ORG", "organization", 0.8)]
    assert spans == sorted(spans)


def test_run_ner_drops_spans_whose_text_is_not_at_the_offsets():
    text = "Clotilde Berrivan signe."

    def fn(chunks):
        return [[(0, 8, "person", 0.9), (9, 17, "person", 0.9), (30, 40, "person", 0.9), (5, 3, "person", 0.9)]
                for _ in chunks]

    backend = ner.CallableBackend(fn, ner.KIND_FASTINO)
    got = ner.run_ner(text, backend, cache=None)
    assert [text[s:e] for s, e, *_ in got] == ["Clotilde", "Berrivan"]


def test_backend_exact_text_check():
    # a backend whose returned text does not match the chunk at its offsets: the span is dropped
    chunk = "Clotilde Berrivan signe."
    assert ner._clean_span(chunk, 0, 8, "Clotilde") == (0, 8)
    assert ner._clean_span(chunk, 0, 8, "Berrivan") is None
    assert ner._clean_span(chunk, 0, 9, None) == (0, 8)  # trailing space trimmed
    assert ner._clean_span(chunk, -1, 8, None) is None
    assert ner._clean_span(chunk, 8, 9, None) is None  # whitespace only


def test_run_ner_thresholds_label_map_and_kind_filter():
    text = "Clotilde Berrivan, Kalvenor Industrie, clotilde@exemple-mail.fr, ville de Lyon."
    backend = fake_backend([("Clotilde Berrivan", "person", 0.45), ("Kalvenor Industrie", "organization", 0.55),
                            ("clotilde@exemple-mail.fr", "email", 0.9), ("Lyon", "city", 0.99)])
    got = ner.run_ner(text, backend, cache=None)
    kinds = {text[s:e]: k for s, e, k, *_ in got}
    assert kinds == {"Clotilde Berrivan": "PERSON", "clotilde@exemple-mail.fr": "EMAIL"}  # ORG 0.55 < 0.60, city ignored
    got = ner.run_ner(text, backend, kinds=("PERSON",), cache=None)
    assert [text[s:e] for s, e, *_ in got] == ["Clotilde Berrivan"]
    strict = fake_backend([("Clotilde Berrivan", "person", 0.45)], thresholds={"PERSON": 0.5})
    assert ner.run_ner(text, strict, cache=None) == []


def test_run_ner_keeps_best_score_for_one_span_with_two_labels():
    text = "Clotilde Berrivan"
    backend = fake_backend([("Clotilde Berrivan", "person", 0.6), ("Clotilde Berrivan", "full_name", 0.8)])
    got = ner.run_ner(text, backend, cache=None)
    assert got == [(0, 17, "PERSON", "full_name", 0.8)]


def test_run_ner_cache_hits_and_batches():
    text = ("Paragraphe de test avec Clotilde Berrivan.\n\n" * 40)
    calls: list = []
    backend = fake_backend([("Clotilde Berrivan", "person", 0.9)], calls=calls)
    cache = ner.ChunkCache(max_items=8)
    first = ner.run_ner(text, backend, max_chars=300, batch_size=4, cache=cache)
    n_chunks = len(ner.chunk_text(text, 300))
    assert sum(len(c) for c in calls) == n_chunks and all(len(c) <= 4 for c in calls)
    assert len(first) == 40
    calls.clear()
    second = ner.run_ner(text, backend, max_chars=300, batch_size=4, cache=cache)
    assert second == first
    assert cache.hits > 0 and len(cache) <= 8  # bounded; identical chunks share one key
    assert sum(len(c) for c in calls) <= n_chunks


def test_cache_key_holds_no_text():
    key = ner.ChunkCache.key("fake", ["person"], "Clotilde Berrivan")
    assert len(key) == 64 and "Clotilde" not in key


def test_run_ner_skips_blank_chunks_and_empty_text():
    calls: list = []
    backend = fake_backend([], calls=calls)
    assert ner.run_ner("", backend, cache=None) == []
    assert ner.run_ner("\n\n   \n", backend, cache=None) == []
    assert calls == []
    assert ner.run_ner("x", None, cache=None) == []


# ---------------------------------------------------------------------------
# Merge: trim, overlaps, stop lists, rules win
# ---------------------------------------------------------------------------


def test_trim_titles_legal_forms_articles_and_punctuation():
    text = "« Maître Vorande », la société Kalvenor Industrie SAS, (Mme Clotilde Berrivan's)"
    assert text[slice(*mg.trim_span(text, 0, text.index("»") + 1, "PERSON"))] == "Vorande"
    s = text.index("la société")
    e = text.index("SAS") + 3
    assert text[slice(*mg.trim_span(text, s, e, "ORG"))] == "Kalvenor Industrie"
    s = text.index("(Mme")
    assert text[slice(*mg.trim_span(text, s, len(text), "PERSON"))] == "Clotilde Berrivan"
    en = "Dr. Priya Natarajan's"
    assert en[slice(*mg.trim_span(en, 0, len(en), "PERSON", "en"))] == "Priya Natarajan"
    en2 = "the Northvale Analytics Inc."
    assert en2[slice(*mg.trim_span(en2, 0, len(en2), "ORG", "en"))] == "Northvale Analytics"


def test_overlap_with_structured_or_protected_drops_the_span():
    text = "Contact : clotilde@exemple-mail.fr. La Cour de cassation et le Tribunal judiciaire de Lyon ont statué."
    spans = [_span(text, "clotilde@exemple-mail.fr", "PERSON"), _span(text, "Cour de cassation", "ORG", "organization"),
             _span(text, "Tribunal judiciaire de Lyon", "ORG", "organization"), _span(text, "Lyon", "ORG", "organization")]
    structured = [(text.index("clotilde@"), text.index(".fr") + 3, "EMAIL")]
    got = mg.merge_ner(text, spans, (), structured)
    assert got == []
    # without the structured list the email span is still refused by the person guard (not a name)
    assert mg.merge_ner(text, spans[:1], (), ()) == []


def test_stop_words_legal_terms_and_stoplist_only_spans_are_dropped():
    text = "L'Expéditeur et le Destinataire signent. Objet : Conclusions. Monsieur Madame. Décision du Tribunal."
    spans = [_span(text, w, "ORG", "organization", 0.9) for w in ("Expéditeur", "Destinataire", "Objet", "Tribunal")]
    spans += [_span(text, w, "PERSON", "person", 0.9) for w in ("Conclusions", "Monsieur Madame", "Décision")]
    assert mg.guard_ner_spans(text, spans) == []


def test_statutory_phrase_is_cut_from_the_start_and_syndicat_never_a_name():
    text = ("La société par actions simplifiée Kalvenor et le syndicat des copropriétaires de l'immeuble sis "
            "12 rue des Lilas ; le liquidateur judiciaire Marnival a été entendu.")
    spans = [_span(text, "société par actions simplifiée Kalvenor", "ORG", "organization", 0.9),
             _span(text, "syndicat des copropriétaires de l'immeuble", "ORG", "organization", 0.9),
             _span(text, "syndicat des copropriétaires", "ORG", "organization", 0.9),
             _span(text, "liquidateur judiciaire Marnival", "PERSON", "person", 0.9)]
    got = _kept(text, spans)
    assert got == {"Kalvenor": "ORG", "Marnival": "PERSON"}


def test_rules_win_on_kind_equal_span_adds_nothing():
    text = "Mme Clotilde Berrivan signe."
    rule = (text.index("Clotilde"), text.index("Berrivan") + 8, "ORG")  # the rule says ORG: it wins, NER adds nothing
    spans = [_span(text, "Clotilde Berrivan", "PERSON")]
    assert mg.merge_ner(text, spans, [rule], ()) == []


def test_rules_win_extension_accepted_only_with_name_words():
    text = "Mme Clotilde Berrivan Maudet, gérante. Groupe Kalvenor Industrie SAS."
    rule_p = (text.index("Clotilde"), text.index("Berrivan") + 8, "PERSON")
    spans = [_span(text, "Clotilde Berrivan Maudet", "PERSON"), _span(text, "Clotilde Berrivan Maudet, gérante", "PERSON")]
    got = mg.merge_ner(text, spans, [rule_p], ())
    assert [(text[m.start:m.end], m.kind, m.origin) for m in got] == [("Clotilde Berrivan Maudet", "PERSON", "rule+ner")]
    rule_o = (text.index("Kalvenor"), text.index("Kalvenor") + 8, "ORG")
    spans = [_span(text, "Groupe Kalvenor Industrie SAS", "ORG", "organization"),
             _span(text, "Kalvenor Industrie", "ORG", "organization")]
    got = mg.merge_ner(text, spans, [rule_o], ())
    # the trigger word stays in clear, as with the rules ("groupe X" -> X); "Industrie" extends the rule span
    assert [(text[m.start:m.end], m.kind, m.origin) for m in got] == [("Kalvenor Industrie", "ORG", "rule+ner")]


def test_rules_win_inner_or_partial_overlap_is_dropped():
    text = "Me Jean-Pierre Vorande et Kalvenor Industrie SAS."
    rule = (text.index("Jean-Pierre"), text.index("Vorande") + 7, "PERSON")
    spans = [_span(text, "Vorande", "PERSON"), _span(text, "Vorande et Kalvenor", "ORG", "organization")]
    assert mg.merge_ner(text, spans, [rule], ()) == []


def test_is_name_word():
    assert mg.is_name_word("Berrivan")
    assert mg.is_name_word("de") and mg.is_name_word("van")
    assert not mg.is_name_word("et") and not mg.is_name_word("the", "en", "PERSON")
    assert mg.is_name_word("the", "en", "ORG") and mg.is_name_word("et", "fr", "ORG")
    assert not mg.is_name_word("Président") and not mg.is_name_word("Janvier")
    assert not mg.is_name_word("Décision", kind="PERSON")      # vocabulary, not a first name
    assert mg.is_name_word("Clotilde", kind="PERSON")           # first name
    assert mg.is_name_word("Industrie", kind="ORG")             # generic company word
    assert not mg.is_name_word("Industrie", kind="PERSON")
    assert not mg.is_name_word("", kind="PERSON")
    assert mg.is_name_word("Analytics", "en", "ORG")
    assert not mg.is_name_word("Monday", "en", "PERSON")


# ---------------------------------------------------------------------------
# Merge: precision guards on NER-only spans
# ---------------------------------------------------------------------------


def test_one_word_person_needs_a_cue_unless_first_name():
    text = ("Bonjour Clotilde, merci. Vorande a signé. Cher Vorande, bonjour. M. Berrivan aussi. "
            "Le gérant Marnival confirme. Signé Kervalon.\nCordialement,\nTalvez\nDécision prise.")
    spans = [_span(text, "Clotilde", "PERSON", "first_name", 0.6), _span(text, "Vorande", "PERSON", "person", 0.9),
             _span(text, "Vorande", "PERSON", "person", 0.9, nth=1), _span(text, "Berrivan", "PERSON", "person", 0.9),
             _span(text, "Marnival", "PERSON", "person", 0.9), _span(text, "Kervalon", "PERSON", "person", 0.9),
             _span(text, "Talvez", "PERSON", "person", 0.9), _span(text, "Décision", "PERSON", "person", 0.95)]
    got = mg.guard_ner_spans(text, spans)
    kept = [(text[m.start:m.end], m.start) for m in got]
    assert ("Clotilde", text.index("Clotilde")) in kept          # first name, no cue needed
    assert ("Vorande", text.index("Vorande")) not in kept         # sentence start, no cue
    assert ("Vorande", text.index("Vorande", text.index("Cher"))) in kept   # after "Cher"
    assert ("Berrivan", text.index("Berrivan")) in kept           # after "M."
    assert ("Marnival", text.index("Marnival")) in kept           # after a role word
    assert ("Kervalon", text.index("Kervalon")) in kept           # after "Signé"
    assert ("Talvez", text.index("Talvez")) in kept               # signature line under "Cordialement,"
    assert not any(w == "Décision" for w, _ in kept)             # vocabulary word
    # a cue is not enough under the one-word score (default 0.50)
    low = [_span(text, "Berrivan", "PERSON", "person", 0.45)]
    assert mg.guard_ner_spans(text, low) == []
    assert mg.guard_ner_spans(text, low, one_word_person_min=0.4)
    # legal context cues: "Dossier X", "Succession X-Y", "X c/ Y"; initials of a person of the text; a nickname
    legal = ("Objet : Dossier Marchetto c/ Lumivor. Succession Lagardello-Aymard.\nMail de P.-H. G., gérant. "
             "PHG rappelle. Mme Marie-Hermeline Le Kervran signe ; Herme confirme. On le surnomme « Tibou ».")
    spans = [_span(legal, "Marchetto", "PERSON", "last_name", 0.55), _span(legal, "Lumivor", "ORG", "organization", 0.65),
             _span(legal, "Lagardello-Aymard", "PERSON", "person", 0.7), _span(legal, "P.-H. G.", "PERSON", "person", 0.9),
             _span(legal, "PHG", "PERSON", "person", 0.8), _span(legal, "Marie-Hermeline Le Kervran", "PERSON", "person", 0.9),
             _span(legal, "Herme", "PERSON", "person", 0.95, nth=1), _span(legal, "Tibou", "PERSON", "person", 0.95)]
    got = {legal[m.start:m.end] for m in mg.guard_ner_spans(legal, spans)}
    assert got == {"Marchetto", "Lumivor", "Lagardello-Aymard", "P.-H. G", "PHG", "Marie-Hermeline Le Kervran",
                   "Herme", "Tibou"}
    assert mg.guard_ner_spans("Vu. PHG rappelle.", [(4, 7, "PERSON", "person", 0.9)]) == []  # no such person


def test_capitalised_common_word_and_place_guards():
    text = "Avenir et Marché sont clos. Fontaine reste. Jean Petit signe. Pierre Blanc aussi. Grand Paris Lumière."
    spans = [_span(text, w, "PERSON", "person", 0.95) for w in ("Avenir", "Marché", "Fontaine", "Jean Petit", "Pierre Blanc")]
    spans.append(_span(text, "Grand Paris Lumière", "ORG", "organization", 0.95))
    got = _kept(text, spans)
    assert got == {"Jean Petit": "PERSON", "Pierre Blanc": "PERSON"}


def test_place_guard_when_places_file_exists(monkeypatch):
    monkeypatch.setattr(mg, "places", lambda lang="fr": frozenset({"paris", "lyon"}))
    mg.lists_for.cache_clear()
    try:
        text = "Rendez-vous avec Paris et Lyon. Mme Paris signe."
        spans = [_span(text, "Paris", "PERSON", "person", 0.9), _span(text, "Lyon", "ORG", "organization", 0.9),
                 _span(text, "Paris", "PERSON", "person", 0.9, nth=1)]
        got = mg.guard_ner_spans(text, spans)
        assert [(text[m.start:m.end], m.start) for m in got] == []   # a place alone is never a name, even after a title
    finally:
        mg.lists_for.cache_clear()


def test_acronym_guards():
    text = ("La Société Verrière de Brenac-Lalonde (ci-après « SVBL ») signe. SVBL paie. CGV et TVA. XQZT refuse. "
            "Le RGPD s'applique. ABC Kalvenor.")
    spans = [_span(text, "SVBL", "ORG", "organization", 0.9), _span(text, "SVBL", "ORG", "organization", 0.9, nth=1),
             _span(text, "CGV", "ORG", "organization", 0.9), _span(text, "TVA", "PERSON", "person", 0.9),
             _span(text, "XQZT", "ORG", "organization", 0.95), _span(text, "RGPD", "ORG", "organization", 0.9),
             _span(text, "Société Verrière de Brenac-Lalonde", "ORG", "organization", 0.9)]
    got = mg.guard_ner_spans(text, spans)
    kept = sorted(text[m.start:m.end] for m in got)
    # the trigger word "Société" stays in clear (rules' convention); the acronym still gets its initials from it
    assert kept == ["SVBL", "SVBL", "Verrière de Brenac-Lalonde"]
    assert mg.guard_ner_spans("Vu. SVBL paie.", [(4, 8, "ORG", "organization", 0.9)]) == []  # no definition, no name
    # a dotted registry acronym at the start is a reference, never a company
    reg = "Immatriculée 938 402 005 R.C.S. Lyon, la société Kalvenor."
    got = mg.guard_ner_spans(reg, [(reg.index("R.C.S."), reg.index("Lyon") + 4, "ORG", "organization", 0.9),
                                   (reg.index("Kalvenor"), reg.index("Kalvenor") + 8, "ORG", "organization", 0.9)])
    assert [reg[m.start:m.end] for m in got] == ["Kalvenor"]
    # the registered acronym list of the masker also unlocks an acronym
    got = mg.merge_ner(text, [_span(text, "XQZT", "ORG", "organization", 0.95)], (), (), org_acronyms=["XQZT"])
    assert [text[m.start:m.end] for m in got] == ["XQZT"]
    # a person is never an acronym
    assert mg.guard_ner_spans("Vu par SVBL.", [(7, 11, "PERSON", "person", 0.99)]) == []


def test_all_caps_line_guard():
    text = ("DÉBOUTONS LA DEMANDE\nCONDAMNE MONSIEUR KERVALON AUX DÉPENS\nPAR CES MOTIFS\nREJETTE TALVEZ\n"
            "SOCIÉTÉ BRIVANOR LOGISTIQUE")
    spans = [_span(text, "DÉBOUTONS", "PERSON", "person", 0.9), _span(text, "LA DEMANDE", "ORG", "organization", 0.9),
             _span(text, "KERVALON", "PERSON", "person", 0.9), _span(text, "MONSIEUR KERVALON", "PERSON", "person", 0.9),
             _span(text, "PAR CES MOTIFS", "ORG", "organization", 0.9), _span(text, "TALVEZ", "PERSON", "person", 0.9),
             _span(text, "SOCIÉTÉ BRIVANOR LOGISTIQUE", "ORG", "organization", 0.9)]
    got = sorted(text[m.start:m.end] for m in mg.guard_ner_spans(text, spans))
    # words of the vocabulary in capitals are never names; a surname after a title or a trigger still is;
    # a bare capital word without any cue ("REJETTE TALVEZ") is left to the rules and the dictionary
    assert got == ["BRIVANOR LOGISTIQUE", "KERVALON"]


def test_org_guards_generic_words_one_word_and_cues():
    text = ("La Direction refuse. Groupe Industrie Services. Kalvenor paie. Brivanor Logistique livre. "
            "Envoyé chez Talvez. Travaux chez Fontaine. the Northvale team")
    spans = [_span(text, "Direction", "ORG", "organization", 0.95), _span(text, "Groupe Industrie Services", "ORG", "organization", 0.9),
             _span(text, "Kalvenor", "ORG", "organization", 0.65), _span(text, "Brivanor Logistique", "ORG", "organization", 0.9),
             _span(text, "Talvez", "ORG", "organization", 0.65), _span(text, "Fontaine", "ORG", "organization", 0.95)]
    got = _kept(text, spans)
    assert got == {"Brivanor Logistique": "ORG", "Talvez": "ORG", "Fontaine": "ORG"}  # "chez" is a cue; 0.65 alone is not
    got = _kept(text, spans, one_word_org_min=0.6)
    assert "Kalvenor" in got
    en = "We met Northvale at the fair. Northvale's Q3 is strong."
    spans = [_span(en, "Northvale", "ORG", "organization", 0.65), _span(en, "Northvale", "ORG", "organization", 0.65, nth=1)]
    got = mg.guard_ner_spans(en, spans, lang="en")
    assert [en[m.start:m.end] for m in got] == ["Northvale"] and got[0].start == en.index("Northvale's")  # possessive cue


def test_english_text_does_not_use_the_french_stop_list():
    # "Car" is a French stop word? no; use a French stop word that is an English name word: "Les" / "Don"
    text = "Hi Don, Les Dupont and Pat Nordqvist joined. Thanks, Don"
    spans = [_span(text, "Don", "PERSON", "person", 0.8), _span(text, "Les Dupont", "PERSON", "person", 0.9),
             _span(text, "Pat Nordqvist", "PERSON", "person", 0.9), _span(text, "Don", "PERSON", "person", 0.8, nth=1)]
    got_en = {(text[m.start:m.end], m.start) for m in mg.guard_ner_spans(text, spans, lang="en")}
    assert ("Les Dupont", text.index("Les")) in got_en and ("Pat Nordqvist", text.index("Pat")) in got_en
    assert ("Don", text.index("Don")) in got_en  # after "Hi"
    got_fr = {text[m.start:m.end] for m in mg.guard_ner_spans(text, spans, lang="fr")}
    assert "Les Dupont" not in got_fr  # in French "Les" is an article and "Dupont" alone keeps the stricter rule


def test_value_kinds_need_a_plausible_shape():
    text = ("Employee ID: EMP-48213, account 1980, ref 12/05/2024, amount 1500 €, badge AB12CD, "
            "DOB 3 mai 1980, born 1980, user jdoe_42, mail x, ip 10.0.0.1, vessel Marnival Star, school École")
    spans = [_span(text, "EMP-48213", "EMPLOYEE_ID", "employee_id", 0.9), _span(text, "1980", "ACCOUNT_NUMBER", "account_number", 0.9),
             _span(text, "12/05/2024", "ID_CODE", "government_id", 0.9), _span(text, "1500", "ACCOUNT_NUMBER", "account_number", 0.9),
             _span(text, "AB12CD", "EMPLOYEE_ID", "employee_id", 0.9), _span(text, "3 mai 1980", "BIRTHDATE", "date_of_birth", 0.9),
             _span(text, "1980", "BIRTHDATE", "date_of_birth", 0.9, nth=2), _span(text, "jdoe_42", "USERNAME", "username", 0.9),
             _span(text, "x", "EMAIL", "email", 0.9), _span(text, "10.0.0.1", "ID_CODE", "ip_address", 0.9),
             _span(text, "Marnival Star", "ID_CODE", "vessel", 0.9), _span(text, "École", "ID_CODE", "school", 0.9)]
    got = _kept(text, spans)
    assert got == {"EMP-48213": "EMPLOYEE_ID", "AB12CD": "EMPLOYEE_ID", "3 mai 1980": "BIRTHDATE",
                   "jdoe_42": "USERNAME", "10.0.0.1": "ID_CODE", "Marnival Star": "ID_CODE"}


def test_kinds_filter_and_nested_collapse():
    text = "Mme Clotilde Berrivan de Kalvenor Industrie."
    spans = [_span(text, "Clotilde Berrivan", "PERSON"), _span(text, "Clotilde", "PERSON", "first_name", 0.95),
             _span(text, "Berrivan", "PERSON", "last_name", 0.95), _span(text, "Kalvenor Industrie", "ORG", "organization", 0.9)]
    got = mg.guard_ner_spans(text, spans)
    assert [text[m.start:m.end] for m in got] == ["Clotilde Berrivan", "Kalvenor Industrie"]
    got = mg.guard_ner_spans(text, spans, kinds=("ORG",))
    assert [text[m.start:m.end] for m in got] == ["Kalvenor Industrie"]


def test_merge_accepts_rule_objects_and_computes_protected_intervals():
    text = "Devant la Cour d'appel de Lyon, Mme Clotilde Berrivan et Kalvenor Industrie SAS."
    rules = nm.detect_names(text)
    assert any(r.kind == "PERSON" for r in rules)
    spans = [_span(text, "Cour d'appel de Lyon", "ORG", "organization", 0.9), _span(text, "Clotilde Berrivan", "PERSON"),
             _span(text, "Kalvenor Industrie SAS", "ORG", "organization", 0.9)]
    got = mg.merge_ner(text, spans, rules, ())
    assert all(text[m.start:m.end] != "Cour d'appel de Lyon" for m in got)
    folded = fold(text)
    protected = nm.protected_intervals(text, folded, tokens(folded.text))
    got2 = mg.merge_ner(text, spans, rules, (), protected)
    assert got == got2


# ---------------------------------------------------------------------------
# End to end through the existing Masker(ner=...) plumbing
# ---------------------------------------------------------------------------


def test_hook_masks_what_rules_miss_and_keeps_courts_clear():
    text = ("Note interne.\nvorande a validé le dossier de Clotilde hier ; son adresse clotilde@exemple-mail.fr.\n"
            "Devant la Cour de cassation, le Trésorier Kalvenor refuse. Le Tribunal judiciaire de Lyon statue.")
    backend = fake_backend([("Clotilde", "first_name", 0.9), ("Kalvenor", "organization", 0.9),
                            ("Cour de cassation", "organization", 0.95), ("Trésorier", "organization", 0.9),
                            ("clotilde@exemple-mail.fr", "person", 0.9), ("Tribunal judiciaire de Lyon", "organization", 0.9)])
    rules_only = Masker(MemoryStore(), use_ner=False).mask(text).text
    assert "Clotilde" in rules_only and "Kalvenor" in rules_only
    m = Masker(MemoryStore(), ner=ner.as_hook(backend))
    assert m.mode == "rules+ner"
    r = m.mask(text)
    assert "Clotilde" not in r.text and "PERSONNE_A" in r.text
    assert "Kalvenor" not in r.text and "SOCIETE_A" in r.text
    assert "EMAIL_1" in r.text and "Cour de cassation" in r.text and "Tribunal judiciaire de Lyon" in r.text
    assert "Trésorier" in r.text
    assert m.unmask(r.text) == text


def test_hook_respects_the_text_size_limit_and_absent_backend():
    calls: list = []
    backend = fake_backend([("Kalvenor", "organization", 0.9)], calls=calls)
    hook = ner.as_hook(backend, max_text_chars=50)
    assert hook("x" * 60) == []
    assert calls == []
    assert hook("Kalvenor paie chez Kalvenor.")  # under the limit: runs
    assert ner.as_hook(None)("Kalvenor paie.") == []
    assert ner.as_hook(backend)("") == []


def test_hook_failure_never_breaks_masking():
    def broken(chunks):
        raise RuntimeError("model crashed")

    backend = ner.CallableBackend(broken, ner.KIND_FASTINO)
    m = Masker(MemoryStore(), ner=ner.as_hook(backend))
    assert m.mask("M. Paul Rivière signe.").text == "M. PERSONNE_A signe."


# ---------------------------------------------------------------------------
# Lexicon files
# ---------------------------------------------------------------------------


def test_lexicon_files_load_and_are_folded():
    words, phrases = mg.ner_stoplist("fr")
    assert "objet" in words and "expediteur" in words and "liquidateur judiciaire" in phrases
    assert all(w == w.lower() and " " not in w for w in words)
    assert all(" " in p for p in phrases)
    en_words, en_phrases = mg.ner_stoplist("en")
    assert "subject" in en_words and "human resources" in en_phrases
    v = mg.vocab("fr")
    assert {"decision", "petit", "blanc", "fontaine", "deboutons", "immeuble"} <= v
    assert mg.lists_for("fr").vocabulary("marchand")  # common_words_fr.txt counts as vocabulary too
    assert not ({"clotilde", "berrivan", "kalvenor"} & v)
    phrases, shorts = mg.spelled_forms("fr")
    assert "societe par actions simplifiee" in phrases and "syndicat des coproprietaires" in phrases
    assert "hlm" in shorts and "asl" in shorts
    assert mg.vocab("en") == frozenset()  # LOCALE-EN ships it; absent file = empty, never an error
    assert mg.places("fr") == frozenset() or isinstance(mg.places("fr"), frozenset)


def test_lexicon_files_hold_no_control_characters_and_no_tabs():
    for name in ("ner_stoplist_fr.txt", "ner_stoplist_en.txt", "vocab_fr.txt", "legal_forms_spelled_fr.txt"):
        text = (LEX / name).read_text(encoding="utf-8")
        assert "\t" not in text and "—" not in text


def test_fr_lexicon_additions_are_known_to_the_rules():
    from ragbase_shield.engine import lexicon as lx

    assert {"jap", "jme", "jcp", "cpc", "cgi"} <= lx.acronym_stoplist()
    assert {"judiciaire", "coproprietaires", "proprietaire", "distributeur"} <= lx.legal_terms()
    assert "conseil regional" in lx.whitelist_phrases() and "assurance maladie" in lx.whitelist_phrases()


# ---------------------------------------------------------------------------
# Real backends (skipped when no model is cached)
# ---------------------------------------------------------------------------

_HAVE_MODEL = ner.ner_installed("auto") and ner.resolve_model("auto") in ("fastino", "urchade")
real = pytest.mark.skipif(not _HAVE_MODEL, reason="no GLiNER model cached (RAGBASE_SHIELD_MODELS_DIR)")


def _models_root() -> str:
    """The cache root where the model was found at collection time (before conftest moved the data home)."""
    for key in ("fastino", "urchade"):
        snap = ner.snapshot_dir(ner.MODELS[key])
        if snap is not None:
            return str(snap.parents[2] if snap.parent.name == "snapshots" else snap.parent)
    return ""


_MODELS_ROOT = _models_root() if _HAVE_MODEL else ""  # at import time: conftest moves the data home per test


@pytest.fixture
def real_models(monkeypatch):
    """conftest points RAGBASE_SHIELD_HOME at a temp dir: keep the models dir the collection saw."""
    root = _MODELS_ROOT
    if root:
        monkeypatch.setenv("RAGBASE_SHIELD_MODELS_DIR", root)
    for var in ("HF_HUB_CACHE", "HF_HOME"):  # an earlier test may have pointed the hub cache at a fake directory
        monkeypatch.delenv(var, raising=False)
    ner.unload_backends()  # earlier tests cached failed loads from fake directories
    yield


@real
def test_real_backend_loads_offline_and_finds_an_invented_person(real_models):
    backend = ner.load_backend("auto")
    assert backend is not None and backend.name.startswith(("gliner2:", "gliner:"))
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    text = ("Bonjour Maître Vorande,\nle dossier de Mme Clotilde Berrivan et de la société Kalvenor Industrie SAS "
            "est prêt. La Cour de cassation a statué. Son matricule est EMP-48213.")
    spans = ner.run_ner(text, backend, cache=None)
    values = {text[s:e]: k for s, e, k, *_ in spans}
    assert any("Berrivan" in v and k == "PERSON" for v, k in values.items())
    assert all(text[s:e] == text[s:e].strip() for s, e, *_ in spans)
    kept = {text[m.start:m.end]: m.kind for m in mg.guard_ner_spans(text, spans)}
    assert "Cour de cassation" not in kept
    assert any("Berrivan" in v for v in kept)
    assert ner.load_backend("auto") is backend  # singleton


@real
def test_real_backend_end_to_end_through_the_masker(real_models):
    backend = ner.load_backend("auto")
    text = "vorande a validé. Clotilde confirme demain ; Kalvenor paie. La Cour de cassation a statué."
    m = Masker(MemoryStore(), ner=ner.as_hook(backend))
    r = m.mask(text)
    assert "Cour de cassation" in r.text
    assert "Clotilde" not in r.text
    assert m.unmask(r.text) == text


@real
def test_real_backend_speed_is_reported(real_models, capsys):
    import time

    backend = ner.load_backend("auto")
    text = ("Le contrat entre Kalvenor Industrie SAS et Mme Clotilde Berrivan prévoit une livraison à Lyon. " * 40)
    ner.run_ner(text[:500], backend, cache=None)  # warm-up
    t = time.perf_counter()
    ner.run_ner(text, backend, cache=None)
    dt = time.perf_counter() - t
    with capsys.disabled():
        print(f"\n[ner speed] {backend.name}: {len(text) / dt:,.0f} chars/s on {len(text)} chars")
    assert dt > 0


# ---------------------------------------------------------------------------
# Integrator: a one-word model find is upgraded by a fuller rule name (no containment left behind)
# ---------------------------------------------------------------------------


def test_one_word_ner_entity_is_upgraded_by_a_fuller_rule_name():
    def hook(text):
        i = text.find("Northvale")
        return [(i, i + len("Northvale"), "ORG")] if i >= 0 and "Analytics" not in text else []

    m = Masker(MemoryStore(locale="en"), locale="en", language="en", ner=hook)
    m.mask("Northvale announced its results today.")
    ent = m.store.all()[0]
    assert ent.value == "Northvale" and ent.source == "ner"
    r = m.mask("Northvale Analytics Inc. confirmed the renewal. Northvale will send the invoice.")
    assert [sp.value for sp in r.spans] == ["Northvale Analytics", "Northvale"]
    ent = m.store.get_by_code(ent.code)
    assert ent.value == "Northvale Analytics" and ent.source == "detected"
    assert len(m.store.all()) == 1
