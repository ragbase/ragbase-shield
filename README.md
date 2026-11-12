# RAGbase Shield

<!-- mcp-name: io.github.ragbase/ragbase-shield -->

**Use Claude, ChatGPT and Copilot on your case files, masking your clients' names before sending.**

RAGbase Shield 0.4.0 is a free, open-source tool (Apache-2.0).
On your own computer, it replaces client names and numbers with codes before the text goes to the AI.
When the AI answers, Shield puts the real names back, also on your computer.

This is **local, reversible pseudonymisation**.
It is not anonymisation: facts, dates and amounts stay readable by the AI.
Nothing goes to RAGbase. Shield sends no usage statistics.

Version française (la version de référence pour les cabinets français) : [README.fr.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/README.fr.md)

Contents:

- [For lawyers: the essentials](#for-lawyers-the-essentials)
- [Install](#install)
- [Daily use](#daily-use)
- [Results: public head-to-head of 11 November 2026](#results-public-head-to-head-of-11-november-2026)
- [Limits (please read)](#limits-please-read)
- [Privacy model in 5 lines](#privacy-model-in-5-lines)
- [For developers and IT](#for-developers-and-it)
- [Links](#links)
- [Going further](#going-further)

---

## For lawyers: the essentials

### What Shield does

You write or open this text (invented example):

```text
M. Thibault Mercadier, domicilié 12 rue des Glycines, 69007 Lyon, conteste son
licenciement par la société Ateliers Brunelac SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° 25/01234).
Contact : t.mercadier@example.org
```

The AI receives this text:

```text
M. PERSONNE_A, domicilié ADRESSE_1, conteste son
licenciement par la société SOCIETE_A SAS, notifié le 3 mars 2025.
Il réclame 48 000 € devant le conseil de prud'hommes de Lyon (RG n° RG_1).
Contact : EMAIL_1
```

This is the real output of the 0.4.0 engine (rules mode, the default) on this example. A test checks it.
Note what stays readable: the date, the amount, the court. The AI needs them to do the work.
The detection rules are built for French legal documents first, with English support.
With `RAGBASE_SHIELD_LOCALE=en`, codes use English labels (PERSON_A, COMPANY_A, ADDRESS_1).

Inside one dossier, a person always keeps the same code.
"M. Mercadier", "Thibault Mercadier" and "MERCADIER Thibault" all become PERSONNE_A.

### Three rules to remember

1. **Connect a folder. Do not attach the file to the chat.**
   A file attached to a chat reaches the AI provider before Shield can act.
   Add the case folder to Shield. The AI then reads the documents through Shield, masked.
2. **Do not paste raw text into the chat box.**
   Go through Shield first (the "Masquer" page in Shield Desk, or the browser extension).
   To talk about a person in the chat, write their code (PERSONNE_A), not their name.
3. **Text already sent cannot be recalled.**
   Shield protects only what goes through it. If a name was sent by mistake, Shield cannot undo it.

### What reaches the AI provider, what stays with you

| Reaches the AI provider (Anthropic, OpenAI, Microsoft) | Stays on your computer |
|---|---|
| Masked text with codes (PERSONNE_A, SOCIETE_A, IBAN_1) | Real names and real numbers |
| Facts, dates (except dates of birth), amounts, legal reasoning | The code-to-name table (the "vault"), encrypted |
| Courts, laws and articles cited | The vault encryption key |
| The dossier code (DOSSIER_1) and masked file names | The real dossier name and folder path |
| Your question | The local journal (events, codes and counts only) |

Details: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/PRIVACY_MODEL.md).

### Codes

| What is masked | Code (French labels, default) |
|---|---|
| Person | PERSONNE_A, PERSONNE_B, ... |
| Company | SOCIETE_A, ... |
| Postal address | ADRESSE_1, ... |
| Email, phone | EMAIL_1, TEL_1 |
| IBAN, payment card | IBAN_1, CARTE_1 |
| French social security number (NIR) | NIR_1 |
| SIREN, SIRET, EU VAT number | SIREN_1, SIRET_1, TVA_1 |
| Case references (RG, pourvoi, Portalis, ECLI) | RG_1 |
| Other identifiers (ISIN, LEI, passport, licence plate, IP address) | IDENT_1 |
| Websites and URLs (except well-known public sites) | SITE_1 |
| Date of birth | NAISSANCE_1 |

Shield does not mask courts, institutions (Cour de cassation, CNIL, URSSAF...), laws, codes,
articles, months and days.

---

## Install

Downloads (installers, Claude Desktop extension, `SHA256SUMS`): the releases page,
https://github.com/ragbase/ragbase-shield/releases/latest. Python package: `ragbase-shield` on PyPI.

| Your app or system | What to install | Guide |
|---|---|---|
| Mac (macOS 13 or later) | `RAGbase-Shield-0.4.0.pkg`: double-click, installs for you only (designed to need no administrator password), no Terminal. Not signed yet: macOS asks you to confirm the first time | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), section 0 |
| Windows 10 or 11 | `RAGbase-Shield-0.4.0-win64.msi`: per-user install (designed to need no administrator rights). Not signed yet: SmartScreen asks you to confirm | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), section 0 |
| Claude Desktop | `ragbase-shield-0.4.0.mcpb`: double-click, then "Install" | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), section 2 |
| Claude Code and Cowork | Plugin: `/plugin marketplace add ragbase/ragbase-shield`, then `/plugin install ragbase-shield@ragbase` | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), section 3 |
| ChatGPT desktop and Codex, GitHub Copilot in VS Code | `uvx ragbase-shield install chatgpt` (or `codex`, `vscode`) | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), sections 4 and 5 |
| Any web app (claude.ai, chatgpt.com, Copilot web) | Shield Desk, and the browser extension for Chrome and Edge (not in the stores yet: load the folder `integrations/browser-extension` in developer mode) | [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md), sections 6 and 7 |
| Terminal, with uv or pip | `uvx ragbase-shield desk`, or `pip install ragbase-shield` | below |

**With uv (one command).** uv is the open-source tool that downloads and runs Shield.

On a Mac: open the Terminal app, paste this line, press Enter.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows: open PowerShell, paste this line, press Enter.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close the window and open a new one. Then start Shield Desk:

```sh
uvx ragbase-shield desk
```

Your browser opens **http://127.0.0.1:7878** with a private link that holds a secret token.
This is a local page: it works only on your computer.
To open it again, run the command again or use the link shown in the Terminal.
The address alone, without the token, shows "Token refused".
Keep the Terminal window open: closing it stops Shield Desk and the browser extension.

**With pip:** `pip install ragbase-shield`, then `ragbase-shield desk`. The optional name recognition model:
`pip install "ragbase-shield[ner]"` (see [docs/NER.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/NER.md)).

On a Mac, the first use may ask for keychain access for the Shield key: click "Always Allow".

---

## Daily use

### With Claude Desktop, Claude Code, ChatGPT desktop or Copilot in VS Code

1. In Shield Desk, on the **Dossiers** page, under "Ajouter un dossier" (Add a folder), type the full path of
   the client's case folder, then click "Ajouter et analyser" (Add and scan).
   Shield gives it a code (DOSSIER_1) and reads the documents. The Desk has an EN toggle for English labels
   (tabs: Matters, Mask, Restore, Files, Log).
   To copy a folder path: on a Mac, in the Finder, hold Option and right-click the folder, then
   "Copy ... as Pathname"; on Windows, Shift + right-click, then "Copy as path".
2. Click "Voir les entités" (Show entities) to see the detected names. Add the missing ones with "Add a name or
   a term", above the list: the client, the parties, a project name. Turn on the "Keep in clear" switch for a
   name that must stay readable.
3. In the AI app, ask for example:
   "List my Shield dossiers. Read the documents of DOSSIER_1 and draft submissions. Save the draft with Shield."
4. The AI sees only codes. It saves the draft with the Shield tool.
5. Shield writes the document, with the real names, into the **"Shield - sorties"** subfolder
   of the case folder. Open it on your computer and review it.

The AI cannot ask Shield for the real names. Only your computer puts them back.

### With any app (Word, Outlook, Copilot, claude.ai, chatgpt.com)

1. Open Shield Desk with the link that `uvx ragbase-shield desk` shows, page **Masquer** (Mask). Choose the
   dossier. Without a dossier, registered names become [PERSONNE] or [SOCIETE] and restore is not possible.
2. Paste your text into the original-text box (not into the chat), then click "Masquer" (Mask).
3. Check the detected items, then click "Copier le texte masqué" (Copy masked text).
4. Paste the masked text into the AI app.
5. Copy the AI's answer. In Shield Desk, page **Restaurer** (Restore), paste it and click
   "Restaurer les noms" (Restore names). Shield also lists codes it does not know in this dossier
   (for example a code the AI invented). Copy the restored text into your document.
   Never paste it back into the chat: it contains the real names.

From a terminal, the same in two commands:
`ragbase-shield mask --dossier DOSSIER_1 --clipboard` replaces the clipboard with the masked text.
`ragbase-shield restore --dossier DOSSIER_1 --clipboard` puts the real names back into the clipboard.

---

## Results: public head-to-head of 11 November 2026

Full file, with every set, mode, status, method and limit:
[evaluation/laptop/RESULTS_PUBLIC.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/evaluation/laptop/RESULTS_PUBLIC.md) (French first, then English).
Protocol fixed in advance: [PROTOCOL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/evaluation/laptop/PROTOCOL.md) and its addenda in the same folder.

Read this before the numbers:

- **Shield 0.4.0 was built after the first results of this comparison were known. No data set is held-out for
  Shield 0.4.0. Hexagone 0.3.9 and Presidio 2.2.364 were measured in October 2026 and were not run again.**
  So the comparison is Shield of November against the other tools of October.
- Shield is our product (RAGbase). We ran this test.
- Status of each set for Shield 0.4.0: REF (not held-out: written by the Shield team, 0.3.1 results known),
  FR-PII-Bench and MAPA (gates), Max (gate, with a fix from this study), Judilibre (not held-out for 0.4.0),
  English (development set).
- Machine: a Windows VM (6 cores, 16 GB, no graphics card). It is not a laptop.
- "Shield 0.4.0 rules" is the product default. "Shield 0.4.0 GLiNER" means rules plus the GLiNER model on the CPU.
- Tonic: measured internally, not published (Tonic's terms).

**Result by the rule fixed in advance** (protocol section 11.3; addendum 4, section 20.9). For Shield 0.4.0 the only
wording allowed is "the conditions of section 11.3 are met" or "are not met".

| Reading | Against Hexagone Fast | Against Hexagone Precis |
|---|---|---|
| Shield 0.4.0, both rows together (the reading of Table 3) | **conditions not met** | **conditions not met** |
| Shield 0.4.0 rules, the product default (S-R4) | conditions not met | conditions not met |
| Shield 0.4.0 GLiNER (S-N4) | conditions not met | conditions not met |
| For reading: Shield 0.3.1, October (Table 3) | conditions not met | conditions not met |

Reason, the same for every line: on REF (not held-out), Hexagone Fast and Hexagone Precis leave less personal data
readable than Shield 0.4.0, with a clear difference. Clear differences in the same direction on MAPA (gate) and
English (development) for Hexagone Fast and Precis, and on FR-PII-Bench (gate) for Hexagone Precis. Detail: Table 14.
Tonic: measured internally, not published (Tonic's terms). Speed is not part of this rule.

**Key numbers** (lower is better; VM, not a laptop). The "Status" column gives the status of REF and Judilibre for
each line.

| Tool | Status of REF and Judilibre for this line | Personal data readable, REF | Legal terms changed, REF | Legal terms changed, Judilibre | Median time, one 10-page REF file | Memory, REF |
|---|---|---|---|---|---|---|
| Shield 0.4.0 rules | not held-out (0.3.1 results known) | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 296 of 6,136 (4.8 %); subset of 50: 88 of 1,476 (6.0 %) | 0.59 s (11 November) | 74 to 75 MB |
| Shield 0.4.0 GLiNER | not held-out (0.3.1 results known) | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 1,048 of 6,136 (17.1 %); 50: 233 (15.8 %) | 17.4 s (11 November) | 3.8 GB |
| Shield 0.3.1 rules | REF invented; Judilibre held-out | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 296 of 6,136 (4.8 %); 50: 88 (6.0 %) | 0.75 s (25 October) | 74 MB |
| Shield 0.3.1 GLiNER | REF invented; Judilibre held-out | 56 of 1,015 (5.5 %) | 15 of 365 (4.1 %) | 1,048 of 6,136 (17.1 %); 50: 233 (15.8 %) | 23 s (25 October) | 3.7 GB |
| Hexagone Fast | REF new; Judilibre held-out | 38 of 1,015 (3.7 %) | 65 of 365 (17.8 %) | 2,264 of 6,136 (36.9 %); 50: 581 (39.4 %) | 27 s (October) | 1.6 to 1.7 GB |
| Hexagone Precis | REF new; Judilibre held-out | 1 of 1,015 (0.1 %) | 172 of 365 (47.1 %) | subset of 50 only: 637 of 1,476 (43.2 %) | 540 s, that is 9 min (October, partial) | 3.8 to 5.4 GB |
| Presidio | REF new; Judilibre held-out | 249 of 1,015 (24.5 %) | 56 of 365 (15.3 %) | 911 of 6,136 (14.8 %); 50: 234 (15.9 %) | 1.6 s (25 October) | 0.57 GB |
| Tonic (cloud) | | measured internally, not published (Tonic's terms) | | | | |

What this means, in short (the claims of Table 13, in both directions):

- **The trade-off.** On REF (not held-out), Shield 0.4.0 leaves more personal data readable than Hexagone, and it
  changes far fewer legal terms (courts, laws, codes, articles).
- **Personal data readable (P1), where Hexagone leaves less.** Hexagone Fast and Hexagone Precis: on REF (not
  held-out), MAPA (gate) and English (development). Hexagone Precis also on FR-PII-Bench (gate).
- **Personal data readable (P1), where Shield 0.4.0 leaves less.** Against Hexagone Fast on FR-PII-Bench (gate).
  Against Presidio on REF, FR-PII-Bench, Max and Judilibre. On English, Presidio leaves less than Shield 0.4.0
  rules, and Shield 0.4.0 GLiNER leaves less than Presidio.
- **No clear difference (P1).** With Hexagone Fast and Hexagone Precis on Max (gate, with a fix from this study)
  and on Judilibre (not held-out for 0.4.0). With Presidio on MAPA.
- **Legal terms changed (P2).** Both Shield 0.4.0 rows change fewer legal terms than Hexagone Fast and Precis on
  every set that has them. Against Presidio: fewer on REF, MAPA and Max for both rows, and on Judilibre for the
  rules row; no clear difference on Judilibre for the GLiNER row.
- **Shield 0.4.0 against 0.3.1.** In rules mode the output text is identical on REF, FR-PII-Bench, MAPA and
  Judilibre. In GLiNER mode, on English (development), Shield 0.4.0 leaves more organisation names readable than
  0.3.1: a clear difference against 0.4.0.
- **Speed.** We do not say that 0.4.0 is faster than 0.3.1: the two sessions are 16 days apart on the same VM.

<details>
<summary>Every set, P1 and P2, both Shield 0.4.0 rows (Tables 12, 13, 14 and 16 of the public file, as printed there)</summary>

P1 = gold personal data items still readable (lower is better). P2 = legal terms that must stay clear and were
changed (lower is better). In brackets: rate and 95 % Wilson interval. The October rows are printed again for reading.

**Table 12. P1 protection and P2 over-masking with the Shield 0.4.0 rows**

| Set | Row | Status of the set for this row | Docs (failed) | P1 exposed, strict | P1 exposed, value | P2 must-stay-clear altered |
|---|---|---|---|---|---|---|
| REF | S-R4, Shield 0.4.0 rules | not held-out: team-written, 0.3.1 results known; unused by record | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: team-written, 0.3.1 results known; unused by record | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-R, Shield 0.3.1 rules | invented | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | S-N, Shield 0.3.1 rules + GLiNER | invented | 5 (0) | 56 of 1,015 (5.5 %; 4.3 to 7.1) | 31 of 1,015 (3.1 %; 2.2 to 4.3) | 15 of 365 (4.1 %; 2.5 to 6.7) |
| REF | H-F, Hexagone 0.3.9 Fast | new to every other tool | 5 (0) | 38 of 1,015 (3.7 %; 2.7 to 5.1) | 9 of 1,015 (0.9 %; 0.5 to 1.7) | 65 of 365 (17.8 %; 14.2 to 22.1) |
| REF | H-P, Hexagone 0.3.9 Precis | new to every other tool | 5 (0) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 1 of 1,015 (0.1 %; 0.0 to 0.6) | 172 of 365 (47.1 %; 42.1 to 52.2) |
| REF | P, Presidio 2.2.364 | new to every other tool | 5 (0) | 249 of 1,015 (24.5 %; 22.0 to 27.3) | 185 of 1,015 (18.2 %; 16.0 to 20.7) | 56 of 365 (15.3 %; 12.0 to 19.4) |
| FR-PII-Bench | S-R4, Shield 0.4.0 rules | gate | 300 (0) | 36 of 2,105 (1.7 %; 1.2 to 2.4) | 27 of 2,105 (1.3 %; 0.9 to 1.9) | no items |
| FR-PII-Bench | S-N4, Shield 0.4.0 rules + GLiNER | gate | 300 (0) | 26 of 2,105 (1.2 %; 0.8 to 1.8) | 18 of 2,105 (0.9 %; 0.5 to 1.3) | no items |
| FR-PII-Bench | S-R, Shield 0.3.1 rules | informed | 300 (0) | 36 of 2,105 (1.7 %; 1.2 to 2.4) | 27 of 2,105 (1.3 %; 0.9 to 1.9) | no items |
| FR-PII-Bench | S-N, Shield 0.3.1 rules + GLiNER | informed | 300 (0) | 26 of 2,105 (1.2 %; 0.8 to 1.8) | 18 of 2,105 (0.9 %; 0.5 to 1.3) | no items |
| FR-PII-Bench | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 300 (0) | 72 of 2,105 (3.4 %; 2.7 to 4.3) | 45 of 2,105 (2.1 %; 1.6 to 2.8) | no items |
| FR-PII-Bench | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 300 (0) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | 3 of 2,105 (0.1 %; 0.0 to 0.4) | no items |
| FR-PII-Bench | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 300 (0) | 918 of 2,105 (43.6 %; 41.5 to 45.7) | 543 of 2,105 (25.8 %; 24.0 to 27.7) | no items |
| MAPA | S-R4, Shield 0.4.0 rules | gate | 19 (0) | 319 of 1,615 (19.8 %; 17.9 to 21.8) | 286 of 1,615 (17.7 %; 15.9 to 19.6) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-N4, Shield 0.4.0 rules + GLiNER | gate | 19 (0) | 222 of 1,615 (13.7 %; 12.2 to 15.5) | 189 of 1,615 (11.7 %; 10.2 to 13.4) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-R, Shield 0.3.1 rules | informed | 19 (0) | 319 of 1,615 (19.8 %; 17.9 to 21.8) | 286 of 1,615 (17.7 %; 15.9 to 19.6) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | S-N, Shield 0.3.1 rules + GLiNER | informed | 19 (0) | 222 of 1,615 (13.7 %; 12.2 to 15.5) | 189 of 1,615 (11.7 %; 10.2 to 13.4) | 0 of 1,344 (0.0 %; 0.0 to 0.3) |
| MAPA | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 19 (0) | 89 of 1,615 (5.5 %; 4.5 to 6.7) | 58 of 1,615 (3.6 %; 2.8 to 4.6) | 579 of 1,344 (43.1 %; 40.5 to 45.7) |
| MAPA | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 19 (0) | 100 of 1,615 (6.2 %; 5.1 to 7.5) | 90 of 1,615 (5.6 %; 4.6 to 6.8) | 640 of 1,344 (47.6 %; 45.0 to 50.3) |
| MAPA | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 19 (0) | 294 of 1,615 (18.2 %; 16.4 to 20.2) | 216 of 1,615 (13.4 %; 11.8 to 15.1) | 242 of 1,344 (18.0 %; 16.0 to 20.2) |
| Max, 33 documents | S-R4, Shield 0.4.0 rules | gate, with a fix from this study | 33 (0) | 52 of 1,003 (5.2 %; 4.0 to 6.7) | 48 of 1,003 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max, 33 documents | S-N4, Shield 0.4.0 rules + GLiNER | gate, with a fix from this study | 33 (0) | 48 of 1,003 (4.8 %; 3.6 to 6.3) | 41 of 1,003 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max, 33 documents | S-R, Shield 0.3.1 rules | informed | 33 (1) | 54 of 1,003 (5.4 %; 4.1 to 7.0) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max, 33 documents | S-N, Shield 0.3.1 rules + GLiNER | informed | 33 (1) | 50 of 1,003 (5.0 %; 3.8 to 6.5) | 43 of 1,003 (4.3 %; 3.2 to 5.7) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max, 33 documents | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 33 (2) | 67 of 1,003 (6.7 %; 5.3 to 8.4) | 56 of 1,003 (5.6 %; 4.3 to 7.2) | 68 of 144 (47.2 %; 39.2 to 55.3) |
| Max, 33 documents | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 33 (2) | 38 of 1,003 (3.8 %; 2.8 to 5.2) | 33 of 1,003 (3.3 %; 2.4 to 4.6) | 84 of 144 (58.3 %; 50.2 to 66.1) |
| Max, 33 documents | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 33 (0) | 393 of 1,003 (39.2 %; 36.2 to 42.2) | 315 of 1,003 (31.4 %; 28.6 to 34.3) | 80 of 144 (55.6 %; 47.4 to 63.4) |
| Max without the workbook, 32 documents | S-R4, Shield 0.4.0 rules | gate, with a fix from this study | 32 (0) | 52 of 1,001 (5.2 %; 4.0 to 6.7) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max without the workbook, 32 documents | S-N4, Shield 0.4.0 rules + GLiNER | gate, with a fix from this study | 32 (0) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 41 of 1,001 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max without the workbook, 32 documents | S-R, Shield 0.3.1 rules | informed | 32 (0) | 52 of 1,001 (5.2 %; 4.0 to 6.7) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 3 of 144 (2.1 %; 0.7 to 5.9) |
| Max without the workbook, 32 documents | S-N, Shield 0.3.1 rules + GLiNER | informed | 32 (0) | 48 of 1,001 (4.8 %; 3.6 to 6.3) | 41 of 1,001 (4.1 %; 3.0 to 5.5) | 6 of 144 (4.2 %; 1.9 to 8.8) |
| Max without the workbook, 32 documents | H-F, Hexagone 0.3.9 Fast | not seen by the other tools, as far as we know | 32 (1) | 65 of 1,001 (6.5 %; 5.1 to 8.2) | 54 of 1,001 (5.4 %; 4.2 to 7.0) | 68 of 144 (47.2 %; 39.2 to 55.3) |
| Max without the workbook, 32 documents | H-P, Hexagone 0.3.9 Precis | not seen by the other tools, as far as we know | 32 (1) | 36 of 1,001 (3.6 %; 2.6 to 4.9) | 31 of 1,001 (3.1 %; 2.2 to 4.4) | 84 of 144 (58.3 %; 50.2 to 66.1) |
| Max without the workbook, 32 documents | P, Presidio 2.2.364 | not seen by the other tools, as far as we know | 32 (0) | 392 of 1,001 (39.2 %; 36.2 to 42.2) | 314 of 1,001 (31.4 %; 28.6 to 34.3) | 80 of 144 (55.6 %; 47.4 to 63.4) |
| Judilibre, 200 decisions | S-R4, Shield 0.4.0 rules | not held-out: 0.3.1 results known, same-source gate; unused by record | 200 (0) | 6 of 673 (0.9 %; 0.4 to 1.9) | 2 of 673 (0.3 %; 0.1 to 1.1) | 296 of 6,136 (4.8 %; 4.3 to 5.4) |
| Judilibre, 200 decisions | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: 0.3.1 results known, same-source gate; unused by record | 200 (0) | 4 of 673 (0.6 %; 0.2 to 1.5) | 2 of 673 (0.3 %; 0.1 to 1.1) | 1,048 of 6,136 (17.1 %; 16.2 to 18.0) |
| Judilibre, 200 decisions | S-R, Shield 0.3.1 rules | held-out | 200 (0) | 6 of 673 (0.9 %; 0.4 to 1.9) | 2 of 673 (0.3 %; 0.1 to 1.1) | 296 of 6,136 (4.8 %; 4.3 to 5.4) |
| Judilibre, 200 decisions | S-N, Shield 0.3.1 rules + GLiNER | held-out | 200 (0) | 4 of 673 (0.6 %; 0.2 to 1.5) | 2 of 673 (0.3 %; 0.1 to 1.1) | 1,048 of 6,136 (17.1 %; 16.2 to 18.0) |
| Judilibre, 200 decisions | H-F, Hexagone 0.3.9 Fast | held-out | 200 (0) | 11 of 673 (1.6 %; 0.9 to 2.9) | 8 of 673 (1.2 %; 0.6 to 2.3) | 2,264 of 6,136 (36.9 %; 35.7 to 38.1) |
| Judilibre, 200 decisions | P, Presidio 2.2.364 | held-out | 200 (0) | 93 of 673 (13.8 %; 11.4 to 16.6) | 68 of 673 (10.1 %; 8.0 to 12.6) | 911 of 6,136 (14.8 %; 14.0 to 15.8) |
| Judilibre, Precis subset of 50 | S-R4, Shield 0.4.0 rules | not held-out: 0.3.1 results known, same-source gate; unused by record | 50 (0) | 3 of 194 (1.5 %; 0.5 to 4.4) | 1 of 194 (0.5 %; 0.1 to 2.9) | 88 of 1,476 (6.0 %; 4.9 to 7.3) |
| Judilibre, Precis subset of 50 | S-N4, Shield 0.4.0 rules + GLiNER | not held-out: 0.3.1 results known, same-source gate; unused by record | 50 (0) | 1 of 194 (0.5 %; 0.1 to 2.9) | 1 of 194 (0.5 %; 0.1 to 2.9) | 233 of 1,476 (15.8 %; 14.0 to 17.7) |
| Judilibre, Precis subset of 50 | S-R, Shield 0.3.1 rules | held-out | 50 (0) | 3 of 194 (1.5 %; 0.5 to 4.4) | 1 of 194 (0.5 %; 0.1 to 2.9) | 88 of 1,476 (6.0 %; 4.9 to 7.3) |
| Judilibre, Precis subset of 50 | S-N, Shield 0.3.1 rules + GLiNER | held-out | 50 (0) | 1 of 194 (0.5 %; 0.1 to 2.9) | 1 of 194 (0.5 %; 0.1 to 2.9) | 233 of 1,476 (15.8 %; 14.0 to 17.7) |
| Judilibre, Precis subset of 50 | H-F, Hexagone 0.3.9 Fast | held-out | 50 (0) | 2 of 194 (1.0 %; 0.3 to 3.7) | 1 of 194 (0.5 %; 0.1 to 2.9) | 581 of 1,476 (39.4 %; 36.9 to 41.9) |
| Judilibre, Precis subset of 50 | H-P, Hexagone 0.3.9 Precis | held-out | 50 (0) | 0 of 194 (0.0 %; 0.0 to 1.9) | 0 of 194 (0.0 %; 0.0 to 1.9) | 637 of 1,476 (43.2 %; 40.7 to 45.7) |
| Judilibre, Precis subset of 50 | P, Presidio 2.2.364 | held-out | 50 (0) | 32 of 194 (16.5 %; 11.9 to 22.4) | 21 of 194 (10.8 %; 7.2 to 16.0) | 234 of 1,476 (15.9 %; 14.1 to 17.8) |
| English | S-R4, Shield 0.4.0 rules | development set (in-sample) | 241 (0) | 143 of 1,276 (11.2 %; 9.6 to 13.1) | 136 of 1,276 (10.7 %; 9.1 to 12.5) | no items |
| English | S-N4, Shield 0.4.0 rules + GLiNER | development set (in-sample) | 241 (0) | 49 of 1,276 (3.8 %; 2.9 to 5.0) | 41 of 1,276 (3.2 %; 2.4 to 4.3) | no items |
| English | S-R, Shield 0.3.1 rules | informed | 241 (0) | 142 of 1,276 (11.1 %; 9.5 to 13.0) | 135 of 1,276 (10.6 %; 9.0 to 12.4) | no items |
| English | S-N, Shield 0.3.1 rules + GLiNER | informed | 241 (0) | 27 of 1,276 (2.1 %; 1.5 to 3.1) | 23 of 1,276 (1.8 %; 1.2 to 2.7) | no items |
| English | H-F, Hexagone 0.3.9 Fast | public benchmark; Hexagone publishes numbers on it | 241 (0) | 22 of 1,276 (1.7 %; 1.1 to 2.6) | 15 of 1,276 (1.2 %; 0.7 to 1.9) | no items |
| English | H-P, Hexagone 0.3.9 Precis | public benchmark; Hexagone publishes numbers on it | 241 (0) | 10 of 1,276 (0.8 %; 0.4 to 1.4) | 8 of 1,276 (0.6 %; 0.3 to 1.2) | no items |
| English | P, Presidio 2.2.364 | public benchmark; Hexagone publishes numbers on it | 241 (0) | 108 of 1,276 (8.5 %; 7.1 to 10.1) | 107 of 1,276 (8.4 %; 7.0 to 10.0) | no items |

**Table 13. Claims per set for the Shield 0.4.0 rows** (paired bootstrap over documents; a claim needs the whole
95 % interval on one side of 0; "none" = no clear difference; claims in both directions have the same weight)

| Set (status for Shield 0.4.0) | Shield 0.4.0 row against | P1, S-R4 | P1, S-N4 | P2, S-R4 | P2, S-N4 | Different from the 0.3.1 rows? |
|---|---|---|---|---|---|---|
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | H-F | H-F better | H-F better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | H-P | H-P better | H-P better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | no |
| REF (not held-out: team-written, 0.3.1 results known; unused by record) | S-R4 against S-N4 | none | | none | | no |
| FR-PII-Bench (gate) | H-F | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | H-F, 30 % cut (sensitivity reading) | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | H-P | H-P better | H-P better | no items | no items | no |
| FR-PII-Bench (gate) | H-P, 30 % cut (sensitivity reading) | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | P | S-R4 better | S-N4 better | no items | no items | no |
| FR-PII-Bench (gate) | S-R4 against S-N4 | S-N4 better | | no items | | no |
| MAPA (gate) | H-F | H-F better | H-F better | S-R4 better | S-N4 better | no |
| MAPA (gate) | H-P | H-P better | H-P better | S-R4 better | S-N4 better | no |
| MAPA (gate) | P | none | none | S-R4 better | S-N4 better | no |
| MAPA (gate) | S-R4 against S-N4 | S-N4 better | | none | | no |
| Max, 33 documents (gate, with a fix from this study) | H-F | none | none | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | H-P | none | none | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | no |
| Max, 33 documents (gate, with a fix from this study) | S-R4 against S-N4 | none (readings disagree) | | none | | no |
| Max without the workbook, 32 documents (gate, with a fix from this study) | H-F | none | none | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Max without the workbook, 32 documents (gate, with a fix from this study) | H-P | none | none | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Max without the workbook, 32 documents (gate, with a fix from this study) | P | S-R4 better | S-N4 better | S-R4 better | S-N4 better | not in Table 2 (new reading) |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-F | none | none | S-R4 better | S-N4 better | no |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | none | no |
| Judilibre, 200 decisions (not held-out: 0.3.1 results known, same-source gate; unused by record) | S-R4 against S-N4 | none | | S-R4 better | | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-F | none | none | S-R4 better | S-N4 better | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | H-P | none (the interval touches 0) | none (the interval touches 0) | S-R4 better | S-N4 better | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | P | S-R4 better | S-N4 better | S-R4 better | none | no |
| Judilibre, Precis subset of 50 (not held-out: 0.3.1 results known, same-source gate; unused by record) | S-R4 against S-N4 | none | | S-R4 better | | no |
| English (development set (in-sample)) | H-F | H-F better | H-F better | no items | no items | yes, P1 for S-N4: "none" for the 0.3.1 row |
| English (development set (in-sample)) | H-P | H-P better | H-P better | no items | no items | no |
| English (development set (in-sample)) | P | P better | S-N4 better | no items | no items | no |
| English (development set (in-sample)) | S-R4 against S-N4 | S-N4 better | | no items | | no |

**Table 14. The section 11.3 reading for Shield 0.4.0**

| Overall line | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) |
|---|---|---|
| Shield 0.4.0 (S-R4 and S-N4 together) | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-F better); S-N4: no P1 claim on REF (H-F better). Opposite claims: S-R4: REF P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: MAPA P1; S-N4: English P1 | **conditions not met**. Fails: S-R4: no P1 claim on REF (H-P better); S-N4: no P1 claim on REF (H-P better). Opposite claims: S-R4: REF P1; S-R4: FR-PII-Bench P1; S-R4: MAPA P1; S-R4: English P1; S-N4: REF P1; S-N4: FR-PII-Bench P1; S-N4: MAPA P1; S-N4: English P1 |
| Shield 0.3.1 (S-R and S-N together), Table 3 of October, cited as written | No | No |

| Shield row | Against Hexagone Fast (H-F) | Against Hexagone Precis (H-P) | Against Presidio (per set only) |
|---|---|---|---|
| S-R4, Shield 0.4.0 rules (product default) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N4, Shield 0.4.0 rules + GLiNER | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |
| S-R, Shield 0.3.1 rules (October files, same rule) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1; English P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, Judilibre P2. Presidio better: English P1 |
| S-N, Shield 0.3.1 rules + GLiNER (the same) | **conditions not met**. Fails: no P1 claim on REF (H-F better). Opposite claims: REF P1; MAPA P1 | **conditions not met**. Fails: no P1 claim on REF (H-P better). Opposite claims: REF P1; FR-PII-Bench P1; MAPA P1; English P1 | Shield row better: REF P1, REF P2, FR-PII-Bench P1, MAPA P2, Max P1, Max P2, Judilibre P1, English P1. Presidio better: none |

**Table 16. Failed documents**

| Set | S-R4 | S-N4 | S-R (October) | S-N (October) | H-F (October) | H-P (October) | P (October) |
|---|---:|---:|---:|---:|---:|---:|---:|
| REF (5 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| FR-PII-Bench (300 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MAPA (19 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Max (33 documents) | 0 | 0 | 1 | 1 | 2 | 2 | 0 |
| Judilibre (200 documents) | 0 | 0 | 0 | 0 | 0 | 0 of 50 (subset) | 0 |
| English (241 documents) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

</details>

---

## Limits (please read)

- **No OCR.** A scanned PDF (an image) has no text. Shield says so and does not read it.
- **Detection is never complete.** A name nobody registered can slip through:
  a rare name, a foreign name, a nickname, a typo. Register the parties of each dossier.
  Those are the names Shield masks most reliably.
- **In the public head-to-head, Hexagone leaves less personal data readable on some sets** (REF, MAPA and English;
  Hexagone Precis also on FR-PII-Bench). Shield changes fewer legal terms. Read the results above with their
  status: no set is held-out for Shield 0.4.0.
- **Restored names use the spelling stored in the dossier.** "M. Mercadier" can come back as
  "M. Thibault Mercadier", and capital letters can change. Identifiers come back in the first spelling seen in
  the dossier (for example "832 456 719" for "832456719"). Re-read the restored document.
- **Facts can still identify a client**, even without a name: a well-known case, a unique job title,
  a precise place, an amount. Shield does not mask facts. Review, and generalise when needed.
- **ChatGPT web (chatgpt.com) has no native connection.** Use Shield Desk or the browser extension.
- **Microsoft 365 Copilot (Word, Outlook, Teams, the Copilot app): through Shield Desk only.**
  Warning: Copilot in Word or Outlook reads the open document or email. Open a masked copy, not the original.
- **The browser extension masks text you paste or drop.** Text you type goes out as typed. A file pasted or
  dropped into the chat is blocked; "Attach anyway" sends it unmasked. It is not in the Chrome or Edge stores yet.
- **The installers are not signed yet.** macOS and Windows show a warning the first time.
- **An administrator can block Shield**: extensions in Claude Team or Enterprise,
  MCP servers in Copilot Business or Enterprise.
- **The GDPR still applies.** For you, pseudonymised data are still personal data.

French compliance sheet (CNB, Paris bar, avocats aux Conseils, GDPR): [docs/CONFORMITE.fr.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/CONFORMITE.fr.md)
FAQ: [docs/FAQ.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/FAQ.md)

---

## Privacy model in 5 lines

1. Masking and restoring run on your computer. The AI provider receives codes, never the real names that Shield
   detected or that you registered.
2. The code-to-name table (the vault) is encrypted, one per dossier; its key stays in the OS keychain (or a file
   only you can read).
3. No tool gives real names to the model, and an AI agent cannot change what is masked.
4. No network call in the library, no telemetry, no update check. The only download you start yourself is the
   optional name recognition model.
5. Pseudonymised data are still personal data: Shield reduces what the provider sees. It is pseudonymisation,
   not anonymisation.

Full model: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/PRIVACY_MODEL.md).

---

## For developers and IT

### Architecture in short

- A local engine (rules, dictionaries, check digits) finds names and identifiers, in French and in English
  (the language is detected per text, or pinned with `RAGBASE_SHIELD_LANGUAGE`).
  A name recognition model (NER) is optional; none is installed by default. To add one (about 1.2 GB,
  Apache-2.0, runs offline, CPU only):

  ```
  pip install "ragbase-shield[ner]"      # or: uv pip install "ragbase-shield[ner]"
  ragbase-shield ner download            # fastino/gliner2-privacy-filter-PII-multi, once, into ~/.ragbase-shield/models
  ragbase-shield ner status              # or: ragbase-shield doctor
  ```

  The model's finds pass the same whitelist and precision guards as the rules; the hooks and the canary never use
  it. `RAGBASE_SHIELD_NER=off` turns it off.
- Replacement by codes (`PERSONNE_A`) by default, or by realistic pseudonyms (`ragbase-shield set DOSSIER_n
  --replacement synthetic`): reversible through the vault, pseudonymisation, not anonymisation.
- One encrypted vault per dossier (SQLite + Fernet). The key lives in the OS keychain,
  or in a file only you can read (mode 0600).
- A local MCP server (stdio) for Claude, ChatGPT desktop, Codex and VS Code.
  Its tools take dossier and document codes, never raw text. No tool gives real names to the model.
- Shield Desk: a local web page on 127.0.0.1, with a per-install token.
- Claude Code hooks block a prompt that contains a registered name, and direct reads of a dossier folder.
- No network calls in library code. No telemetry.

Full contract: [ARCHITECTURE.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/ARCHITECTURE.md). Privacy model: [docs/PRIVACY_MODEL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/PRIVACY_MODEL.md).

### Command line

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

With uv, prefix with `uvx` (`uvx ragbase-shield doctor`),
or install the command once: `uv tool install ragbase-shield`.
From a copy of the repository: `uv tool install .` (or `uv tool install --editable .` to develop).
The configs written by `install` then work, and `doctor` checks that each app can start Shield.

From an AI agent's terminal (Claude Code, Codex), `entities`, `restore` and `export` refuse to run, because
what they print reaches the model. `add`, `register`, `keep-clear` and `import` refuse too: an AI assistant
cannot change what is masked. `list` shows codes only. Run these commands in your own terminal, or use
Shield Desk.

### Supported apps

| App | How Shield plugs in |
|---|---|
| Claude Desktop | One-click extension (`.mcpb`) that runs the local MCP server |
| Claude Code and Cowork | Plugin: MCP server + skill + hooks |
| ChatGPT desktop and Codex | Local MCP server (`~/.codex/config.toml`), where local MCP is allowed |
| GitHub Copilot (VS Code) | Local MCP server (`mcp.json`) |
| Any other app (claude.ai, chatgpt.com, Copilot, Word, Outlook) | Shield Desk, clipboard, browser extension |

### Check it yourself

- `ragbase-shield doctor` checks the install, key storage and each app integration.
- `ragbase-shield verify` plants invented data, runs every path (MCP tools, hooks, Desk) and prints CLEAN or LEAK.
- Tests: `uv run --extra dev pytest -q`. Synthetic data only.
- Bench: `uv run python bench/run_bench.py` (recall and precision per kind, on an invented French legal corpus
  written together with the rules; it is a regression gate, not an accuracy figure for real files).
- Benchmark runners: `evaluation/public/` (public benchmarks; data downloaded into the git-ignored
  `.bench_data/`), `evaluation/holdout-en/` (an invented English corpus), `evaluation/laptop/` (the frozen scorer
  and runners of the public head-to-head).
- Desktop installers: [packaging/README.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/packaging/README.md).

### Environment variables

| Variable | Effect |
|---|---|
| `RAGBASE_SHIELD_HOME` | Data folder (default `~/.ragbase-shield`, or `%LOCALAPPDATA%\ragbase-shield` on Windows) |
| `RAGBASE_SHIELD_LOCALE=en` | English code labels (PERSON_A, COMPANY_A) instead of PERSONNE_A, SOCIETE_A |
| `RAGBASE_SHIELD_PORT` | Shield Desk port (default 7878) |
| `RAGBASE_SHIELD_KEYRING=0` | Key in a 0600 file instead of the OS keychain |
| `RAGBASE_SHIELD_MASK_TOQUE=0` | Keeps lawyers' "toque" numbers visible (masked by default) |

### Contributing, security, licence

- Security issues: [SECURITY.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/SECURITY.md). Do not open a public issue.
- Release history: [CHANGELOG.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/CHANGELOG.md).
- Licence: [Apache-2.0](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/LICENSE). Attributions: [NOTICE](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/NOTICE).
- Test data: invented only. Never put real client data in an issue.

---

## Links

- Source code: https://github.com/ragbase/ragbase-shield
- Releases (installers, `.mcpb`, `SHA256SUMS`): https://github.com/ragbase/ragbase-shield/releases/latest
- Issues: https://github.com/ragbase/ragbase-shield/issues
- Product page: https://shield.ragbase.ai
- Install guide per app: [docs/INSTALL.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/INSTALL.md). FAQ: [docs/FAQ.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/docs/FAQ.md).
- Public results: [evaluation/laptop/RESULTS_PUBLIC.md](https://github.com/ragbase/ragbase-shield/blob/v0.4.0/evaluation/laptop/RESULTS_PUBLIC.md)

---

## Going further

Shield reduces what the AI sees. It does not replace an AI that runs on your own machines.
If your firm wants a private AI installed on its own hardware, RAGbase offers one:
https://ragbase.ai
