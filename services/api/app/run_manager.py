from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from .schemas import RunRecord
from .sim.engine import SimulationEngine
from .storage import get_run, get_scenario, save_run, utc_now


EXECUTOR = ThreadPoolExecutor(max_workers=2)
RUN_FUTURES: Dict[str, object] = {}


def submit_run(run_id: str) -> None:
    future = EXECUTOR.submit(_execute_run, run_id)
    RUN_FUTURES[run_id] = future


def _execute_run(run_id: str) -> None:
    run = get_run(run_id)
    scenario = get_scenario(run.scenario_id)
    run.status = "running"
    run.updated_at = utc_now()
    run.progress = 0.02
    save_run(run)

    def update_progress(progress: float) -> None:
        current = get_run(run_id)
        current.progress = progress
        current.updated_at = utc_now()
        save_run(current)

    try:
        engine = SimulationEngine(scenario.config)
        result = engine.run(progress_callback=update_progress)
        completed = get_run(run_id)
        completed.status = "completed"
        completed.progress = 1.0
        completed.updated_at = utc_now()
        completed.result = result
        save_run(completed)
    except Exception as exc:  # pragma: no cover - surfaced through API state
        failed = get_run(run_id)
        failed.status = "failed"
        failed.error = str(exc)
        failed.updated_at = utc_now()
        save_run(failed)

