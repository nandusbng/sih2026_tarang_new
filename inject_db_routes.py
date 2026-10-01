import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
imports = """import os
import uuid
import base64
import sqlite3
from datetime import datetime
"""
content = content.replace("import os\nimport uuid\nimport base64\n", imports)

# 2. DB Helper
db_helper = """
DB_PATH = os.path.join(os.path.dirname(__file__), 'tarang.db')
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

"""
content = content.replace("app = Flask(__name__, static_folder='.')\n", "app = Flask(__name__, static_folder='.')\n" + db_helper)

# 3. New API Routes
new_routes = """
@app.route('/api/v1/surveys', methods=['POST'])
def create_survey():
    data = request.json
    survey_id = uuid.uuid4().hex[:8]
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO surveys (survey_id, survey_name, survey_date, survey_time, location_name, sonar_device, sonar_frequency, created_by, created_at, status, navigation_status, processing_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        survey_id, data.get('survey_name'), data.get('survey_date'), data.get('survey_time'),
        data.get('location_name'), data.get('sonar_device'), data.get('sonar_frequency'),
        data.get('created_by', 'Operator'), datetime.now().isoformat(),
        'CREATED', 'PENDING', 'PENDING'
    ))
    conn.commit()
    conn.close()
    return jsonify({'survey_id': survey_id, 'status': 'success'})

@app.route('/api/v1/surveys', methods=['GET'])
def get_surveys():
    conn = get_db()
    surveys = conn.execute('SELECT * FROM surveys ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(s) for s in surveys])

@app.route('/api/v1/surveys/<survey_id>', methods=['GET'])
def get_survey(survey_id):
    conn = get_db()
    survey = conn.execute('SELECT * FROM surveys WHERE survey_id = ?', (survey_id,)).fetchone()
    conn.close()
    if not survey:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(survey))

@app.route('/api/v1/detections/analyst', methods=['GET'])
def get_analyst_detections():
    # Only A and B
    conn = get_db()
    detections = conn.execute("SELECT * FROM detections WHERE classification_tier IN ('A', 'B') ORDER BY confidence DESC").fetchall()
    conn.close()
    return jsonify([dict(d) for d in detections])

@app.route('/api/v1/detections/intermediate', methods=['GET'])
def get_intermediate_detections():
    # Only C
    conn = get_db()
    detections = conn.execute("SELECT * FROM detections WHERE classification_tier = 'C' ORDER BY confidence DESC").fetchall()
    conn.close()
    return jsonify([dict(d) for d in detections])

"""
content = content.replace("XTF_SURVEYS = {}\n", "XTF_SURVEYS = {}\n" + new_routes)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
