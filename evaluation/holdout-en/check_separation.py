"""Report every distinctive string of the holdout corpus that also occurs in ``src/`` (code or lexicon) or in
``tests/``: the corpus measures generalisation only while nobody tunes on it.

    python evaluation/holdout-en/check_separation.py [--since COMMIT] [--strict]

Distinctive strings: the first names, last names, nicknames, handles, company words, street names and id
prefixes of ``ground_truth/<set>/characters.json`` (every one invented), minus the words a general English or
French lexicon of the engine holds anyway (stop words, business words, generic company words, street types):
"Group", "Partners" or "Avenue" in a lexicon say nothing about this corpus. Three readings:

- ``src/`` code and the synthetic word lists: a hit here is a problem (a corpus string entered the engine);
- the first-name lexicons: common first names overlap by nature; listed so the reader knows which ones;
- ``tests/``: not a detection signal; listed so invented test data and the corpus stay separate on purpose.

``--since COMMIT`` restricts ``src/`` and ``tests/`` to the lines added since that commit (``git diff``) plus
the untracked files, which is what an integrator wants before a merge. ``--strict`` exits 1 on a hit in
``src/`` code or a synthetic word list. Standard library plus the engine's own lexicon helpers; nothing of this
file is read by ``src/``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
NAME_FIELDS = ("first_names", "last_names", "nicknames", "handles", "usernames", "organizations", "orgs",
               "addresses", "streets", "employee_ids", "ids", "account_numbers", "accounts", "canonical_name",
               "name", "email", "emails")


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def dictionary_words() -> set[str]:
    """The words of the system dictionary (Webster's 2nd on macOS and BSD), folded; empty when it is absent."""
    path = Path("/usr/share/dict/words")
    if not path.is_file():
        return set()
    return {fold(w.strip()) for w in path.read_text(encoding="utf-8", errors="ignore").splitlines() if w.strip()}


def generic_words() -> set[str]:
    """Words a general lexicon of the engine holds: never a corpus-specific signal."""
    out: set[str] = set()
    try:
        from ragbase_shield.engine import lexicon as lx, names as nm, synthetic as sy
        for fn in ("stopwords", "business_words", "legal_terms", "contract_roles"):
            f = getattr(lx, fn, None)
            if callable(f):
                out.update(fold(w) for w in f())
        for attr in ("ORG_GENERIC", "LEGAL_FORMS", "ORG_TRIGGERS", "TITLE_WORDS", "PARTICLES"):
            out.update(fold(w) for w in getattr(nm, attr, ()))
        # the hand-written industry words of the English company head rules ("banking", "dairy", "cargo"): a word
        # of that list is generic when an ordinary dictionary holds it; an invented word stays reported
        dictionary = dictionary_words()
        out.update(w for w in (fold(x) for x in getattr(nm, "_EN_HEAD_EXTRA", ())) if w in dictionary)
        out.update(getattr(sy, "_ADDRESS_WORDS", ()))
        out.update(getattr(sy, "_NEUTRAL_WORDS", ()))
    except Exception as exc:  # noqa: BLE001 - the report still runs without the engine
        print(f"note: engine lexicons not loaded ({type(exc).__name__}); generic words = built-in list only")
    # every general word list of the engine (common words, stop words, whitelists, legal forms, business words of
    # both languages); the synthetic pools and the first-name lists stay out: they are reported, not filtered
    lexdir = ROOT / "src" / "ragbase_shield" / "engine" / "lexicon"
    for f in lexdir.glob("*.txt"):
        if f.name.startswith("synthetic_") or "first" in f.name or f.name.startswith("nicknames"):
            continue
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                out.update(fold(w) for w in WORD_RE.findall(line))
    out.update("inc llc ltd llp corp co plc gmbh sas sarl the and for with from this that".split())
    return out


def corpus_strings() -> dict[str, set[str]]:
    """distinctive folded word -> {set names} from every characters.json."""
    where: dict[str, set[str]] = defaultdict(set)
    generic = generic_words()

    def walk(x, field: str, name: str) -> None:
        if isinstance(x, str):
            if field in NAME_FIELDS or field == "":
                for w in WORD_RE.findall(x):
                    f = fold(w)
                    if f not in generic and len(f) >= 4:
                        where[f].add(name)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, k, name)
        elif isinstance(x, list):
            for v in x:
                walk(v, field, name)

    for cj in sorted((HERE / "ground_truth").glob("*/characters.json")):
        walk(json.loads(cj.read_text(encoding="utf-8")), "", cj.parent.name)
    return where


def lines_of(paths: list[str], since: str | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    if since:
        diff = subprocess.run(["git", "-C", str(ROOT), "diff", since, "--", *paths], capture_output=True,
                              text=True).stdout
        cur = None
        for l in diff.splitlines():
            if l.startswith("+++ b/"):
                cur = l[6:]
            elif l.startswith("+") and not l.startswith("+++") and cur:
                out[cur].append(l[1:])
        untracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", *paths],
                                   capture_output=True, text=True).stdout.split()
        for f in untracked:
            out[f].extend((ROOT / f).read_text(encoding="utf-8", errors="ignore").splitlines())
        return out
    for p in paths:
        for f in sorted((ROOT / p).rglob("*")):
            if f.is_file() and f.suffix in (".py", ".txt", ".json", ".md"):
                out[str(f.relative_to(ROOT))].extend(f.read_text(encoding="utf-8", errors="ignore").splitlines())
    return out


def bucket(path: str) -> str:
    if path.startswith("tests/"):
        return "tests"
    if "lexicon" in path and "first" in Path(path).name:
        return "first-name lexicon"
    if "lexicon" in path and Path(path).name.startswith("synthetic_"):
        return "synthetic word list"
    return "src code or lexicon"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=None, help="only the lines added since this commit, plus untracked files")
    ap.add_argument("--strict", action="store_true", help="exit 1 on a hit in src code or a synthetic word list")
    a = ap.parse_args()
    where = corpus_strings()
    hits: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for path, lines in lines_of(["src", "tests"], a.since).items():
        for l in lines:
            for w in WORD_RE.findall(l):
                f = fold(w)
                if f in where:
                    hits[bucket(path)][path][f] += 1
    print(f"holdout distinctive strings: {len(where)}  scope: {'added since ' + a.since if a.since else 'whole tree'}")
    bad = 0
    for b in ("src code or lexicon", "synthetic word list", "first-name lexicon", "tests"):
        files = hits.get(b) or {}
        n = sum(len(v) for v in files.values())
        print(f"\n[{b}] {n} string(s) in {len(files)} file(s)")
        for path in sorted(files):
            words = ", ".join(f"{w} x{c}" for w, c in sorted(files[path].items()))
            print(f"  {path}: {words}")
        if b in ("src code or lexicon", "synthetic word list"):
            bad += n
    print("\nreading: a hit under [src code or lexicon] or [synthetic word list] means a corpus string entered the "
          "engine (fix it or rebuild the corpus); first-name lexicon hits are common names; tests hits are "
          "invented data to keep apart, not a detection signal.")
    return 1 if (a.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
