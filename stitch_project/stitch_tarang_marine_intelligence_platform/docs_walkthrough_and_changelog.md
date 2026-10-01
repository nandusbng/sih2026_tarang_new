# TARANG Platform — Walkthrough & Changelog
*Smart India Hackathon 2026 • Marine Debris Intelligence & Autonomous Interception*
*Latest Milestone:* Sprint 1 Architecture & Core Frontend Completion

---

## 1. Product Walkthrough & Implemented User Journeys

The TARANG platform has been constructed as a unified, enterprise-grade ocean intelligence suite designed to eliminate marine plastics, ghost fishing nets, and hazardous maritime debris. The application spans four core operational pillars:

### Pillar 1: Mission Operations Command (`/`)
- **Visual Design:** Pure, bright white canvas (`#FAFCFF`) elevated by bespoke oceanic gradients, fluid ambient wave canvas reactions, and authoritative nautical typography (*Plus Jakarta Sans* + *Space Grotesk*).
- **Live Oceanic Sweep Console:** Real-time rotating radar HUD operating across the Arabian Sea and Bay of Bengal, enabling toggleable inspection modes (*Sentinel Optical*, *SAR Radar*, *AUV Sonar Bathymetry*).
- **Interactive Cluster Pins:** Clickable targets (e.g. `Cluster #IN-882`, `Cluster #IN-904`) displaying estimated mass (2.1 Tons), drift heading (1.8 kn SE), and classification neural confidence (96.2%).
- **3-Tier Operational Lifecycle:** Step-by-step technical breakdown of *AI Detection & Spectral Signatures*, *Expert Human-in-the-Loop Validation*, and *Autonomous Retrieval & Fleet Dispatch*.
- **Multi-Sensor Synthesis Viewport:** Side-by-side comparison illustrating raw optical sunglint occlusion vs. calibrated Floating Debris Index (FDI) infrared segmentation (+18.4 dB signal-to-noise gain).
- **National Stakeholder Alignment:** Integrated governance commitments with INCOIS, Ministry of Earth Sciences (MoES), and the Indian Coast Guard.

### Pillar 2: Sonar AI Detection Console (`/analyzer`)
- **Acoustic Video Waterfall Viewport:** Dual-channel side-scan bathymetry seafloor footage recorded at 455 kHz with real-time neural bounding boxes (*Ghost Net Nylon-6: 94.2%*, *HDPE Industrial Drum: 91.8%*).
- **Live Hydrographic Gauges:** Telemetry HUD tracking Nadir Depth Sounding (-44.6m), Acoustic Backscatter (-18.2 dB), and SAR Vector Co-registration index (0.84).
- **Interactive Video Scrubber:** Chronological anomaly markers, playback speed accelerators (1.0x, 2.0x, 4.0x), and freeze-frame analysis.
- **Detected Anomalies Sidebar:** Ranked list of actionable items with severity ratings (*Urgent Intervention*, *Bio-Hazard Mod*, *Derelict Gear*), GPS coordinates, and one-click routing to Expert Review.
- **Bespoke Dropzone Importer:** Wave-patterned drag-and-drop hydrographic ingestion portal accepting `.XTF`, `.JSF`, `.BAG`, and raw hydrophone bundles with live slant-range gain normalization feedback.

### Pillar 3: Expert Human-in-the-Loop Review (`/verification`)
- **Dual-View Validation HUD:** Side-by-side comparative inspection of raw multispectral/SAR imagery against segmented neural masks, preventing false alarms on sargassum biomass.
- **Gating Actions:** Ocean-themed tactile decision triggers (*Accept & Queue for Sortie* in seafoam green, *Reject / Mark False Positive* in coral/red).
- **Citizen Science Portal:** Gamified crowdsourced analysis leaderboard with verification streaks, accuracy rankings, and tokenized reputation points for naval community volunteers.

### Pillar 4: Logistics & ROV Route Planning (`/logistics`)
- **Tactical Maritime GIS Viewport:** Integrated bathymetric chart showing depth contours (-15m to -60m), ocean drift field vectors, and commercial shipping exclusion zones (IN-Bombay High South).
- **Waypoint Recovery Queue:** Sequential recovery scheduling (`WP-01` through `WP-04`) optimized by an A* current-augmented kinematics engine.
- **Interactive Route Kinetics Simulator:** Micro-interaction engine that executes autonomous vessel movement along planned spline trajectories with real-time progress indicators.
- **Mission ROI & Ecological Valuation Engine:** Live economic and ecological balance sheet comparing prevented environmental harm (₹18,40,000 / $22,100, coral reef protection score 94/100, 12.8 Tons CO2e saved) against mission operational expenses (₹4,15,000 / $4,980 for ROV electrical kWh and vessel tender hours).
- **Autonomous Sortie Dispatcher:** One-click mission authorization and KML/GPX waypoint file generator for naval logistics terminals (e.g., INS Kadamba & JNPT Hub).

---

## 2. Detailed Changelog

### Version 2.4.0 — (Sprint 1 Wrap-up)
- **Feature (Documentation):** Published comprehensive `docs/architecture.md`, `docs/tech_stack.md`, and `docs/walkthrough_and_changelog.md`.
- **Feature (Database):** Formalized PostGIS 3.4 and TimescaleDB relational schemas covering `sensor_sources`, `detected_anomalies`, `expert_audits`, `hydrodynamic_drift_vectors`, and `fleet_sorties`.
- **Feature (APIs):** Outlined REST and WebSocket contract specifications for hydrophone ingestion, anomaly querying, expert audit signing, and A* route optimization.
- **Feature (Logistics Screen):** Finalized `/logistics` interactive tactical GIS console, ROV path kinetics simulator, and Mission ROI calculator.

### Version 2.2.0 — (Analyzer & Sonar AI Release)
- **Feature (Analyzer Screen):** Deployed `/analyzer` console featuring 455 kHz dual-channel acoustic side-scan video viewer, live telemetry HUD, and anomaly sidebar.
- **Feature (Data Ingest):** Implemented `.XTF` and multibeam hydrographic drag-and-drop dropzone styled with subtle ocean wave borders.

### Version 2.0.0 — (Landing & Identity Launch)
- **Feature (Landing Screen):** Shipped `/` flagship landing interface with ambient wave canvas effect, real-time rotating radar HUD, 3-step lifecycle cards, and FDI comparison view.
- **Branding:** Established vector brand emblem `TARANG` with wave crest motifs and oceanic gradients.
- **Theme Foundation:** Configured Tailwind tokens with high-contrast `#FAFCFF` maritime white background and bespoke oceanic palette.

### Version 1.0.0 — (Initial Architecture Setup)
- **Init:** Next.js App Router repository initialization with route scaffolding for `/`, `/analyzer`, `/verification`, and `/logistics`.
- **Docs:** Created initial `docs/ARCHITECTURE.md` specification.