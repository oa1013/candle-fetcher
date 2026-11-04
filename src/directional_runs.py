"""
Candle Fetcher — Directional Run Tracking.

Method B: pullback-tolerant historical movement analysis.

Closing prices define structural extremes and reversal
retracements. Wick excursions are measured separately.

No predictions, VWAP calculations, or trading signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.directional_continuation import calculate_wilder_atr
from src.directional_starts import detect_directional_starts


def _validate_reversal_settings(
    reversal_atr_multiple,
    reversal_move_fraction,
    min_opposite_closes,
):
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


def _track_candidate(
    data: pd.DataFrame,
    start: pd.Series,
    settings: dict,
) -> dict:
    """
    Follow one directional candidate through pullbacks.

    Closing prices define the structural endpoint.

    Three complementary movement measurements are retained:
    - Wick on the structural endpoint candle
    - Largest wick within the directional run
    - Largest wick through reversal confirmation

    The starting reference candle's earlier wick is excluded.
    """

    segment_id = int(start["segment_id"])
    start_index = int(start["start_index"])
    confirmation_index = int(start["confirmation_index"])

    direction = start["direction"]
    start_price = float(start["start_price"])
    starting_atr = float(start["atr_at_confirmation"])

    bullish = direction == "bullish"

    initial = data.iloc[
        start_index + 1:confirmation_index + 1
    ]

    if bullish:
        extreme_index = int(initial["close"].idxmax())
        wick_index = int(initial["high"].idxmax())
        wick_column = "high"
    else:
        extreme_index = int(initial["close"].idxmin())
        wick_index = int(initial["low"].idxmin())
        wick_column = "low"

    structural_close = float(
        data.at[extreme_index, "close"]
    )

    extreme_price = float(
        data.at[extreme_index, wick_column]
    )

    maximum_wick_price = float(
        data.at[wick_index, wick_column]
    )

    # The structural endpoint may precede start confirmation.
    # Exclude any later wicks from the in-run measurement.
    in_run_window = data.iloc[
        start_index + 1:extreme_index + 1
    ]

    if bullish:
        in_run_wick_index = int(
            in_run_window["high"].idxmax()
        )
    else:
        in_run_wick_index = int(
            in_run_window["low"].idxmin()
        )

    in_run_wick_price = float(
        data.at[in_run_wick_index, wick_column]
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

        close = float(data.at[index, "close"])
        previous_close = float(
            data.at[index - 1, "close"]
        )

        candle_wick = float(
            data.at[index, wick_column]
        )

        # Extended wick tracks the whole observation window.
        if bullish:
            if candle_wick > maximum_wick_price:
                maximum_wick_price = candle_wick
                wick_index = index

            if close > structural_close:
                structural_close = close
                extreme_index = index
                extreme_price = candle_wick

                # All wicks seen so far now fall within
                # the newly extended structural run.
                in_run_wick_price = maximum_wick_price
                in_run_wick_index = wick_index

            opposite = close < previous_close

            close_progress = (
                structural_close - start_price
            )

            retracement = (
                structural_close - close
            )

        else:
            if candle_wick < maximum_wick_price:
                maximum_wick_price = candle_wick
                wick_index = index

            if close < structural_close:
                structural_close = close
                extreme_index = index
                extreme_price = candle_wick

                in_run_wick_price = maximum_wick_price
                in_run_wick_index = wick_index

            opposite = close > previous_close

            close_progress = (
                start_price - structural_close
            )

            retracement = (
                close - structural_close
            )

        opposite_count = (
            opposite_count + 1 if opposite else 0
        )

        threshold = max(
            settings["reversal_atr_multiple"]
            * starting_atr,
            settings["reversal_move_fraction"]
            * max(close_progress, 0.0),
        )

        if (
            opposite_count
            >= settings["min_opposite_closes"]
            and retracement >= threshold
        ):
            reversal_index = index
            status = "reversal_confirmed"
            break

    start_time = data.at[start_index, "datetime"]
    end_time = data.at[extreme_index, "datetime"]

    close_progress_points = abs(
        structural_close - start_price
    )

    in_run_wick_points = abs(
        in_run_wick_price - start_price
    )

    maximum_wick_excursion_points = abs(
        maximum_wick_price - start_price
    )

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
        "close_progress_points": close_progress_points,
        "maximum_in_run_wick_excursion_points": (
            in_run_wick_points
        ),
        "maximum_in_run_wick_excursion_index": (
            in_run_wick_index
        ),
        "maximum_wick_excursion_points": (
            maximum_wick_excursion_points
        ),
        "maximum_wick_excursion_index": wick_index,
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


def track_first_directional_run(
    candles: pd.DataFrame,
    atr_period: int = 14,
    min_atr_fraction: float = 0.5,
    reversal_atr_multiple: float = 2.0,
    reversal_move_fraction: float = 0.2,
    min_opposite_closes: int = 2,
) -> dict | None:
    """Track the first confirmed directional start."""

    _validate_reversal_settings(
        reversal_atr_multiple,
        reversal_move_fraction,
        min_opposite_closes,
    )

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

    settings = {
        "reversal_atr_multiple": reversal_atr_multiple,
        "reversal_move_fraction": reversal_move_fraction,
        "min_opposite_closes": min_opposite_closes,
    }

    return _track_candidate(
        data,
        starts.iloc[0],
        settings,
    )
