
        // --- Toast Notification ---
        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.className = `fixed bottom-6 right-6 z-50 transform translate-y-0 opacity-100 transition-all duration-300 px-4 py-2.5 rounded-xl border font-mono text-xs font-bold shadow-2xl flex items-center gap-2 ${
        isError ? 'bg-rose-950/90 text-rose-200 border-rose-500/50' : 'bg-teal-950/90 text-teal-200 border-teal-500/50'
      }`;
            toast.innerHTML = `<span class="material-symbols-outlined text-[18px]">${isError ? 'error' : 'check_circle'}</span><span>${message}</span>`;
            setTimeout(() => {
                toast.classList.add('translate-y-20', 'opacity-0');
            }, 3500);
        }

        // --- State Storage ---
        let allSurveys = [];
        let globalDetections = [];
        let currentSurveyId = null;
        let mapInstance = null;
        let mapMarkers = [];
        let cleanupTarangMap = null;
        let latestRoute = null;

        // --- Tab Switching ---
        function switchTab(tabId) {
            document.querySelectorAll('.marine-view-panel').forEach(panel => panel.classList.add('hidden'));
            const activePanel = document.getElementById(`tab-${tabId}`);
            if (activePanel) activePanel.classList.remove('hidden');

            document.querySelectorAll('.marine-nav-btn').forEach(btn => {
                if (btn.getAttribute('data-tab') === tabId) {
                    btn.className = 'marine-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wide transition-all bg-seafoam text-ocean-navy shadow-sm';
                } else {
                    btn.className = 'marine-nav-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100';
                }
            });

            if (tabId === 'hotspots' || tabId === 'cleanup-missions' || tabId === 'clearance-updates') {
                syncSurveySelectors(tabId);
            }

            if (tabId === 'hotspots' && mapInstance) {
                setTimeout(() => mapInstance.invalidateSize(), 200);
            }
            if (tabId === 'cleanup-missions') {
                setTimeout(() => {
                    if (cleanupTarangMap && cleanupTarangMap.map) cleanupTarangMap.map.invalidateSize();
                    if (optimizedRouteMap && optimizedRouteMap.map) {
                        optimizedRouteMap.map.invalidateSize();
                        optimizedRouteMap.fitBounds();
                    }
                }, 200);
            }
        }

        function syncSurveySelectors(tabId) {
            if (currentSurveyId) {
                if (tabId === 'hotspots') {
                    const sel = document.getElementById('hotspot-survey-selector');
                    if (sel) {
                        sel.value = currentSurveyId;
                        loadHotspotMapForSurvey(currentSurveyId);
                    }
                } else if (tabId === 'cleanup-missions') {
                    const sel = document.getElementById('cleanup-survey-selector');
                    if (sel) {
                        sel.value = currentSurveyId;
                        loadCleanupMissionForSurvey(currentSurveyId);
                    }
                } else if (tabId === 'clearance-updates') {
                    const sel = document.getElementById('clearance-survey-selector');
                    if (sel) {
                        sel.value = currentSurveyId;
                        loadClearanceForSurvey(currentSurveyId);
                    }
                }
            }
        }

        function setGlobalSurvey(surveyId, targetTab) {
            currentSurveyId = surveyId;
            if (targetTab) switchTab(targetTab);
        }

        document.addEventListener('DOMContentLoaded', () => {
            const uName = sessionStorage.getItem('currentUserName');
            if (uName) {
                const elem = document.getElementById('marine-user-display-name');
                if (elem) elem.textContent = uName;
            }
            const dateInput = document.getElementById('clearance-date');
            if (dateInput) {
                dateInput.value = new Date().toISOString().split('T')[0];
            }
            initData();
        });

        async function initData() {
            try {
                const [surveysRes, detsRes] = await Promise.all([
                    fetch('/api/v1/surveys'),
                    fetch('/api/v1/surveys/all/detections')
                ]);

                if (surveysRes.ok) allSurveys = await surveysRes.json();
                if (detsRes.ok) {
                    const data = await detsRes.json();
                    globalDetections = Array.isArray(data) ? data : (data.detections || []);
                }

                populateSurveySelectors();
                renderOverviewSurveys();
                renderReportsTable();

            } catch (err) {
                console.error('Failed to init data:', err);
                showToast('Error loading backend data', true);
            }
        }

        function populateSurveySelectors() {
            const selects = ['hotspot-survey-selector', 'cleanup-survey-selector', 'clearance-survey-selector'];
            selects.forEach(id => {
                const sel = document.getElementById(id);
                if (!sel) return;
                sel.innerHTML = `<option value="">— Select a survey —</option>` + allSurveys.map(s => `<option value="${s.survey_id}">${s.survey_name} (${s.survey_id})</option>`).join('');
            });
        }

        // --- Overview Tab ---
        function renderOverviewSurveys() {
            const tbody = document.getElementById('overview-survey-tbody');
            if (!tbody) return;

            if (allSurveys.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-500 font-mono text-sm">No surveys found.</td></tr>`;
                return;
            }

            tbody.innerHTML = allSurveys.map(survey => {
                const sDets = globalDetections.filter(d => d.survey_id === survey.survey_id);
                const verifiedCount = sDets.filter(d => (d.verification_status || '').toLowerCase() === 'verified').length;
                const cleanupReq = sDets.filter(d => (d.clearance_status || '').toLowerCase() !== 'no_cleanup_required' && (d.verification_status || '').toLowerCase() === 'verified');
                const cleared = cleanupReq.filter(d => (d.clearance_status || '').toLowerCase() === 'cleared');

                const cleanupStatus = cleanupReq.length === 0 ? '<span class="text-slate-400">N/A</span>' :
                    (cleared.length === cleanupReq.length ? '<span class="text-teal-600 font-bold">Cleared</span>' :
                        `<span class="text-amber-500 font-bold">${cleared.length} / ${cleanupReq.length} Cleared</span>`);

                return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="py-3 px-4 font-bold text-slate-900">${survey.survey_name}</td>
            <td class="py-3 px-4 text-slate-500">${survey.survey_id}</td>
            <td class="py-3 px-4">
                <span class="px-2 py-1 rounded bg-teal-50 text-teal-700 text-xs font-bold border border-teal-200">${verifiedCount} Verified</span>
            </td>
            <td class="py-3 px-4 font-bold text-slate-700">${cleanupReq.length}</td>
            <td class="py-3 px-4">${cleanupStatus}</td>
            <td class="py-3 px-4 text-right">
                <button onclick="setGlobalSurvey('${survey.survey_id}', 'hotspots')" class="text-teal-600 hover:text-teal-800 font-bold text-xs underline">Analyze Spatial Data</button>
            </td>
          </tr>
        `;
            }).join('');
        }

        // --- Hotspots (Spatial) Tab ---
        function loadHotspotMapForSurvey(surveyId) {
            currentSurveyId = surveyId;
            const overlay = document.getElementById('hotspot-map-overlay');

            if (!surveyId) {
                overlay.classList.remove('opacity-0', 'pointer-events-none');
                return;
            }

            overlay.classList.add('opacity-0', 'pointer-events-none');

            if (!mapInstance) {
                mapInstance = L.map('hotspot-map').setView([8.50, 72.50], 10);
                TarangTiles.attach(mapInstance); // tiles + fallback chain from MAP_CONFIG (js/tarang-map.js)
            }

            // Clear old markers
            mapMarkers.forEach(m => mapInstance.removeLayer(m));
            mapMarkers = [];
            if (window.tspPolyline) {
                mapInstance.removeLayer(window.tspPolyline);
                window.tspPolyline = null;
            }

            const sDets = globalDetections.filter(d => d.survey_id === surveyId && d.latitude && d.longitude && d.is_offshore && (d.verification_status || '').toLowerCase() === 'verified');
            if (sDets.length === 0) {
                showToast('No verified coordinates found for this survey', true);
                return;
            }

            const cleanupTargets = sDets.filter(d => ['cleanup approved', 'cleanup scheduled', 'cleanup dispatched', 'cleanup in progress', 'cleanup completed'].includes((d.cleanup_status || d.clearance_status || '').toLowerCase()));

            const bounds = [];

            sDets.forEach(d => {
                const isCleanup = cleanupTargets.includes(d);
                const color = isCleanup ? '#ef4444' : '#14b8a6'; // red for cleanup, teal for ok/cleared
                const marker = L.circleMarker([d.latitude, d.longitude], {
                    radius: isCleanup ? 8 : 5,
                    fillColor: color,
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(mapInstance);

                marker.bindPopup(`<b>${d.class_name}</b><br>Tier: ${d.classification_tier}<br>Status: ${d.clearance_status}`);
                mapMarkers.push(marker);
                bounds.push([d.latitude, d.longitude]);
            });

            if (bounds.length > 0) {
                mapInstance.fitBounds(bounds, {
                    padding: [50, 50]
                });
            }

            // Route geometry is rendered only from the persisted server-side TSP result.
        }

        // Basic TSP heuristic
        function nearestNeighborTSP(points) {
            if (points.length <= 1) return points;
            let unvisited = [...points];
            let current = unvisited.shift();
            let path = [current];

            while (unvisited.length > 0) {
                let nearestIdx = 0;
                let minDist = Infinity;

                for (let i = 0; i < unvisited.length; i++) {
                    const dist = Math.pow(current.latitude - unvisited[i].latitude, 2) + Math.pow(current.longitude - unvisited[i].longitude, 2);
                    if (dist < minDist) {
                        minDist = dist;
                        nearestIdx = i;
                    }
                }

                current = unvisited.splice(nearestIdx, 1)[0];
                path.push(current);
            }
            return path;
        }

        // --- Cleanup Missions Tab ---
        function loadCleanupMissionForSurvey(surveyId) {
            currentSurveyId = surveyId;
            const details = document.getElementById('cleanup-mission-details');
            if (!surveyId) {
                details.classList.add('hidden');
                return;
            }
            details.classList.remove('hidden');

            const sDets = globalDetections.filter(d => d.survey_id === surveyId && (d.verification_status || '').toLowerCase() === 'verified');
            const cleanupTargets = sDets.filter(d => ['cleanup approved', 'cleanup scheduled', 'cleanup dispatched', 'cleanup in progress', 'cleanup completed'].includes((d.cleanup_status || d.clearance_status || '').toLowerCase()));
            const pendingTargets = cleanupTargets.filter(d => (d.clearance_status || '').toLowerCase() !== 'cleared');
            renderCleanupMap(cleanupTargets);
            latestRoute = null;
            fetch('/api/v1/routes/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    survey_id: surveyId
                })
            }).then(async response => response.ok ? response.json() : null).then(data => {
                latestRoute = data && data.route;
                const routeLabel = document.getElementById('cleanup-route-text');
                if (routeLabel) routeLabel.textContent = latestRoute ? `${latestRoute.target_count} stops · ${TarangUnits.formatDistance(TarangUnits.kmToNm(latestRoute.distance_km), latestRoute.distance_km)}` : 'Awaiting approved targets';
                if (latestRoute && cleanupTarangMap && cleanupTarangMap.map) {
                    cleanupTarangMap.setTrack((latestRoute.target_sequence || []).map(point => [point.latitude, point.longitude]));
                }
            }).catch(() => {});

            document.getElementById('cleanup-targets-text').textContent = pendingTargets.length;

            const statusEl = document.getElementById('cleanup-status-text');
            if (cleanupTargets.length === 0) {
                statusEl.textContent = 'No Cleanup Required';
                statusEl.className = 'text-xl font-bold font-mono text-slate-500 mt-1';
            } else if (pendingTargets.length === 0) {
                statusEl.textContent = 'Mission Accomplished';
                statusEl.className = 'text-xl font-bold font-mono text-emerald-600 mt-1';
            } else {
                statusEl.textContent = 'Active / Pending';
                statusEl.className = 'text-xl font-bold font-mono text-teal-700 mt-1';
            }

            const tbody = document.getElementById('cleanup-locations-tbody');
            if (cleanupTargets.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-slate-500">No cleanup targets for this survey.</td></tr>`;
                return;
            }

            const sequenced = pendingTargets.length > 1 ? nearestNeighborTSP(pendingTargets) : pendingTargets;

            tbody.innerHTML = cleanupTargets.map(d => {
                const seqIndex = sequenced.indexOf(d);
                const isCleared = (d.clearance_status || '').toLowerCase() === 'cleared';
                const seqText = isCleared ? '<span class="text-slate-400">—</span>' : `<span class="font-bold text-sky-600">Stop #${seqIndex + 1}</span>`;
                const statusClass = isCleared ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700';

                return `
                <tr class="hover:bg-slate-50">
                    <td class="p-3 font-bold text-slate-700">${d.id.substring(0,8)}</td>
                    <td class="p-3">${d.class_name || 'Unknown'}</td>
                    <td class="p-3 text-slate-500">${d.latitude ? d.latitude.toFixed(4) : 'N/A'}, ${d.longitude ? d.longitude.toFixed(4) : 'N/A'}</td>
                    <td class="p-3">${seqText}</td>
                    <td class="p-3"><span class="px-2 py-1 rounded text-xs font-bold ${statusClass}">${d.clearance_status || 'Pending'}</span></td>
                </tr>
            `;
            }).join('');
        }

        function renderCleanupMap(targets) {
            if (!cleanupTarangMap) {
                // Use MAP_CONFIG default center, will be auto-centered on actual targets
                cleanupTarangMap = new TarangMap('marineMap', {
                    center: MAP_CONFIG.defaultCenter,
                    zoom: 11
                });
            }
            if (!cleanupTarangMap || !cleanupTarangMap.map) return;

            cleanupTarangMap.clear();
            const mappedTargets = (targets || []).filter(d => d.latitude != null && d.longitude != null);
            cleanupTarangMap.setDetections(mappedTargets);
            if (mappedTargets.length > 1) {
                const route = nearestNeighborTSP(mappedTargets).map(d => [Number(d.latitude), Number(d.longitude)]);
                cleanupTarangMap.setTrack(route);
            }
            cleanupTarangMap.fitBounds();
            setTimeout(() => cleanupTarangMap.map.invalidateSize(), 100);
        }

        // The persisted operation projection is the only source for the cleanup
        // table and route.  This override deliberately replaces the legacy
        // client-side mock/TSP preview above.
        async function loadCleanupMissionForSurvey(surveyId) {
            currentSurveyId = surveyId;
            const details = document.getElementById('cleanup-mission-details');
            if (!surveyId) {
                details.classList.add('hidden');
                return;
            }
            details.classList.remove('hidden');
            const [operationsResponse, routeResponse] = await Promise.all([
                fetch(`/api/v1/cleanup/operations?survey_id=${encodeURIComponent(surveyId)}`),
                fetch('/api/v1/routes')
            ]);
            const cleanupTargets = operationsResponse.ok ? await operationsResponse.json() : [];
            const candidateRoute = routeResponse.ok ? await routeResponse.json() : null;
            latestRoute = candidateRoute && candidateRoute.survey_id === surveyId && candidateRoute.route_id ? candidateRoute : null;
            const pendingTargets = cleanupTargets.filter(target => target.status !== 'Cleanup Completed');
            document.getElementById('cleanup-targets-text').textContent = pendingTargets.length;
            const routeLabel = document.getElementById('cleanup-route-text');
            if (routeLabel) routeLabel.textContent = latestRoute ?
                `${latestRoute.status} · ${latestRoute.target_count} stops · Cleanup Route ${TarangUnits.formatDistance(TarangUnits.kmToNm(latestRoute.distance_km), latestRoute.distance_km)} · ~${latestRoute.estimated_operation_hours} h` :
                'No route generated';
            const statusEl = document.getElementById('cleanup-status-text');
            if (!cleanupTargets.length) {
                statusEl.textContent = 'Awaiting Decision';
                statusEl.className = 'text-xl font-bold font-mono text-slate-500 mt-1';
            } else if (!pendingTargets.length) {
                statusEl.textContent = 'Mission Accomplished';
                statusEl.className = 'text-xl font-bold font-mono text-emerald-600 mt-1';
            } else {
                statusEl.textContent = 'Active / Pending';
                statusEl.className = 'text-xl font-bold font-mono text-teal-700 mt-1';
            }
            const tbody = document.getElementById('cleanup-locations-tbody');
            if (!cleanupTargets.length) {
                tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-slate-500">No approved cleanup targets for this survey.</td></tr>';
                renderCleanupMap([], null);
                return;
            }
            const stopNumbers = new Map((latestRoute?.target_sequence || []).map(stop => [stop.target_id, stop.sequence]));
            const orderedTargets = [...cleanupTargets].sort((a, b) => (stopNumbers.get(a.target_id) || 9999) - (stopNumbers.get(b.target_id) || 9999));
            tbody.innerHTML = orderedTargets.map(target => {
                const stop = stopNumbers.get(target.target_id);
                const completed = target.status === 'Cleanup Completed';
                return `<tr class="hover:bg-slate-50"><td class="p-3 font-bold text-slate-700">${target.target_id.substring(0, 8)}</td><td class="p-3">${target.target_type || 'Unknown'}</td><td class="p-3 text-slate-500">${Number(target.latitude).toFixed(4)}, ${Number(target.longitude).toFixed(4)}</td><td class="p-3">${stop ? `<span class="font-bold text-sky-600">Stop #${stop}</span>` : '<span class="text-slate-400">Generate route</span>'}</td><td class="p-3"><span class="px-2 py-1 rounded text-xs font-bold ${completed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">${target.status}</span></td></tr>`;
            }).join('');
            renderCleanupMap(cleanupTargets, latestRoute);
            loadLatestOptimizedRoute(surveyId);
        }

        // --- Optimized Cleanup Route (POST /api/v1/hotspot-route, NM primary) ---
        let optimizedRouteMap = null;

        async function loadLatestOptimizedRoute(surveyId) {
            try {
                const response = await fetch('/api/v1/hotspot-route/latest');
                if (!response.ok) return;
                const payload = await response.json().catch(() => ({}));
                if (payload.status !== 'success' || !payload.route) return;
                const route = payload.route;
                if (route.survey_id && surveyId && route.survey_id !== surveyId) return;
                renderOptimizedCleanupRoute(route);
            } catch (error) {
                /* latest route is optional context */
            }
        }

        function renderOptimizedCleanupRoute(route) {
            const status = document.getElementById('marine-route-status');
            if (!route) {
                if (status) status.textContent = 'No cleanup route generated yet.';
                return;
            }
            status.className = 'px-4 pt-3 text-xs font-mono text-slate-500';
            status.textContent = `Cleanup Route ${route.route_id} · ${route.hotspot_count} hotspot(s) · TOTAL: ${TarangUnits.formatDistance(route.total_distance_nm, route.total_distance_km)}`;
            document.getElementById('cleanup-route-sequence').innerHTML = TarangRouteUI.sequenceHtml(route);
            if (!optimizedRouteMap) {
                optimizedRouteMap = new TarangMap('cleanupRouteMap', {
                    center: MAP_CONFIG.defaultCenter.slice(),
                    zoom: 6
                });
            }
            optimizedRouteMap.setCleanupRoute(route);
            setTimeout(() => {
                if (optimizedRouteMap && optimizedRouteMap.map) optimizedRouteMap.map.invalidateSize();
            }, 150);
        }

        async function generateOptimizedCleanupRoute() {
            const surveyId = document.getElementById('cleanup-survey-selector').value;
            const status = document.getElementById('marine-route-status');
            status.className = 'px-4 pt-3 text-xs font-mono text-slate-500';
            status.textContent = surveyId ?
                `Optimizing cleanup route for survey ${surveyId}…` :
                'Optimizing cleanup route from all persisted hotspots…';
            try {
                const response = await fetch('/api/v1/hotspot-route', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(surveyId ? {
                        survey_id: surveyId
                    } : {})
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) {
                    // Real server error (e.g. HTTP 409) — never a fake success.
                    status.className = 'px-4 pt-3 text-xs font-mono text-rose-600';
                    status.textContent = payload.message || `Cleanup route request failed (HTTP ${response.status}).`;
                    showToast(payload.message || 'Cleanup route could not be generated.', true);
                    return;
                }
                renderOptimizedCleanupRoute(payload.route);
                showToast(`Optimized cleanup route ${payload.route.route_id} generated — ${payload.route.hotspot_count} hotspot(s), ${TarangUnits.formatDistance(payload.route.total_distance_nm, payload.route.total_distance_km)}.`);
            } catch (error) {
                status.className = 'px-4 pt-3 text-xs font-mono text-rose-600';
                status.textContent = `Cleanup route request failed: ${error.message || error}`;
                showToast('Network error while optimizing the cleanup route.', true);
            }
        }

        // --- JSON downloads (authenticated fetch + Blob via TarangExport) ---
        async function marineDownloadJson(url, filename) {
            const result = await TarangExport.downloadJson(url, filename);
            if (result.ok) showToast(`Downloaded ${filename} from the Supabase-backed export endpoint.`);
            else showToast(`Download could not be authenticated: ${result.error}`, true);
        }

        function downloadHotspotJson() {
            const surveyId = document.getElementById('hotspot-survey-selector').value;
            const url = surveyId ? `/api/v1/export/hotspots.json?survey_id=${encodeURIComponent(surveyId)}` : '/api/v1/export/hotspots.json';
            marineDownloadJson(url, 'tarang_hotspots.json');
        }

        function downloadCleanupRouteJson() {
            const surveyId = document.getElementById('cleanup-survey-selector').value;
            const url = surveyId ? `/api/v1/export/cleanup-route.json?survey_id=${encodeURIComponent(surveyId)}` : '/api/v1/export/cleanup-route.json';
            marineDownloadJson(url, 'tarang_cleanup_route.json');
        }

        async function generateCleanupRoute() {
            const surveyId = document.getElementById('cleanup-survey-selector').value;
            if (!surveyId) return showToast('Select a survey before generating a route.', true);
            const response = await fetch('/api/v1/routes/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    survey_id: surveyId
                })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) return showToast(payload.message || 'No approved offshore cleanup targets are ready for routing.', true);
            showToast(`TSP route ${payload.route.route_id} generated from persisted offshore targets.`);
            await loadCleanupMissionForSurvey(surveyId);
        }

        function renderCleanupMap(targets, route) {
            if (!cleanupTarangMap) cleanupTarangMap = new TarangMap('marineMap', {
                center: MAP_CONFIG.defaultCenter,
                zoom: 11
            });
            if (!cleanupTarangMap || !cleanupTarangMap.map) return;
            cleanupTarangMap.clear();
            const mappedTargets = (targets || []).filter(target => target.latitude != null && target.longitude != null)
                .map(target => ({
                    ...target,
                    id: target.target_id,
                    title: target.target_type,
                    class_name: target.target_type,
                    verification_status: 'Verified'
                }));
            cleanupTarangMap.setDetections(mappedTargets);
            if (route && (route.target_sequence || []).length) {
                cleanupTarangMap.setTrack(route.target_sequence.map(stop => [Number(stop.latitude), Number(stop.longitude)]));
            }
            cleanupTarangMap.fitBounds();
            setTimeout(() => cleanupTarangMap.map.invalidateSize(), 100);
        }

        // --- Clearance Updates Tab ---
        function loadClearanceForSurvey(surveyId) {
            currentSurveyId = surveyId;
            const container = document.getElementById('clearance-content');

            if (!surveyId) {
                container.innerHTML = `<div class="text-center p-8 text-slate-500 font-mono text-xs"><span class="material-symbols-outlined text-slate-300 text-[48px] mb-3 block">inventory_2</span>Please select a survey above to load actionable cleanup targets.</div>`;
                return;
            }

            const sDets = globalDetections.filter(d => d.survey_id === surveyId && (d.verification_status || '').toLowerCase() === 'verified' && (d.detection_status || '') !== 'Rejected');
            // Verified targets remain here until the Marine Analyst explicitly
            // approves or declines cleanup.
            const cleanupTargets = sDets;

            if (cleanupTargets.length === 0) {
                container.innerHTML = `<div class="text-center p-8 text-slate-500 font-mono text-xs">No cleanup targets exist for this survey.</div>`;
                return;
            }

            let html = `
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start text-left">
            <div class="lg:col-span-5 bg-white p-5 rounded-xl shadow-sm border border-slate-200">
              <h3 class="font-bold text-slate-900 mb-4 border-b border-slate-100 pb-2">Log Recovery Operation</h3>
              <form id="clearance-form" onsubmit="handleClearanceSubmit(event)" class="flex flex-col gap-4 text-xs font-mono">
                <div>
                  <label class="block text-slate-500 mb-1">Target to Clear *</label>
                  <select id="clearance-target-id" required class="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:border-emerald-500 focus:outline-none">
                    <option value="">Select target...</option>
                    ${cleanupTargets.map(d => `<option value="${d.id}">${d.id.substring(0,8)} - ${d.class_name} (${d.clearance_status})</option>`).join('')}
                  </select>
                </div>
                <div>
                  <label class="block text-slate-500 mb-1">Clearance Status *</label>
                  <select id="clearance-status" required class="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:border-emerald-500 focus:outline-none">
                    <option value="Cleanup Approved">Accept Cleanup (Marine decision)</option>
                    <option value="Cleanup Not Recommended">Do Not Recommend Cleanup</option>
                    <option value="Cleanup Scheduled">Schedule Cleanup</option>
                    <option value="Cleanup In Progress">Start / Update Operation</option>
                    <option value="Cleanup Completed">Complete Cleanup</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-500 mb-1">Recovery Team</label>
                  <input type="text" id="clearance-team" value="Marine Response Fleet A" class="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:border-emerald-500 focus:outline-none" />
                </div>
                <div>
                  <label class="block text-slate-500 mb-1">Notes</label>
                  <textarea id="clearance-notes" rows="2" class="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:border-emerald-500 focus:outline-none"></textarea>
                </div>
                <button type="submit" class="w-full py-3 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 font-mono font-bold text-xs shadow-md transition-all">
                  Submit Recovery Record
                </button>
              </form>
            </div>
            
            <div class="lg:col-span-7 bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-4">
                  <h3 class="font-bold text-slate-900">Survey Clearance History</h3>
                  <button type="button" onclick="loadClearanceRecordsForSurvey('${surveyId}')" class="text-emerald-600 hover:text-emerald-800 underline font-mono text-xs">Refresh</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs font-mono">
                      <thead class="text-slate-400 border-b border-slate-200 bg-slate-50">
                        <tr>
                          <th class="p-2">Target ID</th>
                          <th class="p-2">Team</th>
                          <th class="p-2">Status</th>
                          <th class="p-2">Date</th>
                        </tr>
                      </thead>
                      <tbody id="survey-clearance-history" class="divide-y divide-slate-100">
                        <tr><td colspan="4" class="p-4 text-center text-slate-500">Loading history...</td></tr>
                      </tbody>
                    </table>
                </div>
            </div>
          </div>
        `;
            container.innerHTML = html;
            loadClearanceRecordsForSurvey(surveyId);
        }

        async function loadClearanceRecordsForSurvey(surveyId) {
            const tbody = document.getElementById('survey-clearance-history');
            if (!tbody) return;
            try {
                const res = await fetch('/api/v1/clearance');
                if (res.ok) {
                    const records = await res.json();
                    const sDets = globalDetections.filter(d => d.survey_id === surveyId).map(d => d.id);
                    const sRecords = records.filter(r => sDets.includes(r.target_id));

                    if (sRecords.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-slate-500">No clearance history found.</td></tr>`;
                    } else {
                        tbody.innerHTML = sRecords.map(r => `
                        <tr>
                            <td class="p-2 font-bold text-slate-700">${r.target_id ? r.target_id.substring(0,8) : 'N/A'}</td>
                            <td class="p-2">${r.team}</td>
                            <td class="p-2"><span class="px-2 py-1 rounded bg-slate-100 font-bold">${r.status}</span></td>
                            <td class="p-2 text-slate-500">${(r.clearance_date||'').split('T')[0]}</td>
                        </tr>
                    `).join('');
                    }
                }
            } catch (err) {
                tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-rose-500">Error loading history</td></tr>`;
            }
        }

        async function handleClearanceSubmit(e) {
            e.preventDefault();
            const targetId = document.getElementById('clearance-target-id').value;
            if (!targetId) return;

            const payload = {
                target_id: targetId,
                hotspot_id: '',
                team: document.getElementById('clearance-team').value,
                status: document.getElementById('clearance-status').value,
                notes: document.getElementById('clearance-notes').value,
                clearance_date: new Date().toISOString().split('T')[0]
            };

            try {
                const status = payload.status;
                let endpoint = `/api/v1/cleanup/${encodeURIComponent(targetId)}/action`;
                let action = status === 'Cleanup Approved' ? 'accept_cleanup' :
                    status === 'Cleanup Scheduled' ? 'schedule_cleanup' :
                    status === 'Cleanup In Progress' ? 'start_operation' :
                    status === 'Cleanup Completed' ? 'complete_cleanup' : null;
                let requestBody = action ? {
                    ...payload,
                    action
                } : {
                    cleanup_required: false,
                    notes: payload.notes
                };
                if (!action && status === 'Cleanup Approved') requestBody = {
                    cleanup_required: true,
                    notes: payload.notes
                };
                if (!action && status !== 'Cleanup Not Recommended') requestBody = {
                    ...payload,
                    action: 'update_progress'
                };
                if (!action && status === 'Cleanup Not Recommended') endpoint = `/api/v1/detections/${encodeURIComponent(targetId)}/cleanup-decision`;
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });

                if (res.ok) {
                    showToast('Clearance record submitted successfully');
                    const d = globalDetections.find(x => x.id === targetId);
                    if (d) {
                        d.clearance_status = status;
                        d.cleanup_status = status;
                    }

                    document.getElementById('clearance-notes').value = '';

                    if (currentSurveyId) {
                        loadClearanceRecordsForSurvey(currentSurveyId);
                        loadCleanupMissionForSurvey(currentSurveyId);
                    }
                    renderOverviewSurveys();
                } else {
                    showToast('Failed to submit clearance', true);
                }
            } catch (err) {
                showToast('Network error on submission', true);
            }
        }

        // --- Reports Tab ---
        function renderReportsTable() {
            const tbody = document.getElementById('reports-tbody');
            if (!tbody) return;

            if (allSurveys.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-slate-500">No survey data available for reports.</td></tr>`;
                return;
            }

            tbody.innerHTML = allSurveys.map(survey => {
                const sDets = globalDetections.filter(d => d.survey_id === survey.survey_id);
                const withCoords = sDets.filter(d => d.latitude && d.longitude);
                let centroid = "N/A";
                if (withCoords.length > 0) {
                    const avgLat = withCoords.reduce((sum, d) => sum + d.latitude, 0) / withCoords.length;
                    const avgLon = withCoords.reduce((sum, d) => sum + d.longitude, 0) / withCoords.length;
                    centroid = `${avgLat.toFixed(3)}&deg;, ${avgLon.toFixed(3)}&deg;`;
                }

                const cleanupReq = sDets.filter(d => (d.clearance_status || '').toLowerCase() !== 'no_cleanup_required' && (d.verification_status || '').toLowerCase() === 'verified');
                const cleared = cleanupReq.filter(d => (d.clearance_status || '').toLowerCase() === 'cleared');

                return `
                <tr class="hover:bg-slate-50">
                    <td class="p-3 font-bold text-slate-900">${survey.survey_name}</td>
                    <td class="p-3 text-slate-500">${survey.survey_id}</td>
                    <td class="p-3 font-mono text-slate-500">${centroid}</td>
                    <td class="p-3 font-bold">${sDets.length}</td>
                    <td class="p-3 text-slate-600">${cleared.length} / ${cleanupReq.length} Cleared</td>
                    <td class="p-3 text-right">
                        <button onclick="downloadReport('${survey.survey_id}')" class="text-white bg-slate-800 hover:bg-slate-900 px-3 py-1 rounded text-xs font-bold transition-colors">Download PDF</button>
                    </td>
                </tr>
            `;
            }).join('');
        }

        async function downloadReport(surveyId) {
            try {
                const response = await fetch(`/api/v1/surveys/${encodeURIComponent(surveyId)}/report`);
                if (!response.ok) throw new Error((await response.json().catch(() => ({}))).message || 'Report generation failed.');
                const report = await response.blob();
                if (!report.size) throw new Error('Report generation returned no data.');
                const link = document.createElement('a');
                link.href = URL.createObjectURL(report);
                link.download = `tarang_report_${surveyId}.pdf`;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(link.href);
                showToast('Report download started.');
            } catch (error) {
                showToast(error.message || 'Unable to download the selected report.', true);
            }
        }
    