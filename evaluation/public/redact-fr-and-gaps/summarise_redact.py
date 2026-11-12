"""Turn the metrics files written by score_redact.sh (the benchmark's own scorer) into the report tables, and list
what stays unmatched (same greedy one-to-one, same-type, any-overlap rule as the scorer's ``partial`` mode).

Usage: .venv/bin/python evaluation/public/redact-fr-and-gaps/summarise_redact.py [config ...]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
W = ROOT / ".bench_data" / "public" / "redact"
ADAPTERS = ("plain", "decomposed")
MODES = ("partial", "exact", "fuzzy")
MAPPED = {"Full_Name", "First_Given_Name", "Last_Family_Name", "Org_Name", "Address_Personal", "Work_Email_Address",
          "Personal_Email_Address", "Telephone_Numbers_Personal", "Account_Statements",
          "National_Identification_Number", "Credit_Card_Numbers", "Customer_Reference_Number", "Date_of_Birth",
          "Social_Media_Identifiers", "Employee_ID_Number"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None


def match(gold, pred):
    used, matched = set(), [False] * len(gold)
    for gi, g in enumerate(gold):
        for pi, p in enumerate(pred):
            if pi in used or g["entity_type"] != p["entity_type"]:
                continue
            if g.get("start") is None or g.get("end") is None:
                ok = g.get("entity_string") == p.get("entity_string")
            else:
                ok = max(0, min(g["end"], p["end"]) - max(g["start"], p["start"])) > 0
            if ok:
                matched[gi] = True
                used.add(pi)
                break
    return matched, used


def main(configs):
    print("### Aggregate (French records: FR 40 + FR_CA 40 = 80, 1,814 gold entities)\n")
    print("| config | adapter | mode | TP | FP | FN | precision | recall | **F1** | macro-F1 (types in the FR gold) |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for c in configs:
        for a in ADAPTERS:
            for m in MODES:
                d = load(W / f"metrics_{c}_{a}_{m}.json")
                if not d:
                    continue
                g = d["aggregate"]
                print(f"| {c} | {a} | {m} | {g['tp']} | {g['fp']} | {g['fn']} | {g['precision']:.3f} | {g['recall']:.3f} | "
                      f"**{g['f1']:.3f}** | {g['macro_f1']:.3f} |")
    print("\n### Per language, partial mode\n")
    print("| config | adapter | FR F1 (P / R) | FR_CA F1 (P / R) |")
    print("|---|---|---|---|")
    for c in configs:
        for a in ADAPTERS:
            d = load(W / f"metrics_{c}_{a}_partial.json")
            if not d:
                continue
            pl = d["per_language"]
            print(f"| {c} | {a} | " + " | ".join(f"{pl[l]['f1']:.3f} ({pl[l]['precision']:.3f} / {pl[l]['recall']:.3f})"
                                              for l in ("FR", "FR_CA")) + " |")
    print("\n### Recall by sensitivity tier (F6) and disclosure form (F5), partial mode\n")
    print("| config | adapter | HIGH | MEDIUM | LOW | complete | partial | obfuscated |")
    print("|---|---|---|---|---|---|---|---|")
    for c in configs:
        for a in ADAPTERS:
            d = load(W / f"metrics_{c}_{a}_partial.json")
            if not d:
                continue
            f6, s6 = d["F6_recall_by_sensitivity_tier"], d["F6_support_by_sensitivity_tier"]
            f5, s5 = d["F5_recall_by_disclosure_form"], d["F5_support_by_disclosure_form"]
            cells = [f"{f6.get(t, 0):.3f} ({round(f6.get(t, 0) * s6.get(t, 0))}/{s6.get(t, 0)})" for t in ("HIGH", "MEDIUM", "LOW")]
            cells += [f"{f5.get(t, 0):.3f} ({round(f5.get(t, 0) * s5.get(t, 0))}/{s5.get(t, 0)})" for t in ("complete", "partial", "obfuscated")]
            print(f"| {c} | {a} | " + " | ".join(cells) + " |")
    # per type for the headline config
    for c in configs:
        d = load(W / f"metrics_{c}_decomposed_partial.json")
        if not d:
            continue
        print(f"\n### Per type, {c} decomposed, partial mode (gold types of the French records)\n")
        print("| REDACT type | gold | TP | FP | FN | precision | recall | F1 | in Shield's adapter |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        rows = sorted(d["per_type"].items(), key=lambda kv: -kv[1]["n_gold"])
        in_scope = Counter()
        for t, r in rows:
            scope = "yes" if t in MAPPED else "no"
            in_scope[scope] += r["n_gold"]
            in_scope[scope + "_tp"] += r["tp"]
            print(f"| {t} | {r['n_gold']} | {r['tp']} | {r['fp']} | {r['fn']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {scope} |")
        print(f"\nGold entities of a type Shield's adapter can emit: {in_scope['yes']} (recall {in_scope['yes_tp']}/{in_scope['yes']} = "
              f"{in_scope['yes_tp'] / max(1, in_scope['yes']):.3f}); of a type it never emits: {in_scope['no']} "
              f"(these are certain misses: {in_scope['no']} of the {in_scope['yes'] + in_scope['no']} FN ceiling).")
        # unmatched predictions and gold, by kind / type
        pred = load(W / f"pred_{c}_decomposed.json")
        fp_kind, fp_type, fn_type, fp_examples = Counter(), Counter(), Counter(), {}
        for rec in pred["predictions"]:
            matched, used = match(rec["gold_entities"], rec["predicted_entities"])
            for pi, p in enumerate(rec["predicted_entities"]):
                if pi not in used:
                    fp_kind[p["kind"]] += 1
                    fp_type[p["entity_type"]] += 1
                    fp_examples.setdefault(p["kind"], [])
                    if len(fp_examples[p["kind"]]) < 6:
                        fp_examples[p["kind"]].append(p["entity_string"][:40])
            for g, ok in zip(rec["gold_entities"], matched):
                if not ok:
                    fn_type[g["entity_type"]] += 1
        print(f"\nUnmatched predictions ({sum(fp_kind.values())}) by Shield kind: " +
              ", ".join(f"{k} {v}" for k, v in fp_kind.most_common()))
        print("Examples per kind (synthetic benchmark strings): " +
              "; ".join(f"{k}: " + " | ".join(v) for k, v in fp_examples.items()))
        print(f"Unmatched gold ({sum(fn_type.values())}) by type: " + ", ".join(f"{k} {v}" for k, v in fn_type.most_common(20)))
        # type confusion: an unmatched prediction that overlaps a gold span of another type is an adapter mismatch,
        # not an over-mask; a type-agnostic any-overlap F1 (NOT the paper's metric) bounds what a perfect adapter gives
        conf, pure, tp_any, fp_any, fn_any = Counter(), Counter(), 0, 0, 0
        for rec in pred["predictions"]:
            gold, preds = rec["gold_entities"], rec["predicted_entities"]
            matched, used = match(gold, preds)
            for pi, p in enumerate(preds):
                if pi in used:
                    continue
                ov = [g for g in gold if g.get("start") is not None and
                      max(0, min(g["end"], p["end"]) - max(g["start"], p["start"])) > 0]
                if ov:
                    conf[(p["kind"], p["entity_type"], ov[0]["entity_type"])] += 1
                else:
                    pure[p["kind"]] += 1
            # type-agnostic greedy one-to-one, any overlap
            used2, m2 = set(), 0
            for g in gold:
                for pi, p in enumerate(preds):
                    if pi in used2:
                        continue
                    if g.get("start") is None:
                        ok = g.get("entity_string") == p.get("entity_string")
                    else:
                        ok = max(0, min(g["end"], p["end"]) - max(g["start"], p["start"])) > 0
                    if ok:
                        used2.add(pi); m2 += 1
                        break
            tp_any += m2; fn_any += len(gold) - m2; fp_any += len(preds) - len(used2)
        P = tp_any / max(1, tp_any + fp_any); R = tp_any / max(1, tp_any + fn_any); F = 2 * P * R / max(1e-9, P + R)
        print(f"Of the unmatched predictions, {sum(conf.values())} overlap a gold span of another type (adapter type "
              f"mismatch) and {sum(pure.values())} overlap no gold span at all (over-mask or unannotated).")
        print("Type mismatches (kind -> emitted type -> gold type): " +
              "; ".join(f"{k[0]}->{k[1]}->{k[2]} {v}" for k, v in conf.most_common(12)))
        print("Over-masks by kind: " + ", ".join(f"{k} {v}" for k, v in pure.most_common()))
        print(f"Type-agnostic any-overlap (NOT the paper's metric): TP {tp_any} FP {fp_any} FN {fn_any} "
              f"P {P:.3f} R {R:.3f} F1 {F:.3f}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["rules", "ner-fastino", "ner-urchade"])
