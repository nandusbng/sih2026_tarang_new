# TARANG Seabed Simulation

Standalone interactive prototype for TARANG’s survey visualization. It renders the spatial relationship among bathymetry, survey vessel, sonar, AI contacts, clearance, predicted shadow geometry, and survey track.

## Run

```powershell
npm.cmd install
npm.cmd run dev
```

For a production bundle, run `npm.cmd run build`. Vite writes the static site to `dist/`.

## Data flow

```text
Survey metadata / XTF-JSF adapter ─┐
AI detection adapter ──────────────┼─> SurveyDataset ─> deriveSimulation() ─> 3D scene + UI
Bathymetry adapter ────────────────┘                         │
                                                      derived physics
                                                (depth, clearance, shadow)
```

The UI only formats fields from `SimulationState`; it does not define measurements. The supplied synthetic generator is in [src/data/synthetic.ts](src/data/synthetic.ts). Replace it with a backend adapter when TARANG survey data is ready.

## Integrating real data

1. Map the backend response to the `SurveyDataset` contract in [src/data/types.ts](src/data/types.ts). Coordinates use a local East/North/Up frame in metres. `waterLevel` is the vertical datum for depth calculation.
2. Pass unknown fields as `null`, never invented numbers. The interface displays `Not Available`.
3. Run `parseSurveyDataset(payload)` at the API boundary. It validates ranges, structure, resource limits, and coordinate metadata before rendering.
4. Give each detection a stable `id`. `Detection.position` is its lowest point, and `dimensions.z` extends upward, allowing clearance and projected-shadow geometry to be calculated consistently.

The JSON loader in the sidebar accepts this same contract and exists for integration testing. It has a 10 MB client-side demo limit; production upload limits and authentication belong in TARANG’s backend.

## Measurements and evidence

- **Water depth** = `waterLevel - seabed elevation`
- **Target depth** = `waterLevel - target elevation`
- **Above seabed** = `target elevation - sampled seabed elevation`
- **Sonar altitude** uses source metadata when supplied; otherwise it is derived from the sonar point and bathymetry.
- **Projected shadow** traces a line from the sonar through the target crown until it intersects the sampled seabed. It is a geometric prediction. It becomes evidence only when a detection-side `shadow` observation exists at the active survey time.

This browser prototype does not validate sonar imagery, infer an object’s class, or replace acoustic physics processing. Those results must come from TARANG’s detection and physics services.
