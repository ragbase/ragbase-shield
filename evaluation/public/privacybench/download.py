"""Fetch PrivacyBench (Tonic.ai) and its scoring code into .bench_data/public/privacybench/.

PrivacyBench is public:

- data: https://huggingface.co/datasets/TonicAI/Privacy-Bench (CC BY 4.0). Raw exports under tasks/<set>/
  (.eml files, a Slack export, a Drive listing with PDF/DOCX/XLSX/CSV), the generated answer keys under
  ground_truth/<set>/, human annotations for six sets under human_annotations/.
- scoring code: https://github.com/TonicAI/privacy_bench_metrics (no licence file; the README says
  "license to be confirmed"). Used here as is, locally, to score Shield with the benchmark's own metric code.

Pinned revisions (2026-10-18):

- dataset `main` = a79d9e80c5ee68f5dd79da8452e5eb1e1ba97a1e (2026-10-15 22:46 UTC, v2.5 answer key; tag v2.5
  itself is a9f3e392, the following commits only touched the card and the figures).
- metrics tag v2.5 = 2a882312d40838a27b6abb87f84096a4e30d4433 (2026-10-15).

Usage:
    python evaluation/public/privacybench/download.py                 # download from the Hub + GitHub
    python evaluation/public/privacybench/download.py --from-local D  # copy D/data and D/code/privacy_bench_metrics

The Hub rate-limits anonymous downloads (HTTP 429 after a few hundred files); `snapshot_download` retries,
or run the command again, it resumes. Writes manifest.json (revisions, file count, bytes, sha256 of every
data file) next to the copied data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "privacybench"
DATA = WORK / "data"
CODE = WORK / "code" / "privacy_bench_metrics"

DATASET = "TonicAI/Privacy-Bench"
DATASET_REVISION = "a79d9e80c5ee68f5dd79da8452e5eb1e1ba97a1e"
METRICS_REPO = "https://github.com/TonicAI/privacy_bench_metrics.git"
METRICS_COMMIT = "2a882312d40838a27b6abb87f84096a4e30d4433"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str, cwd: Path) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def copy_local(src: Path) -> None:
    s_data, s_code = src / "data", src / "code" / "privacy_bench_metrics"
    if not (s_data / "README.md").exists() or not (s_code / "synthesis_evaluation").exists():
        sys.exit(f"--from-local: expected {s_data}/README.md and {s_code}/synthesis_evaluation")
    if DATA.exists():
        shutil.rmtree(DATA)
    shutil.copytree(s_data, DATA, ignore=shutil.ignore_patterns(".cache", ".DS_Store"))
    if CODE.exists():
        shutil.rmtree(CODE)
    # the example runs of another checkout are not part of the code
    shutil.copytree(s_code, CODE, ignore=shutil.ignore_patterns("runs", "__pycache__", ".DS_Store"))


def download() -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit("pip install huggingface_hub (or use --from-local)")
    DATA.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=DATASET, repo_type="dataset", revision=DATASET_REVISION, local_dir=str(DATA),
                      max_workers=4)
    if not CODE.exists():
        CODE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", METRICS_REPO, str(CODE)], check=True)
    subprocess.run(["git", "checkout", "--quiet", METRICS_COMMIT], cwd=str(CODE), check=True)


def manifest() -> dict:
    files = sorted(p for p in DATA.rglob("*") if p.is_file() and ".cache" not in p.parts)
    hashes = {str(p.relative_to(DATA)): sha256(p) for p in files}
    sets = sorted(p.name for p in (DATA / "tasks").iterdir() if p.is_dir())
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {"repo": DATASET, "revision": DATASET_REVISION, "license": "cc-by-4.0", "sets": sets,
                    "files": len(files), "bytes": sum(p.stat().st_size for p in files), "sha256": hashes},
        "code": {"repo": METRICS_REPO, "commit": METRICS_COMMIT, "license": "none (README: to be confirmed)",
                 "head": git("rev-parse", "HEAD", cwd=CODE), "tag": git("describe", "--tags", "--exact-match", cwd=CODE)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-local", type=Path, default=None, help="copy an existing download (dir with data/ and code/)")
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    if args.from_local:
        copy_local(args.from_local.resolve())
    else:
        download()
    m = manifest()
    (WORK / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    short = {k: v for k, v in m["dataset"].items() if k != "sha256"}
    print(json.dumps({"data": str(DATA), "code": str(CODE), "dataset": short, "code_rev": m["code"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
