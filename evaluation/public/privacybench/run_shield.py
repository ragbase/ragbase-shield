"""Run RAGbase Shield (rules mode, no spaCy) on Tonic.ai PrivacyBench v2.5 and write its predictions.

Zero-shot: nothing in Shield is changed or configured for this benchmark. The engine API is the one the
service uses: ``Masker(MemoryStore(locale="en"), locale="en", use_ner=False)``. One store per workspace export
(one PrivacyBench set), so one person keeps one code across every email, Slack message and document of that
export, as in one Shield dossier.

Two passes per export, like Shield's own ``add_dossier`` (scan every document to register the entities, then
read with the full store): pass 1 masks every unit to fill the store, pass 2 masks again and writes the spans.
Two variants are written from pass 2:

- ``mask``: the spans ``Masker.mask`` replaced (what ``mask_text`` returns);
- ``canary``: ``mask`` plus the spans of ``Masker.scan`` (registered values and valid identifiers still in
  clear), which is the extra pass the service runs on every model-facing text (ARCHITECTURE.md 4.4).

Adapters (this file, not Shield): Shield reads .pdf/.docx/.txt/.md/.eml/.html, but the benchmark scores
predictions in each file's native coordinates, so the text given to the masker is extracted here with a
char-level map back to those coordinates: .eml body (file char offsets), Slack message text (JSON pointer +
offsets), PDF (pdfplumber glyph boxes, the same library the answer key uses), DOCX (XPath of each <w:t>),
XLSX (sheet + cell + offset, openpyxl) and CSV (row + column + offset). The benchmark's ten labels are
produced from Shield's kinds by a fixed mapping (``KIND_TO_LABEL``); a PERSON span is split into NAME_GIVEN
(first token) and NAME_FAMILY (last token) exactly like the benchmark's own Presidio and GLiNER2 baselines
(``split_name_span`` in ``run_baseline_ner.py``); a one-token PERSON span is NAME_FAMILY when the store knows
that token only as the last token of a registered person, else NAME_GIVEN (the baselines' default).
A PERSON/ORG span that is a Slack mention or an @handle is labelled USERNAME. ``new_text`` is Shield's code
(PERSON_A, EMAIL_1...): Shield pseudonymises with codes, it does not invent synthetic identities.

v0.3 (2026-10-21) adapter changes, all mirrors of what the product does with a dossier folder:
- PDF text comes from the product's shared reader functions (``documents.pdf_page_lines`` and
  ``documents.pdf_word_separator``): a wide gap between two words of one line is a table cell boundary (" | ");
- the dossier directory of the export (``engine.directory.build`` over the e-mail headers, the Slack ``users.json``
  and the Word authors, the same items ``Service._build_directory`` reads) is given to the masker, which registers
  every full name before the first mask (``RAGBASE_SHIELD_PB_DIRECTORY=0`` turns this off);
- the PERSON split reads the token roles of the engine (``Masker.person_roles``: the entity of the mention, the
  directory, the "Last, First" order, the export's evidence) instead of a positional split; a quoted nickname is its
  own NAME_GIVEN span;
- with ``--synthetic``, pass 1 registers the export in codes mode and the fakes are drawn in pass 2 only
  (``Service._scan`` does the same for a synthetic dossier), so a fake never equals a real value seen later.

v0.4 T1 (2026-10-25) report-format changes (native predictions only; the masked text, the codes and the human-file
report do not change):
- a PDF span is reported as merged per-line ``boxes`` (the README's other PDF format, the answer key's own); its
  per-glyph list is kept under ``glyphs``, which the scorer does not read (leak_check / recheck_v02 do);
- one NAME_GIVEN / NAME_FAMILY span per name token (the answer key tags names token by token);
- a LOCATION_ADDRESS span with a town / state / postcode tail is reported as a street-level span (with its unit) and
  a locality span (the v2.5 answer key is street-level only).

Outputs under .bench_data/public/privacybench/ (or under .bench_data/public/privacybench/<name>/ with --out <name>,
so that a rules run and a rules + NER run keep their own files):
    predictions/<variant>/<set>.jsonl          native-coordinate predictions, one line per file unit
    ner_predictions/<variant>/<set>.jsonl       text-level predictions for human_annotations/<set>.jsonl
    ner_predictions/<variant>/<set>_documents.jsonl
    predictions_synthetic/<variant>/<set>.jsonl with --synthetic: a second, independent run of every export in
                                                synthetic replacement mode (``Masker(..., replacement="synthetic")``,
                                                fresh store); ``new_text`` is the fake value Shield wrote in place of
                                                the span, the input of the benchmark's LLM judge
    run_meta.json                               versions, timings, counts, warnings

Usage: python evaluation/public/privacybench/run_shield.py [--sets a,b] [--workers 6] [--skip-human]
       [--ner off|auto] [--language auto|en] [--out NAME] [--synthetic]
"""
from __future__ import annotations

import argparse
import csv
import email
import email.policy
import io
import json
import platform
import re
import subprocess
import sys
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from operator import itemgetter
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ragbase_shield import documents as D  # noqa: E402  (v0.3: the product's PDF table-cell reader)
from ragbase_shield.engine import Masker, MemoryStore, normalize  # noqa: E402
from ragbase_shield.engine import directory as dr  # noqa: E402  (v0.3: the dossier directory of an export)
from ragbase_shield.engine.types import MAX_DIGITS, MAX_LETTERS, PREFIXES  # noqa: E402

WORK = ROOT / ".bench_data" / "public" / "privacybench"
DATA = WORK / "data"
VARIANTS = ("mask", "canary")

LOCALE = "en"
# v0.2 run flags, passed to the worker processes through the environment (spawned workers re-import this file):
#   RAGBASE_SHIELD_NER=off (R1 rules mode, default) | auto (the installed GLiNER backend)
#   RAGBASE_SHIELD_LANGUAGE=auto (default: detected per unit, short units take the locale "en") | en
import os as _os  # noqa: E402


def _use_ner():
    return None if _os.environ.get("RAGBASE_SHIELD_NER", "off").lower() == "auto" else False


def _language():
    return _os.environ.get("RAGBASE_SHIELD_LANGUAGE", "auto")


# v0.2 output layout and synthetic mode, also through the environment (spawned workers re-import this file):
#   RAGBASE_SHIELD_PB_OUT=<name>      write under .bench_data/public/privacybench/<name>/ (default: the folder itself)
#   RAGBASE_SHIELD_PB_SYNTHETIC=1     add the synthetic replacement run (predictions_synthetic/)
def _out_dir() -> Path:
    name = _os.environ.get("RAGBASE_SHIELD_PB_OUT", "").strip()
    return WORK / name if name else WORK


def _synthetic() -> bool:
    return _os.environ.get("RAGBASE_SHIELD_PB_SYNTHETIC", "0") == "1"


PRED = _out_dir() / "predictions"
NER_PRED = _out_dir() / "ner_predictions"
SYN_PRED = _out_dir() / "predictions_synthetic"

# Harness-side setting, not a Shield setting: the engine keeps a small LRU of NER results per chunk (4,096 entries,
# ``engine/ner.py`` ChunkCache). A benchmark export is masked twice (pass 1 fills the store, pass 2 writes the spans)
# and a third and fourth time with --synthetic; a cache that holds every chunk of one export makes the repeat passes
# rules-speed. The cache holds offsets and labels only, no text; a hit returns exactly what the model returned.
try:
    from ragbase_shield.engine import ner as _ner  # noqa: E402
    _ner._SHARED_CACHE.max_items = 1_000_000
except Exception:  # noqa: BLE001 - rules mode has nothing to cache
    pass
# Shield kind -> benchmark label (or an alias the benchmark's scorer folds onto its labels, see
# LABEL_ALIASES in synthesis_evaluation/types.py). PERSON is split (see split_person). Kinds with no
# benchmark label (NIR, SIREN, SIRET, VAT, CASE_REF, BIRTHDATE) keep Shield's name: the scorer ignores them.
KIND_TO_LABEL = {
    "ORG": "ORGANIZATION", "EMAIL": "EMAIL_ADDRESS", "PHONE": "PHONE_NUMBER", "ADDRESS": "LOCATION_ADDRESS",
    "URL": "URL", "IBAN": "IBAN_CODE", "CARD": "CREDIT_CARD", "ID_CODE": "ID_NUMBER",
}
MESSAGE_LABELS = {"NAME_GIVEN", "NAME_FAMILY", "EMAIL_ADDRESS", "USERNAME", "ORGANIZATION"}
HANDLE_RE = re.compile(r"^(<@[^<>\s]+>|@[A-Za-z0-9._\-]{2,})$")
TOKEN_RE = re.compile(r"\S+")  # same as the benchmark baselines' _TOKEN_RE
# A code as the masker writes it, read back from the masked text. CODE_RE itself refuses a code glued to "_"
# ("signer_PERSON_A" in a snake_case CSV header), so the prefixes are matched here without its lookarounds.
_LETTER_PREFIXES = sorted({p for fr, en, letters in PREFIXES.values() if letters for p in (fr, en)})
_NUMBER_PREFIXES = sorted({p for fr, en, letters in PREFIXES.values() if not letters for p in (fr, en)})
CODE_AT = re.compile(r"\s?((?:" + "|".join(_LETTER_PREFIXES) + r")_[A-Z]{1,%d}|(?:" % MAX_LETTERS
                     + "|".join(_NUMBER_PREFIXES) + r")_[0-9]{1,%d})" % MAX_DIGITS)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"
DOC_EXT = {".pdf": "pdf", ".docx": "docx", ".xlsx": "xlsx", ".csv": "csv"}
MENTION_RE = re.compile(r"<@[^<>\s]+>")


def ordered(paths) -> list[Path]:
    """Paths in the same order on every OS: case-sensitive, part by part, as PosixPath sorts. A WindowsPath sorts
    case-insensitively, so ``sorted()`` read the units of an export in another order on Windows (other codes, another
    store state), and the predictions were not the same as on the Mac (v0.4 W0)."""
    return sorted(paths, key=lambda q: tuple(q.parts))


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------------------
# units: text + a per-character locator back to the file's native coordinates
# ---------------------------------------------------------------------------

class Unit:
    __slots__ = ("kind", "path", "container", "pointer", "text", "locs", "row_key")

    def __init__(self, kind: str, path: str, text: str, locs: list, container: Optional[dict] = None,
                 pointer: Optional[str] = None, row_key: Optional[str] = None):
        self.kind, self.path, self.container, self.pointer = kind, path, container, pointer
        self.text, self.locs, self.row_key = text, locs, row_key


def eml_units(path: Path, rel: str, warn: Counter) -> list[Unit]:
    raw = path.read_bytes()
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        warn["eml_not_utf8"] += 1
        s = raw.decode("utf-8", errors="replace")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    units: list[Unit] = []
    body = msg.get_body(preferencelist=("plain",))
    if body is None or body.get_content_type() != "text/plain":
        warn["eml_no_text_plain"] += 1
    else:
        content = body.get_content()
        if content.endswith("\n"):
            content = content[:-1]
        crlf = content.replace("\r\n", "\n").replace("\n", "\r\n")
        hend = s.find("\r\n\r\n")
        start = s.find(crlf, hend if hend >= 0 else 0) if crlf else -1
        if start < 0:
            warn["eml_body_not_located"] += 1
        else:
            chars: list[str] = []
            locs: list = []
            i, end = start, start + len(crlf)
            while i < end:
                if s[i] == "\r" and i + 1 < end and s[i + 1] == "\n":
                    chars.append("\n")
                    locs.append((i, i + 2))
                    i += 2
                else:
                    chars.append(s[i])
                    locs.append((i, i + 1))
                    i += 1
            units.append(Unit("eml", rel, "".join(chars), locs))
    for i, part in enumerate(msg.iter_attachments()):
        name = part.get_filename() or ""
        kind = DOC_EXT.get(Path(name).suffix.lower())
        if kind is None:
            warn["attachment_kind_unsupported"] += 1
            continue
        payload = part.get_payload(decode=True) or b""
        u = doc_unit(kind, rel, payload, warn,
                     container={"kind": "eml_attachment", "path": rel, "part_index": i, "filename": name})
        if u is not None:
            units.append(u)
    return units


def slack_units(slack_dir: Path, task_dir: Path, warn: Counter) -> list[Unit]:
    units: list[Unit] = []
    seen_files: set[str] = set()
    for cdir in ordered(p for p in slack_dir.iterdir() if p.is_dir()):
        for day in ordered(cdir.glob("*.json")):
            try:
                data = json.loads(day.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                warn["slack_day_unreadable"] += 1
                continue
            if not isinstance(data, list):
                continue
            rel = day.relative_to(task_dir).as_posix()
            for i, m in enumerate(data):
                if not isinstance(m, dict) or m.get("type") != "message":
                    continue
                text = m.get("text") or ""
                if text:
                    # offsets index the export's own (HTML-escaped) string, so the text is used as is
                    units.append(Unit("slack", rel, text, list(range(len(text))), pointer=f"/{i}/text"))
                for f in m.get("files") or []:
                    fid, name = f.get("id"), f.get("name")
                    if not fid or not name:
                        continue
                    local = cdir / "attachments" / f"{fid}-{name}"
                    lrel = local.relative_to(task_dir).as_posix()
                    if lrel in seen_files:
                        continue
                    seen_files.add(lrel)
                    if not local.is_file():
                        warn["slack_file_missing"] += 1
                        continue
                    kind = DOC_EXT.get(local.suffix.lower())
                    if kind is None:
                        warn["attachment_kind_unsupported"] += 1
                        continue
                    u = doc_unit(kind, lrel, local.read_bytes(), warn)
                    if u is not None:
                        units.append(u)
    return units


def drive_units(drive_dir: Path, task_dir: Path, warn: Counter) -> list[Unit]:
    units: list[Unit] = []
    for p in ordered(drive_dir.iterdir()):
        if not p.is_file() or p.name == "files.json":
            continue
        kind = DOC_EXT.get(p.suffix.lower())
        if kind is None:
            warn["drive_kind_unsupported"] += 1
            continue
        u = doc_unit(kind, p.relative_to(task_dir).as_posix(), p.read_bytes(), warn)
        if u is not None:
            units.append(u)
    return units


def doc_unit(kind: str, path: str, payload: bytes, warn: Counter, container: Optional[dict] = None) -> Optional[Unit]:
    try:
        if kind == "pdf":
            text, locs = pdf_text(payload)
        elif kind == "docx":
            text, locs = docx_text(payload)
        elif kind == "xlsx":
            text, locs = xlsx_text(payload)
        else:
            text, locs = csv_text(payload.decode("utf-8"))
    except Exception:  # noqa: BLE001
        warn[f"{kind}_unreadable"] += 1
        return None
    if not text.strip():
        warn[f"{kind}_empty"] += 1
        return None
    return Unit(kind, path, text, locs, container=container)


def pdf_text(payload: bytes) -> tuple[str, list]:
    import pdfplumber
    chars: list[str] = []
    locs: list = []
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        for page in pdf.pages:
            # v0.3 (S1): the product's shared reader functions; a wide gap between two words of one line is a
            # table cell boundary and becomes " | ", as the product reader writes it
            for line in D.pdf_page_lines(page, return_chars=True):
                prev = None
                for w in line:
                    if prev is not None:
                        for ch in D.pdf_word_separator(prev, w):
                            chars.append(ch)
                            locs.append(None)
                    prev = w
                    for c in w["chars"]:
                        # two decimals, as the answer key stores them: the scorer rounds both sides to one
                        # decimal, and a raw float (229.55000000000001) rounds away from the key's 229.55
                        tup = (c["text"], c["page_number"], round(c["x0"], 2), round(c["top"], 2),
                               round(c["x1"], 2), round(c["bottom"], 2))
                        for ch in c["text"]:
                            chars.append(ch)
                            locs.append(tup)
                chars.append("\n")
                locs.append(None)
            chars.append("\n")
            locs.append(None)
    return "".join(chars), locs


def _qname(el) -> Optional[str]:
    return "w:" + el.tag[len(W):] if el.tag.startswith(W) else None


def _children_paths(el, path: str):
    counts: Counter = Counter()
    for ch in el:
        q = _qname(ch)
        if q is None:
            continue  # drawings, text boxes, mc:AlternateContent: not part of the answer key's XPaths
        counts[q] += 1
        yield ch, q, f"{path}/{q}" + (f"[{counts[q]}]" if counts[q] > 1 else "")


_SKIP = {"w:pPr", "w:rPr", "w:tblPr", "w:tblGrid", "w:trPr", "w:tcPr", "w:sectPr", "w:del", "w:drawing",
         "w:pict", "w:object", "w:txbxContent", "w:instrText", "w:delText"}


def docx_text(payload: bytes) -> tuple[str, list]:
    chars: list[str] = []
    locs: list = []
    z = zipfile.ZipFile(io.BytesIO(payload))
    names = set(z.namelist())
    parts = ["word/document.xml"] + sorted(n for n in names if re.fullmatch(r"word/(header|footer)\d*\.xml", n))

    def put(s: str, loc=None) -> None:
        for ch in s:
            chars.append(ch)
            locs.append(loc)

    def run_content(el, path: str) -> None:
        for ch, q, cpath in _children_paths(el, path):
            if q in _SKIP:
                continue
            if q == "w:t":
                text = ch.text or ""
                for k, c in enumerate(text):
                    chars.append(c)
                    locs.append((cpath, k))
            elif q == "w:tab":
                put("\t")
            elif q in ("w:br", "w:cr"):
                put("\n")
            elif q == "w:noBreakHyphen":
                put("-")
            else:
                run_content(ch, cpath)

    def block(el, path: str, para_sep: str) -> None:
        first = True
        for ch, q, cpath in _children_paths(el, path):
            if q in _SKIP:
                continue
            if q == "w:p":
                if not first:
                    put(para_sep)
                first = False
                run_content(ch, cpath)
            elif q == "w:tbl":
                if not first:
                    put("\n")
                first = False
                rows = [(r, rp) for r, rq, rp in _children_paths(ch, cpath) if rq == "w:tr"]
                for ri, (tr, trp) in enumerate(rows):
                    if ri:
                        put("\n")
                    cells = [(c, cp) for c, cq, cp in _children_paths(tr, trp) if cq == "w:tc"]
                    for ci, (tc, tcp) in enumerate(cells):
                        if ci:
                            put(" | ")
                        block(tc, tcp, " ")
            else:
                block(ch, cpath, para_sep)

    for part in parts:
        if part not in names:
            continue
        root = ET.fromstring(z.read(part))
        rq = _qname(root)
        if rq is None:
            continue
        if chars:
            put("\n\n")
        if rq == "w:document":
            body = root.find(W + "body")
            if body is not None:
                block(body, f"/{rq}/w:body", "\n")
        else:
            block(root, f"/{rq}", "\n")
    return "".join(chars), locs


def xlsx_text(payload: bytes) -> tuple[str, list]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    chars: list[str] = []
    locs: list = []

    def put(s: str) -> None:
        for ch in s:
            chars.append(ch)
            locs.append(None)

    for ws in wb.worksheets:
        put(f"Sheet: {ws.title}\n")
        for row in ws.iter_rows():
            cells = [c for c in row if c.value is not None]
            if not cells:
                continue
            for ci, c in enumerate(cells):
                if ci:
                    put(" | ")
                v = c.value if isinstance(c.value, str) else str(c.value)
                for k, ch in enumerate(v):
                    chars.append(ch)
                    locs.append((ws.title, c.coordinate, k))
            put("\n")
    return "".join(chars), locs


def csv_text(text: str) -> tuple[str, list]:
    chars: list[str] = []
    locs: list = []
    for r, row in enumerate(csv.reader(io.StringIO(text, newline=""))):
        if r:
            chars.append("\n")
            locs.append(None)
        for c, val in enumerate(row):
            if c:
                chars.extend(" | ")
                locs.extend((None, None, None))
            for k, ch in enumerate(val):
                chars.append(ch)
                locs.append((r, c, k))
    return "".join(chars), locs


def load_units(task_dir: Path, warn: Counter) -> list[Unit]:
    units: list[Unit] = []
    email_dir = task_dir / "email"
    if email_dir.is_dir():
        for p in ordered(email_dir.rglob("*.eml")):
            units.extend(eml_units(p, p.relative_to(task_dir).as_posix(), warn))
    if (task_dir / "slack").is_dir():
        units.extend(slack_units(task_dir / "slack", task_dir, warn))
    if (task_dir / "drive").is_dir():
        units.extend(drive_units(task_dir / "drive", task_dir, warn))
    return units


# ---------------------------------------------------------------------------
# Shield spans -> benchmark spans
# ---------------------------------------------------------------------------

def recover_codes(original: str, masked: str, spans: list) -> list[Optional[str]]:
    """The code Shield wrote for each span, read back from the masked text (spans are in original offsets)."""
    codes: list[Optional[str]] = []
    p = o = 0
    for sp in spans:
        seg = original[o:sp.start]
        q = masked.find(seg, p) if seg else p
        if q < 0:
            codes.append(None)
            continue
        p = q + len(seg)
        m = CODE_AT.match(masked, p)
        if m:
            codes.append(m.group(1))
            p = m.end()
        else:
            codes.append(None)
        o = sp.end
    return codes


def _trim_token(tok: str, s: int) -> tuple[str, int]:
    while tok and not tok[0].isalnum():
        tok, s = tok[1:], s + 1
    while tok and not tok[-1].isalnum():
        tok = tok[:-1]
    if tok.lower().endswith(("'s", "’s")):
        tok = tok[:-2]
    return tok, s


class _Roles(dict):
    """Token -> roles, plus (v0.3) the masker and store that give the roles of one mention from its entity."""

    masker: Optional[Masker] = None
    store: Optional[MemoryStore] = None


def _positional_roles(store: MemoryStore) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = defaultdict(set)
    for e in store.all():
        if e.kind != "PERSON":
            continue
        toks = [normalize(_trim_token(m.group(), 0)[0]) for m in TOKEN_RE.finditer(e.value)]
        toks = [t for t in toks if t]
        if len(toks) >= 2:
            roles[toks[0]].add("given")
            roles[toks[-1]].add("family")
    return roles


def name_roles(store: MemoryStore, masker: Optional[Masker] = None) -> dict[str, set[str]]:
    """Token -> roles of the store's people. v0.3: from the engine (``Masker.name_roles``: the directory and the
    token roles of every stored full name) when the masker is given; else the R1 positional rule."""
    if masker is None:
        return _positional_roles(store)
    try:
        out = _Roles({k: set(v) for k, v in masker.name_roles().items()})
    except Exception:  # noqa: BLE001 - the adapter falls back to the positional split
        out = _Roles(_positional_roles(store))
    out.masker, out.store = masker, store
    return out


def _split_person_roles(text: str, start: int, roles: _Roles, code: Optional[str]) -> Optional[list[tuple[str, int, int]]]:
    """v0.3: (label, start, end) parts of a PERSON span from the engine's token roles (``Masker.person_roles``:
    the entity the code names, else the store, the directory, the "Last, First" order, the export's evidence).
    None when the engine gives nothing usable (the caller then splits by position)."""
    masker = roles.masker
    if masker is None:
        return None
    entity = None
    if code and roles.store is not None:
        try:
            entity = roles.store.get_by_code(code)
        except Exception:  # noqa: BLE001
            entity = None
        if entity is not None and entity.kind != "PERSON":
            entity = None
    try:
        pairs = masker.person_roles(text, entity)
    except Exception:  # noqa: BLE001
        return None
    if not pairs:
        return None
    labelled: list[tuple[str, int, int]] = []
    pos = 0
    for word, role in pairs:
        i = text.find(word, pos)
        if i < 0:
            return None
        s, e = start + i, start + i + len(word)
        pos = i + len(word)
        if role == "title":
            continue
        if role == "initial":
            role = "given"
        elif role == "particle":
            role = "family"
        elif role not in ("given", "family", "nick"):
            role = "given"
        tok, ts = _trim_token(text[i:i + len(word)], s)
        if not tok:
            continue
        labelled.append((role, ts, ts + len(tok)))
    if not labelled:
        return None
    # contiguous given tokens form one NAME_GIVEN span (the key tags middle names with the first name); every
    # quoted nickname is its own span; the family tokens form one NAME_FAMILY span
    out: list[tuple[str, int, int, str]] = []
    for role, s, e in labelled:
        label = "NAME_FAMILY" if role == "family" else "NAME_GIVEN"
        if out and role != "nick" and out[-1][3] != "nick" and out[-1][0] == label:
            out[-1] = (label, out[-1][1], e, role)
        else:
            out.append((label, s, e, role))
    return [(label, s, e) for label, s, e, _r in out]


def split_person(text: str, start: int, roles: dict[str, set[str]],
                 code: Optional[str] = None) -> list[tuple[str, int, int]]:
    """(label, start, end) parts of a PERSON span: the engine's token roles (v0.3) when ``roles`` carries the
    masker, else the benchmark baselines' split_name_span rule."""
    if isinstance(roles, _Roles):
        parts = _split_person_roles(text, start, roles, code)
        if parts:
            return parts
    toks: list[tuple[str, int]] = []
    for m in TOKEN_RE.finditer(text):
        tok, s = _trim_token(m.group(), start + m.start())
        if tok:
            toks.append((tok, s))
    if not toks:
        return []
    if len(toks) == 1:
        tok, s = toks[0]
        r = roles.get(normalize(tok), set())
        label = "NAME_FAMILY" if r == {"family"} else "NAME_GIVEN"
        return [(label, s, s + len(tok))]
    # NAME_GIVEN = every token but the last (the key tags middle names: "Aaron David" is one NAME_GIVEN span and
    # "David" alone is tagged too; a first-token-only span would cover 5/11 of "Aaron David" = a miss).
    # The benchmark baselines keep the first token only. NAME_FAMILY = the last token, as they do.
    (t0, s0), (tp, sp), (t1, s1) = toks[0], toks[-2], toks[-1]
    return [("NAME_GIVEN", s0, sp + len(tp)), ("NAME_FAMILY", s1, s1 + len(t1))]


def _split_fake_person(fake: str) -> dict[str, str]:
    """Synthetic mode: the given and family parts of a fake full name, for the two benchmark labels of a split
    PERSON span (the Synthesizer keeps the number of given names, so the parts align with the real name's)."""
    toks = [t for t in (_trim_token(m.group(), 0)[0] for m in TOKEN_RE.finditer(fake)) if t]
    if len(toks) < 2:
        return {}
    return {"NAME_GIVEN": " ".join(toks[:-1]), "NAME_FAMILY": toks[-1]}


def bench_spans(text: str, spans: list, codes: list[Optional[str]], roles: dict[str, set[str]],
                stats: Counter, synthetic: bool = False) -> list[dict]:
    """Benchmark-labelled spans (start, end, label, text, new_text) from Shield spans of one text.

    ``codes`` holds the code read back from the masked text (codes mode) or, with ``synthetic``, the fake value
    the masker wrote in place of the span (``MaskResult.replacements``)."""
    out: list[dict] = []
    for sp, code in zip(spans, codes):
        value = text[sp.start:sp.end]
        new_text = code or f"[{sp.kind}]"
        stats[f"kind:{sp.kind}"] += 1
        stats[f"source:{sp.source}"] += 1
        if code is None:
            stats["code_not_recovered"] += 1
        if sp.kind in ("PERSON", "ORG") and HANDLE_RE.match(value.strip()):
            out.append({"start": sp.start, "end": sp.end, "label": "USERNAME", "text": value, "new_text": new_text})
            continue
        if sp.kind == "PERSON":
            # v0.3: the code names the entity of the mention (its roles); in synthetic mode ``code`` is the fake
            # value, so the engine resolves the mention from its surface
            parts = split_person(value, sp.start, roles, None if synthetic else code)
            fake_parts = _split_fake_person(code) if synthetic and code and len(parts) == 2 else {}
            if synthetic and len(parts) == 2 and not fake_parts:
                stats["synthetic_name_not_split"] += 1
            for label, s, e in parts:
                out.append({"start": s, "end": e, "label": label, "text": text[s:e],
                            "new_text": fake_parts.get(label, new_text)})
            continue
        label = KIND_TO_LABEL.get(sp.kind, sp.kind)
        if sp.kind not in KIND_TO_LABEL:
            stats["out_of_scope_kind"] += 1
        out.append({"start": sp.start, "end": sp.end, "label": label, "text": value, "new_text": new_text})
    return out


def mask_unit(masker: Masker, text: str, stats: Counter, synthetic: bool = False,
              chat: Optional[bool] = None) -> dict[str, tuple[list, list]]:
    """One Masker.mask call (+ one Masker.scan call) -> {variant: (spans, codes)} in original offsets.

    ``mask``: the spans Masker.mask replaced, each with the code read back from the masked text (or, with
    ``synthetic``, the fake value written in place of the span: ``MaskResult.replacements``, aligned with its spans).
    ``canary``: the same plus the Masker.scan spans (registered values, valid identifiers) that overlap no
    mask span; those carry no code (new_text falls back to "[KIND]").
    ``chat`` (v0.4, T8): the unit is a chat message (a Slack message counts as chat text, PLAN 2.3 T2).
    """
    r = masker.mask(text, chat=chat)
    if synthetic:
        pairs = sorted(zip(r.spans, r.replacements), key=lambda t: (t[0].start, t[0].end))
        spans = [p[0] for p in pairs]
        codes: list[Optional[str]] = [p[1] or None for p in pairs]
        stats["synthetic_replacement_missing"] += sum(1 for c in codes if c is None)
    else:
        spans = sorted(r.spans, key=lambda s: (s.start, s.end))
        codes = recover_codes(text, r.text, spans)
    extra = [sc for sc in masker.scan(text, chat=chat) if not any(s.start < sc.end and sc.start < s.end for s in spans)]
    if not extra:
        return {"mask": (spans, codes), "canary": (spans, codes)}
    stats["canary_extra_spans"] += len(extra)
    pairs = list(zip(spans, codes)) + [(sc, None) for sc in extra]
    pairs.sort(key=lambda t: (t[0].start, t[0].end))
    return {"mask": (spans, codes), "canary": ([p[0] for p in pairs], [p[1] for p in pairs])}


# ---------------------------------------------------------------------------
# benchmark spans -> native locations
# ---------------------------------------------------------------------------

# v0.4 T1 (X2, K4, K8): the native report follows the span conventions of the v2.5 answer key (dataset card: a name
# is tagged token by token; "LOCATION_ADDRESS is now street-level only"). Only the way a masked span is REPORTED
# changes: the masked text, the codes and the human-file report (a text scorer with an any-overlap rule, whose
# annotators tag full addresses) stay as they were.
_ADDR_SEP = r"(?:,[ \t]*\n?[ \t]*|[ \t]*\n[ \t]*|[ \t]+\|[ \t]+)"
_ADDR_PLACE = r"[A-Z][A-Za-z.'’-]*(?:[ \t]+[A-Za-z.'’-]+){0,4}"
ADDR_LOCALITY_RE = re.compile(
    _ADDR_SEP + r"(?P<loc>"
    + _ADDR_PLACE + r",?[ \t]+[A-Z]{2}\.?[ \t]+\d{5}(?:-\d{4})?"                          # Town, ST 12345
    + r"|" + _ADDR_PLACE + r",[ \t]+[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?[ \t]+\d{5}(?:-\d{4})?"  # Town, State 12345
    + r"|" + _ADDR_PLACE + r",?[ \t]+[A-Z]{1,2}\d[A-Z\d]?[ \t]*\d[A-Z]{2}"                # Town, AB1 2CD
    + r")[ \t]*$")


def street_split(value: str) -> Optional[tuple[int, int]]:
    """v0.4 T1 (K8): (end of the street part, start of the locality part) of an address written as street (and
    unit), then town, state or region and postcode; None when the address has no such locality tail or no street
    part before it. The street part keeps its unit ("Suite 4", "Floor 2"); only the trailing town / state /
    postcode group is cut off."""
    m = ADDR_LOCALITY_RE.search(value)
    if m is None:
        return None
    street = value[:m.start()].rstrip(" \t\n,")
    if len(street) < 3 or not any(ch.isalpha() for ch in street):
        return None
    return len(street), m.start("loc")


def pdf_line_boxes(glyphs: list) -> list[dict]:
    """v0.4 T1 (X1): the merged per-line boxes of a PDF span, from its own glyphs in reading order
    (``[char, page, x0, top, x1, bottom]``, pdfplumber conventions). A new box starts on another page, when the
    next glyph's vertical centre leaves the current line, or when it goes back to the left (a wrapped line, another
    column); so every box holds one left-to-right run of the span's glyphs on one line."""
    boxes: list[dict] = []
    cur: Optional[dict] = None
    prev_x1 = 0.0
    for g in glyphs:
        page, x0, top, x1, bottom = g[1], float(g[2]), float(g[3]), float(g[4]), float(g[5])
        cy = (top + bottom) / 2
        if cur is None or page != cur["page"] or not (cur["top"] <= cy <= cur["bottom"]) or x0 < prev_x1 - 1.0:
            cur = {"page": page, "x0": x0, "x1": x1, "top": top, "bottom": bottom}
            boxes.append(cur)
        else:
            cur["x0"], cur["x1"] = min(cur["x0"], x0), max(cur["x1"], x1)
            cur["top"], cur["bottom"] = min(cur["top"], top), max(cur["bottom"], bottom)
        prev_x1 = x1
    return boxes


def _name_tokens(text: str, s: int, e: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for m in TOKEN_RE.finditer(text, s, e):
        tok, ts = _trim_token(m.group(), m.start())
        if tok:
            out.append((ts, ts + len(tok)))
    return out


def native_report(text: str, bs: list[dict], stats: Optional[Counter] = None) -> list[dict]:
    """v0.4 T1: the benchmark spans of one text as the native report writes them. A NAME_GIVEN or NAME_FAMILY span
    of several tokens gives one span per token (X2, K4: the DOCX scorer has no containment rule); a
    LOCATION_ADDRESS span with a town / state / postcode tail gives a street-level span and a locality span (K8).
    Each part keeps the span's code; in synthetic mode it gets the matching part of the fake value when the fake
    splits the same way, else the whole fake value."""
    out: list[dict] = []
    for b in bs:
        if b["label"] in ("NAME_GIVEN", "NAME_FAMILY"):
            toks = _name_tokens(text, b["start"], b["end"])
            if len(toks) > 1:
                words = (b["new_text"] or "").split()
                news = words if len(words) == len(toks) else [b["new_text"]] * len(toks)
                for (s, e), nt in zip(toks, news):
                    out.append({**b, "start": s, "end": e, "text": text[s:e], "new_text": nt})
                if stats is not None:
                    stats["t1_name_token_split"] += 1
                continue
        elif b["label"] == "LOCATION_ADDRESS":
            cut = street_split(text[b["start"]:b["end"]])
            if cut is not None:
                street_len, loc_off = cut
                nt = b["new_text"] or ""
                fcut = street_split(nt)
                new_street, new_loc = (nt[:fcut[0]], nt[fcut[1]:]) if fcut else (nt, nt)
                s0, s1 = b["start"], b["start"] + street_len
                l0 = b["start"] + loc_off
                out.append({**b, "start": s0, "end": s1, "text": text[s0:s1], "new_text": new_street})
                out.append({**b, "start": l0, "end": b["end"], "text": text[l0:b["end"]], "new_text": new_loc})
                if stats is not None:
                    stats["t1_address_split"] += 1
                continue
        out.append(b)
    return out


def native_locations(u: Unit, s: int, e: int, pdf_boxes: bool = False) -> list[dict]:
    """Native location(s) of the text range [s, e) of a unit. A PDF range is written per glyph (``chars``, the
    answer key's own format, which the holdout builder writes as gold) unless ``pdf_boxes`` (v0.4 T1: the
    prediction writer reports merged per-line ``boxes``)."""
    locs = u.locs
    if u.kind == "eml":
        return [{"kind": "eml", "file_char_start": locs[s][0], "file_char_end": locs[e - 1][1]}]
    if u.kind == "slack":
        return [{"kind": "slack", "json_pointer": u.pointer, "start": s, "end": e}]
    if u.kind == "pdf":
        chars = []
        for i in range(s, e):
            t = locs[i]
            if t is not None and (not chars or chars[-1] is not t):
                chars.append(t)
        if not chars:
            return []
        if not pdf_boxes:
            return [{"kind": "pdf", "pages": sorted({c[1] for c in chars}), "chars": [list(c) for c in chars]}]
        # v0.4 T1 (X1): the span is reported as merged per-line ``boxes`` (the README's second PDF format, the one
        # the answer key itself carries), so a span that contains the gold span covers it, as in eml and csv. The
        # per-glyph list moves to ``glyphs``: the scorer reads only ``chars`` or ``boxes``; the leak check and
        # recheck_v02 read ``glyphs`` for the glyph positions
        return [{"kind": "pdf", "pages": sorted({c[1] for c in chars}), "boxes": pdf_line_boxes(chars),
                 "glyphs": [list(c) for c in chars]}]
    if u.kind == "docx":
        frags: list[dict] = []
        for i in range(s, e):
            t = locs[i]
            if t is None:
                continue
            xpath, k = t
            if frags and frags[-1]["xpath"] == xpath and frags[-1]["end"] == k:
                frags[-1]["end"] = k + 1
            else:
                frags.append({"xpath": xpath, "start": k, "end": k + 1})
        return [{"kind": "docx", "fragments": frags}] if frags else []
    # xlsx / csv: one location per cell the span touches
    out: list[dict] = []
    for i in range(s, e):
        t = locs[i]
        if t is None:
            continue
        if u.kind == "xlsx":
            sheet, cell, k = t
            if out and out[-1]["sheet"] == sheet and out[-1]["cell"] == cell and out[-1]["char_end"] == k:
                out[-1]["char_end"] = k + 1
            else:
                out.append({"kind": "xlsx", "sheet": sheet, "cell": cell, "char_start": k, "char_end": k + 1})
        else:
            r, c, k = t
            if out and out[-1]["row"] == r and out[-1]["col"] == c and out[-1]["value_char_end"] == k:
                out[-1]["value_char_end"] = k + 1
            else:
                out.append({"kind": "csv", "row": r, "col": c, "value_char_start": k, "value_char_end": k + 1})
    return out


# ---------------------------------------------------------------------------
# one export
# ---------------------------------------------------------------------------

def run_set(name: str, do_native: bool, do_human: bool) -> dict:
    t_start = time.time()
    warn: Counter = Counter()
    stats: dict[str, Counter] = {v: Counter() for v in VARIANTS}
    meta: dict[str, Any] = {"set": name, "warnings": warn, "stats": stats, "timings": {}, "counts": {}}
    try:
        if do_native:
            _run_native(name, warn, stats, meta)
        if do_human:
            _run_human(name, warn, stats, meta)
    except Exception:  # noqa: BLE001
        meta["error"] = traceback.format_exc()
    meta["timings"]["total"] = round(time.time() - t_start, 2)
    meta["warnings"] = dict(warn)
    meta["stats"] = {v: dict(c) for v, c in stats.items()}
    return meta


def _use_directory() -> bool:
    return _os.environ.get("RAGBASE_SHIELD_PB_DIRECTORY", "1") != "0"


def build_directory(task_dir: Path):
    """v0.3 (S3): the dossier directory of one export, from the same items ``Service._build_directory`` reads
    (the e-mails, the Slack ``users.json``, the Word documents). None when the flag is off or nothing is found."""
    if not _use_directory():
        return None
    items: list = []
    email_dir = task_dir / "email"
    if email_dir.is_dir():
        items.extend(ordered(email_dir.rglob("*.eml")))
    items.extend(ordered(task_dir.rglob("users.json")))
    drive = task_dir / "drive"
    if drive.is_dir():
        items.extend(ordered(drive.rglob("*.docx")))
    d = dr.build(items, lang="auto")
    return d if d else None


_DIRECTORY: dict[str, Any] = {}  # set name -> directory built by _run_native (the human path of the same set reads it)


def _make_masker(store: MemoryStore, directory, *, replacement: str = "codes") -> Masker:
    if directory is not None:
        return Masker(store, locale=LOCALE, use_ner=_use_ner(), language=_language(), replacement=replacement,
                      directory=directory)
    return Masker(store, locale=LOCALE, use_ner=_use_ner(), language=_language(), replacement=replacement)


def _run_native(name: str, warn: Counter, stats: dict[str, Counter], meta: dict) -> None:
    task_dir = DATA / "tasks" / name
    t0 = time.time()
    units = load_units(task_dir, warn)
    meta["timings"]["extract"] = round(time.time() - t0, 2)
    meta["counts"]["units"] = dict(Counter(u.kind for u in units))
    chars_by_kind: Counter = Counter()
    for u in units:
        chars_by_kind[u.kind] += len(u.text)
    meta["counts"]["chars"] = dict(chars_by_kind)
    t0 = time.time()
    try:
        directory = build_directory(task_dir)
    except Exception:  # noqa: BLE001 - the directory is an aid: the run goes on without it
        warn["directory_failed"] += 1
        directory = None
    _DIRECTORY[name] = directory
    meta["timings"]["directory"] = round(time.time() - t0, 2)
    meta["counts"]["directory_persons"] = len(directory) if directory is not None else 0
    meta["counts"]["directory_domains"] = len(directory.domains) if directory is not None else 0

    _native_passes(name, units, PRED, stats, meta, tag="", synthetic=False, directory=directory)
    if _synthetic():
        # an independent run of the same export in synthetic replacement mode: fresh store, same two passes
        syn_stats: dict[str, Counter] = {v: Counter() for v in VARIANTS}
        _native_passes(name, units, SYN_PRED, syn_stats, meta, tag="_synthetic", synthetic=True, directory=directory)
        meta["stats_synthetic"] = {v: dict(c) for v, c in syn_stats.items()}


def _chat_of(u) -> Optional[bool]:
    """v0.4 (T8): a Slack message is chat text (``chat=True``, PLAN 2.3 T2); every other unit is read from its own
    shape (``None``), as before T8."""
    return True if u.kind == "slack" else None


def _native_passes(name: str, units: list, pred_root: Path, stats: dict[str, Counter], meta: dict, *,
                   tag: str, synthetic: bool, directory=None) -> None:
    store = MemoryStore(locale=LOCALE)
    # v0.3 (synthetic leak fix, PLAN 5.1): in synthetic mode pass 1 registers the export in codes mode and the
    # fakes are drawn in pass 2 only (``Service._scan`` does the same for a synthetic dossier)
    masker = _make_masker(store, directory, replacement="codes")
    # pass 1: register the entities of the whole export (Shield's add_dossier scan)
    t0 = time.time()
    for u in units:
        masker.mask(u.text, chat=_chat_of(u))  # v0.4 (T8): a Slack message is chat text
    meta["timings"]["pass1" + tag] = round(time.time() - t0, 2)
    meta["counts"]["entities_after_pass1" + tag] = dict(Counter(e.kind for e in store.all()))
    if synthetic:
        masker.replacement = "synthetic"
        meta["register_first"] = True
    meta["masker_mode" + tag] = masker.mode
    # pass 2: the spans
    t0 = time.time()
    files = {v: (pred_root / v / f"{name}.jsonl") for v in VARIANTS}
    for f in files.values():
        f.parent.mkdir(parents=True, exist_ok=True)
    handles = {v: f.open("w", encoding="utf-8", newline="\n") for v, f in files.items()}  # "\n" on Windows too
    rev = None
    roles: dict[str, set[str]] = {}
    pred_counts = {v: Counter() for v in VARIANTS}
    try:
        for u in units:
            if store.revision != rev:
                roles, rev = name_roles(store, masker), store.revision
            variants = mask_unit(masker, u.text, stats["canary"], synthetic=synthetic, chat=_chat_of(u))
            for v, (spans, codes) in variants.items():
                bs = bench_spans(u.text, spans, codes, roles, stats[v], synthetic=synthetic)
                bs = native_report(u.text, bs, stats[v])  # v0.4 T1: the answer key's span conventions
                out_spans = []
                for b in bs:
                    for loc in native_locations(u, b["start"], b["end"], pdf_boxes=True):
                        out_spans.append({"label": b["label"], "text": b["text"], "new_text": b["new_text"], "location": loc})
                pred_counts[v][u.kind] += len(out_spans)
                row = {"file": {"kind": u.kind, "path": u.path, "container": u.container}, "spans": out_spans}
                handles[v].write(json.dumps(row, ensure_ascii=False) + "\n")
    finally:
        for h in handles.values():
            h.close()
    meta["timings"]["pass2" + tag] = round(time.time() - t0, 2)
    meta["counts"]["entities_after_pass2" + tag] = dict(Counter(e.kind for e in store.all()))
    meta["counts"]["predicted_spans" + tag] = {v: dict(c) for v, c in pred_counts.items()}
    meta["counts"]["store_entities" + tag] = len(store.all())
    if synthetic:
        try:
            coll = masker.synthesizer().collisions
            meta["counts"]["synthetic_collisions"] = dict(coll) if isinstance(coll, dict) else coll
        except Exception:  # noqa: BLE001
            pass
    try:
        c = _ner._SHARED_CACHE
        meta["counts"]["ner_cache" + tag] = {"hits": c.hits, "misses": c.misses, "items": len(c)}
    except Exception:  # noqa: BLE001
        pass


def _run_human(name: str, warn: Counter, stats: dict[str, Counter], meta: dict) -> None:
    files = [DATA / "human_annotations" / f"{name}.jsonl", DATA / "human_annotations" / f"{name}_documents.jsonl"]
    rows: list[tuple[str, str, bool]] = []  # (row_key, text, is_message_file)
    for f in files:
        if not f.exists():
            continue
        is_msg = not f.name.endswith("_documents.jsonl")
        for line in f.open(encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            m = r.get("meta") or {}
            rid = r.get("row_id") or m.get("row_id") or m.get("cell_id")
            page = r.get("page") if r.get("page") is not None else m.get("page")
            key = f"{rid}#p{page}" if page is not None else str(rid)
            # v0.4 (T8): a message row addressed to a channel is a Slack message, which counts as chat text; any
            # other row is read from its own shape (None), as before T8
            chat = True if is_msg and any(isinstance(t, dict) and t.get("channel_id")
                                          for t in (m.get("to") or [])) else None
            rows.append((key, r.get("text") or "", is_msg, f.name, chat))
    if not rows:
        return
    store = MemoryStore(locale=LOCALE)
    # v0.3: the same export, the same directory as the native run of this set (built there; None when the human
    # files are run alone)
    masker = _make_masker(store, _DIRECTORY.get(name))
    meta["counts"]["human_directory_persons"] = len(_DIRECTORY.get(name) or ())
    t0 = time.time()
    for _, text, _, _, chat in rows:
        masker.mask(text, chat=chat)
    meta["timings"]["human_pass1"] = round(time.time() - t0, 2)
    t0 = time.time()
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    rev, roles = None, {}
    hstats = {v: Counter() for v in VARIANTS}
    for key, text, is_msg, fname, chat in rows:
        if store.revision != rev:
            roles, rev = name_roles(store, masker), store.revision
        for v, (spans, codes) in mask_unit(masker, text, hstats["canary"], chat=chat).items():
            bs = bench_spans(text, spans, codes, roles, hstats[v])
            if is_msg:  # the message files are annotated with the five original labels only (as the baselines)
                dropped = [b for b in bs if b["label"] not in MESSAGE_LABELS]
                hstats[v]["message_spans_outside_5_labels"] += len(dropped)
                bs = [b for b in bs if b["label"] in MESSAGE_LABELS]
            out[(v, fname)].append({"row_id": key, "entities": bs})
    meta["timings"]["human_pass2"] = round(time.time() - t0, 2)
    meta["human_stats"] = {v: dict(c) for v, c in hstats.items()}
    meta["counts"]["human_rows"] = len(rows)
    meta["counts"]["human_chars"] = sum(len(t) for _, t, _, _, _ in rows)
    for (v, fname), lines in out.items():
        p = NER_PRED / v / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="\n") as h:
            for row in lines:
                h.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", default=None, help="comma-separated set names (default: all 21)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--skip-native", action="store_true")
    ap.add_argument("--skip-human", action="store_true")
    ap.add_argument("--ner", choices=("off", "auto"), default="off")
    ap.add_argument("--language", choices=("auto", "en"), default="auto")
    ap.add_argument("--out", default="", help="sub-folder of .bench_data/public/privacybench for this run's outputs")
    ap.add_argument("--synthetic", action="store_true", help="also run every export in synthetic replacement mode")
    args = ap.parse_args()
    _os.environ["RAGBASE_SHIELD_NER"] = args.ner
    _os.environ["RAGBASE_SHIELD_LANGUAGE"] = args.language
    _os.environ["RAGBASE_SHIELD_PB_OUT"] = args.out
    _os.environ["RAGBASE_SHIELD_PB_SYNTHETIC"] = "1" if args.synthetic else "0"
    global PRED, NER_PRED, SYN_PRED
    PRED, NER_PRED, SYN_PRED = _out_dir() / "predictions", _out_dir() / "ner_predictions", _out_dir() / "predictions_synthetic"
    if not (DATA / "tasks").is_dir():
        sys.exit(f"missing {DATA}/tasks: run download.py first")
    sets = args.sets.split(",") if args.sets else sorted(p.name for p in (DATA / "tasks").iterdir() if p.is_dir())
    human_sets = {p.name[:-6] for p in (DATA / "human_annotations").glob("*.jsonl") if not p.name.endswith("_documents.jsonl")}
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_set, s, not args.skip_native, (not args.skip_human) and s in human_sets): s for s in sets}
        for fut in futs:
            m = fut.result()
            results.append(m)
            print(json.dumps({"set": m["set"], "timings": m["timings"], "units": m["counts"].get("units"),
                              "warnings": m["warnings"], "error": bool(m.get("error"))}), flush=True)
    import pdfplumber, openpyxl  # noqa: E401  (versions for the record)
    meta = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "shield_commit": git("rev-parse", "HEAD"), "shield_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "shield_src_dirty": bool(git("status", "--porcelain", "--", "src")),
        "python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
        "pdfplumber": pdfplumber.__version__, "openpyxl": openpyxl.__version__,
        "locale": LOCALE, "use_ner": args.ner, "language": args.language,
        "ner_threads": _os.environ.get("RAGBASE_SHIELD_NER_THREADS", "0 (library default)"),
        "out": args.out, "synthetic": args.synthetic,
        "directory": _use_directory(), "register_first": args.synthetic, "roles": "engine",
        "masker_mode": Masker(MemoryStore(locale=LOCALE), locale=LOCALE, use_ner=_use_ner()).mode,
        "variants": list(VARIANTS), "workers": args.workers,
        "wall_seconds": round(time.time() - t0, 1), "sets": results,
    }
    _out_dir().mkdir(parents=True, exist_ok=True)
    (_out_dir() / "run_meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    errors = [m["set"] for m in results if m.get("error")]
    print(f"done in {meta['wall_seconds']} s, {len(results)} sets, errors: {errors or 'none'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
