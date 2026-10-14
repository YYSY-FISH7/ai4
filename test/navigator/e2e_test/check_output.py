#!/usr/bin/env python3
"""Assertions for Navigator E2E output."""
from __future__ import annotations

import sys
import time

import rospy
from mavros_msgs.msg import PositionTarget


class Checker:
    def __init__(self):
        self.samples = []
        rospy.Subscriber("/test/ctrl_radar", PositionTarget, self.callback, queue_size=200)

    def callback(self, msg):
        self.samples.append((time.monotonic(), msg))

    def run(self):
        deadline = time.monotonic() + 4.5
        rate = rospy.Rate(50)
        while time.monotonic() < deadline and not rospy.is_shutdown():
            rate.sleep()
        valid = [m for _, m in self.samples if abs(m.position.x - 10.0) < 0.01]
        hover = [m for _, m in self.samples if abs(m.position.x - 1.0) < 0.01 and
                 abs(m.position.y - 2.0) < 0.01 and abs(m.position.z - 3.0) < 0.01]
        if len(valid) < 5:
            return self.fail("valid track command was not observed")
        if len(hover) < 5:
            return self.fail("navigator did not enter hover after silent input")
        if len(self.samples) < 20:
            return self.fail("too few output samples")
        elapsed = self.samples[-1][0] - self.samples[0][0]
        hz = (len(self.samples) - 1) / elapsed if elapsed > 0 else 0.0
        if not 40.0 <= hz <= 60.0:
            return self.fail("output frequency %.2f Hz is outside 50 Hz tolerance" % hz)
        if any(m.coordinate_frame != PositionTarget.FRAME_LOCAL_NED for _, m in self.samples):
            return self.fail("coordinate_frame is not FRAME_LOCAL_NED")
        if any(m.type_mask != 3576 for _, m in self.samples):
            return self.fail("type_mask is not 3576")
        print("PASS navigator: samples=%d frequency=%.2fHz valid=%d hover=%d" %
              (len(self.samples), hz, len(valid), len(hover)))
        return 0

    @staticmethod
    def fail(reason):
        print("FAIL navigator: " + reason)
        return 1


def main():
    rospy.init_node("navigator_e2e_checker", anonymous=False)
    sys.exit(Checker().run())


if __name__ == "__main__":
    main()
