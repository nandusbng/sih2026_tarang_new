import os

with open('sonar-ai.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_str = "    function renderXtfResults(data) {"
end_str = "    function renderResults(data) {"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

old_render = """    function renderXtfResults(data) {
        uploadZone.classList.add('hidden');
        resultVideo.classList.add('hidden');
        resultImage.classList.add('hidden'); // We will create custom image elements

        // Clear previous custom xtf container if exists
        let oldContainer = document.getElementById('xtf-container');
        if (oldContainer) oldContainer.remove();

        const container = document.createElement('div');
        container.id = 'xtf-container';
        container.className = 'absolute inset-0 z-10 bg-[#020b15] overflow-y-auto p-4 flex flex-col gap-4';
        
        const metadataHtml = `
            <div class="bg-[#07192c] p-4 rounded-xl border border-teal-500/20 shadow-md text-white">
                <h3 class="text-seafoam-glow font-headline-sm font-bold mb-3">XTF Survey Metadata</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Survey ID</span><span class="font-bold text-sm">${data.survey_id}</span></div>
                    <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Total Pings</span><span class="font-bold text-sm">${data.total_pings}</span></div>
                    <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Channels</span><span class="font-bold text-sm">${data.channels}</span></div>
                    <div><span class="text-[10px] text-slate-400 font-label-code block uppercase">Images Reconstructed</span><span class="font-bold text-sm">${data.images_reconstructed}</span></div>
                </div>
            </div>
        `;
        
        const imagesHtml = `<div class="flex flex-col gap-4" id="xtf-images-wrapper"></div>`;
        
        container.innerHTML = metadataHtml + imagesHtml;
        document.getElementById('media-viewport').appendChild(container);
        
        // Fetch and append images
        fetch(`/api/v1/xtf/${data.survey_id}/images`)
            .then(res => res.json())
            .then(images => {
                const wrapper = document.getElementById('xtf-images-wrapper');
                images.forEach(img => {
                    const imgEl = document.createElement('img');
                    imgEl.src = `/api/v1/xtf/${data.survey_id}/images/${img.id}`;
                    imgEl.className = 'w-full rounded-lg border border-teal-500/20 object-contain';
                    wrapper.appendChild(imgEl);
                });
            });

        currentDetections = data.detections || [];
        updateAnomalyCounts(currentDetections);
        renderAnomalyCards(currentDetections);
    }
"""

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + old_render + content[end_idx:]
    with open('sonar-ai.html', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("Could not find renderXtfResults block!")
