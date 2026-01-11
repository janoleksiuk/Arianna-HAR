from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st


def tail_jsonl(path: str, n: int) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        lines = deque(f, maxlen=n)
    out: List[Dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip malformed lines
            continue
    return out


st.set_page_config(page_title="Ontology HRI Trace", layout="wide")
st.title("Ontology-based HRI — Live Event Trace")

# -----------------------
# Sidebar controls
# -----------------------
st.sidebar.header("Settings")
trace_path = st.sidebar.text_input("trace.jsonl path", value="runs/trace.jsonl")
tail_n = st.sidebar.slider("Tail last N records", 100, 5000, 800, step=100)

st.sidebar.header("Refresh")
st.sidebar.button("Refresh now")

auto_refresh = st.sidebar.checkbox("Auto refresh (basic)", value=False)
refresh_seconds = st.sidebar.slider("Refresh every (seconds)", 1, 10, 2)

# Basic autorefresh without external dependencies:
# sleep -> rerun (works across Streamlit versions)
if auto_refresh:
    import time

    time.sleep(refresh_seconds)
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# -----------------------
# Load trace
# -----------------------
rows = tail_jsonl(trace_path, tail_n)
if not rows:
    st.info("No trace records yet. Run your main system to generate the trace file.")
    st.stop()

df = pd.DataFrame(rows)

# Normalize expected columns
for col in ["procedure", "human_id", "cycle_id", "seq", "kind", "name", "ts"]:
    if col not in df.columns:
        df[col] = None

df["time"] = pd.to_datetime(df["ts"], unit="s", errors="coerce")
df["procedure"] = df["procedure"].fillna("")
df["human_id"] = df["human_id"].fillna("")

df["label"] = df.apply(
    lambda r: f"{r['kind']}: {r['name']}" + (f" | {r['procedure']}" if r["procedure"] else ""),
    axis=1,
)

# -----------------------
# Filters
# -----------------------
st.sidebar.header("Filters")

kinds = sorted([k for k in df["kind"].dropna().unique().tolist() if k != ""])
events = sorted([e for e in df["name"].dropna().unique().tolist() if e != ""])
procs = sorted([p for p in df["procedure"].dropna().unique().tolist() if p != ""])
humans = sorted([h for h in df["human_id"].dropna().unique().tolist() if h != ""])

selected_kinds = st.sidebar.multiselect("kind", options=kinds, default=kinds)
selected_events = st.sidebar.multiselect("event name", options=events, default=events)
selected_procs = st.sidebar.multiselect("procedure", options=procs, default=procs)
selected_humans = st.sidebar.multiselect("human_id", options=humans, default=humans)

# cycle_id range filter (if available)
cycle_min = int(df["cycle_id"].dropna().min()) if df["cycle_id"].notna().any() else 0
cycle_max = int(df["cycle_id"].dropna().max()) if df["cycle_id"].notna().any() else 0
cycle_range = st.sidebar.slider(
    "cycle_id range",
    min_value=cycle_min,
    max_value=cycle_max,
    value=(max(cycle_min, cycle_max - 20), cycle_max),
)

mask = df["kind"].isin(selected_kinds) & df["name"].isin(selected_events)

if selected_procs:
    mask = mask & (df["procedure"].isin(selected_procs) | (df["procedure"] == ""))

if selected_humans:
    mask = mask & df["human_id"].isin(selected_humans)

if df["cycle_id"].notna().any():
    mask = mask & (df["cycle_id"] >= cycle_range[0]) & (df["cycle_id"] <= cycle_range[1])

df_f = df[mask].sort_values(["time", "seq"], na_position="last")

# -----------------------
# Layout
# -----------------------
col1, col2 = st.columns([1.25, 1.0], gap="large")

with col1:
    st.subheader("Scrolling trace table")
    show_cols = ["time", "cycle_id", "kind", "name", "procedure", "human_id"]
    if "payload" in df_f.columns:
        show_cols.append("payload")
    st.dataframe(df_f[show_cols], use_container_width=True, height=560)

with col2:
    st.subheader("Timeline view (Plotly)")
    fig = px.scatter(
        df_f,
        x="time",
        y="label",
        hover_data=["cycle_id", "kind", "name", "procedure", "human_id"],
    )
    fig.update_layout(height=560, yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Tip: use cycle_id range to isolate one PoseTick chain. Use filters to focus on specific events/procedures.")
