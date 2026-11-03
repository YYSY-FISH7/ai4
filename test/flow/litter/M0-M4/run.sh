#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$HERE/../../../.." && pwd -P)"
source /opt/ros/noetic/setup.bash
source "$ROOT/catkin_ws/devel/setup.bash"
case "${1:-check}" in
  check|run) shift 2>/dev/null || true ;;
  *) echo "用法: bash run.sh [check] [检查参数]"; exit 2 ;;
esac
exec python3 "$HERE/check.py" "$@"
