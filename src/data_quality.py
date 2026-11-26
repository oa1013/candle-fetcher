
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


# ---------------------------------------------------------------------------
# Historical research coverage and gap reporting
# ---------------------------------------------------------------------------

def build_research_coverage_report(
    candles: pd.DataFrame,
    start_utc,
    end_utc_exclusive,
) -> dict:
    """
    Measure observed M1 coverage across a requested UTC interval.

    Unobserved calendar minutes are not automatically classified
    as missing trading candles.

    No observations are modified or reconstructed.
    """

    if "datetime" not in candles.columns:
        raise ValueError(
            "Missing required datetime column."
        )

    start = _parse_aware_timestamp(start_utc)
    end = _parse_aware_timestamp(end_utc_exclusive)

    minute = pd.Timedelta(minutes=1)
    day = pd.Timedelta(days=1)

    if pd.isna(start) or pd.isna(end):
        raise ValueError(
            "Coverage boundaries must be timezone-aware."
        )

    if end < start:
        raise ValueError(
            "End boundary cannot precede start boundary."
        )

    if (
        start != start.floor("min")
        or end != end.floor("min")
    ):
        raise ValueError(
            "Coverage boundaries must be minute-aligned."
        )

    source = candles["datetime"]

    if isinstance(source.dtype, pd.DatetimeTZDtype):
        timestamps = source.dt.tz_convert("UTC")

    else:
        timestamps = pd.to_datetime(
            source.map(_parse_aware_timestamp),
            utc=True,
            errors="coerce",
        )

    observed = pd.DatetimeIndex(timestamps)

    if observed.isna().any():
        raise ValueError(
            "Invalid or timezone-naive timestamps found."
        )

    if observed.has_duplicates:
        raise ValueError(
            "Duplicate timestamps found."
        )

    if not observed.is_monotonic_increasing:
        raise ValueError(
            "Timestamps must be chronologically ordered."
        )

    if (observed != observed.floor("min")).any():
        raise ValueError(
            "Non-minute-aligned observations found."
        )

    if ((observed < start) | (observed >= end)).any():
        raise ValueError(
            "Observations outside requested coverage window."
        )

    # -------------------------------------------------------
    # Daily coverage
    # -------------------------------------------------------

    daily_columns = [
        "date_utc",
        "requested_calendar_minutes",
        "recorded_candles",
        "unobserved_minutes",
        "coverage_status",
    ]

    daily_records = []

    observed_counts = pd.Series(
        observed.normalize()
    ).value_counts()

    if start < end:
        requested_days = pd.date_range(
            start=start.normalize(),
            end=(end - minute).normalize(),
            freq="D",
        )

        for current_day in requested_days:

            period_start = max(
                start,
                current_day,
            )

            period_end = min(
                end,
                current_day + day,
            )

            requested_minutes = int(
                (period_end - period_start) / minute
            )

            recorded = int(
                observed_counts.get(current_day, 0)
            )

            unobserved = (
                requested_minutes - recorded
            )

            if recorded == 0:
                status = "no_observations"

            elif unobserved == 0:
                status = "all_calendar_minutes_observed"

            else:
                status = "some_calendar_minutes_unobserved"

            daily_records.append({
                "date_utc": current_day.strftime("%Y-%m-%d"),
                "requested_calendar_minutes": requested_minutes,
                "recorded_candles": recorded,
                "unobserved_minutes": unobserved,
                "coverage_status": status,
            })

    daily = pd.DataFrame(
        daily_records,
        columns=daily_columns,
    )

    # -------------------------------------------------------
    # Monthly coverage
    # -------------------------------------------------------

    monthly_columns = [
        "month_utc",
        "requested_calendar_minutes",
        "recorded_candles",
        "unobserved_minutes",
        "days_requested",
        "days_with_observations",
        "days_without_observations",
        "coverage_status",
    ]

    monthly_records = []

    if not daily.empty:

        month_labels = daily["date_utc"].str[:7]

        for month, group in daily.groupby(
            month_labels,
            sort=True,
        ):

            requested_minutes = int(
                group["requested_calendar_minutes"].sum()
            )

            recorded = int(
                group["recorded_candles"].sum()
            )

            unobserved = int(
                group["unobserved_minutes"].sum()
            )

            days_with_observations = int(
                (group["recorded_candles"] > 0).sum()
            )

            if recorded == 0:
                status = "no_observations"

            elif unobserved == 0:
                status = "all_calendar_minutes_observed"

            else:
                status = "some_calendar_minutes_unobserved"

            monthly_records.append({
                "month_utc": month,
                "requested_calendar_minutes": requested_minutes,
                "recorded_candles": recorded,
                "unobserved_minutes": unobserved,
                "days_requested": len(group),
                "days_with_observations": days_with_observations,
                "days_without_observations": (
                    len(group) - days_with_observations
                ),
                "coverage_status": status,
            })

    monthly = pd.DataFrame(
        monthly_records,
        columns=monthly_columns,
    )

    # -------------------------------------------------------
    # Leading, internal and trailing gaps
    # -------------------------------------------------------

    gap_columns = [
        "gap_start_utc",
        "gap_end_utc_exclusive",
        "unobserved_minutes",
        "gap_type",
        "classification",
    ]

    gap_records = []

    def add_gap(gap_start, gap_end, gap_type):

        if gap_end <= gap_start:
            return

        gap_records.append({
            "gap_start_utc": gap_start,
            "gap_end_utc_exclusive": gap_end,
            "unobserved_minutes": int(
                (gap_end - gap_start) / minute
            ),
            "gap_type": gap_type,
            "classification": "unverified",
        })

    if len(observed) == 0:

        add_gap(
            start,
            end,
            "entire_period",
        )

    else:

        add_gap(
            start,
            observed[0],
            "leading",
        )

        # Identify interrupted M1 sequences without
        # constructing artificial candle observations.
        differences = (
            observed[1:] - observed[:-1]
        )

        gap_positions = np.flatnonzero(
            differences > minute
        )

        for position in gap_positions:

            add_gap(
                observed[position] + minute,
                observed[position + 1],
                "internal",
            )

        add_gap(
            observed[-1] + minute,
            end,
            "trailing",
        )

    gaps = pd.DataFrame(
        gap_records,
        columns=gap_columns,
    )

    # -------------------------------------------------------
    # Overall coverage summary
    # -------------------------------------------------------

    requested_calendar_minutes = int(
        (end - start) / minute
    )

    recorded_candles = len(observed)

    unobserved_minutes = (
        requested_calendar_minutes
        - recorded_candles
    )

    summary = {
        "requested_start_utc": start.isoformat(),

        "requested_end_utc_exclusive": (
            end.isoformat()
        ),

        "requested_calendar_minutes": (
            requested_calendar_minutes
        ),

        "recorded_candles": recorded_candles,

        "unobserved_minutes": unobserved_minutes,

        "first_datetime_utc": (
            observed[0].isoformat()
            if recorded_candles > 0
            else None
        ),

        "last_datetime_utc": (
            observed[-1].isoformat()
            if recorded_candles > 0
            else None
        ),

        "days_requested": len(daily),

        "days_with_observations": int(
            (daily["recorded_candles"] > 0).sum()
        ),

        "days_without_observations": int(
            (daily["recorded_candles"] == 0).sum()
        ),

        "months_requested": len(monthly),

        "months_without_observations": int(
            (monthly["recorded_candles"] == 0).sum()
        ),

        "gap_count": len(gaps),

        "expected_trading_minutes": None,

        "confirmed_missing_trading_minutes": None,

        "historical_trading_calendar_verified": False,

        "coverage_limitation": (
            "Unobserved calendar minutes may include "
            "market closures, holidays, maintenance, "
            "unavailable history or missing trading data. "
            "Historical completeness cannot be established "
            "without a verified broker trading calendar."
        ),
    }

    # Reconcile every report against the same observations.

    if int(daily["recorded_candles"].sum()) != recorded_candles:
        raise RuntimeError(
            "Daily candle count reconciliation failed."
        )

    if int(monthly["recorded_candles"].sum()) != recorded_candles:
        raise RuntimeError(
            "Monthly candle count reconciliation failed."
        )

    if int(gaps["unobserved_minutes"].sum()) != unobserved_minutes:
        raise RuntimeError(
            "Gap duration reconciliation failed."
        )

    return {
        "summary": summary,
        "daily": daily,
        "monthly": monthly,
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Historical timeframe integrity validation
# ---------------------------------------------------------------------------

def validate_historical_timeframe(
    candles: pd.DataFrame,
) -> dict:
    """
    Detect statistical evidence of historical timeframe
    inconsistencies without modifying observations.

    Timestamp spacing alone cannot prove native
    candle timeframe or historical completeness.
    """

    MIN_HOURLY_OBSERVATIONS = 24
    MIN_HOURLY_INTERVAL_RATIO = 0.70
    MIN_MINUTE_RUN = 60

    if "datetime" not in candles.columns:
        raise ValueError(
            "Missing required datetime column."
        )

    source = candles["datetime"].reset_index(drop=True)

    if isinstance(source.dtype, pd.DatetimeTZDtype):

        timestamps = source.dt.tz_convert("UTC")

    else:

        timestamps = pd.to_datetime(
            source.map(_parse_aware_timestamp),
            utc=True,
            errors="coerce",
        )

    if timestamps.isna().any():
        raise ValueError(
            "Invalid or timezone-naive timestamps."
        )

    if timestamps.duplicated().any():
        raise ValueError(
            "Duplicate timestamps detected."
        )

    if not timestamps.is_monotonic_increasing:
        raise ValueError(
            "Timestamps must be chronologically sorted."
        )

    if (
        timestamps != timestamps.dt.floor("min")
    ).any():
        raise ValueError(
            "Non-minute-aligned timestamps detected."
        )

    total = len(timestamps)

    intervals = (
        timestamps.diff()
        .dt.total_seconds()
        .div(60)
    )

    hourly_aligned = (
        timestamps.dt.minute == 0
    )

    non_hourly = timestamps.loc[
        ~hourly_aligned
    ]

    first_non_hourly = (
        non_hourly.iloc[0].isoformat()
        if not non_hourly.empty
        else None
    )

    # ---------------------------------------------------
    # Consecutive minute-level activity
    # ---------------------------------------------------

    minute_intervals = int(
        intervals.eq(1).sum()
    )

    longest_minute_run = 0

    if total:

        minute_groups = (
            intervals.ne(1).cumsum()
        )

        longest_minute_run = int(
            minute_groups.value_counts().max()
        )

    has_minute_evidence = (
        longest_minute_run >= MIN_MINUTE_RUN
    )

    # ---------------------------------------------------
    # Detect uninterrupted regions of hour-aligned
    # observations.
    #
    # Weekend and other longer gaps are permitted,
    # provided that enough intervals are exactly 60
    # minutes apart.
    # ---------------------------------------------------

    hourly_regions = []

    # Hour-aligned candles may still belong to
    # consecutive minute-level activity.
    #
    # Exclude observations with an immediately
    # preceding or following one-minute interval
    # from suspicious hourly region detection.

    adjacent_minute_evidence = (
        intervals.eq(1)
        | intervals.shift(-1).eq(1)
    )

    hourly_candidates = (
        hourly_aligned
        & ~adjacent_minute_evidence
    )

    hourly_positions = np.flatnonzero(
        hourly_candidates.to_numpy()
    )

    if len(hourly_positions):

        split_positions = np.flatnonzero(
            np.diff(hourly_positions) != 1
        ) + 1

        candidate_regions = np.split(
            hourly_positions,
            split_positions,
        )

        for positions in candidate_regions:

            count = len(positions)

            if count < MIN_HOURLY_OBSERVATIONS:
                continue

            region_times = timestamps.iloc[
                positions
            ]

            region_intervals = (
                region_times.diff()
                .dt.total_seconds()
                .div(60)
                .dropna()
            )

            hourly_interval_count = int(
                region_intervals.eq(60).sum()
            )

            hourly_ratio = (
                hourly_interval_count
                / len(region_intervals)
            )

            if hourly_ratio < MIN_HOURLY_INTERVAL_RATIO:
                continue

            hourly_regions.append({
                "first_datetime_utc": (
                    region_times.iloc[0].isoformat()
                ),

                "last_datetime_utc": (
                    region_times.iloc[-1].isoformat()
                ),

                "observation_count": count,

                "first_row_position": int(
                    positions[0]
                ),

                "last_row_position": int(
                    positions[-1]
                ),

                "hourly_interval_count": (
                    hourly_interval_count
                ),

                "hourly_interval_ratio": float(
                    hourly_ratio
                ),

                "classification": "suspected_hourly",
            })

    suspected_hourly_rows = sum(
        region["observation_count"]
        for region in hourly_regions
    )

    has_hourly_evidence = bool(hourly_regions)

    # ---------------------------------------------------
    # Evidence-based classification
    # ---------------------------------------------------

    if total == 0:

        classification = "no_observations"

    elif has_hourly_evidence and has_minute_evidence:

        classification = "possible_mixed_timeframe"

    elif has_hourly_evidence:

        classification = "suspected_hourly"

    elif has_minute_evidence:

        classification = "minute_level_evidence"

    else:

        classification = "insufficient_evidence"

    warnings = []

    if has_hourly_evidence:

        warnings.append(
            "Suspicious hourly observation regions "
            "detected in data requested as M1."
        )

    if classification == "insufficient_evidence":

        warnings.append(
            "Insufficient statistical evidence to "
            "determine historical candle timeframe."
        )

    if classification == "no_observations":

        warnings.append(
            "No observations available for "
            "timeframe validation."
        )

    return {
        "classification": classification,

        "requested_timeframe": "M1",

        "total_observations": total,

        "hour_aligned_observations": int(
            hourly_aligned.sum()
        ),

        "non_hour_aligned_observations": len(
            non_hourly
        ),

        "first_non_hourly_utc": first_non_hourly,

        "consecutive_minute_intervals": (
            minute_intervals
        ),

        "longest_minute_run": longest_minute_run,

        "has_minute_level_evidence": (
            has_minute_evidence
        ),

        "has_suspected_hourly_evidence": (
            has_hourly_evidence
        ),

        "suspected_hourly_rows": (
            suspected_hourly_rows
        ),

        "suspected_hourly_regions": hourly_regions,

        "native_m1_proven": False,

        "cross_timeframe_verification_performed": False,

        "detection_thresholds": {
            "minimum_hourly_observations": (
                MIN_HOURLY_OBSERVATIONS
            ),

            "minimum_hourly_interval_ratio": (
                MIN_HOURLY_INTERVAL_RATIO
            ),

            "minimum_minute_run": MIN_MINUTE_RUN,
        },

        "warnings": warnings,

        "limitation": (
            "Timestamp spacing provides statistical "
            "evidence only. Independent cross-timeframe "
            "verification is required for stronger "
            "historical timeframe validation."
        ),
    }

