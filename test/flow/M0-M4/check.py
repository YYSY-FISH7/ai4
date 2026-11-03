#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0 → M4 小联调自检：确认 M0 的相机图像能进 M4，且检测结果与画面自洽。

用法：
    python3 check.py                       # 可视化 + 检查 15 秒
    python3 check.py --no-gui              # 无窗口（SSH）
    python3 check.py --seconds 30          # 自定义时长
    python3 check.py --topic /uav/front_camera/image_raw   # 接仿真机载相机

判定项：
    1. 图像有发布且出帧（频率 > 0.5 Hz）
    2. 图像尺寸前后一致
    3. /detections 有输出（无目标时发空数组也算通过）
    4. 所有检测框落在画面内
    5. 检测帧率 < 图像帧率（允许丢帧，但不应完全没有检测）
    6. 可视化叠加显示（可选）

退出码：0 = PASS，1 = FAIL。
"""
from __future__ import annotations

import math
import argparse
import collections
import sys
import time

import rospy
from sensor_msgs.msg import Image

from uav_tracking.msg import Detections

try:
    import cv2
    from cv_bridge import CvBridge
except ImportError:  # 无 GUI 依赖时仍可做纯数据检查
    cv2 = None
    CvBridge = None

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
    parser = argparse.ArgumentParser(description='M0→M4 数据流联调自检')
    parser.add_argument('--topic', default='/camera/image_raw', help='M0 发出的图像话题')
    parser.add_argument('--seconds', type=float, default=15.0, help='采集时长（秒）')
    parser.add_argument('--no-gui', action='store_true', help='不弹可视化窗口')
    parser.add_argument('--allow-empty', action='store_true', help='明确测试空场景时允许全程无框')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0: parser.error('seconds 必须为有限正数')

    rospy.init_node('flow_m0_m4_check', anonymous=True)

    stats = {
        'img_frames': 0,
        'det_frames': 0,
        'det_empty': 0,
        'det_targets': [],
        'size': None,
        'size_changed': False,
        'out_of_frame': 0,
        'invalid': 0,
        'max_conf': 0.0,
        'class_ids': [],
        'first_img_wall': None,
        'last_img_wall': None,
        'first_det_wall': None,
        'last_det_wall': None,
    }
    latest = {'vis': None, 'dets': []}
    bridge = CvBridge() if CvBridge else None
    show = (not args.no_gui) and cv2 is not None and bridge is not None

    def on_image(msg):
        stats['img_frames'] += 1
        now = time.time()
        if stats['first_img_wall'] is None:
            stats['first_img_wall'] = now
        stats['last_img_wall'] = now
        size = (msg.width, msg.height)
        if stats['size'] is None:
            stats['size'] = size
        elif stats['size'] != size:
            stats['size_changed'] = True
        if show:
            try:
                latest['vis'] = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            except Exception:
                pass

    def on_det(msg):
        stats['det_frames'] += 1
        now = time.time()
        if stats['first_det_wall'] is None:
            stats['first_det_wall'] = now
        stats['last_det_wall'] = now
        n = len(msg.targets)
        stats['det_targets'].append(n)
        if n == 0:
            stats['det_empty'] += 1
        latest['dets'] = [(int(t.class_id), float(t.confidence),
                           tuple(float(v) for v in t.bbox)) for t in msg.targets]
        w, h = stats['size'] if stats['size'] else (640, 480)
        for t in msg.targets:
            x, y, bw, bh = t.bbox          # msg 定义：[x, y, w, h]（左上角 + 宽高）
            stats['class_ids'].append(t.class_id)
            stats['max_conf'] = max(stats['max_conf'], t.confidence)
            if (not all(math.isfinite(v) for v in [x,y,bw,bh,t.confidence])
                    or bw <= 0 or bh <= 0 or not 0 <= t.confidence <= 1 or t.class_id < 0):
                stats['invalid'] += 1
                continue
            tol = 3.0          # 允许边界浮点误差
            if x < -tol or y < -tol or x + bw > w + tol or y + bh > h + tol:
                stats['out_of_frame'] += 1

    rospy.Subscriber(args.topic, Image, on_image, queue_size=5)
    rospy.Subscriber('/detections', Detections, on_det, queue_size=20)

    print('=' * 62)
    print(' M0 → M4 数据流联调自检   图像话题: %s' % args.topic)
    print('=' * 62)

    # 等发布者上线
    t0 = time.time()
    while not rospy.is_shutdown() and time.time() - t0 < 10:
        if rospy.get_published_topics().count([args.topic, 'sensor_msgs/Image']):
            break
        rospy.sleep(0.2)

    deadline = time.time() + args.seconds
    while not rospy.is_shutdown() and time.time() < deadline:
        if show and latest['vis'] is not None:
            canvas = latest['vis'].copy()
            for cid, conf, bbox in latest['dets']:
                x, y, bw, bh = bbox
                x1, y1 = int(x), int(y)
                x2, y2 = int(x + bw), int(y + bh)
                cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(canvas, 'id%d %.2f' % (cid, conf), (x1, max(12, y1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            try:
                cv2.imshow('M0 -> M4 live', canvas)
                cv2.waitKey(1)
            except Exception:
                show = False
        rospy.sleep(0.03)

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    print('\n--- 核对 ---')
    img_hz = 0.0
    if stats['img_frames'] and stats['last_img_wall'] > stats['first_img_wall']:
        img_hz = (stats['img_frames'] - 1) / (stats['last_img_wall'] - stats['first_img_wall'])
    det_hz = 0.0
    if stats['det_frames'] and stats['last_det_wall'] and stats['first_det_wall']:
        span = stats['last_det_wall'] - stats['first_det_wall']
        if span > 0:
            det_hz = (stats['det_frames'] - 1) / span

    if stats['img_frames'] >= 10:
        ok('图像已进入 M4：%d 帧，约 %.1f Hz' % (stats['img_frames'], img_hz))
    else:
        bad('图像帧数不足：仅 %d 帧（检查 M0 是否启动、话题名是否正确）' % stats['img_frames'])

    if stats['size']:
        note('图像尺寸：%dx%d' % stats['size'])
        if stats['size_changed']:
            bad('图像尺寸中途变化，说明数据源不稳定')
        else:
            ok('图像尺寸稳定')

    if stats['det_frames'] > 0:
        ok('/detections 有输出：%d 帧，约 %.1f Hz' % (stats['det_frames'], det_hz))
    else:
        bad('/detections 无输出（检查 detector 节点是否在跑）')

    if stats['det_frames'] and img_hz > 0 and det_hz > img_hz * 1.15:
        bad('检测频率明显高于图像频率（%.1f Hz vs %.1f Hz），疑似重复发布'
            % (det_hz, img_hz))
    elif img_hz > 0:
        ok('检测频率与图像频率匹配（%.1f Hz / %.1f Hz）' % (det_hz, img_hz))
    if img_hz > 0 and 0 < det_hz < img_hz * 0.3:
        note('检测频率明显低于图像（%.1f vs %.1f Hz），会大量丢帧；'
             '演示前可调低 imgsz 或确认 CPU 没有其他负载' % (det_hz, img_hz))

    if stats['invalid']:
        bad('包含非法检测数据：%d 个框' % stats['invalid'])

    total_boxes = len(stats['class_ids'])
    if total_boxes == 0:
        note('本段没有检测框，跳过越界检查')
    elif stats['out_of_frame'] == 0:
        ok('所有检测框都在画面内（共 %d 个框）' % total_boxes)
    elif stats['out_of_frame'] / total_boxes <= 0.05:
        note('越界框 %d/%d（%.1f%%），属边界浮点误差'
             % (stats['out_of_frame'], total_boxes,
                100.0 * stats['out_of_frame'] / total_boxes))
        ok('检测框整体落在画面内（允许 5% 边界误差）')
    else:
        bad('%d/%d 个检测框越界（%.0f%%），坐标格式可能不一致'
            % (stats['out_of_frame'], total_boxes,
               100.0 * stats['out_of_frame'] / total_boxes))

    hit = sum(1 for n in stats['det_targets'] if n > 0)
    if stats['det_frames']:
        ratio = 100.0 * hit / stats['det_frames']
        note('有目标的帧占比：%.0f%%（%d/%d），最高置信度 %.2f'
             % (ratio, hit, stats['det_frames'], stats['max_conf']))
        if hit == 0 and not args.allow_empty:
            bad('目标场景全程未检出目标；空场景请显式使用 --allow-empty')
        if hit == 0:
            note('提示：全程未检出目标。若图像里确实没有可识别物体属正常；'
                 '否则检查权重/阈值。')
    if stats['class_ids']:
        note('类别分布：%s' % dict(sorted(collections.Counter(stats['class_ids']).items())))

    print('\n' + '=' * 62)
    print(' 结果：PASS=%d  FAIL=%d' % (len(PASS), len(FAIL)))
    print('=' * 62)
    return 0 if not FAIL else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except rospy.ROSInterruptException:
        sys.exit(1)
