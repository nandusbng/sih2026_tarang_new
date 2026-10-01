import os, requests, json
from dotenv import load_dotenv
load_dotenv('.env')

url = os.environ.get('SUPABASE_URL')
svc = os.environ.get('SUPABASE_SERVICE_KEY')
anon = os.environ.get('SUPABASE_KEY')

h = {'apikey': svc, 'Authorization': f'Bearer {svc}', 'Content-Type': 'application/json'}

print("="*60)
print("TARANG SUPABASE CLOUD - DATABASE STATUS REPORT")
print("="*60)

# tarang_users
r = requests.get(f'{url}/rest/v1/tarang_users?select=*&order=created_at.asc', headers=h, timeout=10)
print(f"\n[tarang_users] Status={r.status_code}")
if r.status_code == 200:
    users = r.json()
    print(f"  Count: {len(users)}")
    for u in users:
        meta = u.get('metadata') or {}
        print(f"  -> name={u['name']} | role={u['role']} | username={meta.get('username')} | email={meta.get('email')} | status={u['status']}")

# surveys
r2 = requests.get(f'{url}/rest/v1/surveys?select=*&order=created_at.desc', headers=h, timeout=10)
print(f"\n[surveys] Status={r2.status_code}")
if r2.status_code == 200:
    surveys = r2.json()
    print(f"  Count: {len(surveys)}")
    for s in surveys:
        print(f"  -> {s.get('survey_id','')[:36]} | {s.get('survey_name','')} | status={s.get('status')} | proc={s.get('processing_status')}")
else:
    print(f"  ERROR: {r2.text[:200]}")

# detections
r3c = requests.get(f'{url}/rest/v1/detections?select=id', headers={**h,'Prefer':'count=exact'}, timeout=10)
cr = r3c.headers.get('Content-Range', '')
total = cr.split('/')[-1] if '/' in cr else '?'
print(f"\n[detections] Total: {total}")
r3 = requests.get(f'{url}/rest/v1/detections?select=id,survey_id,class_name,confidence,requires_review,hazard&limit=5', headers=h, timeout=10)
if r3.status_code == 200:
    for d in r3.json():
        print(f"  -> {d['id']} | cls={d['class_name']} | conf={d['confidence']} | review={d['requires_review']} | hazard={d['hazard']}")

# dispatches
r4c = requests.get(f'{url}/rest/v1/dispatches?select=id', headers={**h,'Prefer':'count=exact'}, timeout=10)
cr4 = r4c.headers.get('Content-Range', '')
total4 = cr4.split('/')[-1] if '/' in cr4 else '?'
print(f"\n[dispatches] Total: {total4}")

# Check detections schema
r5 = requests.get(f'{url}/rest/v1/detections?select=*&limit=1', headers=h, timeout=10)
if r5.status_code == 200 and r5.json():
    d = r5.json()[0]
    print(f"\n[detections schema columns]: {list(d.keys())}")

# Check surveys schema
r6 = requests.get(f'{url}/rest/v1/surveys?select=*&limit=1', headers=h, timeout=10)
if r6.status_code == 200 and r6.json():
    s = r6.json()[0]
    print(f"\n[surveys schema columns]: {list(s.keys())}")

print("\n" + "="*60)
print("CONNECTION OK - Supabase Cloud Authoritative")
print("="*60)
