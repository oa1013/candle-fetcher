from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import (
    DEFAULT_INPUT_PATTERN,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    RAW_DATA_DIR,
)
from .date_filters import apply_date_filters
from .exports import print_export_summary, save_session_csv
from .loaders import load_candle_folder, summarize_candles
from .session_filters import describe_session, filter_and_label_session, get_session_config


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_session_pipeline(
    session_name: str,
    start_date=None,
    end_date=None,
    years=None,
    months=None,
    weeks=None,
    days=None,
    weekdays=None,
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    raw_data_folder: str | Path = RAW_DATA_DIR,
    input_pattern: str = DEFAULT_INPUT_PATTERN,
    save_output: bool = True,
    output_suffix: str | None = None,
) -> dict:
    """
    Run the full candle filtering pipeline.

    Steps:
        1. Load all CSVs from data/raw/
        2. Apply optional date filters
        3. Apply session filter
        4. Save filtered CSV
        5. Return result dictionary

    Examples:
        run_session_pipeline("new_york", start_date="2021-01-01", end_date="2021-12-31")

        run_session_pipeline("london", years=[2021, 2022])

        run_session_pipeline("asia", months=[1, 2, 3])

        run_session_pipeline("all_sessions", start_date="2023/12/03", end_date="2024/12/03")
    """
    session_name = session_name.strip().lower()
    session_config = get_session_config(session_name)
    timezone_name = session_config["timezone"]

    print("Starting candle pipeline")
    print(describe_session(session_name))

    # 1. Load raw CSV data
    raw_df = load_candle_folder(
        folder=raw_data_folder,
        pattern=input_pattern,
    )

    raw_summary = summarize_candles(raw_df)

    print(f"Raw rows loaded: {raw_summary['rows']:,}")
    print(f"Raw first datetime: {raw_summary['first_datetime']}")
    print(f"Raw last datetime: {raw_summary['last_datetime']}")

    # 2. Apply date filters
    date_filtered_df = apply_date_filters(
        df=raw_df,
        start_date=start_date,
        end_date=end_date,
        years=years,
        months=months,
        weeks=weeks,
        days=days,
        weekdays=weekdays,
        timezone_name=timezone_name,
    )

    date_summary = summarize_candles(date_filtered_df)

    print(f"Rows after date filters: {date_summary['rows']:,}")

    # 3. Apply session filter and label
    final_df = filter_and_label_session(
        df=date_filtered_df,
        session_name=session_name,
    )

    final_summary = summarize_candles(final_df)

    print(f"Rows after session filter: {final_summary['rows']:,}")

    if final_df.empty:
        raise RuntimeError(
            "No candles remained after filtering. "
            "Check your CSVs, date range, and session settings."
        )

    # 4. Save output
    export_result = None

    if save_output:
        export_result = save_session_csv(
            df=final_df,
            session_name=session_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            suffix=output_suffix,
        )

        print_export_summary(export_result)

    # 5. Return result
    return {
        "session_name": session_name,
        "session_description": describe_session(session_name),
        "raw_rows": raw_summary["rows"],
        "date_filtered_rows": date_summary["rows"],
        "final_rows": final_summary["rows"],
        "first_datetime": final_summary["first_datetime"],
        "last_datetime": final_summary["last_datetime"],
        "export": export_result,
        "data": final_df,
    }


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def run_new_york_pipeline(**kwargs) -> dict:
    """Run the pipeline for the New York session."""
    return run_session_pipeline(
        session_name="new_york",
        **kwargs,
    )


def run_london_pipeline(**kwargs) -> dict:
    """Run the pipeline for the London session."""
    return run_session_pipeline(
        session_name="london",
        **kwargs,
    )


def run_asia_pipeline(**kwargs) -> dict:
    """Run the pipeline for the Asia session."""
    return run_session_pipeline(
        session_name="asia",
        **kwargs,
    )


def run_all_sessions_pipeline(**kwargs) -> dict:
    """Run the pipeline for all sessions with no session time filter."""
    return run_session_pipeline(
        session_name="all_sessions",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_pipeline_result(result: dict) -> None:
    """Print a clean summary from a pipeline result dictionary."""
    print("Pipeline result")
    print(f"Session: {result['session_name']}")
    print(f"Description: {result['session_description']}")
    print(f"Raw rows: {result['raw_rows']:,}")
    print(f"Date-filtered rows: {result['date_filtered_rows']:,}")
    print(f"Final rows: {result['final_rows']:,}")
    print(f"First datetime: {result['first_datetime']}")
    print(f"Last datetime: {result['last_datetime']}")

    if result["export"] is not None:
        print(f"Saved to: {result['export']['output_path']}")