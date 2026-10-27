from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .loaders import load_candle_csv

from .v2_csv_discovery import discover_processed_csvs

from .volatility_jumps import (
    detect_volatility_jumps,
    format_volatility_jump_table,
)


def run_volatility_jump_v2(
    csv_path: str | Path,
    rolling_window: int = 100,
    threshold: float = 2.0,
    top_n: int = 20,
) -> dict:
    """
    Run Volatility Jump analysis for Candle Fetcher 2.0.

    The original volatility detection engine performs
    all statistical calculations.

    This integration prepares results for the V2 website.
    """

    path = Path(csv_path).resolve()

    # ------------------------------------------
    # Dataset validation
    # ------------------------------------------

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

    # ------------------------------------------
    # Parameter validation
    # ------------------------------------------

    if (
        isinstance(rolling_window, bool)
        or not isinstance(rolling_window, int)
        or not 5 <= rolling_window <= 5000
    ):
        raise ValueError(
            "Rolling window must be between 5 and 5000."
        )

    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or not 0.5 <= threshold <= 50.0
    ):
        raise ValueError(
            "Jump threshold must be between 0.5 and 50."
        )

    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or not 1 <= top_n <= 100
    ):
        raise ValueError(
            "Top N must be between 1 and 100."
        )

    # ------------------------------------------
    # Original volatility detection engine
    # ------------------------------------------

    candle_data = load_candle_csv(path)

    if candle_data.empty:
        raise ValueError(
            "The selected CSV contains no candle data."
        )

    scored = detect_volatility_jumps(
        df=candle_data,
        rolling_window=rolling_window,
        threshold=float(threshold),
    )

    # ------------------------------------------
    # Extract detected jumps
    # ------------------------------------------

    jumps = scored.loc[
        scored["is_jump"]
    ].copy()

    total_candles = len(scored)
    total_jumps = len(jumps)

    jump_rate_pct = (
        total_jumps / total_candles * 100
    )

    if jumps.empty:
        largest_jump_score = None
        average_jump_score = None
    else:
        largest_jump_score = float(
            jumps["jump_score"].max()
        )

        average_jump_score = float(
            jumps["jump_score"].mean()
        )

    # ------------------------------------------
    # Rank strongest detected jumps
    # ------------------------------------------

    top_jumps = (
        jumps
        .sort_values(
            "jump_score",
            ascending=False,
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    top_jumps.insert(
        0,
        "rank",
        range(1, len(top_jumps) + 1),
    )

    friendly_jumps = format_volatility_jump_table(
        top_jumps
    )

    # ------------------------------------------
    # Daily jump frequency for graphing
    # ------------------------------------------

    daily_counts = (
        scored
        .groupby(
            scored["datetime"].dt.floor("D")
        )["is_jump"]
        .agg(
            total_candles="size",
            jump_count="sum",
        )
        .reset_index()
        .rename(
            columns={
                "datetime": "date",
            }
        )
    )

    daily_counts["jump_count"] = (
        daily_counts["jump_count"].astype(int)
    )

    daily_counts["jump_rate_pct"] = (
        daily_counts["jump_count"]
        / daily_counts["total_candles"]
        * 100
    )

    # ------------------------------------------
    # Return website-ready results
    # ------------------------------------------

    return {
        "status": "completed",
        "csv_path": str(path),
        "filename": path.name,
        "rolling_window": rolling_window,
        "threshold": float(threshold),
        "top_n": top_n,
        "total_candles": total_candles,
        "total_jumps": total_jumps,
        "jump_rate_pct": jump_rate_pct,
        "largest_jump_score": largest_jump_score,
        "average_jump_score": average_jump_score,
        "top_jumps": top_jumps,
        "formatted_top_jumps": friendly_jumps,
        "daily_counts": daily_counts,
    }
