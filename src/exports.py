from __future__ import annotations

import hashlib
import json
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


# ---------------------------------------------------------------------------
# Raw historical research exports
# ---------------------------------------------------------------------------

def save_raw_research_csv(
    df: pd.DataFrame,
    output_folder: str | Path,
    filename: str,
) -> Path:
    """
    Save original historical M1 observations to CSV.

    No session filtering, resampling, interpolation,
    rounding, filling or observation removal is performed.

    Existing files are never overwritten.
    """

    from .data_quality import RAW_M1_REQUIRED_COLUMNS

    missing_columns = [
        column
        for column in RAW_M1_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required raw candle columns: "
            f"{missing_columns}"
        )

    filename = str(filename)

    if (
        Path(filename).name != filename
        or not filename.lower().endswith(".csv")
    ):
        raise ValueError(
            "Provide a valid CSV filename without "
            "directory components."
        )

    output_folder = Path(output_folder)
    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_folder / filename

    # Exclusive creation prevents accidental overwriting.
    file = output_path.open(
        mode="x",
        encoding="utf-8",
        newline="",
    )

    try:
        with file:
            df.to_csv(
                file,
                index=False,
            )

    except Exception:
        # Remove an incomplete export if writing fails.
        output_path.unlink(missing_ok=True)
        raise

    return output_path


# ---------------------------------------------------------------------------
# Research provenance and checksum verification
# ---------------------------------------------------------------------------

def compute_file_sha256(
    file_path: str | Path,
) -> str:
    """Calculate the SHA-256 fingerprint of a file."""

    file_path = Path(file_path)
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def save_research_metadata(
    csv_path: str | Path,
    metadata: dict,
) -> Path:
    """
    Save companion research metadata without overwriting
    an existing metadata file.

    The original metadata dictionary remains unchanged.
    """

    from .loaders import DATASET_COMPATIBILITY_FIELDS

    csv_path = Path(csv_path)

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Research CSV not found: {csv_path}"
        )

    if not isinstance(metadata, dict):
        raise ValueError("Research metadata must be a dictionary.")

    for field in DATASET_COMPATIBILITY_FIELDS:
        value = metadata.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Missing or invalid provenance field: {field}"
            )

    payload = dict(metadata)

    payload["csv_filename"] = csv_path.name
    payload["sha256"] = compute_file_sha256(csv_path)
    payload["metadata_schema_version"] = 1

    # Serialize before opening the destination file.
    # Invalid metadata must not create a partial sidecar.
    serialized = json.dumps(
        payload,
        indent=4,
        ensure_ascii=False,
        allow_nan=False,
    )

    metadata_path = csv_path.with_suffix(".metadata.json")

    file = metadata_path.open(
        mode="x",
        encoding="utf-8",
        newline="",
    )

    try:
        with file:
            file.write(serialized + "\n")

    except Exception:
        metadata_path.unlink(missing_ok=True)
        raise

    return metadata_path


def verify_research_checksum(
    csv_path: str | Path,
) -> bool:
    """
    Compare a CSV against its recorded SHA-256 checksum.

    Returns True if the fingerprint matches and False
    if the CSV contents have changed.

    Missing or invalid metadata raises an exception.
    """

    from .loaders import read_dataset_metadata

    csv_path = Path(csv_path)

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Research CSV not found: {csv_path}"
        )

    metadata = read_dataset_metadata(csv_path)

    if metadata is None:
        raise FileNotFoundError(
            f"Research metadata not found: "
            f"{csv_path.with_suffix('.metadata.json')}"
        )

    expected = metadata.get("sha256")

    if (
        not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
    ):
        raise ValueError(
            "Missing or invalid SHA256 checksum."
        )

    if metadata.get("csv_filename") != csv_path.name:
        raise ValueError(
            "Metadata CSV filename does not match."
        )

    actual = compute_file_sha256(csv_path)

    return actual == expected.lower()

