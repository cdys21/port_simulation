# main.py

import random
random.seed(42)

import simpy
import statistics
import commentjson as json

def load_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)
    
from vessel import Vessel
from berth import BerthManager
from unloading import unload_vessel
from yard import Yard
from container import Container
from departure import truck_departure_process, train_departure_process
from metrics import Metrics

class Termination(Exception):
    pass

def main(progress_callback=None):
    random.seed(42)
    env = simpy.Environment()
    config = load_config("config_exp.jsonc")
    sim_config = config["simulation"]
    metrics = Metrics()
    
    # Setup Berth Manager.
    num_berths = sim_config["berths"]
    cranes_per_berth = sim_config["cranes_per_berth"]
    effective_crane_availability = sim_config["effective_crane_availability"]
    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
    
    # Setup Yards.
    container_categories = sim_config["yard"]["container_categories"]
    yard_mapping = sim_config["yard"]["yard_mapping"]
    retrieval_delay_per_move = sim_config["yard"]["retrieval_delay_per_move"]
    yards = {}
    for category in container_categories:
        mapping = yard_mapping.get(category, {})
        capacity = mapping.get("capacity", 10000)
        initial_containers = mapping.get("initial_containers", 0)
        yards[category] = Yard(env, capacity, retrieval_delay_per_move, initial_containers)
        # Initial containers already have their checkpoints set in Yard.
    total_initial = sum(yard.get_occupancy() for yard in yards.values())
    metrics.record_yard_utilization(0, "all", total_initial)
    metrics.total_initial = total_initial  # For later use in summarizing departures.
    
    # Assign departure mode for pre-existing containers.
    train_percentage = sim_config["train"]["percentage"]
    for category in container_categories:
        for container in yards[category].containers:
            container.mode = "Rail" if random.random() < train_percentage else "Road"
    
    # Setup Departure Queues and Gate Resource.
    truck_queue = []
    train_queue = []
    gate_resource = simpy.Resource(env, capacity=sim_config["gate"]["number_of_gates"])
    
    # Create Vessel Objects.
    arrival_variability = sim_config["arrival_variability"]
    vessels = []
    for vessel_data in config["vessels"]:
        vessel_obj = Vessel(
            name=vessel_data["name"],
            container_count=vessel_data["containers"],
            expected_arrival_day=vessel_data["expected_arrival_day"],
            expected_arrival=vessel_data["expected_arrival"],
            arrival_variability=arrival_variability
        )
        vessel_obj.adjust_arrival()  # Sets vessel.actual_arrival, corresponding to "vessel_arrives"
        vessels.append(vessel_obj)
        # Optionally, record vessel info in metrics if desired.
    
    container_id_counter = total_initial
    
    def vessel_process(env, vessel, berth_manager, yards):
        nonlocal container_id_counter
        # Wait until the vessel actually arrives.
        yield env.timeout(vessel.actual_arrival)
        
        # Request a berth.
        berth = yield berth_manager.request_berth()
        berth_alloc_time = env.now  # This is "vessel_berths"
        
        # Unload the vessel.
        unload_finish_times = yield env.process(unload_vessel(env, vessel, berth, sim_config["unload_params"]))
        vessel_unload_duration = max(unload_finish_times) - berth_alloc_time
        
        # Release the berth.
        yield berth_manager.release_berth(berth)
        
        # For each container unloaded, create a new container and set checkpoints.
        cs = sim_config["container_storage"]["triangular_distribution"]
        for i in range(vessel.container_count):
            storage_duration = random.triangular(cs["min"], cs["max"], cs["mode"])
            container_yard_arrival = unload_finish_times[i]  # This time becomes "entered_yard"
            new_container = Container(container_id=container_id_counter, is_initial=False)
            # Record vessel-related checkpoints.
            new_container.checkpoints["vessel"] = vessel.name
            new_container.checkpoints["vessel_scheduled_arrival"] = vessel.scheduled_arrival
            new_container.checkpoints["vessel_arrives"] = vessel.actual_arrival
            new_container.checkpoints["vessel_berths"] = berth_alloc_time
            # Record yard-related checkpoints.
            new_container.checkpoints["entered_yard"] = container_yard_arrival
            new_container.checkpoints["retrieval_ready"] = container_yard_arrival + storage_duration
            # Mode assignment.
            new_container.mode = "Rail" if random.random() < train_percentage else "Road"
            # Add the container to the appropriate yard.
            # Assuming container_categories[0] is used.
            new_container.category = container_categories[0]
            yards[new_container.category].add_container(new_container)
            container_id_counter += 1

        total_occ = sum(yard.get_occupancy() for yard in yards.values())
        metrics.record_yard_utilization(env.now, "all", total_occ)
    
    def yard_to_departure(env, yard, truck_queue, train_queue):
        while True:
            if yard.get_occupancy() == 0:
                yield env.timeout(1)
                continue
    
            # Retrieve all ready containers in one batch.
            ready_containers = yield env.process(yard.retrieve_ready_containers())
            if ready_containers:
                for container in ready_containers:
                    # At this point, the yard process has set the "waiting_for_inland_tsp" checkpoint.
                    if container.mode == "Rail":
                        train_queue.append(container)
                    else:
                        truck_queue.append(container)
            else:
                # No container is ready, wait a bit before checking again.
                yield env.timeout(0.1)

    def termination_process(env, yards, truck_queue, train_queue):
        while True:
            total_yard = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            if total_yard == 0 and tq == 0 and trq == 0 and env.now >= 24:
                raise Termination
            yield env.timeout(1)

    def progress_tracker(env, yards, truck_queue, train_queue):
        total_capacity = sum(yard.capacity for yard in yards.values())
        while True:
            total = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            metrics.record_yard_utilization(env.now, "all", total)
            metrics.record_truck_queue(env.now, tq)
            metrics.record_train_queue(env.now, trq)
            if progress_callback:
                progress_callback(total, total_capacity, tq, trq, env.now)
            yield env.timeout(1)
    
    # Start vessel processes.
    for vessel in vessels:
        env.process(vessel_process(env, vessel, berth_manager, yards))
    
    # Start yard-to-departure processes for each yard.
    for yard_instance in yards.values():
        env.process(yard_to_departure(env, yard_instance, truck_queue, train_queue))
    
    # Start departure processes.
    env.process(truck_departure_process(env, truck_queue, gate_resource, sim_config["gate"]["truck_processing_time"], sim_config["gate"]["operating_hours"], metrics))
    env.process(train_departure_process(env, train_queue, sim_config["trains_per_day"], sim_config["train"]["capacity"], metrics))
    
    # Start termination and progress tracking.
    env.process(termination_process(env, yards, truck_queue, train_queue))
    env.process(progress_tracker(env, yards, truck_queue, train_queue))
    
    try:
        env.run()
    except Termination:
        pass
    
    return metrics

if __name__ == '__main__':
    main()
