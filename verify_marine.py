with open('marine-analyst.html', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('Light theme body background', '#f8fafc' in c),
    ('Empty state for hotspots', 'No verified hotspots available.' in c),
    ('Live Operations map container', 'marineMap' in c or 'tab-live-ops' in c),
    ('Clearance workflow intact', 'Clearance Updates' in c or 'clearance' in c),
    ('TarangMap included', 'tarang-map.js' in c),
]

for label, res in checks:
    print(f"{label}: {'OK' if res else 'MISSING'}")
