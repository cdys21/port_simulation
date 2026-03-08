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
    
    # Setup Berth Manager
    num_berths = sim_config["berths"]
    cranes_per_berth = sim_config["cranes_per_berth"]
    effective_crane_availability = sim_config["effective_crane_availability"]
    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
    
    # Setup Yards
    container_categories = sim_config["yard"]["container_categories"]
    yard_mapping = sim_config["yard"]["yard_mapping"]
    retrieval_delay_per_move = sim_config["yard"]["retrieval_delay_per_move"]
    yards = {}
    for category in container_categories:
        mapping = yard_mapping.get(category, {})
        capacity = mapping.get("capacity", 10000)
        initial_containers = mapping.get("initial_containers", 0)
        yards[category] = Yard(env, capacity, retrieval_delay_per_move, initial_containers)
        # Initial containers already have their checkpoints set in Yard
    total_initial = sum(yard.get_occupancy() for yard in yards.values())
    metrics.record_yard_utilization(0, "all", total_initial)
    metrics.total_initial = total_initial  # For later use in summarizing departures
    
    # Assign departure mode for pre-existing containers
    train_percentage = sim_config["train"]["percentage"]
    for category in container_categories:
        for container in yards[category].containers:
            container.mode = "Rail" if random.random() < train_percentage else "Road"
    
    # Setup Departure Queues and Gate Resource
    truck_queue = []
    train_queue = []
    gate_resource = simpy.Resource(env, capacity=sim_config["gate"]["number_of_gates"])
    
    # Create Vessel Objects
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
    
    container_id_counter = total_initial
    
    def vessel_process(env, vessel, berth_manager, yards, container_id_counter, train_percentage, sim_config, container_categories):
        # Wait until the vessel actually arrives
        yield env.timeout(vessel.actual_arrival)
        
        # Request a berth
        berth = yield berth_manager.request_berth()
        berth_alloc_time = env.now  # This is "vessel_berths"
        
        # Unload the vessel, adding containers to the yard as they are unloaded
        yield env.process(unload_vessel(
            env, vessel, berth, sim_config["unload_params"],
            yards[container_categories[0]], container_id_counter, train_percentage, sim_config, container_categories
        ))
        
        # Release the berth
        yield berth_manager.release_berth(berth)
        
        # Update container_id_counter for the next vessel
        container_id_counter += vessel.container_count
        
        # Record yard utilization
        total_occ = sum(yard.get_occupancy() for yard in yards.values())
        metrics.record_yard_utilization(env.now, "all", total_occ)
    
    def yard_to_departure(env, yard, truck_queue, train_queue):
        while True:
            if yard.containers:
                next_ready_time = min(c.checkpoints["retrieval_ready"] for c in yard.containers if "retrieval_ready" in c.checkpoints)
                wait_time = max(0, next_ready_time - env.now)
                yield env.timeout(wait_time)
                ready_containers = [c for c in yard.containers if "retrieval_ready" in c.checkpoints and env.now >= c.checkpoints["retrieval_ready"]]
                for c in ready_containers:
                    yard.containers.remove(c)
                    c.checkpoints["waiting_for_inland_tsp"] = env.now
                    if c.mode == "Rail":
                        train_queue.append(c)
                    else:
                        truck_queue.append(c)
            else:
                yield env.timeout(1)
    
    def termination_process(env, yards, truck_queue, train_queue, vessel_processes):
        yield simpy.events.AllOf(env, vessel_processes)
        while True:
            total_yard = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            if total_yard == 0 and tq == 0 and trq == 0:
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
    
    # Start vessel processes
    vessel_processes = []
    for vessel in vessels:
        proc = env.process(vessel_process(
            env, vessel, berth_manager, yards, container_id_counter,
            train_percentage, sim_config, container_categories
        ))
        vessel_processes.append(proc)
        container_id_counter += vessel.container_count  # Increment for the next vessel
    
    # Start yard-to-departure processes for each yard
    for yard_instance in yards.values():
        env.process(yard_to_departure(env, yard_instance, truck_queue, train_queue))
    
    # Start departure processes
    env.process(truck_departure_process(env, truck_queue, gate_resource, sim_config["gate"]["truck_processing_time"], sim_config["gate"]["operating_hours"], metrics))
    env.process(train_departure_process(env, train_queue, sim_config["trains_per_day"], sim_config["train"]["capacity"], metrics))
    
    # Start termination and progress tracking
    env.process(termination_process(env, yards, truck_queue, train_queue, vessel_processes))
    env.process(progress_tracker(env, yards, truck_queue, train_queue))
    
    try:
        env.run()
    except Termination:
        pass
    
    return metrics

if __name__ == '__main__':
    main()