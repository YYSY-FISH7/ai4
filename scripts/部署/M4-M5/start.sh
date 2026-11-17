#!/usr/bin/env bash
set -eo pipefail
[[ $# = 2 && -f "$2" ]] || { echo '用法: bash start.sh 实际ai4工程目录 本次M0生成的connection.bash' >&2; exit 2; }
CONNECTION=$(realpath -e -- "$2")
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh" "$1"
source "$CONNECTION"
echo "使用本次M0环境: ROS_MASTER_URI=${ROS_MASTER_URI:-未设置}"
[[ -n ${ROS_MASTER_URI:-} ]] || exit 2
# Official entry checks camera publisher and refuses duplicate M4/M5 nodes.
exec bash "$REPO/test/flow/M0-M4/run.sh" --connection "$CONNECTION" --model "$MODEL" --ort-deps "$ORT"
