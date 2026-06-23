from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.theme_manager import (
    THEME_OPTIONS,
    apply_streamlit_theme,
)

from src.regime_period_filter import (
    find_period_regimes_from_csv,
    format_period_regime_table,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Period Regime Finder",
    page_icon="📆",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("Period Regime Settings")

theme = st.sidebar.selectbox(
    "Theme",
    THEME_OPTIONS,
    index=0,
)

apply_streamlit_theme(theme)


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

period = st.sidebar.selectbox(
    "Period type",
    [
        "year",
        "month",
        "week",
        "day",
    ],
    index=1,
)

regime = st.sidebar.selectbox(
    "Regime type",
    [
        "calm",
        "volatile",
    ],
    index=0,
)

top_n = st.sidebar.number_input(
    "Top N periods",
    min_value=1,
    max_value=100,
    value=10,
    step=1,
)

run_analysis = st.sidebar.button(
    "Run Analysis",
    type="primary",
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Period Regime Finder")

st.caption(
    "Find the calmest or most volatile year, month, week, or day from a candle CSV."
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


with st.spinner("Finding period regimes..."):
    result = find_period_regimes_from_csv(
        csv_path=csv_path,
        period=period,
        regime=regime,
        top_n=int(top_n),
    )

friendly_table = format_period_regime_table(result)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

st.subheader("Result summary")

if friendly_table.empty:
    st.warning("No period regime results were found.")
    st.stop()

best_period = friendly_table.iloc[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Best period", str(best_period["Period"]))
col2.metric("Regime", str(best_period["Regime Label"]))
col3.metric("Volatility score", str(best_period["Volatility Score"]))
col4.metric("Rows", f"{int(best_period['Rows']):,}")


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

st.subheader("Ranked period regimes")

st.dataframe(
    friendly_table,
    use_container_width=True,
)