# simulation/simulation_runner.py
import random
import simpy
import yaml
from .models import Vessel, Yard
from .processes import vessel_arrival, train_departure_process, monitor
from .metrics import create_dataframe

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
        env.process(vessel_arrival(env, vessel, berths, yard, all_containers, processes_config, gate_resource))

    # Run the simulation
    duration = config.get('simulation', {}).get('duration', 150)
    env.run(until=duration)

    df = create_dataframe(all_containers)
    print("\nSIMULATION SUMMARY:")
    print(f"Number of containers processed: {len(all_containers)}")
    road_containers = sum(1 for c in all_containers if c.mode == "Road")
    rail_containers = sum(1 for c in all_containers if c.mode == "Rail")
    print(f"Containers by mode: Road {road_containers}, Rail {rail_containers}")

    return df, metrics

def load_config(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == '__main__':
    config = load_config()
    run_simulation(config)
