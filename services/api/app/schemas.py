from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TriangularConfig(BaseModel):
    minimum: float
    mode: float
    maximum: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "TriangularConfig":
        if not (self.minimum <= self.mode <= self.maximum):
            raise ValueError("Triangular bounds must satisfy minimum <= mode <= maximum")
        return self


class ResourceConfig(BaseModel):
    berths: int = Field(ge=1)
    sts_cranes: int = Field(ge=1)
    yard_equipment: int = Field(ge=1)
    gate_lanes: int = Field(ge=1)
    rail_slots: int = Field(ge=1)


class GateCalendar(BaseModel):
    open_hour: int = Field(ge=0, le=23)
    close_hour: int = Field(ge=1, le=24)


class RailConfig(BaseModel):
    import_departures_per_day: int = Field(ge=1)
    train_capacity: int = Field(ge=1)
    train_load_minutes: int = Field(ge=1)
    export_receive_minutes: TriangularConfig


class YardPolicy(BaseModel):
    putaway_minutes: float = Field(gt=0)
    prestage_minutes: float = Field(gt=0)
    base_retrieve_minutes: float = Field(gt=0)
    reshuffle_minutes: float = Field(gt=0)
    alpha_putaway: float = Field(ge=0)
    beta_retrieval: float = Field(ge=0)
    congestion_threshold: float = Field(ge=0, le=1)


class YardBlockConfig(BaseModel):
    id: str
    label: str
    capacity_teu: int = Field(ge=1)
    max_stack_height: int = Field(ge=1)


class ContainerTypeConfig(BaseModel):
    id: str
    label: str
    block_id: str
    initial_import_units: int = Field(ge=0)
    initial_export_ready_units: int = Field(ge=0)
    import_truck_share: float = Field(ge=0, le=1)
    export_truck_share: float = Field(ge=0, le=1)
    import_release_delay_hours: TriangularConfig
    export_arrival_lead_hours: TriangularConfig
    gate_in_minutes: TriangularConfig
    gate_out_minutes: TriangularConfig
    discharge_minutes: TriangularConfig
    load_minutes: TriangularConfig


class VesselCallConfig(BaseModel):
    id: str
    name: str
    eta_hour: float = Field(ge=0)
    export_cutoff_hours_before_eta: float = Field(ge=0)
    prestage_hours_before_eta: float = Field(ge=0)
    load_cutoff_hours_after_eta: float = Field(ge=0)
    switch_over_minutes: int = Field(ge=0)
    import_units: Dict[str, int]
    export_units: Dict[str, int]


class ScenarioConfig(BaseModel):
    name: str
    description: str = ""
    horizon_hours: int = Field(ge=1)
    drain_hours: int = Field(ge=0)
    random_seed: int = 42
    vessel_delay_hours: TriangularConfig
    resources: ResourceConfig
    gate_calendar: GateCalendar
    rail: RailConfig
    yard_policy: YardPolicy
    yard_blocks: List[YardBlockConfig]
    container_types: List[ContainerTypeConfig]
    vessel_calls: List[VesselCallConfig]


class ScenarioRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    config: ScenarioConfig


class RunSummary(BaseModel):
    import_completed: int
    import_unfinished: int
    export_loaded: int
    export_rolled: int
    export_unfinished: int
    peak_yard_units: int
    avg_import_dwell_hours: float
    p90_import_dwell_hours: float
    avg_export_dwell_hours: float
    p90_export_dwell_hours: float
    avg_truck_turn_minutes: float
    avg_vessel_turnaround_hours: float


class RunRecord(BaseModel):
    id: str
    scenario_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    progress: float = 0.0
    error: Optional[str] = None
    result: Optional[dict] = None

