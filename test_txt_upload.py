import urllib.request
import json

sample_txt = """
SURVEY_LOG: TRG-2026-TEST-001
NAME: Bay of Bengal Continental Shelf Hydrography
DATE: 2026-09-19
TIME: 14:30:00
REGION: Bay of Bengal Sector Alpha
PLATFORM: Autonomous Underwater Vehicle (AUV)
SONAR_DEVICE: High-Resolution Dual Frequency Side-Scan Sonar
FREQUENCY: 450/900 kHz
LATITUDE: 13.0827
LONGITUDE: 80.2707
HEADING: 42.5
ALTITUDE: 12.4 m
WATER_DEPTH: 48.6 m
RANGE: 75 m
PING_RATE: 15 Hz
OPERATOR: Cmdr. Rajesh Verma
"""

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
parts = [
    f'--{boundary}',
    'Content-Disposition: form-data; name="file"; filename="survey_log_001.txt"',
    'Content-Type: text/plain',
    '',
    sample_txt.strip(),
    f'--{boundary}--',
    ''
]
body = '\r\n'.join(parts).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:3000/api/v1/txt/upload',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

res = urllib.request.urlopen(req)
res_json = json.loads(res.read().decode('utf-8'))
print('Status:', res.status)
print('Response:', json.dumps(res_json, indent=2))
