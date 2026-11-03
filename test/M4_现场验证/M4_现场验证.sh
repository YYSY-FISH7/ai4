#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
bash "$HERE/实时演示/demo.sh" start
exec bash "$HERE/实时演示/verify.sh"
