# streamlit_app.py
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from simulation_processes import run_simulation
from config import default_config

st.title("Container Terminal Simulation Dashboard")

st.sidebar.header("Modify Configuration")
config_text = st.sidebar.text_area("Edit the simulation config (JSON format)", 
                                   value=json.dumps(default_config, indent=4),
                                   height=400)
try:
    config = json.loads(config_text)
except Exception as e:
    st.error("Invalid JSON configuration!")
    st.stop()

st.sidebar.header("Other Options")
if st.sidebar.button("Reset to Default Config"):
    config = default_config

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
