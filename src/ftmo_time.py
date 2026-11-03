"""
FTMO-specific MT5 server-clock timestamp conversions.

FTMO-Server3 was observed returning Athens wall-clock values
encoded as Unix timestamps.

These helpers are deliberately isolated so they are not
automatically applied to other MT5 brokers.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd


FTMO_TIMEZONE = ZoneInfo("Europe/Athens")
UTC = timezone.utc


def utc_to_ftmo_request_clock(value: datetime) -> datetime:
    """
    Convert a real timezone-aware instant into the
    UTC-labelled Athens clock expected by the observed
    FTMO-Server3 MT5 request interface.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Input datetime must be timezone-aware.")

    athens_time = value.astimezone(FTMO_TIMEZONE)

    return athens_time.replace(tzinfo=UTC)


def ftmo_raw_seconds_to_utc(seconds: pd.Series) -> pd.Series:
    """
    Convert raw FTMO server-clock Unix values into
    genuine timezone-aware UTC timestamps.

    Raise an error for ambiguous or nonexistent Athens
    local times rather than silently corrupting data.
    """
    server_clock = pd.to_datetime(
        seconds,
        unit="s",
        utc=True,
        errors="raise",
    )

    return (
        server_clock
        .dt.tz_localize(None)
        .dt.tz_localize(
            "Europe/Athens",
            ambiguous="raise",
            nonexistent="raise",
        )
        .dt.tz_convert("UTC")
    )
