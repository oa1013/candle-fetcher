from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .v2_csv_discovery import discover_processed_csvs
from .csv_comparison import compare_csv_files
from .comparison_formatting import (
    format_regime_summary_table,
    format_pairwise_comparison_table,
)
from .comparison_exports import save_comparison_result


def run_csv_comparison_v2(
    csv_paths: Iterable[str | Path],
    labels: Iterable[str] | None = None,
    comparison_name: str = "candle_fetcher_v2",
    save_results: bool = False,
    include_timestamp: bool = True,
) -> dict:
    """
    Run CSV Comparison for Candle Fetcher 2.0.

    Uses the existing statistical comparison engine.
    No volatility or similarity calculations are rewritten.
    """

    # Validate selected datasets.
    paths = [Path(path).resolve() for path in csv_paths]

    if len(paths) < 2:
        raise ValueError(
            "Select at least two CSV datasets."
        )

    if len(paths) != len(set(paths)):
        raise ValueError(
            "The same CSV file cannot be selected twice."
        )

    # Only accept files discovered in our processed folders.
    available_paths = {
        Path(dataset["path"]).resolve()
        for dataset in discover_processed_csvs()
    }

    for path in paths:
        if path not in available_paths:
            raise ValueError(
                f"CSV file is not in the processed dataset list: {path}"
            )

        if not path.is_file():
            raise FileNotFoundError(path)

    # Validate dataset labels.
    if labels is None:
        dataset_labels = [
            f"{path.parent.name} | {path.stem}"
            for path in paths
        ]
    else:
        dataset_labels = [
            str(label).strip()
            for label in labels
        ]

    if len(dataset_labels) != len(paths):
        raise ValueError(
            "The number of labels must match the number of CSV files."
        )

    if not all(dataset_labels):
        raise ValueError(
            "Dataset labels cannot be empty."
        )

    if len(dataset_labels) != len(set(dataset_labels)):
        raise ValueError(
            "Dataset labels must be unique."
        )

    # Run our original statistical comparison engine.
    result = compare_csv_files(
        csv_paths=paths,
        labels=dataset_labels,
    )

    # Prepare readable tables for the V2 website.
    regime_table = format_regime_summary_table(
        result["regime_summary"]
    )

    similarity_table = format_pairwise_comparison_table(
        result["pairwise_comparisons"]
    )

    # Optional report exports.
    export_paths = {}

    if save_results:
        export_paths = save_comparison_result(
            result=result,
            comparison_name=comparison_name,
            include_timestamp=include_timestamp,
        )

    return {
        "status": "completed",
        "dataset_count": len(paths),
        "dataset_labels": dataset_labels,
        "regime_summary": regime_table,
        "pairwise_comparisons": similarity_table,
        "raw_result": result,
        "export_paths": export_paths,
    }
