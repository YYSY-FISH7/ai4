#!/usr/bin/env python3
"""Assertions for PID controller E2E output."""
from __future__ import annotations

import sys
import time

import rospy
from mavros_msgs.msg import PositionTarget


class Checker:
    def __init__(self):
        self.samples = []
        rospy.Subscriber("/test/ctrl_visual", PositionTarget, self.callback, queue_size=200)

    def callback(self, msg):
        self.samples.append((time.monotonic(), msg))

    def run(self):
        deadline = time.monotonic() + 3.5
        rate = rospy.Rate(50)
        while time.monotonic() < deadline and not rospy.is_shutdown():
            rate.sleep()
        centered = [m for _, m in self.samples if abs(m.yaw_rate) < 1e-6 and
                    abs(m.velocity.z) < 1e-6 and abs(m.velocity.x) < 1e-6]
        directional = [m for _, m in self.samples if m.yaw_rate < 0.0 and
                       m.velocity.z < 0.0 and m.velocity.x > 0.0]
        stopped = [m for _, m in self.samples if abs(m.yaw_rate) < 1e-6 and
                   abs(m.velocity.x) < 1e-6 and abs(m.velocity.y) < 1e-6 and
                   abs(m.velocity.z) < 1e-6]
        if len(centered) < 3:
            return self.fail("center target did not produce near-zero command")
        if len(directional) < 3:
            return self.fail("offset target direction/depth signs were not observed")
        if len(stopped) < 5:
            return self.fail("silent input did not produce zero velocity")
        if len(self.samples) < 20:
            return self.fail("too few output samples")
        elapsed = self.samples[-1][0] - self.samples[0][0]
        hz = (len(self.samples) - 1) / elapsed if elapsed > 0 else 0.0
        if not 40.0 <= hz <= 60.0:
            return self.fail("output frequency %.2f Hz is outside 50 Hz tolerance" % hz)
        if any(m.coordinate_frame != PositionTarget.FRAME_BODY_OFFSET_NED for _, m in self.samples):
            return self.fail("coordinate_frame is not FRAME_BODY_OFFSET_NED")
        if any(m.type_mask != 1479 for _, m in self.samples):
            return self.fail("type_mask is not 1479")
        if any(abs(m.velocity.y) > 1e-9 for _, m in self.samples):
            return self.fail("velocity.y is not explicitly zero")
        print("PASS pid: samples=%d frequency=%.2fHz centered=%d directional=%d stopped=%d mask=1479" %
              (len(self.samples), hz, len(centered), len(directional), len(stopped)))
        return 0

    @staticmethod
    def fail(reason):
        print("FAIL pid: " + reason)
        return 1


def main():
    rospy.init_node("pid_e2e_checker", anonymous=False)
    sys.exit(Checker().run())


if __name__ == "__main__":
    main()
