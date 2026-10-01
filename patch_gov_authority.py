import re

with open('gov-authority.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Include Leaflet & TarangMap in head if missing
head_includes = """  <!-- Leaflet & TARANG Shared Map -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="js/tarang-map.js"></script>"""

if 'tarang-map.js' not in html:
    html = html.replace('<!-- Tailwind CSS via CDN -->', head_includes + '\n  <!-- Tailwind CSS via CDN -->')

# 2. Light Theme CSS
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

# 3. Clean light classes
html = html.replace('bg-[#020b15]', 'bg-white')
html = html.replace('bg-[#031326]', 'bg-slate-50')
html = html.replace('bg-[#041324]', 'bg-white')
html = html.replace('bg-[#071d34]', 'bg-white')
html = html.replace('bg-[#08223f]', 'bg-slate-100')
html = html.replace('border-slate-800', 'border-slate-200')
html = html.replace('text-white', 'text-slate-900')

# 4. Remove any visible v3.4
html = re.sub(r'[Vv]3\.4', '', html)

# 5. Add "Regional Intelligence" to left sidebar
sidebar_btn = """      <button type="button" onclick="switchTab('regional-intelligence')" data-tab="regional-intelligence" class="gov-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[18px] text-teal-600">article</span>
        <span>Regional Intelligence</span>
      </button>"""

if 'data-tab="regional-intelligence"' not in html:
    html = html.replace('data-tab="clearance-response"', 'data-tab="clearance-response"\n' + sidebar_btn)

# 6. Add Section: Regional Marine Intelligence Report HTML
regional_report_html = """    <!-- ===================================================================== -->
    <!-- TAB: REGIONAL MARINE INTELLIGENCE REPORT                              -->
    <!-- ===================================================================== -->
    <div id="tab-regional-intelligence" class="gov-view-panel hidden flex flex-col gap-6 max-w-7xl mx-auto">
      <!-- Title Strip -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div class="flex items-center gap-2 text-xs font-mono text-teal-700 uppercase tracking-wider mb-1">
            <span class="w-2 h-2 rounded-full bg-teal-600"></span>
            Ministry of Earth Sciences (MoES) &bull; NIOT Marine Observatory
          </div>
          <h1 class="font-headline font-extrabold text-[28px] sm:text-[32px] text-slate-900 tracking-tight leading-tight">
            Regional Marine Intelligence Report
          </h1>
          <p class="text-xs sm:text-sm text-slate-500 font-mono mt-1">
            Structured analysis of acoustic detections, verified seabed anomalies, and DBSCAN concentration clusters.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <a href="/api/v1/export/clusters/json" download class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-teal-600 text-white font-mono font-bold text-xs shadow-sm hover:bg-teal-700 transition-all">
            <span class="material-symbols-outlined text-[16px]">download</span>
            <span>Cluster Dataset (JSON)</span>
          </a>
        </div>
      </div>

      <!-- 1. Executive Summary -->
      <div class="marine-card p-6 rounded-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 class="font-headline font-bold text-lg text-slate-900 flex items-center gap-2">
            <span class="material-symbols-outlined text-teal-600">summarize</span>
            Executive Summary
          </h2>
          <span class="px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 text-xs font-mono font-bold" id="reg-report-status">
            DATA-DRIVEN REPORT
          </span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-slate-400 block text-[10px]">MONITORED REGION</span>
            <strong class="text-slate-900 text-sm" id="reg-region-name">Offshore Bay of Bengal</strong>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-slate-400 block text-[10px]">SURVEY COVERAGE</span>
            <strong class="text-teal-700 text-sm" id="reg-coverage-area">4.85 km²</strong>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-slate-400 block text-[10px]">TOTAL AI DETECTIONS</span>
            <strong class="text-slate-900 text-sm" id="reg-total-detections">0</strong>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-slate-400 block text-[10px]">ANALYST VERIFIED</span>
            <strong class="text-teal-700 text-sm" id="reg-verified-detections">0</strong>
          </div>
        </div>
        <p class="text-xs text-slate-600 leading-relaxed font-body" id="reg-exec-summary-text">
          This intelligence briefing provides verified spatial assessments based on autonomous underwater vehicle side-scan sonar hydrography. AI inferences produced by the TARANG Detection Engine are cataloged and subject to expert human verification prior to clearance dispatch.
        </p>
      </div>

      <!-- 2. Interactive Regional Map with DBSCAN Clusters -->
      <div class="marine-card p-6 rounded-2xl space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h2 class="font-headline font-bold text-lg text-slate-900 flex items-center gap-2">
              <span class="material-symbols-outlined text-teal-600">map</span>
              Interactive Regional Map &amp; Spatial Clusters
            </h2>
            <p class="text-xs text-slate-500 font-mono">Survey tracks, individual detections, and DBSCAN concentration boundaries</p>
          </div>
          <div class="flex items-center gap-3 text-xs font-mono">
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-teal-600 inline-block"></span> Verified</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> AI Detected</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-sky-600 inline-block"></span> Cluster Extent</span>
          </div>
        </div>
        <div id="gov-regional-interactive-map" class="w-full h-[460px] rounded-xl border border-slate-200 overflow-hidden relative"></div>
      </div>

      <!-- 3. Findings, Target Distribution & Spatial Clustering Explanation -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Target Distribution -->
        <div class="marine-card p-6 rounded-2xl space-y-4">
          <h3 class="font-headline font-bold text-base text-slate-900 flex items-center gap-2">
            <span class="material-symbols-outlined text-teal-600">donut_large</span>
            Detected Target Classification Distribution
          </h3>
          <p class="text-xs text-slate-500 font-body">Categorization derived from the YOLO best.pt acoustic model pipeline.</p>
          <div class="space-y-2.5 text-xs font-mono" id="reg-category-breakdown">
            <div class="flex justify-between items-center p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-rose-600"></span> Ghost Drift Net</span>
              <strong class="text-slate-900" id="reg-count-net">0</strong>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-sky-600"></span> Shipwreck / Vessel Structure</span>
              <strong class="text-slate-900" id="reg-count-ship">0</strong>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-amber-600"></span> Derelict Trap / Crab Pot</span>
              <strong class="text-slate-900" id="reg-count-pot">0</strong>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-teal-600"></span> Submarine Pipeline / Cable</span>
              <strong class="text-slate-900" id="reg-count-pipe">0</strong>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-purple-600"></span> Other / Unknown Anomaly</span>
              <strong class="text-slate-900" id="reg-count-unknown">0</strong>
            </div>
          </div>
        </div>

        <!-- Spatial Clustering Explanation -->
        <div class="marine-card p-6 rounded-2xl space-y-4">
          <h3 class="font-headline font-bold text-base text-slate-900 flex items-center gap-2">
            <span class="material-symbols-outlined text-teal-600">grain</span>
            DBSCAN Spatial Clustering Analysis
          </h3>
          <div class="p-3.5 rounded-xl bg-teal-50 border border-teal-200 text-xs text-teal-900 font-mono leading-relaxed">
            <strong>Geospatial Principle:</strong> Spatial clustering groups geographically close detections to help analysts identify areas where multiple anomalies occur within a defined distance. A cluster does NOT necessarily mean one physical object; it indicates spatial concentration.
          </div>
          <div class="space-y-2 text-xs font-mono" id="reg-cluster-list">
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center text-slate-400">
              Loading DBSCAN cluster distribution...
            </div>
          </div>
        </div>
      </div>

      <!-- 4. Methodology & Intelligence Downloads -->
      <div class="marine-card p-6 rounded-2xl space-y-4">
        <h3 class="font-headline font-bold text-base text-slate-900 flex items-center gap-2">
          <span class="material-symbols-outlined text-teal-600">download</span>
          Official Intelligence Downloads
        </h3>
        <p class="text-xs text-slate-500 font-body">Download authentic hydrographic records and spatial datasets for regional planning.</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <a href="/api/v1/export/clusters/json" download class="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-teal-500 flex flex-col justify-between gap-3 transition-all">
            <div>
              <span class="material-symbols-outlined text-teal-600 text-[24px]">grain</span>
              <h4 class="font-bold text-slate-900 mt-1">DBSCAN Clusters</h4>
              <p class="text-[11px] text-slate-500">Spatial cluster boundaries &amp; centroids</p>
            </div>
            <span class="text-teal-700 font-bold flex items-center gap-1">Download JSON &rarr;</span>
          </a>

          <a href="/api/v1/export/survey/TRG-SRV-001/csv" download class="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-teal-500 flex flex-col justify-between gap-3 transition-all">
            <div>
              <span class="material-symbols-outlined text-sky-600 text-[24px]">table_chart</span>
              <h4 class="font-bold text-slate-900 mt-1">Detections Dataset</h4>
              <p class="text-[11px] text-slate-500">Coordinates, classes, and confidence</p>
            </div>
            <span class="text-sky-700 font-bold flex items-center gap-1">Download CSV &rarr;</span>
          </a>

          <a href="/api/v1/export/survey/TRG-SRV-001/geojson" download class="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-teal-500 flex flex-col justify-between gap-3 transition-all">
            <div>
              <span class="material-symbols-outlined text-indigo-600 text-[24px]">public</span>
              <h4 class="font-bold text-slate-900 mt-1">Spatial GeoJSON</h4>
              <p class="text-[11px] text-slate-500">GIS layer format with attributes</p>
            </div>
            <span class="text-indigo-700 font-bold flex items-center gap-1">Download GeoJSON &rarr;</span>
          </a>

          <a href="/api/v1/export/survey/TRG-SRV-001/metadata-txt" download class="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-teal-500 flex flex-col justify-between gap-3 transition-all">
            <div>
              <span class="material-symbols-outlined text-purple-600 text-[24px]">description</span>
              <h4 class="font-bold text-slate-900 mt-1">Survey Metadata TXT</h4>
              <p class="text-[11px] text-slate-500">Hydrographic parameters &amp; ping logs</p>
            </div>
            <span class="text-purple-700 font-bold flex items-center gap-1">Download TXT &rarr;</span>
          </a>
        </div>
      </div>
    </div>
"""

# Insert regional intelligence tab right after tab-overview
html = html.replace('<div id="tab-hotspots"', regional_report_html + '\n    <div id="tab-hotspots"')

# 7. Add JavaScript for Regional Intelligence Report
gov_js_enhancement = """
    let govRegionalMap = null;

    async function loadRegionalIntelligenceReport() {
      // 1. Fetch live detections
      let detections = [];
      try {
        const res = await fetch('/api/v1/surveys/all/detections');
        if (res.ok) detections = await res.json();
      } catch (e) {}

      // 2. Fetch clusters
      let clustersData = { clusters: [], noise: [] };
      try {
        const cRes = await fetch('/api/v1/clusters?eps_meters=500&min_samples=2');
        if (cRes.ok) clustersData = await cRes.json();
      } catch (e) {}

      // Update counts
      const total = detections.length;
      const verified = detections.filter(d => (d.verification_status || '').toLowerCase() === 'verified').length;

      document.getElementById('reg-total-detections').textContent = total;
      document.getElementById('reg-verified-detections').textContent = verified;

      let netCount = 0, shipCount = 0, potCount = 0, pipeCount = 0, unknownCount = 0;
      detections.forEach(d => {
        const cls = (d.class_name || '').toLowerCase();
        if (cls.includes('net')) netCount++;
        else if (cls.includes('ship') || cls.includes('wreck')) shipCount++;
        else if (cls.includes('pot') || cls.includes('trap')) potCount++;
        else if (cls.includes('pipe') || cls.includes('cable')) pipeCount++;
        else unknownCount++;
      });

      document.getElementById('reg-count-net').textContent = netCount;
      document.getElementById('reg-count-ship').textContent = shipCount;
      document.getElementById('reg-count-pot').textContent = potCount;
      document.getElementById('reg-count-pipe').textContent = pipeCount;
      document.getElementById('reg-count-unknown').textContent = unknownCount;

      // Render Cluster List
      const clusterListEl = document.getElementById('reg-cluster-list');
      if (clusterListEl) {
        if (!clustersData.clusters || clustersData.clusters.length === 0) {
          clusterListEl.innerHTML = '<div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center text-slate-400 font-mono text-xs">No spatial clusters detected with current sample density.</div>';
        } else {
          clusterListEl.innerHTML = clustersData.clusters.map(c => `
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <span class="font-bold text-slate-900">${c.cluster_id}</span>
                <span class="text-slate-500 text-[10px] block">${c.count} detections &bull; Dominant: <strong class="text-teal-700">${c.dominant_class}</strong></span>
              </div>
              <span class="px-2 py-0.5 rounded bg-teal-100 text-teal-800 text-[10px] font-bold">
                ${c.verified_count} Verified
              </span>
            </div>
          `).join('') + `
            <div class="p-2 text-right text-[11px] text-slate-400">
              Noise / Isolated Detections: <strong>${clustersData.noise ? clustersData.noise.length : 0}</strong>
            </div>
          `;
        }
      }

      // Initialize / Update Regional Map
      if (!govRegionalMap) {
        govRegionalMap = new TarangMap('gov-regional-interactive-map', {
          center: [13.0827, 80.2707],
          zoom: 12
        });
      }

      // Track coordinates (Bay of Bengal survey track)
      const trackPoints = [
        [13.0827, 80.2707], [13.0855, 80.2735], [13.0880, 80.2760],
        [13.0882, 80.2800], [13.0850, 80.2830], [13.0815, 80.2832],
        [13.0780, 80.2800], [13.0782, 80.2750]
      ];
      govRegionalMap.setTrack(trackPoints);

      if (detections.length > 0) {
        govRegionalMap.setDetections(detections);
      }
      if (clustersData.clusters && clustersData.clusters.length > 0) {
        govRegionalMap.setClusters(clustersData);
      }
    }
"""

html = html.replace('function switchTab(tabKey) {', gov_js_enhancement + '\n    function switchTab(tabKey) {')
html = html.replace("if (tabKey === 'overview') {", "if (tabKey === 'regional-intelligence') {\n        loadRegionalIntelligenceReport();\n      } else if (tabKey === 'overview') {")

with open('gov-authority.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("gov-authority.html Regional Intelligence Report integration complete.")
