# TARANG Platform — Technology Stack Specification
*Enterprise Ocean Telemetry & Maritime Intelligence*
*Smart India Hackathon 2026*

---

## 1. Frontend & Client Presentation Layer

| Layer / Capability | Technology | Version / Specification | Rationale & Enterprise Usage |
| :--- | :--- | :--- | :--- |
| **Core Framework** | **Next.js (App Router)** | `v14.2+` | Production SSR & static pre-rendering, streaming UI with React Suspense, and edge routing. |
| **UI Library** | **React** | `v18.3+` | Declarative component model with concurrency primitives. |
| **Styling Engine** | **Tailwind CSS** | `v3.4+` | Custom ocean theme tokens, ergonomic responsive utilities, zero runtime overhead. |
| **Typography Hierarchy**| **Google Fonts** | Inter, Plus Jakarta Sans, Space Grotesk | • Headings: *Plus Jakarta Sans* (crisp, human-designed authority)<br>• Body: *Inter* (high legibility)<br>• Telemetry & Coordinates: *Space Grotesk* (monospaced mathematical precision) |
| **Interactive Physics**| **HTML5 Canvas / WebGL** | Custom Shader Pipeline | Interactive fluid/water ripple cursor physics layered across background without compromising clean white contrast. |
| **GIS & Geospatial Maps**| **Mapbox GL JS / Leaflet** | `v3.0+` | High-frequency bathymetric contour rendering, nautical vector tiles, and SVG trajectory spline interpolation. |
| **Design Tokens & Theme**| **TARANG Maritime Tokens** | `#FAFCFF` (Canvas), `#0A2540` (Navy), `#0284C7` (Azure), `#14B8A6` (Seafoam Glow) | Strict avoidance of generic AI templates; high-end human craft with deliberate whitespace and nautical accents. |

---

## 2. Artificial Intelligence & Computer Vision Pipeline

| Domain | Framework / Engine | Model Variant | Purpose |
| :--- | :--- | :--- | :--- |
| **Object Detection Head** | **YOLOv10 / YOLOv9-Ocean** | Custom Multi-Class Head | Real-time acoustic bounding box segmentation on 455 kHz side-scan sonar waterfall video feeds. |
| **Multispectral Classifier** | **ResNet-Ocean v4** | PyTorch / TorchScript | Extraction of Floating Debris Index (FDI) and NDVI band differentials (Sentinel-2 MSI bands 4, 8A, 11, 12). |
| **Synthetic Aperture Radar** | **SAR-PolNet** | Dual-Pol VV/VH Radar Model | Cloud-penetrating sea surface roughness anomaly isolation (ISRO RISAT-1 / NovaSAR-1). |
| **Edge Inference Runtime** | **ONNX Runtime & TensorRT** | FP16 Accelerated | Sub-30ms latency inference embedded on coastal buoys and autonomous AUV submersibles. |
| **Hydrodynamic Simulation** | **Lagrangian Particle Engine** | Runge-Kutta 4th Order | Computes current, wind, and tidal drift vectors using INCOIS Ocean State Forecast models. |

---

## 3. Backend, Database & Geospatial Infrastructure

| Service | Technology | Details |
| :--- | :--- | :--- |
| **API Gateway & Microservices** | **FastAPI (Python 3.11) & Node.js** | Async endpoints for sonar stream ingestion, telemetry ingestion, and mission planning. |
| **Primary Relational Store** | **PostgreSQL 16 + PostGIS 3.4** | Spatial indexing (`ST_DWithin`, `ST_Intersects`) for coordinates, polygons, and marine corridors. |
| **Time-Series Telemetry** | **TimescaleDB** | Continuous hypertable aggregates for ocean swell, drift vectors, and vessel telemetry. |
| **In-Memory Cache & Pub/Sub**| **Redis 7.2** | High-velocity caching of live radar sweeps, active ROV coordinates, and session locks. |
| **Object Storage** | **MinIO / AWS S3** | High-capacity archival for raw `.XTF` hydrographic files, SAR GeoTIFFs, and multispectral assets. |
| **Message Broker** | **Apache Kafka** | Ingesting real-time satellite orbital passes and buoy telemetry packets. |

---

## 4. Hardware & Autonomous Fleet Deployment Specs

- **Submersible ROV:** *Sagar-Kavach III* (Autonomous Underwater Vehicle with hydraulic manipulator claw, high-power LED arrays, 300m rated depth, and dual acoustic modems).
- **Surface Interceptor:** *ICGS Varuna* (Indian Coast Guard rapid response cutter, 24 knot cruise, equipped with thermal FLIR and mechanized recovery netting).
- **Communication Protocol:** Dual-mode INSAT-3DR GEO satellite transponder + acoustic underwater modem (+24 dB SNR, zero packet loss link).