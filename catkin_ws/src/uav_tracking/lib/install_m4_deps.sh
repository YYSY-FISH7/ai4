#!/usr/bin/env bash
# 兼容旧路径；规范入口在 scripts/冲突库下载/。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd -P)"
exec bash "$ROOT/scripts/冲突库下载/install_m4_deps.sh" "$@"
