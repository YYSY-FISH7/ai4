#!/usr/bin/env python3
"""Assertions for Tracker E2E output."""
from __future__ import annotations

import sys
import time

import rospy
from uav_tracking.msg import TrackArray


class Checker:
    def __init__(self):
        self.records = []
        rospy.Subscriber("/test/radar_tracks", TrackArray, self.callback, queue_size=100)

    def callback(self, msg):
        self.records.append((time.monotonic(), list(msg.tracks)))

    def run(self):
        deadline = time.monotonic() + 5.5
        rate = rospy.Rate(50)
        while time.monotonic() < deadline and not rospy.is_shutdown():
            rate.sleep()

        nonempty = [tracks for _, tracks in self.records if tracks]
        empty_count = sum(1 for _, tracks in self.records if not tracks)
        if len(nonempty) < 10:
            return self.fail("non-empty TrackArray samples are insufficient")
        first_id = nonempty[0][0].id
        same_id_count = sum(1 for tracks in nonempty if tracks[0].id == first_id)
        if same_id_count < 8:
            return self.fail("stable target ID was not preserved through short loss")
        ages = [tracks[0].age for tracks in nonempty if tracks[0].id == first_id]
        if max(ages) <= min(ages):
            return self.fail("track age did not increase")
        if empty_count < 2:
            return self.fail("empty TrackArray was not published after deletion")
        later_ids = [tracks[0].id for tracks in nonempty if tracks[0].id != first_id]
        if not later_ids:
            return self.fail("recovery after deletion did not create a new ID")
        print("PASS tracker: stable_id=%d age=%d..%d empty=%d new_id=%d" %
              (first_id, min(ages), max(ages), empty_count, later_ids[-1]))
        return 0

    @staticmethod
    def fail(reason):
        print("FAIL tracker: " + reason)
        return 1


def main():
    rospy.init_node("tracker_e2e_checker", anonymous=False)
    sys.exit(Checker().run())


if __name__ == "__main__":
    main()
