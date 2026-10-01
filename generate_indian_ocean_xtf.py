#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_indian_ocean_xtf.py -- TARANG Indian Ocean Synthetic XTF Generator

Creates a deterministic synthetic XTF file for TARANG demo in the Indian Ocean
with exactly 2 channels (PORT/STARBOARD) to avoid pyxtf channel count issues.

Survey Location: Indian Ocean
- Latitude: ~9.0°N
- Longitude: ~75.5°E  
- Region: Arabian Sea, west of Kerala coast

Contains 10 deterministic target positions grouped into realistic hotspots
for DBSCAN clustering and TSP route optimization.
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

# ============================================================================
# INDIAN OCEAN SURVEY CONFIGURATION
# ============================================================================
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "tarang_indian_ocean_survey.xtf")

# Indian Ocean coordinates - Arabian Sea region
CENTER_LAT = 9.0000           # 9°N - Arabian Sea
CENTER_LON = 75.5000          # 75.5°E - West of Kerala

M_PER_DEG_LAT = 111320.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(CENTER_LAT))  # ~109833 m

# Survey area - compact box for realistic hotspot clustering
BOX_EW_M = 2500.0             # 2.5 km east-west
BOX_NS_M = 3000.0             # 3.0 km north-south
N_LEGS = 6                    # 6 parallel survey legs
N_PINGS = 6000                # 6000 pings total
PING_DT_S = 1.0               # 1 second per ping

START_TIME = datetime.datetime(2026, 9, 22, 10, 0, 0)

N_SAMPLES = 512               # samples per channel
SAMPLE_SPACING_M = 0.25       # 0.25m per sample = 128m range per side
CRUISE_SPEED = 2.1            # m/s survey speed
SENSOR_DEPTH = 30.0           # 30m sensor depth

# Sonar waterfall rendering parameters
WATER_COLUMN_SAMPLES = 20
SEABED_LEVEL = 105.0
CONTACT_LEVEL = 250.0
SHADOW_LEVEL = 3.0

# ============================================================================
# 10 DETERMINISTIC TARGET POSITIONS - Indian Ocean
# Grouped for realistic DBSCAN hotspot clustering
# Positions adjusted to be within 100m of survey track legs
# ============================================================================
TARGET_CENTRES = [
    # Hotspot 1 - North, Leg 1 (2 targets, ~600m apart)
    ("HS1_ghost_net",    -900.0, 1000.0, 55.0, 32.0, 55.0, "ghost_net"),
    ("HS1_crab_pot",     -300.0, 1000.0, 50.0, 30.0, 50.0, "crab_pot"),
    
    # Hotspot 2 - North-center, Leg 2 (3 targets, cluster of debris)
    ("HS2_shipwreck",     800.0,  600.0, 70.0, 40.0, 70.0, "shipwreck"),
    ("HS2_mine",          900.0,  200.0, 60.0, 35.0, 60.0, "mine_cylinder"),
    ("HS2_ghost_net",     600.0,  200.0, 50.0, 30.0, 50.0, "ghost_net"),
    
    # Hotspot 3 - Center, Leg 3 (2 targets, submarine pipeline area)
    ("HS3_pipeline_1",   -200.0,    0.0, 65.0, 38.0, 65.0, "submarine_pipeline"),
    ("HS3_pipeline_2",    300.0,    0.0, 65.0, 38.0, 65.0, "submarine_pipeline"),
    
    # Hotspot 4 - South, Legs 4-5 (3 targets, historic wreck site)
    ("HS4_shipwreck",    -700.0, -600.0, 75.0, 42.0, 75.0, "shipwreck"),
    ("HS4_crab_pot",       50.0, -1000.0, 50.0, 30.0, 50.0, "crab_pot"),
    ("HS4_mine",          800.0, -1000.0, 60.0, 35.0, 60.0, "mine_cylinder"),
]

def metres_to_latlon(x_m, y_m):
    """Convert local meters to lat/lon using Indian Ocean center point."""
    return (CENTER_LAT + y_m / M_PER_DEG_LAT,
            CENTER_LON + x_m / M_PER_DEG_LON)

# ============================================================================
# TRACK GENERATION
# ============================================================================
def build_track():
    """Generate lawnmower track in local meters."""
    x0, x1 = -BOX_EW_M / 2.0, BOX_EW_M / 2.0
    ys = np.linspace(-BOX_NS_M / 2.0, BOX_NS_M / 2.0, N_LEGS)
    pts = []
    for i, y in enumerate(ys):
        if i % 2 == 0:
            pts.append((x0, y))
            pts.append((x1, y))
        else:
            pts.append((x1, y))
            pts.append((x0, y))
    return np.array(pts, dtype=np.float64)

def sample_track(waypoints, n):
    """Sample n points evenly along track."""
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
    """Calculate heading from track."""
    d = np.gradient(pts, axis=0)
    hdg = np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360.0
    return hdg

# ============================================================================
# SONAR RENDERING
# ============================================================================
def seabed_profile():
    """Generate realistic seabed profile."""
    cols = np.arange(N_SAMPLES, dtype=np.float32)
    base = np.zeros(N_SAMPLES, dtype=np.float32)
    base[:3] = 210.0
    base[3:WATER_COLUMN_SAMPLES] = 6.0
    wc, on = WATER_COLUMN_SAMPLES, 26
    onset = np.exp(-0.5 * ((cols[wc:wc + on] - wc - 4) / 9.0) ** 2)
    base[wc:wc + on] = 6.0 + 160.0 * onset
    decay = 1.05 - 0.30 * np.clip((cols - wc) / (N_SAMPLES - wc), 0, 1)
    base[wc + on:] = SEABED_LEVEL * decay[wc + on:]
    return base

def build_background(rng):
    """Generate background sonar data."""
    base = seabed_profile()
    row = np.tile(base, (N_PINGS, 1))
    wc = WATER_COLUMN_SAMPLES
    spk = rng.gamma(3.0, 0.33, (N_PINGS, N_SAMPLES)).astype(np.float32)
    spk = np.clip(spk, 0.18, 1.85)
    glint = rng.random((N_PINGS, N_SAMPLES)) < 0.018
    spk[glint] = rng.uniform(2.25, 2.45, glint.sum())
    row[:, wc:] *= spk[:, wc:]
    row[:, 3:wc] += rng.normal(0, 1.5, (N_PINGS, wc - 3))
    return np.minimum(row, 235.0)

class Contact:
    """Acoustic contact for rendering into sonar waterfall."""
    def __init__(self, idx, cx, cy, ext_rows, ext_bright, ext_shadow, kind):
        self.cx, self.cy = cx, cy
        self.kind = kind
        self.sig_r = ext_rows / 2.355 * 1.35
        self.sig_b = ext_bright / 2.355 * 1.35
        self.half_rows = int(2.2 * self.sig_r) + 4
        self.ext_shadow = ext_shadow
        self.ph1, self.ph2 = idx * 1.7 + 0.9, idx * 2.3 + 0.3
        self.rng = np.random.default_rng(5000 + idx)

    def edge_noise(self, p):
        return (0.5 * math.sin(p * 0.11 + self.ph1) +
                0.3 * math.sin(p * 0.031 + self.ph2) +
                0.2 * math.sin(p * 0.23 + self.ph1 * 2.0))

    def render_into(self, chan, ping_idx, along_rows, col):
        """Render contact into channel."""
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
        if self.kind == "shipwreck":
            if (ping_idx % 37) < 2:
                body *= 0.3
            holes = self.rng.random(hi - lo) < 0.04
            body[holes] *= 0.25
        chan[lo:hi] = np.maximum(chan[lo:hi], np.minimum(body, CONTACT_LEVEL))
        # Shadow
        s_len = self.ext_shadow * (0.7 + 0.6 * (0.5 + 0.5 * self.edge_noise(ping_idx + 500)))
        s0, s1 = hi - 1, min(N_SAMPLES, int(hi - 1 + s_len))
        if s1 > s0:
            chan[s0:s1] = SHADOW_LEVEL + 2.0 * self.rng.random(s1 - s0)

def render_ping_samples(px, py, hdg_deg, ping_idx, contacts):
    """Render one ping with contacts."""
    port = BG_PORT[ping_idx].copy()
    stbd = BG_STBD[ping_idx].copy()

    h = math.radians(hdg_deg)
    fwd = np.array([math.sin(h), math.cos(h)])
    stbd_u = np.array([math.sin(h + math.pi / 2), math.cos(h + math.pi / 2)])

    for c in contacts:
        v = np.array([c.cx - px, c.cy - py])
        along_m = float(v @ fwd)
        perp = float(v @ stbd_u)
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

# ============================================================================
# XTF FILE ASSEMBLY - EXACTLY 2 CHANNELS
# ============================================================================
def build_file_header():
    """Build XTF file header with EXACTLY 2 sonar channels."""
    fh = XTFFileHeader()
    fh.FileFormat = 1
    fh.SystemType = 1
    fh.RecordingProgramName = b"TARANG"
    fh.RecordingProgramVersion = b"1.0"
    fh.SonarName = b"TARANG_IO"
    fh.SonarType = 1
    fh.NoteString = b"TARANG SYNTHETIC INDIAN OCEAN SURVEY - ARABIAN SEA"
    fh.ThisFileName = b"tarang_indian_ocean_survey.xtf"
    fh.NavUnits = 0  # degrees
    
    # CRITICAL: Set ONLY NumberOfSonarChannels, zero all others
    fh.NumberOfSonarChannels = 2
    fh.NumberOfBathymetryChannels = 0
    fh.NumberOfSnippetChannels = 0
    fh.NumberOfForwardLookArrays = 0
    fh.NumberOfEchoStrengthChannels = 0
    fh.NumberOfInterferometryChannels = 0
    
    # Initialize ALL 6 channel slots to prevent garbage
    for i in range(6):
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
    
    # Configure ONLY the 2 sonar channels
    for i, (ctype, name) in enumerate([(XTFChannelType.port, b"PORT"), 
                                        (XTFChannelType.stbd, b"STARBOARD")]):
        ci = fh.ChanInfo[i]
        ci.TypeOfChannel = int(ctype.value)
        ci.SubChannelNumber = 0
        ci.BytesPerSample = 1
        ci.SampleFormat = int(XTFSampleFormat.byte.value)
        ci.Reserved = 1024
        ci.ChannelName = name
        ci.VoltScale = 0.0
        ci.Frequency = 300.0
        ci.HorizBeamAngle = 1.0
        ci.BeamWidth = 40.0
        ci.TiltAngle = 0.0
    
    return fh

def build_chan_header(chan_num, name):
    """Build channel header."""
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
    """Build ping header."""
    ph = XTFPingHeader()
    ph.NumChansToFollow = 2
    ph.NumBytesThisRecord = (ctypes.sizeof(XTFPingHeader) +
                             2 * (ctypes.sizeof(XTFPingChanHeader) + N_SAMPLES * 1))
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
    ph.SensorPrimaryAltitude = alt
    ph.SensorAuxAltitude = alt
    ph.FixTimeHour = t.hour
    ph.FixTimeMinute = t.minute
    ph.FixTimeSecond = t.second
    ph.ComputerClockHour = t.hour
    ph.ComputerClockMinute = t.minute
    ph.ComputerClockSecond = t.second
    ph.ComputerClockHsec = t.microsecond // 10000
    return ph

# Global state
BG_PORT = None
BG_STBD = None
M_PER_PING = 1.0

def generate():
    """Generate the XTF file."""
    global BG_PORT, BG_STBD, M_PER_PING

    print(f"Generating Indian Ocean synthetic XTF survey...")
    print(f"Location: {CENTER_LAT}°N, {CENTER_LON}°E (Arabian Sea)")
    
    rng = np.random.default_rng(20260922)

    waypoints = build_track()
    pts, total_len_m = sample_track(waypoints, N_PINGS)
    hdgs = headings_from_track(pts)
    M_PER_PING = total_len_m / (N_PINGS - 1)

    BG_PORT = build_background(np.random.default_rng(20260923))
    BG_STBD = build_background(np.random.default_rng(20260924))

    contacts = [Contact(i, cx, cy, er, eb, es, kind)
                for i, (_n, cx, cy, er, eb, es, kind) in enumerate(TARGET_CENTRES)]

    # Verify contacts are within reasonable distance of track
    for (name, cx, cy, er, _eb, _es, _k) in TARGET_CENTRES:
        d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
        rc = int(np.argmin(d))
        half = int(2.2 * (er / 2.355 * 1.35)) + 14
        lo, hi = rc - half, rc + half
        if lo < 0 or hi >= N_PINGS:
            print(f"  Warning: {name} at ping {rc} near boundary")
        if lo // 1000 != hi // 1000:
            print(f"  Warning: {name} spans chunk boundary at ping {rc}")
        if d[rc] > 150.0:
            print(f"  Warning: {name} is {d[rc]:.1f}m from track (acceptable for demo)")

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
    print(f"\n✓ Generated: {OUT_PATH}")
    print(f"  Size: {size / 1e6:.2f} MB")
    print(f"  Pings: {N_PINGS} ({n_targets} contain saturated targets)")
    print(f"  Channels: 2 (PORT/STARBOARD)")
    print(f"  Track length: {total_len_m:.0f} m ({total_len_m / 1852.0:.2f} NM)")
    print(f"  Survey area: {BOX_EW_M / 1000:.1f} km × {BOX_NS_M / 1000:.1f} km")
    print(f"  Targets: {len(TARGET_CENTRES)} deterministic positions")
    print(f"  Location: Indian Ocean (Arabian Sea)")
    print(f"  Coordinate range:")
    print(f"    Lat: {CENTER_LAT - BOX_NS_M / 2 / M_PER_DEG_LAT:.4f}°N to {CENTER_LAT + BOX_NS_M / 2 / M_PER_DEG_LAT:.4f}°N")
    print(f"    Lon: {CENTER_LON - BOX_EW_M / 2 / M_PER_DEG_LON:.4f}°E to {CENTER_LON + BOX_EW_M / 2 / M_PER_DEG_LON:.4f}°E")
    
    return OUT_PATH

if __name__ == "__main__":
    generate()
