import re
import os

filepath = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/dashboard.html"
html = open(filepath, 'r').read()

# First, let's inject custom CSS for the radar into the head
custom_css = """
<style>
/* Radar Scanlines */
.scanlines {
  background: linear-gradient(
    to bottom,
    rgba(255,255,255,0),
    rgba(255,255,255,0) 50%,
    rgba(0, 0, 0, 0.1) 50%,
    rgba(0, 0, 0, 0.1)
  );
  background-size: 100% 4px;
}
/* Enhanced Radar Sweep */
@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-radar-sweep {
  animation: radar-spin 4s linear infinite;
}
/* Pulse ring */
@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(2.5); opacity: 0; }
}
.animate-pulse-ring {
  animation: pulse-ring 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}
/* Glowing border */
.glow-border {
  box-shadow: 0 0 10px rgba(20, 184, 166, 0.5), inset 0 0 10px rgba(20, 184, 166, 0.2);
  border: 1px solid rgba(20, 184, 166, 0.5);
}
</style>
"""

if '<style>' in html:
    html = html.replace('<style>', custom_css.strip() + '\n<style>', 1)
else:
    html = html.replace('</head>', custom_css + '</head>')


# Redesign the radar block
# We will match the entire section id="drift-console"
radar_pattern = r'<section class="relative z-10 w-full px-margin md:px-gutter-desktop py-space-xl" id="drift-console">.*?</section>'
radar_match = re.search(radar_pattern, html, flags=re.DOTALL)

if radar_match:
    new_radar_html = """
<section class="relative z-10 w-full px-margin md:px-gutter-desktop py-space-xl" id="drift-console">
  <div class="w-full bg-[#031122] rounded-2xl shadow-2xl overflow-hidden border border-[#006398]/30">
    <!-- Console Header Bar -->
    <div class="flex flex-wrap items-center justify-between px-space-lg py-space-md bg-gradient-to-r from-[#031B33] to-[#0a2540] border-b border-[#14B8A6]/20 gap-space-md">
      <div class="flex items-center gap-space-md">
        <div class="flex items-center gap-space-sm bg-[#00101d] px-4 py-2 rounded-lg border border-[#14B8A6]/40 glow-border">
          <span class="inline-block w-2.5 h-2.5 rounded-full bg-[#14B8A6] animate-pulse"></span>
          <span class="font-telemetry-metric text-telemetry-sm font-bold text-[#14B8A6] uppercase tracking-widest">Live Radar Sweep</span>
        </div>
        <span class="hidden md:inline text-[#5bb8fe]/70 font-telemetry-md text-telemetry-md">SECTOR: ARABIAN SEA TO COROMANDEL | GRID: 14.5020° N, 85.1290° E</span>
      </div>
      <!-- Mode Selectors -->
      <div class="flex items-center gap-2">
        <button class="radar-mode-btn px-4 py-2 rounded font-label-code text-[11px] uppercase tracking-widest font-bold bg-[#14B8A6]/20 text-[#14B8A6] border border-[#14B8A6] shadow-[0_0_10px_rgba(20,184,166,0.2)] transition-all" type="button">
          Sentinel Optical
        </button>
        <button class="radar-mode-btn px-4 py-2 rounded font-label-code text-[11px] uppercase tracking-widest font-bold text-[#5bb8fe]/70 hover:text-[#5bb8fe] hover:bg-[#5bb8fe]/10 transition-all border border-transparent hover:border-[#5bb8fe]/30" type="button">
          SAR Radar
        </button>
        <button class="radar-mode-btn px-4 py-2 rounded font-label-code text-[11px] uppercase tracking-widest font-bold text-[#5bb8fe]/70 hover:text-[#5bb8fe] hover:bg-[#5bb8fe]/10 transition-all border border-transparent hover:border-[#5bb8fe]/30" type="button">
          AUV Sonar
        </button>
      </div>
    </div>
    
    <!-- Radar Canvas Area -->
    <div class="relative w-full h-[600px] bg-[#000a14] flex items-center justify-center overflow-hidden">
      <!-- Background Map (Stylized CSS pattern) -->
      <div class="absolute inset-0 opacity-[0.03]" style="background-image: radial-gradient(#5bb8fe 1px, transparent 1px); background-size: 30px 30px;"></div>
      
      <!-- CRT Scanlines -->
      <div class="absolute inset-0 scanlines opacity-30 pointer-events-none z-30"></div>
      
      <!-- Radar Grid Lines (SVG) -->
      <svg class="absolute inset-0 w-full h-full opacity-40 pointer-events-none z-10" xmlns="http://www.w3.org/2000/svg">
        <!-- Concentric circles -->
        <circle cx="50%" cy="50%" fill="none" r="100" stroke="#14B8A6" stroke-dasharray="2 4" stroke-width="1" opacity="0.5"></circle>
        <circle cx="50%" cy="50%" fill="none" r="200" stroke="#14B8A6" stroke-dasharray="2 4" stroke-width="1" opacity="0.4"></circle>
        <circle cx="50%" cy="50%" fill="none" r="300" stroke="#14B8A6" stroke-dasharray="4 8" stroke-width="1" opacity="0.3"></circle>
        <circle cx="50%" cy="50%" fill="none" r="400" stroke="#14B8A6" stroke-width="1" opacity="0.2"></circle>
        <circle cx="50%" cy="50%" fill="none" r="500" stroke="#14B8A6" stroke-width="2" opacity="0.1"></circle>
        <!-- Axis crosshairs -->
        <line opacity="0.3" stroke="#14B8A6" stroke-width="1" x1="50%" x2="50%" y1="0%" y2="100%"></line>
        <line opacity="0.3" stroke="#14B8A6" stroke-width="1" x1="0%" x2="100%" y1="50%" y2="50%"></line>
        
        <!-- Crosshair markers -->
        <path d="M 49.5% 10% L 50.5% 10%" stroke="#14B8A6" stroke-width="2"></path>
        <path d="M 49.5% 90% L 50.5% 90%" stroke="#14B8A6" stroke-width="2"></path>
        <path d="M 10% 49.5% L 10% 50.5%" stroke="#14B8A6" stroke-width="2"></path>
        <path d="M 90% 49.5% L 90% 50.5%" stroke="#14B8A6" stroke-width="2"></path>
      </svg>
      
      <!-- Dynamic Rotating Radar Sweep Line -->
      <div class="absolute w-[1000px] h-[1000px] rounded-full pointer-events-none origin-center animate-radar-sweep z-10" style="background: conic-gradient(from 0deg at 50% 50%, rgba(20, 184, 166, 0.5) 0deg, rgba(20, 184, 166, 0.05) 45deg, transparent 90deg, transparent 360deg);">
        <div class="absolute top-0 bottom-1/2 left-1/2 right-1/2 border-l-2 border-[#14B8A6] shadow-[0_0_15px_#14B8A6]"></div>
      </div>
      
      <!-- Corner Coordinates -->
      <div class="absolute top-4 right-6 text-right z-20 opacity-60">
        <span class="block font-telemetry-sm text-[10px] text-[#5bb8fe]">LAT: 13°04'57"N | LON: 80°15'14"E</span>
        <span class="block font-telemetry-sm text-[10px] text-[#14B8A6]">ARABIAN SEA / BAY OF BENGAL TRANSECT</span>
      </div>
      
      <!-- Target 1 -->
      <div class="absolute top-[28%] left-[40%] group z-40 cursor-pointer">
        <div class="relative flex items-center justify-center">
          <span class="absolute h-10 w-10 rounded-full border border-[#E11D48] animate-pulse-ring"></span>
          <div class="relative h-3 w-3 rounded-full bg-[#E11D48] shadow-[0_0_12px_#E11D48]"></div>
        </div>
        
        <!-- Terminal Style Popup -->
        <div class="absolute left-8 -top-12 w-64 bg-[#00101d]/90 backdrop-blur-md p-4 rounded border border-[#E11D48]/50 shadow-[0_0_20px_rgba(225,29,72,0.15)] pointer-events-none group-hover:pointer-events-auto transition-all transform opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0">
          <div class="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-[#E11D48]"></div>
          <div class="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-[#E11D48]"></div>
          <div class="flex items-center justify-between mb-2">
            <span class="font-telemetry-sm text-[10px] text-[#E11D48] font-bold tracking-widest">&gt; TRG-882</span>
            <span class="font-telemetry-sm text-[10px] bg-[#E11D48]/20 text-[#E11D48] px-1.5 py-0.5 rounded">96.2% CONF</span>
          </div>
          <p class="font-body-md text-[#f8f9ff] font-bold leading-tight mb-2 uppercase tracking-wide text-sm">Submerged Ghost Net</p>
          <div class="grid grid-cols-2 gap-y-2 text-[10px] font-telemetry-sm text-[#5bb8fe]">
            <span>MASS: 2.1 T</span>
            <span>DRIFT: 1.8kn SE</span>
            <span>SST: 28.4°C</span>
            <span class="text-[#E11D48]">RISK: CRITICAL</span>
          </div>
        </div>
      </div>
      
      <!-- Target 2 -->
      <div class="absolute bottom-[35%] right-[32%] group z-40 cursor-pointer">
        <div class="relative flex items-center justify-center">
          <span class="absolute h-12 w-12 rounded-full border border-[#D97706] animate-pulse-ring" style="animation-delay: 1s;"></span>
          <span class="absolute h-6 w-6 rounded-full border border-[#D97706]/50 animate-pulse-ring" style="animation-delay: 0.5s;"></span>
          <div class="relative h-4 w-4 rounded-full bg-[#D97706] shadow-[0_0_15px_#D97706]"></div>
        </div>
        
        <!-- Terminal Style Popup -->
        <div class="absolute right-10 -top-16 w-72 bg-[#00101d]/90 backdrop-blur-md p-4 rounded border border-[#D97706]/50 shadow-[0_0_20px_rgba(217,119,6,0.15)] pointer-events-none group-hover:pointer-events-auto transition-all transform opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0">
          <div class="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-[#D97706]"></div>
          <div class="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-[#D97706]"></div>
          <div class="flex items-center justify-between mb-2">
            <span class="font-telemetry-sm text-[10px] text-[#D97706] font-bold tracking-widest">&gt; CLUSTER-904</span>
            <span class="font-telemetry-sm text-[10px] bg-[#D97706]/20 text-[#D97706] px-1.5 py-0.5 rounded">89.4% CONF</span>
          </div>
          <p class="font-body-md text-[#f8f9ff] font-bold leading-tight mb-2 uppercase tracking-wide text-sm">Macroplastic Slick</p>
          <div class="grid grid-cols-2 gap-y-2 text-[10px] font-telemetry-sm text-[#5bb8fe]">
            <span>AREA: 480 m²</span>
            <span>HDG: 114°</span>
            <span>UNIT: Skimmer-02</span>
            <span class="text-[#14B8A6]">STAT: TRACKED</span>
          </div>
        </div>
      </div>
      
      <!-- Interceptor Ship marker -->
      <div class="absolute bottom-[20%] left-[30%] flex items-center gap-2 z-30">
        <div class="w-6 h-6 rounded bg-[#14B8A6] flex items-center justify-center shadow-[0_0_10px_#14B8A6]">
          <span class="material-symbols-outlined text-[#00101d] text-[16px]">directions_boat</span>
        </div>
        <span class="font-telemetry-sm text-[10px] text-[#14B8A6] tracking-widest font-bold">ICGS-VARUNA [12.4 kn]</span>
      </div>

    </div>
    
    <!-- Footer telemetry -->
    <div class="px-space-lg py-3 bg-[#031B33] border-t border-[#14B8A6]/20 flex items-center justify-between">
      <div class="flex items-center gap-4 font-telemetry-sm text-[10px] text-[#5bb8fe]/60 tracking-wider">
        <span class="flex items-center gap-1 text-[#14B8A6]"><span class="material-symbols-outlined text-[14px]">cell_tower</span> SENSOR SYNTHESIS:</span>
        <span>Sentinel-2 (MSI Band 8A & 12)</span>
        <span>•</span>
        <span>NovaSAR-1 S-Band</span>
        <span>•</span>
        <span>Edge Side-Scan Sonar Ping: 450 kHz</span>
      </div>
      <div class="font-telemetry-sm text-[10px] text-[#14B8A6] tracking-widest font-bold">
        LATENCY: 1.24s Edge
      </div>
    </div>
  </div>
</section>
"""
    
    html = html[:radar_match.start()] + new_radar_html + html[radar_match.end():]
    open(filepath, 'w').write(html)
    print("Radar completely redesigned with custom CSS animations and terminal UI styling.")
else:
    print("Could not find radar drift console in dashboard.html")

