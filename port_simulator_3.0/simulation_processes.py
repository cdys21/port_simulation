# simulation_processes.py
import random
import simpy
import pandas as pd
import matplotlib.pyplot as plt
from simulation_models import Container, Vessel, Yard

def vessel_arrival(env, vessel, berths, yards, gates, all_containers, container_type_params,
                   cumulative_unloaded, cumulative_departures):
    """
    Process vessel arrival, berthing, and unloading.
    Containers are routed to their type-specific yard.
    """
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
    """
    Unloads a group of containers and places each in its corresponding yard.
    Uses type-specific unloading times.
    """
    for container in containers:
        unload_low, unload_high, unload_mode = container_type_params[container.container_type]['unload_time']
        unload_time = random.triangular(unload_low, unload_high, unload_mode)
        yield env.timeout(unload_time)
        container.entered_yard = env.now
        cumulative_unloaded.append((env.now, container.container_type))
        yard = yards[container.container_type]
        if yard.add_container(container):
            env.process(container_departure(env, container, yard, gates, all_containers,
                                             container_type_params, cumulative_unloaded, cumulative_departures))

def is_gate_open(time):
    """Return True if gates are open (06:00 to 17:00)."""
    hour = time % 24
    return 6 <= hour < 17

def next_gate_opening(current_time):
    """Calculate the next time when gates will be open."""
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
    """
    Process a container's departure via truck.
    Truck process times are type-specific.
    """
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
    # Rail containers are handled by train_departure_process

def train_departure_process(env, yards, gates, all_containers, cumulative_departures):
    """
    Process train departures every 6 hours for all rail containers across yards.
    (Train loading time is constant.)
    """
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
            yield env.timeout(2)  # Constant 2 hours loading time.
            for container in departing:
                container.loaded_for_transport = env.now
                container.departed_port = env.now
                yard = yards[container.container_type]
                yard.remove_container(container)
                all_containers.append(container)
                cumulative_departures.append((env.now, container.mode, container.container_type))
            print(f"Train departed at {env.now:.2f} with {len(departing)} containers")

def monitor(env, yards, metrics):
    """
    Monitors overall yard occupancy and queue lengths.
    """
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
    """
    Monitors occupancy per yard over time.
    """
    while True:
        for yard_name, yard in yards.items():
            yard_metrics[yard_name].append((env.now, len(yard.containers)))
        yield env.timeout(1)

def create_dataframe(all_containers):
    """
    Generates a DataFrame summarizing container checkpoints.
    """
    data = []
    for i, container in enumerate(all_containers):
        data.append({
            'container_id': f'C{i+1}',
            'vessel': container.vessel,
            'container_type': container.container_type,
            'mode': container.mode,
            'vessel_scheduled_arrival': container.vessel_scheduled_arrival,
            'vessel_arrives': container.vessel_arrives,
            'vessel_berths': container.vessel_berths,
            'entered_yard': container.entered_yard,
            'waiting_for_inland_tsp': container.waiting_for_inland_tsp,
            'loaded_for_transport': container.loaded_for_transport,
            'departed_port': container.departed_port
        })
    return pd.DataFrame(data)

def plot_yard_occupancy(yard_metrics):
    """
    Plots the occupancy over time for each yard.
    """
    plt.figure(figsize=(10, 6))
    for yard_name, occupancy_data in yard_metrics.items():
        times = [t for t, occ in occupancy_data]
        occupancies = [occ for t, occ in occupancy_data]
        plt.plot(times, occupancies, label=yard_name)
    plt.xlabel("Time (hours)")
    plt.ylabel("Yard Occupancy")
    plt.title("Yard Occupancy per Yard Over Time")
    plt.legend()
    plt.show()

def run_simulation(config):
    """
    Sets up and runs the simulation with multiple container types and type-specific parameters.
    Also monitors various events.
    """
    env = simpy.Environment()
    berths = simpy.Resource(env, capacity=config['berth_count'])
    gates = simpy.Resource(env, capacity=config.get('gate_count', 120))
    
    container_type_params = {ct['name']: ct for ct in config['container_types']}
    
    yards = {}
    for ct in config['container_types']:
        name = ct['name']
        capacity = ct['yard_capacity']
        initial_count = int(capacity * ct.get('initial_yard_fill', 0))
        yards[name] = Yard(capacity, initial_count)
        for container in yards[name].containers:
            container.container_type = name
    
    metrics = {
        'yard_occupancy': [],
        'truck_queue': [],
        'rail_queue': [],
        'gate_status': []
    }
    all_containers = []
    yard_metrics = {yard_name: [] for yard_name in yards.keys()}
    cumulative_unloaded = []      # List of tuples: (time, container_type)
    cumulative_departures = []    # List of tuples: (time, mode, container_type)
    
    env.process(monitor(env, yards, metrics))
    env.process(monitor_yard_occupancy(env, yards, yard_metrics))
    env.process(train_departure_process(env, yards, gates, all_containers, cumulative_departures))
    
    for vessel_data in config['vessels']:
        vessel = Vessel(
            env,
            vessel_data['name'],
            vessel_data['container_counts'],
            vessel_data['day'],
            vessel_data['hour'],
            container_type_params
        )
        env.process(vessel_arrival(env, vessel, berths, yards, gates, all_containers,
                                    container_type_params, cumulative_unloaded, cumulative_departures))
    
    for yard in yards.values():
        for container in yard.containers[:]:
            env.process(container_departure(env, container, yard, gates, all_containers,
                                            container_type_params, cumulative_unloaded, cumulative_departures))
    
    env.run(until=config.get('simulation_duration', 48))
    
    df = create_dataframe(all_containers)
    if config.get('save_csv', False):
        df.to_csv(config.get('output_file', 'container_checkpoints.csv'), index=False)
        print(f"\nSaved {len(all_containers)} containers to '{config.get('output_file', 'container_checkpoints.csv')}'")
    
    print("\nSIMULATION SUMMARY:")
    print(f"Number of containers processed: {len(all_containers)}")
    if all_containers:
        road_containers = sum(1 for c in all_containers if c.mode == "Road")
        rail_containers = sum(1 for c in all_containers if c.mode == "Rail")
        print(f"Containers by mode: Road {road_containers} ({road_containers/len(all_containers)*100:.1f}%), "
              f"Rail {rail_containers} ({rail_containers/len(all_containers)*100:.1f}%)")
        departed_containers = [c for c in all_containers if c.departed_port is not None and c.entered_yard is not None]
        if departed_containers:
            dwell_times = [c.departed_port - c.entered_yard for c in departed_containers]
            avg_dwell = sum(dwell_times) / len(dwell_times)
            print(f"Average dwell time: {avg_dwell:.2f} hours")
    total_remaining = sum(len(yard.containers) for yard in yards.values())
    print(f"Containers remaining in all yards: {total_remaining}")
    
    plot_yard_occupancy(yard_metrics)
    
    # Add cumulative events to metrics.
    metrics['cumulative_unloaded'] = cumulative_unloaded
    metrics['cumulative_departures'] = cumulative_departures
    
    return df, metrics, yard_metrics
