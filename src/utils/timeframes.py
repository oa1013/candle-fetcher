SUPPORTED_TIMEFRAMES = {
    "M1",
    "M5",
    "M15",
    "M30",
    "H1",
    "H4",
    "D1",
}


TIMEFRAME_ALIASES = {
    "1m": "M1",
    "m1": "M1",
    "M1": "M1",

    "5m": "M5",
    "m5": "M5",
    "M5": "M5",

    "15m": "M15",
    "m15": "M15",
    "M15": "M15",

    "30m": "M30",
    "m30": "M30",
    "M30": "M30",

    "1h": "H1",
    "h1": "H1",
    "H1": "H1",

    "4h": "H4",
    "h4": "H4",
    "H4": "H4",

    "1d": "D1",
    "d1": "D1",
    "D1": "D1",
}


def normalize_timeframe(timeframe: str) -> str:
    """
    Converts user-friendly timeframe input into the MT5-style format.

    Examples:
        1m -> M1
        m1 -> M1
        M1 -> M1
        5m -> M5
        1h -> H1
    """

    if timeframe is None:
        return "M1"

    timeframe = str(timeframe).strip()

    if timeframe in TIMEFRAME_ALIASES:
        timeframe = TIMEFRAME_ALIASES[timeframe]
    else:
        timeframe = timeframe.upper()

    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. "
            f"Supported timeframes are: {sorted(SUPPORTED_TIMEFRAMES)}"
        )

    return timeframe