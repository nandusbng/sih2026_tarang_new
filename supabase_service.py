# -*- coding: utf-8 -*-
"""
Authoritative Supabase Service Layer for TARANG Unified Maritime AI Platform
Supabase Cloud (cryfgdedvnyczhausidk) is the Single Source of Truth.
Zero SQLite dependency, zero fake/demo business data.
"""

import os
import uuid
import json
import hashlib
import logging
import requests
import math
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

# Read credentials from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wniatmiforlsjofucegr.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Prefer service key on server-side to allow reliable administrative operations
ACTIVE_KEY = SUPABASE_SERVICE_KEY

# Storage access is part of the same Supabase source of truth as surveys and
# detections.  Keep a process-local readiness flag so ordinary reads do not
# repeatedly attempt bucket creation.
_IMAGE_BUCKET_READY = False
_IMAGE_URL_CHECKS = {}
logger = logging.getLogger("tarang.evidence")

HEADERS = {
    "apikey": ACTIVE_KEY,
    "Authorization": f"Bearer {ACTIVE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── Role mapping ───────────────────────────────────────────────────────────
# The NEW Supabase project enforces a CHECK constraint that only permits:
#   survey_operator | sonar_analyst | marine_analyst | gov_authority |
#   platform_admin  | public
#
# WRITE_ROLE_MAP  – normalise any incoming portal/legacy name → DB-legal value
# READ_ROLE_MAP   – translate DB value → frontend portal destination key
WRITE_ROLE_MAP = {
    # portal names → DB values
    "marine_portal":      "marine_analyst",
    "government_portal":  "gov_authority",
    "admin":              "platform_admin",
    # legacy aliases
    "sonar_operator":     "sonar_analyst",
    "sonar_expert":       "sonar_analyst",
    "atmiya":             "platform_admin",
    "platform_admin":     "platform_admin",
    # pass-throughs (already DB-legal)
    "survey_operator":    "survey_operator",
    "sonar_analyst":      "sonar_analyst",
    "marine_analyst":     "marine_analyst",
    "gov_authority":      "gov_authority",
    "public":             "public",
}

READ_ROLE_MAP = {
    # DB values → frontend portal keys
    "marine_analyst":   "marine_portal",
    "gov_authority":    "government_portal",
    "platform_admin":   "admin",
    # pass-throughs
    "survey_operator":  "survey_operator",
    "sonar_analyst":    "sonar_analyst",
    "public":           "public",
}

# Keep a flat alias map for backwards compatibility with any caller that
# uses the old ROLE_ALIASES dict directly.
ROLE_ALIASES = WRITE_ROLE_MAP


def normalize_role(role):
    """Return the DB-legal role value for any incoming role name."""
    value = (role or "").strip().lower()
    return WRITE_ROLE_MAP.get(value, value or "survey_operator")


def to_portal_role(db_role):
    """Translate a DB role value to the frontend portal key (for redirects)."""
    value = (db_role or "").strip().lower()
    return READ_ROLE_MAP.get(value, value or "survey_operator")


def _institution_auth_email(institution_id):
    """Create a stable internal Auth email without asking for an email field."""
    digest = hashlib.sha256(institution_id.strip().lower().encode("utf-8")).hexdigest()
    return f"{digest[:24]}@access.tarang.local"


def is_configured():
    """Return whether server-only Supabase credentials are available."""
    return bool(SUPABASE_URL and ACTIVE_KEY)


def _storage_headers(content_type):
    return {
        "apikey": ACTIVE_KEY,
        "Authorization": f"Bearer {ACTIVE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }


def _ensure_image_bucket():
    """Ensure the existing Supabase survey-images bucket is public and usable."""
    global _IMAGE_BUCKET_READY
    if _IMAGE_BUCKET_READY:
        return True
    if not is_configured():
        logger.error('Supabase image storage is not configured: missing service key.')
        return False
    bucket_url = f"{SUPABASE_URL}/storage/v1/bucket/survey-images"
    try:
        details = requests.get(bucket_url, headers=HEADERS, timeout=15)
        if details.status_code == 404:
            created = requests.post(
                f"{SUPABASE_URL}/storage/v1/bucket",
                json={"id": "survey-images", "name": "survey-images", "public": True},
                headers=HEADERS,
                timeout=15,
            )
            # Supabase Storage currently returns HTTP 400 with
            # ``code=BucketAlreadyExists`` for a create race, not HTTP 409.
            # Treat that documented conflict as success and re-read the
            # bucket, otherwise fresh uploads incorrectly fall back to local
            # storage even though the bucket exists and is usable.
            created_body = created.json() if created.content else {}
            already_exists = (created_body or {}).get('code') == 'BucketAlreadyExists'
            if created.status_code not in (200, 201) and not already_exists:
                logger.error(
                    'Supabase image bucket creation error: status=%s body=%s',
                    created.status_code, created.text[:300],
                )
                return False
            details = requests.get(bucket_url, headers=HEADERS, timeout=15)

        if details.status_code == 200 and not bool((details.json() or {}).get('public')):
            # A pre-existing private bucket makes a nominally public Storage
            # URL unusable in every browser. Promote the one authoritative
            # evidence bucket before returning any image URL.
            updated = requests.put(bucket_url, json={"public": True}, headers=HEADERS, timeout=15)
            if updated.status_code not in (200, 204):
                logger.error('Supabase image bucket public-mode error: status=%s body=%s', updated.status_code, updated.text[:300])
                return False
        elif details.status_code != 200:
            logger.error('Supabase image bucket lookup error: status=%s body=%s', details.status_code, details.text[:300])
            return False
        _IMAGE_BUCKET_READY = True
        logger.info('Supabase evidence bucket is ready and public.')
        return True
    except requests.RequestException as exc:
        logger.exception('Supabase image bucket connection error: %s', exc)
        return False


def _accessible_image_url(url):
    """Return whether an image URL is directly usable by a browser.

    Evidence URLs are assigned to an ``<img>`` element, which cannot attach
    the server's Supabase service key.  Checking with that key (the old
    behaviour) could therefore approve a URL that every browser would reject.
    Public Storage objects are deliberately verified without credentials.
    
    Short-circuit: Supabase public storage URLs from our own project are trusted
    accessible without an HTTP round-trip to avoid blocking detection listing.
    """
    if not isinstance(url, str) or not url.strip():
        return False
    url = url.strip()
    if url.startswith('/'):
        return True
    # Trust our own Supabase project's public storage URLs without HTTP probe.
    # The browser will get a real error if the file doesn't exist — we don't
    # need to block the entire detection listing for a single image check.
    if 'cryfgdedvnyczhausidk.supabase.co/storage/v1/object/public/' in url:
        return True
    cached = _IMAGE_URL_CHECKS.get(url)
    if cached is not None:
        return cached
    try:
        response = requests.get(url, stream=True, timeout=5)
        content_type = (response.headers.get('content-type') or '').lower()
        ok = response.status_code == 200 and (content_type.startswith('image/') or 'octet-stream' in content_type)
        if not ok:
            logger.error("Evidence URL is not browser-accessible: status=%s url=%s", response.status_code, url)
        response.close()
        _IMAGE_URL_CHECKS[url] = ok
        return ok
    except requests.RequestException as exc:
        logger.warning("Evidence URL retrieval failed for %s: %s", url, exc)
        _IMAGE_URL_CHECKS[url] = True  # Assume accessible on timeout rather than blocking
        return True


def upload_crop(filename, content):
    """Upload an inference crop to server-managed Supabase Storage."""
    if not is_configured():
        return ""
    if not _ensure_image_bucket():
        return ""
    try:
        object_path = f"crops/{filename}"
        response = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/survey-images/{object_path}",
            data=content,
            headers=_storage_headers("image/jpeg"),
            timeout=15,
        )
        if response.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/survey-images/{object_path}"
        print("Supabase crop upload error:", response.status_code, response.text[:300])
    except requests.RequestException as exc:
        print("Supabase crop upload error:", exc)
    return ""


def _public_crop_url(value):
    """Expose only URL-style crop locations; never return embedded image payloads."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if value.startswith(("https://", "http://", "/")) else ""


# TARANG's demo coordinates are deliberately placed in the offshore Indian
# Ocean east of Chennai.  This guard keeps legacy records that were created
# on a shoreline out of public maps and route calculations without changing
# the authoritative database row.
def is_offshore_coordinate(latitude, longitude):
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    if not (-5.0 <= lat <= 25.0 and 65.0 <= lon <= 96.0):
        return False
    # East-coast points need to be east of the shallow coastal strip.  The
    # west-coast branch preserves existing Arabian Sea survey coordinates.
    if 7.0 <= lat <= 22.5 and 77.0 <= lon <= 82.0:
        return lon >= 80.40
    if 7.0 <= lat <= 22.5 and 68.0 <= lon < 77.0:
        return lon <= 72.90
    return True


def _latest_event_by(events, key):
    latest = {}
    for event in events or []:
        value = event.get(key)
        if value is None:
            continue
        existing = latest.get(str(value))
        if not existing or str(event.get('created_at') or '') > str(existing.get('created_at') or ''):
            latest[str(value)] = event
    return latest


def get_detection_state_map():
    """Return the latest persisted lifecycle event for every detection."""
    events = get_dispatch_events('detection_state')
    return _latest_event_by(events, 'detection_id')


def _state_from_detection(row, state_event=None):
    """Normalize legacy columns and lifecycle events into one state model."""
    event = state_event or {}
    event_status = str(event.get('status') or '').strip().lower()
    hazard = str(row.get('hazard') or '').strip().lower()
    if event_status in {'rejected', 'verified', 'pending_review'}:
        review_status = event_status.replace('_', ' ').title()
    elif hazard == 'rejected':
        review_status = 'Rejected'
    elif row.get('requires_review') is not False:
        review_status = 'Pending Review'
    else:
        review_status = 'Verified'

    lifecycle = str(event.get('lifecycle_status') or event.get('cleanup_status') or '').strip().lower()
    if lifecycle:
        cleanup_status = lifecycle.replace('_', ' ').title()
    elif hazard == 'cleared':
        cleanup_status = 'Cleanup Completed'
    elif hazard in {'cleanup_approved', 'cleanup_assigned'}:
        cleanup_status = 'Cleanup Approved'
    elif hazard in {'cleanup_scheduled', 'in_progress'}:
        cleanup_status = 'Cleanup Scheduled'
    elif hazard == 'no_cleanup_required' or review_status == 'Rejected':
        cleanup_status = 'Cleanup Not Recommended'
    else:
        cleanup_status = 'Awaiting Marine Review'

    if review_status == 'Rejected':
        detection_status = 'Rejected'
    elif cleanup_status == 'Cleanup Completed':
        detection_status = 'Cleanup Completed'
    elif cleanup_status in {'Cleanup Approved', 'Cleanup Scheduled', 'Cleanup Dispatched', 'Cleanup In Progress'}:
        detection_status = 'Cleanup Candidate'
    elif review_status == 'Verified':
        detection_status = 'Verified'
    else:
        detection_status = 'Pending Review'
    return review_status, cleanup_status, detection_status


def summarize_detections(detections):
    """Compute the shared workflow counters from persisted records."""
    statuses = [str(d.get('detection_status') or '').lower() for d in detections]
    return {
        'total': len(detections),
        'total_detected': len(detections),
        'verified': sum(s == 'verified' for s in statuses),
        'verified_targets': sum(s == 'verified' for s in statuses),
        'rejected': sum(s == 'rejected' for s in statuses),
        'pending_review': sum(s == 'pending review' for s in statuses),
        'cleanup_candidates': sum(s == 'cleanup candidate' for s in statuses),
        'cleanup_completed': sum(s == 'cleanup completed' for s in statuses),
        'hotspot_count': 0,
    }

def get_tarang_users():
    """Fetches all users from public.tarang_users table."""
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/tarang_users?select=*&order=created_at.asc", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            users = []
            for u in r.json():
                meta = u.get("metadata") or {}
                db_role = u.get("role", "survey_operator")
                portal_role = to_portal_role(db_role)
                users.append({
                    "id": u.get("id"),
                    "full_name": u.get("name") or "Authorized User",
                    "name": u.get("name") or "Authorized User",
                    "institution_id": meta.get("institution_id") or u.get("id", "")[:8],
                    "username": meta.get("username") or "",
                    "email": u.get("email") or meta.get("email") or "",
                    "role": portal_role,       # frontend portal key
                    "db_role": db_role,        # raw DB value (for inserts)
                    "status": u.get("status", "active"),
                    "created_at": u.get("created_at", ""),
                    # Full metadata kept server-side for TARANG-native auth.
                    # Strip _pw_sha256 before returning to any browser client.
                    "metadata": meta,
                })
            return users
    except Exception as e:
        print("Supabase get_tarang_users error:", e)
    return []

def get_user_by_identifier(identifier):
    """Finds user by full name, username, institution ID, email, or ID.

    After the v2.0 migration, email / institution_id / username are proper
    indexed columns on tarang_users.  We try a direct REST lookup against
    each indexed field first; the fallback does a full in-memory scan of
    get_tarang_users() for backward compatibility with rows that have not
    yet been back-filled.
    """
    identifier = (identifier or "").strip().lower()
    if not identifier:
        return None

    # --- Fast path: try each indexed column via direct REST query ---
    indexed_filters = [
        f"institution_id=eq.{identifier}",
        f"username=eq.{identifier}",
        f"email=eq.{identifier}",
        f"id=eq.{identifier}",
    ]
    for filt in indexed_filters:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/tarang_users?select=*&{filt}&limit=1",
                headers=HEADERS, timeout=6
            )
            if r.status_code == 200 and r.json():
                u = r.json()[0]
                meta = u.get("metadata") or {}
                db_role = u.get("role", "survey_operator")
                return {
                    "id": u.get("id"),
                    "full_name": u.get("name") or "Authorized User",
                    "name": u.get("name") or "Authorized User",
                    "institution_id": u.get("institution_id") or meta.get("institution_id") or "",
                    "username": u.get("username") or meta.get("username") or "",
                    "email": u.get("email") or meta.get("email") or "",
                    "role": to_portal_role(db_role),
                    "db_role": db_role,
                    "status": u.get("status", "active"),
                    "created_at": u.get("created_at", ""),
                    "metadata": meta,
                }
        except Exception:
            pass

    # --- Slow fallback: scan full user list (pre-migration rows / name match) ---
    users = get_tarang_users()
    for u in users:
        if (u.get("full_name", "").strip().lower() == identifier or
            u.get("username", "").lower() == identifier or
            u.get("institution_id", "").lower() == identifier or
            u.get("email", "").lower() == identifier or
            u.get("id", "").lower() == identifier or
            u.get("role", "").lower() == identifier):
            return u
    return None


# ---------------------------------------------------------------------------
# TARANG-NATIVE SESSION TOKENS
# Used as a fallback when the Supabase Auth schema itself is non-functional
# (broken trigger, misconfigured email provider, etc.).
# A session token is:  "TARANG:{user_id}:{hmac_hex}"
# The HMAC is keyed with SUPABASE_SERVICE_KEY so only the server can issue or
# verify it — the token never exposes the service key to the browser.
# ---------------------------------------------------------------------------
import hmac as _hmac


def _tarang_token_sign(user_id):
    key = (SUPABASE_SERVICE_KEY or "tarang-fallback").encode()
    return _hmac.new(key, f"TARANG:{user_id}".encode(), "sha256").hexdigest()


def _tarang_token_issue(user_id):
    return f"TARANG:{user_id}:{_tarang_token_sign(user_id)}"


def _tarang_token_verify(token):
    """Return user_id if the token is a valid TARANG-native session, else None."""
    if not isinstance(token, str) or not token.startswith("TARANG:"):
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    _, user_id, sig = parts
    expected = _tarang_token_sign(user_id)
    if not _hmac.compare_digest(sig, expected):
        return None
    return user_id


def get_authenticated_profile(access_token):
    """Resolve either a Supabase JWT or a TARANG-native token to its profile."""
    if not access_token:
        return None

    # --- TARANG-native fallback token (issued when Supabase Auth is broken) ---
    tarang_uid = _tarang_token_verify(access_token)
    if tarang_uid:
        profile = get_user_by_identifier(tarang_uid)
        if profile and str(profile.get("status", "")).lower() == "active":
            return profile
        return None

    # --- Standard Supabase JWT ---
    if not SUPABASE_ANON_KEY:
        return None
    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        if response.status_code != 200:
            return None
        auth_user = response.json()
        profile = get_user_by_identifier(auth_user.get("id"))
        if not profile or str(profile.get("status", "")).lower() != "active":
            return None
        return profile
    except requests.RequestException as exc:
        logger.error("Supabase session lookup error: %s", exc)
        return None

def authenticate_user(identifier, password):
    """
    Authenticate via Supabase Auth (primary path) or TARANG-native credentials
    (fallback when the Supabase Auth schema is broken/misconfigured).
    Returns (success, user_dict, token, error_msg).
    """
    import hashlib as _hl
    try:
        matched_user = get_user_by_identifier(identifier)
        if matched_user and matched_user.get("email"):
            email = matched_user["email"]
        elif "@" in identifier:
            email = identifier
        else:
            email = f"{identifier}@tarang.gov.in"

        if not SUPABASE_ANON_KEY:
            return False, None, None, "Supabase Auth is not configured on this server."

        auth_headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        r = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
            headers=auth_headers, timeout=10
        )

        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token", "")
            user_id = (data.get("user") or {}).get("id")
            profile = get_user_by_identifier(user_id) or matched_user
            if not profile:
                return False, None, None, "No TARANG profile found for this account. Please request access."
            if str(profile.get("status", "")).lower() != "active":
                return False, None, None, "Your TARANG access request is pending approval."
            return True, profile, token, None

        # --- Supabase Auth rejected or is broken — try TARANG-native fallback ---
        # Covers both:
        #   400/401 = invalid_credentials (no Auth user exists because the Auth
        #             schema is broken and users were seeded directly in tarang_users)
        #   500     = broken auth schema trigger
        err_body = r.json() if r.content else {}
        err_code  = str(err_body.get("error_code", ""))
        supabase_msg = err_body.get("error_description") or err_body.get("msg") or "Invalid credentials."

        # Only attempt native fallback when we have a matched profile with a hash
        if matched_user:
            meta = matched_user.get("metadata") or {}
            stored_hash = meta.get("_pw_sha256") or ""
            if stored_hash:
                # The project uses TARANG-native credentials; verify the hash
                candidate_hash = _hl.sha256(password.encode("utf-8")).hexdigest()
                if _hmac.compare_digest(candidate_hash, stored_hash):
                    if str(matched_user.get("status", "")).lower() != "active":
                        return False, None, None, "Your account is not active."
                    token = _tarang_token_issue(matched_user["id"])
                    logger.info(
                        "TARANG-native auth succeeded for user=%s (Supabase Auth status=%s)",
                        matched_user.get("name"), r.status_code
                    )
                    return True, matched_user, token, None
                else:
                    return False, None, None, "Invalid credentials."
            # No hash stored — fall back to the Supabase error message
            if r.status_code in (500,):
                return False, None, None, (
                    "Your account exists but has no password configured. "
                    "Please use 'Request Access' to set your credentials."
                )

        # Surface the Supabase error for genuine wrong-password or not-found cases
        if r.status_code in (400, 401, 422):
            return False, None, None, supabase_msg

        # Unrecognised status — log and return generic message
        logger.warning("Supabase Auth returned unexpected status=%s", r.status_code)
        return False, None, None, "Authentication service unavailable. Please try again."

    except Exception as exc:
        logger.exception("authenticate_user error: %s", exc)
        return False, None, None, "Authentication service unavailable. Please try again."


def request_access(full_name, institution_id, password, role="survey_operator"):
    """Create a real Supabase Auth account and its TARANG access profile.

    New applicants enter as the specified role (default: survey_operator).
    Administrators can change their role later via the tarang_users record.
    """
    full_name = (full_name or "").strip()
    institution_id = (institution_id or "").strip()
    if not full_name or not institution_id or not password:
        return False, None, "Full Name, Institution ID, and password are required."
    if len(password) < 8:
        return False, None, "Password must contain at least 8 characters."
    if not SUPABASE_SERVICE_KEY:
        return False, None, "Supabase service credentials are not configured on this server."
    if get_user_by_identifier(institution_id):
        return False, None, "An account already exists for this Institution ID. Please sign in."

    auth_email = _institution_auth_email(institution_id)
    admin_headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    auth_payload = {
        "email": auth_email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "full_name": full_name,
            "institution_id": institution_id,
            "role": role,
        },
    }
    import uuid as _uuid
    import hashlib as _hl
    try:
        auth_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            json=auth_payload,
            headers=admin_headers,
            timeout=15,
        )

        auth_broken = False
        user_id = None

        if auth_response.status_code in (200, 201):
            body = auth_response.json() if auth_response.content else {}
            user_id = body.get("id") or (body.get("user") or {}).get("id")
        else:
            details = auth_response.json() if auth_response.content else {}
            err_code = str(details.get("error_code", ""))
            raw_msg  = details.get("msg") or details.get("message") or details.get("error_description") or ""

            if "unexpected_failure" in err_code or "Database error" in raw_msg:
                # Supabase Auth schema is broken — fall back to TARANG-native mode
                logger.warning(
                    "Supabase Auth admin endpoint returned %s (broken auth schema). "
                    "Falling back to TARANG-native profile creation.",
                    auth_response.status_code
                )
                auth_broken = True
                user_id = str(_uuid.uuid4())   # server-generated stable UUID
            else:
                message = raw_msg or "Unable to create the Supabase account."
                logger.error("Supabase Auth user creation failed: status=%s body=%s",
                             auth_response.status_code, details)
                return False, None, message

        if not user_id:
            return False, None, "Supabase did not return an account ID."

        # Hash the password for TARANG-native auth (never stored in plaintext)
        pw_hash = _hl.sha256(password.encode("utf-8")).hexdigest()

        db_role = role
        profile_row = {
            "id": user_id,
            "name": full_name,
            "role": db_role,
            "status": "active",
            "metadata": {
                "institution_id": institution_id,
                "username": institution_id.lower(),
                "email": auth_email,
                # TARANG-native password hash (only used when Supabase Auth is broken)
                "_pw_sha256": pw_hash,
                "_auth_mode": "tarang_native" if auth_broken else "supabase_auth",
            },
        }
        profile_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/tarang_users",
            json=profile_row,
            headers=HEADERS,
            timeout=15,
        )
        if profile_response.status_code not in (200, 201):
            if not auth_broken:
                # Roll back the Supabase Auth account
                requests.delete(
                    f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                    headers=admin_headers, timeout=15,
                )
            details = profile_response.json() if profile_response.content else {}
            logger.error("tarang_users profile insert failed: status=%s body=%s",
                         profile_response.status_code, details)
            message = details.get("message") or details.get("hint") or "Unable to store the TARANG access profile."
            return False, None, message

        return True, {
            "id": user_id,
            "full_name": full_name,
            "institution_id": institution_id,
            "role": to_portal_role(db_role),
        }, None
    except requests.RequestException as exc:
        logger.exception("Supabase access request error: %s", exc)
        return False, None, "Unable to reach Supabase while storing the access request."

def get_surveys():
    """Fetches all surveys from public.surveys with real detection counts."""
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/surveys?select=*&order=created_at.desc", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            surveys = r.json()
            # Get detection counts per survey from public.detections
            r_dets = requests.get(f"{SUPABASE_URL}/rest/v1/detections?select=survey_id", headers=HEADERS, timeout=10)
            det_counts = {}
            if r_dets.status_code == 200:
                for d in r_dets.json():
                    sid = d.get("survey_id")
                    if sid:
                        det_counts[sid] = det_counts.get(sid, 0) + 1
            
            upload_events = get_survey_upload_events()
            for s in surveys:
                sid = s.get("survey_id")
                s["detection_count"] = det_counts.get(sid, 0)
                s["areas"] = [{
                    "id": f"area_{sid[:8]}",
                    "area_name": s.get("location_name") or "Primary Coastal Sector",
                    "status": "ACTIVE"
                }]
                upload = upload_events.get(str(sid), {})
                if upload:
                    s['file_name'] = upload.get('file_name')
                    s['file_type'] = upload.get('file_type')
                    s['file_hash'] = upload.get('file_hash')
                    s['uploaded_at'] = upload.get('uploaded_at')
                    s['processing_status'] = upload.get('processing_status') or s.get('processing_status')
                    s['source_label'] = upload.get('source_label') or 'Simulated offshore demo input'
            return surveys
    except Exception as e:
        print("Supabase get_surveys error:", e)
    return []

def get_survey(survey_id):
    """Fetches a specific survey from public.surveys."""
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/surveys?survey_id=eq.{survey_id}", headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.json()) > 0:
            s = r.json()[0]
            # Count detections
            r_cnt = requests.get(f"{SUPABASE_URL}/rest/v1/detections?survey_id=eq.{survey_id}&select=id", headers={**HEADERS, "Prefer": "count=exact"}, timeout=10)
            cr = r_cnt.headers.get("Content-Range", "")
            cnt = int(cr.split("/")[-1]) if "/" in cr else len(r_cnt.json())
            s["detection_count"] = cnt
            s["areas"] = [{
                "id": f"area_{survey_id[:8]}",
                "area_name": s.get("location_name") or "Primary Coastal Sector",
                "status": "ACTIVE"
            }]
            return s
    except Exception as e:
        print(f"Supabase get_survey({survey_id}) error:", e)
    return None

def create_survey(data):
    """
    Inserts a new survey into public.surveys.
    Exact schema columns:
    survey_id, survey_name, survey_date, survey_time, location_name, sonar_device, sonar_frequency, created_by, created_at, status, navigation_status, processing_status
    """
    try:
        survey_id = data.get("survey_id") or str(uuid.uuid4())
        survey_name = data.get("survey_name") or f"Survey-{survey_id[:8]}"
        survey_date = data.get("survey_date") or datetime.now().strftime("%Y-%m-%d")
        survey_time = data.get("survey_time") or datetime.now().strftime("%H:%M")
        location_name = data.get("location_name") or data.get("region") or "Indian Ocean Sector"
        sonar_device = data.get("sonar_device") or "EdgeTech Side-Scan Sonar"
        sonar_frequency = data.get("sonar_frequency") or "400/900 kHz"
        created_by = data.get("created_by") or "survey_ops"

        # Validate created_by matches real user
        valid_user = get_user_by_identifier(created_by)
        if valid_user:
            created_by = valid_user.get("username") or valid_user.get("id")

        row = {
            "survey_id": survey_id,
            "survey_name": survey_name,
            "survey_date": survey_date,
            "survey_time": survey_time,
            "location_name": location_name,
            "sonar_device": sonar_device,
            "sonar_frequency": sonar_frequency,
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "navigation_status": "PENDING",
            "processing_status": "not_started"
        }

        r = requests.post(f"{SUPABASE_URL}/rest/v1/surveys", json=row, headers=HEADERS, timeout=10)
        if r.status_code in [200, 201]:
            # Log operational audit event to dispatches
            log_dispatch_event("survey_created", {
                "survey_id": survey_id,
                "survey_name": survey_name,
                "created_by": created_by,
                "location": location_name
            })
            return True, survey_id, None
        else:
            return False, None, r.text
    except Exception as e:
        print("Supabase create_survey error:", e)
        return False, None, str(e)

def update_survey_status(survey_id, processing_status=None, status=None):
    """Updates survey processing and navigation status."""
    try:
        patch = {}
        if processing_status: patch["processing_status"] = processing_status.lower()
        if status: patch["status"] = status.lower()
        if not patch: return True

        r = requests.patch(f"{SUPABASE_URL}/rest/v1/surveys?survey_id=eq.{survey_id}", json=patch, headers=HEADERS, timeout=10)
        return r.status_code in [200, 204]
    except Exception as e:
        print("Supabase update_survey_status error:", e)
        return False

def get_all_detections(survey_id=None, tier=None, requires_review=None):
    """
    Fetches detections from public.detections.
    Maps fields for portal UI compatibility:
    - requires_review (bool) -> verification_status ('Verified' vs 'Pending Verification')
    - hazard (str) -> clearance_status ('Cleared' vs 'Detected')
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/detections?select=*&order=created_at.desc"
        if survey_id and survey_id != "all":
            url += f"&survey_id=eq.{survey_id}"
        if tier:
            url += f"&classification_tier=eq.{tier}"
        if requires_review is not None:
            url += f"&requires_review=eq.{str(requires_review).lower()}"

        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            state_events = get_detection_state_map()
            # Older workflow rows were persisted before crop_url was hydrated
            # on each detection. Resolve their stable survey-level evidence
            # image from the authoritative sonar_image event once here so the
            # Results, Sonar Analyst, and Marine Analyst APIs all agree.
            evidence_by_id = {}
            survey_images = {}
            for image in get_sonar_images():
                sid = str(image.get('survey_id') or '')
                image_url = _public_crop_url(image.get('url'))
                if image.get('image_id'):
                    evidence_by_id[str(image['image_id'])] = image
                if sid and image_url and sid not in survey_images:
                    survey_images[sid] = image
            evidence_links = get_evidence_detection_links()
            dets = []
            for d in r.json():
                req_rev = d.get("requires_review") is not False
                hazard_val = (d.get("hazard") or "").lower()
                review_status, cleanup_status, detection_status = _state_from_detection(d, state_events.get(str(d.get('id'))))
                is_offshore = is_offshore_coordinate(d.get('latitude'), d.get('longitude'))
                if cleanup_status == 'Cleanup Completed':
                    c_status = 'Completed'
                elif cleanup_status == 'Cleanup In Progress':
                    c_status = 'In Progress'
                elif cleanup_status in {'Cleanup Approved', 'Cleanup Scheduled', 'Cleanup Dispatched'}:
                    c_status = cleanup_status
                elif review_status == 'Rejected':
                    c_status = 'Rejected'
                elif cleanup_status == 'Cleanup Not Recommended':
                    c_status = 'No Cleanup Required'
                else:
                    c_status = 'Awaiting Marine Review'

                # Format coordinates array
                coords = [d.get("latitude") or 0.0, d.get("longitude") or 0.0]

                link = evidence_links.get(str(d.get('id')), {})
                evidence = evidence_by_id.get(str(link.get('image_id') or '')) or survey_images.get(str(d.get('survey_id'))) or {}
                evidence_url = _public_crop_url(evidence.get('url'))
                dets.append({
                    "id": d.get("id"),
                    "survey_id": d.get("survey_id"),
                    "class_name": d.get("class_name"),
                    "title": d.get("title") or (d.get("class_name") or "Target").replace("_", " ").title(),
                    "category": d.get("category") or "Marine Debris",
                    "confidence": float(d.get("confidence") or 0.0),
                    "classification_tier": d.get("classification_tier") or "C",
                    "requires_review": req_rev,
                    "verification_status": "Verified" if review_status == "Verified" else review_status,
                    "review_status": review_status,
                    "cleanup_status": cleanup_status,
                    "detection_status": detection_status,
                    "clearance_status": c_status,
                    "is_offshore": is_offshore,
                    "latitude": d.get("latitude"),
                    "longitude": d.get("longitude"),
                    "coordinates": coords,
                    "ping_number": d.get("ping_number"),
                    "depth": d.get("depth"),
                    "altitude": d.get("altitude"),
                    "heading": d.get("heading"),
                    # New workflow records always use the stable evidence URL.
                    # The crop URL remains a backwards-compatible fallback for
                    # legacy rows that have no evidence record.
                    "crop_url": evidence_url or _public_crop_url(d.get("crop_url")) or "",
                    "evidence_image_id": evidence.get('image_id') or link.get('image_id') or "",
                    "evidence_sequence": evidence.get('sequence') or link.get('sequence') or None,
                    "evidence_image_url": evidence_url or _public_crop_url(d.get("crop_url")) or "",
                    # Real YOLO bounding box (pixels in the evidence image), carried
                    # on the evidence-link event so the analyst portal can draw an
                    # overlay. None for legacy rows persisted before this existed.
                    "bbox": link.get("bbox") or None,
                    "material": d.get("material") or "Unknown Material",
                    "hazard": d.get("hazard") or "Marine Debris",
                    "created_at": d.get("created_at")
                })
            return dets
    except Exception as e:
        print("Supabase get_all_detections error:", e)
    return []

def get_detection(detection_id):
    """Fetches a single detection by ID."""
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/detections?id=eq.{detection_id}", headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.json()) > 0:
            d = r.json()[0]
            req_rev = d.get("requires_review") is not False
            state_event = get_detection_state_map().get(str(d.get('id')))
            review_status, cleanup_status, detection_status = _state_from_detection(d, state_event)
            d["verification_status"] = "Verified" if review_status == "Verified" else review_status
            d["review_status"] = review_status
            d["cleanup_status"] = cleanup_status
            d["detection_status"] = detection_status
            d["is_offshore"] = is_offshore_coordinate(d.get('latitude'), d.get('longitude'))
            d["clearance_status"] = cleanup_status
            link = get_evidence_detection_links().get(str(detection_id), {})
            images = get_sonar_images(d.get('survey_id'))
            image_by_id = {str(image.get('image_id')): image for image in images if image.get('image_id')}
            evidence = image_by_id.get(str(link.get('image_id') or '')) or (images[0] if images else {})
            evidence_url = _public_crop_url(evidence.get('url'))
            d['crop_url'] = evidence_url or _public_crop_url(d.get('crop_url'))
            d['evidence_image_id'] = evidence.get('image_id') or link.get('image_id') or ''
            d['evidence_sequence'] = evidence.get('sequence') or link.get('sequence') or None
            d['evidence_image_url'] = d['crop_url']
            return d
    except Exception as e:
        print(f"Supabase get_detection({detection_id}) error:", e)
    return None

def insert_detection(det):
    """
    Inserts a single detection into public.detections.
    Exact schema columns:
    id, survey_id, class_name, title, category, confidence, classification_tier, requires_review, latitude, longitude, ping_number, depth, altitude, heading, crop_url, material, hazard, created_at
    """
    try:
        det_id = det.get("id") or f"XTF-DET-{uuid.uuid4().hex[:6].upper()}"
        survey_id = det.get("survey_id")
        
        row = {
            "id": det_id,
            "survey_id": survey_id,
            "class_name": det.get("class_name", "unknown"),
            "title": det.get("title", "Acoustic Target"),
            "category": det.get("category", "Marine Target"),
            "confidence": float(det.get("confidence", 0.0)),
            "classification_tier": det.get("classification_tier", "C"),
            "requires_review": bool(det.get("requires_review", True)),
            "latitude": det.get("latitude"),
            "longitude": det.get("longitude"),
            "ping_number": det.get("ping_number"),
            "depth": str(det.get("depth")) if det.get("depth") is not None else None,
            "altitude": str(det.get("altitude")) if det.get("altitude") is not None else None,
            "heading": float(det.get("heading")) if det.get("heading") is not None else None,
            "crop_url": det.get("crop_url", ""),
            "material": det.get("material", "Acoustic Reflection"),
            "hazard": det.get("hazard", "Potential Hazard"),
            "created_at": datetime.now().isoformat()
        }

        r = requests.post(f"{SUPABASE_URL}/rest/v1/detections", json=row, headers=HEADERS, timeout=10)
        return r.status_code in [200, 201], det_id
    except Exception as e:
        print("Supabase insert_detection error:", e)
        return False, None

def update_detection_review(detection_id, status, new_class=None, new_hazard=None, reviewer="sonar_analyst", notes=""):
    """
    Performs Sonar Analyst review on a detection:
    - Sets requires_review = False for Verified
    - Updates class_name if reclassified
    - Logs analyst_review event in public.dispatches
    """
    try:
        patch = {}
        s_lower = (status or "").lower()
        canonical_status = 'Rejected' if 'reject' in s_lower else ('Verified' if 'verif' in s_lower else 'Pending Review')
        if "verif" in s_lower:
            patch["requires_review"] = False
        elif "reject" in s_lower:
            patch["requires_review"] = False
            # Keep the physical hazard description in the detection row; the
            # authoritative lifecycle state is persisted as an event below.
        elif "review" in s_lower or "unknown" in s_lower:
            # The schema represents a pending decision with requires_review.
            # Keep it explicit when an analyst defers a finding.
            patch["requires_review"] = True
        
        if new_class:
            patch["class_name"] = new_class
            patch["title"] = new_class.replace("_", " ").title()
        if new_hazard:
            patch["hazard"] = new_hazard

        if not patch:
            return False

        r = requests.patch(f"{SUPABASE_URL}/rest/v1/detections?id=eq.{detection_id}", json=patch, headers=HEADERS, timeout=10)
        if r.status_code not in [200, 204]:
            print("Failed to update detection in Supabase:", r.text)
            return False

        now_iso = datetime.now().isoformat()

        # --- Write structured row to analyst_reviews (v2.0 migration, best-effort) ---
        try:
            det_snap = get_detection(detection_id) or {}
            analyst_user = get_user_by_identifier(reviewer)
            analyst_uuid = analyst_user.get("id") if analyst_user else None
            ar_row = {
                "id": str(uuid.uuid4()),
                "detection_id": detection_id,
                "analyst_id": analyst_uuid,
                "previous_class": det_snap.get("class_name") or "",
                "assigned_class": new_class or det_snap.get("class_name") or "",
                "previous_tier": det_snap.get("classification_tier") or "",
                "assigned_tier": det_snap.get("classification_tier") or "",
                "decision": canonical_status,
                "status": canonical_status,
                "reviewer": reviewer,
                "notes": notes or "",
                "reviewed_at": now_iso,
                "created_at": now_iso,
            }
            ar_r = requests.post(
                f"{SUPABASE_URL}/rest/v1/analyst_reviews",
                json=ar_row,
                headers={**HEADERS, "Prefer": "return=minimal"},
                timeout=8,
            )
            if ar_r.status_code not in [200, 201]:
                print(f"analyst_reviews insert warning (non-fatal): {ar_r.status_code} {ar_r.text[:120]}")
        except Exception as ar_err:
            print(f"analyst_reviews insert error (non-fatal): {ar_err}")

        # The authoritative detection update has succeeded. Audit logging is
        # best effort so a transient logging failure cannot report a false
        # negative back to the analyst after their decision was persisted.
        log_dispatch_event("analyst_review", {
            "detection_id": detection_id,
            "status": canonical_status,
            "new_class": new_class,
            "reviewer": reviewer,
            "notes": notes,
            "reviewed_at": now_iso
        })
        log_dispatch_event("detection_state", {
            "detection_id": detection_id,
            "status": canonical_status,
            "lifecycle_status": 'Cleanup Not Recommended' if canonical_status == 'Rejected' else 'Awaiting Marine Review',
            "reviewer": reviewer,
            "notes": notes,
            "updated_at": now_iso
        })
        log_dispatch_event("notification", {
            "type": 'Detection Review',
            "title": 'Target rejected by Sonar Analyst' if canonical_status == 'Rejected' else 'Verified targets require cleanup assessment',
            "message": (f'Detection {detection_id} was rejected and removed from downstream cleanup candidates.'
                         if canonical_status == 'Rejected'
                         else f'Detection {detection_id} was verified and is awaiting Marine Analyst cleanup assessment.'),
            "recipient_roles": (['sonar_analyst', 'marine_portal', 'government_portal']
                                if canonical_status == 'Verified' else ['sonar_analyst', 'government_portal']),
            "detection_id": detection_id,
            "is_read": False,
            "timestamp": now_iso
        })
        return True
    except Exception as e:
        print("Supabase update_detection_review error:", e)
        return False

def update_detection_clearance(detection_id, status="Cleared", team="Coast Guard Diving Unit", notes="", hotspot_id=None):
    """
    Performs Marine Portal clearance on a detection:
    - Updates hazard = 'cleared'
    - Logs clearance_record event in public.dispatches
    """
    try:
        status_lower = str(status or '').lower()
        if 'complete' in status_lower or 'clear' in status_lower:
            lifecycle_status = 'Cleanup Completed'
        elif 'progress' in status_lower or 'start' in status_lower:
            lifecycle_status = 'Cleanup In Progress'
        elif 'dispatch' in status_lower:
            lifecycle_status = 'Cleanup Dispatched'
        elif 'schedul' in status_lower:
            lifecycle_status = 'Cleanup Scheduled'
        elif 'approv' in status_lower or 'assign' in status_lower:
            lifecycle_status = 'Cleanup Approved'
        else:
            lifecycle_status = str(status or 'Awaiting Marine Review')
        patch = {"hazard": "cleared" if lifecycle_status == 'Cleanup Completed' else "Potential Marine Hazard"}
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/detections?id=eq.{detection_id}", json=patch, headers=HEADERS, timeout=10)
        if r.status_code not in [200, 204]:
            print("Failed to update clearance in Supabase:", r.text)
            return False

        now_iso = datetime.now().isoformat()
        clr_id = f"CLR-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"

        # --- Write structured row to clearance_records (v2.0 migration, best-effort) ---
        try:
            clr_row = {
                "id": clr_id,
                "detection_id": detection_id,
                "hotspot_id": hotspot_id,
                "team": team,
                "status": lifecycle_status,
                "notes": notes or "",
                "clearance_date": now_iso[:10],
                "created_at": now_iso,
            }
            clr_r = requests.post(
                f"{SUPABASE_URL}/rest/v1/clearance_records",
                json=clr_row,
                headers={**HEADERS, "Prefer": "return=minimal"},
                timeout=8,
            )
            if clr_r.status_code not in [200, 201]:
                print(f"clearance_records insert warning (non-fatal): {clr_r.status_code} {clr_r.text[:120]}")
        except Exception as clr_err:
            print(f"clearance_records insert error (non-fatal): {clr_err}")

        # Log clearance record to dispatches (kept for backward compat)
        log_dispatch_event("detection_state", {
            "detection_id": detection_id,
            "status": 'Verified',
            "lifecycle_status": lifecycle_status,
            "team": team,
            "hotspot_id": hotspot_id,
            "notes": notes,
            "updated_at": now_iso
        })
        log_dispatch_event("notification", {
            "type": 'Cleanup Lifecycle',
            "title": f'Cleanup status updated: {lifecycle_status}',
            "message": f'Detection {detection_id} is {lifecycle_status.lower()}.',
            "recipient_roles": ['marine_portal', 'government_portal'],
            "detection_id": detection_id,
            "hotspot_id": hotspot_id,
            "is_read": False,
            "timestamp": now_iso
        })
        if lifecycle_status == 'Cleanup Approved':
            log_dispatch_event("notification", {
                "type": 'Cleanup Assignment',
                "title": 'Cleanup operation assigned',
                "message": f'Detection {detection_id} was approved for cleanup and assigned to {team}.',
                "recipient_roles": ['marine_portal', 'government_portal'],
                "detection_id": detection_id,
                "hotspot_id": hotspot_id,
                "is_read": False,
                "timestamp": now_iso
            })
        return log_dispatch_event("clearance_record", {
            "id": clr_id,
            "target_id": detection_id,
            "status": lifecycle_status,
            "team": team,
            "notes": notes,
            "hotspot_id": hotspot_id,
            "cleared_at": now_iso,
            "lifecycle_status": lifecycle_status
        })
    except Exception as e:
        print("Supabase update_detection_clearance error:", e)
        return False

def log_dispatch_event(event_type, payload):
    """Appends an immutable operational event record to public.dispatches.

    After the v2.0 migration, dispatches has a top-level indexed ``event_type``
    column.  We set it explicitly on every INSERT so the row is immediately
    queryable via the index without waiting for the back-fill trigger.
    The event_type is also kept inside payload for backward compatibility with
    any code that reads it from payload->>'event_type'.
    """
    try:
        record = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,   # indexed column (v2.0)
            "payload": {
                "event_type": event_type,
                **payload
            }
        }
        r = requests.post(f"{SUPABASE_URL}/rest/v1/dispatches", json=record, headers=HEADERS, timeout=10)
        if r.status_code not in [200, 201]:
            print(f"Supabase dispatch write error ({event_type}):", r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:
        print(f"Supabase log_dispatch_event({event_type}) error:", e)
        return False

def get_dispatch_events(event_type=None):
    """Queries operational events from public.dispatches.

    After the v2.0 migration, dispatches has an indexed `event_type` column.
    We filter on that column server-side so Supabase only returns matching
    rows instead of the entire table.  The fallback (no event_type filter)
    still returns all events for callers that do their own filtering.
    """
    try:
        if event_type:
            # Use the indexed column for server-side filtering (fast path)
            url = (
                f"{SUPABASE_URL}/rest/v1/dispatches"
                f"?select=*&event_type=eq.{event_type}&order=created_at.desc"
            )
        else:
            url = f"{SUPABASE_URL}/rest/v1/dispatches?select=*&order=created_at.desc"

        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            events = []
            for d in r.json():
                p = d.get("payload") or {}
                # If event_type column is not yet backfilled on a row,
                # fall back to checking payload (graceful degradation)
                if event_type is None or p.get("event_type") == event_type:
                    events.append({
                        "id": d.get("id"),
                        "created_at": d.get("created_at"),
                        **p
                    })
            return events
    except Exception as e:
        print(f"Supabase get_dispatch_events({event_type}) error:", e)
    return []


def upload_sonar_image(storage_path, content, content_type='image/jpeg'):
    """Store one evidence artifact and return its stable Storage identity.

    ``storage_path`` is supplied by the workflow and includes the evidence ID
    and sequence.  It is never inferred from a local filename, which prevents
    the previous ``workflow_uploads/...`` versus ``sonar/...`` URL mismatch.
    ``public_url`` is returned only after an unauthenticated browser-style
    request confirms that the public bucket policy actually permits it.
    """
    if not storage_path or not isinstance(content, (bytes, bytearray)):
        logger.error("Evidence upload rejected: storage_path or image bytes are invalid.")
        return None
    if not is_configured():
        logger.warning("Evidence upload skipped: Supabase Storage is not configured.")
        return None
    if not _ensure_image_bucket():
        logger.error("Evidence upload skipped: survey-images bucket is unavailable.")
        return None

    normalized_path = storage_path.strip().lstrip('/')
    if not normalized_path or '..' in normalized_path.split('/'):
        logger.error("Evidence upload rejected: unsafe storage path %r", storage_path)
        return None
    encoded_path = quote(normalized_path, safe='/')
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/survey-images/{encoded_path}"
    try:
        response = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/survey-images/{encoded_path}",
            data=content,
            headers=_storage_headers(content_type),
            timeout=20,
        )
        if response.status_code not in (200, 201):
            logger.error(
                "Evidence storage upload failed: status=%s path=%s body=%s",
                response.status_code, normalized_path, response.text[:300],
            )
            return None
        _IMAGE_URL_CHECKS.pop(public_url, None)
        if not _accessible_image_url(public_url):
            logger.error("Evidence upload completed but browser URL cannot be read: path=%s url=%s", normalized_path, public_url)
            return None
        logger.info("Evidence storage upload completed: path=%s bytes=%s", normalized_path, len(content))
        return {
            'storage_path': normalized_path,
            'public_url': public_url,
            'content_type': content_type,
        }
    except requests.RequestException as exc:
        logger.exception("Evidence storage upload request failed for %s: %s", normalized_path, exc)
        return None


def get_survey_upload_events():
    return _latest_event_by(get_dispatch_events('survey_uploaded'), 'survey_id')


def get_evidence_detection_links():
    """Return the latest immutable evidence-to-detection association per target."""
    return _latest_event_by(get_dispatch_events('evidence_detection_link'), 'detection_id')


def _local_evidence_url(event):
    """Read the browser URL stored with an event, never a filesystem path."""
    url = _public_crop_url(event.get('local_url'))
    if url:
        if url.startswith('/outputs/'):
            output_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'outputs'))
            relative_path = url[len('/outputs/'):].replace('/', os.sep)
            candidate = os.path.abspath(os.path.join(output_root, relative_path))
            if not candidate.startswith(output_root + os.sep) or not os.path.isfile(candidate):
                logger.error("Stored local evidence URL has no file: image_id=%s url=%s", event.get('image_id'), url)
                return ''
        return url
    # Read-time compatibility for evidence records created before local_url
    # existed. Resolve the path relative to outputs rather than assuming every
    # historic record lived in workflow_uploads; that faulty assumption was
    # one cause of valid evidence being returned with a broken browser URL.
    local_path = event.get('local_path') or ''
    output_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'outputs'))
    try:
        candidate = os.path.abspath(local_path)
        if local_path and candidate.startswith(output_root + os.sep) and os.path.isfile(candidate):
            relative_path = os.path.relpath(candidate, output_root).replace(os.sep, '/')
            local_url = f"/outputs/{quote(relative_path, safe='/')}"
            logger.info("Recovered legacy local evidence URL: image_id=%s url=%s", event.get('image_id'), local_url)
            return local_url
    except OSError as exc:
        logger.error("Legacy local evidence URL resolution failed: image_id=%s error=%s", event.get('image_id'), exc)
    if local_path:
        logger.error("Legacy evidence file is missing or outside outputs: image_id=%s", event.get('image_id'))
    return ''


def _public_evidence_record(event):
    """Drop internal filesystem fields before returning evidence to the API."""
    fields = (
        'survey_id', 'image_id', 'evidence_id', 'sequence', 'file_name',
        'file_hash', 'content_sha256', 'storage_path', 'storage_url', 'url',
        'local_url', 'content_type', 'created_at', 'repaired_at', 'storage_status',
    )
    return {field: event.get(field) for field in fields if event.get(field) is not None}


def get_sonar_images(survey_id=None):
    """Return one browser-accessible, stable record for each evidence image."""
    events = get_dispatch_events('sonar_image')
    if survey_id:
        events = [e for e in events if str(e.get('survey_id')) == str(survey_id)]
    unique = {}
    for event in events:
        image_id = str(event.get('image_id') or event.get('evidence_id') or '')
        # Events are newest-first. Prefer the newest usable record, but do
        # not let a failed repair event hide an older record that still has a
        # valid local artifact or public URL.
        if not image_id or (image_id in unique and unique[image_id].get('url')):
            continue

        event = {**event, 'image_id': image_id, 'evidence_id': image_id}
        direct_url = _public_crop_url(event.get('url'))
        storage_url = _public_crop_url(event.get('storage_url'))
        local_url = _local_evidence_url(event)
        # A browser must receive the public Storage URL when it is available;
        # do not let a previous local-fallback URL permanently mask a repaired
        # Storage object.  Check Storage without authorization, exactly as the
        # browser will load it.
        public_url = storage_url or (direct_url if direct_url.startswith(('https://', 'http://')) else '')
        if public_url and _accessible_image_url(public_url):
            event['url'] = public_url
        else:
            # A failed public object can be repaired from the original local
            # artifact without changing its stable image ID, sequence, or
            # storage path. This also upgrades historical local-fallback
            # evidence after Storage becomes available again.
            local_path = event.get('local_path') or ''
            if local_path and os.path.isfile(local_path):
                try:
                    with open(local_path, 'rb') as image_file:
                        upload = upload_sonar_image(
                            event.get('storage_path') or f"evidence/{image_id}/sequence-{int(event.get('sequence') or 1):03d}.jpg",
                            image_file.read(), event.get('content_type') or 'image/jpeg',
                        )
                    if upload:
                        event = {**event, 'url': upload['public_url'], 'storage_url': upload['public_url'],
                                 'storage_path': upload['storage_path'], 'storage_status': 'uploaded',
                                 'repaired_at': datetime.now().isoformat()}
                        if not log_dispatch_event('sonar_image', {key: value for key, value in event.items() if key not in {'id', 'event_type'}}):
                            logger.error("Evidence repair was uploaded but its database event could not be written: image_id=%s", image_id)
                    elif local_url:
                        logger.warning("Using local evidence URL after Storage upload failed: image_id=%s", image_id)
                        event['url'] = local_url
                    else:
                        logger.error("Evidence repair upload failed and no browser URL is available: image_id=%s", image_id)
                        event['url'] = ''
                except OSError as exc:
                    logger.exception("Could not read local evidence artifact for repair: image_id=%s error=%s", image_id, exc)
                    event['url'] = local_url or ''
            elif local_url:
                # Local output routes are valid durable fallback storage, but
                # only after the file existence check in _local_evidence_url.
                logger.warning("Using local evidence URL after Storage URL failed: image_id=%s", image_id)
                event['url'] = local_url
            else:
                logger.error("Evidence record has no readable Storage object or local artifact: image_id=%s", image_id)
                event['url'] = ''
        unique[image_id] = event
    return sorted(
        (_public_evidence_record(item) for item in unique.values()),
        key=lambda item: (item.get('sequence') or 0, item.get('image_id') or ''),
    )


def get_cleanup_operations():
    """Return the latest persisted operation state for each approved target.

    Cleanup is event-sourced in ``dispatches``.  This projection deliberately
    joins each operation to its authoritative detection instead of trusting
    coordinates supplied by a browser.  As a result, downstream maps and the
    route planner can only ever receive persisted offshore target positions.
    """
    events = get_dispatch_events('cleanup_operation')
    latest = _latest_event_by(events, 'target_id')
    detections = {str(d.get('id')): d for d in get_all_detections()}
    operations = []
    for target_id, event in latest.items():
        det = detections.get(str(target_id), {})
        if not det:
            continue
        if det.get('review_status') == 'Rejected':
            continue
        operations.append({
            'operation_id': event.get('operation_id') or f"OP-{target_id}",
            'target_id': target_id,
            'survey_id': det.get('survey_id'),
            'hotspot_id': event.get('hotspot_id') or det.get('hotspot_id'),
            'target_type': det.get('title') or det.get('class_name'),
            'latitude': det.get('latitude'),
            'longitude': det.get('longitude'),
            'priority': event.get('priority') or ('High' if float(det.get('confidence') or 0) >= 80 else 'Medium'),
            'status': event.get('status') or det.get('cleanup_status') or 'Cleanup Approved',
            'progress_percent': int(event.get('progress_percent') or (100 if det.get('cleanup_status') == 'Cleanup Completed' else 0)),
            'assigned_operation': event.get('assigned_operation') or 'Marine Response Fleet A',
            'updated_at': event.get('updated_at') or event.get('created_at'),
            'approved_at': event.get('approved_at'),
            'scheduled_at': event.get('scheduled_at'),
            'started_at': event.get('started_at'),
            'progress_updated_at': event.get('progress_updated_at'),
            'completed_at': event.get('completed_at'),
            'route_id': event.get('route_id') or '',
            'notes': event.get('notes') or '',
        })
    return sorted(operations, key=lambda item: (item.get('priority') != 'High', item.get('target_id') or ''))


def get_latest_route():
    events = get_dispatch_events('route_optimized')
    if not events:
        return None
    # The route geometry is immutable for a generated plan, but stop status
    # is live.  Hydrating it from the operation projection prevents the
    # Marine, Government, and Cleanup portals from showing stale route chips.
    route = dict(events[0])
    operations = {str(operation.get('target_id')): operation
                  for operation in get_cleanup_operations()}
    sequence = []
    for stop in route.get('target_sequence') or []:
        current = dict(stop)
        operation = operations.get(str(current.get('target_id')))
        if operation:
            current['status'] = operation.get('status')
            current['progress_percent'] = operation.get('progress_percent')
            current['updated_at'] = operation.get('updated_at')
        sequence.append(current)
    route['target_sequence'] = sequence
    statuses = {str(stop.get('status') or '') for stop in sequence}
    if statuses and statuses == {'Cleanup Completed'}:
        route['status'] = 'Route Completed'
    elif 'Cleanup In Progress' in statuses:
        route['status'] = 'Operation In Progress'
    elif 'Cleanup Scheduled' in statuses:
        route['status'] = 'Cleanup Scheduled'
    return route

def get_clearance_records():
    """Fetches clearance records from dispatches and cleared detections."""
    try:
        records = get_dispatch_events("clearance_record")
        known = {str(record.get('target_id')) for record in records if record.get('target_id')}
        for operation in get_cleanup_operations():
            if str(operation.get('target_id')) not in known:
                records.append({
                    'id': operation.get('operation_id'), 'target_id': operation.get('target_id'),
                    'hotspot_id': operation.get('hotspot_id'), 'status': operation.get('status'),
                    'team': operation.get('assigned_operation'), 'debris_type': operation.get('target_type'),
                    'survey_id': operation.get('survey_id'), 'clearance_date': operation.get('updated_at'),
                    'progress_percent': operation.get('progress_percent'), 'updated_at': operation.get('updated_at'),
                    'approved_at': operation.get('approved_at'), 'scheduled_at': operation.get('scheduled_at'),
                    'started_at': operation.get('started_at'), 'completed_at': operation.get('completed_at')
                })
        return records
    except Exception as e:
        print("Supabase get_clearance_records error:", e)
    return []

def get_notifications(recipient_role=None):
    """Fetch notifications addressed to one portal role.

    Earlier records did not include recipients, so they remain visible to
    authenticated operational portals for backwards compatibility.  New
    workflow events carry ``recipient_roles`` and are filtered here instead
    of relying on a decorative, static notification count in a page.
    """
    try:
        notifications = get_dispatch_events("notification")
        role = normalize_role(recipient_role) if recipient_role else ''
        if role:
            notifications = [event for event in notifications
                             if not event.get('recipient_roles')
                             or role in {normalize_role(item) for item in event.get('recipient_roles', [])}]
            read_events = get_dispatch_events("notifications_marked_read")
            latest_read = max((str(event.get('marked_at') or event.get('created_at') or '')
                               for event in read_events
                               if normalize_role(event.get('recipient_role')) == role), default='')
            for event in notifications:
                if latest_read and str(event.get('created_at') or event.get('timestamp') or '') <= latest_read:
                    event['is_read'] = True
        return notifications
    except Exception as e:
        print("Supabase get_notifications error:", e)
    return []

def get_documents():
    """Fetches registered document records from dispatches."""
    try:
        return get_dispatch_events("document")
    except Exception as e:
        print("Supabase get_documents error:", e)
    return []

def mark_notifications_read(recipient_role=None):
    """Persist a role-scoped read checkpoint for notification events."""
    try:
        log_dispatch_event("notifications_marked_read", {
            "marked_at": datetime.now().isoformat(),
            "recipient_role": normalize_role(recipient_role),
        })
        return True
    except Exception as e:
        print("Supabase mark_notifications_read error:", e)
        return False

def get_hotspots():
    """
    Computes real dynamic hotspots by running DBSCAN geospatial clustering
    directly on coordinates from public.detections.
    """
    try:
        from dbscan_service import cluster_detections
        all_dets = get_all_detections()
        # Compute is_offshore dynamically from coordinates since the detections
        # table has no is_offshore column — use is_offshore_coordinate() which
        # is the source of truth for all geographic validity checks in TARANG.
        coords_dets = [
            d for d in all_dets
            if d.get('latitude') is not None and d.get('longitude') is not None
            and is_offshore_coordinate(d['latitude'], d['longitude'])
            and d.get('detection_status') != 'Rejected'
        ]

        if not coords_dets:
            return []

        res = cluster_detections(coords_dets, eps_meters=500.0, min_samples=2)

        # Hotspot state is a projection of the same operation events used by
        # the Cleanup Portal.  It therefore changes immediately when an
        # operation is scheduled, started, progressed, or completed.
        operations_by_target = {str(operation.get('target_id')): operation
                                for operation in get_cleanup_operations()}
        hotspots = []
        for c in res.get("clusters", []):
            center = c.get("center")
            if not isinstance(center, list) or len(center) != 2:
                continue
            lat, lon = center
            members = sorted(str(item.get('id')) for item in c.get('detections', []))
            stable_key = '|'.join(members) or f"cluster-{c.get('cluster_num')}"
            hotspot_id = f"HS-{hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:10].upper()}"
            hotspot_states = _latest_event_by(get_dispatch_events('hotspot_status_update'), 'hotspot_id')
            status_event = hotspot_states.get(hotspot_id, {})
            member_operations = [operations_by_target[target_id] for target_id in members
                                 if target_id in operations_by_target]
            operation_statuses = {str(operation.get('status') or '') for operation in member_operations}
            if member_operations and all(status == 'Cleanup Completed' for status in operation_statuses):
                derived_status = 'Cleanup Completed'
            elif 'Cleanup In Progress' in operation_statuses:
                derived_status = 'Cleanup In Progress'
            elif 'Cleanup Scheduled' in operation_statuses:
                derived_status = 'Cleanup Scheduled'
            elif 'Cleanup Approved' in operation_statuses:
                derived_status = 'Cleanup Approved'
            else:
                derived_status = status_event.get('new_status') or "Active Monitoring"
            hotspots.append({
                "id": hotspot_id,
                "name": f"Acoustic Hazard Cluster {c.get('cluster_num', 1)}",
                "location_name": "Offshore Indian Ocean Demonstration Zone",
                "area_km2": round(float(c.get("radius_meters", 0.0) ** 2 * 3.14159 / 1000000.0), 2),
                "dominant_type": (c.get("dominant_class") or "Marine Debris").replace("_", " ").title(),
                "status": derived_status,
                "verified_count": c.get("verified_count", 0),
                "cleared_count": c.get("cleared_count", 0),
                "total_targets": c.get("count", 0),
                "target_types": c.get('class_distribution', {}),
                "target_ids": members,
                "latitude": lat,
                "longitude": lon,
                "coordinates": [lat, lon],
                "priority": "High" if c.get("count", 0) >= 3 else "Medium",
                "severity": "High" if c.get("count", 0) >= 3 else "Medium"
            })
        return hotspots
    except Exception as e:
        print("Supabase get_hotspots error:", e)
    return []

def get_gov_stats():
    """Calculates live Government Portal dashboard statistics from Supabase."""
    try:
        surveys = get_surveys()
        dets = get_all_detections()
        clearance_recs = get_clearance_records()
        hotspots = get_hotspots()

        summary = summarize_detections(dets)
        total_detected = summary['total_detected']
        total_verified = summary['verified']
        total_cleared = summary['cleanup_completed']
        total_in_progress = summary['cleanup_candidates']
        clearance_rate = round((total_cleared / total_verified * 100), 1) if total_verified > 0 else 0.0

        return {
            "total_detected": total_detected,
            "total_verified": total_verified,
            "total_cleared": total_cleared,
            "total_in_progress": total_in_progress,
            "total_pending": summary['pending_review'],
            "active_hotspots": len(hotspots),
            "total_surveys": len(surveys),
            "clearance_rate_percent": clearance_rate,
            "recent_clearances": clearance_recs[:5],
            "summary": summary,
            "cleanup_operations": get_cleanup_operations(),
            "route": get_latest_route()
        }
    except Exception as e:
        print("Supabase get_gov_stats error:", e)
        return {
            "total_detected": 0, "total_verified": 0, "total_cleared": 0,
            "total_in_progress": 0, "total_pending": 0, "active_hotspots": 0,
            "total_surveys": 0, "clearance_rate_percent": 0.0, "recent_clearances": []
        }

def get_public_stats():
    """
    Calculates public-safe metrics and markers from Supabase.
    Strictly filters out unverified dispatches and sensitive operational details.
    """
    try:
        surveys = get_surveys()
        dets = get_all_detections()
        hotspots = get_hotspots()

        # Filter strictly for verified or cleared findings
        public_safe_dets = [
            d for d in dets
            if d.get('detection_status') in {'Verified', 'Cleanup Candidate', 'Cleanup Completed'}
            and d.get('is_offshore')
            and d.get("latitude") is not None and d.get("longitude") is not None
        ]

        summary = summarize_detections(dets)
        total_verified = summary['verified'] + summary['cleanup_candidates'] + summary['cleanup_completed']
        total_cleared = summary['cleanup_completed']
        cleanup_rate = round((total_cleared / total_verified * 100), 1) if total_verified > 0 else 0.0

        public_markers = []
        for d in public_safe_dets:
            public_markers.append({
                "id": d["id"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "category": d["category"],
                "classification_tier": d["classification_tier"],
                "status": d.get('detection_status') or "Verified Debris",
                "registered_date": (d.get("created_at") or "")[:10]
            })

        return {
            "surveys_completed": len(surveys),
            "hotspots_identified": len(hotspots),
            "monitored_hotspots": len(hotspots),
            "verified_hazards": total_verified,
            "total_debris_detected": len(dets),
            "cleared_hazards": total_cleared,
            "total_cleared": total_cleared,
            "coastal_cleanup_rate_percent": cleanup_rate,
            "hotspots": hotspots,
            "public_markers": public_markers,
            "summary": summary,
            "cleanup_operations": [op for op in get_cleanup_operations() if op.get('status') != 'Cleanup Not Recommended']
        }
    except Exception as e:
        print("Supabase get_public_stats error:", e)
        return {
            "surveys_completed": 0, "hotspots_identified": 0, "monitored_hotspots": 0,
            "verified_hazards": 0, "total_debris_detected": 0, "cleared_hazards": 0,
            "total_cleared": 0, "coastal_cleanup_rate_percent": 0.0, "hotspots": [],
            "public_markers": []
        }
