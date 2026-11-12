#!/bin/bash
# TODO (not run yet): sign and notarise the macOS installer. Steps in packaging/macos/TODO_SIGNING.md.
#
# Needs (the publisher's Apple Developer Program account):
#   SHIELD_APP_IDENTITY        "Developer ID Application: <Name> (<TEAMID>)"  in the build keychain
#   SHIELD_INSTALLER_IDENTITY  "Developer ID Installer: <Name> (<TEAMID>)"    in the build keychain
#   SHIELD_NOTARY_PROFILE      a notarytool keychain profile, created once with:
#     xcrun notarytool store-credentials ragbase-notary --apple-id <id> --team-id <TEAMID> --password <app-specific>
#
# Usage: SHIELD_APP_IDENTITY=... SHIELD_INSTALLER_IDENTITY=... SHIELD_NOTARY_PROFILE=ragbase-notary \
#          packaging/macos/sign_and_notarize_TODO.sh [universal|x86_64|arm64]
# Exits 2 until the identities and the profile exist. Nothing here has been run: no signature is faked.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
ARCH="${1:-universal}"
: "${SHIELD_APP_IDENTITY:=}" "${SHIELD_INSTALLER_IDENTITY:=}" "${SHIELD_NOTARY_PROFILE:=}"
if [ -z "$SHIELD_APP_IDENTITY" ] || [ -z "$SHIELD_INSTALLER_IDENTITY" ] || [ -z "$SHIELD_NOTARY_PROFILE" ]; then
  echo "TODO: certificate not configured (see packaging/macos/TODO_SIGNING.md)." >&2
  exit 2
fi
security find-identity -v -p codesigning | grep -qF "$SHIELD_APP_IDENTITY" || { echo "Missing identity: $SHIELD_APP_IDENTITY" >&2; exit 2; }
security find-identity -v | grep -qF "$SHIELD_INSTALLER_IDENTITY" || { echo "Missing identity: $SHIELD_INSTALLER_IDENTITY" >&2; exit 2; }

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -n 1)"
PAYLOAD="$ROOT/build/macos/payload-$ARCH"
[ -d "$PAYLOAD" ] || { echo "Build first: packaging/macos/build.sh --arch $ARCH" >&2; exit 1; }
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null || { echo "Need Python 3.11+ (the repo .venv or python3)." >&2; exit 1; }

# 1. Sign every Mach-O file of the payload (dylibs and extension modules first, executables last),
#    hardened runtime, secure timestamp.
find "$PAYLOAD" -type f \( -name '*.so' -o -name '*.dylib' \) -print0 | while IFS= read -r -d '' f; do
  codesign --force --options runtime --timestamp --sign "$SHIELD_APP_IDENTITY" "$f"
done
find "$PAYLOAD" -type f -perm -u+x -path '*/bin/python3.12' -print0 | while IFS= read -r -d '' f; do
  codesign --force --options runtime --timestamp --entitlements "$HERE/python.entitlements" \
           --sign "$SHIELD_APP_IDENTITY" "$f"
done
# The MANIFEST changes with the signatures: rewrite it, then check the payload again.
# Same interpreter rule as build.sh (a clean checkout has no .venv); checked before any file is signed.
"$PY" -c "import sys; sys.path.insert(0, '$ROOT/packaging/common'); import build_payload as b; b.write_manifest(__import__('pathlib').Path('$PAYLOAD'))"
"$PY" "$ROOT/packaging/common/check_payload.py" "$PAYLOAD"

# 2. Repack with the signed payload (same commands as build.sh), then sign the product archive.
"$HERE/build.sh" --arch "$ARCH" --reuse-payload
case "$ARCH" in universal) PKG="$ROOT/dist/RAGbase-Shield-$VERSION.pkg" ;; *) PKG="$ROOT/dist/RAGbase-Shield-$VERSION-$ARCH.pkg" ;; esac
productsign --timestamp --sign "$SHIELD_INSTALLER_IDENTITY" "$PKG" "$PKG.signed"
mv "$PKG.signed" "$PKG"
pkgutil --check-signature "$PKG"

# 3. Notarise, staple, assess.
xcrun notarytool submit "$PKG" --keychain-profile "$SHIELD_NOTARY_PROFILE" --wait
xcrun stapler staple "$PKG"
xcrun stapler validate "$PKG"
spctl --assess --type install -vv "$PKG"    # expect: accepted, source=Notarized Developer ID
(cd "$ROOT/dist" && shasum -a 256 "$(basename "$PKG")" > "$(basename "$PKG").sha256")
echo "Signed and notarised: $PKG"
