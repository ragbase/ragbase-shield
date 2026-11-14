"""Fixed readers for the benchmark: turn an input file or a tool's output file into plain text.

The SAME reader reads the input file and every tool's output file, so the scorer compares like with like. The
answer keys give character positions in the text of this reader: the readers and the versions of their libraries
are fixed.

Formats and rules:

- ``.txt``  bytes; a UTF-8 BOM is dropped; decoded as UTF-8, or as cp1252 when UTF-8 fails (recorded in the
            meta as ``encoding``). "\r\n" and "\r" become "\n".
- ``.docx`` standard library only (zipfile + ElementTree). Parts in this fixed order: core properties
            (docProps/core.xml), app properties (docProps/app.xml: Company, Manager), custom properties
            (docProps/custom.xml), headers (word/header*.xml, by number), body (word/document.xml), footnotes,
            endnotes, footers (word/footer*.xml, by number), comments (word/comments.xml), then one line per
            distinct ``w:author`` attribute (tracked changes and comments), then the external link targets of
            every part (``_rels``, TargetMode="External", for example ``mailto:``). In a part: each ``w:p`` ends
            with "\n"; ``w:t`` and ``w:delText`` (text of tracked deletions, which stays in the file) give text;
            ``w:tab`` gives "\t"; ``w:br`` and ``w:cr`` give "\n"; ``w:noBreakHyphen`` gives "-". Table cells are
            paragraphs, so each cell paragraph is a line.
- ``.pdf``  pdfplumber 0.11.10 (pdfminer.six 20260107): metadata first (Title, Author, Subject, Keywords,
            Creator), one line each, then each page's ``extract_text()`` with the default settings, pages joined
            by "\n\n", then the ``contents`` of the page annotations, one line each.
- ``.xlsx`` openpyxl 3.1.2, ``load_workbook(data_only=True)``: core properties (creator, lastModifiedBy,
            title, subject, keywords, description), then per sheet in workbook order a line "== <title>", then
            one line per row with at least one value: ``str(value)`` of the non-empty cells joined by " | ",
            then the cell comments of the sheet ("<author>: <text>").

Reader record (``--meta``): ``hidden_ranges`` = the character ranges of the text that come from tracked deletions
(``w:delText``) of a .docx (the scorer reports gold and keep items there apart, as "hidden" content, like
document properties); ``image_only`` = a .pdf whose pages carry images but no letter or digit in their text layer
(the scorer then marks the output "unscorable", not "failed").

Anything else (.eml, .html, .md, scans, encrypted PDFs) is not read.

Usage: python extract_text.py FILE [--meta]   (prints the text; --meta prints the reader record as JSON)
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

READER_VERSION = "laptop-extract-1.1"  # written in each reader record
EXPECTED_LIBS = {"pdfplumber": "0.11.10", "pdfminer.six": "20260107", "openpyxl": "3.1.2"}

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
EP = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
CUSTOM = "{http://schemas.openxmlformats.org/officeDocument/2006/custom-properties}"

SUPPORTED = (".txt", ".docx", ".pdf", ".xlsx")


def lib_versions() -> dict:
    out = {}
    try:
        from importlib.metadata import version
        for name in ("pdfplumber", "pdfminer.six", "openpyxl"):
            try:
                out[name] = version(name)
            except Exception:  # noqa: BLE001
                out[name] = None
    except Exception:  # noqa: BLE001
        pass
    return out


def check_versions() -> list[str]:
    """Differences from the pinned reader libraries (empty list = the pinned versions)."""
    got = lib_versions()
    return [f"{k}: expected {v}, found {got.get(k)}" for k, v in EXPECTED_LIBS.items() if got.get(k) != v]


# ------------------------------------------------------------------------------------------------ txt
def read_txt(path: Path) -> tuple[str, dict]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text, enc = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("cp1252", errors="replace"), "cp1252"
    return text.replace("\r\n", "\n").replace("\r", "\n"), {"encoding": enc}


# ------------------------------------------------------------------------------------------------ docx
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _walk(el: ET.Element, out: list[str], hidden: list[int] | None = None) -> None:
    """Text of ``el`` without descending into nested paragraphs (read as their own lines) or into the
    ``mc:Fallback`` copy of a text box (the ``mc:Choice`` copy is read). ``hidden`` collects the indexes in ``out``
    of tracked-deletion text."""
    for child in el:
        tag = child.tag
        if tag == W + "p" or tag == MC_FALLBACK:
            continue
        if tag in (W + "t", W + "delText"):
            if tag == W + "delText" and hidden is not None and child.text:
                hidden.append(len(out))
            out.append(child.text or "")
        elif tag == W + "tab":
            out.append("\t")
        elif tag in (W + "br", W + "cr"):
            out.append("\n")
        elif tag == W + "noBreakHyphen":
            out.append("-")
        else:
            _walk(child, out, hidden)


def _part_text(xml: bytes) -> str:
    return _part_text_ranges(xml)[0]


def _part_text_ranges(xml: bytes) -> tuple[str, list[tuple[int, int]]]:
    """Text of a part and the ranges (relative to the part text) of its tracked-deletion text."""
    root = ET.fromstring(xml)
    parent = {c: p for p in root.iter() for c in p}

    def in_fallback(el: ET.Element) -> bool:
        while el in parent:
            el = parent[el]
            if el.tag == MC_FALLBACK:
                return True
        return False

    lines: list[str] = []
    ranges: list[tuple[int, int]] = []
    pos = 0
    for p in root.iter(W + "p"):  # document order; a text-box paragraph follows its host paragraph
        if in_fallback(p):
            continue
        out: list[str] = []
        hid: list[int] = []
        _walk(p, out, hid)
        off = pos
        for k, piece in enumerate(out):
            if k in hid:
                ranges.append((off, off + len(piece)))
            off += len(piece)
        line = "".join(out)
        lines.append(line)
        pos += len(line) + 1
    return "\n".join(lines) + ("\n" if lines else ""), ranges


def _numbered(names: list[str], prefix: str) -> list[str]:
    def key(n: str) -> tuple[int, str]:
        m = re.search(r"(\d+)\.xml$", n)
        return (int(m.group(1)) if m else 0, n)
    return sorted((n for n in names if n.startswith(prefix) and n.endswith(".xml")), key=key)


def read_docx(path: Path) -> tuple[str, dict]:
    blocks: list[str] = []
    hidden: list[tuple[int, int]] = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "docProps/core.xml" in names:
            root = ET.fromstring(z.read("docProps/core.xml"))
            for tag, label in ((DC + "title", "title"), (DC + "subject", "subject"), (DC + "creator", "creator"),
                               (CP + "keywords", "keywords"), (DC + "description", "description"),
                               (CP + "lastModifiedBy", "lastModifiedBy"), (CP + "category", "category")):
                el = root.find(tag)
                if el is not None and (el.text or "").strip():
                    blocks.append(f"{label}: {el.text}\n")
        if "docProps/app.xml" in names:
            root = ET.fromstring(z.read("docProps/app.xml"))
            for tag, label in ((EP + "Company", "company"), (EP + "Manager", "manager")):
                el = root.find(tag)
                if el is not None and (el.text or "").strip():
                    blocks.append(f"{label}: {el.text}\n")
        if "docProps/custom.xml" in names:
            root = ET.fromstring(z.read("docProps/custom.xml"))
            for prop in root.findall(CUSTOM + "property"):
                val = "".join(t for t in prop.itertext()).strip()
                if val:
                    blocks.append(f"{prop.get('name')}: {val}\n")
        parts = (_numbered(names, "word/header") + ["word/document.xml", "word/footnotes.xml", "word/endnotes.xml"]
                 + _numbered(names, "word/footer") + ["word/comments.xml"])
        authors: list[str] = []
        links: list[str] = []
        for part in parts:
            if part not in names:
                continue
            xml = z.read(part)
            base = sum(len(b) for b in blocks)
            ptext, pranges = _part_text_ranges(xml)
            hidden += [(base + a, base + b) for a, b in pranges]
            blocks.append(ptext)
            for el in ET.fromstring(xml).iter():
                a = el.get(W + "author")
                if a and a not in authors:
                    authors.append(a)
            rels = part.replace("word/", "word/_rels/") + ".rels"
            if rels in names:
                for r in ET.fromstring(z.read(rels)).iter(REL + "Relationship"):
                    if r.get("TargetMode") == "External" and r.get("Target") not in links:
                        links.append(r.get("Target"))
        for a in authors:
            blocks.append(f"author: {a}\n")
        for t in links:
            blocks.append(f"link: {t}\n")
    return "".join(blocks), {"hidden_ranges": hidden}


# ------------------------------------------------------------------------------------------------ pdf
def read_pdf(path: Path) -> tuple[str, dict]:
    import pdfplumber  # pinned 0.11.10

    out: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        meta = pdf.metadata or {}
        for key in ("Title", "Author", "Subject", "Keywords", "Creator"):
            v = meta.get(key)
            if isinstance(v, bytes):
                v = v.decode("utf-8", errors="replace")
            if v and str(v).strip():
                out.append(f"{key.lower()}: {v}\n")
        pages = [(p.extract_text() or "") for p in pdf.pages]
        out.append("\n\n".join(pages) + "\n")
        alnum = sum(1 for pg in pages for c in pg if c.isalnum())
        images = sum(len(p.images) for p in pdf.pages)
        for p in pdf.pages:
            for a in p.annots or ():
                c = a.get("contents")
                if c and str(c).strip():
                    out.append(f"annotation: {c}\n")
        n_pages = len(pdf.pages)
    return "".join(out), {"pages": n_pages, "text_alnum": alnum, "images": images,
                          "image_only": bool(n_pages and alnum == 0 and images > 0)}


# ------------------------------------------------------------------------------------------------ xlsx
def read_xlsx(path: Path) -> tuple[str, dict]:
    import warnings

    import openpyxl  # pinned 3.1.2

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # "Workbook contains no default style": cosmetic, not a reading change
        wb = openpyxl.load_workbook(str(path), data_only=True)
    out: list[str] = []
    pr = wb.properties
    for label in ("creator", "lastModifiedBy", "title", "subject", "keywords", "description"):
        v = getattr(pr, label, None)
        if v and str(v).strip():
            out.append(f"{label}: {v}\n")
    for ws in wb.worksheets:
        out.append(f"== {ws.title}\n")
        comments = []
        for row in ws.iter_rows():
            vals = [str(c.value) for c in row if c.value is not None and str(c.value) != ""]
            if vals:
                out.append(" | ".join(vals) + "\n")
            for c in row:
                if c.comment is not None:
                    comments.append(f"{c.comment.author or ''}: {c.comment.text}\n")
        out.extend(comments)
    return "".join(out), {"sheets": len(wb.worksheets)}


def extract(path: str | Path) -> tuple[str, dict]:
    """(text, meta). Raises ValueError for a format that is not read."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".txt":
        text, meta = read_txt(p)
    elif ext == ".docx":
        text, meta = read_docx(p)
    elif ext == ".pdf":
        text, meta = read_pdf(p)
    elif ext == ".xlsx":
        text, meta = read_xlsx(p)
    else:
        raise ValueError(f"format not read: {ext}")
    meta = dict(meta, reader=READER_VERSION, format=ext.lstrip("."))
    return text, meta


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    text, meta = extract(argv[0])
    if "--meta" in argv:
        print(json.dumps(dict(meta, chars=len(text), libs=lib_versions(), version_check=check_versions()),
                         ensure_ascii=False, indent=1))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
