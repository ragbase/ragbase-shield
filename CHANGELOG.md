# Changelog

All notable changes to RAGbase Shield are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-11-12

PrivacyBench ladder v0.4 (contracts: ARCHITECTURE.md section 14). Every mechanism is general and runs on English text only;
the French masks of FR-PII-Bench, Judilibre and MAPA are identical to 0.3.1, span for span, in both modes. Rules mode
stays the product default. Measured on commit `321e05f` (the last ladder step), whose version string still reads
0.3.1; 0.4.0 changes no engine code.

### Added

- **T1, report adapter (benchmark runner only, no engine change):** `evaluation/public/privacybench/run_shield.py`
  reports a PDF span as per-line boxes, a multi-word name as one span per word, and a postal address as a
  street-level span plus a locality span, the answer key's own format; `recheck_v02.py` scores boxes.
- **T2, chat names and slots** (`engine/masker.py`, `engine/locale.py`): a lower-case directory first name or nickname
  in chat text is the person unless the words around it read it as a function word, a noun or a verb; a quoted or
  bracketed nickname inside a name stays one name and is never cut in half; a capitalised directory form in a
  greeting or sign-off slot is the person, also when it is a common word; slot-only short forms.
- **T3, company evidence beats a person reading** (`engine/masker.py`, `engine/directory.py`, `engine/locale.py`,
  `engine/names.py`, `vault.py`): firm forms with a connector and a firm word; a shared company mailbox makes no
  person; a one-word company label that is also a person's name is decided per mention by local cues, then by the
  export's own usage (evidence fields `label_org`, `label_person`); a span the export shows as a company becomes the
  company instead of staying in clear.
- **T4, company names written as e-mail domain forms** (`engine/names.py` `domain_form_spans`, masker): a run of
  capitalised words, an "X Company" form, ampersand initials, a camel-case word or, in chat, a lower-case run whose
  letters spell an e-mail domain label of the text or the dossier is that company; a known address or host written
  as words is dropped so the company rules read the company; guards for addresses, hosts, handles, titles, protected
  terms and dossier persons.
- **T5, precision core of the English rules** (masker, locale): the masker reads each English text once and learns
  which words it writes in lower case (common words) and which acronyms it declares; a "First Noun" person whose
  last word is a common word is not a person; a legal form in capitals glued to a code, after a place or in a code
  list is not a legal form; a one-word company that is a common word or a place, found only by a trigger word, is
  not a company; a lower-case common word is not masked; an acronym variant is masked only when declared or an
  e-mail domain label; a one- or two-word place name is not a name.
- **T8, small id rules, PDF wrapped cells, xlsx reader, chat flag** (`documents.py`, `engine/detectors_ids.py`,
  masker, locale): the rows of a ruled PDF table are read cell by cell, a cell wrapped over several lines as one
  cell (`RAGBASE_SHIELD_PDF_TABLES=0` restores the 0.3 reading); a standard-library `.xlsx` reader (one line per
  row, fails closed on a broken file); grouped-prefix identifiers under a label noun or in an id column, and the
  same layout elsewhere in the text; workspace member ids and profile handles as usernames; `Masker.mask(chat=...)`
  and `scan(chat=...)` let the caller say that a text is chat; a contracted auxiliary before a lower-case first name
  reads it as a verb or a noun.
- **T9, NER-mode gate on model-only finds** (masker, English texts, NER mode only): every model find is recorded with
  its evidence (a rule, a cue, an e-mail domain, an owner word); a one-word company or person that is a common word,
  or a reference-code identifier with no owner word, is not masked when nothing in the dossier supports it; the
  dictionary mentions of a model-only name follow the same rule; any exception keeps the find (fail closed).
- **P1, own-company vendor option, OFF by default** (`RAGBASE_SHIELD_OWN_COMPANY_VENDOR`,
  `config.own_company_vendor()`, `Masker(own_company_vendor=...)`, a `service.status()` field): with the option on,
  the one vendor of the "never masked" list that is the dossier's main e-mail domain label is masked like any company
  of that dossier; the `en_whitelist.txt` vendor group gets its own `# [vendors]` section. Default behaviour
  unchanged.
- **W0, Windows compatibility** (`hooks.py`, `vault.py`, `service.py`, `desk/service_manager.py`, tests): the Claude
  Code hooks read Git Bash, cmd.exe and PowerShell commands (an option value is checked but never counted as the path
  argument; `cd /d` in cmd syntax only; the folder list of a shell is never cut, a too complex command is denied with
  the code `SHELL`; PowerShell braces and `foreach` read); vault file handle on Windows; `service.reset` closes the
  hook registries; test isolation on Windows. Every command 0.3.1 denies is still denied (985-row probe, 0
  regressions).
- **S0, synthetic mode and clean-room audit:** three more synthetic leak classes closed (C, D, K) with codes-mode
  masks byte-identical to 0.3.1; `evaluation/audit/audit_bench.py` reads camelCase, escapes, entities, base64 and
  hex, hashes, look-alike letters and joined string literals over the whole repository, and flags a laundered allow
  entry.
- **Installers (unsigned):** a macOS `.pkg` and a Windows `.msi` that install a private Python runtime with Shield in
  the user's own folder and run Shield Desk as a background service (`packaging/`, build and test steps in
  `packaging/README.md`). They are not signed yet: signing and notarisation are to do
  (`packaging/macos/TODO_SIGNING.md`, `packaging/windows/TODO_SIGNING.md`).
- Tests: `tests/test_v04_s0.py`, `test_v04_t1.py` to `test_v04_t5.py`, `test_v04_t8.py`, `test_v04_t9.py`,
  `test_v04_p1.py`, `test_v04_w0.py` (invented data only); 2,055 tests pass on Linux, 2,034 on Windows.

### Changed

- Version 0.4.0 (`pyproject.toml`, `ragbase_shield.__version__`, the four integration manifests).
- `evaluation/holdout-en/run_holdout.py` and the PrivacyBench runner pass the chat flag for Slack units and channel
  messages.

### Results (public head-to-head of 11 November 2026, protocol addendum 4)

- Shield 0.4.0 was built after the first results of this comparison were known. No data set is held-out for
  Shield 0.4.0. Hexagone 0.3.9 and Presidio 2.2.364 were measured in October 2026 and were not run again.
- By the rule fixed in advance (protocol section 11.3; addendum 4, section 20.9): for Shield 0.4.0 rules (the
  product default) and for Shield 0.4.0 rules + GLiNER, the conditions are not met against Hexagone Fast and against
  Hexagone Precis. Hexagone leaves less personal data readable on some sets; Shield changes fewer legal terms on
  every set that has them.
- Rules mode: the output text is identical to 0.3.1 on four of the six sets; Shield 0.4.0 now reads an Excel
  workbook of the Max set that 0.3.1 could not read (a fault that this study found).
- Rules + GLiNER, English (development set): Shield 0.4.0 leaves more organisation names readable than 0.3.1, a
  clear difference against 0.4.0.
- Every number, with its set, its mode and its status: `evaluation/laptop/RESULTS_PUBLIC.md`.
- Checks on commit `321e05f`: `evaluation/audit/audit_bench.py --diff HEAD` 0 findings,
  `check_separation.py --since 693573f --strict` exit 0; `audit_bench.py --tree` 1 finding in
  `packaging/windows/sign_TODO.ps1` (a PowerShell built-in read as a short nickname, not a detection file);
  `ragbase-shield verify` CLEAN (47 paths) on Windows.

## [0.3.1] - unreleased

Synthetic-mode leak fix, NER merge guard and a clean-room audit (contracts: ARCHITECTURE.md section 13). Rules mode stays the product default. Codes mode does not change:
the rules-mode masks of PrivacyBench, FR-PII-Bench, Judilibre, MAPA and holdout-en are identical to 0.3.0.

### Fixed

- **Synthetic mode, nicknames written unchanged** (cause A of 0.3.0): the renderer reads the same nickname sources
  as the masker (French and English tables, prefix forms, nicknames in quotes inside the value, the dossier
  directory through `Synthesizer.use_nicknames`). A nickname becomes the fake word in its place or the fake's first
  given name; a word that maps to nothing fails closed (the code is written). The leak guards flag any mention word
  written unchanged that is not a fixed word (`synthetic.mention_word_fixed`, `synthetic.unchanged_mention_word`,
  `masker._synthetic_leaks(ent, rep, surface="")`). A fake never uses a nickname of a real given name.
- **Synthetic mode, short fake forms hid real values** (cause B of 0.3.0): known fake surfaces count only in a model
  answer masked again (`keep_known_codes=True`, or a text that writes a whole fake value), never in a source document.
  A one-letter or initial-only fake form is never a hit, a hit never removes a longer real candidate, and a fake
  initial never equals a one-letter word of a real value.
- **Synthetic mode, two residual classes found by the 0.3.1 leak check:** a particle word that ends a name (a
  nickname such as "Del") is never kept in a fake or written back; a number of two or more digits of a real person or
  company name is never written again (that name fails closed to its code).
- **NER merge crash:** `merge._name_signals` returns no signal for a model span with no letter word. 0.3.0 dropped
  every model candidate of 22 PrivacyBench units on an `IndexError`.

### Changed

- **Clean room:** every benchmark value in tests, docstrings, comments, docs and the fake surname lists
  (`synthetic_last_en.txt`, `synthetic_last_fr.txt`) is replaced with an invented value of the same shape.
- New `evaluation/audit/audit_bench.py`: the gold of every benchmark held locally against `src/`, `tests/`, `docs/`,
  `integrations/` and the top-level docs; masked output only; exit 1 on a finding. `evaluation/audit/allow.txt`:
  1,082 entries, each with a reason. `evaluation/holdout-en/check_separation.py`: the dictionary words
  of the English industry head list count as generic words.
- Version 0.3.1 (`pyproject.toml`, `ragbase_shield.__version__`, the four integration manifests).

## [0.3.0] - unreleased

PrivacyBench ladder S1 to S7 (contracts: ARCHITECTURE.md section 12). General
mechanisms only; rules mode stays the product default. Correction (0.3.1): this version still held PrivacyBench
values in tests, docstrings and comments (no detection used them); 0.3.1 replaced them.

### Added

- **Dossier directory** (`engine/directory.py`): the people and organisation labels of a dossier from the e-mail
  headers, the Slack `users.json`, the Word authors, the signature blocks and the declared nicknames; every full
  name is in the store before the first mask; `Masker(directory=...)`, `Masker.person_roles()`, `Masker.name_roles()`;
  vault tables `evidence` and `directory` (encrypted, additive); `Service._build_directory` in every scan.
- **Export evidence and kind decisions** (`engine/masker.py`): what the dossier showed each surface to be decides a
  disputed mention (a bare first name with company evidence is the company; rules keep their kind; "Last, First"
  keys to one entity; login names and identifiers match in their slot only; "First Last of Company" keeps the
  person and the company apart).
- **Span refinement** (`engine/names.py`, `detect_names(text, lang, protected, domains)` for both languages): the
  legal-form span policy (`RAGBASE_SHIELD_LEGAL_FORM_SPAN=cover`, default `clear`), company span edges, companies
  named by an e-mail domain of the text or of the dossier, declared acronyms and aliases, same-surface propagation,
  token roles with quoted nicknames.
- **PDF table cells** (`documents.pdf_page_lines`, `pdf_word_separator`): a wide gap between two words of one line
  is a cell boundary; `pdfplumber` (MIT) joins the dependencies, pypdf stays the fallback.
- **Identifier cue rules** (`engine/detectors_ids.py`): labelled account and staff identifiers, in-text id layouts,
  pipe-table columns, English street-level address edges.
- **Gated NER layer** (`engine/merge.py`, `engine/ner.py`, masker): a model find may add people, organisations,
  addresses and the identifier kinds only; named assets and government ids go to `MaskResult.watch` for a review
  step; every find carries its second signals; a find without a signal is masked where the model finds it and gets
  no partial or lower-case variant; a confirmed find is a detected entity (store `confirm(code)`). Per-label score
  floors; `RAGBASE_SHIELD_NER_DEVICE`; GPU out-of-memory fallback to the CPU.
- **Synthetic mode leak fix** (`engine/synthetic.py`, masker, service): a collision index over the whole store,
  re-draw of a fake that collides with a value registered later, reserved surfaces, fail-closed `SyntheticCollision`
  / `SyntheticLeak`; the masker reserves the new surfaces of a text before it looks for known fake surfaces, so a
  real name equal to an earlier fake is masked; a synthetic dossier registers every document in codes mode before
  the first draw (`Service._register_pass`).
- **English holdout corpus** (`evaluation/holdout-en/`, 10 invented exports with ground truth) and its runner,
  scorer and separation check.
- `MaskResult.watch` (additive), `EntityStore` optional `confirm(code)`, `evidence()`, `add_evidence()`,
  `directory()`, `set_directory()`.

### Changed

- `evaluation/public/privacybench/run_shield.py`: PDF text through the product reader, the export's directory,
  the PERSON split from the engine's token roles, `--synthetic` registers in codes mode first. The older MAPA runner
  `run_shield.py` passes `mint_into=` on, but it is still not repaired: it fails 2 of its own checks on 19 of 19
  decisions.

## [0.2.0] - unreleased

v0.2 detection stack (contracts: ARCHITECTURE.md section 11).

### Added

- **Optional NER layer** (`engine/ner.py`, `engine/merge.py`): GLiNER2 `fastino/gliner2-privacy-filter-PII-multi`
  (default) and GLiNER `urchade/gliner_multi_pii-v1`, both Apache-2.0, downloaded once with
  `ragbase-shield ner download` and run offline (`HF_HUB_OFFLINE=1`). Install with `pip install "ragbase-shield[ner]"`.
  The model's spans go through the whitelist, the protected intervals, "rules win on kind" and ten precision guards
  before they become candidates; a one-word find of the model alone is contained (no partial or lower-case variant)
  until a fuller sighting confirms it. `ragbase-shield ner status`, `doctor` and `shield_status` report the packages,
  the cached models and the backend. Never used by the hooks, the canary or the label pass.
- **English locale** (`engine/locale.py`, `engine/lexicon/en_*.txt`): language detection per text
  (`RAGBASE_SHIELD_LANGUAGE=auto|fr|en`, per-dossier `set DOSSIER_n --language`), English name and company rules
  (titles, "First Last", greetings and sign-offs, speaker labels, suffix words, "X & Y", trigger words), English
  protected intervals (courts, public bodies, acts, sections), US and UK phones, SSN, ITIN, NINO, US and UK
  addresses, English month names in birth dates. The French stop list is never applied to an English text.
- **New kinds** `USERNAME` (PSEUDO/USERNAME), `EMPLOYEE_ID` (MATRICULE/EMPLOYEEID), `ACCOUNT_NUMBER`
  (COMPTE/ACCOUNT): Slack mentions and @handles, labelled identifiers in both languages (same line, previous line,
  table column), US routing numbers, id layouts learnt per dossier (`EMP-ddddd`), judges in a comma list after a
  plural title, civility for shared surnames, "casual" lower-case first names in chat text.
- **Synthetic replacement mode** (`engine/synthetic.py`): realistic, deterministic pseudonyms per dossier instead
  of codes (`mask --mode synthetic`, `set DOSSIER_n --replacement synthetic`, Desk `replacement`), reversible through
  the vault (schema 2, export version 2), fiction phone ranges, `.example` domains, valid check digits, dates
  shifted in the same written form. Pseudonymisation, not anonymisation.
- `MaskResult.language`, `MaskResult.ner`, `MaskResult.mode`, `MaskResult.codes`, `MaskResult.replacements`;
  `Entity.source` ("detected", "user", "ner"); `service.status()` fields `language`, `ner`, `replacement`.
- Evaluation runners take `--ner off|auto` and `--language`.

### Changed

- `Masker(store, *, locale, language="auto", use_ner, ner, ner_model="auto", replacement="codes")`;
  `Masker.mode` names the backend (`rules+ner:gliner2:fastino`). `ner_installed()` / `ner_available()` take a model
  argument and cover the GLiNER backends (spaCy stays the `spacy` backend).
- The company trigger rule starts the name after a spelled-out legal form ("société d'économie mixte X",
  "association syndicale libre X").

## [0.1.0] - unreleased

First version. Local, reversible pseudonymisation for Claude, ChatGPT and Copilot.

### Added

- **Engine.** Rules and dictionaries for French legal text, with no model download by default.
  - Structured identifiers with check digits: SIREN, SIRET, NIR, IBAN, French VAT, payment cards.
    A number with a wrong check digit is flagged for review. It is still masked when its shape is clear: an IBAN
    of the exact national length, or a SIREN or SIRET with a company label next to it.
  - Emails, French phone numbers, French postal addresses, birth dates, URLs, other identifiers
    (ISIN, LEI, passport, licence plate, IP address).
  - Case references: RG numbers, Cour de cassation pourvoi numbers, Portalis numbers, ECLI.
  - Persons (titles M., Mme, Me, Maître, and a first-name list) and companies (legal forms such as SAS, SARL,
    SELARL, Ltd, GmbH; "X c. Y" dossier titles). Name variants link to one code.
  - Whitelist: courts, institutions, laws, codes, articles, legal terms, months and days stay readable.
  - Optional NER when `spacy` and a French model are installed. NER never overrides structured detectors.
  - Codes allocated sequentially per dossier (PERSONNE_A, SOCIETE_A, IBAN_1), never derived from a hash.
    French labels by default, English labels with `RAGBASE_SHIELD_LOCALE=en`.
- **Vault.** One encrypted store per dossier (SQLite + Fernet). Key in the OS keychain, with a 0600 key file
  fallback. Dossier titles and folder paths encrypted. Per-dossier "keep clear" and custom terms.
  Encrypted export and import for a colleague.
- **Documents.** Read PDF (text layer), DOCX (body, tables, headers, footers, footnotes), TXT, MD, EML, HTML.
  Write restored DOCX and MD into `<dossier>/Shield - sorties`. Scanned PDFs are reported, not read.
- **MCP server** (stdio): `shield_list_dossiers`, `shield_list_documents`, `shield_read_document`, `shield_search`,
  `shield_save_draft`, `shield_status`. Masked output only, no unmask tool, fail closed.
- **Claude Code hooks**: block prompts with registered values, deny direct reads in dossier folders, mask
  registered values left in tool results.
- **CLI** `ragbase-shield`: add, list, entities, register, keep-clear, mask, restore, desk, mcp, hook, install,
  doctor, verify, export, import, journal.
- **Shield Desk**: local page on http://127.0.0.1:7878 with Dossiers, Masquer, Restaurer, Fichiers and Journal.
  French UI with an English toggle. Token, Host check, 127.0.0.1 only.
- **Integrations**: Claude Desktop extension (`.mcpb`), Claude Code and Cowork plugin, Codex and ChatGPT desktop
  configuration, VS Code `mcp.json`, browser extension (Manifest V3) for chatgpt.com, claude.ai,
  copilot.microsoft.com, m365.cloud.microsoft and gemini.google.com.
- **Local journal** with event names, codes and counts only.
- **Bench** on an invented French legal corpus (10 documents, 197 annotated mentions, including a note full of
  hard forms), with a release gate on registered parties and identifiers with a check digit:
  `bench/run_bench.py`, results in `bench/RESULTS.md`.
- **Leak test**: every MCP tool and every hook runs on every fixture and fails on any vault value.
- **Docs**: README (English and French), install guide per app, privacy model, French compliance sheet, FAQ,
  security policy.

### Fixed before the release (review of 2026-10-16)

- **Privacy.** In an AI agent's shell the CLI refuses `keep-clear`, `register`, `add`, `import` and `export`, and
  the Claude Code hook denies them: a model, or a prompt injection in a document, can no longer switch masking off.
  File names are masked word by word ("Kervadec-c-Veltrane.txt", "MaelleKervadec.txt", "kervadec's notes.txt").
  Masking without a dossier still hides the registered names of every dossier ([PERSONNE], [SOCIETE]).
  `shield_search` can no longer confirm a guessed name next to a code. A damaged vault makes every check fail
  closed. Numbers in tool results (a SIREN sent as a JSON number) are masked. Fail-closed blanking removes every
  string and number. Escaping matches what restore reads.
- **Engine.** No more crash on "la SCI DU PARC" and similar names. Possessives, glued words, social handles,
  words broken at a line end, Unicode hyphens, soft hyphens and decomposed accents. Particles in surnames
  ("Le Goff", "d'Orgeval"), "M." kept as a title, firms joined by "&", tribunal de commerce roll numbers, SIREN
  in an EUID, Kbis codes, toque numbers, more first-mention rules, trade names ("Garage Gravelotte").
- **Hooks.** More tools covered (Monitor, LSP, Artifact, SendUserFile, file tools of other MCP servers), size and
  time budgets that fail closed before the timeout, and a much faster check (a 1 MB tool result with 10 dossiers:
  52 s before, about 8 s now; a hook call with nothing to do: about 0.1 s).
- **Vault.** First-start race on the OS keychain fixed (the key could be lost). Entity creation is no longer
  quadratic. The Windows data folder moves to `%LOCALAPPDATA%`.
- **Desk and extension.** The extension gets only the routes it needs. A second `ragbase-shield desk` prints the
  link with the token. The page no longer says "no dossier yet" when the token is missing, preselects the last
  dossier, and warns when no dossier is chosen; tables become cards on a phone. The extension also masks dropped
  text and HTML-only clipboards, and stops pasted or dropped files.
- **Install.** Docs give the command that works before the PyPI release (`uv tool install .`); `doctor` checks
  that each configured app can start Shield; `install claude-code` says when the hooks are not installed.

### Changed after the first internal evaluation round (R1 corrections)

General rules, each with new invented tests (`tests/test_r1_*.py`).

- **Names.** Company acronyms and person initials of registered entities, first names alone (also after "d'"),
  diminutives of registered first names, common-word surnames without a title, one-letter typos of registered
  names, hyphen compounds, partnership names, more trade nouns. A name part shared by two people gets its own
  code, never one person's code; "fils" or "père" after a surname makes a separate person. Contractual role
  words, generic business adjectives and financial instrument acronyms are no longer read as names.
- **Identifiers.** Court roll numbers with a section letter, labelled references (procedure, complaint, file,
  employee, contract, tracking and IMO numbers), cadastral parcels, birth dates after "né(e) le", in ISO form
  or in a table column, more address parts, vessel and school names after a trigger word, labelled table
  columns.
- **Service.** `shield_search` never confirms a word the last check hid. Values of another dossier get a
  restorable code of this dossier. One MCP server process works on one dossier (the first one it opens);
  `RAGBASE_SHIELD_MULTI_DOSSIER=1` turns this off. Files Shield cannot read (spreadsheets, images) are listed
  as unsupported and are never read.
- **Restore.** Saved drafts and `ragbase-shield restore` name the generic marks ("[SOCIETE]") and the Shield
  ids left in the text. Restored values stay on one line, French elision is fixed, "SURNAME Firstname" values
  read "Firstname SURNAME", DOC_n and OUTPUT_n of the dossier get their local file names, numbered lists keep
  their written numbers in Word, and long file names are cut at a word boundary.

### Known limits

- No OCR: scanned PDFs are not read.
- Detection is never complete for names nobody registered.
- Facts, dates and amounts can still identify a client; Shield does not mask them.
- ChatGPT web: no native connection (use Shield Desk or the browser extension).
- Microsoft 365 Copilot, Word, Outlook: through Shield Desk only.
- Browser extension: store listings pending.
- Not on PyPI at the time of this version.
- Restore gives back the stored spelling of a value, not the spelling of each occurrence.

[0.4.0]: https://github.com/ragbase/ragbase-shield/releases/tag/v0.4.0
