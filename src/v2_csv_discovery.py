from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SESSION_FOLDERS = {
    "new_york": "New York",
    "london": "London",
    "asia": "Asia",
    "all_sessions": "All Sessions",
}


def discover_processed_csvs() -> list[dict]:
    """
    Discover CSV datasets from the four processed
    session folders.

    Return available files, newest first, with
    metadata suitable for the V2 website.
    """

    datasets = []

    for folder_name, session_label in SESSION_FOLDERS.items():

        folder = PROCESSED_DIR / folder_name

        if not folder.is_dir():
            continue

        for csv_path in folder.glob("*.csv"):

            if not csv_path.is_file():
                continue

            file_info = csv_path.stat()

            datasets.append(
                {
                    "session": session_label,
                    "filename": csv_path.name,
                    "path": str(csv_path.resolve()),
                    "label": f"{session_label} | {csv_path.name}",
                    "size_bytes": file_info.st_size,
                    "modified_timestamp": file_info.st_mtime,
                }
            )

    datasets.sort(
        key=lambda item: item["modified_timestamp"],
        reverse=True,
    )

    return datasets
