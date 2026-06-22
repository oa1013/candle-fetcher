from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from .comparison_formatting import build_user_friendly_comparison_tables

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPARISON_DIR = PROJECT_ROOT / "data" / "comparisons"
COMPARISON_TABLES_DIR = COMPARISON_DIR / "tables"
COMPARISON_REPORTS_DIR = COMPARISON_DIR / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_filename_part(value: str) -> str:
    """Convert text into a safe filename component."""
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "comparison"


def ensure_folder_exists(folder: str | Path) -> Path:
    """Create a folder if it does not already exist."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_timestamp() -> str:
    """Return a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Table exports
# ---------------------------------------------------------------------------

def save_dataframe(
    df: pd.DataFrame,
    output_folder: str | Path,
    filename: str,
) -> Path:
    """Save a DataFrame to CSV and return the output path."""
    output_folder = ensure_folder_exists(output_folder)
    output_path = output_folder / filename

    df.to_csv(output_path, index=False)

    return output_path


def save_comparison_tables(
    result: dict,
    comparison_name: str,
    include_timestamp: bool = True,
) -> dict:
    """
    Save comparison result tables to CSV.

    Saves:
        regime summary
        pairwise comparisons
        full metrics
    """
    safe_name = clean_filename_part(comparison_name)

    if include_timestamp:
        safe_name = f"{safe_name}_{get_timestamp()}"

    friendly_tables = build_user_friendly_comparison_tables(result)

    regime_summary = friendly_tables["regime_summary"]
    pairwise_comparisons = friendly_tables["pairwise_comparisons"]
    metrics = result["metrics"]

    regime_summary_path = save_dataframe(
        df=regime_summary,
        output_folder=COMPARISON_TABLES_DIR,
        filename=f"{safe_name}_regime_summary.csv",
    )

    pairwise_path = save_dataframe(
        df=pairwise_comparisons,
        output_folder=COMPARISON_TABLES_DIR,
        filename=f"{safe_name}_pairwise_comparisons.csv",
    )

    metrics_path = save_dataframe(
        df=metrics,
        output_folder=COMPARISON_TABLES_DIR,
        filename=f"{safe_name}_full_metrics.csv",
    )

    return {
        "regime_summary_path": str(regime_summary_path),
        "pairwise_comparisons_path": str(pairwise_path),
        "metrics_path": str(metrics_path),
    }


# ---------------------------------------------------------------------------
# Report exports
# ---------------------------------------------------------------------------

def dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """
    Convert a DataFrame to a markdown table.

    If the DataFrame is empty, return a simple message.
    """
    if df.empty:
        return "_No rows available._"

    return df.to_markdown(index=False)


def build_comparison_report(
    result: dict,
    comparison_name: str,
) -> str:
    """
    Build a markdown report from a comparison result.
    """
    friendly_tables = build_user_friendly_comparison_tables(result)

    regime_summary = friendly_tables["regime_summary"]
    pairwise_comparisons = friendly_tables["pairwise_comparisons"]

    report = f"""# {comparison_name}

Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Regime Summary

{dataframe_to_markdown_table(regime_summary)}

## Pairwise Comparisons

{dataframe_to_markdown_table(pairwise_comparisons)}
"""

    return report


def save_comparison_report(
    result: dict,
    comparison_name: str,
    include_timestamp: bool = True,
) -> Path:
    """
    Save a markdown comparison report.
    """
    safe_name = clean_filename_part(comparison_name)

    if include_timestamp:
        safe_name = f"{safe_name}_{get_timestamp()}"

    output_folder = ensure_folder_exists(COMPARISON_REPORTS_DIR)
    output_path = output_folder / f"{safe_name}_report.md"

    report = build_comparison_report(
        result=result,
        comparison_name=comparison_name,
    )

    output_path.write_text(report, encoding="utf-8")

    return output_path


# ---------------------------------------------------------------------------
# Main export workflow
# ---------------------------------------------------------------------------

def save_comparison_result(
    result: dict,
    comparison_name: str,
    include_timestamp: bool = True,
) -> dict:
    """
    Save all comparison outputs.

    Saves:
        regime summary CSV
        pairwise comparison CSV
        full metrics CSV
        markdown report
    """
    table_paths = save_comparison_tables(
        result=result,
        comparison_name=comparison_name,
        include_timestamp=include_timestamp,
    )

    report_path = save_comparison_report(
        result=result,
        comparison_name=comparison_name,
        include_timestamp=include_timestamp,
    )

    output = {
        **table_paths,
        "report_path": str(report_path),
    }

    return output


def print_exported_comparison_paths(paths: dict) -> None:
    """Print exported comparison file paths."""
    print("Comparison export complete")

    for key, path in paths.items():
        print(f"{key}: {path}")