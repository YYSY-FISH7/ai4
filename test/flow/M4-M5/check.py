#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 → M5 小联调自检：确认 M4 发出的检测/跟踪能被 M5 接收并驱动状态切换。

用法：
    python3 check.py                    # 检查 15 秒
    python3 check.py --seconds 30

判定项：
    1. /detections 有输出（M4 发送方）
    2. /visual/tracks 有输出
    3. 同一 track_id 连续出现 ≥ 5 帧（证明跟踪稳定，不是每帧重建）
    4. 实际观察 RADAR_GUIDE → VISUAL_LOCK 状态切换
    5. 若 tracks 有数据但 state 未切换，给出阈值排查提示

退出码：0 = PASS，1 = FAIL。
"""
from __future__ import annotations

import math
import argparse
import collections
import sys
import time

import rospy
from std_msgs.msg import String

from uav_tracking.msg import Detections, VisualTrackArray

PASS = []
FAIL = []


def ok(msg):
    PASS.append(msg)
    print('  [PASS] ' + msg)


def bad(msg):
    FAIL.append(msg)
    print('  [FAIL] ' + msg)


def note(msg):
    print('         ' + msg)


def main():
    parser = argparse.ArgumentParser(description='M4→M5 数据流联调自检')
    parser.add_argument('--seconds', type=float, default=15.0, help='采集时长（秒）')
    parser.add_argument('--min-streak', type=int, default=5, help='同一 ID 连续帧门槛')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0: parser.error('seconds 必须为有限正数')
    if args.min_streak < 2: parser.error('min-streak 至少为 2')

    rospy.init_node('flow_m4_m5_check', anonymous=True)

    st = {
        'det_frames': 0,
        'trk_frames': 0,
        'trk_empty': 0,
        'id_track': collections.defaultdict(int),      # id -> 出现帧数
        'id_streak': collections.defaultdict(int),     # id -> 当前连续帧
        'id_best_streak': collections.defaultdict(int),
        'prev_ids': set(),
        'states': [],
        'areas': [],
        'invalid': 0,
    }

    def on_det(msg):
        st['det_frames'] += 1

    def on_trk(msg):
        st['trk_frames'] += 1
        ids = set()
        if not msg.tracks:
            st['trk_empty'] += 1
        for t in msg.tracks:
            x,y,w,h = t.bbox
            if not all(math.isfinite(v) for v in [x,y,w,h,t.area_ratio]) or w <= 0 or h <= 0 or t.area_ratio < 0:
                st['invalid'] += 1
                continue
            tid = int(t.id)
            ids.add(tid)
            st['id_track'][tid] += 1
            if tid in st['prev_ids']:
                st['id_streak'][tid] += 1
            else:
                st['id_streak'][tid] = 1
            st['id_best_streak'][tid] = max(st['id_best_streak'][tid], st['id_streak'][tid])
            st['areas'].append(float(t.area_ratio))
        st['prev_ids'] = ids

    def on_state(msg):
        s = (msg.data or '').strip()
        if not st['states'] or st['states'][-1] != s:
            st['states'].append(s)

    rospy.Subscriber('/detections', Detections, on_det, queue_size=20)
    rospy.Subscriber('/visual/tracks', VisualTrackArray, on_trk, queue_size=20)
    rospy.Subscriber('/state', String, on_state, queue_size=10)

    print('=' * 62)
    print(' M4 → M5 数据流联调自检')
    print('=' * 62)

    # 先等 M5 的发布者上线再开始采集，避免错过 state_machine 启动时的初值
    t0 = time.time()
    waited = False
    while not rospy.is_shutdown() and time.time() - t0 < 40:
        if rospy.get_published_topics().count(['/state', 'std_msgs/String']):
            waited = True
            break
        rospy.sleep(0.2)
    if waited:
        print('  （已检测到 /state 发布者，开始采集 %.0f 秒）' % args.seconds)

    rospy.sleep(args.seconds)

    print('\n--- 核对 ---')
    if st['det_frames'] > 0:
        ok('/detections 有输出：%d 帧' % st['det_frames'])
    else:
        bad('/detections 无输出（M4 的 detector 是否在跑？）')

    if st['trk_frames'] > 0:
        ok('/visual/tracks 有输出：%d 帧' % st['trk_frames'])
    else:
        bad('/visual/tracks 无输出（M4 的 visual_tracker 是否在跑？）')

    if st['invalid']:
        bad('包含非法航迹：%d 条' % st['invalid'])

    if st['id_best_streak']:
        best_id, best = max(st['id_best_streak'].items(), key=lambda kv: kv[1])
        if best >= args.min_streak:
            ok('跟踪 ID 稳定：id=%d 连续 %d 帧' % (best_id, best))
        else:
            bad('跟踪 ID 不稳定：最长仅连续 %d 帧（< %d），可能在每帧重建'
                % (best, args.min_streak))
        note('出现过的 ID：%s' % sorted(st['id_track']))
        if st['areas']:
            note('area_ratio 范围：%.4f ~ %.4f' % (min(st['areas']), max(st['areas'])))

    else:
        bad('未收到任何有效航迹，无法证明跟踪成功')

    if st['states']:
        note('状态序列：%s' % ' → '.join(st['states']))
        states = st['states']
        if 'RADAR_GUIDE' in states and 'VISUAL_LOCK' in states[states.index('RADAR_GUIDE') + 1:]:
            ok('M5 已完成状态切换：出现 VISUAL_LOCK')
        else:
            bad('未观察到 RADAR_GUIDE → VISUAL_LOCK，不能证明本次完成切换')
            note('排查：state_machine 判据为 连续 N/M/K=3/3/5、conf≥0.8、area≥0.02；'
                 '若检测置信度长期低于 0.8，需要与 M5 负责人确认门限')
    else:
        bad('/state 无消息（M5 的 state_machine 是否在跑？）')

    if st['trk_frames'] and st['trk_empty'] == st['trk_frames']:
        note('提示：全部帧的 tracks 为空，属于"检测不到目标"，不是链路故障')

    print('\n' + '=' * 62)
    print(' 结果：PASS=%d  FAIL=%d' % (len(PASS), len(FAIL)))
    print('=' * 62)
    return 0 if not FAIL else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except rospy.ROSInterruptException:
        sys.exit(1)
