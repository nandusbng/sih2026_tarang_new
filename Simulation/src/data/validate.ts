import type { SurveyDataset } from './types';
/** Reject incompatible input at the integration boundary. Missing measurements must be null. */
export function parseSurveyDataset(input: unknown): SurveyDataset {
  const fail = (message: string): never => { throw new Error(`Invalid survey: ${message}`); };
  const object = (v: unknown, path: string): Record<string,unknown> => v !== null && typeof v==='object' && !Array.isArray(v) ? v as Record<string,unknown> : fail(`${path} must be an object`);
  const number = (v: unknown, path: string, nullable=false): void => { if(nullable && v===null)return; if(typeof v!=='number'||!Number.isFinite(v))fail(`${path} must be ${nullable?'null or ':''}a finite number`); };
  const point = (v: unknown,path: string): void => { if(v===null)return; const p=object(v,path); for(const k of ['x','y','z'])number(p[k],`${path}.${k}`); };
  const string = (v: unknown,path:string):void=>{if(typeof v!=='string'||!v.trim())fail(`${path} must be a nonempty string`);};
  const data=object(input,'dataset');
  if(data.schemaVersion!==1||data.coordinateFrame!=='local-ENU')fail('expected schemaVersion 1 and local-ENU coordinates');
  if(data.source!=='synthetic'&&data.source!=='survey')fail('source must be synthetic or survey');
  for(const k of ['id','name','platformType'])string(data[k],k);
  number(data.waterLevel,'waterLevel',true);
  if(data.bathymetry!==null){const b=object(data.bathymetry,'bathymetry'),o=object(b.origin,'bathymetry.origin');number(o.x,'origin.x');number(o.y,'origin.y');number(b.spacing,'spacing');if((b.spacing as number)<=0)fail('spacing must be positive');for(const k of ['rows','columns'])if(!Number.isInteger(b[k])||(b[k] as number)<2)fail(`${k} must be an integer >= 2`);if((b.rows as number)*(b.columns as number)>250000)fail('bathymetry is limited to 250,000 samples');if(!Array.isArray(b.elevations)||b.elevations.length!==(b.rows as number)*(b.columns as number))fail('elevation count does not match grid dimensions');(b.elevations as unknown[]).forEach(v=>number(v,'elevation',true));}
  if(!Array.isArray(data.trajectory)||data.trajectory.length>100000)fail('trajectory must be an array of at most 100,000 poses');
  let last=-Infinity;
  (data.trajectory as unknown[]).forEach((v,i)=>{const p=object(v,`trajectory[${i}]`);number(p.time,'time');if((p.time as number)<=last)fail('trajectory times must strictly increase');last=p.time as number;point(p.platform,'platform');point(p.sonar,'sonar');for(const k of ['heading','altitude','latitude','longitude'])number(p[k],k,true);if(typeof p.altitude==='number'&&p.altitude<0)fail('altitude must be nonnegative');if(typeof p.latitude==='number'&&Math.abs(p.latitude)>90)fail('latitude out of range');if(typeof p.longitude==='number'&&Math.abs(p.longitude)>180)fail('longitude out of range');});
  if(!Array.isArray(data.detections)||data.detections.length>1000)fail('detections must be an array of at most 1,000 targets');
  const ids=new Set();
  (data.detections as unknown[]).forEach(v=>{const d=object(v,'detection');string(d.id,'detection.id');if(ids.has(d.id))fail('duplicate detection id');ids.add(d.id);string(d.className,'className');number(d.confidence,'confidence',true);if(typeof d.confidence==='number'&&(d.confidence<0||d.confidence>1))fail('confidence must be between 0 and 1');point(d.position,'position');point(d.dimensions,'dimensions');if(d.dimensions!==null&&Object.values(d.dimensions as object).some(n=>typeof n==='number'&&n<=0))fail('dimensions must be positive');for(const k of ['heading','latitude','longitude'])number(d[k],k,true);if(typeof d.latitude==='number'&&Math.abs(d.latitude)>90)fail('target latitude out of range');if(typeof d.longitude==='number'&&Math.abs(d.longitude)>180)fail('target longitude out of range');
    if(d.boundingBox!==null){const b=object(d.boundingBox,'boundingBox');for(const k of ['x','y','width','height'])number(b[k],`boundingBox.${k}`);if((b.width as number)<=0||(b.height as number)<=0)fail('bounding box dimensions must be positive');}
    if(d.segmentation!==null){if(!Array.isArray(d.segmentation)||d.segmentation.length<3)fail('segmentation must contain at least 3 pixel points');(d.segmentation as unknown[]).forEach(v=>{const p=object(v,'segmentation point');number(p.x,'segmentation.x');number(p.y,'segmentation.y');});}
    if(d.shadow!==null){const s=object(d.shadow,'shadow');if(s.detected!==null&&typeof s.detected!=='boolean')fail('shadow.detected must be boolean or null');number(s.time,'shadow.time');number(s.length,'shadow.length',true);if(typeof s.length==='number'&&s.length<0)fail('shadow length must be nonnegative');}
  });
  const physics=object(data.physics,'physics');for(const k of ['shadowTolerance','observationTimeTolerance']){number(physics[k],`physics.${k}`);if((physics[k] as number)<0)fail(`${k} must be nonnegative`);}
  return input as SurveyDataset;
}
