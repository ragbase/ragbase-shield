# Laptop head-to-head: Shield, Hexagone, Tonic (pre-registered protocol)

Version 1.0, 2026-10-23. Status: FROZEN by `PREREG.sha256` (written 2026-10-23, before any Hexagone, Tonic or
Presidio run, and before Shield read the reference document). A data addendum, `PREREG_DATA.sha256`, adds the
hashes of the fresh Judilibre draw and of the Shield wheel; it must exist before the first scored run of any tool.
Every later change is a deviation (section 12).

## Résumé (français)

1. **Question.** Sur l'ordinateur habituel d'un avocat (Windows, peu ou pas de carte graphique), comment se
   comparent Shield, Hexagone et Tonic sur quatre points : (a) protection : données personnelles encore lisibles
   après l'outil ; (b) sur-masquage : juridictions, villes de juridiction, lois, codes et numéros d'article qui
   doivent rester lisibles mais ont été changés ; (c) vitesse et mémoire sur la machine ; (d) où partent les
   données (sur la machine ou dans le cloud).
2. **Machines.** Profil A = la VM Windows actuelle (6 cœurs, 16 Go, sans GPU), soit le
   portable recommandé par Hexagone. Profil B = le portable minimum d'Hexagone (4 cœurs, 8 Go), obtenu en
   redimensionnant la même VM à la toute fin, pour la vitesse seulement (la licence d'essai peut ne pas survivre
   au changement). Une VM n'est pas un portable : elle est plus rapide en charge longue et elle a AVX-512. Nous
   l'écrivons à côté de chaque chiffre.
3. **Outils.** Shield en mode règles (défaut du produit) et règles + GLiNER sur CPU ; Hexagone en mode Rapide et
   Précis (si l'application propose Précis sur cette machine) ; Tonic Textual par son API cloud : Tonic ne tourne
   pas sur un portable (il faut un serveur avec GPU NVIDIA 16 Go), c'est donc la référence cloud ; Presidio comme
   base locale gratuite.
4. **Données.** Uniquement des données publiques et des documents inventés, jamais de données clients. Six jeux :
   le document de référence (5 fichiers Word inventés de 10 pages, environ 29 400 caractères et 20 données
   personnelles par page, comme le fichier de référence d'Hexagone), FR-PII-Bench (300 documents), MAPA Cour de
   cassation (19 décisions), 200 nouvelles décisions Judilibre tirées au sort avec une graine fixe (jamais vues par
   Shield), les dossiers fictifs du protocole Max (33 fichiers) et 241 courriels anglais de PrivacyBench. Tout tient
   dans l'essai de 7 jours d'Hexagone, d'après son propre tableau de vitesse.
5. **Correcteur.** Un seul correcteur pour tous les outils. Il lit le texte d'entrée, le texte de sortie et le
   gold, aligne les deux textes et dit si chaque donnée est encore lisible à sa place, et ailleurs. Il gère tous
   les styles de remplacement (codes, faux noms, balises, suppression). Sur les sorties de Shield v0.3, il donne
   exactement les comptes de nos correcteurs existants (deux petits écarts expliqués : 1 nom sur 672, 7 régions
   sur 6 039).
6. **Équité.** Mêmes fichiers, même ordre, même correcteur, mêmes lecteurs Word et PDF ; réglages par défaut fixés
   avant ; aucun nouvel essai choisi après avoir vu un résultat ; un document en échec compte comme entièrement
   exposé ; chaque essai est journalisé (version, mode, heure, machine, erreurs).
7. **Hexagone.** Nous mesurons seulement (conditions d'Hexagone §10 (vi) et §13). Aucune sortie d'Hexagone ne
   sert à construire ou régler Shield. Pas d'automatisation de l'application, pas d'interception de trafic, pas
   d'API non documentée : une personne utilise l'application comme un avocat. Les sorties sont mises sous scellé.
8. **Ce qui demande Hadi.** L'inscription à l'essai Hexagone et son téléchargement ; le compte Tonic, sa clé et la
   décision sur le risque des conditions de Tonic ; le redimensionnement de la VM ; l'ouverture de SSH sur la VM
   (ou un script lancé en Bureau à distance) ; le feu vert pour télécharger le nouveau tirage Judilibre.
9. **Limite principale.** Sauf le nouveau tirage Judilibre, tous les jeux français ont déjà servi à construire
   Shield (« informé »). Le document de référence est neuf pour Shield mais écrit par l'équipe Shield. Chaque
   chiffre portera son statut.

## Contents

1. Question and outcomes
2. Systems under test
3. Published reference numbers (what the others tested on)
4. Machines, terms and permissions
5. Data
6. Settings fixed in advance
7. Text extraction (fixed readers)
8. Scorer
9. Run procedure per tool
10. Order, schedule, speed and memory
11. Analysis and decision rules
12. Fairness rules, failures and deviations
13. Sealing: who may read what
14. Limits
15. Files
16. Sources

---

## 1. Question and outcomes

On a lawyer's usual machine (Windows, no dedicated GPU), how do Shield, Hexagone and Tonic compare on:

| Code | Question | Primary measure (per set, per tool and mode) |
|---|---|---|
| (a) P1 | Protection: is gold personal data still readable after the tool? | EXPOSED = gold items with at least one identifying token still readable at its place, out of the scored gold items (document properties apart). Lower is better. |
| (b) P2 | Over-masking: are legal terms, courts, court cities, laws, codes and article numbers that must stay readable changed? | MUST-STAY-CLEAR ALTERED = keep items of the classes court, court_city, article, code, law, legal_ref, legal_term with at least one changed letter-or-digit token. Lower is better. |
| (c) P3 | Speed and memory on the laptop profile | Median time of one reference-document task (drop to protected output), its range, cold start, peak memory, on profile A and profile B. |
| (d) P4 | Where the data goes | Table: where the text is processed, what leaves the machine, how we know (documentation or our own check). |

Secondary measures (reported, never used to pick a headline): readable anywhere in the output, the 80 % coverage
reading (FR-PII-Bench's own rule), per-label results, document properties, dates, amounts, roles and placeholders
changed, false-mask regions, words changed outside gold, retention, failures, task times of the full sets.

## 2. Systems under test

| Row | System and mode | Version rule | Where it runs | Settings (section 6) |
|---|---|---|---|---|
| S-R | RAGbase Shield, rules mode (the product default) | commit `577b423d1c8e72dfee4322c3f32a11589eef9e3d` (v0.3.1, branch `v0.2-detection`, `src/` tree `b99c0387`), wheel built from `git archive` of that commit; wheel SHA-256 in PREREG_DATA | the VM, locally | `RAGBASE_SHIELD_NER=off` |
| S-N | Shield, rules + GLiNER on CPU | same build, model `fastino/gliner2-privacy-filter-PII-multi` revision `1cb41660` | the VM, locally | `RAGBASE_SHIELD_NER=on`, `..._NER_MODEL=fastino`, `..._NER_DEVICE=cpu` |
| S-N2 | Shield S-N with AVX2 only (speed rows only) | same | the VM | plus `ATEN_CPU_CAPABILITY=avx2`, `ONEDNN_MAX_CPU_ISA=AVX2` |
| H-F | Hexagone AI Desktop, Fast mode ("Rapide") | the version installed at day 0 (About screen), never updated during the trial; auto-update off only if the app offers it in its settings | the VM, locally (documented) | defaults |
| H-P | Hexagone AI Desktop, Precis mode ("Précis") | same | the VM, locally | defaults; run only if the app offers Precis after its own calibration |
| T | Tonic Textual, cloud API | SDK `tonic-textual` version at install, Textual server version from `/api/version` at start and end | Tonic's cloud (textual.tonic.ai); the VM is only the client | defaults |
| P | Microsoft Presidio (free local baseline) | `presidio-analyzer`, `presidio-anonymizer`, spaCy and model versions at install | the VM, locally | defaults, spaCy `fr_core_news_md` (French), `en_core_web_lg` (English) |

Why v0.3.1 and not a later build: it is the last committed build at the freeze. Its rules-mode masks are the
same as v0.3 on every benchmark (`evaluation/SCOREBOARD.md`, 2026-10-23). A later Shield build may be run on
the same files as a SEPARATE, labelled row; it never replaces the frozen row, and it never sees a competitor
output (section 13).

Shield has never run on Windows (`docs/LAUNCH_CHECKLIST.md` of `ragbase-shield`). The Windows setup is in
`<work>/WINDOWS_SETUP.md`; it needs SSH on the VM (or one script run by Hadi in Remote Desktop).

## 3. Published reference numbers (what the others tested on)

No vendor publishes accuracy measured on a Windows laptop without a GPU. Read on 2026-10-23.

| Vendor number | Value | What it is | Hardware and mode stated | Source |
|---|---|---|---|---|
| Hexagone, PrivacyBench | 88.1 % combined, 93.7 % NER recall, 94.0 % consistency | v2 key (132,909 spans), v2 formula (product), judge `claude-opus-4-7`, "Hexagone AI Local", each export "traité en une tâche", self-run | none, mode (Fast or Precis) not stated | https://www.hexagone.ai/fr/research/privacy-bench (October 2026) |
| Hexagone, PII-INDEXBENCH v1.2 / AI4Privacy 300k / medical set | 97.9 % / 95.3 % / 98.6 % recall | run through the production API ("l'API de production", "api.hexagone.ai") | none | https://www.hexagone.ai/fr/research (studies Sep and Oct 2026) |
| Hexagone, speed table | Windows 2023+, 16 GB, 6 cores: Fast 30 s to 1 min, Precis 3 to 6 min (estimated). Windows 2019, 8 GB, i5 8th gen, 4 cores: Fast 1 min 20 s to 1 min 45 s, Precis 6 to 10 min (measured) | reference file: 10-page Word document, about 30,000 characters, about 20 personal data items per page | the only hardware Hexagone states; no accuracy attached | https://www.hexagone.ai/fr/system-requirements |
| Tonic, PrivacyBench v2.5 (current) | 96.4 % NER recall | Textual Graph Synthesis, v2.5 key (130,370 spans), card revision `a79d9e80` | none | https://huggingface.co/datasets/TonicAI/Privacy-Bench (2026-10-15) |
| Tonic, PrivacyBench v2 (like for like with Hexagone) | 93.9 % NER recall | v2 key | none | card tag `v2` (2026-09-22) |
| Tonic, glossary page | 95.0 % NER recall | PrivacyBench **v1** (messages only, 5 labels, July 2026); stale, not comparable | none | https://www.tonic.ai/glossary/named-entity-recognition (no date) |

Check of our scoreboard (task item): `SCOREBOARD.md` quotes Tonic 96.4 % on the v2.5 key. That is the current
official number. 95.0 % is the old v1 number. 93.9 % is the v2 number to set next to Hexagone's 93.7 %.

Tonic's own hardware note: a self-hosted Textual needs an NVIDIA GPU with 16 GB; without a GPU "performance is
significantly slower" (AWS m5.2xlarge suggested). There is no Tonic desktop or laptop product
(https://docs.tonic.ai/textual/textual-install-administer/deploying-a-self-hosted-instance/system-requirements,
read 2026-10-23). So a lawyer's laptop reaches Tonic only through Textual Cloud: the text leaves the machine.

## 4. Machines, terms and permissions

### 4.1 Profiles

| Profile | Machine | Matches | Used for |
|---|---|---|---|
| A | GCP VM (name and project left out in this public copy), zone `europe-west1-b`, `n2-custom-12-16384`: 12 vCPU = 6 cores with hyper-threading, 16 GB, Intel Cascade Lake, no GPU, Windows Server 2025 Datacenter (`windows-server-2025-dc-v20261013`), 150 GB `pd-balanced` | Hexagone's recommended row ("PC portable Windows récent, 16 Go, 2023 ou plus récent, Core 12e gén. ou Ryzen 7000, 6 cœurs"); lawyer profile P1 of `research_lawyer-hardware.md` (firm laptop 2022 to 2025, 16 GB) | everything: accuracy, over-masking, speed, memory |
| B | the same VM resized at the END to `n2-custom-8-8192`: 8 vCPU = 4 cores with hyper-threading, 8 GB | Hexagone's measured floor row ("PC portable Windows de 2019, 8 Go, Core i5 8e gén., 4 cœurs, une seule barrette"); lawyer profile P2 | speed and memory only |

Why B comes last: the Hexagone trial is tied to a machine fingerprint checked with Hexagone's backend (terms
§4.2). A resize may break it. All accuracy work runs on A first. If Hexagone refuses to run on B, we record it and
do not try to get around it (terms §13).

Facts recorded at the start of every session with `windows/machine_facts.ps1`: OS build, CPU, cores, logical
processors, RAM and modules, free RAM, power plan, Defender real-time state. The VM stays on its default power
plan. During timed runs no other program runs except the app under test, the memory sampler and one PowerShell
window. (Lawyer laptops run Office and a browser at the same time; we do not simulate that. It is a stated limit.)

### 4.2 Limits of a cloud VM as a lawyer laptop (from `research_lawyer-hardware.md`, sources there)

| Limit | Effect on our numbers |
|---|---|
| No 15 W power cap, no thermal throttling, no battery mode | The VM is faster than a business laptop on any task longer than the laptop's turbo window. Notebookcheck: the same Core i5-1235U gives about half the multi-thread score at 15 W that it gives at 33 W. |
| AVX-512 on Cascade Lake; business laptops have AVX2 only (Intel lists no AVX-512 for 12th gen client chips) | Model-based tools (Shield S-N, Hexagone, Presidio's spaCy) can run faster on the VM. For Shield we add the AVX2-only row S-N2. For Hexagone we cannot choose; both sides may benefit. |
| No hybrid cores (performance and efficiency) | Windows 11 can move background processes to efficiency cores; not visible on the VM. |
| Windows Server 2025, not Windows 11 (GCP has no Windows 11 image) | Same kernel family; desktop defaults, Defender and power plans differ. |
| Server memory with more bandwidth; network disk | Model load and token generation can differ from a laptop with an SSD. |
| One machine, one sample | Same-chip laptops vary 2 to 3.7 times in Cinebench multi-thread (Notebookcheck). |

Rule: every speed number is labelled "VM profile A (or B), not a laptop". Comparisons between local tools on the
same VM are fair (same hardware for all). Absolute laptop times need a later run on real laptops (section 14).

### 4.3 Terms and permissions

| Item | Rule | Source |
|---|---|---|
| Hexagone terms §10 (vi) and §13 | No use of Hexagone to build a competing product; no reverse engineering or extraction of code, models or app logic; no automation of the app beyond Hexagone's own integrations; no disproportionate load; no getting around the one-trial-per-device rule. We only MEASURE. A person uses the app through its documented features (folder flow, its own watched-folder automations, CSV audit export). No GUI scripting, no API, no traffic interception, no reading of app files beyond its documented exports, no VM snapshot or clone to restart a trial. No Hexagone output may inform a Shield rule. | https://www.hexagone.ai/fr/terms (desktop tab, "mai 2026"), read 2026-10-23 |
| Hexagone and benchmarks | The terms neither allow nor forbid publishing a comparison. Hadi decides on publication. | same |
| Tonic terms §2(a) and §6 | No use for the benefit of a competitor, no use to build competing models; Tonic's non-public performance information is its confidential information. Our own Textual scores could fall under §6. Rule: Tonic runs only after Hadi's go; Tonic results stay INTERNAL unless Tonic agrees in writing or counsel clears publication. Only invented or synthetic files are sent. | https://www.tonic.ai/terms-and-conditions (updated 2026-02-05), read 2026-10-23; the trial click-through text is to be read at sign-up |
| Data | Only public benchmark data and invented documents. Never client data. | this protocol |

Actions that only Hadi takes (Claude never does them): the Hexagone sign-up with his e-mail and the download of
its installer; the Tonic account and its API key (put by Hadi in the environment variable
`TONIC_TEXTUAL_API_KEY`); the VM resize and any VM restart; enabling SSH on the VM (or running the Shield script
in Remote Desktop); the go for the 3.3 GB streamed download of the fresh Judilibre draw; any publication.

## 5. Data

Only public benchmark data and invented documents. All sets are built by `prepare_sets.py` (and
`make_reference_doc.py`) into `<work>/sets/<set>/` (git-ignored): `input/` (the files every tool
receives), `gold.jsonl`, `order.txt` and `tasks.json` (the folders a lawyer drops, in run order). The lists and
seeds are copied in `subsets/`. The SHA-256 of every input file and gold file is in `PREREG.sha256`.

| Set | Files (format) | Characters | Words | Gold items scored (+ in document properties) | Must-stay-clear items | Other keep items | Tasks | Status for Shield | Licence |
|---|---:|---:|---:|---:|---:|---|---:|---|---|
| REF: reference document (section 5.1) | 5 (.docx) | 146,917 | 23,445 | 1,015 (+20) | 365 | date 245, amount 155 | 5 (one per file) | invented by the Shield team; never read by Shield before the freeze; not independent | ours, CC BY 4.0 |
| FR-PII-Bench v0 | 300 (.txt) | 109,433 | 17,245 | 2,105 | 0 | none | 1 | informed (fed the v0.2 design) | CC BY 4.0 |
| MAPA, Cour de cassation | 19 (.txt) | 465,252 | 75,753 | 1,615 | 1,344 | date 814, amount 297, role 17, time 2 | 1 | informed | CC BY 4.0 |
| Judilibre fresh draw (section 5.3) | 200 (.txt) | about 2.3 M (estimate from the old draw) | about 380,000 | indicative only: names of lawyers, judges and clerks found by fixed patterns | about 6,000 (estimate) | placeholders (reported apart) | 1 | **held-out for every tool** | Licence Ouverte 2.0 |
| Max-protocol matters A to G | 33 (.docx 10, .pdf 20, .xlsx 1, .txt 2) | 173,365 | 28,860 | 1,004 (+94) | 150 | date 178, amount 149, role 175, obligation 34 | 7 (one per matter) | informed (G was the R1 holdout only) | ours, CC BY 4.0 |
| English: PrivacyBench v2.5 e-mail bodies | 241 (.txt) | 133,186 | 22,113 | 1,276 | 0 | none | 2 (one per export) | informed (PrivacyBench was the v0.3 dev set) | CC BY 4.0 |
| PILOT (format pilot, never scored) | 2 (.docx, .txt) | 29,310 | | not scored | | | 2 | invented | ours |

### 5.1 The reference document (REF)

`make_reference_doc.py` writes an invented French employment-litigation file ("conclusions récapitulatives"
before the conseil de prud'hommes de Lyon) built like Hexagone's speed reference: 10 pages (a page break after each
of 10 sections; Times New Roman 11 pt), about 29,400 characters as read by our reader, about 20.7 personal data
items per page (207 per file: 203 in header, body, table and footer, 4 in document properties), with a header, a
footer, a 25-row table ("bordereau de pièces") and document properties (title, author, last modified by), as in a
real firm file. Every person, company, address and number is invented (common first names; surnames, company
names and towns from a seeded syllable generator; identifiers with valid check digits: NIR key, SIREN and SIRET
Luhn, French IBAN and RIB key). Courts, codes, articles and laws are real; the precedent numbers are invented and
the footer says "Document fictif, données inventées". Five files (seeds 101 to 105) have the same template and
different values: five distinct files of the same size give five timings without a cache hit. Bytes are
deterministic (regenerating gives the same SHA-256). The gold is the generator's own record of each value, located
in the reader's text; every offset is checked.

Gold labels: PERSON 580, ORG 175, ADDRESS 70, ID_CODE 50, EMAIL 45, PHONE 25, CASE_REF 20, BIRTHDATE 15, IBAN 10,
SIREN 10, SIRET 10, NIR 5 (all five files). Keep classes: article 145, code 125, court 30, court_city 20,
legal_term 20, legal_ref 15, law 10, date 245, amount 155 (all five files).

The rendered page count in Word is not checked on the Mac (no Word); the operator records it when the file is
first opened on the VM (expected 10 to 12 pages).

### 5.2 FR-PII-Bench, MAPA, Max, English

- FR-PII-Bench v0: all 300 documents (`JaqueBill/fr-pii-bench` revision `5476b0a`), one .txt each; gold = the
  benchmark's entities. Comparable with the card's per-document numbers only as indicative (folder condition,
  section 9.1).
- MAPA: the 19 Cour de cassation decisions (`FrancophonIA/MAPA_Anonymization_package` revision `8b147fa`); gold =
  PERSON, ORGANISATION and ADDRESS entities with the identifying tokens of the MAPA scorer
  (`evaluation/public/mapa-fr-cassation/score.py`, unchanged since 2026-10-17; 37 entities with no identifying
  token excluded; court-city addresses moved to keep); keep = court cities, the DATE, AMOUNT, ROLE, PROFESSION and
  TIME entities, and the legal patterns of the Judilibre scorer (court names, court cities, articles, codes, laws).
- Max: the 33 files of matters A to G in the common formats (`subsets/max.order.txt`); excluded (16, listed in
  `subsets/max.excluded.json`): 8 e-mails, 3 HTML pages, 1 Markdown note, 2 scanned PDFs, 1 encrypted PDF, and the
  restored handoff the Max harness writes. Gold = every occurrence of every surface form of every protect item of
  `gold.json`, located longest form first (case, accents, apostrophes and white space folded, whole words); keep =
  the preserve items of type legal_ref, court (must stay clear), date, amount, role and obligation.
- English: 2 of the 21 PrivacyBench exports drawn with `random.Random(20261023)` (`malik_spotify`,
  `yusuf_procter_gamble`), every e-mail record (at most 150 per export): 121 + 120 bodies, one .txt each, gold =
  the v2.5 spans.

### 5.3 Judilibre fresh draw (held-out)

The old 200 decisions are in-sample for Shield. The head-to-head uses 200 new ones, drawn by
`draw_judilibre_fresh.py`: same source and revision (`antoinejeannot/jurisprudence` @ `8019db1`), same three
strata and quotas (67 Cour de cassation, 67 cours d'appel, 66 tribunaux judiciaires), every line of the old pools
excluded, a new pool of 150 lines per stratum from `random.Random(20261023)` (frozen now, without any download, in
`subsets/judilibre_fresh_pool.json`), and the first k eligible decisions in pool order. Precis subset: the first
17, 17 and 16 kept decisions per stratum (50). The download (about 3.3 GB streamed, nothing large written) waits
for Hadi's go. The sample and the built set go into `PREREG_DATA.sha256` before any tool reads a decision.
Measures: P2 on the fixed legal patterns (court names, court cities, articles, codes, laws); P1 is indicative only
(lawyers, judges and clerks named in clear by Judilibre, found by the scorer's patterns); placeholders are reported
apart.

### 5.4 Not used, and why

| Set | Why not |
|---|---|
| Old Judilibre 200 | in-sample for Shield (used only to validate the scorer, section 8.3) |
| AI4Privacy 300k | commercial use needs a written licence |
| PII-INDEXBENCH | no public copy found |
| Hexagone's French medical set | built by Hexagone; two thirds scans (Shield has no OCR); terms risk |
| RAT-Bench | no French; scores quasi-identifiers that Shield keeps on purpose |
| holdout-en | written by the Shield team from Shield's miss classes |
| REDACT FR | small; may be added later as a separate, pre-registered addendum |
| Full PrivacyBench | 12 M characters, formats Hexagone does not document (.eml, Slack .json, .csv); both vendors already publish numbers |

### 5.5 Time budget inside the 7-day Hexagone trial (from Hexagone's own speed table)

Assumption: time scales with characters (Fast: 1.0 to 2.0 s per 1,000 characters on the 2023+ row, 2.7 to 3.5 on
the 2019 row; Precis: 6 to 12 and 12 to 20). Per-file overhead is unknown and comes on top.

| Set | Characters | Fast, profile A | Precis, profile A |
|---|---:|---|---|
| REF (5 files) | 146,917 | 2.4 to 4.9 min | 15 to 29 min |
| FR-PII-Bench (300 files) | 109,433 | 1.8 to 3.6 min (+ overhead of 300 files) | 11 to 22 min |
| MAPA (19) | 465,252 | 7.8 to 15.5 min | 47 to 93 min |
| Max (33) | 173,365 | 2.9 to 5.8 min | 17 to 35 min |
| Judilibre fresh (200; Precis: 50) | about 2,300,000 (Precis about 575,000) | 38 to 77 min | 58 to 115 min |
| English (241) | 133,186 | 2.2 to 4.4 min | 13 to 27 min |
| **Total** | about 3.3 M (Precis about 1.6 M) | **about 1 to 2 hours** | **about 2.7 to 5.4 hours** |
| Profile B, REF only (speed) | 146,917 | 6.6 to 8.6 min | 29 to 49 min |

Everything fits in two working days; the 7 days leave room for the speed sessions, profile B and failures.

## 6. Settings fixed in advance

| System | Fixed settings |
|---|---|
| Shield | Product defaults: codes replacement, language auto, legal form left in clear, French codes; one Shield data folder per run; file key (`RAGBASE_SHIELD_KEYRING=0`); no dossier title; S-R `RAGBASE_SHIELD_NER=off`; S-N model fastino on CPU, default threads. No register, no keep-clear, no setting change. |
| Hexagone | Every setting as installed (categories, replacement style, custom types: untouched). No edit in the review pane: the operator accepts the detections as shown. Mode Fast for H-F; Precis for H-P only if offered. Output location: the task's output folder when the app lets the user choose it; else the app's default (next to the source), then copied unchanged. |
| Tonic | Default server, default entity types, default handling (redaction token), language detected by Tonic (French files are French), no custom entity, no allow or block list, no Graph Synthesis. |
| Presidio | Default recognizers, default threshold, default entities, default anonymizer (`<ENTITY_TYPE>`); spaCy `fr_core_news_md` for French sets, `en_core_web_lg` for English. No presidio-fr add-on. |

## 7. Text extraction (fixed readers)

`extract_text.py` (reader `laptop-extract-1.0`) reads the input file AND every tool's output file the same way.
Libraries pinned: pdfplumber 0.11.10 (pdfminer.six 20260107), openpyxl 3.1.2; .docx with the standard library.

| Format | How the text is read |
|---|---|
| .txt | UTF-8 (BOM dropped), cp1252 if UTF-8 fails; line ends normalised to "\n" |
| .docx | Document properties (title, subject, creator, keywords, description, lastModifiedBy, category; Company, Manager; custom properties), headers, body, footnotes, endnotes, footers, comments, then every revision or comment author, then external link targets (for example `mailto:`). Each paragraph is a line; table cells are paragraphs; tracked deletions are read (they stay in the file). |
| .pdf | Metadata (Title, Author, Subject, Keywords, Creator), each page's `extract_text()` with default settings (pages joined by a blank line), then annotation contents |
| .xlsx | Core properties, then per sheet "== name" and one line per row (non-empty cells joined by " \| "), then cell comments |

Shield's output is text (what the assistant receives); Presidio writes text; Hexagone writes files in the input
format; Tonic writes text for .txt and files for the other formats. The scorer finds the output by file stem (any
of the four formats). Gold items inside the reader's document-property lines are part "metadata", reported apart
(an assistant may or may not read file properties).

## 8. Scorer

### 8.1 Rules (`score_text.py`, `laptop-score-1.0`)

1. Tokens: runs of letters, digits and "_" and single other non-space characters; white space ignored.
2. Alignment: line by line, then token by token inside differing blocks (patience diff, then
   `difflib.SequenceMatcher` in the gaps). An input token is KEPT when aligned with an identical output token;
   otherwise CHANGED (replaced or deleted).
3. Gold item: identifying tokens = its letter-or-digit tokens minus words that do not identify alone (titles;
   function words; legal forms for organisations; street words for addresses; fr, com, www... for e-mails and
   URLs), unless none would remain; for MAPA, exactly the identifying tokens of the MAPA scorer. PROTECTED = all
   changed; PARTIAL = some kept; MISSED = all kept. EXPOSED = partial + missed.
4. Readable anywhere: the identifying string (folded) is searched as whole words in the whole folded output
   (document properties included); long digit strings also without spaces; values under 4 letters or digits are
   not searched.
5. 80 % coverage (FR-PII-Bench's own rule): share of the gold span's characters inside changed regions.
6. Keep item: ALTERED when any of its letter-or-digit tokens changed.
7. Changed region: consecutive changed tokens on one line. False-mask region: touches no gold item. Words changed
   outside gold and retention exclude the reader's document-property lines.
8. Failure: run log "failed", no output, unreadable output, or retention under 0.50 (documents with at least 20
   words outside gold): every gold item counts as exposed (missed); keep items are not counted as altered.

The scorer writes only gold and input strings in its reports, never output text.

### 8.2 Self-tests and sanity checks (all pass, 2026-10-23)

- `score_text.py --selftest`: codes, tags (`[a.PERSON_1]`, `<DATE_TIME>`, `[REDACTED]`), realistic fake values,
  deletion; partial and missed; court city and article number altered; a fake equal to another real value
  (protected at its place, readable anywhere); unchanged output; white-space-only changes; the failure rule.
- Identity output (nothing masked) and oracle output (every gold value replaced) on REF, FR-PII-Bench, MAPA, Max,
  English and the old Judilibre 200: identity = every scored gold item exposed, 0 keep altered; oracle = 0 exposed,
  0 keep altered, 0 false-mask regions.
- A simulated tool that rewrites REF-1.docx inside its XML (as a desktop app would): 203 of 203 protected, the 4
  document-property items exposed (they were not rewritten), 0 must-stay-clear altered.

### 8.3 Validation against the existing scorers on Shield v0.3 codes output

Shield v0.3 (commit `89e0b6c`, rules mode) was re-run from a `git archive` of that commit with the engine call of
the v0.3 runners: its spans are byte-identical to the recorded v0.3 runs (FR-PII-Bench 300 of 300 documents,
Judilibre 200 of 200). MAPA uses the recorded `masked_text` of the v0.3 product-path run (Shield's own reader).
Tolerance fixed with the check: protection and keep counts equal; region counts within 0.5 %; every difference
explained.

| Set | Existing scorer (v0.3 rules) | score_text.py | Difference |
|---|---|---|---|
| FR-PII-Bench | recall_any 1,885 of 2,105 | covered 80 %: 1,885 | 0 |
| FR-PII-Bench | precision 2,061 of 2,136 predicted spans | regions with 50 % or more on gold: 2,061 of 2,136 regions | 0 |
| FR-PII-Bench | false masks 75 | false-mask regions 75 | 0 |
| MAPA | protected 1,299 of 1,615 (PERSON 757, ORG 506, ADDRESS 36); partial 72; missed 244 | the same | 0 |
| MAPA | dates masked 0 of 814; amounts 0 of 297; court cities 0 of 99 | keep altered 0 (date 814, amount 297, court_city 108 = 99 + 9 found by pattern) | 0 |
| MAPA | masked spans 1,516; spans outside the 3 scored labels 142 | changed regions 1,516; false-mask regions 142 | 0 |
| Judilibre (old 200) | legal content found by pattern 6,081 (courts 1,312, court cities 866, articles 2,065, codes 1,651, laws 187), overlapping a mask 0 | keep 6,081, altered 0 (each class identical) | 0 |
| Judilibre (old 200) | placeholders overlapping a mask 263 (2 + 261) | 263 | 0 |
| Judilibre (old 200) | professional names fully masked 665 of 672 | protected 666; covered 80 % 665 | +1: "Maître" inside one pattern match is a title, not identifying |
| Judilibre (old 200) | masks 6,039 | changed regions 6,046 | +7 (0.1 %): a mask that spans a line break counts as two regions |

New reading on FR-PII-Bench (identifying-token rule): 46 of 2,105 exposed (2,059 protected). It differs from
recall_any because a company whose legal form stays in clear ("SOCIETE_A SAS") is protected under the
identifying-token rule and not covered at 80 %. Both readings are reported for every tool.

Files: `<work>/validate/` (`run_v03_text.py`, `pairs_v03_*.jsonl`, `score_v03_*.json` and `.md`,
`oracle_check.py`).

## 9. Run procedure per tool

### 9.1 Shield (rows S-R, S-N, S-N2)

1. Build the wheel from `git archive 577b423` (not the working tree); install it in a fresh venv on the VM with
   the `ner` extra and the pinned fastino model; record the wheel SHA-256 in `PREREG_DATA.sha256`.
2. Per set, in the order of section 10.2: `run_shield_files.py --set-dir <set> --out <runs>/shield_rules/<set>
   --mode rules`, then the same with `--mode ner`. Folder condition: each task of `tasks.json` is one dossier
   (`add_dossier` with no title), then every document is read page by page (`read_document`): the joined pages are
   the output. Outbound network connections are refused in the process and logged.
3. Speed rows (section 10.3): REF tasks; three separate processes for cold start; S-N2 with the AVX2 variables.

### 9.2 Tonic Textual cloud (row T)

Preconditions: Hadi's account, key and go (section 4.3). From the VM (profile A), `run_tonic.py` per set in this
order, while the trial word budget allows (a set is run only if its words fit in what is left minus 5,000; no
partial set): REF (23,445 words), FR-PII-Bench (17,245), Max (28,860), English (22,113): 91,663 words of the
100,000. MAPA and Judilibre are not sent (budget; they are real court texts). The recorded time includes the
network. Results are sealed and internal (section 13).

### 9.3 Presidio (row P)

`run_presidio.py` per set on profile A (French sets with `--language fr`, English with `en`), then the REF speed
rows on A and B. It reads the input through `extract_text.py` (a text library has no file rebuild).

### 9.4 Hexagone (rows H-F, H-P): run by a person, step by step

Operator: Hadi or a person he names, in Remote Desktop on the VM [public extract: account name left out]. Every step goes into
`RUNSHEET_HEXAGONE.csv` and, for times, `windows/mark_time.ps1`. Input folders: `C:\bench\in\<set>\<task>\`
(copies of `input/`, same names, same order); outputs: `C:\bench\out\hexagone\<mode>\<set>\<task>\`; CSV audit
exports: `C:\bench\sealed\hexagone\<mode>\<set>\`.

| Step | Action |
|---|---|
| H0 | Hadi signs up (hexagone.ai/fr/get-started), downloads and installs the Windows app, completes onboarding. Record the date and time of first launch (the 7 days start then). |
| H1 | First launch: record the app version, the model download, whether the calibration left Precis available (screenshot of the mode setting), and the default replacement style. Change nothing. |
| H2 | Format pilot (never scored): process `PILOT.docx` and `PILOT.txt` in Fast mode, one at a time. Check: an output exists, where it is, its name (rename rule written in the run sheet), our reader reads it, accents in the .txt output are intact. Contingencies, decided only from the pilot: (a) broken accents in .txt: every .txt input of every set is re-saved as UTF-8 with BOM for EVERY tool (same text, gold unchanged); (b) .txt refused: `txt_to_docx.py` converts every .txt set for EVERY tool, and the new hashes go into `PREREG_DATA.sha256` before any scored run. Nothing else may change. Then restart the app. |
| H3 | Fast mode, sets in the order of section 10.2, each task in `tasks.json` order: run `mark_time.ps1 -Label "<mode> <set> <task> start"`, select the task folder in the app's documented folder flow, let it run, do not touch the review pane, run `mark_time ... end` when the app shows the task as done, export the CSV audit log to the sealed folder, write files in, files out and any error shown. Start `sample_memory.ps1` (process name read once from Task Manager) for REF tasks. |
| H4 | Precis mode, only if offered: switch the mode in the app's settings, restart the app, then H3 again (Judilibre: the Precis subset of 50 only). |
| H5 | Speed session, next day (section 10.3). |
| H6 | Profile B, last: after Hadi's resize, record whether the app still runs and whether Precis is offered; then the REF speed rows. If the licence does not survive, stop and record it. |
| H7 | `collect_outputs.py` maps the outputs to the inputs with the rename rule of H2 only (no content read); the result goes to the sealed folder. |

Forbidden at every step: click scripts or macro tools, any Hexagone API, traffic capture, reading app files,
models or logs beyond the documented exports, editing detections, changing settings (except the mode switch of
H4), restarting the trial on a new device or a cloned VM.

## 10. Order, schedule, speed and memory

### 10.1 Calendar (Hexagone trial days; Shield, Presidio and Tonic runs fit around it on the same VM)

| Day | Work |
|---|---|
| 0 | H0, H1, H2 (pilot). Shield and Presidio pilots on the same PILOT files (unscored). `machine_facts.ps1`. |
| 1 | Hexagone Fast on all sets (H3). Shield S-R and S-N, Presidio, on all sets (any order relative to Hexagone, never at the same time on the VM). |
| 2 | Hexagone Precis (H4), if offered. Tonic runs (if Hadi gave the go). |
| 3 | Speed session on profile A (section 10.3) for every local tool. |
| 4 | Resize to profile B (Hadi). Speed session on B for every local tool. |
| 5 to 7 | Buffer for documented operator or machine errors only (section 12.2). |

### 10.2 Set order (fixed)

REF, FR-PII-Bench, MAPA, Max (A to G), Judilibre fresh, English. Inside a set: `tasks.json` order; inside a task:
`order.txt`.

### 10.3 Speed

- Unit: one REF file = one task (drop to the last output file). Hexagone: from the "start" mark to the last output
  file time (and to the "end" mark; both reported). Shield, Presidio: `task_seconds` of their logs.
- Per tool, mode and profile: the five REF files in one session (5 values), in a fresh app or process session on
  day 3 (or day 4 for B), plus the 5 values of day 1 for profile A: median and range of all values. Distinct files,
  so Hexagone's per-session cache (a re-processed file returns in about 1 s) never applies; the app is restarted
  before each session and each mode.
- Cold start: three app or process starts per tool, mode and profile (Hexagone: launch to ready, by the marks;
  Shield: process start to the end of a warm-up mask, which includes the model load for S-N).
- Characters per second = 29,383 (mean REF characters) / median task time; plus the full-set task times of the
  accuracy runs (informative: they include per-file overhead).
- Rule: nothing else runs on the VM during a timed task; the VM is not used by any other workflow (file
  `evaluation/laptop/VM_BUSY` exists during sessions).

### 10.4 Memory

Peak resident memory: Shield and Presidio from their own process (Windows `PeakWorkingSetSize`); Hexagone from
`sample_memory.ps1` (sum of the working sets of its processes, once per second, from the Windows process list:
OS-level observation only). Reported per tool, mode and profile, with free RAM at session start. On profile B
(8 GB) we report whether a tool ran out of memory or swapped (task failed, or times far above A).

### 10.5 Where the data goes (P4)

| System | Where the text is processed | What leaves the machine | How we know |
|---|---|---|---|
| Shield | on the VM | nothing (outbound connections refused and logged by the runner) | our own process check, every run |
| Hexagone Desktop | on the VM after a 1 GB model download (documented) | documented: the trial's daily machine-fingerprint check with Hexagone's backend | Hexagone documentation only; we do not watch its traffic (terms) |
| Tonic Textual | Tonic's cloud (textual.tonic.ai) | every file sent | by design; DPA lists AWS and Microsoft hosting |
| Presidio | on the VM | nothing (same process guard) | our own process check |

## 11. Analysis and decision rules

### 11.1 What is reported

For each set and each row (S-R, S-N, H-F, H-P, T, P): P1 exposed n of N with its rate and 95 % Wilson interval,
readable anywhere, covered 80 %, per label; document properties apart; P2 must-stay-clear altered n of N per class
and documents with one; dates, amounts, roles, placeholders altered; false-mask regions; words changed outside
gold; failures with reasons. Speed and memory per profile (section 10). P4 table. Each number carries the set's
status for Shield (section 5) and its machine label. No single pooled score is the headline; a pooled French table
(REF, FR-PII-Bench, MAPA, Max) is secondary.

### 11.2 Paired comparisons

`compare_runs.py A.json B.json` for each set: Shield S-R and S-N against each other row. Unit = document; paired
bootstrap of the difference of pooled rates (2,000 resamples, `random.Random(20261023)`).

### 11.3 Claims allowed

- "Shield exposes less than X on set S" only if the whole 95 % bootstrap interval of (X minus Shield) is above 0;
  the same rule for P2 and for the reverse claim.
- Speed: "faster" only if every Shield value of the speed session is below every value of the other tool on the
  same profile (no overlap of ranges).
- A claim always names the set, its status (informed, invented, held-out), the machine label and the mode.
- "Shield beats Hexagone" needs: a P2 claim on the held-out Judilibre draw, P1 and P2 claims on REF, and no
  opposite claim (P1 or P2) on any other set. "Shield beats Tonic" needs P1 and P2 claims on REF and no opposite
  claim on any other set Tonic ran. Anything less is reported as it is.

## 12. Fairness rules, failures and deviations

### 12.1 Fairness

Same files, same order, same tasks, same readers, same scorer for every tool; settings fixed in section 6; every
run logged (app or package version, mode, profile, start and end time, files in and out, errors); a document a
tool fails on counts as fully exposed; the gold never tunes anything; no Shield change during the trial.

### 12.2 Re-runs

A task may be run again only for a reason written in `DEVIATIONS.md` BEFORE any score of that task is computed:
an operator error (wrong folder, wrong mode, a setting changed by mistake) or a machine failure (VM crash, disk
full). A tool error on a document is never a reason: the document counts as failed. The first complete run
after a re-run is the one scored, and both are listed.

### 12.3 Deviations

`DEVIATIONS.md` (created at the first deviation): time, what changed, why, which results had been seen. Any change
to a frozen file is a deviation and its new hash is added with the reason; the old hash stays.

## 13. Sealing: who may read what

- Hexagone and Tonic outputs, their CSV audit exports and their per-document score files go to
  `<work>/sealed/` (git-ignored). The scorer reads them; nobody who works on Shield's `src/` or
  `tests/` (people or Claude sessions) opens them.
- Only aggregate tables (per set, label and class) leave the sealed folder. They contain counts, never output
  text. No Shield rule, lexicon, test or comment may cite or be derived from a competitor output or a competitor's
  per-item result (Hexagone terms §10 (vi), §13; Tonic terms §2(a)).
- Shield's own outputs are not sealed. The clean-room audit (`evaluation/audit/`) may scan `src/` for any string
  that only occurs in a sealed competitor output.
- Tonic results are internal unless Tonic agrees in writing or counsel clears publication (section 4.3).

## 14. Limits

1. **Not held-out for Shield**, except the fresh Judilibre draw: REF was written by the Shield team (never read by
   Shield before the freeze); FR-PII-Bench, MAPA, Max and English informed Shield's design. Hexagone and Tonic did
   not see any of our French sets (as far as we know).
2. **A VM is not a laptop** (section 4.2). Real laptop runs (P1 and P2 machines) are the next step for published
   absolute times.
3. **Folder condition**: each set is one folder (Max: one per matter; English: one per export). Tools that keep one
   pseudonym per person across a folder (Shield's dossier, Hexagone's folder flow) may gain or lose recall from
   cross-document effects; Tonic and Presidio process documents one by one. Per-document numbers of the published
   benchmarks are not directly comparable.
4. **Judilibre P1 is indicative**: parties are already pseudonymised; the gold names are those found by fixed
   patterns (lawyers, judges, clerks).
5. **Gold by our rules**: Max surface forms located by string search (a form inside a longer word is not counted;
   a short form in an unrelated place is); REF gold from our generator; the MAPA identifying-token rule is ours.
6. **Document properties** are reported apart; an assistant may or may not read them.
7. **Hexagone** may update its models during the trial (we record the version each day); Precis may be unavailable
   on the VM; its timing is by person-made marks (about 1 s precision) plus file times.
8. **Tonic** is measured through the network from Belgium (europe-west1) to Tonic's cloud; its time is not laptop
   compute. Graph Synthesis (the 96.4 % system) is not the default SDK path; we measure the default.
9. **One run per tool and mode** for accuracy; speed has 5 to 10 values per row.

## 15. Files

| File | Role |
|---|---|
| `PROTOCOL.md` | this protocol |
| `PREREG.sha256` | SHA-256 of every frozen file (protocol, tools, lists, built data, scorer validation); check with `python evaluation/laptop/freeze.py check` (or `shasum -a 256 -c evaluation/laptop/PREREG.sha256`) from the repository root |
| `freeze.py` | writes and checks `PREREG.sha256` and, later, `PREREG_DATA.sha256` (it refuses to rewrite either) |
| `extract_text.py` | fixed readers (section 7) |
| `score_text.py` | tool-agnostic scorer (section 8) |
| `compare_runs.py` | paired comparison and claim rule (section 11) |
| `make_reference_doc.py` | REF and PILOT generator (section 5.1) |
| `prepare_sets.py` | builds FR-PII-Bench, MAPA, Max, English and Judilibre sets (section 5) |
| `draw_judilibre_fresh.py` | fresh Judilibre draw (section 5.3) |
| `txt_to_docx.py` | contingency of the format pilot (section 9.4, H2) |
| `run_shield_files.py`, `run_presidio.py`, `run_tonic.py` | runners (section 9) |
| `collect_outputs.py` | maps Hexagone outputs to inputs by the pilot's rename rule (section 9.4, H7) |
| `RUNSHEET_HEXAGONE.csv` | run sheet for the Hexagone operator |
| `windows/mark_time.ps1`, `windows/sample_memory.ps1`, `windows/machine_facts.ps1` | time marks, memory sampler, machine facts |
| `subsets/SEEDS.json`, `subsets/judilibre_fresh_pool.json`, `subsets/<set>.order.txt`, `.tasks.json`, `.stats.json`, `subsets/max.excluded.json` | seeds, pool, lists, tasks |
| `<work>/sets/<set>/` (git-ignored) | built inputs and gold (hashes in PREREG.sha256) |
| `<work>/validate/` (git-ignored) | scorer validation (section 8.3) |
| `<work>/research_*.md` (git-ignored) | the research behind sections 3 and 4 |

## 16. Sources (all read 2026-10-23 unless stated)

| Source | Used for |
|---|---|
| https://www.hexagone.ai/fr/system-requirements | requirements, Fast and Precis, Precis disabled on slow machines, speed table and its reference file, cache, model load |
| https://www.hexagone.ai/fr/research, https://www.hexagone.ai/fr/research/privacy-bench | Hexagone's published numbers and how they were run |
| https://www.hexagone.ai/fr/terms (desktop tab, May 2026) | §4.2 trial, §10 (vi), §13 |
| https://www.hexagone.ai/fr/faqs | formats (PDF, DOCX, XLSX, PPTX, TXT), folder flow, CSV audit export |
| https://huggingface.co/datasets/TonicAI/Privacy-Bench (revision `a79d9e80`, 2026-10-15; tag `v2`, 2026-09-22) | Tonic 96.4 % (v2.5) and 93.9 % (v2) |
| https://www.tonic.ai/glossary/named-entity-recognition | the stale 95.0 % (v1) |
| https://docs.tonic.ai/textual/textual-install-administer/deploying-a-self-hosted-instance/system-requirements | GPU need, CPU "significantly slower" |
| https://docs.tonic.ai/textual/textual-billing-overview | 100,000-word trial |
| https://www.tonic.ai/terms-and-conditions (updated 2026-02-05) | §2(a), §6 |
| https://gs.statcounter.com/os-market-share/desktop/france (September 2026) | Windows 77.3 % of French desktop traffic |
| Septeo Avocats prerequisites PDF (2025), https://page.septeo.com/hubfs/Septeo-Avocats/Dossier%20Fabien%20Delmas/2025%20-%20Prerequis%20-%20Septeo%20Avocats%20-HEBERGE.pdf | 16 GB and Core i3 10th gen minimum for French practice software |
| https://www.notebookcheck.net/Intel-Core-i5-1235U-Processor-Benchmarks-and-Specs.589637.0.html | power-limit effect on laptop speed |
| https://docs.cloud.google.com/compute/docs/cpu-platforms | Cascade Lake, AVX-512 |
| `<work>/research_hexagone.md`, `research_tonic.md`, `research_lawyer-hardware.md`, `research_benchmarks.md` | full research notes with every source |
| `evaluation/SCOREBOARD.md` (v0.3, rechecked 2026-10-23) | Shield numbers and the outside numbers we quote |
