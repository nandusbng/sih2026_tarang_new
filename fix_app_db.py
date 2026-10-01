with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Image Det ID
content = content.replace(
    'det_id = f"ANM-2026-{(101 + idx):03d}"',
    'det_id = f"ANM-IMG-{uuid.uuid4().hex[:6]}"'
)

# Fix Video Det ID
content = content.replace(
    'det_id = f"ANM-VID-{det_counter:03d}"',
    'det_id = f"ANM-VID-{uuid.uuid4().hex[:6]}"'
)

# Fix SQLite Locking
bad_try_catch = """try:
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
                        print("DB Insert Error:", e)"""

good_try_catch = """try:
                        conn = get_db()
                        conn.execute('''
                            INSERT INTO detections (id, survey_id, class_name, title, category, confidence, classification_tier, requires_review, crop_url, material, hazard, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            det_id, 'SURVEY-DEMO', cls_name, meta['title'], meta['category'],
                            round(score, 1), tier, req_review, crop_b64, meta['material'], meta['hazard'], datetime.now().isoformat()
                        ))
                        conn.commit()
                    except Exception as e:
                        print("DB Insert Error:", e)
                    finally:
                        try:
                            conn.close()
                        except:
                            pass"""

content = content.replace(bad_try_catch, good_try_catch)

# Also fix the DB Insert Error Video
bad_try_catch_vid = """try:
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
                                    print("DB Insert Error Video:", e)"""

good_try_catch_vid = """try:
                                    conn = get_db()
                                    conn.execute('''
                                        INSERT INTO detections (id, survey_id, class_name, title, category, confidence, classification_tier, requires_review, crop_url, material, hazard, created_at)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        det_id, 'SURVEY-DEMO', cls_name, meta['title'], meta['category'],
                                        round(score, 1), tier, req_review, crop_b64, meta['material'], meta['hazard'], datetime.now().isoformat()
                                    ))
                                    conn.commit()
                                except Exception as e:
                                    print("DB Insert Error Video:", e)
                                finally:
                                    try:
                                        conn.close()
                                    except:
                                        pass"""

content = content.replace(bad_try_catch_vid, good_try_catch_vid)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
