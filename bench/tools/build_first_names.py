"""Rebuild ``engine/lexicon/first_names_fr.txt`` from the INSEE national first-name file.

Source: INSEE, "Fichier des prénoms" (édition 2025, births 1900-2025), national file
``prenoms-2025-nat.csv`` from https://www.insee.fr/fr/statistiques/8595130
(Licence Ouverte / Open Licence 2.0, Etalab).

Usage (run by a maintainer, never at runtime; the library makes no network calls)::

    python bench/tools/build_first_names.py prenoms-2025-nat.csv

Rules: names are folded (lower case, no accents, oe/ae ligatures expanded), totals are summed
over sexes and years, names with fewer than ``THRESHOLD`` births in total or shorter than 3
letters are dropped. The output is sorted alphabetically, one name per line.
"""
from __future__ import annotations

import collections
import csv
import sys
import unicodedata
from pathlib import Path

THRESHOLD = 150
OUT = Path(__file__).resolve().parents[2] / "src" / "ragbase_shield" / "engine" / "lexicon" / "first_names_fr.txt"

HEADER = """# French first names (folded: lower case, no accents), one per line.
# Source: INSEE, Fichier des prénoms, édition 2025 (births in France 1900-2025), national file,
# https://www.insee.fr/fr/statistiques/8595130 . Licence Ouverte / Open Licence 2.0 (Etalab).
# Derived data: names with at least {th} births in total and at least 3 letters; counts dropped.
# Rebuild with bench/tools/build_first_names.py.
"""


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("œ", "oe").replace("æ", "ae").replace("’", "'")


def main(path: str) -> None:
    totals: collections.Counter[str] = collections.Counter()
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            name = fold(row["prenom"].strip())
            if not name or name.startswith("_"):
                continue
            try:
                totals[name] += int(row["valeur"])
            except ValueError:
                continue
    names = sorted(n for n, v in totals.items() if v >= THRESHOLD and len(n) >= 3)
    OUT.write_text(HEADER.format(th=THRESHOLD) + "\n".join(names) + "\n", encoding="utf-8")
    print(f"wrote {len(names)} names to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
