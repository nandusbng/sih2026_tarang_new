import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Video/Image Detection Saving
insert_logic = """
                    det_id = f"ANM-2026-{(101 + idx):03d}"
                    detections.append({
                        'id': det_id,
                        'class_name': cls_name,
                        'title': meta['title'],
                        'category': meta['category'],
                        'badge': meta['badge'],
                        'color': meta['color'],
                        'badge_bg': meta['badge_bg'],
                        'material': meta['material'],
                        'hazard': meta['hazard'],
                        'confidence': round(score, 1),
                        'classification_tier': tier,
                        'requires_review': req_review,
                        'coordinates': [round(c, 1) for c in coords],
                        'dim': est_dim,
                        'depth': est_depth,
                        'crop_url': crop_b64
                    })
                    
                    # DB Insertion
                    try:
                        conn = get_db()
                        conn.execute('''
                            INSERT INTO detections (id, survey_id, class_name, title, category, confidence, classification_tier, requires_review, crop_url, material, hazard, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            det_id, 'SURVEY-DEMO', cls_name, meta['title'], meta['category'],
                            round(score, 1), tier, req_review, crop_b64, meta['material'], meta['hazard'], datetime.now().isoformat()
                        ))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print("DB Insert Error:", e)
"""
# Replace the image block first
pattern_img = re.compile(r"                    detections\.append\(\{\s*'id': f\"ANM-2026-\{\(101 \+ idx\):03d\}\",\s*'class_name': cls_name,.*?'crop_url': crop_b64\s*\}\)", re.DOTALL)
content = pattern_img.sub(insert_logic, content)


# Now video block
insert_video_logic = """
                                det_id = f"ANM-VID-{det_counter:03d}"
                                collected_crops[pos_key] = {
                                    'id': det_id,
                                    'class_name': cls_name,
                                    'title': meta['title'],
                                    'category': meta['category'],
                                    'badge': meta['badge'],
                                    'color': meta['color'],
                                    'badge_bg': meta['badge_bg'],
                                    'material': meta['material'],
                                    'hazard': meta['hazard'],
                                    'confidence': round(score, 1),
                                    'classification_tier': tier,
                                    'requires_review': req_review,
                                    'coordinates': [round(c, 1) for c in coords],
                                    'dim': est_dim,
                                    'depth': est_depth,
                                    'time_offset': f"{int(time_sec // 60):02d}:{int(time_sec % 60):02d}.{int((time_sec % 1)*100):02d}",
                                    'crop_url': crop_b64
                                }
                                
                                # DB Insertion
                                try:
                                    conn = get_db()
                                    conn.execute('''
                                        INSERT INTO detections (id, survey_id, class_name, title, category, confidence, classification_tier, requires_review, crop_url, material, hazard, created_at)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        det_id, 'SURVEY-DEMO', cls_name, meta['title'], meta['category'],
                                        round(score, 1), tier, req_review, crop_b64, meta['material'], meta['hazard'], datetime.now().isoformat()
                                    ))
                                    conn.commit()
                                    conn.close()
                                except Exception as e:
                                    print("DB Insert Error Video:", e)
                                    
                                det_counter += 1
"""
pattern_vid = re.compile(r"                                collected_crops\[pos_key\] = \{\s*'id': f\"ANM-VID-\{det_counter:03d\}\",.*?'crop_url': crop_b64\s*\}\s*det_counter \+= 1", re.DOTALL)
content = pattern_vid.sub(insert_video_logic, content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
