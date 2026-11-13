# Public bundle of the head-to-head: what is here and what changed

This folder holds the public results of the laptop head-to-head of October and November 2026
(`RESULTS_PUBLIC.md`), the protocol it links to, and the scorer and runner scripts it names.

## Files

| File | Status | SHA-256 of the file in this folder |
|---|---|---|
| `RESULTS_PUBLIC.md` | public copy, changed (see below) | `d994cb561d57e473720a9f1514cf2445a9d75e259b8aca29e35d11a84cc54978` |
| `PROTOCOL.md` | public copy, changed (see below) | `23eb69394cd3bfa6860fa3b23094a0d19a450bcf46d3fb7ff3ed3d68f2f62eae` |
| `PROTOCOL_ADDENDUM_1.md` | public copy, changed (see below) | `56947c92d687f4b03e8d953ac3d7454ffffcb001907093f510efa5ea98fd1e72` |
| `PROTOCOL_ADDENDUM_4.md` | public copy, changed (see below) | `2ede30ef1c3b02706b6343a9c4343c55a0ab02a6f23173ae1f4ab34a5296e5a7` |
| `DEVIATIONS.md` | public copy, changed (see below) | `38d663c830f0edb46bdc0ae5eec23565b80fdf41102fe630a2cd329488899ba7` |
| `score_text.py` | frozen file, internal folder in docstrings written `<work>/` (see below); SHA-256 of the frozen file: `d2e32fcfcd8f08a33ad2f4d758b216d4be36fe04d031dd0ec1519eeb351281e2` | `8ac2ddf1b6c544b423665f8db51d159f47d74d259c75af71f39bcf97ae871dde` |
| `extract_text.py` | byte-identical to the frozen file | `71b063fcd853092b74354d8c490b03d418a43db537e1c2d59f315c3ee2a2cc90` |
| `compare_runs.py` | byte-identical to the frozen file | `32dfa48f34ba74681b8e14b10b3c071fd285ac0611e5c8aec014489153806162` |
| `run_shield_files.py` | byte-identical to the frozen file | `1ac1c4c344c6d7eabf368d3024e08ea6cc294e944b4b71998d601c426b95a1eb` |
| `run_presidio.py` | byte-identical to the frozen file | `72a41961cd4311d5e5dd2fcf2f013a0b539443d17996e3e9c95448d9898d616b` |

The five scripts are the frozen versions (scorer `laptop-score-1.1`, reader `laptop-extract-1.1`, `compare_runs.py`
1.1, and the Shield and Presidio runners). Four are byte-identical to the freeze. In `score_text.py`, three
docstring lines named the internal work folder of the study; they are written `<work>/` here, and the code is
unchanged. The table gives the SHA-256 of the frozen file next to the SHA-256 of this copy.

## What changed in the public copies

- `RESULTS_PUBLIC.md`: the two links to `RESULTS_PUBLIC_2026-10-25.md` (a file that is not in this repository) are rewritten: that version's summary and Tables 1 to 10 are repeated word for word in this file.
- `RESULTS_PUBLIC.md`: the section "Ajout du 13 novembre 2026 / Addition of 13 November 2026" (Table 18, word-level precision, recall and F1 of the public rows; deviation D31), the words "D31 pour la Table 18" in the opening paragraph, one paragraph after it and the D31 row of the deviations table were added to this public copy after the extract was made (2026-11-13). No other change.
- `PROTOCOL.md`: the name of the cloud VM, its cloud project and a VM account name are left out (3 places).
- `PROTOCOL.md`: internal work-folder paths written as `<work>/` (8 places).
- `PROTOCOL_ADDENDUM_1.md`: internal work-folder paths written as `<work>/` (4 places).
- `PROTOCOL_ADDENDUM_4.md`: every mention of an internal row, of its addendum, its files, its hash list and its folders is replaced by "the internal row" or left out (35 edits; two table columns about that row removed).
- `PROTOCOL_ADDENDUM_4.md`: internal work-folder paths written as `<work>/` (46 places).
- `DEVIATIONS.md`: the Windows account name of the owner on the VM is written `<owner account>` (4 places).
- `DEVIATIONS.md`: entries D25, D26, D27 and D29 (internal additions) and their table rows are left out.
- `DEVIATIONS.md`: entries D30 and D31 (2026-11-13, the home page of the site and the word-level F1 table) and their table rows were added to this public copy after the extract was made; the note at the top of the file says so.
- `DEVIATIONS.md`: D1: the work e-mail address is left out; the Windows user folder is written `%USERPROFILE%` (also in D10).
- `DEVIATIONS.md`: D17 finding 3 and D18: the Tonic counts and the per-set Tonic claim are left out (Tonic's terms).
- `DEVIATIONS.md`: D3: the path of the local key file and how the key was passed are left out.
- `DEVIATIONS.md`: D28: every mention of the internal row, its hash list and its bundle files is replaced by "the internal row"; the name of an internal summary file is left out.
- `DEVIATIONS.md`: internal work-folder paths written as `<work>/` (43 places).
- `score_text.py`: internal work-folder paths written as `<work>/` (3 places).

`<work>/` stands for the internal work folder of the study (inputs, outputs, scores and logs, not published).

## What is not published

- The frozen originals of the changed files and the hash lists of the freezes (`PREREG*.sha256`) are kept private.
  The public results file quotes the hash of `PREREG.sha256` and of `PREREG_DATA.sha256`.
- Protocol addendum 2 (an exploratory F1 reading added after the runs, deviation D25) and addendum 3 (an internal
  row, deviations D26 and D27) are internal additions. Since 2026-11-13 (deviation D31), Table 18 of the public results
  file gives the set-level word-level precision, recall and F1 of the public rows on four sets. The text of addendum 2,
  its script, its per-document files and its values for the other rows stay private. The public results file does not
  use addendum 3.
- The tool outputs, the per-document scores and the sealed competitor files (protocol section 13).
- The data sets: the public sources are named in the "Data" table of `RESULTS_PUBLIC.md`.
