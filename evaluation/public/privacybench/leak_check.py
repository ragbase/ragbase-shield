"""Synthetic-mode leak check of a PrivacyBench run, against the benchmark's answer key (v0.3, 2026-10-22).

    python leak_check.py <run dir> [--workers 4] [--json out.json] [--examples 40]

``<run dir>`` holds ``predictions/mask/<set>.jsonl`` (codes run) and ``predictions_synthetic/mask/<set>.jsonl``
(synthetic run of the same code, ``new_text`` = what Shield wrote in place of the span), as ``run_shield.py --out NAME
--synthetic`` writes them. It does not import Shield or the benchmark's code (positions: ``recheck_v02.py``).

For every gold span (status located, one of the 10 scored labels), in native coordinates:

- ``hidden_codes``: at least half of its positions lie under a codes-run span of ANY label (the value is masked);
- ``visible_synthetic``: in the synthetic output the real text can still be read there, because (a) less than half of
  its positions lie under a synthetic span (left in the clear), or (b) a synthetic span over it writes the gold text
  again (the folded gold text is a whole-word part of that span's ``new_text``: "Bill" written as "Bill").

**Leak** = ``hidden_codes`` and ``visible_synthetic``: a real value that codes mode masks and synthetic mode shows.
A gold span visible in both modes is a detection miss, not a synthetic leak (counted apart).

Also counted on the synthetic predictions: spans written unchanged (``new_text`` folds to the span text), spans whose
``new_text`` is a Shield code (fail closed: SyntheticLeak / SyntheticCollision), and spans whose ``new_text`` folds to
a gold surface of the same export other than the span's own text (a real value of the dossier used as a fake), split
by whether the codes run masks that surface somewhere in the export (Shield knew it as real) or never.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recheck_v02 as rc  # noqa: E402  (unit keys and native positions)

CODE_RE = re.compile(r"^[A-Z]+(?:_[A-Z]+)*_(?:[A-Z]{1,3}|[0-9]{1,4})$")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s.lower()).strip()


def word_in(needle: str, hay: str) -> bool:
    if not needle:
        return False
    return re.search(r"(?<![0-9a-z])" + re.escape(needle) + r"(?![0-9a-z])", hay) is not None


def gold_cells(kind: str, loc: dict) -> set:
    out: set = set()
    for part in rc.gparts(loc):
        if kind == "pdf":
            out |= rc.glyphs(part)
        else:
            out |= rc.cells(kind, part)
    return out


def load_preds(path: Path) -> dict:
    out: dict = defaultdict(list)
    if not path.exists():
        return out
    for line in path.open(encoding="utf-8"):
        r = json.loads(line)
        f = r["file"]
        k = rc.ukey(f.get("kind"), f.get("path"), f.get("container"))
        for s in r["spans"]:
            out[k].append(s)
    return out


def index(kind: str, spans: list) -> dict:
    """position -> indexes of the spans that cover it"""
    idx: dict = defaultdict(list)
    for j, s in enumerate(spans):
        for c in rc.cells(kind, s["location"]):
            idx[c].append(j)
    return idx


def check_set(run: str, name: str, n_examples: int) -> dict:
    run_dir = Path(run)
    codes = load_preds(run_dir / "predictions" / "mask" / f"{name}.jsonl")
    syn = load_preds(run_dir / "predictions_synthetic" / "mask" / f"{name}.jsonl")
    c: Counter = Counter()
    leak_by_label: Counter = Counter()
    leak_by_cause: Counter = Counter()
    examples: list = []
    gold_surfaces: dict[str, set] = defaultdict(set)   # folded gold surface -> labels
    masked_surfaces: set[str] = set()                  # folded gold surfaces the codes run masks at least once
    rows = [json.loads(line) for line in (rc.DATA / "ground_truth" / name / "ground_truth.jsonl").open(encoding="utf-8")]
    cache_idx: dict = {}
    for row in rows:
        f = row["file"]
        k = rc.ukey(f.get("kind"), f.get("path"), f.get("container"))
        kind = k[0]
        if k not in cache_idx:
            cache_idx[k] = (index(kind, codes.get(k, [])), index(kind, syn.get(k, [])))
        cidx, sidx = cache_idx[k]
        sspans = syn.get(k, [])
        for g in row["ground_truth_spans"]:
            loc = g["location"]
            if loc.get("status") == "not_rendered" or g["label"] not in rc.LABELS:
                continue
            gc = gold_cells(kind, loc)
            if not gc:
                c["gold_no_positions"] += 1
                continue
            c["gold"] += 1
            gt = fold(g["text"])
            gold_surfaces[gt].add(g["label"])
            n = len(gc)
            under_c = sum(1 for x in gc if x in cidx)
            under_s = sum(1 for x in gc if x in sidx)
            hidden_codes = under_c * 2 >= n
            if hidden_codes:
                masked_surfaces.add(gt)
            over = {j for x in gc for j in sidx.get(x, ())}
            rewritten = any(word_in(gt, fold(sspans[j].get("new_text") or "")) for j in over)
            visible = under_s * 2 < n or rewritten
            if hidden_codes:
                c["hidden_codes"] += 1
            if under_s * 2 >= n and not rewritten:
                c["hidden_synthetic"] += 1
            if not hidden_codes and visible:
                c["visible_both_modes"] += 1
            if hidden_codes and not visible:
                c["hidden_both_modes"] += 1
            if not hidden_codes and not visible:
                c["hidden_synthetic_only"] += 1
            if hidden_codes and visible:
                c["leak"] += 1
                leak_by_label[g["label"]] += 1
                cause = "written_again" if rewritten else ("in_clear" if under_s == 0 else "partly_covered")
                leak_by_cause[cause] += 1
                if sum(1 for x in examples if x["cause"] == cause) < n_examples:
                    examples.append({"label": g["label"], "file": kind, "cause": cause, "gold": g["text"],
                                     "new_text_over": sorted({sspans[j].get("new_text") or "" for j in over})[:3],
                                     "codes_over": sorted({s.get("text") or "" for x in gc for s in
                                                           (codes.get(k, [])[j] for j in cidx.get(x, ()))})[:3]})
    # the synthetic predictions themselves
    syn_unchanged: Counter = Counter()
    syn_code: Counter = Counter()
    reuse_known: Counter = Counter()
    reuse_unknown: Counter = Counter()
    for k, spans in syn.items():
        for s in spans:
            c["synthetic_spans"] += 1
            nt, tt = s.get("new_text") or "", s.get("text") or ""
            if CODE_RE.match(nt.strip()):
                syn_code[s["label"]] += 1
                continue
            fnt = fold(nt)
            if fnt and fnt == fold(tt):
                syn_unchanged[s["label"]] += 1
                continue
            if fnt in gold_surfaces:
                (reuse_known if fnt in masked_surfaces else reuse_unknown)[s["label"]] += 1
    c["synthetic_unchanged"] = sum(syn_unchanged.values())
    c["synthetic_code_written"] = sum(syn_code.values())
    c["synthetic_fake_is_other_gold_surface_known"] = sum(reuse_known.values())
    c["synthetic_fake_is_other_gold_surface_unknown"] = sum(reuse_unknown.values())
    return {"set": name, "counts": dict(c), "leak_by_label": dict(leak_by_label), "leak_by_cause": dict(leak_by_cause),
            "synthetic_unchanged_by_label": dict(syn_unchanged), "synthetic_code_by_label": dict(syn_code),
            "fake_is_known_gold_surface_by_label": dict(reuse_known),
            "fake_is_unknown_gold_surface_by_label": dict(reuse_unknown), "examples": examples}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--sets")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json")
    ap.add_argument("--examples", type=int, default=0, help="per set and cause; examples quote the gold text: keep the JSON under .bench_data")
    a = ap.parse_args()
    sets = a.sets.split(",") if a.sets else sorted(p.name for p in (rc.DATA / "ground_truth").iterdir() if p.is_dir())
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(check_set, [a.run] * len(sets), sets, [a.examples] * len(sets)))
    tot: Counter = Counter()
    agg: dict[str, Counter] = defaultdict(Counter)
    for r in res:
        tot.update(r["counts"])
        for key in ("leak_by_label", "leak_by_cause", "synthetic_unchanged_by_label", "synthetic_code_by_label",
                    "fake_is_known_gold_surface_by_label", "fake_is_unknown_gold_surface_by_label"):
            agg[key].update(r[key])
        cc = r["counts"]
        print(f"{r['set']:34s} gold={cc.get('gold', 0):6d} leak={cc.get('leak', 0):5d} unchanged={cc.get('synthetic_unchanged', 0):5d} "
              f"code={cc.get('synthetic_code_written', 0):4d} reuse_known={cc.get('synthetic_fake_is_other_gold_surface_known', 0):4d}", flush=True)
    print("TOTAL", dict(tot))
    for key, v in agg.items():
        print(f"  {key}: {dict(v.most_common())}")
    if a.json:
        Path(a.json).write_text(json.dumps({"run": a.run, "total": dict(tot), "by": {k: dict(v) for k, v in agg.items()},
                                            "per_set": res}, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
