#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TEMP harness v3: hard-edged saturated contacts + irregular black shadow."""
import math
import numpy as np
import cv2
from ultralytics import YOLO

N_PING = 1000
N_S = 512
WC = 20
ONSET = 26

m = YOLO('best.pt')


def value_noise(rng, shape, cells):
    g = rng.random((cells[0], cells[1])).astype(np.float32)
    n = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = (n - n.mean()) / (n.std() + 1e-6)
    return n


def background(rng, n_ping=N_PING, n_s=N_S):
    cols = np.arange(n_s, dtype=np.float32)
    base = np.zeros(n_s, dtype=np.float32)
    base[:3] = 210.0
    base[3:WC] = 6.0
    onset = np.exp(-0.5 * ((cols[WC:WC + ONSET] - WC - 4) / 9.0) ** 2)
    base[WC:WC + ONSET] = 6.0 + 160.0 * onset
    decay = 1.05 - 0.30 * np.clip((cols - WC) / (n_s - WC), 0, 1)
    base[WC + ONSET:] = 105.0 * decay[WC + ONSET:]
    row = np.tile(base, (n_ping, 1))
    tex = value_noise(rng, (n_ping, n_s), (30, 16))
    row[:, WC:] *= (1.0 + 0.22 * tex[:, WC:])
    spk = rng.gamma(3.0, 0.33, (n_ping, n_s)).astype(np.float32)
    spk = np.clip(spk, 0.18, 2.05)
    glint = rng.random((n_ping, n_s)) < 0.018
    spk[glint] = rng.uniform(2.25, 2.45, glint.sum())
    row[:, WC:] *= spk[:, WC:]
    row[:, 3:WC] += rng.normal(0, 1.5, (n_ping, WC - 3))
    return row


def add_contact(arr, rng, row_c, col0, ext_rows, ext_bright, ext_shadow,
                kind='wreck', peak=250.0):
    sig_r = ext_rows / 2.355 * 1.35      # hard edge: use wider sigma, clip at 1.0
    sig_b = ext_bright / 2.355 * 1.35
    half_r = int(2.2 * sig_r) + 4
    p0, p1 = max(0, row_c - half_r), min(arr.shape[0], row_c + half_r)
    # irregular outline noise (per row) for bright body and shadow length
    bn = value_noise(rng, (p1 - p0, 1), (max(8, (p1 - p0) // 6), 1))[:, 0]
    sn = value_noise(rng, (p1 - p0, 1), (max(8, (p1 - p0) // 5), 1))[:, 0]
    cols = np.arange(arr.shape[1], dtype=np.float32)
    for k, p in enumerate(range(p0, p1)):
        dr = (p - row_c) / sig_r
        if abs(dr) > 2.2:
            continue
        # hard-edged body: half-width wobbles with row
        hw = sig_b * math.sqrt(max(0.0, 1.0 - (dr / 2.2) ** 2)) * (1.0 + 0.30 * bn[k])
        if hw < 1.5:
            continue
        lo, hi = int(col0 - hw), int(col0 + hw) + 1
        lo, hi = max(0, lo), min(arr.shape[1], hi)
        body = np.full(hi - lo, peak, np.float32)
        if kind == 'wreck':
            # dark internal structure: compartment cross-lines + holes
            for lc in range(p0, p1, 7):
                if abs(p - lc) <= 1:
                    body *= 0.25
            holes = rng.random(hi - lo) < 0.10
            body[holes] *= 0.2
            edge = rng.random(hi - lo) < 0.25
            body[edge] *= rng.uniform(0.5, 1.0, edge.sum())
        elif kind == 'mine':
            edge = rng.random(hi - lo) < 0.2
            body[edge] *= rng.uniform(0.6, 1.0, edge.sum())
        elif kind == 'net':
            body *= np.where(rng.random(hi - lo) < 0.45, 0.15, 1.0)
        elif kind == 'pipeline':
            tooth = 1.4 if (p % 26) < 6 else 1.0
            body *= tooth
        arr[p, lo:hi] = np.maximum(arr[p, lo:hi], np.minimum(body, peak))
        # irregular hard black shadow starting at body edge
        s_len = ext_shadow * (0.7 + 0.6 * (0.5 + 0.5 * sn[k]))
        s0, s1 = hi - 1, int(hi - 1 + s_len)
        s1 = min(arr.shape[1], s1)
        if s1 > s0:
            arr[p, s0:s1] = 3.0 + 2.0 * rng.random(s1 - s0)
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


def finish(port, stbd):
    pn = normalize_rowwise(port)
    sn = normalize_rowwise(stbd)
    rows = [np.concatenate([np.flip(p), s]) for p, s in zip(pn, sn)]
    return cv2.cvtColor(np.vstack(rows), cv2.COLOR_GRAY2BGR)


def run(img, tag, conf=0.20):
    path = 'scratch_yolo/v3_%s.jpg' % tag
    cv2.imwrite(path, img)
    res = m(path, conf=conf, verbose=False)[0]
    out = []
    for b in res.boxes:
        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
        out.append('%s %.3f box=%dx%d yc=%.0f %s' % (
            m.names[int(b.cls[0])], float(b.conf[0]), x2 - x1, y2 - y1,
            (y1 + y2) / 2, 'port' if (x1 + x2) / 2 < 512 else 'stbd'))
    print('%-22s -> %s' % (tag, out or 'NONE'))
    return out


if __name__ == '__main__':
    variants = [
        ('wreck', 120, 50, 90), ('wreck', 180, 70, 120),
        ('wreck', 240, 90, 150), ('wreck', 90, 40, 70),
        ('mine', 80, 45, 80), ('mine', 120, 55, 100),
        ('pipeline', 320, 16, 40), ('net', 160, 80, 70),
    ]
    for i in range(0, len(variants), 2):
        rng = np.random.default_rng(31 + i)
        port = background(rng); stbd = background(rng)
        for j, (kind, er, eb, es) in enumerate(variants[i:i + 2]):
            arr = stbd if j == 0 else port
            add_contact(arr, rng, 250 + 500 * j, 150, er, eb, es, kind)
        run(finish(port, stbd), 'pair%d' % i)
