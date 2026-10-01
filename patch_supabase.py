import os

with open('survey-operator.html', 'r', encoding='utf-8') as f:
    content = f.read()

supabase_patch = """
        if (data.status === 'success') {
            window.currentSurveyId = data.survey_id;
            
            // Sync to Supabase
            if (typeof supabaseClient !== 'undefined') {
                try {
                    await supabaseClient.from('surveys').insert([{
                        survey_id: data.survey_id, // ensure UUID if required, but SQLite gives 8 chars. We can let Supabase generate it or push the payload.
                        survey_name: payload.survey_name,
                        location_name: payload.location_name,
                        survey_date: payload.survey_date,
                        survey_time: payload.survey_time,
                        sonar_device: payload.sonar_device,
                        sonar_frequency: payload.sonar_frequency,
                        created_by: sessionStorage.getItem('currentUser') || 'Operator'
                    }]);
                    console.log('Synced Survey to Supabase Database');
                } catch(e) {
                    console.error('Supabase Sync Failed', e);
                }
            }
            
            alert('Survey Created successfully! You can now upload media for Survey: ' + data.survey_id);
"""

content = content.replace("        if (data.status === 'success') {\n            window.currentSurveyId = data.survey_id;\n            alert('Survey Created successfully! You can now upload media for Survey: ' + data.survey_id);", supabase_patch)

with open('survey-operator.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched Supabase Sync")
