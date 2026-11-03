#!/usr/bin/env bash
# 显式下载公开 COCO 演示素材；下载失败不会保留半成品。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
mkdir -p "$HERE/assets"
download() {
  local out="$1" url="$2" temp
  [ ! -s "$out" ] || { echo "已有素材: $out"; return; }
  temp="$(mktemp "${out}.download.XXXXXX")"
  if curl -fL --retry 2 --connect-timeout 15 --max-time 300 -o "$temp" "$url" && [ -s "$temp" ]; then
    mv "$temp" "$out"
  else
    rm -f "$temp"
    echo "下载失败: $url" >&2; return 1
  fi
}
download "$HERE/assets/yolov8n.pt" 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt'
download "$HERE/assets/bus.jpg" 'https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/bus.jpg'
python3 - "$HERE/assets/bus.jpg" <<'PY'
import cv2, sys
image = cv2.imread(sys.argv[1])
assert image is not None, '素材不是有效图片，请人工移走损坏文件后重试'
print('图片有效:', image.shape)
PY
python3 "$HERE/make_moving_clip.py"
echo '素材准备完成；模型有效性由首次真实推理检查。'
