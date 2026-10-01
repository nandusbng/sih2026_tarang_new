#!/usr/bin/env python
"""TARANG diagnostic test runner - writes results to diag_out.txt"""
import sys, json, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

BASE = "http://localhost:3000"
out = []

def log(msg):
    out.append(str(msg))
    print(msg, flush=True)

def get_token(portal):
    r = requests.post(f"{BASE}/api/auth/demo-access", json={"portal": portal}, timeout=15)
    assert r.status_code == 200, f"demo-access {portal} failed: {r.status_code} {r.text[:100]}"
    return r.json()["access_token"]

def h(token):
    return {"Authorization": f"Bearer {token}"}

try:
    log("=== TARANG DIAGNOSTIC REPORT ===\n")

    # --- AUTH ---
    log("-- AUTHENTICATION --")
    tok_op = get_token("survey_operator")
    log(f"  survey_operator demo token: {tok_op[:30]}... OK")
    tok_sonar = get_token("sonar_analyst")
    log(f"  sonar_analyst demo token: OK")
    tok_marine = get_token("marine_portal")
    log(f"  marine_portal demo token: OK")
    tok_gov = get_token("government_portal")
    log(f"  government_portal demo token: OK")
    tok_admin = get_token("admin")
    log(f"  admin demo token: OK")
    tok_pub = get_token("public")
    log(f"  public demo token: OK")

    # --- SYSTEM STATUS ---
    log("\n-- SYSTEM STATUS (/api/v1/system/status) --")
    try:
        r = requests.get(f"{BASE}/api/v1/system/status", headers=h(tok_op), timeout=90)
        d = r.json()
        log(f"  HTTP: {r.status_code}")
        log(f"  Overall: {d.get('overall')}")
        log(f"  Database: {d.get('database',{}).get('supabase',{}).get('status')}")
        log(f"  Auth: {d.get('authentication',{}).get('supabase_auth',{}).get('status')}")
        log(f"  Storage: {d.get('storage',{}).get('supabase_storage',{}).get('status')}")
        log(f"  API: {d.get('api',{}).get('backend_api',{}).get('status')}")
    except Exception as e:
        log(f"  ERROR: {e}")

    # --- SURVEYS ---
    log("\n-- SURVEYS --")
    r = requests.get(f"{BASE}/api/v1/surveys", headers=h(tok_op), timeout=15)
    log(f"  HTTP: {r.status_code}")
    surveys = r.json() if r.status_code == 200 else []
    log(f"  Count: {len(surveys)}")
    if surveys:
        s0 = surveys[0]
        log(f"  First survey: {s0.get('survey_id')} / {s0.get('survey_name')} / status={s0.get('processing_status')}")

    # --- DETECTIONS ---
    log("\n-- DETECTIONS --")
    r = requests.get(f"{BASE}/api/v1/detections", headers=h(tok_op), timeout=15)
    log(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        dets = r.json()
        dets_list = dets if isinstance(dets, list) else dets.get("detections", [])
        log(f"  Count: {len(dets_list)}")
        geo = [d for d in dets_list if d.get("latitude") and d.get("longitude")]
        log(f"  With coordinates: {len(geo)}")
        if geo:
            log(f"  Sample: class={geo[0].get('class_name')} lat={geo[0].get('latitude')} lon={geo[0].get('longitude')}")
    else:
        log(f"  ERROR: {r.text[:200]}")

    # --- HOTSPOTS ---
    log("\n-- HOTSPOTS --")
    r = requests.get(f"{BASE}/api/v1/hotspots", headers=h(tok_op), timeout=30)
    log(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        hs = r.json()
        hs_list = hs if isinstance(hs, list) else hs.get("hotspots", [])
        log(f"  Count: {len(hs_list)}")
        if hs_list:
            log(f"  Sample: id={hs_list[0].get('id')} lat={hs_list[0].get('latitude')} lon={hs_list[0].get('longitude')} targets={hs_list[0].get('total_targets')}")
    else:
        log(f"  ERROR: {r.text[:300]}")

    # --- NOTIFICATIONS ---
    log("\n-- NOTIFICATIONS --")
    r = requests.get(f"{BASE}/api/v1/notifications", headers=h(tok_marine), timeout=15)
    log(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        notifs = r.json()
        n_list = notifs if isinstance(notifs, list) else notifs.get("notifications", [])
        log(f"  Count: {len(n_list)}")
    else:
        log(f"  ERROR: {r.text[:200]}")

    # --- TSP CLEANUP ROUTE ---
    log("\n-- TSP CLEANUP ROUTE --")
    r = requests.get(f"{BASE}/api/v1/hotspot-route", headers=h(tok_marine), timeout=30)
    log(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        route = r.json()
        log(f"  Route ID: {route.get('route_id')}")
        log(f"  Total distance: {route.get('total_distance_nm')} NM")
        log(f"  Hotspot count: {len(route.get('target_sequence', []))}")
        log(f"  Algorithm: {route.get('algorithm')}")
    else:
        log(f"  ERROR: {r.text[:400]}")

    # --- WORKFLOW STATE ---
    log("\n-- WORKFLOW STATE --")
    r = requests.get(f"{BASE}/api/v1/workflow/state", headers=h(tok_op), timeout=15)
    log(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        ws = r.json()
        log(f"  Keys: {list(ws.keys())}")
    else:
        log(f"  Content: {r.text[:200]}")

    # --- JSON EXPORTS ---
    log("\n-- JSON EXPORTS --")
    surveys_list = requests.get(f"{BASE}/api/v1/surveys", headers=h(tok_op), timeout=15).json()
    if surveys_list:
        sid = surveys_list[0]["survey_id"]
        r = requests.get(f"{BASE}/api/v1/export/survey/{sid}/json", headers=h(tok_op), timeout=15)
        log(f"  Survey JSON export HTTP: {r.status_code}")
        if r.status_code == 200:
            log(f"  Keys: {list(r.json().keys())}")
        else:
            log(f"  ERROR: {r.text[:200]}")

    r = requests.get(f"{BASE}/api/v1/export/detections/json", headers=h(tok_op), timeout=15)
    log(f"  Detections JSON HTTP: {r.status_code}, len={len(r.text)}")

    r = requests.get(f"{BASE}/api/v1/export/hotspots/json", headers=h(tok_op), timeout=15)
    log(f"  Hotspots JSON HTTP: {r.status_code}, len={len(r.text)}")

    r = requests.get(f"{BASE}/api/v1/export/cleanup-route/json", headers=h(tok_op), timeout=30)
    log(f"  Cleanup route JSON HTTP: {r.status_code}, len={len(r.text)}")

    # --- IMAGE ACCESSIBILITY ---
    log("\n-- IMAGE ACCESSIBILITY --")
    r = requests.get(f"{BASE}/api/v1/detections", headers=h(tok_op), timeout=15)
    if r.status_code == 200:
        dets_all = r.json() if isinstance(r.json(), list) else r.json().get("detections", [])
        img_tested = 0
        for d in dets_all[:5]:
            crop = d.get("crop_url") or d.get("evidence_url") or ""
            if crop and (crop.startswith("http") or crop.startswith("/")):
                img_tested += 1
                try:
                    if crop.startswith("/"):
                        ri = requests.get(f"{BASE}{crop}", timeout=10)
                    else:
                        ri = requests.get(crop, timeout=10)
                    ct = ri.headers.get("content-type","")
                    ok = "image" in ct or ri.status_code == 200
                    log(f"  Image {crop[:60]} -> HTTP {ri.status_code} ({ct[:30]}) {'OK' if ok else 'FAIL'}")
                except Exception as ie:
                    log(f"  Image {crop[:60]} -> ERROR: {ie}")
        if img_tested == 0:
            log("  No image URLs found in recent detections")

    # --- XTF FILES ---
    log("\n-- XTF FILES ON DISK --")
    import os
    xtf_files = [f for f in os.listdir(".") if f.endswith(".xtf")]
    for f in xtf_files:
        size = os.path.getsize(f)
        log(f"  {f}: {size/1024:.1f} KB")

    # --- OUTPUTS DIR ---
    log("\n-- OUTPUTS DIRECTORY --")
    out_dir = "outputs"
    if os.path.isdir(out_dir):
        total = 0
        for root, dirs, files in os.walk(out_dir):
            for fn in files:
                total += 1
        log(f"  Total files in outputs/: {total}")
        imgs = [f for f in os.listdir(out_dir) if f.endswith((".jpg",".png"))]
        log(f"  Images in outputs/: {len(imgs)}")

    log("\n=== DIAGNOSTIC COMPLETE ===")

except Exception as e:
    log(f"\nFATAL ERROR: {e}")
    log(traceback.format_exc())

# Write to file
with open("diag_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("Results written to diag_out.txt", flush=True)
