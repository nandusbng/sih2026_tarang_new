#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scratch harness: render synthetic side-scan target archetypes straight into
raster space (ping x sample), apply the same per-row normalization that
xtf_parser.normalize_samples() uses, save a 1000x1024 JPG and run the real
YOLO model on it.  Used to tune target appearance before porting into
generate_demo_xtf.py.
"""
import sys
import math
import numpy as np
import cv2
from ultralytics import YOLO

N_PING = 1000
N_S = 512
M_PER_PING = 7.78

WC = 80            # water column samples (dark)
ONSET = 40         # bright seabed onset band


def value_noise(rng, shape, cells):
    g = rng.random((cells[0], cells[1])).astype(np.float32)
    n = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = (n - n.mean()) / (n.std() + 1e-6)
    return n


def background(rng, n_ping=N_PING, n_s=N_S):
    """raw float samples (n_ping, n_s) for one channel."""
    cols = np.arange(n_s, dtype=np.float32)
    base = np.zeros(n_s, dtype=np.float32)
    base[:3] = 210.0                       # nadir altitude echo
    base[3:WC] = 7.0                       # water column
    onset = np.exp(-0.5 * ((cols[WC:WC+ONSET] - WC - 6) / 14.0) ** 2)
    base[WC:WC+ONSET] = 7.0 + 180.0 * onset
    decay = 1.05 - 0.35 * np.clip((cols - WC) / (n_s - WC), 0, 1)
    base[WC+ONSET:] = 100.0 * decay[WC+ONSET:]
    row = np.tile(base, (n_ping, 1))
    # low frequency seabed texture, correlated in ping & range
    tex = value_noise(rng, (n_ping, n_s), (20, 12))
    row[:, WC:] *= (1.0 + 0.40 * tex[:, WC:])
    # multiplicative speckle
    spk = rng.gamma(4.0, 0.25, (n_ping, n_s)).astype(np.float32)
    spk = np.clip(spk, 0.15, 1.9)
    # ~2% very bright speckle glints -> keeps per-row p99 stable near 240
    glint = rng.random((n_ping, n_s)) < 0.02
    spk[glint] = rng.uniform(2.35, 2.62, glint.sum())
    row[:, WC:] *= spk[:, WC:]
    row[:, 3:WC] += rng.normal(0, 1.5, (n_ping, WC - 3))
    return row


def add_target(arr, rng, kind, ping_c, col0, **kw):
    """draw one contact: saturated bright return + hard black acoustic shadow.
    sig_al is in pings, sig_ac / sh_len in samples, slope in samples/ping."""
    n_ping, n_s = arr.shape
    cols = np.arange(n_s, dtype=np.float32)
    P = dict(
        shipwreck=dict(sig_al=40.0, sig_ac=8.0, slope=0.15, sh_len=230, sh_fac=0.03, peak=255.0),
        mine_cylinder=dict(sig_al=18.0, sig_ac=10.0, slope=0.0, sh_len=130, sh_fac=0.04, peak=255.0),
        crab_pot=dict(sig_al=10.0, sig_ac=6.0, slope=0.0, sh_len=85, sh_fac=0.05, peak=255.0),
        ghost_net=dict(sig_al=25.0, sig_ac=14.0, slope=0.05, sh_len=80, sh_fac=0.30, peak=230.0),
        submarine_pipeline=dict(sig_al=130.0, sig_ac=4.5, slope=0.05, sh_len=30, sh_fac=0.08, peak=250.0),
    )[kind]
    P.update(kw)
    sig_al, sig_ac, slope = P['sig_al'], P['sig_ac'], P['slope']
    sh_len, sh_fac, peak = P['sh_len'], P['sh_fac'], P['peak']

    half = int(3.0 * sig_al) + 4
    p0, p1 = max(0, int(ping_c - half)), min(n_ping, int(ping_c + half))
    for p in range(p0, p1):
        d = (p - ping_c) / sig_al
        if kind == 'submarine_pipeline':
            env = 1.0 / (1.0 + math.exp((abs(d) - 1.0) * 10.0))
        else:
            env = math.exp(-0.5 * d * d)
        if env < 0.03:
            continue
        along_m = (p - ping_c) * M_PER_PING
        col_c = col0 + slope * (p - ping_c)
        if kind == 'submarine_pipeline':
            tooth = 1.0 + 1.5 * math.exp(-0.5 * (((along_m % 140.0) - 70.0) / 18.0) ** 2)
            sig = sig_ac * tooth
        else:
            sig = sig_ac
        prof = np.exp(-0.5 * ((cols - col_c) / sig) ** 2)
        bright = peak * min(1.0, 1.7 * env) * prof
        if kind == 'ghost_net':
            bright = bright * (0.30 + 0.90 * rng.random(n_s))
        elif kind == 'shipwreck':
            bright = bright * (0.75 + 0.35 * rng.random(n_s))
        arr[p] = np.maximum(arr[p], bright)
        # hard black acoustic shadow beyond the contact
        s0 = int(col_c + 2.2 * sig_ac)
        s1 = int(s0 + sh_len)
        if s1 > s0:
            lo, hi = max(0, s0), min(n_s, s1)
            arr[p, lo:hi] = arr[p, lo:hi] * (1.0 - 0.97 * env) + 2.0
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
        add_target(arr, rng, t['kind'], t['ping_c'], t['col0'], **t.get('kw', {}))
    pn = normalize_rowwise(port)
    sn = normalize_rowwise(stbd)
    rows = [np.concatenate([np.flip(p), s]) for p, s in zip(pn, sn)]
    img = np.vstack(rows)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


if __name__ == '__main__':
    targets = [
        dict(kind='shipwreck', side='s', ping_c=250, col0=170),
        dict(kind='mine_cylinder', side='s', ping_c=700, col0=200),
        dict(kind='crab_pot', side='p', ping_c=250, col0=200),
        dict(kind='ghost_net', side='p', ping_c=700, col0=230),
        dict(kind='submarine_pipeline', side='s', ping_c=480, col0=360),
    ]
    img = render(targets)
    out = sys.argv[1] if len(sys.argv) > 1 else 'scratch_yolo/arch_test.jpg'
    cv2.imwrite(out, img)
    m = YOLO('best.pt')
    r = m(out, conf=0.05, verbose=False)[0]
    print('image', out, img.shape)
    if len(r.boxes) == 0:
        print('  NO DETECTIONS')
    for b in r.boxes:
        print('  %-18s %.3f  xyxy=%s' % (m.names[int(b.cls[0])], float(b.conf[0]),
                                         [round(float(x), 1) for x in b.xyxy[0]]))
