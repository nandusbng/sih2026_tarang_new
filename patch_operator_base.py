import re

with open('operator-portal.html', 'r', encoding='utf-8') as f:
    html = f.read()

# -------------------------------------------------------------
# 1. Update Title & Fonts & Three.js imports
# -------------------------------------------------------------
threejs_scripts = """  <!-- Three.js & GLTFLoader for Local 3D Drone Survey Simulation -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
  <!-- TARANG Shared Map Engine -->
  <script src="js/tarang-map.js"></script>"""

if 'three.min.js' not in html:
    html = html.replace('<!-- Tailwind CSS via CDN -->', threejs_scripts + '\n  <!-- Tailwind CSS via CDN -->')

# -------------------------------------------------------------
# 2. Light Theme CSS Tokens & Styling
# -------------------------------------------------------------
light_theme_styles = """  <style>
    body {
      background-color: #f8fafc;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(2, 132, 199, 0.04) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(13, 148, 136, 0.04) 0%, transparent 40%),
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
    .waterfall-grid {
      background-size: 32px 32px;
      background-image: 
        linear-gradient(to right, rgba(226, 232, 240, 0.6) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(226, 232, 240, 0.6) 1px, transparent 1px);
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
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }
  </style>"""

html = re.sub(r'<style>.*?</style>', light_theme_styles, html, flags=re.DOTALL)

# -------------------------------------------------------------
# 3. Clean light classes in Header & Sidebar
# -------------------------------------------------------------
# Replace dark panel bg classes
html = html.replace('bg-[#020b15]', 'bg-white')
html = html.replace('bg-[#031326]', 'bg-slate-50')
html = html.replace('bg-[#071d34]', 'bg-white')
html = html.replace('bg-[#08223f]', 'bg-slate-100')
html = html.replace('border-slate-800', 'border-slate-200')
html = html.replace('text-white', 'text-slate-900')

# Restore specific brand contrast where needed
html = html.replace('text-slate-900 leading-none">TARANG', 'text-slate-900 leading-none">TARANG')

# Fix Sidebar Navigation: Ensure Verification Queue is present
sidebar_nav_html = """        <nav class="flex flex-col gap-1" id="nav-item-list">
          <button type="button" onclick="switchView('dashboard')" data-view="dashboard" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wide transition-all bg-teal-600 text-white shadow-sm">
            <span class="material-symbols-outlined text-[20px]">dashboard</span>
            <span>Dashboard</span>
          </button>

          <button type="button" onclick="switchView('active-mission')" data-view="active-mission" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-teal-600">satellite_alt</span>
            <span>Active Mission</span>
          </button>

          <button type="button" onclick="switchView('new-survey')" data-view="new-survey" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-sky-600">add_circle</span>
            <span>New Survey</span>
          </button>

          <button type="button" onclick="switchView('surveys')" data-view="surveys" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-indigo-600">travel_explore</span>
            <span>Existing Surveys</span>
          </button>

          <button type="button" onclick="switchView('results')" data-view="results" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-sky-600">analytics</span>
            <span>Results</span>
          </button>

          <button type="button" onclick="switchView('verification-queue')" data-view="verification-queue" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-amber-600">verified</span>
            <span>Verification Queue</span>
          </button>

          <button type="button" onclick="switchView('reports')" data-view="reports" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-purple-600">description</span>
            <span>Reports</span>
          </button>

          <button type="button" onclick="switchView('notifications')" data-view="notifications" class="nav-btn flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-[20px] text-amber-500">notifications</span>
              <span>Notifications</span>
            </div>
            <span id="sidebar-unread-count" class="px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold">0</span>
          </button>

          <button type="button" onclick="switchView('documents')" data-view="documents" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-emerald-600">folder</span>
            <span>Documents</span>
          </button>

          <button type="button" onclick="switchView('settings')" data-view="settings" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-slate-500">settings</span>
            <span>Settings</span>
          </button>
        </nav>"""

html = re.sub(r'<nav class="flex flex-col gap-1" id="nav-item-list">.*?</nav>', sidebar_nav_html, html, flags=re.DOTALL)

# -------------------------------------------------------------
# 4. Remove Mission Readiness & Diagnostics and Marine Environmental Status
# -------------------------------------------------------------
html = re.sub(
    r'<!--\s*28\.\s*REORGANIZED OLD DASHBOARD COMPONENTS.*?<!--\s*24\.\s*Operator',
    '<!-- 24. Operator',
    html,
    flags=re.DOTALL
)

# Also check for direct markup if comment was absent
html = re.sub(
    r'<div class="marine-card[^>]*>.*?Mission Readiness &amp; Diagnostics.*?Marine Environmental Status.*?<\/div>\s*<\/div>\s*<\/div>',
    '',
    html,
    flags=re.DOTALL
)

# -------------------------------------------------------------
# 5. Connect Dashboard Verification Queue Preview
# -------------------------------------------------------------
html = html.replace(
    'onclick="switchView(\'reports\')"\n              class="text-xs font-mono font-bold text-teal-400 hover:underline"',
    'onclick="switchView(\'verification-queue\')"\n              class="text-xs font-mono font-bold text-teal-600 hover:text-teal-700 hover:underline flex items-center gap-1"'
)
html = html.replace('View Formal Reports &rarr;', 'Open Verification Queue &rarr;')

# -------------------------------------------------------------
# 6. Verification Queue Empty State
# -------------------------------------------------------------
html = re.sub(
    r'No detections in queue[^<]*',
    'No surveys awaiting verification.',
    html
)
html = html.replace(
    'No surveys currently pending or reviewed in verification queue.',
    'No surveys awaiting verification.'
)

# -------------------------------------------------------------
# 7. Unescape template literals in loadReportsView()
# -------------------------------------------------------------
html = html.replace(r'fetch(\`/api/v1/surveys/\${targetSurvey.survey_id}/detections\`)', "fetch(`/api/v1/surveys/${targetSurvey.survey_id}/detections`)")
html = html.replace(r'\${', '${')
html = html.replace(r'\`', '`')

# -------------------------------------------------------------
# 8. Remove any visible v3.4 or V3.4
# -------------------------------------------------------------
html = re.sub(r'[Vv]3\.4', '', html)

with open('operator-portal.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("operator-portal.html base update complete.")
