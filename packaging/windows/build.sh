#!/bin/sh
# Build the RAGbase Shield Windows installer (per-user .msi, no administrator) -> dist/RAGbase-Shield-<v>-win64.msi
#
# Usage (on a Mac or Linux build machine, from anywhere):
#   packaging/windows/build.sh                        payload + build folder of the pyproject.toml version
#   packaging/windows/build.sh --msi-version 0.3.2    same payload, higher MSI version (upgrade test)
#   packaging/windows/build.sh --reuse-payload        skip icons, wheel and build_payload.py
#   packaging/windows/build.sh --local-only           same as the default (kept for old scripts)
#
# Steps here: icons, wheel, build_payload.py windows-x64 (private Python 3.12 + Shield, pinned by hash),
# stage_payload.py (MSI version, ProductCode, uninstall.cmd), check_payload.py, gen_components.py, a deterministic
# payload.zip. The result is the folder build/windows/msi-<v>/. The .msi itself is built by WiX on a Windows
# machine: copy that folder to C:\shield_pkg\b-<v> there and run build_msi.ps1 (user-level .NET SDK + pinned WiX,
# wix build, wix msi validate); see packaging/README.md. The .msi is unsigned (TODO_SIGNING.md).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
MSIV=""
REUSE=0
LOCAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --msi-version) MSIV="$2"; shift 2 ;;
    --reuse-payload) REUSE=1; shift ;;
    --local-only) LOCAL=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

PY=""
for cand in "$ROOT/.venv/bin/python" "${SHIELD_BUILD_PYTHON:-}" python3; do
  [ -n "$cand" ] || continue
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys, PIL; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
command -v uv >/dev/null 2>&1 || { echo "Need uv (build tool)." >&2; exit 1; }
if [ -z "$PY" ]; then
  # Same build-only venv as packaging/macos/build.sh: Pillow for the icons only, never shipped.
  TV="$ROOT/build/tools-venv"
  [ -x "$TV/bin/python" ] || uv venv -q --python ">=3.11" "$TV"
  uv pip install -q --python "$TV/bin/python" "pillow==13.0.0" && PY="$TV/bin/python"
fi
[ -n "$PY" ] || { echo "Need Python 3.11+ with Pillow to build." >&2; exit 1; }

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -n 1)"
MSIV="${MSIV:-$VERSION}"
B="$ROOT/build/windows"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 && \
   [ -n "$(git -C "$ROOT" status --porcelain -- src pyproject.toml packaging LICENSE NOTICE integrations/assets)" ]; then
  echo "WARNING: src/, pyproject.toml or packaging/ differ from commit $(git -C "$ROOT" rev-parse --short HEAD)." >&2
  echo "WARNING: this .msi cannot be rebuilt from git (install_info.json says +dirty). Commit first for a release." >&2
fi
mkdir -p "$B/logs" "$ROOT/dist"
LOCK="$ROOT/build/.build-lock"
mkdir "$LOCK" 2>/dev/null || { echo "Another build runs in this checkout ($LOCK exists; remove it if none runs)." >&2; exit 1; }
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
cd "$ROOT"

if [ "$REUSE" = 0 ]; then
  "$PY" packaging/common/make_tray_icons.py "$ROOT/build/icons"
  rm -f "$ROOT"/build/wheel/ragbase_shield-*.whl
  uv build --wheel --out-dir "$ROOT/build/wheel" --build-constraints "$ROOT/packaging/common/build-constraints.txt" "$ROOT"
  WHEEL="$(ls "$ROOT"/build/wheel/ragbase_shield-"$VERSION"-*.whl | head -n 1)"
  "$PY" packaging/common/build_payload.py windows-x64 "$B/payload" --wheel "$WHEEL" --icons "$ROOT/build/icons"
fi
[ -d "$B/payload" ] || { echo "Missing $B/payload (run without --reuse-payload)." >&2; exit 1; }
PV="$(head -n 1 "$B/payload/VERSION" 2>/dev/null || true)"
[ "$PV" = "$VERSION" ] || { echo "$B/payload holds version '$PV' but pyproject.toml says $VERSION." >&2; exit 1; }

S="$B/stage-$MSIV"
"$PY" -I packaging/windows/stage_payload.py "$B/payload" "$S" --msi-version "$MSIV"
"$PY" packaging/common/check_payload.py "$S"
M="$B/msi-$MSIV"
rm -rf "$M"
mkdir -p "$M"
"$PY" -I packaging/windows/gen_components.py "$S" "$M/Components.wxs"
cp "$HERE/Package.wxs" "$HERE/build_msi.ps1" "$M/"
cp "$S.msi_vars.json" "$M/msi_vars.json"
# Deterministic zip: sorted entries, the commit time on every entry, no macOS extended attributes.
EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || echo 315532800)}"
"$PY" -I - "$S" "$M/payload.zip" "$EPOCH" <<'PYEOF'
import os, sys, time, zipfile
src, dest, epoch = sys.argv[1], sys.argv[2], max(int(sys.argv[3]), 315532800)
stamp = time.gmtime(epoch)[:6]
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            p = os.path.join(root, name)
            info = zipfile.ZipInfo(os.path.relpath(p, src).replace(os.sep, "/"), stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(p, "rb") as f:
                z.writestr(info, f.read())
PYEOF
(cd "$M" && shasum -a 256 payload.zip > payload.sha256)
ls -l "$M"
echo "Local steps done: $M"
echo "Next, on a Windows machine: copy $M to C:\\shield_pkg\\b-$MSIV, then run"
echo "  powershell -NoProfile -ExecutionPolicy Bypass -File C:\\shield_pkg\\b-$MSIV\\build_msi.ps1 -Dir C:\\shield_pkg\\b-$MSIV"
echo "and copy out\\RAGbase-Shield-$MSIV-win64.msi back to dist/ (packaging/README.md, section Build)."
[ "$LOCAL" = 1 ] || true
