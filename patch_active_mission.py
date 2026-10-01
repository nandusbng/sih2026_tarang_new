import re

with open('operator-portal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace view-active-mission with the comprehensive 3D Drone & Telemetry & Map layout
active_mission_html = """      <!-- ===================================================================== -->
      <!-- VIEW 2: ACTIVE MISSION (3D Survey Simulation + Telemetry + Map)       -->
      <!-- ===================================================================== -->
      <div id="view-active-mission" class="view-panel hidden flex flex-col gap-6 max-w-7xl mx-auto">
        <!-- Top Bar with Mission Title and Simulation Control Buttons -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div class="flex items-center gap-3">
            <button type="button" onclick="switchView('dashboard')" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-teal-500 text-xs font-mono font-bold text-slate-700 hover:text-slate-900 transition-all shadow-sm shrink-0">
              <span class="material-symbols-outlined text-[16px]">arrow_back</span>
              <span>Back</span>
            </button>
            <div>
              <div class="flex items-center gap-2 text-xs font-mono text-teal-600 uppercase tracking-wider mb-0.5">
                <span class="inline-block w-2 h-2 rounded-full bg-teal-500 animate-ping"></span>
                Autonomous Marine Survey Platform
              </div>
              <h2 class="font-headline font-extrabold text-[26px] sm:text-[28px] text-slate-900 tracking-tight leading-tight" id="active-mission-title">
                Offshore Acoustic Survey Simulation
              </h2>
            </div>
          </div>
          <div class="flex items-center gap-2.5">
            <button type="button" id="btn-start-survey" onclick="startSurveySimulation()" class="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer">
              <span class="material-symbols-outlined text-[18px]">play_arrow</span>
              <span>Start Survey</span>
            </button>
            <button type="button" id="btn-stop-survey" onclick="stopSurveySimulation()" class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer">
              <span class="material-symbols-outlined text-[18px]">pause</span>
              <span>Stop Survey</span>
            </button>
            <button type="button" onclick="resetSurveySimulation()" class="px-3 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 font-mono text-xs font-bold transition-all cursor-pointer">
              <span class="material-symbols-outlined text-[18px]">replay</span>
            </button>
            <span class="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 font-mono text-[11px] font-bold">
              SIMULATION DATA
            </span>
          </div>
        </div>

        <!-- Main Row: Left 3D Viewport (8 cols) + Right Telemetry Panel (4 cols) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <!-- LEFT / MAIN: 3D Survey Platform Simulation -->
          <div class="lg:col-span-8 marine-card rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-teal-600 text-[20px]">view_in_ar</span>
                <h4 class="font-headline font-bold text-sm text-slate-900">3D Survey Platform Simulation (static/models/drone.glb)</h4>
              </div>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200" id="sim-status-pill">
                STANDBY
              </span>
            </div>
            <!-- 3D Canvas Container -->
            <div id="drone-3d-viewport" class="w-full h-[380px] rounded-xl bg-[#071e3d] relative overflow-hidden flex items-center justify-center">
              <div id="drone-loader-spinner" class="absolute z-10 flex flex-col items-center gap-2 text-white font-mono text-xs">
                <span class="material-symbols-outlined text-[32px] animate-spin text-teal-400">autorenew</span>
                <span>Initializing 3D Seabed &amp; Loading static/models/drone.glb...</span>
              </div>
            </div>
            <div class="flex items-center justify-between text-[11px] font-mono text-slate-500 mt-2 px-1">
              <span>Interactive Controls: Left-click rotate • Scroll zoom • Right-click pan</span>
              <span class="text-teal-600 font-bold" id="sim-waypoint-counter">Waypoint: 0 / 12</span>
            </div>
          </div>

          <!-- RIGHT / INFO: Mission Telemetry (SIMULATION DATA) -->
          <div class="lg:col-span-4 marine-card rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
                <div>
                  <h4 class="font-headline font-bold text-sm text-slate-900">Mission Telemetry</h4>
                  <p class="text-[11px] font-mono text-slate-400">Live platform sensor stream</p>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200">
                  SIMULATION DATA
                </span>
              </div>
              <div class="space-y-2 text-xs font-mono">
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Mission ID:</span>
                  <strong class="text-slate-900" id="telemetry-mission-id">MSN-2026-SRV-01</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Survey ID:</span>
                  <strong class="text-teal-700" id="telemetry-survey-id">TRG-SRV-001</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Latitude:</span>
                  <strong class="text-slate-900" id="telemetry-lat">13.0827°N</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Longitude:</span>
                  <strong class="text-slate-900" id="telemetry-lon">80.2707°E</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Platform Heading:</span>
                  <strong class="text-slate-900" id="telemetry-heading">045° NE</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Speed:</span>
                  <strong class="text-slate-900" id="telemetry-speed">3.4 knots</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Sonar Altitude:</span>
                  <strong class="text-teal-700" id="telemetry-altitude">8.2 m</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Water Depth:</span>
                  <strong class="text-sky-700" id="telemetry-depth">34.6 m</strong>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-100">
                  <span class="text-slate-500">Survey Distance:</span>
                  <strong class="text-slate-900" id="telemetry-distance">1.82 km</strong>
                </div>
                <div class="flex justify-between py-1">
                  <span class="text-slate-500">Coverage:</span>
                  <strong class="text-teal-700" id="telemetry-coverage">0.45 km²</strong>
                </div>
              </div>
            </div>

            <!-- Survey Progress Bar -->
            <div class="mt-4 pt-3 border-t border-slate-100">
              <div class="flex justify-between text-xs font-mono mb-1">
                <span class="text-slate-500">Mission Progress:</span>
                <strong class="text-teal-700" id="telemetry-progress-pct">0%</strong>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div id="telemetry-progress-bar" class="bg-teal-600 h-2 rounded-full transition-all duration-300" style="width: 0%;"></div>
              </div>
              <div class="flex justify-between text-[10px] font-mono text-slate-400 mt-2">
                <span>State: <strong class="text-slate-700" id="telemetry-state">STANDBY</strong></span>
                <span>Chirp: <strong>400/900 kHz</strong></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Lower Row: Active Mission Tactical Map (TarangMap Leaflet) -->
        <div class="marine-card rounded-2xl p-5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-teal-600 text-[20px]">map</span>
              <h4 class="font-headline font-bold text-sm text-slate-900">Survey Route &amp; Acoustic Targets Map</h4>
            </div>
            <div class="flex items-center gap-2 text-xs font-mono">
              <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Synchronized with 3D Platform Position
              </span>
            </div>
          </div>
          <div id="active-mission-map" class="w-full h-[360px] rounded-xl border border-slate-200 overflow-hidden relative"></div>
        </div>
      </div>"""

# Replace the whole view-active-mission block
pattern = r'<div id="view-active-mission".*?<\/div>\s*<\/div>\s*<!-- ===================================================================== -->\s*<!-- VIEW 3:'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + active_mission_html + '\n\n      <!-- ===================================================================== -->\n      <!-- VIEW 3:' + content[match.end():]
    print("view-active-mission replaced cleanly.")
else:
    print("Could not match view-active-mission via regex.")

with open('operator-portal.html', 'w', encoding='utf-8') as f:
    f.write(content)
