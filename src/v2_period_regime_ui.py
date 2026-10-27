from __future__ import annotations

from pathlib import Path

import streamlit as st

from .v2_csv_discovery import discover_processed_csvs
from .v2_period_regime_integration import run_period_regime_v2
from .v2_period_regime_charts import build_period_regime_ranking_chart


def _format_dataset(dataset: dict) -> str:
    """Display a concise, identifiable dataset name."""

    filename = dataset["filename"]
    session = dataset["session"]

    if filename == "2025_full_year.csv":
        return f"{session} | 2025 Full Year"

    # Reuse the existing session and filename metadata.
    return f"{session} | {filename}"


def render_period_regime_v2() -> None:
    """
    Render the Period Regime Finder V2 interface.

    All calculations use the existing regime engine.
    """

    datasets = discover_processed_csvs()

    if not datasets:
        st.warning(
            "No processed CSV files were found."
        )
        return

    by_path = {
        dataset["path"]: dataset
        for dataset in datasets
    }

    paths = list(by_path)

    # Prefer the full-year dataset for useful monthly analysis.
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
        "Find and rank the calmest or most volatile "
        "years, months, weeks and days."
    )

    # ------------------------------------------
    # Dataset selection
    # ------------------------------------------

    selected_path = st.selectbox(
        "Historical dataset",
        options=paths,
        index=default_index,
        format_func=lambda path: _format_dataset(
            by_path[path]
        ),
        key="period_v2_dataset",
    )

    # ------------------------------------------
    # Analysis configuration
    # ------------------------------------------

    col_period, col_regime, col_top = st.columns(3)

    with col_period:
        period = st.selectbox(
            "Period type",
            options=["year", "month", "week", "day"],
            index=1,
            key="period_v2_period",
        )

    with col_regime:
        regime = st.selectbox(
            "Ranking direction",
            options=["calm", "volatile"],
            format_func=lambda value: (
                "Calmest periods"
                if value == "calm"
                else "Most volatile periods"
            ),
            index=1,
            key="period_v2_regime",
        )

    with col_top:
        top_n = st.number_input(
            "Top N periods",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            key="period_v2_top_n",
        )

    st.caption(
        "Volatility scores are relative to the periods "
        "within the selected dataset, not probabilities."
    )

    # ------------------------------------------
    # Execute analysis
    # ------------------------------------------

    if st.button(
        "Run Period Regime Finder",
        type="primary",
        use_container_width=True,
        key="period_v2_run",
    ):

        try:
            with st.spinner(
                "Analysing historical market periods..."
            ):
                result = run_period_regime_v2(
                    csv_path=selected_path,
                    period=period,
                    regime=regime,
                    top_n=int(top_n),
                )

            st.session_state["period_v2_last_result"] = result

        except Exception as exc:
            st.session_state["period_v2_last_result"] = None
            st.error(
                f"Period Regime Finder failed: {exc}"
            )

    # ------------------------------------------
    # Show latest completed analysis
    # ------------------------------------------

    result = st.session_state.get(
        "period_v2_last_result"
    )

    if result is None:
        st.info(
            "Choose a historical dataset and run "
            "Period Regime Finder to begin."
        )
        return

    period_count = result["periods_returned"]
    period_word = "period" if period_count == 1 else "periods"

    st.success(
        f"Analysis completed: "
        f"{period_count} {period_word} processed."
    )

    st.caption(
        f"Latest analysis: {result['filename']} "
        f"| {result['period']} "
        f"| {result['regime']}"
    )

    raw_results = result["raw_results"]
    formatted = result["formatted_results"]

    best = raw_results.iloc[0]

    # A one-period baseline cannot support a relative ranking.
    single_baseline = (
        str(best["regime"]) == "single_file_baseline"
    )

    if single_baseline:
        st.warning(
            "Only one period is available in this dataset. "
            "A meaningful relative volatility ranking requires "
            "at least two periods."
        )

        # Preserve raw engine results; clarify displayed/exported ranking.
        formatted = formatted.copy()
        formatted["Volatility Score"] = float("nan")
        formatted["Regime Label"] = "Not comparable"

    # ------------------------------------------
    # Summary metrics
    # ------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Highest-ranked period",
        str(best["period_label"]),
    )

    col2.metric(
        "Regime classification",
        "Not comparable"
        if single_baseline
        else str(best["regime"]).capitalize(),
    )

    col3.metric(
        "Volatility score",
        "N/A"
        if single_baseline
        else f"{float(best['volatility_score']):.1f}",
    )

    col4.metric(
        "Candles analysed",
        f"{int(best['rows']):,}",
    )

    # ------------------------------------------
    # Charts, tables and downloads
    # ------------------------------------------

    chart_tab, table_tab, download_tab = st.tabs(
        [
            "Interactive graph",
            "Ranked results",
            "Downloads",
        ]
    )

    with chart_tab:

        if single_baseline:
            st.info(
                "Ranking graph unavailable: only one period "
                "exists in this dataset."
            )
        else:

            try:
                fig = build_period_regime_ranking_chart(
                    result
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displaylogo": False},
                    key="period_v2_ranking_plot",
                )

                png_bytes = fig.to_image(
                    format="png",
                    width=1400,
                    height=800,
                    scale=2,
                )

                st.download_button(
                    "Download ranking chart (PNG)",
                    data=png_bytes,
                    file_name=(
                        f"period_regime_{result['period']}"
                        f"_{result['regime']}.png"
                    ),
                    mime="image/png",
                    key="period_v2_png_download",
                )

            except Exception as exc:
                st.error(
                    f"Unable to display or export chart: {exc}"
                )

            st.caption(
                "Chart rankings use the original historical "
                "regime calculations."
            )

    with table_tab:

        st.markdown("#### Ranked period regimes")

        st.dataframe(
            formatted,
            use_container_width=True,
            hide_index=True,
        )

    with download_tab:

        # Add interpretation metadata to exported metrics only.
        # Original engine results remain unchanged.
        export_metrics = raw_results.copy()

        export_metrics["relative_comparison_available"] = (
            not single_baseline
        )

        export_metrics["score_interpretation"] = (
            "Baseline only: no relative comparison possible"
            if single_baseline
            else "Relative volatility score within selected dataset"
        )

        st.download_button(
            "Download ranked results (CSV)",
            data=formatted.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name=(
                f"period_regime_{result['period']}"
                f"_{result['regime']}.csv"
            ),
            mime="text/csv",
            key="period_v2_csv_download",
        )

        st.download_button(
            "Download full metrics (CSV)",
            data=export_metrics.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name=(
                f"period_regime_{result['period']}"
                f"_{result['regime']}_full_metrics.csv"
            ),
            mime="text/csv",
            key="period_v2_metrics_download",
        )
