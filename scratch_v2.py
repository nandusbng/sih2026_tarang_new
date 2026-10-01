#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TEMP harness v2: procedural contacts with real-sonar texture statistics,
run through the exact per-row p99 normalization of xtf_parser, then best.pt
at production settings. Positive control = real reference crop pasted in."""
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
                kind='wreck', peak=252.0, rotate_deg=0.0):
    """Draw contact into a local patch then (optionally) rotate and paste."""
    sig_r = ext_rows / 2.355
    sig_b = ext_bright / 2.355
    half_r = int(3.0 * sig_r) + 6
    pad = ext_shadow + int(6 * sig_b) + 8
    ph, pw = 2 * half_r, pad + int(6 * sig_b) + 8
    patch = np.zeros((ph, pw), np.float32)
    rows = np.arange(ph) - half_r
    cols = np.arange(pw)
    edge_n = value_noise(rng, (ph, 1), (max(6, ph // 10), 1))[:, 0]
    sh_n = value_noise(rng, (ph, 1), (max(6, ph // 8), 1))[:, 0]
    for k in range(ph):
        d = rows[k] / sig_r
        env = math.exp(-0.5 * d * d)
        if env < 0.025:
            continue
        e = min(1.0, 1.6 * env) * (0.9 + 0.2 * edge_n[k])
        if kind == 'pipeline':
            envl = 1.0 / (1.0 + math.exp((abs(d) - 1.1) * 8.0))
            e = min(1.0, 1.5 * envl)
        prof = np.exp(-0.5 * ((cols - col0) / sig_b) ** 2)
        bright = peak * min(1.0, e) * prof
        # internal high-contrast structure: speckle + dark compartment lines
        if kind == 'wreck':
            inner = 0.45 + 0.85 * rng.random(pw)
            lines = np.ones(pw)
            for lc in rng.integers(col0 - 2 * sig_b, col0 + 2 * sig_b, 3):
                lines = np.minimum(lines, 0.25 + np.abs(cols - lc) / 6.0)
            bright = bright * inner * np.clip(lines, 0.25, 1.0)
            bright = np.maximum(bright, peak * min(1.0, e) * prof * 0.55)
        elif kind == 'mine':
            bright = bright * (0.7 + 0.5 * rng.random(pw))
        elif kind == 'pipeline':
            tooth = 1.0 + 1.2 * math.exp(-0.5 * (((rows[k] * 1.95 % 60.0) - 30) / 7.0) ** 2)
            bright = bright * tooth * (0.7 + 0.5 * rng.random(pw))
        elif kind == 'net':
            bright = bright * (0.25 + 1.0 * rng.random(pw))
        patch[k] = np.maximum(patch[k], bright)
        # acoustic shadow: near-black, irregular length, slight speckle
        s_len = ext_shadow * (0.75 + 0.5 * (0.5 + 0.5 * sh_n[k])) * min(1.0, 1.5 * env)
        s0 = int(col0 + 1.8 * sig_b)
        s1 = int(s0 + s_len)
        if s1 > s0:
            patch[k, s0:s1] = np.maximum(patch[k, s0:s1], 0.0)
            patch[k, s0:s1] = 3.0 + 2.5 * rng.random(s1 - s0)
    if rotate_deg:
        M = cv2.getRotationMatrix2D((pw / 2, ph / 2), rotate_deg, 1.0)
        ph2, pw2 = ph, pw
        patch = cv2.warpAffine(patch, M, (pw2, ph2),
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    r0, c0 = int(row_c - patch.shape[0] / 2), 0
    h, w = patch.shape
    r0 = max(0, r0); r1 = min(arr.shape[0], r0 + h)
    w1 = min(arr.shape[1], w)
    sub = arr[r0:r1, 0:w1]
    pp = patch[:r1 - r0, :w1]
    # shadow must overwrite bg; bright must dominate bg
    arr[r0:r1, 0:w1] = np.where(pp > 20, np.maximum(sub, pp),
                                np.where(pp < 12, pp, sub))
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


def run(img, tag):
    path = 'scratch_yolo/v2_%s.jpg' % tag
    cv2.imwrite(path, img)
    res = m(path, conf=0.20, verbose=False)[0]
    out = []
    for b in res.boxes:
        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
        out.append('%s %.3f box=%dx%d yc=%.0f %s' % (
            m.names[int(b.cls[0])], float(b.conf[0]), x2 - x1, y2 - y1,
            (y1 + y2) / 2, 'port' if (x1 + x2) / 2 < 512 else 'stbd'))
    print('%-22s -> %s' % (tag, out or 'NONE'))
    return out


if __name__ == '__main__':
    # positive control: real crop through production normalization
    rng = np.random.default_rng(5)
    port = background(rng); stbd = background(rng)
    ref = cv2.imread('scratch_ref_crop.png', cv2.IMREAD_GRAYSCALE).astype(np.float32)
    stbd[100:100 + ref.shape[0], 100:100 + ref.shape[1]] = ref
    run(finish(port, stbd), 'control_refcrop')

    variants = [
        ('wreck', 120, 60, 200, 0), ('wreck', 200, 80, 260, 0),
        ('wreck', 120, 60, 200, 25), ('wreck', 200, 80, 260, 25),
        ('mine', 70, 40, 120, 0), ('mine', 110, 55, 160, 0),
        ('pipeline', 300, 18, 45, 0), ('net', 150, 90, 90, 0),
    ]
    for i in range(0, len(variants), 2):
        rng = np.random.default_rng(21 + i)
        port = background(rng); stbd = background(rng)
        for j, (kind, er, eb, es, rot) in enumerate(variants[i:i + 2]):
            arr = stbd if j == 0 else port
            add_contact(arr, rng, 250 + 500 * j, 150, er, eb, es, kind, rotate_deg=rot)
        run(finish(port, stbd), 'pair%d' % i)
