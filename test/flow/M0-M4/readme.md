# M4 检测器单线程启动

此入口适用于 Ubuntu 20.04、ROS Noetic、系统 Python 3.8 和 CPU 推理。本次使用已编译的 Catkin 工作空间、现有隔离 M4 Python 依赖和 ONNX Runtime 1.19.2。继续使用已验证的 YOLO11s ONNX 权重，SHA-256 为 `320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7`。权重及 Python 依赖保存在实验环境中。

原版用默认 ONNX Runtime 会话线程配置。可选脚本仅将 `SessionOptions.intra_op_num_threads` 和 `inter_op_num_threads` 都设为 1，然后在同一 Python 进程执行原 `detector_node.py`。节点参数原样转发。模型、阈值、图像尺寸、话题、消息格式和原跟踪器均沿用原配置。

## 启动

先使用团队 M0 启动入口，保留它生成的 `connection.bash`。在本次 M0 会话下仅运行一个 `/detector`。已运行的检测节点可在其终端按 Ctrl+C 后切换。跟踪器继续使用原有启动方式。

在已编译的工程目录执行以下命令，将 `RUN_DIR` 替换为本次 M0 的实际数据目录。如隔离依赖或模型放在其他位置，调整对应变量。

```bash
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
RUN_DIR=/path/to/current/m0/run
source "$RUN_DIR/connection.bash"

MODEL_DIR=/home/demo/m4-yolo11s-validation.8b694G
export PYTHONPATH="$PWD/lib/m4:$MODEL_DIR/onnx-deps${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
rosparam load catkin_ws/src/uav_tracking/config/detector.yaml /detector

/usr/bin/python3 -B -u test/flow/M0-M4/python/run-detector-ort1.py \
  "$PWD/catkin_ws/src/uav_tracking/scripts/detector_node.py" \
  _model_path:="$MODEL_DIR/yolo11s-drone.onnx" _imgsz:=640 _conf_thres:=0.50
```

比较原版时，移除命令中的 `test/flow/M0-M4/python/run-detector-ort1.py`，直接运行同一个节点文件，保留其余参数与环境变量。检测时序诊断可在两组同时设置 `M4_TIMING_LOG=1`。若已编译的工程仍检出基线，也可以把命令中的脚本替换为本分支脚本的绝对路径，继续复用当前工程的构建产物。

## 2026-11-10 人工 Gazebo A/B

两组共用 M0 会话、320×240 原图、同一 ONNX 权重、CPU、`imgsz=640`、`conf_thres=0.50` 和原跟踪器。检测频率以墙钟计算。

| 指标 | A 默认线程 | B 单线程 |
| --- | ---: | ---: |
| 检测输出频率 | 0.985 Hz | 2.135 Hz |
| 推理耗时中位数 | 979.41 ms | 459.21 ms |
| 正确匹配／已处理可见帧 | 23／56 | 55／123 |
| 正确匹配／全部可确认可见原图 | 23／367 | 55／324 |
| 相邻正确检出最长间隔（仿真时间） | 7.10 s | 3.20 s |
| 空航迹／全部航迹 | 40／57 | 79／124 |

正确匹配采用源图、Gazebo 位姿投影及像素参考框核对，要求类别为 drone 且 IoU ≥ 0.30。检测与航迹消息没有 Header，使用调试图源时间戳和日志关联，无法配对的样本排除。两段录包未覆盖可确认的离场，且没有人工框标注，表中的比例只描述这两段数据，不能用来宣称模型准确率或 ID 稳定性通过。

证据文件保留在 Ubuntu 的 `/home/demo/m4-ort1-ab/`，包括 `A-default.bag`、`B-ort1.bag` 和两组检测日志。
