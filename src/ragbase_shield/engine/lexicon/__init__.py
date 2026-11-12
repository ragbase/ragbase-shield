"""Lexicon loader. Data files are plain UTF-8 text, one entry per line, ``#`` starts a comment.

Files:

- ``first_names_fr.txt``: French first names (INSEE Fichier des prénoms, Licence Ouverte 2.0).
- ``whitelist_fr.txt``: courts, institutions, laws, legal terms, months, days (never masked).
- ``stopwords_fr.txt``: function words and sentence-initial words (never a name word).
- ``legal_terms_fr.txt``: roles, document words, legal nouns (never a person's name word).
- ``common_words_fr.txt``: common words, many of them also surnames (ambiguity checks).
- ``contract_roles_fr.txt``: contractual party roles, loaded with the legal terms (R1).
- ``business_words_fr.txt``: generic business adjectives and nouns that start company names (R1).
- ``trade_nouns_fr.txt``: trade head nouns ("Minoterie X") that complete ``names.ORG_TRADES`` (R1).
- ``acronyms_fr.txt``: common business and legal acronyms, never read as a company acronym or initials (R1).
- ``instruments_fr.txt``: financial instrument acronyms, never a first name when written in capitals (R1).
- ``nicknames_fr.txt``: standard diminutives that are not a prefix of the full first name (R1).

Every entry is folded with :func:`ragbase_shield.engine.normalize.fold_word` at load time.
"""
from __future__ import annotations

from functools import lru_cache
from importlib import resources

from ..normalize import fold_word

__all__ = [
    "read_lines",
    "first_names",
    "whitelist_phrases",
    "stopwords",
    "legal_terms",
    "common_words",
    "months_days",
    "business_words",
    "contract_roles",
    "trade_nouns",
    "acronym_stoplist",
    "instrument_terms",
    "nicknames",
]

# First names that are also place names or words used capitalised in legal text: they are not
# used as a first-name signal by the rules (they still work inside a registered full name).
_FIRST_NAME_EXCLUDE = frozenset({
    "paris", "france", "europe", "lyon", "nice", "lourdes", "valence", "vienne", "orleans",
    "cannes", "nancy-claude", "loire", "seine", "rhone", "jura", "lorraine", "bretagne",
    "provence", "savoie", "avril", "mai", "juin", "juillet", "aout", "mars", "janvier",
    "fevrier", "septembre", "octobre", "novembre", "decembre", "lundi", "mardi", "mercredi",
    "jeudi", "vendredi", "samedi", "dimanche", "code", "loi", "article", "justice", "cour",
    "conseil", "tribunal", "president", "maitre", "madame", "monsieur", "societe", "sas",
    "sarl", "noel", "toussaint", "paques", "nord", "sud", "est", "ouest", "sainte", "saint",
    "dieu", "ange", "amour", "liberte", "victoire", "fidele", "prudence", "patience",
    "constance", "clemence", "esperance", "providence", "modeste", "juste", "aime", "desire",
    "parfait", "heureux", "merci", "bienvenue", "salut", "joie", "bonheur", "fortune",
    "chance", "destin", "avenir", "horizon", "confiance", "verite", "raison", "sagesse",
})

_MONTHS_DAYS = frozenset({
    "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
    "octobre", "novembre", "decembre", "janv", "fevr", "sept", "oct", "nov", "dec",
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
})


def read_lines(name: str) -> list[str]:
    """Raw entries of a lexicon file (comments and blank lines removed, not folded)."""
    text = resources.files(__name__).joinpath(name).read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _folded_set(name: str) -> frozenset[str]:
    return frozenset(f for f in (fold_word(x) for x in read_lines(name)) if f)


@lru_cache(maxsize=None)
def first_names() -> frozenset[str]:
    """French first names usable as a name signal (folded)."""
    names = _folded_set("first_names_fr.txt")
    return frozenset(n for n in names if n not in _FIRST_NAME_EXCLUDE)


@lru_cache(maxsize=None)
def all_first_names() -> frozenset[str]:
    """Every first name in the lexicon, including the excluded ambiguous ones (folded)."""
    return _folded_set("first_names_fr.txt")


@lru_cache(maxsize=None)
def whitelist_phrases() -> tuple[str, ...]:
    """Whitelist phrases (folded), multi-word and single-word."""
    return tuple(sorted(_folded_set("whitelist_fr.txt")))


@lru_cache(maxsize=None)
def stopwords() -> frozenset[str]:
    return _folded_set("stopwords_fr.txt")


@lru_cache(maxsize=None)
def legal_terms() -> frozenset[str]:
    return _folded_set("legal_terms_fr.txt") | contract_roles()


@lru_cache(maxsize=None)
def contract_roles() -> frozenset[str]:
    """Defined party roles of contracts ("concessionnaire", "franchiseur"), folded; part of the legal terms."""
    return _folded_set("contract_roles_fr.txt")


@lru_cache(maxsize=None)
def common_words() -> frozenset[str]:
    return _folded_set("common_words_fr.txt")


@lru_cache(maxsize=None)
def months_days() -> frozenset[str]:
    return _MONTHS_DAYS


@lru_cache(maxsize=None)
def business_words() -> frozenset[str]:
    """Generic business adjectives and nouns ("financière", "industrielle"), folded."""
    return _folded_set("business_words_fr.txt")


@lru_cache(maxsize=None)
def trade_nouns() -> frozenset[str]:
    """Trade head nouns ("minoterie", "scierie"), folded."""
    return _folded_set("trade_nouns_fr.txt")


@lru_cache(maxsize=None)
def acronym_stoplist() -> frozenset[str]:
    """Common acronyms (folded, lower case): never a company acronym or a person's initials."""
    return _folded_set("acronyms_fr.txt")


@lru_cache(maxsize=None)
def instrument_terms() -> frozenset[str]:
    """Financial instrument acronyms (folded, lower case)."""
    return _folded_set("instruments_fr.txt")


@lru_cache(maxsize=None)
def nicknames() -> dict[str, frozenset[str]]:
    """Full first name (folded) -> its standard diminutives (folded) that are not prefixes."""
    out: dict[str, set[str]] = {}
    for line in read_lines("nicknames_fr.txt"):
        short, sep, full = line.partition("=")
        short, full = fold_word(short), fold_word(full)
        if sep and short and full:
            out.setdefault(full, set()).add(short)
    return {k: frozenset(v) for k, v in out.items()}
