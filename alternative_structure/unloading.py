# unloading.py

import random
import simpy

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

def crane_unload(env, containers_to_unload, unload_time_params):
    """
    Simulate the unloading of containers by a single crane.
    
    For each container, a triangular distribution is used to determine the unloading time.
    The function yields a timeout for each container and returns a list of finish times,
    which represent the time each container finishes unloading and thus "entered_yard".
    
    Args:
        env (simpy.Environment): The simulation environment.
        containers_to_unload (int): Number of containers the crane will unload.
        unload_time_params (dict): Parameters for the triangular distribution (min, mode, max).
    
    Returns:
        list: Sorted list of finish times for each container unloaded.
    """
    finish_times = []
    for _ in range(containers_to_unload):
        t = random.triangular(
            unload_time_params["min"],
            unload_time_params["max"],
            unload_time_params["mode"]
        )
        yield env.timeout(t)
        finish_times.append(env.now)
    return finish_times

def unload_vessel(env, vessel, berth, unload_time_params):
    """
    Unload a vessel using multiple cranes simultaneously.
    
    This function divides the vessel's containers among the effective cranes available at the berth.
    It creates a separate unloading process for each crane. The finish times returned by each crane
    represent the time when a container finishes unloading and "entered_yard".
    
    Args:
        env (simpy.Environment): The simulation environment.
        vessel: Vessel object (assumed to have a 'container_count' attribute).
        berth: Berth object (assumed to have an attribute 'effective_cranes').
        unload_time_params (dict): Parameters for the triangular distribution (min, mode, max).
    
    Returns:
        list: A sorted list of finish times for all containers unloaded from the vessel.
    """
    effective_cranes = berth.effective_cranes
    total_containers = vessel.container_count
    base = total_containers // effective_cranes
    remainder = total_containers % effective_cranes
    unloading_processes = []
    
    for i in range(effective_cranes):
        # Determine the number of containers assigned to this crane.
        containers_for_crane = base + (1 if i < remainder else 0)
        unloading_processes.append(env.process(crane_unload(env, containers_for_crane, unload_time_params)))
    
    results = yield simpy.events.AllOf(env, unloading_processes)
    
    finish_times = []
    for key in results:
        finish_times.extend(results[key])
    finish_times.sort()
    return finish_times
