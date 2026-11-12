"""Remove what Shield never uses from an extracted runtime (pins.json "prune").

Usage:
  python -I packaging/common/prune_runtime.py <runtime_dir> <posix|windows> [<site_packages_dir>]

Removes Tcl/Tk, IDLE, the test suite, headers, build-time scripts with absolute shebangs, and every
__pycache__. Keeps ensurepip and pip (the optional NER extra uses pip). Prints the removed size.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _size(p: Path) -> int:
    if p.is_symlink() or p.is_file():
        try:
            return p.lstat().st_size
        except OSError:
            return 0
    return sum(_size(c) for c in p.iterdir()) if p.is_dir() else 0


def _remove(p: Path) -> int:
    n = _size(p)
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    elif p.exists() or p.is_symlink():
        p.unlink()
    return n


def prune(runtime: Path, flavour: str, site: Path | None = None) -> int:
    pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
    removed = 0
    for pattern in pins["prune"][flavour]:
        for p in sorted(runtime.glob(pattern), reverse=True):
            removed += _remove(p)
    if site is not None and site.is_dir():
        for pattern in pins["prune"]["site_packages"]:
            for p in sorted(site.glob(pattern), reverse=True):
                removed += _remove(p)
    for p in sorted(runtime.rglob("__pycache__"), reverse=True):
        removed += _remove(p)
    return removed


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[1] not in ("posix", "windows"):
        print(__doc__, file=sys.stderr)
        return 2
    site = Path(argv[2]) if len(argv) == 3 else None
    n = prune(Path(argv[0]), argv[1], site)
    print(f"prune: removed {n / 1e6:.1f} MB", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
