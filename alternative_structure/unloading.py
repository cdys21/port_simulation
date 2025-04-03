# unloading.py

import random
import simpy
from container import Container

def unload_container(unload_time_params):
    """
    Generate a random unloading time for one container using a triangular distribution.
    
    Args:
        unload_time_params (dict): Contains 'min', 'mode', and 'max' values for unloading time (in hours).
    
    Returns:
        float: The simulated unloading time for a container (hours).
    """
    return random.triangular(
        unload_time_params["min"],
        unload_time_params["max"],
        unload_time_params["mode"]
    )

def crane_unload(env, containers_to_unload, unload_time_params, yard, vessel, container_id_start, train_percentage, sim_config, container_categories):
    container_id = container_id_start
    cs = sim_config["container_storage"]["triangular_distribution"]  # Storage duration parameters
    for _ in range(containers_to_unload):
        t = random.triangular(unload_time_params["min"], unload_time_params["max"], unload_time_params["mode"])
        yield env.timeout(t)
        # Create and configure the container
        new_container = Container(container_id=container_id, is_initial=False)
        new_container.checkpoints["vessel"] = vessel.name
        new_container.checkpoints["vessel_scheduled_arrival"] = vessel.scheduled_arrival
        new_container.checkpoints["vessel_arrives"] = vessel.actual_arrival
        new_container.checkpoints["vessel_berths"] = env.now - t  # When unloading started
        new_container.checkpoints["entered_yard"] = env.now
        # Set retrieval_ready based on storage duration
        storage_duration = random.triangular(cs["min"], cs["max"], cs["mode"])
        new_container.checkpoints["retrieval_ready"] = env.now + storage_duration
        # Assign mode
        new_container.mode = "Rail" if random.random() < train_percentage else "Road"
        # Set category (use the first category for simplicity, adjust if needed)
        new_container.category = container_categories[0]
        # Add the container to the yard immediately
        yard.add_container(new_container)
        container_id += 1

def unload_vessel(env, vessel, berth, unload_time_params, yard, container_id_start, train_percentage, sim_config, container_categories):
    effective_cranes = berth.effective_cranes
    total_containers = vessel.container_count
    base = total_containers // effective_cranes
    remainder = total_containers % effective_cranes
    crane_processes = []
    current_container_id = container_id_start
    for i in range(effective_cranes):
        containers_for_crane = base + (1 if i < remainder else 0)
        crane_processes.append(env.process(crane_unload(
            env, containers_for_crane, unload_time_params, yard, vessel, current_container_id,
            train_percentage, sim_config, container_categories
        )))
        current_container_id += containers_for_crane
    yield simpy.events.AllOf(env, crane_processes)
