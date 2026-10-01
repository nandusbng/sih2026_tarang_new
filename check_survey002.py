#!/usr/bin/env python
"""Check synthetic survey_002 detections and hotspot state"""
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://localhost:3000"

def log(m): print(m, flush=True)

r = requests.post(f"{BASE}/api/auth/demo-access", json={"portal":"survey_operator"}, timeout=10)
tok = r.json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}

# Find survey_002 records
surveys = requests.get(f"{BASE}/api/v1/surveys", headers=h, timeout=15).json()
xtf_surveys = [s for s in surveys if "survey_002" in (s.get("file_name") or "")]
log(f"Survey_002 records: {len(xtf_surveys)}")
for s in xtf_surveys:
    sid = s["survey_id"]
    log(f"  {sid} - status={s.get('processing_status')} - det_count={s.get('detection_count')}")

    # Get detections
    dets = requests.get(f"{BASE}/api/v1/detections", headers=h, params={"survey_id": sid}, timeout=20).json()
    dets_list = dets if isinstance(dets, list) else dets.get("detections", [])
    log(f"  Detections: {len(dets_list)}")
    geo_dets = [d for d in dets_list if d.get("latitude") and d.get("longitude")]
    log(f"  Geotagged: {len(geo_dets)}")
    if geo_dets:
        lats = [float(d["latitude"]) for d in geo_dets]
        lons = [float(d["longitude"]) for d in geo_dets]
        log(f"  Lat range: {min(lats):.5f} to {max(lats):.5f}")
        log(f"  Lon range: {min(lons):.5f} to {max(lons):.5f}")
        for d in geo_dets[:5]:
            log(f"    {d.get('id')} | {d.get('class_name')} conf={d.get('confidence')} lat={d.get('latitude'):.5f} lon={d.get('longitude'):.5f}")
    
    # Get images
    imgs = requests.get(f"{BASE}/api/v1/xtf/{sid}/images", headers=h, timeout=15)
    if imgs.status_code == 200:
        img_list = imgs.json()
        log(f"  Images: {len(img_list)}")
        for img in img_list[:3]:
            log(f"    seq={img.get('sequence')} url={str(img.get('url',''))[:70]}")
    else:
        log(f"  Images: ERROR {imgs.status_code}")

log("\n--- All Hotspots ---")
hs = requests.get(f"{BASE}/api/v1/hotspots", headers=h, timeout=60).json()
log(f"Total hotspots: {len(hs)}")
for hotspot in hs:
    log(f"  {hotspot.get('id')} lat={hotspot.get('latitude')} lon={hotspot.get('longitude')} targets={hotspot.get('total_targets')} priority={hotspot.get('priority')}")

log("\n--- TSP Route (all surveys) ---")
route = requests.get(f"{BASE}/api/v1/hotspot-route", headers=h, timeout=60)
log(f"HTTP: {route.status_code}")
if route.status_code == 200:
    r = route.json()
    log(f"  Distance: {r.get('total_distance_nm')} NM")
    log(f"  Algorithm: {r.get('algorithm')}")
    log(f"  Stops: {len(r.get('target_sequence', []))}")
    for stop in r.get("target_sequence", []):
        log(f"  #{stop.get('sequence')} {stop.get('label')} lat={stop.get('latitude')} lon={stop.get('longitude')}")
elif route.status_code == 409:
    log(f"  {route.json().get('message')}")
else:
    log(f"  ERROR: {route.text[:200]}")

log("Done.")
