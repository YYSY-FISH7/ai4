# M4/M5最小跨VM部署入口

仅补充develop中不存在的部署工具；已有源码、配置、测试、报告及许可材料均引用，不复制。M4为[detector.py](../../../code/detector.py)及[ROS节点](../../../catkin_ws/src/uav_tracking/scripts/detector_node.py)；M5为[visual_tracker.py](../../../code/visual_tracker.py)及[ROS节点](../../../catkin_ws/src/uav_tracking/scripts/visual_tracker_node.py)。[原M4说明](../../../design_module/M4/模块使用文档.md)、[原M5说明](../../../design_module/M5/模块使用文档.md)保留，原VM绝对路径不用于其他VM。

## 资源和环境

Ubuntu20.04 x86_64、Python3.8、ROS Noetic、cv_bridge、Catkin及共享包声明的mavros_msgs等系统前置。仅依赖消息不意味着启动飞控。本工具不执行apt/sudo，不覆盖系统Python/ROS。

内部包`M4-M5-团队完整交付-PR25.zip`已由成员负责发群；接收时先用同名.sha256校验外层，解压后按包内SHA256SUMS校验组件，再解压内层资源ZIP并核验。原模型另有Release单文件下载入口；7wheel与完整许可原文保留在内部资源包，依赖安装仍复用原流程。本目录[资源清单](resources/RESOURCE_MANIFEST.json)记录其大小/SHA，模型Release地址与校验值见下文。内部包内旧源码快照不等于本PR分支，应使用当前分支/合并后的团队源码运行本工具。

M4基础层及ONNX补充层的**唯一权威依赖清单**为仓库已有的[冲突库汇总.md（M4与M4 ONNX补充段）](../../冲突库下载/冲突库汇总.md)。版本、安装方式及后续变更均以该文件为准；本目录不另建requirements或40包清单。基础依赖首次安装仍需联网，约2GB磁盘，不是完全离线包。

## 在自己的工程中执行

以下路径由队友替换，不依赖维护者旧VM。优先使用已有有效隔离库；已有环境不重复安装。
```bash
cd /自己的实际ai4工程
REPO="$PWD"
TOOLS="$REPO/scripts/部署/M4-M5"
ASSETS="/自己的实际解压目录/assets/m4-resource-kit"
# 默认模型位置，无需设置M4_MODEL；只有复用其他位置的正确原件时才覆盖：
# export M4_MODEL="/自己的已有原模型路径/yolo11s-drone.onnx"
# 已有独立库则设置这两项，并跳过下面的安装：
# export M4_BASE_DEPS="/自己的基础库"
# export M4_ORT_DEPS="/自己的ORT库"
```
## 确认工程版本和两个既有安装入口

从实际工程根目录确认两个路径，文件名均为下划线：
```bash
git -C "$REPO" rev-parse HEAD
test -f "$REPO/scripts/冲突库下载/冲突库汇总.md"
test -f "$REPO/scripts/冲突库下载/install_m4_deps.sh"
test -f "$REPO/scripts/冲突库下载/install_m4_onnx_deps.sh"
```
旧提交e6a5328/a1ffd9e/44c89c8只有基础脚本；c421ec7起及当前develop/本PR均含两个。只看到一个时先确认是不是旧副本/不完整打包或所在目录错误，不重写安装器，也不覆盖当前工程。取得本PR版本或合并后的版本；ONNX入口为[原ONNX补充安装脚本](../../冲突库下载/install_m4_onnx_deps.sh)，基础入口为[原基础安装脚本](../../冲突库下载/install_m4_deps.sh)。

## 复用原环境，不新增安装机制

原安装器不是python -m venv：它用pip --target把基础依赖放在`<工程>/lib/m4`，ONNX扩展放在`<工程>/lib/m4_onnx`。本工具默认复用这两处；若它们是软链接，保留链接并使用其真实目标。已有其他兼容Python3.8环境，可通过M4_BASE_DEPS/M4_ORT_DEPS指定其包目录，再以preflight实际验证；仅激活venv不改变此入口使用ROS系统/usr/bin/python3的方式。仓库另有lib/venv/env.bash给M0传感器加载sensor_python，不能据此认为已含YOLO/ORT，不替换该环境。

已有库先运行后文preflight，检查失败停止并核对实际版本/路径，不自动升级、卸载或重装。需要时原安装器的`--check`只检查本工程目录，不安装；外部自有库应使用preflight。

只有确认相应目标目录不存在、也不是任何软链接，且没有其他可复用兼容库时，才允许使用现有原安装器（不是新增一套安装器）：
```bash
# 基础层已存在就跳过；若目录或软链接存在，下面检查会停止，禁止强行继续。
test ! -e "$REPO/lib/m4" && test ! -L "$REPO/lib/m4" || { echo '已有基础环境：只检查，不重新安装'; exit 2; }
bash "$REPO/scripts/冲突库下载/install_m4_deps.sh"
# ONNX补充层已存在就跳过；仅缺补充层时只执行本段，不重装基础层。
test ! -e "$REPO/lib/m4_onnx" && test ! -L "$REPO/lib/m4_onnx" || { echo '已有ONNX环境：只检查，不重新安装'; exit 2; }
bash "$REPO/scripts/冲突库下载/install_m4_onnx_deps.sh" --wheelhouse "$ASSETS/wheelhouse"
```
本工程缺库时创建的仍是原约定lib/m4与lib/m4_onnx，不创建工具runtime。原节点优先工程lib/m4，BASE与其真实位置冲突时明确拒绝，避免静默错版加载。

**删除风险核查**：原基础安装器安装模式会rm -rf目标lib/m4内numpy、numpy.libs、numpy-*.dist-info以及cv2/opencv_python相关文件，`--uninstall`会rm -rf整个目标lib/m4。不要对已有目录或链接运行安装/卸载。ONNX原安装器无rm -rf且会拒绝已存在目标，但对失效软链接的防护仍须以上test -L检查。本PR不修改这些既有脚本，不执行任何删除或安装。

## 单独下载模型，不安装或重建依赖

先完成原依赖的复用/检查；有lib/m4和lib/m4_onnx且兼容后执行：
```bash
bash "$REPO/scripts/冲突库下载/install_m4_onnx_deps.sh" --download-model
```
下载到`$REPO/lib/m4_onnx/model/yolo11s-drone.onnx`，SHA与37746458字节验收原件一致才发布。正确原件存在则跳过，错误文件、失效模型链接或并发写入均不覆盖。下载失败清除本次临时片段；不执行pip、不修改原依赖。支持lib/m4_onnx指向已有库的软链接，模型写在该库的model子目录。

默认下载地址为个人Fork Release `m4-yolo11s-onnx-20261117`的原ONNX附件。也可用`--download-model --model-url HTTPS_URL`或M4_MODEL_URL指定团队镜像；仍强制同一大小和SHA，不能替换模型。源码、wheel和全部依赖无需重新下载；内部ZIP保留作备用。模型许可与来源仍见MODEL_SOURCE_LICENSE.md，不修改原AGPL元数据。

只有新工程首次需要构建，已有成功构建跳过：
```bash
source /opt/ros/noetic/setup.bash
cd "$REPO/catkin_ws"
catkin_make
source devel/setup.bash
bash "$TOOLS/preflight.sh" "$REPO"
```
预检仅导入依赖和消息并CPU加载原ONNX，不启动ROS节点；缺系统前置交环境负责人。加载顺序Noetic→自己Catkin→隔离库→本次M0连接。复用M0负责人已有真实相机，不另起master或仿真：
```bash
CONNECTION="/本次M0实际目录/connection.bash"
bash "$TOOLS/start.sh" "$REPO" "$CONNECTION"
```
该入口委托已有[test/flow/M0-M4/run.sh](../../../test/flow/M0-M4/run.sh)，只启动原M4/M5，检查相机并拒绝重复节点；同一模型、640/.50、ORT intra/inter=1与原跟踪参数。Ctrl+C只停止自有M4/M5，不停止队友M0。

另一个观察终端设置同样变量后：
```bash
source "$TOOLS/env.sh" "$REPO"
source "$CONNECTION"
rostopic info /camera/image_raw
rostopic echo -n 1 /detections
rostopic echo -n 1 /visual/tracks
rosrun image_view image_view image:=/detector/debug_image
```
实时图像→M4检测→M5航迹；bbox为像素xywh，area_ratio按实际图像尺寸。保留漏检、空航迹、ID重建、主动跳帧和无Header不能严格同帧配对的限制。正常空目标与推理故障不能混淆，下游算法与完整飞行不在本次通过范围。

## 可选导出与许可

[来源和许可说明](MODEL_SOURCE_LICENSE.md)记录HF revision、基础权重未知项、PT/ONNX SHA及转换版本。正常部署不重新导出；可选导出必须使用独立环境与新输出目录：
```bash
# PYTHONPATH需指向自己的Ultralytics8.4.173/torch2.4.1+cpu/onnx1.16.2隔离库。
python3 "$TOOLS/export/export_verified_drone.py" --weights /实际原始best.pt \
  --output-dir /全新导出目录 --acknowledge-third-party-pickle
```
适配器未实际重导出，不能沿用原验收；完整原始许可在内部ZIP，仓库不再复制。HF Apache与ONNX AGPL声明均保留，未自行解决许可差异或给团队指定LICENSE。另一台VM的首次安装/构建/实时启动还需实际确认。
