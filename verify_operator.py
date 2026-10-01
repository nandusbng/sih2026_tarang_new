with open('operator-portal.html', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('drone.glb model URL', 'static/models/drone.glb' in c),
    ('SIMULATION DATA label', 'SIMULATION DATA' in c),
    ('startSurveySimulation function', 'startSurveySimulation' in c),
    ('stopSurveySimulation function', 'stopSurveySimulation' in c),
    ('resetSurveySimulation function', 'resetSurveySimulation' in c),
    ('Verification queue in nav', 'verification' in c and 'Verification Queue' in c),
    ('Empty state for verification', 'No surveys awaiting verification.' in c),
    ('No Mission Readiness Diagnostics', 'Mission Readiness & Diagnostics' not in c),
    ('No Marine Environmental Status', 'Marine Environmental Status' not in c),
    ('Light theme body background', '#f8fafc' in c),
]

for label, res in checks:
    print(f"{label}: {'OK' if res else 'MISSING'}")
