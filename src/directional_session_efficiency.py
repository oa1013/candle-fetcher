"""
Candle Fetcher — New York Session Efficiency Analyzer.

Descriptive analysis of historical M1 price paths.

Measures:
- Session high-to-low range
- Absolute open-to-close displacement
- Sampled M1 close-path length
- Net displacement as a share of range
- Close-path efficiency

No predictions or trading signals.

Only complete, consecutive M1 sessions are accepted.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from src.directional_continuation import (
    M1_INTERVAL,
    prepare_m1_candles,
)


def _minute_of_day(value: str) -> int:
    """Parse a 24-hour HH:MM session time."""

    try:
        parsed = datetime.strptime(value, "%H:%M")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Session times must use HH:MM format."
        ) from exc

    return parsed.hour * 60 + parsed.minute


def calculate_ny_session_efficiency(
    candles: pd.DataFrame,
    *,
    year: int,
    session_start: str = "09:10",
    session_end: str = "12:30",
) -> pd.DataFrame:
    """
    Calculate historical New York session efficiency.

    Session end is exclusive.

    All timestamps must already represent true UTC
    instants and must be timezone-aware.

    The M1 path length equals:

        abs(first_close - first_open)
        + sum(abs(close[t] - close[t-1]))

    for all subsequent candles in the session.

    Missing or nonconsecutive session candles raise
    ValueError rather than silently biasing results.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError("year must be an integer.")

    start_minute = _minute_of_day(session_start)
    end_minute = _minute_of_day(session_end)

    if end_minute <= start_minute:
        raise ValueError(
            "Session must start and end on the same day, "
            "with end after start."
        )

    expected_candles = end_minute - start_minute

    prepared = prepare_m1_candles(candles)

    ny = prepared["datetime"].dt.tz_convert(
        "America/New_York"
    )

    minute = ny.dt.hour * 60 + ny.dt.minute

    mask = (
        (ny.dt.year == year)
        & (minute >= start_minute)
        & (minute < end_minute)
    )

    window = prepared.loc[
        mask,
        ["datetime", "open", "high", "low", "close"],
    ].copy()

    if window.empty:
        raise ValueError(
            "No candles found for the requested sessions."
        )

    window["ny_session_date"] = (
        ny.loc[mask].dt.strftime("%Y-%m-%d").to_numpy()
    )

    groups = window.groupby(
        "ny_session_date",
        sort=True,
    )

    counts = groups.size()

    if not counts.eq(expected_candles).all():
        raise ValueError(
            "Incomplete NY session detected. "
            "Expected "
            f"{expected_candles} M1 candles per session."
        )

    clock = ny.loc[mask].dt.strftime("%H:%M")

    window["ny_clock"] = clock.to_numpy()

    boundaries = groups["ny_clock"].agg(
        ["first", "last"]
    )

    expected_last = (
        pd.Timestamp("2000-01-01")
        + pd.Timedelta(minutes=end_minute - 1)
    ).strftime("%H:%M")

    if not (
        boundaries["first"].eq(session_start).all()
        and boundaries["last"].eq(expected_last).all()
    ):
        raise ValueError(
            "NY session opening or closing minute missing."
        )

    intervals = groups["datetime"].diff()

    invalid_interval = (
        intervals.notna()
        & intervals.ne(M1_INTERVAL)
    )

    if invalid_interval.any():
        raise ValueError(
            "Nonconsecutive M1 candles within NY session."
        )

    window["abs_close_step"] = (
        groups["close"]
        .diff()
        .abs()
        .fillna(0.0)
    )

    result = (
        window.groupby("ny_session_date", sort=True)
        .agg(
            first_open=("open", "first"),
            first_close=("close", "first"),
            final_close=("close", "last"),
            high_price=("high", "max"),
            low_price=("low", "min"),
            close_steps=("abs_close_step", "sum"),
            candle_count=("close", "size"),
        )
        .reset_index()
    )

    result["reconstructed_range"] = (
        result["high_price"] - result["low_price"]
    )

    result["net_displacement_points"] = (
        result["final_close"] - result["first_open"]
    ).abs()

    result["close_path_points"] = (
        (
            result["first_close"] - result["first_open"]
        ).abs()
        + result["close_steps"]
    )

    if (
        (result["reconstructed_range"] <= 0).any()
        or (result["close_path_points"] <= 0).any()
    ):
        raise ValueError(
            "Cannot calculate efficiency with "
            "zero range or zero sampled path length."
        )

    result["net_range_share_pct"] = (
        100
        * result["net_displacement_points"]
        / result["reconstructed_range"]
    )

    result["close_path_efficiency_pct"] = (
        100
        * result["net_displacement_points"]
        / result["close_path_points"]
    )

    fields = [
        "net_range_share_pct",
        "close_path_efficiency_pct",
    ]

    for field in fields:
        values = result[field]

        if not np.isfinite(values).all():
            raise ValueError(
                f"Invalid calculated values: {field}"
            )

        if not values.between(0, 100.0001).all():
            raise ValueError(
                f"Calculated percentage outside bounds: {field}"
            )

    return result
