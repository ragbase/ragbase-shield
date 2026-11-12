"""Engine: synthetic corpus integrity and the bench gate (every registered party and checksummed id masked)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from ragbase_shield.engine import KINDS
from ragbase_shield.engine.detectors import (
    iban_valid,
    isin_valid,
    lei_valid,
    luhn_valid,
    nir_valid,
    siren_valid,
    siret_valid,
    vat_fr_valid,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "tests" / "fixtures" / "docs"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look their module up in sys.modules
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def builder():
    return _load("shield_build_fixtures", ROOT / "tests" / "fixtures" / "build_fixtures.py")


@pytest.fixture(scope="module")
def bench():
    return _load("shield_run_bench", ROOT / "bench" / "run_bench.py")


def test_fixtures_are_up_to_date(builder):
    for doc in builder.DOCS:
        text, mentions, clear = builder.render(doc["text"])
        assert (DOCS / f"{doc['name']}.txt").read_text(encoding="utf-8") == text, doc["name"]
        gold = json.loads((DOCS / f"{doc['name']}.gold.json").read_text(encoding="utf-8"))
        assert [(m["kind"], m["text"], m["start"]) for m in gold["mentions"]] == \
            [(m["kind"], m["text"], m["start"]) for m in mentions]
        assert [c["text"] for c in gold["keep_clear"]] == [c["text"] for c in clear]


def test_corpus_shape():
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) >= 8
    types = {m["type"] for m in manifest}
    assert {"assignation", "conclusions", "contrat", "jugement", "emails", "kbis", "pv_ag", "lettre"} <= types


@pytest.mark.parametrize("gold_path", sorted(DOCS.glob("*.gold.json")), ids=lambda p: p.stem)
def test_gold_offsets_kinds_and_check_digits(gold_path):
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    text = (DOCS / gold["doc"]).read_text(encoding="utf-8")
    validators = {"IBAN": iban_valid, "NIR": nir_valid, "SIREN": siren_valid, "SIRET": siret_valid,
                  "VAT": vat_fr_valid, "CARD": lambda v: luhn_valid(v.replace(" ", "").replace("-", ""))}
    assert gold["parties"] and gold["title"]
    for m in gold["mentions"]:
        assert m["kind"] in KINDS
        assert text[m["start"]:m["end"]] == m["text"]
        if m["kind"] in validators:
            assert validators[m["kind"]](m["text"]), m
        if m["kind"] == "ID_CODE" and m["checksum"]:
            assert isin_valid(m["text"]) or lei_valid(m["text"]), m
    for c in gold["keep_clear"]:
        assert text[c["start"]:c["end"]] == c["text"]
    party_ids = {p["id"] for p in gold["parties"]}
    assert party_ids <= {m["id"] for m in gold["mentions"]}, "every registered party is mentioned"


def test_bench_gate_and_quality(bench, tmp_path):
    docs = bench.load_docs()
    results = [bench.evaluate(docs, "registered"), bench.evaluate(docs, "detected")]
    assert bench.gate(results) == []
    for r in results:
        total = sum(v[0] for v in r.mentions.values())
        covered = sum(v[1] for v in r.mentions.values())
        spans = sum(v[0] for v in r.spans.values())
        tp = sum(v[1] for v in r.spans.values())
        assert covered / total >= 0.97, (r.mode, r.misses)
        assert tp / spans >= 0.95, (r.mode, r.false_pos)
        assert r.over_masked == [], r.over_masked
        assert r.unknown_codes == 0
    out = tmp_path / "RESULTS.md"
    assert bench.main(["--out", str(out), "--quiet"]) == 0
    assert "**PASS**" in out.read_text(encoding="utf-8")


def test_results_file_has_gate_and_kinds(bench, tmp_path):
    out = tmp_path / "RESULTS.md"
    assert bench.main(["--out", str(out), "--quiet"]) == 0
    text = out.read_text(encoding="utf-8")
    assert "## Gate" in text and "Per kind" in text
