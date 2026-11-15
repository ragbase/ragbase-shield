# Benchmark sets: REF and Max

Two French benchmark sets for pseudonymisation tools, written by RAGbase: the files a law firm works on, with an
answer key for every file. The results are on the [benchmark page](../laptop/RESULTS_PUBLIC.md).

| Set | Content | Files | Answer key |
|---|---|---|---|
| [REF](ref) | An employment-law brief before the conseil de prud'hommes de Lyon, in five versions: the same text with different names, addresses, dates and numbers | 5 Word files, about 29,400 characters each | 1,015 personal data items, 365 legal terms |
| [Max](max) | Seven law-firm matters: distribution contract, sale of a company, unpaid invoices, dismissal, financial-markets sanction, estate, commercial lease | 33 files: 10 Word, 20 PDF, 1 Excel, 2 text | 1,003 personal data items, 144 legal terms |

Each set has `input/` (the files), `gold.jsonl` (the answer key), `tasks.json` (the folders a tool receives),
`order.txt` (the run order) and `SHA256SUMS`.

## Answer key

`gold.jsonl` has one line per file. It marks the personal data that a tool must mask and the text that it must
keep readable. Positions are character offsets in the text that [`extract_text.py`](../laptop/extract_text.py)
reads from the file.

| Field | Content |
|---|---|
| `doc_id`, `file` | The file and its path under `input/` |
| `text_sha256`, `chars` | Hash and length of the text of the file |
| `gold` | Personal data to mask. Each item: `id`, `label`, `start`, `end`, `text` |
| `keep` | Text to keep readable. Each item: `id`, `class`, `start`, `end`, `text` |

Labels: PERSON, ORG, ADDRESS, PLACE, BIRTHDATE, EMAIL, PHONE, URL, IBAN, NIR, SIREN, SIRET, VAT, CASE_REF, ID_CODE,
OTHER_ID. The legal terms are the `keep` classes `court`, `court_city`, `article`, `code`, `law`, `legal_ref` and
`legal_term`. The other classes are `date`, `amount`, `role` and `obligation`. The other fields describe the file
or the item, for example `part` in REF, `matter` and `entity` in Max.

The scores count the items in the text of the files, comments included: the counts of the table above. The key
also marks the items of the document properties, the author names of comments and tracked changes, and deleted
text that stays in a Word file: 20 personal data items in REF, 95 personal data items and 6 legal terms in Max.
The scorer reports them apart.

## Licence and content

Documents and answer keys: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Scripts: Apache-2.0.

Every person and company that takes part in a case is invented. A match with a real person, company, address or
number is by chance. Some towns are invented too. Courts, laws and public bodies are real, and the documents
written in their name are invented. The three court decisions cited in REF are invented examples, and a match of
their numbers with a real decision is by chance. Max cites real decisions (Cour de cassation, Conseil
constitutionnel, CJEU, ECHR) and invented ones.

## Reproduce the results

From the root of a clone of this repository, with Python 3.10 or newer (on Windows, in Git Bash or WSL):

```bash
bash evaluation/datasets/reproduce.sh ref
bash evaluation/datasets/reproduce.sh max precise
bash evaluation/datasets/reproduce.sh ref presidio
```

The first argument is the set: `ref` or `max`. The second is the tool: `fast` for Shield 0.4.1 Fast (the default),
`precise` for Shield 0.4.1 Precise (one download of the model, about 1.25 GB) or `presidio` for Presidio 2.2.364.
The script installs the tool, runs it on the set with the network closed, and prints the overall score (F1) with
precision and recall, the legal terms changed, the time and the peak memory. Time and memory depend on the
computer.

Shield 0.4.1 comes from the [release page](https://github.com/ragbase/ragbase-shield/releases/tag/v0.4.1): the
script downloads the file `ragbase_shield-0.4.1-py3-none-any.whl`, checks its SHA-256 and installs it.

By hand, for Shield Fast on REF:

```bash
python3 -m venv .venv
source .venv/bin/activate
W=ragbase_shield-0.4.1-py3-none-any.whl
pip download --no-deps --dest .bench_data https://github.com/ragbase/ragbase-shield/releases/download/v0.4.1/$W
echo "1710644a4e93e3e436f4d46d9d931d98eee208fe6b58d6f82a5f2e455aad54c5  .bench_data/$W" | shasum -a 256 -c
pip install .bench_data/$W pdfplumber==0.11.10 pdfminer.six==20260107 openpyxl==3.1.2
S=evaluation/datasets/ref; L=evaluation/laptop; O=.bench_data/ref
python $L/run_shield_files.py --set-dir $S --out $O --mode rules
python $L/score_text.py score --gold $S/gold.jsonl --inputs $S/input --outputs $O --runlog $O/runlog.jsonl --json $O.text.json
python $L/score_f1.py score --gold $S/gold.jsonl --inputs $S/input --outputs $O --runlog $O/runlog.jsonl --score-text-json $O.text.json --json $O.f1.json
```

The `shasum` line checks the downloaded file against the SHA-256 of `SHA256SUMS` on the release page: it must
print `OK` (on Linux, `sha256sum -c` does the same).

Use a new folder `O` for each run. The overall score is `summary.word.strict` in `$O.f1.json`. The legal terms
changed are `summary.must_stay_clear` in `$O.text.json`. Time and memory are in `$O/tasks_log.jsonl` and
`$O/run_meta.json`.

The method and the case types of matters A, B and C of the Max set follow the white paper Confidentiality and legal artificial intelligence (AIDocs Studio, October 2026). RAGbase wrote every document and every answer key.
