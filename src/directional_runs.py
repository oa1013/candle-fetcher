"""
Candle Fetcher — Directional Run Tracking.

Initial Method B implementation.

Tracks the first directional movement through small
pullbacks until a meaningful reversal is confirmed.

Historical descriptive research only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.directional_continuation import calculate_wilder_atr
from src.directional_starts import detect_directional_starts


def track_first_directional_run(
    candles: pd.DataFrame,
    atr_period: int = 14,
    min_atr_fraction: float = 0.5,
    reversal_atr_multiple: float = 2.0,
    reversal_move_fraction: float = 0.2,
    min_opposite_closes: int = 2,
) -> dict | None:
    """Track the first confirmed directional start."""

    if (
        isinstance(reversal_atr_multiple, bool)
        or not isinstance(reversal_atr_multiple, (int, float))
        or not np.isfinite(reversal_atr_multiple)
        or reversal_atr_multiple <= 0
    ):
        raise ValueError("Invalid reversal ATR multiple.")

    if (
        isinstance(reversal_move_fraction, bool)
        or not isinstance(reversal_move_fraction, (int, float))
        or not np.isfinite(reversal_move_fraction)
        or not 0 <= reversal_move_fraction <= 1
    ):
        raise ValueError("Invalid reversal movement fraction.")

    if (
        isinstance(min_opposite_closes, bool)
        or not isinstance(min_opposite_closes, int)
        or min_opposite_closes < 1
    ):
        raise ValueError("Invalid opposite-close requirement.")

    starts = detect_directional_starts(
        candles,
        atr_period=atr_period,
        min_atr_fraction=min_atr_fraction,
    )

    if starts.empty:
        return None

    data = calculate_wilder_atr(
        candles,
        period=atr_period,
    )

    start = starts.iloc[0]

    start_index = int(start["start_index"])
    confirmation_index = int(start["confirmation_index"])
    segment_id = int(start["segment_id"])
    direction = start["direction"]
    start_price = float(start["start_price"])
    starting_atr = float(start["atr_at_confirmation"])

    # Our start price is the reference candle's close.
    # Its high/low cannot count as subsequent movement.
    initial = data.iloc[
        start_index + 1:confirmation_index + 1
    ]

    extreme_column = (
        "high" if direction == "bullish" else "low"
    )

    if direction == "bullish":
        extreme_index = int(initial["high"].idxmax())
    else:
        extreme_index = int(initial["low"].idxmin())

    extreme_price = float(
        data.at[extreme_index, extreme_column]
    )

    opposite_count = 0
    reversal_index = None
    status = "incomplete_end_of_data"

    for index in range(
        confirmation_index + 1,
        len(data),
    ):
        if int(data.at[index, "segment_id"]) != segment_id:
            status = "incomplete_gap"
            break

        high = float(data.at[index, "high"])
        low = float(data.at[index, "low"])
        close = float(data.at[index, "close"])
        previous_close = float(
            data.at[index - 1, "close"]
        )

        if direction == "bullish":
            if high > extreme_price:
                extreme_price = high
                extreme_index = index

            opposite = close < previous_close
            movement = extreme_price - start_price
            retracement = extreme_price - close

        else:
            if low < extreme_price:
                extreme_price = low
                extreme_index = index

            opposite = close > previous_close
            movement = start_price - extreme_price
            retracement = close - extreme_price

        opposite_count = (
            opposite_count + 1 if opposite else 0
        )

        threshold = max(
            reversal_atr_multiple * starting_atr,
            reversal_move_fraction * max(movement, 0.0),
        )

        if (
            opposite_count >= min_opposite_closes
            and retracement >= threshold
        ):
            reversal_index = index
            status = "reversal_confirmed"
            break

    start_time = data.at[start_index, "datetime"]
    end_time = data.at[extreme_index, "datetime"]

    return {
        "direction": direction,
        "status": status,
        "segment_id": segment_id,
        "start_index": start_index,
        "start_time": start_time,
        "start_price": start_price,
        "start_confirmation_index": confirmation_index,
        "start_confirmation_time": data.at[
            confirmation_index, "datetime"
        ],
        "end_index": extreme_index,
        "end_time": end_time,
        "end_price": extreme_price,
        "movement_points": abs(
            extreme_price - start_price
        ),
        "duration_minutes": (
            end_time - start_time
        ).total_seconds() / 60,
        "reversal_confirmation_index": reversal_index,
        "reversal_confirmation_time": (
            data.at[reversal_index, "datetime"]
            if reversal_index is not None
            else pd.NaT
        ),
        "atr_at_start_confirmation": starting_atr,
    }
