# 第三方许可与版权声明

二进制候选状态：未发布；本目录源码技术资料提交团队PR供审核。各组件分别沿用其原许可，不为整个包指定Apache或其他统一许可证。以下表为来源索引，不能代替许可证原文。原始版权、许可、免责声明与NOTICES逐字节保留在distribution/licenses，本目录小文件哈希在SOURCE_SHA256SUMS.txt；外部模型及wheel哈希另见resources/SHA256SUMS.txt。

## 随包分发的七个wheel

|组件|版本|元数据声明|原文位置/备注|
|---|---|---|---|
|coloredlogs|15.0.1|MIT|distribution/licenses/wheels/coloredlogs/|
|flatbuffers|24.3.25|Apache 2.0|distribution/licenses/flatbuffers-v24.3.25-LICENSE.txt（官方tag补收）；官方根目录无独立NOTICE|
|humanfriendly|10.0|MIT|distribution/licenses/wheels/humanfriendly/|
|onnx|1.16.2|Apache License v2.0|distribution/licenses/wheels/onnx/|
|onnxruntime|1.19.2|MIT License|distribution/licenses/wheels/onnxruntime/，含ThirdPartyNotices.txt，按其中所有第三方原文保留|
|pip|24.3.1|MIT|distribution/licenses/wheels/pip/；内嵌组件见下表及完整vendor.txt，不仅是pip本体MIT|
|protobuf|4.25.8|3-Clause BSD License|distribution/licenses/wheels/protobuf/|

## pip 24.3.1内嵌组件

版本依据官方24.3.1的vendor.txt（完整保留）；下列原文来自同一官方源码标签。packaging双许可文件全部保留，PSF/Python历史许可不截取成单一MIT。

|组件|版本|原文所示许可|许可文件|
|---|---|---|---|
|CacheControl|0.14.0|Apache-2.0|distribution/licenses/pip-vendored/cachecontrol/LICENSE.txt|
|distlib|0.3.9|PSF/Python历史许可原文|distribution/licenses/pip-vendored/distlib/LICENSE.txt|
|distro|1.9.0|Apache-2.0|distribution/licenses/pip-vendored/distro/LICENSE|
|msgpack|1.0.8|Apache-2.0|distribution/licenses/pip-vendored/msgpack/COPYING|
|packaging|24.1|Apache-2.0 OR BSD，保留双许可文本|distribution/licenses/pip-vendored/packaging/LICENSE|
|platformdirs|4.2.2|MIT|distribution/licenses/pip-vendored/platformdirs/LICENSE|
|pyproject-hooks|1.0.0|MIT|distribution/licenses/pip-vendored/pyproject_hooks/LICENSE|
|requests|2.32.3|Apache-2.0|distribution/licenses/pip-vendored/requests/LICENSE|
|certifi|2024.8.30|MPL-2.0，见原文|distribution/licenses/pip-vendored/certifi/LICENSE|
|idna|3.7|BSD-3-Clause|distribution/licenses/pip-vendored/idna/LICENSE.md|
|urllib3|1.26.20|MIT|distribution/licenses/pip-vendored/urllib3/LICENSE.txt|
|rich|13.7.1|MIT|distribution/licenses/pip-vendored/rich/LICENSE|
|Pygments|2.18.0|BSD风格，以原文为准|distribution/licenses/pip-vendored/pygments/LICENSE|
|typing_extensions|4.12.2|PSF/Python历史许可原文|distribution/licenses/pip-vendored/typing_extensions.LICENSE|
|resolvelib|1.0.1|ISC风格，以原文为准|distribution/licenses/pip-vendored/resolvelib/LICENSE|
|setuptools/pkg_resources|70.3.0|MIT|distribution/licenses/pip-vendored/pkg_resources/LICENSE|
|tomli|2.0.1|MIT|distribution/licenses/pip-vendored/tomli/LICENSE|
|truststore|0.10.0|MIT|distribution/licenses/pip-vendored/truststore/LICENSE|

Pygments额外AUTHORS已从对应2.18.0官方源补收并保留。urllib3许可提及的CONTRIBUTORS.txt在已检查pip源码及urllib3该tag路径未取得，不能伪造；原许可中的版权与引用完整保留。该附加贡献者名单的缺失及适用分发要求仍列待确认。

## 来源和范围

wheel元数据/内置许可为首要文件依据；FlatBuffers来源https://github.com/google/flatbuffers/tree/v24.3.25 ，pip内嵌来源https://github.com/pypa/pip/tree/24.3.1/src/pip/_vendor 。来源URL、文件SHA和下载状态见distribution/LICENSE_SOURCES.json。

这里只覆盖实际随包的wheel与其已有嵌入声明（ORT第三方完整清单在原ThirdPartyNotices）。不代表对后续联网下载的torch、ultralytics等全部传递依赖完成独立授权审计；安装后应保留其原许可证和版本清单，不能将其重新归为本项目许可。Ultralytics软件/模型另见model/LICENSE_STATUS.md。项目脚本另见distribution/PROJECT_SCRIPTS_AUTHORIZATION.md。

## 基础运行依赖补充（本轮实读原安装目录）

以下34项基础依赖本体不在wheelhouse中，需要原隔离安装脚本联网取得。已补保留其安装发行物中的原始许可/版权文本；nvidia-ml-py使用原pynvml.py文件头的完整BSD声明。许可证字段仅如实抄录，不代替原文或法律判断。详distribution/BASE_RUNTIME_LICENSE_INVENTORY.json与distribution/licenses/base-runtime-snapshot/；40项版本元数据另见RUNTIME_PACKAGE_SNAPSHOT.json。该快照不是历史导出完整冻结环境。

| 组件 | 当前元数据版本 | 原始许可文件数 |
|---|---|---:|
| MarkupSafe | 2.1.5 | 1 |
| PyYAML | 6.0.3 | 1 |
| certifi | 2026.7.22 | 1 |
| charset-normalizer | 3.5.2 | 1 |
| contourpy | 1.1.1 | 1 |
| cycler | 0.12.1 | 1 |
| filelock | 3.16.1 | 1 |
| fonttools | 4.57.0 | 1 |
| fsspec | 2025.3.0 | 1 |
| idna | 3.15 | 1 |
| importlib_resources | 6.4.5 | 1 |
| Jinja2 | 3.1.6 | 1 |
| kiwisolver | 1.4.7 | 1 |
| matplotlib | 3.7.5 | 12 |
| mpmath | 1.3.0 | 1 |
| networkx | 3.1 | 1 |
| numpy | 1.21.6 | 2 |
| nvidia-ml-py | 13.615.71 | 1 |
| packaging | 26.2 | 3 |
| pillow | 10.4.0 | 1 |
| polars | 1.8.2 | 1 |
| psutil | 7.2.2 | 1 |
| pyparsing | 3.1.4 | 1 |
| python-dateutil | 2.9.0.post0 | 1 |
| requests | 2.32.4 | 1 |
| six | 1.17.0 | 1 |
| sympy | 1.13.3 | 2 |
| torch | 2.4.1+cpu | 2 |
| torchvision | 0.19.1+cpu | 1 |
| typing_extensions | 4.13.2 | 1 |
| ultralytics | 8.4.173 | 2 |
| ultralytics-thop | 2.2.2 | 1 |
| urllib3 | 2.2.3 | 1 |
| zipp | 3.20.2 | 1 |
