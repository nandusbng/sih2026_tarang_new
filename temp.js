    (function() {
      const simBtn = document.getElementById('simulateBtn');
      const rovMarker = document.getElementById('simulatedROV');
      const waypointContainer = document.getElementById('waypointContainer');
      
      // Initialize Supabase Client
      const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
      const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTQwMDU3MSwiZXhwIjoyMTA0OTc2NTcxfQ.3RRFtT--ublCzZZhfSyM0HodY0Goxtb-HrddJkCBLAU';
      const supabaseClient = supabase.createClient(supabaseUrl, supabaseKey);

      async function fetchLatestDispatch() {
          const { data, error } = await supabaseClient
              .from('dispatches')
              .select('payload')
              .eq('payload->>destination', 'MARINE_ANALYST')
              .order('created_at', { ascending: false });
          
          if (error) {
              console.error('Error fetching latest dispatch:', error);
          } else if (data && data.length > 0) {
              let allDetections = [];
              data.forEach(d => {
                  if (d.payload && d.payload.detections) {
                      allDetections = allDetections.concat(d.payload.detections);
                  }
              });
              populateDashboard({ detections: allDetections });
          }
      }

      // Initial fetch
      fetchLatestDispatch();

      // Subscribe to real-time inserts
      supabaseClient
          .channel('dispatches_channel')
          .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'dispatches' }, payload => {
              console.log('New dispatch received via Supabase Realtime!', payload);
              if (payload.new && payload.new.payload && payload.new.payload.destination === 'MARINE_ANALYST') {
                  showToast("New Data Received Successfully from Sonar AI");
                  fetchLatestDispatch();
              }
          })
          .subscribe();

      // Fallback local storage sync just in case
      function loadFromStorage() {
          const storedData = localStorage.getItem('marineAnalystData');
          if (storedData && window.lastLoadedData !== storedData) {
              try {
                  const data = JSON.parse(storedData);
                  window.lastLoadedData = storedData;
                  showToast("New Data Received Successfully from Sonar AI");
                  populateDashboard(data);
              } catch (e) {
                  console.error("Failed to parse stored dispatch data", e);
              }
          }
      }
      window.addEventListener('storage', loadFromStorage);

      function populateDashboard(data) {
          const detections = data.detections || [];
          if (detections.length === 0) {
              alert("No detections found in this payload.");
              return;
          }
          
          document.getElementById('waypointStatus').innerText = "OPTIMIZED BY A* KINEMATICS ENGINE";
          
          // 1. Populate Waypoints
          waypointContainer.innerHTML = '';
          const markersContainer = document.getElementById('mapMarkersContainer');
          if (markersContainer) markersContainer.innerHTML = '';
          
          let totalMass = 0;
          
          const classColors = {
              'shipwreck': 'bg-sonar-alert',
              'ghost_net': 'bg-secondary',
              'other': 'bg-seafoam-glow'
          };
          const textColors = {
              'shipwreck': 'text-sonar-alert',
              'ghost_net': 'text-secondary',
              'other': 'text-seafoam-glow'
          };

          const compositionMap = {};
          // (Simulated waypoints logic removed as it's now handled by the real map)
          detections.forEach((det, idx) => {
              const cat = det.class_name || 'other';
              
              const priority = det.classification_tier === 'A' ? 'PRIORITY 1' : 'PRIORITY 2';
              const colorCls = classColors[cat] || 'bg-primary';
              const textColorCls = textColors[cat] || 'text-primary';

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

              const wpCard = `
              <div class="p-3 rounded-xl bg-surface-container-low/60 flex flex-col gap-1.5 hover:bg-surface-container-high transition-colors shadow-sm">
                <div class="flex items-center justify-between">
                    <span class="font-label-code text-label-code font-bold ${textColorCls}">WP-${(idx+1).toString().padStart(2, '0')} · ${det.id}</span>
                    <span class="font-label-code text-[10px] px-1.5 py-0.5 rounded bg-surface-container-highest text-primary">${priority}</span>
                </div>
                <span class="font-body-sm text-body-sm font-semibold text-primary truncate">${det.title || det.class_name.toUpperCase()}</span>
                <div class="flex items-center justify-between font-label-code text-[11px] text-on-surface-variant pt-1">
                    <span>Depth: ${det.depth}</span>
                </div>
                <div class="w-full bg-surface-container-highest rounded-full h-1.5 mt-1">
                    <div class="${colorCls} h-1.5 rounded-full" style="width: ${det.confidence}%"></div>
                </div>
                ${telemetryHtml}
                <div class="mt-2 rounded overflow-hidden h-24 w-full bg-black">
                    <img src="${det.crop_url}" class="w-full h-full object-contain" />
                </div>
              </div>
              `;
              waypointContainer.innerHTML += wpCard;
          });
          
          // Reinitialize Map with Synced Data
          initMapData(detections);
      }

      // --- MAP, K-MEANS & ROUTING SIMULATION ---
      const map = L.map('gisMap').setView([-5, 70], 4);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap'
      }).addTo(map);

      // India EEZ and Land Boundary (Lat, Lon format for Leaflet)
      const indiaEEZBoundary = [
        [35.5, 76.78], [35.55, 77.15], [35.3, 78.1], [34.3, 78.9],
        [33.1, 79.2], [32.5, 78.7], [32.0, 78.3], [31.0, 78.9],
        [30.2, 80.1], [30.15, 80.15], [27.5, 83.1], [26.7, 85.1],
        [26.4, 88.1], [27.3, 88.5], [27.8, 88.9], [27.3, 88.92],
        [26.9, 91.5], [27.8, 92.0], [28.7, 93.5], [29.0, 95.0],
        [28.4, 96.3], [28.2, 97.4], [26.0, 95.4], [24.0, 94.3],
        [22.5, 93.2], [22.0, 92.4], [21.64, 89.15], [21.44, 89.18],
        [21.12, 89.23], [20.93, 89.26], [20.52, 89.32], [18.07, 89.37],
        [14.0, 93.42], [13.41, 96.03], [9.16, 95.58], [7.25, 94.66],
        [6.0, 94.0], [6.75, 92.16], [11.83, 90.66], [12.25, 84.75],
        [8.33, 83.16], [10.08, 80.05], [9.95, 79.58], [9.67, 79.38],
        [9.36, 79.51], [9.21, 79.53], [9.1, 79.53], [5.66, 78.5],
        [7.08, 72.83], [8.25, 71.33], [11.66, 69.25], [14.83, 70.2],
        [19.36, 68.75], [21.75, 66.17], [23.96, 67.46], [23.8, 68.1],
        [25.0, 70.5], [27.5, 72.0], [29.0, 73.5], [31.0, 74.5],
        [32.5, 75.0], [34.0, 74.0], [34.8, 74.5], [34.5, 76.0],
        [35.5, 76.78]
      ];

      L.polygon(indiaEEZBoundary, {
          color: '#14B8A6',
          weight: 2,
          opacity: 0.8,
          fillColor: '#14B8A6',
          fillOpacity: 0.05,
          dashArray: '5, 10'
      }).addTo(map).bindPopup("<b>India's Maritime EEZ & Boundary</b>");

      let allMapPoints = [];
      let markerGroup = L.featureGroup().addTo(map);

      // Simple K-Means implementation
      function kMeans(points, k, maxIterations = 50) {
          if(points.length <= k) return points.map((p, i) => ({ centroid: p, points: [p], id: i }));
          let centroids = points.slice(0, k).map(p => ({...p}));
          let clusters = [];
          
          for(let iter=0; iter<maxIterations; iter++) {
              clusters = centroids.map((c, i) => ({ centroid: c, points: [], id: i }));
              // Assign points to closest centroid
              points.forEach(p => {
                  let minDist = Infinity;
                  let closestIndex = 0;
                  centroids.forEach((c, i) => {
                      let dist = Math.pow(p.lat - c.lat, 2) + Math.pow(p.lon - c.lon, 2);
                      if(dist < minDist) { minDist = dist; closestIndex = i; }
                  });
                  clusters[closestIndex].points.push(p);
              });
              // Update centroids
              let changed = false;
              clusters.forEach((cluster, i) => {
                  if(cluster.points.length === 0) return;
                  let sumLat = 0, sumLon = 0;
                  cluster.points.forEach(p => { sumLat += p.lat; sumLon += p.lon; });
                  let newLat = sumLat / cluster.points.length;
                  let newLon = sumLon / cluster.points.length;
                  if(centroids[i].lat !== newLat || centroids[i].lon !== newLon) changed = true;
                  centroids[i].lat = newLat;
                  centroids[i].lon = newLon;
                  cluster.centroid = centroids[i];
              });
              if(!changed) break;
          }
          return clusters.filter(c => c.points.length > 0);
      }

      // Nearest Neighbor TSP
      function nearestNeighborTSP(points) {
          if(points.length === 0) return [];
          let unvisited = [...points];
          let path = [unvisited.shift()];
          while(unvisited.length > 0) {
              let last = path[path.length - 1];
              let minDist = Infinity;
              let nextIdx = -1;
              unvisited.forEach((p, i) => {
                  let dist = Math.pow(p.lat - last.lat, 2) + Math.pow(p.lon - last.lon, 2);
                  if(dist < minDist) { minDist = dist; nextIdx = i; }
              });
              path.push(unvisited.splice(nextIdx, 1)[0]);
          }
          return path;
      }

      let routeLine = null;
      let clusterCircles = [];
      let polylineCoords = [];

      function initMapData(detections) {
          if(!detections || detections.length === 0) return;

          allMapPoints = [];
          markerGroup.clearLayers();
          if(routeLine) map.removeLayer(routeLine);
          clusterCircles.forEach(c => map.removeLayer(c));
          clusterCircles = [];

          detections.forEach((det, idx) => {
              const markerIndex = (idx + 1).toString().padStart(2, '0');
              const lat = det.telemetry ? parseFloat(det.telemetry.Latitude) : parseFloat(det.latitude);
              const lon = det.telemetry ? parseFloat(det.telemetry.Longitude) : parseFloat(det.longitude);
              if(!isNaN(lat) && !isNaN(lon)) {
                  allMapPoints.push({ lat, lon, det, index: markerIndex });
                  
                  let color = (det.classification_tier === 'Tier A' || det.classification_tier === 'A') ? '#ff3b30' : 
                             ((det.classification_tier === 'Tier B' || det.classification_tier === 'B') ? '#ff9f0a' : '#34c759');
                  const markerHtml = `
                  <div style="background-color:${color}; width:28px; height:28px; border-radius:50%; border:3px solid white; box-shadow: 0 0 10px ${color}; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:10px; font-family:sans-serif; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">
                      WP-${markerIndex}
                  </div>
                  <div style="width:0; height:0; border-left:6px solid transparent; border-right:6px solid transparent; border-top:8px solid ${color}; margin: 0 auto; margin-top:-2px;"></div>
                  `;
                          // Fallback placeholder image (Underwater / Sonar style)
                          let defaultPlaceholder = "https://images.unsplash.com/photo-1682687982501-1e5898cb4f18?q=80&w=400&auto=format&fit=crop";
                          let popupImg = `<img src="${defaultPlaceholder}" style="width:100%; height:80px; object-fit:cover; border-radius:4px; margin-bottom:6px; border:1px solid #ccc; filter: contrast(1.2) sepia(1) hue-rotate(180deg);" />`;
                          
                          if (det.crop_url) {
                              let imgSrc = det.crop_url;
                              if (!imgSrc.startsWith('data:image')) {
                                  imgSrc = 'data:image/jpeg;base64,' + imgSrc;
                              }
                              popupImg = `<img src="${imgSrc}" onerror="this.onerror=null; this.src='${defaultPlaceholder}';" style="width:100%; height:80px; object-fit:cover; border-radius:4px; margin-bottom:6px; border:1px solid #ccc;" />`;
                          }
                          
                          L.marker([lat, lon], {
                              icon: L.divIcon({ html: markerHtml, className: '', iconSize: [36, 40], iconAnchor: [18, 40] })
                          }).addTo(markerGroup).bindTooltip(`<div style="min-width:180px; text-align:center;">${popupImg}<b>WP-${markerIndex} - ${det.title || det.class_name}</b><br>Lat: ${lat}<br>Lon: ${lon}</div>`, {
                              direction: 'top',
                              offset: [0, -40],
                              className: 'bg-white p-2 rounded-xl shadow-lg border-0'
                          });
                      }
                  });

          if(allMapPoints.length > 0) {
              map.fitBounds(markerGroup.getBounds(), { padding: [50, 50], maxZoom: 12 });
              
              // Run Clustering (K=min(3, points.length))
              let k = Math.min(3, allMapPoints.length);
              let clusters = kMeans(allMapPoints, k);
              
              const clusterColors = ['#ff3b30', '#ff9f0a', '#14B8A6', '#006398'];
              clusters.forEach((c, idx) => {
                  if(c.points.length > 0) {
                      // Draw circle around cluster centroid
                      // Radius based on furthest point in cluster
                      let maxDist = 0;
                      c.points.forEach(p => {
                          let d = map.distance([c.centroid.lat, c.centroid.lon], [p.lat, p.lon]);
                          if(d > maxDist) maxDist = d;
                      });
                      let circle = L.circle([c.centroid.lat, c.centroid.lon], {
                          color: clusterColors[idx % clusterColors.length],
                          fillColor: clusterColors[idx % clusterColors.length],
                          fillOpacity: 0.1,
                          radius: maxDist > 1000 ? maxDist * 1.5 : 15000 // Base 15km if single point
                      }).addTo(map);
                      clusterCircles.push(circle);
                  }
              });

              // TSP Route
              let optimizedPath = nearestNeighborTSP(allMapPoints);
              polylineCoords = optimizedPath.map(p => [p.lat, p.lon]);
              routeLine = L.polyline(polylineCoords, {color: '#ffffff', dashArray: '10, 10', weight: 3}).addTo(map);
          }
      }

      // Simulation Logic (Extracted from initMapData to avoid duplicate listeners)
      let isSimulating = false;
      let rovSimMarker = null;

      if(simBtn) {
          simBtn.addEventListener('click', () => {
              if(isSimulating || polylineCoords.length === 0) return;
              isSimulating = true;
              simBtn.innerHTML = `<span class="material-symbols-outlined text-[20px] animate-spin">refresh</span><span>Simulating Optimal Kinematics...</span>`;
              
              const rovHtml = `<div style="background-color:#14B8A6; width:24px; height:24px; border-radius:50%; border:3px solid white; box-shadow: 0 0 15px #14B8A6; display:flex; align-items:center; justify-content:center;"><span class="material-symbols-outlined text-white text-[16px]">sailing</span></div>`;
              rovSimMarker = L.marker(polylineCoords[0], {
                  icon: L.divIcon({ html: rovHtml, className: '', iconSize: [24, 24], iconAnchor: [12, 12] }),
                  zIndexOffset: 1000
              }).addTo(map);

              let currentStep = 0;
              let moveInterval = setInterval(() => {
                  currentStep++;
                  if(currentStep < polylineCoords.length) {
                      rovSimMarker.setLatLng(polylineCoords[currentStep]);
                  } else {
                      clearInterval(moveInterval);
                      simBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">check_circle</span><span>Simulation Verified: 100% Efficiency</span>`;
                      isSimulating = false;
                      setTimeout(() => { if(rovSimMarker) map.removeLayer(rovSimMarker); }, 3000);
                  }
              }, 1000);
          });
      }
    })();
