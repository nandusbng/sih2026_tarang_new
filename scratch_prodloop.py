#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TEMP: production-equivalent loop: xtf_parser.parse_xtf + best.pt at
app.py settings (conf=0.20, default imgsz=640). Prints detection table."""
import os
import shutil
import sys
import tempfile

import cv2
from ultralytics import YOLO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xtf_parser

XTF = 'tarang_synthetic_survey_002.xtf'
tmp = tempfile.mkdtemp(prefix='tarang_sweep_')
res = xtf_parser.parse_xtf(XTF, tmp)
print('images:', len(res['images']))
m = YOLO('best.pt')
total = 0
for img_info in res['images']:
    img = cv2.imread(img_info['path'])
    r = m(img, conf=0.20, verbose=False)[0]
    for b in r.boxes:
        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
        yc = (y1 + y2) / 2
        ping = img_info['ping_start'] + int(yc)
        p = res['pings'][ping]
        total += 1
        print('img pings %5d-%5d  %s  conf=%.3f  box=%dx%d  ycenter=%.0f -> ping %5d  lat=%.6f lon=%.6f' % (
            img_info['ping_start'], img_info['ping_end'],
            m.names[int(b.cls[0])], float(b.conf[0]), x2 - x1, y2 - y1, yc,
            ping, p['latitude'], p['longitude']))
print('TOTAL detections >=0.20:', total)
shutil.rmtree(tmp, ignore_errors=True)
