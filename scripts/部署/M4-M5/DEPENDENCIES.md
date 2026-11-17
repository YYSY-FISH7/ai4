# 依赖、构建及运行口径

## 系统前置

Ubuntu20.04 x86_64、Python3.8（原VM3.8.10）、ROS Noetic、Catkin、cv_bridge与系统OpenCV（原VM4.2.0）。共享uav_tracking包构建声明需要rospy、std_msgs、sensor_msgs、geometry_msgs、message_generation/runtime、mavros_msgs；后者只是构建依赖，不意味着启动MAVROS/飞控。本工具不执行apt/sudo，不覆盖系统Python/ROS。

## 隔离Python

原仓库`scripts/冲突库下载/install_m4_deps.sh`固定numpy1.21.6、torch2.4.1+cpu、torchvision0.19.1+cpu、ultralytics8.4.173；其他支持依赖保留原范围。原`install_m4_onnx_deps.sh`配合七wheel：onnx1.16.2、onnxruntime1.19.2、coloredlogs15.0.1、humanfriendly10.0、flatbuffers24.3.25、protobuf4.25.8，以及安装工具pip24.3.1。基础torch等需要联网，本资源不是完全离线安装包。

`requirements-runtime-reference.txt`固定记录当前VM40项发行物版本，[元数据快照](distribution/RUNTIME_PACKAGE_SNAPSHOT.json)保留原依赖声明；这是当前目录快照，不冒充历史导出完整锁或新VM已安装结果。原始wheel与基础依赖版权声明见THIRD_PARTY_NOTICES.md。安装前版本可用性和新VM导入仍需核验。

仓库包装器只复用上述两个原安装脚本：先检查七wheel的SHA；在自己的全新runtime.pending.*暂存目录安装，缓存/用户安装前缀也在暂存目录；成功才发布runtime。拒绝已有runtime或失效链接，失败保留现场，不执行卸载或覆盖其他库。实际命令见[VM检查清单](../../../design_module/M4/部署交付/队友VM部署检查清单.md)。

## 构建

优先复用队友成功构建的完整ai4工程。只有首次新工程需要按团队各包要求准备依赖并构建：
```bash
source /opt/ros/noetic/setup.bash
cd /实际工程/catkin_ws
catkin_make
source devel/setup.bash
```
保留package/lib指向根code的软链接，不将源码强行拆为两套。共享uav_tracking CMake安装列表/其他模块文件不改，M0仿真构建前置仍按M0文档处理。缺其他系统包交工程维护者处理，不自动安装或绕过。

## 运行及输出

加载顺序：Noetic→实际工程Catkin→独立Python依赖→当次M0 connection.bash。默认工具runtime/lib/m4和m4_onnx，也可用M4_BASE_DEPS/M4_ORT_DEPS指定既有真实目录，M4_MODEL指定可信ONNX。预检导入消息与依赖并CPU加载模型，不启动节点；start委托已有test/flow/M0-M4入口，使用同一master，仅启动原M4与原M5。ORT intra/inter=1、imgsz640、conf=.50不变。所有节点接同一相机，M5以实际尺寸计算area_ratio。

检测完成后发布结果，不保证随原始相机逐帧发布。主动丢弃旧帧与真正漏检分别记录；无目标空数组、推理失败、过期抑制不混为一谈。检测数组无Header，不能声称严格同帧配对。原跟踪器保留空轨迹与ID重建限制，不合入任何失败恢复方案。

本次不重装、不构建、不重新导出、不运行大型仿真；源版本和历史证据在现有M4/M5模块文档中，后续跨机部署应保存队友自己的预检和实时输出记录。
