import os

dynamic_metadata_logic = """
        let metaGridHtml = '';
        if (data.metadata) {
            for (const [key, value] of Object.entries(data.metadata)) {
                metaGridHtml += `<div><span class="text-[10px] text-slate-400 font-label-code block uppercase">${key}</span><span class="font-bold text-sm break-all">${value}</span></div>`;
            }
        } else {
            // Fallback if metadata object is somehow missing
            metaGridHtml = `
                <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Survey ID</span><span class="font-bold text-sm break-all">${data.survey_id}</span></div>
                <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Total Pings</span><span class="font-bold text-sm break-all">${data.total_pings}</span></div>
                <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Channels</span><span class="font-bold text-sm break-all">${data.channels}</span></div>
            `;
        }
        
        const metadataHtml = `
            <div class="bg-[#07192c] p-4 rounded-xl border border-teal-500/20 shadow-md text-white">
                <h3 class="text-seafoam-glow font-headline-sm font-bold mb-3">XTF Survey Metadata</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    ${metaGridHtml}
                </div>
            </div>
        `;
"""

for filepath in ['sonar-ai.html', 'survey-operator.html']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    # Replace the existing static metadataHtml block
    pattern = re.compile(r'        const metadataHtml = `\n.*?        `;\n', re.DOTALL)
    content = pattern.sub(dynamic_metadata_logic, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

