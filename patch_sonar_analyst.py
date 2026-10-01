import re

with open('sonar-analyst.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Include Leaflet & TarangMap in head
head_includes = """  <!-- Leaflet & TARANG Shared Map -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="js/tarang-map.js"></script>"""

if 'tarang-map.js' not in html:
    html = html.replace('<!-- Tailwind CSS -->', head_includes + '\n  <!-- Tailwind CSS -->')

# 2. Light Theme CSS styling
light_theme_styles = """  <style>
    body {
      background-color: #f8fafc;
      background-image: 
        radial-gradient(circle at 12% 18%, rgba(2, 132, 199, 0.04) 0%, transparent 40%),
        radial-gradient(circle at 88% 82%, rgba(13, 148, 136, 0.04) 0%, transparent 40%),
        linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
      color: #0f172a;
      font-family: 'Inter', sans-serif;
    }
    .marine-panel {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid #e2e8f0;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }
    .marine-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease-in-out;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }
    .marine-card:hover {
      border-color: #cbd5e1;
      box-shadow: 0 6px 18px -4px rgba(15, 23, 42, 0.06);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #f1f5f9;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    .waterfall-grid {
      background-size: 32px 32px;
      background-image: 
        linear-gradient(to right, rgba(226, 232, 240, 0.6) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(226, 232, 240, 0.6) 1px, transparent 1px);
    }
  </style>"""

html = re.sub(r'<style>.*?</style>', light_theme_styles, html, flags=re.DOTALL)

# 3. Replace dark theme background/border classes
html = html.replace('bg-[#020b15]', 'bg-white')
html = html.replace('bg-[#031326]', 'bg-slate-50')
html = html.replace('bg-[#041324]', 'bg-white')
html = html.replace('bg-[#071d34]', 'bg-white')
html = html.replace('bg-[#08223f]', 'bg-slate-100')
html = html.replace('border-slate-800', 'border-slate-200')
html = html.replace('text-white', 'text-slate-900')

# 4. Ensure Empty States match requirements
html = re.sub(
    r'No pending triage targets\.[^<]*',
    'No AI detections available for this survey.',
    html
)
html = re.sub(
    r'No detections match current filter\.[^<]*',
    'No AI detections available for this survey.',
    html
)
html = re.sub(
    r'No targets pending verification\.[^<]*',
    'No AI detections available for this survey.',
    html
)

# 5. Remove any visible v3.4
html = re.sub(r'[Vv]3\.4', '', html)

with open('sonar-analyst.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("sonar-analyst.html updated successfully.")
