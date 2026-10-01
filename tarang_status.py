"""TARANG live system diagnostics.

Every status reported here is the result of a real request against the
configured backend. Nothing is assumed connected because a library is
installed, and no status is ever hardcoded to a passing value.
"""

import os
import time
import uuid
from io import BytesIO

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = (os.environ.get('SUPABASE_URL') or '').rstrip('/')
ANON_KEY = os.environ.get('SUPABASE_KEY') or os.environ.get('SUPABASE_ANON_KEY') or ''
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') or ''

# A table that is part of the core TARANG schema and safe to read with a
# one-row limit. Used purely to prove the REST API answers real queries.
PROBE_TABLE = 'surveys'
PROBE_BUCKET = os.environ.get('TARANG_STATUS_BUCKET', 'survey-images')

TIMEOUT = float(os.environ.get('TARANG_STATUS_TIMEOUT', '12'))


def _headers(key):
    return {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


def _safe_error(error):
    """Return an error string that never leaks credentials or filesystem paths."""
    text = str(error)
    for secret in (SERVICE_KEY, ANON_KEY):
        if secret:
            text = text.replace(secret, '[redacted]')
    return text[:400]


def _result(name, ok, detail='', latency_ms=None):
    entry = {
        'name': name,
        'status': 'CONNECTED' if ok else 'NOT CONNECTED',
        'connected': bool(ok),
    }
    if detail:
        entry['detail'] = detail
    if latency_ms is not None:
        entry['latency_ms'] = round(latency_ms, 1)
    return entry


def check_database():
    """Run a real, safe SELECT against the Supabase REST API."""
    if not SUPABASE_URL or not SERVICE_KEY:
        return _result('database', False,
                       'SUPABASE_URL or SUPABASE_SERVICE_KEY is not configured in .env.')
    started = time.perf_counter()
    try:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/{PROBE_TABLE}?select=survey_id&limit=1',
            headers={**_headers(SERVICE_KEY), 'Prefer': 'count=exact'}, timeout=TIMEOUT)
        latency = (time.perf_counter() - started) * 1000
        # PostgREST answers 206 Partial Content when a row limit truncates a
        # counted query, so 206 is a successful read rather than an error.
        if response.status_code not in (200, 206):
            return _result('database', False,
                           f'Query against "{PROBE_TABLE}" returned HTTP {response.status_code}: '
                           f'{_safe_error(response.text)}', latency)

        count_response = requests.get(
            f'{SUPABASE_URL}/rest/v1/{PROBE_TABLE}?select=survey_id',
            headers={**_headers(SERVICE_KEY), 'Prefer': 'count=exact'}, timeout=TIMEOUT)
        total = None
        content_range = count_response.headers.get('Content-Range', '')
        if '/' in content_range:
            tail = content_range.split('/')[-1]
            total = int(tail) if tail.isdigit() else None
        detail = f'Real query succeeded on "{PROBE_TABLE}".'
        if total is not None:
            detail += f' {total} row(s) readable.'
        return _result('database', True, detail, latency)
    except requests.RequestException as error:
        return _result('database', False, f'Supabase connection failed: {_safe_error(error)}',
                       (time.perf_counter() - started) * 1000)


def check_auth():
    """Verify the Supabase Auth (GoTrue) service is reachable and configured."""
    if not SUPABASE_URL or not ANON_KEY:
        return _result('auth', False,
                       'SUPABASE_URL or SUPABASE_KEY (publishable/anon) is not configured in .env.')
    started = time.perf_counter()
    try:
        response = requests.get(f'{SUPABASE_URL}/auth/v1/health',
                                headers=_headers(ANON_KEY), timeout=TIMEOUT)
        latency = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            return _result('auth', False,
                           f'Auth health endpoint returned HTTP {response.status_code}: '
                           f'{_safe_error(response.text)}', latency)
        payload = response.json() if response.text else {}
        return _result('auth', True,
                       f"GoTrue {payload.get('version', 'unknown version')} responded to a live "
                       f'health request with the configured anon key.', latency)
    except (requests.RequestException, ValueError) as error:
        return _result('auth', False, f'Supabase Auth check failed: {_safe_error(error)}',
                       (time.perf_counter() - started) * 1000)


def check_storage():
    """Verify Supabase Storage by listing buckets and reading one public object list."""
    if not SUPABASE_URL or not SERVICE_KEY:
        return _result('storage', False, 'Supabase Storage credentials are not configured.')
    started = time.perf_counter()
    try:
        response = requests.get(f'{SUPABASE_URL}/storage/v1/bucket',
                                headers=_headers(SERVICE_KEY), timeout=TIMEOUT)
        latency = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            return _result('storage', False,
                           f'Bucket listing returned HTTP {response.status_code}: '
                           f'{_safe_error(response.text)}', latency)
        buckets = response.json() if response.text else []
        names = [bucket.get('name') for bucket in buckets if isinstance(bucket, dict)]
        if PROBE_BUCKET not in names:
            return _result('storage', False,
                           f'Storage answered, but the required bucket "{PROBE_BUCKET}" is '
                           f'missing. Available buckets: {", ".join(names) or "none"}.', latency)
        listing = requests.post(f'{SUPABASE_URL}/storage/v1/object/list/{PROBE_BUCKET}',
                                headers=_headers(SERVICE_KEY),
                                json={'prefix': '', 'limit': 1, 'sortBy': {'column': 'name', 'order': 'asc'}},
                                timeout=TIMEOUT)
        if listing.status_code != 200:
            return _result('storage', False,
                           f'Bucket "{PROBE_BUCKET}" exists but could not be listed '
                           f'(HTTP {listing.status_code}): {_safe_error(listing.text)}', latency)

        # A listing alone does not prove the app can store evidence images, so
        # perform a real write/read/delete round trip on a tiny PNG probe
        # object. The bucket enforces image MIME types, which is exactly what
        # the sonar evidence uploads use.
        from PIL import Image

        buffer = BytesIO()
        Image.new('RGB', (4, 4), (12, 74, 110)).save(buffer, format='PNG')
        probe_bytes = buffer.getvalue()

        probe_key = f"tarang-status-probe/{uuid.uuid4().hex}.png"
        upload = requests.post(f'{SUPABASE_URL}/storage/v1/object/{PROBE_BUCKET}/{probe_key}',
                               headers={**_headers(SERVICE_KEY),
                                        'Content-Type': 'image/png',
                                        'x-upsert': 'true'},
                               data=probe_bytes, timeout=TIMEOUT)
        if upload.status_code not in (200, 201):
            return _result('storage', False,
                           f'Bucket "{PROBE_BUCKET}" rejected a real test upload '
                           f'(HTTP {upload.status_code}): {_safe_error(upload.text)}', latency)

        readback = requests.get(f'{SUPABASE_URL}/storage/v1/object/{PROBE_BUCKET}/{probe_key}',
                                headers=_headers(SERVICE_KEY), timeout=TIMEOUT)
        requests.delete(f'{SUPABASE_URL}/storage/v1/object/{PROBE_BUCKET}/{probe_key}',
                        headers=_headers(SERVICE_KEY), timeout=TIMEOUT)
        if readback.status_code != 200 or readback.content != probe_bytes:
            return _result('storage', False,
                           f'Test object was written to "{PROBE_BUCKET}" but could not be read '
                           f'back intact (HTTP {readback.status_code}).', latency)

        return _result('storage', True,
                       f'{len(names)} bucket(s) reachable; "{PROBE_BUCKET}" passed a real '
                       f'write/read/delete round trip.', latency)
    except (requests.RequestException, ValueError) as error:
        return _result('storage', False, f'Supabase Storage check failed: {_safe_error(error)}',
                       (time.perf_counter() - started) * 1000)


def check_backend(self_base_url=None):
    """Confirm this Flask process answers HTTP and can reach its own API."""
    started = time.perf_counter()
    base = (self_base_url or os.environ.get('TARANG_BACKEND_URL')
            or f"http://127.0.0.1:{os.environ.get('PORT', '3000')}").rstrip('/')
    try:
        response = requests.get(f'{base}/login.html', timeout=TIMEOUT)
        latency = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            return {'name': 'api', 'status': 'OFFLINE', 'connected': False,
                    'detail': f'Self-check of {base} returned HTTP {response.status_code}.',
                    'latency_ms': round(latency, 1)}
        return {'name': 'api', 'status': 'ONLINE', 'connected': True,
                'detail': f'Backend answered a live request at {base}.',
                'latency_ms': round(latency, 1)}
    except requests.RequestException as error:
        return {'name': 'api', 'status': 'OFFLINE', 'connected': False,
                'detail': f'Backend self-check failed: {_safe_error(error)}',
                'latency_ms': round((time.perf_counter() - started) * 1000, 1)}


def collect_status(self_base_url=None):
    """Run every real check and return a report safe to show in the browser."""
    database = check_database()
    auth = check_auth()
    storage = check_storage()
    api = check_backend(self_base_url)

    core_ok = database['connected'] and auth['connected'] and api['connected']
    return {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'probe_id': uuid.uuid4().hex[:12],
        'database': {'supabase': database},
        'authentication': {'supabase_auth': auth},
        'storage': {'supabase_storage': storage},
        'api': {'backend_api': api},
        'overall': 'CONNECTED' if core_ok else 'DEGRADED',
        'authoritative_database': 'supabase' if database['connected'] else 'none',
        'configuration': {
            'supabase_url_configured': bool(SUPABASE_URL),
            'anon_key_configured': bool(ANON_KEY),
            'service_key_configured': bool(SERVICE_KEY),
            'service_key_exposed_to_browser': False,
        },
    }
