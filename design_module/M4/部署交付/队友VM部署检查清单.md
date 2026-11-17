# 队友VM部署检查清单：实时Gazebo → M4 → M5

本清单不依赖维护者旧VM的/home/demo路径。每项完成后记录队友实际路径与结果；当前没有宣称另一台VM已部署成功。

## 1. 确认工程与资源

- 完整ai4工程包含已审核的本部署目录；记录分支/commit及实际REPO。
- Ubuntu20.04 x86_64、Python3.8、ROS Noetic、Catkin、cv_bridge、共享包系统前置已由环境负责人准备。
- 经授权取得原yolo11s-drone.onnx，37746458字节，SHA `320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7`。不是COCO模型；本PR尚不提供公开模型/ZIP下载链接。
- 记录实际M4_BASE_DEPS/M4_ORT_DEPS；没有库才准备七wheel并新建隔离runtime。不覆盖已有依赖。

在自己工程根目录设置：
```bash
REPO="$PWD"
TOOLS="$REPO/scripts/部署/M4-M5"
export M4_MODEL="/自己的资源目录/model/yolo11s-drone.onnx"
python3 "$TOOLS/check-resources.py" --model "$M4_MODEL"
```

已有已核实隔离库则设置并跳过安装：
```bash
export M4_BASE_DEPS="/自己的实际基础库目录"
export M4_ORT_DEPS="/自己的实际ONNX库目录"
```
若工程已有lib/m4，原节点会优先加载它，M4_BASE_DEPS必须指向该目录的真实位置；包装器检测到冲突即拒绝启动。不要为使用另一套库而覆盖旧目录，可改用全新工程。
缺依赖时才执行（基础层需网络；七wheel先经授权取得）：
```bash
bash "$TOOLS/install-isolated.sh" --install-new-runtime   --wheelhouse "/自己的资源目录/wheelhouse"
unset M4_BASE_DEPS M4_ORT_DEPS
# 工具随后默认使用自身runtime/lib/m4和m4_onnx。
```
新runtime已经存在或安装失败时停止核对，不删除重来，不清理他人目录。当前版本快照是参考，不是所有传递依赖已在新VM重装的证明。

## 2. Catkin与无节点预检

已有catkin_ws/devel/setup.bash无需重复构建。首次构建按[依赖说明](../../../scripts/部署/M4-M5/DEPENDENCIES.md)执行；缺系统依赖找环境负责人，不运行全局pip。
```bash
bash "$TOOLS/preflight.sh" "$REPO"
```
预期：模型SHA、Python3.8、Ultralytics8.4.173、ORT1.19.2、uav_tracking消息与CPU模型加载通过；没有启动ROS Master/Gazebo/检测器。

## 3. M0提供实时图像和当次连接

已有M0运行优先复用，不另开一套。需要启动时由M0环境负责人在Ubuntu图形会话、满足其依赖/插件前提后使用团队入口：
```bash
cd "$REPO"
bash catkin_ws/src/uav_sim/scripts/start_mounted_radar.sh sensor_profile:=desktop gui:=false
```
记录该次启动打印的数据目录与其中connection.bash。不要按文件名猜测旧连接，也不要额外运行roscore。不擅自启动或关闭他人仿真。DISPLAY或Gazebo相机异常应交M0环境负责人处理，不能用历史bag冒充此实时接入步骤。

## 4. 同一master启动M4/M5

在M4终端保留第1步变量后：
```bash
CONNECTION="/当次M0打印的数据目录/connection.bash"
bash "$TOOLS/start.sh" "$REPO" "$CONNECTION"
```
预期：相机发布者存在，未运行同名检测/跟踪节点；只启动原detector与visual_tracker，日志目录由入口打印。模型路径显式、640/.50、ORT线程1/1，原跟踪算法/参数不变。节点重复则联系所有者，不自动杀进程。

## 5. 只读检查真实输出

另一个观察终端设置相同REPO/TOOLS/M4_MODEL及依赖变量，加载同一次connection：
```bash
source "$TOOLS/env.sh" "$REPO"
source "$CONNECTION"
rostopic info /camera/image_raw
rostopic info /detections
rostopic info /visual/tracks
rostopic hz /detections
rostopic echo -n 1 /detections
rostopic echo -n 1 /visual/tracks
rosrun image_view image_view image:=/detector/debug_image
```
将真实图像目标与class_id=0/drone、confidence、像素xywh框对应；航迹包含id/bbox/area_ratio，面积按实际图像尺寸计算。观察正常无目标时空数组、重新出现后建轨，保留漏检、空航迹和ID重建。只看到话题存在不代表检测正确；推理异常不能当正常空目标。模型输出频率随CPU竞争变化，不保证固定2～3Hz。

## 6. 结束与交接

在start终端Ctrl+C仅停止本次M4/M5；不要killall或停止队友M0。保留打印出的detector.log/tracker.log、预检输出、版本和实际资源SHA；无需本轮重录视频。把无法满足的前置明确交给相应负责人：M0负责实时相机/master，M4/M5负责自身输入/算法/输出，下游控制和状态决策由M6/M8等负责人验收。

## 常见失败与处理

- 模型缺失/大小或SHA错误：停止，取得正确原件，不换默认COCO模型。
- wheel缺失/校验不符：不进入安装，补齐经授权原资源。
- 库缺失/版本不符：先核对自己的目录，不全局安装。
- 消息/构建setup缺失：完成团队Catkin前置，不另建伪消息。
- master不可达/无相机：核实本次connection及M0，不另起roscore。
- 目标未出框或ID重建：保留运行日志和图像证据，不降正式阈值掩盖问题。
