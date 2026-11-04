"""
Candle Fetcher — Multiple Directional Runs.

Experimental Method B historical run enumeration.

Uses confirmed directional starts and pullback-tolerant
reversal detection. Keeps incomplete runs separate.

Descriptive analysis only; no forecasts or signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.directional_continuation import calculate_wilder_atr
from src.directional_starts import detect_directional_starts


RUN_COLUMNS = [
    "direction",
    "status",
    "segment_id",
    "start_index",
    "start_time",
    "start_price",
    "start_confirmation_index",
    "start_confirmation_time",
    "end_index",
    "end_time",
    "end_price",
    "movement_points",
    "duration_minutes",
    "reversal_confirmation_index",
    "reversal_confirmation_time",
    "atr_at_start_confirmation",
]


def _track_candidate(data, start, settings):
    """Follow one candidate until a reversal or data boundary."""

    segment_id = int(start["segment_id"])
    start_index = int(start["start_index"])
    confirmation_index = int(start["confirmation_index"])

    direction = start["direction"]
    start_price = float(start["start_price"])
    starting_atr = float(start["atr_at_confirmation"])

    initial = data.iloc[
        start_index:confirmation_index + 1
    ]

    if direction == "bullish":
        extreme_index = int(initial["high"].idxmax())
        extreme_price = float(data.at[extreme_index, "high"])
    else:
        extreme_index = int(initial["low"].idxmin())
        extreme_price = float(data.at[extreme_index, "low"])

    opposite_count = 0
    reversal_index = None
    status = "incomplete_end_of_data"

    for index in range(confirmation_index + 1, len(data)):

        if int(data.at[index, "segment_id"]) != segment_id:
            status = "incomplete_gap"
            break

        high = float(data.at[index, "high"])
        low = float(data.at[index, "low"])
        close = float(data.at[index, "close"])
        previous_close = float(data.at[index - 1, "close"])

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
            settings["reversal_atr_multiple"] * starting_atr,
            settings["reversal_move_fraction"]
            * max(movement, 0.0),
        )

        if (
            opposite_count >= settings["min_opposite_closes"]
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
        "movement_points": abs(extreme_price - start_price),
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


def detect_directional_runs(
    candles: pd.DataFrame,
    atr_period: int = 14,
    min_atr_fraction: float = 0.5,
    reversal_atr_multiple: float = 2.0,
    reversal_move_fraction: float = 0.2,
    min_opposite_closes: int = 2,
) -> pd.DataFrame:
    """
    Enumerate successive Method B runs.

    A new candidate cannot start before the previous
    run's price extreme. Opposite-direction candidates
    may begin before the prior reversal is confirmed.

    Incomplete runs are retained with explicit statuses.
    """

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
        return pd.DataFrame(columns=RUN_COLUMNS)

    data = calculate_wilder_atr(
        candles,
        period=atr_period,
    )

    settings = {
        "reversal_atr_multiple": reversal_atr_multiple,
        "reversal_move_fraction": reversal_move_fraction,
        "min_opposite_closes": min_opposite_closes,
    }

    runs = []

    minimum_start_index = 0
    minimum_segment_id = 0
    previous_direction = None
    previous_reversal_index = -1

    for _, candidate in starts.iterrows():

        candidate_segment = int(candidate["segment_id"])
        candidate_start = int(candidate["start_index"])
        candidate_confirmation = int(
            candidate["confirmation_index"]
        )

        if candidate_segment < minimum_segment_id:
            continue

        if candidate_start < minimum_start_index:
            continue

        # Do not restart the same direction using an
        # old candidate from the previous run.
        if (
            candidate["direction"] == previous_direction
            and candidate_confirmation <= previous_reversal_index
        ):
            continue

        run = _track_candidate(
            data,
            candidate,
            settings,
        )

        runs.append(run)

        if run["status"] == "reversal_confirmed":

            minimum_start_index = int(run["end_index"])
            previous_direction = run["direction"]
            previous_reversal_index = int(
                run["reversal_confirmation_index"]
            )

        elif run["status"] == "incomplete_gap":

            minimum_segment_id = candidate_segment + 1
            previous_direction = None
            previous_reversal_index = -1

        else:
            break

    return pd.DataFrame(runs, columns=RUN_COLUMNS)
