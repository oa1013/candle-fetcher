from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .loaders import load_candle_csv
from .volatility_jumps import detect_volatility_jumps


# ---------------------------------------------------------------------------
# Jump profile metrics
# ---------------------------------------------------------------------------

def calculate_jump_profile(
    df: pd.DataFrame,
    label: str,
    rolling_window: int = 100,
    threshold: float = 2.0,
) -> dict:
    """
    Calculate summary metrics for volatility jumps in one candle DataFrame.
    """

    scored_df = detect_volatility_jumps(
        df=df,
        rolling_window=rolling_window,
        threshold=threshold,
    )

    jumps = scored_df[scored_df["is_jump"]].copy()

    total_rows = len(scored_df)
    total_jumps = len(jumps)

    if total_rows == 0:
        jump_rate_pct = 0.0
    else:
        jump_rate_pct = (total_jumps / total_rows) * 100

    if jumps.empty:
        return {
            "label": label,
            "total_rows": total_rows,
            "total_jumps": 0,
            "jump_rate_pct": jump_rate_pct,
            "largest_jump_score": None,
            "avg_jump_score": None,
            "median_jump_score": None,
            "avg_price_move_pct": None,
            "largest_price_move_pct": None,
            "first_jump_datetime": None,
            "last_jump_datetime": None,
        }

    return {
        "label": label,
        "total_rows": total_rows,
        "total_jumps": total_jumps,
        "jump_rate_pct": jump_rate_pct,
        "largest_jump_score": jumps["jump_score"].max(),
        "avg_jump_score": jumps["jump_score"].mean(),
        "median_jump_score": jumps["jump_score"].median(),
        "avg_price_move_pct": jumps["price_move_pct"].abs().mean(),
        "largest_price_move_pct": jumps["price_move_pct"].abs().max(),
        "first_jump_datetime": jumps["datetime"].min(),
        "last_jump_datetime": jumps["datetime"].max(),
    }


def compare_jump_profiles(
    csv_paths: Iterable[str | Path],
    labels: Iterable[str] | None = None,
    rolling_window: int = 100,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """
    Compare volatility jump profiles across multiple CSV files.
    """

    csv_paths = [Path(path) for path in csv_paths]

    if labels is None:
        labels = [path.stem for path in csv_paths]
    else:
        labels = list(labels)

    if len(csv_paths) != len(labels):
        raise ValueError("csv_paths and labels must have the same length.")

    profiles = []

    for csv_path, label in zip(csv_paths, labels):
        df = load_candle_csv(csv_path)

        profile = calculate_jump_profile(
            df=df,
            label=label,
            rolling_window=rolling_window,
            threshold=threshold,
        )

        profile["source_path"] = str(csv_path)

        profiles.append(profile)

    comparison_df = pd.DataFrame(profiles)

    if "total_jumps" in comparison_df.columns:
        comparison_df = comparison_df.sort_values(
            "total_jumps",
            ascending=False,
        ).reset_index(drop=True)

    return comparison_df


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_jump_profile_comparison(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the jump comparison table easier to read.
    """

    if comparison_df.empty:
        return comparison_df.copy()

    columns = [
        "label",
        "total_rows",
        "total_jumps",
        "jump_rate_pct",
        "largest_jump_score",
        "avg_jump_score",
        "median_jump_score",
        "avg_price_move_pct",
        "largest_price_move_pct",
        "first_jump_datetime",
        "last_jump_datetime",
    ]

    available_columns = [
        column for column in columns
        if column in comparison_df.columns
    ]

    output = comparison_df[available_columns].copy()

    round_columns = {
        "jump_rate_pct": 4,
        "largest_jump_score": 2,
        "avg_jump_score": 2,
        "median_jump_score": 2,
        "avg_price_move_pct": 3,
        "largest_price_move_pct": 3,
    }

    for column, decimals in round_columns.items():
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(decimals)

    output = output.rename(
        columns={
            "label": "CSV Name",
            "total_rows": "Total Rows",
            "total_jumps": "Total Jumps",
            "jump_rate_pct": "Jump Rate %",
            "largest_jump_score": "Largest Jump Score",
            "avg_jump_score": "Average Jump Score",
            "median_jump_score": "Median Jump Score",
            "avg_price_move_pct": "Average Price Move %",
            "largest_price_move_pct": "Largest Price Move %",
            "first_jump_datetime": "First Jump",
            "last_jump_datetime": "Last Jump",
        }
    )

    return output


def print_jump_profile_comparison(comparison_df: pd.DataFrame) -> None:
    """
    Print a readable jump comparison table.
    """

    if comparison_df.empty:
        print("No jump profile comparison rows available.")
        return

    friendly_table = format_jump_profile_comparison(comparison_df)

    print("Volatility Jump Comparison")
    print("This table compares volatility jump behavior between CSV files.")
    print()
    print(friendly_table.to_string(index=False))