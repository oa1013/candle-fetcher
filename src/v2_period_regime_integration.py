from __future__ import annotations

from pathlib import Path

from .v2_csv_discovery import discover_processed_csvs
from .regime_period_filter import (
    normalize_period,
    normalize_regime,
    find_period_regimes_from_csv,
    format_period_regime_table,
)


def run_period_regime_v2(
    csv_path: str | Path,
    period: str = "month",
    regime: str = "volatile",
    top_n: int = 10,
) -> dict:
    """
    Run Period Regime Finder for Candle Fetcher 2.0.

    Uses the existing statistical engine without
    rewriting its calculations.
    """

    path = Path(csv_path).resolve()

    # Only accept discovered processed CSV datasets.
    available_paths = {
        Path(item["path"]).resolve()
        for item in discover_processed_csvs()
    }

    if path not in available_paths:
        raise ValueError(
            "Selected CSV is not in the processed dataset list."
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    # Reuse existing parameter normalisation.
    period = normalize_period(period)
    regime = normalize_regime(regime)

    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or not 1 <= top_n <= 100
    ):
        raise ValueError(
            "Top N must be an integer between 1 and 100."
        )

    # Original statistical engine — source of truth.
    raw_results = find_period_regimes_from_csv(
        csv_path=path,
        period=period,
        regime=regime,
        top_n=top_n,
    )

    if raw_results.empty:
        raise ValueError(
            "No period regime results were found."
        )

    # Original readable table formatter.
    formatted_results = format_period_regime_table(
        raw_results
    )

    return {
        "status": "completed",
        "csv_path": str(path),
        "filename": path.name,
        "period": period,
        "regime": regime,
        "top_n": top_n,
        "periods_returned": len(raw_results),
        "raw_results": raw_results,
        "formatted_results": formatted_results,
    }
