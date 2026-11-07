# M0-M1 联调：点云聚类可视化

M0（Gazebo 仿真）发布 `/radar/points`，M1（`/cluster`）输出 `/radar/centroid`。本目录的脚本把质心实时画成三维散点，用于判断「输入是否为规范点云、输出是否符合预期」。

## 目录

| 路径 | 内容 |
|---|---|
| `python/live_centroid_view.py` | 实时三维可视化脚本 |
| `image/live_centroid_view.png` | 实测截图（3 个固定物质心 + 原始点云 + 目标真值） |
| `log/` | 长期保留的运行日志，当前为空 |

## 启动方法

需要三个终端。M0 使用独立 ROS master（端口随机），后两个终端都要 source 同一次运行的 `connection.bash`。

### 终端 A：启动 M0 仿真

```bash
cd /home/demo/桌面/ai4
bash catkin_ws/src/uav_sim/scripts/start_mounted_radar.sh
```

记下它打印的「雷达/相机数据目录：$RUN_DIR」，等待查看器窗口出现。

### 终端 B：启动 M1 聚类

```bash
cd /home/demo/桌面/ai4
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
source data/radar/<RUN_DIR>/connection.bash
roslaunch uav_tracking cluster.launch
```

### 终端 C：启动可视化

```bash
cd /home/demo/桌面/ai4
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
source data/radar/<RUN_DIR>/connection.bash
/usr/bin/python3 test/flow/M0-M1/python/live_centroid_view.py --with-cloud --show-truth
```

必须用系统 `/usr/bin/python3`（rospy 装在该解释器下）。脚本本身不启动 M0 或 M1，只做订阅。

## 参数

| 参数 | 说明 |
|---|---|
| `--duration 30` | 运行秒数，0（默认）表示直到 Ctrl+C |
| `--with-cloud` | 叠加降采样后的原始点云（默认 500 点，用 `--max-cloud-points` 调整） |
| `--show-truth` | 叠加目标真值（橙色星，需 `/target/ground_truth/pose`） |
| `--save out.png` | 退出前保存画面 |
| `--xlim / --ylim / --zlim` | 坐标轴范围，默认 `-2 12` / `-6 6` / `-2 3` |

## 预期效果

![实测截图](image/live_centroid_view.png)

- 红色为 M1 输出的质心，灰色为原始点云，橙色星为目标真值；
- 坐标为 `radar_link` 局部系（x 前、y 左、z 上），原点在机载雷达，不是世界系；
- 标题实时显示接收帧数、仿真时间与当前帧质心数。

## 已知限制

- 默认 `z_thresh=0.3` 是按世界系地面定的，而点云在 `radar_link` 局部系下，目标点常被当成地面滤掉。此时橙星附近没有红点，可临时用 `rosrun uav_tracking cluster_node.py _z_thresh:=-0.5` 覆盖验证 —— 属坐标系遗留问题，不代表链路不通。
- matplotlib 三维渲染约 0.3 s/帧，实测接收约 3 Hz，是显示端上限；M1 实际输出 5 Hz。
