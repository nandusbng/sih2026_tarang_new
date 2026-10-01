/** All spatial values are metres in a local East/North/Up frame. Null means unknown. */
export interface Vec3 { x: number; y: number; z: number }
export interface Bathymetry {
  origin: { x: number; y: number }; columns: number; rows: number;
  spacing: number; elevations: (number | null)[];
}
export interface SurveyPose {
  time: number; platform: Vec3 | null; sonar: Vec3 | null;
  heading: number | null; altitude: number | null;
  latitude: number | null; longitude: number | null;
}
export interface Detection {
  id: string; className: string; confidence: number | null;
  /** Position is the target's lowest point; dimensions extend upwards. */
  position: Vec3 | null; dimensions: Vec3 | null; heading: number | null;
  latitude: number | null; longitude: number | null;
  boundingBox: { x: number; y: number; width: number; height: number } | null;
  segmentation: { x: number; y: number }[] | null;
  /** Shadow observations belong to one survey time, not every playback frame. */
  shadow: { detected: boolean | null; length: number | null; time: number } | null;
}
export interface SurveyDataset {
  schemaVersion: 1; id: string; name: string; source: 'synthetic' | 'survey';
  platformType: string; coordinateFrame: 'local-ENU';
  waterLevel: number | null; bathymetry: Bathymetry | null;
  trajectory: SurveyPose[]; detections: Detection[];
  physics: { shadowTolerance: number; observationTimeTolerance: number };
}
export interface ShadowGeometry { start: Vec3; end: Vec3; length: number; bearing: number }
export interface TargetPhysics {
  seabedElevation: number | null; waterDepth: number | null; targetDepth: number | null;
  clearance: number | null; slantRange: number | null; shadow: ShadowGeometry | null;
  shadowDetected: boolean | null; observedShadowLength: number | null;
  consistency: 'Consistent' | 'Outside tolerance' | null;
}
export interface SimulationState {
  dataset: SurveyDataset; time: number; pose: SurveyPose | null;
  sonarAltitude: number | null; sonarFoot: Vec3 | null;
  track: Vec3[][]; targets: { detection: Detection; physics: TargetPhysics }[];
}
