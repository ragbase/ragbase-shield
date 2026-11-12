"""Score a holdout run with the PrivacyBench metric definitions.

    python evaluation/holdout-en/score_holdout.py --out NAME [--predictions-name predictions_synthetic]
                                                  [--sets a,b] [--official] [--syncover]

Default scorer: the card's native metric as re-implemented in ``evaluation/public/privacybench/recheck_v02.py``
(standard library only). A gold span is detected when a prediction of the same file unit, with the same label or
an alias the benchmark accepts, overlaps it by >= 0.5 of the union in native coordinates (or contains it);
NER recall = detected / gold, per set, per label and per file kind; the headline is the macro mean over the
exports, as on the card. Two readings the card does not have, possible because every planted value of this corpus is
gold: "any label" recall (the value is masked under another label) and a precision proxy (predictions in scope
that cover no gold span of a label they may match; city names, dates, amounts, roles and topics are not gold, so an
ORGANIZATION or NAME prediction on them is a false positive here, while a span on an e-mail header or a cell the
runner never scores is simply absent).

``--official`` runs the benchmark's own scorer unchanged (``synthesis_evaluation.run_eval_native``, tag v2.5,
``--skip-llm-judge``, through ``evaluation/public/privacybench/score.py``) when its code is checked out under
``.bench_data/public/privacybench/code``; its per-set reports and the aggregate land under the run folder.
``--syncover`` runs the codes-versus-synthetic leak check of ``recheck_v02.py`` on the run (needs ``--synthetic``
predictions): codes-run spans with no synthetic-run span over them are values the synthetic output shows in clear.

Outputs under ``.bench_data/holdout-en/<NAME>/``: ``scores[_<predictions-name>].json`` and ``.md``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BENCH_DIR = ROOT / "evaluation" / "public" / "privacybench"
sys.path.insert(0, str(BENCH_DIR))
import recheck_v02 as rc  # noqa: E402

rc.DATA = HERE  # the answer keys of this corpus (ground_truth/<set>/ground_truth.jsonl)
RUNS_ROOT = ROOT / ".bench_data" / "holdout-en"
LABELS = rc.LABELS
KINDS = ("eml", "slack", "pdf", "docx", "xlsx", "csv")
CODE_RE = re.compile(r"^\s?[A-Z]+_(?:[A-Z]{1,4}|\d{1,6})\s?$")  # a Shield code written in place of a fake value


def gold_units(name: str) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = defaultdict(list)
    for line in (HERE / "ground_truth" / name / "ground_truth.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        f = row["file"]
        k = rc.ukey(f.get("kind"), f.get("path"), f.get("container"))
        out[k].extend(g for g in row["ground_truth_spans"] if g["location"].get("status") != "not_rendered")
    return out


def precision_and_codes(pred_file: Path, name: str) -> tuple[Counter, Counter]:
    """(counts, per-label counts): predictions in scope, those matched by a gold span (>= 0.5 overlap, label
    compatible, same file unit), and synthetic replacements that are a code (fail closed)."""
    gold = gold_units(name)
    c: Counter = Counter()
    per: Counter = Counter()
    for k, preds in rc.units(pred_file).items():
        golds = gold.get(k, [])
        cache: dict = {}
        for p in preds:
            if not rc.scorable(p["label"]):
                continue
            c["pred"] += 1
            per["pred|" + p["label"]] += 1
            if CODE_RE.match(p.get("new_text") or ""):
                c["code_written"] += 1
            hit = any(rc.can_match(g["label"], p["label"]) and rc.ov(k[0], p["location"], g["location"], cache) >= 0.5
                      for g in golds)
            c["matched"] += hit
            per["matched|" + p["label"]] += hit
    return c, per


def score_run(run: Path, pred_name: str, sets: list[str]) -> dict:
    per_set: dict[str, dict] = {}
    tot: Counter = Counter()
    totp: Counter = Counter()
    prec: Counter = Counter()
    prec_lab: Counter = Counter()
    for name in sets:
        pred_file = run / pred_name / "mask" / f"{name}.jsonl"
        if not pred_file.exists():
            per_set[name] = {"error": f"missing {pred_file}"}
            continue
        c, n_pred, dup, fallback, _wide = rc.score_set(pred_file, name)
        pc, pl = precision_and_codes(pred_file, name)
        per_set[name] = {"gold": c["gold"], "detected": c["det"], "recall": c["det"] / max(1, c["gold"]),
                         "any_label_recall": (c["det"] + c["other_label_only"]) / max(1, c["gold"]),
                         "other_label_only": c["other_label_only"], "pred_in_scope": sum(n_pred.values()),
                         "precision": pc["matched"] / max(1, pc["pred"]), "code_written": pc["code_written"],
                         "dup_spans": dup, "fallback_rows": fallback,
                         "by_label": {l: {"gold": c["gold|" + l], "detected": c["det|" + l],
                                          "recall": c["det|" + l] / max(1, c["gold|" + l])} for l in LABELS},
                         "by_kind": {k: {"gold": c["gold|kind|" + k], "detected": c["det|kind|" + k],
                                         "recall": c["det|kind|" + k] / max(1, c["gold|kind|" + k])} for k in KINDS}}
        tot += c
        totp += n_pred
        prec += pc
        prec_lab += pl
    scored = [v for v in per_set.values() if "error" not in v]
    n = max(1, len(scored))
    macro = {"ner_recall": sum(v["recall"] for v in scored) / n,
             "any_label_recall": sum(v["any_label_recall"] for v in scored) / n,
             "precision": sum(v["precision"] for v in scored) / n}
    pooled = {"gold": tot["gold"], "detected": tot["det"], "ner_recall": tot["det"] / max(1, tot["gold"]),
              "any_label_recall": (tot["det"] + tot["other_label_only"]) / max(1, tot["gold"]),
              "pred_in_scope": prec["pred"], "matched": prec["matched"],
              "precision": prec["matched"] / max(1, prec["pred"]), "code_written": prec["code_written"],
              "by_label": {l: {"gold": tot["gold|" + l], "detected": tot["det|" + l],
                               "recall": tot["det|" + l] / max(1, tot["gold|" + l]),
                               "other_label_only": tot["other_label_only|" + l],
                               "pred": prec_lab["pred|" + l],
                               "precision": prec_lab["matched|" + l] / max(1, prec_lab["pred|" + l])} for l in LABELS},
              "by_kind": {k: {"gold": tot["gold|kind|" + k], "detected": tot["det|kind|" + k],
                              "recall": tot["det|kind|" + k] / max(1, tot["gold|kind|" + k])} for k in KINDS}}
    return {"corpus": "holdout-en", "run": run.name, "predictions": pred_name, "metric": "PrivacyBench native "
            "(recheck_v02 re-implementation of the card: >= 0.5 overlap of the union or containment, same unit, "
            "label or alias)", "sets": per_set, "macro": macro, "pooled": pooled}


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def render(s: dict) -> str:
    L = [f"# Holdout EN, run `{s['run']}`, predictions `{s['predictions']}`", "",
         f"Metric: {s['metric']}.", "",
         f"**Macro NER recall {pct(s['macro']['ner_recall'])} %** (any label {pct(s['macro']['any_label_recall'])} %, "
         f"precision proxy {pct(s['macro']['precision'])} %); pooled {pct(s['pooled']['ner_recall'])} % "
         f"({s['pooled']['detected']} / {s['pooled']['gold']}), codes written in place of a fake value: "
         f"{s['pooled']['code_written']}.", "",
         "| set | gold | detected | recall | any label | precision | codes |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, v in s["sets"].items():
        if "error" in v:
            L.append(f"| {name} | | | {v['error']} | | | |")
            continue
        L.append(f"| {name} | {v['gold']} | {v['detected']} | {pct(v['recall'])} | {pct(v['any_label_recall'])} | "
                 f"{pct(v['precision'])} | {v['code_written']} |")
    L += ["", "| label | gold | detected | recall | other label only | predictions | precision |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for l, v in s["pooled"]["by_label"].items():
        L.append(f"| {l} | {v['gold']} | {v['detected']} | {pct(v['recall'])} | {v['other_label_only']} | {v['pred']} | "
                 f"{pct(v['precision'])} |")
    L += ["", "| file kind | gold | detected | recall |", "|---|---:|---:|---:|"]
    for k, v in s["pooled"]["by_kind"].items():
        L.append(f"| {k} | {v['gold']} | {v['detected']} | {pct(v['recall'])} |")
    if "official" in s:
        o = s["official"]
        L += ["", "## Benchmark's own scorer (synthesis_evaluation.run_eval_native, --skip-llm-judge)", ""]
        if o.get("ok"):
            L.append(f"Macro NER recall {pct(o.get('macro_ner_recall'))} %, micro {pct(o.get('micro_ner_recall'))} % "
                     f"({o.get('sets_scored')} sets).")
        else:
            L.append(f"Not run: {o.get('error')}")
    if "syncover" in s:
        L += ["", "## Codes versus synthetic (recheck_v02 syncover)", "", "```", s["syncover"].rstrip(), "```"]
    return "\n".join(L) + "\n"


def official(run: Path, pred_name: str, sets: list[str], workers: int) -> dict:
    import score as sc  # evaluation/public/privacybench/score.py, the stock driver of the benchmark's scorer

    if not (sc.CODE / "synthesis_evaluation").is_dir():
        return {"ok": False, "error": f"benchmark code not found under {sc.CODE}"}
    sc.DATA = HERE
    sc.PRED = run / pred_name
    sc.RUNS = run / ("runs" if pred_name == "predictions" else f"runs_{pred_name}")
    sc.RUNS.mkdir(parents=True, exist_ok=True)
    per = {}
    for name in sets:
        per[name] = sc.score_native(name, "mask", None, workers)
    agg = sc.aggregate("mask")
    out = {"ok": agg.get("ok", False), "sets_scored": sum(1 for v in per.values() if v.get("ok")), "per_set": per}
    if agg.get("ok"):
        out["macro_ner_recall"] = (agg.get("macro") or {}).get("ner_recall")
        out["micro_ner_recall"] = (agg.get("micro") or {}).get("ner_recall")
        out["aggregate"] = {k: v for k, v in agg.items() if k != "ok"}
    else:
        out["error"] = agg.get("stderr", "aggregate failed")
    return out


def syncover(run: Path) -> str:
    import io
    from contextlib import redirect_stdout

    if not (run / "predictions_synthetic" / "mask").is_dir():
        return "no predictions_synthetic in this run (run_holdout.py --synthetic)"
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc.syncover(SimpleNamespace(pred_dir=str(run)))
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="default", help="the run folder name given to run_holdout.py --out")
    ap.add_argument("--predictions-name", default="predictions", help="predictions (codes) or predictions_synthetic")
    ap.add_argument("--sets", default=None)
    ap.add_argument("--official", action="store_true", help="also run the benchmark's own scorer (code checkout needed)")
    ap.add_argument("--syncover", action="store_true", help="codes-versus-synthetic leak check")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    run = RUNS_ROOT / a.out
    sets = a.sets.split(",") if a.sets else sorted(p.name for p in (HERE / "ground_truth").iterdir() if p.is_dir())
    s = score_run(run, a.predictions_name, sets)
    if a.official:
        s["official"] = official(run, a.predictions_name, sets, a.workers)
    if a.syncover:
        s["syncover"] = syncover(run)
    suffix = "" if a.predictions_name == "predictions" else f"_{a.predictions_name}"
    (run / f"scores{suffix}.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    md = render(s)
    (run / f"scores{suffix}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
