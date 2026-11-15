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


def _version() -> str:
    return re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.M).group(1)


# The wheel of the GitHub release of the version of pyproject.toml. Every uv and pip command of the docs installs or
# runs this file, so a copied command gives that version (since 15 November 2026).
WHEEL_NAME = f"ragbase_shield-{_version()}-py3-none-any.whl"
WHEEL_URL = f"https://github.com/ragbase/ragbase-shield/releases/download/v{_version()}/{WHEEL_NAME}"


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
    assert f"uvx --from {WHEEL_URL} ragbase-shield desk" in text
    assert "https://astral.sh/uv/install.sh" in text
    assert "https://astral.sh/uv/install.ps1" in text


# uvx, uv tool install or upgrade, uv pip install, pipx or pip install, then options (an option other than --from may
# take a value, as "--python 3.12"), then the package name alone, with or without an extra: that form installs the
# package of PyPI, not the wheel of the release. A direct reference ("ragbase-shield[ner] @ <url>") is not this form;
# its URL is checked below. tests/pages-release.spec.ts of the site uses the same pattern.
_PYPI_FORM = re.compile(
    r"\b(?:uvx|uv tool (?:install|upgrade)|uv pip install|pipx (?:install|run)|pip3? install)\s+"
    r"(?:--(?!from\b)[a-z][a-z-]*(?:[ =](?!-)(?![\"']?ragbase-shield)\S+)?\s+)*"
    r"[\"']?ragbase-shield(?:\[[a-z,]+\])?(?!\[|\s+@\s+https:)"
)
_FROM = re.compile(r"--from[\"',\s]+([^\"',\s<)`]+)")
_DIRECT = re.compile(r"ragbase-shield(?:\[[a-z,]+\])?\s+@\s+([^\"'\s<)`]+)")


def _user_command_files() -> list[str]:
    """The texts a user copies commands from: the docs, the integration guides and the MCP config examples.
    Not scanned: CHANGELOG.md (history of past versions), NOTICE (licence notice), ARCHITECTURE.md (developer
    contract), and the messages printed by the code (CLI, Shield Desk, browser extension)."""
    files = [d for d in DOCS if d not in ("CHANGELOG.md", "NOTICE")] + ["docs/NER.md"]
    integ = ROOT / "integrations"
    files += sorted(p.relative_to(ROOT).as_posix() for p in integ.rglob("*.md"))
    files += sorted(p.relative_to(ROOT).as_posix() for p in integ.rglob("*.example"))
    files += ["integrations/openai-plugin/mcp.json", "integrations/claude-code/plugin/.mcp.json",
              "integrations/claude-code/plugin/hooks/hooks.json"]
    return files


@pytest.mark.parametrize("rel", _user_command_files())
def test_uv_and_pip_commands_install_the_release_wheel(rel):
    """Every uv and pip command installs or runs the wheel of the release: "uvx --from <wheel URL>",
    "uv tool install <wheel URL>", "pip install "ragbase-shield[ner] @ <wheel URL>"". The Claude plugin runs the same
    wheel from its vendor/ folder. No MCP config runs the package name alone."""
    text = _read(rel)
    m = _PYPI_FORM.search(text)
    assert m is None, f"{rel}: a command with the package name alone: {text[max(0, m.start() - 20):m.end() + 40]!r}"
    allowed = {WHEEL_URL, "${CLAUDE_PLUGIN_ROOT}/vendor/" + WHEEL_NAME}
    for url in _FROM.findall(text) + _DIRECT.findall(text):
        assert url in allowed, f"{rel}: installs {url}, not the wheel of the release"
    for url in re.findall(r"https://github\.com/\S+?/releases/download/[^\s\"'`)]+?\.whl", text):
        assert url == WHEEL_URL, f"{rel}: {url} is not the wheel of the release"
    for v in re.findall(r"ragbase_shield-([0-9][^-\s]*)-py3-none-any\.whl", text):
        assert v == _version(), f"{rel}: names the wheel of {v}, pyproject.toml says {_version()}"
    assert not re.search(r'\[\s*"ragbase-shield",\s*"mcp"\s*\]', text), f"{rel}: an MCP config without the wheel"


def test_release_wheel_commands_are_in_the_guides():
    """The install guide and the READMEs give the commands that the site gives: run, install, update, Precise mode."""
    install = _read("docs/INSTALL.md")
    for part in install.split("## Part 2. English", 1):
        assert f"uvx --from {WHEEL_URL} ragbase-shield desk" in part
        assert f"\nuv tool install {WHEEL_URL}\n" in part
        assert f'uv tool install "ragbase-shield[ner] @ {WHEEL_URL}"' in part
        assert f"uvx --from {WHEEL_URL} ragbase-shield doctor" in part
        assert f'args = ["--from", "{WHEEL_URL}", "ragbase-shield", "mcp"]' in part
    for rel in ("README.md", "README.fr.md"):
        text = _read(rel)
        assert f"\nuv tool install {WHEEL_URL}\n" in text
        assert f"\npip install {WHEEL_URL}\n" in text
        assert f'pip install "ragbase-shield[ner] @ {WHEEL_URL}"' in text


# Code blocks of the user docs (round 2 of 15 November 2026). GitHub adds a copy button to every code block, and the
# copy button copies the whole block. The default zsh of macOS does not read "#" as the start of a comment (the option
# interactivecomments is off): a pasted line with "  # ..." fails (the words reach the command as arguments), and a
# line that starts with "#" runs a command named "#". bash and PowerShell read the comment, zsh does not. So no shell
# block (sh, bash, zsh, shell, console, powershell, or a block with no language) holds a comment: what a line does is
# in the text next to the block. A block that is not a command (a usage summary, an example text, the arguments of an
# app) is a "text" block.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_SHELL_TAGS = {"sh", "bash", "zsh", "shell", "console", "powershell", "pwsh", "ps1", ""}
_ZSH_TAGS = {"sh", "bash", "zsh", "shell", "console"}


def _shell_doc_files() -> list[str]:
    """The user docs with code blocks to copy: the READMEs, SECURITY.md, docs/ and every guide of integrations/."""
    files = ["README.md", "README.fr.md", "SECURITY.md"]
    files += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md"))
    files += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "integrations").rglob("*.md"))
    return files


def _code_blocks(rel: str) -> list[tuple[int, str, list[tuple[int, str]]]]:
    """Each fenced block of a Markdown file: (line of the opening fence, language in lower case or "", lines)."""
    out: list[tuple[int, str, list[tuple[int, str]]]] = []
    fence, start, tag, body = None, 0, "", []
    for i, line in enumerate(_read(rel).splitlines(), 1):
        m = _FENCE.match(line)
        if m and fence is None:
            fence, start, tag, body = m.group(1), i, m.group(2).strip().lower(), []
        elif m and fence is not None and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and not m.group(2).strip():
            out.append((start, tag, body))
            fence = None
        elif fence is not None:
            body.append((i, line))
    assert fence is None, f"{rel}: the code block of line {start} is not closed"
    return out


@pytest.mark.parametrize("rel", _shell_doc_files())
def test_shell_blocks_hold_no_comment(rel):
    for _start, tag, body in _code_blocks(rel):
        if tag not in _SHELL_TAGS:
            continue
        for i, line in body:
            assert not re.search(r"(^|[ \t])#", line), \
                f"{rel}:{i}: a comment in a ```{tag or '(no language)'} block: {line.strip()!r}"


@pytest.mark.parametrize("rel", _shell_doc_files())
def test_shell_blocks_paste_into_zsh(rel):
    """Outside quotes, a line of a sh, bash, zsh, shell or console block holds no character that zsh reads as a
    pattern, a redirection or the end of a command: "[--dry-run]" stops the line ("no matches found"), "<folder>"
    reads a file, ";" starts a second command. A pipe ("curl ... | sh") is allowed."""
    for _start, tag, body in _code_blocks(rel):
        if tag not in _ZSH_TAGS:
            continue
        for i, line in body:
            bare = re.sub(r"\"[^\"]*\"|'[^']*'", "", line)
            bad = sorted(set(re.findall(r"[\[\]<>;*?]", bare)))
            assert not bad, f"{rel}:{i}: {''.join(bad)} outside quotes in a ```{tag} block: {line.strip()!r}"


def test_shell_block_scan_sees_the_guides():
    """The two tests above read the blocks of the guides (a guard against a parser that finds nothing)."""
    files = _shell_doc_files()
    for rel in ("README.md", "README.fr.md", "docs/INSTALL.md", "docs/NER.md", "integrations/chatgpt/README.md",
                "integrations/browser-extension/README.md"):
        assert rel in files
    count = {rel: sum(1 for b in _code_blocks(rel) if b[1] in _ZSH_TAGS) for rel in ("README.md", "docs/INSTALL.md")}
    assert count["README.md"] >= 10 and count["docs/INSTALL.md"] >= 25, count
    assert any(t == "powershell" for rel in ("README.md", "docs/INSTALL.md") for _s, t, _b in _code_blocks(rel))


def _sh_block_starts(rel: str, lines: list[str]) -> list[int]:
    """Opening lines of the sh blocks that hold exactly these lines (indentation aside)."""
    return [s for s, t, b in _code_blocks(rel) if t == "sh" and [ln.strip() for _i, ln in b] == lines]


def test_main_uv_way_installs_the_command_first():
    """The main uv way installs the command from the wheel of the release, then starts Shield Desk: one sh block, before
    the way without an install ("uvx --from <wheel> ragbase-shield desk"). Shield Desk, the browser extension and the
    configs written by "ragbase-shield install" call "uvx ragbase-shield", and uvx then runs the installed command."""
    main = [f"uv tool install {WHEEL_URL}", "ragbase-shield desk"]
    no_install = f"uvx --from {WHEEL_URL} ragbase-shield desk"
    install = _read("docs/INSTALL.md").splitlines()
    part2 = next(i for i, ln in enumerate(install, 1) if ln.startswith("## Part 2. English"))
    places = {"README.md": [None], "README.fr.md": [None], "integrations/browser-extension/README.md": [None],
              "docs/INSTALL.md": [(1, part2), (part2, len(install) + 1)]}
    for rel, parts in places.items():
        lines = _read(rel).splitlines()
        for part in parts:
            lo, hi = part or (1, len(lines) + 1)
            starts = [s for s in _sh_block_starts(rel, main) if lo <= s < hi]
            assert starts, f"{rel} (lines {lo} to {hi}): no block with the main uv way"
            later = [i for i, ln in enumerate(lines, 1) if lo <= i < hi and no_install in ln]
            assert later and min(later) > starts[0], f"{rel}: the way without an install must come after the main way"


def test_install_texts_of_round_2():
    """The READMEs offer no PyPI package as a way to install; the arguments of ChatGPT desktop are a block of their
    own, named by the step; the update of the install guide says what to do in Precise mode."""
    for rel, sentence in (("README.md", "Python package: the wheel of the release (commands below)."),
                          ("README.fr.md", "Paquet Python : le fichier wheel de la version (commandes plus bas).")):
        text = _read(rel)
        assert sentence in text, rel
        assert not re.search(r"(?i)(package|paquet)[^.\n]*pypi|pypi[^.\n]*(package|paquet)", text), rel
    args = f"--from {WHEEL_URL} ragbase-shield mcp"
    install = _read("docs/INSTALL.md")
    fr, en = install.split("## Part 2. English", 1)
    for part, step, ner in ((fr, "Arguments : le bloc ci-dessous.", "Mode Précis : relancez plutôt la commande du mode Précis"),
                            (en, "arguments: the block below.", "Precise mode: run the Precise command again instead")):
        assert f"```text\n{args}\n```" in part
        assert step in part and ner in part
    guide = _read("integrations/chatgpt/README.md")
    assert "Arguments: the block below." in guide
    assert [b for _s, t, b in _code_blocks("integrations/chatgpt/README.md")
            if t == "text" and [ln.strip() for _i, ln in b] == [args]]


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
