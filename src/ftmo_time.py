"""
FTMO-Server3 server-clock timestamp conversions.

Observed FTMO-Server3 timestamps encode broker wall-clock
values as Unix timestamps.

For the verified 2024 historical data, the broker clock
follows US daylight-saving transitions:

    FTMO wall time = New York wall time + 7 hours

Therefore:
    Winter: FTMO = UTC+2
    Summer: FTMO = UTC+3

This logic is specific to the verified FTMO server
convention, not a universal MetaTrader5 convention.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd


UTC = timezone.utc
FTMO_REFERENCE_TIMEZONE = ZoneInfo("America/New_York")
FTMO_NEW_YORK_OFFSET = timedelta(hours=7)


def utc_to_ftmo_request_clock(value: datetime) -> datetime:
    """
    Convert a genuine timezone-aware instant into
    the UTC-labelled FTMO broker wall-clock value.

    The broker clock is seven wall-clock hours ahead
    of America/New_York for the verified convention.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "Input datetime must be timezone-aware."
        )

    new_york_local = value.astimezone(
        FTMO_REFERENCE_TIMEZONE
    )

    new_york_wall = new_york_local.replace(
        tzinfo=None
    )

    ftmo_wall = (
        new_york_wall + FTMO_NEW_YORK_OFFSET
    )

    return ftmo_wall.replace(tzinfo=UTC)


def ftmo_raw_seconds_to_utc(
    seconds: pd.Series,
) -> pd.Series:
    """
    Decode FTMO broker-clock Unix labels into genuine
    timezone-aware UTC timestamps.

    First reconstruct the New York wall clock by
    subtracting seven hours, then localize it using
    America/New_York daylight-saving rules.

    Ambiguous and nonexistent wall-clock times raise
    errors rather than being silently interpreted.
    """
    server_labels = pd.to_datetime(
        seconds,
        unit="s",
        utc=True,
        errors="raise",
    )

    server_wall = server_labels.dt.tz_localize(
        None
    )

    new_york_wall = (
        server_wall
        - pd.Timedelta(
            FTMO_NEW_YORK_OFFSET
        )
    )

    return (
        new_york_wall
        .dt.tz_localize(
            "America/New_York",
            ambiguous="raise",
            nonexistent="raise",
        )
        .dt.tz_convert("UTC")
    )
