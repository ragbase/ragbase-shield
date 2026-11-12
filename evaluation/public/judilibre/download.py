"""Draw the fixed random sample of 200 French court decisions (Judilibre, Licence Ouverte 2.0).

Source: the Hugging Face dataset ``antoinejeannot/jurisprudence`` (Judilibre API export by Antoine Jeannot, data
from the Cour de cassation), at a pinned revision. The dataset is NOT committed to this repository: the sample
goes to ``.bench_data/public/judilibre/``.

Sampling design (fixed before Shield was run on any decision):

- three strata, one per file of the dataset: Cour de cassation, cours d'appel, tribunaux judiciaires;
- equal allocation: 67 + 67 + 66 = 200 decisions (equal, not proportional, so first-instance decisions are
  not reduced to a dozen; the results are reported per stratum so a reader can reweight);
- inside a stratum: ``random.Random(42)`` draws a pool of 150 line numbers without replacement
  (``rng.sample(range(N), 150)``, strata drawn in the order above with the same generator); the decisions
  are taken in pool order and the first k eligible ones are kept;
- eligible: ``text`` is not empty and ``to_be_deleted`` is not true. Nothing else is filtered.

The jsonl.gz files are streamed and decompressed on the fly; only the selected lines are kept (about 3.3 GB
pass through the network, nothing large is written to disk). The script checks that each file has the line
count announced by the Parquet metadata at the same revision. Standard library only.

Usage: python evaluation/public/judilibre/download.py [--force]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "judilibre"

REPO = "antoinejeannot/jurisprudence"
REVISION = "8019db1080cf6dc8a34d73ee44d704a8e90b558e"  # HF commit of 2025-03-20 (release v2025.03.20)
SEED = 42
POOL = 150
# (file stem, rows at REVISION from the Parquet metadata, decisions kept)
STRATA = (
    ("cour_de_cassation", 553_075, 67),
    ("cour_d_appel", 430_654, 67),
    ("tribunal_judiciaire", 142_239, 66),
)
CHUNK = 1 << 20
# SHA-256 of sample.jsonl as drawn on 2026-10-17 (Python 3.11.4); a different value means a different sample.
EXPECTED_SAMPLE_SHA256 = "284ed073c5ad81ce06241e7c4aea9a3a6c459ea82a71acb802eebd0ce00d6575"


def url_for(stem: str) -> str:
    return f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{stem}.jsonl.gz"


def draw_pools() -> dict[str, list[int]]:
    rng = random.Random(SEED)
    return {stem: rng.sample(range(n_rows), POOL) for stem, n_rows, _k in STRATA}


def _open(url: str, offset: int):
    headers = {"User-Agent": "ragbase-shield-eval/0.1"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120)


def compressed_chunks(url: str):
    """Yield the raw bytes of ``url``; reopens with a Range header if the connection drops."""
    received, failures = 0, 0
    while True:
        try:
            with _open(url, received) as r:
                if received and r.status != 206:
                    raise RuntimeError("server ignored the Range header; cannot resume")
                while True:
                    block = r.read(CHUNK)
                    if not block:
                        return
                    received += len(block)
                    yield block
        except (OSError, TimeoutError) as exc:  # network error: resume from the last byte received
            failures += 1
            if failures > 8:
                raise
            print(f"  network error after {received} bytes ({exc}); resuming", file=sys.stderr)
            time.sleep(2 * failures)


def lines_of(url: str, wanted: set[int]):
    """Stream a (possibly multi-member) gzip JSONL file. Yields (line_no, raw line) for wanted lines,
    then ('count', total lines)."""
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf = b""
    line_no = 0
    order = sorted(wanted)
    ptr = 0

    def feed(data: bytes):
        nonlocal buf, line_no, ptr
        buf += data
        cut = buf.rfind(b"\n")
        if cut < 0:
            return
        complete, buf = buf[:cut + 1], buf[cut + 1:]
        n = complete.count(b"\n")
        if ptr < len(order) and order[ptr] < line_no + n:
            parts = complete.split(b"\n")
            while ptr < len(order) and order[ptr] < line_no + n:
                yield order[ptr], parts[order[ptr] - line_no]
                ptr += 1
        line_no += n

    for block in compressed_chunks(url):
        data = dec.decompress(block)
        while dec.unused_data:  # next gzip member
            rest = dec.unused_data
            yield from feed(data)
            dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
            data = dec.decompress(rest)
        yield from feed(data)
    yield from feed(dec.flush())
    if buf.strip():  # last line without a trailing newline
        if ptr < len(order) and order[ptr] == line_no:
            yield order[ptr], buf
        line_no += 1
    yield "count", line_no


def eligible(rec: dict) -> bool:
    return bool((rec.get("text") or "").strip()) and rec.get("to_be_deleted") is not True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="draw again even if the sample exists")
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    out = WORK / "sample.jsonl"
    manifest_path = WORK / "sample_manifest.json"
    if out.exists() and manifest_path.exists() and not args.force:
        print(f"sample already there: {out} (use --force to draw again)")
        return 0

    pools = draw_pools()
    kept_all: list[dict] = []
    manifest: dict = {"repo": REPO, "revision": REVISION, "seed": SEED, "pool": POOL, "strata": []}
    for stem, n_rows, k in STRATA:
        t0 = time.time()
        pool = pools[stem]
        got: dict[int, dict] = {}
        total = None
        for key, raw in lines_of(url_for(stem), set(pool)):
            if key == "count":
                total = raw
                continue
            got[key] = json.loads(raw)
        if total != n_rows:
            print(f"ERROR {stem}: {total} lines, expected {n_rows} (revision changed?)", file=sys.stderr)
            return 2
        if len(got) != len(pool):
            print(f"ERROR {stem}: {len(got)} of {len(pool)} pool lines found", file=sys.stderr)
            return 2
        kept, skipped = [], []
        for line_no in pool:
            rec = got[line_no]
            if len(kept) == k:
                break
            if eligible(rec):
                rec["_stratum"] = stem
                rec["_line"] = line_no
                kept.append(rec)
            else:
                skipped.append({"line": line_no, "id": rec.get("id"), "empty_text": not (rec.get("text") or "").strip(),
                                "to_be_deleted": rec.get("to_be_deleted")})
        if len(kept) < k:
            print(f"ERROR {stem}: only {len(kept)} eligible decisions in the pool of {POOL}", file=sys.stderr)
            return 2
        kept_all.extend(kept)
        manifest["strata"].append({
            "stratum": stem, "rows": n_rows, "kept": k, "lines_kept": [r["_line"] for r in kept],
            "ids_kept": [r.get("id") for r in kept], "skipped_before_k": skipped,
            "seconds": round(time.time() - t0, 1),
        })
        print(f"{stem}: {k} kept, {len(skipped)} skipped, {total} lines streamed in {time.time() - t0:.0f}s")

    with out.open("w", encoding="utf-8") as f:
        for rec in kept_all:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    manifest["decisions"] = len(kept_all)
    manifest["sample_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(kept_all)} decisions), sha256 {manifest['sample_sha256']}")
    if manifest["sample_sha256"] != EXPECTED_SAMPLE_SHA256:
        print("WARNING: this is not the sample measured on 2026-10-17 (RESULTS.md); compare sample_manifest.json",
              file=sys.stderr)
        return 3
    print("same sample as the one measured on 2026-10-17")
    return 0


if __name__ == "__main__":
    sys.exit(main())
