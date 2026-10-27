from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loaders import load_candle_csv

from .range_analysis import (
    calculate_daily_ranges,
    calculate_session_ranges_with_quality,
)

from .data_quality import classify_daily_coverage
from .v2_csv_discovery import discover_processed_csvs


# Validated historical session reference settings.
SESSION_REFERENCES = {
    "new_york": None,
    "london": None,
    "asia": "10:05",
}

DAILY_REFERENCE_CANDLES = 1365


def _summarize_session(
    ranges: pd.DataFrame,
) -> dict:
    """
    Summarize session ranges, separating complete
    sessions from incomplete sessions.

    Percentiles use complete sessions only.
    """

    if ranges.empty:
        return {
            "total_sessions": 0,
            "complete_sessions": 0,
            "incomplete_sessions": 0,
            "mean_range": None,
            "median_range": None,
            "max_range": None,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
        }

    complete_mask = (
        ranges["is_complete"]
        .fillna(False)
        .astype(bool)
    )

    complete_ranges = ranges.loc[
        complete_mask, "range_points"
    ]

    def statistic(function):
        if complete_ranges.empty:
            return None
        return round(float(function()), 2)

    return {
        "total_sessions": len(ranges),
        "complete_sessions": int(complete_mask.sum()),
        "incomplete_sessions": int((~complete_mask).sum()),
        "mean_range": statistic(complete_ranges.mean),
        "median_range": statistic(complete_ranges.median),
        "max_range": statistic(complete_ranges.max),
        "p10": statistic(
            lambda: complete_ranges.quantile(0.10)
        ),
        "p25": statistic(
            lambda: complete_ranges.quantile(0.25)
        ),
        "p50": statistic(
            lambda: complete_ranges.quantile(0.50)
        ),
        "p75": statistic(
            lambda: complete_ranges.quantile(0.75)
        ),
        "p90": statistic(
            lambda: complete_ranges.quantile(0.90)
        ),
    }


def run_daily_session_range_v2(
    csv_path: str | Path,
) -> dict:
    """
    Run Daily Session Range Analyzer for Candle Fetcher 2.0.

    Uses the existing historical range and data-quality
    engines without changing their calculations.
    """

    path = Path(csv_path).resolve()

    # ------------------------------------------
    # Validate selected dataset
    # ------------------------------------------

    available_paths = {
        Path(item["path"]).resolve()
        for item in discover_processed_csvs()
    }

    if path not in available_paths:
        raise ValueError(
            "Selected CSV is not in the processed dataset list."
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    # ------------------------------------------
    # Load historical candles
    # ------------------------------------------

    candles = load_candle_csv(path)

    if candles.empty:
        raise ValueError(
            "The selected CSV contains no candle data."
        )

    # ------------------------------------------
    # Daily UTC high / low ranges
    # ------------------------------------------

    daily_ranges = calculate_daily_ranges(
        candles,
        timezone="UTC",
    )

    daily_ranges = classify_daily_coverage(
        daily_ranges,
        reference_candles=DAILY_REFERENCE_CANDLES,
    )

    daily_summary = {
        "total_days": len(daily_ranges),
        "reference_days": int(
            (
                daily_ranges["coverage_status"]
                == "reference_coverage"
            ).sum()
        ),
        "reduced_days": int(
            (
                daily_ranges["coverage_status"]
                == "reduced_coverage"
            ).sum()
        ),
        "above_reference_days": int(
            (
                daily_ranges["coverage_status"]
                == "above_reference"
            ).sum()
        ),
        "mean_range": round(
            float(daily_ranges["range_points"].mean()),
            2,
        ),
        "median_range": round(
            float(daily_ranges["range_points"].median()),
            2,
        ),
        "largest_range": round(
            float(daily_ranges["range_points"].max()),
            2,
        ),
    }

    # ------------------------------------------
    # Market session range analysis
    # ------------------------------------------

    session_ranges = {}
    session_summaries = {}

    for session_name, reference_start in (
        SESSION_REFERENCES.items()
    ):

        ranges = calculate_session_ranges_with_quality(
            candles,
            session_name=session_name,
            reference_start=reference_start,
        )

        session_ranges[session_name] = ranges

        session_summaries[session_name] = (
            _summarize_session(ranges)
        )

    # ------------------------------------------
    # Website-ready results
    # ------------------------------------------

    return {
        "status": "completed",
        "csv_path": str(path),
        "filename": path.name,
        "total_candles": len(candles),
        "daily_ranges": daily_ranges,
        "daily_summary": daily_summary,
        "session_ranges": session_ranges,
        "session_summaries": session_summaries,
        "daily_timezone": "UTC",
        "daily_reference_candles": DAILY_REFERENCE_CANDLES,
        "session_references": SESSION_REFERENCES.copy(),
    }
