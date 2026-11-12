"""Score RAGbase Shield on the 19 MAPA Cour de cassation decisions (French).

Inputs: the WebAnno TSV gold (data/tsv) and plain texts (data/txt) from download.py, and the masked character
ranges written by run_shield.py (run/<doc>.json). Outputs in .bench_data/public/mapa-fr-cassation/scores/:
scores.json (every number), scores.md (the tables of RESULTS.md), misses.tsv, false_masks.tsv,
kept_masked.tsv.

Two families of measures:

A. Protection (the question a lawyer asks: does the identifying part of each person, organisation and address
   reach the AI?). Unit = one gold MAPA entity of label PERSON, ORGANISATION or ADDRESS. The entity is
   PROTECTED when every identifying token of it is masked (every letter and digit of the token lies inside a
   range Shield replaced by a code). Identifying tokens = the entity's tokens holding a letter or digit, minus:
     - PERSON: tokens MAPA itself labels as title (M., Mme, Monsieur), ROLE or PROFESSION (président,
       greffier de chambre), or date parts (day, month, year, day of week; dates mis-annotated as persons);
     - ORGANISATION: French function words and legal-form words (lists below), unless nothing would remain;
     - ADDRESS: French function words and street-type words (lists below), unless nothing would remain.
   An entity left with no identifying token (a bare "M." or "président" annotated PERSON) is reported apart and
   is not in the recall denominator. Partial = some identifying tokens masked, not all (it still leaks).
   Shield keeps dates, amounts, roles, courts and court cities in clear by design: ADDRESS mentions that are the
   city of a court ("cour d'appel de Paris", "arrêt attaqué (Paris, ...)") are reported apart, and DATE, AMOUNT,
   ROLE (and PROFESSION, TIME) entities are counted as "kept in clear by design", not as errors.
   False masks: tokens outside every gold PERSON/ORGANISATION/ADDRESS entity with at least one letter or digit
   replaced by a code, split into court names and court cities, judges and counsel, other.

B. MAPA's own measures (Arranz et al., LREC 2022 Legal and Ethical Issues workshop, section 5.2 and Figure 3):
   precision, recall, F1, F2 at the entity level (exact boundaries and type) and at the word level (labels
   B-X, I-X, <*-X> = either, <*> = any annotated entity, any Shield mask), specificity at the word level only,
   per document, with the micro-average (pooled counts) and the project's 0.895 threshold. Shield kinds are
   mapped PERSON -> PERSON, ORG -> ORGANISATION, ADDRESS -> ADDRESS; other Shield kinds (case numbers...) have
   no MAPA type and count only in <*>.

Usage: python evaluation/public/mapa-fr-cassation/score.py
"""
from __future__ import annotations

import bisect
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / ".bench_data" / "public" / "mapa-fr-cassation"
DATA = WORK / "data"
RUN = WORK / "run"
OUT = WORK / "scores"
sys.path.insert(0, str(HERE))
from download import DOCS  # noqa: E402

TARGETS = ("PERSON", "ORGANISATION", "ADDRESS")
BY_DESIGN = ("DATE", "AMOUNT", "ROLE", "PROFESSION", "TIME")
LEVEL1 = {"PERSON", "ORGANISATION", "ADDRESS", "DATE", "AMOUNT", "ROLE", "PROFESSION", "TIME", "FINANCIAL"}
NAME_PARTS = {"family name", "given name", "given name - male", "given name - female", "initial name"}
ADDRESS_PARTS = {"city", "street", "postcode", "country", "territory", "place", "building", "other:address",
                 "unresolved:address"}
PERSON_NON_ID = {"title", "ROLE", "PROFESSION", "day", "month", "year", "day of week"}
OTHER_SENSITIVE = {"FINANCIAL": "FINANCIAL (account number)", "unresolved:vehicle": "VEHICLE name"}
SHIELD_TO_MAPA = {"PERSON": "PERSON", "ORG": "ORGANISATION", "ADDRESS": "ADDRESS"}
THRESHOLD = 0.895

# Closed word lists, fixed before any Shield output was looked at.
FUNCTION_WORDS = {"le", "la", "les", "l", "l'", "de", "du", "des", "d", "d'", "et", "à", "au", "aux", "en", "sur",
                  "sous", "chez", "&", "of", "the", "and"}
LEGAL_FORMS = {"sa", "sas", "sasu", "sarl", "eurl", "snc", "scs", "sca", "sci", "scp", "scm", "sel", "selarl",
               "selas", "selafa", "selca", "gie", "gaec", "earl", "ltd", "limited", "plc", "llc", "inc", "corp",
               "corporation", "ag", "gmbh", "bv", "nv", "spa", "srl", "société", "sté"}
STREET_WORDS = {"rue", "avenue", "av", "boulevard", "bd", "place", "chemin", "allée", "impasse", "quai", "route",
                "sis", "sise"}

COURT_HEAD = (r"(?:cour administrative d'appel|cour d'appel|cour d'assises|cour de cassation|conseil de prud.hommes"
              r"|conseil d'[ée]tat|chambre de l'instruction|juridiction de proximit[ée]|tribunal(?:\s+[^,.;:\n()]{0,60}?)?"
              r"|juge (?:des libert[ée]s et de la d[ée]tention|d'instruction|de l'ex[ée]cution|des enfants|aux affaires"
              r" familiales|commissaire|de la mise en [ée]tat)|(?-i:\b(?:TGI|TJ|CPH|CA)\b))")
COURT_CITY_BEFORE = re.compile(
    r"(?:" + COURT_HEAD + r"\s+(?:de|d'|du|des)\s*(?:la\s+|l')?|" + COURT_HEAD + r"\s*\(\s*"
    r"|\b(?:arr[êe]t|jugement|ordonnance|d[ée]cision)s?\s+(?:attaqu[ée]|confirmatif|infirmatif|d[ée]f[ée]r[ée]|critiqu[ée])e?s?\s*\(\s*)$",
    re.I)
COURT_EXPR = re.compile(
    COURT_HEAD + r"(?:\s+(?:de|d'|du|des)\s*(?:la\s+|l')?[A-ZÉÈÀÎ][\w'’-]*(?:\s+(?:de|du|la|le|sur|en)?\s*[A-ZÉÈÀÎ][\w'’-]*)*)?"
    r"|\bCour de cassation\b", re.I)
COURT_ROLE = r"(?:premier pr[ée]sident|pr[ée]sidente?s?|conseill[eè]re?s?|greffi[eè]re?s?|avocats? g[ée]n[ée]ra(?:l|le|ux)|rapporteur|doyen|r[ée]f[ée]rendaires?|procureure?s?|magistrats?|juges?)"
COUNSEL_AFTER = re.compile(r"^\s*,?\s*avocats?\b(?!\s+g[ée]n[ée]ra)", re.I)
COURT_AFTER = re.compile(r"^\s*[,(]?\s*" + COURT_ROLE + r"\b", re.I)
PERSON_GAP = re.compile(r"^[\s,]*(?:et\s+)?(?:(?:M|Mme|Mmes|MM|Mlle|Me)\.?\s*)?$")


def has_alnum(s: str) -> bool:
    return any(ch.isalnum() for ch in s)


@dataclass
class Unit:
    tid: str
    start: int
    end: int
    text: str
    labels: list  # [(label, key)]
    sub: bool


@dataclass
class Ent:
    label: str
    key: str
    units: list  # unit indexes
    start: int = 0
    end: int = 0
    repaired: bool = False
    ident: list = field(default_factory=list)  # identifying unit indexes
    subtype: str = ""


# ----------------------------------------------------------------------------------------------- gold loading
def load_gold(doc: str):
    text = (DATA / "txt" / f"{doc}.txt").read_bytes().decode("utf-8-sig")
    units: list[Unit] = []
    sentences: list[tuple[int, int]] = []  # unit index range per sentence
    for line in (DATA / "tsv" / f"{doc}.tsv").read_text(encoding="utf-8").splitlines():
        if line.startswith("#Text="):
            sentences.append((len(units), len(units)))
            continue
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        s, e = map(int, p[1].split("-"))
        labels = []
        if p[4] not in ("_", ""):
            for v in p[4].split("|"):
                m = re.match(r"^(.*?)(?:\[(\d+)\])?$", v)
                labels.append((m.group(1), m.group(2) or f"u{p[0]}"))
        units.append(Unit(p[0], s, e, p[2], labels, "." in p[0]))
        if sentences:
            sentences[-1] = (sentences[-1][0], len(units))
    moved, failed = anchor(units, text)
    return text, units, sentences, moved, failed


def anchor(units: list[Unit], text: str) -> tuple[int, int]:
    """Re-anchor token offsets to the source text in reading order. The TSV offsets are exact for 18 files; one
    file (``-corrected``) had token texts edited without updating offsets."""
    moved = failed = 0
    pos = 0
    parent: dict[str, tuple[int, int]] = {}
    for u in units:
        if u.sub:
            base = u.tid.split(".")[0]
            old_s, new_s = parent.get(base, (u.start, u.start))
            s = new_s + (u.start - old_s)
            if text[s:s + len(u.text)] != u.text:
                q = text.find(u.text, new_s, new_s + 200)
                if q < 0:
                    failed += 1
                    continue
                s = q
        else:
            p = pos
            while p < len(text) and text[p].isspace():
                p += 1
            if text.startswith(u.text, p):
                s = p
            else:
                q = text.find(u.text, pos, pos + 200)
                if q < 0:
                    failed += 1
                    continue
                s = q
            parent[u.tid] = (u.start, s)
            pos = s + len(u.text)
        if s != u.start:
            moved += 1
        u.start, u.end = s, s + len(u.text)
    return moved, failed


def build_entities(units: list[Unit]) -> list[Ent]:
    groups: dict[tuple[str, str], list[int]] = {}
    for i, u in enumerate(units):
        for lab, key in u.labels:
            groups.setdefault((lab, key), []).append(i)
    ents = [Ent(lab, key, ix, min(units[i].start for i in ix), max(units[i].end for i in ix))
            for (lab, key), ix in groups.items()]
    level1 = [e for e in ents if e.label in LEVEL1]
    # Gold repair, reported: a name or address component annotated without its PERSON / ADDRESS block.
    # Orphan components of the same block type on consecutive tokens ("Christian" + "Normand") are one
    # entity, not one per component (checker fix 2026-10-17: they were counted as two persons).
    out = list(level1)
    repaired: list[Ent] = []
    for e in sorted(ents, key=lambda x: (x.start, x.end)):
        if e.label in LEVEL1 or e.label == "*":
            continue
        parent = [p for p in level1 if p.start <= e.start and e.end <= p.end]
        if parent:
            continue
        lab = "PERSON" if e.label in NAME_PARTS else "ADDRESS" if e.label in ADDRESS_PARTS else None
        if lab is None:
            continue
        prev = repaired[-1] if repaired else None
        if prev is not None and prev.label == lab and min(e.units) == max(prev.units) + 1:
            prev.units = prev.units + list(e.units)
            prev.end = max(prev.end, e.end)
            continue
        repaired.append(Ent(lab, "r" + e.key, list(e.units), e.start, e.end, repaired=True))
    out += repaired
    out.sort(key=lambda e: (e.start, e.end))
    return out


def identifying_units(ent: Ent, units: list[Unit], lab_index: dict) -> list[int]:
    alnum = [i for i in ent.units if has_alnum(units[i].text)]
    if ent.label == "PERSON":
        out = []
        for i in alnum:
            labs = {lab for _s, _e, lab, key in lab_index.get(i, ()) if key != ent.key}
            if labs & PERSON_NON_ID and not labs & NAME_PARTS:
                continue
            out.append(i)
        return out
    words = FUNCTION_WORDS | (LEGAL_FORMS if ent.label == "ORGANISATION" else STREET_WORDS)
    out = [i for i in alnum if units[i].text.lower().rstrip(".") not in words]
    if not out:
        out = [i for i in alnum if units[i].text.lower() not in FUNCTION_WORDS] or alnum
    return out


def overlapping_labels(units: list[Unit]) -> dict[int, list]:
    """unit index -> labels of every unit overlapping it (base tokens and sub-tokens)."""
    idx: dict[int, list] = defaultdict(list)
    order = sorted(range(len(units)), key=lambda i: units[i].start)
    for a_pos, i in enumerate(order):
        ui = units[i]
        for j in order[max(0, a_pos - 4):a_pos + 5]:
            uj = units[j]
            if uj.start < ui.end and ui.start < uj.end:
                idx[i].extend((uj.start, uj.end, lab, key) for lab, key in uj.labels)
    return idx


# ----------------------------------------------------------------------------------------------- classification
def is_court_city(ent: Ent, text: str) -> bool:
    line_start = text.rfind("\n", 0, ent.start) + 1
    before = text[max(line_start, ent.start - 150):ent.start]
    return bool(COURT_CITY_BEFORE.search(before))


def address_subtype(ent: Ent, units: list[Unit], text: str) -> str:
    if is_court_city(ent, text):
        return "court city"
    comps = {lab for i in ent.units for lab, _k in units[i].labels}
    if comps & {"street", "postcode", "building", "place"}:
        return "postal address"
    if "city" in comps:
        return "city"
    if comps & {"country", "territory"}:
        return "country or territory"
    return "other"


def family_names(ent: Ent, units: list[Unit], lab_index: dict) -> set[str]:
    out = set()
    for i in ent.units:
        labs = {lab for s, e, lab, key in lab_index.get(i, ())}
        if "family name" in labs:
            out.add(units[i].text.lower())
    return out


def classify_people(ents: list[Ent], units: list[Unit], text: str, lab_index: dict) -> None:
    """Heuristic split (reporting only): court members (judges, court clerks, advocates general) and counsel
    versus everyone else. Direct evidence: a nested ROLE or the text right after the mention; then lists
    ("Mmes A, B, C, conseillers") and same family name in the same decision."""
    people = [e for e in ents if e.label == "PERSON"]
    tag: dict[int, str] = {}
    for k, e in enumerate(people):
        roles = " ".join(units[i].text for i in e.units
                         if any(lab == "ROLE" for s, ee, lab, key in lab_index.get(i, ())))
        titles = {units[i].text for i in e.units if not units[i].sub
                  and any(lab == "title" for s, ee, lab, key in lab_index.get(i, ()))}
        after = text[e.end:e.end + 60]
        if re.search(COURT_ROLE, roles, re.I) or COURT_AFTER.search(after) or text[max(0, e.start - 1):e.start] == "(":
            tag[k] = "court"
        elif COUNSEL_AFTER.search(after) or titles & {"Me", "Maître", "Maitre"} or \
                re.search(r"\bavocats?\b(?!\s+g[ée]n)", roles, re.I):
            tag[k] = "counsel"
    # lists: consecutive mentions separated only by commas / "et" / titles share the tag of the last one
    k = 0
    while k < len(people):
        j = k
        while j + 1 < len(people) and PERSON_GAP.match(text[people[j].end:people[j + 1].start]):
            j += 1
        tags = [tag[m] for m in range(k, j + 1) if m in tag]
        if tags:
            for m in range(k, j + 1):
                tag.setdefault(m, tags[-1])
        k = j + 1
    names = defaultdict(set)
    for k, e in enumerate(people):
        if k in tag:
            for n in family_names(e, units, lab_index):
                names[n].add(tag[k])
    for k, e in enumerate(people):
        if k not in tag:
            hit = [t for n in family_names(e, units, lab_index) for t in names.get(n, ())]
            if hit:
                tag[k] = sorted(hit)[0]
        e.subtype = {"court": "court member", "counsel": "counsel"}.get(tag.get(k), "other person")


def classify_orgs(ents: list[Ent], units: list[Unit], text: str) -> None:
    orgs = [e for e in ents if e.label == "ORGANISATION"]
    norm = lambda e: " ".join(text[e.start:e.end].lower().split())  # noqa: E731
    counsel = {norm(e) for e in orgs if COUNSEL_AFTER.search(text[e.end:e.end + 40])}
    # a firm listed with other firms right before ", avocat" ("SCP A, SCP B, avocat de ...")
    for a, b in zip(orgs, orgs[1:]):
        if norm(b) in counsel and re.fullmatch(r"[\s,]*(?:et\s+)?(?:la\s+|de\s+la\s+)?", text[a.end:b.start]):
            counsel.add(norm(a))
    for e in orgs:
        e.subtype = "counsel firm" if norm(e) in counsel else "other organisation"


# ----------------------------------------------------------------------------------------------- scoring
def load_masks(doc: str, n: int):
    run = json.loads((RUN / f"{doc}.json").read_text(encoding="utf-8"))
    kind = [None] * n
    spans = run["spans"]
    for sp in spans:
        for i in range(sp["start"], sp["end"]):
            if kind[i] is None or sp["stage"] == "mask":
                kind[i] = sp["kind"]
    return run, kind, spans


TITLE_PREFIX = re.compile(r"^(?:M|Mme|Mmes|MM|Mlle|Me|Dr)\.\s*(?=\w)")


def unit_masked(u: Unit, text: str, kind: list, skip_title: bool = False) -> tuple[bool, bool]:
    """(fully masked, partly masked) over the unit's letters and digits. ``skip_title``: a title glued to a
    name in one token ("M.André", annotated title + family name) is not an identifying part."""
    first = u.start
    if skip_title:
        m = TITLE_PREFIX.match(u.text)
        first += m.end() if m else 0
    pos = [i for i in range(first, u.end) if text[i].isalnum()]
    hit = [i for i in pos if kind[i] is not None]
    return bool(pos) and len(hit) == len(pos), bool(hit)


def prf(tp: int, fp: int, fn: int, tn: int | None = None) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    if tp:
        f1, f2 = 2 * p * r / (p + r), 5 * p * r / (4 * p + r)
    else:  # zero_division = 0 when there is any gold or any prediction; undefined when there is neither
        f1 = f2 = 0.0 if fp or fn else None
    out = {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1, "f2": f2}
    if tn is not None:
        out["tn"] = tn
        out["specificity"] = tn / (tn + fp) if tn + fp else None
    return out


def score_doc(doc: str) -> dict:
    text, units, sentences, moved, failed = load_gold(doc)
    ents = build_entities(units)
    lab_index = overlapping_labels(units)
    run, kind, spans = load_masks(doc, len(text))
    classify_people(ents, units, text, lab_index)
    classify_orgs(ents, units, text)
    res = {"doc": doc, "tokens_reanchored": moved, "tokens_unanchored": failed,
           "chars": len(text), "base_tokens": sum(1 for u in units if not u.sub),
           "gold_repaired": Counter(e.label for e in ents if e.repaired)}

    # ---- A. protection
    prot = []
    for e in ents:
        if e.label not in TARGETS:
            continue
        if e.label == "ADDRESS":
            e.subtype = address_subtype(e, units, text)
        e.ident = identifying_units(e, units, lab_index)
        if not e.ident:
            status = "no identifying token"
        else:
            full = [unit_masked(units[i], text, kind, skip_title=e.label == "PERSON") for i in e.ident]
            if all(f for f, _p in full):
                status = "protected"
            elif any(p for _f, p in full):
                status = "partial"
            else:
                status = "missed"
        lower_only = False
        if status == "partial":
            left = [units[i].text for i in e.ident
                    if not unit_masked(units[i], text, kind, skip_title=e.label == "PERSON")[0]]
            lower_only = all(w[:1].islower() for w in left)
        kinds = Counter(kind[c] for i in e.ident for c in range(units[i].start, units[i].end)
                        if text[c].isalnum() and kind[c] is not None)
        main_kind = kinds.most_common(1)[0][0] if kinds else None
        prot.append({"label": e.label, "subtype": e.subtype, "status": status, "repaired": e.repaired,
                     "text": text[e.start:e.end].replace("\n", " "), "start": e.start, "end": e.end,
                     "ident": " ".join(units[i].text for i in e.ident),
                     "shield_kind": main_kind, "partial_lowercase_only": lower_only,
                     "kind_ok": main_kind is not None and SHIELD_TO_MAPA.get(main_kind) == e.label})
    res["protection"] = prot

    # ---- kept in clear by design
    kept = []
    for e in ents:
        if e.label not in BY_DESIGN:
            continue
        al = [i for i in e.units if has_alnum(units[i].text)]
        st = [unit_masked(units[i], text, kind) for i in al]
        masked_any = any(p for _f, p in st)
        kinds = sorted({kind[c] for i in al for c in range(units[i].start, units[i].end) if kind[c]})
        kept.append({"label": e.label, "text": text[e.start:e.end].replace("\n", " "),
                     "masked": masked_any, "shield_kinds": kinds})
    res["kept"] = kept

    # ---- other MAPA labels, outside the scored labels and outside the kept-clear list (reported, not scored)
    groups: dict[tuple[str, str], list[int]] = {}
    for i, u in enumerate(units):
        for lab, key in u.labels:
            if lab in OTHER_SENSITIVE:
                groups.setdefault((lab, key), []).append(i)
    other = []
    for (lab, _key), ix in groups.items():
        al = [i for i in ix if has_alnum(units[i].text)]
        st = [unit_masked(units[i], text, kind) for i in al]
        other.append({"label": OTHER_SENSITIVE[lab], "text": " ".join(units[i].text for i in ix),
                      "masked_fully": bool(st) and all(f for f, _p in st), "masked_any": any(p for _f, p in st)})
    res["other_sensitive"] = other

    # ---- false masks: base tokens outside every gold PERSON/ORGANISATION/ADDRESS entity
    target_cover = [False] * len(text)
    for e in ents:
        if e.label in TARGETS:
            for i in e.units:
                for c in range(units[i].start, units[i].end):
                    target_cover[c] = True
    other_label = [None] * len(text)
    for e in ents:
        if e.label not in TARGETS:
            for i in e.units:
                for c in range(units[i].start, units[i].end):
                    other_label[c] = other_label[c] or e.label
    court_cover = [False] * len(text)
    for m in COURT_EXPR.finditer(text):
        for c in range(m.start(), m.end()):
            court_cover[c] = True
    court_people = [e for e in ents if e.label == "PERSON" and e.subtype in ("court member", "counsel")] + \
                   [e for e in ents if e.label == "ORGANISATION" and e.subtype == "counsel firm"]
    fm = []
    outside = 0
    for u in units:
        if u.sub or not has_alnum(u.text):
            continue
        alnum = [c for c in range(u.start, u.end) if text[c].isalnum()]
        if any(target_cover[c] for c in alnum):
            continue
        outside += 1
        hit = [c for c in alnum if kind[c] is not None]
        if not hit:
            continue
        k = Counter(kind[c] for c in hit).most_common(1)[0][0]
        lab = next((other_label[c] for c in alnum if other_label[c]), None)
        if any(court_cover[c] for c in alnum):
            cat = "court names and court cities"
        elif k in ("PERSON", "ORG") and any(abs(u.start - e.end) <= 40 or abs(e.start - u.end) <= 40
                                            for e in court_people) and u.text[:1].isupper():
            cat = "judges and counsel (not annotated)"
        else:
            cat = "other"
        if lab in BY_DESIGN:
            sub = f"inside gold {lab} (kept in clear by design)"
        elif lab:
            sub = f"inside gold {lab} (sensitive, outside the 3 scored labels)"
        elif k == "CASE_REF":
            sub = "case number (Shield masks case references by design)"
        else:
            sub = f"unannotated text, coded {k}"
        a, b = max(0, u.start - 40), min(len(text), u.end + 40)
        fm.append({"token": u.text, "category": cat, "detail": sub, "shield_kind": k,
                   "context": text[a:b].replace("\n", " ")})
    res["false_masks"] = fm
    res["outside_alnum_tokens"] = outside
    # masked spans not touching any gold PERSON/ORGANISATION/ADDRESS
    res["spans_total"] = len(spans)
    res["spans_outside_targets"] = Counter(sp["kind"] for sp in spans
                                           if not any(target_cover[c] for c in range(sp["start"], sp["end"])))

    # ---- B. MAPA measures
    base = [u for u in units if not u.sub]
    starts = [u.start for u in base]

    def toks_of(s: int, e: int) -> list[int]:
        lo = max(0, bisect.bisect_right(starts, s) - 2)
        out = []
        for t in range(lo, len(base)):
            u = base[t]
            if u.start >= e:
                break
            if u.start < e and s < u.end:
                out.append(t)
        return out

    mapa = {}
    any_gold = [False] * len(base)
    for e in ents:
        for i in e.units:
            for t in toks_of(units[i].start, units[i].end):
                any_gold[t] = True
    any_pred = [False] * len(base)
    for sp in spans:
        for t in toks_of(sp["start"], sp["end"]):
            any_pred[t] = True
    for T in TARGETS:
        gold_tag = [None] * len(base)
        gold_sets = []
        for e in ents:
            if e.label != T:
                continue
            toks = sorted({t for i in e.units for t in toks_of(units[i].start, units[i].end)})
            if not toks:
                continue
            gold_sets.append(frozenset(toks))
            for n, t in enumerate(toks):
                if n == 0 or gold_tag[t] is None:
                    gold_tag[t] = "B" if n == 0 else "I"
        pred_tag = [None] * len(base)
        pred_sets = []
        for sp in spans:
            if SHIELD_TO_MAPA.get(sp["kind"]) != T:
                continue
            toks = toks_of(sp["start"], sp["end"])
            if not toks:
                continue
            pred_sets.append(frozenset(toks))
            for n, t in enumerate(toks):
                if n == 0 or pred_tag[t] is None:
                    pred_tag[t] = "B" if n == 0 else "I"
        row = {}
        for name, g_ok, p_ok in (("B", lambda x: x == "B", lambda x: x == "B"),
                                 ("I", lambda x: x == "I", lambda x: x == "I"),
                                 ("*", lambda x: x is not None, lambda x: x is not None)):
            tp = sum(1 for g, p in zip(gold_tag, pred_tag) if g_ok(g) and p_ok(p))
            fp = sum(1 for g, p in zip(gold_tag, pred_tag) if not g_ok(g) and p_ok(p))
            fn = sum(1 for g, p in zip(gold_tag, pred_tag) if g_ok(g) and not p_ok(p))
            tn = len(base) - tp - fp - fn
            row[f"word {name}-{T}"] = prf(tp, fp, fn, tn)
        gs, ps = Counter(gold_sets), Counter(pred_sets)
        tp = sum(min(c, ps[s]) for s, c in gs.items())
        row[f"entity {T}"] = prf(tp, sum(ps.values()) - tp, sum(gs.values()) - tp)
        mapa.update(row)
    tp = sum(1 for g, p in zip(any_gold, any_pred) if g and p)
    fp = sum(1 for g, p in zip(any_gold, any_pred) if not g and p)
    fn = sum(1 for g, p in zip(any_gold, any_pred) if g and not p)
    mapa["word <*>"] = prf(tp, fp, fn, len(base) - tp - fp - fn)
    # Adaptation (not in the paper): <*> restricted to the 3 scored labels, any Shield mask counts.
    poa_gold = [False] * len(base)
    for e in ents:
        if e.label in TARGETS:
            for i in e.units:
                for t in toks_of(units[i].start, units[i].end):
                    poa_gold[t] = True
    tp = sum(1 for g, p in zip(poa_gold, any_pred) if g and p)
    fp = sum(1 for g, p in zip(poa_gold, any_pred) if not g and p)
    fn = sum(1 for g, p in zip(poa_gold, any_pred) if g and not p)
    mapa["word <*> over PERSON/ORGANISATION/ADDRESS only (adaptation)"] = prf(tp, fp, fn, len(base) - tp - fp - fn)
    res["mapa"] = mapa
    return res


# ----------------------------------------------------------------------------------------------- report
def pct(a: int, b: int) -> str:
    return "n/a" if not b else f"{100.0 * a / b:.1f}%"


def f3(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def main() -> int:
    if not RUN.exists():
        sys.exit("missing run/: run run_shield.py first")
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((RUN / "run_meta.json").read_text(encoding="utf-8"))
    docs = [score_doc(doc) for doc, _c, _s in DOCS]
    md: list[str] = []
    summary: dict = {"run": meta, "documents": len(docs)}

    # gold inventory
    inv = Counter()
    for d in docs:
        for p in d["protection"]:
            inv[p["label"]] += 1
        for k in d["kept"]:
            inv[k["label"]] += 1
    summary["gold_entities"] = dict(inv)
    summary["gold_repaired"] = dict(sum((Counter(d["gold_repaired"]) for d in docs), Counter()))
    summary["tokens_reanchored"] = {d["doc"]: d["tokens_reanchored"] for d in docs if d["tokens_reanchored"]}
    summary["tokens_unanchored"] = sum(d["tokens_unanchored"] for d in docs)

    # ---- protection table
    def agg(rows):
        c = Counter(r["status"] for r in rows)
        n = c["protected"] + c["partial"] + c["missed"]
        return c, n

    md += ["## Protection recall (PERSON, ORGANISATION, ADDRESS)", "",
           "| Label | Gold entities | No identifying token (not scored) | Scored | Protected | Partial (leaks) | Missed | Recall (protected / scored) | Protected with the matching Shield kind | Partial where only lowercase words stayed in clear |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    prot_all = [p for d in docs for p in d["protection"]]
    table = {}
    for name, rows in (
            ("PERSON", [p for p in prot_all if p["label"] == "PERSON"]),
            ("ORGANISATION", [p for p in prot_all if p["label"] == "ORGANISATION"]),
            ("ADDRESS, court cities excluded", [p for p in prot_all if p["label"] == "ADDRESS" and p["subtype"] != "court city"]),
            ("All three, court cities excluded", [p for p in prot_all if not (p["label"] == "ADDRESS" and p["subtype"] == "court city")]),
            ("ADDRESS, all (court cities included)", [p for p in prot_all if p["label"] == "ADDRESS"]),
    ):
        c, n = agg(rows)
        kok = sum(1 for r in rows if r["status"] == "protected" and r["kind_ok"])
        low = sum(1 for r in rows if r["status"] == "partial" and r["partial_lowercase_only"])
        table[name] = {"gold": len(rows), "no_identifying": c["no identifying token"], "scored": n,
                       "protected": c["protected"], "partial": c["partial"], "missed": c["missed"],
                       "recall": c["protected"] / n if n else None, "protected_kind_ok": kok,
                       "partial_lowercase_only": low,
                       "recall_if_lowercase_partials_counted": (c["protected"] + low) / n if n else None}
        md.append(f"| {name} | {len(rows)} | {c['no identifying token']} | {n} | {c['protected']} | {c['partial']} | "
                  f"{c['missed']} | {pct(c['protected'], n)} ({c['protected']}/{n}) | {pct(kok, c['protected'])} ({kok}/{c['protected']}) | {low} |")
    summary["protection"] = table
    md.append("")

    md += ["### By subtype", "",
           "| Label | Subtype | Scored | Protected | Partial | Missed | Recall |", "|---|---|---|---|---|---|---|"]
    sub = {}
    for lab in TARGETS:
        for st in sorted({p["subtype"] for p in prot_all if p["label"] == lab}):
            rows = [p for p in prot_all if p["label"] == lab and p["subtype"] == st]
            c, n = agg(rows)
            sub[f"{lab} / {st}"] = {"scored": n, "protected": c["protected"], "partial": c["partial"],
                                    "missed": c["missed"], "no_identifying": c["no identifying token"]}
            md.append(f"| {lab} | {st} | {n} | {c['protected']} | {c['partial']} | {c['missed']} | "
                      f"{pct(c['protected'], n)} ({c['protected']}/{n}) |")
    summary["protection_by_subtype"] = sub
    md.append("")

    # ---- kept in clear
    kept_all = [k for d in docs for k in d["kept"]]
    md += ["## Kept in clear by design (not errors)", "",
           "| Label | Gold entities | Left fully in clear | Masked anyway (at least one letter or digit) | Shield kinds when masked |",
           "|---|---|---|---|---|"]
    kt = {}
    for lab in BY_DESIGN:
        rows = [k for k in kept_all if k["label"] == lab]
        if not rows:
            continue
        m = [k for k in rows if k["masked"]]
        kinds = Counter(x for k in m for x in k["shield_kinds"])
        kt[lab] = {"gold": len(rows), "clear": len(rows) - len(m), "masked": len(m), "kinds": dict(kinds)}
        md.append(f"| {lab} | {len(rows)} | {len(rows) - len(m)} | {len(m)} | "
                  f"{', '.join(f'{k} {v}' for k, v in kinds.most_common()) or '-'} |")
    oth = [o for d in docs for o in d["other_sensitive"]]
    cc = [p for p in prot_all if p["label"] == "ADDRESS" and p["subtype"] == "court city"]
    ccm = sum(1 for p in cc if p["status"] in ("protected", "partial"))
    md.append(f"| ADDRESS that is a court city | {len(cc)} | {len(cc) - ccm} | {ccm} | - |")
    kt["ADDRESS court city"] = {"gold": len(cc), "clear": len(cc) - ccm, "masked": ccm}
    summary["kept_in_clear"] = kt
    md.append("")
    md += ["## Other MAPA labels (sensitive, outside the three scored labels; reported, not scored)", "",
           "| Label | Gold mentions | Fully masked | Partly masked | Left in clear |", "|---|---|---|---|---|"]
    os_ = {}
    for lab in sorted({o["label"] for o in oth}):
        rows = [o for o in oth if o["label"] == lab]
        fully = sum(1 for o in rows if o["masked_fully"])
        part = sum(1 for o in rows if o["masked_any"] and not o["masked_fully"])
        os_[lab] = {"gold": len(rows), "fully": fully, "partly": part, "clear": len(rows) - fully - part}
        md.append(f"| {lab} | {len(rows)} | {fully} | {part} | {len(rows) - fully - part} |")
    summary["other_sensitive"] = os_
    md.append("")

    # ---- false masks
    fm_all = [dict(f, doc=d["doc"]) for d in docs for f in d["false_masks"]]
    ntok = sum(d["base_tokens"] for d in docs)
    outside = sum(d["outside_alnum_tokens"] for d in docs)
    cats = Counter(f["category"] for f in fm_all)
    fmc = Counter((f["category"], f["detail"]) for f in fm_all)
    n_case = sum(n for (c, det), n in fmc.items() if det.startswith("case number"))
    md += ["## False masks (tokens outside every gold PERSON / ORGANISATION / ADDRESS)", "",
           f"Base tokens with a letter or digit outside every gold PERSON / ORGANISATION / ADDRESS entity: {outside:,}. "
           f"Masked: {len(fm_all)} ({pct(len(fm_all), outside)}); without case numbers, which Shield masks by "
           f"design: {len(fm_all) - n_case} ({pct(len(fm_all) - n_case, outside)}).", "",
           "| Category | Detail | Tokens |", "|---|---|---|"]
    for cat in ("court names and court cities", "judges and counsel (not annotated)", "other"):
        md.append(f"| {cat} | all | {cats.get(cat, 0)} |")
        for (c, det), n in sorted(fmc.items(), key=lambda x: -x[1]):
            if c == cat:
                md.append(f"| | {det} | {n} |")
    md.append(f"| **Total** | | **{len(fm_all)}** |")
    md.append("")
    summary["false_masks"] = {"total_tokens": len(fm_all), "by_category": dict(cats),
                              "by_category_detail": {f"{a} | {b}": n for (a, b), n in fmc.items()},
                              "alnum_tokens_outside_targets": outside, "base_tokens_in_corpus": ntok}
    so = sum((Counter(d["spans_outside_targets"]) for d in docs), Counter())
    st_total = sum(d["spans_total"] for d in docs)
    summary["masked_spans"] = {"total": st_total, "outside_targets_by_kind": dict(so)}

    # ---- per document
    md += ["## Per document", "",
           "| Document | Chars | PERSON protected | ORGANISATION protected | ADDRESS protected (court cities excl.) | Court cities masked | False-mask tokens | DATE / AMOUNT / ROLE kept-clear entities |",
           "|---|---|---|---|---|---|---|---|"]
    per = []
    for d in docs:
        row = {"doc": d["doc"], "chars": d["chars"]}
        cells = []
        for lab in TARGETS:
            rows = [p for p in d["protection"] if p["label"] == lab and not (lab == "ADDRESS" and p["subtype"] == "court city")]
            c, n = agg(rows)
            row[lab] = [c["protected"], n]
            cells.append(f"{c['protected']}/{n}")
        ccd = [p for p in d["protection"] if p["label"] == "ADDRESS" and p["subtype"] == "court city"]
        ccdm = sum(1 for p in ccd if p["status"] in ("protected", "partial"))
        kc = Counter(k["label"] for k in d["kept"])
        row.update(court_cities=[ccdm, len(ccd)], false_masks=len(d["false_masks"]), kept=dict(kc))
        per.append(row)
        md.append(f"| {d['doc']} | {d['chars']:,} | " + " | ".join(cells) +
                  f" | {ccdm}/{len(ccd)} | {len(d['false_masks'])} | {kc['DATE']} / {kc['AMOUNT']} / {kc['ROLE']} |")
    tot = {lab: [sum(r[lab][0] for r in per), sum(r[lab][1] for r in per)] for lab in TARGETS}
    md.append(f"| **Total** | {sum(d['chars'] for d in docs):,} | " +
              " | ".join(f"**{tot[l][0]}/{tot[l][1]}**" for l in TARGETS) +
              f" | {sum(r['court_cities'][0] for r in per)}/{sum(r['court_cities'][1] for r in per)} | "
              f"{sum(r['false_masks'] for r in per)} | {inv['DATE']} / {inv['AMOUNT']} / {inv['ROLE']} |")
    md.append("")
    summary["per_document"] = per

    # ---- MAPA measures
    keys = list(docs[0]["mapa"].keys())
    micro = {}
    for k in keys:
        tp = sum(d["mapa"][k]["tp"] for d in docs)
        fp = sum(d["mapa"][k]["fp"] for d in docs)
        fn = sum(d["mapa"][k]["fn"] for d in docs)
        tn = sum(d["mapa"][k]["tn"] for d in docs) if "tn" in docs[0]["mapa"][k] else None
        micro[k] = prf(tp, fp, fn, tn)
        vals = [d["mapa"][k]["recall"] for d in docs if d["mapa"][k]["recall"] is not None]
        micro[k]["docs_with_gold"] = len(vals)
        micro[k]["docs_recall_ge_threshold"] = sum(1 for v in vals if v >= THRESHOLD)
        f2s = [d["mapa"][k]["f2"] for d in docs if d["mapa"][k]["f2"] is not None]
        micro[k]["docs_f2_ge_threshold"] = sum(1 for v in f2s if v >= THRESHOLD)
        micro[k]["docs_f2_defined"] = len(f2s)
    summary["mapa_micro"] = micro
    summary["mapa_per_document"] = {d["doc"]: d["mapa"] for d in docs}
    md += ["## MAPA measures (paper section 5.2), micro-average over the 19 documents", "",
           "| Measure | TP | FP | FN | Precision | Recall | F1 | F2 | Specificity | Docs with recall >= 0.895 | Docs with F2 >= 0.895 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        m = micro[k]
        md.append(f"| {k} | {m['tp']} | {m['fp']} | {m['fn']} | {f3(m['precision'])} | {f3(m['recall'])} | "
                  f"{f3(m['f1'])} | {f3(m['f2'])} | {f3(m.get('specificity'))} | "
                  f"{m['docs_recall_ge_threshold']}/{m['docs_with_gold']} | {m['docs_f2_ge_threshold']}/{m['docs_f2_defined']} |")
    md.append("")

    # ---- files
    with (OUT / "misses.tsv").open("w", encoding="utf-8") as fh:
        fh.write("doc\tlabel\tsubtype\tstatus\tshield_kind\tidentifying\tentity\n")
        for d in docs:
            for p in d["protection"]:
                if p["status"] != "protected":
                    fh.write(f"{d['doc']}\t{p['label']}\t{p['subtype']}\t{p['status']}\t{p['shield_kind']}\t"
                             f"{p['ident']}\t{p['text']}\n")
    with (OUT / "false_masks.tsv").open("w", encoding="utf-8") as fh:
        fh.write("doc\tcategory\tdetail\tshield_kind\ttoken\tcontext\n")
        for f in fm_all:
            fh.write(f"{f['doc']}\t{f['category']}\t{f['detail']}\t{f['shield_kind']}\t{f['token']}\t{f['context']}\n")
    with (OUT / "kept_masked.tsv").open("w", encoding="utf-8") as fh:
        fh.write("doc\tlabel\tshield_kinds\tentity\n")
        for d in docs:
            for k in d["kept"]:
                if k["masked"]:
                    fh.write(f"{d['doc']}\t{k['label']}\t{','.join(k['shield_kinds'])}\t{k['text']}\n")
    (OUT / "scores.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (OUT / "scores.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(json.dumps({k: summary[k] for k in ("gold_entities", "gold_repaired", "tokens_reanchored",
                                                "tokens_unanchored", "masked_spans")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
