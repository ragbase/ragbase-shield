"""Tool-agnostic scorer for the laptop head-to-head (Shield, Hexagone, Tonic, Presidio).

Pre-registered (PROTOCOL.md section 8). It needs only three things per document: the input text, the tool's
output text and the gold. It never needs a tool's spans, kinds or logs, so every tool is scored the same way,
whatever its replacement style: codes (``PERSONNE_A``), tags (``[a.PERSON_1]``, ``<PERSON>``, ``[REDACTED]``),
realistic fake values, or plain deletion.

Version 1.1 (drafted 2026-10-23 by the protocol critic, finalised 2026-10-24 by the fairness review; the rules
are PROTOCOL_ADDENDUM_1.md, which is section 17 of the protocol; the review is <work>/PROTOCOL_CRITIC.md).
Changes from 1.0, each tested on invented cases for codes, tags, realistic fake values and deletion (``--selftest``
and <work>/critic/fairness_cases.py): tokens are compared case-, accent- and compatibility-folded and
the output is NFC-normalised; a fake value that equals another real value no longer shifts the alignment
(lexicographic repair); a moved block is found again; words split or glued by a re-rendered file are rejoined; a
second, value-level reading of exposure; public or reserved mail domains and format tokens shared by every value
of a type do not identify; keep items (like gold items in 1.0) in document properties, and gold and keep items in
tracked deletions, are reported apart; statuses ``not_run`` and ``unscorable``; run-log rows are matched by
doc_id or by file. Removed by the review (no scoring error fixed): the critic's "dropped with its context" count,
its cue split for person names and its "must stay clear without court_city" line.

How it works

1. Both texts are cut into tokens: runs of letters, digits and "_" (``\\w+``), and single other non-space
   characters. White space is ignored, so a change of line breaks or spaces is not a change. Tokens are compared
   by a KEY: NFKC, then lower case without accents. The output is NFC-normalised first (decomposed accents would
   otherwise split words). So "DUPONT", "Dupont" and "Dupônt" are the same token: a case or accent change is not
   a protection.
2. Alignment in three passes.
   a. Lines are compared as token sequences; equal lines are aligned token by token; inside each block of lines
      that differ, tokens are aligned by a patience diff (tokens unique on both sides are anchors, then
      ``difflib.SequenceMatcher`` in the gaps). Repair: between two aligned words that are outside every gold
      item, when a gold word was aligned while an unchanged word outside gold was left out (a fake value equal to
      another real value, "Jean Dupont et Paul Martin" -> "Paul Martin et Luc Bernard"), that stretch is aligned
      again so as to keep first the most words outside gold, then the most gold words (dynamic programming).
      Words outside gold that equal an identifying word of a gold item ("Roux" of "cabinet Roux" when "Claire
      Roux" is gold), and words of document properties and tracked deletions (point 7), count as gold words for
      this repair.
   b. Moved blocks: the input tokens still unmatched (gold included) are aligned with the output tokens still
      unmatched, over the whole document; only runs of 6 or more identical tokens with 4 or more letter-or-digit
      tokens are accepted (a paragraph a reader puts elsewhere, for example footer and footnotes in another order).
   c. Gaps: each run of unmatched input tokens is aligned with the unmatched output tokens between its two
      neighbours' places (or, when they cross, the next output tokens).
   An input token is KEPT when aligned with an output token of the same key; otherwise CHANGED (replaced or
   deleted).
3. Rejoin: a keep item that looks altered, or a gold item that looks protected or partial, is checked once more
   on its letters and digits alone: when its folded letters and digits appear, in one piece, in the output
   between its two kept neighbours, and that stretch is at most 12 letters or digits longer, the item is read
   as unchanged (a word split or glued by a re-rendered PDF or Word file is not a change; a real value kept inside
   a code, "LANMAS_1", is readable too). A string of fewer than 8 letters or digits must also start and end on
   output token boundaries. Counted as "rejoined".
4. Gold item (personal data to protect). Its identifying tokens are its letter-or-digit tokens, minus words that
   do not identify on their own, unless that leaves none:
     - titles for persons; function words and legal forms for organisations; function words and street words for
       addresses; for e-mail addresses and URLs the words fr, com, net, org, eu, io, be, ch, de, uk, co, gouv,
       info, biz, www, http, https, mailto and the public or reserved mail domains (example, gmail, hotmail,
       outlook, yahoo, orange, free, laposte...);
     - format tokens that every value of the type shares: a phone number's country code and its first group
       when it is two digits starting with 0 (06, 01...); an IBAN's country-and-check group (FR76); a NIR's first
       digit (1 or 2). Only when other tokens remain.
   When the gold gives ``ident`` ranges (MAPA), the identifying tokens are exactly the tokens of those ranges.
   Status at its place:
     - protected: every identifying token changed;
     - partial:   some identifying tokens kept (a leak);
     - missed:    every identifying token kept (a leak).
   Headline (a), STRICT reading: "exposed" = partial + missed.
   VALUE reading (robust to realistic fake values that share a token with the real one by chance): "exposed
   (value)" when more than half of the identifying letters and digits are kept at its place.
   A P1 claim needs both readings (PROTOCOL_ADDENDUM_1.md section 17.4, which amends PROTOCOL.md section 11.3).
   Second check, anywhere: the identifying string (identifying tokens in order, folded, one space between tokens)
   is searched as whole words in the folded output. For a value with 8 or more digits that are at least 60 % of
   its letters and digits, the digit string is also searched with spaces removed. Values with fewer than 4
   letters or digits are not searched. Secondary only: a realistic fake can equal another person's real value.
   Third reading, for comparison with FR-PII-Bench's own rule: the share of the gold span's characters that lie
   inside changed regions; "covered" when it is 0.80 or more.
5. Keep item (must stay readable: courts, court cities, articles, codes, laws, legal terms; secondary classes:
   dates, amounts, roles, placeholders...): ALTERED when any of its letter-or-digit tokens changed and the rejoin
   check fails (headline (b)). Keep items that overlap a gold item are dropped when the gold is built, never here.
6. Over-masking without a list: every changed region (consecutive changed tokens on one line) that touches no gold
   item is a FALSE-MASK REGION; the letter-or-digit tokens changed outside every gold item are counted;
   RETENTION = share of the letter-or-digit tokens outside gold that are kept.
7. Parts. Gold and keep items inside document properties (part "metadata": the "creator: ..." lines the reader
   writes for .docx, .pdf and .xlsx files) or inside tracked deletions of a .docx (part "hidden", from the
   reader's ``hidden_ranges``) are reported apart and are not in the headlines (a) and (b); the words of those
   parts are not in the over-masking counts.
8. Statuses. FAILED (the run log says ``failed``, the output file is missing or unreadable, or the retention is
   under 0.50 when the document has at least 20 letter-or-digit tokens outside gold): every gold item is exposed
   (missed), keep items are not counted as altered, and no region is counted. NOT_RUN (run log ``not_run``: the
   tool never received the document, for example the trial ended or the word quota ran out) and UNSCORABLE (the
   output is a PDF with images and no text layer): no item is counted; the document is listed and left out of
   every paired comparison, on both sides (PROTOCOL_ADDENDUM_1.md section 17.5).

Inputs

- gold JSONL (built by ``prepare_sets.py`` or ``make_reference_doc.py``), one line per document:
  ``{"set", "doc_id", "file", "text_sha256", "chars", "text" (optional), "gold": [{"id", "label", "start",
  "end", "text", "ident" (optional [[s, e], ...]), "non_identifying" (optional [words]), "part" (optional)}],
  "keep": [{"id", "class", "start", "end", "text"}]}``. Offsets are in the text that ``extract_text.py`` reads
  from the input file.
- the input folder (``file`` is relative to it) unless the gold line carries ``text``;
- the output folder of one tool run: for input ``a/b/name.ext`` the output is ``a/b/name.<any supported ext>``
  (exactly one), or a run manifest (``--outputs-manifest``, JSONL ``{"doc_id", "output"}``);
- the run log (JSONL ``{"doc_id", "status": "ok"|"failed"|"not_run", "reason"}``, optional; a row is matched by
  the gold ``doc_id`` or, failing that, by the gold ``file``; a document with no output is failed anyway).

Usage
  python score_text.py score --gold G.jsonl --inputs IN_DIR --outputs OUT_DIR [--runlog RUN.jsonl]
                             --json RESULT.json [--md RESULT.md] [--tool NAME]
  python score_text.py pairs --gold G.jsonl --pairs P.jsonl --json RESULT.json   (P: {"doc_id", "output_text"})
  python score_text.py --selftest
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

SCORER_VERSION = "laptop-score-1.1"

TOKEN_RE = re.compile(r"\w+|[^\w\s]")

# ---------------------------------------------------------------------------------------------- word lists
# Fixed before any competitor run. The function-word, legal-form and street-word lists are the ones of the MAPA
# scorer (evaluation/public/mapa-fr-cassation/score.py, unchanged since 2026-10-17), plus English function words
# and the title words below. The mail-domain and format-token rules were added in 1.1 (fairness review): they
# remove only tokens that every value of the type shares, so a tool that keeps them leaks nothing.
FUNCTION_WORDS = {"le", "la", "les", "l", "de", "du", "des", "d", "et", "à", "au", "aux", "en", "sur", "sous",
                  "chez", "of", "the", "and"}
LEGAL_FORMS = {"sa", "sas", "sasu", "sarl", "eurl", "snc", "scs", "sca", "sci", "scp", "scm", "sel", "selarl",
               "selas", "selafa", "selca", "gie", "gaec", "earl", "ltd", "limited", "plc", "llc", "inc", "corp",
               "corporation", "ag", "gmbh", "bv", "nv", "spa", "srl", "société", "sté"}
STREET_WORDS = {"rue", "avenue", "av", "boulevard", "bd", "place", "chemin", "allée", "impasse", "quai", "route",
                "sis", "sise"}
TITLE_WORDS = {"m", "mme", "mmes", "mm", "mlle", "mlles", "monsieur", "madame", "mademoiselle", "messieurs",
               "mesdames", "me", "maître", "maitre", "dr", "docteur", "pr", "professeur", "mr", "mrs", "ms",
               "miss"}
PERSON_LABELS = {"PERSON", "PERSONNE", "NAME", "NAME_GIVEN", "NAME_FAMILY", "PROFESSIONAL_NAME"}
ORG_LABELS = {"ORG", "ORGANISATION", "ORGANIZATION", "COMPANY", "SOCIETE"}
ADDRESS_LABELS = {"ADDRESS", "LOCATION_ADDRESS", "PLACE", "ADRESSE"}
NET_LABELS = {"EMAIL", "EMAIL_ADDRESS", "URL", "COURRIEL"}
PHONE_LABELS = {"PHONE", "PHONE_NUMBER", "TELEPHONE", "TEL"}
IBAN_LABELS = {"IBAN", "IBAN_CODE"}
NIR_LABELS = {"NIR"}
NET_WORDS = {"fr", "com", "net", "org", "eu", "io", "be", "ch", "de", "uk", "co", "gouv", "info", "biz", "www",
             "http", "https", "mailto"}
# public mail services and reserved example domains (RFC 2606): a kept domain of this list names nobody
MAIL_DOMAINS = {"example", "gmail", "googlemail", "hotmail", "outlook", "live", "msn", "yahoo", "ymail", "icloud",
                "aol", "orange", "wanadoo", "free", "sfr", "neuf", "laposte", "bbox", "gmx", "protonmail", "proton"}

# Keep classes. "Must stay clear" = headline (b); the others are reported apart (policy differences).
MUST_STAY_CLEAR = ("court", "court_city", "article", "code", "law", "legal_ref", "legal_term")

# Lines that extract_text.py writes for document properties, comment authors, link targets and PDF annotations
# ("creator: ...", "link: mailto:..."). Only for .docx, .pdf and .xlsx inputs. Their gold and keep items are part
# "metadata" (reported apart, not in the headlines); their words are left out of the over-masking counts, because
# a tool's own output may simply not carry document properties.
READER_LINE_RE = re.compile(r"^(?:title|subject|creator|keywords|description|lastModifiedBy|category|company|manager|"
                            r"author|link|annotation): ", re.M)

FAIL_RETENTION = 0.50
FAIL_MIN_TOKENS = 20
COVER_T = 0.80
ANYWHERE_MIN_ALNUM = 4
MOVE_MIN_TOKENS = 6
MOVE_MIN_ALNUM = 4
GLUE_SLACK = 12
GLUE_MIN_FREE = 8
EXCLUDED = ("not_run", "unscorable")


# ---------------------------------------------------------------------------------------------- text helpers
def tokenize(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(text)]


def has_alnum(s: str) -> bool:
    return any(c.isalnum() for c in s)


def fold_char(c: str) -> str:
    d = unicodedata.normalize("NFKD", c)
    base = "".join(x for x in d if not unicodedata.combining(x)) or c
    return base.lower()


def fold(s: str) -> str:
    return "".join(fold_char(c) for c in s)


def tok_key(t: str) -> str:
    return fold(unicodedata.normalize("NFKC", t))


def glued(s: str) -> str:
    """Folded letters and digits only."""
    return "".join(c for c in fold(unicodedata.normalize("NFKC", s)) if c.isalnum())


def folded_words(s: str) -> str:
    """lower case, no accents, every run of non-letters-non-digits = one space, padded with spaces."""
    f = fold(unicodedata.normalize("NFKC", s))
    return " " + " ".join(re.findall(r"[^\W_]+", f)) + " "


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------- alignment
def _lis(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Longest subsequence of (i, j) pairs (sorted by i) with increasing j."""
    tails: list[int] = []
    tails_idx: list[int] = []
    prev = [-1] * len(pairs)
    for k, (_i, j) in enumerate(pairs):
        pos = bisect.bisect_left(tails, j)
        if pos == len(tails):
            tails.append(j)
            tails_idx.append(k)
        else:
            tails[pos] = j
            tails_idx[pos] = k
        prev[k] = tails_idx[pos - 1] if pos > 0 else -1
    out = []
    k = tails_idx[-1] if tails_idx else -1
    while k >= 0:
        out.append(pairs[k])
        k = prev[k]
    return out[::-1]


def diff_tokens(a: list[str], b: list[str]) -> list[tuple[int, int]]:
    """Matched (i, j) pairs between token lists a and b, in order (patience diff + SequenceMatcher in gaps)."""
    pairs: list[tuple[int, int]] = []
    stack = [(0, len(a), 0, len(b))]
    while stack:
        a0, a1, b0, b1 = stack.pop()
        while a0 < a1 and b0 < b1 and a[a0] == b[b0]:
            pairs.append((a0, b0))
            a0 += 1
            b0 += 1
        while a0 < a1 and b0 < b1 and a[a1 - 1] == b[b1 - 1]:
            pairs.append((a1 - 1, b1 - 1))
            a1 -= 1
            b1 -= 1
        if a0 >= a1 or b0 >= b1:
            continue
        ca = Counter(a[a0:a1])
        cb = Counter(b[b0:b1])
        pos_b = {b[j]: j for j in range(b0, b1) if cb[b[j]] == 1}
        anchors = [(i, pos_b[a[i]]) for i in range(a0, a1) if ca[a[i]] == 1 and a[i] in pos_b]
        lis = _lis(anchors) if anchors else []
        if lis:
            pi, pj = a0, b0
            for i, j in lis:
                stack.append((pi, i, pj, j))
                pairs.append((i, j))
                pi, pj = i + 1, j + 1
            stack.append((pi, a1, pj, b1))
            continue
        big = (a1 - a0) * (b1 - b0) > 25_000_000
        sm = SequenceMatcher(None, a[a0:a1], b[b0:b1], autojunk=big)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                pairs.append((a0 + blk.a + k, b0 + blk.b + k))
    pairs.sort()
    return pairs


def _line_groups(text: str, toks, keys, skip=None):
    out = []  # (key tuple, [token indexes])
    starts = [t[0] for t in toks]
    pos = 0
    for line in text.split("\n"):
        s, e = pos, pos + len(line)
        lo, hi = bisect.bisect_left(starts, s), bisect.bisect_left(starts, e)
        idx = [k for k in range(lo, hi) if not (skip and skip[k])]
        if idx:
            out.append((tuple(keys[k] for k in idx), idx))
        pos = e + 1
    return out


def _lexi_lcs(ka_seg: list[str], kb_seg: list[str], weight: list[int]) -> list[tuple[int, int]]:
    """Matched (i, j) pairs that maximise the total weight of the matched input tokens (dynamic programming)."""
    n, m = len(ka_seg), len(kb_seg)
    prev = [0] * (m + 1)
    back = []
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        row = bytearray(m + 1)
        ki, wi = ka_seg[i - 1], weight[i - 1]
        for j in range(1, m + 1):
            best, d = prev[j], 1          # skip input token
            if cur[j - 1] > best:
                best, d = cur[j - 1], 2   # skip output token
            if ki == kb_seg[j - 1] and prev[j - 1] + wi > best:
                best, d = prev[j - 1] + wi, 3
            cur[j] = best
            row[j] = d
        back.append(row)
        prev = cur
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        d = back[i - 1][j]
        if d == 3:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif d == 1:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def _repair_block(ai: list[int], bj: list[int], ka, kb, held, match, used) -> int:
    """Lexicographic repair inside one block of differing lines: between two kept skeleton words, when a gold word
    was matched while a skeleton word with an identical unmatched partner was left out (a fake value equal to
    another real value pulled the alignment), redo that stretch maximising first the skeleton matches, then the
    gold matches. Returns the number of stretches redone."""
    anchors = [x for x in ai if match[x] != -1 and not held[x] and has_alnum(ka[x])]
    cuts = [None] + anchors + [None]
    pos = {x: k for k, x in enumerate(ai)}
    redone = 0
    for left, right in zip(cuts, cuts[1:]):
        i0 = pos[left] + 1 if left is not None else 0
        i1 = pos[right] if right is not None else len(ai)
        seg_in = ai[i0:i1]
        if not seg_in:
            continue
        j0 = match[left] + 1 if left is not None else bj[0]
        j1 = match[right] if right is not None else bj[-1] + 1
        seg_out = [y for y in range(j0, j1) if not used[y] or any(match[x] == y for x in seg_in)]
        if not seg_out:
            continue
        if not any(match[x] != -1 and held[x] for x in seg_in):
            continue
        held_out = {match[x] for x in seg_in if held[x] and match[x] != -1}
        free_out = {kb[y] for y in seg_out if not used[y] or y in held_out}
        if not any(match[x] == -1 and not held[x] and has_alnum(ka[x]) and ka[x] in free_out for x in seg_in):
            continue
        if len(seg_in) * len(seg_out) > 2_000_000:
            continue
        for x in seg_in:
            if match[x] != -1:
                used[match[x]] = False
                match[x] = -1
        g = sum(1 for x in seg_in if held[x])
        weight = [1 if held[x] else g + 1 for x in seg_in]
        for i, j in _lexi_lcs([ka[x] for x in seg_in], [kb[y] for y in seg_out], weight):
            match[seg_in[i]] = seg_out[j]
            used[seg_out[j]] = True
        redone += 1
    return redone


def _fill_gaps(idx: list[int], ka, kb, match, used, lo: int, hi: int) -> None:
    """Align each run of unmatched input tokens (indexes ``idx``, in order) with the unused output tokens between
    the output places of its two matched neighbours (bounded by lo..hi), or, when they cross, the next ones."""
    n = len(idx)
    i = 0
    while i < n:
        if match[idx[i]] != -1:
            i += 1
            continue
        p = i
        while i < n and match[idx[i]] == -1:
            i += 1
        q = i - 1
        jl = match[idx[p - 1]] if p > 0 else lo - 1
        jr = match[idx[q + 1]] if q + 1 < n else hi
        if jl < jr:
            window = [j for j in range(jl + 1, jr) if not used[j]]
        else:
            window = [j for j in range(jl + 1, min(hi, jl + 1 + (q - p + 1) + 20)) if not used[j]]
        if not window:
            continue
        for x, y in diff_tokens([ka[idx[k]] for k in range(p, q + 1)], [kb[j] for j in window]):
            match[idx[p + x]] = window[y]
            used[window[y]] = True


def align(in_text: str, out_text: str, gold_chars: list[bool] | None = None, hold_keys: set | None = None):
    """(input tokens, output tokens, match, output text used) with match[i] = index of the aligned output token
    of the same key, or -1. ``gold_chars`` marks the input characters inside gold items and ``hold_keys`` the keys
    of the gold items' identifying tokens (both are "held" words for the repair of pass a)."""
    out_text = unicodedata.normalize("NFC", out_text)
    a = tokenize(in_text)
    b = tokenize(out_text)
    ka = [tok_key(t[2]) for t in a]
    kb = [tok_key(t[2]) for t in b]
    held = [(bool(gold_chars) and any(gold_chars[c] for c in range(t[0], t[1])))
            or (bool(hold_keys) and ka[k] in hold_keys) for k, t in enumerate(a)]
    match = [-1] * len(a)
    used = [False] * len(b)

    # pass a: lines, then tokens inside each block of differing lines; then the lexicographic repair
    la = _line_groups(in_text, a, ka)
    lb = _line_groups(out_text, b, kb)
    sm = SequenceMatcher(None, [k for k, _ in la], [k for k, _ in lb], autojunk=False)
    blocks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for di in range(i2 - i1):
                for x, y in zip(la[i1 + di][1], lb[j1 + di][1]):
                    match[x] = y
                    used[y] = True
            continue
        ai = [x for k in range(i1, i2) for x in la[k][1]]
        bj = [y for k in range(j1, j2) for y in lb[k][1]]
        if not ai or not bj:
            continue
        for i, j in diff_tokens([ka[x] for x in ai], [kb[y] for y in bj]):
            match[ai[i]] = bj[j]
            used[bj[j]] = True
        blocks.append((ai, bj))
    if any(held):
        for ai, bj in blocks:
            _repair_block(ai, bj, ka, kb, held, match, used)

    # pass b: moved blocks (long identical runs among the leftovers of the whole document, gold included)
    for _round in range(5):
        ra = [i for i in range(len(a)) if match[i] == -1]
        rb = [j for j in range(len(b)) if not used[j]]
        if not ra or not rb:
            break
        sm2 = SequenceMatcher(None, [ka[i] for i in ra], [kb[j] for j in rb], autojunk=len(ra) * len(rb) > 25_000_000)
        found = False
        for blk in sm2.get_matching_blocks():
            if blk.size >= MOVE_MIN_TOKENS and sum(has_alnum(ka[ra[blk.a + k]]) for k in range(blk.size)) >= MOVE_MIN_ALNUM:
                for k in range(blk.size):
                    match[ra[blk.a + k]] = rb[blk.b + k]
                    used[rb[blk.b + k]] = True
                found = True
        if not found:
            break

    # pass c: remaining gaps of the whole document, between their neighbours' places
    _fill_gaps(list(range(len(a))), ka, kb, match, used, 0, len(b))
    return a, b, match, out_text


# ---------------------------------------------------------------------------------------------- scoring
def label_family(label: str) -> str:
    u = label.upper()
    if u in PERSON_LABELS:
        return "person"
    if u in ORG_LABELS:
        return "org"
    if u in ADDRESS_LABELS:
        return "address"
    if u in NET_LABELS:
        return "net"
    if u in PHONE_LABELS:
        return "phone"
    if u in IBAN_LABELS:
        return "iban"
    if u in NIR_LABELS:
        return "nir"
    return "other"


DOTTED = re.compile(r"\b(?:[A-Za-z]\.){2,}[A-Za-z]?")
IBAN_HEAD = re.compile(r"^[A-Za-z]{2}\d{2}$")


def identifying_tokens(item: dict, toks, text: str) -> list[int]:
    s, e = item["start"], item["end"]
    starts = [t[0] for t in toks]
    lo = max(0, bisect.bisect_right(starts, s) - 1)
    if item.get("ident"):
        idx = []
        for rs, re_ in item["ident"]:
            for k in range(lo, len(toks)):
                ts, te, tt = toks[k]
                if ts >= re_:
                    break
                if te > rs and ts < re_ and has_alnum(tt) and k not in idx:
                    idx.append(k)
        return sorted(idx)
    alnum = []
    for k in range(lo, len(toks)):
        ts, te, tt = toks[k]
        if ts >= e:
            break
        if te > s and has_alnum(tt):
            alnum.append(k)
    fam = label_family(item["label"])
    drop = {w.lower() for w in item.get("non_identifying", ())}
    if fam == "person":
        drop |= TITLE_WORDS
    elif fam == "org":
        drop |= FUNCTION_WORDS | LEGAL_FORMS
    elif fam == "address":
        drop |= FUNCTION_WORDS | STREET_WORDS
    elif fam == "net":
        drop |= NET_WORDS | MAIL_DOMAINS
    fmt = set()
    if len(alnum) >= 2:
        first = toks[alnum[0]][2]
        if fam == "phone":
            rest = alnum
            if text[s:e].lstrip().startswith(("+", "00")):
                fmt.add(alnum[0])
                rest = alnum[1:]
            if len(rest) >= 4 and re.fullmatch(r"0\d", toks[rest[0]][2]):
                fmt.add(rest[0])
        elif fam == "iban" and IBAN_HEAD.match(first):
            fmt.add(alnum[0])
        elif fam == "nir" and first in ("1", "2"):
            fmt.add(alnum[0])
    if not drop and not fmt:
        return alnum
    dotted_tok = set()
    if fam == "org":
        for m in DOTTED.finditer(text, s, e):
            if m.group().replace(".", "").lower() in LEGAL_FORMS:
                dotted_tok.update(k for k in alnum if toks[k][0] >= m.start() and toks[k][1] <= m.end())
    kept = [k for k in alnum if toks[k][2].lower() not in drop and k not in dotted_tok and k not in fmt]
    if kept:
        return kept
    kept = [k for k in alnum if toks[k][2].lower() not in FUNCTION_WORDS]
    return kept or alnum


def changed_regions(a, changed: list[bool], text: str) -> list[tuple[int, int, int, int]]:
    """(char start, char end, first token, last token + 1) of each run of consecutive changed input tokens on one
    line (a line break ends a region, so two masks on two lines are two regions)."""
    out = []
    k = 0
    n = len(a)
    while k < n:
        if changed[k]:
            j = k
            while j + 1 < n and changed[j + 1] and "\n" not in text[a[j][1]:a[j + 1][0]]:
                j += 1
            out.append((a[k][0], a[j][1], k, j + 1))
            k = j + 1
        else:
            k += 1
    return out


def anywhere_keys(item_text_ident: str) -> tuple[str | None, str | None]:
    words = folded_words(item_text_ident).strip()
    alnum = re.sub(r"\s", "", words)
    if len(alnum) < ANYWHERE_MIN_ALNUM:
        return None, None
    digits = re.sub(r"\D", "", alnum)
    dkey = digits if len(digits) >= 8 and len(digits) >= 0.6 * len(alnum) else None
    return " " + words + " ", dkey


def _rejoined(item_glued: str, a, b, match, out_text: str, k0: int, k1: int) -> bool:
    """True when ``item_glued`` appears in one piece in the output between the kept neighbours of input tokens
    k0..k1-1, in a stretch at most GLUE_SLACK letters or digits longer. A string shorter than GLUE_MIN_FREE must
    also start and end on output token boundaries (so a short name never matches inside a code like ALIAS_1)."""
    if not item_glued:
        return False
    left = next((match[k] for k in range(k0 - 1, -1, -1) if match[k] != -1), -1)
    right = next((match[k] for k in range(k1, len(a)) if match[k] != -1), len(b))
    if left >= right:
        return False
    pieces = [glued(t[2]) for t in b[left + 1:right]]
    w = "".join(pieces)
    if len(w) > len(item_glued) + GLUE_SLACK or item_glued not in w:
        return False
    if len(item_glued) >= GLUE_MIN_FREE:
        return True
    starts, ends, pos = set(), set(), 0
    for piece in pieces:
        if piece:
            starts.add(pos)
            pos += len(piece)
            ends.add(pos)
    at = w.find(item_glued)
    while at >= 0:
        if at in starts and at + len(item_glued) in ends:
            return True
        at = w.find(item_glued, at + 1)
    return False


def score_doc(rec: dict, in_text: str, out_text: str | None, status: str = "ok", reason: str = "",
              hidden: list | None = None) -> dict:
    gold = rec.get("gold", [])
    keep = rec.get("keep", [])
    for g in gold + keep:
        got = in_text[g["start"]:g["end"]]
        if got != g["text"]:
            raise ValueError(f"{rec['doc_id']}: gold offsets do not match the input text: {g['text']!r} vs {got!r}")
    res = {"doc_id": rec["doc_id"], "set": rec.get("set"), "status": status, "reason": reason,
           "chars": len(in_text), "items": [], "keep": [], "regions": 0, "false_mask_regions": 0,
           "regions_on_gold_50": 0, "words_changed_outside_gold": 0, "words_outside_gold": 0, "retention": None,
           "rejoined": 0}
    if status in EXCLUDED:
        return res
    a = tokenize(in_text)
    side = [""] * len(in_text)  # "" body, "metadata", "hidden"
    if Path(rec.get("file", "")).suffix.lower() in (".docx", ".pdf", ".xlsx"):
        for m in READER_LINE_RE.finditer(in_text):
            e = in_text.find("\n", m.start())
            for c in range(m.start(), e if e >= 0 else len(in_text)):
                side[c] = "metadata"
    for hs, he in hidden or ():
        for c in range(max(0, hs), min(len(in_text), he)):
            side[c] = side[c] or "hidden"

    def part_of(g: dict) -> str:
        """"metadata" or "hidden" (reported apart) or "body" (headline). The REF generator's own region
        (header, table, footer...) is kept in the field "region"."""
        if g.get("part") in ("metadata", "hidden"):
            return g["part"]
        for c in range(g["start"], g["end"]):
            if side[c]:
                return side[c]
        return "body"

    gold_cov = [False] * len(in_text)
    for g in gold:
        for c in range(g["start"], g["end"]):
            gold_cov[c] = True
    aside = [bool(side[t[0]]) for t in a]
    is_gold_tok = [any(gold_cov[c] for c in range(t[0], t[1])) for t in a]
    outside = [k for k, t in enumerate(a) if has_alnum(t[2]) and not is_gold_tok[k] and not aside[k]]
    res["words_outside_gold"] = len(outside)

    failed = status != "ok" or out_text is None
    if not failed:
        hold = {tok_key(a[k][2]) for g in gold for k in identifying_tokens(g, a, in_text)}
        held_chars = [gold_cov[c] or bool(side[c]) for c in range(len(in_text))]
        a, b, match, out_norm = align(in_text, out_text, held_chars, hold)
        changed_out = sum(1 for k in outside if match[k] == -1)
        retention = 1 - changed_out / len(outside) if outside else 1.0
        res["retention"] = round(retention, 4)
        if len(outside) >= FAIL_MIN_TOKENS and retention < FAIL_RETENTION:
            failed, res["status"], res["reason"] = True, "failed", f"retention {retention:.3f} < {FAIL_RETENTION}"
    if failed:
        res["status"] = "failed"
        for g in gold:
            idt = identifying_tokens(g, a, in_text)
            res["items"].append({"id": g["id"], "label": g["label"], "status": "missed" if idt else "no_ident",
                                 "exposed_value": bool(idt), "anywhere": True, "cover": 0.0, "part": part_of(g),
                                 "region": g.get("part"), "text": g["text"]})
        for k in keep:
            res["keep"].append({"id": k["id"], "class": k["class"], "altered": False, "part": part_of(k),
                                "text": k["text"]})
        return res

    kept_tok = [m != -1 for m in match]   # after rejoin, tokens of rejoined items count as kept
    item_rows = []
    for g in gold:
        idt = identifying_tokens(g, a, in_text)
        tk = [k for k, t in enumerate(a) if t[1] > g["start"] and t[0] < g["end"]]
        if not idt:
            st, kept_chars, tot_chars = "no_ident", 0, 0
        else:
            ch = [match[k] == -1 for k in idt]
            st = "protected" if all(ch) else "missed" if not any(ch) else "partial"
            if st != "missed" and tk and _rejoined("".join(glued(a[k][2]) for k in idt), a, b, match, out_norm,
                                                    tk[0], tk[-1] + 1):
                st = "missed"
                res["rejoined"] += 1
                for k in tk:
                    kept_tok[k] = True
            tot_chars = sum(len(glued(a[k][2])) for k in idt)
            kept_chars = tot_chars if st == "missed" else sum(len(glued(a[k][2])) for k in idt if match[k] != -1)
        item_rows.append((g, idt, tk, st, kept_chars, tot_chars))
    for kp in keep:
        toks = [k for k, t in enumerate(a) if t[1] > kp["start"] and t[0] < kp["end"] and has_alnum(t[2])]
        altered = any(match[k] == -1 for k in toks)
        if altered and toks and _rejoined(glued(kp["text"]), a, b, match, out_norm, toks[0], toks[-1] + 1):
            altered = False
            res["rejoined"] += 1
            for k in toks:
                kept_tok[k] = True
        res["keep"].append({"id": kp["id"], "class": kp["class"], "altered": altered, "part": part_of(kp),
                            "text": kp["text"]})

    regions = changed_regions(a, [not x for x in kept_tok], in_text)
    covered = [False] * len(in_text)
    for r in regions:
        for c in range(r[0], r[1]):
            covered[c] = True
    out_words = folded_words(out_norm)
    out_digits = re.sub(r"\D", "", fold(out_norm))
    for g, idt, tk, st, kept_chars, tot_chars in item_rows:
        ident_str = " ".join(a[k][2] for k in idt)
        wkey, dkey = anywhere_keys(ident_str)
        anywhere = None
        if wkey is not None:
            anywhere = wkey in out_words or (dkey is not None and dkey in out_digits)
        span = g["end"] - g["start"]
        cover = sum(1 for c in range(g["start"], g["end"]) if covered[c]) / span if span else 0.0
        res["items"].append({"id": g["id"], "label": g["label"], "status": st,
                             "exposed_value": bool(tot_chars) and kept_chars * 2 > tot_chars,
                             "anywhere": anywhere, "cover": round(cover, 4), "part": part_of(g),
                             "region": g.get("part"), "text": g["text"],
                             "left_clear": [a[k][2] for k in idt if match[k] != -1] if st in ("partial", "missed") else []})
    regions = [r for r in regions if not aside[r[2]]]
    res["regions"] = len(regions)
    fm = 0
    ok50 = 0
    for rs, re_, _k0, _k1 in regions:
        ov = sum(1 for c in range(rs, re_) if gold_cov[c])
        fm += ov == 0
        ok50 += (re_ - rs) > 0 and ov / (re_ - rs) >= 0.5
    res["false_mask_regions"] = fm
    res["regions_on_gold_50"] = ok50
    res["words_changed_outside_gold"] = sum(1 for k in outside if not kept_tok[k])
    return res


# ---------------------------------------------------------------------------------------------- aggregation
def is_exposed(it: dict) -> bool:
    return it["status"] in ("partial", "missed")


def aggregate(docs: list[dict]) -> dict:
    excluded = [d for d in docs if d["status"] in EXCLUDED]
    docs = [d for d in docs if d["status"] not in EXCLUDED]
    lab = defaultdict(Counter)
    side = Counter()
    by_part = defaultdict(Counter)
    for d in docs:
        for it in d["items"]:
            if it["status"] != "no_ident":
                pk = it["part"] if it["part"] != "body" else (it.get("region") or "body")
                by_part[pk]["scored"] += 1
                by_part[pk]["exposed"] += is_exposed(it)
                by_part[pk]["exposed_value"] += it["exposed_value"]
            if it["part"] != "body":
                side["n"] += 1
                if it["status"] != "no_ident":
                    side["scored"] += 1
                    side["exposed"] += is_exposed(it)
                continue
            c = lab[it["label"]]
            c["n"] += 1
            c[it["status"]] += 1
            if it["status"] != "no_ident":
                c["scored"] += 1
                c["exposed"] += is_exposed(it)
                c["exposed_value"] += it["exposed_value"]
                c["cover80"] += it["cover"] >= COVER_T
                if it["anywhere"] is not None:
                    c["anywhere_checked"] += 1
                    c["anywhere"] += bool(it["anywhere"])
    tot = Counter()
    for c in lab.values():
        tot.update(c)
    kp = defaultdict(Counter)
    kp_side = defaultdict(Counter)
    for d in docs:
        for k in d["keep"]:
            target = kp if k.get("part", "body") == "body" else kp_side
            target[k["class"]]["n"] += 1
            target[k["class"]]["altered"] += k["altered"]
    must = Counter()
    must_all = Counter()
    for cls, c in kp.items():
        if cls in MUST_STAY_CLEAR:
            must.update(c)
            must_all.update(c)
    for cls, c in kp_side.items():
        if cls in MUST_STAY_CLEAR:
            must_all.update(c)
    ok_docs = [d for d in docs if d["status"] == "ok"]

    def rate(x, y):
        return round(x / y, 4) if y else None

    def body_must(d):
        return any(k["altered"] for k in d["keep"] if k["class"] in MUST_STAY_CLEAR and k.get("part", "body") == "body")

    return {
        "documents": len(docs),
        "documents_failed": sum(1 for d in docs if d["status"] != "ok"),
        "failed_documents": [{"doc_id": d["doc_id"], "reason": d["reason"]} for d in docs if d["status"] != "ok"],
        "documents_excluded": [{"doc_id": d["doc_id"], "status": d["status"], "reason": d["reason"]} for d in excluded],
        "chars": sum(d["chars"] for d in docs),
        "protection": {
            "gold_items": tot["n"], "no_identifying_token": tot["no_ident"], "scored": tot["scored"],
            "protected": tot["protected"], "partial": tot["partial"], "missed": tot["missed"],
            "exposed": tot["exposed"], "exposed_rate": rate(tot["exposed"], tot["scored"]),
            "exposed_value": tot["exposed_value"], "exposed_value_rate": rate(tot["exposed_value"], tot["scored"]),
            "protected_rate": rate(tot["protected"], tot["scored"]),
            "readable_anywhere": tot["anywhere"], "anywhere_checked": tot["anywhere_checked"],
            "covered_80pct": tot["cover80"], "covered_80pct_rate": rate(tot["cover80"], tot["scored"]),
        },
        "protection_metadata": {"gold_items": side["n"], "scored": side["scored"], "exposed": side["exposed"]},
        "protection_by_part": {k: dict(c) for k, c in sorted(by_part.items())},
        "protection_by_label": {k: {"n": c["n"], "scored": c["scored"], "protected": c["protected"],
                                    "partial": c["partial"], "missed": c["missed"], "exposed": c["exposed"],
                                    "exposed_value": c["exposed_value"], "readable_anywhere": c["anywhere"],
                                    "covered_80pct": c["cover80"]}
                                for k, c in sorted(lab.items())},
        "keep_by_class": {k: {"n": c["n"], "altered": c["altered"]} for k, c in sorted(kp.items())},
        "keep_outside_body": {k: {"n": c["n"], "altered": c["altered"]} for k, c in sorted(kp_side.items())},
        "must_stay_clear": {"classes": list(MUST_STAY_CLEAR), "n": must["n"], "altered": must["altered"],
                            "documents_with_one": sum(1 for d in docs if body_must(d))},
        "must_stay_clear_all_parts": {"n": must_all["n"], "altered": must_all["altered"],
                                      "note": "1.0 reading: document properties and tracked deletions included"},
        "regions": {"changed_regions": sum(d["regions"] for d in ok_docs),
                    "false_mask_regions": sum(d["false_mask_regions"] for d in ok_docs),
                    "regions_on_gold_50pct": sum(d["regions_on_gold_50"] for d in ok_docs)},
        "words": {"outside_gold": sum(d["words_outside_gold"] for d in ok_docs),
                  "changed_outside_gold": sum(d["words_changed_outside_gold"] for d in ok_docs),
                  "retention_min": min((d["retention"] for d in ok_docs if d["retention"] is not None), default=None)},
        "rejoined_items": sum(d.get("rejoined", 0) for d in ok_docs),
    }


def per_doc_rows(docs: list[dict]) -> list[dict]:
    rows = []
    for d in docs:
        c = Counter(it["status"] for it in d["items"] if it["part"] == "body")
        rows.append({"doc_id": d["doc_id"], "status": d["status"], "chars": d["chars"],
                     "gold": sum(1 for it in d["items"] if it["part"] == "body"), "protected": c["protected"],
                     "partial": c["partial"], "missed": c["missed"],
                     "exposed_value": sum(1 for it in d["items"] if it["part"] == "body" and it["exposed_value"]),
                     "must_stay_clear_altered": sum(1 for k in d["keep"] if k["altered"] and k["class"] in MUST_STAY_CLEAR
                                                    and k.get("part", "body") == "body"),
                     "keep_altered": sum(1 for k in d["keep"] if k["altered"] and k.get("part", "body") == "body"),
                     "false_mask_regions": d["false_mask_regions"], "retention": d["retention"]})
    return rows


def markdown(summary: dict, title: str) -> str:
    p = summary["protection"]
    md = [f"# {title}", "",
          f"Scorer {SCORER_VERSION}. Documents {summary['documents']} (failed {summary['documents_failed']}; "
          f"left out as not run or unscorable {len(summary['documents_excluded'])}), characters {summary['chars']:,}.",
          "", "## Protection (gold items still readable at their place = exposed)", "",
          "| Label | Gold | Scored | Protected | Partial | Missed | Exposed | Exposed (value) | Readable anywhere | "
          "Covered 80 % |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k, c in summary["protection_by_label"].items():
        md.append(f"| {k} | {c['n']} | {c['scored']} | {c['protected']} | {c['partial']} | {c['missed']} | "
                  f"{c['exposed']} | {c['exposed_value']} | {c['readable_anywhere']} | {c['covered_80pct']} |")
    md.append(f"| **All** | {p['gold_items']} | {p['scored']} | {p['protected']} | {p['partial']} | {p['missed']} | "
              f"**{p['exposed']}** | **{p['exposed_value']}** | {p['readable_anywhere']} | {p['covered_80pct']} |")
    pm = summary["protection_metadata"]
    md += ["", f"Document properties and tracked deletions (parts metadata and hidden, not in the table above): "
               f"{pm['scored']} gold items, {pm['exposed']} exposed."]
    md += ["", "## Must stay readable (keep items altered, body)", "", "| Class | Items | Altered |", "|---|---:|---:|"]
    for k, c in summary["keep_by_class"].items():
        star = " (must stay clear)" if k in MUST_STAY_CLEAR else ""
        md.append(f"| {k}{star} | {c['n']} | {c['altered']} |")
    m = summary["must_stay_clear"]
    md.append(f"| **Must stay clear, all** | {m['n']} | **{m['altered']}** (in {m['documents_with_one']} documents) |")
    m2 = summary["must_stay_clear_all_parts"]
    md.append(f"| Must stay clear, all parts (1.0 reading, properties and tracked deletions included) | {m2['n']} | "
              f"{m2['altered']} |")
    if summary["keep_outside_body"]:
        md += ["", "Keep items in document properties or tracked deletions (not in the table above): " + "; ".join(
            f"{k} {c['altered']} of {c['n']}" for k, c in summary["keep_outside_body"].items())]
    r, w = summary["regions"], summary["words"]
    md += ["", "## Over-masking without a list", "",
           f"Changed regions {r['changed_regions']:,}; false-mask regions (touch no gold) {r['false_mask_regions']:,}; "
           f"regions with 50 % or more of their characters on gold {r['regions_on_gold_50pct']:,}.",
           f"Words outside gold {w['outside_gold']:,}; changed {w['changed_outside_gold']:,}; lowest retention "
           f"{w['retention_min']}. Items rejoined after a split or glued word: {summary['rejoined_items']}.", ""]
    return "\n".join(md) + "\n"


# ---------------------------------------------------------------------------------------------- I/O
def load_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def find_output(out_dir: Path, rel: str) -> Path | None:
    from extract_text import SUPPORTED  # noqa: PLC0415
    p = Path(rel)
    folder = out_dir / p.parent
    if not folder.exists():
        return None
    hits = [q for q in folder.iterdir() if q.is_file() and q.stem == p.stem and q.suffix.lower() in SUPPORTED]
    if len(hits) != 1:
        return None
    return hits[0]


def cmd_score(args) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_text import check_versions, extract  # noqa: PLC0415

    gold = load_jsonl(args.gold)
    runlog = {r["doc_id"]: r for r in load_jsonl(args.runlog)} if args.runlog else {}
    manifest = {r["doc_id"]: r.get("output") for r in load_jsonl(args.outputs_manifest)} if args.outputs_manifest else {}
    docs = []
    for rec in gold:
        if "text" in rec:
            in_text, in_meta = rec["text"], {}
        else:
            in_text, in_meta = extract(Path(args.inputs) / rec["file"])
        if rec.get("text_sha256") and sha256_text(in_text) != rec["text_sha256"]:
            raise SystemExit(f"{rec['doc_id']}: input text hash differs from the pre-registered gold")
        log = runlog.get(rec["doc_id"]) or runlog.get(rec.get("file", "")) or {}
        status, reason = log.get("status", "ok"), log.get("reason", "")
        out_text = None
        if status == "ok":
            if args.outputs_manifest:
                outp = Path(manifest[rec["doc_id"]]) if manifest.get(rec["doc_id"]) else None
            else:
                outp = find_output(Path(args.outputs), rec["file"])
            if outp is None or not outp.exists():
                status, reason = "failed", "no output file"
            else:
                try:
                    out_text, out_meta = extract(outp)
                    if out_meta.get("image_only"):
                        status, reason, out_text = "unscorable", "output PDF has images and no text layer", None
                except Exception as e:  # noqa: BLE001
                    status, reason = "failed", f"output unreadable: {type(e).__name__}: {e}"
        docs.append(score_doc(rec, in_text, out_text, status, reason, hidden=in_meta.get("hidden_ranges")))
    write_results(args, docs, {"reader_version_check": check_versions()})
    return 0


def cmd_pairs(args) -> int:
    gold = {r["doc_id"]: r for r in load_jsonl(args.gold)}
    docs = []
    for p in load_jsonl(args.pairs):
        rec = gold[p["doc_id"]]
        in_text = p.get("input_text", rec.get("text"))
        docs.append(score_doc(rec, in_text, p.get("output_text"), p.get("status", "ok"), p.get("reason", ""),
                              hidden=p.get("hidden_ranges")))
    missing = set(gold) - {d["doc_id"] for d in docs}
    for m in sorted(missing):
        rec = gold[m]
        docs.append(score_doc(rec, rec["text"], None, "failed", "no output"))
    write_results(args, docs, {})
    return 0


def write_results(args, docs: list[dict], extra: dict) -> None:
    summary = aggregate(docs)
    summary.update(scorer=SCORER_VERSION, tool=args.tool, gold=str(args.gold), **extra)
    out = {"summary": summary, "per_document": per_doc_rows(docs), "documents": docs}
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    md = markdown(summary, f"{args.tool or 'tool'} on {Path(args.gold).name}")
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    print(md)


# ---------------------------------------------------------------------------------------------- self-test
def _probe(src: str, gold: list, keep: list = (), file: str = "") -> dict:
    """Invented test record: gold/keep given as (label or class, value, occurrence index)."""
    def find(val, occ):
        s = -1
        for _ in range(occ + 1):
            s = src.index(val, s + 1)
        return s
    gi = [{"id": f"g{i + 1}", "label": lab, "start": find(v, o), "end": find(v, o) + len(v), "text": v}
          for i, (lab, v, o) in enumerate((x + (0,))[:3] for x in gold)]
    ki = [{"id": f"k{i + 1}", "class": c, "start": find(v, o), "end": find(v, o) + len(v), "text": v}
          for i, (c, v, o) in enumerate((x + (0,))[:3] for x in keep)]
    return {"doc_id": "t", "file": file, "gold": gi, "keep": ki}



# ---------------------------------------------------------------------------------------------- review cases
STYLES = ("codes", "tags", "fakes", "deletion")


def review_cases() -> list[dict]:
    """Invented cases of the fairness review (PROTOCOL_ADDENDUM_1.md section 17.2): every kept change of 1.1, for
    each replacement style. Each case gives the TRUE answer; ``--selftest`` checks this scorer against it, and
    <work>/critic/fairness_cases.py runs the same cases through scorer 1.0 for the review table."""
    cases: list[dict] = []
    B = ("Monsieur Jean Dupont, né le 12 mars 1980, demeurant 12 rue des Lilas, 69003 Lyon, joignable au "
         "06 12 34 56 78 et à jean.dupont@example.com, IBAN FR76 3000 4000 0312 3456 7890 143, NIR 1 80 03 69 123 456 78, "
         "a saisi le conseil de prud'hommes de Lyon sur le fondement de l'article L. 1235-3 du code du travail.\n"
         "Appel devant la cour d'appel de Besançon.\n")
    VAL = ("Jean Dupont", "12 mars 1980", "12 rue des Lilas, 69003 Lyon", "06 12 34 56 78", "jean.dupont@example.com",
           "FR76 3000 4000 0312 3456 7890 143", "1 80 03 69 123 456 78")
    rb = _probe(B, list(zip(("PERSON", "BIRTHDATE", "ADDRESS", "PHONE", "EMAIL", "IBAN", "NIR"), VAL)),
                [("court", "conseil de prud'hommes de Lyon"), ("court_city", "Lyon", 1), ("article", "article L. 1235-3"),
                 ("code", "code du travail"), ("court", "cour d'appel de Besançon")])
    REPL = {
        "codes": ("PERSONNE_A", "NAISSANCE_1", "ADRESSE_1", "TEL_1", "EMAIL_1", "IBAN_1", "NIR_1"),
        "tags": ("[NAME_GIVEN_k2] [NAME_FAMILY_p9]", "[DOB_x3]", "[LOCATION_ADDRESS_x4]", "<PHONE_NUMBER>",
                 "<EMAIL_ADDRESS>", "[IBAN_CODE_a1]", "[REDACTED]"),
        "fakes": ("Paul Martin", "4 juillet 1975", "8 avenue Foch, 13002 Marseille", "07 41 98 23 65",
                  "paul.martin@fournisseur-mail.net", "DE89 3704 0044 0532 0130 00", "2 75 07 13 055 482 11"),
        "deletion": ("", "", "", "", "", "", ""),
    }
    allp = {f"g{i + 1}": "protected" for i in range(7)}
    nokeep = {f"k{i + 1}": False for i in range(5)}

    def styled(style, override=None):
        out = B
        for i, v in enumerate(VAL):
            rep = (override or {}).get(i, REPL[style][i])
            out = out.replace(v, rep)
        return out

    def add(finding, case, style, rec, src, out, gold=None, keep=None, value=None, scored=None, must=None,
            excluded=False, kind="error", **kw):
        cases.append({"finding": finding, "case": case, "style": style, "rec": rec, "src": src, "out": out, "kw": kw,
                      "kind": kind,
                      "expect": {"gold": gold or {}, "keep": keep or {}, "value": value or {}, "scored": scored,
                                 "must": must, "excluded": excluded}})

    tags_local = {"codes": "USER_1", "tags": "<USER>", "fakes": "paul.martin", "deletion": ""}
    phone_fmt = {"codes": "06 TEL_1", "tags": "06 <PHONE>", "fakes": "06 98 76 54 32", "deletion": "06"}
    iban_fmt = {"codes": "FR76 IBAN_1", "tags": "FR76 <IBAN>", "fakes": "FR76 1027 8061 2400 0201 4560 182",
                "deletion": "FR76"}
    nir_fmt = {"codes": "1 NIR_1", "tags": "1 <NIR>", "fakes": "1 75 07 13 055 482 11", "deletion": "1"}
    first_only = {"codes": "Jean PERSONNE_A", "tags": "Jean <PERSON>", "fakes": "Jean Martin", "deletion": "Jean"}
    T3 = "Le contrat lie Jean Dupont et Paul Martin.\nFait à Lyon.\n"
    r3 = _probe(T3, [("PERSON", "Jean Dupont"), ("PERSON", "Paul Martin")], [("court_city", "Lyon")])
    swap = {"codes": ("PERSONNE_A", "PERSONNE_B"), "tags": ("<PERSON>", "<PERSON>"),
            "fakes": ("Paul Martin", "Luc Bernard"), "deletion": ("", "")}
    T4 = ("Me Jean Dupont\nCorps du texte avec Paul Martin et le code civil.\nNote de bas de page : Mme Claire Roux.\n"
          "Pied de page : cabinet Roux, 4 rue Neuve à Lille, dossier suivi devant le CPH Lille.\n")
    r4 = _probe(T4, [("PERSON", "Jean Dupont"), ("PERSON", "Paul Martin"), ("PERSON", "Claire Roux"),
                     ("ADDRESS", "4 rue Neuve à Lille")], [("code", "code civil"), ("court", "CPH Lille")])
    four = {"codes": ("PERSONNE_A", "PERSONNE_B", "PERSONNE_C", "ADRESSE_1"),
            "tags": ("<PERSON>", "<PERSON>", "<PERSON>", "<LOCATION>"),
            "fakes": ("Luc Bernard", "Marc Petit", "Anne Morel", "9 rue Haute à Rouen"), "deletion": ("", "", "", "")}
    T6 = "Le témoin Ali a signé devant le tribunal.\n"
    r6 = _probe(T6, [("PERSON", "Ali")])
    short = {"codes": "ALIAS_1", "tags": "<PERSON>", "fakes": "Eli", "deletion": ""}
    T8 = "Écrire à jean.dupont@valmont-avocats.fr pour le dossier.\n"
    r8 = _probe(T8, [("EMAIL", "jean.dupont@valmont-avocats.fr")])
    T10 = "title: Note CPH Lille pour M. Paul Roux\nLe dossier de M. Paul Roux devant le CPH Lille.\n"
    r10 = _probe(T10, [("PERSON", "Paul Roux"), ("PERSON", "Paul Roux", 1)], [("court", "CPH Lille"), ("court", "CPH Lille", 1)],
                 file="x.docx")
    roux = {"codes": "PERSONNE_A", "tags": "<PERSON>", "fakes": "Luc Bernard", "deletion": ""}

    for st in STYLES:
        add("S0", "baseline: every value replaced", st, rb, B, styled(st), allp, nokeep)
        add("F2", "name only upper-cased (not replaced)", st, rb, B, styled(st, {0: "JEAN DUPONT"}),
            dict(allp, g1="missed"), nokeep)
        add("F2", "court name upper-cased", st, rb, B,
            styled(st).replace("conseil de prud'hommes de Lyon", "CONSEIL DE PRUD'HOMMES DE LYON"), allp, nokeep)
        add("F2", "output in Unicode NFD (decomposed accents)", st, rb, B,
            unicodedata.normalize("NFD", styled(st)), allp, nokeep)
        a, b = swap[st]
        add("F3", "both names replaced (fakes: the first fake equals the second real name)", st, r3, T3,
            T3.replace("Jean Dupont", "\x00").replace("Paul Martin", b).replace("\x00", a),
            {"g1": "protected", "g2": "protected"}, {"k1": False})
        add("F3", "leak control: second name left in clear", st, r3, T3, T3.replace("Jean Dupont", a),
            {"g1": "protected", "g2": "missed"}, {"k1": False})
        moved = T4.split("\n")
        moved = "\n".join([moved[3], moved[0], moved[1], moved[2]]) + "\n"   # reader puts the footer first
        m_all = moved
        for v, rep in zip(("Jean Dupont", "Paul Martin", "Claire Roux", "4 rue Neuve à Lille"), four[st]):
            m_all = m_all.replace(v, rep)
        add("F4", "footer put first by the reader, every value replaced", st, r4, T4, m_all,
            {"g1": "protected", "g2": "protected", "g3": "protected", "g4": "protected"}, {"k1": False, "k2": False})
        m_leak = m_all.replace(four[st][3], "4 rue Neuve à Lille") if four[st][3] else \
            moved.replace("Jean Dupont", "").replace("Paul Martin", "").replace("Claire Roux", "")
        add("F4", "footer put first by the reader, its address left in clear", st, r4, T4, m_leak,
            {"g1": "protected", "g2": "protected", "g3": "protected", "g4": "missed"}, {"k1": False, "k2": False})
        add("F5", "words glued by a re-rendered file (court, code)", st, rb, B,
            styled(st).replace("prud'hommes de Lyon", "prud'hommesde Lyon").replace("code du travail", "code dutravail"),
            allp, nokeep)
        add("F5", "name split by a re-rendered file, not replaced", st, rb, B, styled(st, {0: "Jean Du pont"}),
            dict(allp, g1="missed"), nokeep)
        add("F5", "short name; replacement may contain its letters", st, r6, T6, T6.replace("Ali", short[st]),
            {"g1": "protected"})
        add("F6", "first name kept (codes, tags, deletion: a leak; fakes: a coincidence)", st, rb, B,
            styled(st, {0: first_only[st]}), dict(allp, g1="partial"), nokeep, value={"g1": False}, kind="rule")
        add("F7", "e-mail local part replaced, reserved domain example.com kept", st, rb, B,
            styled(st, {4: tags_local[st] + "@example.com"}), allp, nokeep)
        add("F7", "control: firm domain kept", st, r8, T8,
            T8.replace("jean.dupont", tags_local[st]), {"g1": "partial"})
        add("F8", "phone, IBAN, NIR: shared format group kept, rest replaced", st, rb, B,
            styled(st, {3: phone_fmt[st], 5: iban_fmt[st], 6: nir_fmt[st]}), allp, nokeep)
        add("F8", "control: last groups kept", st, rb, B,
            styled(st, {3: "** ** ** 56 78", 5: "FR** **** **** **** **** **** 143", 6: "* ** ** ** *** 456 78"}),
            dict(allp, g4="partial", g6="partial", g7="partial"), nokeep)
        body = T10.split("\n", 1)[1].replace("Paul Roux", roux[st])
        add("F9", "output without document properties (text output)", st, r10, T10, body,
            {"g2": "protected"}, {"k2": False}, scored=1, must=(1, 0))
        add("F9", "output keeps document properties unchanged", st, r10, T10, T10.split("\n", 1)[0] + "\n" + body,
            {"g2": "protected"}, {"k1": False, "k2": False}, scored=1)
    T11 = "Texte supprimé : M. Paul Roux. Texte gardé : article 700 du code de procédure civile.\n"
    r11 = _probe(T11, [("PERSON", "Paul Roux")], [("article", "article 700"), ("code", "code de procédure civile")])
    hid = [(0, T11.index("Texte gardé"))]
    add("F10", "tracked deletion dropped by the reader (text output)", "any", r11, T11, T11[hid[0][1]:],
        keep={"k1": False, "k2": False}, scored=0, must=(2, 0), hidden=hid)
    add("F10", "tracked deletion kept, not replaced (file rewritten)", "any", r11, T11, T11,
        keep={"k1": False, "k2": False}, scored=0, must=(2, 0), kind="rule", hidden=hid)
    add("F11", "document never sent to the tool (trial or quota ended)", "any", rb, B, None, excluded=True,
        status="not_run", reason="trial ended")
    add("F12", "output PDF with images and no text layer", "any", rb, B, None, excluded=True,
        status="unscorable", reason="output PDF has images and no text layer")
    return cases


def check_case(case: dict, res: dict, agg: dict) -> list[str]:
    """Differences between a scored case and its true answer (empty list = right)."""
    e = case["expect"]
    bad = []
    if e["excluded"]:
        if agg["documents"] != 0:
            bad.append("not left out")
        return bad
    st = {it["id"]: it["status"] for it in res["items"]}
    kp = {k["id"]: k["altered"] for k in res["keep"]}
    for i, want in e["gold"].items():
        if st.get(i) != want:
            bad.append(f"{i} {st.get(i)} (true: {want})")
    for i, want in e["keep"].items():
        if kp.get(i) != want:
            bad.append(f"{i} altered={kp.get(i)} (true: {want})")
    for i, want in e["value"].items():
        got = next((it.get("exposed_value") for it in res["items"] if it["id"] == i), None)
        if got != want:
            bad.append(f"{i} exposed_value={got} (true: {want})")
    if e["scored"] is not None and agg["protection"]["scored"] != e["scored"]:
        bad.append(f"headline gold scored {agg['protection']['scored']} (true: {e['scored']})")
    if e["must"] is not None:
        m = agg["must_stay_clear"]
        if (m["n"], m["altered"]) != tuple(e["must"]):
            bad.append(f"headline must-stay-clear {m['altered']} of {m['n']} (true: {e['must'][1]} of {e['must'][0]})")
    return bad

def selftest() -> int:
    src = ("Entre M. Jean Dupont, né le 12/03/1980, demeurant 12 rue des Lilas, 69003 Lyon, et la société "
           "Valmont SARL, devant le tribunal judiciaire de Lyon, en application de l'article 1240 du code civil.\n"
           "Contact : jean.dupont@exemple.fr. Montant : 12 500 euros.\n")
    rec = _probe(src, [("PERSON", "Jean Dupont"), ("DOB", "12/03/1980"), ("ADDRESS", "12 rue des Lilas, 69003 Lyon"),
                       ("ORG", "Valmont SARL"), ("EMAIL", "jean.dupont@exemple.fr")],
                 [("court", "tribunal judiciaire de Lyon"), ("article", "article 1240"), ("code", "code civil"),
                  ("amount", "12 500 euros")])

    def run(out, r=rec, s=src, **kw):
        res = score_doc(r, s, out, **kw)
        return ({it["id"]: it["status"] for it in res["items"]}, {k["id"]: k["altered"] for k in res["keep"]}, res)

    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL", name, info)

    allp = {"g1": "protected", "g2": "protected", "g3": "protected", "g4": "protected", "g5": "protected"}
    cases = {
        "codes": src.replace("Jean Dupont", "PERSONNE_A").replace("12/03/1980", "DATE_A")
                    .replace("12 rue des Lilas, 69003 Lyon", "ADRESSE_A").replace("Valmont", "SOCIETE_A")
                    .replace("jean.dupont@exemple.fr", "EMAIL_A"),
        "tags": src.replace("Jean Dupont", "[a.PERSON_1]").replace("12/03/1980", "<DATE_TIME>")
                   .replace("12 rue des Lilas, 69003 Lyon", "[REDACTED]").replace("Valmont SARL", "[REDACTED]")
                   .replace("jean.dupont@exemple.fr", "[EMAIL]"),
        "fakes": src.replace("Jean Dupont", "Paul Martin").replace("12/03/1980", "04/07/1975")
                    .replace("12 rue des Lilas, 69003 Lyon", "8 rue des Ormes, 13002 Marseille")
                    .replace("Valmont SARL", "Brévine SAS").replace("jean.dupont@exemple.fr", "p.martin@ex.fr"),
        "deletion": src.replace("Jean Dupont", "").replace("12/03/1980", "").replace("12 rue des Lilas, 69003 Lyon", "")
                       .replace("Valmont SARL", "").replace("jean.dupont@exemple.fr", ""),
    }
    for name, out in cases.items():
        st, kp, _r = run(out)
        check(name, st == allp and not any(kp.values()), (st, kp))
    # partial and missed, plus over-masking of a court city and of an article number
    st, kp, r = run(src.replace("Jean Dupont", "Jean PERSONNE_A").replace("de Lyon, en", "de VILLE_A, en")
                    .replace("article 1240", "article NUMERO_A"))
    check("partial/keep", st["g1"] == "partial" and st["g3"] == "missed" and kp["k1"] and kp["k2"] and not kp["k3"]
          and not kp["k4"], (st, kp))
    # fake value equal to another real value of the same document: protected at its place, readable anywhere
    st, _kp, r = run(src.replace("Jean Dupont", "Valmont").replace("Valmont SARL", "Corvel SARL"))
    g4 = next(it for it in r["items"] if it["id"] == "g4")
    check("anywhere", g4["status"] == "protected" and g4["anywhere"], g4)
    # unchanged output: everything missed, nothing altered, retention 1.0
    st, kp, r = run(src)
    check("identity", set(st.values()) == {"missed"} and not any(kp.values()) and r["retention"] == 1.0, (st, kp))
    # line breaks and spaces changed only: still nothing changed
    st, kp, r = run(src.replace(", ", ",\n").replace(" ", "  "))
    check("whitespace", set(st.values()) == {"missed"}, st)
    # failure rule: output that drops most of the document
    st, kp, r = run("PERSONNE_A\n")
    check("retention rule", r["status"] == "failed" and set(st.values()) == {"missed"}, (r["status"], st))

    # ---- 1.1 cases (fairness review), all invented
    s1 = ("Monsieur Jean Dupont, né le 12 mars 1980, demeurant 12 rue des Lilas, 69003 Lyon, joignable au "
          "06 12 34 56 78 et à jean.dupont@gmail.com, IBAN FR76 3000 4000 0312 3456 7890 143, NIR 1 80 03 69 123 456 78, "
          "a saisi le conseil de prud'hommes de Lyon sur le fondement de l'article L. 1235-3 du code du travail.\n")
    r1 = _probe(s1, [("PERSON", "Jean Dupont"), ("BIRTHDATE", "12 mars 1980"), ("ADDRESS", "12 rue des Lilas, 69003 Lyon"),
                     ("PHONE", "06 12 34 56 78"), ("EMAIL", "jean.dupont@gmail.com"),
                     ("IBAN", "FR76 3000 4000 0312 3456 7890 143"), ("NIR", "1 80 03 69 123 456 78")],
                [("court", "conseil de prud'hommes de Lyon"), ("court_city", "Lyon", 1), ("article", "article L. 1235-3"),
                 ("code", "code du travail")])
    fmt = (s1.replace("Jean Dupont", "Paul Martin").replace("12 mars 1980", "4 juillet 1975")
           .replace("12 rue des Lilas, 69003 Lyon", "8 avenue Foch, 13002 Marseille").replace("06 12 34 56 78", "06 98 76 54 32")
           .replace("jean.dupont@gmail.com", "paul.martin@gmail.com")
           .replace("FR76 3000 4000 0312 3456 7890 143", "FR76 1027 8061 2400 0201 4560 182")
           .replace("1 80 03 69 123 456 78", "1 75 07 13 055 482 11"))
    st, kp, r = run(fmt, r1, s1)
    check("format tokens shared by every value", set(st.values()) == {"protected"} and not any(kp.values()), (st, kp))
    coinc = (s1.replace("Jean Dupont", "Jean Martin").replace("12 mars 1980", "12 juin 1975")
             .replace("12 rue des Lilas, 69003 Lyon", "12 rue Pasteur, 13002 Marseille").replace("06 12 34 56 78", "07 41 34 90 11")
             .replace("1 80 03 69 123 456 78", "2 80 07 13 055 482 11"))
    st, kp, r = run(coinc, r1, s1)
    ev = {it["text"]: it["exposed_value"] for it in r["items"]}
    check("coincidence: strict exposed, value not", st["g1"] == "partial" and st["g2"] == "partial"
          and not any(ev[t] for t in ("Jean Dupont", "12 mars 1980", "12 rue des Lilas, 69003 Lyon", "06 12 34 56 78",
                                      "1 80 03 69 123 456 78")), (st, ev))
    st, kp, r = run(s1.replace("Jean Dupont", "JEAN DUPONT").replace("Lyon", "LYON"), r1, s1)
    check("case change is not protection", st["g1"] == "missed" and not any(kp.values()), (st, kp))
    s2 = "Mme Hélène Brûlé est venue devant la cour d'appel de Besançon.\n"
    r2 = _probe(s2, [("PERSON", "Hélène Brûlé")], [("court", "cour d'appel de Besançon")])
    st, kp, r = run("Mme Helene Brule est venue devant la cour d'appel de Besançon.\n", r2, s2)
    check("accents stripped is not protection", st["g1"] == "missed", st)
    st, kp, r = run(unicodedata.normalize("NFD", s2), r2, s2)
    check("NFD output, nothing masked", st["g1"] == "missed" and not kp["k1"], (st, kp))
    st, kp, r = run(s1.replace("prud'hommes de Lyon", "prud'hommesde Lyon").replace("code du travail", "code dutravail"), r1, s1)
    check("glued words (re-rendered PDF)", not any(kp.values()) and r["rejoined"] >= 2, (kp, r["rejoined"]))
    st, kp, r = run(s1.replace("Dupont", "Du pont").replace("travail", "tra vail"), r1, s1)
    check("split words (re-rendered PDF)", st["g1"] == "missed" and not any(kp.values()), (st, kp))
    s3 = "Le contrat lie Jean Dupont et Paul Martin.\nFait à Lyon.\n"
    r3 = _probe(s3, [("PERSON", "Jean Dupont"), ("PERSON", "Paul Martin")], [("court_city", "Lyon")])
    st, kp, r = run("Le contrat lie Paul Martin et Luc Bernard.\nFait à Lyon.\n", r3, s3)
    check("fake equal to another real name does not shift the alignment", st == {"g1": "protected", "g2": "protected"}, st)
    s4 = ("HEADER Me Jean Dupont\nCorps du texte avec Paul Martin et le code civil.\n"
          "Note de bas de page : Mme Claire Roux.\nPied de page : cabinet Roux, 4 rue Neuve à Lille.\n")
    r4 = _probe(s4, [("PERSON", "Jean Dupont"), ("PERSON", "Paul Martin"), ("PERSON", "Claire Roux"),
                     ("ADDRESS", "4 rue Neuve à Lille")], [("code", "code civil")])
    moved = ("HEADER Me Jean Dupont\nCorps du texte avec Paul Martin et le code civil.\n"
             "Pied de page : cabinet Roux, 4 rue Neuve à Lille.\nNote de bas de page : Mme Claire Roux.\n")
    st, kp, r = run(moved, r4, s4)
    check("moved block, nothing masked", set(st.values()) == {"missed"}, st)
    st, kp, r = run(moved.replace("Claire Roux", "PERSONNE_C").replace("4 rue Neuve à Lille", "ADRESSE_A"), r4, s4)
    check("moved block, masked", st["g3"] == "protected" and st["g4"] == "protected", st)
    st, kp, r = run(s4[:s4.index("Pied de page")], r4, s4)
    check("footer deleted: a word equal to a gold word elsewhere does not take its place",
          st == {"g1": "missed", "g2": "missed", "g3": "missed", "g4": "protected"}, st)
    s5 = "Le salarié, M. Karim Lanmas, conteste la mesure prise contre lui par la direction du site de Genay.\n"
    r5 = _probe(s5, [("PERSON", "Karim Lanmas")])
    st, kp, r = run(s5.replace("Karim Lanmas", "K. L."), r5, s5)
    check("initials", st["g1"] == "protected", st)
    st, kp, r = run(s5.replace("Karim Lanmas", "Karim LANMAS_1"), r5, s5)
    check("name kept inside a code is exposed", st["g1"] in ("partial", "missed") and r["items"][0]["anywhere"],
          r["items"][0])
    s9 = "Le témoin Ali a signé.\n"
    st, kp, r = run("Le témoin ALIAS_1 a signé.\n", _probe(s9, [("PERSON", "Ali")]), s9)
    check("short name never matches inside a code", st["g1"] == "protected", st)
    s6 = "Contact : honore80@example.com ou la société Valmont SAS.\n"
    r6 = _probe(s6, [("EMAIL", "honore80@example.com"), ("ORG", "Valmont SAS")])
    st, kp, r = run(s6.replace("honore80", "user_a").replace("Valmont", "SOCIETE_A"), r6, s6)
    check("reserved mail domain kept", st == {"g1": "protected", "g2": "protected"}, st)
    s7 = "title: Note pour M. Paul Roux\nsubject: CPH Lille\nLe dossier de M. Paul Roux devant le CPH Lille.\n"
    r7 = _probe(s7, [("PERSON", "Paul Roux"), ("PERSON", "Paul Roux", 1)], [("court", "CPH Lille"), ("court", "CPH Lille", 1)],
                file="x.docx")
    st, kp, r = run("Le dossier de M. PERSONNE_A devant le CPH Lille.\n", r7, s7)
    agg = aggregate([r])
    check("document properties apart (gold and keep)", agg["protection"]["scored"] == 1
          and agg["must_stay_clear"]["n"] == 1 and agg["must_stay_clear"]["altered"] == 0, agg["must_stay_clear"])
    s8 = "Texte supprimé : M. Paul Roux. Texte gardé : article 700 du code de procédure civile.\n"
    r8 = _probe(s8, [("PERSON", "Paul Roux")], [("article", "article 700")])
    st, kp, r = run(s8, r8, s8, hidden=[(0, s8.index("Texte gardé"))])
    check("tracked deletion apart", r["items"][0]["part"] == "hidden" and aggregate([r])["protection"]["scored"] == 0, r["items"])
    st, kp, r = run(None, r8, s8, status="not_run", reason="trial ended")
    check("not_run left out", aggregate([r])["documents"] == 0 and len(aggregate([r])["documents_excluded"]) == 1, r)
    # ---- review cases (PROTOCOL_ADDENDUM_1.md section 17.2): every kept change, every replacement style
    for case in review_cases():
        kw = dict(case["kw"])
        res = score_doc(case["rec"], case["src"], case["out"], **kw)
        bad = check_case(case, res, aggregate([res]))
        check(f"review {case['finding']} [{case['style']}] {case['case']}", not bad, bad)
    print("selftest", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--gold", required=True)
    s.add_argument("--inputs", default=".")
    s.add_argument("--outputs", default=".")
    s.add_argument("--outputs-manifest")
    s.add_argument("--runlog")
    s.add_argument("--json")
    s.add_argument("--md")
    s.add_argument("--tool", default="")
    s.set_defaults(func=cmd_score)
    p = sub.add_parser("pairs")
    p.add_argument("--gold", required=True)
    p.add_argument("--pairs", required=True)
    p.add_argument("--json")
    p.add_argument("--md")
    p.add_argument("--tool", default="")
    p.set_defaults(func=cmd_pairs)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
