# Protocol addendum 4 (section 20): rows S-R4 and S-N4, Shield 0.4.0

> **Public extract (2026-11-12): entries about an internal row are left out.** This is not the frozen file. The changes are listed in `PUBLIC_EXTRACT.md`. The frozen original and its SHA-256 are kept private.

Version 1.1, 2026-11-11. Status: FROZEN at 2026-11-11T09:04:25Z by `evaluation/laptop/PREREG_V04.sha256` (20.16).
Version 1.0 was the draft of 2026-11-10, 17:13Z to 17:45Z (SHA-256 `459fe7d5...d814`; kept as
`<work>/v04_run/PROTOCOL_ADDENDUM_4.v1.0_draft.md`). Version 1.1 applies the findings of the two critics
(fairness and status honesty; correctness and runnability; section 20.17). Both versions were written before any
output of Shield 0.4.0 on a laptop set through the head-to-head runner existed (20.0, "Checks at the time of
writing" and "Checks at the freeze").

`PROTOCOL.md` (v1.0), `PROTOCOL_ADDENDUM_1.md` (v1.1, section 17), `PROTOCOL_ADDENDUM_2.md` (section 18),
`PROTOCOL_ADDENDUM_3.md` (v1.1, section 19; about an internal row, not published), the frozen scorer `score_text.py` (`laptop-score-1.1`), the readers
(`laptop-extract-1.1`), `compare_runs.py` (1.1), `score_f1.py` (`laptop-f1-1.0`) and the runner
`run_shield_files.py` are not changed by this addendum. It adds two rows. Where it and sections 1 to 19 seem to
differ, the earlier sections apply, except the four points marked "replaces": the set status for these rows
(20.3), the words "held-out Judilibre draw" of 11.3 for these rows (20.3.4), the wording of the overall claim, with
its row-level breakdown (20.9), and the speed claim across sessions (20.6).

Time zones: all times here are UTC ("Z"). Paris has been on CET (UTC+1) since 2026-10-25 03:00.

## 20.0 Status, in plain words

- **Added on 2026-11-10, at the owner's request** (launch preparation of Shield 0.4.0). `PROTOCOL.md` section 2
  allows it: "A later Shield build may be run on the same files as a SEPARATE, labelled row; it never replaces the
  frozen row, and it never sees a competitor output (section 13)."
- **Shield 0.4.0 was built after the results of this head-to-head were known.** The first scores of every row
  date from 2026-10-25, about 09:45Z (D16). Nine of the ten accepted steps of the 0.4.0 work, and three commits of
  the desktop installer work that are also in the wheel, were committed after that time (20.3.1). These rows are a
  second attempt by one of the tools. The rules of the measurement are fixed
  here before the attempt is measured, but the team changed the tool after it saw the first results. Every table,
  every claim and every public sentence about these rows says so.
- **No set is held-out for the 0.4.0 rows** (20.3.4). Four sets were development data or gates of the 0.4.0 work.
  For REF and for the fresh Judilibre draw, the records show no use by the 0.4.0 work, but nothing proves it, and
  the 0.3.1 results on both sets were known while 0.4.0 was built.
- **The competitor rows are not run again.** H-F and H-P (Hexagone 0.3.9, measured 2026-10-24 and 25; the trial
  ended on 2026-10-31 and the app is never opened again), T (Tonic Textual cloud, SDK 3.24.0, run after D3 of
  2026-10-24 and before the scoring of 2026-10-25), P (Presidio 2.2.364, 2026-10-25) and an internal row (2026-10-26; left out of this public extract) keep their
  sealed outputs and scores. These tools may have newer versions today. The
  comparison is Shield of November against the other tools of October (20.14, limit 2).
- **The 0.3.1 rows S-R and S-N stay as measured.** They are not replaced, not run again and not scored again.
- **What the author read.** `RESULTS.md` (the set-level tables of every row), as the task for this addendum asked,
  the run tables of the Shield 0.3.1 session (`runs/shield_A/`: times, memory, logs) and the results pages of the
  0.4.0 work on its own benchmarks. No file under `<work>/sealed/` was opened; folder and file names
  there were listed to write the list of comparisons (20.8), and the 50-line gold subset of D23 was hashed. A
  counts-only scan read the gold of REF and of the fresh Judilibre draw and the text of the REF files and of the
  fresh decisions; a scan of the local agent transcripts printed commands and file names (20.3.3). Neither printed
  a gold value, an output text or a score. Consequence: the rules below were written by someone who knew the 0.3.1 and
  competitor results. 20.14, limit 8, lists the choices where this matters. No rule here depends on a 0.4.0 result:
  none exists.
- **No result of a 0.4.0 row is in this file:** none exists. No P1, P2, F1, speed or memory value of any row is
  here. Limit 8 of 20.14 names one claim direction of the 0.3.1 rows (a public one, in `RESULTS_PUBLIC.md`),
  because the choice about the verdict unit must be read with it. 20.6 names the three speed claims of Table 8.
- **Internal and public.** Tonic numbers and the numbers of the internal row stay internal (4.3, 19.2). The Shield 0.4.0 numbers are
  ours. Hadi decides on every publication (4.3). 20.13 says what a public file must carry.

Checks at the time of writing (2026-11-10):

| Check | Result |
|---|---|
| `shasum -a 256 -c` on `PREREG.sha256`, `PREREG_DATA.sha256`, `PREREG_F1.sha256`, the hash list of the internal row (17:13:18Z, and again at 17:46:08Z) | 685 of 685, 829 of 829, 4 of 4, 4 of 4 OK, both times |
| `evaluation/laptop/VM_BUSY` | absent |
| `<work>/runs/shield_A_v04`, `scores/S-R4`, `scores/S-N4`, `f1/S-R4`, `f1/S-N4`, `sealed/scores/compare_v04`, `sealed/f1/bundle_v04`, `bundle_v040` (17:36:32Z) | all absent |
| `C:/shield_v04` on the VM (read-only query, 17:27:40Z; `v04_run/status_facts/vm_state_20261110T172740Z.txt`) | absent. `C:/shield`, `C:/shield/models`, `C:/bench/in`, `C:/shieldrun` present. VM booted 17:11:59Z |
| Shield 0.4.0 outputs on the same documents made by OTHER runners | exist since 2026-11-07 for FR-PII-Bench, MAPA, Max and PrivacyBench (the benchmarks' own runners and scorers, 20.3.5). None for REF. None for the fresh Judilibre draw |

Checks at the freeze (2026-11-11):

| Check | Result |
|---|---|
| `shasum -a 256 -c` on the four earlier hash lists (08:36:34Z, and again at 2026-11-11T09:04:24Z, right before the freeze) | 685 of 685, 829 of 829, 4 of 4, 4 of 4 OK, both times |
| The same lists, by the two critics (2026-11-10 17:47Z and 2026-11-11 08:33Z to 08:35Z) | the same counts; `status_facts/SHA256SUMS` 7 of 7 OK |
| `evaluation/laptop/VM_BUSY` | absent at every check of the freeze stage |
| `runs/shield_A_v04`, `scores/S-R4`, `scores/S-N4`, `f1/S-R4`, `f1/S-N4`, `sealed/scores/compare_v04`, `sealed/f1/bundle_v04`, and any file named `*S-R4*`, `*S-N4*` or `*no_xlsx*` under `scores/` and `sealed/scores/` (08:39:59Z, and again right before the freeze) | all absent |
| `C:/shield_v04` on the VM (read-only queries, 08:39:06Z, 08:59:08Z and 09:04:18Z) | absent; no process with `shield_v04` in its command line; 0 files under `C:/shield` and `C:/bench` written since the boot of 2026-11-10T17:11:59Z (query of 08:48:40Z) |
| VM load (read-only, 08:48:27Z, 5 samples of one second) | 0 processes of another stage, 0 Hexagone processes, 0 user sessions (`quser`), CPU load 0.9 %, free RAM about 12.6 GB |
| What the freeze stage did on the VM | read-only queries; an in-memory syntax check and a read-only trial of its helper scripts; a copy of five small script files of D15 from `C:/shieldrun/code` to the Mac. Nothing was written on the VM. No Shield process was started |

## 20.1 The systems (adds two rows to section 2)

| Row | System and mode | Version rule | Where it runs | Settings (section 6) |
|---|---|---|---|---|
| S-R4 | RAGbase Shield 0.4.0, rules mode (the product default) | commit `fd8662d120de765fc5fb65aa7bb83155e3ea18f3` (branch `v0.2-detection`, `src/` tree `c4951557`), wheel built from `git archive` of that commit; wheel SHA-256 in the wheel hash file (20.4) | the VM, profile A, locally, install folder `C:/shield_v04` | `RAGBASE_SHIELD_NER=off` |
| S-N4 | Shield 0.4.0, rules + gated GLiNER on CPU | same build; model `fastino/gliner2-privacy-filter-PII-multi` revision `1cb41660`, the same files as row S-N (`model.safetensors`, 1,228,421,964 bytes, SHA-256 `0280f6f39f6012da50b6640bad438d9b7e763a1b0102094115d1b710c4dd79b6`) | the same | `RAGBASE_SHIELD_NER=on`, `..._NER_MODEL=fastino`, `..._NER_DEVICE=cpu` |

- The rows S-R and S-N keep their names. In every table they read "Shield 0.3.1"; the new rows read "Shield 0.4.0".
- "Gated" means the product's own rules on what a model find may add to the rules. Version 0.4.0 holds one more
  such rule for English texts. It is part of the build. No setting turns it on.
- Settings: section 6, unchanged (product defaults: codes, language auto, legal form in clear, one Shield data
  folder per run, file key, no dossier title, no register, no keep-clear). Five setting names are new in 0.4.0.
  Two change what is read or masked and stay at their defaults: `RAGBASE_SHIELD_OWN_COMPANY_VENDOR` (off) and
  `RAGBASE_SHIELD_PDF_TABLES` (on). Three belong to the desktop service and tray (`RAGBASE_SHIELD_NO_TRAY`,
  `RAGBASE_SHIELD_SERVICE`, `RAGBASE_SHIELD_UI`): only files under `desk/` read them, and the runner path does not
  import `desk/` or `cli.py`. None of the five is set. The runner sets its own variables; no other
  `RAGBASE_SHIELD_*` variable exists in the environment, except `RAGBASE_SHIELD_MODELS_DIR` (the runner
  environment of D15).
- No AVX2-only row (S-N2) and no profile B for 0.4.0: this addendum has two rows on profile A.
- P4 (10.5): as rows S-R and S-N. The runner refuses outbound connections and logs every attempt; the count is
  reported for every process.

## 20.2 What is measured, what is not

| Item | Rule |
|---|---|
| Sets | the six sets of section 5, the same 798 input files (hashes in `PREREG_DATA.sha256`), the same gold, tasks and order (10.2) |
| Readers and scorer | `laptop-extract-1.1`, `laptop-score-1.1`, `compare_runs.py` 1.1: the frozen files, unchanged |
| Reported per set and row | everything of 11.1: P1 strict and value with the Wilson interval, readable anywhere, covered 80 %, per label; document properties apart; P2 per class and documents with one; dates, amounts, roles, placeholders altered; false-mask regions; words changed outside gold; failures with reasons |
| New for these rows | the paired comparison with the 0.3.1 row of the same mode, per set (20.8, 20.9) |
| Speed and memory | one REF speed session on profile A, if the VM is quiet (20.6); else "not re-measured" |
| Exploratory F1 | section 18 rules, no claim (20.10) |
| Not measured | profile B, the AVX2-only variant, the Windows against Mac parity sample of D15 (the Mac no longer runs Shield on documents: machine rule of 2026-11-03), any competitor |
| Labels on every number | the row with its version ("Shield 0.4.0"), the mode, the set status FOR 0.4.0 (20.3.4), the machine label "VM profile A, not a laptop", the session date. No 0.4.0 number gets the status "held-out" (20.3.4, consequence 2) |

## 20.3 Status of every set for the 0.4.0 rows (replaces the column "Status for Shield" of section 5 for S-R4 and S-N4)

The facts below were read in the repository and in the local records on 2026-11-10. The scripts and their outputs
are in `<work>/v04_run/status_facts/` (`repo_facts.sh`, `scan_gold.py`, `scan_transcripts.py`, and the
outputs `repo_facts.out.txt`, which holds the output of `scan_gold.py`, and `scan_transcripts.out.txt`). They print
counts and paths, never a gold value or an output text.

### 20.3.1 Timeline

| When (UTC) | Event | Source |
|---|---|---|
| 2026-10-22 | `PLAN_V04.md` written: nine steps (T1 to T9) from the misses of Shield 0.3 on the 21 PrivacyBench exports | the plan's date line; folder `<work>/gap2/plan/` of 2026-10-22 16:17Z |
| 2026-10-23 10:18 | Shield 0.3.1 committed (`577b423`) | git |
| 2026-10-23 14:07 to 14:09 | REF built; head-to-head protocol frozen (v1.0) | file times; D2 |
| 2026-10-23 14:19 | workflow script of the 0.4.0 work written (it holds the Windows step W0 and its gate) | file time of `<work>/scripts/shield-v04-ladder.js` |
| 2026-10-24 13:20 | fresh Judilibre draw | 17.7 |
| 2026-10-24 14:01 | step S0 committed (`a278e28`) | git |
| 2026-10-25 04:28 to 05:37 | rows S-R and S-N run on profile A: the first Shield runs on REF and on the fresh draw | D15 |
| 2026-10-25, about 09:10 to 09:45 | first scores of every row; first `RESULTS.md` | D16 |
| 2026-10-25 | note added to the plan by the orchestrator: "item found by the laptop head-to-head", the Max `.xlsx` file that Shield 0.3.1 could not read | `PLAN_V04.md`, addendum of 2026-10-25 |
| 2026-10-25 11:45, 13:23, 15:20, 17:56 | steps T1, T2, T3, T4 committed (`5eb39ae`, `7fff4b5`, `949f56f`, `531a936`) | git |
| 2026-10-25, about 21:30 | step 2 scores (Hexagone Precis on all sets) | D23 |
| 2026-10-26 | step T5 committed 09:05 (`f0fc3d7`); an internal row added and scored; plan amendment A1 (a rule for near misses of a gate) | git; an internal entry; the plan |
| 2026-10-27 09:19 | commit `0ecb28a` of the desktop installer work (not a step of the 0.4.0 work): `cli.py` and `desk/` | git |
| 2026-10-31 | the Hexagone trial ended | D16 |
| 2026-11-03 19:36, 20:37 | commits `034d607` and `4a3c1ad` of the desktop installer work: `cli.py` and `desk/` | git |
| 2026-11-06 19:00, 21:15, 22:45 | steps T8, T9, P1 committed (`a004885`, `29cd4b1`, `be7c4c3`) | git |
| 2026-11-07 00:23 | step W0 committed (`321e05f`): the last change to the code of `src/` | git |
| 2026-11-07 | the finished build measured on PrivacyBench, FR-PII-Bench, MAPA, the old Judilibre draw, Max static and holdout-en | `<work>/v04/steps/` |
| 2026-11-10 17:02 to 17:08 | those result pages and the version string 0.4.0 committed (`a5f5932`, `f32af9b`, `fd8662d`) | git |

Ten steps were accepted (S0, T1 to T5, T8, T9, P1, W0); four were rejected (the first W0, T6, T7, T6 with T7). Only
S0 was committed before the first scores. Three more commits, of the desktop installer work, change `src/` and are
in the wheel: `0ecb28a` (2026-10-27 09:19Z), `034d607` (2026-11-03 19:36Z) and `4a3c1ad` (2026-11-03 20:37Z). They
change `cli.py` and `desk/` only (no engine file, no reader); the runner does not import these files. So 13 commits
change `src/` after 0.3.1 (S0, T2 to T5, T8, T9, P1, W0, the three installer commits and the version string commit
`f32af9b`; T1 changes no file of `src/`), and 12 of them came after the first scores. The sessions of the three
installer commits are not among the 122 sessions of 20.3.3. Critic 1 checked the sessions outside the 0.4.0 work
that edited `src/` or `tests/` (5 sessions: 2 of 2026-10-23, before the laptop sets existed, and 3 installer
sessions of 2026-10-27 and 2026-11-03): 0 calls read a head-to-head data path or `C:/shieldrun`; 4 calls name
`C:\bench` as deny-list text of the installer test. That check does not see edits made by shell commands, or
sessions still open after 2026-11-10 11:00Z. The plan and its nine detection steps were written before the laptop
sets existed (REF: 2026-10-23; fresh draw: 2026-10-24). What was added to the plan after the first scores: the
`.xlsx` note, amendment A1, and the choices each step made under its gates.

### 20.3.2 What the 0.4.0 work used

Source: the harness `<work>/v04/measure.sh` (what it runs at every step), `PLAN_V04.md` sections 2.4, 3 and
6.1 (the gates), the 46 step reports.

| Data | Role in the 0.4.0 work | Laptop set concerned |
|---|---|---|
| PrivacyBench v2.5, all 21 exports | development set: the steps were built from its miss lists and measured on it at every step | English: 241 e-mail bodies of 2 of these 21 exports |
| FR-PII-Bench v0, 300 documents | regression gate at every step (precision, false masks, recall, round trip not worse than 0.3) | FR-PII-Bench: the same 300 documents |
| MAPA, 19 decisions | regression gate at every step (mask precision not worse than 0.3) | MAPA: the same 19 decisions |
| Judilibre, the OLD draw of 200 | regression gate at every step (must-stay-clear masks not more than 0.3) | none. The fresh draw has the same source and strata and shares 0 of 200 decisions with the old draw |
| Max corpus, matters A to G | audit at every step (no Max gold value in an added code line); the workbook of matter D opened by the builders and the checker of T8 to check the new reader; one full "Max static" run of the finished build (2026-11-07) | Max: 33 files of that corpus |
| holdout-en | guard against overfitting at every step. Written by the Shield team; not held-out | none (section 5.4) |

By the step reports and the language tests in the code, steps T2 to T5, the identifier rules of T8 and step T9 act
on English texts only. T1 changes a benchmark adapter, not the product. P1 is an option that ships off. Code of
0.4.0 that also runs on French files: the new `.xlsx` reader and the reading of
ruled PDF tables (T8, `documents.py`), a sentence rule at a table cell start (T8), the synthetic-mode changes of S0
(not used here: the rows run in codes mode) and W0 (no engine file).

### 20.3.3 REF, the fresh Judilibre draw and the per-document results: what the records show

| Check | Result |
|---|---|
| Lines of the harness, its library, the 46 step reports, the 13 rejected diffs, the plan and the 6 workflow scripts of the 0.4.0 work that name a path of the laptop sets, of the fresh draw, of Shield's laptop runs or scores, of the sealed folder or of the results files | 2 lines. Both are the `.gitignore` entry `evaluation/laptop/RESULTS.md`, seen in a `git diff`. No read |
| The plan | 1 note names the head-to-head: the `.xlsx` item of 2026-10-25 |
| Lines added to `src/` and `tests/` since 0.3.1 that name the laptop folder, a sealed folder or a competitor | 5 lines: a comment of `cli.py` that cites `WINDOWS_SETUP.md`, and 4 lines of the packaging tests that forbid `C:\bench`, `C:\shield` and Hexagone to the installer test |
| REF gold against the 9,702 lines added to `src/`, `tests/`, the docs and the benchmark runners since 0.3.1 | 0 of 390 gold strings of 6 or more characters; 0 of 85 generated surnames; 0 of 22 first words of company names; 0 shared runs of 6 words with the 5 files |
| Fresh Judilibre draw against the same lines | 0 of 330 gold names of 2 or more words; 0 shared runs of 6 words with the 200 decisions |
| Local transcripts of the agents that did the 0.4.0 work: 122 builder, checker and benchmark sessions, 2026-10-23 to 2026-11-07 | commands that name a path of the laptop sets, the fresh draw, Shield's laptop runs or scores, the sealed folder, the results file or `C:/bench`: 0. Search hits inside a laptop file: 0 |
| File names of head-to-head data seen in those sessions | 4 sessions (T8, on 2026-10-26, 11-03 twice, 11-06) ran a `find` for the Max workbook; the listing showed the names of its copies under `sets/max/`, the input folder of the internal row and `sealed/` (Presidio, Tonic and Hexagone output names of that one file). Names only; no file opened |
| What those sessions did read in the laptop folders | folder listings of `evaluation/laptop/` and `<work>/` (names); the Windows setup notes, the Windows test logs and the package list of 0.3.1, the 0.3.1 wheel; the runner script (to see its reader path); the first 20 and the last lines of `RUNSHEET_HEXAGONE.csv` and the last 1,200 characters of `DEVIATIONS.md` (the W0 builder, 2026-10-25 before 09:53Z, to know when the VM was free); whether `results/shield_profileA.md` and `VM_BUSY` existed |
| Task prompts of the 122 sessions | one head-to-head finding was passed on: "fix the .xlsx read gap" (10 prompts). The other sentences that name the head-to-head say: do not edit `evaluation/laptop/`, do not touch `C:/shield` or Hexagone, wait while `VM_BUSY` exists |
| The orchestrator | 3 main sessions ran both the head-to-head and the 0.4.0 work. They read the head-to-head results and handled the sealed folders (listings, run logs). They wrote the prompts above. They are not steps, but they are a possible channel |

Limits of these checks. (1) There is no access log and no technical barrier: the 0.4.0 agents were told not to
edit `evaluation/laptop/`; no rule told them not to read the sets. Section 13 and D7 forbid only the sealed folder
to a session that works on `src/` or `tests/`. (2) The transcript scan finds a path only when the command text
holds the word "laptop" or "sealed", or when a result prints a laptop file name. It reads the calls of Bash, Read,
Grep and Glob only (the 122 sessions also made 46 Monitor calls), and its pattern holds no VM path other than
`C:/bench`. A wider check by critic 1 (every tool, `C:/shieldrun` added, upper and lower case) found 0 more reads:
11 more calls match, and all 11 name the run report folder `evaluation/laptop/results/` or the text of the
`.gitignore` line. (3) Shield's own outputs and
per-document score files on all six sets are not sealed (section 13): they lay readable on the Mac from 2026-10-25.
(4) The owner and the orchestrator knew the set-level results of the 0.3.1 rows on every set, with the per-label
counts of what Shield missed, from 2026-10-25.

### 20.3.4 Status labels for the 0.4.0 rows

"Held-out" is used only when it is proven that neither the set nor a result on it could reach the build. That
is true for no set here.

| Set | Status for S-R4 and S-N4 | Short label for tables | Status for the competitor rows (unchanged) |
|---|---|---|---|
| REF | written by the Shield team; not independent. Scored with Shield 0.3.1 on 2026-10-25, and the misses per label were known while 0.4.0 was built. No record shows that the 0.4.0 work read the files, the gold, Shield's outputs or its scores. Not proven | not held-out: team-written, 0.3.1 results known; unused by record | new to every competitor |
| FR-PII-Bench | informed, and a regression gate of the 0.4.0 work at every step | gate | not seen by the competitors, as far as we know |
| MAPA | informed, and a regression gate of the 0.4.0 work at every step | gate | the same |
| Max, matters A to G | informed; audited at every step; run in full with the finished build on 2026-11-07; and one failure that THIS head-to-head found (the `.xlsx` workbook of matter D) was fixed in 0.4.0 | gate, with a fix from this study | the same |
| Judilibre fresh draw | not used by the 0.4.0 work according to every record (20.3.3); not proven. The 0.3.1 results on it were known. The old draw of the same source and strata was a gate at every step, on the same kind of measure (must-stay-clear masks) | not held-out: 0.3.1 results known, same-source gate; unused by record | held-out |
| English | informed: part of the development set of the 0.4.0 work (its steps were built from the misses on these exports) | development set (in-sample) | PrivacyBench is Tonic's own benchmark; Hexagone and Tonic publish numbers on it |

Consequences. (1) This replaces the words "the held-out Judilibre draw" of 11.3 for the 0.4.0 rows: a 0.4.0 claim
reads "the fresh Judilibre draw (held-out for the other tool; not held-out for Shield 0.4.0: 0.3.1 results known,
same-source gate; unused by record)". (2) No sentence, table cell, column head, row label or caption gives a 0.4.0
number the status "held-out", or "invented" without "results known". A table that holds a 0.4.0 row with other rows
has a status column per row, or a set label with both statuses ("held-out for the other tools; not held-out for
Shield 0.4.0"). The existing tables of `RESULTS.md` and `RESULTS_PUBLIC.md` do not get 0.4.0 rows. (3) A held-out
number for 0.4.0 needs a new draw made after the wheel is frozen. That is not part of this addendum, and Hexagone
could not be run on it.

### 20.3.5 What is already known about 0.4.0 on these documents

The 0.4.0 work measured the finished build on its own benchmarks on 2026-11-07, with the benchmarks' own runners
and scorers (not the head-to-head runner, not the folder condition of 9.1, not the frozen scorer). The pages are
committed (`a5f5932`):

| Benchmark of the 0.4.0 work | Page | Laptop set with the same documents |
|---|---|---|
| PrivacyBench v2.5, 21 exports | `evaluation/public/privacybench/RESULTS_V04.md` | English |
| FR-PII-Bench | `evaluation/public/fr-pii-bench/RESULTS_V04.md` | FR-PII-Bench |
| MAPA | `evaluation/public/mapa-fr-cassation/RESULTS_V04.md` | MAPA |
| Max static, matters A to G | `evaluation/max-protocol/results/V04-static/` | Max |
| Judilibre, old draw | `evaluation/public/judilibre/RESULTS_V04.md` | none |
| holdout-en | `evaluation/holdout-en/RESULTS_V04.md` | none |

The gates of the 0.4.0 work also required that the French rules-mode outputs (FR-PII-Bench, MAPA, the old
Judilibre draw) stayed unchanged against 0.3.1 for the steps gated to English. So the team does not come to these
rows blind: the direction of the difference between 0.4.0 and 0.3.1 on four sets is largely known before the run.
The numbers are in those pages and are not repeated here. Nothing of the kind exists for REF or for the fresh draw.

## 20.4 Build, install and inputs (applies section 9.1, step 1, to version 0.4.0)

### The build (freeze stage, on the Mac; a wheel build is light)

| Item | Value |
|---|---|
| Commit | `fd8662d120de765fc5fb65aa7bb83155e3ea18f3`, branch `v0.2-detection`, 2026-11-10T17:08:51Z |
| Why this commit | `f32af9b` sets the version string 0.4.0; `fd8662d` corrects result pages only. Its `src/` differs from the last step of the 0.4.0 work (`321e05f`) in one line, the version string. The two later commits at the time of writing (`5cf1d41`, `49aa899`) change packaging documents only: no file that enters the wheel |
| `src/` tree | `c495155749767e126484516274c4829e3a5181d2`; 62 files under `src/ragbase_shield`, 29 of them `.py` |
| Package hash | `fb4288ba478aab536b66e75536d3b1386d82302f1703d9e116d98e5412a8526c`: the SHA-256 over the sorted `.py` files that the frozen runner writes in every `run_meta.json` (`package_hash()`). Computed on 2026-11-10 from a `git archive` of the commit. The same function on `577b423` gives `250f2178...6779`, the value in the 0.3.1 run records (check of the method) |
| Build command | `git archive fd8662d120de765fc5fb65aa7bb83155e3ea18f3` unpacked into an empty scratch folder, then `uv build --wheel` there (hatchling, as `pyproject.toml` says; the tool that built the 0.3.1 wheel). Not the working tree. Done twice, from two fresh exports: the two wheels must have the same SHA-256, else the freeze stops. Done at the freeze: uv 0.6.2, hatchling 1.33.0, 2026-11-11T08:38:15Z to 08:38:17Z; the two wheels are byte-identical (573,379 bytes) |
| Wheel | `<work>/bundle_v040/ragbase_shield-0.4.0-py3-none-any.whl` |
| Wheel hash file | `<work>/bundle_v040/ragbase_shield-0.4.0-py3-none-any.whl.sha256`: comment lines (`#`: commit, `src/` tree, package hash, uv and hatchling versions, build time UTC, size in bytes) and one `shasum -a 256` line with the wheel path relative to the repository root. Check from the root: `shasum -a 256 -c <work>/bundle_v040/ragbase_shield-0.4.0-py3-none-any.whl.sha256` |
| Wheel SHA-256 | `01404cd3d6cb321f56ae6629a5b9d62af152b1778790ffd130fb120ed4bd85b9` (the same value as in the wheel hash file; critic 2 got the same value from two builds of his own) |
| Checks at the freeze | the files under `ragbase_shield/` in the wheel are the 62 files of the commit, byte for byte; `package_hash()` over the wheel's `.py` files equals the package hash above; `METADATA` says `Version: 0.4.0`; `git diff --quiet fd8662d <HEAD at the freeze> -- src pyproject.toml README.md LICENSE NOTICE` (exit 0 expected; if not, the row is still the named commit, and the difference is written in D28). Result at the freeze: 62 of 62 files byte-equal and no other file under `ragbase_shield/`; 6 `dist-info` entries; package hash equal, on the export and on the wheel; `Version: 0.4.0`; `git diff --quiet` exit 0 with HEAD `49aa899` |

One build only. The rows are this wheel or nothing. If a commit that changes `src/` must enter before the freeze,
the commit, the tree and the package hash of this table are changed in a new version of this addendum, before the
freeze. After the freeze no other build enters these rows: a later build is a new row under a new addendum.

### Install on the VM (run stage; `C:/shield` is never written)

| Step | Action | Check written in `RUN_NOTES.md` |
|---|---|---|
| I1 | `evaluation/laptop/VM_BUSY` must be absent; machine facts with `windows/machine_facts.ps1`. The run stage tests `VM_BUSY` again before every VM command of I2 to I10 and of the pilot: if the file exists and is not its own, it waits | the facts file; the six items of 20.6 |
| I2 | create `C:/shield_v04` with `code/`, `dist/`, `tasks/`, `sets/`, `runs/`, `logs/`. `C:/shield`, `C:/bench`, `C:/shieldrun`, `C:/shield_pkg`, `C:/shield_dev`, `C:/presidio` are not written | the folder did not exist before (if it does: an earlier try, 20.12) |
| I3 | copy the wheel to `C:/shield_v04/dist/`; `Get-FileHash` | equal to the frozen SHA-256 |
| I4 | new venv: `C:/Program/python.exe -m venv C:/shield_v04/.venv` (Python 3.11.9, as row S-R) | version line |
| I5 | dependencies pinned to the versions of the 0.3.1 venv: every line of `<work>/vm_logs3/pip_freeze_577b423.txt` (the frozen pin list: 80 lines, UTF-8 with a BOM and CRLF, SHA-256 `abb4a823...9004`, listed in `PREREG_V04.sha256`) except the `ragbase-shield` line. pip and setuptools are set to the pinned versions with `python -m pip install`. torch (the one line with a `+cpu` version) comes from the PyTorch CPU index (`https://download.pytorch.org/whl/cpu`), every other line from PyPI (the sources of the 0.3.1 venv), with `--no-deps`: the list is a full freeze. First a fresh `pip freeze --all` of `C:/shield/.venv` is taken read-only (`PYTHONDONTWRITEBYTECODE=1`) and compared with the pin list, after the BOM and CR are removed | the two lists are equal; else the fresh list is the pin list, and the difference and the SHA-256 of the fresh list are written in D28 before the first run |
| I6 | `pip install --no-deps` of the wheel; `pip check` | `pip check` clean |
| I7 | `pip freeze --all` of the new venv against the pin list | equal except the `ragbase-shield` line. Any other difference is written before the first run. A difference in torch, transformers, gliner2, gliner, tokenizers, numpy, safetensors, pypdf, pdfplumber, pdfminer.six, python-docx or lxml stops the run stage until it is fixed (operator matter, 12.2) |
| I8 | installed files against the wheel (as D15): every file of the installed `ragbase_shield/` equals the wheel's own bytes | 62 of 62 equal; no other file under `ragbase_shield/` except `__pycache__`; no patch (the W1 to W4 patches of D8 are not applied; the Windows fixes are in the 0.4.0 code) |
| I9 | model: `RAGBASE_SHIELD_MODELS_DIR=C:/shield/models`, read only, the folder of row S-N. `Get-FileHash` of the fastino `model.safetensors` on its snapshot path (it follows the link). The size is read on the link target under `blobs/`, or through an open file handle, which follows the link: the snapshot entry is a symbolic link and reports 0 bytes | SHA-256 and size of 20.1 |
| I10 | code: `run_shield_files.py`, `windows/machine_facts.ps1`, `windows/sample_memory.ps1` copied to `C:/shield_v04/code/`, with the operator scripts of 20.5 | the hashes of the three frozen files equal `PREREG.sha256`; the hashes of the operator scripts as copied are written to `logs/` |

Order in practice: the copies of I3 and I10, the pin list and the seven `tasks.json` files go to the VM in one step
after I2, because the install checks use the copied tools. The checks are those of the table.

### Inputs (as D15)

The runner needs `<set>/tasks.json` and `<set>/input/<file>`. The seven folders (six sets and PILOT) are built in
`C:/shield_v04/sets/` from `C:/bench/in/<set>/<task>/` (read only) and from the `tasks.json` of the Mac set
folders (copied to `C:/shield_v04/tasks/`). Before any run, each of the 798 input files (and the 2 PILOT files) is
hashed twice, in `C:/bench/in` and in the copy, and each `tasks.json` once: every hash equals
`PREREG_DATA.sha256`. One difference stops the run stage.

## 20.5 Runs (applies section 9.1, step 2)

- **Pilot first (unscored, as on day 0 of 10.1).** Both modes on the PILOT set into `C:/shield_v04/runs/pilot/`.
  It checks the install: exit 0, the right `shield_version` (0.4.0), `shield_package_sha256` (20.4) and
  `engine_mode` (`rules`; `rules+ner:gliner2:fastino`), 0 network attempts. PILOT is not one of the six sets and
  is never scored. If the pilot fails for an install reason, the install is fixed and the pilot repeated (12.2);
  no set is touched before the pilot passes. If it fails because the 0.4.0 wheel does not work on Windows, the
  run stage stops and reports (20.12).
- **Order (10.2, and the order of D15):** REF, FR-PII-Bench, MAPA, Max (A to G), Judilibre fresh, English. For each
  set: rules, then ner. One process per row and set (12 processes). Then the speed processes (20.6). One process at
  a time.
- **Commands** (PowerShell on the VM; `PY` = `C:/shield_v04/.venv/Scripts/python.exe`, `RUN` =
  `C:/shield_v04/code/run_shield_files.py`, `<set>` in `ref`, `frpii`, `mapa`, `max`, `judilibre`, `en`):

```
$env:RAGBASE_SHIELD_MODELS_DIR = 'C:/shield/models'; $env:PYTHONUTF8 = '1'
$env:SHIELD_COMMIT = 'fd8662d120de765fc5fb65aa7bb83155e3ea18f3'
& $PY $RUN --set-dir C:/shield_v04/sets/<set> --out C:/shield_v04/runs/shield_rules/<set> --mode rules
& $PY $RUN --set-dir C:/shield_v04/sets/<set> --out C:/shield_v04/runs/shield_ner/<set> --mode ner
```

- **Environment.** Before the driver starts, every inherited `RAGBASE_SHIELD_*` variable is removed and the three
  variables above are set (the driver writes the models folder as `C:\shield\models`, the form of the D15 driver;
  it is the same folder). `SHIELD_COMMIT` only fills a field of `run_meta.json` (as for row S-R). The runner sets
  the mode variables, a fresh Shield home per process and the file key itself (section 6). The AVX2 variables of
  row S-N2 are not set. No `--tasks`, no `--repeat`, no `--allow-network`.
- **Folder condition:** unchanged (each task of `tasks.json` is one dossier; 14.3).
- **Driver.** One PowerShell driver in `C:/shield_v04/code/`, started through WMI so that a dropped SSH session
  cannot stop it (D15). It writes `logs/drive.txt` (UTC start and end of each process, exit code, wall time),
  `logs/runs.csv`, `logs/machine_state.csv` (before and after each process: CPU load, free RAM, and the count,
  working set and CPU time of any Hexagone or `llama-server` process), the stdout and stderr of each process and
  the memory samples (20.6). The run stage waits by reading `logs/drive.txt`.
- **Operator scripts.** The driver, the set builder and the install audit are copies of
  `C:/shieldrun/code/drive.ps1`, `prep_sets.py` and `audit_wheel.py` of D15 (read only there), with the base folder
  changed to `C:/shield_v04`, the Presidio and S-N2 parts removed and the checks of this section added. The freeze
  stage prepared them, with the other helper scripts of the run, under `<work>/v04_run/ops/`
  (`drive_v04.ps1`, `prep_sets_v04.py`, `audit_wheel.py`, which is unchanged, and the scripts that `RUN_PLAN.md`
  names). They are operator tooling, not frozen, and not yet run on a set: the pilot is their test. A fault found
  in one of them is an operator matter (12.2, 20.12): it is fixed with a note in `RUN_NOTES.md`. The copies that
  ran and their SHA-256 go to `logs/`. No two variable names of the driver differ only by case (the operator error
  of D15, attempt 1). The driver writes the list of `RAGBASE_SHIELD_*` variables before each process to
  `logs/env/`: the runner's `run_meta.json` does not record the two new settings. It refuses to start a process
  whose output folder exists.
- **Each process writes into a folder that does not exist yet.** The runner appends to its run log, so a second
  process in the same folder would mix two runs. A re-run (20.12) uses a new folder name.
- **Hexagone.** The app is never opened. If one of its processes is found running, it is not touched; its count,
  memory and CPU time are logged as on 2026-10-25, and the fact is a stated condition of the session.
- **The VM** is not stopped, restarted or resized by any stage of these rows.

## 20.6 Speed and memory (applies section 9.1, step 3, and sections 10.3 and 10.4, as D15 did for rows S-R and S-N)

**Quiet VM.** The driver starts only when all of this holds:

| # | Condition | How |
|---|---|---|
| Q1 | `evaluation/laptop/VM_BUSY` was absent; the run stage then writes it (one line: who, UTC time) and deletes it after the last process | file on the Mac |
| Q2 | no process of another stage on the VM | the process list holds no `python`, `msiexec`, `dotnet`, `wix`, `candle`, `light`, `MSBuild` or `node` process, and no `RAGbase Shield` process (the supervisor that the installer test of another stage starts). The eight names are matched at the start of the process name, so `pythonw` is included; `RAGbase Shield` is matched anywhere in the name |
| Q3 | total CPU load at or under 10 % (mean of 30 samples, one per second). 10 % is the highest load logged before a Shield process in the session of 2026-10-25 | `Get-Counter` |

If Q2 or Q3 fails, the run stage waits 60 s and checks again, for 30 minutes at most. `VM_BUSY` stays in place
during the wait, so that no stage starts new work. Then:

- **Quiet:** one driver run: the 12 processes of 20.5, then the speed processes below.
- **Not quiet after 30 minutes:** the 12 processes of 20.5 run (their outputs do not depend on the load; their
  times get the label "VM not quiet"), the speed processes do NOT run, and speed and memory of 0.4.0 read "not
  re-measured". What was running is written in `RUN_NOTES.md`.

**Speed processes** (the same file set and repetitions as rows S-R and S-N in D15): three separate processes per
row on the five REF tasks, S-R4 first, then S-N4:

```
& $PY $RUN --set-dir C:/shield_v04/sets/ref --out C:/shield_v04/runs/speed/S-R4/p1 --mode rules     (then p2, p3)
& $PY $RUN --set-dir C:/shield_v04/sets/ref --out C:/shield_v04/runs/speed/S-N4/p1 --mode ner       (then p2, p3)
```

| Value | Rule (10.3, D15) |
|---|---|
| Unit | one REF file = one task; `task_seconds` of the runner's `tasks_log.jsonl` |
| Values of a row | 10: the 5 REF tasks of the per-set run of 20.5 ("per-set run", the "day 1" values of 10.3) and the 5 tasks of speed process 1 ("session"). Median and range of all 10. The 10 values of processes 2 and 3 are listed as extra values |
| Cold start | `cold_seconds` of the three speed processes (process start to the end of a warm-up mask; with the model load for S-N4) |
| Characters per second | 29,383 divided by the median |
| Full-set task times | the sum of `task_seconds` per set (informative, with per-file overhead; Table 10 of `RESULTS.md`) |
| Peak memory (10.4) | the Windows `PeakWorkingSet64` of the runner process read from outside by the loop of the D15 driver (once per second in the driver file; D15 wrote "every 0.5 s"; the value is the system's own running peak), and `windows/sample_memory.ps1 -Name python -Out C:/shield_v04/logs/mem/<process>.csv` once per second (both parameters are mandatory). The runner's own value is recorded but not used (it read 0 MB in D15). Reported: REF range and the highest value over the sets, per row; free RAM at the session start |
| Dropped values | none. A timed process whose "before" CPU load is above 10 % is flagged in the table |

**Machine facts.** The speed values of 0.4.0 are printed next to values of other sessions only with both
sessions' facts. The six items compared with the session of 2026-10-25:

| Item | Value on 2026-10-25 |
|---|---|
| Machine type (`gcloud compute instances describe`, read only; "not checked" if the stage cannot read it) | `n2-custom-12-16384` |
| CPU name | `Intel(R) Xeon(R) CPU @ 2.80GHz` |
| Cores, logical processors | 6, 12 |
| RAM | 16 GB |
| OS build | 26100 |
| Power plan | High performance |

Known differences, written in every speed table: the VM was stopped and started between the sessions (boot
2026-11-10T17:11:59Z). On 2026-10-25 Hexagone ran idle in a disconnected desktop session (3 processes)
and free RAM was about 9.0 GB. On 2026-11-10 at 17:27Z no Hexagone process ran, no user session was open
and free RAM was about 13.4 GB. Less background load helps the 0.4.0 timings. The restart may have put the VM on
another host, faster or slower. We cannot measure either effect.

**Speed claims (replaces the reading of 11.3 for values of different sessions).**

1. Inside the 0.4.0 session, S-R4 against S-N4: rule 11.3 (every value of one row below every value of the other).
2. Against a row of another session (S-R, S-N, S-N2 and P of 2026-10-25; H-F and H-P of 2026-10-24 and 25): the
   values are printed side by side with their session dates. A speed claim of Table 8 of `RESULTS.md` that involves
   the 0.3.1 row of the same mode, in either direction (today: "S-R faster than H-F", "S-R faster than P",
   "Presidio faster than S-N"), is read again for the 0.4.0 row. It is repeated, in the words "still holds for
   0.4.0, measured in another session", when (a) every value of the faster row is below every value of the slower
   row (the 10 values of the 0.4.0 row; the values of Table 8 for the other row; for Hexagone in both readings,
   from the click and from the start mark) and (b) the six machine facts match. When (a) fails, the table says "the
   claim of the 0.3.1 row does not hold for the 0.4.0 values" and gives both ranges. When (b) fails, the table
   gives the values, the facts that differ and the words "the machine facts differ: the claim is not read again",
   for a claim in either direction. No NEW claim in favour of a 0.4.0 row is opened across sessions. When every
   value of a 0.4.0 row is above every value of another row, the table says so in plain words, whatever Table 8
   says. Reasons: the sessions are 16 days apart, the VM was restarted in between, the background load differs in
   favour of 0.4.0, and D15 recorded an unexplained difference between two runs of the same row on the same day.
3. No claim "0.4.0 is faster (or slower) than 0.3.1". Values side by side only.
4. H-P: no claim (its speed session is partial, D22). Tonic and the internal row: no speed (D3, 19.2).
5. Hexagone's speed, cold start and memory values stay the sealed ones of Tables 8, 9 and 11 of `RESULTS.md`.

**Not re-measured.** If the speed processes do not run or do not all finish, Tables 8 and 11 of the 0.4.0 section
say "not re-measured". The values of rows S-R and S-N stay, with the label "Shield 0.3.1, 2026-10-25". The values
that exist are listed without a median, and no speed sentence about 0.4.0 is written.

## 20.7 Run log, output folders and statuses

| On the Mac (`<work>/runs/shield_A_v04/`), a copy of `C:/shield_v04/runs` and `logs` | Content |
|---|---|
| `shield_rules/<set>/`, `shield_ner/<set>/` (`<set>` = `ref`, `frpii`, `mapa`, `max`, `judilibre`, `en`) | the runner's files: one output per document (`<input path with the extension .txt>`, UTF-8), `runlog.jsonl` (one row per document: `doc_id`, `status`, `reason`, `task`, `chars_out`, `read_seconds`), `tasks_log.jsonl` (one row per task: `task_seconds`, files, failed), `run_meta.json` (version, package hash, commit, engine mode, settings, Python, platform, `cold_seconds`, documents, `network_attempts`) |
| `speed/S-R4/p1` to `p3`, `speed/S-N4/p1` to `p3` | the same files for the REF speed processes |
| `pilot/shield_rules`, `pilot/shield_ner` | the unscored pilot |
| `logs/` | `drive.txt`, `runs.csv`, `machine_state.csv`, `mem/<process>.csv`, `env/<process>.txt` (the `RAGBASE_SHIELD_*` variables before each process), `<process>.stdout.txt` and `.stderr.txt`, the machine facts files, the two `pip freeze` lists, the install log and the install audit (I8), the input hash check, the model hash, the hashes of the operator scripts as copied, the Q1 to Q3 readings |
| `SHA256SUMS_vm.txt` | SHA-256 of every file under `C:/shield_v04/runs`, made on the VM after the last process; checked on the Mac after the copy (every file equal). Written by the venv Python (hashlib), not by PowerShell redirection: lowercase hex, two spaces, path relative to `C:/shield_v04/runs` with `/`, UTF-8 without BOM, LF line ends. Check on the Mac: `(cd <work>/runs/shield_A_v04 && shasum -a 256 -c SHA256SUMS_vm.txt)`. The copy is a zip made by Python on the VM, as `C:/shieldrun/code/pack.py` of D15 |

Run notes: `<work>/v04_run/RUN_NOTES.md` (a log, not frozen): every command, UTC time, exit code and
hash, the checks of 20.11, the Q1 to Q3 readings, every failure. Run plan: `<work>/v04_run/RUN_PLAN.md`,
written at the freeze; it repeats this addendum with the exact commands and never overrides it.

**Statuses.**

| Status | When | Counted as |
|---|---|---|
| `ok` | the runner read every page of the document and wrote its output | scored |
| `failed` | the runner's own status (Shield did not list the document, a read error, an `add_dossier` error: its reason is kept), or the scorer's rule 8 of 8.1 (no output, unreadable output, retention under 0.50) | every gold item exposed (12.1); keep items not counted as altered |
| `not_run` | not used for these rows: the tool is ours and no budget limits it. A document the runner could not give to Shield for an operator or machine reason is a matter of 12.2 (20.12) | |
| `unscorable` | cannot occur: the output is text | |

A document that Shield 0.3.1 failed on and 0.4.0 reads (or the reverse) keeps its own status in each row. The
frozen rule charges the failed side with every gold item of the document; 20.8 adds a reading without the one
document where this is already known (the Max workbook).

**Line ends.** The runner writes CRLF on Windows (D15, outcome b). The frozen reader turns them into LF. Unchanged.

**Repeat check (free, instead of the Mac parity sample).** Each row reads REF four times (the per-set run and the
three speed processes). The report gives, per row, how many of the 5 REF outputs have the same text in all four
processes. A difference is reported; the output of the per-set run stays the scored one.

**The run is closed** when both rows have a run-log row (`ok` or `failed`) for each of the 798 documents, the
speed part is done or declared "not re-measured", the copy on the Mac is checked against `SHA256SUMS_vm.txt`,
`VM_BUSY` is deleted and `RUN_NOTES.md` carries the closing time. The run stage computes no score. No score of a
0.4.0 row is computed before the run is closed. After the first score of a 0.4.0 row exists, no 0.4.0 run is
repeated, for any reason.

## 20.8 Scoring and comparisons (applies sections 11.1 and 11.2; done on the Mac, one job at a time, no parallel jobs)

From the repository root, with the venv `<work>/mac_venv_031` (the scoring venv of D16; reader
libraries as pinned), `L` = `<work>/laptop`, `<row>,<mode>` = `S-R4,rules` and `S-N4,ner`:

```
python evaluation/laptop/score_text.py score --gold $L/sets/<set>/gold.jsonl --inputs $L/sets/<set>/input \
  --outputs $L/runs/shield_A_v04/shield_<mode>/<set> --runlog $L/runs/shield_A_v04/shield_<mode>/<set>/runlog.jsonl \
  --tool <row> --json $L/scores/<row>/<set>.json --md $L/scores/<row>/<set>.md

python evaluation/laptop/compare_runs.py <A.json> <B.json> --name-a <A> --name-b <B> \
  > $L/sealed/scores/compare_v04/<set>__<A>__vs__<B>.txt
```

| Scorer jobs | Gold | Output |
|---|---|---|
| S-R4 and S-N4 on the six sets (12 jobs) | the frozen `sets/<set>/gold.jsonl` | `scores/S-R4/<set>.json`, `scores/S-N4/<set>.json` (Shield's own scores are not sealed, section 13) |
| S-R4 and S-N4 on the Judilibre Precis subset (2 jobs; the method of D23) | `sealed/scoring_op2/judilibre_p50/gold.jsonl` (the 50 lines of the frozen gold; SHA-256 `9b1d4694c77a2bb947d137eedcb568dcef1ad121fa257f8a2a40f0dd98f45b6c`) | `scores/<row>/judilibre_p50.json`. Check: the 50 per-document results equal those of the 200-document job; a difference stops the step |
| Max without the workbook (second reading, 9 jobs): S-R4, S-N4, S-R, S-N, H-F, H-P, T, P and the internal row | `v04_run/max_no_xlsx/gold.jsonl`: the 32 lines of the frozen Max gold whose `doc_id` is not `D/Pièce 9 - décompte heures sup.xlsx`, byte-identical, written at the freeze and listed in `PREREG_V04.sha256`. Each row with the output arguments of its first scoring (`scoring/score_all.sh`, `scoring/op2/score_op2.sh`, 19.8), unchanged | `scores/<row>/max_no_xlsx.json` for the four Shield rows, `sealed/scores/<row>/max_no_xlsx.json` for the others. Check: the 32 per-document results equal those of the 33-document jobs |

The scorer checks every input text against the gold hash and stops on a difference. No existing score file is
written again. The frozen scorer does not protect existing files: it overwrites, and `compare_runs.py` prints to
stdout, so a redirect overwrites too. So the score script does two things. (1) Before each job it tests that the
target files (`.json`, `.md`, the stdout and stderr files, the comparison `.txt`) do not exist, and stops if one
exists. (2) Before the first job it writes `v04_run/scores_before.sha256`: the SHA-256 of every file under
`scores/`, `sealed/scores/`, `f1/` and `sealed/f1/` (this covers the bundles of the internal additions). After the last job
`shasum -a 256 -c v04_run/scores_before.sha256` must give all OK. Jobs run one at a time. Each `compare_runs.py`
run must exit 0 and write a non-empty file; the script stops on the first failure (the tool exits 1 with an empty
stdout when the two files do not hold the same documents).

**Comparisons with the competitor rows** (62 runs; the same pairs as rows S-R and S-N have in
`sealed/scores/compare/`). A = S-R4, then A = S-N4; B and its score file:

| Set | B (file `sealed/scores/<B>/<set>.json`) | Reading |
|---|---|---|
| REF | H-F, H-P, T, P and the internal row | all primary |
| FR-PII-Bench | H-F, H-P_map, T, P | primary (H-F: the primary manifest of D12; H-P: the mapping pairs of D23) |
| FR-PII-Bench | H-F_t30, H-P_map_t30, H-P_order, H-P, H-P_t30 | sensitivity readings of D12, D17 and D23; printed, never in a verdict |
| MAPA | H-F, H-P, P | primary |
| Max | H-F, H-P, T, P and the internal row | primary, read together with the second reading on 32 documents (20.9, "Max, competitor pairs"). The limits of 19.12 are printed next to the internal row |
| Judilibre fresh (200) | H-F, P | primary |
| Judilibre Precis subset (50) | H-P | primary for H-P (9.4 H4, D23) |
| Judilibre Precis subset (50) | H-F, P | context, as D23 |
| English | H-F, H-P, T, P | primary |

Second reading, Max without the workbook (10 runs): S-R4 and S-N4 against H-F, H-P, T, P and the internal row on the 32
documents. It enters the Max claims (20.9).
Set names in the file names: `ref`, `frpii`, `mapa`, `max`, `judilibre`, `judilibre_p50`, `en`, `max_no_xlsx`.

**Comparisons between Shield rows** (21 runs):

| Pair | Sets | Use |
|---|---|---|
| S-R against S-R4 (`--name-a S-R --name-b S-R4`) | the six sets, and Max without the workbook | did 0.4.0 change protection or legal-term fidelity in rules mode (20.9) |
| S-N against S-N4 | the same seven | the same, in rules + GLiNER mode |
| S-R4 against S-N4 | the six sets and the Judilibre subset | as S-R against S-N in Table 2 of `RESULTS.md` |

All comparison outputs of this addendum go to `sealed/scores/compare_v04/` (one folder; the files between Shield
rows hold no competitor data). The secondary readings of 19.8 for the internal row on REF are printed for the new pairs as in
an internal section of `RESULTS.md`.

**Descriptive counts for 0.4.0 against 0.3.1** (no claim; counts only; from Shield's own files; headline parts,
strict reading), per set and mode:

| Count | Definition |
|---|---|
| Identical outputs | documents whose output text, read with the frozen reader, is the same in the two rows, of N |
| Gold items gained and lost | exposed with 0.3.1 and protected with 0.4.0 ("gained"); protected with 0.3.1 and exposed with 0.4.0 ("lost"); by label |
| Must-stay-clear items restored and newly altered | altered with 0.3.1 and not with 0.4.0 ("restored"); not altered with 0.3.1 and altered with 0.4.0 ("newly altered"); by class |
| Documents that change status | `failed` in one row and `ok` in the other, with the reason |

The counting script is written by the score stage and reads only the Shield score files and outputs. The
independent recount (20.11) computes the same counts on its own.

**Where the numbers go.** A new section at the end of `evaluation/laptop/RESULTS.md`: "Shield 0.4.0 rows
(addendum 4, D28)". Tables 1 to 15 and the internal sections are not edited. Every table of the new section prints, per
set, the status for 0.4.0 (short label of 20.3.4) and the sentence: "Shield 0.4.0 was built after the first
results of this comparison were known; the other tools were measured in October and not run again."

## 20.9 Claims and the verdict table (applies sections 11.3 and 17.4; the rules are not changed)

**Per-set claims** (11.3, 17.4), from the `compare_runs.py` output of each pair:

- "S-R4 (or S-N4) exposes less than X on set S" only if the whole 95 % interval of the difference is on that side
  of 0 for BOTH P1 readings, strict and value. The same for P2 ("alters fewer must-stay-clear items") and for the
  reverse claims. A claim names the row with its version, the mode, the set, the set status for 0.4.0, the machine
  label and the number of documents left out, if any (17.5).
- The claims of rows S-R and S-N in `RESULTS.md` are not changed and not repeated as 0.4.0 claims.
- **Max, competitor pairs.** A claim in favour of a 0.4.0 row on Max (P1 or P2) is made only when it holds on the
  33 documents and on the 32 documents without the workbook. When it holds only on the 33, the table says "only
  with the workbook; the reader fix came from this study" and no claim is made. A claim against a 0.4.0 row counts
  when it holds in either reading. Reason: sections 12.1 and 12.2 give no tool a second run for a document it
  failed on. The competitors keep their failed documents. Shield 0.4.0 got a reader fix from a per-document result
  of this study.

**0.4.0 against 0.3.1, per set and mode.**

| Reading | Rule |
|---|---|
| Protection changed | a P1 claim between the 0.3.1 row and the 0.4.0 row of the same mode: "0.4.0 exposes less" or "0.4.0 exposes more" |
| Legal-term fidelity changed | a P2 claim: "0.4.0 alters fewer" or "0.4.0 alters more" |
| No clear change | no claim. Written "no clear change", with the descriptive counts of 20.8 |
| Identical | every output text of the set is the same in the two rows: written "identical outputs (N of N)" |
| Max | printed twice: 33 documents (the frozen rule; the workbook that 0.3.1 failed on counts as fully exposed for 0.3.1) and 32 documents without the workbook. A Max sentence about 0.4.0 against 0.3.1 says which of the two it uses, and says that the reader fix came from this study |
| No pooled claim | no sentence "0.4.0 is better than 0.3.1 on the head-to-head". Per set and per measure only. Claims in both directions are listed with the same weight |

**Reading of Table 3 (kept).** Table 3 of `RESULTS.md` reads 11.3 with one line per competitor row and counts the
opposite claims of both Shield rows. The new section prints the same line for "Shield 0.4.0" against H-F, H-P, T
and the internal row: the needed claims must hold for S-R4 and for S-N4, and an opposite claim of either row counts. This line is
the overall reading. The row-level table below is a breakdown. A row-level "conditions met" never stands for
"Shield 0.4.0".

**Wording (replaces the sentence "Shield beats X" of 11.3 for these rows).** No file says "Shield 0.4.0 beats X",
"wins" or "is better overall". Section 11.3 ties that sentence to a held-out Judilibre draw, and no set is held-out
for 0.4.0 (20.3.4). The only wording is "the conditions of 11.3 are met (or not met) for <row, or Shield 0.4.0>
against X", with the words of the last bullet of this section.

**Row-level breakdown (an addition; the overall reading stays that of Table 3).** Section 11.3 does not say which
Shield row "Shield beats X" means; Table 3 read it with both rows. The breakdown reads the conditions of 11.3 with
one Shield row at a time, on the primary readings of 20.8:

| Against | Conditions for the Shield row (all of them) |
|---|---|
| H-F | a P2 claim on the fresh Judilibre draw (200); a P1 claim and a P2 claim on REF; no opposite claim, P1 or P2, on any of the six sets |
| H-P | the same, with the Judilibre Precis subset (50) and the mapping pairs on FR-PII-Bench |
| T (internal) | a P1 claim and a P2 claim on REF; no opposite claim on REF, FR-PII-Bench, Max or English (the sets Tonic ran) |
| P | no overall claim in 11.3: per-set claims only, listed |

"No opposite claim on any set" is the strict reading of 11.3: it includes P1 on Judilibre, which is indicative.
A sensitivity reading never enters a verdict, with one exception: Max without the workbook. The needed and the
opposite claims on Max follow the rule "Max, competitor pairs" above: the condition "no opposite claim on Max" is
read on both readings (33 and 32 documents), and an opposite claim in either one fails it. For the other
sensitivity readings: when one gives the opposite of the primary reading, it is printed next to the verdict.

Verdict tables of the new section (cells filled by the score stage; no cell is filled here). First the overall
line, the reading of Table 3:

| Overall line | Against H-F | Against H-P | Against T (internal) |
|---|---|---|---|
| Shield 0.4.0 (S-R4 and S-N4 together: every needed claim for both rows; an opposite claim of either row counts) | | | |
| Shield 0.3.1 (S-R and S-N together): Table 3 of `RESULTS.md` and the reading of the internal row, cited as written, not computed again | | | |

Then the row-level breakdown:

| Shield row | Against H-F | Against H-P | Against T (internal) | Against P (per set only) |
|---|---|---|---|---|
| S-R4, Shield 0.4.0 rules (product default) | | | | |
| S-N4, Shield 0.4.0 rules + GLiNER | | | | |
| S-R, Shield 0.3.1 rules (read again from the existing comparison files, same rule) | | | | |
| S-N, Shield 0.3.1 rules + GLiNER (the same) | | | | |

- A cell says "conditions met" or "conditions not met", then the conditions that fail and the opposite claims,
  by set.
- A cell that differs from the 0.3.1 row of the same mode names each set whose claim changed and the status of
  that set for 0.4.0 (example: "English: development set of 0.4.0").
- The two 0.3.1 lines come from the existing files in `sealed/scores/compare/`: no new computation. They make the
  four Shield rows read by one rule.
- A verdict always names its row. No sentence says "Shield beats X" for a 0.4.0 row. The product default is the
  rules row: a verdict of S-N4 never stands for the product default. The two 0.4.0 rows and the overall line are
  always printed together.
- Every "conditions met", of a 0.4.0 row or of the overall line, is written with: "a build made after the first
  results of this comparison; no set is held-out for it; the fresh Judilibre draw is held-out for the other tool
  only; the other tool was measured in October". A sentence without these words is not allowed, in any file.
- Speed is not part of a verdict (20.6). F1 is not part of a verdict or of any claim (18.8, 20.10).

## 20.10 Exploratory F1 (section 18; no claim)

- `score_f1.py score` with `--set`, the required `--json` and the required `--frozen-json` (the score file of
  20.8) for S-R4 and S-N4 on the six sets, into `<work>/f1/S-R4/<set>.{json,md}` and
  `f1/S-N4/<set>.{json,md}`, as 18.11 did for S-R and S-N.
- A separate bundle `sealed/f1/bundle_v04/`: the rows of the D25 bundle and of the internal row (on REF and Max), plus S-R4 and
  S-N4; the common set per set over the rows of that table (`score_f1.py common`, then each row with `--docs`),
  as 19.8 did for the bundle of the internal row. Outputs: `bundle_v04/aggregates_f1_v04.json` (set-level only) and
  `bundle_v04/tables_f1_v04.md`. The bundle command, in the form of 19.8: `score_f1.py bundle
  --dir <work>/f1 --dir <work>/sealed/f1/bundle_rows
  --dir <work>/sealed/f1/<bundle of the internal row>/rows --common-dir <work>/sealed/f1/bundle_v04/common
  --out <work>/sealed/f1/bundle_v04/aggregates_f1_v04.json
  --md <work>/sealed/f1/bundle_v04/tables_f1_v04.md`.
- **The status line of the frozen script does not apply to these rows.** The frozen `score_f1.py` prints a
  built-in set status that was written for the 0.3.1 rows (for Judilibre: "held-out for every tool"). Its files
  under `f1/S-R4/`, `f1/S-N4/` and `sealed/f1/bundle_v04/` are machine records and are not edited. That status
  line does NOT apply to rows S-R4 and S-N4. The score stage writes `README_STATUS.md` in each of the three folders
  with this sentence and the table of 20.3.4. Every F1 table of the 0.4.0 rows in `RESULTS.md` and in any other
  file is written from the JSON values with the short label of 20.3.4, never by a copy of the machine `.md`.
- The D25 bundle (`sealed/f1/aggregates_f1.json`, `tables_f1.md`) and the bundle of the internal row are
  not written again: their SHA-256 are taken before and after and must be equal.
- All rules of 18.8 hold: the label "exploratory (added after the runs, not pre-registered)", per set, no pooling,
  no claim, recall-only sets (Judilibre, English), lower-bound precision (MAPA, Max), sealing. The set status
  printed next to an F1 of a 0.4.0 row is the status of 20.3.4.

## 20.11 Checks before and after

| When | Check | Expected |
|---|---|---|
| Freeze, run start, run end, after scoring, after the report | `shasum -a 256 -c` on `PREREG.sha256`, `PREREG_DATA.sha256`, `PREREG_F1.sha256`, the hash list of the internal row | 685, 829, 4 and 4 OK |
| Run start and every later point | `shasum -a 256 -c evaluation/laptop/PREREG_V04.sha256`; `shasum -a 256 -c` on the wheel hash file; `(cd <work>/v04_run/status_facts && shasum -a 256 -c SHA256SUMS)` | all OK (10 of 10, 1 of 1, 7 of 7) |
| Run start | `C:/shield_v04` absent; `runs/shield_A_v04` absent on the Mac; no score file of a 0.4.0 row | all absent (an earlier try of the run stage that died: 20.12; a score file: stop) |
| Run start | the install checks I1 to I10 and the input hashes (20.4) | as written there |
| Each process | exit code 0; `run_meta.json`: `shield_version` 0.4.0, `shield_package_sha256` of 20.4, `shield_commit` of 20.4, the expected `engine_mode`, `network_attempts` empty | every process. A non-empty `network_attempts` list does not stop the run: it is reported in the P4 table |
| Run end | under `C:/shield` and `C:/bench`: 0 files with a write time after the session start | 0 |
| Run end | the copy on the Mac against `SHA256SUMS_vm.txt` | every file equal |
| Before scoring | `score_text.py --selftest`; the reader version check (`check_versions()` empty); the three scripts at their frozen hashes | OK |
| After scoring | the two subset checks of 20.8; the SHA-256 of the bundles of the internal additions unchanged; `shasum -a 256 -c v04_run/scores_before.sha256`: all OK (no existing file of `scores/`, `sealed/scores/`, `f1/` or `sealed/f1/` changed; new files only) | OK |
| After scoring | independent recount of the 12 new cells and of the comparisons by a counter that imports nothing from the frozen scripts (as checks 1 and 2 of D17 and D24), written to `v04_run/CHECK_V04.md`. A correction made after a score was seen is labelled as such in D28 | counts equal, or every difference explained |

## 20.12 Failures, stops and re-runs (applies sections 12.1 and 12.2)

- A document Shield fails on is `failed`: fully exposed (12.1). A Shield error is never a reason to run again.
- A process may be run again only for an operator error (wrong folder, wrong mode, a driver fault, a wrong
  install) or a machine failure (the VM stops, the disk is full, the process is killed from outside). The reason
  is written in `DEVIATIONS.md` (D28) and in `RUN_NOTES.md` BEFORE the new process starts and before any 0.4.0
  score exists. The failed attempt is kept under `logs/attempt<k>/`; the new process writes into a new folder
  (`<set>.rerun<k>`); the first complete run is the one scored, and both are listed.
- If `C:/shield_v04` exists at the run start (an earlier try that died), the run stage reads what is there. First
  it reads the process list of the VM (`Get-CimInstance Win32_Process`, command line contains `shield_v04`). If a
  driver or a runner process of the earlier try is alive, nothing is moved and nothing is started: the stage waits
  for it by reading `logs/drive.txt`. A second driver is never started while the first is alive. A `VM_BUSY` file
  left by the earlier try is kept while that driver is alive; it is taken over (same file, one new line with the
  UTC time) when the stage continues, and deleted only after the last process. Then: a process whose
  `run_meta.json` exists and whose exit code in `logs/runs.csv` is 0 is complete and is kept. Any other process
  folder is moved to `logs/attempt<k>/` and that process is run again, with the note above.
- If the 0.4.0 wheel cannot be installed or the pilot shows that it does not run on Windows for a reason in the
  wheel itself, the run stage stops. No set is run. A fix is a new commit, so a new version of this addendum.
- If the VM cannot be reached or was resized, the run stage stops and reports. It does not start, stop or resize
  the VM.
- After the first score of a 0.4.0 row exists: no re-run, no second wheel, no change of a rule. What is found
  later is a labelled correction (D17 precedent) or a new row under a new addendum.

## 20.13 Sealing, clean room and publication (applies section 13)

- **Sealing is unchanged.** The outputs and per-document scores of H-F, H-P, T, P and the internal row stay under
  `<work>/sealed/`. The comparison outputs of this addendum are sealed too. Only set-level tables leave.
  The stages of these rows (freeze, run, score, check, report) do not edit `src/` or `tests/`.
- **Clean room.** No rule, lexicon, test or comment of Shield may cite or be derived from a competitor output or a
  competitor's per-item result (section 13). The wheel is frozen before the run. Nothing is tuned on a result of
  these rows: a later Shield change is a new row.
- **New rule from this addendum on** (it did not exist before: 20.3.3, limit 1). A session that works on `src/`
  or `tests/` does not open `<work>/sets/ref`, `<work>/sets/judilibre`,
  `<work>/judilibre_fresh`, their copies, or Shield's laptop outputs and per-document score files
  (`runs/shield_A`, `runs/shield_A_v04`, `scores/`). The rule does not make these sets held-out afterwards. It keeps
  the record clean for a later build.
- **Internal.** `RESULTS.md` may hold every row. Tonic numbers, the numbers of the internal row and every comparison with T or with the internal
  row stay internal (4.3, 19.2).
- **Public.** Hadi decides on every publication (4.3). A public file may show S-R4, S-N4, S-R, S-N, H-F, H-P and P.
  It shows no measured Tonic number and does not name the internal row. It keeps the 0.3.1 rows next to the 0.4.0 rows:
  the new rows never silently replace the old ones. Next to every 0.4.0 number it prints the set status for 0.4.0
  (20.3.4). It says once, near the top, that Shield 0.4.0 was built after the first results of this comparison
  were known, that no set is held-out for it, and that Hexagone 0.3.9 and Presidio 2.2.364 were measured in
  October 2026 and not run again.
- **Public, no selective report.** A public file that shows one 0.4.0 number shows both 0.4.0 rows on all six
  sets, P1 and P2, every per-set claim in both directions with the same weight, the Table 3 reading and the
  row-level table in full (without the internal columns), and the failed documents. No 0.4.0 number
  stands in a title, a headline or a summary without its set, its row and its status. The results of S-R4 and S-N4
  are written in `RESULTS.md` whatever they show, and they stay there. A later Shield build is a new row with its
  attempt number (0.3.1 is the first, 0.4.0 the second); a file that shows a later row shows all earlier Shield
  rows.

## 20.14 Limits of these rows (adds to section 14)

1. **A second attempt.** Shield 0.4.0 was built after the first results. No set is held-out for it (20.3.4). The
   rows show what the new build does on these files. They are not a confirmation on unseen data.
2. **November against October.** The competitor rows are the sealed runs of 2026-10-24 to 26, with the versions of
   that time. Hexagone cannot be run again (the trial ended). Tonic, Presidio and the internal row are not run again.
   Their newer versions, if any, could score differently.
3. **Status by record, not by proof**, for REF and for the fresh Judilibre draw (20.3.3 and its limits).
4. **Not blind.** The 0.4.0 work already measured the build on the documents of four laptop sets with other
   runners (20.3.5).
5. **Max and the workbook.** The reader fix for the `.xlsx` file came from this study. The frozen rule charges row
   S-R and row S-N with every gold item of that file. The reading on 32 documents shows the rest (20.8).
6. **More comparisons.** Two more rows add 93 runs of `compare_runs.py`. No correction for multiple comparisons
   is made, as before. Among so many 95 % intervals, some claims can appear by chance.
7. **Speed.** The 0.4.0 session is 16 days after the 0.3.1 and Hexagone sessions, on a VM that was stopped and
   started, with less background load. No control run of 0.3.1 is made in the new session, so a difference of the
   VM between the two dates cannot be told apart from a difference of Shield. Hence the rule of 20.6. No profile B,
   no AVX2-only row. A VM is not a laptop (4.2).
8. **Rules written with the first results known.** The author knew the 0.3.1 and competitor results (20.0).
   Choices made here that the frozen protocol did not fix: (a) the row-level table is an addition; the overall
   reading stays that of Table 3 (both rows). The row-level table ignores the other row's opposite claims, and "no
   opposite claim" counts P1 on Judilibre. On 2026-10-25, on English, S-R had an opposite P1 claim against H-F
   (and against one internal row), and S-N had none against these two rows (Tables 2 and 3 of `RESULTS.md`). The
   author knew this. The two 0.4.0 rows and the overall line are always printed together, and the 0.3.1 rows are
   read by the same rule. (b) No new speed claim in favour of Shield across sessions. Claims and plain statements
   against a 0.4.0 row are kept.
   (c) Max without the workbook is a second reading: it can withhold a claim from a 0.4.0 row or count one against
   it, never add one in its favour (20.9). (d) The descriptive counts against 0.3.1 and (e) the 10 % load limit
   taken from the logs of 2026-10-25 are descriptive or operational; neither enters a verdict.
9. **One run per row** for accuracy (14.9). The REF repeat check of 20.7 is the only repeat.
10. **No Mac parity sample** (20.2). The scored outputs are the Windows outputs, as for rows S-R and S-N.
11. **The wheel, not the installer.** The rows measure the 0.4.0 wheel in a venv with the dependency versions of
    the 0.3.1 rows. The desktop installers of 0.4.0 carry their own Python and packages; they are not measured here.
12. Every limit of sections 14 and 19.12 still holds (folder condition, indicative P1 on Judilibre, gold by our
    rules, document properties apart, the internal row by omission).

## 20.15 Deviation entry (written into `DEVIATIONS.md` at the freeze as D28)

Index line: `| D28 | Rows S-R4 and S-N4: Shield 0.4.0, a build made after the first results, run on profile A; competitor rows not run again (before any 0.4.0 output on a laptop set) | none |`

The entry in `DEVIATIONS.md` has one more bullet, written after the freeze: the hash checks made after it.

## D28. Rows S-R4 and S-N4: Shield 0.4.0, a build made after the first results (2026-11-11, freeze 2026-11-11T09:04:25Z, before any 0.4.0 output on a laptop set existed)

- **Time:** addendum 4 drafted 2026-11-10 from 17:13Z to 17:45Z (v1.0 draft), reviewed by two critics (fairness
  and status honesty; correctness and runnability; reports of 2026-11-11, about 08:35Z), revised (v1.1) and frozen
  at 2026-11-11T09:04:25Z (`PREREG_V04.sha256`). At the draft: the four earlier hash lists passed `shasum -a 256 -c`
  (17:13:18Z and 17:46:08Z: 685, 829, 4 and 4 OK); `VM_BUSY` was absent; `C:/shield_v04` did not exist on the VM
  (17:27:40Z); `runs/shield_A_v04`, `scores/S-R4`, `scores/S-N4` and `bundle_v040` did not exist on the Mac
  (17:36:32Z). At the freeze: the four lists passed again (2026-11-11 08:36:34Z and 2026-11-11T09:04:24Z, the same
  counts); `VM_BUSY` was absent; `C:/shield_v04` did not exist (read-only queries, 08:39:06Z, 08:59:08Z and
  09:04:18Z); no run folder and no score file of a 0.4.0 row existed on the Mac. No output of Shield 0.4.0 on a
  laptop set through the head-to-head runner existed, and no score of one. The P1, P2, speed and F1 results of
  rows S-R, S-N, H-F, H-P, T, P and the internal row existed. The author, the critics and the freeze stage had read set-level tables of `RESULTS.md`; no
  output and no score file under `sealed/` was opened (the freeze stage read five lines of one check log there:
  20.17).
- **What changes:** `PROTOCOL_ADDENDUM_4.md` (section 20, v1.1) adds rows S-R4 (Shield 0.4.0, rules, the product
  default) and S-N4 (rules + gated GLiNER on CPU): the six sets, the same 798 inputs, readers, scorer and run
  procedure (9.1, D15) on profile A, from the wheel of commit `fd8662d120de765fc5fb65aa7bb83155e3ea18f3` (`src/`
  tree `c4951557`, package hash `fb4288ba...526c`, wheel SHA-256
  `01404cd3d6cb321f56ae6629a5b9d62af152b1778790ffd130fb120ed4bd85b9`), installed in `C:/shield_v04` with the dependency
  versions of the 0.3.1 venv. New in the analysis: the paired comparison of each 0.4.0 row with the 0.3.1 row of
  the same mode; a second Max reading without the one workbook that 0.3.1 could not read (a Max claim in favour of
  a 0.4.0 row needs both readings); the overall reading of Table 3 kept (both Shield rows), with a row-level
  breakdown by the conditions of 11.3 and the wording "conditions met", never "Shield 0.4.0 beats X"; the speed
  claims of Table 8 read again in both directions, and no new speed claim in favour of Shield across sessions; a
  new rule that keeps the laptop sets REF and Judilibre fresh, and Shield's laptop outputs and scores, away from
  sessions that work on `src/` or `tests/` (20.13).
- **What does not change:** the gold, the sets, the order, the readers, the frozen scorer, `compare_runs.py`,
  `score_f1.py`, the runner, the per-set claim rules of 11.3 and 17.4, the sealing rules. Rows S-R and S-N stay as
  measured. The competitor rows are the sealed ones: nothing is run again for H-F, H-P, T, P or the internal row, and the
  Hexagone app is not opened. No file of `PREREG.sha256`, `PREREG_DATA.sha256`, `PREREG_F1.sha256` or
  the hash list of the internal row changes.
- **Status of the sets for 0.4.0 (20.3):** Shield 0.4.0 was built after the first results (first scores
  2026-10-25 about 09:45Z; nine of its ten accepted steps, and three installer commits that are also in the wheel,
  were committed between 2026-10-25 11:45Z and 2026-11-07 00:23Z). No set is held-out for it. English: development
  set. FR-PII-Bench and MAPA: regression gates. Max: audited, run with the finished build, and one failure found by
  this study (the `.xlsx` workbook) was fixed in 0.4.0. REF and the fresh Judilibre draw: no use by the 0.4.0 work
  in any record (harness, step reports, prompts, 122 agent transcripts, gold scan of the added code lines: 0
  hits), not proven, and their 0.3.1 results were known. Evidence: `<work>/v04_run/status_facts/`.
- **Speed:** one REF session for S-R4 and S-N4 as D15, only in a quiet VM (20.6); else "not re-measured". The
  Hexagone speed values stay the sealed ones.
- **Freeze:** `evaluation/laptop/PREREG_V04.sha256` (time 2026-11-11T09:04:25Z) holds the SHA-256 of the addendum, of
  the wheel hash file, of the evidence list `v04_run/status_facts/SHA256SUMS`, of the dependency pin list
  `vm_logs3/pip_freeze_577b423.txt`, of the 32-line Max gold `v04_run/max_no_xlsx/gold.jsonl`, and of the frozen
  dependencies `score_text.py`, `extract_text.py`, `compare_runs.py`, `run_shield_files.py` and `score_f1.py`. The
  wheel was built twice from two exports of the commit (uv 0.6.2, hatchling 1.33.0, 2026-11-11 08:38Z): the two
  files are byte-identical (573,379 bytes). The four earlier hash lists passed `shasum -a 256 -c` right before the
  freeze.
- **Effect on results:** none on any existing row. No result of a 0.4.0 row exists at this entry.
- **To be completed by the later stages (times and facts only):** `VM_BUSY` written at `<time>` by `<who>` and
  deleted at `<time>`; install checked at `<time>`; pilot at `<time>`; the 12 processes from `<time>` to `<time>`;
  quiet VM `<yes | no: what ran>`; speed session `<done | not re-measured: reason>`; re-runs `<none | which, why,
  written at what time>`; copy checked at `<time>`; run closed at `<time>`; first 0.4.0 score computed at `<time>`;
  independent recount `<same | differences>`; corrections made after scores were seen `<none | list>`.

## 20.16 Files and freeze

| File | Role |
|---|---|
| `evaluation/laptop/PROTOCOL_ADDENDUM_4.md` | this addendum (frozen by `PREREG_V04.sha256`) |
| `<work>/v04_run/PROTOCOL_ADDENDUM_4.v1.0_draft.md` | the v1.0 draft that the critics read (SHA-256 `459fe7d5...d814`; a record, not frozen) |
| `<work>/bundle_v040/ragbase_shield-0.4.0-py3-none-any.whl` | the 0.4.0 wheel of commit `fd8662d` (20.4) |
| `<work>/bundle_v040/ragbase_shield-0.4.0-py3-none-any.whl.sha256` | the wheel hash file (20.4; frozen by `PREREG_V04.sha256`) |
| `<work>/v04_run/status_facts/` | the evidence of 20.3: `repo_facts.sh`, `scan_gold.py`, `scan_transcripts.py`, the outputs `repo_facts.out.txt` (it holds the output of `scan_gold.py`) and `scan_transcripts.out.txt`, the added code lines, the VM state note, and `SHA256SUMS` (their hash list, 7 files; frozen by `PREREG_V04.sha256`; check: `(cd <work>/v04_run/status_facts && shasum -a 256 -c SHA256SUMS)`) |
| `<work>/vm_logs3/pip_freeze_577b423.txt` | the dependency pin list of I5 (SHA-256 `abb4a823d747d93e528c9cd6f7107253228aec87a19756d94fa3de054ca09004`; frozen by `PREREG_V04.sha256`) |
| `<work>/v04_run/max_no_xlsx/gold.jsonl` | the 32-line Max gold of 20.8, written by the freeze stage: the lines of `sets/max/gold.jsonl` whose `doc_id` is not `D/Pièce 9 - décompte heures sup.xlsx`, bytes unchanged (frozen by `PREREG_V04.sha256`) |
| `evaluation/laptop/PREREG_V04.sha256` | written by the freeze stage: `shasum -a 256` format, paths relative to the repository root, comment lines with the freeze time (UTC). It lists: this addendum; the wheel hash file; `v04_run/status_facts/SHA256SUMS`; the pin list; the 32-line Max gold; and, as frozen dependencies that do not change (also in `PREREG.sha256` and `PREREG_F1.sha256`), `score_text.py`, `extract_text.py`, `compare_runs.py`, `run_shield_files.py` and `score_f1.py`. 10 lines. Verified with `shasum -a 256 -c` right after it is written |
| `<work>/v04_run/RUN_PLAN.md` | the run plan written at the freeze: the commands of 20.4 to 20.8 in order (not frozen; it repeats this addendum and never overrides it) |
| `<work>/v04_run/ops/` | the operator scripts of 20.5, prepared at the freeze (not frozen; the pilot is their test) |
| `<work>/v04_run/RUN_NOTES.md`, `SCORE_LOG.md`, `CHECK_V04.md`, `scores_before.sha256` | logs of the run, the scoring and the independent recount, and the hash list of the existing score files taken before the first job (not frozen) |
| `<work>/runs/shield_A_v04/` | outputs, run logs and VM logs of the two rows (20.7); not sealed (Shield's own outputs) |
| `<work>/scores/S-R4/`, `scores/S-N4/`, `f1/S-R4/`, `f1/S-N4/` | per-document scores and exploratory F1 of the two rows; not sealed |
| `<work>/sealed/scores/compare_v04/`, `sealed/scores/<row>/max_no_xlsx.json`, `sealed/f1/bundle_v04/` | comparisons, the second Max reading of the competitor rows, the F1 bundle; sealed |
| `evaluation/laptop/RESULTS.md` | gets a new section at the end (20.8); its existing tables are not edited |
| `DEVIATIONS.md`, `evaluation/laptop/VM_BUSY` | logs, not frozen. `DEVIATIONS.md` receives the D28 entry of 20.15 at the freeze |
| `PREREG.sha256`, `PREREG_DATA.sha256`, `PREREG_F1.sha256`, the hash list of the internal row, `freeze.py` | not changed |

Fields that the freeze stage filled in this file before it hashed it: the freeze time (header, 20.0 and D28), the
wheel SHA-256 and the build facts (20.4 and D28), the checks at the freeze (20.0), and the "Review" section
(20.17) with the critics' findings and what was done. Every other change of v1.1 has a line in that section.

## 20.17 Review (findings of the two critics applied in v1.1, before the freeze)

Every major finding was applied (no blocker was raised). Every minor finding was applied too, except one that
asked for no change. No finding was answered with a result of a 0.4.0 row: none exists. Numbering is the critics'
own. The critics did not edit the draft and did not run Shield 0.4.0.

| Critic | Blockers | Majors | Minors | Applied |
|---|---:|---:|---:|---|
| 1, fairness and status honesty | 0 | 5 | 5 | 5 majors, 4 minors; minor m5 asks for no change |
| 2, correctness and runnability | 0 | 4 | 11 | 4 majors, 11 minors |

- **Critic 1, majors.** M1 (the verdict unit was chosen with a result in view: the overall reading of Table 3 is
  kept with both rows, the row-level table is a breakdown, no "Shield 0.4.0 beats X" in any file, a changed cell
  names the set and its status: 20.9, 20.14 limit 8a, header). M2 (Max and the workbook: a Max claim in favour of
  a 0.4.0 row needs the 33 and the 32 documents, a claim against it counts in either reading: 20.8, 20.9, 20.14
  limit 8c). M3 (the speed rule worked in one direction only: the claims of Table 8 are read again in both
  directions, a claim against Shield is kept: 20.6 rule 2, 20.14 limit 8b). M4 (the short labels could still show
  "held-out" next to a 0.4.0 number: new short labels for REF, Judilibre and English, consequence 2 covers cells,
  column heads, labels and captions, existing tables get no 0.4.0 row: 20.3.4, 20.2). M5 (no rule against a
  selective public report: both rows, all six sets, both directions, attempt numbers: 20.13).
- **Critic 1, minors.** m1 (three installer commits change `src/` and are in the wheel; 13 commits, 12 after the
  first scores: 20.0, 20.3.1 timeline and text, D28; the freeze stage checked the three commits in git and checked
  by a static import walk that the runner path reaches neither `cli.py` nor `desk/`). m2 (the scan reads four
  tools only; the wider check: 20.3.3 limit 2). m3 (five new setting names, not two: 20.1; checked in git). m4
  (four "replaces" points, "per-set claim rules": header, D28). m5 (no same-session control run of 0.3.1: rule 3
  of 20.6 stays, no control run is added; the critic did not ask for one).
- **Critic 2, majors.** M1 (the frozen scorer overwrites: existence test before each job, `scores_before.sha256`
  before the first job and checked after the last: 20.8, 20.11, 20.16). M2 (the frozen `score_f1.py` prints the
  set status of the 0.3.1 rows: `README_STATUS.md` in three folders, F1 tables written from the JSON values:
  20.10). M3 (an earlier driver could be alive: process list first, never a second driver, `VM_BUSY` taken over:
  20.12; the start script refuses to start when one is alive). M4 (three inputs outside the freeze list: the pin
  list and the 32-line Max gold are in `PREREG_V04.sha256`, the evidence list is checked at the run start: 20.4
  I5, 20.8, 20.11, 20.16).
- **Critic 2, minors.** m1 (model size through the link: I9). m2 (`sample_memory.ps1 -Out` is mandatory: 20.6).
  m3 (`SHA256SUMS_vm.txt` written by Python in a fixed format, the copy is a zip: 20.7). m4 (the D15 scripts as
  templates, no case clash, the variable list per process: 20.5 "Operator scripts"). m5 (`RAGbase Shield` in Q2:
  20.6; see the choices below). m6 (`VM_BUSY` tested before every VM command: I1). m7 (one job at a time;
  `compare_runs.py` must exit 0 with a non-empty file: 20.8). m8 (the bundle command; `--json` is required:
  20.10). m9 (five setting names: 20.1, with critic 1 m3). m10 (pin list format, pip and setuptools, torch
  source, I8 wording: I5, I8; see the choices below). m11 (`scan_gold.py` has no own output file: 20.3, 20.16).
- **Freeze-stage choices (none depends on a result).**
  1. Operator scripts were prepared at the freeze (20.5, `v04_run/ops/`): the critics asked for copies of the D15
     scripts; the freeze stage copied five of them from the VM (read only) and adapted them on the Mac. The
     PowerShell files passed a syntax check (0 parse errors) and the four read-only ones a trial on the VM;
     nothing was written there. The driver and the install script have not run: the pilot is their test.
  2. Q2 matches the eight names at the start of the process name, not anywhere in it (critic 2 m5 wrote
     `*name*`): `*light*`, `*node*` or `*wix*` could match a process that belongs to no stage, and Q2 would then
     fail on every try. `pythonw` is still included.
  3. torch comes from the PyTorch CPU index for its one line, with `--index-url`; critic 2 m10 wrote
     `--extra-index-url` for the whole list. One source per package is closer to the words of I5.
  4. `scores_before.sha256` also covers `f1/` and `sealed/f1/` (more than critic 2 M1 asked).
  5. The peak memory reading is once per second, as in the D15 driver file. The draft said 0.5 s, the words of
     D15; the driver file of D15 sleeps 1,000 ms. The value is the system's own running peak.
  6. Limit 8a of 20.14 names the opposite English claim of S-R against H-F, which is public, and not the other
     row of critic 1's sentence: no result of an internal row is written in this file.
  7. The public rule of 20.13 says "without the internal columns" (added to critic 1's text; 4.3, 19.2).
  8. Speed rule 2: the case "(b) fails" was not in critic 1's text. The table then gives the values and the
     differing facts, and the claim is not read again, in either direction.
  9. A folder `C:/shield_v04/tasks/` holds the seven `tasks.json` copies (I2, "Inputs"), as `C:/shieldrun/tasks`
     did in D15.
  10. The driver writes the models folder as `C:\shield\models`, the value in the driver file of D15 (20.5).
  11. The bullet "No result is in this file" of 20.0 was reworded: limit 8a of 20.14 and rule 2 of 20.6 now name
      claim directions of the 0.3.1 rows, as the critics asked. No value of any row is in this file.
- **What the freeze stage read.** The two critic reports. `RESULTS.md`: Table 3, and Table 8 with its claim list
  (it holds an internal timing row, not copied anywhere). `RESULTS_PUBLIC.md`: the lines with "held-out".
  `PROTOCOL.md` 11.3 and 12; `PROTOCOL_ADDENDUM_3.md` 19.8 and 19.15 (internal); D15; the setup notes of the VM; the scoring
  and F1 scripts of D16, D23, D25 and an internal entry (not the copies under `sealed/`). The Max gold: the `doc_id` values
  only, by a script, to write the 32-line file. The run records of the 0.3.1 session (`runs/shield_A`:
  `run_meta.json`, run-log statuses, hashes of the REF outputs), to test the run check script. Under `sealed/`:
  folder and file names, and five lines of one check log (`sealed/f1/run_f1_pending.log`: PASS lines about
  document lists, no result value). No output and no score file there was opened. No 0.4.0 output of a laptop set
  existed, so none was read.
