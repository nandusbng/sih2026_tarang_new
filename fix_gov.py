import re

with open('gov-authority.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Clean up the sidebar navigation
pattern_sidebar = r'<button type="button" onclick="switchTab\(\'clearance-response\'\)" data-tab="clearance-response".*?<span>Clearance &amp; Response</span>\s*</button>'
clean_nav = """      <button type="button" onclick="switchTab('regional-intelligence')" data-tab="regional-intelligence" class="gov-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[18px] text-teal-600">article</span>
        <span>Regional Intelligence</span>
      </button>
      <button type="button" onclick="switchTab('clearance-response')" data-tab="clearance-response" class="gov-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
        <span class="material-symbols-outlined text-[18px] text-teal-600">task_alt</span>
        <span>Clearance &amp; Response</span>
      </button>"""

html = re.sub(pattern_sidebar, clean_nav, html, flags=re.DOTALL)

# 2. Add TarangMap & Leaflet script if missing
if 'tarang-map.js' not in html:
    html = html.replace('</head>', '  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />\n  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n  <script src="js/tarang-map.js"></script>\n</head>')

# 3. Add loadRegionalIntelligenceReport function
report_fn = """
    let govRegionalMap = null;

    async function loadRegionalIntelligenceReport() {
      // 1. Fetch live detections
      let detections = [];
      try {
        const res = await fetch('/api/v1/surveys/all/detections');
        if (res.ok) {
          const d = await res.json();
          detections = Array.isArray(d) ? d : (d.detections || []);
        }
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

      const totEl = document.getElementById('reg-total-detections');
      const verEl = document.getElementById('reg-verified-detections');
      if (totEl) totEl.textContent = total;
      if (verEl) verEl.textContent = verified;

      let netCount = 0, shipCount = 0, potCount = 0, pipeCount = 0, unknownCount = 0;
      detections.forEach(d => {
        const cls = (d.class_name || '').toLowerCase();
        if (cls.includes('net')) netCount++;
        else if (cls.includes('ship') || cls.includes('wreck')) shipCount++;
        else if (cls.includes('pot') || cls.includes('trap')) potCount++;
        else if (cls.includes('pipe') || cls.includes('cable')) pipeCount++;
        else unknownCount++;
      });

      const netEl = document.getElementById('reg-count-net');
      const shipEl = document.getElementById('reg-count-ship');
      const potEl = document.getElementById('reg-count-pot');
      const pipeEl = document.getElementById('reg-count-pipe');
      const unkEl = document.getElementById('reg-count-unknown');

      if (netEl) netEl.textContent = netCount;
      if (shipEl) shipEl.textContent = shipCount;
      if (potEl) potEl.textContent = potCount;
      if (pipeEl) pipeEl.textContent = pipeCount;
      if (unkEl) unkEl.textContent = unknownCount;

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
      setTimeout(() => {
        const mapContainer = document.getElementById('gov-regional-interactive-map');
        if (mapContainer && !govRegionalMap) {
          govRegionalMap = new TarangMap('gov-regional-interactive-map', {
            center: [13.0827, 80.2707],
            zoom: 12
          });
        }
        if (govRegionalMap) {
          govRegionalMap.map.invalidateSize();
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
      }, 100);
    }
"""

if 'function loadRegionalIntelligenceReport()' not in html:
    html = html.replace('function switchTab(tabId) {', report_fn + '\n    function switchTab(tabId) {\n      if (tabId === "regional-intelligence") { loadRegionalIntelligenceReport(); }')

with open('gov-authority.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("gov-authority.html fixed successfully!")
