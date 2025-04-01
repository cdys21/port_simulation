# unloading.py

import random
import simpy
random.seed(42)

def unload_container(unload_time_params):
    """
    Generate a random unloading time for one container using a triangular distribution.
    """
    return random.triangular(
        unload_time_params["min"],
        unload_time_params["max"],
        unload_time_params["mode"]
    )

def crane_unload(env, containers_to_unload, unload_time_params):
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
    effective_cranes = berth.effective_cranes
    total_containers = vessel.container_count
    base = total_containers // effective_cranes
    remainder = total_containers % effective_cranes
    unloading_processes = []
    start_time = env.now
    for i in range(effective_cranes):
        containers_for_crane = base + (1 if i < remainder else 0)
        unloading_processes.append(env.process(crane_unload(env, containers_for_crane, unload_time_params)))
    results = yield simpy.events.AllOf(env, unloading_processes)
    finish_times = []
    for key in results:
        finish_times.extend(results[key])
    finish_times.sort()
    # Return a list of unloading durations for each container.
    container_unload_durations = [ft - start_time for ft in finish_times]
    return container_unload_durations

## Testing the unloading module.
#if __name__ == '__main__':
#    # Set seed for reproducibility.
#    random.seed(42)
#    
#    # Create a SimPy simulation environment.
#    env = simpy.Environment()
#    
#    # Dummy vessel and berth classes for testing.
#    class DummyVessel:
#        def __init__(self, container_count):
#            self.container_count = container_count
#    
#    class DummyBerth:
#        def __init__(self, effective_cranes):
#            self.effective_cranes = effective_cranes
#    
#    # Create a dummy vessel with 100 containers.
#    vessel = DummyVessel(container_count=1000)
#    # Create a dummy berth with 4 effective cranes.
#    berth = DummyBerth(effective_cranes=4)
#    
#    # Default unloading time parameters (in hours per container).
#    unload_time_params = {"min": 0.03, "mode": 0.04, "max": 0.06}
#    
#    def test_unloading(env, vessel, berth, unload_time_params):
#        print(f"Time {env.now:.2f}: Starting unloading process")
#        unloading_duration = yield env.process(unload_vessel(env, vessel, berth, unload_time_params))
#        print(f"Time {env.now:.2f}: Unloading completed in {unloading_duration:.4f} hours")
#    
#    # Start the test process.
#    env.process(test_unloading(env, vessel, berth, unload_time_params))
#    env.run()