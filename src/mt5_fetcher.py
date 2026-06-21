from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import pandas as pd

from .config import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, RAW_DATA_DIR


UTC_TZ = timezone.utc


# ---------------------------------------------------------------------------
# Timeframe mapping
# ---------------------------------------------------------------------------

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class MT5FetchConfig:
    """
    Settings for fetching raw candles from MetaTrader 5.

    This saves raw candles into data/raw/.
    Session filtering happens later in the runner notebooks.
    """

    symbol: str = DEFAULT_SYMBOL
    timeframe: str = DEFAULT_TIMEFRAME

    range_name: str = "raw"
    start_date: str = "2021-01-01"
    end_date: str = "2021-12-31"

    output_folder: str | Path = RAW_DATA_DIR
    chunk_days: int = 31

    # Calendar dates are interpreted in this timezone before converting to UTC.
    date_timezone_name: str = "America/New_York"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(value: str) -> date:
    """Parse a date string into a Python date."""
    try:
        return date.fromisoformat(value.replace("/", "-"))
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{value}'. Use YYYY-MM-DD or YYYY/MM/DD format."
        ) from exc


def date_range_to_utc_bounds(
    start_day: date,
    end_day: date,
    timezone_name: str,
) -> Tuple[datetime, datetime]:
    """
    Convert an inclusive local calendar date range into UTC bounds.

    The returned end datetime is exclusive.
    """
    if end_day < start_day:
        raise ValueError(f"End date {end_day} is before start date {start_day}.")

    local_tz = ZoneInfo(timezone_name)

    start_local = datetime.combine(start_day, time.min, tzinfo=local_tz)
    end_exclusive_local = datetime.combine(
        end_day + timedelta(days=1),
        time.min,
        tzinfo=local_tz,
    )

    return (
        start_local.astimezone(UTC_TZ),
        end_exclusive_local.astimezone(UTC_TZ),
    )


# ---------------------------------------------------------------------------
# MT5 helpers
# ---------------------------------------------------------------------------

def get_mt5_timeframe(timeframe: str) -> int:
    """Convert a timeframe label like M1 or M5 into an MT5 timeframe constant."""
    label = timeframe.strip().upper()

    if label not in TIMEFRAME_MAP:
        available = ", ".join(TIMEFRAME_MAP.keys())
        raise ValueError(f"Unknown timeframe '{timeframe}'. Available: {available}")

    return TIMEFRAME_MAP[label]


def initialize_mt5() -> None:
    """Start the MT5 connection. MT5 must already be open and logged in."""
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed. Error code: {mt5.last_error()}")


def shutdown_mt5() -> None:
    """Close the MT5 connection."""
    mt5.shutdown()


def ensure_symbol_available(symbol: str) -> None:
    """Make sure the symbol exists and is visible in Market Watch."""
    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        raise ValueError(
            f"Symbol '{symbol}' was not found in MetaTrader 5. "
            "Check the exact broker symbol name in Market Watch."
        )

    if not symbol_info.visible:
        selected = mt5.symbol_select(symbol, True)

        if not selected:
            raise RuntimeError(
                f"Symbol '{symbol}' exists but could not be selected in Market Watch."
            )


# ---------------------------------------------------------------------------
# Data conversion
# ---------------------------------------------------------------------------

def empty_candle_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with the standard candle columns."""
    return pd.DataFrame(
        columns=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]
    )


def rates_to_dataframe(rates) -> pd.DataFrame:
    """Convert MT5 rates output into a clean OHLCV DataFrame."""
    df = pd.DataFrame(rates)

    if df.empty:
        return empty_candle_dataframe()

    df["datetime"] = pd.to_datetime(
        df["time"],
        unit="s",
        utc=True,
    )

    df = df[
        [
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]
    ]

    df = df.drop_duplicates(subset=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_candles_by_range(
    symbol: str,
    timeframe_mt5: int,
    start_utc: datetime,
    end_utc_exclusive: datetime,
    chunk_days: int = 31,
) -> pd.DataFrame:
    """
    Fetch candles from MT5 between explicit UTC datetimes.
    """
    if start_utc.tzinfo is None or end_utc_exclusive.tzinfo is None:
        raise ValueError("start_utc and end_utc_exclusive must be timezone-aware.")

    if end_utc_exclusive <= start_utc:
        raise ValueError("end_utc_exclusive must be after start_utc.")

    chunks = []
    chunk_start = start_utc

    while chunk_start < end_utc_exclusive:
        chunk_end = min(
            chunk_start + timedelta(days=chunk_days),
            end_utc_exclusive,
        )

        print(
            f"Fetching chunk: "
            f"{chunk_start:%Y-%m-%d %H:%M} -> {chunk_end:%Y-%m-%d %H:%M} UTC"
        )

        rates = mt5.copy_rates_range(
            symbol,
            timeframe_mt5,
            chunk_start,
            chunk_end,
        )

        if rates is None:
            print(f"WARNING: MT5 returned None. Error code: {mt5.last_error()}")
        elif len(rates) == 0:
            print("WARNING: MT5 returned zero candles for this chunk.")
        else:
            chunks.append(rates_to_dataframe(rates))

        chunk_start = chunk_end

    if not chunks:
        return empty_candle_dataframe()

    df = pd.concat(chunks, ignore_index=True)

    df = df.drop_duplicates(subset=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    df = df[
        (df["datetime"] >= pd.Timestamp(start_utc))
        & (df["datetime"] < pd.Timestamp(end_utc_exclusive))
    ]

    df = df.reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def clean_filename_part(value: str) -> str:
    """Make a safe filename component from user text."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "value"


def make_raw_output_filename(
    symbol: str,
    timeframe: str,
    range_name: str,
    start_day: date,
    end_day: date,
) -> str:
    """Build the raw CSV filename."""
    symbol_part = clean_filename_part(symbol.replace(".", "_"))
    timeframe_part = clean_filename_part(timeframe).upper()
    range_part = clean_filename_part(range_name)

    return (
        f"{symbol_part}_{timeframe_part}_raw_"
        f"{range_part}_{start_day}_to_{end_day}.csv"
    )


def save_raw_candles_to_csv(
    df: pd.DataFrame,
    output_folder: str | Path,
    filename: str,
) -> Path:
    """Save raw candles to CSV."""
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    output_path = output_folder / filename
    df.to_csv(output_path, index=False)

    return output_path


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def fetch_raw_candles(config: MT5FetchConfig) -> Dict[str, object]:
    """
    Fetch raw candles from MT5 and save them into data/raw/.

    This does not filter by trading session.
    Session filtering happens later.
    """
    start_day = parse_date(config.start_date)
    end_day = parse_date(config.end_date)

    start_utc, end_utc_exclusive = date_range_to_utc_bounds(
        start_day=start_day,
        end_day=end_day,
        timezone_name=config.date_timezone_name,
    )

    timeframe_mt5 = get_mt5_timeframe(config.timeframe)

    initialize_mt5()

    try:
        ensure_symbol_available(config.symbol)

        raw_df = fetch_candles_by_range(
            symbol=config.symbol,
            timeframe_mt5=timeframe_mt5,
            start_utc=start_utc,
            end_utc_exclusive=end_utc_exclusive,
            chunk_days=config.chunk_days,
        )

    finally:
        shutdown_mt5()

    if raw_df.empty:
        raise RuntimeError(
            "No candles were fetched. Check symbol, MT5 login, and data availability."
        )

    filename = make_raw_output_filename(
        symbol=config.symbol,
        timeframe=config.timeframe,
        range_name=config.range_name,
        start_day=start_day,
        end_day=end_day,
    )

    output_path = save_raw_candles_to_csv(
        df=raw_df,
        output_folder=config.output_folder,
        filename=filename,
    )

    return {
        "output_path": str(output_path.resolve()),
        "filename": filename,
        "rows_saved": len(raw_df),
        "first_datetime_utc": str(raw_df["datetime"].iloc[0]),
        "last_datetime_utc": str(raw_df["datetime"].iloc[-1]),
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "start_date": config.start_date,
        "end_date": config.end_date,
    }


def print_fetch_result(result: Dict[str, object]) -> None:
    """Print a clean fetch summary."""
    print("MT5 raw candle fetch complete")
    print(f"Symbol: {result['symbol']}")
    print(f"Timeframe: {result['timeframe']}")
    print(f"Rows saved: {result['rows_saved']:,}")
    print(f"First datetime UTC: {result['first_datetime_utc']}")
    print(f"Last datetime UTC: {result['last_datetime_utc']}")
    print(f"Filename: {result['filename']}")
    print(f"Path: {result['output_path']}")