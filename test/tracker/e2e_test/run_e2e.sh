#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PORT="${TRACKER_E2E_PORT:-11331}"
export ROS_HOME="$(mktemp -d /tmp/uav_tracker_e2e.XXXXXX)"
export ROS_MASTER_URI="http://127.0.0.1:${PORT}"
source /opt/ros/noetic/setup.bash
source "${ROOT}/catkin_ws/devel/setup.bash"

MASTER_PID=""
NODE_PID=""
CHECK_PID=""
cleanup() {
  for pid in "${CHECK_PID}" "${NODE_PID}" "${MASTER_PID}"; do
    [ -n "${pid}" ] && kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  rm -rf -- "${ROS_HOME}"
}
trap cleanup EXIT INT TERM

roscore -p "${PORT}" >/tmp/tracker_e2e_roscore.$$.log 2>&1 & MASTER_PID=$!
for _ in $(seq 1 60); do rosparam list >/dev/null 2>&1 && break; sleep 0.1; done
rosrun uav_tracking tracker_node.py __name:=tracker_e2e \
  /radar/centroid:=/test/radar_centroid /radar/tracks:=/test/radar_tracks \
  >/tmp/tracker_e2e_node.$$.log 2>&1 & NODE_PID=$!
timeout 12s python3 "${ROOT}/test/tracker/e2e_test/check_tracks.py" __name:=tracker_e2e_checker \
  >/tmp/tracker_e2e_check.$$.log 2>&1 & CHECK_PID=$!
sleep 0.8
timeout 8s python3 "${ROOT}/test/tracker/e2e_test/fake_centroid.py" __name:=tracker_e2e_source
wait "${CHECK_PID}"
cat /tmp/tracker_e2e_check.$$.log
