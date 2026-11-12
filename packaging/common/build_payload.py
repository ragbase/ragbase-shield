"""Build one installer payload: private runtime + Shield + dependencies + launchers + licences + manifest.

Usage:
  python packaging/common/build_payload.py <target> <out_dir> [--wheel <ragbase_shield.whl>] [--icons <dir>] [--no-thin]
  python packaging/common/build_payload.py merge-macos <payload_x86_64> <payload_arm64> <out_dir>

<target>: macos-x86_64, macos-arm64 or windows-x64 (pins.json). Everything is installed at BUILD time with
uv (a build tool only, never shipped): binary wheels from the hashed lock files, the few pure-Python sdists
listed in pins.json "source_build_allowed", then the Shield wheel. The payload needs no pip and no network
on the user's machine.

Layout of a payload (DESIGN.md section 3.1, macOS):
  runtime/            python-build-standalone 3.12, trimmed, Shield in its site-packages
  extras/             empty; the optional NER packages go here ("ner install"), on extras.pth
  bin/ragbase-shield  terminal and MCP launcher
  icons/  LICENSES/  VERSION  install_info.json  uninstall.sh  MANIFEST.json
"merge-macos" makes the universal payload: runtime-x86_64/, runtime-arm64/, LICENSES-x86_64/,
LICENSES-arm64/ and the shared files; the postinstall script keeps the folders of the Mac's architecture.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PINS = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(HERE))

import fetch as _fetch  # noqa: E402
import licenses as _licenses  # noqa: E402
import prune_runtime as _prune  # noqa: E402

PYVER = "3.12"
LIPO_ARCH = {"macos-x86_64": "x86_64", "macos-arm64": "arm64"}

MAC_LAUNCHER = """#!/bin/sh
# RAGbase Shield launcher (desktop installer). Runs the private runtime of this install.
# Terminal:  "{{app}}/bin/ragbase-shield" doctor    MCP apps:  "{{app}}/bin/ragbase-shield" mcp
DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
# -I: isolated mode (= -E -s -P). -P keeps the current folder out of sys.path: "-m" would otherwise put it
# first, and an MCP app starts this launcher in the user's project folder (a planted json.py would run).
exec "$DIR/runtime/bin/python{pyver}" -I -X utf8 -m ragbase_shield "$@"
""".format(pyver=PYVER)

WIN_LAUNCHER = "@echo off\r\n" \
               "rem RAGbase Shield launcher (desktop installer). Runs the private runtime of this install.\r\n" \
               "\"%~dp0..\\runtime\\python.exe\" -I -X utf8 -m ragbase_shield %*\r\n"


def log(msg: str) -> None:
    print(f"payload: {msg}", file=sys.stderr, flush=True)


def run(cmd: list, **kw) -> None:
    log("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("payload: no version in pyproject.toml")
    return m.group(1)


def uv_exe() -> str:
    exe = os.environ.get("UV") or shutil.which("uv")
    if not exe:
        raise SystemExit("payload: uv not found (build tool). Install it: https://docs.astral.sh/uv/")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, check=True).stdout.split()
    have = tuple(int(x) for x in re.findall(r"\d+", out[1])[:3])
    need = tuple(int(x) for x in PINS["build_tools"]["uv_min_version"].split("."))
    if have < need:
        raise SystemExit(f"payload: uv {out[1]} is older than {PINS['build_tools']['uv_min_version']}")
    used = PINS["build_tools"].get("uv_used")
    if used and out[1] != used:
        log(f"warning: uv {out[1]} is not uv {used} of the recorded builds: MANIFEST.json may differ")
    return exe


def build_constraints() -> Path:
    """Hashed pins of the build backends (hatchling for the Shield wheel, setuptools and wheel for the sdists of
    pins.json "source_build_allowed"). Without them the WHEEL "Generator" line follows the newest release."""
    p = HERE / PINS["build_tools"].get("build_constraints", "build-constraints.txt")
    if not p.is_file():
        raise SystemExit(f"payload: missing {p} (run packaging/common/relock.sh)")
    return p


# Files that go into a payload: a change there that is not committed makes the build impossible to repeat.
SOURCE_PATHS = ["src", "pyproject.toml", "packaging", "LICENSE", "NOTICE", "integrations/assets"]


def source_id() -> str:
    """The commit of the build, with "+dirty" when a file of SOURCE_PATHS differs from it."""
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *SOURCE_PATHS],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit + ("+dirty" if dirty else "")


def build_time() -> str:
    """SOURCE_DATE_EPOCH, else the last commit time: two builds of one commit write the same value."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch:
        try:
            epoch = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct"], capture_output=True,
                                   text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            epoch = "0"
    return datetime.fromtimestamp(int(epoch or 0), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_wheel() -> Path:
    out = ROOT / "build" / "wheel"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("ragbase_shield-*.whl"):
        old.unlink()
    run([uv_exe(), "build", "--wheel", "--out-dir", out, "--build-constraints", build_constraints(), ROOT])
    wheels = sorted(out.glob("ragbase_shield-*.whl"))
    if not wheels:
        raise SystemExit("payload: wheel build failed")
    return wheels[-1]


def split_lock(lock: Path, work: Path) -> tuple[Path, Path]:
    """(binary-only lock, sdist-allowed lock) from one hashed lock file."""
    text = lock.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=[A-Za-z0-9])", text)
    allowed = {n.lower() for n in PINS["wheels"]["source_build_allowed"]}

    def name(b: str) -> str:
        return re.split(r"[=<>!~ ;\\\[]", b.strip(), maxsplit=1)[0].lower().replace("_", "-")

    reqs = [b for b in blocks if b.strip() and not b.lstrip().startswith("#")]
    binary = [b for b in reqs if name(b) not in allowed]
    source = [b for b in reqs if name(b) in allowed]
    work.mkdir(parents=True, exist_ok=True)
    pb, ps = work / "binary.lock", work / "source.lock"
    pb.write_text("\n".join(binary) + "\n", encoding="utf-8")
    ps.write_text("\n".join(source) + "\n", encoding="utf-8")
    return pb, (ps if source else Path())


def site_packages(runtime: Path, target: str) -> Path:
    if target.startswith("windows"):
        return runtime / "Lib" / "site-packages"
    return runtime / "lib" / f"python{PYVER}" / "site-packages"


def host_python(runtime: Path, target: str) -> str:
    """An interpreter uv can run here: the target runtime itself when it runs on this Mac, else this one."""
    cand = runtime / "bin" / f"python{PYVER}"
    if target.startswith("macos") and cand.is_file():
        try:
            if subprocess.run([str(cand), "-I", "-c", "print(1)"], capture_output=True).returncode == 0:
                return str(cand)
        except OSError:  # another CPU type (arm64 runtime on an Intel Mac)
            pass
    return sys.executable


def thin_macho(root: Path, arch: str) -> int:
    """lipo -thin every universal Mach-O to one architecture (each slice keeps its own signature)."""
    saved = 0
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        try:
            with open(p, "rb") as f:
                head = f.read(8)
        except OSError:
            continue
        if head[:4] not in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf") or int.from_bytes(head[4:8], "big") > 8:
            continue
        before = p.stat().st_size
        tmp = p.with_name(p.name + ".thin")
        r = subprocess.run(["lipo", str(p), "-thin", arch, "-output", str(tmp)], capture_output=True)
        if r.returncode == 0 and tmp.is_file():
            mode = p.stat().st_mode
            os.replace(tmp, p)
            os.chmod(p, mode)
            saved += before - p.stat().st_size
        else:
            tmp.unlink(missing_ok=True)
    return saved


def drop_removed_scripts_from_records(site: Path) -> None:
    """Drop the RECORD line of every file removed after the install: the console scripts of --target
    (site-packages/bin, Scripts: build folder in their shebang), direct_url.json (build folder of the Shield
    wheel), uv_cache.json (wheel build time), the pruned test folders. Those lines made two builds of one
    commit differ (review of 2026-10-27: two clean clones differed in RECORD and uv_cache.json only)."""
    for record in site.glob("*.dist-info/RECORD"):
        lines = record.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = []
        for ln in lines:
            row = next(csv.reader([ln]), [])
            rel = row[0].replace("\\", "/") if row else ""
            if rel and not (site / rel).exists():
                continue
            kept.append(ln)
        if len(kept) != len(lines):
            record.write_text("".join(kept), encoding="utf-8")


def manifest(root: Path) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if rel == "MANIFEST.json":
            continue
        if p.is_symlink():
            files[rel] = "link:" + os.readlink(p)
        elif p.is_file():
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"version": project_version(), "files": files, "count": len(files)}


def write_manifest(root: Path) -> None:
    (root / "MANIFEST.json").write_text(json.dumps(manifest(root), indent=1, sort_keys=True) + "\n", encoding="utf-8")


def du(p: Path) -> int:
    total = 0
    for f in p.rglob("*"):
        if f.is_file() and not f.is_symlink():
            total += f.stat().st_size
    return total


def build(target: str, out: Path, wheel: Path | None, icons: Path, thin: bool) -> None:
    if target not in PINS["python"]["targets"]:
        raise SystemExit(f"payload: unknown target {target}")
    version = project_version()
    windows = target.startswith("windows")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    runtime = out / "runtime"
    archive = _fetch.fetch(target)
    _fetch.extract(archive, runtime)
    site = site_packages(runtime, target)
    site.mkdir(parents=True, exist_ok=True)

    wheel = wheel or build_wheel()
    uv = uv_exe()
    triple = PINS["python"]["targets"][target]["triple"]
    lock = HERE / PINS["wheels"]["locks"][target]
    if not lock.is_file():
        raise SystemExit(f"payload: missing lock {lock} (run packaging/common/relock.sh)")
    work = ROOT / "build" / "work" / target
    binary_lock, source_lock = split_lock(lock, work)
    env = dict(os.environ)
    env.setdefault("UV_CACHE_DIR", str(ROOT / "build" / "cache" / "uv"))
    if target.startswith("macos"):
        env["MACOSX_DEPLOYMENT_TARGET"] = PINS["macos"]["min_version"]
    common = ["pip", "install", "--target", site, "--python", host_python(runtime, target),
              "--python-version", PYVER, "--python-platform", triple, "--no-deps", "--quiet"]
    run([uv, *common, "--only-binary", ":all:", "--require-hashes", "-r", binary_lock], env=env)
    if source_lock != Path() and source_lock.is_file():
        run([uv, *common, "--require-hashes", "-r", source_lock, "--build-constraints", build_constraints()], env=env)
    run([uv, *common, "--only-binary", ":all:", wheel], env=env)

    removed = _prune.prune(runtime, "windows" if windows else "posix", site)
    log(f"pruned {removed / 1e6:.1f} MB")
    drop_removed_scripts_from_records(site)
    if thin and target in LIPO_ARCH and PINS["macos"].get("thin_universal_binaries", True):
        log(f"thinned universal binaries: {thin_macho(runtime, LIPO_ARCH[target]) / 1e6:.1f} MB saved")

    # extras.pth: <app>/extras holds the optional NER packages, outside runtime/ (kept across updates)
    rel = "..\\..\\..\\extras" if windows else "../../../../extras"
    (site / "ragbase_shield_extras.pth").write_text(rel + "\n", encoding="utf-8")
    (out / "extras").mkdir()
    (out / "extras" / "README.txt").write_text(
        "Optional packages (name recognition, NER) installed by \"ragbase-shield ner install\".\n"
        "Kept when RAGbase Shield is updated.\n", encoding="utf-8")

    # launchers
    (out / "bin").mkdir()
    if windows:
        (out / "bin" / "ragbase-shield.cmd").write_bytes(WIN_LAUNCHER.encode("ascii"))
        shutil.copy2(runtime / "pythonw.exe", runtime / "RAGbase Shield.exe")  # process name of the service
    else:
        launcher = out / "bin" / "ragbase-shield"
        launcher.write_text(MAC_LAUNCHER, encoding="utf-8")
        os.chmod(launcher, 0o755)

    # icons, licences, metadata, uninstaller
    (out / "icons").mkdir()
    for name in ("shield_template.png", "shield.ico", "shield.icns", "shield-512.png"):
        if (icons / name).is_file():
            shutil.copy2(icons / name, out / "icons" / name)
    rows = _licenses.collect(site, out / "LICENSES")
    lic_problems = _licenses.check(rows)
    _licenses.write_tables(rows, out / "LICENSES", runtime, ROOT / "build" / f"licenses-{target}.md")
    for f in ("LICENSE", "NOTICE"):
        if (ROOT / f).is_file():
            (out / "LICENSES" / "ragbase-shield").mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, out / "LICENSES" / "ragbase-shield" / f)
    if lic_problems:
        raise SystemExit("payload: licence check failed: " + "; ".join(lic_problems))
    (out / "VERSION").write_text(version + "\n", encoding="utf-8")
    info = {"version": version, "target": target, "python": PINS["python"]["version"],
            "python_release": PINS["python"]["release_tag"], "built_at": build_time(), "source": source_id()}
    if windows:
        ns = uuid.UUID(PINS["windows"]["shield_ns"])
        info["product_code"] = "{" + str(uuid.uuid5(ns, "ragbase-shield-win64-" + version)).upper() + "}"
        info["upgrade_code"] = "{" + PINS["windows"]["upgrade_code"].upper() + "}"
    (out / "install_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    if windows:
        src = ROOT / "packaging" / "windows" / "uninstall.cmd"
        if src.is_file():
            shutil.copy2(src, out / "uninstall.cmd")
    else:
        src = ROOT / "packaging" / "macos" / "uninstall.sh"
        shutil.copy2(src, out / "uninstall.sh")
        os.chmod(out / "uninstall.sh", 0o755)
    write_manifest(out)
    log(f"{target}: {du(out) / 1e6:.1f} MB in {sum(1 for _ in out.rglob('*'))} entries -> {out}")


def merge_macos(x86: Path, arm: Path, out: Path) -> None:
    """Universal payload: both runtimes and licence trees, one copy of the shared files."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for arch, src in (("x86_64", x86), ("arm64", arm)):
        shutil.copytree(src / "runtime", out / f"runtime-{arch}", symlinks=True)
        shutil.copytree(src / "LICENSES", out / f"LICENSES-{arch}", symlinks=True)
    for name in ("bin", "icons", "extras"):
        shutil.copytree(x86 / name, out / name, symlinks=True)
    for name in ("VERSION", "uninstall.sh"):
        shutil.copy2(x86 / name, out / name)
    info = json.loads((x86 / "install_info.json").read_text(encoding="utf-8"))
    info["target"] = "macos-universal"
    (out / "install_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    write_manifest(out)
    log(f"macos-universal: {du(out) / 1e6:.1f} MB -> {out}")


def main(argv: list[str]) -> int:
    if argv[:1] == ["merge-macos"] and len(argv) == 4:
        merge_macos(Path(argv[1]), Path(argv[2]), Path(argv[3]))
        return 0
    args, opts, it = [], {}, iter(argv)
    for a in it:
        if a in ("--wheel", "--icons"):
            opts[a] = Path(next(it))
        elif a == "--no-thin":
            opts[a] = True
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    build(args[0], Path(args[1]).resolve(), opts.get("--wheel"), opts.get("--icons", ROOT / "build" / "icons"),
          thin=not opts.get("--no-thin", False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
