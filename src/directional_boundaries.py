"""
Candle Fetcher — Directional Run Boundary Classification.

Classifies why a historical directional movement is
incomplete, using explicitly configured session hours.

Descriptive analysis only.

Does not modify directional detection, reversal thresholds,
or existing movement statuses.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.directional_continuation import prepare_m1_candles


def _parse_session_minute(value: str) -> int:
    """Convert a 24-hour HH:MM string to minutes after midnight."""

    if not isinstance(value, str):
        raise ValueError("Session time must be a string.")

    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError(
            "Session times must use HH:MM format."
        ) from exc

    return parsed.hour * 60 + parsed.minute


def _local_minute(timestamp: pd.Timestamp) -> int:
    """Return the local clock minute after midnight."""

    return timestamp.hour * 60 + timestamp.minute


def classify_incomplete_runs(
    candles: pd.DataFrame,
    runs: pd.DataFrame,
    *,
    session_timezone: str,
    session_start: str,
    session_end: str,
) -> pd.DataFrame:
    """
    Add an incomplete_reason column to directional runs.

    Supported session configuration:
    - Explicit IANA timezone
    - Same-day session start and end
    - End time is exclusive
    - One-minute candle timestamps

    Reasons:
    - session_window_end
    - missing_historical_data
    - dataset_end
    - unclassified_boundary

    Confirmed runs retain an empty incomplete_reason.

    The original candles and runs are not modified.
    """

    if not isinstance(session_timezone, str):
        raise ValueError(
            "session_timezone must be a valid timezone name."
        )

    try:
        ZoneInfo(session_timezone)
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"Invalid session timezone: {session_timezone}"
        ) from exc

    start_minute = _parse_session_minute(
        session_start
    )

    end_minute = _parse_session_minute(
        session_end
    )

    if end_minute <= start_minute:
        raise ValueError(
            "Session end must be after session start "
            "within the same local day."
        )

    required = {"segment_id", "status"}

    missing = required.difference(runs.columns)

    if missing:
        raise ValueError(
            f"Run table missing required columns: "
            f"{sorted(missing)}"
        )

    prepared = prepare_m1_candles(candles)

    result = runs.copy(deep=True)

    result["incomplete_reason"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="object",
    )

    # Map each continuous M1 segment to its last candle.
    segment_ends = {}

    for segment_id, segment in prepared.groupby(
        "segment_id",
        sort=False,
    ):
        segment_ends[int(segment_id)] = int(
            segment.index[-1]
        )

    final_dataset_index = len(prepared) - 1

    for row_index, run in result.iterrows():

        status = run["status"]

        if status == "reversal_confirmed":
            continue

        if status not in (
            "incomplete_gap",
            "incomplete_end_of_data",
        ):
            result.at[
                row_index, "incomplete_reason"
            ] = "unclassified_boundary"
            continue

        segment_id = int(run["segment_id"])

        if segment_id not in segment_ends:
            raise ValueError(
                f"Unknown segment ID: {segment_id}"
            )

        last_index = segment_ends[segment_id]

        last_time = (
            prepared.at[last_index, "datetime"]
            .tz_convert(session_timezone)
        )

        last_minute = _local_minute(last_time)

        # The end is exclusive. A 12:30 session ends
        # with the candle timestamped 12:29.
        reached_session_end = (
            last_minute == end_minute - 1
        )

        if status == "incomplete_end_of_data":

            if last_index != final_dataset_index:
                reason = "unclassified_boundary"

            elif reached_session_end:
                reason = "session_window_end"

            elif start_minute <= last_minute < end_minute:
                reason = "dataset_end"

            else:
                reason = "unclassified_boundary"

        else:

            next_index = last_index + 1

            if next_index >= len(prepared):
                reason = "unclassified_boundary"

            else:
                next_time = (
                    prepared.at[next_index, "datetime"]
                    .tz_convert(session_timezone)
                )

                next_minute = _local_minute(next_time)

                same_local_date = (
                    last_time.date() == next_time.date()
                )

                normal_next_session = (
                    not same_local_date
                    and next_minute == start_minute
                )

                internal_session_gap = (
                    same_local_date
                    and start_minute <= last_minute < end_minute
                    and start_minute <= next_minute < end_minute
                    and (
                        next_time - last_time
                        > pd.Timedelta(minutes=1)
                    )
                )

                if (
                    reached_session_end
                    and normal_next_session
                ):
                    reason = "session_window_end"

                elif internal_session_gap:
                    reason = "missing_historical_data"

                else:
                    reason = "unclassified_boundary"

        result.at[
            row_index, "incomplete_reason"
        ] = reason

    return result
