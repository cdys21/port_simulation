import random
import simpy
import yaml
from .models import Vessel, Yard
from .processes import vessel_arrival, train_departure_process, monitor, container_departure
from .metrics import create_dataframe

def run_simulation(config):
    env = simpy.Environment()
    # Create berth and gate resources using keys under "port"
    berths = simpy.Resource(env, capacity=config['port']['berth_count'])
    global gates
    gates = simpy.Resource(env, capacity=config['port']['gate_count'])
    
    # Initialize the yard as empty using yard_capacity from config
    yard = Yard(capacity=config['port']['yard_capacity'])
    
    metrics = {
        'yard_occupancy': [],
        'truck_queue': [],
        'rail_queue': [],
        'gate_status': []
    }
    all_containers = []  # List to store all processed containers

    # Start the monitoring process.
    env.process(monitor(env, yard, metrics))
    # Start the train departure process for Rail containers.
    env.process(train_departure_process(env, yard, gates, all_containers, config.get('processes', {})))
    
    # Process vessel arrivals.
    for vessel_data in config['vessels']:
        vessel = Vessel(
            env,
            vessel_data['name'],
            vessel_data['container_count'],
            vessel_data['day'],
            vessel_data['hour'],
            config.get('processes', {}).get('vessel_arrival', {}),
            config.get('container', {}).get('rail_adoption', 0.15)
        )
        env.process(vessel_arrival(env, vessel, berths, yard, all_containers, config.get('processes', {}), gates))
    
    # Run the simulation until the configured duration.
    duration = config['simulation']['duration']  # now using simulation.duration key
    env.run(until=duration)
    
    df = create_dataframe(all_containers)
    print("\nSIMULATION SUMMARY:")
    print(f"Number of containers processed: {len(all_containers)}")
    if all_containers:
        road_containers = sum(1 for c in all_containers if c.mode == "Road")
        rail_containers = sum(1 for c in all_containers if c.mode == "Rail")
        print(f"Containers by mode: Road {road_containers}, Rail {rail_containers}")
        departed_containers = [c for c in all_containers if c.departed_port is not None and c.entered_yard is not None]
        if departed_containers:
            dwell_times = [c.departed_port - c.entered_yard for c in departed_containers]
            avg_dwell = sum(dwell_times) / len(dwell_times)
            print(f"Average dwell time: {avg_dwell:.2f} hours")
    remaining = len(yard.containers)
    print(f"Containers remaining in yard: {remaining}")
    
    return df, metrics

def load_config(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == '__main__':
    config = load_config()
    run_simulation(config)
