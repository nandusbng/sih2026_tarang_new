import re

def main():
    with open('survey-operator.html', 'r') as f:
        html = f.read()

    # 1. Replace the <main> tag to add SPA views
    main_tag_regex = re.compile(r'<main[^>]*>')
    main_match = main_tag_regex.search(html)
    if not main_match:
        print("Could not find <main> tag")
        return

    spa_views_html = """
  <!-- VIEW: DASHBOARD -->
  <div id="view-dashboard" class="w-full max-w-7xl mx-auto flex flex-col gap-6 pt-4 animate-fade-in">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h2 class="text-3xl font-extrabold text-primary tracking-tight">Mission Control Dashboard</h2>
      <button onclick="switchView('view-create')" class="px-6 py-3 bg-seafoam-glow text-abyssal-navy font-bold rounded-xl shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2">
        <span class="material-symbols-outlined">add</span> Create New Mission
      </button>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="material-symbols-outlined text-secondary text-3xl">satellite_alt</span>
          <span class="px-2 py-0.5 rounded bg-surface-ice text-secondary font-label-code text-[10px] font-bold border border-border-subtle">NOMINAL</span>
        </div>
        <h3 class="font-bold text-lg text-primary mt-2">System Readiness</h3>
        <p class="text-on-surface-variant text-sm">All satellite links and ground stations connected.</p>
      </div>
      <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="material-symbols-outlined text-telemetry-amber text-3xl">thunderstorm</span>
          <span class="px-2 py-0.5 rounded bg-surface-ice text-telemetry-amber font-label-code text-[10px] font-bold border border-border-subtle">OPTIMAL</span>
        </div>
        <h3 class="font-bold text-lg text-primary mt-2">Weather Status</h3>
        <p class="text-on-surface-variant text-sm">Sea State 2. Clear skies. Safe for deployment.</p>
      </div>
      <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="material-symbols-outlined text-seafoam-glow text-3xl">memory</span>
          <span class="px-2 py-0.5 rounded bg-surface-ice text-seafoam-glow font-label-code text-[10px] font-bold border border-border-subtle">STANDBY</span>
        </div>
        <h3 class="font-bold text-lg text-primary mt-2">AI Inference</h3>
        <p class="text-on-surface-variant text-sm">ONNX Runtime WebGL active. YOLOv8 ready.</p>
      </div>
    </div>

    <!-- Active Missions Table Placeholder -->
    <div class="mt-4 p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-4">
      <h3 class="font-bold text-lg text-primary border-b border-border-subtle pb-3">Archived & Paused Surveys</h3>
      <div class="text-center py-8 text-on-surface-variant text-sm font-medium">
        <span class="material-symbols-outlined text-4xl mb-2 text-outline-variant">history</span><br>
        No archived missions found in local log.
      </div>
    </div>
  </div>

  <!-- VIEW: CREATE SURVEY -->
  <div id="view-create" class="hidden w-full max-w-4xl mx-auto flex-col gap-6 pt-4 animate-fade-in">
    <div class="flex items-center gap-4 border-b border-border-subtle pb-4">
      <button onclick="switchView('view-dashboard')" class="text-secondary hover:text-primary transition-colors">
        <span class="material-symbols-outlined text-3xl">arrow_back</span>
      </button>
      <h2 class="text-3xl font-extrabold text-primary tracking-tight">Mission Setup & Routing</h2>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-5">
        <div>
          <label class="font-bold text-sm text-primary mb-1.5 block">Mission Identifier</label>
          <input type="text" id="input-mission-id" value="SIH-2026-M409" class="w-full bg-surface-ice border border-border-subtle rounded-lg px-4 py-2.5 font-label-code focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-colors" />
        </div>
        <div>
          <label class="font-bold text-sm text-primary mb-1.5 block">Survey Grid Area</label>
          <select class="w-full bg-surface-ice border border-border-subtle rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-secondary">
            <option>Bay of Bengal Sector 7</option>
            <option>Arabian Sea EEZ</option>
            <option>Andaman & Nicobar Grid</option>
          </select>
        </div>
        <div>
          <label class="font-bold text-sm text-primary mb-1.5 block">Hardware Profile</label>
          <select class="w-full bg-surface-ice border border-border-subtle rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-secondary">
            <option>Edgetech 4125 Side Scan Sonar (400/900kHz)</option>
            <option>Klein 4900 (High Resolution)</option>
            <option>Kongsberg EM2040 Multibeam</option>
          </select>
        </div>
      </div>
      
      <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-4 justify-between">
        <div>
          <h3 class="font-bold text-lg text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">route</span> Routing Engine</h3>
          <p class="text-on-surface-variant text-sm mt-1 leading-relaxed">Select routing protocol for AUV autonomous pathing. AI mode uses TSP optimization to conserve battery.</p>
        </div>
        <div class="flex flex-col gap-3">
          <label class="flex items-center gap-3 p-3 border border-seafoam-glow bg-seafoam-glow/10 rounded-xl cursor-pointer hover:bg-seafoam-glow/20 transition-colors">
            <input type="radio" name="routing" checked class="text-seafoam-glow focus:ring-seafoam-glow h-5 w-5" />
            <div class="flex flex-col">
              <span class="font-bold text-primary">AI-Optimized TSP</span>
              <span class="text-xs text-on-surface-variant">Minimizes turning radius and battery drain.</span>
            </div>
          </label>
          <label class="flex items-center gap-3 p-3 border border-border-subtle rounded-xl cursor-pointer hover:bg-surface-ice transition-colors">
            <input type="radio" name="routing" class="text-secondary focus:ring-secondary h-5 w-5" />
            <div class="flex flex-col">
              <span class="font-bold text-primary">Manual Waypoints</span>
              <span class="text-xs text-on-surface-variant">Operator defines custom lawnmower pattern.</span>
            </div>
          </label>
        </div>
      </div>
    </div>
    
    <div class="flex justify-end mt-4">
      <button onclick="startPreCheck()" class="px-8 py-3.5 bg-primary text-on-primary font-bold rounded-xl shadow-lg hover:bg-primary-container transition-colors flex items-center gap-2">
        <span>Initiate Pre-Mission Check</span> <span class="material-symbols-outlined">arrow_forward</span>
      </button>
    </div>
  </div>

  <!-- VIEW: PRE-MISSION CHECK -->
  <div id="view-precheck" class="hidden w-full max-w-3xl mx-auto flex-col gap-6 pt-4 animate-fade-in">
    <div class="flex items-center gap-4 border-b border-border-subtle pb-4">
      <h2 class="text-3xl font-extrabold text-primary tracking-tight">Automated Pre-Flight Verification</h2>
    </div>
    
    <div class="p-8 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-5">
      <p class="text-sm text-on-surface-variant font-medium">Running system diagnostics and environment checks...</p>
      <div id="check-list" class="flex flex-col gap-3">
        <!-- populated by JS -->
      </div>
      <div id="check-progress-container" class="w-full bg-surface-container-highest rounded-full h-2.5 mt-2 hidden overflow-hidden">
        <div id="check-progress-bar" class="bg-seafoam-glow h-2.5 rounded-full transition-all duration-300" style="width: 0%"></div>
      </div>
    </div>
    
    <div class="flex justify-between items-center mt-4">
      <button onclick="switchView('view-create')" class="text-on-surface-variant font-bold text-sm hover:text-primary transition-colors">Cancel</button>
      <button id="btn-launch-mission" onclick="launchMission()" disabled class="px-8 py-3.5 bg-slate-200 text-slate-400 font-bold rounded-xl flex items-center gap-2 transition-all shadow-none">
        <span class="material-symbols-outlined">rocket_launch</span> <span>Launch Mission</span>
      </button>
    </div>
  </div>

  <!-- VIEW: RESULTS -->
  <div id="view-results" class="hidden w-full max-w-5xl mx-auto flex-col gap-6 pt-4 animate-fade-in">
    <div class="flex items-center justify-between border-b border-border-subtle pb-4">
      <h2 class="text-3xl font-extrabold text-primary tracking-tight">Post-Mission Report</h2>
      <button onclick="switchView('view-dashboard')" class="px-6 py-2.5 bg-surface-container-low text-primary font-bold rounded-lg border border-border-subtle hover:bg-surface-container-highest transition-colors shadow-sm">
        Return to Dashboard
      </button>
    </div>
    <div class="p-6 rounded-2xl bg-surface-container-lowest border border-border-subtle shadow-sm flex flex-col gap-4 text-center items-center py-16">
      <span class="material-symbols-outlined text-[72px] text-seafoam-glow mb-2">task_alt</span>
      <h3 class="text-3xl font-extrabold text-primary tracking-tight">Mission Completed Successfully</h3>
      <p class="text-on-surface-variant max-w-md text-lg leading-relaxed mt-2">Survey logs, AI detections, and routing telemetry have been archived to the Supabase datastore.</p>
    </div>
  </div>

  <!-- VIEW: LIVE MISSION (Wraps Existing UI) -->
  <div id="view-live" class="hidden w-full h-full flex-col lg:grid grid-cols-1 lg:grid-cols-12 gap-3 md:gap-4 animate-fade-in">
"""
    # Create the new <main> start tag
    new_main_start = '<main class="flex-1 w-full p-2 md:p-3 lg:p-4 overflow-y-auto min-h-0 relative">\n'
    
    # Replace the `<main ...>` line
    html = html[:main_match.start()] + new_main_start + spa_views_html + html[main_match.end():]

    # Find the closing </main> tag to close `#view-live`
    end_main_match = re.search(r'</main>', html)
    if end_main_match:
        html = html[:end_main_match.start()] + '  </div>\n</main>' + html[end_main_match.end():]

    # Add the "End Mission" button to the existing minimal status header (or anywhere visible)
    # The header has `<div class="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-ice ...">`
    end_btn_html = """
<button id="end-mission-btn" onclick="endMission()" class="hidden items-center gap-1.5 px-4 py-1.5 rounded-lg bg-sonar-alert hover:bg-red-600 text-white font-bold text-[12px] transition-colors shadow-md ml-4">
  <span class="material-symbols-outlined text-[16px]">power_settings_new</span> END MISSION
</button>
"""
    # Insert it right before </div>\n</header>
    header_end_idx = html.find('</header>')
    if header_end_idx != -1:
        # Find the div closing right before </header>
        last_div_idx = html.rfind('</div>', 0, header_end_idx)
        if last_div_idx != -1:
            html = html[:last_div_idx] + end_btn_html + html[last_div_idx:]

    # Add SPA JavaScript logic before the final </body>
    spa_js = """
<script>
// SPA State Management
window.switchView = function(viewId) {
    const views = ['view-dashboard', 'view-create', 'view-precheck', 'view-live', 'view-results'];
    views.forEach(v => {
        const el = document.getElementById(v);
        if (el) {
            el.classList.add('hidden');
            el.classList.remove('flex');
            // specifically for view-live
            if (v === 'view-live') el.classList.remove('lg:grid');
        }
    });
    
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.remove('hidden');
        if (viewId === 'view-live') {
            target.classList.add('flex', 'lg:grid'); 
        } else {
            target.classList.add('flex');
        }
    }

    // Toggle end mission button visibility
    const endBtn = document.getElementById('end-mission-btn');
    if (endBtn) {
        if (viewId === 'view-live') {
            endBtn.classList.remove('hidden');
            endBtn.classList.add('flex');
        } else {
            endBtn.classList.add('hidden');
            endBtn.classList.remove('flex');
        }
    }
};

window.startPreCheck = async function() {
    window.switchView('view-precheck');
    const checks = [
        { name: 'Sonar Acoustic Calibration', status: 'OK', icon: 'settings_input_antenna', delay: 800 },
        { name: 'AUV Battery Cell Integrity', status: '98%', icon: 'battery_full', delay: 600 },
        { name: 'GPS / GLONASS Uplink', status: 'LOCKED', icon: 'satellite_alt', delay: 1000 },
        { name: 'Exclusion Zone Geofencing', status: 'CLEAR', icon: 'gavel', delay: 700 }
    ];
    
    const container = document.getElementById('check-list');
    container.innerHTML = '';
    const progressContainer = document.getElementById('check-progress-container');
    const progressBar = document.getElementById('check-progress-bar');
    progressContainer.classList.remove('hidden');
    progressBar.style.width = '0%';
    
    // Disable launch button initially
    const btn = document.getElementById('btn-launch-mission');
    btn.disabled = true;
    btn.className = "px-8 py-3.5 bg-slate-200 text-slate-400 font-bold rounded-xl flex items-center gap-2 transition-all shadow-none";
    
    // Save draft state
    await saveMissionState('DRAFT');
    
    let totalDelay = 0;
    checks.forEach((c, idx) => {
        totalDelay += c.delay;
        setTimeout(() => {
            container.innerHTML += `
            <div class="flex items-center justify-between p-4 bg-surface-ice rounded-xl border border-border-subtle shadow-sm animate-fade-in transition-all">
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-secondary text-2xl">${c.icon}</span>
                    <span class="font-bold text-primary">${c.name}</span>
                </div>
                <div class="px-3 py-1 bg-seafoam-glow/20 text-on-tertiary-fixed-variant font-label-code text-[11px] rounded-full font-bold flex items-center gap-1 shadow-inner">
                    <span class="material-symbols-outlined text-[14px]">check_circle</span> ${c.status}
                </div>
            </div>`;
            progressBar.style.width = ((idx + 1) / checks.length * 100) + '%';
            
            if (idx === checks.length - 1) {
                btn.disabled = false;
                btn.className = "px-8 py-3.5 bg-seafoam-glow text-abyssal-navy font-bold rounded-xl shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2 cursor-pointer";
            }
        }, totalDelay);
    });
};

window.launchMission = async function() {
    await saveMissionState('ACTIVE');
    window.switchView('view-live');
    
    // Auto-trigger the "Select Image/Video" button to hint to the user what to do next
    // setTimeout(() => {
    //     const uploadZone = document.getElementById('upload-zone');
    //     if (uploadZone && !uploadZone.classList.contains('hidden')) {
    //         document.getElementById('btn-browse-main')?.classList.add('ring-4', 'ring-seafoam-glow', 'animate-pulse');
    //     }
    // }, 1000);
};

window.endMission = async function() {
    if (confirm("Are you sure you want to end this active mission? All logs will be archived.")) {
        await saveMissionState('COMPLETED');
        window.switchView('view-results');
    }
};

async function saveMissionState(state) {
    if (typeof window.supabaseClient === 'undefined') {
        console.warn('Supabase client not found, skipping saveMissionState');
        return;
    }
    const missionName = document.getElementById('input-mission-id') ? document.getElementById('input-mission-id').value : 'SIH-2026-M409';
    const payload = {
        type: 'mission_state',
        destination: 'GLOBAL_LOGGER',
        state: state,
        name: missionName,
        timestamp: new Date().toISOString()
    };
    try {
        await window.supabaseClient.from('dispatches').insert([{ payload: payload }]);
        console.log('Mission state logged to Supabase:', state);
    } catch (e) {
        console.error('Failed to log mission state:', e);
    }
}

// Add CSS animation for SPA view transitions
document.head.insertAdjacentHTML('beforeend', `
<style>
.animate-fade-in {
    animation: fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
`);
</script>
"""
    body_end_idx = html.rfind('</body>')
    if body_end_idx != -1:
        html = html[:body_end_idx] + spa_js + html[body_end_idx:]

    with open('survey-operator.html', 'w') as f:
        f.write(html)
        print("Updated survey-operator.html successfully")

if __name__ == '__main__':
    main()
