"""Tests for ragbase_shield.documents. Synthetic data only (invented names)."""
from __future__ import annotations

import os
import re
import zipfile
from email.message import EmailMessage
from pathlib import Path

import docx
import pytest
from lxml import etree

from ragbase_shield import documents as D
from ragbase_shield.documents import DocumentError, ReadResult, read_text

PERSON = "Maître Hélène Garnier-Vasseur"
OTHER = "Jules Morvandiau"
COMPANY = "Lambretti Conseil SAS"


# ----------------------------------------------------------------------------------- builders

def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(path: Path, pages: list[str | None]) -> Path:
    """Hand-built minimal PDF (Helvetica, WinAnsiEncoding). None = a page without text (like a scan)."""
    objects: dict[int, bytes] = {}
    page_ids = []
    next_id = 4
    for text in pages:
        pid, cid = next_id, next_id + 1
        next_id += 2
        page_ids.append(pid)
        if text is None:
            stream = b"0 0 m 10 10 l S"
        else:
            ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
            ops += [f"({_pdf_escape(line)}) Tj T*" for line in text.split("\n")]
            ops.append("ET")
            stream = "\n".join(ops).encode("cp1252")
        objects[cid] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        objects[pid] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                        b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % cid)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = (b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % i for i in page_ids)
                  + b"] /Count %d >>" % len(page_ids))
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for i in sorted(objects):
        offsets[i] = len(out)
        out += b"%d 0 obj\n" % i + objects[i] + b"\nendobj\n"
    xref = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for i in range(1, size):
        out += b"%010d 00000 n \n" % offsets[i]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref)
    path.write_bytes(bytes(out))
    return path


_FOOTNOTES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="{D._W}">
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
  <w:footnote w:id="1"><w:p><w:r><w:t>Note fictive concernant {OTHER}.</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""


def _add_footnotes(path: Path) -> None:
    """python-docx cannot create footnotes: add a footnotes part to the package by hand."""
    with zipfile.ZipFile(path) as zin:
        items = {name: zin.read(name) for name in zin.namelist()}
    ct = items["[Content_Types].xml"].decode()
    ct = ct.replace("</Types>", '<Override PartName="/word/footnotes.xml" ContentType="application/'
                    'vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>')
    items["[Content_Types].xml"] = ct.encode()
    rels = items["word/_rels/document.xml.rels"].decode()
    rels = rels.replace("</Relationships>", '<Relationship Id="rIdFn99" Type="http://schemas.openxmlformats.org/'
                        'officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/></Relationships>')
    items["word/_rels/document.xml.rels"] = rels.encode()
    items["word/footnotes.xml"] = _FOOTNOTES_XML.encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)


def make_docx(path: Path) -> Path:
    doc = docx.Document()
    doc.sections[0].header.paragraphs[0].text = "En-tête du cabinet Fictif & Associés"
    doc.sections[0].footer.paragraphs[0].text = "Pied de page confidentiel"
    doc.add_heading("Conclusions", level=1)
    p = doc.add_paragraph(f"Pour {PERSON}, demanderesse, contre ")
    run = p.add_run(COMPANY)
    run.bold = True
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Partie"
    table.cell(0, 1).text = "Rôle"
    table.cell(1, 0).text = OTHER
    table.cell(1, 1).text = "Témoin"
    last = doc.add_paragraph("Paragraphe commenté.")
    doc.add_comment(last.runs, text="Vérifier la date fictive.", author="Auteur Zorglubien", initials="AZ")
    doc.save(path)
    _add_footnotes(path)
    return path


# ----------------------------------------------------------------------------------- ReadResult

def test_read_result_is_a_str_and_hides_text_in_repr():
    r = ReadResult("secret Garnier", pages=2, needs_ocr=False, warnings=["x"])
    assert isinstance(r, str) and r == "secret Garnier"
    assert type(r.text) is str and r.text == "secret Garnier"
    assert r.pages == 2 and r.needs_ocr is False and r.warnings == ("x",)
    assert "Garnier" not in repr(r)


# ----------------------------------------------------------------------------------- PDF

def test_pdf_text_and_accents(tmp_path):
    path = make_pdf(tmp_path / "jugement.pdf", [f"Jugement fictif\n{PERSON} (demanderesse)", f"Page 2 {COMPANY}"])
    res = read_text(path)
    assert res.pages == 2
    assert res.needs_ocr is False
    assert PERSON in res.text
    assert COMPANY in res.text
    assert "(demanderesse)" in res.text
    assert res.warnings == ()


def test_pdf_without_text_needs_ocr(tmp_path):
    res = read_text(make_pdf(tmp_path / "scan.pdf", [None, None]))
    assert res.needs_ocr is True
    assert res.text == ""
    assert res.pages == 2
    assert "pdf_no_text_layer" in res.warnings


def test_pdf_partly_scanned_warns(tmp_path):
    res = read_text(make_pdf(tmp_path / "mixte.pdf", ["Texte fictif", None]))
    assert res.needs_ocr is False
    assert "pdf_pages_without_text:1" in res.warnings


def test_pdf_with_user_password_fails_closed(tmp_path):
    from pypdf import PdfReader, PdfWriter

    src = make_pdf(tmp_path / "src.pdf", [PERSON])
    writer = PdfWriter()
    for page in PdfReader(str(src)).pages:
        writer.add_page(page)
    writer.encrypt(user_password="mot-de-passe-fictif", algorithm="AES-128")
    locked = tmp_path / "verrouille.pdf"
    with open(locked, "wb") as fh:
        writer.write(fh)
    with pytest.raises(DocumentError) as exc:
        read_text(locked)
    assert str(exc.value) == "pdf_encrypted"


def test_pdf_with_owner_password_only_is_read(tmp_path):
    from pypdf import PdfReader, PdfWriter

    src = make_pdf(tmp_path / "src.pdf", [PERSON])
    writer = PdfWriter()
    for page in PdfReader(str(src)).pages:
        writer.add_page(page)
    writer.encrypt(user_password="", owner_password="proprietaire-fictif", algorithm="AES-128")
    locked = tmp_path / "proprietaire.pdf"
    with open(locked, "wb") as fh:
        writer.write(fh)
    assert PERSON in read_text(locked).text


def test_corrupt_pdf_error_has_no_name(tmp_path):
    bad = tmp_path / "Garnier confidentiel.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not a pdf")
    with pytest.raises(DocumentError) as exc:
        read_text(bad)
    assert "Garnier" not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__


# ----------------------------------------------------------------------------------- DOCX

def test_docx_body_tables_headers_footers_footnotes_comments(tmp_path):
    res = read_text(make_docx(tmp_path / "conclusions.docx"))
    text = res.text
    assert PERSON in text and COMPANY in text
    assert f"{OTHER} | Témoin" in text  # table row
    assert "En-tête du cabinet Fictif & Associés" in text
    assert "Pied de page confidentiel" in text
    assert f"Note fictive concernant {OTHER}." in text
    assert "Vérifier la date fictive." in text
    assert "Zorglubien" not in text  # comment authors are not read
    assert "[En-tête]" in text and "[Notes de bas de page]" in text
    assert text.index("En-tête du cabinet") < text.index("Conclusions") < text.index("Pied de page")
    assert res.pages is None and res.needs_ocr is False


def test_docx_labels_follow_locale(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_LOCALE", "en")
    text = read_text(make_docx(tmp_path / "c.docx")).text
    assert "[Header]" in text and "[Footnotes]" in text and "[Comments]" in text


def _w(xml: str):
    return etree.fromstring(f'<w:body xmlns:w="{D._W}" '
                            f'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">{xml}</w:body>')


def test_docx_xml_text_rules():
    body = _w(
        "<w:p><w:pPr><w:tabs><w:tab w:val='left' w:pos='720'/></w:tabs></w:pPr>"
        "<w:r><w:t>Avant</w:t></w:r><w:r><w:tab/><w:t>après</w:t><w:br/><w:t>ligne</w:t></w:r></w:p>"
        "<w:p><w:del><w:r><w:delText>supprimé</w:delText></w:r></w:del><w:ins><w:r><w:t>inséré</w:t></w:r></w:ins>"
        "<w:r><w:instrText>HYPERLINK mailto:x@exemple-fictif.fr</w:instrText></w:r></w:p>"
        "<w:sdt><w:sdtContent><w:p><w:r><w:t>Contrôle de contenu</w:t></w:r></w:p></w:sdtContent></w:sdt>"
        "<w:p><w:r><mc:AlternateContent><mc:Choice Requires='wps'><w:txbxContent><w:p><w:r><w:t>Zone</w:t>"
        "</w:r></w:p></w:txbxContent></mc:Choice><mc:Fallback><w:txbxContent><w:p><w:r><w:t>Zone</w:t></w:r></w:p>"
        "</w:txbxContent></mc:Fallback></mc:AlternateContent></w:r></w:p>"
    )
    text = D._element_text(body)
    assert "Avant\taprès\nligne" in text
    assert "supprimé" not in text and "inséré" in text
    assert "mailto" not in text
    assert "Contrôle de contenu" in text
    assert text.count("Zone") == 1  # text box read once, not twice


def test_corrupt_docx_fails_closed(tmp_path):
    bad = tmp_path / "Morvandiau.docx"
    bad.write_bytes(b"PK\x03\x04 broken")
    with pytest.raises(DocumentError) as exc:
        read_text(bad)
    assert str(exc.value) == "docx_unreadable"


# ----------------------------------------------------------------------------------- TXT / MD

def test_txt_utf8_bom_and_cp1252_fallback(tmp_path):
    a = tmp_path / "a.txt"
    a.write_bytes(b"\xef\xbb\xbf" + f"Bonjour {PERSON}\r\nfin".encode("utf-8"))
    res = read_text(a)
    assert res.text == f"Bonjour {PERSON}\nfin"
    assert res.warnings == ()

    b = tmp_path / "b.md"
    b.write_bytes(f"# Note\n{PERSON} \u2019".encode("cp1252"))
    res = read_text(b)
    assert PERSON in res.text and "\u2019" in res.text
    assert "encoding_fallback_cp1252" in res.warnings


def test_unsupported_and_missing(tmp_path):
    x = tmp_path / "tableau.pptx"  # v0.4 (T8): .xlsx is read since T8, a slide deck is still unsupported
    x.write_bytes(b"x")
    with pytest.raises(DocumentError, match="unsupported_format"):
        read_text(x)
    with pytest.raises(DocumentError, match="file_not_found"):
        read_text(tmp_path / "absent.txt")


# ----------------------------------------------------------------------------------- EML

def test_eml_headers_and_plain_body(tmp_path):
    msg = EmailMessage()
    msg["From"] = f"{OTHER} <jules.morvandiau@exemple-fictif.fr>"
    msg["To"] = "Hélène Garnier-Vasseur <h.garnier@exemple-fictif.fr>"
    msg["Cc"] = "secretariat@exemple-fictif.fr"
    msg["Bcc"] = "cache@exemple-fictif.fr"
    msg["Subject"] = "Dossier fictif : audience du 12 mars"
    msg["Date"] = "Wed, 14 Oct 2026 10:00:00 +0200"
    msg.set_content(f"Chère Maître,\nVoici les pièces concernant {COMPANY}.\n")
    msg.add_alternative("<p>Version <b>HTML</b></p>", subtype="html")
    msg.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="Garnier-piece.pdf")
    path = tmp_path / "message.eml"
    path.write_bytes(bytes(msg))
    res = read_text(path)
    text = res.text
    assert text.startswith(f"From: {OTHER} <jules.morvandiau@exemple-fictif.fr>")
    assert "To: Hélène Garnier-Vasseur <h.garnier@exemple-fictif.fr>" in text
    assert "Cc: secretariat@exemple-fictif.fr" in text
    assert "Subject: Dossier fictif : audience du 12 mars" in text
    assert "Date: Wed, 14 Oct 2026" in text
    assert f"Voici les pièces concernant {COMPANY}." in text
    assert "Version" not in text  # plain body preferred
    assert "Bcc" not in text and "Garnier-piece.pdf" not in text
    assert "eml_attachments_not_read:1" in res.warnings


def test_eml_html_only(tmp_path):
    msg = EmailMessage()
    msg["From"] = "x@exemple-fictif.fr"
    msg["Subject"] = "HTML"
    msg.set_content(f"<html><body><p>Bonjour&nbsp;{OTHER}</p><script>alert(1)</script></body></html>",
                    subtype="html")
    path = tmp_path / "html.eml"
    path.write_bytes(bytes(msg))
    res = read_text(path)
    assert f"Bonjour\u00a0{OTHER}" in res.text or f"Bonjour {OTHER}" in res.text
    assert "alert" not in res.text
    assert "eml_html_body" in res.warnings


# ----------------------------------------------------------------------------------- HTML

def test_html_to_text(tmp_path):
    html = (
        "<html><head><title>Note fictive</title><style>p{color:red}</style></head><body>"
        f"<h1>Audience</h1><p>Pour&nbsp;{PERSON} &amp; associés</p>"
        "<ul><li>Pièce 1</li><li>Pièce 2</li></ul>"
        f"<table><tr><th>Nom</th><th>Rôle</th></tr><tr><td>{OTHER}</td><td>Témoin</td></tr></table>"
        "<script>var x = 'ne pas lire';</script><pre>  a   b</pre></body></html>"
    )
    path = tmp_path / "page.htm"
    path.write_text(html, encoding="utf-8")
    text = read_text(path).text
    assert "Note fictive" in text and "Audience" in text
    assert "& associés" in text
    assert "- Pièce 1" in text and "- Pièce 2" in text
    assert f"{OTHER} | Témoin" in text
    assert "ne pas lire" not in text and "color" not in text
    assert "  a   b" in text


# ----------------------------------------------------------------------------------- writing

MARKDOWN = """# Conclusions récapitulatives

## Faits

Le contrat entre **PERSONNE_A** et *SOCIETE_B* a été signé.
Deuxième ligne du même paragraphe.

- premier point avec PERSONNE_A et SOCIETE_B
- second point
  - sous-point

1. demande principale
2. demande subsidiaire

> Citation fictive

| Partie | Rôle |
|---|---|
| PERSONNE_A | demanderesse |

Texte ***gras italique*** et `code` et \\*pas italique\\*.
"""


def test_write_docx_structure_and_formatting(tmp_path):
    out = D.write_docx(tmp_path / "conclusions.docx", MARKDOWN, "DOSSIER_3")
    doc = docx.Document(str(out))
    paras = doc.paragraphs
    styles = [(p.style.name, p.text) for p in paras]
    assert ("Heading 1", "Conclusions récapitulatives") in styles
    assert ("Heading 2", "Faits") in styles
    assert ("List Bullet", "premier point avec PERSONNE_A et SOCIETE_B") in styles  # underscores kept
    assert ("List Bullet 2", "sous-point") in styles
    assert ("List Number", "demande principale") in styles
    assert ("Quote", "Citation fictive") in styles
    body = next(p for p in paras if p.text.startswith("Le contrat"))
    assert body.text == "Le contrat entre PERSONNE_A et SOCIETE_B a été signé.\nDeuxième ligne du même paragraphe."
    assert any(r.bold and r.text == "PERSONNE_A" for r in body.runs)
    assert any(r.italic and r.text == "SOCIETE_B" for r in body.runs)
    last = next(p for p in paras if p.text.startswith("Texte"))
    assert last.text == "Texte gras italique et code et *pas italique*."
    assert any(r.bold and r.italic and r.text == "gras italique" for r in last.runs)
    assert doc.tables[0].cell(1, 0).text == "PERSONNE_A"


def test_write_docx_properties_hold_only_the_code(tmp_path):
    out = D.write_docx(tmp_path / "x.docx", f"Texte restauré pour {PERSON}", "DOSSIER_12")
    assert D.docx_dossier_code(out) == "DOSSIER_12"
    with zipfile.ZipFile(out) as zf:
        custom = zf.read("docProps/custom.xml").decode()
        core = zf.read("docProps/core.xml").decode()
    assert re.findall(r"<vt:lpwstr>(.*?)</vt:lpwstr>", custom) == ["DOSSIER_12"]
    assert "python-docx" not in core and "Garnier" not in core
    cp = docx.Document(str(out)).core_properties
    assert cp.author == "" and cp.title == "" and cp.comments == "" and cp.last_modified_by == ""
    assert PERSON in read_text(out).text


def test_write_docx_rejects_anything_but_a_dossier_code(tmp_path):
    with pytest.raises(ValueError):
        D.write_docx(tmp_path / "x.docx", "texte", "Garnier c. Lambretti")
    assert not (tmp_path / "x.docx").exists()


def test_writers_never_overwrite_by_default(tmp_path):
    a = D.write_docx(tmp_path / "note.docx", "un", "DOSSIER_1")
    b = D.write_docx(tmp_path / "note.docx", "deux", "DOSSIER_1")
    c = D.write_md(tmp_path / "note.md", "trois")
    d = D.write_md(tmp_path / "note.md", "quatre")
    assert (a.name, b.name, c.name, d.name) == ("note.docx", "note (2).docx", "note.md", "note (2).md")
    assert read_text(a).text == "un" and read_text(b).text == "deux"
    assert d.read_text(encoding="utf-8") == "quatre\n"
    e = D.write_md(tmp_path / "note.md", "cinq", overwrite=True)
    assert e == c and c.read_text(encoding="utf-8") == "cinq\n"
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".shield-")]  # no temp files left


def test_safe_filename():
    assert D.safe_filename("../../etc/passwd") == "etc-passwd"
    for raw in ("../../evil", "..\\..\\evil", "/abs/path", "C:\\x\\y", "a/b\\c"):
        name = D.safe_filename(raw, "docx")
        assert "/" not in name and "\\" not in name and not name.startswith(".")
        assert name.endswith(".docx")
    assert D.safe_filename("Conclusions : PERSONNE_A c. SOCIETE_B", "docx") == "Conclusions - PERSONNE_A c. SOCIETE_B.docx"
    assert D.safe_filename("contrat.PDF") == "contrat.pdf"
    assert D.safe_filename("note.docx", ".docx") == "note.docx"
    assert D.safe_filename("note.md", "docx") == "note.md.docx"
    assert D.safe_filename("CON", "txt") == "_CON.txt"
    assert D.safe_filename(".bashrc") == "bashrc"
    assert D.safe_filename("   ", "md") == "document.md"
    assert D.safe_filename("a\x00b\nc", "md") == "a b c.md"
    assert len(D.safe_filename("x" * 500, "md")) <= D.MAX_STEM_CHARS + 3
    with pytest.raises(ValueError):
        D.safe_filename("x", "../docx")


def test_save_output_stays_in_directory(tmp_path):
    out_dir = tmp_path / "Shield - sorties"
    path = D.save_output(out_dir, "../../../évasion", "contenu", "md")
    assert path.parent == out_dir
    assert path.read_text(encoding="utf-8") == "contenu\n"
    path2 = D.save_output(out_dir, "Note PERSONNE_A", "# Titre", "docx", dossier_code="DOSSIER_2")
    assert path2.parent == out_dir and path2.suffix == ".docx"
    assert D.docx_dossier_code(path2) == "DOSSIER_2"
    with pytest.raises(ValueError):
        D.save_output(out_dir, "x", "y", "exe")


def test_kind_of():
    assert D.kind_of("a/b.HTM") == "html"
    assert D.kind_of("x.docx") == "docx"
    assert D.kind_of("x.doc") is None
    assert D.kind_of("x.XLSX") == "xlsx"  # v0.4 (T8)
    assert set(D.SUPPORTED_EXTENSIONS) == {".pdf", ".docx", ".xlsx", ".txt", ".md", ".eml", ".html", ".htm"}


def test_no_network_imports_in_documents_module():
    src = Path(D.__file__).read_text(encoding="utf-8")
    for banned in ("import socket", "urllib.request", "import requests", "import httpx", "http.client"):
        assert banned not in src
    assert os.environ.get("RAGBASE_SHIELD_KEYRING") == "0"
