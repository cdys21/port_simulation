# simulation_processes.py
import random
import simpy
import pandas as pd
import plotly.graph_objects as go
from simulation_models import Container, Vessel, Yard

def vessel_arrival(env, vessel, berths, yards, gates, all_containers, container_type_params,
                   cumulative_unloaded, cumulative_departures):
    yield env.timeout(vessel.actual_arrival)
    print(f"{vessel.name} arrives at {env.now:.2f}")
    
    with berths.request() as req:
        yield req
        vessel.vessel_berths = env.now
        for container in vessel.containers:
            container.vessel_berths = env.now
        print(f"{vessel.name} berths at {env.now:.2f}")
        
        total_containers = len(vessel.containers)
        crane_processes = []
        containers_per_crane = total_containers // 4
        remainder = total_containers % 4
        start = 0
        for i in range(4):
            num = containers_per_crane + (1 if i < remainder else 0)
            crane_containers = vessel.containers[start:start + num]
            start += num
            proc = env.process(crane_unload(env, crane_containers, yards, gates, all_containers,
                                              container_type_params, cumulative_unloaded, cumulative_departures))
            crane_processes.append(proc)
        yield env.all_of(crane_processes)
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

        # Try to add the container to the yard
        added, _ = yard.add_container(container)
        while not added:
            yield env.timeout(1)
            added, _ = yard.add_container(container)

        # Optional short constant delay to simulate positioning (can be removed if undesired)
        yield env.timeout(0.05)

        # Start the inland departure process
        env.process(container_departure(
            env, container, yard, gates, all_containers,
            container_type_params, cumulative_unloaded, cumulative_departures
        ))

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

def container_departure(env, container, yard, gates, all_containers, container_type_params,
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
                # Remove container from yard with retrieval delay based on stacking.
                removed, retrieval_delay = yard.remove_container(container)
                while not removed:
                    yield env.timeout(1)
                    removed, retrieval_delay = yard.remove_container(container)
                yield env.timeout(retrieval_delay)
                container.loaded_for_transport = env.now
                proc_low, proc_high, proc_mode = container_type_params[container.container_type]['truck_process_time']
                process_time = random.triangular(proc_low, proc_high, proc_mode)
                yield env.timeout(process_time)
                if is_gate_open(env.now):
                    container.departed_port = env.now
                    all_containers.append(container)
                    cumulative_departures.append((env.now, container.mode, container.container_type))

def train_departure_process(env, yards, gates, all_containers, cumulative_departures):
    while True:
        yield env.timeout(6)
        ready_containers = []
        for yard in yards.values():
            ready_containers.extend([
                c for c in yard.containers
                if c.mode == "Rail" and c.waiting_for_inland_tsp is not None and c.departed_port is None
            ])
        ready_containers.sort(key=lambda c: c.waiting_for_inland_tsp)
        departing = ready_containers[:750]
        if departing:
            yield env.timeout(2)  # Constant train loading time.
            for container in departing:
                container.loaded_for_transport = env.now
                container.departed_port = env.now
                yard = yards[container.container_type]
                yard.remove_container(container)
                all_containers.append(container)
                cumulative_departures.append((env.now, container.mode, container.container_type))
            print(f"Train departed at {env.now:.2f} with {len(departing)} containers")

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
    import simpy
    import pandas as pd
    from simulation_models import Vessel, Yard  # Make sure these reflect the updated versions

    env = simpy.Environment()
    berths = simpy.Resource(env, capacity=config["berth_count"])
    gates = simpy.Resource(env, capacity=config.get("gate_count", 120))
    
    # Build a dict for container type parameters.
    container_type_params = {ct["name"]: ct for ct in config["container_types"]}
    
    yards = {}
    for ct in config["container_types"]:
        name = ct["name"]
        capacity = ct["yard_capacity"]
        # Calculate initial count based on yard capacity and fill percentage.
        initial_count = int(capacity * ct.get("initial_yard_fill", 0))
        yards[name] = Yard(capacity, initial_count)

        # For pre-filled containers, ensure their container_type is set.
        for container in yards[name].containers:
            container.container_type = name

    # Metrics for monitoring.
    metrics = {
        "yard_occupancy": [],
        "truck_queue": [],
        "rail_queue": [],
        "gate_status": []
    }
    yard_metrics = {yard_name: [] for yard_name in yards.keys()}
    cumulative_unloaded = []      # List of tuples: (time, container_type)
    cumulative_departures = []    # List of tuples: (time, mode, container_type)
    all_containers = []           # All containers that have departed.

    # Start monitoring processes.
    env.process(monitor(env, yards, metrics))
    env.process(monitor_yard_occupancy(env, yards, yard_metrics))
    env.process(train_departure_process(env, yards, gates, all_containers, cumulative_departures))
    
    # Process vessel arrivals.
    for vessel_data in config["vessels"]:
        vessel = Vessel(
            env,
            vessel_data["name"],
            vessel_data["container_counts"],
            vessel_data["day"],
            vessel_data["hour"],
            container_type_params
        )
        env.process(vessel_arrival(env, vessel, berths, yards, gates, all_containers,
                                    container_type_params, cumulative_unloaded, cumulative_departures))
    
    # Process departure for any initial containers in the yards.
    for yard in yards.values():
        for container in yard.containers[:]:
            env.process(container_departure(env, container, yard, gates, all_containers,
                                            container_type_params, cumulative_unloaded, cumulative_departures))
    
    # Run the simulation in 1-hour increments to allow progress updates.
    duration = config.get("simulation_duration", 48)
    for t in range(1, duration + 1):
        env.run(until=t)
        if progress_callback:
            progress_callback(t / duration)
    
    # Create a dataframe from all departed containers.
    df = create_dataframe(all_containers)
    print(f"\nSimulation processed {len(all_containers)} containers.")
    
    # Add cumulative data to metrics for plotting.
    metrics["cumulative_unloaded"] = cumulative_unloaded
    metrics["cumulative_departures"] = cumulative_departures
    
    return df, metrics, yard_metrics
