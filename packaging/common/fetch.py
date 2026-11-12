"""Download one pinned python-build-standalone runtime, check its SHA-256, extract it.

Usage:
  python -I packaging/common/fetch.py <target> <dest_dir> [--repin]

<target> is a key of pins.json "python.targets" (macos-x86_64, macos-arm64, windows-x64). The archive is kept
in its own empty folder under build/cache/pbs/<name>/ and reused when its hash matches. <dest_dir> is created
fresh and receives the content of the archive's top "python/" folder. A hash that differs from pins.json
stops the build, unless --repin is given (then pins.json is updated and the change shows in git diff).
No code from the archive is run here.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PINS = HERE / "pins.json"
CACHE = ROOT / "build" / "cache" / "pbs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(target: str, repin: bool = False) -> Path:
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    py = pins["python"]
    t = py["targets"][target]
    name = t["file"]
    folder = CACHE / name.removesuffix(".tar.gz")
    archive = folder / name
    if not archive.is_file():
        folder.mkdir(parents=True, exist_ok=True)
        url = py["base_url"] + name.replace("+", "%2B")
        print(f"fetch: downloading {name}", file=sys.stderr)
        tmp = archive.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as out:  # noqa: S310 - pinned URL
            shutil.copyfileobj(r, out)
        tmp.replace(archive)
    got = sha256(archive)
    if got != t["sha256"]:
        if not repin:
            raise SystemExit(f"fetch: SHA-256 mismatch for {name}: got {got}, pinned {t['sha256']} "
                             "(use --repin only after checking the new release)")
        t["sha256"] = got
        t["size"] = archive.stat().st_size
        PINS.write_text(json.dumps(pins, indent=2) + "\n", encoding="utf-8")
        print(f"fetch: repinned {name}", file=sys.stderr)
    return archive


def _safe_members(tf: tarfile.TarFile, prefix: str = "python/"):
    for m in tf.getmembers():
        name = m.name
        if not name.startswith(prefix) or ".." in Path(name).parts or name.startswith("/"):
            continue
        if (m.issym() or m.islnk()) and Path(m.linkname).is_absolute():
            continue  # the "tar" extraction filter also refuses links that leave dest
        m.name = name[len(prefix):]
        if m.islnk() and m.linkname.startswith(prefix):  # hard links name a path from the archive root
            m.linkname = m.linkname[len(prefix):]
        if not m.name:
            continue
        yield m


def extract(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as tf:
        members = list(_safe_members(tf))
        try:
            tf.extractall(dest, members=members, filter="tar")
        except TypeError:  # Python without extraction filters
            tf.extractall(dest, members=members)  # noqa: S202 - members filtered above


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    archive = fetch(args[0], repin="--repin" in argv)
    extract(archive, Path(args[1]))
    print(f"fetch: {args[0]} -> {args[1]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
