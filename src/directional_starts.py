"""
Candle Fetcher — Directional Start Detector.

Identifies historical bullish and bearish movement starts.

This is a descriptive research component.
It does not generate predictions or trading signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.directional_continuation import calculate_wilder_atr


START_COLUMNS = [
    "segment_id",
    "direction",
    "start_index",
    "confirmation_index",
    "start_time",
    "confirmation_time",
    "start_price",
    "confirmation_price",
    "movement_points",
    "atr_at_confirmation",
    "threshold_points",
]


def detect_directional_starts(
    candles: pd.DataFrame,
    atr_period: int = 14,
    min_atr_fraction: float = 0.5,
) -> pd.DataFrame:
    """
    Identify candidate directional movement starts.

    A bullish candidate requires:
    - At least two consecutive rising closes.
    - Upward displacement >= min_atr_fraction * ATR.

    A bearish candidate uses the opposite conditions.

    Only the first qualifying candidate is emitted per
    uninterrupted same-direction close streak.

    Detection resets at missing M1 intervals.
    """

    if (
        isinstance(min_atr_fraction, bool)
        or not isinstance(min_atr_fraction, (int, float))
        or not np.isfinite(min_atr_fraction)
        or min_atr_fraction <= 0
    ):
        raise ValueError(
            "min_atr_fraction must be a finite positive number."
        )

    data = calculate_wilder_atr(
        candles,
        period=atr_period,
    )

    events = []

    for segment_id, segment in data.groupby(
        "segment_id",
        sort=False,
    ):
        indices = list(segment.index)

        if len(indices) < 3:
            continue

        direction = 0
        streak_start = indices[0]
        consecutive_moves = 0
        recorded = False

        for position in range(1, len(indices)):
            previous_index = indices[position - 1]
            current_index = indices[position]

            previous_close = float(
                data.at[previous_index, "close"]
            )
            current_close = float(
                data.at[current_index, "close"]
            )

            change = current_close - previous_close

            current_direction = (
                1 if change > 0
                else -1 if change < 0
                else 0
            )

            if current_direction == 0:
                direction = 0
                consecutive_moves = 0
                recorded = False
                continue

            if current_direction != direction:
                direction = current_direction
                streak_start = previous_index
                consecutive_moves = 1
                recorded = False
            else:
                consecutive_moves += 1

            if consecutive_moves < 2 or recorded:
                continue

            atr = float(data.at[current_index, "atr"])

            if not np.isfinite(atr):
                continue

            start_price = float(
                data.at[streak_start, "close"]
            )

            displacement = abs(
                current_close - start_price
            )

            threshold = (
                min_atr_fraction * atr
            )

            if displacement < threshold:
                continue

            events.append({
                "segment_id": int(segment_id),
                "direction": (
                    "bullish" if direction == 1
                    else "bearish"
                ),
                "start_index": int(streak_start),
                "confirmation_index": int(current_index),
                "start_time": data.at[
                    streak_start, "datetime"
                ],
                "confirmation_time": data.at[
                    current_index, "datetime"
                ],
                "start_price": start_price,
                "confirmation_price": current_close,
                "movement_points": displacement,
                "atr_at_confirmation": atr,
                "threshold_points": threshold,
            })

            recorded = True

    return pd.DataFrame(
        events,
        columns=START_COLUMNS,
    )
