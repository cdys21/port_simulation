import json
import streamlit as st
import plotly.express as px
import random
random.seed(42)

import simpy

# Import our modules.
from vessel import Vessel
from berth import BerthManager
from unloading import unload_vessel
from yard import Yard, Container
from departure import truck_departure_process, train_departure_process

def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def run_simulation(sim_duration=50):
    """
    Run the port logistics simulation for sim_duration hours.
    Returns a dictionary of collected metrics.
    """
    # Initialize metrics dictionary.
    metrics = {
        "vessel_arrivals": [],       # List of tuples: (vessel name, actual arrival time)
        "unloading_durations": [],   # List of tuples: (vessel name, unloading duration)
        "yard_occupancy": [],        # List of tuples: (simulation time, yard occupancy)
        "truck_departures": [],      # List of tuples: (time, container_id)
        "train_departures": []       # List of tuples: (time, container_id)
    }
    
    # Create the simulation environment.
    env = simpy.Environment()
    
    # Load the simulation configuration from the JSON file.
    config = load_config("/Users/yassineklahlou/Documents/GitHub/port_simulation/alternative_structure/config.json")
    simulation_config = config["simulation"]
    
    # --------------------------
    # Setup Berth Manager.
    # --------------------------
    num_berths = simulation_config["berths"]
    cranes_per_berth = simulation_config["cranes_per_berth"]
    effective_crane_availability = simulation_config["effective_crane_availability"]
    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
    
    # --------------------------
    # Setup Yard.
    # --------------------------
    # Get yard configuration for category "ANY".
    yard_config = simulation_config["yard"]["yard_mapping"]["ANY"]
    yard_capacity = yard_config["capacity"]
    initial_container_count = yard_config.get("initial_containers", 0)
    max_stack_height = simulation_config["yard"]["max_stack_height"]
    retrieval_delay_per_move = 0.1  # in hours
    
    yard = Yard(env, yard_capacity, max_stack_height, retrieval_delay_per_move, initial_container_count)
    metrics["yard_occupancy"].append((env.now, yard.get_occupancy()))
    
    # --------------------------
    # Setup Departure Queues and Gate Resource.
    # --------------------------
    truck_queue = []
    train_queue = []
    gate_resource = simpy.Resource(env, capacity=simulation_config["gate"]["number_of_gates"])
    
    # --------------------------
    # Create Vessel Objects.
    # --------------------------
    arrival_variability = simulation_config["arrival_variability"]
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
        metrics["vessel_arrivals"].append((vessel_obj.name, vessel_obj.actual_arrival))
    
    # Global counter for container IDs.
    container_id_counter = initial_container_count
    
    # --------------------------
    # Define Processes.
    # --------------------------
    def vessel_process(env, vessel, berth_manager, yard):
        nonlocal container_id_counter
        # Wait until vessel actual arrival time.
        yield env.timeout(vessel.actual_arrival)
        st.write(f"Time {env.now:.2f}: Vessel {vessel.name} arrived with {vessel.container_count} containers.")
        
        # Request a berth.
        berth = yield berth_manager.request_berth()
        st.write(f"Time {env.now:.2f}: Vessel {vessel.name} allocated {berth}.")
        
        # Unload the vessel.
        unload_params = {"min": 0.03, "mode": 0.04, "max": 0.06}
        unload_duration = yield env.process(unload_vessel(env, vessel, berth, unload_params))
        metrics["unloading_durations"].append((vessel.name, unload_duration))
        st.write(f"Time {env.now:.2f}: Vessel {vessel.name} unloaded in {unload_duration:.2f} hours.")
        
        # Release the berth.
        yield berth_manager.release_berth(berth)
        
        # Create yard containers for each container on the vessel.
        storage_mean = simulation_config["container_storage"]["normal_distribution"]["mean"]
        storage_stdev = simulation_config["container_storage"]["normal_distribution"]["stdev"]
        for i in range(vessel.container_count):
            storage_duration = max(0, random.normalvariate(storage_mean, storage_stdev))
            new_container = Container(
                container_id=container_id_counter,
                arrival_time=env.now,
                storage_duration=storage_duration,
                is_initial=False
            )
            # Randomly assign departure mode.
            new_container.mode = random.choice(["Road", "Rail"])
            yard.add_container(new_container)
            container_id_counter += 1
            # Record yard occupancy update.
            metrics["yard_occupancy"].append((env.now, yard.get_occupancy()))
    
    def yard_to_departure(env, yard, truck_queue, train_queue):
        while True:
            if yard.get_occupancy() == 0:
                yield env.timeout(1)
                continue
            container = yield env.process(yard.retrieve_ready_container())
            if container is not None:
                mode = getattr(container, "mode", "Road")
                if mode == "Rail":
                    train_queue.append(container)
                    metrics["train_departures"].append((env.now, container.container_id))
                    st.write(f"Time {env.now:.2f}: Container {container.container_id} sent to Train queue.")
                else:
                    truck_queue.append(container)
                    metrics["truck_departures"].append((env.now, container.container_id))
                    st.write(f"Time {env.now:.2f}: Container {container.container_id} sent to Truck queue.")
            else:
                break
    
    # --------------------------
    # Schedule Processes.
    # --------------------------
    for vessel in vessels:
        env.process(vessel_process(env, vessel, berth_manager, yard))
    env.process(yard_to_departure(env, yard, truck_queue, train_queue))
    env.process(truck_departure_process(env, truck_queue, gate_resource, simulation_config["gate"]["truck_processing_time"]))
    env.process(train_departure_process(env, train_queue, simulation_config["trains_per_day"]))
    
    # Run simulation for the specified duration.
    env.run(until=sim_duration)
    
    return metrics

# --------------------------
# Streamlit UI.
# --------------------------
st.title("Port Logistics Simulation")

# Sidebar inputs.
sim_duration = st.sidebar.number_input("Simulation Duration (hours)", min_value=1, max_value=200, value=50, step=1)

if st.sidebar.button("Run Simulation"):
    with st.spinner("Running simulation..."):
        metrics = run_simulation(sim_duration)
        st.success("Simulation completed!")
        
        # Display metrics.
        st.subheader("Vessel Arrivals (Vessel Name, Actual Arrival Time)")
        st.write(metrics["vessel_arrivals"])
        
        st.subheader("Unloading Durations (Vessel Name, Duration)")
        st.write(metrics["unloading_durations"])
        
        st.subheader("Yard Occupancy Over Time")
        times = [t for t, occ in metrics["yard_occupancy"]]
        occupancies = [occ for t, occ in metrics["yard_occupancy"]]
        fig_occ = px.line(x=times, y=occupancies, labels={'x': 'Time (hours)', 'y': 'Occupancy'})
        st.plotly_chart(fig_occ)
        
        st.subheader("Truck Departures (Time, Container ID)")
        st.write(metrics["truck_departures"])
        
        st.subheader("Train Departures (Time, Container ID)")
        st.write(metrics["train_departures"])