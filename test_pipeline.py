import urllib.request
import json
import os

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
with open('stitch_project/stitch_tarang_marine_intelligence_platform/tarang_sonar_ai_detection_console/screen.png', 'rb') as f:
    img_data = f.read()

body = []
part1 = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="acoustic_survey_frame.png"\r\nContent-Type: image/png\r\n\r\n'.encode('utf-8')
body.append(part1)
body.append(img_data)
part2 = f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="survey_id"\r\n\r\nTRG-2026-SRV-LIVE\r\n'.encode('utf-8')
body.append(part2)
part3 = f'--{boundary}\r\nContent-Disposition: form-data; name="latitude"\r\n\r\n12.8345\r\n'.encode('utf-8')
body.append(part3)
part4 = f'--{boundary}\r\nContent-Disposition: form-data; name="longitude"\r\n\r\n80.2214\r\n'.encode('utf-8')
body.append(part4)
part5 = f'--{boundary}\r\nContent-Disposition: form-data; name="depth"\r\n\r\n-34.2m\r\n'.encode('utf-8')
body.append(part5)
body.append(f'--{boundary}--\r\n'.encode('utf-8'))
payload = b''.join(body)

req = urllib.request.Request('http://127.0.0.1:3000/api/detect', data=payload, method='POST')
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print('INFERENCE RESULT:', res['status'], 'Detections:', len(res['detections']))
    det_id = res['detections'][0]['id'] if res['detections'] else None
    print('DETECTION ID:', det_id)

if det_id:
    # 1. Analyst Verification
    v_req = urllib.request.Request(
        f'http://127.0.0.1:3000/api/v1/detections/{det_id}/verify', 
        data=json.dumps({'status': 'Verified', 'notes': 'Real model validation pass.'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(v_req) as resp:
        print('VERIFY RESULT:', json.loads(resp.read().decode()))

    # 2. Marine Cleanup Decision
    c_req = urllib.request.Request(
        f'http://127.0.0.1:3000/api/v1/detections/{det_id}/cleanup-decision',
        data=json.dumps({'cleanup_required': True}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(c_req) as resp:
        print('CLEANUP DECISION RESULT:', json.loads(resp.read().decode()))

    # 3. Government Stats Check
    with urllib.request.urlopen('http://127.0.0.1:3000/api/v1/stats/government') as resp:
        stats = json.loads(resp.read().decode())
        print('GOV STATS AFTER WORKFLOW:', {
            'total_detected': stats['total_detected'],
            'total_verified': stats['total_verified'],
            'pending_clearance': stats['pending_clearance']
        })

    # 4. Cleanup Clearance Submission
    clr_req = urllib.request.Request(
        'http://127.0.0.1:3000/api/v1/clearance',
        data=json.dumps({
            'target_id': det_id,
            'team': 'Marine Unit 1',
            'status': 'Cleared',
            'notes': 'Successfully removed via ROV grapple.'
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(clr_req) as resp:
        print('CLEARANCE SUBMITTED:', json.loads(resp.read().decode()))

    # 5. Government Stats Check After Clearance
    with urllib.request.urlopen('http://127.0.0.1:3000/api/v1/stats/government') as resp:
        stats = json.loads(resp.read().decode())
        print('GOV STATS AFTER CLEARANCE:', {
            'total_cleared': stats['total_cleared'],
            'clearance_rate': stats['clearance_rate']
        })
