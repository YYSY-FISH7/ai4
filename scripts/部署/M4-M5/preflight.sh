#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh" "$@"
/usr/bin/python3 -B - <<'PY'
import sys,os,json,ultralytics,onnxruntime,cv_bridge,rospy
from uav_tracking.msg import Detections,VisualTrackArray
assert sys.version_info[:2]==(3,8), '需要ROS Noetic Python3.8'
assert ultralytics.__version__=='8.4.173'
assert onnxruntime.__version__=='1.19.2'
print(json.dumps({'ultralytics':ultralytics.__version__,'onnxruntime':onnxruntime.__version__,'base':os.environ['BASE'],'ort':os.environ['ORT'],'ROS_messages':'OK','nodes_started':False}))
PY
/usr/bin/python3 -B "$REPO/test/flow/M0-M4/python/run-m4.py" --model "$MODEL" --ort-deps "$ORT" --check
