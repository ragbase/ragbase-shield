"""Stage a Windows payload for one .msi: MSI version, ProductCode, uninstall.cmd, MANIFEST.json, msi_vars.json.

Usage:
  python -I packaging/windows/stage_payload.py <payload> <staged_dir> [--msi-version X.Y.Z]

<payload> is the output of packaging/common/build_payload.py windows-x64 (not changed). <staged_dir> is created
fresh: a copy of the payload where
- install_info.json gets "msi_version" and the "product_code" of that MSI version
  (ProductCode = uuid5(shield_ns, "ragbase-shield-win64-" + msi_version), pins.json "product_code_rule");
  the tray's "Désinstaller..." runs "msiexec /x <product_code>", so it must name the MSI really installed;
- uninstall.cmd gets the same ProductCode;
- MANIFEST.json is written again (the reproducibility unit).
It also writes <staged_dir>.msi_vars.json: the "wix build -d" values (Version, ProductCode, UpgradeCode,
ShortcutGuid) for build_msi.ps1.

--msi-version defaults to the payload VERSION (the Shield version in pyproject.toml). Windows Installer compares
only the first three fields, so an upgrade test uses a higher third field (0.3.1 -> 0.3.2), never a fourth one.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))

import build_payload as _bp  # noqa: E402

PINS = _bp.PINS
NS = uuid.UUID(PINS["windows"]["shield_ns"])
PLACEHOLDER = "__PRODUCT_CODE__"


def product_code(msi_version: str) -> str:
    return "{" + str(uuid.uuid5(NS, "ragbase-shield-win64-" + msi_version)).upper() + "}"


def shortcut_guid() -> str:
    return "{" + str(uuid.uuid5(NS, "start-menu-shortcut")).upper() + "}"


def msi_version_ok(v: str) -> bool:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    return bool(m) and int(m.group(1)) < 256 and int(m.group(2)) < 256 and int(m.group(3)) < 65536


def stage(payload: Path, staged: Path, msi_version: str | None) -> dict:
    version = (payload / "VERSION").read_text(encoding="utf-8").strip()
    msi_version = msi_version or version
    if not msi_version_ok(msi_version):
        raise SystemExit(f"stage: MSI version must be X.Y.Z with X, Y < 256 and Z < 65536 (got {msi_version!r})")
    if not (payload / "runtime" / "RAGbase Shield.exe").is_file():
        raise SystemExit(f"stage: {payload} is not a Windows payload")
    if staged.exists():
        shutil.rmtree(staged)
    shutil.copytree(payload, staged)
    code = product_code(msi_version)
    upgrade = "{" + PINS["windows"]["upgrade_code"].upper() + "}"
    info_path = staged / "install_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("target") != "windows-x64":
        raise SystemExit("stage: install_info.json is not a windows-x64 one")
    info["msi_version"] = msi_version
    info["product_code"] = code
    info["upgrade_code"] = upgrade
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    unc = staged / "uninstall.cmd"
    if not unc.is_file():
        raise SystemExit("stage: uninstall.cmd missing from the payload (packaging/windows/uninstall.cmd)")
    text = unc.read_bytes().decode("ascii")
    if PLACEHOLDER not in text:
        raise SystemExit("stage: uninstall.cmd has no " + PLACEHOLDER)
    unc.write_bytes(text.replace(PLACEHOLDER, code).encode("ascii"))
    _bp.write_manifest(staged)
    msi_vars = {"Version": msi_version, "ProductCode": code, "UpgradeCode": upgrade, "ShortcutGuid": shortcut_guid(),
                "ShieldVersion": version, "Source": info.get("source", "unknown")}
    Path(str(staged) + ".msi_vars.json").write_text(json.dumps(msi_vars, indent=2) + "\n", encoding="utf-8")
    return msi_vars


def main(argv: list[str]) -> int:
    args, msi_version, it = [], None, iter(argv)
    for a in it:
        if a == "--msi-version":
            msi_version = next(it, None)
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    v = stage(Path(args[0]).resolve(), Path(args[1]).resolve(), msi_version)
    print(f"stage: MSI {v['Version']} (Shield {v['ShieldVersion']}), ProductCode {v['ProductCode']} -> {args[1]}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
