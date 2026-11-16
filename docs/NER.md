# Precise mode: the optional AI model (NER layer)

Shield has two modes. Fast mode (the default; technical name: rules) finds names and identifiers with lexicons,
check digits and context. Precise mode adds a local AI model for name recognition (technical name: GLiNER; the
models are GLiNER2 and GLiNER). The model finds what the rules miss: first names alone, nicknames, initials, typos,
names in file names and e-mail subjects, organisations without a legal form. Every span it proposes passes the
precision guards of `merge.py` before it becomes a candidate. The rules keep the last word on the kind of a span.

Section 1 shows how to turn Precise mode on. The other sections are the technical reference of the layer, for
developers.

Files: `src/ragbase_shield/engine/ner.py`, `src/ragbase_shield/engine/merge.py`, the lexicon files listed in
section 7, `tests/test_v02_ner.py`, the `ner` extra of `pyproject.toml`.

## 1. Install and download

The extra "ner" installs gliner2, gliner, torch (CPU), transformers and huggingface_hub. With pip:

```sh
pip install "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl"
```

On a Mac with an Intel processor, use this line:

```sh
pip install "numpy<2" "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl"
```

Or with uv. To install uv, paste the uv line for your computer (Mac or Windows) from the
[README](../README.md#install), section Install. If uv is already on your computer, paste this line anyway: it
updates uv. Then:

```sh
uv tool install --python 3.12 "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl"
```

On a Mac with an Intel processor, use this line:

```sh
uv tool install --python 3.12 --with "numpy<2" --with "sentencepiece<0.2.3" "ragbase-shield[ner] @ https://github.com/ragbase/ragbase-shield/releases/download/v0.4.4/ragbase_shield-0.4.4-py3-none-any.whl"
```

Then download a model once. The default model is fastino/gliner2-privacy-filter-PII-multi, about 1.25 GB:

```sh
ragbase-shield ner download
```

The other model is urchade/gliner_multi_pii-v1, about 1.16 GB:

```sh
ragbase-shield ner download --model urchade
```

`ner status` lists the packages, the cached models and the backend that "auto" resolves to. `doctor` with
`RAGBASE_SHIELD_NER=on` checks Precise mode:

```sh
ragbase-shield ner status
RAGBASE_SHIELD_NER=on ragbase-shield doctor
```

The download is the only network step. It goes to the models directory (`RAGBASE_SHIELD_MODELS_DIR`, default
`<home>/models`) in the Hugging Face hub cache layout, so the directory can also be given to the libraries as
their cache. At run time Shield sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`
before any import of the libraries and loads the model from the local snapshot directory. The test suite blocks
outbound sockets; the real-model tests pass under that guard.

A model cached in the user's own Hugging Face cache (`HF_HUB_CACHE`, `HF_HOME/hub`, `~/.cache/huggingface/hub`)
is found too. A snapshot folder copied by hand into `<models dir>/<repo name>` works as well.

On Intel macOS the last torch is 2.2.2 and transformers must stay under 5 (the extra pins `transformers<5`).
The one-click installers do not include the model yet: install it with uv or pip.

## 2. Settings

| Variable | Values | Default | Effect |
|---|---|---|---|
| `RAGBASE_SHIELD_NER` | auto, on, off | auto | off: never a model; on: a warning (once) when no model is installed, rules only |
| `RAGBASE_SHIELD_NER_MODEL` | auto, fastino, urchade, spacy | auto | auto = fastino when cached, else urchade when cached, else spaCy when installed, else rules |
| `RAGBASE_SHIELD_NER_MAX_CHARS` | integer | 200000 | the `Masker(ner=...)` hook runs NER on pasted text up to this size, rules only above |
| `RAGBASE_SHIELD_NER_THREADS` | integer | CPU count | torch threads |
| `RAGBASE_SHIELD_MODELS_DIR` | path | `<home>/models` | where `ner download` puts the models |

Accessors: `ner.ner_setting()`, `ner.ner_model_setting()`, `ner.ner_max_chars()`, `ner.ner_threads()`,
`ner.models_dir()`. `config.py` may re-export them.

## 3. API (`ragbase_shield.engine.ner`)

```python
class NerSpan(NamedTuple): start, end, label, score          # offsets inside one chunk
class NerBackend(Protocol):
    name: str                       # "gliner2:fastino", "gliner:urchade", "spacy:fr_core_news_md"
    labels: dict[str, str]          # model label -> Shield kind
    thresholds: dict[str, float]    # model label -> minimum score
    def predict(self, chunks: list[str]) -> list[list[NerSpan]]

ner_installed(model="auto") -> bool         # packages importable AND model cached; imports nothing, loads nothing
resolve_model(model="auto") -> str | None   # "fastino" | "urchade" | "spacy" | None
load_backend(model="auto", *, kinds=None) -> NerBackend | None   # thread-safe singleton; loads once per process
ner_available(model="auto") -> bool         # load_backend(model) is not None
chunk_text(text, max_chars=1200) -> list[tuple[int, str]]
run_ner(text, backend, *, kinds=None, max_chars=1200, batch_size=16, cache=...) -> [(start, end, kind, label, score)]
as_hook(backend, *, kinds=("PERSON", "ORG"), lang="fr", max_text_chars=None, **guard_kw) -> text -> [(s, e, kind)]
download_model(model="fastino", *, models_dir_path=None, dry_run=False, force=False, log_fn=print) -> [Path]
status(model="auto") -> dict ; status_lines(lang="fr") -> [(level, label, value)]   # for doctor / ner status
snapshot_dir(spec, roots=None) -> Path | None ; model_cached(key) -> bool ; unload_backends()
```

Backends: `Gliner2Backend` (fastino, package `gliner2`), `GlinerBackend` (urchade, package `gliner`),
`SpacyBackend` (a French spaCy model), `CallableBackend(fn, labels)` for tests and custom models.
`kinds` limits the labels asked from the model (fewer labels, faster inference).

### Label maps and default thresholds

| Shield kind | fastino labels | urchade labels | threshold |
|---|---|---|---|
| PERSON | person, full_name, first_name, middle_name, last_name | person | 0.40 |
| ORG | organization, company (custom labels) | organization, company | 0.60 (fastino), 0.45 (urchade) |
| EMAIL, PHONE, ADDRESS, BIRTHDATE | email; phone_number; address, street_address; date_of_birth | email, email address; phone number, mobile phone number, landline phone number; address, full address; date of birth | 0.50 |
| USERNAME | username, account_id | username, social media handle | 0.50 |
| EMPLOYEE_ID | employee_id (custom) | employee id, staff number | 0.50 |
| ACCOUNT_NUMBER | bank_account, account_number, routing_number, sensitive_account_id | bank account number, account number | 0.50 |
| ID_CODE | government_id, national_id_number, passport_number, drivers_license_number, license_number, tax_id, tax_number, ip_address, password, secret, api_key, access_token, recovery_code; custom vessel, building, school | passport number, license plate number, ip address, identity card number, national id number, driver's license number, tax identification number; custom vessel name, building name, school | 0.50 |
| ignored | city, state_or_region, postal_code, country, iban, card_*, sensitive_date, document_date, expiration_date, transaction_date | the rest | |

On the masker path, a model find may add only the kinds of `merge.MODEL_KINDS` (PERSON, ORG, ADDRESS, USERNAME,
EMPLOYEE_ID, ACCOUNT_NUMBER). The other finds of the model are never masked on their own.

### Chunking, batching, exact offsets

`chunk_text` cuts at a blank line, then a line end, then a sentence end, then a space, in the last two thirds of a
1,200-character window (about 300 tokens, under the encoder window), else a hard cut. No overlap. Chunks go to the
backend in batches of 16. Every returned span is checked: the backend drops a span whose text is not at its offsets
in the chunk, `run_ner` checks the chunk against the text again, whitespace edges are trimmed, a span with two
labels keeps the best score, and a span under the backend threshold of its label is dropped. Results are sorted.

A small LRU cache (`ChunkCache`, 4,096 entries) is keyed by `sha256(backend, labels, chunk)`: a page read twice
is not run twice. The cache holds offsets and labels only, never text.

## 4. Merge and precision guards (`ragbase_shield.engine.merge`)

```python
merge_ner(text, ner_spans, rule_spans=(), structured=(), protected=None, *, lang="fr", kinds=None,
          org_acronyms=(), one_word_person_min=0.50, one_word_org_min=0.70, lenient_first_names=False)
    -> list[MergedSpan(start, end, kind, label, score, origin)]      # origin: "ner" | "rule+ner"
guard_ner_spans(text, ner_spans, *, lang="fr", kinds=None, **kw)    # the same without rule or structured spans
is_name_word(word, lang="fr", kind="PERSON") -> bool
trim_span(text, s, e, kind, lang="fr") -> (s, e)
lists_for(lang) -> Lists ; ner_stoplist(lang) ; vocab(lang) ; spelled_forms(lang) ; places(lang)
```

`rule_spans` and `structured` accept anything with `start`, `end`, `kind` (`names.RuleSpan`, the masker's `_Cand`)
or `(start, end, kind)` tuples. `protected` is `names.protected_intervals(...)`; computed here when None.

Rules, in order:

1. Edges: titles (fr and en), a leading function word, company trigger ("société", "groupe", "the") or role noun
   before a capitalised word ("Gérant X" gives "X", as with the rules), a statutory phrase at the start
   ("société par actions simplifiée X" gives "X"; "syndicat des copropriétaires de l'immeuble" gives nothing),
   trailing legal forms, connectors (lower case only: "P.-H. G." keeps its last initial), possessive "'s",
   punctuation and quotes.
2. A span that overlaps a structured span or a protected interval (whitelist, court + city, law reference,
   defined case law) is dropped. A birth date may overlap a whitelisted month.
3. A span made only of stop words, legal terms, months, titles or NER stop-list entries is dropped.
4. Rules win on kind: a span equal to a rule span adds nothing; a span that contains one rule span keeps the
   rule's kind and extends it only when every extra word passes `is_name_word` (origin "rule+ner"); any other
   overlap with a rule span is dropped.
5. NER-only guards (people and organisations): a dotted registry acronym at the start ("R.C.S. Lyon") is never
   a company; in an all-capital line a candidate made only of vocabulary words is never a name; a one-word
   candidate that is a place is never a name; a 2 to 5 letter all-capital token is never a person unless it is
   the initials of a person of the text ("PHG" after "Paul-Henri G." or "P.-H. G."), and it is an
   organisation only when it is the initials of an organisation of the text (rules or NER, a preceding trade or
   trigger word included: "Transports M... V..." gives TMV), one of `org_acronyms` (the masker's registered
   acronyms), or defined right before ("(ci-après « X »"); a one-word PERSON is kept when it is a first name that
   is not a vocabulary word, a prefix of a first name of the text (4+ letters: "Herme" for Marie-Hermeline), or
   with score at least `one_word_person_min` and a cue: a title (also "M." with its dot), a greeting, a role word
   ("gérant X", "liquidateur judiciaire X", "manager X"), "Dossier X", "Succession X", "consorts X", "X c/ Y",
   "with/to/from/avec/pour/chez X", "@X", a quoted nickname after "surnomme/dit/alias/known as", a possessive,
   ", gérante" after it, or a signature line under "Cordialement,"; the cue must be in the same sentence; a
   one-word ORG that is a generic company word or a vocabulary word needs a company cue ("chez X", "at X", "X's",
   a legal form after it), another one-word ORG needs score at least `one_word_org_min` or a cue; a multi-word
   PERSON needs capitalised name words (initials and particles allowed, no stop or legal word); a multi-word
   ORG needs one distinctive word (not generic, vocabulary, legal or place) and a capitalised majority.
6. Identifier kinds (EMAIL, PHONE, ADDRESS, BIRTHDATE, USERNAME, EMPLOYEE_ID, ACCOUNT_NUMBER, ID_CODE) pass a
   value-shape check: an address holds a number or a street word, a username has no space, a date has digits and
   a month or three digit groups, an id holds digits (or letters and digits), never a bare year, a date shape or an
   amount; a named asset (vessel, building, school) is capitalised and holds a non-vocabulary word.
7. Nested and overlapping spans collapse to the longest, then the best score; output sorted by position.

Language lists: French from the lexicon package and `names.py` sets plus the files of section 7; English from
`engine/locale.py` `bundle("en")` (LOCALE-EN) when it imports, else the `*_en.txt` files when present, else a
built-in fallback (function words, titles, greetings, months, generic company words). The French stop list is
never applied to an English text when `lang="en"` is passed.

## 5. Default thresholds

PERSON 0.40 (several words). One-word PERSON 0.50 with a cue. ORG 0.60 (fastino) and 0.45 (urchade). One-word ORG 0.70
without a cue. To change them, use the `guard_kw` of `as_hook` or the arguments of `merge_ner`.

## 6. How the layer plugs into Shield

- **Masker** (`engine/masker.py`). On each text the masker runs its rules, then `ner.run_ner` and `merge.merge_ner`
  with its own rule and structured spans. The masker loads the model on first use, never at construction; the MCP
  server and Shield Desk start the load in the background. A text longer than `RAGBASE_SHIELD_NER_MAX_CHARS` is
  masked with the rules only. `Masker.mode` reads `rules`, or `rules+ner:<backend>` when a model is in use. A model
  find that no second signal confirms is stored with the source `ner`.
- **Plug-in path.** `Masker(store, ner=ner.as_hook(backend))` plugs a model in through the same guards (tests in
  `tests/test_v02_ner.py`).
- **Command line** (`cli.py`). `ragbase-shield ner status` and `ragbase-shield ner download [--model
  fastino|urchade|all] [--dir DIR] [--dry-run] [--force]`; `doctor` prints the same status lines. The download is a
  user action: an AI agent's shell cannot start it.
- **Service** (`service.py`). `status()` has a `ner` block. The hooks, the canary and the label pass never use a
  model.

Full contract: ARCHITECTURE.md, section 11.2.

## 7. Lexicon files of this layer (all written for RAGbase Shield, Apache-2.0)

| File | Entries | Use |
|---|---:|---|
| `ner_stoplist_fr.txt` | 257 words, 140 phrases | an NER span made only of these is dropped; a phrase at the start is cut ("liquidateur judiciaire X" gives "X") |
| `ner_stoplist_en.txt` | 231 words, 89 phrases | same for English |
| `vocab_fr.txt` | 2,401 words (several per line) | capitalised common words: not a name by themselves; all-capital line guard; `is_name_word` |
| `legal_forms_spelled_fr.txt` | 150 phrases, 71 short forms | statutory phrases cut from an organisation span; short forms count as legal forms |
| `acronyms_fr.txt` (+64) | court functions (JAP, JI, JME, JCP, JDE), code abbreviations (CPC, CGI, CSS...), payroll and tax acronyms | never a person, never a company alone |
| `legal_terms_fr.txt` (+96) | legal adjectives ("judiciaire"), party roles ("copropriétaire", "assureur", "distributeur") | never a person's name word (rules and merge) |
| `whitelist_fr.txt` (+55) | public bodies and foreign jurisdictions ("conseil régional", "assurance maladie", "supreme court") | protected intervals |

The `places_fr.txt` and `vocab_en.txt` files belong to LOCALE-EN; the merge reads them when they exist (the
English bundle of `engine/locale.py` already provides vocabulary, places and acronyms).

## 8. Licences

| Component | Licence | Shipped? |
|---|---|---|
| `fastino/gliner2-privacy-filter-PII-multi` (model card) | Apache-2.0 | downloaded by the user |
| `urchade/gliner_multi_pii-v1` (model card) | Apache-2.0 | downloaded by the user |
| `microsoft/mdeberta-v3-base` tokenizer files (needed by the urchade model) | MIT | downloaded by the user |
| gliner2 2.1, gliner 0.2.29, transformers 4.57, huggingface_hub, tokenizers, safetensors, sentencepiece | Apache-2.0 | pip, `ner` extra |
| torch 2.2 (CPU) | BSD-3-Clause | pip, `ner` extra |
| protobuf | BSD-3-Clause | pip, `ner` extra |
| numpy, sympy, networkx, mpmath, jinja2, markupsafe, fsspec, filelock, regex, tqdm, requests, urllib3 | BSD / MIT / Apache-2.0 / Unlicense (tqdm: MPL-2.0 + MIT) | transitive |

No GPL, LGPL or AGPL code. The lexicon files are written for RAGbase Shield. Nothing comes from another project.

## 9. Privacy

- No real value in a log line: the module logs backend names and counts only.
- No network at run time: the offline variables are set before the libraries are imported; the download is one
  explicit command.
- Fail closed means codes only, never raw text: when the model is missing or crashes, the engine runs the rules
  alone and still masks; the hook catches every backend exception (test `test_hook_failure_never_breaks_masking`).
- The chunk cache holds hashes, offsets and labels, never text.
- The canary, the hooks, `scan_text`, `guard_output` and the label pass never use a model (unchanged, service
  owner).

## 10. Notes

1. The trigger word stays in clear: "Société X" is masked as "Société SOCIETE_A", by the rules and by the merge.
2. `vocab_fr.txt` is hand-written (2,400 words). A larger vocabulary would tighten the capitalised-word guard
   further.
3. GLiNER v1 (urchade) prints a tokenizer warning ("no maximum length"); chunks stay under its 384-word window,
   so nothing is truncated. The mDeBERTa "incorrect regex pattern" warning of transformers is cosmetic.
4. The `gliner2` package pulls `requests` through transformers; the library test `test_library_has_no_network_client`
   checks Shield's own modules only, which import nothing from the network stack (the download helper imports
   `huggingface_hub` lazily, inside `download_model`).
