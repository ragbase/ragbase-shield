# RAGbase Shield: architecture and build contract

Status: v0.1 build spec, 2026-10-16. Every module owner follows this file. If a module needs a change to a
shared contract, it writes the change here and says so in its report.

## 1. Product in one paragraph

RAGbase Shield is a free, open-source (Apache-2.0) tool that pseudonymises client data on the user's own
computer before the text reaches Claude, ChatGPT or Microsoft Copilot, and restores the real names on the same
computer afterwards. Nothing goes to RAGbase. It installs in one step and plugs natively into the apps:

| App | How Shield plugs in |
|---|---|
| Claude Desktop | One-click desktop extension (.mcpb) that runs the local MCP server |
| Claude Code / Cowork | Plugin (MCP server + skill + hooks that block raw names and mask file reads) |
| ChatGPT desktop / Codex | Local MCP server (Codex `config.toml`; ChatGPT desktop where local MCP is allowed) |
| GitHub Copilot (VS Code) | Local MCP server (`.vscode/mcp.json` / user `mcp.json`) |
| Any app (claude.ai, chatgpt.com, Copilot app, Word, Outlook) | Shield Desk (local web page) + clipboard commands + browser extension |

## 2. Privacy model (the rules no module may break)

1. **Mask before the model.** Real data must be masked BEFORE it enters a conversation. Text that the user
   types or pastes into a chat has already reached the provider; Shield cannot recall it.
2. **No real value ever goes to a model.** No MCP tool result, error message, log line or hook output may
   contain a vault value (a real name or identifier). Codes only.
3. **No unmask tool for the model.** Restoring names happens only locally: in Shield Desk, in the CLI, in
   the browser extension's own popup/side panel (never in the provider's page DOM), or by writing a file
   to disk (`shield_save_draft` returns only "saved" + a coded file id).
4. **Fail closed.** If the engine or the vault fails, the tool returns an error with codes only, never the
   raw text.
5. **Local only.** No telemetry, no network calls. The Desk binds to 127.0.0.1 only, checks the Host header,
   and requires a random per-install token. The MCP server uses stdio.
6. **Honest wording.** It is pseudonymisation (reversible), not anonymisation. Never claim 100%.
7. **Dossier names are client data.** A dossier is shown to models only by its code (DOSSIER_1). Document file
   names are shown masked.

## 3. Package layout (Python >= 3.10, package `ragbase_shield`, CLI `ragbase-shield`)

```
ragbase-shield/
  pyproject.toml                 # owner: core (lead)
  LICENSE  NOTICE  README.md  README.fr.md  SECURITY.md  CHANGELOG.md   # owner: docs
  ARCHITECTURE.md                # this file
  src/ragbase_shield/
    __init__.py                  # version
    config.py                    # paths, settings (owner: core)
    engine/                      # owner: engine
      __init__.py                # exports Shield-facing API below
      types.py                   # Entity, Span, MaskResult (contract below)
      normalize.py               # accent/case folding, offsets map
      detectors.py               # regex + checksum detectors (structured identifiers); "# --- en ---" section (v0.2)
      names.py                   # French person and company name rules, variants
      locale.py                  # v0.2: language detection, lexicon bundles, English name rules
      ner.py                     # v0.2: optional NER backends (GLiNER2, GLiNER, spaCy), chunking, download
      merge.py                   # v0.2: NER spans merged into candidates, precision guards
      synthetic.py               # v0.2: synthetic replacement mode (realistic pseudonyms)
      lexicon/                   # data files: first names, whitelist (courts, institutions, legal terms), stopwords,
                                 #   en_*.txt bundle, vocab_fr.txt, legal_forms_spelled_fr.txt, ner_stoplist_*.txt,
                                 #   synthetic_*.txt (v0.2)
      masker.py                  # Masker: mask / unmask / scan (canary)
    vault.py                     # owner: vault. Dossier registry + encrypted per-dossier entity store
    documents.py                 # owner: vault. Read PDF/DOCX/TXT/MD/EML/HTML; write DOCX/MD
    service.py                   # owner: core. High-level operations used by MCP, Desk, CLI, hooks
    mcp_server.py                # owner: mcp. FastMCP stdio server
    hooks.py                     # owner: mcp. Claude Code hook handlers
    cli.py                       # owner: mcp. argparse CLI
    clipboard.py                 # owner: mcp. macOS/Windows/Linux clipboard without extra deps
    desk/                        # owner: desk. Starlette app + static UI
      app.py
      static/index.html  static/app.js  static/style.css
  .claude-plugin/marketplace.json   # owner: integrations. Claude Code marketplace "ragbase" (must be at repo root)
  .agents/plugins/marketplace.json  # owner: integrations. ChatGPT/Codex repo marketplace "ragbase"
  integrations/                  # owner: integrations (status table: integrations/README.md)
    README.md  assets/make_icons.py
    claude-desktop/manifest.json (MCPB 0.4, server.type "uv")  server.py (launcher)  build_mcpb.sh  icon.png
    claude-code/plugin/.claude-plugin/plugin.json  plugin/.claude-plugin/icon.png  plugin/.mcp.json
                plugin/hooks/hooks.json  plugin/skills/ragbase-shield/SKILL.md
                plugin/vendor/ragbase_shield-<version>-py3-none-any.whl   # the PyPI wheel the plugin runs
    codex/config.toml.example
    openai-plugin/plugin.json  mcp.json  skills/ragbase-shield/SKILL.md  assets/icon.png   # Agent Plugins 1.0.0
    vscode/mcp.json.example  README.md (vscode:mcp/install link)
    chatgpt/README.md
    microsoft-copilot/README.md
    browser-extension/ (Manifest V3: manifest.json, background.js, content.js, options.html/js,
                        sidepanel.html/js, common.js, ui.css, _locales/{fr,en}, icons/)
  tests/                         # each owner adds tests for its module; synthetic data only
    fixtures/                    # synthetic French legal documents (owner: engine)
  bench/                         # owner: engine. Synthetic recall/precision bench + report
```

## 4. Shared contracts

### 4.1 Engine (`ragbase_shield.engine`)

```python
@dataclass(frozen=True)
class Entity:
    kind: str          # see KINDS below
    value: str         # the real text as found (never shown to a model)
    norm: str          # normalised key (lower, no accents, single spaces)
    code: str          # e.g. "PERSONNE_A", "EMAIL_1"

@dataclass(frozen=True)
class Span:
    start: int; end: int; kind: str; value: str; source: str   # source: "regex", "dictionary", "rule", "ner"

@dataclass
class MaskResult:
    text: str                      # masked text
    spans: list[Span]              # what was replaced, in original offsets
    new_entities: list[Entity]     # entities created by this call (to persist in the vault)

class EntityStore(Protocol):       # implemented by vault.Dossier
    def all(self) -> list[Entity]: ...
    def get_by_norm(self, kind: str, norm: str) -> Entity | None: ...
    def get_by_code(self, code: str) -> Entity | None: ...
    def add(self, kind: str, value: str, norm: str) -> Entity: ...   # allocates the code
    def is_kept_clear(self, norm: str) -> bool: ...                 # user said "garder en clair"

class Masker:
    def __init__(self, store: EntityStore, *, locale: str = "fr", use_ner: bool | None = None): ...
    def mask(self, text: str) -> MaskResult: ...
    def unmask(self, text: str) -> str: ...            # codes -> real values; tolerant to "PERSONNE A", "personne_a"? NO: exact codes only + common punctuation
    def scan(self, text: str) -> list[Span]: ...       # canary: known values + structured ids still present
```

KINDS and code prefixes (locale fr / en):

| kind | fr prefix | en prefix | code style |
|---|---|---|---|
| PERSON | PERSONNE | PERSON | letters: _A.._Z, _AA.. |
| ORG | SOCIETE | COMPANY | letters |
| ADDRESS | ADRESSE | ADDRESS | numbers: _1.. |
| EMAIL | EMAIL | EMAIL | numbers |
| PHONE | TEL | PHONE | numbers |
| IBAN | IBAN | IBAN | numbers |
| NIR | NIR | SSN | numbers |
| SIREN | SIREN | SIREN | numbers |
| SIRET | SIRET | SIRET | numbers |
| VAT | TVA | VAT | numbers |
| CARD | CARTE | CARD | numbers |
| CASE_REF | RG | CASEREF | numbers (RG, pourvoi, ECLI, docket numbers) |
| ID_CODE | IDENT | IDENT | numbers (ISIN, LEI, passport, plate, IP) |
| URL | SITE | SITE | numbers (web domains and URLs, except whitelisted public sites) |
| BIRTHDATE | NAISSANCE | BIRTHDATE | numbers |

Codes are unique per dossier, stable across calls, restart in each dossier. The code regex is
`\b(PERSONNE|PERSON|SOCIETE|COMPANY)_[A-Z]{1,4}\b|\b(ADRESSE|ADDRESS|EMAIL|TEL|PHONE|IBAN|NIR|SSN|SIREN|SIRET|TVA|VAT|CARTE|CARD|RG|CASEREF|IDENT|SITE|NAISSANCE|BIRTHDATE)_[0-9]{1,6}\b`
(plus `DOSSIER_[0-9]{1,6}`, `DOC_[0-9]{1,7}`, `OUTPUT_[0-9]{1,7}`; review 2026-10-16: ranges widened and shared by
`types.CODE_RE`, `masker.UNMASK_RE`, `service._CODE_SHAPE` and `documents._DOSSIER_CODE_RE`; `make_code` raises
`CodeRangeError` past PERSONNE_ZZZZ / EMAIL_999999 instead of writing a code that restore could not read).
Real text that already matches the code regex, OR the wider restore pattern `UNMASK_RE` ("USER_EMAIL_1",
"PERSONNE_Ab", "TEL_1er"), is escaped by the masker (never treated as a code; `code_like_spans(text)`).

Name variants: registering "Jean-Pierre Dupont" also matches "Dupont", "J.-P. Dupont", "M. Dupont",
"DUPONT Jean-Pierre", case and accent insensitive, across line breaks. A surname alone that is also a
common word or a first name is matched only with a title (M., Mme, Me, Maître) or with the first name.
Companies: legal forms (SAS, SARL, SA, SASU, EURL, SCI, SNC, GIE, SELARL, SELAS, Ltd, LLC, Inc, GmbH, BV, SpA)
before or after the name; "société X", "la société X"; the dossier title "X c. Y" / "X contre Y" / "X v. Y".
Never mask: courts and institutions (Tribunal judiciaire de Paris, Cour de cassation, Conseil d'État, CNIL,
AMF, ACPR, URSSAF...), laws and codes (Code du travail, article L1234-9), legal terms, months, days.

Optional NER: if `spacy` and a French model are installed, `use_ner=None` turns it on automatically.
NER spans go through the same whitelist and never override structured detectors.

Engine additions (v0.1, additive, owner: engine). All importable from `ragbase_shield.engine`:

```python
Masker(store, *, locale="fr", use_ner=None, ner=None)   # ner: optional callable text -> [(start, end, "PERSON"|"ORG")]
Masker.mask(text, *, keep_known_codes=False)  # True: codes already in the store stay as they are (re-masking an answer);
                                              # other code-like text is escaped; code-like text is never analysed
Masker.mode -> "rules" | "rules+ner"
Masker.unmask_report(text) -> (restored_text, unknown_codes)   # codes not in the store (invented by a model)
entity_norm(kind, value) -> str        # engine key: "DUPONT Jean-Pierre" -> "jean pierre dupont", "ACME SAS" -> "acme"
find_suspects(text) -> list[Span]      # source "suspect": identifiers with a wrong check digit (review list only)
parse_parties(title) -> [(kind, name)] # "Dupont c. ACME SAS" -> [("PERSON","Dupont"), ("ORG","ACME SAS")]
                                       # descriptions dropped: "Affaire X", "X - constat", "X (appel)", "2026-04 : X"
has_party_separator(title) -> bool     # True for "X c. Y", "X contre Y", "X v. Y", "X / Y"
detect_structured(text) -> list[Span]  # valid checksummed / structured identifiers, source "regex"
UNMASK_RE                              # the code pattern used by unmask (CODE_RE minus DOSSIER/DOC/OUTPUT, glued forms allowed)
```

Review fixes (2026-10-16, owner: fixer), all additive:

```python
prepare_scan(text) -> ScanPrep          # structured spans + confusable folding + tokens, shared by the canary of N dossiers
Masker.scan(text, *, prepared=None)     # canary; reuses a ScanPrep of the same text
ner_installed() -> bool                 # cheap check (find_spec); Masker() never loads spaCy, the first mask() does
canonical_codes(text) -> str            # "PERSONNE\_A", "PERSONNE_\u200bA", "PERSONNE＿A" -> "PERSONNE_A" (unmask uses it)
code_like_spans(text) -> [(s, e, code)] # every CODE_RE or UNMASK_RE match: what the masker escapes
EntityStore.revision                    # OPTIONAL: changes when entities or kept-clear terms change (matcher cache key)
EntityStore.upgrade(code, value, norm)  # OPTIONAL: give a surname-only entity its full name ("Ouardi" -> "Mehdi Ouardi")
```

- `UNMASK_RE` accepts a letter code glued to digits ("PERSONNE_A2026"); the masker adds a space when a code
  would be glued to a capital letter ("PERSONNE_A Industries") or follow a letter or digit ("2026 PERSONNE_A").
- Glued and broken forms: a second dictionary view splits glued words by case and digits ("KervadecMaelle",
  "Kervadec2026"); an English possessive ("Kervadec's") and a lower-case word after a hyphen ("Atlantide-note")
  are not compounds; "KERVA-\nDEC" is joined when the joined word is a known name word or the next line goes on
  in lower case; a social handle holding a known surname or company word is masked ("@mkervadec"). The canary
  ignores the compound rule for distinctive values ("Conclusions-KERVADEC").
- Unicode: U+2010, U+2011, U+2012, U+2212 count as hyphens inside a name, soft hyphens and zero-width
  characters are skipped, combining accents (NFD) belong to their letter.
- Names: a particle is never a first name ("Le Goff", "d'Orgeval"); `surname_key` drops particles; a full name
  links to a known surname-only person; "M." before a surname is a title, not the initial of "Mehdi";
  a name may continue on the next line after a title, or after a first name when the next line starts with an
  upper-case surname; Kbis "Nom, prénoms" fields include the extra first names; greetings, "Martine G." and
  "Signé : J. Morel" are persons; trade nouns ("Garage", "TRANSPORTS", "Pharmacie"...) and legal forms after a
  separator ("X & Y – SELAS", spelled-out forms, AARPI, SPFPL) give companies, and "X (ci-après « X »)" too;
  a company found by its legal form or a trigger word replaces a known person name inside it.
- Detectors: tribunal de commerce roll numbers ("2024J00817"), pourvoi without the dot, SIREN inside an EUID,
  lower-case IBAN (checksum decides), NIR key after " / ", "né en 1968", "City (NNNNN)" addresses, Kbis
  verification code, RCS management number, lawyer toque (`RAGBASE_SHIELD_MASK_TOQUE=0` keeps it visible),
  "permis n°"; "à la résidence de Lyon" is not an address; leading cases ("arrêt Jacques Vabre") stay in clear
  next to a case-law word.
- `ragbase_shield.engine` loads its submodules on first use (PEP 562): importing `engine.types` (the vault, the
  PreToolUse hook) no longer loads the detectors and lexicons.

Notes for callers: the masker links spellings by `entity_norm` computed from `Entity.value`, so a store may keep
any `norm` it likes (the vault's plain `normalize()` works). Entities created by the masker are added with
`store.add(kind, value, entity_norm(kind, value))`. Keep-clear is checked with `is_kept_clear(entity.norm)`
and with `normalize(surface text)`. Titles and legal forms stay in clear ("M. PERSONNE_A", "SOCIETE_A SAS");
unmask does not double them. Deviation from the rule above: a surname that is weak only because it is also a
first name ("BENALI", "MARTIN") also matches alone when written in upper case. Public case-law numbers
(pourvoi, ECLI) are masked like the client's own.

### 4.2 Vault (`ragbase_shield.vault`)

```python
class VaultError(Exception): ...                # message holds codes only (never a value, title or path)
class UnknownDossier(VaultError, KeyError): ...

class Registry:                         # ~/.ragbase-shield/registry.db (or %LOCALAPPDATA%\ragbase-shield)
    def __init__(self, home: Path | None = None): ...   # raises VaultError if the key is missing or wrong
    key_source: str                                  # "keyring" or "file" (for doctor)
    def add_dossier(self, folder: Path, title: str | None = None) -> "Dossier": ...  # returns DOSSIER_n
                                                     # same folder again -> the same dossier
    def list(self) -> list["Dossier"]: ...
    def get(self, code: str) -> "Dossier": ...       # "DOSSIER_3" (case-insensitive); UnknownDossier
    def remove(self, code: str) -> None: ...         # deletes key + vault file; works on a damaged vault
    def folders(self) -> dict[str, Path]: ...        # {"DOSSIER_n": folder}, registry only, no vault opened
    def dossier_code_for_path(self, path) -> str | None: ...   # for the PreToolUse hook (registry only)
    def dossier_for_path(self, path) -> "Dossier | None": ...
    def journal(self, event: str, dossier: str | None = None, **counts) -> None: ...
    def journal_entries(self, code: str | None = None, limit: int | None = 500) -> list[dict]: ...
                                                     # [{time (ISO, local tz), event, dossier, counts}], newest first
    def import_(self, path, passphrase, folder=None, title=None) -> "Dossier": ...   # new DOSSIER_n, codes kept
    def close(self) -> None: ...                     # also a context manager

class Dossier(EntityStore):
    code: str; folder: Path; title: str             # title and folder are REAL values: never to a model
    locale: str; uuid: str                           # locale fixed at creation (config.locale())
    def documents(self) -> list["DocRef"]: ...       # DocRef(id="DOC_7", path, name, kind, size, rel); service masks the name
    def get_document(self, doc_id: str) -> "DocRef | None": ...   # None if unknown or file gone
    def keep_clear(self, norm_or_code: str, value: bool = True) -> None: ...   # PERSONNE_A or a term
    def kept_clear_terms(self) -> list[str]: ...     # REAL values, local display only
    def register(self, kind: str, value: str) -> Entity: ...   # user adds a name (normalised)
    def entity_source(self, code: str) -> str | None: ...      # "user" | "detected"
    def output_dir(self) -> Path: ...                # <folder>/Shield - sorties (created on demand)
    def register_output(self, path) -> str: ...      # "OUTPUT_n", stable, never reused
    def get_output(self, output_id: str) -> Path | None: ...
    def journal(self, event: str, **counts) -> None: ...   # codes and counts only
    def journal_entries(self, limit: int | None = None) -> list[dict]: ...
    def export(self, path, passphrase: str) -> Path: ...   # encrypted handoff file (scrypt + Fernet), 0600

def normalize(value: str) -> str  # engine.normalize.normalize when present, else lower/no accents/1 space
```

Vault additions (review 2026-10-16, owner: fixer): `Registry.set_title(code, title)`, `Registry.is_registered(folder)`,
`Dossier.revision` (`(uuid, rev)`: a `meta.rev` counter bumped in the same transaction as every entity or
kept-clear write), `Dossier.upgrade(code, value, norm)` (a kept-clear choice follows the entity). The decrypted
snapshot is updated in place after this object's own writes and rebuilt only when `rev` changed (journal writes
no longer force a full decrypt: 800 entities in one document went from 109 s to under 2 s). The first creation
of a registry and of its master key runs under an exclusive lock file (`<home>/.registry.lock`, fcntl/msvcrt):
two processes opening a fresh home end with ONE key; the keychain is read again right before writing (never
overwritten) and after the check token is stored (if it changed, the key in use is saved to the 0600 key file).
`PRAGMA journal_mode=WAL` is retried while another process creates the file. `get_document` finds a file whose
on-disk name is NFD (NTFS, ext4). On Windows the data folder is `%LOCALAPPDATA%\ragbase-shield` (never the
roaming profile, often on a file server where SQLite WAL is not safe); a folder left in `%APPDATA%` is moved once.

Storage: `<home>/registry.db` holds one row per dossier: folder path and title Fernet-encrypted with the
master key, plus a random per-dossier data key wrapped by the master key (removing a dossier deletes its key).
One SQLite file per dossier under `<home>/vaults/<uuid>.db`: real values, norms (they reveal names) and
document/output paths are Fernet-encrypted with the dossier key; lookups use an HMAC of the norm (key derived
with HKDF), never the norm in clear. The master key lives in the OS keychain via `keyring` (service
"ragbase-shield", user "vault-key"), with a fallback key file (`<home>/key`, mode 0600) when
`RAGBASE_SHIELD_KEYRING=0` or no keychain is available. A key check token in the registry makes a missing
or wrong key fail closed. Codes are allocated sequentially per (dossier, kind) inside an IMMEDIATE SQLite
transaction (safe across threads and processes). Journal values: int/float/bool/None, codes (CODE_RE), KIND
names, document kinds ("docx", "md"...), one level of list/dict of those; anything else raises ValueError.
DOC_n ids are keyed on the path relative to the folder; ids of deleted files are never reused.
`documents()` skips hidden files/folders, `~$` Office temp files, `Shield - sorties`, symlinks leaving the
folder. Export format: `RAGBASE-SHIELD-EXPORT 1` line, JSON KDF header (scrypt n=2^15 r=8 p=1, salt),
Fernet token of the payload (entities with codes, counters, kept-clear terms, DOC ids; no journal).

### 4.3 Documents (`ragbase_shield.documents`)

`read_text(path) -> ReadResult`. A `ReadResult` IS the text (it subclasses `str`, so old `-> str` callers keep
working) and also has `.text` (plain str), `.pages` (PDF page count, else None), `.needs_ocr` (PDF with no
text layer: text is "" and callers say "OCR not available in v0.1") and `.warnings` (tuple of short codes such
as `pdf_no_text_layer`, `pdf_pages_without_text:2`, `encoding_fallback_cp1252`, `eml_attachments_not_read:1`).
Formats: .pdf (pypdf; empty user password tried), .docx (python-docx + raw XML: body in order, tables as
`a | b`, headers, footers, footnotes, endnotes, comment text without authors, content controls, text boxes
once; deleted tracked text and field codes skipped; section labels "[En-tête]"... follow config.locale()),
.txt/.md (UTF-8/UTF-16 BOM, else cp1252), .eml (From/To/Cc/Subject/Date + text/plain body, HTML fallback;
attachments not read), .html/.htm (stdlib html.parser). Errors raise `DocumentError(code)` with a short code
(`unsupported_format`, `file_not_found`, `pdf_encrypted`, `<kind>_unreadable`), never a name or content.
Writers: `write_docx(path, markdown_text, dossier_code, *, overwrite=False) -> Path` (# headings, paragraphs,
`-`/`1.` lists, **bold**, *italic*, `code`, > quotes, pipe tables, fences; the ONLY metadata is the custom
property `RAGbaseShieldDossier` = dossier code; core properties empty) and `write_md(path, text, *,
overwrite=False) -> Path`. Both write atomically and pick "name (2).ext" instead of overwriting.
Helpers: `save_output(directory, title, text, fmt="docx", dossier_code=None) -> Path` (safe + unique name
inside `directory`), `safe_filename(name, ext=None)`, `unique_path(path)`, `docx_dossier_code(path)`,
`html_to_text(html)`, `kind_of(path)`, `SUPPORTED_EXTENSIONS`, `KIND_BY_EXT`.
No GPL/AGPL dependencies (lxml comes with python-docx, BSD). The lxml binary wheels bundle GNU libiconv
(LGPL-2.1), as lxml's own licence notice states; Shield uses `lxml.etree` (licences of the installers:
`packaging/README.md`).

### 4.4 Service (`ragbase_shield.service`), used by MCP, Desk, CLI and hooks

```python
def list_dossiers() -> list[dict]                       # [{"code","documents","entities"}]  (no real titles)
def list_documents(dossier_code) -> list[dict]          # [{"id","masked_name","kind","size","pages"}]
def read_document(dossier_code, doc_id, start=0, max_chars=20000) -> dict   # {"text": masked, "next": offset|None}
def search(dossier_code, query, limit=10) -> list[dict] # query is unmasked locally, results masked
def save_draft(dossier_code, title, content, fmt="docx") -> dict   # unmask locally, write file, return {"id","bytes"}
def mask_text(text, dossier_code=None) -> dict          # for Desk/CLI/extension (local callers only)
def restore_text(text, dossier_code) -> str             # for Desk/CLI/extension (local callers only)
def scan_text(text) -> list[dict]                       # canary across ALL dossiers; returns codes/kinds only
def status() -> dict
```

Core additions (v0.1, additive, owner: core). Module functions delegate to `service.default()`, a `Service`
bound to `config.home()` (re-created when `RAGBASE_SHIELD_HOME` changes; `service.reset()` closes it).
Every function raises `ShieldError(message, kind)` on any failure; the message holds codes only.

```python
list_dossiers(include_private=False)    # include_private=True adds "title" and "folder" (Desk, CLI only)
list_documents(d) -> [{"id","masked_name","masked_path","kind","size","pages"}]   # masked_path masks sub-folders
read_document(d, doc, start=0, max_chars=20000)
    -> {"id","text","start","next","total_chars","needs_ocr","pages","warnings"}  # max_chars clamped 500..50000
search(d, query, limit=10) -> [{"document","snippet","offset"}]   # offset = a start for read_document. Codes
    # match every masked mention; plain words never match inside a masked value (no "guess the name" oracle)
save_draft(d, title, content, fmt="docx") -> {"id","bytes","format","unknown_codes"}   # title is unmasked too
mask_text(text, d=None, include_values=False) -> {"masked","found":[{"code","kind"[,"value"]}],"counts"}
restore_report(text, d) -> {"text","unknown_codes","restored","placeholders","shield_ids"}  # POST /api/restore
scan_text(text) -> [{"code" | None,"kind","dossier"}]             # registered values only; kept-clear ignored
add_dossier(folder, title=None) -> {"code","documents","entities","counts","parties","unreadable","needs_ocr"}
    # scans every document, then registers the title parties ("X c. Y") that no known entity covers.
    # A typed title is always parsed; the folder-name fallback only when it names sides
    # (engine.has_party_separator). parse_parties drops descriptions: "Dossier X", "X - constat", "(appel)".
scan_dossier(d) -> same counts                                    # POST /api/dossiers/{code}/scan
remove_dossier(d); entities(d) -> [{"code","kind","value","kept_clear","source"}]   # REAL values: local only
register(d, kind, value) -> {"code","kind","value"}; keep_clear(d, code_or_term, value=True) -> {"ok": True}
mask_file(path, d=None, name=None) -> {"name","masked_name","masked_text","needs_ocr","warnings"}  # /api/files
journal(d=None, limit=500); protect(text) -> (masked_text, codes_added)   # PostToolUse hook
Service.guard_output(text, dossier_code=None) -> text   # last canary: registered values of any dossier -> code
    # of this dossier (section 10.3) or, without a dossier, "[PERSONNE]"
```

Every model-facing string (masked names, pages, snippets, MCP results) goes through the canary
(`Masker.scan` of every dossier); a value left by the strict masker is replaced before it leaves.

Service additions (review 2026-10-16, owner: fixer):

- Fail closed: `_guard`, `scan_text`, `has_registered`, `protect` and `guard_output` raise
  `ShieldError(kind="vault_error")` when ONE registered dossier cannot be opened (its values could no longer be
  checked). Only `list_dossiers` keeps the soft `vault_unreadable` row.
- `has_registered(text) -> bool`: cheap canary (no masking), for the hooks.
- `mask_text` ALWAYS runs the canary of every dossier: without a dossier, registered values the fresh masker
  cannot see become `[PERSONNE]`, `[SOCIETE]`...; `counts` include them and the result has `canary` (number).
- File and folder names (`list_documents`, `mask_file`) go through a word pass that splits labels on "-", "_",
  ".", apostrophes, digits and case changes, for the registered names of every dossier; `mask_file` names the
  masked copy `document<ext>` when the canary still sees a value.
- `search`: a phrase that holds codes is matched against the MASKED text (no guess confirmation).
- `add_dossier`: rolls back a new dossier when the scan fails; a typed title for an already registered folder
  is stored (`Registry.set_title`) and parsed; the summary has `existing` and `title_updated`; a title party is
  skipped when an entity of ANY kind has its key, or when it is the first word of a known company.
- `MAX_DOCUMENT_CHARS = 3_000_000`: a bigger document raises `ShieldError(kind="document_too_large")`.
- Text entry points (`mask_text`, `scan_text`, `protect`, `guard_output`, `restore_report`, labels) are NFC.
- The canary and the hooks use rules-only maskers (no NER) and share one `prepare_scan` per text.

### 4.5 MCP tools (names and behaviour)

| Tool | Annotations | Returns |
|---|---|---|
| `shield_list_dossiers` | readOnly | codes + counts only |
| `shield_list_documents(dossier)` | readOnly | coded ids + masked names |
| `shield_read_document(dossier, document, start?, max_chars?)` | readOnly | masked text |
| `shield_search(dossier, query)` | readOnly | masked snippets |
| `shield_save_draft(dossier, title, content, format?)` | not destructive, not readOnly | "saved OUTPUT_n (x KB)" |
| `shield_status` | readOnly | version, engine mode, honest limits |

Server instructions (sent to the model) explain: work with codes, never ask the user for real names, save
the final document with `shield_save_draft`, tell the user to open it locally.

### 4.6 Claude Code hooks (`ragbase-shield hook <event>`, JSON on stdin, JSON on stdout)

- `UserPromptSubmit`: if the prompt contains a registered value of any dossier, block it and tell the user
  which CODE to use (never echo the value).
- `PreToolUse` (Read, Grep, Glob, Bash cat, and the other tools below): deny direct reads inside a registered
  dossier folder and point to `shield_read_document`.
- `PostToolUse`: if a tool result still contains a registered value, replace it with the masked version.

Implementation notes (core, 2026-10-16, from https://code.claude.com/docs/en/hooks):
- Block/deny answers print the JSON decision AND exit 2 with the reason on stderr, so a Claude Code version
  that rejects one JSON field still blocks. UserPromptSubmit also sets `suppressOriginalPrompt: true`.
- PostToolUse uses `hookSpecificOutput.updatedToolOutput` (all tools since Claude Code 2.1.121) with the SAME
  shape as `tool_response` (only strings change), plus `updatedMCPToolOutput` for `mcp__*` tools.
- PreToolUse also denies Edit/Write/LS inside a dossier, any access to the Shield data folder
  (`config.home()`: key, vaults, desk_token), calls to Shield Desk (`127.0.0.1:<port>`), and shell commands
  that print real values or change the vault (`ragbase-shield list|entities|restore|export|import|journal|desk|
  keep-clear|register|add`, `import ragbase_shield`). Bash analysis is best effort; PostToolUse is the second net.
- The plugin has two PreToolUse entries (review 2026-10-16): built-in tools
  `Read|Grep|Glob|LS|LSP|Bash|PowerShell|Monitor|Edit|MultiEdit|Write|NotebookRead|NotebookEdit|Artifact|SendUserFile`
  (it equals the set of tools the handler checks, a test enforces it; Monitor is checked like Bash, LSP like
  Read, Artifact and SendUserFile deny a file inside a dossier because they upload it without the model reading
  it) and `mcp__.*` (file tools of other MCP servers: every path-like string argument is checked; Shield's own
  `mcp__[plugin_ragbase-shield_]ragbase-shield__shield_*` tools are skipped).
- PostToolUse scans string AND number leaves (a registered SIREN sent as the int 388684722 becomes "SIREN_1")
  and skips Shield's own tools (their results already went through the canary). Budgets: a prompt over
  `MAX_PROMPT_CHARS` (1,000,000) is blocked, a result over `MAX_RESULT_CHARS` (2,000,000) or a check over
  `TIME_BUDGET_S` (40 s) fails closed, before Claude Code's 60 s hook timeout.
- The PreToolUse hook reads the registry alone (`hooks._registry()`), not the detection engine; every hook first
  counts the dossiers in the registry file without the key and exits at once when there is none.
- Fail closed: if Shield fails, the prompt is blocked, the tool call denied, or the tool result blanked and
  `continue: false` returned. Blanking keeps the shape: every string becomes a removal notice, every number 0,
  booleans and null stay, known field names stay (`stdout`, `filePath`...) and any other key becomes `champ_n`.

### 4.7 Desk (`ragbase-shield desk`)

Starlette app on 127.0.0.1:<port> (default 7878), opens the browser with `?t=<token>`. Pages: Dossiers (add
folder, see detected entities, keep-clear toggle, add a name), Masquer (paste text -> masked, copy), Restaurer
(paste answer -> real names, copy), Fichiers (drop files -> masked copies to download), Journal. French UI
with an English toggle. JSON API under `/api/*` used by the page and by the browser extension (token
required; CORS only for the extension origin pattern `chrome-extension://*` when a token is present).

Static UI contract (added by desk-ui, 2026-10-16), for `desk/app.py`:

- Serve `static/index.html` at `/` and the `static/` folder at `/static/` (the page loads `/static/style.css`
  and `/static/app.js`). These files hold no data: serve them WITHOUT the token. The page reads `?t=`, keeps
  it in `sessionStorage`, removes it from the address bar, and sends `X-Shield-Token` on every `/api/*` call,
  so a reload of `/` (now without `?t=`) must still return the page. Only `/api/*` checks the token.
  The Host check applies to every route.
- Recommended headers on the page and static files: `Content-Security-Policy: default-src 'self';
  img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none';
  form-action 'none'; frame-ancestors 'none'`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options:
  nosniff`. The UI has no inline script, no inline style and no external request. `Cache-Control: no-store`
  on `/api/*`.
- `POST /api/files`: multipart field `files` (repeated, one per file) and optional field `dossier`. Each
  result item may carry `error` (a French message shown as is); an empty `masked_text` is shown as "no
  readable text, OCR not available in v0.1".
- Errors: any non-2xx JSON body with `error` (or `detail`) as a string is shown to the user. 401/403 shows
  "Le jeton est manquant ou invalide"; no answer shows "Shield Desk ne répond pas".
- The UI also accepts these optional shapes: `found` items as plain code strings; `found[].value` (shown
  only on this local page); scan answer as `{KIND: n}` or `{counts: {KIND: n}}`; `documents`/`entities` in
  `GET /api/dossiers` as numbers or lists; journal `time` as ISO text or epoch seconds; `status.version`.
- The browser extension token (section 6) is shown on the Dossiers tab, card "Extension navigateur": Desk
  address (`location.origin`) and the token, hidden by default, with "Afficher" and "Copier le jeton".

Entry points used by core (added by core, 2026-10-16), in `ragbase_shield/desk/app.py`:

- `serve(port: int = config.DESK_PORT, open_browser: bool = True, show_token: bool = True) -> None` (blocking).
  `ragbase-shield desk` calls it; the CLI passes only the keyword arguments that `serve` declares.
  `show_token=False` (CLI run from an AI agent's shell) means: never print the token or the `?t=` URL.
- `create_app(*, port: int = config.DESK_PORT, token: str | None = None)` returns the Starlette app; `token`
  None reads or creates `<home>/desk_token`. `ragbase-shield verify` calls `create_app(port=..., token=...)`
  and drives it with `starlette.testclient.TestClient(app, base_url="http://127.0.0.1:<port>")`: requests
  without the token and with a foreign Host must get 401/403, a foreign web Origin must get no CORS header,
  and `/api/mask` and `/api/files` must not return a vault value.
- Use the service functions of section 4.4 (`list_dossiers(include_private=True)`, `entities`, `register`,
  `keep_clear`, `scan_dossier`, `mask_text(..., include_values=True)`, `restore_report`, `mask_file`,
  `journal`, `remove_dossier`, `add_dossier`). They raise `ShieldError` (message codes only, `.kind`).

Desk server notes (added by desk app, 2026-10-16, `desk/app.py`):

- `serve(...)` returns an exit code (0 stopped, 1 port busy, 2 bad port). `run` is an alias. It binds its own
  socket to `127.0.0.1:<port>` (not configurable; `SO_EXCLUSIVEADDRUSE` on Windows) and hands it to uvicorn
  with `access_log=False` (a `?t=` URL is never logged), `server_header=False`, `proxy_headers=False`,
  `ws="none"`. It prints the `?t=` link only when `show_token=True`. Upload folders older than 1 hour are
  removed at start.
- Token: `load_or_create_token(home=None)`. First run creates `<home>/desk_token` with `O_EXCL`, mode 0600.
  A damaged file, or one that other users can read (POSIX), gets a new token (the extension must be paired
  again). `create_app(token=...)` accepts 16 to 256 printable ASCII characters; the token never shows in a repr.
- Order of checks in one ASGI guard (outermost): Host (403 `bad_host`) on every route; then `Origin`: absent,
  `http://127.0.0.1:<port>`, `http://localhost:<port>` or an extension origin
  (`chrome-extension://<id>`, `moz-extension://<id>`), anything else 403 `bad_origin` (also
  `Sec-Fetch-Site: cross-site|same-site` on `/api/*` without an extension origin); then the CORS preflight
  (OPTIONS with `Origin`: 204 for an extension origin on `/api/*`, with `Access-Control-Allow-Private-Network`
  when asked, else 403; a preflight cannot carry the token and holds no data); then the token on `/api/*`
  (header only: missing 401 `token_missing`, wrong 403 `token_invalid`); then body limits (413 `too_large`).
  `Access-Control-Allow-Origin: <extension origin>` is sent only after a valid token. No credentials header.
- Real values (`found[].value` of `POST /api/mask`) go to the Desk page only: a request with an extension
  `Origin` gets codes and kinds only.
- Least privilege (review 2026-10-16): an extension origin may call `GET /api/status`, `GET /api/dossiers`
  (without `folder`), `POST /api/mask` and `POST /api/restore` only; any other route answers 403
  `extension_forbidden` after the token check.
- `serve()` on a busy port, run from the user's own terminal (`show_token=True`): prints the `?t=` link of the
  running Desk (same data folder, same token) and opens it with `open_browser`. The pypdf logger is set to ERROR.
- Errors: `{"error": "<French message>", "code": "<short code>"}`. ShieldError kinds map to 400
  (`invalid_argument`), 404 (`unknown_dossier`, `unknown_document`), 422 (`document_unreadable`), 500 (others).
  Other codes: `missing_field`, `invalid_field`, `invalid_json`, `unsupported_media` (415), `invalid_dossier`,
  `missing_dossier`, `invalid_folder`, `folder_not_found`, `not_a_folder`, `folder_too_wide`, `no_files`,
  `bad_upload`, `not_found`, `method_not_allowed`, `internal` (with a log reference, never a stack trace).
- Limits: JSON bodies 16 MB; `POST /api/files` 25 MB per file (larger file = an `error` item), 20 files and
  about 100 MB per request (more = 400 / 413); other requests 64 KB.
- `POST /api/dossiers` checks the folder BEFORE the vault (the vault error would read "vault error"): absolute
  path (surrounding quotes removed), exists, is a folder, and is not the disk root, the user's home folder or
  one of its parents, the Shield data folder or a folder inside it. Answer 201: the `add_dossier` summary plus
  `title` and `folder`. `POST /api/dossiers/{code}/entities` answers 201 with `{code, kind, value}`.
  `keep-clear` takes `{code, value}` or `{term, value}` (`value` defaults to true, must be a boolean).
- `POST /api/files` items: `{name, masked_name, masked_text, needs_ocr, warnings}`, or `{name, masked_name: "",
  masked_text: "", error}`. `name` is the base name of the client file name (label only). Each file is written
  to `<home>/desk-uploads/upload-XXXX/upload-<n>.<ext>` (0600, folder 0700; `<ext>` from
  `documents.SUPPORTED_EXTENSIONS` only) and deleted right after masking. Multipart parts stay in memory up
  to 25 MB (no named file in the system temp folder).
- `GET /api/journal?dossier=DOSSIER_n&limit=1..5000`. The Desk adds two journal events: `mask` with
  `dossier: null` (`spans`) for a mask without a dossier, and `files` (`files`, `errors`).
- `cli.cmd_desk` imports the app with `importlib.import_module` (a `sys.modules` entry wins even after an
  earlier import, which `from .desk import app` does not honour).

## 5. Quality gates for v0.1

- Unit tests pass (`uv run --extra dev pytest -q`; pytest is in the `dev` extra), synthetic data only.
- Bench on the synthetic corpus: every registered party and every checksummed number masked; report recall per kind.
- Leak test: for every fixture, no vault value appears in any MCP tool output or hook output.
- `uvx --from . ragbase-shield doctor` works on a clean machine; the .mcpb builds.

## 6. Desk JSON API (used by the Desk page and the browser extension)

All `/api/*` routes need the token: header `X-Shield-Token: <token>` (`?t=<token>` is read by the page only, to
keep it; the page and `/static/` hold no data and load without the token, see 4.7; the API never accepts `?t=`).
Requests with a Host other than `127.0.0.1:<port>` or `localhost:<port>` get 403. The token lives in
`<home>/desk_token` (0600). CORS: only for origins `chrome-extension://*` and `moz-extension://*`, and only
when the token is valid. Desk is a LOCAL page for the user, so it may show real values.

| Method + path | Body | Returns |
|---|---|---|
| GET /api/status | | service.status() |
| GET /api/dossiers | | [{code, title, folder, documents, entities}] (real titles: local page only) |
| POST /api/dossiers | {folder, title?} | the new dossier |
| DELETE /api/dossiers/{code} | | {ok} |
| GET /api/dossiers/{code}/entities | | [{code, kind, value, kept_clear}] |
| POST /api/dossiers/{code}/entities | {kind, value} | the entity |
| POST /api/dossiers/{code}/keep-clear | {code, value: bool} | {ok} |
| POST /api/dossiers/{code}/scan | | re-reads the folder, detects entities, returns counts per kind |
| POST /api/mask | {text, dossier?, replacement?} | {masked, found: [{code, kind[, synthetic]}], counts, mode} (no dossier = a temporary in-memory store; replacement "codes" or "synthetic", v0.2) |
| POST /api/restore | {text, dossier} | {text, unknown_codes: [..], restored: n, restored_synthetic: n, unmatched_synthetic: n} |
| POST /api/files | multipart files + dossier? | [{name, masked_name, masked_text}] |
| GET /api/journal?dossier= | | [{time, event, dossier, counts}] |

Browser extension use of this API (added by integrations, 2026-10-16): the extension service worker calls
`GET /api/status` (reads `version`), `GET /api/dossiers` (`code`, `title` for its own options and side
panel only; no `folder` for an extension origin), `POST /api/mask` (reads `masked`; the badge count is `len(found)`, else the sum of `counts`) and
`POST /api/restore` (reads `text`, `unknown_codes`, `restored`). It sends `Content-Type: application/json`,
no cookies, and `Origin: chrome-extension://<id>`; the Host is `127.0.0.1:<port>`. 401 or 403 means a bad
token. The Desk page must show the token with a copy button (for example on a "Extension navigateur" panel),
because the user pastes it into the extension options.

## 7. Build rules for every contributor

- **Clean room.** Do not copy code or data from any other project, and never from client work. Write new code. Public open data and permissively licensed
  open-source projects may be reused with attribution in NOTICE (Apache-2.0, MIT, BSD, Licence Ouverte 2.0).
  No GPL, AGPL or LGPL code or dependencies.
- **Synthetic data only.** Fixtures and bench documents are invented. Do not use real people or real company
  names other than public institutions and courts. Use invented names that look French.
- **Tests:** `uv run --extra dev pytest -q` (or `.venv/bin/python -m pytest -q`) from the repo root. `tests/conftest.py` (owned by core) sets
  `RAGBASE_SHIELD_HOME` to a temp dir, sets `RAGBASE_SHIELD_KEYRING=0` (file key, never the OS keychain in
  tests) and blocks outbound network sockets. Do not create another conftest.py.
- **Keyring:** `RAGBASE_SHIELD_KEYRING=0` forces the 0600 key file. Otherwise try `keyring`, then fall back.
- **Style:** type hints, short functions, docstrings in English, user-facing strings in French with English
  variants where the spec asks. No print() in library code (use logging); the CLI may print.
- **Pull requests:** list the files you changed, the tests you ran and their result, and any contract change.

## 8. CLI contract (`ragbase-shield`, owner: mcp; docs must match it exactly)

```
ragbase-shield add <folder> [--title TEXT]           # register a dossier folder, prints DOSSIER_n, scans it
ragbase-shield list                                  # dossiers (real titles: local terminal)
ragbase-shield entities <DOSSIER_n>                  # detected and registered entities
ragbase-shield register <DOSSIER_n> --person NAME | --org NAME | --kind KIND VALUE
ragbase-shield keep-clear <DOSSIER_n> <CODE> [--off]
ragbase-shield mask [--dossier D] [--clipboard] [--mode codes|synthetic] [FILE|-]   # prints masked text, or replaces the clipboard
ragbase-shield set <DOSSIER_n> --replacement codes|synthetic [--language auto|fr|en]  # per-dossier settings (v0.2)
ragbase-shield ner status | download [--model fastino|urchade|all] [--dir DIR] [--dry-run] [--force]  # optional NER model (v0.2)
ragbase-shield restore --dossier D [--clipboard] [FILE|-]     # prints restored text, or replaces the clipboard
ragbase-shield desk [--port 7878] [--no-browser]
ragbase-shield mcp                                   # stdio MCP server (used by every app integration)
ragbase-shield hook <user-prompt-submit|pre-tool-use|post-tool-use>   # Claude Code hooks, JSON stdin/stdout
ragbase-shield install <claude-desktop|claude-code|chatgpt|codex|vscode> [--dry-run]
ragbase-shield doctor                                # checks install, key storage, each app integration
ragbase-shield verify                                # plants synthetic data, runs every path, prints CLEAN or LEAK
ragbase-shield export <DOSSIER_n> <FILE> / import <FILE>      # encrypted vault handoff (passphrase prompt)
ragbase-shield journal [DOSSIER_n]
```

CLI notes (core, 2026-10-16): `import <FILE>` also accepts an optional `--folder DIR`. When a command runs in
an AI agent's shell (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_SANDBOX_NETWORK_DISABLED` or
`RAGBASE_SHIELD_AGENT` set), what it prints reaches the model: `entities`, `restore` and `export` refuse (exit 3),
`add`, `register`, `keep-clear` and `import` refuse too (exit 3: a model must never change what is masked;
review 2026-10-16) and `list` shows codes only. `doctor` reads `CLAUDE_CONFIG_DIR`, shows package versions, and
runs the command each configured app uses with `--version` (`uvx --offline ...`): FAIL when it cannot start.
`install claude-code` without a checkout says clearly that only the MCP server is installed (no hooks, no skill).
On Python 3.10 (no `tomllib`), `install codex` refuses to write when the server is already defined another way.
The `mask` summary reads "N code(s), M remplacement(s) (Personnes 2, Sociétés 1)". Exit codes: 0 ok, 1 error, 2 usage error (verify: 1 LEAK, 2 a path could not run).
`install` writes absolute paths (GUI apps often lack the user PATH), backs up the file
(`<name>.bak-YYYYmmdd-HHMMSS`), never rewrites a file it cannot parse, and `--dry-run` writes nothing.
`install claude-code` installs the plugin from the repo marketplace when run from a checkout (or from
`RAGBASE_SHIELD_MARKETPLACE`), else `claude mcp add --scope user` (MCP server only).

## 9. Library versions (installed in .venv)

mcp 2.3 (`from mcp.server.mcpserver import MCPServer`; FastMCP was renamed in 2.x; tool annotations via
`mcp.types.ToolAnnotations`), starlette 1.8, uvicorn 0.54, cryptography (48 on Intel Mac), pypdf, python-docx,
keyring. Run everything with `.venv/bin/python` or `uv run`.

## 10. R1 corrections (after the first internal evaluation round, R0)

Every rule below is a general rule (a pattern, a lexicon category or an algorithm), written from the finding classes
of the first internal evaluation round (R0, on invented matters; its plan and logs are not published). Tests: `tests/test_r1_names.py`, `tests/test_r1_detectors.py`,
`tests/test_r1_service.py`, `tests/test_r1_restore.py`, `tests/test_r1_integration.py`.

### 10.1 Names (owner: NAMES; `engine/names.py`, `engine/masker.py`, `engine/lexicon/`)

- `names.org_acronyms(value) -> list[str]`: upper-case acronyms of a company value (3 to 6 letters, with and
  without particles and generic words; common acronyms and dictionary words left out).
  `names.person_initials(value) -> list[str]`: initials groups of a person value without dots (2 to 4 letters).
  An acronym matches as a whole capital word or as the capital prefix of a code; dotted initials match anywhere,
  3 or 4 capitals as a whole word, 2 capitals only in an initials context. A form shared by two entities is not
  guessed.
- Variants of a registered person: the usual first name of several given names, a first name after an elision,
  diminutives (prefixes of 4 letters or more and `lexicon/nicknames_fr.txt`, registered persons only, never canary
  hits), a common-word surname in "Surname, Firstname" order, next to a party separator, capitalised in
  mid-sentence and in capitals inside a phrase, and a one-edit typo of a registered name of 6 letters or more
  with the same first letter (one owner only).
- A name part owned by two known people gets its own restorable entity, never one owner's code. A surname
  followed by a generational qualifier is a separate person. A first-name variant never matches right after a
  title. A new full name links to the one known person with a compatible list of given names.
- A hyphen compound that holds a strong registered name is one new entity for the whole compound.
- New lexicon categories: `acronyms_fr.txt` (common acronyms), `business_words_fr.txt` (generic business
  adjectives, in `names.ORG_GENERIC`), `contract_roles_fr.txt` (contractual role nouns: never a name word, a
  company only with a legal form next to it), `instruments_fr.txt` (financial instruments: never a first name),
  `trade_nouns_fr.txt` (extra trade nouns; compounds and plurals of trade nouns are trade nouns).
- Partnership names after SCP, SELARL and similar forms; fund forms (SCSp, FCPR...) are company signals; a
  person name stops before "de" + a company; "dénommée" + article introduces a defined term.
- Resolution: a company found by its context beats a known surname alone, a person after a title beats a company
  word. A bare "M" without a dot is a title only when the name is on its line and does not follow a number.
- `Masker.scan()` (canary) applies the context rule of every variant and keeps the case rule of a one-word
  variant that is a dictionary word. A distinctive one-word name stays case-insensitive (two leak tests pin it).
- A known birth date matches its other written formats with the same code.
- DOC_n, DOSSIER_n and OUTPUT_n in real text are no longer escaped. New entity values are stored on one line.

### 10.2 Detectors (owner: DETECTORS; `engine/detectors.py`)

- `table_cells(text) -> list[(start, end, folded header label)]` for the data cells of a pipe table (also a
  "label | value" row). Detectors use it for labelled columns (birth dates, vessels, schools, SIRET...).
- `Candidate.checked` (default True) is False when a check digit fails; `valid` means "the masker masks it".
  `detect_structured` returns `valid and checked`; `find_suspects` returns every value that is not both. So an
  IBAN of the exact national length whose BBAN is at least half digits, and a SIREN / SIRET with a company label
  on its line or in its column, are masked even with a wrong check digit, and stay on the review list.
- Court roll numbers with a section letter ("F 24/01234" shape) with no keyword; looser forms need a court or
  roll word on the line and never follow a law reference.
- Labelled references: a closed list of labels, then a value with 4 digits or more (laws, articles, dates, times,
  years and amounts excluded); also toque, BIC with a branch code, MiFIR identifier, postal tracking near a mail
  word, IMO numbers (`imo_valid`).
- Cadastre ("section XX n°" and parcel items after a parcel word), birth-date labels ("né(e) le :", "date of
  birth", "DOB", ISO dates), address parts (regional articles in place names, two-column pages, postcode and
  town after an address code, UK and Canadian addresses).
- Vessel and school names after a trigger word: a distinctive name is masked alone, a name of ordinary words is
  masked with its trigger word. Detectors may yield kind ORG (schools only, `PRIORITY["ORG"] = 3`).
- `RAGBASE_SHIELD_MASK_BIC` = `branch` (default: a labelled BIC with a branch code), `all`, `0`. An 8-character
  BIC stays clear by default.

### 10.3 Service and MCP (owner: SERVICE; `service.py`, `mcp_server.py`, `vault.py`)

- Search: the cached document is the masked text after the last canary of every dossier; a plain-word hit counts
  only when that word is visible in clear at that place of the text the model reads.
- Cross-dossier canary: in text that belongs to a dossier, a value of another dossier becomes a new entity of
  THIS dossier (restorable code); a one-word part of another dossier's name is replaced only when it is a
  capitalised strong name word; a hit links to an own entity only when exactly one entity owns it. The generic
  placeholder stays only when the text has no dossier. `guard_output(text, dossier_code=None)` and the
  `output_dossier()` context manager carry the dossier.
- MCP dossier scope: a server process is pinned to the first dossier a tool uses successfully (or to
  `RAGBASE_SHIELD_DOSSIER`); every other dossier code gets the code-only error `dossier_scope`, and
  `shield_list_dossiers` then lists the pinned dossier only. `RAGBASE_SHIELD_MULTI_DOSSIER=1` turns pinning off
  (`mcp_server.PIN_BY_DEFAULT = True`). Desk and the CLI are never pinned.
- Unsupported files: `vault.UNSUPPORTED_KIND`; `Dossier.documents(include_unsupported=False)` and
  `get_document(..., include_unsupported=False)`. They are listed with kind `unsupported`, a stable DOC_n id and
  a masked name; reading one gives the code-only error `unsupported_format`; counts, scans and search skip them.
- `save_draft_report(d, title, content, fmt="docx") -> {"id","bytes","format","unknown_codes","placeholders",
  "shield_ids"}` (used by `shield_save_draft`; `save_draft` keeps its four keys). The MCP save message names the
  placeholders and ids left and asks the model to rewrite those places. `restore_report` returns the same two
  lists, and `ragbase-shield restore` prints them on stderr.
- Labels (file and folder names): an acronym of exactly one registered company, the initials of exactly one
  registered person and a capitalised common-word surname owned by exactly one person get that entity's code.

### 10.4 Restore (owner: RESTORE; `restore_utils.py`, `documents.py`)

- `restore_utils.restore_for_output(text, masker, *, id_labels=None, max_chars=None) -> RestoreReport` with
  `text` (LOCAL only), `unknown_codes`, `placeholders`, `shield_ids`, `ids_replaced`, `restored`, `fixes`,
  `truncated`; `RestoreReport.public()` holds codes and counts only. Same codes as `Masker.unmask_report`.
- Each restored value: line breaks and repeated spaces collapsed; French elision fixed before a vowel sound
  (and undone before a consonant); "SURNAME Firstname" restored as "Firstname SURNAME"; after a birth-name or
  usage-name marker only the surname; a word the model already wrote before the code is not repeated.
- DOC_n, DOSSIER_n and OUTPUT_n of this dossier get their local names (`id_labels`) in the local output only.
- .docx writer: a table row split by a line break is joined; a numbered item continues the open Word list only
  when its number is the next one, else it starts a new Word list at the written number.
- File names: cut at a word boundary within 120 characters and 200 bytes (`documents.cut_at_word`,
  `trim_dangling`, `MAX_STEM_CHARS`); a restored title is cut before a restored value, never inside it.

## 11. v0.2 contract changes (one subsection per builder)

### 11.1 DETECTORS (kinds, detectors, id shape memory, variants)

- `types.KINDS` gains `USERNAME`, `EMPLOYEE_ID`, `ACCOUNT_NUMBER`; `types.PREFIXES` gains `PSEUDO/USERNAME`,
  `MATRICULE/EMPLOYEEID`, `COMPTE/ACCOUNT` (number codes). `CODE_RE`, `UNMASK_RE`, the service code shape, the
  placeholder pattern and the DLP test derive from `PREFIXES`. Known limit: real text shaped `MATRICULE_000123` is
  code-like and is escaped, not masked (same as `IBAN_1`). `types.SHAPE_KINDS = ("EMPLOYEE_ID", "ACCOUNT_NUMBER")`.
- `Entity.source: str = "detected"`: fifth field with a default (additive; "detected", "user", "ner").
- `EntityStore` optional methods (checked with `getattr`): `add_shape(kind, template)` and
  `shapes() -> list[(kind, template)]`. `MemoryStore` implements them (a known template is ignored; only the kinds
  of `SHAPE_KINDS`; the revision changes). The vault implements them in its schema v2 (SYNTH).
- `detectors.detect_candidates(text, lang=None, shapes=())`: `lang` ("fr", "en") skips a detector whose `langs`
  attribute (tuple of language codes) does not hold it; a detector without `langs` runs for every language; `None`
  runs every detector (the canary). The tuple `DETECTORS_EN` of `engine/detectors_en.py` (LOCALE-EN) is registered
  when the module exists (`_en_detectors()`); `shapes` adds the unlabelled matches of the learnt id layouts.
- New detectors (both languages): `mention` (Slack `<@ID>`, the id only), `handle` (`@name`, public mentions such as
  `@channel` excluded, `PUBLIC_HANDLES`), `labelled_id` (one label list for both languages, kind by label group,
  value through the labelled-reference gap logic, refused values: date, year, time, amount, percentage, grouped
  number without a marker, Shield code), `routing` (9 digits, ABA weights 3-7-1, Federal Reserve prefix, a payment
  word on the line; `aba_routing_valid`), `table_id` (pipe-table columns of the three kinds), `shape` (learnt
  layouts). `shape_template(value)` gives the template (`EMP-00123` -> `EMP-ddddd`, letters upper case, digits `d`,
  a pure digit run gives none). Priorities: `ACCOUNT_NUMBER` 8, `EMPLOYEE_ID` 6, `USERNAME` 6.
- `structured_norm`: `USERNAME` = value without `@`, lower case; `EMPLOYEE_ID` and `ACCOUNT_NUMBER` = alphanumerics
  in upper case.
- Birth dates: month names of both languages, "dd Month yyyy" and "Month dd, yyyy"; `_date_key` reads both; the
  masker's `_date_forms` adds the English forms of a known date.
- Precision guards: a `(T4)`-style parenthesised short token is not a toque; a bare year after a file-reference
  label and a trailing year group before a sentence end are not reference values; a SIREN/SIRET label may end the
  previous line (form layout); the SIV plate accepts mixed separators (`AB 123-CD`) and a department suffix after
  it; a public-host URL with a profile path (`/in/`, `/u/`, `/user/`, `/profile/`, `/people/`, `/@name`) is masked.
- `Masker`: `_handles(text, sources, orgs=())` also masks a known name inside the path of a public URL and the
  all-capital prefix of a hyphenated code that is the acronym of exactly one known company (`BVQ-1042`); the
  masker reads `store.shapes()` for `detect_candidates` and calls `store.add_shape` for every masked labelled value
  of a `SHAPE_KINDS` kind (`_learn_shapes`). `names.Variant` need `"casual"` (in `_FIRST_NEEDS`): the usual first
  name of a registered person (4+ letters, not a common word) in any case in chat-like text, with an English
  possessive, after `@`, or before a comma at a line start; `_context_ok` accepts `'s` after a first name; in
  chat-like text `_case_ok` accepts a lower-case mention of a distinctive one-word registered name (4+ letters, not
  a dictionary word). Chat-like text = `locale.casual_text` (LOCALE-EN) when it exists, else the engine's fallback
  (a chat marker, or 30 % of the non-empty lines start in lower case).
- `names`: `_plural_title_lists` (every capitalised item of a comma list after a plural title, up to the role
  word, rule `title_list`); `title_civility(text, pos)` ("M"/"F" from the title before `pos`) and
  `person_civility(value)` (from the usual first name through `lexicon.first_name_sex()` when LOCALE-EN provides
  it, else the tab-separated sex column of `first_names_fr.txt`, else empty); the masker's `_disambiguate` keeps the
  one owner of a shared surname whose civility matches the title before it (no sex data: R1 behaviour, own code).
- `RAGBASE_SHIELD_MASK_LEGAL_FORM=1` (`config.mask_legal_form()`): the legal form joins the company span of the
  `legal_form` rule (`SOCIETE_A` for "ACME SAS"); default 0 keeps it in clear (`SOCIETE_A SAS`).
- CLI `_KIND_LABELS` and the Desk labels (`kind_*`, `kind1_*`, `PREFIX_KIND`, `CODE_RE`) know the three kinds.

### 11.2 NER (`engine/ner.py`, `engine/merge.py`, lexicon additions; details: docs/NER.md)

- Backends behind one protocol (`NerBackend`: `name`, `labels` model label -> Shield kind, `thresholds`,
  `predict(chunks) -> [[NerSpan]]`): `gliner2:fastino` (`fastino/gliner2-privacy-filter-PII-multi`, package
  `gliner2`, Apache-2.0, default), `gliner:urchade` (`urchade/gliner_multi_pii-v1`, package `gliner`, Apache-2.0),
  `spacy:<model>` (the v0.1 French model), `CallableBackend` (tests, custom models). `load_backend(model="auto")` is
  a thread-safe singleton per key, loads on the first call (10 to 15 s), returns None when nothing usable is
  installed; `ner_installed(model)` and `resolve_model(model)` never import torch; `backend_name(model)` gives the
  display name without loading. Settings: `RAGBASE_SHIELD_NER` (auto | on | off), `RAGBASE_SHIELD_NER_MODEL` (auto |
  fastino | urchade | spacy), `RAGBASE_SHIELD_NER_MAX_CHARS` (200000), `RAGBASE_SHIELD_NER_THREADS`,
  `RAGBASE_SHIELD_MODELS_DIR` (`<home>/models`, Hugging Face cache layout; the user's own HF cache is searched too).
- Local only: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` are set before the libraries
  are imported. The download is one explicit user step: `download_model(model, dry_run=, force=)` behind
  `ragbase-shield ner download` (refused in an AI agent's shell, `--dry-run` allowed). `status()` / `status_lines(lang)`
  feed `ner status`, `doctor` and `service.status()["ner"]`.
- `chunk_text(text, max_chars=1200)` cuts at blank lines, line ends, sentence ends, spaces (no overlap, exact
  concatenation); `run_ner(text, backend, kinds=None, batch_size=16, cache=...)` batches the chunks, maps the offsets
  back, drops a span whose text is not at its offsets, applies the per-label thresholds, keeps the best score per
  span, caches per chunk hash (offsets and labels only, never text). `as_hook(backend)` is the v0.1 `Masker(ner=...)`
  adapter.
- `merge.merge_ner(text, ner_spans, rule_spans, structured, protected, lang=, org_acronyms=) -> [MergedSpan]`:
  edges trimmed (titles, legal forms, function words), spans over structured or protected intervals dropped, spans
  made of stop words, legal terms, months or `ner_stoplist_<lang>.txt` entries dropped, statutory phrases cut from the
  start, rules win on kind (an exact rule span adds nothing; a span that contains one rule span extends it only over
  name words), NER-only names pass the precision guards (vocabulary word, place, acronym, all-capital line, one-word
  person with a context cue, one-word organisation, generic organisation words), identifier values pass a shape check,
  nested spans collapse to the longest. `guard_ner_spans` is the same without rule spans. `is_name_word`, `trim_span`,
  `lists_for(lang)` are the building blocks. Thresholds by kind (PERSON 0.40, ORG 0.60 fastino / 0.45 urchade, values
  0.50) and the one-word rules were chosen on the dev fixtures and the invented gap snippets only (docs/NER.md 5).
- Lexicon: `ner_stoplist_fr.txt`, `ner_stoplist_en.txt`, `vocab_fr.txt` (hand-written, 2,401 words),
  `legal_forms_spelled_fr.txt` (150 spelled-out forms + short forms); additions to `acronyms_fr.txt` (court
  functions JAF, JEX, JLD, JAP...), `legal_terms_fr.txt`, `whitelist_fr.txt`. `names._skip_spelled_form` makes the
  trigger rule start a company name after a spelled-out form ("société d'économie mixte X").
- `pyproject.toml` extras `ner` (gliner2, gliner, torch, transformers < 5, huggingface_hub, sentencepiece, protobuf)
  and `ner-spacy`. NOTICE lists the model and package licences.

### 11.3 LOCALE-EN (`engine/locale.py`, `engine/lexicon/en_*.txt`, the `# --- en ---` section of `detectors.py`)

- `locale.detect_language(text, default="fr") -> "fr" | "en"`: deterministic, standard library only (weighted
  function words of both languages, 0.5 per accented letter for French; a language wins at score 3 and 1.5 times the
  other; a text under 40 letters takes `default`). `casual_text(text)` (chat-like text: 30 % of the lines start in
  lower case, or a mention marker). `language_setting()` reads `RAGBASE_SHIELD_LANGUAGE` (auto | fr | en).
- `locale.bundle(lang) -> Bundle` (cached, frozen): first names with sex, nicknames, stop words, months and days,
  greetings, titles, common words, vocabulary, places, acronyms, legal forms (strong / weak, spelled out), suffix,
  generic and trigger organisation words, whitelist phrases, legal terms, roles. English files carry `# [section]`
  headers (`read_sections`). Word predicates: `is_first_name`, `first_name_sex`, `is_stopword`, `is_vocab_word`,
  `is_place`, `is_acronym`, `is_title`, `legal_form`, `is_name_word`, `is_org_word`, `is_distinctive`,
  `dictionary_word(tok, lang)`.
- `locale.detect_names_en(text) -> [names.RuleSpan]`: titles, "First Last" with initials, particles, hyphens and
  Jr/Sr/II/III, "Surname, First", greetings and sign-offs, speaker labels, role words, possessive first names, a
  strong first name alone (priority 2; not an imperative verb at a sentence start: "Ping me", "Bill them"); legal
  forms after the name, suffix words ("Brightwater Capital Partners"), "X & Y" firms, trigger words ("at Northvale",
  "client Lakeshore Medical"), "Bank of X", possessive companies. Priorities match the French rules so that
  `Masker._resolve` ranks them the same way.
- `locale.protected_intervals_en(text, folded, ftoks)`: whitelist phrases, court, public-body, county, act and
  section patterns. `title_before_re(lang)`, `salute_before_re(lang)`: the per-language regexes the masker uses
  before a known name.
- Detectors with `langs = ("en",)` in `detectors.DETECTORS_EN`: NANP and UK phones, SSN (kind NIR, en prefix SSN)
  and ITIN, NINO, US street addresses with unit, city, state and ZIP, PO boxes, UK postcodes; a bare ZIP is never
  masked. `detect_candidates(text, lang="en")` runs them with the language-neutral detectors.
- Sources: US Census Bureau 1990 first-name files (public domain) plus a hand-written supplement; every other list
  is written for RAGbase Shield.

### 11.4 SYNTH (synthetic replacement mode; `engine/synthetic.py`, `vault.py`, `restore_utils.py`, service, CLI, Desk)

- `Masker(store, ..., replacement="codes" | "synthetic")`; `Masker.replacement`; `Masker.mode` gets the suffix
  `+synthetic`. In synthetic mode every masked mention is written as a realistic pseudonym instead of a code: the
  part of the fake value that matches the variant (surname alone, first name alone, initials, "Surname, Firstname",
  upper case, another written form of a date, the digits of a phone or an identifier laid over the separators of the
  text). The synthetic values live in the store (`EntityStore` optional methods `synthetic(code)`,
  `set_synthetic(code, value)`, `get_by_synthetic_norm(norm)`, `synthetic_seed()`; `MemoryStore` and `vault.Dossier`
  implement them) or, for a store without them, in the masker only. Fail closed: a rendering that would still show
  a distinctive word or the digits of the real value is replaced by the code. A text masked again in synthetic mode
  keeps its known synthetic surfaces; masked again in codes mode they become the codes. The canary, the hooks, the
  label pass and `scan_text` build their own maskers in codes mode: synthetic mode never weakens them.
- `engine.synthetic.Synthesizer(seed, lang, store, *, cache=None, gender="keep")`: `value_for(entity)` (deterministic
  from `HMAC(seed, code, attempt)`, unique against every real norm and name word of the store, every other fake
  value and every whitelist word; people with one real surname key share one fake surname; a fake e-mail is built
  from the fake person and the fake company; `.example` domains; ARCEP, Ofcom and NANP fiction phone ranges;
  valid IBAN, SIREN, SIRET, VAT, NIR keys and Luhn test card BINs; birth dates shifted by 30 to 400 days in the same
  written form; other kinds keep their shape), `render(entity, fake, surface)`, `restore(entity, fake, surface)`,
  `date_offset(entity)`, `collisions` (Counter per kind of `UNVERIFIED_KINDS`: values without a reserved fiction
  range). `shift_date_text(text, days)`. Lists: `engine/lexicon/synthetic_*.txt` (written for Shield; the fake first
  names carry a sex column that `gender="keep"` uses; `lexicon.first_name_sex()` is used too when LOCALE-EN ships it).
- `MaskResult.mode` ("codes" | "synthetic"), `MaskResult.codes` and `MaskResult.replacements` (aligned with
  `spans`): additive fields with defaults.
- `Masker.unmask_report` / `unmask` restore the synthetic surfaces first (full and partial forms, any case), then
  the codes. `Masker.synthetic_restore_items(text) -> [(start, end, entity, real text)]` and
  `Masker.synthetic_altered(text) -> int` (capitalised words one edit away from a synthetic name word that no mention
  covers) feed `restore_utils.restore_for_output`: `RestoreReport.restored_synthetic`, `RestoreReport.unmatched_synthetic`
  (counts, in `public()` too). The form fixes (line breaks, elision, name order, birth-name marker, doubled word)
  apply to a restored synthetic mention as to a code.
- Vault schema `2`: `entities.synth_enc`, `entities.synth_mac` (unique keyed HMAC of the normalised fake value), table
  `shapes(kind, template_mac, template_enc, created)`, settings in `meta` (`setting:language`, `setting:replacement`,
  values checked against `vault.DOSSIER_SETTINGS`). A schema-1 vault is migrated in place on open (`ALTER TABLE ADD
  COLUMN`), nothing re-encrypted. `Dossier.add(kind, value, norm, source="detected")` ("detected" | "ner"; "user"
  stays reserved to `register`); `Entity.source` is filled from the row; `vault.ENTITY_SOURCES`. `Dossier.synthetic_seed()`
  = HKDF of the dossier data key (info "synthetic v1"), never stored or exported. `Dossier.add_shape` / `shapes()`
  (DETECTORS' id shape memory, vault part). `Dossier.setting(key)`, `set_setting(key, value | None)`, `settings()`.
  Export version 2: `synthetic` per entity, `shapes`, `settings`; import accepts versions 1 and 2.
- Service: `mask_text(text, dossier_code=None, include_values=False, replacement=None)` returns `mode` and, in
  synthetic mode, `found[].synthetic`; `set_dossier_setting(dossier_code, key, value | None) -> settings`;
  `status()` adds `replacement` (the default of `config.replacement()`, env `RAGBASE_SHIELD_REPLACEMENT`) and
  `replacements`; `entities()` adds `synthetic`; `list_dossiers(include_private=True)` adds `replacement`;
  `restore_report()` adds `restored_synthetic` and `unmatched_synthetic`; `Service._masker(d, replacement=None)` is
  cached per (dossier, replacement) and takes the dossier setting by default; a document read in synthetic mode
  keeps its search alignment from the exact edits (`_edits_alignment`).
- CLI: `mask --mode codes|synthetic` (`--synthetic` = `--mode synthetic`; without `--dossier` the pseudonyms cannot be
  restored and the CLI says so); `set DOSSIER_n --replacement codes|synthetic|default [--language auto|fr|en|default]`
  (refused in an AI agent's shell, exit 3); `restore` prints the synthetic counts; `verify` adds four paths: synthetic
  masking, its exact restore, a synthetic answer masked again in codes, the synthetic values of the entities.
- Desk: `POST /api/mask {text, dossier?, replacement?}` -> `{masked, found, counts, mode}`; `POST /api/restore` adds
  `restored_synthetic`, `unmatched_synthetic`.
- Honest wording: synthetic mode is pseudonymisation with realistic pseudonyms, reversible through the vault, not
  anonymisation (the CLI says so when it is on). Identifiers without a reserved fiction range can collide with a real
  number (`UNVERIFIED_KINDS`); the Synthesizer counts them.

### 11.5 Integration (v0.2 pipeline, owner: integrator)

- `Masker(store, *, locale="fr", language="auto", use_ner=None, ner=None, ner_model="auto", replacement="codes")`.
  `Masker.mode`: `"rules"`, `"rules+ner"` (a plugged function) or `"rules+ner:<backend>"` (`gliner2:fastino`...),
  with the suffix `+synthetic`. `ner_installed(model)` / `ner_available(model)` of `engine` delegate to `engine/ner.py`
  (the v0.1 spaCy model is the `spacy` backend). The model is loaded on the first `mask` that needs it; a load or a
  prediction failure logs the backend name and the exception type (never text) and the call goes on with the rules.
- `Masker.mask` pipeline: language (pinned, else detected per text; a short text takes the language of the code
  labels) -> protected intervals of the language -> structured detectors of the language and the learnt id layouts ->
  name rules of the language (`names.detect_names` or `locale.detect_names_en`) -> NER (`ner.run_ner` on the whole
  text up to `RAGBASE_SHIELD_NER_MAX_CHARS`, then `merge.merge_ner` with the rule and regex candidates, the protected
  intervals and the acronyms of the registered companies; each merged span is a candidate of source `"ner"`,
  rank 3) -> dictionary of known entities and pendings -> `_resolve` -> keep-clear and codes -> codes or synthetic
  rendering. The per-language title and salutation regexes and the dictionary-word check follow the language of the
  text (`_context_ok`, `_dictionary`).
- Containment of a model-only find: a pending or stored entity of source `"ner"` made of one word gets no partial
  and no lower-case variant (`_refs_for`); the rules seeing it, a two-word sighting or an upgrade lifts the
  containment (`MemoryStore.add(kind, value, norm, source="detected")`, vault `upgrade` resets `ner` to `detected`).
- `MaskResult.language` ("fr" | "en") and `MaskResult.ner` ("" rules only, the backend name, `"custom"`,
  `"skipped: text too long"`): additive fields with defaults.
- `engine.__init__` exports `detect_language`, `casual_text`, `bundle`, `detect_names_en`, `protected_intervals_en`,
  `merge_ner`, `guard_ner_spans`, `is_name_word`, `load_backend`, `run_ner`, `as_hook`, `chunk_text`,
  `download_model`, `backend_name`. `config`: `language()`, `ner_setting()`, `ner_model()`, `models_dir()`.
- Service: `_masker(d)` passes the dossier `language` setting (else `config.language()`) and `config.ner_model()`;
  `_rules(d)`, the canary, the hooks and the label pass keep `use_ner=False`. `status()` adds `language` and `ner`
  (setting, model setting, backend, loaded, max_chars, cached models, models directory: no dossier data).
  `service.preload_ner()` starts the model load in a daemon thread; `ragbase-shield mcp` and `desk` call it.
- CLI: `ner status | download | install [--model fastino|urchade|all] [--dir DIR] [--dry-run] [--force]`; `doctor`
  prints the NER status lines (packages, cached models, resolved backend; nothing is loaded).
- Evaluation runners (`evaluation/public/*/run_shield.py`) take `--ner off|auto` (default off = the R1 rules mode)
  and `--language`; the data of a benchmark is read from `.bench_data/public/<bench>/` of the checkout (gitignored).
- Speed on this Intel Mac (16 threads): rules mode about 180 k characters per second; rules + `gliner2:fastino`
  about 1 to 2 k characters per second on a first read (chunk cache: a page read twice costs nothing the second
  time). NER is skipped above `RAGBASE_SHIELD_NER_MAX_CHARS` and never runs in the hooks or the canary.

## 12. v0.3 contract changes: the PrivacyBench ladder (plan of 2026-10-19; build 2026-10-21)

Goal of the ladder: close the recall gap of the v0.2 rules mode on PrivacyBench v2.5 with general mechanisms
only: no benchmark string in `src/`, the lexicons or the tests, the privacy rules of section 2 unchanged (no real
value in a model-facing output, fail closed, local only). Rules mode stays the product default. Every number below
is an "informed" (dev set) number. Correction (v0.3.1): the v0.3 commit `89e0b6c` did NOT pass the corpus audit:
the Max-corpus audit `audit_fix.py --diff 693573f` (internal) gave 1 finding (a false match in this file), and PrivacyBench gold values sat in tests,
docstrings and comments (`audit_fix.py` checks only the Max corpus). v0.3.1 replaced them with invented values and
added the clean-room audit of every benchmark we hold (section 13.3): both audits give 0 findings on v0.3.1.

### 12.1 S1+S4 (spans and organisations; `engine/names.py`, `documents.py`, `engine/detectors.py`)

- `names.detect_names(text, lang="fr", protected=None, domains=())` is the one entry point for both languages: the
  French rules of the module, or `locale.detect_names_en` for "en", then `refine_rule_spans(text, spans, lang, ...)`:
  the legal-form span policy, company span edges (extension over head and unit words; it stops at a line break, a
  cell separator " | ", a comma, a legal form, a first name, a protected term or another span), companies named by an
  e-mail domain of the text or of the dossier (`domains`: a distinctive label matches any capitalised mention, a
  dictionary-word label needs a company cue), declared acronyms and aliases ("Full Name (FN)", quoted alias,
  "ci-après « X »"), same-surface propagation of multi-word company names. `STRONG_ORG_RULES` = the rules whose span
  carries strong evidence of its kind (legal form, field, partnership, party definition, domain, acronym).
- `names.legal_form_policy()`: `"clear"` (default: the span excludes the form, "SOCIETE_A SAS"), `"cover"`
  (`RAGBASE_SHIELD_LEGAL_FORM_SPAN=cover`: the span covers the form, the masker writes `lead + code + tail` from
  `org_form_parts(surface, lang)` and stores the core as the entity value, so the form stays readable and restore
  gives the text back), `"mask"` (`RAGBASE_SHIELD_MASK_LEGAL_FORM=1`, v0.2). `legal_form_after` / `legal_form_before`.
- Token roles of a person mention: `person_token_roles(value)`, `surface_roles(surface, entity_value)`,
  `person_nicknames(value)`; a quoted or bracketed nickname inside a full name is its own token ("nick"); "Ashbury,
  Ray" gives family then nick. `split_person` keeps the comma order.
- `documents.pdf_page_lines(page, return_chars=)`, `pdf_word_separator(prev, word)`, `pdf_cell_gap()`,
  `pdf_page_text(page)`: a gap wider than 2 x the mean character width between two words of one line is a table cell
  and becomes " | ". `_read_pdf_plumber` (pdfplumber, MIT; declared in `pyproject.toml`) with the pypdf fallback.
  The PrivacyBench runner's `pdf_text` calls the same functions.
- `detectors.email_domains(text)`: the domain labels of the e-mail addresses of a text (public mail hosts excluded).

### 12.2 S2+S3 (resolution and directory; `engine/directory.py`, `engine/masker.py`, `vault.py`, `service.py`)

- `directory.build(docs, lang="auto") -> Directory`: people and organisation labels of one dossier from e-mail
  From/To/Cc/Bcc/Reply-To, Slack `users.json`, docx `core.xml` authors, sign-off signature blocks and declared
  nicknames ('First "Nick" Last', "(goes by Nick)", "dit"); `Directory.persons`, `.domains` (label -> count, public
  hosts excluded), `lookup(surface)`, `person_roles(surface)`, `roles(token)`, `persons_for(token)`, `by_norm(norm)`,
  `seed(store, source="directory")` (every full name is in the store before the first mask), `to_dict/from_dict`,
  `domain_label()`, `split_name()`. Items: a path (`.eml`, `users.json`, `.docx`, text) or a `(kind, data)` tuple.
- `Masker(store, ..., directory=Directory | None)`; without it the masker calls `store.directory()` when the store
  has it. `Masker.directory`, `Masker.person_roles(surface, entity=None) -> [(word, role)]` (roles from the entity
  the mention refers to, the store, the dossier directory, the "Last, First" order and the export's evidence, never
  from the position alone when something better is known), `Masker.name_roles() -> {token: {roles}}`.
- Export evidence (S2): `_tally` counts per folded surface what each text showed it to be (given, family, nick,
  person_cue, org, org_head, username) into the store (`add_evidence`) or the process; `_evidence_pass` uses the
  counts before the span resolution (a bare first name with company evidence is the company; a "First Last" span
  the export shows more often as a company is a company; a weak company rule over known person tokens is a list
  of people; "Last, First" with a common word first is not a person span). Rules keep their kind in `_resolve`: a
  rule candidate with a cue is never replaced by a dictionary entity of another kind; a strong company rule beats a
  surname when the evidence agrees; a known name keeps the priority of the rule that found it. Slot rule:
  `USERNAME`, `EMPLOYEE_ID`, `ACCOUNT_NUMBER` and `ID_CODE` dictionary variants match only in their slot (after
  "@", after a label, or id-shaped), never in prose. `_comma_order` keys both written orders of a person to one
  entity.
- Store duck typing (optional, checked with `getattr`): `evidence()`, `add_evidence(batch)`, `directory()`,
  `set_directory(dict)`. The vault adds the encrypted tables `evidence` and `directory` (additive, no schema version
  change), counters `erev` / `drev`, export/import of both; `ENTITY_SOURCES` gains `"directory"`.
- `Service._build_directory(d)` runs in `_scan` (`add_dossier`, `scan_dossier`): builds and seeds the directory,
  never blocks a scan; the scan summary gains `"directory": <persons>`.

### 12.3 S5+S6+S7 (lexicon, identifiers, gated NER; `engine/detectors_ids.py`, `engine/merge.py`, `engine/ner.py`)

- `en_first_names.txt` [supplement] and [nicknames] sections (v0.2 and S5): international and post-1990 first names
  and short forms written for Shield by region of origin, with no data set behind them (header of the lexicon; the
  v0.3 text here said "public first-name statistics", which was wrong). The clean-room audit allows the common
  given names among them that are also benchmark values under rule 6 of `evaluation/audit/allow.txt` (section 13.3).
- `detectors_ids.DETECTORS_IDS` (registered at the end of `detectors.py`): `labelled_id` cue values (a label noun
  of an account or staff identifier, then an id-shaped value on the line; phone, date, amount, year, version and
  grouped-number shapes refused), keyed lines, `layout_id` (every token of a cue-confirmed layout in the same text,
  tails "5826-3306, -3307"), `table_id` (pipe-table columns), `address_street` (English street-level edges over a
  wrapped line). `ID_CODE` maps to the scorer alias `ID_NUMBER` in the adapters.
- Gated NER layer (`merge.merge_ner`, rules 7 and 8 of its docstring): on the masker path a model find may add only
  the kinds of `merge.MODEL_KINDS` (PERSON, ORG, ADDRESS, USERNAME, EMPLOYEE_ID, ACCOUNT_NUMBER); a model "username"
  needs a handle shape, an id a label cue or a letter-prefixed code shape; ID_CODE, EMAIL, PHONE, BIRTHDATE finds and
  the named assets (`ner.WATCH_LABELS`: vessel, building, school) go to `merge.watch_ner()` and are never masked on
  their own. Every kept span carries `MergedSpan.signals` (`merge.SIGNALS`: "cue", "rule", "repeat", "domain",
  "known"; `known_values` = the dossier's own entities). `ner.label_thresholds()` adds per-label floors (the two
  generic account labels 0.60); `ner.ner_device()` (`RAGBASE_SHIELD_NER_DEVICE=auto|cpu|cuda`), a CUDA
  out-of-memory error halves the batch, then moves the model to the CPU.

### 12.4 SYNTH-LEAK + HOLDOUT (`engine/synthetic.py`, `evaluation/holdout-en/`)

- Collision index of the whole store (every real value of every kind, every fake, the reserved surfaces): a fake
  never equals a real value, never reuses a word of a real value, never equals another fake, never holds a
  whitelist word, never is one edit from a real word, never has initials that read as a group of a real value.
  `Synthesizer.value_for()` re-checks a known fake against the store as it is now; `collisions_with_store()`,
  `redraw_collisions()`, `values()` (the only safe source of known fake surfaces), `reserve(surfaces)` (detected
  but unregistered surfaces). Fail closed: `SyntheticCollision` and `SyntheticLeak` raise, the masker writes the
  code; counters `redrawn`, `failed_closed`, `collisions`. Shape rules: word count kept, every replaced word starts
  with another letter, case and separators kept.
- v0.3 left two leak causes (found in the v0.3 PrivacyBench run): nicknames of a known person written
  unchanged (cause A) and one-letter fake forms that hid real text (cause B). v0.3.1 fixes both (section 13.1).
- `evaluation/holdout-en/`: `make_holdout.py` (10 invented English exports, `tasks/`, `ground_truth/`),
  `run_holdout.py [--synthetic [--register-first]]`, `score_holdout.py [--syncover]`, `check_separation.py --since
  <base> [--strict]` (no corpus string in the engine lists), `README.md`, `build_report.json`.

### 12.5 Integration (v0.3 pipeline, owner: integrator)

- `Masker.mask` pipeline: `_seed_directory` (every full name of the directory is in the store before the first
  mask) -> language -> protected intervals -> structured detectors of the language, the learnt id layouts and the
  identifier cue rules -> `names.detect_names(text, lang, protected, domains=self._domains())` (the e-mail domain
  labels of the directory name the companies) -> NER (`run_ner`, then `merge_ner(..., known_values=<the dossier's
  non-model entities>)`; each merged span is a `_Cand(source="ner", signals=...)`; `watch_ner` fills
  `MaskResult.watch`) -> dictionary of known entities and pendings (`_Pending.signals`) -> `_resolve` with the
  export evidence (`_evidence_pass`; "First Last of Company" keeps the person and the company apart; an exact rule
  match of a stored model find marks its dictionary candidate with the "rule" signal) -> guards -> `_apply`:
  codes or synthetic rendering.
- Gated NER in the masker: a model find that no second signal confirms is stored with source `"ner"` and gets the
  v0.2 containment for every word count (the exact capitalised surface only: no partial, no lower-case variant); a
  login name or an identifier of the model alone gets no dictionary variant (masked where the model finds it). A
  find with a signal is stored as a detected entity (full variants). The rules, or a signalled model find, seeing
  a stored model-only entity confirm it: optional store method `confirm(code) -> Entity | None` sets the source to
  `"detected"` (`MemoryStore` and the vault; a store without it keeps the entity as it is). `MaskResult.watch`
  (additive): `(start, end, kind, model label)` of the finds the gate never masks on its own, for a review step.
- Synthetic leak fix in the masker: before it looks for known fake surfaces, `_apply` reserves every candidate of
  the text that the store does not hold yet and that no known fake form covers (`Synthesizer.reserve`), so a fake
  drawn earlier that equals a real value seen later is re-drawn and the real value is masked; a candidate inside a
  known fake form (a pseudonymised answer masked again, "Bosredon" inside "M. Bosredon") is not reserved, so the
  answer stays idempotent. `_synthetic_values` reads `Synthesizer.values()` (collision-checked) instead of the raw
  store rows; a Synthesizer failure gives no known fake surface (fail closed). `Service._register_pass(d)`: a
  dossier in synthetic mode registers every readable document in codes mode before a single fake is drawn
  (`_scan`, PLAN 5.1); the PrivacyBench runner does the same in its `--synthetic` run (pass 1 in codes mode).
  v0.3.1 changes the lookup: known fake surfaces count only in a model answer masked again, never in a source
  document (section 13.1).
- Span policy "cover": `_detect` stores the company core (`org_form_parts`) for a rule span; `_apply` writes
  `lead + code + tail` (codes) or `lead + pseudonym + tail` (synthetic). Default unchanged (`"clear"`).
- `pyproject.toml` gains `pdfplumber>=0.11` (NOTICE: pdfplumber and pdfminer.six, MIT).
- PrivacyBench runner (`evaluation/public/privacybench/run_shield.py`): PDF text through `documents.pdf_page_lines`
  / `pdf_word_separator`; the export's directory built as `Service._build_directory` does and given to the masker
  (`RAGBASE_SHIELD_PB_DIRECTORY=0` turns it off); the PERSON split reads `Masker.person_roles` through the mention's
  code (`name_roles(store, masker)`, `split_person(text, start, roles, code)`); `--synthetic` registers first.
  MAPA runner `run_shield.py`: the recorder passes `mint_into=` on and reads `entry.masked0`, but it is still not
  whole on the v0.2+ service: it fails 2 of its own checks on 19 of 19 decisions (known limit of this runner).
- Gates on the final build (2026-10-21, rules mode): full suite green (`tests/test_v03_integration.py` added, 19
  tests, invented data); `bench/run_bench.py` PASS; `ragbase-shield verify` CLEAN (47 paths, temp home);
  the Max-corpus audit `audit_fix.py --diff 693573f` (internal) was reported as 0 findings over 7,966 added lines, but that ran on an earlier state
  of the diff: on the commit it gives 1 finding (corrected in v0.3.1, section 13.3). Benchmark runs: PrivacyBench
  v2.5 recall up from v0.2; the French rules-mode masks (FR-PII-Bench, Judilibre, MAPA) unchanged. The internal result
  files are not published; the public head-to-head is `evaluation/laptop/RESULTS_PUBLIC.md`.

## 13. v0.3.1 contract changes: synthetic leak fix, NER merge guard, clean-room audit (2026-10-23)

Sources: the findings of the v0.3 PrivacyBench run (internal, not published). Codes mode does not
change: the rules-mode masks of PrivacyBench, FR-PII-Bench, Judilibre, MAPA and holdout-en are identical to v0.3.

### 13.1 SYNTH (`engine/synthetic.py`, `engine/masker.py`)

- Cause A, nicknames written unchanged. The renderer reads the same nickname sources as the masker's resolution: the
  French and English tables, the prefix forms, the nicknames written in quotes inside the value, and the dossier
  directory. `Synthesizer.use_nicknames(source)` plugs the directory in (`source`: `value -> iterable of words`;
  attribute `Synthesizer.nickname_source`, None = the tables only); the masker calls it. A nickname of a word of
  the real value becomes the fake word in its place; a nickname the dossier declares becomes the fake's first given
  name. A mention word that maps to nothing becomes the fake's first given name when the masker linked the mention
  as a given-name form; any other unmapped word fails closed (the code is written). A fake never uses a nickname of
  a real given name.
- Leak guards: `Synthesizer._leaks` and `masker._synthetic_leaks(ent, rep, surface="")` (new optional third
  argument; a two-argument call keeps the v0.3 rule) flag any word of the mention written unchanged that is not a
  fixed word, whatever its length. Helpers: `synthetic.mention_word_fixed(kind, run, surface="", start=-1, value="")`
  (a title, particle, generational word, legal form, generic company word or the "s" of a possessive) and
  `synthetic.unchanged_mention_word(kind, surface, rep, value="")` (a one-letter initial is compared at its own
  place). Integrator additions after the leak check: a particle word that ends a name (no word of two or more letters
  after it, `synthetic._trailing_particle`) is never a fixed word and never kept in a fake (a nickname that is also a
  particle word); a run of two or more digits of a real person or company name written again is a leak (a company
  fake keeps the numbers of the real name, so these names fail closed). Tests: `tests/test_v031_synthetic.py`,
  `tests/test_v031_residuals.py`.
- Cause B, short fake forms hid real values. In `_apply`, known fake surfaces count only in a model answer masked
  again: a call with `keep_known_codes=True`, or a text that writes a whole fake value (a person or company of two or
  more distinctive words, or an e-mail or web address on the `.example` domain). In any other text no hit is used:
  every candidate the store does not hold yet is reserved and a fake that collides with it is re-drawn at once. The
  lookup still runs once per text, only to decide whether it is an answer; the restore path is unchanged. Defence in
  depth: `_synthetic_hits(text, values=None, *, masking=False)`; with `masking=True` a one-letter or initial-only fake
  form (initials, an acronym) is never a hit; a hit never removes a real candidate longer than itself, nor a form of
  a real value that the dictionary found at that place.
- Fake initials: a fake holds a one-letter initial only where the real value has one; that letter is never a
  one-letter word of a real value or of a reserved surface of the dossier, and it avoids the other fakes' initials
  while a free letter is left; otherwise the code is written. A capitalised particle that opens a name ("Al ...") is
  a given name and is replaced; a capital "D" or "Y" with no apostrophe after it is an initial.
- Decision (integrator): a call without `keep_known_codes=True` that writes no whole fake value is a source document.
  `protect()` passes the flag; `mask_text` (Desk and CLI) does not. So an answer pasted there that uses only a fake
  first name is masked as new real text: a new entity, and the earlier fake that collides with it is re-drawn (that
  name in the old answer no longer restores). This is the privacy-safe direction (a fake form can never hide a real
  value); a Desk action "mask a model answer again" should pass the flag (open item).
- Vaults: a fake drawn by v0.3 that breaks a v0.3.1 rule (a nickname, initial or trailing-particle collision) is
  re-drawn the next time it is used; model answers that use the old fake then no longer restore that name.

### 13.2 NER merge guard (`engine/merge.py`)

- `_name_signals` returns no signal when the model span has no letter word. v0.3 read `words[0]` of an empty list
  (`IndexError` at `merge.py:988`); the masker then dropped every model candidate of the unit ("NER merge failed;
  rules only", 22 units of the PrivacyBench NER run). Tests: `tests/test_v031_merge.py`.

### 13.3 Clean-room audit (`evaluation/audit/`, owner: integrator)

- `evaluation/audit/audit_bench.py --tree | --diff <base>`: the gold of every benchmark held locally (PrivacyBench
  spans, characters and human files, FR-PII-Bench, MAPA, REDACT, the Max corpus, the gap snippets) against `src/`,
  `tests/`, `docs/`, `integrations/`, `ARCHITECTURE.md`, `README*.md` and `CHANGELOG.md`. Words and phrases at word
  boundaries (4+ characters, folded), each word of a full person name alone, identifiers on their letter-and-digit
  core (masked tails too). A finding prints `path:line`, the benchmark, the label, a masked form and a hash, never the
  value; exit 1 on a finding, 2 on a setup error. `--quotes` adds a review list of Judilibre 5-word runs (never
  fails). `evaluation/audit/allow.txt`: 1,082 entries, each with a reason, under 6 rules (rule 6, common given
  names of the first-name lexicon checked by hand, added by the integrator for 66 names of the v0.2 and S5 sections).
- Every benchmark value in tests, docstrings, comments, docs and the fake surname lists (`synthetic_last_en.txt`,
  `synthetic_last_fr.txt`) was replaced with an invented value of the same shape.
- `evaluation/holdout-en/check_separation.py`: the dictionary words (Webster's 2nd, `/usr/share/dict/words`) of the
  English industry head list `names._EN_HEAD_EXTRA` count as generic words; an invented word in that list stays
  reported.

### 13.4 Version and gates

- `ragbase_shield.__version__` and `pyproject.toml` read 0.3.1; the four integration manifests follow (a test checks
  them).
- Gates on the final build (2026-10-23): 1,666 tests passed (`tests/test_v031_*.py` added, 27 tests, invented
  data); `bench/run_bench.py` PASS; `ragbase-shield verify` CLEAN (47 paths, temp home); `audit_fix.py --diff
  693573f` 0 findings; `evaluation/audit/audit_bench.py --tree` 0 findings; `check_separation.py --since 693573f
  --strict` exit 0. PrivacyBench v2.5: rules codes predictions byte-identical to v0.3, 0 NER merge failures, no
  synthetic leak against the gold in either mode. FR-PII-Bench, Judilibre, MAPA and holdout-en rules masks identical
  to v0.3.

## 14. v0.4 contract changes: the PrivacyBench ladder v0.4 (plan of 2026-10-22; build 2026-10-24 to 2026-11-07)

Steps S0, T1 to T5, T8, T9, P1 and W0, each built, measured on the whole benchmark harness (on a cloud machine from
2026-11-03) and accepted by a separate checker with its own scorer under the gates of the plan; T6, T7 and T6T7 were
rejected (a per-set recall loss above the limit, or a gain under the gate). The step reports and the internal result
files are not published; the public head-to-head is `evaluation/laptop/RESULTS_PUBLIC.md`.
Rules that bind every step: a general mechanism only (a shape, a label word, a layout, a caller flag; never a benchmark
string, a per-set or a per-value rule); invented test data; every new rule gated on `lang == "en"`, so the French
masks of FR-PII-Bench, Judilibre and MAPA stay byte-identical; rules mode stays the product default. The last accepted
commit is `321e05f`; its version string reads 0.3.1, and 0.4.0 is set in the version commit that follows with no
engine change.

### 14.1 S0 (`engine/synthetic.py`, `evaluation/audit/audit_bench.py`)

- Three more synthetic leak classes closed (C, D, K of the v0.3.1 checker); codes-mode masks byte-identical to v0.3.1;
  synthetic recall within 0.1 point of codes mode.
- The clean-room audit reads every line also as camelCase words, with escapes, entities and percent escapes decoded,
  base64 and hex decoded, Cyrillic and Greek look-alikes as Latin, string literals joined; it matches MD5, SHA-1 and
  SHA-256 of every gold value; the scope is the whole repository except the `evaluation/` subfolders and ignored
  files; with `--diff`, an allow entry added since the base that clears a value in the scanned lines is a finding
  (`--accept-allow` is the reviewer's acceptance).

### 14.2 T1 (benchmark runner only: `evaluation/public/privacybench/run_shield.py`, `recheck_v02.py`)

- No file under `src/` changed. The runner reports a PDF span as merged per-line `boxes` (`pdf_line_boxes`; the glyph
  list moves to `glyphs`), a NAME_GIVEN or NAME_FAMILY span of several words as one span per word (`native_report`),
  and a LOCATION_ADDRESS that ends with a town, state or region and postcode as a street-level span plus a locality
  span (`street_split`). `recheck_v02.py` scores boxes with the card's box rule. The human files keep their report.
  The holdout scorer reads the same functions, so on holdout-en the locality spans count as false positives under
  its street-line key (a format effect, not a masking change).

### 14.3 T2 (`engine/masker.py`, `engine/locale.py`, `engine/synthetic.py`)

- Chat names: a lower-case directory first name or nickname in chat text with no person cue is the person when it is
  a three-letter form that is no common word, or a common word that the words around it do not read as a function
  word, a noun or a verb (`Masker._chat_form_ok`; refused after a determiner, possessive, modal, auxiliary or subject
  pronoun, before a bare verb, as an object at a clause start, before a place name). A chat abbreviation
  (`_CHAT_WORDS`, a generic list) is never a name; a word the export shows as a company is never a lower-case name
  without a cue.
- Quoted nicknames: a single quote or bracket around one nickname is a delimiter inside a name
  (`locale._nickname_open`); a person span never cuts through a pair of quotes or brackets (`locale._quote_trim`).
- Slots: a capitalised directory form in a greeting or sign-off slot is the person, also when it is a common word
  (`Masker._name_slot`); slot-only forms (two-letter names, standard diminutives, three-letter short forms) are
  accepted only in those slots, yield to any other person's first-name form, and never match in French text.

### 14.4 T3 (`engine/masker.py`, `engine/directory.py`, `engine/locale.py`, `engine/names.py`, `vault.py`)

- Firm names: a capitalised name, a connector ("&", "and") and a firm word ("Co.", "Company") are one company name in
  the English rules; the span covers the connector and the firm word; the company core drops the connector
  (`names.org_core`).
- Company mailbox: the directory makes no person from an address whose local part spells the label of its own domain
  when the dossier holds at least two other addresses at that domain; the display name is a company name; new field
  `Directory.orgs` (in `to_dict` only when not empty); `Directory.seed` masks the first mention.
- A one-word company label that is also a person's name (the e-mail domain label of 3 or more addresses) is decided
  per mention by local cues (`Masker._label_cue_en`, `_label_mentions_en`), then by the export's own usage (company
  cues at least 3 times and twice as often as person cues; evidence fields `label_org`, `label_person` in
  `vault._EVIDENCE_FIELDS`).
- Fail closed: in English a two-word person span the export shows as a company becomes the company (v0.3 dropped it
  and the name could stay in clear); a bare first name keeps its person reading when its person evidence is stronger.

### 14.5 T4 (`engine/names.py` `domain_form_spans`, `engine/masker.py`)

- A run of two to four capitalised words whose letters, joined, spell an e-mail domain label of the text or the
  dossier is that company (rule `domain_form`, priority 5, in `STRONG_ORG_RULES`); also "X Company" with the short
  legal form in the label, capitals joined by "&" that spell a two- to four-letter label (never a business
  abbreviation of the generic stop list), one camel-case word, and in chat-like text (`locale.casual_text`) the label
  or its run in lower case (no dictionary word, no first name, 4 or more letters; outside chat only with a legal form
  after it). Guards: never inside an address, host, path, handle, file name or protected term, never after a person
  title, never across a rule span; a form that names a dossier person stays a person (`Masker._dir_person_surface`).
- A known e-mail address or host written as prose words is dropped (`masker._written_as_words`) so the company rules
  read the company. A partial variant made of English place names only is the place; a company seen only in lower
  case gets no common-word partial variant; such variants give no initials.

### 14.6 T5 (`engine/masker.py`, `engine/locale.py`)

- Dossier knowledge: the masker reads each distinct English formal text once and counts how it writes each word in
  mid-sentence (lower case = a common word), the acronyms it declares in brackets, and which rule found each name
  (`_t5_note`, `_t5_rules`, `_t5_mid`, `_t5_declared`; in memory only; a new session knows nothing and keeps more
  masks).
- A common word is a word of the English vocabulary that is not a surname-like word, or a word the dossier writes in
  lower case in mid-sentence 3 times or more and in 10 % or more of its uses; never a lexicon first name or nickname,
  a directory name or an e-mail domain label (`_t5_common`).
- Refusals (`_t5_refuted_impl`, `_t5_drop_reason`): a "First Noun" person found only by the first-name rules whose
  last word is a common word or holds a digit (with company evidence it is the company); a legal form in capitals
  glued to a code, after a place, or in a list of capital codes (`locale._Rules.form_misread`, `org_back`, the USPS
  state codes); a company found only before such a form that a lower-case word follows and whose words are all
  common words; a one-word company found only by a trigger word or a possessive whose word is a common word or a
  place; a lower-case one-word mention that is a common word (the T2 chat forms and the T4 domain companies are
  exempt); an acronym variant of a company unless declared in brackets or an e-mail domain label; a one- or two-word
  place name as a name (directory words, cues, strong sightings, acronyms and titles exempt). The canary (`scan`) is
  unchanged.

### 14.7 T8 (`documents.py`, `engine/detectors_ids.py`, `engine/masker.py`, `engine/locale.py`)

- PDF ruled tables: `pdf_table_rows` reads a page's tables (pdfplumber `find_tables`) one row per line, cell by cell;
  a word belongs to the cell that holds its centre; a cell wrapped over 2 or 3 lines is one cell; the first word of a
  cell carries the cell separator, which starts a cell as a line break starts a line (`_SENT_END_RE`); a table-finder
  error reads the page line by line; `RAGBASE_SHIELD_PDF_TABLES=0` = the v0.3 reading.
- `.xlsx` reader (`SUPPORTED_EXTENSIONS`, `_read_xlsx`): standard library only; one line per row, cells joined by the
  cell separator, the sheet title first; shared and inline strings, cached formula results, numbers as written,
  booleans; a broken file fails closed (`xlsx_unreadable`), a sheetless file warns. `.pptx` is now the unsupported
  kind in the tests.
- Identifiers (English only): `find_grouped_ids`, a value whose prefix is 2 or 3 letter groups then digits under a
  label noun (`labelled_id`), in an id column (`table_id`), a cell that lists several ids read whole, and the same
  layout elsewhere in the text (`layout_id`); `find_member_ids`, a bare workspace member id shape and a profile
  handle after a profile label are usernames.
- Chat flag: `Masker.mask(chat=...)` and `Masker.scan(chat=...)` (True = chat text, False = document, None = the
  text's own shape); the runners pass True for Slack units and channel messages. A pronoun contracted with an
  auxiliary before a lower-case common-word first name reads it as a verb or a noun (`_EN_AUX_BEFORE_RE`).

### 14.8 T9 (`engine/masker.py`; English texts, NER mode only)

- Every model find is recorded per value with the evidence it carries (merge signals `rule`, `cue`, `domain`; an
  owner word before a login, account or staff number); store entities that a model find alone created are recorded
  by code (`_t9_gate`). A value is supported when a sighting had evidence, a rule reading exists that T5 does not
  refute, a store entity holds it that no model find alone created, or the word is a name of the dossier
  (`_t9_supported`).
- Refused when unsupported (`_t9_refuted`): a one-word company that is a common word (OM10); a one-word person that is
  a common word and no first name or nickname (G4); a login, account or staff number that is a reference code
  (capital-letter groups joined by a hyphen) with no owner word, or such a code read as a company or a person (G3).
  The dictionary mentions of a model-only name follow the same rules (`_t9_drop_reason`, `_t9_model_owner`). Any
  exception keeps the find or the mention masked (fail closed); rules, user and directory entities are never touched.

### 14.9 P1 (`engine/lexicon/en_whitelist.txt`, `engine/locale.py`, `engine/masker.py`, `config.py`, `service.py`)

- The vendor group of `en_whitelist.txt` has its own `# [vendors]` section; `Bundle.vendor_phrases` (empty for
  French); `whitelist_phrases` = whitelist + vendors (the protection tuple is unchanged).
- Setting `RAGBASE_SHIELD_OWN_COMPANY_VENDOR` (default off): `locale.own_company_vendor_setting()`,
  `config.own_company_vendor()`, `Masker(own_company_vendor: Optional[bool] = None)` (None = the setting, read at
  each call), `service.status()` field `own_company_vendor`. With the option on, the directory label with the
  highest address count (alone at the top; a tie = none) that is a vendor phrase is released from the protected
  intervals of every English text (`protected_intervals_en(..., release=())`, `Masker._main_domain_label`,
  `_vendor_release`), so the e-mail domain rule masks that one company in that dossier; every other vendor stays
  readable. The French path has no release. Measured: option OFF byte-identical to T9. The policy decision is
  open; the option ships OFF.

### 14.10 W0 (`hooks.py`, `vault.py`, `service.py`, `desk/service_manager.py`, tests, packaging tests)

- Hooks: a command is read in sh, cmd.exe and PowerShell syntax; an option value (`--x=./y`, `--x=/y`, `/x:<v>`) is
  checked against the dossiers when it names a place and is never counted as the path argument, so the
  current-folder check of a recursive or listing command still runs; `cd /d` is cmd syntax only, cmd `cd` without
  `/d` keeps the drive and takes the rest of the line; the folder list of a shell is never cut (past 16 folders the
  command is denied with the new code `SHELL`); PowerShell braces inside a word stay literal, a script block `{` is
  checked like a glob of the folder, `foreach ($x in <command>)` reads the command; cmd switch values (`/g:<file>`)
  are checked; nested shells, Windows readings and file URIs. Every command v0.3.1 denies is still denied
  (differential probe, 985 invented rows, 0 regressions, 59 new denials).
- Vault file handle on Windows; `service.reset` closes the hook registries; `plist_dict` renders POSIX paths; test
  isolation with `USERPROFILE`. Full suite on Windows: 2,034 passed, 0 failed, 26 platform skips; PrivacyBench and
  FR-PII-Bench rules outputs byte-identical to the Linux run. Known limit: a bare `C:\x\y` in a Git Bash command loses its
  backslashes in the POSIX reading and is denied above a dossier (fail closed; write `C:/x/y` or quote).

### 14.11 Version and gates

- `ragbase_shield.__version__` and `pyproject.toml` read 0.4.0 from the version commit on; the four integration
  manifests follow (a test checks them). The measured commit `321e05f` reports 0.3.1 in every run folder.
- Gates on `321e05f` (2026-11-06 and 2026-11-07, on a Linux cloud machine): 2,055 tests passed on Linux (4 skipped,
  1 deselected), 2,034 on Windows; the Max-corpus audit `audit_fix.py --diff 693573f` (internal) 0 findings; `audit_bench.py --diff HEAD` 0;
  `check_separation.py --since 693573f --strict` exit 0; `audit_bench.py --tree` 1 finding in
  `packaging/windows/sign_TODO.ps1` (open, not a detection file). PrivacyBench v2.5: no synthetic leak against the gold
  in either mode; FR-PII-Bench, Judilibre and MAPA masks identical to v0.3.1 in both modes. Public results:
  `evaluation/laptop/RESULTS_PUBLIC.md`.
