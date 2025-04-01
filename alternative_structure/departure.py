# departure.py

import random
random.seed(42)
import simpy

def parse_operating_hours(operating_hours_dict):
    """
    Convert operating hours from a dictionary with string values (HH:MM) into numerical hours.
    
    Args:
        operating_hours_dict (dict): e.g., {"start": "06:00", "end": "17:00"}
    
    Returns:
        tuple: (start_hour, end_hour) as floats.
    """
    start_str = operating_hours_dict.get("start", "00:00")
    end_str = operating_hours_dict.get("end", "24:00")
    start_parts = start_str.split(":")
    end_parts = end_str.split(":")
    start_hour = float(start_parts[0]) + float(start_parts[1]) / 60.0
    end_hour = float(end_parts[0]) + float(end_parts[1]) / 60.0
    return start_hour, end_hour

def truck_departure_process(env, truck_queue, gate_resource, truck_processing_params, op_hours, metrics=None):
    """
    Continuously processes truck departures.
    
    - Checks that current simulation time is within operating hours.
    - Processes up to 2 containers at a time using a gate resource.
    - For each container, records:
        - "loaded_for_transport": when the container is loaded onto a truck.
        - "departed_port": when the container departs (after processing delay).
    """
    # Parse operating hours from config (e.g., {"start": "06:00", "end": "17:00"})
    start_hour, end_hour = parse_operating_hours(op_hours)

    while True:
        current_hour = env.now % 24
        if not (start_hour <= current_hour < end_hour):
            if current_hour < start_hour:
                wait_time = start_hour - current_hour
            else:
                wait_time = 24 - current_hour + start_hour
            yield env.timeout(wait_time)
            continue

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
            processing_time = processing_time_minutes / 60.0
            # Set loaded_for_transport for each container.
            for container in containers:
                container.checkpoints["loaded_for_transport"] = env.now
            yield env.timeout(processing_time)
            # After processing, set departed_port checkpoint.
            for container in containers:
                container.checkpoints["departed_port"] = env.now
                # Now record the container's final state.
                if metrics is not None:
                    metrics.record_container_departure(container)

def train_departure_process(env, train_queue, trains_per_day, train_capacity, metrics=None):
    """
    Continuously schedules train departures at fixed intervals and processes up to train_capacity containers per departure.
    
    For each container processed, records:
        - "loaded_for_transport": timestamp when container is loaded onto a train.
        - "departed_port": timestamp when container departs.
    """
    departure_interval = 24 / trains_per_day
    next_departure = env.now
    while True:
        yield env.timeout(max(0, next_departure - env.now))
        if train_queue:
            num_to_process = min(train_capacity, len(train_queue))
            departing_containers = [train_queue.pop(0) for _ in range(num_to_process)]
            for container in departing_containers:
                container.checkpoints["loaded_for_transport"] = env.now
            # For simplicity, assume departure is instantaneous.
            for container in departing_containers:
                container.checkpoints["departed_port"] = env.now
                if metrics is not None:
                    metrics.record_container_departure(container)
        next_departure += departure_interval
