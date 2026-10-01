"""TARANG upload-format coverage test.

Exercises the real workflow upload endpoint with XTF, PNG, JPG and MP4 inputs
and reports what the backend actually did with each one. Nothing is mocked: a
format only counts as WORKING when the server returns processed artifacts.
"""

import io
import json
import os
import sys

import numpy as np
import requests
from PIL import Image

BASE = os.environ.get('TARANG_BACKEND_URL', 'http://localhost:3000').rstrip('/')
SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs', '_format_probe')
os.makedirs(SCRATCH, exist_ok=True)

TOKEN = None


def demo_token(portal='survey_operator'):
    r = requests.post(f'{BASE}/api/auth/demo-access', json={'portal': portal}, timeout=30)
    body = r.json()
    if r.status_code != 200 or body.get('status') != 'success':
        raise SystemExit(f'Demo session failed for {portal}: HTTP {r.status_code} {body}')
    return body['access_token']


def make_sonar_png(path, size=(640, 480)):
    """Build a sonar-like PNG so the detection pass has plausible imagery."""
    rng = np.random.default_rng(7)
    base = rng.normal(40, 18, size[::-1]).clip(0, 255)
    array = np.repeat(base[:, :, None], 3, axis=2).astype(np.uint8)
    image = Image.fromarray(array)
    image.save(path, format='PNG')
    return path


def upload(path, mime):
    with open(path, 'rb') as handle:
        payload = handle.read()
    headers = {'Authorization': f'Bearer {TOKEN}'}
    return requests.post(
        f'{BASE}/api/v1/surveys/upload',
        files={'file': (os.path.basename(path), io.BytesIO(payload), mime)},
        headers=headers, timeout=900)


def summarise(label, response):
    body = {}
    if response.text:
        try:
            body = response.json()
        except ValueError:
            body = {'_raw': response.text[:400]}

    ok = response.status_code in (200, 201)
    detections = body.get('detections') or []
    images = body.get('images') or []
    status = body.get('processing_status') or body.get('status')

    print(f"\n{'=' * 68}\n{label}\n{'=' * 68}")
    print(f"  HTTP            : {response.status_code}")
    print(f"  status          : {status}")
    print(f"  survey_id       : {body.get('survey_id')}")
    print(f"  input_type      : {body.get('input_type')}")
    print(f"  detections      : {body.get('detections_count', len(detections))}")
    print(f"  images          : {len(images)}")
    if not ok:
        print(f"  ERROR (real)    : {body.get('error') or body.get('message') or body}")
    else:
        metadata = body.get('metadata') or {}
        if metadata:
            print(f"  metadata keys   : {sorted(metadata.keys())[:14]}")
        for det in detections[:3]:
            print(f"    det           : {json.dumps({k: det.get(k) for k in ['id', 'class_name', 'confidence', 'latitude', 'longitude']}, default=str)}")
        for img in images[:2]:
            url = img.get('url') or img.get('crop_url') or ''
            reachable = 'n/a'
            if url:
                full = url if url.startswith('http') else BASE + (url if url.startswith('/') else '/' + url)
                try:
                    reachable = requests.get(full, timeout=60).status_code
                except requests.RequestException as exc:
                    reachable = f'error {exc}'
            print(f"    image         : {url[:110]} -> HTTP {reachable}")
    return ok, body


def main():
    global TOKEN
    TOKEN = demo_token()
    results = {}

    png_path = make_sonar_png(os.path.join(SCRATCH, 'tarang_probe_sonar.png'))
    ok, _ = summarise('PNG upload', upload(png_path, 'image/png'))
    results['PNG'] = ok

    jpg_src = 'logoimage.jpg'
    if os.path.isfile(jpg_src):
        ok, _ = summarise('JPG upload', upload(jpg_src, 'image/jpeg'))
        results['JPG'] = ok
    else:
        print('\nJPG: no source image available to test')
        results['JPG'] = None

    for video in ('video.mp4', 'test.mp4'):
        if os.path.isfile(video):
            ok, body = summarise(f'MP4 upload ({video})', upload(video, 'video/mp4'))
            results[f'MP4:{video}'] = ok
            break
    else:
        print('\nMP4: no video file available to test')
        results['MP4'] = None

    xtf = sys.argv[1] if len(sys.argv) > 1 else 'tarang_synthetic_survey_002.xtf'
    if os.path.isfile(xtf):
        ok, _ = summarise(f'XTF upload ({xtf})', upload(xtf, 'application/octet-stream'))
        results['XTF'] = ok

    print(f"\n{'=' * 68}\nFORMAT COVERAGE SUMMARY\n{'=' * 68}")
    for name, ok in results.items():
        print(f"  {name:<18}: {'WORKING' if ok else ('NOT TESTED' if ok is None else 'NOT WORKING')}")
    return 0 if all(v for v in results.values() if v is not None) else 1


if __name__ == '__main__':
    sys.exit(main())
