import re

with open('sonar-ai.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Main Viewport HTML
# Replace lines from <!-- Waterfall Sonar Feed Canvas / Render Simulation --> to end of the viewport
old_viewport_pattern = r'<!-- Waterfall Sonar Feed Canvas / Render Simulation -->[\s\S]*?<!-- Maritime Playback Scrubber & Navigation Control Console -->'

new_viewport = '''<!-- Waterfall Sonar Feed Canvas / Interactive Media Viewport -->
        <input type="file" id="file-input" accept="image/*,video/*" class="hidden" />
        
        <div id="sonar-canvas-container" class="relative w-full aspect-[16/10] bg-abyssal-navy overflow-hidden group flex items-center justify-center">
          
          <!-- Scanlines & Nadir Grid Overlay -->
          <div class="absolute inset-0 bg-gradient-to-b from-transparent via-seafoam-glow/5 to-transparent pointer-events-none opacity-40 z-10"></div>
          <div class="absolute top-0 bottom-0 left-1/2 w-0.5 bg-secondary/40 pointer-events-none z-10">
            <div class="absolute top-0 bottom-0 -left-6 right-0 w-12 bg-gradient-to-r from-transparent via-primary/80 to-transparent"></div>
          </div>
          <div class="absolute left-3 top-1/2 -translate-y-1/2 font-label-code text-[10px] text-surface-variant/40 [writing-mode:vertical-rl] tracking-widest pointer-events-none select-none z-10">
            PORT CHANNEL (L-SWATH 75M)
          </div>
          <div class="absolute right-3 top-1/2 -translate-y-1/2 font-label-code text-[10px] text-surface-variant/40 [writing-mode:vertical-rl] tracking-widest pointer-events-none select-none z-10">
            STARBOARD CHANNEL (R-SWATH 75M)
          </div>

          <!-- Loading & Inference State -->
          <div id="loading-overlay" class="hidden absolute inset-0 z-30 bg-abyssal-navy/90 backdrop-blur-md flex flex-col items-center justify-center text-center p-6">
            <div class="relative w-20 h-20 mb-4 flex items-center justify-center">
              <div class="absolute inset-0 rounded-full border-2 border-seafoam-glow/20 animate-ping"></div>
              <div class="w-16 h-16 rounded-full border-2 border-t-seafoam-glow border-r-transparent border-b-secondary border-l-transparent animate-spin"></div>
              <span class="material-symbols-outlined text-seafoam-glow text-[28px] absolute">radar</span>
            </div>
            <h3 class="font-headline-sm text-[18px] text-surface-container-lowest font-bold">Neural Model Running (best.pt)</h3>
            <p id="loading-status-text" class="font-label-code text-[12px] text-surface-container-high mt-1 max-w-sm">
              Processing sonar acoustic frames, calculating object coordinates, and extracting detection screenshots...
            </p>
          </div>

          <!-- Active Media Render: Image -->
          <img id="result-image" class="hidden w-full h-full object-contain bg-black select-none z-0" alt="Detected Sonar Feed" />
          
          <!-- Active Media Render: Video -->
          <video id="result-video" class="hidden w-full h-full object-contain bg-black z-0" controls autoplay loop playsinline></video>

          <!-- Upload Dropzone (Shown when no media is loaded) -->
          <div id="upload-zone" class="z-20 w-full h-full flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all hover:bg-surface-ice/5" style="background-image: radial-gradient(rgba(20, 184, 166, 0.15) 1px, transparent 1px); background-size: 20px 20px;">
            <div class="w-16 h-16 rounded-2xl bg-secondary/20 border border-secondary/40 flex items-center justify-center mb-3 text-seafoam-glow shadow-[0_0_20px_rgba(20,184,166,0.25)] transition-transform group-hover:scale-110">
              <span class="material-symbols-outlined text-[36px]">cloud_upload</span>
            </div>
            <h3 class="font-headline-sm text-[18px] text-surface-container-lowest font-bold">
              Upload Sonar Image or Video
            </h3>
            <p class="font-body-sm text-body-sm text-surface-container-high max-w-md mt-1">
              Drag & drop or click to upload acoustic imagery or video. The <strong class="text-seafoam-glow font-label-code">best.pt</strong> YOLO neural engine will detect objects and take instant screenshots of every finding.
            </p>
            <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
              <button type="button" id="btn-browse-main" class="px-4 py-2 rounded-lg bg-seafoam-glow hover:bg-seafoam-glow/90 text-abyssal-navy font-headline-sm text-[12px] font-bold flex items-center gap-1.5 shadow-lg transition-all">
                <span class="material-symbols-outlined text-[16px]">add_photo_alternate</span>
                <span>Select Image / Video</span>
              </button>
              <button type="button" id="btn-sample-video" class="px-3.5 py-2 rounded-lg bg-surface-container-lowest/10 hover:bg-surface-container-lowest/20 text-surface-container-lowest border border-white/20 font-label-code text-[11px] flex items-center gap-1.5 transition-all">
                <span class="material-symbols-outlined text-[15px] text-seafoam-glow">play_circle</span>
                <span>Load Sample Video (LandingPage.mp4)</span>
              </button>
              <button type="button" id="btn-sample-image" class="px-3.5 py-2 rounded-lg bg-surface-container-lowest/10 hover:bg-surface-container-lowest/20 text-surface-container-lowest border border-white/20 font-label-code text-[11px] flex items-center gap-1.5 transition-all">
                <span class="material-symbols-outlined text-[15px] text-secondary-container">image</span>
                <span>Load Sample Scan</span>
              </button>
            </div>
            <div class="mt-3 font-label-code text-[10px] text-surface-variant/60">
              ACCEPTED: .JPG, .PNG, .WEBP, .MP4, .MOV, .AVI, .WEBM
            </div>
          </div>

          <!-- Bottom HUD telemetry strip over media -->
          <div class="absolute bottom-3 left-4 bg-primary/85 backdrop-blur-md px-3 py-1.5 rounded text-surface-container-lowest font-label-code text-[10px] flex items-center gap-space-md z-20 pointer-events-none">
            <div>POS: <span class="text-seafoam-glow font-semibold" id="hud-coords">12°51'24.8"N 80°14'38.2"E</span></div>
            <div>STATUS: <span class="text-tertiary-fixed font-bold" id="hud-status">READY FOR INGEST</span></div>
            <div class="hidden sm:block">MODEL: <span class="text-surface-variant font-semibold">best.pt (YOLO)</span></div>
          </div>
          <div class="absolute bottom-3 right-4 bg-primary/85 backdrop-blur-md px-2.5 py-1 rounded text-surface-container-high font-label-code text-[10px] z-20 flex items-center gap-2">
            <span id="hud-file-info">AUV SIDESCAN FEED</span>
            <button id="btn-reset-media" class="hidden px-2 py-0.5 rounded bg-surface-container text-on-surface hover:bg-white text-[10px] font-bold pointer-events-auto">Change Media</button>
          </div>
        </div>
<!-- Maritime Playback Scrubber & Navigation Control Console -->'''

if re.search(old_viewport_pattern, content):
    content = re.sub(old_viewport_pattern, new_viewport, content)
    print("Viewport replaced successfully.")
else:
    print("Viewport pattern NOT matched.")

# 2. Update Right Sidebar ("Detected Anomalies")
old_sidebar_pattern = r'<!-- Feed Container: High-Fidelity Anomaly Cards -->[\s\S]*?<!-- Sticky Tactical Dispatch Operations Box -->'

new_sidebar = '''<!-- Feed Container: High-Fidelity Anomaly Cards -->
          <div id="anomalies-container" class="flex flex-col gap-space-sm max-h-[820px] overflow-y-auto pr-1">
            <!-- Initial Empty State Placeholder -->
            <div id="empty-state-card" class="bg-surface-container-lowest p-6 rounded-xl border border-dashed border-outline-variant/60 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">
                <span class="material-symbols-outlined text-[28px] animate-pulse">radar</span>
              </div>
              <h4 class="font-headline-sm text-[15px] text-primary font-bold">No Detections Extracted Yet</h4>
              <p class="font-body-sm text-body-sm text-on-surface-variant max-w-xs">
                Upload a sonar image or video to run inference with <code class="bg-surface-ice px-1 py-0.5 rounded text-secondary font-bold">best.pt</code>.
                Every detected object will be cropped as a screenshot and presented here.
              </p>
              <button onclick="document.getElementById('file-input').click()" class="mt-2 px-4 py-1.5 rounded-lg bg-secondary hover:bg-secondary/90 text-on-secondary font-label-code text-[12px] flex items-center gap-1.5 shadow-sm">
                <span class="material-symbols-outlined text-[16px]">upload_file</span>
                <span>Upload Media Now</span>
              </button>
            </div>
          </div>
<!-- Sticky Tactical Dispatch Operations Box -->'''

if re.search(old_sidebar_pattern, content):
    content = re.sub(old_sidebar_pattern, new_sidebar, content)
    print("Sidebar cards replaced successfully.")
else:
    print("Sidebar pattern NOT matched.")

# 3. Update Anomaly count badge and filter tabs
old_filter_pattern = r'<span class="px-2 py-0\.5 bg-sonar-alert/10 text-sonar-alert font-label-code text-\[11px\] font-bold rounded-full">[\s\S]*?14 ACTIVE[\s\S]*?</span>[\s\S]*?<!-- Filter Segmented Tabs -->[\s\S]*?<div class="flex items-center gap-1 bg-surface-ice p-1 rounded-lg font-label-code text-\[11px\]">[\s\S]*?</div>'

new_filter = '''<span id="active-count-badge" class="px-2 py-0.5 bg-secondary/10 text-secondary font-label-code text-[11px] font-bold rounded-full">
            0 ACTIVE
          </span>
        </div>
        <!-- Filter Segmented Tabs -->
        <div id="filter-tabs-container" class="flex items-center gap-1 bg-surface-ice p-1 rounded-lg font-label-code text-[11px] overflow-x-auto">
          <button data-filter="all" class="filter-tab flex-1 py-1 px-2 rounded bg-surface-container-lowest text-primary font-bold shadow-xs text-center whitespace-nowrap">
            All (<span id="count-all">0</span>)
          </button>
          <button data-filter="shipwreck" class="filter-tab flex-1 py-1 px-2 text-on-surface-variant hover:text-on-surface text-center whitespace-nowrap">
            Shipwrecks (<span id="count-shipwreck">0</span>)
          </button>
          <button data-filter="ghost_net" class="filter-tab flex-1 py-1 px-2 text-on-surface-variant hover:text-on-surface text-center whitespace-nowrap">
            Ghost Nets (<span id="count-ghost_net">0</span>)
          </button>
          <button data-filter="crab_pot" class="filter-tab flex-1 py-1 px-2 text-on-surface-variant hover:text-on-surface text-center whitespace-nowrap">
            Traps (<span id="count-crab_pot">0</span>)
          </button>
          <button data-filter="other" class="filter-tab flex-1 py-1 px-2 text-on-surface-variant hover:text-on-surface text-center whitespace-nowrap">
            Other (<span id="count-other">0</span>)
          </button>
        </div>'''

if re.search(old_filter_pattern, content):
    content = re.sub(old_filter_pattern, new_filter, content)
    print("Filter tabs replaced successfully.")
else:
    print("Filter tabs pattern NOT matched.")

# 4. Wire the lower Ingest Raw .XTF / Dropzone section to also open file input
content = content.replace("Chennai_Trawl_Run_02.xtf", "LandingPage.mp4 (Sample)")
content = content.replace("Survey_Transect_05_deep_corridor.xtf (420 MB)", "YOLOv8 best.pt Inference Pipeline Active")
content = content.replace("Pre-processing slant-range gain normalization • 68% complete", "Ready for live Sonar video and acoustic imagery ingest")

# 5. Replace the script tag at the bottom with full client logic
old_script_pattern = r'<script>[\s\S]*?document\.addEventListener\("DOMContentLoaded"[\s\S]*?</script>'

new_script = '''<script>
document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingStatusText = document.getElementById('loading-status-text');
    const resultImage = document.getElementById('result-image');
    const resultVideo = document.getElementById('result-video');
    const hudCoords = document.getElementById('hud-coords');
    const hudStatus = document.getElementById('hud-status');
    const hudFileInfo = document.getElementById('hud-file-info');
    const btnResetMedia = document.getElementById('btn-reset-media');
    
    const btnBrowseMain = document.getElementById('btn-browse-main');
    const btnSampleVideo = document.getElementById('btn-sample-video');
    const btnSampleImage = document.getElementById('btn-sample-image');
    const confSlider = document.getElementById('conf-slider');
    const confVal = document.getElementById('conf-val');
    
    const anomaliesContainer = document.getElementById('anomalies-container');
    const emptyStateCard = document.getElementById('empty-state-card');
    const activeCountBadge = document.getElementById('active-count-badge');
    const filterTabs = document.querySelectorAll('.filter-tab');
    
    let currentDetections = [];
    let currentFilter = 'all';

    // File selection triggers
    if (btnBrowseMain) btnBrowseMain.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
    if (uploadZone) uploadZone.addEventListener('click', () => fileInput.click());
    if (btnResetMedia) btnResetMedia.addEventListener('click', () => fileInput.click());
    
    // Preset sample triggers
    if (btnSampleVideo) {
        btnSampleVideo.addEventListener('click', (e) => {
            e.stopPropagation();
            runDetectionWithSample('LandingPage.mp4');
        });
    }
    if (btnSampleImage) {
        btnSampleImage.addEventListener('click', (e) => {
            e.stopPropagation();
            runDetectionWithSample('stitch_screen');
        });
    }

    // Drag & Drop
    const container = document.getElementById('sonar-canvas-container');
    ['dragenter', 'dragover'].forEach(name => {
        container.addEventListener(name, (e) => {
            e.preventDefault();
            uploadZone.classList.add('bg-seafoam-glow/10');
        });
    });
    ['dragleave', 'drop'].forEach(name => {
        container.addEventListener(name, (e) => {
            e.preventDefault();
            uploadZone.classList.remove('bg-seafoam-glow/10');
        });
    });
    container.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length > 0) {
            handleUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleUpload(this.files[0]);
        }
    });

    // Wire lower dropzone button
    const lowerDropzone = document.getElementById('sonar-dropzone-section');
    if (lowerDropzone) {
        const browseBtn = lowerDropzone.querySelector('button');
        if (browseBtn) {
            browseBtn.addEventListener('click', () => fileInput.click());
        }
    }

    function showLoading(msg) {
        loadingOverlay.classList.remove('hidden');
        if (loadingStatusText) loadingStatusText.innerText = msg || 'Running best.pt inference across frames & generating detection screenshots...';
        if (hudStatus) {
            hudStatus.innerText = 'PROCESSING NEURAL SCAN...';
            hudStatus.className = 'text-sonar-alert font-bold animate-pulse';
        }
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
        if (hudStatus) {
            hudStatus.innerText = 'ONLINE / INFERENCE COMPLETE';
            hudStatus.className = 'text-seafoam-glow font-bold';
        }
    }

    function handleUpload(file) {
        const conf = confSlider ? (parseFloat(confSlider.value) / 100) : 0.20;
        showLoading(`Ingesting ${file.name} — Running YOLO inference on model best.pt...`);
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conf', conf.toString());

        fetch('/api/detect', {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error('Inference server returned status ' + res.status);
            return res.json();
        })
        .then(data => {
            hideLoading();
            renderResults(data);
        })
        .catch(err => {
            hideLoading();
            console.error(err);
            alert('Error running inference: ' + err.message + '\\nPlease ensure Python Flask server is running on port 3000.');
        });
    }

    function runDetectionWithSample(sampleName) {
        const conf = confSlider ? (parseFloat(confSlider.value) / 100) : 0.20;
        showLoading(`Loading preset ${sampleName} — Running YOLO inference on best.pt...`);
        
        const formData = new FormData();
        formData.append('sample', sampleName);
        formData.append('conf', conf.toString());

        fetch('/api/detect', {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error('Inference error');
            return res.json();
        })
        .then(data => {
            hideLoading();
            renderResults(data);
        })
        .catch(err => {
            hideLoading();
            console.error(err);
            alert('Error running sample detection: ' + err.message);
        });
    }

    function renderResults(data) {
        uploadZone.classList.add('hidden');
        if (btnResetMedia) btnResetMedia.classList.remove('hidden');
        if (hudFileInfo) hudFileInfo.innerText = (data.filename || 'Processed Sonar Feed').toUpperCase();

        if (data.media_type === 'video') {
            resultImage.classList.add('hidden');
            resultVideo.classList.remove('hidden');
            resultVideo.src = data.media_url + '?t=' + new Date().getTime();
            resultVideo.play().catch(e => console.log('Autoplay prevented:', e));
        } else {
            resultVideo.classList.add('hidden');
            resultImage.classList.remove('hidden');
            resultImage.src = data.media_url;
        }

        currentDetections = data.detections || [];
        updateAnomalyCounts(currentDetections);
        renderAnomalyCards(currentDetections);
    }

    function updateAnomalyCounts(detections) {
        const total = detections.length;
        if (activeCountBadge) {
            activeCountBadge.innerText = `${total} ACTIVE`;
            if (total > 0) {
                activeCountBadge.className = 'px-2 py-0.5 bg-sonar-alert/15 text-sonar-alert font-label-code text-[11px] font-bold rounded-full animate-pulse';
            } else {
                activeCountBadge.className = 'px-2 py-0.5 bg-secondary/10 text-secondary font-label-code text-[11px] font-bold rounded-full';
            }
        }
        
        const counts = {
            all: total,
            shipwreck: detections.filter(d => d.class_name === 'shipwreck').length,
            ghost_net: detections.filter(d => d.class_name === 'ghost_net').length,
            crab_pot: detections.filter(d => d.class_name === 'crab_pot').length,
            other: detections.filter(d => !['shipwreck', 'ghost_net', 'crab_pot'].includes(d.class_name)).length
        };

        const countAll = document.getElementById('count-all');
        const countShip = document.getElementById('count-shipwreck');
        const countNet = document.getElementById('count-ghost_net');
        const countPot = document.getElementById('count-crab_pot');
        const countOther = document.getElementById('count-other');

        if (countAll) countAll.innerText = counts.all;
        if (countShip) countShip.innerText = counts.shipwreck;
        if (countNet) countNet.innerText = counts.ghost_net;
        if (countPot) countPot.innerText = counts.crab_pot;
        if (countOther) countOther.innerText = counts.other;
    }

    function renderAnomalyCards(detections) {
        anomaliesContainer.innerHTML = '';

        const filtered = currentFilter === 'all' 
            ? detections 
            : currentFilter === 'other'
                ? detections.filter(d => !['shipwreck', 'ghost_net', 'crab_pot'].includes(d.class_name))
                : detections.filter(d => d.class_name === currentFilter);

        if (filtered.length === 0) {
            anomaliesContainer.innerHTML = `
                <div class="bg-surface-container-lowest p-6 rounded-xl border border-dashed border-outline-variant/60 flex flex-col items-center justify-center text-center gap-2">
                    <span class="material-symbols-outlined text-[32px] text-on-surface-variant">search_off</span>
                    <h5 class="font-headline-sm text-[14px] text-primary font-bold">No Detections for Current Filter</h5>
                    <p class="font-body-sm text-[12px] text-on-surface-variant">Try selecting "All" or adjusting the confidence slider.</p>
                </div>
            `;
            return;
        }

        filtered.forEach((det, idx) => {
            const card = document.createElement('div');
            card.className = "bg-surface-container-lowest p-space-md rounded-xl shadow-md hover:shadow-lg transition-all relative flex flex-col gap-space-sm cursor-pointer";
            card.style.borderLeft = `4px solid ${det.color || '#006398'}`;
            
            const timeTag = det.time_offset ? ` • TIME: ${det.time_offset}` : '';

            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex flex-col">
                        <span class="font-label-code text-[10px] text-on-surface-variant">${det.id}${timeTag}</span>
                        <h4 class="font-headline-sm text-[15px] text-primary font-bold">${det.title}</h4>
                    </div>
                    <span class="px-2 py-0.5 rounded font-label-code text-[10px] font-bold ${det.badge_bg}">
                        ${det.badge}
                    </span>
                </div>

                <!-- Acoustic Screenshot Crop -->
                <div class="relative h-32 w-full rounded-lg overflow-hidden bg-abyssal-navy border border-surface-ice group/crop">
                    <img class="w-full h-full object-cover group-hover/crop:scale-105 transition-transform" src="${det.crop_url}" alt="${det.title}" />
                    <div class="absolute top-2 left-2 bg-primary/90 text-seafoam-glow font-label-code text-[9px] px-1.5 py-0.5 rounded backdrop-blur-xs flex items-center gap-1">
                        <span class="material-symbols-outlined text-[10px]">crop</span>
                        <span>DETECTION SCREENSHOT</span>
                    </div>
                    <div class="absolute bottom-2 right-2 bg-abyssal-navy/90 text-surface-container-lowest font-label-code text-[9px] px-1.5 py-0.5 rounded backdrop-blur-xs">
                        Z: ${det.depth} | DIM: ${det.dim}
                    </div>
                </div>

                <!-- Metadata Spec Grid -->
                <div class="grid grid-cols-2 gap-2 bg-surface-container-low p-space-xs rounded-lg font-label-code text-[11px]">
                    <div>
                        <span class="text-on-surface-variant">MATERIAL:</span>
                        <div class="font-semibold text-primary truncate">${det.material}</div>
                    </div>
                    <div>
                        <span class="text-on-surface-variant">NEURAL CONF.:</span>
                        <div class="font-semibold" style="color: ${det.color}">${det.confidence}% (best.pt)</div>
                    </div>
                    <div class="col-span-2">
                        <span class="text-on-surface-variant">HAZARD PROFILE:</span>
                        <div class="font-medium text-primary text-[10px]">${det.hazard}</div>
                    </div>
                </div>

                <!-- Card Action Buttons -->
                <div class="flex items-center gap-space-xs pt-1">
                    <button class="btn-review flex-1 py-1.5 rounded-lg bg-primary hover:bg-abyssal-navy text-on-primary font-label-code text-label-code flex items-center justify-center gap-1 shadow-sm transition-all">
                        <span class="material-symbols-outlined text-[15px] text-seafoam-glow">verified</span>
                        <span>Verify Anomaly</span>
                    </button>
                    ${det.time_offset ? `
                    <button class="btn-seek px-3 py-1.5 rounded-lg bg-surface-ice hover:bg-surface-container text-secondary font-label-code text-[11px] flex items-center gap-1 font-bold" title="Seek video to timestamp">
                        <span class="material-symbols-outlined text-[14px]">fast_forward</span>
                        <span>${det.time_offset}</span>
                    </button>
                    ` : ''}
                </div>
            `;

            // Seek button handler
            const seekBtn = card.querySelector('.btn-seek');
            if (seekBtn && resultVideo && det.time_offset) {
                seekBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const parts = det.time_offset.split(':');
                    const sec = parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
                    resultVideo.currentTime = sec;
                    resultVideo.play();
                });
            }

            // Review button handler
            const reviewBtn = card.querySelector('.btn-review');
            if (reviewBtn) {
                reviewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    reviewBtn.innerHTML = '<span class="material-symbols-outlined text-[15px] text-seafoam-glow animate-spin">sync</span><span>Queued...</span>';
                    setTimeout(() => {
                        reviewBtn.innerHTML = '<span class="material-symbols-outlined text-[15px] text-seafoam-glow">check_circle</span><span>Dispatched #409</span>';
                        reviewBtn.classList.add('bg-teal-800');
                    }, 600);
                });
            }

            anomaliesContainer.appendChild(card);
        });
    }

    // Filter tab clicks
    filterTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            filterTabs.forEach(t => {
                t.classList.remove('bg-surface-container-lowest', 'text-primary', 'font-bold', 'shadow-xs');
                t.classList.add('text-on-surface-variant');
            });
            this.classList.add('bg-surface-container-lowest', 'text-primary', 'font-bold', 'shadow-xs');
            this.classList.remove('text-on-surface-variant');
            
            currentFilter = this.getAttribute('data-filter');
            renderAnomalyCards(currentDetections);
        });
    });
});
</script>'''

if re.search(old_script_pattern, content):
    content = re.sub(old_script_pattern, new_script, content)
    print("Script replaced successfully.")
else:
    print("Script pattern NOT matched.")

with open('sonar-ai.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("sonar-ai.html updated successfully!")
