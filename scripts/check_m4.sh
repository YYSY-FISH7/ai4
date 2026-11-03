#!/usr/bin/env bash
# 本模块可重复检查：单测 + 独立 ROS E2E，不启动正式联调接收方。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
source /opt/ros/noetic/setup.bash
source "$ROOT/catkin_ws/devel/setup.bash"
PYTHONPATH="$ROOT/lib/m4:$ROOT/code:${PYTHONPATH:-}" python3 -m pytest -q test/detector test/visual_tracker test/camera
bash test/camera/e2e_test/run_e2e.sh
bash test/detector/e2e_test/run_e2e.sh
bash test/visual_tracker/e2e_test/run_e2e.sh
echo 'M4 单测与三个 E2E 全部通过。正式仿真联调需另行运行 flow 检查。'
