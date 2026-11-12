# Deviations from the frozen protocol (PROTOCOL.md, PROTOCOL_ADDENDUM_1.md, PREREG.sha256)

> **Public extract (2026-11-12): entries about an internal row are left out.** This extract holds the entries D1 to D24 and D28, the entries that the public results file cites. D25 to D27 and D29 are internal additions and are left out. Inside the kept entries, the Tonic counts and every mention of the internal row are left out, and a few private details are replaced (a marker in square brackets says where). The changes are listed in `PUBLIC_EXTRACT.md`. The original log and the hash lists are kept private.

All times are UTC ("Z"). This file is a log: it is not frozen (PROTOCOL_ADDENDUM_1.md section 17.6). The only
sources for hashes are `PREREG_v1.0.sha256`, `PREREG.sha256` (v1.1) and `PREREG_DATA.sha256`.

| Entry | Subject | Gaps of the internal run check |
|---|---|---|
| D1 | Claude operates Hexagone, at Hadi's instruction (corrected 2026-10-24) | G5, G6, G7, G8 |
| D2 | Interim freeze before the critic finished; fairness review; re-freeze v1.1; run sheet not frozen | G1, G4, G11 |
| D3 | Tonic runs from the Mac with the key file | G10 |
| D4 | Fresh Judilibre draw and data addendum | G2, G3 |
| D5 | H1 facts not recorded yet (open) | G9 |
| D6 | Wrong hash quotes in two operator reports | G11 |
| D7 | Shield working tree changed during the trial | G12 |
| D8 | Shield venv on the VM carries Windows patches W1 to W4 (open, found by the review) | none |
| D9 | H1 facts recorded (closes D5) | G9 |
| D10 | Hexagone masks output file names; name-only mapping rule; operator mechanics (before any scored Hexagone run) | none |
| D11 | Name rule fails on multi-file tasks; content-overlap assignment for those tasks (before any score) | none |
| D12 | D11 threshold drops processed documents; primary manifest keeps every pair when the app wrote one output per input (before any score) | none |
| D13 | Precis input folders are byte-identical copies, because the app allows one synchronisation per source folder | none |
| D14 | H4 Precis stopped after REF and FR-PII: the Remote Desktop session was disconnected (open) | none |
| D15 | Shield and Presidio runs on profile A: setup written before the runs; closes D8 | none |
| D16 | Scoring step: how the frozen scorer is fed (written before any score) | none |
| D17 | Check 1: independent re-score; corrections made AFTER the scores were seen | none |
| D18 | Sealing fixes after the fairness check | none |
| D19 | Hexagone operator 2: H4 resumed, late FR-PII Precis exports, click time log (before any score of the new tasks) | none |
| D20 | Hexagone H5 speed session: set-up written before the session | none |
| D21 | H5 cold start: the frame watcher was blocked by the antivirus; ready time read another way | none |
| D22 | H5 Precis stopped after 3 of 5 tasks: the Remote Desktop session was disconnected again (open) | none |
| D23 | Scoring step 2: how the new Precis rows and H5 are fed to the frozen scorer (written before any score of them) | none |
| D24 | Check of step 2: independent re-score; text corrections made AFTER the scores were seen | none |
| D28 | Rows S-R4 and S-N4: Shield 0.4.0, a build made after the first results, run on profile A; competitor rows not run again (before any 0.4.0 output on a laptop set) | none |

## D1. Claude operates Hexagone, at Hadi's instruction (2026-10-24, before any Hexagone run)

- **Time:** written 2026-10-24 at about 13:01Z (file time). No Hexagone, Tonic or Presidio output existed yet. No
  score had been computed. Corrected 2026-10-24 at 13:50Z by the D2 session: the first text said "13:05 CEST" and
  "13:00 CEST"; these were UTC times with a wrong zone label (gap G6).
- **What changed:** section 9.4 says a person runs Hexagone and forbids click scripts. Section 4.3 makes the
  Hexagone sign-up with Hadi's e-mail and the download of the installer actions that only Hadi takes. Hadi
  instructed Claude to install and operate Hexagone himself ("dude you do that dont care"), and accepted the risk
  under Hexagone's terms (section 13: "toute action visant à automatiser l'usage de l'Application au-delà des
  intégrations prévues"). Who did what at H0 (gap G8):
  - Claude filled the sign-up form in the built-in browser, with Hadi's e-mail, at Hadi's instruction (a
    departure from section 4.3);
  - Hadi clicked the installer download himself in the built-in browser (as section 4.3 says);
  - Claude installed and launched the app and did the onboarding;
  - Hadi entered the verification code himself with the Windows on-screen keyboard.
  Claude drives the app in Hadi's Remote Desktop session (user `<owner account>`, session 2) with one-off screenshot, click
  and key tasks (`<work>/gui/`), one action at a time, looking at each screenshot, as a person would.
  The app's own features only (file and folder flows, settings, documented CSV exports).
- **What did not change:** settings fixed in advance (defaults, French UI, "Tout masquer"), no edit in the review
  pane, no API, no traffic capture, no reading of app files, models or logs, the same sets and order, the sealing
  rules of section 13. The scorer and the reader are `laptop-score-1.1` and `laptop-extract-1.1`, as frozen by
  `PREREG.sha256` v1.1 (D2), not the 1.0 versions (gap G7). Steps H0 to H4 are logged in RUNSHEET_HEXAGONE.csv
  with operator "claude" (H0: "claude + hadi").
- **H0 facts:** installer Hexagone-0.3.9-setup.exe, SHA-256 618297822eb4d82a30115944ae574866db31c67f5364841e3e9a98cdbf6c31de,
  valid Authenticode signature (CN=Hexagone AI, Boulogne-Billancourt; issuer Microsoft ID Verified CS AOC CA 03).
  Per-user install to %USERPROFILE%\AppData\Local\Hexagone AI [public extract: user folder name replaced]. First launch clicked at 2026-10-24T12:09:35Z (the
  7-day trial starts then and ends at about 2026-10-31T12:09Z). Onboarding: French UI, manual setup (no LinkedIn),
  first name "Hadi", a work e-mail address [public extract: address left out] (personal addresses are refused by
  the app), code entered by Hadi.
  Trial shown: "Essai gratuit, 7 jours restants" at about 2026-10-24T13:00Z.
- **H0 run-sheet row (gap G5):** added to RUNSHEET_HEXAGONE.csv on 2026-10-24 at 13:46Z, after the fact, from this
  entry and `<work>/hexagone_trial_log.txt`.
- **Why:** Hadi's decision; the alternative (Hadi operating hundreds of documents by hand) was refused.
- **Effect on results:** none expected on accuracy (same app, same settings); timings are taken from output file
  times and mark_time.ps1 as before. Readers of the results must know the app was operated by an AI agent.

## D2. Interim freeze before the critic finished; fairness review; re-freeze v1.1 (2026-10-24)

- **Time:** review and re-freeze 2026-10-24 from 13:15Z to 13:49Z; entry written at 13:50Z. No Hexagone, Tonic or
  Presidio output existed (checked on the Mac and, names only, on the VM at 13:41Z). No score of any competitor.
- **What happened:** `PREREG.sha256` v1.0 was written on 2026-10-23 at 14:09Z (16:09 CEST), before the protocol
  critic had finished. The critic then changed `extract_text.py` (14:27Z, reader 1.1: "meta only, text unchanged")
  and `score_text.py` (14:45Z, scorer 1.1: 805 changed lines, citing a "PROTOCOL.md section 17" and a "section
  12.4" that were never written), validated them on Shield v0.3 outputs (`<work>/critic/val11/`), and
  was stopped by the app restart before a report or a new freeze (gap G1). On 2026-10-24 at 13:10Z a restarted
  protocol agent edited `compare_runs.py` and `run_tonic.py`; both were restored to v1.0 (its edits are in
  `<work>/stopped_agent_edits_20261024/` and were not used).
- **Review:** `<work>/PROTOCOL_CRITIC.md` (rule: keep a change only if it fixes a real scoring error and
  is the same for codes, tags, fakes and deletion; 76 invented cases).
  - KEPT: F1 reader meta (text identical on 1,000 input files); F2 case-, accent- and NFKC-folded token keys, NFC
    output; F3 alignment repair when a fake equals another real value; F4 moved blocks and gaps; F5 rejoin of split
    or glued words; F6 value reading of exposure, and a P1 claim needs both readings; F7 public or reserved mail
    domains do not identify; F8 format tokens shared by every value of a type do not identify; F9 keep items in
    document properties reported apart; F10 tracked deletions reported apart; F11 status `not_run` (with rules);
    F12 status `unscorable`.
  - REVERTED: F13 "dropped with its context" count, F14 cue split for person names, F15 "must stay clear without
    court_city" line (report-only, no scoring error fixed).
  - FIXED by the review: F16 header citations (now PROTOCOL_ADDENDUM_1.md 17.4 and 17.5); F17 duplicate function;
    F18 run-log rows also matched by `file`; F19 `compare_runs.py` 1.1 (headline parts only, `not_run` and
    `unscorable` documents left out of both sides, P1 strict and value, claim needs both; P1 strict and P2 keep
    the 1.0 bootstrap draws); F20 `freeze.py` 1.1 (logs not frozen, validation and review files frozen).
  - Effect on Shield, measured with Shield 0.3.1's own reader on Max without any masking: the kept rules remove 7
    false "protected" gold items (F4, F10: against Shield) and 6 false must-stay-clear alterations, all in document
    properties (F9: for Shield). F3, F7, F8, F11 and F12 cannot change a codes output that replaces whole values.
- **New protocol text:** `PROTOCOL_ADDENDUM_1.md` = section 17 (PROTOCOL.md stays byte-identical to v1.0).
- **Run sheet (gap G4):** `RUNSHEET_HEXAGONE.csv` is a log and is no longer frozen. Its frozen v1.0 content was the
  header line only, SHA-256 `b2d198aded4e626f4ac39d768195156ec0448ddb1f9303df9b3d429b3cd0fe90`; the header line
  stays unchanged (its SHA-256 is still that value). `DEVIATIONS.md` and `VM_BUSY` are not frozen either.
- **Hashes (SHA-256):**

| File | v1.0 (in PREREG_v1.0.sha256) | Critic draft (not used as is) | v1.1 (in PREREG.sha256) |
|---|---|---|---|
| `extract_text.py` | `da56d76f533454f38c35a33ef8cc50d89824ac4f2813224a36761c35c1d2ad47` | `20d6d7a47caa922adf98a2a37d4b246c953997825b801fee2da2681d189cc5de` | `71b063fcd853092b74354d8c490b03d418a43db537e1c2d59f315c3ee2a2cc90` |
| `score_text.py` | `dc3f95fb60a6b50b8efcb0a2c2dba33d58329fbc43db24bb7d0c08435c61b881` | `38885c11ec9aa57a1c8e76d383070b5560d92495db8f4229261467446f735053` | `d2e32fcf08a33ad2f4d758b216d4be36fe04d031dd0ec1519eeb351281e2` |
| `compare_runs.py` | `05c985b82dd6a150f752b9151f9abecd805afc84568c34a0f26628d82bd7e0cd` | none | `32dfa48f34ba74681b8e14b10b3c071fd285ac0611e5c8aec014489153806162` |
| `freeze.py` | `4a8cb750ad3b359dcbcff15641983989ab8652d30dc16407bf03626602d466ea` | none | `e687438fc5c71018fe08124608e4e367e6970c9858d81cdfc6c8dfa0de818361` |
| `PROTOCOL_ADDENDUM_1.md` | did not exist | none | `1f9089faaa16448cccf79ffd8f8d0f4de9b5853cfd427330f5ff7142f4a7a5ad` |
| `RUNSHEET_HEXAGONE.csv` | `b2d198aded4e626f4ac39d768195156ec0448ddb1f9303df9b3d429b3cd0fe90` | none | not frozen (log) |
| `run_tonic.py` | `5ce6d6792379baad2abc54364e2f1b48b60e527a4a15742f09bbcabd8f85da85` | none | unchanged |
| `PROTOCOL.md` | `5d49d6587bfaabcebc5e7a03f673a4e4981bc03bea22472386726a6fde53b93f` | none | unchanged |

| Freeze file | Written | Files | SHA-256 of the freeze file |
|---|---|---:|---|
| `PREREG_v1.0.sha256` (old `PREREG.sha256`, byte-identical) | 2026-10-23T14:09Z | 668 | `83d4ab60dd9996eb6e77f0ded3e85d17feaf2705250fcb0c32feb9d4011cfee5` |
| `PREREG.sha256` v1.1 | 2026-10-24T13:49:03Z | 685 | `fc3a0d2db5411cf56ad5f5c6debadd43dd209ac0767a2aa684f036264606f25a` |
| `PREREG_DATA.sha256` | 2026-10-24T13:42:25Z | 829 | `6fbfa1cf18a10ed4c7fa5c5daf6fcc1c81d588063dff3c0489bde7b4e71e1eec` |

  Check at 13:49Z: `PREREG_v1.0.sha256` differs in exactly the 5 files above (`RUNSHEET_HEXAGONE.csv`,
  `compare_runs.py`, `extract_text.py`, `freeze.py`, `score_text.py`); `PREREG.sha256` OK; `PREREG_DATA.sha256` OK.
- **Results seen before this re-freeze:** only (a) the critic's `critic/val11/` parity on Shield v0.3 outputs
  (FR-PII-Bench 300, MAPA 19, old Judilibre 200), the same files as the frozen section 8.3 validation; (b) Shield
  0.3.1's own reader text without any masking on Max (reader artefacts); (c) identity and oracle checks (no tool).
  No masking result of Shield 0.3.1 on REF, Max or English was computed; REF was never read by Shield. No
  competitor output existed.
- **Effect:** the section 8.3 validation table is unchanged with scorer 1.1 (every count equal, 0 changed
  statuses). P1 claims need both readings (stricter in both directions).

## D3. Tonic runs from the Mac with the key file (2026-10-24, before any Tonic request)

- **Time:** written 2026-10-24 at 13:50Z. 0 Tonic words used; the SDK is not installed yet; no request was made.
- **What changes:** section 9.2 runs `run_tonic.py` from the VM (profile A) with the key in the environment
  variable `TONIC_TEXTUAL_API_KEY`, put there by Hadi (section 4.3). Instead, `run_tonic.py` (unchanged, v1.0)
  runs on the Mac, in its own venv with `tonic-textual`; for that process only, `TONIC_TEXTUAL_API_KEY` is read from
  a local key file [public extract: path left out]. The key is never typed by Claude, printed, written to a log or
  put in a command's arguments.
- **Hadi's go (section 4.3):** Hadi gave his go for the Tonic run on 2026-10-24 [public extract: how the key was
  passed is left out].
- **Data path:** the files go from the Mac to Tonic's cloud (textual.tonic.ai), not from the VM in europe-west1.
  Only invented or synthetic sets are sent: REF, FR-PII-Bench, Max, English (91,663 words with reader 1.0 and 1.1;
  budget 100,000 minus the 5,000 margin). MAPA and Judilibre are not sent.
- **Effect:** accuracy none expected (same files, same SDK defaults). Tonic times include the Mac's network path,
  not the VM's (limit 14.8); the Tonic rows carry the machine label "Mac client, Tonic cloud" and are never used
  for a speed claim. Outputs go only to `<work>/sealed/tonic/`; results stay internal (section 13).

## D4. Fresh Judilibre draw and data addendum (2026-10-24)

- **Go (gap G3):** section 5.3 and 4.3 say the streamed download waits for Hadi's go. Hadi's instruction "do it
  all" (2026-10-23 and 24) covers it because the download needs no new account and no key: the Hugging Face files
  of `antoinejeannot/jurisprudence` at `8019db1` are public (the resolve URL answers with `user_id=public`).
- **Draw:** `draw_judilibre_fresh.py` as written, 2026-10-24 from 13:20:05Z to 13:21:23Z; the computed pool equals
  the frozen pool file; kept 67 + 67 + 66 decisions; `sample.jsonl` SHA-256
  `96c268e4ea7a33ccbff67f27f6a848cb3e2204d482c6c09266981b85b31e781f`.
- **Sets:** `prepare_sets.py all` at 13:37:47Z rebuilt FR-PII-Bench, MAPA, Max and English byte-identical to the
  v1.0 freeze (621 set files OK); `prepare_sets.py judilibre` at 13:38:46Z built the fresh set (200 .txt,
  2,308,427 characters, 673 indicative gold names, 6,136 must-stay-clear keep items, 8,648 placeholders).
- **Added helper file:** `<work>/judilibre_fresh/precis_subset.txt` (the 50 files of the Precis subset,
  taken from the manifest; not named in the protocol).
- **Data addendum (gap G2):** `PREREG_DATA.sha256` written at 13:42:25Z, 829 files: fresh draw 3, Judilibre set 204,
  REF 8, PILOT 3, FR-PII-Bench 304, MAPA 23, Max 38, English 245, Shield wheel 1 (SHA-256
  `b15c9771e4b40a4dac4cc14bbda71a05d60831d211c3c8af79a607e4c9c2b558`). No tool had read a decision. After it, only
  the scorer's identity and oracle check read the set (13:42:32Z and 13:47:46Z, no tool).

## D5. H1 facts not recorded yet (open, gap G9)

- At 13:50Z: app version (About screen), model download, whether Precis is offered, and the default replacement
  style are not recorded. The next Hexagone operator records H1 first, before H2, and changes nothing. Each day of
  delay uses the buffer days 5 to 7 (trial end about 2026-10-31T12:09Z).

## D6. Wrong hash quotes in two operator reports (gap G11)

- The Hexagone and Tonic operator reports of 2026-10-24 misquoted the frozen SHA-256 of `extract_text.py`, and the
  Hexagone report gave "667 of 669" files instead of 666 of 668. Those reports are not a source. Every hash in this
  file is copied from the three freeze files.

## D7. Shield working tree changed during the trial (gap G12)

- On 2026-10-24 the Shield v0.4 workflow changed `src/`, `tests/` and `evaluation/audit/` after the Hexagone trial
  started. Section 12.1 "no Shield change during the trial" is read as: the tested Shield is the frozen 0.3.1 wheel
  (commit 577b423, SHA-256 in `PREREG_DATA.sha256`), which does not change. A later build may only be a separate,
  labelled row (section 2). From the first competitor output on, a session that works on `src/` or `tests/` never
  opens `<work>/sealed/` (section 13).

## D8. Shield venv on the VM carries Windows patches W1 to W4 (open, found by the review)

- `C:\shield\.venv` holds the 0.3.1 wheel plus the Windows patches W1 to W4 in `cli.py`, `hooks.py` and `vault.py`
  (no engine file changed; audit `vm_logs3/08_audit.txt`; `<work>/WINDOWS_SETUP.md`). Section 9.1 says
  install the wheel. Before the scored Shield run: reinstall the clean wheel (undo command in WINDOWS_SETUP.md) and
  check its RECORD, or write here, before the run, which patch the runner needs on Windows and why. No Shield scored
  run has happened.

## D9. H1 facts recorded (closes D5) (2026-10-24, 14:25Z to 14:39Z)

- Recorded by the Hexagone operator (Claude) from the app's own screens, nothing changed. Run-sheet row H1;
  screenshots in `<work>/hexagone_h1/`.
- App version 0.3.9 (À propos). Default replacement: "Remplacer par des substituts" (tags such as `[PERSON_1]`;
  outputs use namespaced tokens such as `[a.FNAME_1]`). Rule "Tout masquer". Fast is labelled "Standard" and Precis
  "Analyse approfondie" in the per-synchronisation setting "Vitesse"; Préférences > Système says "Analyse
  approfondie (Précis): Disponible (plus lent)". So Precis IS offered on profile A.
- Model: Système says the local model server is not started, "La protection se poursuit avec le détecteur local
  intégré", because the file `base.Q4_K_M.gguf` (the small local language model) is not present. Fast runs only the
  detection model, so Fast is not affected. Whether Precis uses the language model without that file is not known;
  the H4 operator records what the app shows. No model download was shown in the UI at any time.

## D10. Hexagone masks output file names; name-only mapping rule; operator mechanics (2026-10-24, before any scored Hexagone run)

- **Time:** written 2026-10-24 at about 15:02Z, after the H2 pilot (PILOT files only, never scored) and before the
  first scored Hexagone task. No Hexagone output of any scored set existed. No score of any tool was computed.
- **Found at H2:** the app masks file names. Its folder flow (Synchronisation, destination = our task folder) writes
  `document-<8 hex>.<ext>` (same format as the input) and adds an `AGENTS.md`; its "Télécharger" button (download
  all, saved to `%USERPROFILE%/Downloads` without asking) gives a zip with entries `anonymized-<stem>.<ext>`, where
  any detected value in the stem becomes a placeholder token (PILOT became `a.FNAME_1`); the per-file flow gives
  `<masked stem>.<ext>`. Same bytes in all three (checked by size and SHA-256). The rename rule that
  `collect_outputs.py` expects (fixed prefix or suffix) does not exist.
- **Rule fixed now (H7):** `<work>/collect_hexagone.py` maps by NAME ONLY (names, sizes, hashes and file
  times; never content): R1 one input and one output in the task; R2 zip entry `anonymized-<input stem>` (the
  `collect_outputs.py` rule with `--prefix anonymized-`); R3 zip entry stem with each placeholder token read as a
  wildcard, unique input of the same extension and no rival entry; R4 per-file "Télécharger" of the row showing the
  input name. Anything else counts as failed (no output), as in section 12.1. The manifest points at the
  destination file with the same SHA-256 as the zip entry and keeps its VM file time. `collect_outputs.py` is not
  changed. The scorer reads the manifest (`--outputs-manifest`).
- **Per task, the operator also saves** the task's download-all zip and the app's "Exporter le mapping" JSON to
  `C:/bench/sealed/hexagone/<mode>/<set>/<task>_download.zip` and `<task>_mapping.json`. The app has no CSV audit
  export in its UI; the mapping JSON (placeholder, entity type, original values) is its only documented export of
  the detections. Both stay sealed (section 13).
- **Operator mechanics:** the keys helper (`gui.sh keys`) does not reach the app or its dialogs (tested: text not
  typed), so every folder is chosen with mouse clicks in the Windows folder dialog (This PC > C: > bench > ...).
  The app was restarted after the pilot from its desktop icon (parent process explorer, as a user does), not from
  the launch helper. The window is maximised (no setting).
- **Auto-update:** Préférences > Général > "Installer les mises à jour automatiquement" is ON. Section 2 says
  "auto-update off only if the app offers it in its settings"; the operator's task rule says change no setting
  except the mode switch of H4. It is left ON; the version (À propos) is checked before the first and after the last
  task of every set and written in the run sheet. A version change during a set is reported with that set.
- **Effect:** none on accuracy (same files, same app path, same defaults). If a name rule cannot map a file, that
  document counts as failed (fully exposed), which can only lower Hexagone's protection; the count of R3, R4 and
  unmapped documents is reported per set.

## D11. Name rule fails on multi-file tasks; content-overlap assignment for those tasks (2026-10-24, about 15:50Z)

- **Time:** written 2026-10-24 at about 15:50Z, during H3 Fast (REF, FR-PII-Bench and MAPA done, Max not started).
  No Hexagone output content had been read by anyone (only names, sizes and hashes). No score of any tool existed.
- **Found:** in the FR-PII-Bench (300 files) and MAPA (19 files) tasks, EVERY download-all zip entry is
  `anonymized-<x>.FNAME_<n>.<ext>`: the whole file stem is replaced by one placeholder, and the app's mapping
  export does not list these file-name placeholders. So the D10 name rules R2 and R3 map nothing in a multi-file
  task, and R4 (one click per file) is not workable for about 800 files per mode. R1 (one input, one output) still
  maps REF and PILOT.
- **Rule fixed now, before any output content is read or scored:** for a task that R1 and R2 do not map,
  `<work>/match_hexagone.py` assigns outputs to inputs of the same task and the same extension by text
  overlap, with no person looking at the texts: both sides read with reader 1.1 (`extract_text.py`); output
  placeholder tokens `[x.TYPE_n]` removed; tokens = runs of letters and digits, lower case, accents removed;
  similarity = size of the token multiset intersection; one-to-one assignment that maximises the total
  (deterministic order: higher similarity first, then input order, then output name). A pair is kept only when
  its overlap is at least 30 % of the input's tokens; any other input counts as failed (fully exposed). The
  report gives, per set, the pairs kept, the inputs failed, the median overlap and the number of pairs whose best
  and second-best inputs are within 5 % (ties). A tie between outputs that are identical apart from masked values
  gives the same score whichever input they are given to. The matcher writes the same manifest as D10
  (`--outputs-manifest` for the scorer) and never writes output text.
- **Effect:** none on what the app did; only on which output file the scorer pairs with which input. An unmatched
  document counts against Hexagone (failed). This replaces "no content read" in H7 for these tasks only.

## D12. The D11 30 % threshold drops documents the app did process; primary manifest without threshold (2026-10-24, about 17:44Z)

- **Time:** written 2026-10-24 at about 17:44Z, after H3 Fast and the first H7 mapping run, before any score of any
  tool. Seen: only the matcher's counts (pairs kept, overlap ratios, ties), never output text or scores.
- **Found:** on FR-PII-Bench Fast, the app wrote 300 outputs for 300 inputs and showed "300 / 300 Fichiers
  protégés", but the D11 rule (keep a pair only if its overlap is at least 30 % of the input tokens) dropped 34
  pairs (median overlap 0.49; these short documents are mostly personal data, so a well-masked output shares few
  tokens with its input). Counting them as failed (fully exposed) would charge Hexagone for a measurement limit,
  not for a tool failure (section 12.1 counts a document as failed when the TOOL fails on it).
- **Rule:** PRIMARY manifest (`manifest.jsonl`): when a task has exactly one output per input of each extension, every
  pair of the D11 one-to-one assignment is kept (threshold 0). SECONDARY manifest (`manifest_t30.jsonl`): the D11
  rule as first written (threshold 0.30), reported as a sensitivity reading. Both come from the same assignment;
  the report gives the count of pairs under 0.30 and of ties per set. Known limit: inside a tie group of templated
  documents (FR-PII-Bench) a pair can be swapped; for two outputs that differ only in masked values this does not
  change any count, otherwise it can move a few items either way. Readers must see both readings.

## D13. Precis input folders are byte-identical copies (2026-10-24, about 17:55Z, before any Precis task)

- **Found:** when the first Precis synchronisation (REF-1) was set up, the app refused the source folder: "Ce dossier
  est déjà utilisé par l'automatisation « Synchro 2026-10-24 (3) »" (the Fast synchronisation of REF-1); the start
  button stays disabled (screenshot `<work>/hexagone_h1/h4_folder_in_use.png`). Deleting the Fast
  synchronisations could delete app data and is not needed.
- **Change:** H4 reads `C:/bench/precis_in/<set>/<task>/`, copies of the H3 input folders with the same file names
  and bytes (650 files, each SHA-256 checked against PREREG_DATA at copy time: 650 of 650 OK); for Judilibre only
  the 50 files of the Precis subset (`precis_subset.txt`, SHA-256 in PREREG_DATA). Outputs go to
  `C:/bench/out/hexagone/precis/<set>/<task>/` as planned.
- **Mode switch (H4):** in this app the speed is a per-synchronisation setting ("Réglages du masquage" > Vitesse:
  "Standard" | "Analyse approfondie"); for each Precis task the operator selects "Analyse approfondie" there before
  starting. The app was restarted before H4 (quit 17:46Z, relaunched from the desktop icon 17:46:44Z). After the
  restart Préférences > Système shows "Vitesse de génération 38 tok/s", "Temps estimé par page ~13s", "En attente du
  serveur de modèle local..." (screenshots `h4_systeme_*.png`); at H1 (14:28Z) it said the language-model file was
  missing. The operator did not download or change anything; the app's own state changed in between.
- **Effect:** none expected on accuracy (same bytes, same names, same order); the folder path differs. If the app
  cached results by content across modes, Precis task times would be about as short as Fast; the times are reported.

## D14. H4 Precis stopped after REF and FR-PII: the Remote Desktop session was disconnected (open, 2026-10-24 about 20:50Z)

- **What happened:** at about 20:13Z the session of user `<owner account>` went from Active to Disconnected (`quser`: "Disc",
  idle since about 20:13Z). The operator did not disconnect it. In a disconnected session the screen capture is
  blank (white) and clicks reach nothing, so the app cannot be operated. The app kept working in the background:
  the Precis FR-PII-Bench task finished at 20:31:29Z (300 outputs). The operator did not try to reconnect or unlock
  the session (that needs Hadi's own Remote Desktop login).
- **Done in H4:** REF 5 of 5 tasks, FR-PII-Bench 1 of 1 task (300 documents). For FR-PII-Bench Precis the
  download-all zip and the mapping JSON were NOT saved (the export clicks came after the disconnect); its outputs
  were taken from the destination folder and mapped by D11/D12 (no name rule needed).
- **Not run yet (Precis):** MAPA (1 task, 19 documents), Max (7 tasks, 33), Judilibre Precis subset (1 task, 50),
  English (2 tasks, 241). They are NOT `not_run` in the sense of section 17.5: the trial runs until about
  2026-10-31T12:09Z and they can run once Hadi reconnects. Inputs are ready in `C:/bench/precis_in/` (hash-checked),
  output folders exist. Resume notes: `<work>/gui/operator_h3h4/` (scripts; `prepP.sh <setrow>
  <taskrow>` builds a Precis synchronisation; set rows in the folder dialog: en 1, frpii 2, judilibre 3, mapa 4,
  max 5, pilot 6, ref 7; the start button is at y 556, or y 676 after ticking the large-run box at y 612; check each
  set-up screenshot before starting; scripts hold this session's scratchpad paths).
- **Other facts for H4:** a local language-model process `llama-server` (session 2) runs during Precis; the
  protocol sampler (`sample_memory.ps1 -Name hexagone`) does not include it, so a second sampler with
  `-Name llama` was added from REF-2 on (both CSVs sealed; REF-1 has the hexagone one only). Peak working sets on
  REF Precis: hexagone processes 1,687 to 1,755 MB; llama-server 2,568 to 3,760 MB (rising task after task). One
  poll ssh call hung from 20:08Z to 20:44Z (no effect on the app; the FR-PII end mark is late; the last output time
  is the timing source).

## D15. Shield and Presidio runs on profile A: setup written before the runs (2026-10-24, about 21:25Z; closes D8)

- **Time:** written 2026-10-24 at about 21:25Z, before any scored Shield 0.3.1 or Presidio run on any set. No Shield
  0.3.1 masking output of REF, Max or English existed; no Presidio output existed; no score of any tool was read by
  this session. `VM_BUSY` was created at 20:49:42Z ("shield and presidio runs").
- **D8 closed:** before the first run, the clean wheel (`C:/shield/dist/ragbase_shield-0.3.1-py3-none-any.whl`,
  SHA-256 `b15c9771...c2b558`, as in PREREG_DATA) is reinstalled with `pip install --force-reinstall --no-deps`, and
  every installed `ragbase_shield/` file is compared with the wheel's own bytes. The runner uses only
  `Service.add_dossier` and `read_document`; it needs none of W1 to W4. The patched files stay on the Mac
  (`<work>/win/patched_W/`).
- **Environment of the runner (not a Shield setting):** `RAGBASE_SHIELD_MODELS_DIR=C:/shield/models` (the runner
  makes a fresh Shield home per run, which holds no model; the product reads the models from this variable or from
  the home); `PYTHONUTF8=1` (WINDOWS_SETUP.md section 8). Shield sets the Hugging Face offline variables itself.
- **Set folders:** the runner needs `<set>/tasks.json` and `<set>/input/<file>`. They are built on the VM in
  `C:/shieldrun/sets/` from `C:/bench/in/<set>/<task>/` (read only; nothing is written under `C:/bench/in` or
  `C:/bench/precis_in`, which Hexagone watches) and from the Mac `tasks.json`; every file is checked against
  PREREG_DATA before the runs. The runners and the reader are checked against PREREG.sha256.
- **Peak memory:** `run_shield_files.py` calls `GetCurrentProcess()` without a 64-bit return type, the bug that gave 0 MB
  in the smoke test (WINDOWS_SETUP.md section 7). Its own value is recorded but is expected to be wrong. Peak memory
  is also taken from outside the process: the Windows `PeakWorkingSet64` of the runner process, read every 0.5 s,
  and `windows/sample_memory.ps1 -Name python` (once per second). The runner is not changed.
- **Machine state:** Hexagone stays open in Hadi's disconnected session (not touched). Its process count, CPU time
  and memory are logged before and after each run (section 4.1 says no other program runs; stated condition).
- **Calendar:** the speed session (section 10.3) runs on the same day, right after the accuracy runs, in fresh
  processes (section 10.1 says day 3). Speed rows: S-R, S-N and S-N2 (AVX2 variables), each with three separate
  processes on the five REF tasks; the first process gives the 5 session values, all three give cold start.
- **Presidio:** protocol section 2 records versions at install (no pin): the newest `presidio-analyzer`,
  `presidio-anonymizer` and the spaCy version they accept, from PyPI, in a new venv `C:/presidio` (Python 3.11.9);
  `fr_core_news_md` and `en_core_web_lg` by `python -m spacy download` (official explosion/spacy-models release);
  the reader pins pdfplumber 0.11.10, pdfminer.six 20260107, openpyxl 3.1.2. The `tldextract` suffix list that
  Presidio's e-mail and URL checks fetch on first use is cached at install time, so the runner's network guard does
  not turn that fetch into document failures. Outputs go to `<work>/sealed/presidio/`.
- **Pre-registered parity sample (Windows against Mac, same wheel):** S-R: every document of the six sets (798);
  S-N: every document of REF, FR-PII-Bench, MAPA, Max and English (598; Judilibre left out for Mac compute time). The
  Mac runs `run_shield_files.py` unchanged, with the same wheel installed `--no-deps` in a new venv
  (`<work>/mac_venv_031`), the dependency versions of the worktree venv (torch 2.2.2, transformers
  4.57.6, gliner2 2.1.0) and the same model revisions (`~/.ragbase-shield/models`). Pass = the same SHA-256 for each
  output file and the same run-log status. Any difference is reported per set; it never changes which output is
  scored (the Windows output is the profile A result).
- **Presidio install facts (2026-10-25, 02:50Z to 04:24Z, before any Presidio run on a set):** presidio-analyzer
  2.2.364, presidio-anonymizer 2.2.364, spaCy 3.8.16, thinc 8.3.13, fr_core_news_md 3.8.0, en_core_web_lg 3.8.0
  (explosion/spacy-models release wheels), tldextract 5.4.0, pdfplumber 0.11.10, pdfminer.six 20260107, openpyxl
  3.1.2, Python 3.11.9. The newest `preshed` (3.0.14, a spaCy dependency) makes every spaCy model fail to load on
  Windows (`OverflowError: Python int too large to convert to C ssize_t` in the tokenizer); `preshed` 3.0.13 loads
  both models. The venv uses 3.0.13. The `tldextract` cache was filled once with the network on; a check under the
  runner's guard then found e-mails and URLs with 0 network attempts. Presidio's French registry has 10 recognizers
  (Crypto, Date, Email, Iban, Ip, MacAddress, MedicalLicense, Phone, Spacy, Url).
- **Run mechanics:** the runs are started by `C:/shieldrun/code/drive.ps1`, launched through WMI (`Win32_Process`
  Create) so that an SSH drop cannot stop them. Order: Shield pilot (unscored), Shield per set (rules then ner, set
  order of section 10.2), Shield speed rows, Presidio pilot (unscored), Presidio per set, Presidio REF speed (three
  processes). The Mac parity runs (D15) run on the Mac at the same time; they do not touch the VM.
- **Operator error, attempt 1 (2026-10-25, 04:26:32Z to 04:27:35Z):** a variable-name clash in the driver
  (PowerShell names ignore case, so the loop variable `$s` overwrote the runner path `$S`) made Python start with a
  set name instead of the runner script. 11 process starts ended in about 1 s with "can't open file"; Shield never
  ran, no output and no run log were written. The driver was stopped, fixed (`$SHIELD_RUNNER`, `$setName`) and
  started again at 04:28:35Z (section 12.2: operator error; no score existed). Its logs are kept in
  `C:/shieldrun/logs/attempt1/`. The Shield pilot (PILOT files, unscored) had run correctly before the clash.
- **Outcome (2026-10-25, written after the runs, before any score):** Shield runs 04:28:40Z to 05:37:41Z, Presidio
  05:37:45Z to 05:44:00Z; every process exit 0; 0 network attempts in every run. `VM_BUSY` deleted at about 05:46Z.
  (a) The runner's own peak memory is 0.0 MB in every run (the expected handle bug); the outside readings are used.
  (b) Parity: 0 of 1,394 output files have the same bytes on Windows and on the Mac, because the runner writes
  text with Python's text mode, which writes CRLF line ends on Windows. After CRLF is turned into LF (the reader of
  section 7 does this), 1,394 of 1,394 files are identical, and the frozen reader gives the same text for all
  1,394; run-log statuses are the same for all 1,396 documents. The pre-registered byte rule fails only on line
  ends; the text that any scorer reads is the same. (c) Shield 0.3.1 cannot read `.xlsx`: Max
  `D/Pièce 9 - décompte heures sup.xlsx` is `failed` in S-R and S-N on both machines (counts as fully exposed,
  section 12.1). (d) S-N REF task times are 25.7 to 28.3 s in the per-set run and 20.3 to 21.5 s in the speed
  processes 55 to 60 minutes later; the cause is not known (Hexagone used about 0.07 core in both periods). All
  values are reported; none is dropped.

## D16. Scoring step: how the frozen scorer is fed (2026-10-25, about 09:10Z, before any score)

- **Time:** written 2026-10-25 at about 09:10Z, before any score of any tool. Checked: no score or compare file
  exists under `<work>/` apart from the frozen validation (`validate/`, `critic/`).
- **Checks before scoring:** `PREREG.sha256` 685 of 685 OK; `PREREG_DATA.sha256` 829 of 829 OK; `score_text.py`
  (laptop-score-1.1), `compare_runs.py` (1.1) and `extract_text.py` (laptop-extract-1.1) have their frozen hashes;
  `score_text.py --selftest` OK; reader libraries as pinned (`check_versions()` empty). Mac, Python 3.11.4, venv
  `<work>/mac_venv_031`. Note: the D2 hash table prints the v1.1 `score_text.py` hash without 4 of its
  characters; the right value is in `PREREG.sha256` (`d2e32fcfcd8f08a3...51281e2`).
- **What is scored:** S-R and S-N: the Windows outputs (profile A, D15) in `runs/shield_A/shield_{rules,ner}/<set>/`
  with their run logs, six sets. P: `sealed/presidio/<set>/`, six sets. T: `sealed/tonic/<set>/`, REF, FR-PII-Bench,
  Max, English (MAPA and Judilibre are not sent by protocol section 9.2; Tonic RUN_NOTES.md). H-F: six sets. H-P:
  REF and FR-PII-Bench only.
- **Manifest join (mechanical, no pair changes):** the Hexagone manifests of D10 to D12 carry the input file path as
  `doc_id` (the run-log key). `score_text.py` looks up `--outputs-manifest` rows by the gold `doc_id` only, and for
  REF, FR-PII-Bench, MAPA, Judilibre and English the gold `doc_id` is the file name without its extension. Fed as
  they are, every Hexagone document of those sets would read "no output file" (failed). So a copy keyed by the gold
  `doc_id` is written next to each manifest (`manifest_scoring.jsonl`, `manifest_t30_scoring.jsonl`): for each gold
  document, the row whose `doc_id` equals the gold `doc_id` or, when none does, the gold `file` (the rule of
  PROTOCOL_ADDENDUM_1.md 17.2 point 8 for run-log rows). Same output path, same pair. The scorer is not changed.
- **Two readings on FR-PII-Bench (D12):** H-F and H-P are scored with the primary manifest and with the 30 % one;
  both are reported and both are compared. On the other sets the two manifests are identical (match reports: 0 pairs
  under 0.30), so there is one score.
- **Comparisons (section 11.2):** `compare_runs.py` on each set, S-R and S-N against every other row that ran the
  set, and S-R against S-N. H-P on REF and FR-PII-Bench only; T on REF, FR-PII-Bench, Max and English only. Claim
  rules as sections 11.3 and 17.4, applied by `compare_runs.py`; the overall rules of 11.3 ("Shield beats X") are
  read from its verdicts.
- **Pending is not `not_run`:** Precis MAPA, Max, Judilibre subset and English are pending (D14: the trial runs to
  about 2026-10-31T12:09Z). They are not scored and not counted; every table says "pending". The H-P rows are
  therefore partial, and the overall Precis claim of section 11.3 cannot be read yet.
- **Speed:** Hexagone REF task times come from `RUNSHEET_HEXAGONE.csv` (start mark to last output file time, and
  start mark to end mark), day-1 values only. REF-1 Fast starts at the Mac-side click time (its start mark failed,
  run sheet). The Hexagone speed session (H5), its cold start and profile B (H6) are not done, so every speed
  comparison with Hexagone is provisional. Tonic times (Mac client, network included, D3) are never used for a
  speed claim.
- **Where the score files go:** Shield per-document scores in `<work>/scores/` (Shield's own outputs are
  not sealed, section 13). Every Presidio, Tonic and Hexagone per-document score file and every `compare_runs.py`
  output in `<work>/sealed/scores/`. Only aggregate counts leave: `evaluation/laptop/RESULTS.md`.
- **Outcome (written after the scoring, 2026-10-25 about 09:45Z; no rule above changed):** 32 scorer runs (S-R 6, S-N
  6, P 6, H-F 6, T 4, H-P 2, and the two 30 % readings) and 46 `compare_runs.py` runs, every one exit 0; the
  reader version check is empty in every run; the re-keyed manifests have one row per gold document (Fast 798, Precis
  305), with the output paths of the originals (0 unmatched). `PREREG.sha256` and `PREREG_DATA.sha256` still OK after the scoring. Aggregate tables:
  `evaluation/laptop/RESULTS.md`.

## D17. Check 1: independent re-score; corrections made after the scores were seen (2026-10-25, about 10:05Z)

- **Time and status:** written 2026-10-25 at about 10:05Z, AFTER every score and comparison of D16 had been computed and
  read. Everything below is a post-score correction and must be read as such. No frozen file changed: `PREREG.sha256`
  685 of 685 OK, `PREREG_DATA.sha256` 829 of 829 OK after the check. `src/` and `tests/` were not opened or changed.
- **What was done:** a second scorer written from the protocol text (rules 8.1 and addendum 17.2), not importing
  `score_text.py` (it shares only the frozen reader, because the gold offsets are in the reader's text), with another
  alignment method (line diff, token diff, moved blocks, local gaps; no repair pass). It re-scored all 32 runs from the
  inputs, the gold and the tool outputs. Disagreements and alignment-free hunts were read item by item (sealed outputs
  read for scoring only). Scripts: `<work>/scoring/check1/`; per-document results and corrected files:
  `<work>/sealed/check1/` (sealed). Only counts leave.
- **Finding 1, Hexagone Fast FR-PII-Bench pairs (D11, D12):** 172 of the 300 D11 pairs join an output to the wrong input
  of the same document type (masked outputs of one type tie on text overlap). Shown two independent ways: (a) the app's
  own mapping export (`frpii_mapping.json`, saved at H3 under D10) put back into each output gives a one-to-one match,
  overlap 0.84 to 1.00, next best at most 0.75; (b) the app writes outputs by input size, smallest first; output time
  rank against input size rank, inside each document type, gives the same 300 pairs. Corrected manifest:
  `sealed/check1/manifest_frpii_fast_mapping.jsonl`; the frozen scorer, unchanged, run on it: P1 strict 72 (was 68),
  value 45 (same); 30 % cut (D11 overlap rule applied to the corrected pairs: the same 34 invoices under 0.30) 336 (was
  333), value 315 (same). Every claim is the same (`sealed/check1/corrected/`).
- **Finding 2, Hexagone Precis FR-PII-Bench pairs:** no mapping export exists (D14). The order rule of finding 1 (proven
  on Fast only) gives other pairs than D11 for 287 of 300 outputs, but the same P1 numbers (3 and 3; 30 % cut 307 and
  307) and the same claims. RESULTS keeps the D11 numbers for Precis and gives the order-rule reading as a note.
- **Finding 3, frozen scorer alignment (Tonic, Max):** in one Max invoice file (3 pages), the repair pass of addendum
  17.2 point 2a matched a short word inside an address to an identical word outside gold that the tool had deleted
  further down. The rule then left the address's identifying word without a partner, so it read as changed, though it
  is still in the output at its place. The second scorer, a reading at the place, and the frozen scorer re-run with the
  second scorer's alignment for that one file all give the same corrected counts for the Tonic row [public
  extract: the Tonic counts of this finding are left out, Tonic's terms]. Every claim is the same [public extract:
  left out, Tonic's terms].
- **Finding 4, MAPA gold (frozen, not changed):** 8 court-city keep items cover the same words as 8 others (the
  pattern-found court cities of section 8.3, "99 + 9 found by pattern", overlap the MAPA ones). Without duplicates: 1,336
  must-stay-clear items; H-F 571, P 235, S-R and S-N 0. One MAPA gold entity is nested inside another; S-R and S-N count
  that exposure twice. Reported as notes; the frozen gold and its headline counts stay.
- **Other checks with no correction:** no false exposure and no false alteration found by alignment-free hunts; every
  failed document counted as fully exposed; no output used twice; every Hexagone output inside its task folder and time
  window; the other sets' Hexagone pairs (REF, MAPA, Max, Judilibre, English) all confirmed by the mapping export; no
  other job on the VM in a timed window (Mac gcloud log, `machine_state.csv`). Two small text fixes in RESULTS: Table 14
  (786 Fast pairs by overlap, not 788) and Table 11 (S-N REF memory 3,721 to 3,771 MB). Timing note: the H-F REF start
  marks of REF-2 to REF-5 are 2.9 to 4.4 s before the click; REF-1 starts at the click; no claim changes.

## D18. Sealing fixes after the fairness check (2026-10-25, orchestrator, after scores were known)

- `<work>/scoring/aggregates.json` held 114 per-document competitor rows outside the sealed folder:
  moved to `<work>/sealed/scoring/aggregates.json`.
- RESULTS.md Table 4 "Reasons" named failed competitor documents with their retention values: rewritten as
  aggregate counts only; added one finding of the check about the Tonic row [public extract: left out, Tonic's
  terms].
- RESULTS.md holds internal Tonic numbers (Tonic terms, protocol 4.3): added to `.gitignore`; a public copy without
  Tonic numbers must be made before any publication.
- No score, pair or claim changed.

## D19. Hexagone operator 2: H4 resumed, late FR-PII Precis exports, click time log (2026-10-25, about 10:17Z, before any score of the new tasks)

- **Time and status:** written 2026-10-25 at about 10:17Z by the second Hexagone operator (Claude), before any new
  Hexagone task. Scores of H-F (six sets) and H-P (REF, FR-PII-Bench) exist and were computed by other sessions
  (D16, D17); this operator has not opened any score file or any output text. `VM_BUSY` created 10:09:25Z.
- **Checks before work:** `PREREG.sha256` OK, `PREREG_DATA.sha256` OK (`freeze.py check`). The 648 files under
  `C:/bench/precis_in/` (REF 5, FR-PII-Bench 300, MAPA 19, Max 33, Judilibre subset 50, English 241) hashed on the VM
  at 10:10Z: 648 of 648 equal to PREREG_DATA; the Judilibre folder holds exactly the 50 files of `precis_subset.txt`.
  Session of `<owner account>`: Active (session 2). App processes started 2026-10-24 17:46:48Z (the H4 restart of D13), still
  running; no `llama-server` process at 10:09Z. App version 0.3.9 (À propos, 10:15Z).
- **H4 resumes in the same app session** (no restart): protocol H4 asks for one restart before Precis; it was done at
  17:46Z on 2026-10-24 (D13). The app was idle about 13.5 hours in between. Same procedure as D13 (one synchronisation
  per task, source `C:/bench/precis_in/<set>/<task>`, destination `C:/bench/out/hexagone/precis/<set>/<task>`,
  "Analyse approfondie" set in the synchronisation's own settings before start).
- **Late exports for FR-PII-Bench Precis (closes the export gap of D14):** at 10:13:32Z the app's download-all zip
  (114,998 bytes) and at 10:14:27Z its "Exporter le mapping" JSON (263,006 bytes) were saved from the Precis FR-PII
  synchronisation page (the only synchronisation named "Synchro 2026-10-24" with frpii to frpii; the Fast one is
  "(8)"), about 13.7 hours after the task ended; the review pane was never touched in between. Saved sealed as
  `C:/bench/sealed/hexagone/precis/frpii/frpii_download.zip` and `frpii_mapping.json`. This makes the mapping-export
  method of D17 finding 1 possible for Precis FR-PII; scores computed before (D16, D17) are not changed by this
  operator.
- **Click time (D17 timing note):** start marks of H3 were 2.9 to 4.4 s before the click. From now on the start
  click of each task uses the same click path as `gui.sh click` (a one-off scheduled task in session 2), with a copy
  of `click.ps1` that also reads the VM clock right before and right after the mouse button events
  (`C:/shield/gui/clickmark.ps1`, log `C:/bench/click_times.csv`). The mark_time start stays (protocol H3) and both
  are written in the run sheet; task time is taken from the click.

## D20. Hexagone H5 speed session: set-up written before the session (2026-10-25, about 13:40Z, before H5)

- **Time and status:** written 2026-10-25 at about 13:40Z, while the H4 Judilibre Precis task ran, before any H5 action.
  No H5 time existed. This operator has not opened any score file.
- **Calendar:** protocol 10.1 puts the speed session on day 3 ("next day"). It runs on 2026-10-25 right after H4 (trial
  day 2), on profile A. The app has run since the H4 restart (2026-10-24 17:46Z); H5 restarts it (below).
- **Inputs:** the app accepts one synchronisation per source folder (D13), and REF-1 to REF-5 are already used by the H3
  and H4 synchronisations. H5 reads byte-identical copies in `C:/bench/speed_in/fast/REF-n/REF-n.docx` and
  `C:/bench/speed_in/precis/REF-n/REF-n.docx` (made 10:27Z from `C:/bench/precis_in/ref/`; all 10 SHA-256 equal to
  PREREG_DATA). Outputs go to `C:/bench/out/hexagone/speed_fast/ref/REF-n/` and `.../speed_precis/ref/REF-n/`. One
  synchronisation per file, in REF-1 to REF-5 order; "Vitesse" Standard (Fast, the default) or "Analyse approfondie"
  (Precis) set in the synchronisation's settings. Distinct files: the per-session cache of section 10.3 cannot apply
  inside a session. If a task returns in about 1 s (a cache across sessions or across byte-identical copies), it is
  reported as such and not dropped.
- **Restart and cold start (10.3):** before each mode the app is quit with its own menu (Hexagone AI > Quitter
  Hexagone AI), the operator waits until no `hexagone*` and no `llama*` process is left (Windows process list), then
  starts it again by a double-click on its desktop icon, as a user does (parent explorer). Three launches per mode;
  the third launch is the fresh app session of that mode's five tasks. Launch time = the VM clock read at the
  double-click (`clickmark.ps1`, D19), with a mark_time "launch" just before. Ready time = the first screen frame that
  shows the app's main window with its left menu and page content (not a splash or a blank window), read by the
  operator from screen frames captured every 0.3 to 0.5 s with an OS-level screen copy in session 2
  (`C:/shield/gui/watch.ps1`, the same capture as the screenshot helper, small JPEG frames with their VM time; it
  reads nothing of the app). The frame capture runs only during the cold starts, never during a timed task.
- **Task time:** start = the VM clock at the click on "Démarrer la synchronisation" (`clickmark.ps1`); end = the last
  output file time (protocol 10.3), and the mark_time "end" after the output count is complete. Both reported.
- **Memory (10.4):** `windows/sample_memory.ps1` (unchanged) with `-Name hexagone` and, because Precis runs a local
  `llama-server` process (D14), a second sampler with `-Name llama`, both once per second, started before each task's
  click and stopped after its end; free RAM read at the start of each session.
- **Exports:** download-all zip and mapping JSON saved for every H5 task after its end mark (outside the timed window),
  sealed in `C:/bench/sealed/hexagone/speed_<mode>/ref/`.
- **Nothing else on the VM:** the operator checks the process list before each session (no Shield, Presidio or other
  job; VM_BUSY held by this operator).

## D21. H5 cold start: the frame watcher was blocked by the antivirus; ready time read another way (2026-10-25, about 15:56Z, during H5, before any score)

- **What happened:** the app was quit at 15:50:16Z (menu "Quitter Hexagone AI"; at 15:50:57Z no `hexagone*`, `llama*` or
  `msedgewebview2` process was left; free RAM 11,963 MB) and launched again by a double-click on its desktop icon at
  15:51:33.03Z (VM clock at the click; mark_time launch 15:51:28.998Z). The frame watcher of D20 (`watch.ps1`) wrote
  no frame: Windows Defender blocks it ("This script contains malicious content and has been blocked by your
  antivirus software", checked by running it once in the SSH session). The operator did not change, disable or work
  around the antivirus. So this first Fast launch has no ready time; it counts as a launch, not as a cold-start value.
  The app came up in a window that is not maximised (it was maximised before the quit), on the Accueil page "Tout est
  prêt".
- **Ready time from now on:** (a) a process-list observer in session 2 (`C:/shield/gui/pwatch.ps1`, Get-Process every
  about 0.27 s for 60 s: count and names of the app processes and the main window title and handle; log
  `C:/bench/pwatch_<label>.csv`), started before the double-click; (b) screenshots with the normal helper, taken one
  after the other right after the double-click, each read by the operator, with the VM file time of each capture.
  Reported per launch: launch to main window (a), launch to the first screenshot that shows the ready page (b, an upper
  bound) and to the last screenshot that does not (b, a lower bound). The screenshot interval is several seconds, so
  (b) is coarse; both readings are given and none is dropped.
- **Count:** three cold-start values per mode as in 10.3, so Fast has four launches (the first without a value). The
  third valued launch of each mode is that mode's fresh session for the five tasks; the window is maximised (window
  control, not a setting) before the first task, as in H3 and H4.

## D22. H5 Precis stopped after 3 of 5 tasks: the Remote Desktop session was disconnected again (open, 2026-10-25, written about 21:15Z)

- **What happened:** the Precis REF-4 speed task was clicked at 2026-10-25T18:14:41.23Z (VM clock, `clickmark.ps1`; the
  scheduled-task click returned 0). At about 18:15Z the session of user `<owner account>` went from Active to Disconnected (`quser`
  at 18:45:35Z: "Disc", idle 30 min; at 19:20:24Z: idle 1:05). The operator did not disconnect it. A screenshot at about
  18:46Z is fully black (every pixel 0). The poll SSH call started at 18:14Z hung (as in D14) and was stopped by the
  operator on the Mac. The operator did not try to reconnect, unlock or log off.
- **State of REF-4:** no output file in `C:/bench/out/hexagone/speed_precis/ref/REF-4/` at 18:45Z or at 19:20Z; no
  `llama-server` process at any time in the llama sampler of this task (3,896 rows, 18:14Z to 19:20Z), while REF-1 to
  REF-3 Precis each ran one (peaks 2,120 to 2,907 MB). So REF-4 did not run to an output. It is not a tool error on a
  document (section 12.2): it is a machine/session failure, and it gives no H5 value. REF-5 Precis was not started.
  The app (processes started 17:05:39Z) was left running in the disconnected session, untouched.
- **H5 values that exist:** Fast 5 of 5 tasks and 3 cold-start values; Precis 3 of 5 tasks (REF-1 to REF-3) and 3
  cold-start values. Section 10.3 asks for the five REF files in one session: the Precis session is short by two. The
  day-1 Precis values (5) exist. A re-run of Precis REF-4 and REF-5 (and, to keep one session, of the whole Precis H5
  session) needs Hadi to reconnect; the trial runs until about 2026-10-31T12:09Z. Until then every H5 Precis number is
  reported as partial (3 session values + 5 day-1 values), and no speed claim uses it.
- **Other H5 notes:** a status screenshot was taken about 30 s after the click of Precis REF-1 (operator check that the
  task had started); no other action ran during a timed task apart from the output-folder poll (one directory listing
  every 3 s) and the memory samplers, as in H3 and H4.
- **VM_BUSY** deleted after the file collection (this entry), as the operator's instruction says for a disconnect.


## D23. Scoring step 2: how the new Precis rows and H5 are fed to the frozen scorer (2026-10-25, about 21:25Z, before any score of them)

- **Time and status:** written 2026-10-25 at about 21:25Z, before any score of H-P on MAPA, Max, Judilibre or English,
  before any score of the re-paired H-P FR-PII-Bench, and before any H5 number was put in RESULTS. This session had read
  `RESULTS.md` (aggregate numbers of D16 and D17) and the operator report of D19 to D22; it had read no per-document
  score file and no new output text. It does not touch `src/` or `tests/`.
- **Checks before scoring (21:13Z to 21:20Z):** `PREREG.sha256` 685 of 685 OK, `PREREG_DATA.sha256` 829 of 829 OK,
  `PREREG_F1.sha256` OK; `score_text.py` (laptop-score-1.1), `compare_runs.py` (1.1), `extract_text.py`
  (laptop-extract-1.1) have their frozen hashes; `score_text.py --selftest` OK; venv `<work>/mac_venv_031`.
  Manifest checks (`<work>/scoring/op2/prepare_op2.py`, report `sealed/scoring_op2/prepare_report.json`):
  for MAPA 19, Max 33, Judilibre subset 50, English 241 and FR-PII-Bench 300 (mapping pairs), every output exists, is used
  once, is in its task's destination folder, has a file time inside its task's window (run sheet), and has the same
  SHA-256 as one entry of the task's download-all zip (the outputs and the zip entries are the same multiset in every
  task). Run logs: every document `ok`.
- **H-P MAPA, Max, English:** the D10 to D12 primary manifests re-keyed by the gold `doc_id` (`manifest_scoring.jsonl`,
  the D16 rule). They give the same pair as the op2 mapping export and the processing order on every document (19, 33,
  241) and have 0 pairs under 0.30, so there is one reading per set.
- **H-P Judilibre: the Precis subset of 50** (protocol 9.4 H4; `precis_subset.txt`, hash in PREREG_DATA). `compare_runs.py`
  needs the same documents in both runs, and S-R, S-N, H-F and P cover 200. So the scorer gets a subset gold: the 50 lines
  of the frozen `sets/judilibre/gold.jsonl` for those files, byte-identical (`sealed/scoring_op2/judilibre_p50/gold.jsonl`,
  194 indicative gold names; equal to the operator's copy in `h7_op2/`). H-P, S-R, S-N, H-F and P are scored on it with
  the frozen scorer, unchanged. The scorer scores each document on its own, so the 50 per-document results of S-R, S-N,
  H-F and P must equal those of their 200-document runs; this is checked, and a mismatch stops the step. The 200-document
  rows stay the Judilibre headline of S-R, S-N, H-F and P; the 50-document table is the comparison set for H-P. The other
  150 documents are not `not_run` (17.5): the subset is the protocol's design.
- **H-P FR-PII-Bench re-paired (a correction after scores were seen):** the D11 pairs gave the H-P FR-PII numbers of D16,
  and D17 gave the order-rule reading. Now the app's mapping export exists (D19). PRIMARY = the op2 mapping-export pairs
  (`manifest_mapping_scoring.jsonl`, the method of D17 finding 1). 30 % READING = the D11 overlap rule applied to these
  pairs (`sealed/scoring_op2/frpii_precis_mapping_t30_scoring.jsonl`: 38 pairs under 0.30, the same 38 documents as the
  D11 and check 1 30 % readings). SENSITIVITY = the processing-order pairs (`manifest_order_scoring.jsonl`; equal to the
  check 1 time-rank pairs on 300 of 300). The export is weaker than the Fast one: 1,977 placeholders have no value in it,
  and the best-minus-second Dice is under 0.02 for 32 outputs (`scoring/op2/frpii_precis_pairs.py`). It still agrees with
  the order rule, which uses only file times and input sizes, on 298 of 300; the 2 others are two `attestation_employeur`
  inputs of the same size whose two outputs have the same Dice with both, a tie for both methods. RESULTS gives the
  mapping reading, the order reading and the first (D11) reading side by side.
- **Comparisons:** `compare_runs.py` 1.1, S-R and S-N against H-P on MAPA, Max, English, the Judilibre subset (50) and
  FR-PII-Bench (mapping pairs, 30 % reading, order pairs). Score and compare files are new files; no earlier file is
  overwritten.
- **Overall Precis claim (11.3):** read on the H-P rows: the Judilibre P2 claim on the 50-document subset (the only
  held-out H-P data), REF P1 and P2, and no opposite claim on FR-PII-Bench, MAPA, Max or English.
- **H5 speed:** Hexagone values from the H5 run-sheet rows and `sealed/hexagone/_op2_vm_logs/`. Two readings for every
  value: (a) click to last output (D19, D20; day-1 clicks on the Mac clock, 1 s precision, as check 1 read them); (b)
  start mark to last output (protocol 10.3 wording). Median and range over the 5 day-1 values and the session values
  (Fast 10; Precis 8, partial, D22). Speed claims: rule 11.3 on all values (the stricter reading of the first scoring),
  under both readings; no Precis claim while H5 Precis is partial (D22). Cold start as the ranges of D21. Memory:
  `sample_memory.ps1` CSVs of both samplers; "together" = the sum of the two at the same second.
- **Where the files go:** Shield scores `<work>/scores/{S-R,S-N}/judilibre_p50.json`; competitor and Presidio
  scores `<work>/sealed/scores/{H-P,H-P_map,H-P_map_t30,H-P_order,H-F,P}/`; comparisons
  `<work>/sealed/scores/compare/`; scripts `<work>/scoring/op2/` (code only). Only aggregate
  counts go to `RESULTS.md`.
- **Outcome (written after the scoring, 2026-10-25 about 21:35Z; no rule above changed):** 11 scorer runs and 19
  `compare_runs.py` runs, every one exit 0, reader version check empty in every run. Judilibre subset: S-R, S-N, H-F and
  P per-document results on the 50-line gold equal their 200-document runs (50 of 50 each). H-P FR-PII-Bench: the
  mapping-export and order pairs give the same counts as each other and the same P1 as the D11 pairs (3 and 3; 30 %
  cut 307 and 307); secondary numbers move (false-mask regions 1,000 to 998, words changed 3,058 to 3,054, lowest
  retention 0.5185 to 0.5357). No claim of D16 or D17 changes. The overall Precis claim of 11.3 is read on all six sets:
  not allowed (REF P1 and opposite P1 claims on FR-PII-Bench, MAPA and English). H5: the operator's combined medians
  mixed day-1 values from the start mark with session values from the click; RESULTS gives one start event per reading.
  Aggregate tables: `evaluation/laptop/RESULTS.md` (Tables 1 to 15, section "Step 2").

## D24. Check of step 2: independent re-score; text corrections made AFTER the scores were seen (2026-10-25, about 21:55Z)

- **Time and status:** written 2026-10-25 at about 21:55Z, AFTER every score and comparison of D23 had been computed and
  read. Everything below is a post-score correction. No frozen file changed: `PREREG.sha256` 685 of 685, `PREREG_DATA.sha256`
  829 of 829, `PREREG_F1.sha256` OK, before and after the check. `src/` and `tests/` were not opened or changed. No git commit.
- **What was done:** the check-1 scorer (`<work>/scoring/check1/myscore.py`, read again in full before use; it
  does not import `score_text.py`) re-scored the 12 new step-2 runs from the inputs, the gold and the outputs. The Judilibre
  subset gold was built again from the frozen gold and `precis_subset.txt`. Own code for: the H-P pairs (three methods), the
  paired bootstrap (the method of `compare_runs.py` 1.1, written again), the H5 times, memory and cold-start bounds from the
  raw VM logs, and the Mac gcloud log for the H5 window. Scripts: `<work>/scoring/check_op2/` (code only);
  per-document results and pair manifests: `<work>/sealed/check_op2/` (sealed). Only counts leave.
- **Result, numbers:** every new row has the same counts as the frozen scorer, item by item (H-P on MAPA, Max, English,
  Judilibre subset; S-R, S-N, H-F, P on the subset; H-P FR-PII-Bench with the mapping, 30 % and order pairs): 0 items and
  0 keep items differ. The 50-line subset gold is byte-equal to the step-2 copy. S-R, S-N, H-F and P on the subset equal
  their 200-document runs (50 of 50 each). The own bootstrap gives the same claims and intervals as the 19 step-2
  comparisons. The H5 values, medians, memory peaks and cold-start bounds equal RESULTS, except 2 roundings (below).
- **Correction 1, FR-PII-Bench Precis pairs (text only, no count changes).** D23 says the mapping export agrees with the
  processing order on 298 of 300 and that the 2 others are "two `attestation_employeur` inputs of the same size" and "a tie
  for both methods". That is wrong. The step-2 pairing code (`<work>/h7_op2/map_op2.py`) reads only placeholders
  that end in `_<number>`; the Precis outputs also hold a second form (letters, digits, then one letter), so it left 642 of
  the 3,858 placeholder occurrences in place. Read with every form: the mapping export gives one clear best input per output
  (smallest best-minus-second plain Dice 0.112; 0 outputs under 0.02, against 32 with the step-2 pattern), and its pairs
  equal the processing-order pairs on 300 of 300. A third method agrees on 300 of 300: the app numbers its output names
  (`FNAME_<n>`) in processing order, and the Fast output with the same number maps (by the Fast mapping export) to the same
  input. The 2 inputs are not the same size (316 and 334 bytes). So the PRIMARY manifest of D23 has 2 outputs swapped
  between 2 `attestation_employeur` inputs. Scored, the swap changes nothing: the per-document results of the primary
  and of the order manifest are identical in every field. Table 1, 2, 4, 5 and 6 numbers stay. Unknown placeholders: 1,983 of
  3,858 occurrences have no value in the export (D23 said 1,977, counted over the 3,216 occurrences its pattern saw).
- **Correction 2, record of what existed before D23.** D23 says it was written "before any score of H-P on MAPA, Max,
  Judilibre or English". Frozen-scorer results of H-P on MAPA and Max already existed, sealed: the orchestrator ran
  `score_text.py` at 2026-10-25T14:33Z into `<work>/sealed/scores_provisional/H-P/` as a provisional check and
  read their aggregate counts at 14:34Z; the F1 step ran it again at 17:32Z into `<work>/sealed/f1/frozen/H-P/`.
  Both are byte-identical to the step-2 files `sealed/scores/H-P/{mapa,max}.json`. The step-2 session listed the folder at
  21:16Z and did not read its files. Effect: none on any number; on MAPA and Max every pairing method gives the same pairs,
  so D23 had no choice that the earlier results could steer. The statement holds for Judilibre and English.
- **Correction 3, two roundings in RESULTS Table 8:** H-F day-1 REF-4 from the start mark is 27.02 s (27.025, printed
  27.03); H-P day-1 REF-5 to the end mark from the click is 555.63 s (555.625, printed 555.62). No median changes. Also made
  consistent: Hexagone Precis measured "7.0 to 10.5 min from the click" (Table 9) in the two summaries (they said 10.6, the
  start-mark reading).
- **Note added, day-1 click clock:** the day-1 clicks are Mac times in whole seconds, and the run sheet (H3 REF-1) says the
  Mac clock was about 1 s behind the VM. The gaps from mark to click agree (day 1: 2.9 to 4.4 s; H5, on the VM clock: 3.8
  to 5.3 s). So the day-1 values "from the click" can be about 1 s too long. With 1 s less: Fast median 26.93 s (same),
  Precis median 539.28 s (540.28). The start-mark reading uses the VM clock only. No claim changes.
- **No other job during H5 (checked):** `machine_state.csv` covers only the Shield and Presidio runs (04:28Z to 05:44Z), so it
  says nothing about H5. The Mac gcloud log for 15:45Z to 18:50Z holds only the operator's own calls to the VM (screenshots,
  clicks, marks, polls, memory samplers, process lists, file copies); the last Shield or Presidio call is at 05:45Z. Inside
  the H5 timed windows (click to end mark) the only call apart from the poll, the samplers and the marks is one screenshot
  that started 18.5 s after the Precis REF-1 click. Every sampler call started before the click (10.8 to 18.0 s, log times)
  and was stopped after the end mark. `VM_BUSY` was created at 10:09:25Z (D19) and removed by the operator at about 21:12:34Z.
- **Sealing (checked):** outside `sealed/`, the step-2 files are Shield scores (`scores/S-R|S-N/judilibre_p50.*`, the Shield
  against Shield comparison), scripts and two run logs with exit codes only. None holds a value of any Hexagone mapping
  export (14,969 values of 8 or more characters searched; the only hits are common words) or a placeholder or output name.
  RESULTS holds counts only.
- **Verdict (11.3) after the check:** unchanged. Shield beats Hexagone Fast: no. Shield beats Hexagone Precis: no (REF P1
  and opposite P1 claims on FR-PII-Bench, MAPA and English). Shield beats Tonic: no.

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
- **Checks after the freeze (freeze stage):** at 2026-11-11T09:04:25Z, and again at 09:04:32Z, the four earlier
  hash lists passed `shasum -a 256 -c` (685, 829, 4 and 4 OK), `PREREG_V04.sha256` gave 10 of 10 OK, the wheel
  hash file 1 of 1 and `status_facts/SHA256SUMS` 7 of 7. `VM_BUSY` was absent. The addendum v1.1 has the SHA-256
  `0b77606446306c295f0bf708851d7cf4e821c989439ac5a17f82d10b9bca5325`.
  The freeze stage ran no Shield process and wrote nothing on the VM. `RUN_PLAN.md` and the operator scripts
  (`v04_run/ops/`, hashes in `SHA256SUMS_ops.txt`) were written at the freeze; they are not frozen.
- **Completed by the run stage (times and facts only; log: `<work>/v04_run/RUN_NOTES.md`):** session
  start (first VM command) 2026-11-11T09:08:09Z; `C:/shield_v04` did not exist; machine type `n2-custom-12-16384`
  (read only), the six machine facts of 20.6 equal those of 2026-10-25. Install checked at 2026-11-11T09:12:08Z
  (I3 to I9 OK; the fresh freeze of `C:/shield/.venv` equals the frozen pin list, so no I5 note; `pip check`
  clean; 62 of 62 installed files equal the wheel). Inputs checked at 09:12:38Z (800 files, each twice, 0
  problems). Pilot at 09:12:49Z to 09:13:42Z (both processes exit 0, checks passed). `VM_BUSY` written at
  2026-11-11T09:14:12Z by the v04 run stage and deleted at 2026-11-11T10:06:30Z. Quiet VM: yes (09:14:13Z: 0
  processes of another stage, CPU load 0.7 %, 0 Hexagone or llama processes, 0 user sessions). The 12 processes
  from 2026-11-11T09:14:53Z to 09:58:28Z, all exit 0, one driver run. Speed session: done (6 processes, 09:58:32Z
  to 10:04:13Z, all exit 0; no "before" CPU load above 10 %). Re-runs: none. No operator script was changed. Run
  end check at 10:06:06Z: 0 files written under `C:/shield` and `C:/bench` after the session start. Copy checked
  at 2026-11-11T10:06:32Z (1,688 of 1,688 files equal to `SHA256SUMS_vm.txt`, whose SHA-256 is
  `257ad4cc5750cd542c28680ce7f48dc5fcd991b03e010b2d3f3cef4028621da2`). The five hash lists, the wheel hash file and
  the evidence list passed again at 10:07:32Z (685, 829, 4, 4, 10, 1 and 7 OK). Run closed at 2026-11-11T10:07:51Z. No
  0.4.0 score existed at that time.
- **Completed by the score stage (times and facts only; log: `<work>/v04_run/SCORE_LOG.md`):** first
  0.4.0 score computed at 2026-11-11T10:17:33Z (start of the first frozen-scorer job, S-R4 on REF; its result file
  was written at 10:17:35Z), after the run was closed (10:07:51Z). Before the first job: the five hash lists, the
  wheel hash file and the evidence list passed (10:17:31Z: 685, 829, 4, 4, 10, 1 and 7 OK); no file of a 0.4.0 row
  existed under `scores/`, `sealed/scores/`, `f1/` or `sealed/f1/`; `v04_run/scores_before.sha256` was written (854
  files; its SHA-256 is `edfee17798dea6fe02dd8c5fa8c5433ddf08010bc6ce101e97b29ad2baeae205`). Jobs, one at a time,
  from 10:17:33Z to 10:32:23Z, all exit 0: 23 frozen-scorer jobs (the 12 cells, 2 on the Judilibre Precis subset, 9
  on Max without the workbook), 93 `compare_runs.py` runs, 12 exploratory F1 cells and the bundle
  `sealed/f1/bundle_v04/` (48 common-set jobs). The 50 and the 32 per-document results equal those of the full jobs
  (2 rows and 9 rows). After the last job (10:32:23Z to 10:32:27Z): 854 of 854 existing score files unchanged, 436
  new files, the bundle files of the internal additions byte-identical, the hash lists passed again. No job was run twice. No
  0.4.0 run was repeated after the first score.
- **Completed by the check stage (times and facts only; report: `<work>/v04_run/CHECK_V04.md`, SHA-256
  `e870edd96b27be7d0b76b2c15869f90d155006ddceece0b897b000b897e9bcab`):** independent recount on 2026-11-11 from
  10:39:22Z to 11:11:38Z, on the Mac, one process at a time, with a counter that imports nothing from the frozen
  scripts (`v04_run/check_ops/recount_v04.py`; it reuses the check-1 scorer of D17 and D24). P1 strict, P1 value, P2
  and failed documents are the same as the score files in the 12 new cells, item by item (15,604 gold items, 37,418
  keep items, 1,596 document results, 0 differences). The 93 comparisons, with an own bootstrap, give the same lines
  as the files (93 of 93). The claims table, the verdict tables and the table of 0.4.0 against 0.3.1, built again
  from the check numbers, show 0 differences. Differences found: words changed outside gold (equal to the
  exploratory F1 word FP) differ in 5 of the 12 cells, by 37, 1, 37, 1 and 1 words, and region counts differ in 10
  cells. Cause: the alignment of the check counter (a punctuation mark that stands inside and outside a gold span;
  words that its own alignment left unmatched). The score files are right: 39 of 39 and 40 of 40 of these words are
  kept in the output. The same differences exist in the same documents for rows S-R and S-N. No P1 item, keep item,
  status, claim or verdict changes. The scored outputs equal the VM outputs (1,688 of 1,688 files), and the wheel
  hash equals the frozen one. The hash lists passed at the start and at the end of the check (685, 829, 4, 4 and 10
  OK; wheel hash file 1 of 1; evidence list 7 of 7). The check stage also made one labelled extra reading that is
  not in the list of 20.8 and enters no verdict: its own bootstrap of the 0.4.0 rows against the two files that
  check 1 corrected (D17: H-F on FR-PII-Bench, T on Max). The values are in `RESULTS.md`, V4.10. No claim of 20.8
  and no verdict changes.
- **Corrections made after scores were seen:** none. No score file, no comparison file and no F1 file of these rows
  was written again, and no run was repeated.
- **Fact recorded by the check stage and the report stage (working tree; no effect on these rows):** from about
  2026-11-11T11:09Z, during the check stage, another work stream (the preparation of a later Shield build; its
  notes are under `<work>/v05/`) changed `src/ragbase_shield/engine/masker.py`, `merge.py` and `ner.py` and added
  `tests/test_v05_h9.py` in the working tree. At 11:17:49Z `evaluation/audit/audit_bench.py` was modified too. No
  commit (HEAD `49aa899`). The stages of these rows (freeze, run, score, check, report) did not edit `src/` or
  `tests/`. No effect on rows S-R4 and S-N4: they are the wheel of commit `fd8662d`, hash-checked at every stage, and
  every scored output dates from before 10:06:32Z. That work stream holds tool scripts
  (`<work>/v05/model_row_regressions/tools/`) that name Shield's laptop outputs and per-document score files
  (`runs/shield_A`, `runs/shield_A_v04`, `scores/`; the English and Max cells). Rule 20.13 says that a session that
  works on `src/` or `tests/` does not open these files. Neither stage checked which session read what. The point is
  left to the orchestrator. It is written here so that the record of a later build is complete.
- **Completed by the report stage (times and facts only):** start 2026-11-11T11:12:39Z. Hash checks at the start
  (11:12:39Z to 11:20Z), after the tables and files were written (11:34:47Z) and after the last text corrections
  (11:36:44Z), every time: `PREREG.sha256` 685 of 685,
  `PREREG_DATA.sha256` 829 of 829, `PREREG_F1.sha256` 4 of 4, the hash list of the internal row 4 of 4, `PREREG_V04.sha256` 10 of
  10, wheel hash file 1 of 1, evidence list 7 of 7; `v04_run/scores_before.sha256` 854 of 854 and the 436 new score
  files unchanged. `VM_BUSY` was absent. Written: the section "Shield 0.4.0 rows (addendum 4, D28)" at the end of
  `RESULTS.md` (Tables 1 to 15 and the internal sections not edited); `RESULTS_PUBLIC.md` in a new version dated
  2026-11-11, with the 0.4.0 rows in new blocks and new tables (the version of 2026-10-25 is kept byte-identical as
  `RESULTS_PUBLIC_2026-10-25.md`, SHA-256 `718e02e7250f0391a1f87f5c2d7b7bbe2c963abf548e1a1098aee8328f1f6c6c`; its
  summary and its Tables 1 to 10 are in the new file word for word; no Tonic number, no row T, no internal row);
  an internal summary; this entry. The speed and memory tables of 20.6 were
  computed by the report stage from the run records (`v04_run/report_ops/speed_tables.py`: medians, ranges,
  characters per second, sums of task times). The other tables were built by scripts from the set-level files
  (`v04_run/report_ops/`); the lines of all 93 comparison files were parsed again, and their claims equal the score
  stage's record. For reading, the headline tables of the new section print the D17-corrected values of Table 1
  for H-F on FR-PII-Bench and T on Max next to the values of the comparison files of 20.8. The report stage opened
  no output text and no per-document result of another tool. It ran no scorer, no Shield process and no VM command.
  It edited no frozen file and no file under `src/` or `tests/`, and it made no git commit.
