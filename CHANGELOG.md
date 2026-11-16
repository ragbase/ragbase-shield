# Changelog

All notable changes to RAGbase Shield are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.4.4] - 2026-11-17

- Shield works inside the Claude app, on Mac and on Windows, with nothing else to install: add it from
  https://shield.ragbase.ai/installer/ (it needs the Claude desktop app, signed in, with a paid Claude plan). In a new
  conversation, write "Protège un dossier avec Shield" and choose the folder of one client in the Shield window.
- A protected folder is ready at once in each new conversation: Shield keeps the masked text of the folder,
  encrypted, on your computer. When a file of the folder changes, Shield reads the whole folder again.
- Shield reads documents up to 6 million characters. A long PDF file gets more time.
- A place of birth is masked where the text says that it is a place of birth, for example next to a birth date. The
  same town elsewhere in the dossier, as in the name of a court or in "Fait à", stays in clear.
- On Windows, Shield reports the documents whose path is too long, and shortens the name of the final document to
  fit the Windows limit.

## [0.4.3] - 2026-11-16

Published as the Claude plugin only.

- Long PDF files are read fast: about 30 seconds and little memory for a file of 800 pages.
- A large folder is read in the background, and Claude tells you how far the reading is. No document is shown before
  the whole folder is read, so a name found in the last document is also hidden in the first ones.
- Two conversations can work on the same folder: the second one waits for the reading of the first one.
- Dossier codes and counts in Shield's own answers stay readable for Claude.
- A party name in the name of a folder is kept whole, also when it ends in "al".

## [0.4.2] - 2026-11-16

Published as the Claude plugin only.

- The Claude plugin for the Claude app, on Mac and on Windows: it carries Shield and its own Python, so there is
  nothing else to install. It gives Claude seven tools in French.
- Shield opens its own window to choose the folder of one client. The folder name, which often holds the names of
  the parties, never goes to Claude. Only a folder chosen in this window is protected: a file attached to the
  conversation, or a folder added to it, is not.
- Claude reads the documents with codes in place of the names and answers with codes. The real names come back only
  on your computer, in the final document that Shield saves in "Shield - sorties".
- The settings of the plugin are locked, and its key is in the macOS keychain or the Windows Credential Manager.
- Shield masks the place of birth.
- Windows: the plugin works in the deep folder where the Claude app puts it, and its data is in your user folder.

## [0.4.1] - 2026-11-14

- After "M.", "Mme", "Mlle" or "Me", Shield masks the name that follows, with or without capitals, in every French text.
- In text typed without capitals, as on a phone or in a quick note, Shield also masks names with or without a title, companies written with their legal form, postal addresses and the fields "nom :" and "prénom :".
- The setting RAGBASE_SHIELD_LOWERCASE_NAMES=0 turns these rules off.

## [0.4.0] - 2026-11-12

First public release.

- Local, reversible pseudonymisation for legal documents, built for French first, with English support. Shield
  replaces names, companies, addresses, e-mails, phone numbers, bank and identity numbers and case numbers with codes
  on your computer, then puts the real values back in the answer.
- Two modes: Fast (rules only, the default) and Precise (rules and an AI model that runs on your computer).
- Works with Claude Desktop, Claude Code and Cowork (extension, plugin and local MCP server), and with any other app
  through Shield Desk.
- Reads PDF, Word, Excel, e-mail, HTML and text files.
- Installers for macOS and Windows, and `pip install ragbase-shield` on every platform.
- Codes or realistic fictional names as replacements. Inside one dossier, a person always keeps the same code.
- Benchmark against Hexagone and Presidio: [evaluation/laptop/RESULTS_PUBLIC.md](evaluation/laptop/RESULTS_PUBLIC.md).
