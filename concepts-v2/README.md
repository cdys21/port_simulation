# Sandbox Concepts v2

These are the second-round concept mocks built around the same exact directional model:

- berth spaces at the top
- vessels moving left to right
- imports flowing down
- exports flowing up
- live continuous time
- reset to empty
- visible +/- controls for vessels, cranes, forklifts, and gates

Files:

- `index.html`
- `stacked-flow.html`
- `activity-stack.html`
- `dock-playfield.html`
- `live-ops.js`
- `dock-playfield.js`

Notes:

- `dock-playfield.html` now has its own dedicated behavior file, `dock-playfield.js`.
- Candidate C models:
  - vessels arriving fast from the left, holding a berth while worked, then departing fast right
  - export trucks entering through gates and import trucks leaving through gates
  - queue pills as over-capacity counts, not generic activity counts
  - inline recent-usage mini charts for berth, crane, forklift, yard, and gate layers
  - layer tinting by utilization / pressure

Open them directly in a browser, or run a local server from the repo root:

```bash
python3 -m http.server
```

Then go to `http://localhost:8000/concepts-v2/`.
