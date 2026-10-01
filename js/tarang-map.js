/**
 * TARANG Common Leaflet Map Engine
 * Reusable across Operator, Sonar Analyst, Marine Analyst, Government, and Public Portals.
 * Zero external API key dependencies (OpenStreetMap + Leaflet 1.9.x).
 */

class TarangMap {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = Object.assign({
      center: [13.0827, 80.2707], // Default Indian Coast (Bay of Bengal / Chennai offshore)
      zoom: 11,
      minZoom: 3,
      maxZoom: 18,
      readOnly: false,
      publicMode: false,
      defaultEmptyMsg: 'No spatial survey data available.'
    }, options);

    this.map = null;
    this.trackLayer = null;
    this.detectionsLayer = null;
    this.clustersLayer = null;
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

    // Clean, high-availability OpenStreetMap base tiles (Light theme friendly)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors | TARANG Hydrographic Engine'
    }).addTo(this.map);

    // Layer groups
    this.trackLayer = L.layerGroup().addTo(this.map);
    this.detectionsLayer = L.layerGroup().addTo(this.map);
    this.clustersLayer = L.layerGroup().addTo(this.map);

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

    // Polyline
    const polyline = L.polyline(validPoints, {
      color: '#0284c7',
      weight: 3.5,
      opacity: 0.85,
      dashArray: '4, 4'
    }).addTo(this.trackLayer);

    // START Marker (Green Pill)
    const startPt = validPoints[0];
    const startIcon = L.divIcon({
      className: 'tarang-start-marker',
      html: `<div style="background:#10b981; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 2px 8px rgba(16,185,129,0.4); display:flex; align-items:center; gap:3px;">
              <span>●</span> START
             </div>`,
      iconSize: [60, 20],
      iconAnchor: [30, 10]
    });
    L.marker(startPt, { icon: startIcon })
      .addTo(this.trackLayer)
      .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Survey Track Origin</strong><br/>Lat: ${startPt[0].toFixed(4)}°N<br/>Lon: ${startPt[1].toFixed(4)}°E</div>`);

    // END Marker (if more than 1 point)
    if (validPoints.length > 1) {
      const endPt = validPoints[validPoints.length - 1];
      const endIcon = L.divIcon({
        className: 'tarang-end-marker',
        html: `<div style="background:#0284c7; color:#ffffff; font-family:Space Grotesk, monospace; font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 2px 8px rgba(2,132,199,0.4); display:flex; align-items:center; gap:3px;">
                <span>■</span> END
               </div>`,
        iconSize: [52, 20],
        iconAnchor: [26, 10]
      });
      L.marker(endPt, { icon: endIcon })
        .addTo(this.trackLayer)
        .bindPopup(`<div style="font-family:Inter, sans-serif; font-size:12px;"><strong>Survey Track Terminus</strong><br/>Lat: ${endPt[0].toFixed(4)}°N<br/>Lon: ${endPt[1].toFixed(4)}°E</div>`);
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

    const classColors = {
      'ghost_net': '#e11d48',
      'shipwreck': '#0284c7',
      'crab_pot': '#d97706',
      'submarine_pipeline': '#0d9488',
      'mine_cylinder': '#7c3aed',
      'unknown': '#64748b'
    };

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

    if (bounds.isValid()) {
      this.map.fitBounds(bounds.pad(padding));
    }
  }

  clear() {
    if (this.trackLayer) this.trackLayer.clearLayers();
    if (this.detectionsLayer) this.detectionsLayer.clearLayers();
    if (this.clustersLayer) this.clustersLayer.clearLayers();
    this.platformMarker = null;
  }
}

window.TarangMap = TarangMap;
