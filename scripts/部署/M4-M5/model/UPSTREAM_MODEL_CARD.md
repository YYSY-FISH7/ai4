---
license: apache-2.0
tags:
  - yolo
  - object-detection
  - drone-detection
  - uav
  - ultralytics
library_name: ultralytics
---

# YOLOv11s Drone Detector

A YOLOv11s model fine-tuned to detect drones from RGB camera footage. Trained
from the `pathikg/drone-detection-dataset` (54k images) and validated on the
held-out **Anti-UAV-RGBT** test split (91 video sequences).

## Held-out eval (Anti-UAV-RGBT, IoU=0.5)

| metric | value |
|---|---|
| Precision | 0.929 |
| Recall | 0.759 |
| F1 | 0.836 |
| Mean IoU on TPs | 0.998 |
| AP@0.5 | 0.741 |

Beats every other public single-class drone YOLO we found on HF on mAP@50 and
mAP@50-95 (and is much smaller — 19MB).

## Use

```python
from ultralytics import YOLO
model = YOLO("sapoepsilon/yolov11s-drone-detector")
model.track("path/to/drone_video.mp4", tracker="bytetrack.yaml")
```

## Training

| | |
|---|---|
| base | ultralytics yolo11s.pt |
| dataset | pathikg/drone-detection-dataset (~54k images) |
| imgsz | 640 |
| batch | 192 (3-GPU DDP) |
| epochs | 25 (early-stopped from 30) |
| optimizer | AdamW, lr 4e-4, cosine |
| augmentation | mosaic + flip + close-mosaic at epoch 20 |
| hardware | 3× NVIDIA RTX 3090 (1× Ti) |

## Caveats

- Single class only (`drone`); doesn't distinguish drone subtypes
- Trained on YouTube-sourced RGB drone images; recall drops on long-range
  surveillance (Anti-UAV-RGBT shows ~76% recall on small/distant drones)
- Pair with a tracker (ByteTrack or BoT-SORT) for trajectory output

## License
Apache 2.0.
