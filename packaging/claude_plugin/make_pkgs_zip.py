"""Build ``engine/pkgs.zip`` and ``engine/pkgs.id`` of the Windows plugin for the Claude app.

    python make_pkgs_zip.py <packages folder> <engine folder>

Every file of the packages folder goes into ONE deflate archive (sorted names, fixed dates and modes, so the same
files always give the same archive). ``pkgs.id`` holds the first 12 hex characters of the archive's SHA-256: the
start module (``shield_boot``) uses it to name its cache folder and never hashes the archive itself.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

DATE = (2026, 1, 1, 0, 0, 0)


def build(packages: Path, engine: Path) -> tuple:
    files = sorted((p for p in packages.rglob("*") if p.is_file()), key=lambda p: p.relative_to(packages).as_posix())
    if not files:
        raise SystemExit("no file to pack")
    archive = engine / "pkgs.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            name = p.relative_to(packages).as_posix()
            if name.startswith("/") or ".." in name.split("/") or ":" in name:
                raise SystemExit(f"bad name {name}")
            info = zipfile.ZipInfo(name, DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 0
            z.writestr(info, p.read_bytes(), compresslevel=9)
    ident = hashlib.sha256(archive.read_bytes()).hexdigest()[:12]
    (engine / "pkgs.id").write_text(ident + "\n", encoding="ascii", newline="\n")
    return archive, ident, len(files)


if __name__ == "__main__":
    a, i, n = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"{a}: {n} files, id {i}")
