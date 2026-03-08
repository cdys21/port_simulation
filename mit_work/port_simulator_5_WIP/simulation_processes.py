# simulation_processes.py
import random
import simpy
import pandas as pd
import plotly.graph_objects as go
from simulation_models import Container, Vessel, Yard

def vessel_arrival(env, vessel, berths, yards, gates, all_containers, container_type_params,
                   cumulative_unloaded, cumulative_departures, cranes_per_vessel):
    yield env.timeout(vessel.actual_arrival)
    print(f"{vessel.name} arrives at {env.now:.2f}")
    
    with berths.request() as req:
        yield req
        vessel.vessel_berths = env.now
        for container in vessel.containers:
            container.vessel_berths = env.now
        print(f"{vessel.name} berths at {env.now:.2f}")
        
        # divide work among cranes_per_vessel cranes instead of 4
        total = len(vessel.containers)
        per = total // cranes_per_vessel
        rem = total % cranes_per_vessel
        start = 0
        procs = []
        for i in range(cranes_per_vessel):
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

def run_simulation(config, progress_callback=None):
    # seed RNG if provided
    if config.get("random_seed") is not None:
        random.seed(config["random_seed"])

    env = simpy.Environment()
    berths = simpy.Resource(env, capacity=config["berth_count"])
    gates  = simpy.Resource(env, capacity=config["gate_count"])
    
    container_type_params = {ct["name"]: ct for ct in config["container_types"]}
    yards = {}
    for ct in config["container_types"]:
        name = ct["name"]
        capacity = ct["yard_capacity"]
        initial_count = int(capacity * ct.get("initial_yard_fill", 0))
        yards[name] = Yard(capacity, initial_count)
        for container in yards[name].containers:
            container.container_type = name
    
    metrics = {
        "yard_occupancy": [],
        "truck_queue": [],
        "rail_queue": [],
        "gate_status": []
    }
    all_containers = []
    yard_metrics = {yard_name: [] for yard_name in yards.keys()}
    cumulative_unloaded = []      # (time, container_type)
    cumulative_departures = []    # (time, mode, container_type)
    
    # start monitors
    env.process(monitor(env, yards, metrics))
    env.process(monitor_yard_occupancy(env, yards, yard_metrics))
    # pass new params into train process
    env.process(train_departure_process(
        env, yards, gates, all_containers, cumulative_departures,
        config["trains_per_day"], config["train_capacity"]
    ))

    # vessel arrivals: pass cranes_per_vessel
    for v in config["vessels"]:
        vessel = Vessel(env, v["name"], v["container_counts"], v["day"], v["hour"], container_type_params)
        env.process(vessel_arrival(
            env, vessel, berths, yards, gates, all_containers,
            container_type_params, cumulative_unloaded, cumulative_departures,
            config["cranes_per_vessel"]
        ))
    
    for yard in yards.values():
        for container in yard.containers[:]:
            env.process(truck_departure_process(env, container, yard, gates, all_containers,
                                            container_type_params, cumulative_unloaded, cumulative_departures))
    
    duration = config.get("simulation_duration", 48)
    # Run simulation in 1-hour increments to update progress.
    for t in range(1, duration + 1):
        env.run(until=t)
        if progress_callback:
            progress_callback(t / duration)
    
    df = create_dataframe(all_containers)
    print(f"\nSimulation processed {len(all_containers)} containers.")
    
    metrics["cumulative_unloaded"] = cumulative_unloaded
    metrics["cumulative_departures"] = cumulative_departures
    
    return df, metrics, yard_metrics