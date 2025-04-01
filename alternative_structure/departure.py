# departure.py

import random
random.seed(42)
import simpy

def truck_departure_process(env, truck_queue, gate_resource, truck_processing_params, metrics=None):
    """
    Continuously processes truck departures. Each truck processes up to 2 containers.
    For each container processed, inland transport wait = departure time - container.retrieval_time.
    """
    while True:
        if len(truck_queue) == 0:
            yield env.timeout(0.1)
            continue
        with gate_resource.request() as req:
            yield req
            num_to_process = min(2, len(truck_queue))
            containers = [truck_queue.pop(0) for _ in range(num_to_process)]
            processing_time_minutes = random.triangular(
                truck_processing_params["min"],
                truck_processing_params["max"],
                truck_processing_params["mode"]
            )
            processing_time = processing_time_minutes
            #print(f"Time {env.now:.2f}: Truck departing with containers {[c.container_id for c in containers]}, processing time: {processing_time:.2f} hours")
            for c in containers:
                if hasattr(c, 'retrieval_time') and not c.is_initial:
                    inland_wait = env.now - c.retrieval_time
                    if metrics:
                        metrics.record_inland_transport_wait(inland_wait)
            yield env.timeout(processing_time)

def train_departure_process(env, train_queue, trains_per_day, train_capacity, metrics=None):
    """
    Continuously schedules train departures at fixed intervals and processes up to train_capacity containers per departure.
    For each container processed, inland transport wait = departure time - container.retrieval_time.
    """
    departure_interval = 24 / trains_per_day
    next_departure = env.now
    while True:
        yield env.timeout(max(0, next_departure - env.now))
        if train_queue:
            num_to_process = min(train_capacity, len(train_queue))
            departing_containers = [train_queue.pop(0) for _ in range(num_to_process)]
            departing_ids = [c.container_id for c in departing_containers]
            #print(f"Time {env.now:.2f}: Train departing with containers {departing_ids}")
            for c in departing_containers:
                if hasattr(c, 'retrieval_time') and not c.is_initial:
                    inland_wait = env.now - c.retrieval_time
                    if metrics:
                        metrics.record_inland_transport_wait(inland_wait)
        else:
            pass
            #print(f"Time {env.now:.2f}: Train departing with no containers")
        next_departure += departure_interval