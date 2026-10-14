#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``/navigator`` 节点：``TrackArray`` -> ``/ctrl/radar``。

本节点只生成中间雷达导航指令，不连接最终飞控 setpoint 话题，不调用解锁、
模式切换或 command 服务。最终出口仍由现有 ``/control_mux`` 负责。
"""
from __future__ import annotations

import os
import sys

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import PositionTarget
from uav_tracking.msg import TrackArray

_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from config import NAVIGATOR_HOLD_TIMEOUT, NAVIGATOR_RATE_HZ  # noqa: E402
from datatypes import Pose, PositionCommand, Track, Waypoint  # noqa: E402
from navigator import (  # noqa: E402
    hover_setpoint as pure_hover_setpoint,
    on_timer as pure_on_timer,
    send_waypoint as pure_send_waypoint,
)

__all__ = [
    "TOPIC_TRACKS",
    "TOPIC_POSE",
    "TOPIC_OUTPUT",
    "POSITION_ONLY_TYPE_MASK",
    "tracks_from_msg",
    "pose_from_msg",
    "position_command_to_position_target",
    "waypoint_to_position_target",
    "hover_setpoint",
    "NavigatorNode",
]

TOPIC_TRACKS = "/radar/tracks"
TOPIC_POSE = "/mavros/local_position/pose"
TOPIC_OUTPUT = "/ctrl/radar"
QUEUE_SIZE = 1
POSITION_ONLY_TYPE_MASK = (
    PositionTarget.IGNORE_VX
    | PositionTarget.IGNORE_VY
    | PositionTarget.IGNORE_VZ
    | PositionTarget.IGNORE_AFX
    | PositionTarget.IGNORE_AFY
    | PositionTarget.IGNORE_AFZ
    | PositionTarget.IGNORE_YAW
    | PositionTarget.IGNORE_YAW_RATE
)


def tracks_from_msg(msg):
    """``TrackArray`` -> ``list[datatypes.Track]``。"""
    return [
        Track(
            id=int(item.id),
            position=tuple(float(value) for value in item.position),
            velocity=tuple(float(value) for value in item.velocity),
            covariance=tuple(float(value) for value in item.covariance),
            age=int(item.age),
        )
        for item in msg.tracks
    ]


def pose_from_msg(msg):
    """``PoseStamped`` -> 纯 ``Pose``。"""
    position = msg.pose.position
    orientation = msg.pose.orientation
    return Pose(
        position=(float(position.x), float(position.y), float(position.z)),
        orientation=(float(orientation.x), float(orientation.y), float(orientation.z), float(orientation.w)),
    )


def position_command_to_position_target(command: PositionCommand) -> PositionTarget:
    """将纯 ``PositionCommand`` 转换为 ROS ``PositionTarget``。"""
    msg = PositionTarget()
    msg.coordinate_frame = int(command.coordinate_frame)
    msg.type_mask = int(command.type_mask)
    msg.position.x, msg.position.y, msg.position.z = (float(value) for value in command.position)
    msg.velocity.x, msg.velocity.y, msg.velocity.z = (float(value) for value in command.velocity)
    msg.yaw = float(command.yaw)
    msg.yaw_rate = float(command.yaw_rate)
    return msg


def waypoint_to_position_target(wp: Waypoint) -> PositionTarget:
    """兼容旧调用名：航点经纯算法转换后再装包为 ROS 消息。

    仿真坐标系重合，不做外参变换；MAVROS setpoint_raw 使用标准 local NED
    frame 常量。只启用 position，屏蔽 velocity、acceleration、yaw 和 yaw_rate。
    """
    return position_command_to_position_target(pure_send_waypoint(wp))


def hover_setpoint(current_pose):
    """节点层悬停适配：纯位置保持指令 -> ``PositionTarget``。"""
    return position_command_to_position_target(pure_hover_setpoint(current_pose))


class NavigatorNode:
    """事件层缓存 + 50 Hz 时钟层。"""

    def __init__(self):
        self.rate_hz = float(rospy.get_param("~rate_hz", NAVIGATOR_RATE_HZ))
        self.hold_timeout = float(
            rospy.get_param("~hold_timeout", NAVIGATOR_HOLD_TIMEOUT)
        )
        if self.rate_hz <= 0.0:
            raise ValueError("~rate_hz 必须 > 0")
        if self.hold_timeout < 0.0:
            raise ValueError("~hold_timeout 必须 >= 0")

        self._tracks = []
        self._last_valid_time = None
        self._current_pose = None
        self._last_waypoint = None

        self.pub = rospy.Publisher(TOPIC_OUTPUT, PositionTarget, queue_size=QUEUE_SIZE)
        rospy.Subscriber(TOPIC_TRACKS, TrackArray, self.on_tracks, queue_size=QUEUE_SIZE)
        rospy.Subscriber(TOPIC_POSE, PoseStamped, self.on_pose, queue_size=QUEUE_SIZE)
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.rate_hz), self.on_timer)
        rospy.loginfo(
            "[navigator] ready: rate=%.1fHz hold_timeout=%.3fs output=%s",
            self.rate_hz,
            self.hold_timeout,
            TOPIC_OUTPUT,
        )

    def on_tracks(self, msg):
        """事件层：空数组不刷新 ``valid_age``。"""
        tracks = tracks_from_msg(msg)
        self._tracks = tracks
        if tracks:
            self._last_valid_time = rospy.Time.now()

    def on_pose(self, msg):
        self._current_pose = pose_from_msg(msg)

    def on_timer(self, _event):
        """50Hz 时钟层：生成并发布唯一的中间雷达指令。"""
        if self._current_pose is None:
            # 没有当前位置时不能构造可靠的长时悬停点；不发布伪造位置。
            return
        if self._last_valid_time is None:
            valid_age = float("inf")
        else:
            valid_age = max(0.0, (rospy.Time.now() - self._last_valid_time).to_sec())

        command = pure_on_timer(
            self._tracks,
            valid_age,
            self._last_waypoint,
            self._current_pose,
            self.hold_timeout,
        )
        self._last_waypoint = command
        self.pub.publish(position_command_to_position_target(command))


def main():
    rospy.init_node("navigator")
    NavigatorNode()
    rospy.spin()


if __name__ == "__main__":
    main()
