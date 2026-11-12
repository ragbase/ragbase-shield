#!/bin/sh
# Re-create the hashed lock files of the installer payloads (run when pyproject.toml dependencies change, or
# after editing build-constraints.in). Needs uv (build tool). Output: packaging/common/requirements-<target>.lock
# and packaging/common/build-constraints.txt (to be committed with packaging/).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
cd "$ROOT"
# pypdfium2 5.x ships macosx_13_0 wheels only: the macOS payload targets macOS 13 or newer (pins.json).
MACOSX_DEPLOYMENT_TARGET=13.0 uv pip compile pyproject.toml --extra tray-mac --python-version 3.12 \
  --python-platform aarch64-apple-darwin --generate-hashes --no-header --quiet \
  -o packaging/common/requirements-macos-arm64.lock
MACOSX_DEPLOYMENT_TARGET=13.0 uv pip compile pyproject.toml --extra tray-mac --python-version 3.12 \
  --python-platform x86_64-apple-darwin --generate-hashes --no-header --quiet \
  -o packaging/common/requirements-macos-x86_64.lock
uv pip compile pyproject.toml --extra tray-win --python-version 3.12 \
  --python-platform x86_64-pc-windows-msvc --generate-hashes --no-header --quiet \
  -o packaging/common/requirements-windows-x64.lock
# Build backends (build tools only): hatchling for the Shield wheel, setuptools + wheel for the sdists.
uv pip compile packaging/common/build-constraints.in --universal --python-version 3.11 --generate-hashes \
  --no-header --quiet -o packaging/common/build-constraints.txt
echo "relock: $(grep -c '==' packaging/common/requirements-macos-x86_64.lock) / $(grep -c '==' packaging/common/requirements-macos-arm64.lock) / $(grep -c '==' packaging/common/requirements-windows-x64.lock) pins (macOS x86_64 / arm64 / Windows)"
