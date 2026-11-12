# Protocol addendum 1 (section 17 of the laptop head-to-head protocol)

Version 1.1, 2026-10-24. Status: FROZEN by `PREREG.sha256` v1.1 (the v1.0 freeze stays as `PREREG_v1.0.sha256`).
Written before any Hexagone, Tonic or Presidio output existed, and before Shield 0.3.1 read REF.

`PROTOCOL.md` stays byte-identical to version 1.0. This addendum is its section 17. Where the two differ, this
addendum applies. The reasons for each rule, the invented test cases and the results seen are in
`<work>/PROTOCOL_CRITIC.md`; the record of the change is `DEVIATIONS.md` D2.

## 17.1 Reader `laptop-extract-1.1` (amends section 7)

The text is the same as reader 1.0 for every file (checked on all 1,000 prepared input files: 0 differ). The reader
record (`--meta`) adds:

- `hidden_ranges` (.docx): the character ranges of the text that come from tracked deletions (`w:delText`);
- `image_only` (.pdf): the pages carry images but no letter or digit in their text layer.

## 17.2 Scorer `laptop-score-1.1` (amends section 8.1)

Rules 1 to 8 of section 8.1 stay, with these changes:

1. **Token keys.** Tokens are compared by a key: NFKC, lower case, accents removed. The output is NFC-normalised
   first. A change of case or accents is not a change.
2. **Alignment in three passes.** (a) Lines, then tokens inside differing blocks (as in 1.0), then a repair: between
   two aligned words outside gold, when a gold word was aligned while an identical word outside gold was left out,
   that stretch is aligned again to keep first the most words outside gold, then the most gold words. Words
   outside gold that equal an identifying word of a gold item, and words of document properties and tracked
   deletions, count as gold words for this repair. (b) Moved blocks: among the tokens still unmatched, runs of 6 or
   more identical tokens with 4 or more letter-or-digit tokens are matched anywhere in the document. (c) Gaps: each
   remaining run of unmatched input tokens is aligned with the unmatched output tokens between its neighbours'
   places (when the places cross: the next output tokens).
3. **Rejoin.** A keep item that looks altered, or a gold item that looks protected or partial, is checked once more
   on its folded letters and digits alone: when they appear in one piece in the output between the item's two kept
   neighbours, in a stretch at most 12 letters or digits longer, the item is read as unchanged. A string of fewer
   than 8 letters or digits must also start and end on output token boundaries.
4. **Identifying tokens (adds to rule 3 of 8.1).** For e-mail addresses and URLs, these public or reserved mail
   domains do not identify: example, gmail, googlemail, hotmail, outlook, live, msn, yahoo, ymail, icloud, aol,
   orange, wanadoo, free, sfr, neuf, laposte, bbox, gmx, protonmail, proton. Format tokens shared by every value of
   a type do not identify, when other tokens remain: a phone number's country code (value starting with "+" or
   "00") and its first group when it is "0" plus one digit and the number, after any country code, has 4 or more
   groups; an IBAN's first group of two
   letters and two digits; a NIR's first digit when it is 1 or 2. The MAPA `ident` rule is unchanged.
5. **Two readings of exposure.** STRICT (rule 3 of 8.1, the headline): exposed = partial + missed. VALUE: exposed
   when more than half of the identifying letters and digits are kept at the item's place.
6. **Parts (extends rule 7 of 8.1 and section 7).** Gold items AND keep items inside document properties (part
   "metadata") or inside tracked deletions of a .docx (part "hidden", from `hidden_ranges`) are reported apart and
   are not in the headlines (a) and (b); their words are not in the over-masking counts. Every report also shows
   "Must stay clear, all parts" (the 1.0 reading of P2).
7. **Statuses.** `failed` as in rule 8 of 8.1. `not_run` and `unscorable`: see 17.5.
8. **Run log.** A run-log row is matched by the gold `doc_id` or, when no row has it, by the gold `file`.

## 17.3 Validation (amends sections 8.2 and 8.3)

- The section 8.3 table is unchanged with scorer 1.1: every count is equal to 1.0 on the Shield v0.3 outputs
  (`<work>/validate/score_v11_*.json`).
- Identity and oracle (section 8.2) pass with scorer 1.1 on REF, FR-PII-Bench, MAPA, Max, English, the old and the
  fresh Judilibre sets (`validate/oracle_v11.txt`, `validate/oracle_v11_judilibre.txt`). The simulated docx
  rewrite gives the same result as 1.0 (`validate/docx_sim/score_v11.json`).
- `score_text.py --selftest` holds the 76 invented review cases: every kept change, for codes, tags, realistic fake
  values and deletion, with the true answer (`review_cases()`). `<work>/critic/fairness_cases.py` runs
  the same cases through scorer 1.0 for comparison.

## 17.4 Claims (amends sections 11.2 and 11.3)

- `compare_runs.py` 1.1 compares headline parts only (it leaves out gold and keep items of parts "metadata" and
  "hidden", as the scorer's headlines do).
- P1 is compared twice, strict and value. A P1 claim ("X exposes less than Y on set S") is allowed only when the
  whole 95 % bootstrap interval of the difference is on the same side of 0 for BOTH readings. P2 is unchanged.
- The bootstrap order is P1 strict, P2, then P1 value, so P1 strict and P2 use the same resamples as version 1.0.

## 17.5 Statuses `not_run` and `unscorable` (adds to section 12.1; this is the "section 12.4" that scorer 1.1 needed)

- `not_run`: a document the tool never received, because a whole task (folder) was not given to it for a reason
  outside the tool (the Hexagone trial ended, the Tonic word budget of section 9.2 ran out). Only whole tasks, only
  the last tasks in the fixed order of section 10.2, written in the run log and in `RUNSHEET_HEXAGONE.csv` (or the
  Tonic run notes) BEFORE any score of that task is computed. Never for a document the tool received: that is
  `failed` (section 12.1, a failed document counts as fully exposed).
- `unscorable`: the tool's output is a PDF with images and no text layer (reader record `image_only`). Our reader
  cannot see whether the values were masked.
- Both: no item is counted; the documents are listed in every report; they are left out of BOTH sides of every
  paired comparison (`compare_runs.py` 1.1 does this and prints the list). A claim on a set with such documents
  names how many were left out.

## 17.6 Files and logs (amends sections 12.3 and 15)

| File | Role |
|---|---|
| `PREREG_v1.0.sha256` | the v1.0 freeze of 2026-10-23 16:09 CEST, kept unchanged |
| `PREREG.sha256` | the v1.1 freeze (this addendum, the tools as changed by D2, the lists, built data, validation and review files) |
| `PREREG_DATA.sha256` | the data addendum (17.7). If an H2 contingency (section 9.4) changes input files, their hashes go into a new file `PREREG_DATA_2.sha256` before any scored run (a deviation entry) |
| `RUNSHEET_HEXAGONE.csv` | a LOG, not frozen: it grows during the trial. Its frozen v1.0 content was the header line only (SHA-256 in D2); the header must stay as it is |
| `DEVIATIONS.md`, `evaluation/laptop/VM_BUSY` | logs, not frozen |
| `freeze.py` | 1.1: writes and checks the files above; leaves the logs out |

## 17.7 Data addendum (`PREREG_DATA.sha256`, written 2026-10-24T13:42:25Z, 829 files)

The fresh Judilibre draw ran on 2026-10-24 from 13:20:05Z to 13:21:23Z (section 5.3; public dataset, no account
and no key). `prepare_sets.py all` rebuilt FR-PII-Bench, MAPA, Max and English byte-identical to the v1.0 freeze;
`prepare_sets.py judilibre` built the fresh set.

| Part | Files hashed | Content |
|---|---:|---|
| Fresh draw | 3 | `judilibre_fresh/sample.jsonl` (SHA-256 `96c268e4…781f`), `sample_manifest.json`, `precis_subset.txt` (the 50 files of the Precis subset: first 17, 17 and 16 kept decisions per stratum) |
| Judilibre fresh set | 204 | 200 inputs (.txt), gold, order, tasks, stats: 2,308,427 characters, 673 indicative gold names, 6,136 must-stay-clear keep items, 8,648 placeholders; strata 67, 67, 66 |
| REF | 8 | 5 inputs (.docx), gold, order, tasks |
| PILOT | 3 | 2 inputs (.docx, .txt), tasks |
| FR-PII-Bench | 304 | 300 inputs, gold, order, tasks, stats |
| MAPA | 23 | 19 inputs, gold, order, tasks, stats |
| Max | 38 | 33 inputs, gold, order, tasks, stats, excluded |
| English | 245 | 241 inputs, gold, order, tasks, stats |
| Shield wheel | 1 | `bundle_v031/shield/dist/ragbase_shield-0.3.1-py3-none-any.whl`, SHA-256 `b15c9771e4b40a4dac4cc14bbda71a05d60831d211c3c8af79a607e4c9c2b558` (commit 577b423; the copy in `<work>/dist/` has the same hash) |

## 17.8 Operations recorded as deviations

D1 (Claude operates Hexagone, at Hadi's instruction) and D3 (Tonic runs from the Mac with the key file) change
sections 9.2, 9.4 and 4.3. They are in `DEVIATIONS.md`, with the other entries of 2026-10-24.
