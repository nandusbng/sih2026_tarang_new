---
name: Oceanic Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#43474d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#49607e'
  primary: '#000f22'
  on-primary: '#ffffff'
  primary-container: '#0a2540'
  on-primary-container: '#768dad'
  inverse-primary: '#b0c8eb'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#00101d'
  on-tertiary: '#ffffff'
  tertiary-container: '#00263e'
  on-tertiary-container: '#2792d5'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#b0c8eb'
  on-primary-fixed: '#001c37'
  on-primary-fixed-variant: '#314865'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.03em
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.005em
  telemetry-lg:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.02em
  telemetry-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
  telemetry-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes a high-precision, mission-critical marine operations aesthetic. It fuses the analytical rigor of industrial maritime logistics with the refined, crisp clarity of elite software platforms. The target audience comprises maritime operators, port authorities, environmental defense teams, and autonomous vessel dispatchers who require split-second situational awareness, zero visual noise, and absolute data clarity.

The visual style merges ultra-clean modern enterprise minimalism with restrained oceanic glassmorphism. Interfaces feature wide open waterlines of whitespace, sharp structural slate delineations, and layered micro-surfaces that evoke high-tech hydrographic instrumentation. The overall emotional tone is authoritative, sovereign, technologically superior, and ecological—signaling precision tracking, operational control, and environmental guardianship.

## Colors

The palette is rooted in marine topography and oceanic atmospheric layers:

- **Canvas & Backing**: The foundational canvas uses an airy, ultra-pure sea-mist tint (`#FAFCFF`), layered with pure optical white (`#FFFFFF`) on elevated surfaces to maximize contrast and focus.
- **Primary (Abyssal Navy - `#0A2540`)**: The dominant anchor for all primary navigation, commanding headers, structural dividers, and primary interaction targets. Delivers institutional authority and high legibility.
- **Secondary (Marine Teal - `#0D9488`)**: Represents successful environmental recovery, system health, sensor sync states, and affirmative actions. 
- **Tertiary (Azure Ocean - `#0284C7` & `#0EA5E9`)**: High-visibility maritime beacon color. Used for active telemetry pulses, vessel trajectories, interactive selections, and real-time AI detection bounding envelopes.
- **Atmospheric Foams (`#E0F2FE`, `#F0F9FF`)**: Soft, desaturated surface fills that distinguish sonar passes, status pills, and tactical map overlays without overwhelming typography.
- **Structure & Borders (`#E2E8F0`)**: Low-contrast, hairline slate contours that maintain rigid grid alignment across high-density telemetry dashboards.

## Typography

Typography balances humanistic executive presentation with mission-critical instrumentation:

- **Executive & Interface Typography (`Plus Jakarta Sans`)**: Applied across structural headlines, body copy, and UI controls. Its geometric clarity prevents fatigue during multi-hour operational monitoring while maintaining an uncompromising, modern executive polish.
- **Telemetry & Coordinate Data (`JetBrains Mono`)**: Strict rule: all geographic coordinates, AIS transponder payloads, ocean debris density metrics, timestamps, speed/heading calculations, and bounding box confidences must render in `JetBrains Mono`. Monospaced tabular alignment ensures zero layout jitter when live telemetry streams update.
- **Casing Rules**: Operational badges, table column headers, and telemetry keys use `label-caps` in all-caps formatting with deliberate tracking (+0.08em) to ensure immediate scannability against high-density situational maps.

## Layout & Spacing

The layout is built on a 12-column fluid-grid architecture that supports complex telemetry split-screens, dynamic cartographic consoles, and tabular dispatch ledgers. 

- **Grid Architecture**: 
  - **Desktop (1280px+)**: 12 columns, 24px (`1.5rem`) gutters, 32px (`2rem`) edge margins. Designed for wide operational panels featuring fixed 320px telemetry navigation drawers and multi-column visual tracking viewports.
  - **Tablet (768px - 1279px)**: 8 columns, 16px gutters, 24px edge margins. Side panels collapse into layered slide-over sheets.
  - **Mobile (<768px)**: 4 columns, 12px gutters, 16px edge margins. Horizontal card carousels replace multi-axis comparison tables.
- **Vertical Spacing Rhythm**: Strict 4px/8px incremental base rhythm. Component groupings use internal padding of `space-md` (16px) or `space-lg` (24px). Macro screen divisions rely on `space-xl` (40px) to preserve an expansive oceanic whitespace profile and eliminate visual clutter.

## Elevation & Depth

Visual hierarchy uses crisp hairline borders paired with diffused, sea-tinted ambient depth rather than heavy physical drops:

- **Base Layer (Elevation 0)**: Flat `#FAFCFF` background canvas. 
- **Card & Console Layer (Elevation 1)**: Flat `#FFFFFF` surface framed by a 1px crisp outline of `#E2E8F0`. Subtle oceanic ambient tint: `0 1px 3px rgba(10, 37, 64, 0.04), 0 6px 16px rgba(10, 37, 64, 0.02)`.
- **Floating Overlays & Telemetry Tooltips (Elevation 2)**: Translucent `#FFFFFF` (92% opacity) treated with `backdrop-filter: blur(12px)`. Enclosed by a 1px hairline border of `rgba(2, 132, 199, 0.15)`. Drop shadow: `0 8px 24px -4px rgba(10, 37, 64, 0.08), 0 2px 6px -1px rgba(10, 37, 64, 0.04)`.
- **Modals & Critical Intervention Sheets (Elevation 3)**: Pure `#FFFFFF` floating plane atop a dark marine veil (`#0A2540` at 40% opacity with 4px background blur). Box shadow: `0 20px 48px -8px rgba(10, 37, 64, 0.18)`.

## Shapes

The shape system adopts a balanced geometry (`roundedness: 2` / 8px standard corner radius), blending enterprise software precision with hydrodynamic organic curvature:

- **Standard Elements (8px / 0.5rem)**: Standard buttons, input controls, metric readouts, telemetry cards, and operational dropdown menus.
- **Containers & Viewports (16px / 1rem - `rounded-lg`)**: Primary analytics dashboards, map overlays, camera feeds, and multi-vessel dispatch pods.
- **Telemetry Indicators & Badges**: Fully pill-shaped (`9999px`) for target acquisition statuses, debris classification tags, AIS operational modes, and battery/fuel reserves.

## Components

### Buttons & Interactive Triggers
- **Primary Operational Button**: Background `#0A2540`, text `#FFFFFF`, border-radius 8px, padding 10px 20px. Hover state: `#0284C7` transition (200ms ease). Active state: `#081C30`.
- **Action Teal Button**: Background `#0D9488`, text `#FFFFFF`. Reserved for confirmation of cleanup dispatches, vessel launches, and resolved target flags.
- **Secondary Ghost Button**: Transparent background, 1px solid `#E2E8F0`, text `#0A2540`. Hover: `#F0F9FF` background with `#0284C7` border.
- **Telemetry Action Button**: Monospace label, icon-prefixed, compact 32px height, slate border, subtle hover glow using `#E0F2FE`.

### Chips & Tactical Status Badges
- **Pill Silhouette**: 24px height, padding 4px 10px, typography `telemetry-sm`.
- **Critical Debris Alert**: Background `#FEF2F2`, border 1px solid `#FECACA`, text `#DC2626`, accompanied by an animated live pulse dot.
- **Autonomous Sync/Clean**: Background `#F0FDFA`, border 1px solid `#CCFBF1`, text `#0D9488`.
- **En Route / Tracking**: Background `#F0F9FF`, border 1px solid `#BAE6FD`, text `#0284C7`.

### Lists & Telemetry Feeds
- Zebra striping is prohibited. Row separation uses hairline borders (`1px solid #F1F5F9`).
- Hover state on rows applies an instant transition to `#F8FAFC` paired with a 2px left border accent in `#0284C7`.
- Cell alignments strictly adhere to content type: text left-aligned, numeric and coordinate data right-aligned in `JetBrains Mono`.

### Input Fields & Search Consoles
- Height: 42px. Background: `#FFFFFF`. Border: 1px solid `#E2E8F0`. Typography: `body-md`.
- Focus State: Zero heavy outlines. Replaced by a crisp 1px border of `#0284C7` and a soft ambient focus ring (`0 0 0 3px rgba(2, 132, 199, 0.12)`).
- Input Icons: 16px slate monochrome icons (`#64748B`), shifting to `#0284C7` upon focus.

### Checkboxes & Segmented Selectors
- Custom 18px square checkboxes with 4px border-radius. Inactive border: 1.5px solid `#CBD5E1`. Checked state: `#0A2540` fill with white checkmark.
- Segmented Vessel Toggles: Pill container in `#F1F5F9` with a floating white active capsule enclosed by a 1px border of `#E2E8F0`.

### Cards & Telemetry Containers
- Background `#FFFFFF`, 1px solid `#E2E8F0`, 16px border-radius, padding 20px.
- Internal Card Headers: Monospace uppercase metadata label on top, primary metric display below in `headline-md`, completed with an integrated sparkline or sonar coordinate footprint.

### Specialized Maritime Components
- **Sonar / Vision Coordinate HUD**: Translucent slate container with a subtle linear-gradient oceanic top bar (`#0284C7` to `#0D9488`), integrating live latitude, longitude, sea-state index, and computer-vision confidence levels.
- **Debris Classification Bounding Overlay**: Thin 1.5px crisp azure border (`#0EA5E9`) surrounding detected objects with an attached floating glass tag displaying debris material classification and mass estimation.