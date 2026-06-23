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

from src.dashboard_ui import (
    load_css,
    render_footer_note,
    render_page_header,
)

from src.csv_comparison import compare_csv_files

from src.comparison_formatting import (
    format_regime_summary_table,
    format_pairwise_comparison_table,
)

from src.comparison_exports import save_comparison_result


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CSV Comparison",
    page_icon="📊",
    layout="wide",
)

load_css(PROJECT_ROOT / "apps" / "assets" / "app_styles.css")


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("CSV Comparison Settings")

theme = st.sidebar.selectbox(
    "Theme",
    THEME_OPTIONS,
    index=0,
)

apply_streamlit_theme(theme)


DEFAULT_CSV_PATHS = "\n".join(
    [
        str(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "all_sessions"
            / "us100_cash_M1_all_sessions_2024_01_01_to_2024_12_31.csv"
        ),
        str(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "new_york"
            / "us100_cash_M1_new_york_2021_01_01_to_2021_12_31.csv"
        ),
        str(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "london"
            / "us100_cash_M1_london_2021_01_01_to_2021_12_31.csv"
        ),
    ]
)

DEFAULT_LABELS = "\n".join(
    [
        "All Sessions 2024",
        "New York 2021",
        "London 2021",
    ]
)


csv_paths_text = st.sidebar.text_area(
    "CSV file paths",
    value=DEFAULT_CSV_PATHS,
    height=180,
)

labels_text = st.sidebar.text_area(
    "CSV labels",
    value=DEFAULT_LABELS,
    height=120,
)

comparison_name = st.sidebar.text_input(
    "Comparison name",
    value="dashboard_csv_comparison",
)

save_results = st.sidebar.checkbox(
    "Save comparison results",
    value=False,
)

include_timestamp = st.sidebar.checkbox(
    "Include timestamp in saved files",
    value=True,
)

run_analysis = st.sidebar.button(
    "Run Comparison",
    type="primary",
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

render_page_header(
    title="CSV Comparison",
    subtitle=(
        "Compare processed candle CSV files and review regimes, "
        "similarity scores, and pairwise differences."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_lines(text: str) -> list[str]:
    """
    Split text area input into clean non-empty lines.
    """

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def resolve_path(path_text: str) -> Path:
    """
    Resolve relative or absolute CSV path.
    """

    path = Path(path_text)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

if not run_analysis:
    st.info("Add two or more CSV files and click **Run Comparison**.")
    st.stop()


csv_path_lines = parse_lines(csv_paths_text)
label_lines = parse_lines(labels_text)

if len(csv_path_lines) < 2:
    st.error("Please provide at least two CSV files.")
    st.stop()

if label_lines and len(label_lines) != len(csv_path_lines):
    st.error("The number of labels must match the number of CSV paths.")
    st.stop()

csv_paths = [
    resolve_path(path_text)
    for path_text in csv_path_lines
]

missing_paths = [
    path
    for path in csv_paths
    if not path.exists()
]

if missing_paths:
    st.error("Some CSV files were not found:")
    for missing_path in missing_paths:
        st.write(str(missing_path))
    st.stop()

labels = label_lines if label_lines else [path.stem for path in csv_paths]


with st.spinner("Comparing CSV files..."):
    result = compare_csv_files(
        csv_paths=csv_paths,
        labels=labels,
    )


regime_summary = format_regime_summary_table(result["regime_summary"])
pairwise_comparisons = format_pairwise_comparison_table(result["pairwise_comparisons"])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

st.subheader("Comparison summary")

col1, col2, col3 = st.columns(3)

col1.metric("CSV files", len(csv_paths))
col2.metric("Pairwise comparisons", len(pairwise_comparisons))

if not regime_summary.empty and "Regime" in regime_summary.columns:
    regime_counts = regime_summary["Regime"].value_counts()
    most_common_regime = regime_counts.index[0]
else:
    most_common_regime = "N/A"

col3.metric("Most common regime", most_common_regime)


# ---------------------------------------------------------------------------
# Regime table
# ---------------------------------------------------------------------------

st.subheader("Regime summary")

st.caption(
    "This table shows the behavior of each CSV: calm, normal, volatile, or extreme."
)

st.dataframe(
    regime_summary,
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Pairwise table
# ---------------------------------------------------------------------------

st.subheader("Pairwise comparisons")

st.caption(
    "This table compares each CSV against the others and gives similarity scores."
)

st.dataframe(
    pairwise_comparisons,
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

if save_results:
    export_paths = save_comparison_result(
        result=result,
        comparison_name=comparison_name,
        include_timestamp=include_timestamp,
    )

    st.success("Comparison results saved.")
    st.write(export_paths)

    render_footer_note(
    "CSV comparisons are for research only. Similarity scores do not predict future market behavior."
)