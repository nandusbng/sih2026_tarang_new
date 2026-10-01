---
name: TARANG Maritime Intelligence
colors:
  surface: '#f7f9ff'
  surface-dim: '#c8dcf4'
  surface-bright: '#f7f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#edf4ff'
  surface-container: '#e3efff'
  surface-container-high: '#d9eaff'
  surface-container-highest: '#d1e4fd'
  on-surface: '#081d2f'
  on-surface-variant: '#43474d'
  inverse-surface: '#1f3245'
  inverse-on-surface: '#e8f1ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#49607e'
  primary: '#000f22'
  on-primary: '#ffffff'
  primary-container: '#0a2540'
  on-primary-container: '#768dad'
  inverse-primary: '#b0c8eb'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#001210'
  on-tertiary: '#ffffff'
  tertiary-container: '#002a26'
  on-tertiary-container: '#1f9c8f'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#b0c8eb'
  on-primary-fixed: '#001c37'
  on-primary-fixed-variant: '#314865'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#89f5e7'
  tertiary-fixed-dim: '#6bd8cb'
  on-tertiary-fixed: '#00201d'
  on-tertiary-fixed-variant: '#005049'
  background: '#f7f9ff'
  on-background: '#081d2f'
  surface-variant: '#d1e4fd'
  canvas-base: '#FAFCFF'
  abyssal-navy: '#031B33'
  surface-ice: '#F0F4F8'
  border-subtle: '#E2E8F0'
  seafoam-glow: '#14B8A6'
  sonar-alert: '#E11D48'
  telemetry-amber: '#D97706'
typography:
  display-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 42px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  telemetry-metric:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  label-code:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-desktop: 2rem
  margin: 1rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

TARANG (तरंग — Sanskrit for "Wave") is an enterprise-grade maritime telemetry and marine debris intelligence platform designed for mission operations in the Indian Ocean, Bay of Bengal, and Arabian Sea. The visual language blends authoritative naval hydrography with modern, high-precision geospatial telemetry. 

The aesthetic is crisp, technical, and maritime-scientific—eschewing generic dark dashboard tropes in favor of a bright, sunlit open-ocean daylight console (`#FAFCFF` maritime white base). Deep oceanic navy anchors structural components, while vibrant azure crests and bio-sensor seafoams articulate data, confidence thresholds, and trajectory vectors. 

Glassmorphism is deployed with clinical restraint: subtle, ocean-tinted translucent layers (white or ultra-light slate with 12px blur and soft 1px borders) evoke thin water columns and acrylic vessel navigation displays without obscuring multi-layer bathymetric charts or synthetic aperture radar (SAR) raster layers.

## Colors

The color system operates on an maritime light-mode philosophy that maintains sunlight readability for port command centers and offshore bridge consoles:

- **Primary (`#0A2540`) & Abyssal Navy (`#031B33`):** Defines master navigation headers, high-level typography, structural dividing rails, and primary CTA fills.
- **Secondary / Azure Crest (`#0284C7`):** Represents operational vectors, active vessel paths, interactive link states, and AI bounding box highlights.
- **Tertiary / Marina Teal (`#0D9488`) & Seafoam Glow (`#14B8A6`):** Reserved for validated ecological data, verified ocean plastics, sensor health status, and live telemetry badges.
- **Canvas Base (`#FAFCFF`) & Surface Ice (`#F0F4F8`):** Prevents clinical eye strain by infusing neutral whites with 1–2% cyan-slate undertones, echoing sea spray and daylight water reflections.
- **Functional Accents:** `sonar-alert` (`#E11D48`) for ghost gear or vessel collision hazards, and `telemetry-amber` (`#D97706`) for high-drift unconfirmed anomalies.

## Typography

The typographic hierarchy establishes clear boundaries between executive overviews, analytical dense tables, and real-time geospatial telemetry:

1. **Plus Jakarta Sans (Headlines & Display):** Balances geometric authority with friendly, human-calibrated curves. The tight negative tracking (`-0.02em` to `-0.03em`) on display sizes gives TARANG an intentional, modern maritime aerospace character.
2. **Inter (Body & Controls):** Provides neutral, highly legible legibility for data-dense tables, sensor logs, verification workflows, and mission tasking interfaces.
3. **Space Grotesk (Telemetry & Sensor Metrics):** Serves as the signature technical voice for coordinates (GPS/Bathymetry), vessel MMSI IDs, drifting speeds in knots, SAR frequency measurements, and confidence scoring percentages.

## Layout & Spacing

TARANG adheres to a 12-column modular grid designed for mission operations displays ranging from 13-inch field toughbooks to 4K maritime command wall boards:

- **Breakpoints:**
  - `Mobile (sm)`: 320px – 639px (single column, stackable telemetry drawers)
  - `Tablet (md)`: 640px – 1023px (6-column, floating collateral side-sheets)
  - `Desktop (lg/xl)`: 1024px – 1440px+ (12-column fluid grid, split viewport for bathymetric charts & verification panels)
- **Spatial Rhythm:** Built on an 8px base rhythm (`0.5rem` step). UI cards maintain strict 24px (`space-lg`) internal padding for critical data readouts, while compact telemetry strips compress down to 8px (`space-sm`) vertical gaps to maximize map real estate.

## Elevation & Depth

Visual hierarchy combines low-opacity hydrodynamic glass layering with razor-thin hairline borders:

- **Level 0 (Water Canvas):** The baseline `#FAFCFF` canvas hosting the interactive WebGL vector currents or satellite basemap.
- **Level 1 (Submerged Containers):** Floating telemetry cards and control modules utilize `rgba(255, 255, 255, 0.85)` with a 12px backdrop blur, a 1px border colored `#E2E8F0`, and an ultra-subtle ambient shadow: `0 4px 20px -2px rgba(10, 37, 64, 0.05)`.
- **Level 2 (Active Inspection Sheets / Drawers):** Elevated inspection sidebars utilize `rgba(255, 255, 255, 0.95)` with `box-shadow: 0 12px 32px -4px rgba(10, 37, 64, 0.12), 0 0 0 1px rgba(2, 132, 199, 0.15)`.
- **Level 3 (Tactical Overlays & Floating Alerts):** Modals, Sonar detection inspect popovers, and route dispatch menus employ sharp contrast with `box-shadow: 0 20px 48px -8px rgba(3, 27, 51, 0.22)`.

## Shapes

The design system adopts a **Soft (Level 1)** corner geometry (`4px` for small indicators, `8px` for cards/panels, `12px` for primary dialogs). This deliberate restraint evokes technical nautical instruments, marine radar displays, and marine GPS consoles rather than hyper-rounded consumer software. Buttons and interactive chips retain precise, micro-curved edges (`6px`) conveying structural stability.

## Components

### Buttons
- **Primary Action (Mission Command):** Deep Ocean Navy (`#0A2540`) solid fill, white text, 6px border radius. On hover, subtly lifts with a crest highlight (`#031B33`) and an azure glow (`box-shadow: 0 0 12px rgba(2, 132, 199, 0.35)`).
- **Secondary (Hydro Vector):** Pure white background, 1px border in `#E2E8F0`, text in `#0A2540`. On hover, border shifts to `#0284C7` with a tinted background `#F0F9FF`.
- **Telemetry Action (Ghost/Sensor):** Transparent background, monospaced icon, seafoam text (`#0D9488`).

### Telemetry Badges & Chips
- Designed with `Space Grotesk` uppercase tracking (`label-code`).
- Structure: 4px radius, 4px vertical padding, 8px horizontal padding.
- **Variants:**
  - *Confirmed Debris:* Background `rgba(13, 148, 136, 0.1)`, text `#0D9488`, border `1px solid rgba(13, 148, 136, 0.25)`.
  - *Drift Risk Urgent:* Background `rgba(225, 29, 72, 0.1)`, text `#E11D48`, border `1px solid rgba(225, 29, 72, 0.25)`.
  - *Radar Ping / SAR Active:* Background `rgba(2, 132, 199, 0.08)`, text `#0284C7`, animated pulsing dot.

### Cards & Panels
- Constructed using glass-tinted ocean surfaces (`rgba(255, 255, 255, 0.88)` over `#FAFCFF`).
- Enclosed with a crisp 1px `#E2E8F0` border that transitions to `#0284C7` (Azure) upon active hover or coordinate selection.
- Card headers incorporate an ocean coordinate stamp or mission ID in `Space Grotesk` above the primary descriptive title.

### Form Inputs & Filters
- **Text & Coordinate Fields:** Background `#FFFFFF`, 1px solid border `#CBD5E1`, text `#0A2540`. Active focus rings display a 2px outward ring in `rgba(2, 132, 199, 0.25)`.
- **Selection Toggles & Segmented Radios:** Tab pills inside an `#F0F4F8` track, active tab styled with pure white card backing and crisp drop shadow.

### Specialized Maritime Components
- **Sonar Waterfall Strip:** High-contrast dark-mode sub-viewport embedded within light cards, featuring synthetic aperture radar overlays and segmented azure bounding boxes.
- **Drift Vector Gauge:** Directional arrow with knot readings and bathymetric depth indices displayed using `Space Grotesk`.