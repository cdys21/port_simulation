# simulation/processes.py
import random
import simpy
from .models import Vessel, Container

def vessel_arrival(env, vessel, berths, yard, all_containers, processes_config, gate_resource):
    """Process for vessel arrival, berthing, and unloading."""
    yield env.timeout(vessel.actual_arrival)
    with berths.request() as req:
        yield req
        vessel.vessel_berths = env.now
        for container in vessel.containers:
            container.vessel_berths = env.now
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

def container_departure(env, container, yard, gates, all_containers, processes_config):
    """Process for container departure via truck with simplified state tracking."""
    container.waiting_for_inland_tsp = env.now

    if container.mode == "Road":
        if not is_gate_open(env.now):
            next_open = next_gate_opening(env.now)
            yield env.timeout(next_open - env.now)
        with gates.request() as req:
            yield req
            container.loaded_for_transport = env.now
            process_time = random.triangular(0.1, 0.3, 0.13)
            yield env.timeout(process_time)
            if is_gate_open(env.now):
                container.departed_port = env.now
                yard.remove_container(container)
                all_containers.append(container)
            else:
                env.process(container_departure(env, container, yard, gates, all_containers, processes_config))
    # Rail containers are handled by the train departure process.

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
