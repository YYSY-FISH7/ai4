#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/noetic/setup.bash
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec /usr/bin/python3 -B "$here/python/replay.py" "$@"
