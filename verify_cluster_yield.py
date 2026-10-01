"""Simulate the real XTF -> geotag -> DBSCAN chain without the HTTP server.

Uses the same functions the app uses (xtf_parser, best.pt, dbscan_service) so
the cluster count reported here is the count the live pipeline will produce.
"""
import xtf_parser
import tarang_geo as tg
from ultralytics import YOLO
from dbscan_service import cluster_detections

XTF = 'tarang_synthetic_survey_002.xtf'
IMG_DIR = 'outputs/_yield_check'

res = xtf_parser.parse_xtf(XTF, IMG_DIR)
pings = res['pings']
model = YOLO('best.pt')

dets = []
seq = 0
for im in res['images']:
    r = model(im['path'], conf=0.20, verbose=False)[0]
    for b in r.boxes:
        seq += 1
        conf = float(b.conf[0]) * 100
        cls = model.names.get(int(b.cls[0]), '?') if conf >= 50 else 'unknown'
        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
        idx = im['ping_start'] + int((y1 + y2) / 2.0)
        if idx >= len(pings):
            continue
        p = pings[idx]
        dets.append({
            'id': 'D%02d' % seq, 'class_name': cls, 'confidence': round(conf, 1),
            'latitude': p.get('latitude'), 'longitude': p.get('longitude'),
            'ping_number': idx, 'is_offshore': True, 'detection_status': 'Pending',
        })

print('geotagged detections:', len(dets))
for d in dets:
    print('  %-5s %-18s %5.1f%%  ping=%-6s lat=%.6f lon=%.6f'
          % (d['id'], d['class_name'], d['confidence'], d['ping_number'],
             d['latitude'], d['longitude']))

cl = cluster_detections(dets, eps_meters=1500.0, min_samples=2)
clusters = cl.get('clusters', [])
print()
print('CLUSTERS:', len(clusters))
for c in clusters:
    print('  #%s center=%s count=%s dominant=%s radius_m=%.1f'
          % (c.get('cluster_num'), c.get('center'), c.get('count'),
             c.get('dominant_class'), c.get('radius_meters', 0.0)))
print('noise:', len(cl.get('noise', []) or []))

cen = [c['center'] for c in clusters if isinstance(c.get('center'), list) and len(c['center']) == 2]
print()
print('pairwise cluster separations:')
for i in range(len(cen)):
    for j in range(i + 1, len(cen)):
        m = tg.haversine_m(cen[i], cen[j])
        print('  C%d<->C%d: %s' % (i + 1, j + 1, tg.format_nm(m)))

if len(cen) >= 2:
    route = tg.build_route_geometry(
        [{'id': 'HS-%d' % (i + 1), 'latitude': c[0], 'longitude': c[1]} for i, c in enumerate(cen)],
        start=cen[0])
    print()
    print('SIMULATED TSP ROUTE over %d hotspots' % len(cen))
    print('  solver  :', route.get('solver'))
    print('  order   :', route.get('ordered_hotspots'))
    print('  total   :', route.get('distance_display'))
    print('  nm*1852 :', round(route['total_distance_nm'] * 1852.0, 1), 'vs total_m', round(route['total_distance_m'], 1))
    for leg in route.get('legs', []):
        print('   leg %s %s->%s %.3f NM (%.2f km)'
              % (leg['sequence'], leg['from'], leg['to'], leg['distance_nm'], leg['distance_km']))
