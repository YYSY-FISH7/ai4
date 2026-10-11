# Python 代码移植到 ROS 平台方法整理

> 项目：《无人机多模态智能目标跟踪与制导》
> 环境基线：Ubuntu 20.04 + ROS Noetic + Python 3.8.10 + PX4 SITL + MAVROS
> 说明：本文档只整理「如何把 `code/` 下的纯逻辑代码搬上 ROS」的方法，不涉及具体落地代码的编写。

---

## 一、现状对齐

### 1.1 现有交付物（以 `cluster` 模块为例）

| 交付物 | 文件 | 状态 |
|---|---|---|
| 纯逻辑库 | `code/cluster.py`、`code/control_mux.py`、`code/state_machine.py` | 已有 |
| 数据类型 | `code/datatypes.py`（唯一入口，全项目共用） | 已有 |
| 阶段配置 | `code/config.py`（`UAV_STAGE`：`dev` / `onboard`） | 已有 |
| 单元测试 | `test/cluster/test_cluster.py`、`test/control_mux/test_control_mux.py` | 已有 |
| 可视化演示 | `code/cluster.ipynb`、`code/control_mux.ipynb`、`code/state_machine.ipynb` | 已有 |
| **ROS 节点壳** | —— | **缺失** |

### 1.2 关键判断

`code/` 下的 `.py` 是**刻意的「无 ROS 纯逻辑」**（`cluster.py` 开头注释明确写了「本模块只提供纯函数与数据类，**不涉及 ROS 节点**」）。

因此，正确做法**不是**去修改这些代码让它「支持 ROS」，而是**在外面加一层节点壳**：

> **核（算法）不动，壳（搬运）新增。**

这样已有的单测与 notebook 全部继续有效，算法逻辑与通信框架彻底解耦。

---

## 二、总体思路：壳 / 核分离

```
     /radar/points                 ┌──────────────────────────────┐
     (PointCloud2)  ──────────────▶│  node 壳  cluster_node.py     │
                                   │  （只做搬运，不含算法）        │
                                   └──────────────┬───────────────┘
                                                  │ 拆包 read_points
                                                  ▼
                                          list[Point3D]
                                                  │ 调用
                                                  ▼
                                   ┌──────────────────────────────┐
                                   │  纯逻辑（cluster.py 零改动）   │
                                   │  filter_ground → dbscan_cluster│
                                   └──────────────┬───────────────┘
                                                  │ list[Cluster]
                                                  ▼
     /radar/centroid   ◀──────────────  装包 CentroidArray
     (CentroidArray)
```

节点壳只做四件事：

1. **订阅**输入话题，回调触发；
2. **拆包**：ROS 消息 → 项目自定义数据类型；
3. **调用**纯函数（算法唯一发生的地方）；
4. **装包发布**：项目自定义数据类型 → ROS 消息。

---

## 三、工作空间与功能包规划（方案 B）

### 3.1 先建 catkin 工作空间

「工作空间」与「功能包」是两个概念：工作空间是承载一切的大文件夹，功能包是里面的具体模块。

| 概念 | 英文 | 是什么 | 位置 |
|---|---|---|---|
| 工作空间 | workspace | 装所有开发内容的文件夹 | `~/catkin_ws/` |
| 功能包 | package | 一个具体模块 | `~/catkin_ws/src/<pkg>/` |

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws && catkin_make        # 必须在工作空间根目录执行
source ~/catkin_ws/devel/setup.bash  # 每个新终端都要执行
```

> 成功标志：`~/catkin_ws/` 下出现 `build/`、`devel/` 两个目录。
> 已有单测 / notebook 不受影响；工作空间只承载 ROS 节点壳、消息与仿真资源。

### 3.2 功能包划分（方案 B：按分工拆包）

依据《无人机项目实施拆解文档》第五章（「仿真环境」为独立分工），拆为三个包：

| 包 | 职责 | 内容 |
|---|---|---|
| `uav_tracking` | 业务（制导 + 控制） | 自定义消息、8 个节点壳、纯逻辑库 `lib/` |
| `uav_sim` | 仿真环境 | Gazebo 世界、雷达 / 相机插件配置、launch |
| `uav_description` | 模型描述 | iris 改造件、地基雷达 URDF / SDF、meshes |

好处：改仿真不动业务代码；分工到人时边界清晰；`uav_sim` 可 `include` 其他包的资源。

> 单包方案（全部塞进 `uav_tracking`）也能跑，但既然仿真为独立分工，**本项目采用方案 B**。

### 3.3 各包目录结构

```
~/catkin_ws/src/
├── uav_tracking/              # 业务包
│   ├── package.xml
│   ├── CMakeLists.txt
│   ├── msg/                   # 自定义消息（CentroidArray / TrackArray / ...）
│   ├── scripts/
│   │   ├── cluster_node.py    # ← 节点壳（新增）
│   │   └── fake_radar.py      # ← 假点云源（无雷达时联调用）
│   ├── lib/                   # ← code/ 下的纯逻辑搬过来
│   │   ├── config.py  datatypes.py
│   │   ├── cluster.py  control_mux.py  state_machine.py
│   ├── launch/                # cluster.launch / tracking.launch / ...
│   ├── config/                # 参数 yaml
│   └── rviz/                  # 可视化配置
│
├── uav_sim/                   # 仿真包
│   ├── package.xml
│   ├── CMakeLists.txt
│   ├── worlds/                # .world（空世界 / 含敌机）
│   ├── launch/                # radar_world.launch / full_system.launch
│   └── config/                # 传感器插件参数
│
└── uav_description/           # 模型包
    ├── package.xml
    ├── CMakeLists.txt
    ├── urdf/                  # iris 改造件、传感器 link
    ├── models/                # 敌机 / 地基雷达模型
    └── meshes/                # .stl / .dae
```

**`lib/` 设计理由**：保持现有「顶层 import」风格（`from config import ...`、`from datatypes import ...`）。节点壳运行时把 `lib/` 加入 `sys.path` 即可，**无需改动任何一行现有库代码，也无需改动单测**。

### 3.4 `catkin_make` 与 `build/` `devel/` 的作用

**`catkin_make` 是什么**：把 `src/` 里的「原料」加工成 ROS 能用的「成品」的工具。

| 位置 | 比喻 | 装什么 |
|---|---|---|
| `src/` | 车间原料 | 手写的 `.py`、`.msg`、`.launch`、`.cpp` |
| `catkin_make` | 加工机器 | 编译 / 生成，跑一遍 |
| `build/` | 半成品箱 | 编译中间产物（Makefile、`.o` 等） |
| `devel/` | 成品仓库 | 加工好的东西 + 环境脚本 |

**它对项目具体做的 4 件事**：

1. **扫描 `src/`**：发现所有功能包；
2. **解析 `package.xml` + `CMakeLists.txt`**：确定依赖关系、排出拓扑顺序（如 `uav_description → uav_sim → uav_tracking`）；
3. **生成自定义消息代码**（★ 本项目必须用 catkin 的原因）：`.msg` 文件本身 ROS 不认识，需翻译成 Python 类 / C++ 头文件，节点才能 `from uav_tracking.msg import CentroidArray`；
4. **把成品放进 `devel/`**。

**`build/` 与 `devel/`**：

```
catkin_ws/
├── src/      ← 手写内容（真正要纳入版本管理的）
├── build/    ← CMake 中间缓存 + Makefile（可删，重编即重建）
└── devel/    ← 加工结果（开发空间）
    ├── setup.bash                    ← source 它，包才「被系统看见」
    └── lib/python3/dist-packages/... ← 生成的消息类、库
```

- `build/`：临时文件，可随意删除，删后重新 `catkin_make` 会重建；
- `devel/`：开发空间，内容为软链接 / 生成物，`devel/setup.bash` 负责把包路径写入 `ROS_PACKAGE_PATH`、`PYTHONPATH`。

**为什么必须 `source devel/setup.bash`**：`catkin_make` 编完 ≠ ROS 认识它。只有 source 之后，`rospack` / `rosrun` / `roslaunch` 才知道工作区里的包。

```bash
source /opt/ros/noetic/setup.bash      # 认识 ROS 本体
source ~/catkin_ws/devel/setup.bash    # 认识自己的包
rospack list | grep uav                # 未 source 时报 package not found
```

**何时需要重跑 `catkin_make`**：

| 操作 | 要重跑吗 |
|---|---|
| 改 `.msg`（新增 / 改字段） | **必须**（需重新生成消息类） |
| 改 `CMakeLists.txt` / `package.xml` | **必须** |
| 新增一个功能包 | **必须** |
| 新增 / 修改 `.py` 节点内容 | **不用**（`devel/` 中为软链，`rosrun` 即最新代码） |
| 新增 `.py` 脚本文件本身 | 一般不用，但要 `chmod +x` |
| 改 `.launch` / `.world` / `.urdf` | **不用**（`roslaunch` 每次现读） |

> 结论：Python 节点开发无需频繁重编译，**只有动消息 / 构建配置才需 `catkin_make`**。

**补充**：`catkin_make install` 会把成品安装到 `install/`，用于部署到其他机器；开发阶段一律使用 `devel/`，两者不可混用。

---

## 四、消息定义

`msg/CentroidArray.msg`（照搬《无人机项目实施拆解文档》第二章）：

```
geometry_msgs/PointStamped[] centroids
```

其余模块所需的 `TrackArray.msg`、`Detections.msg`、`VisualTrackArray.msg` 同理，在 `msg/` 目录下一并定义。

---

## 五、节点壳（以 `/cluster` 为例）

> 说明：以下为**方法示意**，用于说明「壳」的写法与职责边界；实际落地时以此为模板。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/cluster 节点壳：PointCloud2 → 滤地+DBSCAN → CentroidArray。

纯逻辑住在 cluster.py，本节点只做搬运，不含算法。
"""
from __future__ import annotations

import os
import sys

import rospy
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import PointStamped

# 把 lib/ 加入 import 路径（纯逻辑与壳解耦）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

from cluster import filter_ground, dbscan_cluster   # 纯逻辑，零改动
from datatypes import Point3D
from uav_tracking.msg import CentroidArray          # 自定义消息


class ClusterNode:
    def __init__(self):
        # 算法参数一律走 rosparam（launch 可调，不写死）
        self.z_thresh    = rospy.get_param("~z_thresh", 0.3)
        self.eps         = rospy.get_param("~eps", 0.5)
        self.min_samples = rospy.get_param("~min_samples", 5)

        self.pub = rospy.Publisher("/radar/centroid", CentroidArray, queue_size=1)
        # 点云体积大、旧帧无意义：queue_size=1 只保最新
        rospy.Subscriber("/radar/points", PointCloud2, self.on_points, queue_size=1)
        rospy.loginfo("[cluster] ready: eps=%.2f min_samples=%d z_thresh=%.2f",
                      self.eps, self.min_samples, self.z_thresh)

    # ---- 事件层：收到一帧点云处理一帧（本模块无定时器）----
    def on_points(self, msg):
        # 1) ROS 消息 → 纯数据类型
        #    若雷达点云无 intensity 字段，改为 field_names=("x","y","z") 且 intensity 补 0
        points = [
            Point3D(x, y, z, i)
            for x, y, z, i in pc2.read_points(
                msg, field_names=("x", "y", "z", "intensity"), skip_nans=True)
        ]
        # 2) 调纯逻辑 —— 这一行才是"算法"，其余全是搬运
        clusters = dbscan_cluster(
            filter_ground(points, self.z_thresh), self.eps, self.min_samples)
        # 3) 纯数据 → ROS 消息（空 clusters 也发，即"空也发"约定）
        self.pub.publish(self._to_msg(clusters, msg.header))

    @staticmethod
    def _to_msg(clusters, header):
        out = CentroidArray()
        for c in clusters:
            ps = PointStamped()
            ps.header = header                       # 继承点云时间戳/坐标系
            ps.point.x, ps.point.y, ps.point.z = c.centroid
            out.centroids.append(ps)
        return out


if __name__ == "__main__":
    rospy.init_node("cluster")
    ClusterNode()
    rospy.spin()          # 回调驱动，不用写 while 循环
```

**该壳贯彻的设计约定**：

- **空也发**：无簇时发布空 `CentroidArray`，保证「空 = 没目标（业务正常）、静默 = 故障」语义成立（设计原则第 5 条）；
- **参数外置**：算法参数走 `rosparam`，不写死；
- **队列策略**：传感器大消息 `queue_size=1`，只保最新帧。

---

## 六、构建配置

### 6.1 `CMakeLists.txt` 关键段（以业务包 `uav_tracking` 为例）

```cmake
find_package(catkin REQUIRED COMPONENTS
  rospy std_msgs sensor_msgs geometry_msgs mavros_msgs message_generation)

add_message_files(FILES CentroidArray.msg)   # 其余 msg 同理
generate_messages(DEPENDENCIES geometry_msgs std_msgs)

catkin_package(CATKIN_DEPENDS
  rospy std_msgs sensor_msgs geometry_msgs mavros_msgs message_runtime)
```

### 6.2 `package.xml` 依赖

业务包 `uav_tracking`：

```xml
<build_depend>message_generation</build_depend>
<exec_depend>message_runtime</exec_depend>
<exec_depend>rospy</exec_depend>
<exec_depend>std_msgs</exec_depend>
<exec_depend>sensor_msgs</exec_depend>
<exec_depend>geometry_msgs</exec_depend>
<exec_depend>mavros_msgs</exec_depend>
```

仿真包 `uav_sim` / 模型包 `uav_description` 额外依赖（并在 `find_package` 中加 `gazebo_ros xacro`）：

```xml
<exec_depend>gazebo_ros</exec_depend>
<exec_depend>gazebo_plugins</exec_depend>
<exec_depend>xacro</exec_depend>
<exec_depend>robot_state_publisher</exec_depend>
```

### 6.3 资源目录必须 install（关键坑）

catkin **只自动处理源码**；`world / urdf / mesh / launch` 等资源必须显式声明安装，否则 `roslaunch` 会报 `cannot find ...`：

```cmake
# 按各包实际拥有的目录书写，不存在的目录删掉
install(DIRECTORY launch worlds models urdf meshes rviz config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
```

之后即可用 `$(find uav_sim)/worlds/xxx.world` 方式引用资源。

### 6.4 launch 分层

```
uav_sim/launch/radar_world.launch      # 起 Gazebo + 雷达世界 + Ray 插件
uav_tracking/launch/cluster.launch     # 只起 /cluster
uav_tracking/launch/tracking.launch    # /cluster + /tracker + /navigator + /control_mux
uav_sim/launch/full_system.launch      # include 上面全部 + MAVROS
```

用 `<include file="$(find uav_tracking)/launch/cluster.launch"/>` 组合，避免一份 launch 塞到底。

示例 `uav_tracking/launch/cluster.launch`：

```xml
<launch>
  <env name="UAV_STAGE" value="dev"/>   <!-- dev 报错 / onboard 兜底 -->
  <node pkg="uav_tracking" type="cluster_node.py" name="cluster" output="screen">
    <param name="z_thresh"    value="0.3"/>
    <param name="eps"         value="0.5"/>
    <param name="min_samples" value="5"/>
  </node>
</launch>
```

---

## 七、编译、运行与自测

> 下文以本机实际布局为准：工作区位于**仓库根下的 `catkin_ws/`**（即 `<仓库根>/catkin_ws/devel/setup.bash`）。

### 7.1 编译与手动运行

```bash
source /opt/ros/noetic/setup.bash
cd catkin_ws && catkin_make && source devel/setup.bash
chmod +x src/uav_tracking/scripts/*.py

# 当前 iris 机型没有雷达（见《ROS+MAVROS+Gazebo 全链路打通使用文档》第七节已知限制），
# 用假点云源联调（数据源见 7.3）：
python3 test/cluster/e2e_test/fake_radar.py
rosrun uav_tracking cluster_node.py _eps:=0.5 _min_samples:=5

# 另开终端验证
rostopic hz   /radar/centroid
rostopic echo /radar/centroid -n1
```

### 7.2 单元测试（pytest）

```bash
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash     # 节点壳测试需能 import uav_tracking.msg
cd <仓库根>
python3 -m pytest test/ -q
```

| 测试文件 | 覆盖范围 |
|---|---|
| `test/cluster/test_cluster.py` | 纯逻辑：`filter_ground` / `dbscan_cluster`（含 dev/onboard 两阶段） |
| `test/cluster/test_cluster_node.py` | 节点壳转换：`cloud_to_points` / `clusters_to_centroid_array`（含「空也发」、header 继承） |

> `test_cluster_node.py` 依赖 ROS（`rospy` + 生成的 `uav_tracking.msg`）；未 source 时该文件**整体自动跳过**，不影响纯逻辑测试。

### 7.3 端到端（E2E）全链路测试

用一个可重复运行的脚本，把「消息生成 → 节点壳 → 话题 → 下游」整条链路一次性验穿。

**拓扑**

```
                ┌──────────┐
                │ roscore  │  (master)
                └────┬─────┘
      ┌──────────────┼───────────────────┐
      ▼              ▼                   ▼
fake_radar.py   cluster_node.py    check_centroid.py
 (数据源)  ──/radar/points──▶ (被测节点) ──/radar/centroid──▶ (断言)
```

**文件（`test/cluster/e2e_test/`）**

| 文件 | 作用 |
|---|---|
| `fake_radar.py` | 假雷达源：按参数发 `/radar/points`（`~with_target` / `~x/~y/~z` / `~rate` / `~seed`） |
| `check_centroid.py` | 断言节点：订阅 `/radar/centroid`，按 `~mode=target/empty` 校验并返回退出码 |
| `run_e2e.sh` | 一键编排：roscore → cluster_node → 两阶段 fake_radar + 断言 → `trap` 清理 |
| `logs/` | 运行时日志（roscore / cluster / fake_radar 各一份） |

**两阶段验证**

| 阶段 | 数据源 | 断言 | 证明 |
|---|---|---|---|
| A 有目标 | 地面杂波 + 固定目标簇 `(8, 3, 2)` | 质心唯一、≈ 真值（< 0.3 m）、`frame=map` | 转换 / 算法 / 发布数值全对 |
| B 无目标 | 仅地面杂波（`~with_target:=false`） | 话题仍在流、数组长度为 0 | 「空也发」契约成立 |

**运行**

```bash
bash test/cluster/e2e_test/run_e2e.sh
```

**实测结果**

```
[check] mode=target 收到 60 条 /radar/centroid（期望 >= 20）
[check] 质心 = (7.955, 2.986, 2.048)  真值 = (8.0, 3.0, 2.0)  偏差 = 0.067 m
PASS: target 阶段 —— 数据流正常且质心与真值一致（frame=map）
PASS: empty 阶段 —— 话题在流且数组为空（空也发成立）
E2E RESULT: PASS  (A=0, B=0)
```

> 脚本对 roscore 做**复用检测**，并以 `trap EXIT` 收尾——正常 / 异常退出都会清理后端进程，不残留。
> 断言阈值（`~tol` / `~duration` / `~min_msgs`）与目标真值（`~x/~y/~z`）均可通过命令行传参覆盖。

---

## 八、推广到 8 个模块

| 节点 | 输入话题 | 纯函数 | 输出话题 | 驱动方式 |
|---|---|---|---|---|
| `/cluster` | `/radar/points` | `filter_ground` + `dbscan_cluster` | `/radar/centroid` | 事件 |
| `/tracker` | `/radar/centroid` | `KalmanTracker.*` | `/radar/tracks` | 事件 |
| `/navigator` | `/radar/tracks`、`/mavros/local_position/pose` | `on_timer` | `/ctrl/radar` | **Timer 20-50 Hz** |
| `/detector` | `/camera/image_raw` | `detect` | `/detections` | 事件 |
| `/visual_tracker` | `/detections` | `track` | `/visual/tracks` | 事件 |
| `/pid_controller` | `/visual/tracks` | `on_timer` | `/ctrl/visual` | **Timer 20-50 Hz** |
| `/state_machine` | `/detections`、`/visual/tracks`、`/radar/tracks` | `evaluate_*` + `transition` | `/state` | 事件（按变化发） |
| `/control_mux` | `/state`、`/ctrl/radar`、`/ctrl/visual` | `ControlMux` | `/mavros/setpoint_raw/local` | 事件 |

### 8.1 关键设计：跨帧状态放节点，纯函数保持无状态

纯函数**无状态**（只管单帧 / 单步），**跨帧状态放在节点对象的成员变量里**：

| 节点 | 需要持有的跨帧状态 |
|---|---|
| `/tracker` | `KalmanTracker` 实例（航迹集合） |
| `/visual_tracker` | BoT-SORT / SORT 跟踪器实例 |
| `/state_machine` | 当前状态 + N/M/K `counters` 字典 |
| `/navigator` | `last_cmd`、`current_pose` 缓存、「上次非空」时间戳 |
| `/pid_controller` | `last_cmd`、「上次非空」时间戳 |
| `/control_mux` | 最近一次 `/state`、每路最新一条指令缓存 |

### 8.2 定时器型节点的写法

`/navigator`、`/pid_controller` 必须以 20-50 Hz 定频发布（OFFBOARD 硬性要求），用 `rospy.Timer`：

```python
rospy.Timer(rospy.Duration(1.0 / 50.0), self.on_timer)   # 50 Hz
# on_timer 里：读缓存 + 算 valid_age + 调 navigator.on_timer(...) → 发布
```

---

## 九、环境注意事项

| 坑 | 说明 |
|---|---|
| **必须用系统 `python3.8`** | ROS Noetic 的 `rospy` 装在 `/usr/bin/python3`。节点不要用 conda / venv 运行，否则 `import rospy` 直接失败 |
| **sklearn 要装进系统 python** | `pip3 install -r requirements.txt`（受管环境加 `--user`）。`sklearn==1.3.2` 与系统 `numpy 1.17.4`、`scipy 1.8.1` 兼容，`requirements.txt` 无问题 |
| ⚠️ **notebook 内核 ≠ ROS 解释器** | IDE 默认内核是 venv `python3.12`，**无法 import ROS**（`No module named 'rospkg'`）。已在 `~/.local/share/jupyter/kernels/ros_py38/` 注册内核 **「ROS Noetic (Py3.8)」**（指向系统 `/usr/bin/python3`，并预置 ROS + devel 的 `PYTHONPATH`）；跑 ROS notebook 时在内核选择器里选它即可 |
| 示例 notebook | `code/cluster_node.ipynb` 演示节点壳的消息转换；运行前需选上面注册的 ROS 内核 |
| source 顺序 | 先 `/opt/ros/noetic/setup.bash`，再 `<仓库根>/catkin_ws/devel/setup.bash`；每个新终端都要 |
| 阶段开关 | `dev` 抛错 / `onboard` 兜底，靠 `UAV_STAGE` 环境变量；launch 里用 `<env>` 注入 |
| 队列与频率 | 传感器大消息 `queue_size=1`；决策端 setpoint 话题下游只看最新，`queue_size=1` 亦可 |
| 线程安全 | `rospy` 默认单线程 spinner，回调串行执行，简单变量缓存即安全，无需加锁 |

---

## 十、与 Gazebo / PX4 的衔接

雷达方案（见 `design/雷达仿真配置.md`）依赖插件 `libgazebo_ros_ray_sensor.so`——**这是 Gazebo 的 ROS 插件**。

⚠️ **已知限制**：《ROS+MAVROS+Gazebo 全链路打通使用文档》第七节第 2 条指出，`make px4_sitl gazebo` 启动的 Gazebo **不加载 ROS 插件**，因此 `/gazebo/model_states`、`/clock` 不存在，**按此方式启动也装不了雷达插件**。

后续需改造启动方式（两种，产物均落在 `uav_sim` 包内）：

1. 由 `roslaunch`（`gazebo_ros`）启动带 ROS 插件的 Gazebo，再让 PX4 SITL 接入；
2. 或继续用 `make px4_sitl`，通过 `PX4_SITL_WORLD` 环境变量指定自定义世界，并确认其 `gzserver` 能加载 ROS 插件。

> 对应《全链路打通使用文档》「后续工作① 自写 launch、② 改造 iris 加相机 + 雷达」，产物分属 `uav_sim` 与 `uav_description` 两包。

---

## 十一、待办清单（后续落地）

1. 建 catkin 工作空间 `~/catkin_ws`；
2. 按方案 B 建三个包：`uav_tracking` / `uav_sim` / `uav_description`；
3. `uav_tracking`：定义 4 个自定义消息（`msg/`）；
4. `uav_tracking`：迁移纯逻辑到 `lib/`，新增 8 个节点壳（`scripts/`）；
5. 各包补 `package.xml` / `CMakeLists.txt`（含 `install(DIRECTORY ...)`）；
6. `uav_sim`：编写分层 `launch/` 与 `worlds/`；
7. `uav_description`：改造 iris 模型加相机 + Ray 雷达，加地基雷达模型；
8. 无雷达阶段先用 `fake_radar.py` 打通 `/cluster`；
9. 依次打通 `/tracker` → `/navigator` → `/control_mux`，接入 MAVROS 与 Gazebo。
