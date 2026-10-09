#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断言节点（E2E 测试用）：订阅 ``/visual/tracks`` 并校验。

参数（rosparam）
----------------
:~mode       str    "target" | "empty"
                    - target：要求话题在流 **且** 收到航迹
                    - empty ：要求话题**仍在流** 且 每条消息 ``tracks`` 为空（空也发）
:~duration   float  观察时长（秒）          默认 6.0
:~min_msgs   int    最少消息数（证明在流）   默认 20
:~frame_w    int    画面宽（校验 area_ratio）默认 640
:~frame_h    int    画面高                   默认 480
:~area_tol   float  area_ratio 相对容差      默认 0.02（2%）
:~check_id_stable bool 是否校验 ID 跨帧稳定   默认 True

退出码：0 = PASS，1 = FAIL（便于 run_e2e.sh 汇总）。
"""
from __future__ import annotations

import sys

import rospy
from uav_tracking.msg import VisualTrackArray

TOPIC = "/visual/tracks"


class Checker:
    def __init__(self):
        self.mode = str(rospy.get_param("~mode", "target")).lower()
        self.duration = float(rospy.get_param("~duration", 6.0))
        self.min_msgs = int(rospy.get_param("~min_msgs", 20))
        self.frame_w = int(rospy.get_param("~frame_w", 640))
        self.frame_h = int(rospy.get_param("~frame_h", 480))
        self.area_tol = float(rospy.get_param("~area_tol", 0.02))
        self.check_id_stable = bool(rospy.get_param("~check_id_stable", True))

        self.count = 0
        self.nonempty = 0
        self.ids = set()
        self.id_seq = []
        self.area_bad = 0
        self.area_samples = []
        rospy.Subscriber(TOPIC, VisualTrackArray, self.on_tracks, queue_size=10)

    def on_tracks(self, msg):
        self.count += 1
        if len(msg.tracks) == 0:
            return
        self.nonempty += 1
        for t in msg.tracks:
            self.ids.add(int(t.id))
            self.id_seq.append(int(t.id))
            x, y, w, h = [float(v) for v in t.bbox]
            expect = (w * h) / float(self.frame_w * self.frame_h)
            got = float(t.area_ratio)
            self.area_samples.append(got)
            if expect > 0 and abs(got - expect) / expect > self.area_tol:
                self.area_bad += 1

    def run(self):
        rospy.loginfo("[check] mode=%s 观察 %.1fs ...", self.mode, self.duration)
        rospy.sleep(self.duration)

        print("[check] 收到 %d 条 %s（期望 >= %d）" % (self.count, TOPIC, self.min_msgs))
        failures = []

        if self.count < self.min_msgs:
            failures.append("话题未在流：仅 %d 条 < %d" % (self.count, self.min_msgs))

        if self.mode == "empty":
            if self.nonempty > 0:
                failures.append("mode=empty 却收到 %d 条含航迹的消息" % self.nonempty)
            else:
                print("PASS: empty 阶段 —— 话题在流且 tracks 恒为空（空也发成立）")
        else:
            if self.nonempty == 0:
                failures.append("mode=target 但未收到任何航迹")
            else:
                print("[check] 航迹消息 %d 条，ID 集合 = %s" % (self.nonempty, sorted(self.ids)))
                if self.area_bad:
                    failures.append("area_ratio 与 bbox/画面面积 不一致（%d 条超差）"
                                    % self.area_bad)
                else:
                    print("PASS: area_ratio 与 bbox/(%dx%d) 一致（样本 %s）"
                          % (self.frame_w, self.frame_h,
                             ["%.4f" % v for v in self.area_samples[:3]]))
                if self.check_id_stable:
                    if len(self.ids) != 1:
                        failures.append("ID 跨帧不稳定：出现 %d 个不同 ID %s"
                                        % (len(self.ids), sorted(self.ids)))
                    else:
                        print("PASS: ID 跨帧稳定（全程 id=%d，共 %d 帧）"
                              % (self.id_seq[0], len(self.id_seq)))

        if failures:
            for f in failures:
                print("FAIL: " + f)
            return 1
        return 0


def main():
    rospy.init_node("check_tracks")
    sys.exit(Checker().run())


if __name__ == "__main__":
    main()
