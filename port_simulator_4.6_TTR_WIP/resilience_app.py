# resilience_app.py

import streamlit as st
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


from config import default_config
from simulation_processes import run_simulation

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Port Resilience Experiments",
    layout="wide"
)

st.title("🏗️ Port Resilience Experiment")

# ─── Simulation Base Settings ─────────────────────────────────
st.sidebar.markdown("## Simulation Base Settings")
berth_count    = st.sidebar.number_input(
    "Berth Count", min_value=1, value=default_config["berth_count"]
)
gate_count     = st.sidebar.number_input(
    "Gate Count", min_value=1, value=default_config["gate_count"]
)
simulation_dur = st.sidebar.number_input(
    "Simulation Duration (h)", min_value=1, value=default_config["simulation_duration"]
)
cranes_per_vsl = st.sidebar.number_input(
    "Cranes per Vessel", min_value=1, value=default_config["cranes_per_vessel"]
)
trains_per_day = st.sidebar.number_input(
    "Trains per Day", min_value=1, value=default_config["trains_per_day"]
)
train_capacity = st.sidebar.number_input(
    "Train Capacity", min_value=1, value=default_config["train_capacity"]
)

# build minimal base_config
base_config = {
    "berth_count":        berth_count,
    "gate_count":         gate_count,
    "simulation_duration": simulation_dur,
    "random_seed":        default_config["random_seed"],
    "cranes_per_vessel":  cranes_per_vsl,
    "trains_per_day":     trains_per_day,
    "train_capacity":     train_capacity,
    "container_types":    default_config["container_types"],
    "vessels":            default_config["vessels"],
}

# ─── Baseline Clearance (no shock) ────────────────────────────
_, base_metrics, _ = run_simulation(base_config)
occ_base = base_metrics["yard_occupancy"]
tz_baseline = next((t for t, occ in occ_base if occ == 0), None)

if tz_baseline is not None:
    st.sidebar.write(f"Baseline clear time (no shock): **{tz_baseline:.1f} h**")
else:
    st.sidebar.write("Baseline clear time (no shock): **N/A (yard never cleared)**")

# ─── Resilience Experiment Settings ───────────────────────────
st.sidebar.markdown("## Resilience Experiment")
runs             = st.sidebar.number_input(
    "Runs per disruption type",
    min_value=1,
    value=default_config["resilience"]["runs"]
)
disruption_types = st.sidebar.multiselect(
    "Disruption types",
    options=default_config["resilience"]["disruption_types"],
    default=default_config["resilience"]["disruption_types"]
)
# make sure shock only lands after first vessel arrival
first_arrival = min((v["day"] - 1) * 24 + v["hour"] for v in base_config["vessels"])
ws = st.sidebar.number_input(
    "Window start (h)",
    min_value=int(first_arrival),
    max_value=int(simulation_dur) - 1,
    value=max(default_config["resilience"]["window_start"], int(first_arrival))
)
we = st.sidebar.number_input(
    "Window end (h)",
    min_value=ws + 1,
    max_value=int(simulation_dur),
    value=min(default_config["resilience"]["window_end"], simulation_dur)
)
dur = st.sidebar.number_input(
    "Disruption duration (h)",
    min_value=0.1,
    max_value=float(simulation_dur),
    value=float(default_config["resilience"]["duration"]),
    step=0.1,
    format="%.1f"
)
thresh = st.sidebar.slider(
    "Recovery threshold (%)",
    min_value=0.0,
    max_value=1.0,
    value=default_config["resilience"]["threshold"],
    step=0.05
)

# ─── Run Resilience Experiments ────────────────────────────────
if st.sidebar.button("Run Resilience Experiments"):
    total = runs * len(disruption_types)
    pbar  = st.progress(0)
    recs  = []
    cnt   = 0

    for dtype in disruption_types:
        for run_id in range(runs):
            t0 = random.uniform(ws, we)
            cfg = base_config.copy()
            _, metrics, _ = run_simulation(
                cfg,
                disruption_type=dtype,
                disruption_t0=t0,
                disruption_duration=dur,
                recovery_threshold=thresh
            )
            res  = metrics["resilience"]
            tz   = res["time_to_zero"]
            delta = (tz - tz_baseline) if (tz is not None and tz_baseline is not None) else None

            recs.append({
                "disruption_type":    dtype,
                "run_id":             run_id,
                "t0":                 res["t0"],
                "TTR":                res["TTR"],
                "time_to_zero":       tz,
                "delta_time_to_zero": delta
            })
            cnt += 1
            pbar.progress(cnt / total)

    df = pd.DataFrame(recs)

    # ─── Debug: raw time_to_zero ────────────────────────────────
    st.write("### All Runs: time_to_zero per disruption")
    st.dataframe(df[["disruption_type","run_id","time_to_zero"]])

    # ─── Resilience Summary ────────────────────────────────────
    st.subheader("Resilience Summary (Impact on Clearing Time)")
    summary = (
        df
        .groupby("disruption_type")
        .agg(
            mean_TTR                = ("TTR", "mean"),
            mean_delta_time_to_zero = ("delta_time_to_zero", "mean"),
            n_impacted              = ("delta_time_to_zero", lambda x: x.notna().sum())
        )
        .reset_index()
    )
    st.table(summary)

    # ─── TTR Distribution ──────────────────────────────────────
    st.subheader("TTR Distribution by Disruption Type")
    fig1 = px.box(
        df, x="disruption_type", y="TTR",
        labels={"disruption_type":"Disruption","TTR":"Time to Recovery (h)"}
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ─── Δ Time-to-Zero Distribution ───────────────────────────
    st.subheader("Δ Time to Zero by Disruption Type")
    fig2 = px.box(
        df, x="disruption_type", y="delta_time_to_zero",
        labels={"delta_time_to_zero":"Δ Time to Zero (h)"}
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ─── Recovery Metric Plots ──────────────────────────────────
    st.subheader("Recovery Curves for All Runs by Disruption Type")

    for dtype in disruption_types:
        st.markdown(f"### {dtype}")
        fig = go.Figure()
        subset = df[df["disruption_type"] == dtype]

        for _, row in subset.iterrows():
            t0 = row["t0"]
            # rerun that exact scenario
            cfg = base_config.copy()
            _, metrics_r, _ = run_simulation(
                cfg,
                disruption_type=dtype,
                disruption_t0=t0,
                disruption_duration=dur,
                recovery_threshold=thresh
            )
            ts = pd.DataFrame(metrics_r["yard_occupancy"], columns=["Time","Occupancy"])

            fig.add_trace(
                go.Scatter(
                    x=ts["Time"],
                    y=ts["Occupancy"],
                    mode="lines",
                    name=f"run {int(row['run_id'])}",
                    opacity=0.3,
                    hoverinfo="none"
                )
            )

        fig.update_layout(
            title=f"Yard Occupancy Trajectories: {dtype}",
            xaxis_title="Time (h)",
            yaxis_title="Occupancy",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)