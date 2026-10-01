import os

with open('survey-operator.html', 'r', encoding='utf-8') as f:
    content = f.read()

button_html = """
    <div class="flex items-center gap-4">
      <h3 class="font-headline-sm text-primary font-bold">Upload Media</h3>
      <button id="openSurveyModal" onclick="document.getElementById('surveyPopModal').classList.remove('hidden'); event.stopPropagation();" class="px-3 py-1 bg-secondary hover:bg-abyssal-navy transition-colors text-white rounded text-xs font-bold uppercase shadow z-50">Create Survey</button>
    </div>
"""

content = content.replace('<h3 class="font-headline-sm text-primary font-bold">Upload Media</h3>', button_html)

modal_html = """
<!-- SURVEY POP MODAL -->
<div id="surveyPopModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm hidden">
    <div class="bg-surface-container-lowest w-full max-w-lg rounded-xl shadow-2xl overflow-hidden border border-border-subtle p-6 relative">
        <button onclick="document.getElementById('surveyPopModal').classList.add('hidden')" class="absolute top-4 right-4 text-gray-500 hover:text-red-500">
            <span class="material-symbols-outlined">close</span>
        </button>
        <h2 class="text-xl font-headline-lg font-bold text-primary-container mb-4">Initialize Survey Pop</h2>
        <form id="surveyPopForm" class="space-y-3">
            <div>
                <label class="block text-[11px] font-label-code font-bold text-gray-600 uppercase mb-1">Survey Name</label>
                <input type="text" id="survey_name" required class="w-full rounded border border-gray-300 px-3 py-1.5 text-sm" placeholder="e.g. INCOIS-BAY-04">
            </div>
            <div>
                <label class="block text-[11px] font-label-code font-bold text-gray-600 uppercase mb-1">Location</label>
                <input type="text" id="location_name" required class="w-full rounded border border-gray-300 px-3 py-1.5 text-sm" placeholder="e.g. Bay of Bengal">
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="block text-[11px] font-label-code font-bold text-gray-600 uppercase mb-1">Date</label>
                    <input type="date" id="survey_date" required class="w-full rounded border border-gray-300 px-3 py-1.5 text-sm">
                </div>
                <div>
                    <label class="block text-[11px] font-label-code font-bold text-gray-600 uppercase mb-1">Time</label>
                    <input type="time" id="survey_time" required class="w-full rounded border border-gray-300 px-3 py-1.5 text-sm">
                </div>
            </div>
            <div class="pt-4 flex justify-end gap-3">
                <button type="button" onclick="document.getElementById('surveyPopModal').classList.add('hidden')" class="px-4 py-2 rounded text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
                <button type="submit" class="px-4 py-2 bg-secondary text-white rounded text-sm font-bold uppercase shadow hover:bg-abyssal-navy">Create Survey</button>
            </div>
        </form>
    </div>
</div>
<script>
window.currentSurveyId = null;

document.getElementById('surveyPopForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        survey_name: document.getElementById('survey_name').value,
        location_name: document.getElementById('location_name').value,
        survey_date: document.getElementById('survey_date').value,
        survey_time: document.getElementById('survey_time').value,
        sonar_device: 'Standard',
        sonar_frequency: 'Unknown'
    };
    try {
        const response = await fetch('/api/v1/surveys', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.status === 'success') {
            window.currentSurveyId = data.survey_id;
            alert('Survey Created successfully! You can now upload media for Survey: ' + data.survey_id);
            document.getElementById('surveyPopModal').classList.add('hidden');
        } else {
            alert('Error creating survey: ' + data.error);
        }
    } catch (err) {
        console.error(err);
        alert('Server error.');
    }
});
</script>
"""

content = content.replace('</body>', modal_html + '\n</body>')

# Also, when the XTF uploads via the file-input, it needs to pass the survey_id if it exists.
# But wait, `survey-operator.html` uploads the file directly to `/api/detect` or `/api/upload`?
# In survey-operator.html, the file input logic goes to `/api/detect`. Wait!
# The user's prompt said "Connect the existing upload functionality to the newly created Survey."
# In `survey-operator.html`, I don't need to change the `/api/detect` route, I just need to add the `survey_id` to the formData if `window.currentSurveyId` exists!

js_patch = """
                const formData = new FormData();
                formData.append('file', blob, 'frame.jpg');
                formData.append('conf', '0.20');
                if (window.currentSurveyId) {
                    formData.append('survey_id', window.currentSurveyId);
                }
"""
content = content.replace("const formData = new FormData();\n                formData.append('file', blob, 'frame.jpg');\n                formData.append('conf', '0.20');", js_patch)

# And for regular video uploads in survey-operator.html:
js_patch_2 = """
            const formData = new FormData();
            formData.append('file', file);
            if (window.currentSurveyId) {
                formData.append('survey_id', window.currentSurveyId);
            }
"""
content = content.replace("const formData = new FormData();\n            formData.append('file', file);", js_patch_2)

with open('survey-operator.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched!")
