import urllib.request
import json

endpoints = [
    '/static/models/drone.glb',
    '/drone.glb',
    '/api/v1/clusters',
    '/api/v1/export/clusters/json',
    '/api/v1/stats/government',
    '/api/v1/stats/public'
]

all_passed = True
for ep in endpoints:
    try:
        req = urllib.request.Request(f'http://127.0.0.1:3000{ep}')
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            print(f"PASS: {ep} -> Status {resp.status}, Type: {resp.headers.get('Content-Type')}, Bytes: {len(data)}")
    except Exception as e:
        print(f"FAIL: {ep} -> {e}")
        all_passed = False

if all_passed:
    print("ALL BACKEND ENDPOINTS PASSED SUCCESSFULLY!")
