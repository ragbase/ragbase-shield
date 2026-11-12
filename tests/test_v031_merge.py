"""v0.3.1 NER merge: a model span with no letter word gets no second signal and never crashes the merge
(RESULTS_V03 section 9, item 2; owner SYNTH for ``merge._name_signals``).

Every name and number below is invented for these tests (none comes from a benchmark or a corpus).
"""
from __future__ import annotations

import logging

import pytest

from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import merge as mg
from ragbase_shield.engine import ner as nr

TEXT = "Paid 12.50 on site, ref 4471-22. Corwin Quillmore approved it."


def _span(text: str, frag: str, kind: str = "PERSON", score: float = 0.9):
    i = text.index(frag)
    return (i, i + len(frag), kind, kind.lower(), score)


@pytest.mark.parametrize("frag", ["12.50", "4471-22"])
@pytest.mark.parametrize("kind", ["PERSON", "ORG"])
def test_name_signals_of_a_span_without_a_letter_word_is_empty(frag, kind):
    L = mg.lists_for("en")
    idx = mg._NameIndex(TEXT, [], [], L)
    s = TEXT.index(frag)
    assert mg._name_signals(TEXT, s, s + len(frag), kind, L, idx, frozenset(), {}) == ()


def test_merge_keeps_the_real_name_next_to_digit_spans():
    spans = [_span(TEXT, "12.50"), _span(TEXT, "4471-22"), _span(TEXT, "12.50", "ORG"), _span(TEXT, "Corwin Quillmore")]
    merged = mg.merge_ner(TEXT, spans, lang="en")  # raised IndexError before v0.3.1
    found = {TEXT[m.start:m.end] for m in merged}
    assert "Corwin Quillmore" in found and not found & {"12.50", "4471-22"}


class _Stub:
    name = "stub"
    labels: dict = {}
    thresholds: dict = {}

    def predict(self, chunks):  # never called: run_ner is replaced below
        return [[] for _ in chunks]


def test_masker_keeps_the_model_finds_of_a_unit_with_a_digit_span(monkeypatch, caplog):
    monkeypatch.setattr(nr, "run_ner", lambda text, backend: [_span(text, "12.50"), _span(text, "Corwin Quillmore")])
    m = Masker(MemoryStore(locale="en"), locale="en", language="en", use_ner=True)
    m._backend, m._backend_tried, m.use_ner = _Stub(), True, True
    with caplog.at_level(logging.WARNING):
        out = m.mask(TEXT).text
    assert "NER merge failed" not in caplog.text
    assert "Quillmore" not in out and "Corwin" not in out and "12.50" in out
