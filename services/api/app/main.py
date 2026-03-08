from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .run_manager import submit_run
from .schemas import ScenarioConfig
from .storage import (
    create_run,
    create_scenario,
    ensure_storage,
    get_run,
    get_scenario,
    list_runs,
    list_scenarios,
    update_scenario,
)


app = FastAPI(title="Terminal Sandbox API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_storage()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return [scenario.model_dump(mode="json") for scenario in list_scenarios()]


@app.get("/api/runs")
def runs() -> list[dict]:
    return [run.model_dump(mode="json") for run in list_runs()]


@app.get("/api/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str) -> dict:
    try:
        return get_scenario(scenario_id).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/scenarios")
def scenario_create(config: ScenarioConfig) -> dict:
    scenario = create_scenario(config)
    return scenario.model_dump(mode="json")


@app.put("/api/scenarios/{scenario_id}")
def scenario_update(scenario_id: str, config: ScenarioConfig) -> dict:
    try:
        scenario = update_scenario(scenario_id, config)
        return scenario.model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/scenarios/{scenario_id}/runs")
def run_create(scenario_id: str) -> dict:
    try:
        get_scenario(scenario_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    run = create_run(scenario_id)
    submit_run(run.id)
    return run.model_dump(mode="json")


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str) -> dict:
    try:
        return get_run(run_id).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
