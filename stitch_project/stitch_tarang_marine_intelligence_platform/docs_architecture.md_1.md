# TARANG Platform — Architecture & Documentation
**AI-Powered Marine Debris Detection & Logistics Platform**
*Smart India Hackathon 2026*

---

## 1. Project Overview
TARANG (तरंग - meaning "Wave" in Sanskrit) is an enterprise-grade ocean conservation and maritime logistics platform. It utilizes multispectral satellite imagery, synthetic aperture radar (SAR), autonomous underwater vehicle (AUV) sonar feeds, and hydrodynamic drift modeling to detect, verify, and orchestrate cleanup missions for marine debris across the Indian Ocean and coastal corridors.

---

## 2. Technology Stack & Directory Structure
```
tarang-platform/
├── app/
│   ├── layout.tsx             # Global Root Layout with WebGL fluid/water cursor ripple canvas
│   ├── page.tsx               # (/) Hero, Live Debris Drift Radar, Mission KPIs & Telemetry
│   ├── analyzer/
│   │   └── page.tsx           # (/analyzer) Sonar & Multispectral AI Debris Detection Console
│   ├── verification/
│   │   └── page.tsx           # (/verification) Expert Verification, Confidence Scoring & Classification
│   ├── logistics/
│   │   └── page.tsx           # (/logistics) Vessel Fleet Routing, Recovery Coordinates & Cleanup Dispatch
│   └── globals.css            # Bespoke Ocean Design System & Custom Wave / Ripple Tokens
├── components/
│   ├── navigation/            # Master Header, Persistent Subnav, SIH 2026 Badge
│   ├── fx/
│   │   └── FluidCanvas.tsx    # Interactive cursor water ripple / fluid curtain shader
│   ├── telemetry/             # Real-time bathymetry and oceanic drift counters
│   └── ui/                    # Ocean buttons, glass cards, badges, sensor gauges
├── docs/
│   ├── ARCHITECTURE.md        # High-level architecture and pipeline specs
│   ├── API_SPEC.md            # Sensor telemetry & inference APIs
│   └── DESIGN_SYSTEM.md       # Ocean palette, typography, micro-interactions
└── tailwind.config.js
```

---

## 3. Core Route Definitions
1. **`/` — Mission Operations Command (Landing)**
   - High-precision telemetry: Debris hotspots detected, active fleet cleanup sorties, ocean plastic tonnage intercepted.
   - Interactive live oceanic wave radar preview and drift vector simulation.
2. **`/analyzer` — Sonar & Multispectral AI Detection**
   - Side-scan sonar waterfall viewer, synthetic aperture radar anomaly overlays, microplastic density heatmaps.
   - Confidence threshold filters, bounding box segmentation, and deep ocean spectral signature breakdown.
3. **`/verification` — Expert Human-in-the-Loop Review**
   - Dual-view imagery comparison (raw satellite vs AI-inferred mask).
   - Citizen science and naval coast guard flagged incident audit workflow.
4. **`/logistics` — Maritime Fleet Route Planning**
   - Dynamic waypoint routing considering ocean currents, tide schedules, and vessel fuel autonomy.
   - Dispatch payload calculation and port dropoff coordination.

---

## 4. Ocean Design System Tokens
- **Base Canvas:** `#FAFCFF` (Bright clean maritime white)
- **Primary Deep Ocean:** `#0A2540` / `#031B33`
- **Azure Accent:** `#0284C7` (Lively crest)
- **Teal Marina:** `#0D9488` (Bio-sensor green-teal)
- **Subtle Ripple Effect:** Custom WebGL fragment shader with dampening wave equation coupled to pointer velocity.
