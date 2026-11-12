"""Checks on the user-facing docs (owner: docs).

The docs make promises to lawyers. These tests keep the promises honest and in sync with the contract:
no em dashes, no over-claims, the CLI block matches ARCHITECTURE.md section 8, local links resolve,
no tracking on the RAGbase link, and NOTICE credits the data files the engine ships.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import ragbase_shield

ROOT = Path(__file__).resolve().parents[1]

DOCS = [
    "README.md",
    "README.fr.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "NOTICE",
    "docs/PRIVACY_MODEL.md",
    "docs/INSTALL.md",
    "docs/CONFORMITE.fr.md",
    "docs/FAQ.md",
]

# Files the docs may link to before they exist (published later by another owner).
PENDING_LINKS = {"bench/RESULTS.md"}


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", DOCS)
def test_doc_exists(rel):
    assert (ROOT / rel).is_file(), f"missing doc: {rel}"


@pytest.mark.parametrize("rel", DOCS)
def test_no_em_or_en_dashes(rel):
    text = _read(rel)
    for ch, name in (("—", "em dash"), ("–", "en dash")):
        line = next((i + 1 for i, ln in enumerate(text.splitlines()) if ch in ln), None)
        assert line is None, f"{rel}:{line} contains an {name}"


# Over-claims the product must never make (ARCHITECTURE.md section 2, rule 6).
FORBIDDEN = [
    (re.compile(r"hors\s+RGPD", re.I), "'hors RGPD'"),
    (re.compile(r"100\s*%"), "a 100% claim"),
    (re.compile(r"\banonymi[sz](e|es|ent|ed|ing)\b", re.I), "a claim that Shield anonymises"),
    (re.compile(r"\b(?:outil|logiciel)\s+d'anonymisation\b", re.I), "'outil d'anonymisation'"),
]


@pytest.mark.parametrize("rel", DOCS)
def test_no_over_claims(rel):
    text = _read(rel)
    for rx, label in FORBIDDEN:
        m = rx.search(text)
        assert m is None, f"{rel}: {label}: {text[max(0, m.start() - 40):m.end() + 40]!r}"


def _architecture_cli_block() -> str:
    arch = _read("ARCHITECTURE.md")
    section = arch.split("## 8. CLI contract", 1)[1]
    block = re.search(r"```\n(.*?)```", section, re.S)
    assert block, "ARCHITECTURE.md section 8 has no code block"
    return block.group(1)


@pytest.mark.parametrize("rel", ["README.md", "README.fr.md"])
def test_cli_block_matches_contract(rel):
    assert _architecture_cli_block() in _read(rel), f"{rel}: CLI block differs from ARCHITECTURE.md section 8"


@pytest.mark.parametrize("rel", ["README.md", "README.fr.md", "docs/INSTALL.md"])
def test_desk_url_and_uv_install(rel):
    text = _read(rel)
    assert "http://127.0.0.1:7878" in text
    assert "uvx ragbase-shield desk" in text
    assert "https://astral.sh/uv/install.sh" in text
    assert "https://astral.sh/uv/install.ps1" in text


KEY_WARNINGS = {
    "README.fr.md": ["n'attachez pas le fichier", "Ne collez pas de texte brut", "ne peut pas être rappelé"],
    "docs/INSTALL.md": ["n'attachez pas le fichier", "Ne collez pas de texte brut", "ne peut pas être rappelé"],
    "docs/CONFORMITE.fr.md": ["n'attachez pas le fichier", "ne collez pas de texte brut", "ne peut pas être rappelé"],
    "README.md": ["Do not attach the file", "Do not paste raw text", "cannot be recalled"],
}


@pytest.mark.parametrize("rel", sorted(KEY_WARNINGS))
def test_key_warnings_present(rel):
    text = _read(rel)
    for phrase in KEY_WARNINGS[rel]:
        assert phrase in text, f"{rel}: missing warning {phrase!r}"


@pytest.mark.parametrize("rel", ["README.md", "README.fr.md", "docs/CONFORMITE.fr.md", "docs/PRIVACY_MODEL.md"])
def test_says_pseudonymisation_not_anonymisation(rel):
    text = _read(rel).lower()
    assert "pseudonymisation" in text
    if rel.endswith(".fr.md"):
        assert "pseudonymisation locale et réversible" in text


LIMITS = {
    "README.fr.md": ["OCR", "jamais complète", "faits peuvent identifier", "ChatGPT web", "Microsoft 365 Copilot"],
    "README.md": ["OCR", "never complete", "Facts can still identify", "ChatGPT web", "Microsoft 365 Copilot"],
}


@pytest.mark.parametrize("rel", sorted(LIMITS))
def test_limits_section(rel):
    text = _read(rel)
    for phrase in LIMITS[rel]:
        assert phrase in text, f"{rel}: limits section misses {phrase!r}"


_LINK = re.compile(r"\]\(([^)\s]+)\)")


@pytest.mark.parametrize("rel", [d for d in DOCS if d.endswith(".md")])
def test_local_links_resolve(rel):
    base = (ROOT / rel).parent
    for target in _LINK.findall(_read(rel)):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        resolved = (base / path).resolve()
        rel_to_root = resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else path
        if rel_to_root in PENDING_LINKS:
            continue
        assert resolved.exists(), f"{rel}: broken link {target}"


_TAG_LINK = re.compile(r"https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+/blob/v([0-9][^/]*)/([^)\s#]+)")


@pytest.mark.parametrize("rel", [d for d in DOCS if d.endswith(".md")])
def test_links_at_the_release_tag_resolve(rel):
    """README.md is the PyPI page, so its links are full GitHub links at the release tag: each must name a file of
    this tree and the version of pyproject.toml."""
    version = re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.M).group(1)
    for tag_version, path in _TAG_LINK.findall(_read(rel)):
        assert tag_version == version, f"{rel}: link at v{tag_version}, pyproject.toml says {version}"
        assert (ROOT / path).exists(), f"{rel}: link at the tag to a missing file {path}"


@pytest.mark.parametrize("rel", [d for d in DOCS if d.endswith(".md")])
def test_ragbase_link_has_no_tracking(rel):
    for url in re.findall(r"https?://(?:www\.)?ragbase\.ai[^\s)>\]]*", _read(rel)):
        assert "?" not in url and "utm_" not in url, f"{rel}: tracking on {url}"


def test_readmes_offer_the_soft_link():
    assert "https://ragbase.ai" in _read("README.md")
    assert "https://ragbase.ai" in _read("README.fr.md")
    assert "Pour aller plus loin" in _read("README.fr.md")


def _text_blocks(rel: str) -> list[str]:
    return re.findall(r"```text\n(.*?)```", _read(rel), re.S)


@pytest.mark.parametrize("rel", ["README.md", "README.fr.md"])
def test_readme_example_is_real_engine_output(rel):
    """The before/after example in the READMEs must be what the engine really produces."""
    engine = pytest.importorskip("ragbase_shield.engine")
    blocks = _text_blocks(rel)
    assert len(blocks) >= 2, f"{rel}: expected the before/after example blocks"
    original, shown = blocks[0].rstrip("\n"), blocks[1].rstrip("\n")
    masker = engine.Masker(engine.MemoryStore(locale="fr"), use_ner=False)
    result = masker.mask(original)
    assert result.text == shown, f"{rel}: example differs from engine output:\n{result.text}"
    assert masker.unmask(result.text) == original
    # The example promises that variants of one name share one code.
    variants = masker.mask("M. Mercadier, Thibault Mercadier, MERCADIER Thibault").text
    assert set(re.findall(r"PERSONNE_[A-Z]+", variants)) == {"PERSONNE_A"}


def test_notice_keeps_apache_header():
    lines = _read("NOTICE").splitlines()
    assert lines[0] == "RAGbase Shield"
    assert lines[1] == "Copyright 2026 RAGbase"
    assert "This product includes software developed by RAGbase (https://ragbase.ai)." in lines


def test_notice_credits_lexicon_sources():
    """Every data file in engine/lexicon that names INSEE must be credited with its licence in NOTICE."""
    notice = _read("NOTICE")
    lex = Path(ragbase_shield.__file__).resolve().parent / "engine" / "lexicon"  # source tree or wheel
    files = [p for p in lex.rglob("*") if p.is_file()] if lex.is_dir() else []
    mentions_insee = any("insee" in p.read_text(encoding="utf-8", errors="ignore").lower()[:4000] for p in files)
    if mentions_insee:
        assert "INSEE" in notice and "Licence Ouverte" in notice
