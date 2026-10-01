import re
import os

filepath = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/dashboard.html"
html = open(filepath, 'r').read()

# 1. Replace the #radar-map div with the iframe wrapper
# The map container was: <div id="radar-map" class="relative w-full h-[600px] bg-[#000a14] z-10"></div>
iframe_html = '''<div class="relative w-full h-[600px] bg-[#000a14] z-10">
    <iframe src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d14873500.574686544!2d77.83263028732367!3d20.656845584720177!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1sen!2sin!4v1789398085917!5m2!1sen!2sin" width="100%" height="100%" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" class="opacity-90 filter grayscale contrast-125 brightness-75 invert"></iframe>
</div>'''

# Find the radar-map div
html = re.sub(r'<div id="radar-map"[^>]*></div>', iframe_html, html)

# 2. Remove Leaflet CDN links from head
html = re.sub(r'<!-- Leaflet CSS & JS -->.*?<script src="https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js"[^>]*></script>', '', html, flags=re.DOTALL)

# 3. Remove the Leaflet init script at the bottom
# It starts with <script>\n  document.addEventListener("DOMContentLoaded", function() {\n    if (document.getElementById('radar-map')) {
html = re.sub(r'<script>\s*document\.addEventListener\("DOMContentLoaded", function\(\) \{\s*if \(document\.getElementById\(\'radar-map\'\)\) \{.*?</style>', '', html, flags=re.DOTALL)

open(filepath, 'w').write(html)
print("Replaced OpenStreetMap with Google Maps iframe.")
