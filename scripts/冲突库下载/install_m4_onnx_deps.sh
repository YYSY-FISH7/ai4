#!/usr/bin/env bash
# Add only ONNX Runtime to the existing isolated M4 dependencies.
set -eo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
target="$root/lib/m4_onnx"
check() {
  PYTHONPATH="$root/lib/m4:$target" /usr/bin/python3 -B - <<'PY'
import onnx, onnxruntime, numpy, sympy, packaging, coloredlogs, flatbuffers, google.protobuf
assert onnxruntime.__version__ == '1.19.2'
print('ORT', onnxruntime.__version__, onnxruntime.__file__)
print('numpy', numpy.__version__, numpy.__file__)
PY
}
if [[ ${1:-} == --help ]]; then
  echo '依赖: bash install_m4_onnx_deps.sh [--check | --wheelhouse DIR]'
  echo '只下载原模型（先准备/复用依赖，不会执行pip）: --download-model [--model-url HTTPS_URL]'
  exit 0
fi
if [[ ${1:-} == --download-model ]]; then
  shift
  model_url=${M4_MODEL_URL:-https://github.com/YYSY-FISH7/ai4/releases/download/m4-yolo11s-onnx-20261117/yolo11s-drone.onnx}
  if [[ $# -gt 0 ]]; then
    [[ $# == 2 && $1 == --model-url && -n $2 ]] || { echo '用法: --download-model [--model-url HTTPS_URL]' >&2; exit 2; }
    model_url=$2
  fi
  # Read-only imports first. Never create an empty dependency directory or run pip here.
  [[ -d "$target" && -d "$root/lib/m4" ]] || { echo '先复用或按原流程准备lib/m4、lib/m4_onnx；下载模型不会安装依赖。' >&2; exit 2; }
  export PYTHONDONTWRITEBYTECODE=1
  check
  /usr/bin/python3 -B - "$target/model/yolo11s-drone.onnx" "$model_url" <<'MODEL_PY'
# BEGIN MODEL DOWNLOAD
import fcntl
import hashlib
import os
from pathlib import Path
import tempfile
import time
import urllib.parse
import urllib.request

MODEL_SIZE = 37746458
MODEL_SHA256 = '320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7'


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    loopback = parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError('模型地址不得含账号密码，且必须有主机名')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and loopback):
        raise ValueError('仅接受HTTPS模型地址（本机HTTP仅用于测试）')


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verified(path):
    if not path.is_file() or path.stat().st_size != MODEL_SIZE:
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest() == MODEL_SHA256


def download_model(path, url):
    path = Path(path)
    # The Bash entry has already checked the dependencies. No dependency installation here.
    if not path.parent.parent.is_dir():
        raise ValueError('ONNX依赖目录不存在，不自动创建运行环境')
    path.parent.mkdir(exist_ok=True)
    with (path.parent / '.model-download.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(str(path)):
            if verified(path):
                print('模型已校验，跳过下载: ' + str(path), flush=True)
                return 'skipped'
            raise ValueError('已有模型无效或SHA不同，停止且不覆盖: ' + str(path))
        validate_url(url)
        temporary = None
        try:
            digest = hashlib.sha256()
            count = 0
            deadline = time.monotonic() + 180
            opener = urllib.request.build_opener(CheckedRedirect())
            request = urllib.request.Request(url, headers={'User-Agent': 'ai4-M4-model-download'})
            with opener.open(request, timeout=30) as response:
                validate_url(response.geturl())
                length = response.headers.get('Content-Length')
                if length is not None and int(length) != MODEL_SIZE:
                    raise ValueError('模型下载大小与验收原件不符')
                with tempfile.NamedTemporaryFile(dir=str(path.parent), prefix='.model-', suffix='.part', delete=False) as output:
                    temporary = Path(output.name)
                    while True:
                        if time.monotonic() > deadline:
                            raise TimeoutError('模型下载超时')
                        block = response.read(256 * 1024)
                        if not block:
                            break
                        count += len(block)
                        if count > MODEL_SIZE:
                            raise ValueError('模型超过验收原件大小')
                        output.write(block)
                        digest.update(block)
                    output.flush()
                    os.fsync(output.fileno())
            if count != MODEL_SIZE or digest.hexdigest() != MODEL_SHA256:
                raise ValueError('模型大小或SHA校验失败，不发布文件')
            # Atomic no-clobber publication; even unrelated writers cannot be overwritten.
            os.link(str(temporary), str(path))
            print('模型下载及SHA校验通过: ' + str(path), flush=True)
            return 'downloaded'
        finally:
            if temporary is not None:
                temporary.unlink()


if __name__ == '__main__':
    import sys
    try:
        download_model(sys.argv[1], sys.argv[2])
    except Exception as error:
        # Avoid echoing a possibly signed/private URL from a transport exception.
        print('模型获取失败（' + type(error).__name__ + '）；已有文件未覆盖，请检查网络/地址/文件校验。', file=sys.stderr)
        sys.exit(2)
# END MODEL DOWNLOAD
MODEL_PY
  exit
fi
if [[ ${1:-} == --check ]]; then check; exit; fi
mkdir -p "$root/lib"
exec 9>"$root/lib/.m4_onnx.install.lock"
flock -n 9 || { echo "另一个 M4 ONNX 安装正在运行" >&2; exit 1; }
if [[ -e "$target" ]]; then
  echo "已有 $target；请使用 --check 检查，或在新副本中准备依赖。" >&2
  exit 1
fi
mkdir -p "$root/lib"
stage=$(mktemp -d "$root/lib/m4_onnx.pending.XXXXXX")
printf 'Dependency staging directory: %s\n' "$stage"
options=()
if [[ ${1:-} == --wheelhouse ]]; then
  [[ -d ${2:-} ]] || { echo '缺少 wheelhouse 目录' >&2; exit 1; }
  options=(--no-index --find-links "$2")
fi
bootstrap=$(mktemp -d "$root/lib/m4_pip.pending.XXXXXX")
/usr/bin/python3 -m pip download "${options[@]}" --no-deps --dest "$bootstrap" pip==24.3.1
wheel="$bootstrap/pip-24.3.1-py3-none-any.whl"
[[ -f "$wheel" ]] || { echo '未取得隔离 pip wheel' >&2; exit 1; }
PYTHONPATH="$wheel" /usr/bin/python3 -m pip install --target "$stage" --no-deps "${options[@]}"   onnx==1.16.2 onnxruntime==1.19.2 coloredlogs==15.0.1 humanfriendly==10.0 flatbuffers==24.3.25 protobuf==4.25.8
PYTHONPATH="$root/lib/m4:$stage" /usr/bin/python3 -B -c 'import onnx,onnxruntime,numpy,sympy,packaging,coloredlogs,flatbuffers,google.protobuf; assert onnxruntime.__version__=="1.19.2"'
# Publish the validated directory while holding the installer lock.
/usr/bin/python3 - "$stage" "$target" <<'PY'
import os, sys
if os.path.exists(sys.argv[2]):
    raise SystemExit('Dependency target appeared during installation; staging directory preserved')
os.rename(sys.argv[1], sys.argv[2])
PY
check
