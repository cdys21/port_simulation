# simulation_processes.py

import random
import simpy
import pandas as pd
import plotly.graph_objects as go
from simulation_models import Container, Vessel, Yard

def vessel_arrival(env, vessel, berths, yards, gates, all_containers,
                   container_type_params, cumulative_unloaded, cumulative_departures,
                   config):
    yield env.timeout(vessel.actual_arrival)
    print(f"{vessel.name} arrives at {env.now:.2f}")

    with berths.request() as req:
        yield req
        vessel.vessel_berths = env.now
        for container in vessel.containers:
            container.vessel_berths = env.now
        print(f"{vessel.name} berths at {env.now:.2f}")

        # use the *current* crane count from config
        total = len(vessel.containers)
        cranes = config["cranes_per_vessel"]
        per = total // cranes
        rem = total % cranes
        start = 0
        procs = []
        for i in range(cranes):
            num = per + (1 if i < rem else 0)
            slice_ = vessel.containers[start:start + num]
            start += num
            procs.append(env.process(
                crane_unload(env, slice_, yards, gates, all_containers,
                             container_type_params, cumulative_unloaded, cumulative_departures)
            ))
        yield env.all_of(procs)
        print(f"{vessel.name} unloading complete at {env.now:.2f}")

def crane_unload(env, containers, yards, gates, all_containers, container_type_params,
                 cumulative_unloaded, cumulative_departures):
    for container in containers:
        unload_low, unload_high, unload_mode = container_type_params[container.container_type]['unload_time']
        unload_time = random.triangular(unload_low, unload_high, unload_mode)
        yield env.timeout(unload_time)
        container.entered_yard = env.now
        cumulative_unloaded.append((env.now, container.container_type))
        yard = yards[container.container_type]
        if yard.add_container(container):
            env.process(truck_departure_process(env, container, yard, gates, all_containers,
                                            container_type_params, cumulative_unloaded, cumulative_departures))

def is_gate_open(time):
    hour = time % 24
    return 6 <= hour < 17

def next_gate_opening(current_time):
    current_hour = current_time % 24
    current_day = current_time // 24
    if current_hour < 6:
        return current_day * 24 + 6
    elif current_hour >= 17:
        return (current_day + 1) * 24 + 6
    else:
        return current_time

def truck_departure_process(env, container, yard, gates, all_containers, container_type_params,
                        cumulative_unloaded, cumulative_departures):
    container.waiting_for_inland_tsp = env.now
    if container.mode == "Road":
        while container.departed_port is None:
            if not is_gate_open(env.now):
                next_open = next_gate_opening(env.now)
                yield env.timeout(next_open - env.now)
                continue
            with gates.request() as req:
                yield req
                if not is_gate_open(env.now):
                    continue
                container.loaded_for_transport = env.now
                proc_low, proc_high, proc_mode = container_type_params[container.container_type]['truck_process_time']
                process_time = random.triangular(proc_low, proc_high, proc_mode)
                yield env.timeout(process_time)
                if is_gate_open(env.now):
                    container.departed_port = env.now
                    yard.remove_container(container)
                    all_containers.append(container)
                    cumulative_departures.append((env.now, container.mode, container.container_type))
    # Rail containers will be handled in train_departure_process

def train_departure_process(env, yards, gates, all_containers, cumulative_departures,
                            trains_per_day, train_capacity):
    interval = 24.0 / trains_per_day
    while True:
        yield env.timeout(interval)
        ready = sorted(
            [c for yard in yards.values() for c in yard.containers
             if c.mode=="Rail" and c.waiting_for_inland_tsp is not None and c.departed_port is None],
            key=lambda c: c.waiting_for_inland_tsp
        )
        batch = ready[:train_capacity]
        if not batch:
            continue
        # simulate load time
        yield env.timeout(2)
        for c in batch:
            c.loaded_for_transport = env.now
            c.departed_port = env.now
            yards[c.container_type].remove_container(c)
            all_containers.append(c)
            cumulative_departures.append((env.now, c.mode, c.container_type))
        print(f"Train departed at {env.now:.2f} with {len(batch)} containers")

def monitor(env, yards, metrics):
    while True:
        total_occupancy = sum(len(yard.containers) for yard in yards.values())
        truck_waiting = sum(len([c for c in yard.containers 
                                  if c.mode == "Road" and c.waiting_for_inland_tsp is not None and c.departed_port is None])
                             for yard in yards.values())
        rail_waiting = sum(len([c for c in yard.containers 
                                 if c.mode == "Rail" and c.waiting_for_inland_tsp is not None and c.departed_port is None])
                            for yard in yards.values())
        gate_status = "Open" if is_gate_open(env.now) else "Closed"
        
        metrics['yard_occupancy'].append((env.now, total_occupancy))
        metrics['truck_queue'].append((env.now, truck_waiting))
        metrics['rail_queue'].append((env.now, rail_waiting))
        metrics['gate_status'].append((env.now, gate_status))
        
        if env.now % 12 < 1:
            print(f"Time: {env.now:.2f} | Total Yard: {total_occupancy} | Truck Queue: {truck_waiting} | "
                  f"Rail Queue: {rail_waiting} | Gates: {gate_status}")
        yield env.timeout(1)

def monitor_yard_occupancy(env, yards, yard_metrics):
    while True:
        for yard_name, yard in yards.items():
            yard_metrics[yard_name].append((env.now, len(yard.containers)))
        yield env.timeout(1)

def create_dataframe(all_containers):
    data = []
    for i, container in enumerate(all_containers):
        data.append({
            "container_id": f"C{i+1}",
            "vessel": container.vessel,
            "container_type": container.container_type,
            "mode": container.mode,
            "vessel_scheduled_arrival": container.vessel_scheduled_arrival,
            "vessel_arrives": container.vessel_arrives,
            "vessel_berths": container.vessel_berths,
            "entered_yard": container.entered_yard,
            "waiting_for_inland_tsp": container.waiting_for_inland_tsp,
            "loaded_for_transport": container.loaded_for_transport,
            "departed_port": container.departed_port
        })
    return pd.DataFrame(data)

def plot_yard_occupancy(yard_metrics):
    fig = go.Figure()
    for yard_name, occupancy_data in yard_metrics.items():
        times = [t for t, occ in occupancy_data]
        occs = [occ for t, occ in occupancy_data]
        fig.add_trace(go.Scatter(x=times, y=occs, mode="lines", name=yard_name))
    fig.update_layout(title="Yard Occupancy per Yard Over Time",
                      xaxis_title="Time (hours)",
                      yaxis_title="Occupancy")
    fig.show()

def run_simulation(
    config,
    progress_callback=None,
    disruption_type=None,
    disruption_t0=None,
    disruption_duration=None,
    recovery_threshold=1.0
):
    """
    Runs one replicate of the port simulation.
    If disruption_type is set, injects a single shock at disruption_t0
    lasting disruption_duration hours, and measures:
      - TTR: time until total yard occupancy ≤ baseline * recovery_threshold
      - time_to_zero: time until yard occupancy == 0
    Returns:
      df           : pandas.DataFrame of container checkpoint times
      metrics      : dict containing time series and, if disrupted, a 'resilience' entry
      yard_metrics : dict of per-yard occupancy time series
    """
    import random
    import simpy
    from simulation_processes import (
        baseline_snapshot, disruption_event,
        monitor, monitor_yard_occupancy,
        train_departure_process, vessel_arrival,
        create_dataframe
    )
    from simulation_models import Yard, Vessel

    # 1. Seed RNG
    if config.get("random_seed") is not None:
        random.seed(config["random_seed"])

    # 2. Create environment and shared resources
    env    = simpy.Environment()
    berths = simpy.Resource(env, capacity=config["berth_count"])
    gates  = simpy.Resource(env, capacity=config["gate_count"])

    # 3. Build yards and collect type parameters
    container_type_params = {ct["name"]: ct for ct in config["container_types"]}
    yards = {}
    for ct in config["container_types"]:
        name   = ct["name"]
        cap    = ct["yard_capacity"]
        init_n = int(cap * ct.get("initial_yard_fill", 0))
        yard   = Yard(cap, init_n)
        # ensure container_type is set on the preloaded containers
        for c in yard.containers:
            c.container_type = name
        yards[name] = yard

    # 4. Initialize metrics containers
    metrics = {
        "yard_occupancy": [],
        "truck_queue":    [],
        "rail_queue":     [],
        "gate_status":    []
    }
    yard_metrics        = {name: [] for name in yards}
    all_containers      = []
    cumulative_unloaded = []
    cumulative_departures = []

    # 5. Schedule disruption helper processes if requested
    baseline_store = {}
    if disruption_type:
        # record the pre-shock yard occupancy
        env.process(baseline_snapshot(env, yards, disruption_t0, baseline_store))
        # inject the shock and restore after duration
        env.process(disruption_event(
            env,
            disruption_type,
            disruption_t0,
            disruption_duration,
            berths, gates,
            config
        ))

    # 6. Start monitoring and train departure processes
    env.process(monitor(env, yards, metrics))
    env.process(monitor_yard_occupancy(env, yards, yard_metrics))
    env.process(train_departure_process(
        env, yards, gates,
        all_containers, cumulative_departures,
        config["trains_per_day"], config["train_capacity"]
    ))

    # 7. Schedule vessel arrivals (unloading)
    for v in config["vessels"]:
        vessel = Vessel(
            env, v["name"], v["container_counts"],
            v["day"], v["hour"], container_type_params
        )
        env.process(vessel_arrival(
            env, vessel, berths, yards, gates,
            all_containers, container_type_params,
            cumulative_unloaded, cumulative_departures,
            config
        ))

    # 8. Kick off departures for initial yard contents
    for yard in yards.values():
        for container in list(yard.containers):
            env.process(truck_departure_process(
                env, container, yard, gates,
                all_containers, container_type_params,
                cumulative_unloaded, cumulative_departures
            ))

    # 9. Run simulation in hourly increments to update progress
    duration = config.get("simulation_duration", 48)
    for hour in range(1, duration + 1):
        env.run(until=hour)
        if progress_callback:
            progress_callback(hour / duration)

    # 10. Collect container‐level data
    df = create_dataframe(all_containers)
    metrics["cumulative_unloaded"]   = cumulative_unloaded
    metrics["cumulative_departures"] = cumulative_departures

    # 11. If disrupted, compute TTR and time_to_zero
    if disruption_type:
        occ      = metrics["yard_occupancy"]  # list of (time, occupancy)
        baseline = baseline_store.get("baseline_occ")
        # find first time ≥ t0 with occupancy ≤ baseline * threshold
        t1 = next(
            (t for t, occv in occ
             if t >= disruption_t0 and occv <= baseline * recovery_threshold),
            None
        )
        TTR = (t1 - disruption_t0) if t1 is not None else None
        # find first time occupancy == 0
        tz = next((t for t, occv in occ if occv == 0), None)

        metrics["resilience"] = {
            "type":           disruption_type,
            "t0":             disruption_t0,
            "baseline_occ":   baseline,
            "t1":             t1,
            "TTR":            TTR,
            "time_to_zero":   tz
        }

    return df, metrics, yard_metrics


# ── NEW HELPER PROCESSES ────────────────────────────────────────

def baseline_snapshot(env, yards, t0, store):
    """At time t0, record the total yard occupancy into store['baseline_occ']."""
    yield env.timeout(t0)
    store['baseline_occ'] = sum(len(y.containers) for y in yards.values())
    print(f"Baseline occupancy ({store['baseline_occ']}) sampled at {env.now:.2f}")

def disruption_event(env, disruption_type, t0, duration, berths, gates, config):
    """At t0, apply the chosen disruption for `duration` hours, then restore."""
    yield env.timeout(t0)
    print(f"** Disruption '{disruption_type}' START at {env.now:.2f}")
    if disruption_type == "Gate Outage":
        # grab the real underlying capacity
        orig = gates._capacity
        # knock out all gates
        gates._capacity = 0
        yield env.timeout(duration)
        # restore original capacity
        gates._capacity = orig
        print(f"** Gates restored at {env.now:.2f}")


    elif disruption_type == "Crane Failure":
        orig = config["cranes_per_vessel"]
        # knock out one crane (but leave at least one)
        config["cranes_per_vessel"] = max(1, orig - 1)
        yield env.timeout(duration)
        config["cranes_per_vessel"] = orig
        print(f"** Cranes restored at {env.now:.2f}")

# ── END NEW PROCESSES ──────────────────────────────────────────