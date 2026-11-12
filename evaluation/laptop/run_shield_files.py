"""Run RAGbase Shield on one set of the laptop head-to-head, the way a lawyer uses it (pre-registered,
PROTOCOL.md section 9.1). Runs on Windows, macOS and Linux; standard library plus the installed Shield.

Path (the product path, what an AI assistant receives): for each task of ``tasks.json`` (a folder a lawyer would
drop), the task's files are copied to a staging folder named after the task, the folder is registered with the
public ``Service`` API (``add_dossier``, no title), then each document is read page by page with
``read_document`` (default page size). The pages are joined: that text is Shield's output for the document.

Settings (fixed; PROTOCOL.md section 6):
  --mode rules   RAGBASE_SHIELD_NER=off                                       (the product default)
  --mode ner     RAGBASE_SHIELD_NER=on, RAGBASE_SHIELD_NER_MODEL=fastino, RAGBASE_SHIELD_NER_DEVICE=cpu
Everything else is the product default (language auto, codes, legal form in clear). A fresh Shield data folder
per run (RAGBASE_SHIELD_HOME), file key (RAGBASE_SHIELD_KEYRING=0). Outbound network connections are refused in
this process and every attempt is logged (part (d) of the question).

For the AVX2-only speed row, start the process with ATEN_CPU_CAPABILITY=avx2 and ONEDNN_MAX_CPU_ISA=AVX2 in the
environment (they must be set before torch loads); the runner records them.

Timing: ``cold_seconds`` = process start to the end of a warm-up mask of a fixed invented sentence (imports,
lexicons and, in ner mode, the model load); ``task_seconds`` = add_dossier plus every read_document of the task.
Memory: peak resident memory of this process (Windows: PeakWorkingSetSize; macOS and Linux: ru_maxrss).

Output: OUT/<input path with the extension .txt> (UTF-8), OUT/runlog.jsonl (one line per document: doc_id,
status ok|failed, reason, task, seconds of its read), OUT/tasks_log.jsonl (one line per task), OUT/run_meta.json.

Usage: python run_shield_files.py --set-dir SETS/<set> --out OUT --mode rules|ner [--tasks a,b] [--repeat N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

T_PROCESS = time.perf_counter()
WARMUP = "Le conseil de prud'hommes de Lyon a entendu M. Jean Dupont, né le 3 mars 1980, demeurant 4 rue Neuve à Lille."
NETWORK_ATTEMPTS: list[str] = []
_real_connect = socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host in ("127.0.0.1", "localhost", "::1"):
        return _real_connect(self, address)
    if self.family == getattr(socket, "AF_UNIX", None):
        return _real_connect(self, address)
    NETWORK_ATTEMPTS.append(repr(address))
    raise RuntimeError(f"outbound network connection refused during the evaluation: {address!r}")


def peak_memory_mb() -> float | None:
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            h = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
            return round(pmc.PeakWorkingSetSize / 2**20, 1)
        import resource

        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(r / 2**20 if sys.platform == "darwin" else r / 2**10, 1)
    except Exception:  # noqa: BLE001
        return None


def package_hash() -> str:
    import ragbase_shield

    root = Path(ragbase_shield.__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=("rules", "ner"), required=True)
    ap.add_argument("--tasks", default="", help="only these task names (comma separated)")
    ap.add_argument("--repeat", type=int, default=1, help="speed runs: repeat each task N times (new dossier each)")
    ap.add_argument("--allow-network", action="store_true", help="never used in the protocol")
    args = ap.parse_args()

    set_dir, out = Path(args.set_dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="shield_laptop_"))
    os.environ["RAGBASE_SHIELD_HOME"] = str(work / "home")
    os.environ["RAGBASE_SHIELD_KEYRING"] = "0"
    if args.mode == "rules":
        os.environ["RAGBASE_SHIELD_NER"] = "off"
    else:
        os.environ["RAGBASE_SHIELD_NER"] = "on"
        os.environ["RAGBASE_SHIELD_NER_MODEL"] = "fastino"
        os.environ["RAGBASE_SHIELD_NER_DEVICE"] = "cpu"
    if not args.allow_network:
        socket.socket.connect = _guarded_connect

    import ragbase_shield
    from ragbase_shield.engine import Masker, MemoryStore
    from ragbase_shield.service import Service

    warm = Masker(MemoryStore(locale="fr"), locale="fr")
    warm.mask(WARMUP)
    engine_mode = warm.mode
    cold = time.perf_counter() - T_PROCESS
    if args.mode == "rules" and engine_mode != "rules":
        sys.exit(f"engine mode is {engine_mode!r}, expected rules")
    if args.mode == "ner" and not engine_mode.startswith("rules+ner"):
        sys.exit(f"engine mode is {engine_mode!r}, expected rules+ner (models installed?)")

    tasks = json.loads((set_dir / "tasks.json").read_text(encoding="utf-8"))
    if args.tasks:
        keep = set(args.tasks.split(","))
        tasks = [t for t in tasks if t["task"] in keep]
    svc = Service(work / "home")
    runlog = (out / "runlog.jsonl").open("a", encoding="utf-8")
    tasklog = (out / "tasks_log.jsonl").open("a", encoding="utf-8")
    n_docs = 0
    for rep in range(args.repeat):
        for t in tasks:
            stage = work / "stage" / f"{rep}" / t["task"]
            stage.mkdir(parents=True, exist_ok=True)
            for rel in t["files"]:
                shutil.copyfile(set_dir / "input" / rel, stage / Path(rel).name)
            t0 = time.perf_counter()
            rows = []
            try:
                added = svc.add_dossier(stage)
                code = added["code"]
                d = svc._dossier(code)
                by_name = {ref.name: ref for ref in d.documents(include_unsupported=True)}
                for rel in t["files"]:
                    ref = by_name.get(Path(rel).name)
                    r0 = time.perf_counter()
                    if ref is None:
                        rows.append({"doc_id": rel, "status": "failed", "reason": "not listed by Shield"})
                        continue
                    try:
                        pages, start = [], 0
                        while True:
                            r = svc.read_document(code, ref.id, start)
                            pages.append(r["text"])
                            if r["next"] is None:
                                break
                            start = r["next"]
                        text = "".join(pages)
                        if rep == 0:
                            dest = out / Path(rel).with_suffix(".txt")
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_text(text, encoding="utf-8")
                        rows.append({"doc_id": rel, "status": "ok", "reason": "", "chars_out": len(text),
                                     "read_seconds": round(time.perf_counter() - r0, 4)})
                    except Exception as e:  # noqa: BLE001
                        rows.append({"doc_id": rel, "status": "failed", "reason": f"{type(e).__name__}: {e}"})
            except Exception as e:  # noqa: BLE001
                rows = [{"doc_id": rel, "status": "failed", "reason": f"add_dossier {type(e).__name__}: {e}"}
                        for rel in t["files"]]
            task_seconds = time.perf_counter() - t0
            chars = sum((set_dir / "input" / rel).stat().st_size for rel in t["files"])
            tasklog.write(json.dumps({"task": t["task"], "repeat": rep, "files": len(t["files"]),
                                      "input_bytes": chars, "task_seconds": round(task_seconds, 3),
                                      "failed": sum(1 for r in rows if r["status"] != "ok"),
                                      "peak_memory_mb_so_far": peak_memory_mb()}) + "\n")
            tasklog.flush()
            if rep == 0:
                for r in rows:
                    runlog.write(json.dumps(dict(r, task=t["task"]), ensure_ascii=False) + "\n")
                    n_docs += 1
                runlog.flush()
            print(f"task {t['task']} rep {rep}: {len(t['files'])} files, {task_seconds:.2f} s", flush=True)
    meta = {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "set": set_dir.name, "mode": args.mode, "engine_mode": engine_mode,
        "shield_version": getattr(ragbase_shield, "__version__", "?"),
        "shield_package_sha256": package_hash(), "shield_commit": os.environ.get("SHIELD_COMMIT", "see HEAD_HASH"),
        "env": {k: os.environ.get(k) for k in ("RAGBASE_SHIELD_NER", "RAGBASE_SHIELD_NER_MODEL",
                                               "RAGBASE_SHIELD_NER_DEVICE", "RAGBASE_SHIELD_NER_THREADS",
                                               "RAGBASE_SHIELD_LANGUAGE", "ATEN_CPU_CAPABILITY",
                                               "ONEDNN_MAX_CPU_ISA")},
        "python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(), "cpu_count": os.cpu_count(),
        "cold_seconds": round(cold, 3), "documents": n_docs, "repeat": args.repeat,
        "peak_memory_mb": peak_memory_mb(), "network_attempts": NETWORK_ATTEMPTS,
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=1))
    svc.close()
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
