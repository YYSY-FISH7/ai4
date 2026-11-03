#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由公开公交车照片裁剪、缩放生成合成运动视频。

用途仅为本地界面和图像链路演示，不能代表真实相机运动、飞行动力学、
无人机检测能力或 PID 效果。真实 YOLO 推理在合成视频上运行。
用法：python3 make_moving_clip.py [输出.mp4] [帧数] [fps] [both|sweep|approach]
"""
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ASSETS, "bus_moving.mp4")
NFRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 150
FPS = int(sys.argv[3]) if len(sys.argv) > 3 else 10
MODE = sys.argv[4] if len(sys.argv) > 4 else "both"

SRC = os.path.join(ASSETS, "bus.jpg")

# 缩放与横向漂移的范围（都对准公交+行人那一块）
Z0, Z1 = 1.00, 1.70
CX0, CX1 = 300, 560      # 横向：从偏左扫到偏右 → 目标在画面里横移
CY0, CY1 = 520, 560


def ease(t):
    return t * t * (3 - 2 * t)


def frame_crop(img, t, do_zoom, do_pan):
    """镜头运动：对原图做缩放 + 中心漂移，再拉回原尺寸。"""
    h, w = img.shape[:2]
    z = (Z0 + (Z1 - Z0) * ease(t)) if do_zoom else 1.0
    cx = (CX0 + (CX1 - CX0) * ease(t)) if do_pan else 420
    cy = (CY0 + (CY1 - CY0) * ease(t)) if do_pan else 520

    cw, ch = int(w / z), int(h / z)
    x0 = int(min(max(cx - cw / 2, 0), w - cw))
    y0 = int(min(max(cy - ch / 2, 0), h - ch))
    crop = img[y0:y0 + ch, x0:x0 + cw]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)


def main():
    img = cv2.imread(SRC)
    if img is None:
        raise SystemExit("读不到源图: %s（先跑 get_assets.sh）" % SRC)
    h, w = img.shape[:2]
    print("源图: %s  %dx%d   模式: %s" % (SRC, w, h, MODE))

    modes = {
        "approach": lambda t: frame_crop(img, t, True, False),
        "sweep":    lambda t: frame_crop(img, t, False, True),
        "both":     lambda t: frame_crop(img, t, True, True),
    }
    if MODE not in modes:
        raise SystemExit("未知模式 %r，可选 %s" % (MODE, list(modes)))
    gen = modes[MODE]

    for fourcc_name, ext in (("mp4v", ".mp4"), ("XVID", ".avi")):
        path = OUT if OUT.lower().endswith(ext) else os.path.splitext(OUT)[0] + ext
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*fourcc_name), FPS, (w, h))
        if not writer.isOpened():
            print("  编码器 %s 不可用，换下一个" % fourcc_name)
            continue

        print("  写 %d 帧 @ %d fps -> %s（%s）" % (NFRAMES, FPS, path, fourcc_name))
        for i in range(NFRAMES):
            t = i / float(max(NFRAMES - 1, 1))
            frame = gen(t)
            cv2.putText(frame, "%s  frame %03d/%d" % (MODE, i + 1, NFRAMES),
                        (14, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            writer.write(frame)
        writer.release()

        cap = cv2.VideoCapture(path)
        got = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        print("  完成: %s  %.0f KB  帧数 %d" % (path, os.path.getsize(path) / 1024.0, got))
        if got > 0:
            return 0

    print("!! 所有编码器都失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
