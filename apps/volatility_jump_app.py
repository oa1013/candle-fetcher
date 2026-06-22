from __future__ import annotations

from pathlib import Path
import sys

import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.loaders import load_candle_csv
from src.theme_manager import (
    THEME_OPTIONS,
    apply_streamlit_theme,
    get_plotly_template,
)
from src.volatility_jumps import (
    detect_volatility_jumps,
    format_volatility_jump_table,
    get_top_volatility_jumps,
)
from src.volatility_jump_exports import (
    save_volatility_jump_result,
    print_exported_jump_paths,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Volatility Jump Runner",
    page_icon="📈",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("Analysis Controls")

theme = st.sidebar.selectbox(
    "Theme",
    THEME_OPTIONS,
    index=0,
)

apply_streamlit_theme(theme)

plotly_template = get_plotly_template(theme)


DEFAULT_CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "all_sessions"
    / "us100_cash_M1_all_sessions_2024_01_01_to_2024_12_31.csv"
)

csv_path_input = st.sidebar.text_input(
    "CSV file path",
    value=str(DEFAULT_CSV_PATH),
)

rolling_window = st.sidebar.number_input(
    "Rolling window",
    min_value=5,
    max_value=5000,
    value=100,
    step=5,
)

jump_threshold = st.sidebar.number_input(
    "Jump threshold",
    min_value=0.5,
    max_value=50.0,
    value=2.0,
    step=0.5,
)

top_n = st.sidebar.number_input(
    "Top N jumps",
    min_value=1,
    max_value=100,
    value=10,
    step=1,
)

analysis_name = st.sidebar.text_input(
    "Analysis name",
    value="volatility_jump_analysis",
)

run_analysis = st.sidebar.button(
    "Run Analysis",
    type="primary",
)

save_results = st.sidebar.checkbox(
    "Save results",
    value=False,
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Volatility Jump Runner")

st.caption(
    "Detect volatility spikes, review jump tables, and prepare for CSV comparison/news matching."
)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

if not run_analysis:
    st.info("Choose a CSV file and click **Run Analysis** to begin.")
    st.stop()


csv_path = Path(csv_path_input)

if not csv_path.is_absolute():
    csv_path = PROJECT_ROOT / csv_path

if not csv_path.exists():
    st.error(f"CSV file was not found: {csv_path}")
    st.stop()


with st.spinner("Loading candles and detecting volatility jumps..."):
    raw_df = load_candle_csv(csv_path)

    scored_df = detect_volatility_jumps(
        df=raw_df,
        rolling_window=int(rolling_window),
        threshold=float(jump_threshold),
    )

    top_jumps = get_top_volatility_jumps(
        df=raw_df,
        rolling_window=int(rolling_window),
        threshold=float(jump_threshold),
        top_n=int(top_n),
    )


total_rows = len(scored_df)
total_jumps = int(scored_df["is_jump"].sum())

if top_jumps.empty:
    largest_jump_score = 0.0
    average_jump_score = 0.0
else:
    largest_jump_score = float(top_jumps["jump_score"].max())
    average_jump_score = float(top_jumps["jump_score"].mean())


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    label="Total rows",
    value=f"{total_rows:,}",
)

col2.metric(
    label="Detected jumps",
    value=f"{total_jumps:,}",
)

col3.metric(
    label="Largest jump score",
    value=f"{largest_jump_score:.2f}",
)

col4.metric(
    label="Avg top jump score",
    value=f"{average_jump_score:.2f}",
)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

st.subheader("Price chart with detected jumps")

jump_points = scored_df[scored_df["is_jump"]].copy()

price_fig = go.Figure()

price_fig.add_trace(
    go.Scatter(
        x=scored_df["datetime"],
        y=scored_df["close"],
        mode="lines",
        name="Close price",
    )
)

if not jump_points.empty:
    price_fig.add_trace(
        go.Scatter(
            x=jump_points["datetime"],
            y=jump_points["close"],
            mode="markers",
            name="Detected jumps",
            marker=dict(size=7),
        )
    )

price_fig.update_layout(
    template=plotly_template,
    height=450,
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis_title="Datetime",
    yaxis_title="Close price",
)

st.plotly_chart(
    price_fig,
    use_container_width=True,
)


st.subheader("Rolling volatility and jump score")

jump_score_fig = go.Figure()

jump_score_fig.add_trace(
    go.Scatter(
        x=scored_df["datetime"],
        y=scored_df["jump_score"],
        mode="lines",
        name="Jump score",
    )
)

jump_score_fig.add_hline(
    y=float(jump_threshold),
    line_dash="dash",
    annotation_text=f"Threshold: {jump_threshold}",
)

jump_score_fig.update_layout(
    template=plotly_template,
    height=350,
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis_title="Datetime",
    yaxis_title="Jump score",
)

st.plotly_chart(
    jump_score_fig,
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

st.subheader("Top volatility jumps")

friendly_jumps = format_volatility_jump_table(top_jumps)

st.dataframe(
    friendly_jumps,
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

if save_results:
    export_paths = save_volatility_jump_result(
        jump_df=top_jumps,
        analysis_name=analysis_name,
        include_timestamp=True,
    )

    st.success("Results saved.")

    st.write(export_paths)