"""Synthetic test documents for the long-PDF and background-reading tests (round 9). Invented content only.

``make_long_pdf`` writes a PDF in raw PDF syntax (no new dependency: zlib from the standard library): every page has a
paragraph of prose written in many small text pieces and a ruled table (one rectangle per cell), like the court and
accounting exports that made the 0.4.2 reader slow (about 550 text operators and 160 rectangles per page). Invented
names sit on some pages, and one name appears only near the end, so a test can check that a name found late is also
hidden in what was read before. ``make_dossier`` adds 26 small invented files around it.
"""
from __future__ import annotations

import zlib
from pathlib import Path
from typing import Optional

#: Invented names (no real person or company).
PERSON_EARLY = "Ysaline Corbaz-Thévenet"
COMPANY = "Brévanne Logistique SAS"
PERSON_LATE = "Aurélien Kerbrat-Lussac"

_WORDS = ("le prestataire livre les marchandises au client dans un délai de trente jours à compter de la commande "
          "écrite ; toute réserve est notée sur le bon de livraison et confirmée par lettre recommandée dans les "
          "trois jours ouvrés suivant la réception des colis au dépôt principal").split()
_LABELS = ("Livraison", "Facture", "Avoir", "Relance", "Transport", "Stockage", "Emballage", "Retour")


def _esc(text: str) -> bytes:
    return text.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _page_stream(n: int, pages: int, rows: int = 38, cols: int = 4, line_pieces: int = 10,
                 lines: int = 10) -> bytes:
    """Content of page ``n`` (1-based)."""
    ops: list[bytes] = []
    # paragraph: ``lines`` lines, each written as ``line_pieces`` text pieces placed one after the other
    ops.append(b"BT /F1 9 Tf")
    y = 800
    for li in range(lines):
        x = 40.0
        words = [_WORDS[(n * 7 + li * 5 + k) % len(_WORDS)] for k in range(line_pieces + 4)]
        if li == 0:
            words[:2] = ["Page", str(n)]
        if li == 2 and (n == 1 or n % 50 == 0):
            words[:4] = ["Mme", *PERSON_EARLY.split(), "déclare"]
        if li == 3 and n == pages - 10:
            words[:4] = ["M.", *PERSON_LATE.split(), "signe"]
        for k in range(line_pieces):
            piece = words[k] + " "
            ops.append(b"1 0 0 1 %.1f %d Tm (%s) Tj" % (x, y, _esc(piece)))
            x += len(piece) * 4.9
        y -= 11
    ops.append(b"ET")
    # ruled table: one rectangle per cell, three text pieces per cell
    top = y - 8
    widths = (60, 150, 130, 175)[:cols]
    row_h = 16
    ops.append(b"0.5 w")
    for r in range(rows):
        yy = top - (r + 1) * row_h
        x = 40
        for c in range(cols):
            ops.append(b"%d %d %d %d re S" % (x, yy, widths[c], row_h))
            x += widths[c]
    ops.append(b"BT /F1 7 Tf")
    for r in range(rows):
        yy = top - (r + 1) * row_h + 5
        x = 40
        k = n * rows + r
        cells = (
            ("L", str(k % 997), "A"),
            (_LABELS[k % len(_LABELS)], "n°", f"{k % 9000 + 1000}"),
            (f"{(k * 37) % 9999},{k % 100:02d}", "EUR", "HT"),
            ((COMPANY if (r == 5 and n % 25 == 0) else "Dépôt"), "quai", str(r + 1)),
        )[:cols]
        for c, pieces in enumerate(cells):
            px = x + 3
            for piece in pieces:
                ops.append(b"1 0 0 1 %.1f %d Tm (%s) Tj" % (px, yy, _esc(piece)))
                px += (len(piece) + 1) * 4.2
            x += widths[c]
    ops.append(b"ET")
    for j in range(15):  # thin rules in the bottom margin (no cell: horizontal only)
        ops.append(b"40 %d 515 0.4 re f" % (12 + 2 * j))
    return b"\n".join(ops)


def make_long_pdf(path: Path, pages: int = 800, *, compress: bool = True, **layout) -> Path:
    """Write a PDF of ``pages`` pages (text and ruled tables). Streams the file: flat memory for any page count."""
    path = Path(path)
    font = 3
    first = 4  # page object ids: first + 2 * i, content ids: first + 2 * i + 1
    size = first + 2 * pages
    offsets = [0] * size
    with open(path, "wb") as fh:
        pos = 0

        def put(data: bytes) -> None:
            nonlocal pos
            fh.write(data)
            pos += len(data)

        def obj(i: int, body: bytes) -> None:
            offsets[i] = pos
            put(b"%d 0 obj\n" % i + body + b"\nendobj\n")

        put(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = b" ".join(b"%d 0 R" % (first + 2 * i) for i in range(pages))
        obj(2, b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % pages)
        obj(font, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        for i in range(pages):
            pid, cid = first + 2 * i, first + 2 * i + 1
            obj(pid, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >> "
                     b"/Contents %d 0 R >>" % (font, cid))
            raw = _page_stream(i + 1, pages, **layout)
            if compress:
                data = zlib.compress(raw, 6)
                obj(cid, b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
            else:
                obj(cid, b"<< /Length %d >>\nstream\n" % len(raw) + raw + b"\nendstream")
        xref = pos
        put(b"xref\n0 %d\n0000000000 65535 f \n" % size)
        for i in range(1, size):
            put(b"%010d 00000 n \n" % offsets[i])
        put(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref))
    return path


def make_dossier(folder: Path, pdf_pages: Optional[int] = 800, small_files: int = 26) -> Path:
    """A client folder: one long PDF (``pdf_pages`` pages; None for none) and ``small_files`` small invented files
    (texts, notes, e-mails, web pages)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if pdf_pages:
        make_long_pdf(folder / "Grand livre des livraisons.pdf", pdf_pages)
    kinds = ("txt", "md", "eml", "html")
    for i in range(small_files):
        ext = kinds[i % len(kinds)]
        body = (f"Note {i + 1}. Mme {PERSON_EARLY} a reçu le courrier de {COMPANY} le {i % 28 + 1:02d}/03/2026. "
                f"Le dossier suit son cours ; prochaine réunion le {i % 28 + 1:02d}/04/2026 au cabinet.\n")
        p = folder / f"piece {i + 1:02d}.{ext}"
        if ext == "eml":
            p.write_text(f"From: Cabinet <contact@cabinet-exemple.fr>\nTo: Client <client@exemple.fr>\n"
                         f"Subject: Point {i + 1}\nContent-Type: text/plain; charset=utf-8\n\n{body}", encoding="utf-8")
        elif ext == "html":
            p.write_text(f"<html><body><p>{body}</p></body></html>", encoding="utf-8")
        else:
            p.write_text(body * 3, encoding="utf-8")
    return folder


def make_vector_pdf(path: Path, segments: int, pages: int = 3, heavy_page: int = 2) -> Path:
    """v0.4.3 fix: a short PDF with one plan-like page (``segments`` line segments, a few words) among plain pages,
    like a construction plan. Invented content."""
    path = Path(path)

    def stream(heavy: bool) -> bytes:
        ops = [b"BT /F1 9 Tf 1 0 0 1 40 800 Tm (" + _esc(f"Plan fictif du lot 3, M. {PERSON_LATE}") + b") Tj ET",
               b"0.2 w"]
        if heavy:
            for i in range(segments):
                x, y = 40 + (i * 7) % 500, 60 + (i * 13) % 700
                ops.append(b"%d %d m %d %d l S" % (x, y, x + 5 + i % 9, y + 3 + i % 7))
        return b"\n".join(ops)

    objs: list[Optional[bytes]] = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
                                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    for p in range(pages):
        data = zlib.compress(stream(p + 1 == heavy_page), 6)
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> "
                    b"/Contents %d 0 R >>" % (len(objs) + 2))
        kids.append(len(objs))
        objs.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
    objs[1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + b"] /Count %d >>" % pages
    buf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(buf))
        buf += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(buf)
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    buf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(bytes(buf))
    return path
