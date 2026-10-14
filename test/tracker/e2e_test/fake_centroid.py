#!/usr/bin/env python3
"""Tracker E2E source: target, short loss, recovery, deletion, new target."""
from __future__ import annotations

import time

import rospy
from geometry_msgs.msg import PointStamped
from uav_tracking.msg import CentroidArray


def publish_target(pub, x):
    point = PointStamped()
    point.header.stamp = rospy.Time.now()
    point.header.frame_id = "test_radar"
    point.point.x = x
    point.point.y = 2.0
    point.point.z = 1.0
    msg = CentroidArray()
    msg.centroids = [point]
    pub.publish(msg)


def publish_empty(pub):
    pub.publish(CentroidArray())


def phase(pub, duration, empty=False, x=4.0, rate_hz=10.0):
    deadline = time.monotonic() + duration
    rate = rospy.Rate(rate_hz)
    while time.monotonic() < deadline and not rospy.is_shutdown():
        publish_empty(pub) if empty else publish_target(pub, x)
        rate.sleep()


def main():
    rospy.init_node("tracker_e2e_source", anonymous=False)
    pub = rospy.Publisher("/test/radar_centroid", CentroidArray, queue_size=1)
    rospy.sleep(0.4)
    phase(pub, 1.0, x=4.0)
    phase(pub, 0.25, empty=True)
    phase(pub, 1.0, x=4.1)
    phase(pub, 0.75, empty=True)
    phase(pub, 0.8, x=4.2)


if __name__ == "__main__":
    main()
