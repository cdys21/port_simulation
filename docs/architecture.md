# Architecture

## Purpose

Terminal Sandbox is designed as a scenario-analysis application for terminal operations. The product goal is not static reporting; it is interactive testing of operational choices such as berth count, crane pool size, train frequency, gate hours, yard fill, and export timing rules.

## Repository Layout

```text
apps/web/                 React UI
services/api/app/         FastAPI app, schemas, run manager
services/api/app/sim/     Simulation engine
mit_work/                 Archived legacy repo content
docs/                     Product and model documentation
```

## Runtime Architecture

### Frontend

- Single-page React application in `apps/web/`.
- Scenario builder for editing simulation settings.
- Run workspace for launching, monitoring, and comparing runs.
- Lightweight inline SVG charts for quick operational readouts.
- Vite dev server proxies requests from `/api` to the Python backend.

### Backend

- `services/api/app/main.py`: FastAPI routes.
- `services/api/app/storage.py`: local JSON persistence for scenarios and runs.
- `services/api/app/run_manager.py`: in-process background run execution via `ThreadPoolExecutor`.
- `services/api/app/sim/engine.py`: minute-step discrete-event simulation engine.

### Persistence

- Scenarios are stored as JSON files in `services/api/data/scenarios/`.
- Run metadata and results are stored as JSON files in `services/api/data/runs/`.
- The backend seeds one default baseline scenario on first startup.

## API Surface

- `GET /api/health`
- `GET /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/scenarios`
- `PUT /api/scenarios/{scenario_id}`
- `GET /api/runs`
- `POST /api/scenarios/{scenario_id}/runs`
- `GET /api/runs/{run_id}`

## Data Flow

1. User selects or edits a scenario in the web UI.
2. UI persists the scenario through the API.
3. User launches a run.
4. API creates a run record and submits it to the background executor.
5. The simulation engine runs minute by minute and periodically updates progress.
6. Completed results are saved into the run record.
7. Frontend polls run status and renders KPIs, timeseries, vessel rows, and container rows.

## Current MVP Tradeoffs

- Local JSON storage instead of Postgres.
- In-process worker instead of a separate queue service.
- Vite React SPA instead of a larger SSR app.
- Simple chart components instead of a heavy analytics library.

These choices keep the MVP easy to run locally while preserving the core simulation logic and product interaction model.
