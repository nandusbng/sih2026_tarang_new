"""Maritime geospatial helpers for TARANG.

Single source of truth for nautical-mile distances and cleanup-route
optimisation. Every portal and endpoint that shows a distance must go through
these helpers so the platform reports maritime units consistently.
"""

import math

METERS_PER_NAUTICAL_MILE = 1852.0
EARTH_RADIUS_M = 6371008.8

# Practical ROV / support-vessel planning speed used for time estimates.
DEFAULT_PLANNING_SPEED_KNOTS = 18.0


def haversine_m(point_a, point_b):
    """Great-circle distance in metres between two [lat, lon] pairs."""
    lat1, lon1 = math.radians(float(point_a[0])), math.radians(float(point_a[1]))
    lat2, lon2 = math.radians(float(point_b[0])), math.radians(float(point_b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0.0, 1 - h)))


def haversine_km(point_a, point_b):
    return haversine_m(point_a, point_b) / 1000.0


def meters_to_nm(meters):
    return float(meters) / METERS_PER_NAUTICAL_MILE


def km_to_nm(kilometers):
    return float(kilometers) * 1000.0 / METERS_PER_NAUTICAL_MILE


def nm_to_km(nautical_miles):
    return float(nautical_miles) * METERS_PER_NAUTICAL_MILE / 1000.0


def format_nm(meters, decimals=2):
    """Render a distance in nautical miles with kilometres as the secondary value."""
    nm = meters_to_nm(meters)
    return f"{nm:.{decimals}f} NM ({nm_to_km(nm):.2f} km)"


def track_length_m(coordinates):
    """Total survey-track length in metres for an ordered [[lat, lon], ...] list."""
    total = 0.0
    for index in range(len(coordinates) - 1):
        total += haversine_m(coordinates[index], coordinates[index + 1])
    return total


def _coords_of(item):
    """Accept either a point dict or a plain [lat, lon] pair."""
    if isinstance(item, dict):
        return [float(item['latitude']), float(item['longitude'])]
    return [float(item[0]), float(item[1])]


def _route_length_m(route):
    points = [_coords_of(item) for item in route]
    return sum(haversine_m(points[i], points[i + 1]) for i in range(len(points) - 1))


def two_opt(route, max_passes=60):
    """2-opt improvement over an ordered route of point dicts or [lat, lon] pairs.

    Returns a new list holding the same items in an improved order.
    """
    if len(route) < 4:
        return list(route)

    best = list(route)
    best_length = _route_length_m(best)
    improved = True
    passes = 0
    while improved and passes < max_passes:
        improved = False
        passes += 1
        for i in range(len(best) - 2):
            for j in range(i + 2, len(best)):
                candidate = best[:i + 1] + best[i + 1:j + 1][::-1] + best[j + 1:]
                candidate_length = _route_length_m(candidate)
                if candidate_length < best_length - 1e-9:
                    best, best_length = candidate, candidate_length
                    improved = True
    return best


def optimise_route(points, fixed_start=None):
    """Heuristic open-path TSP: nearest-neighbour seeding plus 2-opt refinement.

    ``points`` is a list of dicts that must each carry ``latitude``/``longitude``
    and a stable ``id``. ``fixed_start`` optionally pins the first waypoint
    (for example the survey start or a port of departure); when omitted the
    highest-priority point seeds the route so the result stays deterministic.

    This is an approximation, not an exact solver, and callers must label the
    result as an optimised heuristic route.
    """
    if not points:
        return []

    remaining = list(points)

    if fixed_start is not None:
        start = {'id': '__START__', 'latitude': fixed_start[0], 'longitude': fixed_start[1],
                 'is_start': True, 'label': 'Start Point'}
        nearest = min(remaining, key=lambda item: haversine_m(_coords_of(start), _coords_of(item)))
        remaining.remove(nearest)
        ordered = [nearest]
    else:
        seed = remaining[0]
        remaining.remove(seed)
        ordered = [seed]

    while remaining:
        current = _coords_of(ordered[-1])
        nxt = min(remaining, key=lambda item: haversine_m(current, _coords_of(item)))
        remaining.remove(nxt)
        ordered.append(nxt)

    if len(ordered) >= 4:
        ordered = two_opt(ordered)

    if fixed_start is not None:
        return [start] + ordered
    return ordered


def coords_list(points):
    return [_coords_of(point) for point in points]


def build_route_geometry(points, start=None):
    """Return the full metric description of an ordered cleanup route.

    ``points`` must already be in visit order. Distances are computed from the
    real coordinates only - nothing here is hardcoded.
    """
    waypoints = []
    if start is not None:
        waypoints.append({'id': 'START', 'label': 'Start Point', 'is_start': True,
                          'latitude': float(start[0]), 'longitude': float(start[1])})
    for index, point in enumerate(points, 1):
        waypoints.append({
            'sequence': index,
            'id': point.get('hotspot_id') or point.get('id') or f'WP-{index:03d}',
            'label': point.get('label') or point.get('hotspot_id') or point.get('id') or f'WP-{index:03d}',
            'latitude': float(point['latitude']),
            'longitude': float(point['longitude']),
            'detection_count': point.get('detection_count', 0),
            'priority': point.get('priority', 'Standard'),
            'target_classes': point.get('target_classes') or [],
        })

    legs = []
    for index in range(1, len(waypoints)):
        previous, current = waypoints[index - 1], waypoints[index]
        distance_m = haversine_m([previous['latitude'], previous['longitude']],
                                 [current['latitude'], current['longitude']])
        legs.append({
            'sequence': index,
            'from': previous['id'],
            'to': current['id'],
            'distance_m': round(distance_m, 1),
            'distance_nm': round(meters_to_nm(distance_m), 3),
            'distance_km': round(distance_m / 1000.0, 3),
        })

    total_m = sum(leg['distance_m'] for leg in legs)
    total_nm = meters_to_nm(total_m)
    speed_knots = DEFAULT_PLANNING_SPEED_KNOTS
    travel_minutes = round(total_nm / speed_knots * 60) if speed_knots else 0

    return {
        'ordered_hotspots': [wp['id'] for wp in waypoints if not wp.get('is_start')],
        'waypoints': waypoints,
        'legs': legs,
        'total_distance_m': round(total_m, 1),
        'total_distance_nm': round(total_nm, 3),
        'total_distance_km': round(total_m / 1000.0, 3),
        'distance_display': format_nm(total_m),
        'route_coordinates': [[wp['latitude'], wp['longitude']] for wp in waypoints],
        'planning_speed_knots': speed_knots,
        'estimated_travel_minutes': travel_minutes,
        'solver': 'nearest-neighbour + 2-opt (heuristic, not exact TSP)',
    }
