#!/bin/sh
# Build the RAGbase Shield macOS installer (.pkg, home domain, no administrator password).
#
# Usage (from anywhere, on a Mac with Xcode command line tools and uv):
#   packaging/macos/build.sh                      universal package -> dist/RAGbase-Shield-<version>.pkg
#   packaging/macos/build.sh --arch x86_64        Intel only        -> dist/RAGbase-Shield-<version>-x86_64.pkg
#   packaging/macos/build.sh --arch arm64         Apple Silicon only -> dist/RAGbase-Shield-<version>-arm64.pkg
#   packaging/macos/build.sh --reuse-payload      skip the payload build (reuse build/macos/payload-*)
#
# Steps: icons, wheel, payload per architecture (build_payload.py), universal merge, checks, pkgbuild,
# productbuild, SHA-256. Network is needed once (python-build-standalone and wheels, all pinned by hash in
# packaging/common/pins.json and requirements-*.lock); later builds use build/cache. Unsigned: see
# packaging/macos/TODO_SIGNING.md.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
ARCH=universal
REUSE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --arch) ARCH="$2"; shift 2 ;;
    --reuse-payload) REUSE=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$ARCH" in universal|x86_64|arm64) ;; *) echo "--arch must be universal, x86_64 or arm64" >&2; exit 2 ;; esac

PY=""
for cand in "$ROOT/.venv/bin/python" python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys, PIL; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
command -v uv >/dev/null 2>&1 || { echo "Need uv (build tool)." >&2; exit 1; }
if [ -z "$PY" ]; then
  # Clean checkout without the repo .venv: a build-only venv with the pinned Pillow (icons only, never shipped;
  # 13.0.0 = the repo .venv of 2026-10-27, so the icons keep the same bytes).
  TV="$ROOT/build/tools-venv"
  [ -x "$TV/bin/python" ] || uv venv -q --python ">=3.11" "$TV"
  uv pip install -q --python "$TV/bin/python" "pillow==13.0.0" && PY="$TV/bin/python"
fi
[ -n "$PY" ] || { echo "Need Python 3.11+ with Pillow (the repo .venv) to build." >&2; exit 1; }

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -n 1)"
B="$ROOT/build/macos"
# A package built from files that differ from the commit cannot be rebuilt later (same list as SOURCE_PATHS
# in build_payload.py; install_info.json records "<commit>+dirty").
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 && \
   [ -n "$(git -C "$ROOT" status --porcelain -- src pyproject.toml packaging LICENSE NOTICE integrations/assets)" ]; then
  echo "WARNING: src/, pyproject.toml or packaging/ differ from commit $(git -C "$ROOT" rev-parse --short HEAD)." >&2
  echo "WARNING: this package cannot be rebuilt from git. Commit first for a release build." >&2
fi
mkdir -p "$B" "$ROOT/dist"
# One build at a time per checkout: build/macos, build/wheel and dist/ have fixed names.
LOCK="$ROOT/build/.build-lock"
mkdir "$LOCK" 2>/dev/null || { echo "Another build runs in this checkout ($LOCK exists; remove it if none runs)." >&2; exit 1; }
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
cd "$ROOT"

if [ "$REUSE" = 0 ]; then
  "$PY" packaging/common/make_tray_icons.py "$ROOT/build/icons"
  rm -f "$ROOT"/build/wheel/ragbase_shield-*.whl
  uv build --wheel --out-dir "$ROOT/build/wheel" --build-constraints "$ROOT/packaging/common/build-constraints.txt" "$ROOT"
  WHEEL="$(ls "$ROOT"/build/wheel/ragbase_shield-"$VERSION"-*.whl | head -n 1)"
  case "$ARCH" in
    universal) TARGETS="x86_64 arm64" ;;
    *) TARGETS="$ARCH" ;;
  esac
  for a in $TARGETS; do
    "$PY" packaging/common/build_payload.py "macos-$a" "$B/payload-$a" --wheel "$WHEEL" --icons "$ROOT/build/icons"
  done
  if [ "$ARCH" = universal ]; then
    "$PY" packaging/common/build_payload.py merge-macos "$B/payload-x86_64" "$B/payload-arm64" "$B/payload-universal"
  fi
fi
PAYLOAD="$B/payload-$ARCH"
[ -d "$PAYLOAD" ] || { echo "Missing $PAYLOAD (run without --reuse-payload)." >&2; exit 1; }
PV="$(head -n 1 "$PAYLOAD/VERSION" 2>/dev/null || true)"
[ "$PV" = "$VERSION" ] || { echo "$PAYLOAD holds version '$PV' but pyproject.toml says $VERSION: run without --reuse-payload." >&2; exit 1; }
"$PY" packaging/common/check_payload.py "$PAYLOAD"

case "$ARCH" in
  universal) ARCHS="x86_64,arm64"; OUT="$ROOT/dist/RAGbase-Shield-$VERSION.pkg" ;;
  *) ARCHS="$ARCH"; OUT="$ROOT/dist/RAGbase-Shield-$VERSION-$ARCH.pkg" ;;
esac

# Resources and Distribution.xml with the version and architectures filled in.
rm -rf "$B/resources" "$B/component"
mkdir -p "$B/resources" "$B/component"
cp "$HERE/resources/welcome.html" "$HERE/resources/conclusion.html" "$B/resources/"
cp "$ROOT/LICENSE" "$B/resources/LICENSE.txt"
sed -e "s/__VERSION__/$VERSION/" -e "s/__ARCHS__/$ARCHS/" "$HERE/Distribution.xml" > "$B/Distribution.xml"

# Same file times in every build of one commit (SOURCE_DATE_EPOCH, else the commit time): the Payload and
# Scripts archives inside the .pkg are then identical; only the xar wrapper keeps its own creation time.
EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || echo 0)}"
STAMP="$(date -r "${EPOCH:-0}" +%Y%m%d%H%M.%S)"
rm -rf "$B/scripts"
cp -R "$HERE/scripts" "$B/scripts"
find "$PAYLOAD" "$B/scripts" -exec touch -h -t "$STAMP" {} +

# Component package: payload under "/Library/Application Support/RAGbase Shield", which the home domain
# turns into ~/Library/Application Support/RAGbase Shield.
pkgbuild --root "$PAYLOAD" \
         --identifier ai.ragbase.shield --version "$VERSION" \
         --install-location "/Library/Application Support/RAGbase Shield" \
         --scripts "$B/scripts" \
         "$B/component/RAGbase-Shield-component.pkg"
# pkgbuild always writes auth="root" in PackageInfo (it has no option for it). This package installs into the
# user's home only and its scripts run as that user, so it asks for no authorisation: with "root", Installer
# may ask for an administrator password that a lawyer without admin rights cannot give, and run the scripts as
# root. Same Payload and Scripts bytes, only that attribute changes.
rm -rf "$B/component-x"
pkgutil --expand "$B/component/RAGbase-Shield-component.pkg" "$B/component-x"
sed -i '' 's/ auth="root"/ auth="none"/' "$B/component-x/PackageInfo"
grep -q ' auth="none"' "$B/component-x/PackageInfo" || { echo "PackageInfo: could not set auth=none" >&2; exit 1; }
rm -f "$B/component/RAGbase-Shield-component.pkg"
pkgutil --flatten "$B/component-x" "$B/component/RAGbase-Shield-component.pkg"
rm -rf "$B/component-x"
# Extended attributes of the build machine (com.apple.provenance when the build runs from a tracked process)
# end up as "._" entries in the Bom: build from Terminal.app on a clean account for a release.
BOM="$(pkgutil --bom "$B/component/RAGbase-Shield-component.pkg" 2>/dev/null | head -n 1)"
NX="$(lsbom -s "$BOM" 2>/dev/null | grep -c '/\._' || true)"
case "$BOM" in /tmp/*.boms.*/Bom|/private/tmp/*.boms.*/Bom|/var/folders/*.boms.*/Bom) rm -rf "${BOM%/Bom}" ;; esac
[ "${NX:-0}" = 0 ] || echo "WARNING: $NX AppleDouble (._) entries in the payload (build-machine extended attributes)." >&2
productbuild --distribution "$B/Distribution.xml" \
             --resources "$B/resources" \
             --package-path "$B/component" \
             "$OUT"
(cd "$ROOT/dist" && shasum -a 256 "$(basename "$OUT")" > "$(basename "$OUT").sha256")
ls -l "$OUT"
echo "Built $OUT ($(du -h "$OUT" | cut -f1), unsigned)"
