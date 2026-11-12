"""Download FR-PII-Bench v0 (JaqueBill/fr-pii-bench, CC BY 4.0) into .bench_data/public/fr-pii-bench/.

The dataset is NOT committed to this repository. This script fetches it at a pinned Hugging Face revision,
plus the dataset card, the generator and the author's technical report (for the metric definitions), and
checks the SHA-256 of the data file.

Usage: python evaluation/public/fr-pii-bench/download.py [--force]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "fr-pii-bench"

REPO = "JaqueBill/fr-pii-bench"
REVISION = "5476b0a489249047a478083ac856a328d0e4d2c3"  # HF commit of 2026-10-07, the one measured on 2026-10-17
REPORT_URL = "https://raw.githubusercontent.com/xiao98/presidio-fr-docs/main/REPORT.md"

FILES = {
    "fr_pii_bench_v0.jsonl": f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/fr_pii_bench_v0.jsonl",
    "README.md": f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/README.md",
    "generate.py": f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/generate.py",
    "REPORT.md": REPORT_URL,
}
# SHA-256 of the data file at REVISION (300 lines, 2 105 gold entities).
DATA_SHA256 = "8b828450534ed43c640f616502c8a6e49b59eefb33032eac951948dcf9e8f9f6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ragbase-shield-eval/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="download again even if the files exist")
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = WORK / name
        if dest.exists() and not args.force:
            print(f"have  {name}")
            continue
        fetch(url, dest)
        print(f"got   {name} ({dest.stat().st_size} bytes)")
    got = sha256(WORK / "fr_pii_bench_v0.jsonl")
    if got != DATA_SHA256:
        print(f"SHA-256 MISMATCH for fr_pii_bench_v0.jsonl: {got} (expected {DATA_SHA256})", file=sys.stderr)
        return 1
    n = sum(1 for _ in (WORK / "fr_pii_bench_v0.jsonl").open(encoding="utf-8"))
    print(f"ok    fr_pii_bench_v0.jsonl sha256={got} docs={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
