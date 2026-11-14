# Changelog

All notable changes to RAGbase Shield are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.4.1] - 2026-11-14

- Shield now masks names and companies typed in lower case in French text: "m. thibault mercadier", "mon client
  thibault mercadier", "la société ateliers brunelac sas". Type your prompt the way you write, with or without
  capital letters.
- The same person keeps the same code whatever the letter case.

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
