#!/bin/sh
# Same as build.sh (name used in packaging/DESIGN.md section 11).
exec "$(cd "$(dirname "$0")" && pwd -P)/build.sh" "$@"
