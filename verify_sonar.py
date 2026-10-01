with open('sonar-analyst.html', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('Light theme body background', '#f8fafc' in c),
    ('Empty state for detections', 'No AI detections available for this survey.' in c),
    ('Spatial Map tab in nav', 'tab-spatial-map' in c),
    ('TarangMap integration', 'TarangMap' in c),
    ('No Supabase createClient in active execution', 'createClient' not in c or 'SUPABASE_KEY' not in c),
    ('Decision actions present', 'verify' in c and 'reject' in c and 'reclassify' in c),
]

for label, res in checks:
    print(f"{label}: {'OK' if res else 'MISSING'}")
