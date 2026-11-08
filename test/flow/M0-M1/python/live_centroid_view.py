#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0-M1 小联调：实时查看 ``/cluster`` 的聚类结果（world 三维散点）。

数据来源
--------
- ``/radar/centroid``（``uav_tracking/CentroidArray``）：每帧的聚类质心，
  坐标在 ``world`` 下（x 东、y 北、z 上，与 Gazebo 世界系一致）；
- 可选 ``/radar/points``：原始点云，同为 ``world``，降采样后叠加，用于核对
  质心是否落在点簇上；
- 可选 ``/target/ground_truth/pose``：目标真值，本身就在 ``world``，直接叠加。

三个话题同属世界系，脚本内不做任何坐标变换。收到非 ``world`` 数据时（例如
``ray_cloud_bridge`` 的世界坐标改造尚未编译生效），质心整帧会被拒绝、画面清空
并在标题中提示，避免画出参照错误的图。

用法
----
M0 使用独立 ROS master（端口随机），启动后先记下它打印的运行目录。M0 与 M1
分别在另外的终端启动，本脚本只订阅、不启动任何节点：

.. code-block:: bash

    source /opt/ros/noetic/setup.bash
    source catkin_ws/devel/setup.bash
    source data/radar/<run_dir>/connection.bash
    /usr/bin/python3 test/flow/M0-M1/python/live_centroid_view.py

常用参数::

    --duration 30            跑 30 秒后自动退出（0 = 一直跑到 Ctrl+C）
    --with-cloud             叠加降采样后的原始点云
    --show-truth             叠加目标真值（橙色星）
    --save out.png           退出前保存最后画面
    --xlim -2 12 --ylim -8 8 --zlim -1 4

注意
----
- 必须用系统 ``/usr/bin/python3``（ROS Noetic 的 rospy 装在系统 Python 下）；
- ``use_sim_time`` 为 true 时 ``rospy.Time.now()`` 是仿真时间，本脚本的频率与
  超时一律用 ``time.monotonic()``（墙钟）；
- 订阅回调放在独立线程，只缓存最新帧；绘图在主线程完成，避免阻塞 rospy 回调；
- matplotlib 3D 渲染约 0.3 s/帧，实测接收约 3 Hz，这是显示端上限，不代表 M1 的
  输出频率（M1 稳定 5 Hz）。只看最新结果时该频率足够。
"""
from __future__ import annotations

import argparse
import threading
import time

import matplotlib

try:  # 优先 Tk：Qt5Agg 在部分 PyQt5 版本上初始化较慢
    import tkinter  # noqa: F401

    matplotlib.use("TkAgg")
except Exception:  # pragma: no cover - 环境相关
    matplotlib.use("Qt5Agg")

import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: E402,F401  注册 3d 投影（matplotlib<3.2 必需）
import numpy as np  # noqa: E402
import rospy  # noqa: E402
import sensor_msgs.point_cloud2 as pc2  # noqa: E402
from geometry_msgs.msg import PoseStamped  # noqa: E402
from sensor_msgs.msg import PointCloud2  # noqa: E402

from uav_tracking.msg import CentroidArray  # noqa: E402


def require_world(frame_id, kind):
    """拒绝非世界系数据，避免数据源改造未生效时画出参照错误的图。"""
    if frame_id != "world":
        raise ValueError(
            "%s frame is %r, expected 'world'; "
            "ray_cloud_bridge world transform not compiled or not active"
            % (kind, frame_id))


class LiveCentroidView:
    """订阅聚类质心并在 matplotlib 3D 轴里实时重绘。"""

    def __init__(self, args):
        self.args = args
        self.latest = None  # (stamp_s, [(x, y, z), ...])
        self.latest_cloud = None  # (N, 3) ndarray，world
        self.truth = None  # (x, y, z)，world
        self.error = ""  # 质心帧的拒绝原因；非空时标题改为提示
        self.frames = 0
        self.t_first = None
        self.t_last = None

        rospy.Subscriber(
            "/radar/centroid", CentroidArray, self.on_centroid, queue_size=1)
        if args.with_cloud:
            rospy.Subscriber(
                "/radar/points", PointCloud2, self.on_cloud, queue_size=1)
        if args.show_truth:
            rospy.Subscriber(
                "/target/ground_truth/pose", PoseStamped, self.on_target,
                queue_size=1)

    # ---- 事件层：只缓存最新值，不做任何绘图 ----
    def on_centroid(self, msg):
        try:
            if msg.centroids:
                # CentroidArray 外层没有 header，frame 与时间戳取首个元素。
                first = msg.centroids[0]
                require_world(first.header.frame_id, "/radar/centroid")
                stamps = {p.header.stamp.to_nsec() for p in msg.centroids}
                if len(stamps) > 1:
                    raise ValueError(
                        "/radar/centroid frame mixes acquisition stamps")
                stamp = first.header.stamp.to_sec()
            else:
                stamp = 0.0  # 空数组无 header，按「空也发」约定正常接收
            self.latest = (
                stamp,
                [(p.point.x, p.point.y, p.point.z) for p in msg.centroids],
            )
            self.error = ""
        except ValueError as exc:
            self.latest = (0.0, [])
            self.error = str(exc)

        now = time.monotonic()
        if self.t_first is None:
            self.t_first = now
        self.t_last = now
        self.frames += 1

    def on_cloud(self, msg):
        try:
            require_world(msg.header.frame_id, "/radar/points")
        except ValueError as exc:
            self.latest_cloud = np.empty((0, 3))
            rospy.logerr_throttle(2, str(exc))
            return
        rows = pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)
        cloud = np.asarray(list(rows), dtype=float)
        if cloud.size == 0:
            self.latest_cloud = np.empty((0, 3))
            return
        limit = self.args.max_cloud_points
        if len(cloud) > limit:
            idx = np.random.choice(len(cloud), limit, replace=False)
            cloud = cloud[idx]
        self.latest_cloud = cloud

    def on_target(self, msg):
        try:
            require_world(msg.header.frame_id, "/target/ground_truth/pose")
        except ValueError as exc:
            self.truth = None
            rospy.logerr_throttle(2, str(exc))
            return
        point = msg.pose.position
        self.truth = (point.x, point.y, point.z)

    # ---- 统计 ----
    def rate_hz(self):
        if self.t_first is None or self.t_last is None:
            return 0.0
        span = self.t_last - self.t_first
        return self.frames / span if span > 0 else 0.0

    # ---- 主循环：新帧驱动重绘 ----
    def run(self):
        plt.ion()
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
        ax.set_xlabel("world X (m)")
        ax.set_ylabel("world Y (m)")
        ax.set_zlabel("world Z (m)")
        ax.set_xlim(*self.args.xlim)
        ax.set_ylim(*self.args.ylim)
        ax.set_zlim(*self.args.zlim)
        ax.grid(True)

        centroid_scatter = ax.scatter(
            [0.0], [0.0], [0.0], c="red", s=60, depthshade=False,
            label="centroid")
        cloud_scatter = None
        if self.args.with_cloud:
            cloud_scatter = ax.scatter(
                [0.0], [0.0], [0.0], c="gray", s=1, alpha=0.3,
                depthshade=False, label="raw points")
        truth_scatter = None
        if self.args.show_truth:
            truth_scatter = ax.scatter(
                [0.0], [0.0], [0.0], c="orange", marker="*", s=220,
                depthshade=False, label="target truth")
        ax.legend(loc="upper right")
        title_artist = fig.suptitle("waiting for /radar/centroid ...")
        # 必须显式 show 一次：TkAgg 下不调用时窗口保持 1x1 的未映射状态。
        fig.show()

        deadline = (
            time.monotonic() + self.args.duration
            if self.args.duration > 0 else None
        )
        rospy.loginfo(
            "[live_view] ready: world frame required; cloud=%s truth=%s duration=%s",
            self.args.with_cloud, self.args.show_truth, self.args.duration)

        try:
            last_drawn = -1
            while not rospy.is_shutdown():
                if deadline is not None and time.monotonic() > deadline:
                    break
                # 只在收到新帧时重绘，避免空转重绘拖慢订阅。
                if self.latest is not None and self.frames != last_drawn:
                    stamp, points = self.latest
                    if points:
                        xs, ys, zs = zip(*points)
                        centroid_scatter._offsets3d = (xs, ys, zs)
                    else:
                        centroid_scatter._offsets3d = ([], [], [])
                    if cloud_scatter is not None and self.latest_cloud is not None:
                        cloud = self.latest_cloud
                        if len(cloud):
                            cloud_scatter._offsets3d = (
                                cloud[:, 0], cloud[:, 1], cloud[:, 2])
                        else:
                            cloud_scatter._offsets3d = ([], [], [])
                    if truth_scatter is not None:
                        if self.truth is None:
                            truth_scatter._offsets3d = ([], [], [])
                        else:
                            truth_scatter._offsets3d = (
                                [self.truth[0]], [self.truth[1]],
                                [self.truth[2]])
                    if self.error:
                        title_artist.set_text("DATA REJECTED: " + self.error)
                    else:
                        title_artist.set_text(
                            "recv %d frames | sim %.2fs | %d centroids"
                            % (self.frames, stamp, len(points)))
                    fig.canvas.draw_idle()
                    last_drawn = self.frames
                fig.canvas.flush_events()
                time.sleep(0.05)
        finally:
            if self.args.save:
                fig.savefig(self.args.save, dpi=150)
                print("[live_view] saved %s (recv %d frames, %.1f Hz)"
                      % (self.args.save, self.frames, self.rate_hz()))
            plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(
        description="实时显示 /radar/centroid 的三维聚类结果（world 系）")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="运行秒数，0 表示直到 Ctrl+C")
    parser.add_argument("--with-cloud", action="store_true",
                        help="叠加降采样后的原始点云（world）")
    parser.add_argument("--show-truth", action="store_true",
                        help="叠加目标真值（world，需 /target/ground_truth/pose）")
    parser.add_argument("--max-cloud-points", type=int, default=500,
                        help="点云叠加时的最大点数")
    parser.add_argument("--save", default="",
                        help="退出前保存图片的路径")
    parser.add_argument("--xlim", nargs=2, type=float, default=[-2.0, 12.0])
    parser.add_argument("--ylim", nargs=2, type=float, default=[-8.0, 8.0])
    parser.add_argument("--zlim", nargs=2, type=float, default=[-1.0, 4.0])
    return parser.parse_args()


def main():
    args = parse_args()
    rospy.init_node("live_centroid_view", anonymous=True, disable_signals=False)
    view = LiveCentroidView(args)
    # 回调放在独立线程，避免 matplotlib 渲染阻塞订阅、造成丢帧。
    threading.Thread(target=rospy.spin, daemon=True).start()
    view.run()


if __name__ == "__main__":
    main()
