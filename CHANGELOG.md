# Changelog

All notable changes to RAGbase Shield are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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
