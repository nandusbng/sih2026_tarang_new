#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_demo_xtf.py -- end-to-end verification of tarang_synthetic_survey_002.xtf.

Everything reported here is read back from the actual generated file:
  * via the project's own xtf_parser.parse_xtf() (metadata + images + pings),
  * via pyxtf.xtf_read() for the raw acoustic samples (to derive which pings
    carry bright contact returns -- i.e. the simulated AI detections).
"""

import math
import os
import shutil
import sys
import tempfile

import numpy as np
import pyxtf
from sklearn.cluster import DBSCAN

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xtf_parser
from generate_demo_xtf import (TARGET_CENTRES, metres_to_latlon,
                               CENTER_LAT, CENTER_LON)

XTF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "tarang_synthetic_survey_002.xtf")

EARTH_R = 6371000.0
# A contact ping is one whose raw samples carry a saturated target return:
# the hard-edged body is written at level 250 while the capped seabed
# background never exceeds 235, so >= 12 samples at >= 248 unambiguously
# identify the ~140-ping footprint of each rendered contact.
CONTACT_SAT_LEVEL = 248       # uint8 sample value of a saturated return
CONTACT_MIN_SAT = 12          # min saturated samples per ping to count


def hav_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def main():
    ok = True
    print("=" * 72)
    print("VERIFY", XTF, "({:.2f} MB)".format(os.path.getsize(XTF) / 1e6))
    print("=" * 72)

    tmpdir = tempfile.mkdtemp(prefix="tarang_verify_")
    try:
        # ---- 1. project parser round-trip ---------------------------------
        res = xtf_parser.parse_xtf(XTF, tmpdir)
        assert res is not None, "parse_xtf returned None"
        md, pings, images = res["metadata"], res["pings"], res["images"]

        print("\n-- metadata dict --")
        for k in sorted(md, key=str):
            print("  {:26s} {}".format(str(k) + ":", md[k]))

        checks = [
            ("Synthetic flag True", md.get("Synthetic") is True),
            ("Note contains SYNTHETIC", "SYNTHETIC" in str(md.get("Note", "")).upper()),
            ("SonarName", md.get("SonarName") == "TARANG SYNTH"),
            ("RecordingProgramName", md.get("RecordingProgramName") == "TARANG"),
            ("RecordingProgramVersion", md.get("RecordingProgramVersion") == "1.0"),
            ("SystemType", md.get("SystemType") == 1),
            ("Total Pings == 12000", md.get("Total Pings") == 12000),
            ("Channel Count == 2", md.get("Channel Count") == 2),
            ("Samples per Ping == 512", md.get("Samples per Ping") == 512),
            ("Channels PORT,STARBOARD", md.get("Channels") == "PORT, STARBOARD"),
        ]
        print("\n-- header/ping field checks --")
        for name, passed in checks:
            print("  [{}] {}".format("PASS" if passed else "FAIL", name))
            ok = ok and passed

        # ---- 2. reconstructed images --------------------------------------
        print("\n-- reconstructed images: {} --".format(len(images)))
        for img in images:
            exists = os.path.isfile(img["path"])
            size = os.path.getsize(img["path"]) if exists else 0
            good = exists and size > 0
            ok = ok and good
            print("  [{}] {} ({} bytes, pings {}-{})".format(
                "PASS" if good else "FAIL", img["path"], size,
                img["ping_start"], img["ping_end"]))

        # ---- 3. geometry ----------------------------------------------------
        lats = np.array([p["latitude"] for p in pings])
        lons = np.array([p["longitude"] for p in pings])
        hdgs = np.array([p["heading_degrees"] for p in pings])
        track_m = sum(hav_m(lats[i], lons[i], lats[i + 1], lons[i + 1])
                      for i in range(len(pings) - 1))

        print("\n-- geometry --")
        print("  lat bbox: {:.6f} .. {:.6f}".format(lats.min(), lats.max()))
        print("  lon bbox: {:.6f} .. {:.6f}".format(lons.min(), lons.max()))
        print("  track length: {:.2f} km = {:.3f} NM".format(
            track_m / 1000.0, track_m / 1852.0))
        print("  distinct latitudes: {}".format(len(np.unique(np.round(lats, 7)))))
        print("  distinct longitudes: {}".format(len(np.unique(np.round(lons, 7)))))

        # legs / direction changes: turns are gradual (spread over the 400 m
        # cross-leg connectors), so count runs of eastward vs westward heading
        # plus the accumulated heading change.
        eastward = hdgs < 180.0
        transitions = int(np.sum(eastward[1:] != eastward[:-1]))
        leg_runs = transitions + 1
        dh = np.diff(hdgs)
        dh = (dh + 180.0) % 360.0 - 180.0
        cum_turn = float(np.abs(dh).sum())
        print("  E/W direction changes (turns): {}".format(transitions))
        print("  straight leg runs detected: {}".format(leg_runs))
        print("  accumulated heading change: {:.0f} deg (~{:.1f} x 180-deg turns)".format(
            cum_turn, cum_turn / 180.0))
        not_straight = (len(np.unique(np.round(lats, 7))) > 100
                        and leg_runs >= 6 and cum_turn > 5 * 150.0)
        print("  [{}] track is NOT a straight line (>=6 legs, many latitudes)".format(
            "PASS" if not_straight else "FAIL"))
        ok = ok and not_straight

        # ---- 4. contact pings from the RAW samples in the file --------------
        fh2, pk = pyxtf.xtf_read(XTF, types=[pyxtf.XTFHeaderType.sonar])
        packets = pk[pyxtf.XTFHeaderType.sonar]
        det_idx = []
        for i, p in enumerate(packets):
            sat = int((p.data[0] >= CONTACT_SAT_LEVEL).sum()
                      + (p.data[1] >= CONTACT_SAT_LEVEL).sum())
            if sat >= CONTACT_MIN_SAT:
                det_idx.append(i)
        det_idx = np.array(det_idx)
        print("\n-- contact (detection) pings derived from raw samples --")
        print("  pings with >= {} samples at >= {}: {} of {}".format(
            CONTACT_MIN_SAT, CONTACT_SAT_LEVEL, len(det_idx), len(packets)))

        # ---- 5. DBSCAN ------------------------------------------------------
        eps = 1500.0 / EARTH_R

        def run_dbscan(lat_arr, lon_arr, label):
            X = np.radians(np.column_stack([lat_arr, lon_arr]))
            db = DBSCAN(eps=eps, min_samples=2, metric="haversine").fit(X)
            lab = db.labels_
            n = lab.max() + 1 if len(lab) else 0
            sizes = [int((lab == c).sum()) for c in range(n)]
            cents = []
            for c in range(n):
                m = lab == c
                cents.append((float(np.degrees(X[m, 0].mean())),
                              float(np.degrees(X[m, 1].mean()))))
            print("  {}: {} clusters, sizes {}, noise {}".format(
                label, n, sizes, int((lab == -1).sum())))
            return n, sizes, cents

        print("\n-- DBSCAN eps=1500 m, min_samples=2, haversine --")
        n_all, sizes_all, _ = run_dbscan(lats, lons, "all ping positions")
        print("    (a continuous lawnmower track is one connected set at "
              "eps=1500 m -- expected)")
        n_det, sizes_det, cents = run_dbscan(lats[det_idx], lons[det_idx],
                                             "contact/detection pings")
        det_ok = 4 <= n_det <= 8
        print("  [{}] detection clusters in required 4-8 range".format(
            "PASS" if det_ok else "FAIL"))
        ok = ok and det_ok

        # ---- 6. the six intended target centres -----------------------------
        print("\n-- intended target centres vs file content --")
        for (name, cx, cy, *_rest) in TARGET_CENTRES:
            clat, clon = metres_to_latlon(cx, cy)
            d_all = [hav_m(clat, clon, lats[i], lons[i]) for i in range(len(pings))]
            nearest = min(d_all)
            if len(det_idx):
                d_det = min(hav_m(clat, clon, lats[i], lons[i]) for i in det_idx)
            else:
                d_det = float("inf")
            good = nearest < 150.0 and d_det < 200.0
            ok = ok and good
            print("  [{}] {:18s} nearest track ping {:6.1f} m, nearest contact ping {:6.1f} m".format(
                "PASS" if good else "FAIL", name, nearest, d_det))

        # cluster centroids (sanity, informational)
        print("\n-- detection cluster centroids --")
        for c, (clat, clon) in enumerate(cents):
            print("  cluster {}: {:.6f}, {:.6f} ({} pings)".format(
                c, clat, clon, sizes_det[c]))

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 72)
    print("OVERALL:", "PASS" if ok else "FAIL")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
