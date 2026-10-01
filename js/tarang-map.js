/**
 * TARANG Common Leaflet Map Engine
 * Reusable across Survey Operator, Sonar Analyst, Marine Portal, Government Portal, and Public Portal.
 * Zero external API key dependencies (key-free tile providers + Leaflet 1.9.x).
 *
 * MAP_CONFIG below is the single source of truth for tile providers, map
 * defaults, marker/route styling and maritime units. Portals must not define
 * their own tile URLs — load this file and use MAP_CONFIG / TarangMap /
 * TarangTiles instead.
 */

// ─────────────────────────────────────────────────────────────────────────────
// MAP_CONFIG — one frozen place where the tile provider chain is configured.
// ─────────────────────────────────────────────────────────────────────────────
const MAP_CONFIG = Object.freeze({
  defaultCenter: Object.freeze([8.50, 72.50]), // Indian Ocean / Arabian Sea (TARANG demo survey region)
  defaultZoom: 11,
  minZoom: 3,
  maxZoom: 18,

  // Primary provider — no API key required.
  primaryProvider: Object.freeze({
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors | TARANG Hydrographic Engine',
    maxZoom: 19,
    subdomains: 'abc'
  }),

  // Ordered key-free fallbacks, tried automatically when a provider fails tiles.
  fallbacks: Object.freeze([
    Object.freeze({
      name: 'CARTO Voyager',
      url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19,
      subdomains: 'abcd'
    }),
    Object.freeze({
      name: 'CARTO Light',
      url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19,
      subdomains: 'abcd'
    }),
    Object.freeze({
      name: 'OpenTopoMap',
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attribution: '&copy; OpenStreetMap contributors, SRTM | &copy; OpenTopoMap (CC-BY-SA)',
      maxZoom: 17,
      subdomains: 'abc'
    })
  ]),

  tileErrorThreshold: 3, // failed tiles tolerated before switching provider
  tileUnavailableMessage: 'Map tiles unavailable. Geospatial data remains available.',

  markers: Object.freeze({
    startColor: '#10b981',
    endColor: '#0284c7',
    platformColor: '#0284c7',
    routeStopColor: '#0f766e',
    detectionColors: Object.freeze({
      ghost_net: '#e11d48',
      shipwreck: '#0284c7',
      crab_pot: '#d97706',
      submarine_pipeline: '#0d9488',
      mine_cylinder: '#7c3aed',
      unknown: '#64748b'
    })
  }),

  route: Object.freeze({          // survey track polyline
    color: '#0284c7',
    weight: 3.5,
    opacity: 0.85,
    dashArray: '4, 4'
  }),

  cleanupRoute: Object.freeze({   // optimized cleanup route polyline
    color: '#0f766e',
    weight: 4,
    opacity: 0.9,
    dashArray: null
  }),

  units: Object.freeze({
    primary: 'NM',
    secondary: 'km',
    METERS_PER_NM: 1852
  })
});

// ─────────────────────────────────────────────────────────────────────────────
// TarangUnits — nautical-mile helpers (1 NM = 1852 m). NM is always primary.
// ─────────────────────────────────────────────────────────────────────────────
const TarangUnits = {
  METERS_PER_NM: MAP_CONFIG.units.METERS_PER_NM,

  metersToNm(meters) { return (Number(meters) || 0) / this.METERS_PER_NM; },
  kmToNm(km) { return ((Number(km) || 0) * 1000) / this.METERS_PER_NM; },
  nmToKm(nm) { return (Number(nm) || 0) * (this.METERS_PER_NM / 1000); },
  nmToMeters(nm) { return (Number(nm) || 0) * this.METERS_PER_NM; },

  /** formats a metric distance as e.g. "2.43 NM (4.50 km)" */
  formatNm(meters) { return this.formatDistance(this.metersToNm(meters)); },

  /** NM primary, km secondary. km is derived from nm when omitted. */
  formatDistance(nm, km) {
    const n = Number(nm) || 0;
    const k = (km === undefined || km === null) ? this.nmToKm(n) : (Number(km) || 0);
    return `${n.toFixed(2)} NM (${k.toFixed(2)} km)`;
  },

  /** Great-circle distance between two [lat, lon] pairs, in meters. */
  haversineMeters(a, b) {
    const R = 6371008.8; // mean Earth radius (m)
    const toRad = v => (v * Math.PI) / 180;
    const dLat = toRad(b[0] - a[0]);
    const dLon = toRad(b[1] - a[1]);
    const s = Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(s));
  },

  /** Total length of an ordered [lat, lon] polyline, in meters. */
  polylineLengthMeters(points) {
    const pts = (points || []).filter(p => Array.isArray(p) && p.length >= 2 && !isNaN(p[0]) && !isNaN(p[1]));
    let total = 0;
    for (let i = 1; i < pts.length; i++) total += this.haversineMeters(pts[i - 1], pts[i]);
    return total;
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// TarangTiles — automatic tile-provider fallback with a visible failure state.
// Attach to ANY Leaflet map: TarangTiles.attach(map). Vector layers (markers,
// polylines, polygons, popups) keep working even when all tile providers fail.
// ─────────────────────────────────────────────────────────────────────────────
class TarangTileController {
  constructor(map) {
    this.map = map;
    this.providers = [MAP_CONFIG.primaryProvider].concat(MAP_CONFIG.fallbacks);
    this.index = -1;
    this.layer = null;
    this.state = 'ok'; // 'ok' | 'fallback' | 'unavailable'
    this.banner = null;
    this.loadProvider(0);
  }

  loadProvider(index) {
    if (index >= this.providers.length) {
      this.markUnavailable();
      return;
    }
    this.index = index;
    const provider = this.providers[index];
    console.info(`TarangMap: attaching tile provider "${provider.name}" (${index === 0 ? 'primary' : 'fallback ' + index + ' of ' + (this.providers.length - 1)}).`);

    if (this.layer) {
      try { this.map.removeLayer(this.layer); } catch (e) { /* already detached */ }
      this.layer = null;
    }

    let errorCount = 0;
    let switched = false;
    const layer = L.tileLayer(provider.url, {
      maxZoom: provider.maxZoom,
      attribution: provider.attribution,
      subdomains: provider.subdomains
    });

    layer.on('tileerror', () => {
      errorCount += 1;
      if (!switched && errorCount >= MAP_CONFIG.tileErrorThreshold) {
        switched = true;
        console.warn(`TarangMap: tile provider "${provider.name}" failed ${errorCount} tile(s) — trying next provider.`);
        if (this.layer === layer) this.loadProvider(index + 1);
      }
    });
    layer.on('tileload', () => {
      if (this.layer === layer) this.hideBanner();
    });

    // Assign before addTo so synchronous tileerror events can cascade safely.
    this.layer = layer;
    this.state = index === 0 ? 'ok' : 'fallback';
    layer.addTo(this.map);
  }

  markUnavailable() {
    if (this.layer) {
      try { this.map.removeLayer(this.layer); } catch (e) { /* already detached */ }
      this.layer = null;
    }
    this.state = 'unavailable';
    console.error('TarangMap: every configured tile provider failed. Geospatial vector data remains available.');
    this.showBanner();
  }

  showBanner() {
    if (this.banner || !this.map) return;
    const container = this.map.getContainer();
    if (!container) return;
    this.banner = document.createElement('div');
    this.banner.className = 'tarang-tile-failure-banner';
    this.banner.setAttribute('role', 'status');
    this.banner.textContent = MAP_CONFIG.tileUnavailableMessage;
    this.banner.style.cssText = 'position:absolute;top:0;left:0;right:0;z-index:1000;pointer-events:none;' +
      'background:rgba(15,23,42,0.9);color:#fecaca;font:700 12px "Space Grotesk",monospace;' +
      'letter-spacing:.04em;text-align:center;padding:8px 12px;border-bottom:2px solid #e11d48;';
    container.appendChild(this.banner);
  }

  hideBanner() {
    if (this.banner) {
      this.banner.remove();
      this.banner = null;
    }
  }

  getTileStatus() {
    const provider = this.providers[this.index];
    return { provider: provider ? provider.name : null, state: this.state };
  }
}

const TarangTiles = {
  /** Attaches the MAP_CONFIG provider chain (with fallback) to a Leaflet map. */
  attach(map) {
    const controller = new TarangTileController(map);
    map._tarangTiles = controller;
    return controller;
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// TarangExport — authenticated JSON downloads (fetch + Blob so the auth.js
// Authorization header is attached; direct-link navigation only as fallback).
// ─────────────────────────────────────────────────────────────────────────────
const TarangExport = {
  async downloadJson(url, filename) {
    const name = filename || url.split('/').pop().split('?')[0] || 'tarang-export.json';
    try {
      const response = await fetch(url);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.message || `Export request failed (HTTP ${response.status}).`);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
      return { ok: true };
    } catch (error) {
      console.warn('TarangExport: authenticated download failed, falling back to a direct link.', error);
      const link = document.createElement('a');
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      return { ok: false, error: error.message || String(error) };
    }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// TarangRouteUI — shared ordered cleanup-route sequence panel renderer.
// ─────────────────────────────────────────────────────────────────────────────
const TarangRouteUI = {
  escape(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  },

  legDistanceNm(route, stop) {
    const legs = (route && route.legs) || [];
    const byTo = legs.find(l => l.to && (l.to === stop.id || l.to === stop.label));
    const leg = byTo || legs.find(l => l.sequence === stop.sequence);
    return leg && leg.distance_nm != null ? Number(leg.distance_nm) : null;
  },

  /** Ordered Start → HS-x → HS-y hotspot selection panel.
   *  Columns (req 28): Hotspot ID, Latitude, Longitude, Detections, Priority,
   *  Distance from survey-start (NM, cumulative along the route), and Distance
   *  to the next hotspot (NM). All values come from the persisted route's real
   *  legs/target_sequence — nothing is hardcoded or randomly generated. */
  sequenceHtml(route) {
    const esc = this.escape;
    if (!route) {
      return '<div class="text-xs font-mono text-slate-500">No cleanup route generated yet.</div>';
    }
    const stops = (route.target_sequence || []).filter(s => !s.is_start);
    const legs = route.legs || [];
    const legBySeq = {};
    legs.forEach(l => { if (l && l.sequence != null) legBySeq[l.sequence] = l; });

    const parts = [];
    parts.push(`<div style="font-weight:800;letter-spacing:.06em;margin-bottom:6px;">CLEANUP ROUTE (${esc(route.algorithm || 'optimized heuristic')})</div>`);

    if (route.start_point && route.start_point.latitude != null) {
      parts.push(`<div style="font-size:11px;opacity:.8;margin-bottom:6px;">Survey start: ${Number(route.start_point.latitude).toFixed(5)}, ${Number(route.start_point.longitude).toFixed(5)}</div>`);
    } else {
      parts.push('<div style="font-size:11px;opacity:.7;margin-bottom:6px;">Survey start point unavailable — cumulative distances are measured along the optimized route order.</div>');
    }

    if (!stops.length) {
      parts.push('<div style="font-size:11px;opacity:.7;">No hotspots in this route.</div>');
      return parts.join('');
    }

    let cumulativeNm = 0;
    const rows = stops.map((stop, i) => {
      const arriveLeg = legBySeq[stop.sequence];
      if (arriveLeg && arriveLeg.distance_nm != null) cumulativeNm += Number(arriveLeg.distance_nm);
      const nextLeg = legBySeq[Number(stop.sequence) + 1];
      return {
        stop,
        fromStartNm: cumulativeNm,
        toNextNm: (nextLeg && nextLeg.distance_nm != null) ? Number(nextLeg.distance_nm) : null,
        last: i === stops.length - 1
      };
    });

    const th = 'text-align:left;padding:3px 6px;border-bottom:1px solid rgba(100,116,139,.35);font-weight:700;white-space:nowrap;';
    const td = 'padding:3px 6px;border-bottom:1px solid rgba(100,116,139,.15);white-space:nowrap;';
    let table = '<div style="overflow-x:auto;"><table style="border-collapse:collapse;font-size:11px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;width:100%;">';
    table += '<thead><tr>'
      + `<th style="${th}">#</th>`
      + `<th style="${th}">Hotspot ID</th>`
      + `<th style="${th}">Latitude</th>`
      + `<th style="${th}">Longitude</th>`
      + `<th style="${th}">Detections</th>`
      + `<th style="${th}">Priority</th>`
      + `<th style="${th}">From Start (NM)</th>`
      + `<th style="${th}">To Next (NM)</th>`
      + '</tr></thead><tbody>';
    rows.forEach(r => {
      const s = r.stop;
      const prioColor = s.priority === 'High' ? '#e11d48' : (s.priority === 'Medium' ? '#d97706' : '#475569');
      const toNextCell = r.last
        ? '<span style="opacity:.7;">Final hotspot in route</span>'
        : (r.toNextNm != null ? r.toNextNm.toFixed(2) : '—');
      table += '<tr>'
        + `<td style="${td}">${esc(s.sequence)}</td>`
        + `<td style="${td}font-weight:700;">${esc(s.label || s.id)}</td>`
        + `<td style="${td}">${s.latitude != null ? Number(s.latitude).toFixed(5) : '—'}</td>`
        + `<td style="${td}">${s.longitude != null ? Number(s.longitude).toFixed(5) : '—'}</td>`
        + `<td style="${td}">${s.detection_count != null ? esc(s.detection_count) : '—'}</td>`
        + `<td style="${td}color:${prioColor};font-weight:700;">${esc(s.priority || '—')}</td>`
        + `<td style="${td}">${r.fromStartNm.toFixed(2)}</td>`
        + `<td style="${td}">${toNextCell}</td>`
        + '</tr>';
    });
    table += '</tbody></table></div>';
    parts.push(table);

    parts.push(`<div style="font-weight:800;margin-top:8px;">TOTAL: ${esc(TarangUnits.formatDistance(route.total_distance_nm, route.total_distance_km))}</div>`);
    if (route.estimated_travel_minutes != null) {
      parts.push(`<div style="opacity:.75;font-size:11px;">Estimated travel: ${Math.round(Number(route.estimated_travel_minutes))} min at ${esc(route.planning_speed_knots != null ? route.planning_speed_knots + ' knots' : 'planning speed')}</div>`);
    }
    return parts.join('');
  }
};

class TarangMap {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = Object.assign({
      center: MAP_CONFIG.defaultCenter.slice(), // Default: Indian Ocean / Arabian Sea (8.50N 72.50E) — auto-pans to data when loaded
      zoom: MAP_CONFIG.defaultZoom,
      minZoom: MAP_CONFIG.minZoom,
      maxZoom: MAP_CONFIG.maxZoom,
      readOnly: false,
      publicMode: false,
      defaultEmptyMsg: 'No spatial survey data available.'
    }, options);

    this.map = null;
    this.tiles = null;
    this.trackLayer = null;
    this.detectionsLayer = null;
    this.clustersLayer = null;
    this.routeLayer = null;
    this.platformMarker = null;
    this.emptyOverlay = null;

    this.init();
  }

  init() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      console.warn(`TarangMap: Container #${this.containerId} not found in DOM.`);
      return;
    }

    // Ensure Leaflet is loaded
    if (typeof L === 'undefined') {
      console.error('TarangMap: Leaflet (L) library is required.');
      return;
    }

    // Remove old Leaflet instance if already initialized on this element
    if (container._leaflet_id) {
      container._leaflet_id = null;
    }

    this.map = L.map(this.containerId, {
      center: this.options.center,
      zoom: this.options.zoom,
      minZoom: this.options.minZoom,
      maxZoom: this.options.maxZoom,
      zoomControl: !this.options.readOnly
    });

    // Base tiles from MAP_CONFIG with automatic provider fallback.
    this.tiles = TarangTiles.attach(this.map);

    // Layer groups
    this.trackLayer = L.layerGroup().addTo(this.map);
    this.detectionsLayer = L.layerGroup().addTo(this.map);
    this.clustersLayer = L.layerGroup().addTo(this.map);
    this.routeLayer = L.layerGroup().addTo(this.map);

    // Invalidate size on load / resize
    setTimeout(() => {
      if (this.map) this.map.invalidateSize();
    }, 250);
  }

  /**
   * Sets and renders a survey track with START and END markers.
   * trackPoints: Array of [lat, lon]
   */
  setTrack(trackPoints, metadata = {}) {
    if (!this.map || !this.trackLayer) return;
    this.trackLayer.clearLayers();

    if (!trackPoints || trackPoints.length === 0) return;

    // Filter valid coordinates
    const validPoints = trackPoints.filter(pt => Array.isArray(pt) && pt.length >= 2 && !isNaN(pt[0]) && !isNaN(pt[1]));
    if (validPoints.length === 0) return;

    // Polyline (styling centralized in MAP_CONFIG.route)
    const polyline = L.polyline(validPoints, Object.assign({}, MAP_CONFIG.route)).addTo(this.trackLayer);

    // Real survey-track length derived from the coordinates (NM primary)
    const trackLengthText = TarangUnits.formatNm(TarangUnits.polylineLengthMeters(validPoints));

    // START Marker (Green Pill)
    const startPt = validPoints[0];
    const startIcon = L.divIcon({
      className: 'tarang-start-marker',
      html: `<div style="background:${MAP_CONFIG.markers.startColor}; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 2px 8px rgba(16,185,129,0.4); display:flex; align-items:center; gap:3px;">
              <span>●</span> START
             </div>`,
      iconSize: [60, 20],
      iconAnchor: [30, 10]
    });
    L.marker(startPt, { icon: startIcon })
      .addTo(this.trackLayer)
      .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Survey Track Origin</strong><br/>Lat: ${startPt[0].toFixed(4)}°N<br/>Lon: ${startPt[1].toFixed(4)}°E<br/>Survey Track Length: <strong>${trackLengthText}</strong></div>`);

    // END Marker (if more than 1 point)
    if (validPoints.length > 1) {
      const endPt = validPoints[validPoints.length - 1];
      const endIcon = L.divIcon({
        className: 'tarang-end-marker',
        html: `<div style="background:${MAP_CONFIG.markers.endColor}; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 2px 8px rgba(2,132,199,0.4); display:flex; align-items:center; gap:3px;">
                <span>■</span> END
               </div>`,
        iconSize: [52, 20],
        iconAnchor: [26, 10]
      });
      L.marker(endPt, { icon: endIcon })
        .addTo(this.trackLayer)
        .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Survey Track Terminus</strong><br/>Lat: ${endPt[0].toFixed(4)}°N<br/>Lon: ${endPt[1].toFixed(4)}°E<br/>Survey Track Length: <strong>${trackLengthText}</strong></div>`);
    }

    this.fitBounds();
  }

  /**
   * Sets current simulated or live platform position (AUV/Drone)
   */
  setPlatformPosition(lat, lon, heading = 0) {
    if (!this.map || !this.trackLayer) return;

    if (this.platformMarker) {
      this.platformMarker.setLatLng([lat, lon]);
    } else {
      const platformIcon = L.divIcon({
        className: 'tarang-platform-marker',
        html: `<div style="position:relative; width:22px; height:22px;">
                <div style="position:absolute; inset:0; background:#0284c7; opacity:0.35; border-radius:50%; animation:ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
                <div style="position:relative; width:22px; height:22px; background:#0284c7; border:2.5px solid #ffffff; border-radius:50%; box-shadow:0 2px 10px rgba(2,132,199,0.6); display:flex; align-items:center; justify-content:center; color:#fff; font-size:11px;">▲</div>
               </div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });
      this.platformMarker = L.marker([lat, lon], { icon: platformIcon }).addTo(this.trackLayer);
      this.platformMarker.bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Active Survey Platform</strong><br/><span style="color:#0284c7; font-weight:700;">SIMULATION DATA</span></div>`);
    }
  }

  /**
   * Loads and displays acoustic detections with distinct class colors and verification status rings.
   */
  setDetections(detections, onSelect = null) {
    if (!this.map || !this.detectionsLayer) return;
    this.detectionsLayer.clearLayers();

    if (!detections || detections.length === 0) return;

    // Class colors centralized in MAP_CONFIG.markers.detectionColors
    const classColors = MAP_CONFIG.markers.detectionColors;

    detections.forEach(d => {
      let lat = parseFloat(d.latitude);
      let lon = parseFloat(d.longitude);
      if (isNaN(lat) || isNaN(lon) || (lat === 0 && lon === 0)) return;

      const cls = (d.class_name || d.title || 'unknown').toLowerCase();
      let color = classColors['unknown'];
      for (const [k, c] of Object.entries(classColors)) {
        if (cls.includes(k)) { color = c; break; }
      }

      const isVerified = (d.verification_status || '').toLowerCase() === 'verified';
      const border = isVerified ? '3px solid #0d9488' : '2px solid #ffffff';
      const shadow = isVerified ? '0 0 10px rgba(13,148,136,0.6)' : '0 2px 6px rgba(0,0,0,0.3)';

      const markerHtml = `
        <div style="background:${color}; width:16px; height:16px; border-radius:50%; border:${border}; box-shadow:${shadow}; cursor:pointer;" title="${d.title || d.class_name}">
        </div>
      `;

      const icon = L.divIcon({
        className: 'tarang-det-icon',
        html: markerHtml,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });

      const m = L.marker([lat, lon], { icon: icon }).addTo(this.detectionsLayer);

      const statusBadge = isVerified 
        ? `<span style="background:#ccfbf1; color:#0f766e; padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px;">VERIFIED TARGET</span>`
        : `<span style="background:#fef3c7; color:#b45309; padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px;">AI DETECTED</span>`;

      const confText = d.confidence ? `Conf: <strong>${Math.round(d.confidence > 1 ? d.confidence : d.confidence * 100)}%</strong><br/>` : '';
      const depthText = d.depth ? `Depth: ${d.depth}m<br/>` : '';

      const latDisplay = this.options.publicMode ? `${lat.toFixed(2)}°N (Generalized)` : `${lat.toFixed(4)}°N`;
      const lonDisplay = this.options.publicMode ? `${lon.toFixed(2)}°E (Generalized)` : `${lon.toFixed(4)}°E`;

      m.bindPopup(`
        <div style="font-family:Inter, sans-serif; font-size:12px; min-width:180px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <strong style="color:#0f172a; font-size:13px;">${d.title || d.class_name}</strong>
          </div>
          <div style="margin-bottom:6px;">${statusBadge}</div>
          <div style="font-size:11px; color:#475569; font-family:Space Grotesk, monospace; line-height:1.5;">
            ID: ${d.id}<br/>
            ${confText}
            ${depthText}
            Coords: ${latDisplay}, ${lonDisplay}
          </div>
        </div>
      `);

      if (typeof onSelect === 'function') {
        m.on('click', () => onSelect(d));
      }
    });
  }

  /**
   * Loads and displays DBSCAN clusters with semi-transparent boundaries and cluster summary badges.
   */
  setClusters(clusterData) {
    if (!this.map || !this.clustersLayer) return;
    this.clustersLayer.clearLayers();

    if (!clusterData || !clusterData.clusters || clusterData.clusters.length === 0) return;

    clusterData.clusters.forEach(c => {
      const center = c.center;
      if (!center || isNaN(center[0]) || isNaN(center[1])) return;

      const radiusMeters = Math.max(c.radius_meters || 150, 100);

      // Cluster extent circle
      L.circle(center, {
        radius: radiusMeters,
        color: '#0284c7',
        fillColor: '#0284c7',
        fillOpacity: 0.12,
        weight: 1.5,
        dashArray: '3, 4'
      }).addTo(this.clustersLayer);

      // Cluster Center Badge
      const badgeIcon = L.divIcon({
        className: 'tarang-cluster-badge',
        html: `<div style="background:#0284c7; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:3px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 3px 10px rgba(2,132,199,0.4); white-space:nowrap; cursor:pointer;">
                ${c.cluster_id}: ${c.count} targets
               </div>`,
        iconSize: [110, 24],
        iconAnchor: [55, 12]
      });

      const badgeMarker = L.marker(center, { icon: badgeIcon }).addTo(this.clustersLayer);
      badgeMarker.bindPopup(`
        <div style="font-family:Inter, sans-serif; font-size:12px; min-width:200px;">
          <div style="font-weight:800; font-size:13px; color:#0f172a; margin-bottom:2px;">${c.cluster_id} (DBSCAN Cluster)</div>
          <p style="font-size:11px; color:#64748b; margin-bottom:6px;">Concentration of spatially grouped acoustic anomalies.</p>
          <div style="font-family:Space Grotesk, monospace; font-size:11px; line-height:1.6; background:#f8fafc; padding:6px; border-radius:6px; border:1px solid #e2e8f0;">
            <div>Total Targets: <strong>${c.count}</strong></div>
            <div>Dominant Class: <strong style="color:#0284c7;">${c.dominant_class}</strong></div>
            <div>Verified Targets: <strong style="color:#0d9488;">${c.verified_count}</strong></div>
            <div>Radial Extent: <strong>${radiusMeters.toFixed(0)} meters</strong></div>
          </div>
        </div>
      `);
    });
  }

  /**
   * Renders an optimized cleanup route from the /api/v1/hotspot-route payload:
   * ordered polyline + numbered hotspot markers + Start Point marker.
   */
  setCleanupRoute(route) {
    if (!this.map || !this.routeLayer) return;
    this.routeLayer.clearLayers();
    if (!route) return;

    const coords = (route.route_coordinates || [])
      .filter(pt => Array.isArray(pt) && pt.length >= 2 && !isNaN(pt[0]) && !isNaN(pt[1]));

    if (coords.length > 1) {
      const line = L.polyline(coords, Object.assign({}, MAP_CONFIG.cleanupRoute)).addTo(this.routeLayer);
      line.bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Cleanup Route</strong><br/>Algorithm: ${route.algorithm || 'optimized heuristic'}<br/>Total: <strong>${TarangUnits.formatDistance(route.total_distance_nm, route.total_distance_km)}</strong></div>`);
    }

    // Start Point marker (survey start, when the API provides one)
    const start = route.start_point;
    if (start && start.latitude != null && start.longitude != null) {
      const startIcon = L.divIcon({
        className: 'tarang-route-start-marker',
        html: `<div style="background:${MAP_CONFIG.markers.startColor}; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 2px 8px rgba(16,185,129,0.4);">● START</div>`,
        iconSize: [60, 20],
        iconAnchor: [30, 10]
      });
      L.marker([Number(start.latitude), Number(start.longitude)], { icon: startIcon })
        .addTo(this.routeLayer)
        .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Start Point</strong><br/>Lat: ${Number(start.latitude).toFixed(4)}°N<br/>Lon: ${Number(start.longitude).toFixed(4)}°E</div>`);
    }

    // Numbered hotspot markers in visit order
    (route.target_sequence || []).forEach(stop => {
      const lat = Number(stop.latitude);
      const lon = Number(stop.longitude);
      if (isNaN(lat) || isNaN(lon)) return;
      const stopIcon = L.divIcon({
        className: 'tarang-route-stop-marker',
        html: `<div style="width:22px;height:22px;border-radius:50%;background:${MAP_CONFIG.markers.routeStopColor};color:#fff;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;font:700 10px Space Grotesk,monospace;">${stop.sequence}</div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });
      const nm = TarangRouteUI.legDistanceNm(route, stop);
      const legText = nm != null ? `Leg distance: <strong>${nm.toFixed(2)} NM</strong><br/>` : '';
      const classes = (stop.target_classes || []).join(', ');
      L.marker([lat, lon], { icon: stopIcon })
        .addTo(this.routeLayer)
        .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px; min-width:190px;">
            <strong>Hotspot ${stop.label || stop.id}</strong><br/>
            <span style="font-family:Space Grotesk, monospace; font-size:11px; color:#475569; line-height:1.5;">
            Sequence: #${stop.sequence}<br/>
            ${legText}
            Sonar Detections: ${stop.detection_count != null ? stop.detection_count : '–'}<br/>
            Priority: ${stop.priority || '–'}<br/>
            Latitude: ${lat.toFixed(4)}°N<br/>
            Longitude: ${lon.toFixed(4)}°E
            ${classes ? `<br/>Target classes: ${classes}` : ''}
            </span></div>`);
    });

    this.fitBounds();
  }

  /**
   * Fits map to visible markers and tracks
   */
  fitBounds(padding = 0.2) {
    if (!this.map) return;
    const bounds = L.latLngBounds([]);

    this.trackLayer.eachLayer(l => {
      if (l.getBounds) bounds.extend(l.getBounds());
      else if (l.getLatLng) bounds.extend(l.getLatLng());
    });

    this.detectionsLayer.eachLayer(l => {
      if (l.getLatLng) bounds.extend(l.getLatLng());
    });

    this.clustersLayer.eachLayer(l => {
      if (l.getBounds) bounds.extend(l.getBounds());
      else if (l.getLatLng) bounds.extend(l.getLatLng());
    });

    if (this.routeLayer) {
      this.routeLayer.eachLayer(l => {
        if (l.getBounds) bounds.extend(l.getBounds());
        else if (l.getLatLng) bounds.extend(l.getLatLng());
      });
    }

    if (bounds.isValid()) {
      this.map.fitBounds(bounds.pad(padding));
    }
  }

  /** Tile provider health: {provider, state:'ok'|'fallback'|'unavailable'} */
  getTileStatus() {
    return this.tiles
      ? this.tiles.getTileStatus()
      : { provider: null, state: 'unavailable' };
  }

  clear() {
    if (this.trackLayer) this.trackLayer.clearLayers();
    if (this.detectionsLayer) this.detectionsLayer.clearLayers();
    if (this.clustersLayer) this.clustersLayer.clearLayers();
    if (this.routeLayer) this.routeLayer.clearLayers();
    this.platformMarker = null;
  }
}

window.MAP_CONFIG = MAP_CONFIG;
window.TarangUnits = TarangUnits;
window.TarangTiles = TarangTiles;
window.TarangExport = TarangExport;
window.TarangRouteUI = TarangRouteUI;
window.TarangMap = TarangMap;
