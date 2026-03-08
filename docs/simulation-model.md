# Simulation Model

## What The Model Represents

The simulation represents one container terminal where imports and exports compete for the same operational resources. The core design objective is logical cause-and-effect:

- More vessel work increases berth and STS pressure.
- More yard fill increases putaway, prestage, retrieval, and reshuffle time.
- Gate and rail limits create visible queueing and dwell changes.
- Export cutoff rules can turn inland lateness into vessel rollover.

## Time Scale

- Internal clock: `minutes`
- Chart resolution: `hourly`
- Scenario horizon: `horizon_hours`
- Drain window: `drain_hours`

The engine continues after the main horizon only to drain residual work already admitted into the system. It does not admit new exogenous demand after the horizon.

## Start Criteria

Each run starts with:

- A full scenario configuration.
- Existing import inventory already in yard.
- Existing export-ready inventory already in yard.
- A planned vessel schedule.
- Gate hours, rail settings, and yard policies already defined.

## End Criteria

The run stops when either:

- The engine reaches `horizon + drain`, or
- The main horizon has passed and the system has fully cleared its active work and queues.

The result still reports unfinished imports, unfinished exports, and rolled export loads.

## Shared Resources

All major resources are global and shared:

- `berths`
- `sts_cranes`
- `yard_equipment`
- `gate_lanes`
- `rail_slots`

No vessel receives a private crane pool. Imports and exports consume the same terminal capacity.

## Entities

### Containers

Each container has:

- `direction`: import or export
- `container_type`
- `block_id`
- `mode`: truck or rail
- `status`
- target vessel linkage where relevant
- per-container timestamps
- burial depth for stacking logic

### Vessels

Each vessel has:

- planned ETA
- stochastic actual arrival
- import workload
- export workload
- switch-over duration between discharge and load
- berth status and service timestamps

### Yard Blocks

Each yard block has:

- TEU capacity
- max stack height
- occupancy

The block tied to a container type determines its fill rate and stacking behavior.

## Import Flow

Import containers follow this chain:

1. `awaiting_discharge`
2. `discharging`
3. `queued_import_putaway`
4. `putting_away`
5. `in_yard_hold`
6. `pickup_eligible`
7. `queued_retrieval`
8. `retrieving`
9. `waiting_gate_out` or `waiting_rail_departure`
10. `gate_service` or `rail_service`
11. `exited`

### Import Timing Rules

- Vessel actual arrival is ETA plus a triangular delay distribution.
- Imports only begin discharge after the vessel gets a berth and an STS crane.
- After discharge, imports require yard putaway.
- Once in yard, each import receives a business release delay.
- Only after release can it enter retrieval.
- Truck imports require gate-open hours and a gate service time.
- Rail imports wait for the next train batch and train loading duration.

## Export Flow

Export containers follow this chain:

1. `awaiting_arrival`
2. `waiting_gate_in` or `waiting_rail_receive`
3. `gate_service` or `rail_service`
4. `queued_export_putaway`
5. `putting_away`
6. `in_yard_export`
7. `queued_prestage`
8. `prestaging`
9. `quay_ready`
10. `loading`
11. `loaded`

Failure path:

- `rolled`

### Export Timing Rules

- Each export belongs to a target vessel.
- Inland arrival happens before vessel ETA according to a lead-time distribution.
- If inland arrival happens after gate cutoff, the export is immediately rolled.
- Truck exports use gate lanes; rail exports use rail receive capacity.
- Once received, exports are put into yard.
- They wait in yard until the prestage window opens.
- Prestage competes for yard equipment.
- Loaded exports must still fit within the vessel load cutoff window.
- If the vessel reaches its load cutoff before a box is loaded, that box rolls.

## Vessel Service Logic

Vessels move through:

1. `scheduled`
2. `waiting_berth`
3. `berthed`
4. `discharge phase`
5. `switch_over`
6. `load phase`
7. `departed`

MVP berth logic is intentionally simple:

- A vessel must secure a berth slot before work starts.
- While in discharge phase, STS cranes are assigned to import discharge moves.
- When all imports are discharged, the vessel enters switch-over.
- After switch-over, STS cranes load `quay_ready` exports.
- When all export work is either loaded or rolled, the vessel departs and frees the berth.

## Yard Stacking Logic

This is the first nonlinear congestion rule in the MVP.

### Fill Rate

For each block:

`fill_rate = occupancy_units / capacity_teu`

### Burial Depth

When a container enters yard, it receives a burial depth based on current fill:

- low fill produces shallow burial
- high fill produces deeper burial
- burial depth is capped by `max_stack_height - 1`

### Putaway Time

Putaway rises with congestion:

`putaway = base_putaway * (1 + alpha_putaway * fill_rate^2)`

### Retrieval And Prestage Time

Retrieval and export prestage use:

- a base service time
- plus `burial_depth * reshuffle_minutes`
- times a congestion multiplier when fill exceeds the threshold

The congestion multiplier is:

`1 + beta_retrieval * max(0, fill_rate - congestion_threshold)^2`

This means higher fill slows flow in a believable way:

- more filled yard
- deeper burial
- more reshuffles
- slower retrieval/prestage
- longer queueing and dwell

## Resource Arbitration

### STS

STS capacity is shared across all berthed vessels. The engine repeatedly assigns free cranes to:

- discharge work first if a vessel is in discharge phase
- export loading when a vessel is in load phase

### Yard Equipment

Yard tasks are prioritized as:

1. import putaway
2. export putaway
3. export prestage
4. import retrieval

### Gates

- Gates only process when the terminal is open.
- Imports and exports use the same gate pool.
- Truck service times are type-specific.

### Rail

- Export rail receiving uses shared rail slots continuously.
- Import rail departures happen in train batches on a fixed interval.
- Each train has a maximum capacity and loading duration.

## Output Metrics

### Summary KPIs

- imports completed
- imports unfinished
- exports loaded
- exports rolled
- exports unfinished
- peak yard units
- average and p90 import dwell
- average import port time
- average and p90 export dwell
- average truck turn time
- average vessel turnaround

### Hourly Timeseries

- total yard units
- import yard units
- export yard units
- berth queue
- gate queue
- rail queue
- yard queue
- STS utilization
- gate utilization
- yard utilization

### Container Rows

Each row includes:

- direction
- type
- mode
- status
- target vessel
- all recorded timestamps converted to hours

### Vessel Rows

Each row includes:

- ETA
- ATA
- berth start
- departure
- status
- total import count
- total export count
- loaded export count
- rolled export count

## Simplifications

The current model intentionally does not yet include:

- 2D yard geometry
- labor classes or shift-specific productivity changes
- chassis pools
- dual cycling or advanced crane balancing
- customs hold categories by commodity
- rail network delays outside terminal-side handling

Those can be added later without changing the basic state-machine structure.
