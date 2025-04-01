# main.py

import random
random.seed(42)

import simpy
import sys
import statistics

import commentjson as json  # Use commentjson instead of the standard json module

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
    config = load_config("/Users/yassineklahlou/Documents/GitHub/port_simulation/alternative_structure/config.jsonc")
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
    max_stack_height = sim_config["yard"]["max_stack_height"]
    retrieval_delay_per_move = sim_config["yard"]["retrieval_delay_per_move"]
    yards = {}
    for category in container_categories:
        mapping = yard_mapping.get(category, {})
        capacity = mapping.get("capacity", 40)
        initial_containers = mapping.get("initial_containers", 0)
        yards[category] = Yard(env, capacity, max_stack_height, retrieval_delay_per_move, initial_containers)
        #print(f"Yard for category '{category}' created with capacity {capacity} and {initial_containers} pre-existing containers.")
    total_initial = sum(yard.get_occupancy() for yard in yards.values())
    metrics.record_yard_occupancy(0, total_initial)
    metrics.total_initial = total_initial  # then access via metrics.total_initial in streamlit
    
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
        vessel_obj.adjust_arrival()
        vessels.append(vessel_obj)
        #print(f"Vessel {vessel_obj.name} scheduled to arrive at {vessel_obj.actual_arrival:.2f} hours.")
        metrics.record_vessel_arrival(vessel_obj.name, vessel_obj.scheduled_arrival, vessel_obj.actual_arrival)
        ship_wait = vessel_obj.actual_arrival - vessel_obj.scheduled_arrival
        for _ in range(vessel_obj.container_count):
            metrics.record_ship_waiting(ship_wait)
    
    container_id_counter = sum(mapping.get("initial_containers", 0) for mapping in yard_mapping.values())
    
    def vessel_process(env, vessel, berth_manager, yards):
        nonlocal container_id_counter
        yield env.timeout(vessel.actual_arrival)
        #print(f"Time {env.now:.2f}: Vessel {vessel.name} arrives with {vessel.container_count} containers.")
        berth = yield berth_manager.request_berth()
        berth_alloc_time = env.now
        #print(f"Time {env.now:.2f}: Vessel {vessel.name} allocated {berth}.")
        unload_finish_times = yield env.process(unload_vessel(env, vessel, berth, sim_config["unload_params"]))
        # Vessel unloading duration is the difference between the last container finish and berth_alloc_time.
        vessel_unload_duration = max(unload_finish_times) - berth_alloc_time
        #print(f"Time {env.now:.2f}: Vessel {vessel.name} unloaded in {vessel_unload_duration:.2f} hours.")
        metrics.record_unloading_duration(vessel.name, vessel_unload_duration)
        yield berth_manager.release_berth(berth)
        
        # Read triangular parameters from the config.
        cs = sim_config["container_storage"]["triangular_distribution"]
        # Assume unload_vessel now returns a list of unload finish times for each container.
        for i in range(vessel.container_count):
            storage_duration = random.triangular(cs["min"], cs["max"], cs["mode"])
            container_yard_arrival = unload_finish_times[i]  # Each container's yard arrival time.
            new_container = Container(
                container_id=container_id_counter,
                storage_duration=storage_duration,
                is_initial=False
            )
            new_container.arrival_time = container_yard_arrival  # Set the actual yard arrival time.
            # Set checkpoints for the container.
            new_container.checkpoints["unload_finish"] = container_yard_arrival
            new_container.checkpoints["berth_allocation"] = berth_alloc_time
            new_container.checkpoints["vessel_expected_arrival"] = vessel.scheduled_arrival
            new_container.category = container_categories[0]
            new_container.mode = "Rail" if random.random() < train_percentage else "Road"
            yards[new_container.category].add_container(new_container)
            container_id_counter += 1



        total_occ = sum(yard.get_occupancy() for yard in yards.values())
        #print(f"Time {env.now:.2f}: Total yard occupancy is now {total_occ}.")
        metrics.record_yard_occupancy(env.now, total_occ)
    
    def yard_to_departure(env, yard, truck_queue, train_queue):
        while True:
            if yard.get_occupancy() == 0:
                yield env.timeout(1)
                continue
            container = yield env.process(yard.retrieve_ready_container())
            if container is not None:
            # Process only non-initial containers for duration metrics.
                if not container.is_initial:
                    yard_storage = env.now - container.arrival_time
                    metrics.record_yard_storage(yard_storage)
                    stacking_retrieval = (max_stack_height - 1 - container.stacking_level) * retrieval_delay_per_move
                    metrics.record_stacking_retrieval(stacking_retrieval)
                    # Compute dwell time only if the checkpoint exists.
                    if "vessel_expected_arrival" in container.checkpoints:
                        dwell_time = env.now - container.checkpoints["vessel_expected_arrival"]
                    else:
                        dwell_time = None
                    metrics.record_container_departure(container.container_id, container.mode, env.now, dwell_time)
                # In either case, assign retrieval time and queue the container.
                container.retrieval_time = env.now
                if container.mode == "Rail":
                    train_queue.append(container)
                else:
                    truck_queue.append(container)
            else:
                break
    
    def termination_process(env, yards, truck_queue, train_queue):
        while True:
            total_yard = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            #print(f"Termination check at time {env.now:.2f}: yards={total_yard}, truck_queue={tq}, train_queue={trq}")
            if total_yard == 0 and tq == 0 and trq == 0:
                #print(f"Time {env.now:.2f}: All containers have left port. Terminating simulation.")
                raise Termination
            yield env.timeout(1)
    
    def progress_tracker(env, yards, truck_queue, train_queue):
        bar_length = 50
        total_capacity = sum(yard.capacity for yard in yards.values())
        while True:
            total = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            filled_length = int(round(bar_length * (total / total_capacity)))
            bar = "[" + "#" * filled_length + "-" * (bar_length - filled_length) + "]"
            #print(f"Time {env.now:.2f}: Yard {bar} {total}/{total_capacity} containers, truck_queue: {tq}, train_queue: {trq}")
            metrics.record_yard_occupancy(env.now, total)
            metrics.record_truck_queue(env.now, tq)
            metrics.record_train_queue(env.now, trq)
            if progress_callback:
                progress_callback(total, total_capacity, tq, trq, env.now)
            yield env.timeout(1)
    
    for vessel in vessels:
        env.process(vessel_process(env, vessel, berth_manager, yards))
    for yard_instance in yards.values():
        env.process(yard_to_departure(env, yard_instance, truck_queue, train_queue))
    env.process(truck_departure_process(env, truck_queue, gate_resource, sim_config["gate"]["truck_processing_time"], metrics))
    env.process(train_departure_process(env, train_queue, sim_config["trains_per_day"], sim_config["train"]["capacity"], metrics))
    env.process(termination_process(env, yards, truck_queue, train_queue))
    env.process(progress_tracker(env, yards, truck_queue, train_queue))
    
    try:
        env.run()
    except Termination:
        #print("Simulation terminated successfully.")
        pass
    
    return metrics

if __name__ == '__main__':
    main()