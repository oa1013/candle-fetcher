from __future__ import annotations

from typing import Any

import pandas as pd

from .config import SESSION_CONFIGS
from .date_filters import get_datetime_series


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def parse_hhmm(value: str) -> tuple[int, int]:
    """
    Parse a HH:MM string into hour and minute.

    Example:
        "09:30" -> (9, 30)
    """
    if not isinstance(value, str):
        raise TypeError("Session time must be a string in HH:MM format.")

    try:
        hour_text, minute_text = value.strip().split(":")
        hour = int(hour_text)
        minute = int(minute_text)
    except Exception as exc:
        raise ValueError(
            f"Invalid time '{value}'. Use HH:MM format, for example '09:30'."
        ) from exc

    if hour < 0 or hour > 23:
        raise ValueError("Hour must be between 0 and 23.")

    if minute < 0 or minute > 59:
        raise ValueError("Minute must be between 0 and 59.")

    return hour, minute


def minutes_since_midnight(value: str) -> int:
    """Convert HH:MM time into minutes since midnight."""
    hour, minute = parse_hhmm(value)
    return hour * 60 + minute


# ---------------------------------------------------------------------------
# Session config helpers
# ---------------------------------------------------------------------------

def list_available_sessions() -> list[str]:
    """Return the available session names."""
    return list(SESSION_CONFIGS.keys())


def get_session_config(session_name: str) -> dict[str, Any]:
    """Return the config dictionary for a session name."""
    normalized_name = session_name.strip().lower()

    if normalized_name not in SESSION_CONFIGS:
        available = ", ".join(list_available_sessions())
        raise ValueError(
            f"Unknown session '{session_name}'. Available sessions: {available}"
        )

    return SESSION_CONFIGS[normalized_name]


def describe_session(session_name: str) -> str:
    """Return a human-readable session description."""
    config = get_session_config(session_name)

    if config["start"] is None or config["end"] is None:
        return f"{config['label']}: full day / no session filter"

    return (
        f"{config['label']}: "
        f"{config['start']} to {config['end']} "
        f"({config['timezone']})"
    )


# ---------------------------------------------------------------------------
# Session filtering
# ---------------------------------------------------------------------------

def filter_by_session(
    df: pd.DataFrame,
    session_name: str,
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """
    Filter candles to one configured session.

    Examples:
        filter_by_session(df, "new_york")
        filter_by_session(df, "london")
        filter_by_session(df, "asia")
        filter_by_session(df, "all_sessions")
    """
    if df.empty:
        return df.copy()

    config = get_session_config(session_name)

    start_time = config["start"]
    end_time = config["end"]
    timezone_name = config["timezone"]

    # All sessions means no intraday time filter.
    if start_time is None or end_time is None:
        return df.copy().reset_index(drop=True)

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    local_minutes = local_dt.dt.hour * 60 + local_dt.dt.minute

    session_start = minutes_since_midnight(start_time)
    session_end = minutes_since_midnight(end_time)

    # Normal same-day session, for example 09:10 to 12:30.
    if session_start < session_end:
        in_session = (
            (local_minutes >= session_start)
            & (local_minutes < session_end)
        )

    # Overnight session, for example 22:00 to 02:00.
    elif session_start > session_end:
        in_session = (
            (local_minutes >= session_start)
            | (local_minutes < session_end)
        )

    # If start and end are the same, treat it as full day.
    else:
        in_session = pd.Series(True, index=df.index)

    return df.loc[in_session].reset_index(drop=True)


def add_session_name_column(
    df: pd.DataFrame,
    session_name: str,
    column_name: str = "session_name",
) -> pd.DataFrame:
    """
    Add a session_name column to a DataFrame.

    This is useful before saving/exporting filtered files.
    """
    output = df.copy()
    output[column_name] = session_name.strip().lower()
    return output


def filter_and_label_session(
    df: pd.DataFrame,
    session_name: str,
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """
    Filter candles by session and add a session_name column.
    """
    filtered = filter_by_session(
        df=df,
        session_name=session_name,
        datetime_column=datetime_column,
    )

    return add_session_name_column(
        df=filtered,
        session_name=session_name,
    )