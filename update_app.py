import os

# Read app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Prepare new routes
new_code = """
import xtf_parser

XTF_SURVEYS = {}

@app.route('/api/v1/xtf/upload', methods=['POST'])
def xtf_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    uploaded_file = request.files['file']
    if not uploaded_file.filename.lower().endswith('.xtf'):
        return jsonify({'error': 'Invalid file extension, expected .xtf'}), 400
    
    # Save file
    save_name = f"upload_{uuid.uuid4().hex[:8]}.xtf"
    temp_path = os.path.join(OUTPUTS_DIR, save_name)
    uploaded_file.save(temp_path)
    
    try:
        # Parse XTF
        parsed_data = xtf_parser.parse_xtf(temp_path, OUTPUTS_DIR)
        if not parsed_data:
            return jsonify({'error': 'Invalid or unsupported XTF file.'}), 400
            
        survey_id = parsed_data['metadata']['survey_id']
        XTF_SURVEYS[survey_id] = parsed_data
        
        # Now pass generated images through YOLO model
        detections = []
        for img_info in parsed_data['images']:
            img_path = img_info['path']
            img = cv2.imread(img_path)
            if img is not None:
                results = model(img, conf=0.20, verbose=False)
                res = results[0]
                if len(res.boxes) > 0:
                    for idx, box in enumerate(res.boxes):
                        cls_id = int(box.cls[0])
                        cls_name = model.names.get(cls_id, f"class_{cls_id}")
                        score = float(box.conf[0]) * 100
                        coords = box.xyxy[0].tolist()
                        meta = get_meta(cls_name)
                        
                        crop_b64 = crop_and_encode(img, coords)
                        
                        detections.append({
                            'detection_id': f"XTF-DET-{uuid.uuid4().hex[:6]}",
                            'class_name': cls_name,
                            'title': meta['title'],
                            'confidence': round(score, 1),
                            'coordinates': [round(c, 1) for c in coords],
                            'crop_url': crop_b64,
                            'image_id': img_info['id'],
                            'ping_start': img_info['ping_start'],
                            'ping_end': img_info['ping_end']
                        })
        
        parsed_data['detections'] = detections
        
        return jsonify({
            'survey_id': survey_id,
            'input_type': 'xtf',
            'filename': uploaded_file.filename,
            'status': 'parsed',
            'total_pings': parsed_data['metadata']['total_pings'],
            'channels': parsed_data['metadata']['channel_count'],
            'images_reconstructed': len(parsed_data['images']),
            'detections_count': len(detections)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process XTF: {str(e)}'}), 500

@app.route('/api/v1/xtf/<survey_id>/metadata', methods=['GET'])
def get_xtf_metadata(survey_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Survey not found'}), 404
    return jsonify(XTF_SURVEYS[survey_id]['metadata'])

@app.route('/api/v1/xtf/<survey_id>/pings', methods=['GET'])
def get_xtf_pings(survey_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Survey not found'}), 404
    return jsonify(XTF_SURVEYS[survey_id]['pings'])

@app.route('/api/v1/xtf/<survey_id>/images', methods=['GET'])
def get_xtf_images(survey_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Survey not found'}), 404
    return jsonify(XTF_SURVEYS[survey_id]['images'])
    
@app.route('/api/v1/xtf/<survey_id>/images/<image_id>', methods=['GET'])
def get_xtf_image_file(survey_id, image_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Survey not found'}), 404
    
    for img in XTF_SURVEYS[survey_id]['images']:
        if img['id'] == image_id:
            return send_file(img['path'], mimetype='image/jpeg')
            
    return jsonify({'error': 'Image not found'}), 404
    
@app.route('/api/v1/xtf/<survey_id>/detections', methods=['GET'])
def get_xtf_detections(survey_id):
    if survey_id not in XTF_SURVEYS:
        return jsonify({'error': 'Survey not found'}), 404
    return jsonify(XTF_SURVEYS[survey_id].get('detections', []))

"""

# Insert before 'if __name__ == '__main__':'
insert_target = "if __name__ == '__main__':"
if insert_target in app_code:
    app_code = app_code.replace(insert_target, new_code + "\n" + insert_target)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)
