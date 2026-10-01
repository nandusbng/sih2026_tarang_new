import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { ArrowUpRight, Box, ChevronDown, Crosshair, Database, Eye, EyeOff, FileUp, Gauge, Layers3, LocateFixed, Map, Maximize2, Navigation, Pause, Play, Radio, RotateCcw, ScanLine, ShipWheel, SlidersHorizontal, Sparkles, Target, Waves, X } from 'lucide-react';
import { SeabedScene, type CameraCommand, type Layers } from './components/SeabedScene';
import { deriveSimulation } from './data/physics';
import { createMissingDataSurvey, createSyntheticSurvey } from './data/synthetic';
import type { Detection, SimulationState, SurveyDataset } from './data/types';
import { parseSurveyDataset } from './data/validate';

const metrics = [
  ['Water Depth', 'waterDepth'], ['Target Depth', 'targetDepth'], ['Above Seabed', 'clearance'], ['Sonar Altitude', 'sonarAltitude'],
] as const;
const formatMeters = (value: number | null | undefined) => typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(1)} m` : 'Not Available';
const formatPercent = (value: number | null) => typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'Not Available';
const formatCoord = (value: number | null, axis: 'lat' | 'lon') => typeof value === 'number' ? `${Math.abs(value).toFixed(6)}° ${axis === 'lat' ? (value >= 0 ? 'N' : 'S') : (value >= 0 ? 'E' : 'W')}` : 'Not Available';
const safeDuration = (data: SurveyDataset) => data.trajectory.at(-1)?.time ?? 0;

function Metric({ label, value }: { label: string; value: number | null | undefined }) {
  return <div className="metric"><span>{label}</span><strong className={value === null || value === undefined ? 'unavailable' : ''}>{formatMeters(value)}</strong></div>;
}

function Evidence({ label, value, subtle = false }: { label: string; value: string; subtle?: boolean }) {
  return <div className="evidence"><span>{label}</span><strong className={subtle ? 'unavailable' : ''}>{value}</strong></div>;
}

function TargetPanel({ state, selected, onFocus }: { state: SimulationState; selected: Detection | undefined; onFocus: () => void }) {
  const item = state.targets.find(target => target.detection.id === selected?.id);
  if (!selected || !item) return <aside className="target-panel empty-panel"><div className="empty-scan"><Target size={25}/></div><h2>Awaiting contact lock</h2><p>Select a detected contact from the visual field or the contact matrix.</p></aside>;
  const { physics } = item; const local = selected.position;
  return <aside className="target-panel" aria-label="Selected target data">
    <div className="panel-heading"><div><span className="eyebrow">Contact inspector</span><h2>{selected.id}</h2></div><button className="icon-button" onClick={onFocus} title="Focus camera on selected target" aria-label="Focus camera on selected target"><Crosshair size={17}/></button></div>
    <div className="class-card"><div className="target-icon"><Target size={20}/></div><div><b>{selected.className}</b><span>AI detection result</span></div><div className="confidence"><small>CONFIDENCE</small><b>{formatPercent(selected.confidence)}</b></div></div>
    <section><h3><Gauge size={12}/> Spatial solution</h3>{metrics.map(([label, key]) => <Metric key={key} label={label} value={key === 'sonarAltitude' ? state.sonarAltitude : physics[key]}/>)}</section>
    <section><h3><ScanLine size={12}/> Evidence vector</h3>
      <Evidence label="Shadow Evidence" value={physics.shadowDetected === true ? 'Detected' : physics.shadowDetected === false ? 'Not detected' : 'Not Available'} subtle={physics.shadowDetected === null}/>
      <Evidence label="Observed Shadow" value={formatMeters(physics.observedShadowLength)} subtle={physics.observedShadowLength === null}/>
      <Evidence label="Projected Shadow" value={formatMeters(physics.shadow?.length)} subtle={!physics.shadow}/>
      <Evidence label="Shadow Direction" value={physics.shadow ? `${physics.shadow.bearing.toFixed(0)}°` : 'Not Available'} subtle={!physics.shadow}/>
      <Evidence label="Physics Consistency" value={physics.consistency ?? 'Not Available'} subtle={!physics.consistency}/>
    </section>
    <section><h3><Navigation size={12}/> Position register</h3>
      <Evidence label="Latitude" value={formatCoord(selected.latitude, 'lat')} subtle={selected.latitude === null}/>
      <Evidence label="Longitude" value={formatCoord(selected.longitude, 'lon')} subtle={selected.longitude === null}/>
      <Evidence label="Local East / North" value={local ? `${local.x.toFixed(1)} / ${local.y.toFixed(1)} m` : 'Not Available'} subtle={!local}/>
      <Evidence label="Slant Range" value={formatMeters(physics.slantRange)} subtle={physics.slantRange === null}/>
    </section>
  </aside>;
}

function TacticalHud({ state, selected }: { state: SimulationState; selected: Detection | undefined }) {
  const physics = state.targets.find(target => target.detection.id === selected?.id)?.physics;
  const heading = state.pose?.heading;
  const bearing = state.pose?.sonar && selected?.position
    ? (Math.atan2(selected.position.x - state.pose.sonar.x, selected.position.y - state.pose.sonar.y) * 180 / Math.PI + 360) % 360
    : null;
  const compassStyle = { '--heading': `${heading ?? 0}deg` } as CSSProperties;
  const sweepStyle = { '--bearing': `${bearing ?? 0}deg` } as CSSProperties;
  return <>
    <div className="mission-hud mission-hud-left">
      <div className="hud-topline"><span className="live-signal"><i></i>{state.dataset.source === 'synthetic' ? 'SYNTHETIC FEED' : 'SURVEY FEED'}</span><span>{state.dataset.id}</span></div>
      <div className="hud-value"><span>TRACK STATE</span><b>{state.pose ? 'POSITION LOCK' : 'AWAITING DATA'}</b></div>
      <div className="hud-rule"></div>
      <div className="hud-readout"><span><i>HDG</i><b>{heading === null || heading === undefined ? '—' : `${heading.toFixed(0)}°`}</b></span><span><i>ALT</i><b>{formatMeters(state.sonarAltitude)}</b></span></div>
    </div>
    <div className="mission-hud mission-hud-right">
      <span className="hud-kicker">FOCUSED CONTACT</span><b>{selected?.className ?? 'NO SELECTION'}</b>
      <div className="hud-readout"><span><i>CLR</i><b>{formatMeters(physics?.clearance)}</b></span><span><i>RNG</i><b>{formatMeters(physics?.slantRange)}</b></span></div>
    </div>
    <div className="compass-dial" style={compassStyle} aria-label="Platform heading">
      <span className="compass-north">N</span><span className="compass-east">E</span><span className="compass-south">S</span><span className="compass-west">W</span><i></i><b>{heading === null || heading === undefined ? '—' : `${heading.toFixed(0)}°`}</b>
    </div>
    <div className="sonar-scope" style={sweepStyle} aria-label="Target relation scope"><div className="scope-grid"></div><div className="scope-sweep"></div><div className="scope-return"></div><span>SONAR</span></div>
  </>;
}

function Playback({ time, duration, playing, targets, onSeek, onToggle, onReset }: { time: number; duration: number; playing: boolean; targets: SimulationState['targets']; onSeek: (time: number) => void; onToggle: () => void; onReset: () => void }) {
  const events = targets.flatMap(target => target.detection.shadow?.time === undefined || target.detection.shadow.time === null ? [] : [{ id: target.detection.id, time: target.detection.shadow.time }]);
  return <div className="mission-tape"><div className="tape-title"><span className="eyebrow">Mission replay</span><b>{playing ? 'PLAYBACK ACTIVE' : 'PAUSED'}</b></div><div className="tape-controls"><button className="play-button" onClick={onToggle} disabled={duration === 0} aria-label={playing ? 'Pause playback' : 'Play playback'}>{playing ? <Pause size={17}/> : <Play size={17} fill="currentColor"/>}</button><button className="reset-button" onClick={onReset} aria-label="Reset playback"><RotateCcw size={15}/></button></div><div className="time-track"><input aria-label="Survey replay time" type="range" min="0" max={duration} value={Math.min(time, duration)} step="0.1" onChange={event => onSeek(Number(event.target.value))}/>{events.map(event => <i key={event.id} title={`${event.id} shadow observation`} style={{ left: `${duration > 0 ? event.time / duration * 100 : 0}%` }}></i>)}</div><div className="time-readout"><b>{time.toFixed(1)}</b><span>/</span><b>{duration.toFixed(0)} s</b></div></div>;
}

function ControlRail({ layers, onToggle, onCamera, onSynthetic, onMissing, onFile }: { layers: Layers; onToggle: (key: keyof Layers) => void; onCamera: (kind: CameraCommand['kind']) => void; onSynthetic: () => void; onMissing: () => void; onFile: (file: File) => void }) {
  const toggles = [['terrain', 'Bathymetry', Layers3], ['track', 'Survey track', Map], ['beam', 'Sonar geometry', ScanLine], ['shadows', 'Projected shadow', Eye], ['measurements', 'Measurement marks', SlidersHorizontal]] as const;
  return <aside className="control-rail" aria-label="Simulation controls"><div className="rail-brand"><Box size={17}/><span>CMD</span></div><div className="rail-segment">{toggles.map(([key, label, Icon]) => <button key={key} className={layers[key] ? 'rail-action active' : 'rail-action'} onClick={() => onToggle(key)} title={label} aria-label={`${layers[key] ? 'Hide' : 'Show'} ${label}`}><Icon size={17}/><span>{label}</span></button>)}</div><div className="rail-segment"> <button className="rail-action" onClick={() => onCamera('reset')} title="Reset camera" aria-label="Reset camera"><RotateCcw size={17}/><span>Reset camera</span></button><button className="rail-action" onClick={() => onCamera('top')} title="Top view" aria-label="Top view"><Maximize2 size={17}/><span>Top view</span></button></div><div className="rail-bottom"><button className="rail-action" onClick={onSynthetic} title="Load synthetic survey" aria-label="Load synthetic survey"><ShipWheel size={17}/><span>Synthetic survey</span></button><button className="rail-action" onClick={onMissing} title="Load missing data demo" aria-label="Load missing-data demo"><EyeOff size={17}/><span>Missing data demo</span></button><label className="rail-action" title="Load TARANG data JSON"><FileUp size={17}/><span>Load JSON</span><input type="file" accept="application/json,.json" onChange={event => { const file = event.target.files?.[0]; if (file) onFile(file); event.currentTarget.value = ''; }}/></label></div></aside>;
}

export default function App() {
  const [dataset, setDataset] = useState<SurveyDataset>(() => createSyntheticSurvey());
  const [time, setTime] = useState(55); const [playing, setPlaying] = useState(false); const [selectedId, setSelectedId] = useState<string | null>('T-001');
  const [layers, setLayers] = useState<Layers>({ terrain: true, track: true, beam: true, shadows: true, measurements: true });
  const [command, setCommand] = useState<CameraCommand>({ kind: 'reset', sequence: 0 }); const [drawer, setDrawer] = useState(false); const [message, setMessage] = useState('');
  const duration = safeDuration(dataset); const state = useMemo(() => deriveSimulation(dataset, time), [dataset, time]); const selected = state.targets.find(item => item.detection.id === selectedId)?.detection;
  const last = useRef<number | undefined>(undefined);
  useEffect(() => { if (!playing) { last.current = undefined; return; } let request = 0; const tick = (now: number) => { if (last.current !== undefined) { const next = time + (now - last.current) / 1000 * 8; if (next >= duration) { setTime(duration); setPlaying(false); return; } setTime(next); } last.current = now; request = requestAnimationFrame(tick); }; request = requestAnimationFrame(tick); return () => cancelAnimationFrame(request); }, [playing, time, duration]);
  useEffect(() => { setTime(current => Math.min(current, duration)); if (!dataset.detections.some(detection => detection.id === selectedId)) setSelectedId(dataset.detections[0]?.id ?? null); }, [dataset, duration, selectedId]);
  const moveCamera = useCallback((kind: CameraCommand['kind']) => setCommand(current => ({ kind, sequence: current.sequence + 1 })), []);
  const upload = async (file: File) => { try { if (file.size > 10 * 1024 * 1024) throw new Error('File exceeds the 10 MB demo import limit.'); const parsed = parseSurveyDataset(JSON.parse(await file.text())); setDataset(parsed); setTime(parsed.trajectory[0]?.time ?? 0); setPlaying(false); setMessage(`Loaded ${parsed.name}.`); } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not read the survey file.'); } };
  const switchDemo = (missing: boolean) => { const next = missing ? createMissingDataSurvey() : createSyntheticSurvey(); setDataset(next); setTime(missing ? 0 : 55); setPlaying(false); setSelectedId(next.detections[0]?.id ?? null); setMessage(missing ? 'Missing-data demo loaded. Values without input data are explicitly unavailable.' : 'Synthetic survey loaded.'); };
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><div className="brand-mark"><Waves size={21}/></div><div><b>TARANG</b><span>SONAR INTELLIGENCE</span></div></div><div className="title"><span className="eyebrow">Abyssal command deck</span><h1>Survey Visualization <i>///</i> Seabed Simulation</h1></div><div className="header-meta"><div><span>COORDINATE FRAME</span><b>LOCAL ENU</b></div><div className="mode"><span className="pulse"></span>SIMULATION MODE</div></div></header>
    <div className="command-deck">
      <ControlRail layers={layers} onToggle={key => setLayers(current => ({ ...current, [key]: !current[key] }))} onCamera={moveCamera} onSynthetic={() => switchDemo(false)} onMissing={() => switchDemo(true)} onFile={file => void upload(file)}/>
      <section className="simulation" aria-label="TARANG seabed simulation"><div className="scene-ambient" aria-hidden="true"><i className="corner corner-a"></i><i className="corner corner-b"></i><i className="corner corner-c"></i><i className="corner corner-d"></i><div className="depth-lines"></div></div><div className="scene-top"><div><span className="eyebrow">Spatial theater / 3D bathymetry</span><p>Orbit the survey volume · select any contact · inspect the evidence vector</p></div><div className="scene-top-actions"><div className="view-badge"><LocateFixed size={14}/> {dataset.platformType} <span></span> REPLAY</div><button className="mobile-inspect-button" onClick={() => setDrawer(true)}>Inspect <ChevronDown size={15}/></button></div></div><SeabedScene state={state} selectedId={selectedId} onSelect={id => { setSelectedId(id); moveCamera('focus'); }} layers={layers} command={command}/><TacticalHud state={state} selected={selected}/><div className="scene-cue"><Sparkles size={13}/><span>INTERACTIVE 3D VOLUME</span></div><div className="scene-legend"><span><i className="legend-platform"></i>Platform</span><span><i className="legend-sonar"></i>Array</span><span><i className="legend-contact"></i>Contact</span><span><i className="legend-shadow"></i>Shadow</span></div><Playback time={time} duration={duration} playing={playing} targets={state.targets} onSeek={setTime} onToggle={() => setPlaying(current => !current)} onReset={() => { setTime(0); setPlaying(false); }}/></section>
      <aside className="intel-panel"><div className="intel-heading"><div><span className="eyebrow">AI detection matrix</span><h2>Contacts <b>{state.targets.length}</b></h2></div></div><div className="contact-summary"><Radio size={14}/><span>ACOUSTIC CORRELATION</span><b>{state.targets.filter(target => target.physics.shadowDetected === true).length} / {state.targets.length}</b></div><div className="contacts-list">{state.targets.map(({ detection, physics }, index) => <button className={`contact ${detection.id === selectedId ? 'active' : ''}`} key={detection.id} onClick={() => { setSelectedId(detection.id); moveCamera('focus'); }}><span className="contact-index">0{index + 1}</span><span className="contact-dot"></span><span className="contact-name"><b>{detection.className}</b><small>{detection.id} <i></i> {formatPercent(detection.confidence)}</small></span><span className={physics.clearance === null ? 'unavailable' : 'clearance'}>{formatMeters(physics.clearance)}<small>CLR</small></span><ArrowUpRight size={13}/></button>)}</div><TargetPanel state={state} selected={selected} onFocus={() => moveCamera('focus')}/></aside>
    </div>
    {message && <div className="toast" role="status"><Database size={15}/>{message}<button onClick={() => setMessage('')} aria-label="Dismiss message"><X size={15}/></button></div>}
    <div className={`mobile-drawer ${drawer ? 'visible' : ''}`}><div className="drawer-backdrop" onClick={() => setDrawer(false)}></div><div className="drawer-content"><button className="close-drawer" onClick={() => setDrawer(false)}><X size={18}/></button><TargetPanel state={state} selected={selected} onFocus={() => { moveCamera('focus'); setDrawer(false); }}/></div></div>
  </main>;
}
