import math
import numpy as np
from collections import Counter
from sklearn.cluster import DBSCAN

def cluster_detections(detections, eps_meters=500.0, min_samples=2):
    """
    Applies DBSCAN geospatial clustering on detection coordinates using exact Haversine metric.
    
    Parameters:
    - detections: list of dicts with 'latitude', 'longitude', 'class_name', 'verification_status', 'id', etc.
    - eps_meters: neighborhood distance threshold in meters (default 500m)
    - min_samples: minimum points required to form a core cluster (default 2)
    
    Returns:
    {
      'total_detections': int,
      'clustered_count': int,
      'noise_count': int,
      'total_clusters': int,
      'parameters': {'eps_meters': eps_meters, 'min_samples': min_samples},
      'clusters': [
         {
            'cluster_id': 'Cluster 01',
            'cluster_num': 1,
            'count': int,
            'dominant_class': str,
            'class_distribution': dict,
            'verified_count': int,
            'center': [lat, lon],
            'radius_meters': float,
            'detections': [...]
         }
      ],
      'noise': [...]  # List of isolated detections
    }
    """
    valid_points = []
    valid_dets = []
    
    for d in detections:
        try:
            lat = float(d.get('latitude'))
            lon = float(d.get('longitude'))
            if -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0):
                valid_points.append([lat, lon])
                valid_dets.append(d)
        except (TypeError, ValueError):
            continue
            
    if not valid_points:
        return {
            'total_detections': len(detections),
            'clustered_count': 0,
            'noise_count': 0,
            'total_clusters': 0,
            'parameters': {'eps_meters': eps_meters, 'min_samples': min_samples},
            'clusters': [],
            'noise': []
        }
        
    coords_deg = np.array(valid_points)
    # Convert degrees to radians for sklearn Haversine metric
    coords_rad = np.radians(coords_deg)
    
    # Earth radius in meters
    EARTH_RADIUS_METERS = 6371000.0
    eps_rad = eps_meters / EARTH_RADIUS_METERS
    
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric='haversine')
    labels = db.fit_predict(coords_rad)
    
    clusters_map = {}
    noise_list = []
    
    for idx, label in enumerate(labels):
        det = valid_dets[idx]
        if label == -1:
            noise_list.append(det)
        else:
            if label not in clusters_map:
                clusters_map[label] = []
            clusters_map[label].append(det)
            
    clusters_result = []
    clustered_total = 0
    
    for cluster_num, (label, c_dets) in enumerate(sorted(clusters_map.items()), 1):
        clustered_total += len(c_dets)
        c_lats = [float(d['latitude']) for d in c_dets]
        c_lons = [float(d['longitude']) for d in c_dets]
        center_lat = sum(c_lats) / len(c_lats)
        center_lon = sum(c_lons) / len(c_lons)
        
        # Calculate maximum radial distance from center in meters
        max_dist_m = 0.0
        for lat, lon in zip(c_lats, c_lons):
            dlat = math.radians(lat - center_lat)
            dlon = math.radians(lon - center_lon)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(lat)) * math.sin(dlon / 2)**2
            dist = EARTH_RADIUS_METERS * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if dist > max_dist_m:
                max_dist_m = dist
                
        classes = [d.get('class_name') or d.get('title') or 'unknown' for d in c_dets]
        class_counts = dict(Counter(classes))
        dominant_class = Counter(classes).most_common(1)[0][0] if classes else 'unknown'
        
        verified_count = sum(1 for d in c_dets if (d.get('verification_status') or '').lower() == 'verified')
        
        clusters_result.append({
            'cluster_id': f"Cluster {cluster_num:02d}",
            'cluster_num': cluster_num,
            'count': len(c_dets),
            'dominant_class': dominant_class,
            'class_distribution': class_counts,
            'verified_count': verified_count,
            'center': [round(center_lat, 6), round(center_lon, 6)],
            'centroid': [round(center_lat, 6), round(center_lon, 6)],
            'radius_meters': round(max(max_dist_m, 50.0), 1),
            'detections': c_dets
        })
        
    return {
        'total_detections': len(valid_dets),
        'clustered_count': clustered_total,
        'noise_count': len(noise_list),
        'total_clusters': len(clusters_result),
        'parameters': {'eps_meters': eps_meters, 'min_samples': min_samples},
        'clusters': clusters_result,
        'noise': noise_list
    }
