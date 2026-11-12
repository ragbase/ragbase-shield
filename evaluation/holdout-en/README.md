# English holdout corpus (`evaluation/holdout-en/`)

Ten fictional company exports in the style of a workspace de-identification benchmark, with an answer key per
export, a runner that applies RAGbase Shield unchanged, and a scorer that reuses the public benchmark's metric
definitions. Its first purpose: a number that nobody tuned on. Status since v0.4: the corpus was a regression gate
at every step of the v0.4 work, so its numbers are informed, not held-out. The PrivacyBench numbers of `evaluation/public/privacybench/`
are "informed (dev set)" numbers since the v0.2 and v0.3 work read that benchmark's miss lists. This corpus was written
blind: from the public description of the task only (file formats, the ten labels, native coordinates, one roster
per export), without reading the benchmark data, its answer keys or any miss list. Every person, company, address,
number, handle and e-mail below is invented; the e-mail hosts and web sites use the reserved `.test` top-level domain.

## What is in it

| | per export | total (10 exports) |
|---|---|---:|
| people | 19 to 25 (home company staff and contacts at 7 outside companies) | 224 |
| organisations | 8: the home company plus 7 outside ones, with a legal form (`LLC`, `Inc.`, `Co.`, `Ltd`, `LLP`) or none, one law firm that carries a person's surname (`<Surname> & Associates LLP`) | 80 |
| e-mails (`.eml`) | 14, RFC 5322, `text/plain`, CRLF, display names in From/To/Cc; the `embed` exports carry the documents as base64 attachments | 140 |
| Slack-style export | `users.json`, `channels.json`, `<channel>/<day>.json` (4 channels and direct messages over 3 days, 46 to 55 messages): lower-case chat, nicknames, `<@Uxxxx>` mentions, handles | 503 |
| documents | `kickoff_notes.docx` (roles table), `contact_roster.xlsx` (two sheets, `Last, First` column), `vendor_accounts.csv`, `statement.pdf`, `site_memo.pdf` (rendered with `cupsfilter`), `files.json` (`drive` exports) | 50 |
| gold spans | 472 to 504 | 4,865 |

Labels (the benchmark's ten): `NAME_GIVEN`, `NAME_FAMILY`, `EMAIL_ADDRESS`, `USERNAME`, `ORGANIZATION`, `PHONE_NUMBER`,
`LOCATION_ADDRESS`, `EMPLOYEE_ID`, `ACCOUNT_NUMBER`, `URL`.

Forms planted on purpose: given and family names in prose, signatures, headers and table cells; `"Nickname"` quoted
inside a full name and nicknames alone; lower-case first names and nicknames in chat; `Last, First` cells; handles in
five styles (`jmoreau`, `jocelyn.whitlock`, `whitlockj`, `j_moreau`, `jocmor`) and `@handle` cells; professional and
personal e-mails (the personal ones on public-style mail hosts, `.test`); phones in four formats on the `555-01xx`
fiction range; US street addresses with city, state and ZIP; employee ids with the company prefix (`EVR-50338`);
account numbers as 8 digits or `ACCT-1234-5678`, and 10-digit vendor account references; company short forms, legal
forms, upper case and lower case mentions; web addresses with paths.

## Layout

```
tasks/<set>/email/<id>.eml
tasks/<set>/slack/users.json, channels.json, <channel>/<day>.json
tasks/<set>/drive/files.json, <documents>            (drive exports; embed exports attach them to e-mails)
ground_truth/<set>/ground_truth.jsonl                one row per e-mail body, Slack message and document
ground_truth/<set>/characters.json                   the roster (people and organisation groups)
ground_truth/<set>/gold.json                         {set, mode, labels, characters, rows}: the answer key in one file
build_report.json                                    counts per export, locating warnings (none)
```

A `ground_truth.jsonl` row: `{"meta": {...}, "text": "...", "file": {"kind", "path", "sha256", "container"},
"ground_truth_spans": [{"text", "start", "end", "label", "characters", "location"}]}`. `start`/`end` are offsets in
`text`; `location` is the native coordinate of the span in the file (`file_char_start`/`file_char_end` of an `.eml`,
`sheet`/`cell`/`char_start` of a sheet, `row`/`col` of a csv, `xpath` fragments of a docx, glyph boxes of a PDF), made
with the same adapters the Shield runner uses, so a gold span sits exactly where a prediction on the same text would.
`characters.json` lists, per person, the first names, last names, nicknames, e-mails, handles, phones, ids, accounts,
addresses and organisations.

Nothing here is a detection signal: no file of this folder is read by `src/`.

## Build, run, score

```
.venv/bin/python evaluation/holdout-en/make_holdout.py --force          # rebuild (cupsfilter needed, macOS)
.venv/bin/python evaluation/holdout-en/run_holdout.py --out NAME --synthetic [--register-first] [--ner off|auto] [--workers 4]
.venv/bin/python evaluation/holdout-en/score_holdout.py --out NAME [--official] [--syncover]
.venv/bin/python evaluation/holdout-en/score_holdout.py --out NAME --predictions-name predictions_synthetic --syncover
.venv/bin/python evaluation/holdout-en/check_separation.py [--since COMMIT] [--strict]   # no corpus string in src/ or tests/
```

The build is deterministic: one seed per export, fixed document properties and zip timestamps, PDF dates and ids
pinned after rendering, so two builds give the same bytes. The runner is `evaluation/public/privacybench/run_shield.py`
pointed at this corpus (zero-shot, one store per export, two passes, rules mode by default), untouched. Outputs land
under `.bench_data/holdout-en/<NAME>/`: `predictions/`, `predictions_synthetic/`, `run_meta.json`, `scores*.json|md`.

`--register-first` is a measurement aid for the synthetic run, off by default: pass 1
registers the export in codes mode and the first fake is drawn in pass 2, when the store already holds every value
of the export. `run_holdout.py` does it by swapping the runner's `Masker` and `mask_unit` names in its own process;
the runner's file is not changed, and `run_meta.json` records `register_first` and the protocol. Without the flag
the synthetic run is the runner's own protocol (both passes in synthetic mode, a fake drawn as soon as a value is
registered), which is what the public benchmark number uses.

Scoring, `score_holdout.py`: the card's native metric as re-implemented in `recheck_v02.py` (standard library only): a
gold span counts as detected when a prediction of the same file unit, with the same label or an accepted alias,
overlaps it by at least 0.5 of the union in native coordinates, or contains it; NER recall = detected / gold per
export; the headline is the macro mean over the exports. Also given: "any label" recall (the value is masked under
another label), a precision proxy (predictions in scope that cover no gold span; every planted value is gold, and
city names, dates, amounts, roles and topics are not), the number of codes written in place of a fake value in
synthetic mode (fail closed), and with `--syncover` the codes-versus-synthetic leak check (codes-run spans with no
synthetic-run span over them: values the synthetic output shows in clear). `--official` runs the benchmark's own
scorer unchanged when its code is checked out under `.bench_data/public/privacybench/code`.

## Reading a number

Two things to know when reading a number. Several surnames and company words of this corpus also occur in Shield's
synthetic word lists (`engine/lexicon/synthetic_*_en.txt`); that is incidental (both are invented English names) and
it is what made the corpus a canary for the fake-surface suppression bug of synthetic mode (a fake drawn before the
real value was registered hides that value). And the 10 exports are smaller than the public ones (about 4,900 gold
spans against 130,000), so one export moves the macro mean by up to a point.

## Rules

- No string of this corpus (a name, a company, a street, an id prefix, a handle) may enter `src/` or a lexicon as
  a detection signal: the number stays held-out only as long as nobody tunes on it. Keep the invented test data of
  `tests/` apart from the corpus too (a test is not a detection signal, but a shared invented name blurs the line).
  `check_separation.py` reports the overlap, by bucket, over the whole tree or over the lines added since a commit
  (`--since <commit> --strict` exits 1 on a hit in engine code or a synthetic word list).
- Freeze the build (`git_head` and `git_dirty` are recorded in `run_meta.json`) before a number is quoted.
- Same licence as the repository (Apache-2.0). Written for RAGbase Shield on 2026-10-20 and 2026-10-21.
