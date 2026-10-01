
document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingStatusText = document.getElementById('loading-status-text');
    const resultImage = document.getElementById('result-image');
    const resultVideo = document.getElementById('result-video');
    const mediaViewport = document.getElementById('media-viewport');
    
    const btnBrowseMain = document.getElementById('btn-browse-main');
    const btnSampleVideo = document.getElementById('btn-sample-video');
    const btnSampleImage = document.getElementById('btn-sample-image');
    const btnPlayPause = document.getElementById('btn-play-pause');
    const btnStop = document.getElementById('btn-stop');
    const btnReupload = document.getElementById('btn-reupload');
    const btnMaximize = document.getElementById('btn-maximize');
    const btnPopout = document.getElementById('btn-popout');
    const videoTime = document.getElementById('video-time');
    
    const anomaliesContainer = document.getElementById('anomalies-container');
    const activeCountBadge = document.querySelector('aside .flex-none span.rounded-full');
    const filterTabs = document.querySelectorAll('aside .overflow-x-auto button');
    
    let currentDetections = [];
    let currentFilter = 'all';
    let isProcessing = false;
    let processingInterval = null;

    // Trigger File Picker
    if (btnBrowseMain) {
        btnBrowseMain.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }
    if (btnReupload) {
        btnReupload.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }
    if (uploadZone) {
        uploadZone.addEventListener('click', (e) => {
            if (e.target !== btnSampleVideo && e.target !== btnSampleImage && !btnSampleVideo?.contains(e.target) && !btnSampleImage?.contains(e.target)) {
                fileInput.click();
            }
        });
    }

    // Sample Triggers
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

    // Stop / Reset Button
    if (btnStop) {
        btnStop.addEventListener('click', () => {
            if (processingInterval) clearInterval(processingInterval);
            resultVideo.pause();
            resultVideo.src = '';
            resultVideo.classList.add('hidden');
            resultImage.src = '';
            resultImage.classList.add('hidden');
            uploadZone.classList.remove('hidden');
            if (btnPlayPause) btnPlayPause.innerHTML = '<span class="material-symbols-outlined text-[28px]">play_circle</span>';
            if (videoTime) videoTime.innerText = '00:00 / 00:00';
            fileInput.value = '';
        });
    }

    // Play / Pause Button
    if (btnPlayPause) {
        btnPlayPause.addEventListener('click', () => {
            if (resultVideo && !resultVideo.classList.contains('hidden')) {
                if (resultVideo.paused) {
                    resultVideo.play();
                    btnPlayPause.innerHTML = '<span class="material-symbols-outlined text-[28px]">pause_circle</span>';
                } else {
                    resultVideo.pause();
                    btnPlayPause.innerHTML = '<span class="material-symbols-outlined text-[28px]">play_circle</span>';
                }
            }
        });
    }

    if (resultVideo) {
        resultVideo.addEventListener('play', () => {
            if (btnPlayPause) btnPlayPause.innerHTML = '<span class="material-symbols-outlined text-[28px]">pause_circle</span>';
        });
        resultVideo.addEventListener('pause', () => {
            if (btnPlayPause) btnPlayPause.innerHTML = '<span class="material-symbols-outlined text-[28px]">play_circle</span>';
        });
        resultVideo.addEventListener('timeupdate', () => {
            if (videoTime && resultVideo.duration) {
                const cur = formatTime(resultVideo.currentTime);
                const dur = formatTime(resultVideo.duration);
                videoTime.innerText = `${cur} / ${dur}`;
            }
        });
    }

    function formatTime(sec) {
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }

    // Maximize & Popout
    if (btnMaximize && mediaViewport) {
        btnMaximize.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                mediaViewport.requestFullscreen().catch(err => console.log(err));
            } else {
                document.exitFullscreen();
            }
        });
    }
    if (btnPopout && resultVideo) {
        btnPopout.addEventListener('click', () => {
            if (document.pictureInPictureEnabled && !resultVideo.classList.contains('hidden')) {
                resultVideo.requestPictureInPicture().catch(err => console.log(err));
            }
        });
    }

    // Drag and Drop
    if (uploadZone) {
        ['dragenter', 'dragover'].forEach(name => {
            uploadZone.addEventListener(name, (e) => {
                e.preventDefault();
                uploadZone.classList.add('bg-teal-500/10');
            });
        });
        ['dragleave', 'drop'].forEach(name => {
            uploadZone.addEventListener(name, (e) => {
                e.preventDefault();
                uploadZone.classList.remove('bg-teal-500/10');
            });
        });
        uploadZone.addEventListener('drop', (e) => {
            if (e.dataTransfer && e.dataTransfer.files.length > 0) {
                handleUpload(e.dataTransfer.files[0]);
            }
        });
    }

    // File Input change
    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            handleUpload(this.files[0]);
        }
    });

    function showLoading(msg) {
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
            if (loadingStatusText) loadingStatusText.innerText = msg || 'Running best.pt inference across frames & generating detection screenshots...';
        }
    }

    function hideLoading() {
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }
    }

    function startRealtimeProcessing() {
        if (processingInterval) clearInterval(processingInterval);
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        processingInterval = setInterval(() => {
            if (!resultVideo || resultVideo.paused || resultVideo.ended || isProcessing) return;
            
            isProcessing = true;
            canvas.width = resultVideo.videoWidth || 1280;
            canvas.height = resultVideo.videoHeight || 720;
            ctx.drawImage(resultVideo, 0, 0, canvas.width, canvas.height);
            
            canvas.toBlob((blob) => {
                if (!blob) {
                    isProcessing = false;
                    return;
                }
                
                
                const formData = new FormData();
                formData.append('file', blob, 'frame.jpg');
                formData.append('conf', '0.20');
                if (window.currentSurveyId) {
                    formData.append('survey_id', window.currentSurveyId);
                }


                fetch('/api/detect', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    if (data.detections && data.detections.length > 0) {
                        data.detections.forEach(d => {
                            const isDuplicate = currentDetections.slice(0, 4).some(existing => existing.class_name === d.class_name);
                            if (!isDuplicate) {
                                d.id = d.id + '-' + Math.random().toString(36).substr(2, 6);
                                currentDetections.unshift(d);
                            }
                        });
                        
                        if (currentDetections.length > 40) currentDetections = currentDetections.slice(0, 40);
                        
                        updateAnomalyCounts(currentDetections);
                        renderAnomalyCards(currentDetections);
                    }
                    isProcessing = false;
                })
                .catch(err => {
                    console.error("Frame processing error:", err);
                    isProcessing = false;
                });
            }, 'image/jpeg', 0.85);
            
        }, 1200);
    }

    function handleUpload(file) {
        uploadZone.classList.add('hidden');
        const isVideo = file.type.startsWith('video/') || file.name.match(/\.(mp4|mov|avi|webm)$/i);

        const isXtf = file.name.toLowerCase().endsWith('.xtf');
        if (isXtf) {
            resultVideo.classList.add('hidden');
            resultImage.classList.add('hidden');
            showLoading(`Ingesting ${file.name} — Parsing XTF binary & reconstructing waterfall...`);
            
            
            const formData = new FormData();
            formData.append('file', file);
            if (window.currentSurveyId) {
                formData.append('survey_id', window.currentSurveyId);
            }


            fetch('/api/v1/xtf/upload', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                renderXtfResults(data);
            })
            .catch(err => {
                hideLoading();
                alert('Error processing XTF: ' + err.message);
            });
            return;
        }

        
        if (isVideo) {
            resultImage.classList.add('hidden');
            resultVideo.classList.remove('hidden');
            
            const fileURL = URL.createObjectURL(file);
            resultVideo.src = fileURL;
            resultVideo.play().catch(e => console.log('Autoplay blocked:', e));
            
            currentDetections = [];
            if (anomaliesContainer) anomaliesContainer.innerHTML = '';
            
            startRealtimeProcessing();
        } else {
            resultVideo.classList.add('hidden');
            resultImage.classList.remove('hidden');
            showLoading(`Ingesting ${file.name} — Running YOLO inference on model best.pt...`);
            
            
            const formData = new FormData();
            formData.append('file', file);
            if (window.currentSurveyId) {
                formData.append('survey_id', window.currentSurveyId);
            }

            formData.append('conf', '0.20');

            fetch('/api/detect', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                renderResults(data);
            })
            .catch(err => {
                hideLoading();
                alert('Error running inference: ' + err.message);
            });
        }
    }

    function runDetectionWithSample(sampleName) {
        uploadZone.classList.add('hidden');
        const isVideo = sampleName.endsWith('.mp4');
        
        if (isVideo) {
            resultImage.classList.add('hidden');
            resultVideo.classList.remove('hidden');
            resultVideo.src = 'LandingPage.mp4';
            resultVideo.play().catch(e => console.log('Autoplay blocked:', e));
            
            currentDetections = [];
            if (anomaliesContainer) anomaliesContainer.innerHTML = '';
            
            startRealtimeProcessing();
        } else {
            resultVideo.classList.add('hidden');
            resultImage.classList.remove('hidden');
            showLoading(`Loading sample scan — Running YOLO inference on model best.pt...`);
            
            const formData = new FormData();
            formData.append('sample', sampleName);
            formData.append('conf', '0.20');

            fetch('/api/detect', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                hideLoading();
                renderResults(data);
            })
            .catch(err => {
                hideLoading();
                alert('Error running sample detection: ' + err.message);
            });
        }
    }

    
    function renderXtfResults(data) {
        uploadZone.classList.add('hidden');
        resultVideo.classList.add('hidden');
        resultImage.classList.add('hidden'); // We will create custom image elements

        // Clear previous custom xtf container if exists
        let oldContainer = document.getElementById('xtf-container');
        if (oldContainer) oldContainer.remove();

        const container = document.createElement('div');
        container.id = 'xtf-container';
        container.className = 'absolute inset-0 z-10 bg-[#020b15] overflow-y-auto p-4 flex flex-col gap-4';
        

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

    function renderResults(data) {
        uploadZone.classList.add('hidden');

        if (data.media_type === 'video') {
            resultImage.classList.add('hidden');
            resultVideo.classList.remove('hidden');
            resultVideo.src = data.media_url + '?t=' + new Date().getTime();
            resultVideo.play().catch(e => console.log(e));
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
            activeCountBadge.innerText = `${total} Active`;
            if (total > 0) {
                activeCountBadge.className = 'px-2 py-0.5 rounded-full bg-red-100 text-sonar-alert text-label-code font-label-code font-bold border border-red-200 animate-pulse';
            } else {
                activeCountBadge.className = 'px-2 py-0.5 rounded-full bg-surface-ice text-primary-container text-label-code font-label-code font-bold border border-border-subtle';
            }
        }
        
        const countAll = document.getElementById('count-all');
        const countShip = document.getElementById('count-shipwreck');
        const countNet = document.getElementById('count-ghost_net');
        const countOther = document.getElementById('count-other');

        if (countAll) countAll.innerText = total;
        if (countShip) countShip.innerText = detections.filter(d => d.class_name === 'shipwreck').length;
        if (countNet) countNet.innerText = detections.filter(d => d.class_name === 'ghost_net').length;
        if (countOther) countOther.innerText = detections.filter(d => !['shipwreck', 'ghost_net'].includes(d.class_name)).length;
    }

    function renderAnomalyCards(detections) {
        if (!anomaliesContainer) return;
        anomaliesContainer.innerHTML = '';

        const filtered = currentFilter === 'all' 
            ? detections 
            : currentFilter === 'other'
                ? detections.filter(d => !['shipwreck', 'ghost_net'].includes(d.class_name))
                : detections.filter(d => d.class_name === currentFilter);

        if (filtered.length === 0) {
            anomaliesContainer.innerHTML = `
                <div class="bg-surface-container-lowest p-6 rounded-xl border border-dashed border-outline-variant/60 flex flex-col items-center justify-center text-center gap-2 h-64 mt-4 mx-2">
                    <span class="material-symbols-outlined text-[32px] text-teal-600 p-3 rounded-xl bg-teal-50 mb-2">policy</span>
                    <h5 class="font-headline-sm text-[15px] text-primary font-bold">No Detections Extracted</h5>
                    <p class="font-body-sm text-[12px] text-on-surface-variant px-4">Upload a sonar image or video to run inference with <strong class="text-primary font-label-code">best.pt</strong>. Each detected target will be extracted as a screenshot here.</p>
                </div>
            `;
            return;
        }

        filtered.forEach((det) => {
            const card = document.createElement('div');
            card.className = "bg-surface-container-lowest p-3 rounded-xl shadow-sm hover:shadow-md transition-all relative flex flex-col gap-2 border border-border-subtle cursor-pointer";
            card.style.borderLeft = `4px solid ${det.color || '#006398'}`;
            
            const timeTag = det.time_offset ? ` • ${det.time_offset}` : '';

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


            card.innerHTML = `
                <div class="flex items-start justify-between gap-1">
                    <div class="flex flex-col">
                        <span class="font-label-code text-[10px] text-on-surface-variant">${det.id}${timeTag}</span>
                        <h4 class="font-headline-sm text-[14px] text-primary font-bold leading-tight">${det.title}</h4>
                    </div>
                    <span class="px-2 py-0.5 rounded font-label-code text-[10px] font-bold bg-teal-50 text-teal-700 border border-teal-200">
                        ${det.confidence}% CONF
                    </span>
                </div>

                <!-- Acoustic Screenshot Crop -->
                <div class="relative h-28 w-full rounded-lg overflow-hidden bg-abyssal-navy border border-slate-200 group/crop">
                    <img class="w-full h-full object-contain bg-black/50 group-hover/crop:scale-105 transition-transform" src="${det.crop_url}" alt="Crop" />
                    <div class="absolute top-1.5 left-1.5 bg-primary/90 text-seafoam-glow font-label-code text-[8px] px-1.5 py-0.5 rounded backdrop-blur-xs flex items-center gap-1">
                        <span class="material-symbols-outlined text-[10px]">crop</span>
                        <span>DETECTION CROP</span>
                    </div>
                    <div class="absolute bottom-1.5 right-1.5 bg-abyssal-navy/90 text-white font-label-code text-[8px] px-1.5 py-0.5 rounded backdrop-blur-xs">
                        Z: ${det.depth} | ${det.dim}
                    </div>
                </div>

                <!-- Metadata Grid -->
                <div class="bg-surface-ice p-2 rounded-lg font-label-code text-[10px]">
                    <span class="text-slate-500">MATERIAL:</span>
                    <div class="font-semibold text-primary truncate">${det.material}</div>
                </div>

                ${telemetryHtml}

                <!-- Card Action Buttons -->
                ${det.time_offset ? `
                <div class="flex items-center gap-2 pt-1">
                    <button class="btn-seek flex-1 py-1 rounded-lg bg-surface-ice hover:bg-surface-container text-secondary font-label-code text-[11px] flex items-center justify-center gap-1 font-bold shadow-xs transition-all" title="Seek video to timestamp">
                        <span class="material-symbols-outlined text-[14px]">fast_forward</span>
                        <span>Seek to ${det.time_offset}</span>
                    </button>
                </div>
                ` : ''}
            `;

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

            const reviewBtn = card.querySelector('.btn-review');
            if (reviewBtn) {
                reviewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    reviewBtn.innerHTML = '<span class="material-symbols-outlined text-[14px] text-seafoam-glow animate-spin">sync</span><span>Queued...</span>';
                    setTimeout(() => {
                        reviewBtn.innerHTML = '<span class="material-symbols-outlined text-[14px] text-seafoam-glow">check_circle</span><span>Verified #409</span>';
                        reviewBtn.classList.add('bg-teal-800');
                    }, 500);
                });
            }

            anomaliesContainer.appendChild(card);
        });
    }

    // Filter Buttons
    if (filterTabs) {
        filterTabs.forEach((tab, index) => {
            tab.addEventListener('click', function() {
                filterTabs.forEach(t => {
                    t.classList.remove('bg-primary-container', 'text-surface-container-lowest', 'font-semibold', 'shadow-xs');
                    t.classList.add('bg-surface-ice', 'text-on-surface-variant');
                });
                this.classList.add('bg-primary-container', 'text-surface-container-lowest', 'font-semibold', 'shadow-xs');
                this.classList.remove('bg-surface-ice', 'text-on-surface-variant');
                
                const filterMap = ['all', 'shipwreck', 'ghost_net', 'other'];
                currentFilter = filterMap[index] || 'all';
                renderAnomalyCards(currentDetections);
            });
        });
    }

    const btnReport = document.getElementById('btn-generate-report');
    if (btnReport) {
        btnReport.addEventListener('click', () => {
            if (currentDetections.length === 0) {
                alert("No detections available to dispatch.");
                return;
            }
            
            const classAB = currentDetections.filter(d => d.classification_tier === 'Tier A' || d.classification_tier === 'Tier B' || d.classification_tier === 'A' || d.classification_tier === 'B').map(d => ({
                ...d,
                latitude: d.metadata?.latitude || d.latitude || null,
                longitude: d.metadata?.longitude || d.longitude || null
            }));
            const classC = currentDetections.filter(d => d.classification_tier === 'Tier C' || d.classification_tier === 'C').map(d => ({
                ...d,
                latitude: d.metadata?.latitude || d.latitude || null,
                longitude: d.metadata?.longitude || d.longitude || null
            }));
            
            // Initialize Supabase Client
            const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
            const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTQwMDU3MSwiZXhwIjoyMTA0OTc2NTcxfQ.3RRFtT--ublCzZZhfSyM0HodY0Goxtb-HrddJkCBLAU';
            const supabaseClient = supabase.createClient(supabaseUrl, supabaseKey);

            // Generate JSON for Class A and B
            if (classAB.length > 0) {
                const jsonObj = {
                    "timestamp": new Date().toISOString(),
                    "system": "TARANG_SURVEY_OPS",
                    "destination": "MARINE_ANALYST",
                    "exported_tier": ["A", "B"],
                    "total_detections": classAB.length,
                    "detections": classAB
                };
                
                // Push payload to Supabase Database
                supabaseClient.from('dispatches').insert([
                    { payload: jsonObj }
                ]).then(({ data, error }) => {
                    if (error) {
                        console.error('Error dispatching to Supabase:', error);
                        showToast("Failed to sync to Marine Analyst.", true);
                    } else {
                        console.log('Dispatch synced to cloud database');
                        showToast("Data sent successfully to Marine Analyst Portal!");
                    }
                });

                // Also save locally as a backup
                localStorage.setItem('marineAnalystData', JSON.stringify(jsonObj));

                const jsonBlob = new Blob([JSON.stringify(jsonObj, null, 2)], { type: 'application/json' });
                const jsonUrl = URL.createObjectURL(jsonBlob);
                const jsonA = document.createElement('a');
                jsonA.href = jsonUrl;
                jsonA.download = `Automated_Dispatch_ClassAB_${Date.now()}.json`;
                document.body.appendChild(jsonA);
                jsonA.click();
                document.body.removeChild(jsonA);
                URL.revokeObjectURL(jsonUrl);
            }
            
            // Push Class C to Supabase for Sonar Analyst
            if (classC.length > 0) {
                const jsonObjC = {
                    "timestamp": new Date().toISOString(),
                    "system": "TARANG_SURVEY_OPS",
                    "destination": "SONAR_ANALYST",
                    "exported_tier": ["C"],
                    "total_detections": classC.length,
                    "detections": classC
                };
                
                supabaseClient.from('dispatches').insert([
                    { payload: jsonObjC }
                ]).then(({ data, error }) => {
                    if (error) {
                        console.error('Error dispatching Class C to Supabase:', error);
                    } else {
                        console.log('Class C dispatch synced to cloud database');
                    }
                });
            }
            
            alert(`Dispatched ${classAB.length} automated targets and queued ${classC.length} manual review targets.`);
        });
    }
});
