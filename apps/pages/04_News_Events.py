from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.theme_manager import (
    apply_streamlit_theme,
    render_theme_selector,
)

from src.dashboard_ui import (
    load_css,
    render_dataframe_download_button,
    render_footer_note,
    render_page_header,
    render_status_card,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="News / Events",
    page_icon="📰",
    layout="wide",
)

load_css(PROJECT_ROOT / "apps" / "assets" / "app_styles.css")


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("News / Events Settings")

theme = render_theme_selector()
apply_streamlit_theme(theme)


DEFAULT_NEWS_PATH = PROJECT_ROOT / "data" / "news" / "market_news_events.csv"
EXAMPLE_NEWS_PATH = PROJECT_ROOT / "data" / "news" / "market_news_events.example.csv"

news_path_input = st.sidebar.text_input(
    "News/events CSV path",
    value=str(DEFAULT_NEWS_PATH),
)

use_example_if_missing = st.sidebar.checkbox(
    "Use example file if real file is missing",
    value=True,
)

uploaded_file = st.sidebar.file_uploader(
    "Upload news/events CSV",
    type=["csv"],
)

save_uploaded_file = st.sidebar.button(
    "Save uploaded CSV locally",
    type="primary",
    disabled=uploaded_file is None,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_path(path_text: str) -> Path:
    path = Path(path_text)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path


def load_news_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def filter_dataframe_by_search(df: pd.DataFrame, search_text: str) -> pd.DataFrame:
    if not search_text:
        return df

    search_text = search_text.lower()

    searchable = df.astype(str).apply(
        lambda row: row.str.lower().str.contains(search_text, na=False).any(),
        axis=1,
    )

    return df[searchable].copy()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

render_page_header(
    title="News / Events",
    subtitle=(
        "View, upload, and download market news or economic event CSV files "
        "used for matching against volatility jumps."
    ),
)


# ---------------------------------------------------------------------------
# Save uploaded CSV
# ---------------------------------------------------------------------------

news_path = resolve_path(news_path_input)

if uploaded_file is not None and save_uploaded_file:
    news_path.parent.mkdir(parents=True, exist_ok=True)

    uploaded_df = pd.read_csv(uploaded_file)
    uploaded_df.to_csv(news_path, index=False)

    st.success(f"Uploaded CSV saved to: {news_path}")


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

loaded_path = news_path
used_example = False

if not loaded_path.exists() and use_example_if_missing and EXAMPLE_NEWS_PATH.exists():
    loaded_path = EXAMPLE_NEWS_PATH
    used_example = True


if not loaded_path.exists():
    st.warning(
        "No news/events CSV was found. Upload one from the sidebar, or create "
        "`data/news/market_news_events.csv`."
    )

    render_footer_note(
        "News/events are used for research context only. Nearby events do not prove causation."
    )

    st.stop()


news_df = load_news_csv(loaded_path)


# ---------------------------------------------------------------------------
# Status cards
# ---------------------------------------------------------------------------

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    render_status_card(
        label="Loaded file",
        value="Example" if used_example else "Real CSV",
        note=str(loaded_path.relative_to(PROJECT_ROOT)),
    )

with status_col2:
    render_status_card(
        label="Rows",
        value=f"{len(news_df):,}",
        note="Total events loaded.",
    )

with status_col3:
    render_status_card(
        label="Columns",
        value=f"{len(news_df.columns):,}",
        note="Fields available in the file.",
    )


# ---------------------------------------------------------------------------
# Search / table
# ---------------------------------------------------------------------------

st.subheader("News / events table")

search_text = st.text_input(
    "Search events",
    value="",
    placeholder="Search by title, currency, impact, source, notes...",
)

filtered_df = filter_dataframe_by_search(news_df, search_text)

st.caption(
    f"Showing {len(filtered_df):,} of {len(news_df):,} rows."
)

st.dataframe(
    filtered_df,
    use_container_width=True,
)


render_dataframe_download_button(
    df=filtered_df,
    filename="news_events_filtered.csv",
    label="Download filtered news/events CSV",
    key="download_filtered_news_events",
)


# ---------------------------------------------------------------------------
# Column guidance
# ---------------------------------------------------------------------------

st.subheader("Recommended CSV columns")

st.write(
    "For best results with volatility jump matching, use columns like: "
    "`datetime`, `event`, `currency`, `impact`, `source`, and `notes`."
)

st.info(
    "The Volatility Jump Runner can match nearby events to detected jumps, "
    "but nearby timing does not prove the event caused the move."
)


render_footer_note(
    "News/events are used for research context only. Nearby events do not prove causation."
)