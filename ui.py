# ui.py using streamlit
import streamlit as st
import plotly.graph_objects as go
from datetime import timedelta
import random
import plotly.express as px
import pandas as pd
import numpy as np

def render_ship_arrivals(ship_arrivals):
    """
    Render the ship arrivals data as a table.
    """
    st.markdown("## Ship Arrivals")
    if ship_arrivals:
        df = pd.DataFrame(ship_arrivals)
        st.dataframe(df)
    else:
        st.write("No ship arrivals data available.")

def render_dwell_time_boxplot(stats):
    """
    Render a horizontal box plot for dwell times (converted from minutes to days).
    """
    st.markdown("## Dwell Times (Box Plot)")
    # Convert dwell times from minutes to days
    dry_dwell_days = [x / (24 * 60) for x in stats.dwell_times['dry']]
    reefer_dwell_days = [x / (24 * 60) for x in stats.dwell_times['reefer']]
    
    fig = go.Figure()
    if dry_dwell_days:
        fig.add_trace(go.Box(x=dry_dwell_days, name='Dry', orientation='h'))
    if reefer_dwell_days:
        fig.add_trace(go.Box(x=reefer_dwell_days, name='Reefer', orientation='h'))
    
    fig.update_layout(
        title='Dwell Time Box Plot (Days)',
        xaxis_title='Days from Expected Arrival to Departure'
    )
    st.plotly_chart(fig, use_container_width=True)

def render_resource_heatmap(stats):
    """
    Render a minute-level heatmap for equipment and rail usage.
    
    Expects:
      - stats.resource_usage_by_minute: a dict with keys 'berths', 'cranes', 'gate', 'yard'.
      - stats.train_departure_records: a list of dicts containing train departure records.
    """

    st.markdown("## Equipment & Rail Usage Heatmap (Minute-Level)")

    # Define the resource keys for which we have instantaneous values.
    usage_keys = ['berths', 'cranes', 'gate', 'yard']
    all_minutes = set()
    for key in usage_keys:
        all_minutes |= set(stats.resource_usage_by_minute.get(key, {}).keys())
    sorted_minutes = sorted(all_minutes)

    # Build a DataFrame for resource usage by minute.
    usage_data = []
    for minute in sorted_minutes:
        entry = {'minute': minute}
        for key in usage_keys:
            entry[key] = stats.resource_usage_by_minute.get(key, {}).get(minute, 0)
        usage_data.append(entry)
    df_usage = pd.DataFrame(usage_data).sort_values('minute') if usage_data else pd.DataFrame()

    # Process rail usage from train departure records.
    rail_df = pd.DataFrame(stats.train_departure_records)
    if not rail_df.empty:
        # Convert departure times to minutes offset.
        if pd.api.types.is_datetime64_any_dtype(rail_df["Departure Time"]):
            rail_df["minute"] = ((rail_df["Departure Time"] - rail_df["Departure Time"].min())
                                 .dt.total_seconds() / 60).astype(int)
        else:
            rail_df["minute"] = (rail_df["Departure Time"] / 60).astype(int)
        # Compute rail utilization as fraction of train capacity.
        rail_df["rail"] = rail_df["Total Loaded"] / rail_df["Capacity"]
        rail_minutely = rail_df.groupby("minute")["rail"].mean().reset_index()
    else:
        rail_minutely = pd.DataFrame(columns=["minute", "rail"])

    # Merge rail usage into our usage DataFrame.
    if not df_usage.empty:
        df_usage = pd.merge(df_usage, rail_minutely, on="minute", how="left")
        df_usage["rail"] = df_usage["rail"].fillna(method="ffill").fillna(0)
    else:
        df_usage = rail_minutely.copy()

    # Define the order of resources for display.
    resource_order = ["berths", "cranes", "yard", "gate", "rail"]
    heat_data = []
    for row in df_usage.itertuples(index=False):
        for resource in resource_order:
            heat_data.append({
                "minute": row.minute,
                "resource": resource,
                "usage": getattr(row, resource)
            })
    df_heatmap = pd.DataFrame(heat_data)
    df_heatmap["resource"] = pd.Categorical(df_heatmap["resource"],
                                            categories=resource_order, ordered=True)

    # Pivot to create a matrix: resources as rows, minutes as columns.
    df_pivot = df_heatmap.pivot(index="resource", columns="minute", values="usage")

    # Create the heatmap.
    fig_heat = px.imshow(
        df_pivot,
        color_continuous_scale=["blue", "red"],
        zmin=0,
        zmax=1,
        labels=dict(color="Usage Fraction"),
        aspect="auto"
    )
    fig_heat.update_xaxes(title="Minute")
    fig_heat.update_yaxes(title="Resource")
    fig_heat.update_layout(title="Equipment & Rail Usage Heatmap (Minute-Level)")
    st.plotly_chart(fig_heat, use_container_width=True)

def plot_dwell_time_waterfall(stats):
    """
    Plot a waterfall chart for the dwell time components.
    """
    avg_components = {
        'Ship Waiting (Schedule Delay)': np.mean(stats.dwell_components['ship_arrival_delay']) / 60 if stats.dwell_components['ship_arrival_delay'] else 0,
        'Berth Queue Time': np.mean(stats.dwell_components['berth_wait_time']) / 60 if stats.dwell_components['berth_wait_time'] else 0,
        'Unloading Process': np.mean(stats.dwell_components['container_unloading']) / 60 if stats.dwell_components['container_unloading'] else 0,
        'Yard Storage Time': np.mean(stats.dwell_components['yard_storage']) / 60 if stats.dwell_components['yard_storage'] else 0,
        'Stacking Retrieval': np.mean(stats.dwell_components['stacking_retrieval']) / 60 if stats.dwell_components['stacking_retrieval'] else 0,
        'Inland Transport Wait': np.mean(stats.dwell_components['departure_wait']) / 60 if stats.dwell_components['departure_wait'] else 0
    }
    ship_total = avg_components['Ship Waiting (Schedule Delay)'] + avg_components['Berth Queue Time'] + avg_components['Unloading Process']
    yard_total = avg_components['Yard Storage Time'] + avg_components['Stacking Retrieval'] + avg_components['Inland Transport Wait']
    overall_total = ship_total + yard_total

    st.markdown("## Dwell Time Breakdown (Waterfall Chart)")
    st.markdown("""
    **Understanding Dwell Time Components:**
    - **Ship Waiting (Schedule Delay)**: Time between scheduled arrival and actual arrival of the vessel.
    - **Berth Queue Time**: Time the vessel waits for an available berth after arriving at port.
    - **Unloading Process**: Time from when the ship docks until the container reaches the yard.
    - **Yard Storage Time**: Planned storage time in the yard (customs, documentation, etc.).
    - **Stacking Retrieval**: Additional time needed to retrieve containers based on stacking level.
    - **Inland Transport Wait**: Additional time waiting for truck/train pickup after container is ready.
    """)
    
    # Create the waterfall chart
    fig = go.Figure(go.Waterfall(
        name="Dwell Time Breakdown",
        orientation="v",
        measure=["relative", "relative", "relative", "relative", "relative", "relative", "total"],
        x=["Ship Waiting", "Berth Queue", "Unloading", "Yard Storage", "Stacking Retrieval", "Transport Wait", "Total Dwell Time"],
        y=[
            avg_components['Ship Waiting (Schedule Delay)'],
            avg_components['Berth Queue Time'],
            avg_components['Unloading Process'],
            avg_components['Yard Storage Time'],
            avg_components['Stacking Retrieval'],
            avg_components['Inland Transport Wait'],
            0
        ]
    ))
    fig.update_layout(
        title="Container Dwell Time Components (Waterfall Chart)",
        yaxis_title="Hours",
        height=500,
        showlegend=False
    )
    
    # Annotate each component with its percentage of the overall total
    components = ['Ship Waiting (Schedule Delay)', 'Berth Queue Time', 'Unloading Process', 
                  'Yard Storage Time', 'Stacking Retrieval', 'Inland Transport Wait']
    labels = ["Ship Waiting", "Berth Queue", "Unloading", "Yard Storage", "Stacking Retrieval", "Transport Wait"]
    for i, comp in enumerate(components):
        percentage = (avg_components[comp] / overall_total) * 100 if overall_total > 0 else 0
        # Calculate the midpoint for annotation on the stacked bar
        midpoint = (avg_components[comp] / 2) if i == 0 else sum([avg_components[c] for c in components[:i]]) + avg_components[comp] / 2
        fig.add_annotation(
            x=labels[i],
            y=midpoint,
            text=f"{percentage:.1f}%",
            showarrow=False,
            font=dict(color="white", size=12)
        )
    st.plotly_chart(fig, use_container_width=True)

def plot_dwell_time_boxplot_components(stats):
    """
    Plot a box plot showing the distribution of each dwell time component.
    """
    st.markdown("## Distribution of Dwell Time Components (Box Plot)")
    component_data = {
        'Ship Waiting (Schedule Delay)': [x / 60 for x in stats.dwell_components['ship_arrival_delay']] if stats.dwell_components['ship_arrival_delay'] else [],
        'Berth Queue Time': [x / 60 for x in stats.dwell_components['berth_wait_time']] if stats.dwell_components['berth_wait_time'] else [],
        'Unloading Process': [x / 60 for x in stats.dwell_components['container_unloading']] if stats.dwell_components['container_unloading'] else [],
        'Yard Storage Time': [x / 60 for x in stats.dwell_components['yard_storage']] if stats.dwell_components['yard_storage'] else [],
        'Stacking Retrieval': [x / 60 for x in stats.dwell_components['stacking_retrieval']] if stats.dwell_components['stacking_retrieval'] else [],
        'Inland Transport Wait': [x / 60 for x in stats.dwell_components['departure_wait']] if stats.dwell_components['departure_wait'] else []
    }
    fig = go.Figure()
    for component, data in component_data.items():
        if data:
            fig.add_trace(go.Box(y=data, name=component))
    fig.update_layout(
        title="Distribution of Dwell Time Components",
        yaxis_title="Hours",
        boxmode='group',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_dwell_time_statistics(stats):
    """
    Display a table of detailed dwell time statistics (in hours) for each component.
    """
    st.markdown("## Detailed Dwell Time Statistics (Hours)")
    stats_table = {}
    for component, values in stats.dwell_components.items():
        if values:
            hours_values = [v / 60 for v in values]
            stats_table[component] = {
                'Mean': np.mean(hours_values),
                'Median': np.median(hours_values),
                'Min': np.min(hours_values),
                'Max': np.max(hours_values),
                'Std Dev': np.std(hours_values),
                'Count': len(hours_values)
            }
        else:
            stats_table[component] = {'Mean': 0, 'Median': 0, 'Min': 0, 'Max': 0, 'Std Dev': 0, 'Count': 0}
    stats_df = pd.DataFrame(stats_table).T
    # Adjust the index names if necessary
    stats_df.index = ['Ship Waiting (Schedule Delay)', 'Berth Queue Time', 'Unloading Process', 
                      'Yard Storage Time', 'Stacking Retrieval', 'Inland Transport Wait']
    st.dataframe(stats_df.style.format("{:.2f}"))

def render_train_departures(train_departure_records):
    st.markdown("## Train Departures")
    if train_departure_records:
        df = pd.DataFrame(train_departure_records)
        st.dataframe(df)
    else:
        st.write("No train departures recorded.")

def render_train_waiting_chart(train_waiting_data):
    st.markdown("## Train Waiting Containers Over Time")
    if train_waiting_data:
        df = pd.DataFrame(train_waiting_data)
        # Use the correct column name for train waiting data. Adjust "train_waiting" if needed.
        fig = px.line(df, x="time", y="train_waiting", title="Train Waiting Containers Over Time")
        st.plotly_chart(fig)
    else:
        st.write("No train waiting data recorded.")

def render_truck_waiting_chart(truck_waiting_data):
    st.markdown("## Truck Waiting Containers Over Time")
    if truck_waiting_data:
        df = pd.DataFrame(truck_waiting_data)
        # Use the correct column name from your data: "truck_waiting" (instead of "waiting").
        fig = px.line(df, x="time", y="truck_waiting", title="Truck Waiting Containers Over Time")
        st.plotly_chart(fig)
    else:
        st.write("No truck waiting data recorded.")

def render_yard_utilization_chart(stats, ship_arrivals):
    st.markdown("## Yard Container Count Over Time")
    yard_data = []
    # Loop over the two container types and two modalities.
    for container_type in ['dry', 'reefer']:
        for modal in ['truck', 'train']:
            # Now the keys in stats.yard_utilization[...] are minutes.
            for minute, count in sorted(stats.yard_utilization[container_type][modal].items()):
                yard_data.append({
                    'minute': minute,
                    'container_type': container_type.capitalize(),
                    'modal': modal.capitalize(),
                    'count': count
                })
    if yard_data:
        yard_df = pd.DataFrame(yard_data)
        # Total yard count over time by summing across container types and modalities.
        fig_yard_total = px.line(
            yard_df.groupby('minute')['count'].sum().reset_index(),
            x='minute',
            y='count',
            title='Total Containers in Yard Over Time',
            labels={'minute': 'Minute', 'count': 'Container Count'}
        )

        # Annotate with ship arrival events.
        if hasattr(stats, 'sim_start_time') and ship_arrivals:
            arrival_minutes = {}
            for ship in ship_arrivals:
                # Use actual_arrival if available; otherwise use expected_arrival.
                arrival_minute = int(ship["actual_arrival"]) if "actual_arrival" in ship else int(ship["expected_arrival"])
                arrival_minutes.setdefault(arrival_minute, []).append(ship.get("name", f"Ship {len(arrival_minutes)+1}"))
            y_max = yard_df.groupby('minute')['count'].sum().max() if not yard_df.empty else 100
            for arrival_minute, ships in arrival_minutes.items():
                fig_yard_total.add_vline(
                    x=arrival_minute,
                    line_dash="dash",
                    line_color="red",
                    opacity=0.7
                )
                for i, ship_name in enumerate(ships):
                    y_position = random.uniform(0.1 * y_max, 0.9 * y_max)
                    fig_yard_total.add_annotation(
                        x=arrival_minute,
                        y=y_position,
                        text=ship_name,
                        showarrow=True,
                        arrowhead=1,
                        ax=-20,
                        ay=0,
                        yref="y",
                        textangle=90
                    )
        st.plotly_chart(fig_yard_total, use_container_width=True)
    else:
        st.write("No yard utilization data available.")

def render_truck_departures_chart(stats):
    st.markdown("## Truck Departures Per Hour")
    # Convert the gate_departures_by_hour dict to a list of dicts for plotting.
    data = [{'Hour': hour, 'Truck Departures': count} 
            for hour, count in sorted(stats.gate_departures_by_hour.items())]
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(
            df,
            x='Hour',
            y='Truck Departures',
            title="Truck Departures by Hour (Each Truck Carries Multiple Containers)",
            labels={'Hour': 'Hour', 'Truck Departures': 'Truck Departures (Trips)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No truck departure data available.")

def render_yard_containers_time_series(all_containers, sim_start_time=None):
    """
    Plot total containers in the yard over time with interactive Plotly buttons.
    This version distinguishes between dry and reefer containers as well as filtering
    by container origin and transportation mode.
    
    Filter options (each key is a label for the update menu):
      - "All": No filtering (all containers)
      - "Dry": Only dry containers
      - "Reefer": Only reefer containers
      - "From Vessel": Only containers that came from a vessel (all modes, all types)
      - "From Vessel - Dry": Only dry containers that came from a vessel
      - "From Vessel - Reefer": Only reefer containers that came from a vessel
      - "Not From Vessel": Only containers that did NOT come from a vessel
      - "Not From Vessel - Dry": Only dry containers not from a vessel
      - "Not From Vessel - Reefer": Only reefer containers not from a vessel
      - "Truck": Only containers transported by truck (all origins, all types)
      - "Truck - Dry": Only dry containers transported by truck
      - "Truck - Reefer": Only reefer containers transported by truck
      - "From Vessel - Truck": Only vessel containers with mode truck (all types)
      - "From Vessel - Truck - Dry": Only dry vessel containers with mode truck
      - "From Vessel - Truck - Reefer": Only reefer vessel containers with mode truck
      - "Not From Vessel - Truck": Only non-vessel containers with mode truck (all types)
      - "Not From Vessel - Truck - Dry": Only dry non-vessel containers with mode truck
      - "Not From Vessel - Truck - Reefer": Only reefer non-vessel containers with mode truck
      - "Train": Only containers transported by train (all origins, all types)
      - "Train - Dry": Only dry containers transported by train
      - "Train - Reefer": Only reefer containers transported by train
      - "From Vessel - Train": Only vessel containers with mode train (all types)
      - "From Vessel - Train - Dry": Only dry vessel containers with mode train
      - "From Vessel - Train - Reefer": Only reefer vessel containers with mode train
      - "Not From Vessel - Train": Only non-vessel containers with mode train (all types)
      - "Not From Vessel - Train - Dry": Only dry non-vessel containers with mode train
      - "Not From Vessel - Train - Reefer": Only reefer non-vessel containers with mode train
    """
    st.markdown("## Yard Containers Over Time (Interactive Filtering)")
    
    # Prepare data from container objects.
    data = []
    for container in all_containers:
        # Only consider containers that have both entry and departure times.
        if container.yard_entry_time is not None and container.departure_time is not None:
            data.append({
                "yard_entry": container.yard_entry_time,  # minutes from simulation start
                "departure": container.departure_time,      # minutes from simulation start
                "from_vessel": container.from_vessel,
                "modal": container.modal,                   # "truck" or "train"
                "type": container.type                      # "dry" or "reefer"
            })
    
    if not data:
        st.write("No container data available.")
        return

    df = pd.DataFrame(data)
    
    # Determine overall time span.
    min_time = int(df["yard_entry"].min())
    max_time = int(df["departure"].max())
    time_range = list(range(min_time, max_time + 1))
    
    # Define filter combinations.
    filter_options = {
        "All": ("All", "All", "All"),
        "Dry": ("All", "All", "dry"),
        "Reefer": ("All", "All", "reefer"),
        "From Vessel": ("From Vessel", "All", "All"),
        "From Vessel - Dry": ("From Vessel", "All", "dry"),
        "From Vessel - Reefer": ("From Vessel", "All", "reefer"),
        "Not From Vessel": ("Not From Vessel", "All", "All"),
        "Not From Vessel - Dry": ("Not From Vessel", "All", "dry"),
        "Not From Vessel - Reefer": ("Not From Vessel", "All", "reefer"),
        "Truck": ("All", "truck", "All"),
        "Truck - Dry": ("All", "truck", "dry"),
        "Truck - Reefer": ("All", "truck", "reefer"),
        "From Vessel - Truck": ("From Vessel", "truck", "All"),
        "From Vessel - Truck - Dry": ("From Vessel", "truck", "dry"),
        "From Vessel - Truck - Reefer": ("From Vessel", "truck", "reefer"),
        "Not From Vessel - Truck": ("Not From Vessel", "truck", "All"),
        "Not From Vessel - Truck - Dry": ("Not From Vessel", "truck", "dry"),
        "Not From Vessel - Truck - Reefer": ("Not From Vessel", "truck", "reefer"),
        "Train": ("All", "train", "All"),
        "Train - Dry": ("All", "train", "dry"),
        "Train - Reefer": ("All", "train", "reefer"),
        "From Vessel - Train": ("From Vessel", "train", "All"),
        "From Vessel - Train - Dry": ("From Vessel", "train", "dry"),
        "From Vessel - Train - Reefer": ("From Vessel", "train", "reefer"),
        "Not From Vessel - Train": ("Not From Vessel", "train", "All"),
        "Not From Vessel - Train - Dry": ("Not From Vessel", "train", "dry"),
        "Not From Vessel - Train - Reefer": ("Not From Vessel", "train", "reefer")
    }
    
    # Precompute aggregated container counts for each filter combination.
    agg_data = {}
    for label, (origin_filter, mode_filter, type_filter) in filter_options.items():
        temp = df.copy()
        if origin_filter != "All":
            if origin_filter == "From Vessel":
                temp = temp[temp["from_vessel"] == True]
            else:  # "Not From Vessel"
                temp = temp[temp["from_vessel"] == False]
        if mode_filter != "All":
            temp = temp[temp["modal"] == mode_filter]
        if type_filter != "All":
            temp = temp[temp["type"] == type_filter]
            
        counts = []
        for t in time_range:
            # Count a container as present if its entry time <= t < departure time.
            count = ((temp["yard_entry"] <= t) & (temp["departure"] > t)).sum()
            counts.append(count)
        agg_data[label] = counts

    # Prepare x-axis values.
    if sim_start_time:
        x_values = [sim_start_time + timedelta(minutes=t) for t in time_range]
        x_label = "Time"
    else:
        x_values = time_range
        x_label = "Minute"
    
    # Create initial trace (default: "All").
    default_label = "All"
    fig = px.line(x=x_values, y=agg_data[default_label],
                  labels={"x": x_label, "y": "Container Count"},
                  title="Total Containers in Yard Over Time")
    
    # Create update menu buttons for each filter option.
    buttons = []
    for label in filter_options.keys():
        button = dict(
            label=label,
            method="update",
            args=[{"y": [agg_data[label]]}]  # update the y-data of the trace
        )
        buttons.append(button)
    
    # Add the update menu to the figure layout.
    fig.update_layout(
        updatemenus=[{
            "buttons": buttons,
            "direction": "down",
            "showactive": True,
            "x": 1.05,
            "xanchor": "left",
            "y": 1,
            "yanchor": "top",
            "pad": {"r": 10, "t": 10}
        }]
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_dashboard(ship_arrivals, stats, containers):
    st.markdown("# Port Simulation Dashboard")
    render_yard_utilization_chart(stats, ship_arrivals)
    render_dwell_time_boxplot(stats)
    plot_dwell_time_waterfall(stats)
    plot_dwell_time_boxplot_components(stats)
    plot_dwell_time_statistics(stats)
    render_train_departures(stats.train_departure_records)
    render_train_waiting_chart(stats.train_waiting_over_time)
    render_truck_waiting_chart(stats.truck_waiting_over_time)
    render_ship_arrivals(ship_arrivals)
    render_resource_heatmap(stats)
    render_truck_departures_chart(stats)
    render_yard_containers_time_series(containers, stats.sim_start_time)