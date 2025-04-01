import streamlit as st
import plotly.express as px
import pandas as pd
from main import main

st.title("Port Logistics Simulation Dashboard")
st.sidebar.header("Simulation Controls")

progress_bar = st.sidebar.progress(0)
progress_text = st.sidebar.empty()

def progress_callback(total, total_capacity, truck_q, train_q, current_time):
    ratio = total / total_capacity if total_capacity > 0 else 0
    progress_bar.progress(int(ratio * 100))
    progress_text.text(f"Time {current_time:.2f}h: Yard occupancy {total}/{total_capacity}, Truck queue: {truck_q}, Train queue: {train_q}")

if st.sidebar.button("Run Simulation"):
    st.write("Running simulation, please wait...")
    metrics = main(progress_callback=progress_callback)
    st.success("Simulation completed!")
    
    # Create container DataFrame, filter non-initial containers.
    if metrics.container_records:
        df_containers = pd.DataFrame(metrics.container_records)
        # Compute total_dwell_time = departed_port - entered_yard if both exist.
        if "departed_port" in df_containers.columns and "entered_yard" in df_containers.columns:
            df_containers["total_dwell_time"] = df_containers.apply(
                lambda row: row["departed_port"] - row["entered_yard"]
                if pd.notnull(row["departed_port"]) and pd.notnull(row["entered_yard"])
                else None, axis=1)
        
        # Filter out initial containers.
        df_non_initial = df_containers[df_containers["is_initial"] == False]
        st.subheader("Container Records (Non-Initial)")
        
        # List of derived duration columns to plot distributions.
        duration_cols = [
            "vessel_delays",
            "berth_delays",
            "unloading_time",
            "yard_time",
            "retrieval_time",
            "queuing_for_tsp",
            "loading_time",
            "total_dwell_time"
        ]

        st.dataframe(df_non_initial)
        
        # Select only the duration columns and melt the DataFrame into long format.
        df_durations = df_non_initial[duration_cols].melt(var_name="Duration", value_name="Hours")
        # Remove any rows with NaN values.
        df_durations = df_durations.dropna()

        if not df_durations.empty:
            fig_box = px.box(
                df_durations,
                x="Duration",
                y="Hours",
                title="Derived Duration Distributions",
                labels={"Duration": "Duration Type", "Hours": "Duration (hours)"}
            )
            st.plotly_chart(fig_box)

    
    # Plot Yard Utilization Over Time.
    if metrics.yard_utilization:
        df_yard = pd.DataFrame(metrics.yard_utilization, columns=["Time", "Yard", "Occupancy"])
        fig_yard = px.line(df_yard, x="Time", y="Occupancy", color="Yard",
                           title="Yard Utilization Over Time",
                           labels={"Time": "Time (hours)", "Occupancy": "Number of Containers"})
        st.plotly_chart(fig_yard)
    
    # Plot Truck Queue Length Over Time.
    if metrics.truck_queue_lengths:
        df_truck = pd.DataFrame(metrics.truck_queue_lengths, columns=["Time", "Truck_Queue_Length"])
        fig_truck = px.line(df_truck, x="Time", y="Truck_Queue_Length",
                            title="Truck Queue Length Over Time",
                            labels={"Time": "Time (hours)", "Truck_Queue_Length": "Truck Queue Length"})
        st.plotly_chart(fig_truck)
    
    # Plot Train Queue Length Over Time.
    if metrics.train_queue_lengths:
        df_train = pd.DataFrame(metrics.train_queue_lengths, columns=["Time", "Train_Queue_Length"])
        fig_train = px.line(df_train, x="Time", y="Train_Queue_Length",
                            title="Train Queue Length Over Time",
                            labels={"Time": "Time (hours)", "Train_Queue_Length": "Train Queue Length"})
        st.plotly_chart(fig_train)
