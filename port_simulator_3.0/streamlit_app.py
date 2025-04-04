# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from simulation_processes import run_simulation
from config import config

st.title("Container Terminal Simulation Dashboard")

st.sidebar.header("Simulation Configuration")
berth_count = st.sidebar.number_input("Number of Berths", value=config['berth_count'], min_value=1)
gate_count = st.sidebar.number_input("Number of Gates", value=config['gate_count'], min_value=1)
sim_duration = st.sidebar.number_input("Simulation Duration (hours)", value=config['simulation_duration'], min_value=1)

# Update configuration with user selections.
config['berth_count'] = berth_count
config['gate_count'] = gate_count
config['simulation_duration'] = sim_duration

if st.button("Run Simulation"):
    st.write("Running simulation...")
    df, metrics, yard_metrics = run_simulation(config)
    st.write("Simulation complete!")
    
    # Data Summary
    st.subheader("Data Summary")
    st.write(df[df.vessel!="Initial"].head())
    
    # 1. Total Yard Occupancy Over Time (Line Chart)
    occ_data = pd.DataFrame(metrics['yard_occupancy'], columns=["Time", "Occupancy"])
    fig1 = px.line(occ_data, x="Time", y="Occupancy",
                   title="Total Yard Occupancy Over Time",
                   labels={"Time": "Time (hours)", "Occupancy": "Total Occupancy"})
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Yard Occupancy Per Container Category Over Time with Capacity Lines
    fig2 = go.Figure()
    for ct in config['container_types']:
        cat = ct['name']
        data = pd.DataFrame(yard_metrics[cat], columns=["Time", "Occupancy"])
        fig2.add_trace(go.Scatter(x=data["Time"], y=data["Occupancy"],
                                  mode="lines", name=f"{cat} Occupancy"))
        # Add horizontal line for capacity.
        fig2.add_shape(type="line",
                       x0=min(data["Time"]), x1=max(data["Time"]),
                       y0=ct['yard_capacity'], y1=ct['yard_capacity'],
                       line=dict(dash="dash", width=1),
                       name=f"{cat} Capacity")
    fig2.update_layout(title="Yard Occupancy per Container Category Over Time",
                       xaxis_title="Time (hours)",
                       yaxis_title="Occupancy")
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Cumulative Unloaded Containers Over Time per Container Type
    unload_df = pd.DataFrame(metrics['cumulative_unloaded'], columns=["Time", "Container_Type"])
    # Calculate cumulative count for each container type.
    unload_df["Cumulative"] = unload_df.groupby("Container_Type").cumcount() + 1
    fig3 = px.line(unload_df, x="Time", y="Cumulative", color="Container_Type",
                   title="Cumulative Unloaded Containers Over Time",
                   labels={"Time": "Time (hours)", "Cumulative": "Cumulative Unloaded"})
    st.plotly_chart(fig3, use_container_width=True)
    
    # 4. Cumulative Departures Over Time per Mode
    dep_df = pd.DataFrame(metrics['cumulative_departures'], columns=["Time", "Mode", "Container_Type"])
    # Calculate cumulative departures per mode.
    dep_df["Cumulative"] = dep_df.groupby("Mode").cumcount() + 1
    fig4 = px.line(dep_df, x="Time", y="Cumulative", color="Mode",
                   title="Cumulative Departures Over Time by Mode",
                   labels={"Time": "Time (hours)", "Cumulative": "Cumulative Departures"})
    st.plotly_chart(fig4, use_container_width=True)
    
    # 5. Cumulative Departures Over Time per Container Type
    dep_df["Cumulative_Type"] = dep_df.groupby("Container_Type").cumcount() + 1
    fig5 = px.line(dep_df, x="Time", y="Cumulative_Type", color="Container_Type",
                   title="Cumulative Departures Over Time per Container Type",
                   labels={"Time": "Time (hours)", "Cumulative_Type": "Cumulative Departures"})
    st.plotly_chart(fig5, use_container_width=True)
    
    # 6. Overall Dwell Time Distribution (Boxplot)
    # Dwell time is calculated as departed_port - entered_yard.
    df["Dwell_Time"] = df["departed_port"] - df["entered_yard"]
    fig6 = px.box(df, y="Dwell_Time", title="Overall Dwell Time Distribution",
                  labels={"Dwell_Time": "Dwell Time (hours)"})
    st.plotly_chart(fig6, use_container_width=True)
    
    # 7. Dwell Time Distribution per Container Type (Boxplot)
    fig7 = px.box(df, x="container_type", y="Dwell_Time",
                  title="Dwell Time Distribution per Container Type",
                  labels={"container_type": "Container Type", "Dwell_Time": "Dwell Time (hours)"})
    st.plotly_chart(fig7, use_container_width=True)
    
    # 8. Dwell Time Distribution per Transportation Mode (Boxplot)
    fig8 = px.box(df, x="mode", y="Dwell_Time",
                  title="Dwell Time Distribution per Transportation Mode",
                  labels={"mode": "Transportation Mode", "Dwell_Time": "Dwell Time (hours)"})
    st.plotly_chart(fig8, use_container_width=True)
    
    st.success("All plots generated.")
