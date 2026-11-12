"""Run RAGbase Shield (engine API) on the Judilibre sample and record every mask.

Input: ``.bench_data/public/judilibre/sample.jsonl`` (written by download.py).
Output (``.bench_data/public/judilibre/`` or, with ``--out NAME``, the sub-folder ``NAME`` of it):

- ``spans.jsonl``: one line per mask Shield applied (decision id, stratum, start, end, kind, detector source,
  the masked surface and 100 characters of context on each side);
- ``docs.jsonl``: one line per decision (chars, masks, seconds, the NER state of the result);
- ``run_meta.json``: Shield commit, settings, machine, totals.

Each decision is masked on its own, with a fresh in-memory store and nothing registered: this is the
``mask_text`` path of the service without a dossier (``Masker(MemoryStore(), use_ner=...)``), i.e. Shield
finding everything by itself. Timing covers ``Masker.mask`` only; the one-off lexicon load (and, in NER mode, the
model load) is measured separately (cold start) and excluded from the throughput.

v0.2 flags:

- ``--ner off`` (default, the R0/R1 path: ``use_ner=False``, ``mode == "rules"``) or ``--ner auto``
  (``use_ner=None``: the installed GLiNER backend, ``mode == "rules+ner:<backend>"``);
- ``--workers N``: decisions are split over N spawned processes (each loads the lexicons and, in NER mode, the
  model once). ``mask_seconds`` is the sum of the per-decision times over all processes (process-seconds), so
  ``chars_per_second`` is the per-process throughput; ``wall_seconds`` / ``chars_per_second_wall`` give the
  aggregate. With ``--workers 1`` (default) everything runs in this process, as in R0/R1;
- ``--out NAME``: write into ``.bench_data/public/judilibre/NAME/`` instead of the work folder itself, so that a
  rules run and a NER run can be kept side by side (``score.py --work NAME`` reads it).

Usage: .venv/bin/python evaluation/public/judilibre/run_shield.py [--ner off|auto] [--workers N] [--out NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "judilibre"
sys.path.insert(0, str(ROOT / "src"))

CONTEXT = 100


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # pragma: no cover - not a git checkout
        return "unknown"


def cpu() -> str:
    try:
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return platform.processor() or platform.machine()


def load_docs() -> list[dict]:
    sample = WORK / "sample.jsonl"
    return [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines() if line.strip()]


def _masker(ner: str):
    from ragbase_shield.engine import Masker, MemoryStore

    return Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False if ner == "off" else None)


def run_slice(indices: list[int], ner: str, total: int) -> dict:
    """Mask the decisions ``indices`` in this process; return their spans, per-decision rows and the cold start."""
    docs = load_docs()
    # Cold start: the first mask loads the lexicons (first names, surnames, legal vocabulary) and, in NER mode,
    # the model (10 to 15 s for a GLiNER model).
    t0 = time.perf_counter()
    warm = _masker(ner)
    warm.mask("La cour d'appel de Paris, M. Jean Dupont, président.")
    cold = time.perf_counter() - t0
    mode = warm.mode
    rows, spans = [], []
    for i in indices:
        d = docs[i]
        text = d["text"]
        m = _masker(ner)
        if ner == "off":
            assert m.mode == "rules", m.mode
        else:
            assert m.mode.startswith("rules+ner"), m.mode
        t = time.perf_counter()
        res = m.mask(text)
        dt = time.perf_counter() - t
        for s in res.spans:
            assert text[s.start:s.end] == s.value
            spans.append({
                "doc": i, "id": d.get("id"), "stratum": d["_stratum"], "start": s.start, "end": s.end,
                "kind": s.kind, "source": s.source, "value": s.value,
                "left": text[max(0, s.start - CONTEXT):s.start], "right": text[s.end:s.end + CONTEXT],
            })
        rows.append({
            "doc": i, "id": d.get("id"), "stratum": d["_stratum"], "line": d["_line"],
            "jurisdiction": d.get("jurisdiction"), "chamber": d.get("chamber"), "location": d.get("location"),
            "formation": d.get("formation"), "decision_date": d.get("decision_date"), "number": d.get("number"),
            "ecli": d.get("ecli"), "chars": len(text), "masks": len(res.spans), "seconds": round(dt, 4),
            "ner": res.ner, "language": res.language,
        })
        print(f"{i + 1:3d}/{total} {d['_stratum']:20s} {len(text):>9,d} chars {len(res.spans):4d} masks {dt:7.2f}s"
              f"{'' if ner == 'off' else '  ner=' + (res.ner or '-')}", flush=True)
    return {"cold": cold, "mode": mode, "rows": rows, "spans": spans}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ner", choices=("off", "auto"), default="off")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default="", help="sub-folder of the work folder for the output files")
    args = ap.parse_args()

    if not (WORK / "sample.jsonl").exists():
        print("run download.py first", file=sys.stderr)
        return 2
    docs = load_docs()
    out_dir = WORK / args.out if args.out else WORK
    out_dir.mkdir(parents=True, exist_ok=True)

    from ragbase_shield.engine import masker as masker_mod

    n = len(docs)
    workers = max(1, args.workers)
    t_wall = time.perf_counter()
    if workers == 1:
        parts = [run_slice(list(range(n)), args.ner, n)]
    else:
        # round-robin slices: the three strata and the long decisions spread over the processes
        slices = [list(range(k, n, workers)) for k in range(workers)]
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as ex:
            parts = list(ex.map(run_slice, slices, [args.ner] * workers, [n] * workers))
    wall = time.perf_counter() - t_wall

    rows = sorted((r for p in parts for r in p["rows"]), key=lambda r: r["doc"])
    spans = sorted((s for p in parts for s in p["spans"]), key=lambda s: (s["doc"], s["start"], s["end"]))
    assert [r["doc"] for r in rows] == list(range(n))
    with (out_dir / "spans.jsonl").open("w", encoding="utf-8") as f:
        for s in spans:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total_chars = sum(r["chars"] for r in rows)
    total_s = sum(r["seconds"] for r in rows)
    ner_states = sorted({r["ner"] for r in rows})
    meta = {
        "date": time.strftime("%Y-%m-%d"),
        "shield_commit": git("rev-parse", "HEAD"),
        "shield_src_tree": git("rev-parse", "HEAD:src"),
        "src_dirty": bool(git("status", "--porcelain", "--", "src")),
        "engine_api": "ragbase_shield.engine.Masker(MemoryStore(locale='fr'), locale='fr', use_ner=%s).mask(text)"
                      % ("False" if args.ner == "off" else "None"),
        "mode": parts[0]["mode"],
        "ner_flag": args.ner,
        "ner_installed": masker_mod.ner_installed(),
        "ner_states": ner_states,
        "ner_skipped_decisions": sum(1 for r in rows if r["ner"].startswith("skipped")),
        "ner_threads_env": os.environ.get("RAGBASE_SHIELD_NER_THREADS", ""),
        "registered_entities": 0,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": cpu(),
        "workers": workers,
        "decisions": n,
        "chars": total_chars,
        "masks": len(spans),
        "mask_seconds": round(total_s, 3),
        "chars_per_second": round(total_chars / total_s) if total_s else None,
        "wall_seconds": round(wall, 3),
        "chars_per_second_wall": round(total_chars / wall) if wall else None,
        "cold_start_seconds": round(max(p["cold"] for p in parts), 3),
        "cold_start_seconds_per_worker": [round(p["cold"], 3) for p in parts],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
