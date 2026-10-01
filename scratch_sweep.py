#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TEMP sweep harness: render contacts in raster space, run best.pt at prod
settings (default imgsz=640, conf=0.20) to find footprint/style that fires."""
import sys
import math
import numpy as np
import cv2
from ultralytics import YOLO

N_PING = 1000
N_S = 512
WC = 24            # water column samples (dark) before seabed onset
ONSET = 30


def value_noise(rng, shape, cells):
    g = rng.random((cells[0], cells[1])).astype(np.float32)
    n = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = (n - n.mean()) / (n.std() + 1e-6)
    return n


def background(rng, n_ping=N_PING, n_s=N_S):
    cols = np.arange(n_s, dtype=np.float32)
    base = np.zeros(n_s, dtype=np.float32)
    base[:3] = 200.0                      # nadir altitude echo
    base[3:WC] = 6.0                      # water column
    onset = np.exp(-0.5 * ((cols[WC:WC + ONSET] - WC - 5) / 10.0) ** 2)
    base[WC:WC + ONSET] = 6.0 + 170.0 * onset
    decay = 1.05 - 0.35 * np.clip((cols - WC) / (n_s - WC), 0, 1)
    base[WC + ONSET:] = 95.0 * decay[WC + ONSET:]
    row = np.tile(base, (n_ping, 1))
    tex = value_noise(rng, (n_ping, n_s), (24, 14))
    row[:, WC:] *= (1.0 + 0.35 * tex[:, WC:])
    spk = rng.gamma(4.0, 0.25, (n_ping, n_s)).astype(np.float32)
    spk = np.clip(spk, 0.15, 1.9)
    glint = rng.random((n_ping, n_s)) < 0.02
    spk[glint] = rng.uniform(2.35, 2.62, glint.sum())
    row[:, WC:] *= spk[:, WC:]
    row[:, 3:WC] += rng.normal(0, 1.5, (n_ping, WC - 3))
    return row


def add_target(arr, rng, row_c, col0, ext_rows, ext_bright, ext_shadow,
               style='tex', peak=420.0):
    n_ping, n_s = arr.shape
    cols = np.arange(n_s, dtype=np.float32)
    sig_r = ext_rows / 2.355
    sig_b = ext_bright / 2.355
    half = int(3.0 * sig_r) + 4
    p0, p1 = max(0, int(row_c - half)), min(n_ping, int(row_c + half))
    # per-row edge jitter so the outline is not a perfect ellipse
    jit = value_noise(rng, (p1 - p0, 1), (max(4, (p1 - p0) // 12), 1))[:, 0]
    for k, p in enumerate(range(p0, p1)):
        env = math.exp(-0.5 * ((p - row_c) / sig_r) ** 2)
        if env < 0.03:
            continue
        e = min(1.0, 1.55 * env) * (0.85 + 0.3 * jit[k])
        col_c = col0
        prof = np.exp(-0.5 * ((cols - col_c) / sig_b) ** 2)
        bright = peak * min(1.0, e) * prof
        if style == 'tex':
            bright = bright * (0.55 + 0.65 * rng.random(n_s))
        elif style == 'solid':
            pass
        elif style == 'edge':
            edge = np.exp(-0.5 * ((np.abs(cols - col_c) - sig_b) / (sig_b * 0.5)) ** 2)
            bright = bright * (0.45 + 0.9 * edge)
        arr[p] = np.maximum(arr[p], bright)
        # hard black acoustic shadow beyond the contact
        s0 = int(col_c + 2.0 * sig_b)
        s1 = int(s0 + ext_shadow)
        if s1 > s0:
            lo, hi = max(0, s0), min(n_s, s1)
            arr[p, lo:hi] = arr[p, lo:hi] * (1.0 - 0.97 * min(1.0, 1.4 * env)) + 2.0
    return arr


def normalize_rowwise(arr):
    out = np.empty_like(arr, dtype=np.uint8)
    for i in range(arr.shape[0]):
        a = arr[i].astype(np.float32)
        p99 = np.percentile(a, 99)
        if p99 > 0:
            a = np.clip(a, 0, p99)
            a = (a / p99) * 255
        out[i] = a.astype(np.uint8)
    return out


def render(targets, seed=7):
    rng = np.random.default_rng(seed)
    port = background(rng)
    stbd = background(rng)
    for t in targets:
        arr = stbd if t['side'] == 's' else port
        add_target(arr, rng, t['row_c'], t['col0'], t['ext_rows'],
                   t['ext_bright'], t['ext_shadow'], t.get('style', 'tex'))
    pn = normalize_rowwise(port)
    sn = normalize_rowwise(stbd)
    rows = [np.concatenate([np.flip(p), s]) for p, s in zip(pn, sn)]
    img = np.vstack(rows)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


if __name__ == '__main__':
    m = YOLO('best.pt')
    combos = []
    for ext_rows in (60, 100, 160, 240, 340):
        for ext_bright in (30, 60, 110):
            for ext_shadow in (120, 240):
                combos.append((ext_rows, ext_bright, ext_shadow))
    # 4 targets per image to cut inference count
    for i in range(0, len(combos), 4):
        group = combos[i:i + 4]
        slots = [dict(side='s', row_c=250, col0=140),
                 dict(side='s', row_c=750, col0=140),
                 dict(side='p', row_c=250, col0=140),
                 dict(side='p', row_c=750, col0=140)]
        targets = []
        for (er, eb, es), sl in zip(group, slots):
            t = dict(sl); t.update(ext_rows=er, ext_bright=eb, ext_shadow=es)
            targets.append(t)
        img = render(targets, seed=11 + i)
        path = 'scratch_yolo/sweep_%03d.jpg' % i
        cv2.imwrite(path, img)
        r = m(path, conf=0.20, verbose=False)[0]
        print('== img %s combos=%s' % (path, group))
        hits = []
        for b in r.boxes:
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
            side = 'p' if (x1 + x2) / 2 < 512 else 's'
            hits.append((side, (y1 + y2) / 2, m.names[int(b.cls[0])], float(b.conf[0])))
        for t in targets:
            # match nearest hit in same side & row band
            best = None
            for h in hits:
                if h[0] == t['side'] and abs(h[1] - t['row_c']) < t['ext_rows']:
                    if best is None or h[3] > best[3]:
                        best = h
            print('   rows=%3d bright=%3d shadow=%3d side=%s -> %s' % (
                t['ext_rows'], t['ext_bright'], t['ext_shadow'], t['side'],
                ('%s %.3f' % (best[2], best[3])) if best else 'MISS'))
