# ui/dashboard.py
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import yaml
import pandas as pd
import matplotlib.pyplot as plt
from simulation.simulation_runner import run_simulation, load_config

def main():
    st.title("Port Simulation Dashboard")

    # Upload a custom configuration file (optional)
    config_file = st.sidebar.file_uploader("Upload Config File", type=["yaml", "yml"])
    if config_file is not None:
        config = yaml.safe_load(config_file)
    else:
        st.sidebar.info("Using default configuration.")
        config = load_config()

    # Display configuration parameters
    st.sidebar.header("Simulation Parameters")
    st.sidebar.write(config)

    if st.sidebar.button("Run Simulation"):
        st.info("Running simulation. Please wait...")
        df, metrics = run_simulation(config)
        st.success("Simulation complete!")

        # Show simulation summary
        st.subheader("Simulation Summary")
        st.write(f"Number of containers processed: {len(df)}")
        
        # Display metrics as plots
        yard_df = pd.DataFrame(metrics['yard_occupancy'], columns=['time', 'occupancy'])
        truck_df = pd.DataFrame(metrics['truck_queue'], columns=['time', 'truck_queue'])
        rail_df = pd.DataFrame(metrics['rail_queue'], columns=['time', 'rail_queue'])
        
        st.subheader("Yard Occupancy Over Time")
        fig, ax = plt.subplots()
        ax.plot(yard_df['time'], yard_df['occupancy'])
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Yard Occupancy')
        ax.set_title('Yard Occupancy Over Time')
        st.pyplot(fig)
        
        st.subheader("Truck Queue Over Time")
        fig2, ax2 = plt.subplots()
        ax2.plot(truck_df['time'], truck_df['truck_queue'])
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Truck Queue Length')
        ax2.set_title('Truck Queue Over Time')
        st.pyplot(fig2)
        
        st.subheader("Rail Queue Over Time")
        fig3, ax3 = plt.subplots()
        ax3.plot(rail_df['time'], rail_df['rail_queue'])
        ax3.set_xlabel('Time (hours)')
        ax3.set_ylabel('Rail Queue Length')
        ax3.set_title('Rail Queue Over Time')
        st.pyplot(fig3)
        
        st.subheader("Container Data")
        st.dataframe(df)

if __name__ == '__main__':
    main()
