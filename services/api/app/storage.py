from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import List
from uuid import uuid4

from pydantic import ValidationError

from .defaults import DEFAULT_SCENARIO
from .schemas import RunRecord, ScenarioConfig, ScenarioRecord


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
SCENARIO_DIR = DATA_DIR / "scenarios"
RUN_DIR = DATA_DIR / "runs"


def _write_json(path: Path, payload: dict) -> None:
    temp_path = path.with_name(f"{path.stem}.{uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2))
    temp_path.replace(path)


def _read_model(path: Path, model_cls):
    last_error: Exception | None = None
    for _ in range(3):
        try:
            return model_cls.model_validate_json(path.read_text())
        except ValidationError as exc:
            last_error = exc
            sleep(0.05)
    if last_error is not None:
        raise last_error
    raise FileNotFoundError(f"{path.name} could not be read")


def ensure_storage() -> None:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if not list(SCENARIO_DIR.glob("*.json")):
        scenario = ScenarioRecord(
            id=f"scn-{uuid4().hex[:8]}",
            created_at=utc_now(),
            updated_at=utc_now(),
            config=ScenarioConfig.model_validate(deepcopy(DEFAULT_SCENARIO)),
        )
        _write_json(
            SCENARIO_DIR / f"{scenario.id}.json",
            scenario.model_dump(mode="json"),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_scenarios() -> List[ScenarioRecord]:
    ensure_storage()
    scenarios = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        scenarios.append(_read_model(path, ScenarioRecord))
    return scenarios


def get_scenario(scenario_id: str) -> ScenarioRecord:
    path = SCENARIO_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario {scenario_id} does not exist")
    return _read_model(path, ScenarioRecord)


def list_runs() -> List[RunRecord]:
    ensure_storage()
    runs = []
    for path in sorted(RUN_DIR.glob("*.json")):
        try:
            runs.append(_read_model(path, RunRecord))
        except ValidationError:
            continue
    runs.sort(key=lambda run: run.created_at, reverse=True)
    return runs


def create_scenario(config: ScenarioConfig) -> ScenarioRecord:
    ensure_storage()
    scenario = ScenarioRecord(
        id=f"scn-{uuid4().hex[:8]}",
        created_at=utc_now(),
        updated_at=utc_now(),
        config=config,
    )
    save_scenario(scenario)
    return scenario


def save_scenario(scenario: ScenarioRecord) -> ScenarioRecord:
    ensure_storage()
    path = SCENARIO_DIR / f"{scenario.id}.json"
    _write_json(path, scenario.model_dump(mode="json"))
    return scenario


def update_scenario(scenario_id: str, config: ScenarioConfig) -> ScenarioRecord:
    existing = get_scenario(scenario_id)
    updated = ScenarioRecord(
        id=existing.id,
        created_at=existing.created_at,
        updated_at=utc_now(),
        config=config,
    )
    return save_scenario(updated)


def create_run(scenario_id: str) -> RunRecord:
    ensure_storage()
    run = RunRecord(
        id=f"run-{uuid4().hex[:8]}",
        scenario_id=scenario_id,
        status="queued",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    save_run(run)
    return run


def get_run(run_id: str) -> RunRecord:
    path = RUN_DIR / f"{run_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Run {run_id} does not exist")
    return _read_model(path, RunRecord)


def save_run(run: RunRecord) -> RunRecord:
    ensure_storage()
    path = RUN_DIR / f"{run.id}.json"
    _write_json(path, run.model_dump(mode="json"))
    return run
