# Terminal Sandbox

Terminal Sandbox is a browser-based port terminal decision-support tool for testing how shared resources, yard fill, rail service, gate hours, and export cutoffs change congestion, throughput, and dwell time. It was created to replace the earlier Streamlit-era prototypes with a clearer, more inspectable product where operators can change assumptions and see the system-wide consequences in one place.

This repository now has two parts:

- `mit_work/`: the preserved legacy simulations, notes, and capstone material from the original repo.
- `apps/` and `services/`: the new MVP implementation built from scratch.

## What This MVP Includes

- Unified import and export flows in one simulation.
- Shared berth, crane, yard, gate, and rail resources.
- Fill-sensitive yard stacking logic where higher yard occupancy increases handling time.
- Export cutoffs and rollover behavior.
- Scenario editing, run history, and baseline comparison in a modern React UI.
- Per-container timestamps, vessel records, hourly timeseries, and summarized KPIs.

## Stack

- Frontend: `React + TypeScript + Vite`
- API: `FastAPI`
- Simulation engine: custom Python minute-step event engine
- Persistence: local JSON files for scenarios and runs under `services/api/data/`

## Quick Start

1. Install frontend dependencies:

```bash
npm install
```

2. Install backend dependencies:

```bash
python3 -m pip install -r services/api/requirements.txt
```

3. Start the API:

```bash
python3 -m uvicorn services.api.app.main:app --reload --port 8000
```

4. Start the web app in a second terminal:

```bash
npm run dev:web
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Documentation

- [Architecture](docs/architecture.md)
- [Simulation Model](docs/simulation-model.md)
- [Playback Decisions](docs/playback-decisions.md)
- [Development](docs/development.md)

## Current Scope

This is an MVP, not a full digital twin. The current model is intentionally strong on shared-resource contention, container state transitions, and fill-based yard delay, while still simplifying labor, 2D yard geometry, and detailed rail planning.
