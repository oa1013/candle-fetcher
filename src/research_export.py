"""Dedicated native M1 historical research export engine."""

from __future__ import annotations

from datetime import datetime, timezone


UTC = timezone.utc


def get_research_year_bounds(
    year: int,
    as_of_utc: datetime,
) -> tuple[datetime, datetime]:
    """
    Return the UTC boundaries of a historical calendar year.

    The start boundary is inclusive.
    The end boundary is exclusive.

    For the current year, exclude the currently forming
    M1 candle by flooring the extraction time to a minute.
    """

    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not 1 <= year <= 9998
    ):
        raise ValueError("Invalid calendar year.")

    if not isinstance(as_of_utc, datetime):
        raise ValueError("Extraction time must be a datetime.")

    if (
        as_of_utc.tzinfo is None
        or as_of_utc.utcoffset() is None
    ):
        raise ValueError(
            "Extraction time must be timezone-aware."
        )

    as_of_utc = as_of_utc.astimezone(UTC)

    if year > as_of_utc.year:
        raise ValueError(
            "Cannot extract a future calendar year."
        )

    start_utc = datetime(
        year, 1, 1, tzinfo=UTC
    )

    calendar_end_utc = datetime(
        year + 1, 1, 1, tzinfo=UTC
    )

    completed_candle_cutoff = as_of_utc.replace(
        second=0,
        microsecond=0,
    )

    end_utc_exclusive = min(
        calendar_end_utc,
        completed_candle_cutoff,
    )

    return start_utc, end_utc_exclusive


# ---------------------------------------------------------------------------
# Native FTMO M1 research extraction
# ---------------------------------------------------------------------------

def fetch_research_year(
    year: int,
    as_of_utc: datetime,
    chunk_days: int = 31,
) -> dict:
    """
    Fetch native US100.cash M1 observations for a UTC year.

    Research extraction is currently restricted to the
    verified FTMO-Server3 timestamp convention.

    No session filtering, interpolation, aggregation,
    resampling or artificial filling is performed.
    """

    from . import mt5_fetcher

    if (
        not isinstance(chunk_days, int)
        or isinstance(chunk_days, bool)
        or chunk_days <= 0
    ):
        raise ValueError(
            "chunk_days must be a positive integer."
        )

    start_utc, end_utc_exclusive = (
        get_research_year_bounds(
            year=year,
            as_of_utc=as_of_utc,
        )
    )

    symbol = "US100.cash"
    timeframe = "M1"

    chunk_diagnostics = []

    duplicate_diagnostics = {
        "identical_duplicates": 0,
        "conflicting_timestamps": 0,
    }

    mt5_fetcher.initialize_mt5()

    try:
        account = mt5_fetcher.mt5.account_info()

        if account is None:
            raise RuntimeError(
                "No logged-in MT5 account was found."
            )

        server = str(
            getattr(account, "server", "") or ""
        ).strip()

        broker = str(
            getattr(account, "company", "") or ""
        ).strip()

        if server != mt5_fetcher.VERIFIED_FTMO_SERVER:
            raise RuntimeError(
                f"Unverified MT5 server: {server!r}. "
                "Research extraction currently requires "
                "FTMO-Server3."
            )

        if not broker:
            raise RuntimeError(
                "MT5 broker information is unavailable."
            )

        mt5_fetcher.ensure_symbol_available(symbol)

        symbol_info = mt5_fetcher.mt5.symbol_info(
            symbol
        )

        if symbol_info is None:
            raise RuntimeError(
                f"Symbol information unavailable: {symbol}"
            )

        provenance = {
            "symbol": symbol,
            "timeframe": timeframe,
            "broker": broker,
            "server": server,
            "timestamp_mode": "ftmo_server",
            "symbol_digits": int(symbol_info.digits),
            "symbol_point": float(symbol_info.point),
            "calendar_timezone": "UTC",
            "session_filter": None,
            "original_timestamp_column": "mt5_time_raw",
            "corrected_timestamp_column": "datetime",
            "timestamp_correction": (
                "FTMO server wall clock equals "
                "New York wall clock plus seven hours; "
                "converted to genuine UTC."
            ),
        }

        if start_utc == end_utc_exclusive:
            candles = (
                mt5_fetcher.empty_candle_dataframe()
            )

        else:
            candles = mt5_fetcher.fetch_candles_by_range(
                symbol=symbol,
                timeframe_mt5=mt5_fetcher.get_mt5_timeframe(
                    timeframe
                ),
                start_utc=start_utc,
                end_utc_exclusive=end_utc_exclusive,
                chunk_days=chunk_days,
                ftmo_athens_clock=True,
                diagnostics=chunk_diagnostics,
                duplicate_diagnostics=duplicate_diagnostics,
            )

    finally:
        mt5_fetcher.shutdown_mt5()

    return {
        "year": year,
        "candles": candles,
        "provenance": provenance,
        "requested_start_utc": start_utc.isoformat(),
        "requested_end_utc_exclusive": (
            end_utc_exclusive.isoformat()
        ),
        "as_of_utc": (
            as_of_utc.astimezone(UTC).isoformat()
        ),
        "chunk_days": chunk_days,
        "chunk_diagnostics": chunk_diagnostics,
        "duplicate_diagnostics": duplicate_diagnostics,
        "rows_fetched": len(candles),
    }

