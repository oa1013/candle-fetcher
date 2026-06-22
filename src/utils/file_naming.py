from pathlib import Path
from datetime import datetime


def clean_filename_part(value: str) -> str:
    """
    Cleans a string so it is safe to use inside a CSV filename.
    """
    if value is None:
        return ""

    value = str(value).strip()
    value = value.replace(" ", "_")
    value = value.replace("/", "-")
    value = value.replace("\\", "-")
    value = value.replace(":", "-")

    return value


def build_csv_path(
    output_dir: str = "data/raw",
    output_name: str | None = None,
    session_name: str | None = None,
    symbol: str | None = None,
    timeframe: str = "1m",
    include_date: bool = True,
) -> Path:
    """
    Builds a clean CSV path.

    If output_name is provided, it uses that directly.
    Otherwise it builds a name from:
    session_name + symbol + timeframe + date
    """

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)

    if output_name:
        filename = clean_filename_part(output_name)

        if not filename.endswith(".csv"):
            filename += ".csv"

        return output_folder / filename

    parts = []

    if session_name:
        parts.append(clean_filename_part(session_name))

    if symbol:
        parts.append(clean_filename_part(symbol))

    if timeframe:
        parts.append(clean_filename_part(timeframe))

    if include_date:
        today = datetime.now().strftime("%Y-%m-%d")
        parts.append(today)

    filename = "_".join([part for part in parts if part])

    if not filename:
        filename = f"candles_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    filename += ".csv"

    return output_folder / filename