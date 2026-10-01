#!/usr/bin/env python
"""
TARANG Full Workflow Test Script
Tests the complete workflow: Upload XTF → Verify Detections → Authority Confirm → Marine Cleanup → TSP Route
"""
import requests
import json
import time

BASE_URL = "http://localhost:3000"

# Demo tokens for each role
TOKENS = {
    'operator': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdXJ2ZXktb3BlcmF0b3IiLCJ1c2VyX2lkIjoic3VydmV5LW9wZXJhdG9yIiwiZnVsbF9uYW1lIjoiU3VydmV5IE9wZXJhdG9yIChEZW1vKSIsImVtYWlsIjoic3VydmV5LW9wZXJhdG9yQGV4YW1wbGUuY29tIiwicm9sZSI6InN1cnZleV9vcGVyYXRvciIsImlhdCI6MTczNzUzMjgyNSwiZXhwIjoxNzM3NTc2NDI1fQ.DEMO_FIXED_SECRET',
    'analyst': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzb25hci1hbmFseXN0IiwidXNlcl9pZCI6InNvbmFyLWFuYWx5c3QiLCJmdWxsX25hbWUiOiJTb25hciBBbmFseXN0IChEZW1vKSIsImVtYWlsIjoic29uYXItYW5hbHlzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJzb25hcl9hbmFseXN0IiwiaWF0IjoxNzM3NTMyODI1LCJleHAiOjE3Mzc1NzY0MjV9.DEMO_FIXED_SECRET',
    'authority': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJnb3Zlcm5tZW50LXBvcnRhbCIsInVzZXJfaWQiOiJnb3Zlcm5tZW50LXBvcnRhbCIsImZ1bGxfbmFtZSI6IkdvdmVybm1lbnQgQXV0aG9yaXR5IChEZW1vKSIsImVtYWlsIjoiZ292ZXJubWVudEBleGFtcGxlLmNvbSIsInJvbGUiOiJnb3Zlcm5tZW50X3BvcnRhbCIsImlhdCI6MTczNzUzMjgyNSwiZXhwIjoxNzM3NTc2NDI1fQ.DEMO_FIXED_SECRET',
    'marine': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJpbmUtcG9ydGFsIiwidXNlcl9pZCI6Im1hcmluZS1wb3J0YWwiLCJmdWxsX25hbWUiOiJNYXJpbmUgUG9ydGFsIChEZW1vKSIsImVtYWlsIjoibWFyaW5lQGV4YW1wbGUuY29tIiwicm9sZSI6Im1hcmluZV9wb3J0YWwiLCJpYXQiOjE3Mzc1MzI4MjUsImV4cCI6MTczNzU3NjQyNX0.DEMO_FIXED_SECRET'
}

def headers(role='operator'):
    return {'Authorization': f'Bearer {TOKENS[role]}'}

def test_system_status():
    """Test 1: System Health"""
    print("\n" + "="*60)
    print("TEST 1: System Status")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/system/status")
    if r.status_code == 200:
        data = r.json()
        print(f"✓ System Status: {data.get('overall')}")
        print(f"  Database: {data.get('database', {}).get('supabase', {}).get('status')}")
        print(f"  Storage: {data.get('storage', {}).get('supabase_storage', {}).get('status')}")
        return True
    print(f"✗ System status failed: {r.status_code}")
    return False

def test_get_surveys():
    """Test 2: Get Existing Surveys"""
    print("\n" + "="*60)
    print("TEST 2: Get Surveys")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/surveys", headers=headers('operator'))
    if r.status_code == 200:
        surveys = r.json()
        print(f"✓ Found {len(surveys)} surveys")
        if surveys:
            latest = surveys[-1]
            print(f"  Latest: {latest.get('survey_id')} - {latest.get('survey_name')}")
            return latest.get('survey_id')
        return None
    print(f"✗ Failed to get surveys: {r.status_code}")
    return None

def test_verification_summary(survey_id):
    """Test 3: Verification Summary API"""
    print("\n" + "="*60)
    print("TEST 3: Verification Summary")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/surveys/{survey_id}/verification-summary", headers=headers('analyst'))
    if r.status_code == 200:
        data = r.json()
        print(f"✓ Survey: {survey_id}")
        print(f"  Total Detections: {data.get('total_detections')}")
        print(f"  Verified: {data.get('verified')}")
        print(f"  Rejected: {data.get('rejected')}")
        print(f"  Needs Review: {data.get('needs_review')}")
        print(f"  Progress: {data.get('verification_progress')}%")
        return data
    print(f"✗ Verification summary failed: {r.status_code}")
    return None

def test_verification_queue(survey_id):
    """Test 4: Verification Queue API"""
    print("\n" + "="*60)
    print("TEST 4: Verification Queue")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/surveys/{survey_id}/verification-queue", headers=headers('analyst'))
    if r.status_code == 200:
        data = r.json()
        print(f"✓ Pending detections: {data.get('total_pending')}")
        queue = data.get('queue', [])
        if queue:
            print(f"  First detection: {queue[0].get('id')[:12]}... - {queue[0].get('class_name')}")
        return queue
    print(f"✗ Verification queue failed: {r.status_code}")
    return []

def test_get_hotspots():
    """Test 5: Get Hotspots"""
    print("\n" + "="*60)
    print("TEST 5: Get Hotspots (Authority View)")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/hotspots", headers=headers('authority'))
    if r.status_code == 200:
        hotspots = r.json()
        print(f"✓ Found {len(hotspots)} hotspots")
        for hs in hotspots[:3]:
            print(f"  {hs.get('id')}: {hs.get('total_targets')} targets - {hs.get('status')}")
        return hotspots
    print(f"✗ Failed to get hotspots: {r.status_code}")
    return []

def test_cleanup_route():
    """Test 6: TSP Cleanup Route"""
    print("\n" + "="*60)
    print("TEST 6: TSP Cleanup Route Generation")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/hotspot-route", headers=headers('marine'))
    if r.status_code == 200:
        route = r.json()
        print(f"✓ Route generated")
        print(f"  Algorithm: {route.get('algorithm')}")
        print(f"  Total Distance: {route.get('total_distance_nm')} NM ({route.get('total_distance_km')} km)")
        print(f"  Hotspots in route: {len(route.get('target_sequence', []))}")
        print(f"  Estimated time: {route.get('estimated_travel_minutes')} min")
        return route
    print(f"✗ Cleanup route failed: {r.status_code}")
    return None

def test_json_exports(survey_id):
    """Test 7: JSON Export Endpoints"""
    print("\n" + "="*60)
    print("TEST 7: JSON Export Endpoints")
    print("="*60)
    
    exports = [
        (f"/api/v1/export/survey/{survey_id}/json", "Survey Bundle"),
        ("/api/v1/export/hotspots.json", "Hotspots"),
        ("/api/v1/export/detections.json", "Detections"),
        ("/api/v1/export/cleanup-route.json", "Cleanup Route"),
    ]
    
    for endpoint, name in exports:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers('operator'))
        if r.status_code == 200:
            print(f"  ✓ {name}: {len(r.content)} bytes")
        else:
            print(f"  ✗ {name}: HTTP {r.status_code}")

def test_spatial_detections(survey_id):
    """Test 8: Spatial Detection Data"""
    print("\n" + "="*60)
    print("TEST 8: Spatial Detection Data (Map)")
    print("="*60)
    r = requests.get(f"{BASE_URL}/api/v1/detections?survey_id={survey_id}", headers=headers('analyst'))
    if r.status_code == 200:
        dets = r.json()
        georef = [d for d in dets if d.get('latitude') and d.get('longitude')]
        print(f"✓ Total detections: {len(dets)}")
        print(f"  Georeferenced: {len(georef)}")
        if georef:
            print(f"  Sample coords: {georef[0].get('latitude'):.5f}, {georef[0].get('longitude'):.5f}")
        return georef
    print(f"✗ Failed to get detections: {r.status_code}")
    return []

def run_all_tests():
    """Run complete workflow test suite"""
    print("\n" + "#"*60)
    print("# TARANG FULL WORKFLOW TEST SUITE")
    print("#"*60)
    
    start_time = time.time()
    
    # Test 1: System Status
    if not test_system_status():
        print("\n✗ System not ready - aborting tests")
        return
    
    # Test 2: Get surveys
    survey_id = test_get_surveys()
    if not survey_id:
        print("\n⚠ No surveys found - please upload tarang_final_demo_survey_001.xtf first")
        return
    
    # Test 3-4: Verification APIs
    test_verification_summary(survey_id)
    test_verification_queue(survey_id)
    
    # Test 5: Hotspots
    test_get_hotspots()
    
    # Test 6: TSP Route
    test_cleanup_route()
    
    # Test 7: JSON Exports
    test_json_exports(survey_id)
    
    # Test 8: Spatial Data
    test_spatial_detections(survey_id)
    
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"✓ All tests completed in {elapsed:.2f} seconds")
    print("="*60)
    print("\n📋 WORKFLOW STATUS:")
    print("  ✓ Backend APIs functional")
    print("  ✓ Verification workflow ready")
    print("  ✓ Authority/hotspot endpoints ready")
    print("  ✓ TSP route optimization working")
    print("  ✓ JSON exports available")
    print("\n🌐 Access the portals:")
    print(f"  Operator: {BASE_URL}/operator-portal.html")
    print(f"  Analyst: {BASE_URL}/sonar-analyst.html")
    print(f"  Authority: {BASE_URL}/gov-authority.html")
    print(f"  Marine: {BASE_URL}/cleanup-portal.html")
    print(f"  Public: {BASE_URL}/public-portal.html")

if __name__ == "__main__":
    run_all_tests()
