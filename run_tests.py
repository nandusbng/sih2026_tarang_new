"""TARANG end-to-end endpoint test — all six portals, all critical routes."""
import sys, requests, json, os, builtins

_outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_results.txt')
_outfile = open(_outpath, 'w', encoding='utf-8')
_orig_print = builtins.print

def _print(*args, **kwargs):
    line = ' '.join(str(a) for a in args)
    _outfile.write(line + '\n')
    _outfile.flush()
    _orig_print(line)

builtins.print = _print

BASE = "http://localhost:3000"
PORTALS = ['survey_operator', 'sonar_analyst', 'marine_portal', 'government_portal', 'admin', 'public']
PASS = FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        FAIL += 1

def get_token(portal):
    r = requests.post(f"{BASE}/api/auth/demo-access", json={"portal": portal}, timeout=10)
    assert r.status_code == 200, f"demo-access {portal} failed: {r.status_code} {r.text[:100]}"
    return r.json()["access_token"]

# ── System status (no auth) ───────────────────────────────────────────────
print("\n=== System Status (no auth) ===")
r = requests.get(f"{BASE}/api/v1/system/status", timeout=15)
check("GET /api/v1/system/status → 200", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    check("overall field present", "overall" in data)
    check("database.supabase.connected", (data.get("database") or {}).get("supabase", {}).get("connected"))

# ── Demo access for all six portals ──────────────────────────────────────
print("\n=== Demo Access — all six portals ===")
tokens = {}
for portal in PORTALS:
    r = requests.post(f"{BASE}/api/auth/demo-access", json={"portal": portal}, timeout=10)
    ok = r.status_code == 200 and r.json().get("access_token")
    check(f"demo-access {portal}", ok, r.text[:80] if not ok else "")
    if ok:
        tokens[portal] = r.json()["access_token"]

# ── Core data endpoints ───────────────────────────────────────────────────
print("\n=== Core Data Endpoints ===")
for portal in ['survey_operator', 'marine_portal', 'government_portal', 'admin']:
    if portal not in tokens:
        continue
    h = {"Authorization": f"Bearer {tokens[portal]}"}

    r = requests.get(f"{BASE}/api/v1/surveys", headers=h, timeout=15)
    check(f"GET /api/v1/surveys [{portal}]", r.status_code == 200, r.text[:60])

    r = requests.get(f"{BASE}/api/v1/hotspots", headers=h, timeout=30)
    check(f"GET /api/v1/hotspots [{portal}]", r.status_code == 200, r.text[:60])

    r = requests.get(f"{BASE}/api/v1/notifications", headers=h, timeout=15)
    check(f"GET /api/v1/notifications [{portal}]", r.status_code == 200, r.text[:60])

    r = requests.get(f"{BASE}/api/v1/detections", headers=h, timeout=20)
    check(f"GET /api/v1/detections [{portal}]", r.status_code == 200, r.text[:60])

    r = requests.get(f"{BASE}/api/v1/clusters", headers=h, timeout=20)
    check(f"GET /api/v1/clusters [{portal}]", r.status_code == 200, r.text[:60])

# ── Sonar analyst access ──────────────────────────────────────────────────
print("\n=== Sonar Analyst Routes ===")
if 'sonar_analyst' in tokens:
    h = {"Authorization": f"Bearer {tokens['sonar_analyst']}"}
    r = requests.get(f"{BASE}/api/v1/surveys", headers=h, timeout=15)
    check("GET /api/v1/surveys [sonar_analyst]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/v1/detections", headers=h, timeout=20)
    check("GET /api/v1/detections [sonar_analyst]", r.status_code == 200)

# ── Marine portal workflow routes ─────────────────────────────────────────
print("\n=== Marine Portal Routes ===")
if 'marine_portal' in tokens:
    h = {"Authorization": f"Bearer {tokens['marine_portal']}"}
    r = requests.get(f"{BASE}/api/v1/cleanup/operations", headers=h, timeout=15)
    check("GET /api/v1/cleanup/operations [marine_portal]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/v1/clearance", headers=h, timeout=15)
    check("GET /api/v1/clearance [marine_portal]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/v1/routes", headers=h, timeout=15)
    check("GET /api/v1/routes [marine_portal]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/v1/hotspot-route", headers=h, timeout=30)
    check("GET /api/v1/hotspot-route [marine_portal]", r.status_code in (200, 409))

# ── Government portal routes ──────────────────────────────────────────────
print("\n=== Government Portal Routes ===")
if 'government_portal' in tokens:
    h = {"Authorization": f"Bearer {tokens['government_portal']}"}
    r = requests.get(f"{BASE}/api/v1/stats/government", headers=h, timeout=15)
    check("GET /api/v1/stats/government [government_portal]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/v1/documents", headers=h, timeout=15)
    check("GET /api/v1/documents [government_portal]", r.status_code == 200)

# ── Admin routes ──────────────────────────────────────────────────────────
print("\n=== Admin Routes ===")
if 'admin' in tokens:
    h = {"Authorization": f"Bearer {tokens['admin']}"}
    r = requests.get(f"{BASE}/api/admin/users", headers=h, timeout=15)
    check("GET /api/admin/users [admin]", r.status_code == 200)
    r = requests.get(f"{BASE}/api/admin/cleanup-teams", headers=h, timeout=10)
    check("GET /api/admin/cleanup-teams [admin]", r.status_code == 200)

# ── Public stats (no auth needed) ────────────────────────────────────────
print("\n=== Public Stats ===")
r = requests.get(f"{BASE}/api/v1/stats/public", timeout=15)
check("GET /api/v1/stats/public (no auth)", r.status_code == 200)

# ── Export endpoints ──────────────────────────────────────────────────────
print("\n=== Export Endpoints ===")
if 'survey_operator' in tokens:
    h = {"Authorization": f"Bearer {tokens['survey_operator']}"}
    surveys = requests.get(f"{BASE}/api/v1/surveys", headers=h, timeout=15).json()
    sid = surveys[0].get("survey_id") if surveys else "all"

    for url, label in [
        (f"/api/v1/export/survey/{sid}/json", "export bundle json"),
        (f"/api/v1/export/hotspots.json",      "export hotspots json"),
        (f"/api/v1/export/detections.json",    "export detections json"),
        (f"/api/v1/export/notifications.json", "export notifications json"),
    ]:
        r = requests.get(f"{BASE}{url}", headers=h, timeout=20)
        check(f"GET {url}", r.status_code == 200, r.text[:80] if r.status_code != 200 else "")

# ── 403 not returned for wrong role ──────────────────────────────────────
print("\n=== 403 Role Guard Checks ===")
if 'public' in tokens:
    h = {"Authorization": f"Bearer {tokens['public']}"}
    r = requests.get(f"{BASE}/api/admin/users", headers=h, timeout=10)
    check("GET /api/admin/users [public] → 403", r.status_code == 403)
    r = requests.get(f"{BASE}/api/v1/cleanup/operations", headers=h, timeout=10)
    check("GET /api/v1/cleanup/operations [public] → 403", r.status_code == 403)

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  TOTAL: {PASS+FAIL}  |  PASSED: {PASS}  |  FAILED: {FAIL}")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
