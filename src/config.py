from pathlib import Path


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"


# ---------------------------------------------------------------------------
# Default candle settings
# ---------------------------------------------------------------------------

DEFAULT_SYMBOL = "US100.cash"
DEFAULT_TIMEFRAME = "M1"

# Your raw CSV files will be loaded from data/raw/
DEFAULT_INPUT_PATTERN = "*.csv"


# ---------------------------------------------------------------------------
# Session settings
# ---------------------------------------------------------------------------
# Times are written as HH:MM.
# You can change these later without rewriting the main functions.

SESSION_CONFIGS = {
    "new_york": {
        "label": "New York",
        "timezone": "America/New_York",
        "start": "09:10",
        "end": "12:30",
        "output_folder": PROCESSED_DATA_DIR / "new_york",
    },
    "london": {
        "label": "London",
        "timezone": "Europe/London",
        "start": "08:00",
        "end": "11:00",
        "output_folder": PROCESSED_DATA_DIR / "london",
    },
    "asia": {
        "label": "Asia",
        "timezone": "Asia/Tokyo",
        "start": "09:00",
        "end": "12:00",
        "output_folder": PROCESSED_DATA_DIR / "asia",
    },
    "all_sessions": {
        "label": "All Sessions",
        "timezone": "UTC",
        "start": None,
        "end": None,
        "output_folder": PROCESSED_DATA_DIR / "all_sessions",
    },
}


# ---------------------------------------------------------------------------
# Expected candle columns
# ---------------------------------------------------------------------------

STANDARD_COLUMNS = [
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]