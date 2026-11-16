# Ubuntu工程与依赖定位

本轮只整理M4/M5实时验收材料，Git基线为PR21已合并后的3e3a5d5。未启动或切换VM运行源码；其既有正式入口为/home/demo/ai4-m4-m5-formal-20261116，已核实运行代码为PR20最终ded098a，核心与后续纯资料提交一致。当前验收不要求M3/M6/M8或飞行链。

## 保留的工程关系

- /home/demo/M4-M5维护资料：M4、M5、跨模块和历史索引；正式实时视频只认正式实时验收-01-02/索引。实际视频在Windows维护根目录/正式交付/实时验收_01-02。旧下游演示索引为历史，不是当前验收依据。
- formal-20261116：原M4/M5代码、ROS脚本和文档入口，lib/detector.py、visual_tracker.py分别指向本工程code/下实现；不移动源码或消息。
- /home/demo/ai4-m4-m5-delivery-20261116：旧f540ae4回归工作区，有历史未提交资料，不能代替正式入口。
- catkin_ws/devel兼容链接依赖/home/demo/ai4-m4-integration-e6a5328已编译结果；Git对象也复用旧仓库，不能删除integration。
- /home/demo/ai4-m4-acceptance-c421ec7：旧c421验收及依赖定位，本身无devel/setup.bash；如运行需显式复用integration构建。
- /home/demo/桌面/ai4：83e0f46旧副本，存在历史未提交工作，不清理或当作最新正式版本。原priority/recovery等历史候选均不因目录名被当正式算法。

## 隔离依赖与模型

formal源码没有本地lib/m4或lib/m4_onnx。现有M4依赖使用/home/demo/ai4-m4-acceptance-c421ec7/lib/m4（实际到ai4-formal-e6a5328，numpy1.21.6、ultralytics8.4.173）和lib/m4_onnx（实际到acceptance-44c89c8，onnx1.16.2、onnxruntime1.19.2）。M4启动显式设置PYTHONPATH与--ort-deps，见M4独立说明；不能把系统numpy1.17.4当检测环境。模型/home/demo/m4-yolo11s-validation.8b694G/yolo11s-drone.onnx保持原处、原SHA，CPU ORT intra/inter=1。新机器按模型/依赖说明准备，不把本机路径当下载链接，不装全局依赖。

## 运行入口

M0本次connection.bash连接其动态master；M4/M5组合入口test/flow/M0-M4/run.sh，M5单独roslaunch uav_tracking visual_tracker.launch（已有节点不重复启动）。M5不加载YOLO。test/flow/M4-M5/run.sh为算法自身离线核验，只作辅助，不能冒充新实时验收。正式视频01/02与原相机、检测、航迹和Gazebo记录共同证明基本功能。

原始视频、bag、模型和历史实验均外存保留。未移动Catkin关键路径、安装依赖、重跑完整环境或新Gazebo；不宣称全新基础镜像部署已重装验证。
