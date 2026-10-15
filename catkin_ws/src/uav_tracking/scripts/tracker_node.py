#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``/tracker`` 节点壳：``CentroidArray`` -> ``TrackArray``。

纯算法位于 ``lib/tracker.py``（指向 ``code/tracker.py`` 的软链接），本文件只
负责 ROS 订阅/发布、消息转换和时间处理。预测 ``dt`` 只使用相邻回调的 ROS
接收时间；消息时间戳仅作为量测更新时间传入算法。节点不连接飞控控制话题。
"""
from __future__ import annotations

import os
import sys

import rospy

from uav_tracking.msg import CentroidArray, Track as TrackMsg, TrackArray

# ``lib/`` 内为指向 ``code/`` 的软链接，避免节点维护第二份算法实现。
_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from config import (  # noqa: E402
    TRACKER_ASSOCIATION_THRESHOLD,
    TRACKER_INITIAL_COVARIANCE,
    TRACKER_MAX_MISSED_FRAMES,
    TRACKER_MEASUREMENT_NOISE,
    TRACKER_PROCESS_NOISE,
    TRACKER_RATE_HZ,
)
from tracker import KalmanTracker, track_state_to_track  # noqa: E402

__all__ = [
    "centroids_from_msg",
    "tracks_to_msg",
    "stamp_to_seconds",
    "TrackerNode",
]

TOPIC_CENTROIDS = "/radar/centroid"
TOPIC_TRACKS = "/radar/tracks"
QUEUE_SIZE = 1


def centroids_from_msg(msg):
    """将 ``CentroidArray`` 转为纯算法使用的 ``list[np.ndarray]``。"""
    import numpy as np

    return [
        np.array([float(point.point.x), float(point.point.y), float(point.point.z)])
        for point in msg.centroids
    ]


def tracks_to_msg(tracks):
    """将纯算法 ``Track`` 列表转换为 ``TrackArray``。

    该节点只负责纯 ``Track`` 到 ROS ``Track.msg`` 的装包；空列表照常返回
    空消息。
    """
    out = TrackArray()
    for track in tracks:
        item = TrackMsg()
        item.id = int(track.id)
        item.position = [float(value) for value in track.position]
        item.velocity = [float(value) for value in track.velocity]
        item.covariance = [float(value) for value in track.covariance]
        item.age = int(track.age)
        out.tracks.append(item)
    return out


def stamp_to_seconds(msg):
    """读取量测时间戳；``CentroidArray`` 从首个点的 header 取值。

    当前 ``CentroidArray.msg`` 没有顶层 header，数组元素是 ``PointStamped``；
    因此空数组或零时间戳时返回 ``None``。该值只记录量测更新时间，不参与
    预测 ``dt`` 计算。
    """
    headers = []
    top_header = getattr(msg, "header", None)
    if top_header is not None:
        headers.append(top_header)
    headers.extend(
        getattr(point, "header", None)
        for point in getattr(msg, "centroids", [])
    )
    for header in headers:
        stamp = getattr(header, "stamp", None)
        if stamp is None:
            continue
        seconds = float(stamp.to_sec())
        if seconds > 0.0:
            return seconds
    return None


class TrackerNode:
    """雷达质心事件驱动的航迹节点。"""

    def __init__(self):
        # 默认值统一来自 config，rosparam 仅用于部署时覆盖。
        self.rate_hz = float(rospy.get_param("~rate_hz", TRACKER_RATE_HZ))
        self.default_dt = 1.0 / self.rate_hz
        self.tracker = KalmanTracker(
            association_threshold=rospy.get_param(
                "~association_threshold", TRACKER_ASSOCIATION_THRESHOLD
            ),
            max_missed_frames=rospy.get_param(
                "~max_missed_frames", TRACKER_MAX_MISSED_FRAMES
            ),
            process_noise=rospy.get_param("~process_noise", TRACKER_PROCESS_NOISE),
            measurement_noise=rospy.get_param(
                "~measurement_noise", TRACKER_MEASUREMENT_NOISE
            ),
            initial_covariance=rospy.get_param(
                "~initial_covariance", TRACKER_INITIAL_COVARIANCE
            ),
        )
        self._last_receive_time = None
        self.pub = rospy.Publisher(TOPIC_TRACKS, TrackArray, queue_size=QUEUE_SIZE)
        rospy.Subscriber(
            TOPIC_CENTROIDS, CentroidArray, self.on_centroids, queue_size=QUEUE_SIZE
        )
        rospy.loginfo(
            "[tracker] ready: rate=%.1fHz gate=%.3f max_missed=%d",
            self.rate_hz,
            self.tracker.association_threshold,
            self.tracker.max_missed_frames,
        )

    def on_centroids(self, msg):
        """收到一帧质心，按 ROS 接收时间推进算法并发布当前航迹。

        第一帧使用配置默认步长。后续有效量测和空数组统一使用相邻回调的
        ``rospy.Time.now()`` 差。重复时间不推进；时间倒退也不推进，并以当前
        时间重建基准，使下一次正向推进可立即恢复。
        """
        receive_time = rospy.Time.now()
        measurement_stamp = stamp_to_seconds(msg)
        if self._last_receive_time is None:
            dt = self.default_dt
            self._last_receive_time = receive_time
        else:
            dt = (receive_time - self._last_receive_time).to_sec()
            if dt <= 0.0:
                # 不为重复/倒退的 ROS 时间虚构默认步长。倒退时赋值同时完成
                # 重基准；重复时赋相同值，下一帧仍从该时刻计算。
                self._last_receive_time = receive_time
                self.pub.publish(tracks_to_msg([
                    track_state_to_track(track) for track in self.tracker.active_tracks
                ]))
                return
            self._last_receive_time = receive_time
        track_states = self.tracker.step(
            centroids_from_msg(msg), dt, timestamp=measurement_stamp
        )
        self.pub.publish(tracks_to_msg([track_state_to_track(track) for track in track_states]))


def main():
    rospy.init_node("tracker")
    TrackerNode()
    rospy.spin()


if __name__ == "__main__":
    main()
