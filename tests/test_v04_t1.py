"""v0.4 T1: the PrivacyBench runner reports its spans in the answer key's conventions (invented data only).

- a PDF span is reported as merged per-line ``boxes`` (the scorer's box rule), its glyph list under ``glyphs``;
- one NAME_GIVEN / NAME_FAMILY span per name token;
- an address with a town / state / postcode tail gives a street-level span and a locality span;
- the masked text and the text-level (human-file) report do not change;
- recheck_v02 (holdout scorer, leak check positions) reads the new PDF format with the card's rules.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from ragbase_shield.engine import Masker, MemoryStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
PB = ROOT / "evaluation" / "public" / "privacybench"


def _load(name: str, file: str):
    path = PB / file
    if not path.exists():
        pytest.skip("runner not present")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def R():
    return _load("privacybench_runner_t1", "run_shield.py")


@pytest.fixture(scope="module")
def RC():
    return _load("privacybench_recheck_t1", "recheck_v02.py")


def _glyphs(word: str, page: int, x: float, top: float, w: float = 5.0, h: float = 10.0) -> list[tuple]:
    out = []
    for ch in word:
        out.append((ch, page, round(x, 2), round(top, 2), round(x + w, 2), round(top + h, 2)))
        x += w
    return out


def _pdf_unit(R, lines: list[list[tuple[str, float]]], page: int = 1):
    """A PDF unit as pdf_text builds it: words of one line separated by a space (no glyph), lines by a newline."""
    chars: list[str] = []
    locs: list = []
    top = 100.0
    for line in lines:
        for k, (word, x) in enumerate(line):
            if k:
                chars.append(" ")
                locs.append(None)
            for g in _glyphs(word, page, x, top):
                chars.append(g[0])
                locs.append(g)
        chars.append("\n")
        locs.append(None)
        top += 14.0
    return R.Unit("pdf", "drive/invented.pdf", "".join(chars), locs)


# ----------------------------------------------------------------------------------------------- PDF boxes (X1)

def test_pdf_span_is_reported_as_line_boxes_with_its_glyphs(R):
    u = _pdf_unit(R, [[("Corwin", 50.0), ("Aldous", 90.0)], [("Pellbright", 50.0)]])
    s, e = 0, u.text.index("Pellbright") + len("Pellbright")
    locs = R.native_locations(u, s, e, pdf_boxes=True)
    assert len(locs) == 1
    loc = locs[0]
    assert "chars" not in loc  # the scorer would take chars first and use the Jaccard rule
    assert loc["pages"] == [1]
    assert [round(b["x0"], 2) for b in loc["boxes"]] == [50.0, 50.0]
    assert [round(b["x1"], 2) for b in loc["boxes"]] == [120.0, 100.0]  # "Aldous" ends at 90 + 6 * 5
    assert [b["top"] for b in loc["boxes"]] == [100.0, 114.0]
    assert len(loc["glyphs"]) == len("CorwinAldousPellbright")


def test_pdf_default_location_stays_the_answer_key_format(R):
    # the holdout builder writes its gold through native_locations: without pdf_boxes it stays per glyph (chars)
    u = _pdf_unit(R, [[("Corwin", 50.0)]])
    loc = R.native_locations(u, 0, len("Corwin"))[0]
    assert set(loc) == {"kind", "pages", "chars"} and len(loc["chars"]) == 6


def test_pdf_line_boxes_start_again_on_a_new_page_or_back_to_the_left(R):
    g = _glyphs("Ab", 1, 200.0, 50.0) + _glyphs("Cd", 1, 40.0, 50.0) + _glyphs("Ef", 2, 40.0, 50.0)
    boxes = R.pdf_line_boxes(g)
    assert [(b["page"], b["x0"]) for b in boxes] == [(1, 200.0), (1, 40.0), (2, 40.0)]


def test_box_rule_counts_a_gold_name_inside_a_longer_span(R, RC):
    u = _pdf_unit(R, [[("Corwin", 50.0), ("Aldous", 90.0), ("Pellbright", 130.0)]])
    pred = R.native_locations(u, 0, len("Corwin Aldous Pellbright"), pdf_boxes=True)[0]
    gold_chars = [list(g) for g in _glyphs("Aldous", 1, 90.0, 100.0)]
    gold = {"kind": "pdf", "chars": gold_chars}
    assert RC.box_cover(pred, gold) == 1.0
    assert RC.ov("pdf", pred, gold, {}) == 1.0
    # the same prediction as chars keeps the Jaccard rule (6 of 22 glyphs: a miss)
    as_chars = {"kind": "pdf", "chars": pred["glyphs"]}
    assert RC.ov("pdf", as_chars, gold, {}) < 0.5
    # a gold name on another line is not covered by the box of this line
    other = {"kind": "pdf", "chars": [list(g) for g in _glyphs("Aldous", 1, 90.0, 130.0)]}
    assert RC.box_cover(pred, other) == 0.0


def test_glyph_positions_of_the_new_format_are_the_old_ones(R, RC):
    u = _pdf_unit(R, [[("Marrowdale", 60.0)]])
    loc = R.native_locations(u, 0, len("Marrowdale"), pdf_boxes=True)[0]
    old = {"kind": "pdf", "chars": loc["glyphs"]}
    assert RC.cells("pdf", loc) == RC.cells("pdf", old) and len(RC.cells("pdf", loc)) == 10


# ------------------------------------------------------------------------------------ name tokens (X2, K4)

def test_name_spans_give_one_span_per_token(R):
    text = "Notes for Corwin Aldous Pellbright and Van Der Kell."
    bs = [{"start": 10, "end": 23, "label": "NAME_GIVEN", "text": text[10:23], "new_text": "PERSON_A"},
          {"start": 24, "end": 34, "label": "NAME_FAMILY", "text": text[24:34], "new_text": "PERSON_A"},
          {"start": 39, "end": 51, "label": "NAME_FAMILY", "text": text[39:51], "new_text": "PERSON_B"}]
    out = R.native_report(text, bs)
    assert [(b["label"], b["text"], b["new_text"]) for b in out] == [
        ("NAME_GIVEN", "Corwin", "PERSON_A"), ("NAME_GIVEN", "Aldous", "PERSON_A"),
        ("NAME_FAMILY", "Pellbright", "PERSON_A"),
        ("NAME_FAMILY", "Van", "PERSON_B"), ("NAME_FAMILY", "Der", "PERSON_B"), ("NAME_FAMILY", "Kell", "PERSON_B")]
    for b in out:
        assert text[b["start"]:b["end"]] == b["text"]


def test_synthetic_name_tokens_take_the_matching_fake_token(R):
    text = "Corwin Aldous"
    b = {"start": 0, "end": 13, "label": "NAME_GIVEN", "text": text, "new_text": "Tobin Merrow"}
    assert [x["new_text"] for x in R.native_report(text, [b])] == ["Tobin", "Merrow"]
    b2 = dict(b, new_text="Tobin")  # the fake has another number of tokens: every part gets the whole fake
    assert [x["new_text"] for x in R.native_report(text, [b2])] == ["Tobin", "Tobin"]


def test_one_token_names_and_other_labels_are_unchanged(R):
    text = "Corwin at Quillbrook Fabrics"
    bs = [{"start": 0, "end": 6, "label": "NAME_GIVEN", "text": "Corwin", "new_text": "PERSON_A"},
          {"start": 10, "end": 28, "label": "ORGANIZATION", "text": text[10:28], "new_text": "ORG_A"}]
    assert R.native_report(text, bs) == bs


# ---------------------------------------------------------------------------------- street-level address (K8)

@pytest.mark.parametrize("value, street, locality", [
    ("48 Quillfeather Lane, Marrowdale, QX 00912", "48 Quillfeather Lane", "Marrowdale, QX 00912"),
    ("48 Quillfeather Lane, Suite 210, Marrowdale, QX 00912", "48 Quillfeather Lane, Suite 210",
     "Marrowdale, QX 00912"),
    ("48 Quillfeather Lane,\nMarrowdale, QX 00912-4471", "48 Quillfeather Lane", "Marrowdale, QX 00912-4471"),
    ("48 Quillfeather Lane\nNorth Marrowdale QX 00912", "48 Quillfeather Lane", "North Marrowdale QX 00912"),
    ("Unit 4, 12345 Brackenridge Road, Marrowdale, QX 00912", "Unit 4, 12345 Brackenridge Road",
     "Marrowdale, QX 00912"),
    ("9 Tollbar Way, Marrowdale, Oldshire 00912", "9 Tollbar Way", "Marrowdale, Oldshire 00912"),
    ("12 Thistlemere Row, Fenwick, ZX9 9QQ", "12 Thistlemere Row", "Fenwick, ZX9 9QQ"),
    ("48 Quillfeather Lane | Marrowdale, QX 00912", "48 Quillfeather Lane", "Marrowdale, QX 00912"),
])
def test_street_split(R, value, street, locality):
    cut = R.street_split(value)
    assert cut is not None
    assert value[:cut[0]] == street and value[cut[1]:] == locality


@pytest.mark.parametrize("value", [
    "48 Quillfeather Lane",            # street only
    "Marrowdale, QX 00912",            # locality only
    "48 Quillfeather Lane, Suite 210",  # no town / state / postcode tail
    "7 rue des Lanternes, 99123 Bourg-Fictif",  # postcode-first forms stay one span
])
def test_street_split_leaves_other_addresses_whole(R, value):
    assert R.street_split(value) is None


def test_address_span_gives_street_and_locality_parts(R):
    text = "Ship to 48 Quillfeather Lane, Marrowdale, QX 00912 today"
    s, e = 8, 8 + len("48 Quillfeather Lane, Marrowdale, QX 00912")
    b = {"start": s, "end": e, "label": "LOCATION_ADDRESS", "text": text[s:e], "new_text": "ADDRESS_1"}
    out = R.native_report(text, [b])
    assert [(x["text"], x["new_text"]) for x in out] == [("48 Quillfeather Lane", "ADDRESS_1"),
                                                         ("Marrowdale, QX 00912", "ADDRESS_1")]
    syn = dict(b, new_text="17 Oak Spur, Fernhill, ZQ 00100")
    assert [x["new_text"] for x in R.native_report(text, [syn])] == ["17 Oak Spur", "Fernhill, ZQ 00100"]
    syn2 = dict(b, new_text="17 Oak Spur")  # the fake does not split: both parts get the whole fake
    assert [x["new_text"] for x in R.native_report(text, [syn2])] == ["17 Oak Spur", "17 Oak Spur"]


# ------------------------------------------------------------------------- what does not change (masked text)

def test_masked_text_and_text_report_do_not_change(R):
    st = MemoryStore(locale="en")
    m = Masker(st, locale="en", language="en", use_ner=False)
    text = "Signed by Mr. Corwin Aldous Pellbright on Monday. Write to 48 Quillfeather Lane, Marrowdale, OR 97999."
    m.mask(text)
    roles = R.name_roles(st, m)
    variants = R.mask_unit(m, text, __import__("collections").Counter())
    spans, codes = variants["mask"]
    text_report = R.bench_spans(text, spans, codes, roles, __import__("collections").Counter())
    # the text-level report (the human files) keeps one NAME_GIVEN span over the two given names
    assert any(b["label"] == "NAME_GIVEN" and b["text"] == "Corwin Aldous" for b in text_report), text_report
    assert [b["text"] for b in text_report if b["label"] == "LOCATION_ADDRESS"] == [
        "48 Quillfeather Lane, Marrowdale, OR 97999"]
    native = R.native_report(text, text_report)
    assert [b["text"] for b in native if b["label"] == "NAME_GIVEN"] == ["Corwin", "Aldous"]
    assert [b["text"] for b in native if b["label"] == "LOCATION_ADDRESS"] == ["48 Quillfeather Lane",
                                                                              "Marrowdale, OR 97999"]
    # every native part lies inside a masked span: the report changes, the protection does not
    for b in native:
        assert any(sp.start <= b["start"] and b["end"] <= sp.end for sp in spans), b
    covered = {i for sp in spans for i in range(sp.start, sp.end)}
    assert {i for b in native for i in range(b["start"], b["end"])} <= covered
