"""Run RAGbase Shield v0.2 on the French records (FR + FR_CA) of the REDACT locked 1,000-record split and write
predictions in the format of the benchmark's own scorer (``evaluation/scripts/compute_stratified_f1.py`` of
github.com/guneeshvats/REDACT-PII-Benchmark, MIT; the data are under the REDACT Dataset Terms, which allow
benchmarking and evaluation).

Zero-shot: nothing in Shield is changed for this benchmark. One fresh ``MemoryStore(locale="fr")`` per record,
``Masker(store, locale="fr", language="fr", use_ner=..., ner_model=...)``; the ``spans`` of the result are the
replaced character ranges of the input text.

Adapter from Shield kinds to the 51 REDACT types (fixed before the first score, 2026-10-18):

- ``plain``: one prediction per Shield span, one type per kind (the rule the benchmark's harness applies to
  Presidio: PERSON -> Full_Name, EMAIL -> Work_Email_Address, PHONE -> Telephone_Numbers_Personal, ...).
  Kinds with no REDACT type (SIREN, SIRET, VAT) are dropped, as the harness drops Presidio's unmapped types.
- ``decomposed``: the same, plus (a) a PERSON span of two words or more also yields First_Given_Name and
  Last_Family_Name sub-spans (the gold annotates the given and family names inside every full name; the order is
  given name first unless the span starts with an all-capital word, the French "NOM Prénom" order; a word in
  lower case joins the family name as a particle; a title word such as "M." or "Dr" is skipped); a one-word PERSON
  span is First_Given_Name when the word is in Shield's own first-name lexicon, else Last_Family_Name;
  (b) an EMAIL whose domain is a public consumer mail provider is Personal_Email_Address, else Work_Email_Address.

Usage: .venv/bin/python evaluation/public/redact-fr-and-gaps/run_redact.py [rules|ner-fastino|ner-urchade ...]
Output: .bench_data/public/redact/pred_<config>_<adapter>.json (+ run_<config>_meta.json)
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import ragbase_shield  # noqa: E402
from ragbase_shield.engine import Masker, MemoryStore  # noqa: E402
from ragbase_shield.engine import names as _names  # noqa: E402
from ragbase_shield.engine import ner as nr  # noqa: E402

WORK = ROOT / ".bench_data" / "public" / "redact"
DATA = WORK / "raw" / "pii_benchmark_sample1000.json"
LANGS = ("FR", "FR_CA")
CONFIGS = {
    "rules": {"use_ner": False, "ner_model": "auto"},
    "ner-fastino": {"use_ner": None, "ner_model": "fastino"},
    "ner-urchade": {"use_ner": None, "ner_model": "urchade"},
}
PLAIN = {
    "PERSON": "Full_Name",
    "ORG": "Org_Name",
    "ADDRESS": "Address_Personal",
    "EMAIL": "Work_Email_Address",
    "PHONE": "Telephone_Numbers_Personal",
    "IBAN": "Account_Statements",
    "ACCOUNT_NUMBER": "Account_Statements",
    "NIR": "National_Identification_Number",
    "CARD": "Credit_Card_Numbers",
    "CASE_REF": "Customer_Reference_Number",
    "ID_CODE": "Customer_Reference_Number",
    "BIRTHDATE": "Date_of_Birth",
    "USERNAME": "Social_Media_Identifiers",
    "EMPLOYEE_ID": "Employee_ID_Number",
    "URL": "Social_Media_Identifiers",
    # SIREN, SIRET, VAT: no REDACT type -> dropped (counted in the meta file)
}
TITLES = {"m.", "m", "mme", "mme.", "mlle", "mlle.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", "me", "me.",
          "maître", "maitre", "pr", "pr.", "prof", "prof."}
WEBMAIL = {"gmail.com", "googlemail.com", "yahoo.com", "yahoo.fr", "yahoo.ca", "hotmail.com", "hotmail.fr", "hotmail.ca",
           "outlook.com", "outlook.fr", "live.com", "live.fr", "live.ca", "msn.com", "icloud.com", "me.com", "mac.com",
           "aol.com", "gmx.com", "gmx.fr", "gmx.net", "protonmail.com", "proton.me", "pm.me", "mail.com", "yandex.com",
           "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "neuf.fr", "laposte.net", "bbox.fr", "numericable.fr",
           "videotron.ca", "sympatico.ca", "bell.net", "rogers.com", "shaw.ca", "telus.net", "cogeco.ca"}
WORD_RE = re.compile(r"\S+")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def first_names() -> set:
    try:
        return set(_names._lists()[3])  # the lexicon the engine itself uses
    except Exception:  # noqa: BLE001
        return set()


def is_first(word: str, fn: set) -> bool:
    low = word.lower().strip("'’.,;:")
    if low in fn:
        return True
    parts = [p for p in low.split("-") if p]
    return len(parts) > 1 and all(p in fn for p in parts)


def decompose_person(text: str, start: int, end: int, fn: set) -> list[tuple[int, int, str]]:
    """Sub-spans (start, end, type) of a PERSON span: the whole span as Full_Name plus given / family parts."""
    words = [(m.start() + start, m.end() + start, m.group()) for m in WORD_RE.finditer(text[start:end])]
    words = [w for w in words if w[2].lower() not in TITLES]
    if not words:
        return []
    if len(words) == 1:
        s, e, w = words[0]
        return [(s, e, "First_Given_Name" if is_first(w, fn) else "Last_Family_Name")]
    out = [(words[0][0], words[-1][1], "Full_Name")]
    caps = [w for w in words if w[2].isupper() and len(w[2].strip(".,-")) > 1]
    if words[0][2].isupper() and len(words[0][2].strip(".,-")) > 1 and len(caps) < len(words):
        # "NOM Prénom": leading capital words = family name, the rest = given name
        k = 0
        while k < len(words) and words[k][2].isupper():
            k += 1
        out.append((words[0][0], words[k - 1][1], "Last_Family_Name"))
        out.append((words[k][0], words[-1][1], "First_Given_Name"))
    else:
        out.append((words[0][0], words[0][1], "First_Given_Name"))
        out.append((words[1][0], words[-1][1], "Last_Family_Name"))
    return out


def adapt(text: str, spans, adapter: str, fn: set) -> tuple[list[dict], int]:
    preds, dropped = [], 0
    for sp in spans:
        kind = sp.kind
        if kind not in PLAIN:
            dropped += 1
            continue
        if adapter == "decomposed" and kind == "PERSON":
            for s, e, t in decompose_person(text, sp.start, sp.end, fn):
                preds.append({"entity_type": t, "entity_string": text[s:e], "start": s, "end": e, "kind": kind})
            continue
        t = PLAIN[kind]
        if adapter == "decomposed" and kind == "EMAIL":
            dom = text[sp.start:sp.end].rsplit("@", 1)[-1].lower().strip(">)]").rstrip(".")
            t = "Personal_Email_Address" if dom in WEBMAIL else "Work_Email_Address"
        preds.append({"entity_type": t, "entity_string": text[sp.start:sp.end], "start": sp.start, "end": sp.end,
                      "kind": kind})
    return preds, dropped


def run(config: str) -> None:
    cfg = CONFIGS[config]
    recs = [r for r in json.loads(DATA.read_text(encoding="utf-8")) if r["axes"]["language"] in LANGS]
    fn = first_names()
    backend, load_s = None, 0.0
    if cfg["use_ner"] is not False:
        t0 = time.perf_counter()
        backend = nr.load_backend(cfg["ner_model"])
        load_s = time.perf_counter() - t0
        if backend is None:
            sys.exit(f"{config}: no NER backend loaded")
        print(config, "backend", backend.name, f"load {load_s:.1f} s", flush=True)
    outs = {a: [] for a in ("plain", "decomposed")}
    modes, total, chars, dropped_total, kinds = set(), 0.0, 0, 0, {}
    roundtrip_ok = 0
    for k, r in enumerate(recs):
        text = r["text"]
        store = MemoryStore(locale="fr")
        m = Masker(store, locale="fr", language="fr", use_ner=cfg["use_ner"], ner_model=cfg["ner_model"])
        modes.add(m.mode)
        t0 = time.perf_counter()
        res = m.mask(text)
        dt = time.perf_counter() - t0
        total += dt
        chars += len(text)
        try:
            from ragbase_shield.engine import unmask  # type: ignore
            roundtrip_ok += int(unmask(res.text, store) == text)
        except Exception:  # noqa: BLE001
            pass
        for sp in res.spans:
            kinds[sp.kind] = kinds.get(sp.kind, 0) + 1
        gold = r["entities"]
        for a in outs:
            preds, dropped = adapt(text, res.spans, a, fn)
            if a == "plain":
                dropped_total += dropped
            outs[a].append({"record_id": r["record_id"], "language": r["axes"]["language"], "axes": r["axes"],
                            "gold_entities": gold, "predicted_entities": preds, "n_spans": len(res.spans),
                            "mask_s": dt, "chars": len(text), "ner": res.ner})
        print(config, k, r["record_id"], r["axes"]["language"], f"{len(text)} ch", f"{dt * 1000:.0f} ms",
              f"{len(res.spans)} spans", flush=True)
    for a, rows in outs.items():
        (WORK / f"pred_{config}_{a}.json").write_text(
            json.dumps({"detector": f"ragbase-shield-v0.2-{config}-{a}", "predictions": rows}, ensure_ascii=False),
            encoding="utf-8")
    meta = {"config": config, "adapters": list(outs), "engine_modes": sorted(modes),
            "backend": backend.name if backend else None, "load_s": load_s, "records": len(recs), "chars": chars,
            "mask_s_total": total, "chars_per_s": chars / total if total else None, "spans_by_kind": kinds,
            "spans_dropped_unmapped": dropped_total, "roundtrip_exact": roundtrip_ok,
            "commit": git("rev-parse", "--short", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "version": getattr(ragbase_shield, "__version__", "?"), "python": platform.python_version(),
            "loadavg_end": os.getloadavg(), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "data": str(DATA),
            "first_name_lexicon_size": len(fn)}
    if backend is not None:
        meta["labels"] = backend.labels
        meta["thresholds"] = backend.thresholds
    (WORK / f"run_{config}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(config, "done", json.dumps({k: v for k, v in meta.items() if k not in ("labels", "thresholds")}), flush=True)


if __name__ == "__main__":
    for c in (sys.argv[1:] or ["rules", "ner-fastino", "ner-urchade"]):
        run(c)
