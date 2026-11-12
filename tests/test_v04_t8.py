"""v0.4 T8 (PLAN_V04 2.3: small name and id rules, PDF wrapped cells; the plan's addendum: the .xlsx reader; the
T2 check's chat-source flag). Invented data only: an invented sailing club, its invented members, places, ids and
sentences.

- K2: the rows of a ruled PDF table are read cell by cell, so a cell wrapped over two lines is one cell;
- the .xlsx reader (standard library): one line per row, cells joined by the cell separator, the sheet title first;
- K5: an id value whose prefix holds 2 or 3 letter groups ("KLM-QV-0442") under an id column or a label noun,
  every id of a cell that lists several, and the same layout in the rest of the text; English texts only;
- K10: a bare workspace member id and a profile handle after the "LinkedIn" label are usernames; English only;
- K11 (quoted names, a code after a name, a spaced dash) was built, measured and DROPPED: its leave-one-out gain
  was under 60 % of its class estimate (the step's own guard); it is not in this release;
- the chat flag (``Masker.mask(chat=...)``): a chat message is chat text whatever its lines look like;
- a contraction before a lower-case common-word first name reads it as a verb or a noun (T2 check, finding 3).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from ragbase_shield import documents as D
from ragbase_shield.engine import Masker, MemoryStore
from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import detectors_ids as ids
from ragbase_shield.engine import directory as DR
from ragbase_shield.engine import names as nm


# --- the invented club roster ------------------------------------------------------------------------------------

def _user(first: str, last: str, display: str = "", real: str = "", domain: str = "brenwick.example") -> dict:
    real = real or f"{first} {last}"
    return {"id": "U0" + (first[:3] + last[:4]).upper(), "name": f"{first}.{last}".lower(), "real_name": real,
            "profile": {"real_name": real, "display_name": display, "first_name": first, "last_name": last,
                        "email": f"{first}.{last}@{domain}".lower()}}


USERS = [
    _user("Pellorin", "Doran"),
    _user("Osric", "Vossberg", display="Ozzy"),
    _user("Ottilie", "Tarquell"),
    _user("Jorun", "Quenby"),
    _user("Lisette", "Varnholt", display="Lis"),
    _user("Ari", "Ndidi Abara", real="Ari Ndidi Abara"),
    _user("Thessaly", "Fenwick", real="Thessaly Rafe Fenwick"),
    _user("Hope", "Pembrooke"),  # a first name that is also a common word
]


@pytest.fixture(scope="module")
def directory() -> DR.Directory:
    return DR.build([("slack_users", USERS)], lang="auto")


def _masked(directory, texts: list[str], target: str, kinds=("PERSON",), chat=None) -> list[tuple[str, str]]:
    """(surface, kind) of the spans of ``target`` after a pass over ``texts`` and ``target`` (the dossier scan)."""
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False, directory=directory)
    for t in texts + [target]:
        m.mask(t, chat=chat)
    r = m.mask(target, chat=chat)
    return [(target[s.start:s.end], s.kind) for s in r.spans if s.kind in kinds]


def _persons(directory, target: str, chat=None) -> list[str]:
    return [s for s, _k in _masked(directory, [], target, chat=chat)]


# --- the .xlsx reader (plan addendum) ---------------------------------------------------------------------------

_SHEET_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
_REL_NS = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
_WS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"


def make_xlsx(path: Path, sheets: list[tuple[str, str]], shared: list[str] = ()) -> Path:
    """A minimal workbook: ``sheets`` = (title, sheetData XML) in order; ``shared`` = the shared strings."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                    'package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
        zf.writestr("_rels/.rels", f'<?xml version="1.0"?><Relationships {_REL_NS}><Relationship Id="rId1" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                    'Target="xl/workbook.xml"/></Relationships>')
        names = "".join(f'<sheet name="{t}" sheetId="{i}" r:id="rId{i}"/>' for i, (t, _x) in enumerate(sheets, 1))
        zf.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook {_SHEET_NS} xmlns:r="http://schemas.'
                    f'openxmlformats.org/officeDocument/2006/relationships"><sheets>{names}</sheets></workbook>')
        rels = "".join(f'<Relationship Id="rId{i}" Type="{_WS_REL}" Target="worksheets/sheet{i}.xml"/>'
                       for i in range(1, len(sheets) + 1))
        zf.writestr("xl/_rels/workbook.xml.rels", f'<?xml version="1.0"?><Relationships {_REL_NS}>{rels}</Relationships>')
        for i, (_t, data) in enumerate(sheets, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", f'<?xml version="1.0"?><worksheet {_SHEET_NS}><sheetData>'
                        f"{data}</sheetData></worksheet>")
        if shared:
            si = "".join(f"<si><t>{s}</t></si>" for s in shared)
            zf.writestr("xl/sharedStrings.xml", f'<?xml version="1.0"?><sst {_SHEET_NS} count="{len(shared)}" '
                        f'uniqueCount="{len(shared)}">{si}</sst>')
    return path


def _inline(ref: str, text: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def test_xlsx_rows_cells_and_sheet_title(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_LOCALE", "fr")
    data = ('<row r="1">' + _inline("A1", "Mois") + _inline("B1", "Jours") + _inline("C1", "Membre") + "</row>"
            '<row r="2"><c r="A2"><v>3</v></c><c r="B2"><v>12.5</v></c>' + _inline("C2", "Pellorin Doran") + "</row>"
            '<row r="3"></row>'
            '<row r="4"><c r="A4" t="s"><v>0</v></c><c r="C4" t="s"><v>1</v></c></row>')
    p = make_xlsx(tmp_path / "presences.xlsx", [("Jours 2026", data)], shared=["Total", "Ottilie Tarquell"])
    res = D.read_text(p)
    lines = res.text.split("\n")
    assert lines[0].endswith("Jours 2026") and lines[0].startswith("[")
    assert lines[1] == "Mois | Jours | Membre"
    assert lines[2] == "3 | 12.5 | Pellorin Doran"
    assert lines[3] == "Total |  | Ottilie Tarquell"  # the empty cell keeps the column in place
    assert res.pages is None and res.warnings == () and D.kind_of(p) == "xlsx"


def test_xlsx_two_sheets_formula_result_and_booleans(tmp_path):
    s1 = '<row r="1">' + _inline("B1", "x") + '<c r="C1" t="str"><v>ok</v></c><c r="D1" t="b"><v>1</v></c></row>'
    s2 = '<row r="1"><c r="A1" t="e"><v>#REF!</v></c>' + _inline("B1", "y") + "</row>"
    p = make_xlsx(tmp_path / "two.xlsx", [("First", s1), ("Second", s2)])
    text = D.read_text(p).text
    blocks = text.split("\n\n")
    assert len(blocks) == 2
    assert blocks[0].split("\n")[1] == "x | ok | TRUE"  # the first used column of the sheet opens the row
    assert blocks[1].split("\n")[1] == "y"  # an error value is not content


def test_xlsx_fails_closed_on_a_broken_workbook(tmp_path):
    p = tmp_path / "broken.xlsx"
    p.write_bytes(b"not a zip")
    with pytest.raises(D.DocumentError, match="xlsx_unreadable"):
        D.read_text(p)
    with zipfile.ZipFile(tmp_path / "empty.xlsx", "w") as zf:
        zf.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook {_SHEET_NS}><sheets/></workbook>')
    res = D.read_text(tmp_path / "empty.xlsx")
    assert res.text == "" and "xlsx_no_sheet" in res.warnings


def test_xlsx_text_goes_through_the_table_rules(directory, tmp_path):
    data = ('<row r="1">' + _inline("A1", "Berth") + _inline("B1", "Staff number") + _inline("C1", "Keeper") + "</row>"
            '<row r="2"><c r="A2"><v>3</v></c>' + _inline("B2", "KLM-QV-0442") + _inline("C2", "Orla Morrow") + "</row>")
    text = D.read_text(make_xlsx(tmp_path / "berths.xlsx", [("Berths", data)])).text
    found = _masked(directory, [], text, kinds=("EMPLOYEE_ID", "PERSON"))
    assert ("KLM-QV-0442", "EMPLOYEE_ID") in found and ("Orla Morrow", "PERSON") in found


# --- K2: ruled PDF tables --------------------------------------------------------------------------------------

def _pdf_bytes(ops: str) -> bytes:
    """A one-page PDF (Helvetica) from raw content-stream operators."""
    content = ops.encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
        b"/Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def _text(x: int, y: int, s: str) -> str:
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 10 Tf {x} {y} Td ({s}) Tj ET\n"


def _line(x0: int, y0: int, x1: int, y1: int) -> str:
    return f"0.5 w {x0} {y0} m {x1} {y1} l S\n"


# A two-column ruled table (header row, one data row whose right cell wraps over two lines) and a paragraph below.
TABLE_PDF_OPS = (
    _line(72, 650, 472, 650) + _line(72, 620, 472, 620) + _line(72, 560, 472, 560)
    + _line(72, 560, 72, 650) + _line(172, 560, 172, 650) + _line(472, 560, 472, 650)
    + _text(76, 632, "Name") + _text(176, 632, "Address")
    + _text(76, 596, "Pellorin Doran") + _text(176, 602, "14 Wharf Lane, Suite 2") + _text(176, 586, "Elmsgate, NV 89101")
    + _text(72, 500, "Prepared for the committee.")
)


@pytest.fixture(scope="module")
def table_pdf(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("t8") / "table.pdf"
    p.write_bytes(_pdf_bytes(TABLE_PDF_OPS))
    return p


def test_k2_wrapped_cell_is_one_cell(table_pdf, monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_PDF_TABLES", raising=False)
    text = D.read_text(table_pdf).text
    lines = text.split("\n")
    assert lines[0] == "Name | Address"
    assert lines[1] == "Pellorin Doran | 14 Wharf Lane, Suite 2 Elmsgate, NV 89101"
    assert lines[2] == "Prepared for the committee."
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False)
    kinds = [(text[s.start:s.end], s.kind) for s in m.mask(text).spans]
    assert any(k == "ADDRESS" and v.startswith("14 Wharf Lane, Suite 2") for v, k in kinds)


def test_k2_switch_restores_the_line_by_line_reading(table_pdf, monkeypatch):
    monkeypatch.setenv("RAGBASE_SHIELD_PDF_TABLES", "0")
    lines = D.read_text(table_pdf).text.split("\n")
    assert "14 Wharf Lane, Suite 2" in lines and "Elmsgate, NV 89101" in lines  # the address is cut in two


def test_k2_rows_keep_every_word_and_their_glyphs(table_pdf, monkeypatch):
    monkeypatch.delenv("RAGBASE_SHIELD_PDF_TABLES", raising=False)
    pdfplumber = pytest.importorskip("pdfplumber")
    with pdfplumber.open(str(table_pdf)) as pdf:
        page = pdf.pages[0]
        lines = D.pdf_page_lines(page, return_chars=True)
        words = [w["text"] for line in lines for w in line]
        assert sorted(words) == sorted(w["text"] for w in page.extract_words())
        row = lines[1]
        assert all("chars" in w for w in row)
        seps = [D.pdf_word_separator(row[i - 1], row[i]) for i in range(1, len(row))]
        assert seps.count(D.PDF_CELL_SEPARATOR) == 1  # one cell boundary in the data row, the wrap is a space


def test_k2_cell_start_is_a_sentence_start_for_the_english_rules():
    # a verb that is also a first name, then a common word, at the start of a table cell: an imperative, no person
    # (as at the start of a line); the same pair in mid-sentence is a name
    t1 = "3 | Grant Meadow for the pending invoices | Orla Morrow | Open"
    t2 = "Grant Meadow for the pending invoices"
    for t in (t1, t2):
        assert not any(r.rule == "first_name" and t[r.start:r.end] == "Grant Meadow" for r in nm.detect_names(t, lang="en")), t
    t3 = "3 | Please ask Grant Meadow about the pending invoices | Orla Morrow | Open"
    assert any(r.rule == "first_name" and t3[r.start:r.end] == "Grant Meadow" for r in nm.detect_names(t3, lang="en"))


def test_k2_page_without_a_table_is_unchanged(tmp_path):
    p = tmp_path / "plain.pdf"
    p.write_bytes(_pdf_bytes(_text(72, 700, "Dear Pellorin Doran,") + _text(72, 686, "the regatta is on Monday.")))
    assert D.read_text(p).text == "Dear Pellorin Doran,\nthe regatta is on Monday."


# --- K5: ids with grouped letter prefixes -------------------------------------------------------------------------

def test_k5_grouped_id_under_a_column_header_and_its_layout_in_the_text():
    t = ("Berth | Staff number | Keeper\n3 | KLM-QV-0442 | Orla Morrow\n4 | KLM-QV-0443 | Pellorin Doran\n"
         "Note: the spare numbers KLM-QV-0501 to KLM-QV-0507 are not assigned.")
    got = {(t[c.start:c.end], c.kind, c.detector) for c in ids.find_grouped_ids(t)}
    assert ("KLM-QV-0442", "EMPLOYEE_ID", "table_id") in got and ("KLM-QV-0443", "EMPLOYEE_ID", "table_id") in got
    assert ("KLM-QV-0501", "EMPLOYEE_ID", "layout_id") in got and ("KLM-QV-0507", "EMPLOYEE_ID", "layout_id") in got


def test_k5_cell_that_lists_several_ids():
    t = "Lot | Billing account | Dock\n7 | HV-TK-30011 | east\n8 | HV-TK-30042, HV-TK-30077 and HV-7781 (Elmsgate Rowing) | west"
    got = {t[c.start:c.end] for c in ids.find_grouped_ids(t)}
    assert got == {"HV-TK-30011", "HV-TK-30042", "HV-TK-30077", "HV-7781"}
    assert all(c.kind == "ACCOUNT_NUMBER" for c in ids.find_grouped_ids(t))


def test_k5_label_cue_and_no_cue():
    t = "Account number: ZT-QA-55012 (club levy); policy no. 1234567 unchanged."
    assert [(t[c.start:c.end], c.kind, c.detector) for c in ids.find_grouped_ids(t)] == [("ZT-QA-55012", "ACCOUNT_NUMBER", "labelled_id")]
    assert list(ids.find_grouped_ids("Meeting reference TQV-QA-2026-0116 and budget line FEX-QV-LMB-014 in the text.")) == []
    assert list(ids.find_grouped_ids("Account number: 2026-01-15 is a date; account number: 12.5 is an amount.")) == []


def test_k5_and_k10_run_for_english_texts_only():
    t = "Berth | Staff number | Keeper\n3 | KLM-QV-0442 | Orla Morrow\nLinkedIn: orla-morrow-7 | U02ORLAMRW"
    en = {c.detector for c in det.detect_candidates(t, lang="en")}
    fr = {c.detector for c in det.detect_candidates(t, lang="fr")}
    assert {"table_id", "handle", "member_id"} <= en
    assert "member_id" not in fr and not any(c.detector == "table_id" and t[c.start:c.end] == "KLM-QV-0442"
                                             for c in det.detect_candidates(t, lang="fr"))


# --- K10: member ids and profile handles ---------------------------------------------------------------------------

@pytest.mark.parametrize("t,want", [
    ("Ari Abara | ari.abara@brenwick.example | U02ARIABARA | berths 4 and 5", ["U02ARIABARA"]),
    ("workspace member U031QT4ZN joined the channel", ["U031QT4ZN"]),
    ("Contact: pellorin.doran@brenwick.example · LinkedIn: pdoran_hq", ["pdoran_hq"]),
    ("her LinkedIn profile pdoran-7 lists the earlier club", ["pdoran-7"]),
    ("LinkedIn: pdoran7.", ["pdoran7"]),
])
def test_k10_member_ids_and_handles(t, want):
    assert [t[c.start:c.end] for c in ids.find_member_ids(t)] == want
    assert all(c.kind == "USERNAME" for c in ids.find_member_ids(t))


@pytest.mark.parametrize("t", [
    "LinkedIn and the club newsletter are listed on the card",
    "the LinkedIn profile updated last week",
    "LinkedIn: Pellorin Doran",
    "part number U0123456 is in stock",
    "see <@U02ARIABARA> for the tow",
])
def test_k10_no_handle_in_prose_or_mentions(t):
    assert [t[c.start:c.end] for c in ids.find_member_ids(t)] == []


def test_k10_handle_beats_the_name_reading(directory):
    t = "Pellorin Doran | pellorin.doran@brenwick.example | LinkedIn: pdoran-hq"
    found = _masked(directory, [], t, kinds=("USERNAME", "PERSON"))
    assert ("pdoran-hq", "USERNAME") in found and ("Pellorin Doran", "PERSON") in found


# --- the chat flag and the contraction rule ------------------------------------------------------------------------

def test_chat_flag_reads_a_short_message_as_chat(directory):
    t = "Thanks, sent it to ottilie already"
    assert _persons(directory, t) == []  # the text's own shape: one capitalised line, no chat marker
    assert _persons(directory, t, chat=True) == ["ottilie"]


def test_chat_flag_false_reads_a_lower_case_note_as_a_document(directory):
    t = "ottilie is in\njorun is out\nnothing else"
    assert "ottilie" in _persons(directory, t)
    assert _persons(directory, t, chat=False) == []


def test_chat_flag_keeps_the_function_word_checks(directory):
    # a common-word first name after a contraction reads as a verb; as a subject before "said" it is the person
    assert _persons(directory, "ok we'll hope the hull dries by noon", chat=True) == []
    assert _persons(directory, "ok hope said the hull dries by noon", chat=True) == ["hope"]


def test_contraction_before_a_common_word_name(directory):
    m = Masker(MemoryStore(locale="en"), locale="en", use_ner=False, directory=directory)
    m._lang = "en"
    assert not m._chat_form_ok("sure i'll hope for the best", 14, "hope", True, "sure i'll ")
    assert m._chat_form_ok("sure hope said no", 9, "hope", True, "sure ")
