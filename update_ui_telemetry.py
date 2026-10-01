import os
import re

logic_to_insert = """
                let telemetryHtml = '';
                if (det.telemetry) {
                    telemetryHtml = `
                    <div class="mt-2 bg-surface-container/50 p-2 rounded border border-outline-variant/30 text-[9px] font-label-code text-on-surface">
                        <div class="text-secondary font-bold mb-1 uppercase tracking-wider flex items-center gap-1">
                            <span class="material-symbols-outlined text-[12px]">my_location</span>
                            Exact Telemetry
                        </div>
                        <div class="grid grid-cols-2 gap-y-1">
                            <div class="truncate"><span class="text-slate-500">LAT:</span> ${det.telemetry.Latitude || 'N/A'}</div>
                            <div class="truncate"><span class="text-slate-500">LON:</span> ${det.telemetry.Longitude || 'N/A'}</div>
                            <div class="truncate"><span class="text-slate-500">PING:</span> ${det.telemetry['Ping Number'] || 'N/A'}</div>
                            <div class="truncate"><span class="text-slate-500">HDG:</span> ${det.telemetry.Heading || 'N/A'}</div>
                            <div class="truncate"><span class="text-slate-500">DPTH:</span> ${det.telemetry.Depth || '0'}m</div>
                            <div class="truncate"><span class="text-slate-500">ALT:</span> ${det.telemetry.Altitude || '0'}m</div>
                        </div>
                    </div>
                    `;
                }
"""

for filepath in ['sonar-ai.html', 'survey-operator.html']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where `const timeTag` is defined and insert telemetryHtml logic
    if 'let telemetryHtml =' not in content:
        content = content.replace(
            "const timeTag = det.time_offset ? ` • ${det.time_offset}` : '';",
            "const timeTag = det.time_offset ? ` • ${det.time_offset}` : '';\n" + logic_to_insert
        )
        
        # Inject ${telemetryHtml} after the metadata grid
        old_material_block = """
                <!-- Metadata Grid -->
                <div class="bg-surface-ice p-2 rounded-lg font-label-code text-[10px]">
                    <span class="text-slate-500">MATERIAL:</span>
                    <div class="font-semibold text-primary truncate">${det.material}</div>
                </div>
"""
        new_material_block = old_material_block + "\n                ${telemetryHtml}\n"
        content = content.replace(old_material_block, new_material_block)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
