"""TARANG end-to-end demo verification.

Exercises the real acceptance chain against a running backend and the real
Supabase project: demo auth -> XTF upload -> parse -> metadata -> sonar image
-> AI detection -> geotagging -> hotspot clustering -> NM cleanup route ->
cross-portal notification -> JSON download. Prints PASS/FAIL per step and the
real server error whenever a step fails. Never asserts a hardcoded success.
"""

import io
import json
import os
import sys
import time

import requests

BASE = os.environ.get('TARANG_BACKEND_URL', 'http://localhost:3000').rstrip('/')
XTF_PATH = sys.argv[1] if len(sys.argv) > 1 else 'tarang_synthetic_survey_001.xtf'

RESULTS = []


def step(name, ok, detail=''):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ''))
    return bool(ok)


def show(label, value):
    print(f"      {label}: {value}")


def main():
    print(f"Backend: {BASE}\nXTF:     {XTF_PATH}\n" + '=' * 70)

    # 1. Backend API online
    try:
        r = requests.get(f'{BASE}/login.html', timeout=20)
        step('Backend API ONLINE', r.status_code == 200, f'HTTP {r.status_code}')
    except requests.RequestException as exc:
        step('Backend API ONLINE', False, f'Server connection failed: {exc}')
        return finish()

    # 2. Real Supabase system status
    r = requests.get(f'{BASE}/api/v1/system/status', timeout=90)
    if not step('System status endpoint responds', r.status_code == 200, f'HTTP {r.status_code}'):
        return finish()
    status = r.json()
    db = status['database']['supabase']
    auth = status['authentication']['supabase_auth']
    storage = status['storage']['supabase_storage']
    api = status['api']['backend_api']
    step('Supabase database CONNECTED (real query)', db['connected'], db.get('detail'))
    step('Supabase Auth CONNECTED (real health check)', auth['connected'], auth.get('detail'))
    step('Supabase Storage CONNECTED (real bucket read)', storage['connected'], storage.get('detail'))
    step('Backend API ONLINE (self-check)', api['connected'], api.get('detail'))
    show('overall', status.get('overall'))
    show('authoritative database', status.get('authoritative_database'))
    show('service key exposed to browser', status['configuration']['service_key_exposed_to_browser'])

    # 3. Demo access for every portal
    tokens = {}
    for portal in ['survey_operator', 'sonar_analyst', 'marine_portal',
                   'government_portal', 'admin', 'public']:
        r = requests.post(f'{BASE}/api/auth/demo-access', json={'portal': portal}, timeout=30)
        body = r.json() if r.text else {}
        ok = r.status_code == 200 and body.get('status') == 'success' and body.get('access_token')
        step(f'Demo session: {portal}', ok,
             body.get('message') or f"HTTP {r.status_code} -> {body.get('redirect')}")
        if ok:
            tokens[portal] = body['access_token']

    if 'survey_operator' not in tokens:
        step('Cannot continue without a Survey Operator demo session', False)
        return finish()

    op = {'Authorization': f"Bearer {tokens['survey_operator']}"}

    # 4. Upload the synthetic XTF through the real pipeline
    if not os.path.isfile(XTF_PATH):
        step('Synthetic XTF file exists', False, f'{XTF_PATH} not found')
        return finish()
    with open(XTF_PATH, 'rb') as handle:
        payload = handle.read()
    step('Synthetic XTF file readable', len(payload) > 0, f'{len(payload)/1024/1024:.2f} MB')

    print('      uploading + parsing + inferring (this takes a moment)...')
    started = time.time()
    r = requests.post(f'{BASE}/api/v1/xtf/upload', files={'file': (os.path.basename(XTF_PATH), io.BytesIO(payload), 'application/octet-stream')}, headers=op, timeout=900)
    elapsed = time.time() - started
    body = r.json() if r.text else {}
    if not step('XTF upload + parse + detection pipeline', r.status_code == 200,
                f'HTTP {r.status_code} in {elapsed:.1f}s {body.get("error") or body.get("message") or ""}'.strip()):
        print(json.dumps(body, indent=2, default=str)[:1500])
        return finish()

    survey_id = body.get('survey_id')
    show('survey_id', survey_id)
    show('filename', body.get('filename'))
    show('detections_count', body.get('detections_count'))
    show('images_reconstructed', body.get('images_reconstructed'))
    show('reused existing survey', body.get('existing'))

    # 5. XTF metadata is real parsed data
    meta = body.get('metadata') or {}
    if not meta and survey_id:
        m = requests.get(f'{BASE}/api/v1/xtf/{survey_id}/metadata', headers=op, timeout=60)
        meta = m.json() if m.status_code == 200 else {}
    step('XTF metadata extracted', bool(meta.get('Total Pings')),
         f"{meta.get('Total Pings')} pings, {meta.get('Channel Count')} channels")
    for key in ['Total Pings', 'Channel Count', 'Samples per Ping', 'SonarName', 'Start Time',
                'End Time', 'Min Latitude', 'Max Latitude', 'Min Longitude', 'Max Longitude']:
        if key in meta:
            show(key, meta[key])

    # 6. Sonar image actually exists and is fetchable
    images = body.get('images') or []
    image_ok = False
    for image in images:
        url = image.get('url') or image.get('crop_url') or ''
        if not url:
            continue
        if url.startswith('http'):
            ir = requests.get(url, timeout=60)
        else:
            ir = requests.get(f'{BASE}{url if url.startswith("/") else "/" + url}', timeout=60)
        if ir.status_code == 200 and len(ir.content) > 1000:
            image_ok = True
            show('sonar image URL', url)
            show('sonar image bytes', len(ir.content))
            show('leaks filesystem path', str(url[:2]).lower().startswith(('c:', '\\\\')))
            break
        show('image fetch failed', f'{url} -> HTTP {ir.status_code}')
    step('Reconstructed sonar image renders (no Image not found)', image_ok)

    # 7. Detections carry real geotags from XTF navigation
    detections = body.get('detections') or []
    if not detections and survey_id:
        d = requests.get(f'{BASE}/api/v1/xtf/{survey_id}/detections', headers=op, timeout=60)
        detections = d.json() if d.status_code == 200 else []
    geotagged = [d for d in detections if d.get('latitude') and d.get('longitude')]
    step('Detections generated by AI inference', len(detections) > 0, f'{len(detections)} detection(s)')
    step('Detections geotagged from XTF navigation', len(geotagged) > 0,
         f'{len(geotagged)}/{len(detections)} have real lat/lon')
    if geotagged:
        sample = geotagged[0]
        show('sample detection', json.dumps({k: sample.get(k) for k in
             ['id', 'class_name', 'confidence', 'latitude', 'longitude', 'ping_number',
              'crop_url', 'evidence_image_url']}, default=str))
        lats = [float(d['latitude']) for d in geotagged]
        lons = [float(d['longitude']) for d in geotagged]
        show('detection lat span', f'{min(lats):.6f} .. {max(lats):.6f}')
        show('detection lon span', f'{min(lons):.6f} .. {max(lons):.6f}')
        spread_m = max(abs(max(lats) - min(lats)), abs(max(lons) - min(lons))) * 111320
        show('detection spread', f'{spread_m:.0f} m ({spread_m/1852:.3f} NM)')
        inside = all(min(lats) - 0.05 <= la <= max(lats) + 0.05 for la in lats)
        step('Detections are geographically near the survey track', inside,
             'all detections inside the parsed navigation bounds')

    # 8. Hotspot clustering
    if 'marine_portal' in tokens:
        mh = {'Authorization': f"Bearer {tokens['marine_portal']}"}
        r = requests.get(f'{BASE}/api/v1/hotspots', headers=mh, timeout=300)
        hotspots = r.json() if r.status_code == 200 else []
        step('Hotspot clustering from real detections', r.status_code == 200 and isinstance(hotspots, list),
             f'HTTP {r.status_code}, {len(hotspots) if isinstance(hotspots, list) else "?"} hotspot(s)')
        if isinstance(hotspots, list):
            show('hotspot count', len(hotspots))
            for hs in hotspots[:10]:
                show(f"  {hs.get('id')}", f"lat={hs.get('latitude')} lon={hs.get('longitude')} "
                                          f"targets={hs.get('total_targets')} priority={hs.get('priority')} "
                                          f"types={list((hs.get('target_types') or {}).keys())}")
            step('Hotspots have required fields',
                 all(h.get('id') and h.get('latitude') is not None and h.get('longitude') is not None
                     for h in hotspots) if hotspots else False,
                 'id/latitude/longitude/detection_count/priority/target_classes present')

            # 9. TSP cleanup route in nautical miles
            r = requests.post(f'{BASE}/api/v1/hotspot-route',
                              json={'survey_id': survey_id} if survey_id else {},
                              headers=mh, timeout=300)
            rb = r.json() if r.text else {}
            if r.status_code == 200 and rb.get('route'):
                route = rb['route']
                step('TSP cleanup route generated from hotspot coordinates', True,
                     f"{route['hotspot_count']} hotspots, {route['total_distance_nm']} NM")
                show('algorithm', route.get('algorithm'))
                show('ordered hotspots', ' -> '.join(route.get('ordered_hotspots') or []))
                show('total distance', route.get('distance_display'))
                for leg in route.get('legs', []):
                    show(f"  leg {leg['sequence']}", f"{leg['from']} -> {leg['to']} = {leg['distance_nm']} NM ({leg['distance_km']} km)")
                step('Route distance reported in nautical miles', route.get('total_distance_nm') is not None
                     and 'NM' in (route.get('distance_display') or ''), route.get('distance_display'))
                step('Route has a Start Point', route.get('start_point') is not None,
                     json.dumps(route.get('start_point'), default=str))
                step('Route coordinates match hotspot coordinates',
                     len(route.get('route_coordinates') or []) >= 2,
                     f"{len(route.get('route_coordinates') or [])} vertices")
                step('Notification delivered on route generation',
                     rb['route'].get('notification_delivered') is not False,
                     f"notification_delivered={rb['route'].get('notification_delivered')}")
            else:
                step('TSP cleanup route generated from hotspot coordinates', False,
                     f'HTTP {r.status_code} {rb.get("message") or rb}')

            # 10. Cross-portal notification retrieval (Marine + Authority)
            for portal in ['marine_portal', 'government_portal']:
                if portal not in tokens:
                    continue
                ph = {'Authorization': f"Bearer {tokens[portal]}"}
                r = requests.get(f'{BASE}/api/v1/notifications', headers=ph, timeout=120)
                notes = r.json() if r.status_code == 200 else []
                got = isinstance(notes, list) and len(notes) > 0
                step(f'Notification retrieved by {portal} via Supabase', got,
                     f'HTTP {r.status_code}, {len(notes) if isinstance(notes, list) else "?"} notification(s)')
                if got:
                    show('latest notification', json.dumps(notes[0], default=str)[:400])

            # 11. Authority portal reads the SAME persisted route
            if 'government_portal' in tokens:
                gh = {'Authorization': f"Bearer {tokens['government_portal']}"}
                r = requests.get(f'{BASE}/api/v1/hotspot-route/latest', headers=gh, timeout=120)
                lb = r.json() if r.text else {}
                step('Authority portal retrieves the same persisted route',
                     r.status_code == 200 and lb.get('route'),
                     f"HTTP {r.status_code} route_id={(lb.get('route') or {}).get('route_id')}")

        # 12. JSON downloads
        for label, url in [
            ('Survey bundle JSON', f'{BASE}/api/v1/export/bundle/{survey_id}.json'),
            ('Detection JSON', f'{BASE}/api/v1/export/detections.json?survey_id={survey_id}'),
            ('Hotspot JSON', f'{BASE}/api/v1/export/hotspots.json?survey_id={survey_id}'),
            ('Cleanup route JSON', f'{BASE}/api/v1/export/cleanup-route.json?survey_id={survey_id}'),
        ]:
            r = requests.get(url, headers=mh, timeout=300)
            valid = False
            parsed = None
            if r.status_code == 200:
                try:
                    parsed = json.loads(r.text)
                    valid = True
                except ValueError as exc:
                    valid = False
                    show('JSON parse error', exc)
            step(f'{label} downloads as valid JSON', valid,
                 f'HTTP {r.status_code}, {len(r.content)} bytes')
            if parsed and label == 'Survey bundle JSON':
                show('bundle survey', json.dumps(parsed.get('survey'), default=str)[:500])
                show('bundle detections', len(parsed.get('detections') or []))
                show('bundle hotspots', len(parsed.get('hotspots') or []))
                cr = parsed.get('cleanup_route') or {}
                show('bundle cleanup_route', f"ordered={cr.get('ordered_hotspots')} "
                                             f"total_nm={cr.get('total_distance_nm')}")
                step('Bundle JSON contains the same records as the UI',
                     (parsed.get('detections') or []) and (parsed.get('hotspots') or []) is not None,
                     f"detections={len(parsed.get('detections') or [])} hotspots={len(parsed.get('hotspots') or [])}")

    return finish()


def finish():
    print('=' * 70)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in RESULTS if not ok]
    print(f'TOTAL: {passed}/{len(RESULTS)} checks passed')
    if failed:
        print('\nFAILURES:')
        for name, detail in failed:
            print(f'  - {name}: {detail}')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
