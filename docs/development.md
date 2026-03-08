# Development

## Prerequisites

- `python3`
- `node` and `npm`

## Install

### Frontend

```bash
npm install
```

### Backend

```bash
python3 -m pip install -r services/api/requirements.txt
```

## Run Locally

### API

```bash
python3 -m uvicorn services.api.app.main:app --reload --port 8000
```

### Web App

```bash
npm run dev:web
```

Open the Vite URL shown in the terminal. The frontend proxies `/api` to the backend.

## Backend Smoke Check

```bash
python3 -m py_compile services/api/app/*.py services/api/app/sim/*.py
python3 - <<'PY'
from services.api.app.defaults import DEFAULT_SCENARIO
from services.api.app.schemas import ScenarioConfig
from services.api.app.sim.engine import SimulationEngine

config = ScenarioConfig.model_validate(DEFAULT_SCENARIO)
result = SimulationEngine(config).run()
print(result["summary"])
PY
```

## API Notes

- `GET /api/scenarios` returns saved scenarios.
- `PUT /api/scenarios/{id}` overwrites a scenario config.
- `POST /api/scenarios/{id}/runs` launches a run asynchronously.
- `GET /api/runs` returns recent runs.
- `GET /api/runs/{id}` returns status plus results when complete.

## Frontend Notes

- `apps/web/src/App.tsx` contains the current scenario builder and results workspace.
- `apps/web/src/api.ts` defines the API client and uses `VITE_API_BASE` or `/api`.
- `apps/web/vite.config.ts` sets the dev proxy to the Python API.

## Legacy Material

All original files from the previous repo are preserved under `mit_work/`. The new build should happen at repo root and should not depend on those older modules.
