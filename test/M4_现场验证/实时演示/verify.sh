#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$HERE/console.py" verify "$@"
