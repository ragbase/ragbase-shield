"""Download the French Cour de cassation part of the MAPA anonymisation package into .bench_data/.

Dataset: FrancophonIA/MAPA_Anonymization_package on Hugging Face (CC BY 4.0), a mirror of the ELRC-SHARE
"MAPA anonymization package (French)". We use only the LEGAL / COUR_CASSATION1 and COUR_CASSATION2 parts:
19 Cour de cassation decisions in which the anonymised names were replaced by fake names ("desanonymise"),
annotated in WebAnno TSV 3.3, plus the 19 plain-text sources the TSV offsets point into.

The dataset is NOT committed to this repository. This script fetches it at a pinned revision, plus the
dataset card, the MAPA LREC 2022 paper (metric definitions, section 5) and the MAPA annotation guidelines v6
(label definitions), and checks every data file against dataset.sha256 (next to this script).

Usage: python evaluation/public/mapa-fr-cassation/download.py [--force] [--write-manifest]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / ".bench_data" / "public" / "mapa-fr-cassation"
DATA = WORK / "data"
MANIFEST = HERE / "dataset.sha256"

REPO = "FrancophonIA/MAPA_Anonymization_package"
REVISION = "8b147fa201356d555228a6351eefaa750f61cc4d"  # HF commit (lastModified 2025-03-30), measured 2026-10-17
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/"

_CC1 = "data/ANNOTATED_DATA/LEGAL/COUR_CASSATION1"
_CC2 = "data/ANNOTATED_DATA/LEGAL/COUR_CASSATION2"
# (document id, annotated TSV path, source text path), paths as in the dataset repository
DOCS = [
    ("JURITEXT000036980367", "Civil", "JURITEXT000036980367_desanonymise"),
    ("JURITEXT000036980368", "Civil", "JURITEXT000036980368_desanonymise"),
    ("JURITEXT000036980371", "Civil", "JURITEXT000036980371_desanonymise"),
    ("JURITEXT000042524888", "Commercial", "JURITEXT000042524888_desanonymise"),
    ("JURITEXT000042551886", "Commercial", "JURITEXT000042551886_desanonymise-corrected"),
    ("JURITEXT000042579929", "Commercial", "JURITEXT000042579929_desanonymise"),
    ("JURITEXT000042619585", "Commercial", "JURITEXT000042619585_desanonymise"),
    ("JURITEXT000042619587", "Commercial", "JURITEXT000042619587_desanonymise"),
    ("JURITEXT000042397755", "Criminal", "JURITEXT000042397755_desanonymise"),
    ("JURITEXT000042486368", "Criminal", "JURITEXT000042486368_desanonymise"),
    ("JURITEXT000042524834", "Criminal", "JURITEXT000042524834_desanonymise"),
    ("JURITEXT000042579643", "Criminal", "JURITEXT000042579643_desanonymise"),
    ("JURITEXT000042579855", "Criminal", "JURITEXT000042579855_desanonymise"),
    ("JURITEXT000042619505", "Criminal", "JURITEXT000042619505_desanonymise"),
    ("JURITEXT000042619507", "Criminal", "JURITEXT000042619507_desanonymise"),
    ("JURITEXT000042931244", "Criminal", "JURITEXT000042931244_desanonymise"),
    ("JURITEXT000042931251", "Criminal", "JURITEXT000042931251_desanonymise"),
    ("JURITEXT000036947082", "CC2", "JURITEXT000036947082"),
    ("JURITEXT000036947086", "CC2", "JURITEXT000036947086_desanonymise.final"),
]


def remote_paths(chamber: str, stem: str) -> tuple[str, str]:
    if chamber == "CC2":
        return f"{_CC2}/annotated/full_dataset/{stem}.tsv", f"{_CC2}/source/CIVIL/{stem}.txt"
    return f"{_CC1}/annotated/full_dataset/{chamber}/{stem}.tsv", f"{_CC1}/source/{chamber}/{stem}.txt"


def file_list() -> list[tuple[str, str]]:
    """(local relative path under data/, URL)."""
    out = [("README.md", BASE + "README.md")]
    for doc, chamber, stem in DOCS:
        tsv, txt = remote_paths(chamber, stem)
        out.append((f"tsv/{doc}.tsv", BASE + tsv))
        out.append((f"txt/{doc}.txt", BASE + txt))
    return out


# Reference documents (not data, not hashed: the publisher may re-render them).
REFERENCES = {
    "mapa_lrec2022_paper.pdf": "https://aclanthology.org/2022.legal-1.12.pdf",
    "mapa_annotation_guidelines_v6.pdf":
        "http://www.elra.info/media/filer_public/2022/05/10/mapa_annotation-guidelines-v6.pdf",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ragbase-shield-eval/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="download again even if the files exist")
    ap.add_argument("--write-manifest", action="store_true",
                    help="write dataset.sha256 from the downloaded files instead of checking them")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    for rel, url in file_list():
        dest = DATA / rel
        if dest.exists() and not args.force:
            continue
        print(f"get {rel}")
        fetch(url, dest)
    for name, url in REFERENCES.items():
        dest = WORK / "reference" / name
        if dest.exists() and not args.force:
            continue
        try:
            print(f"get reference/{name}")
            fetch(url, dest)
        except Exception as exc:  # noqa: BLE001 - references are optional
            print(f"  warning: could not fetch {name}: {exc}", file=sys.stderr)

    rows = [(sha256(DATA / rel), rel) for rel, _url in file_list()]
    if args.write_manifest:
        MANIFEST.write_text("".join(f"{h}  {rel}\n" for h, rel in rows), encoding="utf-8")
        print(f"wrote {MANIFEST} ({len(rows)} files)")
        return 0
    if not MANIFEST.exists():
        print(f"no {MANIFEST.name}: run with --write-manifest once", file=sys.stderr)
        return 1
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, rel = line.split(None, 1)
            expected[rel.strip()] = h
    bad = [rel for h, rel in rows if expected.get(rel) != h]
    if bad or len(expected) != len(rows):
        print(f"SHA-256 mismatch or missing entries: {bad}", file=sys.stderr)
        return 1
    print(f"OK: {len(rows)} files in {DATA} match {MANIFEST.name} (revision {REVISION[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
