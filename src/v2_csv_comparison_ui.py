from __future__ import annotations

from hashlib import sha1
from pathlib import Path

import streamlit as st

from .v2_csv_discovery import discover_processed_csvs
from .v2_csv_comparison_integration import run_csv_comparison_v2
from .v2_comparison_charts import build_volatility_score_chart
from .v2_similarity_heatmap import build_metric_similarity_heatmap


def _dataset_display_label(dataset: dict) -> str:
    """Create a readable and distinguishable dataset label."""

    import re

    stem = Path(dataset["filename"]).stem
    session = dataset["session"]

    match = re.search(
        r"(\d{4}_\d{2}_\d{2})_to_(\d{4}_\d{2}_\d{2})",
        stem,
    )

    if match:
        start_date = match.group(1).replace("_", "-")
        end_date = match.group(2).replace("_", "-")

        date_label = (
            start_date
            if start_date == end_date
            else f"{start_date} to {end_date}"
        )

        run_id = (
            stem.rsplit("_v2_", 1)[-1][-8:]
            if "_v2_" in stem
            else stem[-8:]
        )

        return f"{session} | {date_label} | {run_id}"

    return f"{session} | {stem}"


def _default_label(dataset: dict) -> str:
    """Default chart label for a selected CSV dataset."""
    return _dataset_display_label(dataset)


def render_csv_comparison_v2() -> None:
    """Render comparison controls, graphs, tables, and exports."""

    datasets = discover_processed_csvs()

    if len(datasets) < 2:
        st.warning("At least two processed CSVs are required.")
        return

    by_path = {item["path"]: item for item in datasets}
    choices = list(by_path)

    # Select the newest NY and London exports by default.
    defaults = []

    for session in ("New York", "London"):
        match = next(
            (
                item["path"]
                for item in datasets
                if item["session"] == session
            ),
            None,
        )

        if match:
            defaults.append(match)

    if len(defaults) < 2:
        defaults = choices[:2]

    st.caption(
        f"{len(datasets)} processed CSV files available. "
        "Select at least two distinct datasets."
    )

    selected_paths = st.multiselect(
        "Datasets to compare",
        options=choices,
        default=defaults,
        format_func=lambda path: _dataset_display_label(by_path[path]),
        key="csv_v2_selected_paths",
    )

    # ------------------------------------------
    # Dataset display labels
    # ------------------------------------------

    labels = []

    if selected_paths:
        with st.expander("Dataset labels", expanded=False):

            st.caption(
                "Short labels make comparison graphs easier to read."
            )

            for path in selected_paths:

                dataset = by_path[path]

                key = (
                    "csv_v2_label_"
                    + sha1(path.encode("utf-8")).hexdigest()[:12]
                )

                label = st.text_input(
                    dataset["filename"],
                    value=_default_label(dataset),
                    key=key,
                )

                labels.append(label.strip())

    # ------------------------------------------
    # Comparison options
    # ------------------------------------------

    comparison_name = st.text_input(
        "Comparison name",
        value="candle_fetcher_v2_comparison",
        key="csv_v2_comparison_name",
    )

    save_results = st.checkbox(
        "Save report and CSV tables to the project",
        value=False,
        key="csv_v2_save_results",
    )

    include_timestamp = st.checkbox(
        "Include timestamp in saved filenames",
        value=True,
        disabled=not save_results,
        key="csv_v2_timestamp",
    )

    # ------------------------------------------
    # Validate inputs
    # ------------------------------------------

    configuration_valid = (
        len(selected_paths) >= 2
        and len(set(selected_paths)) == len(selected_paths)
        and len(labels) == len(selected_paths)
        and all(labels)
        and len(set(labels)) == len(labels)
        and bool(comparison_name.strip())
    )

    if selected_paths and len(labels) != len(set(labels)):
        st.error("Dataset labels must be unique.")

    elif any(not label for label in labels):
        st.error("Dataset labels cannot be empty.")

    # ------------------------------------------
    # Execute comparison
    # ------------------------------------------

    if st.button(
        "Run CSV Comparison",
        key="csv_v2_run",
        type="primary",
        use_container_width=True,
        disabled=not configuration_valid,
    ):

        st.session_state["csv_v2_last_result"] = None

        try:

            with st.spinner(
                "Analysing selected candle datasets..."
            ):

                result = run_csv_comparison_v2(
                    csv_paths=selected_paths,
                    labels=labels,
                    comparison_name=comparison_name.strip(),
                    save_results=save_results,
                    include_timestamp=include_timestamp,
                )

            st.session_state["csv_v2_last_result"] = result

            # Record the five most recent runs.
            history = st.session_state.setdefault(
                "csv_v2_recent_runs", []
            )

            history.insert(
                0,
                {
                    "name": comparison_name.strip(),
                    "datasets": result["dataset_count"],
                    "pairs": len(result["pairwise_comparisons"]),
                },
            )

            del history[5:]

        except Exception as exc:

            st.error(
                f"CSV Comparison failed: {exc}"
            )

    # ------------------------------------------
    # Display most recent results
    # ------------------------------------------

    result = st.session_state.get(
        "csv_v2_last_result"
    )

    if result is None:

        st.info(
            "Select at least two datasets and run the comparison."
        )

        return

    st.success(
        f"Comparison completed: {result['dataset_count']} "
        f"datasets, {len(result['pairwise_comparisons'])} pairs."
    )

    st.caption(
        "Showing results from the most recent completed comparison."
    )

    charts_tab, tables_tab, download_tab = st.tabs(
        [
            "Interactive graphs",
            "Results tables",
            "Downloads",
        ]
    )

    # ------------------------------------------
    # Interactive Plotly graphs
    # ------------------------------------------

    with charts_tab:

        volatility_fig = build_volatility_score_chart(
            result
        )

        st.plotly_chart(
            volatility_fig,
            use_container_width=True,
            config={"displaylogo": False},
            key="csv_v2_volatility_plot",
        )

        st.download_button(
            "Download volatility graph (PNG)",
            data=volatility_fig.to_image(
                format="png",
                width=1400,
                height=800,
                scale=2,
            ),
            file_name="volatility_score_comparison.png",
            mime="image/png",
            key="csv_v2_volatility_png",
        )

        similarity_fig = build_metric_similarity_heatmap(
            result
        )

        st.plotly_chart(
            similarity_fig,
            use_container_width=True,
            config={"displaylogo": False},
            key="csv_v2_similarity_plot",
        )

        st.download_button(
            "Download similarity heatmap (PNG)",
            data=similarity_fig.to_image(
                format="png",
                width=1400,
                height=900,
                scale=2,
            ),
            file_name="metric_similarity_heatmap.png",
            mime="image/png",
            key="csv_v2_similarity_png",
        )

        st.caption(
            "Volatility scores are relative to the selected "
            "datasets. Metric similarity is not return correlation."
        )

    # ------------------------------------------
    # Statistical result tables
    # ------------------------------------------

    with tables_tab:

        st.markdown("#### Regime summary")

        st.dataframe(
            result["regime_summary"],
            use_container_width=True,
        )

        st.markdown("#### Pairwise comparison")

        st.dataframe(
            result["pairwise_comparisons"],
            use_container_width=True,
        )

    # ------------------------------------------
    # Download CSV data
    # ------------------------------------------

    with download_tab:

        st.download_button(
            "Download regime summary (CSV)",
            data=result["regime_summary"]
                .to_csv(index=False)
                .encode("utf-8-sig"),
            file_name="regime_summary.csv",
            mime="text/csv",
            key="csv_v2_regime_csv",
        )

        st.download_button(
            "Download pairwise comparisons (CSV)",
            data=result["pairwise_comparisons"]
                .to_csv(index=False)
                .encode("utf-8-sig"),
            file_name="pairwise_comparisons.csv",
            mime="text/csv",
            key="csv_v2_pairs_csv",
        )

        if result["export_paths"]:

            st.write(
                "Saved project reports:",
                result["export_paths"],
            )
