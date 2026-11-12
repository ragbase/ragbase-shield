"""Static checks for the Shield Desk page. No server needed.

They check that the UI files exist, that the page loads its own script and stylesheet,
and that nothing in the static files points to an outside host other than the single
"Pour aller plus loin" link to https://ragbase.ai (no CDN, no fonts, no tracking).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import ragbase_shield

# The files of the package that runs (a source tree or an installed wheel): the wheel must ship them too.
STATIC = Path(ragbase_shield.__file__).resolve().parent / "desk" / "static"
FILES = ("index.html", "app.js", "style.css")
ALLOWED_URLS = {"https://ragbase.ai", "https://ragbase.ai/"}
URL_RE = re.compile(r"https?://[^\s\"'<>()`\\]+", re.IGNORECASE)


def _read(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", FILES)
def test_static_file_exists(name: str) -> None:
    path = STATIC / name
    assert path.is_file(), f"missing {path}"
    assert path.stat().st_size > 200, f"{name} looks empty"


def test_html_references_app_js_and_style_css() -> None:
    html = _read("index.html")
    scripts = re.findall(r"<script\b[^>]*\bsrc=\"([^\"]+)\"", html, re.IGNORECASE)
    styles = re.findall(r"<link\b[^>]*\bhref=\"([^\"]+\.css)\"", html, re.IGNORECASE)
    assert any(s.endswith("app.js") for s in scripts), scripts
    assert any(s.endswith("style.css") for s in styles), styles


@pytest.mark.parametrize("name", FILES)
def test_no_outside_url_except_ragbase(name: str) -> None:
    text = _read(name)
    urls = {u.rstrip(".,;") for u in URL_RE.findall(text)}
    assert urls <= ALLOWED_URLS, f"{name} points outside: {sorted(urls - ALLOWED_URLS)}"
    # Protocol-relative URLs and CSS imports would also load from outside.
    assert not re.search(r"""(?:src|href)\s*=\s*["']//""", text, re.IGNORECASE), name
    assert not re.search(r"url\(\s*[\"']?//", text, re.IGNORECASE), name
    assert "@import" not in text, name


def test_ragbase_link_has_noopener() -> None:
    html = _read("index.html")
    links = re.findall(r"<a\b[^>]*href=\"https://ragbase\.ai/?\"[^>]*>", html, re.IGNORECASE)
    assert links, "the footer link to https://ragbase.ai is missing"
    assert all("noopener" in a for a in links), links


def _dict_keys(js: str, lang: str) -> set[str]:
    m = re.search(r"\n    " + lang + r": \{\n(.*?)\n    \},\n", js, re.DOTALL)
    assert m, f"dictionary block {lang!r} not found in app.js"
    return set(re.findall(r"^      ([A-Za-z0-9_]+):", m.group(1), re.MULTILINE))


def test_french_and_english_strings_match() -> None:
    js = _read("app.js")
    fr, en = _dict_keys(js, "fr"), _dict_keys(js, "en")
    assert fr, "no French strings found"
    assert fr == en, {"missing in en": sorted(fr - en), "missing in fr": sorted(en - fr)}
    html = _read("index.html")
    used = set(re.findall(r'data-i18n(?:-[a-z-]+)?="([A-Za-z0-9_]+)"', html))
    used |= set(re.findall(r'\bt\("([A-Za-z0-9_]+)"\s*[,)]', js))
    for base in re.findall(r'\btn\("([A-Za-z0-9_]+)"\s*[,)]', js):
        used |= {base + "_one", base + "_other"}
    assert used <= fr, f"keys used but not defined: {sorted(used - fr)}"
    for required in ("Le jeton est manquant ou invalide", "Shield Desk ne répond pas",
                     "Pseudonymisation locale et réversible. Rien n'est envoyé à RAGbase.",
                     "Collez ce texte dans Claude, ChatGPT ou Copilot. Ne collez jamais le texte d'origine."):
        assert required in js, required


def test_no_html_injection_and_no_inline_code() -> None:
    """Real values are shown on this page: they must go in as text, never as HTML."""
    js = _read("app.js")
    for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
        assert banned not in js, banned
    html = _read("index.html")
    assert not re.search(r"<script\b(?![^>]*\bsrc=)[^>]*>", html, re.IGNORECASE), "inline <script>"
    assert not re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE), "inline event handler"
    assert not re.search(r"\sstyle\s*=", html, re.IGNORECASE), "inline style attribute"


def test_no_em_dash_in_ui_text() -> None:
    for name in FILES:
        assert "—" not in _read(name), name
