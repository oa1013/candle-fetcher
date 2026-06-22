from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, PROCESSED_DATA_DIR, SESSION_CONFIGS


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def clean_filename_part(value: str) -> str:
    """
    Convert text into a safe filename component.

    Example:
        "US100.cash" -> "us100_cash"
        "New York"   -> "new_york"
    """
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "value"


def format_date_for_filename(value) -> str:
    """
    Convert a date-like value into a clean filename string.

    If value is None, return 'all'.
    """
    if value is None:
        return "all"

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return clean_filename_part(str(value))

    return parsed.strftime("%Y_%m_%d")


def build_output_filename(
    session_name: str,
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    start_date=None,
    end_date=None,
    suffix: str | None = None,
) -> str:
    """
    Build a clean output filename for a filtered candle CSV.

    Example:
        us100_cash_M1_new_york_2021_01_01_to_2021_12_31.csv
    """
    symbol_part = clean_filename_part(symbol)
    timeframe_part = clean_filename_part(timeframe).upper()
    session_part = clean_filename_part(session_name)

    start_part = format_date_for_filename(start_date)
    end_part = format_date_for_filename(end_date)

    filename = (
        f"{symbol_part}_{timeframe_part}_{session_part}_"
        f"{start_part}_to_{end_part}"
    )

    if suffix:
        filename += f"_{clean_filename_part(suffix)}"

    return f"{filename}.csv"


# ---------------------------------------------------------------------------
# Folder helpers
# ---------------------------------------------------------------------------

def get_output_folder(session_name: str | None = None) -> Path:
    """
    Get the correct output folder.

    If session_name is known, use that session's configured output folder.
    Otherwise, use data/processed.
    """
    if session_name is None:
        return PROCESSED_DATA_DIR

    normalized_name = session_name.strip().lower()

    if normalized_name in SESSION_CONFIGS:
        return Path(SESSION_CONFIGS[normalized_name]["output_folder"])

    return PROCESSED_DATA_DIR / clean_filename_part(normalized_name)


def ensure_folder_exists(folder: str | Path) -> Path:
    """Create a folder if it does not already exist and return it as a Path."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def save_dataframe_to_csv(
    df: pd.DataFrame,
    output_folder: str | Path,
    filename: str,
) -> Path:
    """
    Save a DataFrame to CSV and return the saved path.
    """
    output_folder = ensure_folder_exists(output_folder)
    output_path = output_folder / filename

    df.to_csv(output_path, index=False)

    return output_path


def save_session_csv(
    df: pd.DataFrame,
    session_name: str,
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    start_date=None,
    end_date=None,
    suffix: str | None = None,
    output_name: str | None = None,
) -> dict:
    """
    Save a filtered session DataFrame to the correct processed folder.

    If output_name is provided, it will be used as the CSV filename.
    Otherwise, the normal automatic filename will be created.
    """

    output_folder = get_output_folder(session_name)

    if output_name:
        clean_name = str(output_name).strip()

        if clean_name.lower().endswith(".csv"):
            clean_name = clean_name[:-4]

        filename = f"{clean_filename_part(clean_name)}.csv"

    else:
        filename = build_output_filename(
            session_name=session_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            suffix=suffix,
        )

    output_path = save_dataframe_to_csv(
        df=df,
        output_folder=output_folder,
        filename=filename,
    )

    return {
        "output_path": str(output_path),
        "filename": filename,
        "rows_saved": len(df),
        "session_name": session_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def print_export_summary(result: dict) -> None:
    """Print a clean export summary."""
    print("Export complete")
    print(f"Session: {result['session_name']}")
    print(f"Rows saved: {result['rows_saved']:,}")
    print(f"Filename: {result['filename']}")
    print(f"Path: {result['output_path']}")