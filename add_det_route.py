import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

route = """
@app.route('/api/v1/xtf/<survey_id>/detections', methods=['GET'])
def get_survey_detections(survey_id):
    conn = get_db()
    detections = conn.execute("SELECT * FROM detections WHERE survey_id = ? ORDER BY confidence DESC", (survey_id,)).fetchall()
    conn.close()
    return jsonify([dict(d) for d in detections])
"""

if '/api/v1/xtf/<survey_id>/detections' not in content:
    content = content.replace('if __name__ == "__main__":', route + '\nif __name__ == "__main__":')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added route")
else:
    print("Route already exists")
