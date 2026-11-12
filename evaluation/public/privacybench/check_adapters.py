"""Self-check of the format adapters in run_shield.py (NOT a Shield result).

For one set, every unit is extracted with run_shield's adapters, then every gold surface string of that unit
is searched in the extracted text and each occurrence is emitted, with the gold label, through the same
native-coordinate locators Shield's spans go through. The benchmark's scorer then measures how much of the
answer key the adapters can reach at all: a recall close to complete per file kind means a Shield miss on that kind
is Shield's, not the adapter's. Gold is read here only for this check; run_shield.py never reads it.

Usage: python evaluation/public/privacybench/check_adapters.py aaron_pfizer [more sets]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_shield as rs  # noqa: E402

RUNS = rs.WORK / "runs"
CODE = rs.WORK / "code" / "privacy_bench_metrics"


def unit_key(kind: str, path: str, container) -> tuple:
    part = container.get("part_index") if container and container.get("kind") == "eml_attachment" else None
    return (kind, path, part)


def main() -> int:
    sets = sys.argv[1:] or ["aaron_pfizer"]
    for name in sets:
        warn: Counter = Counter()
        units = rs.load_units(rs.DATA / "tasks" / name, warn)
        by_key = defaultdict(list)
        for u in units:
            by_key[unit_key(u.kind, u.path, u.container)].append(u)
        out = rs.WORK / "adapter_check" / f"{name}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        missing_units: Counter = Counter()
        unfound: Counter = Counter()
        with out.open("w", encoding="utf-8") as h:
            for line in (rs.DATA / "ground_truth" / name / "ground_truth.jsonl").open(encoding="utf-8"):
                r = json.loads(line)
                f = r["file"]
                key = unit_key(f["kind"], f["path"], f.get("container"))
                us = by_key.get(key)
                if f["kind"] == "slack":
                    ptr = f.get("json_pointer", "") + "/text"
                    us = [u for u in (us or []) if u.pointer == ptr]
                if not us:
                    missing_units[f["kind"]] += 1
                    continue
                u = us[0]
                spans = []
                for sp in r["ground_truth_spans"]:
                    if sp["location"].get("status") == "not_rendered":
                        continue
                    t = sp["text"]
                    i = u.text.find(t)
                    if i < 0:
                        unfound[f"{f['kind']}:{sp['label']}"] += 1
                        continue
                    while i >= 0:
                        for loc in rs.native_locations(u, i, i + len(t)):
                            spans.append({"label": sp["label"], "text": t, "new_text": "X" + t, "location": loc})
                        i = u.text.find(t, i + 1)
                h.write(json.dumps({"file": {"kind": u.kind, "path": u.path, "container": u.container}, "spans": spans}) + "\n")
        run = f"adapter_check_{name}"
        if (RUNS / run).exists():
            shutil.rmtree(RUNS / run)
        r = subprocess.run([sys.executable, "-m", "synthesis_evaluation.run_eval_native", "--predictions", str(out),
                            "--ground-truth", str(rs.DATA / "ground_truth" / name / "ground_truth.jsonl"),
                            "--skip-llm-judge", "--run-name", run, "--runs-dir", str(RUNS)],
                           cwd=str(CODE), capture_output=True, text=True)
        if r.returncode != 0:
            print(name, "SCORER FAILED", r.stderr[-1500:])
            continue
        res = json.loads((RUNS / run / "results.json").read_text(encoding="utf-8"))
        kinds = {k: v.get("ner_recall") for k, v in (res["metrics"].get("by_kind") or {}).items()}
        print(json.dumps({"set": name, "overall_recall": res["metrics"]["overall"]["ner_recall"], "by_kind": kinds,
                          "units_without_gold_match": dict(missing_units), "gold_text_not_in_extracted": dict(unfound),
                          "adapter_warnings": dict(warn), "native_join": res.get("native_join")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
