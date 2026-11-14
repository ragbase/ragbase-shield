"""Run Microsoft Presidio, a free local tool, on one benchmark set.

Fixed settings: presidio-analyzer and presidio-anonymizer (versions recorded at install), spaCy model
``fr_core_news_md`` (``en_core_web_lg`` with ``--language en``), the default recognizer registry
for that language, the default score threshold, all default entities, and the default anonymizer operator
(``replace``: the value becomes ``<ENTITY_TYPE>``). No presidio-fr add-on, no custom recognizer. Presidio is a text
library, so it gets the text that ``extract_text.py`` reads from each input file (it does not rebuild files).

Output: OUT/<input path with .txt>, OUT/runlog.jsonl, OUT/tasks_log.jsonl, OUT/run_meta.json (same format as
run_shield_files.py). Outbound network connections are refused in this process.

Usage: python run_presidio.py --set-dir SETS/<set> --out OUT --language fr|en
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

T_PROCESS = time.perf_counter()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_text import extract  # noqa: E402
from run_shield_files import NETWORK_ATTEMPTS, _guarded_connect, peak_memory_mb  # noqa: E402

MODELS = {"fr": "fr_core_news_md", "en": "en_core_web_lg"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--language", choices=("fr", "en"), required=True)
    args = ap.parse_args()
    socket.socket.connect = _guarded_connect
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    nlp = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [
        {"lang_code": args.language, "model_name": MODELS[args.language]}]}).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp, supported_languages=[args.language])
    anonymizer = AnonymizerEngine()
    warm = "M. Jean Dupont habite 4 rue Neuve à Lille." if args.language == "fr" else "John Smith lives in Leeds."
    anonymizer.anonymize(text=warm, analyzer_results=analyzer.analyze(text=warm, language=args.language))
    cold = time.perf_counter() - T_PROCESS
    set_dir, out = Path(args.set_dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = json.loads((set_dir / "tasks.json").read_text(encoding="utf-8"))
    runlog = (out / "runlog.jsonl").open("w", encoding="utf-8")
    tasklog = (out / "tasks_log.jsonl").open("w", encoding="utf-8")
    n = 0
    for t in tasks:
        t0 = time.perf_counter()
        for rel in t["files"]:
            r0 = time.perf_counter()
            try:
                text, _m = extract(set_dir / "input" / rel)
                res = analyzer.analyze(text=text, language=args.language)
                masked = anonymizer.anonymize(text=text, analyzer_results=res).text
                dest = out / Path(rel).with_suffix(".txt")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(masked, encoding="utf-8")
                row = {"doc_id": rel, "status": "ok", "reason": "", "seconds": round(time.perf_counter() - r0, 4)}
            except Exception as e:  # noqa: BLE001
                row = {"doc_id": rel, "status": "failed", "reason": f"{type(e).__name__}: {e}"}
            runlog.write(json.dumps(dict(row, task=t["task"]), ensure_ascii=False) + "\n")
            n += 1
        tasklog.write(json.dumps({"task": t["task"], "files": len(t["files"]),
                                  "task_seconds": round(time.perf_counter() - t0, 3)}) + "\n")
    meta = {"date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "set": set_dir.name,
            "tool": "presidio", "language": args.language, "spacy_model": MODELS[args.language],
            "versions": {p: version(p) for p in ("presidio-analyzer", "presidio-anonymizer", "spacy")},
            "python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
            "cold_seconds": round(cold, 3), "documents": n, "peak_memory_mb": peak_memory_mb(),
            "network_attempts": NETWORK_ATTEMPTS}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
