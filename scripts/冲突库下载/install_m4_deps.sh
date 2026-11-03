#!/usr/bin/env bash
# Ubuntu 20.04 / ROS Noetic / Python 3.8. 仅在仓库 lib/m4 隔离安装。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
DIR="$ROOT/lib/m4"
check() {
  PYTHONPATH="$1${PYTHONPATH:+:$PYTHONPATH}" python3 - "$1" <<'PY'
import sys
from pathlib import Path
import numpy, torch, torchvision, ultralytics, matplotlib, cv2
expected = Path(sys.argv[1]).resolve()
for module, version in [(numpy,'1.21.6'), (torch,'2.4.1+cpu'),
                        (torchvision,'0.19.1+cpu'), (ultralytics,'8.4.173'),
                        (matplotlib,'3.7.5')]:
    path = Path(module.__file__).resolve()
    assert expected in path.parents, (module.__name__, str(path), '未隔离')
    assert module.__version__ == version, (module.__name__, module.__version__, version)
    print(module.__name__, module.__version__, path)
assert expected not in Path(cv2.__file__).resolve().parents, 'cv2 必须来自系统'
assert torchvision.ops.nms(torch.tensor([[0.,0.,2.,2.]]), torch.tensor([.9]), .5).tolist() == [0]
print('隔离依赖及 CPU NMS 自检通过；cv2:', cv2.__file__)
PY
}
case "${1:---check}" in
  --check) check "$DIR" ;;
  --install)
    python3 -c 'import sys; assert sys.version_info[:2] == (3,8), "本锁文件仅验证 Python 3.8"'
    if [ -e "$DIR" ]; then
      echo '隔离目录已存在：只检查，不覆盖。修复安装请先人工备份该目录。'
      check "$DIR"
      exit
    fi
    mkdir -p "$ROOT/lib"
    STAGE="$(mktemp -d "$ROOT/lib/.m4-install.XXXXXX")"
    trap 'echo "安装未完成，保留暂存目录供排查: $STAGE" >&2' ERR
    python3 -m pip install --target "$STAGE" --no-deps --retries 3 --timeout 60 \
      --index-url "${M4_TORCH_INDEX:-https://download.pytorch.org/whl/cpu}" \
      'torch==2.4.1+cpu' 'torchvision==0.19.1+cpu'
    python3 -m pip install --target "$STAGE" --no-deps --retries 3 --timeout 60 \
      --index-url "${M4_PYPI_INDEX:-https://pypi.org/simple}" \
      -r "$ROOT/scripts/冲突库下载/m4-requirements.lock"
    check "$STAGE"
    [ ! -e "$DIR" ] || { echo '目标目录被其他进程创建，停止安装'; exit 1; }
    mv -T "$STAGE" "$DIR"
    echo '安装完成。未更改系统包；请再运行 --check。'
    ;;
  *) echo "用法: bash $0 [--check|--install]"; exit 2 ;;
esac
