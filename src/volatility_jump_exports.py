from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .volatility_jumps import format_volatility_jump_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JUMPS_DIR = PROJECT_ROOT / "data" / "jumps"
JUMP_TABLES_DIR = JUMPS_DIR / "tables"
JUMP_REPORTS_DIR = JUMPS_DIR / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_filename_part(value: str) -> str:
    """
    Convert text into a safe filename component.
    """

    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_") or "volatility_jumps"


def ensure_folder_exists(folder: str | Path) -> Path:
    """
    Create a folder if it does not already exist.
    """

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def get_timestamp() -> str:
    """
    Return a timestamp string for filenames.
    """

    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Table export
# ---------------------------------------------------------------------------

def save_jump_table(
    jump_df: pd.DataFrame,
    analysis_name: str,
    include_timestamp: bool = True,
) -> Path:
    """
    Save the user-friendly volatility jump table to CSV.
    """

    output_folder = ensure_folder_exists(JUMP_TABLES_DIR)

    safe_name = clean_filename_part(analysis_name)

    if include_timestamp:
        safe_name = f"{safe_name}_{get_timestamp()}"

    output_path = output_folder / f"{safe_name}_top_jumps.csv"

    friendly_df = format_volatility_jump_table(jump_df)

    friendly_df.to_csv(output_path, index=False)

    return output_path


# ---------------------------------------------------------------------------
# Report export
# ---------------------------------------------------------------------------

def dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """
    Convert a DataFrame to a markdown table.
    """

    if df.empty:
        return "_No volatility jumps found._"

    return df.to_markdown(index=False)


def build_jump_report(
    jump_df: pd.DataFrame,
    analysis_name: str,
) -> str:
    """
    Build a markdown report for volatility jumps.
    """

    friendly_df = format_volatility_jump_table(jump_df)

    if jump_df.empty:
        total_jumps = 0
        largest_jump_score = None
    else:
        total_jumps = len(jump_df)
        largest_jump_score = jump_df["jump_score"].max()

    report = f"""# Volatility Jump Report

Analysis name: {analysis_name}

Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

Total jumps found: {total_jumps}

Largest jump score: {largest_jump_score}

## Top Volatility Jumps

{dataframe_to_markdown_table(friendly_df)}
"""

    return report


def save_jump_report(
    jump_df: pd.DataFrame,
    analysis_name: str,
    include_timestamp: bool = True,
) -> Path:
    """
    Save a markdown volatility jump report.
    """

    output_folder = ensure_folder_exists(JUMP_REPORTS_DIR)

    safe_name = clean_filename_part(analysis_name)

    if include_timestamp:
        safe_name = f"{safe_name}_{get_timestamp()}"

    output_path = output_folder / f"{safe_name}_jump_report.md"

    report = build_jump_report(
        jump_df=jump_df,
        analysis_name=analysis_name,
    )

    output_path.write_text(report, encoding="utf-8")

    return output_path


# ---------------------------------------------------------------------------
# Main export workflow
# ---------------------------------------------------------------------------

def save_volatility_jump_result(
    jump_df: pd.DataFrame,
    analysis_name: str,
    include_timestamp: bool = True,
) -> dict:
    """
    Save volatility jump result table and report.
    """

    table_path = save_jump_table(
        jump_df=jump_df,
        analysis_name=analysis_name,
        include_timestamp=include_timestamp,
    )

    report_path = save_jump_report(
        jump_df=jump_df,
        analysis_name=analysis_name,
        include_timestamp=include_timestamp,
    )

    return {
        "table_path": str(table_path),
        "report_path": str(report_path),
    }


def print_exported_jump_paths(paths: dict) -> None:
    """
    Print exported jump result paths.
    """

    print("Volatility jump export complete")

    for key, path in paths.items():
        print(f"{key}: {path}")