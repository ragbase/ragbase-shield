"""Overall score (F1), precision and recall of a pseudonymisation tool, computed word by word.

The score needs three things per document: the input text, the tool's output text and the answer key. It reads
them exactly as ``score_text.py`` does: this file imports ``score_text.py`` (same folder), calls its functions,
and stops with an error when one of its own counts differs from the ``score_text.py`` result of the same run
(``--score-text-json``, required). No rule depends on the tool.

Definitions
  UNITS. The letter-or-digit words of the input. Words of document properties and of tracked deletions are left
    out.
  WORDS TO MASK. The identifying words of the personal data items of the answer key: for "M. Jean Dupont" the
    words "Jean" and "Dupont", for "Valmont SARL" the word "Valmont". Left out of the count: the other words of
    an item, and the BOUNDARY words just outside it (a title before a person, a legal form with its article next
    to a company, a street word with its function words before an address).
  COUNTS. TP = a word to mask that the tool changed. FN = a word to mask that the tool kept. FP = a changed word
    that is outside every item and is not a boundary word. Precision = TP / (TP + FP). Recall = TP / (TP + FN).
    F1 = 2 TP / (2 TP + FP + FN). The counts of all documents are added, then the ratios are computed (micro
    average).
  STRICT reading (``summary.word.strict``): the overall score. Every changed word outside the answer key is an
    FP, legal terms, dates and amounts included.
  FAILED document (no usable output, or more than half of the words outside its items changed when there are 20
    or more): its words to mask are FN, and it adds no FP.

Other readings of the same counts, in the JSON result only
  ``summary.word``: SCOPE-ADJUSTED (changed dates, amounts, times and roles listed in the answer key are not FP);
    ARTEFACT-TOLERANT (a word that a re-rendered file only splits, glues or hyphenates is not FP); KEEP-ONLY (FP
    only inside the legal terms and the other text to keep of the answer key; dates, amounts, times and roles
    left out); VALUE-TOLERANT recall (a kept word counts as TP when no more than half of the identifying letters
    and digits of its item stay readable at their place).
  ``summary.word_sensitivity``: boundary words counted as FP; failed documents read as they are, or with all
    their other words as FP; digit-only words and month names not FP; every word of an item counted as a word
    to mask.
  ``summary.item``: the same idea per personal data item. Recall = items fully masked / items. Precision = groups
    of changed regions (merged by item) with 50 % or more of their characters on personal data / (groups +
    changed regions that touch no item).
  ``summary.intervals``: 95 % intervals, percentile bootstrap, 2,000 resamples, fixed seed. Unit = the top folder
    of the document id, else the document. Under 10 units no interval is given; the lowest and highest unit
    values are given.

The JSON result holds counts only: no input text and no output text.

Usage
  python score_f1.py score --gold GOLD.jsonl --inputs IN_DIR (--outputs OUT_DIR | --outputs-manifest M.jsonl)
                           [--runlog RUN.jsonl] --score-text-json SCORE_TEXT_RESULT.json --json RESULT.json
                           [--md RESULT.md] [--tool NAME] [--set SET] [--docs DOC_IDS.txt]
  python score_f1.py pairs --gold GOLD.jsonl --pairs P.jsonl --score-text-json SCORE_TEXT_RESULT.json
                           --json RESULT.json [--md RESULT.md] [--tool NAME] [--set SET]
  python score_f1.py common --out DOC_IDS.txt RESULT.json [RESULT.json ...]   (documents scored in every result)
  python score_f1.py --selftest
"""
from __future__ import annotations

import argparse
import bisect
import datetime as _dt
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import score_text as st  # noqa: E402  the scorer of the same folder

F1_VERSION = "laptop-f1-1.0"
NEUTRAL_KEEP = ("date", "amount", "time", "role")
SEED = 20261023
RESAMPLES = 2000
MIN_UNITS = 10
NO_OUTPUT = "no usable output"
RETENTION = "retention under 0.50"
FP_BUCKETS = ("must_stay_clear", "other_keep", "neutral_keep", "no_keep_item")

# Boundary words: (anchor words, filler words, sides). Anchors and fillers are the non-identifying word lists of
# the item's family (score_text.identifying_tokens), so a word is left out next to a span exactly when the same
# word would be left out inside it.
BOUNDARY = {"person": (st.TITLE_WORDS, frozenset(), ("left",)),
            "org": (st.LEGAL_FORMS, st.FUNCTION_WORDS, ("left", "right")),
            "address": (st.STREET_WORDS, st.FUNCTION_WORDS, ("left",))}

# Token shapes for the shape-extended reading: month names (French, English; "may" left out as an English verb)
# and digit-only tokens, compared on the score_text key (case and accents folded).
MONTH_WORDS = frozenset(st.tok_key(w) for w in (
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
    "décembre", "janv", "févr", "fév", "avr", "juil", "sept", "oct", "nov", "déc", "january", "february", "march",
    "april", "june", "july", "august", "september", "october", "november", "december", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "dec"))


class ReadingMismatch(RuntimeError):
    """The rebuilt per-word reading differs from score_text.py: no score is reported."""


def _same(doc_id: str, what: str, mine, theirs) -> None:
    if mine != theirs:
        raise ReadingMismatch(f"{doc_id}: {what}: rebuilt {mine!r}, score_text.py {theirs!r}")


def cluster_of(doc_id: str) -> str:
    """Resampling unit: the top folder of the doc_id (a matter of the Max set), else the document."""
    return doc_id.split("/", 1)[0] if "/" in doc_id else doc_id


# ---------------------------------------------------------------------------------------------- one document
def _side_chars(rec: dict, in_text: str, hidden) -> list[str]:
    """Part of each input character, as ``score_text.score_doc`` sets it: "" body, "metadata", "hidden"."""
    side = [""] * len(in_text)
    if Path(rec.get("file", "")).suffix.lower() in (".docx", ".pdf", ".xlsx"):
        for m in st.READER_LINE_RE.finditer(in_text):
            e = in_text.find("\n", m.start())
            for c in range(m.start(), e if e >= 0 else len(in_text)):
                side[c] = "metadata"
    for hs, he in hidden or ():
        for c in range(max(0, hs), min(len(in_text), he)):
            side[c] = side[c] or "hidden"
    return side


def _part_of(g: dict, side: list[str]) -> str:
    if g.get("part") in ("metadata", "hidden"):
        return g["part"]
    for c in range(g["start"], g["end"]):
        if side[c]:
            return side[c]
    return "body"


def _overlapping(a, starts: list[int], s: int, e: int) -> list[int]:
    """Indexes of the input tokens that overlap characters s..e-1 (the ``t[1] > s and t[0] < e`` test)."""
    out = []
    for k in range(max(0, bisect.bisect_right(starts, s) - 1), len(a)):
        if a[k][0] >= e:
            break
        if a[k][1] > s:
            out.append(k)
    return out


def boundary_words(a, in_text: str, gold: list, scored: list[int], nongold_ok: set, item_toks: dict):
    """Boundary words and the extended span of each scored item: (set of token indexes, {item: (s, e)}).

    From the first (last) token of the item, walk left (right) on the same line, skipping punctuation tokens. Collect
    letter-or-digit tokens while they are words outside gold, in no keep item, and in the family's anchor or filler
    list. Keep the collected chain up to its outermost anchor; on the left side also one filler just beyond it (the
    article of "la société"). A chain with no anchor is dropped."""
    out: set[int] = set()
    ext: dict[int, tuple[int, int]] = {}
    for i in scored:
        g = gold[i]
        rule = BOUNDARY.get(st.label_family(g["label"]))
        toks = item_toks[i]
        s_, e_ = g["start"], g["end"]
        if rule and toks:
            anchors, fillers, sides = rule
            for side_ in sides:
                step = -1 if side_ == "left" else 1
                k = toks[0] - 1 if side_ == "left" else toks[-1] + 1
                edge = a[toks[0]][0] if side_ == "left" else a[toks[-1]][1]
                chain: list[tuple[int, bool]] = []
                while 0 <= k < len(a):
                    t = a[k]
                    gap = in_text[t[1]:edge] if side_ == "left" else in_text[edge:t[0]]
                    if "\n" in gap:
                        break
                    edge = t[0] if side_ == "left" else t[1]
                    if st.has_alnum(t[2]):
                        w = t[2].lower()
                        if k not in nongold_ok or (w not in anchors and w not in fillers):
                            break
                        chain.append((k, w in anchors))
                    k += step
                last = max((j for j, (_, is_a) in enumerate(chain) if is_a), default=-1)
                if last < 0:
                    continue
                cut = last + 1
                if side_ == "left" and cut < len(chain) and not chain[cut][1]:
                    cut += 1
                kept_chain = [k_ for k_, _ in chain[:cut]]
                out.update(kept_chain)
                if side_ == "left":
                    s_ = min(s_, min(a[k_][0] for k_ in kept_chain))
                else:
                    e_ = max(e_, max(a[k_][1] for k_ in kept_chain))
        ext[i] = (s_, e_)
    return out, ext


def _lig(s: str) -> str:
    return s.replace("œ", "oe").replace("æ", "ae")


def read_doc(rec: dict, in_text: str, out_text: str | None, status: str = "ok", reason: str = "",
             hidden: list | None = None) -> tuple[dict, dict]:
    """(``score_text.score_doc`` result, word and item row of this document)."""
    res = st.score_doc(rec, in_text, out_text, status, reason, hidden=hidden)
    doc_id = rec["doc_id"]
    row = {"doc_id": doc_id, "status": res["status"], "reason": res["reason"], "failed_kind": None,
           "format": Path(rec.get("file", "")).suffix.lower() or "text", "cluster": cluster_of(doc_id)}
    if res["status"] in st.EXCLUDED:
        return res, row
    gold, keep = rec.get("gold", []), rec.get("keep", [])
    a = st.tokenize(in_text)
    starts = [t[0] for t in a]
    side = _side_chars(rec, in_text, hidden)
    gold_cov = [False] * len(in_text)
    for g in gold:
        for c in range(g["start"], g["end"]):
            gold_cov[c] = True
    for kp in keep:
        if any(gold_cov[c] for c in range(kp["start"], kp["end"])):
            raise ReadingMismatch(f"{doc_id}: keep item {kp.get('id')} overlaps a gold item")
    aside = [bool(side[t[0]]) for t in a]
    is_gold_tok = [any(gold_cov[c] for c in range(t[0], t[1])) for t in a]
    outside = [k for k, t in enumerate(a) if st.has_alnum(t[2]) and not is_gold_tok[k] and not aside[k]]
    _same(doc_id, "words outside gold", len(outside), res["words_outside_gold"])

    units = {k for k, t in enumerate(a) if st.has_alnum(t[2]) and not aside[k]}
    idts = [st.identifying_tokens(g, a, in_text) for g in gold]
    item_toks = {i: _overlapping(a, starts, g["start"], g["end"]) for i, g in enumerate(gold)}
    scored_body = [i for i, g in enumerate(gold) if idts[i] and _part_of(g, side) == "body"]
    gold_units = {k for i in scored_body for k in idts[i]} & units
    span_units = gold_units | ({k for i in scored_body for k in item_toks[i]} & units)
    out_set = set(outside)
    if gold_units & out_set or span_units & out_set:
        raise ReadingMismatch(f"{doc_id}: an identifying token lies outside every gold span")
    _same(doc_id, "scored body gold items", len(scored_body),
          sum(1 for it in res["items"] if it["part"] == "body" and it["status"] != "no_ident"))

    # keep classes of each word outside gold, from the keep items whose span it overlaps (any part)
    classes: dict[int, set] = {}
    in_keep_tok: set[int] = set()
    for kp in keep:
        for k in _overlapping(a, starts, kp["start"], kp["end"]):
            in_keep_tok.add(k)
            if k in out_set:
                classes.setdefault(k, set()).add(kp["class"])
    boundary, ext = boundary_words(a, in_text, gold, scored_body, out_set - in_keep_tok, item_toks)
    nongold = [k for k in outside if k not in boundary]

    def bucket(k: int) -> str:
        c = classes.get(k)
        if not c:
            return "no_keep_item"
        if c & set(st.MUST_STAY_CLEAR):
            return "must_stay_clear"
        if c - set(NEUTRAL_KEEP):
            return "other_keep"
        return "neutral_keep"

    def is_shape(k: int) -> bool:
        key = st.tok_key(a[k][2])
        return key.isdigit() or key in MONTH_WORDS

    # the per-word reading of score_text (alignment, then rejoin), rebuilt with its functions
    kept = b = match = out_norm = None
    if status == "ok" and out_text is not None:
        hold = {st.tok_key(a[k][2]) for i in range(len(gold)) for k in idts[i]}
        held_chars = [gold_cov[c] or bool(side[c]) for c in range(len(in_text))]
        a2, b, match, out_norm = st.align(in_text, out_text, held_chars, hold)
        if a2 != a:
            raise ReadingMismatch(f"{doc_id}: tokens differ")
        changed_out = sum(1 for k in outside if match[k] == -1)
        retention = 1 - changed_out / len(outside) if outside else 1.0
        _same(doc_id, "retention", round(retention, 4), res["retention"])
        kept = [m != -1 for m in match]
        statuses = []
        for i, g in enumerate(gold):
            idt = idts[i]
            tk = item_toks[i]
            if not idt:
                statuses.append("no_ident")
                continue
            ch = [match[k] == -1 for k in idt]
            s_ = "protected" if all(ch) else "missed" if not any(ch) else "partial"
            if s_ != "missed" and tk and st._rejoined("".join(st.glued(a[k][2]) for k in idt), a, b, match, out_norm,
                                                      tk[0], tk[-1] + 1):
                s_ = "missed"
                for k in tk:
                    kept[k] = True
            statuses.append(s_)
        altered = []
        for kp in keep:
            toks = [k for k in _overlapping(a, starts, kp["start"], kp["end"]) if st.has_alnum(a[k][2])]
            alt = any(match[k] == -1 for k in toks)
            if alt and toks and st._rejoined(st.glued(kp["text"]), a, b, match, out_norm, toks[0], toks[-1] + 1):
                alt = False
                for k in toks:
                    kept[k] = True
            altered.append(alt)
        if res["status"] == "ok":
            _same(doc_id, "gold item statuses", statuses, [it["status"] for it in res["items"]])
            _same(doc_id, "keep items altered", altered, [k["altered"] for k in res["keep"]])

    ext_cov = list(gold_cov)
    for i, (s_, e_) in ext.items():
        for c in range(s_, e_):
            ext_cov[c] = True
    spans = [ext.get(i, (g["start"], g["end"])) for i, g in enumerate(gold)]

    def regions_of(changed: list[bool]) -> dict:
        regions = [r for r in st.changed_regions(a, changed, in_text) if not aside[r[2]]]
        fm = ok50 = 0
        touch = []
        for rs, re_, _k0, _k1 in regions:
            ov = sum(gold_cov[rs:re_])
            fm += ov == 0
            ok50 += (re_ - rs) > 0 and ov / (re_ - rs) >= 0.5
            touch.append([i for i, (es, ee) in enumerate(spans) if es < re_ and ee > rs])
        parent = list(range(len(regions)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        first: dict[int, int] = {}
        for ri, items in enumerate(touch):
            for it in items:
                if it in first:
                    parent[find(ri)] = find(first[it])
                else:
                    first[it] = ri
        comps: dict[int, list[int]] = {}
        for ri, items in enumerate(touch):
            if items:
                comps.setdefault(find(ri), []).append(ri)
        g_ok = 0
        for members in comps.values():
            chars = sum(regions[m][1] - regions[m][0] for m in members)
            ov = sum(sum(ext_cov[regions[m][0]:regions[m][1]]) for m in members)
            g_ok += chars > 0 and ov / chars >= 0.5
        spill = sum(1 for ri, (_rs, _re, k0, k1) in enumerate(regions) if touch[ri]
                    for k in range(k0, k1) if k in out_set and changed[k])
        return {"regions": len(regions), "false": fm, "ok50": ok50, "groups": len(comps), "groups_ok50": g_ok,
                "false_ext": sum(1 for t in touch if not t), "spill": spill}

    def words_of(changed: list[bool]) -> dict:
        fp = Counter({b_: 0 for b_ in FP_BUCKETS})
        fpc = Counter()
        bchg = shape = 0
        for k in outside:
            if not changed[k]:
                continue
            if k in boundary:
                bchg += 1
                continue
            b_ = bucket(k)
            fp[b_] += 1
            for c in classes.get(k, ()):
                fpc[c] += 1
            if b_ == "no_keep_item" and is_shape(k):
                shape += 1
        return {"fp": dict(fp), "fp_class": dict(sorted(fpc.items())), "boundary_changed": bchg, "shape": shape}

    def artefacts_of(changed: list[bool]) -> tuple[int, int]:
        """(words forgiven, runs forgiven): runs of changed non-gold words outside keep items read in one piece by
        the rejoin test of score_text (also with the ligatures oe and ae written as two letters)."""
        cand = [k for k in nongold if changed[k] and k not in in_keep_tok]
        runs, cur = [], []
        for k in cand:
            if cur and any(st.has_alnum(a[j][2]) and (not changed[j] or is_gold_tok[j] or j in in_keep_tok)
                           for j in range(cur[-1] + 1, k)):
                runs.append(cur)
                cur = []
            cur.append(k)
        if cur:
            runs.append(cur)
        words = nruns = 0
        for run in runs:
            g_ = "".join(st.glued(a[k][2]) for k in run)
            if st._rejoined(g_, a, b, match, out_norm, run[0], run[-1] + 1) or (
                    _lig(g_) != g_ and st._rejoined(_lig(g_), a, b, match, out_norm, run[0], run[-1] + 1)):
                words += len(run)
                nruns += 1
        return words, nruns

    failed = res["status"] == "failed"
    zero_w = {"fp": {b_: 0 for b_ in FP_BUCKETS}, "fp_class": {}, "boundary_changed": 0, "shape": 0}
    zero_r = {"regions": 0, "false": 0, "ok50": 0, "groups": 0, "groups_ok50": 0, "false_ext": 0, "spill": 0}
    read_w = read_r = None
    art = (0, 0)
    if kept is not None:
        changed_read = [not x for x in kept]
        read_w, read_r = words_of(changed_read), regions_of(changed_read)
        art = artefacts_of(changed_read)
        if not failed:
            _same(doc_id, "changed regions", read_r["regions"], res["regions"])
            _same(doc_id, "false-mask regions", read_r["false"], res["false_mask_regions"])
            _same(doc_id, "regions with 50 % or more on gold", read_r["ok50"], res["regions_on_gold_50"])
            _same(doc_id, "words changed outside gold", sum(read_w["fp"].values()) + read_w["boundary_changed"],
                  res["words_changed_outside_gold"])
    if failed:
        row["failed_kind"] = RETENTION if kept is not None else NO_OUTPUT
        if any(it["status"] not in ("missed", "no_ident") for it in res["items"]):
            raise ReadingMismatch(f"{doc_id}: failed document with an item not missed")
    prim_w = zero_w if failed else read_w
    prim_r = zero_r if failed else read_r
    asread_w = read_w if read_w is not None else zero_w
    asread_r = read_r if read_r is not None else zero_r
    changed = [False] * len(a) if failed or kept is None else [not x for x in kept]

    # value-tolerant recall: kept identifying words of items that are not exposed in the value reading
    unit_items: dict[int, list[int]] = {}
    for i in scored_body:
        for k in idts[i]:
            if k in units:
                unit_items.setdefault(k, []).append(i)
    tp = sum(1 for k in gold_units if changed[k])
    tp_value = 0 if failed else sum(1 for k in gold_units if changed[k] or all(
        not res["items"][i]["exposed_value"] for i in unit_items[k]))
    tp_span = sum(1 for k in span_units if changed[k])
    neutral_units = sum(1 for k in nongold if bucket(k) == "neutral_keep")
    body_items = [it for it in res["items"] if it["part"] == "body" and it["status"] != "no_ident"]
    row.update({
        "units": {"body": len(units), "aside": sum(1 for k, t in enumerate(a) if st.has_alnum(t[2]) and aside[k]),
                  "gold": len(gold_units), "span": len(span_units), "outside": len(outside),
                  "nongold": len(nongold), "boundary": len(boundary),
                  "span_not_identifying": len(span_units) - len(gold_units),
                  "unscored_span": len(units) - len(span_units) - len(outside),
                  "nongold_in_keep": sum(1 for k in nongold if k in classes),
                  "nongold_neutral": neutral_units,
                  "shape_no_keep": sum(1 for k in nongold if k not in classes and is_shape(k))},
        "tp": tp, "fn": len(gold_units) - tp, "tp_value": tp_value, "tp_span": tp_span,
        "fn_span": len(span_units) - tp_span,
        "fp": prim_w["fp"], "fp_class": prim_w["fp_class"], "boundary_changed": prim_w["boundary_changed"],
        "fp_shape_no_keep": prim_w["shape"],
        "fp_artefact": 0 if failed else art[0], "artefact_runs": 0 if failed else art[1],
        "asread": {"fp_strict": sum(asread_w["fp"].values()),
                   "fp_scope": sum(asread_w["fp"].values()) - asread_w["fp"]["neutral_keep"],
                   "boundary_changed": asread_w["boundary_changed"]},
        "charged": ({"fp_strict": len(nongold), "fp_scope": len(nongold) - neutral_units} if failed else
                    {"fp_strict": sum(prim_w["fp"].values()),
                     "fp_scope": sum(prim_w["fp"].values()) - prim_w["fp"]["neutral_keep"]}),
        "item": {"scored": len(body_items), "protected": sum(it["status"] == "protected" for it in body_items),
                 "partial": sum(it["status"] == "partial" for it in body_items),
                 "covered_80pct": sum(it["cover"] >= st.COVER_T for it in body_items), **prim_r},
        "item_asread": dict(asread_r),
    })
    return res, row


def flat(row: dict) -> dict:
    """Per-document counts used by the self-test and the bootstrap."""
    fp = row["fp"]
    s = sum(fp.values())
    return {"tp": row["tp"], "fn": row["fn"], "tp_value": row["tp_value"], "tp_span": row["tp_span"],
            "fn_span": row["fn_span"], "fp_strict": s, "fp_scope": s - fp["neutral_keep"],
            "fp_keep_only": fp["must_stay_clear"] + fp["other_keep"], "fp_artefact": row["fp_artefact"],
            "boundary_changed": row["boundary_changed"], "fp_asread": row["asread"]["fp_strict"],
            "fp_charged": row["charged"]["fp_strict"], "fp_charged_scope": row["charged"]["fp_scope"],
            "failed_kind": row["failed_kind"], "nongold": row["units"]["nongold"],
            "boundary": row["units"]["boundary"], "words_body": row["units"]["body"],
            "words_aside": row["units"]["aside"], "fp_where": dict(fp), "fp_class": row["fp_class"]}


# ---------------------------------------------------------------------------------------------- set level
def _r(x):
    return None if x is None else round(x, 6)


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * tp / (2 * tp + fp + fn) if tp + fn else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": _r(p), "recall": _r(r), "f1": _r(f)}


def harmonic(p, r):
    if r is None:
        return None
    if r == 0 or p == 0:
        return 0.0
    if p is None:
        return None
    return 2 * p * r / (p + r)


COUNT_KEYS = ("tp", "fn", "tp_value", "tp_span", "fn_span", "fps", "fpa", "fps_at", "fpa_at", "scored", "protected",
              "groups", "groups_ok50", "false_ext")
STATS = ("word_strict_precision", "word_strict_recall", "word_strict_f1", "word_scope_precision", "word_scope_f1",
         "word_strict_at_f1", "word_scope_at_f1", "word_value_recall", "word_value_f1", "span_recall", "span_f1",
         "item_recall", "item_precision", "item_f1")


def _counts(row: dict) -> list[int]:
    f = flat(row)
    it = row["item"]
    return [f["tp"], f["fn"], f["tp_value"], f["tp_span"], f["fn_span"], f["fp_strict"], f["fp_scope"],
            f["fp_strict"] - f["fp_artefact"], f["fp_scope"] - f["fp_artefact"], it["scored"], it["protected"],
            it["groups"], it["groups_ok50"], it["false_ext"]]


def _stats(c: list[int]) -> list:
    tp, fn, tpv, tps, fns, fps, fpa, fps_at, fpa_at, scored, prot, groups, gok, fext = c
    s, a = prf(tp, fps, fn), prf(tp, fpa, fn)
    ir = prot / scored if scored else None
    ip = gok / (groups + fext) if groups + fext else None
    return [s["precision"], s["recall"], s["f1"], a["precision"], a["f1"], prf(tp, fps_at, fn)["f1"],
            prf(tp, fpa_at, fn)["f1"], prf(tpv, fps, tp + fn - tpv)["recall"], prf(tpv, fps, tp + fn - tpv)["f1"],
            prf(tps, fps, fns)["recall"], prf(tps, fps, fns)["f1"], _r(ir), _r(ip), _r(harmonic(ip, ir))]


def _percentiles(units: list[list[int]]) -> tuple[dict, dict]:
    """Percentile bootstrap: units in the given order, n draws rng.randrange(n) per resample, 2,000 resamples."""
    rng = random.Random(SEED)
    n = len(units)
    vals: list[list[float]] = [[] for _ in STATS]
    for _ in range(RESAMPLES):
        tot = [0] * len(COUNT_KEYS)
        for _ in range(n):
            u = units[rng.randrange(n)]
            for j, x in enumerate(u):
                tot[j] += x
        for j, x in enumerate(_stats(tot)):
            if x is not None:
                vals[j].append(x)
    ci, defined = {}, {}
    for name, v in zip(STATS, vals):
        v.sort()
        ci[name] = [v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1]] if v else None
        defined[name] = len(v)
    return ci, defined


def intervals(rows: list[dict]) -> dict:
    """95 % intervals. Unit = cluster; under MIN_UNITS units: not estimable, per-unit minimum and maximum."""
    rows = sorted(rows, key=lambda r: r["doc_id"])
    by: dict[str, list[int]] = {}
    for r in rows:
        c = _counts(r)
        acc = by.setdefault(r["cluster"], [0] * len(COUNT_KEYS))
        for j, x in enumerate(c):
            acc[j] += x
    keys = sorted(by)
    out = {"resamples": RESAMPLES, "seed": SEED, "method": "percentile", "documents": len(rows), "units": len(keys),
           "unit": "document" if len(keys) == len(rows) else "cluster (top folder of the doc_id)",
           "min_units": MIN_UNITS}
    if not rows:
        out.update(estimable=False, ci=None)
        return out
    units = [by[k] for k in keys]
    if len(keys) >= MIN_UNITS:
        out["estimable"] = True
        out["ci"], out["defined_resamples"] = _percentiles(units)
    else:
        out["estimable"] = False
        out["ci"] = None
        per = [_stats(u) for u in units]
        out["unit_min_max"] = {name: ([min(v), max(v)] if v else None) for j, name in enumerate(STATS)
                               for v in [[p[j] for p in per if p[j] is not None]]}
    if len(keys) < len(rows) and len(rows) >= MIN_UNITS:
        ci, defined = _percentiles([_counts(r) for r in rows])
        out["document_bootstrap"] = {"note": "documents resampled, clustering ignored: understates the uncertainty",
                                     "ci": ci, "defined_resamples": defined}
    return out


def summarize(rows: list[dict], text_docs: list[dict], set_id: str) -> dict:
    inc = [r for r in rows if r["status"] not in st.EXCLUDED]
    fl = [flat(r) for r in inc]
    T = Counter()
    for f in fl:
        for k in ("tp", "fn", "tp_value", "tp_span", "fn_span", "fp_strict", "fp_scope", "fp_keep_only",
                  "fp_artefact", "boundary_changed", "fp_asread", "fp_charged", "fp_charged_scope"):
            T[k] += f[k]
    U = Counter()
    for r in inc:
        U.update(r["units"])
    where, by_class, by_format = Counter(), Counter(), Counter()
    for r in inc:
        where.update(r["fp"])
        by_class.update(r["fp_class"])
        by_format[r["format"]] += sum(r["fp"].values())
    asread_scope = sum(r["asread"]["fp_scope"] for r in inc)
    failed = [r for r in inc if r["status"] == "failed"]
    agg = st.aggregate(text_docs)
    p, rg = agg["protection"], agg["regions"]
    scored = p["scored"]
    I = Counter()
    IA = Counter()
    for r in inc:
        I.update(r["item"])
        IA.update(r["item_asread"])
    for key, mine in (("scored", I["scored"]), ("protected", I["protected"]), ("partial", I["partial"]),
                      ("covered_80pct", I["covered_80pct"])):
        _same("set", f"item {key}", mine, p[key])
    _same("set", "changed regions", I["regions"], rg["changed_regions"])
    _same("set", "false-mask regions", I["false"], rg["false_mask_regions"])
    _same("set", "regions with 50 % or more on gold", I["ok50"], rg["regions_on_gold_50pct"])
    _same("set", "words changed outside gold", T["fp_strict"] + T["boundary_changed"],
          agg["words"]["changed_outside_gold"])
    retention_failed = [r for r in failed if r["failed_kind"] == RETENTION]
    tp, fn = T["tp"], T["fn"]
    have_keep = U["nongold_in_keep"] > 0

    def item(name, found, p_hit, p_all, rule_r, rule_p):
        rec_ = found / scored if scored else None
        pre = p_hit / p_all if p_all else None
        return {"name": name, "recall": _r(rec_), "recall_counts": [found, scored], "recall_rule": rule_r,
                "precision": _r(pre), "precision_counts": [p_hit, p_all], "precision_rule": rule_p,
                "f1": _r(harmonic(pre, rec_))}

    merged_rule = ("groups of changed regions merged by gold item with 50 % or more of their characters on gold "
                   "(boundary words count as gold) / (groups + regions touching no gold)")
    # as read: documents that did not fail, plus the regions of retention-failed documents
    ga, ga_ok, gf = IA["groups"], IA["groups_ok50"], IA["false_ext"]
    sizes = sorted((r["units"]["gold"] + r["units"]["nongold"] for r in inc), reverse=True)
    total = sum(sizes)
    out = {
        "f1_version": F1_VERSION, "scorer": st.SCORER_VERSION,
        "set": set_id,
        "neutral_keep_classes": list(NEUTRAL_KEEP),
        "neutral_classes_in_gold": sorted({k["class"] for d in text_docs for k in d.get("keep", [])
                                           if k["class"] in NEUTRAL_KEEP}),
        "set_has_keep_items": have_keep,
        "documents": len(inc),
        "documents_failed": len(failed),
        "documents_failed_by_kind": {k: sum(1 for r in failed if r["failed_kind"] == k) for k in (NO_OUTPUT, RETENTION)},
        "failed_documents": [{"doc_id": r["doc_id"], "kind": r["failed_kind"], "reason": r["reason"]} for r in failed],
        "documents_excluded": [{"doc_id": r["doc_id"], "status": r["status"], "reason": r["reason"]}
                               for r in rows if r["status"] in st.EXCLUDED],
        "units": dict(U),
        "concentration": {"largest_document_share": _r(sizes[0] / total) if total else None,
                          "three_largest_share": _r(sum(sizes[:3]) / total) if total else None},
        "word": {
            "strict": prf(tp, T["fp_strict"], fn),
            "scope_adjusted": prf(tp, T["fp_scope"], fn),
            "strict_artefact_tolerant": prf(tp, T["fp_strict"] - T["fp_artefact"], fn),
            "scope_adjusted_artefact_tolerant": prf(tp, T["fp_scope"] - T["fp_artefact"], fn),
            "keep_only": prf(tp, T["fp_keep_only"], fn) if have_keep else None,
            "value_tolerant": prf(T["tp_value"], T["fp_strict"], tp + fn - T["tp_value"]),
            "value_tolerant_scope_adjusted": prf(T["tp_value"], T["fp_scope"], tp + fn - T["tp_value"]),
        },
        "word_sensitivity": {
            "boundary_words_counted": prf(tp, T["fp_strict"] + T["boundary_changed"], fn),
            "failures_as_read": prf(tp, T["fp_asread"], fn),
            "failures_as_read_scope_adjusted": prf(tp, asread_scope, fn),
            "failures_charged": prf(tp, T["fp_charged"], fn),
            "failures_charged_scope_adjusted": prf(tp, T["fp_charged_scope"], fn),
            "scope_adjusted_shape_extended": prf(tp, T["fp_scope"] - sum(r["fp_shape_no_keep"] for r in inc), fn),
            "span_words": prf(T["tp_span"], T["fp_strict"], T["fn_span"]),
            "span_words_scope_adjusted": prf(T["tp_span"], T["fp_scope"], T["fn_span"]),
        },
        "word_counts": {"boundary_words_changed": T["boundary_changed"], "artefact_words_forgiven": T["fp_artefact"],
                        "artefact_runs_forgiven": sum(r["artefact_runs"] for r in inc),
                        "value_words_forgiven": T["tp_value"] - tp,
                        "shape_words_changed_no_keep": sum(r["fp_shape_no_keep"] for r in inc)},
        "intervals": intervals(inc),
        "fp_where": {b_: where.get(b_, 0) for b_ in FP_BUCKETS},
        "fp_in_keep_class": dict(sorted(by_class.items())),
        "fp_by_input_format": dict(sorted(by_format.items())),
        "failed_documents_counts": {"gold_units_fn": sum(r["fn"] for r in failed),
                                    "nongold_units": sum(r["units"]["nongold"] for r in failed),
                                    "words_changed_as_read_retention": sum(r["asread"]["fp_strict"]
                                                                           for r in retention_failed)},
        "item": {
            "strict": item("strict (regions merged by gold item)", p["protected"], I["groups_ok50"],
                           I["groups"] + I["false_ext"], "protected / scored gold items", merged_rule),
            "overlap_recall": item("overlap (lenient recall, strict precision)", p["protected"] + p["partial"],
                                   I["groups_ok50"], I["groups"] + I["false_ext"],
                                   "(protected + partial) / scored gold items", merged_rule),
            "fr_pii_bench_rules": item("FR-PII-Bench rules (our re-implementation)", p["covered_80pct"],
                                       rg["regions_on_gold_50pct"], rg["changed_regions"],
                                       "gold items with 80 % or more of their characters in changed regions / scored",
                                       "regions with 50 % or more of their characters on gold / changed regions"),
            "strict_retention_failures_as_read": item("strict, retention failures as read", p["protected"], ga_ok,
                                                      ga + gf, "protected / scored gold items",
                                                      merged_rule + "; regions of retention-failed documents counted"),
            "region_precision": {"counts": [rg["regions_on_gold_50pct"], rg["changed_regions"]],
                                 "precision": _r(rg["regions_on_gold_50pct"] / rg["changed_regions"])
                                 if rg["changed_regions"] else None},
            "spill_over_words": I["spill"],
            "retention_failures": len(retention_failed),
            "counts": {"scored": scored, "protected": p["protected"], "partial": p["partial"],
                       "missed": p["missed"], "exposed": p["exposed"], "covered_80pct": p["covered_80pct"],
                       "changed_regions": rg["changed_regions"], "false_mask_regions": rg["false_mask_regions"],
                       "regions_on_gold_50pct": rg["regions_on_gold_50pct"], "groups": I["groups"],
                       "groups_ok50": I["groups_ok50"], "regions_touching_no_gold": I["false_ext"]},
        },
        "score_text_summary": {"documents": agg["documents"], "documents_failed": agg["documents_failed"],
                               "exposed": p["exposed"], "exposed_value": p["exposed_value"], "scored": scored,
                               "must_stay_clear_altered": agg["must_stay_clear"]["altered"],
                               "must_stay_clear_n": agg["must_stay_clear"]["n"],
                               "words_outside_gold": agg["words"]["outside_gold"],
                               "words_changed_outside_gold": agg["words"]["changed_outside_gold"]},
    }
    return out


# ---------------------------------------------------------------------------------------------- report
def _num(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def _share(k: int, n: int) -> str:
    return "n/a" if not n else f"{100 * k / n:.1f} % ({k:,} of {n:,})"


def markdown(s: dict, title: str) -> str:
    """Short report: the overall score with its precision and recall, and the legal terms changed."""
    w, fk, tx = s["word"]["strict"], s["documents_failed_by_kind"], s["score_text_summary"]
    md = [f"# {title}", "",
          "| Measure | Value |", "|---|---:|",
          f"| Overall score (F1) | **{_num(w['f1'])}** |",
          f"| Precision (P) | {_num(w['precision'])} |",
          f"| Recall (R) | {_num(w['recall'])} |",
          f"| Legal terms changed | {_share(tx['must_stay_clear_altered'], tx['must_stay_clear_n'])} |",
          "",
          f"Word by word: {w['tp']:,} masked correctly, {w['fp']:,} masked by mistake, {w['fn']:,} left readable.",
          f"Documents: {s['documents']}"
          + (f" (failed {s['documents_failed']}: {NO_OUTPUT} {fk[NO_OUTPUT]}, {RETENTION} {fk[RETENTION]}; left out as "
             f"not run or unscorable {len(s['documents_excluded'])})"
             if s["documents_failed"] or s["documents_excluded"] else "")
          + (f"; limited to a list of {s['docs_restricted']['documents']} documents" if s.get("docs_restricted") else "")
          + f". Personal data items: {tx['scored']:,}.",
          f"Scorer {s['f1_version']} with {s['scorer']}. The JSON result holds the other readings of the same counts."]
    return "\n".join(md) + "\n"


# ---------------------------------------------------------------------------------------------- I/O
def _sha_file(p) -> str | None:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if p else None


def _set_of(gold: list[dict], wanted: str | None) -> str:
    sets = {r.get("set") for r in gold}
    if len(sets) != 1:
        raise SystemExit(f"the gold holds several sets: {sorted(map(str, sets))}")
    got = sets.pop()
    if wanted and wanted != got:
        raise SystemExit(f"--set {wanted} but the gold is set {got}")
    return got


def _read_docs_list(path) -> list[str] | None:
    if not path:
        return None
    return [x for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def _score_text_check(args, docs: list[dict], restricted: bool, reader_check) -> None:
    """Every document result must equal the ``score_text.py`` result of the same run, else no score is given."""
    ref = json.loads(Path(args.score_text_json).read_text(encoding="utf-8"))
    fdocs = {d["doc_id"]: d for d in ref.get("documents", [])}
    if not fdocs:
        raise ReadingMismatch(f"{args.score_text_json} has no per-document results")
    for d in docs:
        f = fdocs.get(d["doc_id"])
        if f is None:
            raise ReadingMismatch(f"{d['doc_id']}: not in {args.score_text_json}")
        if json.loads(json.dumps(d, ensure_ascii=False)) != f:
            raise ReadingMismatch(f"{d['doc_id']}: document result differs from {args.score_text_json}")
    if not restricted:
        if set(fdocs) != {d["doc_id"] for d in docs}:
            raise ReadingMismatch(f"the documents differ from {args.score_text_json}")
        mine = st.aggregate(docs)
        for key in ("documents", "documents_failed", "protection", "regions", "must_stay_clear", "words"):
            if mine[key] != ref["summary"][key]:
                raise ReadingMismatch(f"summary differs from {args.score_text_json} on {key!r}")
    if reader_check is not None:
        if reader_check:
            raise SystemExit(f"reader libraries differ from the pinned versions: {reader_check}")
        if "reader_version_check" in ref["summary"] and ref["summary"]["reader_version_check"] != reader_check:
            raise SystemExit("reader version check differs from the score_text.py result")


def write_results(args, rows: list[dict], text_docs: list[dict], set_id: str, provenance: dict,
                  restricted: dict | None) -> dict:
    summary = summarize(rows, text_docs, set_id)
    summary.update(tool=args.tool, gold=str(args.gold), score_text_json=str(args.score_text_json),
                   provenance=provenance)
    if restricted:
        summary["docs_restricted"] = restricted
    out = {"summary": summary, "per_document": rows}
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    md = markdown(summary, f"{args.tool} on {set_id}" if args.tool else f"Scores on {set_id}")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(md, encoding="utf-8")
    print(md)
    return summary


def _provenance(args, extra: dict) -> dict:
    return {"score_f1_sha256": _sha_file(Path(__file__)), "score_text_sha256": _sha_file(HERE / "score_text.py"),
            "extract_text_sha256": _sha_file(HERE / "extract_text.py"), "argv": sys.argv[1:],
            "python": sys.version.split()[0], "gold_sha256": _sha_file(args.gold),
            "score_text_json_sha256": _sha_file(args.score_text_json),
            "docs_sha256": _sha_file(getattr(args, "docs", None)),
            "utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **extra}


def cmd_score(args) -> int:
    """Documents, outputs and statuses are read as ``score_text.cmd_score`` reads them."""
    from extract_text import check_versions, extract  # noqa: PLC0415

    gold = st.load_jsonl(args.gold)
    set_id = _set_of(gold, args.set)
    only = _read_docs_list(args.docs)
    if only is not None:
        missing = set(only) - {r["doc_id"] for r in gold}
        if missing:
            raise SystemExit(f"--docs names documents not in the gold: {sorted(missing)[:5]}")
        gold = [r for r in gold if r["doc_id"] in set(only)]
    runlog = {r["doc_id"]: r for r in st.load_jsonl(args.runlog)} if args.runlog else {}
    manifest = ({r["doc_id"]: r.get("output") for r in st.load_jsonl(args.outputs_manifest)}
                if args.outputs_manifest else {})
    rows, docs, digest = [], [], []
    for rec in gold:
        if "text" in rec:
            in_text, in_meta = rec["text"], {}
        else:
            in_text, in_meta = extract(Path(args.inputs) / rec["file"])
        if rec.get("text_sha256") and st.sha256_text(in_text) != rec["text_sha256"]:
            raise SystemExit(f"{rec['doc_id']}: input text hash differs from the answer key")
        log = runlog.get(rec["doc_id"]) or runlog.get(rec.get("file", "")) or {}
        status, reason = log.get("status", "ok"), log.get("reason", "")
        out_text = None
        if status == "ok":
            if args.outputs_manifest:
                outp = Path(manifest[rec["doc_id"]]) if manifest.get(rec["doc_id"]) else None
            else:
                outp = st.find_output(Path(args.outputs), rec["file"])
            if outp is None or not outp.exists():
                status, reason = "failed", "no output file"
            else:
                digest.append(f"{rec['doc_id']}\t{_sha_file(outp)}")
                try:
                    out_text, out_meta = extract(outp)
                    if out_meta.get("image_only"):
                        status, reason, out_text = "unscorable", "output PDF has images and no text layer", None
                except Exception as e:  # noqa: BLE001
                    status, reason = "failed", f"output unreadable: {type(e).__name__}: {e}"
        res, row = read_doc(rec, in_text, out_text, status, reason, hidden=in_meta.get("hidden_ranges"))
        docs.append(res)
        rows.append(row)
    reader = check_versions()
    _score_text_check(args, docs, only is not None, reader)
    prov = _provenance(args, {"runlog_sha256": _sha_file(args.runlog),
                              "manifest_sha256": _sha_file(args.outputs_manifest),
                              "outputs_read": len(digest),
                              "outputs_digest": hashlib.sha256("\n".join(sorted(digest)).encode()).hexdigest(),
                              "reader_version_check": reader})
    write_results(args, rows, docs, set_id, prov,
                  {"documents": len(gold), "docs_file": str(args.docs)} if only is not None else None)
    return 0


def cmd_pairs(args) -> int:
    """As ``score_text.cmd_pairs``: {"doc_id", "output_text", optional "input_text", "status", "reason",
    "hidden_ranges"}; a gold document with no pair is failed."""
    gold = {r["doc_id"]: r for r in st.load_jsonl(args.gold)}
    set_id = _set_of(list(gold.values()), args.set)
    rows, docs = [], []
    for p in st.load_jsonl(args.pairs):
        rec = gold[p["doc_id"]]
        res, row = read_doc(rec, p.get("input_text", rec.get("text")), p.get("output_text"), p.get("status", "ok"),
                            p.get("reason", ""), hidden=p.get("hidden_ranges"))
        docs.append(res)
        rows.append(row)
    for m in sorted(set(gold) - {r["doc_id"] for r in rows}):
        res, row = read_doc(gold[m], gold[m]["text"], None, "failed", "no output")
        docs.append(res)
        rows.append(row)
    _score_text_check(args, docs, False, None)
    prov = _provenance(args, {"pairs_sha256": _sha_file(args.pairs), "outputs_read": len(rows),
                              "outputs_digest": _sha_file(args.pairs)})
    write_results(args, rows, docs, set_id, prov, None)
    return 0


def cmd_common(args) -> int:
    """Documents included (not ``not_run``, not ``unscorable``) in every given result. Give the list to ``--docs``
    to score several tools on the same documents."""
    sets, common = set(), None
    for jf in args.results:
        d = json.loads(Path(jf).read_text(encoding="utf-8"))
        sets.add(d["summary"]["set"])
        inc = {r["doc_id"] for r in d["per_document"] if r["status"] not in st.EXCLUDED}
        common = inc if common is None else common & inc
    if len(sets) != 1:
        raise SystemExit(f"results of several sets: {sorted(sets)}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(f"{x}\n" for x in sorted(common or ())), encoding="utf-8")
    print(f"{sets.pop()}: {len(common or ())} documents in every one of {len(args.results)} results")
    return 0


# ---------------------------------------------------------------------------------------------- self-test
# Invented text only. Expected numbers were written by hand from the definitions; the one exception is the pinned
# bootstrap interval (it guards the draw rule).
T1 = ("Le salarié M. Jean Dupont, domicilié 12 rue des Lilas à Nantes, employé par Valmont SARL, a saisi le tribunal "
      "judiciaire de Lyon le 3 mars 2021 pour 1 500 euros.\n")
T1_GOLD = [("PERSON", "Jean Dupont"), ("ADDRESS", "12 rue des Lilas à Nantes"), ("ORG", "Valmont SARL")]
T1_KEEP = [("court", "tribunal judiciaire de Lyon"), ("date", "3 mars 2021"), ("amount", "1 500 euros")]
T2 = "Contrat de M. Paul Martin signé à Lille.\n"
T3 = ("title: Note pour M. Paul Roux à Lille\n"
      "Le dossier de M. Paul Roux est suivi au tribunal judiciaire de Lille.\n")
T4 = "Le gérant M. Paul Morel dirige la société Varenne depuis Lyon.\n"
T5 = "Le salarié Jean Dupont, domicilié à Nantes, a saisi le juge au cœur du litige.\n"
T6 = "Adresses : 12 rue des Lilas à Nantes ; 7 rue des Pins à Brest. Signé le 3 mars 2021.\n"
T7 = "Please send the report to Anna Kim at Brightwater Labs today.\n"
T8 = "Le Cabinet Morel défend Paul Roy.\n"
T9 = "Vu la loi du 3 mars 2021, Paul Roy a signé.\n"
T10 = "Le contrat lie Paul Roy et Anne Vidal.\n"
T11 = "Il vit au 4 rue des Lilas.\n"


def _rec(src, gold, keep=(), file="", doc_id="t"):
    r = st._probe(src, gold, keep, file=file)
    r["doc_id"] = doc_id
    return r


def _sub(src, *pairs):
    for x, y in pairs:
        src = src.replace(x, y)
    return src


CODES = (("Jean Dupont", "PERSONNE_A"), ("12 rue des Lilas à Nantes", "ADRESSE_A"), ("Valmont SARL", "SOCIETE_A"))
T1_CODES = _sub(T1, *CODES)
T5_CODES = T5.replace("Jean Dupont", "PERSONNE_A")


def selftest_cases() -> list[dict]:
    r1 = _rec(T1, T1_GOLD, T1_KEEP)
    r2 = _rec(T2, [("PERSON", "Paul Martin")])
    r3 = _rec(T3, [("PERSON", "Paul Roux"), ("PERSON", "Paul Roux", 1)],
              [("court_city", "Lille"), ("court", "tribunal judiciaire de Lille")], file="x.docx")
    r4_out = _rec(T4, [("PERSON", "Paul Morel"), ("ORG", "Varenne")])
    r4_in = _rec(T4, [("PERSON", "M. Paul Morel"), ("ORG", "la société Varenne")])
    r5x = _rec(T5, [("PERSON", "Jean Dupont")], file="x.docx")
    r5p = _rec(T5, [("PERSON", "Jean Dupont")], file="x.pdf")
    r6 = _rec(T6, [("ADDRESS", "12 rue des Lilas à Nantes"), ("ADDRESS", "7 rue des Pins à Brest")])
    r7 = _rec(T7, [("NAME_GIVEN", "Anna Kim")])
    r8 = _rec(T8, [("ORG", "Cabinet Morel"), ("PERSON", "Morel"), ("PERSON", "Paul Roy"), ("NAME", "Paul Roy")])
    r9 = _rec(T9, [("PERSON", "Paul Roy")], [("law", "loi du 3 mars 2021"), ("date", "3 mars 2021")])
    r10 = _rec(T10, [("PERSON", "Paul Roy"), ("PERSON", "Anne Vidal")], file="x.docx")
    body3 = T3.split("\n", 1)[1]
    C = []

    def add(name, rec, src, out, want, item=None, **kw):
        C.append({"name": name, "rec": rec, "src": src, "out": out, "kw": kw, "want": want, "item": item})

    # want: per-document counts (flat). item: (R, P, F1) of the strict, the overlap-recall and the FR-PII-Bench-rules
    # readings, in that order.
    add("perfect masker (codes)", r1, T1, T1_CODES,
        dict(tp=6, fn=0, fp_strict=0, fp_scope=0, tp_span=10, fn_span=0, words_body=31, nongold=20, boundary=1,
             boundary_changed=0), (1, 1, 1) * 3)
    add("perfect masker (deletion)", r1, T1, _sub(T1, *((x, "") for x, _ in CODES)),
        dict(tp=6, fn=0, fp_strict=0, fp_scope=0, tp_span=10, fn_span=0), (1, 1, 1) * 3)
    add("no-op tool (output = input)", r1, T1, T1,
        dict(tp=0, fn=6, fp_strict=0, fp_scope=0, tp_span=0, fn_span=10), (0, None, 0) * 3)
    add("mask everything, 6 words outside gold (under 20: the retention rule does not apply)", r2, T2,
        "[CONFIDENTIEL]\n", dict(tp=2, fn=0, fp_strict=5, fp_scope=5, boundary_changed=1, tp_span=2, fn_span=0,
                                 failed_kind=None, nongold=5, boundary=1), (1, 0, 0) * 3)
    add("mask everything, 21 words outside gold (retention 0: failed)", r1, T1, "[CONFIDENTIEL]\n",
        dict(tp=0, fn=6, fp_strict=0, fp_scope=0, tp_span=0, fn_span=10, failed_kind=RETENTION, fp_asread=20,
             fp_charged=20, fp_charged_scope=14), (0, None, 0) * 3)
    add("realistic substitutes of other lengths", r1, T1,
        _sub(T1, ("Jean Dupont", "Marie-Christine Lefebvre-Durand"), ("12 rue des Lilas à Nantes", "48 avenue Foch à Rennes"),
             ("Valmont SARL", "Brévine SAS")),
        dict(tp=6, fn=0, fp_strict=0, fp_scope=0, tp_span=9, fn_span=1), (1, 1, 1) * 3)
    add("placeholder codes and tags, legal form kept, one word over-masked", r1, T1,
        _sub(T1, ("salarié", "[METIER]"), ("Jean Dupont", "[PERSONNE_1]"), ("12 rue des Lilas à Nantes", "<ADRESSE>"),
             ("Valmont SARL", "[SOCIETE_1] SARL")),
        dict(tp=6, fn=0, fp_strict=1, fp_scope=1, tp_span=9, fn_span=1,
             fp_where={"must_stay_clear": 0, "other_keep": 0, "neutral_keep": 0, "no_keep_item": 1}),
        (1, 0.75, 6 / 7, 1, 0.75, 6 / 7, 2 / 3, 0.75, 12 / 17))
    add("date-only masker", r1, T1, _sub(T1, ("3 mars 2021", "[DATE]")),
        dict(tp=0, fn=6, fp_strict=3, fp_scope=0, fp_keep_only=0, tp_span=0, fn_span=10, fp_class={"date": 3}),
        (0, 0, 0) * 3)
    add("gold, dates and amounts masked", r1, T1, _sub(T1, *CODES, ("3 mars 2021", "[DATE]"), ("1 500 euros", "[MONTANT]")),
        dict(tp=6, fn=0, fp_strict=6, fp_scope=0, fp_keep_only=0, tp_span=10, fn_span=0), (1, 0.6, 0.75) * 3)
    add("court name changed (must stay clear: FP in both readings)", r1, T1,
        _sub(T1, *CODES, ("judiciaire de Lyon", "judiciaire de VILLE_A")),
        dict(tp=6, fn=0, fp_strict=1, fp_scope=1, fp_keep_only=1, tp_span=10, fn_span=0, fp_class={"court": 1}),
        (1, 0.75, 6 / 7) * 3)
    add("one name masked, one word over-masked", r1, T1, _sub(T1, ("salarié", "[METIER]"), ("Jean Dupont", "PERSONNE_A")),
        dict(tp=2, fn=4, fp_strict=1, fp_scope=1, tp_span=2, fn_span=8), (1 / 3, 0.5, 0.4) * 3)
    add("first name kept (partial; value reading: not exposed)", r1, T1,
        _sub(T1, ("Jean Dupont", "Jean PERSONNE_A"), *CODES[1:]),
        dict(tp=5, fn=1, tp_value=6, fp_strict=0, fp_scope=0, tp_span=9, fn_span=1),
        (2 / 3, 1, 0.8, 1, 1, 1, 2 / 3, 1, 0.8))
    add("name split by a re-rendered file, not masked (rejoined: kept)", r1, T1,
        _sub(T1, ("Jean Dupont", "Jean Du pont"), *CODES[1:]),
        dict(tp=4, fn=2, tp_value=4, fp_strict=0, fp_scope=0, tp_span=8, fn_span=2), (2 / 3, 1, 0.8) * 3)
    add("realistic fakes equal by chance (value-tolerant recall)", r1, T1,
        _sub(T1, ("Jean Dupont", "Jean Martin"), ("12 rue des Lilas à Nantes", "12 avenue Foch à Rennes"),
             ("Valmont SARL", "Brévine SAS")),
        dict(tp=4, fn=2, tp_value=6, fp_strict=0), (1 / 3, 1, 0.5, 1, 1, 1, 1 / 3, 1, 0.5))
    add("failed document (run log failed, no output)", r1, T1, None,
        dict(tp=0, fn=6, fp_strict=0, fp_scope=0, tp_span=0, fn_span=10, failed_kind=NO_OUTPUT, fp_asread=0,
             fp_charged=20, fp_charged_scope=14), (0, None, 0) * 3, status="failed", reason="tool error")
    add("failed document, empty output file", r1, T1, "",
        dict(tp=0, fn=6, fp_strict=0, failed_kind=RETENTION, fp_asread=20, fp_charged=20), (0, None, 0) * 3)
    add("failed document, error text as output", r1, T1, "Error: service unavailable\n",
        dict(tp=0, fn=6, fp_strict=0, failed_kind=RETENTION, fp_asread=20, fp_charged=20), (0, None, 0) * 3)
    add("failed document, output cut after the company (retention 0.286)", r1, T1,
        T1_CODES.split(" a saisi")[0] + "\n",
        dict(tp=0, fn=6, fp_strict=0, failed_kind=RETENTION, fp_asread=15, fp_charged=20), (0, None, 0) * 3)
    add("document property item, output without properties", r3, T3, body3.replace("Paul Roux", "PERSONNE_A"),
        dict(tp=2, fn=0, fp_strict=0, fp_scope=0, tp_span=2, fn_span=0, words_body=13, words_aside=8, nongold=10,
             boundary=1), (1, 1, 1) * 3)
    add("document property item, properties kept with the name in clear", r3, T3,
        T3.split("\n", 1)[0] + "\n" + body3.replace("Paul Roux", "PERSONNE_A"),
        dict(tp=2, fn=0, fp_strict=0, fp_scope=0, tp_span=2, fn_span=0, words_body=13, words_aside=8),
        (1, 1, 1) * 3)
    # boundary words: the same outputs under the two gold conventions give the same word and item numbers
    for conv, rec in (("title and legal form outside the spans", r4_out), ("inside the spans", r4_in)):
        out_bc = 0 if rec is r4_in else None
        add(f"boundary, {conv}: codes keep the title and the legal form", rec, T4,
            T4.replace("Paul Morel", "PERSONNE_A").replace("Varenne", "SOCIETE_A"),
            dict(tp=3, fn=0, fp_strict=0, nongold=5, boundary_changed=0),
            (1, 1, 1, 1, 1, 1, 1, 1, 1) if rec is r4_out else (1, 1, 1, 1, 1, 1, 0, 1, 0))
        add(f"boundary, {conv}: one tag over title and name, one over article, legal form and name", rec, T4,
            T4.replace("M. Paul Morel", "<PERSON>").replace("la société Varenne", "<ORG>"),
            dict(tp=3, fn=0, fp_strict=0, nongold=5, boundary_changed=3 if out_bc is None else 0), None)
        add(f"boundary, {conv}: realistic fake with a gender change", rec, T4,
            T4.replace("M. Paul Morel", "Mme Claire Roy").replace("Varenne", "Bertin"),
            dict(tp=3, fn=0, fp_strict=0, nongold=5, boundary_changed=1 if out_bc is None else 0), None)
    # re-rendered files: words split, glued, hyphenated or written without a ligature are artefacts
    add("re-rendered .docx: a split word and a soft hyphen (artefact-tolerant FP 0)", r5x, T5,
        T5_CODES.replace("salarié", "sa larié").replace("domicilié", "domi­cilié"),
        dict(tp=2, fn=0, fp_strict=2, fp_artefact=2), None)
    add("re-rendered .pdf: line-end hyphen, glued words, ligature (artefact-tolerant FP 0)", r5p, T5,
        T5_CODES.replace("domicilié", "domi-\ncilié").replace("a saisi", "asaisi").replace("cœur", "coeur"),
        dict(tp=2, fn=0, fp_strict=4, fp_artefact=4), None)
    add("real over-mask is not an artefact", r5p, T5, T5_CODES.replace("salarié", "[METIER]"),
        dict(tp=2, fn=0, fp_strict=1, fp_artefact=0), None)
    # item precision merged by gold item: fakes that keep words inside a span are not split into several hits
    add("two addresses as codes, date masked", r6, T6,
        _sub(T6, ("12 rue des Lilas à Nantes", "ADRESSE_A"), ("7 rue des Pins à Brest", "ADRESSE_B"), ("3 mars 2021", "DATE_A")),
        dict(tp=6, fn=0, fp_strict=3), (1, 2 / 3, 0.8) * 2 + (1, 2 / 3, 0.8))
    add("two addresses as fakes keeping 'rue des' and 'à', date masked", r6, T6,
        _sub(T6, ("12 rue des Lilas à Nantes", "48 rue des Ormes à Rennes"), ("7 rue des Pins à Brest", "9 rue des Saules à Vannes"),
             ("3 mars 2021", "DATE_A")),
        dict(tp=6, fn=0, fp_strict=3), (1, 2 / 3, 0.8, 1, 2 / 3, 0.8, 0, 6 / 7, 0))
    add("organisation not in the answer key masked: FP", r7, T7,
        T7.replace("Anna Kim", "[NAME]").replace("Brightwater Labs", "[ORG]"),
        dict(tp=2, fn=0, fp_strict=2, nongold=9), None)
    add("overlapping gold items: each word counts once", r8, T8, "Le SOCIETE_A défend PERSONNE_A.\n",
        dict(tp=4, fn=0, fp_strict=0, nongold=2, tp_span=4, fn_span=0), (1, 1, 1) * 3)
    add("date inside a law: must stay clear wins", r9, T9, T9.replace("3 mars 2021", "[DATE]").replace("Paul Roy", "PERSONNE_A"),
        dict(tp=2, fn=0, fp_strict=3, fp_scope=3, fp_keep_only=3, fp_class={"date": 3, "law": 3},
             fp_where={"must_stay_clear": 3, "other_keep": 0, "neutral_keep": 0, "no_keep_item": 0}), None)
    add("tracked deletion: its words are not units", r10, T10, "Le contrat lie PERSONNE_A.\n",
        dict(tp=2, fn=0, fp_strict=0, words_body=5, words_aside=3, nongold=3), (1, 1, 1) * 3,
        hidden=[[T10.index(" et Anne"), T10.index("Vidal") + 5]])
    return C


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL", name, info)

    def close(x, y):
        return (x is None and y is None) or (x is not None and y is not None and abs(x - y) < 1e-6)

    cases = selftest_cases()
    for c in cases:
        fr, row = read_doc(c["rec"], c["src"], c["out"], **c["kw"])
        f = flat(row)
        got = {k: f.get(k) for k in c["want"]}
        check(c["name"], got == c["want"], (got, c["want"]))
        s = summarize([row], [fr], "frpii")
        exp = prf(f["tp"], f["fp_strict"], f["fn"])
        check(c["name"] + " [word P R F1]", all(close(s["word"]["strict"][k], exp[k]) for k in ("precision", "recall", "f1")),
              (s["word"]["strict"], exp))
        if c["item"]:
            it = s["item"]
            got_i = tuple(it[k][m] for k in ("strict", "overlap_recall", "fr_pii_bench_rules")
                          for m in ("recall", "precision", "f1"))
            check(c["name"] + " [item]", all(close(x, y) for x, y in zip(got_i, c["item"])), (got_i, c["item"]))

    by = {c["name"]: c for c in cases}

    def one(name, doc_id=None):
        c = by[name]
        rec = dict(c["rec"], doc_id=doc_id or c["rec"]["doc_id"])
        return read_doc(rec, c["src"], c["out"], **c["kw"])

    def set_of(*pairs, set_id="frpii"):
        frs, rows = [], []
        for name, did in pairs:
            fr, row = one(name, did)
            frs.append(fr)
            rows.append(row)
        return summarize(rows, frs, set_id), rows, frs

    s, _, _ = set_of(("mask everything, 6 words outside gold (under 20: the retention rule does not apply)", None))
    w = s["word"]["strict"]
    check("mask everything (short): P 2/7 R 1 F1 4/9; boundary words counted P 0.25 F1 0.4",
          (w["precision"], w["recall"], w["f1"]) == (0.285714, 1.0, 0.444444)
          and (s["word_sensitivity"]["boundary_words_counted"]["precision"],
               s["word_sensitivity"]["boundary_words_counted"]["f1"])
          == (0.25, 0.4), s["word"])
    s, _, _ = set_of(("date-only masker", None))
    check("date-only: strict P 0, scope P n/a, F1 0 both; keep-only P n/a",
          (s["word"]["strict"]["precision"], s["word"]["scope_adjusted"]["precision"], s["word"]["strict"]["f1"],
           s["word"]["scope_adjusted"]["f1"], s["word"]["keep_only"]["precision"]) == (0.0, None, 0.0, 0.0, None),
          s["word"])
    s, _, _ = set_of(("gold, dates and amounts masked", None))
    check("gold+dates+amounts: strict P 0.5 F1 0.666667; scope P 1 F1 1; shape-extended P 1",
          (s["word"]["strict"]["precision"], s["word"]["strict"]["f1"], s["word"]["scope_adjusted"]["precision"],
           s["word"]["scope_adjusted"]["f1"], s["word_sensitivity"]["scope_adjusted_shape_extended"]["precision"])
          == (0.5, 0.666667, 1.0, 1.0, 1.0), s["word"])
    s, _, _ = set_of(("no-op tool (output = input)", None))
    check("no-op: P n/a, R 0, F1 0", (s["word"]["strict"]["precision"], s["word"]["strict"]["recall"],
                                     s["word"]["strict"]["f1"]) == (None, 0.0, 0.0), s["word"])
    check("F1 n/a when there is no gold unit", prf(0, 3, 0)["f1"] is None and prf(0, 0, 0)["f1"] is None)
    # boundary words: the same P, R and F1 under both gold conventions
    for out_name in ("codes keep the title and the legal form",
                     "one tag over title and name, one over article, legal form and name",
                     "realistic fake with a gender change"):
        a_, _, _ = set_of((f"boundary, title and legal form outside the spans: {out_name}", None))
        b_, _, _ = set_of((f"boundary, inside the spans: {out_name}", None))
        check("boundary conventions give the same word P R F1: " + out_name, a_["word"]["strict"] == b_["word"]["strict"],
              (a_["word"]["strict"], b_["word"]["strict"]))
        check("boundary conventions give the same item P R F1: " + out_name, a_["item"]["strict"] == b_["item"]["strict"]
              and a_["item"]["strict"]["precision"] == 1.0, (a_["item"]["strict"], b_["item"]["strict"]))
    # boundary words found by the rule (direct check)
    for text, gold, want in ((T4, [("PERSON", "Paul Morel"), ("ORG", "Varenne")], ["M", "société", "la"]),
                             (T11, [("ADDRESS", "Lilas")], ["rue", "des"]),
                             (T1, T1_GOLD, ["M"])):
        rec = _rec(text, gold)
        a = st.tokenize(text)
        starts = [t[0] for t in a]
        cov = [False] * len(text)
        for g in rec["gold"]:
            for c_ in range(g["start"], g["end"]):
                cov[c_] = True
        outs = {k for k, t in enumerate(a) if st.has_alnum(t[2]) and not any(cov[c_] for c_ in range(t[0], t[1]))}
        idx = list(range(len(rec["gold"])))
        bw, _ = boundary_words(a, text, rec["gold"], idx, outs,
                               {i: _overlapping(a, starts, g["start"], g["end"]) for i, g in enumerate(rec["gold"])})
        check("boundary words of " + text[:20], sorted(a[k][2] for k in bw) == sorted(want), sorted(a[k][2] for k in bw))
    # one rule for every failure kind: FP 0 in the headline; failures charged: all 20 non-gold words
    for crash in ("failed document (run log failed, no output)", "failed document, empty output file",
                  "failed document, error text as output", "mask everything, 21 words outside gold (retention 0: failed)",
                  "failed document, output cut after the company (retention 0.286)"):
        s, _, _ = set_of(("perfect masker (codes)", "a"), (crash, "b"))
        check("failure kind does not change the headline: " + crash,
              (s["word"]["strict"]["precision"], s["word"]["strict"]["recall"], s["word"]["strict"]["f1"])
              == (1.0, 0.5, 0.666667), s["word"]["strict"])
        check("failures charged: " + crash, s["word_sensitivity"]["failures_charged"]["f1"] == 0.315789,
              s["word_sensitivity"]["failures_charged"])
    # item precision of a retention failure: headline leaves its regions out, the as-read line counts them
    s, _, _ = set_of(("perfect masker (codes)", "a"), ("failed document, empty output file", "b"))
    check("retention failure: item P 1 (headline), 0.75 as read",
          (s["item"]["strict"]["precision"], s["item"]["strict_retention_failures_as_read"]["precision"]) == (1.0, 0.75),
          s["item"])
    fr, row = read_doc(by["perfect masker (codes)"]["rec"], T1, None, status="not_run", reason="not sent")
    s = summarize([row], [fr], "frpii")
    check("not_run left out", s["documents"] == 0 and len(s["documents_excluded"]) == 1 and s["word"]["strict"]["f1"] is None, s)
    # keep items may not overlap gold items
    try:
        read_doc(_rec(T9, [("PERSON", "Paul Roy")], [("role", "Paul")]), T9, T9)
        check("keep overlapping gold raises", False)
    except ReadingMismatch:
        pass
    # the short report prints the strict reading and the legal terms changed
    s, _, _ = set_of(("gold, dates and amounts masked", None))
    md = markdown(s, "x")
    check("report", "| Overall score (F1) | **66.7** |" in md and "| Precision (P) | 50.0 |" in md
          and "| Recall (R) | 100.0 |" in md and "| Legal terms changed | 0.0 % (0 of 1) |" in md, md)
    # pooling: perfect (a) + no-op (b) + gold, dates and amounts (c): TP 12 FN 6 FP 6 (strict) / 0 (scope)
    s, rows, frs = set_of(("perfect masker (codes)", "a"), ("no-op tool (output = input)", "b"),
                          ("gold, dates and amounts masked", "c"))
    check("pooled micro strict: P 0.666667 R 0.666667 F1 0.666667",
          (s["word"]["strict"]["precision"], s["word"]["strict"]["recall"], s["word"]["strict"]["f1"])
          == (0.666667, 0.666667, 0.666667), s["word"]["strict"])
    check("pooled micro scope-adjusted: P 1 R 0.666667 F1 0.8",
          (s["word"]["scope_adjusted"]["precision"], s["word"]["scope_adjusted"]["recall"], s["word"]["scope_adjusted"]["f1"])
          == (1.0, 0.666667, 0.8), s["word"]["scope_adjusted"])
    iv = s["intervals"]
    check("3 units: not estimable, unit min to max of strict F1 [0, 1]",
          not iv["estimable"] and iv["unit_min_max"]["word_strict_f1"] == [0.0, 1.0], iv)
    # bootstrap on 12 documents (4 copies each of a, b, c): pinned interval, deterministic, seed and draws fixed
    s12, rows12, frs12 = set_of(*[(n_, f"{n_[:3]}{i:02d}") for i in range(4) for n_ in
                                  ("perfect masker (codes)", "no-op tool (output = input)",
                                   "gold, dates and amounts masked")])
    ci = s12["intervals"]
    check("12 units: estimable", ci["estimable"] and ci["units"] == 12 and ci["resamples"] == 2000 and ci["seed"] == 20261023,
          ci)
    check("bootstrap pinned: strict precision interval", ci["ci"]["word_strict_precision"] == PINNED_PRECISION_CI,
          ci["ci"]["word_strict_precision"])
    check("bootstrap is deterministic", summarize(rows12, frs12, "frpii")["intervals"] == ci)
    # clusters: doc_ids in two folders are two units, not estimable; the document bootstrap is shown apart
    rows_c, frs_c = [], []
    for i in range(12):
        fr, row = one("perfect masker (codes)" if i % 2 else "gold, dates and amounts masked",
                      f"{'AB'[i % 2]}/d{i:02d}")
        rows_c.append(row)
        frs_c.append(fr)
    iv = summarize(rows_c, frs_c, "max")["intervals"]
    check("clusters by top folder: 2 units, not estimable, document bootstrap shown",
          iv["units"] == 2 and not iv["estimable"] and "document_bootstrap" in iv
          and iv["unit_min_max"]["word_strict_f1"] == [0.666667, 1.0], iv)
    # the test cases of score_text.py go through read_doc without any mismatch (every style of mask)
    n = 0
    for case in st.review_cases():
        try:
            read_doc(case["rec"], case["src"], case["out"], **dict(case["kw"]))
            n += 1
        except ReadingMismatch as e:
            check("score_text case " + case["case"], False, e)
    check("all score_text cases rebuilt without mismatch", n == len(st.review_cases()), n)
    print("selftest", "OK" if ok else "FAILED", f"({len(cases)} cases, {n} score_text cases rebuilt)")
    return 0 if ok else 1


PINNED_PRECISION_CI = [0.538462, 0.875]  # fixed value: it guards the draw rule of the bootstrap


# ---------------------------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--gold", required=True)
    s.add_argument("--inputs", default=".")
    s.add_argument("--outputs", default=".")
    s.add_argument("--outputs-manifest")
    s.add_argument("--runlog")
    s.add_argument("--json", required=True)
    s.add_argument("--md")
    s.add_argument("--tool", default="")
    s.add_argument("--set", help="set id; must equal the gold's set field")
    s.add_argument("--docs", help="file of doc_ids: score only these documents")
    s.add_argument("--score-text-json", required=True, help="score_text.py result of the same run (required)")
    s.set_defaults(func=cmd_score)
    p = sub.add_parser("pairs")
    p.add_argument("--gold", required=True)
    p.add_argument("--pairs", required=True)
    p.add_argument("--json", required=True)
    p.add_argument("--md")
    p.add_argument("--tool", default="")
    p.add_argument("--set")
    p.add_argument("--score-text-json", required=True, help="score_text.py result of the same pairs (required)")
    p.set_defaults(func=cmd_pairs)
    c = sub.add_parser("common")
    c.add_argument("--out", required=True)
    c.add_argument("results", nargs="+")
    c.set_defaults(func=cmd_common)
    args = ap.parse_args(argv)
    if args.cmd in ("score", "pairs") and not Path(args.score_text_json).exists():
        raise SystemExit(f"--score-text-json {args.score_text_json} does not exist: run score_text.py first")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
