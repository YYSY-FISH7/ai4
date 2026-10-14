#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PORT="${NAVIGATOR_E2E_PORT:-11332}"
export ROS_HOME="$(mktemp -d /tmp/uav_navigator_e2e.XXXXXX)"
export ROS_MASTER_URI="http://127.0.0.1:${PORT}"
source /opt/ros/noetic/setup.bash
source "${ROOT}/catkin_ws/devel/setup.bash"

MASTER_PID=""; NODE_PID=""; INPUT_PID=""; CHECK_PID=""
cleanup() {
  for pid in "${CHECK_PID}" "${INPUT_PID}" "${NODE_PID}" "${MASTER_PID}"; do
    [ -n "${pid}" ] && kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  rm -rf -- "${ROS_HOME}"
}
trap cleanup EXIT INT TERM

roscore -p "${PORT}" >/tmp/navigator_e2e_roscore.$$.log 2>&1 & MASTER_PID=$!
for _ in $(seq 1 60); do rosparam list >/dev/null 2>&1 && break; sleep 0.1; done
rosrun uav_tracking navigator_node.py __name:=navigator_e2e \
  /radar/tracks:=/test/radar_tracks /mavros/local_position/pose:=/test/local_pose \
  /ctrl/radar:=/test/ctrl_radar >/tmp/navigator_e2e_node.$$.log 2>&1 & NODE_PID=$!
timeout 10s python3 "${ROOT}/test/navigator/e2e_test/check_output.py" __name:=navigator_e2e_checker \
  >/tmp/navigator_e2e_check.$$.log 2>&1 & CHECK_PID=$!
sleep 0.8
timeout 8s python3 "${ROOT}/test/navigator/e2e_test/fake_inputs.py" __name:=navigator_e2e_source \
  >/tmp/navigator_e2e_input.$$.log 2>&1 & INPUT_PID=$!
wait "${INPUT_PID}"
wait "${CHECK_PID}"
cat /tmp/navigator_e2e_check.$$.log
