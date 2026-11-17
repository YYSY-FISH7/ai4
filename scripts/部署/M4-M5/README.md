# M4/M5源码与跨VM部署

本目录补齐现有应用的部署与转换方法，不复制或修改已验收算法。M4在`code/detector.py`与`catkin_ws/src/uav_tracking/scripts/detector_node.py`；M5在`code/visual_tracker.py`与对应`visual_tracker_node.py`。共享`code/config.py`、`datatypes.py`及包内lib软链接、ROS消息、YAML/launch保持原结构。源码基于团队develop `59acc6295776a6f88336072e010b380ef3c30b65`。

## 从这里开始

完整步骤：[队友VM部署检查清单](../../../design_module/M4/部署交付/队友VM部署检查清单.md)；[依赖与构建](DEPENDENCIES.md)；[模型来源](model/SOURCE_CHAIN.md)；[M5独立入口](../../../design_module/M5/部署交付.md)。

假设队友已有完整ai4 Catkin构建、经核验的ONNX和独立依赖，在实际工程根目录执行：
```bash
REPO="$PWD"
TOOLS="$REPO/scripts/部署/M4-M5"
export M4_MODEL="/实际资源目录/model/yolo11s-drone.onnx"
export M4_BASE_DEPS="/实际已有基础依赖目录"
export M4_ORT_DEPS="/实际已有ONNX依赖目录"
python3 "$TOOLS/check-resources.py" --model "$M4_MODEL"
bash "$TOOLS/preflight.sh" "$REPO"
bash "$TOOLS/start.sh" "$REPO" "/当次M0生成的实际目录/connection.bash"
```
这些`/实际...`是需要替换的值，不是历史VM路径。缺库时按检查清单在本工具全新runtime安装，默认使用runtime/lib/m4及m4_onnx；已有库不重装。预检不启动ROS节点，start只启动原M4/M5，拒绝重复节点，不启动/停止M0或飞控。

## 输入输出与限制

实时Gazebo `/camera/image_raw` → M4真实YOLO → `/detections`、`/detector/debug_image`；M5接收正式检测及同一相机尺寸 → `/visual/tracks`（id、像素xywh bbox、area_ratio）。M4/M5分别向下游提供接口，不验收M3/M6/M8算法。conf=.50、imgsz640、ORT intra/inter=1；保留最新帧覆盖、过期保护及原跟踪参数。漏检、空航迹、ID重建和无Header无法严格同帧配对等限制不变。正常空目标与推理异常必须区分。

## 二进制和授权状态

**本PR只有源码、脚本、文档、清单与原始许可，不含ONNX、PT、wheel、完整ZIP、视频或bag。尚无新Release下载地址。** 获得资源后按[资源清单](resources/RESOURCE_MANIFEST.json)校验；不得用COCO模型替代。原ONNX SHA保持320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7。

HF模型卡Apache-2.0、ONNX AGPL元数据及Ultralytics官方政策原样保留，分发适用尚待确认，不通过删元数据解决。团队源码没有统一LICENSE，本次提交供审核不替团队指定许可证。第三方各自声明见[NOTICES](THIRD_PARTY_NOTICES.md)。[导出脚本](export/README.md)是历史流程的可移植适配器，本轮仅语法与帮助检查，没有重新导出或沿用旧视频证明新导出产物。

后续Release条件及上传后独立下载核验见[发行步骤](distribution/RELEASE_WORKFLOW_DRAFT.md)。许可事项不阻止本次源码资料PR；模型、依赖ZIP的公开发行仍需确认。队友另一VM的新安装与实时运行尚待其确认，不能把准备完成写成部署成功。
