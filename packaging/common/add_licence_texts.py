"""Add the missing licence texts to one installer payload of RAGbase Shield (post-build step of the 0.4.0 installers).

Usage:
  python3 -I packaging/common/add_licence_texts.py <payload_dir> <export_root>

<payload_dir>: a single-target payload made by packaging/common/build_payload.py of <export_root>
(build/macos/payload-x86_64, build/macos/payload-arm64 or build/windows/payload). Run it BEFORE
"build_payload.py merge-macos" and before "build.sh --reuse-payload". <export_root>: the clean checkout that built
the payload, for 0.4.0 a clean checkout of the tag v0.4.0 (its packaging/common/build_payload.py writes MANIFEST.json
again, with the same code as the build). Run this script from another checkout (the branch main): a file added under
packaging/ of <export_root> would make the build record "<commit>+dirty".
The upstream texts are read from licence_texts/ next to this script; SOURCES.json there gives the URL and SHA-256 of
each one.

What it adds (licenses.py of the tag v0.4.0 does not do it):
  LICENSES/python/INCORPORATED_SOFTWARE.txt  CPython 3.12.15 Doc/license.rst, section "Licenses and Acknowledgements
                                             for Incorporated Software" (OpenSSL, expat, libffi, zlib, libmpdec and
                                             the other code that CPython incorporates), copied as written
  LICENSES/python/LICENSE.bzip2.txt          bzip2 1.0.8 LICENSE, copied as written
  LICENSES/pyobjc-core/License.txt           macOS only: the PyObjC 12.2.2 licence (the pyobjc-core wheel has no
                                             licence file)
  LICENSES/infi.systray/LICENSE              Windows only: the infi.systray licence of its source repository (the
                                             wheel has no licence file)
  LICENSES/<package>/full-set/...            for a package whose licence files share one file name (pip and its
                                             vendored libraries; pywin32 on Windows): every licence file, with its
                                             path in the dist-info folder (the tag's licenses.py keeps one per name)
  LICENSES/THIRD_PARTY_LICENSES.txt          the runtime line names the new files; notes for the added files; on
                                             Windows the macOS libedit line is removed, and the sentence "No GPL,
                                             LGPL or AGPL component is shipped" is corrected: pywin32 holds the
                                             module adodbapi (LGPL-2.1) and setuptools vendors autocommand
                                             (LGPL-3.0); Shield's own code imports neither
  LICENSES/<package>/vendored/<dist-info>/   the licence files of libraries vendored in a package (setuptools on
                                             Windows); the tag's licenses.py reads top-level dist-info folders only
  LICENSES/licenses.json                     "files" 0 -> 1 for those two packages
Then MANIFEST.json is written again. The script stops when a package of the payload has no licence file and no
text here, when an input text has another SHA-256 than the one below, or when it ran already on this payload.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parent / "licence_texts"
CPYTHON_DOC = SRC / "cpython-3.12.15-Doc-license.rst"
BZIP2 = SRC / "bzip2-1.0.8-LICENSE"
PYOBJC = SRC / "pyobjc-core-12.2.2-License.txt"
INFI = SRC / "infi.systray-LICENSE"
PINNED_FILE = SRC / "SOURCES.json"  # URL and SHA-256 of each upstream text, fetched on 2026-11-12
SECTION = "Licenses and Acknowledgements for Incorporated Software"
OLD_RUNTIME_LINE = "Runtime (python-build-standalone, see python/LICENSE.txt):"
NEW_RUNTIME_LINE = ("Runtime (python-build-standalone). Licence texts: python/LICENSE.txt (CPython), "
                    "python/INCORPORATED_SOFTWARE.txt (OpenSSL, expat, libffi, zlib, libmpdec and the other code "
                    "that CPython incorporates), python/LICENSE.bzip2.txt (bzip2):")
LIBEDIT = "  libedit (macOS system library, not shipped): BSD-3-Clause"
NO_GPL = "No GPL, LGPL or AGPL component is shipped. pystray (LGPL-3.0) is not used."
NO_GPL_WIN = ("LGPL: two modules that come with dependencies are under the LGPL: adodbapi, a part of pywin32 "
              "(LGPL-2.1, licence text pywin32/full-set/licenses/adodbapi/license.txt), and autocommand, vendored in "
              "setuptools (LGPL-3.0, licence text setuptools/vendored/autocommand-2.2.2.dist-info/LICENSE). Shield's "
              "own code does not import them. No GPL or AGPL component is shipped. pystray (LGPL-3.0) is not used.")
GPL_WIN = ["adodbapi/license.txt", "pywin32-312.dist-info/licenses/adodbapi/license.txt",
           "setuptools/_vendor/autocommand-2.2.2.dist-info/LICENSE"]
GPL_TEXT = re.compile(r"GNU (LESSER |LIBRARY |AFFERO )?GENERAL PUBLIC LICENSE", re.I)
VENDORED_NOTE = ("{names}: the licence files of the libraries vendored in these packages (<package>/_vendor/) are in "
                 "<package>/vendored/, one folder per vendored library.")
FULLSET_NOTE = ("{names}: some licence files of the same package have the same file name, so the folder of the "
                "package keeps one file per name; <package>/full-set/ holds every licence file with its path in "
                "the package's dist-info folder.")
ADDED_NOTE = {
    "pyobjc-core": "pyobjc-core: its wheel has no licence file; pyobjc-core/License.txt is the licence file of the "
                   "PyObjC 12.2.2 source (pyobjc-core/License.txt), MIT.",
    "infi.systray": "infi.systray: its wheel has no licence file; infi.systray/LICENSE is the licence file of its "
                    "source repository (Infinidat/infi.systray), BSD-3-Clause.",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(p.parent, 0o755)
    p.write_text(text, encoding="utf-8", newline="\n")
    os.chmod(p, 0o644)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    payload, export = Path(argv[0]).resolve(), Path(argv[1]).resolve()
    lic = payload / "LICENSES"
    if not (lic / "THIRD_PARTY_LICENSES.txt").is_file() or not (payload / "MANIFEST.json").is_file():
        raise SystemExit(f"licence texts: {payload} is not a single-target payload (run before merge-macos)")
    windows = (payload / "bin" / "ragbase-shield.cmd").is_file()

    pins = json.loads(PINNED_FILE.read_text(encoding="utf-8"))
    for f in (CPYTHON_DOC, BZIP2, PYOBJC, INFI):
        if sha256(f) != pins[f.name]["sha256"]:
            raise SystemExit(f"licence texts: {f.name} differs from its SHA-256 in {PINNED_FILE.name}")

    sys.path.insert(0, str(export / "packaging" / "common"))
    import build_payload as bp  # noqa: E402
    import licenses as tag_licenses  # noqa: E402
    if bp.ROOT != export:
        raise SystemExit(f"licence texts: build_payload.py of {bp.ROOT}, not of {export}")
    site = payload / "runtime" / ("Lib" if windows else "lib/python3.12") / "site-packages"
    if not site.is_dir():
        raise SystemExit(f"licence texts: no site-packages in {payload}")

    table = (lic / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")
    if NEW_RUNTIME_LINE in table:
        raise SystemExit("licence texts: already added to this payload")
    if OLD_RUNTIME_LINE not in table:
        raise SystemExit("licence texts: unknown THIRD_PARTY_LICENSES.txt layout")

    # 1. CPython: the "Incorporated Software" section, as written.
    doc = CPYTHON_DOC.read_text(encoding="utf-8")
    start = doc.index(SECTION)
    head = ("Licences and acknowledgements of the software that CPython 3.12 incorporates.\n"
            "Source: CPython v3.12.15, Doc/license.rst, section \"" + SECTION + "\",\n"
            "https://github.com/python/cpython/blob/v3.12.15/Doc/license.rst (copied as written below).\n"
            "The CPython licence itself (PSF-2.0 and its history) is in LICENSE.txt in this folder.\n\n")
    write(lic / "python" / "INCORPORATED_SOFTWARE.txt", head + doc[start:])

    # 2. bzip2 (python-build-standalone builds it into the bz2 module), as written.
    write(lic / "python" / "LICENSE.bzip2.txt",
          "bzip2 and libbzip2 1.0.8: licence file of the bzip2 source (tag bzip2-1.0.8), copied as written.\n\n"
          + BZIP2.read_text(encoding="utf-8"))

    # 3. Packages without a licence file.
    rows = json.loads((lic / "licenses.json").read_text(encoding="utf-8"))
    added = []
    for r in rows:
        if r["files"]:
            continue
        if r["name"] == "pyobjc-core" and not windows:
            write(lic / "pyobjc-core" / "License.txt", PYOBJC.read_text(encoding="utf-8"))
            r["files"] = 1
            added.append(r["name"])
        elif r["name"] == "infi.systray" and windows:
            write(lic / "infi.systray" / "LICENSE", INFI.read_text(encoding="utf-8"))
            r["files"] = 1
            added.append(r["name"])
        else:
            raise SystemExit(f"licence texts: {r['name']} {r['version']} has no licence file and no text here")
    (lic / "licenses.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    os.chmod(lic / "licenses.json", 0o644)

    # 3b. Packages whose licence files share a name: the full set, with the dist-info paths.
    fullset = []
    for di in sorted(site.glob("*.dist-info")):
        meta = (di / "METADATA").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^Name: *(.+)$", meta, re.M)
        name = m.group(1).strip() if m else di.name.split("-")[0]
        files = sorted(p for p in di.rglob("*") if p.is_file()
                       and (tag_licenses.LICENSE_FILE.match(p.name) or "licenses" in p.parts))
        by = defaultdict(list)
        for f in files:
            by[f.name.lower()].append(f)
        if not any(len(v) > 1 for v in by.values()):
            continue
        dest = lic / re.sub(r"[^A-Za-z0-9_.-]", "_", name) / "full-set"
        seen = set()
        for f in files:
            rel = f.relative_to(di).as_posix()
            if rel.lower() in seen:
                raise SystemExit(f"licence texts: {name}: two files differ only by case: {rel}")
            seen.add(rel.lower())
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, out)
            os.chmod(out, 0o644)
        for d in [dest, *[p for p in dest.rglob("*") if p.is_dir()]]:
            os.chmod(d, 0o755)
        fullset.append(f"{name} ({len(files)} files)")

    # 3c. Libraries vendored inside a package (<package>/_vendor/<name>.dist-info): their licence files.
    vendored = defaultdict(int)
    for di in sorted(site.glob("*/_vendor/*.dist-info")):
        top = di.parent.parent.name
        files = sorted(p for p in di.rglob("*") if p.is_file()
                       and (tag_licenses.LICENSE_FILE.match(p.name) or "licenses" in p.parts))
        for f in files:
            out = lic / top / "vendored" / di.name / f.relative_to(di)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, out)
            os.chmod(out, 0o644)
            vendored[top] += 1
    for top in vendored:
        for d in [lic / top / "vendored", *[p for p in (lic / top / "vendored").rglob("*") if p.is_dir()]]:
            os.chmod(d, 0o755)

    # 3d. GPL family: the only known case is adodbapi (LGPL-2.1) in pywin32 on Windows.
    gpl = sorted(p.relative_to(site).as_posix() for p in site.rglob("*")
                 if p.is_file() and tag_licenses.LICENSE_FILE.match(p.name)
                 and GPL_TEXT.search(p.read_text(encoding="utf-8", errors="replace")[:4000]))
    expected = GPL_WIN if windows else []
    if gpl != expected:
        raise SystemExit(f"licence texts: GPL-family licence files {gpl}, expected {expected}")

    # 4. The table.
    table = table.replace(OLD_RUNTIME_LINE, NEW_RUNTIME_LINE)
    if windows:
        if LIBEDIT + "\n" not in table:
            raise SystemExit("licence texts: libedit line not found in the Windows table")
        table = table.replace(LIBEDIT + "\n", "")
    if windows:
        if NO_GPL not in table:
            raise SystemExit("licence texts: GPL sentence not found in the Windows table")
        table = table.replace(NO_GPL, NO_GPL_WIN)
    notes = [ADDED_NOTE[n] for n in added]
    if fullset:
        notes.append(FULLSET_NOTE.format(names=", ".join(fullset)))
    if vendored:
        notes.append(VENDORED_NOTE.format(names=", ".join(f"{k} ({v} files)" for k, v in sorted(vendored.items()))))
    if notes:
        table = table.rstrip("\n") + "\n" + "".join(n + "\n" for n in notes)
    write(lic / "THIRD_PARTY_LICENSES.txt", table)

    # 5. MANIFEST.json, with the build's own code.
    bp.write_manifest(payload)
    print(f"licence texts: {payload.name}: python/INCORPORATED_SOFTWARE.txt, python/LICENSE.bzip2.txt"
          + "".join(f", licence file of {n}" for n in added)
          + "".join(f", full set of {n}" for n in fullset)
          + "".join(f", vendored licences of {k} ({v} files)" for k, v in sorted(vendored.items()))
          + (", libedit line removed, LGPL sentence corrected (adodbapi, autocommand)" if windows else "")
          + "; MANIFEST.json written again")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
