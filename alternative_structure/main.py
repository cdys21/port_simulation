import json
import random
import simpy

# Helper to load configuration from config.json.
def load_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Import our modules.
from vessel import Vessel
from berth import BerthManager
from unloading import unload_vessel
from yard import Yard, Container
from departure import truck_departure_process, train_departure_process

def main():
    # Set random seed for reproducibility.
    random.seed(42)
    
    # Create the simulation environment.
    env = simpy.Environment()
    
    # Load configuration from config.json.
    config = load_config("/Users/yassineklahlou/Documents/GitHub/port_simulation/alternative_structure/config_nynj.json")
    sim_config = config["simulation"]
    
    # --------------------------
    # Setup Berth Manager.
    # --------------------------
    num_berths = sim_config["berths"]
    cranes_per_berth = sim_config["cranes_per_berth"]
    effective_crane_availability = sim_config["effective_crane_availability"]
    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
    
    # --------------------------
    # Setup Yards for Each Container Category.
    # --------------------------
    container_categories = sim_config["yard"]["container_categories"]
    yard_mapping = sim_config["yard"]["yard_mapping"]
    max_stack_height = sim_config["yard"]["max_stack_height"]
    retrieval_delay_per_move = sim_config["yard"]["retrieval_delay_per_move"]
    
    # Create a yard instance for each category.
    yards = {}
    for category in container_categories:
        mapping = yard_mapping.get(category, {})
        capacity = mapping.get("capacity", 40)
        initial_containers = mapping.get("initial_containers", 0)
        yards[category] = Yard(env, capacity, max_stack_height, retrieval_delay_per_move, initial_containers)
        print(f"Yard for category '{category}' created with capacity {capacity} and {initial_containers} pre-existing containers.")
    
    # --------------------------
    # Assign departure mode for pre-existing containers.
    # --------------------------
    rail_probability = sim_config["rail_probability"]
    for category in container_categories:
        for container in yards[category].containers:
            container.mode = "Rail" if random.random() < rail_probability else "Road"
    
    # --------------------------
    # Setup Departure Queues and Gate Resource.
    # --------------------------
    truck_queue = []
    train_queue = []
    gate_resource = simpy.Resource(env, capacity=sim_config["gate"]["number_of_gates"])
    
    # --------------------------
    # Create Vessel Objects.
    # --------------------------
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
        print(f"Vessel {vessel_obj.name} scheduled to arrive at {vessel_obj.actual_arrival:.2f} hours.")
    
    # Global container ID counter starts at total pre-existing containers across all yards.
    container_id_counter = sum(mapping.get("initial_containers", 0) for mapping in yard_mapping.values())
    
    # --------------------------
    # Define Processes.
    # --------------------------
    unload_params = sim_config["unload_params"]
    
    def vessel_process(env, vessel, berth_manager, yards):
        nonlocal container_id_counter
        # Wait until vessel's actual arrival.
        yield env.timeout(vessel.actual_arrival)
        print(f"Time {env.now:.2f}: Vessel {vessel.name} arrives with {vessel.container_count} containers.")
        
        # Request a berth.
        berth = yield berth_manager.request_berth()
        print(f"Time {env.now:.2f}: Vessel {vessel.name} allocated {berth}.")
        
        # Unload the vessel.
        unload_duration = yield env.process(unload_vessel(env, vessel, berth, unload_params))
        print(f"Time {env.now:.2f}: Vessel {vessel.name} unloaded in {unload_duration:.2f} hours.")
        
        # Release the berth.
        yield berth_manager.release_berth(berth)
        
        # For each container on the vessel, create a yard container.
        storage_mean = sim_config["container_storage"]["normal_distribution"]["mean"]
        storage_stdev = sim_config["container_storage"]["normal_distribution"]["stdev"]
        for i in range(vessel.container_count):
            storage_duration = max(0, random.normalvariate(storage_mean, storage_stdev))
            new_container = Container(
                container_id=container_id_counter,
                arrival_time=env.now,
                storage_duration=storage_duration,
                is_initial=False
            )
            # Assign container category explicitly from config (e.g. "TEU").
            new_container.category = container_categories[0]
            # Assign departure mode based on rail_probability.
            new_container.mode = "Rail" if random.random() < rail_probability else "Road"
            # Add the container to its corresponding yard.
            yards[new_container.category].add_container(new_container)
            container_id_counter += 1
        total_occupancy = sum(yard.get_occupancy() for yard in yards.values())
        print(f"Time {env.now:.2f}: Total yard occupancy is now {total_occupancy}.")
    
    def yard_to_departure(env, yard, truck_queue, train_queue):
        """
        Process for a single yard: retrieves ready containers and sends them to the correct departure queue.
        """
        while True:
            if yard.get_occupancy() == 0:
                yield env.timeout(1)
                continue
            container = yield env.process(yard.retrieve_ready_container())
            if container is not None:
                if container.mode == "Rail":
                    train_queue.append(container)
                    print(f"Time {env.now:.2f}: Container {container.container_id} (Cat: {container.category}) sent to Train queue.")
                else:
                    truck_queue.append(container)
                    print(f"Time {env.now:.2f}: Container {container.container_id} (Cat: {container.category}) sent to Truck queue.")
            else:
                break
    
    def termination_process(env, yards, truck_queue, train_queue):
        """
        Terminates the simulation when all yards are empty and both departure queues are empty.
        """
        while True:
            total_yard = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            print(f"Termination check at time {env.now:.2f}: yards={total_yard}, truck_queue={tq}, train_queue={trq}")
            if total_yard == 0 and tq == 0 and trq == 0:
                print(f"Time {env.now:.2f}: All containers have left port. Terminating simulation.")
                env.exit()
            yield env.timeout(1)
    
    def progress_tracker(env, yards, truck_queue, train_queue):
        """
        Periodically prints total containers in all yards and sizes of departure queues.
        """
        while True:
            total = sum(yard.get_occupancy() for yard in yards.values())
            tq = len(truck_queue)
            trq = len(train_queue)
            print(f"Time {env.now:.2f}: Total containers in yards: {total}, truck_queue: {tq}, train_queue: {trq}")
            yield env.timeout(1)
    
    # --------------------------
    # Schedule Processes.
    # --------------------------
    for vessel in vessels:
        env.process(vessel_process(env, vessel, berth_manager, yards))
    for yard_instance in yards.values():
        env.process(yard_to_departure(env, yard_instance, truck_queue, train_queue))
    env.process(truck_departure_process(env, truck_queue, gate_resource, sim_config["gate"]["truck_processing_time"]))
    env.process(train_departure_process(env, train_queue, sim_config["trains_per_day"]))
    env.process(termination_process(env, yards, truck_queue, train_queue))
    env.process(progress_tracker(env, yards, truck_queue, train_queue))
    
    # --------------------------
    # Run the Simulation.
    # --------------------------
    # Simulation runs until termination_process calls env.exit().
    env.run()
    
if __name__ == '__main__':
    main()