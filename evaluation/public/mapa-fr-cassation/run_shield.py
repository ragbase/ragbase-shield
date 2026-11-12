"""Run RAGbase Shield (rules mode, no spaCy) on the 19 MAPA Cour de cassation decisions.

Zero-shot: nothing in Shield is changed, configured or registered for this benchmark.

Path measured (the real product path for a document read by an AI assistant through Shield): the public
``Service`` API, one fresh data directory per decision (``RAGBASE_SHIELD_HOME`` under .bench_data, file key,
never the OS keychain, outbound network blocked in this process):

1. one folder per decision holding only that decision's plain text (``<doc>/decision.txt``);
2. ``add_dossier(folder)`` with no title: Shield scans and masks the document, registering what it finds;
3. ``list_documents`` then ``read_document`` page by page from offset 0 (default page size): this is the
   masked text an assistant receives, after Shield's last canary (the "guard" that replaces any registered
   value still present in a page).

To score character offsets, the runner records (read-only wrappers, nothing changed) the ``Masker.mask`` call
that produced the read text and the canary's ``Service._redact`` call of each page, then maps every replaced
range back to the original source text. Checks recorded per document: the reader text, the recorded mask call
reproducing the service's masked text exactly, every returned page explained by the recorded canary call, and
the letters and digits left outside the recovered ranges equal to those of the text the assistant received.

Output: .bench_data/public/mapa-fr-cassation/run/<doc>.json and run/run_meta.json. Each <doc>.json holds the
masked text an assistant received and the masked character ranges in the ORIGINAL source text coordinates.

Usage: python evaluation/public/mapa-fr-cassation/run_shield.py
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / ".bench_data" / "public" / "mapa-fr-cassation"
DATA = WORK / "data"
OUT = WORK / "run"
HOME = WORK / "shield-home"
FOLDERS = WORK / "folders"

# Isolation BEFORE importing Shield: own data directory, file key, French codes.
os.environ["RAGBASE_SHIELD_HOME"] = str(HOME)
os.environ["RAGBASE_SHIELD_KEYRING"] = "0"
os.environ["RAGBASE_SHIELD_LOCALE"] = "fr"

_real_connect = socket.socket.connect


def _guarded_connect(self, address):  # same rule as tests/conftest.py: local only
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host in ("127.0.0.1", "localhost", "::1"):
        return _real_connect(self, address)
    if self.family == getattr(socket, "AF_UNIX", None):
        return _real_connect(self, address)
    raise RuntimeError(f"network connection attempted during the evaluation: {address!r}")


socket.socket.connect = _guarded_connect

sys.path.insert(0, str(ROOT / "src"))
import ragbase_shield  # noqa: E402
from ragbase_shield import documents  # noqa: E402
from ragbase_shield.engine import PREFIXES, UNMASK_RE, Masker, ner_installed  # noqa: E402
from ragbase_shield.service import DEFAULT_READ_CHARS, Service  # noqa: E402

sys.path.insert(0, str(HERE))
from download import DOCS  # noqa: E402


INFO_CHECKS = ("pages", "masker_mode", "document_mask_calls")
PLACEHOLDER_RE = re.compile(r"\[(?:" + "|".join(sorted({fr for fr, _en, _l in PREFIXES.values()})) + r")\]")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def clean_to_orig(orig: str, clean: str) -> list[int]:
    """Offset map cleaned -> original. documents._clean_text only removes characters (\\r, NUL, trailing
    blanks, extra blank lines, leading/trailing newlines) on these NFC texts; every skipped character is
    checked to be whitespace."""
    m = [0] * len(clean)
    i = 0
    for j, ch in enumerate(clean):
        while i < len(orig) and orig[i] != ch:
            if not orig[i].isspace() and orig[i] != "\x00":
                raise ValueError(f"non-blank character dropped at {i}: {orig[i]!r}")
            i += 1
        if i >= len(orig):
            raise ValueError("cleaned text is not a subsequence of the original")
        m[j] = i
        i += 1
    return m


def segments(raw: str, masked: str, spans) -> list[tuple[int, int, int, int]]:
    """[(masked_start, masked_end, raw_start, raw_end)] for every replaced span, checking that the masked
    text is exactly the raw text with each span replaced by one code."""
    out = []
    q = 0
    prev = 0
    for sp in sorted(spans, key=lambda s: s.start):
        lit = raw[prev:sp.start]
        if masked[q:q + len(lit)] != lit:
            raise ValueError(f"literal mismatch before raw offset {sp.start}")
        q += len(lit)
        m = UNMASK_RE.match(masked, q)
        if m is None:
            raise ValueError(f"no code at masked offset {q}")
        out.append((q, m.end(), sp.start, sp.end))
        q = m.end()
        prev = sp.end
    if masked[q:] != raw[prev:]:
        raise ValueError("tail mismatch")
    return out


def masked_to_raw(pos_s: int, pos_e: int, segs, raw_len: int) -> tuple[int, int]:
    """Map a masked-text range to a raw-text range (a range touching a code covers the code's whole span)."""
    def one(p: int, end: bool) -> int:
        shift = 0
        for ms, me, rs, re_ in segs:
            if p < ms:
                break
            if ms <= p < me:
                return re_ if end else rs
            shift = re_ - me
        return p + shift + (1 if end else 0)
    return one(pos_s, False), one(pos_e - 1, True)


class _Recorder:
    """Read-only instrumentation of the real call path: records every ``Masker.mask`` call and every
    ``Service._redact`` call (the canary replacing leftover values in a page), without changing them."""

    def __init__(self):
        self.masks: list[tuple[str, object]] = []
        self.redacts: list[tuple[str, list, str]] = []
        self._mask = Masker.mask
        self._redact = Service._redact

    def install(self) -> None:
        rec = self

        def mask(self_, text, **kw):
            res = rec._mask(self_, text, **kw)
            rec.masks.append((text, res))
            return res

        def redact(self_, text, hits, d, own, **kw):
            # v0.2+: the service passes ``mint_into=`` (the canary of a shared output); the recorder passes it on
            out = rec._redact(self_, text, hits, d, own, **kw)
            rec.redacts.append((text, list(hits), out))
            return out

        Masker.mask = mask
        Service._redact = redact

    def uninstall(self) -> None:
        Masker.mask = self._mask
        Service._redact = self._redact


def run_doc(doc: str, rec: _Recorder) -> dict:
    src = DATA / "txt" / f"{doc}.txt"
    orig = src.read_bytes().decode("utf-8-sig")
    folder = FOLDERS / doc
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, folder / "decision.txt")
    # One fresh Shield data directory per decision: the canary of one decision never sees another one.
    svc = Service(HOME / doc)
    try:
        rec.masks.clear()
        t0 = time.perf_counter()
        added = svc.add_dossier(folder)
        code = added["code"]
        listed = svc.list_documents(code)
        assert len(listed) == 1, listed
        doc_id = listed[0]["id"]
        pages = []  # (start, end, text returned, redact records of that page)
        start = 0
        while True:
            rec.redacts.clear()
            r = svc.read_document(code, doc_id, start)
            end = r["next"] if r["next"] is not None else r["total_chars"]
            pages.append((start, end, r["text"], list(rec.redacts)))
            if r["next"] is None:
                break
            start = r["next"]
        seconds = time.perf_counter() - t0
        service_text = "".join(p[2] for p in pages)

        d = svc._dossier(code)
        ref = d.get_document(doc_id)
        entry = svc._docs[(d.code, ref.id)]
        # v0.2+: the service runs the canary once on the whole cached document (``_guard_doc``): ``entry.masked``
        # is the guarded text and ``entry.masked0`` the masker's own output, the one a ``Masker.mask`` call made
        raw, pre = entry.raw, getattr(entry, "masked0", entry.masked)
        checks = {"masker_mode": svc._masker(d).mode,
                  "raw_equals_reader": raw == documents.read_text(folder / "decision.txt").text}
        calls = [res for text, res in rec.masks if text == raw and res.text == pre]
        checks["read_mask_call_found"] = bool(calls)
        checks["document_mask_calls"] = sum(1 for text, _res in rec.masks if text == raw)
        mres = calls[-1]
        segs = segments(raw, pre, mres.spans)
        hits_pre = []  # canary hits in pre-canary masked text coordinates
        ok_pages = True
        for pstart, pend, ptext, reds in pages:
            page = pre[pstart:pend]
            if not reds:
                ok_pages &= ptext == page
                continue
            if len(reds) != 1 or reds[0][0] != page or reds[0][2] != ptext:
                ok_pages = False
            for h in reds[0][1]:
                hits_pre.append((pstart + h.start, pstart + h.end, h))
        checks["pages_explained"] = ok_pages
        checks["pages"] = len(pages)
        c2o = clean_to_orig(orig, raw)

        def to_orig(s: int, e: int) -> tuple[int, int]:
            return c2o[s], c2o[e - 1] + 1

        spans = []
        for sp in mres.spans:
            s, e = to_orig(sp.start, sp.end)
            spans.append({"start": s, "end": e, "kind": sp.kind, "source": sp.source, "stage": "mask",
                          "text": orig[s:e]})
        for hs, he, h in hits_pre:
            rs, re_ = masked_to_raw(hs, he, segs, len(raw))
            s, e = to_orig(rs, re_)
            spans.append({"start": s, "end": e, "kind": h.kind, "source": h.source, "stage": "guard",
                          "text": orig[s:e]})
        spans.sort(key=lambda x: (x["start"], x["end"]))
        # End-to-end check: the letters and digits outside the recovered ranges are exactly those of the text
        # the assistant received, once its codes and canary placeholders ("[PERSONNE]") are removed.
        keep = [True] * len(orig)
        for sp in spans:
            for i in range(sp["start"], sp["end"]):
                keep[i] = False
        left = "".join(c for c, k in zip(orig, keep) if k and c.isalnum())
        received = PLACEHOLDER_RE.sub(" ", UNMASK_RE.sub(" ", service_text))
        checks["clear_text_matches_received"] = left == "".join(c for c in received if c.isalnum())
        ents = svc.entities(code)
    finally:
        svc.close()
    kinds: dict[str, int] = {}
    for e in ents:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {
        "doc": doc,
        "dossier": code,
        "chars_original": len(orig),
        "chars_read": len(raw),
        "seconds": round(seconds, 3),
        "checks": checks,
        "entities_registered": len(ents),
        "entities_by_kind": dict(sorted(kinds.items())),
        "spans": spans,
        "masked_text": service_text,
    }


def main() -> int:
    if not (DATA / "txt").exists():
        sys.exit(f"missing {DATA}: run download.py first")
    for p in (HOME, FOLDERS, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    rec = _Recorder()
    rec.install()
    results = []
    try:
        for doc, _chamber, _stem in DOCS:
            res = run_doc(doc, rec)
            (OUT / f"{doc}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            ok = all(v for k, v in res["checks"].items() if k not in INFO_CHECKS)
            print(f"{doc}: {len(res['spans'])} masked spans, {res['entities_registered']} entities, "
                  f"{res['seconds']:.2f}s, checks {'OK' if ok else res['checks']}")
            results.append(res)
    finally:
        rec.uninstall()
    meta = {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "shield_version": ragbase_shield.__version__,
        "git_head": git("rev-parse", "HEAD"),
        "git_src_dirty": bool(git("status", "--porcelain", "--", "src")),
        "src_last_commit": git("log", "-1", "--format=%H", "--", "src"),
        "src_tree": git("rev-parse", "HEAD:src"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "ner_installed": ner_installed(),
        "mode": "rules (no spaCy)",
        "path": "Service.add_dossier (one folder and one fresh data directory per decision, no title) "
                f"+ read_document pages (default page size {DEFAULT_READ_CHARS} chars)",
        "locale": "fr",
        "documents": len(results),
        "all_checks_ok": all(all(v for k, v in r["checks"].items() if k not in INFO_CHECKS)
                             for r in results),
        "masker_modes": sorted({r["checks"]["masker_mode"] for r in results}),
        "seconds_total": round(sum(r["seconds"] for r in results), 2),
        "chars_total": sum(r["chars_read"] for r in results),
    }
    (OUT / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0 if meta["all_checks_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
