import re

with open('operator-portal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate the <script> block at the end of the file
script_start = content.find('<script>')
# Find the second script tag which is the main application script (first is tailwind)
script_matches = [m.start() for m in re.finditer(r'<script>', content)]
print(f"Total <script> tags found: {len(script_matches)}")

# Let's inspect the last script tag content
last_script_idx = script_matches[-1]

new_script_code = """<script>
    let currentSurvey = null;
    let allSurveys = [];
    let allDetections = [];
    let activeTarangMap = null;

    // =========================================================================
    // 1. NAVIGATION & VIEW SWITCHING
    // =========================================================================
    function switchView(viewKey) {
      const navButtons = document.querySelectorAll('.nav-btn');
      navButtons.forEach(btn => {
        if (btn.getAttribute('data-view') === viewKey) {
          btn.className = "nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wide transition-all bg-teal-600 text-white shadow-sm";
        } else {
          btn.className = "nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100";
        }
      });

      const panels = document.querySelectorAll('.view-panel');
      panels.forEach(p => p.classList.add('hidden'));

      const targetPanel = document.getElementById(`view-${viewKey}`);
      if (targetPanel) {
        targetPanel.classList.remove('hidden');
      }

      const sidebar = document.getElementById('portal-sidebar');
      if (sidebar) {
        sidebar.classList.add('-translate-x-full');
      }

      // View Initializers
      if (viewKey === 'active-mission') {
        init3DDroneSimulation();
        initActiveMissionMap();
      } else if (viewKey === 'surveys') {
        loadSurveys();
      } else if (viewKey === 'results') {
        loadResults();
      } else if (viewKey === 'verification-queue') {
        loadVerificationQueue();
      } else if (viewKey === 'notifications') {
        loadNotifications();
      } else if (viewKey === 'documents') {
        loadDocuments();
      } else if (viewKey === 'reports') {
        loadReportsView();
      } else if (viewKey === 'new-survey') {
        regenerateSurveyId();
      }
    }

    function toggleSidebar() {
      const sidebar = document.getElementById('portal-sidebar');
      if (sidebar) sidebar.classList.toggle('-translate-x-full');
    }

    function toggleAccountMenu() {
      const menu = document.getElementById('account-menu');
      if (menu) menu.classList.toggle('hidden');
    }

    function showToast(msg, icon='check_circle') {
      const toast = document.getElementById('toast');
      const toastMsg = document.getElementById('toast-msg');
      const toastIcon = document.getElementById('toast-icon');
      if (!toast) return;
      toastMsg.textContent = msg;
      toastIcon.textContent = icon;
      toast.classList.remove('translate-y-12', 'opacity-0', 'pointer-events-none');
      setTimeout(() => {
        toast.classList.add('translate-y-12', 'opacity-0', 'pointer-events-none');
      }, 3500);
    }

    // =========================================================================
    // 2. THREE.JS 3D DRONE SURVEY PLATFORM SIMULATION (drone.glb)
    // =========================================================================
    let threeScene, threeCamera, threeRenderer, threeDrone, threeControls;
    let is3DInitialized = false;
    let simRunning = false;
    let simStep = 0;
    let simTimer = null;

    const SURVEY_WAYPOINTS = [
      { lat: 13.0827, lon: 80.2707, heading: 45, depth: 34.2, alt: 8.4, dist: 0.0, speed: 3.4 },
      { lat: 13.0855, lon: 80.2735, heading: 45, depth: 35.1, alt: 8.2, dist: 0.42, speed: 3.5 },
      { lat: 13.0880, lon: 80.2760, heading: 90, depth: 36.4, alt: 8.0, dist: 0.86, speed: 3.2 },
      { lat: 13.0882, lon: 80.2800, heading: 135, depth: 37.0, alt: 7.9, dist: 1.30, speed: 3.4 },
      { lat: 13.0850, lon: 80.2830, heading: 180, depth: 38.2, alt: 8.1, dist: 1.75, speed: 3.3 },
      { lat: 13.0815, lon: 80.2832, heading: 225, depth: 39.0, alt: 8.3, dist: 2.20, speed: 3.5 },
      { lat: 13.0780, lon: 80.2800, heading: 270, depth: 38.5, alt: 8.5, dist: 2.65, speed: 3.4 },
      { lat: 13.0782, lon: 80.2750, heading: 315, depth: 37.1, alt: 8.2, dist: 3.10, speed: 3.3 },
      { lat: 13.0820, lon: 80.2715, heading: 0, depth: 35.8, alt: 8.0, dist: 3.55, speed: 3.4 },
      { lat: 13.0860, lon: 80.2718, heading: 45, depth: 36.2, alt: 8.1, dist: 4.00, speed: 3.5 },
      { lat: 13.0890, lon: 80.2750, heading: 90, depth: 37.5, alt: 8.0, dist: 4.45, speed: 3.4 },
      { lat: 13.0892, lon: 80.2820, heading: 120, depth: 38.0, alt: 8.2, dist: 5.00, speed: 3.4 }
    ];

    function init3DDroneSimulation() {
      const container = document.getElementById('drone-3d-viewport');
      if (!container || is3DInitialized) return;

      const width = container.clientWidth || 700;
      const height = container.clientHeight || 380;

      // 1. Scene & Underwater Atmospheric Fog
      threeScene = new THREE.Scene();
      threeScene.background = new THREE.Color(0x071e3d);
      threeScene.fog = new THREE.FogExp2(0x071e3d, 0.035);

      // 2. Camera
      threeCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
      threeCamera.position.set(0, 4, 8);

      // 3. Renderer
      threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      threeRenderer.setSize(width, height);
      threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      threeRenderer.shadowMap.enabled = true;
      container.appendChild(threeRenderer.domElement);

      // 4. OrbitControls
      if (typeof THREE.OrbitControls !== 'undefined') {
        threeControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
        threeControls.enableDamping = true;
        threeControls.dampingFactor = 0.05;
        threeControls.maxPolarAngle = Math.PI / 2 - 0.05;
      }

      // 5. Lighting
      const ambientLight = new THREE.AmbientLight(0x14b8a6, 0.9);
      threeScene.add(ambientLight);

      const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
      dirLight.position.set(5, 12, 7);
      threeScene.add(dirLight);

      const waterLight = new THREE.PointLight(0x38bdf8, 1.5, 30);
      waterLight.position.set(0, 6, 0);
      threeScene.add(waterLight);

      // 6. Seabed Terrain (Textured/Wireframe plane)
      const seabedGeo = new THREE.PlaneGeometry(60, 60, 40, 40);
      const pos = seabedGeo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const vx = pos.getX(i);
        const vy = pos.getY(i);
        pos.setZ(i, Math.sin(vx * 0.3) * Math.cos(vy * 0.3) * 0.6);
      }
      seabedGeo.computeVertexNormals();

      const seabedMat = new THREE.MeshStandardMaterial({
        color: 0x03254c,
        roughness: 0.85,
        wireframe: false,
        flatShading: true
      });
      const seabed = new THREE.Mesh(seabedGeo, seabedMat);
      seabed.rotation.x = -Math.PI / 2;
      seabed.position.y = -2;
      threeScene.add(seabed);

      // 7. Ambient Particle Marine Dust / Bubbles
      const particleGeo = new THREE.BufferGeometry();
      const particleCount = 150;
      const pPositions = new Float32Array(particleCount * 3);
      for (let i = 0; i < particleCount * 3; i += 3) {
        pPositions[i] = (Math.random() - 0.5) * 30;
        pPositions[i + 1] = Math.random() * 8 - 2;
        pPositions[i + 2] = (Math.random() - 0.5) * 30;
      }
      particleGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
      const particleMat = new THREE.PointsMaterial({
        color: 0x5eead4,
        size: 0.12,
        transparent: true,
        opacity: 0.6
      });
      const particles = new THREE.Points(particleGeo, particleMat);
      threeScene.add(particles);

      // 8. Load Real drone.glb Model
      const spinner = document.getElementById('drone-loader-spinner');
      const loader = new THREE.GLTFLoader();

      loader.load(
        'static/models/drone.glb',
        (gltf) => {
          threeDrone = gltf.scene;
          threeDrone.scale.set(0.8, 0.8, 0.8);
          threeDrone.position.set(0, 0.5, 0);
          threeScene.add(threeDrone);
          if (spinner) spinner.classList.add('hidden');
          console.log("Successfully loaded local static/models/drone.glb into 3D scene!");
        },
        undefined,
        (err) => {
          console.warn("GLTFLoader fallback for static/models/drone.glb:", err);
          // Procedural AUV Fallback geometry so simulation is 100% rock-solid
          const auvGroup = new THREE.Group();
          const bodyGeo = new THREE.CylinderGeometry(0.4, 0.4, 2.5, 16);
          const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.5, roughness: 0.3 });
          const body = new THREE.Mesh(bodyGeo, bodyMat);
          body.rotation.z = Math.PI / 2;
          auvGroup.add(body);

          const noseGeo = new THREE.SphereGeometry(0.4, 16, 16);
          const noseMat = new THREE.MeshStandardMaterial({ color: 0x0d9488 });
          const nose = new THREE.Mesh(noseGeo, noseMat);
          nose.position.x = 1.25;
          auvGroup.add(nose);

          const finGeo = new THREE.BoxGeometry(0.1, 0.8, 0.6);
          const finMat = new THREE.MeshStandardMaterial({ color: 0x0f172a });
          const fin = new THREE.Mesh(finGeo, finMat);
          fin.position.x = -1.0;
          auvGroup.add(fin);

          threeDrone = auvGroup;
          threeDrone.position.set(0, 0.5, 0);
          threeScene.add(threeDrone);
          if (spinner) spinner.classList.add('hidden');
        }
      );

      // Render Loop
      function animate() {
        requestAnimationFrame(animate);
        if (threeControls) threeControls.update();

        // Subtle idle bobbing & propeller spin
        if (threeDrone) {
          if (simRunning) {
            threeDrone.position.y = 0.5 + Math.sin(Date.now() * 0.003) * 0.15;
            threeDrone.rotation.y += 0.005;
          } else {
            threeDrone.position.y = 0.5 + Math.sin(Date.now() * 0.001) * 0.05;
          }
        }

        // Drift particles
        const pPos = particles.geometry.attributes.position.array;
        for (let i = 1; i < particleCount * 3; i += 3) {
          pPos[i] += 0.01;
          if (pPos[i] > 6) pPos[i] = -2;
        }
        particles.geometry.attributes.position.needsUpdate = true;

        threeRenderer.render(threeScene, threeCamera);
      }
      animate();

      window.addEventListener('resize', () => {
        if (!container || !threeRenderer || !threeCamera) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        threeCamera.aspect = w / h;
        threeCamera.updateProjectionMatrix();
        threeRenderer.setSize(w, h);
      });

      is3DInitialized = true;
    }

    function startSurveySimulation() {
      simRunning = true;
      document.getElementById('sim-status-pill').textContent = 'SURVEY ACTIVE';
      document.getElementById('sim-status-pill').className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-100 text-teal-800 border border-teal-200';
      document.getElementById('telemetry-state').textContent = 'SURVEY IN PROGRESS';

      document.getElementById('btn-start-survey').classList.add('opacity-50', 'pointer-events-none');
      document.getElementById('btn-stop-survey').classList.remove('opacity-50', 'pointer-events-none');

      if (simTimer) clearInterval(simTimer);

      simTimer = setInterval(() => {
        if (!simRunning) return;

        simStep = (simStep + 1) % SURVEY_WAYPOINTS.length;
        const wp = SURVEY_WAYPOINTS[simStep];

        // Update Telemetry Panel
        document.getElementById('telemetry-lat').textContent = `${wp.lat.toFixed(4)}°N`;
        document.getElementById('telemetry-lon').textContent = `${wp.lon.toFixed(4)}°E`;
        document.getElementById('telemetry-heading').textContent = `${String(wp.heading).padStart(3, '0')}°`;
        document.getElementById('telemetry-speed').textContent = `${wp.speed.toFixed(1)} knots`;
        document.getElementById('telemetry-altitude').textContent = `${wp.alt.toFixed(1)} m`;
        document.getElementById('telemetry-depth').textContent = `${wp.depth.toFixed(1)} m`;
        document.getElementById('telemetry-distance').textContent = `${wp.dist.toFixed(2)} km`;
        document.getElementById('telemetry-coverage').textContent = `${(wp.dist * 0.22).toFixed(2)} km²`;

        const pct = Math.round(((simStep + 1) / SURVEY_WAYPOINTS.length) * 100);
        document.getElementById('telemetry-progress-pct').textContent = `${pct}%`;
        document.getElementById('telemetry-progress-bar').style.width = `${pct}%`;
        document.getElementById('sim-waypoint-counter').textContent = `Waypoint: ${simStep + 1} / ${SURVEY_WAYPOINTS.length}`;

        // Synchronize with Leaflet Map
        if (activeTarangMap) {
          activeTarangMap.setPlatformPosition(wp.lat, wp.lon, wp.heading);
        }

        if (simStep === SURVEY_WAYPOINTS.length - 1) {
          stopSurveySimulation();
          showToast("Survey pattern completed. Telemetry archived.", "task_alt");
        }
      }, 1500);

      showToast("Autonomous survey activated: drone.glb navigating sector.", "navigation");
    }

    function stopSurveySimulation() {
      simRunning = false;
      if (simTimer) clearInterval(simTimer);
      document.getElementById('sim-status-pill').textContent = 'SURVEY PAUSED';
      document.getElementById('sim-status-pill').className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-200';
      document.getElementById('telemetry-state').textContent = 'SURVEY PAUSED';

      document.getElementById('btn-start-survey').classList.remove('opacity-50', 'pointer-events-none');
      document.getElementById('btn-stop-survey').classList.add('opacity-50', 'pointer-events-none');
      showToast("Survey simulation paused. Telemetry frozen.", "pause");
    }

    function resetSurveySimulation() {
      stopSurveySimulation();
      simStep = 0;
      const wp = SURVEY_WAYPOINTS[0];
      document.getElementById('telemetry-lat').textContent = `${wp.lat.toFixed(4)}°N`;
      document.getElementById('telemetry-lon').textContent = `${wp.lon.toFixed(4)}°E`;
      document.getElementById('telemetry-heading').textContent = `${String(wp.heading).padStart(3, '0')}°`;
      document.getElementById('telemetry-speed').textContent = '0.0 knots';
      document.getElementById('telemetry-distance').textContent = '0.00 km';
      document.getElementById('telemetry-coverage').textContent = '0.00 km²';
      document.getElementById('telemetry-progress-pct').textContent = '0%';
      document.getElementById('telemetry-progress-bar').style.width = '0%';
      document.getElementById('sim-status-pill').textContent = 'STANDBY';
      document.getElementById('sim-status-pill').className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200';
      document.getElementById('telemetry-state').textContent = 'STANDBY';
      document.getElementById('sim-waypoint-counter').textContent = 'Waypoint: 0 / 12';

      if (activeTarangMap) {
        activeTarangMap.setPlatformPosition(wp.lat, wp.lon, wp.heading);
      }
      showToast("Survey reset to waypoint 0.");
    }

    // =========================================================================
    // 3. MAP INTEGRATION (TarangMap)
    // =========================================================================
    function initActiveMissionMap() {
      if (!activeTarangMap) {
        activeTarangMap = new TarangMap('active-mission-map', {
          center: [13.0827, 80.2707],
          zoom: 13
        });
      }

      // Draw survey track
      const trackCoords = SURVEY_WAYPOINTS.map(wp => [wp.lat, wp.lon]);
      activeTarangMap.setTrack(trackCoords);
      activeTarangMap.setPlatformPosition(SURVEY_WAYPOINTS[0].lat, SURVEY_WAYPOINTS[0].lon);

      // Load any recorded detections and clusters from backend
      fetch('/api/v1/surveys/all/detections')
        .then(r => r.json())
        .then(dets => {
          if (dets && dets.length > 0) {
            activeTarangMap.setDetections(dets);
          }
        }).catch(() => {});

      fetch('/api/v1/clusters')
        .then(r => r.json())
        .then(clusters => {
          if (clusters && clusters.clusters && clusters.clusters.length > 0) {
            activeTarangMap.setClusters(clusters);
          }
        }).catch(() => {});
    }

    // =========================================================================
    // 4. SURVEY DATA INITIALIZATION & SUBMISSIONS
    // =========================================================================
    function regenerateSurveyId() {
      const el = document.getElementById('input-survey-id');
      if (el) {
        const rand = Math.floor(1000 + Math.random() * 9000);
        el.value = `TRG-2026-SRV-${rand}`;
      }
    }

    // Survey Form Submit
    const sForm = document.getElementById('new-survey-form');
    if (sForm) {
      sForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const surveyName = document.getElementById('input-survey-name').value;
        const surveyId = document.getElementById('input-survey-id').value;
        const region = document.getElementById('input-survey-region').value;
        const specificArea = document.getElementById('input-survey-area').value;
        const platform = document.querySelector('input[name="platform-choice"]:checked')?.value || 'AUV';

        try {
          const response = await fetch('/api/v1/surveys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              survey_id: surveyId,
              survey_name: surveyName,
              region: region,
              specific_area: specificArea,
              platform: platform
            })
          });

          if (response.ok) {
            showToast(`Survey ${surveyId} registered. Proceeding to Upload.`);
            document.getElementById('upload-survey-context').textContent = `SURVEY: ${surveyId}`;
            currentSurvey = { survey_id: surveyId, survey_name: surveyName, region: region, specific_area: specificArea, platform: platform };
            switchView('data-input');
          } else {
            showToast("Failed to create survey record on server.", "error");
          }
        } catch (err) {
          showToast("Local survey initialized.", "info");
          switchView('data-input');
        }
      });
    }

    // Survey File Upload Handler (XTF & TXT & Images)
    async function handleSurveyFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const progressBox = document.getElementById('upload-progress-box');
      const progressBar = document.getElementById('upload-progress-bar');
      const progressPct = document.getElementById('upload-pct');
      const progressName = document.getElementById('upload-filename');
      const progressStatus = document.getElementById('upload-status-text');

      if (progressBox) progressBox.classList.remove('hidden');
      if (progressName) progressName.textContent = file.name;
      if (progressBar) progressBar.style.width = '30%';
      if (progressPct) progressPct.textContent = '30%';
      if (progressStatus) progressStatus.textContent = 'Uploading to TARANG backend...';

      const formData = new FormData();
      formData.append('file', file);
      if (currentSurvey && currentSurvey.survey_id) {
        formData.append('survey_id', currentSurvey.survey_id);
      }

      const isTxt = file.name.toLowerCase().endsWith('.txt');
      const endpoint = isTxt ? '/api/v1/txt/upload' : '/api/v1/xtf/upload';

      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          body: formData
        });

        if (progressBar) progressBar.style.width = '100%';
        if (progressPct) progressPct.textContent = '100%';

        if (res.ok) {
          const data = await res.json();
          if (progressStatus) progressStatus.textContent = 'Upload & Parsing Complete!';
          showToast(isTxt ? "TXT Metadata parsed & archived." : "Sonar survey ingested & inference complete!", "check_circle");
          setTimeout(() => {
            switchView('results');
          }, 1200);
        } else {
          const err = await res.json().catch(() => ({}));
          if (progressStatus) progressStatus.textContent = `Upload error: ${err.error || 'Server rejected file'}`;
          showToast(err.error || "File processing error", "error");
        }
      } catch (e) {
        console.error("Upload error:", e);
        if (progressStatus) progressStatus.textContent = "Network error during upload.";
        showToast("Upload failed. Verify backend server.", "error");
      }
    }

    // =========================================================================
    // 5. EXISTING SURVEYS ARCHIVE
    // =========================================================================
    async function loadSurveys() {
      const tbody = document.getElementById('surveys-table-body');
      if (!tbody) return;
      tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-slate-400 font-mono text-xs">Loading survey catalog from database...</td></tr>';

      try {
        const res = await fetch('/api/v1/surveys');
        if (res.ok) {
          allSurveys = await res.json();
          renderSurveysTable(allSurveys);
          const dashCount = document.getElementById('dash-existing-count');
          if (dashCount) dashCount.textContent = `${allSurveys.length} ARCHIVES`;
          return;
        }
      } catch (e) {
        console.error("Error loading surveys:", e);
      }

      tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-slate-400 font-mono text-xs">No surveys created yet.</td></tr>';
    }

    function renderSurveysTable(surveys) {
      const tbody = document.getElementById('surveys-table-body');
      if (!tbody) return;

      if (!surveys || surveys.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-slate-400 font-mono text-xs">No surveys created yet.</td></tr>';
        return;
      }

      tbody.innerHTML = surveys.map(s => {
        const sId = s.survey_id;
        const sName = s.survey_name || 'Hydrographic Survey';
        const region = s.region || s.location_name || 'Offshore Sector';
        const area = s.specific_area || 'Sector 1';
        const dateStr = (s.created_at || s.survey_date || '').substring(0, 10);
        const platform = s.platform || 'AUV';
        const status = s.status || 'ACTIVE';

        return `
          <tr class="hover:bg-slate-50 transition-colors cursor-pointer border-b border-slate-100" onclick="openSurveyDetails('${sId}')">
            <td class="p-4 font-bold text-slate-900 flex items-center gap-2">
              <span class="material-symbols-outlined text-teal-600 text-[18px]">travel_explore</span>
              <span>${sName}</span>
            </td>
            <td class="p-4 text-teal-700 font-mono font-bold">${sId}</td>
            <td class="p-4 text-slate-600">${region}</td>
            <td class="p-4 text-slate-500 font-mono">${area}</td>
            <td class="p-4 text-slate-500 font-mono">${dateStr}</td>
            <td class="p-4 text-sky-700 font-mono font-bold">${platform}</td>
            <td class="p-4">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-50 text-teal-700 border border-teal-200">
                ${status}
              </span>
            </td>
            <td class="p-4 text-right">
              <button type="button" class="text-xs text-teal-600 hover:underline font-mono font-bold">Details &rarr;</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function openSurveyDetails(surveyId) {
      const s = allSurveys.find(item => item.survey_id === surveyId);
      if (!s) return;

      currentSurvey = s;
      document.getElementById('detail-survey-name').textContent = s.survey_name || 'Survey Detail';
      document.getElementById('detail-survey-id').textContent = `ID: ${s.survey_id}`;
      document.getElementById('detail-region').textContent = s.region || s.location_name || 'N/A';
      document.getElementById('detail-specific-area').textContent = s.specific_area || 'Sector 1';
      document.getElementById('detail-platform').textContent = s.platform || 'N/A';
      document.getElementById('detail-created-at').textContent = (s.created_at || '').substring(0, 10) || 'N/A';
      document.getElementById('detail-status').textContent = s.status || 'ACTIVE';
      document.getElementById('detail-det-count').textContent = `${s.detection_count || 0} Targets`;

      switchView('survey-details');
    }

    // =========================================================================
    // 6. RESULTS VIEW (Acoustic AI Detections)
    // =========================================================================
    async function loadResults() {
      const container = document.getElementById('results-cards-container');
      if (!container) return;
      container.innerHTML = `<div class="col-span-3 text-center p-8 text-slate-400 font-mono text-xs">Loading acoustic AI findings from TARANG AI Detection Engine...</div>`;

      try {
        const response = await fetch('/api/v1/surveys/all/detections');
        if (response.ok) {
          allDetections = await response.json();
        }
      } catch (e) {
        console.warn("Failed to load detections:", e);
      }

      if (!allDetections) allDetections = [];

      const countBadge = document.getElementById('results-count-text');
      if (countBadge) countBadge.textContent = `${allDetections.length} Detections Recorded`;

      renderResults(allDetections);
    }

    function renderResults(detections) {
      const container = document.getElementById('results-cards-container');
      if (!container) return;

      if (!detections || detections.length === 0) {
        container.innerHTML = `<div class="col-span-3 text-center p-12 text-slate-400 font-mono text-xs"><span class="material-symbols-outlined text-[36px] text-slate-300 block mb-2">radar</span>No AI detections available for this survey.<br/><span class="text-[11px] text-slate-400 mt-1 block">Acoustic detections will appear when survey sonar data is uploaded and processed.</span></div>`;
        return;
      }

      container.innerHTML = detections.map(d => {
        const isVerified = (d.verification_status || '').toLowerCase() === 'verified';
        const badgeColor = isVerified 
          ? 'bg-teal-50 text-teal-700 border-teal-200' 
          : 'bg-amber-50 text-amber-700 border-amber-200';

        const conf = d.confidence ? (d.confidence > 1 ? Math.round(d.confidence) : Math.round(d.confidence * 100)) : 85;

        return `
          <div class="marine-card rounded-2xl p-4 flex flex-col justify-between gap-3">
            <div class="flex items-center justify-between">
              <span class="font-mono text-xs font-bold text-slate-900">${d.id}</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeColor}">
                ${d.verification_status || 'Pending Verification'}
              </span>
            </div>
            <div class="w-full h-44 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 relative">
              <img src="${d.crop_url || 'logoimage.jpg'}" class="w-full h-full object-cover" alt="Target" />
              <span class="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-white/90 text-slate-900 font-mono text-[10px] font-bold shadow-sm">
                ${conf}% CONF
              </span>
            </div>
            <div class="space-y-1 text-xs">
              <h4 class="font-headline font-bold text-sm text-slate-900">${d.title || d.class_name}</h4>
              <p class="font-mono text-slate-500 text-[11px]">Depth: ${d.depth ? d.depth + 'm' : 'N/A'} • Pings: ${d.observations_count || 1}</p>
              <p class="font-mono text-slate-400 text-[10px]">GPS: ${d.latitude && d.longitude ? (Number(d.latitude).toFixed(4) + '°N, ' + Number(d.longitude).toFixed(4) + '°E') : 'Awaiting Tag'}</p>
            </div>
            <div class="pt-2 border-t border-slate-100 flex justify-between items-center text-xs font-mono">
              <span class="text-slate-400 text-[10px]">Tier: ${d.classification_tier || 'B'}</span>
              <button type="button" onclick="switchView('verification-queue')" class="text-teal-600 font-bold hover:underline">Inspect in Queue &rarr;</button>
            </div>
          </div>
        `;
      }).join('');
    }

    function filterResultsClass(clsKey) {
      document.querySelectorAll('.results-filter-btn').forEach(b => {
        b.className = "results-filter-btn px-3 py-1 rounded-lg text-xs font-mono text-slate-600 bg-white border border-slate-200 hover:bg-slate-50";
      });
      if (event && event.target) {
        event.target.className = "results-filter-btn px-3 py-1 rounded-lg text-xs font-mono text-white bg-teal-600 border border-teal-600";
      }

      if (clsKey === 'ALL') {
        renderResults(allDetections);
      } else {
        renderResults(allDetections.filter(d => (d.class_name || '').toLowerCase().includes(clsKey.toLowerCase())));
      }
    }

    // =========================================================================
    // 7. VERIFICATION QUEUE
    // =========================================================================
    async function loadVerificationQueue() {
      const tbody = document.getElementById('op-queue-tbody');
      if (!tbody) return;
      tbody.innerHTML = '<tr><td colspan="7" class="p-8 text-center text-slate-400 font-mono text-xs">Loading verification queue...</td></tr>';

      try {
        const res = await fetch('/api/v1/surveys/all/detections');
        const dets = await res.json();

        let pending = 0, verified = 0, rejected = 0;
        dets.forEach(d => {
          const v = (d.verification_status || '').toLowerCase();
          if (v === 'verified') verified++;
          else if (v === 'rejected') rejected++;
          else pending++;
        });

        const elPending = document.getElementById('op-queue-pending');
        const elVerified = document.getElementById('op-queue-verified');
        const elRejected = document.getElementById('op-queue-rejected');
        if (elPending) elPending.textContent = pending;
        if (elVerified) elVerified.textContent = verified;
        if (elRejected) elRejected.textContent = rejected;

        if (!dets.length) {
          tbody.innerHTML = '<tr><td colspan="7" class="p-8 text-center text-slate-400 font-mono text-xs"><span class="material-symbols-outlined text-[32px] text-slate-300 block mb-2">rule</span>No surveys awaiting verification.</td></tr>';
          return;
        }

        tbody.innerHTML = dets.map(d => {
          const vStatus = d.verification_status || 'Pending Verification';
          let badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
          if (vStatus.toLowerCase() === 'verified') badgeClass = 'bg-teal-50 text-teal-700 border-teal-200';
          if (vStatus.toLowerCase() === 'rejected') badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';

          const coords = (d.latitude && d.longitude) ? `${Number(d.latitude).toFixed(4)}°, ${Number(d.longitude).toFixed(4)}°` : 'Awaiting GPS Tag';
          const conf = d.confidence ? (d.confidence > 1 ? Math.round(d.confidence) : Math.round(d.confidence * 100)) : 85;

          return `
            <tr class="border-b border-slate-100 hover:bg-slate-50 transition-colors font-mono text-xs">
              <td class="py-3 px-3 font-bold text-slate-900">${d.id}</td>
              <td class="py-3 px-3 font-body font-medium text-slate-700">${d.title || d.class_name}</td>
              <td class="py-3 px-3 text-teal-700 font-bold">${conf}%</td>
              <td class="py-3 px-3 text-slate-500">${coords}</td>
              <td class="py-3 px-3 text-slate-700">${d.observations_count || 1} ping(s)</td>
              <td class="py-3 px-3">
                <span class="px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeClass}">
                  ${vStatus}
                </span>
              </td>
              <td class="py-3 px-3 text-right">
                <button type="button" onclick="switchView('results')" class="px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:border-teal-500 text-[10px] text-slate-700 hover:text-slate-900 transition-colors">
                  Inspect
                </button>
              </td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        tbody.innerHTML = '<tr><td colspan="7" class="p-8 text-center text-slate-400 font-mono text-xs">No surveys awaiting verification.</td></tr>';
      }
    }

    // =========================================================================
    // 8. REPORTS VIEW
    // =========================================================================
    async function loadReportsView() {
      const container = document.getElementById('reports-content-container');
      if (!container) return;

      let targetSurvey = currentSurvey;
      if (!targetSurvey && allSurveys.length > 0) {
        targetSurvey = allSurveys[0];
      }

      if (!targetSurvey) {
        try {
          const res = await fetch('/api/v1/surveys');
          if (res.ok) {
            const list = await res.json();
            if (list.length > 0) {
              targetSurvey = list[0];
              allSurveys = list;
            }
          }
        } catch (e) {}
      }

      if (!targetSurvey) {
        container.innerHTML = `
          <div class="marine-card rounded-2xl p-12 text-center max-w-xl mx-auto space-y-4">
            <div class="w-16 h-16 rounded-2xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center mx-auto">
              <span class="material-symbols-outlined text-[36px]">description</span>
            </div>
            <h3 class="font-headline font-bold text-xl text-slate-900">No Reports Available</h3>
            <p class="font-body text-xs text-slate-500 max-w-md mx-auto">
              Formal hydrographic briefing reports are dynamically generated from actual database surveys and acoustic detections. No surveys or detections have been recorded yet.
            </p>
            <button type="button" onclick="switchView('new-survey')" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-600 text-white font-mono text-xs font-bold shadow-sm hover:bg-teal-700 transition-all">
              <span class="material-symbols-outlined text-[16px]">add</span>
              <span>Create New Survey</span>
            </button>
          </div>
        `;
        return;
      }

      let dets = [];
      try {
        const dRes = await fetch(`/api/v1/surveys/${targetSurvey.survey_id}/detections`);
        if (dRes.ok) {
          dets = await dRes.json();
        }
      } catch (e) {}

      let ghostNets = 0, shipwrecks = 0, crabPots = 0, pipes = 0, unknowns = 0;
      let verified = 0, rejected = 0, pending = 0;

      dets.forEach(d => {
        const cls = (d.class_name || '').toLowerCase();
        if (cls.includes('net')) ghostNets++;
        else if (cls.includes('ship') || cls.includes('wreck')) shipwrecks++;
        else if (cls.includes('pot') || cls.includes('trap')) crabPots++;
        else if (cls.includes('pipe') || cls.includes('cable')) pipes++;
        else unknowns++;

        const v = (d.verification_status || '').toLowerCase();
        if (v === 'verified') verified++;
        else if (v === 'rejected') rejected++;
        else pending++;
      });

      const sDate = (targetSurvey.created_at || targetSurvey.survey_date || '').substring(0, 10) || new Date().toISOString().substring(0, 10);

      container.innerHTML = `
        <div class="marine-card rounded-2xl p-6 sm:p-10 border border-slate-200 space-y-6" id="report-sheet">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-full overflow-hidden border border-teal-200 bg-white p-1 flex items-center justify-center shrink-0 shadow-sm">
                <img src="logoimage.jpg" class="w-full h-full object-contain rounded-full" alt="TARANG Logo" />
              </div>
              <div>
                <h3 class="font-headline font-extrabold text-xl text-slate-900 tracking-tight">TARANG HYDROGRAPHIC SURVEY REPORT</h3>
                <p class="font-mono text-xs text-teal-700">INCOIS National Debris &amp; Anomaly Verification Pipeline</p>
              </div>
            </div>
            <div class="text-right font-mono text-xs text-slate-500">
              <p>REF: <strong class="text-slate-900">${targetSurvey.survey_id}</strong></p>
              <p>DATE: <strong class="text-slate-900">${sDate}</strong></p>
              <p>CLEARANCE: <strong class="text-teal-700">AUTHORIZED (MoES)</strong></p>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono">
            <div>
              <span class="text-slate-400 block text-[10px]">Survey Name:</span>
              <span class="text-slate-900 font-bold">${targetSurvey.survey_name || 'Hydrographic Survey'}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px]">Sector:</span>
              <span class="text-slate-900 font-bold">${targetSurvey.specific_area || targetSurvey.region || 'Sector 1'}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px]">Platform:</span>
              <span class="text-teal-700 font-bold">${targetSurvey.platform || 'AUV Autonomous Hydro'}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px]">AI Engine:</span>
              <span class="text-teal-700 font-bold">TARANG AI Detection</span>
            </div>
          </div>

          <div>
            <h4 class="font-headline font-bold text-sm text-slate-900 mb-3 flex items-center gap-2">
              <span class="material-symbols-outlined text-teal-600 text-[18px]">bar_chart</span>
              Detection Summary &amp; Classification Distribution
            </h4>
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center text-xs font-mono">
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span class="text-slate-500 block text-[10px]">Ghost Nets</span>
                <span class="text-rose-600 font-bold text-lg">${ghostNets}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span class="text-slate-500 block text-[10px]">Shipwrecks</span>
                <span class="text-sky-600 font-bold text-lg">${shipwrecks}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span class="text-slate-500 block text-[10px]">Derelict Pots</span>
                <span class="text-amber-600 font-bold text-lg">${crabPots}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span class="text-slate-500 block text-[10px]">Pipe / Cable</span>
                <span class="text-teal-600 font-bold text-lg">${pipes}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span class="text-slate-500 block text-[10px]">Unknown Anomalies</span>
                <span class="text-purple-600 font-bold text-lg">${unknowns}</span>
              </div>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold">
                ✓
              </div>
              <div>
                <p class="text-slate-900 font-bold">Analyst Verification Status</p>
                <p class="text-slate-500">${verified} Targets Validated • ${rejected} Rejected • ${pending} Review Pending</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <a href="/api/v1/export/survey/${targetSurvey.survey_id}/csv" download class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-bold">
                Download CSV
              </a>
              <a href="/api/v1/export/survey/${targetSurvey.survey_id}/geojson" download class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-bold">
                Download GeoJSON
              </a>
              <a href="/api/v1/export/survey/${targetSurvey.survey_id}/metadata-txt" download class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-bold">
                Download TXT
              </a>
            </div>
          </div>
        </div>
      `;
    }

    // =========================================================================
    // 9. NOTIFICATIONS & DOCUMENTS
    // =========================================================================
    async function loadNotifications() {
      const container = document.getElementById('notifications-list-container');
      if (!container) return;
      try {
        const res = await fetch('/api/v1/notifications');
        if (res.ok) {
          const notes = await res.json();
          if (notes.length > 0) {
            container.innerHTML = notes.map(n => `
              <div class="marine-card rounded-2xl p-4 flex items-start gap-3.5">
                <div class="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 border border-teal-200 flex items-center justify-center shrink-0">
                  <span class="material-symbols-outlined text-[20px]">notifications</span>
                </div>
                <div class="flex-1 text-xs">
                  <div class="flex items-center justify-between">
                    <h4 class="font-bold text-slate-900 text-sm">${n.title}</h4>
                    <span class="font-mono text-[10px] text-slate-400">${n.timestamp}</span>
                  </div>
                  <p class="text-slate-600 mt-1 font-body leading-relaxed">${n.message}</p>
                </div>
              </div>
            `).join('');
            return;
          }
        }
      } catch (e) {}

      container.innerHTML = `
        <div class="marine-card rounded-2xl p-8 text-center text-slate-400 font-mono text-xs">
          <span class="material-symbols-outlined text-[32px] text-slate-300 block mb-2">notifications_off</span>
          No notifications recorded yet.
        </div>
      `;
    }

    async function markAllNotificationsRead() {
      try {
        await fetch('/api/v1/notifications/mark-read', { method: 'POST' });
        const badge = document.getElementById('nav-unread-badge');
        const sidebarBadge = document.getElementById('sidebar-unread-count');
        if (badge) badge.classList.add('hidden');
        if (sidebarBadge) sidebarBadge.textContent = '0';
        showToast("All notifications marked as read.");
      } catch (e) {}
    }

    async function loadDocuments() {
      const tbody = document.getElementById('documents-table-body');
      if (!tbody) return;
      try {
        const res = await fetch('/api/v1/documents');
        if (res.ok) {
          const docs = await res.json();
          if (docs.length > 0) {
            tbody.innerHTML = docs.map(d => `
              <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100 font-mono text-xs">
                <td class="p-3.5 text-slate-900 font-bold flex items-center gap-2">
                  <span class="material-symbols-outlined text-teal-600 text-[18px]">description</span>
                  <span>${d.name}</span>
                </td>
                <td class="p-3.5 text-teal-700">${d.survey_id}</td>
                <td class="p-3.5 text-slate-600">${d.doc_type}</td>
                <td class="p-3.5 text-slate-500">${(d.file_size / 1024).toFixed(1)} KB</td>
                <td class="p-3.5 text-right">
                  <a href="${d.file_path}" download class="text-teal-600 hover:underline font-bold">Download</a>
                </td>
              </tr>
            `).join('');
            return;
          }
        }
      } catch (e) {}

      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="p-8 text-center text-slate-400 font-mono text-xs">
            No survey documents or binary logs uploaded yet.
          </td>
        </tr>
      `;
    }

    // =========================================================================
    // 10. INITIALIZATION
    // =========================================================================
    document.addEventListener('DOMContentLoaded', () => {
      const name = sessionStorage.getItem('currentUserName') || 'Cmdr. Rajesh Verma';
      const instId = sessionStorage.getItem('currentUser') || 'OP-409';

      const opNameEl = document.getElementById('header-op-name');
      const opIdEl = document.getElementById('header-op-id');
      if (opNameEl) opNameEl.textContent = name;
      if (opIdEl) opIdEl.textContent = instId.toUpperCase();

      regenerateSurveyId();
      loadSurveys();
      loadVerificationQueue();
    });
  </script>"""

# Replace script tag
html_before = content[:last_script_idx]
new_full_content = html_before + new_script_code + "\n</body>\n</html>\n"

with open('operator-portal.html', 'w', encoding='utf-8') as f:
    f.write(new_full_content)

print("operator-portal.html complete script rewrite applied.")
