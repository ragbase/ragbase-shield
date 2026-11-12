"""Score Shield's PrivacyBench predictions with the benchmark's OWN code (privacy_bench_metrics, tag v2.5).

Three scorers of the benchmark are run unchanged:

1. ``synthesis_evaluation.run_eval_native`` per set and variant: NER recall against the generated answer key
   (label-matched, native-coordinate overlap >= 0.5 of the union, or a prediction that contains the gold span),
   by label and by file kind. With ``--judge MODEL`` it also runs the benchmark's LLM judge (synthesis accuracy,
   combined score); without it the judge is skipped (``--skip-llm-judge``), which needs no API key.
2. ``synthesis_evaluation.aggregate`` over the 21 per-set runs: macro (the card's headline) and micro averages.
3. ``synthesis_evaluation.run_ner_eval`` on the six human-annotated sets: precision, recall, F1 (overlap and
   exact), per set, pooled and macro. This is the only place precision (false positives) is defined.

Outputs under .bench_data/public/privacybench/:
    runs/<set>_<variant>/{results.json,summary.md,viewer.html}   the scorer's own reports
    runs/aggregate_<variant>.{json,md}                            the benchmark's aggregator
    runs/human_<variant>/{results.json,summary.md}                NER P/R/F1 vs human annotations
    scores.json, scores.md                                        compact tables built from the above

Usage: python evaluation/public/privacybench/score.py [--variants mask,canary] [--sets a,b] [--workers 8]
                                                       [--judge claude-opus-5-5] [--skip-human]
                                                       [--out NAME] [--predictions-name predictions_synthetic]

--out NAME scores the run that run_shield.py --out NAME wrote (predictions under .bench_data/public/privacybench/NAME/,
runs and scores written there too). --predictions-name picks another prediction folder of that run (the synthetic
replacement run, ``predictions_synthetic``): its runs go to runs_<name> and its scores to scores_<name>.{json,md}.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "privacybench"
DATA = WORK / "data"
CODE = WORK / "code" / "privacy_bench_metrics"
PRED = WORK / "predictions"
NER_PRED = WORK / "ner_predictions"
RUNS = WORK / "runs"
LABELS = ("NAME_GIVEN", "NAME_FAMILY", "EMAIL_ADDRESS", "USERNAME", "ORGANIZATION", "PHONE_NUMBER",
          "LOCATION_ADDRESS", "EMPLOYEE_ID", "ACCOUNT_NUMBER", "URL")
KINDS = ("eml", "slack", "pdf", "docx", "xlsx", "csv", "messages", "documents")
PY = sys.executable


def sh(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, env=env)


def score_native(name: str, variant: str, judge: str | None, workers: int) -> dict:
    run = f"{name}_{variant}"
    out = RUNS / run
    if out.exists():
        shutil.rmtree(out)
    args = [PY, "-m", "synthesis_evaluation.run_eval_native",
            "--predictions", str(PRED / variant / f"{name}.jsonl"),
            "--ground-truth", str(DATA / "ground_truth" / name / "ground_truth.jsonl"),
            "--characters", str(DATA / "ground_truth" / name / "characters.json"),
            "--run-name", run, "--runs-dir", str(RUNS), "--workers", str(workers)]
    args += ["--judge-model", judge] if judge else ["--skip-llm-judge"]
    r = sh(args, CODE)
    ok = r.returncode == 0 and (out / "results.json").exists()
    if not ok:
        return {"set": name, "variant": variant, "ok": False, "stderr": r.stderr[-2000:], "stdout": r.stdout[-500:]}
    res = json.loads((out / "results.json").read_text(encoding="utf-8"))
    return {"set": name, "variant": variant, "ok": True, "metrics": res["metrics"], "native_join": res.get("native_join")}


def aggregate(variant: str) -> dict:
    dirs = sorted(str(p) for p in RUNS.glob(f"*_{variant}") if (p / "results.json").exists()
                  and not p.name.startswith("human_"))
    r = sh([PY, "-m", "synthesis_evaluation.aggregate", *dirs, "--json", str(RUNS / f"aggregate_{variant}.json"),
            "--out", str(RUNS / f"aggregate_{variant}.md")], CODE)
    if r.returncode != 0:
        return {"ok": False, "stderr": r.stderr[-2000:]}
    return {"ok": True, **json.loads((RUNS / f"aggregate_{variant}.json").read_text(encoding="utf-8"))}


def score_human(variant: str) -> dict:
    run = f"human_{variant}"
    out = RUNS / run
    if out.exists():
        shutil.rmtree(out)
    pairs: list[str] = []
    for gold in sorted((DATA / "human_annotations").glob("*.jsonl")):
        pred = NER_PRED / variant / gold.name
        if pred.exists():
            pairs += ["--gold", str(gold), "--predictions", str(pred)]
    if not pairs:
        return {"ok": False, "stderr": f"no prediction files under {NER_PRED / variant}"}
    r = sh([PY, "-m", "synthesis_evaluation.run_ner_eval", *pairs, "--run-name", run, "--runs-dir", str(RUNS)], CODE)
    if r.returncode != 0 or not (out / "results.json").exists():
        return {"ok": False, "stderr": r.stderr[-2000:], "stdout": r.stdout[-500:]}
    return {"ok": True, **json.loads((out / "results.json").read_text(encoding="utf-8"))}


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", default="mask,canary")
    ap.add_argument("--sets", default=None)
    ap.add_argument("--workers", type=int, default=8, help="parallel scorer processes")
    ap.add_argument("--judge", default=None, help="run the benchmark's LLM judge with this model (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--skip-human", action="store_true")
    ap.add_argument("--out", default="", help="sub-folder of .bench_data/public/privacybench holding the run (run_shield.py --out)")
    ap.add_argument("--predictions-name", default="predictions", help="prediction folder of the run to score")
    args = ap.parse_args()
    global PRED, NER_PRED, RUNS
    out_dir = WORK / args.out if args.out else WORK
    suffix = "" if args.predictions_name == "predictions" else "_" + args.predictions_name.removeprefix("predictions_")
    PRED, NER_PRED, RUNS = out_dir / args.predictions_name, out_dir / "ner_predictions", out_dir / ("runs" + suffix)
    scores_json, scores_md = out_dir / f"scores{suffix}.json", out_dir / f"scores{suffix}.md"
    if not (CODE / "synthesis_evaluation").is_dir():
        sys.exit(f"missing {CODE}: run download.py first")
    variants = args.variants.split(",")
    sets = args.sets.split(",") if args.sets else sorted(p.name for p in (DATA / "ground_truth").iterdir() if p.is_dir())
    if args.judge and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("--judge needs ANTHROPIC_API_KEY in the environment")
    RUNS.mkdir(parents=True, exist_ok=True)

    jobs = [(s, v) for v in variants for s in sets if (PRED / v / f"{s}.jsonl").exists()]
    missing = [(s, v) for v in variants for s in sets if not (PRED / v / f"{s}.jsonl").exists()]
    per_set: dict[str, dict[str, dict]] = {v: {} for v in variants}
    with ThreadPoolExecutor(max_workers=1 if args.judge else args.workers) as ex:
        for res in ex.map(lambda sv: score_native(sv[0], sv[1], args.judge, 8), jobs):
            per_set[res["variant"]][res["set"]] = res
            print(json.dumps({k: res[k] for k in ("set", "variant", "ok")}
                             | ({"recall": res["metrics"]["overall"]["ner_recall"]} if res["ok"] else {"stderr": res.get("stderr", "")[-300:]})),
                  flush=True)
    agg = {v: aggregate(v) for v in variants}
    human = {} if args.skip_human else {v: score_human(v) for v in variants}

    scores = {"variants": variants, "sets": sets, "missing_predictions": missing, "judge": args.judge,
              "out": args.out, "predictions_name": args.predictions_name,
              "per_set": per_set, "aggregate": agg, "human": human}
    scores_json.write_text(json.dumps(scores, indent=1, ensure_ascii=False), encoding="utf-8")
    scores_md.write_text(render(scores), encoding="utf-8")
    print(scores_md.read_text(encoding="utf-8"))
    bad = [(s, v) for v in variants for s, r in per_set[v].items() if not r["ok"]]
    return 1 if bad or missing else 0


def _agg_block(a: dict, key: str) -> dict:
    """The aggregator's JSON has macro and micro blocks; return {name: metrics} for `key` (overall/by_label/by_kind)."""
    return a.get(key) or {}


def render(scores: dict) -> str:
    lines = ["# PrivacyBench v2.5: Shield scores (benchmark's own scorer)", ""]
    if scores["judge"]:
        lines.append(f"LLM judge: `{scores['judge']}`.")
    else:
        lines.append("LLM judge: skipped (`--skip-llm-judge`): NER recall only; synthesis accuracy and the combined score are not computed.")
    if scores["missing_predictions"]:
        lines.append(f"Missing prediction files: {scores['missing_predictions']}")
    for v in scores["variants"]:
        a = scores["aggregate"].get(v) or {}
        lines += ["", f"## Variant `{v}`", ""]
        if not a.get("ok"):
            lines.append(f"aggregate failed: {a.get('stderr', '')[-500:]}")
            continue
        lines.append("```json")
        lines.append(json.dumps({k: a[k] for k in a if k not in ("per_dataset", "ok")}, indent=1)[:6000])
        lines.append("```")
        per = scores["per_set"].get(v) or {}
        lines += ["", "| set | NER recall | gold | detected |", "|---|---:|---:|---:|"]
        for s in sorted(per):
            r = per[s]
            if r["ok"]:
                o = r["metrics"]["overall"]
                lines.append(f"| {s} | {pct(o['ner_recall'])} | {o['gold']} | {o['detected']} |")
            else:
                lines.append(f"| {s} | FAILED | | |")
        h = scores["human"].get(v)
        if h:
            lines += ["", f"### Human-annotation NER (variant `{v}`)", "", "```json",
                      json.dumps({k: h[k] for k in h if k in ("pooled", "macro", "micro", "overall", "summary")}, indent=1)[:4000], "```"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
