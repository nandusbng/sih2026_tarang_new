import re

with open('operator-portal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the syntax error in loadReportsView (unescape \` and \${)
content = content.replace(r'fetch(\`/api/v1/surveys/\${targetSurvey.survey_id}/detections\`)', "fetch(`/api/v1/surveys/${targetSurvey.survey_id}/detections`)")
content = content.replace(r'\${targetSurvey.survey_id}', '${targetSurvey.survey_id}')
content = content.replace(r'\${sDate}', '${sDate}')
content = content.replace(r'\${targetSurvey.survey_name || \'Hydrographic Survey\'}', '${targetSurvey.survey_name || "Hydrographic Survey"}')
content = content.replace(r'\${targetSurvey.specific_area || targetSurvey.region || \'Sector 1\'}', '${targetSurvey.specific_area || targetSurvey.region || "Sector 1"}')
content = content.replace(r'\${targetSurvey.platform || \'AUV Autonomous Hydro\'}', '${targetSurvey.platform || "AUV Autonomous Hydro"}')
content = content.replace(r'\${ghostNets}', '${ghostNets}')
content = content.replace(r'\${shipwrecks}', '${shipwrecks}')
content = content.replace(r'\${crabPots}', '${crabPots}')
content = content.replace(r'\${pipes}', '${pipes}')
content = content.replace(r'\${unknowns}', '${unknowns}')
content = content.replace(r'\${verified}', '${verified}')
content = content.replace(r'\${rejected}', '${rejected}')
content = content.replace(r'\${pending}', '${pending}')

# Also check for any remaining \` or \${ anywhere in scripts
# Replace any remaining \${ with ${
content = content.replace(r'\${', '${')
content = content.replace(r'\`', '`')

# 2. Add Verification Queue to Sidebar navigation
old_sidebar_settings_btn = """          <button type="button" onclick="switchView('settings')" data-view="settings" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-300 hover:text-white hover:bg-[#08223f]">
            <span class="material-symbols-outlined text-[20px] text-slate-400">settings</span>
            <span>Settings</span>
          </button>"""

verification_queue_nav_btn = """          <button type="button" onclick="switchView('verification-queue')" data-view="verification-queue" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-teal-600">verified</span>
            <span>Verification Queue</span>
          </button>
          <button type="button" onclick="switchView('settings')" data-view="settings" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-slate-500">settings</span>
            <span>Settings</span>
          </button>"""

if old_sidebar_settings_btn in content:
    content = content.replace(old_sidebar_settings_btn, verification_queue_nav_btn)
else:
    # Alternative match if class attributes changed
    content = re.sub(
        r'(<button[^>]*onclick="switchView\(\'settings\'\)"[^>]*>.*?Settings.*?<\/button>)',
        r'''<button type="button" onclick="switchView('verification-queue')" data-view="verification-queue" class="nav-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium tracking-wide transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100">
            <span class="material-symbols-outlined text-[20px] text-teal-600">verified</span>
            <span>Verification Queue</span>
          </button>\n\1''',
        content,
        flags=re.DOTALL
    )

# 3. Remove Mission Readiness & Diagnostics and Marine Environmental Status sections
old_dash_sections_regex = r'<!--\s*28\.\s*REORGANIZED OLD DASHBOARD COMPONENTS.*?<!--\s*24\.\s*Operator\s*->\s*Analyst Queue'
# Let's check if old_dash_sections_regex matches
match = re.search(old_dash_sections_regex, content, re.DOTALL)
if match:
    print("Found readiness & weather sections, removing them cleanly...")
    content = content[:match.start()] + '<!-- 24. Operator -> Analyst Queue' + content[match.end():]
else:
    print("Could not match via regex, checking explicit substring...")
    idx1 = content.find('Mission Readiness &amp; Diagnostics')
    if idx1 == -1:
        idx1 = content.find('Mission Readiness & Diagnostics')
    print("Index of Mission Readiness:", idx1)

# 4. Connect Operator -> Marine Analyst Queue preview button to switchView('verification-queue')
content = content.replace(
    """<button type="button" onclick="switchView('reports')" class="text-xs font-mono font-bold text-teal-400 hover:underline">
              View Formal Reports &rarr;
            </button>""",
    """<button type="button" onclick="switchView('verification-queue')" class="text-xs font-mono font-bold text-teal-600 hover:text-teal-700 hover:underline flex items-center gap-1">
              <span>Open Verification Queue</span>
              <span class="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>"""
)

# 5. Ensure Verification Queue empty state says: "No surveys awaiting verification."
content = re.sub(
    r'tbody\.innerHTML\s*=\s*[\'"]<tr><td[^>]*>No detections in queue[^<]*<\/td><\/tr>[\'"]',
    """tbody.innerHTML = '<tr><td colspan="7" class="p-8 text-center text-slate-500 font-mono text-xs"><span class="material-symbols-outlined text-[32px] text-slate-400 block mb-2">rule</span>No surveys awaiting verification.</td></tr>'""",
    content
)

# Also check empty state for dash queue container
content = content.replace(
    'No surveys currently pending or reviewed in verification queue.',
    'No surveys awaiting verification.'
)

with open('operator-portal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Targeted fixes applied to operator-portal.html.")
