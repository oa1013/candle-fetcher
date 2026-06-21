from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import DEFAULT_INPUT_PATTERN, RAW_DATA_DIR, STANDARD_COLUMNS


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def clean_column_name(column_name: str) -> str:
    """
    Clean CSV column names so different MT5 formats can be handled.

    Examples:
        <DATE>      -> date
        <TICKVOL>   -> tickvol
        tick volume -> tick_volume
    """
    return (
        str(column_name)
        .strip()
        .strip("<>")
        .strip()
        .lower()
        .replace(" ", "_")
    )


def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the DataFrame with cleaned column names."""
    df = df.copy()
    df.columns = [clean_column_name(col) for col in df.columns]
    return df


def find_first_existing_column(
    df: pd.DataFrame,
    possible_columns: Iterable[str],
) -> str | None:
    """Find the first matching column name from a list of possible names."""
    for column in possible_columns:
        if column in df.columns:
            return column
    return None


# ---------------------------------------------------------------------------
# Datetime handling
# ---------------------------------------------------------------------------

def build_datetime_column(df: pd.DataFrame) -> pd.Series:
    """
    Build a timezone-aware UTC datetime column.

    Supports common formats:
      - date + time columns
      - datetime column
      - unix time column from MT5
    """
    date_col = find_first_existing_column(df, ["date"])
    time_col = find_first_existing_column(df, ["time"])
    datetime_col = find_first_existing_column(df, ["datetime", "date_time"])

    if date_col and time_col:
        return pd.to_datetime(
            df[date_col].astype(str) + " " + df[time_col].astype(str),
            utc=True,
            errors="coerce",
        )

    if datetime_col:
        return pd.to_datetime(
            df[datetime_col],
            utc=True,
            errors="coerce",
        )

    if time_col:
        # MT5 Python exports often store unix seconds in a column called time.
        if pd.api.types.is_numeric_dtype(df[time_col]):
            return pd.to_datetime(
                df[time_col],
                unit="s",
                utc=True,
                errors="coerce",
            )

        return pd.to_datetime(
            df[time_col],
            utc=True,
            errors="coerce",
        )

    raise ValueError(
        "Could not build datetime column. Expected DATE + TIME, DATETIME, or TIME."
    )


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_candle_csv(csv_path: str | Path) -> pd.DataFrame:
    """
    Load one candle CSV and return a standardized candle DataFrame.

    Output columns:
        datetime, open, high, low, close, tick_volume, spread, real_volume
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    raw_df = pd.read_csv(csv_path)
    df = clean_dataframe_columns(raw_df)

    output = pd.DataFrame()
    output["datetime"] = build_datetime_column(df)

    column_map = {
        "open": ["open"],
        "high": ["high"],
        "low": ["low"],
        "close": ["close"],
        "tick_volume": ["tick_volume", "tickvol", "volume", "vol"],
        "spread": ["spread"],
        "real_volume": ["real_volume", "realvol"],
    }

    for output_column, possible_columns in column_map.items():
        source_column = find_first_existing_column(df, possible_columns)

        if source_column is None:
            if output_column in ["spread", "real_volume"]:
                output[output_column] = 0
            elif output_column == "tick_volume":
                output[output_column] = 0
            else:
                raise ValueError(
                    f"Missing required column '{output_column}' in {csv_path}"
                )
        else:
            output[output_column] = df[source_column]

    output = output[STANDARD_COLUMNS]

    output = output.dropna(subset=["datetime"])
    output = output.drop_duplicates(subset=["datetime"])
    output = output.sort_values("datetime").reset_index(drop=True)

    return output


def load_candle_folder(
    folder: str | Path = RAW_DATA_DIR,
    pattern: str = DEFAULT_INPUT_PATTERN,
) -> pd.DataFrame:
    """
    Load and combine all candle CSVs from a folder.

    By default, this loads:
        data/raw/*.csv
    """
    folder = Path(folder)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    csv_files = sorted(folder.glob(pattern))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {folder} using pattern '{pattern}'"
        )

    dataframes = []

    for csv_file in csv_files:
        print(f"Loading: {csv_file}")
        dataframes.append(load_candle_csv(csv_file))

    combined = pd.concat(dataframes, ignore_index=True)

    combined = combined.drop_duplicates(subset=["datetime"])
    combined = combined.sort_values("datetime").reset_index(drop=True)

    return combined


def summarize_candles(df: pd.DataFrame) -> dict:
    """Return a small summary of a candle DataFrame."""
    if df.empty:
        return {
            "rows": 0,
            "first_datetime": None,
            "last_datetime": None,
        }

    return {
        "rows": len(df),
        "first_datetime": str(df["datetime"].iloc[0]),
        "last_datetime": str(df["datetime"].iloc[-1]),
    }