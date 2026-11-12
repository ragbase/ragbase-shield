"""Licence tree and table of a payload. Fails on GPL, LGPL, AGPL or a package without a licence.

Usage:
  python -I packaging/common/licenses.py <site_packages> <licenses_out_dir> [--runtime <runtime_dir>] [--markdown <file>]

Writes <licenses_out_dir>/<package>/<licence files>, <licenses_out_dir>/python/LICENSE.txt (CPython and the
libraries built into python-build-standalone), THIRD_PARTY_LICENSES.txt and licenses.json. The clean-room
rule (ARCHITECTURE.md section 7) forbids GPL, LGPL and AGPL code; MPL-2.0 is accepted for data only and
listed (certifi, when present).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from email.parser import HeaderParser
from pathlib import Path

FORBIDDEN = re.compile(r"\b(A?GPL|LGPL|GNU (Lesser |Affero )?General Public)", re.I)
MPL_OK = {"certifi"}  # data only (CA bundle), unused at run time
LICENSE_FILE = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.I)

# Libraries built into the python-build-standalone runtime (its own licence file covers them).
RUNTIME_PARTS = [
    ("CPython 3.12", "PSF-2.0"),
    ("OpenSSL 3", "Apache-2.0"),
    ("libffi", "MIT"),
    ("SQLite", "Public domain"),
    ("zlib", "Zlib"),
    ("bzip2", "bzip2-1.0.6 (BSD-like)"),
    ("xz / liblzma", "0BSD"),
    ("expat", "MIT"),
    ("mpdecimal", "BSD-2-Clause"),
    ("libedit (macOS system library, not shipped)", "BSD-3-Clause"),
]


def _licence_of(meta) -> str:
    expr = (meta.get("License-Expression") or "").strip()
    if expr:
        return expr
    lic = (meta.get("License") or "").strip()
    first = lic.splitlines()[0].strip() if lic else ""
    if first and len(first) <= 80 and first.upper() not in ("UNKNOWN", "NONE"):
        return first
    classes = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    classes = [c for c in classes if c and c != "OSI Approved"]
    if classes:
        return " / ".join(dict.fromkeys(classes))
    return first


def collect(site: Path, out: Path) -> list[dict]:
    rows = []
    out.mkdir(parents=True, exist_ok=True)
    for di in sorted(site.glob("*.dist-info")):
        meta_path = di / "METADATA"
        if not meta_path.is_file():
            continue
        meta = HeaderParser().parsestr(meta_path.read_text(encoding="utf-8", errors="replace"))
        name = meta.get("Name", di.name.split("-")[0])
        version = meta.get("Version", "")
        lic = _licence_of(meta)
        files = [p for p in di.rglob("*") if p.is_file() and (LICENSE_FILE.match(p.name) or "licenses" in p.parts)]
        dest = out / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        if files:
            dest.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, dest / f.name)
        rows.append({"name": name, "version": version, "license": lic, "files": len(files)})
    return rows


def check(rows: list[dict]) -> list[str]:
    problems = []
    for r in rows:
        if not r["license"]:
            problems.append(f"{r['name']} {r['version']}: no licence field")
        elif FORBIDDEN.search(r["license"]):
            problems.append(f"{r['name']} {r['version']}: forbidden licence ({r['license']})")
        elif "MPL" in r["license"].upper() and r["name"].lower() not in MPL_OK:
            problems.append(f"{r['name']} {r['version']}: MPL licence outside the allow-list ({r['license']})")
    return problems


def write_tables(rows: list[dict], out: Path, runtime: Path | None, markdown: Path | None) -> None:
    if runtime is not None:
        cands = list(runtime.glob("lib/python3*/LICENSE.txt")) + list(runtime.glob("LICENSE.txt"))
        if cands:
            (out / "python").mkdir(parents=True, exist_ok=True)
            shutil.copy2(cands[0], out / "python" / "LICENSE.txt")
    lines = ["RAGbase Shield desktop installer: third-party components", "",
             "Runtime (python-build-standalone, see python/LICENSE.txt):"]
    lines += [f"  {n}: {lic}" for n, lic in RUNTIME_PARTS]
    lines += ["", "Python packages (licence files in the folder of the same name):"]
    width = max((len(r["name"]) for r in rows), default=10) + 2
    lines += [f"  {r['name'] + ' ' + r['version']:<{width + 12}} {r['license']}" for r in rows]
    lines += ["", "No GPL, LGPL or AGPL component is shipped. pystray (LGPL-3.0) is not used.", ""]
    (out / "THIRD_PARTY_LICENSES.txt").write_text("\n".join(lines), encoding="utf-8")
    (out / "licenses.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    if markdown is not None:
        md = ["| Package | Version | Licence |", "|---|---|---|"]
        md += [f"| {r['name']} | {r['version']} | {r['license']} |" for r in rows]
        markdown.write_text("\n".join(md) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    args, opts, it = [], {}, iter(argv)
    for a in it:
        if a in ("--runtime", "--markdown"):
            opts[a] = Path(next(it))
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    site, out = Path(args[0]), Path(args[1])
    rows = collect(site, out)
    problems = check(rows)
    write_tables(rows, out, opts.get("--runtime"), opts.get("--markdown"))
    for p in problems:
        print(f"licenses: FAIL {p}", file=sys.stderr)
    print(f"licenses: {len(rows)} packages, {len(problems)} problem(s)", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
