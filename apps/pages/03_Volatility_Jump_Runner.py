from __future__ import annotations

from pathlib import Path
import sys

import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.loaders import load_candle_csv

from src.theme_manager import (
    apply_streamlit_theme,
    get_plotly_template,
    render_theme_selector,
)

from src.volatility_jumps import (
    detect_volatility_jumps,
    format_volatility_jump_table,
    get_top_volatility_jumps,
)

from src.dashboard_ui import (
    load_css,
    render_dataframe_download_button,
    render_footer_note,
    render_page_header,
)

from src.volatility_jump_exports import save_volatility_jump_result

from src.volatility_jump_comparison import (
    compare_jump_profiles,
    format_jump_profile_comparison,
)

from src.news_matcher import (
    match_news_to_jumps_from_csv,
    format_news_matches_table,
)


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Volatility Jump Runner",
    page_icon="📈",
    layout="wide",
)

load_css(PROJECT_ROOT / "apps" / "assets" / "app_styles.css")


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("Volatility Jump Settings")

theme = render_theme_selector()
apply_streamlit_theme(theme)
plotly_template = get_plotly_template(theme)


DEFAULT_CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "all_sessions"
    / "us100_cash_M1_all_sessions_2024_01_01_to_2024_12_31.csv"
)

DEFAULT_COMPARE_CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "new_york"
    / "us100_cash_M1_new_york_2021_01_01_to_2021_12_31.csv"
)

DEFAULT_NEWS_PATH = PROJECT_ROOT / "data" / "news" / "market_news_events.csv"


csv_path_input = st.sidebar.text_input(
    "CSV file path",
    value=str(DEFAULT_CSV_PATH),
)

compare_csvs = st.sidebar.checkbox(
    "Compare with another CSV",
    value=False,
)

compare_csv_path_input = st.sidebar.text_input(
    "Comparison CSV path",
    value=str(DEFAULT_COMPARE_CSV_PATH),
    disabled=not compare_csvs,
)

show_related_news = st.sidebar.checkbox(
    "Show related news/events",
    value=False,
)

news_path_input = st.sidebar.text_input(
    "News/events CSV path",
    value=str(DEFAULT_NEWS_PATH),
    disabled=not show_related_news,
)

news_window_minutes = st.sidebar.number_input(
    "News match window minutes",
    min_value=5,
    max_value=1440,
    value=30,
    step=5,
    disabled=not show_related_news,
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

save_results = st.sidebar.checkbox(
    "Save results",
    value=False,
)

run_analysis = st.sidebar.button(
    "Run Analysis",
    type="primary",
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

render_page_header(
    title="Volatility Jump Runner",
    subtitle="Detect volatility spikes, compare CSVs, and match nearby news or events.",
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


compare_csv_path = Path(compare_csv_path_input)

if not compare_csv_path.is_absolute():
    compare_csv_path = PROJECT_ROOT / compare_csv_path

if compare_csvs and not compare_csv_path.exists():
    st.error(f"Comparison CSV file was not found: {compare_csv_path}")
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

col1.metric("Total rows", f"{total_rows:,}")
col2.metric("Detected jumps", f"{total_jumps:,}")
col3.metric("Largest jump score", f"{largest_jump_score:.2f}")
col4.metric("Avg top jump score", f"{average_jump_score:.2f}")


# ---------------------------------------------------------------------------
# Price chart
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

st.plotly_chart(price_fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Jump score chart
# ---------------------------------------------------------------------------

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

st.plotly_chart(jump_score_fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Top jumps table
# ---------------------------------------------------------------------------

st.subheader("Top volatility jumps")

friendly_jumps = format_volatility_jump_table(top_jumps)

st.dataframe(
    friendly_jumps,
    use_container_width=True,
)

render_dataframe_download_button(
    df=friendly_jumps,
    filename=f"{analysis_name}_top_volatility_jumps.csv",
    label="Download top jumps CSV",
    key="download_top_jumps",
)


# ---------------------------------------------------------------------------
# CSV comparison
# ---------------------------------------------------------------------------

if compare_csvs:
    st.subheader("CSV jump comparison")

    with st.spinner("Comparing CSV jump profiles..."):
        comparison_df = compare_jump_profiles(
            csv_paths=[
                csv_path,
                compare_csv_path,
            ],
            labels=[
                csv_path.stem,
                compare_csv_path.stem,
            ],
            rolling_window=int(rolling_window),
            threshold=float(jump_threshold),
        )

    friendly_comparison = format_jump_profile_comparison(comparison_df)

    st.dataframe(
        friendly_comparison,
        use_container_width=True,
    )

    render_dataframe_download_button(
        df=friendly_comparison,
        filename=f"{analysis_name}_jump_comparison.csv",
        label="Download jump comparison CSV",
        key="download_jump_comparison",
    )

    comparison_metric = st.selectbox(
        "Comparison chart metric",
        [
            "total_jumps",
            "jump_rate_pct",
            "largest_jump_score",
            "avg_jump_score",
        ],
        format_func={
            "total_jumps": "Total jumps",
            "jump_rate_pct": "Jump rate %",
            "largest_jump_score": "Largest jump score",
            "avg_jump_score": "Average jump score",
        }.get,
    )

    comparison_chart = go.Figure()

    comparison_chart.add_trace(
        go.Bar(
            x=comparison_df["label"],
            y=comparison_df[comparison_metric],
            name=comparison_metric,
        )
    )

    comparison_chart.update_layout(
        template=plotly_template,
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="CSV",
        yaxis_title=comparison_metric,
    )

    st.plotly_chart(
        comparison_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Related news/events
# ---------------------------------------------------------------------------

if show_related_news:
    st.subheader("Related news / events")

    news_path = Path(news_path_input)

    if not news_path.is_absolute():
        news_path = PROJECT_ROOT / news_path

    if not news_path.exists():
        st.warning(
            f"News/events CSV was not found: {news_path}. "
            "Create this file later to match news to volatility jumps."
        )

    else:
        news_matches = match_news_to_jumps_from_csv(
            jump_df=top_jumps,
            news_path=news_path,
            window_minutes=int(news_window_minutes),
        )

        friendly_news_matches = format_news_matches_table(news_matches)

        if friendly_news_matches.empty:
            st.info(
                "No related news/events were found near the selected volatility jumps."
            )
        else:
            st.caption(
                "These events happened near volatility jumps. This does not prove causation."
            )

            st.dataframe(
                friendly_news_matches,
                use_container_width=True,
            )

            render_dataframe_download_button(
                df=friendly_news_matches,
                filename=f"{analysis_name}_news_matches.csv",
                label="Download news matches CSV",
                key="download_news_matches",
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


render_footer_note(
    "Nearby news/events do not prove causation. Use this page for research and review only."
)