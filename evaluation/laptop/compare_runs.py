"""Paired comparison of two scored runs on the same set (pre-registered decision rule, PROTOCOL.md section 11.3).

Inputs: two result JSON files written by ``score_text.py`` for the same gold (same documents). For each primary
measure the unit is the document: P1 = exposed gold items (headline parts), P2 = must-stay-clear items altered.
The difference of the pooled rates (A minus B) gets a 95 % interval from a paired bootstrap over documents (2,000
resamples, ``random.Random(20261023)``). A claim "B is better than A on this measure" is allowed only when the
whole interval is above 0 (for both measures, lower is better). Rates also get a 95 % Wilson interval.

Version 1.1 (2026-10-24, PROTOCOL_ADDENDUM_1.md section 17.4 and 17.5, for scorer 1.1): headline parts only
(gold and keep items in document properties or tracked deletions are left out, as in the scorer's headlines); a
document that is ``not_run`` or ``unscorable`` in either run is left out of BOTH runs and listed; P1 is computed
twice, strict (partial + missed) and value (``exposed_value``), and a P1 claim needs both readings to agree.

Usage: python compare_runs.py A.json B.json [--name-a X --name-b Y]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys

SEED = 20261023
RESAMPLES = 2000
MUST = ("court", "court_city", "article", "code", "law", "legal_ref", "legal_term")


SIDE_PARTS = ("metadata", "hidden")
EXCLUDED = ("not_run", "unscorable")


def per_doc(path: str) -> tuple[dict, set]:
    d = json.load(open(path, encoding="utf-8"))
    out, excluded = {}, set()
    for doc in d["documents"]:
        if doc["status"] in EXCLUDED:
            excluded.add(doc["doc_id"])
        items = [i for i in doc["items"] if i["part"] not in SIDE_PARTS and i["status"] != "no_ident"]
        keep = [k for k in doc["keep"] if k["class"] in MUST and k.get("part", "body") not in SIDE_PARTS]
        out[doc["doc_id"]] = (sum(i["status"] in ("partial", "missed") for i in items), len(items),
                              sum(k["altered"] for k in keep), len(keep),
                              sum(bool(i.get("exposed_value", i["status"] in ("partial", "missed"))) for i in items))
    return out, excluded


def wilson(x: int, n: int) -> tuple[float, float]:
    if not n:
        return (float("nan"), float("nan"))
    z = 1.96
    p = x / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--name-a", default="A")
    ap.add_argument("--name-b", default="B")
    args = ap.parse_args()
    (A, ex_a), (B, ex_b) = per_doc(args.a), per_doc(args.b)
    if set(A) != set(B):
        sys.exit("the two runs do not cover the same documents")
    left_out = ex_a | ex_b
    if left_out:
        print(f"left out of both runs (not_run or unscorable in at least one run): {len(left_out)} documents: "
              + ", ".join(sorted(left_out)))
    ids = sorted(set(A) - left_out)
    if not ids:
        print("no document left to compare")
        return 0
    rng = random.Random(SEED)
    verdicts = {}
    # P1 strict and P2 first, in the 1.0 order (same bootstrap draws as 1.0); the value reading after them
    for label, xi, ni in (("P1 exposed gold items (strict)", 0, 1), ("P2 must-stay-clear items altered", 2, 3),
                          ("P1 exposed gold items (value)", 4, 1)):
        xa, xb = sum(A[i][xi] for i in ids), sum(B[i][xi] for i in ids)
        n = sum(A[i][ni] for i in ids)
        if not n:
            print(f"{label}: no items in this set")
            continue
        diffs = []
        for _ in range(RESAMPLES):
            s = [ids[rng.randrange(len(ids))] for _ in ids]
            nn = sum(A[i][ni] for i in s)
            if nn:
                diffs.append((sum(A[i][xi] for i in s) - sum(B[i][xi] for i in s)) / nn)
        diffs.sort()
        lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
        wa, wb = wilson(xa, n), wilson(xb, n)
        verdict = (f"{args.name_b} better" if lo > 0 else f"{args.name_a} better" if hi < 0 else "no clear difference")
        verdicts[xi] = verdict
        print(f"{label}: {args.name_a} {xa}/{n} ({xa / n:.2%}, 95% {wa[0]:.2%} to {wa[1]:.2%}); "
              f"{args.name_b} {xb}/{n} ({xb / n:.2%}, 95% {wb[0]:.2%} to {wb[1]:.2%}); "
              f"difference {(xa - xb) / n:+.2%} (95% {lo:+.2%} to {hi:+.2%}): {verdict}")
    if 0 in verdicts:
        p1 = verdicts[0] if verdicts[0] == verdicts.get(4) else "no claim (the strict and value readings disagree)"
        print(f"P1 claim (both readings must agree, PROTOCOL_ADDENDUM_1.md section 17.4): {p1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
