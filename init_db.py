import os
import sqlite3
import hashlib
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'tarang.db')

def hash_password(password, salt=None):
    if not salt:
        salt = uuid.uuid4().hex[:16]
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return hashed, salt

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Surveys Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            survey_id TEXT PRIMARY KEY,
            survey_name TEXT,
            survey_date TEXT,
            survey_time TEXT,
            location_name TEXT,
            region TEXT,
            specific_area TEXT,
            platform TEXT,
            sonar_device TEXT,
            sonar_frequency TEXT,
            created_by TEXT,
            created_at TEXT,
            status TEXT,
            navigation_status TEXT,
            processing_status TEXT
        )
    ''')

    # Safe column additions if surveys already existed with older schema
    c.execute("PRAGMA table_info(surveys)")
    existing_cols = [row[1] for row in c.fetchall()]
    if 'region' not in existing_cols:
        c.execute("ALTER TABLE surveys ADD COLUMN region TEXT")
    if 'specific_area' not in existing_cols:
        c.execute("ALTER TABLE surveys ADD COLUMN specific_area TEXT")
    if 'platform' not in existing_cols:
        c.execute("ALTER TABLE surveys ADD COLUMN platform TEXT")

    # 2. Detections Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            survey_id TEXT,
            class_name TEXT,
            title TEXT,
            category TEXT,
            confidence REAL,
            classification_tier TEXT,
            requires_review BOOLEAN,
            latitude REAL,
            longitude REAL,
            ping_number INTEGER,
            depth TEXT,
            altitude TEXT,
            heading REAL,
            crop_url TEXT,
            material TEXT,
            hazard TEXT,
            created_at TEXT,
            verification_status TEXT DEFAULT 'pending',
            clearance_status TEXT DEFAULT 'detected',
            hotspot_id TEXT,
            observations_count INTEGER DEFAULT 1
        )
    ''')

    # Add any missing columns to detections
    c.execute("PRAGMA table_info(detections)")
    existing_det_cols = [row[1] for row in c.fetchall()]
    if 'verification_status' not in existing_det_cols:
        c.execute("ALTER TABLE detections ADD COLUMN verification_status TEXT DEFAULT 'pending'")
    if 'clearance_status' not in existing_det_cols:
        c.execute("ALTER TABLE detections ADD COLUMN clearance_status TEXT DEFAULT 'detected'")
    if 'hotspot_id' not in existing_det_cols:
        c.execute("ALTER TABLE detections ADD COLUMN hotspot_id TEXT")
    if 'observations_count' not in existing_det_cols:
        c.execute("ALTER TABLE detections ADD COLUMN observations_count INTEGER DEFAULT 1")

    # 3. Users Table (Role-based Authentication & Profile)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            institution_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    ''')

    # 4. Survey Areas Table (Subdivisions of Surveys)
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_areas (
            id TEXT PRIMARY KEY,
            survey_id TEXT NOT NULL,
            area_name TEXT NOT NULL,
            coordinates TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )
    ''')

    # 5. Analyst Reviews Table (Operator -> Analyst Queue Status)
    c.execute('''
        CREATE TABLE IF NOT EXISTS analyst_reviews (
            id TEXT PRIMARY KEY,
            survey_id TEXT NOT NULL,
            survey_name TEXT NOT NULL,
            sent_to TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            status TEXT NOT NULL,
            validated_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            review_required_count INTEGER DEFAULT 0,
            notes TEXT
        )
    ''')

    # 6. Notifications Table (Operational Alerts & Events)
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            survey_id TEXT
        )
    ''')

    # 7. Documents Table (Survey files, reports, exports)
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            survey_id TEXT,
            name TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size TEXT,
            created_at TEXT
        )
    ''')

    # 8. Hotspots Table (Declared & Candidate Concentrations)
    c.execute('''
        CREATE TABLE IF NOT EXISTS hotspots (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            radius_nm REAL NOT NULL,
            area_km2 REAL NOT NULL,
            concentration TEXT NOT NULL,
            dominant_type TEXT NOT NULL,
            verified_count INTEGER DEFAULT 0,
            cleared_count INTEGER DEFAULT 0,
            pending_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Candidate Hotspot',
            created_at TEXT
        )
    ''')

    # 9. Clearance Records Table (Marine Portal Cleanup Submissions)
    c.execute('''
        CREATE TABLE IF NOT EXISTS clearance_records (
            id TEXT PRIMARY KEY,
            target_id TEXT,
            hotspot_id TEXT,
            team TEXT NOT NULL,
            status TEXT NOT NULL,
            clearance_date TEXT NOT NULL,
            debris_type TEXT NOT NULL,
            notes TEXT,
            before_image TEXT,
            after_image TEXT,
            created_at TEXT
        )
    ''')

    # Seed Default Users if not present
    default_users = [
        ('Cmdr. Rajesh Verma', 'survey_ops', 'tarang2026', 'survey_operator'),
        ('Dr. Anya Sharma', 'sonar_expert', 'tarang2026', 'sonar_analyst'),
        ('Capt. Vikram Das', 'marine_fleet', 'tarang2026', 'marine_analyst'),
        ('Joint Director Alok Roy', 'gov_admin', 'tarang2026', 'gov_authority'),
        ('Chief Administrator', 'platform_admin', 'tarang2026', 'platform_admin'),
        ('Citizen Observer', 'public', 'public', 'public')
    ]

    for full_name, inst_id, pwd, role in default_users:
        c.execute("SELECT id FROM users WHERE institution_id = ?", (inst_id,))
        if not c.fetchone():
            p_hash, salt = hash_password(pwd)
            c.execute('''
                INSERT INTO users (id, full_name, institution_id, password_hash, salt, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            ''', (str(uuid.uuid4()), full_name, inst_id, p_hash, salt, role, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def reset_operational_data():
    """Purges all fake/sample operational data to satisfy zero-data requirements."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM detections")
    c.execute("DELETE FROM hotspots")
    c.execute("DELETE FROM clearance_records")
    c.execute("DELETE FROM surveys")
    c.execute("DELETE FROM survey_areas")
    c.execute("DELETE FROM analyst_reviews")
    c.execute("DELETE FROM notifications")
    c.execute("DELETE FROM documents")
    conn.commit()
    conn.close()
    print("All operational tables successfully cleared. Platform is 100% database/model-driven.")

if __name__ == '__main__':
    init_db()
    reset_operational_data()
    print("Database initialized and cleared to zero operational state.")
