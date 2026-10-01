with open('operator-portal.html', 'r', encoding='utf-8') as f:
    text = f.read()

queries = [
    'Mission Readiness',
    'Marine Environmental',
    'data-view="verification-queue"',
    'No surveys awaiting verification.'
]

for q in queries:
    print(f"'{q}' in operator-portal.html:", q in text)
