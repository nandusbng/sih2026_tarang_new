import type { Bathymetry, Detection, SurveyDataset, SurveyPose } from './types';
import { projectShadow, sampleSeabed } from './physics';

/** All invented survey values live in this source, never in presentation components. */
export function createSyntheticSurvey(seed = 26): SurveyDataset {
  let s = seed >>> 0;
  const random = () => { s = (Math.imul(1664525,s)+1013904223)>>>0; return s/4294967296; };
  const phase = random()*Math.PI*2;
  const bathymetry: Bathymetry = { origin: {x:-90,y:-65}, columns:91, rows:66, spacing:2, elevations:[] };
  for (let row=0;row<bathymetry.rows;row++) for(let col=0;col<bathymetry.columns;col++) {
    const x=bathymetry.origin.x+col*bathymetry.spacing,y=bathymetry.origin.y+row*bathymetry.spacing;
    bathymetry.elevations.push(-44 + 4.2*Math.sin(x/23+phase)*Math.cos(y/31) + 2.1*Math.sin((x+y)/12) + 7*Math.exp(-((x-37)**2/420+(y+22)**2/650)) - 4*Math.exp(-((x+30)**2/250+(y-20)**2/340)) + 0.15*Math.sin(x*2+y));
  }
  const trajectory: SurveyPose[] = [];
  for(let i=0;i<=120;i++) {
    const x=-74+i*1.2, y=12+8*Math.sin(i/24), z=-16+Math.sin(i/20);
    trajectory.push({time:i,platform:{x,y,z:0},sonar:{x,y,z},heading: (Math.atan2(1.2,8/24*Math.cos(i/24))*180/Math.PI+360)%360,altitude:null,latitude:null,longitude:null});
  }
  const classes = ['Ghost Net','Crab Pot','Pipeline / Cable','Shipwreck'];
  const positions = [{x:-5,y:-12},{x:34,y:27},{x:-45,y:-27},{x:53,y:-24}];
  const dimensions = [{x:13,y:8,z:3.2},{x:4,y:4,z:3},{x:20,y:2,z:1.4},{x:16,y:7,z:5}];
  const detections: Detection[] = classes.map((className,i)=>({
    id:`T-${String(i+1).padStart(3,'0')}`,className,confidence:0.82+random()*0.16,
    position:{...positions[i],z:sampleSeabed(bathymetry,positions[i].x,positions[i].y)!+(i===0?2.4:0)},dimensions:dimensions[i],heading:random()*70,
    latitude:null,longitude:null,boundingBox:{x:Math.round(random()*500),y:Math.round(random()*250),width:80+Math.round(random()*100),height:35+Math.round(random()*60)},segmentation:null,shadow:null,
  }));
  for(const target of detections) { const prediction=projectShadow(bathymetry,trajectory[55].sonar,target); if(prediction) target.shadow={detected:true,length:prediction.length+(random()-0.5)*0.4,time:55}; }
  return {schemaVersion:1,id:`synthetic-${seed}`,name:'Continental shelf · Demo survey',source:'synthetic',platformType:'Survey vessel',coordinateFrame:'local-ENU',waterLevel:0,bathymetry,trajectory,detections,physics:{shadowTolerance:0.5,observationTimeTolerance:0.05}};
}

export function createMissingDataSurvey(): SurveyDataset {
  const data=createSyntheticSurvey();
  return {...data,id:'missing-data-demo',name:'Missing metadata · Demo survey',waterLevel:null,bathymetry:null,
    trajectory:data.trajectory.map(p=>({...p,sonar:null,altitude:null})),
    detections:data.detections.map((d,i)=>({...d,position:i===0?null:d.position,confidence:null,dimensions:null,shadow:null}))};
}
