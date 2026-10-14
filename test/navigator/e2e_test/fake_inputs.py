#!/usr/bin/env python3
"""Navigator E2E source: valid track, then silent tracks with live pose."""
from __future__ import annotations

import time

import rospy
from geometry_msgs.msg import PoseStamped
from uav_tracking.msg import Track, TrackArray


def main():
    rospy.init_node("navigator_e2e_source", anonymous=False)
    tracks_pub = rospy.Publisher("/test/radar_tracks", TrackArray, queue_size=1)
    pose_pub = rospy.Publisher("/test/local_pose", PoseStamped, queue_size=1)
    start = time.monotonic()
    rate = rospy.Rate(30)
    while time.monotonic() - start < 4.0 and not rospy.is_shutdown():
        pose = PoseStamped()
        pose.pose.position.x = 1.0
        pose.pose.position.y = 2.0
        pose.pose.position.z = 3.0
        pose_pub.publish(pose)
        if time.monotonic() - start < 1.2:
            item = Track()
            item.id = 7
            item.position = [10.0, 20.0, 30.0]
            item.velocity = [0.0, 0.0, 0.0]
            item.covariance = [0.0] * 36
            item.age = 5
            msg = TrackArray()
            msg.tracks = [item]
            tracks_pub.publish(msg)
        rate.sleep()


if __name__ == "__main__":
    main()
