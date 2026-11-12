#!/bin/sh
# Compare two macOS installer packages by content. The .pkg files themselves always differ (the xar wrapper
# keeps its own creation time); every part inside must be identical for two builds of one commit.
#   packaging/macos/compare_pkgs.sh <a.pkg> <b.pkg>      exit 0 = same content, 1 = a part differs
set -u
[ $# -eq 2 ] || { sed -n '2,4p' "$0"; exit 2; }
T="$(mktemp -d "${TMPDIR:-/tmp}/shield-pkgcmp.XXXXXX")"
trap 'rm -rf "$T"' EXIT
pkgutil --expand "$1" "$T/a" >/dev/null && pkgutil --expand "$2" "$T/b" >/dev/null || exit 2
rc=0
same() { if "$@" >/dev/null 2>&1; then echo "same    $LABEL"; else echo "DIFFER  $LABEL"; rc=1; fi; }
LABEL="list of parts"; same test "$(cd "$T/a" && ls)" = "$(cd "$T/b" && ls)"
for c in "$T"/a/*.pkg; do
  n="$(basename "$c")"
  for part in Payload Bom PackageInfo; do LABEL="$n/$part"; same cmp "$c/$part" "$T/b/$n/$part"; done
  LABEL="$n/Scripts"; same diff -r "$c/Scripts" "$T/b/$n/Scripts"
done
LABEL="Distribution"; same cmp "$T/a/Distribution" "$T/b/Distribution"
LABEL="Resources"; same diff -r "$T/a/Resources" "$T/b/Resources"
exit $rc
