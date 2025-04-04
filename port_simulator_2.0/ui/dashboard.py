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
import plotly.graph_objects as go
import plotly.express as px
from simulation.simulation_runner import run_simulation, load_config

def compute_key_stats(df, yard_df, truck_df, rail_df):
    # Filter non-initial containers
    df_non_initial = df[df['vessel'] != "Initial"].copy()
    df_non_initial = df_non_initial.dropna(subset=['entered_yard', 'departed_port'])
    
    # Calculate dwell times (in hours)
    df_non_initial["dwell_time"] = df_non_initial["departed_port"] - df_non_initial["entered_yard"]
    df_non_initial["unloading_time"] = df_non_initial["entered_yard"] - df_non_initial["vessel_berths"]
    
    avg_dwell = df_non_initial["dwell_time"].mean() if not df_non_initial.empty else None
    avg_dwell_road = df_non_initial[df_non_initial["mode"]=="Road"]["dwell_time"].mean() if not df_non_initial.empty else None
    avg_dwell_rail = df_non_initial[df_non_initial["mode"]=="Rail"]["dwell_time"].mean() if not df_non_initial.empty else None
    
    max_yard_occ = yard_df['occupancy'].max() if not yard_df.empty else None
    avg_rail_queue = rail_df['rail_queue'].mean() if not rail_df.empty else None
    avg_truck_queue = truck_df['truck_queue'].mean() if not truck_df.empty else None
    vessels_unloaded = df_non_initial["vessel"].nunique() if not df_non_initial.empty else 0
    avg_unloading_time = df_non_initial["unloading_time"].mean() if not df_non_initial.empty else None

    return {
        "Avg Dwell Time (hrs)": avg_dwell,
        "Avg Dwell Time - Road (hrs)": avg_dwell_road,
        "Avg Dwell Time - Rail (hrs)": avg_dwell_rail,
        "Max Yard Occupancy": max_yard_occ,
        "Avg Rail Queue (count)": avg_rail_queue,
        "Avg Truck Queue (count)": avg_truck_queue,
        "Vessels Unloaded": vessels_unloaded,
        "Avg Unloading Time (hrs)": avg_unloading_time,
    }

def plot_yard_occupancy(yard_df, df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=yard_df['time'], y=yard_df['occupancy'],
                             mode='lines',
                             name='Yard Occupancy'))
    # For vessel arrivals, get non-initial containers, group by vessel and get min vessel_arrives
    df_vessels = df[df['vessel'] != "Initial"].dropna(subset=['vessel_arrives'])
    if not df_vessels.empty:
        vessel_arrivals = df_vessels.groupby("vessel")["vessel_arrives"].min().reset_index()
        for idx, row in vessel_arrivals.iterrows():
            fig.add_vline(x=row["vessel_arrives"], line_width=1, line_dash="dash", line_color="green",
                          annotation_text=row["vessel"], annotation_position="top right")
    fig.update_layout(title="Yard Occupancy Over Time",
                      xaxis_title="Time (hrs)",
                      yaxis_title="Occupancy")
    return fig

def plot_queue(df_queue, queue_type):
    # queue_type: "Truck" or "Rail"
    y_col = "truck_queue" if queue_type=="Truck" else "rail_queue"
    fig = px.line(df_queue, x="time", y=y_col,
                  title=f"{queue_type} Queue Over Time",
                  labels={"time": "Time (hrs)", y_col: f"{queue_type} Queue Length"})
    return fig

def plot_dwell_boxplots(df):
    # Filter non-initial containers and compute durations
    df_non_initial = df[df['vessel'] != "Initial"].copy()
    df_non_initial = df_non_initial.dropna(subset=['entered_yard', 'departed_port', 'vessel_berths'])
    if df_non_initial.empty:
        return go.Figure()
    df_non_initial["vessel_arrival_uncertainty"] = df_non_initial['vessel_arrives'] - df_non_initial['vessel_scheduled_arrival']
    df_non_initial["berth_delay"] = df_non_initial['vessel_berths'] - df_non_initial['vessel_arrives']
    df_non_initial["unloading_time"] = df_non_initial['entered_yard'] - df_non_initial['vessel_berths']
    df_non_initial["time_in_yard_waiting"] = df_non_initial['departed_port'] - df_non_initial['entered_yard']
    df_non_initial["total_duration"] = df_non_initial['departed_port'] - df_non_initial['vessel_scheduled_arrival']
    
    # Prepare boxplot data
    fig = go.Figure()
    for col, name in zip(["vessel_arrival_uncertainty", "berth_delay", "unloading_time", "time_in_yard_waiting", "total_duration"],
                         ["Vessel Arrival Uncertainty", "Berth Delay", "Unloading Time", "Time in Yard Waiting", "Total Duration"]):
        fig.add_trace(go.Box(y=df_non_initial[col], name=name))
    fig.update_layout(title="Dwell Time Boxplots (hrs)",
                      yaxis_title="Duration (hrs)")
    return fig

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

        # Convert metric lists to DataFrames
        yard_df = pd.DataFrame(metrics['yard_occupancy'], columns=['time', 'occupancy'])
        truck_df = pd.DataFrame(metrics['truck_queue'], columns=['time', 'truck_queue'])
        rail_df = pd.DataFrame(metrics['rail_queue'], columns=['time', 'rail_queue'])

        # Compute key stats from container DataFrame and queue data
        stats = compute_key_stats(df, yard_df, truck_df, rail_df)

        # Display key stats at the top in a structured layout
        st.subheader("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Dwell Time (days)", f"{stats['Avg Dwell Time (hrs)']/24:.2f}" if stats['Avg Dwell Time (hrs)'] is not None else "N/A")
        col1.metric("Avg Unloading Time (days)", f"{stats['Avg Unloading Time (hrs)']/24:.2f}" if stats['Avg Unloading Time (hrs)'] is not None else "N/A")
        col2.metric("Avg Dwell Time - Road (days)", f"{stats['Avg Dwell Time - Road (hrs)']/24:.2f}" if stats['Avg Dwell Time - Road (hrs)'] is not None else "N/A")
        col2.metric("Avg Dwell Time - Rail (days)", f"{stats['Avg Dwell Time - Rail (hrs)']/24:.2f}" if stats['Avg Dwell Time - Rail (hrs)'] is not None else "N/A")
        col3.metric("Max Yard Occupancy", f"{stats['Max Yard Occupancy']:.0f}" if stats['Max Yard Occupancy'] is not None else "N/A")
        col3.metric("Vessels Unloaded", f"{stats['Vessels Unloaded']}")
        st.markdown("---")
        col4, col5 = st.columns(2)
        col4.metric("Avg Truck Queue Length", f"{stats['Avg Truck Queue (count)']:.2f}" if stats['Avg Truck Queue (count)'] is not None else "N/A")
        col5.metric("Avg Rail Queue Length", f"{stats['Avg Rail Queue (count)']:.2f}" if stats['Avg Rail Queue (count)'] is not None else "N/A")
        st.markdown("---")

        # Show simulation summary (non-initial containers)
        st.subheader("Container Data (Non-initial)")
        st.dataframe(df[df.vessel != "Initial"])

        # Plot yard occupancy with vessel arrival vertical lines (Plotly)
        st.subheader("Yard Occupancy Over Time")
        fig_yard = plot_yard_occupancy(yard_df, df)
        st.plotly_chart(fig_yard, use_container_width=True)

        # Plot truck queue over time
        st.subheader("Truck Queue Over Time")
        fig_truck = plot_queue(truck_df, "Truck")
        st.plotly_chart(fig_truck, use_container_width=True)

        # Plot rail queue over time
        st.subheader("Rail Queue Over Time")
        fig_rail = plot_queue(rail_df, "Rail")
        st.plotly_chart(fig_rail, use_container_width=True)

        # Plot dwell time boxplots
        st.subheader("Dwell Time Boxplots")
        fig_box = plot_dwell_boxplots(df)
        st.plotly_chart(fig_box, use_container_width=True)

if __name__ == '__main__':
    main()
