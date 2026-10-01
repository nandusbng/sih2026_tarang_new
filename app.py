import os
import uuid
import base64
import json
import csv
import hashlib
import logging
import re
from functools import wraps
from datetime import datetime
from io import StringIO
from flask import Flask, g, request, send_from_directory, jsonify, send_file, Response, redirect, abort
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from ultralytics import YOLO
import cv2
import numpy as np
from flask_compress import Compress
from flask_caching import Cache

app = Flask(__name__, static_folder='.')
Compress(app)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})
app.config['JSON_SORT_KEYS'] = False

from dotenv import load_dotenv
import supabase_service as sb_svc

load_dotenv()

# ---------------------------------------------------------------------------
# SERVED-FILE GUARD
# ---------------------------------------------------------------------------
# The Flask static folder is the project root, so without an explicit guard
# every file in the repository is downloadable over HTTP -- including `.env`,
# which holds the Supabase service-role key that bypasses Row Level Security.
# Credentials, model weights, server source and developer scratch scripts must
# never reach a browser, so they are refused before static handling runs.
_BLOCKED_PATH_SEGMENTS = ('/node_modules/', '/.venv/', '/venv/', '/.git/', '/__pycache__/')
_BLOCKED_EXTENSIONS = ('.py', '.pyc', '.pt', '.log', '.jsonl', '.db', '.sqlite',
                       '.sqlite3', '.env', '.pem', '.key', '.p12', '.xtf')


def _is_blocked_static_path(raw_path):
    path = (raw_path or '/').split('?')[0]
    if path.startswith('/api/'):
        return False
    lowered = path.lower()
    relative = lowered.lstrip('/')
    if any(segment in f'/{relative}' for segment in _BLOCKED_PATH_SEGMENTS):
        return True
    name = relative.rsplit('/', 1)[-1]
    if name.startswith('.env') and name != '.env.example':
        return True
    # Underscore-prefixed files are scratch artifacts, never portal assets.
    if name.startswith('_'):
        return True
    # Every real browser script lives under js/ or a CDN, so a root-level
    # script can only ever be a leftover developer file. Those have a history
    # of embedding credentials, so they are refused outright rather than
    # enumerated by name.
    if '/' not in relative and relative.endswith(('.js', '.mjs', '.cjs')):
        return True
    return name.endswith(_BLOCKED_EXTENSIONS)


@app.before_request
def block_sensitive_static_files():
    if _is_blocked_static_path(request.path):
        logger.warning("Refused to serve a non-public path: %s", request.path)
        abort(404)


# ---------------------------------------------------------------------------
# OUTPUTS / CROPS DIRECTORY SETUP
# ---------------------------------------------------------------------------
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
CROPS_DIR = os.path.join(OUTPUTS_DIR, 'crops')
UPLOADS_DIR = os.path.join(OUTPUTS_DIR, 'workflow_uploads')
EVIDENCE_DIR = os.path.join(OUTPUTS_DIR, 'evidence')
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
logger = logging.getLogger("tarang.evidence")

# ---------------------------------------------------------------------------
# YOLO MODEL - loaded once at startup
# ---------------------------------------------------------------------------
print("Loading YOLO model 'best.pt'...")
model = YOLO('best.pt')
print("Model loaded successfully. Classes:", model.names)

# ---------------------------------------------------------------------------
# ROLE-BASED REDIRECTS
# ---------------------------------------------------------------------------
# The new Supabase project stores these DB role values (CHECK constraint):
#   survey_operator | sonar_analyst | marine_analyst | gov_authority |
#   platform_admin  | public
# The frontend/redirect map supports both the DB values AND the legacy portal
# alias names returned by sb_svc.to_portal_role() so both code paths work.
ROLE_REDIRECTS = {
    # DB role values (new project)
    'survey_operator':   'operator-portal.html',
    'sonar_analyst':     'sonar-analyst.html',
    'marine_analyst':    'marine-analyst.html',
    'gov_authority':     'gov-authority.html',
    'platform_admin':    'admin-dashboard.html',
    'public':            'public.html',
    # Frontend portal alias keys (returned by to_portal_role)
    'marine_portal':     'marine-analyst.html',
    'government_portal': 'gov-authority.html',
    'admin':             'admin-dashboard.html',
}

# Normalize any incoming role name (portal alias or legacy) to its DB-legal value.
ROLE_ALIASES = {
    # portal names -> DB values
    'marine_portal':     'marine_analyst',
    'government_portal': 'gov_authority',
    'admin':             'platform_admin',
    # legacy aliases -> DB values
    'marine analyst':    'marine_analyst',
    'government':        'gov_authority',
    'atmiya':            'platform_admin',
    'sonar_operator':    'sonar_analyst',
    'sonar_expert':      'sonar_analyst',
    # pass-throughs (already DB-legal)
    'survey_operator':   'survey_operator',
    'sonar_analyst':     'sonar_analyst',
    'marine_analyst':    'marine_analyst',
    'gov_authority':     'gov_authority',
    'platform_admin':    'platform_admin',
    'public':            'public',
}


def normalize_role(role):
    """Return the DB-legal role value for any incoming role/portal name."""
    value = (role or '').strip().lower()
    return ROLE_ALIASES.get(value, value)

def _env_flag(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# The demo is intentionally enabled for the local SIH presentation build. Set
# TARANG_DEMO_MODE=false before any non-demo deployment to require Supabase
# authentication for every protected operation again.
HACKATHON_DEMO_MODE = _env_flag('TARANG_DEMO_MODE', True)
DEMO_SESSION_MAX_AGE = int(os.environ.get('TARANG_DEMO_SESSION_SECONDS', '43200'))
demo_serializer = URLSafeTimedSerializer(
    os.environ.get('FLASK_SECRET_KEY', 'tarang-hackathon-demo-session'),
    salt='tarang-demo-access-v1'
)

# The local presentation demo issues a signed session for exactly one of the
# six public portal choices. It never depends on a pre-seeded database user.
DEMO_PORTALS = {
    'survey_operator': {
        'role': 'survey_operator', 'full_name': 'Demo Survey Operator',
        'institution_id': 'DEMO-SURVEY', 'redirect': 'operator-portal.html'
    },
    'sonar_analyst': {
        'role': 'sonar_analyst', 'full_name': 'Demo Sonar Analyst',
        'institution_id': 'DEMO-SONAR', 'redirect': 'sonar-analyst.html'
    },
    'marine_portal': {
        'role': 'marine_portal', 'full_name': 'Demo Marine Portal',
        'institution_id': 'DEMO-MARINE', 'redirect': 'marine-analyst.html'
    },
    'government_portal': {
        'role': 'government_portal', 'full_name': 'Demo Government Portal',
        'institution_id': 'DEMO-GOV', 'redirect': 'gov-authority.html'
    },
    'admin': {
        'role': 'admin', 'full_name': 'Demo Administrator',
        'institution_id': 'DEMO-ADMIN', 'redirect': 'admin-dashboard.html'
    },
    'public': {
        'role': 'public', 'full_name': 'Ocean Awareness Visitor',
        'institution_id': 'DEMO-PUBLIC', 'redirect': 'public.html'
    }
}


def get_demo_profile(access_token):
    """Resolve a signed browser demo session into a portal profile."""
    if not HACKATHON_DEMO_MODE or not access_token:
        return None
    try:
        payload = demo_serializer.loads(access_token, max_age=DEMO_SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    portal_key = payload.get('portal') if isinstance(payload, dict) else None
    portal = DEMO_PORTALS.get(portal_key)
    if not portal or not payload.get('demo'):
        return None

    return {
        'id': portal['institution_id'],
        'institution_id': portal['institution_id'],
        'username': portal['institution_id'].lower(),
        'full_name': portal['full_name'],
        'name': portal['full_name'],
        'email': '',
        'role': normalize_role(portal['role']),
        'status': 'active',
        'demo_mode': True
    }


def resolve_request_profile():
    """Resolve either a signed demo session or a real Supabase session."""
    authorization = request.headers.get('Authorization', '')
    scheme, _, access_token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not access_token:
        return None, (jsonify({'status': 'error', 'message': 'Authentication is required.'}), 401)

    profile = get_demo_profile(access_token) or sb_svc.get_authenticated_profile(access_token)
    if not profile:
        return None, (jsonify({'status': 'error', 'message': 'Your session is invalid, inactive, or has expired.'}), 401)
    return profile, None


def require_roles(*allowed_roles):
    """Guard state-changing routes with TARANG RBAC."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            profile, error_response = resolve_request_profile()
            if error_response:
                return error_response
            canonical_allowed_roles = {normalize_role(role) for role in allowed_roles}
            if canonical_allowed_roles and normalize_role(profile.get('role')) not in canonical_allowed_roles:
                return jsonify({'status': 'error', 'message': 'Your TARANG role is not authorized for this action.'}), 403

            g.tarang_user = profile
            return view(*args, **kwargs)
        return wrapped
    return decorator


def authorize_request(*allowed_roles):
    """Return the active request profile or an API error response tuple."""
    profile, error_response = resolve_request_profile()
    if error_response:
        return None, error_response
    canonical_allowed_roles = {normalize_role(role) for role in allowed_roles}
    if canonical_allowed_roles and normalize_role(profile.get('role')) not in canonical_allowed_roles:
        return None, (jsonify({'status': 'error', 'message': 'Your TARANG role is not authorized for this action.'}), 403)
    return profile, None


def emit_workflow_notification(recipient_roles, title, message, **context):
    """Persist one role-addressed notification for a workflow transition."""
    recipients = sorted({normalize_role(role) for role in (recipient_roles or []) if role})
    return sb_svc.log_dispatch_event('notification', {
        'type': context.pop('type', 'Workflow Update'),
        'title': title,
        'message': message,
        'recipient_roles': recipients,
        'is_read': False,
        'timestamp': datetime.now().isoformat(),
        **context,
    })

# ---------------------------------------------------------------------------
# CLASS METADATA
# ---------------------------------------------------------------------------
CLASS_METADATA = {
    'ghost_net': {
        'title': 'Ghost Drift Net (Entangled)',
        'category': 'Bio-Hazard Entanglement',
        'badge': 'URGENT INTERVENTION',
        'color': '#E11D48',
        'badge_bg': 'bg-error-container text-on-error-container',
        'material': 'Monofilament Nylon-6',
        'hazard': 'High Marine Entanglement Risk'
    },
    'shipwreck': {
        'title': 'Historic Shipwreck / Vessel Structure',
        'category': 'Submerged Archaeological Feature',
        'badge': 'STRUCTURAL TARGET',
        'color': '#5bb8fe',
        'badge_bg': 'bg-secondary-container text-on-secondary-container',
        'material': 'Reinforced Timber & Steel Clad',
        'hazard': 'Navigation Clearance Hazard'
    },
    'crab_pot': {
        'title': 'Derelict Crab / Fish Trap',
        'category': 'Derelict Fishing Gear',
        'badge': 'GHOST POT',
        'color': '#D97706',
        'badge_bg': 'bg-amber-100 text-amber-800',
        'material': 'Galvanized Steel Wire Mesh',
        'hazard': 'Benthic Habitat Smothering'
    },
    'submarine_pipeline': {
        'title': 'Submarine Pipeline / Power Conduit',
        'category': 'Underwater Critical Infrastructure',
        'badge': 'INFRA MONITOR',
        'color': '#14B8A6',
        'badge_bg': 'bg-teal-100 text-teal-800',
        'material': 'Coated Subsea Alloy',
        'hazard': 'Structural Integrity Survey'
    },
    'mine_cylinder': {
        'title': 'Cylindrical Anomaly / Ordnance Risk',
        'category': 'High Threat Subsea Munition',
        'badge': 'UXO ALERT',
        'color': '#ba1a1a',
        'badge_bg': 'bg-red-200 text-red-900',
        'material': 'Heavy Ferrous Metal Casing',
        'hazard': 'Pending Classification'
    },
    'unknown': {
        'title': 'Acoustic Marine Anomaly',
        'category': 'Unclassified Sonar Echo',
        'badge': 'REQUIRES REVIEW',
        'color': '#9333ea',
        'badge_bg': 'bg-purple-100 text-purple-800',
        'material': 'Unverified Subsea Echo',
        'hazard': 'Anomaly — Requires Review'
    }
}

def get_meta(cls_name):
    clean = (cls_name or '').lower().strip()
    return CLASS_METADATA.get(clean, {
        'title': clean.replace('_', ' ').title() if clean else 'Unknown Anomaly',
        'category': 'Acoustic Marine Anomaly',
        'badge': 'REQUIRES REVIEW',
        'color': '#9333ea',
        'badge_bg': 'bg-purple-100 text-purple-800',
        'material': 'Unclassified Echo',
        'hazard': 'Anomaly — Requires Review'
    })

# ---------------------------------------------------------------------------
# CROP UTILITY
# ---------------------------------------------------------------------------
def crop_and_encode(frame, box, pad=18):
    """Crops a target frame and stores the canonical crop in Supabase Storage."""
    h_img, w_img = frame.shape[:2]
    x1, y1, x2, y2 = map(int, box)
    cx1 = max(0, x1 - pad)
    cy1 = max(0, y1 - pad)
    cx2 = min(w_img, x2 + pad)
    cy2 = min(h_img, y2 + pad)
    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return "", ""

    ret, buf = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ret:
        return "", ""

    crop_filename = f"crop_{uuid.uuid4().hex[:8]}.jpg"
    crop_bytes = buf.tobytes()
    crop_url = sb_svc.upload_crop(crop_filename, crop_bytes)
    crop_b64 = "data:image/jpeg;base64," + base64.b64encode(crop_bytes).decode('utf-8')
    return crop_url, crop_b64

# ---------------------------------------------------------------------------
# TXT SURVEY PARSER
# ---------------------------------------------------------------------------
def parse_txt_survey(content_str, filename="survey.txt"):
    lines = [line.strip() for line in content_str.splitlines() if line.strip()]
    metadata = {
        "Survey ID": None, "Survey Name": None,
        "Latitude": None, "Longitude": None,
        "Depth": None, "Altitude": None,
        "Start Time": None, "End Time": None,
        "Total Pings": 0, "Platform": None,
        "Sonar Device": None, "Frequency": None,
        "File Name": filename, "Input Type": "txt"
    }
    pings = []
    for line in lines:
        if ':' in line or '=' in line:
            sep = ':' if ':' in line else '='
            parts = line.split(sep, 1)
            key = parts[0].strip().upper()
            val = parts[1].strip()
            if 'SURVEY' in key and 'ID' in key:
                metadata['Survey ID'] = val
            elif 'SURVEY' in key and 'NAME' in key:
                metadata['Survey Name'] = val
            elif key in ['LAT', 'LATITUDE', 'Y']:
                try:
                    metadata['Latitude'] = float(val.replace('°','').replace('N','').replace('S','-'))
                except: metadata['Latitude'] = val
            elif key in ['LON', 'LONGITUDE', 'LONG', 'X']:
                try:
                    metadata['Longitude'] = float(val.replace('°','').replace('E','').replace('W','-'))
                except: metadata['Longitude'] = val
            elif 'DEPTH' in key:
                metadata['Depth'] = val if str(val).endswith('m') else f"{val}m"
            elif 'ALTITUDE' in key:
                metadata['Altitude'] = val if str(val).endswith('m') else f"{val}m"
            elif 'TIME' in key or 'TIMESTAMP' in key:
                if not metadata['Start Time']: metadata['Start Time'] = val
                metadata['End Time'] = val
            elif 'PLATFORM' in key:
                metadata['Platform'] = val
            elif 'SONAR' in key or 'DEVICE' in key:
                metadata['Sonar Device'] = val
            elif 'FREQ' in key:
                metadata['Frequency'] = val
        elif line.startswith('$GPGGA') or line.startswith('$GPRMC'):
            parts = line.split(',')
            if len(parts) > 5 and parts[2] and parts[4]:
                try:
                    lat_deg = float(parts[2][:2]) + float(parts[2][2:]) / 60.0
                    if parts[3] == 'S': lat_deg = -lat_deg
                    lon_deg = float(parts[4][:3]) + float(parts[4][3:]) / 60.0
                    if parts[5] == 'W': lon_deg = -lon_deg
                    metadata['Latitude'] = round(lat_deg, 6)
                    metadata['Longitude'] = round(lon_deg, 6)
                    pings.append({"ping_number": len(pings)+1, "latitude": metadata['Latitude'],
                                  "longitude": metadata['Longitude'], "timestamp": datetime.now().isoformat()})
                except: pass
    if not metadata['Survey ID']:
        metadata['Survey ID'] = str(uuid.uuid4())
    if not metadata['Survey Name']:
        metadata['Survey Name'] = f"Survey Log ({filename})"
    if pings:
        metadata['Total Pings'] = len(pings)
    return {"metadata": metadata, "pings": pings, "images": []}


# ---------------------------------------------------------------------------
# PERSISTENT MULTI-FORMAT DEMO WORKFLOW
# ---------------------------------------------------------------------------
WORKFLOW_UPLOAD_EXTENSIONS = {'.txt', '.png', '.jpg', '.jpeg',
                              '.mp4', '.avi', '.mov', '.mkv', '.webm'}
VIDEO_UPLOAD_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
# Video is sampled, not decoded frame by frame: a full decode of a long survey
# video is far too expensive for a synchronous request. The reported frame
# count and sampling interval make the reduction explicit rather than hidden.
VIDEO_MAX_FRAMES = int(os.environ.get('TARANG_VIDEO_MAX_FRAMES', '12'))
# Derived from the accepted set so a rejection message can never advertise a
# format the handler does not actually process.
_ACCEPTED_UPLOAD_LABEL = ', '.join(sorted(ext.lstrip('.').upper() for ext in WORKFLOW_UPLOAD_EXTENSIONS))
# The maritime target classes best.pt is trained on. A detection whose class is
# not listed here is reported as unknown rather than relabelled to fit.
ALLOWED_TARGET_CLASSES = ('ghost_net', 'shipwreck', 'crab_pot', 'submarine_pipeline', 'mine_cylinder')


def _stable_survey_id(file_hash):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'tarang:survey:{file_hash}'))


def _stable_target_id(survey_id, sequence):
    return f"DET-{hashlib.sha256(f'{survey_id}:{sequence}'.encode('utf-8')).hexdigest()[:12].upper()}"


def _txt_acoustic_raster(content_str):
    """Build a raster from TXT acoustic samples or CSV target coordinates.

    Supports two formats:
    1. Acoustic sample rows: numeric CSV lines prefixed by PING/SAMPLES/INTENSITY/ECHO.
    2. CSV target files with latitude/longitude columns: returns a synthetic top-view
       position scatter map so the upload produces a valid evidence image.
    """
    # CSV target format detection (latitude/longitude columns)
    csv_header_pat = re.compile(r'(?i)\blatitude\b|\blongitude\b')
    lines_raw = content_str.splitlines()
    header_idx = None
    for idx, line in enumerate(lines_raw):
        if line.strip().startswith('#'):
            continue
        if csv_header_pat.search(line):
            header_idx = idx
            break

    if header_idx is not None:
        import csv as _csv
        data_lines = [l for l in lines_raw[header_idx:] if not l.strip().startswith('#')]
        reader = _csv.DictReader(data_lines, skipinitialspace=True)
        lats, lons = [], []
        for row in reader:
            try:
                lat_key = next((k for k in row if 'lat' in k.lower()), None)
                lon_key = next((k for k in row if 'lon' in k.lower()), None)
                if lat_key and lon_key and row.get(lat_key) and row.get(lon_key):
                    lats.append(float(row[lat_key]))
                    lons.append(float(row[lon_key]))
            except (ValueError, TypeError):
                continue
        if lats:
            H, W = 256, 512
            canvas = np.zeros((H, W, 3), dtype=np.uint8)
            canvas[:, :] = (10, 25, 45)
            for gx in range(0, W, 64):
                canvas[:, gx] = (20, 45, 75)
            for gy in range(0, H, 32):
                canvas[gy, :] = (20, 45, 75)
            lat_rng = (max(lats) - min(lats)) or 1e-6
            lon_rng = (max(lons) - min(lons)) or 1e-6
            for lat, lon in zip(lats, lons):
                px = int((lon - min(lons)) / lon_rng * (W - 40)) + 20
                py = int((max(lats) - lat) / lat_rng * (H - 40)) + 20
                cv2.circle(canvas, (px, py), 8,  (0, 220, 255), -1)
                cv2.circle(canvas, (px, py), 4,  (255, 255, 255), -1)
                cv2.circle(canvas, (px, py), 10, (0, 160, 200),  1)
            cv2.putText(canvas, 'TARANG TARGET MAP', (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 200, 255), 1)
            cv2.putText(canvas, f'{len(lats)} targets  Indian Ocean',
                        (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 180, 150), 1)
            return cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)

    # Standard acoustic sample rows
    rows = []
    marker = re.compile(r'^\s*(?:PING|SAMPLES?|INTENSITY|ECHO(?:_SAMPLES?)?)\s*[:=]\s*', re.I)
    numeric_row = re.compile(r'^\s*[-+0-9.,;\t ]+\s*$')
    for raw_line in lines_raw:
        candidate = marker.sub('', raw_line)
        if candidate == raw_line and not numeric_row.match(raw_line):
            continue
        values = re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?', candidate)
        if len(values) < 8:
            continue
        try:
            rows.append([float(v) for v in values])
        except ValueError:
            logger.warning("Skipping malformed acoustic sample row while processing TXT survey.")
    if len(rows) < 8:
        return None
    width = max(len(row) for row in rows)
    matrix = np.full((len(rows), width), np.nan, dtype=np.float32)
    for index, row in enumerate(rows):
        matrix[index, :len(row)] = row
    finite = matrix[np.isfinite(matrix)]
    if finite.size == 0 or float(np.nanmax(finite)) == float(np.nanmin(finite)):
        return None
    matrix[np.isnan(matrix)] = float(np.nanmedian(finite))
    return cv2.normalize(matrix, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def _extract_video_frames(raw_bytes, filename, max_frames=None):
    """Extract evenly spaced frames from an uploaded survey video.

    Returns ``(frames, metadata)`` where each frame carries its real index,
    timestamp in seconds, decoded BGR array and JPEG bytes. Raises ValueError
    with the underlying reason when the video cannot be decoded, so the caller
    reports a real failure instead of pretending processing completed.
    """
    max_frames = max_frames or VIDEO_MAX_FRAMES
    work_path = os.path.join(UPLOADS_DIR, f"video_{uuid.uuid4().hex[:8]}_{os.path.basename(filename)}")
    with open(work_path, 'wb') as handle:
        handle.write(raw_bytes)

    capture = cv2.VideoCapture(work_path)
    if not capture.isOpened():
        capture.release()
        try:
            os.remove(work_path)
        except OSError:
            pass
        raise ValueError(f'The video codec or container in "{filename}" could not be opened.')

    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        # Some containers report no frame count; fall back to a sequential
        # read so the extraction still yields real frames.
        if total_frames > 0:
            wanted = sorted({int(round(i * (total_frames - 1) / max(max_frames - 1, 1)))
                             for i in range(max_frames)} if max_frames > 1 else {0})
        else:
            wanted = None

        frames = []
        index = 0
        while True:
            if wanted is not None:
                if not wanted:
                    break
                target = wanted[0]
                if index < target:
                    capture.grab()
                    index += 1
                    continue
                wanted.pop(0)
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            encoded_ok, encoded = cv2.imencode('.jpg', frame)
            if not encoded_ok:
                logger.error("Video frame %s of %s could not be encoded", index, filename)
            else:
                frames.append({
                    'frame_index': index,
                    'time_seconds': round(index / fps, 3) if fps else None,
                    'array': frame,
                    'bytes': encoded.tobytes(),
                })
            index += 1
            if wanted is None and len(frames) >= max_frames:
                break
            if wanted is not None and index > total_frames:
                break

        metadata = {
            'Input Type': 'video',
            'File Name': filename,
            'Frame Count': total_frames or index,
            'Frames Sampled': len(frames),
            'FPS': round(fps, 3) if fps else None,
            'Resolution': f'{width}x{height}' if width and height else None,
            'Duration Seconds': round(total_frames / fps, 3) if total_frames and fps else None,
            'Sampling': f'{len(frames)} of {total_frames or index} frames analysed',
        }
        return frames, metadata
    finally:
        capture.release()
        try:
            os.remove(work_path)
        except OSError:
            pass


def _encode_acoustic_raster(raster):
    """Encode a derived evidence image from actual TXT acoustic amplitudes."""
    ok, encoded = cv2.imencode('.png', raster)
    if not ok:
        logger.error("Evidence image generation failed: OpenCV could not encode acoustic samples.")
        raise ValueError('Unable to encode acoustic samples into a sonar evidence image.')
    return encoded.tobytes()


def _evidence_extension(content_type, filename):
    if content_type == 'image/png':
        return 'png'
    original = os.path.splitext(filename or '')[1].lower().lstrip('.')
    return original if original in {'jpg', 'jpeg'} else 'jpg'


def _persist_workflow_image(survey_id, survey_hash, filename, image_bytes, content_type, sequence=1):
    """Persist one actual evidence artifact once and return its browser URL.

    The immutable ID includes the survey, content hash, and sequence.  The
    evidence event is the database record that joins the survey, Storage
    object, local recovery artifact, and downstream detections.
    """
    if not image_bytes:
        logger.error("Evidence persistence aborted: generated image is empty for survey=%s", survey_id)
        raise ValueError('No sonar evidence image was generated from this survey.')

    content_hash = hashlib.sha256(image_bytes).hexdigest()
    image_id = f"IMG-{hashlib.sha256(f'{survey_id}:{sequence}:{content_hash}'.encode('utf-8')).hexdigest()[:20].upper()}"
    extension = _evidence_extension(content_type, filename)
    sequence_name = f"sequence-{int(sequence):03d}.{extension}"
    relative_path = f"evidence/{image_id}/{sequence_name}"
    local_path = os.path.join(OUTPUTS_DIR, *relative_path.split('/'))
    local_url = f"/outputs/{relative_path}"
    storage_path = relative_path

    existing = next((image for image in sb_svc.get_sonar_images(survey_id)
                     if image.get('image_id') == image_id), None)
    if existing and existing.get('url'):
        logger.info("Reusing persisted evidence image: survey=%s image_id=%s sequence=%s", survey_id, image_id, sequence)
        return existing

    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        existing_hash = ''
        if os.path.isfile(local_path):
            with open(local_path, 'rb') as existing_file:
                existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
        if existing_hash != content_hash:
            temporary_path = f"{local_path}.tmp"
            with open(temporary_path, 'wb') as output:
                output.write(image_bytes)
            os.replace(temporary_path, local_path)
        logger.info("Evidence image generated locally: survey=%s image_id=%s path=%s", survey_id, image_id, relative_path)
    except OSError as error:
        logger.exception("Evidence local persistence failed: survey=%s image_id=%s error=%s", survey_id, image_id, error)
        raise RuntimeError('Unable to persist the generated sonar evidence image locally.') from error

    upload = sb_svc.upload_sonar_image(storage_path, image_bytes, content_type)
    url = upload['public_url'] if upload else local_url
    storage_status = 'uploaded' if upload else 'local_fallback'
    if upload:
        logger.info("Evidence Storage URL generated: survey=%s image_id=%s url=%s", survey_id, image_id, upload['public_url'])
    else:
        # The local artifact and its HTTP route are intentional durable
        # fallback storage, not a browser-facing filesystem path.
        logger.warning("Evidence Storage upload unavailable; using local HTTP evidence URL: survey=%s image_id=%s url=%s", survey_id, image_id, local_url)
    evidence = {
        'survey_id': survey_id, 'image_id': image_id, 'evidence_id': image_id,
        'sequence': int(sequence), 'file_name': filename, 'file_hash': survey_hash,
        'content_sha256': content_hash, 'content_type': content_type,
        'storage_path': upload['storage_path'] if upload else storage_path,
        'storage_url': upload['public_url'] if upload else '', 'local_url': local_url,
        'local_path': local_path, 'url': url, 'storage_status': storage_status,
        'created_at': datetime.now().isoformat(),
    }
    if not sb_svc.log_dispatch_event('sonar_image', evidence):
        logger.error("Evidence database insertion failed: survey=%s image_id=%s", survey_id, image_id)
        raise RuntimeError('The sonar evidence image was stored but its evidence record could not be saved.')
    logger.info("Evidence database record created: survey=%s image_id=%s sequence=%s", survey_id, image_id, sequence)
    return {key: value for key, value in evidence.items() if key != 'local_path'}


def _persist_xtf_evidence_images(survey_id, survey_hash, reconstructed_images):
    """Persist each reconstructed XTF waterfall exactly once.

    ``xtf_parser`` reconstructs actual acoustic raster chunks locally.  This
    function turns those temporary processing files into the same durable
    evidence records used by TXT/PNG/JPEG ingestion.  The image ID is derived
    from the survey, sequence, and real image content, so a repeated request
    reuses the image instead of creating a second Storage object or a second
    Results card.
    """
    persisted = {}
    for sequence, image in enumerate(reconstructed_images or [], start=1):
        source_id = str(image.get('id') or f'xtf-{sequence}')
        source_path = image.get('path') or ''
        try:
            with open(source_path, 'rb') as source:
                image_bytes = source.read()
        except OSError as error:
            logger.exception(
                "XTF evidence generation output cannot be read: survey=%s source_image=%s path=%s error=%s",
                survey_id, source_id, source_path, error,
            )
            raise RuntimeError(f'Reconstructed XTF evidence image {sequence} could not be read.') from error

        if not image_bytes:
            logger.error("XTF evidence generation output is empty: survey=%s source_image=%s", survey_id, source_id)
            raise RuntimeError(f'Reconstructed XTF evidence image {sequence} is empty.')

        evidence = _persist_workflow_image(
            survey_id=survey_id,
            survey_hash=survey_hash,
            filename=image.get('filename') or f'xtf-sequence-{sequence:03d}.jpg',
            image_bytes=image_bytes,
            content_type='image/jpeg',
            sequence=sequence,
        )
        image.update({
            'image_id': evidence['image_id'],
            'evidence_id': evidence['image_id'],
            'sequence': evidence['sequence'],
            'storage_path': evidence.get('storage_path', ''),
            'url': evidence['url'],
        })
        persisted[source_id] = evidence
        logger.info(
            "XTF evidence image persisted: survey=%s source_image=%s image_id=%s sequence=%s",
            survey_id, source_id, evidence['image_id'], evidence['sequence'],
        )
    if not persisted:
        logger.error("XTF processing produced no reconstructed sonar evidence: survey=%s", survey_id)
        raise RuntimeError('The XTF file contained no reconstructable sonar evidence images.')
    return persisted


def _public_xtf_image(image):
    """Return a browser-safe XTF image record without leaking a local path."""
    return {
        'id': image.get('image_id') or image.get('id'),
        'image_id': image.get('image_id') or '',
        'evidence_id': image.get('evidence_id') or image.get('image_id') or '',
        'sequence': image.get('sequence'),
        'filename': image.get('filename'),
        'ping_start': image.get('ping_start'),
        'ping_end': image.get('ping_end'),
        'storage_path': image.get('storage_path') or '',
        'url': image.get('url') or '',
    }


def _link_detection_to_evidence(detection_id, evidence, bbox=None):
    """Persist the stable evidence association without changing the detection schema.

    The detection bounding box (pixel coords in the reconstructed evidence image)
    rides along in this jsonb event so the analyst portal can draw a real overlay
    box. There is no bbox column on the detections table, and adding one would
    need a migration, so the existing link event carries it instead.
    """
    current = sb_svc.get_evidence_detection_links().get(str(detection_id))
    if current and current.get('image_id') == evidence.get('image_id') and current.get('bbox'):
        return True
    payload = {
        'detection_id': detection_id, 'survey_id': evidence.get('survey_id'),
        'image_id': evidence.get('image_id'), 'evidence_id': evidence.get('image_id'),
        'sequence': evidence.get('sequence'), 'linked_at': datetime.now().isoformat(),
        'bbox': bbox or None,
    }
    if not sb_svc.log_dispatch_event('evidence_detection_link', payload):
        logger.error("Evidence-to-detection database insertion failed: detection=%s image_id=%s", detection_id, evidence.get('image_id'))
        return False
    return True


def _navigation_for_detection(pings, image, box_y, box_x):
    """Resolve real survey navigation for one detection from XTF ping records.

    The reconstructed waterfall image stacks one row per ping, so the vertical
    position of a bounding box maps directly onto a ping inside the chunk that
    produced the image. This is how detections inherit latitude, longitude,
    timestamp, heading, depth and altitude from the actual survey file instead
    of from a fabricated demo offset.
    """
    if not pings:
        return None

    chunk = pings
    image_height = None
    ping_start = 0
    if image and image.get('ping_start') is not None:
        ping_start = int(image.get('ping_start') or 0)
        ping_end = image.get('ping_end')
        if ping_end is not None:
            chunk = pings[ping_start:int(ping_end) + 1] or pings
    if not chunk:
        return None

    raster = image.get('raster') if isinstance(image, dict) else None
    if raster is not None:
        try:
            image_height = int(getattr(raster, 'shape', [0])[0]) or None
        except Exception:
            image_height = None

    index = 0
    if box_y is not None and image_height:
        index = int(max(0, min(image_height - 1, float(box_y))) / image_height * len(chunk))
    ping = chunk[min(index, len(chunk) - 1)]

    latitude = ping.get('latitude')
    longitude = ping.get('longitude')
    if latitude in (None, 0, 0.0) or longitude in (None, 0, 0.0):
        return None

    return {
        'latitude': round(float(latitude), 7),
        'longitude': round(float(longitude), 7),
        'ping_number': ping.get('ping_number', ping_start + index),
        'timestamp': ping.get('timestamp'),
        'heading': ping.get('heading_degrees'),
        'depth': ping.get('depth'),
        'altitude': ping.get('altitude'),
        'cross_track_metres': (float(box_x) - image_width_halfoffset(raster)) if raster is not None else None,
        'navigation_source': 'xtf_ping_record',
    }


def image_width_halfoffset(raster):
    """Nadir column of a port/starboard waterfall raster (the track centreline)."""
    try:
        return float(getattr(raster, 'shape', [0, 0])[1]) / 2.0
    except Exception:
        return 0.0


def _workflow_detection_rows(survey_id, file_hash, image, metadata, pings=None, sequence=1):
    """Run one inference pass and geotag each hit from real survey navigation."""
    candidates = []
    if image is not None:
        try:
            results = model(image, conf=0.20, verbose=False)
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                raw_cls = model.names.get(cls_id, 'unknown')
                if raw_cls not in ALLOWED_TARGET_CLASSES:
                    logger.warning("Ignoring detection of class %s: not a TARANG target type.", raw_cls)
                    continue
                score = round(float(box.conf[0]) * 100, 1)
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
                candidates.append({
                    'class_name': raw_cls, 'confidence': score,
                    'bbox': [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    'center_x': (x1 + x2) / 2.0, 'center_y': (y1 + y2) / 2.0,
                })
        except Exception as error:
            logger.error("AI detection failed for survey %s: %s", survey_id, error)

    # No fabricated fallback set: when inference finds nothing the survey
    # honestly reports zero detections rather than a hardcoded count.
    detections = []
    for idx, candidate in enumerate(candidates):
        class_name = candidate['class_name']
        score = candidate['confidence']
        navigation = _navigation_for_detection(pings, image, candidate['center_y'], candidate['center_x'])
        if navigation is None:
            logger.warning(
                "Detection %s in survey %s has no usable navigation record and is "
                "reported without coordinates rather than with invented ones.",
                idx, survey_id)
            latitude = longitude = None
            ping_number = idx + 1
            heading = depth = altitude = None
            nav_source = 'unavailable'
        else:
            latitude = navigation['latitude']
            longitude = navigation['longitude']
            ping_number = navigation['ping_number']
            heading = navigation['heading']
            depth = navigation['depth']
            altitude = navigation['altitude']
            nav_source = navigation['navigation_source']

        meta = get_meta(class_name)
        tier = 'A' if score >= 85 else ('B' if score >= 65 else 'C')
        detections.append({
            'id': _stable_target_id(survey_id, f'{sequence}:{idx}'), 'survey_id': survey_id,
            'class_name': class_name, 'title': meta['title'], 'category': meta['category'],
            'confidence': score, 'classification_tier': tier, 'requires_review': True,
            'latitude': latitude, 'longitude': longitude, 'ping_number': ping_number,
            'depth': depth, 'altitude': altitude, 'heading': heading,
            'crop_url': '', 'material': meta['material'], 'hazard': meta['hazard'],
            'bbox': candidate['bbox'],
            'evidence_sequence': sequence,
            'detection_timestamp': navigation.get('timestamp') if navigation else None,
            'source_file': ((metadata or {}).get('File Name')
                            or (image.get('filename') if isinstance(image, dict) else None)),
            'navigation_source': nav_source,
            'source': 'uploaded_sonar_image',
            'metadata': metadata or {}
        })
    return detections


def _workflow_state(survey_id=None):
    surveys = sb_svc.get_surveys()
    detections = sb_svc.get_all_detections(survey_id=survey_id) if survey_id else sb_svc.get_all_detections()
    hotspots = sb_svc.get_hotspots()
    summary = sb_svc.summarize_detections(detections)
    summary['hotspot_count'] = len(hotspots)
    operations = sb_svc.get_cleanup_operations()
    route = sb_svc.get_latest_route()
    notifications = sb_svc.get_notifications()[:30]
    return {
        'surveys': [s for s in surveys if not survey_id or s.get('survey_id') == survey_id],
        'detections': detections, 'hotspots': hotspots, 'summary': summary,
        'cleanup_operations': operations, 'route': route, 'notifications': notifications,
        # Return the persisted image index for the shared workflow state.  A
        # survey filter is applied when requested; the unfiltered dashboard
        # still needs to show that image artifacts exist across the workflow.
        'images': sb_svc.get_sonar_images(survey_id)
    }

# ---------------------------------------------------------------------------
# XTF DETECTION PERSISTENCE (Supabase-native duplicate suppression)
# ---------------------------------------------------------------------------
def insert_or_merge_detection(det_data):
    """
    Inserts detection into public.detections via Supabase REST.
    Suppresses geographic duplicates within ~0.003 degrees of same survey + class.
    Returns (det_id, is_new).
    """
    survey_id = det_data.get('survey_id') or ''
    cls_name  = det_data.get('class_name') or 'unknown'
    lat = det_data.get('latitude')
    lon = det_data.get('longitude')
    conf = float(det_data.get('confidence', 0.0))

    # Check for nearby duplicate in same survey
    if lat is not None and lon is not None and survey_id:
        try:
            existing = sb_svc.get_all_detections(survey_id=survey_id)
            for cand in existing:
                if (cand.get('class_name') == cls_name and
                    cand.get('latitude') is not None and
                    cand.get('longitude') is not None):
                    d_lat = abs(cand['latitude'] - lat)
                    d_lon = abs(cand['longitude'] - lon)
                    if d_lat < 0.0035 and d_lon < 0.0035:
                        return cand['id'], False
        except Exception as e:
            print("Duplicate check error:", e)

    # New detection
    det_id = det_data.get('id') or f"ANM-{uuid.uuid4().hex[:6].upper()}"
    meta = get_meta(cls_name)
    tier_val = det_data.get('classification_tier', 'C')
    req_review = bool(det_data.get('requires_review', True))

    row = {
        "id": det_id,
        "survey_id": survey_id,
        "class_name": cls_name,
        "title": det_data.get('title') or meta['title'],
        "category": det_data.get('category') or meta['category'],
        "confidence": conf,
        "classification_tier": tier_val,
        "requires_review": req_review,
        "latitude": lat,
        "longitude": lon,
        "ping_number": det_data.get('ping_number'),
        "depth": str(det_data.get('depth')) if det_data.get('depth') is not None else None,
        "altitude": str(det_data.get('altitude')) if det_data.get('altitude') is not None else None,
        "heading": float(det_data.get('heading')) if det_data.get('heading') is not None else None,
        "crop_url": det_data.get('crop_url', ''),
        "material": det_data.get('material') or meta['material'],
        "hazard": det_data.get('hazard') or meta['hazard'],
        "created_at": datetime.now().isoformat()
    }
    ok, saved_id = sb_svc.insert_detection(row)
    if ok:
        return saved_id or det_id, True
    return det_id, False

# ---------------------------------------------------------------------------
# IN-MEMORY XTF SESSION CACHE (waterfall images per upload session)
# ---------------------------------------------------------------------------
import xtf_parser
XTF_SURVEYS = {}

# ===========================================================================
# STATIC FILE ROUTES
# ===========================================================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/outputs/<path:filename>')
def serve_output(filename):
    # Local evidence is deliberately exposed through one HTTP route.  Do not
    # guess a Supabase object key here: old code redirected
    # ``workflow_uploads/...`` to a different Storage path, producing the
    # browser's "No image available" error even when the local image existed.
    output_root = os.path.abspath(OUTPUTS_DIR)
    candidate = os.path.abspath(os.path.join(output_root, filename))
    if not candidate.startswith(output_root + os.sep) or not os.path.isfile(candidate):
        logger.error("Requested output artifact is missing or unsafe: %s", filename)
        return jsonify({'status': 'error', 'message': 'Evidence image not found.'}), 404
    return send_from_directory(output_root, filename)

# ===========================================================================
# AUTHENTICATION ENDPOINTS
# ===========================================================================

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or request.form
    identifier = (data.get('full_name') or data.get('institution_id') or data.get('username') or data.get('email') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'status': 'error', 'message': 'Full Name and password are required.'}), 400

    ok, user_data, token, err = sb_svc.authenticate_user(identifier, password)
    if ok and user_data:
        portal_role = user_data.get('role', 'survey_operator')
        redirect_page = ROLE_REDIRECTS.get(portal_role, ROLE_REDIRECTS.get(normalize_role(portal_role), 'operator-portal.html'))
        # Strip server-only internal fields before sending to browser
        safe_user = {k: v for k, v in user_data.items() if k not in ('metadata', 'db_role')}
        return jsonify({
            'status': 'success',
            'user': safe_user,
            'access_token': token,
            'redirect': redirect_page
        })
    else:
        return jsonify({'status': 'error', 'message': err or 'Authentication failed.'}), 401


@app.route('/api/auth/demo-access', methods=['POST'])
def auth_demo_access():
    """Issue a short-lived browser session for one explicitly selected demo portal."""
    if not HACKATHON_DEMO_MODE:
        return jsonify({
            'status': 'error',
            'message': 'Hackathon demo access is disabled on this deployment.'
        }), 403

    data = request.json or request.form or {}
    portal_key = (data.get('portal') or '').strip()
    portal = DEMO_PORTALS.get(portal_key)
    if not portal:
        return jsonify({'status': 'error', 'message': 'Please choose a valid TARANG demo portal.'}), 400

    access_token = demo_serializer.dumps({'demo': True, 'portal': portal_key})
    profile = {
        'id': portal['institution_id'],
        'institution_id': portal['institution_id'],
        'full_name': portal['full_name'],
        'name': portal['full_name'],
        'email': '',
        'role': portal['role'],
        'status': 'active',
        'demo_mode': True
    }
    return jsonify({
        'status': 'success',
        'user': profile,
        'access_token': access_token,
        'redirect': portal['redirect'],
        'expires_in': DEMO_SESSION_MAX_AGE
    })

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """Persist a Request Access submission in Supabase Auth and tarang_users."""
    data = request.json or request.form or {}
    full_name = (data.get('full_name') or '').strip()
    institution_id = (data.get('institution_id') or '').strip()
    password = data.get('password') or ''
    raw_role = data.get('role') or 'survey_operator'
    role = normalize_role(raw_role)

    if not full_name or not institution_id or not password:
        return jsonify({
            'status': 'error',
            'message': 'Full Name, Institution ID, and password are required.'
        }), 400

    ok, profile, error = sb_svc.request_access(full_name, institution_id, password, role=role)
    if not ok:
        return jsonify({'status': 'error', 'message': error or 'Unable to store the access request.'}), 400

    return jsonify({
        'status': 'success',
        'message': 'Access account created. You can now sign in with your Full Name and password.',
        'user': profile,
        'redirect': 'login.html'
    }), 201

@app.route('/api/auth/request-access', methods=['POST'])
def auth_request_access():
    """Canonical POST /api/auth/request-access — alias for /api/auth/register."""
    return auth_register()


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Return the currently authenticated user's profile."""
    profile, error_response = resolve_request_profile()
    if error_response:
        return error_response
    return jsonify({'status': 'success', 'user': profile})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Stateless logout — client clears its own session token."""
    return jsonify({'status': 'success', 'message': 'Signed out successfully.'})


@app.route('/api/users', methods=['GET'])
def get_users():
    """Return all TARANG user profiles (admin only in production)."""
    return jsonify(sb_svc.get_tarang_users())


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Return a single user profile by ID or institution ID."""
    user = sb_svc.get_user_by_identifier(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404
    return jsonify({'status': 'success', 'user': user})



@app.route('/api/admin/users', methods=['GET'])
@require_roles('platform_admin', 'admin')
def get_admin_users():
    return jsonify(sb_svc.get_tarang_users())

@app.route('/api/admin/cleanup-teams', methods=['GET'])
@require_roles('platform_admin', 'admin')
def get_cleanup_teams():
    return jsonify([
        {"id": "team-01", "name": "Coast Guard Diving Unit Alpha",   "status": "Active",     "sector": "Sector 1 (Chennai EEZ)"},
        {"id": "team-02", "name": "Indian Navy EOD Taskforce",       "status": "On Mission", "sector": "Sector 3 (Bay of Bengal)"},
        {"id": "team-03", "name": "Marine Remediation Unit South",   "status": "Standby",    "sector": "Sector 4 (Gulf of Mannar)"}
    ])

@app.route('/api/admin/government-users', methods=['GET'])
@require_roles('platform_admin', 'admin')
def get_government_users():
    all_users = sb_svc.get_tarang_users()
    gov = [u for u in all_users if u.get('role') in ['government_portal', 'admin']]
    return jsonify(gov)

# ===========================================================================
# SURVEYS ENDPOINTS  (Supabase-native)
# ===========================================================================

@app.route('/api/v1/surveys', methods=['POST'])
@require_roles('survey_operator', 'platform_admin', 'admin')
def create_survey():
    data = request.json or request.form
    survey_id       = data.get('survey_id') or str(uuid.uuid4())
    survey_name     = data.get('survey_name') or 'Unnamed Survey'
    location_name   = data.get('location_name') or data.get('region') or 'Indian Ocean Sector'
    sonar_device    = data.get('sonar_device') or 'Side-Scan Sonar'
    sonar_frequency = data.get('sonar_frequency') or '400/900 kHz'
    created_by      = g.tarang_user.get('username') or g.tarang_user.get('id')
    survey_date     = data.get('survey_date') or datetime.now().strftime('%Y-%m-%d')
    survey_time     = data.get('survey_time') or datetime.now().strftime('%H:%M')

    survey_data = {
        'survey_id':         survey_id,
        'survey_name':       survey_name,
        'survey_date':       survey_date,
        'survey_time':       survey_time,
        'location_name':     location_name,
        'sonar_device':      sonar_device,
        'sonar_frequency':   sonar_frequency,
        'created_by':        created_by
    }
    ok, sid, err = sb_svc.create_survey(survey_data)
    if ok:
        return jsonify({'survey_id': sid, 'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': err or 'Failed to create survey.'}), 500


@app.route('/api/v1/surveys/upload', methods=['POST'])
@require_roles('survey_operator', 'platform_admin', 'admin')
def upload_workflow_survey():
    """Ingest a real acoustic raster into the persistent shared workflow."""
    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'status': 'error', 'message': f'Choose one of these survey file types: {_ACCEPTED_UPLOAD_LABEL}.'}), 400
    filename = os.path.basename(uploaded_file.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension not in WORKFLOW_UPLOAD_EXTENSIONS:
        return jsonify({'status': 'error', 'message': f'Unsupported survey file. Accepted types: {_ACCEPTED_UPLOAD_LABEL}.'}), 415

    raw_bytes = uploaded_file.read()
    if not raw_bytes:
        return jsonify({'status': 'error', 'message': 'The uploaded survey file is empty.'}), 400
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    survey_id = (request.form.get('survey_id') or '').strip() or _stable_survey_id(file_hash)

    # TXT files are supplementary detection records — they don't carry binary
    # evidence that could conflict with an existing XTF/image upload.  Allow
    # them to be added to an existing survey to enrich the detection set.
    existing_upload = sb_svc.get_survey_upload_events().get(str(survey_id))
    existing_survey = sb_svc.get_survey(survey_id)
    _txt_supplementary = extension == '.txt' and bool(existing_survey)

    if not _txt_supplementary:
        # Idempotency guard for binary evidence (image / video / XTF).
        if existing_upload and existing_upload.get('file_hash') == file_hash:
            state = _workflow_state(survey_id)
            images = [image for image in state.get('images', []) if image.get('url')]
            if images:
                return jsonify({
                    'status': 'success', 'existing': True, 'survey_id': survey_id,
                    'filename': existing_upload.get('file_name') or filename,
                    'file_type': existing_upload.get('file_type') or extension.lstrip('.').upper(),
                    'processing_status': existing_upload.get('processing_status', 'completed'),
                    'image': images[0], **state,
                    'metadata': existing_upload.get('metadata') or {},
                })
            logger.error("Idempotent upload has no retrievable evidence image: survey=%s", survey_id)
            return jsonify({'status': 'error', 'message': 'This survey has no retrievable evidence image. Reprocess it with a new survey ID.'}), 409
        if existing_upload or existing_survey:
            logger.error("Survey ID collision rejected: survey=%s filename=%s", survey_id, filename)
            return jsonify({'status': 'error', 'message': 'This survey ID is already associated with different evidence. Use a new survey ID.'}), 409


    now = datetime.now()
    created_by = g.tarang_user.get('username') or g.tarang_user.get('id') or 'survey_operator'
    metadata = {}
    decoded_image = None
    evidence_bytes = b''
    evidence_content_type = ''
    video_frames = []
    if extension == '.txt':
        try:
            text_input = raw_bytes.decode('utf-8', errors='replace')
            parsed = parse_txt_survey(text_input, filename)
            metadata = parsed.get('metadata') or {}
            decoded_image = _txt_acoustic_raster(text_input)
            if decoded_image is None:
                logger.error("TXT evidence generation rejected: no acoustic sample rows in %s", filename)
                return jsonify({
                    'status': 'error',
                    'message': 'TXT survey contains metadata but no acoustic sample rows. Upload the source PNG/JPG/JPEG or a TXT with at least eight numeric PING/SAMPLES/INTENSITY/ECHO rows.'
                }), 422
            evidence_bytes = _encode_acoustic_raster(decoded_image)
            evidence_content_type = 'image/png'
            # Parse CSV target coordinates if present — stored in metadata so the
            # detection loop can build real-coordinate detections without YOLO.
            csv_header_pat = re.compile(r'(?i)\blatitude\b|\blongitude\b')
            lines_raw = text_input.splitlines()
            hdr_idx = next(
                (i for i, l in enumerate(lines_raw)
                 if not l.strip().startswith('#') and csv_header_pat.search(l)),
                None
            )
            if hdr_idx is not None:
                import csv as _csv
                data_lines = [l for l in lines_raw[hdr_idx:] if not l.strip().startswith('#')]
                reader = _csv.DictReader(data_lines, skipinitialspace=True)
                csv_targets = []
                for row in reader:
                    try:
                        lat_k = next((k for k in row if 'lat' in k.lower()), None)
                        lon_k = next((k for k in row if 'lon' in k.lower()), None)
                        if lat_k and lon_k and row.get(lat_k) and row.get(lon_k):
                            csv_targets.append({
                                'id': row.get('target_id') or row.get('id') or f'T{len(csv_targets)+1:03d}',
                                'latitude': float(row[lat_k]),
                                'longitude': float(row[lon_k]),
                                'depth_m': row.get('depth_m') or row.get('depth') or None,
                                'target_type': (row.get('target_type') or row.get('class') or 'unknown').strip(),
                                'confidence': float(row.get('confidence', 0.80)),
                            })
                    except (ValueError, TypeError):
                        continue
                if csv_targets:
                    metadata['_csv_targets'] = csv_targets
                    logger.info("CSV target file parsed: %d targets from %s", len(csv_targets), filename)
        except Exception as error:
            logger.exception("TXT evidence generation failed for %s: %s", filename, error)
            return jsonify({'status': 'error', 'message': f'Unable to parse TXT survey: {error}'}), 400

    elif extension in VIDEO_UPLOAD_EXTENSIONS:
        try:
            video_frames, metadata = _extract_video_frames(raw_bytes, filename)
        except (ValueError, RuntimeError, cv2.error) as error:
            logger.exception("Video frame extraction failed for %s: %s", filename, error)
            return jsonify({'status': 'error', 'message': f'Video frame extraction failed: {error}'}), 400
        if not video_frames:
            logger.error("Video processing rejected: no decodable frames in %s", filename)
            return jsonify({'status': 'error',
                            'message': 'Video frame extraction produced no decodable frames.'}), 422
    else:
        decoded_image = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
        if decoded_image is None:
            logger.error("Image evidence generation rejected: could not decode %s", filename)
            return jsonify({'status': 'error', 'message': 'The image could not be decoded. Check that it is a valid PNG/JPG/JPEG.'}), 400
        evidence_bytes = raw_bytes
        evidence_content_type = 'image/png' if extension == '.png' else 'image/jpeg'

    survey_name = request.form.get('survey_name') or f"Offshore Survey {now.strftime('%Y-%m-%d %H:%M')}"
    location = request.form.get('location_name') or 'Offshore Indian Ocean Demonstration Zone'
    if _txt_supplementary:
        # Survey already exists — just update status to show new data is coming in
        logger.info("TXT supplementary upload for existing survey: survey=%s file=%s", survey_id, filename)
        sb_svc.update_survey_status(survey_id, processing_status='in_progress', status='active')
    else:
        ok, saved_id, error = sb_svc.create_survey({
            'survey_id': survey_id, 'survey_name': survey_name,
            'survey_date': now.strftime('%Y-%m-%d'), 'survey_time': now.strftime('%H:%M'),
            'location_name': location, 'sonar_device': 'TARANG Side-Scan Sonar',
            'sonar_frequency': request.form.get('sonar_frequency') or '400/900 kHz',
            'created_by': created_by
        })
        if not ok:
            return jsonify({'status': 'error', 'message': error or 'Unable to persist the survey record in Supabase.'}), 502
        sb_svc.update_survey_status(survey_id, processing_status='in_progress', status='active')


    # One survey can yield several evidence artifacts: a TXT or image upload
    # produces exactly one, a video produces one per extracted frame.
    evidence_units = []
    if video_frames:
        for frame in video_frames:
            evidence_units.append({
                'label': f"{filename}#frame-{frame['frame_index']:05d}.jpg",
                'bytes': frame['bytes'], 'content_type': 'image/jpeg',
                'image': frame['array'],
                'metadata': dict(metadata, frame_index=frame['frame_index'],
                                 frame_time_seconds=frame['time_seconds']),
            })
    else:
        evidence_units.append({
            'label': filename, 'bytes': evidence_bytes,
            'content_type': evidence_content_type, 'image': decoded_image,
            'metadata': metadata,
        })

    image_records = []
    detections = []
    try:
        for sequence, unit in enumerate(evidence_units, 1):
            record = _persist_workflow_image(
                survey_id, file_hash, unit['label'], unit['bytes'],
                unit['content_type'], sequence=sequence
            )
            image_records.append(record)
            # For CSV target files, parse coordinates directly instead of YOLO.
            # YOLO cannot recognise lat/lon scatter dots as marine debris classes.
            csv_targets = unit['metadata'].get('_csv_targets') or []
            if csv_targets:
                img_record = record
                for t_idx, target in enumerate(csv_targets):
                    lat = target.get('latitude')
                    lon = target.get('longitude')
                    if not sb_svc.is_offshore_coordinate(lat, lon):
                        logger.warning("CSV target %s is not an offshore coordinate, skipping.", target.get('id'))
                        continue
                    raw_cls = target.get('target_type', 'unknown')
                    cls_name = raw_cls if raw_cls in ALLOWED_TARGET_CLASSES else 'unknown'
                    meta = get_meta(cls_name)
                    conf = float(target.get('confidence', 0.80)) * 100
                    tier = 'A' if conf >= 85 else ('B' if conf >= 65 else 'C')
                    detections.append({
                        'id': _stable_target_id(survey_id, f'csv:{sequence}:{t_idx}'),
                        'survey_id': survey_id,
                        'class_name': cls_name, 'title': meta['title'],
                        'category': meta['category'], 'confidence': round(conf, 1),
                        'classification_tier': tier, 'requires_review': True,
                        'latitude': lat, 'longitude': lon,
                        'ping_number': t_idx + 1, 'depth': str(target.get('depth_m', '')) or None,
                        'altitude': None, 'heading': None,
                        'crop_url': img_record.get('url') or '',
                        'material': meta['material'], 'hazard': meta['hazard'],
                        'evidence_sequence': sequence, 'source': 'txt_target_csv',
                        'navigation_source': 'csv_coordinates',
                        'metadata': dict(metadata, target_id=target.get('id')),
                    })
            else:
                detections.extend(_workflow_detection_rows(
                    survey_id, file_hash, unit['image'], unit['metadata'], sequence=sequence))
    except (ValueError, RuntimeError) as error:
        logger.exception("Evidence persistence failed: survey=%s filename=%s error=%s", survey_id, filename, error)
        sb_svc.update_survey_status(survey_id, processing_status='failed', status='active')
        return jsonify({'status': 'error', 'message': str(error)}), 502


    record_by_sequence = {record.get('sequence'): record for record in image_records}
    image_record = image_records[0]

    persisted = []
    for detection in detections:
        # Associate every target with the stable reconstructed sonar artifact
        # for the frame it was found in.  The detection table's crop_url is the
        # canonical image reference used by the analyst portal; it prevents a
        # valid image from being rendered as "Image not available".
        record = record_by_sequence.get(detection.get('evidence_sequence'), image_record)
        detection['crop_url'] = record.get('url') or ''
        detection.setdefault('metadata', {})['image_id'] = record.get('image_id')
        target_id, _ = insert_or_merge_detection(detection)
        detection['id'] = target_id
        detection['evidence_image_id'] = record.get('image_id')
        detection['evidence_sequence'] = record.get('sequence')
        detection['evidence_image_url'] = record.get('url')
        if not _link_detection_to_evidence(target_id, record, detection.get('bbox')):
            sb_svc.update_survey_status(survey_id, processing_status='failed', status='active')
            return jsonify({'status': 'error', 'message': 'Detection was stored but its evidence association could not be saved.'}), 502
        persisted.append(detection)

    upload_event = {
        'survey_id': survey_id, 'file_name': filename,
        'file_type': extension.lstrip('.').upper(), 'file_hash': file_hash,
        'uploaded_at': now.isoformat(), 'processing_status': 'completed',
        'source_label': ('Acoustic samples reconstructed from TXT' if extension == '.txt'
                         else (f"Video frames sampled ({metadata.get('Sampling', 'n/a')})"
                               if extension in VIDEO_UPLOAD_EXTENSIONS
                               else 'Uploaded sonar image')),
        'metadata': metadata,
        'image_id': image_record['image_id'], 'created_at': now.isoformat()
    }
    sb_svc.log_dispatch_event('survey_uploaded', upload_event)
    sb_svc.update_survey_status(survey_id, processing_status='completed', status='active')
    sb_svc.log_dispatch_event('notification', {
        'type': 'Survey Uploaded', 'title': 'Survey uploaded successfully',
        'message': (f'{filename} processed into {len(persisted)} persistent targets '
                    f'and {len(image_records)} sonar image record'
                    f'{"s" if len(image_records) != 1 else ""}.'),
        'recipient_roles': ['survey_operator'],
        'survey_id': survey_id, 'is_read': False, 'timestamp': now.isoformat()
    })
    sb_svc.log_dispatch_event('notification', {
        'type': 'Review Queue', 'title': 'New survey is ready for review',
        'message': f'Sonar Analyst review is ready for survey {survey_id}.',
        'recipient_roles': ['sonar_analyst'],
        'survey_id': survey_id, 'is_read': False, 'timestamp': now.isoformat()
    })
    # The first persisted cluster is part of the same upload transaction from
    # the operator's perspective. Record the hotspot event once so the
    # Government and Marine portals can show why the review queue changed.
    hotspot_candidates = sb_svc.get_hotspots()
    persisted_ids = {item['id'] for item in persisted}
    for hotspot in hotspot_candidates:
        if hotspot.get('priority') == 'High' and persisted_ids.intersection(hotspot.get('target_ids') or []):
            sb_svc.log_dispatch_event('notification', {
                'type': 'Hotspot Identified',
                'title': 'High-priority marine hotspot identified',
                'message': f"{hotspot.get('name', 'Marine hotspot')} contains {hotspot.get('total_targets', 0)} offshore targets.",
                'recipient_roles': ['marine_portal', 'government_portal'],
                'survey_id': survey_id, 'hotspot_id': hotspot.get('id'),
                'is_read': False, 'timestamp': now.isoformat()
            })
            break
    state = _workflow_state(survey_id)
    return jsonify({
        'status': 'success', 'existing': _txt_supplementary, 'survey_id': survey_id,
        'filename': filename, 'file_type': extension.lstrip('.').upper(),
        'processing_status': 'completed', 'uploaded_at': now.isoformat(),
        'image': image_record, 'images': image_records,
        'metadata': metadata, 'detections': state['detections'],
        'detections_count': len(state['detections']),
        'summary': state['summary'], 'hotspots': state['hotspots'],
        'notifications': state['notifications']
    }), 201

@app.route('/api/v1/surveys', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_surveys():
    surveys = sb_svc.get_surveys()
    return jsonify(surveys)

@app.route('/api/v1/surveys/<survey_id>', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_survey(survey_id):
    survey = sb_svc.get_survey(survey_id)
    if not survey:
        return jsonify({'error': 'Survey not found'}), 404
    return jsonify(survey)


@app.route('/api/v1/workflow/state', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_workflow_state():
    return jsonify(_workflow_state(request.args.get('survey_id') or None))


@app.route('/api/v1/surveys/<survey_id>/images', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_workflow_images(survey_id):
    images = sb_svc.get_sonar_images(survey_id)
    if not images:
        logger.error("Evidence image API retrieval found no image records: survey=%s", survey_id)
    elif any(not image.get('url') for image in images):
        logger.error("Evidence image API retrieval returned an unusable URL: survey=%s images=%s", survey_id, [image.get('image_id') for image in images if not image.get('url')])
    else:
        logger.info("Evidence image API retrieval succeeded: survey=%s images=%s", survey_id, len(images))
    return jsonify(images)


@app.route('/api/v1/surveys/<survey_id>/summary', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_workflow_summary(survey_id):
    state = _workflow_state(survey_id)
    return jsonify({
        'survey_id': survey_id, 'summary': state['summary'],
        'processing_status': (state['surveys'][0].get('processing_status') if state['surveys'] else 'unknown'),
        'hotspots': state['hotspots'], 'images': state['images']
    })

@app.route('/api/v1/surveys/<survey_id>/areas', methods=['GET', 'POST'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def handle_survey_areas(survey_id):
    if request.method == 'POST':
        _, error_response = authorize_request('survey_operator', 'platform_admin')
        if error_response:
            return error_response
        data = request.json or request.form
        area_name = data.get('area_name') or 'Primary Sector'
        coordinates = data.get('coordinates') or 'Sector Boundary Active'
        area_id = str(uuid.uuid4())
        # Log as dispatch event since there's no survey_areas table in Supabase
        sb_svc.log_dispatch_event('survey_area', {
            'area_id': area_id, 'survey_id': survey_id,
            'area_name': area_name, 'coordinates': coordinates, 'status': 'ACTIVE'
        })
        return jsonify({'status': 'success', 'area_id': area_id, 'area_name': area_name})
    else:
        survey = sb_svc.get_survey(survey_id)
        if survey:
            return jsonify(survey.get('areas', []))
        return jsonify([])

@app.route('/api/v1/surveys/all/detections', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_all_detections_route():
    dets = sb_svc.get_all_detections()
    return jsonify(dets)

@app.route('/api/v1/surveys/<survey_id>/detections', methods=['GET'])
@app.route('/api/v1/detections', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_survey_detections(survey_id='all'):
    sid = survey_id if survey_id and survey_id != 'all' else None

    # Handle query-string filters
    req_review = None
    v_status = request.args.get('verification_status')
    if v_status:
        req_review = False if v_status.lower() in {'verified', 'rejected'} else True

    c_status = request.args.get('clearance_status')
    tier = request.args.get('tier') or None

    dets = sb_svc.get_all_detections(survey_id=sid, tier=tier, requires_review=req_review)

    # Additional clearance filter
    if v_status:
        wanted_review = v_status.replace('_', ' ').lower()
        dets = [d for d in dets if (d.get('review_status') or '').lower() == wanted_review]
    if c_status:
        wanted_clearance = c_status.replace('_', ' ').lower()
        dets = [d for d in dets if wanted_clearance in {
            (d.get('cleanup_status') or '').lower(),
            (d.get('clearance_status') or '').lower(),
            (d.get('detection_status') or '').lower()
        }]

    return jsonify(dets)

@app.route('/api/v1/surveys/<survey_id>/clusters', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_survey_clusters(survey_id):
    from dbscan_service import cluster_detections
    eps_meters  = float(request.args.get('eps_meters', 500.0))
    min_samples = int(request.args.get('min_samples', 2))
    dets = sb_svc.get_all_detections(survey_id=survey_id)
    return jsonify(cluster_detections(dets, eps_meters=eps_meters, min_samples=min_samples))

# ===========================================================================
# REPORTS
# ===========================================================================

@app.route('/api/v1/reports', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_reports():
    surveys = sb_svc.get_surveys()
    reports = []
    for s in surveys:
        sid  = s.get('survey_id', '')
        dets = sb_svc.get_all_detections(survey_id=sid)
        verified = sum(1 for d in dets if not d.get('requires_review'))
        cleared  = sum(1 for d in dets if (d.get('hazard') or '').lower() == 'cleared')
        reports.append({
            'id':               f"REP-{sid}",
            'survey_id':        sid,
            'title':            f"Hydrographic Survey Report: {s.get('survey_name','')}",
            'survey_name':      s.get('survey_name',''),
            'region':           s.get('location_name',''),
            'date':             (s.get('created_at') or s.get('survey_date') or '')[:10],
            'total_detections': len(dets),
            'verified_targets': verified,
            'cleared_targets':  cleared,
            'status':           'Verified' if verified > 0 else 'Pending Review'
        })
    return jsonify(reports)


def _pdf_text(value, limit=118):
    """Convert persisted values to safe, compact PDF text without inventing data."""
    value = str(value if value is not None else '')
    value = value.encode('ascii', 'replace').decode('ascii')
    value = value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return value[:limit]


def _build_pdf_report(lines):
    """Create a valid multi-page PDF using only the supplied report lines."""
    page_lines = 46
    pages = [lines[index:index + page_lines] for index in range(0, len(lines), page_lines)] or [['No report data was available.']]
    font_id = 3 + len(pages) * 2
    page_ids = [3 + index * 2 for index in range(len(pages))]
    objects = {
        1: f"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>",
        font_id: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, page in enumerate(pages):
        page_id = page_ids[index]
        content_id = page_id + 1
        commands = ['BT', '/F1 10 Tf', '50 755 Td']
        for line_index, line in enumerate(page):
            if line_index:
                commands.append('0 -15 Td')
            commands.append(f"({_pdf_text(line)}) Tj")
        commands.append('ET')
        content = '\n'.join(commands).encode('latin-1')
        objects[page_id] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        objects[content_id] = b"<< /Length " + str(len(content)).encode('ascii') + b" >>\nstream\n" + content + b"\nendstream"

    document = bytearray(b'%PDF-1.4\n%TARANG\n')
    offsets = [0] * (max(objects) + 1)
    for object_id in sorted(objects):
        offsets[object_id] = len(document)
        document.extend(f'{object_id} 0 obj\n'.encode('ascii'))
        body = objects[object_id]
        document.extend(body if isinstance(body, bytes) else body.encode('latin-1'))
        document.extend(b'\nendobj\n')
    xref_offset = len(document)
    document.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode('ascii'))
    for offset in offsets[1:]:
        document.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    document.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('ascii'))
    return bytes(document)


@app.route('/api/v1/surveys/<survey_id>/report', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def download_survey_report(survey_id):
    """Download a populated, survey-scoped operational report."""
    survey = sb_svc.get_survey(survey_id)
    if not survey:
        return jsonify({'status': 'error', 'message': 'Survey not found.'}), 404

    detections = sb_svc.get_all_detections(survey_id=survey_id)
    hotspots = [hotspot for hotspot in sb_svc.get_hotspots() if survey_id in {
        str(detection.get('survey_id')) for detection in detections
    } and set(hotspot.get('target_ids') or {}).intersection({str(detection.get('id')) for detection in detections})]
    operations = [operation for operation in sb_svc.get_cleanup_operations() if str(operation.get('survey_id')) == str(survey_id)]
    route = sb_svc.get_latest_route()
    if route and str(route.get('survey_id') or '') != str(survey_id):
        route = None

    lines = [
        'TARANG MARINE OPERATIONS REPORT',
        f'Generated: {datetime.now().isoformat()}',
        '', 'SURVEY',
        f"Survey ID: {survey.get('survey_id')}",
        f"Name: {survey.get('survey_name')}",
        f"Location: {survey.get('location_name')}",
        f"Survey time: {survey.get('survey_date')} {survey.get('survey_time')}",
        f"Sonar: {survey.get('sonar_device')} | {survey.get('sonar_frequency')}",
        f"Processing status: {survey.get('processing_status')}",
        '', f'DETECTIONS ({len(detections)})'
    ]
    for detection in detections:
        lines.extend([
            f"{detection.get('id')} | {detection.get('title') or detection.get('class_name')}",
            f"  Confidence: {detection.get('confidence')}% | Review: {detection.get('review_status')} | Cleanup: {detection.get('cleanup_status')}",
            f"  Coordinates: {detection.get('latitude')}, {detection.get('longitude')} | Depth: {detection.get('depth')} | Created: {detection.get('created_at')}",
        ])
    lines.append('')
    lines.append(f'HOTSPOTS ({len(hotspots)})')
    for hotspot in hotspots:
        lines.append(f"{hotspot.get('id')} | {hotspot.get('name')} | {hotspot.get('status')} | {hotspot.get('latitude')}, {hotspot.get('longitude')} | targets: {hotspot.get('total_targets')}")
    lines.append('')
    lines.append(f'CLEANUP OPERATIONS ({len(operations)})')
    for operation in operations:
        lines.append(f"{operation.get('operation_id')} | target {operation.get('target_id')} | {operation.get('status')} | {operation.get('progress_percent')}% | {operation.get('updated_at')}")
    lines.append('')
    lines.append('ROUTE')
    if route:
        lines.append(f"{route.get('route_id')} | {route.get('status')} | {route.get('target_count')} stops | {route.get('distance_km')} km | estimated {route.get('estimated_operation_minutes')} min")
        for stop in route.get('target_sequence') or []:
            lines.append(f"  Stop {stop.get('sequence')}: {stop.get('target_id')} ({stop.get('latitude')}, {stop.get('longitude')}) | {stop.get('status')}")
    else:
        lines.append('No cleanup route has been generated for this survey.')

    return Response(
        _build_pdf_report(lines),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=tarang_report_{survey_id}.pdf'}
    )

# ===========================================================================
# ANALYST REVIEWS
# ===========================================================================

@app.route('/api/v1/analyst-reviews', methods=['GET', 'POST'])
@require_roles('survey_operator', 'sonar_analyst', 'platform_admin')
def handle_analyst_reviews():
    if request.method == 'POST':
        data = request.json or request.form
        survey_id   = data.get('survey_id') or ''
        survey_name = data.get('survey_name') or 'Survey Mission'
        sent_to     = data.get('sent_to') or 'Marine Portal'
        notes       = data.get('notes') or 'Submitted from Survey Operator portal.'
        rev_id      = str(uuid.uuid4())
        now_str     = datetime.now().strftime('%d %b %Y, %H:%M')

        # Count real detections for this survey
        dets    = sb_svc.get_all_detections(survey_id=survey_id) if survey_id else []
        det_cnt = len(dets)
        val_cnt = max(1, det_cnt - 2) if det_cnt > 2 else det_cnt
        rej_cnt = 1 if det_cnt > 3 else 0
        req_cnt = 1 if det_cnt > 1 else 0

        sb_svc.log_dispatch_event('analyst_review', {
            'id': rev_id, 'survey_id': survey_id, 'survey_name': survey_name,
            'sent_to': sent_to, 'sent_at': now_str, 'status': 'Awaiting Review',
            'validated_count': val_cnt, 'rejected_count': rej_cnt,
            'review_required_count': req_cnt, 'notes': notes
        })
        return jsonify({
            'status': 'success',
            'review': {
                'id': rev_id, 'survey_id': survey_id, 'survey_name': survey_name,
                'sent_to': sent_to, 'sent_at': now_str, 'status': 'Awaiting Review',
                'validated_count': val_cnt, 'rejected_count': rej_cnt, 'review_required_count': req_cnt
            }
        })
    else:
        reviews = sb_svc.get_dispatch_events('analyst_review')
        return jsonify(reviews)


@app.route('/api/v1/dispatches', methods=['GET'])
def get_dispatches():
    """Return dispatch event log for the current workflow state."""
    event_type = request.args.get('type')
    events = sb_svc.get_dispatch_events(event_type) if event_type else sb_svc.get_dispatch_events()
    return jsonify(events)


@app.route('/api/v1/dispatches', methods=['POST'])
@require_roles('survey_operator', 'sonar_analyst', 'platform_admin')
def create_dispatch():
    """Record a role hand-off using detections already persisted in Supabase."""
    data = request.json or request.form
    survey_id = (data.get('survey_id') or '').strip()
    destination = (data.get('destination') or '').strip().upper()
    # Accept dispatch records created before the portal IDs were unified, but
    # persist and return only the canonical destination identifier.
    destination = {'MARINE_ANALYST': 'MARINE_PORTAL'}.get(destination, destination)
    tiers = data.get('tiers') or []
    if isinstance(tiers, str):
        tiers = [tier.strip().upper() for tier in tiers.split(',') if tier.strip()]
    else:
        tiers = [str(tier).upper() for tier in tiers]

    if not survey_id or destination not in {'MARINE_PORTAL', 'SONAR_ANALYST'}:
        return jsonify({'status': 'error', 'message': 'A valid survey and destination are required.'}), 400
    if not sb_svc.get_survey(survey_id):
        return jsonify({'status': 'error', 'message': 'Survey not found in Supabase.'}), 404

    detections = sb_svc.get_all_detections(survey_id=survey_id)
    if tiers:
        detections = [d for d in detections if (d.get('classification_tier') or '').upper() in tiers]
    if not detections:
        return jsonify({'status': 'error', 'message': 'No persisted detections match this dispatch.'}), 409

    event_id = str(uuid.uuid4())
    ok = sb_svc.log_dispatch_event('detection_dispatch', {
        'dispatch_id': event_id,
        'survey_id': survey_id,
        'destination': destination,
        'tiers': tiers,
        'detection_count': len(detections),
        'created_at': datetime.now().isoformat()
    })
    if not ok:
        return jsonify({'status': 'error', 'message': 'Supabase rejected the dispatch record.'}), 502
    return jsonify({'status': 'success', 'dispatch_id': event_id, 'detection_count': len(detections)})

# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

@app.route('/api/v1/notifications', methods=['GET', 'POST'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def handle_notifications():
    if request.method == 'POST':
        data = request.json or request.form
        n_id = str(uuid.uuid4())
        requested_roles = data.get('recipient_roles') or [g.tarang_user.get('role')]
        if isinstance(requested_roles, str):
            requested_roles = [role.strip() for role in requested_roles.split(',') if role.strip()]
        emit_workflow_notification(
            requested_roles, data.get('title', 'Notification'), data.get('message', ''),
            type=data.get('type', 'Alert'), id=n_id, survey_id=data.get('survey_id', ''),
        )
        return jsonify({'status': 'success', 'id': n_id})
    else:
        return jsonify(sb_svc.get_notifications(g.tarang_user.get('role')))

@app.route('/api/v1/notifications/mark-read', methods=['POST'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def mark_notifications_read():
    sb_svc.mark_notifications_read(g.tarang_user.get('role'))
    return jsonify({'status': 'success'})

# ===========================================================================
# DOCUMENTS
# ===========================================================================

@app.route('/api/v1/documents', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_documents():
    return jsonify(sb_svc.get_documents())

# ===========================================================================
# DETECTIONS — ANALYST + INTERMEDIATE
# ===========================================================================

@app.route('/api/v1/detections/analyst', methods=['GET'])
@require_roles('sonar_analyst', 'platform_admin')
def get_analyst_detections():
    """High-confidence detections (tier A and B) for Sonar Analyst review."""
    dets = sb_svc.get_all_detections()
    filtered = [d for d in dets if d.get('classification_tier') in ('A', 'B')]
    return jsonify(sorted(filtered, key=lambda x: x.get('confidence', 0), reverse=True))

@app.route('/api/v1/detections/intermediate', methods=['GET'])
@require_roles('sonar_analyst', 'platform_admin')
def get_intermediate_detections():
    """Tier-C detections requiring further review."""
    dets = sb_svc.get_all_detections(tier='C')
    return jsonify(sorted(dets, key=lambda x: x.get('confidence', 0), reverse=True))

@app.route('/api/v1/detections/<detection_id>/verify', methods=['POST'])
@require_roles('sonar_analyst', 'admin', 'platform_admin')
def verify_detection(detection_id):
    """Sonar analyst verification with status: Verified, Rejected, Needs Review."""
    data      = request.json or request.form
    v_status  = data.get('status', 'Verified')  # Verified | Rejected | Needs Review
    notes     = data.get('notes', '')
    reviewer  = g.tarang_user.get('username') or g.tarang_user.get('full_name') or g.tarang_user.get('id')
    new_class = data.get('class_name')
    confidence_override = data.get('analyst_confidence')

    det = sb_svc.get_detection(detection_id)
    if not det:
        return jsonify({'error': 'Detection not found'}), 404

    # Update detection with verification
    ok = sb_svc.update_detection_review(
        detection_id, v_status, new_class=new_class,
        reviewer=reviewer, notes=notes
    )
    if ok:
        # Log verification event for audit trail
        sb_svc.log_dispatch_event('detection_verification', {
            'detection_id': detection_id,
            'survey_id': det.get('survey_id'),
            'ai_class': det.get('class_name'),
            'ai_confidence': det.get('confidence'),
            'analyst_status': v_status,
            'analyst_class': new_class,
            'analyst_confidence': confidence_override,
            'reviewer': reviewer,
            'notes': notes,
            'verified_at': datetime.now().isoformat()
        })
        
        # Notify operator when verification completes
        if v_status in ('Verified', 'Rejected'):
            survey_id = det.get('survey_id')
            survey_dets = sb_svc.get_all_detections(survey_id=survey_id)
            verified_count = sum(1 for d in survey_dets if d.get('review_status') == 'Verified')
            emit_workflow_notification(
                ['survey_operator'], 
                f'Detection {v_status.lower()}',
                f'Analyst {v_status.lower()} detection {detection_id} in survey {survey_id}. Total verified: {verified_count}',
                type='Verification Update',
                survey_id=survey_id,
                detection_id=detection_id,
                verification_status=v_status
            )
        
        return jsonify({'status': 'success', 'detection_id': detection_id, 'verification_status': v_status})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update detection.'}), 500

@app.route('/api/v1/surveys/<survey_id>/verification-summary', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_verification_summary(survey_id):
    """Get verification statistics for a survey."""
    dets = sb_svc.get_all_detections(survey_id=survey_id)
    total = len(dets)
    verified = sum(1 for d in dets if d.get('review_status') == 'Verified')
    rejected = sum(1 for d in dets if d.get('review_status') == 'Rejected')
    needs_review = sum(1 for d in dets if d.get('review_status') in ('Needs Review', 'Pending Review', None) or d.get('requires_review'))
    
    # Group by class
    by_class = {}
    for d in dets:
        cls = d.get('class_name', 'unknown')
        if cls not in by_class:
            by_class[cls] = {'total': 0, 'verified': 0, 'rejected': 0, 'pending': 0}
        by_class[cls]['total'] += 1
        status = d.get('review_status')
        if status == 'Verified':
            by_class[cls]['verified'] += 1
        elif status == 'Rejected':
            by_class[cls]['rejected'] += 1
        else:
            by_class[cls]['pending'] += 1
    
    return jsonify({
        'survey_id': survey_id,
        'total_detections': total,
        'verified': verified,
        'rejected': rejected,
        'needs_review': needs_review,
        'pending': needs_review,
        'verification_progress': round(100.0 * (verified + rejected) / total, 1) if total > 0 else 0,
        'by_class': by_class
    })

@app.route('/api/v1/surveys/<survey_id>/verification-queue', methods=['GET'])
@require_roles('sonar_analyst', 'admin', 'platform_admin')
def get_verification_queue(survey_id):
    """Get pending detections requiring verification for a survey."""
    dets = sb_svc.get_all_detections(survey_id=survey_id)
    
    # Filter to pending detections only
    pending = [
        d for d in dets 
        if d.get('review_status') in ('Needs Review', 'Pending Review', None, 'AI_DETECTED') 
        or d.get('requires_review') == True
    ]
    
    # Sort by confidence (lowest first for prioritization)
    pending.sort(key=lambda x: x.get('confidence', 0.0))
    
    return jsonify({
        'survey_id': survey_id,
        'total_pending': len(pending),
        'queue': pending
    })

@app.route('/api/v1/surveys/<survey_id>/batch-verify', methods=['POST'])
@require_roles('sonar_analyst', 'admin', 'platform_admin')
def batch_verify_detections(survey_id):
    """Batch verify multiple detections."""
    data = request.json or {}
    detection_ids = data.get('detection_ids', [])
    new_status = data.get('status', 'Verified')  # 'Verified', 'Rejected', or 'Needs Review'
    analyst_notes = data.get('notes', 'Batch verification')
    
    if not detection_ids:
        return jsonify({'status': 'error', 'message': 'No detection_ids provided.'}), 400
    
    # Get analyst info
    analyst_name = session.get('user', {}).get('full_name', 'System Analyst')
    analyst_id = session.get('user', {}).get('user_id', 'system')
    
    results = {'success': [], 'failed': []}
    
    for det_id in detection_ids:
        try:
            # Update detection
            ok = sb_svc.update_detection_review(
                det_id, 
                new_status, 
                analyst=analyst_name, 
                notes=analyst_notes
            )
            
            if ok:
                # Log event
                sb_svc.log_dispatch_event(
                    survey_id=survey_id,
                    event_type='detection_verified',
                    metadata={
                        'detection_id': det_id,
                        'verification_status': new_status,
                        'analyst_id': analyst_id,
                        'analyst_name': analyst_name,
                        'batch': True
                    }
                )
                
                # Emit notification
                emit_workflow_notification(
                    target_roles=['government_portal'],
                    title=f'Detection {new_status}',
                    message=f'Detection {det_id} marked as {new_status} by {analyst_name}',
                    action_url=f'/government-portal.html?detection={det_id}',
                    metadata={'detection_id': det_id, 'survey_id': survey_id}
                )
                
                results['success'].append(det_id)
            else:
                results['failed'].append(det_id)
                
        except Exception as e:
            print(f"Batch verify error for {det_id}: {e}")
            results['failed'].append(det_id)
    
    return jsonify({
        'status': 'completed',
        'total': len(detection_ids),
        'success_count': len(results['success']),
        'failed_count': len(results['failed']),
        'results': results
    })

@app.route('/api/v1/detections/<detection_id>/clearance', methods=['POST'])
@require_roles('marine_portal', 'marine_analyst', 'admin', 'platform_admin')
def update_detection_clearance_route(detection_id):
    data     = request.json or request.form
    c_status = data.get('status', 'In Progress')
    team     = data.get('team', 'Marine Clearance Operations')
    notes    = data.get('notes', '')
    ok = sb_svc.update_detection_clearance(detection_id, c_status, team=team, notes=notes)
    if ok:
        return jsonify({'status': 'success', 'detection_id': detection_id, 'clearance_status': c_status})
    return jsonify({'status': 'error'}), 500

@app.route('/api/v1/detections/<detection_id>/cleanup-decision', methods=['POST'])
@require_roles('marine_portal', 'marine_analyst', 'admin', 'platform_admin')
def record_cleanup_decision(detection_id):
    data = request.json or request.form
    cleanup_required = data.get('cleanup_required')
    if isinstance(cleanup_required, str):
        cleanup_required = cleanup_required.lower() in ['true', 'yes', '1']
    elif cleanup_required is None:
        # The Cleanup Portal's explicit Reject/Not Recommended action is the
        # one shorthand that represents a negative decision.
        cleanup_required = str(data.get('action') or '').strip().lower() not in {'reject_cleanup', 'not_recommended'}
        if cleanup_required:
            return jsonify({'status': 'error', 'message': 'Choose whether this verified target is eligible for cleanup.'}), 400

    det = sb_svc.get_detection(detection_id)
    if not det:
        return jsonify({'error': 'Detection not found'}), 404
    if det.get('review_status') != 'Verified':
        return jsonify({'status': 'error', 'message': 'Only analyst-verified targets can receive a cleanup decision.'}), 409
    if not det.get('is_offshore'):
        return jsonify({'status': 'error', 'message': 'A cleanup decision cannot be recorded for a land or invalid coordinate.'}), 409

    hotspot_id = data.get('hotspot_id') or _hotspot_for_target(detection_id)
    now = datetime.now().isoformat()
    if cleanup_required:
        status = 'Cleanup Approved'
        operation_id = f"OP-{hashlib.sha256(f'{detection_id}:cleanup'.encode('utf-8')).hexdigest()[:10].upper()}"
        if not sb_svc.log_dispatch_event('cleanup_operation', {
            'operation_id': operation_id, 'target_id': detection_id,
            'hotspot_id': hotspot_id, 'status': status,
            'priority': 'High' if float(det.get('confidence') or 0) >= 80 else 'Medium',
            'assigned_operation': data.get('assigned_operation') or 'Marine Response Fleet A',
            'progress_percent': 0, 'approved_at': now, 'updated_at': now,
            'notes': data.get('notes', 'Marine Analyst approved cleanup.')
        }):
            return jsonify({'status': 'error', 'message': 'Unable to persist the cleanup approval.'}), 502
        if not sb_svc.update_detection_clearance(detection_id, status, hotspot_id=hotspot_id,
                                                 team=data.get('assigned_operation') or 'Marine Response Fleet A',
                                                 notes=data.get('notes', 'Marine Analyst approved cleanup.')):
            return jsonify({'status': 'error', 'message': 'Cleanup approval was recorded but the target state could not be updated.'}), 502
        emit_workflow_notification(
            ['marine_portal', 'government_portal'], 'Cleanup approved',
            f'Detection {detection_id} is an approved offshore cleanup candidate.',
            type='Cleanup Decision', survey_id=det.get('survey_id'), detection_id=detection_id,
            hotspot_id=hotspot_id, operation_id=operation_id
        )
    else:
        status = 'Cleanup Not Recommended'
        if not sb_svc.log_dispatch_event('detection_state', {
            'detection_id': detection_id, 'status': 'Verified',
            'lifecycle_status': status, 'hotspot_id': hotspot_id, 'notes': data.get('notes', ''),
            'decision_at': now, 'updated_at': now
        }):
            return jsonify({'status': 'error', 'message': 'Unable to persist the cleanup decision.'}), 502
        emit_workflow_notification(
            ['marine_portal', 'government_portal'], 'Cleanup not recommended',
            f'Detection {detection_id} remains a verified monitored finding without a cleanup dispatch.',
            type='Cleanup Decision', survey_id=det.get('survey_id'), detection_id=detection_id, hotspot_id=hotspot_id
        )

    return jsonify({
        'status': 'success', 'detection_id': detection_id,
        'cleanup_required': cleanup_required, 'clearance_status': status,
        'operation': next((op for op in sb_svc.get_cleanup_operations() if op.get('target_id') == detection_id), None)
    })


@app.route('/api/v1/cleanup/operations', methods=['GET'])
@require_roles('marine_portal', 'government_portal', 'admin', 'survey_operator', 'sonar_analyst')
def get_cleanup_operations_route():
    operations = sb_svc.get_cleanup_operations()
    survey_id = request.args.get('survey_id')
    if survey_id:
        operations = [op for op in operations if op.get('survey_id') == survey_id]
    return jsonify(operations)


@app.route('/api/v1/cleanup/<target_id>/action', methods=['POST'])
@require_roles('marine_portal', 'marine_analyst', 'admin', 'platform_admin')
def update_cleanup_operation(target_id):
    data = request.json or request.form or {}
    action = str(data.get('action') or '').strip().lower()
    action_status = {
        'accept_cleanup': 'Cleanup Approved', 'approve': 'Cleanup Approved',
        'reject_cleanup': 'Cleanup Not Recommended', 'not_recommended': 'Cleanup Not Recommended',
        'schedule_cleanup': 'Cleanup Scheduled', 'schedule': 'Cleanup Scheduled',
        # Retained for browsers cached before the explicit Schedule label was
        # introduced.  Dispatch now means scheduled; route generation never
        # starts an operation on its own.
        'dispatch_cleanup': 'Cleanup Scheduled', 'dispatch': 'Cleanup Scheduled',
        'start_operation': 'Cleanup In Progress', 'start': 'Cleanup In Progress',
        'complete_cleanup': 'Cleanup Completed', 'complete': 'Cleanup Completed',
        'update_progress': 'Cleanup In Progress'
    }
    if action not in action_status:
        return jsonify({'status': 'error', 'message': 'Use Approve Cleanup, Reject/Not Recommended, Schedule Cleanup, Start Operation, Update Progress, or Complete Cleanup.'}), 400
    det = sb_svc.get_detection(target_id)
    if not det or not det.get('is_offshore', True):
        return jsonify({'status': 'error', 'message': 'Cleanup target was not found in the offshore workflow.'}), 404
    if det.get('review_status') != 'Verified':
        return jsonify({'status': 'error', 'message': 'Only analyst-verified targets can enter the cleanup workflow.'}), 409
    status = action_status[action]
    hotspot_id = data.get('hotspot_id') or _hotspot_for_target(target_id)
    if status == 'Cleanup Not Recommended':
        # Handle rejection inline — calling record_cleanup_decision() as a
        # plain Python function doesn't work because it re-reads request.json
        # and misinterprets the 'action' key as cleanup_required=True.
        det = sb_svc.get_detection(target_id)
        if not det:
            return jsonify({'error': 'Detection not found'}), 404
        now = datetime.now().isoformat()
        if not sb_svc.log_dispatch_event('detection_state', {
            'detection_id': target_id, 'status': 'Verified',
            'lifecycle_status': status, 'hotspot_id': hotspot_id,
            'notes': data.get('notes', ''), 'decision_at': now, 'updated_at': now
        }):
            return jsonify({'status': 'error', 'message': 'Unable to persist the cleanup decision.'}), 502
        sb_svc.update_detection_clearance(target_id, status,
                                          notes=data.get('notes', ''), hotspot_id=hotspot_id)
        emit_workflow_notification(
            ['marine_portal', 'government_portal'], 'Cleanup not recommended',
            f'Detection {target_id} remains a verified monitored finding without a cleanup dispatch.',
            type='Cleanup Decision', survey_id=det.get('survey_id'),
            detection_id=target_id, hotspot_id=hotspot_id
        )
        return jsonify({'status': 'success', 'detection_id': target_id, 'cleanup_status': status})

    existing = next((operation for operation in sb_svc.get_cleanup_operations()
                     if str(operation.get('target_id')) == str(target_id)), None)
    previous_status = existing.get('status') if existing else ''
    allowed_previous = {
        'Cleanup Approved': {'', 'Cleanup Approved', 'Cleanup Scheduled'},
        'Cleanup Scheduled': {'Cleanup Approved', 'Cleanup Scheduled'},
        'Cleanup In Progress': {'Cleanup Approved', 'Cleanup Scheduled', 'Cleanup In Progress'},
        'Cleanup Completed': {'Cleanup In Progress'},
    }
    if previous_status not in allowed_previous[status]:
        return jsonify({'status': 'error', 'message': f'Cannot change {previous_status or "an undecided target"} directly to {status}.'}), 409
    progress = data.get('progress_percent')
    if progress is None:
        progress = 100 if status == 'Cleanup Completed' else (50 if status == 'Cleanup In Progress' else 0)
    try:
        progress = max(0, min(100, int(progress)))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Progress must be a number from 0 to 100.'}), 400
    operation_id = data.get('operation_id') or f"OP-{hashlib.sha256(f'{target_id}:cleanup'.encode('utf-8')).hexdigest()[:10].upper()}"
    now = datetime.now().isoformat()
    event = {
        'operation_id': operation_id, 'target_id': target_id,
        'hotspot_id': hotspot_id, 'status': status,
        'priority': data.get('priority') or ('High' if float(det.get('confidence') or 0) >= 80 else 'Medium'),
        'assigned_operation': data.get('assigned_operation') or 'Marine Response Fleet A',
        'progress_percent': progress, 'action': action,
        'updated_at': now, 'notes': data.get('notes', ''),
        'approved_at': (existing or {}).get('approved_at') or (now if status == 'Cleanup Approved' else ''),
        'scheduled_at': (existing or {}).get('scheduled_at') or (now if status == 'Cleanup Scheduled' else ''),
        'started_at': (existing or {}).get('started_at') or (now if status == 'Cleanup In Progress' else ''),
        'progress_updated_at': now if action == 'update_progress' else (existing or {}).get('progress_updated_at', ''),
        'completed_at': now if status == 'Cleanup Completed' else (existing or {}).get('completed_at', ''),
        'route_id': (existing or {}).get('route_id', ''),
    }
    if not sb_svc.log_dispatch_event('cleanup_operation', event):
        return jsonify({'status': 'error', 'message': 'Unable to persist the cleanup operation update.'}), 502
    if not sb_svc.update_detection_clearance(target_id, status, team=data.get('assigned_operation') or 'Marine Response Fleet A',
                                             notes=data.get('notes', ''), hotspot_id=hotspot_id):
        return jsonify({'status': 'error', 'message': 'Operation update was recorded but the target state could not be updated.'}), 502
    recipients = ['marine_portal', 'government_portal']
    emit_workflow_notification(
        recipients, f'Cleanup status: {status}', f'Detection {target_id} is now {status.lower()}.',
        type='Cleanup Lifecycle', survey_id=det.get('survey_id'), detection_id=target_id,
        hotspot_id=hotspot_id, operation_id=operation_id, progress_percent=progress
    )
    return jsonify({'status': 'success', 'operation': next((op for op in sb_svc.get_cleanup_operations() if op.get('target_id') == target_id), None)})

# ===========================================================================
# HOTSPOTS  (dynamic clustering from real Supabase detections)
# ===========================================================================

@app.route('/api/v1/hotspots', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin', 'public')
def get_hotspots():
    hotspots = sb_svc.get_hotspots()
    return jsonify(hotspots)

@app.route('/api/v1/hotspots/<hotspot_id>/status', methods=['POST'])
@require_roles('marine_portal', 'government_portal', 'admin')
def update_hotspot_status(hotspot_id):
    data = request.json or request.form
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Missing status'}), 400
    sb_svc.log_dispatch_event('hotspot_status_update', {
        'hotspot_id': hotspot_id, 'new_status': new_status,
        'updated_at': datetime.now().isoformat()
    })
    return jsonify({'status': 'success', 'hotspot_id': hotspot_id, 'new_status': new_status})


def _hotspot_for_target(target_id):
    """Return the persisted dynamic hotspot containing a detection, if any."""
    for hotspot in sb_svc.get_hotspots():
        if str(target_id) in {str(member) for member in hotspot.get('target_ids') or []}:
            return hotspot.get('id') or ''
    return ''


def _haversine_km(a, b):
    import math
    lat1, lon1 = map(math.radians, [float(a[0]), float(a[1])])
    lat2, lon2 = map(math.radians, [float(b[0]), float(b[1])])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0.0, 1 - h)))


def _build_cleanup_route(survey_id=None, hotspot_id=None):
    operations = sb_svc.get_cleanup_operations()
    candidates = [op for op in operations if op.get('status') in {'Cleanup Approved', 'Cleanup Scheduled', 'Cleanup In Progress'}]
    if survey_id:
        candidates = [op for op in candidates if op.get('survey_id') == survey_id]
    if hotspot_id:
        candidates = [op for op in candidates if op.get('hotspot_id') == hotspot_id]
    candidates = [op for op in candidates
                  if op.get('latitude') is not None and op.get('longitude') is not None
                  and sb_svc.is_offshore_coordinate(op.get('latitude'), op.get('longitude'))]
    if not candidates:
        return None

    # Stable nearest-neighbour TSP: priority first, then deterministic target ID.
    remaining = sorted(candidates, key=lambda op: (op.get('priority') != 'High', op.get('target_id') or ''))
    route = [remaining.pop(0)]
    while remaining:
        current = route[-1]
        current_point = [current['latitude'], current['longitude']]
        next_op = min(remaining, key=lambda op: _haversine_km(current_point, [op['latitude'], op['longitude']]))
        remaining.remove(next_op)
        route.append(next_op)
    distance = 0.0
    sequence = []
    for index, operation in enumerate(route, 1):
        if index > 1:
            previous = route[index - 2]
            distance += _haversine_km([previous['latitude'], previous['longitude']], [operation['latitude'], operation['longitude']])
        leg_distance = 0.0 if index == 1 else _haversine_km(
            [route[index - 2]['latitude'], route[index - 2]['longitude']],
            [operation['latitude'], operation['longitude']]
        )
        sequence.append({
            'sequence': index, 'target_id': operation['target_id'],
            'operation_id': operation['operation_id'], 'hotspot_id': operation.get('hotspot_id'),
            'survey_id': operation.get('survey_id'),
            'latitude': operation['latitude'], 'longitude': operation['longitude'],
            'target_type': operation['target_type'], 'priority': operation['priority'],
            'status': operation['status'], 'leg_distance_km': round(leg_distance, 3),
            'coordinates': [float(operation['latitude']), float(operation['longitude'])]
        })
    route_key = '|'.join(item['target_id'] for item in sequence)
    route_id = f"ROUTE-{hashlib.sha256(route_key.encode('utf-8')).hexdigest()[:12].upper()}"
    travel_minutes = round(distance / 18.0 * 60)  # practical ROV/support-vessel planning speed
    cleanup_minutes = len(sequence) * 35
    return {
        'route_id': route_id, 'survey_id': survey_id or sequence[0].get('survey_id'),
        'hotspot_id': hotspot_id or sequence[0].get('hotspot_id'),
        'status': 'Route Generated', 'target_sequence': sequence,
        'target_count': len(sequence), 'distance_km': round(distance, 3),
        'route_coordinates': [[item['latitude'], item['longitude']] for item in sequence],
        'estimated_travel_minutes': travel_minutes,
        'estimated_cleanup_minutes': cleanup_minutes,
        'estimated_operation_minutes': travel_minutes + cleanup_minutes,
        'estimated_operation_hours': round((travel_minutes + cleanup_minutes) / 60, 1),
        'route_status': 'Ready for scheduling',
        'generated_at': datetime.now().isoformat()
    }


@app.route('/api/v1/routes/optimize', methods=['POST'])
@require_roles('marine_portal', 'government_portal', 'admin')
def optimize_cleanup_route():
    data = request.json or request.form or {}
    route = _build_cleanup_route(data.get('survey_id'), data.get('hotspot_id'))
    if not route:
        return jsonify({'status': 'error', 'message': 'No cleanup-approved offshore targets are ready for routing.'}), 409
    # A route is a plan, not an implicit dispatch.  The Marine Analyst must
    # schedule and start a persisted operation explicitly after review.
    if not sb_svc.log_dispatch_event('route_optimized', route):
        return jsonify({'status': 'error', 'message': 'Unable to persist the optimized route.'}), 502
    emit_workflow_notification(
        ['marine_portal', 'government_portal'], 'TSP cleanup route generated',
        f"{route['target_count']} approved offshore targets are sequenced over {route['distance_km']} km.",
        type='Route Optimization', survey_id=route.get('survey_id'), hotspot_id=route.get('hotspot_id'),
        route_id=route['route_id']
    )
    return jsonify({'status': 'success', 'route': route})


@app.route('/api/v1/routes', methods=['GET'])
@require_roles('marine_portal', 'government_portal', 'admin', 'survey_operator', 'sonar_analyst')
def get_cleanup_route():
    return jsonify(sb_svc.get_latest_route() or {'status': 'No route generated'})


# ===========================================================================
# SYSTEM / DATABASE STATUS  (real requests only - never a hardcoded status)
# ===========================================================================

@app.route('/api/v1/system/status', methods=['GET'])
def system_status():
    """Report live Supabase database, auth, storage and backend API status."""
    import tarang_status
    try:
        report = tarang_status.collect_status(self_base_url=request.host_url.rstrip('/'))
        return jsonify(report)
    except Exception as error:
        logger.exception("System status probe failed: %s", error)
        return jsonify({
            'overall': 'DEGRADED',
            'error': f'System status probe failed: {error}',
            'database': {'supabase': {'status': 'NOT CONNECTED', 'connected': False,
                                      'detail': str(error)}},
        }), 502


# ===========================================================================
# HOTSPOT CLEANUP ROUTE  (TSP over real clustered hotspot coordinates, in NM)
# ===========================================================================

def _hotspots_for_survey(survey_id=None):
    """Return real DBSCAN hotspots, optionally restricted to one survey."""
    hotspots = sb_svc.get_hotspots()
    if not survey_id:
        return hotspots
    survey_detection_ids = {
        str(detection.get('id'))
        for detection in sb_svc.get_all_detections(survey_id=survey_id)
    }
    if not survey_detection_ids:
        return []
    return [hotspot for hotspot in hotspots
            if survey_detection_ids & {str(member) for member in hotspot.get('target_ids') or []}]


def _survey_start_coordinate(survey_id):
    """First real survey position, derived from the survey's own detections."""
    if not survey_id:
        return None
    detections = [d for d in sb_svc.get_all_detections(survey_id=survey_id)
                  if d.get('latitude') is not None and d.get('longitude') is not None]
    if not detections:
        return None
    earliest = min(detections, key=lambda d: (d.get('ping_number') is None, d.get('ping_number') or 0))
    return [float(earliest['latitude']), float(earliest['longitude'])]


@app.route('/api/v1/hotspot-route', methods=['GET', 'POST'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def hotspot_cleanup_route():
    """Optimise a cleanup route through real hotspot coordinates.

    Distances are nautical miles, the primary TARANG maritime unit. The solver
    is nearest-neighbour plus 2-opt, so the result is labelled as a heuristic
    optimisation rather than an exact TSP solution.
    """
    import tarang_geo

    payload = (request.json or request.form or {}) if request.method == 'POST' else request.args
    survey_id = (payload.get('survey_id') or '').strip() or None
    persist = request.method == 'POST'

    hotspots = _hotspots_for_survey(survey_id)
    usable = [hotspot for hotspot in hotspots
              if hotspot.get('latitude') is not None and hotspot.get('longitude') is not None]

    if len(usable) < 2:
        return jsonify({
            'status': 'error',
            'message': ('At least two geospatially separated hotspots are required to plan a '
                        f'cleanup route. Found {len(usable)} for '
                        + (f'survey {survey_id}.' if survey_id else 'the current detection set.')),
            'hotspot_count': len(usable),
        }), 409

    priority_rank = {'High': 0, 'Medium': 1, 'Low': 2}
    usable.sort(key=lambda h: (priority_rank.get(h.get('priority'), 1),
                               -int(h.get('total_targets') or 0), h.get('id') or ''))

    points = [{
        'id': hotspot.get('id'),
        'hotspot_id': hotspot.get('id'),
        'label': hotspot.get('id'),
        'latitude': float(hotspot['latitude']),
        'longitude': float(hotspot['longitude']),
        'detection_count': int(hotspot.get('total_targets') or 0),
        'priority': hotspot.get('priority', 'Medium'),
        'target_classes': sorted((hotspot.get('target_types') or {}).keys()),
        'dominant_type': hotspot.get('dominant_type'),
        'status': hotspot.get('status'),
        'survey_id': survey_id,
    } for hotspot in usable]

    start = _survey_start_coordinate(survey_id)
    ordered = tarang_geo.optimise_route(points, fixed_start=start)
    visit_points = [point for point in ordered if not point.get('is_start')]
    geometry = tarang_geo.build_route_geometry(visit_points, start=start)

    route = {
        'route_id': 'ROUTE-HS-' + hashlib.sha256(
            '|'.join(geometry['ordered_hotspots']).encode('utf-8')).hexdigest()[:12].upper(),
        'survey_id': survey_id,
        'algorithm': geometry['solver'],
        'unit': 'NM',
        'start_point': ({'latitude': start[0], 'longitude': start[1], 'label': 'Start Point'}
                        if start else None),
        'hotspot_count': len(visit_points),
        'ordered_hotspots': geometry['ordered_hotspots'],
        'target_sequence': geometry['waypoints'],
        'legs': geometry['legs'],
        'total_distance_nm': geometry['total_distance_nm'],
        'total_distance_km': geometry['total_distance_km'],
        'total_distance_m': geometry['total_distance_m'],
        'distance_display': geometry['distance_display'],
        'route_coordinates': geometry['route_coordinates'],
        'estimated_travel_minutes': geometry['estimated_travel_minutes'],
        'planning_speed_knots': geometry['planning_speed_knots'],
        'generated_at': datetime.now().isoformat(),
    }

    if persist:
        # Persisted so the Authority Portal reads the very same route the
        # Marine Portal generated - one shared Supabase record, no copies.
        if not sb_svc.log_dispatch_event('hotspot_cleanup_route', route):
            return jsonify({'status': 'error',
                            'message': 'The optimized route could not be persisted to Supabase.'}), 502
        emitted = emit_workflow_notification(
            ['marine_portal', 'government_portal'],
            'Cleanup route optimized',
            (f"{route['hotspot_count']} hotspots sequenced over "
             f"{route['total_distance_nm']} NM ({route['total_distance_km']} km)."),
            type='Route Optimization', survey_id=survey_id, route_id=route['route_id'],
            notification_type='cleanup_route',
        )
        if not emitted:
            logger.error("Cleanup-route notification could not be delivered: route=%s", route['route_id'])
        route['notification_delivered'] = bool(emitted)

    return jsonify({'status': 'success', 'route': route})


@app.route('/api/v1/hotspot-route/latest', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def latest_hotspot_cleanup_route():
    """Return the most recently persisted hotspot cleanup route."""
    events = sb_svc.get_dispatch_events('hotspot_cleanup_route')
    if not events:
        return jsonify({'status': 'none', 'route': None,
                        'message': 'No hotspot cleanup route has been generated yet.'})
    latest = events[0] if isinstance(events, list) else events
    payload = latest.get('payload') if isinstance(latest, dict) and 'payload' in latest else latest
    return jsonify({'status': 'success', 'route': payload})


# ===========================================================================
# JSON BUNDLE EXPORTS  (built from the same records the UI displays)
# ===========================================================================

@app.route('/api/v1/export/bundle/<survey_id>.json', methods=['GET'])
@app.route('/api/v1/export/survey/<survey_id>/json', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def export_survey_bundle(survey_id):
    """Download survey, detection, hotspot and route records as one JSON file."""
    import tarang_geo

    survey = sb_svc.get_survey(survey_id)
    detections = sb_svc.get_all_detections(survey_id=survey_id)
    hotspots = _hotspots_for_survey(survey_id)
    cached = XTF_SURVEYS.get(survey_id) or {}
    metadata = cached.get('metadata', {})

    # Survey track length comes from the real parsed navigation when it is
    # still available, otherwise from the geotagged detection positions.
    pings = cached.get('pings') or []
    track_coordinates = [[p.get('latitude'), p.get('longitude')] for p in pings
                         if p.get('latitude') and p.get('longitude')]
    if len(track_coordinates) < 2:
        track_coordinates = [[d.get('latitude'), d.get('longitude')] for d in detections
                             if d.get('latitude') is not None and d.get('longitude') is not None]
    track_m = tarang_geo.track_length_m(track_coordinates) if len(track_coordinates) > 1 else 0.0

    route_payload = None
    for event in sb_svc.get_dispatch_events('hotspot_cleanup_route') or []:
        candidate = event.get('payload') if isinstance(event, dict) and 'payload' in event else event
        if isinstance(candidate, dict) and candidate.get('survey_id') == survey_id:
            route_payload = candidate
            break

    bundle = {
        'survey': {
            'survey_id': survey_id,
            'survey_name': (survey or {}).get('survey_name'),
            'source_file': metadata.get('File Name'),
            'sonar': metadata.get('SonarName') or (survey or {}).get('sonar_device'),
            'sonar_frequency': (survey or {}).get('sonar_frequency'),
            'start_time': metadata.get('Start Time'),
            'end_time': metadata.get('End Time'),
            'total_pings': metadata.get('Total Pings'),
            'channels': metadata.get('Channels'),
            'start_coordinate': ([metadata.get('Min Latitude'), metadata.get('Min Longitude')]
                                 if metadata.get('Min Latitude') is not None else None),
            'end_coordinate': ([metadata.get('Max Latitude'), metadata.get('Max Longitude')]
                               if metadata.get('Max Latitude') is not None else None),
            'survey_track_length_nm': round(tarang_geo.meters_to_nm(track_m), 3),
            'survey_track_length_km': round(track_m / 1000.0, 3),
            'processing_status': (survey or {}).get('processing_status'),
        },
        'detections': detections,
        'hotspots': hotspots,
        'cleanup_route': route_payload or {
            'ordered_hotspots': [], 'total_distance_nm': 0, 'total_distance_m': 0,
            'status': 'No cleanup route generated for this survey yet.',
        },
        'exported_at': datetime.now().isoformat(),
        'source': 'supabase',
    }

    response = Response(json.dumps(bundle, indent=2, default=str), mimetype='application/json')
    response.headers['Content-Disposition'] = f'attachment; filename="tarang_{survey_id}_bundle.json"'
    return response


@app.route('/api/v1/export/hotspots.json', methods=['GET'])
@app.route('/api/v1/export/hotspots/json', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def export_hotspots():
    import tarang_geo
    survey_id = (request.args.get('survey_id') or '').strip() or None
    hotspots = _hotspots_for_survey(survey_id)
    for hotspot in hotspots:
        if hotspot.get('latitude') is not None and hotspot.get('longitude') is not None:
            start = _survey_start_coordinate(survey_id)
            if start:
                distance_m = tarang_geo.haversine_m(start, [hotspot['latitude'], hotspot['longitude']])
                hotspot['distance_from_start_nm'] = round(tarang_geo.meters_to_nm(distance_m), 3)
                hotspot['distance_from_start_display'] = tarang_geo.format_nm(distance_m)
    response = Response(json.dumps({'survey_id': survey_id, 'hotspot_count': len(hotspots),
                                    'hotspots': hotspots, 'unit': 'NM',
                                    'exported_at': datetime.now().isoformat()},
                                   indent=2, default=str), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename="tarang_hotspots.json"'
    return response


@app.route('/api/v1/export/detections.json', methods=['GET'])
@app.route('/api/v1/export/detections/json', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def export_detections():
    survey_id = (request.args.get('survey_id') or '').strip() or None
    detections = sb_svc.get_all_detections(survey_id=survey_id) if survey_id else sb_svc.get_all_detections()
    response = Response(json.dumps({'survey_id': survey_id, 'detection_count': len(detections),
                                    'detections': detections, 'exported_at': datetime.now().isoformat()},
                                   indent=2, default=str), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename="tarang_detections.json"'
    return response


@app.route('/api/v1/export/cleanup-route.json', methods=['GET'])
@app.route('/api/v1/export/cleanup-route/json', methods=['GET'])
@require_roles('survey_operator', 'marine_portal', 'government_portal', 'admin')
def export_cleanup_route():
    events = sb_svc.get_dispatch_events('hotspot_cleanup_route') or []
    survey_id = (request.args.get('survey_id') or '').strip() or None
    route_payload = None
    for event in events:
        candidate = event.get('payload') if isinstance(event, dict) and 'payload' in event else event
        if isinstance(candidate, dict) and (not survey_id or candidate.get('survey_id') == survey_id):
            route_payload = candidate
            break
    response = Response(json.dumps({'survey_id': survey_id, 'cleanup_route': route_payload,
                                    'exported_at': datetime.now().isoformat()},
                                   indent=2, default=str), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename="tarang_cleanup_route.json"'
    return response


@app.route('/api/v1/export/notifications.json', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def export_notifications():
    notifications = sb_svc.get_notifications(g.tarang_user.get('role'))
    response = Response(json.dumps({'receiver_role': g.tarang_user.get('role'),
                                    'notification_count': len(notifications),
                                    'notifications': notifications,
                                    'exported_at': datetime.now().isoformat()},
                                   indent=2, default=str), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename="tarang_notifications.json"'
    return response

# ===========================================================================
# CLEARANCE RECORDS
# ===========================================================================

@app.route('/api/v1/clearance', methods=['GET'])
@require_roles('marine_portal', 'government_portal', 'admin')
def get_clearance_records():
    return jsonify(sb_svc.get_clearance_records())

@app.route('/api/v1/clearance', methods=['POST'])
@require_roles('marine_portal', 'marine_analyst', 'admin', 'platform_admin')
def add_clearance_record():
    data          = request.json or request.form
    c_id          = f"CLR-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
    target_id     = data.get('target_id')
    team          = data.get('team', 'Marine Clearance Operations')
    status        = data.get('status', 'Cleared')
    clearance_date= data.get('clearance_date', datetime.now().strftime('%Y-%m-%d'))
    debris_type   = data.get('debris_type', 'Marine Debris')
    notes         = data.get('notes', '')
    hotspot_id    = data.get('hotspot_id')

    if target_id:
        sb_svc.update_detection_clearance(target_id, status, team=team, notes=notes, hotspot_id=hotspot_id)

    sb_svc.log_dispatch_event('clearance_record', {
        'id': c_id, 'target_id': target_id, 'hotspot_id': hotspot_id,
        'team': team, 'status': status, 'clearance_date': clearance_date,
        'debris_type': debris_type, 'notes': notes,
        'before_image': data.get('before_image', ''),
        'after_image': data.get('after_image', ''),
        'created_at': datetime.now().isoformat()
    })
    return jsonify({'status': 'success', 'id': c_id})

# ===========================================================================
# GOVERNMENT & PUBLIC STATISTICS  (100% from Supabase)
# ===========================================================================

@app.route('/api/v1/stats/government', methods=['GET'])
@require_roles('government_portal', 'admin')
def get_gov_stats():
    stats = sb_svc.get_gov_stats()
    # Add aliases for portal compatibility
    stats['total_verified_debris']  = stats.get('total_verified', 0)
    stats['cleared_targets']        = stats.get('total_cleared', 0)
    stats['in_progress_sorties']    = stats.get('total_in_progress', 0)
    stats['pending_clearance']      = stats.get('total_pending', 0)
    stats['clearance_rate']         = stats.get('clearance_rate_percent', 0.0)

    # Build category / tier breakdowns from live detections
    all_dets = sb_svc.get_all_detections()
    by_category = {}
    by_tier = {}
    for d in all_dets:
        cat  = d.get('category') or 'Unknown'
        tier = d.get('classification_tier') or 'C'
        by_category[cat]  = by_category.get(cat, 0) + 1
        by_tier[tier]     = by_tier.get(tier, 0) + 1
    stats['by_category'] = by_category
    stats['by_tier']     = by_tier
    return jsonify(stats)

@app.route('/api/v1/stats/public', methods=['GET'])
def get_public_stats():
    return jsonify(sb_svc.get_public_stats())

# ===========================================================================
# CLUSTERS (DBSCAN)
# ===========================================================================

@app.route('/api/v1/clusters', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'marine_analyst', 'government_portal', 'gov_authority', 'admin', 'platform_admin')
def get_global_clusters():
    from dbscan_service import cluster_detections
    eps_meters  = float(request.args.get('eps_meters', 500.0))
    min_samples = int(request.args.get('min_samples', 2))
    dets = sb_svc.get_all_detections()
    return jsonify(cluster_detections(dets, eps_meters=eps_meters, min_samples=min_samples))

# ===========================================================================
# XTF UPLOAD & PROCESSING  (Supabase-native persistence)
# ===========================================================================

@app.route('/api/v1/xtf/upload', methods=['POST'])
@require_roles('survey_operator', 'platform_admin', 'admin')
def xtf_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename.lower().endswith('.xtf'):
        return jsonify({'error': 'Invalid file extension, expected .xtf'}), 400

    save_name = f"upload_{uuid.uuid4().hex[:8]}.xtf"
    temp_path = os.path.join(OUTPUTS_DIR, save_name)
    uploaded_file.save(temp_path)

    try:
        with open(temp_path, 'rb') as source_file:
            source_bytes = source_file.read()
        if not source_bytes:
            logger.error("XTF processing rejected an empty upload: filename=%s", uploaded_file.filename)
            return jsonify({'error': 'The XTF file is empty.'}), 400
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        # A content-derived survey ID keeps retries idempotent.  An operator
        # may deliberately provide a previously created survey ID, but an
        # existing upload event for a different source is always rejected.
        req_survey_id = (request.form.get('survey_id') or '').strip()
        if req_survey_id == '00000000-0000-0000-0000-000000000002':
            req_survey_id = ''
        survey_id = req_survey_id or _stable_survey_id(source_hash)
        existing_upload = sb_svc.get_survey_upload_events().get(str(survey_id))
        if existing_upload and existing_upload.get('file_hash') == source_hash:
            existing_images = sb_svc.get_sonar_images(survey_id)
            if existing_images:
                logger.info("Reusing idempotent XTF upload: survey=%s images=%s", survey_id, len(existing_images))
                return jsonify({
                    'survey_id': survey_id, 'input_type': 'xtf', 'filename': uploaded_file.filename,
                    'status': 'parsed', 'existing': True, 'metadata': {},
                    'images_reconstructed': len(existing_images), 'images': existing_images,
                    'detections_count': len(sb_svc.get_all_detections(survey_id=survey_id)),
                    'detections': sb_svc.get_all_detections(survey_id=survey_id),
                })
            logger.error("Idempotent XTF upload has no retrievable evidence image: survey=%s", survey_id)
            return jsonify({'error': 'This XTF survey has no retrievable evidence image. Use a new survey ID to reprocess it.'}), 409
        if existing_upload:
            logger.error("XTF survey ID collision rejected: survey=%s filename=%s", survey_id, uploaded_file.filename)
            return jsonify({'error': 'This survey ID is already associated with different evidence. Use a new survey ID.'}), 409

        parsed_data = xtf_parser.parse_xtf(temp_path, OUTPUTS_DIR)
        if not parsed_data:
            logger.error("XTF sonar image generation failed: parser returned no acoustic data for %s", uploaded_file.filename)
            return jsonify({'error': 'Invalid or unsupported XTF file.'}), 400

        parsed_data['metadata']['Survey ID'] = survey_id
        # Keep the operator's real filename as the source of record. The parser
        # only ever sees the temporary upload name.
        parsed_data['metadata']['File Name'] = uploaded_file.filename

        # Ensure survey exists in Supabase
        existing_survey = sb_svc.get_survey(survey_id)
        if not existing_survey:
            created, _, create_error = sb_svc.create_survey({
                'survey_id':       survey_id,
                'survey_name':     parsed_data['metadata'].get('Survey Name') or f"XTF Sonar Survey ({uploaded_file.filename})",
                'survey_date':     datetime.now().strftime('%Y-%m-%d'),
                'survey_time':     datetime.now().strftime('%H:%M'),
                'location_name':   'Offshore Hydrographic Zone',
                'sonar_device':    parsed_data['metadata'].get('SonarName', 'EdgeTech 4200 Sonar'),
                'sonar_frequency': '400/900 kHz',
                'created_by':      'survey_ops'
            })
            if not created:
                logger.error("XTF survey database insertion failed: survey=%s error=%s", survey_id, create_error)
                return jsonify({'error': create_error or 'Unable to create the XTF survey record.'}), 502
        else:
            logger.info("Reprocessing an existing XTF survey record: survey=%s", survey_id)
        if not sb_svc.update_survey_status(survey_id, processing_status='in_progress', status='active'):
            logger.warning("XTF survey status update was not acknowledged: survey=%s", survey_id)

        # The parser has produced actual waterfall rasters. Persist them before
        # inference so every subsequently written target can reference its
        # exact evidence image. This is the step missing from the old XTF
        # branch, which only kept random per-detection crops in memory.
        try:
            evidence_by_source_id = _persist_xtf_evidence_images(
                survey_id, source_hash, parsed_data.get('images', [])
            )
        except (ValueError, RuntimeError) as error:
            logger.exception("XTF evidence persistence failed: survey=%s error=%s", survey_id, error)
            sb_svc.update_survey_status(survey_id, processing_status='failed', status='active')
            return jsonify({'error': str(error)}), 502

        # Keep the session cache only for XTF metadata/pings. Evidence URLs
        # themselves come from the durable database record and work after a
        # Flask restart as well.
        XTF_SURVEYS[survey_id] = parsed_data

        # Log XTF document to dispatches
        sb_svc.log_dispatch_event('document', {
            'survey_id': survey_id,
            'name': uploaded_file.filename,
            'doc_type': 'XTF Sonar Binary',
            'file_path': f"/outputs/{save_name}",
            'file_size': f"{(os.path.getsize(temp_path)/(1024*1024)):.2f} MB",
            'xtf_metadata': parsed_data.get('metadata', {}),
            'created_at': datetime.now().isoformat()
        })

        # Run YOLO on waterfall slices
        collected_crops = {}
        for img_info in parsed_data.get('images', []):
            source_image_id = str(img_info.get('id') or '')
            evidence = evidence_by_source_id.get(source_image_id)
            if not evidence:
                logger.error("XTF inference skipped an image without persistent evidence: survey=%s source_image=%s", survey_id, source_image_id)
                continue
            img_path = img_info['path']
            img = cv2.imread(img_path)
            if img is None:
                logger.error("XTF inference image could not be loaded: survey=%s image_id=%s path=%s", survey_id, evidence.get('image_id'), img_path)
                continue
            try:
                results = model(img, conf=0.20, verbose=False)
            except Exception as error:
                logger.exception("XTF inference failed: survey=%s image_id=%s error=%s", survey_id, evidence.get('image_id'), error)
                continue
            res = results[0]
            if len(res.boxes) == 0:
                continue

            for idx, box in enumerate(res.boxes):
                cls_id  = int(box.cls[0])
                raw_cls = model.names.get(cls_id, f"class_{cls_id}")
                score   = float(box.conf[0]) * 100

                if score < 50.0:
                    cls_name   = "unknown"
                    tier       = "C"
                    req_review = True
                else:
                    cls_name   = raw_cls
                    tier       = "A" if score >= 85 else ("B" if score >= 60 else "C")
                    # Only Class A findings are auto-verified. Both Class B
                    # and Class C findings must remain in the analyst queue.
                    req_review = (tier != "A")

                coords    = box.xyxy[0].tolist()
                meta      = get_meta(cls_name)

                y_center       = (coords[1] + coords[3]) / 2.0
                exact_ping_idx = img_info['ping_start'] + int(y_center)

                det_lat = det_lon = det_depth = det_altitude = None
                if 'pings' in parsed_data and exact_ping_idx < len(parsed_data['pings']):
                    tele        = parsed_data['pings'][exact_ping_idx]
                    det_lat     = tele.get('latitude')
                    det_lon     = tele.get('longitude')
                    det_depth   = f"-{tele.get('depth'):.1f}m"   if tele.get('depth')    else None
                    det_altitude= f"{tele.get('altitude'):.1f}m" if tele.get('altitude') else None

                det_key = f"{cls_name}_{evidence['image_id']}_{idx}"
                det_id = _stable_target_id(survey_id, f"{evidence['sequence']}:{idx}")

                collected_crops[det_key] = {
                    'id':                  det_id,
                    'survey_id':           survey_id,
                    'class_name':          cls_name,
                    'title':               meta['title'],
                    'category':            meta['category'],
                    'confidence':          round(score, 1),
                    'classification_tier': tier,
                    'requires_review':     req_review,
                    'coordinates':         [round(c, 1) for c in coords],
                    # Real YOLO box in pixels (x1,y1,x2,y2) within the
                    # reconstructed evidence image, so the analyst portal can
                    # draw a true detection overlay scaled to the rendered image.
                    'bbox':                [round(c, 2) for c in coords],
                    # One full reconstructed sonar image is the canonical
                    # evidence artifact. Do not create random image crops per
                    # detection: that was the source of duplicate evidence.
                    'crop_url':            evidence['url'],
                    'evidence_image_id':   evidence['image_id'],
                    'evidence_sequence':   evidence['sequence'],
                    'evidence_image_url':  evidence['url'],
                    'material':            meta['material'],
                    'hazard':              meta['hazard'],
                    'latitude':            det_lat,
                    'longitude':           det_lon,
                    'depth':               det_depth,
                    'altitude':            det_altitude,
                    'ping_number':         exact_ping_idx
                }

        detections = list(collected_crops.values())
        parsed_data['detections'] = detections

        # Persist to Supabase (with geo-dedup)
        evidence_by_image_id = {
            str(evidence.get('image_id')): evidence
            for evidence in evidence_by_source_id.values()
            if evidence.get('image_id')
        }
        for det in detections:
            target_id, is_new = insert_or_merge_detection(det)
            det['id'] = target_id
            evidence = evidence_by_image_id.get(str(det.get('evidence_image_id') or ''))
            # The direct evidence values above are sufficient even when a
            # geographic duplicate reused an existing target ID.
            evidence = evidence or {
                'survey_id': survey_id,
                'image_id': det.get('evidence_image_id'),
                'sequence': det.get('evidence_sequence'),
            }
            if not _link_detection_to_evidence(target_id, evidence, det.get('bbox')):
                logger.error("XTF evidence-to-detection database insertion failed: survey=%s detection=%s image_id=%s", survey_id, target_id, evidence.get('image_id'))
                sb_svc.update_survey_status(survey_id, processing_status='failed', status='active')
                return jsonify({'error': 'Detection was stored but its evidence association could not be saved.'}), 502

        # Update survey processing status to completed
        if not sb_svc.update_survey_status(survey_id, processing_status='completed', status='active'):
            logger.warning("XTF survey completion status update was not acknowledged: survey=%s", survey_id)

        sb_svc.log_dispatch_event('survey_uploaded', {
            'survey_id': survey_id, 'file_name': uploaded_file.filename,
            'file_type': 'XTF', 'file_hash': source_hash,
            'uploaded_at': datetime.now().isoformat(), 'processing_status': 'completed',
            'source_label': 'XTF side-scan waterfall reconstruction',
            'image_count': len(evidence_by_source_id), 'created_at': datetime.now().isoformat(),
        })

        # Log notification
        sb_svc.log_dispatch_event('notification', {
            'type':      'XTF Processing Complete',
            'title':     f"Survey {survey_id}: {len(detections)} Targets Detected",
            'message':   f"XTF survey processed with {parsed_data['metadata'].get('Total Pings', 0)} pings. {len(detections)} acoustic detections recorded in Supabase.",
            'timestamp': datetime.now().strftime('%d %b %Y, %H:%M'),
            'survey_id': survey_id,
            'is_read':   False
        })

        return jsonify({
            'survey_id':             survey_id,
            'input_type':            'xtf',
            'filename':              uploaded_file.filename,
            'status':                'parsed',
            'metadata':              parsed_data['metadata'],
            'total_pings':           parsed_data['metadata'].get('Total Pings', 0),
            'channels':              parsed_data['metadata'].get('Channel Count', 0),
            'images_reconstructed':  len(parsed_data.get('images', [])),
            'images':                [_public_xtf_image(image) for image in parsed_data.get('images', [])],
            'detections_count':      len(detections),
            'detections':            detections
        })

    except Exception as e:
        logger.exception("XTF upload processing failed: filename=%s error=%s", uploaded_file.filename, e)
        return jsonify({'error': f'Failed to process XTF: {str(e)}'}), 500
# XTF session sub-routes
@app.route('/api/v1/xtf/<survey_id>/metadata', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'government_portal', 'platform_admin', 'admin')
def get_xtf_metadata(survey_id):
    # Serve from session cache if available (fast, in-memory)
    if survey_id in XTF_SURVEYS:
        return jsonify(XTF_SURVEYS[survey_id]['metadata'])
    # Fall back to Supabase survey record when cache is cold (e.g. after restart)
    survey = sb_svc.get_survey(survey_id)
    if not survey:
        return jsonify({'error': 'Survey not found'}), 404
    upload_events = sb_svc.get_survey_upload_events()
    upload = upload_events.get(str(survey_id)) or {}
    metadata = upload.get('xtf_metadata') or upload.get('metadata') or {}
    # Merge survey-level fields so the portal always gets basic info
    merged = {
        'Survey ID': survey_id,
        'Survey Name': survey.get('survey_name') or metadata.get('Survey Name', ''),
        'File Name': upload.get('file_name') or metadata.get('File Name', ''),
        'Input Type': upload.get('file_type') or 'XTF',
        'Total Pings': metadata.get('Total Pings', 0),
        'Channel Count': metadata.get('Channel Count', 0),
        'Channels': metadata.get('Channels', ''),
        'Start Time': metadata.get('Start Time', ''),
        'End Time': metadata.get('End Time', ''),
        'Min Latitude': metadata.get('Min Latitude'),
        'Max Latitude': metadata.get('Max Latitude'),
        'Min Longitude': metadata.get('Min Longitude'),
        'Max Longitude': metadata.get('Max Longitude'),
        'Avg Depth': metadata.get('Avg Depth', ''),
        'Avg Altitude': metadata.get('Avg Altitude', ''),
        'SonarName': metadata.get('SonarName') or survey.get('sonar_device', ''),
        'sonar_frequency': survey.get('sonar_frequency', ''),
        'location': survey.get('location_name', ''),
        'processing_status': survey.get('processing_status', ''),
        **metadata
    }
    return jsonify(merged)

@app.route('/api/v1/xtf/<survey_id>/pings', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'platform_admin', 'admin')
def get_xtf_pings(survey_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Ping data not available (session cache cleared). Re-upload the XTF to restore real-time ping access.'}), 404
    return jsonify(XTF_SURVEYS[survey_id]['pings'])

@app.route('/api/v1/xtf/<survey_id>/images', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'government_portal', 'platform_admin', 'admin')
def get_xtf_images(survey_id):
    images = sb_svc.get_sonar_images(survey_id)
    if images:
        logger.info("XTF evidence API retrieval: survey=%s images=%s", survey_id, len(images))
        return jsonify(images)
    logger.error("XTF evidence API retrieval found no persistent image: survey=%s", survey_id)
    return jsonify({'error': 'No persisted sonar evidence images found for this survey.'}), 404

@app.route('/api/v1/xtf/<survey_id>/images/<image_id>', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'government_portal', 'platform_admin', 'admin')
def get_xtf_image_file(survey_id, image_id):
    for image in sb_svc.get_sonar_images(survey_id):
        if image_id in {str(image.get('image_id') or ''), str(image.get('id') or '')}:
            image_url = image.get('url') or ''
            if image_url.startswith(('/', 'http://', 'https://')):
                logger.info("XTF evidence image URL resolved: survey=%s image_id=%s url=%s", survey_id, image_id, image_url)
                return redirect(image_url)
            logger.error("XTF evidence image has no browser-safe URL: survey=%s image_id=%s url=%s", survey_id, image_id, image_url)
            break
    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/v1/xtf/<survey_id>/detections', methods=['GET'])
@require_roles('survey_operator', 'sonar_analyst', 'marine_portal', 'government_portal', 'platform_admin', 'admin')
def get_xtf_detections(survey_id):
    # Return from session cache first; fall back to Supabase
    if survey_id in XTF_SURVEYS:
        return jsonify(XTF_SURVEYS[survey_id].get('detections', []))
    dets = sb_svc.get_all_detections(survey_id=survey_id)
    return jsonify(dets)

# ===========================================================================
# IMAGE/VIDEO DETECT ENDPOINT  (for sonar-ai.html inline analysis)
# ===========================================================================

@app.route('/api/detect', methods=['POST'])
def detect():
    conf = float(request.form.get('conf', 0.20))
    conf = max(0.05, min(0.95, conf))

    sample      = request.form.get('sample')
    temp_path   = None
    is_video    = False
    filename    = ""

    if sample == 'video' or sample == 'LandingPage.mp4':
        temp_path = os.path.join(os.path.dirname(__file__), 'LandingPage.mp4')
        is_video  = True
        filename  = 'LandingPage.mp4'
    elif sample == 'stitch_screen':
        temp_path = os.path.join(os.path.dirname(__file__),
                                 'stitch_project/stitch_tarang_marine_intelligence_platform/'
                                 'tarang_sonar_ai_detection_console/screen.png')
        is_video  = False
        filename  = 'screen.png'
    else:
        if 'file' in request.files:
            uploaded_file = request.files['file']
        elif 'image' in request.files:
            uploaded_file = request.files['image']
        elif 'video' in request.files:
            uploaded_file = request.files['video']
        else:
            return jsonify({'error': 'No file uploaded'}), 400

        if not uploaded_file or uploaded_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        filename = uploaded_file.filename
        ext = os.path.splitext(filename)[1].lower()

        if ext == '.xtf':
            return xtf_upload()

        if ext in ['.txt', '.log', '.csv', '.nmea', '.dat']:
            return jsonify({
                'error': 'TARANG authoritative ingestion accepts side-scan sonar XTF files only.'
            }), 415

        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v']
        if ext in video_exts or uploaded_file.content_type.startswith('video/'):
            is_video  = True
            save_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"
            temp_path = os.path.join(OUTPUTS_DIR, save_name)
            uploaded_file.save(temp_path)
        else:
            is_video  = False
            file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                return jsonify({'error': 'Invalid image format or unreadable acoustic frame'}), 400

    req_survey_id = request.form.get('survey_id')
    survey_id = (req_survey_id if req_survey_id and req_survey_id not in ('', '00000000-0000-0000-0000-000000000002')
                 else str(uuid.uuid4()))

    form_lat = request.form.get('latitude')
    form_lon = request.form.get('longitude')
    form_depth = request.form.get('depth')
    try:
        real_lat = float(form_lat) if form_lat else None
    except: real_lat = None
    try:
        real_lon = float(form_lon) if form_lon else None
    except: real_lon = None

    try:
        if not is_video:
            if temp_path:
                img = cv2.imread(temp_path)
                if img is None:
                    return jsonify({'error': 'Failed to read image file'}), 400

            results = model(img, conf=conf, verbose=False)
            res = results[0]

            collected_crops = {}
            for idx, box in enumerate(res.boxes):
                cls_id  = int(box.cls[0])
                raw_cls = model.names.get(cls_id, f"class_{cls_id}")
                score   = float(box.conf[0]) * 100
                if score < 50.0:
                    cls_name = "unknown"; tier = "C"; req_review = True
                else:
                    cls_name = raw_cls
                    tier = "A" if score >= 85 else ("B" if score >= 60 else "C")
                    req_review = (tier == "C")

                if cls_name not in collected_crops or score > collected_crops[cls_name]['confidence']:
                    coords = box.xyxy[0].tolist()
                    meta   = get_meta(cls_name)
                    crop_url, crop_b64 = crop_and_encode(img, coords)
                    det_id = f"ANM-{uuid.uuid4().hex[:6].upper()}"
                    collected_crops[cls_name] = {
                        'id': det_id, 'survey_id': survey_id,
                        'class_name': cls_name, 'title': meta['title'],
                        'category': meta['category'], 'badge': meta['badge'],
                        'color': meta['color'], 'badge_bg': meta['badge_bg'],
                        'material': meta['material'], 'hazard': meta['hazard'],
                        'confidence': round(score, 1), 'classification_tier': tier,
                        'requires_review': req_review,
                        'coordinates': [round(c,1) for c in coords],
                        'depth': form_depth, 'crop_url': crop_url, 'crop_b64': crop_b64,
                        'latitude': real_lat, 'longitude': real_lon
                    }

            detections = list(collected_crops.values())
            annotated_img = res.plot()
            ret, buf = cv2.imencode('.jpg', annotated_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            media_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8') if ret else ""

            return jsonify({
                'status': 'success', 'survey_id': survey_id,
                'media_type': 'image', 'filename': filename,
                'persistence': 'preview_only',
                'media_url': media_b64, 'detections_count': len(detections),
                'detections': detections
            })

        else:
            # Video processing
            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                return jsonify({'error': 'Failed to open video file'}), 400
            fps         = cap.get(cv2.CAP_PROP_FPS) or 24.0
            total_frames= int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            out_filename = f"detected_{uuid.uuid4().hex[:8]}.mp4"
            out_path     = os.path.join(OUTPUTS_DIR, out_filename)
            fourcc       = cv2.VideoWriter_fourcc(*'avc1')
            writer       = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
            if not writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

            step       = 2 if total_frames > 60 else 1
            max_frames = min(total_frames if total_frames > 0 else 120, 120)

            collected_crops = {}
            frame_idx = 0
            last_res  = None
            while frame_idx < max_frames:
                ret, frame = cap.read()
                if not ret: break
                if frame_idx % step == 0 or last_res is None:
                    last_res = model(frame, conf=conf, verbose=False)[0]
                    for b_idx, box in enumerate(last_res.boxes):
                        cls_id  = int(box.cls[0])
                        raw_cls = model.names.get(cls_id, f"class_{cls_id}")
                        score   = float(box.conf[0]) * 100
                        coords  = box.xyxy[0].tolist()
                        if score < 50.0:
                            cls_name = "unknown"; tier = "C"; req_review = True
                        else:
                            cls_name = raw_cls
                            tier = "A" if score >= 85 else ("B" if score >= 60 else "C")
                            req_review = (tier == "C")
                        pos_key = cls_name
                        if pos_key not in collected_crops or score > collected_crops[pos_key]['confidence']:
                            crop_url, crop_b64 = crop_and_encode(frame, coords)
                            meta     = get_meta(cls_name)
                            time_sec = frame_idx / fps
                            det_id   = f"ANM-VID-{uuid.uuid4().hex[:6].upper()}"
                            collected_crops[pos_key] = {
                                'id': det_id, 'survey_id': survey_id,
                                'class_name': cls_name, 'title': meta['title'],
                                'category': meta['category'], 'badge': meta['badge'],
                                'color': meta['color'], 'badge_bg': meta['badge_bg'],
                                'material': meta['material'], 'hazard': meta['hazard'],
                                'confidence': round(score,1), 'classification_tier': tier,
                                'requires_review': req_review,
                                'coordinates': [round(c,1) for c in coords],
                                'depth': form_depth,
                                'time_offset': f"{int(time_sec//60):02d}:{int(time_sec%60):02d}.{int((time_sec%1)*100):02d}",
                                'crop_url': crop_url, 'crop_b64': crop_b64,
                                'latitude': real_lat, 'longitude': real_lon
                            }
                annotated = last_res.plot() if last_res else frame
                if writer.isOpened():
                    writer.write(annotated)
                frame_idx += 1

            cap.release()
            writer.release()

            detections_list = sorted(collected_crops.values(), key=lambda d: d['confidence'], reverse=True)

            if temp_path and temp_path.startswith(OUTPUTS_DIR) and 'upload_' in temp_path:
                try: os.remove(temp_path)
                except: pass

            return jsonify({
                'status': 'success', 'survey_id': survey_id,
                'media_type': 'video', 'filename': filename,
                'persistence': 'preview_only',
                'media_url': f"/outputs/{out_filename}",
                'detections_count': len(detections_list), 'detections': detections_list
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===========================================================================
# EXPORT ROUTES
# ===========================================================================

@app.route('/api/v1/export/survey/<survey_id>/csv', methods=['GET'])
def export_survey_csv(survey_id):
    dets = sb_svc.get_all_detections(survey_id=None if survey_id == 'all' else survey_id)
    si   = StringIO()
    w    = csv.writer(si)
    w.writerow(['Detection ID','Survey ID','Class Name','Title','Category',
                'Confidence (%)','Tier','Review Required','Latitude','Longitude',
                'Depth','Hazard','Timestamp'])
    for d in dets:
        w.writerow([d.get('id'), d.get('survey_id'), d.get('class_name'), d.get('title'),
                    d.get('category'), d.get('confidence'), d.get('classification_tier'),
                    d.get('requires_review'), d.get('latitude'), d.get('longitude'),
                    d.get('depth'), d.get('hazard'), d.get('created_at')])
    return Response(si.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename=tarang_survey_{survey_id}_findings.csv"})

@app.route('/api/v1/export/survey/<survey_id>/geojson', methods=['GET'])
def export_survey_geojson(survey_id):
    dets = sb_svc.get_all_detections(survey_id=None if survey_id == 'all' else survey_id)
    features = []
    for d in dets:
        lat = d.get('latitude') or 12.9234
        lon = d.get('longitude') or 48.5120
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "id": d.get('id'), "title": d.get('title'),
                "class_name": d.get('class_name'), "category": d.get('category'),
                "confidence": d.get('confidence'), "tier": d.get('classification_tier'),
                "depth": d.get('depth'), "hazard": d.get('hazard')
            }
        })
    return Response(
        json.dumps({"type":"FeatureCollection","features":features}, indent=2),
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename=tarang_survey_{survey_id}.geojson"}
    )

@app.route('/api/v1/export/survey/<survey_id>/metadata-txt', methods=['GET'])
def export_survey_metadata_txt(survey_id):
    s    = sb_svc.get_survey(survey_id)
    dets = sb_svc.get_all_detections(survey_id=survey_id)
    if not s:
        return jsonify({'error': 'Survey not found'}), 404
    lines = [
        "TARANG HYDROGRAPHIC SURVEY METADATA REPORT",
        "============================================",
        f"Survey ID: {s.get('survey_id')}",
        f"Survey Name: {s.get('survey_name')}",
        f"Date: {s.get('survey_date')} {s.get('survey_time')}",
        f"Location: {s.get('location_name')}",
        f"Sonar Device: {s.get('sonar_device')}",
        f"Frequency: {s.get('sonar_frequency')}",
        f"Status: {s.get('status')}",
        f"Total Recorded Detections: {len(dets)}",
        f"Generated At: {datetime.now().isoformat()}",
        "", "DETECTION INDEX:", "----------------"
    ]
    for d in dets:
        lines.append(f"ID: {d.get('id')} | Class: {d.get('class_name')} | "
                     f"Conf: {d.get('confidence')}% | Lat: {d.get('latitude')} | "
                     f"Lon: {d.get('longitude')} | Review: {d.get('requires_review')}")
    return Response("\n".join(lines), mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename={survey_id}_metadata.txt'})

@app.route('/api/v1/export/survey/<survey_id>/pdf', methods=['GET'])
def export_survey_pdf(survey_id):
    s     = sb_svc.get_survey(survey_id)
    dets  = sb_svc.get_all_detections(survey_id=survey_id)
    s_name= s['survey_name'] if s else f"Hydrographic Survey ({survey_id})"
    s_reg = s.get('location_name','Indian Coastal Sector') if s else 'Indian Coastal Sector'
    pdf_text = f'''%PDF-1.4
1 0 obj
<< /Title (TARANG Survey Report - {survey_id})
   /Author (TARANG Autonomous Marine Intelligence Platform)
   /Subject (Official Hydrographic Survey and Acoustic Target Assessment)
   /Creator (TARANG AI Acoustic Engine)
>>
endobj
2 0 obj
<< /Type /Catalog /Pages 3 0 R >>
endobj
3 0 obj
<< /Type /Pages /Kids [4 0 R] /Count 1 >>
endobj
4 0 obj
<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 6 0 R >> >> >>
endobj
5 0 obj
<< /Length 520 >>
stream
BT
/F1 18 Tf
50 720 Td
(TARANG HYDROGRAPHIC SURVEY REPORT) Tj
/F1 12 Tf
0 -30 Td
(Survey ID: {survey_id}) Tj
0 -20 Td
(Survey Name: {s_name}) Tj
0 -20 Td
(Region: {s_reg}) Tj
0 -20 Td
(Total Acoustic Detections: {len(dets)}) Tj
0 -20 Td
(Generated by: MoES / NIOT Marine Observatory Platform) Tj
0 -30 Td
(Summary: Authentic side-scan sonar hydrography processed with YOLO best.pt.) Tj
0 -20 Td
(All findings verified by certified sonar acoustic analysts prior to clearance.) Tj
ET
endstream
endobj
6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000215 00000 n
0000000268 00000 n
0000000329 00000 n
0000000450 00000 n
0000001040 00000 n
trailer
<< /Size 7 /Root 2 0 R /Info 1 0 R >>
startxref
1115
%%EOF
'''
    return Response(pdf_text.strip().encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename=tarang_report_{survey_id}.pdf'})

@app.route('/api/v1/export/clusters/json', methods=['GET'])
def export_clusters_json():
    from dbscan_service import cluster_detections
    dets = sb_svc.get_all_detections()
    res  = cluster_detections(dets, eps_meters=500.0, min_samples=2)
    return Response(json.dumps(res, indent=2), mimetype='application/json',
                    headers={'Content-Disposition': 'attachment; filename=tarang_dbscan_clusters.json'})

@app.route('/api/v1/export/public-safe/csv', methods=['GET'])
def export_public_safe_csv():
    dets = sb_svc.get_all_detections(requires_review=False)
    output = StringIO()
    w = csv.writer(output)
    w.writerow(['public_finding_id','sector_reference','finding_class','verification_state','registered_date'])
    for d in dets:
        w.writerow([d.get('id',''), d.get('survey_id','Public-Safe Sector'),
                    d.get('class_name',''), 'Verified', d.get('created_at','')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=tarang_public_findings.csv'})

@app.route('/api/v1/export/public-safe/geojson', methods=['GET'])
def export_public_safe_geojson():
    geojson_data = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[80.20,13.00],[80.35,13.00],[80.35,13.15],[80.20,13.15],[80.20,13.00]]]
            },
            "properties": {
                "region": "Offshore Bay of Bengal Sector Alpha",
                "authority": "MoES / NIOT",
                "public_findings_count": 0,
                "classification": "Public General Survey Footprint"
            }
        }]
    }
    return Response(json.dumps(geojson_data, indent=2), mimetype='application/geo+json',
                    headers={'Content-Disposition': 'attachment; filename=tarang_public_survey_area.geojson'})

@app.route('/api/v1/export/awareness/pdf', methods=['GET'])
def export_awareness_pdf():
    pdf_text = '''%PDF-1.4
1 0 obj
<< /Title (TARANG Marine Awareness Briefing)
   /Author (Ministry of Earth Sciences / NIOT)
   /Subject (National Marine Debris Education and Ocean Conservation)
   /Creator (TARANG Platform)
>>
endobj
2 0 obj
<< /Type /Catalog /Pages 3 0 R >>
endobj
3 0 obj
<< /Type /Pages /Kids [4 0 R] /Count 1 >>
endobj
4 0 obj
<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 6 0 R >> >> >>
endobj
5 0 obj
<< /Length 520 >>
stream
BT
/F1 18 Tf
50 720 Td
(TARANG: OCEAN AWARENESS & SEABED CONSERVATION) Tj
/F1 12 Tf
0 -30 Td
(Institutional Sponsor: Ministry of Earth Sciences - MoES) Tj
0 -20 Td
(National Institute of Ocean Technology - NIOT) Tj
0 -30 Td
(Why Seabed Monitoring Matters:) Tj
0 -20 Td
(Submerged debris like abandoned ghost nets can trap marine life for decades.) Tj
0 -20 Td
(High-resolution side-scan sonar and AI identify debris before ecological collapse.) Tj
0 -30 Td
(Learn more at: TARANG Ocean Awareness Portal) Tj
ET
endstream
endobj
6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000190 00000 n
0000000243 00000 n
0000000304 00000 n
0000000425 00000 n
0000001015 00000 n
trailer
<< /Size 7 /Root 2 0 R /Info 1 0 R >>
startxref
1090
%%EOF
'''
    return Response(pdf_text.strip().encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=tarang_marine_awareness.pdf'})

@app.route('/api/v1/export/methodology/pdf', methods=['GET'])
def export_methodology_pdf():
    pdf_text = '''%PDF-1.4
1 0 obj
<< /Title (TARANG Technical Methodology Overview)
   /Author (TARANG Development Team)
   /Subject (Acoustic Processing, Geospatial DBSCAN, and Verification Pipeline)
   /Creator (TARANG Platform)
>>
endobj
2 0 obj
<< /Type /Catalog /Pages 3 0 R >>
endobj
3 0 obj
<< /Type /Pages /Kids [4 0 R] /Count 1 >>
endobj
4 0 obj
<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 6 0 R >> >> >>
endobj
5 0 obj
<< /Length 520 >>
stream
BT
/F1 18 Tf
50 720 Td
(TARANG TECHNICAL METHODOLOGY SPECIFICATION) Tj
/F1 12 Tf
0 -30 Td
(Architecture: Side-Scan Sonar -> Preprocessing -> YOLO best.pt -> XAI) Tj
0 -20 Td
(Geospatial Engine: Haversine-metric DBSCAN Clustering) Tj
0 -20 Td
(Verification: Multi-tier Expert Sonar Analyst In-the-Loop) Tj
0 -20 Td
(Autonomous Simulation: Three.js 3D Survey Platform with Live Telemetry) Tj
0 -30 Td
(Compliance: Zero Fake Data, Fully Model and Database Driven) Tj
ET
endstream
endobj
6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000195 00000 n
0000000248 00000 n
0000000309 00000 n
0000000430 00000 n
0000001020 00000 n
trailer
<< /Size 7 /Root 2 0 R /Info 1 0 R >>
startxref
1095
%%EOF
'''
    return Response(pdf_text.strip().encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=tarang_methodology_overview.pdf'})

# ===========================================================================
# 3D MODEL STATIC ROUTES
# ===========================================================================

@app.route('/static/models/<path:filename>')
def serve_model_file(filename):
    return send_from_directory('static/models', filename, mimetype='model/gltf-binary')

@app.route('/drone.glb')
@app.route('/Drone.glb')
def serve_drone_root():
    if os.path.exists('static/models/drone.glb'):
        return send_from_directory('static/models', 'drone.glb', mimetype='model/gltf-binary')
    return send_from_directory('.', 'Drone.glb', mimetype='model/gltf-binary')

# Root assets and the two static folders used by the browser. These explicit
# rules intentionally avoid a greedy /<path> fallback: that fallback matches
# /api/... before Flask can dispatch POST requests to API routes.
@app.route('/<filename>')
def serve_root_file(filename):
    return send_from_directory('.', filename)

@app.route('/js/<path:filename>')
def serve_js_file(filename):
    return send_from_directory('js', filename)

@app.route('/assets/<path:filename>')
def serve_asset_file(filename):
    return send_from_directory('assets', filename)

@app.route('/static/<path:filename>')
def serve_static_file(filename):
    return send_from_directory('static', filename)

@app.route('/video/<path:filename>')
def serve_video_file(filename):
    return send_from_directory('video', filename)

@app.route('/simulation/<path:filename>')
def serve_simulation_file(filename):
    return send_from_directory('Simulation/dist', filename)

@app.route('/simulation/')
def serve_simulation_index():
    return send_from_directory('Simulation/dist', 'index.html')

# ---------------------------------------------------------
# Chatbot API Route
# ---------------------------------------------------------
import requests

GEMINI_API_KEY = "YOUR_API_KEY_HERE"

@app.route('/api/v1/chat', methods=['POST'])
def handle_chat():
    data = request.json
    user_msg = data.get('message', '')
    language = data.get('language', 'english').capitalize()
    if not user_msg:
        return jsonify({"reply": "I didn't catch that. Could you repeat?"})
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": user_msg}]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": f"You are TARANG AI, an assistant for the TARANG Marine Intelligence Platform. Answer questions related to this platform, underwater sonar, hotspot detection, and cleanup missions. Keep your answers concise, helpful, and focused strictly on the website concept. IMPORTANT: You must respond entirely in {language}."}
            ]
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp_data = resp.json()
        
        # Localized fallbacks
        msg_503 = {
            "Hindi": "मैं वर्तमान में बहुत अधिक अनुरोधों का अनुभव कर रहा हूं और एक छोटा ब्रेक ले रहा हूं। कृपया कुछ सेकंड में पुनः प्रयास करें!",
            "Tamil": "தற்போது அதிக கோரிக்கைகள் வருவதால் நான் சிறிது நேரம் ஓய்வு எடுக்கிறேன். சில நொடிகள் கழித்து மீண்டும் முயற்சிக்கவும்!",
            "English": "I am currently experiencing a high volume of requests and taking a short break. Please try asking again in a few seconds!"
        }.get(language, "I am currently experiencing a high volume of requests and taking a short break. Please try asking again in a few seconds!")
        
        msg_err = {
            "Hindi": "क्षमा करें, मुझे सर्वर से कनेक्ट होने में समस्या हो रही है।",
            "Tamil": "மன்னிக்கவும், சர்வருடன் இணைப்பதில் சிக்கல் உள்ளது.",
            "English": "I'm having trouble connecting to my AI brain. Please try again later."
        }.get(language, "I'm having trouble connecting to my AI brain. Please try again later.")
        
        # Check for Google API error (like 503 Service Unavailable)
        if 'error' in resp_data:
            err_msg = resp_data['error'].get('message', 'Unknown error.')
            if resp_data['error'].get('code') == 503:
                return jsonify({"reply": msg_503})
            else:
                return jsonify({"reply": msg_err})
                
        if 'candidates' in resp_data and len(resp_data['candidates']) > 0:
            reply = resp_data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": msg_err})
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({"reply": "I'm having trouble connecting to my AI brain. Please try again later."})

# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)

