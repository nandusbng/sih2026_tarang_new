#!/usr/bin/env python
"""Upload tarang_synthetic_survey_002.xtf through the TARANG XTF pipeline.
Writes results to upload_xtf_result.txt"""
import sys, json, requests, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://localhost:3000"
XTF_FILE = "tarang_synthetic_survey_002.xtf"

out = []
def log(msg):
    out.append(str(msg))
    print(str(msg), flush=True)

log("=== TARANG SYNTHETIC XTF UPLOAD ===\n")

# 1. Get demo token for survey_operator
r = requests.post(f"{BASE}/api/auth/demo-access", json={"portal": "survey_operator"}, timeout=15)
assert r.status_code == 200, f"demo-access failed: {r.text[:200]}"
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
log(f"Token: {token[:30]}... OK")

# 2. Upload the XTF
log(f"\nUploading {XTF_FILE}...")
t0 = time.time()
with open(XTF_FILE, "rb") as f:
    upload_resp = requests.post(
        f"{BASE}/api/v1/xtf/upload",
        headers=headers,
        files={"file": (XTF_FILE, f, "application/octet-stream")},
        timeout=600
    )
elapsed = time.time() - t0
log(f"Upload HTTP: {upload_resp.status_code} (took {elapsed:.1f}s)")

if upload_resp.status_code != 200:
    log(f"ERROR: {upload_resp.text[:500]}")
    with open("upload_xtf_result.txt", "w", encoding="utf-8") as fp:
        fp.write("\n".join(out))
    sys.exit(1)

result = upload_resp.json()
survey_id = result.get("survey_id")
log(f"Survey ID: {survey_id}")
log(f"Status: {result.get('status')}")
log(f"Total Pings: {result.get('total_pings')}")
log(f"Channels: {result.get('channels')}")
log(f"Images Reconstructed: {result.get('images_reconstructed')}")
log(f"Detections Count: {result.get('detections_count')}")

metadata = result.get("metadata", {})
log("\n--- Metadata ---")
for k, v in metadata.items():
    if v not in (None, '', 0, []):
        log(f"  {k}: {v}")

detections = result.get("detections", [])
log(f"\n--- Detections ({len(detections)}) ---")
for d in detections[:5]:
    log(f"  {d.get('id')} | {d.get('class_name')} conf={d.get('confidence')} lat={d.get('latitude')} lon={d.get('longitude')}")

images = result.get("images", [])
log(f"\n--- Images ({len(images)}) ---")
for img in images[:3]:
    url = img.get("url") or img.get("local_url") or img.get("storage_url") or ""
    log(f"  sequence={img.get('sequence')} url={url[:80]}")

# 3. Verify images are accessible
log("\n--- Image accessibility ---")
for img in images[:3]:
    url = img.get("url") or ""
    if not url:
        log(f"  NO URL for sequence={img.get('sequence')}")
        continue
    test_url = f"{BASE}{url}" if url.startswith("/") else url
    try:
        r2 = requests.get(test_url, timeout=15, stream=True)
        ct = r2.headers.get("content-type", "")
        r2.close()
        log(f"  {test_url[:70]} -> HTTP {r2.status_code} ({ct[:30]})")
    except Exception as e:
        log(f"  {test_url[:70]} -> ERROR: {e}")

# 4. Check hotspots now
log("\n--- Hotspots (post-upload) ---")
time.sleep(2)
hs_resp = requests.get(f"{BASE}/api/v1/hotspots", headers=headers, timeout=60)
log(f"Hotspots HTTP: {hs_resp.status_code}")
if hs_resp.status_code == 200:
    hotspots = hs_resp.json()
    log(f"Total hotspots: {len(hotspots)}")
    for hs in hotspots[:6]:
        log(f"  {hs.get('id')} lat={hs.get('latitude')} lon={hs.get('longitude')} targets={hs.get('total_targets')} priority={hs.get('priority')}")
else:
    log(f"  ERROR: {hs_resp.text[:300]}")

# 5. Get TSP route
log("\n--- TSP Cleanup Route ---")
route_resp = requests.get(f"{BASE}/api/v1/hotspot-route",
                          params={"survey_id": survey_id},
                          headers=headers, timeout=60)
log(f"Route HTTP: {route_resp.status_code}")
if route_resp.status_code == 200:
    route = route_resp.json()
    log(f"  Route ID: {route.get('route_id')}")
    log(f"  Total distance: {route.get('total_distance_nm')} NM ({route.get('total_distance_km')} km)")
    log(f"  Algorithm: {route.get('algorithm')}")
    log(f"  Hotspot sequence ({len(route.get('target_sequence', []))}):")
    for stop in route.get("target_sequence", []):
        log(f"    #{stop.get('sequence')} {stop.get('label')} lat={stop.get('latitude')} lon={stop.get('longitude')}")
elif route_resp.status_code == 409:
    log(f"  Not enough hotspots: {route_resp.json().get('message','')[:150]}")
else:
    log(f"  ERROR: {route_resp.text[:300]}")

# 6. Get XTF metadata endpoint
log("\n--- XTF Metadata endpoint ---")
meta_resp = requests.get(f"{BASE}/api/v1/xtf/{survey_id}/metadata", headers=headers, timeout=15)
log(f"HTTP: {meta_resp.status_code}")
if meta_resp.status_code == 200:
    meta = meta_resp.json()
    log(f"  Keys: {list(meta.keys())[:10]}")
    log(f"  Total Pings: {meta.get('Total Pings')}")
    log(f"  Min Lat: {meta.get('Min Latitude')} Max Lat: {meta.get('Max Latitude')}")
    log(f"  Min Lon: {meta.get('Min Longitude')} Max Lon: {meta.get('Max Longitude')}")
else:
    log(f"  ERROR: {meta_resp.text[:200]}")

# 7. Export survey bundle
log("\n--- Export Survey Bundle ---")
export_resp = requests.get(f"{BASE}/api/v1/export/survey/{survey_id}/json", headers=headers, timeout=30)
log(f"Export HTTP: {export_resp.status_code}")
if export_resp.status_code == 200:
    bundle = export_resp.json()
    log(f"  Keys: {list(bundle.keys())}")
    log(f"  Detections in bundle: {len(bundle.get('detections', []))}")
    log(f"  Hotspots in bundle: {len(bundle.get('hotspots', []))}")
    log(f"  Survey ID: {bundle.get('survey', {}).get('survey_id')}")
else:
    log(f"  ERROR: {export_resp.text[:200]}")

# 8. Check notification in marine_portal
log("\n--- Notification in marine_portal ---")
r_marine = requests.post(f"{BASE}/api/auth/demo-access", json={"portal": "marine_portal"}, timeout=10)
tok_marine = r_marine.json()["access_token"]
notif_resp = requests.get(f"{BASE}/api/v1/notifications",
                          headers={"Authorization": f"Bearer {tok_marine}"}, timeout=15)
log(f"Notifications HTTP: {notif_resp.status_code}")
if notif_resp.status_code == 200:
    notifs = notif_resp.json()
    log(f"  Total: {len(notifs)}")
    survey_notifs = [n for n in notifs if n.get("survey_id") == survey_id]
    log(f"  For this survey: {len(survey_notifs)}")
    for n in survey_notifs[:3]:
        log(f"  [{n.get('type')}] {n.get('title')} - {n.get('message', '')[:80]}")
else:
    log(f"  ERROR: {notif_resp.text[:200]}")

log("\n=== UPLOAD + PIPELINE TEST COMPLETE ===")

with open("upload_xtf_result.txt", "w", encoding="utf-8") as fp:
    fp.write("\n".join(out))
print("Results written to upload_xtf_result.txt", flush=True)
