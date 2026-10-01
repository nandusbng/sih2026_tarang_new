#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TEMP: paste real reference sonar crops into a speckled waterfall background
at several scales to learn what pixel scale best.pt expects."""
import numpy as np
import cv2
from ultralytics import YOLO

m = YOLO('best.pt')
ref1 = cv2.imread('scratch_ref_crop.png', cv2.IMREAD_GRAYSCALE)   # shipwreck
ref2 = cv2.imread('scratch_ref_crop2.png', cv2.IMREAD_GRAYSCALE)  # pipeline
print('ref shapes', ref1.shape, ref2.shape)


def value_noise(rng, shape, cells):
    g = rng.random((cells[0], cells[1])).astype(np.float32)
    n = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = (n - n.mean()) / (n.std() + 1e-6)
    return n


def bg(rng, h=1000, w=1024):
    img = np.full((h, w), 120.0, np.float32)
    tex = value_noise(rng, (h, w), (30, 30))
    img *= (1.0 + 0.25 * tex)
    spk = rng.gamma(3.0, 0.33, (h, w)).astype(np.float32)
    img *= np.clip(spk, 0.2, 2.2)
    return np.clip(img, 0, 255).astype(np.uint8)


for name, ref in (('wreck', ref1), ('pipe', ref2)):
    for scale in (0.5, 1.0, 2.0, 3.0):
        rng = np.random.default_rng(3)
        canvas = bg(rng)
        r = cv2.resize(ref, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h, w = r.shape
        if h > 900 or w > 900:
            print(name, scale, 'too big', r.shape)
            continue
        y0, x0 = 60, 60
        canvas[y0:y0 + h, x0:x0 + w] = r
        path = 'scratch_yolo/ref_%s_%.1f.jpg' % (name, scale)
        cv2.imwrite(path, cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR))
        res = m(path, conf=0.05, verbose=False)[0]
        out = []
        for b in res.boxes:
            out.append('%s %.3f xyxy=%s' % (m.names[int(b.cls[0])], float(b.conf[0]),
                                            [round(float(v)) for v in b.xyxy[0]]))
        print('%s scale=%.1f patch=%dx%d -> %s' % (name, scale, h, w, out or 'NONE'))
