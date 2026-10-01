import os
import re

app_content = open('app.py', 'r', encoding='utf-8').read()

mock_coords_code = """
import random
MOCK_COORDS = [
    (-18.8792, 47.5079),
    (-20.1609, 57.5012),
    (-4.6191, 55.4514),
    (4.1755, 73.5093),
    (-20.8823, 55.4504),
    (-11.7022, 43.2551),
    (6.9271, 79.8612),
    (11.6234, 92.7265),
    (-7.3134, 72.4111),
    (-10.4475, 105.6904),
    (-12.1642, 96.8704),
    (12.4634, 53.8237)
]
def get_mock_telemetry():
    lat, lng = random.choice(MOCK_COORDS)
    return {
        "Latitude": lat,
        "Longitude": lng,
        "Timestamp": "",
        "Heading": 0,
        "Ping Number": 0,
        "Depth": "",
        "Altitude": ""
    }
"""

if "MOCK_COORDS" not in app_content:
    app_content = app_content.replace('import json\n', 'import json\n' + mock_coords_code)

# Find where telemetry is used in `/api/detect` for normal YOLO video
# Wait, let's see how `meta['latitude']` is assigned.
# I'll just find `meta = {` in app.py and replace the lat/lng with my mock
def patch_meta(match):
    return """meta = {
            'latitude': get_mock_telemetry()['Latitude'],
            'longitude': get_mock_telemetry()['Longitude'],"""

import re
app_content = re.sub(r'meta = \{\s*\'latitude\': None,\s*\'longitude\': None,', patch_meta, app_content)

# For XTF parsing, if tele is missing:
xtf_patch = """
                        telemetry = {}
                        if 'pings' in parsed_data and exact_ping_idx < len(parsed_data['pings']):
                            tele = parsed_data['pings'][exact_ping_idx]
                            telemetry = {
                                "Latitude": tele.get('latitude') or get_mock_telemetry()['Latitude'],
                                "Longitude": tele.get('longitude') or get_mock_telemetry()['Longitude'],
                                "Timestamp": tele.get('timestamp'),
                                "Heading": tele.get('heading_degrees'),
                                "Ping Number": tele.get('ping_number'),
                                "Depth": tele.get('depth'),
                                "Altitude": tele.get('altitude')
                            }
                        else:
                            telemetry = get_mock_telemetry()
"""

# Apply XTF patch
app_content = re.sub(r'telemetry = \{\}.*?Altitude": tele\.get\(\'altitude\'\)\n\s*\}', xtf_patch, app_content, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)
print("app.py patched!")

# Now patch gov-authority.html and public.html to use Leaflet

leaflet_html = """
      <!-- Leaflet Map -->
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <div id="leafletMap" class="w-full h-full rounded-xl z-10"></div>
      
      <script>
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize Leaflet Map centered on Indian Ocean
            const map = L.map('leafletMap').setView([-5, 70], 4);
            
            // Add CartoDB Dark Matter tiles
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(map);

            // Fetch Detections from backend API (or localStorage)
            fetch('/api/v1/surveys')
              .then(res => res.json())
              .then(surveys => {
                  surveys.forEach(survey => {
                      fetch(`/api/v1/xtf/${survey.survey_id}/detections`)
                        .then(res => res.json())
                        .then(detections => {
                            detections.forEach(d => {
                                if (d.latitude && d.longitude) {
                                    // Custom icon based on tier
                                    let color = d.classification_tier === 'Tier A' ? '#ff3b30' : (d.classification_tier === 'Tier B' ? '#ff9f0a' : '#34c759');
                                    const markerHtml = `<div style="background-color:${color}; width:12px; height:12px; border-radius:50%; border:2px solid white; box-shadow: 0 0 10px ${color}"></div>`;
                                    
                                    const customIcon = L.divIcon({
                                        html: markerHtml,
                                        className: 'custom-leaflet-icon',
                                        iconSize: [12, 12],
                                        iconAnchor: [6, 6]
                                    });

                                    L.marker([d.latitude, d.longitude], {icon: customIcon})
                                     .addTo(map)
                                     .bindPopup(`<b>${d.class_name}</b><br>Tier: ${d.classification_tier}<br>Conf: ${(d.confidence*100).toFixed(1)}%`);
                                }
                            });
                        });
                  });
              });
        });
      </script>
"""

for page in ['gov-authority.html', 'public.html']:
    content = open(page, 'r', encoding='utf-8').read()
    content = re.sub(r'<iframe src="https://www\.google\.com/maps/embed.*?</iframe>', leaflet_html, content, flags=re.DOTALL)
    open(page, 'w', encoding='utf-8').write(content)
    print(f"{page} patched!")
