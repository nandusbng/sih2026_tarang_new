import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SimulationState, Vec3 } from '../data/types';
import { sampleSeabed, validPoint } from '../data/physics';

export interface Layers { terrain: boolean; track: boolean; beam: boolean; shadows: boolean; measurements: boolean }
export type CameraCommand = { kind: 'reset' | 'top' | 'focus'; sequence: number };
interface Props { state: SimulationState; selectedId: string | null; onSelect: (id: string) => void; layers: Layers; command: CameraCommand }

type AnimatedNode = { object: THREE.Object3D; material?: THREE.Material; mode: 'ring' | 'sweep' | 'drift' | 'beacon'; phase: number; size?: number };
type Engine = {
  scene: THREE.Scene; camera: THREE.PerspectiveCamera; controls: OrbitControls;
  dynamic: THREE.Group; terrain: THREE.Group; water: THREE.Group;
  labels: { element: HTMLElement; point: THREE.Vector3 }[]; labelHost: HTMLDivElement;
  animated: AnimatedNode[]; ambient: AnimatedNode[]; span: number; center: THREE.Vector3;
};

const vec = (point: Vec3) => new THREE.Vector3(point.x, point.z, -point.y);
const meter = (value: number | null) => value === null ? 'Not Available' : `${value.toFixed(1)} m`;
const cyan = 0x55f6df;
const amber = 0xffc36d;

function disposeMaterial(material: THREE.Material) {
  for (const value of Object.values(material)) if (value instanceof THREE.Texture) value.dispose();
  material.dispose();
}

function release(root: THREE.Object3D) {
  root.traverse(object => {
    const renderable = object as THREE.Object3D & { geometry?: THREE.BufferGeometry; material?: THREE.Material | THREE.Material[] };
    renderable.geometry?.dispose();
    if (renderable.material) (Array.isArray(renderable.material) ? renderable.material : [renderable.material]).forEach(disposeMaterial);
  });
  root.clear();
}

function line(points: THREE.Vector3[], color: number, dashed = false, opacity = 0.85) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = dashed
    ? new THREE.LineDashedMaterial({ color, dashSize: 1.25, gapSize: 0.85, transparent: true, opacity })
    : new THREE.LineBasicMaterial({ color, transparent: true, opacity });
  const result = new THREE.Line(geometry, material);
  result.computeLineDistances();
  return result;
}

function standardMesh(geometry: THREE.BufferGeometry, color: number, opacity = 1, roughness = 0.62) {
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.32, transparent: opacity < 1, opacity, side: THREE.DoubleSide }));
}

function makeGlow(color: string, size: number, opacity = 1) {
  const canvas = document.createElement('canvas');
  canvas.width = 96; canvas.height = 96;
  const context = canvas.getContext('2d');
  if (!context) return new THREE.Sprite(new THREE.SpriteMaterial({ color, transparent: true, opacity }));
  const gradient = context.createRadialGradient(48, 48, 1, 48, 48, 48);
  gradient.addColorStop(0, '#ffffff'); gradient.addColorStop(0.14, color); gradient.addColorStop(0.5, `${color}55`); gradient.addColorStop(1, `${color}00`);
  context.fillStyle = gradient; context.fillRect(0, 0, 96, 96);
  const material = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending });
  const sprite = new THREE.Sprite(material); sprite.scale.set(size, size, 1); return sprite;
}

function addRing(group: THREE.Group, center: THREE.Vector3, color: number, phase: number, animated: AnimatedNode[], size = 9) {
  const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.42, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false });
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.88, 1.05, 64), material);
  ring.position.copy(center); ring.rotation.x = -Math.PI / 2; group.add(ring);
  animated.push({ object: ring, material, mode: 'ring', phase, size });
}

function addParticles(group: THREE.Group, span: number, waterLevel: number, lowest: number, animated: AnimatedNode[]) {
  let seed = 11939;
  const random = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const count = Math.min(520, Math.max(180, Math.round(span * 2.2)));
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  for (let index = 0; index < count; index++) {
    positions[index * 3] = (random() - .5) * span * 1.35;
    positions[index * 3 + 1] = lowest + random() * Math.max(8, waterLevel - lowest);
    positions[index * 3 + 2] = (random() - .5) * span * 1.35;
    const brightness = .3 + random() * .7;
    colors[index * 3] = .09 * brightness; colors[index * 3 + 1] = .74 * brightness; colors[index * 3 + 2] = .8 * brightness;
  }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3)); geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  const material = new THREE.PointsMaterial({ size: 0.24, transparent: true, opacity: 0.36, vertexColors: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true });
  const points = new THREE.Points(geometry, material); group.add(points); animated.push({ object: points, material, mode: 'drift', phase: .4 });
}

function addRangeArcs(group: THREE.Group, center: THREE.Vector3, span: number) {
  const radius = Math.max(18, span * .14);
  for (let index = 1; index <= 4; index++) {
    const arc = new THREE.Mesh(new THREE.RingGeometry(radius * index - .08, radius * index + .08, 72, 1, Math.PI * .72, Math.PI * .56), new THREE.MeshBasicMaterial({ color: 0x2fcbcb, transparent: true, opacity: .15, side: THREE.DoubleSide, depthWrite: false }));
    arc.rotation.x = -Math.PI / 2; arc.position.copy(center); group.add(arc);
  }
}

function createSurveyVessel(position: THREE.Vector3, heading: number | null, waterLevel: number, animated: AnimatedNode[]) {
  const vessel = new THREE.Group(); vessel.position.copy(position); vessel.rotation.y = -(heading ?? 0) * Math.PI / 180;
  const hull = standardMesh(new THREE.CapsuleGeometry(1.8, 6.6, 6, 16), 0x9ddfe1, 1, .34); hull.rotation.x = Math.PI / 2; hull.scale.set(1, .78, .53); hull.position.y = .25; vessel.add(hull);
  const keel = standardMesh(new THREE.CapsuleGeometry(.75, 5.8, 5, 12), 0x0a3648, 1, .42); keel.rotation.x = Math.PI / 2; keel.scale.set(1, .6, .4); keel.position.y = -.55; vessel.add(keel);
  const deck = standardMesh(new THREE.BoxGeometry(2.6, .35, 4.1), 0xd8ffff, 1, .27); deck.position.set(0, 1.08, .08); vessel.add(deck);
  const cabin = standardMesh(new THREE.BoxGeometry(2.05, 1.55, 2.2), 0xc9f7f1, 1, .25); cabin.position.set(0, 1.92, -.25); vessel.add(cabin);
  const windscreen = new THREE.Mesh(new THREE.BoxGeometry(2.13, .62, .88), new THREE.MeshPhysicalMaterial({ color: 0x4ee4ef, metalness: .1, roughness: .1, transmission: .16, transparent: true, opacity: .75 })); windscreen.position.set(0, 2.13, -.85); vessel.add(windscreen);
  const mast = standardMesh(new THREE.CylinderGeometry(.055, .055, 2.45, 8), 0x93e8e6, 1, .25); mast.position.set(0, 3.36, .65); vessel.add(mast);
  const radar = standardMesh(new THREE.TorusGeometry(.48, .07, 6, 20), 0x50e9dc, .94, .25); radar.rotation.x = Math.PI / 2; radar.position.set(0, 4.35, .65); vessel.add(radar);
  const beacon = makeGlow('#59ffe2', 4.8, .8); beacon.position.set(0, 3.9, .65); vessel.add(beacon); animated.push({ object: beacon, material: beacon.material, mode: 'beacon', phase: .2, size: 4.8 });
  for (let index = 0; index < 3; index++) addRing(vessel, new THREE.Vector3(0, waterLevel - position.y + .03, 2.2 + index * 2.2), 0x34d9ec, .12 + index * .24, animated, 4 + index * 1.5);
  return vessel;
}

export function SeabedScene({ state, selectedId, onSelect, layers, command }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef({ state, selectedId, onSelect, layers }); latest.current = { state, selectedId, onSelect, layers };
  const engine = useRef<Engine | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const container = host.current; if (!container) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' }); }
    catch { setError('3D rendering needs WebGL 2. Try a browser with hardware acceleration enabled. Survey data and measurements are still available below.'); return; }
    setError(''); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setClearColor(0x020813, 0); renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.24; renderer.domElement.className = 'sonar-canvas'; container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Interactive 3D seabed survey. Drag to orbit, scroll to zoom, right-drag to pan. Select targets using the contact list.');

    const scene = new THREE.Scene(); scene.fog = new THREE.FogExp2(0x04101d, .0068);
    const camera = new THREE.PerspectiveCamera(38, 1, .1, 5000); const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.dampingFactor = .055; controls.maxPolarAngle = Math.PI * .485; controls.minDistance = 10;
    scene.add(new THREE.HemisphereLight(0x73d8e4, 0x020711, 1.65));
    const key = new THREE.DirectionalLight(0x9bf5ff, 3.8); key.position.set(-55, 105, 48); scene.add(key);
    const rim = new THREE.DirectionalLight(0x175cf2, 3.2); rim.position.set(75, 7, -78); scene.add(rim);
    const amberLight = new THREE.PointLight(0xffb45c, 1.8, 90); amberLight.position.set(-15, 18, 34); scene.add(amberLight);
    const terrain = new THREE.Group(), water = new THREE.Group(), dynamic = new THREE.Group(); scene.add(terrain, water, dynamic);
    const labelHost = document.createElement('div'); labelHost.className = 'scene-labels'; container.appendChild(labelHost);
    const grid = state.dataset.bathymetry; const platformPoints = state.dataset.trajectory.flatMap(pose => validPoint(pose.platform) ? [pose.platform] : []);
    const span = grid ? Math.max((grid.columns - 1) * grid.spacing, (grid.rows - 1) * grid.spacing) : Math.max(100, ...platformPoints.map(point => Math.max(Math.abs(point.x), Math.abs(point.y)) * 2));
    const elevations = grid?.elevations.filter((value): value is number => value !== null) ?? []; const lowest = elevations.length ? Math.min(...elevations) : -30; const highest = elevations.length ? Math.max(...elevations) : 0; const waterLevel = typeof state.dataset.waterLevel === 'number' ? state.dataset.waterLevel : highest + 5;
    const center = new THREE.Vector3(grid ? grid.origin.x + (grid.columns - 1) * grid.spacing / 2 : 0, elevations.length ? (lowest + waterLevel) / 2 : 0, grid ? -(grid.origin.y + (grid.rows - 1) * grid.spacing / 2) : 0);
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(span * .88, span * .69, span * .96)); controls.maxDistance = span * 4; camera.far = span * 12; camera.updateProjectionMatrix(); controls.update();

    if (grid) {
      const positions: number[] = [], colors: number[] = [], indices: number[] = []; const abyss = new THREE.Color('#041925'), shelf = new THREE.Color('#086e78'), ridge = new THREE.Color('#6ce6cf');
      for (let row = 0; row < grid.rows; row++) for (let col = 0; col < grid.columns; col++) {
        const elevation = grid.elevations[row * grid.columns + col]; positions.push(grid.origin.x + col * grid.spacing, elevation ?? lowest - 6, -(grid.origin.y + row * grid.spacing));
        const normalized = elevation === null ? 0 : (elevation - lowest) / Math.max(highest - lowest, 1); const color = abyss.clone().lerp(shelf, Math.min(.92, normalized * 1.18)).lerp(ridge, Math.max(0, normalized - .72) * 2.4); colors.push(color.r, color.g, color.b);
        if (row < grid.rows - 1 && col < grid.columns - 1) { const a = row * grid.columns + col, b = a + 1, c = a + grid.columns, d = c + 1; if ([a, b, c, d].every(index => grid.elevations[index] !== null)) indices.push(a, c, b, b, c, d); }
      }
      const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3)); geometry.setIndex(indices); geometry.computeVertexNormals();
      terrain.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .54, metalness: .34, emissive: 0x04242c, emissiveIntensity: .45, side: THREE.DoubleSide })));
      const wire = new THREE.Mesh(geometry.clone(), new THREE.MeshBasicMaterial({ color: 0x79ffe9, wireframe: true, transparent: true, opacity: .075, depthWrite: false })); wire.position.y = .11; terrain.add(wire);
      for (let row = 0; row < grid.rows; row += 5) { let strip: THREE.Vector3[] = []; for (let col = 0; col < grid.columns; col++) { const elevation = grid.elevations[row * grid.columns + col]; if (elevation === null) { if (strip.length > 1) terrain.add(line(strip, 0x2ab8b8, false, .23)); strip = []; } else strip.push(new THREE.Vector3(grid.origin.x + col * grid.spacing, elevation + .16, -(grid.origin.y + row * grid.spacing))); } if (strip.length > 1) terrain.add(line(strip, 0x2ab8b8, false, .23)); }
      const frame = new THREE.GridHelper(span * 1.5, 30, 0x1aa5ab, 0x0c3847); frame.position.copy(center); frame.position.y = lowest - 9; const frameMaterials = Array.isArray(frame.material) ? frame.material : [frame.material]; frameMaterials.forEach(material => { material.transparent = true; material.opacity = .28; }); terrain.add(frame);
      const boundary: number[] = []; for (let col = 0; col < grid.columns; col++) boundary.push(col); for (let row = 1; row < grid.rows; row++) boundary.push(row * grid.columns + grid.columns - 1); for (let col = grid.columns - 2; col >= 0; col--) boundary.push((grid.rows - 1) * grid.columns + col); for (let row = grid.rows - 2; row > 0; row--) boundary.push(row * grid.columns); boundary.push(0);
      const skirt: number[] = []; for (let index = 1; index < boundary.length; index++) { const a = boundary[index - 1], b = boundary[index]; if (grid.elevations[a] === null || grid.elevations[b] === null) continue; const ax = positions[a * 3], ay = positions[a * 3 + 1], az = positions[a * 3 + 2], bx = positions[b * 3], by = positions[b * 3 + 1], bz = positions[b * 3 + 2]; skirt.push(ax, ay, az, bx, by, bz, ax, lowest - 7, az, bx, by, bz, bx, lowest - 7, bz, ax, lowest - 7, az); }
      const skirtGeometry = new THREE.BufferGeometry(); skirtGeometry.setAttribute('position', new THREE.Float32BufferAttribute(skirt, 3)); skirtGeometry.computeVertexNormals(); terrain.add(standardMesh(skirtGeometry, 0x03121e, 1, .78));
    }

    if (typeof state.dataset.waterLevel === 'number') {
      const surface = new THREE.Mesh(new THREE.PlaneGeometry(span * 1.65, span * 1.65, 36, 36), new THREE.MeshPhysicalMaterial({ color: 0x0b91a0, metalness: .05, roughness: .21, transmission: .08, transparent: true, opacity: .14, side: THREE.DoubleSide, depthWrite: false })); surface.rotation.x = -Math.PI / 2; surface.position.y = waterLevel; water.add(surface);
      const waterGrid = new THREE.GridHelper(span * 1.55, 28, 0x35dbd0, 0x0d6675); waterGrid.position.y = waterLevel + .05; const waterMaterials = Array.isArray(waterGrid.material) ? waterGrid.material : [waterGrid.material]; waterMaterials.forEach(material => { material.transparent = true; material.opacity = .12; }); water.add(waterGrid);
    }
    const ambient: AnimatedNode[] = []; addParticles(water, span, waterLevel, lowest - 4, ambient);
    engine.current = { scene, camera, controls, dynamic, terrain, water, labels: [], labelHost, animated: [], ambient, span, center };
    const resize = () => { const width = container.clientWidth, height = container.clientHeight; renderer.setSize(width, height); camera.aspect = width / Math.max(height, 1); camera.updateProjectionMatrix(); };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    const clock = new THREE.Clock(); let frameId = 0;
    const animate = () => { frameId = requestAnimationFrame(animate); const elapsed = clock.getElapsedTime(); const current = engine.current; current?.controls.update(); for (const item of [...(current?.ambient ?? []), ...(current?.animated ?? [])]) { if (item.mode === 'ring') { const cycle = (elapsed * .37 + item.phase) % 1; const scale = .35 + cycle * (item.size ?? 7); item.object.scale.setScalar(scale); if (item.material) item.material.opacity = Math.max(0, (1 - cycle) * .48); } else if (item.mode === 'sweep') { item.object.rotation.z = elapsed * .62 + item.phase; } else if (item.mode === 'drift') { item.object.rotation.y = elapsed * .012; item.object.position.y = Math.sin(elapsed * .17) * .65; } else if (item.mode === 'beacon') { const pulse = .8 + Math.sin(elapsed * 3.2 + item.phase) * .14; item.object.scale.setScalar(pulse * (item.size ?? 1)); if (item.material) item.material.opacity = .55 + Math.sin(elapsed * 3.2 + item.phase) * .2; } }
      for (const label of current?.labels ?? []) { const projected = label.point.clone().project(camera); label.element.style.transform = `translate(-50%, -50%) translate(${(projected.x * .5 + .5) * container.clientWidth}px,${(-projected.y * .5 + .5) * container.clientHeight}px)`; label.element.hidden = projected.z > 1 || projected.z < -1 || Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1; }
      renderer.render(scene, camera);
    }; animate();
    const lost = (event: Event) => { event.preventDefault(); setError('The 3D graphics context was lost. Reload to restore the scene. Measurements remain available.'); };
    renderer.domElement.addEventListener('webglcontextlost', lost);
    return () => { cancelAnimationFrame(frameId); observer.disconnect(); controls.dispose(); release(dynamic); release(terrain); release(water); scene.clear(); renderer.dispose(); renderer.domElement.removeEventListener('webglcontextlost', lost); renderer.domElement.remove(); labelHost.remove(); engine.current = null; };
  }, [state.dataset]);

  useEffect(() => {
    const current = engine.current; if (!current) return;
    release(current.dynamic); current.labelHost.replaceChildren(); current.labels = []; current.animated = [];
    current.terrain.visible = layers.terrain; current.water.visible = layers.terrain;
    const label = (text: string, position: THREE.Vector3, className = '', id?: string) => { const element = document.createElement(id ? 'button' : 'div'); element.className = `scene-label ${className}`; element.textContent = text; if (id) { element.setAttribute('aria-label', `Select ${text}`); element.onclick = () => latest.current.onSelect(id); } current.labelHost.appendChild(element); current.labels.push({ element, point: position }); };
    const group = current.dynamic, pose = state.pose, waterLevel = typeof state.dataset.waterLevel === 'number' ? state.dataset.waterLevel : 0;
    if (layers.track) for (const segment of state.track) if (segment.length > 1) { const path = line(segment.map(vec), 0x46f8e1, false, .86); group.add(path); const glow = line(segment.map(vec), 0x1ca9fc, false, .18); glow.scale.setScalar(1.006); group.add(glow); }
    if (validPoint(pose?.platform)) {
      const platform = vec(pose.platform); const vessel = createSurveyVessel(platform, pose.heading, waterLevel, current.animated); group.add(vessel); label(state.dataset.platformType.toUpperCase(), platform.clone().add(new THREE.Vector3(0, 8.2, 0)), 'vessel-label');
      addRangeArcs(group, new THREE.Vector3(platform.x, waterLevel + .08, platform.z), current.span);
    }
    if (validPoint(pose?.sonar)) {
      const sonar = vec(pose.sonar); const sensor = standardMesh(new THREE.SphereGeometry(.92, 22, 16), cyan, 1, .22); sensor.position.copy(sonar); group.add(sensor); const sensorGlow = makeGlow('#39e9d5', 6.2, .82); sensorGlow.position.copy(sonar); group.add(sensorGlow); current.animated.push({ object: sensorGlow, material: sensorGlow.material, mode: 'beacon', phase: .75, size: 6.2 });
      if (validPoint(pose.platform)) group.add(line([vec(pose.platform), sonar], 0x6ba9ba, true, .65)); label('MULTIBEAM ARRAY', sonar.clone().add(new THREE.Vector3(4.2, 1.1, 0)), 'sensor-label');
      if (layers.measurements && state.sonarFoot) { const foot = vec(state.sonarFoot); group.add(line([sonar, foot], cyan, true, .9)); addRing(group, foot, cyan, .1, current.animated, 8); label(`ALTITUDE ${meter(state.sonarAltitude)}`, sonar.clone().lerp(foot, .47).add(new THREE.Vector3(-9, 0, 0)), 'measure-label'); }
    }
    for (const { detection, physics } of state.targets) {
      if (!validPoint(detection.position)) continue;
      const selected = detection.id === selectedId; const color = selected ? amber : 0x3bc5df; const position = vec(detection.position); const target = new THREE.Group(); target.position.copy(position); target.rotation.y = -(detection.heading ?? 0) * Math.PI / 180;
      if (detection.dimensions) {
        const dim = detection.dimensions;
        if (/net/i.test(detection.className)) for (let index = 0; index <= 13; index++) { const t = index / 13, a: THREE.Vector3[] = [], b: THREE.Vector3[] = []; for (let point = 0; point <= 13; point++) { const u = point / 13, height = dim.z * (.35 + .65 * Math.sin(Math.PI * t) * Math.sin(Math.PI * u)); a.push(new THREE.Vector3((t - .5) * dim.x, height, (u - .5) * dim.y)); b.push(new THREE.Vector3((u - .5) * dim.x, height, (t - .5) * dim.y)); } target.add(line(a, color, false, selected ? .95 : .62), line(b, color, false, selected ? .95 : .62)); }
        else if (/pipeline|cable/i.test(detection.className)) { const pipe = standardMesh(new THREE.CylinderGeometry(dim.y / 2, dim.y / 2, dim.x, 16), color, .9, .35); pipe.rotation.z = Math.PI / 2; pipe.position.y = dim.z / 2; pipe.scale.z = dim.z / dim.y; target.add(pipe); }
        else { const object = standardMesh(new THREE.BoxGeometry(dim.x, dim.z, dim.y), color, /pot/i.test(detection.className) ? .35 : .78, .35); object.position.y = dim.z / 2; target.add(object); const edges = new THREE.LineSegments(new THREE.EdgesGeometry(object.geometry), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .9 })); edges.position.y = dim.z / 2; target.add(edges); }
        const box = new THREE.BoxGeometry(dim.x + .8, dim.z + .8, dim.y + .8); const bounds = new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineDashedMaterial({ color, dashSize: .48, gapSize: .38, transparent: true, opacity: selected ? .86 : .3 })); box.dispose(); bounds.position.y = dim.z / 2; bounds.computeLineDistances(); target.add(bounds);
      } else target.add(standardMesh(new THREE.OctahedronGeometry(1.12), color, .9, .22));
      group.add(target); const labelPosition = position.clone().add(new THREE.Vector3(0, (detection.dimensions?.z ?? 0) + 5.2, 0)); label(`${detection.id}  /  ${detection.className}`, labelPosition, selected ? 'target-label selected' : 'target-label', detection.id);
      const glow = makeGlow(selected ? '#ffc36d' : '#2bd7fa', selected ? 11 : 6.8, selected ? .86 : .46); glow.position.copy(position).add(new THREE.Vector3(0, (detection.dimensions?.z ?? 0) * .5, 0)); group.add(glow); if (selected) current.animated.push({ object: glow, material: glow.material, mode: 'beacon', phase: .42, size: 11 });
      if (selected && layers.measurements && physics.seabedElevation !== null && physics.clearance !== null) { const ground = vec({ ...detection.position, z: physics.seabedElevation }); group.add(line([position, ground], amber, true, .95)); addRing(group, ground, amber, .25, current.animated, 7); label(`CLEARANCE ${meter(physics.clearance)}`, position.clone().add(new THREE.Vector3(12, 1, 0)), 'clearance-label'); }
      if (layers.shadows && physics.shadow) {
        const shadow = physics.shadow, dx = shadow.end.x - shadow.start.x, dy = shadow.end.y - shadow.start.y, length = shadow.length, half = (detection.dimensions?.y ?? 0) / 2; const vertices: number[] = [], index: number[] = []; let complete = true;
        for (let i = 0; i <= 24; i++) { const t = i / 24; for (const side of [-1, 1]) { const x = shadow.start.x + dx * t + (-dy / length) * half * side * (1 + t * .25), y = shadow.start.y + dy * t + (dx / length) * half * side * (1 + t * .25), z = sampleSeabed(state.dataset.bathymetry, x, y); if (z === null) { complete = false; break; } vertices.push(x, z + .15, -y); } if (!complete) break; if (i < 24) { const a = i * 2; index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } }
        if (complete) { const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); geometry.setIndex(index); group.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: 0x050715, transparent: true, opacity: .78, side: THREE.DoubleSide, depthWrite: false }))); }
        if (selected) { group.add(line([vec(shadow.start).add(new THREE.Vector3(0, .3, 0)), vec(shadow.end).add(new THREE.Vector3(0, .3, 0))], 0xa889ee, true, .93)); if (layers.measurements) label(`PROJECTED SHADOW ${meter(shadow.length)}`, vec(shadow.end).add(new THREE.Vector3(0, 3.6, 0)), 'shadow-label'); }
      }
      if (selected && layers.beam && validPoint(pose?.sonar) && physics.seabedElevation !== null) {
        const source = vec(pose.sonar), endpoint = vec({ ...detection.position, z: physics.seabedElevation }); const direction = endpoint.clone().sub(source); const distance = direction.length(); const sideways = new THREE.Vector3(-direction.z, 0, direction.x).normalize(); const width = Math.max(detection.dimensions?.x ?? 0, 5) * .7; const left = endpoint.clone().addScaledVector(sideways, width); const right = endpoint.clone().addScaledVector(sideways, -width);
        for (let beam = -7; beam <= 7; beam++) { const offset = beam / 7; group.add(line([source, endpoint.clone().addScaledVector(sideways, offset * width)], cyan, true, Math.abs(offset) < .2 ? .55 : .18)); }
        const fanGeometry = new THREE.BufferGeometry().setFromPoints([source, left, right]); fanGeometry.setIndex([0, 1, 2]); group.add(new THREE.Mesh(fanGeometry, new THREE.MeshBasicMaterial({ color: 0x28e3cf, transparent: true, opacity: .10, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending })));
        const sweep = new THREE.Mesh(new THREE.CircleGeometry(Math.max(7, distance * .26), 44, 0, Math.PI * .28), new THREE.MeshBasicMaterial({ color: 0x4ef9e0, transparent: true, opacity: .085, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending })); sweep.position.copy(source); sweep.rotation.x = -Math.PI / 2; group.add(sweep); current.animated.push({ object: sweep, material: sweep.material, mode: 'sweep', phase: 0 });
      }
    }
  }, [state, selectedId, layers]);

  useEffect(() => {
    const current = engine.current; if (!current) return; const target = latest.current.state.targets.find(item => item.detection.id === latest.current.selectedId)?.detection.position;
    if (command.kind === 'focus' && validPoint(target)) { current.controls.target.copy(vec(target)); current.camera.position.copy(vec(target)).add(new THREE.Vector3(42, 31, 44)); }
    else { current.controls.target.copy(current.center); current.camera.position.copy(current.center).add(command.kind === 'top' ? new THREE.Vector3(0, current.span * 1.45, .01) : new THREE.Vector3(current.span * .88, current.span * .69, current.span * .96)); }
    current.controls.update();
  }, [command]);

  return <div className="scene-host" ref={host}>{error && <div className="webgl-error" role="alert">{error}</div>}</div>;
}
