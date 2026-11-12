"""Score RAGbase Shield predictions on FR-PII-Bench v0 with the benchmark's OWN metric definitions.

Definitions (dataset card + technical report v0.1, section 3, quoted):

- recall_any: "a gold entity is >=80 % covered by predicted spans of any type: was it masked?"
- recall_label: "same, with the right type"
- precision: "a predicted span overlaps gold by >=50 % of its length"
- false masks: "predicted spans with no overlap at all: the utility cost"

The author's scorer is not public ("available to partners on request"), so this is a re-implementation from
those sentences. Choices made where the sentences leave room (stated in RESULTS.md):

- Coverage is character-level over ALL characters of the gold span (spaces and punctuation included), against
  the UNION of the predicted spans (several predicted spans may together cover one gold entity).
- recall_label uses the union of the predicted spans whose kind maps to the gold label.
- Precision: overlap of the predicted span with the union of the gold spans of the document, divided by the
  predicted span's length, >= 0.5. Label-agnostic (the definition names no type). The other reading ("its" =
  the gold span's length) is reported under sensitivity.
- False mask: predicted span with zero overlapping characters with every gold span.

Shield kind -> benchmark label mapping (fixed before scoring, never tuned):

  PERSON->PERSON, ORG->COMPANY, ADDRESS->ADDRESS, EMAIL->EMAIL, PHONE->PHONE, IBAN->IBAN, NIR->NIR,
  SIREN->SIREN, SIRET->SIRET, BIRTHDATE->DOB.
  ID_CODE is Shield's single kind for plates, passport numbers, fiscal numbers and other ID numbers (code IDENT_n).
  - strict (headline): ID_CODE maps to no label, so FISCAL, PLAQUE and PASSEPORT get recall_label 0 by design.
  - grouped (secondary): ID_CODE counts as the right type for FISCAL, PLAQUE and PASSEPORT.
  VAT, CARD, CASE_REF, URL map to no label (they still count for recall_any, precision and false masks).

Usage: python evaluation/public/fr-pii-bench/score.py [--mode detect|title] [--json out.json] [--selftest]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "fr-pii-bench"
DATA = WORK / "fr_pii_bench_v0.jsonl"

LABELS = ["PERSON", "ADDRESS", "COMPANY", "EMAIL", "PHONE", "DOB", "NIR", "SIREN", "SIRET", "IBAN", "FISCAL",
          "PLAQUE", "PASSEPORT"]
MAP_STRICT = {"PERSON": {"PERSON"}, "ORG": {"COMPANY"}, "ADDRESS": {"ADDRESS"}, "EMAIL": {"EMAIL"},
              "PHONE": {"PHONE"}, "IBAN": {"IBAN"}, "NIR": {"NIR"}, "SIREN": {"SIREN"}, "SIRET": {"SIRET"},
              "BIRTHDATE": {"DOB"}}
MAP_GROUPED = dict(MAP_STRICT, ID_CODE={"FISCAL", "PLAQUE", "PASSEPORT"})

ANY_T = 0.80
PREC_T = 0.50

LEGAL_FORMS = {"SARL", "SAS", "SA", "EURL", "S.A.R.L.", "S.A.", "S.A.S.", "SASU", "SNC"}


def chars(spans) -> set[int]:
    out: set[int] = set()
    for s, e in spans:
        out.update(range(s, e))
    return out


def cover(gs: int, ge: int, covered: set[int], only_alnum: str | None = None) -> float:
    idx = range(gs, ge) if only_alnum is None else [i for i in range(gs, ge) if only_alnum[i].isalnum()]
    idx = list(idx)
    if not idx:
        return 0.0
    return sum(1 for i in idx if i in covered) / len(idx)


def person_form(text: str, e: dict) -> str:
    before = text[max(0, e["start"] - 9):e["start"]]
    first = e["text"].split()[0]
    if before.endswith("Maître "):
        return "Maître Nom"
    if re.search(r"(?:M\.|Mme|Monsieur|Madame) $", before):
        return "honorific + Prénom Nom"
    if first.isupper() and len(first) > 1:
        return "NOM Prénom (caps)"
    return "Prénom Nom"


def dob_form(v: str) -> str:
    if "/" in v:
        return "dd/mm/yyyy"
    if "." in v:
        return "dd.mm.yyyy"
    return "dd Month yyyy (English month name)"


def company_core(text: str, e: dict) -> tuple[int, int]:
    """Gold COMPANY span without its trailing legal forms ("Thierry EURL" -> "Thierry")."""
    toks = list(re.finditer(r"\S+", e["text"]))
    while len(toks) > 1 and toks[-1].group().rstrip(",") in LEGAL_FORMS:
        toks.pop()
    return e["start"], e["start"] + toks[-1].end()


def score(mode: str) -> dict:
    docs = {d["id"]: d for d in (json.loads(x) for x in DATA.open(encoding="utf-8"))}
    preds = {p["id"]: p for p in (json.loads(x) for x in (WORK / f"pred_{mode}.jsonl").open(encoding="utf-8"))}
    assert set(docs) == set(preds), "prediction ids differ from gold ids"

    per_label = {l: Counter() for l in LABELS}
    per_kind: dict[str, Counter] = defaultdict(Counter)
    per_doctype: dict[str, Counter] = defaultdict(Counter)
    forms: dict[str, Counter] = defaultdict(Counter)
    misses, false_masks, label_errors = [], [], []
    tot = Counter()

    for did, doc in docs.items():
        text, gold = doc["text"], doc["entities"]
        pspans = preds[did]["spans"]
        all_cov = chars((p["start"], p["end"]) for p in pspans)
        by_label_strict: dict[str, set[int]] = defaultdict(set)
        by_label_grouped: dict[str, set[int]] = defaultdict(set)
        for p in pspans:
            for lab in MAP_STRICT.get(p["kind"], ()):
                by_label_strict[lab].update(range(p["start"], p["end"]))
            for lab in MAP_GROUPED.get(p["kind"], ()):
                by_label_grouped[lab].update(range(p["start"], p["end"]))
        gold_cov = chars((g["start"], g["end"]) for g in gold)

        for g in gold:
            lab = g["label"]
            c_any = cover(g["start"], g["end"], all_cov)
            ok_any = c_any >= ANY_T
            ok_strict = cover(g["start"], g["end"], by_label_strict[lab]) >= ANY_T
            ok_grouped = cover(g["start"], g["end"], by_label_grouped[lab]) >= ANY_T
            ok_alnum = cover(g["start"], g["end"], all_cov, only_alnum=text) >= ANY_T
            row = per_label[lab]
            row["n"] += 1
            row["any"] += ok_any
            row["label_strict"] += ok_strict
            row["label_grouped"] += ok_grouped
            row["any_alnum"] += ok_alnum
            row["fully_masked"] += c_any >= 1.0
            row["touched"] += c_any > 0
            dt = per_doctype[doc["doc_type"]]
            dt["n"] += 1
            dt["any"] += ok_any
            if lab == "PERSON":
                f = person_form(text, g)
                forms["PERSON:" + f]["n"] += 1
                forms["PERSON:" + f]["any"] += ok_any
            elif lab == "DOB":
                f = dob_form(g["text"])
                forms["DOB:" + f]["n"] += 1
                forms["DOB:" + f]["any"] += ok_any
            elif lab == "COMPANY":
                cs, ce = company_core(text, g)
                forms["COMPANY:name without legal form"]["n"] += 1
                forms["COMPANY:name without legal form"]["any"] += cover(cs, ce, all_cov) >= ANY_T
            if not ok_any:
                hit = [p["text"] for p in pspans if p["start"] < g["end"] and p["end"] > g["start"]]
                misses.append({"id": did, "label": lab, "gold": g["text"], "coverage": round(c_any, 3),
                               "overlapping_pred": hit})
            elif not ok_grouped:
                kinds = sorted({p["kind"] for p in pspans if p["start"] < g["end"] and p["end"] > g["start"]})
                label_errors.append({"id": did, "label": lab, "gold": g["text"], "pred_kinds": kinds})

        for p in pspans:
            plen = p["end"] - p["start"]
            ov = len(gold_cov.intersection(range(p["start"], p["end"])))
            best_single = max((min(p["end"], g["end"]) - max(p["start"], g["start"]) for g in gold), default=0)
            ok = plen > 0 and ov / plen >= PREC_T
            k = per_kind[p["kind"]]
            k["n"] += 1
            k["correct"] += ok
            k["false_mask"] += ov == 0
            tot["pred"] += 1
            tot["prec_ok"] += ok
            tot["prec_ok_single"] += plen > 0 and max(best_single, 0) / plen >= PREC_T
            # Other reading of "overlaps gold by >=50 % of its length": "its" = the gold span's length.
            best_gold_frac = max((max(0, min(p["end"], g["end"]) - max(p["start"], g["start"])) / (g["end"] - g["start"])
                                  for g in gold), default=0)
            tot["prec_ok_goldlen"] += best_gold_frac >= PREC_T
            tot["false_mask"] += ov == 0
            if ov == 0:
                false_masks.append({"id": did, "kind": p["kind"], "text": p["text"]})

    n = sum(r["n"] for r in per_label.values())
    agg = {k: sum(r[k] for r in per_label.values()) for k in ("any", "label_strict", "label_grouped", "any_alnum",
                                                                "fully_masked")}
    r3 = lambda a, b: round(a / b, 3) if b else None  # noqa: E731
    return {
        "mode": mode,
        "gold_entities": n,
        "predicted_spans": tot["pred"],
        "recall_any": {"count": agg["any"], "of": n, "rate": r3(agg["any"], n)},
        "recall_label_strict": {"count": agg["label_strict"], "of": n, "rate": r3(agg["label_strict"], n)},
        "recall_label_grouped": {"count": agg["label_grouped"], "of": n, "rate": r3(agg["label_grouped"], n)},
        "precision": {"count": tot["prec_ok"], "of": tot["pred"], "rate": r3(tot["prec_ok"], tot["pred"])},
        "false_masks": tot["false_mask"],
        "sensitivity": {
            "recall_any_alnum_chars_only": {"count": agg["any_alnum"], "of": n, "rate": r3(agg["any_alnum"], n)},
            "recall_fully_masked_100pct": {"count": agg["fully_masked"], "of": n, "rate": r3(agg["fully_masked"], n)},
            "precision_single_gold_span": {"count": tot["prec_ok_single"], "of": tot["pred"],
                                           "rate": r3(tot["prec_ok_single"], tot["pred"])},
            "precision_overlap_ge_50pct_of_gold_length": {"count": tot["prec_ok_goldlen"], "of": tot["pred"],
                                                          "rate": r3(tot["prec_ok_goldlen"], tot["pred"])},
        },
        "per_label": {l: {"n": r["n"], "any": r["any"], "label_strict": r["label_strict"],
                          "label_grouped": r["label_grouped"], "touched": r["touched"]} for l, r in per_label.items()},
        "per_shield_kind": {k: dict(v) for k, v in sorted(per_kind.items())},
        "per_doc_type": {k: dict(v) for k, v in sorted(per_doctype.items())},
        "diagnostics": {k: dict(v) for k, v in sorted(forms.items())},
        "false_mask_list": false_masks,
        "miss_list": misses,
        "label_error_list": label_errors,
    }


def selftest() -> None:
    """Threshold edges of the three rules on toy spans."""
    cov = chars([(0, 8)])
    assert cover(0, 10, cov) == 0.8                       # exactly 80 % -> counts (>=)
    assert cover(0, 10, chars([(0, 7)])) < ANY_T          # 70 % -> miss
    assert cover(0, 10, chars([(0, 4), (4, 8)])) == 0.8   # union of two predicted spans
    gold = chars([(0, 10)])
    assert len(gold.intersection(range(0, 20))) / 20 >= PREC_T        # 50 % of the predicted span -> correct
    assert not len(gold.intersection(range(0, 21))) / 21 >= PREC_T    # 47.6 % -> not correct (but not a false mask)
    assert len(gold.intersection(range(10, 15))) == 0                 # touching end, no shared char -> false mask
    assert company_core("X", {"start": 0, "end": 12, "text": "Thierry EURL"}) == (0, 7)
    assert company_core("X", {"start": 0, "end": 17, "text": "Rodrigues et Fils"}) == (0, 17)
    print("selftest ok")


def fmt(c: dict) -> str:
    return f"{c['rate']:.3f} ({c['count']}/{c['of']})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="detect")
    ap.add_argument("--json", default=None, help="write the full score JSON here (default: .bench_data/.../scores_<mode>.json)")
    ap.add_argument("--selftest", action="store_true", help="check the metric edges on toy spans and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    s = score(args.mode)
    out = Path(args.json) if args.json else WORK / f"scores_{args.mode}.json"
    out.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"mode={s['mode']} gold={s['gold_entities']} predicted={s['predicted_spans']}")
    print(f"recall_any           {fmt(s['recall_any'])}")
    print(f"recall_label strict  {fmt(s['recall_label_strict'])}")
    print(f"recall_label grouped {fmt(s['recall_label_grouped'])}")
    print(f"precision            {fmt(s['precision'])}")
    print(f"false masks          {s['false_masks']}")
    print("per label: n any label_strict label_grouped")
    for l, r in s["per_label"].items():
        print(f"  {l:10} {r['n']:4} {r['any']:4} {r['label_strict']:4} {r['label_grouped']:4}")
    print("per Shield kind:", json.dumps(s["per_shield_kind"]))
    print("diagnostics:", json.dumps(s["diagnostics"], ensure_ascii=False))
    print("sensitivity:", json.dumps(s["sensitivity"]))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
