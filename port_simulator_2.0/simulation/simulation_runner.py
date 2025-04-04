# simulation/simulation_runner.py
import random
import simpy
import yaml
from .models import Vessel, Yard
from .processes import vessel_arrival, train_departure_process, monitor, container_departure
from .metrics import create_dataframe

def initial_container_departure(env, container, yard, gate_resource, all_containers, processes_config):
    """
    Process for initial containers (vessel=="Initial") in Road mode.
    This process is separate from vessel_container departure to allow for custom debug printing
    and potential custom logic.
    """
    #print(f"[DEBUG] Starting initial container departure process for container (mode: {container.mode}) at time {env.now:.2f}")
    # Optionally wait a small delay before triggering departure
    yield env.timeout(0.5)
    #print(f"[DEBUG] Triggering departure process for initial container at time {env.now:.2f}")
    # Call the standard container departure process (this function is a generator)
    yield from container_departure(env, container, yard, gate_resource, all_containers, processes_config)
    #print(f"[DEBUG] Initial container departure process completed at time {env.now:.2f}")

def initial_departure_trigger(env, yard, gate_resource, all_containers, processes_config, check_interval=1):
    """
    Periodically check for initial containers (vessel == "Initial") that haven't departed
    and re-schedule their departure process if they are Road mode.
    """
    while True:
        yield env.timeout(check_interval)
        print(f"[DEBUG] initial_departure_trigger checking at time {env.now:.2f}")
        # Iterate over a copy of the container list to avoid modification issues.
        for container in list(yard.containers):
            if container.vessel == "Initial" and container.departed_port is None:
                #print(f"[DEBUG] Found initial container (mode: {container.mode}) still in yard at time {env.now:.2f}")
                if container.mode == "Road":
                    # Re-schedule departure process for Road containers
                    #print(f"[DEBUG] Rescheduling departure for initial container (Road) at time {env.now:.2f}")
                    env.process(initial_container_departure(env, container, yard, gate_resource, all_containers, processes_config))
                else:
                    # For Rail containers, we rely on train_departure_process.
                    #print(f"[DEBUG] Rail container remains for train departure at time {env.now:.2f}")
                    pass

def run_simulation(config):
    # Set random seed for reproducibility
    seed = config.get('simulation', {}).get('seed', 42)
    random.seed(seed)

    env = simpy.Environment()
    port_config = config.get('port', {})
    berth_count = port_config.get('berth_count', 4)
    gate_count = port_config.get('gate_count', 120)
    yard_capacity = port_config.get('yard_capacity', 50000)
    initial_yard_fill = port_config.get('initial_yard_fill', 0.7)
    initial_count = int(yard_capacity * initial_yard_fill)

    # Process configuration
    processes_config = config.get('processes', {})

    # Container configuration
    rail_adoption = config.get('container', {}).get('rail_adoption', 0.15)

    # Initialize resources and yard
    berths = simpy.Resource(env, capacity=berth_count)
    gate_resource = simpy.Resource(env, capacity=gate_count)
    yard = Yard(yard_capacity, initial_count, rail_adoption)
    print(f"[DEBUG] Created yard with {len(yard.containers)} initial containers.")

    # Metrics dictionary
    metrics = {
        'yard_occupancy': [],
        'truck_queue': [],
        'rail_queue': [],
        'gate_status': []
    }
    all_containers = []  # List to store finished container objects

    # Start monitoring process
    env.process(monitor(env, yard, metrics))
    # Start train departure process for rail containers
    env.process(train_departure_process(env, yard, gate_resource, all_containers, processes_config))

    # --- Process initial containers already in the yard ---
    # Read waiting time configuration for initial containers from config
    initial_container_config = config.get('initial_container', {})
    waiting_time_config = initial_container_config.get('waiting_time', {})
    wt_min = waiting_time_config.get('min', 0)
    wt_max = waiting_time_config.get('max', 0)
    wt_mode = waiting_time_config.get('mode', 5)

    # For each initial container, set waiting time using the triangular distribution.
    for container in yard.containers[:]:  # iterate over a copy of the list
        container.waiting_for_inland_tsp = random.triangular(wt_min, wt_max, wt_mode)
        #print(f"[DEBUG] Set waiting time {container.waiting_for_inland_tsp:.2f} for initial container (mode: {container.mode}) at time {env.now:.2f}")
        # For Road containers, schedule a dedicated initial departure process.
        if container.mode == "Road":
            env.process(initial_container_departure(env, container, yard, gate_resource, all_containers, processes_config))
    # --------------------------------------------------------------------

    # Add a periodic trigger to re-check initial container departures
    env.process(initial_departure_trigger(env, yard, gate_resource, all_containers, processes_config, check_interval=1))

    # Process vessel arrivals
    arrival_params = processes_config.get('vessel_arrival', {})
    vessels_config = config.get('vessels', [])
    for vessel_info in vessels_config:
        vessel = Vessel(
            env,
            vessel_info['name'],
            vessel_info['container_count'],
            vessel_info['day'],
            vessel_info['hour'],
            arrival_params,
            rail_adoption
        )
        #print(f"[DEBUG] Scheduling arrival for vessel {vessel.name} at time {vessel.actual_arrival:.2f}")
        env.process(vessel_arrival(env, vessel, berths, yard, all_containers, processes_config, gate_resource))

    # Run the simulation
    duration = config.get('simulation', {}).get('duration', 150)
    #print(f"[DEBUG] Running simulation until time {duration}")
    env.run(until=duration)

    df = create_dataframe(all_containers)
    #print("\nSIMULATION SUMMARY:")
    #print(f"Number of containers processed: {len(all_containers)}")
    road_containers = sum(1 for c in all_containers if c.mode == "Road")
    rail_containers = sum(1 for c in all_containers if c.mode == "Rail")
    #print(f"Containers by mode: Road {road_containers}, Rail {rail_containers}")

    return df, metrics

def load_config(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == '__main__':
    config = load_config()
    run_simulation(config)
