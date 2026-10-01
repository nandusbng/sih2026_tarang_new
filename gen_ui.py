import os

BASE_HTML_TOP = """<!DOCTYPE html>
<html class="h-full" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>TARANG // तरंग - Survey Management</title>
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&amp;family=Plus+Jakarta+Sans:wght@500;600;700;800&amp;family=Space+Grotesk:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script id="tailwind-config">
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          "colors": {
            "seafoam-glow": "#14B8A6",
            "primary-container": "#0a2540",
            "canvas-base": "#FAFCFF",
            "primary": "#000f22",
            "secondary": "#006398",
            "abyssal-navy": "#031B33"
          },
          "fontFamily": {
            "headline-lg-mobile": ["Plus Jakarta Sans"],
            "label-code": ["Space Grotesk"],
            "headline-sm": ["Plus Jakarta Sans"],
            "body-sm": ["Inter"],
            "body-md": ["Inter"],
            "headline-lg": ["Plus Jakarta Sans"],
            "label-sm": ["Inter"],
            "body-lg": ["Inter"]
          }
        }
      }
    }
</script>
<style>
    .material-symbols-outlined {
      font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20;
      vertical-align: middle;
      display: inline-block;
    }
</style>
</head>
<body class="bg-canvas-base text-gray-900 h-full flex flex-col antialiased selection:bg-secondary selection:text-white font-body-md overflow-x-hidden">
<header class="bg-canvas-base border-b border-gray-200 shadow-sm sticky top-0 z-50 flex-none">
<div class="flex justify-between items-center w-full px-6 max-w-full mx-auto py-2.5">
<div class="flex items-center gap-4">
<div class="flex items-center gap-2">
<div class="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center text-white shadow-inner">
<span class="material-symbols-outlined text-xl" data-icon="waves">waves</span>
</div>
<div class="flex flex-col">
<span class="text-headline-sm font-headline-sm font-bold tracking-tight text-primary-container">TARANG // Survey</span>
</div>
</div>
<nav class="hidden md:flex items-center gap-4 ml-6">
  <a href="surveys.html" class="font-label-code text-xs font-bold text-gray-600 hover:text-secondary uppercase">All Surveys</a>
  <a href="new-survey.html" class="font-label-code text-xs font-bold text-gray-600 hover:text-secondary uppercase">New Survey</a>
  <a href="survey-operator.html" class="font-label-code text-xs font-bold text-gray-600 hover:text-secondary uppercase">Operator</a>
</nav>
</div>
</div>
</header>
"""

HTML_NEW_SURVEY = BASE_HTML_TOP + """
<main class="flex-1 w-full p-4 flex items-center justify-center min-h-0 bg-gray-50">
    <div class="max-w-2xl w-full bg-white rounded-xl shadow-md border border-gray-200 p-8">
        <h1 class="text-2xl font-headline-lg font-bold text-primary-container mb-2">Create New Survey</h1>
        <p class="text-sm text-gray-500 mb-6">Initialize a new underwater sonar scanning mission.</p>
        
        <form id="newSurveyForm" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Survey Name</label>
                    <input type="text" id="survey_name" required class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow" placeholder="e.g. INCOIS-BAY-04">
                </div>
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Location Area</label>
                    <input type="text" id="location_name" required class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow" placeholder="e.g. Bay of Bengal">
                </div>
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Survey Date</label>
                    <input type="date" id="survey_date" required class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow">
                </div>
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Survey Time</label>
                    <input type="time" id="survey_time" required class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow">
                </div>
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Sonar Device</label>
                    <input type="text" id="sonar_device" class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow" placeholder="e.g. Klein 3000">
                </div>
                <div>
                    <label class="block text-xs font-label-code font-bold text-gray-700 uppercase mb-1">Sonar Frequency</label>
                    <input type="text" id="sonar_frequency" class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-seafoam-glow focus:border-seafoam-glow" placeholder="e.g. 100/500 kHz">
                </div>
            </div>
            <div class="pt-4 flex justify-end">
                <button type="submit" class="bg-secondary text-white font-label-code text-xs font-bold uppercase px-6 py-2.5 rounded-md hover:bg-abyssal-navy transition-colors">
                    Create & Proceed to Upload
                </button>
            </div>
        </form>
    </div>
</main>
<script>
document.getElementById('newSurveyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        survey_name: document.getElementById('survey_name').value,
        location_name: document.getElementById('location_name').value,
        survey_date: document.getElementById('survey_date').value,
        survey_time: document.getElementById('survey_time').value,
        sonar_device: document.getElementById('sonar_device').value,
        sonar_frequency: document.getElementById('sonar_frequency').value,
    };
    try {
        const response = await fetch('/api/v1/surveys', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert('Survey Created! Redirecting to XTF Upload.');
            window.location.href = `survey-upload.html?survey_id=${data.survey_id}`;
        } else {
            alert('Error creating survey: ' + data.error);
        }
    } catch (err) {
        console.error(err);
        alert('Server error.');
    }
});
</script>
</body></html>
"""

HTML_SURVEYS = BASE_HTML_TOP + """
<main class="flex-1 w-full p-6 bg-gray-50 overflow-y-auto">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-headline-lg font-bold text-primary-container">Survey Missions</h1>
            <a href="new-survey.html" class="bg-secondary text-white font-label-code text-xs font-bold uppercase px-4 py-2 rounded-md hover:bg-abyssal-navy transition-colors">
                + New Survey
            </a>
        </div>
        
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 border-b border-gray-200">
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500">Survey ID</th>
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500">Name</th>
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500">Date</th>
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500">Location</th>
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500">Status</th>
                        <th class="py-3 px-4 text-xs font-label-code font-bold uppercase text-gray-500 text-right">Action</th>
                    </tr>
                </thead>
                <tbody id="surveyTableBody" class="divide-y divide-gray-200">
                    <tr><td colspan="6" class="text-center py-8 text-gray-500 text-sm">Loading surveys...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</main>
<script>
async function loadSurveys() {
    try {
        const response = await fetch('/api/v1/surveys');
        const surveys = await response.json();
        const tbody = document.getElementById('surveyTableBody');
        tbody.innerHTML = '';
        
        if (surveys.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-500 text-sm">No surveys found. Create one to get started.</td></tr>';
            return;
        }
        
        surveys.forEach(survey => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-50 transition-colors";
            tr.innerHTML = `
                <td class="py-3 px-4 text-sm font-label-code font-semibold text-secondary">${survey.survey_id}</td>
                <td class="py-3 px-4 text-sm font-semibold text-gray-900">${survey.survey_name}</td>
                <td class="py-3 px-4 text-sm text-gray-600">${survey.survey_date}</td>
                <td class="py-3 px-4 text-sm text-gray-600">${survey.location_name}</td>
                <td class="py-3 px-4">
                    <span class="px-2.5 py-1 rounded-full text-[10px] font-label-code font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">${survey.status}</span>
                </td>
                <td class="py-3 px-4 text-right">
                    <a href="survey-dashboard.html?id=${survey.survey_id}" class="text-secondary hover:text-abyssal-navy text-sm font-medium">Dashboard &rarr;</a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
        document.getElementById('surveyTableBody').innerHTML = '<tr><td colspan="6" class="text-center py-8 text-red-500 text-sm">Failed to load surveys.</td></tr>';
    }
}
loadSurveys();
</script>
</body></html>
"""

HTML_SURVEY_UPLOAD = BASE_HTML_TOP + """
<main class="flex-1 w-full p-4 flex items-center justify-center min-h-0 bg-gray-50">
    <div class="max-w-xl w-full bg-white rounded-xl shadow-md border border-gray-200 p-8 text-center">
        <h1 class="text-2xl font-headline-lg font-bold text-primary-container mb-2">Upload Survey XTF</h1>
        <p class="text-sm text-gray-500 mb-6" id="surveyMeta">Loading survey details...</p>
        
        <div id="upload-zone" class="bg-gray-50 p-8 rounded-xl border-2 border-dashed border-gray-300 hover:border-seafoam-glow hover:bg-teal-50 flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors duration-200 mb-4">
            <span class="material-symbols-outlined text-[36px] text-gray-400">cloud_upload</span>
            <h3 class="font-headline-sm text-gray-700 font-bold">Select XTF File</h3>
            <p class="font-body-sm text-[11px] text-gray-500 mt-1">Upload the synthetic XTF for AI Processing</p>
            <input type="file" id="file-input" accept=".xtf" class="hidden" />
        </div>
        
        <div id="status" class="hidden text-sm font-semibold text-secondary">Uploading and processing... This may take a minute...</div>
    </div>
</main>
<script>
const urlParams = new URLSearchParams(window.location.search);
const surveyId = urlParams.get('survey_id');

async function loadMeta() {
    if(!surveyId) return;
    const res = await fetch(`/api/v1/surveys/${surveyId}`);
    const data = await res.json();
    document.getElementById('surveyMeta').innerText = `Survey: ${data.survey_name} | Location: ${data.location_name}`;
}
loadMeta();

const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');

uploadZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async (e) => {
    if(e.target.files.length > 0) {
        document.getElementById('status').classList.remove('hidden');
        const formData = new FormData();
        formData.append('file', e.target.files[0]);
        // The backend expects the survey_id. Wait, our backend xtf_upload uses XTF's internal Survey ID?
        // Let's pass survey_id so the backend can link it.
        formData.append('survey_id', surveyId);
        
        try {
            const res = await fetch('/api/v1/xtf/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if(data.error) {
                alert(data.error);
                document.getElementById('status').classList.add('hidden');
            } else {
                window.location.href = `survey-dashboard.html?id=${data.survey_id || surveyId}`;
            }
        } catch(err) {
            console.error(err);
            alert("Upload failed.");
        }
    }
});
</script>
</body></html>
"""

HTML_SURVEY_DASHBOARD = BASE_HTML_TOP + """
<main class="flex-1 w-full p-4 lg:p-6 bg-gray-50 overflow-y-auto">
    <div class="max-w-7xl mx-auto space-y-6">
        
        <!-- Header -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div>
                <h1 class="text-2xl font-headline-lg font-bold text-primary-container" id="dashName">Survey Dashboard</h1>
                <p class="text-sm font-label-code text-gray-500 mt-1" id="dashId">ID: Loading...</p>
            </div>
            <div class="flex items-center gap-3 mt-4 md:mt-0">
                <div class="px-3 py-1.5 rounded-md bg-green-50 border border-green-200 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-green-500"></span>
                    <span class="text-[11px] font-label-code font-bold text-green-700 uppercase">Status: PENDING REVIEW</span>
                </div>
                <div class="px-3 py-1.5 rounded-md bg-teal-50 border border-teal-200">
                    <span class="text-[11px] font-label-code font-bold text-teal-700 uppercase">Data Quality: 92% GOOD</span>
                </div>
            </div>
        </div>
        
        <!-- Stats Row -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p class="text-xs font-label-code text-gray-500 uppercase font-bold mb-1">Total Pings</p>
                <p class="text-2xl font-headline-sm font-bold text-primary-container" id="statPings">0</p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p class="text-xs font-label-code text-gray-500 uppercase font-bold mb-1">Detections</p>
                <p class="text-2xl font-headline-sm font-bold text-secondary" id="statDetections">0</p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p class="text-xs font-label-code text-gray-500 uppercase font-bold mb-1">Navigation Status</p>
                <p class="text-sm font-headline-sm font-bold text-primary-container mt-2">Available</p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p class="text-xs font-label-code text-gray-500 uppercase font-bold mb-1">Sonar Channels</p>
                <p class="text-2xl font-headline-sm font-bold text-primary-container" id="statChannels">0</p>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
            <div class="border-b border-gray-200 bg-gray-50 px-4 py-3">
                <h2 class="font-headline-sm font-bold text-primary-container text-sm uppercase">AI Detection Pipeline Results</h2>
            </div>
            <div class="p-4 overflow-x-auto">
                <table class="w-full text-left border-collapse min-w-[600px]">
                    <thead>
                        <tr class="border-b border-gray-200">
                            <th class="py-2 text-xs font-label-code font-bold uppercase text-gray-500">Object ID</th>
                            <th class="py-2 text-xs font-label-code font-bold uppercase text-gray-500">Class</th>
                            <th class="py-2 text-xs font-label-code font-bold uppercase text-gray-500">Confidence</th>
                            <th class="py-2 text-xs font-label-code font-bold uppercase text-gray-500">Ping/Location</th>
                            <th class="py-2 text-xs font-label-code font-bold uppercase text-gray-500 text-right">Image</th>
                        </tr>
                    </thead>
                    <tbody id="detTableBody" class="divide-y divide-gray-100">
                        <tr><td colspan="5" class="text-center py-8 text-gray-500 text-sm">Loading detections...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
    </div>
</main>
<script>
const urlParams = new URLSearchParams(window.location.search);
const surveyId = urlParams.get('id');

async function loadDashboard() {
    if(!surveyId) return;
    
    // In our backend, XTF detections are stored in memory under XTF_SURVEYS or in SQLite.
    // The user requirement explicitly states: API GET /api/v1/xtf/<survey_id>/detections
    try {
        const detRes = await fetch(`/api/v1/xtf/${surveyId}/detections`);
        const dets = await detRes.json();
        
        const tbody = document.getElementById('detTableBody');
        tbody.innerHTML = '';
        
        document.getElementById('dashId').innerText = `ID: ${surveyId}`;
        document.getElementById('statDetections').innerText = dets.length || 0;
        
        if (dets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-8 text-gray-500 text-sm">No AI detections found in this survey.</td></tr>';
            return;
        }
        
        dets.forEach(det => {
            const tr = document.createElement('tr');
            const locStr = det.telemetry?.Latitude ? `${det.telemetry.Latitude.toFixed(5)}, ${det.telemetry.Longitude.toFixed(5)}` : `Ping: ${det.ping_start || 'N/A'}`;
            tr.innerHTML = `
                <td class="py-3 text-sm font-label-code font-semibold text-secondary">${det.id}</td>
                <td class="py-3 text-sm font-semibold text-gray-900">${det.class_name.toUpperCase()}</td>
                <td class="py-3 text-sm text-gray-600">
                    <div class="flex items-center gap-2">
                        <div class="w-16 h-1.5 bg-gray-200 rounded-full"><div class="h-1.5 bg-teal-500 rounded-full" style="width: ${det.confidence}%"></div></div>
                        <span class="font-label-code font-bold">${det.confidence}%</span>
                    </div>
                </td>
                <td class="py-3 text-xs font-label-code text-gray-600">${locStr}</td>
                <td class="py-3 text-right">
                    <img src="${det.crop_url}" class="h-8 inline-block rounded bg-black">
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(err) {
        console.error(err);
    }
}

loadDashboard();
</script>
</body></html>
"""

with open('new-survey.html', 'w', encoding='utf-8') as f: f.write(HTML_NEW_SURVEY)
with open('surveys.html', 'w', encoding='utf-8') as f: f.write(HTML_SURVEYS)
with open('survey-upload.html', 'w', encoding='utf-8') as f: f.write(HTML_SURVEY_UPLOAD)
with open('survey-dashboard.html', 'w', encoding='utf-8') as f: f.write(HTML_SURVEY_DASHBOARD)
