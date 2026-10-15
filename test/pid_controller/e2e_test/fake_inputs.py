#!/usr/bin/env python3
"""PID E2E source: centered target, offset target, then silent input."""
from __future__ import annotations

import time

import rospy
from uav_tracking.msg import VisualTrack, VisualTrackArray


def publish(pub, bbox, area):
    item = VisualTrack()
    item.id = 1
    item.bbox = list(bbox)
    item.area_ratio = area
    msg = VisualTrackArray()
    msg.tracks = [item]
    pub.publish(msg)


def main():
    rospy.init_node("pid_e2e_source", anonymous=False)
    pub = rospy.Publisher("/test/visual_tracks", VisualTrackArray, queue_size=1)
    start = time.monotonic()
    rate = rospy.Rate(10)
    while time.monotonic() - start < 3.5 and not rospy.is_shutdown():
        elapsed = time.monotonic() - start
        if elapsed < 1.0:
            publish(pub, (310.0, 230.0, 20.0, 20.0), 0.10)
        elif elapsed < 2.0:
            publish(pub, (400.0, 320.0, 20.0, 20.0), 0.01)
        rate.sleep()


if __name__ == "__main__":
    main()
