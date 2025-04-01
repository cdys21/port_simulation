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
    while truck_queue:
        # Wait until at least 2 containers are available.
        if len(truck_queue) < 2:
            # If there's only one container, wait a bit for a second to arrive.
            yield env.timeout(0.1)
            continue

        # Request a gate (each gate processes one truck).
        with gate_resource.request() as req:
            yield req
            # Group two containers.
            containers = [truck_queue.pop(0) for _ in range(2)]
            # Sample processing time in minutes and convert to hours.
            processing_time_minutes = random.triangular(
                truck_processing_params['min'],
                truck_processing_params['max'],
                truck_processing_params['mode']
            )
            processing_time = processing_time_minutes / 60.0
            print(f"Time {env.now:.2f}: Truck departing with containers {[c.container_id for c in containers]}. Processing time: {processing_time:.2f} hours")
            yield env.timeout(processing_time)

def train_departure_process(env, train_queue, trains_per_day):
    """
    Process train departures.
    
    - train_queue: list of containers (with mode "Rail") waiting for train departure.
    - trains_per_day: number of trains scheduled per day.
    
    Process:
      - Calculate fixed departure interval based on a 24-hour day.
      - At each departure time, load all available train containers (simulate loading instantly for simplicity).
    """
    departure_interval = 24 / trains_per_day  # hours between departures
    next_departure = env.now  # first departure at current simulation time

    while True:
        # Wait until the next scheduled train departure.
        yield env.timeout(max(0, next_departure - env.now))
        # At departure time, retrieve all available train containers.
        if train_queue:
            departing_ids = [c.container_id for c in train_queue]
            print(f"Time {env.now:.2f}: Train departing with containers {departing_ids}")
            # Clear the train queue.
            train_queue.clear()
        else:
            print(f"Time {env.now:.2f}: Train departing with no containers")
        # Schedule the next departure.
        next_departure += departure_interval

        # To allow simulation to eventually finish in test, break if simulation time is very high.
        if env.now > 48:  # run for two days maximum in the test
            break

# Dummy container class for testing.
class DummyContainer:
    def __init__(self, container_id, mode):
        self.container_id = container_id
        self.mode = mode

    def __str__(self):
        return f"Container(id={self.container_id}, mode={self.mode})"

#if __name__ == '__main__':
#    # Set seed for reproducibility.
#    random.seed(42)
#
#    # Create a SimPy environment.
#    env = simpy.Environment()
#
#    # Configuration for truck departures from JSON.
#    truck_processing_params = {"min": 10, "mode": 13, "max": 30}  # in minutes
#    number_of_gates = 125
#    # Create a SimPy resource for gates.
#    gate_resource = simpy.Resource(env, capacity=number_of_gates)
#
#    # For testing, create dummy queues for truck and train containers.
#    # Let's assume 6 truck containers (mode "Road") and 5 train containers (mode "Rail").
#    truck_queue = [DummyContainer(i, "Road") for i in range(6)]
#    train_queue = [DummyContainer(i+100, "Rail") for i in range(5)]
#
#    # Start the truck departure process.
#    env.process(truck_departure_process(env, truck_queue, gate_resource, truck_processing_params))
#    # Start the train departure process with 4 trains per day (i.e. every 6 hours).
#    env.process(train_departure_process(env, train_queue, trains_per_day=4))
#
#    # For testing, let the simulation run for a set duration.
#    env.run(until=30)