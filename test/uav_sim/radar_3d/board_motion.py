#!/usr/bin/env python3
"""五块标定靶板各自独立运动：静止/慢往复/8字/垂直圆周/快速往复。"""
import math

import rospy
from gazebo_msgs.srv import SetModelState
from gazebo_msgs.msg import ModelState

BASE_Z = 1.0
HEIGHTS = [BASE_Z + 5 * math.tan(math.radians(d)) for d in (-10, -5, 0, 5, 10)]

MOTIONS = [
    dict(name='static',   base=(5.1, -2.0)),
    dict(name='sway',     base=(5.1, -2.0), amp=1.2, period=10.0),
    dict(name='figure8',  base=(5.1, -2.0), ax=0.4, ay=1.0, period=14.0),
    dict(name='circle_v', base=(5.1, -2.0), ry=0.7, rz=0.5, period=9.0),
    dict(name='fast',     base=(5.1, -2.0), amp=0.8, period=2.5),
]


def pose_for(i, m, t):
    th = 2 * math.pi * t / m.get('period', 10.0)
    bx, by = m['base']
    z0 = HEIGHTS[i]
    if m['name'] == 'static':
        return bx, by, z0, 0.0
    if m['name'] == 'sway':
        return bx, by + m['amp'] * math.sin(th), z0, 0.0
    if m['name'] == 'figure8':
        return (bx + m['ax'] * math.sin(th),
                by + m['ay'] * math.sin(2 * th),
                z0, 0.15 * math.sin(th))
    if m['name'] == 'circle_v':
        return bx, by + m['ry'] * math.sin(th), z0 + m['rz'] * math.cos(th), 0.0
    if m['name'] == 'fast':
        return bx, by + m['amp'] * math.sin(th), z0, 0.0
    raise ValueError(m['name'])


def main():
    rospy.init_node('radar_board_motion_multi')
    rospy.wait_for_service('/gazebo/set_model_state', timeout=30)
    set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
    t0 = rospy.Time.now()
    rate = rospy.Rate(20)
    rospy.loginfo('5 boards: %s', ', '.join(m['name'] for m in MOTIONS))
    while not rospy.is_shutdown():
        t = (rospy.Time.now() - t0).to_sec()
        for i, m in enumerate(MOTIONS):
            x, y, z, yaw = pose_for(i, m, t)
            state = ModelState()
            state.model_name = 'radar_board_%d' % i
            state.pose.position.x = x
            state.pose.position.y = y
            state.pose.position.z = z
            state.pose.orientation.z = math.sin(yaw / 2)
            state.pose.orientation.w = math.cos(yaw / 2)
            state.reference_frame = 'world'
            try:
                set_state(state)
            except rospy.ServiceException as exc:
                rospy.logwarn_throttle(2, 'set_model_state failed: %s', exc)
        rate.sleep()


if __name__ == '__main__':
    main()
