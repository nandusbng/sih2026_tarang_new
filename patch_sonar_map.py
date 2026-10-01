import re

with open('sonar-analyst.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add "Spatial Map" to Sonar Analyst sidebar navigation
old_nav_btn = """      <button type="button" onclick="switchTab('detections')" data-tab="detections" class="analyst-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-300 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[20px] text-sky-400">category</span>
        <span>AI Detections</span>
      </button>"""

new_nav_btns = """      <button type="button" onclick="switchTab('detections')" data-tab="detections" class="analyst-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[20px] text-sky-600">category</span>
        <span>AI Detections</span>
      </button>

      <button type="button" onclick="switchTab('spatial-map')" data-tab="spatial-map" class="analyst-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[20px] text-teal-600">map</span>
        <span>Spatial Map &amp; Clusters</span>
      </button>"""

if old_nav_btn in html:
    html = html.replace(old_nav_btn, new_nav_btns)
else:
    html = re.sub(
        r'(<button[^>]*data-tab="detections"[^>]*>.*?<\/button>)',
        r'''\1\n      <button type="button" onclick="switchTab('spatial-map')" data-tab="spatial-map" class="analyst-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[20px] text-teal-600">map</span>
        <span>Spatial Map &amp; Clusters</span>
      </button>''',
        html,
        flags=re.DOTALL
    )

# 2. Add TAB: Spatial Map & Clusters HTML
spatial_map_tab = """    <!-- ===================================================================== -->
    <!-- TAB: SPATIAL MAP & CLUSTERS (Requirement 3: Sonar Analyst GIS)        -->
    <!-- ===================================================================== -->
    <div id="tab-spatial-map" class="analyst-view-panel hidden flex flex-col gap-6 max-w-7xl mx-auto">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div class="flex items-center gap-3">
          <button type="button" onclick="switchTab('overview')" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono font-bold text-slate-700 hover:text-slate-900 transition-all shadow-sm shrink-0">
            <span class="material-symbols-outlined text-[16px]">arrow_back</span>
            <span>Back</span>
          </button>
          <div>
            <h2 class="font-headline font-extrabold text-[28px] sm:text-[30px] text-slate-900 tracking-tight leading-tight">
              Spatial Detection &amp; Cluster Map
            </h2>
            <p class="font-body text-xs text-slate-500 mt-0.5">
              Inspect geographic detection positions, verification rings, and DBSCAN concentration clusters.
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 font-mono text-xs">
          <button type="button" onclick="loadAnalystSpatialMap()" class="px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 font-bold shadow-sm">
            <span class="material-symbols-outlined text-[16px]">refresh</span>
            <span>Refresh Map</span>
          </button>
        </div>
      </div>

      <div class="marine-card rounded-2xl p-5 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3 text-xs font-mono border-b border-slate-100 pb-3">
          <div class="flex items-center gap-4">
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-rose-600 inline-block"></span> Ghost Net</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-sky-600 inline-block"></span> Shipwreck</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-600 inline-block"></span> Crab Pot</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-teal-600 inline-block"></span> Pipeline/Cable</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full border-2 border-teal-600 inline-block"></span> Verified Target</span>
          </div>
          <span class="text-slate-500" id="analyst-map-stats-pill">0 Detections Plotted</span>
        </div>
        <div id="analyst-interactive-map" class="w-full h-[520px] rounded-xl border border-slate-200 overflow-hidden relative"></div>
      </div>
    </div>
"""

# Insert spatial map tab before tab-hotspots
html = html.replace('<div id="tab-hotspots"', spatial_map_tab + '\n    <div id="tab-hotspots"')

# 3. Update switchTab function and map loader in script
new_switch_snippet = """      if (tabKey === 'overview') loadOverviewData();
      else if (tabKey === 'detections') renderDetectionsGrid();
      else if (tabKey === 'spatial-map') loadAnalystSpatialMap();
      else if (tabKey === 'hotspots') loadHotspots();
      else if (tabKey === 'verification') loadVerificationCards();"""

html = html.replace(
    "if (tabKey === 'overview') loadOverviewData();\n      else if (tabKey === 'detections') renderDetectionsGrid();\n      else if (tabKey === 'hotspots') loadHotspots();\n      else if (tabKey === 'verification') loadVerificationCards();",
    new_switch_snippet
)

# 4. Add loadAnalystSpatialMap() implementation
map_js_code = """
    let analystTarangMap = null;

    function loadAnalystSpatialMap() {
      if (!analystTarangMap) {
        analystTarangMap = new TarangMap('analyst-interactive-map', {
          center: [13.0827, 80.2707],
          zoom: 12
        });
      }

      // Load detections
      fetch('/api/v1/surveys/all/detections')
        .then(r => r.json())
        .then(dets => {
          if (dets && dets.length > 0) {
            analystTarangMap.setDetections(dets, (d) => {
              openVerificationFor(d.id);
            });
            const pill = document.getElementById('analyst-map-stats-pill');
            if (pill) pill.textContent = `${dets.length} Targets Displayed`;
          }
        }).catch(err => console.error(err));

      // Load DBSCAN clusters
      fetch('/api/v1/clusters?eps_meters=600&min_samples=2')
        .then(r => r.json())
        .then(cData => {
          if (cData && cData.clusters && cData.clusters.length > 0) {
            analystTarangMap.setClusters(cData);
          }
        }).catch(err => console.error(err));
    }
"""

html = html.replace('function openVerificationFor(id) {', map_js_code + '\n    function openVerificationFor(id) {')

with open('sonar-analyst.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("sonar-analyst.html Spatial Map integration complete.")
