"""
Candle Fetcher — Multiple Directional Runs.

Enumerates successive historical Method B movements.

Uses the shared single-run tracking implementation
so both detectors apply identical structural rules.

Descriptive analysis only.
"""

from __future__ import annotations

import pandas as pd

from src.directional_continuation import calculate_wilder_atr
from src.directional_starts import detect_directional_starts
from src.directional_runs import (
    _track_candidate,
    _validate_reversal_settings,
)


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
    "close_progress_points",
    "maximum_in_run_wick_excursion_points",
    "maximum_in_run_wick_excursion_index",
    "maximum_wick_excursion_points",
    "maximum_wick_excursion_index",
    "duration_minutes",
    "reversal_confirmation_index",
    "reversal_confirmation_time",
    "atr_at_start_confirmation",
]


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

    A new candidate cannot begin before the previous
    structural endpoint.

    Opposite-direction candidates may be confirmed
    before the preceding reversal is confirmed.

    Incomplete runs retain explicit statuses.
    """

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

        # Avoid restarting an existing directional run
        # using a candidate confirmed before its reversal.
        if (
            candidate["direction"] == previous_direction
            and candidate_confirmation
            <= previous_reversal_index
        ):
            continue

        run = _track_candidate(
            data,
            candidate,
            settings,
        )

        runs.append(run)

        if run["status"] == "reversal_confirmed":

            minimum_start_index = int(
                run["end_index"]
            )

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

    return pd.DataFrame(
        runs,
        columns=RUN_COLUMNS,
    )
