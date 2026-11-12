"""Dry run of the PrivacyBench LLM judge on a synthetic prediction folder: what the judge WOULD send, no API call.

    python judge_dryrun.py <run dir> [--predictions-name predictions_synthetic] [--variant mask]

Builds the judge's rows with the benchmark's own code (``native.join``, the same call ``run_eval_native`` makes) and
its own mapping and message builders (``score_realism_llm``), then counts per set: the calls (one per character, one
per organisation group chunk of 25 surfaces, one per unowned batch), the characters of every user message, the
(owner, label, surface) verdicts and the value entries the judge must write. It also counts the person surfaces whose
synthetic values include the surface itself (the judge sees "Bill" -> ["Bill"]). Nothing leaves the machine.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "privacybench"
DATA = WORK / "data"
sys.path.insert(0, str(WORK / "code" / "privacy_bench_metrics"))

from synthesis_evaluation import native, score_realism_llm as J  # noqa: E402
from synthesis_evaluation.load import load_characters, load_jsonl  # noqa: E402


def one_set(pred: Path, name: str) -> Counter:
    c: Counter = Counter()
    gt_rows = list(load_jsonl(DATA / "ground_truth" / name / "ground_truth.jsonl"))
    preds = native.load_predictions(load_jsonl(pred))
    rows, _kinds, _diag = native.join(gt_rows, preds, threshold=0.5)
    characters = load_characters(DATA / "ground_truth" / name / "characters.json")
    mappings, _ = J._build_mappings(rows)
    org_mappings, _ = J._build_org_mappings(rows)
    unowned, _ = J._build_unowned_mappings(rows)
    batches = J._unowned_batches(unowned)
    for cid, m in mappings.items():
        org_ctx = []
        for real_org in J._char_orgs(characters, cid):
            synths = sorted({s for d in ((org_mappings.get(real_org) or {}).get("ORGANIZATION") or {}).values() for s in d})
            org_ctx.append((real_org, synths))
        msg = J._build_user_message(cid, m, org_context=org_ctx or None)
        c["calls"] += 1
        c["calls_character"] += 1
        c["user_chars"] += len(msg)
        c["max_user_chars"] = max(c["max_user_chars"], len(msg))
        for lab, d in m.items():
            for orig, vals in d.items():
                c["verdicts"] += 1
                c["value_entries"] += len(vals)
                if orig in vals:
                    c["person_surface_written_unchanged"] += 1
    for grp, m in org_mappings.items():
        flat = [(lab, s) for lab in m for s in m[lab]]
        chunks = max(1, (len(flat) + 24) // 25)
        c["calls"] += chunks
        c["calls_org"] += chunks
        for start in range(0, len(flat), 25):
            piece: dict = {}
            for lab, s in flat[start:start + 25]:
                piece.setdefault(lab, {})[s] = m[lab][s]
            msg = J._build_org_user_message(grp, piece)
            c["user_chars"] += len(msg)
            c["max_user_chars"] = max(c["max_user_chars"], len(msg))
        for lab, d in m.items():
            for _orig, vals in d.items():
                c["verdicts"] += 1
                c["value_entries"] += len(vals)
    for b in batches:
        msg = J._build_unowned_user_message(b)
        c["calls"] += 1
        c["calls_unowned"] += 1
        c["user_chars"] += len(msg)
        c["max_user_chars"] = max(c["max_user_chars"], len(msg))
        for lab, d in b.items():
            for _orig, vals in d.items():
                c["verdicts"] += 1
                c["value_entries"] += len(vals)
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--predictions-name", default="predictions_synthetic")
    ap.add_argument("--variant", default="mask")
    ap.add_argument("--json")
    a = ap.parse_args()
    run = Path(a.run) if Path(a.run).is_absolute() else WORK / a.run
    tot: Counter = Counter()
    per: dict = {}
    for gt in sorted((DATA / "ground_truth").iterdir()):
        if not gt.is_dir():
            continue
        c = one_set(run / a.predictions_name / a.variant / f"{gt.name}.jsonl", gt.name)
        per[gt.name] = dict(c)
        m = c.pop("max_user_chars", 0)
        tot.update(c)
        tot["max_user_chars"] = max(tot["max_user_chars"], m)
        print(f"{gt.name:34s} calls={c['calls']:3d} (char {c['calls_character']}, org {c['calls_org']}, unowned {c['calls_unowned']}) "
              f"user_chars={c['user_chars']:7d} verdicts={c['verdicts']} values={c['value_entries']}", flush=True)
    print("TOTAL", dict(tot))
    print("system prompts (characters):", {"character": len(J.SYSTEM_PROMPT), "org": len(J.ORG_SYSTEM_PROMPT),
                                            "unowned": len(J.UNOWNED_SYSTEM_PROMPT)}, "max_tokens per call:", J.MAX_TOKENS)
    if a.json:
        Path(a.json).write_text(json.dumps({"total": dict(tot), "per_set": per}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
