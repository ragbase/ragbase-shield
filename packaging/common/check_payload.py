"""Checks on a built payload before it is packed. Exit 1 on the first class of failure.

Usage:
  python -I packaging/common/check_payload.py <payload_dir> [<payload_dir> ...]

Checks: licence fields (no GPL, LGPL, AGPL, no missing licence), no build-machine path (/Users/<builder>,
C:\\Users\\<builder>, the repo folder, the payload folder) in text files, no Tcl/Tk, no scripts folder with
absolute shebangs in site-packages, no direct_url.json or uv_cache.json and no RECORD line for a missing file
(both made two builds of one commit differ), MANIFEST.json equal to the tree, no em or en dash in our own text
files. Prints the sizes.
"""
from __future__ import annotations

import csv
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_payload as _bp  # noqa: E402
import licenses as _licenses  # noqa: E402

TEXT_SUFFIXES = {".py", ".pth", ".txt", ".json", ".cfg", ".toml", ".sh", ".cmd", ".md", ".html", ".typed", ""}
OUR_FILES = {"VERSION", "install_info.json", "uninstall.sh", "uninstall.cmd", "ragbase-shield", "ragbase-shield.cmd",
             "README.txt", "ragbase_shield_extras.pth"}


def sites(payload: Path) -> list[Path]:
    out = []
    for rt in [payload / "runtime", *sorted(payload.glob("runtime-*"))]:
        out += [p for p in (rt / "lib").glob("python3*/site-packages")] if (rt / "lib").is_dir() else []
        if (rt / "Lib" / "site-packages").is_dir():
            out.append(rt / "Lib" / "site-packages")
    return out


def check(payload: Path) -> list[str]:
    problems: list[str] = []
    user = getpass.getuser()
    needles = [f"/Users/{user}/".encode(), f"C:\\Users\\{user}\\".encode(), f"C:/Users/{user}/".encode(),
               str(_bp.ROOT).encode(), str(payload.resolve()).encode()]  # builds outside /Users too
    for site in sites(payload):
        with tempfile.TemporaryDirectory() as td:
            rows = _licenses.collect(site, Path(td))
        problems += [f"licence: {p}" for p in _licenses.check(rows)]
        for d in ("bin", "Scripts"):
            if (site / d).exists():
                problems.append(f"site-packages/{d} present in {site} (absolute shebangs)")
        if not any(site.glob("ragbase_shield/__init__.py")):
            problems.append(f"ragbase_shield missing in {site}")
        # Reproducibility: no install record that holds the build folder or the build time, and every RECORD
        # line names a file that ships (build_payload.drop_removed_scripts_from_records).
        for junk in ("direct_url.json", "uv_cache.json"):
            problems += [f"{p.relative_to(payload)} left (build folder or build time)"
                         for p in site.glob(f"*.dist-info/{junk}")]
        for record in site.glob("*.dist-info/RECORD"):
            for ln in record.read_text(encoding="utf-8").splitlines():
                row = next(csv.reader([ln]), [])
                rel = row[0].replace("\\", "/") if row else ""
                if rel and not (site / rel).exists():
                    problems.append(f"{record.relative_to(payload)} names a missing file: {rel}")
                    break
    posix_payload = not (payload / "bin" / "ragbase-shield.cmd").exists()
    for p in payload.rglob("*"):
        name = p.name.lower()
        if p.is_dir() and (name.startswith("tcl") or name.startswith("tk8") or name.startswith("tk9")
                           or name in ("tkinter", "idlelib")):
            problems.append(f"tcl/tk left: {p.relative_to(payload)}")
        # Security: nothing another account could change, no setuid or setgid bit, no link out of the payload
        # (uv leaves a world-writable site-packages/.lock: pruned by pins.json).
        mode = p.lstat().st_mode if posix_payload else 0  # POSIX modes mean nothing in the Windows MSI
        if not p.is_symlink() and mode & 0o022:
            problems.append(f"group or world writable: {p.relative_to(payload)} ({oct(mode & 0o7777)})")
        if mode & 0o6000:
            problems.append(f"setuid or setgid bit: {p.relative_to(payload)}")
        if p.is_symlink():
            target = os.readlink(p)
            if os.path.isabs(target) or not (p.parent / target).resolve().is_relative_to(payload.resolve()):
                problems.append(f"link out of the payload: {p.relative_to(payload)} -> {target}")
        if not p.is_file() or p.is_symlink():
            continue
        if p.suffix.lower() in TEXT_SUFFIXES and p.stat().st_size < 4_000_000:
            data = p.read_bytes()
            if any(n in data for n in needles):
                problems.append(f"build path inside {p.relative_to(payload)}")
            if p.name in OUR_FILES and ("\u2014".encode() in data or "\u2013".encode() in data):
                problems.append(f"em or en dash in {p.relative_to(payload)}")
    try:
        recorded = json.loads((payload / "MANIFEST.json").read_text(encoding="utf-8"))
        now = _bp.manifest(payload)
        if recorded.get("files") != now["files"]:
            diff = set(recorded.get("files", {}).items()) ^ set(now["files"].items())
            problems.append(f"MANIFEST.json differs from the tree ({len(diff)} entries)")
    except (OSError, ValueError):
        problems.append("MANIFEST.json missing or invalid")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    bad = 0
    for arg in argv:
        payload = Path(arg)
        problems = check(payload)
        size = _bp.du(payload)
        n = sum(1 for p in payload.rglob("*") if p.is_file())
        parts = {p.name: _bp.du(p) for p in payload.iterdir() if p.is_dir()}
        print(f"check: {payload}: {size / 1e6:.1f} MB, {n} files; " +
              ", ".join(f"{k} {v / 1e6:.1f} MB" for k, v in sorted(parts.items())))
        for prob in problems:
            print(f"check: FAIL {prob}")
        bad += len(problems)
    print("check: " + ("OK" if not bad else f"{bad} problem(s)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
