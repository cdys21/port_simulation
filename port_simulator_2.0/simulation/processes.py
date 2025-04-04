# simulation/processes.py
import random
import simpy
from .models import Vessel, Container

def vessel_arrival(env, vessel, berths, yard, all_containers, processes_config, gate_resource):
    """Process for vessel arrival, berthing, and unloading."""
    yield env.timeout(vessel.actual_arrival)
    #print(f"{vessel.name} arrives at {env.now:.2f}")
    with berths.request() as req:
        yield req
        vessel.vessel_berths = env.now
        for container in vessel.containers:
            container.vessel_berths = env.now
        #print(f"{vessel.name} berths at {env.now:.2f}")
        crane_processes = []
        cranes = 4  # Number of cranes per berth
        containers_per_crane = vessel.container_count // cranes
        remainder = vessel.container_count % cranes
        start = 0
        for i in range(cranes):
            num = containers_per_crane + (1 if i < remainder else 0)
            crane_containers = vessel.containers[start:start+num]
            start += num
            proc = env.process(crane_unload(env, crane_containers, yard, all_containers, processes_config, gate_resource))
            crane_processes.append(proc)
        yield env.all_of(crane_processes)
        #print(f"{vessel.name} unloading complete at {env.now:.2f}")

def crane_unload(env, containers, yard, all_containers, processes_config, gate_resource):
    """Process for unloading containers with a crane."""
    unload_params = processes_config.get('crane_unload', {})
    min_time = unload_params.get('min', 0.01)
    max_time = unload_params.get('max', 0.033)
    mode_time = unload_params.get('mode', 0.5)
    for container in containers:
        unload_time = random.triangular(min_time, max_time, mode_time)
        yield env.timeout(unload_time)
        container.entered_yard = env.now
        # Start container departure process once container enters yard.
        if yard.add_container(container):
            env.process(container_departure(env, container, yard, gate_resource, all_containers, processes_config))

def is_gate_open(time):
    """Check if gates are open based on the time (6 AM to 5 PM)."""
    hour = time % 24
    return 6 <= hour < 17

def next_gate_opening(current_time):
    """Calculate the next gate opening time."""
    current_hour = current_time % 24
    current_day = current_time // 24
    if current_hour < 6:
        return current_day * 24 + 6
    elif current_hour >= 17:
        return (current_day + 1) * 24 + 6
    else:
        return current_time

def container_departure(env, container, yard, gate_resource, all_containers, processes_config):
    """Process for container departure using road (truck) logic."""
    # Only set waiting_for_inland_tsp if it hasn't been set already
    if container.waiting_for_inland_tsp is None:
        container.waiting_for_inland_tsp = env.now

    if container.mode == "Road":
        if not is_gate_open(env.now):
            next_open = next_gate_opening(env.now)
            yield env.timeout(next_open - env.now)
        with gate_resource.request() as req:
            yield req
            if not is_gate_open(env.now):
                env.process(container_departure(env, container, yard, gate_resource, all_containers, processes_config))
                return
            container.loaded_for_transport = env.now
            truck_params = processes_config.get('truck_departure', {})
            min_time = truck_params.get('min', 0.1)
            max_time = truck_params.get('max', 0.3)
            mode_time = truck_params.get('mode', 0.13)
            process_time = random.triangular(min_time, max_time, mode_time)
            yield env.timeout(process_time)
            if is_gate_open(env.now):
                container.departed_port = env.now
                yard.remove_container(container)
                all_containers.append(container)
            else:
                env.process(container_departure(env, container, yard, gate_resource, all_containers, processes_config))

def train_departure_process(env, yard, gate_resource, all_containers, processes_config):
    """Process for train departures every 6 hours."""
    train_params = processes_config.get('train_departure', {})
    loading_time = train_params.get('loading_time', 2)
    capacity = train_params.get('capacity', 750)
    while True:
        yield env.timeout(6)
        ready_containers = [
            c for c in yard.containers
            if c.mode == "Rail" and c.waiting_for_inland_tsp is not None and c.departed_port is None
        ]
        ready_containers.sort(key=lambda c: c.waiting_for_inland_tsp)
        departing = ready_containers[:capacity]
        if departing:
            yield env.timeout(loading_time)
            for container in departing:
                container.loaded_for_transport = env.now
                container.departed_port = env.now
                yard.remove_container(container)
                all_containers.append(container)
            #print(f"Train departed at {env.now:.2f} with {len(departing)} containers")

def monitor(env, yard, metrics):
    """Monitor yard occupancy and queue lengths."""
    while True:
        occupancy = len(yard.containers)
        truck_waiting = len([
            c for c in yard.containers
            if c.mode == "Road" and c.waiting_for_inland_tsp is not None and c.departed_port is None
        ])
        rail_waiting = len([
            c for c in yard.containers
            if c.mode == "Rail" and c.waiting_for_inland_tsp is not None and c.departed_port is None
        ])
        gate_status = "Open" if is_gate_open(env.now) else "Closed"
        metrics['yard_occupancy'].append((env.now, occupancy))
        metrics['truck_queue'].append((env.now, truck_waiting))
        metrics['rail_queue'].append((env.now, rail_waiting))
        metrics['gate_status'].append((env.now, gate_status))
        if env.now % 12 < 1:
            print(f"Time: {env.now:.2f} | Yard: {occupancy} | Truck Queue: {truck_waiting} | Rail Queue: {rail_waiting} | Gates: {gate_status}")
            pass
        yield env.timeout(1)
