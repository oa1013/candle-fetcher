from __future__ import annotations

from pathlib import Path

import streamlit as st

from .v2_csv_discovery import discover_processed_csvs
from .v2_volatility_jump_integration import run_volatility_jump_v2
from .v2_volatility_jump_charts import (
    build_top_volatility_jumps_chart,
    build_daily_jump_frequency_chart,
)


def _dataset_label(dataset: dict) -> str:
    """Display a readable dataset name."""

    if dataset["filename"] == "2025_full_year.csv":
        return f'{dataset["session"]} | 2025 Full Year'

    return f'{dataset["session"]} | {dataset["filename"]}'


def render_volatility_jump_v2() -> None:
    """Render the Candle Fetcher 2.0 Volatility Jump Runner."""

    datasets = discover_processed_csvs()

    if not datasets:
        st.warning("No processed CSV datasets were found.")
        return

    by_path = {
        item["path"]: item
        for item in datasets
    }

    paths = list(by_path)

    preferred = next(
        (
            path for path in paths
            if Path(path).name == "2025_full_year.csv"
        ),
        None,
    )

    default_index = (
        paths.index(preferred)
        if preferred is not None
        else 0
    )

    st.caption(
        "Detect unusual candle-range expansion, rank "
        "volatility jumps and analyse their daily frequency."
    )

    selected_path = st.selectbox(
        "Historical dataset",
        options=paths,
        index=default_index,
        format_func=lambda path: _dataset_label(by_path[path]),
        key="jump_v2_dataset",
    )

    # ------------------------------------------
    # Detection settings
    # ------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        rolling_window = st.number_input(
            "Rolling window (candles)",
            min_value=5,
            max_value=5000,
            value=100,
            step=5,
            key="jump_v2_window",
        )

    with col2:
        threshold = st.number_input(
            "Jump-score threshold",
            min_value=0.5,
            max_value=50.0,
            value=2.0,
            step=0.5,
            key="jump_v2_threshold",
        )

    with col3:
        top_n = st.number_input(
            "Top N jumps",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            key="jump_v2_top_n",
        )

    st.caption(
        "Jump scores measure unusual candle ranges relative "
        "to a preceding rolling baseline. They are not "
        "probabilities or percentage changes."
    )

    # ------------------------------------------
    # Execute analysis
    # ------------------------------------------

    if st.button(
        "Run Volatility Jump Analysis",
        type="primary",
        use_container_width=True,
        key="jump_v2_run",
    ):

        st.session_state["jump_v2_last_result"] = None

        try:
            with st.spinner(
                "Detecting volatility jumps in historical candles..."
            ):
                result = run_volatility_jump_v2(
                    csv_path=selected_path,
                    rolling_window=int(rolling_window),
                    threshold=float(threshold),
                    top_n=int(top_n),
                )

            st.session_state["jump_v2_last_result"] = result

        except Exception as exc:
            st.error(
                f"Volatility Jump analysis failed: {exc}"
            )

    result = st.session_state.get("jump_v2_last_result")

    if result is None:
        st.info(
            "Select a historical dataset and run the "
            "Volatility Jump analysis to begin."
        )
        return

    # ------------------------------------------
    # Completed analysis summary
    # ------------------------------------------

    st.success(
        f"Analysis completed: "
        f"{result['total_jumps']:,} volatility jumps detected."
    )

    st.caption(
        f"Latest analysis: {result['filename']} "
        f"| window {result['rolling_window']} "
        f"| threshold {result['threshold']:.1f}"
    )

    settings_changed = (
        str(Path(selected_path).resolve()) != result["csv_path"]
        or int(rolling_window) != result["rolling_window"]
        or float(threshold) != result["threshold"]
        or int(top_n) != result["top_n"]
    )

    if settings_changed:
        st.warning(
            "Settings have changed since the latest analysis. "
            "Run the analysis again to refresh these results."
        )

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Candles analysed",
        f"{result['total_candles']:,}",
    )

    metric2.metric(
        "Detected jumps",
        f"{result['total_jumps']:,}",
    )

    metric3.metric(
        "Jump frequency",
        f"{result['jump_rate_pct']:.2f}%",
    )

    largest = result["largest_jump_score"]

    metric4.metric(
        "Largest jump score",
        f"{largest:.2f}" if largest is not None else "N/A",
    )

    # ------------------------------------------
    # Results
    # ------------------------------------------

    graph_tab, jumps_tab, daily_tab, downloads_tab = st.tabs(
        [
            "Interactive graphs",
            "Top jumps",
            "Daily frequency",
            "Downloads",
        ]
    )

    top_jumps = result["top_jumps"]
    daily_counts = result["daily_counts"]

    # ------------------------------------------
    # Interactive graphs
    # ------------------------------------------

    with graph_tab:

        if top_jumps.empty:
            st.info(
                "No jumps met the selected threshold. "
                "Try a lower threshold to see ranked jumps."
            )
        else:
            try:
                rank_fig = build_top_volatility_jumps_chart(
                    result
                )

                st.plotly_chart(
                    rank_fig,
                    use_container_width=True,
                    config={"displaylogo": False},
                    key="jump_v2_ranking_plot",
                )

            except Exception as exc:
                st.error(f"Unable to display ranking chart: {exc}")

        try:
            daily_fig = build_daily_jump_frequency_chart(
                result
            )

            st.plotly_chart(
                daily_fig,
                use_container_width=True,
                config={"displaylogo": False},
                key="jump_v2_daily_plot",
            )

        except Exception as exc:
            st.error(f"Unable to display daily chart: {exc}")

        st.caption(
            "Daily frequency accounts for the number of "
            "available candles in each UTC trading day."
        )

    # ------------------------------------------
    # Ranked volatility jumps
    # ------------------------------------------

    with jumps_tab:

        st.markdown("#### Strongest detected jumps")

        if top_jumps.empty:
            st.info("No volatility jumps met the threshold.")
        else:
            st.dataframe(
                result["formatted_top_jumps"],
                use_container_width=True,
                hide_index=True,
            )

    # ------------------------------------------
    # Daily statistics
    # ------------------------------------------

    with daily_tab:

        st.markdown("#### Daily jump frequency")

        st.dataframe(
            daily_counts,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "A high jump rate on a reduced-coverage day "
            "should be interpreted with its candle count."
        )

    # ------------------------------------------
    # Downloads
    # ------------------------------------------

    with downloads_tab:

        st.download_button(
            "Download top jumps (CSV)",
            data=result["formatted_top_jumps"]
                .to_csv(index=False)
                .encode("utf-8-sig"),
            file_name="volatility_jump_top_results.csv",
            mime="text/csv",
            key="jump_v2_top_csv",
        )

        st.download_button(
            "Download daily frequency (CSV)",
            data=daily_counts
                .to_csv(index=False)
                .encode("utf-8-sig"),
            file_name="volatility_jump_daily_frequency.csv",
            mime="text/csv",
            key="jump_v2_daily_csv",
        )

        if not top_jumps.empty:
            try:
                rank_fig = build_top_volatility_jumps_chart(
                    result
                )

                rank_png = rank_fig.to_image(
                    format="png",
                    width=1400,
                    height=max(
                        800,
                        int(rank_fig.layout.height),
                    ),
                    scale=2,
                )

                st.download_button(
                    "Download jump ranking graph (PNG)",
                    data=rank_png,
                    file_name="volatility_jump_ranking.png",
                    mime="image/png",
                    key="jump_v2_ranking_png",
                )

            except Exception as exc:
                st.error(
                    f"Unable to export ranking graph: {exc}"
                )

        try:
            daily_fig = build_daily_jump_frequency_chart(
                result
            )

            daily_png = daily_fig.to_image(
                format="png",
                width=1400,
                height=700,
                scale=2,
            )

            st.download_button(
                "Download daily frequency graph (PNG)",
                data=daily_png,
                file_name="volatility_jump_daily_frequency.png",
                mime="image/png",
                key="jump_v2_daily_png",
            )

        except Exception as exc:
            st.error(
                f"Unable to export daily graph: {exc}"
            )
