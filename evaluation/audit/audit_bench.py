#!/usr/bin/env python3
"""Clean-room audit: no gold value of a benchmark we hold may sit in the code, the tests, the lexicons or the docs.

    python evaluation/audit/audit_bench.py --tree           the whole repository (see "Scope" below)
    python evaluation/audit/audit_bench.py --diff <base>    only the lines added since <base> (git diff of the
                                                            working tree) plus the untracked files of the scope

Options: ``--allow FILE`` (default ``evaluation/audit/allow.txt``), ``--out FILE`` (JSON report, masked values
only), ``--bench NAME`` (repeatable: limit the gold sources), ``--quotes`` (add the Judilibre review list),
``--paths P ...`` (scan these paths instead of the repository scope), ``--max N`` (print at most N finding lines),
``--accept-allow`` (with ``--diff``: accept the allow entries added since <base>, see "Allow file").

Scope (v0.4 S0): every file git tracks or would track (untracked files not ignored by ``.gitignore``) in the
repository, whatever its suffix: the code, the tests, the docs, the integrations, the root files (SECURITY.md,
pyproject.toml, LICENSE...), ``bench/``, ``.claude-plugin/`` and the files directly in ``evaluation/`` (the
scoreboard). Left out: the subfolders of ``evaluation/`` (the benchmark runners and their result files quote
benchmark values by design, and the Max corpus is the home of its own values), ``.bench_data/`` and other ignored
files. A file is read as text (UTF-8; an undecodable byte is replaced, never a reason to skip the file); Word,
Excel, PowerPoint and OpenDocument files by the text of their XML parts; a PDF with ``pdftotext`` when it is on
the PATH. A file with a NUL byte that is none of these (an image) is not read: the report counts those files.

Gold sources, read in place and never copied (a missing source is reported and skipped):

- PrivacyBench: ``.bench_data/public/privacybench/data/ground_truth/*/ground_truth.jsonl`` (span texts),
  ``*/characters.json`` (names, nicknames, e-mails, phones, handles, organisations, ids, addresses, urls) and
  ``human_annotations/*.jsonl`` (span texts);
- FR-PII-Bench: ``.bench_data/public/fr-pii-bench/fr_pii_bench_v0.jsonl`` (entity texts, every label);
- MAPA: ``.bench_data/public/mapa-fr-cassation/data/tsv/*.tsv`` (PERSON, ORGANISATION, ADDRESS, FINANCIAL and
  their name, street, city, postcode and building parts; DATE, AMOUNT, ROLE, PROFESSION, TIME, titles, countries
  and territories are generic and left out);
- REDACT: ``.bench_data/public/redact/raw/pii_benchmark_sample1000.json`` (every language; the identifying
  entity types only: names, e-mails, phones, ids, card, passport, tax and licence numbers, addresses, cities,
  organisations, handles, IP addresses, dates of birth, passwords; attributes such as gender, title, nationality,
  salary or medical text are not values of a person and are left out);
- Max corpus: ``evaluation/max-protocol/corpus/*/gold.json`` (every protect item: canonical, surface forms,
  variations);
- the full person names of FR-PII-Bench, the Max corpus and the gap snippets also give each of their words of 4+
  letters alone (a surname written without its first name), titles and Max's non-identifying tokens left out;
- gap snippets (dev set of 2026-10-17): ``.bench_data/public/redact-fr-and-gaps/snippets.json`` (target and
  context texts: names, initials, nicknames, acronyms; the clue texts are generic and left out);
- Judilibre, only with ``--quotes``: ``.bench_data/public/judilibre/sample.jsonl`` has no gold, only decision text.
  A run of 5 words that occurs in exactly one of the 200 decisions is listed for review. It never fails the run:
  French legal formulas ("la faute grave est celle qui ...", court and agency names) are public and shared by many
  decisions outside the sample, so a hit is a pointer for a reader, not a proof of a quote.

Matching, after folding (NFKC, case-folded, accents removed, curly quotes made straight):

- names, organisations, addresses and other word values: the value's word sequence at word boundaries (a word is a
  run of letters and digits), values of 4 or more letters and digits; a value made of digits only is an
  identifier; a lone number of fewer than 6 digits (a house number, a postcode) is not distinctive and is skipped;
  an address also gives its first comma part ("<number> <street>"), a company name also gives its core without a
  trailing legal form;
- identifiers (e-mails, phones, ids, accounts, IBAN, handles, urls, dates of birth): the letter-and-digit core
  (separators removed), matched against the identifier-like runs of a line (letters and digits joined by
  ``- . _ @ + / : #`` or digit groups joined by a space, a dot, a dash or brackets) on whole parts of the run,
  so "+1 (555) 010-7788", "555.010.7788" and "15550107788" are the same value; cores of fewer than 4 characters,
  and digit-only cores of fewer than 6 digits, are skipped. A masked value (``****-1234``) is matched on its
  visible part when that part follows a mask run in the line (``****1234``, ``xxxx-1234``), never as a bare
  number. A phone also gives its national form (US "1" or French "33" prefix), an e-mail its local part when that
  part holds a separator or a digit, and a multi-part id each part of 6 or more characters that mixes letters and
  digits.

The allow file holds common words and common first names that are also gold values, one per line:
``value | reason``. Every entry needs a reason; an entry clears a word value equal to it (the whole value, so
allowing a first name never clears a full name that holds it). An identifier is cleared only by an explicit
``id:<value> | reason`` entry (placeholders such as sequential digits or a published example IBAN).
A line of the scanned tree is never printed: a finding prints ``path:line``, the benchmark, the label, a masked
form of the value (first character and length) and a 12-hex id (a hash prefix, to group the findings of one value),
so this script never writes a gold value to the screen or to a file (``--out`` holds the same masked fields).
Exit 0 when nothing is found, 1 on any finding, 2 on a setup error (an allow entry without a reason, no gold source
at all). Standard library only; nothing in ``src/`` reads this file.

Written forms (v0.4 S0): each line is also read decoded, and a value found in any of these forms is a finding:
camelCase split into words ("janeDoe"); string literals joined across ``+`` or side by side (``"Do" + "e"``); Python
and JavaScript escapes (``\\u0061``, ``\\x61``, ``\\N{...}``); HTML entities (``&#97;``); URL percent escapes;
Cyrillic and Greek letters that look like Latin ones (a Cyrillic "О" in a Latin word); base64 and hex text of 12
or more characters that decodes to readable UTF-8; the MD5, SHA-1 and SHA-256 digests of every gold value (as
written, lower case and folded). Digit identifiers are also matched across ANY separator of 1 to 6
non-alphanumeric characters, quotes, commas and brackets included (``("208", "555", "0163")`` reads as one phone
number), when every joined part holds a digit; a lone comma or dot right before the next group is a decimal or
thousands mark and ends the run ("613,57").

Short values (v0.4 S0): a person-name value of exactly three letters ("Qyx") is matched when a line writes it as a
whole word in Title case (the allow file clears the common ones), and a digit-only employee, account, customer or
national number counts from 5 digits.

Allow file and laundering (v0.4 S0): with ``--diff``, an allow entry that is not in the allow file of <base> and
that clears a value in the scanned lines is a finding ("allow entry added since <base>"): a value and the entry
that hides it cannot enter in the same change. A reviewer who accepts the new entry runs ``--accept-allow``.

Example of a masked line, with invented data: ``tests/test_x.py:12  PrivacyBench/NAME_FAMILY  Q~9``.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import glob
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PUB = ROOT / ".bench_data" / "public"
#: v0.4 S0: the default scope is the repository (module doc, "Scope"); ``--paths`` scans other paths instead.
REPO_SCOPE = "repository (evaluation/*/ and ignored files left out)"
ZIP_DOC_SUFFIXES = {".docx", ".docm", ".dotx", ".xlsx", ".xlsm", ".pptx", ".odt", ".ods", ".odp"}
QUOTE_WORDS, QUOTE_MAX_DOCS = 5, 1

_APOS = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "′": "'", " ": " ", " ": " "})
_WORD = re.compile(r"[^\W_]+")
# identifier-like runs: letters/digits joined by tight separators, or digit groups joined by a space, dot, dash or
# brackets (phone and IBAN layouts)
_TIGHT = re.compile(r"[^\W_]+(?:[-._@+/:#][^\W_]+)*")
_DIGIT_TOKEN = r"[^\W_]*\d[^\W_]*"
_SPACED = re.compile(r"\+?\(?" + _DIGIT_TOKEN + r"(?:(?:\)\s?|\s?\(|[ .\-/])" + _DIGIT_TOKEN + r")+")
_HEXHASH = re.compile(r"^[0-9a-f]{24,}$")
_MASKED = re.compile(r"[*•]|x{3,}", re.I)
_MASK_RUN = re.compile(r"(?:[*•]{2,}|(?<![^\W_])x{3,})[ \-./]?(\d+(?:[ \-.]\d+)*)")
_TITLES = {"monsieur", "madame", "mademoiselle", "maitre", "docteur", "professeur", "mister", "miss", "doctor",
           "judge", "prof", "sieur", "dame", "epoux", "epouse", "veuve", "consorts"}
_LEGAL_TAIL = {"inc", "incorporated", "llc", "ltd", "limited", "llp", "lp", "corp", "corporation", "co", "plc",
               "gmbh", "ag", "sa", "sas", "sasu", "sarl", "eurl", "snc", "sci", "scp", "selarl", "nv", "bv", "spa",
               "srl"}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_APOS).casefold()
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def words(s: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(fold(s)))


def mask(raw: str) -> str:
    """First letter or digit of the value, then its length: never the value itself."""
    first = next((c for c in raw if c.isalnum()), "?")
    return f"{first}~{len(raw.strip())}"


# ---------------------------------------------------------------------------------------------------- gold values
@dataclass
class Gold:
    """One gold value: ``key`` is a word tuple (word values) or a letter-and-digit core (identifiers)."""
    kind: str  # "words" or "ident"
    key: object
    masked: str
    where: set = field(default_factory=set)  # {(bench, label)}


class GoldSet:
    def __init__(self) -> None:
        self.by_key: dict[tuple[str, object], Gold] = {}
        self.loaded: Counter = Counter()
        self.notes: list[str] = []
        #: v0.4 S0: every raw gold value as given, for the digests (md5, sha1, sha256) of its written forms
        self.raw_values: dict[str, set] = defaultdict(set)

    def _put(self, kind: str, key, raw: str, bench: str, label: str) -> None:
        g = self.by_key.get((kind, key))
        if g is None:
            g = self.by_key[(kind, key)] = Gold(kind, key, mask(raw))
        g.where.add((bench, label))

    def add_words(self, raw: str, bench: str, label: str) -> None:
        w = words(raw)
        if not w:
            return
        if all(x.isdigit() for x in w):
            self.add_ident(raw, bench, label)
            return
        if sum(len(x) for x in w) < 4:
            if len(w) == 1 and len(w[0]) == 3 and w[0].isalpha() and label in _NAME_LABELS:
                self._put("short", w[0], raw, bench, label)  # v0.4 S0: matched only written "Qyx" (Title case)
                self.loaded[bench] += 1
            return
        self._put("words", w, raw, bench, label)
        self.loaded[bench] += 1

    def add_name_parts(self, raw: str, bench: str, label: str, skip: frozenset = frozenset()) -> None:
        """Each word of 4+ letters of a person's full name, alone ("Lomarec" of "Yann Lomarec"): a benchmark that
        gives full names only would otherwise never catch its surnames. Titles and ``skip`` words are left out."""
        w = words(raw)
        if len(w) < 2:
            return
        for x in w:
            if len(x) >= 4 and not x.isdigit() and x not in _TITLES and x not in skip:
                self._put("words", (x,), x, bench, f"{label} (part)")

    def add_ident(self, raw: str, bench: str, label: str, phone: bool = False) -> None:
        if not raw:
            return
        if _MASKED.search(raw):  # "****-1234": keep the visible part, matched only after a mask run
            vis = "".join(words(_MASKED.sub(" ", raw)))
            if len(vis) >= 4 and any(c.isdigit() for c in vis):
                self._put("masked", vis, raw, bench, label)
                self.loaded[bench] += 1
            return
        w = words(raw)
        core = "".join(w)
        min_digits = 5 if label in _SHORT_ID_LABELS else 6  # v0.4 S0: a 5-digit employee or account number
        if len(core) < 4 or (core.isdigit() and len(core) < min_digits):
            return
        self._put("ident", core, raw, bench, label)
        self.loaded[bench] += 1
        if phone or (core.isdigit() and 10 <= len(core) <= 13):
            for v in _national_forms(core):
                self._put("ident", v, raw, bench, label)
        if len(w) > 1:  # a multi-part id: each distinctive part alone
            for x in w:
                if len(x) >= 6 and any(c.isdigit() for c in x) and (any(c.isalpha() for c in x) or len(x) >= 7):
                    self._put("ident", x, raw, bench, label)

    def add_email(self, raw: str, bench: str, label: str) -> None:
        if not raw or "@" not in raw:
            self.add_words(raw, bench, label)
            return
        self.add_ident(raw, bench, label)
        local = raw.split("@", 1)[0]
        lw = words(local)
        lc = "".join(lw)
        if len(lc) >= 6 and (len(lw) > 1 or any(c.isdigit() for c in lc)):
            self._put("ident", lc, raw, bench, label)
            if len(lw) > 1 and all(x.isalpha() for x in lw):
                self.add_words(" ".join(lw), bench, label)  # "first.last" also as the words "first last"

    def add_address(self, raw: str, bench: str, label: str) -> None:
        self.add_words(raw, bench, label)
        parts = [p for p in raw.split(",") if p.strip()]
        if len(parts) > 1:
            head = parts[0] if len(words(parts[0])) >= 2 else ",".join(parts[:2])
            if len(words(head)) >= 2:
                self.add_words(head, bench, label)

    def add_org(self, raw: str, bench: str, label: str) -> None:
        self.add_words(raw, bench, label)
        w = list(words(raw))
        while len(w) > 1 and w[-1] in _LEGAL_TAIL:
            w.pop()
        if w and w[0] == "the" and len(w) > 1:
            w = w[1:]
        if tuple(w) != words(raw):
            self.add_words(" ".join(w), bench, label)

    def add_any(self, raw: str, bench: str, label: str, how: str) -> None:
        if not isinstance(raw, str) or not raw.strip():
            return
        if len(raw.strip()) >= 4:
            self.raw_values[raw.strip()].add((bench, label))
        {"words": self.add_words, "ident": self.add_ident, "email": self.add_email, "address": self.add_address,
         "org": self.add_org, "phone": lambda r, b, l: self.add_ident(r, b, l, phone=True)}[how](raw, bench, label)


#: Labels of person names: a three-letter value of these labels is a "short" value (v0.4 S0).
_NAME_LABELS = frozenset({
    "NAME_GIVEN", "NAME_FAMILY", "characters.first_names", "characters.last_names", "characters.nicknames",
    "characters.canonical_name", "PERSON", "family name", "given name", "given name - male", "given name - female",
    "initial name", "Full_Name", "Last_Family_Name", "First_Given_Name", "Preferred_Name"})
#: Labels of identifiers whose digit-only value counts from 5 digits (v0.4 S0): an employee, account or customer
#: number, not a postcode or a house number.
_SHORT_ID_LABELS = frozenset({
    "EMPLOYEE_ID", "ACCOUNT_NUMBER", "characters.employee_ids", "characters.account_numbers", "Employee_ID_Number",
    "Customer_Reference_Number", "Building_Badge_Card_Number", "Account_Statements", "Tax_Reference_Number",
    "National_Identification_Number", "Passport_Number", "Driving_License_Number", "FINANCIAL"})


def _national_forms(core: str) -> list[str]:
    out = []
    if len(core) == 11 and core.startswith("1"):
        out.append(core[1:])
    if len(core) == 11 and core.startswith("33"):
        out.append("0" + core[2:])
    if len(core) == 10 and core.startswith("0"):
        out.append("33" + core[1:])
    return out


def digests(gs: GoldSet) -> dict[str, Gold]:
    """``hex digest -> Gold`` for the MD5, SHA-1 and SHA-256 of every raw gold value, as written, lower case and
    folded (v0.4 S0): a value hashed into a test or a fixture is still that value."""
    out: dict[str, Gold] = {}
    for raw, where in gs.raw_values.items():
        for form in {raw, raw.lower(), fold(raw)}:
            b = form.encode("utf-8")
            for algo in (hashlib.md5, hashlib.sha1, hashlib.sha256):
                h = algo(b).hexdigest()
                g = out.get(h)
                if g is None:
                    g = out[h] = Gold("hash", h, mask(raw))
                g.where.update(where)
    return out


# PrivacyBench labels (ground truth and human annotations)
_PB_HOW = {"NAME_GIVEN": "words", "NAME_FAMILY": "words", "ORGANIZATION": "org", "LOCATION_ADDRESS": "address",
           "EMAIL_ADDRESS": "email", "PHONE_NUMBER": "phone", "EMPLOYEE_ID": "ident", "ACCOUNT_NUMBER": "ident",
           "URL": "ident", "USERNAME": "ident"}
_PB_CHAR_HOW = {"canonical_name": "words", "first_names": "words", "last_names": "words", "nicknames": "words",
                "emails": "email", "phone_numbers": "phone", "phone_numbers_linked": "phone",
                "slack_handles": "ident", "alt_slack_handles": "ident", "linkedin_handles": "ident",
                "organizations": "org", "employee_ids": "ident", "addresses": "address", "urls": "ident",
                "account_numbers": "ident"}


def _how_ident_or_words(raw: str, how: str) -> str:
    """A handle or id without any digit (``@jdoe``) is a word value, not an identifier."""
    if how == "ident" and not any(c.isdigit() for c in raw) and "@" not in raw.strip("<@>") and "." not in raw:
        return "words"
    return how


def load_privacybench(gs: GoldSet) -> None:
    base = PUB / "privacybench" / "data"
    files = sorted(glob.glob(str(base / "ground_truth" / "*" / "ground_truth.jsonl")))
    hum = sorted(glob.glob(str(base / "human_annotations" / "*.jsonl")))
    chars = sorted(glob.glob(str(base / "ground_truth" / "*" / "characters.json")))
    if not (files or hum or chars):
        gs.notes.append(f"PrivacyBench: not found under {base.relative_to(ROOT)}")
        return
    for bench, flist in (("PrivacyBench", files), ("PrivacyBench-human", hum)):
        seen: set[tuple[str, str]] = set()
        for f in flist:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    for sp in json.loads(line).get("ground_truth_spans") or []:
                        seen.add((sp.get("label", ""), sp.get("text", "")))
        for label, text in seen:
            gs.add_any(text, bench, label, _how_ident_or_words(text, _PB_HOW.get(label, "words")))
    for f in chars:
        for c in json.loads(Path(f).read_text(encoding="utf-8")).values():
            for k, v in c.items():
                how = _PB_CHAR_HOW.get(k)
                if how is None:
                    continue
                for x in v if isinstance(v, list) else [v]:
                    raw = x.get("value") if isinstance(x, dict) else x
                    if isinstance(raw, str):
                        gs.add_any(raw, "PrivacyBench", f"characters.{k}", _how_ident_or_words(raw, how))


_FR_HOW = {"PERSON": "words", "COMPANY": "org", "ADDRESS": "address", "EMAIL": "email", "PHONE": "phone"}


def load_frpii(gs: GoldSet) -> None:
    f = PUB / "fr-pii-bench" / "fr_pii_bench_v0.jsonl"
    if not f.exists():
        gs.notes.append(f"FR-PII-Bench: {f.relative_to(ROOT)} not found")
        return
    for line in f.open(encoding="utf-8"):
        for e in json.loads(line).get("entities") or []:
            lab = e.get("label", "")
            gs.add_any(e.get("text", ""), "FR-PII-Bench", lab, _FR_HOW.get(lab, "ident"))
            if lab == "PERSON":
                gs.add_name_parts(e.get("text", ""), "FR-PII-Bench", lab)


_MAPA_KEEP = {"PERSON": "words", "ORGANISATION": "org", "ADDRESS": "address", "FINANCIAL": "ident",
              "family name": "words", "given name": "words", "given name - male": "words",
              "given name - female": "words", "initial name": "words", "street": "address", "city": "words",
              "postcode": "words", "building": "words", "place": "words", "other:address": "words",
              "unresolved:address": "words", "unresolved:vehicle": "words"}


def load_mapa(gs: GoldSet) -> None:
    files = sorted(glob.glob(str(PUB / "mapa-fr-cassation" / "data" / "tsv" / "*.tsv")))
    if not files:
        gs.notes.append("MAPA: .bench_data/public/mapa-fr-cassation/data/tsv/ not found")
        return
    for f in files:
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split("\t")
            if len(p) < 5 or p[4] in ("_", ""):
                continue
            for v in p[4].split("|"):
                m = re.match(r"^(.*?)(?:\[(\d+)\])?$", v)
                groups[(m.group(1), m.group(2) or f"u{p[0]}")].append(p[2])
        for (lab, _key), toks in groups.items():
            how = _MAPA_KEEP.get(lab)
            if how:
                gs.add_any(" ".join(toks), "MAPA", lab, how)


_REDACT_HOW = {
    "Full_Name": "words", "Last_Family_Name": "words", "First_Given_Name": "words", "Preferred_Name": "words",
    "Org_Name": "org", "Work_Email_Address": "email", "Personal_Email_Address": "email",
    "Telephone_Numbers_Personal": "phone", "Telephone_Numbers_Work": "phone", "Customer_Reference_Number": "ident",
    "National_Identification_Number": "ident", "Employee_ID_Number": "ident", "Credit_Card_Numbers": "ident",
    "Passport_Number": "ident", "Static_IP_Address": "ident", "Building_Badge_Card_Number": "ident",
    "Driving_License_Number": "ident", "Tax_Reference_Number": "ident", "Account_Statements": "ident",
    "Password": "ident", "Date_of_Birth": "ident", "Geolocation_Data": "ident", "Social_Media_Identifiers": "ident",
    "Address_Personal": "address", "Address_Work": "address", "Emergency_Contact_Details": "words",
    "City": "words", "Location": "words", "Place_of_Birth": "words"}


def load_redact(gs: GoldSet) -> None:
    f = PUB / "redact" / "raw" / "pii_benchmark_sample1000.json"
    if not f.exists():
        gs.notes.append(f"REDACT: {f.relative_to(ROOT)} not found")
        return
    for r in json.loads(f.read_text(encoding="utf-8")):
        for e in r.get("entities") or []:
            how = _REDACT_HOW.get(e.get("entity_type", ""))
            if how:
                raw = e.get("entity_string", "")
                gs.add_any(raw, "REDACT", e["entity_type"], _how_ident_or_words(raw, how))


_MAX_HOW = {"PERSON": "words", "ORG": "org", "ADDRESS": "address", "PLACE": "words", "EMAIL": "email",
            "PHONE": "phone", "URL": "ident"}


def load_max(gs: GoldSet) -> None:
    files = sorted(glob.glob(str(ROOT / "evaluation" / "max-protocol" / "corpus" / "*" / "gold.json")))
    if not files:
        gs.notes.append("Max: evaluation/max-protocol/corpus/*/gold.json not found")
        return
    for f in files:
        for it in json.loads(Path(f).read_text(encoding="utf-8")).get("protect") or []:
            how = _MAX_HOW.get(it.get("kind", ""), "ident")
            skip = frozenset(fold(t) for t in it.get("non_identifying_tokens") or [])
            for raw in [it.get("canonical")] + list(it.get("surface_forms") or []) + list(it.get("variations") or []):
                if isinstance(raw, str):
                    gs.add_any(raw.replace("\\n", " "), "Max", it.get("kind", ""), _how_ident_or_words(raw, how))
                    if it.get("kind") == "PERSON":
                        gs.add_name_parts(raw.replace("\\n", " "), "Max", "PERSON", skip)


def load_gaps(gs: GoldSet) -> None:
    f = PUB / "redact-fr-and-gaps" / "snippets.json"
    if not f.exists():
        gs.notes.append(f"gap snippets: {f.relative_to(ROOT)} not found")
        return
    for s in json.loads(f.read_text(encoding="utf-8")):
        for g in s.get("gold") or []:
            if g.get("role") in ("target", "context"):
                raw = g.get("text", "")
                how = "ident" if any(c.isdigit() for c in raw) else "words"
                gs.add_any(raw, "gap-snippets", s.get("cls", ""), how)
                if how == "words":
                    gs.add_name_parts(raw, "gap-snippets", s.get("cls", ""))


def load_quotes() -> tuple[dict[tuple[str, ...], int], list[str]]:
    """5-word runs of the Judilibre sample that occur in one decision only (review list, see the module doc)."""
    f = PUB / "judilibre" / "sample.jsonl"
    if not f.exists():
        return {}, [f"Judilibre: {f.relative_to(ROOT)} not found"]
    docs_of: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for i, line in enumerate(f.open(encoding="utf-8")):
        w = words(json.loads(line).get("text") or "")
        for k in range(len(w) - QUOTE_WORDS + 1):
            docs_of[w[k:k + QUOTE_WORDS]].add(i)
    return {s: len(d) for s, d in docs_of.items() if len(d) <= QUOTE_MAX_DOCS}, []


LOADERS = {"PrivacyBench": load_privacybench, "FR-PII-Bench": load_frpii, "MAPA": load_mapa, "REDACT": load_redact,
           "Max": load_max, "gap-snippets": load_gaps}


# ---------------------------------------------------------------------------------------------------- allow file
def parse_allow(text: str, name: str) -> tuple[dict[object, str], list[str]]:
    """``{word tuple or ("id", core): reason}`` from the text of an allow file."""
    allow: dict[object, str] = {}
    errors: list[str] = []
    for no, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        value, sep, reason = s.partition("|")
        is_id = value.strip().lower().startswith("id:")
        if is_id:
            value = value.strip()[3:]
        if not sep or not reason.strip() or not words(value):
            errors.append(f"{name}:{no}: an allow entry needs 'value | reason'")
            continue
        allow[("id", "".join(words(value))) if is_id else words(value)] = reason.strip()
    return allow, errors


def load_allow(path: Path) -> tuple[dict[object, str], list[str]]:
    if not path.exists():
        return {}, []
    return parse_allow(path.read_text(encoding="utf-8"), path.name)


def allow_added_since(base: str, path: Path, allow: dict) -> tuple[set, str]:
    """The allow keys that are not in the allow file of ``base`` (v0.4 S0, laundering), and a note."""
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        return set(), f"allow file {path} is outside the repository: the entries added since {base} are not checked"
    res = subprocess.run(["git", "-C", str(ROOT), "show", f"{base}:{rel.as_posix()}"], capture_output=True,
                         text=True, check=False)
    old, _errors = parse_allow(res.stdout if res.returncode == 0 else "", rel.name)
    return set(allow) - set(old), ""


# ---------------------------------------------------------------------------------------------------- scan input
def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout
    return [x for x in out.split("\n") if x]


def in_repo_scope(rel: str) -> bool:
    """The default scope (module doc, "Scope"): no subfolder of evaluation/, no .bench_data/, no cache file."""
    parts = rel.split("/")
    if parts[0] in (".bench_data", ".git", ".venv"):
        return False
    if parts[0] == "evaluation" and len(parts) > 2:
        return False
    return "__pycache__" not in parts and not rel.endswith(".pyc")


def repo_files() -> list[str]:
    """The tracked files and the untracked files .gitignore does not ignore, in the default scope; outside a git
    work tree, every file under the root (fail closed: more files, never fewer)."""
    try:
        files = set(_git("ls-files", "--cached", "--others", "--exclude-standard"))
    except (OSError, subprocess.CalledProcessError):
        files = {str(f.relative_to(ROOT)) for f in ROOT.rglob("*") if f.is_file()}
    return sorted(f for f in files if in_repo_scope(f) and (ROOT / f).is_file())


def _expand(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        hits = sorted(ROOT.glob(p)) if any(ch in p for ch in "*?[") else [ROOT / p]
        for h in hits:
            if h.is_dir():
                out.extend(f for f in sorted(h.rglob("*")) if f.is_file())
            elif h.is_file():
                out.append(h)
    return [f for f in out if "__pycache__" not in f.parts and f.suffix.lower() != ".pyc"]


_XML_BREAK = re.compile(r"</(?:w:p|a:p|text:p|text:h|si|row|c)>|<(?:w:br|w:cr)\s*/>")
_XML_SPACE = re.compile(r"<(?:w:tab|text:s|text:tab|text:line-break)\b[^>]*/>")
_XML_TAG = re.compile(r"<[^>]+>")


def _rel(f: Path) -> str:
    try:
        return str(f.relative_to(ROOT))
    except ValueError:
        return str(f)


def _read(f: Path, unread: list[str]) -> list[str] | None:
    """The text lines of ``f`` (module doc, "Scope"), or None for a file that is not read (listed in ``unread``)."""
    suf = f.suffix.lower()
    try:
        if suf in ZIP_DOC_SUFFIXES:
            lines: list[str] = []
            with zipfile.ZipFile(f) as z:
                for name in z.namelist():
                    if name.endswith(".xml"):
                        txt = z.read(name).decode("utf-8", "replace")
                        txt = _XML_SPACE.sub(" ", _XML_BREAK.sub("\n", txt))
                        lines.extend(html.unescape(_XML_TAG.sub("", txt)).splitlines())
            return lines
        if suf == ".pdf":
            exe = shutil.which("pdftotext")
            if exe is None:
                unread.append(f"{_rel(f)} (pdf, pdftotext not found)")
                return None
            res = subprocess.run([exe, "-q", "-layout", str(f), "-"], capture_output=True, check=False)
            return res.stdout.decode("utf-8", "replace").splitlines()
        data = f.read_bytes()
    except (OSError, zipfile.BadZipFile, KeyError):
        unread.append(f"{_rel(f)} (unreadable)")
        return None
    if b"\0" in data:
        unread.append(f"{_rel(f)} (binary)")
        return None
    return data.decode("utf-8", "replace").splitlines()


def tree_lines(paths: list[str] | None, unread: list[str]) -> dict[str, list[tuple[int, str]]]:
    files = [ROOT / f for f in repo_files()] if paths is None else _expand(paths)
    out: dict[str, list[tuple[int, str]]] = {}
    for f in files:
        lines = _read(f, unread)
        if lines is not None:
            out[_rel(f)] = list(enumerate(lines, 1))
    return out


def diff_lines(base: str, paths: list[str] | None, unread: list[str]) -> dict[str, list[tuple[int, str]]]:
    specs = ["."] if paths is None else list(paths)
    keep = in_repo_scope if paths is None else (lambda rel: True)
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--no-color", "--unified=0", base, "--", *specs],
                          capture_output=True, text=True, check=True).stdout
    out: dict[str, list[tuple[int, str]]] = defaultdict(list)
    cur, no = None, 0
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
            if cur is not None and not keep(cur):
                cur = None
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", ln)
        if m:
            no = int(m.group(1))
            continue
        if ln.startswith("+") and cur:
            out[cur].append((no, ln[1:]))
            no += 1
    for ln in _git("diff", "--numstat", base, "--", *specs):  # a binary file (docx, pdf) changed: read it whole
        a, b, rel = (ln.split("\t", 2) + ["", ""])[:3]
        if a == "-" and b == "-" and keep(rel) and (ROOT / rel).is_file():
            lines = _read(ROOT / rel, unread)
            if lines is not None:
                out[rel] = list(enumerate(lines, 1))
    for rel in _git("ls-files", "--others", "--exclude-standard", "--", *specs):
        f = ROOT / rel
        if not keep(rel) or "__pycache__" in f.parts or f.suffix.lower() == ".pyc" or not f.is_file():
            continue
        lines = _read(f, unread)
        if lines is not None:
            out[rel] = list(enumerate(lines, 1))
    return out


# ---------------------------------------------------------------------------------------------------- written forms
# Cyrillic and Greek letters that read as Latin ones (v0.4 S0)
_CONFUSABLES = {
    "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t",
    "у": "y", "х": "x", "і": "i", "ї": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ԛ": "q", "ԝ": "w", "ӏ": "l", "һ": "h",
    "А": "A", "В": "B", "Е": "E", "Ё": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "У": "Y", "Х": "X", "І": "I", "Ї": "I", "Ј": "J", "Ѕ": "S", "Ԛ": "Q", "Ԝ": "W", "Һ": "H",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Υ": "Y", "Χ": "X", "ο": "o", "ν": "v", "ρ": "p", "ι": "i", "κ": "k", "υ": "u", "α": "a",
    "ı": "i", "ɡ": "g", "ɑ": "a",
}
_CONF_TABLE = str.maketrans(_CONFUSABLES)
_CONF_RX = re.compile("[" + "".join(_CONFUSABLES) + "]")
_ESCAPE = re.compile(r"\\(?:u\{([0-9a-fA-F]{1,6})\}|u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8})|x([0-9a-fA-F]{2})"
                     r"|N\{([^}]{1,80})\})")
_CONCAT = re.compile(r"""(["'])\s*\+?\s*\1""")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z][a-z])|(?<=[A-Z])(?=[A-Z][a-z])")
_B64 = re.compile(r"[A-Za-z0-9+/_-]{12,}={0,2}")
_HEXTEXT = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}){6,}(?![0-9A-Fa-f])")


def _unescape(m: re.Match) -> str:
    g = m.groups()
    try:
        if g[4] is not None:
            return unicodedata.lookup(g[4])
        return chr(int(next(x for x in g[:4] if x is not None), 16))
    except (KeyError, ValueError, OverflowError):
        return m.group()


def _readable(b: bytes) -> str | None:
    """``b`` as text when it is UTF-8 and readable (9 printable characters in 10, a letter or digit)."""
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not t or sum(ch.isprintable() for ch in t) < 0.9 * len(t) or not any(ch.isalnum() for ch in t):
        return None
    return t


def decoded_tokens(text: str) -> list[str]:
    """The readable texts hidden in base64 or hex tokens of 12+ characters of ``text``."""
    out = []
    for m in _B64.finditer(text):
        tok = m.group().rstrip("=")
        if len(tok) % 4 == 1:
            continue
        pad = tok + "=" * (-len(tok) % 4)
        for alt in (pad, pad.replace("-", "+").replace("_", "/")):
            try:
                t = _readable(base64.b64decode(alt, validate=True))
            except (binascii.Error, ValueError):
                continue
            if t:
                out.append(t)
                break
    for m in _HEXTEXT.finditer(text):
        try:
            t = _readable(bytes.fromhex(m.group()))
        except ValueError:
            t = None
        if t:
            out.append(t)
    return out


_DECODERS = (
    ("&", html.unescape),
    ("%", urllib.parse.unquote),
    ("\\", lambda t: _ESCAPE.sub(_unescape, t)),
    (None, lambda t: _CONCAT.sub("", t)),
    (None, lambda t: t.translate(_CONF_TABLE) if _CONF_RX.search(t) else t),
    (None, lambda t: _CAMEL.sub(" ", t)),
)


def variants(text: str) -> list[str]:
    """``text`` and its decoded forms (module doc, "Written forms"): each decoder alone, all of them in a row, and
    the texts of its base64 and hex tokens."""
    out = [text]
    cur = text
    for trigger, fn in _DECODERS:
        if trigger is not None and trigger not in text:
            continue
        v = fn(text)
        if v not in out:
            out.append(v)
        cur = fn(cur)
    if cur not in out:
        out.append(cur)
    for t in decoded_tokens(text):
        if t not in out:
            out.append(t)
    return out


# ---------------------------------------------------------------------------------------------------- matching
_WORD3 = re.compile(r"(?<![^\W_])[^\W\d_]{3}(?![^\W_])")
_HEXRUN = re.compile(r"(?<![0-9a-f])(?:[0-9a-f]{64}|[0-9a-f]{40}|[0-9a-f]{32})(?![0-9a-f])")
_LOOSE_PART = re.compile(r"[^\W_]*\d[^\W_]*")
_LOOSE = re.compile(_LOOSE_PART.pattern + r"(?:(?![,.](?:[^\W_]))[\W_]{1,6}" + _LOOSE_PART.pattern + ")+")


def ident_runs(folded: str) -> list[list[str]]:
    """The identifier-like runs of a folded line, each as its list of letter/digit parts."""
    runs = []
    for rx in (_TIGHT, _SPACED):
        for m in rx.finditer(folded):
            parts = _WORD.findall(m.group())
            core = "".join(parts)
            if len(parts) < 2 and not any(c.isdigit() for c in core):
                continue  # a plain word is not an identifier
            if _HEXHASH.match(core):
                continue  # a hash or a digest, not an identifier
            runs.append(parts)
    return runs


def loose_windows(folded: str, max_len: int):
    """Cores of 2+ digit groups joined across ANY separator of 1 to 6 non-alphanumeric characters (quotes, commas
    and spaces, brackets, slashes) (v0.4 S0): ``("208", "555", "0163")`` gives "2085550163". Every part holds a
    digit; a lone comma or dot between two groups is a decimal or thousands mark and ends the run ("567,89")."""
    for m in _LOOSE.finditer(folded):
        parts = _WORD.findall(m.group())
        for a in range(len(parts) - 1):
            acc = parts[a]
            for b in range(a + 1, len(parts)):
                acc += parts[b]
                if len(acc) > max_len:
                    break
                yield acc


def section_of(lines: list[tuple[int, str]], no: int) -> str:
    """The ``[section]`` a lexicon line sits in (lexicon .txt files mark sections as ``# [name]``)."""
    sec = ""
    for n, text in lines:
        if n > no:
            break
        m = re.match(r"^#?\s*\[([a-z_ -]+)\]\s*$", text.strip())
        if m:
            sec = m.group(1)
    return sec


class _Index:
    """The gold values arranged for the line matcher."""

    def __init__(self, gs: GoldSet, quotes: dict):
        self.first_word: dict[str, list[Gold]] = defaultdict(list)
        self.idents: dict[str, Gold] = {}
        self.maskeds: dict[str, Gold] = {}
        self.shorts: dict[str, Gold] = {}
        self.max_ident = 0
        for (kind, key), g in gs.by_key.items():
            if kind == "words":
                self.first_word[key[0]].append(g)
            elif kind == "masked":
                self.maskeds[key] = g
            elif kind == "short":
                self.shorts[key] = g
            else:
                self.idents[key] = g
                self.max_ident = max(self.max_ident, len(key))
        self.hashes = digests(gs)
        self.quotes = quotes
        self.q_first = {s[0] for s in quotes}


def line_hits(text: str, ix: _Index, allow: dict, new_allow: set, allowed: Counter, hits: dict) -> None:
    """Add to ``hits`` the gold values written in ``text`` (one written form of a line)."""
    fl = fold(text)
    w = _WORD.findall(fl)

    def put_ident(acc: str) -> None:
        g = ix.idents.get(acc)
        if g is None:
            return
        if ("id", acc) in allow and ("id", acc) not in new_allow:
            allowed[("id", acc)] += 1
        else:
            hits[("ident", acc)] = (g, "allow-added" if ("id", acc) in new_allow else "")

    for i, tok in enumerate(w):
        for g in ix.first_word.get(tok, ()):
            n = len(g.key)
            if tuple(w[i:i + n]) == g.key:
                if g.key in allow and g.key not in new_allow:
                    allowed[g.key] += 1
                else:
                    hits[("words", g.key)] = (g, "allow-added" if g.key in new_allow else "")
        if tok in ix.q_first:
            s = tuple(w[i:i + QUOTE_WORDS])
            if s in ix.quotes:
                hits[("quote", s)] = (None, " ".join(s))
    for m in _MASK_RUN.finditer(fl):
        g = ix.maskeds.get("".join(_WORD.findall(m.group(1))))
        if g is not None:
            hits[("masked", g.key)] = (g, "")
    for parts in ident_runs(fl):
        for a in range(len(parts)):
            acc = ""
            for b in range(a, len(parts)):
                acc += parts[b]
                if len(acc) > ix.max_ident:
                    break
                put_ident(acc)
    for acc in loose_windows(fl, ix.max_ident):
        put_ident(acc)
    for m in _HEXRUN.finditer(fl):
        g = ix.hashes.get(m.group())
        if g is not None:
            hits[("hash", m.group())] = (g, "")
    for m in _WORD3.finditer(text):
        t = m.group()
        if not (t[0].isupper() and t[1:].islower()):
            continue  # a three-letter value counts only written in Title case ("Qyx")
        f = fold(t)
        g = ix.shorts.get(f)
        if g is not None:
            key = (f,)
            if key in allow and key not in new_allow:
                allowed[key] += 1
            else:
                hits[("short", f)] = (g, "allow-added" if key in new_allow else "")


def scan(files: dict[str, list[tuple[int, str]]], gs: GoldSet, allow: dict, quotes: dict,
         new_allow: set = frozenset()) -> tuple[list, Counter]:
    """Findings (gold values not allowed, then quote hits flagged ``review``) and the count of allowed hits."""
    ix = _Index(gs, quotes)
    findings, allowed = [], Counter()
    for path, lines in files.items():
        is_lex = path.endswith(".txt") and "/lexicon/" in path
        for no, text in lines:
            hits: dict[tuple, tuple[Gold | None, str]] = {}
            for v in variants(text):
                line_hits(v, ix, allow, new_allow, allowed, hits)
            for (kind, key), (g, note) in hits.items():
                if kind == "quote":
                    where, masked = [("Judilibre", f"quote of {QUOTE_WORDS} words")], mask(note)
                else:
                    where, masked = sorted(g.where), g.masked
                findings.append({"path": path, "line": no, "kind": kind if note != "allow-added" else
                                 f"{kind}, allow entry added since base", "review": kind == "quote",
                                 "section": section_of(lines, no) if is_lex else "",
                                 "benches": sorted({b for b, _ in where}), "labels": sorted({l for _, l in where}),
                                 "masked": masked,
                                 "id": hashlib.sha256(repr(key).encode()).hexdigest()[:12]})
    # one finding per (path, line, value)
    uniq = {(f["path"], f["line"], f["id"]): f for f in findings}
    return sorted(uniq.values(), key=lambda f: (f["path"], f["line"], f["id"])), allowed


# ---------------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tree", action="store_true", help="scan the whole scope")
    g.add_argument("--diff", metavar="BASE", help="scan the lines added since BASE plus untracked files")
    ap.add_argument("--paths", nargs="+", default=None, help="scan these paths instead of the repository scope")
    ap.add_argument("--allow", default=str(HERE / "allow.txt"))
    ap.add_argument("--accept-allow", action="store_true",
                    help="with --diff: accept the allow entries added since BASE (a reviewer's decision)")
    ap.add_argument("--bench", action="append", choices=sorted(LOADERS))
    ap.add_argument("--quotes", action="store_true", help="add the Judilibre review list (never fails the run)")
    ap.add_argument("--out", default=None, help="JSON report (masked values only)")
    ap.add_argument("--max", type=int, default=0, help="print at most N finding lines (0 = all)")
    a = ap.parse_args()

    allow, errors = load_allow(Path(a.allow))
    if errors:
        print("\n".join(errors))
        return 2
    gs = GoldSet()
    for name, fn in LOADERS.items():
        if not a.bench or name in a.bench:
            fn(gs)
    quotes: dict = {}
    if a.quotes:
        quotes, notes = load_quotes()
        gs.notes.extend(notes)
    if not gs.by_key and not quotes:
        print("no gold source found under .bench_data/public or evaluation/max-protocol/corpus: nothing to check")
        return 2
    new_allow: set = set()
    if a.diff:
        new_allow, note = allow_added_since(a.diff, Path(a.allow), allow)
        if note:
            gs.notes.append(note)
        if a.accept_allow and new_allow:
            gs.notes.append(f"{len(new_allow)} allow entries added since {a.diff} accepted (--accept-allow)")
            new_allow = set()

    unread: list[str] = []
    files = tree_lines(a.paths, unread) if a.tree else diff_lines(a.diff, a.paths, unread)
    n_lines = sum(len(v) for v in files.values())
    found, allowed = scan(files, gs, allow, quotes, new_allow)
    findings = [f for f in found if not f["review"]]
    review = [f for f in found if f["review"]]

    scope = "whole " + (REPO_SCOPE if a.paths is None else "tree of the given paths") if a.tree \
        else f"added since {a.diff} + untracked"
    paths = REPO_SCOPE if a.paths is None else " ".join(a.paths)
    print(f"audit_bench: scope {scope}; {len(files)} files, {n_lines} lines; paths {paths}")
    print("gold values loaded: " + ", ".join(f"{k} {v}" for k, v in sorted(gs.loaded.items()))
          + (f", Judilibre review runs {len(quotes)}" if quotes else ""))
    for n in gs.notes:
        print(f"note: {n}")
    print(f"files not read (binary or no reader): {len(unread)}" + (f": {', '.join(unread[:20])}" if unread else ""))
    print(f"allow file: {len(allow)} entries; allowed hits: {sum(allowed.values())} ({len(allowed)} values)"
          + (f"; entries matching nothing in this scope: {len(allow) - len(allowed)}" if a.tree else "")
          + (f"; entries added since {a.diff}: {len(new_allow)}" if a.diff else ""))
    print(f"findings: {len(findings)}")
    for k, f in enumerate(findings):
        if a.max and k >= a.max:
            print(f"... {len(findings) - a.max} more (see --out)")
            break
        sec = f" [{f['section']}]" if f["section"] else ""
        print(f"{f['path']}:{f['line']}{sec}  {'+'.join(f['benches'])}/{'+'.join(f['labels'])[:60]}  "
              f"{f['kind']} {f['masked']}  id {f['id']}")
    if review:
        print(f"\nJudilibre review list (5-word runs found in one decision of the sample; not a failure): "
              f"{len(review)}")
        for f in review[: a.max or len(review)]:
            print(f"  {f['path']}:{f['line']}  {f['masked']}  id {f['id']}")
    if findings:
        per_bench = Counter(b for f in findings for b in f["benches"])
        per_file = Counter(f["path"] for f in findings)
        print("\nper benchmark: " + ", ".join(f"{k} {v}" for k, v in per_bench.most_common()))
        print("per file: " + ", ".join(f"{k} {v}" for k, v in per_file.most_common()))
    if a.out:
        Path(a.out).write_text(json.dumps({"scope": scope, "files": len(files), "lines": n_lines,
                                           "gold_loaded": dict(gs.loaded), "notes": gs.notes, "unread": unread,
                                           "allowed_hits": sum(allowed.values()), "findings": findings,
                                           "review": review},
                                          indent=1), encoding="utf-8")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
