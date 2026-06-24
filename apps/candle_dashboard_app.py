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
    apply_streamlit_theme,
    render_theme_selector,
)

from src.dashboard_ui import (
    load_css,
    render_dashboard_card,
    render_footer_note,
    render_page_header,
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
# Styling
# ---------------------------------------------------------------------------

load_css(PROJECT_ROOT / "apps" / "assets" / "app_styles.css")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Dashboard Settings")

theme = render_theme_selector()
apply_streamlit_theme(theme)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

render_page_header(
    title="Candle Fetcher Dashboard",
    subtitle=(
        "MT5 / FTMO candle research dashboard for session filtering, "
        "CSV comparison, regime analysis, volatility jumps, and news/event matching."
    ),
)


col1, col2, col3 = st.columns(3)

with col1:
    render_dashboard_card(
        title="CSV Comparison",
        body=(
            "Compare processed CSV files and review similarity scores, "
            "regime labels, volatility differences, and pairwise comparisons."
        ),
    )

with col2:
    render_dashboard_card(
        title="Period Regime Finder",
        body=(
            "Find the calmest or most volatile year, month, week, or day "
            "from candle data using volatility metrics."
        ),
    )

with col3:
    render_dashboard_card(
        title="Volatility Jump Runner",
        body=(
            "Detect volatility spikes, compare jump profiles between CSVs, "
            "and match nearby news or market events."
        ),
    )


st.markdown("### Dashboard pages")

st.write(
    "Use the sidebar pages to open each analysis tool. "
    "The notebooks are still available as backup/testing runners."
)


render_footer_note(
    "Research dashboard only. This project does not place trades and is not financial advice."
)