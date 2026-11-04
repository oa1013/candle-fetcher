"""
Candle Fetcher — Directional Continuation Engine.

Historical price movement analysis only.

No predictions, trading signals, or VWAP calculations.

This module initially provides:
1. M1 candle validation
2. Trading gap identification
3. Wilder ATR volatility calculation

Continuation detection will be added after these
foundations are tested.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
)

M1_INTERVAL = pd.Timedelta(minutes=1)


def prepare_m1_candles(
    candles: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate and prepare historical M1 candles.

    Requirements:
    - Timezone-aware timestamps
    - Valid OHLC prices
    - Chronological ordering
    - No duplicate timestamps

    Gaps are allowed but assigned separate segment IDs.
    """

    if candles.empty:
        raise ValueError("Candle dataset is empty.")

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in candles.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required candle columns: {missing}"
        )

    data = candles.copy().reset_index(drop=True)

    timestamps = pd.to_datetime(
        data["datetime"],
        errors="raise",
    )

    if not isinstance(
        timestamps.dtype,
        pd.DatetimeTZDtype,
    ):
        raise ValueError(
            "Candle timestamps must be timezone-aware."
        )

    data["datetime"] = timestamps.dt.tz_convert("UTC")

    if data["datetime"].isna().any():
        raise ValueError("Missing candle timestamps found.")

    if data["datetime"].duplicated().any():
        raise ValueError("Duplicate timestamps found.")

    if not data["datetime"].is_monotonic_increasing:
        raise ValueError(
            "Candles must be sorted chronologically."
        )

    for column in ("open", "high", "low", "close"):

        data[column] = pd.to_numeric(
            data[column],
            errors="raise",
        )

        if not np.isfinite(
            data[column].to_numpy(dtype=float)
        ).all():
            raise ValueError(
                f"Invalid numerical values in {column}."
            )

    invalid_prices = (
        (data["high"] < data["low"])
        | (data["high"] < data["open"])
        | (data["high"] < data["close"])
        | (data["low"] > data["open"])
        | (data["low"] > data["close"])
    )

    if invalid_prices.any():
        raise ValueError(
            "Invalid OHLC relationships detected."
        )

    intervals = data["datetime"].diff()

    # Each interruption of the M1 sequence starts
    # a new segment. Continuations must not cross gaps.
    data["segment_id"] = (
        intervals.ne(M1_INTERVAL)
        .cumsum()
        .astype(int)
    )

    return data


def calculate_wilder_atr(
    candles: pd.DataFrame,
    period: int = 14,
) -> pd.DataFrame:
    """
    Calculate Wilder's Average True Range.

    The first ATR is the average of the first 'period'
    true ranges. Subsequent ATR values use Wilder
    smoothing.

    ATR resets after gaps in the M1 data.
    """

    if not isinstance(period, int) or period < 1:
        raise ValueError(
            "ATR period must be a positive integer."
        )

    data = prepare_m1_candles(candles)

    data["true_range"] = np.nan
    data["atr"] = np.nan

    for _, segment in data.groupby(
        "segment_id",
        sort=False,
    ):

        high = segment["high"]
        low = segment["low"]
        close = segment["close"]

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        tr_values = true_range.to_numpy(
            dtype=float
        )

        atr_values = np.full(
            len(segment),
            np.nan,
            dtype=float,
        )

        if len(segment) >= period:

            atr_values[period - 1] = (
                tr_values[:period].mean()
            )

            for index in range(
                period,
                len(segment),
            ):

                atr_values[index] = (
                    (
                        atr_values[index - 1]
                        * (period - 1)
                    )
                    + tr_values[index]
                ) / period

        data.loc[
            segment.index,
            "true_range",
        ] = tr_values

        data.loc[
            segment.index,
            "atr",
        ] = atr_values

    return data
