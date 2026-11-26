
from __future__ import annotations

import numpy as np
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

    observed = observed[
        (observed >= start_time)
        & (observed < end_time)
    ]

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


# ---------------------------------------------------------------------------
# Raw historical M1 research validation
# ---------------------------------------------------------------------------

RAW_M1_REQUIRED_COLUMNS = (
    "datetime",
    "mt5_time_raw",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
)


def _parse_aware_timestamp(value):
    """Parse a timestamp without assuming a missing timezone."""

    try:
        timestamp = pd.Timestamp(value)

        if pd.isna(timestamp):
            return pd.NaT

        if timestamp.tzinfo is None:
            return pd.NaT

        return timestamp.tz_convert("UTC")

    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def validate_raw_m1_candles(
    candles: pd.DataFrame,
) -> dict:
    """
    Inspect raw M1 candle observations.

    This function reports data-quality problems without
    modifying, deleting, filling or reconstructing observations.

    Timestamp spacing alone does not establish native M1
    provenance or historical market coverage.
    """

    missing_columns = [
        column
        for column in RAW_M1_REQUIRED_COLUMNS
        if column not in candles.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required raw candle columns: "
            f"{missing_columns}"
        )

    data = candles.reset_index(drop=True)

    # Timestamp validation
    source = data["datetime"]

    if isinstance(source.dtype, pd.DatetimeTZDtype):
        timestamps = source.dt.tz_convert("UTC")
    else:
        timestamps = pd.to_datetime(
            source.map(_parse_aware_timestamp),
            utc=True,
            errors="coerce",
        )

    invalid_timestamps = timestamps.isna()
    valid_timestamps = timestamps.dropna()

    non_minute_aligned = (
        valid_timestamps
        != valid_timestamps.dt.floor("min")
    )

    duplicate_timestamps = valid_timestamps.duplicated(
        keep=False
    )

    # Numerical validation uses temporary arrays.
    # The original observations remain unchanged.
    numeric = {}

    for column in (
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    ):
        numeric[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        ).to_numpy(
            dtype=float,
            na_value=np.nan,
        )

    open_price = numeric["open"]
    high_price = numeric["high"]
    low_price = numeric["low"]
    close_price = numeric["close"]

    valid_ohlc = (
        np.isfinite(open_price)
        & np.isfinite(high_price)
        & np.isfinite(low_price)
        & np.isfinite(close_price)
    )

    invalid_relationships = valid_ohlc & (
        (high_price < low_price)
        | (high_price < open_price)
        | (high_price < close_price)
        | (low_price > open_price)
        | (low_price > close_price)
    )

    tick_volume = numeric["tick_volume"]
    real_volume = numeric["real_volume"]
    spread = numeric["spread"]

    negative_volume = (
        (np.isfinite(tick_volume) & (tick_volume < 0))
        | (np.isfinite(real_volume) & (real_volume < 0))
    )

    negative_spread = (
        np.isfinite(spread) & (spread < 0)
    )

    invalid_volume = (
        ~np.isfinite(tick_volume)
        | ~np.isfinite(real_volume)
    )

    invalid_spread = ~np.isfinite(spread)

    return {
        "total_candles": len(data),

        "invalid_timestamp_rows": int(
            invalid_timestamps.sum()
        ),

        "non_minute_aligned_rows": int(
            non_minute_aligned.sum()
        ),

        "duplicate_timestamp_rows": int(
            duplicate_timestamps.sum()
        ),

        "is_chronologically_sorted": bool(
            not invalid_timestamps.any()
            and valid_timestamps.is_monotonic_increasing
        ),

        "invalid_ohlc_rows": int(
            (~valid_ohlc).sum()
        ),

        "invalid_ohlc_relationship_rows": int(
            invalid_relationships.sum()
        ),

        "negative_volume_rows": int(
            negative_volume.sum()
        ),

        "negative_spread_rows": int(
            negative_spread.sum()
        ),

        "invalid_volume_rows": int(
            invalid_volume.sum()
        ),

        "invalid_spread_rows": int(
            invalid_spread.sum()
        ),

        "zero_tick_volume_rows": int(
            (tick_volume == 0).sum()
        ),

        "zero_real_volume_rows": int(
            (real_volume == 0).sum()
        ),
    }


# ---------------------------------------------------------------------------
# FTMO raw timestamp consistency validation
# ---------------------------------------------------------------------------

def validate_ftmo_timestamp_consistency(
    candles: pd.DataFrame,
    start_utc,
    end_utc_exclusive,
) -> dict:
    """
    Validate original FTMO Unix timestamp labels against
    their corrected UTC timestamps.

    Reports inconsistencies without modifying observations.

    This checks consistency with the established FTMO
    clock convention, not independent broker authenticity.
    """

    from .ftmo_time import (
        FTMO_NEW_YORK_OFFSET,
        FTMO_REFERENCE_TIMEZONE,
    )

    required_columns = (
        "datetime",
        "mt5_time_raw",
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in candles.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required timestamp columns: "
            f"{missing_columns}"
        )

    start = _parse_aware_timestamp(start_utc)
    end = _parse_aware_timestamp(end_utc_exclusive)

    if pd.isna(start) or pd.isna(end):
        raise ValueError(
            "Requested boundaries must be timezone-aware."
        )

    if end < start:
        raise ValueError(
            "End boundary cannot precede start boundary."
        )

    data = candles.reset_index(drop=True)

    # Validate corrected timestamps without assuming
    # a timezone for naive values.
    corrected_source = data["datetime"]

    if isinstance(
        corrected_source.dtype,
        pd.DatetimeTZDtype,
    ):
        corrected = corrected_source.dt.tz_convert(
            "UTC"
        )

    else:
        corrected = pd.to_datetime(
            corrected_source.map(
                _parse_aware_timestamp
            ),
            utc=True,
            errors="coerce",
        )

    invalid_corrected = corrected.isna()

    # Validate original Unix timestamp values.
    raw_source = data["mt5_time_raw"]

    raw_values = pd.to_numeric(
        raw_source,
        errors="coerce",
    ).to_numpy(
        dtype=float,
        na_value=np.nan,
    )

    boolean_values = raw_source.map(
        lambda value: isinstance(
            value, (bool, np.bool_)
        )
    ).to_numpy(dtype=bool)

    finite = np.isfinite(raw_values)

    whole_seconds = np.zeros(
        len(data),
        dtype=bool,
    )

    whole_seconds[finite] = (
        raw_values[finite]
        == np.floor(raw_values[finite])
    )

    # Restrict Unix seconds to a safely representable
    # historical timestamp range.
    valid_raw = (
        finite
        & whole_seconds
        & ~boolean_values
        & (raw_values >= 0)
        & (raw_values <= 9223372036)
    )

    safe_seconds = pd.Series(
        raw_values,
        index=data.index,
    ).where(valid_raw)

    server_labels = pd.to_datetime(
        safe_seconds,
        unit="s",
        utc=True,
        errors="coerce",
    )

    # Reconstruct the New York wall clock using
    # the established FTMO server convention.
    server_wall = server_labels.dt.tz_localize(
        None
    )

    new_york_wall = (
        server_wall
        - pd.Timedelta(
            FTMO_NEW_YORK_OFFSET
        )
    )

    # Ambiguous and nonexistent DST timestamps
    # must be reported, never guessed.
    decoded = (
        new_york_wall
        .dt.tz_localize(
            FTMO_REFERENCE_TIMEZONE,
            ambiguous="NaT",
            nonexistent="NaT",
        )
        .dt.tz_convert("UTC")
    )

    undecodable_raw = (
        valid_raw & decoded.isna()
    )

    comparable = (
        corrected.notna()
        & decoded.notna()
        & valid_raw
    )

    timestamp_mismatch = (
        comparable
        & corrected.ne(decoded)
    )

    # Annual boundaries are half-open:
    # start inclusive, end exclusive.
    outside_requested_range = (
        corrected.notna()
        & (
            (corrected < start)
            | (corrected >= end)
        )
    )

    result = {
        "total_candles": len(data),

        "invalid_raw_timestamp_rows": int(
            (~valid_raw).sum()
        ),

        "invalid_corrected_timestamp_rows": int(
            invalid_corrected.sum()
        ),

        "undecodable_raw_timestamp_rows": int(
            undecodable_raw.sum()
        ),

        "timestamp_mismatch_rows": int(
            timestamp_mismatch.sum()
        ),

        "outside_requested_range_rows": int(
            outside_requested_range.sum()
        ),
    }

    result["is_consistent"] = all(
        result[field] == 0
        for field in (
            "invalid_raw_timestamp_rows",
            "invalid_corrected_timestamp_rows",
            "undecodable_raw_timestamp_rows",
            "timestamp_mismatch_rows",
            "outside_requested_range_rows",
        )
    )

    return result

