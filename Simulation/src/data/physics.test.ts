import { describe, expect, it } from 'vitest';
import { deriveSimulation, projectShadow, sampleSeabed } from './physics';
import { createSyntheticSurvey } from './synthetic';
import { parseSurveyDataset } from './validate';
import type { Bathymetry, SurveyDataset } from './types';

describe('spatial calculations', () => {
  const planar: Bathymetry = {origin:{x:0,y:0},columns:2,rows:2,spacing:10,elevations:[-10,-10,-10,-10]};
  it('bilinearly samples the seabed and returns unavailable outside the surveyed patch', () => {
    expect(sampleSeabed(planar,5,5)).toBe(-10);
    expect(sampleSeabed(planar,-.01,5)).toBeNull();
  });
  it('derives altitude and clearance from positions instead of UI defaults', () => {
    const source=createSyntheticSurvey();
    const data:SurveyDataset={...source,bathymetry:planar,waterLevel:0,trajectory:[{time:0,platform:{x:5,y:5,z:0},sonar:{x:5,y:5,z:-4},heading:0,altitude:null,latitude:null,longitude:null}],detections:[{...source.detections[0],position:{x:5,y:5,z:-8},dimensions:{x:1,y:1,z:1},shadow:null}]};
    const state=deriveSimulation(data,0);
    expect(state.sonarAltitude).toBe(6);
    expect(state.targets[0].physics.waterDepth).toBe(10);
    expect(state.targets[0].physics.targetDepth).toBe(8);
    expect(state.targets[0].physics.clearance).toBe(2);
  });
  it('projects shadow geometry along the sonar-to-target ray until terrain intersection', () => {
    const source=createSyntheticSurvey();
    const target={...source.detections[0],position:{x:5,y:5,z:-8},dimensions:{x:1,y:1,z:2}};
    const shadow=projectShadow(planar,{x:4,y:5,z:-4},target);
    expect(shadow?.start).toEqual({x:5,y:5,z:-10});
    expect(shadow?.end.z).toBeCloseTo(-10,4);
    expect(shadow?.length).toBeGreaterThan(0);
  });
});

describe('external survey contract', () => {
  it('accepts the generated synthetic contract', () => expect(parseSurveyDataset(createSyntheticSurvey())).toMatchObject({schemaVersion:1,coordinateFrame:'local-ENU'}));
  it('rejects values that would corrupt a spatial visualization', () => {
    const invalid={...createSyntheticSurvey(),trajectory:[{...createSyntheticSurvey().trajectory[0],latitude:123}]};
    expect(()=>parseSurveyDataset(invalid)).toThrow('latitude out of range');
  });
});
