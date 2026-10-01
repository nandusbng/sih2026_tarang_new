"""Verify TARANG's persisted, browser-safe sonar evidence workflow.

The default run uses the configured Supabase project. ``--offline`` runs the
same Flask upload/API flow with an in-memory database and Storage equivalent;
it is useful when this workstation is offline. Both modes use an existing
reconstructed XTF JPEG as the actual input image, never a placeholder image.
"""

import argparse
import glob
import io
import json
from contextlib import ExitStack
from unittest.mock import patch

from app import app, demo_serializer
import supabase_service as sb_svc


class OfflineEvidenceStore:
    """Minimal faithful test double for TARANG's evidence persistence API."""

    def __init__(self):
        self.surveys = {}
        self.detections = {}
        self.events = []

    def create_survey(self, data):
        survey_id = data['survey_id']
        if survey_id in self.surveys:
            return False, None, 'Survey already exists.'
        self.surveys[survey_id] = {**data, 'status': 'active', 'processing_status': 'not_started'}
        return True, survey_id, None

    def get_survey(self, survey_id):
        return self.surveys.get(survey_id)

    def get_surveys(self):
        return list(self.surveys.values())

    def update_survey_status(self, survey_id, processing_status=None, status=None):
        survey = self.surveys.get(survey_id)
        if not survey:
            return False
        if processing_status:
            survey['processing_status'] = processing_status
        if status:
            survey['status'] = status
        return True

    def log_dispatch_event(self, event_type, payload):
        self.events.insert(0, {'event_type': event_type, **payload})
        return True

    def _events(self, event_type):
        return [event for event in self.events if event.get('event_type') == event_type]

    def get_survey_upload_events(self):
        latest = {}
        for event in self._events('survey_uploaded'):
            latest.setdefault(str(event.get('survey_id')), event)
        return latest

    def get_evidence_detection_links(self):
        latest = {}
        for event in self._events('evidence_detection_link'):
            latest.setdefault(str(event.get('detection_id')), event)
        return latest

    def get_sonar_images(self, survey_id=None):
        images = {}
        for event in self._events('sonar_image'):
            if survey_id and str(event.get('survey_id')) != str(survey_id):
                continue
            image_id = event.get('image_id')
            if image_id and image_id not in images:
                images[image_id] = {
                    key: value for key, value in event.items()
                    if key not in {'event_type', 'local_path'}
                }
        return sorted(images.values(), key=lambda image: (image.get('sequence') or 0, image.get('image_id') or ''))

    def upload_sonar_image(self, storage_path, content, content_type):
        # Exercise TARANG's persistent local HTTP fallback in an offline test.
        return None

    def get_all_detections(self, survey_id=None, tier=None, requires_review=None):
        records = list(self.detections.values())
        if survey_id:
            records = [record for record in records if record.get('survey_id') == survey_id]
        if tier:
            records = [record for record in records if record.get('classification_tier') == tier]
        links = self.get_evidence_detection_links()
        images = {
            image.get('image_id'): image
            for image in self.get_sonar_images()
            if image.get('image_id')
        }
        hydrated = []
        for record in records:
            evidence = images.get((links.get(str(record.get('id'))) or {}).get('image_id')) or {}
            hydrated.append({
                **record,
                'evidence_image_id': evidence.get('image_id', ''),
                'evidence_sequence': evidence.get('sequence'),
                'evidence_image_url': evidence.get('url', record.get('crop_url', '')),
            })
        return hydrated

    def insert_detection(self, record):
        self.detections[record['id']] = dict(record)
        return True, record['id']

    def get_hotspots(self):
        return []

    def summarize_detections(self, detections):
        return {
            'total_detected': len(detections), 'verified': 0, 'rejected': 0,
            'pending_review': len(detections), 'cleanup_candidates': 0,
        }

    def get_cleanup_operations(self):
        return []

    def get_latest_route(self):
        return None

    def get_notifications(self):
        return []


def offline_patches(store):
    return {
        'create_survey': store.create_survey,
        'get_survey': store.get_survey,
        'get_surveys': store.get_surveys,
        'update_survey_status': store.update_survey_status,
        'log_dispatch_event': store.log_dispatch_event,
        'get_survey_upload_events': store.get_survey_upload_events,
        'get_evidence_detection_links': store.get_evidence_detection_links,
        'get_sonar_images': store.get_sonar_images,
        'upload_sonar_image': store.upload_sonar_image,
        'get_all_detections': store.get_all_detections,
        'insert_detection': store.insert_detection,
        'get_hotspots': store.get_hotspots,
        'summarize_detections': store.summarize_detections,
        'get_cleanup_operations': store.get_cleanup_operations,
        'get_latest_route': store.get_latest_route,
        'get_notifications': store.get_notifications,
    }


def verify(offline=False):
    paths = glob.glob('outputs/xtf_*.jpg')
    if not paths:
        raise RuntimeError('No reconstructed sonar JPEG is available for the integration verification.')

    with open(paths[0], 'rb') as source:
        source_bytes = source.read()

    token = demo_serializer.dumps({'demo': True, 'portal': 'survey_operator'})
    headers = {'Authorization': f'Bearer {token}'}
    with ExitStack() as stack:
        if offline:
            stack.enter_context(patch.multiple(sb_svc, **offline_patches(OfflineEvidenceStore())))

        client = app.test_client()
        upload = client.post(
            '/api/v1/surveys/upload',
            data={
                'file': (io.BytesIO(source_bytes), 'actual_reconstructed_sonar.jpg'),
                'survey_name': 'Evidence URL Verification',
            },
            headers=headers,
            content_type='multipart/form-data',
        )
        payload = upload.get_json() or {}
        assert upload.status_code in (200, 201), payload

        survey_id = payload['survey_id']
        images_response = client.get(f'/api/v1/surveys/{survey_id}/images', headers=headers)
        images = images_response.get_json() or []
        assert images_response.status_code == 200 and len(images) == 1, images
        image = images[0]
        image_url = image.get('url') or ''
        assert image.get('image_id') and image.get('sequence') == 1, image
        assert image_url.startswith(('/', 'https://', 'http://')), image
        assert not (len(image_url) > 2 and image_url[1] == ':'), image_url

        # A local fallback must be exposed by Flask and be an actual image,
        # never a filesystem path or a fabricated browser placeholder.
        if image_url.startswith('/'):
            served_image = client.get(image_url)
            assert served_image.status_code == 200, served_image.get_data(as_text=True)
            assert served_image.content_type.startswith('image/'), served_image.content_type

        detections_response = client.get(f'/api/v1/surveys/{survey_id}/detections', headers=headers)
        detections = detections_response.get_json() or []
        assert detections_response.status_code == 200 and detections, detections
        assert all(
            detection.get('evidence_image_id') == image['image_id']
            and detection.get('evidence_image_url') == image_url
            for detection in detections
        ), detections

        # The Results renderer groups strictly by evidence ID and no longer
        # falls back to a survey's first image, so a multi-image survey cannot
        # be shown as duplicate/wrong evidence cards.
        with open('operator-portal.html', encoding='utf-8') as results_page:
            results_source = results_page.read()
        assert 'const groups = new Map(); // evidence_image_id -> [detections]' in results_source
        assert 'const defaultImage = (images || [])[0];' not in results_source

    print(json.dumps({
        'mode': 'offline-local-fallback' if offline else 'supabase',
        'input': paths[0],
        'survey_id': survey_id,
        'evidence_image_id': image['image_id'],
        'sequence': image['sequence'],
        'image_url': image_url,
        'detections_linked': len(detections),
        'storage_path': image.get('storage_path'),
        'results_renderer_uses_evidence_id': True,
    }, indent=2))


def verify_xtf_offline():
    """Exercise actual XTF reconstruction, persistent evidence, and links."""
    paths = glob.glob('*.xtf')
    if not paths:
        raise RuntimeError('No XTF source file is available for the XTF evidence verification.')

    token = demo_serializer.dumps({'demo': True, 'portal': 'survey_operator'})
    headers = {'Authorization': f'Bearer {token}'}
    store = OfflineEvidenceStore()
    with patch.multiple(sb_svc, **offline_patches(store)):
        client = app.test_client()
        with open(paths[0], 'rb') as source:
            source_bytes = source.read()
            upload = client.post(
                '/api/v1/xtf/upload',
                data={'file': (io.BytesIO(source_bytes), 'actual_side_scan_survey.xtf')},
                headers=headers,
                content_type='multipart/form-data',
            )
        payload = upload.get_json() or {}
        assert upload.status_code == 200, payload
        survey_id = payload['survey_id']
        images = payload.get('images') or []
        assert images and all(image.get('image_id') and image.get('sequence') and image.get('url', '').startswith('/') for image in images), images
        assert all('path' not in image for image in images), images

        images_response = client.get(f'/api/v1/surveys/{survey_id}/images', headers=headers)
        api_images = images_response.get_json() or []
        assert images_response.status_code == 200 and {image['image_id'] for image in api_images} == {image['image_id'] for image in images}

        detections_response = client.get(f'/api/v1/surveys/{survey_id}/detections', headers=headers)
        detections = detections_response.get_json() or []
        image_ids = {image['image_id'] for image in api_images}
        assert all(detection.get('evidence_image_id') in image_ids and detection.get('evidence_image_url', '').startswith('/') for detection in detections), detections

        # The legacy XTF image endpoint now resolves to the durable evidence
        # URL instead of serving a path that only existed in the process cache.
        redirected = client.get(f"/api/v1/xtf/{survey_id}/images/{api_images[0]['image_id']}", headers=headers)
        assert redirected.status_code in (301, 302, 307, 308), redirected.status_code
        served_image = client.get(redirected.headers['Location'])
        assert served_image.status_code == 200 and served_image.content_type.startswith('image/'), served_image.content_type

        # Retrying the exact source must reuse every evidence ID/object rather
        # than create a second image per detection or per upload attempt.
        evidence_events_before = len(store._events('sonar_image'))
        retry = client.post(
            '/api/v1/xtf/upload',
            data={'file': (io.BytesIO(source_bytes), 'actual_side_scan_survey.xtf')},
            headers=headers,
            content_type='multipart/form-data',
        )
        retry_payload = retry.get_json() or {}
        assert retry.status_code == 200 and retry_payload.get('existing') is True, retry_payload
        assert len(store._events('sonar_image')) == evidence_events_before
        assert {image['image_id'] for image in retry_payload.get('images', [])} == image_ids

    print(json.dumps({
        'mode': 'offline-xtf-reconstruction', 'input': paths[0], 'survey_id': survey_id,
        'evidence_images': len(api_images), 'detections_linked': len(detections),
        'first_image_id': api_images[0]['image_id'], 'first_image_url': api_images[0]['url'],
        'retry_reused_evidence_images': True,
    }, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Run with local in-memory Supabase/Storage equivalents.')
    parser.add_argument('--xtf-offline', action='store_true', help='Also verify actual XTF reconstruction and evidence persistence offline.')
    args = parser.parse_args()
    if args.xtf_offline:
        verify_xtf_offline()
    else:
        verify(offline=args.offline)
