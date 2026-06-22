SUPPORTED_TIMEFRAMES = {
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
}


TIMEFRAME_ALIASES = {
    "m1": "1m",
    "m5": "5m",
    "m15": "15m",
    "m30": "30m",
    "h1": "1h",
    "h4": "4h",
    "d1": "1d",
}


def normalize_timeframe(timeframe: str) -> str:
    """
    Converts timeframe input into a standard format.

    Example:
    M1 -> 1m
    m1 -> 1m
    H1 -> 1h
    1m -> 1m
    """

    if timeframe is None:
        return "1m"

    timeframe = str(timeframe).strip().lower()

    if timeframe in TIMEFRAME_ALIASES:
        timeframe = TIMEFRAME_ALIASES[timeframe]

    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. "
            f"Supported timeframes are: {sorted(SUPPORTED_TIMEFRAMES)}"
        )

    return timeframe