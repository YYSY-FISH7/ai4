# M4/M5最小跨VM部署入口

仅补充develop中不存在的部署工具；已有源码、配置、测试、报告及许可材料均引用，不复制。M4为[detector.py](../../../code/detector.py)及[ROS节点](../../../catkin_ws/src/uav_tracking/scripts/detector_node.py)；M5为[visual_tracker.py](../../../code/visual_tracker.py)及[ROS节点](../../../catkin_ws/src/uav_tracking/scripts/visual_tracker_node.py)。[原M4说明](../../../design_module/M4/模块使用文档.md)、[原M5说明](../../../design_module/M5/模块使用文档.md)保留，原VM绝对路径不用于其他VM。

## 资源和环境

Ubuntu20.04 x86_64、Python3.8、ROS Noetic、cv_bridge、Catkin及共享包声明的mavros_msgs等系统前置。仅依赖消息不意味着启动飞控。本工具不执行apt/sudo，不覆盖系统Python/ROS。

内部包`M4-M5-团队完整交付-PR24.zip`已由成员负责发群；接收时先用同名.sha256校验外层，解压后按包内SHA256SUMS校验组件，再解压内层资源ZIP并核验。模型、7wheel、完整许可原文均在内部资源包，不公开上传。本目录[资源清单](resources/RESOURCE_MANIFEST.json)记录其大小/SHA，未发布任何新Release。内部包内旧源码快照不等于本PR分支，应使用当前分支/合并后的团队源码运行本工具。

原安装器固定numpy1.21.6、torch2.4.1+cpu、torchvision0.19.1+cpu、ultralytics8.4.173。七wheel：onnx1.16.2、ORT1.19.2、coloredlogs15.0.1、humanfriendly10.0、flatbuffers24.3.25、protobuf4.25.8、pip24.3.1。基础torch等仍需联网、约2GB磁盘，不是完全离线包。[40项版本参考](requirements-runtime-reference.txt)是原VM当前元数据快照，不是完整历史导出锁，也不是新VM安装成功证明。

## 在自己的工程中执行

以下路径由队友替换，不依赖维护者旧VM。优先使用已有有效隔离库；已有runtime不重复安装。
```bash
cd /自己的实际ai4工程
REPO="$PWD"
TOOLS="$REPO/scripts/部署/M4-M5"
ASSETS="/自己的实际解压目录/assets/m4-resource-kit"
export M4_MODEL="$ASSETS/model/yolo11s-drone.onnx"
python3 "$TOOLS/check-resources.py" --model "$M4_MODEL" --wheelhouse "$ASSETS/wheelhouse"
# 已有独立库则设置这两项，并跳过下面的安装：
# export M4_BASE_DEPS="/自己的基础库"
# export M4_ORT_DEPS="/自己的ORT库"
```
仅确认缺库时：
```bash
bash "$TOOLS/install-isolated.sh" --install-new-runtime --wheelhouse "$ASSETS/wheelhouse"
unset M4_BASE_DEPS M4_ORT_DEPS
```
包装器复用仓库既有[基础安装器](../../冲突库下载/install_m4_deps.sh)和[ONNX安装器](../../冲突库下载/install_m4_onnx_deps.sh)，不在仓库复制；只在全新runtime.pending.*安装并成功后发布runtime。拒绝已有runtime或链接、错版/缺失wheel，不卸载旧库。原节点优先工程lib/m4，BASE与其真实位置冲突时明确拒绝，避免静默错版加载。

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
