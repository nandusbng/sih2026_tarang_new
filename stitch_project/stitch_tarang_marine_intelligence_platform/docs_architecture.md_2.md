# TARANG Platform — Architecture Specification
**Autonomous AI-Powered Marine Debris Detection, Verification & Maritime Interception**
*Smart India Hackathon 2026 • Ministry of Earth Sciences (MoES) & INCOIS Track*
*Document Version:* 2.4.0 • *Updated:* October 2026

---

## 1. System Vision & Executive Overview
**TARANG** (तरंग — Sanskrit for *"Wave"*) is an enterprise maritime intelligence and autonomous ocean cleanup coordination platform. Engineered for the Indian Ocean, Arabian Sea, and Bay of Bengal maritime corridors, TARANG ingests multi-sensor remote sensing feeds (Sentinel-2 multispectral, ISRO RISAT C-band SAR, NovaSAR-1, and Autonomous Underwater Vehicle side-scan sonar hydrophone recordings), isolates anthropogenic debris clusters with >94.8% F1-precision, validates anomalies via a dual-expert/citizen-science pipeline, and computes hydrodynamic drift trajectories for autonomous ROVs (e.g., *Sagar-Kavach III*) and naval salvage interceptors.

---

## 2. Multi-Tier System Architecture

```
                                  [ MULTI-MODAL DATA SOURCES ]
                   ┌───────────────────────┬────────────────────────┬──────────────────────┐
                   │  Sentinel-2 (MSI)     │  SAR (ISRO-RISAT / C)  │  AUV Sonar (.XTF/.JSF│
                   │  Bands 4, 8A, 11, 12  │  VV/VH Dual-Pol Radar  │  455 kHz Dual Sidescan
                   └───────────┬───────────┴───────────┬────────────┴──────────┬───────────┘
                               │                       │                       │
                               ▼                       ▼                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. SENSOR INGESTION & TACTICAL PRE-PROCESSING LAYER                                                    │
│    • Atmospheric & sunglint correction (Sen2Cor / ACOLITE baseline)                                   │
│    • Floating Debris Index (FDI) & NDVI differential indexing                                          │
│    • Slant-range gain normalization & acoustic beamforming for sonar hydrophones                      │
└────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. NEURAL PERCEPTION & SEGMENTATION ENGINE (Edge & Cloud)                                              │
│    • Model Architecture: YOLOv10-Ocean custom detection head + ResNet-Ocean v4 backbone                │
│    • Target Classes: Ghost Nets (Nylon-6), Macroplastic Slicks (HDPE/PET), Derelict Drums, Longlines   │
│    • Inference Engine: ONNX Runtime / TensorRT deployed on Jetson AGX Orin Buoys & Cloud Cluster       │
│    • Multi-Scale Fusion: Confidence Scoring = 0.5 * FDI_Score + 0.3 * SAR_CoReg + 0.2 * Sonar_IoU     │
└────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. EXPERT VALIDATION & HUMAN-IN-THE-LOOP HUD (/verification)                                          │
│    • Dual-frame raw vs. segmented mask visual comparator                                               │
│    • Chlorophyll-a / sargassum weed false positive rejection heuristics                                │
│    • Multi-stakeholder gating: Coast Guard Tactical Authority + INCOIS Senior Hydrographers           │
│    • Gamified Citizen Science crowd-verification portal with consensus weighting algorithms            │
└────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                 │ (Approved Waypoints & Coordinates)
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. HYDRODYNAMIC DRIFT ENGINE & LOGISTICS OPTIMIZATION (/logistics)                                     │
│    • Ocean Current Coupling: INCOIS Ocean State Forecast (OSF) numerical Eulerian/Lagrangian models    │
│    • Trajectory Algorithm: Current-augmented A* pathfinding incorporating swell, tidal vectors, & wind│
│    • Mission ROI & Valuation Engine: Quantifies Ecological Benefit vs. Vessel kWh / Fuel Burn          │
│    • Autonomous Sortie Dispatch: GPX/KML waypoints handoff to Autonomous Surface Vessels & Class-4 ROVs│
└────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
                                     [ MARITIME INTERCEPTION FLEET ]
                   ┌───────────────────────────────────┬───────────────────────────────────┐
                   │ Autonomous ROV Sagar-Kavach III   │ Indian Coast Guard Interceptors   │
                   │ Hydraulic Claws & Suction Harvester│ Harbor Recovery Tender Flotillas │
                   └───────────────────────────────────┴───────────────────────────────────┘
```

---

## 3. Database Schema Specification (PostgreSQL / PostGIS & TimescaleDB)

TARANG requires high-throughput spatial vector indexing and time-series telemetry storage for active hydrophone nodes and drifting targets.

### 3.1 `sensor_sources`
Tracks orbital passes, airborne sorties, and naval hydrophone buoy assets.
```sql
CREATE TABLE sensor_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(32) NOT NULL, -- 'SENTINEL_2', 'SAR_RISAT', 'AUV_SONAR', 'BUOY_ARGO'
    satellite_or_vessel_id VARCHAR(64) NOT NULL,
    orbital_pass_time TIMESTAMPTZ NOT NULL,
    spatial_footprint GEOMETRY(Polygon, 4326),
    ingest_latency_ms INTEGER,
    raw_telemetry_uri TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 `detected_anomalies`
Master catalog of detected macroplastics, ghost fishing gear, and maritime hazards.
```sql
CREATE TABLE detected_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_code VARCHAR(32) UNIQUE NOT NULL, -- e.g. 'ANM-2026-089' / '#LOC-8821'
    primary_category VARCHAR(64) NOT NULL, -- 'GHOST_NET', 'HDPE_DRUM', 'POLYMER_SLICK', 'DERELICT_RIG'
    neural_confidence NUMERIC(5, 4) NOT NULL, -- e.g. 0.9482 (94.82%)
    model_version VARCHAR(32) DEFAULT 'YOLOv10-Ocean-v4.2',
    coordinates GEOMETRY(Point, 4326) NOT NULL,
    nadir_depth_meters NUMERIC(6, 2), -- e.g. -34.50m
    estimated_mass_kg NUMERIC(8, 2), -- e.g. 420.00
    estimated_area_m2 NUMERIC(8, 2),
    fdi_spectral_index NUMERIC(5, 4),
    acoustic_backscatter_db NUMERIC(5, 2), -- e.g. -18.2 dB
    severity_level VARCHAR(16) NOT NULL, -- 'CRITICAL', 'ELEVATED', 'NOMINAL'
    verification_status VARCHAR(24) DEFAULT 'PENDING', -- 'PENDING', 'ACCEPTED', 'REJECTED', 'DISPATCHED'
    imagery_crop_uri TEXT,
    mask_overlay_uri TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_anomalies_geo ON detected_anomalies USING GIST(coordinates);
CREATE INDEX idx_anomalies_status ON detected_anomalies(verification_status);
```

### 3.3 `expert_audits`
Audit trail of decisions made by INCOIS scientists, Coast Guard commanders, and crowd analysts.
```sql
CREATE TABLE expert_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id UUID REFERENCES detected_anomalies(id) ON DELETE CASCADE,
    auditor_id UUID NOT NULL,
    auditor_role VARCHAR(32) NOT NULL, -- 'INCOIS_HYDROGRAPHER', 'COAST_GUARD_TACTICAL', 'CITIZEN_ANALYST'
    action_decision VARCHAR(16) NOT NULL, -- 'ACCEPT', 'REJECT', 'ESCALATE'
    rejection_reason VARCHAR(64), -- 'SARGASSUM_WEED', 'CLOUD_GLARE', 'FOAM_LINE', 'CORAL_OUTCROP'
    consensus_score NUMERIC(5, 4),
    cryptographic_audit_hash VARCHAR(128) NOT NULL,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.4 `hydrodynamic_drift_vectors`
TimescaleDB hypertable tracking real-time surface drift predictions and current vectors.
```sql
CREATE TABLE hydrodynamic_drift_vectors (
    id BIGSERIAL,
    anomaly_id UUID REFERENCES detected_anomalies(id),
    timestamp TIMESTAMPTZ NOT NULL,
    surface_drift_speed_knots NUMERIC(4, 2),
    drift_heading_deg NUMERIC(5, 2),
    swell_height_meters NUMERIC(4, 2),
    sea_surface_temp_c NUMERIC(4, 2),
    projected_position GEOMETRY(Point, 4326),
    corridor_breach_window_hrs NUMERIC(4, 2),
    PRIMARY KEY (id, timestamp)
);
SELECT create_hypertable('hydrodynamic_drift_vectors', 'timestamp');
```

### 3.5 `fleet_sorties` & `mission_waypoints`
Orchestration for autonomous ROVs, surface skimmers, and naval salvage cutters.
```sql
CREATE TABLE fleet_sorties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sortie_code VARCHAR(32) UNIQUE NOT NULL, -- e.g. 'IN-402'
    assigned_vessel_id VARCHAR(64) NOT NULL, -- e.g. 'ROV Sagar-Kavach III'
    vessel_class VARCHAR(32) NOT NULL, -- 'IMO_CLASS_4_AUTONOMOUS', 'SALVAGE_CUTTER'
    mission_status VARCHAR(24) DEFAULT 'QUEUED', -- 'QUEUED', 'DISPATCHED', 'INTERCEPTING', 'RECOVERED', 'DOCKED'
    origin_hub VARCHAR(64) NOT NULL, -- e.g. 'INS Kadamba Hub'
    destination_terminal VARCHAR(64) NOT NULL, -- e.g. 'JNPT Marine Plastics Hub'
    total_path_nm NUMERIC(6, 2),
    target_debris_mass_kg NUMERIC(8, 2),
    est_fuel_kwh_burn NUMERIC(8, 2),
    ecological_roi_ratio NUMERIC(5, 2),
    dispatched_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE mission_waypoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sortie_id UUID REFERENCES fleet_sorties(id) ON DELETE CASCADE,
    waypoint_order INTEGER NOT NULL,
    target_anomaly_id UUID REFERENCES detected_anomalies(id),
    waypoint_coordinates GEOMETRY(Point, 4326) NOT NULL,
    target_depth_meters NUMERIC(6, 2),
    estimated_arrival TIMESTAMPTZ,
    completion_status VARCHAR(24) DEFAULT 'PENDING'
);
```

---

## 4. REST & WebSocket API Specification

Base URL: `https://api.tarang.incois.gov.in/v1`

### 4.1 Ingestion & Neural Inference Endpoints
* `POST /ingest/hydrophone-batch`
  - **Payload:** Multiform file upload (`.XTF`, `.JSF`, `.BAG`, `.RAW`) or direct hydrophone sensor stream.
  - **Action:** Slant-range gain normalization, STFT spectrogram extraction, and YOLOv10-Ocean forward pass.
  - **Returns:** `{ batch_id, status: "PROCESSING", estimated_duration_sec: 1.4 }`
* `GET /telemetry/sonar-stream/live`
  - **Protocol:** `WebSocket / SSE`
  - **Payload:** Real-time stream of detected bounding boxes, acoustic backscatter dB, nadir depth soundings, and FPS.

### 4.2 Detection & Anomaly Query APIs
* `GET /anomalies`
  - **Query Params:** `status=PENDING&min_confidence=0.85&bbox=[minLon,minLat,maxLon,maxLat]`
  - **Response:** JSON list of detected anomalies with GeoJSON coordinates, spectral classification, and mass estimate.
* `GET /anomalies/:id/spectra`
  - **Response:** FDI (Floating Debris Index), NDVI, raw Sentinel-2 12-band spectral curve, and acoustic reflectivity profile.

### 4.3 Expert Verification & Governance APIs
* `POST /verification/:anomalyId/decision`
  - **Body:** `{ action: "ACCEPT" | "REJECT", auditor_id: "...", rejection_reason: "...", cryptographic_signature: "..." }`
  - **Response:** `{ status: "RESOLVED", new_verification_state: "ACCEPTED", queue_updated: true }`
* `GET /gamification/leaderboard`
  - **Response:** Citizen science analyst rankings, verified points, streak count, and tokenized reputation scores.

### 4.4 Maritime Logistics & Trajectory Simulation APIs
* `POST /logistics/optimize-route`
  - **Body:** `{ origin_base: "INS Kadamba", waypoint_ids: ["LOC-8821", "LOC-8824", "LOC-8830"], vessel_class: "IMO_CLASS_4" }`
  - **Response:** GeoJSON spline trajectory, waypoint order, A* current-corrected ETA, electrical kWh consumption, and ecological ROI ratio.
* `POST /logistics/sortie/dispatch`
  - **Body:** `{ sortie_code: "IN-402", export_format: "KML" | "GPX" | "AP_PAYLOAD" }`
  - **Response:** Encrypted telemetry manifest and autonomous autopilot packet link.

---

## 5. Security, Failover & Resiliency
- **mTLS & Satellite Tunneling:** All ship-to-shore communications over INSAT-3DR and Argo buoys enforce mutual TLS with hardware security module (HSM) key storage.
- **Offline Edge Autonomy:** ROV edge microcontrollers cache hydrodynamic drift matrices; if satellite link SNR falls below +12 dB, autonomous failsafe returns vehicle to last verified acoustic waypoint.
- **Audit Immutability:** Every human verification trigger writes to a SHA-256 chained audit log ensuring non-repudiation for Indian Coast Guard operations.