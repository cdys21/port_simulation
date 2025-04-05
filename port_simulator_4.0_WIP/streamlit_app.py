import streamlit as st
import json
import pandas as pd
import plotly.express as px
from simulation_processes import run_simulation
from config import default_config

# Define presets (you can expand these as needed)
presets = {
    "Default": default_config,
    "High Throughput": {
        "berth_count": 6,
        "gate_count": 150,
        "simulation_duration": 200,
        "save_csv": False,
        "output_file": "container_checkpoints.csv",
        "container_types": [
            {
                "name": "Standard",
                "yard_capacity": 40000,
                "initial_yard_fill": 0.5,
                "rail_percentage": 0.20,
                "unload_time": [0.008, 0.03, 0.015],
                "truck_process_time": [0.08, 0.25, 0.1]
            },
            {
                "name": "Reefer",
                "yard_capacity": 15000,
                "initial_yard_fill": 0.4,
                "rail_percentage": 0.25,
                "unload_time": [0.015, 0.035, 0.02],
                "truck_process_time": [0.12, 0.3, 0.18]
            },
            {
                "name": "Hazardous",
                "yard_capacity": 6000,
                "initial_yard_fill": 0.35,
                "rail_percentage": 0.10,
                "unload_time": [0.012, 0.045, 0.025],
                "truck_process_time": [0.18, 0.4, 0.28]
            }
        ],
        "vessels": default_config["vessels"]
    },
    "Energy Saving": {
        "berth_count": 3,
        "gate_count": 100,
        "simulation_duration": 150,
        "save_csv": False,
        "output_file": "container_checkpoints.csv",
        "container_types": [
            {
                "name": "Standard",
                "yard_capacity": 25000,
                "initial_yard_fill": 0.7,
                "rail_percentage": 0.10,
                "unload_time": [0.012, 0.036, 0.02],
                "truck_process_time": [0.12, 0.35, 0.15]
            },
            {
                "name": "Reefer",
                "yard_capacity": 8000,
                "initial_yard_fill": 0.6,
                "rail_percentage": 0.15,
                "unload_time": [0.025, 0.045, 0.03],
                "truck_process_time": [0.18, 0.4, 0.25]
            },
            {
                "name": "Hazardous",
                "yard_capacity": 4000,
                "initial_yard_fill": 0.5,
                "rail_percentage": 0.05,
                "unload_time": [0.018, 0.05, 0.03],
                "truck_process_time": [0.25, 0.45, 0.35]
            }
        ],
        "vessels": default_config["vessels"]
    }
}

st.title("Container Terminal Simulation Dashboard")

# Sidebar: Preset Selection
preset_choice = st.sidebar.selectbox("Select a Preset", list(presets.keys()))
preset_config = presets[preset_choice]

# Step 1: General Settings
st.sidebar.markdown("## Step 1: General Settings")
berth_count = st.sidebar.number_input("Berth Count", value=preset_config["berth_count"], min_value=1)
gate_count = st.sidebar.number_input("Gate Count", value=preset_config["gate_count"], min_value=1)
simulation_duration = st.sidebar.number_input("Simulation Duration (hours)", 
                                              value=preset_config["simulation_duration"], min_value=1)
save_csv = st.sidebar.checkbox("Save CSV", value=preset_config["save_csv"])
output_file = st.sidebar.text_input("Output File", value=preset_config["output_file"])

# Step 2: Container Type Settings
st.sidebar.markdown("## Step 2: Container Type Settings")
container_types = []
# Create one expander per container type at the sidebar level
for ct in preset_config["container_types"]:
    with st.sidebar.expander(f"Container Type: {ct['name']}", expanded=False):
        yard_capacity = st.number_input(f"{ct['name']} Yard Capacity", value=ct["yard_capacity"], min_value=1)
        initial_yard_fill = st.slider(f"{ct['name']} Initial Yard Fill", 0.0, 1.0, value=ct["initial_yard_fill"])
        rail_percentage = st.slider(f"{ct['name']} Rail Percentage", 0.0, 1.0, value=ct["rail_percentage"])
        unload_low = st.number_input(f"{ct['name']} Unload Time Low", value=ct["unload_time"][0], format="%.3f")
        unload_high = st.number_input(f"{ct['name']} Unload Time High", value=ct["unload_time"][1], format="%.3f")
        unload_mode = st.number_input(f"{ct['name']} Unload Time Mode", value=ct["unload_time"][2], format="%.3f")
        truck_low = st.number_input(f"{ct['name']} Truck Process Time Low", value=ct["truck_process_time"][0], format="%.3f")
        truck_high = st.number_input(f"{ct['name']} Truck Process Time High", value=ct["truck_process_time"][1], format="%.3f")
        truck_mode = st.number_input(f"{ct['name']} Truck Process Time Mode", value=ct["truck_process_time"][2], format="%.3f")
        
        container_types.append({
            "name": ct["name"],
            "yard_capacity": yard_capacity,
            "initial_yard_fill": initial_yard_fill,
            "rail_percentage": rail_percentage,
            "unload_time": [unload_low, unload_high, unload_mode],
            "truck_process_time": [truck_low, truck_high, truck_mode]
        })

# Step 3: Vessel Schedule
st.sidebar.markdown("## Step 3: Vessel Schedule")
vessels = []
# Create one expander per vessel
for i, vessel in enumerate(preset_config["vessels"]):
    with st.sidebar.expander(f"Vessel {i+1}", expanded=False):
        vessel_name = st.text_input("Vessel Name", value=vessel["name"], key=f"vessel_name_{i}")
        day = st.number_input("Day", value=vessel["day"], min_value=1, key=f"vessel_day_{i}")
        hour = st.number_input("Hour", value=vessel["hour"], min_value=0, max_value=23, key=f"vessel_hour_{i}")
        # Editable container counts per container type for this vessel
        container_counts = {}
        st.markdown("**Container Counts:**")
        for ct in container_types:
            # Use the preset vessel container count if available; otherwise default to 0.
            default_count = vessel.get("container_counts", {}).get(ct["name"], 0)
            count = st.number_input(f"{ct['name']}", value=default_count, min_value=0, key=f"{vessel_name}_{ct['name']}")
            container_counts[ct["name"]] = count
        
        vessels.append({
            "name": vessel_name,
            "day": day,
            "hour": hour,
            "container_counts": container_counts
        })

# Assemble the full configuration dictionary
config = {
    "berth_count": berth_count,
    "gate_count": gate_count,
    "simulation_duration": simulation_duration,
    "save_csv": save_csv,
    "output_file": output_file,
    "container_types": container_types,
    "vessels": vessels
}

if st.button("Run Simulation"):
    progress_bar = st.progress(0)
    
    def update_progress(progress):
        progress_bar.progress(int(progress * 100))
    
    st.write("Running simulation...")
    df, metrics, yard_metrics = run_simulation(config, progress_callback=update_progress)
    st.write("Simulation complete!")
    
    st.subheader("Data Summary")
    st.write(df[df.vessel!="Initial"].head())
    
    # 1. Total Yard Occupancy Over Time
    occ_data = pd.DataFrame(metrics["yard_occupancy"], columns=["Time", "Occupancy"])
    fig1 = px.line(occ_data, x="Time", y="Occupancy",
                   title="Total Yard Occupancy Over Time",
                   labels={"Time": "Time (hours)", "Occupancy": "Total Occupancy"})
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Yard Occupancy Per Container Category Over Time with Capacity Lines
    fig2 = px.line()
    for ct in config["container_types"]:
        cat = ct["name"]
        data = pd.DataFrame(yard_metrics[cat], columns=["Time", "Occupancy"])
        fig2.add_scatter(x=data["Time"], y=data["Occupancy"], mode="lines", name=f"{cat} Occupancy")
        fig2.add_hline(y=ct["yard_capacity"], line_dash="dash", annotation_text=f"{cat} Capacity")
    fig2.update_layout(title="Yard Occupancy per Container Category Over Time",
                       xaxis_title="Time (hours)",
                       yaxis_title="Occupancy")
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Cumulative Unloaded Containers Over Time per Container Type
    unload_df = pd.DataFrame(metrics["cumulative_unloaded"], columns=["Time", "Container_Type"])
    unload_df["Cumulative"] = unload_df.groupby("Container_Type").cumcount() + 1
    fig3 = px.line(unload_df, x="Time", y="Cumulative", color="Container_Type",
                   title="Cumulative Unloaded Containers Over Time",
                   labels={"Time": "Time (hours)", "Cumulative": "Cumulative Unloaded"})
    st.plotly_chart(fig3, use_container_width=True)
    
    # 4. Cumulative Departures Over Time per Mode
    dep_df = pd.DataFrame(metrics["cumulative_departures"], columns=["Time", "Mode", "Container_Type"])
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
    df_clean = df[df.vessel!="Initial"]
    df_clean["Dwell_Time"] = (df_clean["departed_port"] - df_clean["entered_yard"])/60
    fig6 = px.box(df_clean, y="Dwell_Time", title="Overall Dwell Time Distribution",
                  labels={"Dwell_Time": "Dwell Time (days)"})
    st.plotly_chart(fig6, use_container_width=True)
    
    # 7. Dwell Time Distribution per Container Type
    fig7 = px.box(df_clean, x="container_type", y="Dwell_Time",
                  title="Dwell Time Distribution per Container Type",
                  labels={"container_type": "Container Type", "Dwell_Time": "Dwell Time (days)"})
    st.plotly_chart(fig7, use_container_width=True)
    
    # 8. Dwell Time Distribution per Transportation Mode
    fig8 = px.box(df_clean, x="mode", y="Dwell_Time",
                  title="Dwell Time Distribution per Transportation Mode",
                  labels={"mode": "Transportation Mode", "Dwell_Time": "Dwell Time (days)"})
    st.plotly_chart(fig8, use_container_width=True)
    
    st.success("All plots generated.")
