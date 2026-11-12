"""RAGbase Shield engine bench on the synthetic French legal corpus (tests/fixtures/docs).

Two modes:

- ``registered``: the dossier parties are registered first, as a lawyer would do (dossier title
  parties, client, opposing party);
- ``detected``: nothing registered, the engine finds everything by itself.

Metrics: recall per kind (a gold mention is covered when every letter and digit of it is masked),
kind accuracy, precision per kind (a masked span is right when it overlaps a gold mention),
over-masking of text that must stay in clear (courts, institutions, laws, ordinary words),
round trip (restore of the masked text), speed. Gate: every registered party and every identifier with a check
digit masked (recall 1.0 on both).

Usage: ``python bench/run_bench.py [--out bench/RESULTS.md] [--quiet]``. Exit code 1 if the gate fails.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragbase_shield.engine import KINDS, UNMASK_RE, Masker, MemoryStore, entity_norm  # noqa: E402

DOCS = ROOT / "tests" / "fixtures" / "docs"


@dataclass
class Doc:
    name: str
    text: str
    gold: dict


@dataclass
class ModeResult:
    mode: str
    mentions: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0, 0]))  # kind -> [total, covered, kind_ok]
    spans: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))  # kind -> [total, tp]
    misses: list = field(default_factory=list)
    false_pos: list = field(default_factory=list)
    over_masked: list = field(default_factory=list)
    clear_total: int = 0
    party_total: int = 0
    party_covered: int = 0
    checksum_total: int = 0
    checksum_covered: int = 0
    roundtrip_docs: int = 0
    faithful_spans: int = 0
    total_spans: int = 0
    unknown_codes: int = 0
    seconds: float = 0.0
    chars: int = 0


def load_docs() -> list[Doc]:
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    out = []
    for item in manifest:
        text = (DOCS / item["doc"]).read_text(encoding="utf-8")
        gold = json.loads((DOCS / item["gold"]).read_text(encoding="utf-8"))
        out.append(Doc(item["doc"], text, gold))
    return out


def _covered(text: str, start: int, end: int, masked: list[tuple[int, int, str]]) -> tuple[bool, str]:
    need = {i for i in range(start, end) if text[i].isalnum()}
    kinds: dict[str, int] = defaultdict(int)
    for s, e, k in masked:
        if e <= start or s >= end:
            continue
        hit = need.intersection(range(s, e))
        need -= hit
        kinds[k] += len(hit)
    best = max(kinds, key=kinds.get) if kinds else ""
    return not need, best


def evaluate(docs: list[Doc], mode: str, use_ner: bool = False) -> ModeResult:
    res = ModeResult(mode)
    for doc in docs:
        store = MemoryStore()
        registered_ids = set()
        if mode == "registered":
            for p in doc.gold["parties"]:
                store.add(p["kind"], p["value"], entity_norm(p["kind"], p["value"]))
                registered_ids.add(p["id"])
        masker = Masker(store, use_ner=use_ner)
        t0 = time.perf_counter()
        result = masker.mask(doc.text)
        res.seconds += time.perf_counter() - t0
        res.chars += len(doc.text)
        masked = [(s.start, s.end, s.kind) for s in result.spans]
        gold_ranges = [(m["start"], m["end"]) for m in doc.gold["mentions"]]

        for m in doc.gold["mentions"]:
            ok, kind = _covered(doc.text, m["start"], m["end"], masked)
            row = res.mentions[m["kind"]]
            row[0] += 1
            row[1] += ok
            row[2] += ok and kind == m["kind"]
            if not ok:
                res.misses.append((doc.name, m["kind"], m["text"]))
            if m["id"] in registered_ids:
                res.party_total += 1
                res.party_covered += ok
            if m.get("checksum"):
                res.checksum_total += 1
                res.checksum_covered += ok

        for s in result.spans:
            row = res.spans[s.kind]
            row[0] += 1
            tp = any(not (s.end <= gs or s.start >= ge) for gs, ge in gold_ranges)
            row[1] += tp
            if not tp:
                res.false_pos.append((doc.name, s.kind, s.value))

        for c in doc.gold["keep_clear"]:
            res.clear_total += 1
            if any(not (e <= c["start"] or s >= c["end"]) for s, e, _k in masked):
                res.over_masked.append((doc.name, c["text"]))

        restored, unknown = masker.unmask_report(result.text)
        res.unknown_codes += len(unknown)
        res.roundtrip_docs += restored == doc.text
        codes = [m.group() for m in UNMASK_RE.finditer(result.text)]
        for s, code in zip(sorted(result.spans, key=lambda x: x.start), codes):
            res.total_spans += 1
            ent = store.get_by_code(code)
            res.faithful_spans += ent is not None and ent.value == s.value
    return res


def speed_check() -> tuple[int, float]:
    docs = load_docs()
    blob = "\n\n".join(d.text for d in docs)
    text = (blob * (300_000 // len(blob) + 1))[:300_000]
    m = Masker(MemoryStore(), use_ner=False)
    t0 = time.perf_counter()
    m.mask(text)
    return len(text), time.perf_counter() - t0


def _pct(a: int, b: int) -> str:
    return "n/a" if b == 0 else f"{100.0 * a / b:.1f}%"


def gate(results: list[ModeResult]) -> list[str]:
    fails = []
    for r in results:
        if r.mode == "registered" and r.party_covered < r.party_total:
            fails.append(f"{r.mode}: registered parties {r.party_covered}/{r.party_total}")
        if r.checksum_covered < r.checksum_total:
            fails.append(f"{r.mode}: checksummed identifiers {r.checksum_covered}/{r.checksum_total}")
    return fails


def report(results: list[ModeResult], docs: list[Doc], speed: tuple[int, float]) -> str:
    n_mentions = sum(len(d.gold["mentions"]) for d in docs)
    lines = [
        "# RAGbase Shield engine bench",
        "",
        "Synthetic French legal corpus (`tests/fixtures/docs`): "
        f"{len(docs)} documents ({', '.join(sorted({d.gold['type'] for d in docs}))}), "
        f"{sum(len(d.text) for d in docs):,} characters, {n_mentions} annotated mentions. "
        "All names, companies, addresses and numbers are invented; identifiers with a check digit are "
        "generated valid. Engine mode: rules only (no NER model).",
        "",
        "Recall: a mention counts as covered when every letter and digit of it is masked. "
        "Precision: a masked span counts as right when it overlaps an annotated mention. "
        "Over-masking: text that must stay in clear (courts, institutions, laws, ordinary words) that was masked.",
        "",
        "Reproduce: `.venv/bin/python bench/run_bench.py`.",
        "",
    ]
    fails = gate(results)
    lines += ["## Gate", "", "**PASS**" if not fails else "**FAIL**: " + "; ".join(fails), ""]
    lines += ["| Mode | Registered parties | Checksummed identifiers | All mentions | Precision | Over-masked clear items | Exact round trip (docs) | Unknown codes after restore |",
              "|---|---|---|---|---|---|---|---|"]
    for r in results:
        tot = sum(v[0] for v in r.mentions.values())
        cov = sum(v[1] for v in r.mentions.values())
        st = sum(v[0] for v in r.spans.values())
        tp = sum(v[1] for v in r.spans.values())
        party = _pct(r.party_covered, r.party_total) + f" ({r.party_covered}/{r.party_total})" if r.mode == "registered" else "n/a"
        lines.append(
            f"| {r.mode} | {party} | {_pct(r.checksum_covered, r.checksum_total)} ({r.checksum_covered}/{r.checksum_total}) "
            f"| {_pct(cov, tot)} ({cov}/{tot}) | {_pct(tp, st)} ({tp}/{st}) | {len(r.over_masked)}/{r.clear_total} "
            f"| {r.roundtrip_docs}/{len(docs)} | {r.unknown_codes} |"
        )
    lines.append("")
    for r in results:
        lines += [f"## Per kind, mode `{r.mode}`", "",
                  "| Kind | Mentions | Recall | Kind accuracy | Masked spans | Precision |",
                  "|---|---|---|---|---|---|"]
        for k in KINDS:
            m = r.mentions.get(k, [0, 0, 0])
            s = r.spans.get(k, [0, 0])
            if m[0] == 0 and s[0] == 0:
                continue
            lines.append(f"| {k} | {m[0]} | {_pct(m[1], m[0])} | {_pct(m[2], m[1])} | {s[0]} | {_pct(s[1], s[0])} |")
        lines.append("")
        if r.misses:
            lines += ["Missed mentions:", ""] + [f"- `{d}` {k}: {t!r}" for d, k, t in r.misses] + [""]
        if r.false_pos:
            lines += ["Spans masked outside the annotations:", ""] + [f"- `{d}` {k}: {t!r}" for d, k, t in r.false_pos] + [""]
        if r.over_masked:
            lines += ["Clear items that were masked:", ""] + [f"- `{d}`: {t!r}" for d, t in r.over_masked] + [""]
        lines += [f"Faithful restores (code restores the exact surface text): {_pct(r.faithful_spans, r.total_spans)}. "
                  "The other restores are variants of the same entity (for example \"BENALI\" restored as \"Karim BENALI\"), "
                  "which is why the exact document round trip is not complete.", ""]
    n, secs = speed
    corpus_secs = sum(r.seconds for r in results) / max(1, len(results))
    lines += ["## Speed", "",
              f"- Corpus: {sum(len(d.text) for d in docs):,} characters masked in {corpus_secs:.2f} s per mode.",
              f"- Large text: {n:,} characters masked in {secs:.2f} s (target: under 3 s, rules mode).", ""]
    lines += ["## Honest limits", "",
              "- Pseudonymisation, not anonymisation: masked text can still allow re-identification through context.",
              "- Recall on unregistered names depends on titles, first names and legal forms; a bare surname that "
              "appears without any of them is found only after one full mention in the same text.",
              "- Public case-law numbers (pourvoi, ECLI) are masked like the client's own case numbers.",
              "- The corpus is small and synthetic, and it was written together with the rules: the gate figures "
              "show that the gate is met, not the accuracy on real files. Real documents (OCR, tables, odd "
              "layouts, names without any title or first name) score lower.",
              "- Names in table cells without a title or a known first name are not found by the rules.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "bench" / "RESULTS.md"))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    docs = load_docs()
    results = [evaluate(docs, "registered"), evaluate(docs, "detected")]
    text = report(results, docs, speed_check())
    Path(args.out).write_text(text, encoding="utf-8")
    if not args.quiet:
        print(text)
    return 1 if gate(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
