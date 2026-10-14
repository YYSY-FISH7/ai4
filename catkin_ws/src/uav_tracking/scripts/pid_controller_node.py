#!/usr/bin/env python3
"""模块 6 ROS 适配节点：``/visual/tracks`` -> ``/ctrl/visual``。

仅发布中间控制话题，不发布 ``/mavros/setpoint_raw/local``，也不调用任何
飞控服务。坐标转换由 MAVROS setpoint_raw 插件完成，本节点不重复转换。
"""
from __future__ import annotations

import os
import sys

import rospy
from mavros_msgs.msg import PositionTarget
from uav_tracking.msg import VisualTrackArray

_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from config import (  # noqa: E402
    PID_DEPTH_KD, PID_DEPTH_KI, PID_DEPTH_KP, PID_DEPTH_MAX_OUT,
    PID_DESIRED_AREA, PID_FORWARD_SPEED_LIMIT, PID_HOLD_TIMEOUT,
    PID_IMAGE_HEIGHT, PID_IMAGE_WIDTH, PID_IMPACT_AREA_THRESHOLD,
    PID_INTEGRAL_LIMIT, PID_MIN_AREA, PID_RATE_HZ, PID_TERMINAL_FORWARD_SPEED,
    PID_VERTICAL_KD, PID_VERTICAL_KI, PID_VERTICAL_KP, PID_VERTICAL_MAX_OUT,
    PID_YAW_KD, PID_YAW_KI, PID_YAW_KP, PID_YAW_MAX_OUT,
)
from datatypes import PositionCommand, VisualTrack  # noqa: E402
from pid_controller import PIDController, on_timer as pure_on_timer  # noqa: E402

TOPIC_TRACKS = "/visual/tracks"
TOPIC_OUTPUT = "/ctrl/visual"
QUEUE_SIZE = 1
VELOCITY_TYPE_MASK = (
    PositionTarget.IGNORE_PX | PositionTarget.IGNORE_PY | PositionTarget.IGNORE_PZ |
    PositionTarget.IGNORE_AFX | PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ |
    PositionTarget.IGNORE_YAW
)


def tracks_from_msg(msg):
    return [VisualTrack(int(item.id), tuple(float(value) for value in item.bbox), float(item.area_ratio)) for item in msg.tracks]


def command_to_position_target(command: PositionCommand) -> PositionTarget:
    msg = PositionTarget()
    # 纯算法已固定 body-offset frame 和 velocity mask；节点只负责装包。
    msg.coordinate_frame = int(command.coordinate_frame)
    msg.type_mask = int(command.type_mask)
    msg.velocity.x = float(command.velocity_x)
    # 启用横向速度通道并明确控制为零，不能通过 IGNORE_VY 代替零速。
    msg.velocity.y = 0.0
    msg.velocity.z = float(command.velocity_z)
    msg.yaw_rate = float(command.yaw_rate)
    return msg


class PIDControllerNode:
    def __init__(self):
        self.rate_hz = float(rospy.get_param("~rate_hz", PID_RATE_HZ))
        self.hold_timeout = float(rospy.get_param("~hold_timeout", PID_HOLD_TIMEOUT))
        if self.rate_hz <= 0.0 or self.hold_timeout < 0.0:
            raise ValueError("PID rate 必须 > 0 且 hold_timeout 必须 >= 0")
        self.image_width = float(rospy.get_param("~image_width", PID_IMAGE_WIDTH))
        self.image_height = float(rospy.get_param("~image_height", PID_IMAGE_HEIGHT))
        self.desired_area = float(rospy.get_param("~desired_area", PID_DESIRED_AREA))
        self.min_area = float(rospy.get_param("~min_area", PID_MIN_AREA))
        self.forward_speed_limit = float(rospy.get_param("~forward_speed_limit", PID_FORWARD_SPEED_LIMIT))
        self.impact_area_threshold = float(rospy.get_param("~impact_area_threshold", PID_IMPACT_AREA_THRESHOLD))
        self.terminal_forward_speed = float(rospy.get_param("~terminal_forward_speed", PID_TERMINAL_FORWARD_SPEED))
        self.controllers = (
            PIDController(PID_YAW_KP, PID_YAW_KI, PID_YAW_KD, PID_YAW_MAX_OUT, PID_INTEGRAL_LIMIT),
            PIDController(PID_VERTICAL_KP, PID_VERTICAL_KI, PID_VERTICAL_KD, PID_VERTICAL_MAX_OUT, PID_INTEGRAL_LIMIT),
            PIDController(PID_DEPTH_KP, PID_DEPTH_KI, PID_DEPTH_KD, PID_DEPTH_MAX_OUT, PID_INTEGRAL_LIMIT),
        )
        self._tracks = []
        self._last_valid_time = None
        self._last_cmd = None
        self._last_tick = rospy.Time.now()
        self.pub = rospy.Publisher(TOPIC_OUTPUT, PositionTarget, queue_size=QUEUE_SIZE)
        rospy.Subscriber(TOPIC_TRACKS, VisualTrackArray, self.on_tracks, queue_size=QUEUE_SIZE)
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.rate_hz), self.on_timer)

    def on_tracks(self, msg):
        self._tracks = tracks_from_msg(msg)
        if self._tracks:
            self._last_valid_time = rospy.Time.now()

    def on_timer(self, _event):
        now = rospy.Time.now()
        dt = max(0.0, (now - self._last_tick).to_sec())
        self._last_tick = now
        valid_age = float("inf") if self._last_valid_time is None else max(0.0, (now - self._last_valid_time).to_sec())
        command = pure_on_timer(
            self._tracks, valid_age, self._last_cmd, self.hold_timeout,
            dt=dt, controllers=self.controllers,
            image_width=self.image_width, image_height=self.image_height,
            desired_area=self.desired_area, min_area=self.min_area,
            forward_speed_limit=self.forward_speed_limit,
            impact_area_threshold=self.impact_area_threshold,
            terminal_forward_speed=self.terminal_forward_speed,
        )
        self._last_cmd = command
        self.pub.publish(command_to_position_target(command))


def main():
    rospy.init_node("pid_controller")
    PIDControllerNode()
    rospy.spin()


if __name__ == "__main__":
    main()
