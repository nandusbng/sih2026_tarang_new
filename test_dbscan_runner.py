from dbscan_service import cluster_detections

test_detections = [
    # Cluster 1: Net concentration near Chennai coast (within ~200m)
    {'id': 'DET-001', 'class_name': 'ghost_net', 'confidence': 88.5, 'latitude': 13.0827, 'longitude': 80.2707, 'verification_status': 'verified'},
    {'id': 'DET-002', 'class_name': 'ghost_net', 'confidence': 91.2, 'latitude': 13.0835, 'longitude': 80.2715, 'verification_status': 'verified'},
    {'id': 'DET-003', 'class_name': 'ghost_net', 'confidence': 85.0, 'latitude': 13.0840, 'longitude': 80.2710, 'verification_status': 'pending'},

    # Cluster 2: Wreck site anomalies ~10km away
    {'id': 'DET-004', 'class_name': 'shipwreck', 'confidence': 94.0, 'latitude': 13.1800, 'longitude': 80.3500, 'verification_status': 'verified'},
    {'id': 'DET-005', 'class_name': 'shipwreck', 'confidence': 89.1, 'latitude': 13.1810, 'longitude': 80.3512, 'verification_status': 'verified'},

    # Noise point: isolated pot far away
    {'id': 'DET-006', 'class_name': 'crab_pot', 'confidence': 72.0, 'latitude': 13.4000, 'longitude': 80.5000, 'verification_status': 'pending'}
]

res = cluster_detections(test_detections, eps_meters=500.0, min_samples=2)
print("Total Clusters:", len(res['clusters']))
for c in res['clusters']:
    print(f"{c['cluster_id']}: {c['count']} points, Dominant: {c['dominant_class']}, Verified: {c['verified_count']}, Centroid: {c['centroid']}")
print("Noise points:", len(res['noise']))
