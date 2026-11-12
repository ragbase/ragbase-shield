"""Run RAGbase Shield (rules mode, no spaCy) on FR-PII-Bench v0 and write the predicted spans.

Zero-shot: nothing in Shield is changed or configured for this benchmark. The engine API is the one the
service uses for ``mask_text`` without a dossier: ``Masker(MemoryStore(locale="fr"), locale="fr",
use_ner=False).mask(text)``; its ``spans`` are the replaced character ranges of the input text.

Two modes:

- ``detect`` (headline): one fresh in-memory store per document, nothing registered.
- ``title``: the documents have no parties field and no title field. Only the lawyer letters
  (``courrier_avocat``) carry a natural dossier title, the line ``Affaire : X c/ Y``. In this mode that
  line is given to Shield's own title parser (``parse_parties``, the code that ``add_dossier`` uses) and the
  parties it returns are registered in the store before masking, as a lawyer who names the dossier
  "X c/ Y" would do. Documents without that line are masked exactly as in ``detect``.

Output: .bench_data/public/fr-pii-bench/pred_<mode>.jsonl and run_meta.json.

v0.3 (additive, ignored by score.py): a document record carries ``watch`` = the model finds the gated NER layer
never masks on its own (``MaskResult.watch``: start, end, kind, model label, text), so a results file can say
where a model find went; ``watch_spans`` in the stats. Empty in rules mode.

Usage: python evaluation/public/fr-pii-bench/run_shield.py [--modes detect,title]
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ragbase_shield.engine import Masker, MemoryStore, entity_norm, parse_parties  # noqa: E402

WORK = ROOT / ".bench_data" / "public" / "fr-pii-bench"
DATA = WORK / "fr_pii_bench_v0.jsonl"
NER = "off"          # --ner off|auto (v0.2): "auto" uses the installed GLiNER backend, "off" = R1 rules mode
LANGUAGE = "fr"      # --language fr|auto (v0.2)
TITLE_RE = re.compile(r"^Affaire\s*:\s*(?P<t>.+?)\s*$", re.M)


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load() -> list[dict]:
    if not DATA.exists():
        sys.exit(f"missing {DATA}: run download.py first")
    return [json.loads(line) for line in DATA.open(encoding="utf-8")]


def run(docs: list[dict], mode: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    total = 0.0
    roundtrip_ok = 0
    titled = 0
    registered = 0
    watch_total = 0
    for doc in docs:
        text = doc["text"]
        store = MemoryStore(locale="fr")
        title, parties = None, []
        if mode == "title":
            m = TITLE_RE.search(text)
            if m:
                title = m.group("t")
                titled += 1
                for kind, value in parse_parties(title):
                    norm = entity_norm(kind, value)
                    if norm:
                        store.add(kind, value, norm)
                        parties.append({"kind": kind, "value": value})
                registered += len(parties)
        masker = Masker(store, locale="fr", use_ner=False if NER == "off" else None, language=LANGUAGE)
        assert masker.mode == ("rules" if NER == "off" else masker.mode), masker.mode
        t0 = time.perf_counter()
        res = masker.mask(text)
        dt = time.perf_counter() - t0
        total += dt
        spans = []
        for s in res.spans:
            assert text[s.start:s.end] == s.value, (doc["id"], s)
            spans.append({"start": s.start, "end": s.end, "kind": s.kind, "source": s.source, "text": s.value})
        roundtrip_ok += masker.unmask(res.text) == text
        rec = {"id": doc["id"], "doc_type": doc["doc_type"], "mode": mode, "spans": spans,
               "ms": round(dt * 1000, 3)}
        watch = []
        for w in getattr(res, "watch", None) or ():
            try:
                ws, we, wkind, wlabel = int(w[0]), int(w[1]), str(w[2]), str(w[3])
            except (TypeError, IndexError, ValueError):
                continue
            watch.append({"start": ws, "end": we, "kind": wkind, "label": wlabel, "text": text[ws:we]})
        if watch:
            rec["watch"] = watch
        watch_total += len(watch)
        if mode == "title":
            rec["title"] = title
            rec["parties"] = parties
        out.append(rec)
    stats = {"docs": len(docs), "seconds_total": round(total, 3), "ms_per_doc": round(total * 1000 / len(docs), 2),
             "roundtrip_exact_docs": roundtrip_ok, "predicted_spans": sum(len(r["spans"]) for r in out),
             "watch_spans": watch_total}
    if mode == "title":
        stats.update(docs_with_title=titled, parties_registered=registered)
    return out, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="detect,title")
    ap.add_argument("--ner", choices=("off", "auto"), default="off")
    ap.add_argument("--language", choices=("fr", "auto"), default="fr")
    args = ap.parse_args()
    global NER, LANGUAGE
    NER, LANGUAGE = args.ner, args.language
    docs = load()
    head = git("rev-parse", "HEAD")
    meta = {
        "benchmark": "FR-PII-Bench v0 (JaqueBill/fr-pii-bench @ 5476b0a489249047a478083ac856a328d0e4d2c3)",
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "shield_head": head,
        "shield_src_last_change": git("log", "-1", "--format=%H", "--", "src"),
        "shield_src_dirty": bool(git("status", "--porcelain", "--", "src")),
        "engine_mode": Masker(MemoryStore(locale="fr"), locale="fr", use_ner=False if NER == "off" else None).mode,
        "ner_flag": NER, "language_flag": LANGUAGE,
        "locale": "fr",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "modes": {},
    }
    for mode in [m.strip() for m in args.modes.split(",") if m.strip()]:
        if mode not in ("detect", "title"):
            sys.exit(f"unknown mode {mode}")
        preds, stats = run(docs, mode)
        with (WORK / f"pred_{mode}.jsonl").open("w", encoding="utf-8") as f:
            for r in preds:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        meta["modes"][mode] = stats
        print(mode, json.dumps(stats))
    (WORK / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("shield HEAD", head, "src dirty" if meta["shield_src_dirty"] else "src clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
