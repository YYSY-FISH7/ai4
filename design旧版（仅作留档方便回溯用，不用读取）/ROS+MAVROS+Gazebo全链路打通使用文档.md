# ROS + MAVROS + Gazebo 全链路打通使用文档

> Ubuntu 20.04 + ROS Noetic + Gazebo 11 + PX4 SITL v1.14.0 ｜ 2026-10-03 本机实测跑通
> 对应项目：《无人机多模态智能目标跟踪与制导》仿真环境（阶段 1）

---

## 一、快速开始（三个终端）

### 终端1 · 启动仿真（PX4 + Gazebo）

```bash
cd ~/PX4-Autopilot
make px4_sitl gazebo
```

启动后进入 `pxh>` 命令行。可选变体：

```bash
HEADLESS=1 make px4_sitl gazebo      # 无界面，省 CPU
make px4_sitl gazebo_iris_vision     # 带相机
make px4_sitl gazebo_iris_rplidar    # 带激光雷达
```

### 终端2 · 启动 MAVROS 桥（保持开启，不可复用）

```bash
source /opt/ros/noetic/setup.bash
roslaunch mavros px4.launch fcu_url:="udp://:14540@127.0.0.1:14557"
```

成功标志：

```
[INFO] CON: Got HEARTBEAT, connected. FCU: PX4 Autopilot
```

> `roslaunch` 会自动启动 rosmaster，无需单独跑 `roscore`。

### 终端3 · 查看数据

```bash
source /opt/ros/noetic/setup.bash
rostopic echo /mavros/altitude
```

> **两条铁律**
> 1. 每个新终端第一句永远是 `source /opt/ros/noetic/setup.bash`
> 2. 跑着 `roslaunch` 的终端是"死的"，想敲命令必须再开一个

---

## 二、PX4 命令（终端1）

```
commander takeoff / land / arm / disarm      # 起飞 / 降落 / 解锁 / 上锁
listener sensor_combined                     # IMU 原始数据
listener vehicle_local_position              # 本地位置
listener vehicle_attitude                    # 姿态
param show MAV_0_CONFIG                      # 查看参数
```

---

## 三、ROS 话题速查（终端3）

```bash
rostopic list | grep mavros         # 列出话题
rostopic hz /mavros/imu/data        # 看实时频率
rostopic echo /mavros/altitude -n1  # 看单条数据
rosnode list                        # master 在不在
rqt_graph                           # 节点连接图
```

| 话题 | 实测频率 | 内容 |
|---|---|---|
| `/mavros/imu/data` | ~50 Hz | IMU（加计+陀螺+姿态） |
| `/mavros/imu/mag` | ~15 Hz | 磁力计 |
| `/mavros/imu/static_pressure` | ~17 Hz | 气压计 |
| `/mavros/altitude` | ~10 Hz | 高度 |
| `/mavros/local_position/pose` | ~30 Hz | 本地位置 x/y/z ⭐ |
| `/mavros/global_position/global` | ~51 Hz | GPS 经纬度 |
| `/mavros/state` | 1 Hz | 连接/解锁/模式 |
| `/mavros/battery` | 低频 | 电池（3 秒内可能抓不到，正常） |
| `/mavros/rc/in` | 无 | SITL 无遥控器，恒无数据（正常） |

**`/mavros/altitude` 字段**（单位：米）

| 字段 | 含义 |
|---|---|
| `local` | **相对起飞点高度** ⭐ 最常用 |
| `relative` | 相对高度（另一来源，与 local 略有差异） |
| `amsl` | 海拔高度 |
| `monotonic` | 单调高度，只增不减 |
| `terrain` / `bottom_clearance` | `nan` = 无此传感器（正常） |
| `header.seq` | 序号，持续递增 = 数据在流 |

**`/mavros/state` 字段**：`connected`（连上飞控）、`armed`（已解锁）、`mode`（飞行模式）。

---

## 四、关键参数

| 项 | 值 |
|---|---|
| MAVROS 连接串 | `udp://:14540@127.0.0.1:14557`（本地绑 14540，PX4 offboard 口 14580） |
| PX4 端口 | Offboard 14580↔14540，GCS 18570，载荷 14280↔14030，云台 13030↔13280 |
| 机型 / 世界 | `iris`（airframe 10015）/ `empty.world` |
| 预置数据流 | `ATTITUDE`、`LOCAL_POSITION_NED` 均 50 Hz |

> `px4.launch` 默认 `fcu_url` 是 `/dev/ttyACM0:57600`（真机串口），仿真必须覆盖。

---

## 五、常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| `Unable to communicate with master!` | MAVROS 没起 / 已退出 | 去终端2 启动 MAVROS |
| `rostopic: 未找到命令` | 新终端没 source | `source /opt/ros/noetic/setup.bash` |
| `/mavros/state` 显示 `connected: False` | MAVROS 没连上 PX4 | 检查 `fcu_url` 与终端1 是否在跑 |
| `/mavros/battery`、`rc/in` 无数据 | 低频 / 无遥控器 | 正常，无需处理 |
| `TM : Time jump detected` | 主机算力不足或系统时钟跳变 | 偶发可忽略；反复刷屏用 `HEADLESS=1` |
| `CMD: Unexpected command 520` | MAVROS 请求飞控能力 | 无害 |
| `Could not retrive ... parameter` | 插件参数未配置 | 无害 |
| Gazebo 黑屏/闪退 | OpenGL 问题 | `LIBGL_ALWAYS_SOFTWARE=1 gazebo` |

**自检**：`rosnode list` — 报 master 错误 = MAVROS 没起；列出节点 = 正常。

---

## 六、关闭与清理

```bash
pkill -f mavros_node      # 停 MAVROS
pkill -x gazebo           # 停 Gazebo
pkill -f "bin/px4"        # 停 PX4
```

---

## 七、已知限制

1. **默认机型无相机、无雷达** —— `iris` 只有 IMU/GPS/磁力计/气压计，项目所需传感器需自行加进模型 URDF/SDF。
2. **无 Gazebo ROS 桥** —— `make px4_sitl gazebo` 不给 Gazebo 加载 ROS 插件，故 `/gazebo/model_states`、`/clock` 不存在（`gzserver` 启动参数已实测确认）。
3. **`/mavros/*` 是 PX4 的 EKF 估计值，不是 Gazebo 物理真值**，评估误差必须用真值，两者不可混用。
4. **PX4 v1.14 的 `launch/*.launch` 面向 ROS 2**（`package.xml` 为 `ament_cmake`/`rclcpp`），Noetic 下无法直接 `roslaunch px4 ...`。

**后续工作**：① 自写 launch 打通 Gazebo 真值话题；② 改造 iris 模型加相机 + Ray 雷达（见 `design/雷达仿真配置.md`）；③ 建 catkin 工作区承载业务节点。
