"""Independent re-check of the PrivacyBench v0.2 run (2026-10-19). Does NOT import the benchmark's code.

    python recheck_v02.py native   <predictions dir>      NER recall (label-matched and any-label), per set/label/kind
    python recheck_v02.py human    <ner_predictions dir>  [any]   P/R/F1 on the 12 human-annotation files
    python recheck_v02.py syncover <run dir>              codes-run spans absent from the synthetic run: still covered?

Native metric re-implemented from the dataset card: a gold span (status != not_rendered) is detected when a prediction
of the same file unit, with the same label or a label the benchmark lists as an alias of it, overlaps it by >= 0.5 in
native coordinates (eml/slack/xlsx/csv: intersection / union, 1.0 when the prediction contains the gold span; pdf:
Jaccard of the glyph sets for a prediction reported as ``chars``, share of the gold glyphs whose centre lies in a box
for one reported as ``boxes`` (v0.4 T1); docx: shared characters per xpath / max(gold, prediction)). "any label" also counts a gold
span covered (>= 0.5) only by a prediction of another label: the value is masked, the benchmark does not credit it.
Human metric: overlap matching per row, P = matched predictions / predictions, R = detected gold / gold.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".bench_data" / "public" / "privacybench"
DATA = WORK / "data"
HUM = DATA / "human_annotations"
LABELS = ["NAME_GIVEN", "NAME_FAMILY", "EMAIL_ADDRESS", "USERNAME", "ORGANIZATION", "PHONE_NUMBER",
          "LOCATION_ADDRESS", "EMPLOYEE_ID", "ACCOUNT_NUMBER", "URL"]
# alias table typed from the dataset card / types.py documentation (prediction label -> gold labels it may match)
ALIAS = {"PHONE": {"PHONE_NUMBER"}, "TELEPHONE": {"PHONE_NUMBER"}, "LOCATION": {"LOCATION_ADDRESS"},
         "ADDRESS": {"LOCATION_ADDRESS"}, "STREET_ADDRESS": {"LOCATION_ADDRESS"}, "GPE": {"LOCATION_ADDRESS"},
         "DOMAIN_NAME": {"URL"}, "WEBSITE": {"URL"}, "LINK": {"URL"},
         "NUMERIC_PII": {"EMPLOYEE_ID", "ACCOUNT_NUMBER"}, "HEALTHCARE_ID": {"EMPLOYEE_ID", "ACCOUNT_NUMBER"},
         "ID": {"EMPLOYEE_ID", "ACCOUNT_NUMBER"}, "ID_NUMBER": {"EMPLOYEE_ID", "ACCOUNT_NUMBER"},
         "IDENTIFIER": {"EMPLOYEE_ID", "ACCOUNT_NUMBER"}, "US_BANK_NUMBER": {"ACCOUNT_NUMBER"},
         "IBAN_CODE": {"ACCOUNT_NUMBER"}, "CREDIT_CARD": {"ACCOUNT_NUMBER"}, "BANK_ACCOUNT": {"ACCOUNT_NUMBER"}}
for l in LABELS:
    ALIAS.setdefault(l, set()).add(l)


def can_match(gold_label, pred_label):
    return gold_label in ALIAS.get(str(pred_label).upper(), ()) or gold_label == pred_label


def scorable(pred_label):
    return str(pred_label).upper() in ALIAS


def ukey(kind, path, container):
    kind = "eml" if (kind or "").lower() == "email" else (kind or "").lower()
    part = None
    if container and container.get("kind") == "eml_attachment":
        part = container.get("part_index")
        if part is None:
            part = ("name", container.get("filename"))
    p = (path or "").replace("\\", "/")
    return (kind, p, part)


def rng(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    if b1 - b0 > 0 and inter >= b1 - b0:
        return 1.0
    uni = max(a1, b1) - min(a0, b0)
    return inter / uni if uni > 0 else 0.0


def glyphs(loc):
    """Glyph positions of a PDF location: ``chars`` (the answer key, older runs) or ``glyphs`` (v0.4 T1 runs, which
    report ``boxes`` to the scorer and keep their per-glyph list under a key the scorer does not read)."""
    parts = loc["fragments"] if loc.get("crosses_parts") else [loc]
    out = set()
    for p in parts:
        for c in p.get("chars") or p.get("glyphs") or []:
            out.add((int(c[1]), round(float(c[2]) * 100), round(float(c[3]) * 100)))
    return out


def reports_boxes(p):
    """True for a predicted PDF location scored by its ``boxes`` (no ``chars``), as the card's scorer does."""
    return not p.get("chars") and bool(p.get("boxes"))


def box_cover(p, g):
    """The card's PDF rule for a prediction reported as ``boxes``: the share of the gold glyphs whose centre lies in
    one of the boxes of the same page (0.5 pt tolerance)."""
    gch = [c for q in gparts(g) for c in (q.get("chars") or [])]
    boxes = p.get("boxes") or []
    if not gch or not boxes:
        return 0.0
    covered = 0
    for c in gch:
        cx, cy = (c[2] + c[4]) / 2, (c[3] + c[5]) / 2
        if any(b.get("page") == c[1] and b["x0"] - 0.5 <= cx <= b["x1"] + 0.5 and b["top"] - 0.5 <= cy <= b["bottom"] + 0.5
               for b in boxes):
            covered += 1
    return covered / len(gch)


def gparts(loc):
    return loc["fragments"] if loc.get("crosses_parts") else [loc]


def xp(x):
    return (x or "").replace("[1]", "")


def ov(kind, p, g, cache):
    if kind == "eml":
        return rng(p["file_char_start"], p["file_char_end"], g["file_char_start"], g["file_char_end"])
    if kind == "slack":
        ptr = (p.get("json_pointer") or "").rstrip("/")
        if not ptr.endswith("/text"):
            ptr += "/text"
        if ptr != g["json_pointer"]:
            return 0.0
        return rng(p["start"], p["end"], g["start"], g["end"])
    if kind == "pdf":
        if reports_boxes(p):
            return box_cover(p, g)
        gk = cache.setdefault(("g", id(g)), glyphs(g))
        pk = cache.setdefault(("p", id(p)), glyphs(p))
        if not gk or not pk:
            return 0.0
        i = len(gk & pk)
        return i / (len(gk) + len(pk) - i)
    if kind == "docx":
        gf = [(xp(f["xpath"]), f["start"], f["end"]) for q in gparts(g) for f in (q.get("fragments") or [])]
        pf = [(xp(f.get("xpath")), f["start"], f["end"]) for f in (p.get("fragments") or [])]
        gt, pt = sum(e - s for _, s, e in gf), sum(e - s for _, s, e in pf)
        if not gt:
            return 0.0
        inter = sum(max(0, min(ge, pe) - max(gs, ps)) for gx, gs, ge in gf for px, ps, pe in pf if gx == px)
        return inter / max(gt, pt)
    if kind == "xlsx":
        best = 0.0
        for q in gparts(g):
            if (p.get("sheet") or "").lower() != (q.get("sheet") or "").lower() or (p.get("cell") or "").upper() != (q.get("cell") or "").upper():
                continue
            best = max(best, rng(p["char_start"], p["char_end"], q["char_start"], q["char_end"]) if "char_start" in p else 1.0)
        return best
    if kind == "csv":
        best = 0.0
        for q in gparts(g):
            if p.get("row") != q.get("row") or p.get("col") != q.get("col"):
                continue
            best = max(best, rng(p["value_char_start"], p["value_char_end"], q["value_char_start"], q["value_char_end"]))
        return best
    raise ValueError(kind)


def score_set(pred_file: Path, name: str):
    preds = defaultdict(list)
    by_file = defaultdict(list)
    n_pred = Counter()
    dup = 0
    seen = set()
    for line in pred_file.open(encoding="utf-8"):
        r = json.loads(line)
        f = r["file"]
        k = ukey(f.get("kind"), f.get("path"), f.get("container"))
        for s in r["spans"]:
            sig = (k, s["label"], json.dumps(s["location"], sort_keys=True))
            if sig in seen:
                dup += 1
            seen.add(sig)
            if not scorable(s["label"]):
                continue
            preds[k].append(s)
            by_file[k[:2]].append(s)
            n_pred[s["label"]] += 1
    c = Counter()
    wide = Counter()
    fallback = 0
    for line in (DATA / "ground_truth" / name / "ground_truth.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        f = row["file"]
        k = ukey(f.get("kind"), f.get("path"), f.get("container"))
        cands = preds.get(k)
        if not cands:
            cands = by_file.get(k[:2]) or []
            if cands:
                fallback += 1
        cache = {}
        kind = k[0]
        if kind == "pdf":
            gidx = cache.get(("idx", id(cands)))
            if gidx is None:
                gidx = defaultdict(list)
                plen = []
                for j, p in enumerate(cands):
                    gs = glyphs(p["location"])
                    plen.append(len(gs))
                    for gk in gs:
                        gidx[gk].append(j)
                gidx = (gidx, plen)
                cache[("idx", id(cands))] = gidx
        for g in row["ground_truth_spans"]:
            loc = g["location"]
            if loc.get("status") == "not_rendered":
                c["not_rendered"] += 1
                continue
            lab = g["label"]
            if lab not in LABELS:
                c["gold_out_of_scope"] += 1
                continue
            c["gold"] += 1
            c["gold|" + lab] += 1
            c["gold|kind|" + kind] += 1
            hit = None
            any_other = False
            if kind == "pdf":
                gk = glyphs(loc)
                shared = Counter(j for x in gk for j in gidx[0].get(x, ()))
                pairs = [(i / (len(gk) + gidx[1][j] - i), cands[j]) for j, i in shared.items()
                         if not reports_boxes(cands[j]["location"])]
                # v0.4 T1: a prediction reported as boxes is scored by the card's box rule (any box of the page)
                gpages = {c[0] for c in gk}
                pairs += [(box_cover(p["location"], loc), p) for p in cands if reports_boxes(p["location"])
                          and any(b.get("page") in gpages for b in p["location"]["boxes"])]
            else:
                pairs = [(ov(kind, p["location"], loc, cache), p) for p in cands]
            for o, p in pairs:
                if o >= 0.5:
                    if can_match(lab, p["label"]):
                        if hit is None or o > hit[0]:
                            hit = (o, p)
                    else:
                        any_other = True
            if hit:
                c["det"] += 1
                c["det|" + lab] += 1
                c["det|kind|" + kind] += 1
                c["det_via|" + lab + "|" + hit[1]["label"]] += 1
                plen, glen = len(hit[1].get("text") or ""), len(g["text"])
                if glen and plen >= 3 * glen and plen - glen >= 10:
                    wide[lab] += 1
                    c["det_wide"] += 1
            elif any_other:
                c["other_label_only"] += 1
                c["other_label_only|" + lab] += 1
    return c, n_pred, dup, fallback, wide


def native(a):
    sets = a.sets.split(",") if a.sets else sorted(p.name for p in (DATA / "ground_truth").iterdir() if p.is_dir())
    tot, totp = Counter(), Counter()
    per = {}
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(4) as ex:
        results = list(ex.map(score_set, [Path(a.pred_dir) / f"{s}.jsonl" for s in sets], sets))
    for s, (c, np_, dup, fb, wide) in zip(sets, results):
        per[s] = {"gold": c["gold"], "det": c["det"], "recall": c["det"] / c["gold"], "dup_spans": dup,
                  "fallback_rows": fb, "pred_in_scope": sum(np_.values()), "det_wide": c["det_wide"],
                  "other_label_only": c["other_label_only"]}
        tot += c
        totp += np_
        print(f"{s:34s} {c['gold']:6d} {c['det']:6d} {100*c['det']/c['gold']:6.2f}  dup={dup} fb={fb} wide={c['det_wide']}", flush=True)
    macro = sum(v["recall"] for v in per.values()) / len(per)
    print(f"MACRO {100*macro:.3f}  POOLED {100*tot['det']/tot['gold']:.3f} ({tot['det']}/{tot['gold']})  not_rendered={tot['not_rendered']}")
    for l in LABELS:
        print(f"  {l:18s} {tot['gold|'+l]:6d} {tot['det|'+l]:6d} {100*tot['det|'+l]/max(1,tot['gold|'+l]):6.2f}  other_label_only={tot['other_label_only|'+l]}")
    for k in ("eml", "slack", "pdf", "docx", "xlsx", "csv"):
        print(f"  kind {k:6s} {tot['gold|kind|'+k]:6d} {tot['det|kind|'+k]:6d} {100*tot['det|kind|'+k]/max(1,tot['gold|kind|'+k]):6.2f}")
    via = {k: v for k, v in tot.items() if k.startswith("det_via|")}
    print("  detected via label:", dict(sorted(via.items())))
    print("  predictions in scope by label:", dict(totp), "total", sum(totp.values()))
    ol = sum(v["other_label_only"] for v in per.values())
    mac_any = sum((v["det"] + v["other_label_only"]) / v["gold"] for v in per.values()) / len(per)
    print(f"ANY LABEL macro {100*mac_any:.3f}  pooled {100*(tot['det']+ol)/tot['gold']:.3f} ({tot['det']+ol}/{tot['gold']})")
    if a.json:
        Path(a.json).write_text(json.dumps({"per_set": per, "macro": macro, "totals": dict(tot), "pred": dict(totp)}, indent=1))


def rid(row):
    m = row.get("meta") or {}
    r = row.get("row_id") or m.get("row_id") or m.get("cell_id")
    page = row.get("page") if row.get("page") is not None else m.get("page")
    return f"{r}#p{page}" if page is not None else str(r)


def human(a):
    pdir = Path(a.pred_dir)
    anylab = a.extra == "any"
    cm = (lambda g, p: True) if anylab else can_match
    tot = Counter()
    per = {}
    for gpath in sorted(HUM.glob("*.jsonl")):
        gold, text = {}, {}
        dup_gold_rows = 0
        for line in gpath.open(encoding="utf-8"):
            r = json.loads(line)
            k = rid(r)
            if k in gold:
                dup_gold_rows += 1
            gold[k] = [s for s in r["ground_truth_spans"] if s["label"] in LABELS]
            text[k] = r.get("text") or ""
        pred = {}
        dup_pred_rows = 0
        c = Counter()
        for line in (pdir / gpath.name).open(encoding="utf-8"):
            r = json.loads(line)
            k = rid(r)
            if k in pred:
                dup_pred_rows += 1
            spans = r.get("entities") if "entities" in r else r.get("spans", [])
            pred[k] = [s for s in spans if scorable(s["label"])]
            c["pred_out_of_scope"] += sum(1 for s in spans if not scorable(s["label"]))
            for s in spans:
                if k in text and text[k][s["start"]:s["end"]] != s.get("text"):
                    c["offset_mismatch"] += 1
            sigs = [(s["start"], s["end"], s["label"]) for s in spans]
            c["dup_spans"] += len(sigs) - len(set(sigs))
        c["pred_rows_without_gold"] = len(set(pred) - set(gold))
        c["gold_rows_without_pred_row"] = len(set(gold) - set(pred))
        c["dup_gold_rows"] = dup_gold_rows
        c["dup_pred_rows"] = dup_pred_rows
        for k, gs in gold.items():
            ps = pred.get(k, [])
            c["gold"] += len(gs)
            c["pred"] += len(ps)
            for g in gs:
                hit = any(cm(g["label"], p["label"]) and p["start"] < g["end"] and g["start"] < p["end"] for p in ps)
                c["det"] += hit
                c["gold|" + g["label"]] += 1
                c["det|" + g["label"]] += hit
                c["exact"] += any(cm(g["label"], p["label"]) and p["start"] == g["start"] and p["end"] == g["end"] for p in ps)
            for p in ps:
                m = any(cm(g["label"], p["label"]) and p["start"] < g["end"] and g["start"] < p["end"] for g in gs)
                c["matched"] += m
                c["pred|" + p["label"]] += 1
                c["matched|" + p["label"]] += m
        P = c["matched"] / c["pred"] if c["pred"] else 0
        R = c["det"] / c["gold"]
        F = 2 * P * R / (P + R) if P + R else 0
        per[gpath.stem] = (P, R, F)
        print(f"{gpath.stem:44s} gold={c['gold']:5d} pred={c['pred']:5d} matched={c['matched']:5d} det={c['det']:5d} "
              f"P={100*P:5.1f} R={100*R:5.1f} F1={100*F:5.1f} offs_bad={c['offset_mismatch']} dupspan={c['dup_spans']} "
              f"oos={c['pred_out_of_scope']} rows_nogold={c['pred_rows_without_gold']} gold_nopred={c['gold_rows_without_pred_row']} dupg={dup_gold_rows} dupp={dup_pred_rows}")
        tot += c
    P = tot["matched"] / tot["pred"]
    R = tot["det"] / tot["gold"]
    F = 2 * P * R / (P + R)
    Pe, Re = tot["exact"] / tot["pred"], tot["exact"] / tot["gold"]
    print(f"POOLED gold={tot['gold']} pred={tot['pred']} matched={tot['matched']} det={tot['det']} P={100*P:.2f} R={100*R:.2f} F1={100*F:.2f} "
          f"exact={tot['exact']} Pe={100*Pe:.2f} Re={100*Re:.2f} F1e={100*2*Pe*Re/(Pe+Re):.2f} out_of_scope_dropped={tot['pred_out_of_scope']}")
    mp = [sum(v[i] for v in per.values()) / len(per) for i in range(3)]
    print("MACRO P/R/F1 = %.1f / %.1f / %.1f" % tuple(100 * x for x in mp))
    for l in LABELS:
        print(f"  {l:18s} gold={tot['gold|'+l]:5d} recall={100*tot['det|'+l]/max(1,tot['gold|'+l]):5.1f}  pred={tot['pred|'+l]:5d} prec={100*tot['matched|'+l]/max(1,tot['pred|'+l]):5.1f}")
    for l in sorted(set(k.split('|')[1] for k in tot if k.startswith('pred|')) - set(LABELS)):
        print(f"  alias {l:12s} pred={tot['pred|'+l]:5d} prec={100*tot['matched|'+l]/max(1,tot['pred|'+l]):5.1f}")


def units(p):
    out = defaultdict(list)
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        f = r["file"]
        out[ukey(f["kind"], f["path"], f.get("container"))].extend(r["spans"])
    return out


def cells(kind, loc):
    """set of atomic positions covered by a location"""
    if kind == "eml":
        return {("c", i) for i in range(loc["file_char_start"], loc["file_char_end"])}
    if kind == "slack":
        return {(loc["json_pointer"], i) for i in range(loc["start"], loc["end"])}
    if kind == "csv":
        return {(loc["row"], loc["col"], i) for i in range(loc["value_char_start"], loc["value_char_end"])}
    if kind == "xlsx":
        return {(loc["sheet"], loc["cell"], i) for i in range(loc["char_start"], loc["char_end"])}
    if kind == "docx":
        return {(xp(f["xpath"]), i) for f in loc.get("fragments") or [] for i in range(f["start"], f["end"])}
    if kind == "pdf":
        return glyphs(loc)
    return set()


def syncover(a):
    W = Path(a.pred_dir)
    tot = Counter()
    lab_clear = Counter()
    for p in sorted((W / "predictions/mask").glob("*.jsonl")):
        ua, ub = units(p), units(W / "predictions_synthetic/mask" / p.name)
        for k, sa in ua.items():
            sb = ub.get(k, [])
            keyb = {(s["label"], json.dumps(s["location"], sort_keys=True)) for s in sb}
            cov = set()
            for s in sb:
                cov |= cells(k[0], s["location"])
            for s in sa:
                if (s["label"], json.dumps(s["location"], sort_keys=True)) in keyb:
                    continue
                c = cells(k[0], s["location"])
                tot["only_codes"] += 1
                if not c:
                    tot["no_cells"] += 1
                elif c <= cov:
                    tot["fully_covered"] += 1
                elif c & cov:
                    tot["partly_covered"] += 1
                else:
                    tot["clear"] += 1
                    lab_clear[s["label"]] += 1
    print(dict(tot))
    print("left fully in the clear, by label:", dict(lab_clear.most_common()))


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("native", "human", "syncover"))
    ap.add_argument("pred_dir")
    ap.add_argument("extra", nargs="?", default="")
    ap.add_argument("--sets")
    ap.add_argument("--json")
    a = ap.parse_args()
    {"native": native, "human": human, "syncover": syncover}[a.cmd](a)


if __name__ == "__main__":
    cli()
