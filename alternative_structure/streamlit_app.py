import streamlit as st
import plotly.express as px
from main import main  # our simulation function that returns a Metrics instance

st.title("Port Logistics Simulation Dashboard")

st.sidebar.header("Simulation Controls")
# Although our simulation terminates on its own, you might add additional controls later.
if st.sidebar.button("Run Simulation"):
    st.write("Running simulation, please wait...")
    metrics = main()  # Run the simulation; it prints output to console and returns metrics
    st.success("Simulation completed!")
    
    # Plot yard occupancy over time.
    if metrics.yard_occupancy:
        times = [t for t, occ in metrics.yard_occupancy]
        occupancy = [occ for t, occ in metrics.yard_occupancy]
        fig = px.line(x=times, y=occupancy, labels={'x': 'Time (hours)', 'y': 'Yard Occupancy'},
                      title="Yard Occupancy Over Time")
        st.plotly_chart(fig)