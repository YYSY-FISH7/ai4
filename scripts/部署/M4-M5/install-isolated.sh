#!/usr/bin/env bash
set -eo pipefail
KIT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO=$(realpath -e -- "$KIT/../../..")
usage() { echo '用法: bash install-isolated.sh --install-new-runtime --wheelhouse /实际七wheel目录；只安装至本工具runtime，不覆盖已有目录。'; }
[[ ${1:-} = --install-new-runtime ]] || { usage >&2; exit 2; }
shift
WHEELHOUSE=${M4_WHEELHOUSE:-"$KIT/wheelhouse"}
if [[ $# -gt 0 ]]; then
  [[ $# = 2 && $1 = --wheelhouse ]] || { usage >&2; exit 2; }
  WHEELHOUSE=$2
fi
[[ ! -e "$KIT/runtime" && ! -L "$KIT/runtime" ]] || { echo 'runtime已存在（或为链接），停止；不覆盖。' >&2; exit 2; }
[[ -d "$WHEELHOUSE" ]] || { echo '缺少经授权取得的七wheel目录；本PR不包含或公开发布二进制资源。' >&2; exit 2; }
WHEELHOUSE=$(realpath -e -- "$WHEELHOUSE")
export PATH="/usr/bin:/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 YOLO_AUTOINSTALL=false
/usr/bin/python3 -c 'import sys,platform; assert sys.version_info[:2]==(3,8), "需要Python3.8"; assert platform.machine()=="x86_64", "需要x86_64"'
/usr/bin/python3 -B "$KIT/check-resources.py" --wheelhouse "$WHEELHOUSE"
INSTALLERS="$REPO/scripts/冲突库下载"
[[ -f "$INSTALLERS/install_m4_deps.sh" && -f "$INSTALLERS/install_m4_onnx_deps.sh" ]] || { echo '缺团队原隔离安装脚本，请使用完整ai4工程。' >&2; exit 2; }
exec 9>"$KIT/.install.lock"; flock -n 9 || { echo '另一次安装正在运行' >&2; exit 2; }
STAGE=$(mktemp -d "$KIT/runtime.pending.XXXXXX")
export PIP_CONFIG_FILE=/dev/null PIP_CACHE_DIR="$STAGE/pip-cache" PYTHONUSERBASE="$STAGE/userbase"
unset PIP_TARGET PIP_PREFIX PIP_USER PIP_REQUIRE_VIRTUALENV
mkdir -p "$STAGE/scripts/冲突库下载"
cp "$INSTALLERS/install_m4_deps.sh" "$INSTALLERS/install_m4_onnx_deps.sh" "$STAGE/scripts/冲突库下载/"
echo "独立安装暂存: $STAGE；失败保留现场，不自动删除或覆盖其他环境。"
bash "$STAGE/scripts/冲突库下载/install_m4_deps.sh"
bash "$STAGE/scripts/冲突库下载/install_m4_onnx_deps.sh" --wheelhouse "$WHEELHOUSE"
/usr/bin/python3 - "$STAGE" "$KIT/runtime" <<'PY'
import os,sys
if os.path.lexists(sys.argv[2]):raise SystemExit('runtime出现，停止发布；暂存保留')
os.rename(sys.argv[1],sys.argv[2])
PY
echo '完成：仅本工具runtime/lib/m4和m4_onnx；系统Python、ROS和其他工程未安装。下一步preflight.sh。'
