import type { Bathymetry, Detection, ShadowGeometry, SimulationState, SurveyDataset, SurveyPose, TargetPhysics, Vec3 } from './types';

export const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export const validPoint = (v: Vec3 | null | undefined): v is Vec3 => !!v && finite(v.x) && finite(v.y) && finite(v.z);
export function sampleSeabed(grid: Bathymetry | null, x: number, y: number): number | null {
  if (!grid || grid.spacing <= 0) return null;
  const gx = (x - grid.origin.x) / grid.spacing, gy = (y - grid.origin.y) / grid.spacing;
  if (gx < 0 || gy < 0 || gx > grid.columns - 1 || gy > grid.rows - 1) return null;
  const ix = Math.min(Math.floor(gx), grid.columns - 2), iy = Math.min(Math.floor(gy), grid.rows - 2);
  const tx = gx - ix, ty = gy - iy;
  const samples = [grid.elevations[iy * grid.columns + ix], grid.elevations[iy * grid.columns + ix + 1], grid.elevations[(iy + 1) * grid.columns + ix], grid.elevations[(iy + 1) * grid.columns + ix + 1]];
  if (!samples.every(finite)) return null;
  return samples[0]! * (1 - tx) * (1 - ty) + samples[1]! * tx * (1 - ty) + samples[2]! * (1 - tx) * ty + samples[3]! * tx * ty;
}
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const mixPoint = (a: Vec3 | null, b: Vec3 | null, t: number): Vec3 | null => validPoint(a) && validPoint(b) ? { x: mix(a.x,b.x,t), y: mix(a.y,b.y,t), z: mix(a.z,b.z,t) } : null;
export function poseAt(data: SurveyDataset, time: number): SurveyPose | null {
  const frames = data.trajectory;
  if (!frames.length) return null;
  if (time <= frames[0].time) return frames[0];
  if (time >= frames.at(-1)!.time) return frames.at(-1)!;
  const index = frames.findIndex(p => p.time >= time), a = frames[index - 1], b = frames[index];
  if (b.time === time) return b;
  const t = (time - a.time) / (b.time - a.time);
  const field = (key: 'altitude' | 'latitude' | 'longitude') => finite(a[key]) && finite(b[key]) ? mix(a[key]!, b[key]!, t) : null;
  const heading = finite(a.heading) && finite(b.heading) ? (a.heading + (((b.heading - a.heading + 540) % 360) - 180) * t + 360) % 360 : null;
  return { time, platform: mixPoint(a.platform,b.platform,t), sonar: mixPoint(a.sonar,b.sonar,t), heading, altitude: field('altitude'), latitude: field('latitude'), longitude: field('longitude') };
}
/** Geometric prediction: ray from sensor through target crown intersects sampled terrain.
 * No acoustic intensity, refraction, or validation of AI detections is implied. */
export function projectShadow(grid: Bathymetry | null, sonar: Vec3 | null, target: Detection): ShadowGeometry | null {
  if (!grid || !validPoint(sonar) || !validPoint(target.position) || !validPoint(target.dimensions)) return null;
  const p = target.position, crown = { ...p, z: p.z + target.dimensions.z };
  const dx = crown.x - sonar.x, dy = crown.y - sonar.y, dz = crown.z - sonar.z;
  const horizontal = Math.hypot(dx, dy), ground = sampleSeabed(grid,p.x,p.y);
  if (!horizontal || dz >= 0 || ground === null || crown.z <= ground) return null;
  const step = grid.spacing / 4, maxDistance = Math.hypot(grid.columns,grid.rows) * grid.spacing;
  let previous = 0;
  const ray = (distance: number) => ({ x: p.x + dx / horizontal * distance, y: p.y + dy / horizontal * distance, z: crown.z + dz / horizontal * distance });
  for (let distance = step; distance <= maxDistance; distance += step) {
    const point = ray(distance), seabed = sampleSeabed(grid,point.x,point.y);
    if (seabed === null) return null;
    if (point.z <= seabed) {
      let low = previous, high = distance;
      for (let i = 0; i < 20; i++) { const mid = (low+high)/2, m = ray(mid), z = sampleSeabed(grid,m.x,m.y); if (z === null) return null; if (m.z > z) low = mid; else high = mid; }
      const end = ray((low+high)/2);
      return { start: { ...p, z: ground }, end, length: Math.hypot(end.x-p.x,end.y-p.y), bearing: (Math.atan2(dx,dy)*180/Math.PI+360)%360 };
    }
    previous = distance;
  }
  return null;
}
export function deriveTarget(data: SurveyDataset, pose: SurveyPose | null, target: Detection, time: number): TargetPhysics {
  const p = target.position, ground = validPoint(p) ? sampleSeabed(data.bathymetry,p.x,p.y) : null;
  const shadow = projectShadow(data.bathymetry,pose?.sonar ?? null,target);
  const observation = target.shadow && Math.abs(target.shadow.time-time) <= data.physics.observationTimeTolerance ? target.shadow : null;
  const observed = observation?.length ?? null;
  return {
    seabedElevation: ground,
    waterDepth: finite(data.waterLevel) && ground !== null ? data.waterLevel-ground : null,
    targetDepth: finite(data.waterLevel) && validPoint(p) ? data.waterLevel-p.z : null,
    clearance: validPoint(p) && ground !== null ? p.z-ground : null,
    slantRange: validPoint(p) && validPoint(pose?.sonar) ? Math.hypot(p.x-pose.sonar.x,p.y-pose.sonar.y,p.z-pose.sonar.z) : null,
    shadow, shadowDetected: observation?.detected ?? null, observedShadowLength: observed,
    consistency: observation?.detected === true && shadow && finite(observed) ? (Math.abs(shadow.length-observed) <= data.physics.shadowTolerance ? 'Consistent' : 'Outside tolerance') : null,
  };
}
export function deriveSimulation(data: SurveyDataset, time: number): SimulationState {
  const pose = poseAt(data,time), sonar = pose?.sonar;
  const ground = validPoint(sonar) ? sampleSeabed(data.bathymetry,sonar.x,sonar.y) : null;
  const track: Vec3[][] = []; let segment: Vec3[] = [];
  for (const frame of data.trajectory.filter(p=>p.time<=time)) { if (validPoint(frame.platform)) segment.push(frame.platform); else if (segment.length) { track.push(segment); segment=[]; } }
  if (validPoint(pose?.platform)) segment.push(pose.platform);
  if (segment.length) track.push(segment);
  return { dataset: data, time, pose, track, sonarAltitude: finite(pose?.altitude) ? pose.altitude : validPoint(sonar) && ground !== null ? sonar.z-ground : null,
    sonarFoot: validPoint(sonar) && ground !== null ? {...sonar,z:ground} : null,
    targets: data.detections.map(detection=>({detection,physics:deriveTarget(data,pose,detection,time)})) };
}
