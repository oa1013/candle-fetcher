
from __future__ import annotations

import pandas as pd

from .session_filters import get_session_config, filter_by_session


def validate_timestamps(
    df: pd.DataFrame,
    datetime_column: str = "datetime",
) -> dict:
    """
    Validate candle timestamps for duplicates and ordering.

    Returns a dictionary containing data-quality results.
    Does not modify the original DataFrame.
    """

    if datetime_column not in df.columns:
        raise ValueError(
            f"Missing required datetime column: {datetime_column}"
        )

    if df.empty:
        raise ValueError("Cannot validate an empty candle dataset.")

    timestamps = pd.to_datetime(
        df[datetime_column],
        utc=True,
        errors="raise",
    )

    if timestamps.isna().any():
        raise ValueError("Dataset contains missing timestamps.")

    duplicate_rows = int(
        timestamps.duplicated(keep=False).sum()
    )

    backward_moves = int(
        (timestamps.diff() < pd.Timedelta(0)).sum()
    )

    return {
        "total_candles": len(df),
        "unique_timestamps": int(timestamps.nunique()),
        "duplicate_rows": duplicate_rows,
        "is_chronologically_sorted": bool(
            timestamps.is_monotonic_increasing
        ),
        "backward_movements": backward_moves,
    }

def detect_candle_gaps(
    df: pd.DataFrame,
    datetime_column: str = "datetime",
    expected_frequency: str = "1min",
) -> pd.DataFrame:
    """
    Identify gaps between consecutive candle timestamps.

    Returns a DataFrame containing:
    - previous_candle
    - datetime
    - gap_minutes
    - missing_intervals

    Does not modify the original dataset.
    """

    if datetime_column not in df.columns:
        raise ValueError(
            f"Missing required datetime column: {datetime_column}"
        )

    if df.empty:
        raise ValueError("Cannot analyse gaps in an empty dataset.")

    frequency = pd.Timedelta(expected_frequency)

    if frequency <= pd.Timedelta(0):
        raise ValueError("Expected frequency must be positive.")

    timestamps = pd.to_datetime(
        df[datetime_column],
        utc=True,
        errors="raise",
    )

    if timestamps.isna().any():
        raise ValueError("Dataset contains missing timestamps.")

    if timestamps.duplicated().any():
        raise ValueError("Remove duplicate timestamps before gap analysis.")

    if not timestamps.is_monotonic_increasing:
        raise ValueError("Timestamps must be chronologically ordered.")

    gaps = pd.DataFrame({
        "datetime": timestamps,
        "previous_candle": timestamps.shift(1),
    })

    gaps["time_difference"] = (
        gaps["datetime"] - gaps["previous_candle"]
    )

    gaps = gaps[
        gaps["time_difference"] > frequency
    ].copy()

    gaps["gap_minutes"] = (
        gaps["time_difference"].dt.total_seconds() / 60
    )

    gaps["missing_intervals"] = (
        gaps["time_difference"] / frequency - 1
    ).astype(int)

    return gaps[
        [
            "previous_candle",
            "datetime",
            "gap_minutes",
            "missing_intervals",
        ]
    ].reset_index(drop=True)

def classify_candle_gaps(
    gaps: pd.DataFrame,
) -> pd.DataFrame:
    """
    Classify detected candle gaps using observed patterns.

    These are preliminary classifications, not confirmed
    broker trading schedules.
    """

    required = {
        "previous_candle",
        "datetime",
        "gap_minutes",
    }

    if not required.issubset(gaps.columns):
        raise ValueError(
            "Gap data is missing required columns."
        )

    result = gaps.copy()

    if result.empty:
        result["gap_classification"] = pd.Series(
            dtype="string"
        )
        return result

    previous = pd.to_datetime(
        result["previous_candle"], utc=True
    )
    current = pd.to_datetime(
        result["datetime"], utc=True
    )

    recurring_pattern = (
        (result["gap_minutes"] == 76)
        & (previous.dt.strftime("%H:%M") == "23:49")
        & (current.dt.strftime("%H:%M") == "01:05")
    )

    result["gap_classification"] = "extended_gap_review"

    result.loc[
        result["gap_minutes"] < 76,
        "gap_classification"
    ] = "short_gap_review"

    result.loc[
        recurring_pattern,
        "gap_classification"
    ] = "recurring_break_pattern"

    return result

def classify_daily_coverage(
    daily_ranges: pd.DataFrame,
    reference_candles: int = 1365,
) -> pd.DataFrame:
    """
    Classify daily candle coverage against a reference count.

    A reduced count does not automatically mean missing
    data. Holidays and shortened sessions may be legitimate.
    """

    if "candle_count" not in daily_ranges.columns:
        raise ValueError("Missing required column: candle_count")

    if reference_candles <= 0:
        raise ValueError("reference_candles must be positive.")

    result = daily_ranges.copy()

    result["coverage_ratio"] = (
        result["candle_count"] / reference_candles
    ).round(4)

    result["coverage_status"] = "reduced_coverage"

    result.loc[
        result["candle_count"] == reference_candles,
        "coverage_status"
    ] = "reference_coverage"

    result.loc[
        result["candle_count"] > reference_candles,
        "coverage_status"
    ] = "above_reference"

    return result

def validate_session_coverage(
    df: pd.DataFrame,
    session_name: str,
    trading_date: str,
    reference_start: str | None = None,
) -> dict:
    """
    Validate one same-day trading session against its
    configured local opening and closing times.

    Designed for 1-minute candle data.
    """

    config = get_session_config(session_name)

    if config["start"] is None or config["end"] is None:
        raise ValueError("Choose a specific trading session.")

    if df.empty:
        raise ValueError("Cannot validate an empty dataset.")

    data = df.copy()
    data["datetime"] = pd.to_datetime(
        data["datetime"], utc=True
    )

    filtered = filter_by_session(data, session_name)

    timezone = config["timezone"]

    local_times = filtered["datetime"].dt.tz_convert(timezone)

    selected_date = pd.Timestamp(trading_date).date()

    selected = filtered[
        local_times.dt.date == selected_date
    ].copy()

    effective_start = (
        reference_start
        if reference_start is not None
        else config["start"]
    )

    start_time = pd.Timestamp(
        f"{trading_date} {effective_start}",
        tz=timezone,
    )

    end_time = pd.Timestamp(
        f"{trading_date} {config['end']}",
        tz=timezone,
    )

    if start_time >= end_time:
        raise ValueError(
            "Reference start time must be earlier "
            "than the session end time."
        )

    expected_index = pd.date_range(
        start=start_time,
        end=end_time,
        freq="1min",
        inclusive="left",
    )

    observed = pd.DatetimeIndex(
        selected["datetime"].dt.tz_convert(timezone)
    )

    missing = expected_index.difference(observed)
    
    duplicate_candles = int(
    observed.duplicated(keep=False).sum()
)

    return {
        "session": session_name,
        "trading_date": str(selected_date),
        "expected_candles": len(expected_index),
        "recorded_candles": len(observed),
        "missing_candles": len(missing),
        "duplicate_candles": duplicate_candles,
        "first_candle_matches": (
            len(observed) > 0
            and observed.min() == expected_index[0]
        ),
        "last_candle_matches": (
            len(observed) > 0
            and observed.max() == expected_index[-1]
        ),
        "is_complete": (
            len(missing) == 0
            and len(observed) == len(expected_index)
            and duplicate_candles == 0
        ),
    }
