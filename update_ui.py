import os

with open('sonar-ai.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to extract the existing renderXtfResults block and replace it.
start_str = "    function renderXtfResults(data) {"
end_str = "    function renderResults(data) {"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx != -1 and end_idx != -1:
    new_render = """
    function renderXtfResults(data) {
        uploadZone.classList.add('hidden');
        resultVideo.classList.add('hidden');
        resultImage.classList.add('hidden');

        let oldContainer = document.getElementById('xtf-container');
        if (oldContainer) oldContainer.remove();

        const container = document.createElement('div');
        container.id = 'xtf-container';
        container.className = 'absolute inset-0 z-10 bg-[#020b15] flex flex-row overflow-hidden';
        
        // Metadata Sidebar
        const meta = data.metadata || {};
        const metaHtml = `
            <div class="w-72 bg-[#07192c] border-r border-teal-500/20 shadow-xl overflow-y-auto flex flex-col">
                <div class="p-4 border-b border-teal-500/20 bg-[#051322]">
                    <h3 class="text-seafoam-glow font-headline-sm font-bold">XTF SURVEY</h3>
                    <div class="text-[11px] text-slate-400 font-label-code mt-1">${meta.survey?.survey_id || 'Unknown'}</div>
                </div>
                
                <div class="p-4 flex flex-col gap-5">
                    <!-- FILE -->
                    <div>
                        <div class="text-[10px] text-teal-500 font-bold tracking-wider mb-2 uppercase">File</div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <span class="text-slate-400">Format:</span><span class="text-white font-medium text-right">${meta.file?.format || 'Unavailable'}</span>
                            <span class="text-slate-400">Size:</span><span class="text-white font-medium text-right">${meta.file?.file_size_bytes ? (meta.file.file_size_bytes/1024/1024).toFixed(2)+' MB' : 'Unavailable'}</span>
                        </div>
                    </div>
                    
                    <!-- SONAR -->
                    <div>
                        <div class="text-[10px] text-teal-500 font-bold tracking-wider mb-2 uppercase">Sonar System</div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <span class="text-slate-400">Type:</span><span class="text-white font-medium text-right">${meta.sonar?.type || 'Unavailable'}</span>
                            <span class="text-slate-400">Model:</span><span class="text-white font-medium text-right">${meta.sonar?.model || 'Unavailable'}</span>
                            <span class="text-slate-400">Channels:</span><span class="text-white font-medium text-right">${meta.summary?.channel_count || 'Unavailable'}</span>
                        </div>
                    </div>
                    
                    <!-- NAVIGATION -->
                    <div>
                        <div class="text-[10px] text-teal-500 font-bold tracking-wider mb-2 uppercase">Navigation</div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <span class="text-slate-400">Start Lat:</span><span class="text-white font-medium text-right">${meta.navigation?.start_latitude ?? 'Unavailable'}</span>
                            <span class="text-slate-400">Start Lon:</span><span class="text-white font-medium text-right">${meta.navigation?.start_longitude ?? 'Unavailable'}</span>
                        </div>
                    </div>
                    
                    <!-- PINGS -->
                    <div>
                        <div class="text-[10px] text-teal-500 font-bold tracking-wider mb-2 uppercase">Data Summary</div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <span class="text-slate-400">Total Pings:</span><span class="text-white font-medium text-right">${meta.summary?.total_pings || 'Unavailable'}</span>
                            <span class="text-slate-400">Samples/Ping:</span><span class="text-white font-medium text-right">${meta.summary?.samples_per_ping || 'Unavailable'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Viewer Area
        const viewerHtml = `
            <div class="flex-1 relative overflow-hidden bg-black flex flex-col">
                <!-- Toolbar -->
                <div class="h-12 bg-[#051322] border-b border-teal-500/20 flex items-center justify-between px-4 z-20">
                    <div class="text-sm font-bold text-white flex items-center gap-2">
                        <span class="material-symbols-outlined text-seafoam-glow text-lg">image_search</span> Full-Resolution Viewer
                    </div>
                    <div class="flex gap-2">
                        <button onclick="zoomXtf(0.2)" class="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700 text-xs font-bold">+ Zoom</button>
                        <button onclick="zoomXtf(-0.2)" class="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700 text-xs font-bold">- Zoom</button>
                        <button onclick="resetZoomXtf()" class="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700 text-xs font-bold">Fit Width</button>
                    </div>
                </div>
                <!-- Interactive Pan/Zoom Canvas -->
                <div id="xtf-pan-container" class="flex-1 overflow-auto relative flex justify-center bg-black cursor-grab active:cursor-grabbing p-4">
                    <div id="xtf-images-wrapper" class="flex flex-col gap-0 transition-transform origin-top"></div>
                </div>
            </div>
        `;
        
        container.innerHTML = metaHtml + viewerHtml;
        document.getElementById('media-viewport').appendChild(container);
        
        // Setup Pan/Zoom logic
        window.currentXtfZoom = 1.0;
        window.zoomXtf = function(delta) {
            window.currentXtfZoom = Math.max(0.1, window.currentXtfZoom + delta);
            document.getElementById('xtf-images-wrapper').style.transform = `scale(${window.currentXtfZoom})`;
        };
        window.resetZoomXtf = function() {
            window.currentXtfZoom = 1.0;
            document.getElementById('xtf-images-wrapper').style.transform = `scale(1.0)`;
        };
        
        // Fetch and append images
        fetch(`/api/v1/xtf/${data.survey_id}/images`)
            .then(res => res.json())
            .then(images => {
                const wrapper = document.getElementById('xtf-images-wrapper');
                images.forEach(img => {
                    const imgEl = document.createElement('img');
                    imgEl.src = `/api/v1/xtf/${data.survey_id}/images/${img.id}`;
                    // NO cropping CSS (object-cover, max-width, etc) - natural uncropped dimensions
                    imgEl.className = 'block max-w-none';
                    imgEl.style.width = '100%';
                    wrapper.appendChild(imgEl);
                });
            });

        currentDetections = data.detections || [];
        updateAnomalyCounts(currentDetections);
        renderAnomalyCards(currentDetections);
    }
"""
    content = content[:start_idx] + new_render + content[end_idx:]
    with open('sonar-ai.html', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("Could not find renderXtfResults block!")
