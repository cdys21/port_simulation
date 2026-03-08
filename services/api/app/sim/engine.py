from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Literal, Optional

from ..schemas import ScenarioConfig


Direction = Literal["import", "export"]
Mode = Literal["truck", "rail"]


@dataclass
class Container:
    id: str
    direction: Direction
    container_type: str
    block_id: str
    mode: Mode
    status: str
    target_vessel_id: Optional[str] = None
    actual_vessel_arrival_min: Optional[int] = None
    export_arrival_min: Optional[int] = None
    gate_cutoff_min: Optional[int] = None
    prestage_open_min: Optional[int] = None
    load_cutoff_min: Optional[int] = None
    burial_depth: int = 0
    timestamps: Dict[str, Optional[int]] = field(default_factory=dict)


@dataclass
class VesselState:
    id: str
    name: str
    eta_min: int
    actual_arrival_min: int
    load_cutoff_min: int
    switch_over_minutes: int
    status: str = "scheduled"
    phase: str = "waiting"
    berth_start_min: Optional[int] = None
    departure_min: Optional[int] = None
    berth_slot: Optional[int] = None
    switch_over_end_min: Optional[int] = None
    import_container_ids: List[str] = field(default_factory=list)
    export_container_ids: List[str] = field(default_factory=list)


@dataclass
class YardBlockState:
    id: str
    label: str
    capacity_teu: int
    max_stack_height: int
    occupancy_units: int = 0


@dataclass
class Task:
    kind: str
    end_minute: int
    container_ids: List[str]
    vessel_id: Optional[str] = None


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(math.ceil((pct / 100.0) * len(ordered)) - 1)))
    return float(ordered[index])


class SimulationEngine:
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.random = random.Random(config.random_seed)
        self.current_minute = 0
        self.horizon_minutes = config.horizon_hours * 60
        self.max_minutes = (config.horizon_hours + config.drain_hours) * 60
        self.container_types = {ct.id: ct for ct in config.container_types}
        self.blocks = {
            block.id: YardBlockState(
                id=block.id,
                label=block.label,
                capacity_teu=block.capacity_teu,
                max_stack_height=block.max_stack_height,
            )
            for block in config.yard_blocks
        }
        self.vessels: Dict[str, VesselState] = {}
        self.containers: Dict[str, Container] = {}
        self.berth_waiting: List[str] = []
        self.gate_queue: List[str] = []
        self.rail_receive_queue: List[str] = []
        self.yard_queue: List[str] = []
        self.import_rail_ready: List[str] = []
        self.berth_slots: List[Optional[str]] = [None] * config.resources.berths
        self.active_sts: List[Task] = []
        self.active_gate: List[Task] = []
        self.active_yard: List[Task] = []
        self.active_rail: List[Task] = []
        self.next_import_train_departure_min = self._train_interval_minutes()
        self.snapshot_interval_minutes = 15
        self.timeseries: List[dict] = []
        self.playback_snapshots: List[dict] = []
        self.events: List[dict] = []
        self.event_counts = {
            "import_completed": 0,
            "export_loaded": 0,
            "export_rolled": 0,
        }
        self._gate_was_open = self._is_gate_open(0)
        self._yard_congested = False
        self._gate_congested = False
        self._build_entities()
        self._log_event(
            kind="scenario_start",
            label="Scenario seeded with warm-start inventory and vessel schedule.",
            zone="terminal",
            severity="info",
        )

    def _sample_value(self, tri) -> float:
        return self.random.triangular(tri.minimum, tri.maximum, tri.mode)

    def _sample_duration_minutes(self, tri) -> int:
        return max(1, int(round(self._sample_value(tri))))

    def _sample_duration_hours_to_minutes(self, tri) -> int:
        return max(0, int(round(self._sample_value(tri) * 60)))

    def _train_interval_minutes(self) -> int:
        return max(1, int(round((24 * 60) / self.config.rail.import_departures_per_day)))

    def _is_gate_open(self, minute: int) -> bool:
        hour = (minute // 60) % 24
        return self.config.gate_calendar.open_hour <= hour < self.config.gate_calendar.close_hour

    def _block_fill_rate(self, block_id: str) -> float:
        block = self.blocks[block_id]
        return min(1.0, block.occupancy_units / block.capacity_teu) if block.capacity_teu else 0.0

    def _sample_burial_depth(self, block_id: str) -> int:
        block = self.blocks[block_id]
        fill = self._block_fill_rate(block_id)
        expected = (block.max_stack_height - 1) * (fill ** 1.5)
        sampled = self.random.gauss(expected, 0.75)
        return max(0, min(block.max_stack_height - 1, int(round(sampled))))

    def _putaway_duration(self, block_id: str) -> int:
        fill = self._block_fill_rate(block_id)
        base = self.config.yard_policy.putaway_minutes
        return max(1, int(round(base * (1 + self.config.yard_policy.alpha_putaway * (fill**2)))))

    def _prestage_duration(self, block_id: str, burial_depth: int) -> int:
        fill = self._block_fill_rate(block_id)
        base = self.config.yard_policy.prestage_minutes
        penalty = burial_depth * self.config.yard_policy.reshuffle_minutes
        multiplier = 1 + self.config.yard_policy.beta_retrieval * max(
            0.0, fill - self.config.yard_policy.congestion_threshold
        ) ** 2
        return max(1, int(round((base + penalty) * multiplier)))

    def _retrieve_duration(self, block_id: str, burial_depth: int) -> int:
        fill = self._block_fill_rate(block_id)
        base = self.config.yard_policy.base_retrieve_minutes
        penalty = burial_depth * self.config.yard_policy.reshuffle_minutes
        multiplier = 1 + self.config.yard_policy.beta_retrieval * max(
            0.0, fill - self.config.yard_policy.congestion_threshold
        ) ** 2
        return max(1, int(round((base + penalty) * multiplier)))

    def _log_event(
        self,
        kind: str,
        label: str,
        zone: str,
        severity: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        count: Optional[int] = None,
    ) -> None:
        self.events.append(
            {
                "minute": self.current_minute,
                "hour": round(self.current_minute / 60, 2),
                "kind": kind,
                "label": label,
                "zone": zone,
                "severity": severity,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "count": count,
            }
        )

    def _mark_export_rolled(self, container: Container, reason: str, zone: str) -> None:
        if container.status == "rolled":
            return
        container.status = "rolled"
        self.event_counts["export_rolled"] += 1
        self._log_event(
            kind="export_rolled",
            label=f"Export {container.id} rolled after {reason}.",
            zone=zone,
            severity="warning",
            entity_type="container",
            entity_id=container.id,
        )

    def _yard_counts(self) -> tuple[int, int, int]:
        total_yard = sum(block.occupancy_units for block in self.blocks.values())
        import_yard = sum(
            1
            for container in self.containers.values()
            if container.direction == "import"
            and container.status
            in {
                "in_yard_hold",
                "pickup_eligible",
                "queued_retrieval",
                "retrieving",
                "queued_import_putaway",
                "putting_away",
            }
        )
        export_yard = sum(
            1
            for container in self.containers.values()
            if container.direction == "export"
            and container.status
            in {"in_yard_export", "queued_prestage", "prestaging", "queued_export_putaway", "putting_away", "rolled"}
        )
        return total_yard, import_yard, export_yard

    def _queue_counts(self) -> dict:
        return {
            "berth_queue": len(self.berth_waiting),
            "gate_queue": len(
                [cid for cid in self.gate_queue if self.containers[cid].status.startswith("waiting_gate")]
            ),
            "rail_queue": len(self.import_rail_ready) + len(self.rail_receive_queue),
            "yard_queue": len(self.yard_queue),
        }

    def _flow_counts(self) -> dict:
        return {
            "vessel_to_yard": len([task for task in self.active_sts if task.kind == "discharge_move"]),
            "quay_to_vessel": len([task for task in self.active_sts if task.kind == "load_move"]),
            "gate_to_yard": len([task for task in self.active_gate if task.kind == "export_gate_receive"]),
            "yard_to_gate": len([task for task in self.active_gate if task.kind == "import_gate_exit"]),
            "rail_to_yard": len([task for task in self.active_rail if task.kind == "export_rail_receive"]),
            "yard_to_rail": sum(
                len(task.container_ids) for task in self.active_rail if task.kind == "import_train_batch"
            ),
            "yard_to_quay": len([task for task in self.active_yard if task.kind == "export_prestage"]),
            "yard_retrieval": len([task for task in self.active_yard if task.kind == "import_retrieve"]),
        }

    def _vessel_zone(self, vessel: VesselState) -> str:
        if vessel.status == "scheduled":
            return "scheduled"
        if vessel.status == "waiting_berth":
            return "anchorage"
        if vessel.status == "berthed" and vessel.berth_slot is not None:
            return f"berth-{vessel.berth_slot + 1}"
        if vessel.status == "departed":
            return "departed"
        return "terminal"

    def _record_playback_snapshot(self) -> None:
        total_yard, import_yard, export_yard = self._yard_counts()
        queues = self._queue_counts()
        total_capacity = sum(block.capacity_teu for block in self.blocks.values()) or 1
        self.playback_snapshots.append(
            {
                "minute": self.current_minute,
                "hour": round(self.current_minute / 60, 2),
                "gate_open": self._is_gate_open(self.current_minute),
                "yard": {
                    "total_units": total_yard,
                    "import_units": import_yard,
                    "export_units": export_yard,
                    "fill_rate": round(total_yard / total_capacity, 3),
                },
                "queues": queues,
                "resources": {
                    "berths_in_use": sum(1 for slot in self.berth_slots if slot is not None),
                    "berths_capacity": self.config.resources.berths,
                    "berth_utilization": round(
                        sum(1 for slot in self.berth_slots if slot is not None) / self.config.resources.berths,
                        3,
                    ),
                    "sts_utilization": round(len(self.active_sts) / self.config.resources.sts_cranes, 3),
                    "gate_utilization": round(len(self.active_gate) / self.config.resources.gate_lanes, 3),
                    "yard_utilization": round(len(self.active_yard) / self.config.resources.yard_equipment, 3),
                    "rail_utilization": round(len(self.active_rail) / self.config.resources.rail_slots, 3),
                },
                "flows": self._flow_counts(),
                "counters": {
                    "import_completed": self.event_counts["import_completed"],
                    "export_loaded": self.event_counts["export_loaded"],
                    "export_rolled": self.event_counts["export_rolled"],
                },
                "blocks": [
                    {
                        "id": block.id,
                        "label": block.label,
                        "occupancy": block.occupancy_units,
                        "capacity": block.capacity_teu,
                        "fill_rate": round(self._block_fill_rate(block.id), 3),
                    }
                    for block in self.blocks.values()
                ],
                "vessels": [
                    {
                        "id": vessel.id,
                        "name": vessel.name,
                        "zone": self._vessel_zone(vessel),
                        "status": vessel.status,
                        "phase": vessel.phase,
                        "remaining_imports": sum(
                            1
                            for cid in vessel.import_container_ids
                            if self.containers[cid].status not in {"exited", "yard_overflow"}
                        ),
                        "remaining_exports": sum(
                            1
                            for cid in vessel.export_container_ids
                            if self.containers[cid].status not in {"loaded", "rolled"}
                        ),
                        "quay_ready_exports": sum(
                            1 for cid in vessel.export_container_ids if self.containers[cid].status == "quay_ready"
                        ),
                    }
                    for vessel in self.vessels.values()
                ],
            }
        )

    def _emit_operational_alerts(self) -> None:
        gate_open = self._is_gate_open(self.current_minute)
        if gate_open != self._gate_was_open:
            self._log_event(
                kind="gate_window",
                label=f"Gate {'opened' if gate_open else 'closed'} for truck operations.",
                zone="gate",
                severity="info",
            )
            self._gate_was_open = gate_open

        total_yard, _, _ = self._yard_counts()
        total_capacity = sum(block.capacity_teu for block in self.blocks.values()) or 1
        fill_rate = total_yard / total_capacity
        yard_congested = fill_rate >= self.config.yard_policy.congestion_threshold
        if yard_congested and not self._yard_congested:
            self._log_event(
                kind="yard_congested",
                label=f"Yard fill crossed congestion threshold at {round(fill_rate * 100, 1)}%.",
                zone="yard",
                severity="warning",
            )
        if not yard_congested and self._yard_congested:
            self._log_event(
                kind="yard_recovered",
                label="Yard fill dropped back below the congestion threshold.",
                zone="yard",
                severity="info",
            )
        self._yard_congested = yard_congested

        gate_queue = self._queue_counts()["gate_queue"]
        gate_congested = gate_queue >= self.config.resources.gate_lanes * 3
        if gate_congested and not self._gate_congested:
            self._log_event(
                kind="gate_queue_spike",
                label=f"Gate queue spiked to {gate_queue} trucks waiting.",
                zone="gate",
                severity="warning",
                count=gate_queue,
            )
        if not gate_congested and self._gate_congested:
            self._log_event(
                kind="gate_queue_relieved",
                label="Gate queue dropped back to normal range.",
                zone="gate",
                severity="info",
            )
        self._gate_congested = gate_congested

    def _build_entities(self) -> None:
        export_by_type: Dict[str, List[str]] = {ct.id: [] for ct in self.config.container_types}
        for vessel_cfg in self.config.vessel_calls:
            delay_minutes = int(round(self._sample_value(self.config.vessel_delay_hours) * 60))
            actual_arrival = max(0, int(round(vessel_cfg.eta_hour * 60)) + delay_minutes)
            vessel = VesselState(
                id=vessel_cfg.id,
                name=vessel_cfg.name,
                eta_min=int(round(vessel_cfg.eta_hour * 60)),
                actual_arrival_min=actual_arrival,
                load_cutoff_min=int(round((vessel_cfg.eta_hour + vessel_cfg.load_cutoff_hours_after_eta) * 60)),
                switch_over_minutes=vessel_cfg.switch_over_minutes,
            )
            self.vessels[vessel.id] = vessel
            for type_id, units in vessel_cfg.import_units.items():
                type_cfg = self.container_types[type_id]
                for _ in range(units):
                    container_id = f"imp-{len(self.containers)+1:05d}"
                    mode = "truck" if self.random.random() < type_cfg.import_truck_share else "rail"
                    self.containers[container_id] = Container(
                        id=container_id,
                        direction="import",
                        container_type=type_id,
                        block_id=type_cfg.block_id,
                        mode=mode,
                        status="awaiting_discharge",
                        target_vessel_id=vessel.id,
                        actual_vessel_arrival_min=actual_arrival,
                        timestamps={
                            "scheduled_vessel_arrival": vessel.eta_min,
                            "actual_vessel_arrival": actual_arrival,
                        },
                    )
                    vessel.import_container_ids.append(container_id)
            for type_id, units in vessel_cfg.export_units.items():
                type_cfg = self.container_types[type_id]
                for _ in range(units):
                    container_id = f"exp-{len(self.containers)+1:05d}"
                    mode = "truck" if self.random.random() < type_cfg.export_truck_share else "rail"
                    arrival_min = max(
                        0,
                        vessel.eta_min - self._sample_duration_hours_to_minutes(type_cfg.export_arrival_lead_hours),
                    )
                    cutoff_min = vessel.eta_min - int(round(vessel_cfg.export_cutoff_hours_before_eta * 60))
                    prestage_open_min = vessel.eta_min - int(round(vessel_cfg.prestage_hours_before_eta * 60))
                    self.containers[container_id] = Container(
                        id=container_id,
                        direction="export",
                        container_type=type_id,
                        block_id=type_cfg.block_id,
                        mode=mode,
                        status="awaiting_arrival",
                        target_vessel_id=vessel.id,
                        export_arrival_min=arrival_min,
                        gate_cutoff_min=cutoff_min,
                        prestage_open_min=prestage_open_min,
                        load_cutoff_min=vessel.load_cutoff_min,
                        timestamps={
                            "target_vessel_eta": vessel.eta_min,
                        },
                    )
                    vessel.export_container_ids.append(container_id)
                    export_by_type[type_id].append(container_id)

        for type_cfg in self.config.container_types:
            for i in range(type_cfg.initial_import_units):
                container_id = f"init-imp-{type_cfg.id}-{i+1:04d}"
                mode = "truck" if self.random.random() < type_cfg.import_truck_share else "rail"
                container = Container(
                    id=container_id,
                    direction="import",
                    container_type=type_cfg.id,
                    block_id=type_cfg.block_id,
                    mode=mode,
                    status="pickup_eligible",
                    timestamps={
                        "yard_in": 0,
                        "release_ready": 0,
                    },
                )
                container.burial_depth = self._sample_burial_depth(type_cfg.block_id)
                self.blocks[type_cfg.block_id].occupancy_units += 1
                self.containers[container_id] = container

        for type_cfg in self.config.container_types:
            ready_count = min(type_cfg.initial_export_ready_units, len(export_by_type[type_cfg.id]))
            for container_id in export_by_type[type_cfg.id][:ready_count]:
                container = self.containers[container_id]
                container.status = "in_yard_export"
                container.export_arrival_min = 0
                container.timestamps["yard_in"] = 0
                container.timestamps["gate_in_complete"] = 0 if container.mode == "truck" else None
                container.timestamps["rail_receive_complete"] = 0 if container.mode == "rail" else None
                container.burial_depth = self._sample_burial_depth(container.block_id)
                self.blocks[container.block_id].occupancy_units += 1

    def _active_vessel_work(self, vessel: VesselState) -> bool:
        return any(task.vessel_id == vessel.id for task in self.active_sts)

    def _complete_tasks(self) -> None:
        self._complete_task_group(self.active_sts, self._handle_sts_completion)
        self._complete_task_group(self.active_gate, self._handle_gate_completion)
        self._complete_task_group(self.active_yard, self._handle_yard_completion)
        self._complete_task_group(self.active_rail, self._handle_rail_completion)

    def _complete_task_group(self, tasks: List[Task], handler) -> None:
        finished = [task for task in tasks if task.end_minute <= self.current_minute]
        tasks[:] = [task for task in tasks if task.end_minute > self.current_minute]
        for task in finished:
            handler(task)

    def _handle_sts_completion(self, task: Task) -> None:
        container = self.containers[task.container_ids[0]]
        vessel = self.vessels[task.vessel_id]
        if task.kind == "discharge_move":
            container.timestamps["discharge_end"] = self.current_minute
            container.status = "queued_import_putaway"
            self.yard_queue.append(container.id)
        elif task.kind == "load_move":
            container.timestamps["loaded_on_vessel"] = self.current_minute
            container.status = "loaded"
            self.event_counts["export_loaded"] += 1
        if vessel.phase == "discharge" and not self._has_pending_import_work(vessel):
            vessel.phase = "switch_over"
            vessel.switch_over_end_min = self.current_minute + vessel.switch_over_minutes
            self._log_event(
                kind="vessel_switch_over",
                label=f"{vessel.name} finished discharge and entered switch-over.",
                zone="quay",
                severity="info",
                entity_type="vessel",
                entity_id=vessel.id,
            )

    def _handle_gate_completion(self, task: Task) -> None:
        container = self.containers[task.container_ids[0]]
        if task.kind == "export_gate_receive":
            if container.load_cutoff_min and self.current_minute >= container.load_cutoff_min:
                self._mark_export_rolled(container, "missing the vessel load cutoff", "gate")
                return
            container.timestamps["gate_in_complete"] = self.current_minute
            container.status = "queued_export_putaway"
            self.yard_queue.append(container.id)
        elif task.kind == "import_gate_exit":
            container.timestamps["terminal_exit"] = self.current_minute
            container.status = "exited"
            self.event_counts["import_completed"] += 1

    def _handle_yard_completion(self, task: Task) -> None:
        container = self.containers[task.container_ids[0]]
        block = self.blocks[container.block_id]
        if task.kind in {"import_putaway", "export_putaway"}:
            if block.occupancy_units < block.capacity_teu:
                block.occupancy_units += 1
                container.timestamps["yard_in"] = self.current_minute
                container.burial_depth = self._sample_burial_depth(container.block_id)
                if task.kind == "import_putaway":
                    release_minutes = int(
                        self._sample_duration_hours_to_minutes(
                            self.container_types[container.container_type].import_release_delay_hours
                        )
                    )
                    container.timestamps["release_ready"] = self.current_minute + release_minutes
                    container.status = "in_yard_hold"
                else:
                    container.status = "in_yard_export"
            else:
                container.status = "yard_overflow"
        elif task.kind == "import_retrieve":
            if block.occupancy_units > 0:
                block.occupancy_units -= 1
            container.timestamps["retrieval_complete"] = self.current_minute
            if container.mode == "truck":
                container.status = "waiting_gate_out"
                self.gate_queue.append(container.id)
            else:
                container.status = "waiting_rail_departure"
                self.import_rail_ready.append(container.id)
        elif task.kind == "export_prestage":
            if block.occupancy_units > 0:
                block.occupancy_units -= 1
            container.timestamps["quay_ready"] = self.current_minute
            container.status = "quay_ready"
            container.burial_depth = 0

    def _handle_rail_completion(self, task: Task) -> None:
        if task.kind == "export_rail_receive":
            container = self.containers[task.container_ids[0]]
            if container.load_cutoff_min and self.current_minute >= container.load_cutoff_min:
                self._mark_export_rolled(container, "missing the vessel load cutoff", "rail")
                return
            container.timestamps["rail_receive_complete"] = self.current_minute
            container.status = "queued_export_putaway"
            self.yard_queue.append(container.id)
        elif task.kind == "import_train_batch":
            for container_id in task.container_ids:
                container = self.containers[container_id]
                container.timestamps["terminal_exit"] = self.current_minute
                container.status = "exited"
                self.event_counts["import_completed"] += 1

    def _has_pending_import_work(self, vessel: VesselState) -> bool:
        for container_id in vessel.import_container_ids:
            if self.containers[container_id].status not in {"queued_import_putaway", "in_yard_hold", "pickup_eligible", "queued_retrieval", "retrieving", "waiting_gate_out", "waiting_rail_departure", "gate_service", "rail_service", "exited", "yard_overflow"}:
                return True
        return self._active_vessel_work(vessel)

    def _has_pending_export_work(self, vessel: VesselState) -> bool:
        for container_id in vessel.export_container_ids:
            if self.containers[container_id].status not in {"loaded", "rolled"}:
                return True
        return self._active_vessel_work(vessel)

    def _activate_exogenous(self) -> None:
        for vessel in self.vessels.values():
            if vessel.status == "scheduled" and vessel.actual_arrival_min <= self.current_minute:
                vessel.status = "waiting_berth"
                self.berth_waiting.append(vessel.id)
                self._log_event(
                    kind="vessel_arrived",
                    label=f"{vessel.name} arrived and entered the berth queue.",
                    zone="anchorage",
                    severity="info",
                    entity_type="vessel",
                    entity_id=vessel.id,
                )
        for container in self.containers.values():
            if container.direction == "export" and container.status == "awaiting_arrival":
                if container.export_arrival_min is not None and container.export_arrival_min <= self.current_minute:
                    if container.gate_cutoff_min is not None and self.current_minute > container.gate_cutoff_min:
                        self._mark_export_rolled(container, "arriving after terminal cutoff", "gate")
                    elif container.mode == "truck":
                        container.status = "waiting_gate_in"
                        self.gate_queue.append(container.id)
                    else:
                        container.status = "waiting_rail_receive"
                        self.rail_receive_queue.append(container.id)
            if container.direction == "import" and container.status == "in_yard_hold":
                release_ready = container.timestamps.get("release_ready")
                if release_ready is not None and release_ready <= self.current_minute:
                    container.status = "pickup_eligible"

    def _assign_berths(self) -> None:
        for slot_index, vessel_id in enumerate(self.berth_slots):
            if vessel_id is None and self.berth_waiting:
                next_vessel_id = self.berth_waiting.pop(0)
                vessel = self.vessels[next_vessel_id]
                vessel.status = "berthed"
                vessel.phase = "discharge"
                vessel.berth_start_min = self.current_minute
                vessel.timestamps = getattr(vessel, "timestamps", {})
                vessel.berth_slot = slot_index
                self.berth_slots[slot_index] = next_vessel_id
                self._log_event(
                    kind="vessel_berthed",
                    label=f"{vessel.name} secured berth {slot_index + 1}.",
                    zone="quay",
                    severity="info",
                    entity_type="vessel",
                    entity_id=vessel.id,
                )

    def _advance_vessel_phases(self) -> None:
        for vessel in self.vessels.values():
            if vessel.status != "berthed":
                continue
            if vessel.phase == "switch_over" and vessel.switch_over_end_min is not None:
                if self.current_minute >= vessel.switch_over_end_min:
                    vessel.phase = "load"
                    self._log_event(
                        kind="load_window_open",
                        label=f"{vessel.name} started export loading.",
                        zone="quay",
                        severity="info",
                        entity_type="vessel",
                        entity_id=vessel.id,
                    )
            if vessel.phase == "load":
                for container_id in vessel.export_container_ids:
                    container = self.containers[container_id]
                    if container.status not in {"loaded", "loading", "rolled"}:
                        if vessel.load_cutoff_min <= self.current_minute:
                            self._mark_export_rolled(container, "the vessel load window closing", "quay")
                if not self._has_pending_export_work(vessel):
                    vessel.status = "departed"
                    vessel.departure_min = self.current_minute
                    if vessel.berth_slot is not None:
                        self.berth_slots[vessel.berth_slot] = None
                        vessel.berth_slot = None
                    self._log_event(
                        kind="vessel_departed",
                        label=f"{vessel.name} completed work and departed the terminal.",
                        zone="quay",
                        severity="info",
                        entity_type="vessel",
                        entity_id=vessel.id,
                    )

    def _enqueue_yard_work(self) -> None:
        for container in self.containers.values():
            if container.direction == "import" and container.status == "pickup_eligible":
                container.status = "queued_retrieval"
                self.yard_queue.append(container.id)
            if container.direction == "export" and container.status == "in_yard_export":
                if container.prestage_open_min is not None and self.current_minute >= container.prestage_open_min:
                    container.status = "queued_prestage"
                    self.yard_queue.append(container.id)

    def _start_sts_tasks(self) -> None:
        free_cranes = self.config.resources.sts_cranes - len(self.active_sts)
        if free_cranes <= 0:
            return
        active_vessels = [v for v in self.vessels.values() if v.status == "berthed"]
        while free_cranes > 0:
            assigned = False
            for vessel in active_vessels:
                if vessel.phase == "discharge":
                    pending = next(
                        (
                            c_id
                            for c_id in vessel.import_container_ids
                            if self.containers[c_id].status == "awaiting_discharge"
                        ),
                        None,
                    )
                    if pending:
                        container = self.containers[pending]
                        duration = self._sample_duration_minutes(
                            self.container_types[container.container_type].discharge_minutes
                        )
                        container.status = "discharging"
                        container.timestamps["discharge_start"] = self.current_minute
                        self.active_sts.append(
                            Task(
                                kind="discharge_move",
                                end_minute=self.current_minute + duration,
                                container_ids=[container.id],
                                vessel_id=vessel.id,
                            )
                        )
                        free_cranes -= 1
                        assigned = True
                elif vessel.phase == "load":
                    pending = next(
                        (
                            c_id
                            for c_id in vessel.export_container_ids
                            if self.containers[c_id].status == "quay_ready"
                        ),
                        None,
                    )
                    if pending and self.current_minute < vessel.load_cutoff_min:
                        container = self.containers[pending]
                        duration = self._sample_duration_minutes(
                            self.container_types[container.container_type].load_minutes
                        )
                        container.status = "loading"
                        container.timestamps["load_start"] = self.current_minute
                        self.active_sts.append(
                            Task(
                                kind="load_move",
                                end_minute=self.current_minute + duration,
                                container_ids=[container.id],
                                vessel_id=vessel.id,
                            )
                        )
                        free_cranes -= 1
                        assigned = True
                if free_cranes <= 0:
                    break
            if not assigned:
                break

    def _start_yard_tasks(self) -> None:
        free_units = self.config.resources.yard_equipment - len(self.active_yard)
        if free_units <= 0:
            return
        priorities = {
            "queued_import_putaway": 0,
            "queued_export_putaway": 0,
            "queued_prestage": 1,
            "queued_retrieval": 2,
        }
        self.yard_queue.sort(key=lambda cid: (priorities.get(self.containers[cid].status, 9), cid))
        while free_units > 0 and self.yard_queue:
            container_id = self.yard_queue.pop(0)
            container = self.containers[container_id]
            kind = None
            duration = 0
            if container.status == "queued_import_putaway":
                kind = "import_putaway"
                duration = self._putaway_duration(container.block_id)
                container.status = "putting_away"
            elif container.status == "queued_export_putaway":
                kind = "export_putaway"
                duration = self._putaway_duration(container.block_id)
                container.status = "putting_away"
            elif container.status == "queued_retrieval":
                kind = "import_retrieve"
                duration = self._retrieve_duration(container.block_id, container.burial_depth)
                container.status = "retrieving"
                container.timestamps["retrieval_start"] = self.current_minute
            elif container.status == "queued_prestage":
                kind = "export_prestage"
                duration = self._prestage_duration(container.block_id, container.burial_depth)
                container.status = "prestaging"
                container.timestamps["prestage_start"] = self.current_minute
            if kind:
                self.active_yard.append(
                    Task(
                        kind=kind,
                        end_minute=self.current_minute + duration,
                        container_ids=[container_id],
                    )
                )
                free_units -= 1

    def _start_gate_tasks(self) -> None:
        if not self._is_gate_open(self.current_minute):
            return
        free_lanes = self.config.resources.gate_lanes - len(self.active_gate)
        if free_lanes <= 0:
            return
        self.gate_queue.sort(
            key=lambda cid: (
                self.containers[cid].status not in {"waiting_gate_out", "waiting_gate_in"},
                self.containers[cid].timestamps.get("retrieval_complete", self.current_minute),
                cid,
            )
        )
        while free_lanes > 0 and self.gate_queue:
            container_id = self.gate_queue.pop(0)
            container = self.containers[container_id]
            if container.status == "waiting_gate_in":
                duration = self._sample_duration_minutes(
                    self.container_types[container.container_type].gate_in_minutes
                )
                container.status = "gate_service"
                self.active_gate.append(
                    Task(
                        kind="export_gate_receive",
                        end_minute=self.current_minute + duration,
                        container_ids=[container_id],
                    )
                )
                free_lanes -= 1
            elif container.status == "waiting_gate_out":
                duration = self._sample_duration_minutes(
                    self.container_types[container.container_type].gate_out_minutes
                )
                container.status = "gate_service"
                container.timestamps["exit_service_start"] = self.current_minute
                self.active_gate.append(
                    Task(
                        kind="import_gate_exit",
                        end_minute=self.current_minute + duration,
                        container_ids=[container_id],
                    )
                )
                free_lanes -= 1

    def _start_rail_tasks(self) -> None:
        free_slots = self.config.resources.rail_slots - len(self.active_rail)
        while free_slots > 0 and self.rail_receive_queue:
            container_id = self.rail_receive_queue.pop(0)
            container = self.containers[container_id]
            if container.status == "waiting_rail_receive":
                duration = self._sample_duration_minutes(self.config.rail.export_receive_minutes)
                container.status = "rail_service"
                self.active_rail.append(
                    Task(
                        kind="export_rail_receive",
                        end_minute=self.current_minute + duration,
                        container_ids=[container_id],
                    )
                )
                free_slots -= 1
        if self.current_minute >= self.next_import_train_departure_min and free_slots > 0:
            ready = [cid for cid in self.import_rail_ready if self.containers[cid].status == "waiting_rail_departure"]
            if ready:
                batch = ready[: self.config.rail.train_capacity]
                self.import_rail_ready = [cid for cid in self.import_rail_ready if cid not in batch]
                for cid in batch:
                    self.containers[cid].status = "rail_service"
                    self.containers[cid].timestamps["exit_service_start"] = self.current_minute
                self.active_rail.append(
                    Task(
                        kind="import_train_batch",
                        end_minute=self.current_minute + self.config.rail.train_load_minutes,
                        container_ids=batch,
                    )
                )
                free_slots -= 1
                self._log_event(
                    kind="import_train_departed",
                    label=f"Import train departed with {len(batch)} containers.",
                    zone="rail",
                    severity="info",
                    count=len(batch),
                )
            self.next_import_train_departure_min += self._train_interval_minutes()

    def _record_metrics(self) -> None:
        total_yard, import_yard, export_yard = self._yard_counts()
        queues = self._queue_counts()
        self.timeseries.append(
            {
                "hour": round(self.current_minute / 60, 2),
                "total_yard_units": total_yard,
                "import_yard_units": import_yard,
                "export_yard_units": export_yard,
                "berth_queue": queues["berth_queue"],
                "gate_queue": queues["gate_queue"],
                "rail_queue": queues["rail_queue"],
                "yard_queue": queues["yard_queue"],
                "sts_utilization": round(len(self.active_sts) / self.config.resources.sts_cranes, 3),
                "gate_utilization": round(len(self.active_gate) / self.config.resources.gate_lanes, 3),
                "yard_utilization": round(len(self.active_yard) / self.config.resources.yard_equipment, 3),
            }
        )

    def _clear_after_horizon(self) -> bool:
        if self.current_minute < self.horizon_minutes:
            return False
        active_vessels = any(v.status in {"waiting_berth", "berthed"} for v in self.vessels.values())
        active_tasks = any([self.active_sts, self.active_gate, self.active_yard, self.active_rail])
        queues = any([self.berth_waiting, self.gate_queue, self.rail_receive_queue, self.yard_queue, self.import_rail_ready])
        return not active_vessels and not active_tasks and not queues

    def run(self, progress_callback=None) -> dict:
        for minute in range(self.max_minutes + 1):
            self.current_minute = minute
            self._complete_tasks()
            self._activate_exogenous()
            self._assign_berths()
            self._advance_vessel_phases()
            self._enqueue_yard_work()
            self._start_sts_tasks()
            self._start_yard_tasks()
            self._start_gate_tasks()
            self._start_rail_tasks()
            self._emit_operational_alerts()
            if minute % self.snapshot_interval_minutes == 0:
                self._record_playback_snapshot()
            if minute % 60 == 0:
                self._record_metrics()
                if progress_callback and self.max_minutes:
                    progress_callback(min(1.0, minute / self.max_minutes))
            if self._clear_after_horizon():
                break
        if not self.playback_snapshots or self.playback_snapshots[-1]["minute"] != self.current_minute:
            self._record_playback_snapshot()
        return self._build_result()

    def _build_result(self) -> dict:
        import_dwell = []
        import_port = []
        export_dwell = []
        truck_turn = []
        vessel_turn = []
        container_rows = []
        for container in self.containers.values():
            yard_in = container.timestamps.get("yard_in")
            exit_min = container.timestamps.get("terminal_exit")
            load_min = container.timestamps.get("loaded_on_vessel")
            gate_start = container.timestamps.get("exit_service_start")
            if container.direction == "import" and yard_in is not None and exit_min is not None:
                import_dwell.append((exit_min - yard_in) / 60)
                if container.actual_vessel_arrival_min is not None:
                    import_port.append((exit_min - container.actual_vessel_arrival_min) / 60)
                if gate_start is not None:
                    truck_turn.append(exit_min - gate_start)
            if container.direction == "export" and yard_in is not None and load_min is not None:
                export_dwell.append((load_min - yard_in) / 60)
            row = {
                "id": container.id,
                "direction": container.direction,
                "type": container.container_type,
                "mode": container.mode,
                "status": container.status,
                "target_vessel_id": container.target_vessel_id,
            }
            row.update({key: (value / 60 if value is not None else None) for key, value in container.timestamps.items()})
            container_rows.append(row)
        for vessel in self.vessels.values():
            if vessel.berth_start_min is not None and vessel.departure_min is not None:
                vessel_turn.append((vessel.departure_min - vessel.berth_start_min) / 60)
        summary = {
            "import_completed": self.event_counts["import_completed"],
            "import_unfinished": sum(
                1 for c in self.containers.values() if c.direction == "import" and c.status not in {"exited", "yard_overflow"}
            ),
            "export_loaded": self.event_counts["export_loaded"],
            "export_rolled": self.event_counts["export_rolled"],
            "export_unfinished": sum(
                1 for c in self.containers.values() if c.direction == "export" and c.status not in {"loaded", "rolled"}
            ),
            "peak_yard_units": max((point["total_yard_units"] for point in self.timeseries), default=0),
            "avg_import_dwell_hours": round(mean(import_dwell), 2) if import_dwell else 0.0,
            "p90_import_dwell_hours": round(percentile(import_dwell, 90), 2) if import_dwell else 0.0,
            "avg_import_port_hours": round(mean(import_port), 2) if import_port else 0.0,
            "avg_export_dwell_hours": round(mean(export_dwell), 2) if export_dwell else 0.0,
            "p90_export_dwell_hours": round(percentile(export_dwell, 90), 2) if export_dwell else 0.0,
            "avg_truck_turn_minutes": round(mean(truck_turn), 1) if truck_turn else 0.0,
            "avg_vessel_turnaround_hours": round(mean(vessel_turn), 2) if vessel_turn else 0.0,
        }
        vessel_rows = []
        for vessel in self.vessels.values():
            vessel_rows.append(
                {
                    "id": vessel.id,
                    "name": vessel.name,
                    "eta_hour": round(vessel.eta_min / 60, 2),
                    "ata_hour": round(vessel.actual_arrival_min / 60, 2),
                    "berth_start_hour": round(vessel.berth_start_min / 60, 2) if vessel.berth_start_min is not None else None,
                    "departure_hour": round(vessel.departure_min / 60, 2) if vessel.departure_min is not None else None,
                    "status": vessel.status,
                    "imports": len(vessel.import_container_ids),
                    "exports": len(vessel.export_container_ids),
                    "loaded_exports": sum(
                        1 for cid in vessel.export_container_ids if self.containers[cid].status == "loaded"
                    ),
                    "rolled_exports": sum(
                        1 for cid in vessel.export_container_ids if self.containers[cid].status == "rolled"
                    ),
                }
            )
        return {
            "summary": summary,
            "timeseries": self.timeseries,
            "containers": container_rows,
            "vessels": vessel_rows,
            "playback": {
                "snapshot_interval_minutes": self.snapshot_interval_minutes,
                "duration_hours": round(self.current_minute / 60, 2),
                "snapshots": self.playback_snapshots,
                "events": self.events,
            },
        }
