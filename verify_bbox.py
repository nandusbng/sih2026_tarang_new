"""Upload the regenerated offshore XTF and confirm the real YOLO bbox is
persisted on the evidence-link event and returned by the detections API, so the
analyst portal can draw a real detection overlay. Nothing is mocked."""

import io
import os
import sys
import uuid

import requests

BASE = os.environ.get('TARANG_BACKEND_URL', 'http://localhost:3000').rstrip('/')
XTF = sys.argv[1] if len(sys.argv) > 1 else 'tarang_synthetic_survey_002.xtf'


def token(portal='sonar_analyst'):
    r = requests.post(f'{BASE}/api/auth/demo-access', json={'portal': portal}, timeout=30)
    return r.json()['access_token']


def main():
    # /api/v1/xtf/upload is authorized for the survey_operator role (the portal
    # that actually uploads XTF). The analyst role is 403 on upload, so use the
    # operator token for the POST and the analyst token for reading detections.
    upload_tok = token('survey_operator')
    read_tok = token('sonar_analyst')
    h = {'Authorization': f'Bearer {upload_tok}'}
    with open(XTF, 'rb') as fh:
        payload = fh.read()
    print(f'uploading {XTF} ({len(payload)/1e6:.2f} MB) ...', flush=True)
    # A fresh survey_id forces full re-inference instead of the idempotent
    # cache branch (which keys on file_hash and would skip writing bbox).
    fresh_sid = f'00000000-0000-0000-0000-{uuid.uuid4().hex[:12]}'
    r = requests.post(f'{BASE}/api/v1/xtf/upload',
                      files={'file': (os.path.basename(XTF), io.BytesIO(payload), 'application/octet-stream')},
                      data={'survey_id': fresh_sid},
                      headers=h, timeout=900)
    print('upload HTTP', r.status_code, flush=True)
    body = r.json()
    sid = body.get('survey_id')
    print('survey_id', sid, flush=True)
    print('reused existing survey:', body.get('reused_existing') or body.get('reused'), flush=True)

    d = requests.get(f'{BASE}/api/v1/surveys/{sid}/detections',
                     headers={'Authorization': f'Bearer {read_tok}'}, timeout=60).json()
    print('persisted detections:', len(d), flush=True)
    with_bbox = [x for x in d if x.get('bbox')]
    with_ping = [x for x in d if x.get('ping_number') is not None]
    print('detections with bbox:', len(with_bbox), flush=True)
    print('detections with ping_number:', len(with_ping), flush=True)
    if with_bbox:
        s = with_bbox[0]
        print('sample bbox:', s.get('bbox'), 'evidence_sequence:', s.get('evidence_sequence'),
              'ping:', s.get('ping_number'), 'img:', (s.get('evidence_image_url') or '')[-40:], flush=True)
        ok = True
    else:
        print('NO bbox persisted - overlay cannot be drawn from real data', flush=True)
        ok = False
    print('RESULT:', 'BBOX_OK' if ok else 'BBOX_MISSING', flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
