#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_demo_xtf.py -- TARANG hackathon demo XTF generator.

Produces `tarang_synthetic_survey_002.xtf` in the project root: a realistic
synthetic side-scan-sonar XTF file containing

  * a 7-leg lawnmower (boustrophedon) survey over a ~3.0 km x 4.2 km box
    centred on 13.0827 N, 80.5000 E (offshore waters east of Chennai, India),
  * 12000 sonar pings (PORT + STARBOARD, 512 x uint8 samples each),
    1.0 s apart starting 2026-09-20 09:00:00 (~2.05 m along-track per ping),
  * per-ping navigation (lat/lon/heading/depth/altitude/speed),
  * 8 embedded acoustic contacts in 4 geographic groups of 2, rendered as
    hard-edged saturated bright returns with irregular black acoustic
    shadows -- the signature side-scan sonar targets produce in real
    waterfall imagery (validated against the TARANG YOLO model best.pt).

Group geometry: intra-group contact spacing ~700 m (DBSCAN eps=1500 m,
min_samples=2 merges each pair into one hotspot), inter-group spacing
>= ~1660 m so the four hotspots stay separable, all inside the compact
survey box.

pyxtf has no writer, so the binary file is assembled directly from pyxtf's
own ctypes structures (XTFFileHeader / XTFPingHeader / XTFPingChanHeader)
using to_bytes() -- the exact inverse of what pyxtf.xtf_read() parses.

The existing tarang_synthetic_survey_001.xtf is NEVER touched.
"""

import ctypes
import math
import os
import datetime

import numpy as np
import cv2
import pyxtf
from pyxtf import (
    XTFFileHeader,
    XTFPingHeader,
    XTFPingChanHeader,
    XTFHeaderType,
    XTFChannelType,
    XTFSampleFormat,
)

# ----------------------------------------------------------------------------
# Survey configuration
# ----------------------------------------------------------------------------
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "tarang_synthetic_survey_002.xtf")

CENTER_LAT = 13.0827          # survey box centre (offshore east of Chennai)
# TARANG only routes cleanup for offshore coordinates. supabase_service.
# is_offshore_coordinate() treats this east-coast box (7-22.5 N, 77-82 E) as
# offshore only when lon >= 80.40, so the whole 3 km E-W box (centre +/- ~0.014
# deg) must sit east of that boundary or its detections are excluded from
# hotspot clustering and no cleanup route can form. 80.50 keeps ~5 km of margin.
CENTER_LON = 80.5000

M_PER_DEG_LAT = 111320.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(CENTER_LAT))  # ~108431 m

BOX_EW_M = 3000.0             # long axis (east-west), 1.62 NM
BOX_NS_M = 4200.0             # short axis (north-south), 7 legs @ 600 m
N_LEGS = 7                    # parallel E-W legs
N_PINGS = 12000               # total sonar pings
PING_DT_S = 1.0               # ping interval

START_TIME = datetime.datetime(2026, 9, 21, 9, 0, 0)

N_SAMPLES = 512               # samples per channel per ping
SAMPLE_SPACING_M = 0.25       # 512 * 0.25 = 128 m swath range per side
CRUISE_SPEED = 2.05           # m/s (SensorSpeed field, matches ping spacing)
SENSOR_DEPTH = 25.0           # m

# Side-scan waterfall background profile (raw uint8 levels before the
# per-row p99 normalization applied by xtf_parser.normalize_samples).
WATER_COLUMN_SAMPLES = 20     # dark water column either side of nadir
SEABED_LEVEL = 105.0          # mid-grey speckled seabed return
CONTACT_LEVEL = 250.0         # saturated hard-edged target return
SHADOW_LEVEL = 3.0            # near-black acoustic shadow

# Acoustic contacts in survey-box local metres (x = east, y = north of
# centre).  Four groups of two; each contact sits ~60 m to starboard of the
# leg that insonifies it.  Fields:
#   (name, x_m, y_m, along-track extent rows, bright width samples,
#    shadow length samples, archetype)
TARGET_CENTRES = [
    ("G1A_wreck",     -1250.0, -2160.0, 60.0, 35.0, 60.0, "wreck"),
    ("G1B_mine",       -550.0, -2160.0, 55.0, 32.0, 55.0, "mine"),
    ("G2A_mine",        600.0,  -760.0, 60.0, 35.0, 60.0, "mine"),
    ("G2B_wreck",      1300.0,  -760.0, 65.0, 38.0, 65.0, "wreck"),
    ("G3A_wreck",     -1250.0,   640.0, 65.0, 38.0, 65.0, "wreck"),
    ("G3B_mine",       -550.0,   640.0, 60.0, 35.0, 60.0, "mine"),
    ("G4A_mine",        600.0,  2040.0, 55.0, 32.0, 55.0, "mine"),
    ("G4B_wreck",      1300.0,  2040.0, 60.0, 35.0, 60.0, "wreck"),
]


def metres_to_latlon(x_m, y_m):
    return (CENTER_LAT + y_m / M_PER_DEG_LAT,
            CENTER_LON + x_m / M_PER_DEG_LON)


# ----------------------------------------------------------------------------
# Track geometry: lawnmower over the box, legs run east-west
# ----------------------------------------------------------------------------
def build_track():
    """Waypoints of the boustrophedon track in local metres."""
    x0, x1 = -BOX_EW_M / 2.0, BOX_EW_M / 2.0
    ys = np.linspace(-BOX_NS_M / 2.0, BOX_NS_M / 2.0, N_LEGS)
    pts = []
    for i, y in enumerate(ys):
        if i % 2 == 0:      # west -> east
            pts.append((x0, y))
            pts.append((x1, y))
        else:               # east -> west
            pts.append((x1, y))
            pts.append((x0, y))
    return np.array(pts, dtype=np.float64)


def sample_track(waypoints, n):
    """Evenly sample n points by arc length along the polyline."""
    seg = np.diff(waypoints, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate(([0.0], np.cumsum(seg_len)))
    total = cum[-1]
    s = np.linspace(0.0, total, n)
    idx = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg_len) - 1)
    frac = (s - cum[idx]) / seg_len[idx]
    pts = waypoints[idx] + seg[idx] * frac[:, None]
    return pts, total


def headings_from_track(pts):
    """Per-point heading (deg clockwise from north) via central differences."""
    d = np.gradient(pts, axis=0)          # (dx_east, dy_north)
    hdg = np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360.0
    return hdg


# ----------------------------------------------------------------------------
# Sonar sample rendering
# ----------------------------------------------------------------------------
def value_noise(rng, shape, cells):
    """Smooth low-frequency 2-D noise in [-1, 1] (seabed texture)."""
    g = rng.random((cells[0], cells[1])).astype(np.float32)
    n = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = (n - n.mean()) / (n.std() + 1e-6)
    return n


def seabed_profile():
    """Range profile of one channel: nadir echo, water column, seabed."""
    cols = np.arange(N_SAMPLES, dtype=np.float32)
    base = np.zeros(N_SAMPLES, dtype=np.float32)
    base[:3] = 210.0                                   # nadir altitude echo
    base[3:WATER_COLUMN_SAMPLES] = 6.0                 # dark water column
    wc, on = WATER_COLUMN_SAMPLES, 26
    onset = np.exp(-0.5 * ((cols[wc:wc + on] - wc - 4) / 9.0) ** 2)
    base[wc:wc + on] = 6.0 + 160.0 * onset             # first bottom return
    decay = 1.05 - 0.30 * np.clip((cols - wc) / (N_SAMPLES - wc), 0, 1)
    base[wc + on:] = SEABED_LEVEL * decay[wc + on:]    # TVG-like seabed
    return base


def build_background(rng):
    """(n_pings, n_samples) float raw samples for one channel."""
    base = seabed_profile()
    row = np.tile(base, (N_PINGS, 1))
    wc = WATER_COLUMN_SAMPLES
    tex = value_noise(rng, (N_PINGS, N_SAMPLES), (max(8, N_PINGS // 33), 16))
    row[:, wc:] *= (1.0 + 0.22 * tex[:, wc:])
    spk = rng.gamma(3.0, 0.33, (N_PINGS, N_SAMPLES)).astype(np.float32)
    spk = np.clip(spk, 0.18, 1.85)                     # multiplicative speckle
    glint = rng.random((N_PINGS, N_SAMPLES)) < 0.018   # bright speckle glints
    spk[glint] = rng.uniform(2.25, 2.45, glint.sum())  # stabilise row p99
    row[:, wc:] *= spk[:, wc:]
    row[:, 3:wc] += rng.normal(0, 1.5, (N_PINGS, wc - 3))
    # Cap the background below the contact level: keeps every row's p99 at
    # the same value (stable normalization in xtf_parser) and lets saturated
    # contact returns be unambiguously identified in the raw samples.
    return np.minimum(row, 235.0)


class Contact:
    """One acoustic contact rendered into ping/sample space.

    Real side-scan contacts are hard-edged saturated returns with internal
    structure and an irregular near-black acoustic shadow trailing away from
    nadir -- not smooth Gaussian blobs.  Extents are given in waterfall
    pixels: rows along-track, samples across-track.
    """

    def __init__(self, idx, cx, cy, ext_rows, ext_bright, ext_shadow, kind):
        self.cx, self.cy = cx, cy
        self.kind = kind
        self.sig_r = ext_rows / 2.355 * 1.35           # rows
        self.sig_b = ext_bright / 2.355 * 1.35         # samples
        self.half_rows = int(2.2 * self.sig_r) + 4
        self.ext_shadow = ext_shadow
        self.ph1, self.ph2 = idx * 1.7 + 0.9, idx * 2.3 + 0.3
        self.rng = np.random.default_rng(4000 + idx)

    def edge_noise(self, p):
        """Smooth per-row outline wobble in [-1, 1]."""
        return (0.5 * math.sin(p * 0.11 + self.ph1)
                + 0.3 * math.sin(p * 0.031 + self.ph2)
                + 0.2 * math.sin(p * 0.23 + self.ph1 * 2.0))

    def render_into(self, chan, ping_idx, along_rows, col):
        """Paint body + shadow of this contact into one channel row."""
        dr = along_rows / self.sig_r
        if abs(dr) > 2.2:
            return
        hw = self.sig_b * math.sqrt(max(0.0, 1.0 - (dr / 2.2) ** 2))
        hw *= 1.0 + 0.30 * self.edge_noise(ping_idx)
        if hw < 1.5:
            return
        lo, hi = int(col - hw), int(col + hw) + 1
        lo, hi = max(0, lo), min(N_SAMPLES, hi)
        if hi <= lo:
            return
        body = np.full(hi - lo, CONTACT_LEVEL, np.float32)
        if self.kind == "wreck":
            if (ping_idx % 37) < 2:                    # compartment cross-line
                body *= 0.3
            holes = self.rng.random(hi - lo) < 0.04
            body[holes] *= 0.25
            fr = self.rng.random(hi - lo) < 0.12
            body[fr] *= self.rng.uniform(0.6, 1.0, fr.sum())
        else:
            fr = self.rng.random(hi - lo) < 0.2
            body[fr] *= self.rng.uniform(0.6, 1.0, fr.sum())
        chan[lo:hi] = np.maximum(chan[lo:hi], np.minimum(body, CONTACT_LEVEL))
        # irregular hard black acoustic shadow beyond the contact
        s_len = self.ext_shadow * (0.7 + 0.6 * (0.5 + 0.5 * self.edge_noise(ping_idx + 500)))
        s0, s1 = hi - 1, min(N_SAMPLES, int(hi - 1 + s_len))
        if s1 > s0:
            chan[s0:s1] = SHADOW_LEVEL + 2.0 * self.rng.random(s1 - s0)


def render_ping_samples(px, py, hdg_deg, ping_idx, contacts):
    """Build (port, stbd) uint8 sample rows for one ping at local (px, py)."""
    port = BG_PORT[ping_idx].copy()
    stbd = BG_STBD[ping_idx].copy()

    h = math.radians(hdg_deg)
    fwd = np.array([math.sin(h), math.cos(h)])      # east, north
    stbd_u = np.array([math.sin(h + math.pi / 2), math.cos(h + math.pi / 2)])

    for c in contacts:
        v = np.array([c.cx - px, c.cy - py])
        along_m = float(v @ fwd)
        perp = float(v @ stbd_u)                    # + = starboard, - = port
        if abs(along_m) > c.half_rows * M_PER_PING or abs(perp) > 110.0:
            continue
        col = abs(perp) / SAMPLE_SPACING_M
        if col >= N_SAMPLES - 3:
            continue
        along_rows = along_m / M_PER_PING
        c.render_into(stbd if perp >= 0 else port, ping_idx, along_rows, col)

    port = np.clip(port, 0, 255).astype(np.uint8)
    stbd = np.clip(stbd, 0, 255).astype(np.uint8)
    return port, stbd


# ----------------------------------------------------------------------------
# XTF file assembly (pyxtf ctypes structs, no writer exists in pyxtf)
# ----------------------------------------------------------------------------
def build_file_header():
    fh = XTFFileHeader()
    fh.FileFormat = 1
    fh.SystemType = 1
    fh.RecordingProgramName = b"TARANG"
    fh.RecordingProgramVersion = b"1.0"
    fh.SonarName = b"TARANG SYNTH"
    fh.SonarType = 1
    fh.NoteString = b"TARANG DEMO SYNTHETIC SURVEY 002 - CHENNAI OFFSHORE"
    fh.ThisFileName = b"tarang_synthetic_survey_002.xtf"
    fh.NavUnits = 0                     # degrees (same as survey 001)
    fh.NumberOfSonarChannels = 2
    fh.NumberOfBathymetryChannels = 0
    
    # Initialize ALL channel slots to zero/empty to prevent garbage data
    # pyxtf can misread uninitialized memory as additional channels
    for i in range(6):  # XTFFileHeader has 6 channel slots
        ci = fh.ChanInfo[i]
        ci.TypeOfChannel = 0
        ci.SubChannelNumber = 0
        ci.BytesPerSample = 0
        ci.SampleFormat = 0
        ci.Reserved = 0
        ci.ChannelName = b""
        ci.VoltScale = 0.0
        ci.Frequency = 0.0
        ci.HorizBeamAngle = 0.0
        ci.BeamWidth = 0.0
        ci.TiltAngle = 0.0
    
    # Now set up the actual 2 channels we want
    for i, (ctype, name) in enumerate(
            [(XTFChannelType.port, b"PORT"), (XTFChannelType.stbd, b"STARBOARD")]):
        ci = fh.ChanInfo[i]
        ci.TypeOfChannel = int(ctype.value)
        ci.SubChannelNumber = 0
        ci.BytesPerSample = 1
        ci.SampleFormat = int(XTFSampleFormat.byte.value)   # 8 -> uint8
        ci.Reserved = 1024
        ci.ChannelName = name
        ci.VoltScale = 0.0
        ci.Frequency = 300.0
        ci.HorizBeamAngle = 1.0
        ci.BeamWidth = 40.0
        ci.TiltAngle = 0.0
    return fh


def build_chan_header(chan_num, name):
    ch = XTFPingChanHeader()
    ch.ChannelNumber = chan_num
    ch.SlantRange = N_SAMPLES * SAMPLE_SPACING_M
    ch.GroundRange = N_SAMPLES * SAMPLE_SPACING_M
    ch.TimeDelay = 0.0
    ch.TimeDuration = 2.0 * ch.SlantRange / 1500.0
    ch.SecondsPerPing = PING_DT_S
    ch.Frequency = 300
    ch.NumSamples = N_SAMPLES
    ch.MillivoltScale = 100
    ch.Weight = 0
    return ch


def build_ping_header(i, t, lat, lon, hdg, depth, alt, speed):
    ph = XTFPingHeader()                    # HeaderType defaults to sonar
    ph.NumChansToFollow = 2
    ph.NumBytesThisRecord = (ctypes.sizeof(XTFPingHeader)
                             + 2 * (ctypes.sizeof(XTFPingChanHeader)
                                    + N_SAMPLES * 1))
    ph.PingNumber = i
    ph.Year = t.year
    ph.Month = t.month
    ph.Day = t.day
    ph.Hour = t.hour
    ph.Minute = t.minute
    ph.Second = t.second
    ph.HSeconds = t.microsecond // 10000
    ph.JulianDay = t.toordinal() + 1721425
    ph.SoundVelocity = 1500.0
    ph.WaterTemperature = 28.5
    ph.ComputedSoundVelocity = 1500.0
    ph.ShipSpeed = speed
    ph.ShipGyro = hdg
    ph.ShipYcoordinate = lat
    ph.ShipXcoordinate = lon
    ph.SpeedLog = speed
    ph.SensorSpeed = speed
    ph.SensorYcoordinate = lat
    ph.SensorXcoordinate = lon
    ph.SensorDepth = depth
    ph.SensorHeading = hdg
    ph.SensorPrimaryAltitude = alt          # altitude above seabed
    ph.SensorAuxAltitude = alt
    ph.FixTimeHour = t.hour
    ph.FixTimeMinute = t.minute
    ph.FixTimeSecond = t.second
    ph.ComputerClockHour = t.hour
    ph.ComputerClockMinute = t.minute
    ph.ComputerClockSecond = t.second
    ph.ComputerClockHsec = t.microsecond // 10000
    return ph


# module-level state filled by generate() before rendering
BG_PORT = None
BG_STBD = None
M_PER_PING = 1.0


def generate():
    global BG_PORT, BG_STBD, M_PER_PING

    rng = np.random.default_rng(20260920)

    waypoints = build_track()
    pts, total_len_m = sample_track(waypoints, N_PINGS)
    hdgs = headings_from_track(pts)
    M_PER_PING = total_len_m / (N_PINGS - 1)

    # Seabed background for both channels (real-sonar speckle statistics).
    BG_PORT = build_background(np.random.default_rng(20260921))
    BG_STBD = build_background(np.random.default_rng(20260922))

    contacts = [Contact(i, cx, cy, er, eb, es, kind)
                for i, (_n, cx, cy, er, eb, es, kind) in enumerate(TARGET_CENTRES)]

    # Sanity: every contact must be insonified by exactly one leg and its
    # waterfall footprint must stay clear of the 1000-ping image chunk
    # boundaries used by xtf_parser (otherwise a contact is sliced in two).
    for (name, cx, cy, er, _eb, _es, _k) in TARGET_CENTRES:
        d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
        rc = int(np.argmin(d))
        half = int(2.2 * (er / 2.355 * 1.35)) + 14
        lo, hi = rc - half, rc + half
        assert lo >= 0 and hi < N_PINGS, (name, rc)
        assert lo // 1000 == hi // 1000, (name, rc)
        assert d[rc] < 150.0, (name, d[rc])

    fh = build_file_header()
    ch_port = build_chan_header(0, "PORT")
    ch_stbd = build_chan_header(1, "STARBOARD")

    n_targets = 0
    with open(OUT_PATH, "wb") as f:
        f.write(bytes(fh))
        for i in range(N_PINGS):
            px, py = float(pts[i, 0]), float(pts[i, 1])
            t = START_TIME + datetime.timedelta(seconds=PING_DT_S * i)
            lat, lon = metres_to_latlon(px, py)
            hdg = float(hdgs[i])
            depth = SENSOR_DEPTH + rng.normal(0.0, 0.3)
            alt = float(np.clip(rng.normal(5.0, 1.0), 3.0, 8.0))
            speed = float(np.clip(rng.normal(CRUISE_SPEED, 0.1), 1.6, 2.6))

            port, stbd = render_ping_samples(px, py, hdg, i, contacts)
            if int((port >= 248).sum()) + int((stbd >= 248).sum()) >= 12:
                n_targets += 1

            ph = build_ping_header(i, t, lat, lon, hdg, depth, alt, speed)
            ph.ping_chan_headers = [ch_port, ch_stbd]
            ph.data = [port, stbd]
            f.write(ph.to_bytes())

    size = os.path.getsize(OUT_PATH)
    print("Wrote {} ({:.2f} MB)".format(OUT_PATH, size / 1e6))
    print("  pings: {}  ({} carry saturated contact returns)".format(N_PINGS, n_targets))
    print("  along-track spacing: {:.2f} m/ping".format(M_PER_PING))
    print("  track length: {:.0f} m ({:.2f} NM)".format(total_len_m, total_len_m / 1852.0))
    print("  legs: {}   box: {:.1f} km x {:.1f} km".format(N_LEGS, BOX_EW_M / 1000, BOX_NS_M / 1000))
    print("  contacts: {} in 4 groups".format(len(TARGET_CENTRES)))
    print("  time span: {} -> {}".format(START_TIME, START_TIME + datetime.timedelta(seconds=PING_DT_S * (N_PINGS - 1))))
    return OUT_PATH


if __name__ == "__main__":
    generate()
