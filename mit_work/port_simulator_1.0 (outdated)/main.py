# main.py
import streamlit as st
import simpy
import pandas as pd
from datetime import datetime, timedelta
import random
import numpy as np

# Set a fixed seed for reproducibility
random.seed(42)
np.random.seed(42)


from config import (DEFAULT_SHIPS_SCHEDULE, ARRIVAL_TIME_VARIABILITY, MAX_BERTHS_DEFAULT,
                    CRANES_PER_BERTH_DEFAULT, CONTAINER_UNLOAD_TIME_DEFAULT, BERTH_TRANSITION_TIME_DEFAULT,
                    CONTAINER_TYPES_DEFAULT, MODAL_SPLIT_DEFAULT, GATE_HOURS_DEFAULT, TRAIN_SCHEDULE_DEFAULT,
                    MAX_STACKING_HEIGHT_DEFAULT, STACKING_RETRIEVAL_BASE_TIME_DEFAULT, STACKING_RETRIEVAL_FACTOR_DEFAULT,
                    SIMULATION_START_DEFAULT)
from models import ShipSchedule
from simulation import PortSimulation
import ui

def main():
    st.set_page_config(page_title="Port Simulation", layout="wide")
    st.title("Port Simulation Dashboard")

    st.sidebar.header("Settings ⚙️")
    # Configure ship schedule and other simulation parameters.
    if 'ship_schedule' not in st.session_state:
        ship_sched = ShipSchedule()
        for ship in DEFAULT_SHIPS_SCHEDULE:
            ship_sched.add_ship(ship["name"], ship["containers"], ship["expected_arrival"])
        st.session_state.ship_schedule = ship_sched
    
    schedule_df = st.session_state.ship_schedule.get_dataframe()
    if not schedule_df.empty:
        display_df = schedule_df.copy()
        display_df["expected_arrival"] = display_df["expected_arrival"] / 60
        edited_df = st.sidebar.data_editor(
            display_df,
            column_config={
                "name": "Ship Name",
                "containers": "Container Count",
                "expected_arrival": st.column_config.NumberColumn("Expected Arrival", min_value=0, format="%d")
            },
            num_rows="dynamic",
            key="ship_schedule_editor"
        )
        if edited_df is not None and not edited_df.equals(display_df):
            st.session_state.ship_schedule.clear()
            for _, row in edited_df.iterrows():
                st.session_state.ship_schedule.add_ship(row["name"], row["containers"], row["expected_arrival"])
    
    st.sidebar.markdown("### Arrival Time Variability")
    arrival_std = st.sidebar.number_input("Standard Deviation (hours)", min_value=0.0,
                                            value=float(ARRIVAL_TIME_VARIABILITY["std"]), step=0.5,
                                            help="Controls how much ships deviate from schedule. Higher values create more variability, with delays being more common than early arrivals.")
    
    use_start_date = st.sidebar.checkbox("Use Start Date", value=True)
    if use_start_date:
        sim_start_date = st.sidebar.date_input("Simulation Start Date", datetime(2025, 1, 1).date())
        sim_start_time = st.sidebar.time_input("Simulation Start Time", datetime(2025, 1, 1, 6, 0).time())
        combined_datetime = datetime.combine(sim_start_date, sim_start_time)
        simulation_start = combined_datetime
    else:
        simulation_start = None
    
    st.sidebar.markdown("### Container Stacking")
    max_stacking_height = st.sidebar.slider("Maximum Stacking Height", 1, 6, 4, 1,
                                              help="Maximum number of containers that can be stacked on top of each other")
    stacking_retrieval_base = st.sidebar.number_input("Base Retrieval Time (min)", min_value=1, value=15, step=1,
                                                        help="Minimum time needed to retrieve any container")
    stacking_retrieval_factor = st.sidebar.number_input("Additional Time per Container Above (min)", min_value=1, value=10, step=1,
                                                          help="Additional time needed for each container that must be moved")
    
    st.sidebar.markdown("---")
    max_berths = st.sidebar.number_input("Max Berths", min_value=1, value=MAX_BERTHS_DEFAULT, step=1)
    cranes_per_berth = st.sidebar.number_input("Cranes per Berth", min_value=1, value=CRANES_PER_BERTH_DEFAULT, step=1)
    unload_mean = st.sidebar.number_input("Container Unload Time Mean (min)", value=CONTAINER_UNLOAD_TIME_DEFAULT["mean"], step=0.1)
    unload_std = st.sidebar.number_input("Container Unload Time Std (min)", value=CONTAINER_UNLOAD_TIME_DEFAULT["std"], step=0.1)
    berth_transition = st.sidebar.number_input("Berth Transition Time (min)", value=BERTH_TRANSITION_TIME_DEFAULT, step=1)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Container Type Proportions")
    dry_prob = st.sidebar.slider("Dry Proportion", 0.0, 1.0, CONTAINER_TYPES_DEFAULT["dry"]["probability"], 0.01)
    reefer_prob = 1 - dry_prob

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Modal Split")
    truck_prob = st.sidebar.slider("Truck Proportion", 0.0, 1.0, MODAL_SPLIT_DEFAULT["truck"], 0.01)
    train_prob = 1.0 - truck_prob

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Gate Hours")
    gate_open = st.sidebar.number_input("Gate Open (hour)", min_value=0, max_value=23, value=GATE_HOURS_DEFAULT["open"], step=1)
    gate_close = st.sidebar.number_input("Gate Close (hour)", min_value=0, max_value=23, value=GATE_HOURS_DEFAULT["close"], step=1)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Train Schedule")
    trains_per_day = st.sidebar.number_input("Trains per Day", min_value=1, value=TRAIN_SCHEDULE_DEFAULT["trains_per_day"], step=1)
    train_capacity = st.sidebar.number_input("Train Capacity", min_value=1, value=TRAIN_SCHEDULE_DEFAULT["capacity"], step=1)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Starting Yard Utilization")
    starting_yard_util = st.sidebar.slider("Starting Yard Utilization (%)", 0, 100, 10, 1)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Equipment Availability Factors (%)")
    berth_availability_percent = st.sidebar.slider("Effective Berth Availability (%)", 0, 100, 100, 1)
    crane_availability_percent = st.sidebar.slider("Effective Crane Availability (%)", 0, 100, 100, 1)
    gate_availability_percent = st.sidebar.slider("Effective Gate Availability (%)", 0, 100, 100, 1)
    yard_availability_percent = st.sidebar.slider("Effective Yard Availability (%)", 0, 100, 100, 1)

    container_types = {
        "dry": {
            "probability": dry_prob,
            "yard_waiting_time": CONTAINER_TYPES_DEFAULT["dry"]["yard_waiting_time"]
        },
        "reefer": {
            "probability": reefer_prob,
            "yard_waiting_time": CONTAINER_TYPES_DEFAULT["reefer"]["yard_waiting_time"]
        }
    }
    modal_split = {"truck": truck_prob, "train": train_prob}

    gate_hours = {
        "open": gate_open,
        "close": gate_close,
        "gates_capacity": GATE_HOURS_DEFAULT["gates_capacity"],
        "truck_pickup_time": GATE_HOURS_DEFAULT["truck_pickup_time"],
        "containers_per_truck": GATE_HOURS_DEFAULT["containers_per_truck"]
    }
    
    if st.button("Run Simulation"):
        ship_schedule = st.session_state.ship_schedule.get_dataframe().to_dict('records')
        arrival_time_variability = {"mean": 1.0, "std": arrival_std}
        sim = PortSimulation(
            max_berths=max_berths,
            cranes_per_berth=cranes_per_berth,
            unload_time_mean=unload_mean,
            unload_time_std=unload_std,
            berth_transition_time=berth_transition,
            container_types=container_types,
            modal_split=modal_split,
            gate_hours=gate_hours,
            ship_schedule=ship_schedule,
            trains_per_day=trains_per_day,
            train_capacity=train_capacity,
            arrival_time_variability=arrival_time_variability,
            starting_yard_util_percent=starting_yard_util,
            simulation_start=simulation_start,
            effective_berth_availability=berth_availability_percent / 100,
            effective_crane_availability=crane_availability_percent / 100,
            effective_gate_availability=gate_availability_percent / 100,
            effective_yard_availability=yard_availability_percent / 100,
            max_stacking_height=max_stacking_height,
            stacking_retrieval_base_time=stacking_retrieval_base,
            stacking_retrieval_factor=stacking_retrieval_factor
        )
        # Run the simulation for a fixed duration (e.g. 15 days) so that trains are scheduled on all days.
        sim.run()
        
        # Once sim.run() returns, the simulation has ended.
        if sim.ship_arrivals:
            arrivals_df = pd.DataFrame(sim.ship_arrivals)
            for col in ['expected_arrival', 'actual_arrival', 'arrival_delta', 'berth_entry_time', 'departure_time', 'berth_wait_time', 'total_port_time']:
                if col in arrivals_df.columns:
                    if simulation_start and col in ['expected_arrival', 'actual_arrival', 'berth_entry_time', 'departure_time']:
                        arrivals_df[col] = arrivals_df[col].apply(lambda x: (simulation_start + timedelta(minutes=x)).strftime('%Y-%m-%d %H:%M') if pd.notnull(x) else None)
                    else:
                        arrivals_df[col] = arrivals_df[col].apply(lambda x: f"{x/60:.2f} hrs" if pd.notnull(x) else None)
        ui.render_dashboard(sim.ship_arrivals, sim.stats, sim.all_containers)

if __name__ == "__main__":
    main()