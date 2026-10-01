import re
import os

filepath = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/dashboard.html"
html = open(filepath, 'r').read()

# 1. Add Leaflet CDN if not present
if 'leaflet.css' not in html:
    leaflet_cdn = """
<!-- Leaflet CSS & JS -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
"""
    html = html.replace('</head>', leaflet_cdn + '</head>')

# 2. Replace the radar canvas area with the map div
# We will match from <div class="relative w-full h-[600px] bg-[#000a14]... to the closing tag before <!-- Footer telemetry -->
pattern = r'(<!-- Radar Canvas Area -->\s*)<div class="relative w-full h-\[600px\] bg-\[#000a14\].*?(?=<!-- Footer telemetry -->)'
replacement = r'''\1<div id="radar-map" class="relative w-full h-[600px] bg-[#000a14] z-10"></div>
    '''
html = re.sub(pattern, replacement, html, flags=re.DOTALL)

# 3. Add the initialization script at the end of the body
map_script = """
<script>
  document.addEventListener("DOMContentLoaded", function() {
    if (document.getElementById('radar-map')) {
      // Initialize map centered on Arabian Sea / Bay of Bengal transect
      var map = L.map('radar-map').setView([14.5020, 85.1290], 7);
      
      // Use CartoDB Dark Matter tiles for a command-center look based on OSM
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
          subdomains: 'abcd',
          maxZoom: 20
      }).addTo(map);
      
      // Target 1: Ghost Net
      var target1 = L.circleMarker([13.5, 79.8], {
          color: '#E11D48',
          fillColor: '#E11D48',
          fillOpacity: 0.8,
          radius: 8,
          weight: 2
      }).addTo(map);
      target1.bindPopup(`
        <div style="background:#00101d; color:#f8f9ff; padding:8px; border:1px solid #E11D48; border-radius:4px; font-family:monospace;">
          <strong style="color:#E11D48;">> TRG-882 [96.2% CONF]</strong><br>
          <span style="font-size:14px; font-weight:bold;">SUBMERGED GHOST NET</span><br>
          <span style="color:#5bb8fe; font-size:11px;">MASS: 2.1 T | DRIFT: 1.8kn SE</span><br>
          <span style="color:#E11D48; font-size:11px;">RISK: CRITICAL</span>
        </div>
      `, {
        className: 'custom-terminal-popup'
      });
      
      // Target 2: Macroplastic
      var target2 = L.circleMarker([12.2, 81.0], {
          color: '#D97706',
          fillColor: '#D97706',
          fillOpacity: 0.8,
          radius: 10,
          weight: 2
      }).addTo(map);
      target2.bindPopup(`
        <div style="background:#00101d; color:#f8f9ff; padding:8px; border:1px solid #D97706; border-radius:4px; font-family:monospace;">
          <strong style="color:#D97706;">> CLUSTER-904 [89.4% CONF]</strong><br>
          <span style="font-size:14px; font-weight:bold;">MACROPLASTIC SLICK</span><br>
          <span style="color:#5bb8fe; font-size:11px;">AREA: 480 m² | HDG: 114°</span><br>
          <span style="color:#14B8A6; font-size:11px;">STAT: TRACKED</span>
        </div>
      `, {
        className: 'custom-terminal-popup'
      });
      
      // Interceptor
      var interceptorIcon = L.divIcon({
        className: 'custom-interceptor-icon',
        html: '<div style="background:#14B8A6; width:24px; height:24px; border-radius:4px; display:flex; align-items:center; justify-content:center; box-shadow: 0 0 10px #14B8A6;"><span class="material-symbols-outlined" style="color:#00101d; font-size:16px;">directions_boat</span></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });
      
      var interceptor = L.marker([12.8, 80.0], {icon: interceptorIcon}).addTo(map);
      interceptor.bindPopup(`
        <div style="background:#00101d; color:#f8f9ff; padding:8px; border:1px solid #14B8A6; border-radius:4px; font-family:monospace;">
          <strong style="color:#14B8A6;">> ICGS-VARUNA</strong><br>
          <span style="color:#5bb8fe; font-size:11px;">SPEED: 12.4 kn</span>
        </div>
      `, {
        className: 'custom-terminal-popup'
      });
    }
  });
</script>
<style>
/* Leaflet Popup overrides for terminal styling */
.custom-terminal-popup .leaflet-popup-content-wrapper {
  background: transparent;
  box-shadow: none;
  padding: 0;
  border-radius: 0;
}
.custom-terminal-popup .leaflet-popup-tip {
  background: #00101d;
  border: 1px solid #14B8A6;
  border-top: none;
  border-left: none;
}
.custom-terminal-popup .leaflet-popup-content {
  margin: 0;
}
</style>
</body>
"""

html = html.replace('</body>', map_script)
open(filepath, 'w').write(html)
print("Replaced CSS radar with interactive OpenStreetMap (Leaflet + Carto Dark)")
