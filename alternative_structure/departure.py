import random
random.seed(42)

import simpy

def truck_departure_process(env, truck_queue, gate_resource, truck_processing_params):
    """
    Process truck departures.
    
    - truck_queue: list of containers (with mode "Road") waiting for truck departure.
    - gate_resource: SimPy Resource representing the available gates.
    - truck_processing_params: dict with keys 'min', 'mode', 'max' (in minutes) for triangular distribution.
    
    Process:
      - While there are at least 2 containers waiting (since one truck takes 2 containers),
        request a gate, process the truck (simulate processing time),
        and remove the two containers from the queue.
    """
    while True:
        if len(truck_queue) == 0:
            yield env.timeout(0.1)
            continue
        with gate_resource.request() as req:
            yield req
            # Process as many containers as available, up to 2.
            num_to_process = min(2, len(truck_queue))
            containers = [truck_queue.pop(0) for _ in range(num_to_process)]
            # Sample processing time (in minutes) and convert to hours.
            processing_time_minutes = random.triangular(
                truck_processing_params["min"],
                truck_processing_params["max"],
                truck_processing_params["mode"]
            )
            processing_time = processing_time_minutes / 60.0
            #print(f"Time {env.now:.2f}: Truck departing with containers {[c.container_id for c in containers]}, processing time: {processing_time:.2f} hours")
            yield env.timeout(processing_time)

def train_departure_process(env, train_queue, trains_per_day, train_capacity):
    """
    Continuously schedules train departures at fixed intervals and processes up to train_capacity containers per departure.
    """
    departure_interval = 24 / trains_per_day  # hours between departures
    next_departure = env.now  # first departure at current simulation time
    while True:
        # Wait until the next scheduled train departure.
        yield env.timeout(max(0, next_departure - env.now))
        if train_queue:
            num_to_process = min(train_capacity, len(train_queue))
            departing_containers = [train_queue.pop(0) for _ in range(num_to_process)]
            departing_ids = [c.container_id for c in departing_containers]
            #print(f"Time {env.now:.2f}: Train departing with containers {departing_ids}")
        else:
            #print(f"Time {env.now:.2f}: Train departing with no containers")
            pass
        next_departure += departure_interval