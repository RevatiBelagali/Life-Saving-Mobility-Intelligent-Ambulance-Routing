import streamlit as st
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

st.set_page_config(layout="wide")
st.title("🚑 Emergency Vehicle Simulation Dashboard")

# Load log files
log_dir = "logs"

def load_json(filename):
    path = os.path.join(log_dir, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

# Load data
alerts = load_json("v2v_alerts.json")  # Expecting list of counts per timestep
speeds = load_json("ambulance_speed.json")  # Expecting list of speeds per timestep
tl_controls = load_json("tl_overrides.json")  # Expecting list of counts per timestep
arrivals = load_json("arrival_summary.json")  # Expecting list or dict
clearance = load_json("clearance_times.json")  # Expecting list of stopped vehicle counts
travel_times = load_json("travel_times.json")  # (not used in your snippet yet)
heat_before = load_json("traffic_heatmap_before.json")  # (not used in your snippet yet)
heat_after = load_json("traffic_heatmap_after.json")  # (not used in your snippet yet)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Ambulance Speed Over Time")
    if speeds and isinstance(speeds, list) and len(speeds) > 0:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(speeds, label="Speed (m/s)", color='red')
        ax.set_xlabel("Timestep")
        ax.set_ylabel("Speed")
        ax.grid(True)
        st.pyplot(fig)
    else:
        st.warning("Speed data not found or invalid format.")

with col2:
    st.subheader("📡 Vehicles Alerted (V2V)")
    if alerts and isinstance(alerts, list) and len(alerts) > 0:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(alerts, label="Alerted Vehicles", color='blue')
        ax.set_xlabel("Timestep")
        ax.set_ylabel("Count")
        ax.grid(True)
        st.pyplot(fig)
    else:
        st.warning("Alert log not found or invalid format.")

st.subheader("🚦 Traffic Light Overrides")
if tl_controls and isinstance(tl_controls, list) and len(tl_controls) > 0:
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(tl_controls, label="Overridden TLs", color='orange')
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Overrides")
    ax.grid(True)
    st.pyplot(fig)
else:
    st.warning("Traffic light override log not found or invalid format.")

st.subheader("🛑 Stopped Vehicles (Clearance Time Proxy)")
if clearance and isinstance(clearance, list) and len(clearance) > 0:
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(clearance, label="Stopped Vehicles", color='purple')
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Count")
    ax.grid(True)
    st.pyplot(fig)
else:
    st.warning("Clearance time log not found or invalid format.")

st.subheader("🏥 Ambulance Arrival Summary")
if arrivals:
    # If arrivals is a list of dictionaries, show as dataframe or json
    if isinstance(arrivals, list):
        df_arrivals = pd.DataFrame(arrivals)
        st.success(f"{len(arrivals)} ambulances reached the hospital.")
        st.dataframe(df_arrivals)
    else:
        # If dictionary or other structure, pretty print JSON
        st.success("Arrival summary data loaded.")
        st.json(arrivals)
else:
    st.warning("Arrival summary log not found.")
