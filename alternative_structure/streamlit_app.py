# streamlit_app.py

import streamlit as st
import plotly.express as px
import pandas as pd
from main import main

st.title("Port Logistics Simulation Dashboard")
st.sidebar.header("Simulation Controls")

progress_bar = st.sidebar.progress(0)
progress_text = st.sidebar.empty()

def progress_callback(current, total_capacity, tq, trq, current_time):
    ratio = current / total_capacity if total_capacity > 0 else 0
    progress_bar.progress(int(ratio * 100))
    progress_text.text(f"Time {current_time:.2f}h: Yard occupancy {current}/{total_capacity}, Truck queue: {tq}, Train queue: {trq}")

if st.sidebar.button("Run Simulation"):
    st.write("Running simulation, please wait...")
    metrics = main(progress_callback=progress_callback)
    st.success("Simulation completed!")
    
    # Filter non-initial container departures.
    non_initial_departures = [record for record in metrics.container_departures if record[0] >= metrics.total_initial]

    # Plot Yard Occupancy Over Time.
    if metrics.yard_occupancy:
        times = [t for t, occ in metrics.yard_occupancy]
        occ = [occ for t, occ in metrics.yard_occupancy]
        fig1 = px.line(x=times, y=occ, labels={'x': 'Time (hours)', 'y': 'Yard Occupancy'},
                       title="Yard Occupancy Over Time")
        st.plotly_chart(fig1)
    
    # Distribution of Container Dwell Times (only non-initial containers).
    dwell_times = [dwell for cid, mode, t, dwell in non_initial_departures if dwell is not None]
    if dwell_times:
        fig2 = px.histogram(x=dwell_times, nbins=50, labels={'x': 'Container Dwell Time (hours)'}, 
                            title="Distribution of Container Dwell Times (Non-Initial)")
        st.plotly_chart(fig2)
    
    # Truck Queue Length Over Time.
    if metrics.truck_queue_lengths:
        tq_times = [t for t, length in metrics.truck_queue_lengths]
        tq_lengths = [length for t, length in metrics.truck_queue_lengths]
        fig3 = px.line(x=tq_times, y=tq_lengths, labels={'x': 'Time (hours)', 'y': 'Truck Queue Length'}, 
                       title="Truck Queue Length Over Time")
        st.plotly_chart(fig3)
    
    # Train Queue Length Over Time.
    if metrics.train_queue_lengths:
        trq_times = [t for t, length in metrics.train_queue_lengths]
        trq_lengths = [length for t, length in metrics.train_queue_lengths]
        fig4 = px.line(x=trq_times, y=trq_lengths, labels={'x': 'Time (hours)', 'y': 'Train Queue Length'}, 
                       title="Train Queue Length Over Time")
        st.plotly_chart(fig4)
    
    # Create summary table for duration metrics (non-initial containers only).
    def summarize(metric_list):
        if not metric_list:
            return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
        return {
            "n": len(metric_list),
            "mean": round(sum(metric_list) / len(metric_list), 2),
            "median": round(pd.Series(metric_list).median(), 2),
            "min": round(min(metric_list), 2),
            "max": round(max(metric_list), 2)
        }
    
    summary_data = {
        "Ship Waiting": summarize([v for v in metrics.ship_waiting_times]),
        "Berth Queue": summarize([v for v in metrics.berth_waiting_times]),
        "Unloading": summarize([v for v in metrics.unloading_durations]),
        "Yard Storage": summarize([v for v in metrics.yard_storage_times]),
        "Stacking Retrieval": summarize([v for v in metrics.stacking_retrieval_times]),
        "Inland Transport": summarize([v for v in metrics.inland_transport_wait_times])
    }
    
    summary_rows = []
    for metric, stats in summary_data.items():
        summary_rows.append({
            "Metric": metric,
            "n": stats["n"],
            "Mean": stats["mean"],
            "Median": stats["median"],
            "Min": stats["min"],
            "Max": stats["max"]
        })
    df_summary = pd.DataFrame(summary_rows)
    st.subheader("Duration Metrics Summary (All Containers)")
    st.dataframe(df_summary)
    
    # Create a summary table for departures by mode for non-initial containers.
    truck_departures = len([record for record in non_initial_departures if record[1] == "Road"])
    rail_departures = len([record for record in non_initial_departures if record[1] == "Rail"])
    
    departure_summary = pd.DataFrame({
        "Mode": ["Truck (Road)", "Train (Rail)"],
        "Number of Containers": [truck_departures, rail_departures]
    })
    
    st.subheader("Total Departures by Mode (Non-Initial Containers)")
    st.table(departure_summary)
