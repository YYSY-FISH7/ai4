#!/usr/bin/env bash
set -eo pipefail
KIT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $# -ge 1 && -d "$1" ]] || { echo '请提供队友实际ai4工程目录' >&2; return 2; }
REPO=$(realpath -e -- "$1")
MODEL=${M4_MODEL:-"$KIT/model/yolo11s-drone.onnx"}
BASE=${M4_BASE_DEPS:-"$KIT/runtime/lib/m4"}
ORT=${M4_ORT_DEPS:-"$KIT/runtime/lib/m4_onnx"}
[[ -f "$MODEL" ]] || { echo "模型缺失：$MODEL；请取得完整交接包，不使用COCO替代" >&2; return 2; }
[[ $(stat -c %s "$MODEL") = 37746458 ]] || { echo '模型大小错误' >&2; return 2; }
echo "320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7  $MODEL" | sha256sum -c -
[[ -d "$BASE" && -d "$ORT" ]] || { echo '隔离依赖不存在：先核实并通过M4_BASE_DEPS/M4_ORT_DEPS指定已有库，或阅读README在全新runtime目录安装。' >&2; return 2; }
if [[ -d "$REPO/lib/m4" && $(realpath -e -- "$REPO/lib/m4") != $(realpath -e -- "$BASE") ]]; then
  echo '现有原节点优先加载工程lib/m4；它与M4_BASE_DEPS不同。请核实并指定该工程真实库，或使用全新工程，避免静默加载错版依赖；本工具不覆盖旧库。' >&2
  return 2
fi
[[ -f /opt/ros/noetic/setup.bash && -f "$REPO/catkin_ws/devel/setup.bash" ]] || { echo '缺ROS Noetic或本工程编译消息setup；联系工程维护者，不自动构建或装系统包。' >&2; return 2; }
source /opt/ros/noetic/setup.bash
source "$REPO/catkin_ws/devel/setup.bash"
export PYTHONPATH="$BASE:$ORT${PYTHONPATH:+:$PYTHONPATH}"
export ROS_PACKAGE_PATH="$REPO/catkin_ws/src${ROS_PACKAGE_PATH:+:$ROS_PACKAGE_PATH}"
export PYTHONDONTWRITEBYTECODE=1 YOLO_AUTOINSTALL=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export KIT REPO MODEL BASE ORT
