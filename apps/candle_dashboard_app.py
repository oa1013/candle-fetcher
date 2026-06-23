from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.theme_manager import (
    THEME_OPTIONS,
    apply_streamlit_theme,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Candle Fetcher Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Dashboard Settings")

theme = st.sidebar.selectbox(
    "Theme",
    THEME_OPTIONS,
    index=0,
)

apply_streamlit_theme(theme)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

st.title("Candle Fetcher Dashboard")

st.caption(
    "MT5 / FTMO candle research dashboard for session filtering, CSV comparison, "
    "regime analysis, volatility jumps, and news/event matching."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("CSV Comparison")
    st.write(
        "Compare processed CSV files and see similarity scores, regime labels, "
        "and volatility differences."
    )

with col2:
    st.subheader("Period Regime Finder")
    st.write(
        "Find the calmest or most volatile year, month, week, or day from candle data."
    )

with col3:
    st.subheader("Volatility Jump Runner")
    st.write(
        "Detect volatility jumps, compare CSVs, and match nearby news or events."
    )

st.divider()

st.info(
    "Use the pages in the sidebar to open each analysis tool. "
    "The notebooks will stay available for testing and development."
)