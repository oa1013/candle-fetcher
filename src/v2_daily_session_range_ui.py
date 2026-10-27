from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .v2_csv_discovery import discover_processed_csvs
from .v2_daily_session_range_integration import (
    run_daily_session_range_v2,
)
from .v2_daily_session_range_charts import (
    build_daily_range_chart,
    build_session_range_comparison_chart,
)


SESSION_LABELS = {
    "new_york": "New York",
    "london": "London",
    "asia": "Asia",
}

SESSION_EXPECTED_CANDLES = {
    "new_york": 200,
    "london": 180,
    "asia": 115,
}


def _dataset_label(item: dict) -> str:
    if item["filename"] == "2025_full_year.csv":
        return "All Sessions | 2025 Full Year"

    return f'{item["session"]} | {item["filename"]}'


def _session_summary_table(result: dict) -> pd.DataFrame:
    rows = []

    for key, label in SESSION_LABELS.items():
        summary = result["session_summaries"][key]

        rows.append({
            "Session": label,
            "Total Sessions": summary["total_sessions"],
            "Complete": summary["complete_sessions"],
            "Incomplete": summary["incomplete_sessions"],
            "Mean Range": summary["mean_range"],
            "Median Range": summary["median_range"],
            "Largest Range": summary["max_range"],
            "P10": summary["p10"],
            "P25": summary["p25"],
            "P50": summary["p50"],
            "P75": summary["p75"],
            "P90": summary["p90"],
        })

    return pd.DataFrame(rows)


def render_daily_session_range_v2() -> None:
    """
    Render the Daily Session Range Analyzer V2.

    Reuses existing statistical and data-quality engines.
    """

    # ------------------------------------------
    # Discover suitable historical datasets
    # ------------------------------------------

    datasets = [
        item
        for item in discover_processed_csvs()
        if item["session"] == "All Sessions"
    ]

    if not datasets:
        st.warning(
            "No All Sessions historical CSV files were found. "
            "A full-day dataset is needed to compare all "
            "three trading sessions."
        )
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
        "Analyse historical daily highs, lows and ranges, "
        "compare trading sessions and examine candle coverage."
    )

    selected_path = st.selectbox(
        "Historical dataset",
        options=paths,
        index=default_index,
        format_func=lambda path: _dataset_label(
            by_path[path]
        ),
        key="range_v2_dataset",
    )

    st.caption(
        "Daily ranges use UTC dates. Session ranges use "
        "their configured market timezones. "
        "Asia uses the validated 10:05 reference start."
    )

    # ------------------------------------------
    # Run analysis
    # ------------------------------------------

    if st.button(
        "Run Daily Session Range Analyzer",
        type="primary",
        use_container_width=True,
        key="range_v2_run",
    ):

        st.session_state["range_v2_last_result"] = None

        try:
            with st.spinner(
                "Analysing historical daily and session ranges..."
            ):
                result = run_daily_session_range_v2(
                    csv_path=selected_path
                )

            st.session_state["range_v2_last_result"] = result

        except Exception as exc:
            st.error(
                f"Daily Session Range analysis failed: {exc}"
            )

    result = st.session_state.get(
        "range_v2_last_result"
    )

    if result is None:
        st.info(
            "Select a historical dataset and run "
            "Daily Session Range Analyzer to begin."
        )
        return

    # ------------------------------------------
    # Summary
    # ------------------------------------------

    daily = result["daily_ranges"]
    summary = result["daily_summary"]

    st.success(
        f"Analysis completed: "
        f"{summary['total_days']:,} trading days and "
        f"{result['total_candles']:,} candles analysed."
    )

    st.caption(
        f"Latest analysis: {result['filename']} | UTC daily ranges"
    )

    if Path(selected_path).resolve() != Path(
        result["csv_path"]
    ).resolve():
        st.warning(
            "The selected dataset has changed. "
            "Run the analysis again to refresh these results."
        )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Trading days",
        f"{summary['total_days']:,}",
    )

    m2.metric(
        "Average daily range",
        f"{summary['mean_range']:,.2f} pts",
    )

    m3.metric(
        "Largest daily range",
        f"{summary['largest_range']:,.2f} pts",
    )

    m4.metric(
        "Reference-coverage days",
        f"{summary['reference_days']:,}",
    )

    largest_day = daily.loc[
        daily["range_points"].idxmax()
    ]

    st.caption(
        f"Largest daily range: {largest_day['trading_date']} "
        f"| High {float(largest_day['high']):,.2f} "
        f"| Low {float(largest_day['low']):,.2f} "
        f"| {int(largest_day['candle_count']):,} candles"
    )

    if (
        summary["reduced_days"]
        or summary["above_reference_days"]
    ):
        st.info(
            f"Daily coverage: {summary['reference_days']} "
            f"reference-coverage days, "
            f"{summary['reduced_days']} reduced-coverage days "
            f"and {summary['above_reference_days']} "
            f"above-reference days. The daily reference is "
            f"{result['daily_reference_candles']:,} candles."
        )

    # ------------------------------------------
    # Tabs
    # ------------------------------------------

    graph_tab, daily_tab, session_tab, download_tab = st.tabs(
        [
            "Interactive graphs",
            "Daily ranges",
            "Session ranges",
            "Downloads",
        ]
    )

    # ------------------------------------------
    # Interactive graphs
    # ------------------------------------------

    with graph_tab:

        try:
            daily_fig = build_daily_range_chart(result)

            st.plotly_chart(
                daily_fig,
                use_container_width=True,
                config={"displaylogo": False},
                key="range_v2_daily_chart",
            )

        except Exception as exc:
            st.error(
                f"Unable to display daily range graph: {exc}"
            )

        try:
            session_fig = (
                build_session_range_comparison_chart(result)
            )

            st.plotly_chart(
                session_fig,
                use_container_width=True,
                config={"displaylogo": False},
                key="range_v2_session_chart",
            )

        except Exception as exc:
            st.error(
                f"Unable to display session comparison: {exc}"
            )

        st.caption(
            "Session distribution graphs include only complete "
            "sessions. Reduced daily coverage does not "
            "automatically indicate a data error."
        )

    # ------------------------------------------
    # Daily ranges and coverage
    # ------------------------------------------

    with daily_tab:

        st.markdown("#### Historical daily highs and lows")

        st.dataframe(
            daily,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Coverage is classified against the 1,365-candle "
            "daily reference, including legitimate shortened days."
        )

    # ------------------------------------------
    # Session ranges and quality
    # ------------------------------------------

    with session_tab:

        st.markdown("#### Session range summary")

        summary_table = _session_summary_table(result)

        st.dataframe(
            summary_table,
            use_container_width=True,
            hide_index=True,
        )

        selected_session = st.selectbox(
            "Inspect trading session",
            options=list(SESSION_LABELS),
            format_func=lambda key: SESSION_LABELS[key],
            key="range_v2_inspect_session",
        )

        session_data = result[
            "session_ranges"
        ][selected_session]

        session_stats = result[
            "session_summaries"
        ][selected_session]

        st.caption(
            f"Expected candles per session: "
            f"{SESSION_EXPECTED_CANDLES[selected_session]} "
            f"| Complete: {session_stats['complete_sessions']} "
            f"| Incomplete: {session_stats['incomplete_sessions']}"
        )

        st.dataframe(
            session_data,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Session statistics and percentiles above use "
            "complete sessions only. The detailed table "
            "also includes incomplete sessions for review."
        )

    # ------------------------------------------
    # Downloads
    # ------------------------------------------

    with download_tab:

        st.markdown("#### CSV exports")

        st.download_button(
            "Download daily ranges (CSV)",
            data=daily.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="daily_historical_ranges.csv",
            mime="text/csv",
            key="range_v2_daily_csv",
        )

        summary_table = _session_summary_table(result)

        st.download_button(
            "Download session summary (CSV)",
            data=summary_table.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="session_range_summary.csv",
            mime="text/csv",
            key="range_v2_summary_csv",
        )

        for key, label in SESSION_LABELS.items():

            session_data = result["session_ranges"][key]

            st.download_button(
                f"Download {label} ranges (CSV)",
                data=session_data.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name=f"{key}_historical_ranges.csv",
                mime="text/csv",
                key=f"range_v2_{key}_csv",
            )

        st.markdown("#### Chart exports")

        chart_exports = [
            (
                "Daily ranges",
                build_daily_range_chart,
                "daily_historical_ranges.png",
                "range_v2_daily_png",
            ),
            (
                "Session comparison",
                build_session_range_comparison_chart,
                "session_range_comparison.png",
                "range_v2_session_png",
            ),
        ]

        for label, builder, filename, key in chart_exports:

            try:
                figure = builder(result)

                png = figure.to_image(
                    format="png",
                    width=1400,
                    height=700,
                    scale=2,
                )

                st.download_button(
                    f"Download {label} graph (PNG)",
                    data=png,
                    file_name=filename,
                    mime="image/png",
                    key=key,
                )

            except Exception as exc:
                st.error(
                    f"Unable to export {label} graph: {exc}"
                )
